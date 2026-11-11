# Change record APG-M6.4: approval bound to the exact proposal (finding F-56)

| Field | Value |
|---|---|
| Release | APG-M6.4, a separately versioned correction of the delivered M6.3 package |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** F-56 is corrected in the builder's tree and stays open until the auditor verifies it independently. F-52, F-53, F-54 and F-55 also stay open until independently verified. CF-22 stays open. |
| Authority | The instruction of 2026-10-15 (14:29) to review the outstanding approval gates, prioritise CF-22, implement and test the approval path within scope, and make a new version only for a genuine code change with a change record, hashes, regression tests and independent verification. The independent audit of M6.3 had recommended keeping M6.3 unchanged unless a concrete defect was found: this is one, found by the builder (not by the auditor) and reproduced on the delivered M6.3 package. |
| Untouched | Delivered M5 ZIP `4c15ad568c5c5ff12977529ba3253c9042781e4aa272af3b87a10eab5a010be6`; delivered M6 ZIP `abcfefd9f28464de46dc205c1112b2ea33f537ef4a788562484c1d24109a1efb`; delivered M6.1 ZIP `f0fac9a8d3b5920b985f6de939580dd300f58a1cec268f11463a9ccd7823e277`; delivered M6.2 ZIP `774f835291b61a9bd7aa690389d444ddf3634c316c8298a1dc121db497421f8e`; delivered M6.3 ZIP `4379699e0cdc32c7cb0088006fc2c2ae6dd41c1f2a4e1048fdd9e01ae7a42acc`; locked Sections 00-18 (`487becabdf47796800937d13a706a19b63b7b8230ecc5354b2f01a647ae5d960`); CR-09; the RTM; RFC-01 (still PROPOSED and unnumbered); the milestones table (M7 not started); the Engine #17 governance register (G-01 to G-12, unchanged); the handoff register. |

## 1. The defect

An approval token named the finding, its version and its evidence digest, but not the proposal. Scenario, reproduced by `tools/probe_proposal_swap.py` on the delivered M6.3 package (`logs/m64/probe_on_delivered_m63.log`): an approver is shown proposal 1 and its token. Before the approver submits, a reviewer sends the finding back to `confirmed` and the owner proposes a different action against the same evidence. The finding version and the evidence digest are unchanged, so the token still matched and `approve_action()` recorded the approval against the new text, which the approver never saw. It is the same class as F-53 (an approval that is not of what was shown). M6.1 bound the approval to the evidence, M6.2 bound the proposal to its evidence and M6.3 made those checks strict; none bound the approval to the proposal itself. That is the builder's omission.

## 2. Impact

APG never carries out an action or moves money, so the weakness concerns the integrity of the approval record: what the record says a named approver approved could differ from what the approver was shown. It needs a legitimate sequence (a reviewer returns the finding and the owner proposes again) between the display of the proposal and the submission of the approval, with no change to the evidence. No approval screen or API exists yet, and no stored data outside the builder's tests exists.

## 3. Files changed

Compared byte for byte with the delivered M6.3 ZIP. All other files (the count is in `regression/BASELINE_M63.json`) are identical.

**Changed (19)**

| File | Kind | What changed and why |
|---|---|---|
| `README.md` | records and documents | adds the M6.4 section above the unchanged M6.3 text |
| `RUN_COMMANDS.txt` | records and documents | adds the M6.4 commands above the unchanged M6.3 text |
| `apg/det/findings.py` | application code | the correction itself: `proposal_ref` (a digest of the proposal on record: text, proposer, time, the version and digest it was written against, and how many proposals it replaced); `approval_token` carries it; `approve_action` and `transition` take `approving_proposal`, refuse a token without it (`APPROVAL_TOKEN_REQUIRED`), refuse another proposal (`PROPOSAL_CHANGED`) after the evidence checks, store `approved_proposal`; `approval_current` also needs it to equal the proposal on record; ended approvals, proposal history and events carry the reference |
| `programme/CARRIED_FORWARD_REGISTER.csv` | records and documents | row CF-25 appended (the approval request boundary is not built); no earlier row changed |
| `programme/FINDINGS_REGISTER.csv` | records and documents | row F-56 appended; no earlier row changed (F-52 to F-55 are not rewritten) |
| `programme/INTERPRETATIONS_REGISTER.csv` | records and documents | rows I-75 to I-78 appended; no earlier row changed |
| `programme/STATUS_REGISTER.csv` | records and documents | rows SR-72 and SR-73 appended; no earlier row changed |
| `tests/test_det_approval_binding.py` | tests | updated for the proposal reference the approval entry point now requires (calls and fixtures only; every assertion is kept) |
| `tests/test_det_proposal_binding.py` | tests | updated for the proposal reference the approval entry point now requires (calls and fixtures only; every assertion is kept) |
| `tests/test_det_version_types.py` | tests | updated for the proposal reference the approval entry point now requires (calls and fixtures only; every assertion is kept); one test added in M6.3 is kept and its approvable shape now includes the reference |
| `tools/m5_mutants.py` | tools | runs the new test file in the M5 mutation run (added to its list of tests); nothing else |
| `tools/make_m0.py` | tools | runs the M6.4 register step after the M6.3 one, so the derived-files check regenerates the programme tables with the M6.4 rows; nothing else |
| `tools/probe_malformed_proposal_version.py` | tools | passes the proposal reference the entry point now requires; the scenarios and the expected output are unchanged |
| `tools/programme_check_m62.py` | tools | check N08 accepts the status `Open - not built` (CF-25 is appended in M6.4); nothing else |
| `tools/programme_check_m63.py` | tools | checks N05, N06 and N07 look at CF-01 to CF-24 by identifier and accept the status `Open - not built`; nothing else |
| `tools/run_regression_m6.py` | tools | accepts files the M6.4 baseline declares and pins by hash; check L05 accepts status-register rows with milestone M6.4; nothing else |
| `tools/run_regression_m61.py` | tools | accepts the files the M6.4 baseline declares and pins (R02, R03), files it adds (R04) and rows with milestone M6.4 (R10, R11); every other check is unchanged |
| `tools/run_regression_m62.py` | tools | accepts the files the M6.4 baseline declares and pins (R02, R03), files it adds, a longer known set and rows with milestone M6.4 (R10, R11); every other check is unchanged |
| `tools/run_regression_m63.py` | tools | accepts the files the M6.4 baseline declares and pins (R02, R03), files it adds, a longer known set, rows with milestone M6.4 and CF-25 after CF-24 (R10, R11); every other check is unchanged |

**Added (15)**

| File | Kind | What it is |
|---|---|---|
| `programme/CHANGE_RECORD_APG-M6.4.md` | records and documents | new: this record |
| `regression/m63_snapshot/CARRIED_FORWARD_REGISTER.csv` | regression data | stored copy of a delivered M6.3 programme table, used as the comparison for the append-only check |
| `regression/m63_snapshot/E17_GOVERNANCE_REGISTER.csv` | regression data | stored copy of a delivered M6.3 programme table, used as the comparison for the append-only check |
| `regression/m63_snapshot/ENGINE_HANDOFF_REGISTER.csv` | regression data | stored copy of a delivered M6.3 programme table, used as the comparison for the append-only check |
| `regression/m63_snapshot/FINDINGS_REGISTER.csv` | regression data | stored copy of a delivered M6.3 programme table, used as the comparison for the append-only check |
| `regression/m63_snapshot/INTERPRETATIONS_REGISTER.csv` | regression data | stored copy of a delivered M6.3 programme table, used as the comparison for the append-only check |
| `regression/m63_snapshot/PROGRAMME_MILESTONES.csv` | regression data | stored copy of a delivered M6.3 programme table, used as the comparison for the append-only check |
| `regression/m63_snapshot/RFC_REGISTER.csv` | regression data | stored copy of a delivered M6.3 programme table, used as the comparison for the append-only check |
| `regression/m63_snapshot/STATUS_REGISTER.csv` | regression data | stored copy of a delivered M6.3 programme table, used as the comparison for the append-only check |
| `tests/test_det_proposal_identity.py` | tests | new: 29 regression tests for the correction (25 written first, 4 added after the change) |
| `tools/make_m64_registers.py` | tools | new: adds the M6.4 rows |
| `tools/probe_proposal_swap.py` | tools | new: reproduces the defect in a few lines (an approval of a proposal replaced after it was shown); exits 1 on the M6.3 code, 0 here |
| `tools/programme_check_m64.py` | tools | new: structure checks of the M6.4 records |
| `tools/run_m64_all.py` | tools | new: wrapper that runs every M6.4 check except the long mutation runs |
| `tools/run_regression_m64.py` | tools | new: shows that nothing but the declared files changed |

Run output of the correction is under `logs/m64/` and is not compared. `regression/BASELINE_M63.json` records the hash of every file above and is itself not compared. The M6.3 logs under `logs/m63/` are carried unchanged.

## 4. What the correction does

| Situation | Result |
|---|---|
| `approval_token(finding)` | Returns the finding id, version, evidence digest and `proposal`: the reference of the proposal on record (a digest of its text, proposer, time, the version and digest it was written against, and the number of proposals it replaced), or `None` if there is no usable proposal. |
| `approve_action` without a proposal reference, or with one that is not a non-empty text | Refused with `APPROVAL_TOKEN_REQUIRED` and audited, before anything is looked at. |
| An approval that names a proposal other than the one on record (it was replaced after it was shown) | Refused with `PROPOSAL_CHANGED` and audited; the record is not changed. The same text proposed again counts as another proposal, because the count of replaced proposals is part of the reference (I-75). |
| A proposal on record that cannot be identified (damaged) | Refused with `PROPOSAL_CHANGED`, whatever is named. |
| An accepted approval | Stores `approved_proposal`; the reference is also in the approval event, in the proposal history and in an ended approval's history. `approval_current` is true only if the stored reference equals the reference of the proposal on record. |
| An approval stored before M6.4 | Has no `approved_proposal`, so it is not an approval in force and a person approves again (I-77). |
| Order of the refusals | Self-approval, malformed named value, older version or digest, proposal written against old evidence, then proposal not the one shown (I-78). |
| The lower-level `transition` | Keeps the optional argument for existing callers and checks a reference when one is named (I-76). That a screen or API uses `approve_action` is for the Engine build (CF-22). |
| Everything else | Unchanged from M6.3: ten statuses, 14 transitions, the proposer cannot approve, stale proposals and ended approvals are kept in the history, strict version and digest rules (F-55). |

## 5. Tests

`tests/test_det_proposal_identity.py` has 29 tests. 25 were written before the change; 4 (class `TestAStoredProposalThatIsEditedIsNotTheOneThatWasShown`) were added after it, because the builder's first sabotage run showed two corruptions of the new code that the first 25 did not catch (the proposer left out of the reference; the refusal of a proposal that cannot be identified removed). Run against the delivered M6.3 code, 28 of them fail or error (the rest cover behaviour that was already right, for example a normal approval of the proposal that was shown). They cover the reproduction through the real `approve_action()` path with no change to the record on refusal, the token carrying the reference, the entry point failing closed on missing and malformed references, the reference being kept in the record, events and history, replay and ordering of the refusals, and that nothing else moved (the same text proposed again is another proposal; the proposer still cannot approve; evidence changes still end the approval).

Three existing test files call `approve_action` or build approvals by hand, so they were updated (calls and fixtures only; every assertion is kept). Run unchanged against the corrected code, 12 of the 179 tests in those files and their neighbours fail or error (`logs/m64/m63_tests_on_m64_code.log`): they build approvals without the reference the entry point now requires. No M5 or earlier test changed. The whole unit suite, the probes, the M5 and M6 wrappers and the regressions are run by `tools/run_m64_all.py`. The M5 mutation runs for the four M5 modules are repeated (the source hash changed because `findings.py` and the test list changed).

## 6. Results, and how each is classified

Three classes are kept apart. **Builder-run**: run by the builder in the builder's sandbox; this is the status of every result of this release. **Reproduced by the builder**: the F-56 defect on the delivered M6.3 tree (`logs/m64/probe_on_delivered_m63.log`); it was found by the builder, so no auditor reproduction exists. **Independently reviewed**: nothing in this release. The audit of APG-M6.3 is an independent review of M6.3: it reproduced the M6.3 unit suite in groups, the non-static regression, the wrapper and the 245-mutant run, and the builder's standalone sabotage runner covers the 42 package-level corruptions. None of that is carried over to M6.4.

The test, mutation, sabotage and clean-extraction results are in the documents file delivered with the archive and in `logs/m64/`; they are not copied into this record because they are produced after it is written.

## 7. Carried forward

All of these remain open and are untouched by this release except as stated; they are listed with their sources in `programme/CARRIED_FORWARD_REGISTER.csv` (CF-01 to CF-25): all M6 data is synthetic and the ports were tested only against in-memory references; no Anchor Engine, production database, event bus, AUIF or Governor repository is integrated; the event and provenance gaps; tenant and project isolation (F-39, EDR-29; not fixed here); the approval request boundary (CF-25, new): a replay-safe request, project-level authorisation and boundary audit are not built and CF-22 stays open; invoice-only cost coverage and the missing cost components; quantity reconciliation inputs, payment-term economics and capacity controls; M6 portfolio purchasing is a backward-looking view; the verification limits of the earlier audits (CF-23, CF-24).

## 8. What this does not show

It does not show that the correction is independently verified: nothing here has been reviewed by anyone but the builder, and the new archive is for the auditor to verify. It does not show that an approval screen or API exists or is safe: none exists, and a request that is safe to repeat, authorisation by project and a boundary audit are not built (CF-25). It does not show that the proposal reference covers every way a proposal could be replaced in a real record store (I-75). It does not show anything about the Engine. It does not make the prototype production-ready or integrated, and it does not start Engine #17, the versioned-baseline foundations or M7.
