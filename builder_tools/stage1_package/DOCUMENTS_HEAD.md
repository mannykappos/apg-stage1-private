# APG-M11-S1, successor stage 1 (the evidence tooling): stage 1 documents

**BUILDER-EXECUTED: NOT INDEPENDENT.** Everything in this file and in the package is builder evidence, produced and checked by the builder. It is not independent evidence. It accepts nothing, closes no finding, EDR or CF item, and makes no production-readiness claim. Stage 2, stage 3, Part B and final verification are not authorised and were not started.

## 0. Identity

| Item | Value |
|---|---|
| Base | APG-M10, `APG_M10_CODE_AND_DATA.zip`, SHA-256 `bd5c592a198581808237e5a5e563aa15c3be977d3f3e0d68511499d755435192` (never written to) |
| Stage 1 frozen ZIP | `APG-M11-S1.zip`, SHA-256 `{ZIP_SHA256}`, 1,555 files under `APG-M11-S1/`, built deterministically from git commit `cd840c0a6b7dd4530e42ea5d8ca18d9df277146b` (`tools/freeze_s1.py`: sorted names, fixed timestamps; built twice, identical bytes) |
| In-tree manifest | `programme/APG-M11-S1_MANIFEST.csv`, SHA-256 `{MANIFEST_SHA256}` |
| Pins | `tools/expected_counts.json`, version {PINS_VERSION}, every change with a change record |
| Pythons | 3.13.16 (`/usr/bin/python3.13`, SHA-256 `a35753ccb97941cce1467786cce892e608141f09d717188a3235d4f51a754446`) and 3.12.3 (`/usr/bin/python3.12`, SHA-256 `e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f`), as recorded in every wrapper and mutation log (`ENV version`, `ENV interpreter_sha256`; the unittest logs of the T sets carry no `ENV` lines) |

## 1. Authority

| Document | Posted by the product owner | SHA-256 |
|---|---|---|
| Build authorisation, draft 3 | 2026-10-31 11:20 | `9af3151fb6e034b2e9d6504b04e6066d5b0733ae89cf0e852a600e9682148197` |
| Part A decisions D-1 to D-9 | 2026-10-31 11:04 | `e8757f6e61df02f1b57ad27bda2db1ff452ccb3cc95317fef87fffc7b429beaa` |
| Amendment 1 (89 D1 rows) | 2026-10-31 13:18 | `9e76ee37f299b94677d21925d375da8cc2d307916aa78d0c7145c987566d357f` |
| Amendment 2 (`tests_m8/test_m8_boundary.py`) | 2026-10-31 13:18 | `b67192d9270e8ae38dd34d9c1da6e0f55d7f8047b19520f033c28dc5fe85c853` |
| Decisions K-1, R12 (a), F-55 | 2026-10-31 13:18 | `660525fc51786a1bbe1a7daa6819a0ff6b1e1fa7d1d88159ba9e7d5859c58082` |
| Decisions M8-T (a), E-1 (i), M-1 (a), W-1 | 2026-10-31 20:57 | `a857445999e51d4af2595d0270cb6b90f607b6f51103f089c0ce6c34d843be91`; W-1 draft 2 `21728a940907d061efcfac4c913eea517b51e4e55ce72a6a506490dc2c460951` |
| Decision W-1A | 2026-11-01 06:22 | `396e268ff3e5882f4ed26df0c971bb42c8923ebbf0e219ac84655be7bf56488d` |
| Decision W-1B, option (a) | 2026-11-01 11:32 | `f45619e38f55d52cade909845dc9d4232db49d8bb3a4e0b4a84aa82e5094b773`; `wrapper_groups_v3.csv` `f559ec57a50a045c36e8faedb9d1574315fb45c023046287264568fbe2fbb7c9`; `W1_EXCLUSION_LIST_v3.csv` `266eea0dd870452921a19b52bff2c64eb9aa0b42a5f579ecffba33da9a28e479` |

Every post is filed verbatim with its decision record in the records folder; each was compared word for word with the prepared statement. The reviewer's document reviews are filed beside them; they were document and decision reviews, not technical acceptance.

## 2. Findings corrected, and the test that proves each (authorisation §4.1)

Each block's "Tests that prove it" (`T_tooling.md`, latest revision) is implemented in the 10 `tests_tools` files. Where the plan gives an M10 behaviour, the test runs M10's own tool (byte-identical in the tree, DP-1.2 (B)) in a temporary copy and asserts the defect, then runs the successor and asserts the fix. All 10 files passed on the frozen ZIP on both Pythons (section 3: 410 tests per Python). The bullet-by-bullet mapping, with line numbers, is `evidence/static/plan_test_mapping_RECHECK.md` (a second, read-only reading of the tests against the plan; its remaining points are dealt with in section 9).

| Block | Defect on M10, shown by the test's M10 half | Fixed on stage 1, shown by the successor half | Main tests |
|---|---|---|---|
| P1-F5 | `run_m2_tests -q 'nomatch_*.py'`, `mut_runner` with no names, `run_contracts --suite nope` exit 0 after zero work; `mut_runner test_nope.py` exits 1; a child's exit 2 is a kill in all 15 mutation tools; M10 `mut_runner` prints nothing | exit 2 with `RUN_ERROR` and a `RESULT v=2` line the checker accepts; a child's evidence error is that mutant's `ITEM_ERROR`, exit 2; per-file counts reconciled against pins; fail-fast and full modes | zw `SelectorsThatDoNoWorkExitTwo` 01-03; mro (all 9); cec `ConsumersOfAChildEvidenceError` (15 tools) |
| P1-F6 | `APG_ROOT` redirects `run_m2_tests` and `tests_m8/_auif.py` to a decoy; a runner started without `-I`, with `site`, with a decoy `sitecustomize` or user-site `.pth`, or from a decoy working directory, runs and passes | `APG_ROOT` removed; the decoys never run; refused without `-I -S` or outside the root (`ENV_NOT_ISOLATED`, `ENV_SITE_LOADED`, `ENV_CWD`); every child of `run_m8_tests_s1`, `m8_mutants_s1`, `sabotage_m10_s1` and `run_regression_m10_s1 --step R07` starts `-I -S` and imports the real `apg` | ar `ApgRootRedirect`; ee `RunnerLevelStartChecks`, `ChildrenStartIsolated`, `StartChecksInAChild` |
| P1-F7, AX-4, P4-B13, P5-S08 | every mutation tool counts a hanging or crashing child as a kill (exit 0); f672's second timeout too; the census finds the pattern in the 12 tools with their own runner | timeout `INDETERMINATE cause=timeout` with its `TIMEOUT` measurement, exit 3; crash `INDETERMINATE`, exit 3; genuine failure `KILLED`; failed start control: every mutant `NOT_RUN`, exit 3; census clean on all 16 successors | mto `ToolLevelTimeoutCrashKill` (60), `ToolLevelM8` (5); ntk `Census` |
| P2-B8 | `run_fin_corpus --only NOPE`, `run_m3_contracts --suite nope`, `m3 --only ZZ`, `m4 --ids NOPE` exit 0; `run_m4_all` with a zero-work runner reports PASS for its 13 test groups; empty M3 faults and ingest corpus "pass" | exit 2 each; the wrapper group `ITEM_ERROR`, exit 2; empty lists refused against the pins | zw selectors 04-07, `WrapperWithAStubTestRunner`, `test_an_empty_m3_fault_list_and_an_empty_ingest_corpus` |
| P2-S3, P3-S01, P4-S14, P5-S07 | m3, m4, m5, m6, m7, m91 die with a traceback when `mutate` raises | stopped in the preflight (every mutant `NOT_RUN`, exit 2), or a worker exception is that mutant's `ITEM_ERROR` with every other line kept | mes (all 4) |
| P3-B03 | `m5 --ids DT-x-999`, `--ids <valid>,NOPE`, `--only QQ`, `run_det_corpus --only NOPE` exit 0 | exit 2 each | zw selectors 08-10, 14 |
| P3-B04 | 8 contract and corpus runners run a fake harness from the candidate path and report `ALL … CASES PASS` | refused (`CANDIDATE_SHADOWS_TRUSTED`), also for `tools`, `mie`, `apg_ui`, `tests_m10` | hi `RunnerLevel` |
| P4-B15 | `m6 --ids NOPE`, `--ids <valid>,NOPE`, `run_mkt_corpus --only NOPE` exit 0 | exit 2 each | zw selectors 11-13 |
| P4-B17 | `run_m6_all` with a zero-work runner reports PASS for its 20 test groups | group `ITEM_ERROR`, exit 2; further stubs: zero tests against the pin 2, child exit 3 → 3, FAILED → 1, contradicting exit → 2; a child killed by a signal → `INDETERMINATE`, 3 | zw `WrapperWithAStubTestRunner` |
| P5-B06 | `run_m7_all --group 0` runs the LAST group; `--range 5-3` and `m7 --ids NOPE` exit 0; `sabotage_m7 --only S99` exit 0 | exit 2 each | zw selectors 15-17, `test_sabotage_unknown_id…` |
| P7-B2 | M10 `run_m8_tests` honours a set `APG_ROOT` | ignored; `m8_mutants_s1` controls pass and ML-01 is still killed with the tiers inside the mutated copy | ar `test_m10_run_m8_tests_imports_the_decoy`, `test_successor_run_m8_tests_ignores_apg_root`; ee `ChildrenStartIsolated` |
| P7-B3 | `run_m8_tests --file`, `sabotage_m8 --only S99`, `sabotage_m10 --only Z99`, `m8_mutants --batch 0/4`, `run_m8_all --range 5-3` exit 0; `run_m8_all --group 0` runs the last group; m8 exits 1 on a timeout and 2 on a failed control, and counts a crashed tier as a kill | exit 2 each, with `RESULT`; m8 timeout `INDETERMINATE` exit 3, crash `INDETERMINATE`, failed control exit 3, failing end control keeps the mutant line, exit 3 | zw selectors 18-23; mto `ToolLevelM8` |
| E1-C8 | M10 `mut_runner` prints nothing, for one file and for the eight C8 files | the pinned counts per file, reconciled | mro `test_the_eight_c8_files` and others |
| E1-RI10 | M10's M2 list, read from the source, has RI10's target 0 times; M10 starts its workers and reports the ERROR afterwards | the corrected list has every target once; with a target removed the run stops in the preflight (199 `NOT_RUN`, no worker directory; two removed → two `RUN_ERROR` lines) | mtg `EveryTextListOnTheSource`, `PreflightFailClosedAtToolLevel` |
| T-0 (evkit contract, §4.3 to §4.5) | — | the checker's rejections, exit precedence, controls, preflight before any item in all 29 mutation and sabotage tools, sabotage timeout/crash/failed-control in all 13 sabotage tools, a child in the wrong mode refused | cec, mtg `Preflight`, mto `Controls`, `PreflightBeforeAnyItem` (29), `SabotageToolLevel` (53), cec `AChildInTheWrongModeIsAnItemError` |
| P1-M1 | see section 6 | | `d14/tools_tests/test_d14_record_postgresql.py` |
| Amendment 1 (T-K, T-F), K-1, R12, F-55, M8-T, M-1, W-1, W-1A, W-1B | as recorded in each decision | built as decided | zw `WrappersW1A`, `WrappersW1B`, `M8CallerModeAndTiers`, `CasesRunners`, `SabotageAndFaultRunners`; cec `WrapperResultW1`; mto `BaselineOptionW1A`; ar `BoundaryManifest`, `RegressionManifestW1A` |

Three successor defects were found while these tests and this report were written, and were fixed (section 9, mistake 1):
- a child reporting a mode other than its pinned one was accepted by its caller;
- a wrapper group whose child exited normally without its `RESULT` line was `INDETERMINATE` rather than `ITEM_ERROR`;
- some runs a successor refused before any work printed no `RESULT` line. Every such refusal now ends with its `RESULT` line (zw `RefusalsEndWithAResultLine`).
