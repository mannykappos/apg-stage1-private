# Change record APG-F67.1: correction of finding F-72 (an approval stuck after an audit-write failure), for all five policy records

| Field | Value |
|---|---|
| Release | APG-F67.1, a separately versioned, additive correction release. It is the delivered APG-F67 package (ZIP SHA-256 `17badf419b26753caaa7a20592322738d6eee9b4e1be5b940f4453629bbaa958`, 1,105 files; every file hash in `regression/f671/F67_MANIFEST.sha256`) plus the changes below. The APG-F67 ZIP and documents, and every earlier ZIP, are not modified or replaced. |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** F-72 stays open until the independent auditor verifies the correction, and F-67 stays open as before. Nothing here is accepted or approved, and nothing is for use outside tests. |
| Authority | The product owner, 2026-10-20, explicitly: "Authorise F-67.1 correction release. Cover audit-write failure recovery across all five policy records, with the identity and role safeguards, retry and double-counting tests, and smaller independently auditable test and mutation batches. Preserve the F-67 ZIP and all earlier releases unchanged. Keep F-67.1 open until independent verification. M8 is not authorised and must not start." |
| The APG-F67 start (CF-41) | The product owner decided, on the same day: "Record F-67 as started without explicit authorisation; do not retroactively ratify it." This is recorded as CF-41. APG-F67 was started without explicit authorisation, the builder disclosed it, the APG-F67 ZIP stays unchanged, and APG-F67 stays unaccepted until independent verification (CF-40). It is not ratified, and the APG-F67 change record is not edited: it still contains the builder's request for confirmation, which this decision answers. |
| Not authorised | M8. |
| Gates still open | M7.3 final release acceptance, EDR-36 and M9.4 (CF-36); BLK-01 to BLK-03 (CF-37); DEV-MIE-01 (CF-38); CF-39; the audit of APG-F67 (CF-40); the audit of this release (CF-42); EDR-34 and EDR-36 to EDR-40. |

## 1. The finding and what changed

**F-72** (independent audit of APG-F67, reproduced by the auditor). An approval wrote the approved policy revision and then the confirming audit event. If the audit write failed in between:
- the policy listed the approval;
- the log confirmed nobody, so the approval was rightly not counted (fail-closed);
- the owner's retry was refused as "already approved".

The policy stayed unapproved with no supported way forward, and the failure surfaced as the raw audit exception. The builder found the same order in the recommendation policy (APG-M7.1, F-66), so the correction covers all five policy records: financial, detection, procurement, the specification register and recommendations.

`tools/probe_f671.py` runs unchanged on APG-F67 and here. For each record it tests four things:
- **A:** an approval while the audit write fails. It must not count, and the error must say the approval is recorded but NOT CONFIRMED.
- **B:** the owner's retry once the log works. It must complete the approval.
- **C:** another person's approval meanwhile. It must not confirm the owner's.
- **D:** the owner's retry while the log still fails. It must not count.

On APG-F67 there are 10 defects (A and B for every record); here there are 0, and the control passes.

| Part | Change |
|---|---|
| `apg/policy_approval.py` | **`approve`:** the confirming event is written by `_confirm`. If that write fails, `approve` raises `ApprovalNotConfirmed`. That error is also the record's own error class, so existing callers still catch it, and it says the approval is recorded in the policy but NOT CONFIRMED by the audit log and does not count. If the log, read back, shows the event was in fact written, the approval is reported as confirmed and nothing is repeated; a read-back that fails counts as not confirmed. **Completion:** when the policy already lists the caller's approval and the log does not confirm it, `approve` from that same person writes only the missing confirming event, under their own context, and changes no record. All the usual checks still apply: a person, holding the role, not the proposer. An entry in their name that `approve` did not write (another role or kind) is refused. If the log already confirms them, the call is refused as "already approved". **`status`:** per version, what is recorded, what is confirmed, and what is recorded but not confirmed. |
| `apg/rec/policy.py` | The same for the recommendation policy, with its own event `rec.policy_approved`. New `approval_status`. |
| `apg/fin/policy.py`, `apg/det/policy.py`, `apg/mkt/policy.py` | New `approval_status` (and `spec_approval_status`), wrappers of `status`. |

**What does not change:**
- An approval counts only when the policy lists it and the log confirms it (I-128).
- A run pins the confirmations, so a run made while an approval was unconfirmed stays unapproved on replay.
- Nobody but the listed approver can complete their approval: the event is always written under the caller's own context and names the caller.

**Atomicity** (the record and its event written together) is a property of the Engine's store and audit log. It is requested as EDR-40, alongside EDR-39. APG does not claim it.

## 2. Tests

**New file: `tests/test_f671_approval_recovery.py`, 11 tests, each over all five records.**

The tests check that:
- an audit failure leaves the approval recorded, not confirmed and not counted, with a clear error and status;
- the same approver completes it by retrying, the record is unchanged, exactly one event is written, and the approval is then counted;
- a retry while the log still fails is not counted;
- when the log cannot be read back either, the approval is not confirmed;
- a write that lands but raises is confirmed and not repeated;
- another person with the role adds and confirms only their own approval;
- the approver without the role, as a service or as an AI, cannot complete it;
- an entry in the approver's name that `approve` did not write cannot be completed;
- after recovery the approver is listed once and confirmed once, and cannot approve again;
- a run made before the recovery stays unapproved and replays so;
- `status` reports a proposal and a missing version correctly.

**On the delivered APG-F67 code, all 11 fail (1) or error (10)** (`logs/f671/tests_on_f67.log`).

No existing test file is changed (regression step R10).

## 3. Independently auditable runs

The auditor of APG-F67 could not complete the whole suite or all the mutants within the execution limits. This release adds three things:
- **`tools/run_f671_all.py`:** the whole suite in small groups, each with its test count, and a group that checks the groups cover every test file exactly once. It runs through the new `tools/run_test_files.py`. The whole suite remains one command: `tools/run_m2_tests.py -q`.
- **`tools/f671_mutants.py`:** the mutation run in fixed batches (`--batch K/N`), with a configurable per-mutant timeout (`--timeout 30`).
- **`tools/sabotage_f671.py`:** sabotage cases that run one at a time (`--only Sxx`).

## 4. Evidence (run fresh by the build; logs in `logs/f671/`)

| Check | Command | Result |
|---|---|---|
| Probe | `tools/probe_f671.py` | 21 cases, 0 defects present; F-72 IS CORRECTED (on APG-F67: 10 present, `probe_on_f67.log`) |
| New tests on APG-F67 | copied into a clean APG-F67 extraction | 11 tests: 1 fails, 10 error (`tests_on_f67.log`) |
| Groups 1 to 23 | `tools/run_f671_all.py --range 1-23` | 23 groups passed. These include the static regression, the probe, the 11 tests, the F-67 probe and tests, the M7 probe, the golden runs unchanged, the contracts, faults and guard contract, the mutation baseline and the coverage check. The whole suite is 2,551 tests in 13 counted parts (the 2,540 of APG-F67 and the 11 new tests), 0 failures |
| Regression against APG-F67 | `tools/run_regression_f671.py --all` | 11 checks (R01 to R11), 0 failed |
| Mutation | `tools/f671_mutants.py --batch K/6 --jobs 2 --timeout 30` | 88 mutants in six batches (15, 15, 15, 15, 15, 13), each under 15 seconds: 88 killed, 0 equivalents, 0 survivors |
| Sabotage | `tools/sabotage_f671.py` | 23 cases, 23 caught |

## 5. Records (append-only; `tools/make_f671_registers.py`)

| Row | What |
|---|---|
| F-72 | The finding; corrected here, open until independently verified |
| SR-113, SR-114 | The correction; the auditable groups, batches and sabotage; Local-tested |
| I-130 | The completion rule |
| EDR-40 | The record and its approval event written atomically |
| CF-41 | APG-F67 was started without explicit authorisation and is not ratified (product owner decision, 2026-10-20) |
| CF-42 | The audit of this release is outstanding; M8 is not authorised |

## 6. Files changed and added (compared byte for byte with the delivered APG-F67 ZIP)

- **Existing files changed: 12.**
  - 5 application files (section 1).
  - `README.md` and `RUN_COMMANDS.txt` (an F-67.1 section on top; the earlier text follows unchanged).
  - 5 programme tables, with rows appended only.
  - No existing test, tool or specification changed.
- **Files added.**
  - `tests/test_f671_approval_recovery.py`
  - Seven tools: `probe_f671.py`, `f671_mutants.py`, `sabotage_f671.py`, `run_regression_f671.py`, `run_f671_all.py`, `run_test_files.py` and `make_f671_registers.py`
  - This record
  - `regression/f671/`: the F67 manifest, the F67 tables and the F67 originals of the changed code
  - `logs/f671/`
- **The per-release tools of APG-F67 and earlier describe their own release.** Run here, they report the F-67.1 changes as undeclared, and their whole-suite counts differ by the 11 new tests. Run them on their own delivered ZIPs.
