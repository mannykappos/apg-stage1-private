#!/usr/bin/env python3
"""Regression checks of APG-M8.1 against the delivered APG-M8-R2 package (ZIP SHA-256 dadcba92e801280ca1c82bc9ac7ba96efad00c169e666f2916782c70568927a8, 1,340 files;
every file hash in regression/m81/M8R2_MANIFEST.sha256, the four registers before M8.1 in regression/m81/m8r2_registers/).  M8.1 moves APG onto AUIF rev14 (product owner,
2026-10-21: "Authorise M8.1 as written, on AUIF rev14 as audited with its stated qualifications").  The lists below are the ONE declaration of what M8.1 changes, adds and
removes; tools/run_regression_m8.py and tests_m8/test_m8_boundary.py read the same intent.  Every step is short except R08 and R09.
Usage: python3 -I tools/run_regression_m81.py --list | --all | --step Rnn      Exit 0 only if every step run passed."""
import csv, hashlib, json, os, re, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
G = os.path.join(ROOT, 'regression', 'm81')
REGS = ('STATUS_REGISTER.csv', 'INTERPRETATIONS_REGISTER.csv', 'CARRIED_FORWARD_REGISTER.csv')
M81_CHANGED = {'README.md', 'RUN_COMMANDS.txt', 'apg_auif/__init__.py', 'apg_auif/client.py', 'apg_auif/definitions.py', 'apg_auif/dependency.py', 'apg_auif/intake.py',
               'apg_auif/module.py', 'apg_auif/pack.py', 'auif_m8/PATH_EQUIVALENCE_DECLARED_DIFFERENCES.json', 'auif_m8/definitions/construction_definitions.json',
               'tests_m8/test_m8_boundary.py', 'tests_m8/test_m8_definitions.py', 'tests_m8/test_m8_dependency.py', 'tests_m8/test_m8_dev01.py', 'tests_m8/test_m8_events.py',
               'tests_m8/test_m8_findings.py', 'tests_m8/test_m8r1_empty_source.py', 'tools/m8_mutants.py', 'tools/make_m8_config.py', 'tools/run_m8_all.py',
               'tools/run_m8_tests.py', 'tools/run_regression_m8.py', 'tools/sabotage_m8.py'} | {'programme/' + r for r in REGS}
M81_CHANGED_PREFIXES = ('auif_m8/packs/',)                                   # the 15 packs, regenerated in the contract form
M81_ADDED = {'tools/make_m81_registers.py', 'tools/run_regression_m81.py', 'programme/CHANGE_RECORD_APG-M8.1.md'}
M81_ADDED_PREFIXES = ('third_party/auif_rev14/', 'regression/m81/', 'logs/m81/')
M81_REMOVED = {'third_party/auif_rev13/AUIF_Independent_Build_v1.0_rev13.zip', 'third_party/auif_rev13/AUIF_Independent_Build_v1.0_rev13.zip.sha256'}
NEW = {'STATUS_REGISTER.csv': ['SR-127'], 'INTERPRETATIONS_REGISTER.csv': ['I-142', 'I-143', 'I-144'], 'CARRIED_FORWARD_REGISTER.csv': ['CF-54', 'CF-55']}
REV14 = 'd534a6e6541b6d1a58e0389161d08698a1d7ac92ee9ad880a51fcee36497c649'
CLAIMS = re.compile(r'production[- ]ready|ready for (production|release|use)|release[- ]ready|\bcertified\b|\bguarantee[sd]?\b|100 ?%|fully (tested|verified|covered)|'
                    r'\b(APG-M8(\.1|-R[12])?|AUIF rev14|rev14|this release|this package|the release|M8(\.1)?) (is|was|has been) (accepted|approved|signed off|verified)\b|'
                    r'integrated with the (Anchor )?Engine\b(?! is)|(EDR-0?5|EDR-0?6|EDR-18|EDR-39|EDR-40|EDR-41|CF-41|CF-53) (is|was|has been) (closed|satisfied|resolved|ratified|approved)|'
                    r'definitions? (is|are|were) (locked|approved)', re.I)
results = []


def sh(p):
    return hashlib.sha256(open(os.path.join(ROOT, p), 'rb').read()).hexdigest()


def files():
    out = []
    for d, ds, fs in os.walk(ROOT):
        ds[:] = [x for x in ds if x != '__pycache__']
        out += [os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/') for f in fs]
    return sorted(out)


def manifest():
    return {line[66:].rstrip('\n'): line[:64] for line in open(os.path.join(G, 'M8R2_MANIFEST.sha256'), encoding='utf-8')}


def changed_declared(p):
    return p in M81_CHANGED or p.startswith(M81_CHANGED_PREFIXES)


def rows(path):
    return list(csv.DictReader(open(path, encoding='utf-8', newline='')))


def r01():
    m = manifest()
    present = {p for p in m if os.path.exists(os.path.join(ROOT, p))}
    bad = [p for p in present if not changed_declared(p) and sh(p) != m[p]]
    same = [p for p in present if changed_declared(p) and sh(p) == m[p]]
    removed = sorted(set(m) - present)
    ok = not bad and not same and removed == sorted(M81_REMOVED) and len(m) == 1340
    return ok, ('every APG-M8-R2 file is byte-identical except the declared M8.1 changes (the adapter, the configuration, seven M8 test files, seven M8 tools, README, '
                'RUN_COMMANDS, three registers); the only removal is the AUIF rev13 ZIP and its sidecar; no apg/ or tests/ file changed'), bad[:5] + same[:5] + removed[:3]


def r02():
    m = manifest()
    extra = [p for p in files() if p not in m]
    undeclared = [p for p in extra if not (p in M81_ADDED or p.startswith(M81_ADDED_PREFIXES))]
    missing = sorted(M81_ADDED - set(extra))
    return not undeclared and not missing, 'every added file is declared (the AUIF rev14 ZIP and its sidecar, two tools, the change record, regression/m81/, logs/m81/)', undeclared + missing


def r03():
    with tempfile.TemporaryDirectory() as td:
        for n in REGS:
            shutil.copy(os.path.join(G, 'm8r2_registers', n), td)
        r = subprocess.run([sys.executable, '-I', '-B', os.path.join(ROOT, 'tools', 'make_m81_registers.py'), td], capture_output=True, text=True)
        bad = [n for n in REGS if open(os.path.join(td, n), 'rb').read() != open(os.path.join(ROOT, 'programme', n), 'rb').read()]
    for n in REGS:
        old, new = rows(os.path.join(G, 'm8r2_registers', n)), rows(os.path.join(ROOT, 'programme', n))
        idcol = list(new[0])[0]
        if new[:len(old)] != old or [x[idcol] for x in new[len(old):]] != NEW[n]:
            bad.append(n + ': not the M8-R2 rows plus exactly the M8.1 rows')
    f = rows(os.path.join(ROOT, 'programme', 'FINDINGS_REGISTER.csv'))
    if f != rows(os.path.join(G, 'm8r2_registers', 'FINDINGS_REGISTER.csv')):
        bad.append('the findings register changed')
    return r.returncode == 0 and not bad, 'the registers are the M8-R2 registers plus exactly SR-127, I-142 to I-144, CF-54 and CF-55; no existing row changed; no finding added', bad + ([r.stderr[-300:]] if r.returncode else [])


def r04():
    sys.path.insert(0, ROOT)
    from apg_auif import dependency
    bad = []
    if dependency.sha256_file(dependency.ZIP) != REV14 or dependency.ZIP_SHA256 != REV14:
        bad.append('ZIP hash')
    try:
        root = dependency.extract(tempfile.mkdtemp(prefix='apg_m81_r04_'))
        v = dependency.verify_tree(root)
        shutil.rmtree(os.path.dirname(root))
    except dependency.AuifDependencyError as e:
        bad.append(str(e)[:200])
        v = {}
    ok = not bad and v.get('core_tree_sha256') == '923de5100f95debbbf63d5ab6e960cee2091ee57abce403792403ff049ac7839' and v.get('files_checked') == 253
    return ok, 'the package carries the exact AUIF rev14 ZIP (d534a6e6...); a fresh extraction passes AUIF\'s own manifest check (253 files, tree 4918c2a6...) and core tree hash (923de510...)', bad


def r05():
    bad = []
    for name, text in (('README.md', open(os.path.join(ROOT, 'README.md'), encoding='utf-8').read().split('---- the APG-M8-R2 readme follows')[0]),
                       ('CHANGE_RECORD_APG-M8.1.md', open(os.path.join(ROOT, 'programme', 'CHANGE_RECORD_APG-M8.1.md'), encoding='utf-8').read())):
        for need in ('Builder-implemented and locally tested', 'not accepted', 'Authorise M8.1 as written, on AUIF rev14 as audited with its stated qualifications', 'DEV-M8-01',
                     'qualifications', 'PROPOSED', 'CF-53', 'synthetic', 'SOURCE_EMPTY'):
            if need not in text:
                bad.append('%s does not mention %r' % (name, need))
        bad += ['%s: %r' % (name, text[max(0, m.start() - 40):m.end() + 20]) for m in CLAIMS.finditer(text)]
    return not bad, 'the M8.1 text states the authorisation, the dependency\'s qualifications, the end of DEV-M8-01 and what stays open, and makes no acceptance, readiness, Engine-integration or gate-closing claim', bad[:5]


def r06():
    bad = []
    for fn in sorted(os.listdir(os.path.join(ROOT, 'auif_m8', 'packs'))):
        p = json.load(open(os.path.join(ROOT, 'auif_m8', 'packs', fn), encoding='utf-8'))
        ents = {m['source_ref']: m['canonical_ref'] for m in p['mappings'] if m['kind'] == 'ENTITY'}
        for m in p['mappings']:
            if m['kind'] == 'FIELD':
                c = ents.get(m['source_ref'].split('.', 1)[0], '')
                if not (c.startswith('module.apg.') and m['canonical_ref'].startswith(c + '.') and '.' not in m['canonical_ref'][len(c) + 1:]):
                    bad.append('%s %s %s' % (fn, m['mapping_id'], m['canonical_ref']))
    return not bad, 'every FIELD mapping of the 15 stored packs is in the contract form module.apg.<Type>.<attribute> of its entity\'s concept (DEV-M8-01 ended)', bad[:5]


def run(args, what, expect, timeout=3600):
    try:
        r = subprocess.run([sys.executable, '-I'] + args, cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    except subprocess.TimeoutExpired:
        return False, what + ' (INCOMPLETE: cut off by the time limit)', []
    return r.returncode == 0 and expect in r.stdout + r.stderr, what, (r.stdout + r.stderr).strip().splitlines()[-1:]


STEPS = {'R01': r01, 'R02': r02, 'R03': r03, 'R04': r04, 'R05': r05, 'R06': r06,
         'R07': lambda: run(['tools/make_m8_config.py', '--check'], 'the stored definitions, model and packs are exactly what tools/make_m8_config.py generates', 'differing 0, unexpected 0'),
         'R08': lambda: run(['tools/run_regression_m8.py', '--all'], 'the M8 regression R01 to R10 passes on M8.1', 'checks 10  failed 0'),
         'R09': lambda: run(['tools/run_m8_tests.py', '--file', 'test_m8_boundary.py'], 'the M8 boundary tests pass (no other change, no network, Governor or credential)', 'failed files 0')}


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
