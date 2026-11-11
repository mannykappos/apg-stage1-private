#!/usr/bin/env python3
"""APG-M10: five seeded bad edits on private copies, each expected to be caught by tools/run_regression_m10.py (R03 or R04).  Usage: python3 -I regression/m10/seeded_edits.py <package folder>"""
import os, shutil, subprocess, sys, tempfile
SRC = sys.argv[1]


def case(name, path, old, new, step):
    td = tempfile.mkdtemp(prefix='m10_seed_')
    root = os.path.join(td, 'APG_M10')
    shutil.copytree(SRC, root, ignore=shutil.ignore_patterns('logs', '__pycache__', 'ui', 'ui_tests', 'builder_zero', 'research', 'regression'))
    shutil.copytree(os.path.join(SRC, 'regression', 'm10'), os.path.join(root, 'regression', 'm10'))
    p = os.path.join(root, path)
    s = open(p, encoding='utf-8').read()
    assert s.count(old) == 1, name
    open(p, 'w', encoding='utf-8').write(s.replace(old, new))
    r = subprocess.run([sys.executable, '-I', 'tools/run_regression_m10.py', '--step', step], cwd=root, capture_output=True, text=True)
    out = r.stdout.strip().splitlines()[0]
    caught = r.returncode != 0 and out.startswith('FAIL')
    print('%s %s: %s -> %s' % ('CAUGHT' if caught else 'MISSED', name, step, out[:300]))
    shutil.rmtree(td)
    return caught


res = [
    case('extra list entry', 'tests_m8/test_m8_boundary.py', "'regression/m10/', 'logs/m10/')", "'regression/m10/', 'logs/m10/', 'apg/')", 'R04'),
    case('removed list entry', 'tools/run_regression_m81.py', "M81R1_ADDED = {'tools/make_m81r1_registers.py', 'tools/run_regression_m81r1.py',", "M81R1_ADDED = {'tools/make_m81r1_registers.py',", 'R04'),
    case('code change outside the lists', 'tools/run_regression_m8.py', "    return (not bad and not same and len(m) == 1222,", "    return (not same and len(m) == 1222,", 'R04'),
    case('second milestone cell changed', 'programme/PROGRAMME_MILESTONES.csv', ',EDR-13; EDR-17,Not started', ',EDR-13; EDR-17,In this delivery', 'R03'),
    case('existing status row edited', 'programme/STATUS_REGISTER.csv', 'SR-127,"M8.1:', 'SR-127,"M8.1 (edited):', 'R03'),
]
print('seeded %d  caught %d' % (len(res), sum(res)))
sys.exit(0 if all(res) else 1)
