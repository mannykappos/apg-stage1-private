# Change record APG-M9.1: the approval request boundary (first slice of M9; carried-forward item CF-25)

| Field | Value |
|---|---|
| Release | APG-M9.1, a separately versioned release: the delivered M6.5 package plus the new package `apg/api` |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** CF-22 and CF-25 stay open. F-52, F-53, F-54, F-55, F-56 and F-57 stay open until independently verified. |
| Authority | The instruction relayed by the product owner after the auditor's verdict on M6.5: move on to CF-25 / APG-M9.1 with the approval-request boundary, execution-time validation, a project-scope authorisation interface, contract tests and documented integration requirements; keep F-52 to F-57 and CF-22 open; do not label APG production-ready; do not start Engine #17 or M7; RFC-01 stays proposed and unnumbered; build the boundary carefully, with the same independent checks before that milestone is accepted; keep Amir out of the loop. |
| Untouched | Delivered M5 ZIP `4c15ad568c5c5ff12977529ba3253c9042781e4aa272af3b87a10eab5a010be6`; delivered M6 ZIP `abcfefd9f28464de46dc205c1112b2ea33f537ef4a788562484c1d24109a1efb`; delivered M6.1 ZIP `f0fac9a8d3b5920b985f6de939580dd300f58a1cec268f11463a9ccd7823e277`; delivered M6.2 ZIP `774f835291b61a9bd7aa690389d444ddf3634c316c8298a1dc121db497421f8e`; delivered M6.3 ZIP `4379699e0cdc32c7cb0088006fc2c2ae6dd41c1f2a4e1048fdd9e01ae7a42acc`; delivered M6.4 ZIP `ae481618dce8a2426d84c0353659cd9992a214ee29ee122329fd5ffc766c8e57`; delivered M6.5 ZIP `ab41a43f7ffa797dbdacacce1be04aebef0ec0ac7fba3fd2de5de26f9a6ac5fe`; locked Sections 00-18 (`487becabdf47796800937d13a706a19b63b7b8230ecc5354b2f01a647ae5d960`); CR-09; the RTM; RFC-01 (still PROPOSED and unnumbered); the findings register (no finding added or changed); the Engine #17 governance register (G-01 to G-12, unchanged); the application code of M6.5 and earlier (`apg/det`, `apg/mkt` and the rest are byte-identical) and every existing test. |

## 1. What this slice is

The M6.1 to M6.5 corrections made the lifecycle call `approve_action` (and, since M6.5, `transition` itself) refuse an approval that does not name the finding version, the evidence digest and the proposal reference the approver was shown. What a screen or an API needs around that call did not exist: a request that is checked for shape; a person with a live session and the approver role; authorisation for the finding's project; one answer for one request id however often it is sent; recovery of a request that stopped half way; and an audit event for every outcome. This slice builds that as logic, in a new additive package, with a port for the one thing only the Engine can decide (who may do what in which project, EDR-31). It is the first slice of M9; the milestones table has no row for slices, so the M9 row records it ("In this delivery") and gains EDR-31.

## 2. A defect found in the builder's own draft

No delivered release is affected. The following were found by the builder's own tests and reviews while the boundary was being written, before anything was delivered, and corrected in the draft; they are listed because the tests that found them are kept:

* `present` treated `bool(FD.approvable(f))` as true for any finding. `approvable` returns a pair (answer, reason), which is always true as a pair, so the screen would have handed out an approval token for a finding that could not be approved. Found by `test_the_screen_gives_no_token_for_a_finding_that_cannot_be_approved`; corrected to test the first element, and a mutation of that line is killed by the same test.
* A request that stopped half way could be credited with an approval made by a different request: the search of the finding's history started at the beginning. The request record now stores the length of the history when it was opened (`history_len`) and only later entries count. Tests added for two requests by the same person on the same finding.
* `check_for_execution` raised for a revoked session because its refusal was logged without protection; refusals are now logged by `_log_refusal`, which does not raise (a success is still logged without that protection, so an approval that cannot be audited is not given).
* When two copies of one request met, the loser assumed that both had written the same answer. It now returns the answer actually noted first under the request id, marked as a replay, and falls through if there is none.
* The first mutation run left survivors; further tests were written for them (class `TestEdgesTheFirstMutationRunFound`, and the case for AB-BOL-026) until every mutant was killed or documented as equivalent (section 6).
* The first draft of the contract helper `exact()` allowed a port to raise, so two of the faulty ports escaped; it now fails a port that raises.
* The first location of the module was `apg/det`, where the M5 static rules (no `re` import, no clock reads, Blueprint docstrings) rejected it; the code moved into a new package `apg/api` with its own static rules (`tests/test_api_static.py`) instead of relaxing the M5 ones.

## 3. Files changed and added

Compared byte for byte with the delivered M6.5 ZIP. All other files (the count is in `regression/BASELINE_M65.json`) are identical.

**Changed (18)**

| File | Kind | What changed and why |
|---|---|---|
| `README.md` | records and documents | adds the M9.1 section above the unchanged M6.5 text |
| `RUN_COMMANDS.txt` | records and documents | adds the M9.1 commands above the unchanged M6.5 text |
| `programme/CARRIED_FORWARD_REGISTER.csv` | records and documents | rows CF-26 and CF-27 appended; CF-22 and CF-25 are not edited and stay open |
| `programme/ENGINE_HANDOFF_REGISTER.csv` | records and documents | row EDR-31 appended (the per-action project permission port); no earlier row changed |
| `programme/INTERPRETATIONS_REGISTER.csv` | records and documents | rows I-81 to I-87 appended; no earlier row changed |
| `programme/PROGRAMME_MILESTONES.csv` | records and documents | the M9 row only: status "In this delivery" and EDR-31 added to its handoff entries (the table has no row for slices); M7 and every other row unchanged |
| `programme/STATUS_REGISTER.csv` | records and documents | rows SR-76 to SR-80 appended; no earlier row changed |
| `tools/make_m0.py` | tools | runs the M9.1 register step after the M6.5 one, so the derived-files check regenerates the programme tables with the M9.1 rows; nothing else |
| `tools/programme_check_m4.py` | tools | time-bound historical checks relaxed so that the appended M9.1 rows and the M9 row edit are tolerated (the check of that table's earlier content is kept) |
| `tools/programme_check_m5.py` | tools | time-bound historical checks relaxed so that the appended M9.1 rows and the M9 row edit are tolerated |
| `tools/programme_check_m6.py` | tools | time-bound historical checks relaxed so that the appended M9.1 rows and the M9 row edit are tolerated |
| `tools/programme_check_m65.py` | tools | check N05 allows rows appended after CF-25 (CF-26, CF-27) and N06/N07 accept their status texts; nothing else |
| `tools/run_regression_m6.py` | tools | L03 and L04 accept the M9 row edit and the appended EDR-31 when the M9.1 baseline pins the table's hash; accepts the files, rows and tables the M9.1 baseline declares and pins by hash; every other check is unchanged |
| `tools/run_regression_m61.py` | tools | accepts the files, rows and tables the M9.1 baseline declares and pins by hash; every other check is unchanged (R02, R03, R04, R09, R10, R11) |
| `tools/run_regression_m62.py` | tools | accepts the files, rows and tables the M9.1 baseline declares and pins by hash; every other check is unchanged (R02, R03, R04, R09, R10, R11) |
| `tools/run_regression_m63.py` | tools | accepts the files, rows and tables the M9.1 baseline declares and pins by hash; every other check is unchanged (R02, R03, R04, R09, R10, R11) |
| `tools/run_regression_m64.py` | tools | accepts the files, rows and tables the M9.1 baseline declares and pins by hash; every other check is unchanged (R02, R03, R04, R09, R10, R11); R10-CARR allows rows appended after CF-25 |
| `tools/run_regression_m65.py` | tools | accepts the files, rows and tables the M9.1 baseline declares and pins by hash; every other check is unchanged (R02, R03, R04, R09, R10, R11) |

**Added (25)**

| File | Kind | What it is |
|---|---|---|
| `apg/api/__init__.py` | application code | new: the package docstring (Section 15) |
| `apg/api/approval_boundary.py` | application code | new: the boundary: `present`, `request_approval`, `check_for_execution`, the `ProjectActionPort` base class |
| `apg/api/contracts_m9.py` | application code | new: the 14-case ProjectActionPort contract suite (EDR-31) |
| `apg/api/faulty_m9.py` | application code | new: 16 deliberately faulty ports; each contract case is failed by at least one |
| `apg/api/reference_m9.py` | application code | new: an in-memory reference port and its contract environment (a test double, not a permission model) |
| `programme/APPROVAL_REQUEST_BOUNDARY.md` | records and documents | new: the contract document for the Engine's author (calls, request, order of checks, replay and audit rules, result codes, suggested mapping, what the Engine must provide) |
| `programme/CHANGE_RECORD_APG-M9.1.md` | records and documents | new: this record |
| `regression/m65_snapshot/CARRIED_FORWARD_REGISTER.csv` | regression data | stored copy of a delivered M6.5 programme table, used as the comparison for the append-only check |
| `regression/m65_snapshot/E17_GOVERNANCE_REGISTER.csv` | regression data | stored copy of a delivered M6.5 programme table, used as the comparison for the append-only check |
| `regression/m65_snapshot/ENGINE_HANDOFF_REGISTER.csv` | regression data | stored copy of a delivered M6.5 programme table, used as the comparison for the append-only check |
| `regression/m65_snapshot/FINDINGS_REGISTER.csv` | regression data | stored copy of a delivered M6.5 programme table, used as the comparison for the append-only check |
| `regression/m65_snapshot/INTERPRETATIONS_REGISTER.csv` | regression data | stored copy of a delivered M6.5 programme table, used as the comparison for the append-only check |
| `regression/m65_snapshot/PROGRAMME_MILESTONES.csv` | regression data | stored copy of a delivered M6.5 programme table, used as the comparison for the append-only check |
| `regression/m65_snapshot/RFC_REGISTER.csv` | regression data | stored copy of a delivered M6.5 programme table, used as the comparison for the append-only check |
| `regression/m65_snapshot/STATUS_REGISTER.csv` | regression data | stored copy of a delivered M6.5 programme table, used as the comparison for the append-only check |
| `tests/test_api_action_port_contract.py` | tests | new: 4 tests: the contract suite against the reference and against each faulty port, and an end-to-end test of the boundary with the reference |
| `tests/test_api_approval_boundary.py` | tests | new: 67 tests of the boundary |
| `tests/test_api_static.py` | tests | new: 7 static rules for apg/api (imports, no floats or file access, clock use, docstrings cite the Blueprint, only the request record is written, no overclaiming words) |
| `tools/m91_mutants.py` | tools | new: mutation run over the boundary (comparison, boolean, not, raise and arithmetic mutants; every site is a mutant) |
| `tools/make_m91_registers.py` | tools | new: adds the M9.1 rows and edits the M9 row |
| `tools/probe_approval_boundary.py` | tools | new: six situations through the three calls, in a few lines |
| `tools/programme_check_m91.py` | tools | new: structure checks of the M9.1 records |
| `tools/run_m91_all.py` | tools | new: wrapper that runs every M9.1 check except the mutation run |
| `tools/run_m91_contracts.py` | tools | new: runs the ProjectActionPort contract on the reference |
| `tools/run_regression_m91.py` | tools | new: shows that nothing but the declared files changed |

Run output of the release is under `logs/m91/` and is not compared. `regression/BASELINE_M65.json` records the hash of every file above and is itself not compared. The earlier logs under `logs/m65/` and before are carried unchanged.

## 4. What the boundary does

The full contract is `programme/APPROVAL_REQUEST_BOUNDARY.md`. In short:

| Situation | Result |
|---|---|
| A request that is not exactly the six fields (request id, finding id, version, digest, proposal, rationale), or with a malformed value, or a rationale of more than 2000 characters (I-81) | `REQUEST_MALFORMED`; audited; nothing stored |
| A service identity, an ended session, or a person without the approver role | `HUMAN_REQUIRED`, `SESSION_EXPIRED`, `ROLE_REQUIRED`; audited |
| A finding that does not exist, belongs to another tenant, or sits in a project the person may not approve in (asked of the port on every request and every replay) | `NOT_FOUND`, the same answer for all three (I-83) |
| A first request | A request record is opened, `approve_action` is called, the answer is noted under the request id and audited |
| The same request again | The first answer, marked `replayed: true`, nothing done a second time (I-84); the port is asked again |
| The same request id used for different content or by another person | `REQUEST_ID_REUSED` |
| Evidence changed, proposal replaced, wrong version, digest or proposal, self-approval | The lifecycle's own refusals (`STALE_APPROVAL`, `STALE_PROPOSAL`, `PROPOSAL_CHANGED`, `SELF_APPROVAL` and the rest), passed on and audited |
| A request that stopped between the approval and the note of it | Recognised on the next try from the finding's history, credited only if this person approved exactly this version, digest and proposal after the request was opened (I-87); never approved twice |
| `present` | The proposal, who wrote it and when, whether the caller can approve, and a token only for a finding that can be approved now |
| `check_for_execution` | True only for the exact approved version, digest and proposal while the approval is in force; false after the evidence changed, the proposal was replaced or the approval ended (I-86) |
| A failure to write the audit entry for a refusal | Not raised; the refusal stands. A failure to write the entry for a success is raised: an approval that cannot be audited is not given |

## 5. Tests

78 new tests. `tests/test_api_approval_boundary.py` (67) covers the path from the screen to the approval, malformed requests, who may ask (person, session, role, tenant, project, service), one answer per request id (including two copies meeting, and a request id reused), a request that stopped half way, evidence changing between proposal, approval and execution, an audit event for every outcome with no rationale text in any event, recovery and replay, and that nothing else moved (the lifecycle table is as in M6.5; the boundary adds no status and no finding field). `tests/test_api_action_port_contract.py` (4) runs the 14-case contract against the in-memory reference and shows that each of 16 faulty ports fails the case it is meant to fail. `tests/test_api_static.py` (7) holds the static rules. No test was written for behaviour the boundary does not have. Nothing was written before the code in a way the builder could show; the tests and the code were written together and hardened by the mutation run, and this record does not claim otherwise.

The whole unit suite, the probes, the M5 and M6 wrappers and the regressions are run by `tools/run_m91_all.py`. The M5 and M6 mutation runs are not repeated: no M5 or M6 module, test or mutation tool changed (the source-hash check of the M5 logs is in the verification record of the documents file).

## 6. Results, and how each is classified

Three classes are kept apart. **Builder-run**: run by the builder in the builder's sandbox; this is the status of every result of this release. **Reviewed by anyone other than the builder**: nothing in this release, and the auditor's verdict on M6.5 does not extend to it. **Reported by an audit**: nothing; no defect in this release was reported by an audit. The test, mutation, sabotage and clean-extraction results are in the documents file delivered with the archive and in `logs/m91/`; they are not copied into this record because they are produced after it is written.

## 7. Carried forward

All of these remain open and are untouched by this release except where CF-26 and CF-27 are appended (`programme/CARRIED_FORWARD_REGISTER.csv`, CF-01 to CF-27): all M6 data is synthetic and the ports were tested only against in-memory references; no Anchor Engine, production database, event bus, AUIF or Governor repository is integrated; tenant and project isolation (F-39, EDR-29) is not fixed here; the approval request boundary exists as logic (CF-26), but no approval screen or API exists, the session store, the role directory and the project permission model are the Engine's (EDR-11, EDR-20, EDR-29, EDR-31), the record kind `approval_request` must be writable only through the boundary (EDR-20), and CF-22 and CF-25 stay open; the verification limits of the M6.5 audit are recorded in CF-27 for the auditor; invoice-only cost coverage and the missing cost components; quantity reconciliation inputs, payment-term economics and capacity controls; M6 portfolio purchasing is a backward-looking view.

## 8. What this does not show

It does not show that the boundary is independently verified: nothing here has been reviewed by anyone but the builder. It does not show that an approval screen, an API or a permission model exists or is safe: none exists, and the reference port is a test double. It does not show that any real Engine port meets the contract: no Engine code was seen. It does not show that an action is carried out correctly: nothing in APG executes one, and `check_for_execution` is called by no code in this package. It does not show that the audit trail is complete outside this package, that request ids cannot be guessed, or that rate limiting or transport security hold: those are the Engine's. It does not make the prototype production-ready or integrated, and it does not start Engine #17, the versioned-baseline foundations or M7.
