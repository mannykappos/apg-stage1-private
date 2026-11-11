#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/sabotage_mie1_1.py (P1-F6, T-K; decision K-1 K20: kind=sabotage; DP-1.2 (B): the M10 file stays
byte-identical).  The seventy plants are M10's CASES (the MIE-1 catalogue with SB-29's moved target, and C-01 to C-10), unchanged; their
checks are M10's static checker, M10's MIE-1.1 regression steps, or a test file run by run_m2_tests_s1 under its pinned sabotage_tool
profile (failfast, F8).  Preflight exactly once, start and end controls, kind=sabotage (tools/evkit.mie_sabotage_main).
Usage: python3 -I -S tools/sabotage_mie1_1_s1.py [--list] [--only ID[,ID]] [--jobs N] [--run-id ID] | --pin --reason TEXT --cause TEXT
Exit codes as §2.4; the M10 marker EVERY SABOTAGE CASE IS CAUGHT only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

if __name__ == '__main__':
    sys.exit(E.mie_sabotage_main('sabotage_mie1_1_s1', 'sabotage_mie1_1', 'run_regression_mie1_1', sys.argv[1:],
                                 success_marker='EVERY SABOTAGE CASE IS CAUGHT'))
