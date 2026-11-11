#!/usr/bin/env python3
"""Every APG-F67 check as a short numbered group.  The whole unit suite is split into parts whose test counts are given, so that a reviewer can add them up: groups 10 to 21
together are the whole suite (every MIE-1.1-R1 test, with the declared F-67 edits, and the 12 F-67 correction tests).  The mutation run and the sabotage run are longer and
are run in slices (RUN_COMMANDS.txt D, E).
Usage: python3 -I tools/run_f67_all.py --list | --group N | --range A-B
A group cut off by a time limit is incomplete, not a pass: run it again alone and report it as incomplete if it still does not finish.  Exit 0 only if every group run passed."""
import os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
T = 'tools/run_m2_tests.py'
OK = 'failures 0  errors 0'
GROUPS = [
    ('Static regression against the delivered MIE-1.1-R1 package (R01 to R05, R10, R11)', ['tools/run_regression_f67.py', '--static'], 'failed 0', None),
    ('The F-67 probe: every forged, appended, direct and swapped-proposer approval is refused or not counted; the owner\'s own approval is counted', ['tools/probe_f67.py'], 'F-67 IS CORRECTED', None),
    ('unit tests: the F-67 correction tests', [T, '-q', 'test_f67_policy_approval.py'], OK, 12),
    ('The earlier audit-findings probes still corrected (M7, M7.1, M7.2, MIE-1) (regression step R08)', ['tools/run_regression_f67.py', '--step', 'R08'], 'failed 0', None),
    ('The golden Builder Zero runs are unchanged (financial, detection, procurement, recommendations, MIE-1) (regression step R09)', ['tools/run_regression_f67.py', '--step', 'R09'], 'failed 0', None),
    ('The M2 store contracts', ['tools/run_contracts.py'], 'ALL CONTRACT CASES PASS', None),
    ('The M2 faulty implementations: each caught by the contract suite', ['tools/run_faults.py'], 'ALL FAULTS CAUGHT', None),
    ('The record-store guard contract (M7.3)', ['tools/run_guard_contract.py'], 'ALL GUARD CASES PASS', None),
    ('Mutation baseline (the unparsed modules pass every test the F-67 mutation run uses)', ['tools/f67_mutants.py', '--baseline'], 'BASELINE OK', None),
    ('whole suite, part 1 of 12: the API boundary tests (M9)', [T, '-q', 'test_api_*.py'], OK, 149),
    ('whole suite, part 2 of 12: detection and findings (M5, M6.1 to M6.5; three files edited for F-67)', [T, '-q', 'test_det_*.py'], OK, 605),
    ('whole suite, part 3 of 12: the financial core (M4; four files edited for F-67)', [T, '-q', 'test_fin_*.py'], OK, 340),
    ('whole suite, part 4 of 12: ingestion (M3)', [T, '-q', 'test_ingest_*.py'], OK, 224),
    ('whole suite, part 5 of 12: materials and market (M6; three files edited for F-67)', [T, '-q', 'test_mkt_*.py'], OK, 544),
    ('whole suite, part 6 of 12: recommendations (M7 to M7.3)', [T, '-q', 'test_rec_*.py'], OK, 216),
    ('whole suite, part 7 of 12: the materiality engine (M2)', [T, '-q', 'test_materiality_engine.py'], OK, 45),
    ('whole suite, part 8 of 12: golden, source authority, status model, tenancy, values (M2)', [T, '-q', 'test_[gstv]*.py'], OK, None),
    ('whole suite, part 9 of 12: the Builder Zero adversarial tests (M1)', [T, '-q', 'test_adversarial_builder_zero.py'], OK, None),
    ('whole suite, part 10 of 12: reproducibility (M2)', [T, '-q', 'test_repro.py'], OK, None),
    ('whole suite, part 11 of 12: MIE-1 and MIE-1.1 (one file edited for F-67)', [T, '-q', 'test_mie_*.py'], OK, 244),
    ('whole suite, part 12 of 12: the F-67 correction tests (group 3)', [T, '-q', 'test_f67_*.py'], OK, 12),
]
WHOLE = 2540                                                         # the whole unit suite: groups 10 to 21 add up to this (the MIE-1.1-R1 suite of 2,528 and the 12 F-67 tests)
FIRST, LAST = 10, 21

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
