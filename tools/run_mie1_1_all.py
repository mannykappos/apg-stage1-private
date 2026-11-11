#!/usr/bin/env python3
"""Every MIE-1.1 check as a short numbered group.  The whole unit suite is split into parts whose test counts are given, so that a reviewer can add them up: groups 9 to 19
together are the whole suite (every M2 to M7.3 test, unchanged, and the MIE-1 and MIE-1.1 tests).  The mutation run and the sabotage run are longer and are run in slices (RUN_COMMANDS.txt D, E).
Usage: python3 -I tools/run_mie1_1_all.py --list | --group N | --range A-B
A group cut off by a time limit is incomplete, not a pass: run it again alone and report it as incomplete if it still does not finish.  Exit 0 only if every group run passed."""
import os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
T = 'tools/run_m2_tests.py'
OK = 'failures 0  errors 0'
GROUPS = [
    ('Static regression against the delivered MIE-1 package (R01 to R08, R13, R14 the audit-findings probe)', ['tools/run_regression_mie1_1.py', '--static'], 'failed 0', None),
    ('Static checks of the core: neutrality, imports, field names, operations, clock, feed calls, isolation gate (NE-01 to NE-06, FL-01, IG-01, IG-05)', ['tools/mie_static.py'], 'static checks 8  failed 0', None),
    ('Coverage: every one of the 175 planned cases accounted for (QA-02)', ['tools/mie_coverage.py'], 'EVERY PLANNED CASE IS ACCOUNTED FOR', None),
    ('MIE tests: the core, synthetic pack only (thirteen files, with the MIE-1.1 correction tests)', [T, '-q', 'test_mie_core_*.py'], OK, 210),
    ('MIE tests: the observation-feed flow and portability', [T, '-q', 'test_mie_[fp]*.py'], OK, 11),
    ('MIE tests: the construction pack, the M6 mapping and feed, isolation, golden (Builder Zero)', [T, '-q', 'test_mie_construction.py'], OK, 23),
    ('The golden Builder Zero MIE-1 run equals regression/mie1/golden_mie1.json', ['tools/run_golden_mie1.py'], 'THE GOLDEN MIE-1 RUN EQUALS THE RECORDED ANSWER', None),
    ('Mutation baseline (the unparsed core modules pass every MIE core test)', ['tools/mie11_mutants.py', '--baseline'], 'BASELINE OK', None),
    ('whole suite, part 1 of 11: the API boundary tests (M9)', [T, '-q', 'test_api_*.py'], OK, 149),
    ('whole suite, part 2 of 11: detection and findings (M5, M6.1 to M6.5)', [T, '-q', 'test_det_*.py'], OK, 605),
    ('whole suite, part 3 of 11: the financial core (M4)', [T, '-q', 'test_fin_*.py'], OK, 340),
    ('whole suite, part 4 of 11: ingestion (M3)', [T, '-q', 'test_ingest_*.py'], OK, 224),
    ('whole suite, part 5 of 11: materials and market (M6)', [T, '-q', 'test_mkt_*.py'], OK, 544),
    ('whole suite, part 6 of 11: recommendations (M7 to M7.3)', [T, '-q', 'test_rec_*.py'], OK, 216),
    ('whole suite, part 7 of 11: the materiality engine (M2)', [T, '-q', 'test_materiality_engine.py'], OK, 45),
    ('whole suite, part 8 of 11: golden, source authority, status model, tenancy, values (M2)', [T, '-q', 'test_[gstv]*.py'], OK, None),
    ('whole suite, part 9 of 11: the Builder Zero adversarial tests (M1)', [T, '-q', 'test_adversarial_builder_zero.py'], OK, None),
    ('whole suite, part 10 of 11: reproducibility (M2)', [T, '-q', 'test_repro.py'], OK, None),
    ('whole suite, part 11 of 11: MIE-1 and MIE-1.1 (groups 4 to 6 together)', [T, '-q', 'test_mie_*.py'], OK, 244),
]
WHOLE = 2528                                                         # the whole unit suite: groups 9 to 19 add up to this (the M7.3 suite of 2,284 and the 244 MIE tests)
FIRST, LAST = 9, 19


def main():
    a = sys.argv[1:]
    if not a or a[0] == '--list':
        for i, (name, cmd, _, n) in enumerate(GROUPS, 1):
            print('%2d  %s%s    (python3 -I %s)' % (i, name, (' [%d tests]' % n) if n else '', ' '.join(cmd)))
        print('groups %d to %d together are the whole unit suite: %d tests' % (FIRST, LAST, WHOLE))
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
        r = subprocess.run([sys.executable, '-I'] + cmd, cwd=ROOT, capture_output=True, text=True, timeout=3600)
        out = r.stdout + r.stderr
        m = re.search(r'tests (\d+)  failures', out)
        ran = int(m.group(1)) if m else None
        ok = r.returncode == 0 and expect in out and (count is None or ran == count)
        if FIRST <= n <= LAST and ran:
            total += ran
        print('%s group %d: %s | %s' % ('PASS' if ok else 'FAIL', n, name, ('tests %d' % ran) if ran is not None else (out.strip().splitlines() or [''])[-1]), flush=True)
        if not ok:
            bad.append(n)
    if set(range(FIRST, LAST + 1)) <= set(want):
        print('whole suite: %d tests in groups %d to %d (expected %d)%s' % (total, FIRST, LAST, WHOLE, '' if total == WHOLE else '  MISMATCH'))
        if total != WHOLE:
            bad.append('whole-suite count')
    print('groups %d  failed %d%s' % (len(want), len(bad), ('  FAILED: %r' % bad) if bad else ''))
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
