# INDEPENDENT READ-ONLY RE-MAPPING (agent), recovery step 6, freeze ee1ce3ec

INDEPENDENT READ-ONLY (agent). This is a mapping of requirements to tests and evidence. It is not a stage 1 acceptance statement, and it says nothing about production readiness. Written 2026-11-13 AEDT (Australia/Melbourne, from `date`): first clock read 18:14:00, report written 18:29:41.

## 0. Method and limits

**Inputs and their hashes, as I checked them**
- `FREEZE`: SHA-256 `ee1ce3ec4be1a76482595688cfd9b41910fa26f4c9fe9a936f8971e86b5e0735`. This matches the expected hash and both entries in `SCR/recovery/freeze5/two_builds_sha256.txt` (a and b).
  - I extracted it fresh into `SCR/remap6/x/`: 1555 files.
  - `diff -rq` against `EV5/run_sets/py313_T/x` and `EV5/run_sets/py312_T/x` found no difference.
- `M10`: SHA-256 `bd5c592a198581808237e5a5e563aa15c3be977d3f3e0d68511499d755435192`. It matches.
- Authority files in `REPO/authority/`:
  - paper `23d2adb9…f0ea5`;
  - AM1 `211971…d382`, AM2 `a3cc26b5…cd6e`, AM3 `89e5a268…6715`, AM4 `b6be070e…a7d6`;
  - AM5 draft v4 `3649fa74…c295b`.
  - All of these match the hashes in amendment 5 §0 and in the recovery authorisation.
- The T sets:
  - `EV5/run_sets/py313_T` and `py312_T`: 10 files, every exit 0, 700 tests on each Python (51+91+42+16+12+66+4+200+52+166);
  - each log ends `OK`, with 0 lines matching `skip` and 0 `FAIL:`/`ERROR:` lines;
  - `tree_after` shows 0 changes, and the zip hash recorded in it is `ee1ce3ec…`.
- **How "ran OK on both Pythons" is judged.** The T logs are not verbose. A named test counts as passing when its file ran OK on both Pythons.
  - I found no `skipTest` and no early-return guards in the AM5 tests I read.
  - Tests generated at run time are counted the same way: `AM5SabotageControls.test_row41_*` and the inherited `AM5FaultRunner{M3,M5,M6,History}`.

**What I ran** (all read-only on the inputs):
- `sha256sum`, `ls`, `diff -rq`, `grep`, `sed -n`, `head`/`tail`, `date`;
- `unzip -q` of the freeze into `SCR/remap6/x/`;
- `git --no-optional-locks log/status` on `REPO`;
- short inline `python3 -I -S` reads of JSON (`tools/expected_counts.json`, `EV5/audit_final/outside_services.txt`).

I ran no test file and no long job.

**What I wrote** (only under `SCR/remap6/`):
- `scripts/inv.py`, an AST inventory of the test methods in `tests_tools`;
- its outputs, `scripts/inv.txt` (426 static test methods) and `scripts/ident_tests_313.txt` (the test ids carrying `P_IDENTITY` records in the py313 T logs);
- the extraction `x/`;
- this report.

**What I could not check:**
- **The 303b6414 re-mapping v4.** Its item list is lost, so it can be compared only on counts.
- **The owner's 12:47 plan corrections for rows 6 and 17.** Their text is lost. The surviving record (`RECONSTRUCTED_OWNER_RULINGS_…`) says only "as the builder proposed". So I cannot verify the builder's reading of row 6.
- **The reconstructed owner posts** of 2026-11-08 11:26 and 12:47. These are the builder's reconstructions, not verbatim; I took them as given.
- **Whether a test asserts its full intent at run time.** I judged that by reading the code, not by running the tests.

## 1. Table

Classes: C = closed by evidence, P = partly addressed, O = still open. Test paths are `FREEZE:tests_tools/…`. "1st" is the class in the first mapping (`c9b324eb`); "disc." means it was listed there as a discrepancy, not a row. File:line is the test's `def` line.

| # | Requirement (short) | Now | Test / evidence | What is missing (P/O) | 1st |
|---|---|---|---|---|---|
| 4 | P.2/P.10 refusal `ENV_NO_PROCESS_SUPERVISION`, exit 2, every item NOT_RUN, for each failing step incl. /proc and pidfd_send_signal | P | `test_mutation_timeout.py:1360,1367,1374` (`AM5ToolLevelRefusals`: libc, pidfd_send_signal, SIGCHLD, at tool level with exit 2 and every item NOT_RUN); `test_no_timeout_kill.py:699` (/proc, pidfd_send_signal, pidfd_open, prctl set, copy-import level only) | At tool level, /proc, pidfd_open, prctl-set and prctl-read-back failures are not shown with exit 2 and items NOT_RUN. They are shown only as the `supervision_errors()` text in an import copy | P |
| 6 | P.2: no secret in the allowlist; a secret in a unit's env stops the work; value never recorded | P | `test_no_timeout_kill.py:711` (a planted token in the parent never reaches a `run_unit` or `run_forked` child, and its value is in no output); `EV5/audit_final/outside_services.txt` (`secret_bearing_names: []` for both units) | The plan asks for a tool-level test where "the work stops". The test is helper level and shows non-inheritance only. The owner's plan correction for row 6 is lost, so the builder's reworded target ("never reaches a unit or a record") cannot be checked against it | P |
| 7 + D7 | P.2/P.9 audit items 1–6 with the basis for each conclusion, rerun on the new freeze; audit children through `run_unit`/`run_forked`; docstring corrected | P | Builder tool `audit_outside_services_s1.py` (children through `E.run_unit` :169 and `E.run_forked` :178; docstring states `env -i` with five names). `EV5/audit_final/outside_services.txt` (auditor env 5 names; units get the six `clean_env` names, stdin /dev/null). `process_api_reach.txt` (PID 1 line and process list present) | D7's method and docstring half is closed. Missing: item 6, the basis for each finding. There is no conclusions file for this freeze; `outside_services_conclusions.txt` exists only in the c9b324eb pack. See D6-5 | P |
| 11 | P.3 equal start times: `ambiguous=` / `CLEANUP_AMBIGUOUS` output; adoption and cleanup exercised | P | `test_no_timeout_kill.py:732` (both output forms asserted; the ambiguous process never signalled; simulated table) | The adoption of the ambiguous process after its parent ends, and its cleanup and reap, are not exercised | P |
| 12 | P.3 orphan attributed to every unit in flight, each a leak; `--jobs 2` at tool level; classifications | P | `test_no_timeout_kill.py:753` (S15: both units `leaked`, each CLEANUP names the orphan, `CLEANUP_SUMMARY units=2 leaked=2`); `:779` | Helper level (two threads) only. No tool run at `--jobs 2`; item classifications (`INDETERMINATE processes_left` for each) not asserted. `:436` still asserts `ua.leaked or ub.leaked` | P |
| 15 | P.4: no wait on −1 or a group; every wait WNOHANG | C | `test_no_timeout_kill.py:794` (AST: every `os.waitpid` takes a variable pid and `os.WNOHANG`; no `os.wait*`). Matches `tools/evkit.py:1315,1504,1883` | — | P |
| 19 | P.5/P.10: a unit forking repeatedly during cleanup; scans and deadline recorded | C | `test_no_timeout_kill.py:808` (more than 5 members, all gone; `sigterm`/`sigkill` > 1, `scans`, `deadline=grace` asserted) | — | O |
| 21 | P.5 steps 8–9: full CLEANUP fields, scan ids, `CLEANUP_SUMMARY` last, order by unit id, gone at the RESULT point (D12) | P | `test_no_timeout_kill.py:829` (full field regex, scan ids increasing, summary last, members gone when the final lines are made) | Helper level only. The tool-level helpers `p2_gone` (`test_mutation_timeout.py:1062`) and `p2b_gone` (`test_runner_zero_work.py:1206`) still check after the tool exits (D12 at tool level). The order assertion cannot fail: units are created in id order, and `final_lines` sorts by creation (`evkit.py:1474`) | P |
| 22 | P.6 leak: a mutation item, a tests-kind FILE, a wrapper FILE and CHECK at tool level | P | Tests-kind FILE: `test_exec_env.py:664`. Wrapper FILE: `test_runner_zero_work.py:2275`. Wrapper CHECK: `:2287` | No tool-level `MUTANT … INDETERMINATE cause=processes_left` test anywhere in `tests_tools` | P |
| 23 | P.7: a real nested supervisor; orphan adoption after escalation | C | `test_no_timeout_kill.py:853` (the child imports evkit, declares a supervisor and runs its own unit; escalation; both orphans adopted and attributed to `n1`) | — | P |
| 25 | P.8 step 5: failed id outside the paired inventory rejected, all 5 pairs | C | `test_runner_zero_work.py:2177` (`len(FAULT_CASE_PAIRS)==5`; each `INDETERMINATE cause=bad_result`, never CAUGHT, exit 3, `check_output`) | — | O |
| 29 | P.10 two-level nesting tool→leaf→test→process→child on timeout, interrupt and normal paths; second chain through `run_m8_tests_s1`; CLEANUP attribution | P | `test_exec_env.py:664,680,694` (the second chain: normal with attribution by `child_unittest_runner`, timeout with attribution by `run_m8_tests_s1`, interrupt) | The first chain (a mutation tool → leaf, e.g. `run_m2_tests_s1` → test → process → child) is not tested. No CLEANUP attribution is asserted on the interrupt path | P |
| 30 | P.10 `valid_result_then_hangs`: forked plant and forked case, SIGTERM-ignoring and unkillable; `processes_left` and no RESULT while alive | P | `test_runner_zero_work.py:2129` (plant, ignores SIGTERM), `:2143` (plant, unkillable: `CLEANUP_INCOMPLETE`, `remaining=`), `:2158` (case, ignores SIGTERM) | No unkillable variant for the forked case | P |
| 31 | A.1: steps 5, 6 and 8 keep the resolved selection | C | `test_runner_zero_work.py:2499,2507,2517` | — | P |
| 34 | A.3: `suites=-` with non-zero `selected` rejected | C | `test_consumer_exit_codes.py:963` | — | P |
| 36 | A.4: import failure keeps selection, with hash; history in case mode | C | `test_runner_zero_work.py:2535` (suites, `case_inventory_sha256`, every CASE `NOT_RUN cause=run_error`, for contracts and history with `--path`/`--factory`) | — | P |
| 41 | B.4: crash and bad_result causes for mutation and sabotage controls | P | `test_mutation_timeout.py:1491` and :1530 (8 generated tests: sabotage_m8 and sabotage_mie1, start and end, `CRASH_NO_RESULT` and `CHILD_EVIDENCE_ERROR`, per S17 (a)); `test_consumer_exit_codes.py:634` (m6 start control `CHILD_EVIDENCE_ERROR`) | Mutation tools: a crash cause appears only at helper level (`E.control`, `test_mutation_timeout.py:54`). No tool-level mutation end-control crash or bad-result test | P |
| 42 | B.5: full set on all five fault runners; the hang exercises the plant's own hang; pids, pgids and CLEANUP recorded | P | `test_runner_zero_work.py:2016-2068` (`AM5FaultRunner{M3,M5,M6,History}` inherit `test_plants`, `test_controls`, `test_f2_…`; `plant_is` asserts `CONTROL start CONTROL_PASS` and no start TIMEOUT; the permissive hang test is set to `None`); `P_IDENTITY` lines in `EV5/run_sets/py31x_T/logs/T10_*` | Group ids: every one of the 96 descendant entries for these runners has pgid `-`, because it is read after the run. A pgid appears only on the CLEANUP lines of leaking units. `run_faults_s1`'s own `P2FaultRunners` runs (`:1295`) write no record | P |
| 46 | C.2 per runner: nothing imported first; `cause=run_error`; the case hash; history case mode | P | `test_runner_zero_work.py:1918-1933` (IMPORT lines name only tools; every item `NOT_RUN cause=run_error`); `:1937`, `:1950`; `:2535` (hash for contracts and history) | The case hash is asserted for `run_contracts_s1` and `run_history_contract_s1` only, not for the other case runners in `test_c2_the_15_runners`. The item count is skipped when a cases run prints no item lines (`:1931`) | P |
| 50 | F.1: `sabotage_m7_s1` floor during items at `--jobs 2`; `NOT_RUN cause=run_stopped` | C | `test_mutation_timeout.py:1544` | — | P |
| 51 | F.2(a): one mechanism in every work loop | P | m2, sabotage_m7, the five fault runners, run_contracts, run_fin_corpus, run_m4_all (wrapper_main), run_m8_tests_s1 and child_unittest_runner (`test_runner_zero_work.py:2774,2787`; `test_exec_env.py:694`), the regression successors | No interrupt test for the three leaves `mut_runner_s1`, `run_m2_tests_s1` and `run_test_files_s1` (`tests_runner_main` is exercised only through child_unittest_runner) | P |
| 52 | F.2: SIGINT and, separately, SIGTERM on m2, sabotage_m7, run_faults, run_m2_tests, run_contracts, run_m4_all | P | m2 both (`test_mutation_timeout.py:1121,1135,1404-1438`); sabotage_m7 both (`:1244,1462,1475`); run_faults both (`test_runner_zero_work.py:1328` SIGINT, `:1350` SIGTERM); run_m4_all both (`:2235`) | `run_m2_tests_s1`: no signal test at all. `run_contracts_s1`: SIGINT only (`:1446`) | P |
| 53 | F.2 points: during a child, between items, during the end control, during its cleanup | P | m2: all four, both signals. sabotage_m7: child, end control, cleanup. run_faults: child, controls. run_m4_all: in a group (SIGINT), between groups | sabotage_m7 between items; run_faults between items and during the end control's cleanup; run_contracts and run_m2_tests_s1 beyond "during a child" (the latter not at all) | P |
| 55 | F.2(b): interrupted wrapper, group INDETERMINATE, rest NOT_RUN, exit 3 | C | `test_runner_zero_work.py:2255` | — | O |
| 56 | Reading 16: EXCLUDED printed after an interrupt before an H group | C | `test_runner_zero_work.py:2235` (G16–G18 `EXCLUDED … NOT_RUN_HISTORICAL`, both signals) | — | O |
| 57 | K.1 rejected forms | C | `test_consumer_exit_codes.py:974,982` | — | P |
| 59 | K.2 per-case message forms | C | `test_runner_zero_work.py:2591` (descendant hang, incomplete, malformed, ok=false, child_error, kill while writing, wrong keys, wrong types, looks-like-ok=false, valid-then-hang; `check_output`; gone) | — | P |
| 60 | K.2 hang: `check_output` and gone for history; `check_output` for mkt | C | `test_runner_zero_work.py:2625` (with `:1460`/`:1519` for the outcomes) | — | P |
| 62 | K.3 cross-kind v=3 dispatch | C | `test_consumer_exit_codes.py:989` | — | P |
| 63 | K.3 tests and wrapper outputs twice through the checker, with and without P's records | C | `test_consumer_exit_codes.py:1011` (outputs from `finish_tests`/`finish_wrapper`) | — | O |
| 66 | AM-2: F.2 in the leaves and child_unittest_runner (between tests); run_m8_tests_s1 | P | `test_runner_zero_work.py:2774` (child_unittest_runner: no test starts after the signal), `:2787` (run_m8_tests_s1) | The leaves (`LEAF_STEMS`: `mut_runner_s1`, `run_m2_tests_s1`, `run_test_files_s1`) are not interrupt-tested. SIGINT only | O |
| 68 + D6 | AM-2: fresh check of every process start in `tests_tools` with its limit; T-set leaf deadlines re-measured | P | `EV5/audit_final/tset_start_scan.txt` ("sites 83; with a limit found 83") | The scanner misses the `_p2sp` alias: at least 10 process starts in `test_runner_zero_work.py` (e.g. :1183 `p2b_run`, :1546, :2452, :2561) are not listed. The ones I read do have limits, but the recorded evidence is incomplete (D6-1). No leaf column (AM-2's file listed parent, limit and leaf) | P |
| 69 | AM-3 CR-02: a leak test; SystemExit cleanup on the normal path | C | `test_runner_zero_work.py:2696,2706` | — | P |
| 71 | AM-5(a): `run_child` plus the hook register once; `m8_mutants_s1`'s pre-start AUIF children registered; the leaf's reap before RESULT | P | `test_no_timeout_kill.py:882` (once only), `:903` (leaf reap); `:923` (AUIF `verify_tree` children registered under a phase, in the test process) | Not shown in `m8_mutants_s1` itself, i.e. its own pre-start `dependency.ensure()` children registered with "the hook shown in place before them". The tool-level test `test_runner_zero_work.py:2422` plants a Popen *after* `ensure()` | P |
| 72 | AM-5(b): immutable code's children keep command, env and limit (probe) | C | `test_no_timeout_kill.py:923` (flags `-I -B`, argv, env kept, `timeout=600` in source) | — | P |
| 73 | AM-5(c): each attribution-table row at tool level | P | `test_runner_zero_work.py:2422` (m8_mutants_s1 `PROCESSES_LEFT run_start`), `:2407` (child_unittest_runner run start read by its parent); test-module child in child_unittest_runner (`test_exec_env.py:664`); unit children (many) | Not tested: m8_mutants_s1 `after()` → `PROCESSES_LEFT run_end` (the test named `…run_start_and_run_end…` does run_start only, D6-3); run_m8_tests_s1's own ensure/reverify (run_start and run_end); r03 → "(INCOMPLETE: processes left)" | O |
| 75 | AM-5(e): a probe in each path (six classes), recorded in the evidence | P | Class 1 only, asserted in `test_no_timeout_kill.py:923` | No probe for classes 2–6; nothing recorded in `EV5/audit_final` | P |
| 77 | AM-6(b): drain, a grandchild with the write end (one byte, and silent) | C | `test_no_timeout_kill.py:951` | — | O |
| 79 | AM2-1(a): no batch after a start refusal; `--pin` uses the batch unit | C | `test_runner_zero_work.py:2558` | — | P |
| 81 | AM2-1(d) precedence row 7 over a leak; row 3 with a leak | C | `test_runner_zero_work.py:2572` | — | P |
| 83 | AM2-2(a) `SIGNAL_AFTER_COMPLETION` placement; M10's exit unchanged | C | `test_runner_zero_work.py:2737` | — | P |
| 85 | AM2-2(c) CR-02 synthetic `CompletedProcess` fields | P | `test_runner_zero_work.py:2715` (returncode −15, stdout `''`/`b''` by mode, `args[0]`) | `stderr` is not asserted. `args` "as rewritten" (the added `-S`) is not asserted beyond its first element (AM2-2 text, AM2 :156) | P |
| 90 | Reading 3: pipe drain bounded | C | `test_no_timeout_kill.py:981` | — | P |
| 91 | Reading 4: SIGTERM to the nested supervisor alone, others present | P | `test_no_timeout_kill.py:995` | It asserts only that the *first* SIGTERM goes to the direct child (`terms[0]`, and `terms[:1]` is redundant). Signalling every member at once with the direct child first would pass. "Alone while it lives" is not asserted | P |
| 92 | Reading 5: grace ends after two empty scans | C | `test_no_timeout_kill.py:1014` | — | O |
| 95 | Reading 8: start control interrupted before it began, tool level | C | `test_runner_zero_work.py:2376` | — | P |
| 96 | Reading 9: unowned child → run_end, `RUN_ERROR PROCESSES_LEFT run_end` (test in a copy) | P | `test_no_timeout_kill.py:1029` (attribution and `close_run()` error, in-process) | Not a tool run in a copy. No tool output is shown with `RUN_ERROR PROCESSES_LEFT run_end` (see also row 73) | O |
| 97 | Reading 10: argument errors are step 3 refusals with `suites=-` | C | `test_runner_zero_work.py:2339` | — | P |
| 98 | Reading 11: a real runner in both orders; CASE order | C | `test_runner_zero_work.py:2358` | — | P |
| 99 | Reading 13: `CLEANUP_SUMMARY units=` counting | P | `test_no_timeout_kill.py:1049` (3 subprocess units + 1 forked = `units=4`) | Reading 13's phase rule (a phase with children counted once, never twice) is not asserted. A real run's `units=` (e.g. m2s) is not reconciled | O |
| 100 | Reading 14: child_unittest_runner declares itself just before `verify_auif`; the check | C | `test_runner_zero_work.py:2440` | — | P |
| 101 | Reading 15: zombie check by the tool itself; leaf reap | C | `test_no_timeout_kill.py:903` (in-process leaf reap; no Z child of the process); `:416` (ChildProcessError) | — (the supervisor-side "no Z child" check is covered only through `assert_all_gone` on recorded identities) | P |
| 121 + D1 | I.3/B.5: P, B, K.2 and F.2 tests write pid, start, pgid, CLEANUP lines and the cleaning supervisor | P | `P_IDENTITY` records (helpers `test_no_timeout_kill.py:228`, `test_mutation_timeout.py:1276`, `test_runner_zero_work.py:1977`); 93 test ids in the py313 T logs | Not written by `P2FaultRunners` (`run_faults_s1`, B), `P2CaseRunners` (`:1413`, `:1460`, `:1488`, `:1519`, K.2), `P2MutationFamily` (`test_mutation_timeout.py:1121-1269`, F.2) or `P2NoResultSupervisors`. Descendant pgids are mostly `-` (204 of 291 entries on py313), read after the run | O |
| 113 + D20 | I.1 change record: `ENV_THREADS_AT_FORK`; the authorisation dated as AM-1 §0, 23:00 named as the build authorisation; mistakes 23, 29 and 34 as ruled | P | `programme/CHANGE_RECORD_APG-M11-S1.md:80` (code), `:50-51` (dates), `:150-152` (mistakes) | The plan items are present. But the record's pin references (v87–v97, v98–v109, v110, v111) are c9b324eb's; this tree's pins end at v102, with v87–v98 the recovery re-pins, v99 test_files and v100–v102 AM5/row 68. The row 68 test change (v102) is not named (D6-2) | P |
| D10 | E.2's fixed values asserted in a test | C | `test_mutation_timeout.py:1560` | — | disc. |
| D14 | 1 MiB exactly accepted, +1 rejected, tool level | C | `test_mutation_timeout.py:1576` (run_faults_s1: `FORK_MESSAGE_MAX` → `child_error`; +1 → `bad_result`) | — | disc. |
| D17 | `E7…test_m8_mutants_controls_and_a_known_kill` asserts the known kill | P | `test_exec_env.py:575` | It asserts M10's *control* line `KILLED tier 1` and that ML-01 never runs. It is a builder reading that the control's kill is "the known kill"; no mutant kill is asserted, and by its own comment none can be on this view. Needs a ruling, or a name that matches | disc. |
| D21 | Builder-tool docstrings: `run_index_s1.py` last_line ≤ 300-char prefix; `check_m8_log_s1.py` reads v=3 via `check_output` | C | `SCR/recovery/btools/run_index_s1.py:5-6` (code :68), `check_m8_log_s1.py:2-4` (hashes `10cb9570…`, `0cd97130…`, equal to the `REPO` copies) | — (the packaging statement on how c9b324eb's evidence was made is pending) | disc. |
| D15 | m2 INDETERMINATE allowance requires M10 info `timeout` | C | `btools/compare_pass2_s1.py:274` and `:423` (`a == KILLED and a[1] == 'timeout'`); tool `7c2bd48d…` (rewritten, recorded in `REPO/builder_tools/step5_recovery/SHA256_now.txt`) | — | disc. |
| D16 | b6 compares CONTROL values and causes | C | `EV5/compare_py31x/b6.txt` (`CONTROL lines new=… old=…` per runner; `RESULT b6 SAME`, 111 items, both Pythons); totals vs d5f87d6b and c9b324eb also compare the CONTROL lines | — | disc. |
| D18 | Build log "same as 11-05" corrected; env 5 names, PID 1 and process list, conclusions file | P | `REPO/records/PASS2_BUILD_LOG.md:87` (03:15 correction); on this freeze `EV5/audit_final/*` has 5 names and PID 1 with the process list | No conclusions file for ee1ce3ec. The correction names "the 02:45 entry" while the claim is in the 02:15–02:43 entry (`:82`, D6-6) | disc. |
| D22 | Privacy: no session-identifier values in the audit | C (packaging) | `EV5/audit_final/outside_services.txt`: auditor and unit environments are 5 and 6 allowlist names; no e-mail and no URL. The only UUID-shaped string is the workspace folder id inside paths | The package-level search is at packaging (Appendix A part 2). Loose EV5 files carry the workspace folder id in paths (the owner's "mask loose" rule applies at packaging) | disc. |
| 106 | AM3-1(e): B.6, K.2 and E.2 still identical | C | `EV5/compare_py31x/b6.txt`, `k2.txt` SAME item by item against e4531a35 (owner 2026-11-11 22:47), `b6_/k2_recorded_totals.txt` SAME (d5f87d6b, c9b324eb); `golden.txt`, `pairs.txt`, `m2.txt` SAME, both Pythons | — (reference reworded per the owner's answer) | P |
| 110 | AM4-1/E.2 m2: M10 `run_one` harness, fixed values, allowances only, both Pythons; AM5-3 A1 + B | C | `EV5/compare_py313/m2.txt`: SAME; allowed CA01 and RI13 (A1) and RI10 only. `compare_py312/m2.txt`: SAME, RI10 only. `m2_logs/equiv_1worker.txt`: all 3 EQUIV ids SURVIVED on both. Five slices with coverage checked (AM5-2). The allowance code `compare_pass2_s1.py:429` matches AM5-4's paragraph (`AM53_IDS` the two ids, M10 `('KILLED','timeout')`, successor `EQUIVALENT`) | — (the timeout-kill limitation now reads 79 on 3.13 and 0 on 3.12, against AM5 §0's "83"; for the documents) | O |
| 111 | AM4-1 literal run of M10's `m2_mutants.py` | C (by waiver) | AM5-1 A substitute: `m2_logs/m10_script_list.txt` on both Pythons (exit 0, 199 ids, RI10 at 51); the harness has RI10 as its only ERROR; M10's code in AM5 App. D.3; `m2.txt` "M10 script as written: NOT RUN" | Closed by the owner's evidence substitution, not by a literal run | O |

**Mapped outside the 65 (scope check, section 2)**

| # | Requirement | Now | Evidence | Note | 1st |
|---|---|---|---|---|---|
| 17 | P.5 constants and item limits; LIMIT line | C | `test_consumer_exit_codes.py:944`; `LIMIT item=300s …` on all 16 b6/k2 runs on both Pythons (`EV5/compare_py31x/b6_logs`, `k2_logs`) | Owner's 12:47 plan correction for row 17 lost; the builder added no test | C |
| E.2 | E.2 comparisons on both Pythons | C | golden, pairs and m2 SAME on both (`EV5/compare_py31x/`); literal run waived (AM5-1 A) | E point 2 itself stays partly addressed by the paper (paper :545, :603) | O |
| AM5-4 allowance paragraph | the comparison-tool change checked against it | C | `compare_pass2_s1.py:29,426-431` | As row 110 | — |

## 2. Scope check

- **The 65-item list matches what amendment 5 sends to the scoped re-mapping.** That is AM5-4 (v): "the changed rows and discrepancies 6, 7, 15, 16, 18, 21 and 22"; Appendix A part 3 ("the scoped re-mapping verifies each"); and AM5-4's comparison-allowance paragraph.
  - Appendix A part 1 has 54 row entries plus D10, D14, D17 and D21, so 58 in all.
  - Part 3 has D15, D16, D18 and D22.
  - Rows 106, 110 and 111 complete the 65.
  - So the list is a faithful reading of AM5. The owner's own "64 + row 42" cannot be checked against the lost v4 list.
- **Possibly missing:**
  - **Row 17.** The owner's 12:47 rulings include "plan corrections for rows 6 and 17". That brings row 17 into the AM5 plan, but it is not in Appendix A part 1 and not in the 65. I mapped it separately: C.
  - **E.2.** It was O in the first mapping and waits on S13/S14 like rows 110 and 111, but AM5's triage lists only rows 106, 110 and 111. I mapped it separately: C. E point 2 stays P by the paper's own terms.
  - **AM5-4's comparison-allowance paragraph.** It explicitly names "the scoped re-mapping". It is not a numbered item, so I checked it under row 110: it conforms.
- **Embedded in rows, not separate:** discrepancies 1 (row 121), 6 (68), 7 (7), 12 (21), 20 (113), and the D13/D14 sub-items (rows 11, 12, 4, 30, 71, 42, 60, 98, 63, 29).
- **Nothing extra.** I found no item in the 65 that amendment 5 does not send to the re-mapping.

## 3. Counts

| Set | C | P | O | Total |
|---|---|---|---|---|
| 64 items (the 65 without row 42) | 37 | 27 | 0 | 64 |
| Row 42 | 0 | 1 | 0 | 1 |
| All 65 | 37 | 28 | 0 | 65 |

**Against v4 on 303b6414 (56 C, 8 P, 0 O over 64 items):**
- This re-mapping has 19 fewer C and 19 more P, and the same 0 O.
- With v4's item list lost, the comparison can be made only at the level of counts. I cannot say which items v4 closed, so I cannot say which items "regressed".
- I can say this much: the number of partly addressed items is higher than v4's (27 against 8 over the same 64-item count). The recovery authorisation names a higher count of P or O than on 303b6414 as a stop condition. I report the count; the decision is the owner's.

**Every item classed P (none O), with its class in the first mapping:**

| Item | 1st |
|---|---|
| 4 | P |
| 6 | P |
| 7 (+D7) | P |
| 11 | P |
| 12 | P |
| 21 | P |
| 22 | P |
| 29 | P |
| 30 | P |
| 41 | P |
| 42 | P |
| 46 | P |
| 51 | P |
| 52 | P |
| 53 | P |
| 66 | O |
| 68 (+D6) | P |
| 71 | P |
| 73 | O |
| 75 | P |
| 85 | P |
| 91 | P |
| 96 | O |
| 99 | O |
| 121 (+D1) | O |
| 113 (+D20) | P |
| D17 | disc. |
| D18 | disc. |

## 4. New discrepancies

- **D6-1: the row 68 scanner misses an alias, so its evidence is incomplete.**
  - `btools/tset_start_scan_s1.py` (`86f7d2ab…`) matches subprocess calls only when the module name contains "subprocess" or is `sp`/`_sp` (:23), though its docstring says "any alias" (:5).
  - So every start through `_p2sp` in `test_runner_zero_work.py` is missing from `EV5/audit_final/tset_start_scan.txt`: :1183 (`p2b_run`, used by most AM5 tests), :1546, :1577, :1764, :2335, :2443, :2452, :2561, :2566, :2768.
  - The scan lists only 3 sites in that file.
  - Every missed site I read has a limit, so the substance holds by my reading. But "sites 83" and the owner's "10 of 83" are undercounts.
  - This is the same class of mistake as mistake 31.
- **D6-2: the change record's pin references are stale.**
  - It names pins v87–v97, v98–v109, v110 and v111 (`CHANGE_RECORD:41,107,112,115`), which are c9b324eb's numbering.
  - This tree's `tools/expected_counts.json` is at version 102: v87–v98 are recovery re-pins, v99 test_files, v100–v102 the AM5 and row 68 test changes.
  - The row 68 test-only change (commit 417cafb, v102) is not described in the record.
- **D6-3: a test does less than its name.** `test_runner_zero_work.py:2422` `test_run_start_and_run_end_of_a_mutation_tool` tests run_start only. Its comment promises run_end (`PROCESSES_LEFT run_end`), which is not exercised.
- **D6-4: the GitHub copy of a builder tool is not the one that made the evidence.**
  - `REPO/builder_tools/step5_recovery/recorded_totals_s1.py` (`2af98df5…`, listed in `SHA256_now.txt`) is the pre-fix version with the "be0c27b" label.
  - The tool that made the corrected evidence (`SCR/recovery/btools/recorded_totals_s1.py`, `55049361…`) is not in `REPO`.
- **D6-5: no audit conclusions file for this freeze.**
  - Amendment 5 Appendix A part 3 says a conclusions file was written, but that was for c9b324eb.
  - For ee1ce3ec, `EV5/audit_final` has none, and audit item 6 (the basis for each finding) is not recorded.
  - The step 5.4 build-log entry does not mention this.
- **D6-6: a wrong entry time.** The 03:15 correction in `REPO/records/PASS2_BUILD_LOG.md:87`, and AM5 Part 3, say the "02:45 entry" was corrected. The "same as 11-05" text is in the 02:15–02:43 entry (`:82`); the 02:45 entry is the child-start scan.
- **D6-7: the per-test pgid is mostly not recorded.**
  - The `p2_identity_record` docstring says the pgid is read "while it lived when possible" (`test_runner_zero_work.py:1978`).
  - In fact it is read after the tool has exited, so 204 of 291 descendant entries in the py313 T logs carry `-`.
  - Bears on rows 42 and 121.
- **D6-8: the timeout-kill counts have changed (for the documents).**
  - On this freeze M10's `run_one` gives 79 timeout kills on 3.13 (KILLED 197: tests 118, timeout 79) and 0 on 3.12 (KILLED 195: tests 182, contracts 13; EQUIVALENT 3).
  - AM5 §0's limitation states 83, and the 5.3 build-log entry gives no counts.
  - The final report must carry this freeze's figures.

## 5. Summary

1. The freeze, M10 and authority hashes match. The fresh extraction equals the T-set extractions.
2. The T sets ran 700 tests OK on both Pythons, with no skips.
3. Of the 65 items: 37 closed, 28 partly addressed, 0 open. Row 42 is partly addressed.
4. Over the 64 items: 37 C, 27 P, 0 O, against v4's 56 C, 8 P, 0 O.
5. The item comparison with v4 is impossible: its list is lost.
6. Rows 106, 110 and 111 are closed. The m2 comparison is SAME on both Pythons, within the A1 allowance exactly as authorised, and the literal run is waived.
7. Discrepancies 10, 14, 15, 16 and 21 are closed; 22 is closed pending its packaging check.
8. Most partly addressed items lack one named piece: a tool-level form, a missing tool or signal in F.2, or a weak assertion (rows 21, 91).
9. Real gaps:
   - no F.2 test on the three leaves;
   - no tool-level mutation-item leak;
   - no first nesting chain;
   - missing AM-5(c) rows;
   - incomplete identity records.
10. The audit for this freeze has no item 6 conclusions (rows 7 and D18).
11. The row 68 scan misses an alias (D6-1). The change record's pin numbers are stale (D6-2).
12. The scope list matches amendment 5. Row 17 and E.2 may belong to it; both map as closed.
