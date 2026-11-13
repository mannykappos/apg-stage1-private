# M15 row-level check, Part B (Sections 04 to 07)

INDEPENDENT READ-ONLY (agent). Design work only: nothing is built. Input: `in/RTM_PART_B.csv` (618 rows). Output: `out/M15_PART_B.csv` (618 rows, same order).

## Method

Every row was read, in paragraph order within its section, together with its heading and the list it sits in (section text checked where context sat in rows outside Part B, for example S05 s7 and s10 and S07 s5.1, s6, s11, s12). Each data need was checked against the register's **required field groups** (`ENTITY_REGISTER.csv`), not against what APG holds today. Rules applied:

- Headings, purpose, principles, calculation/presentation rules, tests, and all Claude implementation, Gemini audit and lock rows are `NO-DATA-NEED`. Implementation instructions that name data (for example S06 L0152, S04 L0171) are marked `NO-DATA-NEED` as delivery instructions; the data they name is judged at the substantive rows.
- Source-category, taxonomy, delay-cause and trigger lists were judged `Y`: they name kinds of records APG must hold or read.
- E01, E45, E84 and E96 were credited only for the field groups they actually list.

## Counts by verdict

| Verdict | Rows |
| --- | --- |
| COVERED | 186 |
| COVERED-BY-PROPOSED | 10 |
| GAP | 122 |
| NO-DATA-NEED | 300 |
| **Total** | **618** |

By section: see the CSV. The 122 GAP rows reduce to **26 proposed fixes (B1 to B26)**: 5 new entities or entity generalisations and 21 field-group additions. Most GAP rows fall in four places the heading-level check treated as covered: the S04 ingestion audit trail and its registers (E01, E02, E03, E35), the S06 s6 finding data contract (E84), the S05 s10 benefit lifecycle, and S07 s3 programme data (E47, E48).

## Proposed fixes (smallest fix for each gap)

| Fix | Kind | Proposed change | GAP rows |
| --- | --- | --- | --- |
| B1 | field group on E01 | **Per-record lineage**: received time, effective time, payload hash or evidence reference (link to E83), schema version and mapping version applied, authority rule and register version applied. | S04 L0053, L0084, L0111, L0136, L0138, PG-DI-AC-15; S05 C0053 |
| B2 | new entity | **Ingestion receipt and processing record** (one per received message, file or batch, with per-record lines): source, batch, receipt time, correlation id, validation results and warnings, duplicate decision, outcome classification, processing state, errors, retries, replay, canonical changes and events produced, downstream results, final disposition, row-level errors. | S04 L0032, L0125, L0129, L0137, L0140, L0147, PG-DI-AC-15 |
| B3 | new entity | **Reconciliation / quarantine case**: records involved, case type (conflict, duplicate candidate, missing link, mismatch, known timing difference, incomplete), quarantine reason, candidate matches, status, assigned reviewer, outcome (accept, correct, reject, merge, retain), link to the E87 decision. | S04 L0066, C0075, L0095, L0099, C0100, L0114, L0137, L0139, PG-DI-AC-15 |
| B4 | new entity | **Canonical mapping rule (versioned)**: source, source field or spreadsheet column, canonical field, transformation (unit, currency, date/time zone, tax, sign), version, effective dates, approved by. | S04 L0040, L0084, L0147 |
| B5 | field group on E02 | **Connector contract**: connector identity and environment; direction of flow; authentication method, permissions, credential rotation/expiry dates (not the secrets); transport mode and batch/pagination behaviour; documented freshness; mapping version and effective dates; idempotency, duplicate, retry, backoff, dead-letter and replay policy; owner and escalation contact. | S04 L0036 to L0042 |
| B6 | field group on E03 | **Authority entry in full**: domain/entity, permitted secondary sources and precedence rule, effective period, owner, evidence basis, version and approval history; field class (source-owned, derived, human-approved, provisional); handling of revisions, cancellations, late records and corrections; conflict outcomes and resolver role; trust level per field/domain. | S04 L0047 to L0050, L0053, L0059, PG-DI-AC-02 |
| B7 | new entity | **Entity cross-reference**: source system, source id or alias, canonical entity and id, match basis, approved by and date (covers supplier aliases and approved cross-reference tables). | S04 C0091, L0095 |
| B8 | generalise E35 | **Document extraction reading** for any document (not only quotes): document (E83), field, value, page/region, extractor and model/tool version, extraction time, confidence, unresolved ambiguity, verified by and on, confirmed or corrected value, evidence considered, disposition. | S04 C0102, L0103 to L0105, L0107, L0108, PG-DI-AC-07 |
| B9 | field groups on E96 | Source amount and currency kept with converted amount and currency, FX rate reference and conversion method; transaction date, posting date and accounting period; add "risk-adjusted" (and "estimated", if not read as "forecast") to the value status list. | S04 L0086; S05 L0013, L0023, C0066 |
| B10 | field group on E83 | Upload metadata: uploader identity, upload time, source description, project scope, manual transformations. | S04 L0145 |
| B11 | widen E77 (or field group on E78) | Record release, cancellation, renewal and return of security instruments as events with actor and evidence, as E77 does for retention. | S04 L0017 |
| B12 | field group on E75 | Hold reason and linked defects on client-held retention (E76 already links trade retention to defects). | S04 L0096; S05 C0100 (also referenced by PG-SD-AC-14) |
| B13 | field groups on E41 and E44 | E41: assumptions and confidence of the cost-to-complete estimate. E44: reason each approved version replaced the prior one. | S05 L0045, L0070 |
| B14 | field group on E42 | Accrual basis, status, and link to the actual cost that reconciles or reverses it. | S05 L0046 |
| B15 | field groups on E84 (and E85) | **Finding / exposure contract (S06 s6, S05 s7)**: scope (project or portfolio), version, taxonomy family and subtype, detection method, lifecycle status (detected to superseded) with timestamps, explanation (observed, expected, reason), financial interpretation class, time window and currency, severity and urgency held separately, ownership (responsible role, reviewer, next review date), relationships (linked findings, suspected or confirmed cause links, overlap/double-counting group, overlap status), deduplication identity, assertion basis (evidenced, inference, hypothesis, unverified), late/missed marker. | S05 L0047, C0092; S06 L0017, L0020, C0036, C0054, L0057, C0065, L0067 to L0069, L0072, L0073, L0076 to L0078, C0087, L0090, L0092 to L0094, L0096, C0098, C0112, L0120, L0121, PG-AI-AC-08 to AC-12; S07 C0054, PG-SD-AC-06 |
| B16 | field groups on N01 | Allowed range per threshold (the "approved governance boundaries"), rule exceptions, alert suppression window and re-notification rules. | S06 C0040, C0098, PG-AI-AC-09 |
| B17 | field groups on E86 and E88 | **Action and benefit lifecycle (S05 s10, s10.1)**: action state (proposed, approved, in progress, implemented) and implementation evidence; benefit state (identified to realised, reversed/not realised); estimated gross benefit, implementation cost, net benefit; approved baseline reference and comparability basis (scope/spec, quantity, timing, landed-cost treatment); verification (by, when, evidence). | S05 C0104, C0107, PG-PC-AC-02, PG-PC-AC-13; S06 L0019, C0112, L0121, PG-AI-AC-16 |
| B18 | field groups on E45 | Run type (calculation or scheduled/event monitoring sweep); scope (project/entity, reporting period); as-of time and cut-off; run status and failure detail; exclusions; policy versions used; calculation timestamp; prior result link; downstream use. | S05 L0023, L0122, L0124, L0125; S06 C0021, C0109, PG-AI-AC-18 |
| B19 | field group on E89 | Resolution path and expected date for each gap. | S05 L0080 |
| B20 | field groups on E46 | Owner / responsible reviewer, rule version, input provenance and freshness, uncertainty and limitations, evidence gaps, constraints requiring review (quality, safety, operational). | S05 L0111, L0112; S07 L0077, L0079, PG-SD-AC-11 |
| B21 | field group on E05 | Data-sharing and aggregation permissions: eligibility, permitted fields, de-identification, limits. | S06 C0118, PG-AI-AC-17 |
| B22 | field groups on E47 | Version type (original baseline, approved revision, working forecast, scenario, unapproved proposal), change classification (approved revision, forecast update, correction, proposal), baseline date, scope. | S07 L0014, C0019, C0020, PG-SD-AC-01, PG-SD-AC-02 |
| B23 | field groups on E48 | Activity description, forecast start and finish, remaining duration, resource or subcontractor assigned. | S04 L0012; S07 L0015 to L0017, L0023, L0024 |
| B24 | field group on E53 | Effective period of each holding-cost rate. | S07 L0056 |
| B25 | field groups on E21 and E28 | E21: promised / forecast delivery date per line (the "delivery commitment"). E28: the programme activity or work package the demand serves. | S04 L0011; S07 C0068, PG-SD-AC-10 |
| B26 | field group on E12 | Assumptions behind a generated deadline or interpretation. | S07 C0086 |

Release placement of these fixes is for the owner; this check does not judge it.

## Counts by section

| Section | COVERED | COVERED-BY-PROPOSED | GAP | NO-DATA-NEED | Rows |
| --- | --- | --- | --- | --- | --- |
| S04 | 41 | 4 | 46 | 88 | 179 |
| S05 | 49 | 2 | 20 | 85 | 156 |
| S06 | 51 | 2 | 37 | 68 | 158 |
| S07 | 45 | 2 | 19 | 59 | 125 |

## Every GAP row (122)

| Row | Requirement (its words) | What is missing | Proposed fix |
| --- | --- | --- | --- |
| PG-DI-AC-02 | PG-DI-AC-02: Authority rules support different sources governing different fields and are versioned and auditable. | E03 has no version or approval history. | B6 |
| PG-DI-AC-07 | PG-DI-AC-07: Material AI/OCR-extracted values cannot become authoritative before authorised human verification. | Quote-only today. | B8 |
| PG-DI-AC-15 | PG-DI-AC-15: Audit records trace the source through validation, reconciliation, authority decision and canonical outcome. | audit trace: validation, reconciliation, authority decision, canonical outcome | B1, B2, B3 |
| APG-S04-L0011 | Procurement and commitments: purchase orders, subcontract orders, amendments, supplier quotations and delivery commitments. | All covered except delivery commitments: E21 has no promised/forecast delivery date and E29 holds only actual deliveries. | B25 |
| APG-S04-L0012 | Project management and scheduling: programme dates, activities, progress, dependencies, delay events and completion forecasts. | Activities hold planned and actual dates only; forecast dates and forecast completion are not in E48 or E47. | B23 |
| APG-S04-L0017 | Retentions and security: balances, release conditions, due dates, bank guarantees, bonds, expiry and release/cancellation evidence. | Retention events with evidence exist (E77) but nothing records release or cancellation of a security instrument with its evidence; E78 has dates and release conditions only. | B11 |
| APG-S04-L0032 | Record downstream processing status, errors, retries, replay and final disposition. | No entity holds per-receipt processing history; E01 holds only the current ingestion state. | B2 |
| APG-S04-L0036 | Source system/provider, tenant and organisation scope, connector identity and environment. | E02 has source; connector identity and environment are not in its field groups. | B5 |
| APG-S04-L0037 | Data domains and fields supplied, expected direction of flow and source identifiers. | Fields supplied covered; direction of flow not in E02. | B5 |
| APG-S04-L0038 | Authentication method, permissions, secret-handling requirements and rotation/expiry controls. | No field group for connector authentication metadata or credential rotation/expiry dates (the secrets themselves need not be in the register). | B5 |
| APG-S04-L0039 | Transport mode, expected cadence, pagination/batch behaviour, rate limits and documented freshness. | Cadence and limits covered; transport mode, batch behaviour and documented freshness missing. | B5 |
| APG-S04-L0040 | Schema/version information, mapping version and effective dates. | Schema version covered; mapping version and effective dates missing. | B4, B5 |
| APG-S04-L0041 | Idempotency keys, duplicate policy, retry policy, backoff, dead-letter/error handling and replay capability. | No field group for the connector duplicate/retry/replay policy. | B5 |
| APG-S04-L0042 | Known limitations, reliability characteristics, source authority by field, owner and escalation contact. | Limits, health and E03 covered; owner and escalation contact missing from E02. | B5 |
| APG-S04-L0047 | Record the field/fact, domain/entity, authoritative source, permitted secondary sources, precedence rule, effective period, owner, evidence basis and approval history. | E03 lacks domain/entity, precedence rule, effective period, owner, evidence basis and approval history. | B6 |
| APG-S04-L0048 | Define how revisions, cancellations, late-arriving records and corrections are handled. | Not in E03. | B6 |
| APG-S04-L0049 | Define whether a field is source-owned, derived deterministically, human-approved, or provisional. | Not in E03. | B6 |
| APG-S04-L0050 | Define conflict outcomes and the role authorised to resolve each material conflict. | Not in E03. | B6 |
| APG-S04-L0053 | Changes to the register must be versioned, approved and auditable. Historical records must retain the authority/mapping version used at the time. | E03 has no version or approval history; E01 does not record which authority or mapping version was applied. | B1, B6 |
| APG-S04-L0059 | Record the source identity and trust level; trust must be field/domain-specific rather than a blanket assumption that all content from a system is correct. | Source identity covered; no trust level per field or domain. | B6 |
| APG-S04-L0066 | Send unresolvable duplicate candidates to reconciliation rather than guessing. | No reconciliation/quarantine case entity to hold the candidate pair and its outcome. | B3 |
| APG-S04-C0075 | Ambiguous or conflicting financial records must be excluded from authoritative financial calculations. They must remain visible to authorised reviewers in a controlled investigation/reconciliation workflow. Where useful, the system may expose sandboxed provisional analysis, provided that it is clearly labelled, traceable to unverified inputs and technically prevented from silently replacing authoritative figures. | Provisional analysis covered (E45/E46 with E01 state), but no entity holds the investigation/reconciliation case. | B3 |
| APG-S04-L0084 | Record mapping rule/version and transformations applied; retain enough information to reproduce the normalised result. | No mapping rule register and E01 does not record the mapping version or transformations applied. | B1, B4 |
| APG-S04-L0086 | Keep source currency and amount distinct from converted currency and amount; record exchange-rate source, timestamp/effective date and conversion method. | E96 holds one amount and currency; source and converted amounts and the rate used are not both held. | B9 |
| APG-S04-C0091 | Resolve incoming records against canonical projects, organisations, suppliers, subcontractors, contracts, purchase orders, invoices, variations, materials, schedule activities, defects, retention/security instruments and other relevant entities. Matching may use stable IDs, approved cross-reference tables and documented composite rules. Confidence alone must not authorise a material financial merge. | E01 holds one source id per record; no entity holds approved cross-references between source ids/aliases and canonical entities. | B7 |
| APG-S04-L0095 | Supplier aliases, legal-entity differences, project/cost-code mismatches and duplicate candidates. | Cost codes via E04; no home for supplier aliases or duplicate-candidate cases. | B3, B7 |
| APG-S04-L0096 | Retention amount/rate conflicts, security expiry/release discrepancies and DLP/defect links. | E76 links trade retention to defects but client retention E75 has no defect link; DLP period needs M15 fix 4. | B12 |
| APG-S04-L0099 | Partial, missing or inconsistent records where reconciliation cannot be completed automatically. | No reconciliation case entity. | B3 |
| APG-S04-C0100 | Reconciliation outcomes must be explicit and auditable. The system must distinguish a genuine mismatch from a known timing difference and must not force a match simply to clear an exception queue. | No reconciliation case/outcome entity. | B3 |
| APG-S04-C0102 | AI/OCR-extracted values from invoices, contracts, supplier quotations, delivery dockets and other documents must not become authoritative where they materially affect financial calculations or contractual decisions until an authorised human verifies them. This is a non-negotiable control. | E35 covers quote readings only. Extracted values from invoices, contracts, dockets have no entity. | B8 |
| APG-S04-L0103 | Retain the original document or evidence reference, extraction output, model/tool version where available, extraction timestamp and confidence/uncertainty indicators. | E35 lacks model/tool version, extraction time and confidence, and is quote-only. | B8 |
| APG-S04-L0104 | Identify extracted fields, page/region or source location where supported, and any unresolved ambiguity. | Not in E35. | B8 |
| APG-S04-L0105 | Require verification for material values such as amounts, quantities, rates, tax, dates, contractual terms, retention provisions, payment conditions, specifications and variations. | Quote values only. | B8 |
| APG-S04-L0107 | Keep unverified extracted values in quarantine or clearly labelled provisional analysis. | State is available through E01, but non-quote extracted values have no entity to sit in. | B8 |
| APG-S04-L0108 | Record reviewer identity, timestamp, value confirmed or corrected, evidence considered and disposition. | E35 has verified by (and verified on today); corrected value, evidence considered and disposition missing. | B8 |
| APG-S04-L0111 | Maintain source revision/version, received time, effective time where available, and relationship to superseded/corrected records. | Revision and supersession covered; received and effective time are not on E01 (E83 has received for documents only). | B1 |
| APG-S04-L0114 | Route unresolved material conflicts to authorised review and prevent them from changing authoritative financial views. | No reconciliation/conflict case entity. | B3 |
| APG-S04-L0125 | Record processing state and correlation identifiers across ingestion, reconciliation, canonical update and downstream consumers. | No processing record. | B2 |
| APG-S04-L0129 | Make partial batch success/failure visible at record level where feasible. | No batch/receipt record. | B2 |
| APG-S04-L0136 | Receipt time, source/effective time, payload hash or durable evidence reference, and schema/mapping versions. | Hash and received time on E83 for documents only; not on records from connectors. | B1 |
| APG-S04-L0137 | Validation results, warnings, duplicate decisions, entity matches and reconciliation status. | Only current ingestion state on E01. | B2, B3 |
| APG-S04-L0138 | Authority rule applied and relevant register version. | Not recorded per record. | B1 |
| APG-S04-L0139 | Quarantine reason, reviewer actions, corrections, approvals and final disposition. | Decisions via E87, but quarantine reason has no home. | B3 |
| APG-S04-L0140 | Canonical changes/events produced, downstream processing results and retry/replay history. | canonical changes/events produced, downstream results, retry/replay history | B2 |
| APG-S04-L0145 | Record uploader, upload time, source description, project scope, file identity/hash where feasible, and any manual transformations. | E83 has type, source, received, hash, links; uploader identity and manual transformations not named. | B10 |
| APG-S04-L0147 | Spreadsheet imports must define column mapping, units, currency, date interpretation, duplicate policy and row-level error reporting. | Column mappings need fix B4; row-level errors need fix B2. | B2, B4 |
| PG-PC-AC-02 | PG-PC-AC-02: Actuals, commitments, accruals, forecasts, exposures, opportunities and realised benefits are not conflated. | All but realised benefits covered; benefit state missing. | B17 |
| PG-PC-AC-13 | PG-PC-AC-13: Realised net benefit requires an approved baseline, implementation evidence and authorised verification. | benefit baseline, implementation evidence, verification | B17 |
| APG-S05-L0013 | Temporal correctness: distinguish transaction, effective, posting, forecast and calculation-as-of times. | E96 has effective date only; transaction date and posting date (with accounting period) are not a shared field group. | B9 |
| APG-S05-L0023 | Identify accounting period and calculation cut-off. | No accounting period on financial records and no cut-off/as-of on E45. | B9, B18 |
| APG-S05-L0045 | Cost-to-complete: estimate basis, owner, date, assumptions, confidence and revisions. | E41 has basis, owner, date, version; assumptions and confidence are not named. | B13 |
| APG-S05-L0046 | Accruals: period, basis, status and reconciliation to actuals. | E42 has period, cost code, amount, reversal; basis, status and the reconciling actual are missing. | B14 |
| APG-S05-L0047 | Variations/claims: approval state, value, evidence and overlap status. | Overlap status (whether already represented elsewhere) is not held. | B15 |
| APG-S05-C0053 | Every material input must have source, status, effective date where available, provenance and applicable authority rule. | The authority rule applied to each input is not recorded. | B1 |
| APG-S05-C0066 | Each component must be classified as actual, committed, estimated, risk-adjusted or scenario-only. If inputs are insufficient, return a qualified/incomplete forecast rather than silently filling gaps. | E96 value status has no risk-adjusted value. | B9 |
| APG-S05-L0070 | Preserve previous approved versions and the reason for each replacement. | E44 has the prior-baseline chain but no replacement reason. | B13 |
| APG-S05-L0080 | Record how and when the forecast can be reconciled or upgraded. | E89 holds gaps and owners but not the resolution path or expected date. | B19 |
| APG-S05-C0092 | Each exposure must have a unique identity and documented relationships to related exposures. Record gross estimated amount, method/inputs, evidence, confidence/uncertainty, time window, currency, financial classification, overlap status, owner, review state and resolution outcome. | E84 has rule, evidence, quantification, confidence, limits; no relationships, time window, classification, overlap status, owner or review state. | B15 |
| APG-S05-C0100 | Retention or bank-guarantee face value is not itself a profit loss. If an open defect delays retention release, link the relationship and calculate only distinct, evidence-supported consequences. Do not count defect cost twice. | E76 links trade retention to defects; client-held retention E75 has no defect link or hold reason. | B12 |
| APG-S05-C0104 | A saving must not be claimed merely because a proposed price is below a historical quote. Require comparable baseline, scope/specification, quantity, timing, landed-cost treatment and outcome evidence. | No entity holds a benefit with its baseline, comparability basis and outcome evidence. | B17 |
| APG-S05-C0107 | Where work is not yet executed, invoiced or otherwise sufficiently reconciled to establish the outcome, retain the benefit in an appropriate non-realised state. The exact verification evidence may vary by benefit type but must be specified and auditable. | No benefit state or verification record. | B17 |
| APG-S05-L0111 | Record changed assumptions, rule version, input provenance/freshness, owner and creation time. | E46 has assumptions; owner, rule version and input freshness are not named. | B20 |
| APG-S05-L0112 | Show gross/net effects, uncertainty and limitations. | Outputs covered; uncertainty and limitations not named. | B20 |
| APG-S05-L0122 | Record calculation ID/type, project/entity/reporting period and as-of time. | E45 does not name calculation type, scope, reporting period or as-of time. | B18 |
| APG-S05-L0124 | Record formula/rule version, currency, units, tax and rounding policy, assumptions, exclusions and calculation timestamp. | Exclusions, policy versions used and calculation timestamp are not on E45. | B18 |
| APG-S05-L0125 | Record result, quality status, prior result/version, recalculation reason and downstream use. | Measures, warnings, trigger covered; prior result link and downstream use missing. | B18 |
| PG-AI-AC-08 | PG-AI-AC-08: Severity, urgency and confidence remain separate. | separate severity, urgency, confidence | B15 |
| PG-AI-AC-09 | PG-AI-AC-09: Repeated detections update existing findings without duplicate alert spam; material changes support controlled reopening/notification. | dedup identity, notification history, reopening | B15, B16 |
| PG-AI-AC-10 | PG-AI-AC-10: Related findings link together while overlapping financial amounts are not blindly summed. | linked findings and overlap | B15 |
| PG-AI-AC-11 | PG-AI-AC-11: Correlation is not presented as proven causation without evidence. | suspected vs proven cause | B15 |
| PG-AI-AC-12 | PG-AI-AC-12: AI claims are grounded or labelled as hypotheses. | grounded vs hypothesis label | B15 |
| PG-AI-AC-16 | PG-AI-AC-16: Opportunity estimates cannot be reported as realised savings without Section 05 verification. | opportunity estimate vs verified realised saving | B17 |
| PG-AI-AC-17 | PG-AI-AC-17: Portfolio intelligence respects tenant isolation and sharing permissions. | sharing permissions | B21 |
| PG-AI-AC-18 | PG-AI-AC-18: Failed monitoring runs and stale data are observable. | Stale data via E02; run failure not held. | B18 |
| APG-S06-L0017 | Create or update a finding, prioritise it and assign an owner. | Finding and priority covered; no owner on E84 or E85. | B15 |
| APG-S06-L0019 | Track review, decision, implementation and outcome. | Decision and outcome covered; no action implementation state. | B17 |
| APG-S06-L0020 | Reassess when evidence changes; close, downgrade, reopen or supersede with an audit trail. | Supersession via E01 and decisions via E87, but E84 has no lifecycle status. | B15 |
| APG-S06-C0021 | Support event-triggered analysis and scheduled reassessment. Scheduled sweeps are required for persistent conditions that may not generate a new event. Failed monitoring runs must be observable; the absence of an alert is not proof that no issue exists. | E45 is a calculation run with no run status or failure; scheduled detection sweeps have no record. | B18 |
| APG-S06-C0036 | Data-integrity findings must be distinguishable from confirmed financial leakage. A missing record may create reporting risk but is not automatically a financial loss. | E84 has no financial interpretation class. | B15 |
| APG-S06-C0040 | Each rule requires a stable identifier, version, purpose, inputs, evaluation logic, thresholds, exceptions, severity mapping and test cases. Thresholds must be configurable within approved governance boundaries and may not be silently changed by AI. | N01 holds versioned thresholds and severity grading; allowed ranges (approved boundaries) and rule exceptions are not named in its field groups. Rule logic and test cases live in the detection catalogue/code. | B16 |
| APG-S06-C0054 | Connect related evidence across design, quantities, procurement, delivery, programme, labour, quality, defects, retention and cash flow. Show the evidence chain and distinct financial effects. Related findings must not automatically be summed as independent losses. | Evidence covered; finding-to-finding relationships not held. | B15 |
| APG-S06-L0057 | Show why an observation differs from the baseline. | E84 has no explanation (observed, expected, reason). | B15 |
| APG-S06-C0065 | Material AI-generated assertions must trace to supporting evidence or be labelled as inference, hypothesis or unverified suggestion. | No such label on E84 (E68 hypothesis covers quality only). | B15 |
| APG-S06-L0067 | Identity: stable finding ID, project/portfolio scope and finding version. | Version via E01 revision; scope not on E84. | B15 |
| APG-S06-L0068 | Classification: taxonomy family, subtype and detection method. | Not on E84. | B15 |
| APG-S06-L0069 | Status: detected, under review, confirmed, dismissed, action proposed, action approved, in progress, resolved, reopened or superseded. | E85 state is the alert's; E84 has no lifecycle status. | B15 |
| APG-S06-L0072 | Explanation: observed condition, expected condition and reason. | observed condition, expected condition, reason | B15 |
| APG-S06-L0073 | Financial interpretation: actual loss, forecast exposure, potential opportunity, data-quality risk or non-financial operational risk. | financial interpretation class | B15 |
| APG-S06-L0076 | Priority: severity, urgency, time sensitivity and potential impact. | E85 holds one priority; severity and urgency are not held separately. | B15 |
| APG-S06-L0077 | Ownership: responsible role, reviewer and next review date. | responsible role, reviewer, next review date | B15 |
| APG-S06-L0078 | Relationships: linked findings, root-cause hypotheses and overlap/double-counting groups. | E68 is quality-only; no general relationship or overlap group. | B15 |
| APG-S06-C0087 | Keep severity, urgency and confidence separate. A high-severity finding with weak evidence warrants careful verification, not presentation as a confirmed loss. Thresholds and weights must be documented, testable and approved; AI cannot silently rewrite policy. | Thresholds via N01; urgency not separate from severity. | B15 |
| APG-S06-L0090 | Deduplicate repeated detection of the same underlying condition. | No dedup key on E84. | B15 |
| APG-S06-L0092 | Create a new linked finding for a genuinely distinct issue. | linked new finding | B15 |
| APG-S06-L0093 | Link symptoms to a common cause where evidence supports it; distinguish suspected relationships from confirmed causation. | Quality-only today. | B15 |
| APG-S06-L0094 | Prevent portfolio aggregation from summing overlapping exposures. | overlap groups for portfolio aggregation | B15 |
| APG-S06-L0096 | Reopen when new evidence materially changes the situation. | No lifecycle status on E84. | B15 |
| APG-S06-C0098 | Repeated detections of the same unresolved condition must update the existing finding rather than generate duplicate findings or notifications each processing cycle. Preserve change history and notification history. Controlled reopening or renewed notification is permitted when material new evidence, a meaningful status transition or an approved escalation condition occurs. Define deduplication identity, suppression window and re-notification rules, and test them. | Notification history via E85 rows; dedup identity (B15) and suppression/re-notification settings (B16) missing. | B15, B16 |
| APG-S06-C0109 | Use discovered event/workflow contracts. Scheduled sweeps must detect persistent conditions that do not generate events. Failed monitoring runs must be observable; no alert does not prove no issue. | monitoring run records incl. failures | B18 |
| APG-S06-C0112 | Distinguish detected signal from confirmed finding, recommendation from approved action, and implemented action from verified outcome. Dismissal/deferment of material findings must record rationale; retain evidence and allow future reassessment. | Dismissal rationale via E87; finding status (B15) and action/benefit states (B17) missing. | B15, B17 |
| APG-S06-C0118 | Compare only sufficiently comparable projects, periods, quantities, specifications and terms. Respect tenant boundaries and data-sharing rules. One client's commercially sensitive data must not be disclosed to another merely because aggregation is useful. Govern eligibility, permitted fields, privacy and limitations for aggregated/de-identified learning. | No entity holds aggregation/sharing permissions. | B21 |
| APG-S06-L0120 | Track findings by detection method/category, confirmation/dismissal rates, reopened findings and identifiable late/missed findings. | Needs detection method, lifecycle status and a late/missed marker. | B15 |
| APG-S06-L0121 | Track time to review/resolution, estimated versus verified outcomes, data-quality factors and performance changes after rule/model revisions. | Needs lifecycle timestamps (B15) and verified benefit (B17). | B15, B17 |
| PG-SD-AC-01 | PG-SD-AC-01: Approved schedule baselines and revisions are distinguishable and historically preserved. | baselines and revisions distinguishable and preserved | B22 |
| PG-SD-AC-02 | PG-SD-AC-02: Working forecasts and scenarios cannot silently replace approved baselines. | working forecasts/scenarios vs approved baselines | B22 |
| PG-SD-AC-06 | PG-SD-AC-06: Material holding-cost exposure requires a documented counterfactual, evidenced rates, eligible duration and overlap checks. | Overlap check result not held. | B15 |
| PG-SD-AC-10 | PG-SD-AC-10: Material delivery risks link to affected activities/milestones where evidence permits. | No material-demand-to-activity link. | B25 |
| PG-SD-AC-11 | PG-SD-AC-11: Mitigation scenarios show time benefit, incremental cost, material trade-offs and uncertainty. | Uncertainty not on E46. | B20 |
| APG-S07-L0014 | Project/programme identity, programme version and approval status, baseline date and scope. | E47 has version, data date, approval; no baseline date, scope or baseline/revision designation. | B22 |
| APG-S07-L0015 | Activity identifiers/descriptions, planned and actual start/finish dates, forecast dates, dependencies and relationship types. | E48 holds planned and actual dates only; forecast dates and description missing. | B23 |
| APG-S07-L0016 | Activity calendars, working days/holidays, duration and remaining-duration estimates. | Calendar and duration covered; remaining-duration estimate missing. | B23 |
| APG-S07-L0017 | Progress measures and source, resource/subcontractor dependencies, relevant milestones and contractual dates. | Progress and milestones covered; no activity-level resource or subcontractor assignment. | B23 |
| APG-S07-C0019 | Distinguish original programme, approved revisions, working forecasts and actual performance. Preserve historical versions. Working forecasts and what-if scenarios must remain separate from approved programme versions. | E47 has no version type. | B22 |
| APG-S07-C0020 | When a programme changes, record whether the change is an approved scope/schedule revision, operational forecast update, correction or unapproved proposal. A revised completion date must not erase the earlier forecast. | programme change classification (approved revision, forecast update, correction, proposal) | B22 |
| APG-S07-L0023 | Planned versus forecast dates. | No forecast dates. | B23 |
| APG-S07-L0024 | Remaining duration and forecast completion, where the source/model supports it. | remaining duration, forecast completion | B23 |
| APG-S07-C0054 | Every material quantified holding-cost exposure must use a documented counterfactual baseline or scenario, evidenced cost rates, eligible incremental duration and overlap checks before inclusion as a quantified financial exposure. | All covered except the recorded overlap check result. | B15 |
| APG-S07-L0056 | Identify applicable resource/cost rates and their source/effective period. | E53 has category, rate, basis, source; no effective period. | B24 |
| APG-S07-C0068 | Link required-on-site dates, forecast delivery dates, lead times and affected activities. Detect late forecasts, lead-time changes, substitutions requiring approval, early-delivery storage costs, fragmented delivery costs, supply risks across work packages and alternative supply opportunities. | Forecast/promised delivery date missing from E21 and E28 has no link to an activity or work package (fix B25). Substitutions need M15 fix 3. | B25 |
| APG-S07-L0077 | Quality, safety and operational constraints requiring review. | Not in E46. | B20 |
| APG-S07-L0079 | Uncertainty, evidence gaps and responsible reviewer. | uncertainty, evidence gaps, responsible reviewer | B20 |
| APG-S07-C0086 | It must not autonomously determine entitlement to an extension of time, liability, valid service of a notice or delay damages. Contract terms and circumstances govern. Any generated deadline/interpretation must identify its source, clause/rule, assumptions and review status. Consequential notices/submissions require authorised human review and approval. | E12 has source clause, trigger, date, verification; assumptions not named. | B26 |

## COVERED-BY-PROPOSED rows, grouped by M15 fix

### Fix 1: E100 material movement and stock

- **APG-S04-L0013**: Materials and inventory: demand, specifications, quantities, stock, substitutions, delivery records and material movements.  (Stock and material movements by M15 fix 1 (E100); substitutions by M15 fix 3 (E27). Rest covered.)

### Fix 3: substitutions on E27

- **APG-S04-L0013**: Materials and inventory: demand, specifications, quantities, stock, substitutions, delivery records and material movements.  (Stock and material movements by M15 fix 1 (E100); substitutions by M15 fix 3 (E27). Rest covered.)
- **APG-S04-L0098**: Material specification, grade, unit, quantity and substitution mismatches.  (Spec and units covered (E27, N01 specification register); substitutions only by M15 fix 3.)

### Fix 4: E08 pricing basis, milestones, defects liability period

- **APG-S04-L0016**: Quality and defects: inspections, non-conformances, rework, defect responsibility, rectification, completion and DLP evidence.  (Quality records covered (E65 to E72). DLP period itself only by M15 fix 4 (E08 defects liability period). Note: inspections/test results are carried only as E65 observations.)
- **APG-S06-L0028**: Quality and defects: repeat defects, rework cost growth, unresolved DLP obligations and defect-linked cash delays.  (DLP obligations need the defects liability period: M15 fix 4.)
- **PG-SD-AC-14**: PG-SD-AC-14: Retention, security and DLP impacts remain linked but are not double-counted.  (DLP needs M15 fix 4; client-retention-to-defect link is fix B12 (see S05 C0100).)
- **PG-SD-AC-15**: PG-SD-AC-15: Post-completion obligations can remain monitored until appropriately resolved.  (Needs the defects liability period: M15 fix 4.)

### Fix 5: E64 widened to owned plant and equipment

- **APG-S05-L0060**: Plant, equipment, logistics and site overhead.  (Hired plant and overhead covered; owned plant and equipment only by M15 fix 5.)
- **APG-S06-L0031**: Equipment and logistics: idle equipment, duplicated hire, inefficient deliveries, storage and handling costs.  (Idle owned equipment needs M15 fix 5 (E64 widened to owned plant).)

### Fix 6: journals and account balances on E73/E96

- **APG-S04-L0009**: Accounting and finance: posted invoices, credits, payments, receipts, journals and relevant account balances.  (Invoices, credits, payments, receipts covered. Journals and account balances only by M15 fix 6 (E73 account and reconciled balance; E96 posted journal reference).)
- **APG-S05-L0024**: Reconcile to relevant accounting records where available.  (Needs ledger journals and account balances: M15 fix 6.)

M15 fix 2 (E101 cash-flow forecast) and the E38 budget-part change are not needed by any Part B row.


## Where I think the M15 heading-level result is wrong or incomplete

1. **It reports only 2 missing entities and 4 field gaps.** At row level, Sections 04 to 07 alone need 26 further fixes (B1 to B26 above). The heading-level method credited an entity whenever a heading pointed at it (for example S04 s4 to E02, s5 to E03, s12 to E35, S06 s6 to E84, S07 s3 to E47/E48) without checking the itemised field lists in those headings against the entities' required field groups. Section 04 s4, s5, s12 and s17, Section 05 s5.1, s7, s10 and s13, Section 06 s6 and Section 07 s3 are all itemised data lists, yet the M15 file's list of "data lists read item by item" names only S04 §2, S05 §4 and S07 §3 for these sections.
2. **S07 §3 was listed as read item by item, but E47 and E48 do not carry it**: no version type or change classification (S07 L0014, C0019, C0020), no forecast dates or remaining duration (L0015, L0016, L0023, L0024), no activity resource or subcontractor (L0017).
3. **S05 §4 was listed as read item by item, but three items are not carried**: CTC assumptions and confidence (L0045, E41), accrual basis/status/reconciliation (L0046, E42), and variation/claim overlap status (L0047).
4. **The S04 ingestion controls have no records to live in.** E01 holds only the *current* ingestion state; there is no ingestion/processing record (B2), no reconciliation or quarantine case (B3), no mapping rule register (B4) and no cross-reference table (B7). S04 s17 is an explicit audit-trail list and none of L0136 to L0140 is fully carried.
5. **E35 is quote-only**, but S04 s12 makes human verification of extracted values mandatory for invoices, contracts, delivery dockets and other documents (B8). This is one of the three audited lock decisions of S04, so it is not a minor omission.
6. **The S05 s10 / s10.1 benefit lifecycle (a mandatory lock decision of S05) has no entity.** E88 Outcome is only "decision, realised result, date"; the ten benefit states, baseline, implementation evidence and verification are not held (B17).
7. **E84 Finding covers about a third of the S06 s6 finding data contract** (B15). Two of the four S06 lock decisions (repeat detections update the existing finding; explicit relationships and overlap controls) depend on fields E84 does not have: deduplication identity, lifecycle status, relationships and overlap group.
8. **Monitoring runs.** S06 requires failed monitoring runs to be observable (C0021, C0109, PG-AI-AC-18); E45 is a calculation run with no run status (B18).
9. The six M15 fixes themselves look right where they touch Part B. Fix 1 (E100), fix 3 (substitutions on E27), fix 4 (DLP on E08), fix 5 (owned plant on E64) and fix 6 (journals and balances on E73/E96) are each needed by at least one Part B row (see the COVERED-BY-PROPOSED list). Fix 2 (E101 cash-flow forecast) and the E38 budget-part change are not exercised by Part B.

## Rows I could not judge

None. All 618 rows were judged. Judgement calls the owner or GPT may want to revisit:

- S04 L0043, L0118, L0141 are marked COVERED on the strength of E02's single "health" field group. If "health" is not meant to hold last receipt, last reconciliation, lag, error state and operational metrics, these become GAPs under B5.
- S07 L0043 (multiple interacting delay causes) is COVERED on the assumption that E52 "recorded cause" can hold more than one cause.
- S06 L0046 is COVERED through E77 events; the hold reason APG holds today (hold_reason_text) is not in E75's required field groups, which is part of fix B12.
- S06 L0030 (design changes) is COVERED through E09, E10 and E63. The blueprint row names no design-document or RFI register, so I did not invent one.
- All Claude implementation and Gemini audit rows are NO-DATA-NEED as delivery instructions, including those that name data (S04 L0171 and L0172, S05 L0157, S06 L0152, S07 L0124 and L0128). Their data is judged at the substantive rows.
