# Change record APG-MIE-1.1-R1: records only -- the independent auditor's disposition of F-70 and F-71

| Field | Value |
|---|---|
| Release | APG-MIE-1.1-R1, a records-only release on the delivered MIE-1.1 package (ZIP SHA-256 `0d2d158c47d5208dfbc3f19a2ad1a75ebed288e038e463241b841ea1de171b4b`, 1,033 files; every file hash in `regression/mie1_1r1/MIE1_1_MANIFEST.sha256`). No code, test, tool or specification changes. The MIE-1.1 ZIP is not modified. |
| Status | Builder-made records. The disposition recorded is the independent auditor's; this release adds nothing to what the auditor verified. |
| Authority | The independent audit of MIE-1.1, relayed by the product owner on 2026-10-20, and the agreed next steps: record F-70 and F-71 as independently verified corrected, preserving the audit scope and without implying release acceptance; then the F-67 correction release, after the MIE-1.1 mutation audit. |

## 1. What is recorded

| Disposition | Finding | Disposition | Not independently verified |
|---|---|---|---|
| AD-01 | F-70 (auditor F-MIE1-01) | Independently verified corrected (audit scope recorded) | The full 624-mutant run is builder-reported; the auditor ran selected mutants, which were killed. The whole-suite command R12 timed out for the auditor; groups 9 to 19 (2,528 tests) passed separately |
| AD-02 | F-71 (auditor F-MIE1-02) | Independently verified corrected (audit scope recorded) | The same; and I-125 (the strict reading of what a correction may supersede) is still retained for review |

Each row in `programme/AUDIT_DISPOSITION_REGISTER.csv` also states what the auditor reproduced and what the disposition does not mean. It is not a release acceptance, and it says nothing about a real Anchor Engine store. EDR-36 to EDR-38, BLK-01 to BLK-03, M7.3 final acceptance, the M9.4 comparison and DEV-MIE-01 stay open (CF-36 to CF-39).

**Why a new table (I-127).** Programme rows are append-only and never edited. So the findings register keeps the builder's text for F-70 and F-71 ("open until independently verified"), and their verification status is read from the disposition register. Earlier findings are not back-filled; only F-70 and F-71 were agreed for recording.

## 2. Files

- **Changed (3):**
  - `README.md` and `RUN_COMMANDS.txt`: an R1 section above the MIE-1.1 text.
  - `programme/INTERPRETATIONS_REGISTER.csv`: I-127 appended.
- **Added:**
  - `programme/AUDIT_DISPOSITION_REGISTER.csv`;
  - this record;
  - `tools/make_mie1_1r1_registers.py` and `tools/run_regression_mie1_1r1.py`;
  - `regression/mie1_1r1/`, holding the MIE-1.1 manifest and table snapshot;
  - `logs/mie1_1r1/`.

## 3. Next

The F-67 correction release (the detection, financial and procurement policies accept caller-asserted approvals) is the agreed next build, after the auditor has run the MIE-1.1 mutation batches. M8 follows under its own authorisation.
