# Issue record S13 (2026-11-07, 19:55 Melbourne): AM4-1's "also recorded" run of M10's `m2_mutants.py` cannot be made here

**BUILDER-EXECUTED: NOT INDEPENDENT.** Reported under paper H ("a requirement that cannot be met within the authorised scope"). No logic change is involved and none has been made. Nothing in the stage 1 tree has changed. The freeze is still `c9b324eb…9459297`.

## What AM4-1 requires
- The harness calls M10's own `run_one` once for each of the 199 items of `MUT`, in M10's order, with 4 workers.
- **Also recorded:** "the literal output of one run of M10's `m2_mutants.py` itself, as evidence that it stops at RI10."

## What was found
- **The one-process m2 comparison was stopped by the 2-hour background job limit.** It ran from 17:39 to 19:39, while still inside M10's 199 `run_one` calls, so there is no result. This session runs on a machine with 2 cores and 7 GB of memory.
- **Disk.**
  - M10's `run_one` copies the tree for each mutant (26 MB) and deletes nothing until the whole run ends.
  - M10's tests also leave temporary directories behind (`mie_static_*`).
  - Measured on two items: 238.5 MB of temporary space at the end, so about 120 MB per mutant. Over 199 mutants that is roughly 16 to 24 GB.
  - The stopped run had reached 14 GB before it was stopped; its temporary copies have been removed.
  - Free disk is 22 GB, after removing 3.6 GB of stale October temporary directories. The 10 GB floor is the D14 run-set constraint.
- **So one run of M10's script as written:**
  - needs one process for more than 2 hours, which is over the job limit;
  - and roughly 16 to 24 GB of temporary disk. That would take free disk below the 10 GB floor, and possibly to zero.
- **A full disk would also spoil the record:** M10's `run_one` counts any non-zero exit, including a crash, as a kill.

## The harness, as now run (an implementation reading, disclosed)
- **The AM4-1 harness now runs in five processes,** over the slices `MUT[0:40]`, `[40:80]`, `[80:120]`, `[120:160]` and `[160:199]`, in M10's order.
- **Each slice:**
  - runs on its own fresh extraction;
  - calls M10's own `run_one` with 4 workers;
  - removes its temporary space at the end (about 5 GB at most).
- **The comparison step (`m2c`)** checks that the slices loaded the same `MUT` and `EQUIV` and cover every id exactly once, in M10's order. It then applies the unchanged E.2 / AM4-1 comparison.
- **The tool:** `d14/s1/tools/compare_pass2_s1.py`, modes `m2h`, `m2w`, `m2s` and `m2c`, all outside the tree.
- **The builder reads this as within AM4-1:**
  - every item is called once;
  - in M10's order;
  - with M10's default of 4 workers;
  - by M10's own function.

  The owner may rule otherwise.

## Options for the "also recorded" run
- **A (recommended).** The literal run is not made. In its place:
  - the literal output of M10's script as written with `--list` (exit 0, the 199 ids in order, RI10 at position 51);
  - the harness's own result for RI10 (`ERROR`, pattern not found) and for the 50 ids before it (none `ERROR`);
  - M10's `main`, quoted (`if st == 'ERROR': print(...); return 2`).

  The S12 basis then rests on these, not on an observed run.
- **B.** Make the literal run anyway, in a process detached from the job limit, with free disk falling to a few GB or to zero. Not recommended: the 10 GB floor is breached, the run may fail, and a full disk turns crashes into "kills".
- **C.** Leave the record open and say so in the documents.

## Disclosures
- **Mistake 30.** I wrote the one-process m2 mode without estimating M10's run time and temporary disk on this machine.
- **The idle gap.** The first four Python 3.13 comparisons finished at 10:16 Melbourne time on 2026-11-07. The session then sat idle until 17:39: the container restarted, and the completion was not acted on. No work ran in that time.

## Continuing meanwhile (evidence only, no logic change)
- the harness slices and the successor run, on both Pythons;
- the Python 3.12 golden, pairs, b6 and k2 comparisons;
- the historical, static and audit checks;
- the mapping agent.

The m2 comparison result (`m2c`) is reported when its inputs exist. Any difference outside AM4-1's allowances is a stop-rule event.

## Addendum (2026-11-07, 22:40 Melbourne): measured figures, Python 3.13
**BUILDER-EXECUTED: NOT INDEPENDENT.** The disk estimate above (about 120 MB per mutant, 16 to 24 GB) was overstated: it came from a 2-item probe. The five harness slices measure it directly.

| Slice | Exit | Results | Time | Temporary space at end |
|---|---|---|---|---|
| MUT[0:40] | 0 | 40 | 1028 s | 2.08 GB |
| MUT[40:80] | 0 | 40 | 1854 s | 2.73 GB |
| MUT[80:120] | 0 | 40 | 1989 s | 2.94 GB |
| MUT[120:160] | 0 | 40 | 2738 s | 3.19 GB |
| MUT[160:199] | 0 | 39 | 1969 s | 1.09 GB |
| **Total** | | **199** | **9578 s (2 h 40 min)** | **12.03 GB** |

Every slice loaded `tools/m2_mutants.py` with SHA-256 `fe1fd878…157b`, as expected.

**So one literal run of M10's script, on this machine:**
- about 2 h 40 min in one process, which is over the 2-hour job limit, so it would have to run detached;
- about 12 GB of temporary space held until the end. Free disk is 22 GB, so it would end at or just below the 10 GB floor, not at a few GB or zero as first estimated.

Option B is therefore less dangerous than first stated, but it still reaches the floor. The builder still recommends option A; the owner decides.

**The successor's own run (`m2_mutants_s1`, as written, default `--jobs 2`)** is also expected to take more than 2 hours here. It is running detached, in one process, from 11:37:39Z. The builder tool's timeout for that step was raised from 7000 s to 8 h; that is a change to the builder's comparison tool only, outside the tree. It is not a change to the successor or to how it is run.
