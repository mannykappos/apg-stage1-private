#!/usr/bin/env python3
"""Structural checks of the APG-M6.2 records: the findings F-53 and F-54, the interpretations I-65 to I-70, the status rows SR-66 to SR-69, the carried-forward register, the change record, and that the
governance records of M6.1 were not changed.  Python 3 standard library only; read-only.  Usage: python3 -I tools/programme_check_m62.py <package_root>   Exit 0 only if every check passes.
(The M3 to M6.1 register checks keep passing on the extended tables.)"""
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
OPEN_FIXED = 'Corrected in APG-M6.2 (builder-implemented); open until independently verified'
by = {f['finding_id']: f for f in fr}
f53, f54, f52 = by.get('F-53', {}), by.get('F-54', {}), by.get('F-52', {})
chk('N01', f53.get('milestone') == 'M6.2' and f53['raised_by'].startswith('Auditor') and f53['status'] == OPEN_FIXED and all(t in f53['description'] for t in ('version 1', 'version 2', 'without naming a version', 'did not cover'))
    and all(t in f53['linked_items'] for t in ('apg/det/findings.py', 'tests/test_det_proposal_binding.py', 'tools/probe_stale_proposal.py', 'F-52')) and 'STALE_PROPOSAL' in f53['how_it_is_handled_here']
    and 'no independent review has taken place' in f53['how_it_is_handled_here'] and 'F-52 also stays open' in f53['how_it_is_handled_here'] and 'unchanged' in f53['how_it_is_handled_here'],
    'F-53 records the audit reproduction, the gap in the M6.1 tests, the files, the refusal (STALE_PROPOSAL) and that it is builder-implemented with no independent review, still open, with F-52 also open; the earlier archives stay unchanged')
chk('N02', f54.get('milestone') == 'M6.2' and f54['raised_by'].startswith('Auditor') and f54['status'] == OPEN_FIXED and 'proposal_history' in f54['how_it_is_handled_here'] and 'I-69' in f54['linked_items']
    and 'no independent review has taken place' in f54['how_it_is_handled_here'], 'F-54 records the audit-trail point, the reading behind the correction (I-69) and that it is builder-implemented with no independent review, still open')
chk('N03', f52.get('status') == 'Handled in the correction release; for the auditor to confirm' and f52['milestone'] == 'M6.1', 'F-52 is unchanged (the M6.1 row is not rewritten) and not shown as closed')
i62 = [i for i in ir if i['milestone'] == 'M6.2']
chk('N04', [i['interpretation_id'] for i in i62] == [f'I-{k}' for k in range(65, 71)] and all(i['status'] == 'Retained for review - not approved' and i['reviewer_decision'] == '' for i in i62)
    and 'digest' in i62[0]['builder_reading'] and 'reviewer' in i62[1]['builder_reading'] and '14 allowed transitions' in i62[1]['builder_reading'] and 'approve_action' in i62[3]['builder_reading'] and 'proposal_history' in i62[4]['builder_reading'],
    'I-65 to I-70 are retained for review, not approved, with no reviewer decision, and state the digest reading, the reviewer route with the unchanged 14 transitions, the entry point and the history')
s62 = [s for s in sr if s['milestone'] == 'M6.2']
chk('N05', [s['item_id'] for s in s62] == ['SR-66', 'SR-67', 'SR-68', 'SR-69'] and [s['evidence_ladder_status'] for s in s62] == ['Local-tested', 'Local-tested', 'Local-tested', 'Specified'] and all(s['claim_limit'] and s['evidence'] for s in s62)
    and all('no independent review has taken place' in s['claim_limit'] for s in s62[:3]) and 'incomplete, not as a pass' in s62[2]['claim_limit'] and 'closes nothing' in s62[3]['claim_limit'],
    'SR-66 to SR-69 sit at or below Local-tested, each has evidence and a claim limit; the limits say no independent review, incomplete runs are not passes, and the register closes nothing')
chk('N06', [c['cf_id'] for c in cf][:23] == [f'CF-{k:02d}' for k in range(1, 24)] and all(len(v.strip()) >= 3 for c in cf for k, v in c.items() if k != 'audit_section') and all(c['audit_section'].strip() for c in cf), 'the carried-forward register holds CF-01 to CF-23 first and in order (later releases may append), every cell filled')
c = {x['cf_id']: x for x in cf}
chk('N07', set(x['audit_section'] for x in cf) >= {'1, 3', '5', '7.1', '7.2', '7.3', '7.4', '7.5'}
    and 'EDR-29' in c['CF-05']['linked_records'] and 'Not independently reproduced' in c['CF-05']['what_remains_open'] and 'No fix is claimed' in c['CF-05']['what_this_package_shows']
    and 'supplier invoices' in c['CF-12']['what_remains_open'] and 'backward-looking' in c['CF-09']['what_remains_open'] and 'synthetic' in c['CF-01']['what_remains_open'].lower()
    and 'event' in c['CF-04']['topic'].lower() and 'recorded_at' in c['CF-04']['what_remains_open'] and 'timed out' in c['CF-23']['what_remains_open'] and 'screen and API' in c['CF-22']['status'],
    'the register carries the audit\'s open items by section: synthetic data, ports, tenant isolation (EDR-29, not reproduced, no fix claimed), invoice-only cost, event gaps, portfolio purchasing, the approval-screen gate and the verification limits')
chk('N08', all(x['status'] in ('Open - carried forward', 'For the auditor to confirm', 'Followed - nothing added', 'Open - for the auditor', 'Open - not built') or x['status'].startswith('Open - function built') for x in cf)
    and not any(re.search(r'\b(closed|resolved|accepted|approved)\b', x['status'], re.I) for x in cf), 'no carried-forward item is shown as closed, resolved, accepted or approved')
g = {x['record_id']: x for x in gv}
chk('N09', [x['record_id'] for x in gv] == [f'G-{k:02d}' for k in range(1, 13)] and g['G-01']['status'] == 'Recorded - RFC-01 still proposed and unnumbered' and all(g[k]['status'] == 'PROPOSED - not implemented' for k in ('G-04', 'G-05', 'G-06', 'G-07'))
    and g['G-10']['status'] == 'Corrected in APG-M6.1; for the auditor to confirm' and g['G-11']['status'] == 'In sequence - foundations not started' and g['G-09']['status'] == 'Recorded - nothing configured',
    'the governance register of M6.1 is unchanged: RFC-01 unnumbered, the four baseline rules PROPOSED, no finance assumption configured, foundations not started')
chk('N10', len(rfc) == 1 and rfc[0]['rfc_id'] == 'RFC-01' and rfc[0]['status'].startswith('PROPOSED - not approved') and 'not yet a numbered change request' in rfc[0]['status']
    and next(m for m in ms if m['milestone_id'] == 'M7')['status'] == 'Not started', 'RFC-01 is still PROPOSED, not approved and not numbered; M7 is not started')
claim = re.compile(r'(?<!not )(?<!no )\b(has been approved|is approved|independently reviewed|has been independently|production[- ]ready|release[- ]ready|now working|closed by|accepted by|complies with|compliant with|guaranteed|has been adopted|is adopted)\b', re.I)
new_rows = [f53, f54] + i62 + s62 + cf
hits = [(r.get('finding_id') or r.get('interpretation_id') or r.get('item_id') or r.get('cf_id'), k) for r in new_rows for k, v in r.items() if claim.search(v or '')]
chk('N11', not hits, 'no new register text claims approval, independent review, readiness, compliance, adoption or closure ' + str(hits))
chk('N12', not any(re.search(r'\b(closed|resolved|accepted|approved)\b', f['status'], re.I) for f in fr), 'no finding in the register is shown as closed, resolved, accepted or approved')
cr = txt('programme/CHANGE_RECORD_APG-M6.2.md')
B = json.load(open(os.path.join(ROOT, 'regression', 'BASELINE_M61.json')))
listed = set(B['changed_in_m62']) | set(B['added_in_m62'])
missing = sorted(r for r in listed if '`' + r + '`' not in cr and not r.startswith('logs/'))
secs = ('## 1. The defect', '## 2. Impact', '## 3. Files changed', '## 4. What the correction does', '## 5. Tests', '## 6. Results, and how each is classified', '## 7. Carried forward', '## 8. What this does not show')
chk('N13', not missing and all(k in cr for k in secs) and 'no independent review has taken place' in cr, 'the change record has the defect, impact, exact files changed, behaviour, tests, classified results, carried-forward and limits sections, and names every changed or added file ' + str(missing[:5]))
print(f'\nchecks {n}  failed {len(fails)}')
if fails:
    print('FAILED:', fails)
    sys.exit(1)
print('ALL M6.2 REGISTER CHECKS PASS')
