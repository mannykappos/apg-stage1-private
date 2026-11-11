# Change record APG-M7.3: the commit holds whole queries, after the independent audit of APG-M7.2 (F-69)

| Field | Value |
|---|---|
| Release | APG-M7.3, a separately versioned, additive correction release. It is the delivered M7.2 package (ZIP SHA-256 `d2f900490f9a0d88c76c390aac3e7d2169f30ccf770ccb8f9dbc779f1d08a476`) plus the correction below. The delivered M7.2 ZIP and documents are not modified or replaced. |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** F-69 stays open until the auditor verifies it, and so do F-64 to F-68. F-67 is still open and not corrected. |
| Authority | The auditor's verdict on M7.2, relayed by the product owner on Mon 2026-10-19. The verdict was not yet accepted. It asked for a targeted M7.3: a store-level guard that a query is unchanged (no new matching record), or serialisable transactions, plus tests at each interleaving. |
| Scope beyond apg/rec | The race could be closed only at the store, so three M2 files change: `apg/ports.py`, `apg/reference_impl.py` and `apg/tenancy.py` (I-117). The change is additive: a batch without guards behaves as before. The 38 M2 contract cases and the 39 faulty implementations give the same results. No other M2 to M6 or M9 file changes. Engine #17 and RFC-01 are unchanged. |

## 1. The finding and what changed

| ID | What was wrong in M7.2 | What changed | Tests |
|---|---|---|---|
| F-69 | The store could not hold a query as unchanged. A new overlapping finding created between the check and the commit was caught only by a second check after the commit, and the act had been committed before being reversed. A finding created after that second check left the act standing | **The store.** `ports.Guard` adds revision guards (0 = absent) and whole-query guards to `RecordStorePort.atomic`, checked with the writes as one indivisible step. The reference store checks them under a lock, and the scoped store passes guards on and screens query filters. **The lifecycle.** Each checked act commits with a whole-query guard on the findings and the recommendation inputs, and revision guards on everything read by key. **What goes.** The check after the commit and the reversal are removed | `tests/test_rec_m73_insert_race.py` (12 tests): the auditor's three interleavings at each boundary; the commit carrying every guard; real threads; and the guard contract, which the reference store passes and a store that ignores guards or whose batch is not indivisible fails. `apg/contracts/record_store_guard_contract.py` (RG-01 to RG-08) |

**What "closed" means here (I-116).** A checked act takes effect when its batch commits, and only if every guard holds then. A record committed before that moment refuses the act, and nothing is recorded. A record committed after it is a later change, ordered after the act in the store's commit order. That includes a record created after the commit but before the call returns. It is handled like any later change: the next checked act is refused, and the next run ends what no longer matches.

The auditor's interleavings 2 (between the commit and the M7.2 second check) and 3 (after the second check returned) are of this kind. M7.3 shows the commit order for them, and does not reverse the act.

If the product owner wants no overlapping finding to be creatable at all while an act is in progress, that needs a lock shared with detection (M5), and it is a decision for the product owner.

## 2. Files changed and added (compared byte for byte with the delivered M7.2 ZIP)

**Changed (15)**

- **Application.**
  - `apg/ports.py`: `Guard`, and the atomic contract.
  - `apg/reference_impl.py`: guards, a lock, and a commit-order list used by tests.
  - `apg/tenancy.py`: guards passed on, and query filters screened.
  - `apg/rec/lifecycle.py`: `source_check` returns guards; `_commit_checked` commits with them; the reversal is removed.
  - `apg/rec/engine.py`: `current_inputs` returns query and revision guards.
- **Tests.** `tests/test_rec_m72_race.py`: seven tests that expected the M7.2 reversal or inspected the M7.2 guard form now expect a refusal with nothing recorded, or inspect store guards. The other 11 are unchanged.
- **Tools.** `tools/m7_mutants.py`: it runs the M7.3 tests too.
- **Records and documents.**
  - `README.md` and `RUN_COMMANDS.txt`: an M7.3 section above the M7.2 text.
  - `programme/RECOMMENDATION_ENGINE.md`: section 8c.
  - Five programme tables with rows appended: finding F-69, status SR-103 and SR-104, interpretations I-116 and I-117, Engine handoff EDR-36, and carried-forward CF-35.

**Added**

- **Application.** `apg/contracts/record_store_guard_contract.py`.
- **Tests.** `tests/test_rec_m73_insert_race.py`.
- **Tools.** `probe_m72_insert_race.py`, `m73_store_mutants.py`, `run_guard_contract.py`, `run_regression_m73.py`, `run_m73_all.py`, `sabotage_m73.py` and `make_m73_registers.py`.
- **Regression data and logs.** `regression/m73/` holds the M7.2 manifest and the M7.2 table snapshot. `logs/m73/` holds the builder's runs.
- **Documents.** This record.

## 3. What the auditor could not complete (CF-35)

In the M7.2 audit, the full mutation run and sabotage case S22 did not finish. These are incomplete, not passes. S22 tested the check after the commit, which M7.3 removes. The split commands are in `RUN_COMMANDS.txt`, sections B, D and E. The store mutation run takes under a minute. The delivered M9.4, M7, M7.1 and M7.2 ZIPs can be supplied to the auditor.
