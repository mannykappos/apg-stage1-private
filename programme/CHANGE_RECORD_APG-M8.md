# Change record APG-M8: APG as a module client of the frozen AUIF rev13 (synthetic data only)

| Field | Value |
|---|---|
| Release | APG-M8, a separately versioned, additive release. It is the delivered APG-F67.4-R2 package (ZIP SHA-256 `3e474b4671c846e7581ccb6d1ca27a6fe339f03a2275bf9ad7f753b0097a516e`, 1,222 files; every file hash in `regression/m8/R2_MANIFEST.sha256`) plus the additions below. The APG-F67.4-R2 ZIP and every earlier ZIP are not modified or replaced. |
| Status | **Builder-implemented and locally tested; not accepted.** No independent verification has taken place. Not a release acceptance, not production approval, not proof of integration with a real Anchor Engine. |
| Authority | The product owner, 2026-10-20: "AUTHORISE M8" (the APG integration with the frozen AUIF rev13 module interface, synthetic data only, baselines first), and, after the builder's stop report on finding M8-F1, "Authorise M8 continuation under DEV-M8-01 as written". |
| Dependency | AUIF rev13, unmodified: ZIP `61748ddeba21e8c1d71b56bd0d3ad7a376ea051f4ae6fbe56c6464c0de76e070` (from handover archive `5dad8d27…`), manifest tree `9fbc5de7…` (248 files), core tree `74cec87afd167601fd4f260ec02b6f3c16121355b2d5c29767b5f1d3273bf93d`. Carried as the ZIP only (`third_party/auif_rev13/`), verified by hash before every run. |
| Deviation | DEV-M8-01 (finding M8-F1): FIELD mappings write `<Type>.<attribute>`; ENTITY mappings and the model keep `module.apg.<Type>`. Recorded as CF-47 and I-135; the AUIF fix that would end it is CF-50. |
| Gates still open | EDR-05, EDR-06, EDR-18, EDR-39, EDR-40, EDR-41 and every other open EDR and CF item; CF-41 unchanged. The construction definitions are PROPOSED, never LOCKED. The AUIF-side Engine work remains with Amir. |

## 1. Baselines (before any adapter code; `logs/m8/baseline/`)

All archive hashes matched. AUIF rev13 on Python 3.12.3 and 3.13.16 alike: verify_package 248 files, 0 mismatches (also after the tests); static checks clean, core tree as specified; core 410 OK, extensions 343 OK (20 skipped: the real-Governor tests, as rev13's own evidence records), accelerator 418 OK. APG-F67.4-R2 unchanged, on 3.13 and 3.12 alike: M3 import tests 224, whole suite 2,583 in 117 files one file at a time, R2 self-check 5 of 5.

## 2. The stop and the deviation

Building on rev13 showed that AUIF cannot translate any field into a MODULE-namespace concept (finding M8-F1, `auif/translation.py` line 152). The builder stopped and reported (stop report, 2026-10-20) with a reproduction using AUIF alone. The product owner authorised DEV-M8-01. `tests_m8/test_m8_dev01.py` pins both: the contract form still fails on rev13 (that test fails on purpose once AUIF is fixed: regenerate the packs then, under a new authorisation), and the deviation's form gives valid module objects, while invalid input is still rejected and the path fails closed.

## 3. What was added

| Part | What |
|---|---|
| `apg_auif/dependency.py` | Verifies the AUIF ZIP (pinned hash and sidecar), extracts it to a private temporary folder, runs AUIF's own manifest check and core tree hash, then makes AUIF importable (at the end of `sys.path`). |
| `apg_auif/layout.py` | The 26 Builder Zero files the financial core and detection read, in M3 load order, with the same templates and source identities; 15 synthetic integrations (one APG source in one folder each). |
| `apg_auif/definitions.py` | The construction definitions (MODULE namespace, PROPOSED), built from the APG templates, intake rules and a relationship table checked against the code that follows each reference; and the AUIF canonical model (PROPOSED). |
| `apg_auif/pack.py` | The CANDIDATE synthetic translation packs: one-to-one IDENTITY mappings, read-only, unmapped columns REJECTED, DEV-M8-01 form only. |
| `apg_auif/module.py` | The APG module on AUIF's `BaseModule`: receives entities, observations, events, states, errors; never acts outward; never silent on its own failure. |
| `apg_auif/intake.py` | Deliveries → APG records with lineage, under the unchanged M3 mapping and delivery rules; a sync batch applied whole or not at all. |
| `apg_auif/gate.py`, `apg_auif/assess.py` | "Cannot assess" with reasons; the assessment runs the existing calculations only when the gate allows, and withdraws the result if what the gate reads changes during the run. |
| `apg_auif/lineage.py` | The lineage checks used by the no-laundering tests. |
| `apg_auif/client.py`, `apg_auif/loaders.py` | An AUIF runtime for APG on AUIF's reference ports (no real system, credential, Engine port, Governor or outbound action); loaders with the M3 loaders' signatures. |
| `auif_m8/` | The generated configuration (definitions, model, 15 packs) and the path-equivalence declarations. |
| `tests_m8/` | 154 tests in 14 files (and three helpers: `_auif.py`, `synthetic_events.py`, `__init__.py`). |
| Tools | `make_m8_config.py`, `run_m8_tests.py`, `run_m8_all.py`, `m8_mutants.py`, `sabotage_m8.py`, `run_regression_m8.py`, `make_m8_registers.py`. |

## 4. Evidence (run by the builder; logs in `logs/m8/`)

| Check | Command | Result |
|---|---|---|
| M8 tests, one file at a time | `tools/run_m8_tests.py` | 154 tests in 14 files, every file at its expected count, AUIF verified before and after; Python 3.13.16 and 3.12.3 |
| Groups, one test file per group | `tools/run_m8_all.py --range 1-141` | 141 groups passed on Python 3.13.16 (`groups_python3.13.log`) and on Python 3.12.3 (`groups_python3.12.log`): the AUIF dependency, the configuration, the 14 M8 files, the M3 import tests (224, unchanged), each of the 117 existing APG test files (2,583 tests, each at its expected count) and seven regression steps |
| Mutation | `tools/m8_mutants.py --batch K/4 --jobs 2` | 67 mutants: 65 killed, 2 documented equivalent (MD-02, MI-36; reasons in the tool), 0 survived, 0 timed out; a control run passed first in every batch (`mutation_batch_1.log` to `_4.log`). The first pass (`mutation_first_pass/`) left 11 survivors: 9 now have a test that defeats that one check alone (`tests_m8/test_m8_integrity.py` and others), 2 are the documented equivalents |
| Sabotage | `tools/sabotage_m8.py` | 14 cases, 14 caught (`sabotage.log`) |
| Regression against APG-F67.4-R2 | `tools/run_regression_m8.py --all` | R01 to R09 (`regression.log`) |
| Configuration | `tools/make_m8_config.py --check` | 17 files, 0 differing |

**Correction after these runs (product owner, 2026-10-20: "Yes make the corrections").** AUIF is the builder's own build, so the six AUIF findings are recorded as defects in it with one open AUIF correction revision (CF-50), and NOT as Engine handoff rows (EDR-42 to EDR-47, drafted earlier, were never delivered and were removed; the Engine handoff register is byte-identical to R2). This changed only the register rows, the regression and boundary checks' list of changed files, one test docstring and this text. On the final tree the M8 tests were rerun on Python 3.12.3 and 3.13.16 (154 in 14 files each: `m8_tests_python3.12.log`, `m8_tests_python3.13.log`), the regression R01 to R09 (`regression.log`) and sabotage S06 and S11; all passed. The adapter code is unchanged since the mutation, sabotage and group runs.

## 5. Path equivalence and declared differences

Declared before the comparison (`auif_m8/PATH_EQUIVALENCE_DECLARED_DIFFERENCES.json`; hash recorded in `logs/m8/00_declared_differences_before_comparison.txt`, with one correction made before the corpus test existed: R03). Results: GOLDEN_FIN and GOLDEN_DET reproduce exactly on the AUIF path; GOLDEN_M3 except `PS-11/whole_files_replayed` (declared: it counts M3 file receipts). Every record of every collection, both tenants, is identical apart from provenance (declared); the figures, detection results, exclusions and assessment status are identical. On the M3 fault corpus (44 cases) the AUIF path gives the same result in 24 cases, refuses with M3 in 13, and differs in 7 as declared (stricter: R01, R02, R03, R13, H10, T01; more lenient: F09).

## 6. Findings (defects in the builder's own AUIF rev13, frozen for M8; none patched)

F-76 (M8-F1) module-namespace translation; F-77 (M8-F2) composite identity falls back to a content hash; F-78 (M8-F3) waiting events not notified to the module; F-79 (M8-F4) BaseModule swallows handler exceptions; F-80 (M8-F5) the sync report does not say whether the read finished; F-81 (M8-F6) sync raises instead of reporting (drift before first validation; blank identity value). Each is pinned by a test and handled on the APG side. Their fix is a separately authorised AUIF correction revision (CF-50), built by the builder and audited independently; it is not Engine work, so nothing was added to the Engine handoff register.

## 7. Records (append-only; `tools/make_m8_registers.py`)

F-76 to F-81; SR-121 to SR-125 (Local-tested); I-135 to I-140 (retained for review); CF-46 to CF-50. The Engine handoff register is unchanged. No existing row changed.

## 8. Files changed and added (compared byte for byte with the delivered APG-F67.4-R2 ZIP)

- Existing files changed: 6 - `README.md` and `RUN_COMMANDS.txt` (an M8 section on top; the earlier text follows unchanged) and four programme registers (rows appended only). No existing application code, test, tool, template, data file or specification changed.
- Files added: `apg_auif/`, `tests_m8/`, `auif_m8/`, `third_party/auif_rev13/` (the AUIF ZIP and its sidecar, byte for byte), the seven tools above, this record, `regression/m8/`, `logs/m8/`.
