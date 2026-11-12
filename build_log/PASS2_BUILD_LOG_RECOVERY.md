# APG D14 stage 1, corrective pass 2: recovery build log (BUILDER-EXECUTED: NOT INDEPENDENT)

Times are AEDT (UTC+11), read from the clock at each entry. This log continues the pass 2 build log, which was lost in the
workspace wipe of 2026-11-11. The lost log's entries up to amendment 5 draft 2 survive in records/PASS2_BUILD_LOG.md (from the AM5
review pack); everything after that is restated here from the conversation record and marked as such.

## 2026-11-11

- 15:31 Workspace loss found (recovery/LOSS_RECORD_2026-11-11.md). Nothing had been sent to the owner or to the reviewer.
- 15:48 Recovery authorisation received; filed verbatim as recovery/received/RECEIVED_OWNER_POST_2026-11-11_1548_RECOVERY_AUTHORISATION.txt.
- 15:50 Owner: "Done" (private repository mannykappos/apg-stage1-private created).
- 15:51 Repository attached with push access; cloned (empty).
- 15:58 Branch `main`: the stage 1 tree.
  - Commit 57f778a "base": freeze e4531a35's tree, recovered byte-exact from APG-M11-S1_STAGE1_PACKAGE.zip (131bffa4…33f9).
    The one-word commit message predates the repository; it is kept so the commit is unchanged.
  - Commit 0d1d233: the partial reconstruction of freeze c9b324eb, 1538 of 1555 files byte-exact to c9b324eb's recorded
    s1_sha256; 17 files still to finish (step 2).
- Branch `records` (this branch): the authority, the surviving records, the c9b324eb review pack evidence, builder tools, the
  stop 3 work in progress, the loss record and this log.

### Privacy (amendment 5, discrepancy 22, and the owner's decision of 2026-11-11 "Mask loose, accept in ZIPs")

- Before each push the branch is searched for the user's e-mail, the session and conversation ids, the container id and credential
  shapes. Two loose record files held the conversation id inside workspace paths; it is masked as `<SESSION-ID>`, with both hashes in
  recovery/PRIVACY_MASKING.csv.
- Branch `main` keeps logs/m81/baseline/00_hashes.txt unchanged: it is part of the immutable M10 baseline and holds the conversation
  id inside paths (2 lines). Masking it would change an immutable file and break every byte-exact comparison. It sits in the owner's
  own private repository; it is listed here, and will be listed in PRIVACY_CHECK.txt at packaging, as accepted under the owner's
  decision (inside the freezes and M10).
- Commit messages carry the `Co-Authored-By` line only. The session-link trailer the tooling suggests is left out, because it would
  write the session id into the repository, which the privacy rule forbids.

### Mistakes (numbering continues the lost log: 36 to 48 are restated in the documents)

- 49. The builder kept the whole pass 2 workspace on one disk with no off-box copy, although the session had already restarted four
  times. The wipe destroyed it. Corrected: every commit and every finished evidence step now goes to this repository, and checkpoint
  zips go to the owner at the end of steps 3, 5 and 7.
- 50. At 16:32 the owner wrote "Done" again. The builder's condensed working notes had left out the 15:51–15:58 attach and pushes,
  so the builder called the repository attach a second time instead of checking the repository first. The tool replied that the
  repository was already attached; nothing was pushed, changed or duplicated. Owner: "What is going on here we already did this".
  Corrected: the repository's branches are checked first at every resume.

### Step 2 (2026-11-11, from 16:33): the last 17 files of c9b324eb

- Finding: the stop 3 work-in-progress diff was taken against the corrective pass 1 freeze, not e4531a35. In the 14 AST successor
  mutation tools (m3 to m7, m73_store, m91, f67, f671 to f674, mie, mie11) it applied by context, so their corrective pass 1 change
  (decision (c), owner 2026-11-02 14:24: `evkit.list_mutants`) was missing; child_unittest_runner lacked decision (f) (`verify_auif`).
- Exact recovery tried and abandoned: about 25,000 likely forms of the decision (c) lines in m7 were checked against the pass 1 git
  blob id (e412676, from the diff header) and against c9b324eb's SHA-256; none matched.
- Rewritten after the loss, not recovered (recovery authorisation, rebuild rule), from the change record and evkit (c9b324eb-exact):
  - the 14 tools: `ms, rc = E.list_mutants(TOOL, mutants)`, refusal returned before any work; the --batch refusal now names the
    listed mutants (`ms`) instead of listing them a second time (same ids);
  - child_unittest_runner: passes the checked APG_AUIF_ROOT copy as `verify_auif` to `evkit.tests_runner_main`.
  - Commit cba5c5d on main.
- Pins rebuilt on the rebuilt tree (commit 82b82f1): v87 to v98, the 19 wrappers re-pinned with the adopted W-1B files (12 changed:
  f67, f671 to f674, m3, m7, m71, m72, m73, mie1, mie1_1, the same 12 as c9b324eb's v98 to v109; 7 unchanged); v99, the test_files
  entries of the 10 tests_tools files (613 tests, as c9b324eb). Not byte-identical to c9b324eb's v111: the version numbers, dates and
  reasons differ.
- Manifest regenerated with make_s1_manifest.py (D1 input rebuilt from the e4531a35 manifest's d1 rows; M10 list from the verified M10
  archive): the same 184 rows in the same order; only 63 s1_sha256 values changed.
- Result: 1538 of 1555 files byte-identical to c9b324eb; 17 rewritten or regenerated (the 14 tools, child_unittest_runner, the pins,
  the manifest), each to be disclosed.
- 16:39 full suite started on 3.13 then 3.12 (resumable driver, one job per file).
- 51. The builder committed two __pycache__ folders in 82b82f1 (`git add -A` after a pin run that wrote bytecode). Removed in 42305fb;
  `__pycache__/` added to the clone's local exclude.

### Step 3 (2026-11-11, from 16:41, written while the step 2 suite runs; nothing of it run yet)

- Branch `step3` (from main 42305fb), pushed at every commit.
- evkit: S15, S16, S17 (b) rewritten from the 12:47 rulings of 2026-11-08 (commit 2a2476b). S17 (a) has no code change.
- Tests rewritten from amendment 5 Appendix A part 1 and the option A answer of 2026-11-09, not recovered (the 04e9f2f2 and
  303b6414 test code was lost): test_no_timeout_kill (rows 4, 6, 11, 12/S15, 15, 19, 21, 23, 71, 72, 77, 90, 91, 92, 96, 99, 101,
  121), test_mutation_timeout (rows 4 tool level, 41, 50, 51 to 53, D10, D14, 121), test_runner_zero_work (rows 22, 25, 30, 31, 36,
  42, 46, 51 to 53, 55, 56, 59, 60, 69, 73, 79, 81, 85, 95, 97, 98, 100, S16), test_consumer_exit_codes (rows 34, 57, 62, 63),
  test_exec_env (rows 22, 29).
- Row 6: the 12:47 plan correction for rows 6 and 17 was lost with the issue record; row 6 is written as "the secret never reaches a
  unit or a record", row 17 has no new test. Both are disclosed.
- Still to write: rows 66 and 83, discrepancy 17, the change record, then the focused runs on both Pythons.
- 17:24 Step 2 suite on Python 3.13.18: all 10 tests_tools files OK, 613 tests (51+86+39+16+12+66+4+180+34+125), as c9b324eb. 3.12 started.
- 18:13 Step 2 suite on Python 3.12.3: all 10 files OK, 613 tests. Step 2 complete; logs in evidence_recovery/step2_suite (session id masked). Step 3 focused checks start.
- 18:14 to 18:48 Step 3 focused checks (BUILDER-EXECUTED: NOT INDEPENDENT). First run on 3.13: failures, every one a fault in the
  new tests, none in the code under test (no logic changed): row 6 output order; sabotage outcome names (CAUGHT/MISSED) and a failed
  control's exit 3 (rows 41, 51 to 53); the row 30 unkillable mode name, then the test's own read waiting on a pipe the planted
  process kept; the S16 leak first planted in the check's own tool file, which the CHECK identity pins (moved to the module it
  imports); row 55 assumed the signal lands in G01; the run_start refusal names the selection; row 29's record precedes the RESULT
  line; row 62 first asserted a rule K.3 does not make (rewritten to dispatch by kind and version). Each fixed test rerun on 3.13:
  OK. 3.12, the whole focused set: OK (52 + 5 + 20 + 32 + 16 + 4).
- 18:49 Pins v100: the five changed tests_tools files; 700 tests in tests_tools (303b6414 had 713; the rewritten tests are not the
  lost ones, to be disclosed). Manifest regenerated (cefafbae…621c); the first attempt, on the worktree, refused because a worktree's
  .git is a file; regenerated on an export of the branch.
- 18:50 Step 3 full suite started on both Pythons (branch step3, e1b79ac).
- 19:43 Step 3 full suite, 3.13: 9 files OK; test_runner_zero_work 165 of 166 OK, 1 FAIL: test_row55_an_interrupted_wrapper_group.
  The signal landed between G01 and G02 (G01 finished within the test's 0.3 s delay), so no group was INDETERMINATE: correct
  behaviour, a timing race in the new test (not a defect, no logic change). Fixed: the copy holds G01's child (marker, then sleep), so
  the signal always lands inside G01 (58b3f81; pins v101; manifest 8809e511...67b6, be0c27b). Rerun on 3.13: OK. The 3.12 suite
  continues on e1b79ac; test_runner_zero_work is then rerun on both Pythons on be0c27b.
- 19:36 Separate work for the owner (not stage 1): the APG Data Readiness change request draft (a Claude doc) and its GPT/Gemini
  review pack were sent.
- 20:42 Step 3 suite on 3.12 (e1b79ac): all 10 files OK, 700 tests. 3.13: 699 OK + the row 55 race (fixed). Rerun of test_runner_zero_work on both Pythons on be0c27b started. Evidence in evidence_recovery/step3_suite.
- 21:08 Rerun of test_runner_zero_work on be0c27b (BUILDER-EXECUTED: NOT INDEPENDENT): Python 3.13 166 tests OK (20:42 to 20:55),
  Python 3.12 166 tests OK (20:55 to 21:08). With the 20:42 suites, step 3 is 700 tests OK on both Pythons on be0c27b (the only file
  changed after e1b79ac is test_runner_zero_work.py, rerun here). Logs in evidence_recovery/step3_suite (session id masked).
- Mistake 52 (disclosed): at about 19:36 a scratchpad path containing the session id was pushed in data-readiness/build_gap.py (the
  separate data readiness work, not stage 1). Found in my own check; the path was replaced and the branch squashed and force-pushed,
  so no commit on GitHub now carries it. It was on GitHub for a short time.
- 21:00 to 21:30 Separate work for the owner (not stage 1): revision 2 of the data readiness change request written after the GPT
  and two Gemini reviews (a new Claude doc; the CSVs on the data-readiness branch).
- 21:32 Step 3 merged into main (fast-forward to be0c27b). Step 3 checkpoint zip next, then step 4.
- Mistake 53 (disclosed): two times written before reading the clock: the merge entry above said 21:35 (the clock and the commit
  show 21:32) and the checkpoint PRIVACY_CHECK.txt said 21:40 (made at 21:33). Both corrected before sending.
- 21:33 Step 3 checkpoint zip built (tree be0c27b, records), privacy check: one accepted immutable hit (logs/m81 baseline),
  hostname false positives, nothing else.
- Mistake 54 (disclosed): while pushing the data readiness rev 2 files, a git worktree command failed and the following copy and
  commit ran in this records checkout (local commit 534af9c, rev2 files). Not pushed: the remote records branch stayed at e2437e2.
  Undone with a reset to e2437e2; the files were then committed on the data-readiness branch as intended. Cause: a cd joined with &&
  under set -e does not stop the script when it fails; later scripts use set -euo pipefail and separate cd lines.
- Mistake 55 (disclosed): in the same script the session-id search for the rev 2 re-check pack used a wrong value (the folder name
  "scratchpad", not the session id), so that check proved nothing. Rerun with the right value on the pack and the branch: no hits for
  any searched pattern. The step 3 checkpoint check used the right value (its one hit is the accepted M10 baseline file).
- 21:38 Step 4 (BUILDER-EXECUTED: NOT INDEPENDENT): freeze of main at be0c27b with builder_tools/freeze_s1.py (recovered byte-exact from
  the e4531a35 package), built twice into separate folders: byte-identical, 1555 files, APG-M11-S1.zip SHA-256
  67203973d4db8b361c4537b9a4affd3e323fb5c58f9c06c16fa74ae871d57aec (303b6414 is not reproduced: the tree differs, as disclosed).
  Sanity check, frozen_compare_s1.py against APG_M10_CODE_AND_DATA.zip (bd5c592a...): changed 3, identical 1463, new 89, problems 0;
  73 successor tools, every M10 original byte-identical. The ZIP is in freezes/be0c27b; the two hashes and the comparison CSV are in
  evidence_recovery/step4_freeze. Step 5 (the full evidence, AM5-6 order) next.
- 21:41 STOP before step 5 (recovery authorisation: stop if anything would need a changed claim). B.6 and K.2 (rows 43 and 61) compare the
  new freeze's 111 plant verdicts and 386 case verdicts, item by item, with the runs of freeze d5f87d6b. d5f87d6b was lost with the
  workspace and cannot be rebuilt (only e4531a35 survives byte-exact); its per-item verdicts were never kept outside it: the review
  pack's b6.txt and k2.txt hold only per-runner counts, status, exit, controls and CONTROL lines. Any b6/k2 run now changes what rows 43
  and 61 can claim. Reported to the owner with options; nothing in step 5 runs until the owner answers. The other step 5 tools
  (AM5-3 allowance in compare_pass2_s1, discrepancies 7 and 21, the row 68 check, the names check) are specified in amendment 5 and
  will be rewritten from it, disclosed as rewritten. Spot check: discrepancies 10, 14, 17 are in the step 3 tests.
- 22:48 (11-11) Step 5.1 started on be0c27b (driver ev5/driver51.sh). Before it, builder-tool work for step 5 (outside the tree):
  compare_pass2_s1.py gained the AM5-3 A1 allowance (rewritten from AM5-4's paragraph; the 303b6414-era change was lost); the
  discrepancy 21 docstrings of run_index_s1.py and check_m8_log_s1.py; audit_outside_services_s1.py rewritten for discrepancy 7 (children
  through run_unit and run_forked, docstring); new recorded_totals_s1.py (the owner's B.6/K.2 answer of 22:47) and tset_start_scan_s1.py
  (row 68). Owner's answer filed: B.6/K.2 "e4531a35 + recorded totals"; step 5.1 to start.
- About 22:58 (11-11) Finding while writing the row 68 scan (a dry run on the work tree, low priority, during T01-T03): 83 process
  starts in tests_tools; 10 with no explicit time limit, all helper processes the tests plant (5 already in c9b324eb's tests, 5 from the
  step 3 rewrite); e4531a35's 28 starts all have one. Asked the owner. The question waited until 06:31 on 11-12.
- Container restart: boot 2026-11-12 06:31:32 (uptime -s); the disk survived (unlike 11-11). The step 5.1 run had stopped writing at
  23:21 during T08 (cause not determined: no log line after that). Nothing was evidence yet.
- 2026-11-12 06:32 Owner's answer: "Add limits, then refreeze". The be0c27b step 5.1 run is abandoned (kept as ev5/run_sets/py313_T, not evidence).
  Next: limits on the 10 helper starts (tests only), focused checks on both Pythons, a new freeze built twice, step 5.1 restarted.
- 06:33 to 06:34 (11-12) Row 68 change, tests only (branch row68): a time limit on the 10 helper starts (wait(timeout=60), run(...,
  timeout=60), a bounded cleanup in a finally for two Popen helpers, signal.alarm(120) in the row 77 grandchild); no assertion
  changed, no test added or removed (commit 417cafb). Pins v102 by evkit.update_pins on the two files (ids and counts unchanged,
  a57faba); manifest regenerated on an export (e9e11d9, 34e722db...). Row 68 scan (dev run, tset_start_scan_s1.py): 83 sites, 83 with a
  limit. The scan's alarm pattern was widened to the test's alias _sig before this count (builder tool).
- 06:34 to 06:40 Focused checks (BUILDER-EXECUTED: NOT INDEPENDENT), fresh exports of row68: test_consumer_exit_codes 91 OK and
  test_no_timeout_kill 52 OK on Python 3.13 and on 3.12. Logs in evidence_recovery/row68_focus (session id masked).
- 06:41 main fast-forwarded to e9e11d9. Freeze of e9e11d9 built twice, byte-identical, 1555 files, APG-M11-S1.zip SHA-256
  ee1ce3ec4be1a76482595688cfd9b41910fa26f4c9fe9a936f8971e86b5e0735; frozen_compare against M10: changed 3, identical 1463, new 89,
  problems 0. This supersedes be0c27b (67203973..., kept in freezes/be0c27b, no evidence made on it). Step 5.1 restarts on it.

## 2026-11-12 step 5.1 (T/W/M sets) on freeze ee1ce3ec (e9e11d9) - BUILDER-EXECUTED: NOT INDEPENDENT
- Tool note: the step 5 tools were rewritten after the workspace loss (AM5-3 A1 allowance limited to CA01-float-allowed and RI13-input-aliased,
  M10 ('KILLED','timeout') with successor EQUIVALENT only; discrepancies 7 and 21 handled as recorded earlier). run_index_s1.py always returns 0,
  so the driver does not gate on it: every set's exits are checked by hand from run_index.csv.
- 06:41 to 07:31 py313_T: 700 tests, every exit 0, tree changes 0.
- 07:31 to 08:27 py313_W: 19 wrappers, every exit 0; wrapper_check: every group OK or OK_WITH_EXCLUSIONS, checker_problems 0 on all 19,
  totals FILE 454 / CHECK 103 / EXCLUDED 100, non-passing group lines none; tree changes 0.
- 08:27 to 08:39 py313_M: exit 0; m8_check "as expected (exit 0, no checker problem, 79 KILLED, 3 EQUIVALENT: MI-36 MI-39 MD-02): True";
  82 mutants, survived 0, indeterminate 0, item_errors 0; tree changes 0.
- 08:39 py312_T started.
- 08:39 to 09:27 py312_T: 10 run_index rows, every exit 0, tree changes 0.
- 09:27 to 10:21 py312_W: 19 wrappers, every exit 0; wrapper_check: checker_problems 0 on all 19, totals FILE 454 / CHECK 103 / EXCLUDED 100
  (identical to py313), non-passing group lines none; tree changes 0.
- 10:21 to 10:32 py312_M: exit 0; m8_check "as expected (exit 0, no checker problem, 79 KILLED, 3 EQUIVALENT: MI-36 MI-39 MD-02): True"; tree changes 0.
- 10:32 STEP51 DONE. Step 5.1 found nothing unexpected on either Python.
- 10:32 driver523 started (steps 5.2 and 5.3: golden, pairs, b6 and k2 against e4531a35 with the recorded totals, then m2), one job at a time.
- 10:32 to 10:36 step 5.2 (BUILDER-EXECUTED: NOT INDEPENDENT): golden SAME, pairs SAME, b6 SAME (111 items vs e4531a35), k2 SAME (386 items vs
  e4531a35), b6 and k2 recorded totals SAME (d5f87d6b and c9b324eb), on Python 3.13 and on 3.12. No per-item difference.
- MISTAKE 56 (disclosed): recorded_totals_s1.py printed a hard-coded label "be0c27b" for the new side, left from when be0c27b was the freeze. The
  numbers compared are this run's (driver523 reads freeze5 = e9e11d9 / ee1ce3ec); only the label is wrong. Fixed the label (line 42, now
  "e9e11d9 (freeze ee1ce3ec)"); the old file is kept as ev5/recorded_totals_s1.py.before_label_fix. The four totals jobs (b6tot and k2tot on both
  Pythons) will be re-run after step 5.3 finishes, one job at a time, so the evidence carries the right label; the wrong-label outputs are kept.
- 10:36 STEP52 DONE; step 5.3 (m2) started: m2list_313 "m10 --list: exit 0, 199 ids, RI10 at 51, m2_mutants.py as expected: OK".
- 11:16 Defect candidates raised by GPT's check of the data readiness revision 3 (outside the D14 item list), logged at the owner's
  instruction ("Log them, stage 1 continues"); no code change, step 5 continues. Both files are byte-identical in M10 and stage 1
  (rules_commercial.py ffbe9d122d29, rules_ops.py cd407e323b84):
  DC-1 apg/det/rules_commercial.py r04b_instruction: an instruction whose linked_variation_ref names any stored variation is silent, whether
  or not that variation is usable (held, quarantined or rejected variations also suppress the finding).
  DC-2 apg/det/rules_ops.py LAB (line 142): a missing overtime_hours is counted as 0 (the det intake only warns on it), so a week with unknown
  overtime is assessed rather than treated as not assessable.
  To be raised as their own change request; not stage 1 regressions.
