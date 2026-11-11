#!/usr/bin/env python3
"""Run the corpus of deliberately faulty or borderline detection inputs and configurations through the detection layer.  Exit 0 only if every case gives the result the corpus requires.
Amir can run the same corpus against the Engine with --world module:attr, a callable(approved) that returns an object with the world interface documented in apg/det/corpus_det.py."""
import importlib, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
args = sys.argv[1:]
def opt(n):
    return args[args.index(n) + 1] if n in args else None
if opt('--path'):
    sys.path.insert(0, opt('--path'))
from apg.det import corpus_det as K
if opt('--world'):
    mod, attr = opt('--world').split(':')
    factory = getattr(importlib.import_module(mod), attr)
else:
    factory = lambda approved: K.ReferenceWorld(ROOT, approved=approved)
only = opt('--only')
bad = 0
cases = [c for c in K.cases() if not only or c['id'] in only.split(',')]
for case in cases:
    ok, msg = K.check_case(case, factory)
    bad += not ok
    print(('PASS ' if ok else 'FAIL ') + case['id'] + ' ' + case['desc'] + ('' if ok else '  -> ' + msg))
print(f'\ncorpus cases {len(cases)}  failed {bad}')
print('ALL CORPUS CASES PASS' if not bad else 'CORPUS NOT MET')
sys.exit(1 if bad else 0)
