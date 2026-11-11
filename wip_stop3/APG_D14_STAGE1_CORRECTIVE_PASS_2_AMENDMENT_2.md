# APG D14 stage 1, corrective pass 2: amendment 2 to the decision paper (final text; identical to draft 3 except this title)

**BUILDER-EXECUTED: NOT INDEPENDENT.** Prepared by the builder on 2026-11-06. Draft 1 (`7369b2d6…2eaf`) was reviewed in `rec/reviews/RECEIVED_REVIEW_2026-11-06_0818_AMENDMENT_2_DRAFT_1.txt` (`0f4d8a6e…5262`). Draft 2 (`6415687e…30c6`) was audited read-only by a separate agent that had not seen the builder's working: `d14/decisions/INDEPENDENT_AUDIT_AMENDMENT_2_DRAFT_2.md`. The changes made for the review and for the audit are listed in sections 6 and 7.

This amendment authorises nothing until the owner posts it. It accepts nothing, closes no finding, EDR or CF item, and makes no production-readiness claim.

## 0. What this amends, and the state of the work
- **What it amends:** the paper `23d2adb9…f0ea5`, as amended by amendment 1 `211971…d382`. Where they differ, this amendment governs. Everything it does not change stands, the stop rule H and AM-8 included.
- **The state of the work.** Implementation stopped under H and AM-8 at stop 2 (`rec/ISSUE_RECORD_2026-11-05_CORRECTIVE_PASS_2_STOP_2_K2.md`).
  - No logic change has been made since.
  - The work in progress is uncommitted, and is in `d14/s1/pass2_work/WIP_at_stop_1.diff` (`b8998f3a…cdcf75`). It is unaccepted, and has only been smoke-checked.
  - The freeze `d5f87d6b…85c8` is unchanged.
- **When the owner posts this amendment:**
  - the builder resumes from that diff, under the paper as amended by amendments 1 and 2;
  - the diff is changed wherever it disagrees with this amendment (AM2-2 (c) names one known place);
  - each correction is tested with focused checks, and the full verification runs once, on the final candidate.

| # | Matter | Decision proposed |
|---|---|---|
| AM2-1 | S6: in 7 case runners the harness runs every case in one call, in the parent, at step 6 | the harness call is one forked unit (option (a)) |
| AM2-2 | S7: interruption in the 6 supervisors that print no `RESULT` line, and how their consumers read it | an exact record, its placement, the consumer rule for each consumer, and a bounded stop for blocking in-process steps |
| AM2-3 | S8: B.1's `_CACHE` sentence | struck; mistake 22 |
| AM2-4 | the builder's implementation readings | confirmed as worded here |

## AM2-1. The 7 batch case runners: the harness call is the unit
**Scope.**
- **The 7 runners:**
  - `run_contracts_s1` (`R.run`);
  - `run_guard_contract_s1` (`run_guard_suite`);
  - `run_history_contract_s1`, case mode (`H.run_history_suite`);
  - `run_m3_contracts_s1`, `run_m5_contracts_s1`, `run_m6_contracts_s1` and `run_m91_contracts_s1` (`C.run_all`).

  They hold 126 of the 386 cases.
- **Why they need it.** Each runs and reports all its cases in one immutable M10 harness call, which has no entry point for a single case.
- **The 4 corpus runners** (`run_det_corpus_s1`, `run_fin_corpus_s1`, `run_ingest_corpus_s1`, `run_mkt_corpus_s1`, 260 cases) keep K.2 as worded: one forked unit per case.

**(a) The unit.**
- **When it runs.** For the 7 runners, the one harness call runs as a single forked unit under P (P.2 to P.8 as amended by AM-6, the single-thread check included), after steps 1 to 5 of A.1. It is started only when steps 1 to 5 refused nothing. Today's code calls `enumerate_cases` even after a start refusal (`evkit.py:1965`); that call is not kept.
- **What it replaces.** It is both the inventory step (step 6) and the case step (step 7) of A.1. It replaces the in-parent `enumerate_cases`, and the per-case `run_case`, for these runners.
- **The time limit:** `CASE_ITEM_TIMEOUT_S`, 300 s, for the unit. Today each runner's whole call takes 0.2 to 0.5 s in the builder's workspace.
- **No selection is applied to the call.** The child makes the full harness call whatever `--suite` or `--only` selects, as the call does today. It returns every row. The selection is applied only in the parent, after the inventory comparison.
- **`--pin` mode** uses the same unit to obtain the inventory it pins.

**(b) The message.**
- **The success form:** `{"results": [[<suite>, <case id>, <ok>, <detail>], …]}`.
  - Every row has exactly four items: a string, a string, a bool and a string.
  - The suite and case id, after `_case_token` (as today), form a pair that is unique across the rows. Today's duplicate check in the comparison (`evkit.py:1999`) therefore moves into the message's validation, as `bad_result` (row 5).
- **The other forms:** `{"exception": "<type>"}` (an exception escaping the harness call), and `{"child_error": "<type>"}` (B.1).
- **Size.** P.8's 1 MiB limit on the encoded message applies.
  - The largest legitimate message today is `run_contracts_s1`'s: 38 rows, 1,389 bytes. The largest row of any of the 7 is 43 bytes (`run_history_contract_s1`).
  - Tests send a message of exactly 1 MiB, which is read, and one of 1 MiB + 1 byte, which is `bad_result`. They also send `run_contracts_s1`'s real message.

**(c) Steps 6 and 7 in the parent, from a validated `results` message.**
- **Step 6.** The complete inventory in the rows is compared with the runner's pins for all its pinned suites, exactly as today's comparison of `enumerate_cases`' list. A difference is today's `CASE_INVENTORY_MISMATCH` refusal, with the resolved selection kept and the cases `NOT_RUN`.
- **Step 7.** Then each selected case takes its verdict from its row, exactly as today: `ok` true is `PASS cause=ok`, and false is `FAIL cause=expected_outcome_differs`. The `CASE` lines keep the requested order.

**(d) When the unit gives no validated `results` message, or gives one and leaves members alive (row 7).**
- **Rows 1 to 6:** no inventory comparison is made.
- **Row 7:** the comparison of (c) is made first. A difference is `CASE_INVENTORY_MISMATCH`, with the cases `NOT_RUN`, and is not weakened to `processes_left` (like rows 3 and 4). Otherwise every selected case is `INDETERMINATE cause=processes_left`.
- **No case is ever `PASS`.**

Every selected case, and the run, takes the outcome below. Where two conditions hold together, the first matching row decides, and every leak still appears on the unit's `CLEANUP` line and in `CLEANUP_SUMMARY`.

| # | Condition | Run-level record | Every selected case |
|---|---|---|---|
| 1 | an interrupt before the outcome was fixed (F.2, P.8) | `INTERRUPTED …` | `INDETERMINATE cause=interrupted` |
| 2 | the deadline passed with no complete message | `TIMEOUT` line, as B.1 | `INDETERMINATE cause=timeout` |
| 3 | a valid `exception` message: an enumeration failure of the run, not a case failure | `RUN_ERROR CASES_ENUMERATION_FAILED <type>` (today's code) | `NOT_RUN cause=run_error`; the resolved selection kept (`suites` and `suites_selected` as resolved) |
| 4 | a valid `child_error` message, or no complete message and exit status 70 | none | `ITEM_ERROR cause=child_error` |
| 5 | a message that fails P.8's steps 2 to 5 (framing, the 1 MiB limit, JSON, a trailing byte, form, types, a duplicate pair) | none | `INDETERMINATE cause=bad_result` |
| 6 | the child ended before its message was complete (any other status, or a signal) | none | `INDETERMINATE cause=crash` |
| 7 | a valid `results` message, with members alive after it (P.6) | none | `INDETERMINATE cause=processes_left` |

- **Rows 3 and 4 keep their result when a leak is also found:** an enumeration failure and an `ITEM_ERROR` are not weakened to `processes_left`. This is reading 1 of AM2-4.
- **A leak in row 5 keeps `bad_result`,** as AM-6 (b) already requires.
- **Row 7 applies only to a message that passed every validation step.** So a malformed or incomplete message with a leak is row 5 or 6, never 7. It can never be `PASS`.

**(e) What this does not give.**
- **One case is not isolated from another.** A hang or crash in any case makes every case of that run `INDETERMINATE`.
- **Shared state is preserved.** The cases share state as they do today. The child's environment, descriptors and standard input do differ from today's parent (P.2, AM-4), so whether the verdicts are unchanged is shown by the K.2 comparison below, not assumed.
- **K.2's comparison of all 386 verdicts with the current freeze is kept as a stop-rule check.** It shows only that the verdicts are unchanged. It is not evidence of per-case isolation, and it is not claimed as such.

**(f) Tests, replacing K.2's per-case tests for these runners.**
- **On `run_contracts_s1`, in a temporary copy, with the harness call replaced in that copy only:**
  - a hang;
  - a descendant that hangs;
  - a background descendant after a valid message (row 7);
  - a crash;
  - an incomplete message;
  - a malformed message;
  - a wrong-typed row;
  - a duplicate pair;
  - a trailing byte;
  - the 1 MiB and 1 MiB + 1 boundary;
  - an `ok=false` row (`FAIL cause=expected_outcome_differs`);
  - an exception in the harness (row 3, `suites` kept);
  - `child_error`, by message and by status 70;
  - a kill while writing (`crash`);
  - an interrupt;
  - `child_error` with a background descendant (row 4 kept, the leak on `CLEANUP`);
  - a malformed message with a background descendant (row 5 kept, the leak on `CLEANUP`);
  - `--only` of one case, showing that the full inventory was compared (a pinned case removed from the copy's harness output is `CASE_INVENTORY_MISMATCH`, even though it was not selected).
- **On each of the other six batch runners:** a hang (`INDETERMINATE cause=timeout` for every selected case) and `run_contracts_s1`'s real-message shape.
- **What every test asserts:**
  - each listed identity is shown gone, not alive and not a zombie;
  - the output passes `check_output`;
  - the exit code and status are as stated.
- **`run_fin_corpus_s1`** keeps K.2's per-case tests, and the hang test is also run on the other three corpus runners.

**(g) Code.**
- **The 7 runners.** Each runner's `results(cand)` becomes the unit's callable, with its module-level `_CACHE` removed.
- **`cases_main`** gains this batch path.
- **Other tools.** No harness, and no M10 file, changes.
- **Pins.** The changed files are re-pinned, with change records.

## AM2-2. The 6 supervisors with no `RESULT` line
**Scope.**
- **The 6 tools:** the 5 regression successors (`run_regression_m10_s1`, `_m8_s1`, `_m81_s1`, `_m81r1_s1`, `_m8r2_s1`) and `run_cr02_reference_s1`.
- **Why they need their own rule.** They print M10's own output and no `RESULT` line (T-K). AM-6 (c) puts them under F.2's mechanism. Today, no consumer recognises an interrupted run of one of them:
  - `check_outcome` (a wrapper's `CHECK`) reads exit 3 as `ITEM_ERROR`;
  - `regression_step_classifier` and the regression successors' marker reading read it as a failure or a crash.

**(a) The record and its placement.** When one of the 6 is interrupted (F.2: the flag is set before the outcome of its last unit or step is fixed):
- **The record:** `INTERRUPTED signal=<SIGINT|SIGTERM> at=<step id, or child> received=<n>`.
- **Placement.** The record is the last line of its standard output.
- **The exit code** is 3, whatever M10's own code would have been.
- **Other P lines.** The `CLEANUP`, `CLEANUP_AMBIGUOUS` and `CLEANUP_SUMMARY` lines come before M10's final line, and `INTERRUPTED` comes after it.
- **A signal after the last unit's or step's outcome is fixed** gives `SIGNAL_AFTER_COMPLETION signal=<…>` before M10's final line, and M10's exit code unchanged.
- **How the placement is built.** M10 prints its own final line before control returns to the successor (`run_regression_m8.py:195`, `run_cr02_reference.py:18-19`). So the successor holds back M10's last line, through a `sys.stdout` wrapper, until it has printed the P lines that come before it. An uninterrupted run's last line stays M10's own.
- **The meaning of the pair.** Of the tools that print no `RESULT` line, only these 6 print `INTERRUPTED`. No M10 tool does. So "exit 3 with a last line matching the record" is unambiguous.

**(b) The regression successors.**
- **Steps.** Each M10 step is wrapped in `M.STEPS`, as for its owner phase (AM-5 (c)).
  - **A step not started when the flag is set** is not run. It returns M10's failed-check form, with what `"<step> (INCOMPLETE: interrupted)"`.
  - **A step whose child unit is in flight** is stopped under P.5, with the cancelled grace. The step returns `"<what> (INCOMPLETE: interrupted)"`.
- **In-process steps that are blocked waiting on a child:**
  - R03 of the 5 M10 tools (`subprocess.run` with no time limit);
  - the AUIF verification in `run_regression_m8`'s R06 and `run_regression_m81`'s R04 (`apg_auif.dependency.verify_tree`, two `subprocess.run` calls with `timeout=600`, `dependency.py:52`, `:60`).

  **How their children are treated.** In `run_regression_m8_s1` and `run_regression_m81_s1`, the hook registers these AUIF children, and they are owned by that step, as in AM-5 (c)'s `r03` row: a leak gives "(INCOMPLETE: processes left)". AM-5's list of `verify_tree`'s callers, and finding 13 class 1, gain these two steps. Killing such a child is safe: its empty output raises `AuifDependencyError`, which the step catches (`run_regression_m8.py:150`, `run_regression_m81.py:108`), so the step returns `False`.
  - **The watcher.** The successor runs one watcher thread. It blocks SIGINT and SIGTERM in itself (`signal.pthread_sigmask`) before it starts polling, so the main thread's handler always receives them. Every 0.2 s (F.2) it checks the flag. Its scans, 0.1 s apart (P.5 step 4), do not run the reaper. Once the flag is set, it signals the live members of the owner phase of the in-flight step, as P.5 steps 4 and 5 do: `SIGTERM`, then `SIGKILL` after `T_GRACE_CANCELLED`.
  - **What it never does:** it never waits on or reaps any child, and never prints.
  - **How the step ends.** The blocking call returns once its child has died. The step's own wrapper then completes P.5's cleanup and reaping in the main thread, and reports `(INCOMPLETE: interrupted)`.
  - **Bound.** So an interrupt during any of these steps ends within `T_GRACE_CANCELLED` + `T_KILL_VERIFY` + one poll, plus the time M10's code takes to return once its child is dead.
  - **No M10 code changes.**
- **The limitations that remain, disclosed and not claimed away:**
  - **In-process M10 code that blocks without a child** (a loop, or a wait on anything other than a child) cannot be interrupted. The successor then reaches its cleanup, its record and its exit only when that code returns.
  - **Without an interrupt,** a hang in R03's child stays unbounded. This is open finding 13: no time limit is added.
  - **Neither is a guarantee** that every interruption produces the record. The record is produced whenever control returns to the successor.

**(c) `run_cr02_reference_s1`.**
- **How a child is stopped.** M10's script starts its children through the shim (AM-3), each a P unit whose wait sees the flag. So no watcher is needed:
  - **a child in flight when the flag is set** is stopped under P.5;
  - **a child not yet started** is not started.

  In both cases the shim returns to M10's script a `subprocess.CompletedProcess(args=<the command as rewritten>, returncode=-15, stdout='' or b'' by the call's text mode, stderr=the same)`. This is a child terminated by SIGTERM.
- **Why the output is empty.** A partial output with exactly one line would make M10's script raise `IndexError` (`run_cr02_reference.py:14`) rather than report a failure. The successor also catches any other exception from M10's script, with the same cleanup and record.
- **How the run ends.** M10's script then reports its own failure and raises `SystemExit`. The successor catches it, completes cleanup (AM-3, in its `finally`), and prints the record as the last line. The exit code is 3.
- **The known WIP mismatch.** The work-in-progress `emit()` inserts the record before the last line of an output with no `RESULT` line. It will be changed to (a)'s placement.
- **Tests:**
  - what M10's script reads from the returned object (`args`, `returncode`, `stdout`, `stderr`, in the call's text mode);
  - that cleanup happens when M10 raises `SystemExit`.

**(d) The consumer rule.** An interrupted no-kind child is a child of one of the 6 whose exit is 3 and whose last line matches `^INTERRUPTED signal=(SIGINT|SIGTERM) at=\S+ received=[1-9][0-9]*$`. It is never a pass, never an ordinary failure, and never an unexplained `ITEM_ERROR`. The consumers:

| Consumer | Today | Under this amendment |
|---|---|---|
| A wrapper's `CHECK`, class N: `run_regression_m8`, `run_regression_m81`, `run_cr02_reference` (`check_outcome`) | exit 3 is `ITEM_ERROR` | the `CHECK` is `INDETERMINATE`, with `exit=3` and its marker field as observed. Every other exit keeps today's mapping. |
| A mutation or sabotage tool reading a regression step through `regression_step_classifier` (`sabotage_m8_s1`) | `CRASH_NO_RESULT`, so the item is `INDETERMINATE cause=crash_no_result` (`map_mutant`, `map_plant`), and a control is `FAIL` | `run_child` gives a new outcome, `CHILD_INTERRUPTED`: the child's exit is 3 and its last line matches the record. It is distinct from the run's own `INTERRUPTED`. The item is `INDETERMINATE cause=child_interrupted`. A control whose command gives it is a completed `FAIL`: `CONTROL start CONTROL_FAIL cause=child_interrupted`, after which every item is `NOT_RUN` as for any failed start control; or `CONTROL end CONTROL_FAIL cause=child_interrupted`, with `control_end=FAIL`. `child_interrupted` is not a stop under K.1 or reading 6. The run's own `INTERRUPTED`, `CONTROL_INTERRUPTED` and `CONTROL_NOT_RUN` forms are used only when the tool itself is interrupted (F.2), and the child's output is then not used. |
| A regression successor's own redirected call to another regression successor (`REGRESSION_REDIRECTS`, marker reading) | a failed step | the step returns `"<what> (INCOMPLETE: interrupted)"`, and the calling successor exits 3 at its end, even if it was not itself interrupted. Its last line is then M10's own, and its `INTERRUPTED` record is absent (it was not signalled). So a consumer of the caller reads exit 3 with no record by today's rule for exit 3. |
| Direct invocation by the run index (`run_index_s1`) | records the exit code and the last line | unchanged. The evidence-set checks treat exit 3 with the record as an interrupted run: that set is incomplete and is not used as evidence. |

  Consumers of stage 1 runners that print `RESULT` are unchanged: their interrupted result is the `RESULT … status=INDETERMINATE exit=3` of F.2.

**(e) Tests.** Each test shows every process gone, and asserts the lines, the placement and the exit code.
- **`run_regression_m8_s1`:**
  - SIGINT during a child step;
  - SIGTERM between steps;
  - SIGTERM during R03 with R03's child replaced in a temporary copy by one that hangs (the watcher's bound);
  - SIGTERM during R06, with AUIF's first verification child replaced in a temporary copy by one that hangs;
  - a signal after the last step (`SIGNAL_AFTER_COMPLETION`).
- **`run_cr02_reference_s1`:** SIGTERM during its first child, with the returned object's fields and the cleanup on `SystemExit`.
- **The consumers:**
  - `run_m8_all_s1`'s class N `CHECK`, with an interrupted `run_regression_m8_s1` child (substituted in a temporary copy): `INDETERMINATE`;
  - `sabotage_m8_s1` with a regression step interrupted from outside, at a plant and at each control: the plant `INDETERMINATE cause=child_interrupted`; the control `CONTROL_FAIL cause=child_interrupted`; the output accepted by `check_output`;
  - a regression successor redirected from another: `(INCOMPLETE: interrupted)` and exit 3.

## AM2-3. S8
- **The sentence struck from B.1:** "and `run_history_contract_s1`'s result cache (`_CACHE`) is no longer shared".
- **Why it is wrong.** That cache belongs to the tool's case mode (AM2-1). Its fault mode calls `failed(cls)` once per plant, and never used it.
- **Disclosure:** mistake 22. It was written from the plan, not the code.

## AM2-4. Implementation readings, confirmed as worded here
1. **A leak on an item already `ITEM_ERROR`.** An item genuinely classified `ITEM_ERROR` before its cleanup (its child `CHILD_EVIDENCE_ERROR` or `LAUNCH_ERROR`, or `child_error`) keeps `ITEM_ERROR`. Its `CLEANUP` line records the leak, and the leak counts in `CLEANUP_SUMMARY leaked=`. This never applies to an item whose result was otherwise `PASS`, `KILLED`, `CAUGHT`, `SURVIVED` or `MISSED`: that item is `INDETERMINATE cause=processes_left` (P.6).
2. **Timeout, interrupt and `run_stopped` keep that cause.** Cleanup still records the members, and counts the unit as leaked.
3. **A subprocess unit's pipes** are drained for at most `T_EXIT_AFTER_RESULT` after its direct child exits. A member still holding a pipe is found by the scan that follows, and is a leak.
4. **A unit whose child is a nested supervisor.** While the nested supervisor lives, `SIGTERM` goes to it alone, so it can clean up its own units (P.7). Its other members are signalled once it has exited, and every live member is killed at `T_ESCALATE`.
5. **The grace phase also ends early** after two consecutive empty scans. They are separate scans, at least `SCAN_INTERVAL_S` apart, and each first runs the reaper, and polls the owner's direct child.
6. **The phase F.2 records.**
   - It is `control_start` from the run's start until the start control's outcome is fixed.
   - After that, while any item is in flight, it is the id of the first in-flight item in selection order.
   - Otherwise it is `between`, until every selected item has started and the last outstanding item's outcome has been fixed. From that moment it is `control_end`, whatever order the items finished in under concurrency.
   - It moves before the fix is decided, so a signal at the same instant is either `interrupted` on that item or `at=control_end`.
   - **For a family with no controls** (case runners, tests runners, wrappers), the phase is `between` before the first item, and is never `control_start` or `control_end`. For a batch case unit (AM2-1), the in-flight item recorded is the first selected case. The checker does not read this record for those kinds (K.3).
   - **K.1's "stopped before its last item"** means either of:
     - an item `NOT_RUN`;
     - an item stopped in flight (cause `interrupted` or `run_stopped`).
7. **An end control with several commands** has its outcome fixed by the command that ends it: the last command, or one that is not `CHILD_OK` when it is fixed. A leak found by the cleanup of an otherwise successful earlier command fixes it at that cleanup's end. A `TIMEOUT` is fixed at its deadline.
8. **A start control interrupted before it began** prints `CONTROL start CONTROL_INTERRUPTED cause=interrupted`, with `control_start=FAIL`.
9. **A child started in a supervisor that no unit or phase owns** is attributed to the run's end. A leak there is `RUN_ERROR PROCESSES_LEFT run_end`. A test starts such a child (in a temporary copy) and asserts both the attribution and the run error.
10. **Case runners: argument errors are step 3 refusals,** with no resolved selection (`suites=-`, `suites_selected=0`, `selected=0`, the empty-selection hash). They are: an unknown option, a missing value, `--path` without a candidate factory or a factory without `--path`, and a malformed `module:attr`.
11. **`case_inventory_sha256` (kind=cases v=3) is canonical, and independent of the order the suites were requested in.** It is `sha256_lines` over the lines `<suite>/<case id>`:
    - the suites are the resolved selection, deduplicated and sorted by code point (the order of `suites=`);
    - within each suite, the case ids are in the order the pins record them (`case_inventories/<tool>/<suite>/ids`).

    `--suite b --suite a` and `--suite a --suite b` give the same hash, and the same `suites=a,b`. The `CASE` lines keep the requested execution order. A test runs both orders and asserts both. (Draft 1 already sorted the suites; this states the case-id order too.)
12. **P.8 step 5 for a fault plant or control:** each failed id must be in the pinned case inventory of the paired case runner. The pairs:

    | Fault runner | Paired case runner |
    |---|---|
    | `run_faults_s1` | `run_contracts_s1` |
    | `run_m3_faults_s1` | `run_m3_contracts_s1` |
    | `run_m5_faults_s1` | `run_m5_contracts_s1` |
    | `run_m6_faults_s1` | `run_m6_contracts_s1` |
    | `run_history_contract_s1` | itself |

    Every pinned `must_fail` id is in its pair today. A test, on each of the 5 pairs, plants a failed id outside its pair (`bad_result`), and one inside it (accepted).
13. **`CLEANUP_SUMMARY units=`** counts each P unit once, plus each phase that registered at least one child. A phase is never counted again because one of its children is also a unit's child. Units and phases are distinct owners, and every registration has exactly one owner.
14. **A supervisor is identified by its tool's file stem** (AM-6 (c)), in `evkit.start`, except for `child_unittest_runner`.
    - **When `child_unittest_runner` is a supervisor.** It declares itself one in `tests_runner_main` when, and only when, it was given an AUIF copy to verify. It declares itself immediately before that verification (current freeze `evkit.py:1452`), and checks process supervision there: `ENV_NO_PROCESS_SUPERVISION` if unavailable, before `verify_auif` runs.
    - **The 3 true leaves** do not refuse on that check, because they supervise nothing.
15. **Importing `tools.evkit` installs the hook, and attempts the subreaper.** The tests prove what happens:
    - **the subreaper is active:** `PR_GET_CHILD_SUBREAPER` reads 1, and an orphaned grandchild's parent becomes the importing process;
    - **adopted zombies are reaped before the result, not merely uncounted:**
      - after a supervisor's cleanup, and after a leaf's pre-`RESULT` reap, no process remains whose parent is that process and whose state is `Z`, read from `/proc` by the tool itself, in a test-only check;
      - the in-process tests assert `waitpid` raises `ChildProcessError` for each reaped identity.
16. **A wrapper interrupted before an `H` group** still prints that group's `EXCLUDED` line. An `H` group never executes. A test interrupts `run_m4_all_s1` before an `H` group and asserts both.
17. **The residual of finding 9.** `regression_sabotage_main` and `mie_sabotage_main` load their M10 tool inside the function, so a load failure there ends in a traceback. These 11 tools are not in C's tables, and this pass does not change them. The documents will say this is not fixed.

## 5. Unchanged
Everything else in the paper and in amendment 1 stands, the stop rule H and AM-8 included. Any further mismatch found during implementation is again a stop-rule event.

## 6. Changes from draft 1, made for the review of 2026-11-06 08:18

| Review point | Change |
|---|---|
| AM2-1: exception outcome | defined as a run-level enumeration failure, the cases `NOT_RUN`, the selection kept (row 3) |
| AM2-1: precedence of `child_error`, malformed messages and leaks | the ordered table (d) |
| AM2-1: message size | the 1 MiB limit, today's largest legitimate message, and boundary tests (b) |
| AM2-1: inventory independent of selection | (a) and (c), with a test (f) |
| AM2-2: exit 3 for each consumer | (d), with a test for each consumer (e) |
| AM2-2: R03 limitation | a bounded watcher, and the limitations that remain, stated (b) |
| AM2-2: CR-02 synthetic `CompletedProcess` | its fields, with tests (c) |
| AM2-2: placement of the record | (a); the WIP `emit()` noted for change (c) |
| Reading 6 | the last outstanding item's outcome |
| Reading 11 | the case-id order, and the order-independence test |
| Reading 14 | where `child_unittest_runner` declares itself |
| Reading 15 | proof of reaping |
| Readings 9, 12, 16 | the tests |
| Reading 1 | made precise |

## 7. Changes from draft 2, made for the independent audit (1 blocking, 2 should-fix, 7 can-wait; all applied)

| Audit item | Change |
|---|---|
| B1: consumer-table row 2 contradicted K.1, B.4 and reading 6 for a parent that is not itself interrupted | new outcome `CHILD_INTERRUPTED` (a completed result, not a stop); the "Today" column corrected; test changed |
| S1: R06 and R04 also wait on children in-process (AUIF `verify_tree`) | added to AM2-2 (b), with the ownership row, finding 13, and a test |
| S2: table (d) and row 7 | the inventory comparison comes first for row 7, and a mismatch wins |
| Can-wait 1 | largest row 43 bytes |
| Can-wait 2 | "the verdicts cannot change" replaced: the comparison shows it |
| Can-wait 3 | "Only these 6 print `INTERRUPTED`" narrowed to the tools with no `RESULT` line |
| Can-wait 4 | CR-02's interrupted output is empty, and other exceptions are caught |
| Can-wait 5 | the watcher's signal mask, the polling values stated, no reaper in its scans |
| Can-wait 6 | the batch unit starts only if steps 1 to 5 refused nothing; duplicate pairs become `bad_result` |
| Can-wait 7 | the phase for families with no controls |
| Implementability | how the "last line" placement is built (M10's last line held back) |

**Rejected:** nothing. **Disagreements with the audit:** none.
