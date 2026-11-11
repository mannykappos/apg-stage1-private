#!/usr/bin/env python3
"""Every M7 check as a short numbered group, so that no command needs a long wrapper.  Usage: python3 -I tools/run_m7_all.py --list | --group N | --range A-B
A group cut off by a time limit is incomplete, not a pass: run it again alone and report it as incomplete if it still does not finish.  Exit 0 only if every group run passed."""
import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
T = 'tools/run_m2_tests.py'
GROUPS = [
    ('The M7 guarantees probe', ['tools/probe_rec_m7.py'], 'THE M7 GUARANTEES HOLD'),
    ('Static regression against the delivered M9.4 package (R01 to R08)', ['tools/run_regression_m7.py', '--static'], 'failed 0'),
    ('unit tests: recommendation policy', [T, '-q', 'test_rec_policy.py'], 'failures 0  errors 0'),
    ('unit tests: eligibility gates', [T, '-q', 'test_rec_eligibility.py'], 'failures 0  errors 0'),
    ('unit tests: explainable ranking', [T, '-q', 'test_rec_ranking.py'], 'failures 0  errors 0'),
    ('unit tests: net benefit and overlap', [T, '-q', 'test_rec_money.py'], 'failures 0  errors 0'),
    ('unit tests: constraints, authority and scenarios', [T, '-q', 'test_rec_constraints.py'], 'failures 0  errors 0'),
    ('unit tests: lifecycle and approval binding', [T, '-q', 'test_rec_lifecycle.py'], 'failures 0  errors 0'),
    ('unit tests: the realised-benefit verification gate', [T, '-q', 'test_rec_verify.py'], 'failures 0  errors 0'),
    ('unit tests: reproducibility and reconstruction', [T, '-q', 'test_rec_repro.py'], 'failures 0  errors 0'),
    ('unit tests: scenario isolation and the action boundary', [T, '-q', 'test_rec_isolation.py'], 'failures 0  errors 0'),
    ('unit tests: boundaries, displayed values, concurrency and record details', [T, '-q', 'test_rec_edges.py'], 'failures 0  errors 0'),
    ('unit tests: golden Builder Zero run with the independent oracle', [T, '-q', 'test_rec_golden.py'], 'failures 0  errors 0'),
    ('The whole unit suite (every earlier test unchanged, plus M7; about two minutes)', [T, '-q'], 'failures 0  errors 0'),
    ('Mutation baseline (the unparsed modules pass every M7 test)', ['tools/m7_mutants.py', '--baseline'], 'BASELINE OK'),
]


def main():
    a = sys.argv[1:]
    if not a or a[0] == '--list':
        for i, (name, cmd, _) in enumerate(GROUPS, 1):
            print('%2d  %s    (python3 -I %s)' % (i, name, ' '.join(cmd)))
        return 0
    if a[0] == '--group':
        want = [int(a[1])]
    elif a[0] == '--range':
        lo, hi = (int(x) for x in a[1].split('-'))
        want = list(range(lo, hi + 1))
    else:
        print(__doc__)
        return 2
    bad = []
    for n in want:
        name, cmd, expect = GROUPS[n - 1]
        r = subprocess.run([sys.executable, '-I'] + cmd, cwd=ROOT, capture_output=True, text=True, timeout=1800)
        out = r.stdout + r.stderr
        ok = r.returncode == 0 and expect in out
        print('%s group %d: %s | %s' % ('PASS' if ok else 'FAIL', n, name, (out.strip().splitlines() or [''])[-1]))
        if not ok:
            bad.append(n)
    print('groups %d  failed %d%s' % (len(want), len(bad), ('  FAILED: %r' % bad) if bad else ''))
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
