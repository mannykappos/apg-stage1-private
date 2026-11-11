# APG Data Supply System (blueprint amendment, draft 1)

Nov 12, 2026 · @Emmanuel

## Status and scope

This is draft 1 of a proposed amendment to the locked APG blueprint. It is design only: nothing here authorises a build, and stage 2 stays not authorised. It is the builder's (Claude's) work, not independent evidence, and goes to a fresh-agent audit and then GPT before the owner decides.

- **Rests on:** the APG Data Readiness Change Request, revision 3. That gives the 99 entities APG needs, the exact inputs of every rule and figure (39 rows), and the survey of 16 builder systems. Corrections from its pending GPT check flow into this draft.
- **Brief:** the owner's direction of 2026-11-12. Design one data supply system with several ways in, all of it now, built in stages. APG must never be unable to work because a builder uses different software or lacks a system.
- **Out of scope:** new insights, changes to any detection rule or figure, and the integration design itself (that stays with AUIF).

## Purpose and the rule

APG must never be unable to work because a builder uses different software, or has no system at all for some of the data. This amendment makes that a design rule, with three parts:

1. **One system, many ways in.** Every way of supplying data feeds the same Section 04 intake. No way in gets its own validation, storage or approval rules.
2. **A core way in for every entity.** Each of the 99 entities can be supplied through at least one Level 1 way in: an import template, document or email capture, an entry screen, a setup question, or a record APG creates. None of these needs the builder's software. Phone site capture and integrations add convenience on top.
3. **The rules never change for a new way in.** Detection rules and financial figures read canonical records only. Adding a way in, or a builder switching systems, changes the builder's effort, never an insight's logic.

A builder who uses Procore and Xero, and one who runs everything from Excel and email, get the same insights from the same evidence. The first does less typing.

## Architecture: one data supply system

The shared intake GPT describes already exists. Section 04 specifies it, and the stage 1 code holds a working reference version, tested on synthetic data only, not production. This amendment adds the front ends and a readiness layer. It does not add a second intake.

Every way in submits through the same stages. Each submission records its channel, the person or system, and the time, so the audit trail shows how each value arrived.

| Intake stage | Blueprint | Stage 1 code today | What this amendment adds |
| --- | --- | --- | --- |
| Receive, identify, duplicates and revisions | S04 §3, §7, §15 | `ingest/pipeline.py`, `ingest/jobs.py`: duplicate deliveries, revisions, stale deliveries, bounded retries | Every way in submits here, its channel recorded |
| Mapping and normalisation | S04 §10, §18 | `ingest/mapping.py`: raw value kept beside the mapped one; a blank stays unknown, never zero | A mapping per builder layout; entry screens and phone capture use fixed mappings |
| Source authority | S04 §5 | `apg/source_authority.py` | Setup questions that build the register and route it for approval |
| Validation outcomes and quarantine | S04 §8, §9 | `ingest/reconcile.py`: five outcomes, the worst finding wins | Nothing new |
| Entity resolution and reconciliation | S04 §11 | `ingest/entities.py`, `ingest/reconcile.py`, `ingest/review.py` | Nothing new |
| Human verification of document values | S04 §12 | `ingest/documents.py`: extracted values stay unverified until a person confirms them | An upload and email front end, and the verification screen |
| Freshness | S04 §14 | `ingest/freshness.py`: no built-in thresholds | The owner's thresholds (revision 3's table) |
| Audit trail | S04 §17 | provenance fields on records (E01, partly) | Channel, person and device for each way in |
| Readiness | S06 §10, S04 §14 | not built (E89 proposed) | A readiness record per insight, the missing-data list and nudges (see Data readiness) |

&#91;embedded content: APG Data Supply System · 7 ways in, 1 intake\]

Every way in, from a spreadsheet to a Procore feed, passes the same intake before any rule reads its data; the readiness record reports what is still missing.

## The ways in, by level

There are seven ways in, in three levels. Level 1 is the core, and every entity has at least one Level 1 way in. Level 2 adds site capture where the data starts on site. Level 3 adds integrations to save effort. The counts are revision 3's: entities each way in serves, with the way in built or partly built, against not built.

### Level 1: core

**Import templates (built or partly built for 37 entities, not built for 29).** These take bulk data from a CSV or spreadsheet, including a system's own export, such as a Procore, Xero or Jobpac report saved to Excel.

- The builder maps each file layout once: which column is which field, the units, currency and date format (S04 §18). APG suggests the mapping and the builder confirms it. The mapping is saved and versioned.
- Each row is accepted or rejected with a reason the builder can fix. A blank is never read as zero.
- Today's templates are synthetic layouts. The gap is real builder layouts, a mapping screen, and templates for the 29 entities without one.

**Document and email capture (17 built or partly, 6 not).** Claims, payment schedules, quotes, invoices, contracts and certificates arrive as documents, often by email.

- The builder uploads a file or forwards an email to an APG address for their organisation. The original is kept.
- Extraction proposes values. A person confirms or corrects every material value before it counts (S04 §12), and APG stores who confirmed it, when, and what they looked at.
- Today `ingest/documents.py` holds the verification rules and a stand-in extractor for quotes. The gap is the inbox, real extraction and the verification screen.

**Entry screens (47 not built).** These cover small, frequent facts: one forecast line, one variation, one delay, one programme activity.

- One general entry feature, not 47 screens. Each form is generated from the entity's field definitions, so a new entity gets a form without new screen code.
- Values pass the same validation as an imported row. Each value carries the person who entered it, and needs approval where the register requires.
- It depends on the field-level schema register, a next step from revision 3.

**Setup questions (1 partly built, 12 not).** Policies, maps and rates the builder sets once and then keeps current.

- A guided onboarding covers the cost-code map, the financial policy, the source registry and authority register, labour rates, holding-cost rates and work packages.
- The cost-code map is mandatory. APG suggests matches and the builder confirms each one.
- The policy includes the status maps without which the cost and commitment figures stop (`PO_STATUS_MAP_NOT_CONFIGURED`, for example).
- Every answer is versioned, and approved by the owner's approver role where the register requires.

**Records APG creates (8 built or partly, 9 not).** Baselines, assessments, scenarios, findings, alerts and the readiness record. APG generates these from other records; the builder never types them.

### Level 2: site capture

**Phone site capture (14 not built).** Delays, defects with photos, deliveries, crews, progress, site conditions and instructions, captured where they happen.

- It is a phone-sized version of the general entry feature: the same field definitions, the same validation, the same intake.
- The person, time, place and any photo are kept as evidence.
- It is never the only way in. Every one of its 14 entities also has a Level 1 way in, usually an entry screen or a template.

### Level 3: integrations

**Integrations through AUIF (24 not built).** Recurring feeds from Procore, Xero, MYOB, Jobpac, Payapps and others.

- Each feed has a source profile (S04 §4) and lands in the same intake. The authority register decides which system governs which field.
- They remain proposed until the Section 01 discovery. The first ones built follow the systems the pilot builders actually use.
- Until then, the same data comes through those systems' export files and the import templates.

## Entity supply plan

Each of the 99 entities has one minimum way in from Level 1, plus the alternatives that satisfy the same requirement. For 48 of them that minimum way in is already built or partly built; 51 need it built. Phone capture and integrations are never the minimum: every entity they serve also has a Level 1 way in. The full plan is `SUPPLY_PLAN.csv`, generated from revision 3's registers by `build_supply_plan.py`.

**How the minimum way in is chosen.** It is a mechanical rule, so it can be checked:

1. Only Level 1 ways in count: import template, document capture, entry screen, setup question, record APG creates.
2. A record APG keeps itself takes "APG creates". Configuration takes a setup question, where the register lists one.
3. Otherwise the most-built way in wins (built, then partly built, then not built). Ties go to the template, then document capture, entry screen, setup, APG creates.

**How each entity is phased.** Also mechanical, from revision 3's input contracts:

- **Phase 1:** what a current rule or financial figure reads, the configuration those contracts name, the intake's own records (provenance, source registry, authority register) and the readiness record.
- **Phase 2:** what closes a known limit of a current rule or figure, for example claims and certificates for revenue, accruals for actual cost, the programme for delay cost.
- **Later:** what the blueprint needs for insights not built yet. These are settled after builder discovery.
- **Optional:** the five developer entities, outside the locked blueprint.

| Phase | Entities | Minimum way in built or partly built | Minimum way in not built |
| --- | --- | --- | --- |
| 1 | 29 | 24: 21 import templates, 2 APG records, 1 setup (the financial policy) | 5: 3 setup (source registry, authority register, cost-code map), 1 template (receivables), 1 APG record (readiness) |
| 2 | 17 | 3: 2 import templates, 1 document capture (subcontracts) | 14: 10 templates, 2 entry screens, 1 setup, 1 APG record |
| Later | 48 | 21: 14 templates, 6 APG records, 1 document capture | 27: 10 templates, 6 entry screens, 5 setup, 6 APG records |
| Optional | 5 | 0 | 5 templates |
| **Total** | **99** | **48** | **51** |

"Built" here means the stage 1 code accepts it. The import templates are synthetic layouts, marked "draft - unverified against any real export". So a built template still needs checking against a real builder's file before it can be relied on.

## Data readiness

APG tells the builder, per insight, what data it needs, what is missing, who usually holds it and how to supply it. This is the readiness record (E89), which APG keeps for every insight and project. It joins three things that already exist: the input contracts from revision 3, the supply plan above, and the intake's states from Section 04.

**What the readiness record holds for each insight:**

- Its state, from the insight's own blueprint gate: eligible, qualified, blocked or unavailable.
- Each input from its contract, with five steps: capture available, validation available, authority established, reconciliation available, decision-eligible. A value that arrived but is unverified or stale stops at its step.
- For each gap: the entity and field, the period, the likely holder (revision 3's "likely data owner"), and the way in to supply it, saying plainly when that way in is not built yet.

**When it is reassessed:** at setup, after every intake, on a schedule, and whenever a record is corrected, quarantined, superseded or revoked (S06 §10, S04 §14).

**What the builder sees:**

1. **At onboarding, a data checklist.** The builder says which systems they use. APG shows which insights those systems can feed and which data must come another way, with the way in for each. This is the survey's judgement until a sample export confirms it, and the checklist says so.
2. **A missing-data list,** ranked by money at risk together with urgency, confidence, whether the person can act now, and what depends on it (S10 §4).
3. **Nudges that name the period, the field and the fix,** for example: "3 May invoices from Acme Electrical have no cost code. Add the code on each invoice (bookkeeper)." A money figure in a nudge comes from a traceable calculation, and a data gap is never called confirmed leakage (S06 §4).

A rule whose input has no built way in stays qualified. For example, R04B finds only instructions that were recorded, so until instruction capture is built its results say "recorded instructions only".

## Phase 1: the first usable release

Phase 1 feeds every current rule and financial figure without phone capture or any integration. The script checks this: for each of revision 3's 39 contract rows, every entity the rule reads and every configuration its contract names has a Level 1 way in in phase 1. All 39 pass (`PHASE1_CHECK.csv`). The check follows from the phase rule by design; its value is that no current insight is shown to need phone capture or an integration.

**The minimum phase 1 build:**

1. **Import, made real.** A mapping screen, the 21 existing templates checked and adjusted against one real builder's files, and one new template for receivables and receipts (E15).
2. **Setup.** The source registry, the authority register, the cost-code map (mandatory, APG suggests and the builder confirms), and the rest of the financial policy, including the status maps the figures stop without.
3. **APG's own records.** The readiness record (E89), and finishing the provenance fields (E01) and retention events (E77).
4. **Readiness for the builder.** The onboarding data checklist, the missing-data list and nudges.

**Recommended on top, for you to decide.** The minimum assumes the builder can fill a spreadsheet for everything. Two more Level 1 ways in remove that assumption for the facts that rarely sit in a tidy file:

- **The general entry screen,** for small, frequent facts (a variation, a delay, a forecast line, a defect) and for correcting a held record.
- **Document and email capture,** finished: the inbox and the verification screen, for invoices, quotes, contracts and certificates. Its verification rules already exist in the stage 1 code.

With both, most phase 1 facts no longer need a spreadsheet. Five still come only by file: purchase orders, credit notes, timesheets, bank transactions and receivables. These usually sit in the accounting or payroll system, which can export them (Claude's judgement, to confirm with pilot builders). That choice is the decision "Phase 1 scope" at the end.

## Later phases and what waits for builder discovery

Phase 2 lifts the known limits of today's insights. After that, each way in is built when evidence from real builders justifies it, not before.

**Phase 2 (17 entities).** Client claims and certificates, subcontracts, deliveries, budget revision approval, accruals, overhead allocation, the programme (versions, calendars, progress), work conditions, root cause and closure of defects, retention held from trades, aged payables, statutory liabilities and payroll outflows. Their minimum ways in are mostly templates: 12 of the 17, of which 10 are still to build. Claims and certificates also suit document capture, since many builders receive them by email.

**Later (48 entities).** These feed insights the blueprint specifies but stage 1 has not built, such as the full quality lifecycle and critical-path analysis. Each is designed when its insight is.

| Way in | Build it when |
| --- | --- |
| Phone site capture | Discovery shows which site facts site staff record and how; phase 2's progress, delivery, conditions and closure records are the likely first |
| An integration | A pilot builder's system and data volume justify it, after the Section 01 discovery and through AUIF; until then, its export file through a template |
| A new import template | A pilot builder supplies a sample export of that data |
| A new setup question | The insight that needs the setting is designed |

**What discovery must answer:** which systems the pilot builders use; a sample export from each, to confirm the survey; what site staff capture today and on what device; and how often each kind of data changes, which sets the integration case.

## What does not change

The detection rules and financial figures do not change. They read canonical records through their input contracts, and a way in only adds a route to those records. When two ways in supply the same field, for example invoices from both a Xero feed and a template, the authority register decides which governs, never the most recent arrival (S04 §5, §13).

**Proposed acceptance criteria for every way in:**

| Id | Criterion |
| --- | --- |
| PG-DS-AC-01 | It submits only through the Section 04 intake; nothing writes canonical records directly. |
| PG-DS-AC-02 | The same fact supplied through any two ways in gives the same canonical record and the same rule outcome, shown by a test. |
| PG-DS-AC-03 | Adding it changes no file under `apg/det` or `apg/fin` and no rule test result. |
| PG-DS-AC-04 | Every value records its channel, the person or system that supplied it, and the time. |
| PG-DS-AC-05 | Entry screens and phone capture cannot bypass approval or audit (S04 §18). |
| PG-DS-AC-06 | The readiness record is reassessed after every intake through it. |
| PG-DS-AC-07 | A way in that is not built is never offered to the builder as available. |

## What is not proven, and your decisions

This design shows what to build and in what order. It does not show what it costs. No effort or cost estimate is given, because none can be made honestly before the feature designs and a real builder's files exist.

**Not proven yet:**

- **Real file layouts.** Every template is synthetic. One real builder's exports may need different mappings.
- **Extraction quality.** Document capture uses a stand-in extractor today. How much a person must correct is unknown.
- **Site behaviour.** What site staff will record on a phone, and how often, is unknown until discovery.
- **Production readiness.** The stage 1 intake is tested on synthetic data only. Tenant isolation, security and the Section 01 discovery gate (S04 §16, §20) all come before any production use.
- **The entry feature's basis.** The general entry screen needs the field-level schema register, which is not built yet.

**Decisions for you:**

1. **The architecture.** One data supply system with seven ways in, in three levels, every entity with a Level 1 way in, and the rules unchanged by any way in.
2. **Phase 1 scope.** The minimum build, or the minimum plus the general entry screen and finished document capture. Claude recommends the second.
3. **The phase rule.** Phase 1 is what current insights read, phase 2 is what lifts their known limits, and the rest waits for discovery.
4. **The acceptance criteria.** PG-DS-AC-01 to 07, as above.
5. **The route into the blueprint.** This amendment and revision 3 go through Section 18's change process (S18 §6), as one change request or two.

**Next, before you decide:** a fresh-agent audit of this draft, its fixes, then one scoped GPT check. Corrections from revision 3's GPT check are folded in first, and the supply plan is regenerated if the registers change.
