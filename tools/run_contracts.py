#!/usr/bin/env python3
"""Run the port contract suites.  Usage: python3 -I tools/run_contracts.py [--factory module:attr] [--path dir] [--suite NAME]
With no --factory, runs against the in-memory reference implementations.  Exit 0 only if every case passes."""
import importlib, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True
args = sys.argv[1:]
def opt(n):
    return args[args.index(n) + 1] if n in args else None
if opt('--path'):
    sys.path.insert(0, opt('--path'))
from apg.contracts import run as R
from apg.contracts.framework import ContractEnv
if opt('--factory'):
    mod, attr = opt('--factory').split(':')
    factory = getattr(importlib.import_module(mod), attr)
else:
    from apg.reference_impl import FakeClock, StaticContextProvider, InMemoryRecordStore, InMemoryAuditLog
    def factory():
        c = FakeClock(); p = StaticContextProvider(c)
        return ContractEnv(p, InMemoryRecordStore(p), InMemoryAuditLog(p, c), c.advance)
res = R.run(factory, [opt('--suite')] if opt('--suite') else None)
for suite, cid, text, ok, detail in res:
    print(('PASS ' if ok else 'FAIL ') + cid + ' ' + text + ('' if ok else '  -> ' + detail))
n, bad, _ = R.summarise(res)
print(f'\ncontract cases {n}  failed {bad}')
print('ALL CONTRACT CASES PASS' if not bad else 'CONTRACT NOT MET')
sys.exit(1 if bad else 0)
