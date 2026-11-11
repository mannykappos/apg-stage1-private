#!/usr/bin/env python3
"""Regression protection for the delivered M4 package.  Usage: python3 -I tools/run_regression_m5.py
 1. every M4 file that M5 must not change is byte-identical to its recorded SHA-256 (regression/BASELINE_M4.json); the files M5 legitimately changed are listed in that file and are checked to have changed;
 2. the programme tables differ from their delivered M4 versions only in the ways M5 is allowed to change them (rows are appended; M4 rows, findings and interpretations are untouched; EDR-10 gains its contract test);
 3. the M4 regression tool (which itself protects M3, M2 and M0/M1) still passes;
 4. the M5 golden cases and demonstration still give the recorded answers.
Later milestones keep this tool and add their own baselines; a change that moves any of this must be recorded and reviewed, not silently accepted."""
import csv, hashlib, json, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
rd = lambda p: list(csv.DictReader(open(p, encoding='utf-8', newline='')))
bad = []
def chk(i, ok, t):
    print(('PASS ' if ok else 'FAIL ') + i + ' ' + t)
    if not ok: bad.append(i)
B = json.load(open(os.path.join(ROOT, 'regression', 'BASELINE_M4.json')))
diff = [rel for rel, h in B['frozen'].items() if not os.path.exists(os.path.join(ROOT, rel)) or sha(os.path.join(ROOT, rel)) != h]
chk('K01', not diff, f"{len(B['frozen'])} M4 files are byte-identical to the delivered M4 package " + str(diff[:5]))
code_changed = sorted(rel for rel in B['updated_in_m5'] if rel.endswith('.py') and rel.startswith('apg/'))
chk('K01b', code_changed == ['apg/fin/intake.py'] and all(sha(os.path.join(ROOT, rel)) != B['updated_in_m5'][rel] for rel in ('apg/fin/intake.py', 'tools/mut_runner.py')),
    'the only M4 code file M5 changes is apg/fin/intake.py (and the mutation helper tools/mut_runner.py); both differ from the M4 versions, as recorded')
snap = lambda n: rd(os.path.join(ROOT, 'regression', 'm4_snapshot', n))
cur = lambda n: rd(os.path.join(ROOT, 'regression', 'm5_snapshot', n))   # M6: the M5 tables as delivered (the live tables are checked by run_regression_m6.py)
chk('K02', all(sha(os.path.join(ROOT, 'regression', 'm4_snapshot', os.path.basename(rel))) == B['updated_in_m5'][rel] for rel in B['updated_in_m5'] if rel.startswith('programme/')), 'the stored M4 snapshots of the programme tables equal the delivered M4 hashes')
a, b = snap('PROGRAMME_MILESTONES.csv'), cur('PROGRAMME_MILESTONES.csv')
ok = len(a) == len(b) and all(x['milestone_id'] == y['milestone_id'] and all(x[k] == y[k] for k in x if k not in ('status', 'handoff_register_entries')) for x, y in zip(a, b))
ok = ok and all(x['handoff_register_entries'] == y['handoff_register_entries'] for x, y in zip(a, b) if x['milestone_id'] != 'M5')
m5, m5o = next(y for y in b if y['milestone_id'] == 'M5'), next(x for x in a if x['milestone_id'] == 'M5')
ok = ok and m5['handoff_register_entries'].startswith(m5o['handoff_register_entries'])
want = {f'M{i}': 'Delivered - builder-checked' for i in range(5)}; want['M5'] = 'In this delivery'
ok = ok and all(y['status'] == want.get(y['milestone_id'], 'Not started') for y in b)
chk('K03', ok, 'milestone rows: only status and the M5 handoff list changed; M5 only added entries; M0-M4 delivered, M5 in this delivery, nothing later started')
a, b = snap('ENGINE_HANDOFF_REGISTER.csv'), cur('ENGINE_HANDOFF_REGISTER.csv')
newids = [y['edr_id'] for y in b[len(a):]]
changed = [x['edr_id'] for x, y in zip(a, b) if x != y]
e10o, e10 = next(x for x in a if x['edr_id'] == 'EDR-10'), next(y for y in b if y['edr_id'] == 'EDR-10')
ok = len(b) > len(a) and changed == ['EDR-10'] and all(e10o[k] == e10[k] for k in e10o if k not in ('contract_test', 'status')) and e10['status'] == 'Open - contract test written' and 'written in M5' in e10['contract_test']
ok = ok and newids == sorted(newids) and all(y['status'] == 'Open - described only' and y['evidence_seen'].startswith('No Engine code') for y in b[len(a):]) and all(i in m5['handoff_register_entries'] for i in newids)
chk('K04', ok, f'handoff register: every M4 entry is unchanged except EDR-10 (contract test written, still open); new entries {newids} appended and listed under M5')
a, b = snap('STATUS_REGISTER.csv'), cur('STATUS_REGISTER.csv')
chk('K05', b[:len(a)] == a and len(b) > len(a) and all(r['milestone'] == 'M5' for r in b[len(a):]) and [r['item_id'] for r in b] == [f'SR-{i:02d}' for i in range(1, len(b) + 1)] and all(r['evidence_ladder_status'] == 'Local-tested' for r in b[len(a):]),
    'status register: the M4 rows are unchanged and M5 rows (Local-tested at most) were appended')
a, b = snap('FINDINGS_REGISTER.csv'), cur('FINDINGS_REGISTER.csv')
chk('K06', b[:len(a)] == a and len(b) > len(a) and not any(re.search(r'\b(closed|accepted|approved|resolved)\b', r['status'], re.I) for r in b)
    and [r['finding_id'] for r in b] == [f'F-{i:02d}' for i in range(1, len(b) + 1)], 'findings register: the M4 findings are unchanged, M5 findings appended, none shown as closed')
a, b = snap('INTERPRETATIONS_REGISTER.csv'), cur('INTERPRETATIONS_REGISTER.csv')
chk('K07', b[:len(a)] == a and len(b) > len(a) and all(r['status'] == 'Retained for review - not approved' and r['reviewer_decision'] == '' for r in b[len(a):]), 'interpretations: I-1 to I-29 unchanged; the new ones are retained for review, not approved, no reviewer decision filled in')
for name, args, marker, cid, text in (('run_regression_m4.py', [], 'REGRESSION OK', 'K08', 'the M4 regression tool (M3, M2 and M0/M1 protection, M4 golden cases and demonstration) still passes'),
                                      ('run_golden_det.py', [], 'GOLDEN OK', 'K09', 'the M5 golden cases still give the recorded answers and agree with the independent oracle'),
                                      ('run_demo_m5.py', ['--check'], 'DEMO OUTPUT MATCHES', 'K10', 'the M5 narrated demonstration still prints exactly the recorded output')):
    r = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', name), *args], capture_output=True, text=True, cwd=ROOT)
    chk(cid, r.returncode == 0 and marker in r.stdout, text)
print(f'\nregression checks failed {len(bad)}')
print('REGRESSION OK' if not bad else 'REGRESSION FAILURE')
sys.exit(1 if bad else 0)
