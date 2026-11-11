#!/usr/bin/env python3
"""Runs every M5 check except the long mutation run, in named groups that each print the time they took and can be run on their own (see RUN_COMMANDS.txt).
Usage (from the package root):  python3 -I tools/run_m5_all.py [--with-earlier]      Exit 0 only if everything passes.
Without --with-earlier the earlier milestones are covered by the M5 regression step (frozen M0 to M4 files by hash, M2 to M4 golden cases and demonstrations).  --with-earlier also
runs the whole M4 wrapper, which takes longer.   Mutation runs (long, split by module with --only):  python3 -I tools/m5_mutants.py --jobs 2   (then m4_mutants.py, m3_mutants.py, m2_mutants.py)"""
import os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = lambda label, f: ('M5 unit tests: ' + label, 'run_m2_tests.py', ['-q', f], 'failures 0  errors 0')
G = [T('signal contract', 'test_det_signal.py'), T('shared helpers', 'test_det_common.py'), T('detection policy and its bounds', 'test_det_policy*.py'), T('detection intake', 'test_det_intake.py'), T('cost rules and their edge cases', 'test_det_rules_cost*.py'), T('commercial rules and their edge cases', 'test_det_rules_commercial*.py'),
     T('operations rules and their edge cases', 'test_det_rules_ops*.py'), T('signals, runs and the two reproducible formulas', 'test_det_detect.py'), T('run pins, malformed results and the check of a stored run', 'test_det_run_edges.py'), T('finding lifecycle, monitor and link edge cases', 'test_det_findings*.py'),
     T('noise control', 'test_det_noise.py'), T('monitor', 'test_det_monitor.py'), T('overlap and portfolio', 'test_det_portfolio.py'), T('notification contract suite and faulty notifiers', 'test_det_contracts.py'),
     T('static source rules', 'test_det_static.py'), T('faulty-input corpus', 'test_det_corpus.py'), T('golden cases', 'test_det_golden.py'),
     ('M5 golden Builder Zero cases with the independent oracle', 'run_golden_det.py', [], 'GOLDEN OK'),
     ('M5 faulty-input corpus through intake and the detection rules', 'run_det_corpus.py', [], 'ALL CORPUS CASES PASS'),
     ('M5 NotificationPort contract suite against the in-memory reference', 'run_m5_contracts.py', [], 'ALL CONTRACT CASES PASS'),
     ('M5 faulty notifiers (the contract suite must catch each)', 'run_m5_faults.py', [], 'ALL FAULTS CAUGHT'),
     ('M5 register checks', 'programme_check_m5.py', [], 'ALL M5 REGISTER CHECKS PASS'),
     ('M4 register checks on the extended tables', 'programme_check_m4.py', [], 'ALL M4 REGISTER CHECKS PASS'),
     ('M3 register checks on the extended tables', 'programme_check_m3.py', [], 'ALL M3 REGISTER CHECKS PASS'),
     ('M5 regression against the delivered M4 package (includes the M4, M3 and M2 regression tools)', 'run_regression_m5.py', [], 'REGRESSION OK')]
if '--with-earlier' in sys.argv:
    G.append(('The whole M4 wrapper (earlier milestones)', 'run_m4_all.py', [], 'ALL M4 CHECKS PASS'))
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
print('ALL M5 CHECKS PASS' if ok else 'SOME M5 CHECKS FAILED')
sys.exit(0 if ok else 1)
