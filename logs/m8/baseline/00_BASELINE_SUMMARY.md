# M8 baseline verification (run before any adapter code was written)

Environment: Linux 6.18.44-fc-v139 x86_64, glibc 2.39; Python 3.12.3 and Python 3.13.16; standard library only; no network. PYTHONDONTWRITEBYTECODE=1. Each run in its own clean extraction.

## Archives (01_archives.log)
| Item | Expected | Found |
|---|---|---|
| APG-F67.4-R2 ZIP | 3e474b4671c846e7581ccb6d1ca27a6fe339f03a2275bf9ad7f753b0097a516e | match (1,222 files) |
| AUIF handover archive | 5dad8d2764f6f8c54f6fdb6a6079eb9ab30062c48af7e6225a847d203c5f4f1a | match; the two uploaded copies are byte-identical |
| Handover SHA256SUMS | all entries | all OK |
| AUIF rev13 ZIP | 61748ddeba21e8c1d71b56bd0d3ad7a376ea051f4ae6fbe56c6464c0de76e070 | match (also its .sha256 sidecar) |

## AUIF rev13 (02_auif_python3.12.log, 02_auif_python3.13.log)
| Group | Python 3.12.3 (stated version) | Python 3.13.16 |
|---|---|---|
| verify_package (manifest, 248 files) | ok, 0 mismatches, tree 9fbc5de7041c4cba0b177b1cb3b7fb4c7da6290a69a96ab2a939140bdf11652e | identical |
| static_checks | no violations; core tree 74cec87afd167601fd4f260ec02b6f3c16121355b2d5c29767b5f1d3273bf93d (as specified) | identical |
| core tests | 410 run, OK | 410 run, OK |
| extension tests | 343 run, OK, 20 skipped | 343 run, OK, 20 skipped |
| accelerator tests | 418 run, OK | 418 run, OK |
| verify_package after the tests | ok, 0 mismatches | ok, 0 mismatches |

The 20 skipped extension tests are the real-Governor-R14 tests, which run only when that Governor package is supplied; the rev13 evidence records exactly "343 run, 20 skipped" for this run (shipped_verifier_full_run.log step 5e). The whole-package tree hash 9fbc5de7... is the one in rev13's FILE_MANIFEST.json. No difference between 3.12 and 3.13.

## APG-F67.4-R2, unchanged (03_apg_python3.13.log, 03_apg_python3.12.log, 04_apg_r2_self_check.log)
| Group | Python 3.13.16 (APG's stated version) | Python 3.12.3 |
|---|---|---|
| M3 import tests (test_ingest_*.py, 8 files) | 224 tests, 0 failures, 0 errors | identical |
| whole suite, one test file per group (117 files) | 2,583 tests, every file at its expected count, 0 failed | identical |
| R2 self-check (run_regression_f674r2.py --all) | 5 of 5 | - |

Result: every baseline passed with the expected counts and source integrity; no unexplained difference. Adapter work started after this.
