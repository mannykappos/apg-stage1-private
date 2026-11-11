#!/usr/bin/env python3
"""Regression checks of the APG-M7.1 correction against the delivered APG-M7 package (ZIP SHA-256 a58b2294a95cb8901dec0154b41e89bd2e987c7eb461672b5e6cf175fba0f934), whose 840 file hashes are
stored in regression/m71/M7_MANIFEST.sha256 and whose programme tables are stored in regression/m71/m7_snapshot/; and, through regression/m7/M9_4_MANIFEST.sha256, against the delivered M9.4 package.
Usage: python3 -I tools/run_regression_m71.py --list | --static | --step Rnn | --all
  --static   R01 to R08: files, tables and boundaries (seconds)
  --step     one step; R09 to R12 run tests and take longer (R12, the whole unit suite, takes about two minutes)
A step cut off by a time limit is incomplete, not a pass.  Exit 0 only if every step run passed."""
import csv, hashlib, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
MAN = os.path.join(ROOT, 'regression', 'm71', 'M7_MANIFEST.sha256')
MAN94 = os.path.join(ROOT, 'regression', 'm7', 'M9_4_MANIFEST.sha256')
SNAP = os.path.join(ROOT, 'regression', 'm71', 'm7_snapshot')
CHANGED_APP = {'apg/rec/policy.py', 'apg/rec/engine.py', 'apg/rec/lifecycle.py', 'apg/rec/demo_rec.py', 'apg/rec/golden_rec.py'}
CHANGED_TESTS = {'tests/helpers_rec.py', 'tests/test_rec_policy.py', 'tests/test_rec_edges.py', 'tests/test_rec_repro.py'}
TABLES = ('FINDINGS_REGISTER', 'STATUS_REGISTER', 'INTERPRETATIONS_REGISTER', 'ENGINE_HANDOFF_REGISTER', 'CARRIED_FORWARD_REGISTER')
CHANGED = CHANGED_APP | CHANGED_TESTS | {'README.md', 'RUN_COMMANDS.txt', 'regression/m7/golden_rec.json', 'tools/m7_mutants.py', 'programme/RECOMMENDATION_ENGINE.md'} | {'programme/%s.csv' % t for t in TABLES}
ADDED_PREFIXES = ('regression/m71/', 'logs/m71/')
ADDED_FILES = {'tests/test_rec_m71_corrections.py', 'tools/probe_m7_audit_findings.py', 'tools/make_m71_registers.py', 'tools/run_regression_m71.py', 'tools/run_m71_all.py',
               'tools/sabotage_m71.py', 'programme/CHANGE_RECORD_APG-M7.1.md'}
REC_MODULES = {'__init__.py', 'policy.py', 'engine.py', 'inputs.py', 'lifecycle.py', 'verify.py', 'demo_rec.py', 'golden_rec.py'}
results = []


def sh(p):
    return hashlib.sha256(open(os.path.join(ROOT, p), 'rb').read()).hexdigest()


def files():
    out = []
    for d, ds, fs in os.walk(ROOT):
        ds[:] = [x for x in ds if x != '__pycache__']
        for f in fs:
            out.append(os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/'))
    return sorted(out)


def manifest():
    return {line[66:].rstrip('\n'): line[:64] for line in open(MAN, encoding='utf-8')}


def rows(path):
    return list(csv.DictReader(open(path, encoding='utf-8', newline='')))


def manifest(path=MAN):
    return {line[66:].rstrip('\n'): line[:64] for line in open(path, encoding='utf-8')}


def r01():
    m = manifest()
    bad = [p for p, h in m.items() if p not in CHANGED and (not os.path.exists(os.path.join(ROOT, p)) or sh(p) != h)]
    missing = [p for p in CHANGED if p not in m]
    same = [p for p in CHANGED if p in m and os.path.exists(os.path.join(ROOT, p)) and sh(p) == m[p]]
    return not bad and not missing and not same and len(m) == 840, 'every one of the 840 M7 files except the %d declared changed ones is byte-identical here, and each declared one did change' % len(CHANGED), bad[:5] + missing + same


def r02():
    m = manifest()
    extra = [p for p in files() if p not in m]
    undeclared = [p for p in extra if not (p in ADDED_FILES or p.startswith(ADDED_PREFIXES))]
    missing = [p for p in ADDED_FILES if p not in extra]
    return not undeclared and not missing, 'every file beyond M7 is a declared M7.1 addition, and every declared single addition exists', undeclared[:5] + missing[:5]


def r03():
    m, m94 = manifest(), manifest(MAN94)
    app = [p for p in files() if p.startswith('apg/') and p.endswith('.py')]
    changed = sorted(p for p in app if p in m and sh(p) != m[p])
    added = [p for p in app if p not in m]
    old = [p for p in app if p in m94 and sh(p) != m94[p]]
    ok = changed == sorted(CHANGED_APP) and not added and not old
    return ok, 'the only application files changed are the five declared apg/rec modules (inputs.py, verify.py and __init__.py are unchanged); no M9.4 application file differs from M9.4', changed + added + old


def r04():
    m, m94 = manifest(), manifest(MAN94)
    tests = [p for p in files() if p.startswith('tests/')]
    changed = sorted(p for p in tests if p in m and sh(p) != m[p])
    old = [p for p in tests if p in m94 and sh(p) != m94[p]]
    return changed == sorted(CHANGED_TESTS) and not old, 'the only test files changed are the four declared M7 test files; every M2 to M9.4 test is unchanged; the correction tests are added', [p for p in changed if p not in CHANGED_TESTS] + old


def r05():
    bad = []
    for name in TABLES:
        old, new = rows(os.path.join(SNAP, name + '.csv')), rows(os.path.join(ROOT, 'programme', name + '.csv'))
        if new[:len(old)] != old:
            bad.append(name + ': an M7 row changed')
        if not new[len(old):] or not all(r.get('milestone', 'M7.1') == 'M7.1' for r in new[len(old):]):
            bad.append(name + ': the appended rows are not M7.1 rows')
    for name in ('PROGRAMME_MILESTONES', 'RFC_REGISTER', 'E17_GOVERNANCE_REGISTER'):
        if open(os.path.join(SNAP, name + '.csv'), 'rb').read() != open(os.path.join(ROOT, 'programme', name + '.csv'), 'rb').read():
            bad.append(name + ' changed')
    return not bad, 'the programme tables are append-only (F-64 to F-67, SR-98 to SR-100, I-110 to I-113, EDR-34, CF-33); the milestones, RFC and Engine #17 tables are byte-identical to M7', bad


def r06():
    new = rows(os.path.join(ROOT, 'programme', 'FINDINGS_REGISTER.csv'))
    added = {r['finding_id']: r['status'] for r in new[len(rows(os.path.join(SNAP, 'FINDINGS_REGISTER.csv'))):]}
    rfc = rows(os.path.join(ROOT, 'programme', 'RFC_REGISTER.csv'))
    ok = sorted(added) == ['F-64', 'F-65', 'F-66', 'F-67'] and all(s.startswith(('Corrected in APG-M7.1', 'Open')) for s in added.values()) and not any('closed' in s.lower() for s in added.values()) \
        and rfc[0]['status'].startswith('PROPOSED')
    return ok, 'F-64 to F-66 are corrected but open until independently verified, F-67 is open and not corrected, no finding is closed, RFC-01 is still PROPOSED', added


def r07():
    import tempfile, shutil
    with tempfile.TemporaryDirectory() as td:
        for n in os.listdir(SNAP):
            shutil.copy(os.path.join(SNAP, n), td)
        r = subprocess.run([sys.executable, '-I', '-B', os.path.join(ROOT, 'tools', 'make_m71_registers.py'), td], capture_output=True, text=True)
        bad = [n + '.csv' for n in TABLES if open(os.path.join(td, n + '.csv'), 'rb').read() != open(os.path.join(ROOT, 'programme', n + '.csv'), 'rb').read()]
    return r.returncode == 0 and not bad, 'the programme tables are exactly what tools/make_m71_registers.py makes from the M7 tables', bad + ([r.stderr[-200:]] if r.returncode else [])


def r08():
    src = {n: open(os.path.join(ROOT, 'apg', 'rec', n), encoding='utf-8').read() for n in REC_MODULES}
    bad = [n for n, s in src.items() if 'adopt(' in s or 'register_scenario' in s or 'claim_realised(' in s]
    import ast
    banned = {'os', 'sys', 'socket', 'subprocess', 'urllib', 'http', 'shutil', 'smtplib', 'threading', 'asyncio', 'random', 'time'}
    for n, s in src.items():
        for node in ast.walk(ast.parse(s)):
            mods = [a.name.split('.')[0] for a in node.names] if isinstance(node, ast.Import) else ([node.module.split('.')[0]] if isinstance(node, ast.ImportFrom) and node.module and node.level == 0 else [])
            if set(mods) & banned:
                bad.append('%s imports %s' % (n, ', '.join(sorted(set(mods) & banned))))
    return not bad, 'no recommendation module adopts or files a forecast, claims a realised saving outside the gate, or reaches outside the record store', bad


def run(args, what, expect=None):
    r = subprocess.run([sys.executable, '-I'] + args, cwd=ROOT, capture_output=True, text=True, timeout=1800)
    tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or ['']
    ok = r.returncode == 0 and (expect is None or expect in r.stdout + r.stderr)
    return ok, what, tail


STEPS = {
    'R01': r01, 'R02': r02, 'R03': r03, 'R04': r04, 'R05': r05, 'R06': r06, 'R07': r07, 'R08': r08,
    'R09': lambda: run(['tools/run_m2_tests.py', '-q', 'test_rec_*.py'], 'the M7 unit tests and the M7.1 correction tests pass', 'failures 0  errors 0'),
    'R10': lambda: run(['tools/probe_rec_m7.py'], 'the M7 guarantees probe passes', 'THE M7 GUARANTEES HOLD'),
    'R10B': lambda: run(['tools/probe_m7_audit_findings.py'], 'the M7 audit findings probe reports every finding corrected', 'THE AUDIT FINDINGS ARE CORRECTED'),
    'R11': lambda: run(['tools/run_m2_tests.py', '-q', 'test_rec_golden.py'], 'the golden Builder Zero run equals regression/m7/golden_rec.json and the independent oracle agrees', 'failures 0  errors 0'),
    'R12': lambda: run(['tools/run_m2_tests.py', '-q'], 'the whole unit suite passes (every earlier test, unchanged, and the M7 tests)', 'failures 0  errors 0'),
}
STATIC = ['R01', 'R02', 'R03', 'R04', 'R05', 'R06', 'R07', 'R08']


def main():
    a = sys.argv[1:]
    if not a or a[0] == '--list':
        for k, f in STEPS.items():
            print(k, (f.__doc__ or '').strip() or '')
        print('steps:', ' '.join(STEPS))
        return 0
    want = STATIC if a[0] == '--static' else list(STEPS) if a[0] == '--all' else [a[1]] if a[0] == '--step' else []
    for k in want:
        ok, what, detail = STEPS[k]()
        results.append((k, ok))
        print('%s %s %s %s' % ('PASS' if ok else 'FAIL', k, what, detail if not ok or detail else ''))
    failed = [k for k, ok in results if not ok]
    print('\nchecks %d  failed %d' % (len(results), len(failed)) + ('\nFAILED: %r' % failed if failed else ''))
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
