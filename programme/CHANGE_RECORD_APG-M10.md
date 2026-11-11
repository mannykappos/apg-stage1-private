# Change record APG-M10: the UX/UI prototype, director first (synthetic data only)

| Field | Value |
|---|---|
| Release | APG-M10, a separately versioned, additive release. It is the delivered APG-M8.1-R1 package plus the changes below. That package is ZIP SHA-256 `e39eef1f72eff49131179e4a3a07ee2b178c43bad8f0eaef556d95c0927b778e`, 1,390 files, with every file hash in `regression/m10/M81R1_MANIFEST.sha256`. The APG-M8.1-R1 ZIP and every earlier ZIP are not modified or replaced. |
| Status | **Builder-made and locally tested; not accepted.** No independent review of APG-M10 has taken place (CF-56). A prototype, not a production screen, an API, a login or a session. No live system, no network call. The approval screen sends nothing. |
| Authority | The product owner, 2026-10-21: "Authorise M10 as proposed, director first". **As proposed:** a UX/UI prototype over Builder Zero synthetic data, using real APG calculations read through the M9 API contract. Its screens are portfolio and project overview, findings and recommendations with every number linked to its evidence, data health with honest "cannot assess" states, import status, approvals and materials buy-timing. It has automated browser tests, accessibility checks and screenshots, and its primary user is a builder's director. |
| What "read through the M9 API contract" means here | The M9 contract is the approval boundary and its project-action port (EDR-31). The prototype asks that port, a fixed synthetic stand-in, what each person may view and approve. The approvals screen is the real `present()` answer, and the recorded approval's standing is the real `check_for_execution()` answer. APG has no API for figures (EDR-12 is the Engine's), so the figures are read from the APG calculations directly (`apg.fin.calc_records.run_calc`), never computed by the prototype. |
| Gates still open | CF-53 (which record types may validly be empty), CF-52, CF-56, CF-57. EDR-05, EDR-06, EDR-12, EDR-18, EDR-29, EDR-31, EDR-39, EDR-40, EDR-41 and every other open EDR and CF item stay open. CF-41 stands. The construction definitions are PROPOSED. |

## 1. Baselines (before any change)

The APG-M8.1-R1 ZIP matched its hash, and its own regression (`tools/run_regression_m81r1.py --all`) passed on a fresh extraction (`logs/m10/00_baseline_regression_m81r1.log`).

## 2. What was added

| Part | What it is |
|---|---|
| `apg_ui/viewmodel.py` | Builds what each screen shows by running the existing APG code on Builder Zero.<br>**The worlds.** One world per tenant on the file-import route, loaded as the golden runs load it. The detection and (zero_one) procurement runs are ingested. A scripted demonstration state is laid on top (I-149). The connected-systems route (AUIF rev14) is imported into a separate world, and only its gate answer and import results are kept (I-147).<br>**Each person's view.** Three views: Dana, director of Builder Zero One; Drew, director of Builder Zero Two; Pat, project manager on PRJ-001 only. Each view is filtered by the project-action port. Every amount is an object `{cents, state or label, ev}` whose `ev` names an evidence entry of the same view. A missing value has no cents, never zero. Nothing is totalled (I-145). |
| `apg_ui/plain.py` | The builder's plain wording next to each code. The code itself is always kept, and an unknown code gets no wording (I-151). |
| `tools/build_m10_views.py` | Writes `ui/data/views.js` from the view model. `--check` regenerates it in memory and fails if the stored file differs by a byte. |
| `ui/` | `index.html`, `app.css`, `app.js`, the generated `data/views.js`, and IBM Plex Sans and Sans Condensed (OFL; `fonts/README.txt` gives the source and hashes). The page opens from the file system and needs no server. It loads only its own files and makes no network call. |
| `tests_m10/test_m10_viewmodel.py` | 19 tests. The stored data file equals a fresh build. Every amount names its evidence. Every project figure equals a fresh APG calculation in value, state and reasons. A figure that cannot be assessed has no value and says why. Finding amounts are the findings' own quantifications. Nothing is totalled. No amount is labelled realised. Estimated net benefits appear only when APG estimated them. Scenarios never change the forecast. The project manager sees only PRJ-001 and nothing builder-wide. One builder never sees the other. The request the screen would send is exactly the token `present()` gave. The one approval is in force. zero_two cannot be assessed through AUIF for exactly the CF-53 record types. The page code has no network call. |
| `ui_tests/run_ui_tests.js` (with `vendor/axe.min.js`, axe-core 4.10.3, MPL-2.0) | Browser tests in headless Chromium.<br>**Screens:** every screen of every view in light and dark mode, with no console error, no request leaving the machine and no axe violation (WCAG 2.0 to 2.2 A and AA tags and best practice).<br>**Amounts:** every amount is a button to its evidence; a missing value never shows a digit; no dollar amount sits outside an evidence button, except a collapsed row's summary, whose amount must also appear as a button in that row (I-150). The portfolio ledger equals the data file, rounded to the dollar, with each figure's state, and has no total.<br>**Words:** no sentence claims a saving or a realised amount.<br>**Drawer:** it opens from the keyboard, keeps focus inside, and closes on Escape with focus returned.<br>**Approvals:** each form shows exactly the token; a missing rationale is refused; submitting shows "Not sent" and the exact request.<br>**Access:** no PRJ-002 or PRJ-003 appears anywhere in the project manager's pages; zero_two shows nothing of zero_one.<br>**Data health:** zero_two's connected route says "Cannot assess", with its eight SOURCE_EMPTY reasons.<br>**Materials:** says scenarios are not recommendations, and shows the excluded concrete quote with its reason.<br>**Layout and keyboard:** no sideways scroll at 390 px; the skip link moves to the screen without changing the route. |
| `tools/sabotage_m10.py` | 19 seeded breakages (V01 to V08 in the view model and data file, U01 to U11 in the screens), each on a private copy, with a control run first. |
| `tools/run_regression_m10.py` | R01 to R08 against APG-M8.1-R1. |
| `tools/make_m10_registers.py` | SR-128; I-145 to I-151 (retained for review); CF-56 (the audit of APG-M10) and CF-57 (the product decisions the prototype leaves open), both open; the M10 milestone row's status. |
| `regression/m10/`, `logs/m10/` | The M8.1-R1 file hashes, the four tables and three list files before M10; the run logs; the screenshots (`logs/m10/screens/`). |

## 3. What changed in existing files

| File | Change |
|---|---|
| `README.md`, `RUN_COMMANDS.txt` | An M10 section on top. |
| `programme/STATUS_REGISTER.csv`, `INTERPRETATIONS_REGISTER.csv`, `CARRIED_FORWARD_REGISTER.csv` | Rows appended (SR-128; I-145 to I-151; CF-56, CF-57). No existing row changed. |
| `programme/PROGRAMME_MILESTONES.csv` | The M10 row's status only: "In this delivery (prototype over synthetic data, builder-tested; not independently reviewed)". |
| `tools/run_regression_m81.py`, `tools/run_regression_m8.py`, `tests_m8/test_m8_boundary.py` | M10's files are added to the M8 checks' declared-file lists, as APG-M8-R2 and M8.1-R1 did on the product owner's decision "Update the 2 lists". The two register replays also run M10's register step after M8.1's and expect M10's rows after M8.1's, as APG-M8.1 did for its own rows. `tools/run_regression_m10.py` R04 checks that nothing else changed in these files. |

**Release-specific checks of earlier releases.** These now report M10's changes, as such checks have done for every later release. `tools/run_regression_m81r1.py` R01 and R03 report the new files and register rows, because that check pins its own release's files. The checks the current suite runs, which are the M8.1 regression, the M8 regression and the M8 boundary tests, pass with M10 declared.

## 4. What is not done, and why

- **No live approval.** Sending an approval needs a session, an HTTP layer and the Engine's port (EDR-12, EDR-31). The prototype shows the request (I-146).
- **No total across projects** (I-145).
- **No connected-systems figures.** The figures come from the file route (I-147).
- **No responsive design system or component library.** One page, hand-built.
- **Not tested in browsers other than Chromium.** No screen-reader session with a person was run; axe-core is an automated check, not an audit by a person.

## 5. Evidence (run by the builder; logs in `logs/m10/`)

| Check | Command | Result |
|---|---|---|
| Release regression | `tools/run_regression_m10.py --all` | R01 to R08 pass on Python 3.13.16 and 3.12.3 on the final tree (`regression_m10_python3.13.log`, `regression_m10_python3.12.log`).<br>R01: only the declared files differ from APG-M8.1-R1.<br>R02: only declared files were added.<br>R03: the tables are the M8.1-R1 tables plus exactly M10's rows, and only M10's milestone status changed.<br>R04: the list files changed only to declare M10.<br>R05: the text.<br>R06: the data file equals a fresh build.<br>R07: the 19 view-model tests.<br>R08: the M8.1 regression, which reruns the M8 regression and the M8 boundary tests. |
| R03 and R04 can fail | `regression/m10/seeded_edits.py` | 5 seeded edits, each caught (`seeded_edits.log`) |
| Browser and accessibility | `node ui_tests/run_ui_tests.js --shots logs/m10/screens` | 173 checks pass, Node 22.22.0 with Playwright 1.56.0 and its Chromium (`ui_tests.log`). Screenshots: `logs/m10/screens/`, 29 images. |
| Sabotage | `tools/sabotage_m10.py` | 19 seeded breakages, each caught, with a control first (`sabotage.log`) |
| M8 tests | `tools/run_m8_tests.py` | 172 tests in 15 files pass on Python 3.13.16 and 3.12.3, with AUIF rev14 unchanged (`m8_tests_python3.13.log`, `m8_tests_python3.12.log`) |
| All groups | `tools/run_m8_all.py --range 1-150` | 150 groups pass on Python 3.13.16 (`groups_python3.13.log`). They include the 2,583 existing APG tests, the M3 import tests, the M8 tests and the regression steps. Python 3.12 was not run for the groups. |

## 6. First passes and corrections (kept in `logs/m10/first_pass/`)

- **The sabotage run exposed three weak checks before the final runs.** The fixes were made before any log here was written:
  - **A total row was missed.** The ledger check looked for the word "total", and a seeded total row sat next to the digit "5", so the word boundary failed. The check now counts the ledger's rows and columns and looks for any cell that begins with "total".
  - **Plain-text amounts were missed.** The amount check looked only at evidence buttons, so an amount drawn as plain text slipped through. It now looks at every cell, list item and paragraph, with the buttons removed.
  - **The hand-edited data file case did not apply.** The text it edited occurs four times in the data file, so the case was rewritten to edit a unique line. U11 was added as a new case.
- **A seeded edit was badly designed.** One of the seeded edits for R04 first removed an entry M10 itself added, which R04 does not police (the M8.1 regression's R02 does). It now removes a pre-existing entry and is caught.
- **The first full evidence run failed R08 of `tools/run_regression_m10.py` on both Python versions, and failed group 140.** The cause is the M8 regression's R05, which requires `README.md` to start with the M8 section; M10's section now sits on top. That check now skips M10's section and reads the readme from M8.1-R1's section on, exactly as before M10. The change is in `tools/run_regression_m8.py`, and R04 checks it. The failed logs are kept (`first_pass/regression_m10_python3.13.log`, `first_pass/regression_m10_python3.12.log`, `first_pass/groups_python3.13.log`). Every check was then rerun on the final tree.
- **A screenshot showed wrong wording, fixed after the rerun.** On the screenshot of Builder Zero Two's portfolio, "No findings are visible to this person" appeared although one finding is visible; it is not a financial exposure. The wording was corrected in `ui/app.js`. The browser tests, the sabotage run and the regression were then rerun, and the regression was run once more after this record was finished. The earlier browser and sabotage logs, both passing, are kept as `first_pass/ui_tests_before_wording_fix.log` and `first_pass/sabotage_before_wording_fix.log`.

## 7. What these results do not show

- They are builder evidence, not an independent review (CF-56).
- The accessibility result is axe-core's automated rules in one browser. It is not an audit by a person or a screen-reader session.
- The data and the demonstration state are synthetic and scripted (I-149).
- No estimate here is a realised saving, and the prototype sends nothing.
