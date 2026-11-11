# APG D14 stage 1, corrective pass 2: decision paper (final, for the owner to post)

**BUILDER-EXECUTED: NOT INDEPENDENT.** Prepared by the builder on 2026-11-04 and 2026-11-05 at the product owner's request (`rec/reviews/RECEIVED_OWNER_POST_2026-11-04_1936_CORRECTIVE_PASS_2_DIRECTION.txt`). It authorises nothing until the owner posts it. It accepts nothing, closes no finding, EDR or CF item, and makes no production-readiness claim.

**Draft history.**
- **This final text** is draft 6, with the six targeted edits the reviewer required in its review of draft 6 (`rec/reviews/RECEIVED_REVIEW_2026-11-05_CORRECTIVE_PASS_2_PAPER_DRAFT_6.txt`, SHA-256 `0eb4b108…024c`), and that review's optional evidence suggestions.
  - The reviewer said that, once these edits were made, the paper could be posted without another full review round, provided they introduced no new design choice and no wider scope.
  - **They introduce neither.** The six edits:
    1. P.2: forked children close their inherited descriptors and replace their environment;
    2. P.4: the register lock is held across a direct child's creation and registration;
    3. P.3: a parent link with equal start times is not proven membership, fails closed, and is recorded;
    4. P.10: the hanging-after-result test child closes its result pipe first;
    5. P.2: no secret in the allowlist or the evidence;
    6. P.2 and P.4: `SIGCHLD` is set to its default and checked at start.

    The optional suggestions affect only the evidence: scan ids, exited versus killed, the time to escalation, separate test names, and direct links in the evidence index.
- **Every earlier draft and review is kept beside it:**
  - draft 1 (`66b1e078…39d0`) and its review (`60b75c6e…4853`);
  - draft 2 (`18748735…1f69`) and its review (`e0f64a7a…81ac`);
  - draft 3 (`4a04129c…878f`) and its review (`bb25cd0a…5662`);
  - draft 4 (`8ad3d729…6343`) and its review (`266e847c…59e8`);
  - draft 5 (`0f7fbcc5…d4fb`) and its review (`aef667b5…4da3`);
  - draft 6 (`a4f269b5…cff2`) and its review (`0eb4b108…024c`).

## 0. Basis and status

- **The reviewer's second gate review:** `rec/reviews/RECEIVED_REVIEW_2026-11-04_STAGE1_GATE_2.txt` (`aab60eec…c4f0`). It reviewed freeze `d5f87d6b…85c8` (commit `ec426550`) and did not recommend progression.
- **Status of the current freeze:** unchanged. It is not recorded as the base for stage 2, and nothing has been built or run under this paper.

**The owner's choices.** Every one is recommended by both the builder and the reviewer:

| Choice | Decision |
|---|---|
| A.2: case result version | `kind=cases` becomes `v=3`, and the checker keeps a `v=2` reader |
| B.2: fault-item time limit | 300 s per plant and per control |
| C: import fix reach | the 15 runners and the 18 mutation and sabotage successors (33) |
| F.1: disk floor reached during a run | implement T-0's behaviour |
| F.2: caught interrupt | implement T-0's behaviour |
| K.1: `control_end` after the last item | amend R1 §2.7, as worded in K.1 |
| K.2: in-process cases | each case is supervised in a forked child |
| K.3: versions | `kind=mutation` and `kind=sabotage` also become `v=3`, each with its own schema (K.3), and the checker keeps a `v=2` reader |

## P. One process model for every child (used by B, F.1, F.2 and K.2)

**P.1 Units of work.** A unit is one child the successor starts and then classifies, together with every descendant of that child:
- a mutant's or plant's command;
- a control;
- a test file;
- a test runner started by a mutation or sabotage tool;
- a wrapper group's child;
- a fault plant or control (B);
- a case (K.2).

A successor that starts units is a **supervisor**, whether it was started from a shell or is itself a unit of another supervisor.

**P.2 Containment.**
- **The child subreaper.** At start, every supervisor marks itself a child subreaper: `prctl(PR_SET_CHILD_SUBREAPER, 1)`, through `ctypes` on `libc.so.6`.
  - The return code is checked, and the setting is read back with `prctl(PR_GET_CHILD_SUBREAPER)`.
  - A descendant of its units whose parent ends is then reparented to the nearest live supervisor above it, not to process 1. This holds whatever process group or session the descendant has moved to, including after a `setsid()`.
  - So no descendant can leave the supervisor's process tree.
  - A nested supervisor does the same, so orphans below it come to it first, and to the next supervisor above if it has ended.
- **The child's own group.** Each unit's direct child starts in a new process group (`process_group=0` for a subprocess, `os.setpgid(0, 0)` in a forked child). That is only a convenience. Membership is decided by the tree (P.3).
- **The refusal.** A supervisor refuses at start, `RUN_ERROR ENV_NO_PROCESS_SUPERVISION <reason>`, exit 2, with every item `NOT_RUN`, when any of these is unavailable or fails:
  - `prctl`;
  - the read-back;
  - `/proc`;
  - `os.pidfd_open` and `signal.pidfd_send_signal`;
  - setting `SIGCHLD` to `SIG_DFL` and reading it back as `SIG_DFL` (`signal.getsignal`), which P.4 needs.

  It never runs without containment.
- **Outside services.** A process started on a unit's behalf by an outside service is not a descendant, and is outside this model.
  - **What the units inherit.** Every unit's child gets only:
    - file descriptors 0, 1 and 2, and its result pipe where it has one;
    - the environment allowlist.
  - **How, for each way a child is started:**
    - **a subprocess child:** `close_fds=True`, `pass_fds` for the result pipe only, and `env=` the allowlist;
    - **a forked child (B, K.2):** immediately after `os.fork`, before it calls the plant, control or case callable, the child:
      - closes every inherited descriptor other than 0, 1, 2 and its result pipe's write end (`os.closerange` around the kept ones);
      - replaces its whole environment with the allowlist (`os.environ.clear()`, then the allowlist's values).

      The child never uses the supervisor's register or its lock (P.4). It only runs the callable, writes its message and exits.

    The case and plant comparisons (B.6, K.2) are what show that this does not change a verdict.
  - **No secret in the allowlist.**
    - The allowlist holds no credential, token, password or other secret.
    - If the audit finds a secret-bearing variable in a unit's environment, the builder stops and reports it, by name only.
    - The value is not written to the evidence or the package.
  - **The outside-service audit** (part of P.9, before implementing, from a process started exactly as a unit is started) records each of these, in `evidence/audit/outside_services.txt` in the package:
    1. **Descriptors:** the unit child's open file descriptors (`/proc/self/fd`), each with its target. They are recorded for a subprocess child and for a forked child, as each actually receives them.
    2. **Environment:** the unit child's environment: every variable's name, and its value unless it is secret-bearing. Under the rule above, a secret-bearing variable stops the work.
    3. **Unix-domain sockets:**
       - every socket listed in `/proc/net/unix`, path-named and abstract;
       - for each path-named one, its owner and permissions, and whether the unit's user can connect to it;
       - every socket file found under `/run`, `/var/run`, `/tmp`, `/var/tmp`, `/dev/shm`, the home directory and any `XDG_*` directory present.
    4. **Process-launching interfaces:** session and system buses, service managers (`systemd` system or user instances), `at`, `batch` and `cron` (their binaries, spool directories and permissions), container-runtime sockets, and set-user-id or set-group-id programs on the `PATH` the allowlist gives.
    5. **Network:** the endpoints a unit can reach (the egress allowlist).
    6. **For each finding,** the basis for concluding that a unit cannot use it to have a local process started outside its tree, or that it can.

    The list in 3 and 4 is a minimum, not a limit.
  - **If a reachable service cannot be ruled out,** the stop rule applies: the builder reports before implementing.
  - **A test** asserts the open descriptors and environment a unit child actually receives, for a subprocess child and for a forked child, with the parent holding an extra descriptor and an extra environment variable that the child must not see.

**P.3 Process identity and membership.**
- **A process's identity** is the pair (pid, start time). The start time is field 22 of `/proc/<pid>/stat`. The fields are counted after the last `)` of the line, because the command name in field 2 can hold spaces and parentheses.
- **The parent's identity is recorded too.** Each process observed is recorded with its parent's identity: the parent's pid and that parent's start time, read in the same scan.
- **A parent link counts only when both identities match.** A link from a process to its parent counts for membership only when:
  - the parent's current identity (pid and start time) equals a recorded member's identity; and
  - the parent's start time is not later than the child's.

  So a reused pid never makes an unrelated process a member. Its start time differs from the recorded member's.
- **Equal start times.** Start times are in clock ticks, so a parent and its child can show the same value, and a pid could in principle be reused within one tick.
  - **A link where the parent's start time equals the child's** is ambiguous unless the parent is a direct child of this supervisor. A direct child's identity is certain: it is registered at creation (P.4), and its pid cannot be reused before the supervisor reaps it.
  - **An ambiguous link is not counted as proven membership.** The process is not a member by that link. It is never signalled on the strength of that link alone.
  - **It is recorded,** as `ambiguous=<pid>:<start>` on the unit's `CLEANUP` line, or as a `CLEANUP_AMBIGUOUS <pid>:<start> parent=<pid>:<start>` line if the unit has no `CLEANUP` line.
  - **It cannot escape this way.** When its parent (a member) ends, through cleanup or otherwise, the process is adopted by the supervisor through the subreaper. As an adopted orphan, its identity is certain, because it is now the supervisor's own child. It is then attributed by its recorded identity, or conservatively to every unit in flight (below), and cleaned up and reaped. A unit cleanup is not complete while such a process lives.
- **A remembered process is acted on only while it is the same process:**
  - **it is signalled only this way:** open `os.pidfd_open(pid)`; then re-check that the start time is unchanged; then send the signal through `signal.pidfd_send_signal`. Once the descriptor is open it refers to that process alone, so a reused pid never receives the signal;
  - **it is waited on only by its parent's designated wait owner (P.4).** A pid cannot be reused before its parent reaps it.
- **The unit's members**, at each scan of `/proc`:
  - its direct child;
  - every process linked to it by a chain of matching identities;
  - every orphan adopted by the supervisor, attributed to the unit whose recorded member it was, by its identity.

  The supervisor keeps each unit's member identities from every scan, so an orphan's attribution survives its adoption.
- **An adopted orphan no unit has recorded** (created and orphaned between two scans) is attributed conservatively to every unit in flight at that moment. Each such unit is then a leak (P.6).
- **Alive** means `/proc/<pid>` exists with the recorded start time and a state other than `Z`. A zombie has exited. A zombie that is the supervisor's child must still be reaped (P.4).

**P.4 Wait ownership: exactly one owner for every child's wait status.**
- **One owner per child.**

  | Child | Its only wait owner | How it waits |
  |---|---|---|
  | a direct child started as a subprocess | the unit's `Popen` handle | `Popen.poll()`, which is `waitpid(pid, WNOHANG)` on that pid alone |
  | a direct child started by `os.fork` | the unit's fork handle | `os.waitpid(pid, os.WNOHANG)` on that pid alone |
  | an adopted orphan (a process whose parent is now the supervisor, not in the register of direct children) | the supervisor-level reaper | `os.waitpid(pid, os.WNOHANG)` on that pid alone |

- **The register, and its lock.** The supervisor keeps a register of every direct child's identity, under one lock.
  - **At creation,** the supervisor acquires that lock before it creates a direct child (`Popen` or `os.fork`). It holds it through the registration of the returned pid and start time, with a `pidfd_open` on the new child, and only then releases it.
  - **The reaper** acquires the same lock before it examines or registers any child of the supervisor.
  - So the reaper can never see a direct child that is not yet registered, however quickly that child exits.
  - The forked child itself never touches the register or the lock (P.2).
  - The reaper never waits on a pid in the register.
  - A unit handle never waits on a pid it did not start.
  - No code waits on `-1` or on a process group.
  - So no two mechanisms ever wait on or reap the same process.
  - Python's own `subprocess._cleanup` acts only on `Popen`-owned pids, so it is part of the `Popen` owner, not a second one.
- **`SIGCHLD`** keeps its default disposition, so the kernel never reaps a child automatically.
- **Every wait is non-blocking,** polled with `WNOHANG`. Nothing waits on a process past a deadline.
- **Adopted zombies.**
  - At each scan, the reaper registers every adopted child of the supervisor, alive or zombie, with its identity and its unit (P.3), and reaps the zombies.
  - A unit's cleanup is complete only when no member is alive **and** every adopted orphan attributed to it has been reaped.

**P.5 One cleanup contract, for every terminal path:** a normal result, a timeout, a crash, a malformed or incomplete message, an exception, an interrupt, a disk stop, or a cancellation.

**The time values.** Each is a named constant in `tools/evkit.py`, recorded in the change record. Every supervisor prints them on one `LIMIT` line beside its `SELECTED` line (or at start, where there is none), with its item limit where it has one: `LIMIT item=<n>s exit_after_result=2s grace=10s grace_cancelled=2s escalate=10s kill_verify=5s`.

| Constant | Value | What it bounds |
|---|---|---|
| `T_EXIT_AFTER_RESULT` | 2 s | how long a forked unit's direct child may take to exit after its result message has been validated |
| `T_GRACE` | 10 s | the `SIGTERM` grace for a supervisor's own units, in ordinary cleanup |
| `T_GRACE_CANCELLED` | 2 s | the `SIGTERM` grace a supervisor uses for its own units when it is itself cleaning up because it was cancelled by a signal (F.2) |
| `T_ESCALATE` | 10 s | how long a supervisor waits, after sending `SIGTERM` to a unit whose child is a nested supervisor, for that child to exit, before it kills the unit's whole remaining tree (P.7). It applies whatever the supervisor's own grace is |
| `T_KILL_VERIFY` | 5 s | how long, after `SIGKILL`, the supervisor re-scans for the unit's members to be gone |

**The steps:**
1. **The trigger.**
   - **A timeout, interrupt, disk stop or cancellation:** the supervisor stops the unit by sending `SIGTERM` to the direct child, and goes to step 3.
   - **A subprocess unit with no stop:** it polls the direct child until it exits, within the unit's time limit. The exit fixes its outcome (P.8).
   - **A forked unit with no stop:** it reads the result message within the unit's time limit. A validated message fixes the outcome (P.8). It then polls the direct child for up to `T_EXIT_AFTER_RESULT`.
     - **A direct child still alive after that** is a process left behind. It is not waited on further, and is handled as a member in step 4.
     - So a child that sends a valid result and then hangs never holds up the run.
2. **The scan.** The supervisor scans the unit's members.
3. **No members left.** If no member is alive, go to step 6.
4. **Members left.** If any member is alive, the direct child included, this is a leak on the normal path too.
   - It sends `SIGTERM` to each, re-scanning every 0.1 s and signalling every newly found member. A process that forks during cleanup is found this way. This lasts for up to the grace in force: `T_GRACE`, or `T_GRACE_CANCELLED`; for a unit whose child is a nested supervisor, `T_ESCALATE`.
   - It then sends `SIGKILL` to each member still alive, the newly found ones included.
   - It re-scans every 0.1 s until two consecutive scans find none alive, for up to `T_KILL_VERIFY`. Each scan's count and the deadline reached are kept for the `CLEANUP` record.
5. **Nothing waits indefinitely.** Every wait in steps 1 to 4 has the deadline stated there.
6. **Reaping.**
   - The direct child is reaped by its owner, and every adopted orphan of the unit by the reaper (P.4).
   - The supervisor claims to have reaped only its own children (its direct child and its adopted orphans).
   - A descendant that was still another live process's child when it exited is shown gone by the scans, and is not said to have been reaped by this supervisor.
7. **Members that would not die.** If any member is still alive at the end of step 4:
   - no reap is claimed for it;
   - the run adds `RUN_ERROR CLEANUP_INCOMPLETE <unit id> <pid>:<start time>[,<pid>:<start time>…]`, exit 2;
   - the unit is as in P.6;
   - nothing waits on it any longer.
8. **The records.**
   - **For every unit that had members alive at step 3:** `CLEANUP <unit id> by=<supervisor tool>:<pid> child=<pid>:<start> pgid=<n> scan=<first scan id>-<last scan id> left=<pid>:<start>[,…] exited_in_grace=<pid>:<start>[,…] or - killed=<pid>:<start>[,…] or - sigterm=<n> sigkill=<n> scans=<n> deadline=<grace or kill-verify, if one was reached, else none> escalated_after=<seconds, for a supervisor unit, else -> ambiguous=<pid>:<start>[,…] or - remaining=<pid>:<start>[,…] or -`. Scan ids count up through the run, so a reviewer can tell which identities were seen in which scan.
   - **Before the `RESULT` line:** `CLEANUP_SUMMARY units=<n> leaked=<n> remaining=<n>`, where:
     - `leaked` counts the units that had members alive at step 3, whether or not they were then killed;
     - `remaining` counts the processes still alive after step 4.

     The order of the `CLEANUP` lines is the order of the units' ids.
9. **The `RESULT` line** is printed only after the cleanup of every unit has finished. It is never printed while a member of any unit is alive, except as the evidence error of step 7.

**P.6 How a leak is classified.**
- **An item** (a mutant, a plant, a test file, a wrapper group or a case) whose unit had members alive at step 3 is `INDETERMINATE` with cause `processes_left`, whatever its result. This includes a direct child that outlived `T_EXIT_AFTER_RESULT`.
  - It is never `KILLED`, `CAUGHT`, `PASS` or `COMPLETED` on a result its leftover processes could have affected.
  - Where an item's line has no cause field (a tests-kind `FILE` line, a wrapper `FILE` or `CHECK` line), its state is `INDETERMINATE`, and the cause is on its `CLEANUP` line.
- **A control** keeps B.4's control rule: `FAIL cause=processes_left`.

**P.7 Nested supervisors: who owns what.**
- **Each supervisor owns the units it starts directly.**
  - It alone stops, cleans up and reaps them and its adopted orphans, and it alone attributes their members.
  - No two supervisors reap the same process: only a process's current parent can reap it, and each supervisor waits only as P.4 says.
- **A supervisor unit** is a unit whose direct child is one of the successors that themselves start units:
  - the mutation and sabotage tools;
  - the fault, case and tests runners;
  - the wrappers (F.2 (a)).

  A supervisor knows this from the command it starts.
- **Cancellation propagates downwards.** To stop a supervisor unit, the outer supervisor sends `SIGTERM` to its child. The nested supervisor's handler sets its flag (F.2). It cleans up its own units with `T_GRACE_CANCELLED` (and `T_ESCALATE` for any supervisor units of its own), prints its own `INTERRUPTED` and `RESULT` lines, and exits.
- **The outer supervisor escalates after `T_ESCALATE`.** If the nested supervisor has not exited by then:
  - the outer sends `SIGKILL` to every remaining member of the unit's tree, the nested supervisor included;
  - the orphans then come to the outer through the subreaper, and it adopts and reaps them;
  - the nested supervisor's partial output is kept in the log, and is never used to classify the outer item (F.2 (b)).

  **A nested supervisor with supervisor units of its own** may not finish within its parent's `T_ESCALATE`. The parent's escalation then ends it. That is the designed outcome, not a failure of containment.
- **The outer supervisor always checks** that its whole unit tree is gone before its own `RESULT` line.
- **A nested result is never turned into a pass.** A nested supervisor's `INDETERMINATE` or `EVIDENCE_ERROR` result is read by its parent through the existing consumer rules (`check_output`, the child classification). It cannot make the parent's item pass.

**P.8 When an item or control counts as completed.**
- **The outcome is fixed when the unit's result has been received and validated.**
  - **For a forked unit (B, K.2),** "received and validated" means all of these, in order:
    1. the complete message has been received: a 4-byte big-endian length, then exactly that many bytes, then end of file;
    2. the framing is valid: the length is within the 1 MiB limit, and nothing follows the message;
    3. the bytes decode as UTF-8 and parse as JSON;
    4. the object has exactly the keys and types of one of the unit's message forms (B.3, K.2);
    5. its content is valid for that unit's result contract. A plant's or control's failed cases must be ids of the runner's pinned or enumerated cases, and an exception type must be a token.

    A message that fails step 1 is `crash`. A message that fails any of steps 2 to 5 is `bad_result`. A merely parseable JSON object never fixes an outcome.
  - **For a subprocess unit:** when the direct child has exited and its output has been classified by its existing rules.
- **Cleanup comes after.** It decides only whether that outcome stands. A leak gives P.6 (items) or B.4 (controls).
- **An interrupt after the outcome is fixed** does not turn it into `NOT_RUN` or `INDETERMINATE cause=interrupted`. Cleanup continues to its end, because the handler never interrupts it.
  - For the run's last unit, that signal is `SIGNAL_AFTER_COMPLETION`.
  - For an earlier unit, the run is interrupted from the next unit on.
- **An interrupt before the outcome is fixed** makes the unit interrupted (F.2).

**P.9 Where this applies, and the audit before implementing.**
- **What it replaces:** every successor child-start site in `tools/evkit.py`. Today `subprocess.run(…, timeout=…)` kills only the direct child.
- **The timeout classification is unchanged:** it stays `INDETERMINATE`.
- **The audit.** Before implementing, the builder lists:
  - every successor child-start site;
  - every path by which a successor runs beneath another successor or an M10 tool;
  - the outside-service checks of P.2.

  The full inventory and results go into `evidence/audit/` in the package. If any site or path cannot be brought under P, or any outside service cannot be ruled out, the builder stops and reports.

**P.10 Tests.**
- **Nested two levels.** A mutation tool's child test runner starts a test-file child, which starts a grandchild. The grandchild is tested three ways:
  - one hangs;
  - one calls `setsid()` and double-forks;
  - one leaves a background process after a passing result.

  On a timeout, on an interrupt and on the normal path, every process, by the pid and start time the test processes record, is shown gone before the `RESULT` line. The `CLEANUP` lines show which supervisor cleaned up what.
- **A direct child that sends a valid result and then hangs without exiting** (its own test, `…_valid_result_then_hangs`), for a forked plant (B) and a forked case (K.2). The injected child:
  - writes the complete valid message;
  - closes its result pipe's write end, so the parent reaches end of file and validates the message (P.8);
  - then deliberately stays alive.

  The supervisor stops waiting after `T_EXIT_AFTER_RESULT`, detects the child as left behind, and cleans it up;
  - the item is `INDETERMINATE cause=processes_left`, not a clean completion;
  - no `RESULT` line is printed while the child is alive.

  A variant whose child ignores `SIGTERM` is killed by `SIGKILL`. A variant that cannot be killed (simulated) gives `CLEANUP_INCOMPLETE`.
- **Concurrent orphan attribution:**
  - two units in flight (`--jobs 2`);
  - one creates a descendant whose parent exits between scans;
  - the supervisor adopts it and attributes it conservatively;
  - an unrelated process started by the test outside the supervisor's tree survives;
  - both units' classifications and `CLEANUP` records are as P.3 and P.6 say.
- **Reused pids, simulated through the identity checks:**
  - a remembered pid is taken by an unrelated process: it is not signalled;
  - a recorded parent's pid is taken by an unrelated process that has a child of its own: that child is not counted as a member.
- **Wait ownership** (its own test, separate from the one above): in a run with two concurrent units, each direct child's exit status is collected by its own handle and every adopted orphan by the reaper, and no wait status is lost or taken twice. An adopted zombie is reaped before its unit's cleanup is complete.
- **The registration race** (its own test, `…_child_exits_immediately`): a direct child that exits immediately, with the reaper made to scan at the same moment. Its wait status is collected only by its own handle, and it is never registered as an adopted orphan.
- **Equal start times** (simulated through the identity check): an ambiguous parent link is not counted as membership, is recorded, and the process is still cleaned up once it is adopted.
- **`SIGCHLD`:** a supervisor started with `SIGCHLD` ignored refuses with `ENV_NO_PROCESS_SUPERVISION`, unless it can set and read back `SIG_DFL`.
- **Cleanup edge cases:**
  - a unit that forks repeatedly during cleanup, with the scan count and the deadline reached recorded;
  - a member that ignores `SIGTERM`;
  - a member that cannot be killed (simulated): `RUN_ERROR CLEANUP_INCOMPLETE`, exit 2, and the run ends without waiting on it.
- **The nested timings:** a nested supervisor cancelled by its parent finishes within `T_ESCALATE`, and one made to hang is killed at `T_ESCALATE`.
- **A nested result kept.** A nested supervisor's `INDETERMINATE` result: its parent's item is not a pass.
- **The refusals:** `ENV_NO_PROCESS_SUPERVISION`, when `prctl`, its read-back or `pidfd_open` is made unavailable in a temporary copy. When it works, the supervisor is shown to be a subreaper.
- **`/proc/<pid>/stat` parsing:** a test process whose command name contains spaces and parentheses is identified correctly.
- **What a unit child inherits:** its open descriptors and environment, as P.2 says.

## A. Open finding 10: the `kind=cases` result contract, the checker and their tests (one authorisation)

**A.1 The new contract: `kind=cases`, `v=3`.** This amends R1 §2.7 for `kind=cases`.

**The new field.** `suites=<ids>` comes immediately after `suites_selected`.

**The order of a case run, and which refusals keep a resolved selection:**

| Step | What | A refusal at this step |
|---|---|---|
| 1 | the early start checks (`evkit.start`: isolation flags, `site`, `sitecustomize`, `sys.path`, the working directory, the interpreter record, the disk floor, and process supervision, P.2) | **no resolved selection.** The environment that would read the pins is not trusted, so the pins are not read. |
| 2 | reading the pins, including `case_inventories/<tool>` in `tools/expected_counts.json` | **no resolved selection** |
| 3 | resolving the selection from that pinned inventory and the `--suite` and `--only` options | **no resolved selection** (`SELECTION_INVALID`, below) |
| 4 | the guarded imports (C), the trusted harness first | the resolved selection is kept |
| 5 | loading the candidate path (`--path`), with its trusted-name checks (P3-B04) | the resolved selection is kept |
| 6 | comparing the harness's own inventory with the pins | the resolved selection is kept |
| 7 | the cases (K.2) | the resolved selection is kept |
| 8 | the end checks (`IMPORT_END`, import identity) | the resolved selection is kept |

- **"No resolved selection"** means `suites=-`, `suites_selected=0`, `selected=0`, no `CASE` record, and the empty-selection hash below.
- **"Kept"** means `suites` lists the resolved selection, and its cases not run are `NOT_RUN`.
- **What changes from today.** Today an environment refusal prints the selection anyway: on the current freeze, `python3.13 -I tools/run_contracts_s1.py --suite audit_log`, run without `-S`, prints `suites_selected=1 selected=14`. Under `v=3` it prints no resolved selection.
- **Why a failed guarded import still has a resolved selection:** the selection comes from the pins (step 3) before the import (step 4). The current `cases_main` already resolves it from the pinned inventory (`sel_pairs`).

**The resolved selection:**
- **When every requested suite and case is pinned,** it is the requested pinned suites with `--suite`, or every pinned suite without it. This holds whether or not `--only` selects a case in a suite, and whether or not anything runs.
- **When any requested suite or case is not pinned:** `RUN_ERROR SELECTION_INVALID`, and no resolved selection.
  - This replaces today's mixed form (`--suite audit_log --suite nope` prints `suites_selected=1 selected=14` today).
  - **It applies to `kind=cases` only.** D12's owner-accepted refusal form is unchanged for the mutation, sabotage, fault-runner and wrapper refusals.

**The rules of the line:**
- `<ids>` is sorted, comma-separated, each once, every one a pinned suite of the tool. It is `-` for an empty selection;
- `suites_selected` is the number of ids;
- every suite a `CASE` record names is in `suites`;
- `case_inventory_sha256` is `sha256_lines` over the pinned case ids of exactly those suites.

**The empty selection's hash** is `sha256_lines([])`, the SHA-256 of the empty string: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

All other fields and rules are as in `v=2`.

**A.2 Versions.**
- **Who writes `v=3`:** every current case runner. Current consumers validate `v=3`.
- **Who reads `v=2`:** the checker keeps a `v=2` reader for the historical evidence. A `kind=cases v=2` line is checked under the `v=2` schema, with the (a′) rule as frozen, and is never read as `v=3`.
- **A `kind=cases v=3` line without `suites`** is rejected.
- **The mutation and sabotage kinds:** as K.3 decides. The other kinds stay at `v=2`.

**A.3 The checker (`v=3`).**
- It verifies `case_inventory_sha256` against exactly the listed suites.
- It rejects:
  - `suites` that is unsorted, duplicated, malformed or unpinned;
  - `suites` whose count disagrees with `suites_selected`;
  - `suites` that misses a suite a `CASE` record names;
  - `suites=-` with any non-zero `suites_selected` or `selected`;
  - `suites=-` with any hash other than `e3b0c442…b855`.
- Consumers read child results only through `check_output`.

**A.4 Tests.** On the real runners:
- a full run;
- a single-suite partial run;
- the partial run with more pinned cases than printed;
- `--suite record_store --suite audit_log --only AL-01`;
- refusals with no `CASE` record: an unknown suite, an unknown case, and pinned and unpinned suites mixed;
- an early environment refusal (step 1) and an unreadable pins file (step 2), each with no resolved selection;
- a refusal at each of steps 4, 5, 6 and 8, each keeping its resolved selection;
- for each case runner, an import failure that keeps its resolved selection, with `suites` and the hash asserted.

On constructed lines through the checker:
- a hash of a different combination of suites;
- each malformed form in A.3, including `suites=-` with a wrong hash;
- a `v=3` line without `suites`;
- a `v=2` line read under `v=2`.

The section 2C demonstration is rerun, and must show only the true selection accepted.

## B. Point 24: the five fault runners

**B.1 What changes.**
- **The runners:** `tools/run_faults_s1.py`, `tools/run_history_contract_s1.py`, `tools/run_m3_faults_s1.py`, `tools/run_m5_faults_s1.py`, `tools/run_m6_faults_s1.py`, through `evkit.faults_main`.
- **The parent state:** the runner's state after its start checks, its guarded imports (C), the pins and the preflight, fixed before the first child.
- **The children:**
  - each of the two controls (the reference implementation, a read-only probe that returns its failed cases) and each plant is forked from that same parent state, as a unit under P;
  - nothing a control or plant does in memory reaches the parent or a later plant;
  - the difference from today: today they share one process, and `run_history_contract_s1`'s result cache (`_CACHE`) is no longer shared.
- **What a change means:** any change in a plant's verdict, a control's outcome, the run's status or exit, or a `CONTROL` record's value or cause is a stop-rule event, not an accepted change.
- **What a child does:**
  - it runs the unchanged callable;
  - it writes one length-prefixed JSON message to its pipe, in one of three forms: `{"failed": [<case id>, …]}`, `{"exception": "<type>"}` or `{"child_error": "<type>"}`;
  - it ends with `os._exit(0)`.
- **The child's own failure.** If encoding or writing its message raises, the child catches it and tries once to write the fixed message `{"child_error": "<type>"}`. If that fails too, it ends with `os._exit(70)`. The status 70 is reserved for this.
- **What the parent does:**
  - it reads the pipe against a deadline on the monotonic clock;
  - it closes the pipe on every path;
  - it fixes the outcome (P.8), then cleans up under P.5.

**B.2 The time limit.**
- **The value:** `FAULT_ITEM_TIMEOUT_S = 300`, a named constant in `tools/evkit.py`, per plant and per control.
- **Why it is new:** M10's fault runners have no limit, so there is no M10 value. The 300 s is the per-item limit M10's mutation tools use.
- **Where it is recorded:**
  - every fault run's `LIMIT` line (P.5) shows `item=300s`;
  - the in-tree change record and the documents state it.
- **No `--timeout` option** is added (consistent with D2). Tests shorten the limit in their temporary copy.

**B.3 The plant outcomes** (the boundaries between them are those of K.2):

| What happened | Outcome |
|---|---|
| a validated `failed` message (P.8) | `CAUGHT` or `MISSED`, as now |
| a validated `exception` message (an exception escaping the plant) | `ITEM_ERROR cause=exception_<type>` |
| a validated `child_error` message, or no complete message with exit status exactly 70 | `ITEM_ERROR cause=child_error` |
| the deadline passed with no complete message | `INDETERMINATE cause=timeout`, with its `TIMEOUT` line in the D13 form |
| the child ended (any other exit status, or a signal) before completing its message | `INDETERMINATE cause=crash` |
| a complete message that fails P.8's steps 2 to 5 | `INDETERMINATE cause=bad_result` |
| processes left (P.6), the direct child included | `INDETERMINATE cause=processes_left` |
| an interrupt before the outcome was fixed (F.2) | `INDETERMINATE cause=interrupted` |

**A note on status 70.** Code under test that itself ends with status 70 before writing would be reported `child_error`. That is `ITEM_ERROR`, exit 2, never a catch.

None of the `INDETERMINATE` outcomes is ever `CAUGHT`.

**B.4 The control outcomes (T-0 R4's control rule), for a control that completed:**
- **`PASS`:** only for a well-formed result with no failed case;
- **`TIMEOUT`:** for the deadline;
- **`FAIL` with its cause, for every other completed outcome:**
  - `reference_failed_<n>`;
  - `exception_<type>`;
  - `crash`;
  - `bad_result`;
  - `processes_left`.

The `CONTROL` line gives the value and cause (for example `CONTROL end CONTROL_TIMEOUT cause=timeout`).

**A control that did not complete:**
- **The start control interrupted before its outcome was fixed (P.8):**
  - the result field is `control_start=FAIL` (the start control did not pass, which is all the start rule needs), and every plant `NOT_RUN`;
  - its diagnostic line is `CONTROL start CONTROL_INTERRUPTED cause=interrupted`. That marks it as interrupted, never as a completed failure.
- **The end control stopped before its outcome was fixed** (an interrupt, or its copy refused under F.1): it has no completed outcome.
  - `control_end=NOT_RUN` (K.1);
  - the diagnostic line is `CONTROL end CONTROL_NOT_RUN cause=interrupted` or `cause=disk_below_floor`;
  - **it is never also recorded as `FAIL`.**
- **The checker (K.3)** validates each diagnostic line against its result field:
  - `CONTROL start CONTROL_INTERRUPTED` only with `control_start=FAIL` and an `INTERRUPTED … at=control_start` line;
  - `CONTROL end CONTROL_NOT_RUN` only with `control_end=NOT_RUN` and the stop record of K.1;
  - a completed `CONTROL` line's value equal to its field.

**These control rules hold for every control,** in the mutation and sabotage tools (`mutation_main`, `control`) as well as the fault runners.

**The run:**
- **A start control that does not pass:** every plant `NOT_RUN`, exit 3.
- **A completed end control that does not pass:** the plant lines are kept, exit 3.
- **Every run** ends with its `RESULT` line.

**B.5 Tests, for each of the five runners:**
- a plant that hangs;
- a plant whose child spawns a descendant and hangs;
- a plant that leaves a background descendant after a valid result (`INDETERMINATE cause=processes_left`);
- a plant that crashes;
- incomplete and malformed messages;
- a plant that raises (`ITEM_ERROR`, exit 2);
- the controls, at the start and at the end: a fail, a timeout, a crash, a malformed result, a leaked process and an interrupt before the outcome (`CONTROL start CONTROL_INTERRUPTED`, `CONTROL end CONTROL_NOT_RUN`), each with its `CONTROL` line and `RESULT` values asserted;
- each output through `check_output`.

The test evidence records each child's process and group ids and the `CLEANUP` lines.

**B.6 The comparison with the current freeze.** The full runs on the new freeze are compared with the current freeze's runs (`d5f87d6b…85c8`):
- all 111 plant verdicts;
- both control outcomes and their `CONTROL` values and causes (not their timings);
- each run's status and exit.

They must be equal.

## C. Open finding 9: import-time crashes

**C.1 What moves.** In each runner below:
- every listed module-level import or load moves into the guarded start path, after `evkit.start`'s checks (and, for case runners, after the selection is resolved, A.1);
- so does every module-level statement that uses it;
- P3-B04's order is kept: the trusted harness is imported before any candidate path is added;
- nothing listed is imported or executed before the guard.

**The 15 runners finding 9 names:**

| Runner | Imports and loads that move |
|---|---|
| `tools/run_faults_s1.py` | `apg.contracts.run`, `apg.contracts.framework.ContractEnv`, `apg.faulty_impls.FAULTS`, `apg.reference_impl` (four names), and `PLANTS` |
| `tools/run_history_contract_s1.py` | `E.load_m10_prefix("run_history_contract", …)` and `STORES` |
| `tools/run_m3_faults_s1.py` | `apg.ingest.contracts_m3`, `apg.ingest.reference_m3`, `apg.ingest.faulty_m3.FAULTS`, and `PLANTS` |
| `tools/run_m5_faults_s1.py` | `apg.det.contracts_m5`, `apg.det.reference_m5`, `apg.det.faulty_m5.FAULTS`, and `PLANTS` |
| `tools/run_m6_faults_s1.py` | `apg.mkt.contracts_m6`, `apg.mkt.reference_m6`, `apg.mkt.faulty_m6.FAULTS`, and `PLANTS` |
| `tools/run_contracts_s1.py` | `apg.contracts.run`, `apg.contracts.framework.ContractEnv`, `apg.reference_impl` (four names) |
| `tools/run_det_corpus_s1.py` | `apg.det.corpus_det` |
| `tools/run_fin_corpus_s1.py` | `apg.fin.corpus_fin` |
| `tools/run_guard_contract_s1.py` | `apg.contracts.framework.ContractEnv`, `apg.contracts.record_store_guard_contract.run_guard_suite`, `apg.reference_impl` (four names) |
| `tools/run_ingest_corpus_s1.py` | `apg.tenancy`, `apg.ports.TenantMismatch`, `apg.reference_impl` (four names), `apg.ingest.corpus`, `apg.ingest.demo_setup`, `apg.ingest.pipeline`, `apg.ingest.mapping.Limits` |
| `tools/run_m3_contracts_s1.py` | `apg.ingest.contracts_m3`, `apg.ingest.reference_m3` |
| `tools/run_m5_contracts_s1.py` | `apg.det.contracts_m5`, `apg.det.reference_m5` |
| `tools/run_m6_contracts_s1.py` | `apg.mkt.contracts_m6`, `apg.mkt.reference_m6` |
| `tools/run_m91_contracts_s1.py` | `apg.api.contracts_m9`, `apg.api.reference_m9` |
| `tools/run_mkt_corpus_s1.py` | `tests.corpus_mkt` |

**The 18 mutation and sabotage successors.** In each, the module-level `E.load_tool_module(...)` call moves, with everything that load executes, and every module-level statement that uses its result:

| Successor | M10 file loaded | Module-level statements that use it |
|---|---|---|
| `tools/f67_mutants_s1.py` | `f67_mutants` | none |
| `tools/f671_mutants_s1.py` | `f671_mutants` | `F = L.F` |
| `tools/f672_mutants_s1.py` | `f672_mutants` | `F = L.F` |
| `tools/f673_mutants_s1.py` | `f673_mutants` | `F = L.F` |
| `tools/f674_mutants_s1.py` | `f674_mutants` | `F = L.F` |
| `tools/m2_mutants_s1.py` | `m2_mutants` | none |
| `tools/m3_mutants_s1.py` | `m3_mutants` | none |
| `tools/m4_mutants_s1.py` | `m4_mutants` | none |
| `tools/m5_mutants_s1.py` | `m5_mutants` | none |
| `tools/m6_mutants_s1.py` | `m6_mutants` | none |
| `tools/m7_mutants_s1.py` | `m7_mutants` | none |
| `tools/m73_store_mutants_s1.py` | `m73_store_mutants` | none |
| `tools/m8_mutants_s1.py` | `m8_mutants`, which itself imports `apg_auif.dependency` at its top | `TIERS` |
| `tools/m91_mutants_s1.py` | `m91_mutants` | none |
| `tools/mie_mutants_s1.py` | `mie_mutants` | none |
| `tools/mie11_mutants_s1.py` | `mie11_mutants` | `Q = L.M` |
| `tools/sabotage_m10_s1.py` | `sabotage_m10` | none |
| `tools/sabotage_m8_s1.py` | `sabotage_m8` | none |

**The refusal.** `RUN_ERROR IMPORT_FAILED <module> <type> <message>` (a new code), then the `RESULT` line, exit 2:
- **fault runners, mutation and sabotage tools:** every pinned item `NOT_RUN cause=run_error`, `preflight=NOT_RUN`, `control_start=NOT_RUN` (the form decision (c) gave a failed mutant list);
- **case runners:** the resolved selection of A.1, its cases `NOT_RUN`.

**C.2 Tests, for each of the 33 runners:**
- in a temporary copy, the import or load is made to fail;
- the run passes its start checks first;
- nothing listed is imported first;
- the output is the `IMPORT_FAILED` line and a terminal `RESULT` line, exit 2, with no traceback in its place;
- every selected item is `NOT_RUN`, and the checker accepts the output as `EVIDENCE_ERROR`;
- for the case runners, the resolved selection is asserted.

**C.3 The wrapper consumer paths,** each tested with its real wrapper and the failing child in a temporary copy:

| Wrapper group | Child it starts | Group kind | Expected result |
|---|---|---|---|
| `run_m3_all_s1` G03 | `run_contracts_s1` | `kind=cases` (a `FILE` group) | group `ITEM_ERROR`, wrapper exit 2 |
| `run_m3_all_s1` G04 | `run_faults_s1` | `kind=sabotage` (a `FILE` group) | group `ITEM_ERROR`, wrapper exit 2 |
| `run_m7_all_s1` G15 | `m7_mutants_s1 --baseline` (its pinned tool hash is `m7_mutants_s1.py`'s) | class B, a `CHECK` group | group `ITEM_ERROR`, wrapper exit 2 |

No wrapper starts `sabotage_m10_s1` or `sabotage_m8_s1`, or a mutation tool other than through a class B baseline group (`wrapper_groups_v3.csv`). Their consumers are the run index and the checker, as tested in C.2.

## D. The 36 plants whose target is not exactly once (open finding 2)

- They stay refused by the preflight, and their targets are not repaired in this pass.
- They are excluded from every coverage claim, and finding 2 stays open.

## E. The missing tests, from the mapping's points

Each point gets its own test. Where M10 turns out not to have the defect, that is recorded as found, and no failing M10 half is manufactured.

| Point | What the test shows |
|---|---|
| 1 | A real mutation tool whose kill oracle names a missing test file. M10 half: M10's own kill line, asserted literally. Successor: `ITEM_ERROR`, never `KILLED`. |
| 2 | See E.2. **Point 2 stays partly open.** |
| 3 | The start line `IMPORT apg <real path>` asserted on a real runner. |
| 4 | M10 from a decoy working directory: what it actually imports is asserted, and recorded as found. The successor from a non-root directory, through a real runner: `ENV_CWD`. |
| 6 | The disk floor reached during a run, under F.1. |
| 7 | The M10 halves of the four child-isolation cases. |
| 8 | M10's timeout and crash attribution asserted in M10's literal text. |
| 9 (D13) | For a timeout, the `TIMEOUT` line's command matches a timing for the same command on the `CONTROL end` line of the same log. |
| 12 | A real non-matching pattern through `m3_mutants_s1`. |
| 15 | See E.15. |
| 17 | P7-B2: the real `apg` import path asserted. ML-01's kill attribution compared with M10's. |
| 20 | E1-C8: the genuine-kill attribution compared with M10's for the C8 cases. |
| 22 | Asserted directly, and also through the checker: the F11 records for `mut_runner_s1`'s failing file and the M8 tiers; the `mut_runner_s1@standalone` pin; the `TEST` lines. |
| 25 | `check_output` on each of these outputs: `run_m7_all_s1 --group 0` and `--range 5-3`, plus one stubbed-child group run; `run_m8_all_s1 --group 0` and `--range 5-3`, plus one stubbed-child group run; `run_f672_all_s1 --group 11` refused with `EXCLUSION_LIST_MISMATCH`; `run_f674_all_s1 --group 10` (a success output, the case the mapping named); and the E.15 refusals. |
| 26 | Real fail-fast on the real child runner, with a failing first test file, inside a mutation tool (F1), an M8 tier (F7) and a sabotage tool (F8): the files after the first failure did not run, and the F11 records are verified. F11 also on `mut_runner_s1` and the M8 tiers. |

**E.2 Point 2: what is compared, and what is not.**

**Golden outputs.** M10's six golden runners have no successor and are byte-identical in the stage 1 tree:
- `tools/run_golden.py`, `run_golden_det.py`, `run_golden_fin.py`, `run_golden_m3.py`, `run_golden_mie1.py`, `run_golden_mkt.py`.

Each is run on a fresh extraction of the M10 archive and on the stage 1 tree. Their full outputs and exit codes must be identical.

**Contract, corpus and fault outputs.** Each M10 runner is run beside its successor on the unchanged tree, and their verdicts are compared case by case or plant by plant. The `RESULT` format is not compared. The pairs:

| M10 runner | Successor |
|---|---|
| `run_contracts` | `run_contracts_s1` |
| `run_det_corpus` | `run_det_corpus_s1` |
| `run_fin_corpus` | `run_fin_corpus_s1` |
| `run_guard_contract` | `run_guard_contract_s1` |
| `run_ingest_corpus` | `run_ingest_corpus_s1` |
| `run_m3_contracts` | `run_m3_contracts_s1` |
| `run_m5_contracts` | `run_m5_contracts_s1` |
| `run_m6_contracts` | `run_m6_contracts_s1` |
| `run_m91_contracts` | `run_m91_contracts_s1` |
| `run_mkt_corpus` | `run_mkt_corpus_s1` |
| `run_history_contract` | `run_history_contract_s1` |
| `run_faults` | `run_faults_s1` |
| `run_m3_faults` | `run_m3_faults_s1` |
| `run_m5_faults` | `run_m5_faults_s1` |
| `run_m6_faults` | `run_m6_faults_s1` |

**The M2 count, at fixed values.**
- **M10's list** (`tools/m2_mutants.py`, SHA-256 `fe1fd878fee975dff6dfdbdf27a7124665228a6efef624c396b40f7d68cd157b`) has 199 ids.
  - **One is invalid on M10:** `RI10-query-crosses-tenants`, at position 51 of 199. Its target text occurs 0 times in M10's `reference_impl.py`. Under run instruction R6 (2026-10-30) it is recorded `INVALID_MUTATION_TARGET`.
  - So M10 has 198 executable ids and 1 invalid.
- **The successor's pinned list** (`mutation_lists/m2_mutants_s1`) has the same 199 ids, all executable, `ids_sha256 649e0e48d843bf4e792727b5b7789ff9a9a0d3ddb346f36dc51693d652f3384e`. It keeps RI10's id and position, with its corrected target (E1-RI10).
- **So the M10-only invalid id and the successor's corrected RI10 are the same id.** No other id is on one side only.
- **The 198 common executable ids:** `sha256_lines` `d5da4f9a3e083a30952c46b65491f907df832f7183710be088df08b15016694c`.

These numbers and hashes are in the test, not computed from the list it checks.

**Mutation results, m2 only.** M10's `m2_mutants.py` and `m2_mutants_s1` are run, and their per-id verdicts compared over the 198 common ids. The only allowed differences:
- `RI10-query-crosses-tenants`: invalid on M10 (its `ERROR`), with a verdict on the successor;
- an id M10 counted as killed by a timeout or crash, which the successor reports `INDETERMINATE` (DP-2.1 (a)). Each such id is listed.

This runs as its own evidence set on both Pythons.

**Not compared.** The mutation results of the other 15 mutation successors are not compared with M10. **They remain unverified, and point 2 is recorded as partly addressed, not closed.**

**E.15 The fake harness and the trusted names, on each of the eight runners:** `run_contracts_s1`, `run_m5_contracts_s1`, `run_det_corpus_s1`, `run_fin_corpus_s1`, `run_m3_contracts_s1`, `run_ingest_corpus_s1`, `run_m6_contracts_s1`, `run_m91_contracts_s1`.
- **The fake harness:**
  - it returns all-pass results, and writes a marker file if any of its code is executed;
  - **M10 half:** M10's runner executes it, reports a pass, and the marker is written;
  - **successor:** refused through the real validation path (`CANDIDATE_SHADOWS_TRUSTED`), the marker never written, and the output through `check_output`.
- **The trusted names:**
  - each of the nine names of `evkit.TRUSTED_PACKAGES` (`apg`, `apg_auif`, `apg_ui`, `mie`, `auif_m8`, `tests`, `tests_m8`, `tests_m10`, `tools`) is placed in the candidate path as a package directory and as a module file, and is refused on each of the eight runners;
  - a factory spec naming a trusted package is refused;
  - each output goes through `check_output`.

## F. Gaps found while preparing this paper (stop rule), now authorised

**F.1 The disk floor reached during a run** (T-0 `env_check` R4).

*Today:* a refused tree copy is caught as that item's worker exception (`ITEM_ERROR`), and the run goes on to exit 2.

*Authorised:*
- **During the items:**
  - the run stops starting items;
  - every item in flight (the one whose copy was refused, and every other started and unfinished item) is stopped under P.5, and is `INDETERMINATE cause=run_stopped`;
  - the items not started are `NOT_RUN cause=run_stopped`;
  - `control_end=NOT_RUN`, and `RUN_ERROR ENV_DISK_BELOW_FLOOR items free=<n> floor=<n>`, exit 2.
- **The start control's copy refused:** `control_start=FAIL cause=disk_below_floor`, no item run, every item `NOT_RUN`, `control_end=NOT_RUN`, `RUN_ERROR ENV_DISK_BELOW_FLOOR control_start free=<n> floor=<n>`, exit 2.
- **The end control's copy refused after every item finished:** the item lines are kept, `CONTROL end CONTROL_NOT_RUN cause=disk_below_floor`, `control_end=NOT_RUN` (K.1), and `RUN_ERROR ENV_DISK_BELOW_FLOOR control_end free=<n> floor=<n>`, exit 2.
- **The phase word** (`items`, `control_start`, `control_end`) records where the stop happened. K.1's check reads it.

*Tests:*
- on `m2_mutants_s1` and `sabotage_m7_s1`, which share `mutation_main` and `control`;
- the floor crossed during the items with `--jobs 2`, at the start control's copy, and at the end control's copy;
- each output through `check_output`.

**F.2 A run interrupted by SIGINT or SIGTERM** (T-0 `finish` R4).

*Today:* no signal handling. The run ends with no `RESULT` line, and the driver records it as `INTERRUPTED` under R1 §2.7's hard-kill rule.

*Authorised:*

(a) **One cancellation mechanism in `evkit`,** used by every loop that starts work:
- `mutation_main`, so `regression_sabotage_main`, `sabotage_m10_s1` and `sabotage_m8_s1` too;
- `faults_main`;
- `tests_runner_main`, `run_m2_tests_s1`, `run_m8_tests_s1`, `mut_runner_s1`;
- `cases_main`;
- `wrapper_main`.

**The handler,** for SIGINT and SIGTERM:
- it only records the signal and sets a cancellation flag;
- the first signal's name and the phase at that moment are kept;
- each further signal adds 1 to a count;
- it does no output and no cleanup, and a further signal never interrupts the reconciliation or the cleanup.

**The flag is checked:**
- before each item starts;
- before each control starts;
- between completed items;
- before the result is reconciled;
- by every wait on a child, at least every 0.2 s. A wait that sees it stops its unit under P.5 and returns.

**The last unit of work, by family.** A run is interrupted if the flag is set before its last unit's outcome has been fixed (P.8):

| Family | The last unit |
|---|---|
| mutation and sabotage tools | the end control |
| fault runners | the end control |
| case runners | the last selected case |
| tests runners (`run_m2_tests_s1`, `run_m8_tests_s1`, `mut_runner_s1`, `run_test_files_s1`) | the last selected file |
| wrappers | the last selected group |

So a completed last item is not by itself a completed run where an end control follows.

**The result of an interrupted run:**
- items in flight (started, with no outcome fixed yet, P.8) `INDETERMINATE cause=interrupted`. An item whose outcome was fixed before the signal keeps it, subject to its cleanup;
- items not started `NOT_RUN cause=run_stopped`;
- a start control in flight: `control_start=FAIL`, with `CONTROL start CONTROL_INTERRUPTED cause=interrupted`, and every item `NOT_RUN` (B.4);
- an end control in flight or not yet started: `control_end=NOT_RUN`, with `CONTROL end CONTROL_NOT_RUN cause=interrupted` if it had started (K.1);
- **no `RUN_ERROR` is added for the interrupt.** It is recorded on its own line, `INTERRUPTED signal=<SIGINT|SIGTERM> at=<item id|control_start|control_end|between> received=<n>`, immediately before the `RESULT` line. For `kind=mutation` and `kind=sabotage` the checker reads it (K.1, B.4). For the other kinds it is a record (K.3);
- the status and exit come from §2.7's counts as they stand: `INDETERMINATE`, exit 3, unless a run error recorded for another reason makes it `EVIDENCE_ERROR`, exit 2.

**A signal after the last unit's outcome has been fixed** does not change the result. It is recorded as `SIGNAL_AFTER_COMPLETION signal=<name>`.

**A `SIGKILL`** cannot be caught, and stays under §2.7's hard-kill rule.

(b) **A wrapper.**
- When a wrapper is interrupted, the group it is running is `INDETERMINATE cause=interrupted`, whatever its child printed before it was stopped.
- The child's partial output is kept in the log, and is never used to classify the group.
- The groups not started are `NOT_RUN cause=run_stopped`.
- The wrapper prints its own `INTERRUPTED` line and `RESULT` line, `INDETERMINATE`, exit 3.

(c) **Process containment** is P.

*Tests:*
- **The runners:** for each family, its real runner is sent SIGINT, and separately SIGTERM: `m2_mutants_s1`, `sabotage_m7_s1`, `run_faults_s1`, `run_m2_tests_s1`, `run_contracts_s1` and `run_m4_all_s1`.
- **The points of interruption:** while a child is running; between two items; and, for the three with an end control (`m2_mutants_s1`, `sabotage_m7_s1`, `run_faults_s1`), during the end control and during the end control's cleanup.
- **What is asserted in each:**
  - the interrupted form, passed through `check_output`;
  - every child and descendant shown gone before the parent's `RESULT` line;
  - a second signal counted, without cutting the output.

## K. Decisions K.1, K.2 and K.3 (recommended by both the builder and the reviewer)

**K.1 `control_end` when a run is stopped after its last item, but before its end control has completed.**
- **The rule today.** R1 §2.7 says: "`control_end=NOT_RUN` if and only if `control_start` is not `PASS` or the run was stopped before the last item". The checker implements exactly that. The builder's reading is confirmed by the reviewer.
- **Decided (recommended by both):** amend that rule, for `kind=mutation` and `kind=sabotage`, to:

  > `control_end=NOT_RUN` if and only if `control_start` is not `PASS`, or the run was stopped before the last item, or the run was stopped after its last item and before the end control's outcome (`PASS`, `FAIL` or `TIMEOUT`) was fixed.
  >
  > In that last case, the output must carry the stop record for that stop and that moment: either `RUN_ERROR ENV_DISK_BELOW_FLOOR control_end …` or `INTERRUPTED … at=control_end`. It must carry no `CONTROL end` record with a completed outcome. Only `CONTROL end CONTROL_NOT_RUN` with the matching cause is allowed.
  >
  > An end control that completed always reports its own outcome, whatever stop records exist.
- **When the outcome is fixed:** as P.8 says, when the control's result has been received and validated.
  - A leak found by the cleanup that follows makes it `FAIL cause=processes_left` (B.4). It is still a completed outcome, never `NOT_RUN`.
  - An interrupt after that moment is `SIGNAL_AFTER_COMPLETION`, and never turns the control into `NOT_RUN`.
- **The checker** enforces all three conditions. A stop record for another phase, or a completed `CONTROL end` record, never permits `NOT_RUN`.
- **Tests:**
  - each permitted form;
  - and each rejected form:
    - `NOT_RUN` with no stop record;
    - a stop record for another phase;
    - a completed `CONTROL end` record beside `NOT_RUN`;
    - a completed end control reported as `NOT_RUN`;
    - an `INTERRUPTED … at=control_end` line beside a completed end control (the signal arrived after the outcome was fixed, so the line must be `SIGNAL_AFTER_COMPLETION`).
  - and, on a real tool, an end control that returns a valid result, leaves a background process, and is sent an interrupt during cleanup: `control_end=FAIL cause=processes_left`, with `SIGNAL_AFTER_COMPLETION`.

**K.2 The case runners' in-process cases: decided, each case supervised (recommended by both).**
- **Today:** `cases_main` runs each of the 386 pinned cases of the 11 case runners (the ten of C.1 and `run_history_contract_s1`) inside the runner's own process.
- **Authorised:**
  - each case runs as a forked unit under P, from the parent state after the start checks, the pins, the resolved selection, the guarded imports and the inventory comparison;
  - **the time limit:** `CASE_ITEM_TIMEOUT_S = 300` per case, recorded as for B.2;
  - **the child:**
    - it calls the unchanged `run_case(candidate, suite, case_id)`;
    - it writes one length-prefixed JSON message (P.8): `{"ok": <bool>, "detail": <string>}`, `{"exception": "<type>"}` for an exception escaping `run_case`, or `{"child_error": "<type>"}`;
    - its own failure is handled as in B.1: on a caught encoding or write exception it tries once to write `child_error`, then ends with `os._exit(70)`.

**The case-result mapping:**

| What happened | Outcome |
|---|---|
| a validated `ok` message (P.8) with `ok` true | `PASS cause=ok` |
| a validated `ok` message with `ok` false (the harness's own verdict that the candidate's outcome differs, an ordinary test failure) | `FAIL cause=expected_outcome_differs`, as today |
| a validated `exception` message (an exception escaping `run_case`) | `FAIL cause=exception_<type>`, as today |
| a validated `child_error` message, or no complete message with exit status exactly 70 (a caught child-side encoding or write exception) | `ITEM_ERROR cause=child_error` |
| the deadline passed with no complete message | `INDETERMINATE cause=timeout`, with its `TIMEOUT` line |
| the child ended (any other exit status, or a signal) before completing its message | `INDETERMINATE cause=crash` |
| a complete message that fails P.8's steps 2 to 5 | `INDETERMINATE cause=bad_result` |
| processes left (P.6), the direct child included | `INDETERMINATE cause=processes_left` |
| an interrupt before the outcome was fixed | `INDETERMINATE cause=interrupted` |

**The boundaries:**
- `child_error` is only a failure the child itself caught and reported, by message or by status 70;
- `crash` is a child that ended any other way before its message was complete, including one that died while writing;
- `bad_result` is a complete message that is not a valid result.

Code under test that ends with status 70 before writing would be reported `child_error`: `ITEM_ERROR`, exit 2, never a pass.

**Why an exception escaping `run_case` stays `FAIL`.** That is the current frozen verdict for a case whose harness run raised: an exception is the candidate or the harness failing the case. Changing it would change what a case tests, which is outside this pass. The new infrastructure failure, the child's own machinery, is the separate `ITEM_ERROR` row. A timeout, crash, malformed result or leak is never `PASS`.

**The comparison.** Every one of the 386 case verdicts and causes of the 11 runners' full runs on the new freeze must equal the current freeze's (`d5f87d6b…85c8`), with each run's status and exit. A difference, from shared state, fixtures or order no longer carrying across cases, is a stop-rule event.

**Tests:**
- **on two real runners,** `run_contracts_s1` and `run_fin_corpus_s1`, with the limit shortened in a temporary copy:
  - a case that hangs;
  - a case that spawns a descendant and hangs;
  - a case that leaves a background descendant after a passing result (`INDETERMINATE cause=processes_left`);
  - a case that crashes;
  - incomplete and malformed messages;
  - a well-formed `ok=false` result: `FAIL cause=expected_outcome_differs`;
  - an exception raised inside `run_case`: `FAIL cause=exception_<type>`;
  - a child machinery failure (`ITEM_ERROR cause=child_error`), arranged so that the same case would otherwise fail. The machinery failure is asserted, not the case failure. It is tested both ways: by the `child_error` message, and by status 70 with no message;
  - a child killed while writing, leaving an incomplete message: `INDETERMINATE cause=crash`, never `child_error`;
  - a complete message that parses as JSON but has the wrong keys or types: `INDETERMINATE cause=bad_result`;
  - a malformed message whose text resembles an `ok=false` result: `INDETERMINATE cause=bad_result`, never `FAIL`;
  - an interrupt while a case is running;
  - each with the descendants shown gone before `RESULT`, and each output through `check_output`;
- **on each of the other nine case runners:** a case that hangs.

**K.3 The versions: decided, `kind=mutation` and `kind=sabotage` also become `v=3`.**
- **R1's versioning rule, verbatim (§2.7, last line):** "A later schema version (`v=3`) needs a change record (§2.2) and a checker that reads every version still in the evidence."
- **What the rule does not say.** It does not say what makes a change a new schema version.
- **The reading adopted.** §2.7 is titled "The terminal `RESULT` line: the exact schema", and its consistency rules are part of it. K.1, and the checker's new reading of `CONTROL` and `INTERRUPTED` records (B.4), change those rules for `kind=mutation` and `kind=sabotage`. So each gets a new version, although no field is added.

**The schemas after this pass:**

| Kind | Written now | The checker also reads | What `v=3` changes |
|---|---|---|---|
| `cases` | `v=3` | `v=2`, under the frozen rules and (a′) | the `suites` field and its rules (A.1, A.3) |
| `mutation` | `v=3` | `v=2`, under the frozen rules | the same fields as `v=2`, in the same order, and no `suites`. Changed: the K.1 `control_end` rule, and the `CONTROL start` and `CONTROL end` diagnostic rules (B.4) |
| `sabotage` (the sabotage tools and the fault runners) | `v=3` | `v=2`, under the frozen rules | as for `mutation`, with `sabotage`'s own fields |
| `tests` | `v=2` | `v=2` | unchanged |
| `wrapper` | `v=2` | `v=2` | unchanged |

- **The checker dispatches by kind and version together.** A `v=3` line of one kind is never read under another kind's `v=3` rules, and a `v=2` line is never read as `v=3`.
- **For `tests` and `wrapper`:**
  - the `INTERRUPTED`, `SIGNAL_AFTER_COMPLETION`, `CLEANUP` and `CLEANUP_SUMMARY` records do not change these kinds' result-schema consistency rules;
  - the checker does not use them to accept or reject a `tests` or `wrapper` result. Those results stay governed by the frozen `v=2` contract alone;
  - their interrupted, leaked and stopped results use only states `v=2` already has (`INDETERMINATE`, `NOT_RUN`, `ITEM_ERROR`), so these kinds stay `v=2`;
  - a test passes a `tests` and a `wrapper` output through the checker twice, with and without these records, and the verdict is the same.
- **Consumers.**
  - Every consumer that reads a mutation, sabotage or case child (the wrappers, the M8 tiers' callers and the builder's log checkers) reads it through `check_output`, and so accepts `v=3`.
  - The builder's own log checkers outside the tree are updated to match, and say so.
- **The records.** Each version change has its own change record, in-tree and in the documents.

## G. What stays as decided

- **Still owner-accepted, unchanged:** D2, D8, D12 and (e). A.1's `selected=0` rule does not change D12.
- **D13, D14 and D15:** accepted on the reviewer's terms. D13 needs its test, under E point 9.
- **Open findings 1 to 8:** stay open.
- **Findings 9 and 10:** stay open until the reviewer has reviewed the new evidence.

## H. Stop rule

The known defects and missing behaviours expressly identified and authorised for correction in sections P, A, B, C, F.1 and F.2 and K are not stop-rule triggers merely because their new tests reproduce them. The builder is authorised to implement those specified corrections.

If a test reveals any of these, work stops and the builder reports it before making any further logic change:
- an additional defect;
- an unlisted behaviour gap;
- an unexpected regression, including any change in B.6's or K.2's comparison or E.2's allowed differences;
- a requirement that cannot be met within the authorised scope, including P.9's audit.

No other logic change, no change to what a plant, mutant or case tests, and no change to the scope is made without the owner.

## I. The new freeze and its evidence

1. **The commit.** The changes and tests are committed, and pins are re-pinned only where a changed file's hash requires it, each with its change record. The commit also includes:
   - the manifest, regenerated;
   - the in-tree change record, updated. It records:
     - the version changes and their compatibility rules (A.2 and K.3);
     - the amended `control_end` rule (K.1);
     - `FAULT_ITEM_TIMEOUT_S`, `CASE_ITEM_TIMEOUT_S` and P.5's five time constants, and where each applies;
     - the process model P;
     - the new codes and lines (`IMPORT_FAILED`, `ENV_NO_PROCESS_SUPERVISION`, `CLEANUP_INCOMPLETE`, `INTERRUPTED`, `SIGNAL_AFTER_COMPLETION`, `CLEANUP`, `CLEANUP_SUMMARY`, `CLEANUP_AMBIGUOUS`, `LIMIT`, `CONTROL_NOT_RUN`, `CONTROL_INTERRUPTED`);
   - the checker docstring's "in their order" corrected (mistake 17);
   - the stale "decision pending, (g)" comment corrected (mistake 18).
2. **The suite and the freeze.** The full `tests_tools` suite passes on Python 3.13 and 3.12. Then comes a new deterministic freeze, built twice with identical bytes.
3. **On the new freeze, the full evidence set:**
   - the six run sets (T, W and M on both Pythons);
   - the E.2 comparisons, golden, contract, corpus, fault and m2, on both Pythons;
   - the B.6 and K.2 comparisons;
   - the historical checks on both Pythons;
   - the frozen-file comparison;
   - both route proofs;
   - the check of the cited test names;
   - the 2C demonstration rerun.

   **What the run records carry:**
   - the limits in force;
   - every `CLEANUP` and `CLEANUP_SUMMARY` line;
   - for the P, B, K.2 and F.2 tests, the process ids, start times and group ids the tests record, and which supervisor cleaned up each unit, so a reviewer can follow each cleanup check;
   - the P.9 audit itself (`evidence/audit/`): the inventory of child-start sites and paths, and the outside-service record of P.2 with the basis for each conclusion;
   - the package's evidence index (its README), linking `evidence/audit/` and the process-identity and `CLEANUP` records directly.

   The run index describes `last_line` as a prefix of at most 300 characters.
4. **The mapping.** A new read-only mapping, by a separate agent that did not write the tests. It classifies each point as closed by evidence, partly addressed, or still open.
5. **The delivery:** the documents file and the package, as one ZIP plus one documents file. Freeze `d5f87d6b…85c8` and its evidence are kept unchanged as superseded.
6. **Any change after the new freeze.** Any code or test change after the new freeze invalidates its evidence. A changed tree means a replacement freeze and the evidence rerun on it.
7. **Not acceptance.** The reviewer reviews the new package. A clean evidence run is not acceptance, and whether stage 1 may be the base for stage 2 stays a separate owner decision.

## J. What this does not authorise

- stage 1 acceptance;
- stage 2, stage 3, Part B or final verification;
- any repair of plant or mutant targets;
- any change to what a case tests;
- any change outside sections P, A to F and K;
- any work assigned to Amir, or any dependency on him.

Production systems, credentials and customer data stay out of scope. APG-M8.1 and the earlier audited packages, and the M10 archive (`bd5c592a…5192`), stay immutable.
