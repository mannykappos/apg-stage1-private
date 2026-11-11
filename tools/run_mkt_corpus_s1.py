#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_mkt_corpus.py (P4-B15; DP-1.2 (B): tools/run_mkt_corpus.py stays byte-identical).
Runs the M6 procurement corpus (tests/corpus_mkt.py).
It prints kind=cases evidence (R1_REQUIREMENTS.md §2.7, T-K R5): one CASE line per case, the M10 human lines, any RUN_ERROR lines and one
RESULT v=3 line; the case inventory is pinned (tools/expected_counts.json); a candidate is loaded only after the trusted harness, from
its own top-level package appended to the path, and one of a trusted name is refused (P3-B04, DP-4.3 (c); tools/evkit.cases_main).
Exit codes as §2.4.  The M10 success marker is printed only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT.
Corrective pass 2 (C, A.1, K.2): the harness imports and the module-level statements that use them run in load(), under
evkit.import_guard, after the start checks, the pins and the resolved selection; each case runs as a forked unit under P
(evkit.cases_main)."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

TOOL = 'run_mkt_corpus_s1'
K = None
CASES = {}


def load():
    global K, CASES
    with E.import_guard('tests.corpus_mkt'):
        from tests import corpus_mkt as K  # (the trusted harness)
        CASES = {c['id']: c for c in K.cases()}
    return {'enumerate_cases': lambda cand: [('mkt_corpus', cid) for cid in CASES], 'run_case': lambda cand, s, c: K.check_case(CASES[c])}


if __name__ == '__main__':
    sys.exit(E.cases_main(TOOL, None, None, sys.argv[1:], success_marker='ALL CORPUS CASES PASS', human_label='corpus cases', load=load))
