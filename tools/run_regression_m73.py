#!/usr/bin/env python3
"""Regression checks of the APG-M7.3 correction against the delivered APG-M7.2 package (ZIP SHA-256 d2f900490f9a0d88c76c390aac3e7d2169f30ccf770ccb8f9dbc779f1d08a476), whose 889 file hashes are
stored in regression/m73/M7_2_MANIFEST.sha256 and whose programme tables are stored in regression/m73/m72_snapshot/; and, through regression/m7/M9_4_MANIFEST.sha256, against the delivered M9.4 package.
M7.3 changes three M2 files (the record-store port, the reference store and the scoped store): they are declared, and every other M9.4 application file must be unchanged.
Usage: python3 -I tools/run_regression_m73.py --list | --static | --step Rnn | --all
  --static   R01 to R08: files, tables and boundaries (seconds)
  --step     one step; R09 to R12 run tests and take longer (R12, the whole unit suite, takes about two minutes)
A step cut off by a time limit is incomplete, not a pass.  Exit 0 only if every step run passed."""
import csv, hashlib, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
MAN = os.path.join(ROOT, 'regression', 'm73', 'M7_2_MANIFEST.sha256')
MAN94 = os.path.join(ROOT, 'regression', 'm7', 'M9_4_MANIFEST.sha256')
SNAP = os.path.join(ROOT, 'regression', 'm73', 'm72_snapshot')
CHANGED_APP = {'apg/rec/engine.py', 'apg/rec/lifecycle.py', 'apg/ports.py', 'apg/reference_impl.py', 'apg/tenancy.py'}
M2_CHANGED = {'apg/ports.py', 'apg/reference_impl.py', 'apg/tenancy.py'}
ADDED_APP = {'apg/contracts/record_store_guard_contract.py'}
CHANGED_TESTS = {'tests/test_rec_m72_race.py'}
TABLES = ('FINDINGS_REGISTER', 'STATUS_REGISTER', 'INTERPRETATIONS_REGISTER', 'ENGINE_HANDOFF_REGISTER', 'CARRIED_FORWARD_REGISTER')
CHANGED = CHANGED_APP | CHANGED_TESTS | {'README.md', 'RUN_COMMANDS.txt', 'tools/m7_mutants.py', 'programme/RECOMMENDATION_ENGINE.md'} | {'programme/%s.csv' % t for t in TABLES}
ADDED_PREFIXES = ('regression/m73/', 'logs/m73/')
ADDED_FILES = {'tests/test_rec_m73_insert_race.py', 'tools/probe_m72_insert_race.py', 'tools/m73_store_mutants.py', 'tools/run_guard_contract.py', 'tools/make_m73_registers.py',
               'tools/run_regression_m73.py', 'tools/run_m73_all.py', 'tools/sabotage_m73.py', 'programme/CHANGE_RECORD_APG-M7.3.md'} | ADDED_APP
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


def rows(path):
    return list(csv.DictReader(open(path, encoding='utf-8', newline='')))


def manifest(path=MAN):
    return {line[66:].rstrip('\n'): line[:64] for line in open(path, encoding='utf-8')}


def r01():
    m = manifest()
    bad = [p for p, h in m.items() if p not in CHANGED and (not os.path.exists(os.path.join(ROOT, p)) or sh(p) != h)]
    missing = [p for p in CHANGED if p not in m]
    same = [p for p in CHANGED if p in m and os.path.exists(os.path.join(ROOT, p)) and sh(p) == m[p]]
    return not bad and not missing and not same and len(m) == 889, 'every one of the 889 M7.2 files except the %d declared changed ones is byte-identical here, and each declared one did change' % len(CHANGED), bad[:5] + missing + same


def r02():
    m = manifest()
    extra = [p for p in files() if p not in m]
    undeclared = [p for p in extra if not (p in ADDED_FILES or p.startswith(ADDED_PREFIXES))]
    missing = [p for p in ADDED_FILES if p not in extra]
    return not undeclared and not missing, 'every file beyond M7.2 is a declared M7.3 addition, and every declared single addition exists', undeclared[:5] + missing[:5]


def r03():
    m, m94 = manifest(), manifest(MAN94)
    app = [p for p in files() if p.startswith('apg/') and p.endswith('.py')]
    changed = sorted(p for p in app if p in m and sh(p) != m[p])
    added = sorted(p for p in app if p not in m)
    old = [p for p in app if p in m94 and sh(p) != m94[p] and p not in M2_CHANGED]
    ok = changed == sorted(CHANGED_APP) and added == sorted(ADDED_APP) and not old
    return ok, 'the only application files changed are the declared five (apg/rec/lifecycle.py and engine.py; apg/ports.py, reference_impl.py and tenancy.py); the only one added is the guard contract; no other M9.4 application file differs from M9.4', changed + added + old


def r04():
    m, m94 = manifest(), manifest(MAN94)
    tests = [p for p in files() if p.startswith('tests/')]
    changed = sorted(p for p in tests if p in m and sh(p) != m[p])
    old = [p for p in tests if p in m94 and sh(p) != m94[p]]
    return changed == sorted(CHANGED_TESTS) and not old, 'the only test file changed is tests/test_rec_m72_race.py (seven tests, declared); every other M2 to M9.4, M7, M7.1 and M7.2 test is unchanged; the M7.3 tests are added', [p for p in changed if p not in CHANGED_TESTS] + old


def r05():
    bad = []
    for name in TABLES:
        old, new = rows(os.path.join(SNAP, name + '.csv')), rows(os.path.join(ROOT, 'programme', name + '.csv'))
        if new[:len(old)] != old:
            bad.append(name + ': an M7.2 row changed')
        if not new[len(old):] or not all(r.get('milestone', 'M7.3') == 'M7.3' for r in new[len(old):]):
            bad.append(name + ': the appended rows are not M7.3 rows')
    for name in ('PROGRAMME_MILESTONES', 'RFC_REGISTER', 'E17_GOVERNANCE_REGISTER'):
        if open(os.path.join(SNAP, name + '.csv'), 'rb').read() != open(os.path.join(ROOT, 'programme', name + '.csv'), 'rb').read():
            bad.append(name + ' changed')
    return not bad, 'the programme tables are append-only (F-69, SR-103 and SR-104, I-116 and I-117, EDR-36, CF-35); the M7.2 rows, including F-64 to F-68, are unchanged; the milestones, RFC and Engine #17 tables are byte-identical to M7.2', bad


def r06():
    new = rows(os.path.join(ROOT, 'programme', 'FINDINGS_REGISTER.csv'))
    added = {r['finding_id']: r['status'] for r in new[len(rows(os.path.join(SNAP, 'FINDINGS_REGISTER.csv'))):]}
    rfc = rows(os.path.join(ROOT, 'programme', 'RFC_REGISTER.csv'))
    st = {r['finding_id']: r['status'] for r in new}
    ok = sorted(added) == ['F-69'] and added['F-69'].startswith('Corrected in APG-M7.3') and 'open until independently verified' in added['F-69'] \
        and all('open' in st[f].lower() and 'closed' not in st[f].lower() for f in ('F-64', 'F-65', 'F-66', 'F-67', 'F-68')) and rfc[0]['status'].startswith('PROPOSED')
    return ok, 'F-69 is corrected but open until independently verified; F-64 to F-68 are still open; no finding is closed; RFC-01 is still PROPOSED', added


def r07():
    import tempfile, shutil
    with tempfile.TemporaryDirectory() as td:
        for n in os.listdir(SNAP):
            shutil.copy(os.path.join(SNAP, n), td)
        r = subprocess.run([sys.executable, '-I', '-B', os.path.join(ROOT, 'tools', 'make_m73_registers.py'), td], capture_output=True, text=True)
        bad = [n + '.csv' for n in TABLES if open(os.path.join(td, n + '.csv'), 'rb').read() != open(os.path.join(ROOT, 'programme', n + '.csv'), 'rb').read()]
    return r.returncode == 0 and not bad, 'the programme tables are exactly what tools/make_m73_registers.py makes from the M7.2 tables', bad + ([r.stderr[-200:]] if r.returncode else [])


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
    'R09': lambda: run(['tools/run_m2_tests.py', '-q', 'test_rec_*.py'], 'the M7 unit tests and the M7.1, M7.2 and M7.3 correction tests pass', 'failures 0  errors 0'),
    'R10': lambda: run(['tools/probe_rec_m7.py'], 'the M7 guarantees probe passes', 'THE M7 GUARANTEES HOLD'),
    'R10B': lambda: run(['tools/probe_m7_audit_findings.py'], 'the M7 audit findings probe reports every finding corrected', 'THE AUDIT FINDINGS ARE CORRECTED'),
    'R10C': lambda: run(['tools/probe_m71_race.py'], 'the M7.1 audit race probe reports the race closed at every boundary', 'THE RACE IS CLOSED'),
    'R10D': lambda: run(['tools/probe_m72_insert_race.py'], 'the M7.2 audit insert-race probe reports no act committed on changed sources', 'THE INSERT RACE IS CLOSED'),
    'R11': lambda: run(['tools/run_m2_tests.py', '-q', 'test_rec_golden.py'], 'the golden Builder Zero run equals regression/m7/golden_rec.json and the independent oracle agrees', 'failures 0  errors 0'),
    'R12': lambda: run(['tools/run_m2_tests.py', '-q'], 'the whole unit suite passes', 'failures 0  errors 0'),
    'R13': lambda: run(['tools/run_contracts.py'], 'the M2 port contracts still pass on the changed reference store (38 cases)', 'ALL CONTRACT CASES PASS'),
    'R13B': lambda: run(['tools/run_faults.py'], 'every M2 faulty implementation is still caught (39)', 'ALL FAULTS CAUGHT'),
    'R14': lambda: run(['tools/run_guard_contract.py'], 'the reference store passes the guard contract (RG-01 to RG-08)', 'ALL GUARD CASES PASS'),
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
