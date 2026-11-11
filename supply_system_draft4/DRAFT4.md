# APG Data Supply System (blueprint amendment, draft 4)

Nov 12, 2026 · @Emmanuel

## Status and scope

This is draft 4 of a proposed amendment to the locked APG blueprint. It is design only: nothing here authorises a build, and stage 2 stays not authorised. Under S04 §20, no production feature code or core integration logic may begin until Section 01's Discovery Exit Report is signed off, and every build item below waits for that and for your authorisation. It is the builder's (Claude's) work, not independent evidence.

Five reviews shaped it. Two independent agent checks: the audit of draft 1 (37 problems) and a scoped re-check of draft 2 (26 points), all fixed in draft 3. Then a GPT design review of draft 3 (30 points) with a note proposing a governance section, and a Gemini design review (7 points) with five further ideas. Draft 4 fixes or answers every point from all five; the fix list is in the pack. Two GPT points (28, 29) said material was missing that is in the pack. The five further ideas widen the scope and are listed separately, not designed in.

- **Rests on:** the APG Data Readiness Change Request, revision 3. That gives the 99 entities APG needs, the exact inputs of every detection rule and M4 figure (39 rows), and the survey of 16 systems builders and developers use plus 2 data sources. Corrections from its pending GPT check flow into this draft.
- **Brief:** the owner's direction of 2026-11-12. Design one data supply system with several ways in, all of it now, built in stages. APG must never be unable to work because a builder uses different software or lacks a system.
- **Out of scope:** new insights, changes to any detection rule or figure, and the integration design itself (that stays with AUIF). Where a rule or figure would need changing to use new data, this draft says so and leaves it to its own change request.

## Purpose and the rule

APG must never be unable to work because a builder uses different software, or has no system at all for some of the data. This amendment makes that a design rule, with three parts:

1. **One intake, many ways in.** Every way of supplying data is designed to feed the same Section 04 intake and its controls. No way in gets its own validation, storage or approval rules.
2. **A core way in for every entity and every field.** Each entity (revision 3's 99, plus one this draft adds) has at least one designed Level 1 way in: an import template, document or email capture, an entry screen, a setup question, or a record APG calculates. None of these needs the builder's software. Every field a current rule or M4 figure reads is checked separately (see "Field-level coverage"). For 53 of the 100 entities, that way in still has to be built (see the supply plan).
3. **A new way in never changes a rule.** Detection rules and financial figures read stored records, whichever way they arrived. Adding a way in, or a builder switching systems, changes the builder's effort, not an insight's logic. Teaching a rule or figure to use data it does not read today is a different thing: a governed change to that rule, with its own change request and tests.

A builder who uses Procore and Xero, and one who runs everything from Excel and email, are meant to get the same insights from the same verified evidence. The first does less typing.

## Architecture: one data supply system

Section 04 specifies one intake with one set of controls. Stage 1 has it only in parts, all tested on synthetic data and none in production. Paths below are inside the `apg/` package.

- A reference intake (`ingest/`) takes 11 record kinds through delivery decisions, reconciliation, authority and supplier resolution. It does not yet resolve projects, contracts or other entities, and has no freshness thresholds set.
- A second delivery loop (`fin/intake.py`, reused by `det/intake.py` and `mkt/intake.py`) takes 24 more kinds. It reuses the same mapping and delivery decisions, but cross-record checks are made inside the calculations, not by Section 04 reconciliation. The code records its own finding F-16 as closed, because det and mkt reuse the fin loop; the two loops (reference and fin) are still separate, and nothing open tracks merging them, so that merge is new work this amendment adds.
- Three supplied records are written straight to the store: retention events (`fin/cash_states.py`), authority register rows (`source_authority.py`) and extracted documents (`ingest/documents.py`).

So this amendment's first job is to bring every kind under one intake. Then it adds the front ends and a readiness layer. Every way in submits through the same stages and records its channel, the person or system, and the time. All kinds share one intake envelope and the same control checkpoints; the processing between the checkpoints is specific to each kind of record (a bank line, a defect photo, a contract and a forecast line need different validation), as Section 04 already allows.

| Intake stage | Blueprint | Stage 1 code today | What this amendment adds |
| --- | --- | --- | --- |
| Source registration and authentication | S04 §3, §4, §6, §16 | tenant scope in code; no builder channels | Per channel: signed-in users for screens; email sender verification, with the tenant never taken from the address alone (a verified sender does not make an attached document genuine or authorised: S04 §5 and §12 still apply); phone enrolment and identified users on shared site phones; tenant isolation tested on each new path |
| File handling | S04 §18 | `ingest/filestore.py`: a scan-gated import path (test double), for the reference intake only; the det and mkt intakes read files directly | Scanning of every upload, email attachment and photo before it is read, on every path; safe parsing in isolation; size, archive and resource limits; malformed or unsupported files rejected with a reason |
| Receive, duplicates and revisions | S04 §3, §7, §15 | `ingest/pipeline.py` (11 kinds) and `fin/intake.py` (24 kinds); `ingest/jobs.py` retries | One delivery loop for every kind |
| Mapping and normalisation | S04 §10, §18 | `ingest/mapping.py`: CSV only; raw value kept; a blank stays unknown; a template must be marked draft | A mapping screen; Excel and programme files (XER, MS Project XML); promotion of a template checked against real files |
| Source authority | S04 §5 | `source_authority.py`, rows written straight to the store | Setup questions that build the register and route it for approval, through the intake; authority scoped by organisation, project, record kind, field and effective period; two sources both claiming authority, or a change of authority mid-project, is held for a person to resolve, never settled by picking one |
| Validation outcomes and quarantine | S04 §8, §9 | `ingest/reconcile.py` for the 11 kinds; intrinsic outcomes only for the other 24 | The five outcomes and quarantine for every kind |
| Entity resolution and reconciliation | S04 §11 | suppliers only (`ingest/entities.py`); other checks inside the calculations | Resolution of projects, contracts, variations, activities and defects; an uncertain or material match is held until a person confirms it and never becomes an authoritative link on confidence alone |
| Human verification of document values | S04 §12 | `ingest/documents.py`: values stay unverified until a person with the verifier role confirms them; a stand-in quote parser; not linked to the intake; dates cannot be verified yet | An upload and email inbox, real extraction (needs the Engine and a vendor, EDR-22), the verification screen, and the link into the intake |
| Freshness | S04 §14 | `ingest/freshness.py`: no built-in thresholds | The thresholds you set (revision 3 proposes values) |
| Audit trail | S04 §17 | provenance fields on records (E01, partly) | Channel, person and device for each way in |
| Readiness | S06 §10, S04 §14 | not built (E89) | A readiness record per insight, the missing-data list and nudges |

Each new channel (entry, email, phone) also gets its interface documented as the 8-layer data contracts require (§11.6): purpose and caller, request and response schemas, authentication, validation, errors, behaviour when data is unavailable, audit, idempotency and tests.

[diagram in the Claude doc and the Word file: APG Data Supply System, 6 ways to supply data, 1 intake; described in words below]

In words, for readers of an export: the four Level 1 ways to supply data (import templates, document and email capture, entry screens, setup questions), phone site capture (Level 2) and AUIF integrations (Level 3) all feed one Section 04 intake. Stored records feed the rules and figures, which no way in changes. APG then derives its own records from them: findings, baselines and the readiness record that tells the builder what is missing.

## The ways in, by level

There are seven ways in: six ways for people or systems to supply data, and the records APG derives itself. Level 1 holds five of them (four ways to supply data, plus records APG derives), and every entity has at least one. Level 2 adds site capture where the data starts on site. Level 3 adds integrations to save effort. Each count is the number of entities whose register row lists that way in, split by its state today. "Partly" means something different for each way in, so each says what it means.

### Level 1: core

**Import templates (a synthetic template exists for 37 entities; 29 have none).** These take bulk data from a file, including a system's own export, such as a Procore, Xero or Jobpac report. A blank template the builder fills by hand is a fallback, not effortless capture.

- The builder maps each file layout once: which column is which field, the units, currency and date format (S04 §18). APG suggests the mapping and the builder confirms it. The mapping is saved and versioned.
- Each row gets one of the five Section 04 outcomes (accepted, accepted with warnings, pending reconciliation, quarantined, rejected), with a reason the builder can act on. A blank is never read as zero.
- Today the code reads CSV files only, and every template is a synthetic layout that must stay marked "draft". The gap is real builder layouts, a mapping screen, Excel and programme files, a way to promote a template once it is checked, and templates for the 29 entities without one.
- Real builder files have several worksheets, inconsistent headers, formulas, merged cells, subtotals and odd date formats. Each file family is supported only once real pilot files prove it; an unsupported layout is shown as unsupported, never half-imported. Programme files (XER, MS Project XML) keep their activities, relationships and calendars; they are not flattened into a table.
- A template cannot carry a value Section 04 says a person must verify. Quote readings (E35) therefore take document capture as their minimum. The approver and checker columns of the specification, landed-cost and import-check templates (E27, E33, E34) are only asserted by the file today, not governed approvals.

**Document and email capture (partly built for 17 entities; 6 have nothing).** Claims, payment schedules, quotes, invoices, contracts and certificates arrive as documents, often by email.

- The builder uploads a file or forwards an email. The sender is verified and the organisation is never taken from the address alone (S04 §6). The original message and attachment are kept. Every file is scanned and safely parsed before it is read. Who sent it and whether the document is genuine and authorised are separate questions: the second is settled by verification and the authority register, not by the sender.
- Extraction proposes values. A person with the verifier role confirms or corrects every material value before it counts (S04 §12), and APG stores who confirmed it, when, and what they looked at. Verification can be done in batches (for example a page of extracted invoice values), but each value keeps its own confirmation and provenance; batching never weakens the rule.
- "Partly" here means only the verification control exists, with a stand-in parser for quotes. It is not linked to the intake and cannot verify dates yet. Finished capture needs an inbox, the verification screen, the link into the intake and real extraction, which needs the Engine and a vendor (EDR-22) not yet chosen. Without extraction, a person keys every value, so finished document capture waits for the vendor (see release A).

**Entry screens (47 entities; none built).** These cover small, frequent facts: one forecast line, one variation, one delay, one retention event.

- One general form engine, not 47 separate screens: forms are generated from each entity's field definitions, so a new entity needs no new screen code. Each kind of record still gets its own task-shaped layout (the questions, evidence and approval steps of a variation differ from a delay or a forecast line), so the user sees the job they are doing, not a database table. It depends on the field-level schema register, a next step from revision 3, for each entity it serves.
- Values pass the same validation as an imported row. Each carries the signed-in person who entered it, and needs approval where the register requires.
- It never edits a held record. Correcting a quarantined or pending record goes through the review queue, with its roles, distinct approvers and recorded disposition (S04 §9, §13); the entry feature may only open that workflow.

**Setup questions (14 entities, counting the detection-rule settings this draft adds; 1 partly built).** Policies, maps, rates and settings the builder sets once and keeps current. They use the same general entry feature.

- Onboarding asks only what the first insights the builder wants need. Further settings are asked for when an insight that needs them is switched on, so nobody configures everything before seeing a result. Settings that affect financial figures keep their approval.
- The cost-code map is required before any figure that groups by cost code. APG suggests matches and the builder confirms each one. A record whose code is not mapped yet still completes intake: it is held as "pending cost-code mapping" only for the figures that need the code, and listed for the person who owns the mapping.
- The financial policy (E90) holds the settings the M4 figures stop without, such as the status maps (`PO_STATUS_MAP_NOT_CONFIGURED`, for example). The detection-rule settings (N01) hold each rule's thresholds and windows, R04B's instruction types and R07's pairs of comparable items, which a person declares.
- The detection-rule settings ship pre-set to defaults you approve, so a builder sees results without configuring thresholds; adjusting them is optional, within the allowed ranges (as S06 §5.1 requires thresholds to be configurable within approved boundaries); the builder's approver makes any change. Defaults are not tied to one state's contract forms.
- Every answer is versioned, submitted through the intake, and approved by the right role before it takes effect. "Partly" (the financial policy) means the policy object exists in code with no builder setup.

**Records APG calculates (17 entities list it; 8 built or partly built, 9 not).** Baselines, assessments (calculation runs), scenarios, findings, alerts and the readiness record, calculated from stored records by APG and recorded with their calculation run (Section 03). These are different from records a person confirms: retention events, root-cause hypotheses, quality cost, outcomes and prevention opportunities. APG may propose a value for those, but a person records or confirms it, through an entry screen and the intake, with its own approval; so the entry screen is their minimum way in. "Partly" mostly means the code calculates the record but does not store it as its own; the exceptions are the provenance fields (stored on other records) and retention events (stored, but written directly, outside the intake).

### Level 2: site capture

**Phone site capture (14 entities; none built).** Delays, defects with photos, deliveries, work allocation, progress, site conditions and instructions, captured where they happen.

- It is a phone-sized version of the general entry feature: the same field definitions, the same validation, the same intake. The phone is enrolled to the organisation, and the time is checked against the server. Whether capture must work offline is a question for discovery.
- The person, time, place and any photo are kept as evidence, subject to Section 09 §14 (labour data privacy and role permissions, as revision 3 cites it). Each record says how the place was established (entered by the person or taken from the device); the device location is not assumed reliable; on a shared site phone the signed-in user is recorded, not the device; workers can see what was recorded about them, and a disputed record goes through the correction route. The detail is left to the cascade impact assessment.
- Every one of its 14 entities also has a Level 1 way in, so it is never the only way in.
- A Level 1 fallback can supply the same fact, but not always at the time it happened. Where timing matters (a delay, an instruction, a defect), a record entered after the event is marked retrospective, and the readiness record qualifies the insight that uses it.

This is a change from revision 3, which listed phone capture among the required features (its decision 3). It moves to Level 2 because every site fact also has an entry screen or a template, so phone capture adds convenience rather than coverage. If you approve revision 3's decision 3 as written, phone capture stays required, and this draft's later timing would need your choice (see the decisions). Both design reviews agreed with Level 2, provided site needs are tested early: discovery of site capture, including whether it must work offline, is an early gate, not a late one.

### Level 3: integrations

**Integrations through AUIF (24 entities; none built).** Recurring feeds from systems such as Procore, Xero, MYOB and Jobpac; for Payapps, whether any feed exists is still to confirm with the vendor.

- Each feed has a source registry entry (S04 §4; revision 2 called it a source profile) and lands in the same intake. The authority register decides which system governs which field.
- They remain proposed until the Section 01 discovery. Each is chosen on four tests: the pilot builders actually use the system, it has a usable API or export, its data quality is good enough, and it saves real manual effort. Popularity alone is not a reason.
- Until then, the same data comes through those systems' export files and the import templates.

## Entity supply plan

Each entity has one minimum way in from Level 1, plus the alternatives that satisfy the same requirement. The plan covers revision 3's 99 entities plus one this draft adds: N01, the detection-rule settings, which every rule needs and no register entity holds (to be added to the register). For 47 of the 100 the minimum way in is built or partly built; for 53 it is not. The full plan is `SUPPLY_PLAN.csv`, generated from revision 3's registers by `build_supply_plan.py`.

**How the minimum way in is chosen.** A mechanical rule, so it can be checked:

1. Only Level 1 ways in count: import template, document capture, entry screen, setup question, record APG derives.
2. A value Section 04 says a person must verify (quote readings) takes document capture. Configuration takes a setup question where the register lists one. An APG record takes "APG derives" only where the register lists it and no entry screen; where people record the fact, the entry screen is the minimum.
3. Otherwise the most-built way in wins (exists, then partly, then not built). Ties go to the template, then document capture, entry screen, setup, APG derives.

**How each entity is placed in a release.** From revision 3's input contracts, with ranges such as "E47 to E50" read in full, plus five named lists in the script (M6 inputs, intake needs, the intake's own records, the readiness record's dependencies, values that must be verified). "Release" is used so as not to clash with Section 18's build phases; how the two relate is under "What is not proven".

- **Release A:** what a current rule or M4 figure actually reads; the configuration the contracts name, plus N01; the inputs of the current M6 market figures, inferred from the record kinds the M6 code ingests until their contracts are written; what the intake needs before it will use those records (the supplier list, and users and roles, which may come from the Anchor platform); the intake's own records; the readiness record; and the two APG outputs of today's code it depends on (findings and calculation runs).
- **Release B:** what closes a known limit of a current rule or figure, for example claims and certificates for revenue, accruals for actual cost, or the programme for delay cost. Supplying these changes nothing until the rule or figure that would use them is changed, under its own change request. Receivables sit here: the overdue-receivables figure reads no record today.
- **Later:** inputs of insights not built yet, settled after builder discovery, and APG outputs that today's code only partly produces (baselines, scenarios, the productivity baseline, the financial-record status), kept as their own records when their use is designed.
- **Optional:** the five developer entities, outside the locked blueprint.

| Release | Entities | Minimum way in built or partly built | Minimum way in not built |
| --- | --- | --- | --- |
| A | 44 | 37: 32 import templates (synthetic), 3 APG records (findings, calculation runs, provenance fields), 1 document capture (quote readings; verification control only), 1 setup (the financial policy) | 7: 5 setup (source registry, authority register, cost-code map, users and roles, detection-rule settings), 1 entry screen (retention events), 1 APG record (readiness) |
| B | 22 | 2: 1 import template, 1 document capture (subcontracts; verification control only, and no subcontract record kind exists) | 20: 13 templates, 6 entry screens, 1 setup |
| Later | 29 | 8: 3 templates, 4 APG records, 1 document capture | 21: 8 templates, 6 entry screens, 4 setup, 3 APG records |
| Optional | 5 | 0 | 5 templates |
| **Total** | **100** | **47** | **53** |

"Built" means the stage 1 code accepts the data on synthetic files; it does not mean it has met a real builder's file. Of release A's 44 entities, 9 go through the Section 04 reference intake today, 24 through the second delivery loop, 2 are written straight to the store, 2 are derived by current code, 5 have no record kind yet, and the last two are the provenance fields and the policy object (the plan's "intake today" column).

### Field-level coverage

A way in for an entity does not prove a way in for every field a rule reads. `build_field_coverage.py` checks every field that revision 3's 39 contract rows name (`FIELD_COVERAGE.csv`). Every named field of a supplied record is carried by an existing template today (89 field mentions, 65 distinct field names). The other named items are not template fields, and each has a supplier: retention events are recorded by a person (release A entry form); duplicate and reconciliation states are set by the intake; invoice lines and the carrying components are calculated; R04B's instruction types are a detection-rule setting (N01). The check finds no gap, and fails if one appears.

Its limits: it matches the field names the contracts give (a few entries use plain words, such as "amount", that correspond to template fields); it covers the template path only, because the entry screens and document capture will be generated from the same field definitions once the schema register exists; and it does not yet check each field's authority and verification requirement. PG-DS-AC-12 makes the full check, for every way in, a release condition.

## Data readiness

APG will tell the builder, per insight, what data it needs, what is missing, who usually holds it and how to supply it. This is the readiness record (E89), which APG will keep for every insight and project. Everything in this section is designed behaviour, not built.

**What it is built from:** revision 2's per-insight contracts (each insight's gate, completeness, freshness, verification and behaviour below the gate), which revision 3 keeps in force; revision 3's input contracts for each rule and M4 figure; this supply plan; and the intake's outcomes. The M6 market figures have no input contracts yet, so they cannot have a readiness record until those are written.

**What it will hold for each insight:**

- Its state, from the insight's own gate: eligible, qualified, blocked or unavailable. An insight is never shown as eligible while an input it needs is missing, unverified or stale.
- Each input, with five steps: capture available, validation available, authority established, reconciliation available, decision-eligible. A value that arrived but is unverified or stale stops at its step.
- For each gap: the entity and field, the period, the reason (nobody supplied it; no built way in yet; the source is not authoritative; it is unverified or stale; the underlying record does not exist), the likely holder of the information, the action owner who can supply or correct it, and the approver where one is needed. The builder assigns or confirms those roles; the way in is named, saying plainly when it is not built.
- Its scope: each readiness item belongs to a project, the organisation, a supplier, the portfolio or external data. A shared missing setting (a policy, a labour rate, the authority register) is raised once, with the projects it affects, not once per project.

**When it is reassessed:** at setup, after each intake batch or material change of state (not row by row; reassessment is queued and combined for large batches, but prompt), on a schedule, and whenever a record is corrected, quarantined, superseded or revoked (S06 §10, S04 §14).

**What the builder will see:**

1. **At onboarding, a data checklist.** The builder says which systems they use. APG shows which data those systems can supply through their export files and a template (integrations come later), and which must come another way, with the way in for each. Where the survey's sources say what a system holds, the checklist says so; where it is Claude's judgement (revision 3's "likely also" column), it says that, until a sample export confirms it.
2. **A missing-data list.** Each gap shows its factors side by side, not folded into one score (S10 §4): the amount affected, urgency, confidence in that amount, whether the person can act now, and what depends on it. A gap is never called a loss or confirmed leakage (S06 §4), and any amount comes from a traceable calculation or is labelled an estimate (S06 §2 and §7, PG-AI-AC-06).
3. **Nudges that name the period, the field and the fix,** for example: "3 May invoices from Acme Electrical have no cost code. Add the code on each invoice (assigned cost-code owner)." The responsible role is configurable. Each gap has a stable identity (entity, field, period and source), and a lifecycle: open, assigned, awaiting evidence, resolved, suppressed, reopened, superseded. A gap found again updates its existing nudge instead of sending a new one; a suppression window and re-notification rules apply, as S06 §9.1 requires for alerts. A nudge links straight to the form that fixes it, after sign-in. APG prioritises the gaps worth most, allows bulk correction where it is safe, and never asks for data it already holds.

An insight whose input has no built way in is shown at the state its gate gives: qualified where the gap only limits it, blocked or unavailable where the input is needed to run it, and never eligible. For example, R04B finds only instructions that were recorded, so until instruction capture is built its results will be labelled "recorded instructions only" (a designed label; the rule does not produce it today).

## Release A: the first usable release

Release A gives every current detection rule and M4 figure a designed Level 1 way in for every input it reads, with no phone capture and no integration. For the M6 market figures this holds only as far as their inputs can be inferred, until their contracts are written. It holds by construction: release A is defined to contain those inputs, so a check of membership could not fail and is not offered as evidence. The field check above is the real test of the fields; the gap list, `RELEASE_A_COVERAGE.csv`, has one row per contract row:

- 18 of the 39 rows read a record that does not go through the Section 04 reference intake today.
- 13 rows need the detection-rule settings (N01), 16 name financial-policy fields (E90), and 2 need both.
- 32 rows name an input, a record or a setting, whose minimum way in is not fully built. In plain terms: every M4 figure waits on the financial policy setup, and every detection rule waits on the settings. One of the 32, overdue receivables, needs only release B data.
- 2 figures read no records at all today (security carrying cost and overdue receivables), so new data alone cannot change them.

**Release A is not complete until two gates are passed:** the M6 input contracts are written and approved, and their fields checked like the rest; and the intake migration (item 1) has passed as its own milestone. Release A is also delivered progressively: the first pilot project gets the data its first chosen insights need, then the forms and document types grow. No builder is asked to populate all 100 entities.

**The minimum release A build:**

1. **One intake for every kind, as its own gated milestone.** Bring the 24 kinds of the second delivery loop and the directly written records under the Section 04 intake: reconciliation, authority and resolution beyond suppliers. This is not neutral for the rules: today they use those 24 kinds whenever the record's own checks pass, so reconciling them changes which records the rules and figures may use. It is a separate technical milestone under its own change request, with a regression baseline of today's rule and figure results taken first, every difference explained and signed off, and nothing in release A relying on the merged intake until it passes; afterwards the rules read the reconciled state, as they already do for the 11 reference kinds. PG-DS-AC-03 governs new ways in, not this migration. The other release A items do not wait for it.
2. **Import, made real.** CSV and Excel, a mapping screen, and a way to promote a checked template out of "draft" (today's code refuses any other status). Of the 32 templates, 27 can be checked against real files (a builder's, or a data source's for market and FX data). The other 5 (specification requirements, quote tiers, quote terms, landed-cost components, import checks) were written as synthetic supplements because no builder file carries them; with the minimum build, builders would fill them by hand.
3. **The general entry feature, for setup and retention only.** Setup questions and the retention-event form are its first uses, so release A needs the field definitions for those entities and the form generator. The source registry, authority register, cost-code map, users and roles (or the Anchor platform's, if Section 01 discovery finds them there), the financial policy with its status maps, and the detection-rule settings come through it.
4. **Retention events and quote readings.** Recorded through that form and the intake, replacing today's direct write. Quote readings likewise: today's verification control is linked into the intake, so a reading counts only once a person with the verifier role confirms it (values keyed by that person until real extraction exists).
5. **The M6 input contracts.** Written first, so the market figures' inputs can be checked like the rest.
6. **Readiness for the builder.** The readiness record (with the findings and calculation runs it depends on), the onboarding checklist, the missing-data list and nudges.

**Recommended, for you to decide.** Both design reviews said the earlier recommendation (every small fact plus finished document capture) is too much for a first release. Claude now recommends a middle path:

- **Entry forms only for the facts the first pilot's insights need**, beyond setup and retention, added progressively as more insights are switched on. The five M6 supplements (specification requirements, quote tiers, quote terms, landed-cost components, import checks) are asked for only when a builder uses the market insights, and come from real quotes; APG does not invent default values for them, because they are facts from real quotes.
- **Document upload, not finished document capture:** upload and email intake with person-keyed verification, used for quote readings and as evidence attached to records. Finished capture with real extraction waits until an extraction vendor is chosen (EDR-22), because without it staff would key every value. Choosing finished capture later moves the document record (E83) into scope.

Even so, seven release A facts come only by file: purchase orders, credit notes, timesheets, bank transactions and deliveries, which usually come from the accounting, payroll or job system's export (Claude's judgement, to confirm with pilot builders), and market observations and FX rates, which are data sources rather than builder records. Discovery must confirm, for each, that the pilot builder can really produce the file; where it cannot, the readiness record shows the gap and its fallback.

## Release B, later work, and what waits for builder discovery

Release B supplies the data that would lift the known limits of today's insights. Supplying it does nothing on its own: each limit is lifted only when the rule or figure that would use the data is changed, under its own Section 18 change request with its own tests. After that, each way in is built when evidence from real builders justifies it.

**Release B (22 entities).** Client claims, certificates and receivables; subcontracts; budget revision approval; accruals and overhead allocation; the programme (versions, activities, dependencies, calendars, progress); work conditions; defect causes, rectification, quality cost and closure; retention held from trades; aged payables, statutory liabilities and payroll outflows. Their minimum ways in are mostly templates (14 of the 22, 13 still to build). Claims and certificates also suit document capture, since many builders receive them by email. Subcontractor claims, assessments and payments (E17 to E19) are not in release B by the mechanical rule (no current contract names them as a limit), so they sit in "later". Both reviews flagged them as a main source of profit leakage; promoting them to the front of release B is a decision for you (decision 7).

**Later (29 entities).** These feed insights the blueprint specifies but stage 1 has not built, such as the full quality lifecycle. Each is designed when its insight is. Four are APG outputs that today's code partly produces (baselines, scenarios, the productivity baseline, the financial-record status), stored as their own records when their use is designed.

| Way in | Build it when |
| --- | --- |
| Phone site capture | Discovery shows which site facts site staff record and how; release B's progress, conditions and closure records are the likely first |
| An integration | A pilot builder's system and data volume justify it, after the Section 01 discovery and through AUIF; until then, its export file through a template |
| A new import template | A pilot builder supplies a sample export of that data |
| A new setup question | The insight that needs the setting is designed |

**What discovery must answer:** which systems the pilot builders use; a sample export from each, to confirm the survey; what site staff capture today and on what device; and how often each kind of data changes, which sets the integration case.

## Data supply governance and lifecycle

The ways in are only half the system. The other half is knowing, for every value, who supplied it, whether it can be trusted, which version counts, who must fix a problem and which conclusions change when it changes. Most of this the blueprint already requires; this section ties it to the ways in.

- **Who does what.** For each kind of record the builder names who supplies it, who checks it, who may correct it, who approves it and who is accountable if it stays missing. One person can hold several roles; the roles stay distinct in the record (for example, a subcontractor claim entered by an administrator, checked by a contract administrator, approved by a commercial manager).
- **Data from outside the office.** Much of it starts with subcontractors, suppliers and consultants. In this design it reaches APG through the builder, by document, email, template or entry form; no external portal is designed.
- **Corrections, disputes and versions.** What was received, what changed, who changed it, why, and which version each insight used are all kept (S04 §13). A change to a record an insight used marks that insight for reassessment; an earlier conclusion stays explainable from the records it used at the time.
- **Access.** Organisation, legal entity, project and role boundaries hold on every way in, including information shared between related companies or joint ventures (S04 §6, §16).
- **Failed or incomplete supply.** A partial import, an unreadable document, a stopped feed, an unmatched record, a wrong version or a duplicate batch is shown as exactly that, with counts and reasons, and goes to the review queue (S04 §8, §9, §15; PG-DS-AC-13).
- **The builder's effort.** APG asks for the most valuable gaps first, allows safe bulk correction and never asks again for data it already holds.
- **The evidence trail.** Every conclusion traces back through its calculation and rule version to the verified, reconciled records and to the original documents, files, emails and source records, as they were at the time.

## What a new way in may and may not change

A new way in may change the intake code. It may not change a detection rule or financial figure. Rules and figures read stored records, whichever way they arrived; when two ways in supply the same field, for example invoices from both a Xero feed and a template, the authority register decides which governs, never the most recent arrival (S04 §5, §13). Teaching a rule to use new data is its own change request.

**Proposed acceptance criteria for every way in:**

| Id | Criterion |
| --- | --- |
| PG-DS-AC-01 | Every fact a person or system supplies enters through the Section 04 intake; nothing writes a supplied fact to the store directly. Records APG derives are written by its calculation runs, with the run recorded. |
| PG-DS-AC-02 | Two inputs are equivalent when, after canonical mapping, they have the same values, units, currency, date and time, tax basis, authority and verification state. Equivalent inputs supplied through any two ways in give the same field values and the same rule outcome; only the provenance differs. Shown by a test. |
| PG-DS-AC-03 | Adding a way in changes no detection rule or financial figure logic and no rule test result. Changes to the intake code are allowed. (The one-off move of today's 24 kinds onto the reconciled intake is governed by its own change request, release A item 1.) |
| PG-DS-AC-04 | Every value records its channel, the person or system that supplied it, and the time. |
| PG-DS-AC-05 | No manual way in (templates, documents, entry screens, phone capture, setup answers) bypasses validation, approval or audit (S04 §18). Setup answers are versioned and take effect only after approval by the required role. |
| PG-DS-AC-06 | Every way in meets PG-DI-AC-01 to 18, including tenant isolation tested on that path (PG-DI-AC-14), human verification of extracted values (PG-DI-AC-07) and quarantine isolation (PG-DI-AC-03 to 05). |
| PG-DS-AC-07 | Every uploaded file, email attachment and photo is scanned before it is read. |
| PG-DS-AC-08 | A held record is corrected only through the review queue, never by an entry form. |
| PG-DS-AC-09 | The readiness record is reassessed at setup, after each intake batch or material state change, on its schedule, and when a record is corrected, quarantined, superseded or revoked; an insight is never shown as eligible while an input it needs is missing, unverified or stale. |
| PG-DS-AC-10 | Each data gap has a stable identity; a gap found again updates its existing nudge instead of creating a new one; suppression windows and re-notification rules are defined and tested (S06 §9.1). |
| PG-DS-AC-11 | A way in that is not built is never offered to the builder as available. |
| PG-DS-AC-12 | Every field a current rule or figure reads has at least one built way in that carries it, with its authority and verification requirement met; shown by a generated field-coverage report that fails on a gap. |
| PG-DS-AC-13 | A partly failed or failed intake (a batch with rejected rows, an unreadable document, a stopped feed, an unmatched record) is shown as such, with its count and reasons, and never as a successful intake. |

## What is not proven, and your decisions

This design shows what to build and in what order. It does not show what it costs. No effort or cost estimate is given, because none can be made honestly before the feature designs and a real builder's files exist.

**Not proven yet:**

- **Real file layouts.** Every template is synthetic, and the code reads CSV only. One real builder's exports may need different mappings, and five M6 templates have no real file to check against at all.
- **Extraction quality.** Document capture has a stand-in parser for quotes only. How much a person must correct is unknown until a vendor is chosen.
- **Site behaviour.** What site staff will record on a phone, and how often, is unknown until discovery.
- **One intake.** Bringing the 24 kinds of the second delivery loop and the three direct writes under the Section 04 intake is design work not yet done.
- **Production readiness.** Everything is tested on synthetic data only. Under S04 §20, no production feature code starts before the Section 01 Discovery Exit Report is signed off, and tenant isolation and security (S04 §16) must be proven on every path. In Section 18's build sequence (§8), every release starts after Phase 0 and the Discovery Exit Report; release A's work spans phases 1 to 3 (the intake, authority and identity in phase 1, the financial policy in phase 2, readiness and nudges in phase 3); and no release reaches production use without the phase 4 to 6 evidence.
- **The entry feature's basis.** The general entry screen needs the field-level schema register, which is not built yet.
- **Adoption.** A complete way in can still fail if it takes too long. The pilot measures completion rates, correction effort, time to supply and the share of material inputs still missing.

**Decisions for you, in principle.** Section 18 (§6) says a change request may not be approved until its cascade impact assessment is complete. So these are approvals of direction; the formal approval follows the assessment.

1. **The architecture.** One intake, six ways to supply data in three levels plus the records APG derives, a Level 1 way in for every entity, and no rule changed by any way in.
2. **Release A scope.** The minimum build (entry forms for setup and retention only); the recommended middle path (entry forms for the first pilot's insights, document upload with person-keyed verification, M6 supplements only when used); or the earlier full option (every small fact plus finished document capture, which needs the extraction vendor). Claude recommends the middle path.
3. **The release rule.** Release A is what current insights read and need to run, release B is what lifts their known limits (each with its own rule change), and the rest waits for discovery.
4. **Phone capture.** Level 2, built when discovery shows the need (this draft), or required now, as revision 3's decision 3 proposed.
5. **The acceptance criteria.** PG-DS-AC-01 to 13.
6. **The route into the blueprint.** This amendment and revision 3 go through Section 18's change process, as one change request or two.
7. **Subcontractor claims.** Promote subcontractor claims, assessments and payments (E17 to E19) to the front of release B. Claude recommends yes.
8. **Reviewers' further ideas.** Which, if any, of the ideas below to take forward as their own change requests.

**The cascade impact assessment must cover at least:** Section 04 (one intake for every kind, the new channels and the PG-DS criteria); Section 03 and the 8-layer data contracts §11.2 (new entities, including N01 and the readiness record); Sections 06 and 10 (readiness, nudges and their ranking); Section 09 §14 (labour privacy for phone capture); Section 05 (the financial policy and its status maps); Sections 07 and 13 (release B's programme and quality entities); Section 01 (users and roles, if they come from the platform); Section 08 (the M6 input contracts); and the Master Requirements Traceability Matrix (new rows for PG-DS-AC-01 to 13).

**One gap for revision 3.** No register entity holds the detection-rule settings. This draft adds N01 for them; revision 3's register should gain the same row when its GPT check is folded in.

**Ideas raised by the reviewers, not designed here.** These widen the scope (new insights or features), so each would be its own change request:

- **Back-to-back claim checks** (Gemini): compare each subcontractor claim with the matching client claim line. A new detection rule; its data is E13 and E17.
- **Statutory declaration gating** (Gemini): hold a subcontractor's claim until a verified statutory declaration arrives. A new entity and a new rule; APG flags, a person decides payment (S10 human approval). The legal requirement differs by state and needs checking.
- **One-tap actions in messages without signing in** (Gemini): not recommended. Anyone holding the link could approve or change data, which breaks the sign-in and approval controls (S04 §6, PG-DS-AC-05). The safe form, a link that opens the exact form after sign-in, is in this design.
- **Adjudication evidence packs** (Gemini): export the full chain of evidence for a disputed claim or variation. A new feature built on the provenance this design keeps.
- **A learning cost-code map** (Gemini): learn from the builder's own confirmed mappings to suggest better matches, a person still confirming low-confidence ones. Allowed within one builder's data only, never across builders (S04 §16).

**Gaps in the locked blueprint itself:** data retention, archiving and retrieval after project close-out and when a customer leaves APG (GPT). The blueprint sections in this pack do not cover it; it needs its own change request.

**Next:** a fresh-agent check of what changed in this draft, then your decisions. No further GPT or Gemini round unless a blocking problem appears. Corrections from revision 3's GPT check are folded in first, and the supply plan is regenerated if the registers change.
