# Issue record: corrective pass 2, stop 3 (section C.1 against E point 3, and the moved imports' identity check)

**BUILDER-EXECUTED: NOT INDEPENDENT.** Written by the builder at about 12:00 on 2026-11-06 (AEDT), during the build the owner authorised (paper `23d2adb9…f0ea5`, as amended by amendment 1 `211971…d382` and amendment 2 `a3cc26b5…cd6e`, posted 10:55). It accepts nothing, closes no finding, EDR or CF item, and makes no production-readiness claim.

## Why the work stopped
- **Paper H** names "a requirement that cannot be met within the authorised scope" and "an unlisted behaviour gap". Either one stops the work "before making any further logic change".
- **AM-8:** any further mismatch between the amended paper and the code is a stop-rule event.
- **The builder applied H literally,** as the reviewer confirmed at stop 2. No logic change has been made since S9 was found. (The one checker change in "State of the tree" below was made before this stop. It is set out for confirmation.)

## State of the tree at the stop
- **Branch** `corrective-pass-2`, from `ec42655`, uncommitted: 43 files, +4380 −500 lines.
- **A copy of the diff:** `d14/s1/pass2_work/WIP_at_stop_3.diff`, SHA-256 `faeebfb68195ce93062e7f365494615e0d3330978d9e88b003a937b5598bfed6`.
- **Implemented:**
  - P;
  - A (v=3, the checker, `cases_main`);
  - AM2-1 (the batch unit) and K.2 (the per-case forks);
  - B (the forked plants and controls);
  - C (the 33 guarded loads);
  - F.1, F.2 and K.1;
  - AM2-2 (the 6 supervisors with no `RESULT` line, and their consumers);
  - the tests runners, the wrappers, `pin_test_files`, the CR-02 shim, and the run index's `stdin`.
- **Tests:**
  - **P.10 helper level:** 33, passing.
  - **The v=3 checker tests:** passing.
  - **Tool level, passing on Python 3.13:**
    - `P2MutationFamily` (12);
    - `P2FaultRunners`, `P2CaseRunners`, `P2NoResultSupervisors` and `P2GuardedImports`.
  - **Not yet written:** the E points.
  - **Not yet run:** the full suite on either Python.
- **One checker change since the last report, made before this stop.** The wrapper `CHECK` rule now accepts `INDETERMINATE` with `exit=3` and a marker field of `seen` or `absent`. That is the form AM2-2 (d) defines for an interrupted no-kind child. Before the change, the checker refused it, so the AM2-2 (e) consumer test failed. Every other `INDETERMINATE` with a child exit is still refused, and a test shows it (`exit=2`, `exit=3 marker=-` and `exit=0`). It is listed as AM3-4 for confirmation.
- **The freeze** `d5f87d6b…85c8` is unchanged, and no evidence set has been run.

## S9 (the stop): E point 3 cannot be met once C.1 is applied
- **E point 3** asks for "the start line `IMPORT apg <real path>` asserted on a real runner".
- **What prints that line today.** `evkit.start` prints one `IMPORT <module> <path>` line for each module already imported when it runs. On the current freeze, the 15 runners of C.1 import their harness at module level, before `start`. So their start lines include `IMPORT apg …`. That is the line the mapping's point 3 found printed but never asserted.
- **What C.1 does.** It moves exactly those imports after `evkit.start`'s checks, and C.2 tests that "nothing listed is imported first". So on all 15 runners, the start lines no longer name `apg`. The builder checked this on the tree:
  - `run_contracts_s1`, `run_det_corpus_s1` and `run_faults_s1` on the current freeze: `IMPORT apg …` at start;
  - the same three in the tree: no `apg` line at start, and only `IMPORT_END apg <tree>/apg/__init__.py` at the end.
- **No other real runner prints it,** on either freeze:
  - no `tools/*_s1.py` imports `apg` at module level, and neither does `tools/evkit.py` or `tools/child_unittest_runner.py`;
  - `run_m2_tests_s1` and `run_m8_tests_s1` print only `IMPORT_END` lines for `apg`;
  - the mutation tools print none.
- **So E point 3 and C.1 contradict each other.** E point 3 cannot be met without undoing C.1, or without a new output line, which would be a logic change.

## S10 (found while checking S9): the moved imports' identity is checked only at the end of the run
- **Before C.1:** a trusted module from outside the tree, imported at module level, was found by `start`'s import identity check. The run was refused before any work, with exit 2.
- **After C.1:** the guarded load runs after `start`, so the next identity check is the end-of-run one (§2.5, `IMPORT_END`). A harness that resolves outside the tree is used for every case. The run is refused only at the end.
- **Shown in a temporary copy.** `run_contracts_s1`'s `load()` was made to put a decoy directory, holding a full copy of `apg` with a marker, first on `sys.path`. The result:
  - the decoy's code ran (marker written);
  - all 38 cases ran on the decoy harness and printed `CASE … PASS`;
  - then came 8 `RUN_ERROR IMPORT_OUTSIDE_EXTRACTION apg… <decoy path>` lines;
  - `status=EVIDENCE_ERROR exit=2`.
- **What still holds:** the run is never a pass. The candidate path is still appended after the harness (P3-B04), and `candidate_check` still refuses a trusted name in it. So no ordinary route puts a decoy first on `sys.path`.
- **What is lost:** the guarantee that no item runs on a harness from elsewhere. C.1 says nothing about when the identity of the moved imports is checked, so this is an unlisted behaviour gap under H.
- **The same applies to the 18 mutation and sabotage tools,** whose M10 module now loads after `start`. Their items run in children in copies of the tree, so the parent's harness is not what is tested. The gap is narrower there, but the order is the same.

## Two readings found while preparing this report
Neither is a stop. Both are set out for confirmation.
- **E point 17's first half** ("P7-B2: the real `apg` import path asserted"). On both freezes, the P7-B2 run (`run_m8_tests_s1 --file test_m8_dependency.py`) never imports `apg` in its own process, and prints no `apg` line at all. The child imports `apg` through `tests_m8/_auif.py`. The proposed reading: assert the child's real `apg` path in that test with the child probe that `test_exec_env::ChildrenStartIsolated` already uses, which records each child's `apg.__file__`, with `APG_ROOT` set to the decoy. This is a test only, with no logic change.
- **The K.1 real-tool test needs the leak on the end control's last command.** Reading 7 fixes a multi-command end control's outcome at the end of an earlier command's cleanup. So an interrupt during the cleanup of `m2_mutants_s1`'s first end command (`run_m2_tests_s1`) correctly gives `CONTROL end CONTROL_NOT_RUN cause=interrupted`, not K.1's `FAIL`. The K.1 test now plants the leak on the last command (`run_contracts_s1`), and gives `CONTROL_FAIL cause=processes_left` with `SIGNAL_AFTER_COMPLETION`. The first-command case is kept as its own test of reading 7. No code was changed for this.

## Disclosures
- **Mistake 24.** The builder wrote E point 3 into the paper from the mapping's wording without checking it against the builder's own C.1. Both the paper's drafts and the reviewer's reviews missed the conflict.
- **Mistake 25.** The builder's working log (`PASS2_BUILD_LOG.md`) gave clock times after 11:2x that were not read from a clock, and were wrong ("12:1x" to "15:xx"; the real time at this stop is about 12:00). They are order labels only, and the log now says so. From now on, the times in the records are read from the clock.
- **Test-code fixes since the last report (no logic change):**
  - the temporary trees reused a name across subtests (`p2b_copy` now clears it first);
  - the case inventory ids are read from `['ids']`;
  - two m2 tests pass `--jobs 1`, where exactly one item must be in flight;
  - `CA01` is a documented equivalent, so the regex also accepts `EQUIVALENT`.

## What the builder proposes
`d14/decisions/APG_D14_STAGE1_CORRECTIVE_PASS_2_AMENDMENT_3_DRAFT_v1.md`.

## While waiting
- No logic change is made.
- The builder goes on writing the E-point tests that S9 and S10 do not touch: points 1, 4, 7, 8, 9, 12, 15, 20, 22, 25 and 26, and 17 under the reading above. That is test code only. It does not change the tree's logic, and every test is rerun after amendment 3.
