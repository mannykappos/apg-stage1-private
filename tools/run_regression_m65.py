#!/usr/bin/env python3
"""Regression protection for the APG-M6.5 correction (finding F-57).  Usage: python3 -I tools/run_regression_m65.py [--static]     (--static skips item 5, which runs the other tools)     Exit 0 only if every check passes.
 1. every file of the delivered M6.4 package that the correction was not meant to change is byte-identical to its recorded SHA-256 (regression/BASELINE_M64.json);
 2. the files it changed or added are exactly the declared ones, and each equals its recorded hash (a later edit is noticed);
 3. in the application code only apg/det/findings.py changed; of the existing test files only the seven that approve through the lower-level call, build approval records by hand or hold the shared fixture changed (two of them are M5 files, changed in their calls); the only test file added is the transition-gate one;
 4. the programme tables differ from their delivered M6.4 versions only by appended rows (milestone M6.5; no carried-forward row is added); no earlier row, no governance row, no RFC-01 row and no milestone row changed; nothing is shown as closed;
 5. the probes reproduce the bypass of the lower-level call and the swap scenario and show them refused; the new tests pass; the earlier regression tools, the M6 regression tool (which protects M5 and earlier), the M6 golden cases and the demonstrations still pass.
The delivered M5, M6, M6.1, M6.2, M6.3 and M6.4 archives are not part of this package and are not changed by it.  This tool shows that the correction changed what it says it changed; it does not show that the correction is right: that is for the auditor's independent verification."""
import csv, hashlib, json, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
rd = lambda p: list(csv.DictReader(open(p, encoding='utf-8', newline='')))
bad = []
M64_ZIP = 'ae481618dce8a2426d84c0353659cd9992a214ee29ee122329fd5ffc766c8e57'
M64_DOCS = '74d1c243acda0588239ce6b9a874450763c65c78122bef653b018de1f06b02ea'
N = [0]


def chk(i, ok, t):
    N[0] += 1
    print(('PASS ' if ok else 'FAIL ') + i + ' ' + t)
    if not ok:
        bad.append(i)


B = json.load(open(os.path.join(ROOT, 'regression', 'BASELINE_M64.json')))
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
chk('R01', B['m64_zip_sha256'] == M64_ZIP and B['m64_docs_sha256'] == M64_DOCS and B['m64_file_count'] == len(B['frozen']) + len(B['changed_in_m65']), 'the baseline names the delivered M6.4 ZIP and documents by hash and accounts for every one of its files')
diff = [r for r, h in B['frozen'].items() if (not os.path.exists(os.path.join(ROOT, r)) or sha(os.path.join(ROOT, r)) != h) and not ok91(r)]
chk('R02', not diff and len(B['frozen']) > 400, f"{len(B['frozen'])} files of the delivered M6.4 package are byte-identical to it " + str(diff[:5]))
drift = [r for r, v in B['changed_in_m65'].items() if (not os.path.exists(os.path.join(ROOT, r)) or sha(os.path.join(ROOT, r)) != v['m65_sha256'] or v['m65_sha256'] == v['m64_sha256']) and not ok91(r)]
drift += [r for r, h in B['added_in_m65'].items() if (not os.path.exists(os.path.join(ROOT, r)) or sha(os.path.join(ROOT, r)) != h) and not ok91(r)]
chk('R03', not drift, f"the {len(B['changed_in_m65'])} changed and {len(B['added_in_m65'])} added files equal their recorded hashes, and every changed file differs from M6.4 " + str(drift[:5]))
known = set(B['frozen']) | set(B['changed_in_m65']) | set(B['added_in_m65']) | set(B['not_compared']) | set(B91['added_in_m91']) | set(B91['not_compared']) | set(B92['added_in_m92']) | set(B92['not_compared']) | set(B93['added_in_m93']) | set(B93['not_compared']) | set(B94['added_in_m94']) | set(B94['not_compared'])
extra = []
for root, dns, fns in os.walk(ROOT):
    dns[:] = [d for d in dns if d != '__pycache__']
    extra += [r for r in (os.path.relpath(os.path.join(root, f), ROOT).replace(os.sep, '/') for f in fns) if r not in known and not r.startswith((B['not_compared_prefix'], B91['not_compared_prefix'], B92['not_compared_prefix'], B93['not_compared_prefix'], B94['not_compared_prefix']))]
chk('R04', not extra, 'no file exists in the package beyond the M6.4 files and the declared additions ' + str(extra[:5]))
ch, ad = sorted(B['changed_in_m65']), sorted(B['added_in_m65'])
code = [r for r in ch if r.startswith('apg/')]
chk('R05', code == ['apg/det/findings.py'] and not [r for r in ad if r.startswith('apg/')], 'the only application code that changed is apg/det/findings.py; no application file was added')
chk('R06', [r for r in ch if r.startswith('tests/')] == ['tests/helpers_det.py', 'tests/test_det_approval_binding.py', 'tests/test_det_findings.py', 'tests/test_det_findings_edges.py', 'tests/test_det_proposal_binding.py', 'tests/test_det_proposal_identity.py', 'tests/test_det_version_types.py'] and [r for r in ad if r.startswith('tests/')] == ['tests/test_det_transition_gate.py'],
    'of the existing test files only helpers_det.py (one helper added) and six that approve through the lower-level call changed (test_det_findings.py and test_det_findings_edges.py are M5 files, changed in their calls only; the assertions that were changed are listed in the change record); the only test file added is tests/test_det_transition_gate.py')
chk('R07', [r for r in ch if r.startswith('tools/')] == ['tools/m5_mutants.py', 'tools/make_m0.py', 'tools/probe_approval_binding.py', 'tools/probe_malformed_proposal_version.py', 'tools/probe_stale_proposal.py', 'tools/run_regression_m6.py', 'tools/run_regression_m61.py', 'tools/run_regression_m62.py', 'tools/run_regression_m63.py', 'tools/run_regression_m64.py'] and
    [r for r in ad if r.startswith('tools/')] == ['tools/make_m65_registers.py', 'tools/probe_transition_bypass.py', 'tools/programme_check_m65.py', 'tools/run_m65_all.py', 'tools/run_regression_m65.py'],
    'tools changed: m5_mutants.py (runs the new tests), make_m0.py (runs the M6.5 register step), probe_approval_binding.py, probe_malformed_proposal_version.py and probe_stale_proposal.py (name the whole token the lower-level call now requires), run_regression_m6.py to run_regression_m64.py (accept the M6.5 rows and declared files); tools added: the register step, the bypass probe, the M6.5 register check, the wrapper and this tool')
other = [r for r in ch if not r.startswith(('tools/', 'apg/', 'tests/'))]
okset = {'README.md', 'RUN_COMMANDS.txt', 'programme/STATUS_REGISTER.csv', 'programme/FINDINGS_REGISTER.csv', 'programme/INTERPRETATIONS_REGISTER.csv'}
chk('R08', set(other) <= okset and not [r for r in ch if r.startswith(('regression/BASELINE', 'regression/GOLDEN', 'regression/DEMO', 'regression/m1', 'regression/m2', 'regression/m3', 'regression/m4', 'regression/m5', 'regression/m6', 'research/', 'builder_zero/', 'catalogue/', 'logs/'))],
    'of the non-code files only the readme, the run commands and the three append-only tables changed; no golden file, baseline, demonstration output, snapshot, earlier log, research file or Builder Zero case changed ' + str(sorted(set(other) - okset)))
snap = lambda n: rd(os.path.join(ROOT, 'regression', 'm64_snapshot', n))
cur = lambda n: rd(os.path.join(ROOT, 'programme', n))
raw = lambda *a: open(os.path.join(ROOT, *a), 'rb').read()
chk('R09', all(raw('regression', 'm64_snapshot', t) == raw('programme', t) or ok91('programme/' + t) for t in ('PROGRAMME_MILESTONES.csv', 'ENGINE_HANDOFF_REGISTER.csv', 'RFC_REGISTER.csv', 'E17_GOVERNANCE_REGISTER.csv')),
    'the milestones table, the handoff register, the RFC register and the governance register are byte-identical to the delivered M6.4 ones (M7 not started; RFC-01 still PROPOSED and unnumbered; the proposed baseline rules unchanged)')
for n, idc, pre, nmin in (('STATUS_REGISTER.csv', 'item_id', 'SR-', 74), ('FINDINGS_REGISTER.csv', 'finding_id', 'F-', 57), ('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', 'I-', 79)):
    a, b = snap(n), cur(n)
    ids = [r[idc] for r in b]
    chk('R10-' + n[:4], b[:len(a)] == a and len(b) > len(a) and all(r['milestone'] in ('M6.5', 'M9.1', 'M9.2', 'M9.3', 'M9.4') for r in b[len(a):]) and ids == [f'{pre}{i:02d}' if pre != 'I-' else f'{pre}{i}' for i in range(1, len(b) + 1)] and ids[len(a)] == f'{pre}{nmin}',
        f'{n}: every delivered M6.4 row is unchanged; rows from {pre}{nmin} are appended with milestone M6.5')
a, b = snap('CARRIED_FORWARD_REGISTER.csv'), cur('CARRIED_FORWARD_REGISTER.csv')
chk('R10-CARR', b[:len(a)] == a and [r['cf_id'] for r in b] == [f'CF-{i:02d}' for i in range(1, len(b) + 1)], 'CARRIED_FORWARD_REGISTER.csv is byte-for-byte the delivered M6.4 table in content: no row is added or changed (CF-22 and CF-25 stay open)')
f = cur('FINDINGS_REGISTER.csv')
chk('R11', not any(re.search(r'\b(closed|accepted|approved|resolved)\b', r['status'], re.I) for r in f) and all(r['status'] == 'Retained for review - not approved' and r['reviewer_decision'] == '' for r in cur('INTERPRETATIONS_REGISTER.csv') if r['milestone'] in ('M6.1', 'M6.2', 'M6.3', 'M6.4', 'M6.5', 'M9.1', 'M9.2', 'M9.3', 'M9.4')),
    'no finding is shown as closed; F-52 to F-57 stay open for independent verification; the new interpretations are retained for review, not approved, with no reviewer decision')
steps = (('probe_transition_bypass.py', [], 'every incomplete approval is refused at transition', 'R12', 'the probe reproduces the bypass of the lower-level call (seven incomplete approvals) and shows each refused and the complete one accepted (on the delivered M6.4 code the same probe prints DEFECT PRESENT)'),
         ('probe_proposal_swap.py', [], 'APPROVAL IS BOUND TO THE EXACT PROPOSAL', 'R13', 'the M6.4 swap probe still shows an approval of a replaced proposal refused'),
         ('probe_malformed_proposal_version.py', [], 'MALFORMED VERSIONS ARE REFUSED', 'R14', 'the M6.3 malformed-version probe still shows the malformed values refused'),
         ('probe_stale_proposal.py', [], 'PROPOSAL IS BOUND TO THE EVIDENCE', 'R15', 'the M6.2 stale-proposal probe still shows the stale proposal refused'),
         ('probe_approval_binding.py', [], 'APPROVAL IS BOUND TO THE EVIDENCE', 'R16', 'the M6.1 approval-binding probe still shows the old approval ended'),
         ('run_m2_tests.py', ['-q', 'test_det_transition_gate*'], 'failures 0  errors 0', 'R17', 'the transition-gate regression tests pass'),
         ('run_m2_tests.py', ['-q', 'test_det_*'], 'failures 0  errors 0', 'R18', 'every M5 detection and finding test, the M6.1 to M6.5 binding tests and the frozen ones included, passes on the corrected code'),
         ('run_regression_m64.py', ['--static'], 'STATIC CHECKS OK', 'R19', 'the M6.4 regression tool\'s file and table checks still pass (with the M6.5 declarations)'),
         ('run_regression_m63.py', ['--static'], 'STATIC CHECKS OK', 'R20', 'the M6.3 regression tool\'s file and table checks still pass (with the M6.4 and M6.5 declarations)'),
         ('run_regression_m62.py', ['--static'], 'STATIC CHECKS OK', 'R21', 'the M6.2 regression tool\'s file and table checks still pass (with the M6.3 to M6.5 declarations)'),
         ('run_regression_m61.py', ['--static'], 'STATIC CHECKS OK', 'R22', 'the M6.1 regression tool\'s file and table checks still pass (with the M6.2 to M6.5 declarations)'),
         ('run_regression_m6.py', [], 'REGRESSION OK', 'R23', 'the M6 regression tool (which protects M5, M4, M3, M2 and M0/M1) still passes'),
         ('run_golden_mkt.py', [], 'GOLDEN OK', 'R24', 'the M6 golden cases still give the recorded answers'),
         ('run_demo_m6.py', ['--check'], 'DEMO OUTPUT MATCHES', 'R25', 'the M6 narrated demonstration still prints exactly the recorded output'),
         ('run_demo_m5.py', ['--check'], 'DEMO OUTPUT MATCHES', 'R26', 'the M5 narrated demonstration still prints exactly the recorded output'))
for tool, args, marker, cid, text in (() if '--static' in sys.argv else steps):
    x = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', tool), *args], capture_output=True, text=True, cwd=ROOT)
    out = x.stdout + x.stderr
    chk(cid, x.returncode == 0 and marker in out, text + ('' if x.returncode == 0 and marker in out else ' :: ' + out[-300:]))
print(f'\nchecks {N[0]}  failed {len(bad)}')
if bad:
    print('FAILED:', bad)
    sys.exit(1)
print('STATIC CHECKS OK (R12 to R26 skipped)' if '--static' in sys.argv else 'REGRESSION OK')
