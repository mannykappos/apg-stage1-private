#!/usr/bin/env python3
"""Runs every M3 check except the long mutation run, and every earlier check that must still pass.  Usage (from the package root): python3 -I tools/run_m3_all.py
Each step prints the time it took and can be run on its own (see RUN_COMMANDS.txt).  Exit 0 only if everything passes.
Mutation runs (long):  python3 -I tools/m3_mutants.py --jobs 2     python3 -I tools/m2_mutants.py --jobs 2"""
import os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEPS = [('M0/M1 package checks', 'run_all_checks.py', [], 'ALL CHECKS PASS'),
         ('All unit, adversarial and golden tests (M2 tests unchanged, M3 tests added)', 'run_m2_tests.py', ['-q'], 'failures 0  errors 0'),
         ('M2 contract suites on the reference implementations', 'run_contracts.py', [], 'ALL CONTRACT CASES PASS'), ('M2 faulty implementations must all be caught', 'run_faults.py', [], 'ALL FAULTS CAUGHT'),
         ('M3 contract suites: FileStorePort and JobRunnerPort', 'run_m3_contracts.py', [], 'ALL CONTRACT CASES PASS'), ('M3 faulty file stores and job runners must all be caught', 'run_m3_faults.py', [], 'ALL FAULTS CAUGHT'),
         ('Faulty-file corpus through the ingestion pipeline', 'run_ingest_corpus.py', [], 'ALL CORPUS CASES PASS'),
         ('CR-02 reference tests and mutants on the packaged model', 'run_cr02_reference.py', [], 'CR-02 REFERENCE RERUN OK'),
         ('M2 golden Builder Zero cases', 'run_golden.py', [], 'GOLDEN OK'), ('M3 golden Builder Zero cases with the independent oracle', 'run_golden_m3.py', [], 'GOLDEN OK'),
         ('M3 register checks', 'programme_check_m3.py', [], 'ALL M3 REGISTER CHECKS PASS'),
         ('M2 regression tool (against the delivered M0+M1 package)', 'run_regression.py', [], 'REGRESSION OK'), ('M3 regression against the delivered M2 package', 'run_regression_m3.py', [], 'REGRESSION OK')]
ok = True
t_all = time.time()
for name, tool, args, marker in STEPS:
    t0 = time.time()
    r = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', tool), *args], capture_output=True, text=True, cwd=ROOT)
    good = r.returncode == 0 and marker in (r.stdout + r.stderr)
    last = [l for l in (r.stdout + r.stderr).strip().splitlines() if l.strip()][-1:] or ['']
    print(('PASS ' if good else 'FAIL ') + name + f'  ({time.time() - t0:.0f}s)  [' + last[0].strip()[:100] + ']', flush=True)
    if not good:
        ok = False; print((r.stdout + r.stderr)[-1500:])
print(f'\n{time.time() - t_all:.0f}s in total')
print('ALL M3 CHECKS PASS' if ok else 'SOME M3 CHECKS FAILED')
sys.exit(0 if ok else 1)
