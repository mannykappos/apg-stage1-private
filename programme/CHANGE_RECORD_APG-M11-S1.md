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

## What changed
`programme/APG-M11-S1_MANIFEST.csv` holds the exact list:
- the 89 D1 lines;
- the one supplementary line;
- this record;
- every file whose hash differs from M10.

The base is APG-M10 (`bd5c592a198581808237e5a5e563aa15c3be977d3f3e0d68511499d755435192`), which is unchanged.
