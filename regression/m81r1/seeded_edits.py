#!/usr/bin/env python3
"""APG-M8.1-R1: five seeded bad edits on private copies, each expected to be caught by tools/run_regression_m81r1.py (R03 or R04).  Usage: python3 -I regression/m81r1/seeded_edits.py <package folder>"""
import os, shutil, subprocess, sys, tempfile
SRC = sys.argv[1]
def case(name, path, old, new, step):
    td = tempfile.mkdtemp(prefix='m81r1_seed_')
    root = os.path.join(td, 'APG_M81R1')
    shutil.copytree(SRC, root, ignore=shutil.ignore_patterns('logs'))
    p = os.path.join(root, path); s = open(p, encoding='utf-8').read()
    assert s.count(old) == 1, name
    open(p, 'w', encoding='utf-8').write(s.replace(old, new))
    r = subprocess.run([sys.executable, '-I', 'tools/run_regression_m81r1.py', '--step', step], cwd=root, capture_output=True, text=True)
    out = r.stdout.strip().splitlines()[0]
    caught = r.returncode != 0 and out.startswith('FAIL')
    print('%s %s: %s -> %s' % ('CAUGHT' if caught else 'MISSED', name, step, out[:300]))
    shutil.rmtree(td)
    return caught
res = [
 case('extra list entry', 'tests_m8/test_m8_boundary.py', "'regression/m81r1/', 'logs/m81r1/')", "'regression/m81r1/', 'logs/m81r1/', 'apg/')", 'R04'),
 case('removed list entry', 'tools/run_regression_m8.py', "'tools/make_m8r2_registers.py', 'tools/run_regression_m8r2.py', 'programme/CHANGE_RECORD_APG-M8R2.md'} | M81.M81_ADDED", "'tools/make_m8r2_registers.py', 'programme/CHANGE_RECORD_APG-M8R2.md'} | M81.M81_ADDED", 'R04'),
 case('code change outside the lists', 'tools/run_regression_m81.py', "    ok = not bad and not same and removed == sorted(M81_REMOVED) and len(m) == 1340\n", "    ok = not same and removed == sorted(M81_REMOVED) and len(m) == 1340\n", 'R04'),
 case('second milestone cell changed', 'programme/PROGRAMME_MILESTONES.csv', ',EDR-12,Not started', ',EDR-12,In this delivery', 'R03'),
 case('existing disposition row edited', 'programme/AUDIT_DISPOSITION_REGISTER.csv', 'AD-14,F-82', 'AD-14,F-83', 'R03'),
]
print('seeded %d  caught %d' % (len(res), sum(res)))
sys.exit(0 if all(res) else 1)
