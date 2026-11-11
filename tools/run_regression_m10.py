#!/usr/bin/env python3
"""Regression checks of APG-M10 (the UX/UI prototype) against the delivered APG-M8.1-R1 package (ZIP SHA-256 e39eef1f72eff49131179e4a3a07ee2b178c43bad8f0eaef556d95c0927b778e,
1,390 files; every file hash in regression/m10/M81R1_MANIFEST.sha256, the four programme tables before M10 in regression/m10/m81r1_registers/, the three list files before M10 in
regression/m10/m81r1_lists/).  M10 adds the prototype and its tests; it changes no APG application code, no existing test, no data and no specification.  As in APG-M8-R2 and
APG-M8.1-R1 (the product owner's decision "Update the 2 lists"), M10's files are added to the declared-file lists of the M8 checks, and their register replay runs M10's
register step after M8.1's.  Every step is short except R07 (the view-model tests, about 25 s) and R08 (the M8.1 regression, which reruns the M8 regression and boundary tests).
The browser tests (ui_tests/run_ui_tests.js) need Node and Playwright and are run separately.
Usage: python3 -I tools/run_regression_m10.py --list | --all | --step Rnn      Exit 0 only if every step run passed."""
import collections, csv, difflib, hashlib, os, re, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
G = os.path.join(ROOT, 'regression', 'm10')
TABLES = ('STATUS_REGISTER.csv', 'INTERPRETATIONS_REGISTER.csv', 'CARRIED_FORWARD_REGISTER.csv', 'PROGRAMME_MILESTONES.csv')
LISTS = ('tests_m8/test_m8_boundary.py', 'tools/run_regression_m8.py', 'tools/run_regression_m81.py')
CHANGED = {'README.md', 'RUN_COMMANDS.txt'} | {'programme/' + t for t in TABLES} | set(LISTS)
ADDED_FILES = {'tools/build_m10_views.py', 'tools/sabotage_m10.py', 'tools/make_m10_registers.py', 'tools/run_regression_m10.py', 'programme/CHANGE_RECORD_APG-M10.md'}
ADDED_PREFIXES = ('apg_ui/', 'ui/', 'ui_tests/', 'tests_m10/', 'regression/m10/', 'logs/m10/')
NEW = {'STATUS_REGISTER.csv': ['SR-128'], 'INTERPRETATIONS_REGISTER.csv': ['I-145', 'I-146', 'I-147', 'I-148', 'I-149', 'I-150', 'I-151'], 'CARRIED_FORWARD_REGISTER.csv': ['CF-56', 'CF-57']}
ALLOWED = ADDED_FILES | set(ADDED_PREFIXES) | {'tools/make_m10_registers.py'}
TOKENS = ('M10', 'm10')
CLAIMS = re.compile(r'production[- ]ready|ready for (production|release|use)|release[- ]ready|\bcertified\b|\bguarantee[sd]?\b|100 ?%|fully (tested|verified|covered|accessible)|'
                    r'\b(APG-M10|M10|this release|this package|the release|the prototype|the design) (is|was|has been) (accepted|approved|signed off)\b|WCAG[- ]compliant|'
                    r'integrated with the (Anchor )?Engine\b(?! is)|(EDR-0?5|EDR-0?6|EDR-12|EDR-18|EDR-29|EDR-31|EDR-39|EDR-40|EDR-41|CF-41|CF-52|CF-53) (is|was|has been) (closed|satisfied|resolved|ratified|approved|decided)|'
                    r'definitions? (is|are|were) (locked|approved)|\brealised saving(s)? (of|is|are|was)\b', re.I)
results = []


def sh(p):
    return hashlib.sha256(open(os.path.join(ROOT, p), 'rb').read()).hexdigest()


def files():
    out = []
    for d, ds, fs in os.walk(ROOT):
        ds[:] = [x for x in ds if x not in ('__pycache__', 'node_modules')]
        out += [os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/') for f in fs]
    return sorted(out)


def manifest():
    return {line[66:].rstrip('\n'): line[:64] for line in open(os.path.join(G, 'M81R1_MANIFEST.sha256'), encoding='utf-8')}


def rows(path):
    return list(csv.DictReader(open(path, encoding='utf-8', newline='')))


def r01():
    m = manifest()
    bad = [p for p, h in m.items() if p not in CHANGED and (not os.path.exists(os.path.join(ROOT, p)) or sh(p) != h)]
    same = [p for p in CHANGED if sh(p) == m[p]]
    return (not bad and not same and len(m) == 1390, 'every one of the 1,390 APG-M8.1-R1 files is byte-identical except README.md, RUN_COMMANDS.txt, four programme tables and the '
            'three declared-file lists; no APG application code, existing test, data or specification changed', bad[:5] + same)


def r02():
    m = manifest()
    extra = [p for p in files() if p not in m]
    undeclared = [p for p in extra if not (p in ADDED_FILES or p.startswith(ADDED_PREFIXES))]
    return not undeclared and ADDED_FILES <= set(extra), 'every added file is declared (apg_ui/, ui/, ui_tests/, tests_m10/, four tools, the change record, regression/m10/, logs/m10/)', undeclared + sorted(ADDED_FILES - set(extra))


def r03():
    bad = []
    with tempfile.TemporaryDirectory() as td:
        for n in TABLES:
            shutil.copy(os.path.join(G, 'm81r1_registers', n), td)
        r = subprocess.run([sys.executable, '-I', '-B', os.path.join(ROOT, 'tools', 'make_m10_registers.py'), td], capture_output=True, text=True)
        bad += ['%s is not what tools/make_m10_registers.py makes from the M8.1-R1 table' % n for n in TABLES
                if open(os.path.join(td, n), 'rb').read() != open(os.path.join(ROOT, 'programme', n), 'rb').read()]
    for n, ids in NEW.items():
        old, new = rows(os.path.join(G, 'm81r1_registers', n)), rows(os.path.join(ROOT, 'programme', n))
        idcol = list(new[0])[0]
        if new[:len(old)] != old or [x[idcol] for x in new[len(old):]] != ids:
            bad.append(n + ': not the M8.1-R1 rows plus exactly the M10 rows')
    mo, mn = rows(os.path.join(G, 'm81r1_registers', 'PROGRAMME_MILESTONES.csv')), rows(os.path.join(ROOT, 'programme', 'PROGRAMME_MILESTONES.csv'))
    diffs = [(a['milestone_id'], k) for a, b in zip(mo, mn) for k in a if a[k] != b[k]]
    if len(mo) != len(mn) or diffs != [('M10', 'status')]:
        bad.append('milestones: changed cells %r' % diffs[:5])
    if [b['status'] for b in mn if b['milestone_id'] in ('M11', 'M12')] != ['Not started'] * 2:
        bad.append('M11 or M12 is not "Not started"')
    for x in rows(os.path.join(ROOT, 'programme', 'CARRIED_FORWARD_REGISTER.csv'))[-2:]:
        if not x['status'].startswith('Open'):
            bad.append(x['cf_id'] + ' is not open')
    for x in rows(os.path.join(ROOT, 'programme', 'INTERPRETATIONS_REGISTER.csv'))[-7:]:
        if x['status'] != 'Retained for review - not approved' or x['reviewer_decision']:
            bad.append(x['interpretation_id'] + ' is not retained for review')
    return r.returncode == 0 and not bad, ('the tables are the M8.1-R1 tables plus exactly SR-128, I-145 to I-151 (retained for review) and CF-56, CF-57 (open); in the milestones table only '
                                           'the status of M10 changed; M11 and M12 are not started'), bad[:5] + ([r.stderr[-300:]] if r.returncode else [])


def r04():
    """Every quoted entry of the three list files, counted: the entries M10 adds must be its own files, and none may be removed.  Outside quoted entries, a changed line must name
    M10 (a comment, the union that adds M10's lists, or the call of M10's register step in a register replay)."""
    bad = []
    q = lambda text: collections.Counter(t.strip("'") for line in text.splitlines() for t in re.findall(r"'[^'\n]*'", line.split('#')[0]))
    for p in LISTS:
        old = open(os.path.join(G, 'm81r1_lists', p.replace('/', '__')), encoding='utf-8').read()
        new = open(os.path.join(ROOT, p), encoding='utf-8').read()
        added, removed = q(new) - q(old), q(old) - q(new)
        extra = {a for a in added if a not in ALLOWED and not re.fullmatch(r'(SR-128|I-14[5-9]|I-15[01]|CF-5[67]|STATUS_REGISTER\.csv|INTERPRETATIONS_REGISTER\.csv|CARRIED_FORWARD_REGISTER\.csv)', a)}
        extra -= {'tools', 'make_m10_registers.py', '-I', '-B'}
        extra -= {'# APG-M10', '---- the APG-M8.1-R1 readme follows, unchanged ----'}      # the M8 readme check skips M10's section on top (tools/run_regression_m8.py R05)
        if extra:
            bad.append('%s: new entries %s' % (p, sorted(extra)[:4]))
        if removed:
            bad.append('%s: removed entries %s' % (p, sorted(removed)[:3]))
        for d in difflib.ndiff(old.splitlines(True), new.splitlines(True)):
            if d.startswith('+ ') and re.sub(r"'[^']*'", '', d[2:].split('#')[0]).strip(' ,{}()\n') and not any(t in d for t in TOKENS):
                bad.append('%s: changed code %s' % (p, d[2:].strip()[:100]))
    return not bad, ('the three list files changed only to declare M10\'s files and rows (no other new entry, no entry removed, every other changed line names M10)'), bad[:5]


def r05():
    bad = []
    t = open(os.path.join(ROOT, 'README.md'), encoding='utf-8').read().split('---- the APG-M8.1-R1 readme follows')[0]
    c = open(os.path.join(ROOT, 'programme', 'CHANGE_RECORD_APG-M10.md'), encoding='utf-8').read()
    for name, text in (('README.md', t), ('CHANGE_RECORD_APG-M10.md', c)):
        for need in ('Authorise M10 as proposed, director first', 'not accepted', 'prototype', 'synthetic', 'PROPOSED', 'CF-53', 'CF-56', 'CF-57', 'sends nothing', 'realised'):
            if need not in text:
                bad.append('%s does not mention %r' % (name, need))
        bad += ['%s: %r' % (name, text[max(0, m.start() - 40):m.end() + 20]) for m in CLAIMS.finditer(text)]
    return not bad, 'the M10 text states the authorisation, that it is a prototype over synthetic data that sends nothing, and what stays open, and makes no acceptance, readiness or gate-closing claim', bad[:5]


def run(args, what, expect, timeout=3600, py=True):
    try:
        r = subprocess.run(([sys.executable] if py else []) + args, cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    except subprocess.TimeoutExpired:
        return False, what + ' (INCOMPLETE: cut off by the time limit)', []
    out = r.stdout + r.stderr
    return r.returncode == 0 and expect in out, what, out.strip().splitlines()[-1:]


STEPS = {'R01': r01, 'R02': r02, 'R03': r03, 'R04': r04, 'R05': r05,
         'R06': lambda: run(['-I', 'tools/build_m10_views.py', '--check'], 'ui/data/views.js is exactly what the view model builds from the APG code now', 'matches a fresh build'),
         'R07': lambda: run(['-B', '-W', 'ignore', '-m', 'unittest', 'tests_m10.test_m10_viewmodel'], 'the 19 view-model tests pass', 'Ran 19 tests'),
         'R08': lambda: run(['-I', 'tools/run_regression_m81.py', '--all'], 'the M8.1 regression R01 to R09 still passes with M10 declared (its R08 reruns the M8 regression, its R09 the M8 boundary tests)', 'checks 9  failed 0')}


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
