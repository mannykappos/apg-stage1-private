#!/usr/bin/env python3
"""Runs every APG-M6.4 check except the long mutation runs, in named groups that each print the time they took.  Usage (from the package root):  python3 -I tools/run_m64_all.py
Exit 0 only if everything passes.  Covers: the proposal-identity tests (F-56), the version-types tests (F-55), the proposal-binding and approval-binding tests; every M5 detection and finding test; the three probes; the M5 wrapper; the M6 wrapper (which includes
the M6 regression against M5 and the M3 to M6 register checks); the M6.2 and M6.3 register checks and regressions; the M6.4 register checks and regression against the delivered M6.3 package.
It takes several minutes; if it is cut off by a time limit, that is an incomplete run, not a pass: run the groups separately instead.  Mutation runs (long, split by module):  python3 -I tools/m5_mutants.py --only FN --jobs 2  (then DT, RL, PF)."""
import os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = lambda label, f: ('M6.4 unit tests: ' + label, 'run_m2_tests.py', ['-q', f], 'failures 0  errors 0')
G = [T('proposal identity (F-56)', 'test_det_proposal_identity.py'), T('version types (F-55)', 'test_det_version_types.py'), T('proposal binding (F-53, F-54)', 'test_det_proposal_binding.py'), T('approval binding (F-52)', 'test_det_approval_binding.py'), T('every M5 detection and finding test', 'test_det_*.py'),
     ('The proposal-swap probe', 'probe_proposal_swap.py', [], 'APPROVAL IS BOUND TO THE EXACT PROPOSAL'),
     ('The malformed-version probe', 'probe_malformed_proposal_version.py', [], 'MALFORMED VERSIONS ARE REFUSED'),
     ('The stale-proposal probe', 'probe_stale_proposal.py', [], 'PROPOSAL IS BOUND TO THE EVIDENCE'),
     ('The approval-binding probe', 'probe_approval_binding.py', [], 'APPROVAL IS BOUND TO THE EVIDENCE'),
     ('The M5 wrapper', 'run_m5_all.py', [], 'ALL M5 CHECKS PASS'),
     ('The M6 wrapper (includes the M6 regression against M5)', 'run_m6_all.py', [], 'ALL M6 CHECKS PASS'),
     ('M6.2 register checks', 'programme_check_m62.py', ['.'], 'ALL M6.2 REGISTER CHECKS PASS'),
     ('M6.2 regression against the delivered M6 package', 'run_regression_m62.py', [], 'REGRESSION OK'),
     ('M6.3 register checks', 'programme_check_m63.py', ['.'], 'ALL M6.3 REGISTER CHECKS PASS'),
     ('M6.3 regression against the delivered M6.2 package', 'run_regression_m63.py', [], 'REGRESSION OK'),
     ('M6.4 register checks', 'programme_check_m64.py', ['.'], 'ALL M6.4 REGISTER CHECKS PASS'),
     ('M6.4 regression against the delivered M6.3 package', 'run_regression_m64.py', [], 'REGRESSION OK')]
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
print('ALL M6.4 CHECKS PASS' if ok else 'SOME M6.4 CHECKS FAILED')
sys.exit(0 if ok else 1)
