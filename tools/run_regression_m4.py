#!/usr/bin/env python3
"""Regression protection for the delivered M3 package.  Usage: python3 -I tools/run_regression_m4.py
 1. every M3 file that M4 must not change is byte-identical to its recorded SHA-256 (regression/BASELINE_M3.json);
 2. the programme tables differ from their delivered M3 versions only in the ways M4 is allowed to change them (rows are appended; M3 rows, findings and interpretations are untouched);
 3. the M3 regression tool (which itself protects M2 and M0/M1) still passes;
 4. the M4 golden cases and demonstration still give the recorded answers.
Later milestones keep this tool and add their own baselines; a change that moves any of this must be recorded and reviewed, not silently accepted."""
import csv, hashlib, json, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
rd = lambda p: list(csv.DictReader(open(p, encoding='utf-8', newline='')))
bad = []
def chk(i, ok, t):
    print(('PASS ' if ok else 'FAIL ') + i + ' ' + t)
    if not ok: bad.append(i)
B = json.load(open(os.path.join(ROOT, 'regression', 'BASELINE_M3.json')))
diff = [rel for rel, h in B['frozen'].items() if not os.path.exists(os.path.join(ROOT, rel)) or sha(os.path.join(ROOT, rel)) != h]
chk('G01', not diff, f"{len(B['frozen'])} M3 files are byte-identical to the delivered M3 package " + str(diff[:5]))
snap = lambda n: rd(os.path.join(ROOT, 'regression', 'm3_snapshot', n))
cur = lambda n: rd(os.path.join(ROOT, 'regression', 'm4_snapshot', n))   # M5: the M4 tables as delivered (the live tables are checked by run_regression_m5.py)
chk('G02', all(sha(os.path.join(ROOT, 'regression', 'm3_snapshot', os.path.basename(rel))) == B['updated_in_m4'][rel] for rel in B['updated_in_m4'] if rel.startswith('programme/')), 'the stored M3 snapshots of the programme tables equal the delivered M3 hashes')
a, b = snap('PROGRAMME_MILESTONES.csv'), cur('PROGRAMME_MILESTONES.csv')
ok = len(a) == len(b) and all(x['milestone_id'] == y['milestone_id'] and all(x[k] == y[k] for k in x if k not in ('status', 'handoff_register_entries')) for x, y in zip(a, b))
ok = ok and all(x['handoff_register_entries'] == y['handoff_register_entries'] for x, y in zip(a, b) if x['milestone_id'] != 'M4')
m4, m4o = next(y for y in b if y['milestone_id'] == 'M4'), next(x for x in a if x['milestone_id'] == 'M4')
ok = ok and m4['handoff_register_entries'].startswith(m4o['handoff_register_entries'])
want = {f'M{i}': 'Delivered - builder-checked' for i in range(4)}; want['M4'] = 'In this delivery'
ok = ok and all(y['status'] == want.get(y['milestone_id'], 'Not started') for y in b)
chk('G03', ok, 'milestone rows: only status and the M4 handoff list changed; M4 only added entries; M0-M3 delivered, M4 in this delivery, nothing later started')
a, b = snap('ENGINE_HANDOFF_REGISTER.csv'), cur('ENGINE_HANDOFF_REGISTER.csv')
newids = [y['edr_id'] for y in b[len(a):]]
ok = len(b) > len(a) and b[:len(a)] == a and newids == sorted(newids) and all(y['status'] == 'Open - described only' and y['evidence_seen'].startswith('No Engine code') for y in b[len(a):]) and all(i in m4['handoff_register_entries'] for i in newids)
chk('G04', ok, f'handoff register: every M3 entry is unchanged; new entries {newids} appended and listed under M4')
a, b = snap('STATUS_REGISTER.csv'), cur('STATUS_REGISTER.csv')
chk('G05', b[:len(a)] == a and len(b) > len(a) and all(r['milestone'] == 'M4' for r in b[len(a):]) and [r['item_id'] for r in b] == [f'SR-{i:02d}' for i in range(1, len(b) + 1)] and all(r['evidence_ladder_status'] == 'Local-tested' for r in b[len(a):]),
    'status register: the M3 rows are unchanged and M4 rows (Local-tested at most) were appended')
a, b = snap('FINDINGS_REGISTER.csv'), cur('FINDINGS_REGISTER.csv')
chk('G06', b[:len(a)] == a and len(b) > len(a) and not any(re.search(r'\b(closed|accepted|approved|resolved)\b', r['status'], re.I) for r in b)
    and [r['finding_id'] for r in b] == [f'F-{i:02d}' for i in range(1, len(b) + 1)], 'findings register: the M3 findings are unchanged, M4 findings appended, none shown as closed')
a, b = snap('INTERPRETATIONS_REGISTER.csv'), cur('INTERPRETATIONS_REGISTER.csv')
chk('G07', b[:len(a)] == a and len(b) > len(a) and all(r['status'] == 'Retained for review - not approved' and r['reviewer_decision'] == '' for r in b[len(a):]), 'interpretations: I-1 to I-16 unchanged; the new ones are retained for review, not approved, no reviewer decision filled in')
for name, args, marker, cid, text in (('run_regression_m3.py', [], 'REGRESSION OK', 'G08', 'the M3 regression tool (M2 and M0/M1 protection, M3 golden cases and demonstration) still passes'),
                                      ('run_golden_fin.py', [], 'GOLDEN OK', 'G09', 'the M4 golden cases still give the recorded answers and agree with the independent oracle'),
                                      ('run_demo_m4.py', ['--check'], 'DEMO OUTPUT MATCHES', 'G10', 'the M4 narrated demonstration still prints exactly the recorded output')):
    r = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', name), *args], capture_output=True, text=True, cwd=ROOT)
    chk(cid, r.returncode == 0 and marker in r.stdout, text)
print(f'\nregression checks failed {len(bad)}')
print('REGRESSION OK' if not bad else 'REGRESSION FAILURE')
sys.exit(1 if bad else 0)
