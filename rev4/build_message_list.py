"""Data Readiness revision 4: every message APG's production code can give when it cannot fully do a check or a figure, with what the
builder is to do (the owner's rule of 2026-11-12: "This feature of telling the builder what apg needs to work should be across the whole
apg").  Builder work (Claude), not independent.  It states the design; nothing here changes the code.

It scans the production modules of apg/fin, apg/det, apg/mkt, apg/ingest and apg/source_authority.py (test, corpus, demo, golden, faulty,
reference, contract and port modules are left out) for
  - every upper-case reason code written as a string ('PO_NOT_VISIBLE', 'COMPONENT_MISSING:' ...),
  - every plain-language reason a detection or M6 rule gives for not assessing an item,
  - the run states cannot_assess, not_configured and disabled, and M6's missing_parameter,
and fails if the code gives one that the table below does not cover, or if the table holds one the code no longer gives.  So the list is
complete for the code it was run on.  It adds the silent cases (DC-3 to DC-11), which give no message today.

Audience:  builder      - a gap in the builder's data or settings: the message says what to do and who usually does it
           person       - a check on an action a person is taking (approving, resolving, recording an event): what that person must add
           information  - a label or note that explains a result; no action needed
           system       - an APG integrity or programming fault: nothing for the builder; APG support investigates
The wording is the design's starting point; the exact text is settled when each message is built (first in the DC change request).
usage: python3 -I build_message_list.py <the apg folder> <output folder>"""
import csv, os, re, sys

APG, OUT = sys.argv[1], sys.argv[2]
SKIP = re.compile(r'(corpus|demo_|faulty|golden|reference_|contracts_|ports_)')

B, P, I, S = 'builder', 'person', 'information', 'system'
BK, PM, CM, FN, AP, SU = 'bookkeeper', 'project manager', 'commercial manager', 'finance', "the builder's approver", 'APG support'
# code: (audience, what it means, what to do, who usually does it)
MSG = {
 'ACTION_REQUIRED': (P, 'a proposed action on a finding was not described', 'describe the proposed action', 'the person proposing it'),
 'ACTUALS_AFTER_FORECAST_DATE_NOT_ADDED': (I, 'cost recorded after the forecast date is not added to the forecast final cost', 'none; update the forecast to include it', PM),
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
 'BUDGET_EXCEEDED_BY': (I, 'cost on this code is above its budget, so a budget-derived cost to complete is not known', 'enter a cost to complete for the code', PM),
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
 'CRITICAL_VALUE_MISSING': (B, 'a value the record cannot be used without is missing', 'enter the value', BK),
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
 'EXPIRY_REVIEW': (B, 'a security instrument is close to expiry', 'review the instrument: renew or release it', FN),
 'FACILITY_RECORD_HELD': (B, 'the facility statement is held, so carrying cost cannot be assessed', 'resolve the hold on the facility statement', FN),
 'FACILITY_STATEMENT_AFTER_AS_OF': (I, 'the facility statement is dated after the assessment date', 'none; or supply a statement for the period', FN),
 'FILE_INTEGRITY': (S, 'a stored file no longer matches its recorded fingerprint', 'none for the builder', SU),
 'FILE_NOT_FOUND': (S, 'a stored file cannot be found', 'none for the builder', SU),
 'FILE_TOO_LARGE': (B, 'the import file is larger than allowed', 'split the file and import the parts', BK),
 'FINDING_UNKNOWN': (S, 'an action named a finding that does not exist', 'none for the builder', SU),
 'FORECAST_BASIS_CANNOT_BE_ASSESSED': (B, 'the forecast the margin rests on cannot be assessed', 'resolve what stops the forecast (listed with it)', PM),
 'FORECAST_DERIVED_FROM_BUDGET_NO_DECLARED_VERSION': (B, 'there is no declared forecast, so the cost to complete is derived from the budget', 'enter a forecast version', PM),
 'FORECAST_DOES_NOT_REPRODUCE': (S, 'a forecast run does not reproduce from its stored inputs', 'none for the builder', SU),
 'FORECAST_FINAL_COST_NOT_POSITIVE': (B, 'the forecast final cost is zero or negative, so the margin cannot be assessed', 'check the forecast and cost records', PM),
 'FORECAST_OWNER_REQUIRED': (P, 'adopting a forecast needs a person with the forecast-owner role', 'have the forecast owner adopt it', PM),
 'FORECAST_REVENUE': (I, 'the result is labelled forecast revenue', 'none', '-'),
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
 'INPUT_MISSING': (S, 'the policy version a run names is not stored', 'none for the builder', SU),
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
 'NON_ASCII_IDENTIFIER': (B, 'an identifier holds characters other than plain letters and digits; the row is rejected', 'correct the identifier', BK),
 'NOT_ACTIVE': (P, 'the finding is not active, so this action does not apply', 'none', 'the person acting'),
 'NOT_APPLICABLE_REVENUE_ZERO_OR_NEGATIVE': (B, 'revenue is zero or negative, so a margin percentage does not apply', 'check the contract value and variations', CM),
 'NOT_A_DETECTION_RUN': (S, 'the run given is not a detection run', 'none for the builder', SU),
 'NOT_A_FORECAST': (S, 'the run given is not a forecast', 'none for the builder', SU),
 'NOT_A_SCENARIO_RUN': (S, 'the run given is not a scenario run', 'none for the builder', SU),
 'NOT_BYTES': (S, 'the importer was given something that is not a file', 'none for the builder', SU),
 'NOT_RECONCILED': (B, 'the order has not been through reconciliation, so it is not used', 'run reconciliation for the order', BK),
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
 'NO_RECONCILIATION_STATE': (B, 'the record has not been reconciled, so it is held', 'run reconciliation', BK),
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
 'PO_STATUS_MAP_NOT_CONFIGURED': (B, 'purchase-order statuses are not set up', 'set up the purchase-order statuses (open, committed, closed)', FN),
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
 'RECOGNISED_REVENUE': (I, 'the result is labelled recognised revenue', 'none', '-'),
 'RECOGNITION_METHOD_NOT_CONFIGURED': (B, 'the revenue recognition method is not set', 'set it in setup', FN),
 'RECORD_MISSING': (S, 'a record a stored run needs is missing', 'none for the builder', SU),
 'RECORD_NO_LONGER_COUNTED': (I, 'a record counted before is no longer counted, so the movement is not explained', 'check why (held, corrected or replaced)', BK),
 'REFERENCE_BASIS_UNRECORDED': (I, 'the order rate\'s delivery basis and inclusions are not recorded', 'none; it is a reference only', '-'),
 'REFERENCE_ONLY': (I, 'an order rate is a reference, not an offer', 'none', '-'),
 'REJECTED_BY_REVIEW': (I, 'a reviewer rejected the record', 'none, or send a corrected record', BK),
 'RELEASED_AND_RECEIVED': (I, 'the retention was released and the money received', 'none', '-'),
 'RELEASED_PER_LEDGER_CASH_RECEIPT_NOT_EVIDENCED': (B, 'the ledger says released but no bank receipt is held', 'import the bank receipt', FN),
 'RELEASE_REVIEW_DUE': (B, 'the retention is due for release review', 'review the release and lodge the claim', FN),
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
 'UNIT_INCOMPATIBLE': (I, 'the offer\'s unit cannot be converted to the requirement\'s, so it is not comparable', 'none, unless a conversion should be declared; then declare it', CM),
 'UNIT_MISMATCH': (B, 'orders are in a unit other than the demand\'s, so coverage cannot be assessed', 'correct the unit, or record the demand in the same unit', CM),
 'UNIT_UNVERIFIED': (B, 'the unit of the offer is not verified', 'verify the unit against the quote', CM),
 'UNKNOWN_DENOMINATOR': (S, 'a calculation was asked for with an unknown basis', 'none for the builder', SU),
 'UNKNOWN_STATUS': (S, 'an unknown finding status was named', 'none for the builder', SU),
 'VALUE_MISSING': (B, 'an optional value is missing; the record is used with a warning', 'enter the value if known', BK),
 'VARIATION_STATUS_MAP_NOT_CONFIGURED': (B, 'variation statuses are not set up', 'set up the variation statuses (approved, submitted, rejected, disputed)', CM),
 'VARIATION_STATUS_UNMAPPED': (B, 'the variation\'s status is not in the status settings, so it is left out', 'add the status to the variation status settings', CM),
 'VERIFICATION_NOT_AVAILABLE': (P, 'a realised outcome needs the Section 05 verification, which is not available', 'none yet', '-'),
}
# plain-language reasons the rules give (matched by their start)
TEXT = {
 'record not in the store': (B, 'R07: the quote or reference named in the comparable pair is not stored', 'import it, or correct the pair', CM),
 'purchase order has no unit rate': (B, 'R07: the reference order has no unit rate', 'enter the order\'s unit rate', BK),
 'currency %s: conversion is not done here': (I, 'R07: a quote not in AUD is left to M6', 'none', '-'),
 'ex-works quote with no freight': (B, 'R07: an ex-works quote has no freight, so a landed cost cannot be built', 'add the freight to the quote', CM),
 'delivery basis %r needs the landed-cost model': (I, 'R07: this delivery basis is left to M6', 'none', '-'),
 'the declared pair names different materials': (B, 'R07: the comparable pair names two different materials', 'correct the pair', CM),
 'status %r is not mapped by the financial policy': (B, 'R04: the variation\'s status is not in the status settings', 'add the status to the variation status settings', CM),
 'invoice for ': (B, 'R03: an invoice for the order is held, so the invoiced total may be higher', 'resolve the invoice\'s hold', BK),
 'held, disputed, undated or after the as-of date': (B, 'R09: the forecast line is held, disputed, undated or after the date', 'resolve the line (date it, or resolve the hold)', PM),
 'not usable (': (B, 'AGG: the order is held', 'resolve the hold', BK),
 'undated or after the as-of date': (B, 'AGG: the order is undated or after the date', 'enter the order date', BK),
 'a grouping key is missing: ': (B, 'AGG: a field the split-order check groups by is missing', 'enter the field named', BK),
 'hours are not a plain non-negative decimal': (B, 'LAB: the timesheet hours are not a valid number', 'correct the hours', PM),
 'fewer than %d complete weeks with both hours and output': (B, 'LAB: not enough complete weeks of hours and output', 'record hours and output for the missing weeks', PM),
 'the windows are not consecutive weeks': (B, 'LAB: a week is missing or incomplete', 'complete the missing week', PM),
 'the unit of measure changes inside the windows': (B, 'LAB: the output unit changes between weeks', 'use one unit for the work package', PM),
 'a window has no output or no hours': (B, 'LAB: a period has hours but no output, or output but no hours', 'record the missing hours or output', PM),
 'subcontractor or trade is not recorded': (B, 'DEF: the defect has no subcontractor or trade', 'record the subcontractor and trade', PM),
 'no evidenced need date': (B, 'R08: the plant hire has no need date', 'enter the date the plant is needed until', PM),
 'no end date: an open delay': (B, 'DLY: the delay has no end date', 'enter the end date, or close the delay', PM),
 'starts after the as-of date or ends before it starts': (B, 'DLY: the delay\'s dates are wrong', 'correct the delay\'s dates', PM),
 'uncovered demand but no rankable current quote': (B, 'MP03: demand is not covered and no current quote can be ranked', 'get a comparable current quote', CM),
 'no retention ledger': (B, 'R05: there is no retention ledger for the project', 'import the retention ledger', FN),
 'held': (B, 'R02: the order amendment is held', 'resolve the amendment\'s hold', BK),
 'sample_note': (I, 'MP08: too few orders with deliveries to draw a conclusion', 'none', '-'),
}
STATES = {
 'cannot_assess': (B, 'the rule or figure cannot be assessed; the reason codes say why', 'act on the reason codes given with it', '-'),
 'not_configured': (B, 'a setting the rule needs is missing; it is named', 'set the setting named, in setup', AP),
 'disabled': (I, 'the rule is switched off in the settings', 'none; switch it on if wanted', AP),
 'missing_parameter': (B, 'M6: an analysis is not assessed because a setting is missing; it is named', 'set the setting named, in setup', CM),
}
# silent today: no message is given (defect candidates; the owner decided on 2026-11-12 that each gets one)
SILENT = [
 ('DC-3', 'M6 last rate paid', 'a null purchase-order status map stops the whole M6 run with an error', 'purchase-order statuses not set up', 'set up the purchase-order statuses'),
 ('DC-4', 'MP05, MP08, MP10, MP02 reference, MP09', 'without the status map nothing is evaluated, and nothing says so; MP09 drops an opportunity when the GST rate is not set', 'not assessed: purchase-order statuses not set up; GST rate not set', 'set up the purchase-order statuses; set the GST rate'),
 ('DC-5', 'MP01', 'a watched material with no usable quote raises no signal', 'no current quote', 'get a quote, or resolve the held one'),
 ('DC-6', 'M6 comparison', 'a requirement with no positive quantity is reported nowhere', 'not assessed: quantity zero or unusable', 'enter the quantity needed'),
 ('DC-7', 'M4 commitments, R02', 'a held variation mapped to approved counts as approved', 'not assessed: the linked variation is on hold', 'approve, reject or correct the variation'),
 ('DC-8', 'R01', 'cost on a code with no budget line is neither assessed nor listed', 'not assessed: no budget line for this cost code', 'add a budget line, or move the cost to the right code'),
 ('DC-9', 'DEF', 'a partial rework cost is shown as the recorded sum', 'at least $X (n of m defects costed)', 'add the remaining rework costs'),
 ('DC-10', 'MP03, MP04, MP05, MP08, MP10, last rate paid', 'held, unreconciled or zero-quantity orders are left out unlisted', 'order not included, with its reason', 'resolve the hold, reconcile the order, or enter the quantity'),
 ('DC-11', 'every detection and M6 rule', 'findings are graded with settings nobody approved, and do not say so', 'grading not set up yet', 'set the grading levels in setup'),
 ('DC-1', 'R04B', 'an instruction linked to a rejected (or held) variation is silent', 'the client rejected the variation: this work may not be paid (or: not assessed, the variation is on hold)', 'record the outcome: disputed, at own cost, resubmitted, withdrawn (or approve, reject or correct the variation)'),
 ('DC-2', 'LAB', 'a missing overtime is counted as 0', 'not assessed: overtime unknown', 'enter the overtime hours (0 if none)'),
]

CODE = re.compile(r"""['"]([A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+)(?::|['"])""")
WHY = re.compile(r"""(?:'why': |return None, |why = |why2 = )f?'([a-z][^']{3,})'""")
files = []
for top in ('fin', 'det', 'mkt', 'ingest'):
    for dp, dn, fn in os.walk(os.path.join(APG, top)):
        if '__pycache__' in dp:
            continue
        files += [os.path.join(dp, f) for f in sorted(fn) if f.endswith('.py') and not SKIP.search(f)]
files.append(os.path.join(APG, 'source_authority.py'))
where, texts, states = {}, {}, {}
for f in sorted(files):
    rel = os.path.relpath(f, APG)
    src = open(f).read()
    for m in CODE.finditer(src):
        where.setdefault(m.group(1), set()).add(rel)
    if re.search(r'(det/rules_|det/common|mkt/rules|mkt/demand|mkt/suppliers|mkt/analysis)', rel):
        for m in WHY.finditer(src):
            texts.setdefault(m.group(1), set()).add(rel)
        if "or 'no retention ledger'" in src:
            texts.setdefault('no retention ledger', set()).add(rel)
        if "'why': 'held'" in src:
            texts.setdefault('held', set()).add(rel)
        if "'sample_note'" in src or 'sample_note' in src:
            texts.setdefault('sample_note', set()).add(rel)
    for st in STATES:
        if re.search(r"""['"]%s['"]""" % st, src):
            states.setdefault(st, set()).add(rel)

def match_text(t):
    hits = [k for k in TEXT if t.startswith(k) or t == k]
    return max(hits, key=len) if hits else None

problems = [('code without an entry', c) for c in sorted(where) if c not in MSG]
problems += [('entry the code no longer gives', c) for c in sorted(MSG) if c not in where]
used = {}
for t, fs in texts.items():
    k = match_text(t)
    if k is None:
        problems.append(('reason text without an entry', t))
    else:
        used.setdefault(k, set()).update(fs)
problems += [('text entry the code no longer gives', k) for k in TEXT if k not in used]
problems += [('state entry the code no longer gives', k) for k in STATES if k not in states]
if problems:
    for p in problems:
        print(*p)
    sys.exit('the message list does not match the code')

rows = []
for c in sorted(MSG):
    a, m, d, w = MSG[c]
    rows.append({'kind': 'reason code', 'message': c, 'given by': ' '.join(sorted(where[c])), 'audience': a, 'what it means': m,
                 'what the builder is told to do': d, 'who usually does it': w, 'today': 'given by the code'})
for k in sorted(TEXT):
    a, m, d, w = TEXT[k]
    rows.append({'kind': 'rule reason (plain text)', 'message': k, 'given by': ' '.join(sorted(used[k])), 'audience': a, 'what it means': m,
                 'what the builder is told to do': d, 'who usually does it': w, 'today': 'given by the code'})
for k in sorted(STATES):
    a, m, d, w = STATES[k]
    rows.append({'kind': 'run state', 'message': k, 'given by': ' '.join(sorted(states[k])), 'audience': a, 'what it means': m,
                 'what the builder is told to do': d, 'who usually does it': w, 'today': 'given by the code'})
for dc, rule, today, msg, do in SILENT:
    rows.append({'kind': 'silent today (' + dc + ')', 'message': msg, 'given by': rule, 'audience': B, 'what it means': today,
                 'what the builder is told to do': do, 'who usually does it': '-', 'today': 'no message: the decided fix adds it (' + dc + ')'})
with open(os.path.join(OUT, 'NOT_ASSESSED_MESSAGES.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)
from collections import Counter
print('messages', len(rows), 'codes', len(MSG), 'rule texts', len(TEXT), 'states', len(STATES), 'silent', len(SILENT),
      'by audience', dict(Counter(r['audience'] for r in rows)))
