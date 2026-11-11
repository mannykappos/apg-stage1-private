"""APG Data Supply System, draft 1: the entity supply plan.  Reads revision 3's ENTITY_REGISTER.csv and RULE_INPUT_CONTRACTS.csv and writes
SUPPLY_PLAN.csv: for each entity, its minimum (Level 1) way in, the alternatives, and its phase.  Builder work (Claude), not independent.

Phase rules (stated in the doc, applied here mechanically):
  1  entities a current rule or financial figure reads; the configuration those contracts name; the intake's own records (E01 provenance,
     E02 source registry, E03 authority register) and the readiness record (E89)
  2  entities that close a known limit of a current rule or figure (the contracts' last column), not already in phase 1
  later  everything else: needed by insights the blueprint specifies but not yet built, settled after builder discovery
  optional  the developer entities (not in the locked blueprint)
Minimum way in: Level 1 only (T import template, D document capture, E entry screen, S setup question, A record APG creates).  APG-internal
entities take A where listed, configuration takes S where listed; otherwise the most-built path wins (exists, then partly, then proposed),
ties broken T, D, E, S, A.  P (phone) and I (integration) are never the minimum."""
import csv, re, sys
REV3 = sys.argv[1]
E = list(csv.DictReader(open(f'{REV3}/ENTITY_REGISTER.csv')))
R = list(csv.DictReader(open(f'{REV3}/RULE_INPUT_CONTRACTS.csv')))
ids = lambda s: set(re.findall(r'E\d\d', s))
read = set().union(*(ids(r['entity']) for r in R))
config = set().union(*(ids(r['configuration or parameter']) for r in R))
limits = set().union(*(ids(r['known limit and the entity that closes it']) for r in R))
P1 = read | config | {'E01', 'E02', 'E03', 'E89'}
L1, ORDER, BUILT = 'TDESA', 'TDESA', {'exists': 0, 'partly': 1, 'proposed': 2}
NAME = {'T': 'import template', 'D': 'document capture', 'E': 'entry screen', 'S': 'setup question', 'A': 'APG creates',
        'P': 'phone site capture', 'I': 'integration'}
rows = []
for e in E:
    paths = []
    for part in e['path status'].split(';'):
        code, state = part.split()[0], part.split()[-1]
        assert code in NAME and state in BUILT, (e['id'], part)
        paths.append((code, state))
    l1 = [p for p in paths if p[0] in L1]
    assert l1, e['id']
    pref = {'I': 'A', 'C': 'S'}.get(e['class'])
    if pref and any(c == pref for c, _ in l1):
        best = next(p for p in l1 if p[0] == pref)
    else:
        best = min(l1, key=lambda p: (BUILT[p[1]], ORDER.index(p[0])))
    phase = 'optional' if e['class'] == 'V' else '1' if e['id'] in P1 else '2' if e['id'] in limits else 'later'
    why = ('read by a current rule or figure' if e['id'] in read else 'configuration a current contract names' if e['id'] in config
           else 'the intake or readiness itself' if e['id'] in P1 else 'closes a known limit of a current rule or figure' if e['id'] in limits
           else 'developer extension' if phase == 'optional' else 'needed by insights not yet built')
    rows.append({'id': e['id'], 'entity': e['entity'], 'class': e['class'], 'status today': e['status'], 'phase': phase, 'why this phase': why,
                 'minimum way in (Level 1)': NAME[best[0]], 'its build state': best[1],
                 'other Level 1 ways in': '; '.join(f'{NAME[c]} ({s})' for c, s in l1 if (c, s) != best),
                 'Level 2 and 3': '; '.join(f'{NAME[c]} ({s})' for c, s in paths if c not in L1)})
with open('SUPPLY_PLAN.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)
from collections import Counter
print('entities', len(rows), 'classes', Counter(r['class'] for r in rows))
print('phase', Counter(r['phase'] for r in rows))
print('phase x minimum:', sorted(Counter((r['phase'], r['minimum way in (Level 1)'], r['its build state']) for r in rows).items()))

# Phase 1 check: every current rule and figure gets every entity it reads, and every configuration entity its contract names, from a Level 1
# way in that phase 1 builds; none depends on phone capture or an integration.
plan = {r['id']: r for r in rows}
out, bad = [], 0
for c in R:
    need = sorted(ids(c['entity']) | ids(c['configuration or parameter']))
    ok = all(plan[i]['phase'] == '1' and plan[i]['minimum way in (Level 1)'] in {NAME[x] for x in L1} for i in need)
    bad += not ok
    out.append({'rule or figure': c['rule or figure'], 'code': c['code'], 'entities it reads or is configured by': ' '.join(need) or '-',
                'their minimum ways in': '; '.join(f"{i} {plan[i]['minimum way in (Level 1)']} ({plan[i]['its build state']})" for i in need) or '-',
                'fed in phase 1 without phone or integration': 'yes' if ok else 'NO'})
with open('PHASE1_CHECK.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0]), lineterminator='\n'); w.writeheader(); w.writerows(out)
print('phase 1 check rows', len(out), 'failing', bad)
nb = [r for r in rows if r['phase'] == '1' and r['its build state'] != 'exists']
print('phase 1 minimum ways in not fully built:', [(r['id'], r['minimum way in (Level 1)'], r['its build state']) for r in nb])
assert bad == 0
