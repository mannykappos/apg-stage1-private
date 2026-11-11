#!/usr/bin/env python3
"""Regression checks of the correction release APG-F67.1 (finding F-72) against the delivered APG-F67 package (ZIP SHA-256
17badf419b26753caaa7a20592322738d6eee9b4e1be5b940f4453629bbaa958, 1,105 files; hashes in regression/f671/F67_MANIFEST.sha256, the tables it appends to in
regression/f671/f67_snapshot/, and the F67 text of every changed code file in regression/f671/f67_originals/ for review by diff).
Every step is short.  Usage: python3 -I tools/run_regression_f671.py --list | --static | --all | --step Rnn      (--static: R01 to R05, R10, R11)
Exit 0 only if every step run passed."""
import ast, csv, hashlib, os, re, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
G = os.path.join(ROOT, 'regression', 'f671')
MAN = os.path.join(G, 'F67_MANIFEST.sha256')
SNAP = os.path.join(G, 'f67_snapshot')
ORIG = os.path.join(G, 'f67_originals')
F67_ZIP = '17badf419b26753caaa7a20592322738d6eee9b4e1be5b940f4453629bbaa958'
CODE = {'apg/policy_approval.py', 'apg/fin/policy.py', 'apg/det/policy.py', 'apg/mkt/policy.py', 'apg/rec/policy.py'}
TABLES = ('FINDINGS_REGISTER.csv', 'STATUS_REGISTER.csv', 'INTERPRETATIONS_REGISTER.csv', 'ENGINE_HANDOFF_REGISTER.csv', 'CARRIED_FORWARD_REGISTER.csv')
RECORDS = {'README.md', 'RUN_COMMANDS.txt'} | {'programme/' + t for t in TABLES}
CHANGED = CODE | RECORDS
ADDED_FILES = {'tests/test_f671_approval_recovery.py', 'tools/probe_f671.py', 'tools/f671_mutants.py', 'tools/sabotage_f671.py', 'tools/run_regression_f671.py',
               'tools/run_f671_all.py', 'tools/run_test_files.py', 'tools/make_f671_registers.py', 'programme/CHANGE_RECORD_APG-F67.1.md'}
ADDED_PREFIXES = ('regression/f671/', 'logs/f671/')
NEW_ROWS = {'FINDINGS_REGISTER.csv': ['F-72'], 'STATUS_REGISTER.csv': ['SR-113', 'SR-114'], 'INTERPRETATIONS_REGISTER.csv': ['I-130'], 'ENGINE_HANDOFF_REGISTER.csv': ['EDR-40'],
            'CARRIED_FORWARD_REGISTER.csv': ['CF-41', 'CF-42']}
CLAIMS = re.compile(r'production[- ]ready|ready for (production|release|use)|release[- ]ready|\bcertified\b|\bguarantee[sd]?\b|100 ?%|fully (tested|verified|covered)|'
                    r'\b(F-67|F-72|APG-F67|APG-F67\.1|F-67\.1|this release|this package|the release|the correction) (is|was|has been) (accepted|approved|signed off|verified|ratified)\b|'
                    r'(F-67|F-72) (is )?closed|ratified the start', re.I)
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
    return (not bad and not same and len(m) == 1105, 'every one of the 1,105 APG-F67 files is byte-identical except the declared changes (%d code files, %d records); '
            'no existing test, tool or specification changed' % (len(CODE), len(RECORDS)), bad[:5] + same)


def r02():
    m = manifest()
    extra = [p for p in files() if p not in m]
    undeclared = [p for p in extra if not (p in ADDED_FILES or p.startswith(ADDED_PREFIXES))]
    missing = [p for p in ADDED_FILES if p not in extra]
    orig = [p for p in sorted(CODE) if not os.path.exists(os.path.join(ORIG, p)) or hashlib.sha256(open(os.path.join(ORIG, p), 'rb').read()).hexdigest() != m[p]]
    return not undeclared and not missing and not orig, ('every file beyond APG-F67 is a declared F-67.1 addition, and regression/f671/f67_originals holds the exact F67 text '
                                                          'of every changed code file'), undeclared + missing + orig


def r03():
    with tempfile.TemporaryDirectory() as td:
        for n in os.listdir(SNAP):
            shutil.copy(os.path.join(SNAP, n), td)
        r = subprocess.run([sys.executable, '-I', '-B', os.path.join(ROOT, 'tools', 'make_f671_registers.py'), td], capture_output=True, text=True)
        bad = [n for n in TABLES if open(os.path.join(td, n), 'rb').read() != open(os.path.join(ROOT, 'programme', n), 'rb').read()]
    for n in TABLES:
        old, new = rows(os.path.join(SNAP, n)), rows(os.path.join(ROOT, 'programme', n))
        if new[:len(old)] != old or [list(x.values())[0] for x in new[len(old):]] != NEW_ROWS[n]:
            bad.append('%s is not the F67 rows plus %s' % (n, NEW_ROWS[n]))
    return r.returncode == 0 and not bad, ('the five tables are exactly what tools/make_f671_registers.py makes from the F67 tables: F-72, SR-113, SR-114, I-130, EDR-40, CF-41 '
                                           'and CF-42 appended; no existing row changed'), bad + ([r.stderr[-300:]] if r.returncode else [])


def r04():
    P = os.path.join(ROOT, 'programme')
    f = {r['finding_id']: r for r in rows(os.path.join(P, 'FINDINGS_REGISTER.csv'))}
    st = {r['item_id']: r for r in rows(os.path.join(P, 'STATUS_REGISTER.csv'))}
    cf = {r['cf_id']: r for r in rows(os.path.join(P, 'CARRIED_FORWARD_REGISTER.csv'))}
    edr = {r['edr_id']: r['status'] for r in rows(os.path.join(P, 'ENGINE_HANDOFF_REGISTER.csv'))}
    bad = []
    if f['F-67']['status'] != 'Open - not corrected':
        bad.append('the F-67 findings row was edited')
    if not f['F-72']['status'].endswith('open until independently verified'):
        bad.append('F-72 is not kept open until verified')
    for k in ('SR-113', 'SR-114'):
        if st[k]['evidence_ladder_status'] != 'Local-tested' or 'no independent review' not in st[k]['claim_limit']:
            bad.append(k + ' claims more than local testing')
    c41 = cf.get('CF-41', {})
    if c41.get('status') != 'Recorded - deviation, not ratified (product owner decision 2026-10-20)' or 'without the required explicit authorisation' not in c41.get('topic', '') \
            or 'do not ratify it retroactively' not in c41.get('what_remains_open', '') or F67_ZIP not in c41.get('what_this_package_shows', ''):
        bad.append('CF-41 does not record APG-F67 as started without explicit authorisation and not ratified')
    for k in ('CF-36', 'CF-37', 'CF-38', 'CF-39', 'CF-40', 'CF-42'):
        if not cf[k]['status'].startswith('Open'):
            bad.append(k + ' is not open')
    if 'M8 is not authorised' not in cf['CF-42']['what_remains_open']:
        bad.append('CF-42 does not keep M8 unauthorised')
    for k in ('EDR-34', 'EDR-36', 'EDR-37', 'EDR-38', 'EDR-39', 'EDR-40'):
        if not edr[k].startswith('Open'):
            bad.append(k + ' is not open')
    return not bad, ('F-67 keeps its row; F-72 stays open until verified; SR-113 and SR-114 are Local-tested only; CF-41 records APG-F67 as started without explicit authorisation '
                     'and not ratified, with its ZIP unchanged; CF-36 to CF-40, CF-42 and EDR-34, EDR-36 to EDR-40 stay open; M8 is not authorised'), bad


def r05():
    bad = []
    for p in ('README.md', 'programme/CHANGE_RECORD_APG-F67.1.md'):
        text = open(os.path.join(ROOT, p), encoding='utf-8').read()
        if p == 'README.md':
            text = text.split('---- the APG-F67 readme follows')[0] if text.startswith('# APG F-67.1') else ''
            if not text:
                bad.append('README.md does not start with the F-67.1 section')
        for need in ('builder', 'open until', 'M8', 'without explicit authorisation', 'not ratified', 'Authorise F-67.1 correction release'):
            if need not in text:
                bad.append('%s does not mention %r' % (p, need))
        bad += ['%s: %r' % (p, text[max(0, m.start() - 40):m.end() + 20]) for m in CLAIMS.finditer(text)]
    return not bad, ('the F-67.1 text makes no acceptance, verification, ratification or readiness claim; keeps F-72 open; records APG-F67 as started without explicit '
                     'authorisation and not ratified; quotes the F-67.1 authorisation; M8 not authorised'), bad[:5]


def _names(path):
    return {n.name for n in ast.walk(ast.parse(open(path, encoding='utf-8').read())) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}


def r10():
    m = manifest()
    tests = sorted(p for p in m if p.startswith('tests/test_'))
    bad = [p for p in tests if not os.path.exists(os.path.join(ROOT, p)) or sh(p) != m[p]]
    return not bad, 'every one of the %d APG-F67 test files is unchanged (no test removed, renamed or edited); the F-67.1 tests are in a new file' % len(tests), bad[:5]


def r11():
    bad = []
    pa = ast.parse(open(os.path.join(ROOT, 'apg/policy_approval.py'), encoding='utf-8').read())
    fns = {n.name: n for n in pa.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    for need in ('ApprovalNotConfirmed', '_confirm', 'status', '_confirmed_after_error'):
        if need not in fns:
            bad.append('apg/policy_approval.py has no ' + need)
    ap = ast.unparse(fns['approve'])
    if ap.count('_confirm(') != 2 or 'scoped.log(event_type' in ap:
        bad.append('approve does not write the confirming event only through _confirm, on both paths')
    rp = ast.parse(open(os.path.join(ROOT, 'apg/rec/policy.py'), encoding='utf-8').read())
    rf = {n.name: n for n in rp.body if isinstance(n, ast.FunctionDef)}
    for need in ('_confirm', 'approval_status'):
        if need not in rf:
            bad.append('apg/rec/policy.py has no ' + need)
    if ast.unparse(rf['approve_policy']).count('_confirm(') != 2 or "scoped.log('rec.policy_approved'" in ast.unparse(rf['approve_policy']):
        bad.append('the recommendation approve_policy does not confirm only through _confirm, on both paths')
    for p, names in (('apg/fin/policy.py', ('approval_status',)), ('apg/det/policy.py', ('approval_status',)), ('apg/mkt/policy.py', ('approval_status', 'spec_approval_status'))):
        t = {n.name for n in ast.parse(open(os.path.join(ROOT, p), encoding='utf-8').read()).body if isinstance(n, ast.FunctionDef)}
        bad += ['%s has no %s' % (p, n) for n in names if n not in t]
    return not bad, ('static: every approval of the five records writes its confirming event only through _confirm (new and completing paths); ApprovalNotConfirmed, '
                     'status and approval_status exist for each record'), bad


def run(args, what, expect, timeout=1800):
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
         'R06': lambda: run(['tools/probe_f671.py'], 'the F-72 probe reports every case corrected and the control counted', 'F-72 IS CORRECTED'),
         'R07': lambda: run(['tools/run_m2_tests.py', '-q', 'test_f671_approval_recovery.py'], 'the F-67.1 recovery tests pass (11)', 'tests 11  failures 0  errors 0'),
         'R08': lambda: runs([(['tools/probe_f67.py'], 'F-67 IS CORRECTED'), (['tools/run_m2_tests.py', '-q', 'test_f67_policy_approval.py'], 'tests 12  failures 0  errors 0'),
                              (['tools/probe_m7_audit_findings.py'], 'THE AUDIT FINDINGS ARE CORRECTED')],
                             'the F-67 probe and tests and the M7 audit-findings probe (F-64 to F-66) still report every case corrected'),
         'R09': lambda: runs([(['tools/run_golden_fin.py'], 'GOLDEN OK'), (['tools/run_golden_det.py'], 'GOLDEN OK'), (['tools/run_golden_mkt.py'], 'GOLDEN OK'),
                              (['tools/run_m2_tests.py', '-q', 'test_rec_golden.py'], 'failures 0  errors 0')],
                             'the golden Builder Zero runs (financial, detection, procurement, recommendations) are unchanged'),
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
