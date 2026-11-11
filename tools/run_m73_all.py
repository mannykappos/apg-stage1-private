#!/usr/bin/env python3
"""Every M7.3 check as a short numbered group (none needs a long wrapper; the longest, the detection tests, takes under a minute).  The whole unit suite is split into parts whose test counts are
given, so that a reviewer can add them up: groups 13 to 22 together are the whole suite.  Usage: python3 -I tools/run_m73_all.py --list | --group N | --range A-B
A group cut off by a time limit is incomplete, not a pass: run it again alone and report it as incomplete if it still does not finish.  Exit 0 only if every group run passed."""
import os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
T = 'tools/run_m2_tests.py'
OK = 'failures 0  errors 0'
GROUPS = [
    ('The M7.2 audit insert-race probe (F-69: a new overlapping finding at each point the auditor named, at submission, approval and start)', ['tools/probe_m72_insert_race.py'], 'THE INSERT RACE IS CLOSED', None),
    ('The M7.1 audit race probe (F-68: an existing source changed after the check and before the commit)', ['tools/probe_m71_race.py'], 'THE RACE IS CLOSED', None),
    ('The M7 audit findings probe (F-64, F-65, F-66)', ['tools/probe_m7_audit_findings.py'], 'THE AUDIT FINDINGS ARE CORRECTED', None),
    ('The M7 guarantees probe', ['tools/probe_rec_m7.py'], 'THE M7 GUARANTEES HOLD', None),
    ('Static regression against the delivered M7.2 package (R01 to R08)', ['tools/run_regression_m73.py', '--static'], 'failed 0', None),
    ('The M2 port contracts on the changed reference store (38 cases)', ['tools/run_contracts.py'], 'ALL CONTRACT CASES PASS', None),
    ('The M2 faulty implementations are all still caught (39)', ['tools/run_faults.py'], 'ALL FAULTS CAUGHT', None),
    ('The record-store guard contract (RG-01 to RG-08)', ['tools/run_guard_contract.py'], 'ALL GUARD CASES PASS', None),
    ('unit tests: the M7.3 tests', [T, '-q', 'test_rec_m73_insert_race.py'], OK, 12),
    ('unit tests: the M7.2 race tests', [T, '-q', 'test_rec_m72_race.py'], OK, 18),
    ('unit tests: the M7.1 correction tests', [T, '-q', 'test_rec_m71_corrections.py'], OK, 23),
    ('The golden Builder Zero run with the independent oracle', [T, '-q', 'test_rec_golden.py'], OK, 4),
    ('whole suite, part 1 of 10: the API boundary tests (M9)', [T, '-q', 'test_api_*.py'], OK, 149),
    ('whole suite, part 2 of 10: detection and findings (M5, M6.1 to M6.5)', [T, '-q', 'test_det_*.py'], OK, 605),
    ('whole suite, part 3 of 10: the financial core (M4)', [T, '-q', 'test_fin_*.py'], OK, 340),
    ('whole suite, part 4 of 10: ingestion (M3)', [T, '-q', 'test_ingest_*.py'], OK, 224),
    ('whole suite, part 5 of 10: materials and market (M6)', [T, '-q', 'test_mkt_*.py'], OK, 544),
    ('whole suite, part 6 of 10: recommendations (M7 to M7.3, all fourteen files)', [T, '-q', 'test_rec_*.py'], OK, 216),
    ('whole suite, part 7 of 10: the materiality engine (M2)', [T, '-q', 'test_materiality_engine.py'], OK, 45),
    ('whole suite, part 8 of 10: golden, source authority, status model, tenancy, values (M2)', [T, '-q', 'test_[gstv]*.py'], OK, None),
    ('whole suite, part 9 of 10: the Builder Zero adversarial tests (M1)', [T, '-q', 'test_adversarial_builder_zero.py'], OK, None),
    ('whole suite, part 10 of 10: reproducibility (M2)', [T, '-q', 'test_repro.py'], OK, None),
    ('Mutation baseline (the unparsed modules pass every M7 to M7.3 test)', ['tools/m7_mutants.py', '--baseline'], 'BASELINE OK', None),
    ('Store mutation baseline (the unparsed store files pass the store tests)', ['tools/m73_store_mutants.py', '--baseline'], 'BASELINE OK', None),
]
WHOLE = 2284                                                         # the whole unit suite: groups 13 to 22 add up to this


def main():
    a = sys.argv[1:]
    if not a or a[0] == '--list':
        for i, (name, cmd, _, n) in enumerate(GROUPS, 1):
            print('%2d  %s%s    (python3 -I %s)' % (i, name, (' [%d tests]' % n) if n else '', ' '.join(cmd)))
        print('groups 13 to 22 together are the whole unit suite: %d tests' % WHOLE)
        return 0
    if a[0] == '--group':
        want = [int(a[1])]
    elif a[0] == '--range':
        lo, hi = (int(x) for x in a[1].split('-'))
        want = list(range(lo, hi + 1))
    else:
        print(__doc__)
        return 2
    bad, total = [], 0
    for n in want:
        name, cmd, expect, count = GROUPS[n - 1]
        r = subprocess.run([sys.executable, '-I'] + cmd, cwd=ROOT, capture_output=True, text=True, timeout=1800)
        out = r.stdout + r.stderr
        m = re.search(r'tests (\d+)  failures', out)
        ran = int(m.group(1)) if m else None
        ok = r.returncode == 0 and expect in out and (count is None or ran == count)
        if 13 <= n <= 22 and ran:
            total += ran
        print('%s group %d: %s | %s' % ('PASS' if ok else 'FAIL', n, name, ('tests %d' % ran) if ran is not None else (out.strip().splitlines() or [''])[-1]))
        if not ok:
            bad.append(n)
    if set(range(13, 23)) <= set(want):
        print('whole suite: %d tests in groups 13 to 22 (expected %d)%s' % (total, WHOLE, '' if total == WHOLE else '  MISMATCH'))
        if total != WHOLE:
            bad.append('whole-suite count')
    print('groups %d  failed %d%s' % (len(want), len(bad), ('  FAILED: %r' % bad) if bad else ''))
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
