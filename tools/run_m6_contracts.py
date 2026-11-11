#!/usr/bin/env python3
"""Run the M6 port contract suites (MarketFeedPort EDR-09, ExtractionRuntimePort EDR-08).
  python3 -I tools/run_m6_contracts.py [--feed module:attr] [--extract module:attr] [--path dir]
With no options, runs both against the in-memory reference doubles.  A factory returns apg.mkt.contracts_m6.FeedEnv / ExtractEnv.  Exit 0 only if every case passes."""
import importlib, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
args = sys.argv[1:]
def opt(n):
    return args[args.index(n) + 1] if n in args else None
if opt('--path'):
    sys.path.insert(0, opt('--path'))
from apg.mkt import contracts_m6 as C, reference_m6 as REF
def pick(name, default):
    spec = opt(name)
    if not spec:
        return default
    mod, attr = spec.split(':')
    return getattr(importlib.import_module(mod), attr)
only = ('--feed' in args) != ('--extract' in args)
feed = pick('--feed', None if only and '--extract' in args else REF.feed_env())
extract = pick('--extract', None if only and '--feed' in args else REF.extract_env())
res = C.run_all(feed, extract)
for suite, cid, text, ok, detail in res:
    print(('PASS ' if ok else 'FAIL ') + cid + ' ' + text + ('' if ok else '  -> ' + detail))
bad = [r for r in res if not r[3]]
print(f'\ncontract cases {len(res)}  failed {len(bad)}')
print('ALL CONTRACT CASES PASS' if not bad else 'CONTRACT NOT MET')
sys.exit(1 if bad else 0)
