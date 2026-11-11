#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_guard_contract.py (amendment 1 row 11, T-K; decision K-1 K25: kind=cases; DP-1.2 (B): the M10 file stays
byte-identical).  Runs the record-store guard contract (RG-01 to RG-08) against the in-memory reference store, or a candidate --factory
module:attr from --path, loaded after the trusted harness (§2.5, DP-4.3 (c); tools/evkit.cases_main); the case inventory is pinned.
Usage: python3 -I -S tools/run_guard_contract_s1.py [--path DIR --factory module:attr] [--only RG-01,..] [--run-id ID] | --pin --reason T --cause T
Exit codes as §2.4; the M10 marker ALL GUARD CASES PASS only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT.
Corrective pass 2 (C, A.1, K.2, amendment 2 AM2-1): the harness imports and the module-level statements that use them run in load(),
under evkit.import_guard, after the start checks, the pins and the resolved selection; the one harness call that lists and runs
every case is batch(), run by evkit.cases_main as one forked unit under P."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

SUITE = "record_store_guard"
ContractEnv = run_guard_suite = FakeClock = StaticContextProvider = InMemoryRecordStore = InMemoryAuditLog = None


def load():
    global ContractEnv, run_guard_suite, FakeClock, StaticContextProvider, InMemoryRecordStore, InMemoryAuditLog
    with E.import_guard("apg.contracts.framework"):
        from apg.contracts.framework import ContractEnv  # (the trusted harness, imported first)
    with E.import_guard("apg.contracts.record_store_guard_contract"):
        from apg.contracts.record_store_guard_contract import run_guard_suite
    with E.import_guard("apg.reference_impl"):
        from apg.reference_impl import FakeClock, StaticContextProvider, InMemoryRecordStore, InMemoryAuditLog
    return {"batch": batch}


def reference():
    c = FakeClock(); p = StaticContextProvider(c)
    return ContractEnv(p, InMemoryRecordStore(p), InMemoryAuditLog(p, c), c.advance)


def batch(cand):
    return [[SUITE, r[0], bool(r[2]), str(r[3])] for r in run_guard_suite(cand.get("--factory") or reference)]


if __name__ == "__main__":
    sys.exit(E.cases_main("run_guard_contract_s1", None, None, sys.argv[1:], candidate_options=("--factory",),
                          success_marker="ALL GUARD CASES PASS", human_label="guard cases", load=load))
