#!/usr/bin/env python3
"""Run the record-store guard contract (APG-M7.3, EDR-36: apg/contracts/record_store_guard_contract.py, cases RG-01 to RG-08).
Usage: python3 -I tools/run_guard_contract.py [--factory module:attr] [--path dir]
With no --factory, runs against the in-memory reference store.  The factory returns a fresh ContractEnv, as for tools/run_contracts.py.  Exit 0 only if every case passes."""
import importlib, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True
args = sys.argv[1:]


def opt(n):
    return args[args.index(n) + 1] if n in args else None


if opt('--path'):
    sys.path.insert(0, opt('--path'))
from apg.contracts.framework import ContractEnv                    # noqa: E402
from apg.contracts.record_store_guard_contract import run_guard_suite   # noqa: E402
if opt('--factory'):
    mod, attr = opt('--factory').split(':')
    factory = getattr(importlib.import_module(mod), attr)
else:
    from apg.reference_impl import FakeClock, StaticContextProvider, InMemoryRecordStore, InMemoryAuditLog

    def factory():
        c = FakeClock(); p = StaticContextProvider(c)
        return ContractEnv(p, InMemoryRecordStore(p), InMemoryAuditLog(p, c), c.advance)
res = run_guard_suite(factory)
for cid, text, ok, detail in res:
    print(('PASS ' if ok else 'FAIL ') + cid + ' ' + text + ('' if ok else '  -> ' + detail))
bad = [r for r in res if not r[2]]
print(f'\nguard cases {len(res)}  failed {len(bad)}')
print('ALL GUARD CASES PASS' if not bad else 'GUARD CONTRACT NOT MET')
sys.exit(1 if bad else 0)
