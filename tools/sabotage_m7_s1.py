#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/sabotage_m7.py (E1-RI10, P1-F6, P5-B06; decision K-1 row: kind=sabotage; DP-1.2 (B): tools/sabotage_m7.py stays byte-identical).
The plants are M10's own CASES, loaded from tools/sabotage_m7.py and unchanged; each one's check is a step of M10's tools/run_regression_m7.py,
also unchanged (it is outside stage 1's scope).  What changes is how they are run and judged (tools/evkit.regression_sabotage_main):
exact selection, a preflight (each target text exactly once, §2.1), start and end controls on the unsabotaged tree with every selected
plant's step, the step's own result read exactly, a timeout never a catch (DP-2.1 (a)), and one RESULT v=2 kind=sabotage line.
Usage (from the package root):  python3 -I -S tools/sabotage_m7_s1.py [--list] [--only ID[,ID]] [--ids ID[,ID]] [--jobs N] [--run-id ID]
                                 python3 -I -S tools/sabotage_m7_s1.py --pin --reason TEXT --cause TEXT
Exit codes as §2.4.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

if __name__ == '__main__':
    sys.exit(E.regression_sabotage_main('sabotage_m7_s1', 'sabotage_m7', 'run_regression_m7', sys.argv[1:], timeout=1800))
