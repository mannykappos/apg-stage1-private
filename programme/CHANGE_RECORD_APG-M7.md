# Change record APG-M7: recommendations, prioritisation and scenarios (programme milestone M7)

| Field | Value |
|---|---|
| Release | APG-M7. This is a new milestone release, additive to the delivered APG-M9.4 package (ZIP SHA-256 `31c05bf715b0df3e37424347fddd80a795eaaf30bc2940704688eabbcf9b44d3`). The M9.4 ZIP and documents are not modified or replaced. |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** Not integrated with the Anchor Engine. Not production-ready. |
| Authority | The product owner's instruction of Mon 2026-10-19 (Sydney) to start building M7 and then MIE-1 as code, under the standing programme authorisation for milestones M0 to M12. Each milestone is one ZIP and one documents file, built standalone without the Anchor Engine. |
| Specification | Locked Section 10 v1.0 (and Section 05 sections 10, 10.1, 11 and 13; Section 02 section 7). M7 programme row: "Build eligibility, prioritisation, scenario isolation and the realised-savings gate. Acceptance: scenarios never change the official forecast; savings count only with evidence." |
| Not started | Engine #17 and RFC-01 (still PROPOSED and unnumbered); the remaining non-Engine work of M9; M10 to M12. The open M9.4 audit items (F-52 to F-63, CF-22, CF-25, CF-29 to CF-31) are not touched and stay open. |

## 1. What this release is

It is the M7 engine of the programme plan. It covers capabilities CAP-27 (recommend what to do next, ranked and explained), CAP-28 (compare options without changing the official forecast), CAP-29 (count a saving only once it is verified) and CAP-30 (keep a human in charge). The contract is `programme/RECOMMENDATION_ENGINE.md`.

## 2. Files

Every one of the 795 files of the delivered M9.4 package is byte-identical here except the seven listed under "Changed". `python3 -I tools/run_regression_m7.py --static` checks this against `regression/m7/M9_4_MANIFEST.sha256`.

**Changed (7, all records and documents; no application or test file of M9.4 changed)**

| File | What changed |
|---|---|
| `README.md` | The M7 section is added above the unchanged M9.4 text |
| `RUN_COMMANDS.txt` | The M7 commands are added above the unchanged M9.4 text |
| `programme/STATUS_REGISTER.csv` | Rows SR-90 to SR-97 appended |
| `programme/INTERPRETATIONS_REGISTER.csv` | Rows I-99 to I-109 appended (the builder's readings, retained for review, not approved) |
| `programme/ENGINE_HANDOFF_REGISTER.csv` | Row EDR-33 appended (mapping the recommendation lifecycle to the Engine's workflow, Governor and audit contracts) |
| `programme/CARRIED_FORWARD_REGISTER.csv` | Row CF-32 appended (independent verification of M7; the earlier regression tools) |
| `programme/PROGRAMME_MILESTONES.csv` | The M7 row's status and handoff entry only |

**Added**

- **Application code.** `apg/rec/` (eight modules): `__init__.py`, `policy.py`, `engine.py`, `inputs.py`, `lifecycle.py`, `verify.py`, `demo_rec.py` and `golden_rec.py`.
- **Tests.**
  - The helper `tests/helpers_rec.py`.
  - Eleven test files: `test_rec_policy.py`, `test_rec_eligibility.py`, `test_rec_ranking.py`, `test_rec_money.py`, `test_rec_constraints.py`, `test_rec_lifecycle.py`, `test_rec_verify.py`, `test_rec_repro.py`, `test_rec_isolation.py`, `test_rec_edges.py` and `test_rec_golden.py`.
  - `test_rec_edges.py` was written after the builder's first mutation run. That run left 73 of 533 mutants alive: boundaries, displayed values, concurrency refusals and record details that no test pinned down. Of the 73, 70 are now killed and 3 are documented equivalents, each with its proof in `tools/m7_mutants.py`.
- **Tools.** `probe_rec_m7.py`, `run_regression_m7.py`, `run_m7_all.py`, `m7_mutants.py`, `sabotage_m7.py` and `make_m7_registers.py`.
- **Regression data.** `regression/m7/`: the M9.4 manifest, the M9.4 programme-table snapshot and `golden_rec.json`.
- **Logs.** `logs/m7/`: the builder's runs.
- **Documents.** `programme/RECOMMENDATION_ENGINE.md` and this record.

## 3. Decisions made and not made

**The builder chose no business value.** Every threshold, category, band, ranking order, materiality amount and offsetting-cost list is configuration with no default. The demonstration policy is synthetic.

**The builder's readings of the blueprint** are I-99 to I-109. They include:

- missing information counts as critical until it is assessed;
- urgency and time sensitivity are separate dimensions;
- the ranking is lexicographic, not weighted;
- the approval bands apply to the potential gross amount;
- a baseline is an adopted M4 forecast;
- what happens when evidence changes while an action is in progress;
- the two approval paths: M5 findings and M7 recommendations.

Each reading needs the product owner's or the reviewer's decision.

## 4. Known limits

- **No Engine integration.** There is no screen, API or Engine integration. Approval roles are role names: who holds them per project is the Engine's (EDR-33).
- **Fixture findings in the unit tests.** The unit tests use fixture findings written through the real signal contract and the real M5 lifecycle. The golden test runs the real M3 to M6 pipeline on Builder Zero.
- **Earlier regression tools are unchanged.** The per-release regression tools of M6 to M9.4 were not changed. Run on this package, they report the M7 files as undeclared additions, because each describes its own release. Run them on their own delivered ZIPs (CF-32).
