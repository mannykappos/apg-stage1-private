# Change record APG-M6.1: approval binding (finding F-52)

| Field | Value |
|---|---|
| Release | APG-M6.1, a separately versioned correction of the delivered M6 package |
| Status | **Builder-implemented and locally tested, not independently reviewed.** The auditor confirms the correction. |
| Authority | The auditor's response of 2026-10-15 approved a labelled correction of the M5 code under these controls: preserve the frozen M5 archive and hash; a separately versioned correction with a change record; bind each approval to the finding version and evidence digest; on a material change end the approval and require a fresh one; regression tests for version 1 to 2, unchanged evidence, replay and reuse; re-run the M5 regression and verify the new archive independently. |
| Untouched | Delivered M5 ZIP `4c15ad568c5c5ff12977529ba3253c9042781e4aa272af3b87a10eab5a010be6`; delivered M6 ZIP `abcfefd9f28464de46dc205c1112b2ea33f537ef4a788562484c1d24109a1efb`; locked Sections 00-18 (`487becabdf47796800937d13a706a19b63b7b8230ecc5354b2f01a647ae5d960`); CR-09; the RTM; RFC-01 (still PROPOSED and unnumbered); the milestones table (M7 not started). |

## 1. The defect

A finding's approved action recorded who approved it and when. It did not record which version of the finding, or which evidence, was approved. When a later detection run changed the evidence (a new state digest), `ingest_run` replaced the signal and added one to the version, and left the status and the action alone. A finding approved at version 1 on one figure therefore read as approved at version 2 on a different figure, by the same approver, with no new review. The probe `tools/probe_approval_binding.py` shows it: on the delivered M6 code it prints `AFTER  action_approved version 2 ... approved by abby` and `DEFECT PRESENT`. It was found in the Engine #17 Phase 0 discovery (gate E17-A23) and recorded as F-52.

## 2. Impact

APG never carries out an action or moves money, so the defect harms the integrity of the record, not a balance. Its effect was that a person reading the record could take an approval as covering evidence the approver had not seen, and that anything built later on "approved" (the realised-benefit work the auditor has in mind) would have inherited that. It affected every finding whose evidence changed after approval or while work was in progress. It could not affect a finding whose evidence did not change. No stored data outside the builder's own tests exists.

## 3. Files changed

Compared byte for byte with the delivered M6 ZIP. All other files (the count is in `regression/BASELINE_M6.json`) are identical.

**Changed (9)**

| File | Kind | What changed and why |
|---|---|---|
| `README.md` | records and documents | adds the M6.1 section above the unchanged M6 text |
| `RUN_COMMANDS.txt` | records and documents | adds the M6.1 commands above the unchanged M6 text |
| `apg/det/findings.py` | application code | the correction itself: approval binding, ending an approval when the digest changes, the optional version named by the approver, the approval history, `approval_current` |
| `programme/FINDINGS_REGISTER.csv` | records and documents | row F-52 appended; no earlier row changed |
| `programme/INTERPRETATIONS_REGISTER.csv` | records and documents | rows I-59 to I-64 appended; no earlier row changed |
| `programme/STATUS_REGISTER.csv` | records and documents | rows SR-62 to SR-65 appended; no earlier row changed |
| `tools/m5_mutants.py` | tools | runs the new test file in the M5 mutation run (the new file is added to its list of tests and made the first test run for `findings.py`) |
| `tools/make_m0.py` | tools | runs the M6.1 register step after the M6 one, so the derived-files check regenerates the programme tables with the M6.1 rows; nothing else |
| `tools/run_regression_m6.py` | tools | check L05 now accepts status-register rows with milestone M6.1 after the M6 rows (still none above Local-tested); check L01 now tolerates an M5 file that the M6.1 baseline declares and pins by hash (tools/m5_mutants.py); nothing else |

**Added (16)**

| File | Kind | What it is |
|---|---|---|
| `programme/CHANGE_RECORD_APG-M6.1.md` | records and documents | new: this record |
| `programme/E17_GOVERNANCE_RECORD.md` | records and documents | new: the auditor's 2026-10-15 directions, the proposed baseline rules and the draft RFC-01 annex |
| `programme/E17_GOVERNANCE_REGISTER.csv` | records and documents | new: the same directions as a table (G-01 to G-12) |
| `programme/E17_PHASE_0_REPOSITORY_DISCOVERY.md` | records and documents | new: the Phase 0 report as delivered |
| `regression/m6_snapshot/ENGINE_HANDOFF_REGISTER.csv` | regression data | stored copy of a delivered M6 programme table, used as the comparison for the append-only check |
| `regression/m6_snapshot/FINDINGS_REGISTER.csv` | regression data | stored copy of a delivered M6 programme table, used as the comparison for the append-only check |
| `regression/m6_snapshot/INTERPRETATIONS_REGISTER.csv` | regression data | stored copy of a delivered M6 programme table, used as the comparison for the append-only check |
| `regression/m6_snapshot/PROGRAMME_MILESTONES.csv` | regression data | stored copy of a delivered M6 programme table, used as the comparison for the append-only check |
| `regression/m6_snapshot/RFC_REGISTER.csv` | regression data | stored copy of a delivered M6 programme table, used as the comparison for the append-only check |
| `regression/m6_snapshot/STATUS_REGISTER.csv` | regression data | stored copy of a delivered M6 programme table, used as the comparison for the append-only check |
| `tests/test_det_approval_binding.py` | tests | new: 21 regression tests for the correction; the first 14 were written before it |
| `tools/make_m61_registers.py` | tools | new: adds the M6.1 rows and writes the governance register |
| `tools/probe_approval_binding.py` | tools | new: reproduces the defect in a few lines; exits 1 on the M6 code, 0 here |
| `tools/programme_check_m61.py` | tools | new: structure checks of the M6.1 records |
| `tools/run_m61_all.py` | tools | new: wrapper that runs every M6.1 check except the long mutation runs |
| `tools/run_regression_m61.py` | tools | new: shows that nothing but the declared files changed |

Run output of the correction is under `logs/m61/` and is not compared. `regression/BASELINE_M6.json` records the hash of every file above and is itself not compared.

## 4. What the correction does

| Situation | Result |
|---|---|
| An action is proposed | The proposal records the finding version and evidence digest it was written against and has `approval_state: proposed`. |
| A different person approves | The approval records `approved_version` and `approved_digest` and has `approval_state: current`. The approver may also name the version they read; if it is not the current one the approval is refused (`STALE_APPROVAL`). The proposer still cannot approve (`SELF_APPROVAL`). |
| A later run changes the evidence (new state digest) while the finding is `action_approved` or `in_progress` | The service ends the approval: the fields are cleared, the ended approval is appended to `approval_history` (who, when, what version and digest, who ended it, why, at which version and digest), the finding returns to `action_proposed`, a history event and a notification say so. Nobody has to notice. |
| The evidence is unchanged | Nothing changes; the approval stands. A figure that only drifts with time does not end it. |
| The same run is delivered again, or an older run arrives | No change (the existing replay and out-of-order rules). |
| Work is started on the ended approval | Refused: `action_proposed` cannot go to `in_progress`. |
| A fresh approval | A person other than the proposer approves; it binds the new version and digest; the first approval stays in the history. |
| A resolved or dismissed finding is reopened by a run | An approval still in force is ended in the same step (reason `finding_reopened`). |
| A record without a binding (made before this release) | Never counted as in force (`approval_current` is false); if its evidence then changes the ending is recorded with no version or digest. |

No status is added; the ten statuses and the table of allowed transitions are unchanged. The ending is a service act, not a role transition. The readings behind this are I-59 to I-64 in the interpretations register, retained for review.

## 5. Tests

`tests/test_det_approval_binding.py` has 21 tests. The first 14 were written first and run against the old code: 13 of them failed or errored there (the version-1-to-version-2, reuse and binding tests among them). Six more were added after the change for cases the first set did not reach (the run summary, the notification, reopening, a new proposal after an ending), and one, the history across two endings, was added after a package-level sabotage run showed that nothing checked it. Together they cover: binding on proposal and approval; version 1 to 2; the ended approval kept in the history with who, what and why; an action in progress; unchanged evidence; replay of the run that ended the approval; an older run; refusal of work on the ended approval; a fresh approval by a different person; the stale-version refusal; a second change while waiting; the strict `approval_current`; the run summary; the notification; reopening; and a new proposal after an ending. The probe and the full M5 and M6 suites are run by `tools/run_m61_all.py`. The M5 mutation runs for the four M5 modules are repeated (the source hash of all four changed because the new tests are in the list).

## 6. What this does not show

It does not show that the correction is independently verified: nothing here has been reviewed by anyone but the builder, and the new archive is for the auditor to verify independently. It does not show that "any change of digest" is the right measure of a material change (I-59); a threshold would be a policy decision no one has made. It does not show anything about the Engine: approval screens must pass the version they show (I-62), and real stored records need moving (I-64); both are for the Engine build. It does not start Engine #17, the versioned-baseline foundations, E1-E5 or M7.
