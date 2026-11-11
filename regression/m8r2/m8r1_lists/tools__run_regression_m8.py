#!/usr/bin/env python3
"""Regression checks of APG-M8 against the delivered APG-F67.4-R2 package (ZIP SHA-256 3e474b4671c846e7581ccb6d1ca27a6fe339f03a2275bf9ad7f753b0097a516e, 1,222 files; every file
hash in regression/m8/R2_MANIFEST.sha256, the R2 registers in regression/m8/r2_registers/).  Every step is short.
M8-R1 adds R10: against the delivered APG-M8 ZIP (SHA-256 f1b634d36f2ac57eefed6910cdc86273b30b5bdcc13d8be778d1b2f21a81157c, 1,307 files; every file hash in
regression/m8r1/M8_MANIFEST.sha256), only the declared M8-R1 files differ.
Usage: python3 -I tools/run_regression_m8.py --list | --all | --step Rnn      Exit 0 only if every step run passed."""
import csv, hashlib, os, re, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
G = os.path.join(ROOT, 'regression', 'm8')
REGS = ('FINDINGS_REGISTER.csv', 'STATUS_REGISTER.csv', 'INTERPRETATIONS_REGISTER.csv', 'CARRIED_FORWARD_REGISTER.csv')       # the Engine handoff register is NOT changed
CHANGED = {'README.md', 'RUN_COMMANDS.txt'} | {'programme/' + r for r in REGS}
ADDED_PREFIXES = ('apg_auif/', 'tests_m8/', 'auif_m8/', 'third_party/auif_rev13/', 'regression/m8/', 'logs/m8/', 'regression/m8r1/', 'logs/m8r1/')
ADDED_FILES = {'tools/make_m8_config.py', 'tools/run_m8_tests.py', 'tools/run_m8_all.py', 'tools/m8_mutants.py', 'tools/sabotage_m8.py', 'tools/run_regression_m8.py',
               'tools/make_m8_registers.py', 'programme/CHANGE_RECORD_APG-M8.md', 'tools/make_m8r1_registers.py', 'programme/CHANGE_RECORD_APG-M8R1.md'}
NEW = {'FINDINGS_REGISTER.csv': ['F-76', 'F-77', 'F-78', 'F-79', 'F-80', 'F-81', 'F-82'], 'STATUS_REGISTER.csv': ['SR-121', 'SR-122', 'SR-123', 'SR-124', 'SR-125', 'SR-126'],
       'INTERPRETATIONS_REGISTER.csv': ['I-135', 'I-136', 'I-137', 'I-138', 'I-139', 'I-140', 'I-141'],
       'CARRIED_FORWARD_REGISTER.csv': ['CF-46', 'CF-47', 'CF-48', 'CF-49', 'CF-50', 'CF-51', 'CF-52', 'CF-53']}           # M8-R1 appends F-82, SR-126, I-141, CF-51 to CF-53
M8_ZIP_SHA256 = 'f1b634d36f2ac57eefed6910cdc86273b30b5bdcc13d8be778d1b2f21a81157c'
R1_CHANGED = {'README.md', 'RUN_COMMANDS.txt', 'apg_auif/intake.py', 'apg_auif/gate.py', 'auif_m8/PATH_EQUIVALENCE_DECLARED_DIFFERENCES.json', 'tests_m8/test_m8_corpus.py',
              'tests_m8/test_m8_path_equivalence.py', 'tests_m8/test_m8_boundary.py', 'tools/run_m8_tests.py', 'tools/run_m8_all.py', 'tools/m8_mutants.py', 'tools/sabotage_m8.py', 'tools/run_regression_m8.py'} | {'programme/' + r for r in REGS}
R1_ADDED = {'tests_m8/test_m8r1_empty_source.py', 'tools/make_m8r1_registers.py', 'programme/CHANGE_RECORD_APG-M8R1.md'}
R1_ADDED_PREFIXES = ('regression/m8r1/', 'logs/m8r1/')
CLAIMS = re.compile(r'production[- ]ready|ready for (production|release|use)|release[- ]ready|\bcertified\b|\bguarantee[sd]?\b|100 ?%|fully (tested|verified|covered)|'
                    r'\b(APG-M8|this release|this package|the release|M8) (is|was|has been) (accepted|approved|signed off|verified)\b|integrated with the (Anchor )?Engine\b(?! is)|'
                    r'(EDR-0?5|EDR-0?6|EDR-18|EDR-39|EDR-40|EDR-41|CF-41) (is|was|has been) (closed|satisfied|resolved|ratified)|definitions? (is|are|were) (locked|approved)', re.I)
results = []


def sh(p):
    return hashlib.sha256(open(os.path.join(ROOT, p), 'rb').read()).hexdigest()


def manifest():
    return {line[66:].rstrip('\n'): line[:64] for line in open(os.path.join(G, 'R2_MANIFEST.sha256'), encoding='utf-8')}


def files():
    out = []
    for d, ds, fs in os.walk(ROOT):
        ds[:] = [x for x in ds if x != '__pycache__']
        out += [os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/') for f in fs]
    return sorted(out)


def rows(path):
    return list(csv.DictReader(open(path, encoding='utf-8', newline='')))


def r01():
    m = manifest()
    bad = [p for p, h in m.items() if p not in CHANGED and (not os.path.exists(os.path.join(ROOT, p)) or sh(p) != h)]
    same = [p for p in CHANGED if sh(p) == m[p]]
    return (not bad and not same and len(m) == 1222, 'every one of the 1,222 APG-F67.4-R2 files is byte-identical except README.md, RUN_COMMANDS.txt and four programme '
            'registers (rows appended only; the Engine handoff register is unchanged); no existing application code, test, tool, template, data or specification was modified', bad[:5] + same)


def r02():
    m = manifest()
    extra = [p for p in files() if p not in m]
    undeclared = [p for p in extra if not (p in ADDED_FILES or p.startswith(ADDED_PREFIXES))]
    missing = [p for p in ADDED_FILES if p not in extra]
    return not undeclared and not missing, 'every file beyond APG-F67.4-R2 is a declared M8 addition (apg_auif/, tests_m8/, auif_m8/, the AUIF ZIP, seven tools, the change record, regression and logs)', undeclared + missing


def r03():
    with tempfile.TemporaryDirectory() as td:
        for n in REGS:
            shutil.copy(os.path.join(G, 'r2_registers', n), td)
        r = subprocess.run([sys.executable, '-I', '-B', os.path.join(ROOT, 'tools', 'make_m8_registers.py'), td], capture_output=True, text=True)
        if r.returncode == 0:
            r = subprocess.run([sys.executable, '-I', '-B', os.path.join(ROOT, 'tools', 'make_m8r1_registers.py'), td], capture_output=True, text=True)
        bad = [n for n in REGS if open(os.path.join(td, n), 'rb').read() != open(os.path.join(ROOT, 'programme', n), 'rb').read()]
    for n in REGS:
        old, new = rows(os.path.join(G, 'r2_registers', n)), rows(os.path.join(ROOT, 'programme', n))
        idcol = list(new[0])[0]
        if new[:len(old)] != old or [x[idcol] for x in new[len(old):]] != NEW[n]:
            bad.append(n + ': not the R2 rows plus exactly the M8 rows')
    return r.returncode == 0 and not bad, 'the four registers are exactly what tools/make_m8_registers.py and then tools/make_m8r1_registers.py make from the R2 registers: every R2 row unchanged; F-76 to F-82, SR-121 to SR-126, I-135 to I-141 and CF-46 to CF-53 appended; the Engine handoff register byte-identical to R2', bad + ([r.stderr[-300:]] if r.returncode else [])


def r04():
    P = os.path.join(ROOT, 'programme')
    edr = {r['edr_id']: r['status'] for r in rows(os.path.join(P, 'ENGINE_HANDOFF_REGISTER.csv'))}
    cf = {r['cf_id']: r['status'] for r in rows(os.path.join(P, 'CARRIED_FORWARD_REGISTER.csv'))}
    old_edr = dict(edr)                                                     # the Engine handoff register is an R2 file, byte-identical (R01)
    old_cf = {r['cf_id']: r['status'] for r in rows(os.path.join(G, 'r2_registers', 'CARRIED_FORWARD_REGISTER.csv'))}
    bad = [k for k in old_edr if edr[k] != old_edr[k]] + [k for k in old_cf if cf[k] != old_cf[k]]
    for k in ('EDR-05', 'EDR-06', 'EDR-18', 'EDR-39', 'EDR-40', 'EDR-41'):
        if not edr[k].startswith('Open'):
            bad.append(k + ' is not open')
    if cf['CF-41'] != 'Recorded - deviation, not ratified (product owner decision 2026-10-20)':
        bad.append('CF-41 changed')
    if any(k in edr for k in ('EDR-42', 'EDR-43', 'EDR-44', 'EDR-45', 'EDR-46', 'EDR-47')):
        bad.append('M8 wrote to the Engine handoff register')
    for k in ('CF-46', 'CF-47', 'CF-48', 'CF-49', 'CF-50', 'CF-51', 'CF-52', 'CF-53'):
        if not cf.get(k, '').startswith('Open'):
            bad.append(k + ' is not open')
    f = {r['finding_id']: r['status'] for r in rows(os.path.join(P, 'FINDINGS_REGISTER.csv'))}
    bad += [k for k in ('F-76', 'F-77', 'F-78', 'F-79', 'F-80', 'F-81', 'F-82') if not f[k].startswith('Open')]
    return not bad, 'every EDR and CF status from R2 is unchanged (EDR-05, EDR-06, EDR-18, EDR-39, EDR-40, EDR-41 open; CF-41 as recorded); no EDR row added; the M8 and M8-R1 findings and CF-46 to CF-53 are open', bad


def r05():
    bad = []
    for p in ('README.md', 'programme/CHANGE_RECORD_APG-M8.md'):
        text = open(os.path.join(ROOT, p), encoding='utf-8').read()
        if p == 'README.md':
            text = text.split('---- the APG-F67.4-R2 readme follows')[0] if text.startswith('# APG-M8') else ''
            if not text:
                bad.append('README.md does not start with the M8 section')
        for need in ('Builder-implemented and locally tested', 'not accepted', 'DEV-M8-01', 'PROPOSED', 'AUTHORISE M8', 'Authorise M8 continuation under DEV-M8-01 as written',
                     'synthetic', 'M8-F1', 'unmodified'):
            if need not in text:
                bad.append('%s does not mention %r' % (p, need))
        bad += ['%s: %r' % (p, text[max(0, m.start() - 40):m.end() + 20]) for m in CLAIMS.finditer(text)]
    text = open(os.path.join(ROOT, 'programme', 'CHANGE_RECORD_APG-M8R1.md'), encoding='utf-8').read()          # M8-R1
    for need in ('Builder-implemented and locally tested', 'not accepted', 'M8-F7', 'SOURCE_EMPTY', 'Authorise M8-R1 as written', 'synthetic', 'unmodified', 'DEV-M8-01'):
        if need not in text:
            bad.append('CHANGE_RECORD_APG-M8R1.md does not mention %r' % need)
    bad += ['CHANGE_RECORD_APG-M8R1.md: %r' % text[max(0, m.start() - 40):m.end() + 20] for m in CLAIMS.finditer(text)]
    return not bad, 'the M8 text makes no acceptance, readiness, Engine-integration or gate-closing claim and states the authorisations, DEV-M8-01 and the PROPOSED status', bad[:5]


def r06():
    sys.path.insert(0, ROOT)
    from apg_auif import dependency
    bad = []
    if dependency.sha256_file(dependency.ZIP) != '61748ddeba21e8c1d71b56bd0d3ad7a376ea051f4ae6fbe56c6464c0de76e070':
        bad.append('ZIP hash')
    try:
        root = dependency.extract(tempfile.mkdtemp(prefix='apg_m8_r06_'))
        v = dependency.verify_tree(root)
        shutil.rmtree(os.path.dirname(root))
    except dependency.AuifDependencyError as e:
        bad.append(str(e)[:200])
        v = {}
    return not bad and v.get('core_tree_sha256') == dependency.CORE_TREE_SHA256, 'the package carries the exact AUIF rev13 ZIP (61748dde...); a fresh extraction passes AUIF\'s own manifest check (tree 9fbc5de7..., 248 files) and core tree hash (74cec87a...)', bad


def run(args, what, expect, timeout=1800):
    try:
        r = subprocess.run([sys.executable, '-I'] + args, cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    except subprocess.TimeoutExpired:
        return False, what + ' (INCOMPLETE: cut off by the time limit)', []
    return r.returncode == 0 and expect in r.stdout + r.stderr, what, (r.stdout + r.stderr).strip().splitlines()[-1:]


def r10():
    m = {line[66:].rstrip('\n'): line[:64] for line in open(os.path.join(ROOT, 'regression', 'm8r1', 'M8_MANIFEST.sha256'), encoding='utf-8')}
    now = files()
    changed = sorted(p for p, h in m.items() if os.path.exists(os.path.join(ROOT, p)) and sh(p) != h)
    removed = sorted(p for p in m if not os.path.exists(os.path.join(ROOT, p)))
    added = sorted(p for p in now if p not in m)
    undeclared = [p for p in added if p not in R1_ADDED and not p.startswith(R1_ADDED_PREFIXES)]
    bad = sorted(set(changed) ^ R1_CHANGED) + removed + undeclared + sorted(R1_ADDED - set(added))
    return (not bad and len(m) == 1307, 'against the delivered APG-M8 ZIP (%s..., 1,307 files): only the declared M8-R1 files changed (the adapter intake and gate, the corpus declaration, the corpus and '
            'path-equivalence tests, the boundary test, five M8 tools, README, RUN_COMMANDS and four registers, rows appended only) and only the declared M8-R1 files were added' % M8_ZIP_SHA256[:12], bad[:8])


STEPS = {'R01': r01, 'R02': r02, 'R03': r03, 'R04': r04, 'R05': r05, 'R06': r06,
         'R07': lambda: run(['tools/make_m8_config.py', '--check'], 'the stored definitions, model and packs are exactly what tools/make_m8_config.py generates', 'differing 0, unexpected 0'),
         'R08': lambda: run(['tools/run_m2_tests.py', '-q', 'test_ingest_*.py'], 'the M3 import tests pass unchanged (224, as on R2)', 'tests 224  failures 0  errors 0'),
         'R09': lambda: run(['tools/run_m8_tests.py', '--file', 'test_m8_boundary.py'], 'the M8 boundary tests pass (no other change, no network, Governor or credential)', 'failed files 0'),
         'R10': r10}


def main():
    a = sys.argv[1:]
    if not a or a[0] == '--list':
        print('steps:', ' '.join(STEPS))
        return 0
    want = list(STEPS) if a[0] == '--all' else [a[1]]
    for k in want:
        ok, what, detail = STEPS[k]()
        results.append((k, ok))
        print('%s %s %s %s' % ('PASS' if ok else 'FAIL', k, what, detail if not ok or detail else ''), flush=True)
    failed = [k for k, ok in results if not ok]
    print('\nchecks %d  failed %d' % (len(results), len(failed)) + ('\nFAILED: %r' % failed if failed else ''))
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
