# Change record APG-M8-R1: an empty source is not current data (finding M8-F7)

| Field | Value |
|---|---|
| Release | APG-M8-R1, a separately versioned, additive correction release. It is the delivered APG-M8 package (ZIP SHA-256 `f1b634d36f2ac57eefed6910cdc86273b30b5bdcc13d8be778d1b2f21a81157c`, 1,307 files; every file hash in `regression/m8r1/M8_MANIFEST.sha256`) plus the changes below. The APG-M8 ZIP and every earlier ZIP are not modified or replaced. |
| Status | **Builder-implemented and locally tested; not accepted.** No independent verification of this correction has taken place. Not a release acceptance, not production approval, not proof of integration with a real Anchor Engine. |
| Authority | The product owner, 2026-10-20: "Authorise M8-R1 as written, after rev14". The independent audit of APG-M8 refused acceptance pending this correction. |
| Dependency | AUIF rev13, unmodified (ZIP `61748ddeba21e8c1d71b56bd0d3ad7a376ea051f4ae6fbe56c6464c0de76e070`), verified by hash before every run, exactly as in APG-M8. AUIF rev14 (the separately authorised AUIF correction, CF-50) is NOT used here. |
| Deviation | DEV-M8-01 unchanged (CF-47). |
| Gates still open | Every open EDR and CF item, including EDR-05, EDR-06, EDR-18, EDR-39, EDR-40, EDR-41; CF-41 unchanged; F-76 to F-81 open; the construction definitions PROPOSED. |

## 1. The finding (M8-F7, F-82)

Reproduced by the independent audit on the delivered APG-M8, and again by the builder (`logs/m8r1/repro_on_delivered_m8.txt`): after a good import of the synthetic AP invoices (187 records), the source file was cut to its header and imported again through AUIF rev13. AUIF reported NO_DATA (`empty`). `apg_auif/intake.py` `batch_checks()` did not treat that as a reason, so the import was applied with no reason, the 187 earlier records stayed, and the gate answered can_assess. No M8 test covered a source that becomes empty.

## 2. The correction

`apg_auif/intake.py`, `batch_checks()`, sync mode: a full read that brings back no record is refused with the integrity reason **SOURCE_EMPTY**. "No record" means AUIF reported NO_DATA, or the read ended with nothing delivered and no other outcome (no invalid or ambiguous object, no failure, not refused by the integration's state); a read whose objects were all invalid or ambiguous keeps its own reason (interpretation I-141). As for every integrity reason, nothing from the batch is written and the record type's latest import is blocked, so:

- the gate answers cannot_assess with SOURCE_EMPTY, whether the source was empty from the start or became empty after a good import;
- the assessment returns no figure, no signal and no run key, and no earlier result is shown as current; earlier records stay stored but are never made current by an empty read;
- a clean import after the source is restored (a replay of the same content included) makes the assessment possible again;
- an event poll that brings no new event is not a full read and is not refused.

No record type is declared as validly empty: the audit allows that only under a separately approved contract, and none exists. `apg_auif/gate.py`: SOURCE_EMPTY added to the documented list of reasons (docstring only).

## 3. The declared corpus difference (written before the comparison ran)

Corpus case F11 (header only, no data rows) was "same" in APG-M8. M3 records it as a valid empty delivery whose receipt does not stop the assessment; the AUIF path now refuses it. Before `tests_m8/test_m8_corpus.py` was run on M8-R1, F11 was moved to "differs" in `auif_m8/PATH_EQUIVALENCE_DECLARED_DIFFERENCES.json` with its reason and a correction note, and the file's hash was logged (`logs/m8r1/00_declared_differences_before_comparison.txt`). `tests_m8/test_m8_corpus.py` expects M3 to allow the assessment for F11 (as for T01 and H10). Whether the M3 path can also assess with earlier records after a source becomes empty was not examined or changed: it is outside M8-R1 (CF-52).

## 3a. What the builder did NOT foresee: Builder Zero tenant zero_two cannot be assessed through AUIF any more

Builder Zero's second tenant (zero_two) has eight record types whose files are header only: credit notes, notices, variations, plant hire, PO amendments, supplier quotes, delay events and defects. M3 records each as a valid empty delivery and can assess zero_two. Under M8-R1 the AUIF path refuses each one with SOURCE_EMPTY, so **zero_two now answers "cannot assess" on the AUIF path**, with exactly those eight reasons. Its stored records, figures and detection results are still the same as on the M3 path; they are compared by running the calculations on both stores instead of through the assessment.

This was **not declared before the comparison**. The first M8-R1 run of `tests_m8/test_m8_path_equivalence.py` failed on Python 3.13 and 3.12 (the logs are kept: `logs/m8r1/m8_tests_first_run_python3.13_FAILED.log`, `..._python3.12_FAILED.log`). After that run the builder added the `source_empty` section and 24 GOLDEN_M3 entries (the empty-file counts of `credit_notes.csv`, `po_amendments.csv` and `quotes.csv`) to `auif_m8/PATH_EQUIVALENCE_DECLARED_DIFFERENCES.json`, recorded the correction in the file and its new hash in `logs/m8r1/00_declared_differences_before_comparison.txt`, and changed `tests_m8/test_m8_path_equivalence.py` to check exactly those scopes. The partial mutation batch that was running when the failure was found was stopped and its log deleted; every M8-R1 run reported below was made after the change.

This follows the audit's rule literally: an empty result is a reason not to assess "unless a separately approved contract defines the empty result as valid", and no such contract exists. It is also the product owner's decision to make: a builder with no variations or no defects is a normal case, and the AUIF path now cannot assess it. **Decision needed (recorded as CF-53):** whether some record types may validly be empty, and for which tenants. If so, a further correction would let an approved empty record type through, only when the approval exists; until then the strict rule stands.

## 4. Files changed and added (compared byte for byte with the delivered APG-M8 ZIP; regression step R10)

Checked by `tools/run_regression_m8.py --step R10` against `regression/m8r1/M8_MANIFEST.sha256` (the 1,307 file hashes of the delivered APG-M8 ZIP). The package folder is now `APG_M8R1/`.

| Changed file | Change |
|---|---|
| `apg_auif/intake.py` | The SOURCE_EMPTY rule in `batch_checks()` (section 2). |
| `apg_auif/gate.py` | SOURCE_EMPTY added to the docstring's list of reasons. No code change. |
| `auif_m8/PATH_EQUIVALENCE_DECLARED_DIFFERENCES.json` | F11 moved to "differs" (before the comparison); the `source_empty` section and 24 GOLDEN_M3 entries (after it, section 3a); two correction notes. |
| `tests_m8/test_m8_corpus.py` | M3's expected status for F11 (one line). |
| `tests_m8/test_m8_path_equivalence.py` | Checks the declared zero_two empty sources exactly: those batches are refused for SOURCE_EMPTY alone, M3's empty receipts have no AUIF counterpart, and zero_two's assessment refuses with exactly those eight reasons while its figures and detection results still equal the M3 path's (section 3a). |
| `tests_m8/test_m8_boundary.py` | M8-R1's added paths and files declared. |
| `tools/run_m8_tests.py`, `tools/run_m8_all.py` | The new test file (9 tests); regression group R10. |
| `tools/m8_mutants.py` | MI-38 to MI-42 and the new test file in tier 1; MI-39 documented as equivalent. |
| `tools/sabotage_m8.py` | S15. |
| `tools/run_regression_m8.py` | The M8-R1 register rows; step R10. |
| `README.md`, `RUN_COMMANDS.txt` | An M8-R1 section on top; the M8 text follows unchanged. |
| `programme/` four registers | Rows appended only (section 6). |

| Added | What |
|---|---|
| `tests_m8/test_m8r1_empty_source.py` | 9 tests. 5 fail on the delivered APG-M8. 4 are guards: an event poll with no new event, and reads that fail, are refused by the integration state, are wholly invalid or ambiguous, or bring records, each keep their own outcome. |
| `tools/make_m8r1_registers.py` | The M8-R1 register rows. |
| `programme/CHANGE_RECORD_APG-M8R1.md` | This record. |
| `regression/m8r1/M8_MANIFEST.sha256` | The delivered APG-M8 file hashes. |
| `logs/m8r1/` | Every M8-R1 run log, including the failed first runs. |

## 5. Evidence (run by the builder; logs in `logs/m8r1/`)

| Check | Command | Result |
|---|---|---|
| Reproduction | the builder's script (`logs/m8r1/repro_on_delivered_m8.txt`) | delivered APG-M8: second import applied, 187 records, gate can_assess; APG-M8-R1: second import blocked (SOURCE_EMPTY), gate cannot_assess |
| M8 tests, one file at a time | `tools/run_m8_tests.py` | 163 tests in 15 files, every file at its expected count, AUIF rev13 verified before and after; Python 3.13.16 and 3.12.3 (`m8_tests_python3.13.log`, `m8_tests_python3.12.log`) |
| Groups, one test file per group | `tools/run_m8_all.py --range 1-143` | 143 groups passed, 0 failed, 0 incomplete, on Python 3.13.16 and on 3.12.3 (`groups_python3.13.log`, `groups_python3.12.log`): the AUIF dependency, the configuration, the 15 M8 test files, the M3 import tests (224, unchanged), each of the 117 existing APG test files (2,583 tests) and regression R01 to R05, R08 to R10 |
| Mutation | `tools/m8_mutants.py --batch K/4 --jobs 2` | 72 mutants: 69 killed, 3 documented equivalent (MD-02, MI-36 from APG-M8; MI-39 new, reason in the tool), 0 survived, 0 timed out; a control run passed first in every batch (`mutation_batch_1.log` to `_4.log`). The four new mutants that can be killed (MI-38, MI-40, MI-41, MI-42) were all killed. |
| Sabotage | `tools/sabotage_m8.py` | 15 cases, 15 caught (`sabotage.log`), including S15 (the empty-source refusal removed) |
| Regression | `tools/run_regression_m8.py --all` | R01 to R10 (`regression.log`) |

**Runs that failed and are kept.**
- The first run of the M8 tests on M8-R1 failed in `test_m8_path_equivalence.py` on both Pythons (section 3a; `m8_tests_first_run_python3.13_FAILED.log`, `..._python3.12_FAILED.log`). A mutation batch that had started was stopped and its log was not kept.
- The first regression run failed R10 (`regression_first_run_R10_FAILED.log`): `tests_m8/test_m8_path_equivalence.py`, changed for section 3a, was missing from R10's list of declared changes. The list was corrected (`tools/run_regression_m8.py`). R01 to R10 were then rerun, and so were the sabotage cases that use that tool (S11 and S12; `sabotage_rerun_S11_S12_after_R10_fix.log`). The group runs on both Pythons were started after the correction (a group run in progress was stopped and its log was not kept). The M8 tests, mutation and the other sabotage cases ran before that correction; it changed only R10's file list and description, which none of them reads.
- After the group runs, only this change record (its evidence section) was edited. Regression R05 and R10 were rerun on the final tree.

The AUIF rev13 ZIP is unchanged and verified by hash before and after every run. AUIF rev14 was not used.

## 6. Records (append-only; `tools/make_m8r1_registers.py`, run after `tools/make_m8_registers.py`)

F-82 (M8-F7, open: corrected by the builder, not accepted until audited); SR-126 (Local-tested); I-141 (what counts as an empty source; retained for review); CF-51 (the audit of APG-M8-R1); CF-52 (the M3 path's handling of a header-only file; not examined); CF-53 (which record types may validly be empty: an owner decision; section 3a). No existing row changed. The Engine handoff register is unchanged.
