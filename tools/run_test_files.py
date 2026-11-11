#!/usr/bin/env python3
"""Runs the named test files (exact file names in tests/) in ONE interpreter and prints 'tests N  failures F  errors E', like tools/run_m2_tests.py does for a pattern.  Used by
tools/run_f671_all.py to run the whole suite in small, separately countable groups.  Usage: python3 -I tools/run_test_files.py [-q] test_a.py test_b.py ...   Exit 0 only if all pass."""
import os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT)
names = [a for a in sys.argv[1:] if not a.startswith('-')]
suite = unittest.TestSuite()
for n in names:
    if not os.path.isfile(os.path.join(ROOT, 'tests', n)):
        print('no such test file: %s' % n)
        sys.exit(2)
    suite.addTests(unittest.defaultTestLoader.discover(os.path.join(ROOT, 'tests'), pattern=n, top_level_dir=ROOT))
r = unittest.TextTestRunner(verbosity=0 if '-q' in sys.argv else 1, stream=sys.stderr if '-q' in sys.argv else sys.stdout).run(suite)
print(f'tests {r.testsRun}  failures {len(r.failures)}  errors {len(r.errors)}')
sys.exit(0 if r.wasSuccessful() and r.testsRun else 1)
