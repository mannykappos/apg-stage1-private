#!/usr/bin/env python3
"""Shows that the M6 contract suites have teeth: every deliberately faulty MarketFeedPort / ExtractionRuntimePort must fail at least the cases listed for it."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
from apg.mkt import contracts_m6 as C, reference_m6 as REF
from apg.mkt.faulty_m6 import FAULTS
bad = 0
for fid, (text, suite, factory, expect) in FAULTS.items():
    res = C.run_all(factory if suite == 'market_feed' else None, factory if suite == 'extraction' else None)
    failed = {r[1] for r in res if not r[3]}
    ok = bool(failed) and set(expect) <= failed
    bad += not ok
    print(('CAUGHT ' if ok else 'MISSED ') + f'{fid} {text}: failed {sorted(failed)}; expected at least {expect}')
print(f'\nfaulty implementations {len(FAULTS)}  missed {bad}')
print('ALL FAULTS CAUGHT' if not bad else 'CONTRACT SUITE HAS A GAP')
sys.exit(1 if bad else 0)
