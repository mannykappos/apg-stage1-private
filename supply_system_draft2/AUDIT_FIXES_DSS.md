# Builder's fixes to the INDEPENDENT READ-ONLY (agent) audit of draft 1 (37 findings) — BUILDER-WRITTEN

Draft 2 is the doc after these fixes. The generator is build_supply_plan.py (draft 2); draft 1's is build_supply_plan_draft1.py.

| # | Class | Fix in draft 2 |
| --- | --- | --- |
| 1 | BLOCKING | Architecture rewritten: the reference intake takes 11 kinds; milestone intakes (apg/fin/intake.py, used by det and mkt) take 24 kinds with the same mapping and delivery decisions but cross-record checks in the calculations (F-16); two direct writers. "First job: one intake for every kind" added; "Nothing new" rows replaced; plan column "intake today"; AC-03 reworded to allow intake changes. |
| 2 | BLOCKING | ids() expands "E47 to E50" style ranges; regenerated: B 22 (adds E48, E49, E69, E70, E71). |
| 3 | BLOCKING | Current M6 inputs (E26 to E37, the kinds apg/mkt ingests) placed in release A with the reason "input to a current M6 market figure (its contract is still to be written)"; writing the M6 contracts is release A item 5; readiness section says M6 cannot have a readiness record until then. |
| 4 | BLOCKING | E20 supplier list in release A as an intake dependency; release rule states it. |
| 5 | BLOCKING | New N01 "detection-rule settings" (thresholds, windows, R04B instruction types, R07 comparable pairs) with a setup question, in release A; flagged as a gap for revision 3's register; coverage report counts the 27 rows with settings that have no entity id. |
| 6 | BLOCKING | Rule 3 reworded ("a new way in never changes a rule"; teaching a rule new data is its own change request); release B states supplying data changes nothing until the consuming rule or figure changes under its own CR; E15 moved to B (its figure reads no record); scope line updated. |
| 7 | SHOULD FIX | Membership check replaced by RELEASE_A_COVERAGE.csv; the doc says membership holds by construction and is not offered as evidence, and reports the gaps instead. |
| 8 | SHOULD FIX | Minimum rule: an APG record takes "APG derives" only where no entry screen is listed; E77 now entry screen (release A item 4, replacing the direct write); "Records APG derives" text names the person-recorded ones. |
| 9 | SHOULD FIX | E05 users and roles in release A, "or the Anchor platform's, if Section 01 discovery finds them there". |
| 10 | SHOULD FIX | Each way in says what "partly" means; document capture "verification control only"; E16 labelled so; CSV only stated. |
| 11 | SHOULD FIX | Recommended document capture now includes real extraction, E83 and E35, and the vendor dependency (EDR-22). |
| 12 | SHOULD FIX | S04 §20 quoted accurately in Status and in Not proven. |
| 13 | SHOULD FIX | Intake table gains "Source registration and authentication" and "File handling" rows; email sender verification and tenant binding; phone enrolment and server time; scanning; labour privacy (S09 §14) for phone capture. |
| 14 | SHOULD FIX | Entry feature never edits a held record; corrections go through the review queue (AC-08). |
| 15 | SHOULD FIX | Import rows get one of the five S04 outcomes. |
| 16 | SHOULD FIX | AC-01 scoped to supplied facts plus how derived records are written; AC-02 reworded per the audit; AC-03 reworded. |
| 17 | SHOULD FIX | AC-05 widened to all manual ways in incl. setup; AC-06 PG-DI-AC-01..18 per way in (incl. 07, 14, 03-05); AC-07 scanning; AC-08 corrections; AC-09 readiness reassessment and correctness; AC-10 nudge dedupe. |
| 18 | SHOULD FIX | Missing-data list shows factors side by side (S10 §4); "amount affected"; nudges dedupe per S06 §9.1. |
| 19 | SHOULD FIX | Decisions are "in principle"; the cascade impact assessment is stated as the precondition, with the sections and RTM it must cover. |
| 20 | SHOULD FIX | The change from revision 3's decision 3 is stated with its reason, and phone capture is decision 4. |
| 21 | SHOULD FIX | Phases renamed releases A / B / later / optional, with a line relating them to Section 18's phases. |
| 22 | SHOULD FIX | Tense fixed: "designed" way in, "will" for readiness, R04B label marked as designed, thresholds "you set (revision 3 proposes values)". |
| 23 | MINOR | "the synthetic templates for 33 entities". |
| 24 | MINOR | Paths given relative to apg/ consistently. |
| 25 | MINOR | "16 systems builders and developers use plus 2 data sources". |
| 26 | MINOR | "source registry entry (S04 §4; revision 2 called it a source profile)". |
| 27 | MINOR | S06 §4 and S06 §7 (PG-AI-AC-06) cited separately. |
| 28 | MINOR | Diagram redrawn (derived records after the rules, not under the intake) and described in words under it. |
| 29 | MINOR | Minimum rule step 2 states "where the register lists it". |
| 30 | MINOR | GPT reference removed. |
| 31 | MINOR | Payapps "whether any feed exists is still to confirm with the vendor". |
| 32 | MINOR | Checklist says "through their export files and a template", and labels Claude's judgement. |
| 33 | MINOR | "a person with the verifier role"; dates cannot be verified yet. |
| 34 | MINOR | Release A item 2 includes promoting a checked template out of "draft". |
| 35 | OPTIONAL | Readiness basis names revision 2's per-insight contracts and revision 3's input contracts; M6 gap stated. |
| 36 | OPTIONAL | Each new channel documented per 8-layer §11.6. |
| 37 | OPTIONAL | Plan and coverage regenerated; the generator run twice gives identical CSVs. A failing-register test was not added: the coverage report is not a pass/fail check any more. |
