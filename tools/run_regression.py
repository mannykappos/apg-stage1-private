#!/usr/bin/env python3
"""Regression protection for the earlier milestones.  Usage: python3 -I tools/run_regression.py
 1. every M0+M1 file that M2 must not change is byte-identical to its recorded SHA-256 (regression/BASELINE_M0_M1.json);
 2. the programme tables differ from their M1 versions only in the ways M2 is allowed to change them;
 3. all the M0/M1 package checks (Builder Zero, templates, programme) still pass;
 4. the golden cases on Builder Zero still give the recorded answers.
Later milestones keep this tool (M3 changed one line: the M2 tables it compares against are the stored M2 snapshot) and add their own baselines; a change that moves any of this must be recorded and reviewed, not silently accepted."""
import csv, hashlib, json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
rd = lambda p: list(csv.DictReader(open(p, encoding='utf-8', newline='')))
bad = []
def chk(i, ok, t):
    print(('PASS ' if ok else 'FAIL ') + i + ' ' + t)
    if not ok: bad.append(i)
B = json.load(open(os.path.join(ROOT, 'regression', 'BASELINE_M0_M1.json')))
diff = [rel for rel, h in B['frozen'].items() if not os.path.exists(os.path.join(ROOT, rel)) or sha(os.path.join(ROOT, rel)) != h]
chk('R01', not diff, f"{len(B['frozen'])} M0/M1 files are byte-identical to the delivered M0+M1 package " + str(diff[:5]))

snap = lambda n: rd(os.path.join(ROOT, 'regression', 'm1_snapshot', n))
cur = lambda n: rd(os.path.join(ROOT, 'regression', 'm2_snapshot', n))        # M3: the M1 -> M2 step is checked against the delivered M2 tables; M3's own changes are checked by run_regression_m3.py
chk('R02a', all(sha(os.path.join(ROOT, 'regression', 'm1_snapshot', os.path.basename(rel))) == B['updated_in_m2'][rel] for rel in B['updated_in_m2'] if rel.startswith('programme/')), 'the stored M1 snapshots of the programme tables equal the delivered M1 hashes')
# milestones: same rows, only status (and M2 handoff entries) may differ
a, b = snap('PROGRAMME_MILESTONES.csv'), cur('PROGRAMME_MILESTONES.csv')
ok = len(a) == len(b) and all(x['milestone_id'] == y['milestone_id'] and all(x[k] == y[k] for k in x if k not in ('status', 'handoff_register_entries')) for x, y in zip(a, b))
ok = ok and all(x['handoff_register_entries'] == y['handoff_register_entries'] for x, y in zip(a, b) if x['milestone_id'] != 'M2')
m2 = next(y for y in b if y['milestone_id'] == 'M2'); m2o = next(x for x in a if x['milestone_id'] == 'M2')
ok = ok and m2['handoff_register_entries'].startswith(m2o['handoff_register_entries'])
chk('R02b', ok, 'milestone rows: only status and the M2 handoff list changed; M2 only added entries')
# handoff register: M1 rows intact except status and contract_test of EDR-01..03; new rows only appended
a, b = snap('ENGINE_HANDOFF_REGISTER.csv'), cur('ENGINE_HANDOFF_REGISTER.csv')
newids = [y['edr_id'] for y in b[len(a):]]
ok = len(b) >= len(a)
for x, y in zip(a, b):
    allowed = {'status', 'contract_test'} if x['edr_id'] in ('EDR-01', 'EDR-02', 'EDR-03') else set()
    ok = ok and x['edr_id'] == y['edr_id'] and all(x[k] == y[k] for k in x if k not in allowed)
chk('R02c', ok and newids == sorted(newids) and all(y['status'] == 'Open - described only' for y in b[len(a):]), f'handoff register: M1 entries unchanged apart from EDR-01..03 status and contract test; new entries {newids}')
a, b = snap('STATUS_REGISTER.csv'), cur('STATUS_REGISTER.csv')
chk('R02d', b[:len(a)] == a and len(b) > len(a), 'status register: the M1 rows are unchanged and M2 rows were appended')
for name, args, marker in (('run_all_checks.py', [], 'ALL CHECKS PASS'), ('run_golden.py', [], 'GOLDEN OK'), ('run_demo.py', ['--check'], 'DEMO OUTPUT MATCHES')):
    r = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', name), *args], capture_output=True, text=True, cwd=ROOT)
    cid, text = {'run_all_checks.py': ('R03', 'M0/M1 package checks still pass'), 'run_golden.py': ('R04', 'golden Builder Zero cases still give the recorded answers'),
                 'run_demo.py': ('R05', 'the narrated demonstration still prints exactly the recorded output')}[name]
    chk(cid, r.returncode == 0 and marker in r.stdout, text)
print(f'\nregression checks failed {len(bad)}')
print('REGRESSION OK' if not bad else 'REGRESSION FAILURE')
sys.exit(1 if bad else 0)
