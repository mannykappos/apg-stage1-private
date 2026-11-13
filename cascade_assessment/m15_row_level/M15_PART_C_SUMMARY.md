# M15 row-level check, Part C (Sections 08 to 13)

INDEPENDENT READ-ONLY (agent). Design work only: nothing was built. Every one of the 673 rows in `in/RTM_PART_C.csv` was read and judged against `in/ENTITY_REGISTER.csv` (the required field groups) and the M15 proposed fixes. Each row was read in the context of its section text. The per-row results are in `out/M15_PART_C.csv`.

## 1. Counts by verdict

| Verdict | Rows |
| --- | --- |
| COVERED | 204 |
| COVERED-BY-PROPOSED | 24 |
| GAP | 162 |
| NO-DATA-NEED | 283 |
| **Total** | **673** |

Rows with a data need: 390. Of these, 204 are covered, 24 are covered only by an M15 fix, and 162 are gaps.

How I judged:
- Scope bullets that name data APG must hold were judged Y. The brief lists "scope" as No, but it also says "when unsure, say yes", and these bullets name records outright.
- Headings, tests, audit instructions, delivery and closure-evidence lists and lock records are N. So are lead-in sentences that only introduce a list (the list items are judged on their own rows).
- Implementation-instruction bullets are Y only when they name a specific kind of record (for example "recommendation lifecycle" or "source register").
- A generic entity was counted only where its named field group really holds the item. E45 measures and E46 outputs were accepted for calculated results. A field the text names that has no matching field group was counted as a gap.
- Where a row is partly covered and partly a gap, the verdict is GAP, and the note says which part is missing.

## 2. Gaps

There are 162 GAP rows, which come down to 24 distinct missing items. Each item has its own smallest fix. The rows under each item are listed with the requirement's words. Where a row touches two items, it is listed under each, and the per-gap row counts add up to more than 162.

Summary of the fixes:

| Gap | What is missing | Smallest fix | Rows |
| --- | --- | --- | --- |
| G-REC | Recommendation record is too thin (E86: finding, action, conditions) | Field groups on E86 Recommendation: category; prioritisation factors (one field per s4 dimension) with the ranking method version; lifecycle state and history; eligibility outcome and decision deadline; dependencies; constraints and required approvals; responsible authority; outcome-verification method; closure reason. | 30 |
| G-BEN | Benefit state and its verification are not carried | (a) Field group on E88 Outcome: benefit state (the S05 s10 states), baseline reference, implementation evidence, verified by and when, offsetting costs, realised net benefit, variance against the estimate. (b) Field group on E44 Baseline, for benefit baselines: scope and period covered, comparability characteristics, historical rate or frequency, exposure volume, relevant changes. | 25 |
| G-REL | Finding relationships and overlap groups are not carried | Field group on E84 Finding: linked findings (relationship type), shared event or cause, overlap group, and the aggregation rule applied. | 19 |
| G-FND | Finding lifecycle is not carried | Field group on E84 Finding: deduplication identity, lifecycle status and history, ownership (responsible role, reviewer, next review date), disposition (decision, rationale, approver). | 5 |
| G-SCN | Scenario record lacks action, dependencies and verification fields | Field group on E46 Scenario: proposed action, affected activities and resources, dependencies and required approvals, invalidating conditions, outcome-verification method, reversibility. | 7 |
| G-CMP | Result of the specification comparability gate is not carried | Field group on E30 Supplier quote: comparability class against the specification requirement (E27), differences found, documented adjustments and their basis, assessed and verified by. | 6 |
| G-MKT | Market observation lacks currency, scope, methodology, limitations and validity | Field group on E36 Market observation: currency, specification scope, methodology, limitations, validity window, retrieval timestamp, conversion method, verification class. | 3 |
| G-DEM | Material demand lacks delivery location, waste allowance and drawing; orders lack expected delivery | Field group on E28 Material demand: delivery location, waste allowance, source drawing and revision, approval state. E21 lines gain expected delivery date and location. | 1 |
| G-DL | Deadline record lacks calculation method, interpretation status and responsibility | Field group on E12 Deadline: calculation method and assumptions, required action, interpretation status (verified administrative / inferred from ambiguous wording) with reviewer, last verification date, responsible role. E75 release conditions gain interpretation status. | 7 |
| G-CLM | Contract schedule-of-rates/BoQ items and claim-line quantities are not carried | Extend M15 fix 4: E08 gains the SoR/BoQ items (item ref, description, unit, contract quantity, rate). E13 lines gain claimed quantity, rate and contract-item ref. | 1 |
| G-HC | Head contract lacks approved scope/exclusions and valuation rules | Add to the E08 field groups of M15 fix 4: approved scope and exclusions, valuation rules. | 1 |
| G-VAR | Variation lacks assumptions and unresolved questions | Field group on E09 Variation: commercial assumptions and unresolved questions (open/resolved), affected dates. | 1 |
| G-SEC | Security instrument record is incomplete | Field group on E78 Security instrument: instrument reference, currency, project and obligation secured, renewal terms, cancellation conditions, collateral, cash margin, linked facility (E74), lifecycle status, responsible owner. | 9 |
| G-FIN | Funding facility lacks day-count convention and financing assumptions | Field group on E74 Funding facility: day-count convention, rate type and effective dates, documented financing assumptions. | 3 |
| G-FA | No entity for final-account items and post-completion obligations | New entity, Close-out obligation and final-account item: head contract, type (final-account item, close-out obligation, required certificate, warranty obligation), description, amounts (claimed, agreed, disputed), status, due date, responsible party, evidence. | 8 |
| G-PT | Supplier payment terms are not carried | Field group on E21 Purchase order (with a default on E20): payment terms and deposit terms. | 1 |
| G-PROV | Provenance fields lack timestamps | Field group on E01: source timestamp, received/extracted timestamp, effective date. | 2 |
| G-AUD | No general state-transition record | Field group on E01 (every record): state history of from-state, to-state, triggering event, evidence ref, actor or rule, timestamp. | 2 |
| G-DCL | Defect and observation classification and links are missing | Field groups on E66 Defect: defect type, classification flags per s13.4 dimension (safety and compliance kept apart from financial severity), links to material (E26), supplier (E20) and delivery (E29), installation method, design detail/interface ref. On E65 Quality observation: observation type (inspection, test, commissioning, handover, reported issue), stage, result. | 19 |
| G-QCFG | No setting for the defect classification scheme and the closure evidence it requires | Field group on N01: quality settings, namely the defect classification scheme and the closure evidence required per defect class or transition. | 2 |
| G-QC | Quality cost cannot separate cost components or recovery states | Field groups on E71 Quality cost: cost component (the s13.5 list); value state extended to potential recovery, approved/recognised recovery and actual recovered; recovery counterparty; verification state. | 16 |
| G-RCA | Root-cause hypothesis lacks review outcome and unresolved questions | Field group on E68: review status/outcome (open, rejected, confirmed with link to E69), unresolved questions. | 1 |
| G-INT | Work interruption record lacks duration, resources affected and cause status | Field group on E63 Work conditions record: duration or hours lost, crew/resources affected, recorded reason, cause status (observed, suspected, supported). | 1 |
| G-ALLOC | Work allocation lacks activity, location and task | Field group on E58 Work allocation: programme activity (E48), location, assigned task. | 1 |

Two of these are new entities or settings rather than field groups: **G-FA** (a new entity) and **G-QCFG** (an N01 settings group). Everything else is a field group on an existing entity.

### G-REC: Recommendation record is too thin (E86: finding, action, conditions)

**What is missing.** S10 needs each recommendation to keep its category (s5), its prioritisation factors held separately (s4: magnitude, urgency, confidence, time sensitivity or decision deadline, actionability, implementation cost, net benefit, dependencies, risk and constraints), its lifecycle state (s9: generated, awaiting evidence, awaiting approval, approved, rejected, deferred, in progress, completed pending verification, verified outcome, closed without implementation), the approval it needs and the responsible authority, how its outcome will be verified, and its version history (s10). E85 Alert holds one priority value, which is the single score S10 forbids. Execution state and urgency have no home anywhere.

**Proposed fix.** Field groups on E86 Recommendation: category; prioritisation factors (one field per s4 dimension) with the ranking method version; lifecycle state and history; eligibility outcome and decision deadline; dependencies; constraints and required approvals; responsible authority; outcome-verification method; closure reason.

| Row | Requirement words | Row note |
| --- | --- | --- |
| APG-S09-C0070 | No productivity or cost-improvement recommendation may bypass required safety, quality, competence, inspection, design or contractual controls, regardless of estimated financial benefit. Where a proposed scenario conflicts with such a control, it must be blocked or referred for authorised resolution, not presented as a ... | G-REC: E86 has no lifecycle state (blocked, referred, awaiting approval). |
| PG-RS-AC-01 | PG-RS-AC-01: Ranking factors remain visible and explainable. | G-REC: E85 holds one priority value and E86 none; the separate factor values are not carried. |
| PG-RS-AC-02 | PG-RS-AC-02: Financial magnitude, urgency and confidence remain distinct. | G-REC: E84 has quantification and confidence but urgency has no home. |
| PG-RS-AC-05 | PG-RS-AC-05: Safety, quality and approval constraints cannot be bypassed by a high score. | G-REC: E86 has no constraint or blocked state. |
| PG-RS-AC-09 | PG-RS-AC-09: Approval and execution states remain distinct. | G-REC: approval is in E87; no entity holds execution state (in progress, completed pending verification). |
| APG-S10-C0016 | Before prioritisation, assess evidence sufficiency, data freshness, duplication/overlap, financial status (authoritative, qualified or scenario-only), user authority, mandatory safety/quality/legal/contractual reviews, continued actionability and decision deadlines. | G-REC (eligibility outcome, actionability, decision deadline) and G-REL (overlap). |
| APG-S10-C0017 | A finding with unresolved critical evidence must not be presented as an unrestricted ready-to-execute recommendation. It may be prioritised for investigation or evidence collection when that is the valuable next action. | G-REC: no category (Investigate) or state (awaiting evidence). |
| APG-S10-C0019 | The engine must not collapse every consideration into one unexplained score. Expose dimensions separately: | G-REC. |
| APG-S10-C0027 | Dependencies: Other decisions, people or work packages required. | G-REC. |
| APG-S10-C0028 | Risk and constraints: Potential adverse effects and required approvals. | G-REC: E86 conditions are partial; required approvals not held. |
| APG-S10-C0029 | Confidence must not be confused with magnitude. A large low-confidence estimate is not automatically superior to a smaller, well-supported and time-critical issue. Ranking logic and factor values must be explainable and auditable. | G-REC (factor values); method version in E45. |
| APG-S10-L0031 | Investigate: obtain missing evidence or resolve conflicting data. | G-REC: E86 has no category field. |
| APG-S10-L0032 | Prevent: act to avoid a potential loss. | G-REC. |
| APG-S10-L0033 | Correct: address an established operational or commercial problem. | G-REC. |
| APG-S10-L0034 | Recover: pursue supported recovery of cost or commercial value. | G-REC. |
| APG-S10-L0035 | Optimise: improve procurement, productivity, sequencing or resource utilisation. | G-REC. |
| APG-S10-L0036 | Negotiate: seek improved terms or resolve a commercial issue. | G-REC. |
| APG-S10-L0037 | Escalate: obtain a decision from a person with appropriate authority. | G-REC. |
| APG-S10-L0038 | Monitor: continue observing a developing risk or opportunity. | G-REC. |
| APG-S10-L0039 | Close: record resolution, rejection or loss of actionability with reasons. | G-REC: closure state and reason (resolution, rejection, loss of actionability); rejection reason alone fits E87 basis. |
| APG-S10-L0065 | Required approval and responsible authority. | G-REC: E90 holds approval roles in general; the approval required and the responsible authority per recommendation are not held. |
| APG-S10-L0066 | How the outcome will be measured and verified. | G-REC. |
| APG-S10-L0091 | Map recommendation lifecycle to actual Anchor finding, workflow, Governor and audit contracts after Section 01 discovery. | G-REC. |
| APG-S10-L0093 | Implement eligibility gates and explainable multi-factor prioritisation. | G-REC. |
| APG-S10-L0094 | Keep financial magnitude, urgency, confidence, time sensitivity, actionability, dependencies and risk separately visible. | G-REC. |
| PG-CR-AC-11 | PG-CR-AC-11: Recommendations identify evidence gaps, costs, risks and approvals. | G-REC (risks, required approvals). |
| APG-S11-L0093 | Integrate Sections 05–10 for financial integrity, finding lifecycle, schedule, labour and recommendation workflows. | G-FND and G-REC. |
| APG-S12-L0118 | Section 10 — Keep scenarios isolated and prioritise transparently with dependencies, net benefit, uncertainty, and human approval. | G-REC. |
| APG-S13-C0123 | Each material recommendation must identify its supporting evidence, expected outcome, implementation cost, dependencies, uncertainty and relevant safety, quality, contractual or operational constraints. | G-REC: dependencies and constraints not held. |
| APG-S13-L0139 | Section 10 — Recommendations: corrective actions are prioritised transparently, with costs, risks and dependencies. | G-REC. |

### G-BEN: Benefit state and its verification are not carried

**What is missing.** S05 s10 and its gate (repeated in S08 s11, S09 s13, S10, S11 s13, S12 s12.7/12.14 D, S13 s13.6/13.13 D) need a benefit to sit in an explicit state (identified, estimated gross, estimated implementation cost, estimated net, approved, implemented, observed, verified, realised net, reversed/not realised) and a verification tied to an approved baseline, with implementation evidence, the verifier, offsetting costs and variance against the estimate. E88 Outcome has only decision, realised result and date. S13 s13.6 also needs the savings baseline to define scope and period, comparable characteristics, historical frequency, exposure volume and relevant changes. E44 Baseline is the forecast baseline and names only version, snapshot, model version, assumptions and approval.

**Proposed fix.** (a) Field group on E88 Outcome: benefit state (the S05 s10 states), baseline reference, implementation evidence, verified by and when, offsetting costs, realised net benefit, variance against the estimate. (b) Field group on E44 Baseline, for benefit baselines: scope and period covered, comparability characteristics, historical rate or frequency, exposure volume, relevant changes.

| Row | Requirement words | Row note |
| --- | --- | --- |
| PG-MP-AC-15 | PG-MP-AC-15: Procurement savings remain non-realised until Section 05 verification is complete. | G-BEN: no entity holds the benefit state (identified ... verified, realised) or its verification. |
| APG-S08-L0016 | Benefits must be verified: estimates are not realised profit until Section 05 verification requirements are satisfied. | G-BEN. |
| APG-S08-C0068 | Each opportunity requires an approved baseline, comparable specification/quantity, documented calculation, estimated gross benefit, implementation/other incremental costs, schedule and quality implications, assumptions, uncertainty, approval/implementation status and evidence required to verify the result. | G-BEN: implementation status and verification evidence not carried; rest via E44/E45/E84/E87. |
| APG-S08-C0070 | A reported procurement saving must satisfy Section 05: approved comparable baseline, implementation evidence and authorised verification of actual outcome against baseline, including offsetting costs such as storage, waste, handling, freight, financing and other material effects. A negotiated quote or lower price on pa ... | G-BEN. |
| PG-LR-AC-15 | PG-LR-AC-15: Material savings satisfy Section 05 verification. | G-BEN. |
| APG-S09-C0059 | Section 05's realised-benefit verification gate is mandatory. An unimplemented recommendation or lower planned-hours scenario is not a realised saving. | G-BEN. |
| APG-S09-L0102 | Integrate Section 06 finding lifecycle and Section 05 financial and benefit-verification rules. | G-FND (E84 has no lifecycle status) and G-BEN. |
| PG-RS-AC-10 | PG-RS-AC-10: Realised benefits require verification. | G-BEN. |
| APG-S10-L0096 | Implement outcome tracking and verified-benefit workflows without mutating historical decisions. | G-BEN. |
| PG-CR-AC-13 | PG-CR-AC-13: Realised benefits satisfy Section 05 verification requirements. | G-BEN. |
| APG-S11-L0015 | Benefits require verification: identified, prepared or submitted claims are not automatically realised profit. | G-BEN. |
| APG-S11-C0069 | Commercial opportunities remain estimates until their financial outcome is supported and verified. Verification must account for applicable approval/certification, invoicing and collection states, incremental delivery costs, disputes, financing effects, offsets and overlapping benefits. These states are tracked separat ... | G-BEN (and G-REL for overlaps). |
| APG-S12-C0074 | If evidence is incomplete, label the result as provisional/qualified and explain what is missing. Do not imply that the full face value of a retention or security instrument incurred financing cost for the whole period. Avoid double-counting the same funding exposure across projects, cost categories, or linked findings ... | G-REL and G-BEN. |
| APG-S12-C0106 | Improving cash timing is not automatically profit improvement. Any financing benefit or realised saving must be separately calculated, evidenced, and verified. Recommendations are advisory by default. The system must not autonomously issue binding instructions, cancel security, vary contracts, or make other consequenti ... | G-BEN. |
| APG-S12-L0113 | Section 05 — Keep recognised margin, forecast final margin, and cash-position-adjusted margin distinct; use approved benefit verification. | G-BEN. |
| APG-S12-L0114 | Section 06 — Apply finding lifecycle, repeated-finding controls, cross-domain overlap controls, and recommendation/outcome verification. | G-FND, G-REL, G-BEN. |
| APG-S12-C0128 | MANDATORY. Cash-timing improvements remain distinct from accounting margin and realised profit. Financing benefits are separately calculated and verified. | G-BEN. |
| APG-S13-L0028 | Preventive recommendations and verified quality-improvement outcomes. | Scope item. G-BEN. |
| APG-S13-L0078 | The work scope and period covered. | G-BEN (baseline field group). |
| APG-S13-L0079 | Comparable project, work-package or activity characteristics. | G-BEN. |
| APG-S13-L0080 | Historical defect or rework frequency. | G-BEN. |
| APG-S13-L0082 | Exposure volume or number of relevant activities. | G-BEN. |
| APG-S13-L0084 | Relevant changes in scope, specification, design, workforce or operating conditions. | G-BEN. |
| APG-S13-C0155 | MANDATORY. Claimed savings require an approved, versioned and sufficiently comparable baseline, implementation evidence, verified outcomes and relevant offsetting costs. Otherwise report qualified indicative improvement only. | G-BEN. |
| APG-S13-L0163 | Baseline-dependent savings calculations expose comparability, assumptions, offsets and verification status. | G-BEN. |

### G-REL: Finding relationships and overlap groups are not carried

**What is missing.** Many rows require related findings to be linked to a shared event or cause and overlapping amounts to be kept from being summed (S06 s6 "Relationships: linked findings, root-cause hypotheses and overlap/double-counting groups"; S06 s9). E84 Finding has rule, evidence, quantification, confidence and limits only.

**Proposed fix.** Field group on E84 Finding: linked findings (relationship type), shared event or cause, overlap group, and the aggregation rule applied.

| Row | Requirement words | Row note |
| --- | --- | --- |
| PG-MP-AC-13 | PG-MP-AC-13: Procurement benefits are linked to schedule, quality and finance without double counting. | G-REL: E84 has no linked-finding or overlap/double-counting group field. |
| APG-S08-C0065 | Quality, safety, design approval and relevant regulatory requirements are constraints, not merely optional financial weights. Link related effects to Sections 05–07 and prevent double counting—for example, the same avoided delay cost must not be counted independently in procurement and schedule benefits without an expl ... | G-REL. |
| APG-S08-L0108 | Connect schedule, quality, inventory and supplier-performance evidence through governed finding relationships. | G-REL. |
| PG-LR-AC-12 | PG-LR-AC-12: Related labour/schedule findings are linked without double counting. | G-REL. |
| APG-S09-C0052 | Related findings may be linked but costs must not be blindly summed twice. Recommendations must identify which constraints they expect to address and which remain unresolved. | G-REL (overlap); constraints addressed could sit in E86 conditions. |
| PG-RS-AC-04 | PG-RS-AC-04: Duplicate and overlapping findings do not inflate apparent value. | G-REL. |
| APG-S10-C0016 | Before prioritisation, assess evidence sufficiency, data freshness, duplication/overlap, financial status (authoritative, qualified or scenario-only), user authority, mandatory safety/quality/legal/contractual reviews, continued actionability and decision deadlines. | G-REC (eligibility outcome, actionability, decision deadline) and G-REL (overlap). |
| APG-S10-C0044 | Do not describe forecast savings as guaranteed profit or count the same benefit independently across procurement, schedule, labour and financial findings. | G-REL. |
| PG-CR-AC-10 | PG-CR-AC-10: Financing and other cost effects are not double-counted. | G-REL. |
| APG-S11-C0069 | Commercial opportunities remain estimates until their financial outcome is supported and verified. Verification must account for applicable approval/certification, invoicing and collection states, incremental delivery costs, disputes, financing effects, offsets and overlapping benefits. These states are tracked separat ... | G-BEN (and G-REL for overlaps). |
| APG-S12-L0073 | Overlap checks against other project costs, facility fees, and carrying-cost estimates. | G-REL. |
| APG-S12-C0074 | If evidence is incomplete, label the result as provisional/qualified and explain what is missing. Do not imply that the full face value of a retention or security instrument incurred financing cost for the whole period. Avoid double-counting the same funding exposure across projects, cost categories, or linked findings ... | G-REL and G-BEN. |
| APG-S12-L0105 | Potential overlap with other recommendations or financial exposures. | G-REL. |
| APG-S12-C0109 | Cross-domain impacts must be linked and reconciled. For example, one defect may affect rework cost, schedule, retention release, and cash forecast; these are related consequences, not four automatically additive independent losses. Preserve the underlying relationships and prevent double-counting. | G-REL. |
| APG-S12-L0114 | Section 06 — Apply finding lifecycle, repeated-finding controls, cross-domain overlap controls, and recommendation/outcome verification. | G-FND, G-REL, G-BEN. |
| APG-S12-C0124 | MANDATORY. Material estimates require an eligible balance, evidenced or explicitly qualified rate, defined period and method, and overlap checks. Missing evidence requires a qualified result, not false precision. | G-REL (overlap checks). |
| APG-S12-L0135 | Material financing-cost calculations expose balance basis, rate basis, eligible period, method/day-count basis, fees where applicable, uncertainty, and overlap controls. | G-FIN (day-count) and G-REL (overlap). |
| APG-S12-L0141 | Cross-domain linked consequences are traceable and not blindly added together. | G-REL. |
| APG-S13-L0164 | Cross-domain cost and schedule impacts are linked and protected against double-counting. | G-REL. |

### G-FND: Finding lifecycle is not carried

**What is missing.** Rows in Sections 09 to 13 point to the S06 finding lifecycle (status detected ... superseded, stable finding identity for deduplication, ownership, disposition and change history). E84 has none of these. This is mainly a Section 06 matter. Part B should confirm it.

**Proposed fix.** Field group on E84 Finding: deduplication identity, lifecycle status and history, ownership (responsible role, reviewer, next review date), disposition (decision, rationale, approver).

| Row | Requirement words | Row note |
| --- | --- | --- |
| APG-S09-L0102 | Integrate Section 06 finding lifecycle and Section 05 financial and benefit-verification rules. | G-FND (E84 has no lifecycle status) and G-BEN. |
| APG-S10-L0092 | Reuse Section 05 financial core and Section 06 finding lifecycle where appropriate. | G-FND. |
| APG-S11-L0093 | Integrate Sections 05–10 for financial integrity, finding lifecycle, schedule, labour and recommendation workflows. | G-FND and G-REC. |
| APG-S12-L0114 | Section 06 — Apply finding lifecycle, repeated-finding controls, cross-domain overlap controls, and recommendation/outcome verification. | G-FND, G-REL, G-BEN. |
| APG-S13-L0135 | Section 06 — Active intelligence: repeated findings update existing records through controlled lifecycle rules. | G-FND: no finding identity/lifecycle on E84. |

### G-SCN: Scenario record lacks action, dependencies and verification fields

**What is missing.** S10 s7, S09 s12, S11 s12 and S12 s12.11 say each scenario records its proposed action and the activities and resources it affects, its dependencies and required approvals, the conditions that would invalidate it, the method for verifying the outcome, and its reversibility. E46 has only base, assumptions, outputs and isolation.

**Proposed fix.** Field group on E46 Scenario: proposed action, affected activities and resources, dependencies and required approvals, invalidating conditions, outcome-verification method, reversibility.

| Row | Requirement words | Row note |
| --- | --- | --- |
| APG-S09-C0055 | Each scenario records baseline/version, activities/resources affected, output/duration assumptions, expected labour-hour change, incremental costs, quality/safety constraints, programme effects, uncertainty/evidence and required approvals. Scenarios are estimates, not guarantees. | G-SCN: E46 (base, assumptions, outputs, isolation) has no affected activities/resources or required approvals. |
| APG-S10-L0048 | Proposed action and affected activities/resources. | G-SCN. |
| APG-S10-L0051 | Dependencies and required approvals. | G-SCN. |
| APG-S10-L0054 | Conditions that would invalidate the recommendation. | G-SCN. |
| APG-S10-L0055 | Method for verifying eventual outcome. | G-SCN. |
| APG-S12-L0104 | Dependencies, data gaps, confidence/qualification, and reversibility. | G-SCN: dependencies and reversibility. |
| APG-S12-L0139 | Cash-timing scenarios disclose incremental costs, expected timing impact, trade-offs, uncertainty, and dependencies and remain isolated from the authoritative forecast. | G-SCN: dependencies. |

### G-CMP: Result of the specification comparability gate is not carried

**What is missing.** S08 s4.1 (mandatory) classes each comparison as comparable, comparable with adjustment (with documented adjustments), partially comparable, not comparable or unverified, and that class decides whether a definitive ranking is allowed. No entity carries the class or the documented adjustments. N01 holds the rules only, and E45 measures are generic.

**Proposed fix.** Field group on E30 Supplier quote: comparability class against the specification requirement (E27), differences found, documented adjustments and their basis, assessed and verified by.

| Row | Requirement words | Row note |
| --- | --- | --- |
| PG-MP-AC-02 | PG-MP-AC-02: Definitive supplier rankings are blocked unless specification and commercial terms are sufficiently comparable; indicative comparisons are clearly labelled. | G-CMP: no entity holds the comparability-gate result (class, differences, documented adjustments) per quote against the specification; only generic E45 measures. |
| APG-S08-L0034 | Comparable: specification and commercial basis sufficiently aligned. | G-CMP. |
| APG-S08-L0035 | Comparable with adjustment: differences can be addressed through documented adjustments. | G-CMP: documented adjustments have no home. |
| APG-S08-L0036 | Partially comparable: indicative benchmarking only, not definitive ranking. | G-CMP. |
| APG-S08-L0037 | Not comparable: material differences prevent defensible price comparison. | G-CMP. |
| APG-S08-L0038 | Unverified: required specification or source evidence is missing. | G-CMP. |

### G-MKT: Market observation lacks currency, scope, methodology, limitations and validity

**What is missing.** S08 s7 and s2 (and s14, which has no RTM row): each observation keeps source, observation date, currency, geographic scope, specification, units, methodology, limitations and validity window. S08 s14 also lists retrieval timestamp, conversion method and verified/indicative/scenario class. E36 has material, date, value, unit, source type and geography only.

**Proposed fix.** Field group on E36 Market observation: currency, specification scope, methodology, limitations, validity window, retrieval timestamp, conversion method, verification class.

| Row | Requirement words | Row note |
| --- | --- | --- |
| PG-MP-AC-07 | PG-MP-AC-07: Market references retain provenance, freshness and limitations. | G-MKT: E36 has date and source type but no validity window, limitations, methodology or currency. |
| APG-S08-L0013 | Freshness is explicit: market observations retain source, observation date and applicable validity window. | G-MKT: E36 has no validity window. |
| APG-S08-C0050 | Each observation retains source, observation date, currency, geographic scope, specification, units, methodology and limitations. Distinguish asking prices, quotes, indices and completed transactions; do not represent an indicative listing as a verified transaction. | G-MKT: E36 lacks currency, specification scope, methodology, limitations. |

### G-DEM: Material demand lacks delivery location, waste allowance and drawing; orders lack expected delivery

**What is missing.** The S08 s4 input list names delivery location, waste allowance, approved drawings and revisions, approval state and expected deliveries. E28 has material, quantity, unit and required date only. E21 lines have no expected delivery date. The M15 check read this list but did not raise these.

**Proposed fix.** Field group on E28 Material demand: delivery location, waste allowance, source drawing and revision, approval state. E21 lines gain expected delivery date and location.

| Row | Requirement words | Row note |
| --- | --- | --- |
| APG-S08-C0031 | Relevant inputs include canonical material identity, specification/grade/dimensions/performance requirements, approved drawings and revisions, quantity and unit, required-on-site date, delivery location, waste allowance, approved alternatives, quality/design/compliance constraints, existing stock, committed orders, exp ... | G-DEM: E28 has no delivery location, waste allowance, source drawing/revision or approval state; E21 lines have no expected delivery date. Stock needs proposed E100; alternatives need proposed E27 fix. |

### G-DL: Deadline record lacks calculation method, interpretation status and responsibility

**What is missing.** S11 s7/s7.1 says each deadline records clause, trigger, calculation method and assumptions, required action, last verification date, interpretation/approval status and responsible role. It must also tell verified administrative dates from dates inferred from ambiguous wording. S12 s12.8 asks for interpretation status on retention release conditions too. E12 has source clause, trigger, computed date and verification. E75 has no interpretation status.

**Proposed fix.** Field group on E12 Deadline: calculation method and assumptions, required action, interpretation status (verified administrative / inferred from ambiguous wording) with reviewer, last verification date, responsible role. E75 release conditions gain interpretation status.

| Row | Requirement words | Row note |
| --- | --- | --- |
| PG-CR-AC-05 | PG-CR-AC-05: Notice/submission dates record source and calculation basis. | G-DL: E12 (source clause, trigger, computed date, verification) has no calculation method or assumptions. |
| PG-CR-AC-06 | PG-CR-AC-06: Ambiguous contractual interpretations are qualified and referred for human review. | G-DL: no interpretation status (verified date vs inferred from ambiguous wording). |
| APG-S11-L0012 | Deadlines require traceability: potential notice/submission dates identify their source and interpretation status. | G-DL. |
| APG-S11-C0040 | Each deadline records underlying source and clause/rule where applicable, triggering event/reference date, calculation method/assumptions, required action/review, last verification date, interpretation/approval status and responsible person/role where known. | G-DL. |
| APG-S11-C0041 | Distinguish verified administrative dates from dates inferred from ambiguous contractual language. Do not autonomously determine entitlement, waiver, compliance with notice requirements or validity of a notice. Consequential interpretations and submissions require authorised human review. | G-DL: interpretation status. |
| APG-S11-C0043 | Contract-derived deadlines must be traceable to their source, trigger, calculation and review status. Ambiguous or consequential contractual interpretations require authorised human review. Generated reminders do not constitute legal advice or proof that a notice is validly served. | G-DL: calculation method. |
| APG-S12-L0078 | Contractual release milestones and conditions, with the supporting clause/record and interpretation status. | G-DL: no interpretation status on E75 or E12. |

### G-CLM: Contract schedule-of-rates/BoQ items and claim-line quantities are not carried

**What is missing.** PG-CR-AC-04 needs claim comparisons to use traceable quantities and valuation evidence. E13 holds amount by item only. M15 fix 4 adds the pricing-basis type (SoR, BoQ, lump sum) to E08 but not the items, so claimed quantity x rate cannot be traced to the contract.

**Proposed fix.** Extend M15 fix 4: E08 gains the SoR/BoQ items (item ref, description, unit, contract quantity, rate). E13 lines gain claimed quantity, rate and contract-item ref.

| Row | Requirement words | Row note |
| --- | --- | --- |
| PG-CR-AC-04 | PG-CR-AC-04: Claim comparisons use traceable quantities and valuation evidence. | G-CLM: E13 holds amount by item only; contract SoR/BoQ items (unit, quantity, rate) are not held. M15 fix 4 adds only the pricing-basis type. |

### G-HC: Head contract lacks approved scope/exclusions and valuation rules

**What is missing.** S11 s3 (no RTM row) and S11 s5 C0034 name approved scope/exclusions and valuation rules. E08 and M15 fix 4 carry neither, even though the M15 check says it read S11 s3 item by item.

**Proposed fix.** Add to the E08 field groups of M15 fix 4: approved scope and exclusions, valuation rules.

| Row | Requirement words | Row note |
| --- | --- | --- |
| APG-S11-C0034 | Do not assume all completed work is immediately claimable. Contract terms, valuation rules, approvals, evidence requirements and other conditions may affect the position. | G-HC: E08 (and M15 fix 4) has no valuation rules or approved scope/exclusions. |

### G-VAR: Variation lacks assumptions and unresolved questions

**What is missing.** S11 s4 lists "unresolved commercial assumptions" as a trigger. The s4 closing paragraph, which has no RTM row, says to preserve "unresolved questions" and "affected dates". E09 has none of these.

**Proposed fix.** Field group on E09 Variation: commercial assumptions and unresolved questions (open/resolved), affected dates.

| Row | Requirement words | Row note |
| --- | --- | --- |
| APG-S11-L0027 | Unresolved commercial assumptions. | G-VAR: E09 holds no assumptions or unresolved questions with status. |

### G-SEC: Security instrument record is incomplete

**What is missing.** S12 s12.9 lists reference, currency, project/scope and obligation secured, renewal terms, cancellation conditions, collateral, cash margin, facility utilisation, verification status, responsible owner, approval history, and a distinct lifecycle. E78 has type, issuer, beneficiary, face value, dates, release conditions and fees. The M15 check says it read s12.9 item by item.

**Proposed fix.** Field group on E78 Security instrument: instrument reference, currency, project and obligation secured, renewal terms, cancellation conditions, collateral, cash margin, linked facility (E74), lifecycle status, responsible owner.

| Row | Requirement words | Row note |
| --- | --- | --- |
| APG-S12-L0022 | Financing and carrying-cost estimates, facility fees, collateral, and cash margins where evidenced. | Scope item. G-SEC: E78 has no collateral or cash margin. |
| APG-S12-L0044 | Guarantees, bonds, security instruments, issuer/beneficiary details, fees, collateral, cash margins, expiry dates, and release conditions. | G-SEC: no collateral or cash margin. |
| APG-S12-C0084 | Security instruments are not equivalent to cash or retention and must have a distinct record and lifecycle. Capture, where applicable: | G-SEC: E78 has no lifecycle status. |
| APG-S12-L0085 | Instrument type, reference, issuer, beneficiary, face value, and currency. | G-SEC: no instrument reference or currency. |
| APG-S12-L0086 | Project/scope and the obligation secured. | G-SEC. |
| APG-S12-L0087 | Issue date, expiry date, renewal terms, and release/cancellation conditions. | G-SEC: renewal terms, cancellation conditions. |
| APG-S12-L0088 | Fees, collateral, cash margin, facility utilisation, and evidenced financing impact. | G-SEC: collateral, cash margin. |
| APG-S12-L0089 | Supporting documents, verification status, responsible owner, and approval history. | G-SEC: responsible owner. |
| APG-S12-C0090 | Expiry or an expected release date must trigger review where appropriate, not automatic cancellation or a claim that capital has returned. Consequential release, cancellation, renewal, or external instruction requires authorised human approval and an audit trail. The system must distinguish instrument face value from a ... | G-SEC: cash collateral/margin. |

### G-FIN: Funding facility lacks day-count convention and financing assumptions

**What is missing.** S12 s12.4 names "day-count conventions, and documented financing assumptions", and s12.7 builds the calculation on a day-count basis. E74 has limit, drawn, rate, fees and statement date.

**Proposed fix.** Field group on E74 Funding facility: day-count convention, rate type and effective dates, documented financing assumptions.

| Row | Requirement words | Row note |
| --- | --- | --- |
| APG-S12-L0045 | Funding rates, facility limits, utilisation, fees, day-count conventions, and documented financing assumptions. | G-FIN: E74 has no day-count convention or documented financing assumptions. |
| APG-S12-L0070 | Start/end dates, eligible duration, and day-count basis. | G-FIN: day-count basis not held. |
| APG-S12-L0135 | Material financing-cost calculations expose balance basis, rate basis, eligible period, method/day-count basis, fees where applicable, uncertainty, and overlap controls. | G-FIN (day-count) and G-REL (overlap). |

### G-FA: No entity for final-account items and post-completion obligations

**What is missing.** S12 s12.4, s12.8, s12.12 and S13 s13.2, s13.12 (and S11 s7, s11, which have no RTM rows) track final-account records and items, close-out obligations, certificates and warranty obligations until they are discharged. The register has DLP (via fix 4), defects, retention and security, but no record of a final-account item or close-out obligation and its status.

**Proposed fix.** New entity, Close-out obligation and final-account item: head contract, type (final-account item, close-out obligation, required certificate, warranty obligation), description, amounts (claimed, agreed, disputed), status, due date, responsible party, evidence.

| Row | Requirement words | Row note |
| --- | --- | --- |
| APG-S12-L0025 | Post-completion obligations that may delay collection, release, or return of capital. | Scope item. G-FA: no entity for final-account items or close-out obligations. |
| APG-S12-L0043 | Retention ledgers, release milestones, defect obligations, final-account records, and dispute status. | G-FA: final-account records have no entity. |
| APG-S12-L0080 | Defects, inspections, certificates, final-account requirements, close-out obligations, and disputes that may affect release. | G-FA: final-account requirements and close-out obligations have no entity. |
| APG-S12-C0108 | Monitoring must continue after practical completion where relevant obligations remain unresolved. Track retention, security, final account, claims/disputes, inspections, certificates, defects, and remaining delivery/close-out costs. Completion status alone does not establish that all capital is released or all obligati ... | G-FA. |
| APG-S12-L0140 | Post-completion monitoring continues while relevant obligations remain unresolved. | G-FA. |
| APG-S13-L0026 | Warranty, latent-defect and post-completion obligations where relevant. | Scope item. G-FA; DLP itself via M15 fix 4. |
| APG-S13-C0111 | Closing a defect must not automatically mean that the underlying root cause is resolved, the financial cost is final, a potential recovery is collected, a retention release condition is satisfied, or all contractual or warranty obligations are discharged. Maintain these outcomes separately. | G-QC (recovery collected) and G-FA (obligations discharged). |
| APG-S13-L0167 | Post-completion obligations remain visible while unresolved. | G-FA. |

### G-PT: Supplier payment terms are not carried

**What is missing.** S12 s12.4 names supplier/subcontractor commitments and their payment terms as cash-forecast inputs. E16 terms cover subcontracts. E20 Supplier and E21 Purchase order have no payment terms, so the timing of uninvoiced commitments cannot be forecast.

**Proposed fix.** Field group on E21 Purchase order (with a default on E20): payment terms and deposit terms.

| Row | Requirement words | Row note |
| --- | --- | --- |
| APG-S12-L0042 | Supplier/subcontractor commitments, payment terms, payroll, plant/equipment costs, taxes, statutory liabilities, and close-out costs. | G-PT: supplier payment terms have no home (E20 and E21 lack them; E16 terms cover subcontracts only). |

### G-PROV: Provenance fields lack timestamps

**What is missing.** S12 s12.4 and s12.15 name source timestamps, extraction timestamps, effective dates and as-of time. E01 has source, source record id, revision, ingestion state, verification and supersession, with no times. E96 has an effective date for financial records only.

**Proposed fix.** Field group on E01: source timestamp, received/extracted timestamp, effective date.

| Row | Requirement words | Row note |
| --- | --- | --- |
| APG-S12-L0046 | Source identifiers, source timestamps, extraction timestamps, effective dates, confidence/verification state, and reconciliation status. | G-PROV: E01 has source, id, revision, ingestion state, verification but no source/extraction timestamps or effective date (E96 has effective date for financial records only). |
| APG-S12-L0131 | Material cash-flow records expose provenance, source authority, as-of time, freshness, reconciliation/verification status, and qualification. | G-PROV: timestamps; as-of for forecasts via proposed E101. |

### G-AUD: No general state-transition record

**What is missing.** S12 s12.3 (C0036) and s12.15 need every transition between claim, certification, invoice, approval, collection, retention release and security return to carry its event, evidence, actor or rule, timestamp and audit record. Only retention has this (E77). E01 revisions and E87 decisions do not record from-state/to-state transitions made by a deterministic rule.

**Proposed fix.** Field group on E01 (every record): state history of from-state, to-state, triggering event, evidence ref, actor or rule, timestamp.

| Row | Requirement words | Row note |
| --- | --- | --- |
| APG-S12-C0036 | No state may be silently promoted into another state. Each transition must have a defined event, evidence requirement, authorised actor or deterministic rule, timestamp, provenance, and audit record. A forecast is not a bank balance; a claim is not a certified receivable; certification is not collection; and a retentio ... | G-AUD: only retention has transition events (E77); no general state-history record for claims, certificates, invoices, collections, security. |
| APG-S12-L0133 | A state transition between claim, certification, invoice, approval, collection, retention release, or security return requires defined evidence and a recorded event. | G-AUD. |

### G-DCL: Defect and observation classification and links are missing

**What is missing.** S13 s13.2, s13.4 and s13.7 classify defects (type: material, product, installation, workmanship, design; dimensions: safety, regulatory, structural/functional, building performance, workmanship, inspection/commissioning failure, handover/warranty) and detect recurrence by material, product, supplier, method, design detail and inspection stage. E66 has location, work package, trade, subcontractor and one severity, with no material or supplier link. E65 has no observation type, stage or result.

**Proposed fix.** Field groups on E66 Defect: defect type, classification flags per s13.4 dimension (safety and compliance kept apart from financial severity), links to material (E26), supplier (E20) and delivery (E29), installation method, design detail/interface ref. On E65 Quality observation: observation type (inspection, test, commissioning, handover, reported issue), stage, result.

| Row | Requirement words | Row note |
| --- | --- | --- |
| APG-S13-L0018 | Defect identification, classification and lifecycle tracking. | Scope item. G-DCL: E66 has severity and status but no classification beyond severity. |
| APG-S13-L0020 | Inspection, testing, commissioning and handover failures. | Scope item. G-DCL: E65 has no observation type, stage or result. |
| APG-S13-L0021 | Material, product, installation and workmanship defects. | Scope item. G-DCL: no defect type. |
| APG-S13-L0022 | Design coordination, specification and constructability-related quality issues. | Scope item. G-DCL. |
| APG-S13-L0023 | Supplier- and subcontractor-related quality patterns. | Scope item. G-DCL: E66 links subcontractor but not supplier or material. |
| APG-S13-L0045 | Safety and potential harm. | G-DCL. |
| APG-S13-L0046 | Regulatory or mandatory-standard implications. | G-DCL. |
| APG-S13-L0047 | Structural, functional and durability implications. | G-DCL. |
| APG-S13-L0048 | Water ingress, fire performance, weatherproofing or other material building-performance risks where applicable. | G-DCL. |
| APG-S13-L0049 | Workmanship and finish. | G-DCL. |
| APG-S13-L0050 | Inspection, testing or commissioning failures. | G-DCL. |
| APG-S13-L0051 | Handover, warranty and future maintenance implications. | G-DCL. |
| APG-S13-C0053 | Financial prioritisation must never override safety or mandatory quality requirements. A low-cost defect may still require urgent attention if the risk is serious. | G-DCL. |
| APG-S13-L0090 | Materials, products and suppliers. | G-DCL: no material or supplier link on E66. |
| APG-S13-L0091 | Installation methods and construction sequences. | G-DCL: no method field. |
| APG-S13-L0092 | Design details, interfaces and specifications. | G-DCL. |
| APG-S13-L0094 | Inspection stages, commissioning and handover. | G-DCL: no stage on E65/E66. |
| APG-S13-L0137 | Section 08 — Procurement: material defects and replacements link to comparable product, landed-cost and supplier information. | G-DCL: no material/supplier link on E66. |
| APG-S13-L0159 | Quality classifications can prioritise serious safety or mandatory-compliance risks independently of financial magnitude. | G-DCL. |

### G-QCFG: No setting for the defect classification scheme and the closure evidence it requires

**What is missing.** S13 s13.4 (lead-in, no RTM row) asks for a classification scheme that can be configured for the project. Checkpoint A requires configured verification evidence before a defect is closed. N01 holds no quality settings.

**Proposed fix.** Field group on N01: quality settings, namely the defect classification scheme and the closure evidence required per defect class or transition.

| Row | Requirement words | Row note |
| --- | --- | --- |
| APG-S13-C0149 | MANDATORY. A defect cannot be marked verified and closed solely because someone reports the work complete. Configured verification evidence must be present, with a controlled reopen path. | G-QCFG: no setting holds the closure evidence required per defect class. |
| APG-S13-L0161 | Rectification closure requires configured evidence and verification controls. | G-QCFG. |

### G-QC: Quality cost cannot separate cost components or recovery states

**What is missing.** S13 s13.5 lists cost components (plant/access/specialist, demolition/removal, inspection/testing/engineering, subcontractor charges, credits/insurance offsets) and seven value states: observed, estimated, forecast, potential recovery, approved recovery, actual recovered, net verified. Checkpoint B keeps these apart. E71 has defect, cost type (observed, estimated, forecast, recovery) and amount. A single "recovery" type cannot split potential, approved and actual recovery, and no component or recovery counterparty is held. The M15 check says it read s13.5 item by item.

**Proposed fix.** Field groups on E71 Quality cost: cost component (the s13.5 list); value state extended to potential recovery, approved/recognised recovery and actual recovered; recovery counterparty; verification state.

| Row | Requirement words | Row note |
| --- | --- | --- |
| APG-S13-L0019 | Rework events and associated direct and indirect costs. | Scope item. G-QC: E71 has no cost component, so direct vs indirect cannot be told apart. |
| APG-S13-L0059 | Plant, equipment, access and specialist service costs. | G-QC: no cost component on E71. |
| APG-S13-L0060 | Demolition, removal, disposal and reinstatement. | G-QC. |
| APG-S13-L0061 | Inspection, testing, engineering and specialist assessments. | G-QC. |
| APG-S13-L0062 | Subcontractor rectification charges or recoveries. | G-QC: no recovery counterparty or recovery state. |
| APG-S13-L0066 | Credits, insurance recoveries or other offsets where verified. | G-QC. |
| APG-S13-L0071 | Potential recovery from another party. | G-QC: E71 has one 'recovery' type; potential, approved and actual cannot be told apart. |
| APG-S13-L0072 | Approved or recognised recovery. | G-QC. |
| APG-S13-L0073 | Actual recovered value. | G-QC. |
| APG-S13-L0074 | Net verified financial impact. | G-QC. |
| APG-S13-C0075 | A potential recovery must not automatically reduce the recorded cost or improve forecast margin. A cost estimate must not be represented as actual expenditure. | G-QC. |
| APG-S13-C0111 | Closing a defect must not automatically mean that the underlying root cause is resolved, the financial cost is final, a potential recovery is collected, a retention release condition is satisfied, or all contractual or warranty obligations are discharged. Maintain these outcomes separately. | G-QC (recovery collected) and G-FA (obligations discharged). |
| APG-S13-L0134 | Section 05 — Profitability: verified rework costs and recoveries flow into the appropriate financial classifications. | G-QC: recovery states. |
| APG-S13-L0140 | Section 11 — Commercial intelligence: potential recovery or contractual claims remain distinct from approved and collected values. | G-QC. |
| APG-S13-C0151 | MANDATORY. Actual costs, estimated costs, potential recoveries, approved recoveries and collected amounts remain separate. Potential recovery must not silently offset costs or improve margin. | G-QC. |
| APG-S13-L0158 | Actual costs, estimated rectification costs, forecast costs, potential recoveries and realised recoveries remain separate. | G-QC. |

### G-RCA: Root-cause hypothesis lacks review outcome and unresolved questions

**What is missing.** S13 s13.7 preserves competing explanations, evidence, confidence, unresolved questions and review outcomes. E68 has defect, hypothesis, evidence, confidence and raised by.

**Proposed fix.** Field group on E68: review status/outcome (open, rejected, confirmed with link to E69), unresolved questions.

| Row | Requirement words | Row note |
| --- | --- | --- |
| APG-S13-C0097 | Root-cause analysis must preserve competing explanations, evidence, confidence, unresolved questions and review outcomes. Where multiple causes contribute to an issue, support that complexity rather than forcing a single cause without justification. | G-RCA: E68 has no review outcome or unresolved questions. |

### G-INT: Work interruption record lacks duration, resources affected and cause status

**What is missing.** PG-LR-AC-06 (and S09 s3/s6, which have no RTM rows) tell an observed interruption apart from a suspected cause and a supported cause, with its duration and the resources affected. E63 has date, package and condition only.

**Proposed fix.** Field group on E63 Work conditions record: duration or hours lost, crew/resources affected, recorded reason, cause status (observed, suspected, supported).

| Row | Requirement words | Row note |
| --- | --- | --- |
| PG-LR-AC-06 | PG-LR-AC-06: Waiting-time findings distinguish observations from suspected causes. | G-INT: E63 has date, package, condition only; no duration/time lost, resources affected, recorded reason or cause status (observed, suspected, supported). |

### G-ALLOC: Work allocation lacks activity, location and task

**What is missing.** PG-LR-AC-01 maps labour records to activities. S09 s3 (no RTM row) defines work allocation as project, work package, activity, location and assigned task. E58 has worker or crew, package and period only. The M15 check says it read S09 s3.

**Proposed fix.** Field group on E58 Work allocation: programme activity (E48), location, assigned task.

| Row | Requirement words | Row note |
| --- | --- | --- |
| PG-LR-AC-01 | PG-LR-AC-01: Labour records map to governed projects, activities and work packages. | G-ALLOC: E58 work allocation has worker/crew, package, period only; S09 s3 also needs activity, location and assigned task. |

## 3. Rows covered only by an M15 fix, grouped by fix

### M15 fix 1: E100 material movement and stock (5 rows)

- PG-MP-AC-01: PG-MP-AC-01: Material demand reconciles to approved scope, inventory, commitments and deliveries.
- PG-MP-AC-14: PG-MP-AC-14: Inventory findings distinguish verified stock from estimates.
- APG-S08-C0032: Reconcile demand against approved quantities and scope, revised drawings, inventory, open orders, delivered/accepted quantities, cancelled orders, returns, wastage and approved substitutions. Flag ove ...
- APG-S08-C0075: Reconcile materials required, ordered, delivered, accepted, installed, returned and held in inventory. Potential findings include excess quantity, duplicate orders, unused stock, orders against supers ...
- APG-S08-C0076: Distinguish verified inventory from estimates and unverified site reports. Proposed transfer/reuse must account for specification, condition, ownership, transport, handling, timing and approval.

### M15 fix 2: E101 cash-flow forecast (12 rows)

- APG-S12-L0020: Time-phased project and business cash-flow forecasts, including explicit assumptions and uncertainty.
- APG-S12-L0021: Working-capital exposure created by the timing gap between outflows and inflows.
- APG-S12-L0031: Forecast receipts and payments: modelled estimates with assumptions, as-of time, confidence/qualification, and source freshness.
- APG-S12-L0035: Working-capital exposure and financing cost: distinct from accounting margin and from gross retention/security face value.
- APG-S12-C0049: The forecast must support dated, time-phased inflows and outflows at the relevant project and business level.
- APG-S12-C0060: Every material forecast must identify its as-of date, time horizon, source freshness, key assumptions, known gaps, and qualification. Where critical inputs are missing or stale, provide a qualified fo ...
- APG-S12-C0063: Separate the existence and duration of a liquidity gap from a loss of project profit. A timing gap can create funding pressure without directly reducing accounting margin. Recommendations may include ...
- APG-S12-L0081: Expected release dates and assumptions, clearly distinguished from confirmed eligibility and actual cash receipt.
- APG-S12-L0097: Material concentration or timing exposure, with assumptions and source freshness stated.
- APG-S12-L0116: Section 08 — Link procurement timing and landed-cost decisions to cash commitments, deposits, delivery risk, and working capital.
- APG-S12-L0117: Section 09 — Link labour/resource forecasts to payment timing without bypassing safety, quality, competence, or fairness controls.
- APG-S12-L0134: Working-capital exposure is calculated separately from accounting margin and forecast final margin.

### M15 fix 3: E27 substitutions and approved equivalents (4 rows)

- PG-MP-AC-17: PG-MP-AC-17: Human approval is required before purchase commitments and material substitutions.
- APG-S08-L0015: Human approval remains mandatory for purchase commitments and material substitutions.
- APG-S08-C0032: Reconcile demand against approved quantities and scope, revised drawings, inventory, open orders, delivered/accepted quantities, cancelled orders, returns, wastage and approved substitutions. Flag ove ...
- APG-S08-C0039: A cheaper substitute must not be recommended solely on price when performance, design approval, warranty, compliance or other material requirements remain unresolved.

### M15 fix 4: E08 pricing basis, milestones, defects liability period (1 rows)

- APG-S13-C0146: Post-completion monitoring must connect the quality record to the relevant commercial and financial state while retaining each domain's own evidence and approval requirements.

### M15 fix 6: E73 account and reconciled balance / E96 journal reference (3 rows)

- APG-S12-L0018: Actual cash positions and dated cash movements.
- APG-S12-L0029: Actual cash: supported by authoritative bank/cash evidence and reconciled according to the approved source rules.
- APG-S12-L0039: Bank transactions, reconciled cash balances, cashbook entries, and funding-facility statements.

No row in Part C depends on M15 fix 5 (owned plant on E64) or on the E38 budget-part change.

## 4. Where I think the M15 heading-level result is wrong or incomplete

1. **Lists it says it read item by item but that are not fully covered.** The check names S08 s4, S09 s3, S11 s3, S12 s12.4, s12.8 to s12.10 and S13 s13.3, s13.5 as read item by item. Each still has items with no field group:
   - S08 s4: delivery location, waste allowance, drawing and revision on demand, expected deliveries (G-DEM).
   - S09 s3: work allocation's activity, location and task (G-ALLOC); interruption duration, resources affected and reasons (G-INT). E62 also has no explicit "planned hours" or "benchmark source". I let that pass under E62 rate, comparability basis and E01 source, but it is thin.
   - S11 s3: approved scope/exclusions and valuation rules (G-HC). Fix 4 adds only the pricing-basis type, not the SoR/BoQ items a claim must trace to (G-CLM).
   - S12 s12.4: day-count conventions and financing assumptions (G-FIN), supplier payment terms (G-PT), source and extraction timestamps (G-PROV), final-account records (G-FA).
   - S12 s12.8: interpretation status of release conditions (G-DL); final-account requirements and close-out obligations (G-FA).
   - S12 s12.9: collateral, cash margin, currency, reference, obligation secured, renewal terms, owner, lifecycle (G-SEC).
   - S13 s13.3 / s13.5: E71 cannot hold cost components or split recovery into potential, approved and actual (G-QC). E68 has no review outcome or unresolved questions (G-RCA).
2. **Record lists the check did not treat as data lists.** These carry most of the gaps found here: S05 s10 benefit states (G-BEN); S06 s6 finding record and s9 relationships (G-REL, G-FND); S08 s4.1 comparability gate (G-CMP); S08 s7 and s14 observation fields (G-MKT); S10 s4, s5, s9, s10 recommendation factors, categories, states and history (G-REC); the scenario lists in S10 s7, S09 s12, S11 s12 and S12 s12.11 (G-SCN); S11 s7 deadline fields (G-DL); S12 s12.3 transition rule (G-AUD); S13 s13.4 classification and s13.7 recurrence dimensions (G-DCL, G-QCFG); S13 s13.6 baseline contents (G-BEN part b). The register has the right entities for all of these (E84, E86, E88, E46, E12, E66, E71, E44). The required field groups are too thin to carry what the text names. That is why the heading-level pass, which matched needs to entities, did not see these gaps.
3. **Fix 1 (E100)** has no stock ownership. S08 s13 (C0076) says a proposed transfer or reuse must account for "specification, condition, ownership, transport, handling, timing and approval". Add an owner (project or legal entity) to E100.
4. **Fix 2 (E101)** is right. Its field list should name everything S12 C0060 requires: as-of date, time horizon, source freshness, key assumptions, known gaps and qualification. The M15 table names as-of date, horizon and qualification only. Also, M15 cites S12 s12.3 "scheduled ... receipts and payments" as a reason for E101. Scheduled amounts are already held as due dates on E14, E15, E79 and E80, so E101 is needed for the forecast values, not for the scheduled ones.
5. **Fix 4 (E08)** should be widened as G-HC and G-CLM describe.
6. **Release placement.** I did not check the release claim ("none affects the first data release"). G-REL, G-FND, G-REC and G-BEN concern the finding, recommendation and outcome records that any insight writes. The "later" placement should be re-checked for those four.
7. **Weak coverage I accepted, worth a second look.** Recognised revenue (S11 s8 / PG-CR-AC-07): E96's value statuses have no "recognised", so I accepted an E96 actual revenue record under the E90 revenue basis. Client-side credit notes (S12 L0019, L0040): E24 is the supplier side only. Overtime purpose (PG-LR-AC-08): accepted through the E87 decision basis. Rectification resource requirements (S13 L0025): E70 has owner and timing but no planned resources.

## 5. Paragraphs of Sections 08 to 13 that have no RTM row

Part C has no row for 134 paragraphs inside the sections' ranges, counted by gaps in paragraph_index. Acceptance criteria are left out of that count because they appear as PG- rows. The missing numbers are:

- S08 (23): 6, 18-22, 24-28, 41, 44, 46, 47, 49, 56-58, 61, 64, 67, 78
- S09 (33): 6, 8, 10, 14-25, 27, 28, 31, 33, 34, 36, 37, 39, 42, 43, 45, 48, 51, 54, 57, 58, 72, 73
- S10 (19): 6, 9-13, 20-26, 40, 43, 46, 67, 70, 73
- S11 (24): 6, 7, 17, 20, 29, 33, 36, 39, 45-53, 57, 58, 60, 61, 63, 66, 67
- S12 (15): 6-9, 11, 16, 38, 50, 56, 62, 65, 66, 76, 92, 156
- S13 (20): 6-9, 11, 12, 14, 16, 31, 42, 44, 56, 85, 88, 99, 113, 142, 144, 145, 178

(The numbers follow the row-ID convention, which is paragraph_index + 1.)

Many of these are the data lists themselves: S08 s3 domains, s5 quote capture, s6 international record, s9 performance measures, s14 finding fields; S09 s3 data model, s6, s15; S10 s2, s4 factors, s9 states, s10 history; S11 s3 baseline, s6 evidence, s8 states, s9 to s12; S13 s13.4 lead-in and s13.12. A matrix check alone cannot catch a need stated only there. I gave these paragraphs no verdicts because they have no rows. I did read them for context, and the gaps above already draw on them (G-ALLOC, G-INT, G-HC, G-VAR, G-REC, G-SCN, G-FA, G-QCFG, G-MKT). The others I checked are covered: S08 s5 by E30/E32/E33/E83, S08 s6 by E33/E37, S11 s6 by E83. **The RTM should be checked for completeness against the section text.** This is a gap in the matrix, not in the register.

## 6. Rows I could not judge

None. All 673 rows have a verdict. The closest calls are listed here so a reviewer can overrule them:
- PG-MP-AC-02 and APG-S08-L0034 to L0038 (G-CMP). These would become COVERED if the register stated that the comparability class and adjustments are E45 outputs stored with the comparison run.
- APG-S10-L0031 to L0039 (G-REC, recommendation category). One missing field gives nine GAP rows.
- APG-S13-L0020 to L0023 and L0045 to L0051 (G-DCL). Judged on what the text names. A free-text E66 description was not accepted as a classification.
- APG-S12-L0046 and L0131 (G-PROV). "Ingestion state" was accepted as reconciliation status, but there are no timestamps.
