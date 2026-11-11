#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_guard_contract.py (amendment 1 row 11, T-K; decision K-1 K25: kind=cases; DP-1.2 (B): the M10 file stays
byte-identical).  Runs the record-store guard contract (RG-01 to RG-08) against the in-memory reference store, or a candidate --factory
module:attr from --path, loaded after the trusted harness (§2.5, DP-4.3 (c); tools/evkit.cases_main); the case inventory is pinned.
Usage: python3 -I -S tools/run_guard_contract_s1.py [--path DIR --factory module:attr] [--only RG-01,..] [--run-id ID] | --pin --reason T --cause T
Exit codes as §2.4; the M10 marker ALL GUARD CASES PASS only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

from apg.contracts.framework import ContractEnv  # noqa: E402  (the trusted harness, imported first)
from apg.contracts.record_store_guard_contract import run_guard_suite  # noqa: E402
from apg.reference_impl import FakeClock, StaticContextProvider, InMemoryRecordStore, InMemoryAuditLog  # noqa: E402

SUITE = "record_store_guard"
_CACHE = {}


def reference():
    c = FakeClock(); p = StaticContextProvider(c)
    return ContractEnv(p, InMemoryRecordStore(p), InMemoryAuditLog(p, c), c.advance)


def results(cand):
    if "r" not in _CACHE:
        _CACHE["r"] = {r[0]: (r[2], r[3]) for r in run_guard_suite(cand.get("--factory") or reference)}
    return _CACHE["r"]


if __name__ == "__main__":
    sys.exit(E.cases_main("run_guard_contract_s1", lambda cand: [(SUITE, c) for c in results(cand)], lambda cand, s, c: results(cand)[c],
                          sys.argv[1:], candidate_options=("--factory",), success_marker="ALL GUARD CASES PASS", human_label="guard cases"))
