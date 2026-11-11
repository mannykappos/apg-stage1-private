#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_fin_corpus.py (P3-B03, P3-B04; DP-1.2 (B): tools/run_fin_corpus.py stays byte-identical).
Runs the fin corpus (apg/fin/corpus_fin.py) against its reference world, or a candidate --world module:attr.
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

from apg.fin import corpus_fin as K  # noqa: E402  (the trusted harness, imported first)

TOOL = 'run_fin_corpus_s1'
CASES = {c['id']: c for c in K.cases()}


def run_case(cand, suite, cid):
    factory = cand.get('--world') or (lambda approved: K.ReferenceWorld(ROOT, approved=approved))
    return K.check_case(CASES[cid], factory)


if __name__ == '__main__':
    sys.exit(E.cases_main(TOOL, lambda cand: [('fin_corpus', cid) for cid in CASES], run_case, sys.argv[1:],
                          candidate_options=('--world',), success_marker='ALL CORPUS CASES PASS', human_label='corpus cases'))
