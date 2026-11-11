#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_faults.py (amendment 1 row 8, T-K; decision K-1 K22: kind=sabotage; DP-1.2 (B): the M10 file stays
byte-identical).  The plants are M10's faulty implementations (apg/faulty_impls.py FAULTS, unchanged), each with its M10 list of contract
cases it must fail; the in-memory reference implementation is the start and end control and must fail no case (tools/evkit.faults_main).
Usage: python3 -I -S tools/run_faults_s1.py [--list] [--ids ID[,ID]] [--run-id ID] | --pin --reason TEXT --cause TEXT
Exit codes as §2.4; the M10 marker ALL FAULTS CAUGHT only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

from apg.contracts import run as R  # noqa: E402
from apg.contracts.framework import ContractEnv  # noqa: E402
from apg.faulty_impls import FAULTS  # noqa: E402
from apg.reference_impl import FakeClock, StaticContextProvider, InMemoryRecordStore, InMemoryAuditLog  # noqa: E402


def reference():
    c = FakeClock(); p = StaticContextProvider(c)
    return ContractEnv(p, InMemoryRecordStore(p), InMemoryAuditLog(p, c), c.advance)


def failed(factory):
    return {r[1] for r in R.run(factory) if not r[3]}


PLANTS = [(fid, text, (lambda factory=factory: failed(factory)), list(expect)) for fid, (text, factory, expect) in FAULTS.items()]

if __name__ == "__main__":
    sys.exit(E.faults_main("run_faults_s1", PLANTS, lambda: failed(reference), sys.argv[1:], success_marker="ALL FAULTS CAUGHT"))
