#!/usr/bin/env python3
"""Regression protection for APG-M9.3, the correction of the session expiry check of the approval request boundary after the independent audit of APG-M9.2 (finding F-62).
Usage: python3 -I tools/run_regression_m93.py [--static | --step Rnn | --list]     (--static skips item 5; --step runs the file and table checks and only the named step of item 5, so a long run can be split; --list prints the steps)     Exit 0 only if every check passes.
 1. every file of the delivered M9.2 package that the correction was not meant to change is byte-identical to its recorded SHA-256 (regression/BASELINE_M92.json);
 2. the files it changed or added are exactly the declared ones, and each equals its recorded hash (a later edit is noticed);
 3. in the application code only apg/api/approval_boundary.py changed and none was added; no existing test file changed; the only test file added is the correction one;
 4. the programme tables differ from their delivered M9.2 versions only by appended rows (milestone M9.3); the milestones, handoff, RFC and governance tables are byte-identical; nothing is shown as closed;
 5. the expiry probe shows the gap corrected; the M9.3 and M9.2 correction tests, the earlier boundary tests and the contract suite pass; the earlier probes, the lifecycle tests, the earlier regression tools, the golden cases and the demonstrations still pass.
The delivered M5, M6, M6.1, M6.2, M6.3, M6.4, M6.5, M9.1 and M9.2 archives are not part of this package and are not changed by it.  This tool shows that M9.3 changed what it says it changed; it does not show that the correction is right: that is for the auditor's independent verification."""
import csv, hashlib, json, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
rd = lambda p: list(csv.DictReader(open(p, encoding='utf-8', newline='')))
bad = []
M92_ZIP = 'ad889d545a5ad91a100ff89425353b425a908fe23f50c44d0a11dd128247f1d8'
M92_DOCS = 'ebbb77f2e99e26fb6cc54ac710763b000737dc965a45f8f3fb358163ee7f7df0'
N = [0]
OPEN = 'Corrected in APG-M9.3 (builder-implemented); open until independently verified'


def chk(i, ok, t):
    N[0] += 1
    print(('PASS ' if ok else 'FAIL ') + i + ' ' + t)
    if not ok:
        bad.append(i)


steps = (('probe_m92_session_expiry.py', [], 'THE SESSION EXPIRY CHECK IS CORRECTED', 'R12', 'the expiry probe shows the impossible timestamps refused and a real leap day accepted (on the delivered M9.2 code the same probe prints DEFECT PRESENT five times)'),
         ('run_m2_tests.py', ['-q', 'test_api_m93*'], 'failures 0  errors 0', 'R13', 'the M9.3 correction tests pass (on the delivered M9.2 code the tests listed in logs/m93/new_tests_on_delivered_m92.log fail)'),
         ('run_m2_tests.py', ['-q', 'test_api_*'], 'failures 0  errors 0', 'R14', 'the boundary tests of M9.1 (unchanged), the M9.2 and M9.3 correction tests, the port-contract tests and the static tests of apg/api pass'),
         ('probe_m91_audit_findings.py', [], 'THE AUDIT FINDINGS ARE CORRECTED', 'R14b', 'the M9.2 audit-findings probe still shows its five items corrected'),
         ('run_m91_contracts.py', [], 'ALL CONTRACT CASES PASS', 'R15', 'the 14 cases of the ProjectActionPort contract pass on the in-memory reference'),
         ('probe_approval_boundary.py', [], 'THE BOUNDARY BEHAVES AS THE CONTRACT SAYS', 'R16', 'the M9.1 boundary probe still shows its six situations ending as the contract says'),
         ('probe_transition_bypass.py', [], 'every incomplete approval is refused at transition', 'R17', 'the M6.5 transition-bypass probe still shows every incomplete approval refused'),
         ('probe_proposal_swap.py', [], 'APPROVAL IS BOUND TO THE EXACT PROPOSAL', 'R18', 'the M6.4 swap probe still shows an approval of a replaced proposal refused'),
         ('probe_malformed_proposal_version.py', [], 'MALFORMED VERSIONS ARE REFUSED', 'R19', 'the M6.3 malformed-version probe still shows the malformed values refused'),
         ('probe_stale_proposal.py', [], 'PROPOSAL IS BOUND TO THE EVIDENCE', 'R20', 'the M6.2 stale-proposal probe still shows the stale proposal refused'),
         ('probe_approval_binding.py', [], 'APPROVAL IS BOUND TO THE EVIDENCE', 'R21', 'the M6.1 approval-binding probe still shows the old approval ended'),
         ('run_m2_tests.py', ['-q', 'test_det_*'], 'failures 0  errors 0', 'R22', 'every M5 detection and finding test, the M6.1 to M6.5 binding and gate tests included, passes unchanged'),
         ('run_regression_m92.py', ['--static'], 'STATIC CHECKS OK', 'R22b', 'the M9.2 regression tool\'s file and table checks still pass (with the M9.3 declarations)'),
         ('run_regression_m91.py', ['--static'], 'STATIC CHECKS OK', 'R23', 'the M9.1 regression tool\'s file and table checks still pass (with the M9.2 and M9.3 declarations)'),
         ('run_regression_m65.py', ['--static'], 'STATIC CHECKS OK', 'R24', 'the M6.5 regression tool\'s file and table checks still pass (with the M9.1 to M9.3 declarations)'),
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
B = json.load(open(os.path.join(ROOT, 'regression', 'BASELINE_M92.json')))
B94p = os.path.join(ROOT, 'regression', 'BASELINE_M93.json')
B94 = json.load(open(B94p)) if os.path.exists(B94p) else {'changed_in_m94': {}, 'added_in_m94': {}, 'not_compared': [], 'not_compared_prefix': '\0'}      # APG-M9.4 declares the files it changed against the delivered M9.3
ok94 = lambda r: r in B94['changed_in_m94'] and os.path.exists(os.path.join(ROOT, r)) and sha(os.path.join(ROOT, r)) == B94['changed_in_m94'][r]['m94_sha256']
chk('R01', B['m92_zip_sha256'] == M92_ZIP and B['m92_docs_sha256'] == M92_DOCS and B['m92_file_count'] == len(B['frozen']) + len(B['changed_in_m93']), 'the baseline names the delivered M9.2 ZIP and documents by hash and accounts for every one of its files')
diff = [r for r, h in B['frozen'].items() if not os.path.exists(os.path.join(ROOT, r)) or sha(os.path.join(ROOT, r)) != h]
chk('R02', not diff and len(B['frozen']) > 400, f"{len(B['frozen'])} files of the delivered M9.2 package are byte-identical to it " + str(diff[:5]))
drift = [r for r, v in B['changed_in_m93'].items() if (not os.path.exists(os.path.join(ROOT, r)) or sha(os.path.join(ROOT, r)) != v['m93_sha256'] or v['m93_sha256'] == v['m92_sha256']) and not ok94(r)]
drift += [r for r, h in B['added_in_m93'].items() if (not os.path.exists(os.path.join(ROOT, r)) or sha(os.path.join(ROOT, r)) != h) and not ok94(r)]
chk('R03', not drift, f"the {len(B['changed_in_m93'])} changed and {len(B['added_in_m93'])} added files equal their recorded hashes, and every changed file differs from M9.2 " + str(drift[:5]))
known = set(B['frozen']) | set(B['changed_in_m93']) | set(B['added_in_m93']) | set(B['not_compared']) | set(B94['added_in_m94']) | set(B94['not_compared'])
extra = []
for root, dns, fns in os.walk(ROOT):
    dns[:] = [d for d in dns if d != '__pycache__']
    extra += [r for r in (os.path.relpath(os.path.join(root, f), ROOT).replace(os.sep, '/') for f in fns) if r not in known and not r.startswith((B['not_compared_prefix'], B94['not_compared_prefix']))]
chk('R04', not extra, 'no file exists in the package beyond the M9.2 files and the declared additions ' + str(extra[:5]))
ch, ad = sorted(B['changed_in_m93']), sorted(B['added_in_m93'])
chk('R05', [r for r in ch if r.startswith('apg/')] == ['apg/api/approval_boundary.py'] and not [r for r in ad if r.startswith('apg/')], 'the only application code that changed is apg/api/approval_boundary.py; no application file was added (apg/det, apg/mkt and the rest, and the other four files of apg/api, are byte-identical to M9.2)')
chk('R06', not [r for r in ch if r.startswith('tests/')] and [r for r in ad if r.startswith('tests/')] == ['tests/test_api_m93_corrections.py'], 'no existing test file changed (the M9.1 and M9.2 tests are untouched); the only test file added is tests/test_api_m93_corrections.py')
chk('R07', [r for r in ch if r.startswith('tools/')] == ['tools/m91_mutants.py', 'tools/make_m0.py', 'tools/programme_check_m92.py', 'tools/run_regression_m6.py', 'tools/run_regression_m61.py', 'tools/run_regression_m62.py', 'tools/run_regression_m63.py', 'tools/run_regression_m64.py', 'tools/run_regression_m65.py', 'tools/run_regression_m91.py', 'tools/run_regression_m92.py'] and
    [r for r in ad if r.startswith('tools/')] == ['tools/make_m93_registers.py', 'tools/probe_m92_session_expiry.py', 'tools/programme_check_m93.py', 'tools/run_m93_all.py', 'tools/run_regression_m93.py'],
    'tools changed: m91_mutants.py (runs the M9.3 tests; the equivalent-mutant id moved again), make_m0.py (runs the M9.3 register step), programme_check_m92.py and run_regression_m6.py to run_regression_m92.py (accept the M9.3 rows, tables and declared files; every other check is unchanged); tools added: the register step, the expiry probe, the M9.3 register check, the wrapper and this tool')
other = [r for r in ch if not r.startswith(('tools/', 'apg/', 'tests/'))]
okset = {'README.md', 'RUN_COMMANDS.txt', 'programme/APPROVAL_REQUEST_BOUNDARY.md', 'programme/STATUS_REGISTER.csv', 'programme/INTERPRETATIONS_REGISTER.csv', 'programme/CARRIED_FORWARD_REGISTER.csv', 'programme/FINDINGS_REGISTER.csv'}
chk('R08', set(other) <= okset and not [r for r in ch if r.startswith(('regression/BASELINE', 'regression/GOLDEN', 'regression/DEMO', 'regression/m1', 'regression/m2', 'regression/m3', 'regression/m4', 'regression/m5', 'regression/m6', 'regression/m9', 'research/', 'builder_zero/', 'catalogue/', 'logs/'))],
    'of the non-code files only the readme, the run commands, the contract document and four programme tables changed; no golden file, baseline, demonstration output, snapshot, earlier log, research file or Builder Zero case changed ' + str(sorted(set(other) - okset)))
snap = lambda n: rd(os.path.join(ROOT, 'regression', 'm92_snapshot', n))
cur = lambda n: rd(os.path.join(ROOT, 'programme', n))
raw = lambda *a: open(os.path.join(ROOT, *a), 'rb').read()
same = ('RFC_REGISTER.csv', 'E17_GOVERNANCE_REGISTER.csv', 'PROGRAMME_MILESTONES.csv', 'ENGINE_HANDOFF_REGISTER.csv')
chk('R09', all(raw('regression', 'm92_snapshot', t) == raw('programme', t) for t in same), 'the RFC, governance, milestones and handoff tables are byte-identical to the delivered M9.2 ones (RFC-01 still PROPOSED and unnumbered; M7 not started; no new Engine entry)')
for n, idc, pre, nmin, last in (('STATUS_REGISTER.csv', 'item_id', 'SR-', 84, 86), ('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', 'I-', 93, 95), ('FINDINGS_REGISTER.csv', 'finding_id', 'F-', 62, 62)):
    a, b = snap(n), cur(n)
    ids = [r[idc] for r in b]
    chk('R10-' + n[:4], b[:len(a)] == a and len(b) > len(a) and all(r['milestone'] in ('M9.3', 'M9.4') for r in b[len(a):]) and ids == [f'{pre}{i:02d}' if pre != 'I-' else f'{pre}{i}' for i in range(1, len(b) + 1)] and ids[len(a)] == f'{pre}{nmin}' and ids[len(a) + (last - nmin)] == f'{pre}{last}',
        f'{n}: every delivered M9.2 row is unchanged; rows {pre}{nmin} to {pre}{last} are appended with milestone M9.3')
a, b = snap('CARRIED_FORWARD_REGISTER.csv'), cur('CARRIED_FORWARD_REGISTER.csv')
chk('R10-CARR', b[:len(a)] == a and [r['cf_id'] for r in b[len(a):]][:1] == ['CF-30'] and [r['cf_id'] for r in b] == [f'CF-{i:02d}' for i in range(1, len(b) + 1)],
    'CARRIED_FORWARD_REGISTER.csv: every delivered M9.2 row is unchanged (CF-22, CF-25 and CF-29 are not edited and stay open); CF-30 is appended')
f = cur('FINDINGS_REGISTER.csv')
chk('R11', not any(re.search(r'\b(closed|accepted|approved|resolved)\b', r['status'], re.I) for r in f) and not any(re.search(r'\b(closed|accepted|approved|resolved)\b', r['status'], re.I) for r in cur('CARRIED_FORWARD_REGISTER.csv'))
    and [r['status'] for r in f if r['milestone'] == 'M9.3'] == [OPEN] and [r['finding_id'] for r in f if r['milestone'] == 'M9.2'] == ['F-58', 'F-59', 'F-60', 'F-61']
    and all(r['status'] == 'Retained for review - not approved' and r['reviewer_decision'] == '' for r in cur('INTERPRETATIONS_REGISTER.csv') if r['milestone'] in ('M6.1', 'M6.2', 'M6.3', 'M6.4', 'M6.5', 'M9.1', 'M9.2', 'M9.3', 'M9.4')),
    'no finding and no carried-forward item is shown as closed; F-52 to F-62, CF-22, CF-25 and CF-29 stay open; the new interpretations are retained for review, not approved, with no reviewer decision')
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
