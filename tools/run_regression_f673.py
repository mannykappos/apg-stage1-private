#!/usr/bin/env python3
"""Regression checks of the correction release APG-F67.3 (finding F-74 and its defect class) against the delivered APG-F67.2 package (ZIP SHA-256
8f2cbf538cd979e102be3872d55ad5fc2dc41a20775e0b400b306ca95d32c706, 1,155 files; hashes in regression/f673/F672_MANIFEST.sha256, the tables it appends to in
regression/f673/f672_snapshot/, and the F67.2 text of every changed code file in regression/f673/f672_originals/ for review by diff).
Every step is short.  Usage: python3 -I tools/run_regression_f673.py --list | --static | --step Rnn | --all      (--static: R01 to R05, R10, R11, R12)
Exit 0 only if every step run passed."""
import ast, csv, hashlib, os, re, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
G = os.path.join(ROOT, 'regression', 'f673')
MAN = os.path.join(G, 'F672_MANIFEST.sha256')
SNAP = os.path.join(G, 'f672_snapshot')
ORIG = os.path.join(G, 'f672_originals')
CODE = {'apg/policy_approval.py', 'apg/rec/policy.py', 'apg/rec/engine.py', 'apg/fin/gather.py', 'apg/det/gather.py', 'apg/mkt/gather.py'}
TESTS = set()
RENAMED = {}
TABLES = ('FINDINGS_REGISTER.csv', 'STATUS_REGISTER.csv', 'INTERPRETATIONS_REGISTER.csv', 'ENGINE_HANDOFF_REGISTER.csv', 'CARRIED_FORWARD_REGISTER.csv')
RECORDS = {'README.md', 'RUN_COMMANDS.txt'} | {'programme/' + t for t in TABLES}
CHANGED = CODE | TESTS | RECORDS
ADDED_FILES = {'tests/test_f673_approval_integrity.py', 'apg/contracts/record_store_history_contract.py', 'tools/run_history_contract.py', 'tools/probe_f673.py',
               'tools/f673_mutants.py', 'tools/sabotage_f673.py', 'tools/run_regression_f673.py', 'tools/run_f673_all.py', 'tools/make_f673_registers.py',
               'programme/CHANGE_RECORD_APG-F67.3.md'}
ADDED_PREFIXES = ('regression/f673/', 'logs/f673/')
NEW_ROWS = {'FINDINGS_REGISTER.csv': ['F-74'], 'STATUS_REGISTER.csv': ['SR-117', 'SR-118'], 'INTERPRETATIONS_REGISTER.csv': ['I-132'], 'ENGINE_HANDOFF_REGISTER.csv': ['EDR-41'],
            'CARRIED_FORWARD_REGISTER.csv': ['CF-44']}
CLAIMS = re.compile(r'production[- ]ready|ready for (production|release|use)|release[- ]ready|\bcertified\b|\bguarantee[sd]?\b|100 ?%|fully (tested|verified|covered)|'
                    r'\b(F-67|F-72|F-73|F-74|APG-F67(\.[123])?|F-67\.[123]|this release|this package|the release|the correction) (is|was|has been) (accepted|approved|signed off|verified|ratified)\b|'
                    r'(F-67|F-72|F-73|F-74) (is )?closed|M8 (is|was|has been) (authorised|started)', re.I)
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
    return (not bad and not same and len(m) == 1155, 'every one of the 1,155 APG-F67.2 files is byte-identical except the declared changes (%d code files, %d test files, %d records); no existing test changed'
            % (len(CODE), len(TESTS), len(RECORDS)), bad[:5] + same)


def r02():
    m = manifest()
    extra = [p for p in files() if p not in m]
    undeclared = [p for p in extra if not (p in ADDED_FILES or p.startswith(ADDED_PREFIXES))]
    missing = [p for p in ADDED_FILES if p not in extra]
    orig = [p for p in sorted(CODE | TESTS) if not os.path.exists(os.path.join(ORIG, p)) or hashlib.sha256(open(os.path.join(ORIG, p), 'rb').read()).hexdigest() != m[p]]
    return not undeclared and not missing and not orig, ('every file beyond APG-F67.2 is a declared F-67.3 addition, and regression/f673/f672_originals holds the exact F67.2 '
                                                          'text of every changed code file'), undeclared + missing + orig


def r03():
    with tempfile.TemporaryDirectory() as td:
        for n in os.listdir(SNAP):
            shutil.copy(os.path.join(SNAP, n), td)
        r = subprocess.run([sys.executable, '-I', '-B', os.path.join(ROOT, 'tools', 'make_f673_registers.py'), td], capture_output=True, text=True)
        bad = [n for n in TABLES if open(os.path.join(td, n), 'rb').read() != open(os.path.join(ROOT, 'programme', n), 'rb').read()]
    for n in TABLES:
        old, new = rows(os.path.join(SNAP, n)), rows(os.path.join(ROOT, 'programme', n))
        if new[:len(old)] != old or [list(x.values())[0] for x in new[len(old):]] != NEW_ROWS[n]:
            bad.append('%s is not the F67.2 rows plus %s' % (n, NEW_ROWS[n]))
    return r.returncode == 0 and not bad, ('the five tables are exactly what tools/make_f673_registers.py makes from the F67.2 tables: F-74, SR-117, SR-118, I-132, EDR-41 and '
                                           'CF-44 appended; no existing row changed'), bad + ([r.stderr[-300:]] if r.returncode else [])


def r04():
    P = os.path.join(ROOT, 'programme')
    f = {r['finding_id']: r for r in rows(os.path.join(P, 'FINDINGS_REGISTER.csv'))}
    st = {r['item_id']: r for r in rows(os.path.join(P, 'STATUS_REGISTER.csv'))}
    cf = {r['cf_id']: r for r in rows(os.path.join(P, 'CARRIED_FORWARD_REGISTER.csv'))}
    edr = {r['edr_id']: r['status'] for r in rows(os.path.join(P, 'ENGINE_HANDOFF_REGISTER.csv'))}
    bad = []
    if f['F-67']['status'] != 'Open - not corrected':
        bad.append('the F-67 findings row was edited')
    for k in ('F-72', 'F-73', 'F-74'):
        if not f[k]['status'].endswith('open until independently verified'):
            bad.append(k + ' is not kept open until verified')
    for k in ('SR-117', 'SR-118'):
        if st[k]['evidence_ladder_status'] != 'Local-tested' or 'no independent review' not in st[k]['claim_limit']:
            bad.append(k + ' claims more than local testing')
    if cf['CF-41']['status'] != 'Recorded - deviation, not ratified (product owner decision 2026-10-20)':
        bad.append('CF-41 changed')
    for k in ('CF-36', 'CF-37', 'CF-38', 'CF-39', 'CF-40', 'CF-42', 'CF-43', 'CF-44'):
        if not cf[k]['status'].startswith('Open'):
            bad.append(k + ' is not open')
    if 'M8 is not authorised' not in cf['CF-44']['what_remains_open']:
        bad.append('CF-44 does not keep M8 unauthorised')
    for k in ('EDR-34', 'EDR-36', 'EDR-37', 'EDR-38', 'EDR-39', 'EDR-40', 'EDR-41'):
        if not edr[k].startswith('Open'):
            bad.append(k + ' is not open')
    return not bad, ('F-67 keeps its row; F-72, F-73 and F-74 stay open until verified; SR-117 and SR-118 are Local-tested only; CF-41 is unchanged; CF-36 to CF-40 and CF-42 '
                     'to CF-44 and EDR-34, EDR-36 to EDR-41 stay open; M8 is not authorised'), bad


def r05():
    bad = []
    for p in ('README.md', 'programme/CHANGE_RECORD_APG-F67.3.md'):
        text = open(os.path.join(ROOT, p), encoding='utf-8').read()
        if p == 'README.md':
            text = text.split('---- the APG-F67.2 readme follows')[0] if text.startswith('# APG F-67.3') else ''
            if not text:
                bad.append('README.md does not start with the F-67.3 section')
        for need in ('builder', 'open until', 'M8', 'Authorise F-67.3 correction release', 'threat model', 'EDR-41'):
            if need not in text:
                bad.append('%s does not mention %r' % (p, need))
        bad += ['%s: %r' % (p, text[max(0, m.start() - 40):m.end() + 20]) for m in CLAIMS.finditer(text)]
    return not bad, ('the F-67.3 text makes no acceptance, verification or readiness claim; keeps F-72 to F-74 open; quotes the F-67.3 authorisation; states the threat '
                     'model and EDR-41; M8 not authorised'), bad[:5]


def _names(path):
    return {n.name for n in ast.walk(ast.parse(open(path, encoding='utf-8').read())) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}


def r10():
    m = manifest()
    bad = [p for p in sorted(p for p in m if p.startswith('tests/')) if not os.path.exists(os.path.join(ROOT, p)) or sh(p) != m[p]]
    return not bad, 'every APG-F67.2 test file (and helper) is unchanged; the F-67.3 tests are in a new file', bad[:5]


def r11():
    bad = []
    pa = {n.name: n for n in ast.parse(open(os.path.join(ROOT, 'apg/policy_approval.py'), encoding='utf-8').read()).body if isinstance(n, ast.FunctionDef)}
    for need in ('holds', 'content', 'added_at', 'confirmed', 'confirmations'):
        if need not in pa:
            bad.append('apg/policy_approval.py has no ' + need)
    if 'holds(' not in ast.unparse(pa['confirmed']) or 'at)' not in ast.unparse(pa['confirmed']):
        bad.append('confirmed does not judge with holds at the given revision')
    h = ast.unparse(pa['holds'])
    if 'added_at(' not in h or 'content(' not in h or 'history(' not in h:
        bad.append('holds does not check the binding, the content and every revision')
    if 'r.revision' not in ast.unparse(pa['confirmations']):
        bad.append('confirmations does not judge an InputRef at its pinned revision')
    rp = {n.name: n for n in ast.parse(open(os.path.join(ROOT, 'apg/rec/policy.py'), encoding='utf-8').read()).body if isinstance(n, ast.FunctionDef)}
    if 'PA.holds(' not in ast.unparse(rp['verified_approvers']):
        bad.append('verified_approvers does not use holds')
    if "RP.verified_approvers(scoped, pol, refs[0].revision)" not in open(os.path.join(ROOT, 'apg/rec/engine.py'), encoding='utf-8').read():
        bad.append('the recommendation run does not judge at its pinned policy revision')
    for p, call, n in (('apg/fin/gather.py', 'PA.confirmations(scoped, [refs[k] for k in sorted(refs)])', 1), ('apg/det/gather.py', 'PA.confirmations(scoped, [pins[k] for k in sorted(pins)])', 2),
                       ('apg/mkt/gather.py', 'PA.confirmations(scoped, [pins[k] for k in sorted(pins)])', 1)):
        text = open(os.path.join(ROOT, p), encoding='utf-8').read()
        if text.count('PA.confirmations(') != n or text.count(call) != n:                  # every call (det has a project and a tenant gatherer) passes the pinned references
            bad.append('%s: %d of %d confirmation calls pass the pinned references' % (p, text.count(call), text.count('PA.confirmations(')))
    return not bad, ('static: confirmed judges with holds at the given revision; holds checks the binding, the content and every revision; the gatherers and the '
                     'recommendation run judge at their pinned revisions'), bad


def r12():
    return run(['tools/run_history_contract.py'], 'the record-store history contract passes on the reference store and catches every faulty store',
               'ALL HISTORY CASES PASS AND EVERY FAULTY STORE IS CAUGHT')


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
         'R06': lambda: run(['tools/probe_f673.py'], 'the F-74 probe reports every case corrected and the control counted', 'F-74 IS CORRECTED'),
         'R07': lambda: run(['tools/run_m2_tests.py', '-q', 'test_f673_approval_integrity.py'], 'the F-67.3 tests pass (12)', 'tests 12  failures 0  errors 0'),
         'R08': lambda: runs([(['tools/probe_f672.py'], 'F-73 IS CORRECTED'), (['tools/run_m2_tests.py', '-q', 'test_f672_forged_entry.py'], 'tests 11  failures 0  errors 0'),
                              (['tools/probe_f671.py'], 'F-72 IS CORRECTED'), (['tools/run_m2_tests.py', '-q', 'test_f671_approval_recovery.py'], 'tests 11  failures 0  errors 0'),
                              (['tools/probe_f67.py'], 'F-67 IS CORRECTED'), (['tools/run_m2_tests.py', '-q', 'test_f67_policy_approval.py'], 'tests 12  failures 0  errors 0'),
                              (['tools/probe_m7_audit_findings.py'], 'THE AUDIT FINDINGS ARE CORRECTED')],
                             'the F-73, F-72 and F-67 probes and tests and the M7 audit-findings probe still report every case corrected'),
         'R09': lambda: runs([(['tools/run_golden_fin.py'], 'GOLDEN OK'), (['tools/run_golden_det.py'], 'GOLDEN OK'), (['tools/run_golden_mkt.py'], 'GOLDEN OK'),
                              (['tools/run_m2_tests.py', '-q', 'test_rec_golden.py'], 'failures 0  errors 0')],
                             'the golden Builder Zero runs (financial, detection, procurement, recommendations) are unchanged'),
         'R10': r10, 'R11': r11, 'R12': r12}
STATIC = ['R01', 'R02', 'R03', 'R04', 'R05', 'R10', 'R11', 'R12']


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
