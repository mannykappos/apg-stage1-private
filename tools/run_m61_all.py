#!/usr/bin/env python3
"""Runs every APG-M6.1 check except the long mutation runs, in named groups that each print the time they took.  Usage (from the package root):  python3 -I tools/run_m61_all.py
Exit 0 only if everything passes.  Covers: the new approval-binding tests; every M5 detection and finding test; the M5 wrapper; the M6 wrapper (which includes the M6 regression against M5 and the M3 to M6 register checks);
the M6.1 regression against the delivered M6 package; the M6.1 register checks; the probe.  Mutation runs (long, split by module):  python3 -I tools/m5_mutants.py --only FN --jobs 2  (then DT, RL, PF)."""
import os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = lambda label, f: ('M6.1 unit tests: ' + label, 'run_m2_tests.py', ['-q', f], 'failures 0  errors 0')
G = [T('approval binding (F-52)', 'test_det_approval_binding.py'), T('every M5 detection and finding test', 'test_det_*.py'),
     ('The approval-binding probe', 'probe_approval_binding.py', [], 'APPROVAL IS BOUND TO THE EVIDENCE'),
     ('The M5 wrapper', 'run_m5_all.py', [], 'ALL M5 CHECKS PASS'),
     ('The M6 wrapper (includes the M6 regression against M5)', 'run_m6_all.py', [], 'ALL M6 CHECKS PASS'),
     ('M6.1 register checks', 'programme_check_m61.py', ['.'], 'ALL M6.1 REGISTER CHECKS PASS'),
     ('M6.1 regression against the delivered M6 package', 'run_regression_m61.py', [], 'REGRESSION OK')]
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
        ok = False
        print(out[-1500:])
print(f'\n{time.time() - t_all:.0f}s in total')
print('ALL M6.1 CHECKS PASS' if ok else 'SOME M6.1 CHECKS FAILED')
sys.exit(0 if ok else 1)
