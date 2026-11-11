#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_regression_m10.py (P1-F6; DP-1.2 (B): the M10 file stays byte-identical).  M10's steps, checks and
output are kept unchanged; the child environment is the §2.8 allowlist, every Python child starts with -I -S, and each child that has a
stage 1 successor is redirected to it and judged by its RESULT v=2 line and M10's marker (tools/evkit.regression_successor_main).
These steps compare the tree with earlier releases' baselines, so on a successor tree they flag stage 1's own declared changes; they are
historical-baseline checks, run against the M10 archive (D-1, DP-1.1).
Usage: python3 -I -S tools/run_regression_m10_s1.py --list | --step Rnn | --all          BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

if __name__ == '__main__':
    sys.exit(E.regression_successor_main('run_regression_m10', sys.argv[1:]))
