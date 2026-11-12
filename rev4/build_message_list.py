"""Data Readiness revision 4: the messages APG's production code gives when it cannot fully do a check or a figure, with what the builder
is to do (the owner's rule of 2026-11-12: "This feature of telling the builder what apg needs to work should be across the whole apg").
Builder work (Claude), not independent.  It states the design; nothing here changes the code.

It parses (with Python's ast module) every production module of apg/fin, apg/det, apg/mkt, apg/ingest, plus apg/source_authority.py and
apg/policy_approval.py (test, corpus, demo, golden, faulty, reference, contract and port modules are left out), and collects:
  - every string constant that starts with an upper-case code (one word or more, with or without ':'), and pieces the code joins into codes
    (EXPAND); rule ids and a few non-message words are listed in NOT_CODE;
  - the reason of every figure 'unknown' input, every exclusion class and every dispute text (fin FigureBuilder);
  - every text or word given as 'why', 'reason', 'note', 'missing_parameter', 'sample_note' or 'status' (dict keys, assignments, keyword
    arguments other than audit-log calls), every '(None, text)' a function returns, every 'skipped' reason;
  - the states of ingest/freshness.py and the provisional and cannot-assess figure states, and the run states of det and mkt;
  - every text raised by an APG exception class (not Python's own errors, which are programming faults) or refused by policy_approval.py.
It fails if the code gives one of these that the tables below do not cover, or if a table holds one the code no longer gives.  This is a
check against the code by those patterns, not a proof: a message built in a way the patterns do not see would be missed.  Each message is
proven when it is built and tested, first in the defect change request.  It also lists the cases that give no message today (DC-1 to DC-12;
DC-3 is an uncaught error, the others are silent).

Audience:  builder      - a gap in the builder's data or settings: the message says what to do and who usually does it
           person       - a check on an action a person is taking (approving, resolving, recording, verifying): what that person must add
           information  - a label or note that explains a result; no action needed
           system       - an APG integrity or programming fault: nothing for the builder; APG support investigates
The wording is the design's starting point; the exact text is settled when each message is built.
usage: python3 -I build_message_list.py <the apg folder> <output folder>"""
import csv, os, re, sys

APG, OUT = sys.argv[1], sys.argv[2]
SKIP = re.compile(r'(corpus|demo_|faulty|golden|reference_|contracts_|ports_)')

B, P, I, S = 'builder', 'person', 'information', 'system'
BK, PM, CM, FN, AP, SU = 'bookkeeper', 'project manager', 'commercial manager', 'finance', "the builder's approver", 'APG support'
# code: (audience, what it means, what to do, who usually does it)
MSG = {
 'ACTION_REQUIRED': (P, 'a proposed action on a finding was not described', 'describe the proposed action', 'the person proposing it'),
 'ACTUALS_AFTER_FORECAST_DATE_NOT_ADDED': (I, 'the assessment date differs from the forecast date; any cost recorded after the forecast date is not added to the forecast final cost', 'update the forecast if it should include later cost', PM),
 'ACTUAL_COST_FIGURE_PROVISIONAL': (I, 'the budget comparison rests on an actual-cost figure that is provisional', 'resolve what makes actual cost provisional (listed with it)', BK),
 'AMBIGUOUS_LATEST_FORECAST': (B, 'two forecast versions share the latest date, so APG cannot tell which is current', 'mark one forecast version as current, or date them differently', PM),
 'AMBIGUOUS_REVISION': (B, 'two values of the same field arrived and their revision order cannot be told', 'confirm which value is current', BK),
 'AMOUNT_INVALID': (P, 'a retention event has an amount that is not valid', 'enter a valid amount for the event', FN),
 'AMOUNT_UNKNOWN': (B, 'the record has no usable amount, so it is left out of the figure', 'enter or correct the amount', BK),
 'APPROVAL_NOT_CURRENT': (P, 'the approval no longer matches the proposal and evidence on record', 'approve the action again', AP),
 'APPROVAL_TOKEN_REQUIRED': (P, 'the approval does not name the version, evidence and proposal the approver was shown', 'approve from the current proposal', AP),
 'APPROVER_ROLE_REQUIRED': (P, 'this retention step needs a person with the approver role', 'have an approver record the step', AP),
 'ASSIGNEE_REQUIRED': (P, 'a finding was assigned without naming a person', 'name the person it is assigned to', PM),
 'ASSUMPTION_INVALID_OR_UNSIGNED': (B, 'a landed-cost assumption is invalid or not signed off, so it is not used', 'correct the assumption and have it signed off', CM),
 'AS_OF_INVALID': (S, 'the authority check was given an invalid date', 'none for the builder', SU),
 'ATTRIBUTE_FAILS': (I, 'the offer fails a required attribute of the specification, so it is not comparable', 'none, unless the specification or the quote is wrong; then correct it', CM),
 'ATTRIBUTE_UNKNOWN': (B, 'a required attribute of the offer is not known, so it is unverified', 'record the attribute from the quote, and have it verified', CM),
 'AUTHORITATIVE_DIFFERS_FROM_LAST_ADOPTION': (S, 'the authoritative forecast differs from the one last adopted', 'none for the builder', SU),
 'AUTHORITATIVE_RULE_APPLIED': (I, 'the value was chosen by the approved source-authority rule', 'none', '-'),
 'AUTHORITATIVE_SOURCE_ABSENT': (B, 'no value has arrived from the source the authority register names for this field; a reviewer cannot clear it', 'supply the value from the authoritative source, or have the register corrected', BK),
 'AUTHORITATIVE_VALUE_UNKNOWN': (B, 'the authoritative source sent no usable value for this field; a reviewer cannot clear it', 'correct the value in the authoritative source and send it again', BK),
 'AWAITING_HUMAN_APPROVAL': (B, 'the authority register says this field needs a person\'s approval', 'approve the value', AP),
 'AWAITING_HUMAN_VERIFICATION': (B, 'the value was read by AI or OCR and waits for a person to verify it', 'verify the value against the document', 'the verifier'),
 'BANK_EVIDENCE_REQUIRED': (P, 'a retention release marked received needs the bank transaction of exactly that amount', 'import the bank transaction, then record the event', FN),
 'BASIS_NOT_IN_TABLE': (B, 'the quote\'s delivery basis is not in the delivery-basis table, so what the rate includes is unknown', 'add the delivery basis to the table in setup', CM),
 'BUDGET_CHANGED_AND_CTC_DERIVED_FROM_IT': (I, 'the forecast moved because the budget changed and the cost to complete is derived from it', 'none; check the budget change was intended', PM),
 'BUDGET_EXCEEDED_BY': (B, 'cost on this code is above its budget, so a budget-derived cost to complete is not known', 'enter a cost to complete for the code', PM),
 'BUDGET_NOT_POSITIVE': (B, 'the cost code\'s budget is zero or negative, so overspend cannot be assessed', 'correct the budget line', PM),
 'CANNOT_ADOPT_A_FORECAST_THAT_CANNOT_BE_ASSESSED': (P, 'a forecast that cannot be assessed cannot be adopted', 'resolve what stops the forecast, then adopt it', PM),
 'CARRYING_NOT_CONFIGURED': (B, 'the carrying-cost method is not set, so carrying cost cannot be assessed', 'set the carrying-cost method in setup', FN),
 'CASH_ADJUSTMENT_NOT_CONFIGURED': (B, 'the cash-adjusted margin settings are not set', 'set the cash-adjustment settings in setup', FN),
 'CELL_TOO_LONG': (B, 'a cell in the import file is longer than allowed; the row is rejected', 'shorten the cell and import the file again', BK),
 'CHANGE_NOT_APPROVED': (B, 'the order amendment has no approved change, so it counts as exposure, not commitment', 'link the approved variation, or have the change approved', PM),
 'CLERK_ROLE_REQUIRED': (P, 'this retention step needs a person with the clerk role', 'have the right person record the step', FN),
 'CLUSTER_WITH_SINGLE_MATERIAL_ORDER': (I, 'a group of possibly split orders includes one order that is material on its own', 'none; review the group', PM),
 'COMPONENT_MISSING': (B, 'a landed-cost component this purchase requires is missing, so the cost is "at least"', 'add the missing component (freight, duty or other, as named)', CM),
 'CONCURRENT_CHANGE': (P, 'the finding changed while the action was being decided', 'read the finding again and retry', 'the person acting'),
 'CONFLICT_SAME_KEY': (B, 'two different records arrived under the same identifier; both are quarantined', 'confirm which record is right and send the correction', BK),
 'CONFLICT_SAME_REVISION': (B, 'different values arrived at the same revision; the field is quarantined', 'confirm the right value with the source', BK),
 'CONTRACT_SUMMARY_DISAGREES_WITH_REGISTER': (B, 'the contract\'s approved-variations total differs from the variation register', 'reconcile the contract summary with the variation register', CM),
 'CONVERTED_FROM_INC_GST_AT_POLICY_RATE': (I, 'an amount entered including GST was converted at the policy\'s GST rate', 'none', '-'),
 'COST_NOT_ALLOCATED_TO_A_COST_CODE': (B, 'cost without a cost code cannot be forecast by code', 'add the cost code to the invoices listed', BK),
 'COST_SCOPE_NOT_CONFIGURED': (B, 'what actual cost includes is not set, so actual cost cannot be assessed', 'set the cost scope in setup', FN),
 'COST_TO_COMPLETE_CHANGED_WITH_BLANK_MOVEMENT_REASON': (B, 'a cost to complete moved and no reason was recorded', 'record the reason for the movement', PM),
 'COST_TO_COMPLETE_NEWLY_KNOWN_WAS_UNKNOWN': (I, 'a cost to complete is known now that was unknown before, so the movement is not explained', 'none; check the new figure', PM),
 'COST_TO_COMPLETE_NOW_UNKNOWN': (B, 'a cost to complete that was known is now unknown', 'enter the cost to complete for the code', PM),
 'COUNTED_RECORD_CHANGED_AMOUNT': (B, 'a record already counted changed its amount, so the movement is not explained', 'confirm the change and record why', BK),
 'CREDIT_DATED_AFTER_CUTOFF': (I, 'the credit is dated after the cut-off, so it is not yet applied', 'none', '-'),
 'CREDIT_EXCEEDS_INVOICE': (B, 'credits against the invoice add up to more than the invoice; all are held', 'correct the credit notes or the invoice reference', BK),
 'CREDIT_NOT_LINKED_TO_A_TRUSTED_INVOICE': (B, 'the credit is not linked to an invoice APG can trust', 'link the credit to its invoice, or resolve the invoice\'s hold', BK),
 'CREDIT_SUPPLIER_MISMATCH': (B, 'the credit note\'s supplier differs from the invoice\'s; the credit is held', 'correct the supplier or the invoice reference', BK),
 'CREDIT_TARGET_NOT_VISIBLE': (B, 'the invoice the credit names has not arrived; the credit is held', 'import the invoice, or correct the reference', BK),
 'CRITICAL_VALUE_MISSING': (B, 'a value is missing that the intake settings do not declare optional, so the record is held', 'enter the value, or have the field declared optional in the intake settings', BK),
 'CTC_METHOD_CHANGED': (I, 'the cost-to-complete method changed between the two forecasts', 'none; check the change was intended', PM),
 'CTC_UNKNOWN': (B, 'the cost to complete for this code is not known, so the forecast is provisional', 'enter the cost to complete for the code', PM),
 'CURRENCY_NOT_CONVERTED': (B, 'the price cannot be converted to the home currency', 'import a current exchange rate for the currency', CM),
 'DATED_AFTER_CUTOFF': (I, 'the record is dated after the cut-off, so it is not counted yet', 'none', '-'),
 'DATE_ORDER': (B, 'the dates are in the wrong order (for example valid until before issue)', 'correct the dates', BK),
 'DATE_OUT_OF_RANGE': (B, 'a date in the file is outside the accepted range; the row is rejected', 'correct the date and import again', BK),
 'DATE_UNKNOWN': (B, 'the record has no usable date, so it is left out of the figure', 'enter the date', BK),
 'DECLARED_LINE_HELD': (B, 'the cost-to-complete line for this code is held', 'resolve the hold on the line', PM),
 'DECLARED_LINE_NOT_USED_BY_METHOD': (I, 'the forecast method does not use declared lines for this code', 'none', '-'),
 'DET_POLICY_NOT_PINNED': (B, 'no detection settings are in force, so the rule cannot be assessed', 'set up and approve the detection settings', AP),
 'DIFFERENT_FFC_BASIS': (I, 'the two forecasts use different bases, so they are not compared', 'none', '-'),
 'DIFFERENT_PROJECTS': (S, 'the two runs compared are for different projects', 'none for the builder', SU),
 'DIFFERENT_TAX_BASIS': (I, 'the two forecasts use different tax bases, so they are not compared', 'none', '-'),
 'DUPLICATE_CANDIDATE': (B, 'the record looks like a duplicate of another; both are held for review', 'confirm whether they are the same, or correct one', BK),
 'DUPLICATE_HEADER': (B, 'a column name appears twice in the file; the file is rejected', 'fix the header and import again', BK),
 'DUPLICATE_OF': (I, 'a repeat delivery of the same record; it is counted once', 'none', '-'),
 'EMPTY_FILE': (B, 'the import file is empty', 'export the file again and import it', BK),
 'EVENT_NOT_LISTED_FOR_RENOTIFICATION': (I, 'this kind of change does not send a new notification', 'none', '-'),
 'EVIDENCE_REQUIRED': (P, 'this step needs a reference to the evidence', 'attach the evidence reference', 'the person acting'),
 'EXPECTED_RELEASE_DATE_PASSED_AND_NOT_RELEASED': (B, 'the retention release date has passed without a release, so a forward cost cannot be estimated', 'record the new expected release date', FN),
 'EXPIRY_REVIEW': (B, 'a security instrument has reached its expiry date', 'review the instrument: renew or release it', FN),
 'FACILITY_RECORD_HELD': (B, 'the facility statement is held, so carrying cost cannot be assessed', 'resolve the hold on the facility statement', FN),
 'FACILITY_STATEMENT_AFTER_AS_OF': (B, 'the only facility statement is dated after the assessment date, so carrying cost cannot be assessed', 'supply a statement for the period', FN),
 'FILE_INTEGRITY': (S, 'a stored file no longer matches its recorded fingerprint', 'none for the builder', SU),
 'FILE_NOT_FOUND': (S, 'a stored file cannot be found', 'none for the builder', SU),
 'FILE_TOO_LARGE': (B, 'the import file is larger than allowed', 'split the file and import the parts', BK),
 'FINDING_UNKNOWN': (S, 'an action named a finding that does not exist', 'none for the builder', SU),
 'FORECAST_BASIS_CANNOT_BE_ASSESSED': (B, 'the forecast the margin rests on cannot be assessed', 'resolve what stops the forecast (listed with it)', PM),
 'FORECAST_DERIVED_FROM_BUDGET_NO_DECLARED_VERSION': (B, 'there is no declared forecast, so the cost to complete is derived from the budget', 'enter a forecast version', PM),
 'FORECAST_DOES_NOT_REPRODUCE': (S, 'a forecast run does not reproduce from its stored inputs', 'none for the builder', SU),
 'FORECAST_FINAL_COST_NOT_POSITIVE': (B, 'the forecast final cost is zero or negative, so the margin cannot be assessed', 'check the forecast and cost records', PM),
 'FORECAST_OWNER_REQUIRED': (P, 'adopting a forecast needs a person with the forecast-owner role', 'have the forecast owner adopt it', PM),
 'FORECAST_VERSION_DATES_DISAGREE': (B, 'the lines of the chosen forecast version carry different dates', 'correct the forecast lines\' dates', PM),
 'FORECAST_VERSION_NOT_FOUND': (B, 'the forecast version asked for is not in the data', 'import that version, or choose another', PM),
 'FORMULA_PREFIX': (B, 'a cell starts like a spreadsheet formula; it is flagged', 'check the cell holds a value, not a formula', BK),
 'FUTURE_DATED': (B, 'the record is dated in the future', 'correct the date, or wait for it', BK),
 'GST_RATE_NOT_CONFIGURED': (B, 'the GST rate is not set', 'set the GST rate in setup', FN),
 'HELD_SUPPORTING_RECORDS': (B, 'records the offer depends on are held, so no definitive ranking', 'resolve the holds listed', CM),
 'HELD_WITH_REASON': (I, 'the retention is held, with a recorded reason', 'none', '-'),
 'HIDDEN_CHARACTER': (B, 'a cell holds a hidden character; the row is rejected', 'remove the character and import again', BK),
 'HISTORY_CHAIN_BROKEN_AT': (S, 'the forecast history chain is broken', 'none for the builder', SU),
 'HISTORY_RUN_MISSING': (S, 'a run in the forecast history is missing', 'none for the builder', SU),
 'HUMAN_ACTOR_REQUIRED': (P, 'this retention step must be recorded by a person', 'have a named person record it', FN),
 'HUMAN_CORRECTION_APPLIED': (I, 'a person\'s correction was applied to the record', 'none', '-'),
 'HUMAN_REQUIRED': (P, 'this step must be done by a person', 'have a named person do it', 'the person acting'),
 'COMPONENT_PROVISIONAL': (B, 'an M4 figure rests on a part that is provisional; the part is named', 'act on that part\'s reasons', FN),
 'COMPONENT_CANNOT_ASSESS': (B, 'an M4 figure rests on a part that cannot be assessed; the part is named', 'act on that part\'s reasons', FN),
 'PROVISIONAL': (I, 'a separate total of the candidate values of records that are not yet authoritative; it is never added to the authoritative total', 'resolve the records listed with it', BK),
 'INSIDE_SUPPRESSION_WINDOW': (I, 'the notification is not re-sent inside the quiet period', 'none', '-'),
 'INSUFFICIENT_IN_POOL': (P, 'the retention event moves more than the state holds', 'correct the event amount', FN),
 'INTERNATIONAL_CHECKS_UNRESOLVED': (B, 'import checks for the international quote are not resolved, so no definitive ranking', 'resolve the import checks listed', CM),
 'INVALID_BOOLEAN': (B, 'a yes/no cell holds something else; the row is rejected', 'correct the cell and import again', BK),
 'INVALID_DATE': (B, 'a date cell does not match the expected format; the row is rejected', 'correct the date and import again', BK),
 'INVALID_DECIMAL': (B, 'a number cell is not a valid decimal; the row is rejected', 'correct the number and import again', BK),
 'INVALID_ENUM': (B, 'a cell holds a value not in the allowed list; the row is rejected', 'use one of the allowed values', BK),
 'INVALID_INTEGER': (B, 'a whole-number cell holds something else; the row is rejected', 'correct the number and import again', BK),
 'INVALID_MONEY': (B, 'a money cell is not a whole number of cents; the row is rejected', 'correct the amount and import again', BK),
 'INVALID_TYPE': (S, 'the import template names an unknown field type', 'none for the builder', SU),
 'INVALID_VALUE': (B, 'a value is not valid for its field', 'correct the value', BK),
 'INVOICED_EXCEEDS_COMMITMENT': (B, 'invoices against the order exceed what was committed', 'check the order, its amendments and the invoices', PM),
 'LANDED_COST_INCOMPLETE': (B, 'the landed cost has missing parts, so no definitive ranking', 'add the missing components listed', CM),
 'LINKED_CREDIT_UNRESOLVED': (B, 'a credit linked to the invoice is not resolved, so the invoice is held out', 'resolve the credit\'s hold', BK),
 'LINK_INVALID': (P, 'the link given for a finding is not valid', 'give a valid link', 'the person acting'),
 'MALFORMED_CSV': (B, 'the import file is not a valid CSV file', 'export the file again and import it', BK),
 'MARGIN_CANNOT_BE_ASSESSED': (B, 'the margin cannot be assessed', 'resolve what stops it (listed with it)', FN),
 'MATERIAL_VALUE_UNKNOWN': (B, 'a value that decides money is missing or not usable; a reviewer cannot clear it', 'supply the value from its source', BK),
 'MISSING_COLUMNS': (B, 'required columns are missing from the file', 'add the columns named and import again', BK),
 'MIXED_BUDGET_REVISIONS': (B, 'budget lines from different revisions are mixed', 'import one complete budget revision', PM),
 'MKT_POLICY_NOT_PINNED': (B, 'no procurement settings are in force, so the M6 rules cannot be assessed', 'set up and approve the procurement settings', AP),
 'NOISE_POLICY_NOT_CONFIGURED': (B, 'notification settings are not set, so only new and reopened findings notify', 'set the notification settings in setup', PM),
 'NON_ASCII_IDENTIFIER': (B, 'an identifier holds characters that are not plain ASCII; the row is rejected', 'correct the identifier', BK),
 'NOT_ACTIVE': (P, 'the finding is not active, so this action does not apply', 'none', 'the person acting'),
 'NOT_APPLICABLE_REVENUE_ZERO_OR_NEGATIVE': (B, 'revenue is zero or negative, so a margin percentage does not apply', 'check the contract value and variations', CM),
 'NOT_A_DETECTION_RUN': (S, 'the run given is not a detection run', 'none for the builder', SU),
 'NOT_A_FORECAST': (S, 'the run given is not a forecast', 'none for the builder', SU),
 'NOT_A_SCENARIO_RUN': (S, 'the run given is not a scenario run', 'none for the builder', SU),
 'NOT_BYTES': (S, 'the importer was given something that is not a file', 'none for the builder', SU),
 'NOT_RECONCILED': (B, 'the order or quote has no reconciliation state, so it is not used', 'have the record reconciled (the intake does this when it runs)', BK),
 'NOT_USABLE': (B, 'the record is held, so it is not used', 'resolve the hold (its reasons are listed)', BK),
 'NO_APPROVED_CHANGE_REFERENCE': (B, 'the order amendment names no approved change', 'link the approved variation', PM),
 'NO_APPROVED_REGISTER': (B, 'there is no approved source-authority register, so the field cannot be trusted; a reviewer cannot clear it', 'set up and approve the source-authority register', AP),
 'NO_AUTHORITY_RULE': (B, 'the register has no rule for this field; a reviewer cannot clear it', 'add a rule for the field to the register', AP),
 'NO_BUDGET_FOR_CODE': (B, 'this cost code has no budget line', 'add a budget line, or move the cost to the right code', PM),
 'NO_CASH_MARGIN_EVIDENCE': (B, 'security face value is not collateral; no cash margin or fee data is held, so carrying cost cannot be assessed', 'supply the cash margin or fee records', FN),
 'NO_COST_CODES': (B, 'there are no cost codes, so the forecast cannot be built', 'import the budget or the cost-code list', PM),
 'NO_COST_TO_COMPLETE_INFORMATION': (B, 'there is no cost-to-complete information', 'enter a forecast', PM),
 'NO_DECLARED_LINE': (B, 'the forecast has no line for this cost code', 'add a forecast line for the code', PM),
 'NO_EXPECTED_RELEASE_DATE': (B, 'the retention has no expected release date', 'enter the expected release date', FN),
 'NO_FACILITY_STATEMENT': (B, 'there is no facility statement, so carrying cost cannot be assessed', 'import the facility statement', FN),
 'NO_FORECAST_VERSION': (B, 'no forecast version is in the data', 'import a forecast', PM),
 'NO_HEADER': (B, 'the import file has no header row', 'add the header row and import again', BK),
 'NO_RECEIVABLES_DATA': (B, 'client invoices, certificates and receipts are not held, so overdue receivables cannot be assessed', 'supply the receivables data once its way in is built (E13 to E15)', FN),
 'NO_RECONCILIATION_STATE': (B, 'the record has no reconciliation state, so it is held', 'have the record reconciled (the intake does this when it runs)', BK),
 'NO_SUPPRESSION_WINDOW_CONFIGURED': (B, 'the quiet period for notifications is not set', 'set it in setup', PM),
 'NUL_BYTE': (B, 'the file holds binary content', 'export the file again as text', BK),
 'OUTSIDE_PERIOD': (I, 'the record falls outside the period assessed', 'none', '-'),
 'OUT_OF_RANGE': (B, 'a value is outside the accepted range; the row is rejected', 'correct the value and import again', BK),
 'PAYMENT_EXCEEDS_INVOICE': (B, 'payments against the invoice add up to more than it; all are held', 'correct the payments or the invoice reference', BK),
 'PAYMENT_LIMIT_UNCHECKED': (I, 'the invoice total is unknown, so the payment limit is not checked', 'none; or complete the invoice', BK),
 'PAYMENT_TARGET_NOT_VISIBLE': (B, 'the invoice the payment names has not arrived; the payment is held', 'import the invoice, or correct the reference', BK),
 'PERCENT_COMPLETE_IS_COST_TO_COST_ON_THE_FORECAST_FINAL_COST': (I, 'percent complete is cost to date over forecast final cost', 'none', '-'),
 'POLICY_NOT_APPROVED': (B, 'the financial settings are not approved, so the figure is at most provisional', 'have the financial settings approved', AP),
 'POLICY_NOT_PINNED': (B, 'no financial settings are in force, so the figure cannot be assessed', 'set up and approve the financial settings', AP),
 'PORTFOLIO_BOUNDARY_APPLIED': (I, 'some projects that bought the material are outside what the viewer may see, so no portfolio comparison', 'none', '-'),
 'PO_COST_CODE_MISMATCH': (B, 'the invoice\'s cost code differs from its order\'s; the invoice is held', 'correct the cost code on the invoice or the order', BK),
 'PO_NOT_VISIBLE': (B, 'the order the record names has not arrived; the record is held', 'import the order, or correct the reference', BK),
 'PO_PROJECT_MISMATCH': (B, 'the invoice\'s project differs from its order\'s; the invoice is held', 'correct the project on the invoice or the order', BK),
 'PO_STATUS_MAP_NOT_CONFIGURED': (B, 'purchase-order statuses are not set up', 'set up the purchase-order statuses: map each of your order statuses to committed, draft, cancelled or closed', FN),
 'PO_STATUS_UNKNOWN': (B, 'the order has no status, so it is left out of commitments', 'enter the order status', BK),
 'PO_STATUS_UNMAPPED': (B, 'the order\'s status is not in the status settings, so it is left out', 'add the status to the purchase-order status settings', FN),
 'PO_SUPPLIER_MISMATCH': (B, 'the invoice\'s supplier differs from its order\'s; the invoice is held', 'correct the supplier on the invoice or the order', BK),
 'PROJECT_UNKNOWN': (B, 'the run names a project that is not stored', 'import the project, or choose another', PM),
 'PROJECT_UNKNOWN_OR_AMBIGUOUS': (B, 'the record\'s project cannot be told, so it is left out', 'add or correct the project reference', BK),
 'PROMOTED_BY_REVIEW': (I, 'a reviewer cleared the record for use', 'none', '-'),
 'PROMOTION_CANNOT_CLEAR': (B, 'a reviewer cannot waive this hold; it needs new evidence', 'supply the new evidence named', BK),
 'PROPOSAL_CHANGED': (P, 'the proposal on record cannot be identified', 'propose the action again', 'the person acting'),
 'QUANTITY_INVALID': (B, 'the quantity is not valid', 'correct the quantity', CM),
 'QUANTITY_NOT_POSITIVE': (B, 'the quantity is zero or missing', 'enter the quantity', CM),
 'QUOTE_TEXT_UNVERIFIED': (B, 'the quote\'s specification text is not verified', 'verify the reading against the quote', CM),
 'RAGGED_ROW': (B, 'a row has the wrong number of cells; it is rejected', 'fix the row and import again', BK),
 'RAISED_AFTER_AS_OF': (I, 'the variation was raised after the assessment date, so it is not counted', 'none', '-'),
 'RATE_IS_A_POLICY_PROXY_NOT_AN_EVIDENCED_FACILITY_RATE': (I, 'carrying cost uses the settings\' rate, not an evidenced facility rate', 'import the facility statement for an evidenced rate', FN),
 'RATE_ONLY_FOR_DUTY': (I, 'this rate is used only for duty', 'none', '-'),
 'RATIONALE_REQUIRED': (P, 'this change of status must record why', 'record the reason', 'the person acting'),
 'RECOGNITION_METHOD_NOT_CONFIGURED': (B, 'the revenue recognition method is not set', 'set it in setup', FN),
 'RECORD_MISSING': (S, 'a record a stored run needs is missing', 'none for the builder', SU),
 'RECORD_NO_LONGER_COUNTED': (I, 'a record counted before is no longer counted, so the movement is not explained', 'check why (held, corrected or replaced)', BK),
 'REFERENCE_BASIS_UNRECORDED': (I, 'the order rate\'s delivery basis and inclusions are not recorded', 'none; it is a reference only', '-'),
 'REFERENCE_ONLY': (I, 'an order rate is a reference, not an offer', 'none', '-'),
 'REJECTED_BY_REVIEW': (I, 'a reviewer rejected the record', 'none, or send a corrected record', BK),
 'RELEASED_AND_RECEIVED': (I, 'the retention was released and the money received', 'none', '-'),
 'RELEASED_PER_LEDGER_CASH_RECEIPT_NOT_EVIDENCED': (B, 'the ledger says released but no bank receipt is held', 'import the bank receipt', FN),
 'RELEASE_REVIEW_DUE': (B, 'the release date has passed with retention still withheld: a review prompt, not an entitlement', 'review whether release is due and, if so, claim it', FN),
 'REQUIRED_MISSING': (B, 'a required cell is blank; the row is rejected', 'fill the cell and import again', BK),
 'REQUIREMENT_UNAPPROVED': (B, 'the specification requirement is not approved by a person', 'have the requirement approved', 'the specification owner'),
 'RESIDUAL_NOT_ATTRIBUTED': (I, 'part of the cost movement cannot be attributed to a code', 'check the cost records', BK),
 'RETENTION_EVENTS_INCONSISTENT': (B, 'the retention events do not agree with each other', 'correct the retention events', FN),
 'RETENTION_POSITION_CANNOT_BE_ASSESSED': (B, 'the retention position cannot be assessed', 'resolve what stops it (listed with it)', FN),
 'REVENUE_NOT_POSITIVE': (B, 'revenue is zero or negative, so the margin cannot be assessed', 'check the contract value and variations', CM),
 'REVENUE_RECORD_AMOUNT_CHANGED_WITHOUT_RECORDED_REASON': (B, 'a revenue record changed amount with no recorded reason', 'record the reason for the change', CM),
 'REVENUE_RECORD_NO_LONGER_COUNTED': (I, 'a revenue record counted before is no longer counted', 'check why', CM),
 'REVISION_INVALID': (S, 'a revision label could not be read by the authority check', 'none for the builder', SU),
 'REVISION_UNPARSED': (B, 'the revision label could not be read', 'use a revision label APG can read', BK),
 'ROLE_REQUIRED': (P, 'this action needs a particular role', 'have a person with the role do it', 'the person acting'),
 'RUN_DOES_NOT_VERIFY': (S, 'a stored run does not verify', 'none for the builder', SU),
 'RUN_IS_FOR_A_DIFFERENT_PROJECT_OR_DATE': (P, 'the run is for a different project or date', 'choose the right run', PM),
 'RUN_IS_NOT_A_FORECAST_MADE_FOR_THIS_SCENARIO': (P, 'the run was not made for this scenario', 'choose the scenario\'s run', PM),
 'RUN_NOT_FOUND': (S, 'the run named is not stored', 'none for the builder', SU),
 'SCAN_INFECTED': (B, 'the file was marked unsafe by the scanner', 'send a clean copy of the file', BK),
 'SCAN_REQUIRED': (S, 'the file has not been scanned yet', 'none for the builder; wait', SU),
 'SCENARIO_IS_AUTHORITATIVE_WITHOUT_PROMOTION': (S, 'a scenario became authoritative without being promoted', 'none for the builder', SU),
 'SCENARIO_NAME_REQUIRED': (P, 'a scenario needs a name', 'name the scenario', PM),
 'SCENARIO_NEEDS_EXPLICIT_PROMOTION': (P, 'a scenario becomes the forecast only by explicit promotion', 'promote it explicitly if intended', PM),
 'SECONDARY_DISAGREES': (B, 'a second source disagrees with the authoritative value', 'confirm the right value', BK),
 'SECONDARY_IN_CONFLICT': (B, 'a second source conflicts with the primary record', 'confirm the right value', BK),
 'SECONDARY_WITHOUT_PRIMARY': (B, 'a second-source record has no primary record to compare with', 'import the primary record', BK),
 'SELF_APPROVAL': (P, 'a different person must approve the action', 'have another person approve it', AP),
 'SELF_APPROVAL_REFUSED': (P, 'the person who ran the calculation cannot adopt it', 'have another person adopt it', AP),
 'SEQUENCE_GAP': (B, 'a retention event is missing from the sequence', 'record the missing event', FN),
 'SERVICE_REQUIRED': (S, 'only the detection service may store detection runs', 'none for the builder', SU),
 'SEVERAL_FACILITIES': (B, 'there are several facility statements, so APG cannot tell which applies', 'confirm which facility applies', FN),
 'SIGN_CONVENTION': (B, 'an amount has the wrong sign for its field', 'correct the sign', BK),
 'SOURCE_NOT_PERMITTED': (I, 'a value came from a source the register does not permit, so it is ignored', 'none; or add the source to the register', AP),
 'SPEC_REGISTER_UNAPPROVED': (B, 'the specification register is missing or not approved, so nothing is rankable', 'set up and approve the specification register', 'the specification owner'),
 'STALE_APPROVAL': (P, 'the approval names an older version of the finding', 'read the finding again and approve the current version', AP),
 'STALE_PROPOSAL': (P, 'the proposal is out of date', 'propose the action again', 'the person acting'),
 'STORED_EVENTS_INCONSISTENT': (S, 'stored retention events are inconsistent', 'none for the builder', SU),
 'SUBSTITUTION_NEEDS_APPROVAL': (B, 'the offer is a different material, so it needs approval', 'have the substitution approved, or reject it', CM),
 'SUPERSEDING_FINDING_REQUIRED': (P, 'superseding a finding needs the finding that replaces it', 'name the replacing finding', 'the person acting'),
 'SUPPLIER_AMBIGUOUS': (B, 'the supplier matches more than one in the supplier list; the record is held', 'confirm which supplier it is', BK),
 'SUPPLIER_NEEDS_CONFIRMATION': (B, 'the supplier match needs a person to confirm it; the record is held', 'confirm the supplier', BK),
 'SUPPLIER_NOT_CHECKED': (I, 'the supplier was not checked against a supplier list', 'import the supplier list', BK),
 'SUPPLIER_RESOLVED_BY_PERSON': (I, 'a person confirmed the supplier', 'none', '-'),
 'SUPPLIER_UNRESOLVED': (B, 'the supplier is not in the supplier list; the record is held', 'add the supplier, or correct the name', BK),
 'SUPPLIER_UNVERIFIABLE_NO_MASTER': (B, 'there is no supplier list, so the supplier cannot be checked; the record is held', 'import the supplier list', BK),
 'SWITCHED_OFF_IN_POLICY': (I, 'the rule is switched off in the settings', 'none; switch it on if wanted', AP),
 'TARGET_INVOICE_AFTER_CUTOFF': (I, 'the invoice the credit names is after the cut-off', 'none', '-'),
 'TARGET_INVOICE_NOT_COUNTED': (B, 'the invoice the credit names is not counted, so the credit is not applied', 'resolve the invoice\'s hold', BK),
 'TEMPLATE_INVALID': (S, 'the import template is not valid', 'none for the builder', SU),
 'TIER_INVALID': (B, 'a price tier is not valid, so it is not used', 'correct the tier', CM),
 'TOO_MANY_ROWS': (B, 'the file has more rows than allowed', 'split the file', BK),
 'TRANSITION_NOT_ALLOWED': (P, 'this change of status is not allowed', 'choose an allowed next status', 'the person acting'),
 'UNEXPLAINED_MOVEMENT': (B, 'the forecast moved and the movement is not explained', 'record the reason for the movement', PM),
 'UNIT_INCOMPATIBLE': (B, 'the offer\'s unit cannot be converted to the requirement\'s, so it is not comparable', 'none, unless a conversion should be declared; then declare it', CM),
 'UNIT_MISMATCH': (B, 'orders are in a unit other than the demand\'s, so coverage cannot be assessed', 'correct the unit, or record the demand in the same unit', CM),
 'UNIT_UNVERIFIED': (B, 'the unit of the offer is not verified', 'verify the unit against the quote', CM),
 'UNKNOWN_DENOMINATOR': (S, 'a calculation was asked for with an unknown basis', 'none for the builder', SU),
 'UNKNOWN_STATUS': (S, 'an unknown finding status was named', 'none for the builder', SU),
 'VALUE_MISSING': (B, 'an optional value is missing; the record is used with a warning', 'enter the value if known', BK),
 'VARIATION_STATUS_MAP_NOT_CONFIGURED': (B, 'variation statuses are not set up', 'set up the variation statuses: map each of your variation statuses to approved, unapproved, disputed or rejected', CM),
 'VARIATION_STATUS_UNMAPPED': (B, 'the variation\'s status is not in the status settings, so it is left out', 'add the status to the variation status settings', CM),
 'VERIFICATION_NOT_AVAILABLE': (P, 'a realised outcome needs the Section 05 verification, which is not available', 'none yet', '-'),
 'TAX_BASIS_NOT_CONFIGURED': (B, 'the tax basis is not set, so revenue cannot be assessed', 'set the tax basis in setup', FN),
 'CTC_METHOD_NOT_CONFIGURED': (B, 'the cost-to-complete method is not set, so the forecast cannot be assessed', 'set the cost-to-complete method in setup', PM),
 'FFC_BASIS_NOT_CONFIGURED': (B, 'the forecast-final-cost basis is not set, so the forecast cannot be assessed', 'set the forecast basis in setup', FN),
 'A_COMPONENT_CANNOT_BE_ASSESSED': (B, 'a part of the forecast cannot be assessed, so the forecast final margin cannot be either', 'resolve what stops that part (its reasons are listed)', PM),
 'A_DEFINED_COMPONENT_CANNOT_BE_ASSESSED': (B, 'a part the cash-adjusted margin is defined to include cannot be assessed', 'resolve what stops that part (its reasons are listed)', FN),
 'A_FORECAST_CANNOT_BE_ASSESSED': (B, 'one of the two runs being compared cannot be assessed, or is not a forecast, so no movement bridge is built', 'resolve what stops that forecast, or compare two forecasts', PM),
 'AMOUNT_COMPARISON_ONLY': (I, 'R03 compares amounts only: invoice quantities and unit rates are not held', 'none', '-'),
 'CLEARED': (I, 'a reviewer cleared this hold', 'none', '-'),
 'ENCODING': (B, 'the import file is not in the expected text encoding; the file is rejected', 'export the file again in the encoding the template names', BK),
 'EXPIRED': (B, 'R07 compared an expired quote or reference, at weak strength', 'get a current quote or reference', CM),
 'FRESHNESS': (B, 'the offer, its exchange rate or its index is not fresh enough for this decision; an expired or future-dated quote is history only and cannot be ranked', 'get a current quote, exchange rate or index observation, as the limitations name', CM),
 'GATE': (B, 'the offer did not pass the comparability gate; the gate codes say why', 'act on the gate codes given with it', CM),
 'MISSING': (B, 'fields this M6 record needs are missing', 'enter the fields named', CM),
 'RECONCILIATION': (B, 'the record\'s reconciliation outcome does not allow its use', 'resolve the hold, or send a corrected record if a reviewer rejected it', BK),
 'STALE': (B, 'an input is older than the freshness limit set for it', 'supply a current one', PM),
 'TERMINAL': (P, 'a superseded finding is kept for audit and cannot change', 'none', 'the person acting'),
 'RECOGNISED_REVENUE_UNKNOWN': (P, 'the margin run named does not carry recognised revenue (for example a cash-adjusted margin, or a forecast margin), so no percentage is given', 'choose the margin run that carries this basis', 'the person asking'),
 'FORECAST_REVENUE_UNKNOWN': (P, 'the margin run named does not carry forecast revenue (for example a cash-adjusted or recognised margin), so no percentage is given', 'choose the margin run that carries this basis', 'the person asking'),
 'PERCENT_COMPLETE_RESTS_ON_A_FORECAST_THAT_IS_PROVISIONAL': (I, 'percent complete rests on a provisional forecast', 'resolve what makes the forecast provisional', PM),
}
# pieces the code joins into codes: each must expand to codes that have an entry above
EXPAND = {
 '_NOT_CONFIGURED': ['TAX_BASIS_NOT_CONFIGURED', 'VARIATION_STATUS_MAP_NOT_CONFIGURED', 'CTC_METHOD_NOT_CONFIGURED', 'FFC_BASIS_NOT_CONFIGURED', 'COST_SCOPE_NOT_CONFIGURED'],   # fin/revenue.py, fin/forecast.py: fld.upper() + '_NOT_CONFIGURED'
 '_UNKNOWN': ['RECOGNISED_REVENUE_UNKNOWN', 'FORECAST_REVENUE_UNKNOWN'],                     # fin/margins.py pct_figure: label + '_UNKNOWN', labels from fin/calc_records.py
 'PERCENT_COMPLETE_RESTS_ON_A_FORECAST_THAT_IS_': ['PERCENT_COMPLETE_RESTS_ON_A_FORECAST_THAT_IS_PROVISIONAL'],
 'COMPONENT_': ['COMPONENT_PROVISIONAL', 'COMPONENT_CANNOT_ASSESS'],     # fin/figure.py: 'COMPONENT_%s:%s' % (state.upper(), part)   # fin/margins.py: + state.upper(); a cannot_assess forecast stops earlier
}
# where each joined code is built (the scan sees only the piece)
EXPAND_SRC = {'TAX_BASIS_NOT_CONFIGURED': {'fin/revenue.py'}, 'VARIATION_STATUS_MAP_NOT_CONFIGURED': {'fin/revenue.py'}, 'CTC_METHOD_NOT_CONFIGURED': {'fin/forecast.py'},
              'FFC_BASIS_NOT_CONFIGURED': {'fin/forecast.py'}, 'COST_SCOPE_NOT_CONFIGURED': {'fin/forecast.py'}, 'RECOGNISED_REVENUE_UNKNOWN': {'fin/margins.py'},
              'FORECAST_REVENUE_UNKNOWN': {'fin/margins.py'}, 'PERCENT_COMPLETE_RESTS_ON_A_FORECAST_THAT_IS_PROVISIONAL': {'fin/margins.py'},
              'COMPONENT_PROVISIONAL': {'fin/figure.py'}, 'COMPONENT_CANNOT_ASSESS': {'fin/figure.py'}}
# upper-case strings that are not messages
NOT_CODE = {
 'AWAITING_': 'a prefix the code matches codes against', 'CONFLICT_': 'a prefix the code matches codes against',
 'RECOGNISED_REVENUE': 'a label joined into RECOGNISED_REVENUE_UNKNOWN', 'FORECAST_REVENUE': 'a label joined into FORECAST_REVENUE_UNKNOWN',
 'APG': 'the product name', 'AUD': 'a currency code', 'GST': 'a tax name', 'NFKC': 'a text normalisation form', 'T00': 'part of a time stamp',
}
RULE_ID = re.compile(r'(R0\dB?|D0\d|AGG|DEF|DLY|LAB|MP\d\d|MPD1)$')
# plain-language reasons (matched by their start); 'unknown: <kind>' is a figure's unknown input, 'exclude: <class>' an exclusion class,
# 'status: <word>' a status value, 'freshness: <state>' a state of ingest/freshness.py
TEXT = {
 'record not in the store': (B, 'R07: the quote or reference named in the comparable pair is not stored', 'import it, or correct the pair', CM),
 'purchase order has no unit rate': (B, 'R07: the reference order has no unit rate', 'enter the order\'s unit rate', BK),
 'currency %s: conversion is not done here': (I, 'R07: a quote not in AUD is left to M6', 'none', '-'),
 'ex-works quote with no freight': (B, 'R07: an ex-works quote has no freight, so a landed cost cannot be built', 'add the freight to the quote', CM),
 'delivery basis %r needs the landed-cost model': (I, 'R07: this delivery basis is left to M6', 'none', '-'),
 'is not usable (held, disputed or duplicate)': (B, 'R07: the quote or reference is held, disputed or a duplicate', 'resolve the hold', BK),
 'the declared pair names different materials': (B, 'R07: the comparable pair names two different materials', 'correct the pair', CM),
 'status %r is not mapped by the financial policy': (B, 'R04: the variation\'s status is not in the status settings', 'add the status to the variation status settings', CM),
 'status %r is not one of %s': (B, 'M6: an import check\'s status is not one of the allowed values', 'record the check with an allowed status', CM),
 'status %r maps to %s': (I, 'M6 coverage: an order whose status is not committed or closed is not counted', 'none, unless the status is wrong', BK),
 'invoice for': (B, 'R03: an invoice for the order is held, so the invoiced total may be higher', 'resolve the invoice\'s hold', BK),
 'held, disputed, undated or after the as-of date': (B, 'R09: the forecast line is held, disputed, undated or after the date', 'resolve the hold, or date the line', PM),
 'held': (B, 'R02: the order amendment is held', 'resolve the amendment\'s hold', BK),
 'not usable (': (B, 'AGG: the order is held', 'resolve the hold', BK),
 'undated or after the as-of date': (B, 'AGG: the order is undated, or dated after the assessment date', 'enter the order date if it is missing; a later order is assessed in a later run', BK),
 'a grouping key is missing': (B, 'AGG: a field the split-order check groups by is missing', 'enter the field named', BK),
 'hours are not a plain non-negative decimal': (B, 'LAB: the timesheet hours are not a valid number', 'correct the hours', PM),
 'fewer than %d complete weeks with both hours and output': (B, 'LAB: not enough complete weeks of hours and output', 'record hours and output for the missing weeks', PM),
 'the windows are not consecutive weeks': (B, 'LAB: a week is missing or incomplete', 'complete the missing week', PM),
 'the unit of measure changes inside the windows': (B, 'LAB: the output unit changes between weeks', 'use one unit for the work package', PM),
 'a window has no output or no hours': (B, 'LAB: a period has hours but no output, or output but no hours', 'record the missing hours or output', PM),
 'subcontractor or trade is not recorded': (B, 'DEF: the defect has no subcontractor or trade', 'record the subcontractor and trade', PM),
 'no evidenced need date': (B, 'R08: the plant hire has no need date', 'enter the date the plant is needed until', PM),
 'no end date: an open delay': (B, 'DLY: the delay has no end date', 'enter the end date, or close the delay', PM),
 'starts after the as-of date or ends before it starts': (B, 'DLY: the delay\'s dates are wrong, or it starts after the assessment date', 'correct the dates if they are wrong', PM),
 'uncovered demand but no rankable current quote': (B, 'MP03: demand is not covered and no current quote can be ranked', 'get a comparable current quote', CM),
 'no retention ledger': (B, 'R05: there is no retention ledger for the project', 'import the retention ledger', FN),
 '%d order(s) with deliveries against a minimum of %d': (I, 'MP08: too few orders with deliveries to draw a conclusion', 'none', '-'),
 'mkt_policy': (B, 'M6: no procurement settings are in force, so nothing is assessed', 'set up and approve the procurement settings', AP),
 'no record of this check': (B, 'M6: a critical import check is not recorded', 'record the check, with the person, date and evidence', CM),
 'recorded as unresolved': (B, 'M6: an import check is recorded as unresolved', 'resolve the check', CM),
 'recorded as %s without %s': (B, 'M6: an import check lacks the person, the date or the evidence', 'add what is missing to the check', CM),
 'no usable %s rate on or before %s': (B, 'M6: no exchange rate is held for the currency and date', 'import a current exchange rate', CM),
 'tax treatments differ (%s and %s) and no GST rate is configured': (B, 'MP09: the quote and the order have different tax bases and the GST rate is not set', 'set the GST rate in the procurement settings', CM),
 'no approved register': (B, 'M6: the specification register is not approved', 'set up and approve the specification register', 'the specification owner'),
 'no declared conversion from %s to %s': (B, 'M6: no unit conversion is declared between the two units', 'declare the conversion in the specification register', 'the specification owner'),
 'a unit is not recorded': (B, 'M6: the unit is not recorded', 'record the unit', CM),
 'fewer than two rankable offers have a complete landed cost': (B, 'buy timing: fewer than two comparable offers have a complete landed cost', 'get another comparable quote, or complete the landed costs', CM),
 'no explicit future-price paths are configured': (I, 'buy timing: no future-price paths are set, so no rising-price scenario is built', 'set price paths in the procurement settings, if wanted', CM),
 'scenarios.context_points is not configured': (B, 'buy timing: the market-context setting is not set', 'set it in the procurement settings', CM),
 'scenarios.stage is not configured': (B, 'buy timing: the staged-purchase setting is not set', 'set it in the procurement settings', CM),
 'priced per %s but needed per %s': (B, 'buy timing: the quote is priced in a different unit from the need, so no purchase scenario is built', 'declare the unit conversion, or get a quote in the needed unit', CM),
 'the latest order date that still meets %s': (I, 'buy timing: the latest order date has passed for the required date', 'none; plan for the delay', PM),
 'history of an index, not a price': (I, 'buy timing: an index is shown as history only', 'none', '-'),
 'a larger tier lowers the unit rate but the total paid is': (I, 'landed cost: a larger price tier changes the total paid', 'none', '-'),
 'quoted rate %s %s%s': (I, 'landed cost: the quoted rate, as a component', 'none', '-'),
 'unit rate paid on the order': (I, 'landed cost: an order rate used as a reference', 'none', '-'),
 'observed performance on these records': (I, 'MP08: supplier performance is observed, not predicted', 'none', '-'),
 'the condition was detected again with changed evidence': (I, 'a finding reopened because the condition came back with changed evidence', 'review the finding', PM),
 'a range, not a total': (I, 'the portfolio total is a range, or a sum of separate estimates and records; not a verified figure', 'none', '-'),
 '%d usable observations, %d wanted': (I, 'buy timing: not enough market observations for context', 'none', '-'),
 'the quote records no unit and no verified unit reading exists': (B, 'M6: the offer\'s unit is inferred from the material master, not verified', 'record and verify the unit from the quote', CM),
 'conversion declared, but the offered unit is inferred, not verified': (B, 'M6: a conversion exists, but the offer\'s unit is not verified', 'verify the unit reading from the quote', CM),
 'the blocking facts no longer exist': (I, 'a hold cleared because its cause no longer exists', 'none', '-'),
 'the rule ran and did not raise this condition': (I, 'a finding was not raised again; a person decides whether it is resolved', 'decide whether the finding is resolved', PM),
 'approval_invalidated_evidence_changed': (P, 'the evidence changed after approval, so the approval no longer stands', 'approve again', AP),
 'after_cutoff': (I, 'a credit dated after the cut-off is not yet applied', 'none', '-'),
 'a date written as text is not interpreted by the stand-in': (P, 'document capture: the stand-in reader does not interpret dates written as text', 'the verifier checks the date against the document', 'the verifier'),
 'decimal point or thousands separator?': (P, 'document capture: a number is ambiguous', 'the verifier checks the number against the document', 'the verifier'),
 'letters inside a number': (P, 'document capture: a number holds letters', 'the verifier checks the number against the document', 'the verifier'),
 'more than two decimals': (P, 'document capture: a money value has more than two decimals', 'the verifier checks the value against the document', 'the verifier'),
 'not readable as a dollar amount': (P, 'document capture: a value is not readable as a dollar amount', 'the verifier enters the value from the document', 'the verifier'),
 'not readable as a whole number': (P, 'document capture: a value is not readable as a whole number', 'the verifier enters the value from the document', 'the verifier'),
 'budget lines carry different revision labels': (B, 'M4 budget: budget lines from different revisions are mixed', 'import one complete budget revision', PM),
 'contract summary of approved variations (': (B, 'M4 revenue: the contract\'s approved-variations total differs from the variation register', 'reconcile the contract summary with the variation register', CM),
 'variation register approved total (': (B, 'M4 revenue: the variation register differs from the contract summary', 'reconcile the two', CM),
 'project master contract value': (B, 'M4 revenue: the project master contract value differs from the contract record', 'correct one of them', CM),
 'differs from the project master contract value': (B, 'M4 revenue: the contract record differs from the project master contract value', 'correct one of them', CM),
 'several different versions of the contract record': (B, 'M4 revenue: conflicting versions of the contract record', 'confirm which version is right', CM),
 'several different versions of the variation': (B, 'M4 revenue: conflicting versions of a variation', 'confirm which version is right', CM),
 'several different versions of the retention ledger record': (B, 'M4 retention: conflicting versions of the retention ledger', 'confirm which version is right', FN),
 'event sequence breaks a rule at seq %d: %s': (B, 'M4 retention: the retention events break the allowed sequence', 'correct the events', FN),
 'variation is disputed': (I, 'M4 revenue: the variation is recorded as disputed, so it is kept out of secured revenue', 'none; it is listed beside the figure', '-'),
 'derived from budget less actual; budget unchanged': (I, 'forecast movement: explained by actual cost against an unchanged budget', 'none', '-'),
 'newly counted:': (I, 'forecast movement: a record newly counted', 'none', '-'),
 'variation newly approved:': (I, 'forecast movement: a variation newly approved', 'none', '-'),
 'rounding of the policy tax conversion': (I, 'forecast movement: rounding of the tax conversion', 'none', '-'),
 'unknown: no_data': (B, 'M4: a record or field a figure needs is not held; the figure names it', 'supply the record or field named', BK),
 'unknown: method_not_configured': (B, 'M4: a setting the figure needs is not set; it names the open decision', 'make that setting in setup', FN),
 'unknown: stale': (B, 'M4: an input is older than its freshness limit', 'supply a current one', PM),
 'unknown: unmapped': (B, 'M4: a status is not in the status settings', 'add the status to the status settings', FN),
 'unknown: held': (B, 'M4: an invoice against an order is not resolved, so how much of the commitment it uses is unknown', 'resolve the invoice\'s hold', BK),
 'unknown: not_obtained': (B, 'M4: no evidenced facility rate is held; the settings\' rate is used as a proxy', 'import the facility statement', FN),
 'unknown: invalid': (B, 'M4: a cost-to-complete entry is not valid', 'correct the forecast line for the code', PM),
 'exclude: after_cutoff': (I, 'a record dated after the cut-off is not counted yet', 'none', '-'),
 'exclude: duplicate_delivery': (I, 'a repeat delivery of the same record is counted once', 'none', '-'),
 'exclude: not_counted': (B, 'a record left out and not counted: a forecast line the method does not use, or a credit whose invoice is not counted; the figure is provisional', 'act on the code given with it (for a credit, resolve its invoice)', BK),
 'exclude: held': (B, 'a record is held, so it is left out of the figure; its codes say why', 'resolve the hold', BK),
 'exclude: disputed': (B, 'conflicting versions of a record, so it is left out of the figure', 'confirm which version is right', BK),
 'exclude: unattributed': (B, 'a record whose project cannot be told is left out', 'add or correct the project reference', BK),
 'exclude: unknown_value': (B, 'a record with an unknown status or amount is left out; its code says which', 'act on the code given with it', BK),
 'status: cannot_assess': (B, 'M6 coverage or buy timing cannot be assessed; the reason is given', 'act on the reason given', CM),
 'status: not_configured': (B, 'buy timing: a scenario setting is not set', 'set it in the procurement settings', CM),
 'status: not_available': (I, 'buy timing: a scenario is not available; the reason is given', 'act on the reason given', CM),
 'status: insufficient_history': (I, 'buy timing: not enough market history for context', 'none', '-'),
 'status: insufficient_offers': (B, 'M6: fewer than two comparable offers, so no definitive ranking', 'get another comparable quote', CM),
 'status: no_offers': (B, 'M6: no offers for the requirement', 'get quotes', CM),
 'status: unverified': (B, 'M6: the offer cannot be verified against the specification', 'verify the readings, or approve the register or requirement', CM),
 'status: unknown': (B, 'M6: the offer cannot be checked: an attribute is not known, the material is not in the specification register, or the register is not approved', 'act on the reason given (record the attribute, add the material, or approve the register)', CM),
 'status: incompatible': (B, 'M6: the units cannot be converted', 'declare a conversion if one applies', CM),
 'status: fail': (I, 'M6: the offer fails a required attribute', 'none, unless the quote or specification is wrong', CM),
 'status: indicative': (I, 'M6: the ranking is indicative, not definitive', 'act on the reasons given', CM),
 'status: unresolved': (B, 'M6: an import check is unresolved', 'resolve the check', CM),
 'status: held': (B, 'a record is held; its reasons are listed', 'resolve the hold', BK),
 'status: rejected': (I, 'a reviewer rejected the record', 'send a corrected record, if needed', BK),
 'status: pending_reconciliation': (B, 'a credit waits for reconciliation', 'resolve the invoice it is linked to', BK),
 'status: file_rejected': (B, 'the import file was rejected; the reasons are listed', 'fix the file and import it again', BK),
 'status: not_ingested': (B, 'APG refused to read a stored file; its code says why (not scanned yet, unsafe, damaged, not found)', 'act on the code given with it', BK),
 'status: refused': (S, 'an import job was refused because no tenant could be established (an authentication fault)', 'none for the builder', SU),
 'status: missing': (B, 'landed cost: a required component is missing, so the cost is "at least"', 'add the missing component', CM),
 'status: partial': (S, 'a scheduled monitoring run partly failed', 'none for the builder', SU),
 'status: failed': (S, 'a scheduled monitoring run failed', 'none for the builder', SU),
 'freight is in %s and cannot be converted': (B, 'landed cost: the freight is in a currency that cannot be converted', 'import a current exchange rate for that currency', CM),
 'required for this kind of purchase; nothing in the quote or the assumptions gives it': (B, 'landed cost: a required component is not given by the quote or the assumptions', 'add the component to the quote or the landed-cost assumptions', CM),
 'duty is a share of the purchase cost, which is unknown': (B, 'landed cost: duty cannot be worked out because the purchase cost is unknown', 'complete the purchase cost', CM),
 'assumption is in %s and cannot be converted': (B, 'landed cost: an assumption is in a currency that cannot be converted', 'import a current exchange rate for that currency', CM),
 'assumption set by %s': (I, 'landed cost: a component taken from a signed assumption', 'none', '-'),
 'stated on the quote': (I, 'landed cost: a component stated on the quote', 'none', '-'),
 'the %s basis includes it': (I, 'landed cost: the delivery basis includes this component', 'none', '-'),
 'not required by the policy and not stated': (I, 'landed cost: a component not required and not stated', 'none', '-'),
 'scenarios are not recommendations and no offer is chosen': (I, 'buy timing: scenarios are not recommendations', 'none', '-'),
 'status: assumed': (I, 'landed cost: a component comes from an assumption, not the quote', 'none; check the assumption', CM),
 'status: no_uncovered_demand': (I, 'buy timing: no uncovered demand, so no scenario is needed', 'none', '-'),
 'status: no_rankable_offer': (B, 'buy timing: no offer can be ranked, so no scenario is built', 'get a comparable current quote', CM),
 'status: no_scenario_built': (I, 'buy timing: no scenario could be built; the reasons are given', 'act on the reasons given', CM),
 'the condition was detected again after resolution': (I, 'a resolved finding reopened because the condition came back', 'review the finding', PM),
 'no overlapping amounts found among the quantified findings': (I, 'the portfolio total is a sum of separate estimates and records, not a verified figure', 'none', '-'),
 'unquantified: the variation has no recorded value': (B, 'R04: the variation has no recorded value, so no amount can be stated', 'record the variation\'s value', CM),
 'unquantified: no value is recorded for the instructed work': (B, 'R04B: no value is recorded for the instructed work', 'record the value of the work', CM),
 'unquantified: hourly rates are missing or zero': (B, 'LAB: hourly rates are missing or zero, so the cost of the lower output cannot be stated', 'enter the hourly rates on the timesheets', PM),
 'unquantified: no rework cost is recorded': (B, 'DEF: no rework cost is recorded on the defects', 'record the rework costs', PM),
 'unquantified: the surplus is delivered but no order rate is available': (B, 'MP04: no order rate to value the surplus', 'enter the order\'s unit rate', BK),
 'unquantified: an order amount is missing': (B, 'MP05: an order amount is missing', 'enter the order amount', BK),
 'unquantified: no quote exists to cost the purchase': (B, 'MP03: no quote to cost the purchase', 'get a quote', CM),
 'unquantified: a missing current quote has no amount': (I, 'MP01: a missing current quote has no amount until a purchase depends on it', 'none', '-'),
 'unquantified: holding cost needs a documented counterfactual': (I, 'DLY: holding cost needs a documented counterfactual, which is not held', 'none until programme data exists (E47 to E50)', '-'),
 'unquantified: the quantity to be bought is not known here': (I, 'the difference is stated per unit only, because the quantity is not known', 'none', '-'),
 'unquantified: no demand is left uncovered': (I, 'MP09: no uncovered demand to apply the difference to', 'none', '-'),
 'unquantified: a broken link is a reporting risk, not a loss': (I, 'the finding is a reporting risk, not a loss', 'none', '-'),
 'unquantified: an expiry has no financial amount': (I, 'R06: an expiry has no amount until a consequence is evidenced', 'none', '-'),
 'unquantified: held records are a reporting risk, not a loss': (I, 'D01, D02, MPD1: held records are a reporting risk, not a loss', 'none', '-'),
 'unquantified: a missing figure is not a loss': (I, 'a missing figure is not a loss', 'none', '-'),
 'unquantified: no loss is asserted': (I, 'AGG: the finding is about an approval threshold, not an amount lost', 'none', '-'),
 'unquantified: a reduction in forecast cost is not a loss': (I, 'R09: the finding is that the reduction is unexplained', 'none', '-'),
 'unquantified: scenario outcomes depend on explicit assumptions': (I, 'buy timing: scenario outcomes are not a forecast', 'none', '-'),
 'unquantified: an unresolved check has no amount': (I, 'MP07: an unresolved check has no amount; it blocks a definitive comparison', 'none', '-'),
 'unquantified: performance has no amount': (I, 'MP08: performance has no amount until a consequence is evidenced', 'none', '-'),
 'unquantified: stale market data has no amount': (I, 'MP01: stale market data has no amount', 'none', '-'),
 'unquantified: the apparent difference of': (I, 'MP02: the apparent difference is not a saving, because the offers are not like-for-like', 'none', '-'),
 'no usable quote for this requirement': (B, 'M6: no usable quote for the requirement', 'get a quote, or resolve the held one', CM),
 'docket %s records no accepted quantity': (I, 'M6 coverage: a delivery docket has no accepted quantity, so its delivered quantity is used', 'record the accepted quantity, if known', PM),
 'docket %s is held (%s) and is not counted': (B, 'M6 coverage: a delivery docket is held and not counted', 'resolve the docket\'s hold', BK),
 'no usable reference rate:': (B, 'MP06: no usable reference exchange rate', 'import a current exchange rate', CM),
 'the quote states no usable FX rate': (I, 'MP06: the quote states no exchange rate, so its own conversion cannot be checked', 'none, or ask the supplier for the rate used', CM),
 'converting at the reference rate instead of the stated rate': (I, 'MP06: the quote\'s exchange rate differs from the reference by more than the tolerance', 'review the quote\'s rate', CM),
 'the latest reference rate (%s) is %d days old': (B, 'MP06: the latest reference exchange rate is too old', 'import a current exchange rate', CM),
 'the rate stated on the quote (%s) is dated %s': (I, 'MP06: the rate stated on the quote is too old', 'ask the supplier for a current rate', CM),
 'lead time is not stated': (B, 'buy timing: the quote states no lead time, so the delivery or latest order date cannot be worked out', 'record the lead time from the quote', CM),
 'scenarios.lead_time_variation_days is not configured': (B, 'buy timing: the lead-time variation setting is not set', 'set it in the procurement settings', CM),
 'payment terms are not recorded': (B, 'buy timing: no payment terms are recorded, so payment is taken at delivery', 'record the quote\'s payment terms', CM),
 'payment terms %r cannot be read as a number of days': (B, 'buy timing: the payment terms cannot be read, so payment is taken at delivery', 'correct the payment terms', CM),
 'the quote %s lapses on %s, before the order date %s': (B, 'buy timing: the quote lapses before the order date, so the price is modelled, not an offer', 'get a new quote', CM),
 'the minimum order or pack size means %s units more than needed are bought': (I, 'buy timing: a minimum order or pack size means buying more than needed', 'none', '-'),
 'no financing rate or day-count basis is configured': (B, 'buy timing: the financing settings are not set, so working-capital cost is not assessed', 'set the financing rate and day count in the procurement settings', CM),
 'no storage rate is configured': (B, 'buy timing: no storage rate is set, so storage cost is not assessed', 'set the storage rate in the procurement settings', CM),
 'the deposit %r basis points is outside 0 to 10000': (B, 'buy timing: the deposit is not a valid percentage, so no deposit is assumed', 'correct the deposit on the quote terms', CM),
 'the deposit %r cannot be read as basis points': (B, 'buy timing: the deposit cannot be read, so no deposit is assumed', 'correct the deposit on the quote terms', CM),
 'material %s is not in the specification register': (B, 'M6: the material is not in the specification register, so the offer cannot be verified or ranked', 'add the material to the specification register', 'the specification owner'),
 'different product families (%s and %s)': (I, 'M6: the offer is a different product family from the requirement', 'none, unless the family is wrong', CM),
 'the quote text is not verified against the register': (B, 'M6: the quote text is not verified, so attributes pass only on the catalogue code', 'verify the quote readings', CM),
 'attribute %s: %s offered against %s required': (I, 'M6: an offered attribute does not meet the requirement', 'none, unless the reading is wrong', CM),
 'attribute %s: the verified reading (%s) disagrees with the catalogue': (B, 'M6: a verified reading disagrees with the catalogue specification', 'check the reading and the catalogue', CM),
 'attribute %s cannot be assessed (nothing usable offered)': (B, 'M6: nothing usable is recorded for a required attribute', 'record the attribute from the quote', CM),
 '%d orders with deliveries (minimum %d)': (I, 'MP08: the number of orders with deliveries, against the minimum', 'none', '-'),
 '%s expired %d days before the as-of day': (B, 'M6: a quote or observation has expired; it is history only, not a current basis', 'get a current quote or observation', CM),
 '%s is dated after the as-of day: not yet usable': (I, 'M6: a quote or observation is dated after the assessment date', 'none; or correct the date', CM),
 '%s is %d days old against a limit of %d days': (B, 'M6: a quote, exchange rate or index observation is older than the freshness limit for this decision', 'get a current one', CM),
 '%s is unavailable': (B, 'M6: no usable quote, rate or observation on or before the assessment date', 'supply a current one', CM),
 'status: dead_letter': (S, 'an import job failed repeatedly and was set aside', 'none for the builder', SU),
 'status: unquantified': (I, 'the finding has no amount; it says why', 'supply what it names, if wanted', PM),
 'status: over_ordered': (I, 'MP04: more ordered than the demand', 'review the order', PM),
 'status: uncovered': (I, 'M6: demand not yet covered by orders', 'none; a purchase decision is due', PM),
 'freshness: stale': (B, 'an input is older than its freshness limit (ingest/freshness.py, which no stage 1 run calls yet)', 'supply a current one', PM),
 'freshness: missing': (B, 'an input the decision needs has never arrived', 'supply it', BK),
 'freshness: unconfigured': (B, 'no freshness limit is set for this use, so it cannot be assessed (ingest/freshness.py, which no stage 1 run calls yet; its settings record is to be designed)', 'set the freshness limit, once its setup exists', AP),
 'freshness: future_dated': (B, 'an input is dated after the assessment date', 'correct the date if it is wrong', BK),
 'freshness: cannot_assess': (B, 'the decision cannot be assessed for freshness; the inputs say why', 'act on the inputs\' states', PM),
 'freshness: qualified': (I, 'the decision is qualified because an input is stale', 'supply a current input', PM),
}
NOT_TEXT = {k: 'a normal state, not a gap' for k in ('status: queued_again', 'status: approved', 'status: included_in_rate', 'status: stated', 'status: not_required', 'status: scenarios', 'status: ok', 'status: same', 'status: converted', 'status: covered', 'status: definitive', 'status: detected', 'status: estimate', 'status: evaluated', 'status: history',
            'status: ingested', 'status: known', 'status: open', 'status: promoted', 'status: proposed', 'status: quantified', 'status: scenario_only', 'status: succeeded',
            'freshness: fresh', 'freshness: eligible')}
NOT_TEXT['notice'] = 'the text of an R04B finding: a finding, not a gap'
STATES = {
 'cannot_assess': (B, 'the rule or figure cannot be assessed; the reason codes say why', 'act on the reason codes given with it', '-'),
 'not_configured': (B, 'a setting the rule needs is missing; it is named', 'set the setting named, in setup', AP),
 'disabled': (I, 'the rule is switched off in the settings', 'none; switch it on if wanted', AP),
 'provisional': (B, 'a figure is provisional; its reasons are listed with it', 'act on the reasons given', '-'),
}
# refusals raised to a person taking an action, and integrity errors, by the class that raises them
RAISE = {'MissingParam': B, 'FileNotFound': S, 'IntegrityError': S, 'ScanInfected': S, 'ScanRequired': S, 'AuthorityError': P, 'PolicyError': P, 'DetPolicyError': P, 'MktPolicyError': P, 'err': P, '_refuse': P, 'call': P, 'SavingNotVerified': P,
         'NotPermitted': S, 'PayloadInvalid': S, 'EventError': S, 'FigureError': S, 'SignalError': S, 'IngestError': S}
RAISE_TEXT = {'file larger than the store allows': B, 'file name must be 1-200 characters': B}
RAISE_MEANING = {('MissingParam', '(no fixed text: self._path + str(k))'): ('M6: a procurement setting is missing; it is named by its dotted path, and only the analysis that needs it stops', 'set the setting named, in the procurement settings', CM)}
# silent today: no message is given (defect candidates; the owner decided on 2026-11-12 that each gets one)
SILENT = [
 ('DC-1', 'R04B', 'an instruction linked to any stored variation is silent, whatever that variation\'s state (held, quarantined, conflicting or rejected included)', 'the client rejected the variation for this work (or: not assessed, the variation is on hold)', 'record the outcome: disputed, at own cost, resubmitted, withdrawn (or approve, reject or correct the variation)'),
 ('DC-2', 'LAB', 'a missing overtime is counted as 0', 'not assessed: overtime unknown', 'enter the overtime hours (0 if none)'),
 ('DC-3', 'M6 last rate paid', 'not silent: an uncaught error; a null purchase-order status map stops the whole M6 run', 'purchase-order statuses not set up', 'set up the purchase-order statuses'),
 ('DC-4', 'MP05, MP08, MP10, MP02 reference, MP09', 'without the status map MP05, MP08 and MP10 evaluate nothing and nothing says so; MP02 still evaluates but loses its last-paid reference; MP09 finds no opportunity, and drops one unstated when the GST rate is not set', 'not assessed: purchase-order statuses not set up; GST rate not set', 'set up the purchase-order statuses; set the GST rate'),
 ('DC-5', 'MP01', 'a watched material with no usable quote raises no signal', 'no current quote', 'get a quote, or resolve the held one'),
 ('DC-6', 'M6 comparison', 'a demand line with no positive quantity is reported nowhere; an unusable demand line or specification requirement is left out of the requirements', 'not assessed: quantity zero or unusable', 'enter the quantity needed'),
 ('DC-7', 'M4 commitments, R02', 'a held variation mapped to approved counts as approved', 'not assessed: the linked variation is on hold', 'approve, reject or correct the variation'),
 ('DC-8', 'R01', 'cost on a code with no budget line is neither assessed nor listed', 'not assessed: no budget line for this cost code', 'add a budget line, or move the cost to the right code'),
 ('DC-9', 'DEF', 'a partial rework cost is shown as the recorded sum', 'at least $X (n of m defects costed)', 'add the remaining rework costs'),
 ('DC-10', 'MP03, MP04, MP05, MP08, MP10, last rate paid', 'held, unreconciled or zero-quantity orders are left out unlisted', 'order not included, with its reason', 'resolve the hold, reconcile the order, or enter the quantity'),
 ('DC-11', 'every detection and M6 rule', 'findings are graded with the pinned detection policy\'s bands whether or not that policy is approved; a stored finding is flagged policy_unapproved when created or updated (a reopened finding keeps its earlier flag), the signal is not', 'grading not set up yet', 'set the grading levels in setup'),
 ('DC-12', 'M4 commitments, R02', 'amendments on an order the commitments figure skips (held, duplicate, unreconciled, without an amount, after the cut-off, status unknown or unmapped) are never examined; the order is listed, its amendments are not', 'amendment on hold, not checked: its order is not counted, with the order\'s reason; never added to a figure until confirmed', 'resolve the order\'s reason'),
]
SILENT.append(('DC-13', 'R01, R04, R04B, R08, R09, AGG, DLY, LAB, DEF, D02, MPD1', 'a record whose project cannot be told is in no project\'s run, so these rules neither assess nor list it', 'record not assessed: its project is unknown', 'add or correct the project reference'))

SKIP = re.compile(r'(corpus|demo_|faulty|golden|reference_|contracts_|ports_)')
BUILTIN = {'ValueError', 'TypeError', 'KeyError', 'AssertionError', 'RuntimeError', 'NotImplementedError', 'IndexError', 'AttributeError', 'LookupError', 'PermissionError', 'StopIteration'}
CODE = re.compile(r'(_?[A-Z][A-Z0-9_]*[A-Z0-9_])(?=$|:|\s|\(|%s)')
import ast

def consts(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, str): return [n.value]
    if isinstance(n, ast.JoinedStr): return [v.value for v in n.values if isinstance(v, ast.Constant) and isinstance(v.value, str)]
    if isinstance(n, ast.BinOp): return consts(n.left) + consts(n.right)
    if isinstance(n, ast.BoolOp): return [x for v in n.values for x in consts(v)]
    if isinstance(n, ast.IfExp): return consts(n.body) + consts(n.orelse)
    return []

def text(n):
    c = [x.strip() for x in consts(n) if re.search(r'[a-z]{3}', x)]
    return c[0] if c else None                          # the first piece with words: the start of the message

def texts_of(n):
    """every message text in an expression: each branch of a conditional, each element of a list or tuple"""
    if isinstance(n, ast.IfExp):
        return texts_of(n.body) + texts_of(n.orelse)
    if isinstance(n, (ast.List, ast.Tuple)):
        return [t for e in n.elts for t in texts_of(e)]
    if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add) and isinstance(n.left, (ast.List, ast.IfExp)):
        return texts_of(n.left) + texts_of(n.right)
    t = text(n)
    return [t] if t else []

def words(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, str): return [n.value]
    if isinstance(n, ast.IfExp): return words(n.body) + words(n.orelse)
    return []

def scan(apg):
    files = []
    for top in ('fin', 'det', 'mkt', 'ingest'):
        for dp, dn, fn in os.walk(os.path.join(apg, top)):
            if '__pycache__' in dp:
                continue
            files += [os.path.join(dp, f) for f in fn if f.endswith('.py') and not SKIP.search(f)]
    files = sorted(files) + [os.path.join(apg, x) for x in ('source_authority.py', 'policy_approval.py')]
    codes, texts, raises, states = {}, {}, {}, {}
    def add(d, k, rel): d.setdefault(k, set()).add(rel)
    for f in files:
        rel = os.path.relpath(f, apg)
        src = open(f).read()
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                m = CODE.match(n.value)
                if m and len(m.group(1)) >= 3 and (m.group(1) == n.value or n.value[m.end():][:1] in (':', ' ', '(') or '_' in m.group(1)):
                    add(codes, m.group(1), rel)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                a = n.func.attr
                if a == 'unknown' and len(n.args) >= 2:
                    for w in words(n.args[1]): add(texts, 'unknown: ' + w, rel)
                if a == 'dispute' and len(n.args) >= 2 and text(n.args[1]): add(texts, text(n.args[1]), rel)
                if a == 'exclude' and len(n.args) >= 2:
                    for w in words(n.args[1]): add(texts, 'exclude: ' + w, rel)
                if a == 'append' and isinstance(n.func.value, ast.Name) and n.func.value.id == 'skipped' and n.args and isinstance(n.args[0], ast.Tuple) and len(n.args[0].elts) == 2 and text(n.args[0].elts[1]):
                    add(texts, text(n.args[0].elts[1]), rel)
                if a in ('append', 'extend') and isinstance(n.func.value, ast.Name) and (n.func.value.id in ('gaps', 'reasons', 'notes', 'limitations', 'outstanding') or (n.func.value.id == 'out' and rel.replace(os.sep, '/') == 'mkt/fresh.py')) and n.args:
                    for tx in texts_of(n.args[0]):
                        if tx[:1].islower() or tx[:1] == '%':
                            add(texts, tx, rel)
                if a == 'unquantified' and n.args:
                    for tx in texts_of(n.args[0]):
                        add(texts, 'unquantified: ' + tx, rel)
            if isinstance(n, ast.Call) and not (isinstance(n.func, ast.Attribute) and n.func.attr in ('log', '_event')):   # audit-log reasons are records, not messages
                for kw in n.keywords:
                    if kw.arg in ('why', 'reason', 'note'):
                        for tx in texts_of(kw.value):
                            if tx[:1].islower():
                                add(texts, tx, rel)
                    if kw.arg == 'status':
                        for w in words(kw.value): add(texts, 'status: ' + w, rel)
            if isinstance(n, ast.Dict):
                for k, v in zip(n.keys, n.values):
                    if isinstance(k, ast.Constant) and k.value in ('why', 'reason', 'note', 'missing_parameter', 'sample_note', 'reasons', 'unknown', 'outstanding'):
                        txs = [v.value] if isinstance(v, ast.Constant) and isinstance(v.value, str) and re.fullmatch(r'[a-z_]+', v.value) else texts_of(v)
                        for tx in txs:
                            if tx[:1].islower() or tx[:1] == '%':
                                add(texts, tx, rel)
                    if isinstance(k, ast.Constant) and k.value == 'status':
                        for w in words(v): add(texts, 'status: ' + w, rel)
            if isinstance(n, ast.Assign):
                tg = n.targets[0]
                names = [tg.id] if isinstance(tg, ast.Name) else [e.id for e in tg.elts if isinstance(e, ast.Name)] if isinstance(tg, ast.Tuple) else []
                vals = n.value.elts if isinstance(n.value, ast.Tuple) else [n.value]
                if len(names) == len(vals):
                    for nm, v in zip(names, vals):
                        if nm in ('why', 'why2', 'reason', 'note'):
                            for tx in texts_of(v):
                                if tx[:1].islower():
                                    add(texts, tx, rel)
                        if nm == 'status':
                            for w in words(v): add(texts, 'status: ' + w, rel)
                        if rel == os.path.join('ingest', 'freshness.py') and nm.isupper():
                            for w in words(v): add(texts, 'freshness: ' + w, rel)
                        if rel == os.path.join('fin', 'figure.py') and nm in ('PROV', 'CANT'):
                            for w in words(v): add(states, w, rel)
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Tuple) and len(n.value.elts) == 2 and isinstance(n.value.elts[0], ast.Constant) and n.value.elts[0].value is None and text(n.value.elts[1]):
                add(texts, text(n.value.elts[1]), rel)
            if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call):
                fn = n.exc.func
                nm = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else 'call'
                if nm not in BUILTIN and n.exc.args and text(n.exc.args[0]):
                    add(raises, (nm, text(n.exc.args[0])), rel)
                elif nm not in BUILTIN and n.exc.args and isinstance(n.exc.args[0], ast.Call) and isinstance(n.exc.args[0].func, ast.Attribute) and n.exc.args[0].func.attr == 'join':
                    add(raises, (nm, 'the fields named are not well formed (a list of field names)'), rel)
                elif nm not in BUILTIN and n.exc.args and not (isinstance(n.exc.args[0], ast.Constant) and isinstance(n.exc.args[0].value, str)):
                    add(raises, (nm, '(no fixed text: ' + ast.unparse(n.exc.args[0]) + ')'), rel)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == '_refuse' and len(n.args) >= 5 and text(n.args[4]):
                add(raises, ('_refuse', text(n.args[4])), rel)
        if re.search(r'(det|mkt)/common\.py$', rel.replace(os.sep, '/')):
            for st in ('cannot_assess', 'not_configured', 'disabled'):
                if re.search(r"""\['status'\] = ['"]%s['"]""" % st, src):
                    add(states, st, rel)
    return codes, texts, raises, states

codes, texts, raises, states = scan(APG)
problems = []
covered = set(MSG) | set(NOT_CODE) | set(EXPAND)
for c in sorted(codes):
    if c not in covered and not RULE_ID.match(c):
        problems.append(('code without an entry', c))
for piece, full in EXPAND.items():
    problems += [('expansion without an entry', x) for x in full if x not in MSG]
expanded = {x for v in EXPAND.values() for x in v}
problems += [('entry the code no longer gives', c) for c in sorted(MSG) if c not in codes and c not in expanded]
def match_text(t):
    hits = [k for k in list(TEXT) + list(NOT_TEXT) if t == k or t.startswith(k)]
    return max(hits, key=len) if hits else None
used = {}
for t, fs in texts.items():
    k = match_text(t)
    if k is None:
        problems.append(('reason text without an entry', t))
    else:
        used.setdefault(k, set()).update(fs)
problems += [('text entry the code no longer gives', k) for k in list(TEXT) + list(NOT_TEXT) if k not in used]
problems += [('raised by a class without an audience', nm) for nm in sorted({k[0] for k in raises}) if nm not in RAISE]
problems += [('state entry the code no longer gives', k) for k in STATES if k not in states]
if problems:
    for p in problems:
        print(*p)
    sys.exit('the message list does not match the code')

rows = []
def row(kind, msg, where, a, m, d, w, today='given by the code'):
    rows.append({'kind': kind, 'message': msg, 'given by': where, 'audience': a, 'what it means': m,
                 'what the builder is told to do': d, 'who usually does it': w, 'today': today})
for c in sorted(MSG):
    a, m, d, w = MSG[c]
    src = codes.get(c, set()) | EXPAND_SRC.get(c, set())
    row('reason code', c, ' '.join(sorted(src)), a, m, d, w)
for k in sorted(TEXT):
    a, m, d, w = TEXT[k]
    row('plain-language reason', k, ' '.join(sorted(used[k])), a, m, d, w)
for k in sorted(STATES):
    a, m, d, w = STATES[k]
    row('run or figure state', k, ' '.join(sorted(states[k])), a, m, d, w)
for (nm, t) in sorted(raises):
    a = RAISE_TEXT.get(next((x for x in RAISE_TEXT if t.startswith(x)), None), RAISE[nm])
    if (nm, t) in RAISE_MEANING:
        m, d, w = RAISE_MEANING[(nm, t)]
        row('refusal or error raised (' + nm + ')', t, ' '.join(sorted(raises[(nm, t)])), a, m, d, w)
        continue
    if t.startswith('the fields named are not well formed'):
        m, d = 'the settings are refused: the fields named are not well formed', 'correct the fields named, then submit again'
    elif t.startswith('(no fixed text') and nm in ('FileNotFound', 'IntegrityError', 'ScanInfected', 'ScanRequired'):
        m, d = 'a file-store error; the intake turns it into FILE_NOT_FOUND, FILE_INTEGRITY, SCAN_INFECTED or SCAN_REQUIRED', 'none for the builder here; act on that code'
    elif t.startswith('(no fixed text') and a == S:
        m, d = 'an integrity error naming the field at fault', 'none for the builder'
    elif t.startswith('(no fixed text'):
        m, d = 'a refusal whose reason is given with it', 'do what the reason says, then try again'
    else:
        m, d = 'the message states it', 'do what the message says, then try again' if a in (P, B) else 'none for the builder'
    row('refusal or error raised (' + nm + ')', t, ' '.join(sorted(raises[(nm, t)])), a, m, d, 'the person acting' if a == P else BK if a == B else SU)
for dc, rule, today, msg, do in SILENT:
    row('silent today (' + dc + ')' if dc != 'DC-3' else 'an uncaught error today (DC-3)', msg, rule, B, today, do, '-', 'no message: the ' + ('proposed fix, put to the owner,' if dc == 'DC-13' else 'decided fix') + ' adds it (' + dc + ')')
with open(os.path.join(OUT, 'NOT_ASSESSED_MESSAGES.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)
from collections import Counter
print('messages', len(rows), 'by kind', dict(Counter(r['kind'].split(' (')[0] for r in rows)), 'by audience', dict(Counter(r['audience'] for r in rows)))
