# Change record APG-F67: correction of finding F-67 (approval provenance for the financial, detection and procurement policies and the specification register)

| Field | Value |
|---|---|
| Release | APG-F67, a separately versioned, additive correction release. It is the delivered MIE-1.1-R1 package (ZIP SHA-256 `6afe8b6116cc46cd1db3161a80bc91bf4bb97b847fcdfa1fa4c2967bf17f1185`, 1,049 files; every file hash in `regression/f67/R1_MANIFEST.sha256`) plus the changes below. The delivered MIE-1.1-R1 ZIP and documents, and every earlier ZIP, are not modified or replaced. |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** F-67 stays open until the independent auditor verifies the correction. Nothing here is accepted or approved, and nothing is for use outside tests. |
| Authority | The sequence agreed by the product owner, the auditor and the builder: after the MIE-1.1 mutation audit and the records update R1, the "F-67 correction release", reusing the M7.1 (F-66) pattern, with regression tests for the detection, financial and procurement policies covering forged, missing and invalid approval evidence; the R1 ZIP preserved. The audit of R1 recommended proceeding to F-67 and said the product owner should authorise "F-67 correction release" explicitly. **The builder started F-67 when the product owner relayed the R1 audit, as the builder's earlier message had said it would ("F-67 starts as soon as you pass on those results"), and treated that relay as the authorisation. The product owner should confirm this, or say otherwise.** |
| Not started | M8. It needs its own authorisation, after the audit of this release, and is not run in parallel (CF-40). |
| Gates still open | M7.3 final release acceptance, EDR-36 and the M9.4 comparison (CF-36); BLK-01 to BLK-03 (CF-37); the development deviation DEV-MIE-01 (CF-38); the MIE-1 audit runs not completed (CF-39, except the mutation run now recorded in AD-03); EDR-34, EDR-37, EDR-38 and the new EDR-39; the audit of this release (CF-40). |

## 1. The finding and what changed

F-67 (builder, recorded in M7.1 as the same-class sweep of F-66): `fin/policy.approve`, `det/policy.approve` and `mkt/policy.approve` (used for both the procurement policy and the specification register) took the approver, role and kind as plain arguments, `store_policy` / `store_spec` accepted any approvals a record carried, and a calculation, detection or procurement run counted an approval on its fields alone. A caller could therefore have any person recorded as the approving owner.

`tools/probe_f67.py` reproduces it on the delivered MIE-1.1-R1 code in four ways for each of the four records: (A) store a version that already carries a caller-written approval; (B) store the proposal, then store it again with an approval appended; (C) write the record straight into the store; (D) name somebody else as the proposer so that the person storing it appears as an independent approver. On R1 all 16 cases are counted as approved, and the control (an approval through the corrected path) cannot run: 17 of 17 DEFECT PRESENT. Here: 0 of 17.

What changed (the M7.1 pattern for F-66, in one shared module):

| Part | Change |
|---|---|
| `apg/policy_approval.py` (new) | `store`: a version is proposed by the person storing it. The actor must be a person, the proposer named in the record must be that person, and the record must arrive without approvals; otherwise it is refused, with a `<kind>.refused` audit event. Storing the same content again, or the bare proposal of an approved version, is a no-op; any other content under an existing version is refused. `approve`: the only way an approval is recorded. The approver must be a person holding the record's owner role, must not be the proposer, and must not have approved that version already, and must give a rationale. The approval is appended as a new revision and the event `<kind>.approved` is written under the approver's own context. `confirmed`: the people whose approval the tenant's audit log confirms. `counted`: an approval counts only if it is by a person with the role, not the proposer, and confirmed. |
| `apg/fin/policy.py`, `apg/det/policy.py`, `apg/mkt/policy.py` | `approve()` is removed. New `approve_policy(scoped, clock, version, rationale)` (and `approve_spec` for the specification register). `store_policy` / `store_spec` go through `policy_approval.store`. `new_policy` / `new_spec` refuse an `approvals` argument. `is_approved`, `view` and `spec_view` take the confirmed approvers. |
| `apg/fin/gather.py`, `apg/det/gather.py`, `apg/mkt/gather.py` | Every run pins `approvals_confirmed` (the confirmed approvers of every policy record it pins) in its parameters, so a replay gives the same answer without reading the log. |
| `apg/fin/snap.py`, `apg/det/common.py`, `apg/mkt/common.py` | The loaders count only the approvals the run pinned. |
| Demonstrations, goldens and corpora (`demo_fin`, `demo_det`, `demo_mkt`, `golden_fin`, `golden_det`, `golden_mkt`, `golden_rec`, `corpus_fin`, `corpus_det`) | The demonstration policies are proposals. A synthetic owner (`synthetic.policy_owner`, holding the four owner roles) approves them in person from their own session through `install` / `install_det` / `install_mkt` / `install_spec`. An approved policy now has two revisions (the proposal and the approval). **The golden outputs are unchanged** (`tools/run_golden_fin.py`, `run_golden_det.py`, `run_golden_mkt.py`, `tests/test_rec_golden.py`, `tools/run_golden_mie1.py`). |

The limit that remains is I-128, and closing it is the Engine's job (EDR-39). The reference audit events carry no roles, and APG cannot stop code outside these functions from writing the store or the audit log. A person without the owner role could write both of these directly: a record with an approval in their own name, and a matching `<kind>.approved` event under their own context. That approval would be counted. The tests do not cement this; they document it.

## 2. Tests

- **New: `tests/test_f67_policy_approval.py`, 12 tests, each over all four records.**
  - Forged approvals are refused and nothing is stored: cases A, B and D, a service as proposer, and an `approvals` argument to the builders.
  - A missing approval is not counted: case C, or no audit event.
  - Invalid evidence is not counted, and the audit log confirms nobody (9 cases), when the event is:
    - for another version;
    - a refusal;
    - of another record kind;
    - naming an approver who did not write it;
    - written by the person the record lists, but naming somebody else as the approver;
    - written by a service;
    - for another resource;
    - with detail naming another version;
    - with detail naming another kind.
  - The owner's approval through the corrected path is counted (control).
  - A concurrent change during an approval is refused and leaves no event.
  - Reproduction: a run pins the confirmed approvers, and a run made before the approval replays as unapproved.
  - Who may approve.
  - **On the delivered R1 code, all 12 fail (6) or error (6)** (`logs/f67/tests_on_r1.log`).
- **Edited test files (11) and helpers (3).** These are declared in `tools/run_regression_f67.py`; the R1 text of each is in `regression/f67/r1_originals/` for review by diff.
  - They set up approved policies through the owner's session instead of the removed `approve()`, and the tests that expected the old behaviour now expect the corrected behaviour.
  - `test_det_policy.py`: the test `test_a_stored_version_is_immutable_but_an_approval_can_be_appended` is renamed `..._and_an_approval_is_added_only_by_approve_policy`, because the old name described the defect.
  - `test_mie_construction.py` FL-10 no longer lists `apg/mkt/policy.py` among the files that must be unchanged.
  - No test is removed or added in an edited file (regression step R10).

## 3. Evidence (run fresh by the build; logs in `logs/f67/`)

| Check | Command | Result |
|---|---|---|
| Probe | `tools/probe_f67.py` | 17 cases, 0 defects present; F-67 IS CORRECTED (on R1: 17 of 17 present, `logs/f67/probe_on_r1.log`) |
| Whole unit suite | `tools/run_f67_all.py --range 10-21` | 2,540 tests in 12 counted parts (the 2,528 of MIE-1.1-R1 and the 12 F-67 tests), 0 failures, 0 errors |
| Regression against R1 | `tools/run_regression_f67.py --all` | 11 checks (R01 to R11), 0 failed |
| Earlier probes, goldens, contracts | `tools/run_f67_all.py --range 1-9` | 9 groups passed: the static regression, the F-67 probe and tests, the M7, M7.1, M7.2 and MIE-1 probes, the five golden runs unchanged, the M2 contracts and faults, the guard contract, the mutation baseline |
| Mutation | `tools/f67_mutants.py --jobs 2` | 55 mutants (the whole of `policy_approval.py` and the changed functions of the three policy modules), 55 killed, 0 equivalents, 0 survivors. The first run left two survivors, PA-RSE-007 (the refusal of an approval that meets a concurrent change) and MP-RSE-003 (the builder test raised for another reason). Both were test gaps and are closed by tests in the new file (`logs/f67/f67_mutants_first_run.log`). |
| Sabotage | `tools/sabotage_f67.py` | 27 cases, 27 caught. The first run missed 3 (`logs/f67/sabotage_f67_first_run.log`). S01 and S04 (storing accepts caller approvals) were aimed at the probe, which stays green because an unconfirmed approval is still not counted; they are now aimed at R07, whose tests assert the refusal itself. S07 (the confirmation no longer checks that the approver wrote the event) was a test gap: the evidence tests now also assert that the log confirms nobody, with a case where the writer is the person the record lists. |

## 4. Records (append-only; `tools/make_f67_registers.py`)

| Row | What |
|---|---|
| SR-111, SR-112 | The correction, and its mutation and sabotage runs: Local-tested |
| I-128 | What counts as an approval now, and the limit above |
| I-129 | How the correction is recorded: the F-67 findings row is not edited (it still reads "Open - not corrected", its M7.1 text). The correction is recorded in SR-111 and in this record, and F-67 stays open until verified |
| EDR-39 | The Engine restricts writes of the four policy kinds and their approval events, and audit events carry roles (extends EDR-34) |
| CF-40 | The audit of this release is outstanding; M8 is not started |
| AD-03 | The auditor's completed MIE-1.1 mutation audit, relayed with the audit of R1: 624 mutants, 621 killed, 3 documented equivalents, 0 survivors, with the auditor's qualification that it was run by slices with a 30-second per-mutant timeout instead of the tool's 300 seconds, so it is not an identical rerun under the original timeout setting |

## 5. Files changed and added (compared byte for byte with the delivered MIE-1.1-R1 ZIP)

- **Existing files changed: 39.**
  - 18 application files (section 1).
  - 3 test helpers and 11 test files (section 2).
  - `README.md` and `RUN_COMMANDS.txt` (an F-67 section on top; the earlier text follows unchanged).
  - 5 programme tables, with rows appended only.
  - No specification and no existing tool is changed.
- **Files added.**
  - `apg/policy_approval.py`
  - `tests/test_f67_policy_approval.py`
  - Six tools: `probe_f67.py`, `f67_mutants.py`, `sabotage_f67.py`, `run_regression_f67.py`, `run_f67_all.py` and `make_f67_registers.py`
  - This record
  - `regression/f67/`: the R1 manifest, the R1 tables and the R1 originals
  - `logs/f67/`
- **The per-release tools of MIE-1.1-R1 and earlier describe their own release.** Run here, they report the F-67 changes as undeclared changes (for example `tools/run_regression_mie1_1r1.py` R01 and R02, and `tools/run_mie1_1_all.py` group 1), and their whole-suite counts differ by the 12 new tests. Run them on their own delivered ZIPs.
