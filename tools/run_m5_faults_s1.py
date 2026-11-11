#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_m5_faults.py (amendment 1 row 9, T-K; decision K-1 K23: kind=sabotage; DP-1.2 (B): the M10 file stays
byte-identical).  The plants are M10's faulty NotificationPorts (apg/det/faulty_m5.py FAULTS, unchanged); the reference NotificationPort is
the start and end control and must fail no case (tools/evkit.faults_main).
Usage: python3 -I -S tools/run_m5_faults_s1.py [--list] [--ids ID[,ID]] [--run-id ID] | --pin --reason TEXT --cause TEXT
Exit codes as §2.4; the M10 marker ALL FAULTS CAUGHT only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT.
Corrective pass 2 (C, B): the harness imports and PLANTS run in load(), under evkit.import_guard, after the start checks
(evkit.guarded_load); every plant and both controls run as forked units under P (evkit.faults_main)."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

TOOL = "run_m5_faults_s1"
C = REF = FAULTS = None
PLANTS = []


def load():
    global C, REF, FAULTS, PLANTS
    with E.import_guard("apg.det.contracts_m5"):
        import apg.det.contracts_m5 as C
    with E.import_guard("apg.det.reference_m5"):
        import apg.det.reference_m5 as REF
    with E.import_guard("apg.det.faulty_m5"):
        from apg.det.faulty_m5 import FAULTS
        PLANTS = [(fid, text, (lambda factory=factory: failed(factory)), list(expect)) for fid, (text, factory, expect) in FAULTS.items()]


def failed(factory):
    return {r[1] for r in C.run_all(factory) if not r[3]}


if __name__ == "__main__":
    rc = E.guarded_load(TOOL, "sabotage", load)
    if rc is not None:
        sys.exit(rc)
    sys.exit(E.faults_main(TOOL, PLANTS, lambda: failed(REF.notify_env()), sys.argv[1:], success_marker="ALL FAULTS CAUGHT"))
