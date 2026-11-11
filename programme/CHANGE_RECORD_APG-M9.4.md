# Change record APG-M9.4: correction of the clock and session failure handling in the approval request boundary after the independent audit of APG-M9.3 (F-63)

| Field | Value |
|---|---|
| Release | APG-M9.4, a separately versioned, additive correction release: the delivered M9.3 package plus the correction below. The delivered M9.3, M9.2 and M9.1 ZIPs and documents are not modified or replaced. |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** The audit reproduced the failure on M9.3; it has not reviewed this correction. F-52 to F-63, CF-22, CF-25 and CF-29 stay open until independently verified. |
| Authority | The auditor's verdict on M9.3 relayed by the product owner (Fri 2026-10-16): M9.3 not accepted; the expiry correction of F-62 is supported by targeted tests but F-62 is not to be marked closed until F-63 is resolved and regression-tested; build a new additive release M9.4 from the exact verified M9.3 baseline; a clock exception must not escape the three entry points, an unavailable or invalid clock reading fails closed and is never a live session, no approval or execution is granted when the clock cannot be trusted, the existing refusal representation is used, a deterministic audit outcome is recorded through the existing contract without claiming an audit that failed to write, tenant, session, approval, action-state and execution invariants are preserved, no unrelated refactoring, regression tests for all three entry points and for accessor failures. |
| Untouched | Delivered M5 ZIP `4c15ad568c5c5ff12977529ba3253c9042781e4aa272af3b87a10eab5a010be6`; M6 `abcfefd9f28464de46dc205c1112b2ea33f537ef4a788562484c1d24109a1efb`; M6.1 `f0fac9a8d3b5920b985f6de939580dd300f58a1cec268f11463a9ccd7823e277`; M6.2 `774f835291b61a9bd7aa690389d444ddf3634c316c8298a1dc121db497421f8e`; M6.3 `4379699e0cdc32c7cb0088006fc2c2ae6dd41c1f2a4e1048fdd9e01ae7a42acc`; M6.4 `ae481618dce8a2426d84c0353659cd9992a214ee29ee122329fd5ffc766c8e57`; M6.5 `ab41a43f7ffa797dbdacacce1be04aebef0ec0ac7fba3fd2de5de26f9a6ac5fe`; M9.1 ZIP `12326469a951238f674013918f279b89a75f3ea471fa6c5cbcefd1df0496cb9f` and documents `d6431737b0160ac2be1e50ec8a92bbd55c147720107b2045118e51704265f453`; M9.2 ZIP `ad889d545a5ad91a100ff89425353b425a908fe23f50c44d0a11dd128247f1d8` and documents `ebbb77f2e99e26fb6cc54ac710763b000737dc965a45f8f3fb358163ee7f7df0`; M9.3 ZIP `4dae205ca53e6b47ca794e0515a7b679fa52b9d803ade257f169748e963d8882` and documents `541c59a523aefbae6595956fb07bb2f8d27bf42eed39658444581f359f1f1497`; locked Sections 00-18 (`487becabdf47796800937d13a706a19b63b7b8230ecc5354b2f01a647ae5d960`); CR-09; the RTM; RFC-01 (still PROPOSED and unnumbered); the Engine #17 governance register (G-01 to G-12); the milestone and Engine handoff tables (no Engine record was added) |

## 1. What this release is

A correction release for one function and the three calls that use it. The audit of M9.3 found that `_session_live()` in `apg/api/approval_boundary.py` read the clock without protection, so a clock whose `now()` raised an exception made `present`, `request_approval` and `check_for_execution` raise it to their caller, with no refusal and no audit entry. The session check is corrected, the tests that reproduce the failure were run against the unmodified M9.3 package, and nothing else changed: no screen, API, session store, role directory or project permission model was added, nothing executes an action, and no Engine code was seen. The M9.3 rule for what a live session is (F-62) is kept and its tests still pass.

## 2. The defect, and where it came from

| ID | Source | What was wrong in M9.3 | What changed | Test class (tests that fail on M9.3) |
|---|---|---|---|---|
| F-63 | Audit of M9.3; reproduced by the auditor at all three entry points | `_session_live` read `ctx.expires_at` and then `clock.now()` with nothing around them. A `now()` that raised `RuntimeError("clock unavailable")` made `present`, `request_approval` and `check_for_execution` raise it to the caller, with zero new audit events; `request_approval` left the finding at `action_proposed`. | `_check_session` reads the clock first, inside `try/except Exception`, then the expiry inside its own `try/except Exception`; anything that cannot be read, or is not a real UTC moment, or an expiry that is not strictly later, ends the session. The session check returns the one reading, which the call then uses for everything (`_Pinned`). `_is_human` treats an actor kind that cannot be read as not a person. The three calls give the refusals they already gave for an ended session and write the audit entry they already wrote; the reason text names the clock when the clock is the cause. | `TestAClockThatRaisesNeverEscapesAndNeverApproves` (4), `TestAccessorFailuresOfTheSession` (2), `TestTheClockIsReadOnceSoALaterFailureCannotHalveAnApproval` (4), `TestFailurePathsKeepTheInvariants` (7), `TestTheSessionRuleOfM93StillHolds` (1) |

How far the failure reaches: the audit says plainly that it demonstrated no approval or execution bypass; it is a failure-handling and auditability defect, and this record does not call it more. On M9.3 an exception from the clock did not grant anything: it escaped before any grant. What the defect cost was an uncontrolled exception for the caller, no audit record of the attempt, and (for `request_approval`) a request left unanswered. A second, smaller effect that the builder found while writing the tests: `request_approval` read the clock again inside the lifecycle after the session check, so a clock that failed on a later read could stop the request part way (the fourth item of the probe shows the finding left at `action_proposed` on M9.3); the one-reading rule removes that.

The sweep for the same class of weakness covered every place the module reads something from the caller's side of the line: the clock (this correction), the expiry (this correction), the actor kind (now guarded), and the identifiers (F-60, unchanged). The other attributes of the context (tenant, user, roles, session id, seal) belong to the Engine's sealed context and are read as before; if that context can raise when they are read, those calls would still raise, which is the Engine's contract to state (I-98). It is a builder's sweep, not an independent one; the auditor should repeat it.

## 3. Files changed and added

Compared byte for byte with the delivered M9.3 ZIP. All other files (the count is in `regression/BASELINE_M93.json`) are identical.

**Changed (20)**

| File | Kind | What changed and why |
|---|---|---|
| `README.md` | records and documents | adds the M9.4 section above the unchanged M9.3 text |
| `RUN_COMMANDS.txt` | records and documents | adds the M9.4 commands (clean extraction, environment, the defect on M9.3, the split groups, the regression steps, the mutation chunks of ten) above the unchanged M9.3 text |
| `apg/api/approval_boundary.py` | application code | the correction F-63: `_check_session` reads the clock once inside a guard and fails closed; `_Pinned` carries that one reading through the call; `_session_live` is a thin wrapper of it; `_is_human` is guarded; the three entry points use them and give their existing refusals (section 4) |
| `programme/APPROVAL_REQUEST_BOUNDARY.md` | records and documents | the contract document revised: a clock or an expiry that cannot be read ends the session, and the clock is read once per call |
| `programme/CARRIED_FORWARD_REGISTER.csv` | records and documents | row CF-31 appended (what the M9.3 audit could not complete or obtain: nested wrapper runs, a fresh complete mutation run, the 67-test invocation); CF-22, CF-25 and CF-29 are not edited and stay open |
| `programme/FINDINGS_REGISTER.csv` | records and documents | row F-63 appended (status: corrected in APG-M9.4, builder-implemented, open until independently verified); no earlier row changed; F-62 keeps its M9.3 status and F-52 to F-61 stay open |
| `programme/INTERPRETATIONS_REGISTER.csv` | records and documents | rows I-96 to I-98 appended; no earlier row changed |
| `programme/STATUS_REGISTER.csv` | records and documents | rows SR-87 to SR-89 appended; no earlier row changed |
| `tools/m91_mutants.py` | tools | runs the M9.4 correction tests as well; the id of the one documented equivalent mutant moved (AB-BOL-005 to AB-BOL-004) because the module's sites before it changed (same site; the proof is unchanged) |
| `tools/make_m0.py` | tools | runs the M9.4 register step after the M9.3 one, so the derived-files check regenerates the programme tables with the M9.4 rows; nothing else |
| `tools/programme_check_m93.py` | tools | allows the rows appended after CF-30, F-62 and I-95 and the longer revision line of the contract document; nothing else |
| `tools/run_regression_m6.py` | tools | L03 and L04 accept the M9.4 additions when the M9.4 baseline pins the tables; accepts the files, rows and tables the M9.4 baseline declares and pins by hash; every other check is unchanged |
| `tools/run_regression_m61.py` | tools | accepts the files, rows and tables the M9.4 baseline declares and pins by hash; every other check is unchanged |
| `tools/run_regression_m62.py` | tools | accepts the files, rows and tables the M9.4 baseline declares and pins by hash; every other check is unchanged |
| `tools/run_regression_m63.py` | tools | accepts the files, rows and tables the M9.4 baseline declares and pins by hash; every other check is unchanged |
| `tools/run_regression_m64.py` | tools | accepts the files, rows and tables the M9.4 baseline declares and pins by hash; every other check is unchanged |
| `tools/run_regression_m65.py` | tools | accepts the files, rows and tables the M9.4 baseline declares and pins by hash; every other check is unchanged |
| `tools/run_regression_m91.py` | tools | accepts the files, rows and tables the M9.4 baseline declares and pins by hash; every other check is unchanged |
| `tools/run_regression_m92.py` | tools | accepts the files, rows and tables the M9.4 baseline declares and pins by hash; every other check is unchanged |
| `tools/run_regression_m93.py` | tools | accepts the files, rows and tables the M9.4 baseline declares and pins by hash; every other check is unchanged |

**Added (15)**

| File | Kind | What it is |
|---|---|---|
| `programme/CHANGE_RECORD_APG-M9.4.md` | records and documents | new: this record |
| `regression/m93_snapshot/CARRIED_FORWARD_REGISTER.csv` | regression data | stored copy of a delivered M9.3 programme table, used as the comparison for the append-only check |
| `regression/m93_snapshot/E17_GOVERNANCE_REGISTER.csv` | regression data | stored copy of a delivered M9.3 programme table, used as the comparison for the append-only check |
| `regression/m93_snapshot/ENGINE_HANDOFF_REGISTER.csv` | regression data | stored copy of a delivered M9.3 programme table, used as the comparison for the append-only check |
| `regression/m93_snapshot/FINDINGS_REGISTER.csv` | regression data | stored copy of a delivered M9.3 programme table, used as the comparison for the append-only check |
| `regression/m93_snapshot/INTERPRETATIONS_REGISTER.csv` | regression data | stored copy of a delivered M9.3 programme table, used as the comparison for the append-only check |
| `regression/m93_snapshot/PROGRAMME_MILESTONES.csv` | regression data | stored copy of a delivered M9.3 programme table, used as the comparison for the append-only check |
| `regression/m93_snapshot/RFC_REGISTER.csv` | regression data | stored copy of a delivered M9.3 programme table, used as the comparison for the append-only check |
| `regression/m93_snapshot/STATUS_REGISTER.csv` | regression data | stored copy of a delivered M9.3 programme table, used as the comparison for the append-only check |
| `tests/test_api_m94_corrections.py` | tests | new: 29 tests in six classes (a clock that raises, a clock that says something else, the one-reading rule, accessor failures, failure-path integrity, the M9.3 rule still holding), all through the public entry points; 18 of them fail or error on the delivered M9.3 code |
| `tools/make_m94_registers.py` | tools | new: adds the M9.4 rows |
| `tools/probe_m93_clock_failure.py` | tools | new: the clock failure in a few lines each; DEFECT PRESENT on M9.3, handled on M9.4 |
| `tools/programme_check_m94.py` | tools | new: structure checks of the M9.4 records |
| `tools/run_m94_all.py` | tools | new: wrapper in 88 numbered groups (the M5 and M6 wrappers split into their components); `--list`, `--group N` and `--range A-B` split it |
| `tools/run_regression_m94.py` | tools | new: shows that nothing but the declared files changed; `--step Rnn` splits the long steps |

Run output of the release is under `logs/m94/` and is not compared. `regression/BASELINE_M93.json` records the hash of every file above and is itself not compared. The earlier logs under `logs/m93/` and before are carried unchanged: they describe the earlier code and are not evidence about this release. The line-level difference of the one application file is `logs/m94/diff_approval_boundary_vs_m93.diff` (57 lines added, 12 removed).

## 4. What the corrected boundary does

The full contract is `programme/APPROVAL_REQUEST_BOUNDARY.md`. In every one of the three calls, the first thing decided about the session is:

| Situation | M9.3 | M9.4 |
|---|---|---|
| `clock.now()` raises an ordinary exception (`RuntimeError`, `OSError`, `TimeoutError`, `ValueError` and others) | the exception reaches the caller; no audit entry | the session is ended: `present` answers `NOT_ALLOWED`, `request_approval` answers `SESSION_EXPIRED`, `check_for_execution` answers `{'valid': False, 'code': 'NOT_ALLOWED'}`; the refusal is audited with the reason that names the clock |
| the clock returns `None`, a number, a list, text that is not a real moment, or an impossible date or time | ended (the M9.3 rule) | ended, with the same refusals and the clock named as the reason |
| the clock has no `now`, or `now` is not callable | an exception | ended, with the clock named as the reason |
| `ctx.expires_at` raises, is missing, is not a string or is not a real moment | ended or an exception | ended |
| the actor kind cannot be read | an exception | not a person: `HUMAN_REQUIRED` or `NOT_ALLOWED` |
| the reading equals the expiry, or is later | ended | ended |
| the reading is earlier than the expiry | live | live |
| later reads of the clock in the same call | read again inside the lifecycle | none: the one reading is used |
| `KeyboardInterrupt`, `SystemExit` | propagate | propagate (only `Exception` is caught) |

No result code was added and no outcome other than the existing refusals. If the audit write of a refusal fails, the refusal is still returned and is not reported as audited: the existing best-effort rule for refusals applies (CF-29, EDR-32); the first audit write of an approval still raises by contract, and a failing clock never reaches that point.

## 5. Tests, run against the delivered M9.3 code first

29 new tests in `tests/test_api_m94_corrections.py`, in six classes, all through the public entry points with deterministic clocks (`RaisingClock`, `FailsAfter`, `Counting`, `Advancing`) and isolated fixtures. They were run against the delivered, unmodified M9.3 package (extracted from its ZIP, hash-checked): 18 of the 29 fail or error there (`logs/m94/new_tests_on_delivered_m93.log`), in five of the six classes; the same 29 pass on this release. The other 11 pass on both: they check what M9.3 already did right (a clock that returns something other than a real moment ends the session; a reading equal to, later than or earlier than the expiry) and make sure M9.4 keeps it.

They cover: ten exception types raised by `now()` at each of the three calls; 22 bad readings (`None`, numbers, a boolean, lists, a mapping, bytes, text, malformed and impossible moments, a leap second, non-ASCII digits) at each of the three calls; readings equal to, later than and earlier than the expiry; a clock that fails after its first read; a clock with no `now` or that is not callable; an expiry or actor kind that raises; that no finding becomes approved or executable on a failing clock, with the same request id usable afterwards; that repeated refusals leave one history; that a failing audit write during a clock refusal is still a refusal and is not counted as audited; another tenant's session; a replay of an answered request with a failing clock; the missing approver role; and the M9.3 expiry and syntax rules at the helper and at the entry points.

The mutation run over the module was repeated fresh by this build (`logs/m94/mutation_run_m94.log`, `logs/m94/mutation_chunks_m94.log`) and the package-level sabotage list was extended with the correction (`logs/m94/sabotage_m94.log`).

## 6. Results, and how each is classified

Four classes are kept apart, as the audit asked.

* **Independently reproduced** (by the auditor, as relayed): the original M9.2 gap (three impossible expiry values accepted on M9.2); the M9.3 expiry cases (year 0001 accepted, 0000 refused, 2000-02-29 accepted, 1900-02-29 refused, 2400-02-29 accepted, second 60 refused, trailing newline refused, non-string refused); the 18 M9.3 correction tests; the M9.3 static regression (14 checks), the M9.2 static regression (16 checks) and the M9.1 baseline check; individually run test groups, including reruns of groups that timed out in batches; and the uncaught `RuntimeError` at all three entry points on M9.3.
* **Builder-reported**: every result of this release, including the reproduction of the failure on the delivered M9.3 code, the correction tests, the full unit run, the mutation run, the sabotage run and the clean-extraction run (documents file, section 3; `logs/m94/`).
* **Failed**: the clock failure handling of M9.3 (F-63). Nothing in this release is reported failed by any reviewer; no one but the builder has run it.
* **Incomplete**: some long nested regression wrappers did not complete in the auditor's runs; the auditor obtained no fresh complete mutation result (the existing mutation logs are builder artefacts); and the auditor's one approval-boundary invocation counted 67 tests, which is one test file, not evidence that every suite ran (CF-31). They are not counted as passes. This release splits every long run (`--group`, `--step`, chunks of ten mutants), runs each piece from a clean extraction, records the builder's times, and lists anything that did not complete in the documents file; it does not turn the auditor's incomplete runs into passes.

**Unverified assumptions** this release rests on: that the Engine's real clock behaves as the `now()` interface the tests use; that a real sealed context cannot raise when its other attributes are read; that the audit store reports a failed write by raising, as the test double does; and that the builder's test doubles reflect those behaviours. None of these was seen or tested against Engine code.

## 7. Carried forward

All of these remain open (`programme/CARRIED_FORWARD_REGISTER.csv`, CF-01 to CF-31): CF-22 and CF-25 are unedited and open; CF-26 to CF-28 and CF-30 stand; CF-29 (the approval and its audit entry are not written atomically; EDR-32, the Engine's; the audit is at least once, not exactly once) is unedited and open; CF-31 records what the M9.3 audit could not complete or obtain, for the auditor to complete or confirm. F-52 to F-63 stay open until the auditor verifies them; F-62 in particular is not marked closed, as the audit directed.

## 8. What this does not show

It does not show that the correction is independently verified: no one but the builder has reviewed it. It does not show that the boundary is complete: the same-class sweep is the builder's, and the auditor found this failure by probing, which the builder's tests and mutation run on M9.3 had not. It does not show that a real clock, a real session issuer or a real audit store behave as the test doubles do: none of them was seen. It is not an approval screen, an API, a session store, a role directory or a project permission model, and it executes nothing. Nothing in it is production-ready or accepted.
