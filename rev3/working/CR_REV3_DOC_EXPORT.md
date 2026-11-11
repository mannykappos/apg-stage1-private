# APG Data Readiness Change Request (revision 3)

Nov 12, 2026 · @Emmanuel (product owner) · drafted by Claude

APG must state exactly what data each insight needs, know which systems a builder uses and what they supply, and have its own way to supply everything those systems do not, whatever the share turns out to be. Revision 3 answers GPT's re-check of revision 2 (2 blocking, 6 should fix, 1 optional, 1 minor), the owner's direction of 2026-11-12 (the 80% / 20% split was an example; it may be 60 / 40 or 90 / 10), and an independent agent audit of revision 3's first draft (28 findings, all fixed; the report is in the pack).

**Status:** design direction only. It authorises no production feature code or integration work: under S04 §20 that waits for the Section 01 Discovery Exit Report and the owner's decisions below.

**What changed since revision 2:**

- **One row per entity.** 99 logical entities instead of 45 grouped rows, with the links between them (GPT blocking 1). Counts: 11 covered, 41 partial, 47 missing.
- **Inputs read from the code.** Every detection rule and every M4 financial figure (29 in all) lists the record kinds and fields it reads, what the code does when one is missing, the configuration it needs and its known limits (GPT blocking 2). The M6 market figures are not yet covered.
- **A systems survey.** 16 systems builders and developers use, and what their cited documentation supports.
- **An APG path for every entity.** Each of the 99 entities has at least one designed way to be supplied inside APG without the builder's software; integrations reduce effort but are never required.

**The honest answer to the owner's question.** The design covers every entity at any split; the code does not yet. Today 38 entities have a built path for the fields APG already holds (11 complete, 27 partial), and 37 of those 38 rely on an import template whose layout is synthetic; 10 more are partly built, and 51 can be supplied only through features designed but not built. The largest pieces still to build are entry screens (47 entities), import templates (29), integrations (24, after the Section 01 discovery), phone site capture (14) and setup questions (12).

## The requirement and the design principle

The owner's requirement (2026-11-11, restated 2026-11-12): APG must have the features to get the right data it needs to work, from whatever the builder's systems supply plus its own capture, at whatever split that turns out to be.

**The design principle: every entity has an APG path.** For each of the 99 entities, at least one designed way to supply it inside APG does not depend on the builder's software: an import template (a CSV or spreadsheet file, which a builder can fill without any particular system), document or email capture with a person confirming the values, an entry screen, phone site capture, a setup question, or a record APG creates itself. Programme data, for example, can come from a P6 or MS Project file or from a simple activity spreadsheet or entry screen. An integration with the builder's software is an accelerator: it reduces effort, but no insight depends on it. Once these paths are built, the split between what systems supply and what APG captures will change the builder's effort, not what APG can do; the features section shows which are built today.

"Fail-proof on our end" keeps revision 2's two guarantees, which GPT found resolved:

1. **No result beyond its evidence.** Each insight is shown only at the eligibility its blueprint gate allows (eligible, qualified, blocked or unavailable); a gap is never treated as satisfied, and an estimate is never shown as a fact.
2. **A way to supply every gap.** For each missing input, APG names it, says who normally holds it, and offers a working way to supply it inside APG; where that way is not built yet, it says so plainly.

## What APG needs: 99 entities

APG needs 99 logical entities; 11 are covered today, 41 partly and 47 are missing. Revision 2's 45 grouped rows are split one row per entity, following the 8-layer data contracts §11.2 (including FinancialRecord), all nine quality records of Section 13 §3, Section 03 §2 (work package, milestone, calculation run) and Section 07 for the programme. A row is "covered" only when it lists no gap.

| Class | What it is | Entities | Covered | Partial | Missing |
| --- | --- | --- | --- | --- | --- |
| Builder-source | facts the builder's systems or people hold | 60 | 9 | 27 | 24 |
| APG internal | records APG creates and maintains | 20 | 1 | 7 | 12 |
| Configuration and policy | set once by the builder, then versioned | 9 | 0 | 3 | 6 |
| Developer (optional) | the owner's developer capability; not in the locked blueprint | 5 | 0 | 0 | 5 |
| Evidence and documents | documents that support facts | 3 | 1 | 2 | 0 |
| External reference | market and FX data | 2 | 0 | 2 | 0 |
| **Total** |  | **99** | **11** | **41** | **47** |

The row-by-row register is `ENTITY_REGISTER.csv`: the blueprint section, the required field groups, the fields APG holds today, the gap, the systems the survey supports and those only judged likely, the APG supply paths with each path's status, the likely data owner, and the entities each row links to.

The largest holes:

- **Claims and payments:** client progress claims, payment schedules and receivables (E13 to E15), and subcontractor claims, assessments and payments (E17 to E19) have no record kind; a subcontract (E16) exists only as a purchase order.
- **Programme:** versions, activities, dependencies, calendars, progress and milestones are missing (E47 to E51, E99), so delay cost stays unquantified and critical-path analysis stays behind the S07 §4.1 gate.
- **Quality lifecycle:** observations, rework events, causes, rectification, quality cost, closure and prevention are missing (E65, E67 to E72, E97); only the defect record exists.
- **Cost completeness:** accruals, overhead allocation, labour rates and on-costs are missing (E42, E43, E59, E60), so actual cost is supplier invoices only (finding F-17).

## Exactly what each insight reads

Every detection rule (R01 to R09, R04B, AGG, D01, D02, DLY, LAB, DEF) and every M4 financial figure has its inputs read from the code in `apg/det/` and `apg/fin/`, not inferred from its name; the source files are in the pack. Each contract lists the record kinds and fields read, what the code does when one is missing (its own reason codes), the configuration it needs, and the known limit with the entity that closes it. The full list is `RULE_INPUT_CONTRACTS.csv` (39 rows, 29 rules and figures). The M6 market figures (landed cost, indicative comparison, buy timing) are not covered yet: a next step.

| Rule or figure | Reads | When an input or setting is missing | Known limit (entity that closes it) |
| --- | --- | --- | --- |
| M4 actual cost | supplier invoices (amount, date, cost code), credit notes, reconciliation state | held or unknown invoices are listed out and the figure is provisional; an uncoded invoice counts under "no cost code"; COST\_SCOPE\_NOT\_CONFIGURED stops it | supplier invoices only: labour, plant, accruals, contingency and overhead excluded, F-17 (E57, E64, E42, E43) |
| M4 commitments | orders (amount, date, status, cost code), amendments (delta, approved change), the invoices that name each order | PO\_STATUS\_MAP\_NOT\_CONFIGURED stops it; an unknown or unmapped status excludes the order; an amendment without an approved change is exposure | goods received but not invoiced are unknown (E29); no order approval state (E21) |
| M4 revenue | contract value, approved variations, variation status | TAX\_BASIS or VARIATION\_STATUS\_MAP not configured stops it; an unmapped status keeps the variation out | no claimed or certified amounts (E13, E14) |
| M4 cost to complete, forecast final margin | CTC lines (code, version, date, amount, basis, reason), budget, actual cost, revenue | CTC\_METHOD, FFC\_BASIS or COST\_SCOPE not configured stops it; an unknown code makes it provisional | no forecast owner, approval or tax and currency basis (E41) |
| M4 recognised margin | forecast final cost and revenue, actual cost | RECOGNITION\_METHOD\_NOT\_CONFIGURED stops it | inherits the forecast's limits |
| M4 retention, carrying cost, cash-adjusted margin | retention ledger and events, the bank receipt, the facility statement | carrying not configured, no due date, or no single facility: cannot; security carrying and overdue receivables always cannot | no retention from trades, receivables, payables due dates, payroll or statutory outflows (E76, E13 to E15, E79 to E81) |
| R01 actual over budget | M4 actual cost and budget by cost code | actual cost cannot be assessed: the rule cannot run | F-17 scope; budget revision approval unknown (E39) |
| R02 amendment without approved change | the amendments in M4 commitments | commitments cannot be assessed (PO status map) or no variation status map: cannot run | amendments on orders the commitments figure skips are never examined |
| R03 invoiced above order | committed, approved amendments and invoiced amount per order | commitments cannot be assessed: cannot run; held invoices listed | amount only: invoice quantity and unit rate not ingested, F-09 (E23 lines) |
| R04 variation unresolved | variation raised date, status, value | no variation status map: cannot run; status not mapped: not assessed; no value: unquantified | whether the work was done (E51); client correspondence (E10) |
| R04B instruction without variation | notice type, date, linked variation | not an instruction type or undated: silent | an instruction never recorded cannot be found (E10) |
| R05 retention release overdue | M4 retention: due date, held, released, hold reason | policy not pinned: cannot run; position unknown: not assessed | release conditions and claim lodged (E08, E75) |
| R06 compliance expired | evidence type, expiry, supplier | held: not assessed | a missing certificate is not detected (E82, E16) |
| R07 quote above reference | quote rate, currency (AUD only), delivery basis, freight, validity; reference rate | non-AUD, ex-works without freight: not assessed | no unit of measure or quantity on quotes (E30) |
| R08 hire beyond need | on-hire, off-hire, need date, daily rate | no need date: not assessed | hire invoices not checked; on-site confirmation (E64) |
| R09 unexplained forecast movement | CTC line code, amount, date, version, movement reason | undated or held: not assessed | the M4 movement bridge is not consulted |
| DLY overlapping delays | delay start, end, activity, cause, holding rate | no end date: not assessed | no counterfactual, no network, calendar days only (E47 to E50) |
| LAB output per hour | timesheet hours, package, rate; output quantity, week, unit | too few complete weeks or unit changes: not assessed | conditions and acceptance unverified (E63, E61) |
| DEF repeat defects | defect date, subcontractor, trade, rework cost | no subcontractor or trade: not assessed | cause and responsibility not concluded (E68 to E72) |

These contracts give the exact fields underneath revision 2's insight contracts (per insight: blueprint gate, completeness, freshness, verification and behaviour below the gate), which remain in force; revision 2 is in the pack. Each contract will be confirmed against the rule's tests when the rules are next changed.

## What builders' and developers' systems provide

No single system holds everything APG needs, and the cited sources support only 33 of the 65 builder and developer entities. For the other 32, where the data usually sits is Claude's judgement, recorded in its own register column and to be checked with pilot builders' sample exports. Searched 2026-11-12; `SYSTEMS_SURVEY.csv` lists only what each source supports.

| System | What it is | What the source supports | How data gets out | Evidence |
| --- | --- | --- | --- | --- |
| [Procore](https://procore.github.io/documentation/tutorial-financial-tools) | project management and financials, large commercial | projects, prime contracts, commitments, change events, subcontractor invoices, payment applications, payments; on the [AU page](https://www.procore.com/en-au/commercial): variations, progress claims, inspections, defect tracking | API (financials) | developer docs; vendor page |
| [Payapps](https://www.payapps.com/features/) | progress claims, head contract and subcontract | claims, payment schedules, variations, retention, compliance documents | integrations with Xero, MYOB, Jobpac, Procore; no API described | vendor page |
| [Jobpac Connect](https://info.viewpoint.com/Jobpac-Brand_01-Landing-Page.html) | construction ERP (AU, NZ) | job and labour costing, forecasting, payroll, payables, receivables; per [Mastt](https://www.mastt.com/glossary/what-is-jobpac): variations, progress claims, subcontractor payments, purchase orders | not stated | vendor page; third-party |
| [Oracle Aconex](https://help.aconex.com/apis/mail-api-developer-guide/) | document control and correspondence | that a Mail API exists; what its mail holds is to confirm | API | developer docs (existence only) |
| [Xero](https://developers.apideck.com/apis/accounting/xero/resources) | accounting | invoices, bills, credits, payments, bank transactions, purchase orders; aged debtors and creditors in beta | API | third-party |
| [MYOB](https://www.apideck.com/blog/how-to-integrate-with-the-myob-api) | accounting | invoices, bills, payments | API | third-party |
| [Buildxact](https://developer.buildxact.com/getting-started) | estimating and job management, residential | estimates, catalogues, jobs | API with partner approval | developer docs |
| [Databuild](https://www.softwareadvice.com.au/software/275036/databuild-estimating-software) | estimating and job management | estimates, orders, budgets | not established | third-party |
| [RIB CostX](https://www.capterra.com.au/software/75416/costx) | takeoff and estimating | estimates and quantities | Excel integration | third-party |
| [Oracle Primavera (P6 XML and XER)](https://docs.oracle.com/cd/E80480_01/help/en/user/234146.htm) | programme | activities, relationships, calendars, WBS, baselines | XER and XML files | developer docs |
| [HammerTech](https://www.hammertech.com/en-au/integration-partners/procore) | safety, inductions, site | labour hours by trade partner, worker counts, site diaries (synced to Procore) | Procore sync | vendor page |
| [EstateMaster](https://www.mastt.com/glossary/estatemaster) | development feasibility (developers) | feasibility, actual costs and revenues against it | not established | third-party |
| Microsoft Project | programme | not checked | XML file | not checked |
| [Employment Hero (KeyPay)](https://www.keypay.com.au/feature/integration) | payroll and timesheets | not checked | integrations and an API advertised | not checked |
| Excel and Google Sheets | spreadsheets | budgets, forecasts, registers (common practice, not sourced) | file import | not sourced |
| Email and documents | correspondence | contracts, claims, schedules, quotes, invoices, certificates | forwarding or upload, confirmed by a person | APG design |

Two consequences for the design. First, claims and payment schedules are documented only in Payapps, Procore and Jobpac, and otherwise arrive by email, so document capture is the path that works for every builder. Second, no source checked documents site-level records (progress, crews, work allocation, accepted output, rework, conditions); they likely sit in site diaries and spreadsheets (judgement), so phone site capture (CR-05 in the owner's change-request list) is the designed path that depends on no system.

## The features APG needs to fill any gap

APG's own supply paths are mostly not built: 51 of the 99 entities can today be supplied only through a path designed but not built, and 10 more are partly built. The 38 with a built path have it only for the fields APG already holds (11 complete, 27 partial), and 37 of them rely on an import template whose layout is synthetic.

[chart in the Claude doc: entities each APG supply path serves, built today vs not built; data: CHART_DATA_PATHS.csv]

What each path is, and the rule it must keep (every path passes the same Section 04 controls, S04 §18):

- **Entry screens:** small, frequent facts (one forecast line, one variation, one delay, a programme activity); each value carries the person and needs approval where the register says so.
- **Import templates:** bulk data from a CSV or spreadsheet file, or a system's export file; each builder's layout mapped once and checked, with row-level errors. Today's 36 templates are synthetic layouts (29 Builder Zero, 6 M6 supplements, 1 example), all marked "draft - unverified against any real export". `FIELD_REGISTER.csv` (215 fields) and `TEMPLATE_REGISTER.csv` are an inventory of what they accept today, not a validated schema register; that register, with validation rules and tests, is a build task.
- **Integrations through AUIF:** recurring feeds from the builder's systems, each with a versioned source profile (S04 §4); marked proposed on every row, after the Section 01 discovery; the connectors are Amir's work at the end.
- **Phone site capture (CR-05):** progress, delays, defects with photos, deliveries, crews and conditions; the person, time and place recorded as evidence.
- **Setup questions:** policies, maps and rates (the cost-code map, the financial policy, labour rates, holding-cost rates, work packages), versioned and approved by the owner where the register requires it.
- **Records APG creates:** baselines, assessments, findings, alerts, the readiness record.
- **Document and email capture:** claims, schedules, quotes, invoices and certificates, with material values confirmed by a person (S04 §12); partly built in `apg/ingest/documents.py`.

Each entity marks each of its paths as exists, partly or proposed, so no row presents an unbuilt path as a working one (GPT re-check, new problem 4); the chart's data is that column, in `CHART_DATA_PATHS.csv` in the pack.

## Readiness, intake and estimates

Revision 2's readiness, intake and estimating design stands, as GPT found it resolved, and so do its insight contracts and source profiles; this section keeps the design and applies the re-check's fixes. Everything here is designed behaviour, not current code.

**Three separate states.** The ingestion state of each record (accepted, accepted with warnings, pending reconciliation, quarantined, rejected; S04 §8); the readiness of each insight (eligible, qualified, blocked, unavailable, from its own gate); and action eligibility (whether a finding may drive a recommendation). Readiness will be reassessed at setup, after every intake, on a schedule, and whenever a record is corrected, quarantined, superseded or revoked (S06 §10, with the freshness tracking of S04 §14).

**Nudges name the period, the field and the fix.** For example: "3 May invoices from Acme Electrical have no cost code. Add the code on each invoice (bookkeeper)." Every money figure in a nudge will come from a traceable calculation, labelled with its basis; a data gap is never called confirmed leakage (S06 §4). Revision 2's "$45,000 at risk" was an illustration, not a figure from any data.

**Fix-first order uses more than money.** Gaps will be ranked by money at risk together with urgency (a deadline or a claim date), confidence in the amount, whether the person can act on it now, and what else depends on it (S10 §4); money is one factor, not the ranking rule.

**A rule that needs capture APG lacks stays qualified.** R04B can only find instructions that were recorded. Until document or phone capture of instructions (E10) is built, its results will be labelled "recorded instructions only", and an absence of findings will never be shown as "no unclaimed instructions". The same will apply to any rule whose contract names an input with no built path.

**Freshness: proposed values for the owner to set.** Revision 2 gave labels; these are maximum ages, after which the insight is qualified. The code already reads the forecast, budget and facility settings (`freshness_days`).

| Data | Good | Qualified after | Why |
| --- | --- | --- | --- |
| Variations and order amendments | 30 days | 60 days | Gemini design review |
| Cost-to-complete forecast | the current month | one month-end missed | monthly cost reporting |
| Budget revision | the current month | two month-ends | monthly cost reporting |
| Supplier invoices and credits | the last month-end | two month-ends | accounting close |
| Bank transactions | 7 days | 31 days | Claude's proposal (revision 2 had daily / weekly) |
| Facility statement | the last month | two months | statement cycle |
| Claims and payment schedules | the current claim period | one period missed | the contract's claim cycle |
| Programme | the last update | one monthly update missed | programme reporting |
| Timesheets | the last week | two weeks | pay cycle |
| Delays, defects, plant hire | weekly | monthly | revision 2's values |
| Compliance evidence | before expiry | at expiry | R06 |
| Market and quote data | S08 §7.1 per decision | S08 §7.1 per decision | the blueprint gate |

**One intake contract.** Every path passes the same Section 04 controls (S04 §18). Coverage of each input is recorded in five steps: capture available, validation available, authority established, reconciliation available, decision-eligible. A template that accepts a value does not make it correct.

**Estimates.** APG may estimate a derived result from disclosed assumptions; it never invents a missing authoritative fact. Builder forecasts, deterministic calculations from evidenced inputs and scenarios are allowed; holding cost, landed cost and indicative market comparisons only when their blueprint gates are met; a run-rate projection of a stale cost to complete only as a labelled provisional estimate the builder accepts or overrides. Progress inferred from claims, labour cost from generic award rates, and AI-inferred contract values, claims, approvals, deadlines or entitlements are not allowed. Carrying cost from face value alone is not allowed either.

## Decisions for the owner

**Now, to set the direction:**

1. Adopt the design principle (an APG path for every entity; integrations accelerate but are never required) and the two guarantees as APG's definition of "fail-proof on our end".
2. Approve the data scope: the 99 entities in `ENTITY_REGISTER.csv`, with the five developer entities as an optional extension.
3. Approve as required features, not add-ons: entry screens, document and email capture, phone site capture (CR-05), setup questions (including the cost-code map and work packages), the new import templates, and the readiness record with its nudges.
4. Make a builder-confirmed cost-code map a mandatory onboarding step; whether APG's suggestion uses AI can be decided when the step is designed (GPT optional item).
5. Set the freshness values in the table above, or replace them.
6. Give this change request its number in your change-request list (CR-01 to CR-08 and CR-10 are in use there) and say how it relates to CR-07 (builder integrations), which it overlaps: this request sets what data APG needs and its own capture; CR-07 builds the connectors.

**Blueprint changes this needs.** The new record kinds amend locked sections, so each goes through Section 18's controlled change process (S18 §6: a controlled Change Request with a cascade-impact assessment). The developer entities need a further change, because the locked blueprint does not yet cover the developer capability.

**Required before production** (decided as each part is designed): the ten shared financial foundation decisions (8-layer 02 §2.11); the Source Authority Register and its approver; baseline and assessment governance; the commitment policy, including the PO and variation status maps the code stops without; labour data privacy and role permissions (S09 §14); retention and security state handling.

**Next steps after the decisions** (all within the S04 §20 gate):

- Confirm the systems survey with two or three pilot builders' sample exports; it is documentation-level today.
- Map one real builder export (the profit autopsy data) into a first source profile.
- Write the input contracts of the M6 market figures (landed cost, indicative comparison, buy timing).
- Generate the field-level schema register with validation rules and tests.
- Cross-check the 99 entities against every row of the Master Requirements Traceability Matrix.
- Optionally, one GPT check limited to its re-check's points, then proceed; no full review round again.

## Responses to the GPT re-check and the agent audit

Every point GPT found new, partly resolved or not resolved, and where revision 3 answers it; the items GPT found resolved stand as they were. The independent agent audit of revision 3's first draft (28 findings) is in the pack as `AUDIT.txt`, with the fix for each.

| Item | The point | Where answered |
| --- | --- | --- |
| New 1 (blocking) | 45 grouped rows are not 45 entities; relationships | 99 entities, one row each, with a links column; FinancialRecord (E96), the ninth quality record (E97), work package (E98) and milestones (E99) added |
| New 2 (blocking) | rule inputs deferred to code inspection | Exactly what each insight reads; `RULE_INPUT_CONTRACTS.csv`, corrected against the code after the audit |
| New 3 | template register is not a schema register | Features, import templates: stated as an inventory; the schema register is a next step |
| New 4 | proposed paths read as working ones | each path marked exists, partly or proposed per entity, integrations always proposed; the chart and its data |
| New 5 | R04/R04b gate | Readiness: a rule that needs capture APG lacks stays qualified |
| New 6 | fix-first ranks by money only | Readiness: money is one factor of five (S10 §4) |
| New 7 | freshness thresholds too general | Readiness: maximum ages proposed, including the settings the code reads |
| New 8 | S18 and CR-06 not evidenced | S18 §6 cited and in the pack; CR-05 and CR-06 are the owner's change-request list, not the locked blueprint; decision 6 |
| New 9 | $45,000 example | stated as an illustration; nudge figures must be traceable |
| New 10 (optional) | cost-code AI policy | decision 4 |
| B3, S4, S6 | contracts not field-level; R01, R02, R09, R04, R04b deferred | rule input contracts, from the code |
| B4, S13, S15 | grouped rows; quality and other lifecycles bundled | 99-entity register (quality: E65 to E72 and E97) |
| B5 | no schema version, validation route or tests | as New 3 |
| S1 | margin inputs provisional | rule contracts: M4 revenue, actual cost, cost to complete and recognised margin, with their stops and limits |
| S3 | forecast tax and currency basis and approval | E41: owner, approval and tax and currency basis listed as gaps; foundation decisions |
| S7 | retention from client vs from trades | E75 and E76 separate; E77 retention event |
| S12 | allowances, overtime premiums | E57 (allowances, premiums, absences, breaks, adjustments), E59 and E60 |
| S14 | payables, payroll and statutory outflows | E79, E80, E81 |
| S19 | pagination and connector detail | revision 2's source profiles (in force) plus the survey; pagination and connector detail wait for the Section 01 discovery |
| O1 | nudges lack period, field and action | Readiness: nudges name the period, the field and the fix |
| Gemini design 2 and 6 | cost-code map not a settled onboarding gate | decision 4 |
| Gemini design 4, evidence 4 | 30/60-day thresholds not adopted | freshness table |
| Gemini evidence 1 | R04/R04b gate | as New 5 |
| Gemini evidence 3 | amendment governance | as New 8 |
| Gemini evidence 5 | the full matrix cross-check | next steps: the RTM cross-check |
| Agent audit, 28 findings | counts, contracts, references, survey, wording | all fixed; `AUDIT.txt` |
