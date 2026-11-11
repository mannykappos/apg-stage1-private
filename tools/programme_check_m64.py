#!/usr/bin/env python3
"""Structural checks of the APG-M6.4 records: the finding F-56, the interpretations I-75 to I-78, the status rows SR-72 and SR-73, the carried-forward row CF-25, the change record, and that the records of
M6.1, M6.2 and M6.3 were not changed.  Python 3 standard library only; read-only.  Usage: python3 -I tools/programme_check_m64.py <package_root>   Exit 0 only if every check passes.
(The M3 to M6.3 register checks keep passing on the extended tables.)"""
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
OPEN_FIXED = 'Corrected in APG-M6.4 (builder-implemented); open until independently verified'
by = {f['finding_id']: f for f in fr}
f56 = by.get('F-56', {})
chk('N01', f56.get('milestone') == 'M6.4' and f56['raised_by'].startswith('Builder') and f56['status'] == OPEN_FIXED and all(t in f56['description'] for t in ('SAME evidence', 'approve_action', 'never saw', 'F-53', 'builder\'s omission', 'did not report'))
    and all(t in f56['linked_items'] for t in ('apg/det/findings.py', 'tests/test_det_proposal_identity.py', 'tools/probe_proposal_swap.py', 'CF-22')) and 'PROPOSAL_CHANGED' in f56['how_it_is_handled_here'] and 'APPROVAL_TOKEN_REQUIRED' in f56['how_it_is_handled_here']
    and 'no independent review has taken place' in f56['how_it_is_handled_here'] and 'F-52, F-53, F-54 and F-55 also stay open' in f56['how_it_is_handled_here'] and 'unchanged' in f56['how_it_is_handled_here'],
    'F-56 records the swap scenario, that the builder found it, that the earlier audits did not report it, the files, both refusals, that it is builder-implemented with no independent review and still open, with F-52 to F-55 also open; the earlier archives stay unchanged')
chk('N02', all(by[k]['milestone'] == m and by[k]['status'] == s_ for k, m, s_ in (('F-52', 'M6.1', 'Handled in the correction release; for the auditor to confirm'), ('F-53', 'M6.2', 'Corrected in APG-M6.2 (builder-implemented); open until independently verified'),
                                                                                       ('F-54', 'M6.2', 'Corrected in APG-M6.2 (builder-implemented); open until independently verified'), ('F-55', 'M6.3', 'Corrected in APG-M6.3 (builder-implemented); open until independently verified'))),
    'F-52 to F-55 are unchanged (earlier rows are not rewritten) and not shown as closed')
i64 = [i for i in ir if i['milestone'] == 'M6.4']
chk('N03', [i['interpretation_id'] for i in i64] == [f'I-{k}' for k in range(75, 79)] and all(i['status'] == 'Retained for review - not approved' and i['reviewer_decision'] == '' for i in i64)
    and 'new proposal' in i64[0]['builder_reading'] and 'fails closed' in i64[1]['builder_reading'] and 'approved_proposal' in i64[2]['builder_reading'] and 'PROPOSAL_CHANGED' in i64[3]['builder_reading'],
    'I-75 to I-78 are retained for review, not approved, with no reviewer decision, and state what makes a proposal the same one, the entry point rule, approvals made before M6.4 and the order of refusals')
s64 = [s for s in sr if s['milestone'] == 'M6.4']
chk('N04', [s['item_id'] for s in s64] == ['SR-72', 'SR-73'] and [s['evidence_ladder_status'] for s in s64] == ['Local-tested', 'Local-tested'] and all(s['claim_limit'] and s['evidence'] for s in s64)
    and all('no independent review has taken place' in s['claim_limit'] for s in s64) and 'incomplete, not as a pass' in s64[1]['claim_limit'], 'SR-72 and SR-73 sit at Local-tested, each has evidence and a claim limit; the limits say no independent review and that incomplete runs are not passes')
chk('N05', [c['cf_id'] for c in cf][:25] == [f'CF-{k:02d}' for k in range(1, 26)] and all(len(v.strip()) >= 3 for c in cf for k, v in c.items() if k != 'audit_section') and all(c['audit_section'].strip() for c in cf), 'the carried-forward register holds CF-01 to CF-25 in order, every cell filled')
c25 = next(c for c in cf if c['cf_id'] == 'CF-25')
chk('N06', c25['status'] == 'Open - not built' and 'CF-22 stays open' in c25['what_remains_open'] and 'EDR-29' in c25['what_remains_open'] and 'replay' in c25['what_remains_open'] and 'CF-22' in c25['linked_records'] and 'F-56' in c25['linked_records']
    and 'No project-level check exists' in c25['what_this_package_shows'], 'CF-25 records that the approval request boundary (replay-safe requests, project authorisation, boundary audit) is not built and that CF-22 stays open')
chk('N07', all(c['status'] in ('Open - carried forward', 'For the auditor to confirm', 'Followed - nothing added', 'Open - for the auditor', 'Open - not built') or c['status'].startswith('Open - function built') for c in cf)
    and not any(re.search(r'\b(closed|resolved|accepted|approved)\b', c['status'], re.I) for c in cf), 'no carried-forward item is shown as closed, resolved, accepted or approved')
g = {x['record_id']: x for x in gv}
chk('N08', [x['record_id'] for x in gv] == [f'G-{k:02d}' for k in range(1, 13)] and g['G-01']['status'] == 'Recorded - RFC-01 still proposed and unnumbered' and all(g[k]['status'] == 'PROPOSED - not implemented' for k in ('G-04', 'G-05', 'G-06', 'G-07'))
    and g['G-09']['status'] == 'Recorded - nothing configured' and g['G-11']['status'] == 'In sequence - foundations not started', 'the governance register is unchanged: RFC-01 unnumbered, the four baseline rules PROPOSED, no finance assumption configured, foundations not started')
chk('N09', len(rfc) == 1 and rfc[0]['rfc_id'] == 'RFC-01' and rfc[0]['status'].startswith('PROPOSED - not approved') and 'not yet a numbered change request' in rfc[0]['status']
    and next(m for m in ms if m['milestone_id'] == 'M7')['status'] == 'Not started', 'RFC-01 is still PROPOSED, not approved and not numbered; M7 is not started')
claim = re.compile(r'(?<!not )(?<!no )\b(has been approved|is approved|independently reviewed|has been independently|production[- ]ready|release[- ]ready|now working|closed by|accepted by|complies with|compliant with|guaranteed|has been adopted|is adopted)\b', re.I)
new_rows = [f56] + i64 + s64 + [c25]
hits = [(r.get('finding_id') or r.get('interpretation_id') or r.get('item_id') or r.get('cf_id'), k) for r in new_rows for k, v in r.items() if claim.search(v or '')]
chk('N10', not hits, 'no new register text claims approval, independent review, readiness, compliance, adoption or closure ' + str(hits))
chk('N11', not any(re.search(r'\b(closed|resolved|accepted|approved)\b', f['status'], re.I) for f in fr), 'no finding in the register is shown as closed, resolved, accepted or approved')
cr = txt('programme/CHANGE_RECORD_APG-M6.4.md')
B = json.load(open(os.path.join(ROOT, 'regression', 'BASELINE_M63.json')))
listed = set(B['changed_in_m64']) | set(B['added_in_m64'])
missing = sorted(r for r in listed if '`' + r + '`' not in cr and not r.startswith('logs/'))
secs = ('## 1. The defect', '## 2. Impact', '## 3. Files changed', '## 4. What the correction does', '## 5. Tests', '## 6. Results, and how each is classified', '## 7. Carried forward', '## 8. What this does not show')
chk('N12', not missing and all(k in cr for k in secs) and 'no independent review has taken place' in cr, 'the change record has the defect, impact, exact files changed, behaviour, tests, classified results, carried-forward and limits sections, and names every changed or added file ' + str(missing[:5]))
print(f'\nchecks {n}  failed {len(fails)}')
if fails:
    print('FAILED:', fails)
    sys.exit(1)
print('ALL M6.4 REGISTER CHECKS PASS')
