# Change record APG-M7.2: the source check and the act commit together, after the independent audit of APG-M7.1 (F-68)

| Field | Value |
|---|---|
| Release | APG-M7.2, a separately versioned, additive correction release. It is the delivered M7.1 package (ZIP SHA-256 `6fd3bac49f16a9b954dba79d70ea8d673b8756cdc92ab44e100ffaaea35abe89`) plus the correction below. The delivered M7.1 ZIP and documents are not modified or replaced. |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** F-68 stays open until the auditor verifies it, and so do F-64 to F-66. F-67 is still open and not corrected. |
| Authority | The auditor's verdict on M7.1, relayed by the product owner on Mon 2026-10-19. The verdict was not yet accepted, with a request for a narrowly scoped correction (M7.2) and not another specification package. |
| Not touched | No M2 to M6 file and no M9 file, including the record store and its contract. Of apg/rec, only `lifecycle.py` and `engine.py` changed. No existing test changed. Engine #17 and RFC-01 are unchanged (RFC-01 is still PROPOSED and unnumbered). |

## 1. The finding and what changed

| ID | What was wrong in M7.1 | What changed | Tests (12 of the 18 fail or error on the M7.1 code) |
|---|---|---|---|
| F-68 | The freshness check and the write of the recommendation were separate store operations. A source change between them (the finding dismissed right after the check) was not seen, and the act was recorded. This held at submission, approval and the start of work | `lifecycle._commit_checked` writes the act in one atomic store batch with a guard on every stored record the check read. A guard holds the record at the revision the check saw and writes nothing. If any record changed, the batch fails, nothing is recorded, and the act is refused (`SOURCE_CHANGED`, or `CONCURRENT_CHANGE` when the sources still match). A record created during the act is caught by checking again once the act is recorded; the act is then reversed at once, audited and refused | `tests/test_rec_m72_race.py` (18 tests): seven kinds of change, at each of the three boundaries, at both injection points (after the check, and immediately before the commit). Also covered: a new overlapping finding at each boundary and point, nothing changed, an unrelated change, the recommendation itself changing, the guard's own rules, and the check before the act |

**What the store contract can and cannot hold.**

- **What it can hold.** The record store's existing rules give a conditional commit for records that exist. An op whose payload equals the latest payload appends nothing, and an op whose expected revision is not the latest fails the whole batch. A test pins these rules for the reference store.
- **What it cannot hold.** The contract cannot hold a record as still absent, or a query as unchanged, without writing. M7.2 does not hide that limit behind another check. It is recorded as I-115 and EDR-35.
- **What M7.2 does instead.** Records created during the act are caught by checking again once the act is recorded. When the check fails, the act is reversed with an audited, append-only record.
- **The reference store.** It is single-process and holds no lock, so atomicity against truly concurrent callers is the store's to provide (EDR-02 already requires all-or-nothing batches).

## 2. Files changed and added (compared byte for byte with the delivered M7.1 ZIP)

**Changed (11)**

- **Application.** `apg/rec/lifecycle.py`: `_commit_checked` and `_guards`, and `source_check` now reports the records it read. `apg/rec/engine.py`: `current_inputs` can report the records it read.
- **Tools.** `tools/m7_mutants.py`: it runs the race tests too.
- **Records and documents.**
  - `README.md` and `RUN_COMMANDS.txt`: an M7.2 section above the M7.1 text.
  - `programme/RECOMMENDATION_ENGINE.md`: section 8b.
  - Five programme tables with rows appended: finding F-68, status SR-101 and SR-102, interpretations I-114 and I-115, Engine handoff EDR-35, and carried-forward CF-34.

**Added**

- **Tests.** `tests/test_rec_m72_race.py`.
- **Tools.** `probe_m71_race.py` prints DEFECT PRESENT on M7.1 and THE RACE IS CLOSED here. Also added: `run_regression_m72.py`, `run_m72_all.py`, `sabotage_m72.py` and `make_m72_registers.py`.
- **Regression data and logs.** `regression/m72/` holds the M7.1 manifest and the M7.1 table snapshot. `logs/m72/` holds the builder's runs.
- **Documents.** This record.

## 3. What the auditor could not complete (CF-34)

The full sabotage suite was incomplete in the M7.1 audit, and the full mutation run was not independently completed. These are incomplete, not passes. The split commands are in `RUN_COMMANDS.txt`, sections B, D and E. The delivered M9.4, M7 and M7.1 ZIPs can be supplied to the auditor, so that the stored manifests are compared with the real archives.
