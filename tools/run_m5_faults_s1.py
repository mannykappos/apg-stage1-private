#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_m5_faults.py (amendment 1 row 9, T-K; decision K-1 K23: kind=sabotage; DP-1.2 (B): the M10 file stays
byte-identical).  The plants are M10's faulty NotificationPorts (apg/det/faulty_m5.py FAULTS, unchanged); the reference NotificationPort is
the start and end control and must fail no case (tools/evkit.faults_main).
Usage: python3 -I -S tools/run_m5_faults_s1.py [--list] [--ids ID[,ID]] [--run-id ID] | --pin --reason TEXT --cause TEXT
Exit codes as §2.4; the M10 marker ALL FAULTS CAUGHT only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

from apg.det import contracts_m5 as C, reference_m5 as REF  # noqa: E402
from apg.det.faulty_m5 import FAULTS  # noqa: E402


def failed(factory):
    return {r[1] for r in C.run_all(factory) if not r[3]}


PLANTS = [(fid, text, (lambda factory=factory: failed(factory)), list(expect)) for fid, (text, factory, expect) in FAULTS.items()]

if __name__ == "__main__":
    sys.exit(E.faults_main("run_m5_faults_s1", PLANTS, lambda: failed(REF.notify_env()), sys.argv[1:], success_marker="ALL FAULTS CAUGHT"))
