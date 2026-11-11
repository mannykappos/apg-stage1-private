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
