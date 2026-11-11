#!/usr/bin/env python3
"""Regression checks of APG-M7 against the delivered APG-M9.4 package (ZIP SHA-256 31c05bf715b0df3e37424347fddd80a795eaaf30bc2940704688eabbcf9b44d3), whose 795 file hashes are stored in
regression/m7/M9_4_MANIFEST.sha256, and whose programme tables are stored in regression/m7/m94_snapshot/.
Usage: python3 -I tools/run_regression_m7.py --list | --static | --step Rnn | --all
  --static   R01 to R08: files, tables and boundaries (seconds)
  --step     one step; R09 to R12 run tests and take longer (R12, the whole unit suite, takes about two minutes)
A step cut off by a time limit is incomplete, not a pass.  Exit 0 only if every step run passed."""
import csv, hashlib, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
MAN = os.path.join(ROOT, 'regression', 'm7', 'M9_4_MANIFEST.sha256')
SNAP = os.path.join(ROOT, 'regression', 'm7', 'm94_snapshot')
CHANGED = {'README.md', 'RUN_COMMANDS.txt', 'programme/STATUS_REGISTER.csv', 'programme/INTERPRETATIONS_REGISTER.csv', 'programme/ENGINE_HANDOFF_REGISTER.csv',
           'programme/CARRIED_FORWARD_REGISTER.csv', 'programme/PROGRAMME_MILESTONES.csv'}
ADDED_PREFIXES = ('apg/rec/', 'tests/test_rec_', 'regression/m7/', 'logs/m7/')
ADDED_FILES = {'tests/helpers_rec.py', 'tools/m7_mutants.py', 'tools/make_m7_registers.py', 'tools/probe_rec_m7.py', 'tools/run_regression_m7.py', 'tools/run_m7_all.py', 'tools/sabotage_m7.py',
               'programme/CHANGE_RECORD_APG-M7.md', 'programme/RECOMMENDATION_ENGINE.md'}
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


def r01():
    m = manifest()
    bad = [p for p, h in m.items() if p not in CHANGED and (not os.path.exists(os.path.join(ROOT, p)) or sh(p) != h)]
    return not bad and len(m) == 795, 'every one of the 795 M9.4 files except the 7 declared changed ones is byte-identical here', bad[:5]


def r02():
    m = manifest()
    extra = [p for p in files() if p not in m]
    undeclared = [p for p in extra if not (p in ADDED_FILES or p.startswith(ADDED_PREFIXES))]
    missing = [p for p in ADDED_FILES if p not in extra]
    return not undeclared and not missing, 'every file beyond M9.4 is a declared M7 addition, and every declared single addition exists', undeclared[:5] + missing[:5]


def r03():
    m = manifest()
    app = [p for p in files() if p.startswith('apg/') and p.endswith('.py')]
    changed = [p for p in app if p in m and sh(p) != m[p]]
    added = sorted(p for p in app if p not in m)
    ok = not changed and added == sorted('apg/rec/' + n for n in REC_MODULES)
    return ok, 'no application file of M9.4 changed; the only application files added are the eight modules of apg/rec', changed + [p for p in added if not p.startswith('apg/rec/')]


def r04():
    m = manifest()
    tests = [p for p in files() if p.startswith('tests/')]
    changed = [p for p in tests if p in m and sh(p) != m[p]]
    return not changed, 'no existing test file changed (every M2 to M9.4 test is untouched); the M7 tests are added', changed


def r05():
    bad = []
    for name in ('STATUS_REGISTER', 'INTERPRETATIONS_REGISTER', 'ENGINE_HANDOFF_REGISTER', 'CARRIED_FORWARD_REGISTER'):
        old, new = rows(os.path.join(SNAP, name + '.csv')), rows(os.path.join(ROOT, 'programme', name + '.csv'))
        if new[:len(old)] != old:
            bad.append(name + ': an M9.4 row changed')
        if not all(r.get('milestone', 'M7') == 'M7' for r in new[len(old):]):
            bad.append(name + ': an appended row is not an M7 row')
    old, new = rows(os.path.join(SNAP, 'PROGRAMME_MILESTONES.csv')), rows(os.path.join(ROOT, 'programme', 'PROGRAMME_MILESTONES.csv'))
    diff = [(a['milestone_id'], k) for a, b in zip(old, new) for k in a if a[k] != b[k]]
    if len(old) != len(new) or sorted(diff) != [('M7', 'handoff_register_entries'), ('M7', 'status')]:
        bad.append('PROGRAMME_MILESTONES: changes other than the M7 status and handoff entry: %r' % diff)
    return not bad, 'the programme tables are append-only (rows SR-90 to SR-97, I-99 to I-109, EDR-33, CF-32) and only the M7 milestone status and handoff entry changed', bad


def r06():
    bad = [n for n in ('FINDINGS_REGISTER', 'RFC_REGISTER', 'E17_GOVERNANCE_REGISTER') if open(os.path.join(SNAP, n + '.csv'), 'rb').read() != open(os.path.join(ROOT, 'programme', n + '.csv'), 'rb').read()]
    rfc = rows(os.path.join(ROOT, 'programme', 'RFC_REGISTER.csv'))
    ok = not bad and rfc[0]['status'].startswith('PROPOSED')
    return ok, 'the findings, RFC and Engine #17 governance tables are byte-identical to M9.4 (RFC-01 still PROPOSED and unnumbered; no finding is closed)', bad


def r07():
    import tempfile, shutil
    with tempfile.TemporaryDirectory() as td:
        for n in os.listdir(SNAP):
            shutil.copy(os.path.join(SNAP, n), td)
        r = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', 'make_m7_registers.py'), td], capture_output=True, text=True)
        bad = [n for n in ('STATUS_REGISTER.csv', 'INTERPRETATIONS_REGISTER.csv', 'ENGINE_HANDOFF_REGISTER.csv', 'CARRIED_FORWARD_REGISTER.csv', 'PROGRAMME_MILESTONES.csv')
               if open(os.path.join(td, n), 'rb').read() != open(os.path.join(ROOT, 'programme', n), 'rb').read()]
    return r.returncode == 0 and not bad, 'the programme tables are exactly what tools/make_m7_registers.py makes from the M9.4 tables', bad


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
    'R09': lambda: run(['tools/run_m2_tests.py', '-q', 'test_rec_*.py'], 'the M7 unit tests pass', 'failures 0  errors 0'),
    'R10': lambda: run(['tools/probe_rec_m7.py'], 'the M7 guarantees probe passes', 'THE M7 GUARANTEES HOLD'),
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
