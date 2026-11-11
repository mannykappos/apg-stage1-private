#!/usr/bin/env python3
"""Structural checks of the APG-M6.5 records: the finding F-57, the interpretations I-79 and I-80, the status rows SR-74 and SR-75, the change record, and that the records of M6.1 to M6.4 were not changed.
Python 3 standard library only; read-only.  Usage: python3 -I tools/programme_check_m65.py <package_root>   Exit 0 only if every check passes.  (The M3 to M6.4 register checks keep passing on the extended tables.)"""
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


fr, ir, sr, gv, rfc, cf, ms = (rd('programme/' + f) for f in ('FINDINGS_REGISTER.csv', 'INTERPRETATIONS_REGISTER.csv', 'STATUS_REGISTER.csv', 'E17_GOVERNANCE_REGISTER.csv', 'RFC_REGISTER.csv', 'CARRIED_FORWARD_REGISTER.csv', 'PROGRAMME_MILESTONES.csv'))
OPEN_FIXED = 'Corrected in APG-M6.5 (builder-implemented); open until independently verified'
by = {f['finding_id']: f for f in fr}
f57 = by.get('F-57', {})
chk('N01', f57.get('milestone') == 'M6.5' and f57['raised_by'].startswith('Independent audit of APG-M6.4') and f57['status'] == OPEN_FIXED
    and all(t in f57['description'] for t in ('lower-level', 'bypassed', 'seven incomplete combinations', 'I-76', "builder\'s omission", 'F-56'))
    and all(t in f57['linked_items'] for t in ('apg/det/findings.py', 'tests/test_det_transition_gate.py', 'tools/probe_transition_bypass.py', 'CF-22'))
    and all(t in f57['how_it_is_handled_here'] for t in ('APPROVAL_TOKEN_REQUIRED', 'APPROVAL_NOT_CURRENT', 'no independent review has taken place', 'F-52, F-53, F-54, F-55 and F-56 also stay open', 'CF-22 stays open')),
    'F-57 records the bypass of the lower-level call, that the audit reported it and the builder reproduced it, that M6.4 left the arguments optional (I-76), the files, the refusals, that it is builder-implemented with no independent review and still open, with F-52 to F-56 and CF-22 also open')
chk('N02', all(by[k]['milestone'] == m and by[k]['status'] == s_ for k, m, s_ in (('F-52', 'M6.1', 'Handled in the correction release; for the auditor to confirm'), ('F-53', 'M6.2', 'Corrected in APG-M6.2 (builder-implemented); open until independently verified'),
                                                                                       ('F-54', 'M6.2', 'Corrected in APG-M6.2 (builder-implemented); open until independently verified'), ('F-55', 'M6.3', 'Corrected in APG-M6.3 (builder-implemented); open until independently verified'),
                                                                                       ('F-56', 'M6.4', 'Corrected in APG-M6.4 (builder-implemented); open until independently verified'))),
    'F-52 to F-56 are unchanged (earlier rows are not rewritten) and not shown as closed')
i65 = [i for i in ir if i['milestone'] == 'M6.5']
chk('N03', [i['interpretation_id'] for i in i65] == ['I-79', 'I-80'] and all(i['status'] == 'Retained for review - not approved' and i['reviewer_decision'] == '' for i in i65)
    and 'I-76' in i65[0]['builder_reading'] and 'withdrawn' in i65[0]['builder_reading'] and 'append-only' in i65[0]['builder_reading'] and 'APPROVAL_NOT_CURRENT' in i65[1]['builder_reading'],
    'I-79 and I-80 are retained for review, not approved, with no reviewer decision; I-79 withdraws the reading I-76 without rewriting it, I-80 states the re-check on starting the action')
i76 = next(i for i in ir if i['interpretation_id'] == 'I-76')
chk('N03b', i76['milestone'] == 'M6.4' and i76['status'] == 'Retained for review - not approved' and 'keeps its optional arguments' in i76['builder_reading'], 'I-76 is kept as it was written in M6.4 (earlier rows are append-only); I-79 withdraws it')
s65 = [s for s in sr if s['milestone'] == 'M6.5']
chk('N04', [s['item_id'] for s in s65] == ['SR-74', 'SR-75'] and [s['evidence_ladder_status'] for s in s65] == ['Local-tested', 'Local-tested'] and all(s['claim_limit'] and s['evidence'] for s in s65)
    and all('no independent review has taken place' in s['claim_limit'] for s in s65) and 'incomplete, not as a pass' in s65[1]['claim_limit'], 'SR-74 and SR-75 sit at Local-tested, each has evidence and a claim limit; the limits say no independent review and that incomplete runs are not passes')
chk('N05', [c['cf_id'] for c in cf][:25] == [f'CF-{k:02d}' for k in range(1, 26)] and all(len(v.strip()) >= 3 for c in cf for k, v in c.items() if k != 'audit_section') and all(c['audit_section'].strip() for c in cf),
    'the carried-forward register still holds CF-01 to CF-25 in order, every cell filled (no row added or changed in M6.5; later releases may append)')
c = {x['cf_id']: x for x in cf}
chk('N06', c['CF-25']['status'] == 'Open - not built' and 'CF-22 stays open' in c['CF-25']['what_remains_open'] and c['CF-22']['status'].startswith('Open'),
    'CF-22 stays open and CF-25 (the approval request boundary) stays not built')
chk('N07', all(x['status'] in ('Open - carried forward', 'For the auditor to confirm', 'Followed - nothing added', 'Open - for the auditor', 'Open - not built') or x['status'].startswith('Open - function built') for x in cf)
    and not any(re.search(r'\b(closed|resolved|accepted|approved)\b', x['status'], re.I) for x in cf), 'no carried-forward item is shown as closed, resolved, accepted or approved')
g = {x['record_id']: x for x in gv}
chk('N08', [x['record_id'] for x in gv] == [f'G-{k:02d}' for k in range(1, 13)] and g['G-01']['status'] == 'Recorded - RFC-01 still proposed and unnumbered' and all(g[k]['status'] == 'PROPOSED - not implemented' for k in ('G-04', 'G-05', 'G-06', 'G-07'))
    and g['G-09']['status'] == 'Recorded - nothing configured' and g['G-11']['status'] == 'In sequence - foundations not started', 'the governance register is unchanged: RFC-01 unnumbered, the four baseline rules PROPOSED, no finance assumption configured, foundations not started')
chk('N09', len(rfc) == 1 and rfc[0]['rfc_id'] == 'RFC-01' and rfc[0]['status'].startswith('PROPOSED - not approved') and 'not yet a numbered change request' in rfc[0]['status']
    and next(m for m in ms if m['milestone_id'] == 'M7')['status'] == 'Not started', 'RFC-01 is still PROPOSED, not approved and not numbered; M7 is not started')
claim = re.compile(r'(?<!not )(?<!no )\b(has been approved|is approved|independently reviewed|has been independently|production[- ]ready|release[- ]ready|now working|closed by|accepted by|complies with|compliant with|guaranteed|has been adopted|is adopted)\b', re.I)
new_rows = [f57] + i65 + s65
hits = [(r.get('finding_id') or r.get('interpretation_id') or r.get('item_id'), k) for r in new_rows for k, v in r.items() if claim.search(v or '')]
chk('N10', not hits, 'no new register text claims approval, independent review, readiness, compliance, adoption or closure ' + str(hits))
chk('N11', not any(re.search(r'\b(closed|resolved|accepted|approved)\b', f['status'], re.I) for f in fr), 'no finding in the register is shown as closed, resolved, accepted or approved')
cr = txt('programme/CHANGE_RECORD_APG-M6.5.md')
B = json.load(open(os.path.join(ROOT, 'regression', 'BASELINE_M64.json')))
listed = set(B['changed_in_m65']) | set(B['added_in_m65'])
missing = sorted(r for r in listed if '`' + r + '`' not in cr and not r.startswith('logs/'))
secs = ('## 1. The defect', '## 2. Impact', '## 3. Files changed', '## 4. What the correction does', '## 5. Tests', '## 6. Results, and how each is classified', '## 7. Carried forward', '## 8. What this does not show')
chk('N12', not missing and all(k in cr for k in secs) and 'no independent review has taken place' in cr, 'the change record has the defect, impact, exact files changed, behaviour, tests, classified results, carried-forward and limits sections, and names every changed or added file ' + str(missing[:5]))
chk('N13', 'assertions that were changed' in cr and 'every other assertion is kept' in cr, 'the change record lists the test assertions that were changed and says that every other assertion is kept')
print(f'\nchecks {n}  failed {len(fails)}')
if fails:
    print('FAILED:', fails)
    sys.exit(1)
print('ALL M6.5 REGISTER CHECKS PASS')
