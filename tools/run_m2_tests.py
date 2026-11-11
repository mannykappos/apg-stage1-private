#!/usr/bin/env python3
"""Runs the M2 unit, adversarial and regression tests (unittest, standard library).  Usage: python3 -I tools/run_m2_tests.py [-q] [--failfast] [pattern]
Env APG_ROOT: import the apg package from another folder (used by the mutation run)."""
import os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT)
args = [a for a in sys.argv[1:] if not a.startswith('-')]
suite = unittest.defaultTestLoader.discover(os.path.join(ROOT, 'tests'), pattern=(args[0] if args else 'test_*.py'), top_level_dir=ROOT)
r = unittest.TextTestRunner(verbosity=0 if '-q' in sys.argv else 1, failfast='--failfast' in sys.argv, stream=sys.stderr if '-q' in sys.argv else sys.stdout).run(suite)
print(f'tests {r.testsRun}  failures {len(r.failures)}  errors {len(r.errors)}')
sys.exit(0 if r.wasSuccessful() else 1)
