# INDEPENDENT READ-ONLY MAPPING (agent), corrective pass 2

**What this is.** An independent read-only mapping of APG D14 stage 1, corrective pass 2. It covers freeze `APG-M11-S1.zip`, SHA-256 `c9b324ebd236b6ad1b5c6207e6d1ea3db584ef0861db636d9f94fb8137459297` (commit `6f65d488`). It maps the requirements to the tests and evidence and classifies each one. It makes no acceptance or production-readiness statement.

## 0. Method and limits

**Inputs checked**
- **Freeze:** the hash matches, and the second build (`pass2_work/freeze_build2.zip`) has the same hash. I extracted it fresh into `/tmp/mapagent_x/`. It is identical to every `evidence_pass2/<set>/x/APG-M11-S1` and to the working tree, apart from `__pycache__`.
- **M10 archive:** `bd5c592a…5192` matches.
- **Authority files:** the paper `23d2adb9…`, AM1 `211971…`, AM2 `a3cc26b5…`, AM3 `89e5a268…` and AM4 `b6be070e…`. The AM4 hash is the one named in the owner's 17:31 post.
  - The AM3 and AM4 files still carry their "draft" headers. Their hashes equal the posted texts.

**What I wrote.** I wrote one small read-only AST inventory script and its output to `/tmp/mapagent_scripts/` (`inv.py`, `inv.txt`). That is outside "extract only". I disclose it here. Nothing under the base directory was changed.

**Read-only commands used:** ls, grep, sha256sum, AST reads with `python3 -I -S`, `ps`, `date` and `git log --no-optional-locks`.

**How "passes on both Pythons" is judged.**
- The T logs are not verbose: they hold dots, ResourceWarnings and `Ran N tests … OK`.
- So a named test counts as passing when its file ran `OK` on both py313_T and py312_T, with no skips, no failures and no early-return guards. I found none of those in `tests_tools`.
- All 10 files are OK on both Pythons: 51+86+39+16+12+66+4+180+34+125 = 613 tests each.
- Tests generated at run time (for example `ToolLevelTimeoutCrashKill.test_timeout_<tool>`) are counted the same way.

**Something running while I read.** An S14 diagnostic process was running (`python3.13 -I …/pass2_work/s14_diag/diag.py`, started about 02:44). `evidence_pass2/diagnostic_s14/` may change after I read it.

## 1. Requirement table

C = CLOSED BY EVIDENCE · P = PARTLY ADDRESSED · O = STILL OPEN. Test files are in `tests_tools/`; evidence paths are under `d14/s1/evidence_pass2/`.

| # | Section | Requirement (short) | Class | Test / evidence | Note |
|---|---|---|---|---|---|
| 1 | P.1, AM-2, AM-6(c) | Unit set; 71 supervisors and 3 leaves | C | `test_consumer_exit_codes.py::Pass2ProcStat::test_supervisor_list` | Checks the count and the set of stems against the files on disk; does not check each tool's category |
| 2 | P.2 | Subreaper set through prctl and read back | C | `test_no_timeout_kill.py::P2SubprocessUnits::test_the_supervisor_is_a_subreaper_and_supervision_is_available`; `P2NestedAndRefusals::test_refusals_when_containment_cannot_be_set_up` (read-back case) | |
| 3 | P.2 | Each unit's direct child in its own process group | C | `P2SubprocessUnits::test_what_a_unit_child_inherits`; `P2ForkedUnits::test_what_a_forked_child_inherits` | pgid = pid, both kinds |
| 4 | P.2, P.10 | Refusal `ENV_NO_PROCESS_SUPERVISION`, exit 2, every item NOT_RUN, when prctl, read-back, /proc, pidfd_open, pidfd_send_signal or SIGCHLD fail | P | `P2NestedAndRefusals::test_refusals_when_containment_cannot_be_set_up`, `::test_sigchld_ignored_is_set_back_or_refused` | Only the `supervision_errors()` text after importing evkit in a copy. No supervisor tool is shown refusing with exit 2 and items NOT_RUN. /proc and pidfd_send_signal not covered |
| 5 | P.2, AM-4, P.10 | Child gets fds 0–2 (+ result pipe), the allowlist env, fd 0 on /dev/null; a parent's extra fd and env var not inherited; both kinds | C | `P2SubprocessUnits::test_what_a_unit_child_inherits`; `P2ForkedUnits::test_what_a_forked_child_inherits` | |
| 6 | P.2 | No secret in the allowlist; a secret in a unit's env stops the work; values never recorded | P | `audit_final/outside_services.txt` (`subprocess_unit` and `forked_unit_after_scrub`: `secret_bearing_names: []`) | Auditor started with the builder's full environment (231 names). `forked_unit_before_scrub` lists 17 secret-bearing names, values withheld. See D-list 7 and 22 |
| 7 | P.2, P.9, AM-1(4) | Audit items 1–6 with the basis for each conclusion, rerun on the new freeze | P | `audit_final/outside_services.txt`, `process_api_reach.txt`; `audit/outside_services_conclusions.txt` (earlier freeze) | No conclusions file for this freeze. `process_api_reach` lacks the PID 1 line and the process list. The audit's units are not started through `run_unit`/`run_forked` |
| 8 | P.2, AM-1 | No outside service can start a process outside a unit's tree | O | AM-1, open finding 11 | Reachable: PID 1 API, the harness socket, the telemetry socket, `/etc/cron.d` (writable). Egress unknown |
| 9 | P.3, P.10 | `/proc/<pid>/stat` fields counted after the last `)` | C | `Pass2ProcStat::test_command_name_with_spaces_and_parentheses` | |
| 10 | P.3, P.10 | A reused pid is never signalled; a reused parent pid's child is not a member | C | `P2Identity::test_a_reused_pid_is_never_signalled`, `::test_a_reused_parent_pid_with_a_child_of_its_own_is_not_a_member` | Simulated, as the paper allows |
| 11 | P.3, P.10 | Equal start times: not membership; recorded (`ambiguous=` or `CLEANUP_AMBIGUOUS`); cleaned up once adopted | P | `P2Identity::test_equal_start_times_are_ambiguous_and_recorded` | Only an internal dict (`o.ambiguous`). No output line asserted; adoption and cleanup not exercised |
| 12 | P.3, P.10 | Orphan created between scans attributed to every unit in flight, each a leak; `--jobs 2`; an unrelated process survives | P | `P2SubprocessUnits::test_concurrent_orphan_attribution_and_an_unrelated_process_survives` | Asserts `ua.leaked or ub.leaked` (the paper says each unit). Two threads calling `run_unit`, not `--jobs 2`. Classifications not asserted |
| 13 | P.4, P.10 | One wait owner per child; no status lost or taken twice; adopted zombie reaped | C | `P2SubprocessUnits::test_wait_ownership_two_concurrent_units_and_an_adopted_zombie` | |
| 14 | P.4, P.10 | Register lock held across creation; a child that exits at once is never taken for an adopted orphan | C | `::test_the_registration_race_child_exits_immediately`, `::test_the_registration_race_with_the_window_widened` | Mistake 29 fixed in this pass |
| 15 | P.4 | No wait on −1 or a process group; every wait WNOHANG | P | No test. My static read of `tools/evkit.py` (waitpid at :1308, :1495, :1874, all WNOHANG on a single pid) | Code read only |
| 16 | P.2, P.4, P.10 | SIGCHLD set to SIG_DFL and read back, otherwise refused | C | `P2NestedAndRefusals::test_sigchld_ignored_is_set_back_or_refused` | Asserts the internal token `sigchld_not_default` |
| 17 | P.5, B.2, K.2 | The five constants and two item limits; a `LIMIT` line from each supervisor | C | `Pass2ProcStat::test_limit_line`; LIMIT lines in py313/py312 W and M logs; `compare_py31x/b6_logs` and `k2_logs` (`item=300s` on all 16 runs); `m2_logs/m2_mutants_s1.txt` | |
| 18 | P.5, P.10 | SIGTERM, grace, SIGKILL, kill-verify; a member ignoring SIGTERM is killed and recorded | C | `::test_a_member_that_ignores_sigterm_is_killed`; `P2ForkedUnits::test_valid_result_then_hangs_ignoring_sigterm_is_killed` | |
| 19 | P.5, P.10 | A unit that forks repeatedly during cleanup, with the scan count and deadline recorded | O | none | |
| 20 | P.5 step 7, P.10 | Unkillable member: `CLEANUP_INCOMPLETE`, exit 2, no waiting | C | `::test_a_member_that_cannot_be_killed_is_cleanup_incomplete` | Helper level; exit 2 through `finish_items` |
| 21 | P.5 steps 8–9 | Full `CLEANUP` form and scan ids; `CLEANUP_SUMMARY` before RESULT, ordered by unit id; RESULT only after all cleanup | P | Field and prefix asserts in the P2 tests; `CLEANUP_SUMMARY … leaked=0` in W, M and m2 logs | The full field set appears only in the excluded `interrupted/` set. Tools are shown clean after the supervisor exits, not at its RESULT line. Order untested |
| 22 | P.6 | Leak gives item `INDETERMINATE cause=processes_left`, control `FAIL processes_left`; cause on the CLEANUP line where the item line has none | P | `test_runner_zero_work.py::P2FaultRunners::test_plants`, `::test_controls`; `P2CaseRunners` (batch, fin); `test_mutation_timeout.py::P2MutationFamily::test_f2_and_k1_during_the_end_controls_cleanup` | Not shown: a mutation item leak at tool level, a tests-kind FILE leak, a wrapper FILE or CHECK leak |
| 23 | P.7, P.10 | Nested supervisor: SIGTERM, `T_ESCALATE`, kill, partial output ignored; nested INDETERMINATE never a pass | P | `P2NestedAndRefusals::test_nested_supervisor_cancelled_by_its_parent_finishes_and_a_hung_one_is_killed_at_t_escalate`, `::test_a_nested_indeterminate_result_is_not_a_pass` | A stub script named `run_faults_s1.py`, not a real nested supervisor. Orphan adoption after escalation not shown |
| 24 | P.8 steps 1–4, AM-6(b) | Framing, 1 MiB limit, UTF-8/JSON, form; crash vs bad_result vs child_error | C | `Pass2ForkedMessage::test_validation_steps`; `P2ForkedUnits::test_message_forms_and_classification`, `::test_framing_limit` | |
| 25 | P.8 step 5, reading 12 | A failed id must be in the paired case runner's inventory; tests on 5 pairs | O | none | |
| 26 | P.8 | Interrupt after the outcome is fixed gives `SIGNAL_AFTER_COMPLETION`; an earlier unit keeps its outcome | C | `P2MutationFamily::test_f2_and_k1_…`, `::test_f2_during_the_end_control`; `P2NoResultSupervisors::test_between_steps_and_after_the_last_step` | |
| 27 | P.9 | Inventory of start sites and paths before implementing; stop if not containable | C | `audit/child_start_sites.txt`, `independent_inventory.md`, `paper_to_code_matrix.md`; P9 stop issue record; `audit_final/child_start_scan.txt` (2 sites) | |
| 28 | P.9 | A timeout stays INDETERMINATE | C | `test_mutation_timeout.py::ToolLevelTimeoutCrashKill.test_timeout_<tool>` (15 tools), `ToolLevelM8::test_timeout_m8`, `TimeoutStaysIndeterminate` | |
| 29 | P.10, AM-2 | Nested two levels: tool, leaf, test, process, child (hang; setsid + double fork; leftover after a pass), on timeout, interrupt and normal path; second chain through `run_m8_tests_s1`; CLEANUP attribution | P | `P2SubprocessUnits::test_hang_timeout_and_setsid_double_fork_are_contained`, `::test_normal_path_background_grandchild_after_a_passing_result_is_a_leak` | One level only, in the test process. No tool-level nesting, no interrupt path, no `run_m8_tests_s1` chain |
| 30 | P.10 | Own `…_valid_result_then_hangs` tests for a forked plant and a forked case; SIGTERM-ignoring and unkillable variants | P | `P2ForkedUnits::test_valid_result_then_hangs` (helper), `::…_ignoring_sigterm_is_killed`; subtests `plant:valid_then_hang`, `batch:valid_then_hang` | No own tool-level tests, no per-case (K.2) variant, no unkillable variant. The helper test does not assert `processes_left` or "no RESULT while alive" |
| 31 | A.1 | Order of a case run; refusals at steps 1–3 give no resolved selection; steps 4–8 keep it | P | `P2CaseRunners::test_a4_the_v3_contract_on_the_real_runners` (steps 1, 2, 3 and 4) | Keeping the selection at steps 5, 6 and 8 is not asserted |
| 32 | A.1 | `SELECTION_INVALID` for any unpinned suite or case; the mixed form replaced | C | `test_a4` subtests (`--suite nope`, `--only NOPE-99`, mixed, `--bogus`) | |
| 33 | A.1–A.3 | `suites=` rules; empty-selection hash; v=3 without `suites` rejected; v=2 reader kept | C | `Pass2CasesV3` (6 tests); `test_a4` | |
| 34 | A.3 | Each checker rejection | P | `Pass2CasesV3::test_rejected_forms`, `::test_no_resolved_selection` | `suites=-` with a non-zero `selected` is not tested |
| 35 | A.4 | Real-runner runs: full, single suite, more pinned than printed, `--suite record_store --suite audit_log --only AL-01` | C | `test_a4` | |
| 36 | A.4 | Each case runner's import failure keeps its selection, with `suites` and hash asserted | P | `P2GuardedImports::test_c2_the_15_runners` | `suites` and `selected` asserted, hash not; `run_history_contract_s1` case mode not run |
| 37 | A.4, I.3 | 2C demonstration rerun: only the true selection accepted | C | `static/case_inventory_limit.txt` | One Python |
| 38 | B.1 | Plants and controls forked; message forms; child_error fallback; status 70 | C | `P2FaultRunners::test_plants` (`child_error`, `status70`, `raise`); `P2ForkedUnits::test_message_forms_and_classification` (unencodable) | |
| 39 | B.2 | `FAULT_ITEM_TIMEOUT_S=300`; `LIMIT item=300s` on every fault run; recorded | C | `test_limit_line`; `b6_logs/*_new.txt` on both Pythons; change record | |
| 40 | B.3 | Plant outcome table | C | `P2FaultRunners::test_plants`, `::test_f2_sigterm_while_a_plant_runs` | `run_faults_s1` only |
| 41 | B.4 | Control outcomes and causes, `CONTROL_INTERRUPTED`, `CONTROL_NOT_RUN`, checker validation; the same for mutation and sabotage controls | P | `P2FaultRunners::test_controls`; `SabotageAndFaultRunners` (`reference_failed_<n>`); `Pass2ControlsV3`; `ToolLevelTimeoutCrashKill.test_failed_start_control_*` | Crash and `bad_result` causes for mutation and sabotage controls not tested |
| 42 | B.5 | All tests on each of the five runners; test evidence records pids, pgids and CLEANUP lines | P | `P2FaultRunners` (full on `run_faults_s1`); `::test_the_hang_on_each_of_the_other_four_runners` | The other four get the hang only, and that test accepts a start-control timeout in place of the plant's. No pid, pgid or CLEANUP record appears in any evidence log |
| 43 | B.6 | 111 verdicts, CONTROL values and causes, status and exit equal to d5f87d6b | C | `compare_py313/b6.txt`, `compare_py312/b6.txt` (SAME); `b6_logs` | The tool does not compare CONTROL causes. I compared them in the logs: equal on all 10 runs |
| 44 | C.1 | The 33 loads moved; P3-B04 order; nothing imported before the guard | C | `static/route_scan.txt`; `P2Amendment3::test_am3_2_e_point_3`; `P2GuardedImports` | |
| 45 | C.1 | `IMPORT_FAILED` refusal form for each family | C | `P2GuardedImports::test_c2_the_15_runners`, `::test_c2_the_18_mutation_and_sabotage_successors` | |
| 46 | C.2 | Per-runner assertions | P | same | Not asserted per runner: nothing listed imported first, `cause=run_error`, the case hash; history case mode |
| 47 | C.3 | Three wrapper consumer paths give ITEM_ERROR, exit 2 | C | `P2GuardedImports::test_c3_the_wrapper_consumer_paths` | |
| 48 | AM2-4 r17 | Residual of finding 9 (11 tools) stated in the documents | O | — | Documents not yet produced |
| 49 | D | 36 plants stay refused; finding 2 stays open | O | By the paper. The refusal is shown by older tests (`EveryTextListOnTheSource`, `PreflightFailClosedAtToolLevel`) | |
| 50 | F.1 | Disk floor during the items (`--jobs 2`), at the start control and at the end control; phase word; checker | P | `P2MutationFamily::test_f1_*` (m2, all three), `::test_sabotage_m7_f1_*` (start, end) | `sabotage_m7_s1` lacks the during-items `--jobs 2` case; `NOT_RUN cause=run_stopped` for unstarted items not exercised |
| 51 | F.2(a) | One mechanism in every work loop | P | `P2MutationFamily`, `P2FaultRunners`, `P2CaseRunners`, `P2NoResultSupervisors` | Untested: `tests_runner_main`, `run_m2_tests_s1`, `mut_runner_s1`, `run_test_files_s1`, `run_m8_tests_s1`, `child_unittest_runner`, `wrapper_main` |
| 52 | F.2 tests | SIGINT and, separately, SIGTERM on m2, sabotage_m7, run_faults, run_m2_tests, run_contracts and run_m4_all | P | same | `run_m2_tests_s1` and `run_m4_all_s1` untested; `run_contracts_s1` SIGINT only |
| 53 | F.2 tests | Points: during a child, between items, during the end control and during its cleanup | P | m2: all four; sabotage_m7: during a child only; run_faults: during a child and during the end control | |
| 54 | F.2 | Interrupted form; `INTERRUPTED` immediately before RESULT; no RUN_ERROR; second signal counted | C | `P2MutationFamily::test_f2_sigint_while_a_child_runs`, `::test_f2_a_second_signal_is_counted_without_cutting_the_output`; `Pass2ControlsV3::test_interrupted_placement_and_counts` | Second-signal case on m2 only |
| 55 | F.2(b) | Interrupted wrapper: group INDETERMINATE, the rest NOT_RUN, RESULT exit 3 | O | none | The excluded `interrupted/py312_W_container_restart` W07 shows this form; it is not evidence |
| 56 | AM2-4 r16 | Wrapper interrupted before an H group still prints EXCLUDED (run_m4_all_s1) | O | none | |
| 57 | K.1 | Checker: each permitted and each rejected form | P | `Pass2ControlsV3::test_not_run_with_no_stop_record_is_rejected`, `::test_stopped_after_the_last_item`, `::test_stopped_before_the_last_item` | Missing rejected forms: a completed `CONTROL end` beside NOT_RUN; a completed end control reported as NOT_RUN |
| 58 | K.1 | Real tool: valid end result, leftover process, interrupt in cleanup gives `FAIL processes_left` with `SIGNAL_AFTER_COMPLETION` | C | `P2MutationFamily::test_f2_and_k1_during_the_end_controls_cleanup`; `::test_reading_7_…` | The end-control commands are stubs |
| 59 | K.2 | Per-case forked unit (4 corpus runners); message forms and mapping | P | `P2CaseRunners::test_k2_per_case_on_run_fin_corpus_s1` | Shown: hang, crash, status 70, exception→FAIL, leak, interrupt. Missing on the per-case path: descendant hang, incomplete, malformed, `ok=false`, child_error by message (and "would otherwise fail"), kill while writing, wrong keys or types, malformed text that looks like `ok=false`, valid-then-hang |
| 60 | K.2, AM2-1(f) | Hang on every other case runner, with identities gone and `check_output` | P | `::test_the_hang_on_the_other_six_batch_runners`, `::test_k2_the_hang_on_the_other_three_corpus_runners` | `run_history_contract_s1`: no `check_output`, no gone check. `run_mkt_corpus_s1`: no `check_output` |
| 61 | K.2 | 386 verdicts and causes, status and exit equal to d5f87d6b | C | `compare_py313/k2.txt`, `compare_py312/k2.txt` (SAME, 386) | |
| 62 | K.3 | v=3 for mutation and sabotage; dispatch by kind and version; v=2 kept; tests and wrapper stay v=2 | P | `Pass2CasesV3::test_tests_and_wrapper_stay_v2`, `::test_the_v2_reader_…`; `Pass2ControlsV3::test_v2_mutation_line_keeps_the_frozen_rule` | Cross-kind v=3 dispatch not tested |
| 63 | K.3 | Tests and wrapper outputs through the checker twice, with and without the new records | O | none | |
| 64 | K.3 | Consumers read through `check_output`; the builder's log checkers updated and say so | P | W `wrapper_check.txt`, M `m8_check.txt` (no checker problems, both Pythons) | `check_wrapper_logs_s1.py` says so; `check_m8_log_s1.py` does not |
| 65 | AM-1 | Finding 11, the narrowed claim, the risk basis and the explicit statement, in the documents | O | — | Documents pending. The risk basis is supported by `audit_final/child_start_scan.txt` section E |
| 66 | AM-2 | F.2 in leaves and `child_unittest_runner` (between tests); `run_m8_tests_s1` | O | none | |
| 67 | AM-2 | Finding 12 | O | By the amendment | |
| 68 | AM-2 | T-set leaves bounded by each test's own limit | P | `audit/tset_leaf_deadlines.txt` | Measured on the earlier freeze; not re-measured for this pass's new tests |
| 69 | AM-3 | CR-02 shim under P; cleanup on SystemExit; tests: leak recorded, sys.exit path, output unchanged | P | `P2NoResultSupervisors::test_cr02_sigterm_during_its_first_child`; W02 `CHECK G08` | No leak test. SystemExit cleanup shown only on the interrupt path. G08's exit and marker hash match across freezes by my own cross-check, not a builder record |
| 70 | AM-4 | stdin /dev/null for both kinds; the run index too | C | Row 5 tests; `d14/s1/tools/run_index_s1.py:64` | |
| 71 | AM-5(a) | Hook at import; registration atomic; one wait owner; leaf reaps exited orphans before RESULT | P | `P2NestedAndRefusals::test_the_hook_registers_children_created_by_in_process_code_and_a_phase_owns_them`; the race tests | Not shown: `run_child` plus the hook registering once only; `m8_mutants_s1`'s pre-start AUIF children registered; the leaf's pre-RESULT reap |
| 72 | AM-5(b) | Immutable code's children keep their command, env and limit | P | Indirect: the T, W and M runs pass | No test or probe asserts what these children receive |
| 73 | AM-5(c) | Attribution table rows (`PROCESSES_LEFT run_start` / `run_end`, `(INCOMPLETE: processes left)`, …) | O | Generic phase leak at helper level only | No row is tested at tool level |
| 74 | AM-5(d) | Finding 13 | O | By the amendment | |
| 75 | AM-5(e) | Documents and docstring corrected; a probe per class recorded in `evidence/audit/` | P | `tools/evkit.py` docstring around :4151 | P1-F6 documents row pending; no per-class probe in `audit_final` |
| 76 | AM-6(a) | Single-thread check before fork; `ENV_THREADS_AT_FORK` | C | `P2ForkedUnits::test_forking_needs_a_single_thread` | The `/proc/self/task` branch is not exercised on its own |
| 77 | AM-6(b) | Drain tests: a grandchild holds the write end and adds one byte (bad_result + leak); holds it and stays silent (processes_left) | O | none | The `trailing` subtests write from the direct child |
| 78 | AM-7, AM2-3, AM3-5, AM4 | Mistakes 20–31 and findings 11–13 disclosed in the documents | P | Change record (17, 18, 27, 29); issue records and build log | Pass-2 documents not yet produced |
| 79 | AM2-1(a) | Batch unit only after steps 1–5; 300 s; full call whatever the selection; `--pin` uses it | P | `test_am2_1_the_batch_unit` (`drop_pinned` with `--only`); `P2Amendment3::test_am3_1_c_…` | Not shown: no batch run after an ordinary start refusal; `--pin` using the unit |
| 80 | AM2-1(b)(c) | Message form, unique pairs, 1 MiB; inventory compared before selection; `ok` mapping | C | `test_am2_1` (`wrong_type`, `duplicate`, `too_big`, `false_row`, `drop_pinned`, `none:x`); `P2ForkedUnits::test_framing_limit` | Exact 1 MiB / 1 MiB + 1 only at helper level |
| 81 | AM2-1(d) | Precedence rows 1–7 | P | `test_am2_1` subtests | Not tested: row 7's inventory mismatch winning over the leak; row 3 with a leak |
| 82 | AM2-1(g) | `_CACHE` removed; re-pinned | C | Static: no `_CACHE` in `tools/*_s1.py`; `static/frozen_compare.txt` problems 0 | |
| 83 | AM2-2(a) | Record as the last line, exit 3, P lines before M10's final line; `SIGNAL_AFTER_COMPLETION` before it with M10's exit unchanged | P | `P2NoResultSupervisors` (`interrupted()`); `::test_between_steps_and_after_the_last_step` | Placement of `SIGNAL_AFTER_COMPLETION` and the unchanged exit not asserted (only "not 3") |
| 84 | AM2-2(b) | Steps, the watcher for R03, R06 and R04, the bound | C | `::test_a_child_step_interrupted_by_sigint`, `::test_r03_…`, `::test_r06_…`, `::test_r04_…`, `::test_between_steps_…` | |
| 85 | AM2-2(c) | CR-02 synthetic `CompletedProcess` fields; cleanup on SystemExit | P | `::test_cr02_sigterm_during_its_first_child` | Fields not asserted |
| 86 | AM2-2(d)(e) | Consumers: class N CHECK, sabotage_m8 plant and both controls, redirected successor | C | `::test_consumer_*` (3); `Pass2InterruptedNoKindChild` | The signal is self-sent through an evkit edit |
| 87 | AM2-3 | B.1 sentence struck; mistake 22 | C | Stop 2 issue record (S8) | Documents pending |
| 88 | r1 | ITEM_ERROR kept when a leak is also found | C | `test_am2_1` `batch:child_error_leak` | |
| 89 | r2 | Timeout, interrupt and run_stopped keep their cause | C | `plant:spawn_hang`, `batch:spawn_hang`; `test_f1_…_with_jobs_2` | |
| 90 | r3 | Subprocess pipe drain bounded | P | `::test_normal_path_background_grandchild_…` | The bound is not asserted |
| 91 | r4 | SIGTERM to the nested supervisor alone | P | Row 23 test | The stub has no other members |
| 92 | r5 | Grace ends early after two empty scans | O | none | |
| 93 | r6 | Phase recorded | C | `Pass2ControlsV3`; `at=` asserts in P2 tool tests | |
| 94 | r7 | Multi-command end control | C | `::test_reading_7_an_interrupt_during_an_earlier_commands_cleanup` | |
| 95 | r8 | Start control interrupted before it began | P | `Pass2ControlsV3::test_start_control_interrupted` | Checker level only |
| 96 | r9 | Unowned child attributed to run_end; test in a copy | O | none | |
| 97 | r10 | Argument errors are step 3 refusals | P | `test_a4` `--bogus` | Missing value, `--path`/factory mismatch and malformed spec not asserted for `suites=-` |
| 98 | r11 | Canonical hash; a test runs both orders | P | `Pass2CasesV3::test_the_hash_is_canonical_…`; 2C file | Helper only; no real runner in both orders; CASE order not asserted |
| 99 | r13 | `CLEANUP_SUMMARY units=` counting | O | none | For example `units=219` in m2s is not reconciled anywhere |
| 100 | r14 | `child_unittest_runner` declares itself just before `verify_auif` | P | `test_supervisor_list` | The declaration point and its check not tested |
| 101 | r15 | Subreaper proof; zombie check by the tool itself; ChildProcessError | P | Row 2 and row 13 tests | No zombie check by the tool itself; leaf reap untested |
| 102 | AM3-1(a) | Post-load identity check before any item | C | `P2Amendment3::test_am3_1_a_a_decoy_harness_is_refused_before_any_item` | |
| 103 | AM3-1(b) | No load after a failed start check; changed tests listed | C | `::test_am3_1_b_no_load_after_a_failed_start_check`; change record | |
| 104 | AM3-1(c) | `--pin` guarded | C | `::test_am3_1_c_a_case_runners_pin_is_guarded` | |
| 105 | AM3-1(d) | The import-time limit | C | The row 102 test asserts the decoy marker was written | |
| 106 | AM3-1(e) | B.6, K.2 and E.2 still identical | P | b6, k2, golden, pairs SAME on both Pythons | E.2 m2 DIFFERENT 2 on py313 (S14); not run on py312 |
| 107 | AM3-2 | E point 3 rewritten | C | `P2Amendment3::test_am3_2_e_point_3` | |
| 108 | AM3-3 | E point 17, first half | C | `test_apg_root.py::ApgRootRedirect::test_e17_the_p7_b2_run_imports_the_real_apg_in_its_child` | |
| 109 | AM3-4 | Exit-3 INDETERMINATE accepted for classes N and B only; refused otherwise | C | `::test_am3_4_class_b_a_real_baseline_that_exits_3`, `::test_am3_4_class_n_…`; `P2NoResultSupervisors::test_consumer_a_wrappers_class_n_check` | |
| 110 | AM4-1, E.2, I.3 | m2 comparison (M10 `run_one` harness, fixed values, allowances only) on both Pythons | O | `compare_py313/m2.txt`: fixed values hold; `RESULT m2 DIFFERENT 2`. Nothing for py312 | S14 open; the S13 slicing reading awaits the owner; the tool's allowance is wider (D-list 15) |
| 111 | AM4-1 | Literal output of one run of M10's `m2_mutants.py` | O | `m2_logs/m10_script_list.txt` (`--list` only) | S13 open |
| 112 | H | Stop rule applied | P | Issue records S6–S14 | Mistakes 23 and 29 handled without a stop record; the S14 diagnostic is unrecorded (D-list 11) |
| 113 | I.1 | Commit, re-pins, manifest, change record contents, mistakes 17 and 18 | P | Commit `6f65d488`; `programme/CHANGE_RECORD_APG-M11-S1.md`; `tools/evkit.py:774`; no "decision pending" text remains | `ENV_THREADS_AT_FORK` missing from the codes list; one combined record for three version changes |
| 114 | I.2 | Suite passes on 3.13 and 3.12; freeze built twice with identical bytes | C | py313_T, py312_T (613 OK each); `freeze_build2.zip` = `c9b324eb…` | |
| 115 | I.3 | Six run sets | C | `py31x_{T,W,M}/run_index.csv`, `tree_after.txt` (0 changes), `wrapper_check.txt`, `m8_check.txt` | |
| 116 | I.3, E.2 | Golden: 6 runners identical, both Pythons | C | `compare_py31x/golden.txt` SAME | |
| 117 | I.3, E.2 | 15 pairs, case by case, both Pythons | C | `compare_py31x/pairs.txt` SAME | |
| 118 | I.3 | Historical checks, both Pythons | C | `historical_py31x/summary.json` (100/100, archive unchanged) | |
| 119 | I.3 | Frozen-file comparison; both route proofs | C | `static/frozen_compare.txt` (problems 0), `route_children.txt`, `route_scan.txt` | |
| 120 | I.3 | Check of the cited test names | O | none for this freeze | |
| 121 | I.3 | Pids, start times, pgids and the cleaning supervisor recorded for the P, B, K.2 and F.2 tests | O | The T logs hold none | |
| 122 | I.3 | Evidence index (README) linking `evidence/audit/` and the identity and CLEANUP records | O | `d14/s1/README_PACKAGE.md` describes d5f87d6b | |
| 123 | I.3 | Run index describes `last_line` as a prefix of at most 300 characters | P | `run_index_s1.py:67` truncates at 300 | The docstring says "the last line" |
| 124 | I.4 | Separate-agent mapping | P | This document | Not yet reviewed |
| 125 | I.5 | One ZIP plus one documents file; d5f87d6b kept | P | `freeze/superseded_d5f87d6b/` kept | Package and documents not produced |
| 126 | I.6 | No change after the freeze | C | `tree_after` 0 for all six sets; fresh extraction equals the evidence extractions | |
| 127 | G | Findings 1–10 stay open; D2, D8, D12 and (e) unchanged | O | By the paper | |

## 2. E points

| Point | Class | Test / evidence | Note |
|---|---|---|---|
| 1 | C | `test_mutation_timeout.py::E1KillOracleNamesAMissingTestFile` (2 tests) | M10's kill line asserted literally |
| 2 | O | See E.2 | |
| 3 | C | `P2Amendment3::test_am3_2_e_point_3` | As rewritten by AM3-2 |
| 4 | C | `test_apg_root.py::E4DecoyWorkingDirectory` (2 tests) | Recorded as found: M10 imports its own apg |
| 5 | O | — | Not in E's table; (e) is owner-accepted |
| 6 | C | `P2MutationFamily::test_f1_*` (m2) | F.1 as a whole is partial (row 50) |
| 7 | C | `test_exec_env.py::E7ChildIsolationM10Halves` (4 tests) | See D-list 17 for one test's name |
| 8 | C | `ToolLevelTimeoutCrashKill` (15 tools, timeout and crash, M10's literal text); `ToolLevelM8::test_timeout_m8`, `::test_crash_m8` | |
| 9 (D13) | C | `ToolLevelTimeoutCrashKill.test_timeout_<tool>` (15) | |
| 10 | O | — | D2, owner-accepted; outside this pass |
| 11 | O | — | P1-M1, outside this tree |
| 12 | C | `E12M3NonMatchingPattern` (2 tests) | |
| 13 | O | — | D8, owner-accepted |
| 14 | O | — | D12, owner-accepted. The stale comment is corrected (mistake 18) |
| 15 | C | See E.15 | |
| 16 | O | — | D6, stated deviation; not addressed |
| 17 | C | `test_e17_the_p7_b2_run_imports_the_real_apg_in_its_child`; `E26RealFailFast::test_e17_ml01_kill_attribution_matches_m10` | |
| 18 | O | — | D15, accepted on the reviewer's terms (G) |
| 19 | O | — | D3, stated deviation |
| 20 | C | `MutRunnerOutput::test_e20_the_c8_kill_attribution_matches_m10` | |
| 21 | O | — | D14, accepted on the reviewer's terms (G) |
| 22 | P | `MutRunnerOutput::test_e22_…`; `E26RealFailFast` `f11()` with `check_output` | The standalone run is not passed through the checker |
| 23 | O | — | D: finding 2 stays open |
| 24 | P | Rows 38–43 | B.5 is incomplete on four runners |
| 25 | C | `SelectorsThatDoNoWorkExitTwo` (m7 and m8: `--group 0`, `--range 5-3`); `E25StubbedChildGroups`; `WrappersW1B` (f672 G11); `WrappersW1A` (f674 G10); E.15 refusals | |
| 26 | P | `E26RealFailFast` F1, F7, F8 | F8 shows only a stop inside one file (the builder's reading, not confirmed); "files after the failure" is not shown for F8 |
| **E.2** | O | Golden and pairs SAME on both Pythons. m2: py313 DIFFERENT 2 (CA01, RI13), py312 not run. Literal run not made | The paper itself keeps point 2 partly open; S13 and S14 are open |
| **E.15** | C | `test_harness_isolation.py::E15FakeHarnessAndTrustedNames` (3 tests) | 8 runners × 9 names × package and module; factory spec; all through `check_output` |

## 3. Discrepancies

**Claims I cannot find evidence for**
1. **B.5 and I.3: child pids, pgids and CLEANUP lines.** The paper says the test evidence records each child's process and group ids, its CLEANUP lines, and which supervisor cleaned up each unit. No T log carries any of this.
2. **I.3: the check of the cited test names.** There is no record for c9b324eb.
3. **I.3: the evidence index.** No README links `evidence/audit/` or the identity and CLEANUP records. `README_PACKAGE.md` is the d5f87d6b one.
4. **Change record: "the tests added are listed in the stage 1 documents' mapping".** No pass-2 documents exist yet.
5. **AM-5(e): "a probe in each path, recorded in `evidence/audit/`".** There is no such probe output.
6. **AM-2's "all 26 process starts set a time limit".** This was measured on the earlier freeze only.
7. **The audit tool's docstring.** It says the tool runs with "env PATH TMPDIR LANG LC_ALL TZ only", and that it starts its child "exactly as run_child starts a unit today (subprocess.run…)".
   - The `audit_final` record shows 231 auditor environment names.
   - On this freeze, `run_child` goes through `run_unit` (Popen hook, stdin DEVNULL), and the tool's fork scrub is its own code, not `run_forked`.
   - So `audit_final`'s fd 0 = /dev/null comes from how the auditor was started, not from the AM-4 code. The 11-05 conclusions file says the same.
8. **Builder readings presented as within the authority but not confirmed by the owner:**
   - the S13 five-slice harness;
   - the F8 "within-file stop";
   - mistake 23 (C.1's tables were incomplete; moved under the general rule with no AM-8 stop);
   - mistake 29 (fixed with no stop record).
9. **Reading 17's "the documents will say this is not fixed".** Documents pending.
10. **E.2's "these numbers and hashes are in the test".** They are in the builder's out-of-tree tool (`compare_pass2_s1.py:26-28`), not in any `tests_tools` file.
11. **An unrecorded S14 diagnostic.** `evidence_pass2/diagnostic_s14/` exists, and an S14 diagnostic was running at about 02:44–02:51 on 2026-11-08 (1 worker, `run_one` on the EQUIV ids). Neither the build log nor the S14 record mentions it. It applies S14 option B, which departs from AM4-1's 4 workers, before the owner has decided. First result: CA01 SURVIVED in 203.6 s.

**Tests weaker than their names or than the paper**

12. **"Shown gone before the RESULT line"** (P.10, K.2, F.2). The tool-level helpers (`p2b_gone`, `p2_gone`) check after the supervisor exits, not at its RESULT line.
13. **Several P tests assert less than their names or the paper:**
    - `test_equal_start_times_are_ambiguous_and_recorded`: "recorded" means only an internal dict.
    - `test_concurrent_orphan_attribution_…`: asserts `or` where the paper requires each unit.
    - `test_refusals_when_containment_cannot_be_set_up`: no tool-level refusal form.
    - `test_valid_result_then_hangs` (helper): no classification asserted.
    - `test_the_hook_registers_…`: registration only.
14. **Runner-level gaps:**
    - `test_the_hang_on_each_of_the_other_four_runners`: passes on a start-control timeout, so the plant's own hang may never be exercised.
    - The hang tests for history and mkt lack `check_output`; history also lacks the gone check.
    - `test_the_hash_is_canonical_…`: helper only.
    - `test_tests_and_wrapper_stay_v2`: checks write versions only; K.3's twice-through-checker test is absent.
    - `test_hang_timeout_and_setsid_double_fork_are_contained`: one level, not P.10's nesting.
    - `too_big` is about 16 bytes over 1 MiB, not exactly 1 MiB + 1.

**Evidence that contradicts a claim, or tools that differ from the authority**

15. **The m2 compare tool allows more than AM4-1.** It accepts any M10 KILLED (even "by tests") against a successor INDETERMINATE (`compare_pass2_s1.py:416`). AM4-1 allows that only for an M10 kill by timeout or crash. No id used the allowance.
16. **The b6 compare tool does not compare the CONTROL causes** B.6 requires. The logs agree.
17. **`E7ChildIsolationM10Halves::test_m8_mutants_controls_and_a_known_kill`** asserts only that M10's control fails. No kill is asserted.
18. **Build log, 02:15–02:43: audits "(same as 11-05)". This is contradicted:**
    - the auditor's environment differs (231 names against 5);
    - `process_api_reach` lacks the PID 1 and process listing;
    - there is no conclusions file.
19. **E.2 m2: `DIFFERENT 2`, outside AM4-1's allowances** (S14, open). For 83 of M10's 197 kills, which were by timeout, the comparison shows only that both sides end KILLED.
20. **Change record:**
    - `ENV_THREADS_AT_FORK` is absent from the new codes;
    - it dates the paper's authorisation to 23:00 on 2026-11-05, while AM-1 §0 says 10:56. The 23:00 was the build authorisation.
21. **Other builder tools:**
    - `run_index_s1.py`'s docstring says "the last line", not "a prefix of at most 300 characters";
    - `check_m8_log_s1.py` does not say it was updated for v=3.
22. **Privacy, not a P.2 breach.** `audit_final/outside_services.txt` records the values of non-secret identifiers from the builder's session: the user e-mail variable, the account and organisation UUID variables, the container id and the remote-session URL variable. P.2 allows this wording-wise. The owner may want them reviewed before the package is distributed.

## 4. Summary

| | CLOSED BY EVIDENCE | PARTLY ADDRESSED | STILL OPEN | Total |
|---|---|---|---|---|
| Requirement table (section 1) | 55 | 49 | 23 | 127 |
| E points 1–26 (section 2) | 12 | 3 | 11 | 26 |
| E.2 / E.15 | E.15 | — | E.2 | 2 |

- **What depends on the owner:** rows 106, 110 and 111, E point 2 and E.2 are open or partial because they wait on S13 and S14.
- **The largest groups of gaps:**
  - P.10's nested and cleanup edge tests;
  - the K.2 per-case message forms;
  - F.2 for the tests runners and wrappers;
  - the AM-5(c) attribution rows;
  - the AM-6(b) drain tests;
  - readings 5, 9, 12, 13 and 16;
  - K.3's twice-through-checker test;
  - I.3's identity records, names check and evidence index.