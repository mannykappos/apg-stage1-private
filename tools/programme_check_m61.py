#!/usr/bin/env python3
"""Structural checks of the APG-M6.1 records: the correction finding and its interpretations, the status rows, the Engine #17 governance register and record, the change record.  Python 3 standard
library only; read-only.  Usage: python3 -I tools/programme_check_m61.py <package_root>   Exit 0 only if every check passes.  (The M3 to M6 register checks keep passing on the extended tables.)"""
import csv, hashlib, json, os, re, sys
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


fr, ir, sr, gv, rfc = (rd('programme/' + f) for f in ('FINDINGS_REGISTER.csv', 'INTERPRETATIONS_REGISTER.csv', 'STATUS_REGISTER.csv', 'E17_GOVERNANCE_REGISTER.csv', 'RFC_REGISTER.csv'))
BASE = '487becabdf47796800937d13a706a19b63b7b8230ecc5354b2f01a647ae5d960'
f52 = next((f for f in fr if f['finding_id'] == 'F-52'), {})
chk('N01', f52.get('milestone') == 'M6.1' and f52['raised_by'].startswith('Builder') and 'version 1 to version 2' in f52['description'] and 'E17-A23' in f52['description'] and 'apg/det/findings.py' in f52['linked_items']
    and 'tests/test_det_approval_binding.py' in f52['linked_items'] and f52['status'] == 'Handled in the correction release; for the auditor to confirm' and 'no independent review has taken place' in f52['how_it_is_handled_here']
    and 'unchanged' in f52['how_it_is_handled_here'], 'F-52 records the defect, the gate that found it, the files, and the correction as builder-implemented with no independent review, with the auditor to confirm; the M5 and M6 archives stay unchanged')
i6 = [i for i in ir if i['milestone'] == 'M6.1']
chk('N02', [i['interpretation_id'] for i in i6] == [f'I-{k}' for k in range(59, 65)] and all(i['status'] == 'Retained for review - not approved' and i['reviewer_decision'] == '' for i in i6)
    and 'digest' in i6[0]['builder_reading'] and 'in_progress' in i6[1]['builder_reading'] and 'STALE_APPROVAL' in i6[3]['builder_reading'], 'I-59 to I-64 are retained for review, not approved, with no reviewer decision, and state the digest reading, the in-progress reading and the stale-version refusal')
s6 = [s for s in sr if s['milestone'] == 'M6.1']
chk('N03', [s['item_id'] for s in s6] == ['SR-62', 'SR-63', 'SR-64', 'SR-65'] and [s['evidence_ladder_status'] for s in s6] == ['Local-tested', 'Local-tested', 'Specified', 'Research record'] and all(s['claim_limit'] and s['evidence'] for s in s6)
    and 'no independent review has taken place' in s6[0]['claim_limit'] and 'PROPOSED' in s6[2]['claim_limit'] and 'not an independent audit' in s6[3]['claim_limit'], 'SR-62 to SR-65 sit at or below Local-tested, each has evidence and a claim limit, and the limits say no independent review, proposed only, and not an independent audit')
chk('N04', [g['record_id'] for g in gv] == [f'G-{k:02d}' for k in range(1, 13)] and all(len(v.strip()) >= 4 for g in gv for v in g.values()), 'the Engine #17 governance register holds G-01 to G-12 in order, every cell filled')
g = {x['record_id']: x for x in gv}
chk('N05', g['G-01']['status'] == 'Recorded - RFC-01 still proposed and unnumbered' and all(g[k]['status'] == 'PROPOSED - not implemented' for k in ('G-04', 'G-05', 'G-06', 'G-07')) and g['G-10']['status'] == 'Corrected in APG-M6.1; for the auditor to confirm'
    and g['G-11']['status'] == 'In sequence - foundations not started' and g['G-09']['status'] == 'Recorded - nothing configured', 'RFC-01 is unnumbered, the four baseline rules are PROPOSED and not implemented, no finance assumption is configured, the foundations are not started, the correction waits for the auditor')
claim = re.compile(r'(?<!not )(?<!no )\b(has been approved|is approved|independently reviewed|has been independently|production[- ]ready|release[- ]ready|now working|closed by|accepted by|complies with|compliant with|guaranteed|has been adopted|is adopted)\b', re.I)
new_rows = [f52] + i6 + s6 + gv
hits = [(r.get('finding_id') or r.get('interpretation_id') or r.get('item_id') or r.get('record_id'), k) for r in new_rows for k, v in r.items() if claim.search(v or '')]
chk('N06', not hits, 'no new register text claims approval, independent review, readiness, compliance, adoption or closure ' + str(hits))
chk('N07', len(rfc) == 1 and rfc[0]['rfc_id'] == 'RFC-01' and rfc[0]['status'].startswith('PROPOSED - not approved') and 'not yet a numbered change request' in rfc[0]['status'], 'RFC-01 is still PROPOSED, not approved and not numbered')
rec = txt('programme/E17_GOVERNANCE_RECORD.md')
chk('N08', BASE in rec and all(k in rec for k in ('V1 value engineering', 'V2 quantity and waste', 'V3 payment terms', 'V4 portfolio aggregation', 'None has happened', 'Not an approval of RFC-01', 'Draft annex'))
    and rec.count('PROPOSED') >= 2 and 'last paid rate' in rec, 'the governance record keeps the locked-baseline hash, the four vector rules as proposed, the approvals-not-given statement and the last-paid-rate rule')
cr = txt('programme/CHANGE_RECORD_APG-M6.1.md')
B = json.load(open(os.path.join(ROOT, 'regression', 'BASELINE_M6.json')))
listed = set(B['changed_in_m61']) | set(B['added_in_m61'])
missing = sorted(r for r in listed if '`' + r + '`' not in cr and not r.startswith('logs/'))
chk('N09', not missing and all(k in cr for k in ('## 1. The defect', '## 2. Impact', '## 3. Files changed', '## 4. What the correction does', '## 5. Tests', '## 6. What this does not show')), 'the change record has the defect, impact, exact files changed, behaviour, tests and limits sections, and names every changed or added file ' + str(missing[:5]))
ph = os.path.join(ROOT, 'programme', 'E17_PHASE_0_REPOSITORY_DISCOVERY.md')
chk('N10', os.path.exists(ph) and hashlib.sha256(open(ph, 'rb').read()).hexdigest() == 'fb25d5bfd27b6a00cdd55834b326099b1c3aa6d628beb684d52742173bf4a70e', 'the Phase 0 report in the package is the one delivered, by hash')
print(f'\nchecks {n}  failed {len(fails)}')
if fails:
    print('FAILED:', fails)
    sys.exit(1)
print('ALL M6.1 REGISTER CHECKS PASS')
