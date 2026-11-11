# Issue record: corrective pass 2, P.9 audit, stopped under the stop rule before implementing

**BUILDER-EXECUTED: NOT INDEPENDENT.** Written by the builder on 2026-11-05 (AEDT), under the owner's authorisation of 10:56 (paper `23d2adb9…f0ea5`). It accepts nothing, closes no finding, EDR or CF item, and makes no production-readiness claim.

**Nothing has been implemented.** No file of the successor tree has changed, and the freeze is unchanged. P.9 requires the audit before implementing, and the paper's stop rule requires the builder to stop and report when the audit finds:
- a site or path that cannot be brought under P; or
- an outside service that cannot be ruled out.

The audit found four points.

## Evidence (in `d14/s1/evidence_pass2/audit/`, to go into the package)
- `child_start_sites.txt`: every successor child-start site, and every nested path.
- `outside_services.txt`: the P.2 record from three children, each started from a fresh extraction of the freeze:
  - one exactly as `run_child` starts a unit today;
  - one by `os.fork` before the scrub, with a parent-only descriptor and a parent-only variable planted;
  - one after the scrub P.2 authorises.

  The tool is `d14/s1/tools/audit_outside_services_s1.py`.
- `process_api_reach.txt`: can a unit reach PID 1's process API? Tool: `d14/s1/tools/audit_process_api_reach_s1.py`.

**Every connection attempt** was a connect, closed at once. Nothing was sent to any socket or port.

## S1. Outside services that cannot be ruled out (P.2)
- **PID 1 is the workspace's process API** (`/process_api --firecracker-init --addr 0.0.0.0:2024 … --block-local-connections`). A unit's TCP connect to `127.0.0.1:2024` and to `192.0.2.2:2024` is accepted. This service starts processes in the workspace. A process it started would be a child of PID 1, not a descendant of the supervisor, so P cannot contain it. Whether it would serve a local request (its `--block-local-connections` flag suggests not) cannot be established without speaking its protocol, which the builder did not do.
- **The agent harness's socket**, `/tmp/cc-socks/96.sock` (root, mode 0600), accepts a unit's connect, because **units run as uid 0**. Its protocol and abilities are unknown.
- **The telemetry collector's socket**, `/run/sandbox-telemetry/ingest.sock` (uid 64321, mode 0666), accepts a connect. It is very probably ingest only, but that is not established.
- **The rest is ruled out or harmless:**
  - **no process-launching daemon is running** (no cron, atd, systemd, dockerd or containerd). `/etc/cron.d` is writable by a unit (root), but nothing reads it;
  - **the launcher programs on the unit `PATH`** (`systemd-run`, `systemctl`, `docker`, `ctr`, `runc`, `nsenter`, `unshare`, `setsid`, `nohup`, `sudo`, `su`) either need a daemon that is absent, or start their process as a descendant, which P contains;
  - **the PostgreSQL socket under `/tmp`** refuses connections;
  - **network:** a unit has no proxy variable. A direct TCP connect to an outside address was accepted. A remote endpoint cannot start a local process except through the process API above.
- **What lowers the risk, and why it is not proof.** No file of the frozen tree opens a socket or names port 2024, `cc-socks` or `process_api` (0 files, `child_start_sites.txt` E). Every unit runs frozen code, or a pinned mutation or plant of it. So no unit in this pass contains code that could make such a request. That is a basis for the risk being negligible. It is not the "cannot use it" the paper asks the audit to establish.

## S2. Test files run in-process, not as child processes (P.1, P.10 and F.2 assume otherwise)
- **What the code does.** `tests_runner_main` (`run_m2_tests_s1`, `mut_runner_s1`, `run_test_files_s1`) and `child_unittest_runner` import and run each test file in their own process (`evkit.run_test_file`, "Run one test file in this process").
- **Where the paper is wrong.** The paper lists "a test file" as a unit of work. Its P.10 nested test is "a mutation tool's child test runner starts a test-file child". That child does not exist.
- **The consequences:**
  - the tests runners are not supervisors;
  - a test that hangs hangs its tests runner, with no `RESULT` line. Where that runner is a child of a mutation tool, wrapper or `run_m8_tests_s1`, the parent's time limit bounds it. Standalone, nothing does;
  - under F.2, an interrupt to a tests runner is honoured only between files.
- **Why it was missed:** the builder wrote P from the plan's description, not from the code. This is a builder mistake, disclosed.

## S3. A successor child-start path outside `tools/evkit.py` (P.9's stated scope)
`tools/run_cr02_reference_s1.py` runs M10's `tools/run_cr02_reference.py` in its own process, with `subprocess.run` replaced by a shim that adds `-S` and filters the environment. The children that script starts go through the shim, not through `evkit`. P.9 names only `evkit.py` sites.

## S4. A unit's standard input is inherited
Today no successor sets `stdin` for a child. In one audit run, a unit's descriptor 0 was a socket inherited from the workspace (`socket:[609]`). In another, from a different shell, it was `/dev/null`. P.2 allows descriptors 0, 1 and 2, but says nothing of where 0 points.

## What the builder proposes (for the owner)
- **S1 (i), recommended:**
  - record S1 as a limitation of the builder's workspace (open finding 11), with this evidence and the basis above;
  - narrow P's claim to what it does contain: every descendant of a unit;
  - state that an independent environment must repeat the outside-service audit.

  **S1 (ii):** isolate units from these services, for example with a new network namespace per unit plus an unprivileged user. That is a new design and needs its own paper, and the 0666 telemetry socket would still be reachable by path.
- **S2 (i), recommended:**
  - correct P.1, P.10 and F.2's wording to the code: tests runners are leaves, not supervisors, and test files run in-process;
  - P.10's nested test becomes mutation tool → tests runner → a test that starts a process → its grandchild;
  - record the standalone-hang and between-files interrupt limit as open finding 12. Every evidence path runs the tests runners under a parent with a time limit.

  **S2 (ii):** fork each test file as a unit, like K.2. That changes the tests runners' design.
- **S3 (i), recommended:** bring the CR-02 shim under P. The shim starts each child through the P start (own group, register, cleanup on every path) and hands M10's script the same `CompletedProcess`, so `run_cr02_reference_s1` becomes a supervisor for containment.

  **S3 (ii):** leave it, contained only by an outer supervisor when nested.
- **S4, recommended:** read P.2 as requiring descriptor 0 to be `/dev/null` for every unit (`stdin=subprocess.DEVNULL`; `os.open('/dev/null')` onto 0 in a forked child), with the P.2 test asserting it.

None of these is implemented until the owner decides.

## Addendum, 2026-11-05, after the reviewer's review of this report (`rec/reviews/RECEIVED_REVIEW_2026-11-05_CORRECTIVE_PASS_2_P9_STOP.txt`). The text above is left as first written.
- **The reviewer's corrections, accepted:**
  - S2 is narrowed: `run_m8_tests_s1` does start one child per test file, and is a supervisor;
  - the socket findings are worded as "reachable, not ruled out", never as "would launch" or "harmless";
  - the egress boundary is recorded as unknown;
  - the environment inventory is reconciled.

  These are in `d14/s1/evidence_pass2/audit/outside_services_conclusions.txt`. The raw audit records are unchanged.
- **The bounded paper-to-code verification the reviewer required** is in `paper_to_code_matrix.md`, cross-checked against an independent read-only inventory by a separate agent (`independent_inventory.md`).
- **It found one more stop-rule matter, S5.** Code that stage 1 must not change starts children outside the successor's start path, and without R1 §2.8's `-S`:
  - AUIF's `verify_tree` (two children per check, with the caller's environment);
  - the five M10 regression tools' `r03` (no time limit);
  - in-process test files.

  In a supervisor these children would also confuse P.4's reaper.
- **Mistake 20, disclosed.** The stage 1 documents (section 2, P1-F6) said every child of `run_m8_tests_s1` and `m8_mutants_s1` starts `-I -S`. AUIF's verification children of those tools do not. The test probed only the children `run_child` starts, and the builder did not check the claim against the code.
- **Still nothing implemented.** The amendment proposing decisions on S1 to S5 is `d14/decisions/APG_D14_STAGE1_CORRECTIVE_PASS_2_AMENDMENT_1_DRAFT.md`.
