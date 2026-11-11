# APG Data Readiness Change Request (revision 2)

Nov 11, 2026 · @Emmanuel

APG must know, for every insight, exactly which data it needs, check what each builder supplies, say plainly what is missing and who can supply it, and offer a working way to supply each gap inside APG; until a gap is filled, no insight may present a result its evidence does not support. This revision answers the three reviews of draft 1 (GPT, 33 findings; Gemini, two passes); "Review responses" at the end maps each finding to its fix.

**Status:** design direction only. It authorises no production feature code or integration work: under S04 §20 that waits for the Section 01 Discovery Exit Report and the owner's decisions below.

## The requirement and the two guarantees

The owner's requirement (2026-11-11): APG must state exactly what data it needs; when a builder's software supplies only part of it, APG's own features must supply the rest, so APG gets what it needs to work.

"Fail-proof on our end" means two guarantees about evidence and decisions, not a promise that every answer is correct:

1. **No result beyond its evidence.** For every insight, APG identifies the inputs its blueprint rules require (fields, status, source authority, freshness) and which of them are present, absent, stale, conflicting, quarantined, provisional, unverified or estimated. A result is shown only at the eligibility its own blueprint gate allows: eligible, qualified, blocked or unavailable. A gap is never silently treated as satisfied, and an estimate is never shown as a fact.
2. **A way to supply every gap.** For each missing input, APG names it, says who in the builder's business normally holds it, and offers a working way to supply it inside APG; where no supported path exists yet, it says so plainly instead of implying one.

Both are testable: each insight's gate, each status and each supply path can be exercised with planted gaps, as the stage 1 evidence does for the calculation core.

## What is specified, what exists, what is unverified

The locked blueprint already requires the fail-safe controls; the code holds parts of them; none of it is yet verified against a real builder's data.

| Requirement | Specified in | Present in the code (builder inventory) | Not yet established |
| --- | --- | --- | --- |
| No invented values or silent defaults | S04 §10, PG-DI-AC-11 | Intake pipeline outcomes (accepted, warnings, pending, quarantined) | Behaviour on real exports |
| Freshness and completeness by source, project, domain and decision use, with decision-aware thresholds | S04 §14, PG-DI-AC-13 | `apg/ingest/freshness.py` (decision eligibility) | Thresholds per insight; scheduled reassessment; the builder-facing report |
| Quarantine; provisional use isolated and labelled | S04 §9 | `apg/ingest/review.py`, pipeline outcomes | Review screens for the builder |
| Human verification of material AI/OCR values | S04 §12 | `apg/ingest/documents.py`; `quote_reading.verified_by` | Verification queue in the UI; email and phone capture |
| Field-level Source Authority Register; source registry | S04 §4, §5 | `apg/source_authority.py` (synthetic register) | Builder setup and approval of the register |
| Manual entry and imports never bypass the controls | S04 §18 | 36 import templates (one per record kind, plus one alternative layout) | All 36 are Builder Zero layouts, marked "draft - unverified against any real export"; no entry screens |
| Qualified forecast when inputs are missing or stale, each value labelled | S05 §5.2 | `apg/fin/figure.py` (qualified figures), `apg/fin/forecast.py` | The insight-level readiness record |
| Evidence gates for holding cost, landed cost, productivity, deadlines, cash and quality | S07, S08, S09, S11, S12, S13 | Partly, per module | The missing records in the gap analysis below |
| Data-integrity findings kept apart from leakage | S06 §4 | `apg/det/findings.py` | Readiness findings in the builder's report |

## The data model gap analysis

The gap is larger than draft 1's four record kinds: of 45 logical entities the blueprint needs, 2 are covered, 32 partly and 11 are missing, and they split into what the builder must supply and what APG must create.

| Class | What it is | Entities | Missing | Partly covered |
| --- | --- | --- | --- | --- |
| Builder-source records | Facts the builder's systems or people hold | 31 | client progress claims; client payment schedules; receivables and receipts; subcontractor claims, assessments and payments; estimate lines; programme versions, activities and dependencies; progress | project, head contract, variations, site instructions, notices, subcontracts, purchase orders, invoices, materials, budgets, cost to complete, delay events, labour, plant, defects, bank, retention, security, payables, suppliers (quotes covered) |
| Configuration and policy | Set once by the builder, then versioned | 6 | cost-code map; accruals and overhead allocation; labour rates and on-costs | Source Authority Register, holding-cost rates, accounting and contract policies |
| APG internal records | Created and maintained by APG | 5 | quality root cause, rectification and closure records | provenance fields, baselines and scenarios, findings and decisions, the readiness record |
| Evidence and documents | Documents that support facts | 2 | none | compliance evidence; documents and their verification |
| External reference | Market and FX data | 1 | none | none (covered) |

The full analysis, row by row with the blueprint section, the required field groups, the fields present today, the gap, the supply paths and the likely data owner, is in `DATA_MODEL_GAP_ANALYSIS.csv`; the fields present come from `FIELD_REGISTER.csv`, generated from the 36 templates (215 fields).

Two findings matter most for the owner's 80% / 20% question:

- **Claims and payments are the biggest hole.** APG has no record of claims on the client, client payment schedules, receivables, or subcontractor claims, assessments and payments. These are where much construction profit leaks, and what the cash view depends on.
- **Cost codes need a map.** APG carries the builder's cost codes as given; every builder codes differently, so a cost-code map is needed at setup: APG suggests it, the builder confirms it (S06 §5.6 keeps AI from changing authoritative inputs).

## The insight contracts

Each insight's contract names the fields it needs, the status distinctions it must keep, its blueprint gate, and four separate quality measures: completeness, freshness, verification and coverage. A contract starts provisional and becomes final only when the insight's rule code and tests have been inspected against it.

| Insight | Blueprint gate | Required inputs (field groups) | Completeness | Freshness (good / minimum, proposed) | Verification | Below the gate |
| --- | --- | --- | --- | --- | --- | --- |
| Recognised margin | S03 §5.1, §6; 8-layer 02 §2.4 | recognised revenue on the owner-approved basis (contract, approved variations, certified claims), recognised cost (invoices, credits, accruals), tax basis, period | every cost and revenue component for the period under the approved policy | monthly / quarterly | invoices and claims reconciled to source | not assessable; names the missing component or policy |
| Forecast final margin and cost to complete | S05 §5.1–5.3; S03 §5.2, §6.3 | the adopted forecast version (owner, date, approval), cost to complete by cost code, actuals and commitments without overlap, forecast revenue, assumptions, holding-cost inputs where used | every budgeted cost code mapped and forecast | monthly / quarterly | forecast approved by its owner | qualified provisional forecast listing missing or stale codes (S05 §5.2); never the authoritative forecast |
| Committed cost | S03 §7; S05 §6 | orders with revision, approval, status (approved, cancelled, superseded), cost code; amendments with approved change; subcontract variations | every order in an approved state, under the commitment policy | 30 days / 60 days | approval state from the authoritative source | commitment total qualified as incomplete |
| Budget variance (R01), order amendment (R02), forecast movement (R09) | S05 §5.3; S06 §5.2 | R01: budget revisions with approval; R02: amendments with reason and approval; R09: two adopted forecast versions | per rule, inspected from its code | per rule | per rule | finding withheld; data gap reported (provisional until the rule code is inspected) |
| Invoice against order (R03) | S04 §11 | invoice lines linked to order lines and project; partial deliveries; credits and amendments; duplicate candidates | each invoice reconciled or held as an exception | timeliness reported separately as a source service measure | reconciliation outcome recorded | unmatched invoices held, never force-matched |
| Unclaimed variations (R04) and instructions without a variation (R04b) | S11 §4–6 | per rule, inspected from its code; S11 evidence: instruction, scope, drawings/revisions, quantities, valuation evidence | per rule | per rule | entitlement never inferred | provisional until the rule code and tests are inspected; operational evidence never shown as entitlement |
| Retention intelligence | S03 §10.1; S12 §7 | clause and basis; withheld, claimed for release, approved, released, outstanding; due/review date; conditions, disputes, linked defects (held by the client and from trades) | each retention with its clause | monthly / quarterly | clause verified | release timing not inferred without terms |
| Security instruments | S03 §10.2; S12 §8–9 | type, issuer, beneficiary, face value, issue and expiry dates, release conditions, fees, facility usage | each instrument with its conditions | monthly / quarterly | document verified | face value never treated as cost |
| Carrying cost of retention and security | S03 §10.4; S12 | eligible tied-up balance, period, annual rate and its source, day-count convention, method, facility fees, overlap checks | the full S12 evidence set | facility statement monthly / quarterly | rate source recorded | not calculated; never from face value alone |
| Supplier and subcontractor compliance (R06) | S04 §2; S09; S13 | evidence type, holder, trade/work, jurisdiction, coverage/limit, issue/expiry dates, source, verification status | every active trade | before expiry / at expiry | document verified | status "unknown", never "compliant" |
| Quote comparison, landed cost, buy timing (R07) | S08 §4–7; S03 §8.3–8.4 | specification, quantity/unit, quote date and expiry, supplier, delivery basis, inclusions/exclusions, currency/tax, terms, freight, duty, insurance, storage, lead time; market data by source type | the comparability set for the decision | quote valid / S08 §7.1 thresholds per decision | extracted quote values human-verified (S04 §12) | indicative comparison only; definitive ranking blocked |
| Plant hire idle cost (R08) | S09; S07 §5 | on/off-hire dates, off-hire request and confirmation, minimum hire, usage or idle evidence, rate basis, project/activity allocation | idle status evidenced | weekly / monthly | supplier docket | qualified date-based exposure only |
| Delay events and holding cost | S07 §3–6; S03 §9 | dated event first; to quantify: approved programme version, activities and dependencies, actual progress, attribution state, counterfactual, evidenced rates, eligible duration, overlap | two levels: event identified / cost quantified | weekly / monthly | rate and duration evidenced | event shown; cost unquantified or qualified (S07); critical-path analysis only past S07 §4.1's gate |
| Labour productivity | S09 §3, §5–6, §14 | pseudonymous worker, employer, trade, crew, work allocation, hours, rates and on-costs, accepted output, comparable baseline, conditions | the S09 comparison gate | weekly / monthly | output accepted | qualified indicative comparison; never a conclusion about a person or crew |
| Defects, rework and quality cost | S13 §3, §5–8 | observation, defect, rework event, cause (hypothesis vs confirmed), rectification, closure verification, actual vs estimated cost | each defect with location and trade | weekly / monthly | closure verified | recurrence only; no cost or fault without evidence |
| Cash-position-adjusted margin | S03 §5.3; S12 §3–5, §10–13 | actual bank cash, scheduled receipts and payments, claims awaiting certification, certified receivables, disputed amounts, retention, security, facility costs, each kept separate | each cash component named, or stated as not assessable | bank daily / weekly; claims monthly / quarterly | reconciled to bank | not assessable until the claim, receivable and payment-schedule records exist |

The freshness levels are proposals from the Gemini design review, aligned to monthly claim and accounting cycles; the owner sets them.

## Readiness: three separate states

APG keeps three states apart, so one simple label never hides a blueprint gate:

1. **Ingestion state of each record:** accepted, accepted with warnings, pending reconciliation, quarantined or rejected (S04 §8).
2. **Readiness of each insight:** eligible, qualified, blocked or unavailable, decided by that insight's own gate (S05 §5.2, S07 §4.1, S08, S09, S11 human review).
3. **Action eligibility:** whether a finding may drive a recommendation; consequential actions stay reserved for evidenced inputs and human approval.

How the builder sees it:

- **Nudges, not a dashboard:** short, specific messages to the person who can fix the gap, for example "3 subcontractor invoices from one trade have no cost code: fix them here". A full readiness view stays for setup and review.
- **Each gap names its owner by role:** contract administrator, bookkeeper, project manager, site manager or estimator, configurable per builder.
- **Fix-first list:** gaps ranked by the money they put at risk.
- **Framed as profit risk, honestly:** "possible unbilled variations: 4 instructions with no claim entry, up to $45,000 at risk". A data gap is never called confirmed leakage (S06 §4).
- **When it runs:** at setup, after every intake, on a schedule (a source can go stale with no new data), and whenever a record is corrected, quarantined, superseded or revoked (S04 §14, S06). Last receipt, last processing and last reconciliation are kept distinct.

## One intake contract for every path

Every way data enters APG passes the same Section 04 controls; no screen, setup answer, email or estimate is a way around them (S04 §18).

Each path must keep: the source and its evidence; identity and duplicate handling; project and tenant scope; field-level source authority; validation; reconciliation; the record's status; reviewer and approval state; audit history; freshness.

| Path | What it fills | Extra rule for this path | Exists today |
| --- | --- | --- | --- |
| Integration through AUIF | recurring feeds from the builder's software | a versioned source profile (below) | no connectors (Amir, at the end) |
| Email and document capture | claims, payment schedules, variations, quotes, invoices, compliance documents | material values extracted by AI/OCR stay provisional until a person confirms them, one tap per document (S04 §12) | partly (`apg/ingest/documents.py`) |
| Phone site capture (CR-05) | progress, delays, defects with photos, plant and labour on site | the person, time and place recorded as evidence | no |
| Entry screens | small, frequent gaps: one forecast line, one variation, one delay | entered values carry the person and need approval where the register says so | no |
| Import templates | bulk data from spreadsheets and exports | each builder's layout mapped and checked once; row-level errors | mechanism yes; templates are synthetic layouts |
| Setup questions | policies and rates: margin and revenue basis, commitment rules, tax, holding-cost and labour rates | versioned; owner approval where the decision register requires it | partly (policies in code, no builder questions) |

Coverage of each input is recorded in five steps, not one: capture available, validation available, authority established, reconciliation available, decision-eligible. A template that accepts a value does not by itself make it correct.

## Estimates

APG may estimate a derived result from disclosed assumptions; it must never invent a missing authoritative fact. Four kinds of value are kept apart: estimates of a missing source fact, builder-supplied forecasts and assumptions, APG-derived qualified calculations, and scenarios.

| Method | Position | Conditions |
| --- | --- | --- |
| Builder-entered cost to complete or forecast | allow | labelled forecast, versioned, dated, attributed to its owner |
| Deterministic calculation from evidenced inputs | allow | formula, inputs, authority, tax/currency basis and version kept |
| Run-rate projection of a stale cost to complete (Gemini) | allow as provisional only | labelled "estimated: run-rate projection", never the authoritative forecast, accepted or overridden by the builder in one step (S05 §5.1–5.2) |
| Holding cost | allow conditionally | S07 and S12 evidence gates met |
| Landed cost | allow conditionally | S08 inputs sufficient; omissions disclosed |
| Indicative market comparison | allow conditionally | source and date visible; stale evidence qualified |
| Scenario | allow | isolated from the authoritative forecast |
| Progress inferred from claims | not as progress | a claim is not proof of physical progress; at most a labelled investigative indicator |
| Labour cost from generic award rates | not as cost | only the builder's verified classification and rates |
| Contract value, claimed amount, approval, deadline or entitlement inferred by AI | never | source evidence and human verification only |
| Carrying cost from face value alone | never | S12 needs the eligible balance and period |

## Source profiles and integration mapping

For each builder software product, a versioned source profile records everything S04 §4 requires, so a builder's gaps are known before they sign up.

- **Contents:** fields supplied and their mapping to APG fields; authority per field (linked to the Source Authority Register); authentication and permissions; transport, cadence, batching and rate limits; schema version; duplicate, retry and error handling; known limits; last receipt, reconciliation and health.
- **Its output** is the readiness forecast for that product: which insights it can feed, and which gaps another path must fill.
- **First profiles** come from sample exports of the pilot builders' systems. A mapped export is a mapping exercise, not proof of a live connector.
- **"Where builders usually hold it"** in the gap analysis is a list of likely locations, to be validated with pilot builders; no coverage promise is made from it.

## Decisions for the owner

**Now, to set the direction:**

1. Adopt the two guarantees as APG's definition of "fail-proof on our end".
2. Approve the data model scope: the 11 missing entities and the partial ones in the gap analysis, split into what builders supply and what APG maintains.
3. Approve as required features: email and document capture, phone site capture, entry screens, the cost-code map at setup, nudges to named roles, and the readiness view.
4. Set the freshness levels (the table holds proposals).
5. Approve the estimating table above.

**Required before production** (a register, decided as each part is designed):

- the ten shared financial foundation decisions (8-layer 02 §2.11): margin measures, revenue basis, cost taxonomy, contingencies, tax basis, cost-to-complete method, variation treatment, approval roles, freshness rules, rounding and currency;
- the Source Authority Register and who approves it;
- baseline and assessment governance;
- the commitment policy;
- labour data privacy and role permissions (S09 §14);
- retention and security state handling;
- the contractual and accounting policies each insight's contract names.

**Next steps after the owner's decisions:**

- Inspect each rule's code and tests against its contract (every "provisional" row), and generate a full field-level schema register with validation rules and tests.
- Map one real builder export (the profit autopsy data) into a first source profile.
- A scoped re-check by GPT against its 33 findings and Gemini's, then the owner decides; no further review rounds unless that check finds a blocking issue.

## Review responses

Every finding of the three reviews of draft 1, and where this revision answers it. All are accepted except where the response says otherwise.

| Finding | Where answered |
| --- | --- |
| GPT B1 guarantees not testable; supply path missing | The requirement and the two guarantees |
| GPT B2 specified vs delivered blurred | What is specified, what exists, what is unverified |
| GPT B3 contracts list record kinds, not fields and states | The insight contracts |
| GPT B4 four missing kinds understate the data model | The data model gap analysis (45 entities, 11 missing, by class) |
| GPT B5 template coverage not established | Specified table: 36 templates found, all synthetic Builder Zero layouts unverified against real exports; `FIELD_REGISTER.csv` |
| GPT B6 controls per path | One intake contract for every path |
| GPT S1 recognised margin basis | Insight contracts, recognised margin; foundation decisions in the register. Note: the margin module builds on the revenue and cost modules, so "reads project only" in the inventory is not itself a gap |
| GPT S2 commitment rule | Insight contracts, committed cost; commitment policy in the register |
| GPT S3 forecast governance | Insight contracts, forecast final margin |
| GPT S4 R01, R02, R09 mapped separately | Insight contracts (provisional until the rule code is inspected) |
| GPT S5 invoice matching, not same-day posting | Insight contracts, R03 |
| GPT S6 R04, R04b from names | Insight contracts (provisional; next steps) |
| GPT S7 retention, security and carrying cost; `retention_event` | Three separate contracts; `retention_event` is created by APG (`apg/fin/cash_states.py`), not supplied by the builder |
| GPT S8 compliance evidence | Insight contracts, R06 |
| GPT S9 quote comparability | Insight contracts, R07 |
| GPT S10 plant idle evidence | Insight contracts, R08 |
| GPT S11 delay: event vs quantified cost | Insight contracts, two levels |
| GPT S12 labour inputs and fairness | Insight contracts, labour productivity |
| GPT S13 quality lifecycle | Gap analysis (APG internal records) and insight contracts |
| GPT S14 cash-adjusted margin | Insight contracts; not assessable until claim and receivable records exist |
| GPT S15 matrix omits data groups | The data model gap analysis |
| GPT S16 source locations are assumptions | Source profiles: likely locations, to be validated |
| GPT S17 readiness states too generic | Readiness: three separate states |
| GPT S18 readiness only at refresh | Readiness: when it runs |
| GPT S19 integration map incomplete | Source profiles and integration mapping |
| GPT S20 estimates of inputs vs outputs | Estimates |
| GPT S21 decision list incomplete | Decisions: required before production |
| GPT S22 discovery gate | Status line at the top; decisions |
| GPT O1 actionable report | Readiness: fix-first list |
| GPT O2 accept vs verify | One intake contract: five coverage steps |
| GPT O3 data owner column | Gap analysis "likely data owner"; readiness: owner by role |
| GPT M1 good level mixes measures | Insight contracts: four separate measures |
| GPT M2 capability states | Specified table and the five coverage steps |
| GPT estimating table | Adopted in Estimates |
| Gemini design 1: CSV-heavy; email and mobile capture | One intake contract: email/document and phone capture as main paths |
| Gemini design 2: subcontractor claims; cost-code map; data ownership | Gap analysis (subcontractor claims, cost-code map); readiness owner by role |
| Gemini design 3: nudges, not a dashboard | Readiness |
| Gemini design 4: freshness levels | Insight contracts (adopted as proposals) |
| Gemini design 5: run-rate estimates | Estimates (provisional only, builder accepts or overrides) |
| Gemini design 6: cost-code decision | Decisions 2 and 3 |
| Gemini design 7: frame gaps as profit risk | Readiness, worded so a gap is never called confirmed leakage (S06 §4) |
| Gemini evidence 1: R04/R04b | As GPT S6 |
| Gemini evidence 2: guarantee wording | As GPT B1 |
| Gemini evidence 3: new kinds need an amendment | Decision 2; the new entities go through the blueprint's controlled change governance (S18), under a new number (CR-06 is taken) |
| Gemini evidence 4: freshness | As Gemini design 4 |
| Gemini evidence 5: cross-references | Kept; the full matrix cross-check remains a next step |
