#!/usr/bin/env python3
"""Runs every M2 check except the long mutation run.  Usage (from the package root): python3 -I tools/run_m2_all.py     Exit 0 only if everything passes.
Mutation run (about five minutes):  python3 -I tools/m2_mutants.py --jobs 4"""
import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEPS = [('M0/M1 package checks', 'run_all_checks.py', [], 'ALL CHECKS PASS'), ('Unit, adversarial and golden tests', 'run_m2_tests.py', ['-q'], 'failures 0  errors 0'),
         ('Contract suites on the reference implementations', 'run_contracts.py', [], 'ALL CONTRACT CASES PASS'), ('Faulty implementations must all be caught', 'run_faults.py', [], 'ALL FAULTS CAUGHT'),
         ('CR-02 reference tests and mutants on the packaged model', 'run_cr02_reference.py', [], 'CR-02 REFERENCE RERUN OK'), ('Golden Builder Zero cases', 'run_golden.py', [], 'GOLDEN OK'),
         ('Regression against the delivered M0+M1 package', 'run_regression.py', [], 'REGRESSION OK')]
ok = True
for name, tool, args, marker in STEPS:
    r = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', tool), *args], capture_output=True, text=True, cwd=ROOT)
    good = r.returncode == 0 and marker in (r.stdout + r.stderr)
    last = [l for l in (r.stdout + r.stderr).strip().splitlines() if l.strip()][-1:] or ['']
    print(('PASS ' if good else 'FAIL ') + name + '  [' + last[0].strip()[:110] + ']')
    if not good:
        ok = False; print((r.stdout + r.stderr)[-1500:])
print('\nALL M2 CHECKS PASS' if ok else '\nSOME M2 CHECKS FAILED')
sys.exit(0 if ok else 1)
