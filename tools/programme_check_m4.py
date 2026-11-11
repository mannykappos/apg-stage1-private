#!/usr/bin/env python3
"""Structural checks of the M4 registers.  Python 3 standard library only; read-only.  Usage: python3 -I tools/programme_check_m4.py <package_root>   Exit 0 only if every check passes.
(The M3 register checks, tools/programme_check_m3.py, keep passing on the extended tables and are run alongside this tool.)"""
import csv, os, re, sys
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rd = lambda p: list(csv.DictReader(open(os.path.join(ROOT, p), encoding='utf-8', newline='')))
fails = []; n = 0
def chk(cid, ok, text):
    global n; n += 1
    print(('PASS ' if ok else 'FAIL ') + cid + ' ' + text)
    if not ok: fails.append(cid)
ms, fr, ir, edr, sr = (rd('programme/' + f) for f in ('PROGRAMME_MILESTONES.csv', 'FINDINGS_REGISTER.csv', 'INTERPRETATIONS_REGISTER.csv', 'ENGINE_HANDOFF_REGISTER.csv', 'STATUS_REGISTER.csv'))
m4 = next(m for m in ms if m['milestone_id'] == 'M4')
chk('H01', m4['status'] in ('In this delivery', 'Delivered - builder-checked') and {'CAP-10', 'CAP-11', 'CAP-31'} <= set(re.findall(r'CAP-\d\d', m4['covers_capabilities'])) and all(m['status'] == ('In this delivery' if m['milestone_id'] == 'M9' else 'Not started') for m in ms if int(m['milestone_id'][1:]) > 6),
    'M4 is delivered (or in its delivery), covers CAP-10, CAP-11 and CAP-31, and nothing after M6 has started except, from APG-M9.1, the first slice of M9 (M5 may be delivered and M6 in its delivery)')
new = [e for e in edr if e['edr_id'] in ('EDR-24', 'EDR-25', 'EDR-26', 'EDR-27')]
req = ['what_apg_needs', 'why_the_engine_is_needed', 'contract_summary', 'contract_test', 'decisions_for_amir', 'owner']
chk('H02', len(new) == 4 and [e['edr_id'] for e in edr][23:27] == ['EDR-24', 'EDR-25', 'EDR-26', 'EDR-27'] and all(all(len(e[k].strip()) >= 25 for k in req) for e in new)
    and all(e['blueprint_refs'].strip() for e in new) and all(e['status'] == 'Open - described only' and e['evidence_seen'].startswith('No Engine code') for e in new) and all(e['edr_id'] in m4['handoff_register_entries'] for e in new), 'the four handoff entries opened by M4 exist, are fully described, open, and are listed under M4')
rows = [s for s in sr if s['milestone'] == 'M4']
chk('H03', len(rows) >= 9 and all(s['evidence_ladder_status'] == 'Local-tested' and s['claim_limit'] and s['evidence'] for s in rows), 'M4 status rows sit at Local-tested at most and each has evidence and a claim limit')
f4 = [f for f in fr if 14 <= int(f['finding_id'][2:]) <= 22]
chk('H04', len(f4) >= 9 and not any(re.search(r'\b(closed|resolved|accepted|approved)\b', f['status'], re.I) for f in fr) and any(f['raised_by'].startswith('Auditor') for f in f4), 'M4 findings are recorded, one carries the auditor M3 review point, and none is shown as closed')
i4 = [i for i in ir if 17 <= int(i['interpretation_id'][2:]) <= 29]
chk('H05', len(i4) >= 13 and all(i['status'] == 'Retained for review - not approved' and i['reviewer_decision'] == '' for i in i4), 'M4 interpretations are retained for review, not approved, with no reviewer decision filled in')
claim = re.compile(r'\b(has been approved|is approved|independently reviewed|has been independently|production[- ]ready|release[- ]ready|now working|closed by|accepted by|complies with|compliant with)\b', re.I)
hits = [(r.get('item_id') or r.get('finding_id') or r.get('interpretation_id') or r.get('edr_id'), k) for tbl in (rows, f4, i4, new) for r in tbl for k, v in r.items() if claim.search(v or '')]
chk('H06', not hits, 'no register text claims approval, independent review, readiness, compliance or closure ' + str(hits))
dec = ' '.join(' '.join(i.values()) for i in i4)
chk('H07', all(d in ' '.join(' '.join(r.values()) for r in i4 + f4) for d in ('CR-02 A5', 'CR-02 A7', 'CR-02 A1')) and 'not approved' in dec, 'the open CR-02 decisions the calculations wait on are named in the M4 rows and none is settled')
print(f'\nchecks {n}  failed {len(fails)}')
if fails: print('FAILED:', fails); sys.exit(1)
print('ALL M4 REGISTER CHECKS PASS')
