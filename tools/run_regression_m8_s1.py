#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_regression_m8.py (P1-F6; DP-1.2 (B): the M10 file stays byte-identical).  M10's steps, checks and
output are kept unchanged; the child environment is the §2.8 allowlist, every Python child starts with -I -S, and each child that has a
stage 1 successor is redirected to it and judged by its RESULT v=2 line and M10's marker (tools/evkit.regression_successor_main).
Decision W-1A.2 (ii) (a) (owner, 2026-11-01 06:22): steps (R01, R02, R10) compare the tree with an earlier release's baseline; here they also
permit exactly what the frozen stage 1 manifest declares, validated by amendment 2's validator and only at each file's exact recorded stage 1
hash (tools/evkit.s1_manifest_view, _s1_step), so an undeclared change still fails.  The other steps are M10's, unchanged.
Usage: python3 -I -S tools/run_regression_m8_s1.py --list | --step Rnn | --all          BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

if __name__ == '__main__':
    sys.exit(E.regression_successor_main('run_regression_m8', sys.argv[1:], s1_manifest_steps=('R01', 'R02', 'R10')))
