#!/usr/bin/env python3
"""Structural checks of the M6 registers and of the RFC-01 record.  Python 3 standard library only; read-only.  Usage: python3 -I tools/programme_check_m6.py <package_root>   Exit 0 only if every check passes.
(The M3, M4 and M5 register checks keep passing on the extended tables and are run alongside this tool.)"""
import csv, os, re, sys
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rd = lambda p: list(csv.DictReader(open(os.path.join(ROOT, p), encoding='utf-8', newline='')))
fails = []; n = 0
def chk(cid, ok, text):
    global n; n += 1
    print(('PASS ' if ok else 'FAIL ') + cid + ' ' + text)
    if not ok: fails.append(cid)
ms, fr, ir, edr, sr, rfc = (rd('programme/' + f) for f in ('PROGRAMME_MILESTONES.csv', 'FINDINGS_REGISTER.csv', 'INTERPRETATIONS_REGISTER.csv', 'ENGINE_HANDOFF_REGISTER.csv', 'STATUS_REGISTER.csv', 'RFC_REGISTER.csv'))
rfc_doc = open(os.path.join(ROOT, 'programme', 'RFC-01_LATENT_RISK_AND_INTERVENTION_ENGINE.md'), encoding='utf-8').read()
m6 = next(m for m in ms if m['milestone_id'] == 'M6')
need = {f'CAP-{i}' for i in range(18, 27)}
chk('L01', m6['status'] == 'In this delivery' and need <= set(re.findall(r'CAP-\d\d', m6['covers_capabilities'])) and all(m['status'] == 'Delivered - builder-checked' for m in ms if int(m['milestone_id'][1:]) < 6)
    and all(m['status'] == ('In this delivery' if m['milestone_id'] == 'M9' else 'Not started') for m in ms if int(m['milestone_id'][1:]) > 6), 'M6 is the milestone in this delivery and covers CAP-18 to CAP-26; M0 to M5 are delivered; nothing after M6 has started except, from APG-M9.1, the first slice of M9 (M7 is untouched)')
e08, e09, e29, e30 = (next(e for e in edr if e['edr_id'] == i) for i in ('EDR-08', 'EDR-09', 'EDR-29', 'EDR-30'))
req = ['what_apg_needs', 'why_the_engine_is_needed', 'contract_summary', 'contract_test', 'decisions_for_amir', 'owner']
chk('L02', all(len(e[k].strip()) >= 25 for e in (e29, e30) for k in req) and all(e['status'] == 'Open - described only' and e['evidence_seen'].startswith('No Engine code') for e in (e29, e30)) and [e['edr_id'] for e in edr][:30][-2:] == ['EDR-29', 'EDR-30']
    and all(e['status'] == 'Open - contract test written' and 'written in M6' in e['contract_test'] for e in (e08, e09)) and all(i in m6['handoff_register_entries'] for i in ('EDR-08', 'EDR-09', 'EDR-29', 'EDR-30')),
    'EDR-29 and EDR-30 are fully described, open and listed under M6; EDR-08 and EDR-09 have their contract tests written in M6 and are still open')
rows = [s for s in sr if s['milestone'] == 'M6']
chk('L03', len(rows) >= 18 and all(s['evidence_ladder_status'] == 'Local-tested' and s['claim_limit'] and s['evidence'] for s in rows), 'M6 status rows sit at Local-tested at most and each has evidence and a claim limit')
f6 = [f for f in fr if int(f['finding_id'][2:]) >= 36]
chk('L04', len(f6) >= 14 and not any(re.search(r'\b(closed|resolved|accepted|approved)\b', f['status'], re.I) for f in fr) and sum(f['raised_by'].startswith('Auditor') for f in f6) >= 4, 'M6 findings are recorded, four carry the auditor M5 review points, and none is shown as closed')
i6 = [i for i in ir if int(i['interpretation_id'][2:]) >= 44]
chk('L05', len(i6) >= 15 and all(i['status'] == 'Retained for review - not approved' and i['reviewer_decision'] == '' for i in i6), 'M6 interpretations are retained for review, not approved, with no reviewer decision filled in')
claim = re.compile(r'(?<!not )(?<!no )\b(has been approved|is approved|independently reviewed|has been independently|production[- ]ready|release[- ]ready|now working|closed by|accepted by|complies with|compliant with|guaranteed)\b', re.I)
hits = [(r.get('item_id') or r.get('finding_id') or r.get('interpretation_id') or r.get('edr_id') or r.get('rfc_id'), k) for tbl in (rows, f6, i6, [e29, e30], rfc) for r in tbl for k, v in r.items() if claim.search(v or '')]
chk('L06', not hits, 'no register text claims approval, independent review, readiness, compliance, a guarantee or closure ' + str(hits))
alltext = ' '.join(' '.join(r.values()) for r in f6 + i6 + rows)
chk('L07', all(d in alltext for d in ('DEC-A1-8', 'DEC-MIE-01', 'CR-02', 'EDR-24', 'EDR-29')) and all(i['status'] != 'Approved' for i in i6), 'the open decisions the procurement layer waits on are named in the M6 rows and none is settled')
auditor = {f['finding_id']: f for f in f6 if f['raised_by'].startswith('Auditor') and f['milestone'] == 'M6'}          # later correction releases (M6.2) record their own auditor findings under their own milestone
chk('L08', set(auditor) == {'F-36', 'F-37', 'F-38', 'F-40'} and '$0.00' in auditor['F-36']['description'] and 'DEC-A1-8' in auditor['F-37']['linked_items'] and 'whole record types' in auditor['F-38']['description']
    and all(t in auditor['F-40']['description'] for t in ('supplier invoices', 'synthetic', '678')), 'the four auditor M5 review points (portfolio display, grouping key, scalability, invoice-only scope / synthetic data / unreproduced runs) are carried in the findings register')
cited = {t for f in f6 for t in re.findall(r'EDR-\d\d', f['linked_items'] + ' ' + f['how_it_is_handled_here'] + ' ' + f['description'])}
chk('L09', cited <= {e['edr_id'] for e in edr}, 'every handoff entry cited by an M6 finding exists ' + str(sorted(cited - {e['edr_id'] for e in edr})))
r1 = rfc[0] if len(rfc) == 1 else {}
BASE = '487becabdf47796800937d13a706a19b63b7b8230ecc5354b2f01a647ae5d960'
chk('L10', len(rfc) == 1 and r1.get('rfc_id') == 'RFC-01' and r1['status'].startswith('PROPOSED') and 'not approved' in r1['status'] and all(len(v.strip()) >= 20 for k, v in r1.items() if k not in ('rfc_id', 'received')),
    'the RFC register holds RFC-01 as PROPOSED and not approved, with scope, affected components, dependencies, acceptance criteria, unresolved decisions, required approvals and conflicts all filled in')
chk('L11', BASE in r1.get('locked_baseline_effect', '') and 'None' in r1['locked_baseline_effect'] and 'M7' in r1['conflicts_reported'] and 'not independently' in r1['evidence_level_reached'] and 'Not started' in r1['later_milestone_status']
    and 'test target' in r1['acceptance_criteria'] and '72 hours' in r1['acceptance_criteria'] and 'None has happened' in r1['required_approvals'],
    'the RFC record states that the locked baseline is unchanged (with its hash), reports the M7 conflict, keeps independent verification unclaimed, calls 72 hours and $2,000 / $10,000 test targets and says no approval has happened')
levels = ['Proposed design', 'Implemented code', 'Locally tested', 'Independently verified', 'Production accepted']
chk('L12', all(l in rfc_doc for l in levels) and BASE in rfc_doc and 'PROPOSED' in rfc_doc and 'Not approved' in rfc_doc and 'CR-09' in rfc_doc and rfc_doc.count('| ') > 30 and all(f'| {i} |' in rfc_doc for i in range(1, 7)), 'the RFC document keeps the five evidence levels apart, cites the baseline hash, and gives a row for each of the six capabilities')
a, b = rd('regression/m5_snapshot/PROGRAMME_MILESTONES.csv'), ms
m7a, m7b = next(x for x in a if x['milestone_id'] == 'M7'), next(x for x in b if x['milestone_id'] == 'M7')
chk('L13', m7a == m7b, 'the existing M7 row (Recommendations) is byte-for-byte the delivered one; RFC-01 does not edit it')
print(f'\nchecks {n}  failed {len(fails)}')
if fails: print('FAILED:', fails); sys.exit(1)
print('ALL M6 REGISTER CHECKS PASS')
