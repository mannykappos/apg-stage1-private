#!/usr/bin/env python3
"""Builder tool: check the M8 mutation log of a run set with the frozen tree's own evkit.check_output, and print its CONTROL lines,
its summary and RESULT lines, the MUTANT counts by verdict and the EQUIVALENT ids.  The RESULT line (v=3) is read through the frozen
tree's check_output, not parsed by this tool (amendment 5, discrepancy 21: documentation only).
Usage: python3 -I -S check_m8_log_s1.py RUN_DIR      BUILDER-EXECUTED: NOT INDEPENDENT."""
import collections, csv, os, re, sys
d = sys.argv[1]
sys.path.insert(0, os.path.join(d, 'x', 'APG-M11-S1'))
import tools.evkit as E
rows = [r for r in csv.DictReader(open(os.path.join(d, 'run_index.csv'))) if r['order'] == 'M01']
assert len(rows) == 1, rows
r = rows[0]
t = open(os.path.join(d, r['log']), encoding='utf-8').read()
c = int(r['exit'])
probs = E.check_output(t, c)
lines = t.splitlines()
print('M01 %s exit=%d checker_problems=%d %s' % (r['command'].split('/')[-1], c, len(probs), probs or ''))
for l in lines:
    if l.startswith(('SELECTED ', 'CONTROL ')):
        print(l)
verdicts = collections.Counter(l.split()[2] for l in lines if l.startswith('MUTANT '))
print('MUTANT lines by verdict:', dict(sorted(verdicts.items())))
print('EQUIVALENT ids:', [l.split()[1] for l in lines if l.startswith('EQUIVALENT ')])
for l in lines:
    if re.match(r'^mutants \d+ ', l) or l.startswith('RESULT '):
        print(l)
want = {'EQUIVALENT': 3, 'KILLED': 79}
eq = [l.split()[1] for l in lines if l.startswith('EQUIVALENT ')]
ok = c == 0 and not probs and dict(verdicts) == want and eq == ['MI-36', 'MI-39', 'MD-02']
print('as expected (exit 0, no checker problem, 79 KILLED, 3 EQUIVALENT: MI-36 MI-39 MD-02):', ok)
