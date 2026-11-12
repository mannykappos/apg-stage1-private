"""Draft 7 of the APG Data Supply System: draft 6 with the Data Readiness revision 4 corrections folded in (GPT's check of revision 3).
Each replacement must match exactly once.  Builder work (Claude), not independent."""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src).read()
R = [
 ("# APG Data Supply System (blueprint amendment, draft 6)", "# APG Data Supply System (blueprint amendment, draft 7)"),
 ("This is draft 6 of a proposed amendment", "This is draft 7 of a proposed amendment"),
 ("Draft 6 folds those conditions in. Formal approval still needs revision 3's own GPT check and the Section 18 cascade impact assessment;",
  "Draft 6 folded those conditions in. Revision 3's own GPT check then found it NOT READY (3 blocking items, 5 should-fix); the owner directed that all be fixed, and revision 4 answers them. Draft 7 folds revision 4 in: the M6 input contracts, the field-level coverage report, N01 in the register and widened to the procurement policy, and the survey's \"holding is not a feed\". Formal approval still needs revision 4's scoped GPT check and the Section 18 cascade impact assessment;"),
 ("- **Rests on:** the APG Data Readiness Change Request, revision 3. That gives the 99 entities APG needs, the exact inputs of every detection rule and M4 figure (39 rows), and the survey of 16 systems builders and developers use plus 2 data sources. Corrections from its pending GPT check flow into this draft.",
  "- **Rests on:** the APG Data Readiness Change Request, revision 4. That gives the 100 entities APG needs (N01 included), the exact inputs of every detection rule, M4 figure and M6 market figure (56 rows, 43 rules and figures, three of the rows stating behaviour shared by a group), the field-level coverage report, and the survey of 16 systems builders and developers use plus 2 data sources."),
 ("Each entity (revision 3's 99, plus one this draft adds) has at least one designed Level 1 way in",
  "Each of the 100 entities in revision 4's register has at least one designed Level 1 way in"),
 ("| Freshness | S04 §14 | `ingest/freshness.py`: no built-in thresholds | The thresholds you set (revision 3 proposes values) |",
  "| Freshness | S04 §14 | `ingest/freshness.py`: no built-in thresholds | The thresholds you set (starting values approved in principle, decision 10) |"),
 ("Excel and programme files (XER, MS Project XML); promotion", "Excel and programme files (XER; MS Project XML, its format still to be verified); promotion"),
 ("Programme files (XER, MS Project XML) keep their activities", "Programme files (XER, and MS Project XML once a sample confirms the format) keep their activities"),
 ("The detection-rule settings (N01) hold each rule's thresholds and windows, R04B's instruction types and R07's pairs of comparable items, which a person declares.",
  "The rule settings (N01) hold each detection rule's thresholds and windows, R04B's instruction types and R07's pairs of comparable items, which a person declares, and the procurement policy the M6 figures read (home currency, delivery-basis table, freshness per decision, scenario settings)."),
 ("The plan covers revision 3's 99 entities plus one this draft adds: N01, the detection-rule settings, which every rule needs and no register entity holds (to be added to the register).",
  "The plan covers the 100 entities of revision 4's register, which now holds N01, the rule settings."),
 ("generated from revision 3's registers by `build_supply_plan.py`.", "generated from revision 4's registers by `build_supply_plan.py`; moving from revision 3's registers to revision 4's changed no entity's release or minimum way in."),
 ("**How each entity is placed in a release.** From revision 3's input contracts,", "**How each entity is placed in a release.** From revision 4's input contracts,"),
 ("the inputs of the current M6 market figures, inferred from the record kinds the M6 code ingests until their contracts are written;",
  "the inputs of the current M6 market figures, read from their contracts (revision 4);"),
 ("This amendment and revision 3 go through Section 18's change process, as one change request or two.",
  "This amendment and the Data Readiness Change Request go through Section 18's change process as one change request (decision 11)."),
 ("**One gap for revision 3.** No register entity holds the detection-rule settings. This draft adds N01 for them; revision 3's register should gain the same row when its GPT check is folded in.",
  "**N01 is in the register.** Revision 4 added the rule settings to the register, as draft 6 asked, and widened them to the procurement policy the M6 figures read."),
 ("**Next:** revision 3's GPT check (the owner runs it with its pack), with its corrections folded into both documents and the supply plan regenerated if the registers change;",
  "**Next:** revision 4's scoped GPT check (the owner runs it with its pack), with any corrections folded into both documents;"),
 ("which revision 3 keeps in force; revision 3's input contracts for each rule and M4 figure; this supply plan; and the intake's outcomes. The M6 market figures have no input contracts yet, so they cannot have a readiness record until those are written.",
  "which revisions 3 and 4 keep in force; revision 4's input contracts for each rule, M4 figure and M6 figure; this supply plan; and the intake's outcomes."),
 ("Release A gives every current detection rule and M4 figure a designed Level 1 way in for every input it reads, with no phone capture and no integration. For the M6 market figures this holds only as far as their inputs can be inferred, until their contracts are written. It holds",
  "Release A gives every current detection rule, M4 figure and M6 figure a designed Level 1 way in for every input it reads, with no phone capture and no integration. It holds"),
 ("- 18 of the 39 rows read a record that does not go through the Section 04 reference intake today.\n- 13 rows need the detection-rule settings (N01), 16 name financial-policy fields (E90), and 2 need both.\n- 32 rows name an input, a record or a setting, whose minimum way in is not fully built. In plain terms: every M4 figure waits on the financial policy setup, and every detection rule waits on the settings. One of the 32, overdue receivables, needs only release B data.",
  "- 28 of the 56 rows read a record that does not go through the Section 04 reference intake today.\n- 29 rows need the rule settings (N01), 23 name financial-policy fields (E90), and 9 need both.\n- 48 rows name an input, a record or a setting, whose minimum way in is not fully built. In plain terms: every M4 figure waits on the financial policy setup, and every detection rule and M6 figure waits on the settings. One of the 48, overdue receivables, needs only release B data."),
 ("**Release A is not complete until three gates are passed:** the M6 input contracts are written and approved, and their fields checked like the rest;",
  "**Release A is not complete until three gates are passed:** the M6 input contracts (written in revision 4) are approved;"),
 ("where it is Claude's judgement (revision 3's \"likely also\" column)", "where it is Claude's judgement (the register's \"likely also\" column)"),

 ("takes 11 record kinds through delivery decisions, reconciliation, authority and supplier resolution.",
  "takes 11 record kinds through delivery decisions, reconciliation, field authority (for the material amounts of six of them) and supplier resolution."),
 ("- Three supplied records are written straight to the store: retention events (`fin/cash_states.py`), authority register rows (`source_authority.py`) and extracted documents (`ingest/documents.py`).",
  "- Two supplied records are written straight to the store: retention events (`fin/cash_states.py`) and extracted documents (`ingest/documents.py`). The source authority register is not stored at all: it is an object built in code and passed to reconciliation (`source_authority.py`), its approval asserted on the object. (Draft 6 said its rows were written straight to the store; that was wrong.)"),
 ("| Source authority | S04 §5 | `source_authority.py`, rows written straight to the store |",
  "| Source authority | S04 §5 | `source_authority.py`: an in-code register object passed to reconciliation, its approval asserted on the object; field authority resolved only for the material amounts of six reference kinds |"),
 ("**Document and email capture (partly built for 17 entities; 6 have nothing).**",
  "**Document and email capture (partly built for 3 entities: quotes, quote readings and the document record; 20 have nothing).**"),
 ("**Setup questions (14 entities, counting the detection-rule settings this draft adds; 1 partly built).**",
  "**Setup questions (14 entities, counting the rule settings; 2 partly built: the financial policy and the rule settings exist as versioned policy records, with no builder setup question).**"),
 ("| A | 44 | 37: 32 import templates (synthetic), 3 APG records (findings, calculation runs, provenance fields), 1 document capture (quote readings; verification control only), 1 setup (the financial policy) | 7: 5 setup (source registry, authority register, cost-code map, users and roles, detection-rule settings), 1 entry screen (retention events), 1 APG record (readiness) |\n| B | 22 | 2: 1 import template, 1 document capture (subcontracts; verification control only, and no subcontract record kind exists) | 20: 13 templates, 6 entry screens, 1 setup |",
  "| A | 44 | 38: 32 import templates (synthetic), 3 APG records (findings, calculation runs, provenance fields), 1 document capture (quote readings; verification control only), 2 setup (the financial policy and the rule settings: policy records, no setup question) | 6: 4 setup (source registry, authority register, cost-code map, users and roles), 1 entry screen (retention events), 1 APG record (readiness) |\n| B | 22 | 1: 1 import template | 21: 14 templates, 6 entry screens, 1 setup |"),
 ("Of release A's 44 entities, 9 go through the Section 04 reference intake today, 24 through the second delivery loop, 2 are written straight to the store, 2 are derived by current code, 5 have no record kind yet, and the last two are the provenance fields and the policy object (the plan's \"intake today\" column).",
  "Of release A's 44 entities, 9 go through the Section 04 reference intake today, 24 through the second delivery loop, 1 (retention events) is written straight to the store, 2 are derived by current code, 4 have no record kind yet, and the rest are the provenance fields, the two policy records (the financial policy and the rule settings) and the in-code authority register (the plan's \"intake today\" column)."),
 ("Bringing the 24 kinds of the second delivery loop and the three direct writes under the Section 04 intake",
  "Bringing the 24 kinds of the second delivery loop, the two direct writes and the in-code authority register under the Section 04 intake"),
 ("and the procurement policy the M6 figures read (home currency, delivery-basis table, freshness per decision, scenario settings).",
  "the procurement policy the M6 figures read (home currency, delivery-basis table, freshness per decision, scenario settings) and the specification register every M6 comparison needs (material families, attributes, match rules, unit conversions, approved by the specification owner). Today they are held as versioned, approved policy records, with no builder setup question."),
]
for a, b in R:
    n = s.count(a)
    assert n == 1, (n, a[:70])
    s = s.replace(a, b)
# the field-level coverage section: replaced whole, from its heading to the next heading
h = "### Field-level coverage\n"
i = s.index(h); j = s.index("\n## ", i)
s = s[:i] + h + """
A way in for an entity does not prove a way in for every field a rule reads. Revision 4's `build_field_coverage.py` writes two files from the contracts and the register, with no hand-entered rows:

- `FIELD_COVERAGE.csv`, one row per contract row (56): each field a contract names is checked against its own record kind in the field register, never against all kinds pooled. 155 record-kind fields are named, in 33 entities; none is missing from its kind. Plain words in a contract (such as "amount") are matched to their named field; the project is checked on each kind the M4 figures read, and credit notes, order amendments and bank lines reach it through a linked record. Items that are not template fields each have a supplier: retention events and their fields (a person, through the release A entry form; today a direct write, with no field definition yet), duplicate and reconciliation states (the intake), invoice lines and carrying components (calculated), quote terms such as payment days (values of a quote term), R04B's instruction types (N01).
- `FIELD_SUPPLY_ROUTES.csv`, one row per field (155) and one per contract row that names configuration, per settings entity (56 rows: N01, E90, E03, E20, E04): the field's entity, the entity's ways in and their status, whether the intake specifications mark it material (a proxy for S04 §12 and a lower bound: 33 fields), the verification route of each way in, and today's source authority and verification state.

What it shows today: every field is accepted by a built way in, but only by a synthetic template (19, all on quotes and quote readings, also by document capture, which is only partly built); field authority is resolved for 6 fields, the material amounts of the reference intake; 48 more pass through the reference intake with link, duplicate and supplier checks only; 101 go through the second delivery loop, which checks no authority; the material fields cannot yet be verified by a person through the intake; and no setting has a builder setup question. So no field yet meets PG-DS-AC-12 (a criterion of this design, approved in principle, not a locked blueprint ID), and the report says per row what release A must add. Its limits: it covers the fields the contracts name, which since revision 4's agent check include the fields the code was found to read beyond them; a field the code reads and no contract names would still be missed, and is caught only by checking the contracts against the code; it lists authority and verification routes, it does not test them; the field register is an inventory of the synthetic templates, not yet a validated schema register. The entry screens and document capture will be generated from the same field definitions once the schema register exists, and the check then runs for each way in as it is built (PG-DS-AC-12).
""" + s[j:]
open(dst, 'w').write(s)
print('draft 7 written', len(R), 'replacements plus the field-level section')
