#!/usr/bin/env python3
"""Structural checks of the APG-M9.2 records: the findings F-58 to F-61, the status rows SR-81 to SR-83, the interpretations I-88 to I-92, the handoff entry EDR-32, the carried-forward items CF-28 and CF-29, the M9 milestone row, the contract document, the change record,
and that nothing is shown as closed and the RFC and governance records were not changed.
Python 3 standard library only; read-only.  Usage: python3 -I tools/programme_check_m92.py <package_root>   Exit 0 only if every check passes."""
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
OPEN = 'Corrected in APG-M9.2 (builder-implemented); open until independently verified'
f92 = [f for f in fr if f['milestone'] == 'M9.2']
by = {f['finding_id']: f for f in fr}
chk('P01', [f['finding_id'] for f in f92] == ['F-58', 'F-59', 'F-60', 'F-61'] and [f['finding_id'] for f in fr][:61] == [f'F-{k:02d}' for k in range(1, 62)] and all(f['status'] == OPEN for f in f92)
    and all(f['title'] and f['description'] and f['how_it_is_handled_here'] and f['linked_items'] for f in f92)
    and all(by[k]['raised_by'].startswith('Independent audit of APG-M9.1') for k in ('F-58', 'F-59', 'F-60')) and by['F-61']['raised_by'].startswith("The builder's own review"),
    'F-58 to F-60 are recorded as raised by the independent audit of M9.1 and F-61 as found by the builder\'s own review; all four are "corrected in APG-M9.2 (builder-implemented); open until independently verified"')
chk('P01b', not any(re.search(r'\b(closed|accepted|approved|resolved)\b', f['status'], re.I) for f in fr) and all(by[k]['status'].startswith(('Corrected in', 'Handled in')) or 'open' in by[k]['status'].lower() for k in ('F-52', 'F-53', 'F-54', 'F-55', 'F-56', 'F-57')) and all('open until independently verified' in by[k]['status'] for k in ('F-53', 'F-54', 'F-55', 'F-56', 'F-57')),
    'no finding is shown as closed, accepted, approved or resolved; F-52 to F-57 stay open')
s92 = [s for s in sr if s['milestone'] == 'M9.2']
chk('P02', [s['item_id'] for s in s92] == ['SR-81', 'SR-82', 'SR-83'] and [s['evidence_ladder_status'] for s in s92] == ['Local-tested', 'Specified', 'Local-tested'] and all(s['claim_limit'] and s['evidence'] for s in s92)
    and all('no independent review has taken place' in s['claim_limit'] for s in s92) and 'EDR-32' in s92[0]['claim_limit'] and 'CF-22 and CF-25 stay open' in s92[0]['claim_limit'] and 'logs/m92/mutation_run_m92.log' in s92[2]['evidence'] and 'logs/m92/sabotage_m92.log' in s92[2]['evidence'],
    'SR-81 to SR-83 sit at Local-tested (the contract document at Specified), each has evidence and a claim limit saying no independent review has taken place; SR-81 names EDR-32 and says CF-22 and CF-25 stay open')
chk('P02b', all(not re.search(r'\b(Independently|Accepted|Approved|Production)\b', s['evidence_ladder_status']) for s in s92), 'no new status row is above Local-tested or Specified')
i92 = [i for i in ir if i['milestone'] == 'M9.2']
chk('P03', [i['interpretation_id'] for i in i92] == [f'I-{k}' for k in range(88, 93)] and all(i['status'] == 'Retained for review - not approved' and i['reviewer_decision'] == '' and i['builder_reading'] and i['effect_if_wrong'] for i in i92)
    and [i['interpretation_id'] for i in ir][:92] == [f'I-{k}' for k in range(1, 93)],
    'I-88 to I-92 are retained for review, not approved, with no reviewer decision; each states the reading and what follows if it is wrong; the interpretation numbering is unbroken')
c = {x['cf_id']: x for x in cf}
chk('P04', [x['cf_id'] for x in cf][:29] == [f'CF-{k:02d}' for k in range(1, 30)] and all(len(v.strip()) >= 3 for x in cf for k, v in x.items() if k != 'audit_section') and all(x['audit_section'].strip() for x in cf),
    'the carried-forward register holds CF-01 to CF-29 in order with every cell filled')
chk('P04b', c['CF-25']['status'] == 'Open - not built' and c['CF-22']['status'].startswith('Open') and c['CF-26']['status'].startswith('Open - function built and tested (APG-M9.1)') and c['CF-27']['status'] == 'Open - for the auditor' and c['CF-28']['status'] == 'Open - for the auditor'
    and 'incomplete' in c['CF-28']['what_remains_open'].lower() and 'Auditor' in c['CF-28']['who_must_act'] and c['CF-29']['status'].startswith('Open - function built and tested (APG-M9.2)') and 'EDR-32' in c['CF-29']['what_remains_open'] and 'No independent review has taken place' in c['CF-29']['what_remains_open'],
    'CF-22, CF-25, CF-26 and CF-27 are unedited and open; CF-28 records the auditor\'s incomplete runs as incomplete and is open for the auditor; CF-29 names EDR-32 and says no independent review has taken place')
chk('P04c', not any(re.search(r'\b(closed|resolved|accepted|approved)\b', x['status'], re.I) for x in cf), 'no carried-forward item is shown as closed, resolved, accepted or approved')
e = {x['edr_id']: x for x in eh}
m9 = next(m for m in ms if m['milestone_id'] == 'M9')
chk('P05', [x['edr_id'] for x in eh][-1] == 'EDR-32' and e['EDR-32']['port'] == 'AuditedChangePort' and e['EDR-32']['status'] == 'Open - described only' and e['EDR-32']['evidence_seen'].startswith('No Engine code') and e['EDR-32']['owner'].startswith('Amir')
    and e['EDR-31']['status'] == 'Open - described only' and 'EDR-31' in m9['handoff_register_entries'] and 'EDR-32' in m9['handoff_register_entries'] and m9['status'] == 'In this delivery'
    and all(next(m for m in ms if m['milestone_id'] == k)['status'] == 'Not started' for k in ('M7', 'M8', 'M10', 'M11', 'M12')),
    'EDR-32 is described only (no Engine code seen) and owned by the Engine; the M9 row lists EDR-31 and EDR-32 and is "In this delivery"; M7, M8 and M10 to M12 are not started')
g = {x['record_id']: x for x in gv}
chk('P06', [x['record_id'] for x in gv] == [f'G-{k:02d}' for k in range(1, 13)] and g['G-01']['status'] == 'Recorded - RFC-01 still proposed and unnumbered' and all(g[k]['status'] == 'PROPOSED - not implemented' for k in ('G-04', 'G-05', 'G-06', 'G-07'))
    and g['G-09']['status'] == 'Recorded - nothing configured' and g['G-11']['status'] == 'In sequence - foundations not started' and len(rfc) == 1 and rfc[0]['rfc_id'] == 'RFC-01' and rfc[0]['status'].startswith('PROPOSED - not approved') and 'not yet a numbered change request' in rfc[0]['status'],
    'the governance and RFC registers are unchanged: RFC-01 unnumbered and proposed, the four baseline rules PROPOSED, no finance assumption configured, foundations not started')
claim = re.compile(r'(?<!not )(?<!no )\b(has been approved|is approved|independently reviewed|has been independently|production[- ]ready|release[- ]ready|now working|closed by|accepted by|complies with|compliant with|guaranteed|has been adopted|is adopted|verified by)\b', re.I)
new_rows = f92 + s92 + i92 + [c['CF-28'], c['CF-29'], e['EDR-32']]
hits = [(r.get('finding_id') or r.get('item_id') or r.get('interpretation_id') or r.get('cf_id') or r.get('edr_id'), k) for r in new_rows for k, v in r.items() if claim.search(v or '')]
chk('P07', not hits, 'no new register text claims approval, independent review, readiness, compliance, adoption or closure ' + str(hits))
doc = txt('programme/APPROVAL_REQUEST_BOUNDARY.md')
narrow = re.compile(r'\b(has been approved|is approved|has been independently (?:verified|accepted|approved|audited)|closed by|accepted by|complies with|compliant with|guaranteed|has been adopted|is adopted)\b', re.I)
secs = ('## 1. What it is for', '## 2. The three calls', '## 3. The order of checks', '## 4. One answer per request id', '## 5. Results and codes', '## 6. Audit', "## 7. Suggested mapping", '## 8. What the Engine must provide', '## 9. What this does not show')
chk('P08', all(k in doc for k in secs) and 'revised for APG-M9.2' in doc and 'EDR-32' in doc and 'EDR-31' in doc and 'Nothing here has been independently reviewed' in doc and 'CF-22 and CF-25 stay open' in doc and 'apg/api/approval_boundary.py' in doc and 'apg/det/approval_boundary' not in doc and not narrow.search(doc),
    'the contract document (revised for M9.2) has its nine sections, names EDR-31 and EDR-32, cites the right module path, says nothing here has been independently reviewed and that CF-22 and CF-25 stay open')
cr = txt('programme/CHANGE_RECORD_APG-M9.2.md')
B = json.load(open(os.path.join(ROOT, 'regression', 'BASELINE_M91.json')))
listed = set(B['changed_in_m92']) | set(B['added_in_m92'])
missing = sorted(r for r in listed if '`' + r + '`' not in cr and not r.startswith(('logs/', 'regression/m91_snapshot/')))
csecs = ('## 1. What this release is', '## 2. The defects, and where each came from', '## 3. Files changed and added', '## 4. What the corrected boundary does', '## 5. Tests, written before the fix', '## 6. Results, and how each is classified', '## 7. Carried forward', '## 8. What this does not show')
chk('P09', not missing and all(k in cr for k in csecs) and 'no independent review has taken place' in cr and 'CF-22' in cr and 'F-52 to F-61' in cr and 'F-58' in cr and 'F-61' in cr and 'CF-28' in cr and 'incomplete' in cr,
    'the change record has its eight sections, names every changed or added file, names F-58 to F-61 and CF-28, records the auditor\'s unfinished runs as incomplete, says no independent review has taken place, and keeps CF-22 and F-52 to F-61 open ' + str(missing[:5]))
chk('P10', not narrow.search(cr), 'the change record does not claim approval, independent review, readiness, compliance or closure')
rc = txt('RUN_COMMANDS.txt'); rm = txt('README.md')
chk('P11', 'APG M9.2' in rc and '--group' in rc and '--ids' in rc and '# APG M9.2 --' in rm and 'not independently reviewed' in rm and 'M9.1 ZIP' in rm,
    'the run commands and the readme start with an M9.2 section; the run commands give the split-group and mutation-chunk commands; the readme says the corrections are not independently reviewed and the M9.1 ZIP is unchanged')
print(f'\nchecks {n}  failed {len(fails)}')
if fails:
    print('FAILED:', fails)
    sys.exit(1)
print('ALL M9.2 REGISTER CHECKS PASS')
