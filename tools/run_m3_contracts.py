#!/usr/bin/env python3
"""Run the M3 port contract suites (FileStorePort EDR-07, JobRunnerPort EDR-04).
  python3 -I tools/run_m3_contracts.py [--suite file_store|job_runner] [--files module:attr] [--jobs module:attr] [--path dir]
With no options, runs against the in-memory references.  A FILES factory returns apg.ingest.contracts_m3.FileEnv(provider, files, advance); a JOBS factory returns
JobEnv(provider, store, audit, make_runner, advance, sleeps).  Exit 0 only if every case passes."""
import importlib, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
args = sys.argv[1:]
def opt(n):
    return args[args.index(n) + 1] if n in args else None
if opt('--path'):
    sys.path.insert(0, opt('--path'))
from apg.ingest import contracts_m3 as C, reference_m3 as REF
def load(spec, default):
    if not spec:
        return default
    mod, attr = spec.split(':')
    return getattr(importlib.import_module(mod), attr)
res = C.run_all(load(opt('--files'), REF.file_env()), load(opt('--jobs'), REF.job_env()), [opt('--suite')] if opt('--suite') else None)
for suite, cid, text, ok, detail in res:
    print(('PASS ' if ok else 'FAIL ') + cid + ' ' + text + ('' if ok else '  -> ' + detail))
bad = [r for r in res if not r[3]]
print(f'\ncontract cases {len(res)}  failed {len(bad)}')
print('ALL CONTRACT CASES PASS' if not bad else 'CONTRACT NOT MET')
sys.exit(1 if bad else 0)
