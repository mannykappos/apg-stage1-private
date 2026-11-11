#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_m5_contracts.py (P3-B04; DP-1.2 (B): tools/run_m5_contracts.py stays byte-identical).
Runs the M5 notification contract suite against the in-memory reference, or a candidate --notify module:attr from --path.
It prints kind=cases evidence (R1_REQUIREMENTS.md §2.7, T-K R5): one CASE line per case, the M10 human lines, any RUN_ERROR lines and one
RESULT v=3 line; the case inventory is pinned (tools/expected_counts.json); a candidate is loaded only after the trusted harness, from
its own top-level package appended to the path, and one of a trusted name is refused (P3-B04, DP-4.3 (c); tools/evkit.cases_main).
Exit codes as §2.4.  The M10 success marker is printed only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT.
Corrective pass 2 (C, A.1, K.2, amendment 2 AM2-1): the harness imports and the module-level statements that use them run in load(),
under evkit.import_guard, after the start checks, the pins and the resolved selection; the one harness call that lists and runs
every case is batch(), run by evkit.cases_main as one forked unit under P."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

TOOL = "run_m5_contracts_s1"
C = REF = None


def load():
    global C, REF
    with E.import_guard("apg.det.contracts_m5"):
        import apg.det.contracts_m5 as C  # (the trusted harness, imported first)
    with E.import_guard("apg.det.reference_m5"):
        import apg.det.reference_m5 as REF
    return {"batch": batch}


def batch(cand):
    return [[s, cid, bool(ok), str(d)] for s, cid, text, ok, d in C.run_all(cand.get("--notify") or REF.notify_env())]


if __name__ == "__main__":
    sys.exit(E.cases_main(TOOL, None, None, sys.argv[1:], candidate_options=("--notify",), success_marker="ALL CONTRACT CASES PASS",
                          load=load))
