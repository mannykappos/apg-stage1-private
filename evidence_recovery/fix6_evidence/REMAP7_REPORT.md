# INDEPENDENT READ-ONLY RE-MAPPING (agent), after fix 6, freeze a7f599f9

INDEPENDENT READ-ONLY (agent). A mapping of requirements to tests and evidence. Not a stage 1 acceptance statement; nothing here
on production readiness. Times from `date` (Australia/Melbourne, AEDT): first clock read 01:26:25 on 2026-11-15; report written
from 01:37 onward (final clock read in section 5).

## 0. Method and limits

**Inputs and hashes, as I checked them**
- `FREEZE`: SHA-256 `a7f599f936937d5fd06a720d19ba3bbd1966ef81e2b9395687db28501c2f76bd`. Matches the brief and both lines (a, b) of
  `SCR/recovery/freeze6/two_builds_sha256.txt`. Extracted fresh into `SCR/remap7/x/`: 1555 files.
  - `diff -rq` against `EV6/run_sets/py313_T/x` and `py312_T/x`: identical apart from `__pycache__` folders (6 in each), which the
    test runs write; the same holds for `EV5`'s T-set extractions, and `tree_after.txt` reports 0 changes with the zip hash `a7f599f9…`.
- `OLDFREEZE`: `ee1ce3ec4be1a76482595688cfd9b41910fa26f4c9fe9a936f8971e86b5e0735`, extracted into `SCR/remap7/x5/` for the diff only.
- `M10`: `bd5c592a198581808237e5a5e563aa15c3be977d3f3e0d68511499d755435192`. Matches.
- Authority (`REPO/authority/`): paper `23d2adb9…f0ea5`, AM1 `211971…d382`, AM2 `a3cc26b5…cd6e`, AM3 `89e5a268…6715`,
  AM4 `b6be070e…a7d6`, AM5 draft v4 `3649fa74…c295b`. Same as step 6 read.
- `REPO` read at HEAD `f48b8d3` (branch `records`; two builder commits, `c6868ba` and `f48b8d3`, landed at 01:28 while I worked; they
  touch the build log and the brief only).
- **What fix 6 changed** (`diff -rq OLDFREEZE FREEZE`): exactly 7 files: four `tests_tools` files (`test_exec_env.py`,
  `test_mutation_timeout.py`, `test_no_timeout_kill.py`, `test_runner_zero_work.py`), `tools/expected_counts.json` (one new pin entry,
  v103, for those four files only), `programme/CHANGE_RECORD_APG-M11-S1.md` and `programme/APG-M11-S1_MANIFEST.csv` (the four test
  hashes, the pins file and the record). No product or successor-tool file changed. The new test files' hashes equal the v103 pins
  and the manifest. Test edits to `tools/evkit.py` and other tools happen only inside temporary copies made by the tests.
- **The T sets** (`EV6/run_sets/py313_T`, `py312_T`): 10 files each, every exit 0, every log ends `OK`, 0 lines matching `skip`, 0
  `FAIL:`/`ERROR:` lines. 727 tests on each Python (51+91+44+16+12+66+4+206+56+181), up from 700 (pins: 42→44, 200→206, 52→56,
  166→181). `EV6/interrupted/` was not used as evidence.
- **Builder tools**: every `.py` in `SCR/recovery/btools` is byte-identical to `REPO/builder_tools/current_fix6/` and to its
  `SHA256.txt`; the fix 6 tools (`audit_outside_services_s1.py` `b27d60ac…`, `tset_start_scan_s1.py` `9572e0c0…`) were last
  written 19:07 on 2026-11-13, before the evidence run (19:23:30). The `EV6` drivers differ from the `REPO` copies only in the
  masked session-folder path line.
- **"Ran OK on both Pythons"** is judged as step 6 did: the T logs are not verbose, so a named test counts when its file ran OK on
  both Pythons with no skips. I found no `skipTest` or early-return guard in the fix 6 tests. A test attribute set to `None`
  (`AM5FaultRunnerFullSet.test_the_hang_on_each_of_the_other_four_runners`) is not run, as step 6 noted.

**What I ran** (read-only on every input): `sha256sum`, `ls`, `diff`, `cmp`, `grep`, `sed -n`, `awk`, `unzip -q` (into
`SCR/remap7/`), `git --no-optional-locks log/rev-parse/status`, `date`, and four short `python3 -I -S` scripts of my own (below). I ran
no test file and no long job.

**What I wrote** (only under `SCR/remap7/`): the extractions `x/` and `x5/`; `work/rzw.diff` (a diff of one test file);
`work/ident.py` (counts `P_IDENTITY`/`P_PROBE` records in T logs); `work/cov.py` (which test methods of the P/AM5/AM6 classes have
records); `work/starts.py` (an independent AST list of process-starting calls in `tests_tools`, compared with the row 68 scan);
`work/linemap.py` (maps step 6's cited lines to test names and their new lines); two hash lists of the T logs; this report.

**What I could not check**
- The v4 re-mapping's item list (lost): comparison with v4 is on counts only.
- The owner's 12:47 plan corrections for rows 6 and 17: the surviving record says only "as the builder proposed".
- What a test asserts at run time: judged by reading its code; the T logs show only that the file passed.
- Whether a particular timing-dependent test hit the moment its name describes (see D7-1).

## 1. Table

Classes: C = closed by evidence, P = partly addressed, O = still open. Test paths are `FREEZE:tests_tools/…` (file:line is the
`def` line). "S6" is the class at step 6 (`ee1ce3ec`); "1st" the class in the first mapping (`c9b324eb`; "disc." = a discrepancy
there). Every named test's file ran OK on both Pythons in `EV6/run_sets/py31x_T`.

| # | Requirement (short) | Now | Test / evidence | What is missing (P/O), notes | S6 | 1st |
|---|---|---|---|---|---|---|
| 4 | P.2/P.10 refusal `ENV_NO_PROCESS_SUPERVISION`, exit 2, every item NOT_RUN, each failing step | C | `test_mutation_timeout.py:1722` `AM6MutationToolGaps.test_row4_each_remaining_setup_failure_refuses_at_tool_level` (run_faults_s1 in copies: /proc, pidfd_open, prctl set, prctl read-back; each: exit 2, the reason token, every pinned PLANT `NOT_RUN cause=run_error`, no CONTROL, `check_output`); with `:1383,1390,1397` (libc, pidfd_send_signal, SIGCHLD) | — | P | P |
| 6 | P.2: no secret in the allowlist; a secret in a unit's env stops the work; value never recorded | P | Builder tool `audit_outside_services_s1.py:148,225` (stop, exit 3, names only); `EV6/audit_final/secret_stop_demo.txt` (planted `APG_AUDIT_DEMO_API_TOKEN`, STOP line, value shown as `<secret-bearing: value not recorded>`; the planted value is in no `EV6` file); `outside_services.txt` (`p2_secret_check`: none in the two units); `test_no_timeout_kill.py:712` (non-inheritance) | The stop is shown in the builder's audit tool, not in a T-set test of a successor tool, which is what AM5 App. A part 1 means by "tool level" ("the real successor tool, run in a temporary copy … added to the T set"). The planted name reached only the unscrubbed control child, not a unit. P.2's own wording (the audit stops, by name) is met; whether the lost 12:47 plan correction for row 6 accepted an audit-level stop cannot be checked. A successor-level stop would need product logic, outside fix 6's scope | P | P |
| 7 + D7 | P.2/P.9 audit items 1–6 with the basis for each, rerun on the new freeze; children via run_unit/run_forked; docstring | C | `EV6/audit_final/outside_services_conclusions.txt` (points 0–7, a "Basis" per finding; identical to `REPO/evidence_recovery/fix6_evidence/`); `outside_services.txt` (auditor env 5 names; `started_by` `evkit.run_unit` / `run_forked`); `process_api_reach.txt`. Spot checks of its bases hold (driver6_54.sh:38 E5, :40 `test $? -eq 3`; `child_start_scan.txt` evkit.py:1748 Popen, :1840 fork) | — (open finding 11 stays open, as the file says) | P | P |
| 11 | P.3 equal start times: `ambiguous=` recorded; adoption, cleanup, reap | C | `test_no_timeout_kill.py:1080` (real processes: equal start time asserted, `ambiguous=` on the CLEANUP line, adopted by `am`, in `reaped_orphans`, never signalled while its equal-start parent existed, all gone); `:733` (output forms) | — (see D7-5 on a pid-order assumption) | P | P |
| 12 | P.3 orphan attributed to every unit in flight, each a leak; `--jobs 2` at tool level; classifications | C | `test_mutation_timeout.py:1761` (m2_mutants_s1 `--jobs 2`: each MUTANT `INDETERMINATE cause=processes_left`, each item's CLEANUP `left=` shares the orphan, `check_output`, gone); `test_no_timeout_kill.py:436` now asserts each (`:457-458`); `:754` | — | P | P |
| 15 | P.4 every wait WNOHANG on one pid | C | `test_no_timeout_kill.py:795` | — | C | P |
| 19 | P.5/P.10 forking during cleanup; scans, deadline | C | `test_no_timeout_kill.py:809` | — | C | O |
| 21 | P.5 steps 8–9: full CLEANUP fields, scan ids, summary last, order by unit id, gone at the RESULT line | C | `test_no_timeout_kill.py:830` (fields, scan ids, summary last); `:1105` (order that can fail: first-created unit finishes last and sorts last by name, lines still in creation order); tool level at the RESULT line: `test_mutation_timeout.py:1750` (m2) and `test_runner_zero_work.py:3068` (run_faults_s1), both through `p2_run_result_check` (`test_mutation_timeout.py:1659`, checks every seen identity when the RESULT line is read) | — Notes: the order rests on the builder's reading "id order is creation order" (disclosed, not owner-ruled; section 4, D7-6). The RESULT-line check runs when the line is read, which can be just after the tool exits; it would still catch a post-RESULT cleanup here because the leftover ignores SIGTERM (10 s grace) (D7-11) | P | P |
| 22 | P.6 leak: mutation item, tests-kind FILE, wrapper FILE and CHECK at tool level | C | Mutation item: `test_mutation_timeout.py:1739` (`MUTANT … INDETERMINATE cause=processes_left`, CLEANUP `killed=`, `check_output`, gone). FILE: `test_exec_env.py:664`. Wrapper FILE/CHECK: `test_runner_zero_work.py:2315,2327` | — | P | P |
| 23 | P.7 real nested supervisor; orphan adoption after escalation | C | `test_no_timeout_kill.py:854` | — | C | P |
| 25 | P.8 step 5: failed id outside the paired inventory, all 5 pairs | C | `test_runner_zero_work.py:2217` | — | C | O |
| 29 | P.10 two-level nesting on timeout, interrupt and normal paths; second chain; CLEANUP attribution | P | First chain (m3_mutants_s1 → run_m2_tests_s1 → test → process → child): `test_exec_env.py:733` (normal: CONTROL start `processes_left`, CLEANUP by m3_mutants_s1 names ≥2) and `:749` (interrupt: `CONTROL_INTERRUPTED`, CLEANUP names ≥3). Second chain: `:664,680,694`, interrupt now with CLEANUP attribution by run_m8_tests_s1 (`:703-706`) | The first chain's **timeout** path is not tested (P.10/AM-2: "on a timeout, on an interrupt and on the normal path"; the change record itself says "normal and interrupt paths") | P | P |
| 30 | P.10 `valid_result_then_hangs`: forked plant and case, SIGTERM-ignoring and unkillable | C | `test_runner_zero_work.py:2169,2183,2198`; new `:2945` (forked case, unkillable by simulation in a copy: CASE `INDETERMINATE cause=processes_left`, `RUN_ERROR CLEANUP_INCOMPLETE`, exit 2, `deadline=kill_verify`, `remaining=`, summary `remaining=1`) | — | P | P |
| 31 | A.1 steps 5, 6, 8 keep the selection | C | `test_runner_zero_work.py:2549,2557,2567` | — | C | P |
| 34 | A.3 `suites=-` with non-zero `selected` | C | `test_consumer_exit_codes.py:963` | — | C | P |
| 36 | A.4 import failure keeps selection, with hash; history case mode | C | `test_runner_zero_work.py:2585` | — | C | P |
| 41 | B.4 crash and bad_result for mutation and sabotage controls | C | Mutation: `test_mutation_timeout.py:1778` (m2 start and end control: `CRASH_NO_RESULT`, `CHILD_EVIDENCE_ERROR`, exit 3, `control_<where>=FAIL`, item kept or NOT_RUN, `check_output`, gone). Sabotage: `:1513` `AM5SabotageControls` (generated by `:1547`); `test_consumer_exit_codes.py:632` | — | P | P |
| 42 | B.5 full set on five runners; plant's own hang; pids, pgids, CLEANUP recorded | C | `test_runner_zero_work.py:2056-2111` (`AM5FaultRunner{M3,M5,M6,History}`), `P2FaultRunners.run_f` `:1318` now writes the record; pgids noted while alive (`p2b_note_pgids` `:1182`). `EV6` T logs: 506 (3.13) / 522 (3.12) descendant entries, 3 / 2 with `-`, none in the fault-runner tests | — | P | P |
| 46 | C.2 per runner: nothing imported first; run_error; case hash; history case mode | C | `test_runner_zero_work.py:1977` (case hash now asserted for every case runner, `:1985-1987`); `refused` `:1956` (item count never skipped, `:1974`); `:1993`; `:2585` | — | P | P |
| 50 | F.1 sabotage_m7 floor during items `--jobs 2`; run_stopped | C | `test_mutation_timeout.py:1567` | — | C | P |
| 51 | F.2(a) one mechanism in every work loop | C | As step 6, plus the three leaves: `test_mutation_timeout.py:1833` (`run_m2_tests_s1`, `mut_runner_s1`, `run_test_files_s1`; SIGINT and SIGTERM; no test starts after the signal; `INTERRUPTED`, exit 3, `check_output`, gone) | — | P | P |
| 52 | F.2 SIGINT and, separately, SIGTERM on m2, sabotage_m7, run_faults, run_m2_tests, run_contracts, run_m4_all | C | m2 `test_mutation_timeout.py:1135,1150,1427,1461`; sabotage_m7 `:1267,1485,1498`; run_faults `test_runner_zero_work.py:1352,1374`; run_m2_tests_s1 `test_mutation_timeout.py:1833`; run_contracts SIGINT `:1439`, SIGTERM `:2978` (first half: 38 cases `INDETERMINATE cause=interrupted`, `INTERRUPTED signal=SIGTERM`); run_m4_all `:2275` | — | P | P |
| 53 | F.2 points: during a child, between items, during the end control, during its cleanup | P | sabotage_m7 between items, both signals `test_runner_zero_work.py:3003`; run_faults between items and during the end control's cleanup, both signals `:3040` (`SIGNAL_AFTER_COMPLETION`, never `INTERRUPTED`); run_m2_tests_s1 during a test (leaf: honoured between tests) `test_mutation_timeout.py:1833`; run_contracts during the batch's cleanup `test_runner_zero_work.py:2978` (second half) | run_contracts "during its cleanup" is not shown: the test accepts either `INTERRUPTED` or `SIGNAL_AFTER_COMPLETION` (`:2998`), so it neither shows the signal landed in the cleanup nor that the fixed outcome was kept (P.8 requires `SIGNAL_AFTER_COMPLETION` there). D7-1 | P | P |
| 55 | F.2(b) interrupted wrapper | C | `test_runner_zero_work.py:2295` | — | C | O |
| 56 | Reading 16 EXCLUDED after an interrupt | C | `test_runner_zero_work.py:2275` | — | C | O |
| 57 | K.1 rejected forms | C | `test_consumer_exit_codes.py:974,982` | — | C | P |
| 59 | K.2 per-case message forms | C | `test_runner_zero_work.py:2641` | — | C | P |
| 60 | K.2 hang: check_output and gone (history); check_output (mkt) | C | `test_runner_zero_work.py:2675` | — | C | P |
| 62 | K.3 cross-kind v=3 dispatch | C | `test_consumer_exit_codes.py:989` | — | C | P |
| 63 | K.3 twice through the checker | C | `test_consumer_exit_codes.py:1011` | — | C | O |
| 66 | AM-2: F.2 in the leaves and child_unittest_runner (between tests); run_m8_tests_s1 | P | Leaves: `test_mutation_timeout.py:1833` (SIGINT and SIGTERM). child_unittest_runner `test_runner_zero_work.py:2828`, run_m8_tests_s1 `:2841`, `test_exec_env.py:694` | child_unittest_runner and run_m8_tests_s1 are still interrupt-tested with SIGINT only (step 6's "SIGINT only"; AM5 App. A rows 51–53 ask for SIGINT and SIGTERM separately on them too). D7-3 | P | O |
| 68 + D6 | AM-2: every process start in tests_tools with its limit; leaf deadlines re-measured | C | `EV6/audit_final/tset_start_scan.txt` ("sites 102; with a limit found 102; NONE 0", `_p2sp` sites included, leaf table "parent, limit and leaf"). My own AST scan (`work/starts.py`) finds 102 process-starting calls in `tests_tools`, every one listed | — | P | P |
| 69 | AM-3 CR-02 leak test; SystemExit cleanup | C | `test_runner_zero_work.py:2747,2757` | — | C | P |
| 71 | AM-5(a) run_child + hook once; m8_mutants_s1's pre-start AUIF children registered; leaf reap | C | `test_no_timeout_kill.py:883,904`; new `test_runner_zero_work.py:2899` (a child started inside AUIF's own `ensure()`, in a copy: `RUN_ERROR PROCESSES_LEFT run_start`, every MUTANT NOT_RUN, exit 2, CLEANUP run_start by m8_mutants_s1 `left=`) | — | P | P |
| 72 | AM-5(b) immutable code's children keep command, env, limit | C | `test_no_timeout_kill.py:924` | — | C | P |
| 73 | AM-5(c) each attribution-table row at tool level | C | m8_mutants_s1 run_start and run_end `test_runner_zero_work.py:2462` (run_end half now present: item kept, `RUN_ERROR PROCESSES_LEFT run_end`, exit 2); run_m8_tests_s1 run_start and run_end `:2913`; child_unittest_runner start `:2447`; test-module child `test_exec_env.py:664`; r03 "(INCOMPLETE: processes left)" `test_runner_zero_work.py:2932`; unit children (many) | — Note: for the two run_start rows the table's "every FILE NOT_RUN" is not asserted (`:2925` asserts only no CHILD line; `:2447` asserts the parent's ITEM_ERROR). Beyond what step 6 named: section 4, D7-7 | P | O |
| 75 | AM-5(e) a probe in each path (six classes), recorded in the evidence | P (packaging) | Class 1 `test_no_timeout_kill.py:924`; classes 2–6 `test_runner_zero_work.py:3112,3124,3139,3157,3177` (`AM6FindingThirteenProbes`), records written as `P_PROBE` lines: 86 in each `EV6` py31x_T T10 log (5 tests) | Nothing in `EV6/audit_final` (AM-5(e): "recorded in `evidence/audit/`"; step 6 named this). Copying the `P_PROBE` records there at packaging would meet it. Also weaker than finding 13's description: class 2 does not assert "no `-S`" or "no time limit" (`:3119-3121`), class 3 not its 300 s; no probe asserts a limit. The documents' corrections (P1-F6 row, docstring) are at packaging | P | P |
| 77 | AM-6(b) drain, grandchild holds write end | C | `test_no_timeout_kill.py:952` | — | C | O |
| 79 | AM2-1(a) no batch after a start refusal; `--pin` | C | `test_runner_zero_work.py:2608` | — | C | P |
| 81 | AM2-1(d) precedence row 7 and row 3 with a leak | C | `test_runner_zero_work.py:2622` | — | C | P |
| 83 | AM2-2(a) SIGNAL_AFTER_COMPLETION placement; exit kept | C | `test_runner_zero_work.py:2791` | — | C | P |
| 85 | AM2-2(c) CR-02 synthetic CompletedProcess fields | C | `test_runner_zero_work.py:2766` (returncode −15, stdout `''`/`b''`, `args[0]`; new: `stderr` `''`/`b''` and `args[1:3] == ['-I', '-S']`, `:2776-2777`, printed by the stub `:2703`) | — | P | P |
| 90 | Reading 3 pipe drain bounded | C | `test_no_timeout_kill.py:982` | — | C | P |
| 91 | Reading 4 SIGTERM to the nested supervisor alone while it lives | C | `test_no_timeout_kill.py:1129` (every SIGTERM sent while the nested supervisor is alive goes to it; the other member only after; all gone). Signalling every member at once would now fail | — | P | P |
| 92 | Reading 5 two empty scans | C | `test_no_timeout_kill.py:1015` | — | C | O |
| 95 | Reading 8 start control interrupted before it began | C | `test_runner_zero_work.py:2416` | — | C | P |
| 96 | Reading 9 unowned child → run_end, tool run in a copy | C | `test_runner_zero_work.py:3209` (run_faults_s1 in a copy, a child started outside every unit and phase: `RUN_ERROR PROCESSES_LEFT run_end`, exit 2, CLEANUP run_end `left=`, the plant's CAUGHT kept, `check_output`, gone); `test_no_timeout_kill.py:1030` | — | P | O |
| 97 | Reading 10 argument errors, `suites=-` | C | `test_runner_zero_work.py:2379` | — | C | P |
| 98 | Reading 11 real runner both orders; CASE order | C | `test_runner_zero_work.py:2398` | — | C | P |
| 99 | Reading 13 `units=` counting | C | `test_no_timeout_kill.py:1153` (a phase with two children counted once: `units=2` for phase + one unit); `test_runner_zero_work.py:3225` (a real run_faults_s1 run reconciled: 2 plants + 2 controls = `units=4`); `test_no_timeout_kill.py:1050` | — (the m2s evidence run's `units=` is still not reconciled; step 6 gave it as an example only) | P | O |
| 100 | Reading 14 child_unittest_runner declaration | C | `test_runner_zero_work.py:2490` | — | C | P |
| 101 | Reading 15 zombie check; leaf reap | C | `test_no_timeout_kill.py:904,416` | — | C | P |
| 121 + D1 | I.3/B.5: P, B, K.2, F.2 tests write pid, start, pgid, CLEANUP lines, cleaning supervisor | P | Records now from `P2MutationFamily` (12/12 tests), `P2FaultRunners` (4/4), `P2NoResultSupervisors` (9/9), `P2CaseRunners` (4/5), all AM6 classes; pgids noted while alive. `EV6` T logs: 149 test ids with `P_IDENTITY` (93 on `EV5`); 506/522 descendant entries, 3/2 `-` (`EV5`: 291 entries, 204 `-` on 3.13) | `P2CaseRunners.test_k2_per_case_on_run_fin_corpus_s1` (`test_runner_zero_work.py:1516`, the K.2 per-case test; step 6 named it as `:1488`) still writes no record. Nor does the F.2 test `AM5NoResultSupervisors.test_row66_child_unittest_runner_stops_between_tests` (`:2828`). The fix 6 claims of records "from P2CaseRunners" are therefore incomplete (D7-2) | P | O |
| 113 + D20 | I.1 change record: codes, dates, mistakes; pins | C | `programme/CHANGE_RECORD_APG-M11-S1.md`: :41,107,112,115 now say "c9b324eb's numbering"; new "Pin history of the rebuilt tree" v87–v98, v99, v100–v101, v102 (row 68), v103 (fix 6), matching `tools/expected_counts.json` history versions 87–103 (dates and causes checked); fix 6 entry | — | P | P |
| D10 | E.2 fixed values in a test | C | `test_mutation_timeout.py:1583` | — | C | disc. |
| D14 | 1 MiB exactly accepted, +1 rejected | C | `test_mutation_timeout.py:1599` | — | C | disc. |
| D17 | E7 test name matches what it asserts | C | `test_exec_env.py:575`, renamed `test_m8_mutants_control_is_killed_at_tier_1_and_ml01_never_runs` (pins list the new id) | — Note: AM5 App. A planned "the known kill asserted, as the name says"; fix 6 took step 6's other way out, the rename (section 4, D7-8) | P | disc. |
| D21 | Builder-tool docstrings (run_index, check_m8_log) | C | `REPO/builder_tools/current_fix6/run_index_s1.py` `10cb9570…`, `check_m8_log_s1.py` `0cd97130…` (same as step 6, same as `SCR/recovery/btools`) | — | C | disc. |
| D15 | m2 allowance needs M10 info `timeout` | C | `compare_pass2_s1.py` `7c2bd48d…` (unchanged, same in `current_fix6`); `EV6/compare_py31x/m2.txt` allowances printed as "M10 KILLED (by timeout)" | — | C | disc. |
| D16 | b6 compares CONTROL values and causes | C | `EV6/compare_py31x/b6.txt` (`CONTROL lines new=… old=…` per runner, `RESULT b6 SAME`) on both Pythons | — | C | disc. |
| D18 | Build log "same as 11-05" corrected; env 5 names, PID 1, process list, conclusions file | C | Conclusions file for this freeze (row 7); `REPO/build_log/PASS2_BUILD_LOG_RECOVERY.md:307-309` corrects the entry time (D6-6); `EV6/audit_final` 5 names, PID 1 line and process list | — | P | disc. |
| D22 | Privacy: no session-identifier values in the audit | C (packaging) | `EV6/audit_final/*.txt`: no e-mail, no URL, no session-id names; the only UUID-shaped string is the workspace folder id inside paths; the conclusions file writes `<WORKSPACE>` | The package-level search stays at packaging (App. A part 2) | C (pkg) | disc. |
| 106 | AM3-1(e) B.6, K.2, E.2 still identical | C | `EV6/compare_py31x/`: golden, pairs, b6, k2, m2 `SAME`; b6/k2 recorded totals `SAME`, both Pythons | — | C | P |
| 110 | AM4-1/E.2 m2 with the run_one harness, allowances only, both Pythons | C | `EV6/compare_py313/m2.txt` SAME, allowed CA01 (A1) and RI10; `compare_py312/m2.txt` SAME, allowed CA01 and RI13 (A1) and RI10; five slices covering 199 ids; `m2_logs/equiv_1worker.txt` every EQUIV id SURVIVED on both; ids_sha256 as expected | — (timeout-kill counts changed again: section 2, D6-8) | C | O |
| 111 | AM4-1 literal run of M10's m2_mutants.py | C (by waiver) | AM5-1 A substitute: `m2_logs/m10_script_list.txt` on both (exit 0, 199 ids, RI10 at 51); `m2.txt` "M10 script as written: NOT RUN" | Closed by the owner's waiver, not by a literal run | C | O |

**Outside the 65 (as step 6 mapped them):** row 17 C (`test_consumer_exit_codes.py:944`; `LIMIT item=300s` on all 16 new-side
b6/k2 runs on each Python in `EV6/compare_py31x/b6_logs`, `k2_logs`); E.2 C on the comparisons (E point 2 stays partly addressed by the paper); AM5-4's allowance
paragraph: the tool is unchanged (`7c2bd48d…`), so step 6's check stands.

## 2. D6-1 to D6-8

| # | Step 6's discrepancy | Fix 6 | Evidence |
|---|---|---|---|
| D6-1 | Row 68 scanner missed the `_p2sp` alias | Resolved | `tset_start_scan_s1.py` (`9572e0c0…`) reads aliases from each file's imports; `EV6/audit_final/tset_start_scan.txt` lists 102 sites incl. `test_runner_zero_work.py:1197` (`p2b_run`) and the other `_p2sp` sites, all with a limit, plus a leaf table. My independent AST count is also 102, none unlisted. Disclosed as mistake 60 (build log :310-312) |
| D6-2 | Change record pin numbers stale; v102 not named | Resolved | Change record :41,107,112,115 relabelled "c9b324eb's numbering"; "Pin history of the rebuilt tree" lists v87–v103 and describes v102 (row 68); matches `expected_counts.json` history |
| D6-3 | `test_run_start_and_run_end_of_a_mutation_tool` did run_start only | Resolved | `test_runner_zero_work.py:2462`, second half (`reverify` leak: `RUN_ERROR PROCESSES_LEFT run_end`, CLEANUP run_end, item kept, exit 2) |
| D6-4 | REPO held the pre-fix `recorded_totals_s1.py` | Resolved | `REPO/builder_tools/current_fix6/recorded_totals_s1.py` = `55049361…`, byte-identical to `SCR/recovery/btools`; every btools file copied, `SHA256.txt` matches. The old copy and old `SHA256_now.txt` remain in `REPO/builder_tools/step5_recovery/` (superseded; the `current_fix6/README.txt` says so) |
| D6-5 | No audit conclusions file for the freeze | Resolved (for a7f599f9) | `EV6/audit_final/outside_services_conclusions.txt` (= `REPO/evidence_recovery/fix6_evidence/` copy), basis per finding. ee1ce3ec stays without one (superseded) |
| D6-6 | Wrong entry time ("02:45") in the 03:15 correction | Resolved by a later entry | `REPO/build_log/PASS2_BUILD_LOG_RECOVERY.md:307-309` names the 02:15–02:43 entry (line 82). AM5 App. A part 3 still reads "02:45" (authority text, unchanged) |
| D6-7 | Per-test pgids read after the run (204 of 291 `-`) | Resolved | `p2_note_pgids` (`test_mutation_timeout.py:1027`) and `p2b_note_pgids` (`test_runner_zero_work.py:1182`) note pgids during polling. `EV6`: 3.13 506 entries, 3 `-`; 3.12 522 entries, 2 `-`; all the `-` in `test_d14_the_1_mib_boundary_at_tool_level` (short-lived processes) |
| D6-8 | Documents must carry this freeze's timeout-kill counts | Packaging (not yet) | The counts the documents must carry, from `EV6/compare_py31x/m2.txt` (M10 `run_one`, five-slice harness): **Python 3.13: KILLED 196 (tests 157, contracts 0, timeout 39), EQUIVALENT 2, SURVIVED 0, ERROR 1. Python 3.12: KILLED 197 (tests 116, contracts 0, timeout 81), EQUIVALENT 1, SURVIVED 0, ERROR 1.** On ee1ce3ec they were 79 (3.13) and 0 (3.12); AM5 §0 says 83. So for 39 (3.13) and 81 (3.12) of M10's kills the comparison shows only that both sides end KILLED. The counts move a lot between runs of the same M10 code; the documents should say so. The build log's 01:22 entry ("every job's outcome line is the same") gives no counts (D7-10) |

## 3. Counts

| Set | C | P | O | Total |
|---|---|---|---|---|
| 64 items (the 65 without row 42) | 58 | 6 | 0 | 64 |
| Row 42 | 1 | 0 | 0 | 1 |
| All 65 | 59 | 6 | 0 | 65 |

- **Against step 6 on ee1ce3ec (37 C, 28 P, 0 O over 65):** 22 more C, 22 fewer P. 22 of step 6's 28 P items are now C (rows 4,
  7, 11, 12, 21, 22, 30, 41, 42, 46, 51, 52, 68, 71, 73, 85, 91, 96, 99, 113, D17, D18).
- **Against v4 on 303b6414 (56 C, 8 P, 0 O over 64):** 58 C, 6 P, 0 O over the same count of 64. Fewer partly addressed items
  than v4 (6 against 8). The item-level comparison is impossible (v4's list is lost).
- Two C items carry a packaging note (D22, row 111 by waiver as before); one P item (row 75) could be closed at packaging.

**Every item classed P (none O):**

| Item | Now | Step 6 | First mapping | In one line |
|---|---|---|---|---|
| 6 | P | P | P | Secret stop shown in the builder's audit tool, not a T-set successor-tool test as AM5 defines "tool level"; owner's row 6 correction lost |
| 29 | P | P | P | First chain has no timeout-path test |
| 53 | P | P | P | run_contracts "during its cleanup" test accepts INTERRUPTED or SIGNAL_AFTER_COMPLETION |
| 66 | P | P | O | child_unittest_runner and run_m8_tests_s1: SIGINT only |
| 75 | P (packaging) | P | P | Probes for classes 2–6 exist, recorded in the T logs, not in `evidence/audit/`; some descriptors not asserted |
| 121 (+D1) | P | P | O | K.2 per-case test (`:1516`) and one F.2 test (`:2828`) write no identity record |

**Regressions (C at step 6, P or O now):** none.

## 4. New discrepancies

- **D7-1: a test weaker than its name.** `test_runner_zero_work.py:2978`
  `test_rows52_53_run_contracts_s1_sigterm_and_both_signals_during_the_batchs_cleanup`, second half: the signal is sent 0.5 s after
  the leftover marks itself; the assertion at `:2998` accepts `INTERRUPTED signal=… ` **or** `SIGNAL_AFTER_COMPLETION`. After the
  batch's valid result, P.8 allows only `SIGNAL_AFTER_COMPLETION` (the run's last unit, outcome fixed). The case lines kept are not
  asserted. So the test does not show that the signal landed in the cleanup, or that the outcome was kept. The parallel run_faults
  test (`:3040`) asserts the strict form. Keeps row 53 at P.
- **D7-2: the identity-record claim is incomplete.** The change record's fix 6 entry, `FIXPLAN` ("records from P2FaultRunners,
  P2CaseRunners, P2NoResultSupervisors") and the build log (rows 42/121) say the P2CaseRunners tests now write records.
  `P2CaseRunners.test_k2_per_case_on_run_fin_corpus_s1` (`test_runner_zero_work.py:1516`; step 6 named it as `:1488`) writes none;
  nor does the F.2 test `AM5NoResultSupervisors.test_row66_child_unittest_runner_stops_between_tests` (`:2828`) or the three row 4
  tests of `AM5ToolLevelRefusals` (`test_mutation_timeout.py:1383-1397`). Checked in both `EV6` T logs (149 test ids with records;
  these absent). Keeps row 121 at P.
- **D7-3: `FIXPLAN` marks done what is not.** It ticks "51-53/66 interrupts" and row 29. Row 66's "SIGINT only" for
  child_unittest_runner and run_m8_tests_s1 (step 6's words) is untouched: no SIGTERM test of either exists in `tests_tools`. Row 29's
  first chain has no timeout path. The change record states "normal and interrupt paths" correctly; `FIXPLAN` and the build log's
  "Row by row: … 29 …" do not say a path is missing.
- **D7-4: the planted-secret evidence labels a non-unit as a unit.** The STOP line in `EV6/audit_final/secret_stop_demo.txt` (last
  line), its console file and `EV6/progress54.txt` reads "a secret-bearing variable in a unit's environment … :
  control_raw_fork_no_scrub:APG_AUDIT_DEMO_API_TOKEN". The name was found in the unscrubbed control child, not a unit; the tool adds
  the control to the checked list only in demonstration mode (`audit_outside_services_s1.py:153`). The conclusions file (point 2)
  explains this correctly. Also: `progress54.txt` records `rc=0` for this job while the build log says it "stopped with exit 3";
  both hold, because the driver wraps it in `test $? -eq 3` (`driver6_54.sh:40`), but the recorded rc is the wrapper's.
- **D7-5: a pid-order assumption remains in row 11's test.** `test_no_timeout_kill.py:1093` takes the lower pid as the parent
  (`m, g = sorted(ids[1:])`, "M forked first (the lower pid)"). The build log (:296-299) lists "a pid ordering assumption in row
  11's test" among faults fixed while writing. A pid wrap between the two forks would fail the test (a flake risk, not a product
  issue).
- **D7-6: row 21's order rests on an unruled builder reading.** P.5 step 8: "The order of the CLEANUP lines is the order of the
  units' ids." The new test (`test_no_timeout_kill.py:1105`) asserts creation order and shows it is **not** the sorted order of the ids
  (`z_first` before `a_second`). Disclosed in the test, the change record and the build log (:300), but not ruled by the owner. If
  "order of ids" means sorted order, the product does not meet P.5 step 8. This asks more than step 6 said (step 6 asked only for an
  order assertion that can fail).
- **D7-7: AM-5(c)'s run_start rows are not asserted in full.** The table says "every FILE NOT_RUN, exit 2" for run_m8_tests_s1's
  and child_unittest_runner's start. `test_runner_zero_work.py:2913` asserts exit 2, the RUN_ERROR and the CLEANUP record, and only
  the absence of a CHILD line (`:2925`); `:2447` asserts only the parent's `ITEM_ERROR`. Beyond what step 6 named; row 73 is C on
  step 6's terms.
- **D7-8: D17 handled by renaming, not by the planned assertion.** AM5 App. A part 1 planned "The known kill asserted, as the name
  says". Fix 6 renamed the test (`test_exec_env.py:575`) instead. Step 6 allowed either ("a ruling, or a name that matches"), so
  D17 is C; the owner may want to know the plan's action was not taken.
- **D7-9: the finding 13 probes assert less than finding 13 says.** `AM6FindingThirteenProbes`: class 2 asserts `-I` and `-B` and
  the allowlist, not "no `-S`" or "no time limit" (`test_runner_zero_work.py:3119-3121`); class 3 does not assert its 300 s; no probe
  of classes 2–6 asserts a limit. The records are in the T logs only, not in `evidence/audit/` (AM-5(e)). Bears on row 75.
- **D7-10: the build log's comparison with ev5 omits a material change.** The 01:22 entry says "every job's outcome line is the
  same" as on ee1ce3ec. The RESULT lines are, but M10's own `run_one` breakdown moved a lot: timeout kills 79 → 39 (3.13) and
  0 → 81 (3.12); EQUIVALENT 1 → 2 (3.13) and 3 → 1 (3.12); the 3.13 allowances are now CA01 and RI10 (RI13 no longer needed),
  the 3.12 ones CA01, RI13 and RI10. No counts are logged (D6-8 is still open for the documents).
- **D7-11: the "at the RESULT line" check is taken when the line is read.** `p2_run_result_check`
  (`test_mutation_timeout.py:1659`) checks in a reader thread when it reads the RESULT line; `emit` prints that line and flushes just
  before the tool exits, so the check may fall just after exit. Both row 21 tool tests use a SIGTERM-ignoring leftover (a 10 s
  grace), so a cleanup after the RESULT line would still be caught here; with a quickly-dying leftover the check could miss it.
  A limitation to state, not a defect.

**Checked and found in order (no discrepancy):** fix 6's reach (only the seven files above; no product or successor-tool logic;
every product edit the new tests make is inside a temporary copy); the v103 pins, manifest hashes and file hashes agree; the
builder tools that made `EV6` are the ones in `REPO`; the focus logs (`REPO/evidence_recovery/fix6_focus`: 14, 18, 51 and 9 tests,
OK on both Pythons) match the build log; `EV6` T sets were run on the freeze's hash with 0 tree changes; every `EV6` step 5.2–5.4
job ended as recorded in `progress523.txt` and `progress54.txt`.

## 5. Summary

1. Freeze `a7f599f9`, M10 and the authority hashes match. Fix 6 changed only four test files, the pins, the manifest and the record.
2. The T sets ran 727 tests OK on both Pythons, no skips. The comparisons are SAME on both Pythons; historical 100/100.
3. Of the 65 items: 59 closed, 6 partly addressed, 0 open. Over the 64 without row 42: 58 C, 6 P, 0 O (v4: 56 C, 8 P; step 6: 37 C, 28 P).
4. Row 42 is now closed (pgids recorded while alive; records from the fault-runner tests). No item regressed.
5. Still partly addressed: rows 6, 29, 53, 66, 75 and 121.
6. The real gaps: the first nesting chain's timeout path; SIGTERM for child_unittest_runner and run_m8_tests_s1; a test that cannot
   tell INTERRUPTED from SIGNAL_AFTER_COMPLETION; two tests still writing no identity record.
7. Row 6's secret stop is shown in the builder's audit, not in a successor tool; row 75's probes sit in the T logs, not `evidence/audit/`.
8. D6-1 to D6-7 are resolved. D6-8 waits for the documents: 39 timeout kills on 3.13 and 81 on 3.12 (they were 79 and 0).
9. New: 11 discrepancies (D7-1 to D7-11), mostly tests weaker than their names or than claims in `FIXPLAN` and the log.
10. Two requirement readings need the owner: CLEANUP order (creation vs sorted ids, D7-6) and row 6's lost plan correction.

Report finished 2026-11-15 at 01:40 AEDT (clock reads 01:39:45 before sections 3 to 5 were written and 01:40:23 after).
