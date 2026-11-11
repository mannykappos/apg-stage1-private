#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_m3_faults.py (P2-B8; decision K-1 K21: kind=sabotage; DP-1.2 (B): the M10 file stays byte-identical).
The plants are M10's faulty FileStore and JobRunner implementations (apg/ingest/faulty_m3.py FAULTS, unchanged, a Part B file this tool only
reads), each run on its own suite with the reference for the other, as M10 does; the reference envs on both suites are the start and end
control and must fail no case (tools/evkit.faults_main).
Usage: python3 -I -S tools/run_m3_faults_s1.py [--list] [--ids ID[,ID]] [--run-id ID] | --pin --reason TEXT --cause TEXT
Exit codes as §2.4; the M10 marker ALL FAULTS CAUGHT only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT.
Corrective pass 2 (C, B): the harness imports and PLANTS run in load(), under evkit.import_guard, after the start checks
(evkit.guarded_load); every plant and both controls run as forked units under P (evkit.faults_main)."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

TOOL = "run_m3_faults_s1"
C = REF = FAULTS = None
PLANTS = []


def load():
    global C, REF, FAULTS, PLANTS
    with E.import_guard("apg.ingest.contracts_m3"):
        import apg.ingest.contracts_m3 as C
    with E.import_guard("apg.ingest.reference_m3"):
        import apg.ingest.reference_m3 as REF
    with E.import_guard("apg.ingest.faulty_m3"):
        from apg.ingest.faulty_m3 import FAULTS
        PLANTS = [(fid, text, (lambda kind=kind, factory=factory: failed_for(kind, factory)), list(expect))
                  for fid, (text, kind, factory, expect) in FAULTS.items()]


def failed_for(kind, factory):
    suite = C.FS if kind == "files" else C.JR
    res = C.run_all(factory if kind == "files" else REF.file_env(), factory if kind == "jobs" else REF.job_env(), [suite])
    return {r[1] for r in res if not r[3]}


def reference_failed():
    return {r[1] for r in C.run_all(REF.file_env(), REF.job_env(), [C.FS, C.JR]) if not r[3]}


if __name__ == "__main__":
    rc = E.guarded_load(TOOL, "sabotage", load)
    if rc is not None:
        sys.exit(rc)
    sys.exit(E.faults_main(TOOL, PLANTS, reference_failed, sys.argv[1:], success_marker="ALL FAULTS CAUGHT"))
