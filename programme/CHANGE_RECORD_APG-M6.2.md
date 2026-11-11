# Change record APG-M6.2: proposal binding (findings F-53 and F-54)

| Field | Value |
|---|---|
| Release | APG-M6.2, a separately versioned correction of the delivered M6.1 package |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** F-53 and F-54 are corrected in the builder's tree and stay open until the auditor verifies them independently. F-52 also stays open until independently verified. |
| Authority | The independent audit of APG-M6.1 and its action brief (2026-10-15) directed: investigate and correct the stale-proposal approval defect first; write failing tests first; preserve the M5, M6 and M6.1 ZIPs byte for byte; deliver a separately versioned archive and documents with a complete file-level change record and updated registers; refuse approval of a proposal written against old evidence even when `approving_version` is omitted; keep the exact old proposal and approval context in the history; require the version (or an equivalent fail-closed token) at the future screen or API boundary; run the complete relevant suites and repeat the relevant mutation runs; record timeouts as incomplete; carry forward the open issues. |
| Untouched | Delivered M5 ZIP `4c15ad568c5c5ff12977529ba3253c9042781e4aa272af3b87a10eab5a010be6`; delivered M6 ZIP `abcfefd9f28464de46dc205c1112b2ea33f537ef4a788562484c1d24109a1efb`; delivered M6.1 ZIP `f0fac9a8d3b5920b985f6de939580dd300f58a1cec268f11463a9ccd7823e277`; locked Sections 00-18 (`487becabdf47796800937d13a706a19b63b7b8230ecc5354b2f01a647ae5d960`); CR-09; the RTM; RFC-01 (still PROPOSED and unnumbered); the milestones table (M7 not started); the Engine #17 governance register (G-01 to G-12, unchanged). |

## 1. The defect

APG-M6.1 bound an approval to the finding version and evidence digest and ended it when the evidence changed. It also recorded, on the action, the version and digest the proposal was written against. But nothing compared those at approval. The audit's reproduction (its section 5), which the builder repeated on the delivered M6.1 tree with the same evidence digests: an action is proposed at version 1 (`67a504082f14...`); a later run changes the evidence to version 2 (`619f1afb69a4...`) while the finding is still `action_proposed`; a different person approves without naming a version; the approval is accepted and bound to version 2, although the proposal and its text were written against the version-1 evidence. The same gap let an old proposal be approved again after an approval had been ended by changed evidence. The M6.1 tests did not cover either case; that is the builder's omission. `tools/probe_stale_proposal.py` shows it: on the M6.1 code it prints `APPROVE   no version named -> ACCEPTED action_approved at version 2` and `DEFECT PRESENT`. It is recorded as F-53.

The audit also asked (its section 6) whether the history must keep the exact approved text and proposal metadata. In M6.1 a new proposal overwrote the action record and only the approval history was carried; the history events named neither the text nor the versions; and an ended approval kept no text or rationale. That is F-54.

## 2. Impact

APG never carries out an action or moves money, so the defect harmed the integrity of the record: an approver could appear to approve a proposal on evidence it was not written for, and an approval could not later be reconstructed from the history alone. It could occur only when the evidence changed between a proposal and its approval, or after an approval had been ended. No stored data outside the builder's own tests exists.

## 3. Files changed

Compared byte for byte with the delivered M6.1 ZIP. All other files (the count is in `regression/BASELINE_M61.json`) are identical.

**Changed (12)**

| File | Kind | What changed and why |
|---|---|---|
| `README.md` | records and documents | adds the M6.2 section above the unchanged M6.1 text |
| `RUN_COMMANDS.txt` | records and documents | adds the M6.2 commands above the unchanged M6.1 text |
| `apg/det/findings.py` | application code | the correction itself: `proposal_current`, the `STALE_PROPOSAL` gate in the approval step, `approving_digest`, `approve_action`, `approval_token`, `approvable`, proposals marked stale by the run that changes the evidence, `proposal_history`, and the exact action text and versions in the proposal and approval events and in an ended approval |
| `programme/FINDINGS_REGISTER.csv` | records and documents | rows F-53 and F-54 appended; no earlier row changed (F-52 is not rewritten) |
| `programme/INTERPRETATIONS_REGISTER.csv` | records and documents | rows I-65 to I-70 appended; no earlier row changed |
| `programme/STATUS_REGISTER.csv` | records and documents | rows SR-66 to SR-69 appended; no earlier row changed |
| `tests/test_det_approval_binding.py` | tests | the M6.1 tests: the ones that approved straight after an ended approval now propose again first; `approval_current` is tested with a current proposal and two more bad cases; the number of tests (21) is unchanged. This is an M6.1 file, not a frozen M5 test |
| `tools/m5_mutants.py` | tools | runs the new test file in the M5 mutation run (added to its list of tests and made the first test run for `findings.py`) |
| `tools/make_m0.py` | tools | runs the M6.2 register step after the M6.1 one, so the derived-files check regenerates the programme tables with the M6.2 rows; nothing else |
| `tools/programme_check_m6.py` | tools | check L08 (the four auditor M5-review findings) is limited to findings with milestone M6, because later correction releases record their own auditor findings under their own milestone; nothing else |
| `tools/run_regression_m6.py` | tools | check L05 accepts status-register rows with milestone M6.2; check L01 also tolerates an M5 file that the M6.2 baseline declares and pins by hash (tools/m5_mutants.py); nothing else |
| `tools/run_regression_m61.py` | tools | accepts files the M6.2 baseline declares and pins (R02, R03), files it adds (R04) and rows with milestone M6.2 after the M6.1 rows (R10, R11); every other check is unchanged |

**Added (15)**

| File | Kind | What it is |
|---|---|---|
| `programme/CARRIED_FORWARD_REGISTER.csv` | records and documents | new: the open issues of the earlier M6 audit and the M6.1 audit that this release carries forward (CF-01 to CF-23); it closes nothing |
| `programme/CHANGE_RECORD_APG-M6.2.md` | records and documents | new: this record |
| `regression/m61_snapshot/E17_GOVERNANCE_REGISTER.csv` | regression data | stored copy of a delivered M6.1 programme table, used as the comparison for the append-only check |
| `regression/m61_snapshot/ENGINE_HANDOFF_REGISTER.csv` | regression data | stored copy of a delivered M6.1 programme table, used as the comparison for the append-only check |
| `regression/m61_snapshot/FINDINGS_REGISTER.csv` | regression data | stored copy of a delivered M6.1 programme table, used as the comparison for the append-only check |
| `regression/m61_snapshot/INTERPRETATIONS_REGISTER.csv` | regression data | stored copy of a delivered M6.1 programme table, used as the comparison for the append-only check |
| `regression/m61_snapshot/PROGRAMME_MILESTONES.csv` | regression data | stored copy of a delivered M6.1 programme table, used as the comparison for the append-only check |
| `regression/m61_snapshot/RFC_REGISTER.csv` | regression data | stored copy of a delivered M6.1 programme table, used as the comparison for the append-only check |
| `regression/m61_snapshot/STATUS_REGISTER.csv` | regression data | stored copy of a delivered M6.1 programme table, used as the comparison for the append-only check |
| `tests/test_det_proposal_binding.py` | tests | new: 47 regression tests for the correction, written first |
| `tools/make_m62_registers.py` | tools | new: adds the M6.2 rows and writes the carried-forward register |
| `tools/probe_stale_proposal.py` | tools | new: reproduces the audit's defect in a few lines; exits 1 on the M6.1 code, 0 here |
| `tools/programme_check_m62.py` | tools | new: structure checks of the M6.2 records |
| `tools/run_m62_all.py` | tools | new: wrapper that runs every M6.2 check except the long mutation runs |
| `tools/run_regression_m62.py` | tools | new: shows that nothing but the declared files changed |

Run output of the correction is under `logs/m62/` and is not compared. `regression/BASELINE_M61.json` records the hash of every file above and is itself not compared. The M6.1 logs under `logs/m61/` are carried unchanged.

## 4. What the correction does

| Situation | Result |
|---|---|
| An action is proposed | The proposal records the finding version and evidence digest it was written against (`proposed_version`, `proposed_digest`) and has `proposal_state: current`. The proposal event carries the exact action text and those two values. Any earlier proposal that is being replaced is appended in full to `action.proposal_history` (text, proposer, time, version, digest, approval state, whether it was stale, who replaced it and at which version and digest). |
| A later run changes the evidence while the finding has an action (`action_proposed`, `action_approved`, `in_progress`, or a reopened finding) | The proposal is marked `stale` in the same step; the `updated` (or `reopened`) event says so and names the version it was written against; the run summary lists it under `proposals_stale`. An approval in force is ended as in M6.1, and the ended approval now keeps the action text, the proposer, the proposal version and digest and the approval rationale. |
| Someone tries to approve a stale proposal | Refused with `STALE_PROPOSAL` and an audited reason naming both versions, **whether or not the approver names a version**; naming the current version or digest does not help. Naming an older version or digest is refused as `STALE_APPROVAL` first. The proposer is still refused as `SELF_APPROVAL` before anything else. A refused approval changes nothing in the record. |
| The stale proposal is to be replaced | A reviewer returns the finding to `confirmed` with a reason, and the owner proposes the action again against the current evidence. This is the route the lifecycle already had; the table of 14 allowed transitions and the ten statuses are unchanged (I-66). Approval of the new proposal then works, with or without the version named. |
| The evidence is unchanged, or the same run is delivered again, or an older run arrives | Nothing changes; the proposal stays current (or stays stale if it already was). |
| A screen or API approves | It calls `approve_action(scoped, clock, finding, version, digest, rationale)`, which refuses with `APPROVAL_TOKEN_REQUIRED` unless a whole-number version and a non-empty digest are given (`approval_token(finding)` returns what the screen must show and hand back); everything else is checked as above. `approvable(finding)` says whether an action can be approved now and why not. The lower-level `transition` keeps its optional arguments for existing callers. That a real screen or API uses `approve_action` and passes what it displayed is for the Engine build and cannot be enforced here (I-68). |
| A record made before M6.1 (no recorded version or digest) | Never counted as a current proposal (`proposal_current` is false), so it cannot be approved until proposed again. |

The readings behind this are I-65 to I-70 in the interpretations register, retained for review.

## 5. Tests

`tests/test_det_proposal_binding.py` has 47 tests. They were written before the change. Run against the delivered M6.1 code, 11 of them fail and 29 error (the rest cover behaviour that was already right: for example the proposer being refused as self-approver, and a fresh proposal being approvable). They cover the cases the audit listed: evidence changing while the status is `action_proposed`; approval with and without `approving_version` after that change (current version, older version, current digest, older digest); evidence changing after an approval was ended and before re-approval; a fresh, updated proposal followed by approval; unchanged proposal and evidence; replay of the run and an older run arriving late; a later run with the same evidence; and the preservation of the exact old proposal and approval context when a proposal is replaced twice. They also cover the run summary, the stale mark, the strict `proposal_current` and `approval_current`, the unchanged transition table, only a reviewer sending a proposal back, and the fail-closed entry point (missing, wrongly typed, older and current tokens; the other gates still apply).

`tests/test_det_approval_binding.py` (the M6.1 file, still 21 tests) was changed: the tests that approved straight after an ended approval now send the proposal back and propose it again first, because M6.2 refuses the direct approval; `approval_current` is tested with a current proposal and with two more bad cases. Run as delivered in M6.1 against the M6.2 code, 4 of the 21 no longer pass: `test_an_approval_that_names_a_version_other_than_the_current_one_is_refused`, `test_the_proposer_still_cannot_approve_and_a_new_approval_binds_the_new_version_and_digest`, `test_two_endings_leave_two_entries_in_order_in_the_approval_history`, `test_only_a_current_approval_of_exactly_this_version_and_digest_counts`. That is the intended change of behaviour, and it is recorded here rather than hidden.

No frozen M5 or earlier test was changed; all 39 tests of `test_det_findings.py` and the rest of the M5 detection and finding tests pass unchanged on the corrected code. The whole unit suite, the probes, the M5 and M6 wrappers and the regressions are run by `tools/run_m62_all.py`. The M5 mutation runs for the four M5 modules are repeated (the source hash of all four changed because `findings.py` and the test list changed).

## 6. Results, and how each is classified

Three classes are kept apart. **Builder-run**: run by the builder in the builder's sandbox; this is the status of every result in this release. **Reproduced by the builder from the auditor's description**: the F-53 defect on the delivered M6.1 tree, with the same digests (`logs/m62/probe_on_delivered_m61.log`). **Independently reviewed**: nothing in this release. The audit of APG-M6.1 is an independent review of M6.1, not of M6.2; its own hash, probe and test results do not carry over. The auditor's full-suite and full-wrapper runs timed out in the auditor's environment and are not recorded as pass or fail; the mutation and sabotage figures of M6.1 were builder-reported only. The mutation and sabotage figures of this release are builder-reported only too. The build's own run times are in the documents so that a time limit can be set above them; a run cut off by a limit is incomplete, not a pass.

The test, mutation, sabotage and clean-extraction results are in the documents file delivered with the archive and in `logs/m62/`; they are not copied into this record because they are produced after it is written.

## 7. Carried forward

All of these remain open and are untouched by this release; they are listed with their sources in `programme/CARRIED_FORWARD_REGISTER.csv` (CF-01 to CF-23): all M6 data is synthetic and the ports were tested only against in-memory references; no Anchor Engine, production database, event bus, AUIF or Governor repository is integrated; the event and provenance gaps (no event store, no `recorded_at`, no single `provenance_id`, no correction or supersession links, no baseline version or hash, unvalidated currency, unit and quantity); tenant and project isolation (F-39, EDR-29; not reproduced in the M6.1 audit and not fixed here); invoice-only cost coverage and the missing cost components; quantity reconciliation inputs, payment-term economics and capacity controls; M6 portfolio purchasing is a backward-looking rate-gap estimate, not the specified forward aggregation; no realised-outcome workflow and no finance assumptions; Engine #17 is not built; RFC-01 is PROPOSED and unnumbered; the Engine #1-#18 mapping is not authoritative; the V1-V4 baseline rules are proposed only; no third lifecycle; and the existing open decisions. The integration gate (a real approval screen or API must call the fail-closed entry point and pass the version it displayed) is CF-22, for the handoff package at M12.

## 8. What this does not show

It does not show that the correction is independently verified: nothing here has been reviewed by anyone but the builder, and the new archive is for the auditor to verify. It does not show that "any change of digest" is the right measure of a material change (I-59, I-65); a threshold would be a policy decision no one has made. It does not show that the history keeps everything an auditor may want (I-69). It does not show anything about the Engine: a screen or API must use `approve_action`, and real stored records need moving (I-64, I-68). It does not make the prototype production-ready or integrated, and it does not start Engine #17, the versioned-baseline foundations, E1-E5 or M7.
