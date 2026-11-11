# APG D14 stage 1, corrective pass 2: amendment 1 to the decision paper (final text, for the owner to post)

**BUILDER-EXECUTED: NOT INDEPENDENT.** Prepared by the builder on 2026-11-05. It authorises nothing until the owner posts it. It accepts nothing, closes no finding, EDR or CF item, and makes no production-readiness claim.

## Draft history
- **This final text** is draft 1 (`…_AMENDMENT_1_DRAFT_v1.md`, SHA-256 `c2e8c442…ca72`), with the targeted corrections required by the reviewer's review of it (`rec/reviews/RECEIVED_REVIEW_2026-11-05_CORRECTIVE_PASS_2_AMENDMENT_1.txt`, `b92cdc3d…bb13`). The reviewer said that, with those corrections and nothing beyond them, the amendment could be posted without another full review round.
- **The reviewer's check of that text** (`841a322d…9bb0`, relayed by the owner at 22:57 on 2026-11-05) asked for one more precision: AM-5 (a) must distinguish the hook's registration from descendant containment. That is the only change from `841a322d…9bb0`. The reviewer's suggested sentence named "test-file subprocesses" among the processes the hook does not intercept. The builder has worded that part precisely: a test module run in-process starts its subprocess in the runner's own process, so the hook does register that subprocess (as AM-5 (c)'s table already says). The hook does not register the children such a subprocess starts in turn.
- **The corrections:**
  - AM-1: the explicit containment sentence;
  - AM-2: `child_unittest_runner` is a supervisor with AUIF; the T-set deadlines;
  - AM-3: CR-02's grandchildren;
  - AM-5: the hook's bootstrap point, its single registration and wait owner, the attribution table, and finding 13 made complete;
  - AM-6: the fork check, the drain protocol and the unique count.

  The reviewer's optional suggestions are also in: the hook as one named subsection, the process-tree diagram, the hashes of the evidence files, and the change log in AM-9.

## 0. Status, and what this amends
- **The paper it amends:** `APG_D14_STAGE1_CORRECTIVE_PASS_2_DECISION_PAPER.md` (SHA-256 `23d2adb9…f0ea5`), authorised by the owner at 10:56 on 2026-11-05.
- **The stop.** The P.9 audit stopped the work under the paper's stop rule before anything was implemented: `rec/ISSUE_RECORD_2026-11-05_CORRECTIVE_PASS_2_P9_AUDIT_STOP.md`, with its addendum.
- **The reviewer's review of the stop:** `rec/reviews/RECEIVED_REVIEW_2026-11-05_CORRECTIVE_PASS_2_P9_STOP.txt`. It agreed the stop was right. It required:
  - owner decisions on S1 to S4;
  - an amendment;
  - a bounded paper-to-code verification before implementation.
- **The verification is done.** It is `d14/s1/evidence_pass2/audit/paper_to_code_matrix.md` (23 rows, then the corrections section), cross-checked against an independent read-only inventory by a separate agent (`independent_inventory.md`). It found a fifth matter, S5, and the gaps in rows 5, 6, 18 and 23.
- **The evidence files and their SHA-256** (`d14/s1/evidence_pass2/audit/`, for the package; the raw records are unchanged):

  | File | SHA-256 |
  |---|---|
  | `child_start_sites.txt` | `eb817425…4d1d` |
  | `outside_services.txt` | `74604588…48c6` |
  | `process_api_reach.txt` | `16d1a89d…a9169` |
  | `outside_services_conclusions.txt` | `73a435a1…b26e` |
  | `independent_inventory.md` | `e9ba12b9…c254` |
  | `tset_leaf_deadlines.txt` | `1f9b9d48…b539` |
  | `paper_to_code_matrix.md` | `961b3077…3f84` |
- **Still in force:** the freeze is unchanged, nothing has been implemented, and the stop rule remains in force until this amendment is posted.
- **The rest of the paper is unchanged.** Where this amendment and the paper differ, this amendment governs.

**The owner's decisions.** Each is put with the builder's recommendation. The reviewer recommended the same for S2, S3 and S4, and asked the owner to decide S1.

| # | Matter | Recommended decision |
|---|---|---|
| AM-1 | S1, outside services | accept them as a limitation of the builder's workspace (open finding 11), and narrow P's containment claim to descendants |
| AM-2 | S2, test files run in-process | correct the paper to the code (open finding 12): three leaves; `run_m8_tests_s1`, and `child_unittest_runner` whenever it verifies AUIF, are supervisors |
| AM-3 | S3, the CR-02 shim | bring it under P, cleanup on its `SystemExit` path included |
| AM-4 | S4, standard input | `/dev/null` for every unit, and for the runners the run index starts |
| AM-5 | S5, children started by immutable in-process code | register every child through one hook, installed when `tools.evkit` is imported (needed for P.4); leave their command, environment and limit unchanged (open finding 13, six classes) |
| AM-6 | the verification gaps | single-threaded fork (Python threads and `/proc/self/task`); the message complete at its declared length, with a bounded drain; 71 unique supervisors |

## AM-1. S1: outside services in the builder's workspace (open finding 11)

**The finding** (`outside_services.txt`, `process_api_reach.txt` and the corrected `outside_services_conclusions.txt`). A unit can connect to:
- the workspace's process API (PID 1, TCP port 2024);
- the agent harness's socket, because units run as uid 0;
- the telemetry collector's socket.

Whether a unit could use any of them to have a process started outside its tree is neither ruled out nor established. The egress boundary is unknown. No process-launching daemon runs.

**Recommended decision:**
1. **Record it as open finding 11:** "In the builder's workspace, P.2's outside-service requirement is not met. Units can reach PID 1's process API, the harness socket and the telemetry socket, and the egress boundary is unknown."
2. **Narrow P's containment claim.** P.2 changes from "no descendant can leave the supervisor's process tree" and "outside services … outside this model" to:

   > P contains every descendant of a unit. A process started on a unit's behalf by an outside service, which in the builder's workspace may include PID 1's process API, the harness socket or the telemetry collector, is not a descendant and is not contained. Nothing in this pass establishes that such a request cannot be made.
3. **What is said about the risk.** The documents state the basis for judging the risk: no file of the frozen tree opens a socket or names these services, and every unit runs frozen code or a pinned mutation or plant of it. They state just as clearly that this is risk context, not the boundary test P.2 asked for.
4. **The audit runs again with the evidence.** The P.2 audit tool is part of the package, and runs again on the new freeze in the evidence set. Any independent environment that reproduces the evidence must repeat it, because its services differ.
5. **The explicit statement:**

   > This amendment does not establish complete process containment in the builder's workspace. It establishes containment of every descendant of a unit, subject to the documented workspace limitation (finding 11).
6. **Untrusted code.** If APG is later used to run untrusted code in a production or customer environment, a separate isolation design is required before the stronger containment guarantee is relied on. This pass does not provide it.

**The alternative.** Commission an isolation design as its own paper, before implementation. The reviewer notes that a network namespace alone would not close the Unix-socket paths, so such a design would need, at least, an unprivileged user and a filesystem view without those sockets. The builder does not recommend it for stage 1.

## AM-2. S2: test files run in-process (open finding 12)

**Recommended decision:** P.1, P.7, P.10 and F.2 are corrected to the code.

| Tool | Model | Under P |
|---|---|---|
| `run_m2_tests_s1`, `mut_runner_s1`, `run_test_files_s1` | each test file imported and run in the tool's own process (`evkit.run_test_file`) | **leaves:** not supervisors. A test file is not a unit. Processes a test starts are descendants of the leaf. |
| `child_unittest_runner` | its test modules run in its own process, as in the leaves. When it is given an AUIF copy to verify (`verify_auif`, `evkit.py:1455`), AUIF's `verify_tree` starts two children in its process | **a supervisor whenever it verifies an AUIF copy** (the hook, the subreaper and cleanup of AM-5). Otherwise its test modules are in-process, as in a leaf. |
| `run_m8_tests_s1` | one `child_unittest_runner` per test file through `E.run_child` (3600 s), plus AUIF's verification children (AM-5) | **a supervisor.** Each file's child is a unit. |

**What changes in the paper:**
- **P.1:** "a test file" is replaced by "a test file's child, where a tool starts one (`run_m8_tests_s1`)".
- **P.7:** the supervisor list is AM-6 (c).
- **P.10's nested test** becomes: a mutation tool, then its leaf tests runner, then a test that starts a process, then that process's own child (hanging; `setsid()` and double fork; left behind after a pass). It is cleaned up by the mutation tool, the supervisor. A second nested test goes through `run_m8_tests_s1`, then a file's `child_unittest_runner`, then a test's process.
- **F.2, in a leaf and in `child_unittest_runner`:** an interrupt is honoured between tests. The handler's flag makes the tool's own `Collector` result call `stop()`, so the test that is running finishes and no further test starts. A test that never returns cannot be interrupted. The last unit is the last selected file. `child_unittest_runner`'s AUIF children are stopped under P.5.
- **F.2, in `run_m8_tests_s1`:** a supervisor. Its wait on a file's child sees the flag and stops that unit under P.5, as for any supervisor.

**Open finding 12:**

> A leaf tests runner run on its own has no time limit per file or per test. A hanging test hangs it with no `RESULT` line, and an interrupt is honoured only between tests.
>
> Tests that start their own processes mostly give them no time limit: `tests/test_det_static`, `test_fin_static`, `test_mie_construction`, `test_mkt_intake`, `test_mkt_static`, `tests_m8/test_m8_dependency`, `test_m8_layout_config`, `tests_m8/_auif.py`.

**Which evidence relies on an outer deadline:**
- **In the W and M sets,** every invocation of a leaf runs under a parent with a time limit:
  - a mutation or sabotage tool (its per-item limit, 240 s to 3600 s);
  - a wrapper's `FILE` group (`run_child`, 3600 s);
  - `run_m8_tests_s1` (3600 s per file);
  - a regression successor (`regression_successor_main.run`, 3600 s).
- **In the T sets,** leaves are started by `tests_tools` tests. All 26 process starts in `tests_tools` set a time limit (60 s to 1800 s) (`tset_leaf_deadlines.txt`, which lists each with its parent, limit and leaf). A hanging test there is bounded by its test's own limit, and the test reports the missing `RESULT` line.
- **The run index starts no leaf directly.**
- **Standalone use** of a leaf, outside these, is not bounded, and is finding 12.

**The alternative:** fork each test file as a unit, like K.2. That is a new execution model for the tests runners, and is not recommended.

## AM-3. S3: the CR-02 shim

**Recommended decision:** `tools/run_cr02_reference_s1.py` is added to P's scope (P.9).
- **It becomes a supervisor:** the subreaper, the hook of AM-5, and the registration of P.4.
- **Its shim starts each child through P's start.** It keeps exactly its current command rewriting (it adds `-S`) and its environment filtering, and returns the same `CompletedProcess` to M10's script.
- **No time limit is added.** The script's children keep the one they have today, which is none. Bounding them is left to the outer wrapper's limit (AM-5 (b)).
- **Its grandchildren.** The shim intercepts only the M10 script's two direct `subprocess.run` calls. The second child, `reference/cr02/cr02_materiality_mutants.py`, starts a grandchild per mutant (`:114`, `-I` without `-S`, 300 s), and those are not intercepted. They are descendants and are contained under P. They do not meet R1 §2.8, and are part of finding 13 (AM-5 (c), class 3).
- **Cleanup runs on every exit path,** including the `SystemExit` that M10's script raises with `sys.exit`, in a `finally` before the process ends.
- **Tests:**
  - a CR-02 child that leaves a process behind: it is cleaned up, and recorded;
  - the `sys.exit` path: cleanup runs;
  - the output and exit code are unchanged against the current freeze's W-set runs that include CR-02.

## AM-4. S4: standard input

**Recommended decision:** a unit's descriptor 0 is `/dev/null`.
- **A subprocess child:** `stdin=subprocess.DEVNULL`.
- **A forked child:** `/dev/null` opened onto descriptor 0, before the callable.
- **The runners:** the builder's `run_index_s1.py` starts each runner with standard input from `/dev/null` as well.
- **P.2's tests and audit** assert that descriptor 0 is `/dev/null` for both kinds of child.

This changes what a child receives if it reads its standard input. No successor unit is meant to.

## AM-5. S5: children started by code stage 1 must not change (open finding 13)

**The finding** (matrix rows 19 to 21):
- **AUIF's `apg_auif.dependency.verify_tree`** (immutable M8 code) starts two children per `ensure()` call: `-I -B`, without `-S`, with `dict(os.environ, …)`, under a 600 s limit. It is called by `run_m8_tests_s1`, by `m8_mutants_s1` (before its environment is scrubbed) and by `child_unittest_runner`.
- **The `r03` step of the five M10 regression tools** (byte-identical M10 code, run in-process by the regression successors) starts its children with `-I -B`, without `-S`, with the inherited environment and no time limit.
- **Test files run in-process** start children of their own.

**Two problems follow:**
1. **R1 §2.8 is not met for these children:** every child starts `-I -S`, with the allowlist environment. That has been so throughout stage 1, and was not disclosed. The stage 1 documents' P1-F6 row claimed the opposite for `run_m8_tests_s1` and `m8_mutants_s1` (mistake 20).
2. **Under P, P.4's reaper would confuse them.** In a supervisor such a child is an unregistered child of the supervisor. The reaper would take it for an adopted orphan, and its wait could take the status `subprocess.run` is waiting for.

**Recommended decision:**

**(a) `evkit.child_register`: one registration mechanism for every Python subprocess started in a supervisor's own process.**
- **Where it is installed.** When `tools.evkit` is imported, which is the first import of every successor (`m8_mutants_s1.py:28`, `run_m8_tests_s1.py:17`, `child_unittest_runner.py:18`, and likewise the others) and happens before any successor code runs, evkit:
  - wraps `subprocess.Popen.__init__` with the hook;
  - makes the process a child subreaper (P.2).

  So the hook is in place before `m8_mutants_s1`'s pre-start `dependency.ensure()` (`m8_mutants_s1.py:59`), and before every other AUIF or M10 child. Nothing about AUIF's command or environment is changed to achieve this.
- **What it registers, and what it does not.**

  > The `Popen` hook registers Python subprocesses created in the current process after the hook is installed. This includes those created by in-process code there: AUIF, M10's `r03`, the CR-02 shim, and test modules that a tests runner imports and runs in that same process.
  >
  > It does not intercept process starts made internally by a separately running child process. That includes the CR-02 grandchildren (started inside the `cr02_materiality_mutants.py` child), the children of a process that a test starts, and the browser launched by the Node UI test.
  >
  > Those remain descendants governed by P.5 and the subreaper cleanup rules. They are not `Popen` registrations in the supervisor's register.
- **It is the only registration path.** `evkit.run_child`, `_run_check`, `regression_successor_main.run` and P's own start all create their children through `subprocess.Popen`, so they are registered by the same hook, never twice. The one other start, `os.fork` for B and K.2, registers under the same lock in its own code (P.4).
- **Registration is atomic with creation:**
  - the hook takes the P.4 register lock;
  - it calls the real `Popen.__init__`;
  - it records the new pid, its start time and a `pidfd_open` on it;
  - then it releases the lock.

  The reaper takes the same lock before every scan, so it can never see an unregistered child.
- **One wait owner.** A registered child's `Popen` handle is its sole wait owner. The reaper never waits on a registered pid. It waits only on adopted orphans, which are by definition not in the register.
- **In a leaf** (`run_m2_tests_s1`, `mut_runner_s1`, `run_test_files_s1`), the hook and the subreaper are installed too, because they come with the import.
  - A leaf runs no scans and classifies nothing.
  - Before its `RESULT` line it reaps, with `WNOHANG` on specific pids, any adopted orphan that has already exited.
  - Live ones are left in the tree for its parent supervisor.

**(b) Their command, environment and time limit are left exactly as the immutable code sets them.**
- The hook adds no `-S`, replaces no environment, and imposes no limit. CR-02's existing shim, which adds `-S` today, is unchanged.
- **Why:** changing them would change the behaviour of code that DP-1.2 (B) and the M8 immutability rule keep fixed, and AUIF's own verification under `-S` is untested.

**(c) Attribution and classification of the children started by immutable code:**

| Where the child starts | Its owner | Phase or item | A leak (P.5) gives |
|---|---|---|---|
| `m8_mutants_s1`'s `dependency.ensure()`, before `mutation_main` (`m8_mutants_s1.py:59`) | `m8_mutants_s1` | the run's start, before the preflight | `RUN_ERROR PROCESSES_LEFT run_start`, every mutant `NOT_RUN cause=run_error`, exit 2 |
| `m8_mutants_s1`'s `after()` (`dependency.reverify`) | `m8_mutants_s1` | the run's end, after the end control | `RUN_ERROR PROCESSES_LEFT run_end`, the item lines kept, exit 2 |
| `run_m8_tests_s1`'s `ensure()` in its start checks, and its `reverify()` at the end (`run_m8_tests_s1.py:69`, `:82`) | `run_m8_tests_s1` | the run's start; the run's end | start: `RUN_ERROR PROCESSES_LEFT run_start`, every `FILE` `NOT_RUN`, exit 2. End: `RUN_ERROR PROCESSES_LEFT run_end`, the `FILE` lines kept, exit 2 |
| `child_unittest_runner`'s AUIF verification (`evkit.py:1455`, before its files) | `child_unittest_runner` | the run's start | `RUN_ERROR PROCESSES_LEFT run_start`, every `FILE` `NOT_RUN`, exit 2. Its parent reads an evidence error, so that unit is `ITEM_ERROR` |
| a child started by a test module inside `child_unittest_runner` (for example `tests_m8/test_m8_dependency.py:78`; `ensure()` itself reuses the verified copy, `dependency.py:89`) | `child_unittest_runner` | that file | the file `INDETERMINATE`, its cause on its `CLEANUP` line |
| the `r03` register generators in a regression successor | that regression successor | that step | the step reported as M10's failed check with "(INCOMPLETE: processes left)", the form the successor already uses for a step cut off by its time limit (`evkit.py:2478-2480`). Never a pass. The successors print no `RESULT` line (T-K) |
| a child or grandchild of a unit (any class) | the supervisor that started the unit | that unit | as P.6: the item `INDETERMINATE cause=processes_left`; a control `FAIL cause=processes_left` |

`PROCESSES_LEFT` is a new `RUN_ERROR` code, recorded in the change record.

**(d) Open finding 13,** covering every class the inventory found:

> These children are started by code stage 1 must not change, and do not meet R1 §2.8:
> 1. AUIF's `verify_tree` children: `-I -B`, the caller's environment, 600 s;
> 2. the `r03` register generators of the five M10 regression tools: `-I -B`, no time limit. Their environment is the allowlist, because the successor replaces `os.environ` first;
> 3. CR-02's grandchildren: `cr02_materiality_mutants.py:114`, `-I` without `-S`, 300 s;
> 4. the grandchildren of the M10 tools the successors run unchanged as children (the M10 regression tools' `--step` runs, `mie_static.py`, the wrapper P-group tools): plain `subprocess.run`, the allowlist environment they were given, and no `-S` control;
> 5. processes started by test files run in-process, mostly with no time limit;
> 6. `sabotage_m10_s1`'s UI checks: a Node child, to which `-I` and `-S` do not apply, whose test starts a browser grandchild.
>
> All are contained as descendants under P. None is started under §2.8. The list is complete for what the independent inventory searched (its section 0), and is not claimed beyond that.

**(e) The documents correct their claims** (mistake 20):
- the P1-F6 row (every child of `run_m8_tests_s1` and `m8_mutants_s1` starts `-I -S`);
- the regression successors' docstring ("every Python child starts with -I -S").

The new evidence asserts what each class actually receives, by a probe in each path, recorded in `evidence/audit/`.

**Tests:**
- the hook registers a child that in-process code starts, and the reaper, scanning while that child exits, never waits on it;
- `run_child` and the hook register a child once only;
- `m8_mutants_s1`'s pre-start AUIF children are registered (the hook is shown in place before them);
- each row of (c) is tested: a leak there gives the stated result;
- the existing evidence runs give the same results (B.6, K.2 and the W and M sets).

**The alternative to (b):** the hook adds `-S`, uses the allowlist environment and imposes the item's limit. That changes immutable code's behaviour, and would need its own comparison. It is not recommended in this pass.

## AM-6. The verification gaps (matrix rows 5, 6, 18 and 23, and the supervisor list)

**(a) Forking is single-threaded** (row 5).
- In a fork-based supervisor (B, K.2), the reaper's scans and every other piece of P's machinery run in the main thread.
- Immediately before each `os.fork`, in the main thread, the supervisor checks both `threading.active_count() == 1` and exactly one entry in `/proc/self/task`.
  - No thread can start between the check and the fork: the process has no other thread to start one, and the main thread does nothing in between.
  - If either check fails, it refuses: `RUN_ERROR ENV_THREADS_AT_FORK`, exit 2.
- A case's own threads (for example RG-08's six) run inside its forked child, never in the parent.
- `mutation_main`'s thread pool starts subprocesses, not forks, and is unchanged.

**(b) A forked message is complete at its declared length** (row 6). P.8 step 1 is replaced by this protocol:
1. Within the unit's time limit, read the 4-byte big-endian length, then exactly that many bytes. That is the complete message.
2. **Drain.** Continue reading without blocking until end of file, or until `T_EXIT_AFTER_RESULT` has passed since the message was completed, whichever comes first. This does not depend on the direct child having exited, so a descendant still holding the write end is read from for the whole drain.
3. **A trailing byte** read in the drain makes the item `bad_result`.
4. **A pipe still open at the end of the drain** means a member holds the write end. P.5 finds it, cleans it up, and gives `processes_left`. The run never waits beyond the drain.
5. **Where both a trailing byte and a leak occur,** the cause is `bad_result`, and the `CLEANUP` line records the leak.
6. **The pipe ends:** the parent closes its write end at once after `fork`; the child closes its read end.

**Tests:**
- the hanging-after-result child that closes its pipe (P.10);
- a forked grandchild that holds the write end after the direct child exits, and then writes one extra byte: `bad_result`, with the leak recorded;
- one that holds the write end and writes nothing: `processes_left`.

Neither waits past the drain.

**(c) The supervisors** (rows 3 and 8), replacing P.7's list and F.2 (a)'s. Each tool is counted once:

| Supervisors | Unique tools |
|---|---|
| the wrappers | 19 |
| the `mutation_main` tools, including `sabotage_m10_s1` and `sabotage_m8_s1` | 18 |
| the `regression_sabotage_main` tools | 9 |
| the `mie_sabotage_main` tools (`sabotage_mie1_s1`, `sabotage_mie1_1_s1`) | 2 |
| the fault runners (B), including `run_history_contract_s1`, which has both a fault mode and a case mode | 5 |
| the case runners (K.2), other than `run_history_contract_s1` | 10 |
| `run_m8_tests_s1` | 1 |
| `child_unittest_runner`, whenever it verifies an AUIF copy (AM-2) | 1 |
| the regression successors (`run_regression_m10_s1`, `_m8_s1`, `_m81_s1`, `_m81r1_s1`, `_m8r2_s1`) | 5 |
| `run_cr02_reference_s1` (AM-3) | 1 |
| **Total** | **71** |

- **The leaves** are `run_m2_tests_s1`, `mut_runner_s1` and `run_test_files_s1` (3).
- **The cancellation mechanism of F.2 (a)** is used by all 71 supervisors and the 3 leaves.

**The deepest process tree found:**

```
run_m8_all_s1 (wrapper, supervisor)
└─ run_regression_m8_s1 (regression successor, supervisor)          a FILE or CHECK unit of the wrapper
   ├─ r03 register generators (M10 code in-process; finding 13 class 2)
   └─ run_m8_tests_s1 (supervisor)                                  a unit of the regression successor
      ├─ AUIF verify_tree children, at its start and end (finding 13 class 1)
      └─ child_unittest_runner (supervisor while it verifies AUIF)  one unit per test file
         ├─ AUIF verify_tree children (finding 13 class 1)
         └─ tests_m8 test modules, in-process
            └─ any process a test starts (a descendant; finding 13 class 5)
```

**(d) The run index** (row 18): AM-4.

**(e) CR-02's exit path** (row 23): AM-3.

## AM-7. What stays as decided
- **Every other part of the paper stands as posted:** A to F, K.1 to K.3, the timing constants, the stop rule, I and J.
- **D2, D8, D12, (e), D13, D14 and D15** stay as decided.
- **Open findings 1 to 10** stay open.
- **Findings 11, 12 and 13** are added, as above.
- **The documents' mistake list** gains:
  - mistake 20 (AM-5);
  - mistake 21: the builder wrote P's description of the tests runners from the plan, not from the code (S2), and missed the CR-02 shim and the in-process child starts in its own first scan (S3, S5).

## AM-8. Before implementation
- **The verification** the reviewer required is the matrix and the independent inventory. Both are in `evidence/audit/` for the package.
- **If implementation finds any further mismatch** between this amended paper and the code, it is a stop-rule event.

## AM-9. Change log: what each decision changes in the paper

| Decision | The paper's sections it changes |
|---|---|
| AM-1 | P.2 (the outside-services limit and the containment claim); I.3 (the audit runs again in the evidence); the documents (finding 11) |
| AM-2 | P.1 (units); P.7 (the supervisor list, with AM-6 (c)); P.10 (the nested tests); F.2 (the interrupt in leaves and in `child_unittest_runner`; the last unit); the documents (finding 12) |
| AM-3 | P.9 (scope); P.10 (the CR-02 tests); the documents (finding 13 class 3) |
| AM-4 | P.2 (descriptor 0); P.10 (its test); I.3 (the run index) |
| AM-5 | P.2 and P.4 (the hook, the bootstrap point, the subreaper at import, and the register); P.5 and P.6 (attribution and classification of library children, `PROCESSES_LEFT`); I.1 (new codes); the documents (finding 13, mistake 20) |
| AM-6 | P.4 and B, K.2 (the fork check, `ENV_THREADS_AT_FORK`); P.8 (the drain protocol); P.7 and F.2 (a) (the supervisor list) |
| AM-7 | G (findings 11 to 13; mistakes 20 and 21) |

