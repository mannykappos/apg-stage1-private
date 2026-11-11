# APG Data Supply System (blueprint amendment, draft 2)

Nov 12, 2026 · @Emmanuel

## Status and scope

This is draft 2 of a proposed amendment to the locked APG blueprint. It is design only: nothing here authorises a build, and stage 2 stays not authorised. Under S04 §20, no production feature code or core integration logic may begin until Section 01's Discovery Exit Report is signed off, and every build item below waits for that and for your authorisation. It is the builder's (Claude's) work, not independent evidence.

Draft 2 fixes all 37 findings of an independent agent audit of draft 1 (6 blocking, 16 should fix, 12 minor, 3 optional). The report and the fix for each finding are in the pack.

- **Rests on:** the APG Data Readiness Change Request, revision 3. That gives the 99 entities APG needs, the exact inputs of every detection rule and M4 figure (39 rows), and the survey of 16 systems builders and developers use plus 2 data sources. Corrections from its pending GPT check flow into this draft.
- **Brief:** the owner's direction of 2026-11-12. Design one data supply system with several ways in, all of it now, built in stages. APG must never be unable to work because a builder uses different software or lacks a system.
- **Out of scope:** new insights, changes to any detection rule or figure, and the integration design itself (that stays with AUIF). Where a rule or figure would need changing to use new data, this draft says so and leaves it to its own change request.

## Purpose and the rule

APG must never be unable to work because a builder uses different software, or has no system at all for some of the data. This amendment makes that a design rule, with three parts:

1. **One intake, many ways in.** Every way of supplying data is designed to feed the same Section 04 intake and its controls. No way in gets its own validation, storage or approval rules.
2. **A core way in for every entity.** Each entity (revision 3's 99, plus one this draft adds) has at least one designed Level 1 way in: an import template, document or email capture, an entry screen, a setup question, or a record APG derives from other records. None of these needs the builder's software. For 53 of these 100, that way in still has to be built (see the supply plan).
3. **A new way in never changes a rule.** Detection rules and financial figures read stored records, whichever way they arrived. Adding a way in, or a builder switching systems, changes the builder's effort, not an insight's logic. Teaching a rule or figure to use data it does not read today is a different thing: a governed change to that rule, with its own change request and tests.

A builder who uses Procore and Xero, and one who runs everything from Excel and email, are meant to get the same insights from the same verified evidence. The first does less typing.

## Architecture: one data supply system

Section 04 specifies one intake with one set of controls. Stage 1 has it only in parts, all tested on synthetic data and none in production:

- A reference intake (`apg/ingest`) takes 11 record kinds with the full Section 04 treatment: delivery decisions, reconciliation, authority and supplier resolution.
- Milestone intakes (`apg/fin/intake.py`, also used by `apg/det` and `apg/mkt`) take 24 more kinds. They copy the same mapping and delivery decisions, but cross-record checks are made inside the calculations, not by Section 04 reconciliation. Merging the two loops is already logged as finding F-16.
- Two records are written straight to the store: retention events (`fin/cash_states.py`) and authority register rows (`source_authority.py`).

So this amendment's first job is to bring every kind under one intake. Then it adds the front ends and a readiness layer. Every way in submits through the same stages and records its channel, the person or system, and the time.

| Intake stage | Blueprint | Stage 1 code today | What this amendment adds |
| --- | --- | --- | --- |
| Source registration and authentication | S04 §3, §4, §6, §16 | tenant scope in code; no builder channels | Per channel: signed-in users for screens; email sender verification, with the tenant never taken from the address alone; phone enrolment; tenant isolation tested on each new path |
| File handling | S04 §18 | `ingest/filestore.py`: a scan-gated import path (test double) | Scanning of every upload, email attachment and photo before it is read |
| Receive, duplicates and revisions | S04 §3, §7, §15 | `ingest/pipeline.py` (11 kinds) and its copy in `fin/intake.py` (24 kinds); `ingest/jobs.py` retries | One delivery loop for every kind |
| Mapping and normalisation | S04 §10, §18 | `ingest/mapping.py`: CSV only; raw value kept; a blank stays unknown; a template must be marked draft | A mapping screen; Excel and programme files (XER, MS Project XML); promotion of a template checked against real files |
| Source authority | S04 §5 | `source_authority.py`, rows written straight to the store | Setup questions that build the register and route it for approval, through the intake |
| Validation outcomes and quarantine | S04 §8, §9 | `ingest/reconcile.py` for the 11 kinds; intrinsic outcomes only for the other 24 | The five outcomes and quarantine for every kind |
| Entity resolution and reconciliation | S04 §11 | suppliers only (`ingest/entities.py`); other checks inside the calculations | Resolution of projects, contracts, variations, activities and defects |
| Human verification of document values | S04 §12 | `ingest/documents.py`: values stay unverified until a person with the verifier role confirms them; a stand-in quote parser; not linked to the intake; dates cannot be verified yet | An upload and email inbox, real extraction (needs the Engine and a vendor, EDR-22), the verification screen, and the link into the intake |
| Freshness | S04 §14 | `ingest/freshness.py`: no built-in thresholds | The thresholds you set (revision 3 proposes values) |
| Audit trail | S04 §17 | provenance fields on records (E01, partly) | Channel, person and device for each way in |
| Readiness | S06 §10, S04 §14 | not built (E89) | A readiness record per insight, the missing-data list and nudges |

Each new channel (entry, email, phone) also gets its interface documented as the 8-layer data contracts require (§11.6): purpose, schema, authentication, validation, errors, audit, idempotency and tests.

&#91;embedded content: APG Data Supply System, 6 ways to supply data, 1 intake\]

In words, for readers of an export: the four Level 1 ways to supply data (import templates, document and email capture, entry screens, setup questions), phone site capture (Level 2) and AUIF integrations (Level 3) all feed one Section 04 intake. Stored records feed the rules and figures, which no way in changes. APG then derives its own records from them: findings, baselines and the readiness record that tells the builder what is missing.

## The ways in, by level

There are six ways to supply data, in three levels, plus the records APG derives itself. Level 1 is the core, and every entity has at least one Level 1 way in. Level 2 adds site capture where the data starts on site. Level 3 adds integrations to save effort. Each count is the number of entities whose register row lists that way in, split by its state today. "Partly" means something different for each way in, so each says what it means.

### Level 1: core

**Import templates (a synthetic template exists for 37 entities; 29 have none).** These take bulk data from a file, including a system's own export, such as a Procore, Xero or Jobpac report.

- The builder maps each file layout once: which column is which field, the units, currency and date format (S04 §18). APG suggests the mapping and the builder confirms it. The mapping is saved and versioned.
- Each row gets one of the five Section 04 outcomes (accepted, accepted with warnings, pending reconciliation, quarantined, rejected), with a reason the builder can act on. A blank is never read as zero.
- Today the code reads CSV files only, and every template is a synthetic layout that must stay marked "draft". The gap is real builder layouts, a mapping screen, Excel and programme files, a way to promote a template once it is checked, and templates for the 29 entities without one.

**Document and email capture (partly built for 17 entities; 6 have nothing).** Claims, payment schedules, quotes, invoices, contracts and certificates arrive as documents, often by email.

- The builder uploads a file or forwards an email. The sender is verified and the organisation is never taken from the address alone (S04 §6). Every file is scanned before it is read, and the original is kept.
- Extraction proposes values. A person with the verifier role confirms or corrects every material value before it counts (S04 §12), and APG stores who confirmed it, when, and what they looked at.
- "Partly" here means only the verification control exists, with a stand-in parser for quotes. It is not linked to the intake and cannot verify dates yet. The gap is the inbox, real extraction (which needs the Engine and a vendor, EDR-22), the verification screen and the link into the intake.

**Entry screens (47 entities; none built).** These cover small, frequent facts: one forecast line, one variation, one delay, one retention event.

- One general entry feature, not 47 screens. Each form is generated from the entity's field definitions, so a new entity gets a form without new screen code. It depends on the field-level schema register, a next step from revision 3.
- Values pass the same validation as an imported row. Each carries the signed-in person who entered it, and needs approval where the register requires.
- It never edits a held record. Correcting a quarantined or pending record goes through the review queue, with its roles, distinct approvers and recorded disposition (S04 §9, §13); the entry feature may only open that workflow.

**Setup questions (13 entities, counting the detection-rule settings this draft adds; 1 partly built).** Policies, maps, rates and settings the builder sets once and keeps current.

- A guided onboarding covers the cost-code map, the financial policy, the source registry and authority register, users and roles, labour rates, holding-cost rates, work packages and the detection-rule settings.
- The cost-code map is mandatory. APG suggests matches and the builder confirms each one.
- The financial policy holds the settings the figures stop without, such as the status maps (`PO_STATUS_MAP_NOT_CONFIGURED`, for example). The detection-rule settings hold each rule's thresholds and windows, R04B's instruction types and R07's pairs of comparable items, which a person declares.
- Every answer is versioned, submitted through the intake, and approved by the right role before it takes effect. "Partly" (the financial policy) means the policy object exists in code with no builder setup.

**Records APG derives (8 partly or fully built, 9 not).** Baselines, assessments, scenarios, findings, alerts and the readiness record, derived from stored records by APG's calculations and recorded with their calculation run (Section 03). Where people record or confirm the fact, the register also lists an entry screen: retention events, root-cause hypotheses, quality cost, outcomes and prevention opportunities. There APG may propose a value, but a person records it, so the entry screen is the minimum way in. "Partly" means the code computes it but does not store it as its own record.

### Level 2: site capture

**Phone site capture (14 entities; none built).** Delays, defects with photos, deliveries, crews, progress, site conditions and instructions, captured where they happen.

- It is a phone-sized version of the general entry feature: the same field definitions, the same validation, the same intake. The phone is enrolled to the organisation, and the time is checked against the server.
- The person, time, place and any photo are kept as evidence. Location and photos of workers fall under the labour-privacy rules (S09 §14): capture only what the record needs, and only for its purpose.
- Every one of its 14 entities also has a Level 1 way in, so it is never the only way in.

This is a change from revision 3, which listed phone capture among the required features (its decision 3). It moves to Level 2 because every site fact also has an entry screen or a template, so phone capture adds convenience rather than coverage. If you approve revision 3's decision 3 as written, phone capture stays required, and this draft's later timing would need your choice (see the decisions).

### Level 3: integrations

**Integrations through AUIF (24 entities; none built).** Recurring feeds from systems such as Procore, Xero, MYOB and Jobpac; for Payapps, whether any feed exists is still to confirm with the vendor.

- Each feed has a source registry entry (S04 §4; revision 2 called it a source profile) and lands in the same intake. The authority register decides which system governs which field.
- They remain proposed until the Section 01 discovery. The first ones built follow the systems the pilot builders actually use.
- Until then, the same data comes through those systems' export files and the import templates.

## Entity supply plan

Each entity has one minimum way in from Level 1, plus the alternatives that satisfy the same requirement. The plan covers revision 3's 99 entities plus one this draft adds: N01, the detection-rule settings, which every rule needs and no register entity holds (to be added to the register). For 47 of the 100 the minimum way in is built or partly built; for 53 it is not. The full plan is `SUPPLY_PLAN.csv`, generated from revision 3's registers by `build_supply_plan.py`.

**How the minimum way in is chosen.** A mechanical rule, so it can be checked:

1. Only Level 1 ways in count: import template, document capture, entry screen, setup question, record APG derives.
2. Configuration takes a setup question where the register lists one. An APG record takes "APG derives" only where the register lists it and no entry screen; where people record the fact, the entry screen is the minimum.
3. Otherwise the most-built way in wins (exists, then partly, then not built). Ties go to the template, then document capture, entry screen, setup, APG derives.

**How each entity is placed in a release.** Mechanical, from revision 3's input contracts, with ranges such as "E47 to E50" read in full. "Release" is used so as not to clash with Section 18's build phases; all releases sit inside Section 18's phases 1 to 3.

- **Release A:** what a current rule or M4 figure actually reads; the configuration the contracts name, plus N01; the inputs of the current M6 market figures, whose contracts are still to be written; what the intake needs before it will use those records (the supplier list, and users and roles, which may come from the Anchor platform); the intake's own records; and the readiness record.
- **Release B:** what closes a known limit of a current rule or figure, for example claims and certificates for revenue, accruals for actual cost, or the programme for delay cost. Supplying these changes nothing until the rule or figure that would use them is changed, under its own change request. Receivables sit here: the overdue-receivables figure reads no record today.
- **Later:** inputs of insights not built yet, settled after builder discovery.
- **Optional:** the five developer entities, outside the locked blueprint.

| Release | Entities | Minimum way in built or partly built | Minimum way in not built |
| --- | --- | --- | --- |
| A | 42 | 35: 33 import templates (synthetic), the provenance fields, the financial policy | 7: 5 setup (source registry, authority register, cost-code map, users and roles, detection-rule settings), 1 entry screen (retention events), 1 APG record (readiness) |
| B | 22 | 2: 1 import template, 1 document capture (subcontracts; verification control only) | 20: 13 templates, 6 entry screens, 1 setup |
| Later | 31 | 10: 3 templates, 6 APG records, 1 document capture | 21: 8 templates, 6 entry screens, 4 setup, 3 APG records |
| Optional | 5 | 0 | 5 templates |
| **Total** | **100** | **47** | **53** |

"Built" means the stage 1 code accepts the data on synthetic files; it does not mean it has met a real builder's file. Of release A's 42 entities, 9 go through the Section 04 reference intake today, 24 through the milestone intakes, 2 are written straight to the store, and 7 have no stored record kind yet (the plan's "intake today" column).

## Data readiness

APG will tell the builder, per insight, what data it needs, what is missing, who usually holds it and how to supply it. This is the readiness record (E89), which APG will keep for every insight and project. Everything in this section is designed behaviour, not built.

**What it is built from:** revision 2's per-insight contracts (each insight's gate, completeness, freshness, verification and behaviour below the gate), which revision 3 keeps in force; revision 3's input contracts for each rule and M4 figure; this supply plan; and the intake's outcomes. The M6 market figures have no input contracts yet, so they cannot have a readiness record until those are written.

**What it will hold for each insight:**

- Its state, from the insight's own gate: eligible, qualified, blocked or unavailable. An insight is never shown as eligible while an input it needs is missing, unverified or stale.
- Each input, with five steps: capture available, validation available, authority established, reconciliation available, decision-eligible. A value that arrived but is unverified or stale stops at its step.
- For each gap: the entity and field, the period, the likely holder (revision 3's "likely data owner") and the way in to supply it, saying plainly when that way in is not built yet.

**When it is reassessed:** at setup, after every intake, on a schedule, and whenever a record is corrected, quarantined, superseded or revoked (S06 §10, S04 §14).

**What the builder will see:**

1. **At onboarding, a data checklist.** The builder says which systems they use. APG shows which data those systems can supply through their export files and a template (integrations come later), and which must come another way, with the way in for each. Where the survey's sources say what a system holds, the checklist says so; where it is Claude's judgement (revision 3's "likely also" column), it says that, until a sample export confirms it.
2. **A missing-data list.** Each gap shows its factors side by side, not folded into one score (S10 §4): the amount affected, urgency, confidence in that amount, whether the person can act now, and what depends on it. A gap is never called a loss or confirmed leakage (S06 §4), and any amount comes from a traceable calculation or is labelled an estimate (S06 §7, PG-AI-AC-06).
3. **Nudges that name the period, the field and the fix,** for example: "3 May invoices from Acme Electrical have no cost code. Add the code on each invoice (bookkeeper)." A gap found again updates its existing nudge instead of sending a new one, with suppression and re-notification rules as S06 §9.1 requires for alerts.

A rule whose input has no built way in will be shown as qualified. For example, R04B finds only instructions that were recorded, so until instruction capture is built its results will be labelled "recorded instructions only" (a designed label; the rule does not produce it today).

## Release A: the first usable release

Release A gives every current rule and figure a designed Level 1 way in for every input it reads, with no phone capture and no integration. That holds by construction: release A is defined to contain those inputs, so a check of membership could not fail and is not offered as evidence. What is useful is the gap list, `RELEASE_A_COVERAGE.csv`, one row per contract row:

- 23 of the 39 rows read an input that does not go through the Section 04 reference intake today.
- 27 rows need detection or policy settings that no register entity held before N01.
- 5 rows depend on an input whose minimum way in is not fully built (the cost-code map, the authority register, the financial policy, retention events).
- 2 figures read no records at all today (security carrying cost and overdue receivables), so new data alone cannot change them.

**The minimum release A build:**

1. **One intake for every kind.** Bring the 24 milestone kinds and the two directly written records under the Section 04 intake: reconciliation, authority and resolution beyond suppliers. This changes the intake code, not any rule or figure.
2. **Import, made real.** CSV and Excel, a mapping screen, the synthetic templates for 33 entities checked against one real builder's files, and a way to promote a checked template out of "draft" (today's code refuses any other status).
3. **Setup.** The source registry, the authority register, the cost-code map, users and roles (or the Anchor platform's, if Section 01 discovery finds them there), the financial policy with its status maps, and the detection-rule settings.
4. **Retention events.** One entry form, through the intake, replacing today's direct write.
5. **The M6 input contracts.** Written first, so the market figures' inputs can be checked like the rest.
6. **Readiness for the builder.** The readiness record, the onboarding checklist, the missing-data list and nudges.

**Recommended on top, for you to decide.** The minimum assumes the builder can produce a file for everything. Two more Level 1 ways in remove that assumption for facts that rarely sit in a tidy file:

- **The general entry screen,** for small, frequent facts (a variation, a delay, a forecast line, a defect).
- **Document and email capture, finished:** the inbox, real extraction, the verification screen and the link into the intake, with the document record (E83) and quote readings (E35). Real extraction needs the Engine and an extraction vendor (EDR-22); without it a person keys every value.

With both, most release A facts no longer need a file. Seven still come only by file: purchase orders, credit notes, timesheets, bank transactions and deliveries, which usually come from the accounting, payroll or job system's export (Claude's judgement, to confirm with pilot builders), and market observations and FX rates, which are data sources rather than builder records.

## Release B, later work, and what waits for builder discovery

Release B supplies the data that would lift the known limits of today's insights. Supplying it does nothing on its own: each limit is lifted only when the rule or figure that would use the data is changed, under its own Section 18 change request with its own tests. After that, each way in is built when evidence from real builders justifies it.

**Release B (22 entities).** Client claims, certificates and receivables; subcontracts; budget revision approval; accruals and overhead allocation; the programme (versions, activities, dependencies, calendars, progress); work conditions; defect causes, rectification, quality cost and closure; retention held from trades; aged payables, statutory liabilities and payroll outflows. Their minimum ways in are mostly templates (14 of the 22, 13 still to build). Claims and certificates also suit document capture, since many builders receive them by email.

**Later (31 entities).** These feed insights the blueprint specifies but stage 1 has not built, such as the full quality lifecycle. Each is designed when its insight is.

| Way in | Build it when |
| --- | --- |
| Phone site capture | Discovery shows which site facts site staff record and how; release B's progress, conditions and closure records are the likely first |
| An integration | A pilot builder's system and data volume justify it, after the Section 01 discovery and through AUIF; until then, its export file through a template |
| A new import template | A pilot builder supplies a sample export of that data |
| A new setup question | The insight that needs the setting is designed |

**What discovery must answer:** which systems the pilot builders use; a sample export from each, to confirm the survey; what site staff capture today and on what device; and how often each kind of data changes, which sets the integration case.

## What a new way in may and may not change

A new way in may change the intake code. It may not change a detection rule or financial figure. Rules and figures read stored records, whichever way they arrived; when two ways in supply the same field, for example invoices from both a Xero feed and a template, the authority register decides which governs, never the most recent arrival (S04 §5, §13). Teaching a rule to use new data is its own change request.

**Proposed acceptance criteria for every way in:**

| Id | Criterion |
| --- | --- |
| PG-DS-AC-01 | Every fact a person or system supplies enters through the Section 04 intake; nothing writes a supplied fact to the store directly. Records APG derives are written by its calculation runs, with the run recorded. |
| PG-DS-AC-02 | Once the same authority and verification conditions are met, the same fact supplied through any two ways in gives the same field values and the same rule outcome; only the provenance differs. Shown by a test. |
| PG-DS-AC-03 | Adding a way in changes no detection rule or financial figure logic and no rule test result. Changes to the intake code are allowed. |
| PG-DS-AC-04 | Every value records its channel, the person or system that supplied it, and the time. |
| PG-DS-AC-05 | No manual way in (templates, documents, entry screens, phone capture, setup answers) bypasses validation, approval or audit (S04 §18). Setup answers are versioned and take effect only after approval by the required role. |
| PG-DS-AC-06 | Every way in meets PG-DI-AC-01 to 18, including tenant isolation tested on that path (PG-DI-AC-14), human verification of extracted values (PG-DI-AC-07) and quarantine isolation (PG-DI-AC-03 to 05). |
| PG-DS-AC-07 | Every uploaded file, email attachment and photo is scanned before it is read. |
| PG-DS-AC-08 | A held record is corrected only through the review queue, never by an entry form. |
| PG-DS-AC-09 | The readiness record is reassessed at setup, after every intake, on its schedule, and when a record is corrected, quarantined, superseded or revoked; an insight is never shown as eligible while an input it needs is missing, unverified or stale. |
| PG-DS-AC-10 | A data gap found again updates its existing nudge instead of creating a new one (S06 §9.1). |
| PG-DS-AC-11 | A way in that is not built is never offered to the builder as available. |

## What is not proven, and your decisions

This design shows what to build and in what order. It does not show what it costs. No effort or cost estimate is given, because none can be made honestly before the feature designs and a real builder's files exist.

**Not proven yet:**

- **Real file layouts.** Every template is synthetic, and the code reads CSV only. One real builder's exports may need different mappings.
- **Extraction quality.** Document capture has a stand-in parser for quotes only. How much a person must correct is unknown until a vendor is chosen.
- **Site behaviour.** What site staff will record on a phone, and how often, is unknown until discovery.
- **One intake.** Bringing 24 milestone kinds and two direct writers under the Section 04 intake is design work not yet done.
- **Production readiness.** Everything is tested on synthetic data only. Under S04 §20, no production feature code starts before the Section 01 Discovery Exit Report is signed off, and tenant isolation and security (S04 §16) must be proven on every path.
- **The entry feature's basis.** The general entry screen needs the field-level schema register, which is not built yet.

**Decisions for you, in principle.** Section 18 (§6) says a change request may not be approved until its cascade impact assessment is complete. So these are approvals of direction; the formal approval follows the assessment.

1. **The architecture.** One intake, six ways to supply data in three levels plus the records APG derives, a Level 1 way in for every entity, and no rule changed by any way in.
2. **Release A scope.** The minimum build, or the minimum plus the general entry screen and finished document capture. Claude recommends the second.
3. **The release rule.** Release A is what current insights read and need to run, release B is what lifts their known limits (each with its own rule change), and the rest waits for discovery.
4. **Phone capture.** Level 2, built when discovery shows the need (this draft), or required now, as revision 3's decision 3 proposed.
5. **The acceptance criteria.** PG-DS-AC-01 to 11.
6. **The route into the blueprint.** This amendment and revision 3 go through Section 18's change process, as one change request or two.

**The cascade impact assessment must cover at least:** Section 04 (one intake for every kind, the new channels and the PG-DS criteria); Section 03 and the 8-layer data contracts §11.2 (new entities, including N01 and the readiness record); Sections 06 and 10 (readiness, nudges and their ranking); Section 09 §14 (labour privacy for phone capture); Section 08 (the M6 input contracts); and the Master Requirements Traceability Matrix (new rows for PG-DS-AC-01 to 11).

**One gap for revision 3.** No register entity holds the detection-rule settings. This draft adds N01 for them; revision 3's register should gain the same row when its GPT check is folded in.

**Next, before you decide:** one scoped GPT check of this draft. Corrections from revision 3's GPT check are folded in first, and the supply plan is regenerated if the registers change.
