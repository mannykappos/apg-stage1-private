#!/usr/bin/env python3
"""Runs every APG-M9.2 check except the long mutation runs, in numbered groups that each print the time they took.
Usage (from the package root):   python3 -I tools/run_m92_all.py                 (all groups; several minutes)
                                  python3 -I tools/run_m92_all.py --list          (print the groups)
                                  python3 -I tools/run_m92_all.py --group N       (run only group N; N as printed by --list)
Exit 0 only if everything run passes.  If a time limit cuts a run off, that is an incomplete run, not a pass: run the groups one at a time instead (RUN_COMMANDS.txt lists them).
The mutation run (long):  python3 -I tools/m91_mutants.py --jobs 2   or in chunks of ten with --ids (RUN_COMMANDS.txt)."""
import os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = lambda label, f: ('unit tests: ' + label, 'run_m2_tests.py', ['-q', f], 'failures 0  errors 0')
G = [('The audit-findings probe (F-58 to F-61 and the audit consistency)', 'probe_m91_audit_findings.py', [], 'THE AUDIT FINDINGS ARE CORRECTED'),
     T('the M9.2 correction tests', 'test_api_m92_corrections.py'),
     T('the approval request boundary (M9.1 tests, unchanged)', 'test_api_approval_boundary.py'), T('the ProjectActionPort contract (EDR-31)', 'test_api_action_port_contract.py'), T('static rules for apg/api', 'test_api_static.py'),
     ('The ProjectActionPort contract suite and its faulty ports', 'run_m91_contracts.py', [], 'ALL CONTRACT CASES PASS'),
     ('The approval-boundary probe', 'probe_approval_boundary.py', [], 'THE BOUNDARY BEHAVES AS THE CONTRACT SAYS'),
     T('every M5 detection and finding test', 'test_det_*.py'),
     ('The transition-bypass probe', 'probe_transition_bypass.py', [], 'every incomplete approval is refused at transition'),
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
     ('M6.4 regression against the delivered M6.3 package', 'run_regression_m64.py', [], 'REGRESSION OK'),
     ('M6.5 register checks', 'programme_check_m65.py', ['.'], 'ALL M6.5 REGISTER CHECKS PASS'),
     ('M6.5 regression against the delivered M6.4 package', 'run_regression_m65.py', [], 'REGRESSION OK'),
     ('M9.1 register checks', 'programme_check_m91.py', ['.'], 'ALL M9.1 REGISTER CHECKS PASS'),
     ('M9.1 regression against the delivered M6.5 package', 'run_regression_m91.py', [], 'REGRESSION OK'),
     ('M9.2 register checks', 'programme_check_m92.py', ['.'], 'ALL M9.2 REGISTER CHECKS PASS'),
     ('M9.2 regression against the delivered M9.1 package (file and table checks; the other steps of that tool are the groups above, or run it whole: python3 -I tools/run_regression_m92.py)', 'run_regression_m92.py', ['--static'], 'STATIC CHECKS OK')]
if '--list' in sys.argv:
    for i, (name, tool, args, marker) in enumerate(G, 1):
        print(f'group {i:2d}: {name}   [python3 -I tools/{tool} {" ".join(args)}]')
    sys.exit(0)
only = None
if '--group' in sys.argv:
    only = int(sys.argv[sys.argv.index('--group') + 1])
    assert 1 <= only <= len(G), f'group must be 1 to {len(G)}'
ok = True
t_all = time.time()
for i, (name, tool, args, marker) in enumerate(G, 1):
    if only and i != only:
        continue
    t0 = time.time()
    r = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', tool), *args], capture_output=True, text=True, cwd=ROOT)
    out = r.stdout + r.stderr
    good = r.returncode == 0 and marker in out
    last = [l for l in out.strip().splitlines() if l.strip()][-1:] or ['']
    print(('PASS ' if good else 'FAIL ') + f'[{i}] ' + name + f'  ({time.time() - t0:.0f}s)  [' + last[0].strip()[:100] + ']', flush=True)
    if not good:
        ok = False
        print(out[-1500:])
print(f'\n{time.time() - t_all:.0f}s in total')
print(('ALL M9.2 CHECKS PASS' if ok else 'SOME M9.2 CHECKS FAILED') + (f' (group {only} only)' if only else ''))
sys.exit(0 if ok else 1)
