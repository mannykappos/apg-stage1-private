#!/usr/bin/env python3
"""Mutation-run helper: runs the named test files in order inside ONE interpreter, stopping at the first failure.  Prints the failing file name (or nothing) and exits 0 / 1.
Usage: python3 -I tools/mut_runner.py file1 file2 ...   (run from the package root)"""
import os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT)
for name in sys.argv[1:]:
    suite = unittest.defaultTestLoader.discover(os.path.join(ROOT, 'tests'), pattern=name, top_level_dir=ROOT)
    r = unittest.TextTestRunner(verbosity=0, failfast=True, stream=open(os.devnull, 'w')).run(suite)
    if not r.wasSuccessful() or r.testsRun == 0:
        print(name.replace('test_det_', '').replace('test_fin_', '').replace('.py', ''))
        sys.exit(1)
sys.exit(0)
