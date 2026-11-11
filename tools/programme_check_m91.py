#!/usr/bin/env python3
"""Structural checks of the APG-M9.1 records: the status rows SR-76 to SR-80, the interpretations I-81 to I-87, the handoff entry EDR-31, the carried-forward items CF-26 and CF-27, the M9 milestone row, the contract document, the change record,
and that the findings, RFC and governance records were not changed.
Python 3 standard library only; read-only.  Usage: python3 -I tools/programme_check_m91.py <package_root>   Exit 0 only if every check passes.  (The M3 to M6.5 register checks keep passing on the extended tables.)"""
import csv, json, os, re, sys
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rd = lambda p: list(csv.DictReader(open(os.path.join(ROOT, p), encoding='utf-8', newline='')))
txt = lambda p: open(os.path.join(ROOT, p), encoding='utf-8').read()
fails = []; n = 0


def chk(cid, ok, text):
    global n
    n += 1
    print(('PASS ' if ok else 'FAIL ') + cid + ' ' + text)
    if not ok:
        fails.append(cid)


fr, ir, sr, gv, rfc, cf, ms, eh = (rd('programme/' + f) for f in ('FINDINGS_REGISTER.csv', 'INTERPRETATIONS_REGISTER.csv', 'STATUS_REGISTER.csv', 'E17_GOVERNANCE_REGISTER.csv', 'RFC_REGISTER.csv', 'CARRIED_FORWARD_REGISTER.csv', 'PROGRAMME_MILESTONES.csv', 'ENGINE_HANDOFF_REGISTER.csv'))
s91 = [s for s in sr if s['milestone'] == 'M9.1']
chk('N01', [s['item_id'] for s in s91] == ['SR-76', 'SR-77', 'SR-78', 'SR-79', 'SR-80'] and [s['evidence_ladder_status'] for s in s91] == ['Local-tested', 'Local-tested', 'Local-tested', 'Specified', 'Local-tested'] and all(s['claim_limit'] and s['evidence'] for s in s91)
    and all('no independent review has taken place' in s['claim_limit'] for s in s91) and 'no screen, API' in s91[0]['claim_limit'] and 'CF-22 and CF-25 stay open' in s91[0]['claim_limit'] and 'incomplete, not as a pass' in s91[4]['claim_limit'],
    'SR-76 to SR-80 sit at Local-tested (the contract document at Specified), each has evidence and a claim limit; every limit says no independent review has taken place; SR-76 says no screen or API exists and CF-22 and CF-25 stay open; SR-80 says an unfinished run is incomplete, not a pass')
chk('N01b', all(not re.search(r'\b(Independently|Accepted|Approved|Production)\b', s['evidence_ladder_status']) for s in s91), 'no new status row is above Local-tested or Specified')
i91 = [i for i in ir if i['milestone'] == 'M9.1']
chk('N02', [i['interpretation_id'] for i in i91] == [f'I-{k}' for k in range(81, 88)] and all(i['status'] == 'Retained for review - not approved' and i['reviewer_decision'] == '' and i['builder_reading'] and i['effect_if_wrong'] for i in i91)
    and 'EDR-29' in i91[1]['builder_reading'] and 'same answer' in i91[2]['topic'] and 'replay' in i91[3]['builder_reading'].lower(),
    'I-81 to I-87 are retained for review, not approved, with no reviewer decision; each states the reading and what follows if it is wrong')
c = {x['cf_id']: x for x in cf}
chk('N03', [x['cf_id'] for x in cf][:27] == [f'CF-{k:02d}' for k in range(1, 28)] and all(len(v.strip()) >= 3 for x in cf for k, v in x.items() if k != 'audit_section') and all(x['audit_section'].strip() for x in cf),
    'the carried-forward register holds CF-01 to CF-27 in order with every cell filled')
chk('N03b', c['CF-25']['status'] == 'Open - not built' and c['CF-22']['status'].startswith('Open') and c['CF-26']['status'].startswith('Open - function built and tested (APG-M9.1)') and 'CF-25 and CF-22 stay open' in c['CF-26']['what_remains_open']
    and 'No independent review of the boundary has taken place' in c['CF-26']['what_remains_open'] and c['CF-27']['status'] == 'Open - for the auditor' and 'Auditor' in c['CF-27']['who_must_act'],
    'CF-22 and CF-25 are unedited and open (CF-26 records what was built and what remains); CF-26 says no independent review has taken place; CF-27 is open for the auditor')
chk('N03c', not any(re.search(r'\b(closed|resolved|accepted|approved)\b', x['status'], re.I) for x in cf), 'no carried-forward item is shown as closed, resolved, accepted or approved')
e = {x['edr_id']: x for x in eh}
m9 = next(m for m in ms if m['milestone_id'] == 'M9')
chk('N04', 'EDR-31' in e and e['EDR-31']['status'] == 'Open - described only' and e['EDR-31']['evidence_seen'].startswith('No Engine code') and e['EDR-31']['owner'].startswith('Amir') and e['EDR-31']['port'] == 'ProjectActionPort'
    and 'allows(context, scope, action)' in e['EDR-31']['contract_summary'] and 'run_m91_contracts.py' in e['EDR-31']['contract_test'] and 'EDR-31' in m9['handoff_register_entries'] and m9['status'] == 'In this delivery' and next(m for m in ms if m['milestone_id'] == 'M7')['status'] == 'Not started',
    'EDR-31 is described only (no Engine code seen), with its contract and contract test named; the M9 row lists it and is "In this delivery"; M7 is not started')
by = {f['finding_id']: f for f in fr}
chk('N05', [f['finding_id'] for f in fr][56] == 'F-57' and len(fr) >= 57 and all(by[k]['status'].startswith(('Corrected in', 'Handled in')) or 'open' in by[k]['status'].lower() or 'Open' in by[k]['status'] for k in ('F-52', 'F-53', 'F-54', 'F-55', 'F-56', 'F-57')) and 'open until independently verified' in by['F-57']['status']
    and not any(re.search(r'\b(closed|accepted|approved|resolved)\b', f['status'], re.I) for f in fr), 'no finding was added (F-57 is the last) or closed; F-52 to F-57 stay open for independent verification')
g = {x['record_id']: x for x in gv}
chk('N06', [x['record_id'] for x in gv] == [f'G-{k:02d}' for k in range(1, 13)] and g['G-01']['status'] == 'Recorded - RFC-01 still proposed and unnumbered' and all(g[k]['status'] == 'PROPOSED - not implemented' for k in ('G-04', 'G-05', 'G-06', 'G-07'))
    and g['G-09']['status'] == 'Recorded - nothing configured' and g['G-11']['status'] == 'In sequence - foundations not started' and len(rfc) == 1 and rfc[0]['rfc_id'] == 'RFC-01' and rfc[0]['status'].startswith('PROPOSED - not approved') and 'not yet a numbered change request' in rfc[0]['status'],
    'the governance and RFC registers are unchanged: RFC-01 unnumbered and proposed, the four baseline rules PROPOSED, no finance assumption configured, foundations not started')
claim = re.compile(r'(?<!not )(?<!no )\b(has been approved|is approved|independently reviewed|has been independently|production[- ]ready|release[- ]ready|now working|closed by|accepted by|complies with|compliant with|guaranteed|has been adopted|is adopted|verified by)\b', re.I)
new_rows = s91 + i91 + [c['CF-26'], c['CF-27'], e['EDR-31']]
hits = [(r.get('item_id') or r.get('interpretation_id') or r.get('cf_id') or r.get('edr_id'), k) for r in new_rows for k, v in r.items() if claim.search(v or '')]
chk('N07', not hits, 'no new register text claims approval, independent review, readiness, compliance, adoption or closure ' + str(hits))
doc = txt('programme/APPROVAL_REQUEST_BOUNDARY.md')
narrow = re.compile(r'\b(has been approved|is approved|has been independently (?:verified|accepted|approved|audited)|closed by|accepted by|complies with|compliant with|guaranteed|has been adopted|is adopted)\b', re.I)          # the contract document and the change record must say what is NOT done, so the words 'production-ready' and 'independently reviewed' may appear in negations
secs = ('## 1. What it is for', '## 2. The three calls', '## 3. The order of checks', '## 4. One answer per request id', '## 5. Results and codes', '## 6. Audit', "## 7. Suggested mapping", '## 8. What the Engine must provide', '## 9. What this does not show')
chk('N08', all(k in doc for k in secs) and 'Nothing here has been independently reviewed' in doc and 'CF-22 and CF-25 stay open' in doc and 'EDR-31' in doc and not narrow.search(doc), 'the contract document has its nine sections, names EDR-31, says nothing here has been independently reviewed and that CF-22 and CF-25 stay open')
cr = txt('programme/CHANGE_RECORD_APG-M9.1.md')
B = json.load(open(os.path.join(ROOT, 'regression', 'BASELINE_M65.json')))
listed = set(B['changed_in_m91']) | set(B['added_in_m91'])
missing = sorted(r for r in listed if '`' + r + '`' not in cr and not r.startswith(('logs/', 'regression/m65_snapshot/')))
secs = ('## 1. What this slice is', "## 2. A defect found in the builder's own draft", '## 3. Files changed and added', '## 4. What the boundary does', '## 5. Tests', '## 6. Results, and how each is classified', '## 7. Carried forward', '## 8. What this does not show')
chk('N09', not missing and all(k in cr for k in secs) and 'no independent review has taken place' in cr and 'CF-22' in cr and 'F-52 to F-57' in cr, 'the change record has its eight sections, names every changed or added file, says no independent review has taken place, and keeps CF-22 and F-52 to F-57 open ' + str(missing[:5]))
chk('N10', not narrow.search(cr), 'the change record does not claim approval, independent review, readiness, compliance or closure')
print(f'\nchecks {n}  failed {len(fails)}')
if fails:
    print('FAILED:', fails)
    sys.exit(1)
print('ALL M9.1 REGISTER CHECKS PASS')
