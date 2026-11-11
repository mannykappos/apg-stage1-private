# Data-model gap analysis for the APG Data Readiness change request (revision 2). Rows authored from the locked blueprint
# (sections cited) against the field register generated from the code (FIELD_REGISTER.csv). BUILDER-EXECUTED: NOT INDEPENDENT.
import csv
H = ['domain', 'entity', 'class', 'blueprint', 'required field groups (blueprint)', 'APG today (record kind: fields present)',
     'status', 'gap', 'supply paths', 'likely data owner']
R = [
# --- common
('Common', 'Identity, provenance and lifecycle fields on every record', 'I', 'S03 s3; S04 s10, s13, s17',
 'source system, source record id and revision, observed/effective/recorded times, validity, status, actor, evidence refs, schema version',
 'pipeline record format: source, source_record_id, revision decision (new/duplicate/revision/stale/conflict), outcome',
 'partial', 'effective vs observed vs recorded times and evidence refs to be confirmed per kind', 'created by APG at intake', 'APG'),
('Common', 'Source registry and Source Authority Register', 'C', 'S04 s4, s5; PG-DI-AC-01/02',
 'per source: fields supplied, cadence, limits, auth; per field: authoritative source, secondary sources, precedence, owner, approval history',
 'apg/source_authority.py; synthetic register in the demo', 'partial', 'no builder-facing setup of the register; approval workflow', 'setup with the builder; versioned', 'builder finance lead + APG onboarding'),
('Common', 'Cost-code map (builder chart of accounts / cost codes to APG cost structure)', 'C', 'S03 s2 (cost code); 8-layer 02 s2.4 (cost taxonomy)',
 'builder code, APG code, scope/work package, effective dates, approval', 'cost_code_ref carried as given; no mapping entity',
 'missing', 'new mapping entity and onboarding step; APG suggests, builder confirms (S06 s5.6)', 'setup step; AI-suggested, human-confirmed', 'builder contract administrator / finance'),
('Common', 'Organisation, legal entity, tenancy', 'B', 'S03 s2; S04 s6, s16', 'legal entity, tenant scope, ABN', 'tenancy.py; supplier ABN only',
 'partial', 'legal entity of the builder per project', 'setup', 'builder'),
# --- commercial and revenue
('Commercial', 'Project', 'B', 'S03 s2; 8-layer 11 s11.2', 'code, name, type, jurisdiction, currency, reporting calendar, lifecycle stage, status',
 'project: project_ref, project_name, contract_value_cents, start_date, planned_finish', 'partial', 'jurisdiction, project type, lifecycle stage, reporting calendar', 'template; setup screen', 'builder PM'),
('Commercial', 'Head contract (with the client)', 'B', 'S03 s2, s6.1; S11 s4', 'contract sum, form (e.g. AS4000), clauses: payment terms, notice and time-bar triggers, valuation rules, retention and security terms',
 'contract: original_contract_cents, approved_variations_cents', 'partial', 'contract form, payment terms, notice triggers, retention/security clauses', 'setup questions + document capture (human-verified)', 'builder contract administrator'),
('Commercial', 'Variation (client side)', 'B', 'S03 s6.1; S11 s4-6; 8-layer 11 Variation', 'instruction, scope, status (raised/submitted/approved/rejected/disputed), estimated cost, claimed, approved amounts and dates, evidence',
 'variation: raised_date, source_status, value_cents, description_text', 'partial', 'separate claimed/approved amounts and dates; instruction link; evidence', 'template; entry screen; email/document capture', 'contract administrator'),
('Commercial', 'Site instruction / direction', 'B', 'S11 s4-5 (written instruction)', 'instruction id, date, issuer, scope, linked variation', 'notice (notice_type_text) used for instructions',
 'partial', 'confirm whether R04b reads notices as instructions; dedicated fields', 'site capture; email capture', 'site manager'),
('Commercial', 'Client progress claim / payment claim', 'B', 'S03 s6.1; S11 s5; S12 s3-5', 'claim period, amount claimed, date served, status: submitted/certified/disputed/rejected/paid, certified amount and date',
 'none', 'missing', 'new record kind with lifecycle states', 'template; accounting integration; entry screen', 'contract administrator'),
('Commercial', 'Payment schedule / certificate (from the client)', 'B', 'S11 s5; S12 s3', 'scheduled amount, reasons for withholding, date, link to claim', 'none',
 'missing', 'new record kind (SOP Act payment schedule)', 'email/document capture (human-verified); template', 'contract administrator'),
('Commercial', 'Notice and deadline (time bars, EOT)', 'B', 'S07 s3; S11 s6 (deadlines traceable)', 'trigger event, clause, deadline, served date, status, interpretation status',
 'notice: notice_date, notice_type_text, linked_variation_ref, description_text', 'partial', 'trigger, clause and deadline fields; human-review status for interpretations', 'site capture; email capture', 'contract administrator'),
('Commercial', 'Accounts receivable, receipts and collection', 'B', 'S03 s6.1; S12 s3-5', 'invoice to client, amount, due date, received, outstanding, disputed', 'bank_txn only (no receivable record)',
 'missing', 'receivable and receipt record kinds', 'accounting integration; template', 'bookkeeper'),
# --- subcontract and procurement
('Subcontract', 'Subcontract (with each trade)', 'B', 'S03 s2 (subcontractor/trade); S04 s2', 'trade, scope, subcontract sum, terms, retention, security', 'purchase_order used for commitments; supplier for identity',
 'partial', 'subcontract terms, retention held from the trade, security from the trade', 'template; document capture', 'contract administrator'),
('Subcontract', 'Subcontractor progress claim, assessment and payment', 'B', 'S03 s7; S04 s11; S12 s3 (Gemini review item)', 'claim period, claimed, assessed/certified, paid, back-charges, variation claims, dates, status',
 'none (ap_invoice holds the resulting invoice only)', 'missing', 'new record kinds: subcontractor claim, assessment, payment schedule; over-certification check', 'email/document capture; accounting integration; entry screen', 'contract administrator'),
('Procurement', 'Supplier / subcontractor identity', 'B', 'S03 s2; S04 s11', 'name, ABN, aliases, trade', 'supplier: supplier_name, abn_text', 'partial', 'trade and aliases', 'template; integration', 'bookkeeper'),
('Procurement', 'Purchase order / commitment', 'B', 'S03 s7; S05 s6', 'revision, approval history, scope, quantity, price, status (approved/cancelled/superseded), cost code',
 'purchase_order: supplier, project, cost code, order date, material, qty, unit, rate, amount, source_status; po_amendment: delta, approved_change_ref, reason',
 'partial', 'approval state and cancellation semantics to be defined (commitment policy)', 'template; integration', 'procurement / PM'),
('Procurement', 'Supplier invoice, credit, payment', 'B', 'S03 s7; S04 s11', 'invoice lines linked to PO lines, tax, credits linked to originals, payments', 'ap_invoice (header-level, PO ref), credit_note, payment; pm_invoice as secondary source',
 'partial', 'line-level PO matching (partial invoices, multiple deliveries)', 'accounting integration; template', 'bookkeeper'),
('Procurement', 'Material specification, demand, delivery', 'B', 'S03 s8.1-8.2; S08 s4-7', 'spec attributes, required/ordered/delivered/accepted/consumed quantities, required-on-site date',
 'material, material_demand, spec_requirement, delivery (qty delivered/accepted)', 'partial', 'consumed/installed, returned, wasted quantities', 'template; site capture', 'procurement'),
('Procurement', 'Quotes, tiers, terms, landed-cost components, import checks', 'B', 'S03 s8.3-8.4; S08 s4-7', 'spec, quantity/unit, validity, currency, delivery basis, inclusions/exclusions, terms, freight/duty/insurance/storage',
 'supplier_quote, quote_tier, quote_term, landed_assumption, import_check, quote_reading (with verified_by)', 'covered', 'freshness thresholds per decision (S08 s7.1) to be set', 'document capture (human-verified); template', 'procurement'),
('Market', 'Market observations and FX', 'X', 'S08 s7; S03 s11.1', 'source type (asking/quote/index/transaction), date, geography, unit', 'market_observation, fx_rate', 'covered', 'licensed sources to be chosen', 'external feeds', 'APG'),
# --- cost and forecast
('Cost and forecast', 'Budget (original and current approved)', 'B', 'S03 s4, s6.2', 'cost code, scope, revision, approval', 'budget_line: cost_code_ref, budget_cents, source_revision_label, revision_date', 'partial', 'approval status of each revision', 'template; integration', 'estimator / PM'),
('Cost and forecast', 'Estimate lines', 'B', '8-layer 11 EstimateLine; Layer 1', 'scope/trade/package, quantity/unit/rate, pricing source and date, inclusions/exclusions, PC/provisional sums', 'none (budget lines only)', 'missing', 'new record kind for Estimation Intelligence', 'estimating software export; template', 'estimator'),
('Cost and forecast', 'Cost-to-complete forecast (the builder\'s)', 'B', 'S05 s5-5.2; 8-layer 02 s2.4 (EAC/CTC method)', 'version, date, cost code, CTC, basis, owner, approval, assumptions',
 'ctc_line: cost code, forecast_version, forecast_date, cost_to_complete_cents, estimate_basis_text, movement_reason_text', 'partial', 'forecast owner and approval; adopted vs draft version', 'template; forecast-update screen', 'PM'),
('Cost and forecast', 'Accruals and overhead allocation', 'C', 'S03 s6.3 (accruals, overhead allocation must be specified)', 'accrual policy, overhead allocation basis', 'none', 'missing', 'policy decisions (owner register)', 'setup questions', 'builder finance lead'),
('Cost and forecast', 'Baseline, assessment, scenario', 'I', 'S05 s5.1, s11, s13; 8-layer 11 Baseline/Assessment/Scenario', 'versioned baselines, input snapshots, calculation version, assumptions, warnings',
 'calc_records, repro (pinned input snapshots), forecast_book', 'partial', 'baseline approval workflow; scenario isolation in the UI', 'created by APG', 'APG + builder approver'),
# --- schedule
('Schedule', 'Programme version, activities, dependencies, calendars', 'B', 'S03 s9; S07 s3-4.1', 'programme identity/version, approved baseline and revisions, activities, planned/forecast/actual dates, dependencies, calendars, float where supported',
 'none (delay_event carries an activity_ref only)', 'missing', 'new record kinds; capability gate for critical-path analysis (S07 s4.1)', 'scheduling software export; template', 'planner / PM'),
('Schedule', 'Progress (percent complete, actual activity dates)', 'B', 'S07 s3; S09 s3', 'activity, as-of date, percent or quantity complete, evidence', 'none (work_output holds weekly quantities by work package)', 'missing', 'new record kind; progress screen; site capture', 'site capture; scheduling export', 'site manager'),
('Schedule', 'Delay event', 'B', 'S03 s9; S07 s3, s6', 'event, dates, activity, attribution state, evidence, overlap', 'delay_event: activity_ref, start/end dates, working_days, recorded_cause_text, holding_rate_cents_per_day',
 'partial', 'attribution state, evidence refs; holding rate belongs to a rate record, not the event', 'site capture; template', 'site manager'),
('Schedule', 'Holding-cost rates (site overhead, equipment, financing)', 'C', 'S07 s5-6; S03 s9', 'rate, basis, source, eligible period', 'holding_rate_cents_per_day on the delay event', 'partial', 'separate evidenced rate records', 'setup questions; template', 'builder finance lead'),
# --- labour and plant
('Labour', 'Worker (pseudonymous), employer, trade, crew', 'B', 'S09 s3, s14 (privacy)', 'pseudonymous id, employer (own or subcontractor), trade, crew', 'timesheet.worker_pseudonym only', 'partial', 'employer, trade, crew', 'payroll/timesheet export', 'payroll'),
('Labour', 'Timesheet and work allocation', 'B', 'S09 s3', 'date, hours, overtime, task/activity, work package', 'timesheet: work_package_ref, work_date, ordinary/overtime hours, rate_cents_per_hour', 'partial', 'activity link; allowances', 'timesheet app export; site capture', 'site manager / payroll'),
('Labour', 'Labour rates, allowances, on-costs, award classification', 'C', 'S09 s3', 'classification, rate, allowances, overtime premiums, on-costs, effective dates', 'rate_cents_per_hour on the timesheet only', 'missing', 'rate records by classification; never inferred from generic awards (GPT estimating table)', 'payroll export; setup', 'payroll'),
('Labour', 'Accepted output, productivity baseline, work conditions', 'B', 'S09 s5-6', 'quantity accepted, unit, quality acceptance, comparable baseline, constraints (access, materials, drawings)', 'work_output: work_package_ref, week_start, quantity, unit_text', 'partial', 'quality acceptance, conditions, baseline records', 'site capture', 'site manager'),
('Plant', 'Plant hire', 'B', 'S09; S07 s5', 'on/off hire, off-hire request and confirmation, minimum hire, usage/idle evidence, rate basis', 'plant_hire: equipment_text, on/off hire dates, needed_until, rate_cents_per_day', 'partial', 'off-hire request/confirmation, usage evidence, minimum hire terms', 'site capture; supplier docs', 'site manager'),
# --- quality
('Quality', 'Quality observation, defect, rework event', 'B', 'S13 s3', 'observation, defect, rework event as distinct records; location, trade, discovery date, evidence, severity', 'defect: subcontractor_text, trade_text, raised_date, severity_text, rework_cost_cents, status_text', 'partial', 'observation and rework-event records; location; evidence', 'site capture with photos', 'site manager / quality'),
('Quality', 'Root cause (hypothesis vs confirmed), rectification, closure verification, quality cost', 'I', 'S13 s3, s5-8', 'hypothesis vs confirmed cause, action, verification, actual vs estimated cost, recovery', 'none', 'missing', 'lifecycle records created in APG with human confirmation', 'APG workflow', 'quality lead'),
# --- cash, retention, security
('Cash', 'Bank transactions and funding facility', 'B', 'S12 s3-5', 'actual cash, facility limit/drawn/rate, fees, day-count', 'bank_txn; facility: limit, drawn, rate_bps, statement_date', 'partial', 'facility fees and day-count basis', 'bank feed; template', 'bookkeeper'),
('Cash', 'Retention (held by client, and held from trades)', 'B', 'S03 s10.1; S12 s7', 'contract clause, basis, withheld/claimed/approved/released/outstanding, due/review date, conditions, disputes, linked defects', 'retention: retention_held_cents, release_due_date, released_date, hold_reason_text; retention_event created by APG (fin/cash_states.py)',
 'partial', 'clause and basis; claimed/approved release amounts; retention held from trades', 'template; setup questions', 'contract administrator'),
('Cash', 'Security instrument (bank guarantee, bond)', 'B', 'S03 s10.2; S12 s8-9', 'type, issuer, beneficiary, face value, issue/expiry, release conditions, fees, facility usage', 'security: kind_text, face_value_cents, expiry_date', 'partial', 'issuer, beneficiary, issue date, fees, release conditions', 'template; document capture', 'bookkeeper'),
('Cash', 'Payables and statutory liabilities (GST, PAYG)', 'B', 'S12 s3; S03 s11.4', 'due dates, amounts, tax basis', 'gst_cents on invoices; tax basis per template (gst field)', 'partial', 'tax basis policy; payable due dates', 'accounting integration', 'bookkeeper'),
# --- compliance
('Compliance', 'Supplier/subcontractor compliance evidence', 'D', 'S04 s2; S09; S13', 'evidence type, holder, trade/work, jurisdiction, coverage/limit, issue/expiry, verification', 'compliance: supplier_ref, evidence_type_text, expiry_date', 'partial', 'holder, coverage/limit, jurisdiction, verification status', 'document capture (human-verified); reminders', 'contract administrator'),
# --- outputs and decisions
('Intelligence', 'Finding, alert, recommendation, decision, outcome', 'I', 'S03 s12; S06 s6; S10; 8-layer 11 Alert/Decision', 'evidence, severity, lifecycle, human decisions, realised outcome', 'det/findings.py, rec/*, policy_approval.py', 'partial', 'data-integrity findings feeding the readiness report', 'created by APG', 'APG + builder reviewer'),
('Intelligence', 'Readiness state per insight', 'I', 'this request', 'insight, contract version, status per blueprint gate, missing inputs, owner, next action', 'freshness.py (decision eligibility); figure.py (qualified figures)', 'partial', 'the per-insight readiness record and the builder report', 'created by APG', 'APG'),
('Configuration', 'Accounting and contract policies (margin basis, revenue basis, commitments, tax, rounding)', 'C', '8-layer 02 s2.4, s2.11; S03 s5, s6.3', 'the ten foundation decisions', 'fin/policy.py, det/policy.py, mkt/policy.py (approved policies)', 'partial', 'builder-facing setup of each policy; owner decision register', 'setup questions', 'builder finance lead'),
('Evidence', 'Documents (contracts, claims, invoices, quotes, photos)', 'D', 'S04 s12, s18', 'document, hash, extraction output, reviewer, verification', 'ingest/documents.py; ingest/filestore.py; quote_reading (verified_by)', 'partial', 'capture by email and phone; verification queue in the UI', 'email capture; phone capture', 'whoever receives it'),
]
assert all(len(r) == len(H) for r in R), [r[1] for r in R if len(r) != len(H)]
with open('DATA_MODEL_GAP_ANALYSIS.csv', 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(H); w.writerows(R)
import collections
c = collections.Counter(r[6] for r in R); print(len(R), dict(c))
print('missing:', [r[1] for r in R if r[6] == 'missing'])
print('by class:', dict(collections.Counter(r[2] for r in R)))
