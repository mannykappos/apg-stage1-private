# Change record APG-F67.4: correction of finding F-75 (a type-changing edit kept an approval), for all five policy records

| Field | Value |
|---|---|
| Release | APG-F67.4, a separately versioned, additive correction release. It is the delivered APG-F67.3 package (ZIP SHA-256 `bd58c8652c45c008d663b6b9ec6fbae3acaa77882233c54ba101549b46a5d490`, 1,186 files; every file hash in `regression/f674/F673_MANIFEST.sha256`) plus the changes below. The APG-F67.3 ZIP and documents, and every earlier ZIP, are not modified or replaced. |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** F-75, F-74, F-73, F-72 and F-67 each stay open until the independent auditor verifies it. Nothing here is accepted or approved, and nothing is for use outside tests. |
| Authority | The product owner, 2026-10-20, explicitly: "Authorise F-67.4 correction release: compare approved content and approval entries by the store's canonical, type-preserving fingerprint, and apply the same comparison to the re-store checks; per-record regression tests for type-changing edits (including bool/integer substitutions) showing the approval no longer counts and the owner can approve afresh; keep the F-73 and F-74 tests intact; add finer-grained test runs (one test file per group) for independent audit; rerun mutation, sabotage and release comparison in small batches. Preserve F-67.3 and all earlier releases. F-75, F-74, F-73, F-72 and F-67 stay open until independent verification. M8 is not authorised." |
| Not authorised | M8. |
| Gates still open | CF-36 to CF-40 and CF-42 to CF-45; EDR-34 and EDR-36 to EDR-41. CF-41 is unchanged. |

## 1. The finding and what changed

**F-75** (independent audit of APG-F67.3). APG-F67.3 compared the approved content of each revision with Python dictionary equality, under which `False == 0` and `True == 1`. The auditor reproduced it on the financial, detection and procurement policies:
- a direct write that changed an approved value's type (False to 0, 1 to True, 0 to False) appended a new revision;
- the confirmation still held, and the run still counted the approval.

The builder reproduced it on all five records, and found two more things:
- the owner could not approve the changed content afresh ("already approved");
- the same loose comparison is in the re-store checks of the shared policy store and of the recommendation policy store. There, a re-store with True for 1 was treated as the same content and nothing was written. With today's schemas the schema check refuses such content first, so this was not reachable through the normal path; it is corrected anyway.

`tools/probe_f674.py` runs unchanged on APG-F67.3 and here. It works on approved content holding a 0, a 1 or a boolean; the specification register, whose demonstration content holds none, uses a version with a conversion factor of 1, which its schema permits. For each record it tests three things:
- **A:** the value's type is changed by a direct write. The approval must stop being confirmed, and a run must not count it. The recommendation run refuses the type-changed policy outright.
- **B:** the owner approves the changed content afresh. This must be accepted.
- **C:** the version is stored again with the type-changed content. The re-store comparison itself must refuse it; the schema check is stubbed out to reach the comparison.

There is also a control. On APG-F67.3 there are 15 defects (A, B and C on every record); here there are 0.

| Part | Change |
|---|---|
| `apg/policy_approval.py` | New `fingerprint` (the store's canonical, type-preserving `canon.digest`) and `same`. `holds` compares the approved content and the approver's entries by fingerprint. Content that cannot be fingerprinted never holds. The re-store check in `store` compares by fingerprint. |
| `apg/rec/policy.py` | `store_policy`'s re-store check compares by fingerprint. |

**How the fingerprint treats differences:**
- the order of a record's keys alone is not a change, and the store appends nothing for it;
- a list in another order is a change;
- True and 1, False and 0, and 1 and "1" are all different (I-133).

## 2. Tests

**New file: `tests/test_f674_type_strict.py`, 9 tests over the five records.** They check that:
- a type-changing edit breaks the approval (where the run still runs it reports unapproved; the recommendation run refuses the content);
- the owner can approve the changed content afresh;
- every type change breaks it at the `holds` level: True for 1, 1 for True, False for 0, 0 for False, "1" for 1, and the same inside a list or a nested record;
- a change of key order alone is not a change;
- content that cannot be fingerprinted never holds;
- a type-changed re-store is refused as different content (the comparison itself);
- the same content stored again is still a no-op;
- the `same` function behaves as above;
- a run before the type change replays as approved.

**On the delivered APG-F67.3 code, 7 of the 9 fail or error** (`logs/f674/tests_on_f673.log`). The other 2 guard behaviour F-67.3 already had and must keep: key order is not a change, and an identical re-store is a no-op.

**The F-73 and F-74 tests are unchanged**, and so is every other test (regression step R10).

## 3. Finer-grained runs for the independent audit

The auditor of APG-F67.3 could not complete group 4, even alone. `tools/run_f674_all.py` now also runs **one test file per group**:
- `--files-list` lists the 117 files with their test counts;
- `--file N` runs one file;
- `--files A-B` runs a range of files.

The counts add up to the whole suite (2,583 tests), and group 10 (regression step R13) checks that both the groups and the per-file list cover every test file exactly once. The slowest single file (`test_mie_construction.py`) takes about 23 seconds on the build machine. A single class or test can also be run, from the package folder and without `-I`: `python3 -B -m unittest tests.<file>.<Class>[.<test>]`.

## 4. Evidence (run fresh by the build; logs in `logs/f674/`)

| Check | Command | Result |
|---|---|---|
| Probe | `tools/probe_f674.py` | 16 cases, 0 defects present; F-75 IS CORRECTED (on APG-F67.3: 15 present, `probe_on_f673.log`) |
| New tests on APG-F67.3 | copied into a clean APG-F67.3 extraction | 9 tests: 7 fail or error; 2 pass, guarding behaviour F-67.3 already had (`tests_on_f673.log`) |
| One test file per group | `tools/run_f674_all.py --files 1-117` | 117 files passed, 2,583 tests, each file's count as listed (the 2,574 of APG-F67.3 and the 9 new tests) |
| Groups 1 to 23 | `tools/run_f674_all.py --range 1-23` | 23 groups passed; the whole suite is 2,583 tests in 13 counted parts |
| Regression against APG-F67.3 | `tools/run_regression_f674.py --all` | 13 checks (R01 to R13), 0 failed |
| Mutation | `tools/f674_mutants.py --batch K/10 --jobs 2 --timeout 30` | 131 mutants in ten batches: 130 killed, 1 documented equivalent (PA-CMP-013), 0 survivors |
| Sabotage | `tools/sabotage_f674.py` | 16 cases, 16 caught |

The documented equivalent PA-CMP-013 is the same mutant as in APG-F67.2 and APG-F67.3. It is equivalent for any store that meets RH-03 of the history contract.

## 5. Records (append-only; `tools/make_f674_registers.py`)

| Row | What |
|---|---|
| F-75 | The finding; corrected here, open until independently verified |
| SR-119, SR-120 | The correction; the finer-grained runs; Local-tested |
| I-133 | What "unchanged" means |
| CF-45 | The audit of this release is outstanding; M8 is not authorised |

## 6. Files changed and added (compared byte for byte with the delivered APG-F67.3 ZIP)

- **Existing files changed: 8.**
  - `apg/policy_approval.py` and `apg/rec/policy.py`.
  - `README.md` and `RUN_COMMANDS.txt` (an F-67.4 section on top; the earlier text follows unchanged).
  - 4 programme tables, with rows appended only.
  - No existing test, tool or specification changed.
- **Files added.**
  - `tests/test_f674_type_strict.py`
  - Six tools: `probe_f674.py`, `f674_mutants.py`, `sabotage_f674.py`, `run_regression_f674.py`, `run_f674_all.py` and `make_f674_registers.py`
  - This record
  - `regression/f674/`
  - `logs/f674/`
