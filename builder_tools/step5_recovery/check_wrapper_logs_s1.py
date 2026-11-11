#!/usr/bin/env python3
"""Builder tool: check every wrapper log of a run set with the frozen tree's own evkit (check_output, wrapper_verdict) and total the
FILE, CHECK and EXCLUDED groups.  Usage: python3 -I -S check_wrapper_logs_s1.py RUN_DIR      BUILDER-EXECUTED: NOT INDEPENDENT."""
import csv, os, re, sys
d = sys.argv[1]
sys.path.insert(0, os.path.join(d, 'x', 'APG-M11-S1'))
import tools.evkit as E
tot = {'FILE': 0, 'CHECK': 0, 'EXCLUDED': 0}
nonpass = []
for r in csv.DictReader(open(os.path.join(d, 'run_index.csv'))):
    t = open(os.path.join(d, r['log']), encoding='utf-8').read()
    c = int(r['exit'])
    probs = E.check_output(t, c)
    v = E.wrapper_verdict(t, c)
    for k in tot:
        tot[k] += len(re.findall(r'(?m)^%s G\d+ ' % k, t))
    bad = [l for l in t.splitlines() if re.match(r'^(CHECK \S+ (?!PASS)|FILE \S+ state=(?!COMPLETED)|FILE \S+ state=COMPLETED .* (failed|errors)=[1-9])', l)]
    nonpass += [(r['order'], l[:120]) for l in bad]
    print('%s %-22s exit=%s %-19s checker_problems=%d' % (r['order'], r['command'].split('/')[-1].split(' ')[0], c, v, len(probs)))
print('totals', tot)
print('non-passing group lines:', nonpass or 'none')
