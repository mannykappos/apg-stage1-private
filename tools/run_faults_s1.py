#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_faults.py (amendment 1 row 8, T-K; decision K-1 K22: kind=sabotage; DP-1.2 (B): the M10 file stays
byte-identical).  The plants are M10's faulty implementations (apg/faulty_impls.py FAULTS, unchanged), each with its M10 list of contract
cases it must fail; the in-memory reference implementation is the start and end control and must fail no case (tools/evkit.faults_main).
Usage: python3 -I -S tools/run_faults_s1.py [--list] [--ids ID[,ID]] [--run-id ID] | --pin --reason TEXT --cause TEXT
Exit codes as §2.4; the M10 marker ALL FAULTS CAUGHT only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT.
Corrective pass 2 (C, B): the harness imports and PLANTS run in load(), under evkit.import_guard, after the start checks
(evkit.guarded_load); every plant and both controls run as forked units under P (evkit.faults_main)."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

TOOL = "run_faults_s1"
R = ContractEnv = FAULTS = FakeClock = StaticContextProvider = InMemoryRecordStore = InMemoryAuditLog = None
PLANTS = []


def load():
    global R, ContractEnv, FAULTS, FakeClock, StaticContextProvider, InMemoryRecordStore, InMemoryAuditLog, PLANTS
    with E.import_guard("apg.contracts.run"):
        from apg.contracts import run as R
    with E.import_guard("apg.contracts.framework"):
        from apg.contracts.framework import ContractEnv
    with E.import_guard("apg.faulty_impls"):
        from apg.faulty_impls import FAULTS
    with E.import_guard("apg.reference_impl"):
        from apg.reference_impl import FakeClock, StaticContextProvider, InMemoryRecordStore, InMemoryAuditLog
    with E.import_guard("apg.faulty_impls"):
        PLANTS = [(fid, text, (lambda factory=factory: failed(factory)), list(expect)) for fid, (text, factory, expect) in FAULTS.items()]


def reference():
    c = FakeClock(); p = StaticContextProvider(c)
    return ContractEnv(p, InMemoryRecordStore(p), InMemoryAuditLog(p, c), c.advance)


def failed(factory):
    return {r[1] for r in R.run(factory) if not r[3]}


if __name__ == "__main__":
    rc = E.guarded_load(TOOL, "sabotage", load)
    if rc is not None:
        sys.exit(rc)
    sys.exit(E.faults_main(TOOL, PLANTS, lambda: failed(reference), sys.argv[1:], success_marker="ALL FAULTS CAUGHT"))
