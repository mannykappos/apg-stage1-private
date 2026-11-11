# Change record APG-F67.4-R2: records-only correction of the wording of AD-05 to AD-08 (superseded by AD-09 to AD-12)

| Field | Value |
|---|---|
| Release | APG-F67.4-R2, a separately versioned, records-only correction. It is the delivered APG-F67.4-R1 package (ZIP SHA-256 `33a149796293622398d0c1fae7fbf4d41b0dcb4649c4bae388f00cd737e9c407`, 1,215 files; every file hash in `regression/f674r2/F674R1_MANIFEST.sha256`) plus the records below. The APG-F67.4-R1 ZIP and documents, and every earlier ZIP, are not modified or replaced. |
| What changed | No existing application code, tests, tools or specifications were modified; two R2 verification tools were added. The audit disposition register gains AD-09 to AD-12; the interpretations register gains I-134; `README.md` and `RUN_COMMANDS.txt` gain an R2 section on top. |
| Authority | The product owner, 2026-10-20, explicitly: "Authorise F-67.4-R2 records correction: append AD-09 to AD-12 superseding AD-05 to AD-08, identical except that the "what is not independently verified" field reads "No finding-specific qualification beyond the execution-limit qualifications recorded for the APG-F67.4 audit as a whole." followed by the unchanged execution-limit qualifications; record that a finding's current disposition is its latest row. No code changes; no finding status changes. Preserve the F-67.4-R1 ZIP and all earlier releases. Keep EDR-39/40/41 and all other gates open; CF-41 stands. M8 is not authorised." Option 1 (append, do not edit) was recommended by both the auditor and the builder. |
| The defect corrected | The independent audit of APG-F67.4-R1 (relayed 2026-10-20) found that in AD-05 to AD-08 the field `what_is_not_independently_verified` began with a sentence describing the auditor's own evidence ("The auditor's independent reruns against the final package APG-F67.4 ..."). That contradicts the field. It was a records defect; no correction failed and no disposition is in question. |
| Not authorised | M8. Authorising R2 does not accept R1 or any earlier release, close any gate, or authorise M8. |

## 1. What was appended

| New row | Supersedes | Finding | Difference from the superseded row |
|---|---|---|---|
| AD-09 | AD-05 | F-74 | Only the three fields described below |
| AD-10 | AD-06 | F-73 | Only the three fields described below |
| AD-11 | AD-07 | F-72 | Only the three fields described below |
| AD-12 | AD-08 | F-67 | Only the three fields described below |

**The three fields that differ:**
- **`what_is_not_independently_verified`** now reads "No finding-specific qualification beyond the execution-limit qualifications recorded for the APG-F67.4 audit as a whole.", followed by the execution-limit qualifications, unchanged.
- **`disposition_id`** is the new row's own id.
- **`recorded_in`** reads "APG-F67.4-R2; supersedes AD-nn (corrects the wording of what_is_not_independently_verified only)".

Every other field is identical to the superseded row, including the disposition, the auditor reference, what the auditor reproduced and what the disposition does not mean. AD-04 (F-75) was already correct and is not touched. AD-05 to AD-08 stay in the register as the history of what was first recorded.

**I-134 (the reading rule).** A row is corrected by appending a new row whose `recorded_in` names the row it supersedes. A finding's current disposition is its latest row in the register. This extends I-127.

**Current rows by finding:**

| Finding | Current row |
|---|---|
| F-75 | AD-04 |
| F-74 | AD-09 |
| F-73 | AD-10 |
| F-72 | AD-11 |
| F-67 | AD-12 |

Each is independently verified corrected in APG-F67.4, as a finding-level disposition only. EDR-39, EDR-40 and EDR-41, and every other gate, stay open. CF-41 (APG-F67 started without explicit authorisation, not ratified) stands.

## 2. Checks (`tools/run_regression_f674r2.py --all`, R01 to R05, each short)

- **R01:** every APG-F67.4-R1 file is byte-identical except the four declared records.
- **R02:** every new file is a declared R2 addition.
- **R03:** the two registers are exactly what `tools/make_f674r2_registers.py` makes from the R1 registers.
- **R04:** each new row differs from the row it supersedes only in the three fields, and the corrected field is the agreed sentence followed by the unchanged qualifications. The latest row per finding is AD-04 and AD-09 to AD-12, I-134 holds the rule, and the dispositions, findings rows, CF-41 and every gate are unchanged.
- **R05:** the R2 text makes no claim beyond this.

No code suite was rerun; the code is byte-identical (R01). Logs are in `logs/f674r2/`.

## 3. Files

- **Changed (rows appended only):**
  - `README.md`
  - `RUN_COMMANDS.txt`
  - `programme/AUDIT_DISPOSITION_REGISTER.csv`
  - `programme/INTERPRETATIONS_REGISTER.csv`
- **Added:**
  - `tools/make_f674r2_registers.py`
  - `tools/run_regression_f674r2.py`
  - this record
  - `regression/f674r2/`
  - `logs/f674r2/`
