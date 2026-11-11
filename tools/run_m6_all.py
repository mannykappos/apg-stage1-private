#!/usr/bin/env python3
"""Runs every M6 check except the long mutation run, in named groups that each print the time they took and can be run on their own (see RUN_COMMANDS.txt).
Usage (from the package root):  python3 -I tools/run_m6_all.py [--with-earlier]      Exit 0 only if everything passes.
Without --with-earlier the earlier milestones are covered by the M6 regression step (frozen M0 to M5 files by hash, M2 to M5 golden cases and demonstrations).  --with-earlier also
runs the whole M5 wrapper, which takes longer.   Mutation runs (long, split by module with --only):  python3 -I tools/m6_mutants.py --jobs 2   (then m5_mutants.py --only DT/FN/RL/PF for the four M5 modules M6 changed, and the earlier m4/m3/m2 tools, unchanged)"""
import os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = lambda label, f: ('M6 unit tests: ' + label, 'run_m2_tests.py', ['-q', f], 'failures 0  errors 0')
G = [T('policy and specification register (versioned, two-person, no defaults)', 'test_mkt_policy.py'), T('specification register', 'test_mkt_spec.py'), T('intake (quotes, orders, deliveries, materials, readings, FX and index series)', 'test_mkt_intake.py'),
     T('foreign exchange and freshness gates', 'test_mkt_fx_fresh.py'), T('landed cost', 'test_mkt_landed.py'), T('comparability and ranking', 'test_mkt_compare.py'), T('demand coverage, over-ordering, duplicates', 'test_mkt_demand.py'),
     T('scenarios (buy now, wait, stage, negotiate)', 'test_mkt_scenarios.py'), T('opportunities, supplier performance, portfolio purchasing', 'test_mkt_opportunities.py'), T('rules MP01 to MP10 and MPD1', 'test_mkt_rules.py'),
     T('signals, runs, events and the reproducible formulas', 'test_mkt_detect.py'), T('edge cases: shared views, gathering, FX, freshness, import checks (written to kill mutation survivors)', 'test_mkt_edges_base.py'), T('edge cases: policy validators, specification gate', 'test_mkt_edges_policy.py'),
     T('edge cases: landed cost, comparability application, scenarios', 'test_mkt_edges_landed.py'), T('edge cases: demand, opportunities, portfolio, supplier performance', 'test_mkt_edges_demand.py'),
     T('edge cases: rules, analysis, runs, events', 'test_mkt_edges_rules.py'), T('port contract suites and faulty implementations', 'test_mkt_contracts.py'), T('static source rules', 'test_mkt_static.py'),
     T('faulty-input corpus', 'test_mkt_corpus.py'), T('golden cases', 'test_mkt_golden.py'),
     ('M6 golden Builder Zero cases with the independent oracle', 'run_golden_mkt.py', [], 'GOLDEN OK'),
     ('M6 faulty-input corpus through intake and the procurement rules', 'run_mkt_corpus.py', [], 'ALL CORPUS CASES PASS'),
     ('M6 ExtractionRuntimePort and MarketFeedPort contract suites against the in-memory references', 'run_m6_contracts.py', [], 'ALL CONTRACT CASES PASS'),
     ('M6 faulty feeds and extractors (the contract suites must catch each)', 'run_m6_faults.py', [], 'ALL FAULTS CAUGHT'),
     ('M6 narrated demonstration (compared with the saved output)', 'run_demo_m6.py', ['--check'], 'DEMO OUTPUT MATCHES'),
     ('M6 register checks', 'programme_check_m6.py', ['.'], 'ALL M6 REGISTER CHECKS PASS'),
     ('M5 register checks on the extended tables', 'programme_check_m5.py', ['.'], 'ALL M5 REGISTER CHECKS PASS'),
     ('M4 register checks on the extended tables', 'programme_check_m4.py', ['.'], 'ALL M4 REGISTER CHECKS PASS'),
     ('M3 register checks on the extended tables', 'programme_check_m3.py', ['.'], 'ALL M3 REGISTER CHECKS PASS'),
     ('M6 regression against the delivered M5 package (includes the M5, M4, M3 and M2 regression tools)', 'run_regression_m6.py', [], 'REGRESSION OK')]
if '--with-earlier' in sys.argv:
    G.append(('The whole M5 wrapper (earlier milestones)', 'run_m5_all.py', [], 'ALL M5 CHECKS PASS'))
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
print('ALL M6 CHECKS PASS' if ok else 'SOME M6 CHECKS FAILED')
sys.exit(0 if ok else 1)
