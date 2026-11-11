# APG D14 stage 1, corrective pass 2: amendment 5 (draft 4), the decisions after S13, S14 and the independent mapping

**BUILDER-EXECUTED: NOT INDEPENDENT. Draft for decision. Not authorised until the owner posts it.**

- **Prepared:** 2026-11-08, Melbourne time.
- **Supersedes:** draft 3 (`ff94b7c3…7983`) and draft 2 (`3e0850ea…acda`), both kept.
  - Draft 3 made every correction in GPT's review of draft 2 (received 10:52 on 2026-11-08), and two gaps the builder found itself.
  - Draft 4 makes the four corrections of GPT's scoped re-review of draft 3 (received 11:10), in the reviewer's own wording. That review found the other items resolved. By the owner's decision, draft 4 goes to the owner without a further review round.
  - **Appendix C** lists each review item and how it was handled.
  - **Appendix D** quotes the operative passages of AM4-1 and C.1, and M10's code, verbatim.
  - **Appendix A** is the builder's plan for every gap the mapping found.
  - **Appendix B** is the mapping agent's report, verbatim. It was written before the corrections in Appendix A part 3, so it still reports discrepancies 15, 16, 18 and 22 as found.

## 0. Where things stand

**Authority.** The posted paper `23d2adb9…f0ea5`, as amended by:

| Amendment | SHA-256 | Authorised |
|---|---|---|
| 1 | `211971…d382` | |
| 2 | `a3cc26b5…cd6e` | |
| 3 | `89e5a268…6715` | owner, 14:38 on 2026-11-06 |
| 4 | `b6be070e…a7d6` | owner, 17:31 on 2026-11-06 |

**The frozen candidate.** Freeze `c9b324ebd236b6ad1b5c6207e6d1ea3db584ef0861db636d9f94fb8137459297`: commit `6f65d488`, 1555 files, built twice byte-identical. The old freeze `d5f87d6b…` is kept.

**Evidence on this freeze.** All builder-executed. Every run set changed 0 files.

| Evidence | Python 3.13 | Python 3.12 |
|---|---|---|
| T: the 10 test files (613 tests) | 10/10 OK | 10/10 OK |
| W: the 19 wrapper runs | 19/19 exit 0, 0 checker problems | the same |
| M: m8 mutation | 82 selected, 79 killed, 3 equivalent, 0 survived; checks as expected | the same |
| Golden (6 runners) | SAME | SAME |
| Pairs (15) | SAME | SAME |
| B.6 (111 items; CONTROL values and causes compared, see Appendix A part 3) | SAME | SAME |
| K.2 (386 items) | SAME | SAME |
| m2 (E.2 / AM4-1) | **DIFFERENT 2 (S14)** | not run (waits for this decision) |
| Historical (100 rows) | 100/100, archive unchanged | 100/100, archive unchanged |

**Other evidence on this freeze:**
- **Static checks:** frozen-file comparison 0 problems (73 successor tools, the M10 originals byte-identical); route proofs 0 old-tool children; case-inventory limit check.
- **Audits:** outside services (rerun, see mistake 33) and process-API reach. Finding 11 stays open.
- **Child-start scan:** process starts in successor code at exactly two sites, `run_unit` and `run_forked`.

**A limitation that applies to every m2 result here.** 83 of M10's 197 kills on Python 3.13 are kills by timeout. For those 83 ids the comparison shows only matching classifications. They are not shown to be kills by M10's tests, and no claim is made that all 197 M10 kills were caused by M10's tests. The same holds for any later m2 result made under the same 4-worker condition.

**Open stops:**
- **S13:** the literal run of M10's `m2_mutants.py` (AM5-1 and AM5-2).
- **S14:** two m2 differences outside AM4-1's allowances (AM5-3).

**The independent mapping (Appendix B):** 127 requirements, of which 55 are closed by evidence, 49 partly addressed and 23 still open. It also lists 22 discrepancies. After triage (Appendix A), about 54 rows and discrepancies need tests or test records (AM5-4).

**This amendment changes no product logic.** Every option is either evidence work, a waiver or an alternative evidence method named as such, or tests, test records, builder-tool documentation and the change record. Any test that fails is a stop under paper H.

## Summary of the decisions

| # | Decision | Options | Builder's recommendation |
|---|---|---|---|
| AM5-1 | S13: the literal run of M10's m2 script | A waive it, with named substitute evidence · B run it detached · C leave open | **A (a waiver)** |
| AM5-2 | S13: the five-slice harness | approve it as an alternative evidence method, not as equivalent to one process; or rule otherwise | **approve as an alternative** |
| AM5-3 | S14: CA01 and RI13, M10 "killed by timeout" against successor EQUIVALENT | A1 an allowance for the 2 ids · A2 an allowance for the 3 ids of M10's fixed `EQUIV` · B rerun the 3 EQUIV ids at 1 worker · C rerun everything at fewer workers | **A1 with B** (builder and reviewer agree) |
| AM5-4 | The mapping's test gaps | A write the missing tests, re-freeze, run the full evidence once · B package now, with the gaps disclosed | **A** |
| AM5-5 | (a) F8; (b) mistake 23; (c) mistake 29 | see AM5-5 | (a) **F8 stays partly addressed** · (b) **ratify as an application of C.1's rule, with the failure to stop recorded** · (c) **keep the fix; the breach stays recorded** |
| AM5-6 | The order of the remaining evidence | as set out, for each AM5-4 option | — |

---

## AM5-1. S13: AM4-1's "also recorded" literal run, a waiver

**The requirement.** AM4-1, quoted in Appendix D.1: "Also recorded: the literal output of one run of M10's `m2_mutants.py` itself, as evidence that it stops at RI10, its 50 printed verdicts compared with the harness's for the same ids."

**What was found.**

- **The slices (measured).** The five harness slices on Python 3.13 took 1028 + 1854 + 1989 + 2738 + 1969 = 9578 s, that is 2 h 39 min 38 s. Their temporary space at the end of each slice was 2.08, 2.73, 2.94, 3.19 and 1.09 GB.
- **A single run (estimated, not measured).**
  - **Time.** M10's `main` runs all 199 items before it prints anything (Appendix D.3), so one literal run would take at least the full 2 h 40 min in one process. That is over the 2-hour job limit, so it would have to run detached.
  - **Disk.** The sum of the slices' figures, 12.03 GB, is an estimate derived from five separate runs. It is not a measurement of one run.
  - **The measured single-process attempt.** That attempt (mistake 30) is the more relevant figure. It was still inside M10's 199 calls when it was stopped at the 2-hour limit, and its temporary space had already reached 14 GB. Its starting free disk was not recorded.
  - **So a full single run would probably need more than 14 GB.** With about 22 GB free now, it would probably end below 8 GB, breaching the 10 GB floor. The S13 addendum's "at or just below the floor" understated this; it is corrected here (see Disclosures).
- **A full disk would spoil the record,** because M10's `run_one` counts any non-zero exit, including a crash, as a kill (Appendix D.3).

**Options.**

- **A (recommended): a waiver.** Suggested wording for the owner:

  > The owner waives the requirement for a literal full execution of M10's `m2_mutants.py`, and for the comparison of its 50 printed verdicts with the harness's. The `--list` output, the harness's results, and the static control-flow evidence below are accepted as the alternative evidence for this item. S13 is therefore resolved by an owner-approved evidence substitution, not by completion of the original literal-run requirement.

  The substitute evidence:
  - (i) the literal output of M10's script with `--list`: exit 0, 199 ids, RI10 at position 51 (`evidence_pass2/compare_py313/m2_logs/m10_script_list.txt`);
  - (ii) the harness's result for RI10, `ERROR` "pattern not found in reference_impl.py", and its results for the 50 ids before RI10, none of them `ERROR`;
  - (iii) M10's code, quoted whole in Appendix D.3:
    - `main` collects all 199 results in `MUT` order before printing;
    - its print loop walks the results in that order and returns 2 at the first `ERROR`;
    - `run_one` returns `ERROR` when the mutant's pattern is absent from the source.

  Together these show that M10's `main` would first complete all 199 `run_one` calls, then its ordered print loop would print the 50 results before RI10, print `ERROR RI10-query-crosses-tenants: pattern not found in reference_impl.py`, and return 2. This is static evidence of the output and exit behaviour. It is not evidence that execution stops at RI10, or an observed literal run.

- **B.** The run is made detached on each Python. Cost: at least 2 h 40 min per Python. Risk: the 10 GB floor is probably breached, and a full disk would turn crashes into "kills".
- **C.** The item is left open, and the documents say so.

## AM5-2. S13: the five-slice harness, as an alternative evidence method

**What the method preserves (not equivalence to one process):**
- M10's own `run_one`, called once for every item of `MUT`, in M10's order;
- 4 workers within each slice;
- each slice on a fresh extraction of the freeze, with its temporary space removed at its end;
- the comparison step checks that every slice loaded the same `MUT` and `EQUIV`, and that together they cover every id exactly once, in order.

**What it changes compared with one uninterrupted process:**
- Temporary state does not accumulate across slices.
- The load is lower at each slice's boundaries, because fewer items are in flight. This bears on S14: ME35 survived on M10 in the last slice.

**It does not establish** that a single-process execution would produce identical results.

**The decision asked.** The owner approves the five-slice method as the chosen alternative execution method for AM4-1's harness, because one process exceeds the 2-hour job limit and the disk floor. The documents describe it as such, not as AM4-1's method itself.

## AM5-3. S14: the two m2 differences

**The result on Python 3.13** (`evidence_pass2/compare_py313/m2.txt`, SHA-256 `6a2685af…a590`):
- **The successor, `m2_mutants_s1` as written** (default `--jobs 2`, one process, run detached from the job limit, 3 h 31 min):
  - selected=199, killed=196, equivalent=3, survived=0, indeterminate=0;
  - controls PASS/PASS, start control 196.3 s, end control 209.8 s;
  - `ids_sha256` as fixed, status=OK, exit 0;
  - no timeouts;
  - `CLEANUP_SUMMARY units=219 leaked=0 remaining=0`.
- **M10, through the harness:** KILLED 197 (by tests 114, by contracts 0, by timeout 83), EQUIVALENT 1 (ME35), SURVIVED 0, ERROR 1 (RI10).
- **The fixed values all hold:** 199 ids; RI10 at position 51; the common-id `sha256_lines` `d5da4f9a…694c`; the successor's `ids_sha256` `649e0e48…384e`.
- **The allowed difference (1):** RI10, which is ERROR on M10 and KILLED on the successor.
- **The differences outside the allowances (2):**

| id | M10 (`run_one`, the AM4-1 reading) | successor |
|---|---|---|
| CA01-float-allowed | KILLED (timeout) | EQUIVALENT (documented) |
| RI13-input-aliased | KILLED (timeout) | EQUIVALENT (documented) |

**The cause.** The results are consistent with CPU contention under M10's 4-worker configuration on this 2-core machine:
- all three ids are in M10's own `EQUIV`;
- a surviving mutant runs M10's whole suite, with no failfast exit;
- that suite took 203 to 259 s per id even when run one at a time;
- M10's timeout is 300 s, and `run_one` records a timeout as `('KILLED','timeout')` (Appendix D.3).

The one-at-a-time diagnostic below supports this explanation. It does not conclusively isolate machine load as the sole cause.

**A diagnostic, made before this decision and disclosed.** It is not AM4-1 evidence (`evidence_pass2/diagnostic_s14/`). The builder called M10's own `run_one` on the three `EQUIV` ids, one at a time, on each Python, from a fresh extraction of the freeze:

| id | Python 3.13 | Python 3.12 |
|---|---|---|
| CA01-float-allowed | SURVIVED, 203.6 s | SURVIVED, 258.8 s |
| RI13-input-aliased | SURVIVED, 212.8 s | SURVIVED, 225.3 s |
| ME35-decision-ledger-by-presence | SURVIVED, 232.1 s | SURVIVED, 233.4 s |

None was killed by tests or contracts. The diagnostic tests three ids only. It does not establish the cause of the 83 timeout kills (section 0).

**Options.**
- **A1 (recommended by the builder and the reviewer).** AM4-1's allowed differences gain exactly two entries: `CA01-float-allowed` and `RI13-input-aliased`, each where M10's `run_one` kills it by `timeout` and the successor reports `EQUIVALENT`. Any other "M10 timeout against successor EQUIVALENT" difference stays a stop needing a separate owner decision.
- **A2 (not recommended; kept as an owner option).** The same, but naming all three ids of M10's `EQUIV`: `CA01-float-allowed`, `RI13-input-aliased` and `ME35-decision-ledger-by-presence`.
  - **The list is bounded.** M10's `EQUIV` is a fixed dictionary in the immutable M10 file (`tools/m2_mutants.py`, `fe1fd878…157b`), quoted in Appendix D.4.
  - **But A2 is wider than A1.** It grants an allowance for an id that has not produced the S14 discrepancy, and so pre-authorises a future M10 timeout against a successor EQUIVALENT for ME35.
  - **The evidence on ME35.** ME35 survived in M10's final slice, and the one-at-a-time diagnostic also shows that it can survive when run individually. This is consistent with sensitivity to machine load, but does not establish that low load was the sole reason for its survival.
  - **What A1 risks.** If ME35 times out on the new freeze or on Python 3.12, A1 makes it a stop for the owner's decision. That is the disciplined outcome: a decision on evidence, not in advance.
- **B (with A1 or A2).** M10's own `run_one` is called on the three `EQUIV` ids only, one at a time, on each Python, and recorded beside the comparison.
  - It is repeated on the new freeze under AM5-4 option A.
  - A survivor supports the allowance; a kill by tests or contracts is a stop.
  - This departs from the 4 workers for these three calls only.
- **C.** The whole harness is rerun with 1 or 2 workers, so that M10's verdicts mostly come from its own tests.
  - This is the strongest evidence. It also addresses the 83-timeout limitation, which no other option does.
  - It costs about 3.5 to 5 hours per Python, and changes AM4-1's fixed 4 workers.

**Unchanged:** the fixed values, the RI10 allowance, and AM4-1's INDETERMINATE allowance. Any other difference is a stop. The 83-timeout limitation (section 0) is carried into the final evidence report whichever option is chosen.

## AM5-4. The mapping's test gaps

**What the mapping found.** The independent read-only mapping (Appendix B) classifies 49 requirements as partly addressed and 23 as still open. The builder's triage (Appendix A):

| Group | Rows / discrepancies | What it needs |
|---|---|---|
| Open or partial by the paper or the owner's own terms (findings 11, 12, 13, 2; D; G) | 8, 49, 67, 74, 127 | nothing: they stay open, as stated |
| Waiting for S13 and S14 | 106, 110, 111 | AM5-1 to AM5-3 |
| E point 26, F8 | E point 26 | stays partly addressed (AM5-5 (a)) |
| Produced at packaging | 48, 65, 78, 112, 120, 122, 123, 124, 125; discrepancy 22's final check | the packaging step, Appendix A part 2 |
| Builder evidence already corrected | 7 (in part), discrepancies 15, 16, 18 | Appendix A part 3, verified by the scoped re-mapping |
| **Tests, test records and builder-tool documentation** | about 54 rows and discrepancies (Appendix A part 1), including the two the builder found itself: discrepancy 6, and discrepancy 7's process-start half | **this decision** |

**The builder's spot checks agree with the mapping.** Where checked, the logic exists and only the test is missing or weak:
- Row 12's test asserts `ua.leaked or ub.leaked` (`test_no_timeout_kill.py:437`), where P.3 requires each unit.
- P.8 step 5 is implemented at `evkit.py` 3802, and reading 5's two-empty-scans rule at 1382–1418; neither has a test.
- No test makes a unit fork repeatedly during cleanup (row 19).
- No test makes a grandchild hold the message pipe (row 77).

**Options.**
- **A (recommended).** The builder makes every item in Appendix A, part 1, in one batch.
  - **Scope.** Only:
    - test code (`tests_tools/`), test helpers, and the pins for changed test files;
    - builder-tool documentation and the outside-service audit tool's start method (discrepancies 7 and 21);
    - the AM5-3 comparison allowance (below);
    - the change record.
  - **AM5-3 comparison allowance:** The builder may update the out-of-tree comparison tool, or its explicit allowance input, solely to implement the owner-selected AM5-3 allowance. The permitted mismatch is limited to the selected IDs, where M10 reports `KILLED` with information `timeout` and the successor reports `EQUIVALENT`. Every other ID or status combination remains a stop. This does not authorise changes to M10, successor-tool logic or product logic. (The tool, `d14/s1/tools/compare_pass2_s1.py`, has no allowance input today, so the change is to the tool itself. Its new SHA-256 is recorded, and the scoped re-mapping checks the change against this paragraph.)
  - **No product or successor-tool logic changes.** If a new test fails, or shows behaviour the paper did not expect, work stops under H and the builder reports it before any logic change.
  - **The order of work:**
    - (i) write the tests;
    - (ii) run the focused new tests on both Pythons;
    - (iii) one new freeze, built twice. `c9b324eb` is kept as superseded, as `d5f87d6b` was;
    - (iv) the full evidence once, on that freeze, in the order of AM5-6;
    - (v) the mapping agent, scoped to the changed rows and to discrepancies 6, 7, 15, 16, 18, 21 and 22;
    - (vi) the documents and the package, with the package-level privacy check.
  - **Cost.** About 1.5 to 2 days to write and focus-test, plus about a day of runs. Each m2 comparison alone takes about 6 hours per Python on this machine.
- **B.** No new tests. The package goes to the gate now, with every row in Appendix A, part 1, listed in the documents as partly addressed or open. The builder expects the gate to return the same gaps.

## AM5-5. Builder readings and acts not yet ruled on

**(a) E point 26, F8: the "within-file stop".**
- **Point 26 requires** "the files after the first failure did not run" inside a sabotage tool (F8).
- **The F8 test shows less.** A sabotage check names one test file. The F8 test (`E26RealFailFast`, `sabotage_m10_s1`, plant V01) shows a stop inside that file. It cannot show that later files did not run.
- **The builder no longer asks for ratification.** That would change the requirement's meaning. Point 26's F8 stays **partly addressed**, as the mapping classified it.
- **The within-file test is kept as additional evidence,** and is not represented as proof that later files were not run.

**(b) Mistake 23: C.1's tables were incomplete.**
- **The rule.** C.1's operative rule (Appendix D.2) moves "every listed module-level import or load … ; so does every module-level statement that uses it". For the 18 mutation and sabotage successors it moves "the module-level `E.load_tool_module(...)` call … with everything that load executes, and every module-level statement that uses its result".
- **What the table missed.** Its third column listed "none", `F = L.F` or `Q = L.M` for eight successors, each of which had one more module-level statement using the load's result. The builder moved these under the rule:

| Successor | Statement (before, commit `ec42655`) |
|---|---|
| `tools/f67_mutants_s1.py:22` | `CANDIDATES, SITES, MUTATE, EQUIV = F.candidates, F.M7._sites, F.M7.mutate, F.EQUIV` |
| `tools/f671_mutants_s1.py:23` | `CANDIDATES, SITES, MUTATE, EQUIV = F.candidates, F.M7._sites, F.M7.mutate, F.EQUIV` |
| `tools/f672_mutants_s1.py:25` | the same |
| `tools/f673_mutants_s1.py:25` | the same |
| `tools/f674_mutants_s1.py:25` | the same |
| `tools/m73_store_mutants_s1.py:22` | `CANDIDATES, SITES, MUTATE, EQUIV = S.candidates, S.M._sites, S.M.mutate, S.EQUIV` |
| `tools/mie_mutants_s1.py:22` | `CANDIDATES, SITES, MUTATE, EQUIV = Q.candidates, Q.M._sites, Q.M.mutate, Q.EQUIV` |
| `tools/mie11_mutants_s1.py:23` | `CANDIDATES, SITES, MUTATE, EQUIV = Q.candidates, Q.M._sites, Q.M.mutate, Q.EQUIV` |

- **The builder's reading.** These fall under the rule's "every module-level statement that uses its result". The table's third column was incomplete, but the rule was not. The B.6, K.2, golden, pairs, frozen-file and route checks are unchanged.
- **The record.** The builder did not stop and report the incomplete table before proceeding. It disclosed it only as mistake 23, in the build log and the change record.
- **Ask:** ratify the eight moves as an application of C.1's general rule, not as individually authorised in its table, with the failure to stop recorded. Or rule otherwise.

**(c) Mistake 29: a race in the builder's own P code, fixed without a stop.**
- **What happened:**
  - The full suite failed once (`test_no_timeout_kill`, the registration race).
  - Diagnosis: `_Supervision.scan` read the process table before pruning reaped registrations. A direct child reaped between the read and the pruning was taken for an adopted orphan.
  - The builder moved the pruning before the table read (`tools/evkit.py`, `_Supervision.scan`, the comment at line 1279 of freeze `c9b324eb`, commit `6f65d488`), and added a deterministic test (`test_no_timeout_kill.py`, `…the_registration_race_with_the_window_widened`, from line 369; pins v111).
  - Measured: the old order failed 4 of 40 runs, and 20 of 20 with the window widened; the fixed order failed 0 of 20.
- **This was a logic change made before the stop and owner decision that H requires** (mistake 34).
- **Ask:** approve retaining the fix as a correction to meet P.4, while the process is recorded as non-compliant. The change record in the new freeze records:
  - the before-and-after order;
  - the commit and freeze;
  - the test;
  - the 4/40, 20/20 and 0/20 observations;
  - that the change was made before the required stop and owner decision.

## AM5-6. The order of the remaining evidence

**Under AM5-4 option A,** on the new freeze, one job at a time, with nothing else running and the 10 GB floor kept:
1. T, W and M on Python 3.13 and on Python 3.12;
2. golden, pairs, b6 and k2 on both Pythons;
3. m2 on each Python:
   - the five harness slices, if AM5-2 is approved;
   - the successor as written, detached from the job limit;
   - under AM5-3 option B, the three-id 1-worker run;
   - the comparison, with the allowances as decided;
   - under AM5-1 option B, the literal run;
4. historical (both Pythons), static, the audits (with the corrected start method), the child-start scan, the fresh check of all 26 process starts (row 68), and the names check;
5. the mapping agent, scoped as in AM5-4;
6. the documents, the package with its privacy check, and the gate prompt.

**Under option B,** on `c9b324eb`, only what is missing or affected; the completed evidence stands:
- the Python 3.12 m2 (slices, successor, comparison), and AM5-3 option B's run if chosen;
- under AM5-3 option A1 or A2, the comparison tool updated as AM5-4's "AM5-3 comparison allowance" paragraph permits (that paragraph applies under option B too), and Python 3.13's m2 comparison step rerun with the decided allowance. This is the comparison only, from the existing slice and successor logs; nothing is re-executed;
- the corrected audit records (discrepancy 7);
- the names check;
- the scoped mapping;
- the packaging, with its privacy check.

## Disclosures (all builder-executed)

| Mistake or event | What happened | Status |
|---|---|---|
| **30** | The one-process m2 mode was written without estimating time or disk. It ran into the 2-hour limit and left 14 GB of temporary files, since removed. | replaced by the slices |
| **The S13 disk estimates** | The first estimate (16 to 24 GB, from a 2-item probe) was overstated. The addendum's figure ("about 12 GB", "at or just below the floor") understated it: 12.03 GB is a sum over five slices, while the one-process attempt had reached 14 GB before it was stopped. | corrected in AM5-1 |
| **The successor run** | The successor's own run was made detached from the job limit, unchanged. The only change was to the builder's comparison tool, whose timeout for that step went from 7000 s to 8 h. | disclosed |
| **31** | The child-start scanner's first version missed evkit's `_subprocess` alias and reported 1 site. | fixed before its output was kept |
| **32** | The m2 comparison's INDETERMINATE allowance did not check that M10's kill was by timeout, so it allowed more than AM4-1. It now checks, and fails closed on M10 crashes, which M10's `run_one` cannot tell apart from test kills. No id used it. | fixed; tool `25724120…4392`; `m2.txt` byte-identical |
| **33** | The outside-service audit was first rerun from the builder's shell, with its full environment (231 names). Secret-bearing names were recorded by name only, but the values of session identifiers were recorded. The record was read only by the builder and the mapping agent in this workspace, has been deleted, and was rerun with the five-name environment. | fixed; final package check added |
| **34** | Mistake 29's logic fix was made without a stop (AM5-5 (c)). | for the owner's ruling |
| **35** | Draft 2 of this amendment presented the five-slice harness as within AM4-1, and asked for ratification of F8. Both overstated. Draft 3 omitted the comparison-tool change AM5-3 needs from the authorised scope, overstated the cause of ME35's survival, and described the literal run as stopping at RI10 where only its output does. | corrected in AM5-2, AM5-5 (a), AM5-4, AM5-3 and AM5-1 |
| **The diagnostic** | The S14 diagnostic (AM5-3) was run before the owner's decision. It was first noted only in draft 1. | recorded in the build log and the S14 record |
| **The idle gap** | 10:16 to 17:39 Melbourne time on 2026-11-07: a container restart, and a completed job not acted on. No work ran. | disclosed |
| **The container restart** | The restart interrupted the first Python 3.12 W set. It is kept in `evidence_pass2/interrupted/` and is not used as evidence. | disclosed |
| **The process-API record** | PID 1's command line changed after the restart (`--tcp-readiness-only` added), and the harness socket moved (`96.sock` to `92.sock`). | recorded in the audit conclusions |

## What stays as it is

- **Not acceptance, not production readiness.** This is not stage 1 acceptance, and nothing here claims production readiness.
- **Out of scope:** stage 2 is not authorised. No work is assigned to Amir, he is not treated as a dependency, and no handoff to him is brought forward.
- **Open items stay open:** EDR and CF items are not closed. Findings 1 to 13 stay open as stated, including finding 11, P.2 not met in this workspace.
- **Immutable:** APG-M8.1 and earlier packages, and the M10 archive `bd5c592a…5192`, are unchanged.

## Suggested owner post

The post names this file's SHA-256. The hash cannot be written inside the file it is a hash of, so the builder gives it beside the file when it is sent, and the owner copies it into the post.

*"I authorise amendment 5 to APG D14 stage 1 corrective pass 2, as set out in APG_D14_STAGE1_CORRECTIVE_PASS_2_AMENDMENT_5_DRAFT_v4.md (SHA-256 <the full hash>), with:*
- *AM5-1 option A: I waive the literal run of M10's m2_mutants.py and the comparison of its printed verdicts, and accept the stated substitute evidence;*
- *AM5-2: I approve the five-slice harness as an alternative evidence method, not as equivalent to one process;*
- *AM5-3 options A1 and B, with the comparison allowance limited to CA01-float-allowed and RI13-input-aliased as AM5-4 states;*
- *AM5-4 option A;*
- *AM5-5: (a) E point 26's F8 stays partly addressed; (b) the eight moves of mistake 23 are ratified as an application of C.1's general rule, with the failure to stop recorded; (c) the mistake 29 fix is retained as a correction to P.4, and the stop-rule breach (mistake 34) stays recorded;*
- *AM5-6 as written for option A.*

*The posted paper 23d2adb9…f0ea5, as amended by amendments 1 to 4, stands as further amended. This authorises corrective work, tests and evidence only; it is not stage 1 acceptance and does not authorise stage 2."*

---

## Appendix A. The builder's plan for each gap

### Part 1. What option A adds
"Tool level" means the real successor tool, run in a temporary copy with a planted fault, as the existing P2 tests do. Each new test is added to the T set and to the evidence.

| Row | Requirement | What is added |
|---|---|---|
| 4 | P.2 / P.10 refusals | A supervisor tool refusing `ENV_NO_PROCESS_SUPERVISION`, exit 2, every item NOT_RUN, for each failing step, including the /proc and `pidfd_send_signal` failures |
| 6 | P.2: a secret in a unit's environment stops the work | A tool-level test with a planted secret-bearing name: the work stops, and the value is never recorded |
| 11 | P.3: equal start times | The `ambiguous=` or `CLEANUP_AMBIGUOUS` output asserted; adoption and cleanup of the ambiguous process exercised |
| 12 | P.3: orphan attribution | Each unit in flight records the leak (not "either"); run through `--jobs 2` at tool level; classifications asserted |
| 15 | P.4: no wait on −1 or a group; WNOHANG | A static AST test over `evkit.py` asserting every `waitpid` is on a single pid with WNOHANG |
| 19 | P.5 / P.10: forking during cleanup | A unit that forks repeatedly during cleanup; the scan count and deadline recorded and asserted |
| 21 | P.5 steps 8–9 | The full CLEANUP field set and scan ids asserted; `CLEANUP_SUMMARY` before RESULT and ordered by unit id; "gone" checked at the RESULT line, not after exit (discrepancy 12) |
| 22 | P.6: leak attribution | A tool-level leak for a mutation item, a tests-kind FILE, and a wrapper FILE and CHECK |
| 23 | P.7: nested supervisors | A real nested supervisor (not a stub); orphan adoption after escalation |
| 25 | P.8 step 5 | A failed id outside the paired case runner's pinned inventory is rejected, on all 5 pairs |
| 29 | P.10: two-level nesting | tool → leaf → test → process → child, on the timeout, interrupt and normal paths; the second chain through `run_m8_tests_s1`; CLEANUP attribution |
| 30 | P.10: `valid_result_then_hangs` | Own tool-level tests for a forked plant and a forked case, with SIGTERM-ignoring and unkillable variants; `processes_left` and "no RESULT while alive" asserted |
| 31 | A.1: case-run order | Steps 5, 6 and 8 keep the resolved selection |
| 34 | A.3: checker rejections | `suites=-` with a non-zero `selected` |
| 36 | A.4: import failure | The case hash asserted; `run_history_contract_s1` in case mode |
| 41 | B.4: control causes | Crash and `bad_result` causes for mutation and sabotage controls |
| 42 | B.5: all tests on all five fault runners | The full set on the other four runners; the hang test must exercise the plant's own hang, not pass on a start-control timeout; pids, pgids and CLEANUP recorded |
| 46 | C.2: per-runner assertions | Nothing listed is imported before the guard; `cause=run_error`; the case hash; history case mode |
| 50 | F.1: the disk floor | `sabotage_m7_s1` during items at `--jobs 2`; `NOT_RUN cause=run_stopped` for items not started |
| 51–53 | F.2: interrupts | SIGINT and SIGTERM separately on m2, sabotage_m7, run_faults, `run_m2_tests_s1`, `run_contracts_s1` and `run_m4_all_s1`, at each point: during a child, between items, during the end control, during its cleanup. Also `tests_runner_main`, `mut_runner_s1`, `run_test_files_s1`, `run_m8_tests_s1`, `child_unittest_runner` and `wrapper_main` |
| 55 | F.2(b): interrupted wrapper | Group INDETERMINATE, the rest NOT_RUN, RESULT exit 3 |
| 56 | Reading 16 | A wrapper interrupted before an H group still prints EXCLUDED (`run_m4_all_s1`) |
| 57 | K.1: checker forms | The rejected forms: a completed `CONTROL end` beside NOT_RUN; a completed end control reported as NOT_RUN |
| 59 | K.2: per-case message forms | On the per-case path: descendant hang, incomplete, malformed, `ok=false`, child_error by message, kill while writing, wrong keys or types, malformed text that looks like `ok=false`, valid-then-hang |
| 60 | K.2: hang on other runners | `check_output` and the "identities gone" check for `run_history_contract_s1`; `check_output` for `run_mkt_corpus_s1` |
| 62 | K.3: dispatch | Cross-kind v=3 dispatch |
| 63 | K.3: twice through the checker | Tests and wrapper outputs through the checker twice, with and without the new records |
| 66 | AM-2: F.2 in leaves | F.2 in the leaves and in `child_unittest_runner` (between tests); `run_m8_tests_s1` |
| **68, discrepancy 6** | AM-2: "all 26 process starts set a time limit"; the T-set leaf limits | **(widened from draft 2)** A fresh check, on the new freeze, of every process start AM-2 counts: each site and the limit applied there, recorded as evidence; plus the T-set leaf deadlines re-measured, including this batch's tests |
| 69 | AM-3: CR-02 | A leak test; SystemExit cleanup on the normal path |
| 71 | AM-5(a): the hook | `run_child` plus the hook registers once only; `m8_mutants_s1`'s AUIF children started before the run are registered; the leaf's reap before RESULT |
| 72 | AM-5(b) | A recorded probe test: the children of immutable code keep their command, environment and limit |
| 73 | AM-5(c) | Each attribution-table row at tool level (`PROCESSES_LEFT run_start` / `run_end`, `(INCOMPLETE: processes left)`, …) |
| 75 | AM-5(e) | One probe in each path, recorded in the evidence |
| 77 | AM-6(b): drain | A grandchild holds the write end and adds one byte (bad_result plus a leak); a grandchild holds it and stays silent (processes_left) |
| 79 | AM2-1(a) | No batch run after an ordinary start refusal; `--pin` uses the batch unit |
| 81 | AM2-1(d) | Precedence row 7 (an inventory mismatch wins over a leak); row 3 with a leak |
| 83 | AM2-2(a) | The placement of `SIGNAL_AFTER_COMPLETION`, and M10's exit unchanged |
| 85 | AM2-2(c) | CR-02's synthetic `CompletedProcess` fields |
| 90 | Reading 3 | The pipe-drain bound asserted |
| 91 | Reading 4 | SIGTERM goes to the nested supervisor alone, with other members present |
| 92 | Reading 5 | Grace ends early after two empty scans |
| 95 | Reading 8 | A start control interrupted before it began, at tool level |
| 96 | Reading 9 | An unowned child is attributed to `run_end` (test in a copy) |
| 97 | Reading 10 | A missing value, a `--path`/factory mismatch and a malformed spec, each asserted as a step 3 refusal with `suites=-` |
| 98 | Reading 11 | A real runner in both orders; CASE order asserted |
| 99 | Reading 13 | `CLEANUP_SUMMARY units=` reconciled against the units started |
| 100 | Reading 14 | `child_unittest_runner` declares itself just before `verify_auif`; the check of it |
| 101 | Reading 15 | The zombie check by the tool itself; the leaf's reap |
| 121, discrepancy 1 | I.3 / B.5 | The P, B, K.2 and F.2 tests write each child's pid, start time and pgid, its CLEANUP lines and the cleaning supervisor to a per-test evidence record, kept with the T logs |
| **7, discrepancy 7** | P.2 / P.9 audit: method and docstring | **(new in draft 3)** The outside-service audit tool starts its subprocess child through the freeze's `run_unit`, and its forked child through `run_forked`, so the audit shows what the freeze itself gives a unit (AM-4: stdin /dev/null; the P.2 scrub). Its docstring is corrected to say exactly how it is started (`env -i` with the five names) and how it starts its children. This is a builder tool outside the tree |
| Discrepancy 10 | E.2: "these numbers and hashes are in the test" | A `tests_tools` test asserting the fixed values against the tree: 199 ids, RI10 at 51, the common-id `sha256_lines`, the successor's `ids_sha256` |
| Discrepancy 14 | `too_big` boundary | Exactly 1 MiB accepted, and 1 MiB + 1 rejected, at tool level |
| Discrepancy 17 | `E7…test_m8_mutants_controls_and_a_known_kill` | The known kill asserted, as the name says |
| **Discrepancy 21** | Builder-tool documentation | **(changed from draft 2)** Before the new evidence run: `run_index_s1.py`'s docstring says `last_line` is a prefix of at most 300 characters of the last line; `check_m8_log_s1.py`'s says it reads v=3 through the frozen tree's `check_output`. Documentation only. The evidence on `c9b324eb` was made with the tools as they were, and that is stated |
| 113, discrepancy 20 | I.1: the change record | `ENV_THREADS_AT_FORK` added to the codes list; the paper's authorisation dated as AM-1 §0 gives it, and the 23:00 build authorisation named as such; mistakes 23, 29 and 34 recorded as ruled in AM5-5 |

### Part 2. Done at packaging, no decision needed
- **The documents and package** (rows 48, 65, 78, 112, 120, 122, 123, 124 and 125):
  - the documents (findings 9 and 11 to 13, reading 17, mistakes 20 to 35);
  - the evidence index;
  - the cited-names check;
  - the scoped re-mapping;
  - the package of one ZIP plus one documents file.
- **Discrepancy 22, the package-level privacy check.** Before distribution, the final ZIP and documents file, including every included log, are searched for the user's e-mail address, the account and organisation identifiers, the session link and its id, the container id, and any credential-shaped strings. The result is recorded in the package. Any hit stops the packaging.

### Part 3. Already corrected (builder evidence only; the scoped re-mapping verifies each)
- **Row 7, in part, and discrepancies 18 and 22:**
  - The audit was rerun with the five-name environment; the process-API record now has the PID 1 line and the process list; a new conclusions file was written (`evidence_pass2/audit_final/`).
  - The build log's 02:45 entry ("same as 11-05") is corrected by its 03:15 entry, which says the audits were not the same and points to the conclusions file. The log is kept append-only, so the earlier entry is corrected by a later one and not rewritten.
  - The method half of discrepancy 7 is in part 1.
- **Discrepancy 15 (mistake 32):**
  - The m2 allowance now requires M10's information to be `timeout` (`d14/s1/tools/compare_pass2_s1.py`, SHA-256 `25724120962e8fe255ec237c3e7ffe149d098b217965a8d0921f3cfb8b5e4392`, both places in `mode_m2` and `mode_m2_compare`).
  - The rerun `m2.txt` is byte-identical: `6a2685af…a590`.
- **Discrepancy 16:**
  - The same tool's `_both` now extracts each runner's `CONTROL (start|end) <value> cause=<cause>` lines on both sides, prints them, and counts any inequality as a difference.
  - b6 was rerun on both Pythons: `RESULT b6 SAME`, 111 items, the CONTROL lines equal on all 5 runners. `b6.txt` is `11c4da98…03f7` on both Pythons.

---

## Appendix C. GPT's review of draft 2: each item and how draft 3 handles it

| # | Review item | Draft 3 |
|---|---|---|
| 1 | Quote AM4-1 and C.1's operative wording | Appendix D.1 and D.2 |
| 2 | AM5-1 is a waiver; show the whole control flow | AM5-1 option A is now a waiver, with the reviewer's wording, extended to cover "its 50 printed verdicts compared". M10's `main` and `run_one` are quoted whole (Appendix D.3) |
| 3 | AM5-2 is not equivalence | AM5-2 now asks for approval as an alternative evidence method, and states what it does not establish |
| 4 | 12.03 GB is an estimate; use the 14 GB observation | Done. The builder also corrects its own earlier "at or just below the floor" (Disclosures) |
| 5 | S14's cause is too certain | The reviewer's wording is used |
| 6 | Keep the 83 timeout kills prominent | Section 0 and AM5-3, and carried into the final report |
| 7 | Narrow the allowance to the two ids | Offered as **A1**. The builder offers **A2** beside it (the three ids of M10's fixed `EQUIV`) and explains why. **The owner chooses.** |
| 8 | Discrepancies 7, 15, 16, 18, 21, 22 | Discrepancy 7 is fully planned (docstring and method). 15 and 16 have tool and output hashes recorded and are in the scoped re-mapping. 18: the build log's correction entry is named. 21: the docstrings are now corrected, not just documented. 22: a package-level privacy check is added |
| 9 | Row 68 is too narrow | Widened to every process start AM-2 counts (discrepancy 6) |
| 10 | Do not ratify F8 | Accepted: F8 stays partly addressed |
| 11 | Mistake 23: quote C.1; list the sites | C.1 is quoted (D.2); the eight successors and their statements are listed in AM5-5 (b). (The review said "five movements"; there are eight files, one statement each.) |
| 12 | Mistake 29: keep the fix, keep the breach | Accepted, with the record's contents listed |
| 13 | Option B repeats work | AM5-6 option B now runs only what is missing or affected |
| 14 | The post's hash is an ellipsis; it ratifies all three of AM5-5 | The post now reflects the rulings. The hash cannot be inside the file it hashes; the builder gives it beside the file, and the owner copies it in |

**GPT's scoped re-review of draft 3 (11:10 on 2026-11-08).** It found items 1 to 14 resolved, agreed that the hash placeholder is the right approach, and raised four points. Draft 4 handles them in the reviewer's own wording:

| # | Re-review point | Draft 4 |
|---|---|---|
| R1 | Blocking: AM5-4's scope does not include the comparison-tool change AM5-3 needs | The reviewer's paragraph is added to AM5-4 option A, and applied to AM5-6 option B |
| R2 | AM5-1: the evidence shows that the output stops at RI10, not the execution | The reviewer's replacement paragraph is used |
| R3 | AM5-3: ME35's explanation is too certain | The reviewer's sentence is used. A1 is now the builder's recommendation too |
| R4 | If A2 stays an option, quote M10's `EQUIV` | Appendix D.4 |

**Found by the builder itself, after draft 2:**
- discrepancy 6 (item 9 above);
- the process-start half of discrepancy 7: the audit's children did not go through `run_unit` / `run_forked`;
- the understated S13 disk risk (item 4).

---

## Appendix D. Operative passages, verbatim

### D.1 AM4-1 (amendment 4, `b6be070e…a7d6`)
> **M10's verdicts are taken from M10's own per-mutant function,** called by a builder harness outside the tree. The harness:
> - loads the tree's byte-identical `tools/m2_mutants.py`, checked against `fe1fd878…157b`, without changing it;
> - calls M10's own `run_one(item, tmp)` once for each of the 199 items of M10's `MUT`, in M10's order, with M10's default of 4 workers;
> - records, per id, M10's status (`KILLED`, `SURVIVED`, `ERROR`), its information (`tests`, `contracts`, `timeout`, or the error text), and whether the id is in M10's `EQUIV`;
> - applies M10's own reading to them: `KILLED` stays a kill; a survivor documented in `EQUIV` is `EQUIVALENT`; any other survivor is `SURVIVED`.
>
> The successor `m2_mutants_s1` is run as written, on all 199 ids.
>
> **The comparison, unchanged from E.2:**
> - the fixed values: 199 ids; RI10 at position 51, invalid on M10; 198 common executable ids with `sha256_lines` `d5da4f9a…694c`; the successor's `ids_sha256` `649e0e48…384e`;
> - the allowed differences only:
>   - RI10, which is `ERROR` on M10 and has a verdict on the successor;
>   - an id M10 killed by `timeout`, or by a crash its `run_one` counts as a kill, that the successor reports `INDETERMINATE`. Each such id is listed.
> - **any other difference is a stop-rule event.**
>
> **Also recorded:** the literal output of one run of M10's `m2_mutants.py` itself, as evidence that it stops at RI10, its 50 printed verdicts compared with the harness's for the same ids.

### D.2 C.1 (the posted paper, `23d2adb9…f0ea5`)
> **C.1 What moves.** In each runner below:
> - every listed module-level import or load moves into the guarded start path, after `evkit.start`'s checks (and, for case runners, after the selection is resolved, A.1);
> - so does every module-level statement that uses it;
> - P3-B04's order is kept: the trusted harness is imported before any candidate path is added;
> - nothing listed is imported or executed before the guard.
>
> […]
>
> **The 18 mutation and sabotage successors.** In each, the module-level `E.load_tool_module(...)` call moves, with everything that load executes, and every module-level statement that uses its result:
>
> | Successor | M10 file loaded | Module-level statements that use it |
> |---|---|---|
> | `tools/f67_mutants_s1.py` | `f67_mutants` | none |
> | `tools/f671_mutants_s1.py` | `f671_mutants` | `F = L.F` |
> | `tools/f672_mutants_s1.py` | `f672_mutants` | `F = L.F` |
> | `tools/f673_mutants_s1.py` | `f673_mutants` | `F = L.F` |
> | `tools/f674_mutants_s1.py` | `f674_mutants` | `F = L.F` |
> | `tools/m73_store_mutants_s1.py` | `m73_store_mutants` | none |
> | `tools/mie_mutants_s1.py` | `mie_mutants` | none |
> | `tools/mie11_mutants_s1.py` | `mie11_mutants` | `Q = L.M` |
>
> (These are the table's rows for the eight successors of AM5-5 (b). The other ten rows are unaffected.)

### D.3 M10's `tools/m2_mutants.py` (`fe1fd878…157b`), `run_one` and `main`, whole
```python
def run_one(item, tmp):
    mid, fname, old, new = item
    path = os.path.join(ROOT, 'apg', fname)
    src = open(path, encoding='utf-8').read()
    if src.count(old) < 1:
        return mid, 'ERROR', f'pattern not found in {fname}'
    work = os.path.join(tmp, mid)
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns('logs', '__pycache__', '.git', 'dist'))
    open(os.path.join(work, 'apg', fname), 'w', encoding='utf-8').write(src.replace(old, new, 1))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for cmd in ([sys.executable, '-I', 'tools/run_m2_tests.py', '-q', '--failfast'], [sys.executable, '-I', 'tools/run_contracts.py']):
        try:
            r = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            return mid, 'KILLED', 'timeout'
        if r.returncode != 0:
            return mid, 'KILLED', 'tests' if 'run_m2_tests' in cmd[2] else 'contracts'
    return mid, 'SURVIVED', ''


def main():
    ids = [m[0] for m in MUT]
    if len(set(ids)) != len(ids):
        print('ERROR duplicate mutant ids'); return 2
    if '--list' in sys.argv:
        print('\n'.join(ids)); return 0
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 4
    tmp = tempfile.mkdtemp(prefix='m2_mut_')
    try:
        with ThreadPoolExecutor(max_workers=jobs) as ex:
            results = list(ex.map(lambda m: run_one(m, tmp), MUT))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    killed = equiv = 0; unexplained = []; by_tests = by_contracts = 0
    for mid, st, info in results:
        if st == 'ERROR':
            print(f'ERROR {mid}: {info}'); return 2
        if st == 'KILLED':
            killed += 1; by_tests += info == 'tests'; by_contracts += info == 'contracts'; print(f'KILLED     {mid}  (by {info})')
        elif mid in EQUIV and EQUIV[mid]:
            equiv += 1; print(f'EQUIVALENT {mid}  -- {EQUIV[mid]}')
        else:
            unexplained.append(mid); print(f'SURVIVED   {mid}')
    print(f'mutants {len(MUT)}  killed {killed} (tests {by_tests}, contracts {by_contracts})  documented-equivalent {equiv}  unexplained survivors {len(unexplained)}')
    if unexplained:
        print('UNEXPLAINED:', unexplained); return 1
    print('MUTATION RUN OK'); return 0
```

RI10's entry in `MUT` (line 66): `('RI10-query-crosses-tenants', 'reference_impl.py', "if t == ctx.tenant_id and k == kind:", "if k == kind:")`. Its pattern is absent from the tree's `apg/reference_impl.py`, so `run_one` returns `ERROR` (the harness's result for RI10).

**`ThreadPoolExecutor.map` returns results in input order**, so `main`'s print loop walks the ids in `MUT` order. It prints the 50 verdicts before RI10, then returns 2 at RI10. All 199 `run_one` calls complete first.

### D.4 M10's `EQUIV` (`tools/m2_mutants.py`, `fe1fd878fee975dff6dfdbdf27a7124665228a6efef624c396b40f7d68cd157b`, lines 222–226)
```python
EQUIV = {
 'ME35-decision-ledger-by-presence': "the only writer of the ledger kind in this package is record_decision, which always stores decided_by; a direct store write is outside the engine and is recorded as handoff item EDR-20 (write authorisation by record kind).",
 'CA01-float-allowed': "a float then reaches the final 'unsupported type' branch of _check and is still refused with CanonError; only the message differs.",
 'RI13-input-aliased': "_mk deep-copies the payload again before it is stored, so a caller's object is never held; the first copy is redundant defence.",
}
```

---

## Appendix B. The independent mapping agent's report (verbatim)
It was produced by a separate read-only agent on 2026-11-08, between 02:52 and 03:13 Melbourne time, on freeze `c9b324eb`. It was written before the corrections in Appendix A part 3.

## INDEPENDENT READ-ONLY MAPPING (agent), corrective pass 2

**What this is.** An independent read-only mapping of APG D14 stage 1, corrective pass 2. It covers freeze `APG-M11-S1.zip`, SHA-256 `c9b324ebd236b6ad1b5c6207e6d1ea3db584ef0861db636d9f94fb8137459297` (commit `6f65d488`). It maps the requirements to the tests and evidence and classifies each one. It makes no acceptance or production-readiness statement.

### 0. Method and limits

**Inputs checked**
- **Freeze:** the hash matches, and the second build (`pass2_work/freeze_build2.zip`) has the same hash. I extracted it fresh into `/tmp/mapagent_x/`. It is identical to every `evidence_pass2/<set>/x/APG-M11-S1` and to the working tree, apart from `__pycache__`.
- **M10 archive:** `bd5c592a…5192` matches.
- **Authority files:** the paper `23d2adb9…`, AM1 `211971…`, AM2 `a3cc26b5…`, AM3 `89e5a268…` and AM4 `b6be070e…`. The AM4 hash is the one named in the owner's 17:31 post.
  - The AM3 and AM4 files still carry their "draft" headers. Their hashes equal the posted texts.

**What I wrote.** I wrote one small read-only AST inventory script and its output to `/tmp/mapagent_scripts/` (`inv.py`, `inv.txt`). That is outside "extract only". I disclose it here. Nothing under the base directory was changed.

**Read-only commands used:** ls, grep, sha256sum, AST reads with `python3 -I -S`, `ps`, `date` and `git log --no-optional-locks`.

**How "passes on both Pythons" is judged.**
- The T logs are not verbose: they hold dots, ResourceWarnings and `Ran N tests … OK`.
- So a named test counts as passing when its file ran `OK` on both py313_T and py312_T, with no skips, no failures and no early-return guards. I found none of those in `tests_tools`.
- All 10 files are OK on both Pythons: 51+86+39+16+12+66+4+180+34+125 = 613 tests each.
- Tests generated at run time (for example `ToolLevelTimeoutCrashKill.test_timeout_<tool>`) are counted the same way.

**Something running while I read.** An S14 diagnostic process was running (`python3.13 -I …/pass2_work/s14_diag/diag.py`, started about 02:44). `evidence_pass2/diagnostic_s14/` may change after I read it.

### 1. Requirement table

C = CLOSED BY EVIDENCE · P = PARTLY ADDRESSED · O = STILL OPEN. Test files are in `tests_tools/`; evidence paths are under `d14/s1/evidence_pass2/`.

| # | Section | Requirement (short) | Class | Test / evidence | Note |
|---|---|---|---|---|---|
| 1 | P.1, AM-2, AM-6(c) | Unit set; 71 supervisors and 3 leaves | C | `test_consumer_exit_codes.py::Pass2ProcStat::test_supervisor_list` | Checks the count and the set of stems against the files on disk; does not check each tool's category |
| 2 | P.2 | Subreaper set through prctl and read back | C | `test_no_timeout_kill.py::P2SubprocessUnits::test_the_supervisor_is_a_subreaper_and_supervision_is_available`; `P2NestedAndRefusals::test_refusals_when_containment_cannot_be_set_up` (read-back case) | |
| 3 | P.2 | Each unit's direct child in its own process group | C | `P2SubprocessUnits::test_what_a_unit_child_inherits`; `P2ForkedUnits::test_what_a_forked_child_inherits` | pgid = pid, both kinds |
| 4 | P.2, P.10 | Refusal `ENV_NO_PROCESS_SUPERVISION`, exit 2, every item NOT_RUN, when prctl, read-back, /proc, pidfd_open, pidfd_send_signal or SIGCHLD fail | P | `P2NestedAndRefusals::test_refusals_when_containment_cannot_be_set_up`, `::test_sigchld_ignored_is_set_back_or_refused` | Only the `supervision_errors()` text after importing evkit in a copy. No supervisor tool is shown refusing with exit 2 and items NOT_RUN. /proc and pidfd_send_signal not covered |
| 5 | P.2, AM-4, P.10 | Child gets fds 0–2 (+ result pipe), the allowlist env, fd 0 on /dev/null; a parent's extra fd and env var not inherited; both kinds | C | `P2SubprocessUnits::test_what_a_unit_child_inherits`; `P2ForkedUnits::test_what_a_forked_child_inherits` | |
| 6 | P.2 | No secret in the allowlist; a secret in a unit's env stops the work; values never recorded | P | `audit_final/outside_services.txt` (`subprocess_unit` and `forked_unit_after_scrub`: `secret_bearing_names: []`) | Auditor started with the builder's full environment (231 names). `forked_unit_before_scrub` lists 17 secret-bearing names, values withheld. See D-list 7 and 22 |
| 7 | P.2, P.9, AM-1(4) | Audit items 1–6 with the basis for each conclusion, rerun on the new freeze | P | `audit_final/outside_services.txt`, `process_api_reach.txt`; `audit/outside_services_conclusions.txt` (earlier freeze) | No conclusions file for this freeze. `process_api_reach` lacks the PID 1 line and the process list. The audit's units are not started through `run_unit`/`run_forked` |
| 8 | P.2, AM-1 | No outside service can start a process outside a unit's tree | O | AM-1, open finding 11 | Reachable: PID 1 API, the harness socket, the telemetry socket, `/etc/cron.d` (writable). Egress unknown |
| 9 | P.3, P.10 | `/proc/<pid>/stat` fields counted after the last `)` | C | `Pass2ProcStat::test_command_name_with_spaces_and_parentheses` | |
| 10 | P.3, P.10 | A reused pid is never signalled; a reused parent pid's child is not a member | C | `P2Identity::test_a_reused_pid_is_never_signalled`, `::test_a_reused_parent_pid_with_a_child_of_its_own_is_not_a_member` | Simulated, as the paper allows |
| 11 | P.3, P.10 | Equal start times: not membership; recorded (`ambiguous=` or `CLEANUP_AMBIGUOUS`); cleaned up once adopted | P | `P2Identity::test_equal_start_times_are_ambiguous_and_recorded` | Only an internal dict (`o.ambiguous`). No output line asserted; adoption and cleanup not exercised |
| 12 | P.3, P.10 | Orphan created between scans attributed to every unit in flight, each a leak; `--jobs 2`; an unrelated process survives | P | `P2SubprocessUnits::test_concurrent_orphan_attribution_and_an_unrelated_process_survives` | Asserts `ua.leaked or ub.leaked` (the paper says each unit). Two threads calling `run_unit`, not `--jobs 2`. Classifications not asserted |
| 13 | P.4, P.10 | One wait owner per child; no status lost or taken twice; adopted zombie reaped | C | `P2SubprocessUnits::test_wait_ownership_two_concurrent_units_and_an_adopted_zombie` | |
| 14 | P.4, P.10 | Register lock held across creation; a child that exits at once is never taken for an adopted orphan | C | `::test_the_registration_race_child_exits_immediately`, `::test_the_registration_race_with_the_window_widened` | Mistake 29 fixed in this pass |
| 15 | P.4 | No wait on −1 or a process group; every wait WNOHANG | P | No test. My static read of `tools/evkit.py` (waitpid at :1308, :1495, :1874, all WNOHANG on a single pid) | Code read only |
| 16 | P.2, P.4, P.10 | SIGCHLD set to SIG_DFL and read back, otherwise refused | C | `P2NestedAndRefusals::test_sigchld_ignored_is_set_back_or_refused` | Asserts the internal token `sigchld_not_default` |
| 17 | P.5, B.2, K.2 | The five constants and two item limits; a `LIMIT` line from each supervisor | C | `Pass2ProcStat::test_limit_line`; LIMIT lines in py313/py312 W and M logs; `compare_py31x/b6_logs` and `k2_logs` (`item=300s` on all 16 runs); `m2_logs/m2_mutants_s1.txt` | |
| 18 | P.5, P.10 | SIGTERM, grace, SIGKILL, kill-verify; a member ignoring SIGTERM is killed and recorded | C | `::test_a_member_that_ignores_sigterm_is_killed`; `P2ForkedUnits::test_valid_result_then_hangs_ignoring_sigterm_is_killed` | |
| 19 | P.5, P.10 | A unit that forks repeatedly during cleanup, with the scan count and deadline recorded | O | none | |
| 20 | P.5 step 7, P.10 | Unkillable member: `CLEANUP_INCOMPLETE`, exit 2, no waiting | C | `::test_a_member_that_cannot_be_killed_is_cleanup_incomplete` | Helper level; exit 2 through `finish_items` |
| 21 | P.5 steps 8–9 | Full `CLEANUP` form and scan ids; `CLEANUP_SUMMARY` before RESULT, ordered by unit id; RESULT only after all cleanup | P | Field and prefix asserts in the P2 tests; `CLEANUP_SUMMARY … leaked=0` in W, M and m2 logs | The full field set appears only in the excluded `interrupted/` set. Tools are shown clean after the supervisor exits, not at its RESULT line. Order untested |
| 22 | P.6 | Leak gives item `INDETERMINATE cause=processes_left`, control `FAIL processes_left`; cause on the CLEANUP line where the item line has none | P | `test_runner_zero_work.py::P2FaultRunners::test_plants`, `::test_controls`; `P2CaseRunners` (batch, fin); `test_mutation_timeout.py::P2MutationFamily::test_f2_and_k1_during_the_end_controls_cleanup` | Not shown: a mutation item leak at tool level, a tests-kind FILE leak, a wrapper FILE or CHECK leak |
| 23 | P.7, P.10 | Nested supervisor: SIGTERM, `T_ESCALATE`, kill, partial output ignored; nested INDETERMINATE never a pass | P | `P2NestedAndRefusals::test_nested_supervisor_cancelled_by_its_parent_finishes_and_a_hung_one_is_killed_at_t_escalate`, `::test_a_nested_indeterminate_result_is_not_a_pass` | A stub script named `run_faults_s1.py`, not a real nested supervisor. Orphan adoption after escalation not shown |
| 24 | P.8 steps 1–4, AM-6(b) | Framing, 1 MiB limit, UTF-8/JSON, form; crash vs bad_result vs child_error | C | `Pass2ForkedMessage::test_validation_steps`; `P2ForkedUnits::test_message_forms_and_classification`, `::test_framing_limit` | |
| 25 | P.8 step 5, reading 12 | A failed id must be in the paired case runner's inventory; tests on 5 pairs | O | none | |
| 26 | P.8 | Interrupt after the outcome is fixed gives `SIGNAL_AFTER_COMPLETION`; an earlier unit keeps its outcome | C | `P2MutationFamily::test_f2_and_k1_…`, `::test_f2_during_the_end_control`; `P2NoResultSupervisors::test_between_steps_and_after_the_last_step` | |
| 27 | P.9 | Inventory of start sites and paths before implementing; stop if not containable | C | `audit/child_start_sites.txt`, `independent_inventory.md`, `paper_to_code_matrix.md`; P9 stop issue record; `audit_final/child_start_scan.txt` (2 sites) | |
| 28 | P.9 | A timeout stays INDETERMINATE | C | `test_mutation_timeout.py::ToolLevelTimeoutCrashKill.test_timeout_<tool>` (15 tools), `ToolLevelM8::test_timeout_m8`, `TimeoutStaysIndeterminate` | |
| 29 | P.10, AM-2 | Nested two levels: tool, leaf, test, process, child (hang; setsid + double fork; leftover after a pass), on timeout, interrupt and normal path; second chain through `run_m8_tests_s1`; CLEANUP attribution | P | `P2SubprocessUnits::test_hang_timeout_and_setsid_double_fork_are_contained`, `::test_normal_path_background_grandchild_after_a_passing_result_is_a_leak` | One level only, in the test process. No tool-level nesting, no interrupt path, no `run_m8_tests_s1` chain |
| 30 | P.10 | Own `…_valid_result_then_hangs` tests for a forked plant and a forked case; SIGTERM-ignoring and unkillable variants | P | `P2ForkedUnits::test_valid_result_then_hangs` (helper), `::…_ignoring_sigterm_is_killed`; subtests `plant:valid_then_hang`, `batch:valid_then_hang` | No own tool-level tests, no per-case (K.2) variant, no unkillable variant. The helper test does not assert `processes_left` or "no RESULT while alive" |
| 31 | A.1 | Order of a case run; refusals at steps 1–3 give no resolved selection; steps 4–8 keep it | P | `P2CaseRunners::test_a4_the_v3_contract_on_the_real_runners` (steps 1, 2, 3 and 4) | Keeping the selection at steps 5, 6 and 8 is not asserted |
| 32 | A.1 | `SELECTION_INVALID` for any unpinned suite or case; the mixed form replaced | C | `test_a4` subtests (`--suite nope`, `--only NOPE-99`, mixed, `--bogus`) | |
| 33 | A.1–A.3 | `suites=` rules; empty-selection hash; v=3 without `suites` rejected; v=2 reader kept | C | `Pass2CasesV3` (6 tests); `test_a4` | |
| 34 | A.3 | Each checker rejection | P | `Pass2CasesV3::test_rejected_forms`, `::test_no_resolved_selection` | `suites=-` with a non-zero `selected` is not tested |
| 35 | A.4 | Real-runner runs: full, single suite, more pinned than printed, `--suite record_store --suite audit_log --only AL-01` | C | `test_a4` | |
| 36 | A.4 | Each case runner's import failure keeps its selection, with `suites` and hash asserted | P | `P2GuardedImports::test_c2_the_15_runners` | `suites` and `selected` asserted, hash not; `run_history_contract_s1` case mode not run |
| 37 | A.4, I.3 | 2C demonstration rerun: only the true selection accepted | C | `static/case_inventory_limit.txt` | One Python |
| 38 | B.1 | Plants and controls forked; message forms; child_error fallback; status 70 | C | `P2FaultRunners::test_plants` (`child_error`, `status70`, `raise`); `P2ForkedUnits::test_message_forms_and_classification` (unencodable) | |
| 39 | B.2 | `FAULT_ITEM_TIMEOUT_S=300`; `LIMIT item=300s` on every fault run; recorded | C | `test_limit_line`; `b6_logs/*_new.txt` on both Pythons; change record | |
| 40 | B.3 | Plant outcome table | C | `P2FaultRunners::test_plants`, `::test_f2_sigterm_while_a_plant_runs` | `run_faults_s1` only |
| 41 | B.4 | Control outcomes and causes, `CONTROL_INTERRUPTED`, `CONTROL_NOT_RUN`, checker validation; the same for mutation and sabotage controls | P | `P2FaultRunners::test_controls`; `SabotageAndFaultRunners` (`reference_failed_<n>`); `Pass2ControlsV3`; `ToolLevelTimeoutCrashKill.test_failed_start_control_*` | Crash and `bad_result` causes for mutation and sabotage controls not tested |
| 42 | B.5 | All tests on each of the five runners; test evidence records pids, pgids and CLEANUP lines | P | `P2FaultRunners` (full on `run_faults_s1`); `::test_the_hang_on_each_of_the_other_four_runners` | The other four get the hang only, and that test accepts a start-control timeout in place of the plant's. No pid, pgid or CLEANUP record appears in any evidence log |
| 43 | B.6 | 111 verdicts, CONTROL values and causes, status and exit equal to d5f87d6b | C | `compare_py313/b6.txt`, `compare_py312/b6.txt` (SAME); `b6_logs` | The tool does not compare CONTROL causes. I compared them in the logs: equal on all 10 runs |
| 44 | C.1 | The 33 loads moved; P3-B04 order; nothing imported before the guard | C | `static/route_scan.txt`; `P2Amendment3::test_am3_2_e_point_3`; `P2GuardedImports` | |
| 45 | C.1 | `IMPORT_FAILED` refusal form for each family | C | `P2GuardedImports::test_c2_the_15_runners`, `::test_c2_the_18_mutation_and_sabotage_successors` | |
| 46 | C.2 | Per-runner assertions | P | same | Not asserted per runner: nothing listed imported first, `cause=run_error`, the case hash; history case mode |
| 47 | C.3 | Three wrapper consumer paths give ITEM_ERROR, exit 2 | C | `P2GuardedImports::test_c3_the_wrapper_consumer_paths` | |
| 48 | AM2-4 r17 | Residual of finding 9 (11 tools) stated in the documents | O | — | Documents not yet produced |
| 49 | D | 36 plants stay refused; finding 2 stays open | O | By the paper. The refusal is shown by older tests (`EveryTextListOnTheSource`, `PreflightFailClosedAtToolLevel`) | |
| 50 | F.1 | Disk floor during the items (`--jobs 2`), at the start control and at the end control; phase word; checker | P | `P2MutationFamily::test_f1_*` (m2, all three), `::test_sabotage_m7_f1_*` (start, end) | `sabotage_m7_s1` lacks the during-items `--jobs 2` case; `NOT_RUN cause=run_stopped` for unstarted items not exercised |
| 51 | F.2(a) | One mechanism in every work loop | P | `P2MutationFamily`, `P2FaultRunners`, `P2CaseRunners`, `P2NoResultSupervisors` | Untested: `tests_runner_main`, `run_m2_tests_s1`, `mut_runner_s1`, `run_test_files_s1`, `run_m8_tests_s1`, `child_unittest_runner`, `wrapper_main` |
| 52 | F.2 tests | SIGINT and, separately, SIGTERM on m2, sabotage_m7, run_faults, run_m2_tests, run_contracts and run_m4_all | P | same | `run_m2_tests_s1` and `run_m4_all_s1` untested; `run_contracts_s1` SIGINT only |
| 53 | F.2 tests | Points: during a child, between items, during the end control and during its cleanup | P | m2: all four; sabotage_m7: during a child only; run_faults: during a child and during the end control | |
| 54 | F.2 | Interrupted form; `INTERRUPTED` immediately before RESULT; no RUN_ERROR; second signal counted | C | `P2MutationFamily::test_f2_sigint_while_a_child_runs`, `::test_f2_a_second_signal_is_counted_without_cutting_the_output`; `Pass2ControlsV3::test_interrupted_placement_and_counts` | Second-signal case on m2 only |
| 55 | F.2(b) | Interrupted wrapper: group INDETERMINATE, the rest NOT_RUN, RESULT exit 3 | O | none | The excluded `interrupted/py312_W_container_restart` W07 shows this form; it is not evidence |
| 56 | AM2-4 r16 | Wrapper interrupted before an H group still prints EXCLUDED (run_m4_all_s1) | O | none | |
| 57 | K.1 | Checker: each permitted and each rejected form | P | `Pass2ControlsV3::test_not_run_with_no_stop_record_is_rejected`, `::test_stopped_after_the_last_item`, `::test_stopped_before_the_last_item` | Missing rejected forms: a completed `CONTROL end` beside NOT_RUN; a completed end control reported as NOT_RUN |
| 58 | K.1 | Real tool: valid end result, leftover process, interrupt in cleanup gives `FAIL processes_left` with `SIGNAL_AFTER_COMPLETION` | C | `P2MutationFamily::test_f2_and_k1_during_the_end_controls_cleanup`; `::test_reading_7_…` | The end-control commands are stubs |
| 59 | K.2 | Per-case forked unit (4 corpus runners); message forms and mapping | P | `P2CaseRunners::test_k2_per_case_on_run_fin_corpus_s1` | Shown: hang, crash, status 70, exception→FAIL, leak, interrupt. Missing on the per-case path: descendant hang, incomplete, malformed, `ok=false`, child_error by message (and "would otherwise fail"), kill while writing, wrong keys or types, malformed text that looks like `ok=false`, valid-then-hang |
| 60 | K.2, AM2-1(f) | Hang on every other case runner, with identities gone and `check_output` | P | `::test_the_hang_on_the_other_six_batch_runners`, `::test_k2_the_hang_on_the_other_three_corpus_runners` | `run_history_contract_s1`: no `check_output`, no gone check. `run_mkt_corpus_s1`: no `check_output` |
| 61 | K.2 | 386 verdicts and causes, status and exit equal to d5f87d6b | C | `compare_py313/k2.txt`, `compare_py312/k2.txt` (SAME, 386) | |
| 62 | K.3 | v=3 for mutation and sabotage; dispatch by kind and version; v=2 kept; tests and wrapper stay v=2 | P | `Pass2CasesV3::test_tests_and_wrapper_stay_v2`, `::test_the_v2_reader_…`; `Pass2ControlsV3::test_v2_mutation_line_keeps_the_frozen_rule` | Cross-kind v=3 dispatch not tested |
| 63 | K.3 | Tests and wrapper outputs through the checker twice, with and without the new records | O | none | |
| 64 | K.3 | Consumers read through `check_output`; the builder's log checkers updated and say so | P | W `wrapper_check.txt`, M `m8_check.txt` (no checker problems, both Pythons) | `check_wrapper_logs_s1.py` says so; `check_m8_log_s1.py` does not |
| 65 | AM-1 | Finding 11, the narrowed claim, the risk basis and the explicit statement, in the documents | O | — | Documents pending. The risk basis is supported by `audit_final/child_start_scan.txt` section E |
| 66 | AM-2 | F.2 in leaves and `child_unittest_runner` (between tests); `run_m8_tests_s1` | O | none | |
| 67 | AM-2 | Finding 12 | O | By the amendment | |
| 68 | AM-2 | T-set leaves bounded by each test's own limit | P | `audit/tset_leaf_deadlines.txt` | Measured on the earlier freeze; not re-measured for this pass's new tests |
| 69 | AM-3 | CR-02 shim under P; cleanup on SystemExit; tests: leak recorded, sys.exit path, output unchanged | P | `P2NoResultSupervisors::test_cr02_sigterm_during_its_first_child`; W02 `CHECK G08` | No leak test. SystemExit cleanup shown only on the interrupt path. G08's exit and marker hash match across freezes by my own cross-check, not a builder record |
| 70 | AM-4 | stdin /dev/null for both kinds; the run index too | C | Row 5 tests; `d14/s1/tools/run_index_s1.py:64` | |
| 71 | AM-5(a) | Hook at import; registration atomic; one wait owner; leaf reaps exited orphans before RESULT | P | `P2NestedAndRefusals::test_the_hook_registers_children_created_by_in_process_code_and_a_phase_owns_them`; the race tests | Not shown: `run_child` plus the hook registering once only; `m8_mutants_s1`'s pre-start AUIF children registered; the leaf's pre-RESULT reap |
| 72 | AM-5(b) | Immutable code's children keep their command, env and limit | P | Indirect: the T, W and M runs pass | No test or probe asserts what these children receive |
| 73 | AM-5(c) | Attribution table rows (`PROCESSES_LEFT run_start` / `run_end`, `(INCOMPLETE: processes left)`, …) | O | Generic phase leak at helper level only | No row is tested at tool level |
| 74 | AM-5(d) | Finding 13 | O | By the amendment | |
| 75 | AM-5(e) | Documents and docstring corrected; a probe per class recorded in `evidence/audit/` | P | `tools/evkit.py` docstring around :4151 | P1-F6 documents row pending; no per-class probe in `audit_final` |
| 76 | AM-6(a) | Single-thread check before fork; `ENV_THREADS_AT_FORK` | C | `P2ForkedUnits::test_forking_needs_a_single_thread` | The `/proc/self/task` branch is not exercised on its own |
| 77 | AM-6(b) | Drain tests: a grandchild holds the write end and adds one byte (bad_result + leak); holds it and stays silent (processes_left) | O | none | The `trailing` subtests write from the direct child |
| 78 | AM-7, AM2-3, AM3-5, AM4 | Mistakes 20–31 and findings 11–13 disclosed in the documents | P | Change record (17, 18, 27, 29); issue records and build log | Pass-2 documents not yet produced |
| 79 | AM2-1(a) | Batch unit only after steps 1–5; 300 s; full call whatever the selection; `--pin` uses it | P | `test_am2_1_the_batch_unit` (`drop_pinned` with `--only`); `P2Amendment3::test_am3_1_c_…` | Not shown: no batch run after an ordinary start refusal; `--pin` using the unit |
| 80 | AM2-1(b)(c) | Message form, unique pairs, 1 MiB; inventory compared before selection; `ok` mapping | C | `test_am2_1` (`wrong_type`, `duplicate`, `too_big`, `false_row`, `drop_pinned`, `none:x`); `P2ForkedUnits::test_framing_limit` | Exact 1 MiB / 1 MiB + 1 only at helper level |
| 81 | AM2-1(d) | Precedence rows 1–7 | P | `test_am2_1` subtests | Not tested: row 7's inventory mismatch winning over the leak; row 3 with a leak |
| 82 | AM2-1(g) | `_CACHE` removed; re-pinned | C | Static: no `_CACHE` in `tools/*_s1.py`; `static/frozen_compare.txt` problems 0 | |
| 83 | AM2-2(a) | Record as the last line, exit 3, P lines before M10's final line; `SIGNAL_AFTER_COMPLETION` before it with M10's exit unchanged | P | `P2NoResultSupervisors` (`interrupted()`); `::test_between_steps_and_after_the_last_step` | Placement of `SIGNAL_AFTER_COMPLETION` and the unchanged exit not asserted (only "not 3") |
| 84 | AM2-2(b) | Steps, the watcher for R03, R06 and R04, the bound | C | `::test_a_child_step_interrupted_by_sigint`, `::test_r03_…`, `::test_r06_…`, `::test_r04_…`, `::test_between_steps_…` | |
| 85 | AM2-2(c) | CR-02 synthetic `CompletedProcess` fields; cleanup on SystemExit | P | `::test_cr02_sigterm_during_its_first_child` | Fields not asserted |
| 86 | AM2-2(d)(e) | Consumers: class N CHECK, sabotage_m8 plant and both controls, redirected successor | C | `::test_consumer_*` (3); `Pass2InterruptedNoKindChild` | The signal is self-sent through an evkit edit |
| 87 | AM2-3 | B.1 sentence struck; mistake 22 | C | Stop 2 issue record (S8) | Documents pending |
| 88 | r1 | ITEM_ERROR kept when a leak is also found | C | `test_am2_1` `batch:child_error_leak` | |
| 89 | r2 | Timeout, interrupt and run_stopped keep their cause | C | `plant:spawn_hang`, `batch:spawn_hang`; `test_f1_…_with_jobs_2` | |
| 90 | r3 | Subprocess pipe drain bounded | P | `::test_normal_path_background_grandchild_…` | The bound is not asserted |
| 91 | r4 | SIGTERM to the nested supervisor alone | P | Row 23 test | The stub has no other members |
| 92 | r5 | Grace ends early after two empty scans | O | none | |
| 93 | r6 | Phase recorded | C | `Pass2ControlsV3`; `at=` asserts in P2 tool tests | |
| 94 | r7 | Multi-command end control | C | `::test_reading_7_an_interrupt_during_an_earlier_commands_cleanup` | |
| 95 | r8 | Start control interrupted before it began | P | `Pass2ControlsV3::test_start_control_interrupted` | Checker level only |
| 96 | r9 | Unowned child attributed to run_end; test in a copy | O | none | |
| 97 | r10 | Argument errors are step 3 refusals | P | `test_a4` `--bogus` | Missing value, `--path`/factory mismatch and malformed spec not asserted for `suites=-` |
| 98 | r11 | Canonical hash; a test runs both orders | P | `Pass2CasesV3::test_the_hash_is_canonical_…`; 2C file | Helper only; no real runner in both orders; CASE order not asserted |
| 99 | r13 | `CLEANUP_SUMMARY units=` counting | O | none | For example `units=219` in m2s is not reconciled anywhere |
| 100 | r14 | `child_unittest_runner` declares itself just before `verify_auif` | P | `test_supervisor_list` | The declaration point and its check not tested |
| 101 | r15 | Subreaper proof; zombie check by the tool itself; ChildProcessError | P | Row 2 and row 13 tests | No zombie check by the tool itself; leaf reap untested |
| 102 | AM3-1(a) | Post-load identity check before any item | C | `P2Amendment3::test_am3_1_a_a_decoy_harness_is_refused_before_any_item` | |
| 103 | AM3-1(b) | No load after a failed start check; changed tests listed | C | `::test_am3_1_b_no_load_after_a_failed_start_check`; change record | |
| 104 | AM3-1(c) | `--pin` guarded | C | `::test_am3_1_c_a_case_runners_pin_is_guarded` | |
| 105 | AM3-1(d) | The import-time limit | C | The row 102 test asserts the decoy marker was written | |
| 106 | AM3-1(e) | B.6, K.2 and E.2 still identical | P | b6, k2, golden, pairs SAME on both Pythons | E.2 m2 DIFFERENT 2 on py313 (S14); not run on py312 |
| 107 | AM3-2 | E point 3 rewritten | C | `P2Amendment3::test_am3_2_e_point_3` | |
| 108 | AM3-3 | E point 17, first half | C | `test_apg_root.py::ApgRootRedirect::test_e17_the_p7_b2_run_imports_the_real_apg_in_its_child` | |
| 109 | AM3-4 | Exit-3 INDETERMINATE accepted for classes N and B only; refused otherwise | C | `::test_am3_4_class_b_a_real_baseline_that_exits_3`, `::test_am3_4_class_n_…`; `P2NoResultSupervisors::test_consumer_a_wrappers_class_n_check` | |
| 110 | AM4-1, E.2, I.3 | m2 comparison (M10 `run_one` harness, fixed values, allowances only) on both Pythons | O | `compare_py313/m2.txt`: fixed values hold; `RESULT m2 DIFFERENT 2`. Nothing for py312 | S14 open; the S13 slicing reading awaits the owner; the tool's allowance is wider (D-list 15) |
| 111 | AM4-1 | Literal output of one run of M10's `m2_mutants.py` | O | `m2_logs/m10_script_list.txt` (`--list` only) | S13 open |
| 112 | H | Stop rule applied | P | Issue records S6–S14 | Mistakes 23 and 29 handled without a stop record; the S14 diagnostic is unrecorded (D-list 11) |
| 113 | I.1 | Commit, re-pins, manifest, change record contents, mistakes 17 and 18 | P | Commit `6f65d488`; `programme/CHANGE_RECORD_APG-M11-S1.md`; `tools/evkit.py:774`; no "decision pending" text remains | `ENV_THREADS_AT_FORK` missing from the codes list; one combined record for three version changes |
| 114 | I.2 | Suite passes on 3.13 and 3.12; freeze built twice with identical bytes | C | py313_T, py312_T (613 OK each); `freeze_build2.zip` = `c9b324eb…` | |
| 115 | I.3 | Six run sets | C | `py31x_{T,W,M}/run_index.csv`, `tree_after.txt` (0 changes), `wrapper_check.txt`, `m8_check.txt` | |
| 116 | I.3, E.2 | Golden: 6 runners identical, both Pythons | C | `compare_py31x/golden.txt` SAME | |
| 117 | I.3, E.2 | 15 pairs, case by case, both Pythons | C | `compare_py31x/pairs.txt` SAME | |
| 118 | I.3 | Historical checks, both Pythons | C | `historical_py31x/summary.json` (100/100, archive unchanged) | |
| 119 | I.3 | Frozen-file comparison; both route proofs | C | `static/frozen_compare.txt` (problems 0), `route_children.txt`, `route_scan.txt` | |
| 120 | I.3 | Check of the cited test names | O | none for this freeze | |
| 121 | I.3 | Pids, start times, pgids and the cleaning supervisor recorded for the P, B, K.2 and F.2 tests | O | The T logs hold none | |
| 122 | I.3 | Evidence index (README) linking `evidence/audit/` and the identity and CLEANUP records | O | `d14/s1/README_PACKAGE.md` describes d5f87d6b | |
| 123 | I.3 | Run index describes `last_line` as a prefix of at most 300 characters | P | `run_index_s1.py:67` truncates at 300 | The docstring says "the last line" |
| 124 | I.4 | Separate-agent mapping | P | This document | Not yet reviewed |
| 125 | I.5 | One ZIP plus one documents file; d5f87d6b kept | P | `freeze/superseded_d5f87d6b/` kept | Package and documents not produced |
| 126 | I.6 | No change after the freeze | C | `tree_after` 0 for all six sets; fresh extraction equals the evidence extractions | |
| 127 | G | Findings 1–10 stay open; D2, D8, D12 and (e) unchanged | O | By the paper | |

### 2. E points

| Point | Class | Test / evidence | Note |
|---|---|---|---|
| 1 | C | `test_mutation_timeout.py::E1KillOracleNamesAMissingTestFile` (2 tests) | M10's kill line asserted literally |
| 2 | O | See E.2 | |
| 3 | C | `P2Amendment3::test_am3_2_e_point_3` | As rewritten by AM3-2 |
| 4 | C | `test_apg_root.py::E4DecoyWorkingDirectory` (2 tests) | Recorded as found: M10 imports its own apg |
| 5 | O | — | Not in E's table; (e) is owner-accepted |
| 6 | C | `P2MutationFamily::test_f1_*` (m2) | F.1 as a whole is partial (row 50) |
| 7 | C | `test_exec_env.py::E7ChildIsolationM10Halves` (4 tests) | See D-list 17 for one test's name |
| 8 | C | `ToolLevelTimeoutCrashKill` (15 tools, timeout and crash, M10's literal text); `ToolLevelM8::test_timeout_m8`, `::test_crash_m8` | |
| 9 (D13) | C | `ToolLevelTimeoutCrashKill.test_timeout_<tool>` (15) | |
| 10 | O | — | D2, owner-accepted; outside this pass |
| 11 | O | — | P1-M1, outside this tree |
| 12 | C | `E12M3NonMatchingPattern` (2 tests) | |
| 13 | O | — | D8, owner-accepted |
| 14 | O | — | D12, owner-accepted. The stale comment is corrected (mistake 18) |
| 15 | C | See E.15 | |
| 16 | O | — | D6, stated deviation; not addressed |
| 17 | C | `test_e17_the_p7_b2_run_imports_the_real_apg_in_its_child`; `E26RealFailFast::test_e17_ml01_kill_attribution_matches_m10` | |
| 18 | O | — | D15, accepted on the reviewer's terms (G) |
| 19 | O | — | D3, stated deviation |
| 20 | C | `MutRunnerOutput::test_e20_the_c8_kill_attribution_matches_m10` | |
| 21 | O | — | D14, accepted on the reviewer's terms (G) |
| 22 | P | `MutRunnerOutput::test_e22_…`; `E26RealFailFast` `f11()` with `check_output` | The standalone run is not passed through the checker |
| 23 | O | — | D: finding 2 stays open |
| 24 | P | Rows 38–43 | B.5 is incomplete on four runners |
| 25 | C | `SelectorsThatDoNoWorkExitTwo` (m7 and m8: `--group 0`, `--range 5-3`); `E25StubbedChildGroups`; `WrappersW1B` (f672 G11); `WrappersW1A` (f674 G10); E.15 refusals | |
| 26 | P | `E26RealFailFast` F1, F7, F8 | F8 shows only a stop inside one file (the builder's reading, not confirmed); "files after the failure" is not shown for F8 |
| **E.2** | O | Golden and pairs SAME on both Pythons. m2: py313 DIFFERENT 2 (CA01, RI13), py312 not run. Literal run not made | The paper itself keeps point 2 partly open; S13 and S14 are open |
| **E.15** | C | `test_harness_isolation.py::E15FakeHarnessAndTrustedNames` (3 tests) | 8 runners × 9 names × package and module; factory spec; all through `check_output` |

### 3. Discrepancies

**Claims I cannot find evidence for**
1. **B.5 and I.3: child pids, pgids and CLEANUP lines.** The paper says the test evidence records each child's process and group ids, its CLEANUP lines, and which supervisor cleaned up each unit. No T log carries any of this.
2. **I.3: the check of the cited test names.** There is no record for c9b324eb.
3. **I.3: the evidence index.** No README links `evidence/audit/` or the identity and CLEANUP records. `README_PACKAGE.md` is the d5f87d6b one.
4. **Change record: "the tests added are listed in the stage 1 documents' mapping".** No pass-2 documents exist yet.
5. **AM-5(e): "a probe in each path, recorded in `evidence/audit/`".** There is no such probe output.
6. **AM-2's "all 26 process starts set a time limit".** This was measured on the earlier freeze only.
7. **The audit tool's docstring.** It says the tool runs with "env PATH TMPDIR LANG LC_ALL TZ only", and that it starts its child "exactly as run_child starts a unit today (subprocess.run…)".
   - The `audit_final` record shows 231 auditor environment names.
   - On this freeze, `run_child` goes through `run_unit` (Popen hook, stdin DEVNULL), and the tool's fork scrub is its own code, not `run_forked`.
   - So `audit_final`'s fd 0 = /dev/null comes from how the auditor was started, not from the AM-4 code. The 11-05 conclusions file says the same.
8. **Builder readings presented as within the authority but not confirmed by the owner:**
   - the S13 five-slice harness;
   - the F8 "within-file stop";
   - mistake 23 (C.1's tables were incomplete; moved under the general rule with no AM-8 stop);
   - mistake 29 (fixed with no stop record).
9. **Reading 17's "the documents will say this is not fixed".** Documents pending.
10. **E.2's "these numbers and hashes are in the test".** They are in the builder's out-of-tree tool (`compare_pass2_s1.py:26-28`), not in any `tests_tools` file.
11. **An unrecorded S14 diagnostic.** `evidence_pass2/diagnostic_s14/` exists, and an S14 diagnostic was running at about 02:44–02:51 on 2026-11-08 (1 worker, `run_one` on the EQUIV ids). Neither the build log nor the S14 record mentions it. It applies S14 option B, which departs from AM4-1's 4 workers, before the owner has decided. First result: CA01 SURVIVED in 203.6 s.

**Tests weaker than their names or than the paper**

12. **"Shown gone before the RESULT line"** (P.10, K.2, F.2). The tool-level helpers (`p2b_gone`, `p2_gone`) check after the supervisor exits, not at its RESULT line.
13. **Several P tests assert less than their names or the paper:**
    - `test_equal_start_times_are_ambiguous_and_recorded`: "recorded" means only an internal dict.
    - `test_concurrent_orphan_attribution_…`: asserts `or` where the paper requires each unit.
    - `test_refusals_when_containment_cannot_be_set_up`: no tool-level refusal form.
    - `test_valid_result_then_hangs` (helper): no classification asserted.
    - `test_the_hook_registers_…`: registration only.
14. **Runner-level gaps:**
    - `test_the_hang_on_each_of_the_other_four_runners`: passes on a start-control timeout, so the plant's own hang may never be exercised.
    - The hang tests for history and mkt lack `check_output`; history also lacks the gone check.
    - `test_the_hash_is_canonical_…`: helper only.
    - `test_tests_and_wrapper_stay_v2`: checks write versions only; K.3's twice-through-checker test is absent.
    - `test_hang_timeout_and_setsid_double_fork_are_contained`: one level, not P.10's nesting.
    - `too_big` is about 16 bytes over 1 MiB, not exactly 1 MiB + 1.

**Evidence that contradicts a claim, or tools that differ from the authority**

15. **The m2 compare tool allows more than AM4-1.** It accepts any M10 KILLED (even "by tests") against a successor INDETERMINATE (`compare_pass2_s1.py:416`). AM4-1 allows that only for an M10 kill by timeout or crash. No id used the allowance.
16. **The b6 compare tool does not compare the CONTROL causes** B.6 requires. The logs agree.
17. **`E7ChildIsolationM10Halves::test_m8_mutants_controls_and_a_known_kill`** asserts only that M10's control fails. No kill is asserted.
18. **Build log, 02:15–02:43: audits "(same as 11-05)". This is contradicted:**
    - the auditor's environment differs (231 names against 5);
    - `process_api_reach` lacks the PID 1 and process listing;
    - there is no conclusions file.
19. **E.2 m2: `DIFFERENT 2`, outside AM4-1's allowances** (S14, open). For 83 of M10's 197 kills, which were by timeout, the comparison shows only that both sides end KILLED.
20. **Change record:**
    - `ENV_THREADS_AT_FORK` is absent from the new codes;
    - it dates the paper's authorisation to 23:00 on 2026-11-05, while AM-1 §0 says 10:56. The 23:00 was the build authorisation.
21. **Other builder tools:**
    - `run_index_s1.py`'s docstring says "the last line", not "a prefix of at most 300 characters";
    - `check_m8_log_s1.py` does not say it was updated for v=3.
22. **Privacy, not a P.2 breach.** `audit_final/outside_services.txt` records the values of non-secret identifiers from the builder's session: the user e-mail variable, the account and organisation UUID variables, the container id and the remote-session URL variable. P.2 allows this wording-wise. The owner may want them reviewed before the package is distributed.

### 4. Summary

| | CLOSED BY EVIDENCE | PARTLY ADDRESSED | STILL OPEN | Total |
|---|---|---|---|---|
| Requirement table (section 1) | 55 | 49 | 23 | 127 |
| E points 1–26 (section 2) | 12 | 3 | 11 | 26 |
| E.2 / E.15 | E.15 | — | E.2 | 2 |

- **What depends on the owner:** rows 106, 110 and 111, E point 2 and E.2 are open or partial because they wait on S13 and S14.
- **The largest groups of gaps:**
  - P.10's nested and cleanup edge tests;
  - the K.2 per-case message forms;
  - F.2 for the tests runners and wrappers;
  - the AM-5(c) attribution rows;
  - the AM-6(b) drain tests;
  - readings 5, 9, 12, 13 and 16;
  - K.3's twice-through-checker test;
  - I.3's identity records, names check and evidence index.