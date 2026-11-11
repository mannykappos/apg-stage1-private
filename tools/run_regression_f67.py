#!/usr/bin/env python3
"""Regression checks of the correction release APG-F67 (finding F-67) against the delivered APG-MIE-1.1-R1 package (ZIP SHA-256
6afe8b6116cc46cd1db3161a80bc91bf4bb97b847fcdfa1fa4c2967bf17f1185, 1,049 files; hashes in regression/f67/R1_MANIFEST.sha256, the tables it appends to in
regression/f67/r1_snapshot/, and the R1 text of every changed code and test file in regression/f67/r1_originals/ for review by diff).
Usage: python3 -I tools/run_regression_f67.py --list | --static | --all | --step Rnn      (--static: R01 to R05, R10, R11; each other step runs one tool)
Exit 0 only if every step run passed."""
import ast, csv, hashlib, os, re, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
G = os.path.join(ROOT, 'regression', 'f67')
MAN = os.path.join(G, 'R1_MANIFEST.sha256')
SNAP = os.path.join(G, 'r1_snapshot')
ORIG = os.path.join(G, 'r1_originals')
CODE = {'apg/fin/policy.py', 'apg/det/policy.py', 'apg/mkt/policy.py',                                  # the correction
        'apg/fin/snap.py', 'apg/det/common.py', 'apg/mkt/common.py',                                     # a run counts only confirmed approvals
        'apg/fin/gather.py', 'apg/det/gather.py', 'apg/mkt/gather.py',                                   # a run pins the confirmations
        'apg/fin/demo_fin.py', 'apg/det/demo_det.py', 'apg/mkt/demo_mkt.py',                             # demonstration policies are proposals, approved in person
        'apg/fin/golden_fin.py', 'apg/det/golden_det.py', 'apg/mkt/golden_mkt.py', 'apg/rec/golden_rec.py', 'apg/fin/corpus_fin.py', 'apg/det/corpus_det.py'}
TESTS = {'tests/helpers_fin.py', 'tests/helpers_det.py', 'tests/helpers_mkt.py',
         'tests/test_det_detect.py', 'tests/test_det_golden.py', 'tests/test_det_policy.py', 'tests/test_fin_arith.py', 'tests/test_fin_boundaries.py',
         'tests/test_fin_golden.py', 'tests/test_fin_records.py', 'tests/test_mie_construction.py', 'tests/test_mkt_edges_policy.py', 'tests/test_mkt_golden.py',
         'tests/test_mkt_policy.py'}
RECORDS = {'README.md', 'RUN_COMMANDS.txt', 'programme/STATUS_REGISTER.csv', 'programme/INTERPRETATIONS_REGISTER.csv', 'programme/ENGINE_HANDOFF_REGISTER.csv',
           'programme/CARRIED_FORWARD_REGISTER.csv', 'programme/AUDIT_DISPOSITION_REGISTER.csv'}
CHANGED = CODE | TESTS | RECORDS
RENAMED = {'tests/test_det_policy.py': {'test_a_stored_version_is_immutable_but_an_approval_can_be_appended':
                                        'test_a_stored_version_is_immutable_and_an_approval_is_added_only_by_approve_policy'}}   # the old name described the defect
ADDED_FILES = {'apg/policy_approval.py', 'tests/test_f67_policy_approval.py', 'tools/probe_f67.py', 'tools/f67_mutants.py', 'tools/sabotage_f67.py',
               'tools/run_regression_f67.py', 'tools/run_f67_all.py', 'tools/make_f67_registers.py', 'programme/CHANGE_RECORD_APG-F67.md'}
ADDED_PREFIXES = ('regression/f67/', 'logs/f67/')
TABLES = ('STATUS_REGISTER.csv', 'INTERPRETATIONS_REGISTER.csv', 'ENGINE_HANDOFF_REGISTER.csv', 'CARRIED_FORWARD_REGISTER.csv', 'AUDIT_DISPOSITION_REGISTER.csv')
NEW_ROWS = {'STATUS_REGISTER.csv': ['SR-111', 'SR-112'], 'INTERPRETATIONS_REGISTER.csv': ['I-128', 'I-129'], 'ENGINE_HANDOFF_REGISTER.csv': ['EDR-39'],
            'CARRIED_FORWARD_REGISTER.csv': ['CF-40'], 'AUDIT_DISPOSITION_REGISTER.csv': ['AD-03']}
CLAIMS = re.compile(r'production[- ]ready|ready for (production|release|use)|release[- ]ready|\bcertified\b|\bguarantee[sd]?\b|100 ?%|fully (tested|verified|covered)|'
                    r'\b(F-67|APG-F67|this release|this package|the release|the correction) (is|was|has been) (accepted|approved|signed off|verified)\b|F-67 (is )?closed', re.I)
results = []


def sh(p):
    return hashlib.sha256(open(os.path.join(ROOT, p), 'rb').read()).hexdigest()


def files():
    out = []
    for d, ds, fs in os.walk(ROOT):
        ds[:] = [x for x in ds if x != '__pycache__']
        out += [os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/') for f in fs]
    return sorted(out)


def rows(path):
    return list(csv.DictReader(open(path, encoding='utf-8', newline='')))


def manifest():
    return {line[66:].rstrip('\n'): line[:64] for line in open(MAN, encoding='utf-8')}


def r01():
    m = manifest()
    bad = [p for p, h in m.items() if p not in CHANGED and (not os.path.exists(os.path.join(ROOT, p)) or sh(p) != h)]
    same = [p + ' (declared changed, but identical)' for p in sorted(CHANGED) if p not in m or sh(p) == m[p]]
    return (not bad and not same and len(m) == 1049, 'every one of the 1,049 MIE-1.1-R1 files is byte-identical except the declared changes (%d code, %d test, %d records)'
            % (len(CODE), len(TESTS), len(RECORDS)), bad[:5] + same)


def r02():
    m = manifest()
    extra = [p for p in files() if p not in m]
    undeclared = [p for p in extra if not (p in ADDED_FILES or p.startswith(ADDED_PREFIXES))]
    missing = [p for p in ADDED_FILES if p not in extra]
    orig = [p for p in sorted(CODE | TESTS) if not os.path.exists(os.path.join(ORIG, p)) or hashlib.sha256(open(os.path.join(ORIG, p), 'rb').read()).hexdigest() != m[p]]
    return not undeclared and not missing and not orig, ('every file beyond MIE-1.1-R1 is a declared F-67 addition, and regression/f67/r1_originals holds the exact R1 text of '
                                                          'every changed code and test file'), undeclared + missing + orig


def r03():
    with tempfile.TemporaryDirectory() as td:
        for n in os.listdir(SNAP):
            shutil.copy(os.path.join(SNAP, n), td)
        r = subprocess.run([sys.executable, '-I', '-B', os.path.join(ROOT, 'tools', 'make_f67_registers.py'), td], capture_output=True, text=True)
        bad = [n for n in TABLES if open(os.path.join(td, n), 'rb').read() != open(os.path.join(ROOT, 'programme', n), 'rb').read()]
    for n in TABLES:
        old, new = rows(os.path.join(SNAP, n)), rows(os.path.join(ROOT, 'programme', n))
        if new[:len(old)] != old or [list(x.values())[0] for x in new[len(old):]] != NEW_ROWS[n]:
            bad.append('%s is not the R1 rows plus %s' % (n, NEW_ROWS[n]))
    return r.returncode == 0 and not bad, ('the five tables are exactly what tools/make_f67_registers.py makes from the R1 tables: SR-111, SR-112, I-128, I-129, EDR-39, CF-40 '
                                           'and AD-03 appended; no existing row changed; the findings register is byte-identical (R01)'), bad + ([r.stderr[-300:]] if r.returncode else [])


def r04():
    P = os.path.join(ROOT, 'programme')
    f = {r['finding_id']: r for r in rows(os.path.join(P, 'FINDINGS_REGISTER.csv'))}
    st = {r['item_id']: r for r in rows(os.path.join(P, 'STATUS_REGISTER.csv'))}
    cf = {r['cf_id']: r['status'] for r in rows(os.path.join(P, 'CARRIED_FORWARD_REGISTER.csv'))}
    edr = {r['edr_id']: r['status'] for r in rows(os.path.join(P, 'ENGINE_HANDOFF_REGISTER.csv'))}
    ad = {r['disposition_id']: r for r in rows(os.path.join(P, 'AUDIT_DISPOSITION_REGISTER.csv'))}
    it = {r['interpretation_id']: r for r in rows(os.path.join(P, 'INTERPRETATIONS_REGISTER.csv'))}
    bad = []
    if f['F-67']['status'] != 'Open - not corrected':
        bad.append('the F-67 findings row was edited')
    if st['SR-111']['evidence_ladder_status'] != 'Local-tested' or 'no independent review' not in st['SR-111']['claim_limit']:
        bad.append('SR-111 claims more than local testing')
    if 'open until the independent auditor verifies' not in it['I-129']['builder_reading'] or 'LIMIT' not in it['I-128']['builder_reading']:
        bad.append('I-128 or I-129 lost the limit or the open status')
    a3 = ad.get('AD-03', {})
    if '30-second' not in a3.get('what_is_not_independently_verified', '') or 'not an identical rerun' not in a3.get('what_is_not_independently_verified', '') \
            or '624 mutants, 621 killed, 3 documented equivalents' not in a3.get('what_the_auditor_reproduced', ''):
        bad.append('AD-03 does not record the result with the timeout qualification')
    if 'does not accept the MIE-1.1 release' not in a3.get('what_this_does_not_mean', ''):
        bad.append('AD-03 does not say it is not a release acceptance')
    for k in ('CF-36', 'CF-37', 'CF-38', 'CF-39', 'CF-40'):
        if not cf[k].startswith('Open'):
            bad.append(k + ' is not open')
    for k in ('EDR-34', 'EDR-36', 'EDR-37', 'EDR-38', 'EDR-39'):
        if not edr[k].startswith('Open'):
            bad.append(k + ' is not open')
    return not bad, ('F-67 keeps its findings row and stays open until verified; SR-111 is Local-tested only; I-128 states the limit; AD-03 records the auditor\'s completed '
                     'MIE-1.1 mutation run with the 30-second timeout qualification and no release acceptance; CF-36 to CF-40 and EDR-34, EDR-36 to EDR-39 stay open'), bad


def r05():
    bad = []
    for p in ('README.md', 'programme/CHANGE_RECORD_APG-F67.md'):
        text = open(os.path.join(ROOT, p), encoding='utf-8').read()
        if p == 'README.md':
            text = text.split('---- the MIE-1.1-R1 readme follows')[0] if text.startswith('# APG F-67') else ''
            if not text:
                bad.append('README.md does not start with the F-67 section')
        for need in ('builder', 'open until', 'M8', 'authoris'):
            if need not in text:
                bad.append('%s does not mention %r' % (p, need))
        bad += ['%s: %r' % (p, text[max(0, m.start() - 40):m.end() + 20]) for m in CLAIMS.finditer(text)]
    return not bad, 'the F-67 text makes no acceptance, verification or readiness claim, keeps F-67 open, and states how the build was authorised and that M8 is not started', bad[:5]


def _names(path):
    return {n.name for n in ast.walk(ast.parse(open(path, encoding='utf-8').read())) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}


def r10():
    bad = []
    for p in sorted(TESTS):
        if not os.path.basename(p).startswith('test_'):
            continue
        old, new = _names(os.path.join(ORIG, p)), _names(os.path.join(ROOT, p))
        ren = RENAMED.get(p, {})
        want = {ren.get(n, n) for n in old}
        if want != new:
            bad.append('%s: removed %s, added %s' % (p, sorted(want - new), sorted(new - want)))
    return not bad, 'no test of MIE-1.1-R1 is removed or added in an edited file; one test is renamed because its old name described the defect', bad


def r11():
    bad = []
    for p in ('apg/fin/policy.py', 'apg/det/policy.py', 'apg/mkt/policy.py'):
        tree = ast.parse(open(os.path.join(ROOT, p), encoding='utf-8').read())
        fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        if 'approve' in fns:
            bad.append(p + ': the caller-asserted approve() is still present')
        for name in ('store_policy', 'store_spec', 'approve_policy', 'approve_spec'):
            if name in fns:
                src = ast.unparse(fns[name])
                if ('PA.store(' if name.startswith('store') else 'PA.approve(') not in src:
                    bad.append('%s: %s does not go through apg/policy_approval.py' % (p, name))
        for name in ('is_approved',):
            if 'PA.counted(' not in ast.unparse(fns[name]):
                bad.append('%s: is_approved does not count only confirmed approvals' % p)
    for p, call in (('apg/fin/gather.py', 'PA.confirmations('), ('apg/det/gather.py', 'PA.confirmations('), ('apg/mkt/gather.py', 'PA.confirmations('),
                    ('apg/fin/snap.py', 'PA.pinned('), ('apg/det/common.py', 'PA.pinned('), ('apg/mkt/common.py', 'PA.pinned(')):
        if call not in open(os.path.join(ROOT, p), encoding='utf-8').read():
            bad.append('%s does not call %s' % (p, call))
    return not bad, ('static: no caller-asserted approve() remains; every store and approval goes through apg/policy_approval.py; is_approved counts only confirmed approvals; '
                     'the gatherers pin the confirmations and the loaders read only the pinned ones'), bad


def run(args, what, expect, timeout=3600):
    try:
        r = subprocess.run([sys.executable, '-I'] + args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, what + ' (INCOMPLETE: cut off by the time limit)', []
    out = r.stdout + r.stderr
    return r.returncode == 0 and expect in out, what, out.strip().splitlines()[-1:]


def runs(cmds, what):
    for args, expect in cmds:
        ok, _, detail = run(args, what, expect)
        if not ok:
            return False, what, [' '.join(args)] + detail
    return True, what, ''


STEPS = {'R01': r01, 'R02': r02, 'R03': r03, 'R04': r04, 'R05': r05,
         'R06': lambda: run(['tools/probe_f67.py'], 'the F-67 probe reports every case corrected and the control counted', 'F-67 IS CORRECTED'),
         'R07': lambda: run(['tools/run_m2_tests.py', '-q', 'test_f67_policy_approval.py'], 'the F-67 correction tests pass (12)', 'tests 12  failures 0  errors 0'),
         'R08': lambda: runs([(['tools/probe_m7_audit_findings.py'], 'THE AUDIT FINDINGS ARE CORRECTED'), (['tools/probe_m71_race.py'], 'THE RACE IS CLOSED'),
                              (['tools/probe_m72_insert_race.py'], 'THE INSERT RACE IS CLOSED'), (['tools/probe_mie1_audit_findings.py'], 'THE MIE-1 AUDIT FINDINGS ARE CORRECTED')],
                             'the earlier audit-findings probes (M7, M7.1, M7.2, MIE-1) still report every case corrected'),
         'R09': lambda: runs([(['tools/run_golden_fin.py'], 'GOLDEN OK'), (['tools/run_golden_det.py'], 'GOLDEN OK'), (['tools/run_golden_mkt.py'], 'GOLDEN OK'),
                              (['tools/run_m2_tests.py', '-q', 'test_rec_golden.py'], 'failures 0  errors 0'), (['tools/run_golden_mie1.py'], 'THE GOLDEN MIE-1 RUN EQUALS')],
                             'the golden Builder Zero runs (financial, detection, procurement, recommendations, MIE-1) are unchanged'),
         'R10': r10, 'R11': r11}
STATIC = ['R01', 'R02', 'R03', 'R04', 'R05', 'R10', 'R11']


def main():
    a = sys.argv[1:]
    if not a or a[0] == '--list':
        print('steps:', ' '.join(STEPS), '  (--static:', ' '.join(STATIC) + ')')
        return 0
    want = list(STEPS) if a[0] == '--all' else STATIC if a[0] == '--static' else [a[1]]
    for k in want:
        ok, what, detail = STEPS[k]()
        results.append((k, ok))
        print('%s %s %s %s' % ('PASS' if ok else 'FAIL', k, what, detail if not ok or detail else ''), flush=True)
    failed = [k for k, ok in results if not ok]
    print('\nchecks %d  failed %d' % (len(results), len(failed)) + ('\nFAILED: %r' % failed if failed else ''))
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
