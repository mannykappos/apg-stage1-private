#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_m3_contracts.py (P2-B8, P3-B04; DP-1.2 (B): tools/run_m3_contracts.py stays byte-identical).
Runs the M3 file-store and job-runner contract suites against the in-memory references, or candidates --files / --jobs module:attr.
It prints kind=cases evidence (R1_REQUIREMENTS.md §2.7, T-K R5): one CASE line per case, the M10 human lines, any RUN_ERROR lines and one
RESULT v=2 line; the case inventory is pinned (tools/expected_counts.json); a candidate is loaded only after the trusted harness, from
its own top-level package appended to the path, and one of a trusted name is refused (P3-B04, DP-4.3 (c); tools/evkit.cases_main).
Exit codes as §2.4.  The M10 success marker is printed only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

from apg.ingest import contracts_m3 as C, reference_m3 as REF  # noqa: E402  (the trusted harness, imported first)

TOOL = "run_m3_contracts_s1"
_CACHE = {}


def results(cand):
    if "r" not in _CACHE:
        _CACHE["r"] = {(s, cid): (ok, d) for s, cid, text, ok, d in C.run_all(cand.get("--files") or REF.file_env(),
                                                                            cand.get("--jobs") or REF.job_env())}
    return _CACHE["r"]


if __name__ == "__main__":
    sys.exit(E.cases_main(TOOL, lambda cand: list(results(cand)), lambda cand, s, c: results(cand)[(s, c)], sys.argv[1:],
                          candidate_options=("--files", "--jobs"), success_marker="ALL CONTRACT CASES PASS"))
