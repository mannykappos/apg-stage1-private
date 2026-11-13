"""Assemble the cascade impact assessment from its hand-written text and the tables build_cia.py generates.
Builder work (Claude), not independent.  usage: python3 -I assemble.py <CIA_SOURCE.md> <folder with the CSVs> <output .md>
Markers in the source:  <<SECTION_SUMMARY>>  one row per section: amended or dependent, insertions, RTM IDs reviewed
                        <<PROPOSED_TEXT>>    every proposed addition, by section, with its ID and where it goes
                        <<COUNTS>>           the counts file, as a list"""
import csv, os, sys, collections

SRC, D, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
prop = list(csv.DictReader(open(os.path.join(D, 'CIA_PROPOSED_TEXT.csv'))))
imp = list(csv.DictReader(open(os.path.join(D, 'CIA_RTM_IMPACT.csv'))))
TITLE = {'00': 'Control & Product Charter', '01': 'Discovery, Current-State Inventory & Assumptions Register', '02': 'Product Requirements, Actors & Workflows',
         '03': 'Domain Model & Canonical Financial Semantics', '04': 'Data Ingestion, Normalisation & Reconciliation', '05': 'Profitability Calculation Engine',
         '06': 'Active Intelligence & Profit Leakage Detection', '07': 'Schedule, Delay & Holding-Cost Intelligence',
         '08': 'Materials, Global Markets & Procurement Intelligence', '09': 'Labour, Productivity & Resource Intelligence',
         '10': 'Recommendations, Prioritisation & Scenario Engine', '11': 'Commercial & Revenue Intelligence',
         '12': 'Cash Flow, Working Capital, Retentions & Security', '13': 'Quality, Rework & Defect Intelligence',
         '14': 'Implementation Plan, Dependency Sequencing & Claude Handoff', '15': 'Security, Privacy, Access Control & Governance',
         '16': 'Operational Reliability, Monitoring, Resilience & Recovery', '17': 'Testing, Acceptance, Verification & Release Readiness',
         '18': 'Final Blueprint Handoff, Consolidation & Controlled Change Governance'}

def esc(s):
    return s.replace('|', '\\|')

def summary():
    amended = collections.Counter(p['section'] for p in prop)
    ids = collections.defaultdict(set); items = collections.defaultdict(set)
    for r in imp:
        ids[r['section']].add(r['RTM ID or source anchor'])
        for it in r['change item'].split(', '):
            items[r['section']].add(it)
    out = ['| Section | Title (as the section itself is titled) | Disposition | Additions | Existing IDs or anchors touched | Change items |', '| --- | --- | --- | --- | --- | --- |']
    for s in sorted(set(ids) | set(amended) | {'18'}):
        if s == '18':
            out.append('| 18 | %s | reviewed; no text change; its package assets change (section 6.7) | 0 | none (S18 has no RTM rows, by design) | C21 |' % TITLE[s])
            continue
        disp = 'amended: v1.0 to v1.1, additions only' if s in amended else 'dependent: reviewed, no text change'
        out.append('| %s | %s | %s | %d | %d | %s |' % (s, TITLE[s], disp, amended.get(s, 0), len(ids[s]), ', '.join(sorted(items[s]))))
    return '\n'.join(out)

def proposed():
    out = []
    for s in sorted({p['section'] for p in prop}):
        out.append('### Section %s (%s)' % (s, TITLE[s]))
        out.append('')
        last = None
        for p in [x for x in prop if x['section'] == s]:
            if p['inserted after'] != last:
                if last is not None:
                    out.append('')
                out.append('Inserted after **%s**, which reads: "%s…"' % (p['inserted after'], p['which reads'].rstrip()))
                out.append('')
                last = p['inserted after']
            text = p['proposed text']
            if p['kind'] == 'table rows':
                out.append('- **%s** (%s; change item %s):' % (p['proposed ID'], p['kind'], p['change item']))
                for row in text.split(' ; '):
                    a, b = row.split(' | ', 1)
                    out.append('    - %s: %s' % (a.strip(), b.strip()))
            else:
                out.append('- **%s** (%s; change item %s): %s' % (p['proposed ID'], p['kind'], p['change item'], text))
        out.append('')
    return '\n'.join(out)

def counts():
    return '\n'.join(('- ' + l.strip()) if l.strip() else '' for l in open(os.path.join(D, 'CIA_COUNTS.txt')).read().split('\n'))

t = open(SRC).read()
for k, f in (('<<SECTION_SUMMARY>>', summary), ('<<PROPOSED_TEXT>>', proposed), ('<<COUNTS>>', counts)):
    if k not in t:
        sys.exit('marker missing: ' + k)
    t = t.replace(k, f())
open(OUT, 'w').write(t)
print('written', OUT, len(t.split()), 'words')
