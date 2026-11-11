#!/usr/bin/env python3
"""Regression protection for the delivered M5 package.  Usage: python3 -I tools/run_regression_m6.py
 1. every M5 file that M6 must not change is byte-identical to its recorded SHA-256 (regression/BASELINE_M5.json); the files M6 legitimately changed are listed there (code, tools, tables, documents) and are checked to have changed;
 2. the programme tables differ from their delivered M5 versions only in the ways M6 is allowed to change them (rows are appended; M5 rows, findings and interpretations are untouched; EDR-08 and EDR-09 gain their contract tests);
 3. the M5 regression tool (which itself protects M4, M3, M2 and M0/M1) still passes;
 4. the M6 golden cases and demonstration still give the recorded answers.
The M5 files that M6 changed (the portfolio display fix and the checker tolerance edits) are listed, not hidden: they are baseline-changed and are for the reviewer.  A change that moves any of this must be recorded and reviewed, not silently accepted."""
import csv, hashlib, json, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
rd = lambda p: list(csv.DictReader(open(p, encoding='utf-8', newline='')))
bad = []
def chk(i, ok, t):
    print(('PASS ' if ok else 'FAIL ') + i + ' ' + t)
    if not ok: bad.append(i)
B = json.load(open(os.path.join(ROOT, 'regression', 'BASELINE_M5.json')))
B61p = os.path.join(ROOT, 'regression', 'BASELINE_M6.json')
B61 = json.load(open(B61p))['changed_in_m61'] if os.path.exists(B61p) else {}          # APG-M6.1 (the correction release) declares the files it changed and pins their new hashes there
ok61 = lambda rel: rel in B61 and os.path.exists(os.path.join(ROOT, rel)) and sha(os.path.join(ROOT, rel)) == B61[rel]['m61_sha256']
B62p = os.path.join(ROOT, 'regression', 'BASELINE_M61.json')
B62 = json.load(open(B62p))['changed_in_m62'] if os.path.exists(B62p) else {}          # APG-M6.2 (the second correction release) declares the files it changed again and pins their new hashes there
ok62 = lambda rel: rel in B62 and os.path.exists(os.path.join(ROOT, rel)) and sha(os.path.join(ROOT, rel)) == B62[rel]['m62_sha256']
B63p = os.path.join(ROOT, 'regression', 'BASELINE_M62.json')
B63 = json.load(open(B63p))['changed_in_m63'] if os.path.exists(B63p) else {}          # APG-M6.3 (the third correction release) declares the files it changed again and pins their new hashes there
ok63 = lambda rel: rel in B63 and os.path.exists(os.path.join(ROOT, rel)) and sha(os.path.join(ROOT, rel)) == B63[rel]['m63_sha256']
B64p = os.path.join(ROOT, 'regression', 'BASELINE_M63.json')
B64 = json.load(open(B64p))['changed_in_m64'] if os.path.exists(B64p) else {}          # APG-M6.4 (the fourth correction release) declares the files it changed again and pins their new hashes there
ok64 = lambda rel: rel in B64 and os.path.exists(os.path.join(ROOT, rel)) and sha(os.path.join(ROOT, rel)) == B64[rel]['m64_sha256']
B65p = os.path.join(ROOT, 'regression', 'BASELINE_M64.json')
B65 = json.load(open(B65p))['changed_in_m65'] if os.path.exists(B65p) else {}          # APG-M6.5 (the fifth correction release) declares the files it changed again and pins their new hashes there
ok65 = lambda rel: rel in B65 and os.path.exists(os.path.join(ROOT, rel)) and sha(os.path.join(ROOT, rel)) == B65[rel]['m65_sha256']
B91p = os.path.join(ROOT, 'regression', 'BASELINE_M65.json')
B91 = json.load(open(B91p))['changed_in_m91'] if os.path.exists(B91p) else {}          # APG-M9.1 declares the files it changed against the delivered M6.5 package and pins their new hashes there
ok91 = lambda rel: rel in B91 and os.path.exists(os.path.join(ROOT, rel)) and sha(os.path.join(ROOT, rel)) == B91[rel]['m91_sha256']
B92p = os.path.join(ROOT, 'regression', 'BASELINE_M91.json')
B92 = json.load(open(B92p)) if os.path.exists(B92p) else {'changed_in_m92': {}, 'added_in_m92': {}, 'not_compared': [], 'not_compared_prefix': '\0'}      # APG-M9.2 declares the files it changed against the delivered M9.1 package, and what it added
ok92 = lambda r: r in B92['changed_in_m92'] and os.path.exists(os.path.join(ROOT, r)) and sha(os.path.join(ROOT, r)) == B92['changed_in_m92'][r]['m92_sha256']
B93p = os.path.join(ROOT, 'regression', 'BASELINE_M92.json')
B93 = json.load(open(B93p)) if os.path.exists(B93p) else {'changed_in_m93': {}, 'added_in_m93': {}, 'not_compared': [], 'not_compared_prefix': '\0'}      # APG-M9.3 declares the files it changed against the delivered M9.2
ok93 = lambda r: r in B93['changed_in_m93'] and os.path.exists(os.path.join(ROOT, r)) and sha(os.path.join(ROOT, r)) == B93['changed_in_m93'][r]['m93_sha256']
B94p = os.path.join(ROOT, 'regression', 'BASELINE_M93.json')
B94 = json.load(open(B94p)) if os.path.exists(B94p) else {'changed_in_m94': {}, 'added_in_m94': {}, 'not_compared': [], 'not_compared_prefix': '\0'}      # APG-M9.4 declares the files it changed against the delivered M9.3
ok94 = lambda r: r in B94['changed_in_m94'] and os.path.exists(os.path.join(ROOT, r)) and sha(os.path.join(ROOT, r)) == B94['changed_in_m94'][r]['m94_sha256']
_ok93 = ok93
ok93 = lambda r: _ok93(r) or ok94(r)          # a file M9.4 changed again is accepted when the M9.4 baseline pins its new hash
_ok92 = ok92
ok92 = lambda r: _ok92(r) or ok93(r)          # a file M9.3 changed again is accepted when the M9.3 baseline pins its new hash
_ok91 = ok91
ok91 = lambda r: _ok91(r) or ok92(r)          # a file M9.2 changed again is accepted when the M9.2 baseline pins its new hash
diff = [rel for rel, h in B['frozen'].items() if (not os.path.exists(os.path.join(ROOT, rel)) or sha(os.path.join(ROOT, rel)) != h) and not ok61(rel) and not ok62(rel) and not ok63(rel) and not ok64(rel) and not ok65(rel) and not ok91(rel)]
chk('L01', not diff, f"{len(B['frozen'])} M5 files are byte-identical to the delivered M5 package, except any that the M6.1 correction declares and pins ({len([r for r in B['frozen'] if r in B61])}) " + str(diff[:5]))
code = sorted(B['code_changed_in_m6']); tools = sorted(B['tools_changed_in_m6'])
chk('L01b', code == ['apg/det/detect.py', 'apg/det/findings.py', 'apg/det/portfolio.py', 'apg/det/relations.py', 'tests/test_det_portfolio.py', 'tools/run_demo_m5.py'],
    'the M5 code files M6 changed are exactly: detect.py (adds the two M6 formula ids), findings.py (accepts them), relations.py (two policy prefixes), portfolio.py (unquantified display fix), test_det_portfolio.py (2 tests), run_demo_m5.py (prints the fixed display)')
chk('L01c', tools == ['tools/make_m0.py', 'tools/programme_check_m4.py', 'tools/programme_check_m5.py', 'tools/run_regression_m5.py'] and all(os.path.exists(os.path.join(ROOT, r)) for r in code + tools),
    'the M5 tools M6 changed are exactly: make_m0.py (runs the M6 register step), programme_check_m4.py and programme_check_m5.py (tolerant of M6 rows), run_regression_m5.py (reads the stored M5 tables)')
snap = lambda n: rd(os.path.join(ROOT, 'regression', 'm5_snapshot', n))
cur = lambda n: rd(os.path.join(ROOT, 'programme', n))
upd = B['updated_in_m6']
chk('L02', all(sha(os.path.join(ROOT, 'regression', 'm5_snapshot', os.path.basename(rel))) == h for rel, h in upd.items() if rel.startswith('programme/') or rel == 'regression/DEMO_OUTPUT_M5.txt'),
    'the stored M5 snapshots of the programme tables and of the M5 demonstration output equal the delivered M5 hashes')
chk('L02b', all(sha(os.path.join(ROOT, rel)) != h for rel, h in upd.items() if rel in code + tools + ['regression/DEMO_OUTPUT_M5.txt']),
    'every listed M5 code, tool and demonstration file differs from its delivered M5 version, as recorded')
a, b = snap('PROGRAMME_MILESTONES.csv'), cur('PROGRAMME_MILESTONES.csv')
later = {'M9'} if ok91('programme/PROGRAMME_MILESTONES.csv') else set()          # APG-M9.1 edits the M9 row only (status, handoff list); the baseline pins the table's new hash
ok = len(a) == len(b) and all(x['milestone_id'] == y['milestone_id'] and all(x[k] == y[k] for k in x if k not in ('status', 'handoff_register_entries')) for x, y in zip(a, b))
ok = ok and all(x['handoff_register_entries'] == y['handoff_register_entries'] for x, y in zip(a, b) if x['milestone_id'] not in ('M6',) + tuple(later))
m6, m6o = next(y for y in b if y['milestone_id'] == 'M6'), next(x for x in a if x['milestone_id'] == 'M6')
ok = ok and m6['handoff_register_entries'].startswith(m6o['handoff_register_entries'])
want = {f'M{i}': 'Delivered - builder-checked' for i in range(6)}; want['M6'] = 'In this delivery'
for i in later: want[i] = 'In this delivery'
ok = ok and all(y['status'] == want.get(y['milestone_id'], 'Not started') for y in b)
chk('L03', ok, 'milestone rows: only status and the M6 handoff list changed; M6 only added entries; M0-M5 delivered, M6 in this delivery, nothing later started (M7 not started)')
a, b = snap('ENGINE_HANDOFF_REGISTER.csv'), cur('ENGINE_HANDOFF_REGISTER.csv')
b = [y for y in b if y['edr_id'] not in ('EDR-31', 'EDR-32')]          # EDR-31 (APG-M9.1) and EDR-32 (APG-M9.2) are appended and listed under M9 and M10, not M6; the baselines pin the table's hashes
newids = [y['edr_id'] for y in b[len(a):]]
changed = [x['edr_id'] for x, y in zip(a, b) if x != y]
ok = len(b) > len(a) and changed == ['EDR-08', 'EDR-09']
for i in ('EDR-08', 'EDR-09'):
    xo, xn = next(x for x in a if x['edr_id'] == i), next(y for y in b if y['edr_id'] == i)
    ok = ok and all(xo[k] == xn[k] for k in xo if k not in ('contract_test', 'status')) and xn['status'] == 'Open - contract test written' and 'written in M6' in xn['contract_test']
ok = ok and newids == sorted(newids) and all(y['status'] == 'Open - described only' and y['evidence_seen'].startswith('No Engine code') for y in b[len(a):]) and all(i in m6['handoff_register_entries'] for i in newids)
chk('L04', ok, f'handoff register: every M5 entry is unchanged except EDR-08 and EDR-09 (contract tests written, still open); new entries {newids} appended and listed under M6')
a, b = snap('STATUS_REGISTER.csv'), cur('STATUS_REGISTER.csv')
chk('L05', b[:len(a)] == a and len(b) > len(a) and all(r['milestone'] in ('M6', 'M6.1', 'M6.2', 'M6.3', 'M6.4', 'M6.5', 'M9.1', 'M9.2', 'M9.3', 'M9.4') for r in b[len(a):]) and [r['item_id'] for r in b] == [f'SR-{i:02d}' for i in range(1, len(b) + 1)]
    and all(r['evidence_ladder_status'] == 'Local-tested' for r in b[len(a):] if r['milestone'] == 'M6') and all(r['evidence_ladder_status'] in ('Local-tested', 'Specified', 'Research record') for r in b[len(a):]),
    'status register: the M5 rows are unchanged and M6 rows (Local-tested at most) were appended; the APG-M6.1, APG-M6.2 and APG-M6.3 correction rows (milestones M6.1, M6.2, M6.3) may follow them, none above Local-tested')
a, b = snap('FINDINGS_REGISTER.csv'), cur('FINDINGS_REGISTER.csv')
chk('L06', b[:len(a)] == a and len(b) > len(a) and not any(re.search(r'\b(closed|accepted|approved|resolved)\b', r['status'], re.I) for r in b)
    and [r['finding_id'] for r in b] == [f'F-{i:02d}' for i in range(1, len(b) + 1)], 'findings register: the M5 findings are unchanged, M6 findings appended, none shown as closed')
a, b = snap('INTERPRETATIONS_REGISTER.csv'), cur('INTERPRETATIONS_REGISTER.csv')
chk('L07', b[:len(a)] == a and len(b) > len(a) and all(r['status'] == 'Retained for review - not approved' and r['reviewer_decision'] == '' for r in b[len(a):]), 'interpretations: the M5 ones are unchanged; the new ones are retained for review, not approved, no reviewer decision filled in')
rfc = rd(os.path.join(ROOT, 'programme', 'RFC_REGISTER.csv'))
chk('L07b', len(rfc) == 1 and rfc[0]['rfc_id'] == 'RFC-01' and rfc[0]['status'].startswith('PROPOSED - not approved'), 'RFC-01 is recorded as PROPOSED, not approved')
for name, args, marker, cid, text in (('run_regression_m5.py', [], 'REGRESSION OK', 'L08', 'the M5 regression tool (M4, M3, M2 and M0/M1 protection, M5 golden cases and demonstration) still passes'),
                                      ('run_golden_mkt.py', [], 'GOLDEN OK', 'L09', 'the M6 golden cases still give the recorded answers and agree with the independent oracle'),
                                      ('run_demo_m6.py', ['--check'], 'DEMO OUTPUT MATCHES', 'L10', 'the M6 narrated demonstration still prints exactly the recorded output')):
    r = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', name), *args], capture_output=True, text=True, cwd=ROOT)
    chk(cid, r.returncode == 0 and marker in r.stdout, text)
print(f'\nregression checks failed {len(bad)}')
print('REGRESSION OK' if not bad else 'REGRESSION FAILURE')
sys.exit(1 if bad else 0)
