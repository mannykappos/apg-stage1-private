# Change record APG-MIE-1.1: correction of the two findings of the independent audit of APG-MIE-1 (F-70, F-71)

| Field | Value |
|---|---|
| Release | APG-MIE-1.1, a separately versioned, additive correction release. It is the delivered MIE-1 package (ZIP SHA-256 `26fe3517d0d4f64981bad3cc2f28e1d748e0c25062f98c22209359435dd4206d`, 1,007 files; every file hash in `regression/mie1_1/MIE1_MANIFEST.sha256`) plus the corrections below. The delivered MIE-1 ZIP and documents are not modified or replaced. |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** F-70 and F-71 stay open until the auditor verifies them. Nothing here is accepted or approved, and nothing is for use outside tests. |
| Authority | The auditor's verdict on MIE-1, relayed by the product owner: an additive MIE-1.1 correction release that preserves the MIE-1 ZIP, fixes both defects, adds regression tests that fail against the current package, and reruns the relevant tests from a clean extraction; the gates stay open. |
| Development deviation (DEV-MIE-01) | MIE1_SPEC v0.3 (line 6, unchanged) says no implementation code is written or authorised until the specification has been reviewed, BLK-01 to BLK-03 are cleared, and the product owner separately authorises implementation. The product owner authorised development while BLK-01 to BLK-03 are still open. MIE-1 and MIE-1.1 are built under that explicit deviation (CF-38) and do not claim unconditional conformity with that wording. The specification is not edited; the deviation clears no blocker and closes no gate. |
| Gates still open | M7.3 final release acceptance, EDR-36 and the M9.4 comparison (CF-36); BLK-01 to BLK-03 (CF-37); EDR-37 and EDR-38; the MIE-1 audit runs that did not complete (CF-39). |

## 1. The findings and what changed

| ID | What was wrong in MIE-1 | What changed | Tests |
|---|---|---|---|
| F-70 (auditor F-MIE1-01) | `Engine._run` caught only `StoreFailure` at the commit. A store raising `RuntimeError` let a raw exception escape after the ACCEPTED event, with no FAILED event. Also, the builder found: an audit sink raising an unexpected exception escaped raw; a store failing part-way through a batch of observations left the first items stored | Any other exception at the commit is INTERNAL_ERROR_FAIL_CLOSED with one attempted FAILED event and no result (`engine.py`). Any failure of the audit sink is AUDIT_UNAVAILABLE (`Engine._append`). A batch of observations is written in one call, `ObservationStorePort.append_batch`, all or nothing; the reference store stages the batch and applies it in one step (`ports.py`, `reference.py`; EDR-38) | `tests/test_mie_core_m11_corrections.py`: every committing operation with a store raising RuntimeError; the FAILED event's own failure; an audit sink raising RuntimeError for a commit, a read and a refusal; a failure at the second of three items; the batch-store contract |
| F-71 (auditor F-MIE1-02) | `supersedes` was checked only for an existing identifier. An observation of another subject or series could name one, and the original silently became history wherever both were in scope | A correction must be of the same series (subject, market, unit, class, basis), from the same source, for the same as_of date and of the same kind (`signals.corrects`, checked in `observations.check` against the stored or same-batch original); anything else is REJECTED, OBSERVATION_INVALID, field `supersedes`. `signals.classify` also ignores an incompatible link, so an observation written by any other path cannot hide evidence (I-125) | The same file: ten incompatible variants (each attribute changed on its own, and two pairs) rejected with the signal view byte-identical before and after; level versus event; a true correction, also within one batch; an incompatible link already in a store |

Nine of the ten tests fail or error when run against the delivered MIE-1 code (`logs/mie1_1/correction_tests_against_mie1.txt`). The tenth was added after the first MIE-1.1 mutation run left one survivor (OB-BOL-009): a `supersedes` value that is not text must still be REJECTED, not an internal error. It guards the new code and passes on MIE-1 as well.

**Reproduction.** `tools/probe_mie1_audit_findings.py` runs unchanged on both packages. On MIE-1 it prints DEFECT PRESENT 17 times; here, all 18 cases (including a control) are CORRECTED (`logs/mie1_1/probe_on_mie1_and_mie1_1.txt`).

## 2. Evidence (run fresh by the build; logs in `logs/mie1_1/`)

| Check | Result |
|---|---|
| Whole unit suite | 2,528 tests in eleven counted parts (`tools/run_mie1_1_all.py`, groups 9 to 19): the 2,284 M2 to M7.3 tests unchanged, the 234 MIE-1 tests (one changed) and the 10 correction tests |
| Mutation run | `tools/mie11_mutants.py`: 624 mutants over the same seven core modules (every site), 621 killed, the 3 MIE-1 documented equivalents, 0 unexplained survivors. The first MIE-1.1 run left one survivor (OB-BOL-009: a non-text `supersedes` value), closed by the tenth correction test |
| Sabotage | `tools/sabotage_mie1_1.py`: 70 of 70 caught: the 60 catalogue cases and C-01 to C-10, which undo each part of the corrections. The first run missed C-09, because the test case for another source also changed the value basis; the cases now change each attribute on its own |
| Regression against MIE-1 | `tools/run_regression_mie1_1.py`, all steps: every MIE-1 file byte-identical except the declared changes; no APG application file and no M2 to M7.3 test changed; programme tables append-only; the golden Builder Zero run unchanged |
| Clean extraction | The ZIP extracted into an empty folder and the groups, the probe and samples of the mutation and sabotage runs re-run there |

## 3. Files changed and added (compared byte for byte with the delivered MIE-1 ZIP)

**Changed (14)**

- **Core.**
  - `mie/core/engine.py`: the commit and audit failure paths, and the batch write.
  - `mie/core/observations.py`: the correction check.
  - `mie/core/signals.py`: `corrects` and the classification guard.
  - `mie/core/ports.py`: `append_batch`.
  - `mie/core/reference.py`: the staged batch write.
- **Test.** `tests/test_mie_core_audit.py`: AU-07 watches `append_batch` instead of `append`.
- **Records and documents.**
  - `README.md` and `RUN_COMMANDS.txt`: an MIE-1.1 section above the MIE-1 text.
  - `programme/MIE1_CASE_COVERAGE.csv`: regenerated, because the correction tests cite CT-03.
  - Five programme tables, with rows appended: F-70, F-71, SR-109, SR-110, I-125, I-126, EDR-38, CF-38 and CF-39 (`tools/make_mie1_1_registers.py`).

**Added**

- `tests/test_mie_core_m11_corrections.py`.
- Tools:
  - `tools/probe_mie1_audit_findings.py`, `mie11_mutants.py`, `sabotage_mie1_1.py`;
  - `run_regression_mie1_1.py`, `run_mie1_1_all.py`, `make_mie1_1_registers.py`.
- `regression/mie1_1/`: the MIE-1 manifest and the MIE-1 table snapshot.
- `logs/mie1_1/`.
- This record.
