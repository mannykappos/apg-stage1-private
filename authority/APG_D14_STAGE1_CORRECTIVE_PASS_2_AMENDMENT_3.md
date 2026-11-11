# APG D14 stage 1, corrective pass 2: amendment 3 (draft 2)

**BUILDER-EXECUTED: NOT INDEPENDENT. Draft for review. Not authorised until the owner posts it.**

## Basis
- **Amended:** the posted paper `23d2adb980216c9703287cd8803570dc2fab3cf48f037dfa1d39a0d3029f0ea5`, as amended by amendment 1 (`211971452c8f02ac0d24514ebc9a12c1c0cded3eeb55f2c918f125a775c6d382`) and amendment 2 (`a3cc26b5073ea4082de6a7a52013767634e076b64886bba0f49524a7f706cd6e`).
- **The stop:** `rec/ISSUE_RECORD_2026-11-06_CORRECTIVE_PASS_2_STOP_3_C1.md` (S9, S10), with its addendum of 13:55 on 2026-11-06 (S11).
- **The review:** the reviewer's review of draft 1 (13:50 on 2026-11-06), filed as `rec/reviews/RECEIVED_REVIEW_2026-11-06_1350_AMENDMENT_3_DRAFT_1.txt`. It accepted every decision and required three corrections.
- **This amendment authorises corrective work only.** It is not stage 1 acceptance and does not authorise stage 2.
- **Unchanged:** every other part of the paper and its two amendments, the stop rule H, AM-8 and the standing constraints.

## What changed from draft 1
| Change | Source | Where |
|---|---|---|
| a failed start check stops the load (no moved import runs) | reviewer, required correction 1 | AM3-1 (b) |
| a case runner's `--pin` runs the start checks and the post-load check before its harness and before writing pins | reviewer, required correction 2 | AM3-1 (c) |
| the `CHECK … INDETERMINATE exit=3` form accepted only for classes N and B, by their pinned class | reviewer, required correction 3 | AM3-4 |
| class B's form was never accepted by the checker in the current freeze: a defect, S11 | builder, found while checking correction 3 | AM3-4, and the issue record's addendum |
| the import-time side-effect limit stated as a limit | reviewer | AM3-1 (d) |

## Summary of decisions
| Decision | What it settles | Recommended |
|---|---|---|
| AM3-1 | S10: when the moved imports' identity is checked, and what a failed check stops | option A: check immediately after the load; nothing loads after a failed start check; case `--pin` guarded too |
| AM3-2 | S9: E point 3, which C.1 makes unmeetable | option A: rewrite point 3, no new output line |
| AM3-3 | E point 17's first half | a reading: the child's `apg` path through the existing child probe |
| AM3-4 | the wrapper `CHECK` rule for an exit-3 `INDETERMINATE` (AM2-2 (d), W-1A.3 (a)), and S11 | accepted only for classes N and B, by the group's pinned class |
| AM3-5 | disclosures | mistakes 24 to 26; the K.1 test's placement |

## AM3-1. The guarded loads and their identity (S10)

**(a) The post-load identity check.**
- **Where it runs:** in `evkit.guarded_load` (the 5 fault runners and the 18 mutation and sabotage successors) and in `cases_main`'s `load=` path (the 10 case runners, and `run_history_contract_s1`'s case mode).
- **The check:** as soon as `load()` returns, the §2.5 import identity check (`evkit.import_identity`) runs again, with the same rules and arguments as `start`'s.
- **When it runs:** before the candidate is loaded, before the inventory comparison or any enumeration, the preflight, the start control, and any case, plant or mutant. For case runners, it runs after the selection is resolved (A.1), which is where the load already runs.
- **If it finds an error,** the run is refused in C.1's form, with the identity check's own codes (`IMPORT_OUTSIDE_EXTRACTION`, `IMPORT_PRELOADED`, `IMPORT_NO_FILE`, or an untrusted module outside the standard library):
  - **fault runners, mutation and sabotage tools:** every pinned item `NOT_RUN cause=run_error`, `preflight=NOT_RUN`, `control_start=NOT_RUN`;
  - **case runners:** the resolved selection of A.1, its cases `NOT_RUN`;
  - then the `RESULT` line, exit 2.
- **The end-of-run check (`IMPORT_END`) is unchanged.**

**(b) A failed start check stops the load** (reviewer's correction 1).
- **Today, in the work in progress:** `guarded_load` calls `load()` even when `start` returned errors. The builder did this so that a start refusal stayed the main's own refusal, naming the run's selection, as in the current freeze. That lets the moved imports run after a failed start check.
- **Decided:** if `start` returns any error, `guarded_load` refuses at once, without calling `load()`, in C.1's form, with the start errors.
- **What this changes, stated:** on the 23 tools that use `guarded_load`, a start refusal no longer names the run's selection, because the selection of a mutation tool cannot be resolved without its M10 module. It now names every pinned item, as an `IMPORT_FAILED` refusal already does. The exit code (2) and every item `NOT_RUN` are unchanged.
- **The tests** whose expected start-refusal output names the selection are changed to this form. Each is listed in the change record.
- **Case runners are already like this:** `cases_main` neither resolves a selection nor loads after a start error.

**(c) A case runner's `--pin`** (reviewer's correction 2).
- **Today (and in the current freeze):** `cases_main --pin` skips `start` altogether, and then runs `load()` and the harness to build the inventory it writes. Before C.1, the harness was imported at module level anyway. So this path predates this pass. Closing it is a widening of C, stated here.
- **Decided:** `--pin` follows this order: the start checks, then the guarded load, then the post-load identity check, then the batch unit or the enumeration, then the pin write.
- **If either check refuses,** no harness runs and no pin is changed. The refusal is `RUN_ERROR` lines and exit 2, as `--pin` refusals are today.
- **Consequence:** pinning now needs a clean start (isolated, from the root, above the disk floor), as every other run does.

**(d) The limit that remains.**
- A module's import-time code still runs when it is imported, as it did before C.1. No check can come before an import.
- The check stops any later work, any item and any pin write from using a harness from elsewhere. It does not undo what that harness's import-time code may already have done.

**(e) Tests.**
- **Decoy tests.** Each runs in a temporary copy whose `load()` puts a decoy directory, holding a full copy of `apg`, first on `sys.path`. The four tools are `run_contracts_s1` (a batch case runner), `run_fin_corpus_s1` (a per-case runner), `run_faults_s1` and `m2_mutants_s1`. Each is refused with `RUN_ERROR IMPORT_OUTSIDE_EXTRACTION apg <decoy path>`:
  - no `CASE`, `PLANT` or `MUTANT` line other than `NOT_RUN`;
  - no control run;
  - exit 2;
  - the output accepted by `check_output` as `EVIDENCE_ERROR`.
- **(b)** A start check made to fail (a working directory other than the root), with a marker written by `load()` in a temporary copy, on one fault runner and one mutation tool. The marker is never written, and the output is C.1's refusal form.
- **(c)** `run_contracts_s1 --pin` with the decoy `load()`. The run is refused, no batch runs (marker), and `expected_counts.json` is byte-identical afterwards. Also, the same `--pin` started from a directory other than the root is refused before the load.
- **The comparisons.** On the unchanged tree these checks find nothing, so B.6, K.2 and E.2 must still be identical. Any difference is a stop-rule event.

**Option B (not recommended): no change,** with the gap recorded as a limitation of C.1.

## AM3-2. E point 3 (S9)
**Option A (recommended; accepted by the reviewer).** Point 3 becomes:

> On a real case runner (`run_contracts_s1`) and a real fault runner (`run_faults_s1`), unchanged:
> - the start lines name no `apg` module (C.1);
> - the post-load identity check of AM3-1 finds nothing (no `RUN_ERROR`);
> - the end line `IMPORT_END apg <this tree>/apg/__init__.py` is asserted literally.
>
> Together with AM3-1's decoy tests, this shows which `apg` the work used, and that one from elsewhere is refused before any item.

**Option B (not recommended):** a new `IMPORT_LOAD <module> <path>` line.

## AM3-3. E point 17, first half (a reading)
- **The point:** "P7-B2: the real `apg` import path asserted".
- **What the P7-B2 run does.** `run_m8_tests_s1 --file test_m8_dependency.py` never imports `apg` in its own process, on either freeze, and prints no `apg` record.
- **The reading.** The child probe of `test_exec_env::ChildrenStartIsolated` records the child's `apg.__file__`. With `APG_ROOT` set to the decoy, the test asserts that path is exactly the tree's `apg/__init__.py`, never the decoy's.
- This is a test design, not evidence. The test was written while waiting (test code only) and passes on Python 3.13. It is evidence only when it runs on the final freeze.

## AM3-4. The wrapper `CHECK` rule for an exit-3 `INDETERMINATE` (reviewer's correction 3, and S11)

**Two rules produce this form:**
- **class N:** AM2-2 (d), an interrupted no-kind child gives `CHECK <g> INDETERMINATE source=child exit=3 marker=<seen|absent>`;
- **class B:** decision W-1A.3 (a), owner, 2026-11-01. `_run_check` gives the same form when a successor `--baseline` exits 3.

**S11, a defect in the current freeze** (`d5f87d6b…`).
- The checker accepted a child `CHECK … INDETERMINATE` only with `exit=-`, so it refused class B's W-1A.3 (a) form.
- No evidence run produced it, because no baseline ever exited 3, and no test passed such an output through the checker.
- **Shown:** the current freeze's real `run_m7_all_s1 --group 15` output, with only its `CHECK` and `RESULT` lines changed to the form `_run_check` writes for a class B exit 3. The frozen checker refuses it: "CHECK G15 outcome INDETERMINATE contradicts exit=3 marker=absent".
- The reviewer's statement that "class B retains its existing form" does not hold. B never had a form the checker accepted.
- The checker change made before stop 3 accepts the form for every class. That is wider than needed, as the reviewer says.

**Decided (option A, recommended).**
- **The checker** accepts `CHECK <g> INDETERMINATE source=child exit=3 marker=<seen|absent>` only when the group's pinned class is N or B.
  - The checker judges the output, together with the pins and selection it is given. It does not read the tree, and the `CHECK` line does not carry the class.
  - So the class comes from the pins argument: a new optional key `classes`, `{group id: class}`, taken from `wrapper_inventories/<tool>/groups`.
  - **Without class pins, the form is refused.** The problem names the missing class, so the rule fails closed.
- **Every caller that checks a wrapper output** passes the wrapper's classes:
  - in the tree: the tests;
  - outside the tree: the builder's `check_wrapper_logs_s1.py` and `check_m8_log_s1.py`.
  - A helper `evkit.wrapper_check_pins(tool)` builds them from the tree's pins.
- **`_run_check`:** the AM2-2 interrupted-child classification applies only to class N groups. Class B keeps its W-1A.3 (a) rule, and every other class keeps today's mapping (exit 3 is `ITEM_ERROR`).
- **Tests:**
  - class N accepts the form;
  - class B accepts it, through a real `run_m7_all_s1 --group 15` in a temporary copy whose baseline is made to exit 3 and is re-pinned there;
  - a class P group with the same line is refused;
  - the form with no class pins is refused;
  - `exit=2`, `exit=3 marker=-` and `exit=0` with `INDETERMINATE` stay refused.

**Option B (not recommended):** the checker reads the classes from the tree's pins itself. That would change the checker from judging the output and its given pins to reading the tree.

## AM3-5. Disclosures
- **Mistake 24.** The builder wrote E point 3 from the mapping's wording without checking it against its own C.1.
- **Mistake 25.** The builder's working log gave clock times after 11:2x on 2026-11-06 that were not read from a clock. One more entry was written the same way after the stop, and corrected to the clock (13:13).
- **Mistake 26.** The builder made `guarded_load` call `load()` after a failed start check (AM3-1 (b)), to keep the frozen refusal form. It did not see that this let the moved imports run after the check had failed. Found by the reviewer.
- **The K.1 real-tool test** plants the leak on the end control's last command, under reading 7. The earlier-command case is its own test.

## Change log
| Decision | The sections it changes |
|---|---|
| AM3-1 | C.1 (the post-load check; no load after a failed start check; a case runner's `--pin`, a stated widening); C.2 (the tests) |
| AM3-2 | E point 3 |
| AM3-3 | E point 17 (how its first half is asserted) |
| AM3-4 | AM2-2 (d) (the checker's acceptance, by class); W-1A.3 (a)'s form made checkable (S11); the checker's pins argument (`classes`) |
| AM3-5 | the documents' list of mistakes |
