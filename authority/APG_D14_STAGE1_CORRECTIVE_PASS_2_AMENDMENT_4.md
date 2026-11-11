# APG D14 stage 1, corrective pass 2: amendment 4 (draft 1): how M10's m2 verdicts are obtained for E.2

**BUILDER-EXECUTED: NOT INDEPENDENT. Draft for decision. Not authorised until the owner posts it.**

## Basis
- **Amended:** the posted paper `23d2adb9…f0ea5`, as amended by amendments 1 (`211971…d382`), 2 (`a3cc26b5…cd6e`) and 3 (`89e5a268…6715`, owner, 14:38 on 2026-11-06).
- **This amendment authorises evidence work only.** It changes no file in the stage 1 tree, no logic, and no claim other than the one stated. It is not stage 1 acceptance and does not authorise stage 2.

## S12 (found at 15:35 on 2026-11-06, while preparing the E.2 m2 comparison)
- **E.2 says:** "M10's `m2_mutants.py` and `m2_mutants_s1` are run, and their per-id verdicts compared over the 198 common ids."
- **What M10's `m2_mutants.py` does.** It is byte-identical in the tree, SHA-256 `fe1fd878…157b`. Its `main` runs all 199 mutants, then prints the results in list order. At the first `ERROR` it prints `ERROR <id>: <info>` and returns 2 (`m2_mutants.py`, `main`: `if st == 'ERROR': print(...); return 2`).
- **On M10's `apg/reference_impl.py`** (identical in the tree, SHA-256 `1f910bf4…7c7f`):
  - `RI10-query-crosses-tenants`, at position 51, finds its target 0 times. That is the invalid target E.2 already names. No id before it is invalid.
  - So one run of M10's `m2_mutants.py` prints M10's verdicts for the first 50 ids only, then `ERROR RI10-query-crosses-tenants: pattern not found in reference_impl.py`, and exits 2.
  - The verdicts of the other 148 common ids are computed but never printed.
- **So E.2's m2 comparison cannot be made from runs of M10's script as written.** That is a requirement that cannot be met within the authorised scope (H). It needs no change to any file in the tree.

## AM4-1. Decided (option A, recommended)
**M10's verdicts are taken from M10's own per-mutant function,** called by a builder harness outside the tree. The harness:
- loads the tree's byte-identical `tools/m2_mutants.py`, checked against `fe1fd878…157b`, without changing it;
- calls M10's own `run_one(item, tmp)` once for each of the 199 items of M10's `MUT`, in M10's order, with M10's default of 4 workers;
- records, per id, M10's status (`KILLED`, `SURVIVED`, `ERROR`), its information (`tests`, `contracts`, `timeout`, or the error text), and whether the id is in M10's `EQUIV`;
- applies M10's own reading to them: `KILLED` stays a kill; a survivor documented in `EQUIV` is `EQUIVALENT`; any other survivor is `SURVIVED`.

The successor `m2_mutants_s1` is run as written, on all 199 ids.

**The comparison, unchanged from E.2:**
- the fixed values: 199 ids; RI10 at position 51, invalid on M10; 198 common executable ids with `sha256_lines` `d5da4f9a…694c`; the successor's `ids_sha256` `649e0e48…384e`;
- the allowed differences only:
  - RI10, which is `ERROR` on M10 and has a verdict on the successor;
  - an id M10 killed by `timeout`, or by a crash its `run_one` counts as a kill, that the successor reports `INDETERMINATE`. Each such id is listed.
- **any other difference is a stop-rule event.**

**Also recorded:** the literal output of one run of M10's `m2_mutants.py` itself, as evidence that it stops at RI10, its 50 printed verdicts compared with the harness's for the same ids.

**Option B: M10's script run in a temporary copy with RI10 taken out of `MUT`.** This changes M10's file in that copy, so the run is no longer M10's script as written. Not recommended.

**Option C: only the 50 ids before RI10 compared,** and the other 148 recorded as not compared. Point 2 then stays more open than E.2 says. Not recommended.

## Disclosure
- **Mistake 28.** The builder wrote E.2's m2 comparison without reading M10's `main`, which stops at its first `ERROR`.
