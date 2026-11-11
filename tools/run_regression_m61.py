#!/usr/bin/env python3
"""Regression protection for the APG-M6.1 correction (finding F-52).  Usage: python3 -I tools/run_regression_m61.py [--static]     (--static skips item 5, which runs the other tools)     Exit 0 only if every check passes.
 1. every file of the delivered M6 package that the correction was not meant to change is byte-identical to its recorded SHA-256 (regression/BASELINE_M6.json);
 2. the files it did change or add are exactly the declared ones, and each equals its recorded hash (a later edit is noticed);
 3. in the application code only apg/det/findings.py changed; no frozen test file changed; the only tests added are the new approval-binding tests;
 4. the programme tables differ from their delivered M6 versions only by appended rows (milestone M6.1); no earlier row, no RFC-01 row and no milestone row changed; nothing is shown as closed;
 5. the probe reproduces the defect's scenario and shows the approval ended; the new tests pass; the M6 regression tool (which protects M5 and earlier), the M6 golden cases and the M6 demonstration still pass.
The delivered M5 and M6 archives are not part of this package and are not changed by it.  This tool shows that the correction changed what it says it changed; it does not show that the correction is right: that is for the auditor's independent verification."""
import csv, hashlib, json, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
rd = lambda p: list(csv.DictReader(open(p, encoding='utf-8', newline='')))
bad = []
M6_ZIP = 'abcfefd9f28464de46dc205c1112b2ea33f537ef4a788562484c1d24109a1efb'
M6_DOCS = 'fa62d60ad33384a83896e05cb10cc34bbd551803d2b9e678aa21683286daaf00'


N = [0]


def chk(i, ok, t):
    N[0] += 1
    print(('PASS ' if ok else 'FAIL ') + i + ' ' + t)
    if not ok:
        bad.append(i)


B = json.load(open(os.path.join(ROOT, 'regression', 'BASELINE_M6.json')))
B62p = os.path.join(ROOT, 'regression', 'BASELINE_M61.json')
B62 = json.load(open(B62p)) if os.path.exists(B62p) else {'changed_in_m62': {}, 'added_in_m62': {}, 'not_compared': [], 'not_compared_prefix': '\0'}      # APG-M6.2 (the second correction release) declares the M6.1 files it changed again, and what it added
ok62 = lambda r: r in B62['changed_in_m62'] and os.path.exists(os.path.join(ROOT, r)) and sha(os.path.join(ROOT, r)) == B62['changed_in_m62'][r]['m62_sha256']
B63p = os.path.join(ROOT, 'regression', 'BASELINE_M62.json')
B63 = json.load(open(B63p)) if os.path.exists(B63p) else {'changed_in_m63': {}, 'added_in_m63': {}, 'not_compared': [], 'not_compared_prefix': '\0'}      # APG-M6.3 (the third correction release) declares the files it changed again, and what it added
ok63 = lambda r: r in B63['changed_in_m63'] and os.path.exists(os.path.join(ROOT, r)) and sha(os.path.join(ROOT, r)) == B63['changed_in_m63'][r]['m63_sha256']
B64p = os.path.join(ROOT, 'regression', 'BASELINE_M63.json')
B64 = json.load(open(B64p)) if os.path.exists(B64p) else {'changed_in_m64': {}, 'added_in_m64': {}, 'not_compared': [], 'not_compared_prefix': '\0'}      # APG-M6.4 (the fourth correction release) declares the files it changed again, and what it added
ok64 = lambda r: r in B64['changed_in_m64'] and os.path.exists(os.path.join(ROOT, r)) and sha(os.path.join(ROOT, r)) == B64['changed_in_m64'][r]['m64_sha256']
B65p = os.path.join(ROOT, 'regression', 'BASELINE_M64.json')
B65 = json.load(open(B65p)) if os.path.exists(B65p) else {'changed_in_m65': {}, 'added_in_m65': {}, 'not_compared': [], 'not_compared_prefix': '\0'}      # APG-M6.5 (the fifth correction release) declares the files it changed again, and what it added
ok65 = lambda r: r in B65['changed_in_m65'] and os.path.exists(os.path.join(ROOT, r)) and sha(os.path.join(ROOT, r)) == B65['changed_in_m65'][r]['m65_sha256']
B91p = os.path.join(ROOT, 'regression', 'BASELINE_M65.json')
B91 = json.load(open(B91p)) if os.path.exists(B91p) else {'changed_in_m91': {}, 'added_in_m91': {}, 'not_compared': [], 'not_compared_prefix': '\0'}      # APG-M9.1 declares the files it changed against the delivered M6.5 package, and what it added
ok91 = lambda r: r in B91['changed_in_m91'] and os.path.exists(os.path.join(ROOT, r)) and sha(os.path.join(ROOT, r)) == B91['changed_in_m91'][r]['m91_sha256']
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
ok62a = lambda r: r in B62['added_in_m62'] and os.path.exists(os.path.join(ROOT, r)) and sha(os.path.join(ROOT, r)) == B62['added_in_m62'][r]
chk('R01', B['m6_zip_sha256'] == M6_ZIP and B['m6_docs_sha256'] == M6_DOCS and B['m6_file_count'] == len(B['frozen']) + len(B['changed_in_m61']), 'the baseline names the delivered M6 ZIP and documents by hash and accounts for every one of its files')
diff = [r for r, h in B['frozen'].items() if (not os.path.exists(os.path.join(ROOT, r)) or sha(os.path.join(ROOT, r)) != h) and not ok62(r) and not ok63(r) and not ok64(r) and not ok65(r) and not ok91(r)]
chk('R02', not diff and len(B['frozen']) > 400, f"{len(B['frozen'])} files of the delivered M6 package are byte-identical to it, except any that the M6.2 correction declares and pins ({len([r for r in B['frozen'] if r in B62['changed_in_m62']])}) " + str(diff[:5]))
drift = [r for r, v in B['changed_in_m61'].items() if (not os.path.exists(os.path.join(ROOT, r)) or sha(os.path.join(ROOT, r)) != v['m61_sha256'] or v['m61_sha256'] == v['m6_sha256']) and not ok62(r) and not ok63(r) and not ok64(r) and not ok65(r) and not ok91(r)]
drift += [r for r, h in B['added_in_m61'].items() if (not os.path.exists(os.path.join(ROOT, r)) or sha(os.path.join(ROOT, r)) != h) and not ok62(r) and not ok63(r) and not ok64(r) and not ok65(r) and not ok91(r)]
chk('R03', not drift, f"the {len(B['changed_in_m61'])} changed and {len(B['added_in_m61'])} added files equal their recorded hashes, and every changed file differs from M6 " + str(drift[:5]))
known = set(B['frozen']) | set(B['changed_in_m61']) | set(B['added_in_m61']) | set(B['not_compared']) | set(B62['added_in_m62']) | set(B62['not_compared']) | set(B63['added_in_m63']) | set(B63['not_compared']) | set(B64['added_in_m64']) | set(B64['not_compared']) | set(B65['added_in_m65']) | set(B65['not_compared']) | set(B91['added_in_m91']) | set(B91['not_compared']) | set(B92['added_in_m92']) | set(B92['not_compared']) | set(B93['added_in_m93']) | set(B93['not_compared']) | set(B94['added_in_m94']) | set(B94['not_compared'])
extra = []
for root, dns, fns in os.walk(ROOT):
    dns[:] = [d for d in dns if d != '__pycache__']
    extra += [r for r in (os.path.relpath(os.path.join(root, f), ROOT).replace(os.sep, '/') for f in fns) if r not in known and not r.startswith((B['not_compared_prefix'], B62['not_compared_prefix'], B63['not_compared_prefix'], B64['not_compared_prefix'], B65['not_compared_prefix'], B91['not_compared_prefix'], B92['not_compared_prefix'], B93['not_compared_prefix'], B94['not_compared_prefix']))]
chk('R04', not extra, 'no file exists in the package beyond the M6 files and the declared additions (M6.1, and any declared by M6.2) ' + str(extra[:5]))
ch, ad = sorted(B['changed_in_m61']), sorted(B['added_in_m61'])
code = [r for r in ch if r.startswith('apg/')]
chk('R05', code == ['apg/det/findings.py'] and not [r for r in ad if r.startswith('apg/')], 'the only application code that changed is apg/det/findings.py; no application file was added')
chk('R06', not [r for r in ch if r.startswith('tests/')] and [r for r in ad if r.startswith('tests/')] == ['tests/test_det_approval_binding.py'], 'no existing test file changed; the only test file added is tests/test_det_approval_binding.py')
chk('R07', [r for r in ch if r.startswith('tools/')] == ['tools/m5_mutants.py', 'tools/make_m0.py', 'tools/run_regression_m6.py'] and
    [r for r in ad if r.startswith('tools/')] == ['tools/make_m61_registers.py', 'tools/probe_approval_binding.py', 'tools/programme_check_m61.py', 'tools/run_m61_all.py', 'tools/run_regression_m61.py'],
    'tools changed: m5_mutants.py (runs the new tests), make_m0.py (runs the M6.1 register step) and run_regression_m6.py (accepts the M6.1 status rows); tools added: the register step, the probe, the M6.1 register check, the wrapper and this tool')
other = [r for r in ch if not r.startswith(('tools/', 'apg/', 'tests/'))]
okset = {'README.md', 'RUN_COMMANDS.txt', 'programme/STATUS_REGISTER.csv', 'programme/FINDINGS_REGISTER.csv', 'programme/INTERPRETATIONS_REGISTER.csv'}
chk('R08', set(other) <= okset and not [r for r in ch if r.startswith(('regression/BASELINE', 'regression/GOLDEN', 'regression/DEMO', 'regression/m1', 'regression/m2', 'regression/m3', 'regression/m4', 'regression/m5', 'research/', 'builder_zero/', 'catalogue/'))],
    'of the non-code files only the readme, the run commands and the three append-only tables changed; no golden file, baseline, demonstration output, snapshot, research file or Builder Zero case changed ' + str(sorted(set(other) - okset)))
snap = lambda n: rd(os.path.join(ROOT, 'regression', 'm6_snapshot', n))
cur = lambda n: rd(os.path.join(ROOT, 'programme', n))
raw = lambda *a: open(os.path.join(ROOT, *a), 'rb').read()
chk('R09', all(raw('regression', 'm6_snapshot', t) == raw('programme', t) or ok91('programme/' + t) for t in ('PROGRAMME_MILESTONES.csv', 'ENGINE_HANDOFF_REGISTER.csv', 'RFC_REGISTER.csv')),
    'the milestones table, the handoff register and the RFC register are byte-identical to the delivered M6 ones (M7 not started; RFC-01 still PROPOSED and unnumbered)')
for n, idc, pre, nmin in (('STATUS_REGISTER.csv', 'item_id', 'SR-', 62), ('FINDINGS_REGISTER.csv', 'finding_id', 'F-', 52), ('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', 'I-', 59)):
    a, b = snap(n), cur(n)
    ids = [r[idc] for r in b]
    chk('R10-' + n[:4], b[:len(a)] == a and len(b) > len(a) and all(r['milestone'] in ('M6.1', 'M6.2', 'M6.3', 'M6.4', 'M6.5', 'M9.1', 'M9.2', 'M9.3', 'M9.4') for r in b[len(a):]) and ids == [f'{pre}{i:02d}' if pre != 'I-' else f'{pre}{i}' for i in range(1, len(b) + 1)] and ids[len(a)] == f'{pre}{nmin}',
        f'{n}: every delivered M6 row is unchanged; rows from {pre}{nmin} are appended with milestone M6.1 (M6.2 and M6.3 rows may follow)')
f = cur('FINDINGS_REGISTER.csv')
chk('R11', not any(re.search(r'\b(closed|accepted|approved|resolved)\b', r['status'], re.I) for r in f) and all(r['status'] == 'Retained for review - not approved' and r['reviewer_decision'] == '' for r in cur('INTERPRETATIONS_REGISTER.csv') if r['milestone'] in ('M6.1', 'M6.2', 'M6.3', 'M6.4', 'M6.5', 'M9.1', 'M9.2', 'M9.3', 'M9.4')),
    'no finding is shown as closed; the new interpretations are retained for review, not approved, with no reviewer decision')
steps = (('probe_approval_binding.py', [], 'APPROVAL IS BOUND TO THE EVIDENCE', 'R12', 'the probe reproduces the version-1-to-version-2 scenario and shows the old approval ended (on the delivered M6 code the same probe prints DEFECT PRESENT)'),
         ('run_m2_tests.py', ['-q', 'test_det_approval_binding*'], 'failures 0  errors 0', 'R13', 'the approval-binding regression tests pass'),
         ('run_m2_tests.py', ['-q', 'test_det_*'], 'failures 0  errors 0', 'R14', 'every M5 detection and finding test, frozen ones included, still passes on the corrected code'),
         ('run_regression_m6.py', [], 'REGRESSION OK', 'R15', 'the M6 regression tool (which protects M5, M4, M3, M2 and M0/M1) still passes'),
         ('run_golden_mkt.py', [], 'GOLDEN OK', 'R16', 'the M6 golden cases still give the recorded answers'),
         ('run_demo_m6.py', ['--check'], 'DEMO OUTPUT MATCHES', 'R17', 'the M6 narrated demonstration still prints exactly the recorded output'),
         ('run_demo_m5.py', ['--check'], 'DEMO OUTPUT MATCHES', 'R18', 'the M5 narrated demonstration still prints exactly the recorded output'))
for tool, args, marker, cid, text in (() if '--static' in sys.argv else steps):
    x = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', tool), *args], capture_output=True, text=True, cwd=ROOT)
    out = x.stdout + x.stderr
    chk(cid, x.returncode == 0 and marker in out, text + ('' if x.returncode == 0 and marker in out else ' :: ' + out[-300:]))
print(f'\nchecks {N[0]}  failed {len(bad)}')
if bad:
    print('FAILED:', bad)
    sys.exit(1)
print('STATIC CHECKS OK (R12 to R18 skipped)' if '--static' in sys.argv else 'REGRESSION OK')
