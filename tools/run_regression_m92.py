#!/usr/bin/env python3
"""Regression protection for APG-M9.2, the correction of the approval request boundary after the independent audit of APG-M9.1 (findings F-58 to F-61).
Usage: python3 -I tools/run_regression_m92.py [--static | --step Rnn | --list]     (--static skips item 5; --step runs the file and table checks and only the named step of item 5, so a long run can be split; --list prints the steps)     Exit 0 only if every check passes.
 1. every file of the delivered M9.1 package that the correction was not meant to change is byte-identical to its recorded SHA-256 (regression/BASELINE_M91.json);
 2. the files it changed or added are exactly the declared ones, and each equals its recorded hash (a later edit is noticed);
 3. in the application code only apg/api/approval_boundary.py changed and none was added; no existing test file changed; the only test file added is the correction one;
 4. the programme tables differ from their delivered M9.1 versions only by appended rows (milestone M9.2) and the handoff list of the M9 milestone row (EDR-32); the RFC and governance tables are byte-identical; nothing is shown as closed;
 5. the audit-findings probe shows the five defects corrected; the correction tests, the earlier boundary tests and the contract suite pass; the earlier probes, the lifecycle tests, the earlier regression tools, the golden cases and the demonstrations still pass.
The delivered M5, M6, M6.1, M6.2, M6.3, M6.4, M6.5 and M9.1 archives are not part of this package and are not changed by it.  This tool shows that M9.2 changed what it says it changed; it does not show that the correction is right: that is for the auditor's independent verification."""
import csv, hashlib, json, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
rd = lambda p: list(csv.DictReader(open(p, encoding='utf-8', newline='')))
bad = []
M91_ZIP = '12326469a951238f674013918f279b89a75f3ea471fa6c5cbcefd1df0496cb9f'
M91_DOCS = 'd6431737b0160ac2be1e50ec8a92bbd55c147720107b2045118e51704265f453'
N = [0]
OPEN = 'Corrected in APG-M9.2 (builder-implemented); open until independently verified'


def chk(i, ok, t):
    N[0] += 1
    print(('PASS ' if ok else 'FAIL ') + i + ' ' + t)
    if not ok:
        bad.append(i)


steps = (('probe_m91_audit_findings.py', [], 'THE AUDIT FINDINGS ARE CORRECTED', 'R12', 'the audit-findings probe shows the five defects corrected (on the delivered M9.1 code the same probe prints DEFECT PRESENT five times)'),
         ('run_m2_tests.py', ['-q', 'test_api_m92*'], 'failures 0  errors 0', 'R13', 'the correction tests pass (on the delivered M9.1 code 16 of the 24 fail or error)'),
         ('run_m2_tests.py', ['-q', 'test_api_*'], 'failures 0  errors 0', 'R14', 'the boundary tests of M9.1 (unchanged), the correction tests, the port-contract tests and the static tests of apg/api pass'),
         ('run_m91_contracts.py', [], 'ALL CONTRACT CASES PASS', 'R15', 'the 14 cases of the ProjectActionPort contract pass on the in-memory reference'),
         ('probe_approval_boundary.py', [], 'THE BOUNDARY BEHAVES AS THE CONTRACT SAYS', 'R16', 'the M9.1 boundary probe still shows its six situations ending as the contract says'),
         ('probe_transition_bypass.py', [], 'every incomplete approval is refused at transition', 'R17', 'the M6.5 transition-bypass probe still shows every incomplete approval refused'),
         ('probe_proposal_swap.py', [], 'APPROVAL IS BOUND TO THE EXACT PROPOSAL', 'R18', 'the M6.4 swap probe still shows an approval of a replaced proposal refused'),
         ('probe_malformed_proposal_version.py', [], 'MALFORMED VERSIONS ARE REFUSED', 'R19', 'the M6.3 malformed-version probe still shows the malformed values refused'),
         ('probe_stale_proposal.py', [], 'PROPOSAL IS BOUND TO THE EVIDENCE', 'R20', 'the M6.2 stale-proposal probe still shows the stale proposal refused'),
         ('probe_approval_binding.py', [], 'APPROVAL IS BOUND TO THE EVIDENCE', 'R21', 'the M6.1 approval-binding probe still shows the old approval ended'),
         ('run_m2_tests.py', ['-q', 'test_det_*'], 'failures 0  errors 0', 'R22', 'every M5 detection and finding test, the M6.1 to M6.5 binding and gate tests included, passes unchanged'),
         ('run_regression_m91.py', ['--static'], 'STATIC CHECKS OK', 'R23', 'the M9.1 regression tool\'s file and table checks still pass (with the M9.2 declarations)'),
         ('run_regression_m65.py', ['--static'], 'STATIC CHECKS OK', 'R24', 'the M6.5 regression tool\'s file and table checks still pass (with the M9.1 and M9.2 declarations)'),
         ('run_regression_m64.py', ['--static'], 'STATIC CHECKS OK', 'R25', 'the M6.4 regression tool\'s file and table checks still pass'),
         ('run_regression_m63.py', ['--static'], 'STATIC CHECKS OK', 'R26', 'the M6.3 regression tool\'s file and table checks still pass'),
         ('run_regression_m62.py', ['--static'], 'STATIC CHECKS OK', 'R27', 'the M6.2 regression tool\'s file and table checks still pass'),
         ('run_regression_m61.py', ['--static'], 'STATIC CHECKS OK', 'R28', 'the M6.1 regression tool\'s file and table checks still pass'),
         ('run_regression_m6.py', [], 'REGRESSION OK', 'R29', 'the M6 regression tool (which protects M5, M4, M3, M2 and M0/M1) still passes'),
         ('run_golden_mkt.py', [], 'GOLDEN OK', 'R30', 'the M6 golden cases still give the recorded answers'),
         ('run_demo_m6.py', ['--check'], 'DEMO OUTPUT MATCHES', 'R31', 'the M6 narrated demonstration still prints exactly the recorded output'),
         ('run_demo_m5.py', ['--check'], 'DEMO OUTPUT MATCHES', 'R32', 'the M5 narrated demonstration still prints exactly the recorded output'))
if '--list' in sys.argv:
    for tool, args, marker, cid, text in steps:
        print(cid, 'python3 -I tools/' + tool, ' '.join(args))
    sys.exit(0)
B = json.load(open(os.path.join(ROOT, 'regression', 'BASELINE_M91.json')))
B93p = os.path.join(ROOT, 'regression', 'BASELINE_M92.json')
B93 = json.load(open(B93p)) if os.path.exists(B93p) else {'changed_in_m93': {}, 'added_in_m93': {}, 'not_compared': [], 'not_compared_prefix': '\0'}      # APG-M9.3 declares the files it changed against the delivered M9.2
ok93 = lambda r: r in B93['changed_in_m93'] and os.path.exists(os.path.join(ROOT, r)) and sha(os.path.join(ROOT, r)) == B93['changed_in_m93'][r]['m93_sha256']
B94p = os.path.join(ROOT, 'regression', 'BASELINE_M93.json')
B94 = json.load(open(B94p)) if os.path.exists(B94p) else {'changed_in_m94': {}, 'added_in_m94': {}, 'not_compared': [], 'not_compared_prefix': '\0'}      # APG-M9.4 declares the files it changed against the delivered M9.3
ok94 = lambda r: r in B94['changed_in_m94'] and os.path.exists(os.path.join(ROOT, r)) and sha(os.path.join(ROOT, r)) == B94['changed_in_m94'][r]['m94_sha256']
_ok93 = ok93
ok93 = lambda r: _ok93(r) or ok94(r)          # a file M9.4 changed again is accepted when the M9.4 baseline pins its new hash
chk('R01', B['m91_zip_sha256'] == M91_ZIP and B['m91_docs_sha256'] == M91_DOCS and B['m91_file_count'] == len(B['frozen']) + len(B['changed_in_m92']), 'the baseline names the delivered M9.1 ZIP and documents by hash and accounts for every one of its files')
diff = [r for r, h in B['frozen'].items() if not os.path.exists(os.path.join(ROOT, r)) or sha(os.path.join(ROOT, r)) != h]
chk('R02', not diff and len(B['frozen']) > 400, f"{len(B['frozen'])} files of the delivered M9.1 package are byte-identical to it " + str(diff[:5]))
drift = [r for r, v in B['changed_in_m92'].items() if (not os.path.exists(os.path.join(ROOT, r)) or sha(os.path.join(ROOT, r)) != v['m92_sha256'] or v['m92_sha256'] == v['m91_sha256']) and not ok93(r)]
drift += [r for r, h in B['added_in_m92'].items() if (not os.path.exists(os.path.join(ROOT, r)) or sha(os.path.join(ROOT, r)) != h) and not ok93(r)]
chk('R03', not drift, f"the {len(B['changed_in_m92'])} changed and {len(B['added_in_m92'])} added files equal their recorded hashes, and every changed file differs from M9.1 " + str(drift[:5]))
known = set(B['frozen']) | set(B['changed_in_m92']) | set(B['added_in_m92']) | set(B['not_compared']) | set(B93['added_in_m93']) | set(B93['not_compared']) | set(B94['added_in_m94']) | set(B94['not_compared'])
extra = []
for root, dns, fns in os.walk(ROOT):
    dns[:] = [d for d in dns if d != '__pycache__']
    extra += [r for r in (os.path.relpath(os.path.join(root, f), ROOT).replace(os.sep, '/') for f in fns) if r not in known and not r.startswith((B['not_compared_prefix'], B93['not_compared_prefix'], B94['not_compared_prefix']))]
chk('R04', not extra, 'no file exists in the package beyond the M9.1 files and the declared additions ' + str(extra[:5]))
ch, ad = sorted(B['changed_in_m92']), sorted(B['added_in_m92'])
chk('R05', [r for r in ch if r.startswith('apg/')] == ['apg/api/approval_boundary.py'] and not [r for r in ad if r.startswith('apg/')], 'the only application code that changed is apg/api/approval_boundary.py; no application file was added (apg/det, apg/mkt and the rest, and the other four files of apg/api, are byte-identical to M9.1)')
chk('R06', not [r for r in ch if r.startswith('tests/')] and [r for r in ad if r.startswith('tests/')] == ['tests/test_api_m92_corrections.py'], 'no existing test file changed (the M9.1 boundary tests are untouched); the only test file added is tests/test_api_m92_corrections.py')
chk('R07', [r for r in ch if r.startswith('tools/')] == ['tools/m91_mutants.py', 'tools/make_m0.py', 'tools/programme_check_m91.py', 'tools/run_regression_m6.py', 'tools/run_regression_m61.py', 'tools/run_regression_m62.py', 'tools/run_regression_m63.py', 'tools/run_regression_m64.py', 'tools/run_regression_m65.py', 'tools/run_regression_m91.py'] and
    [r for r in ad if r.startswith('tools/')] == ['tools/make_m92_registers.py', 'tools/probe_m91_audit_findings.py', 'tools/programme_check_m92.py', 'tools/run_m92_all.py', 'tools/run_regression_m92.py'],
    'tools changed: m91_mutants.py (runs the correction tests; one equivalent-mutant id moved), make_m0.py (runs the M9.2 register step), programme_check_m91.py and run_regression_m6.py to run_regression_m91.py (accept the M9.2 rows, tables and declared files; every other check is unchanged); tools added: the register step, the audit-findings probe, the M9.2 register check, the wrapper and this tool')
other = [r for r in ch if not r.startswith(('tools/', 'apg/', 'tests/'))]
okset = {'README.md', 'RUN_COMMANDS.txt', 'programme/APPROVAL_REQUEST_BOUNDARY.md', 'programme/STATUS_REGISTER.csv', 'programme/INTERPRETATIONS_REGISTER.csv', 'programme/CARRIED_FORWARD_REGISTER.csv', 'programme/ENGINE_HANDOFF_REGISTER.csv', 'programme/PROGRAMME_MILESTONES.csv', 'programme/FINDINGS_REGISTER.csv'}
chk('R08', set(other) <= okset and not [r for r in ch if r.startswith(('regression/BASELINE', 'regression/GOLDEN', 'regression/DEMO', 'regression/m1', 'regression/m2', 'regression/m3', 'regression/m4', 'regression/m5', 'regression/m6', 'regression/m9', 'research/', 'builder_zero/', 'catalogue/', 'logs/'))],
    'of the non-code files only the readme, the run commands, the contract document and six programme tables changed; no golden file, baseline, demonstration output, snapshot, earlier log, research file or Builder Zero case changed ' + str(sorted(set(other) - okset)))
snap = lambda n: rd(os.path.join(ROOT, 'regression', 'm91_snapshot', n))
cur = lambda n: rd(os.path.join(ROOT, 'programme', n))
raw = lambda *a: open(os.path.join(ROOT, *a), 'rb').read()
chk('R09', all(raw('regression', 'm91_snapshot', t) == raw('programme', t) for t in ('RFC_REGISTER.csv', 'E17_GOVERNANCE_REGISTER.csv')), 'the RFC and governance tables are byte-identical to the delivered M9.1 ones (RFC-01 still PROPOSED and unnumbered; the proposed baseline rules unchanged)')
a, b = snap('PROGRAMME_MILESTONES.csv'), cur('PROGRAMME_MILESTONES.csv')
only9 = [x['milestone_id'] for x, y in zip(a, b) if x != y]
m9o, m9 = next(x for x in a if x['milestone_id'] == 'M9'), next(y for y in b if y['milestone_id'] == 'M9')
chk('R09b', len(a) == len(b) and only9 == ['M9'] and all(m9o[k] == m9[k] for k in m9o if k != 'handoff_register_entries') and m9['handoff_register_entries'] == m9o['handoff_register_entries'] + '; EDR-32' and all(y['status'] == 'Not started' for y in b if y['milestone_id'] in ('M7', 'M8', 'M10', 'M11', 'M12')),
    'the milestones table differs from the delivered M9.1 one in the handoff list of the M9 row only (EDR-32 added); M9 is still "In this delivery"; M7, M8 and M10 to M12 are not started')
a, b = snap('ENGINE_HANDOFF_REGISTER.csv'), cur('ENGINE_HANDOFF_REGISTER.csv')
chk('R09c', b[:len(a)] == a and [r['edr_id'] for r in b[len(a):]] == ['EDR-32'] and b[-1]['status'] == 'Open - described only' and b[-1]['evidence_seen'].startswith('No Engine code'), 'the handoff register: every delivered row is unchanged; EDR-32 (atomic persistence of a state change and its audit record) is appended, described only, no Engine code seen')
for n, idc, pre, nmin, last in (('STATUS_REGISTER.csv', 'item_id', 'SR-', 81, 83), ('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', 'I-', 88, 92), ('FINDINGS_REGISTER.csv', 'finding_id', 'F-', 58, 61)):
    a, b = snap(n), cur(n)
    ids = [r[idc] for r in b]
    chk('R10-' + n[:4], b[:len(a)] == a and len(b) > len(a) and all(r['milestone'] in ('M9.2', 'M9.3', 'M9.4') for r in b[len(a):]) and ids == [f'{pre}{i:02d}' if pre != 'I-' else f'{pre}{i}' for i in range(1, len(b) + 1)] and ids[len(a)] == f'{pre}{nmin}' and ids[len(a) + (last - nmin)] == f'{pre}{last}',
        f'{n}: every delivered M9.1 row is unchanged; rows {pre}{nmin} to {pre}{last} are appended with milestone M9.2')
a, b = snap('CARRIED_FORWARD_REGISTER.csv'), cur('CARRIED_FORWARD_REGISTER.csv')
chk('R10-CARR', b[:len(a)] == a and [r['cf_id'] for r in b[len(a):]][:2] == ['CF-28', 'CF-29'] and [r['cf_id'] for r in b] == [f'CF-{i:02d}' for i in range(1, len(b) + 1)],
    'CARRIED_FORWARD_REGISTER.csv: every delivered M9.1 row is unchanged (CF-22 and CF-25 are not edited and stay open); CF-28 and CF-29 are appended')
f = cur('FINDINGS_REGISTER.csv')
chk('R11', not any(re.search(r'\b(closed|accepted|approved|resolved)\b', r['status'], re.I) for r in f) and not any(re.search(r'\b(closed|accepted|approved|resolved)\b', r['status'], re.I) for r in cur('CARRIED_FORWARD_REGISTER.csv'))
    and [r['status'] for r in f if r['milestone'] == 'M9.2'] == [OPEN] * 4
    and all(r['status'] == 'Retained for review - not approved' and r['reviewer_decision'] == '' for r in cur('INTERPRETATIONS_REGISTER.csv') if r['milestone'] in ('M6.1', 'M6.2', 'M6.3', 'M6.4', 'M6.5', 'M9.1', 'M9.2', 'M9.3', 'M9.4')),
    'no finding and no carried-forward item is shown as closed; F-52 to F-61, CF-22 and CF-25 stay open; the new interpretations are retained for review, not approved, with no reviewer decision')
only = None
if '--step' in sys.argv:
    only = sys.argv[sys.argv.index('--step') + 1]
    assert only in [s[3] for s in steps], 'unknown step ' + only
for tool, args, marker, cid, text in (() if '--static' in sys.argv else steps):
    if only and cid != only:
        continue
    x = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', tool), *args], capture_output=True, text=True, cwd=ROOT)
    out = x.stdout + x.stderr
    chk(cid, x.returncode == 0 and marker in out, text + ('' if x.returncode == 0 and marker in out else ' :: ' + out[-300:]))
print(f'\nchecks {N[0]}  failed {len(bad)}')
if bad:
    print('FAILED:', bad)
    sys.exit(1)
print('STATIC CHECKS OK (R12 to R32 skipped)' if '--static' in sys.argv else ('STEP OK ' + only if only else 'REGRESSION OK'))
