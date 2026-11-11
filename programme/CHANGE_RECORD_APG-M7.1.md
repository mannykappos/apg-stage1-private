# Change record APG-M7.1: correction of the recommendation lifecycle and the policy approval after the independent audit of APG-M7 (F-64, F-65, F-66)

| Field | Value |
|---|---|
| Release | APG-M7.1, a separately versioned, additive correction release: the delivered M7 package (ZIP SHA-256 `a58b2294a95cb8901dec0154b41e89bd2e987c7eb461672b5e6cf175fba0f934`) plus the correction below. The delivered M7 ZIP and documents are not modified or replaced. |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** F-64 to F-66 stay open until the auditor verifies them. F-67 (the same class in the M5 and M6 policies) is recorded and NOT corrected. |
| Authority | The auditor's verdict on M7, relayed by the product owner on Mon 2026-10-19. The verdict: M7 is NOT ACCEPTED; send the findings back for a targeted correction release, not another specification package. |
| Not touched | No M2 to M6 file and no M9 file. Of apg/rec, `inputs.py`, `verify.py` and `__init__.py` are unchanged. Engine #17 and RFC-01 are unchanged (RFC-01 is still PROPOSED and unnumbered). |

## 1. The findings and what changed

| ID | What was wrong in M7 | What changed | Tests (20 of the 23 fail or error on the M7 code) |
|---|---|---|---|
| F-64 | A recommendation is a snapshot of a run. Submission and approval checked only the snapshot, so a recommendation stayed submittable after its finding was dismissed or its mandatory review was changed to not cleared, until someone reran the engine | `lifecycle.source_check` runs at submission, approval and start. Exact revisions of the finding, its overlapping findings, its inputs and its policy must match the run's pins, and an in-memory recomputation must give the same digest. Otherwise the act is refused (`SOURCE_CHANGED`) | `TestStaleAtSubmission`: ten kinds of change, the refusal text, a fresh run, a new overlapping finding, a change elsewhere, a check that cannot complete. `TestStaleBetweenSubmissionAndApproval` |
| F-65 | After a valid approval, the start of work was accepted although the finding had since been dismissed | The start of work is source-checked too | `TestStaleBetweenApprovalAndStart` |
| F-66 | `policy.approve()` built an approval from caller-supplied approver, role and kind, and `store_policy` accepted it | `approve()` is removed. `store_policy` accepts only proposals stored by their proposer with no approvals. `approve_policy` approves from the approver's verified context and writes an audit event. A run counts only audit-confirmed approvals, recorded in its parameters. Under an unapproved policy, nothing can be submitted | `TestPolicyApprovalBoundary` |

**Same-class sweep.**

- **Other consequential acts.** The sweep covered every consequential act in apg/rec:
  - completion and verification take their actor from the context;
  - the inputs, reviews and evidence assessments take their author from the context;
  - completion and verification are deliberately not source-checked (I-111).
- **Other policy modules.** The sweep also looked outside apg/rec. The detection, financial and procurement policies have the same caller-supplied `approve()` (F-67). They are not changed here, because this release changes no M2 to M6 file; F-67 needs its own correction.

## 2. Files changed and added (compared byte for byte with the delivered M7 ZIP)

**Changed (19)**

- **Application.** `apg/rec/policy.py`, `engine.py`, `lifecycle.py`, `demo_rec.py` (the demonstration policy is returned unapproved) and `golden_rec.py` (the golden run approves through `approve_policy`).
- **Tests.**
  - `tests/helpers_rec.py`: test worlds propose and approve policies through the boundary.
  - `tests/test_rec_policy.py`, `tests/test_rec_edges.py`: the three tests that called the removed `approve()` now use the boundary, or build the approval shape directly to test `is_approved`.
  - `tests/test_rec_repro.py`: the policy's pinned revision is now the approval's revision.
- **Regression data.** `regression/m7/golden_rec.json`: the only difference is the new field `approvers_confirmed_by_audit`.
- **Tools.** `tools/m7_mutants.py`: it runs the correction tests, and the documented equivalents are re-checked against the new site numbering.
- **Records and documents.**
  - `README.md` and `RUN_COMMANDS.txt`: an M7.1 section above the M7 text.
  - `programme/RECOMMENDATION_ENGINE.md`: sections 2a and 8a, and the gate list.
  - Five programme tables with rows appended: findings F-64 to F-67, status SR-98 to SR-100, interpretations I-110 to I-113, Engine handoff EDR-34 and carried-forward CF-33.

**Added**

- **Tests.** `tests/test_rec_m71_corrections.py` (23 tests).
- **Tools.** `probe_m7_audit_findings.py` prints DEFECT PRESENT on M7 and THE AUDIT FINDINGS ARE CORRECTED here. Also added: `run_regression_m71.py`, `run_m71_all.py` (the whole suite in ten counted parts), `sabotage_m71.py` and `make_m71_registers.py`.
- **Regression data and logs.** `regression/m71/`: the M7 manifest and the M7 table snapshot. `logs/m71/` holds the builder's runs.
- **Documents.** This record.

## 3. What the auditor could not complete (CF-33)

The whole suite, the sabotage suite and the mutation suite did not complete in the audit environment. These are incomplete, not passes. M7.1 splits each of them:

- `tools/run_m71_all.py --group N`: the whole suite in ten parts that add up to 2,254 tests. No part takes more than about a minute.
- `tools/sabotage_m71.py --only Sxx`: one sabotage case at a time.
- `tools/m7_mutants.py --only EN-CMP` and so on: the mutation run by module and kind.

The delivered M9.4 and M7 ZIPs can be supplied to the auditor, so that the stored manifests are compared with the real archives.
