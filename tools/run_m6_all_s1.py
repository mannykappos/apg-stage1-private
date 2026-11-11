#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_m6_all.py (decision W-1, owner 2026-10-31 20:57, as corrected by W-1A, owner 2026-11-01 06:22; T-0;
DP-1.2 (B): tools/run_m6_all.py stays byte-identical).  It reads M10's own group table (tools/evkit.m10_wrapper_table: the M10 source run only
up to where its run starts, its hash checked against the pins) and runs every group in M10's order, mode full:
  - a stage 1 test runner or a tool whose successor prints RESULT v=2 -> its successor, judged by that line (FILE line, child lines relayed);
  - any other check -> a CHECK line (the M10 tool, or its stage 1 successor for the M8 regression steps and the CR-02 rerun, or the
    successor's --baseline for a mutation baseline), judged by its exit code and marker (W-1 §1.2 (b));
  - a historical check of an earlier release (W1_EXCLUSION_LIST_v2.csv) -> an EXCLUDED line; it is never run.
Prints RESULT v=2 kind=wrapper.  The M10 success marker (ALL M6 CHECKS PASS) only with status=OK; OK_WITH_EXCLUSIONS (exit 0) never claims a full
pass: read the RESULT status (tools/evkit.wrapper_verdict), not the exit code alone (W-1 §1.9).
Usage (from the package root):  python3 -I -S tools/run_m6_all_s1.py [--list | --group N | --range A-B] [--run-id ID]      (no option: every group, as M10)
Exit codes as §2.4.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

if __name__ == '__main__':
    sys.exit(E.wrapper_main('run_m6_all_s1', 'run_m6_all', sys.argv[1:], success_marker='ALL M6 CHECKS PASS'))
