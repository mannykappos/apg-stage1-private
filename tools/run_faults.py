#!/usr/bin/env python3
"""Shows that the contract suites have teeth: every deliberately faulty implementation must fail at least the contract cases listed for it."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
from apg.contracts import run as R
from apg.faulty_impls import FAULTS
bad = 0
for fid, (text, factory, expect) in FAULTS.items():
    res = R.run(factory)
    failed = {r[1] for r in res if not r[3]}
    ok = bool(failed) and set(expect) <= failed
    bad += not ok
    print(('CAUGHT ' if ok else 'MISSED ') + f'{fid} {text}: failed {sorted(failed)}; expected at least {expect}')
print(f'\nfaulty implementations {len(FAULTS)}  missed {bad}')
print('ALL FAULTS CAUGHT' if not bad else 'CONTRACT SUITE HAS A GAP')
sys.exit(1 if bad else 0)
