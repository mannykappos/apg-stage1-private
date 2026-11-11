# Change record APG-M6.3: strict version and digest validation (finding F-55)

| Field | Value |
|---|---|
| Release | APG-M6.3, a separately versioned correction of the delivered M6.2 package |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** F-55 is corrected in the builder's tree and stays open until the auditor verifies it independently. F-52, F-53 and F-54 also stay open until independently verified. |
| Authority | The independent audit of APG-M6.2 (2026-10-15) directed: investigate proposed F-55 first; add fail-closed type and range validation and regression tests first; issue a separately versioned correction preserving the M5, M6, M6.1 and M6.2 archives; re-run the relevant approval tests, all detection and finding tests, regression and register checks, mutation tests and the clean-extraction build; record every run as builder-run or independently reproduced accurately; keep F-52, F-53 and F-54 open until independently verified; do not start Engine #17 or M7 or claim production readiness. |
| Untouched | Delivered M5 ZIP `4c15ad568c5c5ff12977529ba3253c9042781e4aa272af3b87a10eab5a010be6`; delivered M6 ZIP `abcfefd9f28464de46dc205c1112b2ea33f537ef4a788562484c1d24109a1efb`; delivered M6.1 ZIP `f0fac9a8d3b5920b985f6de939580dd300f58a1cec268f11463a9ccd7823e277`; delivered M6.2 ZIP `774f835291b61a9bd7aa690389d444ddf3634c316c8298a1dc121db497421f8e`; locked Sections 00-18 (`487becabdf47796800937d13a706a19b63b7b8230ecc5354b2f01a647ae5d960`); CR-09; the RTM; RFC-01 (still PROPOSED and unnumbered); the milestones table (M7 not started); the Engine #17 governance register (G-01 to G-12, unchanged). |

## 1. The defect

APG-M6.2 compared the stored `proposed_version` of an action with the finding's version using Python equality. In Python `True == 1` and `1.0 == 1`, so a stored proposal version of `True` counted as version 1. The audit's reproduction: make a normal version-1 proposal, change the stored `proposed_version` to `True` leaving the digest unchanged, obtain the current approval token, call `approve_action()`; the action was accepted as `action_approved`. The builder repeated it on the delivered M6.2 tree (`logs/m63/probe_on_delivered_m62.log`) and found the same weakness in the version named by the approver: `approving_version=True` was accepted for a version-1 finding. The approval-token check already refused a boolean as a version; the proposal-side check and the named-version check did not. The M6.2 tests did not cover malformed values; that is the builder's omission. It is recorded as F-55.

## 2. Impact

APG never carries out an action or moves money, so the weakness concerns the integrity of the record. It could occur only if a stored record held a malformed version (a corrupted or hand-edited record, or a legacy record), or if a screen or API passed a boolean as the version it had shown. The record store refuses floats, so a stored `1.0` cannot be reached through it; the functions, called directly, nevertheless accepted a `1.0` until now. No stored data outside the builder's own tests exists.

## 3. Files changed

Compared byte for byte with the delivered M6.2 ZIP. All other files (the count is in `regression/BASELINE_M62.json`) are identical.

**Changed (13)**

| File | Kind | What changed and why |
|---|---|---|
| `README.md` | records and documents | adds the M6.3 section above the unchanged M6.2 text |
| `RUN_COMMANDS.txt` | records and documents | adds the M6.3 commands above the unchanged M6.2 text |
| `apg/det/findings.py` | application code | the correction itself: `_is_version` and `_is_digest`; `proposal_current` and `approval_current` require a well-formed finding version, stored version and digests (a boolean, a float, 0, a negative number, a text or a missing value is not a version) and never treat a proposal marked stale as current; a named version or digest that is not well formed is refused with `APPROVAL_TOKEN_REQUIRED` before any other comparison; `_token_ok` uses the same rules; a stored value that is not a dictionary no longer raises |
| `programme/CARRIED_FORWARD_REGISTER.csv` | records and documents | row CF-24 appended (the M6.2 audit's verification limits); no earlier row changed |
| `programme/FINDINGS_REGISTER.csv` | records and documents | row F-55 appended; no earlier row changed (F-52, F-53 and F-54 are not rewritten) |
| `programme/INTERPRETATIONS_REGISTER.csv` | records and documents | rows I-71 to I-74 appended; no earlier row changed |
| `programme/STATUS_REGISTER.csv` | records and documents | rows SR-70 and SR-71 appended; no earlier row changed |
| `tools/m5_mutants.py` | tools | runs the new test file in the M5 mutation run (added to its list of tests); nothing else |
| `tools/make_m0.py` | tools | runs the M6.3 register step after the M6.2 one, so the derived-files check regenerates the programme tables with the M6.3 rows; nothing else |
| `tools/programme_check_m62.py` | tools | check N06 accepts a carried-forward register that has rows after CF-23 (CF-24 is appended in M6.3); nothing else |
| `tools/run_regression_m6.py` | tools | accepts files the M6.3 baseline declares and pins by hash; check L05 accepts status-register rows with milestone M6.3; nothing else |
| `tools/run_regression_m61.py` | tools | accepts the files the M6.3 baseline declares and pins (R02, R03), files it adds (R04) and rows with milestone M6.3 (R10, R11); every other check is unchanged |
| `tools/run_regression_m62.py` | tools | accepts the files the M6.3 baseline declares and pins (R02, R03), files it adds, a longer known set and rows with milestone M6.3 (R10, R11); every other check is unchanged |

**Added (15)**

| File | Kind | What it is |
|---|---|---|
| `programme/CHANGE_RECORD_APG-M6.3.md` | records and documents | new: this record |
| `regression/m62_snapshot/CARRIED_FORWARD_REGISTER.csv` | regression data | stored copy of a delivered M6.2 programme table, used as the comparison for the append-only check |
| `regression/m62_snapshot/E17_GOVERNANCE_REGISTER.csv` | regression data | stored copy of a delivered M6.2 programme table, used as the comparison for the append-only check |
| `regression/m62_snapshot/ENGINE_HANDOFF_REGISTER.csv` | regression data | stored copy of a delivered M6.2 programme table, used as the comparison for the append-only check |
| `regression/m62_snapshot/FINDINGS_REGISTER.csv` | regression data | stored copy of a delivered M6.2 programme table, used as the comparison for the append-only check |
| `regression/m62_snapshot/INTERPRETATIONS_REGISTER.csv` | regression data | stored copy of a delivered M6.2 programme table, used as the comparison for the append-only check |
| `regression/m62_snapshot/PROGRAMME_MILESTONES.csv` | regression data | stored copy of a delivered M6.2 programme table, used as the comparison for the append-only check |
| `regression/m62_snapshot/RFC_REGISTER.csv` | regression data | stored copy of a delivered M6.2 programme table, used as the comparison for the append-only check |
| `regression/m62_snapshot/STATUS_REGISTER.csv` | regression data | stored copy of a delivered M6.2 programme table, used as the comparison for the append-only check |
| `tests/test_det_version_types.py` | tests | new: 34 regression tests for the correction, written first |
| `tools/make_m63_registers.py` | tools | new: adds the M6.3 rows |
| `tools/probe_malformed_proposal_version.py` | tools | new: reproduces the audit's defect in a few lines (and the named-version case); exits 1 on the M6.2 code, 0 here |
| `tools/programme_check_m63.py` | tools | new: structure checks of the M6.3 records |
| `tools/run_m63_all.py` | tools | new: wrapper that runs every M6.3 check except the long mutation runs |
| `tools/run_regression_m63.py` | tools | new: shows that nothing but the declared files changed |

Run output of the correction is under `logs/m63/` and is not compared. `regression/BASELINE_M62.json` records the hash of every file above and is itself not compared. The M6.2 logs under `logs/m62/` are carried unchanged.

## 4. What the correction does

| Situation | Result |
|---|---|
| A version (the finding's, a stored proposal's or approval's, or one named by an approver) | Valid only if it is a whole number of at least 1 and not a boolean. `True`, `False`, `1.0`, `0`, negative numbers, texts and missing values are not versions. |
| A digest (the finding's, a stored one, or one named by an approver) | Valid only if it is a non-empty text. |
| A stored proposal with a malformed version or digest, or a finding with a malformed version or digest | `proposal_current` is false, so approval is refused with `STALE_PROPOSAL` and an audited reason; nothing in the record changes. The reason text says `(not recorded)` or `(not a valid version number)` rather than a value. |
| A stored approval with a malformed version or digest | `approval_current` is false: it is not an approval in force. |
| A proposal explicitly marked `proposal_state: stale` | Never current, even if its version and digest happen to match. A record without the field is judged by version and digest only (I-72). |
| An approver names a version or digest that is not well formed | Refused with `APPROVAL_TOKEN_REQUIRED` and audited, after the self-approval check and before any other comparison. `approve_action` refuses the same values through the same rules (`_token_ok`). |
| A stored `action` that is not a dictionary | Not a proposal; no error is raised. |
| Floats | The record store refuses them (`PayloadInvalid`), so none can be stored; the functions refuse them too (I-73). |
| A damaged value in a stored record | Refused, not repaired in place: it is kept as found. The normal route (reviewer returns the finding to `confirmed`, owner proposes again) replaces the damaged proposal, which is then recorded in `proposal_history` as stale (I-74). |
| Everything else | Unchanged from M6.2: ten statuses, 14 transitions, the proposer cannot approve, stale proposals and ended approvals are kept in the history, the re-proposal route is reviewer then owner. |

The readings behind this are I-71 to I-74 in the interpretations register, retained for review.

## 5. Tests

`tests/test_det_version_types.py` has 34 tests. They were written before the change. Run against the delivered M6.2 code, 19 of them fail and 2 error (the rest cover behaviour that was already right, for example a normal integer version being accepted and the proposer being refused as self-approver). They cover the audit's list through the real `approve_action()` path with no state change on refusal: `True`, `False`, `1.0` (through the function, because the store cannot hold it), `0`, negative numbers, missing values, texts and a normal integer, for the stored proposal version, the finding version, the digests and the named version and digest; a damaged non-dictionary action; the explicit stale mark; and that nothing else moved.

No existing test file was changed. All 47 proposal-binding tests, all 21 approval-binding tests and the frozen M5 detection and finding tests pass unchanged on the corrected code. The whole unit suite, the probes, the M5 and M6 wrappers and the regressions are run by `tools/run_m63_all.py`. The M5 mutation runs for the four M5 modules are repeated (the source hash changed because `findings.py` and the test list changed).

## 6. Results, and how each is classified

Three classes are kept apart. **Builder-run**: run by the builder in the builder's sandbox; this is the status of every result of this release. **Reproduced by the builder from the auditor's description**: the F-55 defect on the delivered M6.2 tree (`logs/m63/probe_on_delivered_m62.log`). **Independently reviewed**: nothing in this release. The audit of APG-M6.2 is an independent review of M6.2: it reported that the M6.2 hashes, the 47 proposal-binding tests, the static regression and register checks, the M6 golden, corpus, contract, fault and demonstration checks passed in its environment, and that the full unit suite, the long wrappers, the mutation results and the clean-extraction wrapper were not independently completed (CF-24). Those statements are about M6.2 and do not carry over to M6.3. A run cut off by a time limit is incomplete, not a pass.

The test, mutation, sabotage and clean-extraction results are in the documents file delivered with the archive and in `logs/m63/`; they are not copied into this record because they are produced after it is written.

## 7. Carried forward

All of these remain open and are untouched by this release; they are listed with their sources in `programme/CARRIED_FORWARD_REGISTER.csv` (CF-01 to CF-24): all M6 data is synthetic and the ports were tested only against in-memory references; no Anchor Engine, production database, event bus, AUIF or Governor repository is integrated; the event and provenance gaps; tenant and project isolation (F-39, EDR-29; not fixed here); invoice-only cost coverage and the missing cost components; quantity reconciliation inputs, payment-term economics and capacity controls; M6 portfolio purchasing is a backward-looking rate-gap estimate, not the specified forward aggregation; no realised-outcome workflow and no finance assumptions; Engine #17 is not built; RFC-01 is PROPOSED and unnumbered; the Engine #1-#18 mapping is not authoritative; the V1-V4 baseline rules are proposed only; and the existing open decisions. The integration gate (a real approval screen or API must call the fail-closed entry point and pass the version it displayed) is CF-22, for the handoff package at M12. CF-24 records the verification the M6.2 audit could not complete.

## 8. What this does not show

It does not show that the correction is independently verified: nothing here has been reviewed by anyone but the builder, and the new archive is for the auditor to verify. It does not show that the fail-closed rules cover every malformed shape a real record store could hold; they cover the cases listed in section 4 (I-74). It does not show anything about the Engine: a screen or API must use `approve_action`, and real stored records need checking and moving (I-64, I-68). It does not make the prototype production-ready or integrated, and it does not start Engine #17, the versioned-baseline foundations, E1-E5 or M7.
