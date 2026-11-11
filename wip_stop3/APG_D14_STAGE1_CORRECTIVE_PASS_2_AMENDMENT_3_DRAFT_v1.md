# APG D14 stage 1, corrective pass 2: amendment 3 (draft 1)

**BUILDER-EXECUTED: NOT INDEPENDENT. Draft for review. Not authorised until the owner posts it.**

## Basis
- **Amended:** the posted paper `23d2adb980216c9703287cd8803570dc2fab3cf48f037dfa1d39a0d3029f0ea5`, as amended by amendment 1 (`211971452c8f02ac0d24514ebc9a12c1c0cded3eeb55f2c918f125a775c6d382`) and amendment 2 (`a3cc26b5073ea4082de6a7a52013767634e076b64886bba0f49524a7f706cd6e`).
- **The stop:** `rec/ISSUE_RECORD_2026-11-06_CORRECTIVE_PASS_2_STOP_3_C1.md` (S9, S10).
- **This amendment authorises corrective work only.** It is not stage 1 acceptance and does not authorise stage 2.
- **Unchanged:** every other part of the paper and its two amendments, the stop rule H, AM-8 and the standing constraints.

## Summary of decisions

| Decision | What it settles | Builder's recommendation |
|---|---|---|
| AM3-1 | S10: when the moved imports' identity is checked | check it immediately after the guarded load, before any item (option A) |
| AM3-2 | S9: E point 3, which C.1 makes unmeetable | rewrite point 3 against C.1, with no new output line (option A) |
| AM3-3 | E point 17's first half | a reading: assert the child's `apg` path through the existing child probe |
| AM3-4 | the wrapper `CHECK` checker rule for AM2-2 (d) | confirm the change made before the stop |
| AM3-5 | disclosures | mistakes 24 and 25; the K.1 test's placement |

## AM3-1. The identity of the moved imports (S10)

**Option A (recommended): check immediately after the load.**
- **Where it applies:** in `evkit.guarded_load` (the 5 fault runners and the 18 mutation and sabotage successors) and in `cases_main`'s `load=` path (the 10 case runners, and `run_history_contract_s1`'s case mode).
- **The check:** as soon as `load()` returns, the import identity check of §2.5 (`evkit.import_identity`) runs again, with the same rules and arguments as `start`'s.
- **When it runs:**
  - before the inventory comparison, the preflight, the start control or any item;
  - for case runners, after the selection is resolved (A.1), since that is where the load already runs.
- **If it finds an error,** the run is refused in C.1's refusal form, with the identity check's own codes (`IMPORT_OUTSIDE_EXTRACTION`, `IMPORT_PRELOADED`, `IMPORT_NO_FILE`, or an untrusted module outside the standard library):
  - **fault runners, mutation and sabotage tools:** every pinned item `NOT_RUN cause=run_error`, `preflight=NOT_RUN`, `control_start=NOT_RUN`;
  - **case runners:** the resolved selection of A.1, its cases `NOT_RUN`;
  - in both cases, the `RESULT` line, exit 2.
- **The end-of-run check (`IMPORT_END`) is unchanged.**
- **What this does not change:** a module's own import-time code still runs when it is imported, as it did before C.1. No check can come before an import. The check stops any item from running on a harness from elsewhere.
- **Tests,** each in a temporary copy whose `load()` puts a decoy directory holding a full copy of `apg` first on `sys.path`:
  - `run_contracts_s1` (a batch case runner), `run_fin_corpus_s1` (a per-case runner), `run_faults_s1` and `m2_mutants_s1`;
  - each is refused with `RUN_ERROR IMPORT_OUTSIDE_EXTRACTION apg <decoy path>`, with no `CASE`, `PLANT` or `MUTANT` line other than `NOT_RUN`, and no control run, exit 2;
  - each output is accepted by `check_output` as `EVIDENCE_ERROR`.
- **The effect on the comparisons:** none expected. On the unchanged tree the check finds nothing, so B.6, K.2 and E.2 must still be identical. Any difference is a stop-rule event.

**Option B: no change.** The gap is recorded as a limitation of C.1: the moved imports are checked only at the end, and a run that used a harness from elsewhere is `EVIDENCE_ERROR`, exit 2, after its items have run. The builder does not recommend this, because before C.1 the start check refused such a run before any work.

## AM3-2. E point 3 (S9)

**The conflict.** E point 3 asks for "the start line `IMPORT apg <real path>` asserted on a real runner". C.1 moves every module-level `apg` import of the 15 runners after `start`, and C.2 tests that nothing listed is imported first. No other real runner imports `apg` before `start`, on either freeze.

**Option A (recommended): point 3 rewritten, with no new output line.** Point 3 becomes:

> On a real case runner (`run_contracts_s1`) and a real fault runner (`run_faults_s1`), unchanged:
> - the start lines name no `apg` module (C.1);
> - the post-load identity check of AM3-1 finds nothing (no `RUN_ERROR`);
> - the end line `IMPORT_END apg <this tree>/apg/__init__.py` is asserted literally.
>
> Together with AM3-1's decoy tests, this shows which `apg` the work used, and that one from elsewhere is refused before any item.

**Option B: a new record line.** `guarded_load` and `cases_main` print one `IMPORT_LOAD <module> <path>` line for each module the load added, immediately after the post-load check. Point 3 then asserts `IMPORT_LOAD apg <real path>`. This changes the output of 33 runners. The checker would have to accept the new line, and option A shows the same thing without it.

## AM3-3. E point 17, first half (a reading for confirmation)
- **The point:** "P7-B2: the real `apg` import path asserted".
- **What the P7-B2 run does.** `run_m8_tests_s1 --file test_m8_dependency.py`, with `APG_ROOT` set to a decoy, never imports `apg` in its own process, on either freeze, so it prints no `apg` record. Its child imports `apg` through `tests_m8/_auif.py`.
- **The reading.** The test adds the child probe that `test_exec_env::ChildrenStartIsolated` already uses, which records each child's `apg.__file__`. It asserts that path is this tree's `apg/__init__.py`, never the decoy's, and keeps every existing assertion.
- This is a test only, with no logic change.

## AM3-4. The wrapper `CHECK` rule (confirmation of a change made before the stop)
- **The rule.** AM2-2 (d) defines an interrupted no-kind child's `CHECK` as `INDETERMINATE`, with `exit=3` and its marker field as observed.
- **What the checker did.** It accepted `INDETERMINATE` only with `exit=-`, so it refused that form, and the AM2-2 (e) consumer test failed.
- **The change.** The checker now also accepts `INDETERMINATE` with `exit=3` and a marker of `seen` or `absent`. Everything else is unchanged.
- **The test** also shows that `exit=2`, `exit=3 marker=-` and `exit=0` with `INDETERMINATE` are still refused.

## AM3-5. Disclosures
- **Mistake 24.** The builder wrote E point 3 from the mapping's wording without checking it against its own C.1. The drafts and the reviews of the paper missed the conflict.
- **Mistake 25.** The builder's working log gave clock times after 11:2x on 2026-11-06 that were not read from a clock, and were wrong. They are order labels only. Times are now read from the clock.
- **The K.1 real-tool test** plants the leak on the end control's last command. Under reading 7, a leak on an earlier command is fixed at the end of that command's cleanup, so an interrupt during that cleanup is correctly `CONTROL_NOT_RUN cause=interrupted`. That case is kept as its own test of reading 7. No code was changed.

## Change log: what each decision changes
| Decision | The sections it changes |
|---|---|
| AM3-1 | C.1 (a post-load identity check, and its refusal); C.2 (the decoy tests) |
| AM3-2 | E point 3 |
| AM3-3 | E point 17 (how the first half is asserted) |
| AM3-4 | AM2-2 (d): the checker's acceptance of the form it defines |
| AM3-5 | the documents' list of mistakes |
