#!/usr/bin/env python3
"""Structural checks of the M3 registers.  Python 3 standard library only; read-only.  Usage: python3 -I tools/programme_check_m3.py <package_root>   Exit 0 only if every check passes."""
import csv, os, re, sys
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rd = lambda p: list(csv.DictReader(open(os.path.join(ROOT, p), encoding='utf-8', newline='')))
fails = []; n = 0
def chk(cid, ok, text):
    global n; n += 1
    print(('PASS ' if ok else 'FAIL ') + cid + ' ' + text)
    if not ok: fails.append(cid)
fr, ir, edr, sr = rd('programme/FINDINGS_REGISTER.csv'), rd('programme/INTERPRETATIONS_REGISTER.csv'), rd('programme/ENGINE_HANDOFF_REGISTER.csv'), rd('programme/STATUS_REGISTER.csv')
chk('Q01', [f['finding_id'] for f in fr] == [f'F-{i:02d}' for i in range(1, len(fr) + 1)] and all(all(len(f[k].strip()) >= 20 for k in ('title', 'description', 'how_it_is_handled_here')) and len(f['status'].strip()) >= 10 and f['raised_by'] for f in fr), 'findings: sequential ids, each with a description, handling and status')
chk('Q02', [i['interpretation_id'] for i in ir] == [f'I-{i}' for i in range(1, len(ir) + 1)] and all(i['builder_reading'] and i['effect_if_wrong'] and i['blueprint_ref'] for i in ir), 'interpretations: sequential ids, each with the builder reading, the blueprint reference and what follows if it is wrong')
chk('Q03', all(i['status'] == 'Retained for review - not approved' and i['reviewer_decision'] == '' for i in ir), 'every interpretation is retained for review and none has a reviewer decision recorded by the builder')
edrs = {e['edr_id'] for e in edr}
cited = {t for f in fr for t in re.findall(r'EDR-\d\d', f['linked_items'] + ' ' + f['how_it_is_handled_here'] + ' ' + f['description'])}
chk('Q04', cited <= edrs, 'every handoff entry cited by a finding exists ' + str(sorted(cited - edrs)))
chk('Q05', not any(re.search(r'\b(closed|resolved|accepted|approved)\b', f['status'], re.I) for f in fr), 'no finding is shown as closed, resolved, accepted or approved')
claim = re.compile(r'\b(has been approved|is approved|independently reviewed|has been independently|production[- ]ready|is built|now working|closed by|accepted by)\b', re.I)
txt = [(r['finding_id'], k) for r in fr for k, v in r.items() if claim.search(v)] + [(r['interpretation_id'], k) for r in ir for k, v in r.items() if claim.search(v)]
chk('Q06', not txt, 'no register text claims approval, independent review, readiness or closure ' + str(txt))
m3rows = [s for s in sr if s['milestone'] == 'M3']
chk('Q07', len(m3rows) >= 9 and all(s['evidence_ladder_status'] == 'Local-tested' and s['claim_limit'] for s in m3rows), 'M3 status rows sit at Local-tested at most and each has a claim limit')
chk('Q08', {'EDR-22', 'EDR-23'} <= edrs and all(e['status'] == 'Open - described only' for e in edr if e['edr_id'] in ('EDR-22', 'EDR-23')), 'the two handoff entries opened by M3 exist and are described only')
print(f'\nchecks {n}  failed {len(fails)}')
if fails: print('FAILED:', fails); sys.exit(1)
print('ALL M3 REGISTER CHECKS PASS')
