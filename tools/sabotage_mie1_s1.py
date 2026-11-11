#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/sabotage_mie1.py (P1-F6; its P6-B1 part is not stage 1's; decision K-1 K19: kind=sabotage; DP-1.2 (B): the
M10 file stays byte-identical).  The sixty plants are M10's CASES, unchanged, still required to equal spec/MIE1_SPEC_v0.3's sabotage
catalogue one to one; their checks are M10's static checker, M10's MIE-1 regression steps, or a test file run by run_m2_tests_s1 under
its pinned sabotage_tool profile (failfast, F8).  Preflight exactly once, start and end controls, kind=sabotage (tools/evkit.mie_sabotage_main).
Usage: python3 -I -S tools/sabotage_mie1_s1.py [--list] [--only ID[,ID]] [--jobs N] [--run-id ID] | --pin --reason TEXT --cause TEXT
Exit codes as §2.4; the M10 marker EVERY SABOTAGE CASE IS CAUGHT only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

if __name__ == '__main__':
    sys.exit(E.mie_sabotage_main('sabotage_mie1_s1', 'sabotage_mie1', 'run_regression_mie1', sys.argv[1:],
                                 catalogue='spec/MIE1_SPEC_v0.3/MIE1_SABOTAGE_CATALOGUE.csv', success_marker='EVERY SABOTAGE CASE IS CAUGHT'))
