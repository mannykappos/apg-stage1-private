# Change record APG-F67.3: correction of finding F-74 and the approval-binding defect class of F-73 and F-74, for all five policy records

| Field | Value |
|---|---|
| Release | APG-F67.3, a separately versioned, additive correction release. It is the delivered APG-F67.2 package (ZIP SHA-256 `8f2cbf538cd979e102be3872d55ad5fc2dc41a20775e0b400b306ca95d32c706`, 1,155 files; every file hash in `regression/f673/F672_MANIFEST.sha256`) plus the changes below. The APG-F67.2 ZIP and documents, and every earlier ZIP, are not modified or replaced. |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** F-74, F-73, F-72 and F-67 each stay open until the independent auditor verifies it. Nothing here is accepted or approved, and nothing is for use outside tests. |
| Authority | On 2026-10-20 the product owner wrote "I authorise chatgpts authorisation", adopting the authorisation text the independent auditor recommended. That text begins: "Authorise F-67.3 correction release. Objective: Close the approval-binding defect class identified by F-73 and F-74, including approvals invalidated by later changes to approval entries or approved policy content." It goes on to set the required behaviour, the threat model, the testing and evidence, and the preservation of earlier releases, and closes: "M8 is not authorised and must not start. F-67.3 authorisation does not itself accept the release or authorise M8." |
| Not authorised | M8. |
| Gates still open | CF-36 to CF-40 and CF-42 to CF-44; EDR-34 and EDR-36 to EDR-41. CF-41 (APG-F67 started without explicit authorisation, not ratified) is unchanged. |

## 1. The finding, the threat model and what changed

**F-74** (independent audit of APG-F67.2, reproduced by the auditor on all five records). APG-F67.2 counted a confirming event when the revision it named had added the approver's entry, but did not check what happened afterwards. In the auditor's case:
- a genuine approval was made (revision 2, with an event naming revision 2);
- its entry was removed by a direct store write (revision 3);
- it was re-planted by another direct store write (revision 4);
- the old confirmation still counted.

**Same class, found by the builder:**
- an entry changed in place still counted;
- approved content rewritten with the entry kept still counted;
- content rewritten and then restored still counted;
- after a content rewrite, the owner could not approve the new content ("already approved").

**Threat model** (from the authorisation). The attacker can append arbitrary revisions of a policy record directly to the store: planting, removing, re-planting or modifying approval entries, and rewriting policy content while keeping entries. They can do this at any time between approval, confirmation and a run. The attacker cannot:
- write an audit event authenticated as another person;
- rewrite or delete a past revision or audit event;
- change what a pinned revision reads on replay.

Those store requirements are stated and tested as a contract (EDR-41), not assumed.

`tools/probe_f673.py` runs unchanged on APG-F67.2 and here. For each record, after the owner's genuine approval, it tests eight paths:
- **A:** the entry removed, then re-planted identical.
- **B:** the entry changed in place.
- **C:** the approved content rewritten, with the entry kept.
- **D:** the content rewritten, then restored.
- **E:** the same content and entry written as a new version.
- **F:** a run made before C, replayed after it.
- **G:** another person approves after the owner (this must keep the owner's approval).
- **H:** after C, the owner approves again (this must count).

There is also a control. On APG-F67.2, 25 cases are defects (A, B, C, D and H on every record). Here there are 0.

**The rule (I-132).** A confirmation counts at revision R only if all of these hold:
- it is authentic (I-128);
- it names the revision that added the approver's entry (I-131);
- in every revision from that one through R, the approver's entry is present and unchanged;
- in every revision from that one through R, the approved content (every field except the approvals) is unchanged.

R is the exact revision a run pinned (otherwise the latest). Adding other people's approvals keeps it. A broken confirmation never counts again; the owner approves afresh and is never stuck.

| Part | Change |
|---|---|
| `apg/policy_approval.py` | New `content` and `holds`. `confirmed(scoped, kind, version, at=None)` judges with `holds` at revision `at`. `confirmations` judges a pinned reference at its pinned revision. |
| `apg/rec/policy.py`, `apg/rec/engine.py` | `verified_approvers(scoped, p, at=None)` uses `holds`, and the recommendation run passes its pinned policy revision. |
| `apg/fin/gather.py`, `apg/det/gather.py`, `apg/mkt/gather.py` | They pass the pinned references, so confirmations are judged at the exact revisions the run pins. |
| `apg/contracts/record_store_history_contract.py` (new), `tools/run_history_contract.py` (new) | The record-store history contract, RH-01 to RH-06:<br>• revisions are numbered 1..n in the order written;<br>• a past revision reads back the same for ever, payload and hash;<br>• a revision outside 1..n (0, negative, beyond n, a boolean, a text or a fraction) reads as nothing;<br>• an identical write appends nothing;<br>• history and get agree, per tenant;<br>• nothing a caller does with what it reads or writes changes a stored revision.<br>The tool runs it on the reference store and shows it catches four deliberately faulty stores (EDR-41). |

**Limit:** whoever can write both the store and an audit event in the approver's name is outside APG's checks (EDR-39, EDR-40).

## 2. Tests

**New file: `tests/test_f673_approval_integrity.py`, 12 tests, each over all five records.**

Each attack path no longer counts:
- an entry removed and re-planted identical;
- an entry changed in place (date; role);
- rewritten approved content (a field; the proposer);
- content rewritten and then restored;
- a confirmation reused for a new version with the same content and entry;
- an old confirmation, after a fresh approval replaces it.

What keeps an approval:
- another person's approval keeps the existing ones;
- the owner is never stuck after a broken confirmation.

Pinned revisions:
- a run before tampering replays as approved, and a run after it is unapproved;
- confirmations are judged at the revision given, including through `confirmations` with a pinned reference;
- the recommendation policy is judged at the revision given;
- a unit test of `holds`.

**On the delivered APG-F67.2 code, 10 of the 12 fail or error** (`logs/f673/tests_on_f672.log`). The other 2 guard properties F-67.2 already had and must keep: another person's approval keeps existing ones, and a confirmation is not reused for a new version. No existing test changed (regression step R10).

## 3. Evidence (run fresh by the build; logs in `logs/f673/`)

| Check | Command | Result |
|---|---|---|
| Probe | `tools/probe_f673.py` | 41 cases, 0 defects present; F-74 IS CORRECTED (on APG-F67.2: 25 present, `probe_on_f672.log`) |
| New tests on APG-F67.2 | copied into a clean APG-F67.2 extraction | 12 tests: 10 fail or error; 2 pass, guarding properties F-67.2 already had (`tests_on_f672.log`) |
| Store history contract | `tools/run_history_contract.py` | RH-01 to RH-06 pass on the reference store; the four faulty stores are each caught |
| Groups 1 to 23 | `tools/run_f673_all.py --range 1-23` | 23 groups passed; the whole suite is 2,574 tests in 13 counted parts (the 2,562 of APG-F67.2 and the 12 new tests), 0 failures |
| Regression against APG-F67.2 | `tools/run_regression_f673.py --all` | 12 checks (R01 to R12), 0 failed |
| Mutation | `tools/f673_mutants.py --batch K/9 --jobs 2 --timeout 30` | 120 mutants in nine batches: 119 killed, 1 documented equivalent (PA-CMP-013), 0 survivors. Batch 1 takes about a minute, because the equivalent's full test list runs twice; the others take about 15 seconds or less |
| Sabotage | `tools/sabotage_f673.py` | 20 cases, 20 caught |

**One sabotage miss on the first run** (`sabotage_f673_first_run.log`). S13 makes the detection gatherer pass bare keys again. Regression step R11 only checked that the pinned form appeared somewhere in the file, which has two gatherers. R11 now requires every confirmation call to pass the pinned references. No behavioural test can separate the two forms within one gather, so this is guarded statically.

**Mutation timeouts.** A mutant that times out under a short timeout is rerun under 300 seconds before it is classified (as in APG-F67.2). A timeout is not counted as a kill.

**The documented equivalent.** PA-CMP-013 (numbered PA-CMP-012 in APG-F67.2) is equivalent for any store that meets RH-03, which the history contract now states and tests.

## 4. Records (append-only; `tools/make_f673_registers.py`)

| Row | What |
|---|---|
| F-74 | The finding and the builder-found cases of its class; corrected here, open until independently verified |
| SR-117, SR-118 | The correction; the history contract and the auditable runs; Local-tested |
| I-132 | The rule, the threat model, the store requirements, the limit |
| EDR-41 | The record-store history contract an Engine store must pass |
| CF-44 | The audit of this release is outstanding; M8 is not authorised |

## 5. Files changed and added (compared byte for byte with the delivered APG-F67.2 ZIP)

- **Existing files changed: 13.**
  - 6 application files (section 1).
  - `README.md` and `RUN_COMMANDS.txt` (an F-67.3 section on top; the earlier text follows unchanged).
  - 5 programme tables, with rows appended only.
  - No existing test, tool or specification changed.
- **Files added.**
  - `apg/contracts/record_store_history_contract.py`
  - `tests/test_f673_approval_integrity.py`
  - Seven tools: `run_history_contract.py`, `probe_f673.py`, `f673_mutants.py`, `sabotage_f673.py`, `run_regression_f673.py`, `run_f673_all.py` and `make_f673_registers.py`
  - This record
  - `regression/f673/`
  - `logs/f673/`
- **Earlier per-release tools describe their own release.** Run here, they report the F-67.3 changes as undeclared.
