# Change record APG-M6.5: the approval gate in the lowest-level call (finding F-57)

| Field | Value |
|---|---|
| Release | APG-M6.5, a separately versioned correction of the delivered M6.4 package |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** F-57 is corrected in the builder's tree and stays open until the auditor verifies it independently. F-52, F-53, F-54, F-55 and F-56 also stay open until independently verified. CF-22 stays open. |
| Authority | The instruction relayed by the product owner after the independent audit of M6.4: do not start the approval request boundary (APG-M9.1) yet; investigate and fix the bypass in a new correction; preserve the delivered M6.3 and M6.4 archives unchanged; add regression tests; run the relevant regression and mutation and sabotage checks; keep F-56 and CF-22 open; do not start Engine #17 or M7; do not treat RFC-01 as approved. |
| Untouched | Delivered M5 ZIP `4c15ad568c5c5ff12977529ba3253c9042781e4aa272af3b87a10eab5a010be6`; delivered M6 ZIP `abcfefd9f28464de46dc205c1112b2ea33f537ef4a788562484c1d24109a1efb`; delivered M6.1 ZIP `f0fac9a8d3b5920b985f6de939580dd300f58a1cec268f11463a9ccd7823e277`; delivered M6.2 ZIP `774f835291b61a9bd7aa690389d444ddf3634c316c8298a1dc121db497421f8e`; delivered M6.3 ZIP `4379699e0cdc32c7cb0088006fc2c2ae6dd41c1f2a4e1048fdd9e01ae7a42acc`; delivered M6.4 ZIP `ae481618dce8a2426d84c0353659cd9992a214ee29ee122329fd5ffc766c8e57`; locked Sections 00-18 (`487becabdf47796800937d13a706a19b63b7b8230ecc5354b2f01a647ae5d960`); CR-09; the RTM; RFC-01 (still PROPOSED and unnumbered); the milestones table (M7 not started); the Engine #17 governance register (G-01 to G-12, unchanged); the handoff register; the carried-forward register (no row added or changed). |

## 1. The defect

M6.4 made the entry point `approve_action` refuse an approval that did not name the finding version, the evidence digest and the proposal reference the approver was shown. The lower-level call `transition(scoped, clock, fid, 'action_approved', ...)` still took those three as optional arguments (I-76, a builder reading retained for review, not approved) and checked only what was named. Reproduced by `tools/probe_transition_bypass.py` on the delivered M6.4 package (`logs/m65/probe_on_delivered_m64.log`): an approval that names nothing, one that names only the version, only the digest or only the proposal reference, and each pair of the three is accepted and recorded as an approval in force; so is the complete one. The version and the digest had been optional there since M6.1; the proposal reference since M6.4. Any code that calls `transition` directly, including a future screen, API or script that did not use `approve_action`, could therefore record an approval of something the approver was never shown. It is the same class as F-52, F-53 and F-56 and it is the builder's omission: M6.4 documented the optional arguments instead of closing them.

The report reached the builder through the product owner as a summary of the independent audit of M6.4 (the bypass through the lower-level function); the builder did not receive the audit text in this session and reproduced the defect itself.

## 2. Impact

APG never carries out an action or moves money, so the weakness concerns the integrity of the approval record: the record could say that a named approver approved a proposal that the approver was not shown or that no longer matched the evidence. It needs a caller that uses the lower-level function. No approval screen or API exists yet, and no stored data outside the builder's tests exists. The entry point `approve_action` was already safe and is not weakened.

## 3. Files changed

Compared byte for byte with the delivered M6.4 ZIP. All other files (the count is in `regression/BASELINE_M64.json`) are identical.

**Changed (23)**

| File | Kind | What changed and why |
|---|---|---|
| `README.md` | records and documents | adds the M6.5 section above the unchanged M6.4 text |
| `RUN_COMMANDS.txt` | records and documents | adds the M6.5 commands above the unchanged M6.4 text |
| `apg/det/findings.py` | application code | the correction itself: `transition` refuses an approval unless the version, the evidence digest and the proposal reference are all named and well formed (`APPROVAL_TOKEN_REQUIRED`, after the self-approval check), then checks each against the record (`STALE_APPROVAL`, `STALE_PROPOSAL`, `PROPOSAL_CHANGED`); a proposal that cannot be identified is refused before the reference is compared; moving a finding to `in_progress` requires `approval_current` (`APPROVAL_NOT_CURRENT`); `approve_action` is unchanged except that its comment says the gate is not held by the entry point alone |
| `programme/FINDINGS_REGISTER.csv` | records and documents | row F-57 appended; no earlier row changed (F-52 to F-56 are not rewritten) |
| `programme/INTERPRETATIONS_REGISTER.csv` | records and documents | rows I-79 and I-80 appended; no earlier row changed (I-76 is withdrawn by I-79, not rewritten) |
| `programme/STATUS_REGISTER.csv` | records and documents | rows SR-74 and SR-75 appended; no earlier row changed |
| `tests/helpers_det.py` | tests | one helper added, `approve_filled`: approves through the lower-level call and names whatever the test does not name from the record; nothing else changed |
| `tests/test_det_approval_binding.py` | tests | calls only: approvals made through the lower-level call now name the whole token (the helper `approve_filled` names whatever the test does not name, from the record as the approver would have been shown it); every assertion is kept |
| `tests/test_det_findings.py` | tests | calls only: approvals made through the lower-level call now name the whole token (the helper `approve_filled` names whatever the test does not name, from the record as the approver would have been shown it); every assertion is kept (an M5 test file; its `t()` wrapper routes approvals through the helper) |
| `tests/test_det_findings_edges.py` | tests | calls only: approvals made through the lower-level call now name the whole token (the helper `approve_filled` names whatever the test does not name, from the record as the approver would have been shown it); every assertion is kept (an M5 test file) |
| `tests/test_det_proposal_binding.py` | tests | calls only: approvals made through the lower-level call now name the whole token (the helper `approve_filled` names whatever the test does not name, from the record as the approver would have been shown it); every assertion is kept |
| `tests/test_det_proposal_identity.py` | tests | calls only: approvals made through the lower-level call now name the whole token (the helper `approve_filled` names whatever the test does not name, from the record as the approver would have been shown it); every assertion is kept, except the two tests listed in section 5 whose assertions changed (the lower-level call no longer accepts an approval that names nothing) |
| `tests/test_det_version_types.py` | tests | calls only: approvals made through the lower-level call now name the whole token (the helper `approve_filled` names whatever the test does not name, from the record as the approver would have been shown it); every assertion is kept, except the three tests listed in section 5 whose assertions changed (a damaged record gives no token to name) |
| `tools/m5_mutants.py` | tools | runs the new test file in the M5 mutation run (added to its list of tests); nothing else |
| `tools/make_m0.py` | tools | runs the M6.5 register step after the M6.4 one, so the derived-files check regenerates the programme tables with the M6.5 rows; nothing else |
| `tools/probe_approval_binding.py` | tools | names the whole token (version, digest, proposal reference) to the lower-level call, only for the parameters the code under test has, so it still runs on the earlier packages; the scenario and the expected output are unchanged |
| `tools/probe_malformed_proposal_version.py` | tools | names the digest and the proposal reference with the malformed version it tests; the scenarios and the expected output are unchanged |
| `tools/probe_stale_proposal.py` | tools | adds a case that names the whole token as shown (STALE_PROPOSAL) because naming little is now refused earlier (APPROVAL_TOKEN_REQUIRED); the final approval names the whole token; the expected output line is unchanged |
| `tools/run_regression_m6.py` | tools | accepts the files the M6.5 baseline declares and pins by hash; check L05 accepts status-register rows with milestone M6.5; nothing else |
| `tools/run_regression_m61.py` | tools | accepts the files the M6.5 baseline declares and pins (R02, R03), files it adds (R04) and rows with milestone M6.5 (R10, R11); every other check is unchanged |
| `tools/run_regression_m62.py` | tools | accepts the files the M6.5 baseline declares and pins (R02, R03), files it adds (R04) and rows with milestone M6.5 (R10, R11); every other check is unchanged |
| `tools/run_regression_m63.py` | tools | accepts the files the M6.5 baseline declares and pins (R02, R03), files it adds (R04) and rows with milestone M6.5 (R10, R11); every other check is unchanged |
| `tools/run_regression_m64.py` | tools | accepts the files the M6.5 baseline declares and pins (R02, R03), files it adds (R04) and rows with milestone M6.5 (R10, R11); every other check is unchanged |

**Added (15)**

| File | Kind | What it is |
|---|---|---|
| `programme/CHANGE_RECORD_APG-M6.5.md` | records and documents | new: this record |
| `regression/m64_snapshot/CARRIED_FORWARD_REGISTER.csv` | regression data | stored copy of a delivered M6.4 programme table, used as the comparison for the append-only check |
| `regression/m64_snapshot/E17_GOVERNANCE_REGISTER.csv` | regression data | stored copy of a delivered M6.4 programme table, used as the comparison for the append-only check |
| `regression/m64_snapshot/ENGINE_HANDOFF_REGISTER.csv` | regression data | stored copy of a delivered M6.4 programme table, used as the comparison for the append-only check |
| `regression/m64_snapshot/FINDINGS_REGISTER.csv` | regression data | stored copy of a delivered M6.4 programme table, used as the comparison for the append-only check |
| `regression/m64_snapshot/INTERPRETATIONS_REGISTER.csv` | regression data | stored copy of a delivered M6.4 programme table, used as the comparison for the append-only check |
| `regression/m64_snapshot/PROGRAMME_MILESTONES.csv` | regression data | stored copy of a delivered M6.4 programme table, used as the comparison for the append-only check |
| `regression/m64_snapshot/RFC_REGISTER.csv` | regression data | stored copy of a delivered M6.4 programme table, used as the comparison for the append-only check |
| `regression/m64_snapshot/STATUS_REGISTER.csv` | regression data | stored copy of a delivered M6.4 programme table, used as the comparison for the append-only check |
| `tests/test_det_transition_gate.py` | tests | new: 36 regression tests for the correction (33 written before the correction, 3 added after it; 8 of the 36 fail on the M6.4 code) |
| `tools/make_m65_registers.py` | tools | new: adds the M6.5 rows |
| `tools/probe_transition_bypass.py` | tools | new: reproduces the defect in a few lines (the lower-level call accepts incomplete approvals); exits 1 on the M6.4 code, 0 here |
| `tools/programme_check_m65.py` | tools | new: structure checks of the M6.5 records |
| `tools/run_m65_all.py` | tools | new: wrapper that runs every M6.5 check except the long mutation runs |
| `tools/run_regression_m65.py` | tools | new: shows that nothing but the declared files changed |

Run output of the correction is under `logs/m65/` and is not compared. `regression/BASELINE_M64.json` records the hash of every file above and is itself not compared. The M6.4 logs under `logs/m64/` are carried unchanged.

## 4. What the correction does

| Situation | Result |
|---|---|
| `transition(..., 'action_approved', ...)` that does not name a version, an evidence digest and a proposal reference, each well formed (a version is a whole number of at least 1 and not a boolean; a digest and a proposal reference are non-empty texts) | Refused with `APPROVAL_TOKEN_REQUIRED` and audited; the record is not changed. Every proper subset of the three is refused. |
| A well-formed version or digest that is not the current one | Refused with `STALE_APPROVAL`, as before. |
| A proposal written against older evidence | Refused with `STALE_PROPOSAL`, as before. |
| A proposal reference that is not the one on record, or a proposal on record that cannot be identified | Refused with `PROPOSAL_CHANGED`, as before; the unidentifiable proposal is now refused before the reference is compared (the comparison alone would have refused it for the wrong reason). |
| Order of the refusals in `transition` | Role and person checks, then self-approval, then an incomplete or malformed token, then an older version or digest, then a stale proposal, then the proposal reference (I-79; extends I-78). The entry point `approve_action` still checks the token first. |
| Moving a finding from `action_approved` to `in_progress` | Requires `approval_current` to be true for the finding as stored, otherwise `APPROVAL_NOT_CURRENT` (I-80). Through the lifecycle this changes nothing, because detection already returns an approved finding to `action_proposed` when the evidence changes; it matters for a record changed outside the lifecycle. |
| Every other transition | Unchanged. No token is needed to confirm, propose, dismiss, start, resolve, reopen or supersede. |
| Replay | A second submission of the same approval is refused as not allowed (the finding is no longer `action_proposed`) and changes nothing. |
| Everything else | Unchanged from M6.4: ten statuses, 14 transitions, the proposer cannot approve, evidence changes end an approval, proposals and ended approvals are kept in the history, strict version and digest rules (F-55), the proposal reference (F-56). |

## 5. Tests

`tests/test_det_transition_gate.py` has 36 tests. 33 were written before the change and run against the delivered M6.4 code (34 were written; one was removed before the change because it did not test what it claimed: the two test worlds it compared produced the same token); 3 (class `TestTheEntryPointStillRefusesFirst`) were added after it, because the builder's first mutation run left one mutant alive: the entry point's own early check of the token, which the check in `transition` now makes redundant except for what it answers first (an unknown finding, the proposer). Run against the delivered M6.4 code, 8 of them fail or error (the rest cover behaviour that was already right). They cover: every incomplete approval (all eight subsets) through the lower-level call; malformed versions, digests and references (booleans, zero, negatives, floats, text where a number belongs, empty or blank text, lists, mappings, bytes, the token itself); well-formed but wrong items; a proposal replaced after it was shown, written again with the same words, edited in the store, or with no usable reference; evidence that moved after the token was issued; replay, also after an approval was ended by new evidence; who may approve (self-approval first, role, a service, another tenant); that the other transitions need no token; and the re-check on starting the action, for nine ways a stored approval can stop being in force.

Seven existing test files were changed because they approve through the lower-level call, build approval records by hand or hold the shared fixture. In all of them the change is to the call: the approval now names the whole token (the helper `approve_filled` names whatever a test does not name, taken from the record as the approver would have been shown it; what a test names itself, including a wrong or malformed value, is passed through). Two of the files, `test_det_findings.py` and `test_det_findings_edges.py`, are M5 files; no other M5 or earlier test changed. Run unchanged against the corrected code, 56 of the 605 detection and finding tests fail or error (`logs/m65/m64_tests_on_m65_code.log`), all because they approve without naming the token.

**The assertions that were changed.** Five tests asserted the old behaviour or one of its consequences; each was changed on purpose, and every other assertion is kept:

| Test (file) | Before (M6.4) | After (M6.5) |
|---|---|---|
| `test_the_lower_level_transition_still_works_for_a_caller_that_names_nothing` (`test_det_proposal_identity.py`), renamed `test_the_lower_level_transition_refuses_a_caller_that_names_nothing_and_accepts_the_whole_token` | Asserted that an approval naming nothing was accepted (this was the defect, written down as a test) | Asserts it is refused with `APPROVAL_TOKEN_REQUIRED` and that the whole token is accepted |
| `test_the_lower_level_transition_refuses_a_proposal_that_has_no_usable_reference_even_when_nothing_is_named` (same file), renamed `..._whatever_reference_is_named` | Named nothing and expected `PROPOSAL_CHANGED` | Names a placeholder reference (a damaged proposal gives none) and expects `PROPOSAL_CHANGED` |
| `test_naming_nothing_through_the_lower_level_transition_still_works_for_a_fresh_proposal` (`test_det_version_types.py`), renamed `test_the_lower_level_transition_approves_a_fresh_proposal_when_the_whole_token_is_named` | Named nothing and expected acceptance | Names the whole token and expects acceptance |
| `test_a_malformed_stored_finding_version_blocks_approval_and_cannot_even_make_a_token` (same file) | Named nothing and expected `STALE_PROPOSAL` | Naming nothing expects `APPROVAL_TOKEN_REQUIRED`; naming a version and digest expects `STALE_PROPOSAL` |
| `test_a_malformed_stored_digest_blocks_approval` (same file) | Named nothing and expected `STALE_PROPOSAL` | Naming nothing, or the damaged value, expects `APPROVAL_TOKEN_REQUIRED`; naming a well-formed digest expects `STALE_APPROVAL` |

The helper `refused_by_transition` in `test_det_version_types.py` also names a placeholder proposal reference by default (a damaged record gives none), which is a fixture change. Five probes are run by the wrapper: the three earlier ones were changed to name the whole token (and so still run on the earlier packages), the M6.4 probe is unchanged, and the new one reproduces F-57.

The whole unit suite, the probes, the M5 and M6 wrappers and the regressions are run by `tools/run_m65_all.py`. The M5 mutation runs for the four M5 modules are repeated (the source hash changed because `findings.py`, the test list and the tests changed).

## 6. Results, and how each is classified

Three classes are kept apart. **Builder-run**: run by the builder in the builder's sandbox; this is the status of every result of this release. **Reproduced by the builder**: the F-57 defect on the delivered M6.4 tree (`logs/m65/probe_on_delivered_m64.log`); the audit found it first, as reported to the builder. **Independently reviewed**: nothing in this release. The independent audit of M6.4 found the defect; it has not reviewed this correction. Nothing from the audits of earlier packages is carried over to M6.5.

The test, mutation, sabotage and clean-extraction results are in the documents file delivered with the archive and in `logs/m65/`; they are not copied into this record because they are produced after it is written.

## 7. Carried forward

All of these remain open and are untouched by this release; they are listed with their sources in `programme/CARRIED_FORWARD_REGISTER.csv` (CF-01 to CF-25, no row added or changed): all M6 data is synthetic and the ports were tested only against in-memory references; no Anchor Engine, production database, event bus, AUIF or Governor repository is integrated; the event and provenance gaps; tenant and project isolation (F-39, EDR-29; not fixed here); the approval request boundary (CF-25): a replay-safe request, project-level authorisation and boundary audit are not built and CF-22 stays open; invoice-only cost coverage and the missing cost components; quantity reconciliation inputs, payment-term economics and capacity controls; M6 portfolio purchasing is a backward-looking view; the verification limits of the earlier audits (CF-23, CF-24).

## 8. What this does not show

It does not show that the correction is independently verified: nothing here has been reviewed by anyone but the builder, and the new archive is for the auditor to verify. It does not show that no other path records an approval: the tests and a search of the code found `transition` to be the only function that writes the `action_approved` status or the approval fields, apart from the service that ends an approval, but a different store or a different caller outside this package is not covered. It does not show that an approval screen or API exists or is safe: none exists, and a request that is safe to repeat, authorisation by project and a boundary audit are not built (CF-25). It does not show anything about the Engine. It does not make the prototype production-ready or integrated, and it does not start Engine #17, the versioned-baseline foundations, the approval request boundary or M7.
