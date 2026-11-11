#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_m6_contracts.py (amendment 1 row 13, T-K; decision K-1 K26: kind=cases; DP-1.2 (B): the M10 file stays
byte-identical).  Runs the M6 port contract suites (market_feed, EDR-09; extraction, EDR-08).  Each suite runs against its candidate
(--feed / --extract module:attr from --path, loaded after the trusted harness, §2.5, DP-4.3 (c)) or else its in-memory reference double;
both suites always run, so the pinned inventory is always complete (M10 ran only the one suite whose candidate was given; --suite NAME
selects one suite here).  The case inventory is pinned (tools/evkit.cases_main).
Usage: python3 -I -S tools/run_m6_contracts_s1.py [--path DIR [--feed module:attr] [--extract module:attr]] [--suite NAME] [--only ID,..]
Exit codes as §2.4; the M10 marker ALL CONTRACT CASES PASS only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

from apg.mkt import contracts_m6 as C, reference_m6 as REF  # noqa: E402  (the trusted harness, imported first)

_CACHE = {}


def results(cand):
    if "r" not in _CACHE:
        _CACHE["r"] = {(s, cid): (ok, d) for s, cid, text, ok, d in C.run_all(cand.get("--feed") or REF.feed_env(),
                                                                            cand.get("--extract") or REF.extract_env())}
    return _CACHE["r"]


if __name__ == "__main__":
    sys.exit(E.cases_main("run_m6_contracts_s1", lambda cand: list(results(cand)), lambda cand, s, c: results(cand)[(s, c)], sys.argv[1:],
                          candidate_options=("--feed", "--extract"), success_marker="ALL CONTRACT CASES PASS"))
