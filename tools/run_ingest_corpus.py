#!/usr/bin/env python3
"""Run the corpus of deliberately faulty files through the ingestion pipeline (Builder Zero accounting invoice layout).  Exit 0 only if every case gives the outcome
the corpus requires.  Amir can pass his own ingest function with --ingest module:attr (same signature as apg.ingest.pipeline.ingest_file)."""
import importlib, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
args = sys.argv[1:]
def opt(n):
    return args[args.index(n) + 1] if n in args else None
if opt('--path'):
    sys.path.insert(0, opt('--path'))
from apg import tenancy
from apg.ports import TenantMismatch
from apg.reference_impl import FakeClock, InMemoryAuditLog, InMemoryRecordStore, StaticContextProvider
from apg.ingest import corpus, demo_setup as D, pipeline
from apg.ingest.mapping import Limits
if opt('--ingest'):
    mod, attr = opt('--ingest').split(':')
    ingest = getattr(importlib.import_module(mod), attr)
else:
    ingest = pipeline.ingest_file
tpl = json.load(open(os.path.join(ROOT, 'import_templates', 'TPL-BZ-AP-INVOICES.json'), encoding='utf-8'))
bad = 0
cases = corpus.cases()
for case in cases:
    c = FakeClock('2026-10-01T09:00:00Z'); p = StaticContextProvider(c); st = InMemoryRecordStore(p); au = InMemoryAuditLog(p, c)
    p._contract_register_session('t1', 'zero_one', 'ann', ('importer',), 'human', 360000)
    s = tenancy.ScopedStore(st, au, p.resolve('t1'))
    ok, msg = corpus.check_case(case, s, c, tpl, D.DEMO_POLICY, ingest, Limits, TenantMismatch)
    bad += not ok
    print(('PASS ' if ok else 'FAIL ') + case['id'] + ' ' + case['desc'] + ('' if ok else '  -> ' + msg))
print(f'\ncorpus cases {len(cases)}  failed {bad}')
print('ALL CORPUS CASES PASS' if not bad else 'CORPUS NOT MET')
sys.exit(1 if bad else 0)
