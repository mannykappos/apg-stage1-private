# Change record APG-F67.4-R1: records-only release recording the independent auditor's finding-level dispositions from the audit of APG-F67.4

| Field | Value |
|---|---|
| Release | APG-F67.4-R1, a separately versioned, records-only release. It is the delivered APG-F67.4 package (ZIP SHA-256 `4abaa349e201ae2ffccb589b248b2e5d255a92340acdf2bfed17b1194b56c4cd`, 1,209 files; every file hash in `regression/f674r1/F674_MANIFEST.sha256`) plus the records below. The APG-F67.4 ZIP and documents, and every earlier ZIP, are not modified or replaced. |
| What changed | No existing application code, tests, tools or specifications were modified; two R1 verification tools were added. The audit disposition register gains five rows (AD-04 to AD-08), and `README.md` and `RUN_COMMANDS.txt` gain an R1 section on top (the earlier text follows unchanged). |
| Authority | The product owner, 2026-10-20, explicitly: "Authorise F-67.4-R1 records release: record F-75 as independently verified corrected in F-67.4 with the auditor's execution-limit qualifications; record F-74, F-73, F-72 and F-67 as independently verified corrected based on the auditor's independent reruns. No code changes. Preserve the F-67.4 ZIP and all earlier releases. Keep EDR-39/40/41 and all other gates open. M8 is not authorised and must not start." |
| The audit | The independent audit of APG-F67.4, relayed by the product owner on 2026-10-20, and the auditor's confirmation, relayed the same day, that it is willing to record F-74, F-73, F-72 and F-67 as independently verified corrected in F-67.4, based on the probes and associated tests it independently reran against the final package. |
| Not authorised | M8 (AUIF-side integration and file import). It needs its own explicit authorisation after the audit of this release. |

## 1. The dispositions recorded (`programme/AUDIT_DISPOSITION_REGISTER.csv`)

| Row | Finding | Disposition |
|---|---|---|
| AD-04 | F-75 | Independently verified corrected in APG-F67.4, with the execution-limit qualifications |
| AD-05 | F-74 | Independently verified corrected in APG-F67.4 |
| AD-06 | F-73 | Independently verified corrected in APG-F67.4 |
| AD-07 | F-72 | Independently verified corrected in APG-F67.4 |
| AD-08 | F-67 | Independently verified corrected in APG-F67.4; the authorisation-process issue of its start stands as recorded in CF-41 |

**The execution-limit qualifications** (recorded on every row). These are execution limitations, not failed tests.
- The combined 23-group runner timed out after group 3, and the combined regression step R08 exceeded the limit. Their constituent tests and probes were run individually.
- Mutation batch 1 timed out on the slow path of the documented equivalent PA-CMP-013. Its 13 other mutants were run separately, and batches 2 to 10 completed.
- No timeout was counted as a kill. PA-CMP-013 is documented as equivalent under RH-03 of the record-store history contract.

**What the auditor ran.** The auditor:
- verified the ZIP hash and integrity, and that all 1,186 APG-F67.3 files match the F67.3 manifest;
- ran the F-75 probe: 15 defects on APG-F67.3, 0 on APG-F67.4, and the control passed;
- ran the 9 F-67.4 tests;
- ran the F-74, F-73, F-72 and F-67 probes and their 46 tests in four files;
- ran the static regression (9 of 9) and the golden-output check;
- ran the record-store history contract, which caught all four faulty stores;
- ran all 117 test files individually, with expected counts totalling 2,583;
- ran the mutation run: 130 killed, 1 documented equivalent, 0 unexplained survivors;
- ran sabotage: 16 of 16 caught.

**What these dispositions do not mean** (recorded on every row). They are finding-level dispositions only.
- They do not accept APG-F67.4 or any APG release, establish production readiness, or approve integration or deployment.
- EDR-39, EDR-40 and EDR-41 are unverified on any Engine store and stay open. So do EDR-34 and EDR-36 to EDR-38, CF-36 to CF-39, BLK-01 to BLK-03, M7.3 final acceptance, M9.4 and DEV-MIE-01.
- They do not retroactively authorise the start of APG-F67: CF-41 (started without explicit authorisation, not ratified) stands.
- M8 is not authorised.

**How a finding's status is read.** The findings rows keep their builder text, because programme rows are never edited. A finding's verification status is read from the disposition register (I-127).

**The open audit items.** CF-40 and CF-42 to CF-45 ("Open - for the auditor") are answered by these dispositions as far as the findings go. Those rows are not edited, and they stay open for the wider release questions they also carry.

## 2. Checks (`tools/run_regression_f674r1.py --all`, R01 to R07, each short)

- **R01:** every APG-F67.4 file is byte-identical except the three declared records.
- **R02:** every new file is a declared R1 addition.
- **R03:** the register is exactly what `tools/make_f674r1_registers.py` makes from the F67.4 register.
- **R04:** the five dispositions say what is above, and the gates are still open.
- **R05:** the R1 text makes no acceptance or readiness claim.
- **R06:** the F-75 probe still passes.
- **R07:** the F-67.4 tests still pass.

Logs are in `logs/f674r1/`.

## 3. Files

- **Changed:** `README.md`, `RUN_COMMANDS.txt` and `programme/AUDIT_DISPOSITION_REGISTER.csv` (rows appended only).
- **Added:**
  - `tools/make_f674r1_registers.py`
  - `tools/run_regression_f674r1.py`
  - this record
  - `regression/f674r1/` (the F67.4 manifest and the register before R1)
  - `logs/f674r1/`
