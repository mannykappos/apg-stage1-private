#!/usr/bin/env python3
"""Runs every APG-M9.4 check except the long mutation runs, in numbered groups that each print the time they took.
Usage (from the package root):   python3 -I tools/run_m94_all.py                 (all groups; several minutes)
                                  python3 -I tools/run_m94_all.py --list          (print the groups)
                                  python3 -I tools/run_m94_all.py --group N       (run only group N; N as printed by --list)
                                  python3 -I tools/run_m94_all.py --range A-B     (run groups A to B)
Exit 0 only if everything run passes.  If a time limit cuts a run off, that is an incomplete run, not a pass: run the groups one at a time instead (RUN_COMMANDS.txt lists them).
The mutation run (long):  python3 -I tools/m91_mutants.py --jobs 2   or in chunks of ten with --ids (RUN_COMMANDS.txt)."""
import os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = lambda label, f: ('unit tests: ' + label, 'run_m2_tests.py', ['-q', f], 'failures 0  errors 0')


def comps(fn, prefix):
    """The groups of an earlier, unchanged wrapper (run_m5_all.py, run_m6_all.py), listed one by one so that each can be run on its own: the auditor's runs of those wrappers as a whole did not complete within the time limit (CF-28, CF-30)."""
    path = os.path.join(ROOT, 'tools', fn)
    ns = {'__file__': path}
    exec(compile(open(path, encoding='utf-8').read().split("if '--with-earlier'")[0], fn, 'exec'), ns)          # the part of the file that defines its list of groups; nothing is run
    return [(prefix + n, tool, args, marker) for (n, tool, args, marker) in ns['G']]

G = [('The clock-failure probe (F-63)', 'probe_m93_clock_failure.py', [], 'THE CLOCK FAILURE IS HANDLED SAFELY'),
     ('The session-expiry probe (F-62)', 'probe_m92_session_expiry.py', [], 'THE SESSION EXPIRY CHECK IS CORRECTED'),
     T('the M9.4 correction tests', 'test_api_m94_corrections.py'), T('the M9.3 correction tests', 'test_api_m93_corrections.py'), T('the M9.2 correction tests', 'test_api_m92_corrections.py'),
     T('the approval request boundary (M9.1 tests, unchanged)', 'test_api_approval_boundary.py'), T('the ProjectActionPort contract (EDR-31)', 'test_api_action_port_contract.py'), T('static rules for apg/api', 'test_api_static.py'),
     ('The M9.2 audit-findings probe', 'probe_m91_audit_findings.py', [], 'THE AUDIT FINDINGS ARE CORRECTED'),
     ('The ProjectActionPort contract suite and its faulty ports', 'run_m91_contracts.py', [], 'ALL CONTRACT CASES PASS'),
     ('The approval-boundary probe', 'probe_approval_boundary.py', [], 'THE BOUNDARY BEHAVES AS THE CONTRACT SAYS'),
     T('every M5 detection and finding test', 'test_det_*.py'),
     ('The transition-bypass probe', 'probe_transition_bypass.py', [], 'every incomplete approval is refused at transition'),
     ('The proposal-swap probe', 'probe_proposal_swap.py', [], 'APPROVAL IS BOUND TO THE EXACT PROPOSAL'),
     ('The malformed-version probe', 'probe_malformed_proposal_version.py', [], 'MALFORMED VERSIONS ARE REFUSED'),
     ('The stale-proposal probe', 'probe_stale_proposal.py', [], 'PROPOSAL IS BOUND TO THE EVIDENCE'),
     ('The approval-binding probe', 'probe_approval_binding.py', [], 'APPROVAL IS BOUND TO THE EVIDENCE'),
     *comps('run_m5_all.py', 'M5 wrapper, one group: '), *comps('run_m6_all.py', 'M6 wrapper, one group: '),
     ('M6.2 register checks', 'programme_check_m62.py', ['.'], 'ALL M6.2 REGISTER CHECKS PASS'), ('M6.2 regression against the delivered M6 package', 'run_regression_m62.py', [], 'REGRESSION OK'),
     ('M6.3 register checks', 'programme_check_m63.py', ['.'], 'ALL M6.3 REGISTER CHECKS PASS'), ('M6.3 regression against the delivered M6.2 package', 'run_regression_m63.py', [], 'REGRESSION OK'),
     ('M6.4 register checks', 'programme_check_m64.py', ['.'], 'ALL M6.4 REGISTER CHECKS PASS'), ('M6.4 regression against the delivered M6.3 package', 'run_regression_m64.py', [], 'REGRESSION OK'),
     ('M6.5 register checks', 'programme_check_m65.py', ['.'], 'ALL M6.5 REGISTER CHECKS PASS'), ('M6.5 regression against the delivered M6.4 package', 'run_regression_m65.py', [], 'REGRESSION OK'),
     ('M9.1 register checks', 'programme_check_m91.py', ['.'], 'ALL M9.1 REGISTER CHECKS PASS'), ('M9.1 regression against the delivered M6.5 package', 'run_regression_m91.py', [], 'REGRESSION OK'),
     ('M9.2 register checks', 'programme_check_m92.py', ['.'], 'ALL M9.2 REGISTER CHECKS PASS'), ('M9.2 regression against the delivered M9.1 package (file and table checks)', 'run_regression_m92.py', ['--static'], 'STATIC CHECKS OK'),
     ('M9.3 register checks', 'programme_check_m93.py', ['.'], 'ALL M9.3 REGISTER CHECKS PASS'), ('M9.3 regression against the delivered M9.2 package (file and table checks)', 'run_regression_m93.py', ['--static'], 'STATIC CHECKS OK'),
     ('M9.4 register checks', 'programme_check_m94.py', ['.'], 'ALL M9.4 REGISTER CHECKS PASS'),
     ('M9.4 regression against the delivered M9.3 package (file and table checks; the other steps of that tool are the groups above, or run it whole: python3 -I tools/run_regression_m94.py)', 'run_regression_m94.py', ['--static'], 'STATIC CHECKS OK')]
if '--list' in sys.argv:
    for i, (name, tool, args, marker) in enumerate(G, 1):
        print(f'group {i:2d}: {name}   [python3 -I tools/{tool} {" ".join(args)}]')
    sys.exit(0)
only = None
lo, hi = 1, len(G)
if '--group' in sys.argv:
    only = int(sys.argv[sys.argv.index('--group') + 1])
    assert 1 <= only <= len(G), f'group must be 1 to {len(G)}'
if '--range' in sys.argv:                                   # --range A-B runs groups A to B
    lo, hi = (int(x) for x in sys.argv[sys.argv.index('--range') + 1].split('-'))
    assert 1 <= lo <= hi <= len(G), f'range must lie within 1 to {len(G)}'
ok = True
t_all = time.time()
for i, (name, tool, args, marker) in enumerate(G, 1):
    if (only and i != only) or not (lo <= i <= hi):
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
print(('ALL M9.4 CHECKS PASS' if ok else 'SOME M9.4 CHECKS FAILED') + (f' (group {only} only)' if only else (f' (groups {lo} to {hi} only)' if (lo, hi) != (1, len(G)) else '')))
sys.exit(0 if ok else 1)
