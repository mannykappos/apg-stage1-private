#!/usr/bin/env python3
"""Run the M5 port contract suite (NotificationPort EDR-10).
  python3 -I tools/run_m5_contracts.py [--notify module:attr] [--path dir]
With no options, runs against the in-memory reference.  A NOTIFY factory returns apg.det.contracts_m5.NotifyEnv(provider, notifier, advance).  Exit 0 only if every case passes."""
import importlib, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
args = sys.argv[1:]
def opt(n):
    return args[args.index(n) + 1] if n in args else None
if opt('--path'):
    sys.path.insert(0, opt('--path'))
from apg.det import contracts_m5 as C, reference_m5 as REF
spec = opt('--notify')
if spec:
    mod, attr = spec.split(':')
    factory = getattr(importlib.import_module(mod), attr)
else:
    factory = REF.notify_env()
res = C.run_all(factory)
for suite, cid, text, ok, detail in res:
    print(('PASS ' if ok else 'FAIL ') + cid + ' ' + text + ('' if ok else '  -> ' + detail))
bad = [r for r in res if not r[3]]
print(f'\ncontract cases {len(res)}  failed {len(bad)}')
print('ALL CONTRACT CASES PASS' if not bad else 'CONTRACT NOT MET')
sys.exit(1 if bad else 0)
