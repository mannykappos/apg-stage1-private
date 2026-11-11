#!/usr/bin/env python3
"""Shows that the M3 contract suites have teeth: every deliberately faulty FileStore / JobRunner must fail at least the cases listed for it."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
from apg.ingest import contracts_m3 as C, reference_m3 as REF
from apg.ingest.faulty_m3 import FAULTS
bad = 0
for fid, (text, kind, factory, expect) in FAULTS.items():
    suite = C.FS if kind == 'files' else C.JR
    res = C.run_all(factory if kind == 'files' else REF.file_env(), factory if kind == 'jobs' else REF.job_env(), [suite])
    failed = {r[1] for r in res if not r[3]}
    ok = bool(failed) and set(expect) <= failed
    bad += not ok
    print(('CAUGHT ' if ok else 'MISSED ') + f'{fid} {text}: failed {sorted(failed)}; expected at least {expect}')
print(f'\nfaulty implementations {len(FAULTS)}  missed {bad}')
print('ALL FAULTS CAUGHT' if not bad else 'CONTRACT SUITE HAS A GAP')
sys.exit(1 if bad else 0)
