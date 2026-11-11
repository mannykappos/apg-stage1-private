#!/usr/bin/env python3
"""APG-M8 verification in small, separately runnable groups, so that a reviewer can run each one alone and add the counts up.  ONE TEST FILE PER GROUP throughout:
  the AUIF dependency and configuration checks; each of the 15 M8 test files (14 from M8, one from M8-R1); the unchanged M3 import tests; each of the 117 existing APG test files (through the
  APG-F67.4 per-file runner, unchanged); the nine regression steps against APG-F67.4-R2; and (M8-R1) step R10 against the delivered APG-M8.
Mutation (tools/m8_mutants.py --batch K/4) and sabotage (tools/sabotage_m8.py --only ID) are run separately: they are longer.
A group cut off by the time limit is INCOMPLETE: neither a pass nor a failure.
Usage: python3 -I tools/run_m8_all.py --list | --group N | --range A-B [--timeout SECONDS]"""
import os, re, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import run_m8_tests as RT                                          # noqa: E402
import run_f674_all as F                                           # noqa: E402


def groups():
    g = [('AUIF dependency (rev14 from APG-M8.1): ZIP hash, fresh extraction, manifest and core tree (regression R06)', ['tools/run_regression_m8.py', '--step', 'R06'], 'checks 1  failed 0'),
         ('configuration: stored definitions, model and packs equal the generator (regression R07)', ['tools/run_regression_m8.py', '--step', 'R07'], 'checks 1  failed 0')]
    for f in sorted(RT.EXPECTED):
        g.append(('M8 test file %s (%d tests)' % (f, RT.EXPECTED[f]), ['tools/run_m8_tests.py', '--file', f], 'failed files 0'))
    g.append(('M3 import tests, unchanged (224)', ['tools/run_m2_tests.py', '-q', 'test_ingest_*.py'], 'tests 224  failures 0  errors 0'))
    for i, (name, n) in enumerate(F.PER_FILE, 1):
        g.append(('existing APG test file %d: %s (%d tests)' % (i, name, n), ['tools/run_f674_all.py', '--file', str(i)], 'files 1  failed 0'))
    for k in ('R01', 'R02', 'R03', 'R04', 'R05', 'R08', 'R09'):
        g.append(('regression %s against APG-F67.4-R2' % k, ['tools/run_regression_m8.py', '--step', k], 'checks 1  failed 0'))
    g.append(('regression R10 against the delivered APG-M8 (M8-R1)', ['tools/run_regression_m8.py', '--step', 'R10'], 'checks 1  failed 0'))
    for k in ('R01', 'R02', 'R03', 'R04', 'R05', 'R06', 'R07'):
        g.append(('regression %s of APG-M8.1 against the delivered APG-M8-R2' % k, ['tools/run_regression_m81.py', '--step', k], 'checks 1  failed 0'))
    return g


def main():
    a = sys.argv[1:]
    G = groups()
    if not a or a[0] == '--list':
        for i, (name, cmd, _) in enumerate(G, 1):
            print('%3d  %s\n      python3 -I %s' % (i, name, ' '.join(cmd)))
        print('%d groups; M8 tests %d in %d files; existing APG tests %d in %d files' % (len(G), sum(RT.EXPECTED.values()), len(RT.EXPECTED), sum(n for _, n in F.PER_FILE), len(F.PER_FILE)))
        return 0
    timeout = int(a[a.index('--timeout') + 1]) if '--timeout' in a else 3600
    if a[0] == '--group':
        sel = [int(a[1])]
    else:
        lo, hi = map(int, a[1].split('-'))
        sel = list(range(lo, hi + 1))
    bad, inc = [], []
    for i in sel:
        name, cmd, expect = G[i - 1]
        t = time.time()
        try:
            r = subprocess.run([sys.executable, '-I'] + cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            ok = r.returncode == 0 and expect in r.stdout + r.stderr
            st = 'PASS' if ok else 'FAIL'
            tail = (r.stdout + r.stderr).strip().splitlines()[-1:] if not ok else []
        except subprocess.TimeoutExpired:
            st, tail = 'INCOMPLETE', ['cut off by the time limit: neither a pass nor a failure']
        (bad if st == 'FAIL' else inc if st == 'INCOMPLETE' else []).append(i)
        print('%s group %d: %s  %.1fs %s' % (st, i, name, time.time() - t, tail), flush=True)
    print('groups %d  failed %d  incomplete %d' % (len(sel), len(bad), len(inc)) + (' FAILED %s' % bad if bad else '') + (' INCOMPLETE %s' % inc if inc else ''))
    return 0 if not bad and not inc else 1


if __name__ == '__main__':
    sys.exit(main())
