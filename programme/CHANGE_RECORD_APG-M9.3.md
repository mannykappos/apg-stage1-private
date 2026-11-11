# Change record APG-M9.3: correction of the session expiry check in the approval request boundary after the independent audit of APG-M9.2 (F-62)

| Field | Value |
|---|---|
| Release | APG-M9.3, a separately versioned, additive correction release: the delivered M9.2 package plus the correction below. The delivered M9.2 and M9.1 ZIPs and documents are not modified or replaced. |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** The audit reproduced the gap on M9.2; it has not reviewed this correction. F-52 to F-62, CF-22, CF-25 and CF-29 stay open until independently verified. |
| Authority | The auditor's verdict on M9.2 relayed by the product owner (Fri 2026-10-16): the three M9.1 defects are corrected in M9.2; one validation gap remains in `_session_live`; produce a small additive correction release (M9.3); an expiry is live only if it is a valid UTC timestamp in the required format and strictly later than now; keep strict ASCII and whole-string validation; add tests for invalid months, days, hours, minutes and seconds, impossible calendar dates, valid leap days, trailing newlines, non-ASCII digits, expired and valid future timestamps, through the boundary entry points where feasible; re-run the M9.2 correction tests, the approval-boundary tests, the permission contracts, the lifecycle tests, probes, mutation chunks, sabotage and regression; keep CF-22, CF-25 and CF-29 open; EDR-32 atomicity stays an Engine requirement; do not start Engine #17 or M7; RFC-01 stays PROPOSED. |
| Untouched | Delivered M5 ZIP `4c15ad568c5c5ff12977529ba3253c9042781e4aa272af3b87a10eab5a010be6`; M6 `abcfefd9f28464de46dc205c1112b2ea33f537ef4a788562484c1d24109a1efb`; M6.1 `f0fac9a8d3b5920b985f6de939580dd300f58a1cec268f11463a9ccd7823e277`; M6.2 `774f835291b61a9bd7aa690389d444ddf3634c316c8298a1dc121db497421f8e`; M6.3 `4379699e0cdc32c7cb0088006fc2c2ae6dd41c1f2a4e1048fdd9e01ae7a42acc`; M6.4 `ae481618dce8a2426d84c0353659cd9992a214ee29ee122329fd5ffc766c8e57`; M6.5 `ab41a43f7ffa797dbdacacce1be04aebef0ec0ac7fba3fd2de5de26f9a6ac5fe`; M9.1 ZIP `12326469a951238f674013918f279b89a75f3ea471fa6c5cbcefd1df0496cb9f` and documents `d6431737b0160ac2be1e50ec8a92bbd55c147720107b2045118e51704265f453`; M9.2 ZIP `ad889d545a5ad91a100ff89425353b425a908fe23f50c44d0a11dd128247f1d8` and documents `ebbb77f2e99e26fb6cc54ac710763b000737dc965a45f8f3fb358163ee7f7df0`; locked Sections 00-18 (`487becabdf47796800937d13a706a19b63b7b8230ecc5354b2f01a647ae5d960`); CR-09; the RTM; RFC-01 (still PROPOSED and unnumbered); the Engine #17 governance register (G-01 to G-12); the milestone and Engine handoff tables (no Engine record was added); every application file except `apg/api/approval_boundary.py`; and every existing test. |

## 1. What this release is

A correction release for one function. The audit of M9.2 found that `_session_live()` in `apg/api/approval_boundary.py` accepted any expiry of the right shape and then compared it with the present time as a string, so impossible values counted as live. The function is corrected, the tests that reproduce the gap were run against the unmodified M9.2 package, and nothing else changed: no screen, API, session store, role directory or permission model exists, nothing executes an action, and Engine #17, the versioned-baseline foundations and M7 are not started.

## 2. The defect, and where it came from

| ID | Source | What was wrong in M9.2 | What changed | Test class (tests that fail on M9.2) |
|---|---|---|---|---|
| F-62 | Audit of M9.2; the three values were reproduced by the auditor | `_session_live` matched the expiry against a whole-string ASCII pattern (the M9.2 correction of F-60) and compared it as a string. The pattern checks shape only, so `2999-99-99T99:99:99Z`, `2999-13-01T00:00:00Z` and `2999-01-01T25:61:61Z` were live, and so were impossible dates such as `2999-02-30`. The present time was not checked either. | An expiry is live only if it is a real UTC moment in the required format and strictly later than the present time, which must itself be a real moment (I-93 to I-95). | `TestTheExpiryMustBeARealMomentInTime` (6); `TestTheSessionCheckThroughTheBoundaryEntryPoints` (5); `TestTheSameShapeFlawsStayClosed` (1) |

How far the gap reaches: the auditor demonstrated no end-to-end bypass with a normally issued, validly sealed session; the context is immutable and the session issuer is the Engine's. The builder's own demonstration on M9.2 used a test double (`Expiring` in the correction tests) that presents a context with a chosen expiry. **That double bypasses the seal**, which a real context carries; it shows what the helper does with an impossible value, not that a real sealed session can be forged. The helper is used by all three entry points of the boundary, so it had to treat impossible values as not live whoever issues the session.

The sweep for the same class of weakness covered every place the module reads a time or matches a pattern: the expiry (this correction), the clock (now held to the same rule), and the identifiers (F-60, unchanged). It is a builder's sweep, not an independent one; the auditor should repeat it.

## 3. Files changed and added

Compared byte for byte with the delivered M9.2 ZIP. All other files (the count is in `regression/BASELINE_M92.json`) are identical.

**Changed (19)**

| File | Kind | What changed and why |
|---|---|---|
| `README.md` | records and documents | adds the M9.3 section above the unchanged M9.2 text |
| `RUN_COMMANDS.txt` | records and documents | adds the M9.3 commands (the defect on M9.2, the split groups, the regression steps, the mutation chunks of ten) above the unchanged M9.2 text |
| `apg/api/approval_boundary.py` | application code | the correction F-62: `_session_live` now requires a real UTC moment (new helper `_is_moment`) and a clock that is itself a real moment (section 4) |
| `programme/APPROVAL_REQUEST_BOUNDARY.md` | records and documents | the contract document revised: what a live session is (a real UTC moment, strictly later than the present one, the clock held to the same rule) |
| `programme/CARRIED_FORWARD_REGISTER.csv` | records and documents | row CF-30 appended (the auditor's unfinished nested M5/M6 wrapper runs on M9.2); CF-22, CF-25 and CF-29 are not edited and stay open |
| `programme/FINDINGS_REGISTER.csv` | records and documents | row F-62 appended (status: corrected in APG-M9.3, builder-implemented, open until independently verified); no earlier row changed; F-52 to F-61 stay open |
| `programme/INTERPRETATIONS_REGISTER.csv` | records and documents | rows I-93 to I-95 appended; no earlier row changed |
| `programme/STATUS_REGISTER.csv` | records and documents | rows SR-84 to SR-86 appended; no earlier row changed |
| `tools/m91_mutants.py` | tools | runs the M9.3 correction tests as well; the id of the one documented equivalent mutant moved again (AB-BOL-003 to AB-BOL-005) because new `and` sites were added earlier in the module (same site; the proof is unchanged) |
| `tools/make_m0.py` | tools | runs the M9.3 register step after the M9.2 one, so the derived-files check regenerates the programme tables with the M9.3 rows; nothing else |
| `tools/programme_check_m92.py` | tools | allows the rows appended after CF-29 and F-61; nothing else |
| `tools/run_regression_m6.py` | tools | L03 and L04 accept the M9.3 additions when the M9.3 baseline pins the tables; accepts the files, rows and tables the M9.3 baseline declares and pins by hash; every other check is unchanged |
| `tools/run_regression_m61.py` | tools | accepts the files, rows and tables the M9.3 baseline declares and pins by hash; every other check is unchanged |
| `tools/run_regression_m62.py` | tools | accepts the files, rows and tables the M9.3 baseline declares and pins by hash; every other check is unchanged |
| `tools/run_regression_m63.py` | tools | accepts the files, rows and tables the M9.3 baseline declares and pins by hash; every other check is unchanged |
| `tools/run_regression_m64.py` | tools | accepts the files, rows and tables the M9.3 baseline declares and pins by hash; every other check is unchanged |
| `tools/run_regression_m65.py` | tools | accepts the files, rows and tables the M9.3 baseline declares and pins by hash; every other check is unchanged |
| `tools/run_regression_m91.py` | tools | accepts the files, rows and tables the M9.3 baseline declares and pins by hash; every other check is unchanged |
| `tools/run_regression_m92.py` | tools | accepts the files, rows and tables the M9.3 baseline declares and pins by hash; every other check is unchanged |

**Added (15)**

| File | Kind | What it is |
|---|---|---|
| `programme/CHANGE_RECORD_APG-M9.3.md` | records and documents | new: this record |
| `regression/m92_snapshot/CARRIED_FORWARD_REGISTER.csv` | regression data | stored copy of a delivered M9.2 programme table, used as the comparison for the append-only check |
| `regression/m92_snapshot/E17_GOVERNANCE_REGISTER.csv` | regression data | stored copy of a delivered M9.2 programme table, used as the comparison for the append-only check |
| `regression/m92_snapshot/ENGINE_HANDOFF_REGISTER.csv` | regression data | stored copy of a delivered M9.2 programme table, used as the comparison for the append-only check |
| `regression/m92_snapshot/FINDINGS_REGISTER.csv` | regression data | stored copy of a delivered M9.2 programme table, used as the comparison for the append-only check |
| `regression/m92_snapshot/INTERPRETATIONS_REGISTER.csv` | regression data | stored copy of a delivered M9.2 programme table, used as the comparison for the append-only check |
| `regression/m92_snapshot/PROGRAMME_MILESTONES.csv` | regression data | stored copy of a delivered M9.2 programme table, used as the comparison for the append-only check |
| `regression/m92_snapshot/RFC_REGISTER.csv` | regression data | stored copy of a delivered M9.2 programme table, used as the comparison for the append-only check |
| `regression/m92_snapshot/STATUS_REGISTER.csv` | regression data | stored copy of a delivered M9.2 programme table, used as the comparison for the append-only check |
| `tests/test_api_m93_corrections.py` | tests | new: 18 tests in three classes (the rule on its own, the rule through the three entry points, the shape flaws that stay closed); 12 of them fail or error on the delivered M9.2 code |
| `tools/make_m93_registers.py` | tools | new: adds the M9.3 rows |
| `tools/probe_m92_session_expiry.py` | tools | new: the impossible expiry values in a few lines each; DEFECT PRESENT on M9.2, corrected on M9.3 |
| `tools/programme_check_m93.py` | tools | new: structure checks of the M9.3 records |
| `tools/run_m93_all.py` | tools | new: wrapper in 84 numbered groups (the M5 and M6 wrappers split into their components); `--list`, `--group N` and `--range A-B` split it |
| `tools/run_regression_m93.py` | tools | new: shows that nothing but the declared files changed; `--step Rnn` splits the long steps |

Run output of the release is under `logs/m93/` and is not compared. `regression/BASELINE_M92.json` records the hash of every file above and is itself not compared. The earlier logs under `logs/m92/` and before are carried unchanged: they describe the earlier code and are not evidence about this release.

## 4. What the corrected check does

The full contract is `programme/APPROVAL_REQUEST_BOUNDARY.md`. A session is live only if all of these hold:

| Condition | Rule |
|---|---|
| Shape | exactly `YYYY-MM-DDTHH:MM:SSZ`, ASCII digits, the whole string (no trailing newline, no non-ASCII digits) |
| Month, day | month 1 to 12; a day the month has; 29 February only in a Gregorian leap year (divisible by 4, except centuries not divisible by 400) |
| Hour, minute, second | hour 0 to 23; minute 0 to 59; second 0 to 59 (a leap second is refused; the format cannot say it) |
| Year | 0001 or later (0000 does not exist) |
| Order | strictly later than the present time; an expiry equal to the present time has ended |
| Present time | the clock must itself give a real moment; if it does not, every session counts as ended (fail closed) |

| Situation | M9.2 | M9.3 |
|---|---|---|
| Expiry `2999-99-99T99:99:99Z`, `2999-13-01T00:00:00Z`, `2999-01-01T25:61:61Z` or `2999-02-30T00:00:00Z` | live | not live: `present` and `check_for_execution` refuse, `request_approval` answers `SESSION_EXPIRED` |
| Expiry `2999-12-31T23:59:59Z` or `2996-02-29T00:00:00Z` | live | live |
| A clock that does not give a real moment | compared as a string | every session ended |

## 5. Tests, run against the delivered M9.2 code first

18 new tests in `tests/test_api_m93_corrections.py`, in three classes. They were run against the delivered, unmodified M9.2 package (extracted from its ZIP, hash-checked): 12 of the 18 fail or error there (`logs/m93/new_tests_on_delivered_m92.log`), and every class has at least one failing test; the same 18 pass on this release. The remaining 6 tests pass on both: they pin behaviour that was already right (valid future dates, expired timestamps, trailing newlines, non-ASCII digits) and must stay right. The build repeats the run on M9.2 each time, so the claim does not rest on the order in which the builder worked. `tools/probe_m92_session_expiry.py` shows the same values in a few lines each (`logs/m93/probe_on_delivered_m92.log`). The existing 78 API tests and the 24 M9.2 correction tests were not changed and pass.

The tests cover invalid months, days, hours, minutes and seconds; impossible calendar dates; valid leap days (and the century rules); trailing newlines; non-ASCII digits; expired and equal-to-now timestamps; valid future timestamps; year 0000 and 0001; and a clock that is not a real moment. The boundary-level tests use the `Expiring` double (see section 2) and a fixed clock, and check the three entry points and the audit events (no event carries an impossible value as a resource name).

The mutation run over the module was repeated (`logs/m93/mutation_run_m93.log`) and the package-level sabotage list was extended with the correction (`logs/m93/sabotage_m93.log`).

## 6. Results, and how each is classified

Four classes are kept apart, as the audit asked.

* **Independently reproduced** (by the auditor, on M9.1 and M9.2, as relayed): the original M9.1 defects, all five probe scenarios; the 24 M9.2 correction tests pass; the approval-boundary tests, the permission-port contract and the earlier probes pass; all 27 lifecycle test files individually (605 tests); the mutation run in chunks (91 of 92 killed, one documented equivalent); the ZIP hash and integrity, the M9.2 static regression and register checks, the M6.1 to M6.5 static regressions, the procurement golden checks and the M5/M6 demonstrations; and the three impossible expiry values above. Nothing in this release (M9.3) has been independently reproduced.
* **Builder-reported**: every result of this release, including the reproduction of the gap on the delivered M9.2 code, the correction tests, the full unit run, the mutation run, the sabotage run and the clean-extraction run (documents file, section 3; `logs/m93/`).
* **Failed**: the session expiry check of M9.2 failed for impossible values (F-62). Nothing in this release is reported failed by any reviewer; no one but the builder has run it.
* **Incomplete**: the auditor's full nested M5 and M6 regression wrapper runs on M9.2 did not complete within the auditor's execution limits and are not counted as passes (CF-30). This release splits every long run (`--group`, `--step`, chunks of ten mutants) and records the builder's own times; it does not turn the auditor's incomplete runs into passes.

## 7. Carried forward

All of these remain open (`programme/CARRIED_FORWARD_REGISTER.csv`, CF-01 to CF-30): CF-22 and CF-25 are unedited and open; CF-26 to CF-28 stand; CF-29 (the approval and its audit entry are not written atomically; EDR-32, the Engine's; the audit is at least once, not exactly once) is unedited and open; CF-30 records the auditor's incomplete nested wrapper runs on M9.2, for the auditor to complete or confirm. F-52 to F-62 stay open until independently verified. All M6 data is synthetic and the ports were tested only against in-memory references; no Anchor Engine, production database, event bus, AUIF or Governor repository is integrated; tenant and project isolation (F-39, EDR-29) is not fixed here; the screen, API, transport, session store and issuer, role directory and project permission model are the Engine's (EDR-11, EDR-20, EDR-29, EDR-31). Invoice-only cost coverage, quantity reconciliation inputs, payment-term economics and capacity controls, and the backward-looking M6 purchasing view are unchanged.

## 8. What this does not show

It does not show that the correction is independently verified: no one but the builder has reviewed it. It does not show that the boundary is complete: the same-class sweep is the builder's, and the auditor found this gap by reading and probing, which the builder's own tests and mutation run had not. It does not show that a real sealed session cannot be forged: the session issuer and the seal are the Engine's and were not seen. It does not show exactly-once auditing or a transaction across state and audit (EDR-32). It does not show that an approval screen, an API or a permission model exists or is safe: none exists, and the reference port is a test double. It does not make the prototype production-ready or integrated, and it does not start Engine #17, the versioned-baseline foundations or M7.
