"""APG Data Supply System, draft 4: field-level coverage of the current rules and M4 figures.  Builder work (Claude), not independent.
For every row of revision 3's RULE_INPUT_CONTRACTS.csv, every field name it lists is classified:
  template field          - a field of that record kind in FIELD_REGISTER.csv (a synthetic stage 1 template carries it today)
  person-entered record   - retention_event: recorded by a named person; release A entry form (today a direct write)
  intake state            - set by the intake itself (duplicate_of, reconciliation state)
  calculation output      - produced by an M4 calculation, not supplied (invoice_lines, the carrying components)
  setting                 - a detection-rule setting (N01), e.g. instruction_types
Anything else is a GAP: a field a rule reads that no way in carries.  The script fails if a gap is found.
usage: python3 -I build_field_coverage.py <folder with RULE_INPUT_CONTRACTS.csv and FIELD_REGISTER.csv>"""
import csv, re, sys, collections
d = sys.argv[1]
R = list(csv.DictReader(open(f'{d}/RULE_INPUT_CONTRACTS.csv')))
reg = collections.defaultdict(set)
for f in csv.DictReader(open(f'{d}/FIELD_REGISTER.csv')):
    reg[f['record_kind']].add(f['field'])
fields = set().union(*reg.values())
KNOWN = {'retention_event': 'person-entered record', 'duplicate_of': 'intake state', 'invoice_lines': 'calculation output',
         'retention_carrying': 'calculation output', 'security_carrying': 'calculation output', 'overdue_receivables': 'calculation output',
         'instruction_types': 'setting (N01)'}
out, gaps = [], 0
for r in R:
    toks = re.findall(r'[a-z][a-z_]*[a-z]', r['record kinds and fields'])
    kinds = sorted({t for t in toks if t in reg})
    named = [t for t in toks if '_' in t and t not in reg]
    tmpl = sorted({t for t in named if t in fields})
    other = sorted({t for t in named if t not in fields})
    cls = {t: KNOWN.get(t, 'GAP') for t in other}
    gaps += sum(v == 'GAP' for v in cls.values())
    out.append({'rule or figure': r['rule or figure'], 'record kinds named': ' '.join(kinds) or '-',
                'fields carried by a template today': ' '.join(tmpl) or '-',
                'other items and what supplies them': '; '.join(f'{k}: {v}' for k, v in cls.items()) or '-',
                'reads records': 'no' if r['record kinds and fields'].strip() == '-' else 'yes'})
with open('FIELD_COVERAGE.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0]), lineterminator='\n'); w.writeheader(); w.writerows(out)
n = sum(len(o['fields carried by a template today'].split()) for o in out if o['fields carried by a template today'] != '-')
print('rows', len(out), 'template field mentions', n, 'gaps', gaps)
assert gaps == 0
