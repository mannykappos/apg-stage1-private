#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_m91_contracts.py (amendment 1 row 14, T-K; decision K-1 K27: kind=cases; DP-1.2 (B): the M10 file stays
byte-identical).  Runs the M9.1 ProjectActionPort contract suite (EDR-31) against the in-memory reference, or a candidate --action
module:attr from --path, loaded after the trusted harness (§2.5, DP-4.3 (c)); the case inventory is pinned (tools/evkit.cases_main).
Usage: python3 -I -S tools/run_m91_contracts_s1.py [--path DIR --action module:attr] [--only ID,..] [--run-id ID] | --pin --reason T --cause T
Exit codes as §2.4; the M10 marker ALL CONTRACT CASES PASS only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

from apg.api import contracts_m9 as C, reference_m9 as REF  # noqa: E402  (the trusted harness, imported first)

_CACHE = {}


def results(cand):
    if "r" not in _CACHE:
        _CACHE["r"] = {(s, cid): (ok, d) for s, cid, text, ok, d in C.run_all(cand.get("--action") or REF.action_env())}
    return _CACHE["r"]


if __name__ == "__main__":
    sys.exit(E.cases_main("run_m91_contracts_s1", lambda cand: list(results(cand)), lambda cand, s, c: results(cand)[(s, c)], sys.argv[1:],
                          candidate_options=("--action",), success_marker="ALL CONTRACT CASES PASS"))
