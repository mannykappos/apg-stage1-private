# Change record APG-M8.1-R1: records only, the auditor's result for APG-M8.1

| Field | Value |
|---|---|
| Release | APG-M8.1-R1, a separately versioned, records-only release. It is the delivered APG-M8.1 package plus the changes below. The APG-M8.1 package is ZIP SHA-256 `60d4a47318782cdab2f59d54696c1cd493a365ce261ae269bdde52e41c9e2251`, 1,368 files, with every file hash in `regression/m81r1/M81_MANIFEST.sha256`. The APG-M8.1 ZIP and every earlier ZIP are not modified or replaced. |
| Status | **Builder-made, records only; not accepted.** No independent review of this records release has taken place. |
| Authority | The product owner, 2026-10-21: "Authorise the records-only release for the M8.1 audit result". The auditor's final verdict on APG-M8.1 was relayed the same day. The declared-file lists are extended as APG-M8-R2 did on the product owner's decision ("Update the 2 lists"). Since APG-M8.1 the same lists are held in three files, because `tools/run_regression_m81.py` is the one declaration of M8.1's files and `tools/run_regression_m8.py` reads it. |
| What changed | **Records:** one row (AD-21) appended to `programme/AUDIT_DISPOSITION_REGISTER.csv`. In `programme/PROGRAMME_MILESTONES.csv`, the status cell of the M8 row changed from "Not started", as M7 and M9.1 did for their own rows. **Text:** an M8.1-R1 section on top of `README.md` and `RUN_COMMANDS.txt`. **Lists:** this release's files and the two tables added to the declared-file lists of `tools/run_regression_m81.py` (a separate `M81R1_*` declaration, read by its R01 and R02), `tools/run_regression_m8.py` (R01, R02 and R10) and `tests_m8/test_m8_boundary.py`. No application code, test logic, data or specification changed. |
| Added | `tools/make_m81r1_registers.py` (writes the row and the status), `tools/run_regression_m81r1.py` (checks this release), this record, `regression/m81r1/` (the M8.1 file hashes, the two tables before R1, the three list files before R1, and the seeded-edit script), `logs/m81r1/`. |

## 1. The disposition (as the auditor reported it; full text in the register)

| ID | Covers | Release audited | Disposition | Not independently verified |
|---|---|---|---|---|
| AD-21 | SR-127 (the APG-M8.1 release; not a finding). The audit is carried forward as CF-54, the end of DEV-M8-01 as CF-55. | APG-M8.1 | Scoped audit passed. No defect was found in the audited APG-M8.1 scope, and "no correction build is indicated by the results". Qualified. | (1) Python 3.12: unavailable to the auditor, so the builder's Python 3.12 results remain builder evidence. (2) The real-Governor extension tests were not rerun against the exact real-Governor ZIP; this is inherited from the AUIF rev14 audit (AD-15 to AD-20). |

**What the auditor reproduced:**
- the ZIP hash, its integrity and the 1,368 files;
- the 172 M8 tests and the 11 path-equivalence tests, all passing;
- the M8 regression and boundary checks;
- the nine M8.1 regression steps;
- the 17 sabotage cases, all caught;
- all 150 groups on Python 3.13.5, including the 2,583 existing APG tests;
- the 82 mutants: 79 killed, 3 documented equivalent (MD-02, MI-36, MI-39), 0 survived, 0 timed out, with the control run first. MI-43 to MI-52 and the previously escaping MC-03 were killed.

The AUIF rev14 dependency was unchanged during verification.

The AD-21 row also records what the auditor said the audit establishes and what it does not mean. The CF-54 and CF-55 rows are not edited (append-only); AD-21 records the outcome of CF-54.

## 2. The milestone row

M8's status now reads: "Delivered - builder-checked, in APG-M8, M8-R1, M8-R2 (records) and M8.1 (on AUIF rev14). APG-M8.1 passed its scoped independent audit, qualified (AD-21). Not accepted as a release; Builder Zero tenant zero_two cannot be assessed through AUIF until the product owner decides CF-53".

No other cell of the table changed. Its handoff entries (EDR-05; EDR-06) are unchanged, and M10 to M12 still say "Not started".

## 3. What stays open

- **CF-53:** which record types may validly be empty. This is the product owner's decision. The auditor approved no empty record type, so Builder Zero tenant zero_two still cannot be assessed through AUIF under the current strict rule.
- **CF-52:** the M3 path's handling of a header-only file. It has not been examined.
- **The AUIF rev14 qualifications** (AD-15 to AD-20) still stand.
- **Every other open item:** EDR-05, EDR-06, EDR-18, EDR-39, EDR-40, EDR-41 and every other open EDR and CF item stay open. CF-41 stands. The construction definitions are PROPOSED. The Engine handoff register and the findings, status, interpretations and carried-forward registers are unchanged.

This is a pass for the audited scope only. It is not acceptance of the APG programme, not production readiness, and not Engine or Governor integration.

## 4. Evidence (run by the builder; logs in `logs/m81r1/`)

| Check | Command | Result |
|---|---|---|
| Baseline | `tools/run_regression_m81.py --all` on a fresh extraction of the delivered APG-M8.1 ZIP, before any change | R01 to R09 pass (`baseline_regression_m81_on_delivered.log`) |
| Release regression | `tools/run_regression_m81r1.py --all` | R01 to R07 pass on Python 3.13.16 and 3.12.3 (`regression_m81r1_python3.13.log`, `regression_m81r1_python3.12.log`).<br>R01: only the declared files differ from APG-M8.1.<br>R02: only the declared files were added.<br>R03: the register is the M8.1 register plus exactly AD-21, and in the milestones table only M8's status changed.<br>R04: the three list files gained only M8.1-R1's own files and the two tables, and lost no entry.<br>R05: the text states what it must and makes no claim it must not.<br>R06: the configuration is unchanged.<br>R07: the M8.1 regression R01 to R09 still passes. Its R08 reruns the M8 regression R01 to R10, and its R09 the M8 boundary tests. |
| R03 and R04 can fail | five seeded edits, each on its own private copy (`regression/m81r1/seeded_edits.py`; `seeded_edits.log`) | each caught: an extra list entry, a removed list entry, a code change outside the lists, a second milestone cell changed, an existing disposition row edited |
| All M8 tests | `tools/run_m8_tests.py` | 172 tests in 15 files, every file at its expected count, AUIF rev14 verified before and after, on Python 3.13.16 and 3.12.3 (`m8_tests_python3.13.log`, `m8_tests_python3.12.log`) |

**First pass (kept, `logs/m81r1/first_pass/`).** On the first full run, R05 failed on both Python versions. The M8 milestone status ended with "until" followed by CF-53 and the passive verb "decided". This release's own claim check reads that phrase as a claim that the gate is closed. The text was not such a claim, but the check is kept as strict as it is. The words were changed to "until the product owner decides CF-53", in the register step (`tools/make_m81r1_registers.py`), the milestones table it regenerates, and this record. The first-pass M8 test runs passed, and they are kept with the failed runs.

The second full run failed R05 again, on both versions, because this note quoted the old phrase word for word. The note was reworded, those two logs are kept as `first_pass/second_run_regression_m81r1_python3.13.log` and `first_pass/second_run_regression_m81r1_python3.12.log`, and every check above was rerun on the final tree.

Nothing else was rerun. No application code, test logic or data changed, so the APG-M8.1 mutation, sabotage and group results stand as they were audited (AD-21).
