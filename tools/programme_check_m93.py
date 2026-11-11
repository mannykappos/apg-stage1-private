#!/usr/bin/env python3
"""Structural checks of the APG-M9.3 records: the finding F-62, the status rows SR-84 to SR-86, the interpretations I-93 to I-95, the carried-forward item CF-30, the contract document, the change record,
and that nothing is shown as closed and the milestones, handoff, RFC and governance records were not changed.
Python 3 standard library only; read-only.  Usage: python3 -I tools/programme_check_m93.py <package_root>   Exit 0 only if every check passes."""
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
OPEN3 = 'Corrected in APG-M9.3 (builder-implemented); open until independently verified'
OPEN2 = 'Corrected in APG-M9.2 (builder-implemented); open until independently verified'
by = {f['finding_id']: f for f in fr}
f93 = [f for f in fr if f['milestone'] == 'M9.3']
chk('Q01', [f['finding_id'] for f in f93] == ['F-62'] and [f['finding_id'] for f in fr][:62] == [f'F-{k:02d}' for k in range(1, 63)] and f93[0]['status'] == OPEN3 and f93[0]['raised_by'].startswith('Independent audit of APG-M9.2')
    and all(f93[0][k] for k in ('title', 'description', 'how_it_is_handled_here', 'linked_items')) and all(by[k]['status'] == OPEN2 for k in ('F-58', 'F-59', 'F-60', 'F-61')),
    'F-62 is recorded as raised by the independent audit of M9.2 and as "corrected in APG-M9.3 (builder-implemented); open until independently verified"; F-58 to F-61 keep their M9.2 status (the audit has not verified them)')
chk('Q01b', not any(re.search(r'\b(closed|accepted|approved|resolved)\b', f['status'], re.I) for f in fr) and all(by[k]['status'].startswith(('Corrected in', 'Handled in')) or 'open' in by[k]['status'].lower() for k in ('F-52', 'F-53', 'F-54', 'F-55', 'F-56', 'F-57')),
    'no finding is shown as closed, accepted, approved or resolved; F-52 to F-57 stay open')
s93 = [s for s in sr if s['milestone'] == 'M9.3']
chk('Q02', [s['item_id'] for s in s93] == ['SR-84', 'SR-85', 'SR-86'] and [s['evidence_ladder_status'] for s in s93] == ['Local-tested', 'Specified', 'Local-tested'] and all(s['claim_limit'] and s['evidence'] for s in s93)
    and all('no independent review has taken place' in s['claim_limit'] for s in s93) and 'CF-22, CF-25 and CF-29 stay open' in s93[0]['claim_limit'] and 'logs/m93/mutation_run_m93.log' in s93[2]['evidence'] and 'logs/m93/sabotage_m93.log' in s93[2]['evidence']
    and all(not re.search(r'\b(Independently|Accepted|Approved|Production)\b', s['evidence_ladder_status']) for s in s93),
    'SR-84 to SR-86 sit at Local-tested (the contract document at Specified), each has evidence and a claim limit saying no independent review has taken place; SR-84 says CF-22, CF-25 and CF-29 stay open')
i93 = [i for i in ir if i['milestone'] == 'M9.3']
chk('Q03', [i['interpretation_id'] for i in i93] == ['I-93', 'I-94', 'I-95'] and [i['interpretation_id'] for i in ir][:95] == [f'I-{k}' for k in range(1, 96)] and all(i['status'] == 'Retained for review - not approved' and i['reviewer_decision'] == '' and i['builder_reading'] and i['effect_if_wrong'] for i in i93),
    'I-93 to I-95 are retained for review, not approved, with no reviewer decision; each states the reading and what follows if it is wrong; the numbering is unbroken')
c = {x['cf_id']: x for x in cf}
chk('Q04', [x['cf_id'] for x in cf][:30] == [f'CF-{k:02d}' for k in range(1, 31)] and all(len(v.strip()) >= 3 for x in cf for k, v in x.items() if k != 'audit_section') and all(x['audit_section'].strip() for x in cf)
    and c['CF-25']['status'] == 'Open - not built' and c['CF-22']['status'].startswith('Open') and c['CF-29']['status'].startswith('Open - function built and tested (APG-M9.2)') and c['CF-28']['status'] == 'Open - for the auditor'
    and c['CF-30']['status'] == 'Open - for the auditor' and 'incomplete' in c['CF-30']['what_remains_open'].lower() and 'Auditor' in c['CF-30']['who_must_act'] and not any(re.search(r'\b(closed|resolved|accepted|approved)\b', x['status'], re.I) for x in cf),
    'the carried-forward register holds CF-01 to CF-30 in order with every cell filled; CF-22, CF-25 and CF-29 are unedited and open; CF-30 records the auditor\'s incomplete wrapper runs as incomplete and is open for the auditor; none is closed')
e = {x['edr_id']: x for x in eh}
m9 = next(m for m in ms if m['milestone_id'] == 'M9')
chk('Q05', [x['edr_id'] for x in eh][-1] == 'EDR-32' and e['EDR-32']['status'] == 'Open - described only' and e['EDR-32']['evidence_seen'].startswith('No Engine code') and 'EDR-31' in m9['handoff_register_entries'] and 'EDR-32' in m9['handoff_register_entries'] and m9['status'] == 'In this delivery'
    and all(next(m for m in ms if m['milestone_id'] == k)['status'] == 'Not started' for k in ('M7', 'M8', 'M10', 'M11', 'M12')),
    'EDR-32 is still described only (no Engine code seen) and no Engine entry was added; the M9 row is "In this delivery"; M7, M8 and M10 to M12 are not started')
g = {x['record_id']: x for x in gv}
chk('Q06', [x['record_id'] for x in gv] == [f'G-{k:02d}' for k in range(1, 13)] and g['G-01']['status'] == 'Recorded - RFC-01 still proposed and unnumbered' and all(g[k]['status'] == 'PROPOSED - not implemented' for k in ('G-04', 'G-05', 'G-06', 'G-07'))
    and g['G-09']['status'] == 'Recorded - nothing configured' and g['G-11']['status'] == 'In sequence - foundations not started' and len(rfc) == 1 and rfc[0]['rfc_id'] == 'RFC-01' and rfc[0]['status'].startswith('PROPOSED - not approved') and 'not yet a numbered change request' in rfc[0]['status'],
    'the governance and RFC registers are unchanged: RFC-01 unnumbered and proposed, the four baseline rules PROPOSED, no finance assumption configured, foundations not started')
claim = re.compile(r'(?<!not )(?<!no )\b(has been approved|is approved|independently reviewed|has been independently|production[- ]ready|release[- ]ready|now working|closed by|accepted by|complies with|compliant with|guaranteed|has been adopted|is adopted|verified by)\b', re.I)
new_rows = f93 + s93 + i93 + [c['CF-30']]
hits = [(r.get('finding_id') or r.get('item_id') or r.get('interpretation_id') or r.get('cf_id'), k) for r in new_rows for k, v in r.items() if claim.search(v or '')]
chk('Q07', not hits, 'no new register text claims approval, independent review, readiness, compliance, adoption or closure ' + str(hits))
doc = txt('programme/APPROVAL_REQUEST_BOUNDARY.md')
narrow = re.compile(r'\b(has been approved|is approved|has been independently (?:verified|accepted|approved|audited)|closed by|accepted by|complies with|compliant with|guaranteed|has been adopted|is adopted)\b', re.I)
secs = ('## 1. What it is for', '## 2. The three calls', '## 3. The order of checks', '## 4. One answer per request id', '## 5. Results and codes', '## 6. Audit', "## 7. Suggested mapping", '## 8. What the Engine must provide', '## 9. What this does not show')
chk('Q08', all(k in doc for k in secs) and 'revised for APG-M9.2' in doc and 'APG-M9.3' in doc and 'real UTC moment' in doc and 'strictly later' in doc and 'F-62' in doc and 'EDR-32' in doc and 'Nothing here has been independently reviewed' in doc and 'CF-22 and CF-25 stay open' in doc and 'apg/det/approval_boundary' not in doc and not narrow.search(doc),
    'the contract document (revised for M9.3) has its nine sections, says what a live session is (a real UTC moment, strictly later than now, the clock held to the same rule), names F-62, says nothing here has been independently reviewed and that CF-22 and CF-25 stay open')
cr = txt('programme/CHANGE_RECORD_APG-M9.3.md')
B = json.load(open(os.path.join(ROOT, 'regression', 'BASELINE_M92.json')))
listed = set(B['changed_in_m93']) | set(B['added_in_m93'])
missing = sorted(r for r in listed if '`' + r + '`' not in cr and not r.startswith(('logs/', 'regression/m92_snapshot/')))
csecs = ('## 1. What this release is', '## 2. The defect, and where it came from', '## 3. Files changed and added', '## 4. What the corrected check does', '## 5. Tests, run against the delivered M9.2 code first', '## 6. Results, and how each is classified', '## 7. Carried forward', '## 8. What this does not show')
chk('Q09', not missing and all(k in cr for k in csecs) and 'no independent review has taken place' in cr and 'CF-22' in cr and 'CF-29' in cr and 'F-52 to F-62' in cr and 'F-62' in cr and 'CF-30' in cr and 'incomplete' in cr and not narrow.search(cr),
    'the change record has its eight sections, names every changed or added file, names F-62 and CF-30, records the auditor\'s unfinished wrapper runs as incomplete, says no independent review has taken place, keeps CF-22, CF-25, CF-29 and F-52 to F-62 open, and claims no approval ' + str(missing[:5]))
rc = txt('RUN_COMMANDS.txt'); rm = txt('README.md')
chk('Q10', 'APG M9.3' in rc and '--group' in rc and '--ids' in rc and '# APG M9.3 --' in rm and 'not independently reviewed' in rm and 'M9.2 ZIP' in rm,
    'the run commands and the readme start with an M9.3 section; the run commands give the split-group and mutation-chunk commands; the readme says the correction is not independently reviewed and the M9.2 ZIP is unchanged')
print(f'\nchecks {n}  failed {len(fails)}')
if fails:
    print('FAILED:', fails)
    sys.exit(1)
print('ALL M9.3 REGISTER CHECKS PASS')
