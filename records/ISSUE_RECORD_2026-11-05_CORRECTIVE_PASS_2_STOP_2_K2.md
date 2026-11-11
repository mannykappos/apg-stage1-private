# Issue record: corrective pass 2, stop 2 (K.2's premise is false for 7 of the 11 case runners)

**BUILDER-EXECUTED: NOT INDEPENDENT.** Written by the builder at 23:3x on 2026-11-05 (AEDT), during the unattended build the owner authorised at 23:00 (paper `23d2adb9…f0ea5` as amended by amendment 1 `211971…d382`). It accepts nothing, closes no finding, EDR or CF item, and makes no production-readiness claim.

## Why the work stopped
- **The rule.** Amendment 1, AM-8: "If implementation finds any further mismatch between this amended paper and the code, it is a stop-rule event."
- **The paper's stop rule H:** work stops and the builder reports "before making any further logic change". It names "a requirement that cannot be met within the authorised scope".
- **The builder applied it literally.** No further logic change has been made to the tree since the mismatch was found. The builder did not use the narrower reading in its own 23:00 decision record ("stops the work it concerns"), because H's text is wider.

## State of the tree at the stop
- **Branch** `corrective-pass-2`, uncommitted. One file is changed, `tools/evkit.py` (+1292 −61 lines).
- **A copy of the diff** is at `d14/s1/pass2_work/WIP_at_stop_1.diff`, SHA-256 `b8998f3a63a0d9f7c18631acc0dd1781e8b3fad59796919b226775a759cdcf75`.
- **What it contains, not yet tested beyond a smoke check:**
  - the P section;
  - `run_child` on P;
  - `run_sequence`;
  - `control()` with F.1, F.2 and B.4;
  - `mutation_main` with F.1, F.2 and the `LIMIT` line;
  - the `v=3` schema;
  - the K.1, B.4 and A.3 checker rules.
- **Not started:** `cases_main`, `faults_main`, the tests runners, the wrappers, the regression successors, the 33 guarded imports, and the tests.
- **The freeze** `d5f87d6b…85c8` is unchanged, and no evidence has been run.

## S6 (the stop): K.2's premise does not hold for 7 runners
- **The paper's premise.** K.2 assumes that each case runs inside `run_case(candidate, suite, case_id)`: "each case runs as a forked unit under P, from the parent state after … the inventory comparison; the child calls the unchanged `run_case`".
- **What the code does.** In 7 runners, the harness API runs a whole suite in one call. `enumerate_cases` calls it to list the cases, and caches every verdict in `_CACHE`. `run_case` only looks up the cached verdict. The 7 runners:

  | Runner | The harness call that runs every case |
  |---|---|
  | `run_contracts_s1` | `R.run` (`:31`) |
  | `run_guard_contract_s1` | `run_guard_suite` (`:30`) |
  | `run_history_contract_s1`, case mode | `H.run_history_suite` (`:37`) |
  | `run_m3_contracts_s1` | `C.run_all` (`:24`) |
  | `run_m5_contracts_s1` | `C.run_all` (`:24`) |
  | `run_m6_contracts_s1` | `C.run_all` (`:24`) |
  | `run_m91_contracts_s1` | `C.run_all` (`:22`) |

  Between them they hold 126 of the 386 cases.
- **The effect.** `cases_main` calls `enumerate_cases` for its inventory comparison (step 6 of A.1, current freeze `evkit.py:1966`). That comparison runs in the parent, so all 126 cases execute in the parent: unsupervised, with no time limit, and before any fork. A forked child would only return a cached verdict.
- **Two of K.2's own tests cannot pass,** because the hang happens in the parent at step 6:
  - "a case that hangs" on `run_contracts_s1`;
  - the same test on the other six runners.
- **The 4 corpus runners are not affected:** `run_det_corpus_s1`, `run_fin_corpus_s1`, `run_ingest_corpus_s1` and `run_mkt_corpus_s1` (260 cases). Their cases are listed statically (`K.cases()`, `corpus.cases()`), and `run_case` really runs one case.
- **How long a run takes today** (builder's workspace, Python 3.13): each of the 7 runners completes in 0.2 to 0.5 s.

## S7 (a gap the same read-only sweep found): F.2's result form for 6 supervisors that print no `RESULT` line
- **The supervisors.** AM-6 (c) puts the 5 regression successors and `run_cr02_reference_s1` under F.2's cancellation mechanism.
- **The gap.** F.2 defines the interrupted result only through the item and `RESULT` forms. These 6 print M10's own output, with no `RESULT` line (T-K). Nothing in the paper says what they print, or which exit code they use, when they are interrupted.
- **What it affects.** AM-5 (c) already fixes the leak form for a regression step: "(INCOMPLETE: processes left)". The interrupted form is not fixed anywhere.

## S8 (a paper error, disclosed as mistake 22)
- **The error.** B.1 says that under forking "`run_history_contract_s1`'s result cache (`_CACHE`) is no longer shared".
- **Why it is wrong.** `_CACHE` is used only by that tool's case mode (S6). Its fault mode calls `failed(cls)` once per plant, and never uses the cache. The sentence was written from the plan, not the code: the same class of mistake as mistake 21.

## What the builder proposes
These are in `d14/decisions/APG_D14_STAGE1_CORRECTIVE_PASS_2_AMENDMENT_2_DRAFT_v1.md`, together with the implementation readings the builder had taken before the stop, set out for confirmation.
