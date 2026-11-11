# Change record APG-M9.2: correction of the approval request boundary after the independent audit of APG-M9.1 (F-58 to F-61)

| Field | Value |
|---|---|
| Release | APG-M9.2, a separately versioned, additive correction release: the delivered M9.1 package plus the corrections below. The delivered M9.1 ZIP and documents are not modified or replaced. |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** The audit reproduced the defects on M9.1; it has not reviewed these corrections. F-52 to F-61, CF-22 and CF-25 stay open until independently verified. |
| Authority | The auditor's verdict on M9.1 relayed by the product owner: M9.1 not accepted yet; produce a new additive correction package; write tests that reproduce each defect before the fix and show they pass on the corrected package; report each result as independently reproduced, builder-reported, failed or incomplete; split long commands; document and address the audit-consistency risk; keep F-52 to F-57, CF-22 and CF-25 open; do not start Engine #17 or M7; RFC-01 stays PROPOSED. |
| Untouched | Delivered M5 ZIP `4c15ad568c5c5ff12977529ba3253c9042781e4aa272af3b87a10eab5a010be6`; M6 `abcfefd9f28464de46dc205c1112b2ea33f537ef4a788562484c1d24109a1efb`; M6.1 `f0fac9a8d3b5920b985f6de939580dd300f58a1cec268f11463a9ccd7823e277`; M6.2 `774f835291b61a9bd7aa690389d444ddf3634c316c8298a1dc121db497421f8e`; M6.3 `4379699e0cdc32c7cb0088006fc2c2ae6dd41c1f2a4e1048fdd9e01ae7a42acc`; M6.4 `ae481618dce8a2426d84c0353659cd9992a214ee29ee122329fd5ffc766c8e57`; M6.5 `ab41a43f7ffa797dbdacacce1be04aebef0ec0ac7fba3fd2de5de26f9a6ac5fe`; M9.1 ZIP `12326469a951238f674013918f279b89a75f3ea471fa6c5cbcefd1df0496cb9f` and documents `d6431737b0160ac2be1e50ec8a92bbd55c147720107b2045118e51704265f453`; locked Sections 00-18 (`487becabdf47796800937d13a706a19b63b7b8230ecc5354b2f01a647ae5d960`); CR-09; the RTM; RFC-01 (still PROPOSED and unnumbered); the Engine #17 governance register (G-01 to G-12); every application file except `apg/api/approval_boundary.py` (`apg/det`, `apg/mkt` and the other four files of `apg/api` are byte-identical); and every existing test. |

## 1. What this release is

A correction release for one module. The audit of M9.1 reproduced three defects in `apg/api/approval_boundary.py` and raised one risk; the builder reviewed the same class of weakness and found a fourth defect. All four are corrected here, the risk is addressed in the way the in-memory test world can show and documented where only the Engine can finish it, and the tests that reproduce each defect were run against the unmodified M9.1 package. Nothing else changed: no screen, API, session store, role directory or permission model exists, nothing executes an action, and Engine #17, the versioned-baseline foundations and M7 are not started.

## 2. The defects, and where each came from

| ID | Source | What was wrong in M9.1 | What changed | Test class (tests that fail on M9.1) |
|---|---|---|---|---|
| F-58 | Audit; reproduced by the auditor | `present` computed `can_approve` from the approver role, the proposer check and the project permission, but returned the approval token whenever the finding itself could be approved. A caller with project `view` and no `approve` permission got `can_approve: false` and a non-null token. I-88 records the corrected reading of the contract. | The token is returned only when `can_approve` is true. | `TestTheTokenIsOnlyForACallerWhoCanApprove` (6) |
| F-59 | Audit; reproduced by the auditor | When opening the request record raised a conflict (two copies of one request), the call answered `CONCURRENT_CHANGE` with `retry: true` and wrote no audit event, against the rule that every outcome is audited. | The outcome is written as an `approval_request.refused` event with the code `CONCURRENT_CHANGE` (best-effort like every refusal, I-90). | `TestAConflictOnOpeningTheRequestIsAudited` (3) |
| F-60 | Audit; reproduced by the auditor | The identifier pattern ended in `$` and was applied with `match`, so an id ending in a newline passed (Python's `$` also matches before a final newline). The builder's test showed a worse effect than reported: the approval was recorded and then the audit write raised. The session expiry time had the same shape (`\d` also matches non-ASCII digits). | `fullmatch` with ASCII-only patterns for identifiers and for the expiry time (I-91). | `TestIdentifiersAndTimesAreWholeStrings` (4) |
| F-61 | Builder, same class as F-59 (every outcome audited) | `check_for_execution` returned `NOT_ALLOWED` for a malformed call or an ended session without an audit event. | The refusal is audited best-effort (I-92). | `TestEveryCallOfTheExecutorCheckIsAudited` (1) |
| (risk) CF-29 | Audit; documented by the M9.1 delivery | If the approval was recorded and the following success audit write failed, the approval existed without its `approval_request.accepted` event, and the answer was already noted so a retry never wrote it. | The entry is written first and without protection; if it fails the call raises, the answer is not noted, the request stays pending, and the retry recognises the approval from the finding's history and writes the entry (I-89). The audit is therefore at least once: a crash between the entry and the note can leave two entries. Exactly once needs a transaction across the state change and its audit record, which is the Engine's (EDR-32, CF-29). | `TestAnApprovalIsAuditedAfterAFailedFirstAuditWrite` (2) |

Also corrected: the contract document named the module `apg/det/approval_boundary.py`; the file is `apg/api/approval_boundary.py`.

The sweep for the same class of weakness covered every pattern match and every return path in the module: the identifier and expiry patterns (F-60), every path out of `request_approval` and `check_for_execution` (F-59, F-61). It is a builder's sweep, not an independent one; the auditor should repeat it.

## 3. Files changed and added

Compared byte for byte with the delivered M9.1 ZIP. All other files (the count is in `regression/BASELINE_M91.json`) are identical.

**Changed (20)**

| File | Kind | What changed and why |
|---|---|---|
| `README.md` | records and documents | adds the M9.2 section above the unchanged M9.1 text |
| `RUN_COMMANDS.txt` | records and documents | adds the M9.2 commands (the defects on M9.1, the split groups, the regression steps, the mutation chunks of ten) above the unchanged M9.1 text |
| `apg/api/approval_boundary.py` | application code | the corrections F-58 to F-61 and the audit-first order (section 2) |
| `programme/APPROVAL_REQUEST_BOUNDARY.md` | records and documents | the contract document revised: the token rule, the audit order (audit first, at least once), the whole-string ASCII identifier rule, the audited conflict and executor-check refusals, and the module path corrected (it said apg/det/approval_boundary.py; the file is apg/api/approval_boundary.py) |
| `programme/CARRIED_FORWARD_REGISTER.csv` | records and documents | rows CF-28 and CF-29 appended; CF-22 and CF-25 are not edited and stay open |
| `programme/ENGINE_HANDOFF_REGISTER.csv` | records and documents | row EDR-32 appended (atomic persistence of a state change and its audit record); no earlier row changed |
| `programme/FINDINGS_REGISTER.csv` | records and documents | rows F-58 to F-61 appended (status: corrected in APG-M9.2, builder-implemented, open until independently verified); no earlier row changed; F-52 to F-57 stay open |
| `programme/INTERPRETATIONS_REGISTER.csv` | records and documents | rows I-88 to I-92 appended; no earlier row changed |
| `programme/PROGRAMME_MILESTONES.csv` | records and documents | the M9 row only: EDR-32 added to its handoff entries; M7 and every other row unchanged |
| `programme/STATUS_REGISTER.csv` | records and documents | rows SR-81 to SR-83 appended; no earlier row changed |
| `tools/m91_mutants.py` | tools | runs the correction tests as well; the id of the one documented equivalent mutant moved from AB-BOL-002 to AB-BOL-003 because a new `and` was added earlier in the module (same site; the proof is unchanged) |
| `tools/make_m0.py` | tools | runs the M9.2 register step after the M9.1 one, so the derived-files check regenerates the programme tables with the M9.2 rows; nothing else |
| `tools/programme_check_m91.py` | tools | N03 and N05 allow the rows appended after CF-27 and F-57; nothing else |
| `tools/run_regression_m6.py` | tools | L03 and L04 accept the M9.2 additions (EDR-32, the M9 row edit) when the M9.2 baseline pins the tables; accepts the files, rows and tables the M9.2 baseline declares and pins by hash; every other check is unchanged |
| `tools/run_regression_m61.py` | tools | accepts the files, rows and tables the M9.2 baseline declares and pins by hash; every other check is unchanged (R02, R03, R04, R09, R10, R11) |
| `tools/run_regression_m62.py` | tools | accepts the files, rows and tables the M9.2 baseline declares and pins by hash; every other check is unchanged (R02, R03, R04, R09, R10, R11) |
| `tools/run_regression_m63.py` | tools | accepts the files, rows and tables the M9.2 baseline declares and pins by hash; every other check is unchanged (R02, R03, R04, R09, R10, R11) |
| `tools/run_regression_m64.py` | tools | accepts the files, rows and tables the M9.2 baseline declares and pins by hash; every other check is unchanged (R02, R03, R04, R09, R10, R11) |
| `tools/run_regression_m65.py` | tools | accepts the files, rows and tables the M9.2 baseline declares and pins by hash; every other check is unchanged (R02, R03, R04, R09, R10, R11) |
| `tools/run_regression_m91.py` | tools | accepts the files, rows and tables the M9.2 baseline declares and pins by hash; every other check is unchanged (R02, R03, R04, R09, R09b, R09c, R10, R11) |

**Added (15)**

| File | Kind | What it is |
|---|---|---|
| `programme/CHANGE_RECORD_APG-M9.2.md` | records and documents | new: this record |
| `regression/m91_snapshot/CARRIED_FORWARD_REGISTER.csv` | regression data | stored copy of a delivered M9.1 programme table, used as the comparison for the append-only check |
| `regression/m91_snapshot/E17_GOVERNANCE_REGISTER.csv` | regression data | stored copy of a delivered M9.1 programme table, used as the comparison for the append-only check |
| `regression/m91_snapshot/ENGINE_HANDOFF_REGISTER.csv` | regression data | stored copy of a delivered M9.1 programme table, used as the comparison for the append-only check |
| `regression/m91_snapshot/FINDINGS_REGISTER.csv` | regression data | stored copy of a delivered M9.1 programme table, used as the comparison for the append-only check |
| `regression/m91_snapshot/INTERPRETATIONS_REGISTER.csv` | regression data | stored copy of a delivered M9.1 programme table, used as the comparison for the append-only check |
| `regression/m91_snapshot/PROGRAMME_MILESTONES.csv` | regression data | stored copy of a delivered M9.1 programme table, used as the comparison for the append-only check |
| `regression/m91_snapshot/RFC_REGISTER.csv` | regression data | stored copy of a delivered M9.1 programme table, used as the comparison for the append-only check |
| `regression/m91_snapshot/STATUS_REGISTER.csv` | regression data | stored copy of a delivered M9.1 programme table, used as the comparison for the append-only check |
| `tests/test_api_m92_corrections.py` | tests | new: 24 tests, one class for each of the four defects, one for the audit consistency; 16 of them fail or error on the delivered M9.1 code |
| `tools/make_m92_registers.py` | tools | new: adds the M9.2 rows and edits the M9 row |
| `tools/probe_m91_audit_findings.py` | tools | new: the five audit items in a few lines each; DEFECT PRESENT on M9.1, corrected on M9.2 |
| `tools/programme_check_m92.py` | tools | new: structure checks of the M9.2 records |
| `tools/run_m92_all.py` | tools | new: wrapper in 27 numbered groups; `--list` and `--group N` split it |
| `tools/run_regression_m92.py` | tools | new: shows that nothing but the declared files changed; `--step Rnn` splits the long steps |

Run output of the release is under `logs/m92/` and is not compared. `regression/BASELINE_M91.json` records the hash of every file above and is itself not compared. The earlier logs under `logs/m91/` and before are carried unchanged: they describe the M9.1 code and are not evidence about this release.

## 4. What the corrected boundary does

The full contract is `programme/APPROVAL_REQUEST_BOUNDARY.md`. Only what changed relative to M9.1:

| Situation | M9.1 | M9.2 |
|---|---|---|
| `present` for a caller who cannot approve now (no approver role, no project approval, the proposer, or a finding that cannot be approved) | `can_approve: false` and, for an approvable finding, a token | `can_approve: false` and no token |
| Two copies of one request meet while the record is opened | `CONCURRENT_CHANGE`, no audit event | `CONCURRENT_CHANGE`, one `approval_request.refused` event with that code; the request stays open |
| A request or finding id, or a session expiry, ending in a newline or containing non-ASCII digits | passed the shape check | `REQUEST_MALFORMED` (an expiry that does not match is an ended session) |
| `check_for_execution` with a malformed call or an ended session | `NOT_ALLOWED`, nothing audited | `NOT_ALLOWED`, one `approval_request.execution_check` event, best-effort |
| The approval is recorded and the first audit write fails | the answer was noted anyway; the entry was never written | the call raises, the request stays pending, the retry finds the approval in the finding's history and writes the entry |
| The approval is recorded, the entry is written, and the process stops before the answer is noted | one entry | the retry writes a second entry (at least once, documented, CF-29) |

## 5. Tests, written before the fix

24 new tests in `tests/test_api_m92_corrections.py`, in five classes (one per defect and one for the audit consistency). They were run against the delivered, unmodified M9.1 package (extracted from its ZIP, hash-checked): 16 of the 24 fail or error there (`logs/m92/new_tests_on_delivered_m91.log`), and every class has at least one failing test; the same 24 pass on this release. The remaining 8 tests pass on both: they pin behaviour that was already right and must stay right. The build repeats the run on M9.1 each time, so the claim does not rest on the order in which the builder worked. `tools/probe_m91_audit_findings.py` shows the same five items in a few lines each (`logs/m92/probe_on_delivered_m91.log`). The existing 78 API tests were not changed and pass.

The mutation run over the module was repeated (`logs/m92/mutation_run_m92.log`) and the package-level sabotage list was extended with the corrections (`logs/m92/sabotage_m92.log`).

## 6. Results, and how each is classified

Four classes are kept apart, as the audit asked.

* **Independently reproduced** (by the auditor, on M9.1, as relayed): the three defects F-58, F-59 and F-60; the delivered hashes and ZIP integrity; the 78 API tests; the 14-case project-permission contract; the static and register checks; the boundary probe and the earlier approval probes; the procurement golden cases and saved demonstrations. Nothing in this release has been independently reproduced.
* **Builder-reported**: every result of this release, including the reproduction of the defects on the delivered M9.1 code, the correction tests, the full unit run, the mutation run, the sabotage run and the clean-extraction run (documents file, section 3; `logs/m92/`).
* **Failed**: the three audit defects were failures of M9.1. Nothing in this release is reported failed by any reviewer; no one but the builder has run it.
* **Incomplete**: the auditor's full regression and complete mutation suite on M9.1 timed out and stay recorded as incomplete (CF-28), not as passes. This release splits every long run (`--group`, `--step`, chunks of ten mutants) and records the builder's own times; it does not turn the auditor's incomplete runs into passes.

## 7. Carried forward

All of these remain open (`programme/CARRIED_FORWARD_REGISTER.csv`, CF-01 to CF-29): CF-22 and CF-25 are unedited and open; CF-26 and CF-27 stand; CF-28 records the auditor's incomplete runs of M9.1 for the auditor to complete; CF-29 records that the approval and its audit entry are not written atomically (EDR-32, the Engine's). All M6 data is synthetic and the ports were tested only against in-memory references; no Anchor Engine, production database, event bus, AUIF or Governor repository is integrated; tenant and project isolation (F-39, EDR-29) is not fixed here; the screen, API, transport, session store, role directory and project permission model are the Engine's (EDR-11, EDR-20, EDR-29, EDR-31). Invoice-only cost coverage, quantity reconciliation inputs, payment-term economics and capacity controls, and the backward-looking M6 purchasing view are unchanged.

## 8. What this does not show

It does not show that the corrections are independently verified: no one but the builder has reviewed them. It does not show that the boundary is complete: the same-class sweep is the builder's, and the auditor found the first three defects by reading and probing, which the builder's own tests and mutation run had not. It does not show exactly-once auditing or a transaction across state and audit: that is the Engine's (EDR-32) and was never built. It does not show that an approval screen, an API or a permission model exists or is safe: none exists, and the reference port is a test double. It does not show that any real Engine port meets the contract: no Engine code was seen. It does not make the prototype production-ready or integrated, and it does not start Engine #17, the versioned-baseline foundations or M7.
