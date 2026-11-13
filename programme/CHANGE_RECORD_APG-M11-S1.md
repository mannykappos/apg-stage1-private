# Change record: APG-M11-S1, successor stage 1 (the evidence tooling)

**BUILDER-EXECUTED: NOT INDEPENDENT.** Final for the frozen stage 1 tree. The evidence produced on the frozen tree (the run index, the
fail-on-M10 and pass-on-stage-1 results, the route proof, the frozen-file comparison and the historical checks) is in the stage 1
documents file, not here, because it is produced after the freeze. It accepts nothing, closes no finding, EDR or CF item, and makes
no production-readiness claim.

## Authority
- Build authorisation, product owner, 2026-10-31 11:20: `APG_D14_STAGE1_BUILD_AUTHORISATION_DRAFT.md`, SHA-256
  `9af3151fb6e034b2e9d6504b04e6066d5b0733ae89cf0e852a600e9682148197`.
- Amendment 1 (14 Workstream T rows, 89 rows) and amendment 2 (`tests_m8/test_m8_boundary.py`), with decisions K-1, R12 (a) and F-55,
  product owner, 2026-10-31 13:18. The documents are `APG_D14_STAGE1_AUTHORISATION_AMENDMENT_1_DRAFT.md` (`9e76ee37…357f`),
  `APG_D14_STAGE1_AUTHORISATION_AMENDMENT_2_DRAFT.md` (`b67192d9…c853`) and `APG_D14_STAGE1_DECISIONS_K1_R12_F55.md` (`660525fc…8082`).
- The decisions D-1 to D-9, adopted 2026-10-31 11:04 (`e8757f6e…beaa`).
- Decisions M8-T (a), E-1 (i), M-1 (a) and W-1 (W-1.1 and W-1.2 (a)), product owner, 2026-10-31 20:57: `APG_D14_STAGE1_DECISIONS_W1_M8T_E1_M1.md` (`a8574459…be91`) and `APG_D14_STAGE1_DECISION_W1_REV2.md` draft 2 (`21728a94…0951`).
- Decision W-1A, correcting W-1 for the true inventory of 657 wrapper groups, product owner, 2026-11-01 06:22: `APG_D14_STAGE1_DECISION_W1A_CORRECTION.md` draft 2 (`396e268f…488d`), `wrapper_groups_v2.csv` (`0fe5b28b…899a`) and `W1_EXCLUSION_LIST_v2.csv` (`e2f80c22…cfd3`). Its §0A supersedes every inventory figure in the earlier W-1 documents.
- Decision W-1B option (a), correcting W-1A for the three built-in coverage checks that fail on clean M10, product owner, 2026-11-01 11:32: `APG_D14_STAGE1_DECISION_W1B_BUILT_IN_CHECKS.md` draft 2 (`f45619e3…b773`), `wrapper_groups_v3.csv` (`f559ec57…b7c9`) and `W1_EXCLUSION_LIST_v3.csv` (`266eea0d…e479`), which replace the v2 files.

## The changes those decisions call for (pins in `tools/expected_counts.json`, each with a change record)
- **M8-T:** `tools/m8_mutants_s1.py` tier 1 is M10's `TIER1` without `test_m8_boundary`, and tier 2 is unchanged. The tiers are pinned as the tool's oracle (pins v55). The tool also restores `sys.path` after the AUIF check; before that fix it could not have reached its controls.
- **M-1:** `runner_profiles/run_m8_tests_s1@sabotage_tool` = `full`, recorded with a change record citing M-1 (v56). A test shows that a full run goes on after a failing test.
- **W-1, kind=wrapper:** the `CHECK` and `EXCLUDED` records, `OK_WITH_EXCLUSIONS` (exit 0), the checker, the §1.8 hashing and the §1.9 consumer rule. `run_child` refuses a `kind=wrapper` child, and `wrapper_verdict` is the one reader.
- **The 19 successor wrappers, `tools/run_*_all_s1.py`:** each reads M10's own group table and runs every group in M10's order.
  - Over all 19 wrappers there are 454 `FILE`, 103 `CHECK` and 100 `EXCLUDED` groups (W-1B).
  - Their pins are `wrapper_inventories`, `check_lists` and `exclusion_lists` (v57 to v75; v76 to v78 for `run_f671_all_s1`, `run_f672_all_s1` and `run_f673_all_s1` under W-1B). They were written only after checking them against the adopted inventory and exclusion list, whose SHA-256 values are fixed in `tools/evkit.py`.
- **W-1B (a):** a built-in check that fails on clean M10 and is listed individually in the adopted exclusion list is class H: `EXCLUDED`, with `command_sha256` the empty-string SHA-256, never evaluated, and never a pass. G10 of `run_f671_all`, `run_f672_all` and `run_f673_all` are such checks; `run_f674_all` G10 stays a W `CHECK` and runs. `--pin` accepts only the v3 files; re-pinning all 19 wrappers changed only those three.
- **W-1A.2 (ii) (a):** `run_regression_m8_s1` R01, R02 and R10, and `run_regression_m81_s1` R01 and R02, also permit exactly what the frozen stage 1 manifest declares, only at each file's exact recorded hash. The manifest is validated by amendment 2's validator, whose file hash is checked first.
- **W-1A.3 (a):** the nine successor mutation tools take `--baseline`. It runs only the start control and prints `BASELINE OK` only on a pass; its exit codes are 0, 1, 3 and 2.
- **W-1A.4 (a):** `run_m8_all_s1` runs its 117 per-file groups directly through `tools/run_test_files_s1.py`, mapped one to one from M10's `PER_FILE`.
- **Found while writing the plan's tool-level tests (2026-11-01; `rec/ISSUE_RECORD_2026-11-01_STAGE1_MISSING_TOOL_LEVEL_TESTS.md`):**
  - `tools/evkit.run_child`: a stage 1 test runner's child whose `mode=` differs from the mode pinned for its runner and caller (`runner_profiles`) is `CHILD_EVIDENCE_ERROR` (T-0 (R5), DP-2.3 F10; authorisation §4.6): `ITEM_ERROR` in a mutation or sabotage tool, a failed control in a control.
  - `tools/evkit._run_file_group`: a wrapper S group whose child ends through its own exit 0, 1 or 2 with its `RESULT` line missing is `ITEM_ERROR` (T-0 (R4) `expect_line`, adopted for S groups by W-1 §1.2 (a); P4-B17 (R4)); a child that dies with no structured result (a signal, any other exit) stays `INDETERMINATE` (§2.7).
  - Every run a successor refuses before any work ends with its `RUN_ERROR` line and one `RESULT v=2` line, every item `NOT_RUN cause=run_error`, exit 2 (§2.7; P7-B3 (R4)): `--batch` in `m8_mutants_s1` and in the eight mutation tools `f67`, `f671` to `f674`, `m73_store`, `mie`, `mie11`; `--timeout` in `sabotage_m8_s1`; and the tool-definition errors (duplicate ids, the MIE catalogue, M8-T's tier check, an unverified AUIF dependency), through `evkit.refuse_run`. The eight changed mutation tools are the B groups' tools in eight wrappers, whose pinned check identities were rewritten (pins v79 to v86).
  - The tool-level tests of every block's "Tests that prove it" list, in the 10 `tests_tools` files.
- **The corrective evidence work after the stage 1 gate review (2026-11-02):**
  - Authority: owner decisions at 12:51 and 14:24 (`rec/DECISION_RECORD_2026-11-02_STAGE1_CORRECTIVE_D2_D8.md` and `rec/DECISION_RECORD_2026-11-02_STAGE1_A_C_E_F_G.md`).
  - Findings: `rec/ISSUE_RECORD_2026-11-02_STAGE1_CORRECTIVE_TEST_FINDINGS.md`.
  - **(c)** `tools/evkit.list_mutants`, used by the 14 AST successor mutation tools (`m3` to `m7`, `m73_store`, `m91`, `f67`, `f671` to `f674`, `mie`, `mie11`): a failure of the tool's own listing of its mutants is a refusal, not a crash. The listing fails when a target file is missing or a region marker is gone. The tool prints `RUN_ERROR MUTANT_LIST_INVALID`, every pinned mutant `NOT_RUN cause=run_error`, one `RESULT v=2` line, and exits 2. The mutants themselves are unchanged.
  - **(f)** `tools/evkit.tests_runner_main` and `tools/child_unittest_runner.py`: a child given `APG_AUIF_ROOT` verifies that copy with AUIF's own loader (`apg_auif.dependency.ensure`) before any test. A copy that cannot be verified is `RUN_ERROR ENV_AUIF_ROOT_UNVERIFIED`, every file `NOT_RUN`, exit 2.
  - **(a′)** `tools/evkit.check_output`, for `kind=cases`: given the tool's pinned case inventories, the checker verifies `case_inventory_sha256` (owner, 15:33). It must be the hash of the selected suites' pinned inventories, in their order, for a choice of `suites_selected` pinned suites that contains the suites the `CASE` records name, in their printed order. A mismatch, or a `CASE` suite that is not pinned, is a problem. Without the pins this field cannot be verified, and that limitation is stated. The first rule approved, (a) at 14:24, hashed the printed `CASE` records. It was wrong for partial `--only` runs, because it confused the pinned inventory with the executed subset. It was reverted before anything depended on it, and (a′) replaces it.
  - **Pins v87 to v97 (the numbering of freeze c9b324eb, before the workspace loss of 2026-11-11; this rebuilt tree's own pin versions are listed under "Pin history of the rebuilt tree" below):** the `check_lists` entries of `run_m7_all_s1`, `run_m71_all_s1`, `run_m72_all_s1`, `run_m73_all_s1` (two), `run_f67_all_s1`, `run_f671_all_s1` to `run_f674_all_s1`, `run_mie1_all_s1` and `run_mie1_1_all_s1`. These name the changed tool files' hashes; each re-pin has a change record. No other pin changed. The other eight wrappers were re-pinned too and came out unchanged.
  - Owner-accepted deviations, with no code change:
    - D2, f672's short-timeout rerun removed;
    - D8, `CASE_INVENTORY_MISMATCH` for an empty corpus;
    - (e), runners record but do not compare the interpreter's identity (R1 §2.8 not fully met by automated runner enforcement);
    - D12 (g), an invalid selection lists every pinned item `NOT_RUN` instead of `selected=0`, and prints no `SELECTION INVALID:` or `ERROR <id>` human line.
  - The tests added are listed in the stage 1 documents' mapping.
- **Corrective pass 2 (2026-11-05 to 2026-11-06):**
  - **Authority:**
    - the paper `d14/decisions/APG_D14_STAGE1_CORRECTIVE_PASS_2_DECISION_PAPER.md` (`23d2adb9…f0ea5`, authorised by the owner at 10:56 on 2026-11-05, as amendment 1 §0 gives it; amendment 5, row 113);
    - amendment 1 (`211971452c8f…d382`) and the build of the pass, authorised by the owner at 23:00 on 2026-11-05 (the build authorisation);
    - amendment 2 (`a3cc26b5…cd6e`, owner, 10:55 on 2026-11-06);
    - amendment 3 (`89e5a268…6715`, owner, 14:38 on 2026-11-06).
    - The decision record `rec/DECISION_RECORD_2026-11-05_STAGE1_CORRECTIVE_PASS_2.md` lists the stops and the issue records.
  - **The process model P (`tools/evkit.py`, the P section):**
    - every supervisor is a child subreaper;
    - children are identified by pid and start time, and signalled through pidfds;
    - one register and `Popen` hook record every child;
    - every child is a unit: `run_unit` for a subprocess, `run_forked` for a forked unit with one length-prefixed message (at most 1 MiB; status 70 is `child_error`);
    - orphans are reaped and attributed;
    - one cleanup contract (P.5) applies to every terminal path, with `CLEANUP`, `CLEANUP_SUMMARY`, `CLEANUP_AMBIGUOUS` and `RUN_ERROR CLEANUP_INCOMPLETE` records;
    - a run that cannot be supervised is refused with `ENV_NO_PROCESS_SUPERVISION`.
  - **The time constants, and where each applies:**
    - `T_EXIT_AFTER_RESULT` = 2 s: the exit and drain after a unit's result;
    - `T_GRACE` = 10 s: the SIGTERM grace in ordinary cleanup;
    - `T_GRACE_CANCELLED` = 2 s: the grace when the supervisor is itself cancelled;
    - `T_ESCALATE` = 10 s: for a unit whose child is a nested supervisor;
    - `T_KILL_VERIFY` = 5 s: after SIGKILL;
    - `FAULT_ITEM_TIMEOUT_S` = 300 s: per plant and per control of the five fault runners (B.2);
    - `CASE_ITEM_TIMEOUT_S` = 300 s: per case, or per batch unit (K.2, AM2-1).
    - Every supervising run prints a `LIMIT` line with the limits in force.
  - **The result schema (A.2, K.3):**
    - `kind=cases`, `kind=mutation` and `kind=sabotage` now write `v=3`; `tests` and `wrapper` stay `v=2`.
    - The checker reads `v=2` under the frozen rules (and (a′) for cases), and `v=3` under the new rules; a `v=2` line is never read as `v=3`.
    - `kind=cases v=3` adds `suites=` (sorted, or `-`). Its `case_inventory_sha256` is over the sorted suites, with each suite's cases in pinned order (amendment 2, reading 11).
  - **The amended `control_end` rule (K.1),** for `kind=mutation` and `kind=sabotage`: `control_end=NOT_RUN` if and only if `control_start` is not `PASS`, the run was stopped before its last item, or it was stopped after its last item and before the end control's outcome was fixed. The last case needs its stop record (`RUN_ERROR ENV_DISK_BELOW_FLOOR control_end …` or `INTERRUPTED … at=control_end`) and only `CONTROL end CONTROL_NOT_RUN` with the matching cause.
  - **The new codes and lines:**
    - `RUN_ERROR IMPORT_FAILED`;
    - `RUN_ERROR ENV_NO_PROCESS_SUPERVISION`;
    - `RUN_ERROR ENV_THREADS_AT_FORK` (AM-6 (a); added to this list by amendment 5, row 113);
    - `RUN_ERROR CLEANUP_INCOMPLETE`;
    - `RUN_ERROR PROCESSES_LEFT run_start|run_end`;
    - `RUN_ERROR ENV_DISK_BELOW_FLOOR items|control_start|control_end`;
    - `INTERRUPTED signal=… at=… received=…`;
    - `SIGNAL_AFTER_COMPLETION`;
    - `CLEANUP`, `CLEANUP_SUMMARY` and `CLEANUP_AMBIGUOUS`;
    - `LIMIT`;
    - `CONTROL … CONTROL_NOT_RUN` and `CONTROL_INTERRUPTED`;
    - the child outcome `CHILD_INTERRUPTED` and the cause `child_interrupted` (AM2-2);
    - the causes `interrupted`, `run_stopped`, `processes_left`, `timeout`, `crash`, `bad_result` and `child_error`.
  - **What changed in each family:**
    - **The 10 case runners and `run_history_contract_s1`:**
      - A.1's order and selection;
      - each case is a forked unit (K.2), and the 7 batch runners' harness call is one forked unit (AM2-1);
      - their module-level harness imports are guarded loads (C.1).
    - **The 5 fault runners:** each plant and control is a forked unit (B), and their imports are guarded loads.
    - **The 18 mutation and sabotage successors:** their M10 loads are guarded loads (C.1), and they have F.1 (the disk floor during a run), F.2 (interrupts) and K.1.
    - **The tests runners, the wrappers and `pin_test_files`:** on P, with F.2.
    - **The 5 regression successors and `run_cr02_reference_s1`:** on P, with the interrupted form of AM2-2: the `INTERRUPTED` record as the last line, exit 3.
  - **Amendment 3:**
    - **AM3-1:** the import identity check runs again immediately after every guarded load, before any item. The load never runs after a failed start check. A case runner's `--pin` runs the start checks and that check before its harness, and writes no pin after a refusal.
    - **AM3-4:** the wrapper checker accepts a child `CHECK … INDETERMINATE exit=3` only for a group whose pinned class is N (AM2-2 (d)) or B (W-1A.3 (a)). The class is given with the pins (`evkit.wrapper_check_pins`). This also corrects S11: the checker of freeze `d5f87d6b…` refused class B's W-1A.3 (a) form.
  - **Comments corrected:**
    - mistake 17: `_check_case_inventory`'s docstring no longer says "in their order", because `sha256_lines` sorts its lines;
    - mistake 18: `tests_tools/test_runner_zero_work.py`'s stale "decision pending, (g)" comment.
    - The (a′) item above keeps its original wording as historical; this item corrects it.
  - **Pins v98 to v109 (c9b324eb's numbering):** the `check_lists` entries of the B and N groups whose tool file changed, 13 entries in 12 wrappers:
    - `run_f67_all_s1`, `run_f671_all_s1` to `run_f674_all_s1` (G09);
    - `run_m3_all_s1` (G08, `run_cr02_reference_s1`);
    - `run_m7_all_s1` (G15), `run_m71_all_s1` (G16), `run_m72_all_s1` (G18) and `run_m73_all_s1` (G23, G24);
    - `run_mie1_all_s1` and `run_mie1_1_all_s1` (G08).
  - **Pins v110 (c9b324eb's numbering):** the `test_files` entries of the 10 `tests_tools` files, which hold the new tests. New test files are not allowed by the manifest contract, so the tests went into the existing files.
    - These ten entries had not been updated since they were first pinned. In freeze `d5f87d6b…` they named stale hashes and listed 158 test ids, while the files held 508 tests (mistake 27).
    - Nothing in the evidence reads them: the T set runs each file directly. A runner given those files would refuse on the mismatch.
  - **Pins v111 (c9b324eb's numbering):** `tests_tools/test_no_timeout_kill.py`, for the mistake 29 test.
  - **Mistake 29, a race in the builder's P code, found by the full suite.**
    - `evkit._Supervision.scan` read the process table before it pruned the reaped registrations.
    - A direct child reaped by its own handle in between was taken for an adopted orphan. Its status was still collected correctly, but P.4 requires that the reaper never sees an unregistered direct child.
    - The pruning now comes first.
    - `test_the_registration_race_child_exits_immediately` failed once in a full run, and 4 times in 40 repeated runs. A deterministic test with the window widened (`test_the_registration_race_with_the_window_widened`) adopted 20 of 20 children before the fix and 0 of 20 after.
  - **The tests that AM3-1 (b) changed** (a start refusal now names every pinned item, not the selection):
    - `tests_tools/test_exec_env.py::RunnerLevelStartChecks::test_free_disk_below_the_floor_stops_a_runner_and_a_mutation_tool_before_any_work`;
    - `tests_tools/test_apg_root.py::E4DecoyWorkingDirectory::test_successor_runners_refuse_a_working_directory_other_than_the_root` (new in this pass).
  - Each pin version has its change record in `tools/expected_counts.json`.
  - The tests added are listed in the stage 1 documents' mapping.

- **Amendment 5 (owner, 11:26 on 2026-11-08; `3649fa74…dc295b`) and the rulings of 12:47 on 2026-11-08:**
  - **Rebuilt after the workspace loss of 2026-11-11 (recovery authorisation, owner, 15:48 on 2026-11-11).** The code of this item
    was lost with the workspace before any freeze containing it was sent. It was rewritten from the amendment and the rulings, not
    recovered, and its bytes differ from the lost freeze `303b6414…`. The records of the owner's 11:26 post and 12:47 rulings are
    reconstructed from the builder's notes, not verbatim.
  - **S15 (option A), `tools/evkit._Supervision`:** an orphan found with no recorded parent is attributed, as before, to every unit
    in flight (or the current owner); each of those owners now records it as a leak (P.6), and its `CLEANUP` record names it in
    `left=`, even when it has exited before that owner's cleanup. The signal steps run only when a member is alive.
  - **S16 (option A), `tools/evkit._check_wrapper`:** a `CHECK … INDETERMINATE` line of a group whose `CLEANUP` record is in the output
    is accepted when its source is the child, or when its exit and marker are both `-` (a leak makes a check INDETERMINATE whatever its
    exit, P.6). Without the record the AM3-4 rules apply unchanged.
  - **S17 (a) (option A):** no code change; the row 41 tests assert `CRASH_NO_RESULT` and `CHILD_EVIDENCE_ERROR`.
  - **S17 (b) (option A), `tools/evkit.cases_main` step 3:** a candidate factory spec must be exactly `module:attr` (a dotted module name,
    one colon, one attribute name, `evkit.FACTORY_SPEC`); anything else is `RUN_ERROR SELECTION_INVALID <option> must be module:attr`.
  - **AM5-4 option A, the tests of Appendix A part 1** (and the option A corrections of 2026-11-09), in the existing `tests_tools`
    files; no product or successor-tool logic changed by them. The row-by-row list is in the stage 1 documents' mapping.
    - `test_no_timeout_kill.py`: the P rows (4, 6, 11, 12 with S15, 15, 19, 21, 23, 71, 72, 77, 90, 91, 92, 96, 99, 101) and row 121's
      per-test identity record (`P_IDENTITY`).
    - `test_mutation_timeout.py`: rows 4 (tool level), 41, 50, 51 to 53, discrepancies 10 and 14, and row 121.
    - `test_runner_zero_work.py`: rows 22, 25, 30, 31, 36, 42, 46, 51 to 53, 55, 56, 59, 60, 66, 69, 73, 79, 81, 83, 85, 95, 97, 98,
      100, S16 and row 121. `P2FaultRunners` takes the runner's name (`TOOL`) so its full set runs on the other four fault runners.
    - `test_consumer_exit_codes.py`: rows 34, 57, 62 and 63.
    - `test_exec_env.py`: rows 22 and 29.
  - **Mistakes 23, 29 and 34, as ruled in AM5-5:** mistake 23 (C.1's table incomplete; the eight moves ratified as an application of
    its general rule, the failure to stop recorded); mistake 29 (the scan race, fixed before the stop and decision H requires: the fix
    retained, the process recorded as non-compliant); mistake 34 (that logic change made before the stop).
  - **Pins:** the `test_files` entries of the changed `tests_tools` files; each version has its change record in
    `tools/expected_counts.json`.
  - **Pin history of the rebuilt tree** (fix 6, discrepancy D6-2 of the step 6 re-mapping: the pin numbers above are c9b324eb's):
    - v87 to v98 (2026-11-11): the recovery's re-pins of the `check_lists` entries listed above under c9b324eb's v87 to v109;
    - v99: the `tests_tools` files, byte-identical to freeze c9b324eb;
    - v100 and v101 (step 3): the rewritten amendment 5 tests (700 tests; v101 the row 55 held group);
    - v102 (row 68, owner 2026-11-12 "Add limits, then refreeze"): a time limit on the ten helper process starts in two
      `tests_tools` files (`test_consumer_exit_codes.py`, `test_no_timeout_kill.py`), tests only, ids and counts unchanged;
    - v103 (fix 6): below.
- **Fix 6 (owner, 2026-11-13 18:34, "Fix them, then re-run"), after the step 6 re-mapping (37 closed, 28 partly addressed):**
  tests only, in the existing `tests_tools` files; no product or successor-tool logic changed.
  - `test_no_timeout_kill.py` (`AM6Supervision`): row 11 with real processes (an equal-start-time grandchild, ambiguous, adopted and
    reaped after its parent ends); row 21 (the records in the units' id order, the builder reading "id order is creation order"
    stated in the test, against completion order and name order); row 91 (no other member signalled while the nested supervisor
    lives); row 99 (a phase with children counted once); row 12's older test now asserts each unit's leak (S15).
  - `test_mutation_timeout.py` (`AM6MutationToolGaps`, `AM6LeafInterrupts`): rows 4 (the /proc, pidfd_open, prctl set and read-back
    refusals at tool level), 12 (an orphan at `--jobs 2`: each item in flight INDETERMINATE processes_left), 21 (gone when the RESULT
    line arrives), 22 (a mutant's leak), 41 (a mutation tool's control crash and rejected output), 51 to 53 and 66 (the three leaves,
    SIGINT and SIGTERM); row 121's identity record from `P2MutationFamily`, with each process group noted while it lived (D6-7).
  - `test_runner_zero_work.py` (`AM6AttributionAndSignals`, `AM6FindingThirteenProbes`, `AM6RunEndAndCounts`): rows 21, 30 (an
    unkillable forked case), 46 (the case hash for every case runner; the item count never skipped), 52 and 53 (run_contracts_s1
    SIGTERM and during the batch's cleanup; sabotage_m7_s1 and run_faults_s1 between items; run_faults_s1 during the end control's
    cleanup), 71 (m8_mutants_s1's own AUIF children at its start), 73 and D6-3 (run_start and run_end on m8_mutants_s1 and
    run_m8_tests_s1; R03's "(INCOMPLETE: processes left)"), 75 (probes of finding 13 classes 2 to 6, recorded as `P_PROBE` lines in
    the test log), 85 (stderr and the rewritten command), 96 and 99 at tool level; row 121's identity record from `P2FaultRunners`,
    `P2CaseRunners` and `P2NoResultSupervisors`, process groups noted while they lived (D6-7).
  - `test_exec_env.py`: row 29's first chain (m3_mutants_s1 -> run_m2_tests_s1 -> test -> process -> child, normal and interrupt
    paths) and the interrupt path's CLEANUP attribution in the second chain; D17: `test_m8_mutants_controls_and_a_known_kill`
    renamed `test_m8_mutants_control_is_killed_at_tier_1_and_ml01_never_runs`, so its name says what it asserts.

## What changed
`programme/APG-M11-S1_MANIFEST.csv` holds the exact list:
- the 89 D1 lines;
- the one supplementary line;
- this record;
- every file whose hash differs from M10.

The base is APG-M10 (`bd5c592a198581808237e5a5e563aa15c3be977d3f3e0d68511499d755435192`), which is unchanged.
