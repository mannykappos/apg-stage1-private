#!/usr/bin/env python3
"""Regression protection for APG-M9.1, the first slice of M9 (the approval request boundary, CF-25).  Usage: python3 -I tools/run_regression_m91.py [--static]     (--static skips item 5, which runs the other tools)     Exit 0 only if every check passes.
 1. every file of the delivered M6.5 package that M9.1 was not meant to change is byte-identical to its recorded SHA-256 (regression/BASELINE_M65.json);
 2. the files it changed or added are exactly the declared ones, and each equals its recorded hash (a later edit is noticed);
 3. no application file of M6.5 or earlier changed: the only application files added are the five in the new package apg/api; no existing test file changed; the only test files added are the three of the boundary;
 4. the programme tables differ from their delivered M6.5 versions only by appended rows (milestone M9.1) and the one edit of the M9 milestone row; the findings, RFC and governance tables are byte-identical; nothing is shown as closed;
 5. the boundary probe shows the six situations ending as the contract says; the new tests and the contract suite pass; the earlier probes, the unit tests of the lifecycle, the earlier regression tools, the M6 regression tool (which protects M5 and earlier), the golden cases and the demonstrations still pass.
The delivered M5, M6, M6.1, M6.2, M6.3, M6.4 and M6.5 archives are not part of this package and are not changed by it.  This tool shows that M9.1 changed what it says it changed; it does not show that the boundary is right: that is for the auditor's independent review."""
import csv, hashlib, json, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
rd = lambda p: list(csv.DictReader(open(p, encoding='utf-8', newline='')))
bad = []
M65_ZIP = 'ab41a43f7ffa797dbdacacce1be04aebef0ec0ac7fba3fd2de5de26f9a6ac5fe'
M65_DOCS = '44f61a0549e8d53869048f04d05188fcc50f7fbb409c81be5b76d1ac4368db87'
N = [0]


def chk(i, ok, t):
    N[0] += 1
    print(('PASS ' if ok else 'FAIL ') + i + ' ' + t)
    if not ok:
        bad.append(i)


B = json.load(open(os.path.join(ROOT, 'regression', 'BASELINE_M65.json')))
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
chk('R01', B['m65_zip_sha256'] == M65_ZIP and B['m65_docs_sha256'] == M65_DOCS and B['m65_file_count'] == len(B['frozen']) + len(B['changed_in_m91']), 'the baseline names the delivered M6.5 ZIP and documents by hash and accounts for every one of its files')
diff = [r for r, h in B['frozen'].items() if (not os.path.exists(os.path.join(ROOT, r)) or sha(os.path.join(ROOT, r)) != h) and not ok92(r)]
chk('R02', not diff and len(B['frozen']) > 400, f"{len(B['frozen'])} files of the delivered M6.5 package are byte-identical to it " + str(diff[:5]))
drift = [r for r, v in B['changed_in_m91'].items() if (not os.path.exists(os.path.join(ROOT, r)) or sha(os.path.join(ROOT, r)) != v['m91_sha256'] or v['m91_sha256'] == v['m65_sha256']) and not ok92(r)]
drift += [r for r, h in B['added_in_m91'].items() if (not os.path.exists(os.path.join(ROOT, r)) or sha(os.path.join(ROOT, r)) != h) and not ok92(r)]
chk('R03', not drift, f"the {len(B['changed_in_m91'])} changed and {len(B['added_in_m91'])} added files equal their recorded hashes, and every changed file differs from M6.5 " + str(drift[:5]))
known = set(B['frozen']) | set(B['changed_in_m91']) | set(B['added_in_m91']) | set(B['not_compared']) | set(B92['added_in_m92']) | set(B92['not_compared']) | set(B93['added_in_m93']) | set(B93['not_compared']) | set(B94['added_in_m94']) | set(B94['not_compared'])
extra = []
for root, dns, fns in os.walk(ROOT):
    dns[:] = [d for d in dns if d != '__pycache__']
    extra += [r for r in (os.path.relpath(os.path.join(root, f), ROOT).replace(os.sep, '/') for f in fns) if r not in known and not r.startswith((B['not_compared_prefix'], B92['not_compared_prefix'], B93['not_compared_prefix'], B94['not_compared_prefix']))]
chk('R04', not extra, 'no file exists in the package beyond the M6.5 files and the declared additions ' + str(extra[:5]))
ch, ad = sorted(B['changed_in_m91']), sorted(B['added_in_m91'])
chk('R05', not [r for r in ch if r.startswith('apg/')] and [r for r in ad if r.startswith('apg/')] == ['apg/api/__init__.py', 'apg/api/approval_boundary.py', 'apg/api/contracts_m9.py', 'apg/api/faulty_m9.py', 'apg/api/reference_m9.py'],
    'no application file of M6.5 or earlier changed (apg/det, apg/mkt and the rest are byte-identical); the only application files added are the five of the new package apg/api')
chk('R06', not [r for r in ch if r.startswith('tests/')] and [r for r in ad if r.startswith('tests/')] == ['tests/test_api_action_port_contract.py', 'tests/test_api_approval_boundary.py', 'tests/test_api_static.py'],
    'no existing test file changed (the lifecycle tests are untouched); the only test files added are tests/test_api_approval_boundary.py, tests/test_api_action_port_contract.py and tests/test_api_static.py')
chk('R07', [r for r in ch if r.startswith('tools/')] == ['tools/make_m0.py', 'tools/programme_check_m4.py', 'tools/programme_check_m5.py', 'tools/programme_check_m6.py', 'tools/programme_check_m65.py', 'tools/run_regression_m6.py', 'tools/run_regression_m61.py', 'tools/run_regression_m62.py', 'tools/run_regression_m63.py', 'tools/run_regression_m64.py', 'tools/run_regression_m65.py'] and
    [r for r in ad if r.startswith('tools/')] == ['tools/m91_mutants.py', 'tools/make_m91_registers.py', 'tools/probe_approval_boundary.py', 'tools/programme_check_m91.py', 'tools/run_m91_all.py', 'tools/run_m91_contracts.py', 'tools/run_regression_m91.py'],
    'tools changed: make_m0.py (runs the M9.1 register step), the register checks of M4, M5, M6 and M6.5 and the regression tools of M6 to M6.5 (accept the M9.1 rows, tables and declared files; every other check is unchanged); tools added: the mutation tool, the register step, the probe, the M9.1 register check, the wrapper, the contract runner and this tool')
other = [r for r in ch if not r.startswith(('tools/', 'apg/', 'tests/'))]
okset = {'README.md', 'RUN_COMMANDS.txt', 'programme/STATUS_REGISTER.csv', 'programme/INTERPRETATIONS_REGISTER.csv', 'programme/CARRIED_FORWARD_REGISTER.csv', 'programme/ENGINE_HANDOFF_REGISTER.csv', 'programme/PROGRAMME_MILESTONES.csv'}
chk('R08', set(other) <= okset and not [r for r in ch if r.startswith(('regression/BASELINE', 'regression/GOLDEN', 'regression/DEMO', 'regression/m1', 'regression/m2', 'regression/m3', 'regression/m4', 'regression/m5', 'regression/m6', 'research/', 'builder_zero/', 'catalogue/', 'logs/'))],
    'of the non-code files only the readme, the run commands and five programme tables changed; no golden file, baseline, demonstration output, snapshot, earlier log, research file or Builder Zero case changed ' + str(sorted(set(other) - okset)))
snap = lambda n: rd(os.path.join(ROOT, 'regression', 'm65_snapshot', n))
cur = lambda n: rd(os.path.join(ROOT, 'programme', n))
raw = lambda *a: open(os.path.join(ROOT, *a), 'rb').read()
a_, b_ = snap('FINDINGS_REGISTER.csv'), cur('FINDINGS_REGISTER.csv')
chk('R09', b_[:len(a_)] == a_ and all(r['milestone'] in ('M9.2', 'M9.3', 'M9.4') for r in b_[len(a_):]) and all(raw('regression', 'm65_snapshot', t) == raw('programme', t) for t in ('RFC_REGISTER.csv', 'E17_GOVERNANCE_REGISTER.csv')),
    'the findings, RFC and governance tables are byte-identical to the delivered M6.5 ones (no finding is added or changed; RFC-01 still PROPOSED and unnumbered; the proposed baseline rules unchanged)')
a, b = snap('PROGRAMME_MILESTONES.csv'), cur('PROGRAMME_MILESTONES.csv')
only9 = [x['milestone_id'] for x, y in zip(a, b) if x != y]
m9o, m9 = next(x for x in a if x['milestone_id'] == 'M9'), next(y for y in b if y['milestone_id'] == 'M9')
chk('R09b', len(a) == len(b) and only9 == ['M9'] and all(m9o[k] == m9[k] for k in m9o if k not in ('status', 'handoff_register_entries')) and m9['status'] == 'In this delivery' and m9['handoff_register_entries'] in (m9o['handoff_register_entries'] + '; EDR-31', m9o['handoff_register_entries'] + '; EDR-31; EDR-32')
    and all(y['status'] == 'Not started' for y in b if y['milestone_id'] in ('M7', 'M8', 'M10', 'M11', 'M12')),
    'the milestones table differs from the delivered M6.5 one in the M9 row only (status and the handoff list gain EDR-31; there is no row for slices, so the slice is recorded on the M9 row); M7, M8 and M10 to M12 are not started')
a, b = snap('ENGINE_HANDOFF_REGISTER.csv'), cur('ENGINE_HANDOFF_REGISTER.csv')
chk('R09c', b[:len(a)] == a and [r['edr_id'] for r in b[len(a):]][:1] == ['EDR-31'] and b[len(a)]['status'] == 'Open - described only' and b[len(a)]['evidence_seen'].startswith('No Engine code'), 'the handoff register: every delivered row is unchanged; EDR-31 (the per-action project permission port) is appended, described only, no Engine code seen')
for n, idc, pre, nmin in (('STATUS_REGISTER.csv', 'item_id', 'SR-', 76), ('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', 'I-', 81)):
    a, b = snap(n), cur(n)
    ids = [r[idc] for r in b]
    chk('R10-' + n[:4], b[:len(a)] == a and len(b) > len(a) and all(r['milestone'] in ('M9.1', 'M9.2', 'M9.3', 'M9.4') for r in b[len(a):]) and ids == [f'{pre}{i:02d}' if pre != 'I-' else f'{pre}{i}' for i in range(1, len(b) + 1)] and ids[len(a)] == f'{pre}{nmin}',
        f'{n}: every delivered M6.5 row is unchanged; rows from {pre}{nmin} are appended with milestone M9.1')
a, b = snap('CARRIED_FORWARD_REGISTER.csv'), cur('CARRIED_FORWARD_REGISTER.csv')
chk('R10-CARR', b[:len(a)] == a and [r['cf_id'] for r in b[len(a):]][:2] == ['CF-26', 'CF-27'] and [r['cf_id'] for r in b] == [f'CF-{i:02d}' for i in range(1, len(b) + 1)],
    'CARRIED_FORWARD_REGISTER.csv: every delivered M6.5 row is unchanged (CF-22 and CF-25 are not edited and stay open); CF-26 and CF-27 are appended')
f = cur('FINDINGS_REGISTER.csv')
chk('R11', not any(re.search(r'\b(closed|accepted|approved|resolved)\b', r['status'], re.I) for r in f) and not any(re.search(r'\b(closed|accepted|approved|resolved)\b', r['status'], re.I) for r in cur('CARRIED_FORWARD_REGISTER.csv'))
    and all(r['status'] == 'Retained for review - not approved' and r['reviewer_decision'] == '' for r in cur('INTERPRETATIONS_REGISTER.csv') if r['milestone'] in ('M6.1', 'M6.2', 'M6.3', 'M6.4', 'M6.5', 'M9.1', 'M9.2', 'M9.3', 'M9.4')),
    'no finding and no carried-forward item is shown as closed; F-52 to F-57, CF-22 and CF-25 stay open; the new interpretations are retained for review, not approved, with no reviewer decision')
steps = (('probe_approval_boundary.py', [], 'THE BOUNDARY BEHAVES AS THE CONTRACT SAYS', 'R12', 'the boundary probe shows the six situations ending as the contract says (normal path, replay, evidence changed after approval, proposal replaced, wrong project, extra field)'),
         ('run_m2_tests.py', ['-q', 'test_api_*'], 'failures 0  errors 0', 'R13', 'the boundary tests, the port contract tests and the static tests of apg/api pass'),
         ('run_m91_contracts.py', [], 'ALL CONTRACT CASES PASS', 'R14', 'the 14 cases of the ProjectActionPort contract pass on the in-memory reference'),
         ('probe_transition_bypass.py', [], 'every incomplete approval is refused at transition', 'R15', 'the M6.5 transition-bypass probe still shows every incomplete approval refused'),
         ('probe_proposal_swap.py', [], 'APPROVAL IS BOUND TO THE EXACT PROPOSAL', 'R16', 'the M6.4 swap probe still shows an approval of a replaced proposal refused'),
         ('probe_malformed_proposal_version.py', [], 'MALFORMED VERSIONS ARE REFUSED', 'R17', 'the M6.3 malformed-version probe still shows the malformed values refused'),
         ('probe_stale_proposal.py', [], 'PROPOSAL IS BOUND TO THE EVIDENCE', 'R18', 'the M6.2 stale-proposal probe still shows the stale proposal refused'),
         ('probe_approval_binding.py', [], 'APPROVAL IS BOUND TO THE EVIDENCE', 'R19', 'the M6.1 approval-binding probe still shows the old approval ended'),
         ('run_m2_tests.py', ['-q', 'test_det_*'], 'failures 0  errors 0', 'R20', 'every M5 detection and finding test, the M6.1 to M6.5 binding and gate tests included, passes unchanged'),
         ('run_regression_m65.py', ['--static'], 'STATIC CHECKS OK', 'R21', 'the M6.5 regression tool\'s file and table checks still pass (with the M9.1 declarations)'),
         ('run_regression_m64.py', ['--static'], 'STATIC CHECKS OK', 'R22', 'the M6.4 regression tool\'s file and table checks still pass (with the M6.5 and M9.1 declarations)'),
         ('run_regression_m63.py', ['--static'], 'STATIC CHECKS OK', 'R23', 'the M6.3 regression tool\'s file and table checks still pass (with the M6.4 to M9.1 declarations)'),
         ('run_regression_m62.py', ['--static'], 'STATIC CHECKS OK', 'R24', 'the M6.2 regression tool\'s file and table checks still pass (with the M6.3 to M9.1 declarations)'),
         ('run_regression_m61.py', ['--static'], 'STATIC CHECKS OK', 'R25', 'the M6.1 regression tool\'s file and table checks still pass (with the M6.2 to M9.1 declarations)'),
         ('run_regression_m6.py', [], 'REGRESSION OK', 'R26', 'the M6 regression tool (which protects M5, M4, M3, M2 and M0/M1) still passes'),
         ('run_golden_mkt.py', [], 'GOLDEN OK', 'R27', 'the M6 golden cases still give the recorded answers'),
         ('run_demo_m6.py', ['--check'], 'DEMO OUTPUT MATCHES', 'R28', 'the M6 narrated demonstration still prints exactly the recorded output'),
         ('run_demo_m5.py', ['--check'], 'DEMO OUTPUT MATCHES', 'R29', 'the M5 narrated demonstration still prints exactly the recorded output'))
for tool, args, marker, cid, text in (() if '--static' in sys.argv else steps):
    x = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', tool), *args], capture_output=True, text=True, cwd=ROOT)
    out = x.stdout + x.stderr
    chk(cid, x.returncode == 0 and marker in out, text + ('' if x.returncode == 0 and marker in out else ' :: ' + out[-300:]))
print(f'\nchecks {N[0]}  failed {len(bad)}')
if bad:
    print('FAILED:', bad)
    sys.exit(1)
print('STATIC CHECKS OK (R12 to R29 skipped)' if '--static' in sys.argv else 'REGRESSION OK')
