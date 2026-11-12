"""Revision 4: CHART_DATA_PATHS.csv from ENTITY_REGISTER.csv: for each APG supply path, the entities whose row lists it, built (exists or partly)
or not built (proposed).  Builder work (Claude)."""
import csv
NAMES = [('Entry screens', 'E'), ('Import templates', 'T'), ('Integrations', 'I'), ('Phone site capture', 'P'), ('Setup questions', 'S'),
         ('Records APG calculates', 'A'), ('Document capture', 'D')]
cnt = {c: [0, 0] for _, c in NAMES}
for r in csv.DictReader(open('ENTITY_REGISTER.csv')):
    for part in r['path status'].split(';'):
        code, state = part.split()[0], part.split()[-1]
        cnt[code][0 if state in ('exists', 'partly') else 1] += 1
with open('CHART_DATA_PATHS.csv', 'w', newline='') as fh:
    w = csv.writer(fh, lineterminator='\n')
    w.writerow(['path', 'code', 'entities with this path built (exists or partly)', 'entities with this path not built (proposed)'])
    for n, c in NAMES:
        w.writerow([n, c] + cnt[c])
print({n: cnt[c] for n, c in NAMES})
