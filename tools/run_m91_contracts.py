#!/usr/bin/env python3
"""Run the M9.1 port contract suite (ProjectActionPort EDR-31).
  python3 -I tools/run_m91_contracts.py [--action module:attr] [--path dir]
With no options, runs against the in-memory reference.  An ACTION factory returns apg.api.contracts_m9.ActionEnv(provider, port, advance).  Exit 0 only if every case passes."""
import importlib, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
args = sys.argv[1:]
def opt(n):
    return args[args.index(n) + 1] if n in args else None
if opt('--path'):
    sys.path.insert(0, opt('--path'))
from apg.api import contracts_m9 as C, reference_m9 as REF
spec = opt('--action')
if spec:
    mod, attr = spec.split(':')
    factory = getattr(importlib.import_module(mod), attr)
else:
    factory = REF.action_env()
res = C.run_all(factory)
for suite, cid, text, ok, detail in res:
    print(('PASS ' if ok else 'FAIL ') + cid + ' ' + text + ('' if ok else '  -> ' + detail))
bad = [r for r in res if not r[3]]
print(f'\ncontract cases {len(res)}  failed {len(bad)}')
print('ALL CONTRACT CASES PASS' if not bad else 'CONTRACT NOT MET')
sys.exit(1 if bad else 0)
