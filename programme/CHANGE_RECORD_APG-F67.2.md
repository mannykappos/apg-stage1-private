# Change record APG-F67.2: correction of finding F-73 (a planted approval entry with the correct role was completed), for all five policy records

| Field | Value |
|---|---|
| Release | APG-F67.2, a separately versioned, additive correction release. It is the delivered APG-F67.1 package (ZIP SHA-256 `e815ca3dd2f66808b9e14dc97cd13aae656f10997029b1b17a15cb9bbcfe0884`, 1,132 files; every file hash in `regression/f672/F671_MANIFEST.sha256`) plus the changes below. The APG-F67.1 ZIP and documents, and every earlier ZIP, are not modified or replaced. |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** F-73 and F-72 stay open until the independent auditor verifies them, and F-67 stays open as before. Nothing here is accepted or approved, and nothing is for use outside tests. |
| Authority | The product owner, 2026-10-20, explicitly: "Authorise F-67.2 correction release: replace, never complete, an unconfirmed approval entry in the approver's name; bind each confirmation to the revision the approval function wrote; per-record tests for a forged matching-role entry; rerun the recovery, mutation and sabotage checks in small batches. Preserve the F-67.1 ZIP and all earlier releases. Keep F-72 open until independent verification. M8 is not authorised." |
| Not authorised | M8. |
| Gates still open | CF-36 to CF-40, CF-42 and CF-43; EDR-34 and EDR-36 to EDR-40. CF-41 (APG-F67 started without explicit authorisation, not ratified) is unchanged. |

## 1. The finding and what changed

**F-73** (independent audit of APG-F67.1, reproduced by the auditor on all five records). When the policy listed an unconfirmed entry in the caller's name, APG-F67.1 `approve` wrote only the confirming event.
- It checked the entry's role and kind, not that `approve` had written it. An entry planted directly in the store, naming the owner with the owner role and kind `human`, was therefore confirmed when the owner approved.
- The F-67.1 tests covered a planted entry only with the wrong role.
- The confirming event named no revision, so it could not show which entry it confirmed.

`tools/probe_f672.py` runs unchanged on APG-F67.1 and here. For each record it tests three things:
- **A:** a planted matching entry must not count.
- **B:** after the owner approves in person, the planted entry must be gone, and the event must name the revision that added the owner's fresh entry.
- **C:** as B, with a planted entry byte-identical to `approve`'s own.

There is also a control: an ordinary approval is counted, and its event names the revision `approve` wrote. On APG-F67.1 there are 11 defects (B and C on every record, and the control, whose event names no revision). Here there are 0.

**Why the planted entry is replaced, not refused.** `approve` cannot tell an entry it wrote from one written directly with the same fields. So it never completes an entry it finds. Refusing the entry instead would let anyone able to write the store block the named person's approval for good, which is the F-72 stuck state again (I-131).

| Part | Change |
|---|---|
| `apg/policy_approval.py` | **`approve`:** if the caller (a person holding the role, not the proposer) has an entry in their name that the log does not confirm, whoever wrote it, `approve` takes two steps. It writes a revision without that entry, then a revision with a fresh entry of its own; both are new revisions, even when the planted entry is identical. If the log confirms them already, the call is refused as "already approved". Other approvers' entries are kept. **`_confirm`:** the confirming event names the revision `approve` wrote (`revision`) and how many entries it replaced. **`confirmed` and the new `added_at`:** an event counts only if the revision it names is the one that added that person's entry, meaning that revision lists it and the revision before does not. The F-67.1 completing path is removed. |
| `apg/rec/policy.py` | The same for the recommendation policy: `approve_policy` and `_confirm`, and `verified_approvers` uses `added_at`. |

**What does not change:**
- An approval counts only when the policy lists it and the log confirms it.
- A failed confirming write raises `ApprovalNotConfirmed` and does not count; the same person approving again records and confirms a fresh approval.
- Runs pin their confirmations.
- The goldens are unchanged.

**Limit (I-131, as I-128).** The named person could still write both a record revision and a matching event directly. Restricting direct writes is the Engine's job (EDR-39), as is writing a record and its event atomically (EDR-40).

The binding reads the revision before the one an event names. It relies on the store returning None for revision 0 or any revision outside 1..n. The reference store does this, but the record-store contract does not yet test it, so an Engine store must keep it.

## 2. Tests

**New file: `tests/test_f672_forged_entry.py`, 11 tests, each over all five records.** It checks that:
- a planted matching-role entry never counts on its own;
- the named person approving replaces it, and the confirmation names the new revision;
- an identical planted entry is still replaced by a new revision;
- another person cannot turn it into the owner's approval;
- other approvers' entries are kept;
- a concurrent change between the two writes is refused and nothing counts;
- an audit failure after the replacement is reported, and a later approval records afresh;
- an event naming a revision that did not add the entry is not counted (no revision, the one before, a missing one, 0, -1, true, a text);
- an event naming a later revision that merely still lists the entry is not counted;
- `added_at` reads the revision and the one before;
- `added_at` handles a first revision that already lists the entry.

**On the delivered APG-F67.1 code, 8 of the 11 fail or error** (`logs/f672/tests_on_f671.log`). The other 3 guard properties F-67.1 already had and F-67.2 must keep: a planted entry never counts on its own; another person cannot make it the owner's; other approvers' entries are kept.

**Changed (declared): two tests in `tests/test_f671_approval_recovery.py`.** They asserted the F-67.1 behaviour that F-73 shows to be wrong:
- The retry test (renamed `test_the_same_approver_retries_and_a_fresh_approval_is_recorded_and_confirmed`) now expects a fresh entry in two new revisions, with the event naming the revision.
- The wrong-role planted-entry test (renamed `test_an_entry_in_the_approvers_name_that_approve_did_not_write_is_replaced_not_completed`) now expects replacement instead of a refusal that would have left the person unable to approve.

The F67.1 text of that file is in `regression/f672/f671_originals/`. No test is removed (regression step R10), and no other test file changed.

## 3. Independently auditable runs

- **`tools/run_f672_all.py`:** 23 short groups. Groups 11 to 23 are the whole suite in 13 counted parts; group 10 checks that the parts cover every test file exactly once.
- **`tools/f672_mutants.py --batch K/8 --timeout 30`:** 106 mutants in eight batches.
- **`tools/sabotage_f672.py --only Sxx`** and **`tools/run_regression_f672.py --step Rnn`:** one case or step at a time.

**A fault found and fixed in the mutation tooling.** Under a short `--timeout`, a mutant whose tests all pass can take longer than the timeout, and the method then counted the timeout as a kill. While the builder was building this release, that hid two survivors (PA-CMP-011, PA-CMP-012). `tools/f672_mutants.py` now reruns any mutant that times out under a short timeout with the original 300 seconds, and classifies it by that run.
- PA-CMP-011 is now killed by a new test (`added_at` for a first revision).
- PA-CMP-012 is a documented equivalent against the reference store (it reads revision 0, which the store returns as None).

The APG-F67.1 batch logs show no timeout kills, so the F-67.1 result is not affected. The F-67.1 tool itself keeps the old behaviour; its `--timeout 30` should be read with this in mind.

## 4. Evidence (run fresh by the build; logs in `logs/f672/`)

| Check | Command | Result |
|---|---|---|
| Probe | `tools/probe_f672.py` | 16 cases, 0 defects present; F-73 IS CORRECTED (on APG-F67.1: 11 present, `probe_on_f671.log`) |
| New tests on APG-F67.1 | copied into a clean APG-F67.1 extraction | 11 tests: 5 fail and 3 error; 3 pass, guarding properties F-67.1 already had (`tests_on_f671.log`) |
| Groups 1 to 23 | `tools/run_f672_all.py --range 1-23` | 23 groups passed: the static regression, the probe, the 11 tests, the F-72 and F-67 probes and tests and the M7 probe, the golden runs unchanged, the contracts, faults and guard contract, the mutation baseline, the coverage check, and the whole suite in 13 counted parts. That is 2,562 tests (the 2,551 of APG-F67.1 and the 11 new tests), 0 failures |
| Regression against APG-F67.1 | `tools/run_regression_f672.py --all` | 11 checks (R01 to R11), 0 failed |
| Mutation | `tools/f672_mutants.py --batch K/8 --jobs 2 --timeout 30` | 106 mutants in eight batches: 105 killed, 1 documented equivalent (PA-CMP-012), 0 survivors. Batch 1 takes about a minute, because the equivalent's full test list is run twice (it times out under 30 s and is rerun under 300 s); the other batches take under 15 seconds |
| Sabotage | `tools/sabotage_f672.py` | 20 cases, 20 caught |

## 5. Records (append-only; `tools/make_f672_registers.py`)

| Row | What |
|---|---|
| F-73 | The finding; corrected here, open until independently verified |
| SR-115, SR-116 | The correction; its auditable runs; Local-tested |
| I-131 | Replace, never complete; the revision binding; what it supersedes in I-130; the limit |
| CF-43 | The audit of this release is outstanding; M8 is not authorised |

## 6. Files changed and added (compared byte for byte with the delivered APG-F67.1 ZIP)

- **Existing files changed: 9.**
  - `apg/policy_approval.py` and `apg/rec/policy.py`.
  - `tests/test_f671_approval_recovery.py` (two tests).
  - `README.md` and `RUN_COMMANDS.txt` (an F-67.2 section on top; the earlier text follows unchanged).
  - 4 programme tables, with rows appended only.
- **Files added.**
  - `tests/test_f672_forged_entry.py`
  - Six tools: `probe_f672.py`, `f672_mutants.py`, `sabotage_f672.py`, `run_regression_f672.py`, `run_f672_all.py` and `make_f672_registers.py`
  - This record
  - `regression/f672/`
  - `logs/f672/`
- **Earlier per-release tools describe their own release.** The APG-F67.1 tools, run here, report the F-67.2 changes as undeclared.
