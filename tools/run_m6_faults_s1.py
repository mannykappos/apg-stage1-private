#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_m6_faults.py (amendment 1 row 10, T-K; decision K-1 K24: kind=sabotage; DP-1.2 (B): the M10 file stays
byte-identical).  The plants are M10's faulty MarketFeed and ExtractionRuntime ports (apg/mkt/faulty_m6.py FAULTS, unchanged), each run on its
own suite as M10 does; the reference doubles on both suites are the start and end control and must fail no case (tools/evkit.faults_main).
Usage: python3 -I -S tools/run_m6_faults_s1.py [--list] [--ids ID[,ID]] [--run-id ID] | --pin --reason TEXT --cause TEXT
Exit codes as §2.4; the M10 marker ALL FAULTS CAUGHT only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT.
Corrective pass 2 (C, B): the harness imports and PLANTS run in load(), under evkit.import_guard, after the start checks
(evkit.guarded_load); every plant and both controls run as forked units under P (evkit.faults_main)."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

TOOL = "run_m6_faults_s1"
C = REF = FAULTS = None
PLANTS = []


def load():
    global C, REF, FAULTS, PLANTS
    with E.import_guard("apg.mkt.contracts_m6"):
        import apg.mkt.contracts_m6 as C
    with E.import_guard("apg.mkt.reference_m6"):
        import apg.mkt.reference_m6 as REF
    with E.import_guard("apg.mkt.faulty_m6"):
        from apg.mkt.faulty_m6 import FAULTS
        PLANTS = [(fid, text, (lambda suite=suite, factory=factory: failed_for(suite, factory)), list(expect))
                  for fid, (text, suite, factory, expect) in FAULTS.items()]


def failed_for(suite, factory):
    res = C.run_all(factory if suite == "market_feed" else None, factory if suite == "extraction" else None)
    return {r[1] for r in res if not r[3]}


if __name__ == "__main__":
    rc = E.guarded_load(TOOL, "sabotage", load)
    if rc is not None:
        sys.exit(rc)
    sys.exit(E.faults_main(TOOL, PLANTS, lambda: {r[1] for r in C.run_all(REF.feed_env(), REF.extract_env()) if not r[3]},
                           sys.argv[1:], success_marker="ALL FAULTS CAUGHT"))
