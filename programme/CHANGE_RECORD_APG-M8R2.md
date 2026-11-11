# Change record APG-M8-R2: records only, the auditor's dispositions from three audits

| Field | Value |
|---|---|
| Release | APG-M8-R2, a separately versioned, records-only release. It is the delivered APG-M8-R1 package (ZIP SHA-256 `6e326a6ea02c0df4c7c40952294efcffdd2e74b52340aa1127437f17c7d16fe8`, 1,328 files; every file hash in `regression/m8r2/M8R1_MANIFEST.sha256`) plus the changes below. The APG-M8-R1 ZIP and every earlier ZIP are not modified or replaced. |
| Status | **Builder-made, records only; not accepted.** No independent review of this records release has taken place. |
| Authority | The product owner, 2026-10-21: "Authorise the records-only release for the M8, M8-R1 and rev14 audit results, after the rev14 audit". The rev14 audit result was relayed the same day. Asked how to keep the two M8 checks that list the files M8 may change passing, the product owner decided: "Update the 2 lists". |
| What changed | Records: eight rows appended to `programme/AUDIT_DISPOSITION_REGISTER.csv`. Text: an M8-R2 section on top of `README.md` and `RUN_COMMANDS.txt`. Lists: this release's files and the disposition register added to the declared-file lists of `tests_m8/test_m8_boundary.py` and `tools/run_regression_m8.py` (in the latter, both for steps R01/R02 and for step R10). No application code, test logic, data or specification changed. |
| Added | `tools/make_m8r2_registers.py` (writes the rows), `tools/run_regression_m8r2.py` (checks this release), this record, `regression/m8r2/` (the M8-R1 file hashes, the register before R2, and the two list files before R2), `logs/m8r2/`. |

## 1. The dispositions (as the auditor reported them; full text in the register)

| ID | Finding | Release audited | Disposition | Not independently verified |
|---|---|---|---|---|
| AD-13 | F-82 (M8-F7) | APG-M8 | Defect raised and reproduced by the auditor; APG-M8 not accepted pending its correction (an acceptance blocker) | Python 3.12; the 67-mutant campaign; the real-Governor tests of AUIF rev13 |
| AD-14 | F-82 (M8-F7) | APG-M8-R1 | Independently verified corrected in APG-M8-R1 ("scoped audit passed") | Python 3.12 (the audit ran on Python 3.13.5) |
| AD-15 to AD-20 | F-76 to F-81 (M8-F1 to M8-F6) | AUIF rev14 | No defect found in the AUIF rev14 correction (qualified) | The full fresh-ZIP verifier did not complete in one run; the real-Governor extension tests were not repeated (the Governor ZIP was not available to the auditor); only the 51 revision-specific mutants were rerun; Python 3.12 |

Each row also records what the auditor reproduced and what the disposition does not mean. The findings rows keep their builder text and status, so a finding's disposition is read from the disposition register (I-127). The CF-50 row (the AUIF correction revision) is not edited: AD-15 to AD-20 record its outcome.

## 2. What stays open

- **CF-53:** which record types may validly be empty. Product owner decision. The auditor approved no empty record type, and Builder Zero tenant zero_two still cannot be assessed through AUIF.
- **CF-52:** the M3 path's handling of a header-only file (not examined).
- **CF-51:** the APG-M8-R1 audit is recorded by AD-14. The row is not edited (append-only).
- **M8.1:** moving APG onto AUIF rev14, which ends DEV-M8-01 (CF-47). Not authorised. APG still depends on AUIF rev13.
- **Every other open item:** EDR-05, EDR-06, EDR-18, EDR-39, EDR-40, EDR-41 and every other open EDR and CF item stay open. CF-41 stands. The construction definitions are PROPOSED. The Engine handoff register is unchanged.

These are finding-level dispositions only. Not acceptance of any release, not production readiness, not Engine or Governor integration.

## 3. Evidence (run by the builder; logs in `logs/m8r2/`)

| Check | Command | Result |
|---|---|---|
| Release regression | `tools/run_regression_m8r2.py --all` | R01 to R08 pass on Python 3.13.16 and 3.12.3 (`regression_m8r2_python3.13.log`, `regression_m8r2_python3.12.log`). R01: only the declared files differ from APG-M8-R1. R02: only the declared files were added. R03: the register is the M8-R1 register plus exactly AD-13 to AD-20. R04: the two list files gained only M8-R2's own files and the disposition register, and lost no entry. R05: the text states what it must and makes no claim it must not. R06: the configuration is unchanged. R07: the M8 regression R01 to R10 still passes. R08: the M8 boundary tests still pass. |
| R04 can fail | three seeded edits on a private copy (`r04_seeded_edits.log`) | each caught: an extra list entry, a removed entry, a code change outside the lists |
| All M8 tests | `tools/run_m8_tests.py` | 163 tests in 15 files, every file at its expected count, AUIF rev13 verified before and after, on Python 3.13.16 and 3.12.3 (`m8_tests_python3.13.log`, `m8_tests_python3.12.log`) |

Nothing else was rerun: no application code, test logic or data changed, so the APG-M8-R1 mutation, sabotage and group results stand as they were audited (AD-14).
