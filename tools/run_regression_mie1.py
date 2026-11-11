#!/usr/bin/env python3
"""Regression checks of the MIE-1 build against the delivered APG-M7.3 package (ZIP SHA-256 f14b6818000cb1ac76482d5d2b5246f82030aa84216eb44dc6b0ee1fac7f6307, 918 files), whose file hashes are stored in
regression/mie1/M7_3_MANIFEST.sha256 and whose programme tables are stored in regression/mie1/m73_snapshot/.  MIE-1 adds the market-intelligence core and its tests and tools; it
changes no APG application file and no existing test.  The only changed files are README.md, RUN_COMMANDS.txt and four programme tables (append-only).
Usage: python3 -I tools/run_regression_mie1.py --list | --static | --step Rnn | --all
  --static   R01 to R08 and R13: files, tables, boundaries, text (seconds)
  --step     one step; R09 to R12 run tests (R12, the whole unit suite, takes several minutes)
A step cut off by a time limit is incomplete, not a pass.  Exit 0 only if every step run passed."""
import csv, hashlib, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
MAN = os.path.join(ROOT, 'regression', 'mie1', 'M7_3_MANIFEST.sha256')
SNAP = os.path.join(ROOT, 'regression', 'mie1', 'm73_snapshot')
TABLES = ('STATUS_REGISTER', 'INTERPRETATIONS_REGISTER', 'ENGINE_HANDOFF_REGISTER', 'CARRIED_FORWARD_REGISTER')
UNCHANGED_TABLES = ('FINDINGS_REGISTER', 'PROGRAMME_MILESTONES', 'RFC_REGISTER', 'E17_GOVERNANCE_REGISTER')
CHANGED = {'README.md', 'RUN_COMMANDS.txt'} | {'programme/%s.csv' % t for t in TABLES}
ADDED_PREFIXES = ('mie/', 'spec/MIE1_SPEC_v0.3/', 'regression/mie1/', 'logs/mie1/')
ADDED_FILES = {'tests/helpers_mie.py', 'tests/helpers_mie_construction.py', 'tests/test_mie_construction.py', 'tests/test_mie_core_adversarial.py', 'tests/test_mie_core_audit.py', 'tests/test_mie_core_boundaries.py', 'tests/test_mie_core_canon.py',
               'tests/test_mie_core_observations.py', 'tests/test_mie_core_pack.py', 'tests/test_mie_core_ports.py', 'tests/test_mie_core_replay.py',
               'tests/test_mie_core_signals.py', 'tests/test_mie_core_static.py', 'tests/test_mie_core_tenancy.py', 'tests/test_mie_core_timing.py', 'tests/test_mie_flow.py',
               'tests/test_mie_portability.py', 'tools/make_mie1_registers.py', 'tools/mie_coverage.py', 'tools/mie_mutants.py', 'tools/mie_static.py', 'tools/run_golden_mie1.py',
               'tools/run_regression_mie1.py', 'tools/run_mie1_all.py', 'tools/sabotage_mie1.py', 'programme/CHANGE_RECORD_APG-MIE1.md', 'programme/MIE1_CASE_COVERAGE.csv'}
NEW_IDS = {'STATUS_REGISTER': ['SR-105', 'SR-106', 'SR-107', 'SR-108'], 'INTERPRETATIONS_REGISTER': ['I-118', 'I-119', 'I-120', 'I-121', 'I-122', 'I-123', 'I-124'],
           'ENGINE_HANDOFF_REGISTER': ['EDR-37'], 'CARRIED_FORWARD_REGISTER': ['CF-36', 'CF-37']}
RELEASE_TEXT = ['README.md', 'programme/CHANGE_RECORD_APG-MIE1.md', 'mie/packs/construction.py', 'mie/packs/synthetic.py']
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
    return not bad and not same and len(m) == 918, 'every one of the 918 M7.3 files except the %d declared changed ones is byte-identical here, and each declared one did change' % len(CHANGED), bad[:5] + same


def r02():
    m = manifest()
    extra = [p for p in files() if p not in m]
    undeclared = [p for p in extra if not (p in ADDED_FILES or p.startswith(ADDED_PREFIXES))]
    missing = [p for p in ADDED_FILES if p not in extra]
    return not undeclared and not missing, 'every file beyond M7.3 is a declared MIE-1 addition, and every declared single addition exists', undeclared[:5] + missing[:5]


def r03():
    m = manifest()
    app = [p for p in files() if p.startswith('apg/')]
    changed = [p for p in app if p not in m or sh(p) != m[p]]
    tests = [p for p in files() if p.startswith('tests/') and p in m and sh(p) != m[p]]
    return not changed and not tests, 'IG-04: no APG application file is changed or added, and no existing test is changed (the MIE-1 tests are additions)', changed[:5] + tests[:5]


def r04():
    bad = []
    for name in TABLES:
        old, new = rows(os.path.join(SNAP, name + '.csv')), rows(os.path.join(ROOT, 'programme', name + '.csv'))
        if new[:len(old)] != old:
            bad.append(name + ': an M7.3 row changed')
        ids = [list(r.values())[0] for r in new[len(old):]]
        if ids != NEW_IDS[name] or not all(r.get('milestone', 'MIE-1') == 'MIE-1' for r in new[len(old):]):
            bad.append(name + ': the appended rows are not exactly the MIE-1 rows')
    for name in UNCHANGED_TABLES:
        if open(os.path.join(SNAP, name + '.csv'), 'rb').read() != open(os.path.join(ROOT, 'programme', name + '.csv'), 'rb').read():
            bad.append(name + ' changed')
    return not bad, 'the programme tables are append-only (SR-105 to SR-108, I-118 to I-124, EDR-37, CF-36, CF-37); the M7.3 rows are unchanged; findings, milestones, RFC and Engine #17 tables are byte-identical', bad


def r05():
    st = {r['finding_id']: r['status'] for r in rows(os.path.join(ROOT, 'programme', 'FINDINGS_REGISTER.csv'))}
    cf = {r['cf_id']: r for r in rows(os.path.join(ROOT, 'programme', 'CARRIED_FORWARD_REGISTER.csv'))}
    interp = {r['interpretation_id']: r for r in rows(os.path.join(ROOT, 'programme', 'INTERPRETATIONS_REGISTER.csv'))}
    edr = {r['edr_id']: r for r in rows(os.path.join(ROOT, 'programme', 'ENGINE_HANDOFF_REGISTER.csv'))}
    bad = []
    if not st['F-69'].startswith('Corrected in APG-M7.3') or 'open until independently verified' not in st['F-69']:
        bad.append('F-69 is no longer open until independently verified')
    for k in ('CF-36', 'CF-37'):
        if not cf[k]['status'].startswith('Open'):
            bad.append(k + ' is not open')
    gates = cf['CF-36']['what_remains_open']
    for g in ('final release acceptance is pending', 'EDR-36', 'M9.4', 'not been independently audited'):
        if g not in gates:
            bad.append('CF-36 no longer records: ' + g)
    blk = cf['CF-37']['what_remains_open']
    for b in ('BLK-01', 'BLK-02', 'BLK-03'):
        if b not in blk:
            bad.append('CF-37 no longer lists ' + b)
    if re.search(r'\b(resolved|decided|closed|accepted|approved)\b', blk + ' ' + cf['CF-37']['status'] + ' ' + gates + ' ' + cf['CF-36']['status'], re.I):
        bad.append('CF-36 or CF-37 records a gate or a blocker as resolved, decided, closed, accepted or approved')
    for i in ('I-118', 'I-119', 'I-120', 'I-121', 'I-122', 'I-123', 'I-124'):
        if interp[i]['status'] != 'Retained for review - not approved':
            bad.append(i + ' is not retained for review')
    for e in ('EDR-36', 'EDR-37'):
        if not edr[e]['status'].startswith('Open'):
            bad.append(e + ' is not open')
    return not bad, 'no finding is closed; the M7.3 release gates (CF-36) and the blockers BLK-01 to BLK-03 (CF-37) are recorded open; EDR-36 and EDR-37 are open; every MIE-1 interpretation is retained for review', bad


def r06():
    import tempfile, shutil
    with tempfile.TemporaryDirectory() as td:
        for n in os.listdir(SNAP):
            shutil.copy(os.path.join(SNAP, n), td)
        r = subprocess.run([sys.executable, '-I', '-B', os.path.join(ROOT, 'tools', 'make_mie1_registers.py'), td], capture_output=True, text=True)
        bad = [n + '.csv' for n in TABLES if open(os.path.join(td, n + '.csv'), 'rb').read() != open(os.path.join(ROOT, 'programme', n + '.csv'), 'rb').read()]
    return r.returncode == 0 and not bad, 'the programme tables are exactly what tools/make_mie1_registers.py makes from the M7.3 tables', bad + ([r.stderr[-200:]] if r.returncode else [])


def r08():
    bad = []
    for p in RELEASE_TEXT:
        text = open(os.path.join(ROOT, p), encoding='utf-8').read()
        if p == 'README.md':
            text = text.split('---- the M7.3 readme follows')[0] if text.startswith('# APG MIE-1') else ''
            if not text:
                bad.append('README.md does not start with the MIE-1 section')
        for m in CLAIMS.finditer(text):
            bad.append('%s: %r' % (p, text[max(0, m.start() - 40):m.end() + 20]))
    return not bad, 'QA-04: the MIE-1 release text makes no readiness, acceptance, predictive or coverage claim', bad[:5]


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
    'R12': lambda: run([T, '-q'], 'IG-03: the whole unit suite passes (every M2 to M7.3 test unchanged, plus the MIE-1 tests)', 'failures 0  errors 0'),
    'R13': lambda: run(['tools/mie_coverage.py'], 'QA-02: every one of the 175 planned cases is accounted for, and programme/MIE1_CASE_COVERAGE.csv is what the tool makes', 'EVERY PLANNED CASE IS ACCOUNTED FOR'),
}
STATIC = ['R01', 'R02', 'R03', 'R04', 'R05', 'R06', 'R07', 'R08', 'R13']


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
