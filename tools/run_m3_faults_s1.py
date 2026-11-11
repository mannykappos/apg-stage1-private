#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_m3_faults.py (P2-B8; decision K-1 K21: kind=sabotage; DP-1.2 (B): the M10 file stays byte-identical).
The plants are M10's faulty FileStore and JobRunner implementations (apg/ingest/faulty_m3.py FAULTS, unchanged, a Part B file this tool only
reads), each run on its own suite with the reference for the other, as M10 does; the reference envs on both suites are the start and end
control and must fail no case (tools/evkit.faults_main).
Usage: python3 -I -S tools/run_m3_faults_s1.py [--list] [--ids ID[,ID]] [--run-id ID] | --pin --reason TEXT --cause TEXT
Exit codes as §2.4; the M10 marker ALL FAULTS CAUGHT only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

from apg.ingest import contracts_m3 as C, reference_m3 as REF  # noqa: E402
from apg.ingest.faulty_m3 import FAULTS  # noqa: E402


def failed_for(kind, factory):
    suite = C.FS if kind == "files" else C.JR
    res = C.run_all(factory if kind == "files" else REF.file_env(), factory if kind == "jobs" else REF.job_env(), [suite])
    return {r[1] for r in res if not r[3]}


def reference_failed():
    return {r[1] for r in C.run_all(REF.file_env(), REF.job_env(), [C.FS, C.JR]) if not r[3]}


PLANTS = [(fid, text, (lambda kind=kind, factory=factory: failed_for(kind, factory)), list(expect))
          for fid, (text, kind, factory, expect) in FAULTS.items()]

if __name__ == "__main__":
    sys.exit(E.faults_main("run_m3_faults_s1", PLANTS, reference_failed, sys.argv[1:], success_marker="ALL FAULTS CAUGHT"))
