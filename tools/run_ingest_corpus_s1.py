#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_ingest_corpus.py (P3-B03, P3-B04; DP-1.2 (B): tools/run_ingest_corpus.py stays byte-identical).
Runs the M3 ingestion corpus (apg.ingest.corpus) against apg.ingest.pipeline.ingest_file, or a candidate --ingest module:attr.
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

import json  # noqa: E402
from apg import tenancy  # noqa: E402  (the trusted harness, imported first)
from apg.ports import TenantMismatch  # noqa: E402
from apg.reference_impl import FakeClock, InMemoryAuditLog, InMemoryRecordStore, StaticContextProvider  # noqa: E402
from apg.ingest import corpus, demo_setup as D, pipeline  # noqa: E402
from apg.ingest.mapping import Limits  # noqa: E402

TOOL = "run_ingest_corpus_s1"
CASES = {c["id"]: c for c in corpus.cases()}


def run_case(cand, suite, cid):
    with open(os.path.join(ROOT, "import_templates", "TPL-BZ-AP-INVOICES.json"), encoding="utf-8") as fh:
        tpl = json.load(fh)
    c = FakeClock("2026-10-01T09:00:00Z"); p = StaticContextProvider(c); st = InMemoryRecordStore(p); au = InMemoryAuditLog(p, c)
    p._contract_register_session("t1", "zero_one", "ann", ("importer",), "human", 360000)
    s = tenancy.ScopedStore(st, au, p.resolve("t1"))
    return corpus.check_case(CASES[cid], s, c, tpl, D.DEMO_POLICY, cand.get("--ingest") or pipeline.ingest_file, Limits, TenantMismatch)


if __name__ == "__main__":
    sys.exit(E.cases_main(TOOL, lambda cand: [("ingest_corpus", cid) for cid in CASES], run_case, sys.argv[1:],
                          candidate_options=("--ingest",), success_marker="ALL CORPUS CASES PASS", human_label="corpus cases"))
