#!/usr/bin/env python3
"""Regression protection for the delivered M2 package.  Usage: python3 -I tools/run_regression_m3.py
 1. every M2 file that M3 must not change is byte-identical to its recorded SHA-256 (regression/BASELINE_M2.json);
 2. the programme tables differ from their delivered M2 versions only in the ways M3 is allowed to change them;
 3. the auditor's M2 findings and the interpretations I-1..I-5 are preserved and not marked approved or closed;
 4. the M2 regression tool, the M0/M1 checks, the M2 golden cases and the M2 demonstration still pass;
 5. the M3 golden cases and demonstration still give the recorded answers.
Later milestones keep this tool and add their own baselines; a change that moves any of this must be recorded and reviewed, not silently accepted."""
import csv, hashlib, json, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
rd = lambda p: list(csv.DictReader(open(p, encoding='utf-8', newline='')))
bad = []
def chk(i, ok, t):
    print(('PASS ' if ok else 'FAIL ') + i + ' ' + t)
    if not ok: bad.append(i)
B = json.load(open(os.path.join(ROOT, 'regression', 'BASELINE_M2.json')))
diff = [rel for rel, h in B['frozen'].items() if not os.path.exists(os.path.join(ROOT, rel)) or sha(os.path.join(ROOT, rel)) != h]
chk('M01', not diff, f"{len(B['frozen'])} M2 files are byte-identical to the delivered M2 package " + str(diff[:5]))
snap = lambda n: rd(os.path.join(ROOT, 'regression', 'm2_snapshot', n))
cur = lambda n: rd(os.path.join(ROOT, 'regression', 'm3_snapshot', n))   # M4: the M3 tables as delivered (the live tables are checked by run_regression_m4.py)
chk('M02', all(sha(os.path.join(ROOT, 'regression', 'm2_snapshot', os.path.basename(rel))) == B['updated_in_m3'][rel] for rel in B['updated_in_m3'] if rel.startswith('programme/')), 'the stored M2 snapshots of the programme tables equal the delivered M2 hashes')
a, b = snap('PROGRAMME_MILESTONES.csv'), cur('PROGRAMME_MILESTONES.csv')
ok = len(a) == len(b) and all(x['milestone_id'] == y['milestone_id'] and all(x[k] == y[k] for k in x if k not in ('status', 'handoff_register_entries')) for x, y in zip(a, b))
ok = ok and all(x['handoff_register_entries'] == y['handoff_register_entries'] for x, y in zip(a, b) if x['milestone_id'] != 'M3')
m3, m3o = next(y for y in b if y['milestone_id'] == 'M3'), next(x for x in a if x['milestone_id'] == 'M3')
ok = ok and m3['handoff_register_entries'].startswith(m3o['handoff_register_entries'])
want = {f'M{i}': 'Delivered - builder-checked' for i in range(3)}; want['M3'] = 'In this delivery'
ok = ok and all(y['status'] == want.get(y['milestone_id'], 'Not started') for y in b)
chk('M03', ok, 'milestone rows: only status and the M3 handoff list changed; M3 only added entries; M0-M2 delivered, M3 in this delivery, nothing later started')
a, b = snap('ENGINE_HANDOFF_REGISTER.csv'), cur('ENGINE_HANDOFF_REGISTER.csv')
ok = len(b) >= len(a)
for x, y in zip(a, b):
    allowed = {'status', 'contract_test', 'decisions_for_amir'} if x['edr_id'] in ('EDR-04', 'EDR-07') else set()
    ok = ok and x['edr_id'] == y['edr_id'] and all(x[k] == y[k] for k in x if k not in allowed)
    if x['edr_id'] in ('EDR-04', 'EDR-07'):
        ok = ok and y['status'] == 'Open - contract test written' and 'written in M3' in y['contract_test']
new = b[len(a):]
newids = [y['edr_id'] for y in new]
ok = ok and newids == sorted(newids) and all(y['status'] == 'Open - described only' and y['evidence_seen'].startswith('No Engine code') for y in new) and all(i in m3['handoff_register_entries'] for i in newids)
chk('M04', ok, f'handoff register: M2 entries unchanged apart from EDR-04 and EDR-07 (contract test written); new entries {newids} appended and listed under M3')
a, b = snap('STATUS_REGISTER.csv'), cur('STATUS_REGISTER.csv')
chk('M05', b[:len(a)] == a and len(b) > len(a) and all(r['milestone'] == 'M3' for r in b[len(a):]) and [r['item_id'] for r in b] == [f'SR-{i:02d}' for i in range(1, len(b) + 1)], 'status register: the M2 rows are unchanged and M3 rows were appended')
fr = rd(os.path.join(ROOT, 'programme', 'FINDINGS_REGISTER.csv')); ir = rd(os.path.join(ROOT, 'programme', 'INTERPRETATIONS_REGISTER.csv'))
txt = {f['finding_id']: ' '.join(f.values()) for f in fr}
aud = {f['finding_id'] for f in fr if f['raised_by'].startswith('Auditor')}
chk('M06', {'F-01', 'F-02', 'F-03', 'F-04'} <= aud and '96 of the 101' in txt['F-01'] and 'DEC-A1-8' in txt['F-01'] and 'EDR-21' in txt['F-02'] and 'EDR-20' in txt['F-03']
    and not any(re.search(r'\b(closed|accepted|approved|resolved)\b', f['status'], re.I) for f in fr), 'the auditor findings (96 of 101 materiality, audit tail rewrite, direct-write gap, wrapper time) are preserved and none is shown as closed')
ids = [i['interpretation_id'] for i in ir]
chk('M07', ids[:5] == ['I-1', 'I-2', 'I-3', 'I-4', 'I-5'] and all(i['status'] == 'Retained for review - not approved' and i['reviewer_decision'] == '' for i in ir) and 'closure evidence' in ir[0]['auditor_note'] and 'platform roles' in ir[1]['auditor_note'],
    'interpretations I-1 to I-5 are retained for review and not approved; I-1 and I-2 carry the auditor notes; no reviewer decision has been filled in by the builder')
for name, args, marker, cid, text in (('run_regression.py', [], 'REGRESSION OK', 'M08', 'the M2 regression tool (M0/M1 files, M1 to M2 table steps, M0/M1 checks, M2 golden, M2 demonstration) still passes'),
                                      ('run_golden_m3.py', [], 'GOLDEN OK', 'M09', 'the M3 golden cases still give the recorded answers and agree with the independent oracle'),
                                      ('run_demo_m3.py', ['--check'], 'DEMO OUTPUT MATCHES', 'M10', 'the M3 narrated demonstration still prints exactly the recorded output')):
    r = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', name), *args], capture_output=True, text=True, cwd=ROOT)
    ok = r.returncode == 0 and marker in r.stdout
    chk(cid, ok, text)
print(f'\nregression checks failed {len(bad)}')
print('REGRESSION OK' if not bad else 'REGRESSION FAILURE')
sys.exit(1 if bad else 0)
