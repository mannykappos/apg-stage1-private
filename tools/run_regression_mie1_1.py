#!/usr/bin/env python3
"""Regression checks of the MIE-1.1 correction release against the delivered APG-MIE-1 package (ZIP SHA-256 26fe3517d0d4f64981bad3cc2f28e1d748e0c25062f98c22209359435dd4206d,
1007 files), whose file hashes are stored in regression/mie1_1/MIE1_MANIFEST.sha256 and whose programme tables are stored in regression/mie1_1/mie1_snapshot/.  MIE-1.1 changes
five core files and one MIE-1 test, the readme, the run commands, five programme tables (append-only) and the case-coverage map; it changes no APG application file and no
M2 to M7.3 test.  The M7.3 manifest of MIE-1 still holds for every APG file (R03).
Usage: python3 -I tools/run_regression_mie1_1.py --list | --static | --step Rnn | --all
  --static   R01 to R08, R13 and R14: files, tables, boundaries, text, coverage, the audit-findings probe (seconds)
  --step     one step; R09 to R12 run tests (R12, the whole unit suite, takes several minutes)
A step cut off by a time limit is incomplete, not a pass.  Exit 0 only if every step run passed."""
import csv, hashlib, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
MAN = os.path.join(ROOT, 'regression', 'mie1_1', 'MIE1_MANIFEST.sha256')
MAN73 = os.path.join(ROOT, 'regression', 'mie1', 'M7_3_MANIFEST.sha256')
SNAP = os.path.join(ROOT, 'regression', 'mie1_1', 'mie1_snapshot')
TABLES = ('FINDINGS_REGISTER', 'STATUS_REGISTER', 'INTERPRETATIONS_REGISTER', 'ENGINE_HANDOFF_REGISTER', 'CARRIED_FORWARD_REGISTER')
UNCHANGED_TABLES = ('PROGRAMME_MILESTONES', 'RFC_REGISTER', 'E17_GOVERNANCE_REGISTER')
CORE_CHANGED = {'mie/core/engine.py', 'mie/core/observations.py', 'mie/core/signals.py', 'mie/core/ports.py', 'mie/core/reference.py'}
TESTS_CHANGED = {'tests/test_mie_core_audit.py'}
CHANGED = CORE_CHANGED | TESTS_CHANGED | {'README.md', 'RUN_COMMANDS.txt', 'programme/MIE1_CASE_COVERAGE.csv'} | {'programme/%s.csv' % t for t in TABLES}
ADDED_PREFIXES = ('regression/mie1_1/', 'logs/mie1_1/')
ADDED_FILES = {'tests/test_mie_core_m11_corrections.py', 'tools/probe_mie1_audit_findings.py', 'tools/mie11_mutants.py', 'tools/sabotage_mie1_1.py', 'tools/run_regression_mie1_1.py',
               'tools/run_mie1_1_all.py', 'tools/make_mie1_1_registers.py', 'programme/CHANGE_RECORD_APG-MIE1.1.md'}
NEW_IDS = {'FINDINGS_REGISTER': ['F-70', 'F-71'], 'STATUS_REGISTER': ['SR-109', 'SR-110'], 'INTERPRETATIONS_REGISTER': ['I-125', 'I-126'],
           'ENGINE_HANDOFF_REGISTER': ['EDR-38'], 'CARRIED_FORWARD_REGISTER': ['CF-38', 'CF-39']}
RELEASE_TEXT = ['README.md', 'programme/CHANGE_RECORD_APG-MIE1.1.md']
CLAIMS = re.compile(r'production[- ]ready|ready for (production|release|use)|release[- ]ready|\bcertified\b|\bguarantee[sd]?\b|will (rise|fall|increase|decrease|go up|go down)|'
                    r'\bpredicts?\b|\bpredicted (price|level|value)|100 ?%|fully (tested|verified|covered)|(?<!not )independently (verified|reviewed|audited)\b(?! yet)|'
                    r'\b(MIE-1|this release|this package|the build|the core|the pack) (is|was|has been|have been) (accepted|approved|signed off|verified)\b', re.I)
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


def manifest():
    return {line[66:].rstrip('\n'): line[:64] for line in open(MAN, encoding='utf-8')}


def r01():
    m = manifest()
    bad = [p for p, h in m.items() if p not in CHANGED and (not os.path.exists(os.path.join(ROOT, p)) or sh(p) != h)]
    same = [p for p in CHANGED if p in m and sh(p) == m[p]]
    return not bad and not same and len(m) == 1007, 'every one of the 1007 MIE-1 files except the %d declared changed ones is byte-identical here, and each declared one did change' % len(CHANGED), bad[:5] + same


def r02():
    m = manifest()
    extra = [p for p in files() if p not in m]
    undeclared = [p for p in extra if not (p in ADDED_FILES or p.startswith(ADDED_PREFIXES))]
    missing = [p for p in ADDED_FILES if p not in extra]
    return not undeclared and not missing, 'every file beyond MIE-1 is a declared MIE-1.1 addition, and every declared single addition exists', undeclared[:5] + missing[:5]


def r03():
    m, m73 = manifest(), {line[66:].rstrip('\n'): line[:64] for line in open(MAN73, encoding='utf-8')}
    app = [p for p in files() if p.startswith('apg/')]
    changed = [p for p in app if p not in m or sh(p) != m[p] or p not in m73 or sh(p) != m73[p]]
    tests = [p for p in files() if p.startswith('tests/') and p in m and sh(p) != m[p] and p not in TESTS_CHANGED]
    core = sorted(p for p in files() if p.startswith('mie/') and p in m and sh(p) != m[p])
    old_tests = [p for p in files() if p.startswith('tests/') and p in m73 and sh(p) != m73[p]]
    return not changed and not tests and not old_tests and core == sorted(CORE_CHANGED), ('IG-04: no APG application file differs from MIE-1 or M7.3; no M2 to M7.3 test changed; '
            'the only MIE files changed are the five declared core files and tests/test_mie_core_audit.py'), changed[:5] + tests[:5] + old_tests[:5] + [c for c in core if c not in CORE_CHANGED]


def r04():
    bad = []
    for name in TABLES:
        old, new = rows(os.path.join(SNAP, name + '.csv')), rows(os.path.join(ROOT, 'programme', name + '.csv'))
        if new[:len(old)] != old:
            bad.append(name + ': an MIE-1 row changed')
        ids = [list(r.values())[0] for r in new[len(old):]]
        if ids != NEW_IDS[name] or not all(r.get('milestone', 'MIE-1.1') == 'MIE-1.1' for r in new[len(old):]):
            bad.append(name + ': the appended rows are not exactly the MIE-1.1 rows')
    for name in UNCHANGED_TABLES:
        if open(os.path.join(SNAP, name + '.csv'), 'rb').read() != open(os.path.join(ROOT, 'programme', name + '.csv'), 'rb').read():
            bad.append(name + ' changed')
    return not bad, 'the programme tables are append-only (F-70, F-71, SR-109, SR-110, I-125, I-126, EDR-38, CF-38, CF-39); the MIE-1 rows are unchanged; milestones, RFC and Engine #17 tables are byte-identical', bad


def r05():
    st = {r['finding_id']: r['status'] for r in rows(os.path.join(ROOT, 'programme', 'FINDINGS_REGISTER.csv'))}
    cf = {r['cf_id']: r for r in rows(os.path.join(ROOT, 'programme', 'CARRIED_FORWARD_REGISTER.csv'))}
    interp = {r['interpretation_id']: r for r in rows(os.path.join(ROOT, 'programme', 'INTERPRETATIONS_REGISTER.csv'))}
    edr = {r['edr_id']: r for r in rows(os.path.join(ROOT, 'programme', 'ENGINE_HANDOFF_REGISTER.csv'))}
    bad = []
    for f in ('F-69', 'F-70', 'F-71'):
        if 'open until independently verified' not in st[f]:
            bad.append(f + ' is no longer open until independently verified')
    for k in ('CF-36', 'CF-37', 'CF-38', 'CF-39'):
        if not cf[k]['status'].startswith('Open'):
            bad.append(k + ' is not open')
        if re.search(r'\b(resolved|decided|closed|accepted|approved)\b', cf[k]['what_remains_open'] + ' ' + cf[k]['status'], re.I):
            bad.append(k + ' records a gate, a blocker or the deviation as resolved, decided, closed, accepted or approved')
    for g in ('final release acceptance is pending', 'EDR-36', 'M9.4', 'not been independently audited'):
        if g not in cf['CF-36']['what_remains_open']:
            bad.append('CF-36 no longer records: ' + g)
    for b in ('BLK-01', 'BLK-02', 'BLK-03'):
        if b not in cf['CF-37']['what_remains_open']:
            bad.append('CF-37 no longer lists ' + b)
    if 'deviation' not in cf['CF-38']['what_remains_open'] or 'BLK-01 to BLK-03 are still open' not in cf['CF-38']['what_remains_open']:
        bad.append('CF-38 no longer records the development deviation with the blockers open')
    for i in ('I-118', 'I-119', 'I-120', 'I-121', 'I-122', 'I-123', 'I-124', 'I-125', 'I-126'):
        if interp[i]['status'] != 'Retained for review - not approved':
            bad.append(i + ' is not retained for review')
    for e in ('EDR-36', 'EDR-37', 'EDR-38'):
        if not edr[e]['status'].startswith('Open'):
            bad.append(e + ' is not open')
    return not bad, ('F-69 to F-71 stay open until independently verified; the release gates (CF-36), the blockers BLK-01 to BLK-03 (CF-37), the development deviation (CF-38) and '
                     'the incomplete audit runs (CF-39) are recorded open; EDR-36 to EDR-38 are open; every MIE interpretation is retained for review'), bad


def r06():
    import tempfile, shutil
    with tempfile.TemporaryDirectory() as td:
        for n in os.listdir(SNAP):
            shutil.copy(os.path.join(SNAP, n), td)
        r = subprocess.run([sys.executable, '-I', '-B', os.path.join(ROOT, 'tools', 'make_mie1_1_registers.py'), td], capture_output=True, text=True)
        bad = [n + '.csv' for n in TABLES if open(os.path.join(td, n + '.csv'), 'rb').read() != open(os.path.join(ROOT, 'programme', n + '.csv'), 'rb').read()]
    return r.returncode == 0 and not bad, 'the programme tables are exactly what tools/make_mie1_1_registers.py makes from the MIE-1 tables', bad + ([r.stderr[-200:]] if r.returncode else [])


def r08():
    bad = []
    for p in RELEASE_TEXT:
        text = open(os.path.join(ROOT, p), encoding='utf-8').read()
        if p == 'README.md':
            text = text.split('---- the MIE-1 readme follows')[0] if text.startswith('# APG MIE-1.1') else ''
            if not text:
                bad.append('README.md does not start with the MIE-1.1 section')
        if 'DEV-MIE-01' not in text:
            bad.append(p + ' does not state the development deviation DEV-MIE-01')
        for m in CLAIMS.finditer(text):
            bad.append('%s: %r' % (p, text[max(0, m.start() - 40):m.end() + 20]))
    return not bad, 'QA-04: the MIE-1.1 release text makes no readiness, acceptance, predictive or coverage claim, and states the development deviation (DEV-MIE-01)', bad[:5]


def run(args, what, expect=None):
    r = subprocess.run([sys.executable, '-I'] + args, cwd=ROOT, capture_output=True, text=True, timeout=3600)
    tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or ['']
    ok = r.returncode == 0 and (expect is None or expect in r.stdout + r.stderr)
    return ok, what, tail


T = 'tools/run_m2_tests.py'
STEPS = {
    'R01': r01, 'R02': r02, 'R03': r03, 'R04': r04, 'R05': r05, 'R06': r06,
    'R07': lambda: run(['tools/mie_static.py'], 'NE-01 to NE-06, FL-01, IG-01, IG-05: the static checks of the core and the isolation gate pass', 'static checks 8  failed 0'),
    'R08': r08,
    'R09': lambda: run([T, '-q', 'test_mie_core_*.py'], 'the MIE core tests pass (synthetic pack only)', 'failures 0  errors 0'),
    'R09B': lambda: run([T, '-q', 'test_mie_[fp]*.py'], 'the feed-flow and portability tests pass', 'failures 0  errors 0'),
    'R10': lambda: run([T, '-q', 'test_mie_construction.py'], 'the construction pack, M6 mapping, M6 feed and isolation tests pass on Builder Zero', 'failures 0  errors 0'),
    'R11': lambda: run(['tools/run_golden_mie1.py'], 'the golden Builder Zero MIE-1 run equals regression/mie1/golden_mie1.json', 'THE GOLDEN MIE-1 RUN EQUALS THE RECORDED ANSWER'),
    'R12': lambda: run([T, '-q'], 'IG-03: the whole unit suite passes (every M2 to M7.3 test unchanged, plus the MIE-1 and MIE-1.1 tests)', 'failures 0  errors 0'),
    'R14': lambda: run(['tools/probe_mie1_audit_findings.py'], 'the MIE-1 audit findings probe reports every case corrected', 'THE MIE-1 AUDIT FINDINGS ARE CORRECTED'),
    'R15': lambda: run([T, '-q', 'test_mie_core_m11_corrections.py'], 'the MIE-1.1 correction tests pass', 'failures 0  errors 0'),
    'R13': lambda: run(['tools/mie_coverage.py'], 'QA-02: every one of the 175 planned cases is accounted for, and programme/MIE1_CASE_COVERAGE.csv is what the tool makes', 'EVERY PLANNED CASE IS ACCOUNTED FOR'),
}
STATIC = ['R01', 'R02', 'R03', 'R04', 'R05', 'R06', 'R07', 'R08', 'R13', 'R14']


def main():
    a = sys.argv[1:]
    if not a or a[0] == '--list':
        for k in STEPS:
            print(k)
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
