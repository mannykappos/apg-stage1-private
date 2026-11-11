#!/usr/bin/env python3
"""Structural checks of the M5 registers.  Python 3 standard library only; read-only.  Usage: python3 -I tools/programme_check_m5.py <package_root>   Exit 0 only if every check passes.
(The M3 and M4 register checks keep passing on the extended tables and are run alongside this tool.)"""
import csv, os, re, sys
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rd = lambda p: list(csv.DictReader(open(os.path.join(ROOT, p), encoding='utf-8', newline='')))
fails = []; n = 0
def chk(cid, ok, text):
    global n; n += 1
    print(('PASS ' if ok else 'FAIL ') + cid + ' ' + text)
    if not ok: fails.append(cid)
ms, fr, ir, edr, sr = (rd('programme/' + f) for f in ('PROGRAMME_MILESTONES.csv', 'FINDINGS_REGISTER.csv', 'INTERPRETATIONS_REGISTER.csv', 'ENGINE_HANDOFF_REGISTER.csv', 'STATUS_REGISTER.csv'))
m5 = next(m for m in ms if m['milestone_id'] == 'M5')
need = {'CAP-07', 'CAP-08', 'CAP-09', 'CAP-12', 'CAP-13', 'CAP-14', 'CAP-15', 'CAP-16', 'CAP-17'}
chk('J01', m5['status'] in ('In this delivery', 'Delivered - builder-checked') and need <= set(re.findall(r'CAP-\d\d', m5['covers_capabilities'])) and all(m['status'] == 'Delivered - builder-checked' for m in ms if int(m['milestone_id'][1:]) < 5)
    and all(m['status'] == ('In this delivery' if m['milestone_id'] == 'M9' else 'Not started') for m in ms if int(m['milestone_id'][1:]) > 6), 'M5 is delivered (or in its delivery) and covers CAP-07, 08, 09 and 12 to 17; M0 to M4 are delivered; nothing after M6 has started except, from APG-M9.1, the first slice of M9 (M6 may be in its delivery)')
e10 = next(e for e in edr if e['edr_id'] == 'EDR-10'); e28 = next(e for e in edr if e['edr_id'] == 'EDR-28')
req = ['what_apg_needs', 'why_the_engine_is_needed', 'contract_summary', 'contract_test', 'decisions_for_amir', 'owner']
chk('J02', [e['edr_id'] for e in edr][27] == 'EDR-28' and all(len(e28[k].strip()) >= 25 for k in req) and e28['status'] == 'Open - described only' and e28['evidence_seen'].startswith('No Engine code')
    and e10['status'] == 'Open - contract test written' and 'written in M5' in e10['contract_test'] and 'EDR-10' in m5['handoff_register_entries'] and 'EDR-28' in m5['handoff_register_entries'],
    'EDR-28 is fully described, open and listed under M5; EDR-10 has its contract test written in M5 and is still open')
rows = [s for s in sr if s['milestone'] == 'M5']
chk('J03', len(rows) >= 11 and all(s['evidence_ladder_status'] == 'Local-tested' and s['claim_limit'] and s['evidence'] for s in rows), 'M5 status rows sit at Local-tested at most and each has evidence and a claim limit')
f5 = [f for f in fr if int(f['finding_id'][2:]) >= 23]
chk('J04', len(f5) >= 13 and not any(re.search(r'\b(closed|resolved|accepted|approved)\b', f['status'], re.I) for f in fr) and sum(f['raised_by'].startswith('Auditor') for f in f5) >= 2, 'M5 findings are recorded, two carry the auditor M4 review points, and none is shown as closed')
i5 = [i for i in ir if int(i['interpretation_id'][2:]) >= 30]
chk('J05', len(i5) >= 14 and all(i['status'] == 'Retained for review - not approved' and i['reviewer_decision'] == '' for i in i5), 'M5 interpretations are retained for review, not approved, with no reviewer decision filled in')
claim = re.compile(r'\b(has been approved|is approved|independently reviewed|has been independently|production[- ]ready|release[- ]ready|now working|closed by|accepted by|complies with|compliant with)\b', re.I)
new_edr = [e28]
hits = [(r.get('item_id') or r.get('finding_id') or r.get('interpretation_id') or r.get('edr_id'), k) for tbl in (rows, f5, i5, new_edr) for r in tbl for k, v in r.items() if claim.search(v or '')]
chk('J06', not hits, 'no register text claims approval, independent review, readiness, compliance or closure ' + str(hits))
alltext = ' '.join(' '.join(r.values()) for r in f5 + i5 + rows)
chk('J07', all(d in alltext for d in ('DEC-A1-8', 'OQ-A1-7', 'CR-02 A5', 'PS-14', 'PS-25')) and all(i['status'] != 'Approved' for i in i5), 'the open decisions the detection layer waits on are named in the M5 rows and none is settled; the M6 scenarios are named as not claimed')
f24 = next(f for f in fr if f['finding_id'] == 'F-24'); f25 = next(f for f in fr if f['finding_id'] == 'F-25')
chk('J08', all(t in f24['description'] for t in ('MG-CMP-004', 'CO-BOL-013', '672')) and all(t in f25['description'] for t in ('supplier invoices', 'Labour', 'synthetic', 'EDR-24')) and f24['raised_by'].startswith('Auditor') and f25['raised_by'].startswith('Auditor'),
    'the auditor M4 review points (two weak survivors, unreproduced runs, invoice-only cost scope, synthetic data, scalability, unresolved policies) are carried in the findings register')
cited = {t for f in f5 for t in re.findall(r'EDR-\d\d', f['linked_items'] + ' ' + f['how_it_is_handled_here'] + ' ' + f['description'])}
chk('J09', cited <= {e['edr_id'] for e in edr}, 'every handoff entry cited by an M5 finding exists ' + str(sorted(cited - {e['edr_id'] for e in edr})))
print(f'\nchecks {n}  failed {len(fails)}')
if fails: print('FAILED:', fails); sys.exit(1)
print('ALL M5 REGISTER CHECKS PASS')
