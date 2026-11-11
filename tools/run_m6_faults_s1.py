#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_m6_faults.py (amendment 1 row 10, T-K; decision K-1 K24: kind=sabotage; DP-1.2 (B): the M10 file stays
byte-identical).  The plants are M10's faulty MarketFeed and ExtractionRuntime ports (apg/mkt/faulty_m6.py FAULTS, unchanged), each run on its
own suite as M10 does; the reference doubles on both suites are the start and end control and must fail no case (tools/evkit.faults_main).
Usage: python3 -I -S tools/run_m6_faults_s1.py [--list] [--ids ID[,ID]] [--run-id ID] | --pin --reason TEXT --cause TEXT
Exit codes as §2.4; the M10 marker ALL FAULTS CAUGHT only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

from apg.mkt import contracts_m6 as C, reference_m6 as REF  # noqa: E402
from apg.mkt.faulty_m6 import FAULTS  # noqa: E402


def failed_for(suite, factory):
    res = C.run_all(factory if suite == "market_feed" else None, factory if suite == "extraction" else None)
    return {r[1] for r in res if not r[3]}


PLANTS = [(fid, text, (lambda suite=suite, factory=factory: failed_for(suite, factory)), list(expect))
          for fid, (text, suite, factory, expect) in FAULTS.items()]

if __name__ == "__main__":
    sys.exit(E.faults_main("run_m6_faults_s1", PLANTS, lambda: {r[1] for r in C.run_all(REF.feed_env(), REF.extract_env()) if not r[3]},
                           sys.argv[1:], success_marker="ALL FAULTS CAUGHT"))
