#!/usr/bin/env python3
"""Regression checks of the records-only release APG-M8.1-R1 against the delivered APG-M8.1 package (ZIP SHA-256
60d4a47318782cdab2f59d54696c1cd493a365ce261ae269bdde52e41c9e2251, 1,368 files; hashes in regression/m81r1/M81_MANIFEST.sha256, the two tables before R1 in
regression/m81r1/m81_snapshot/, the three list files before R1 in regression/m81r1/m81_lists/).  R1 appends the auditor's disposition AD-21, sets the status of the M8 milestone
row and, as in APG-M8-R2 (the product owner's decision "Update the 2 lists"), adds its own files to the declared-file lists of the M8 checks that would otherwise report them.
Since APG-M8.1 those lists are held in three files: tools/run_regression_m81.py (the one declaration, read by tools/run_regression_m8.py), tools/run_regression_m8.py and
tests_m8/test_m8_boundary.py.  It changes no application code, no test logic, no data and no specification.  Every step is short except R07, which reruns the M8.1 regression.
Usage: python3 -I tools/run_regression_m81r1.py --list | --all | --step Rnn      Exit 0 only if every step run passed."""
import collections, csv, difflib, hashlib, os, re, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
G = os.path.join(ROOT, 'regression', 'm81r1')
DISP = 'programme/AUDIT_DISPOSITION_REGISTER.csv'
MILES = 'programme/PROGRAMME_MILESTONES.csv'
LISTS = ('tests_m8/test_m8_boundary.py', 'tools/run_regression_m8.py', 'tools/run_regression_m81.py')
CHANGED = {'README.md', 'RUN_COMMANDS.txt', DISP, MILES} | set(LISTS)
ADDED_FILES = {'tools/make_m81r1_registers.py', 'tools/run_regression_m81r1.py', 'programme/CHANGE_RECORD_APG-M8.1-R1.md'}
ADDED_PREFIXES = ('regression/m81r1/', 'logs/m81r1/')
ALLOWED = ADDED_FILES | set(ADDED_PREFIXES) | {DISP, MILES}
TOKENS = ('m81r1', 'M81R1', 'M8.1-R1')
CLAIMS = re.compile(r'production[- ]ready|ready for (production|release|use)|release[- ]ready|\bcertified\b|\bguarantee[sd]?\b|100 ?%|fully (tested|verified|covered)|'
                    r'\b(APG-M8(\.1)?(-R[12])?|AUIF rev14|rev14|this release|this package|the release|M8(\.1)?) (is|was|has been) (accepted|approved|signed off)\b|'
                    r'integrated with the (Anchor )?Engine\b(?! is)|(EDR-0?5|EDR-0?6|EDR-18|EDR-39|EDR-40|EDR-41|CF-41|CF-52|CF-53) (is|was|has been) (closed|satisfied|resolved|ratified|approved|decided)|'
                    r'definitions? (is|are|were) (locked|approved)|M10 (is|was|has been) (delivered|built|completed)', re.I)
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
    return {line[66:].rstrip('\n'): line[:64] for line in open(os.path.join(G, 'M81_MANIFEST.sha256'), encoding='utf-8')}


def rows(path):
    return list(csv.DictReader(open(path, encoding='utf-8', newline='')))


def r01():
    m = manifest()
    bad = [p for p, h in m.items() if p not in CHANGED and (not os.path.exists(os.path.join(ROOT, p)) or sh(p) != h)]
    same = [p for p in CHANGED if sh(p) == m[p]]
    return (not bad and not same and len(m) == 1368, 'every one of the 1,368 APG-M8.1 files is byte-identical except README.md, RUN_COMMANDS.txt, the audit disposition '
            'register, the milestones table and the three declared-file lists; no application code, test logic, data or specification changed', bad[:5] + same)


def r02():
    m = manifest()
    extra = [p for p in files() if p not in m]
    undeclared = [p for p in extra if not (p in ADDED_FILES or p.startswith(ADDED_PREFIXES))]
    return not undeclared and ADDED_FILES <= set(extra), 'every added file is declared (two tools, the change record, regression/m81r1/, logs/m81r1/)', undeclared + sorted(ADDED_FILES - set(extra))


def r03():
    bad = []
    with tempfile.TemporaryDirectory() as td:
        for n in ('AUDIT_DISPOSITION_REGISTER.csv', 'PROGRAMME_MILESTONES.csv'):
            shutil.copy(os.path.join(G, 'm81_snapshot', n), td)
        r = subprocess.run([sys.executable, '-I', '-B', os.path.join(ROOT, 'tools', 'make_m81r1_registers.py'), td], capture_output=True, text=True)
        for n, p in (('AUDIT_DISPOSITION_REGISTER.csv', DISP), ('PROGRAMME_MILESTONES.csv', MILES)):
            if open(os.path.join(td, n), 'rb').read() != open(os.path.join(ROOT, p), 'rb').read():
                bad.append('%s is not what tools/make_m81r1_registers.py makes from the snapshot' % n)
    old, new = rows(os.path.join(G, 'm81_snapshot', 'AUDIT_DISPOSITION_REGISTER.csv')), rows(os.path.join(ROOT, DISP))
    if new[:len(old)] != old:
        bad.append('an existing disposition row changed')
    got = [(x['disposition_id'], x['release_audited'], x['recorded_in']) for x in new[len(old):]]
    if got != [('AD-21', 'APG-M8.1', 'APG-M8.1-R1')]:
        bad.append('appended rows %r' % got)
    for x in new[len(old):]:
        for need in ('CF-53', 'not production readiness', 'zero_two'):
            if need not in x['what_this_does_not_mean']:
                bad.append('AD-21 what_this_does_not_mean lacks %r' % need)
        for need in ('Python 3.12', 'real-Governor'):
            if need not in x['what_is_not_independently_verified']:
                bad.append('AD-21 what_is_not_independently_verified lacks %r' % need)
    mo, mn = rows(os.path.join(G, 'm81_snapshot', 'PROGRAMME_MILESTONES.csv')), rows(os.path.join(ROOT, MILES))
    diffs = [(a['milestone_id'], k) for a, b in zip(mo, mn) for k in a if a[k] != b[k]]
    if len(mo) != len(mn) or diffs != [('M8', 'status')]:
        bad.append('milestones: changed cells %r' % diffs[:5])
    st = next((b['status'] for b in mn if b['milestone_id'] == 'M8'), '')
    if 'AD-21' not in st or 'CF-53' not in st or 'Not accepted' not in st:
        bad.append('the M8 status does not name AD-21, CF-53 and "Not accepted"')
    if [b['status'] for b in mn if b['milestone_id'] in ('M10', 'M11', 'M12')] != ['Not started'] * 3:
        bad.append('M10 to M12 are not all "Not started"')
    return r.returncode == 0 and not bad, ('the disposition register is the M8.1 register plus exactly AD-21 (APG-M8.1, with its qualifications and what it does not mean); in the '
                                           'milestones table only the status of M8 changed; M10 to M12 are not started; no existing disposition row changed'), bad[:5]


def r04():
    """Every quoted entry of the three files, counted: the entries R1 adds must be exactly its own files and the two tables, and none may be removed. Outside quoted entries, a
    changed line must name M8.1-R1 (a comment or the union that adds its lists)."""
    bad = []
    q = lambda text: collections.Counter(t.strip("'") for line in text.splitlines() for t in re.findall(r"'[^'\n]*'", line.split('#')[0]))
    for p in LISTS:
        old = open(os.path.join(G, 'm81_lists', p.replace('/', '__')), encoding='utf-8').read()
        new = open(os.path.join(ROOT, p), encoding='utf-8').read()
        added, removed = q(new) - q(old), q(old) - q(new)
        if set(added) - ALLOWED:
            bad.append('%s: new entries %s' % (p, sorted(set(added) - ALLOWED)[:3]))
        if removed:
            bad.append('%s: removed entries %s' % (p, sorted(removed)[:3]))
        for d in difflib.ndiff(old.splitlines(True), new.splitlines(True)):
            if d.startswith('+ ') and re.sub(r"'[^']*'", '', d[2:].split('#')[0]).strip(' ,{}()\n') and not any(t in d for t in TOKENS):
                bad.append('%s: changed code %s' % (p, d[2:].strip()[:100]))
    return not bad, ('the three list files changed only by adding M8.1-R1\'s own files and its two tables to their declared lists (no other new entry; no entry is removed; every '
                     'other changed line names M8.1-R1)'), bad[:5]


def r05():
    bad = []
    t = open(os.path.join(ROOT, 'README.md'), encoding='utf-8').read().split('---- the APG-M8.1 readme follows')[0]
    c = open(os.path.join(ROOT, 'programme', 'CHANGE_RECORD_APG-M8.1-R1.md'), encoding='utf-8').read()
    for name, text in (('README.md', t), ('CHANGE_RECORD_APG-M8.1-R1.md', c)):
        for need in ('records only', 'not accepted', 'AD-21', 'CF-53', 'zero_two', 'Python 3.12', 'real-Governor', 'PROPOSED', 'Authorise the records-only release for the M8.1 audit result'):
            if need not in text:
                bad.append('%s does not mention %r' % (name, need))
        bad += ['%s: %r' % (name, text[max(0, m.start() - 40):m.end() + 20]) for m in CLAIMS.finditer(text)]
    return not bad, 'the M8.1-R1 text states the authorisation, the disposition, its qualifications and what stays open, and makes no acceptance, readiness, Engine-integration or gate-closing claim', bad[:5]


def run(args, what, expect, timeout=3600):
    try:
        r = subprocess.run([sys.executable, '-I'] + args, cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    except subprocess.TimeoutExpired:
        return False, what + ' (INCOMPLETE: cut off by the time limit)', []
    return r.returncode == 0 and expect in r.stdout + r.stderr, what, (r.stdout + r.stderr).strip().splitlines()[-1:]


STEPS = {'R01': r01, 'R02': r02, 'R03': r03, 'R04': r04, 'R05': r05,
         'R06': lambda: run(['tools/make_m8_config.py', '--check'], 'the stored definitions, model and packs are unchanged', 'differing 0, unexpected 0'),
         'R07': lambda: run(['tools/run_regression_m81.py', '--all'], 'the M8.1 regression R01 to R09 still passes with the extended lists (its R08 reruns the M8 regression R01 to R10, its R09 the M8 boundary tests)', 'checks 9  failed 0')}


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
