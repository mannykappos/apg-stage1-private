# Issue record S14 (2026-11-08, 02:15 Melbourne): the Python 3.13 m2 comparison differs outside AM4-1's allowances

**BUILDER-EXECUTED: NOT INDEPENDENT.** This is a stop under paper H: a change in E.2's allowed differences. No logic change is involved and none has been made. Nothing in the stage 1 tree has changed. The freeze is still `c9b324eb…9459297`. The m2 comparison waits for the owner. As at S12, the rest of the evidence work continues.

## The result (`evidence_pass2/compare_py313/m2.txt`)

**The successor, `m2_mutants_s1` as written:**
- Python 3.13, the default `--jobs 2`, one process, run detached from the 2-hour job limit;
- 11:37:39Z to 15:08:33Z on 2026-11-07, which is 3 h 31 min;
- `RESULT v=3 kind=mutation tool=m2_mutants_s1 run=run selected=199 preflight=PASS control_start=PASS started=199 completed=199 killed=196 survived=0 equivalent=3 indeterminate=0 item_errors=0 not_run=0 control_end=PASS run_errors=0 ids_sha256=649e0e48…3384e status=OK exit=0`;
- no timeouts;
- `CLEANUP_SUMMARY units=219 leaked=0 remaining=0`;
- start control: `run_m2_tests_s1` took 196.3 s; end control: 209.8 s.

**M10, through the AM4-1 harness** (`run_one`, 4 workers, the five slices):
- KILLED 197: by tests 114, by contracts 0, **by timeout 83**;
- EQUIVALENT 1 (ME35);
- SURVIVED 0;
- ERROR 1 (RI10).

**The fixed values all hold:**
- 199 ids;
- RI10 at position 51, ERROR on M10;
- the common-id `sha256_lines` `d5da4f9a…694c`;
- the successor's `ids_sha256` `649e0e48…384e`.

**The allowed difference (1):** RI10, which is ERROR on M10 and KILLED on the successor (`test_adversarial_builder_zero.py`).

**The differences outside the allowances (2):**

| id | M10 (`run_one`, AM4-1 reading) | successor |
|---|---|---|
| CA01-float-allowed | KILLED (timeout) | EQUIVALENT (documented) |
| RI13-input-aliased | KILLED (timeout) | EQUIVALENT (documented) |

`RESULT m2 DIFFERENT 2`

## Why, as far as the builder can see (an environment effect, not a change in either tool's logic)
- **All three mutants are in M10's own `EQUIV`.** A mutant that survives runs M10's whole test suite, with no failfast exit.
- **That suite takes 196 to 210 s alone on this machine.** That is the successor's control timing for `run_m2_tests_s1`; M10's `run_m2_tests` is expected to be similar.
- **AM4-1 fixes M10's default of 4 workers.** This machine has 2 cores, so a full pass under that contention exceeds M10's 300 s timeout.
- **M10's `run_one` counts a timeout as a kill:** `('KILLED','timeout')`. AM4-1's reading keeps a kill a kill.
- **ME35 survived on M10.** It ran in the last slice, where fewer items were in flight at the end.
- **So, for an `EQUIV` mutant, M10's verdict here depends on load.**
- **AM4-1 allows only one timeout case:** M10 killed by timeout while the successor reports INDETERMINATE. It does not cover M10 killed by timeout while the successor reports EQUIVALENT.

**Also disclosed: 83 of M10's 197 kills here are by timeout.** For those 83 ids the comparison shows only that both sides end in KILLED; it does not show that M10's tests killed them. The successor killed all 196 non-equivalent ids by its oracles, with no timeouts.

## Options (the owner decides; each is evidence-only)
- **A (recommended).** Add an allowed difference: an id in M10's `EQUIV` that M10's `run_one` kills by timeout, and that the successor reports EQUIVALENT. Each such id is listed, as for the other allowances. The 83 timeout kills are disclosed as weak evidence. The cost is no new run.
- **B (supporting evidence, with A or alone).** Call M10's own `run_one` again for the three `EQUIV` ids only, one at a time (1 worker), to show that M10 itself lets them survive when the machine is not overloaded. The cost is about 15 minutes per Python. This departs from AM4-1's fixed 4 workers for these three calls only.
- **C (strongest).** Rerun the whole AM4-1 harness with fewer workers (1 or 2), so that M10's timeouts mostly disappear and its kills are kills by its own tests. The cost is about 3.5 to 5 hours per Python. This changes AM4-1's fixed 4 workers.

## Meanwhile
- **Continuing (no logic change):** the Python 3.12 golden, pairs, b6 and k2 comparisons (started 15:13Z); then the historical, static and audit checks, and the mapping agent.
- **Waiting for the owner:** the Python 3.12 m2 harness and the successor run, because the owner's choice may change how they are run.

## Addendum (2026-11-08, 03:25 Melbourne): a diagnostic, made before the owner's decision
**BUILDER-EXECUTED: NOT INDEPENDENT. A diagnostic, not AM4-1 evidence.** To characterise S14 before asking, the builder called M10's own `run_one` on the three `EQUIV` ids, one at a time (1 worker), on each Python, from a fresh extraction of freeze `c9b324eb` (`m2_mutants.py` `fe1fd878…157b`).
- It is option B's run, made before the owner chose. That departs from AM4-1's 4 workers, for diagnosis only. It changes nothing in the tree, and nothing in the comparison.
- It was first noted in amendment 5 draft 1, and not in this record or the build log until the mapping agent pointed that out (its discrepancy 11).
- **Results** (`d14/s1/evidence_pass2/diagnostic_s14/`): all three SURVIVED on both Pythons, with no kill by tests or contracts.

| id | Python 3.13 | Python 3.12 |
|---|---|---|
| CA01-float-allowed | SURVIVED, 203.6 s | SURVIVED, 258.8 s |
| RI13-input-aliased | SURVIVED, 212.8 s | SURVIVED, 225.3 s |
| ME35-decision-ledger-by-presence | SURVIVED, 232.1 s | SURVIVED, 233.4 s |

**What this shows:** a full pass takes 200 to 260 s even with one item at a time (the mapping agent was also running during part of it). With 4 workers on 2 cores, that is well over M10's 300 s limit.

**Also corrected (mistake 32):** the comparison tool's INDETERMINATE allowance did not check that M10's kill was by timeout, so it allowed more than AM4-1 does. It now checks. M10's `run_one` cannot tell a crash from a test kill, so no allowance is made on the crash ground; that fails closed. No id used the allowance, and the rerun `m2.txt` is byte-identical.
