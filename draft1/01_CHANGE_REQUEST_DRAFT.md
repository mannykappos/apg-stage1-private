# APG Data Readiness Change Request (draft)

Nov 11, 2026 · Emmanuel (product owner) · drafted by Claude

APG must know exactly what data each of its insights needs, check what each builder's systems supply, tell the builder plainly what is missing, and give a simple way to fill every gap, so that it never gives a wrong or overconfident answer because data was missing.

## The requirement

The owner's requirement (2026-11-11): APG must state exactly what data it needs. When a builder's existing software supplies only part of it (say 80%), APG's own features must supply the rest, so APG gets everything it needs to work.

"Fail-proof on our end" is defined here as two guarantees APG can be built and tested to meet:

1. **APG never gives a wrong or overconfident answer because data was missing.** Every result shows whether it rests on evidenced, estimated, stale or missing inputs.
2. **APG always knows and tells the builder what it lacks,** per insight, and how to supply it.

One thing APG cannot guarantee: that every builder will enter the missing data. So the design also makes filling a gap as easy as possible, and keeps APG useful on whatever it has, with each limit stated.

## What the locked blueprint already guarantees

The locked blueprint v1.0 already makes the fail-safe behaviour mandatory; this request adds the builder-facing side it leaves open.

| Already locked | Where |
| --- | --- |
| Missing critical values are never invented or silently defaulted | S04 §10, PG-DI-AC-11 |
| Freshness and completeness tracked by source, project, domain and decision use; recommendations suppressed, qualified or downgraded when inputs are stale or missing | S04 §14, PG-DI-AC-13 |
| Conflicting records quarantined; provisional results labelled and traceable to unverified inputs | S04 §9 |
| AI/OCR-extracted material values need human verification | S04 §12 |
| Field-level Source Authority Register; a source registry of the fields each source supplies, its cadence and limits | S04 §4, §5 |
| Manual uploads and spreadsheet imports pass the same controls, with row-level errors | S04 §18 |
| Missing or stale cost-to-complete inputs give a qualified forecast showing each value as evidenced, estimated, stale, missing or scenario | S05 §5.2, PG-PC-AC-04 |
| The same rule for holding costs, productivity, deadlines, cash forecasts and savings | S07, S09, S11, S12, S13 |
| Data-integrity findings kept separate from profit leakage | S06 §4 |

**What is not yet specified, and this request adds:** a per-insight data contract the builder can see; a readiness check and plain-words report; gap-filling paths mapped to every required input; a coverage matrix proving which gaps APG's existing features fill; and integration coverage maps per builder software.

## The data contract

Each APG insight gets a contract: the records it needs, how fresh they must be, and what APG does at each level. The table below is drafted from the insights the code already calculates (M4 financial core, M5 detection, M6 procurement); freshness levels are proposals for the owner and the reviewers to settle.

| Insight | Records it needs | Minimum level | Good level | Below minimum |
| --- | --- | --- | --- | --- |
| Revenue and recognised margin | Project, contract, approved variations, supplier invoices and credits | Contract value and all posted invoices for the period | Variations current within 7 days | Margin shown as not assessable, with the missing record named |
| Committed cost | Purchase orders, amendments, subcontract variations | Every open order on the project | Amendments within 7 days | Commitment total qualified as incomplete |
| Forecast final margin and cost to complete | Budget lines by cost code, the builder's cost-to-complete lines, actuals, commitments | A current forecast version covering every budgeted cost code | Forecast no older than one reporting period | Qualified forecast listing the missing or stale codes (S05 §5.2) |
| Budget and forecast movement (R01, R02, R09) | Budget lines, order amendments, forecast versions | Two forecast versions to compare | Monthly versions or better | No movement finding; data gap reported |
| Invoice against order (R03) | Supplier invoices, purchase orders | Invoices linked to orders | Same-day posting | Unmatched invoices held for reconciliation |
| Variations not claimed (R04, R04b) | Variations, site instructions, notices | Variation register | Instructions logged within 2 days | Finding withheld; register gap reported |
| Retention, security and carrying cost (R05) | Retentions, retention events, security instruments, the funding facility, bank transactions | Retention held and facility rate | Bank feed daily | Carrying cost not assessed |
| Supplier compliance (R06) | Supplier compliance evidence | Licence and insurance with expiry dates | All trades covered | Compliance status unknown, not "compliant" |
| Quote against reference (R07), landed cost, buy timing | Supplier quotes, tiers, terms, landed assumptions, materials, market observations, FX rates | Quote and the material it prices | Market data within its freshness window | Price finding withheld |
| Plant hire idle cost (R08) | Plant hire records | On-hire and off-hire dates | Daily usage | Idle cost not assessed |
| Delay and holding cost | Delay events, programme dates, holding-cost rates | Delay events with dates | Programme with progress and dependencies | Qualified estimate or unquantified finding (S07) |
| Labour productivity | Timesheets, work output | Hours and output on the same tasks | A comparable baseline (S09) | Comparison marked qualified, never a definitive conclusion |
| Defect recurrence and rework | Defect records | Defects with trade and location | Rectification cost recorded | Recurrence only, no cost |
| Cash-adjusted margin | All of the above for cash: retention, receivables, facility | Overdue receivables and facility rate | Bank feed daily | Not assessed |

Open question: the minimum and good levels above are first proposals, to be set per insight with the owner, not left to the build.

## The coverage matrix

First pass against the code: every one of APG's 35 record kinds can already be filled through an import template, but APG has no in-app entry screens or site capture yet, and four kinds of data the blueprint needs have no record kind at all.

| Data | Where builders usually hold it | APG today | Gap |
| --- | --- | --- | --- |
| Projects, contracts, variations | Job costing or project management | Import templates (project, contract, variation) | Entry screens |
| Supplier invoices, credits, payments | Accounting | Import templates (ap_invoice, credit_note, payment; pm_invoice as a second source) | Entry screens |
| Purchase orders and amendments | Procurement or job costing | Import templates (purchase_order, po_amendment) | Entry screens |
| Budgets and cost-to-complete forecasts | Estimating or job costing; often spreadsheets | Import templates (budget_line, ctc_line) | Entry screens; a simple forecast-update screen |
| Retentions and security | Accounting or spreadsheets | Import templates (retention, security) | Entry screens |
| Funding facility and bank transactions | Bank and accounting | Import templates (facility, bank_txn) | A bank feed (integration) |
| Supplier compliance | Spreadsheets or compliance tools | Import template (compliance) | Expiry reminders to the builder |
| Notices, delay events | Email, site diaries | Import templates (notice, delay_event) | Site capture (CR-05) |
| Plant hire, timesheets, work output | Payroll, timesheet apps, site diaries | Import templates (plant_hire, timesheet, work_output) | Site capture |
| Defects | Quality tools, site diaries | Import template (defect) | Site capture with photos |
| Materials, quotes, deliveries, market data | Procurement, supplier quotes, market feeds | Import templates (9 kinds) | Quote capture from documents (with the S04 §12 human check) |
| Programme activities, dates and percent complete | Scheduling software | **No record kind** | New record kind, import and a progress screen (needed for S07 delay and holding cost) |
| Client progress claims, payment schedules and receipts | Accounting, contract administration | **No record kind** (revenue uses contract and variations) | New record kinds (needed for S11 claims and S12 cash timing) |
| Labour rates and award costs | Payroll | **No record kind** | New record kind or setup questions |
| Estimate lines (8-layer blueprint EstimateLine) | Estimating software | Only budget lines | New record kind for Estimation Intelligence |

Not yet checked: field by field within each record kind; this pass is by record kind only. The owner's belief that existing features cover the gap holds for import, but not yet for in-app entry or the four missing kinds.

## The readiness check and the builder's report

At setup, and after every data refresh, APG compares what it holds with each insight's contract and tells the builder, in plain words, which insights are on, qualified or off, and exactly what would turn each one on.

- **Per insight:** on (good level), qualified (minimum level, with what is weak), or off (below minimum, with the missing record named).
- **Per source:** last received, how stale, which fields it supplies and which it does not.
- **The next step for each gap:** the quickest way to fill it (a template, an entry screen, a setup question, or the integration that would supply it).
- **Example wording:** "From your accounting system we have invoices and payments. We have no cost-to-complete forecast for 3 of 12 cost codes, so the forecast margin is qualified. Update those 3 codes to complete it."
- **Built on what exists:** the freshness tracking (S04 §14, `apg/ingest/freshness.py`) and the qualified figures (`apg/fin/figure.py`) already compute most of this inside APG; the new part is the builder-facing report and its link to each insight's contract.

## Gap filling

Every input in the contract must have at least one way for the builder to supply it inside APG, and the simplest one is offered first.

| Path | What it fills | Exists today |
| --- | --- | --- |
| Import templates (CSV and spreadsheet) | Every one of the 35 record kinds | Yes, with the S04 controls and row-level errors |
| Entry screens in APG | Small, frequent gaps: one forecast line, one variation, one delay | No (the UI is a read-only prototype) |
| Site capture on a phone (CR-05) | Delays, progress, defects, plant and labour on site | No |
| Document capture | Quotes, invoices, contracts, with the human check S04 §12 requires | Partly (`apg/ingest/documents.py`); to be checked |
| Setup questions | One-off facts: accounting method, state rules, rates | Partly (policies exist; the builder-facing questions do not) |
| Integrations through AUIF | Recurring feeds from the builder's software | No connectors yet (Amir, at the end) |

Every path feeds the same pipeline, so manual data is never a way around the controls (S04 §18).

## Estimates and confidence

APG may estimate a missing input only where a documented method exists, and every estimate is labelled as one until real data replaces it; it never silently fills a gap (S04 §10, S05 §5.2).

- **Labels on every figure:** evidenced, estimated (with the method), stale (with its age), missing, or scenario.
- **A warning built on estimates says so,** and names the estimate it rests on.
- **No estimate for material contractual or financial facts** (contract value, claimed amounts, deadlines): those stay missing until supplied or verified.
- **Confidence affects action:** a qualified insight can inform, but cannot trigger a consequential recommendation that the blueprint reserves for evidenced inputs.

Open question for the owner: which estimating methods are allowed (for example, progress inferred from claims), and for which insights.

## Integration mapping per builder software

For each software APG connects to, a map records which of its fields fill which contract inputs, so a builder's gaps are known before they sign up.

- **One map per product and version,** held in the source registry S04 §4 already requires (fields supplied, cadence, limits).
- **Its output is the readiness report for that product:** for example, "on this software, the forecast and variations come through; programme progress does not, so use the progress screen".
- **First maps:** the products used by the initial segment, Victorian commercial builders of about $5–50m turnover; the list is to be confirmed with the pilot builders.
- **Before any connector exists,** the same map can be built from a sample export, which is also the first step of the profit autopsy.

## Decisions for the owner, and the review

This is a first draft for direction; it changes no locked section and no stage 1 work.

1. Adopt the two guarantees in "The requirement" as APG's definition of fail-proof on our end.
2. Approve the four new record kinds the matrix found missing: programme and progress, client claims and payment schedules, labour rates, estimate lines.
3. Approve entry screens, the readiness report and site capture as required features, not optional add-ons.
4. Set the minimum and good level for each insight (the contract table holds first proposals).
5. Decide which estimating methods are allowed, and for which insights.

**Known open items (the reviewers are asked to check what they can):**

- [ ] Check the matrix field by field within each record kind, not only by kind.
- [ ] Check each contract row against the rule and calculation specifications; some descriptions are drafted from the rule names (R04, R04b in particular).
- [ ] Cross-check against the Master Requirements Traceability Matrix and the 8-layer data contracts.
- [ ] Map one real builder export (the profit autopsy data) as the first integration map.

GPT (and Gemini, if used) review the whole draft in one pass, listing every finding classed as blocking, should fix, optional or minor, with a rough cost, before the owner decides.
