#!/usr/bin/env python3
"""Runs every M4 check except the long mutation run, in named groups that each print the time they took and can be run on their own (see RUN_COMMANDS.txt).
Usage (from the package root):  python3 -I tools/run_m4_all.py [--with-earlier]      Exit 0 only if everything passes.
Without --with-earlier the earlier milestones are covered by the M4 regression step (frozen M0 to M3 files by hash, M2 and M3 golden cases and demonstrations).  --with-earlier also
runs the whole M3 wrapper, which takes longer.   Mutation runs (long, split by module with --only):  python3 -I tools/m4_mutants.py --jobs 2   (then m3_mutants.py, m2_mutants.py)"""
import os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = [('M4 unit tests: arithmetic and figure model', 'run_m2_tests.py', ['-q', 'test_fin_arith.py'], 'failures 0  errors 0'),
     ('M4 unit tests: financial intake', 'run_m2_tests.py', ['-q', 'test_fin_intake.py'], 'failures 0  errors 0'),
     ('M4 unit tests: actual cost', 'run_m2_tests.py', ['-q', 'test_fin_costs.py'], 'failures 0  errors 0'),
     ('M4 unit tests: commitments', 'run_m2_tests.py', ['-q', 'test_fin_commitments.py'], 'failures 0  errors 0'),
     ('M4 unit tests: secured revenue', 'run_m2_tests.py', ['-q', 'test_fin_revenue.py'], 'failures 0  errors 0'),
     ('M4 unit tests: forecast', 'run_m2_tests.py', ['-q', 'test_fin_forecast.py'], 'failures 0  errors 0'),
     ('M4 unit tests: retention, security, carrying cost, cash views', 'run_m2_tests.py', ['-q', 'test_fin_cash.py'], 'failures 0  errors 0'),
     ('M4 unit tests: bridge and forecast book', 'run_m2_tests.py', ['-q', 'test_fin_bridge_book.py'], 'failures 0  errors 0'),
     ('M4 unit tests: calculation records, replay and drift', 'run_m2_tests.py', ['-q', 'test_fin_records.py'], 'failures 0  errors 0'),
     ('M4 unit tests: boundary and guard tests added after the first mutation run', 'run_m2_tests.py', ['-q', 'test_fin_boundaries.py'], 'failures 0  errors 0'),
     ('M4 unit tests: golden cases', 'run_m2_tests.py', ['-q', 'test_fin_golden.py'], 'failures 0  errors 0'),
     ('M4 unit tests: faulty-input corpus', 'run_m2_tests.py', ['-q', 'test_fin_corpus.py'], 'failures 0  errors 0'),
     ('M4 unit tests: static source rules', 'run_m2_tests.py', ['-q', 'test_fin_static.py'], 'failures 0  errors 0'),
     ('M4 golden Builder Zero cases with the independent oracle', 'run_golden_fin.py', [], 'GOLDEN OK'),
     ('M4 faulty-input corpus through intake and the calculations', 'run_fin_corpus.py', [], 'ALL CORPUS CASES PASS'),
     ('M4 register checks', 'programme_check_m4.py', [], 'ALL M4 REGISTER CHECKS PASS'),
     ('M3 register checks on the extended tables', 'programme_check_m3.py', [], 'ALL M3 REGISTER CHECKS PASS'),
     ('M4 regression against the delivered M3 package (includes the M3 and M2 regression tools)', 'run_regression_m4.py', [], 'REGRESSION OK')]
if '--with-earlier' in sys.argv:
    G.append(('The whole M3 wrapper (earlier milestones)', 'run_m3_all.py', [], 'ALL M3 CHECKS PASS'))
ok = True
t_all = time.time()
for name, tool, args, marker in G:
    t0 = time.time()
    r = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', tool), *args], capture_output=True, text=True, cwd=ROOT)
    out = r.stdout + r.stderr
    good = r.returncode == 0 and marker in out
    last = [l for l in out.strip().splitlines() if l.strip()][-1:] or ['']
    print(('PASS ' if good else 'FAIL ') + name + f'  ({time.time() - t0:.0f}s)  [' + last[0].strip()[:100] + ']', flush=True)
    if not good:
        ok = False; print(out[-1500:])
print(f'\n{time.time() - t_all:.0f}s in total')
print('ALL M4 CHECKS PASS' if ok else 'SOME M4 CHECKS FAILED')
sys.exit(0 if ok else 1)
