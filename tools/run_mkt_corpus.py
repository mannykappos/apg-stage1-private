#!/usr/bin/env python3
"""Run the corpus of deliberately faulty or borderline procurement inputs (tests/corpus_mkt.py) through the real M6 pipeline.  Exit 0 only if every case gives the result the corpus requires.
  python3 -I tools/run_mkt_corpus.py [--only A01,B02]"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
args = sys.argv[1:]
only = args[args.index('--only') + 1].split(',') if '--only' in args else None
from tests import corpus_mkt as K
bad = 0
cs = [c for c in K.cases() if not only or c['id'] in only]
for c in cs:
    ok, msg = K.check_case(c)
    bad += not ok
    print(('PASS ' if ok else 'FAIL ') + c['id'] + ' ' + c['desc'] + ('' if ok else '  -> ' + msg))
print(f'\ncorpus cases {len(cs)}  failed {bad}')
print('ALL CORPUS CASES PASS' if not bad else 'CORPUS NOT MET')
sys.exit(1 if bad else 0)
