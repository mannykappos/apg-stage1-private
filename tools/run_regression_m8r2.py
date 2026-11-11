#!/usr/bin/env python3
"""Regression checks of the records-only release APG-M8-R2 against the delivered APG-M8-R1 package (ZIP SHA-256
6e326a6ea02c0df4c7c40952294efcffdd2e74b52340aa1127437f17c7d16fe8, 1,328 files; hashes in regression/m8r2/M8R1_MANIFEST.sha256, the disposition register before R2 in
regression/m8r2/m8r1_snapshot/).  R2 appends the auditor's dispositions AD-13 to AD-20 and, on the product owner's decision, adds its own files to the declared-file lists of
the two M8 checks that would otherwise report them (tests_m8/test_m8_boundary.py and tools/run_regression_m8.py).  It changes no application code, no test logic and no
specification.  Every step is short except R07 and R08, which rerun those two M8 checks.
Usage: python3 -I tools/run_regression_m8r2.py --list | --all | --step Rnn      Exit 0 only if every step run passed."""
import csv, difflib, hashlib, os, re, subprocess, sys, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
G = os.path.join(ROOT, 'regression', 'm8r2')
DISP = 'programme/AUDIT_DISPOSITION_REGISTER.csv'
LISTS = ('tests_m8/test_m8_boundary.py', 'tools/run_regression_m8.py')
CHANGED = {'README.md', 'RUN_COMMANDS.txt', DISP} | set(LISTS)
ADDED_FILES = {'tools/make_m8r2_registers.py', 'tools/run_regression_m8r2.py', 'programme/CHANGE_RECORD_APG-M8R2.md'}
ADDED_PREFIXES = ('regression/m8r2/', 'logs/m8r2/')
NEW = [('AD-13', 'F-82', 'APG-M8'), ('AD-14', 'F-82', 'APG-M8-R1'), ('AD-15', 'F-76', 'AUIF rev14'), ('AD-16', 'F-77', 'AUIF rev14'), ('AD-17', 'F-78', 'AUIF rev14'),
       ('AD-18', 'F-79', 'AUIF rev14'), ('AD-19', 'F-80', 'AUIF rev14'), ('AD-20', 'F-81', 'AUIF rev14')]
TOKENS = ('m8r2', 'M8-R2', 'AUDIT_DISPOSITION_REGISTER')
ALLOWED = ADDED_FILES | set(ADDED_PREFIXES) | {DISP}
CLAIMS = re.compile(r'production[- ]ready|ready for (production|release|use)|release[- ]ready|\bcertified\b|\bguarantee[sd]?\b|100 ?%|fully (tested|verified|covered)|'
                    r'\b(APG-M8(-R[12])?|AUIF rev14|rev14|this release|this package|the release|M8) (is|was|has been) (accepted|approved|signed off)\b|integrated with the (Anchor )?Engine\b(?! is)|'
                    r'(EDR-0?5|EDR-0?6|EDR-18|EDR-39|EDR-40|EDR-41|CF-41|CF-53) (is|was|has been) (closed|satisfied|resolved|ratified|approved)|M8\.1 (is|was|has been) (authorised|started)', re.I)
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
    return {line[66:].rstrip('\n'): line[:64] for line in open(os.path.join(G, 'M8R1_MANIFEST.sha256'), encoding='utf-8')}


def rows(path):
    return list(csv.DictReader(open(path, encoding='utf-8', newline='')))


def r01():
    m = manifest()
    bad = [p for p, h in m.items() if p not in CHANGED and (not os.path.exists(os.path.join(ROOT, p)) or sh(p) != h)]
    same = [p for p in CHANGED if sh(p) == m[p]]
    return (not bad and not same and len(m) == 1328, 'every one of the 1,328 APG-M8-R1 files is byte-identical except README.md, RUN_COMMANDS.txt, the audit disposition '
            'register and the two declared-file lists; no application code, test logic, data or specification changed', bad[:5] + same)


def r02():
    m = manifest()
    extra = [p for p in files() if p not in m]
    undeclared = [p for p in extra if not (p in ADDED_FILES or p.startswith(ADDED_PREFIXES))]
    return not undeclared and ADDED_FILES <= set(extra), 'every added file is declared (two tools, the change record, regression/m8r2/, logs/m8r2/)', undeclared + sorted(ADDED_FILES - set(extra))


def r03():
    with tempfile.TemporaryDirectory() as td:
        shutil.copy(os.path.join(G, 'm8r1_snapshot', 'AUDIT_DISPOSITION_REGISTER.csv'), td)
        r = subprocess.run([sys.executable, '-I', '-B', os.path.join(ROOT, 'tools', 'make_m8r2_registers.py'), td], capture_output=True, text=True)
        same = open(os.path.join(td, 'AUDIT_DISPOSITION_REGISTER.csv'), 'rb').read() == open(os.path.join(ROOT, DISP), 'rb').read()
    old, new = rows(os.path.join(G, 'm8r1_snapshot', 'AUDIT_DISPOSITION_REGISTER.csv')), rows(os.path.join(ROOT, DISP))
    bad = [] if same else ['the register is not what tools/make_m8r2_registers.py makes from the snapshot']
    if new[:len(old)] != old:
        bad.append('an existing disposition row changed')
    got = [(x['disposition_id'], x['finding_id'], x['release_audited']) for x in new[len(old):]]
    if got != NEW:
        bad.append('appended rows %r' % got)
    for x in new[len(old):]:
        if x['recorded_in'] != 'APG-M8-R2' or not x['what_this_does_not_mean']:
            bad.append(x['disposition_id'] + ': recorded_in or what_this_does_not_mean')
    return r.returncode == 0 and not bad, 'the disposition register is the M8-R1 register plus exactly AD-13 to AD-20 (F-82 on APG-M8 and on APG-M8-R1; F-76 to F-81 on AUIF rev14); no existing row changed', bad


def r04():
    """Every quoted entry of the two files, counted: the entries R2 adds must be exactly its own files and the disposition register, and none may be removed. Outside quoted
    entries, a changed line must name M8-R2 or the register (a comment or the union that adds the register)."""
    import collections
    bad = []
    q = lambda text: collections.Counter(t.strip("'") for line in text.splitlines() for t in re.findall(r"'[^'\n]*'", line.split('#')[0]))
    for p in LISTS:
        old = open(os.path.join(G, 'm8r1_lists', p.replace('/', '__')), encoding='utf-8').read()
        new = open(os.path.join(ROOT, p), encoding='utf-8').read()
        added, removed = q(new) - q(old), q(old) - q(new)
        if set(added) - ALLOWED:
            bad.append('%s: new entries %s' % (p, sorted(set(added) - ALLOWED)[:3]))
        if removed:
            bad.append('%s: removed entries %s' % (p, sorted(removed)[:3]))
        for d in difflib.ndiff(old.splitlines(True), new.splitlines(True)):
            if d.startswith('+ ') and re.sub(r"'[^']*'", '', d[2:].split('#')[0]).strip(' ,{}()\n') and not any(t in d for t in TOKENS):
                bad.append('%s: changed code %s' % (p, d[2:].strip()[:100]))
    return not bad, 'the two M8 checks changed only by adding M8-R2\'s own files and the disposition register to their declared lists (no other new entry; no entry is removed)', bad[:5]


def r05():
    bad = []
    t = open(os.path.join(ROOT, 'README.md'), encoding='utf-8').read().split('---- the APG-M8-R1 readme follows')[0]
    c = open(os.path.join(ROOT, 'programme', 'CHANGE_RECORD_APG-M8R2.md'), encoding='utf-8').read()
    for name, text in (('README.md', t), ('CHANGE_RECORD_APG-M8R2.md', c)):
        for need in ('records only', 'not accepted', 'AD-13', 'AD-20', 'CF-53', 'M8.1', 'Authorise the records-only release for the M8, M8-R1 and rev14 audit results, after the rev14 audit'):
            if need not in text:
                bad.append('%s does not mention %r' % (name, need))
        bad += ['%s: %r' % (name, text[max(0, m.start() - 40):m.end() + 20]) for m in CLAIMS.finditer(text)]
    return not bad, 'the M8-R2 text states the authorisation, the dispositions and what stays open, and makes no acceptance, readiness, Engine-integration or gate-closing claim', bad[:5]


def run(args, what, expect, timeout=3600):
    try:
        r = subprocess.run([sys.executable, '-I'] + args, cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    except subprocess.TimeoutExpired:
        return False, what + ' (INCOMPLETE: cut off by the time limit)', []
    return r.returncode == 0 and expect in r.stdout + r.stderr, what, (r.stdout + r.stderr).strip().splitlines()[-1:]


STEPS = {'R01': r01, 'R02': r02, 'R03': r03, 'R04': r04, 'R05': r05,
         'R06': lambda: run(['tools/make_m8_config.py', '--check'], 'the stored definitions, model and packs are unchanged', 'differing 0, unexpected 0'),
         'R07': lambda: run(['tools/run_regression_m8.py', '--all'], 'the M8 regression R01 to R10 still passes with the extended lists', 'checks 10  failed 0'),
         'R08': lambda: run(['tools/run_m8_tests.py', '--file', 'test_m8_boundary.py'], 'the M8 boundary tests still pass with the extended lists', 'failed files 0')}


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
