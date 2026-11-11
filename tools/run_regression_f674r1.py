#!/usr/bin/env python3
"""Regression checks of the records-only release APG-F67.4-R1 against the delivered APG-F67.4 package (ZIP SHA-256
4abaa349e201ae2ffccb589b248b2e5d255a92340acdf2bfed17b1194b56c4cd, 1,209 files; hashes in regression/f674r1/F674_MANIFEST.sha256, the disposition register before R1 in
regression/f674r1/f674_snapshot/).  R1 records the auditor's finding-level dispositions of F-75, F-74, F-73, F-72 and F-67 and changes no code, test, tool or specification.
Every step is short.  Usage: python3 -I tools/run_regression_f674r1.py --list | --all | --step Rnn      Exit 0 only if every step run passed."""
import csv, hashlib, os, re, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
G = os.path.join(ROOT, 'regression', 'f674r1')
MAN = os.path.join(G, 'F674_MANIFEST.sha256')
SNAP = os.path.join(G, 'f674_snapshot')
DISP = 'programme/AUDIT_DISPOSITION_REGISTER.csv'
CHANGED = {'README.md', 'RUN_COMMANDS.txt', DISP}
ADDED_FILES = {'tools/make_f674r1_registers.py', 'tools/run_regression_f674r1.py', 'programme/CHANGE_RECORD_APG-F67.4-R1.md'}
ADDED_PREFIXES = ('regression/f674r1/', 'logs/f674r1/')
NEW = [('AD-04', 'F-75'), ('AD-05', 'F-74'), ('AD-06', 'F-73'), ('AD-07', 'F-72'), ('AD-08', 'F-67')]
CLAIMS = re.compile(r'production[- ]ready|ready for (production|release|use)|release[- ]ready|\bcertified\b|\bguarantee[sd]?\b|100 ?%|fully (tested|verified|covered)|'
                    r'\b(APG-F67(\.[1-4])?(-R1)?|this release|this package|the release) (is|was|has been) (accepted|approved|signed off)\b|M8 (is|was|has been) (authorised|started)|'
                    r'(EDR-39|EDR-40|EDR-41|CF-41) (is|was|has been) (closed|satisfied|resolved|ratified)', re.I)
results = []


def sh(p):
    return hashlib.sha256(open(os.path.join(ROOT, p), 'rb').read()).hexdigest()


def files():
    out = []
    for d, ds, fs in os.walk(ROOT):
        ds[:] = [x for x in ds if x != '__pycache__']
        out += [os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/') for f in fs]
    return sorted(out)


def rows(path):
    return list(csv.DictReader(open(path, encoding='utf-8', newline='')))


def manifest():
    return {line[66:].rstrip('\n'): line[:64] for line in open(MAN, encoding='utf-8')}


def r01():
    m = manifest()
    bad = [p for p, h in m.items() if p not in CHANGED and (not os.path.exists(os.path.join(ROOT, p)) or sh(p) != h)]
    same = [p for p in CHANGED if sh(p) == m[p]]
    return (not bad and not same and len(m) == 1209, 'every one of the 1,209 APG-F67.4 files is byte-identical except README.md, RUN_COMMANDS.txt and the audit disposition '
            'register; no existing application code, tests, tools or specifications were modified', bad[:5] + same)


def r02():
    m = manifest()
    extra = [p for p in files() if p not in m]
    undeclared = [p for p in extra if not (p in ADDED_FILES or p.startswith(ADDED_PREFIXES))]
    missing = [p for p in ADDED_FILES if p not in extra]
    return not undeclared and not missing, 'every file beyond APG-F67.4 is a declared R1 addition (two R1 verification tools, the change record, regression and logs)', undeclared + missing


def r03():
    with tempfile.TemporaryDirectory() as td:
        for n in os.listdir(SNAP):
            shutil.copy(os.path.join(SNAP, n), td)
        r = subprocess.run([sys.executable, '-I', '-B', os.path.join(ROOT, 'tools', 'make_f674r1_registers.py'), td], capture_output=True, text=True)
        bad = [] if open(os.path.join(td, os.path.basename(DISP)), 'rb').read() == open(os.path.join(ROOT, DISP), 'rb').read() else ['the register is not what the tool makes']
    old, new = rows(os.path.join(SNAP, os.path.basename(DISP))), rows(os.path.join(ROOT, DISP))
    if new[:len(old)] != old or [(x['disposition_id'], x['finding_id']) for x in new[len(old):]] != NEW:
        bad.append('the register is not the F67.4 rows (AD-01 to AD-03) plus AD-04 to AD-08')
    return r.returncode == 0 and not bad, ('the audit disposition register is exactly what tools/make_f674r1_registers.py makes from the F67.4 register: AD-04 to AD-08 '
                                           'appended (F-75, F-74, F-73, F-72, F-67); AD-01 to AD-03 unchanged'), bad + ([r.stderr[-300:]] if r.returncode else [])


def r04():
    P = os.path.join(ROOT, 'programme')
    d = {r['disposition_id']: r for r in rows(os.path.join(ROOT, DISP))}
    f = {r['finding_id']: r['status'] for r in rows(os.path.join(P, 'FINDINGS_REGISTER.csv'))}
    cf = {r['cf_id']: r['status'] for r in rows(os.path.join(P, 'CARRIED_FORWARD_REGISTER.csv'))}
    edr = {r['edr_id']: r['status'] for r in rows(os.path.join(P, 'ENGINE_HANDOFF_REGISTER.csv'))}
    bad = []
    for i, fid in NEW:
        r = d[i]
        if not r['disposition'].startswith('Independently verified corrected in APG-F67.4') or r['release_audited'] != 'APG-F67.4':
            bad.append(i + ': not recorded as independently verified corrected in APG-F67.4')
        for need in ('finding-level disposition only', 'EDR-39', 'EDR-40', 'EDR-41', 'CF-41', 'M8 is not authorised', 'does not accept'):
            if need not in r['what_this_does_not_mean']:
                bad.append('%s: does not say %r' % (i, need))
        if 'timed out after group 3' not in r['what_is_not_independently_verified'] or 'no timeout was counted as a kill' not in r['what_is_not_independently_verified']:
            bad.append(i + ': the execution-limit qualifications are missing')
    if 'CF-41' not in d['AD-08']['disposition']:
        bad.append('AD-08 does not keep the F-67 authorisation-process issue')
    if f['F-67'] != 'Open - not corrected':
        bad.append('the F-67 findings row was edited')
    if cf['CF-41'] != 'Recorded - deviation, not ratified (product owner decision 2026-10-20)':
        bad.append('CF-41 changed')
    for k in ('CF-36', 'CF-37', 'CF-38', 'CF-39', 'CF-40', 'CF-42', 'CF-43', 'CF-44', 'CF-45'):
        if not cf[k].startswith('Open'):
            bad.append(k + ' is not open')
    for k in ('EDR-34', 'EDR-36', 'EDR-37', 'EDR-38', 'EDR-39', 'EDR-40', 'EDR-41'):
        if not edr[k].startswith('Open'):
            bad.append(k + ' is not open')
    return not bad, ('AD-04 to AD-08 record F-75 to F-72 and F-67 as independently verified corrected in APG-F67.4, each with the execution-limit qualifications and as a '
                     'finding-level disposition only; F-67 keeps CF-41; the findings rows are untouched; CF-36 to CF-45 (CF-41 as recorded) and EDR-34, EDR-36 to EDR-41 stay '
                     'open; M8 is not authorised'), bad


def r05():
    bad = []
    for p in ('README.md', 'programme/CHANGE_RECORD_APG-F67.4-R1.md'):
        text = open(os.path.join(ROOT, p), encoding='utf-8').read()
        if p == 'README.md':
            text = text.split('---- the APG-F67.4 readme follows')[0] if text.startswith('# APG F-67.4-R1') else ''
            if not text:
                bad.append('README.md does not start with the R1 section')
        for need in ('records-only', 'No existing application code, tests, tools or specifications were modified; two R1 verification tools were added.', 'M8',
                     'CF-41', 'finding-level', 'Authorise F-67.4-R1 records release'):
            if need not in text:
                bad.append('%s does not mention %r' % (p, need))
        bad += ['%s: %r' % (p, text[max(0, m.start() - 40):m.end() + 20]) for m in CLAIMS.finditer(text)]
    return not bad, 'the R1 text makes no acceptance, readiness, integration or ratification claim, keeps M8 unauthorised and uses the agreed wording', bad[:5]


def run(args, what, expect):
    try:
        r = subprocess.run([sys.executable, '-I'] + args, cwd=ROOT, capture_output=True, text=True, timeout=1800)
    except subprocess.TimeoutExpired:
        return False, what + ' (INCOMPLETE: cut off by the time limit)', []
    return r.returncode == 0 and expect in r.stdout + r.stderr, what, (r.stdout + r.stderr).strip().splitlines()[-1:]


STEPS = {'R01': r01, 'R02': r02, 'R03': r03, 'R04': r04, 'R05': r05,
         'R06': lambda: run(['tools/probe_f674.py'], 'the F-75 probe still reports every case corrected (the code is unchanged)', 'F-75 IS CORRECTED'),
         'R07': lambda: run(['tools/run_m2_tests.py', '-q', 'test_f674_type_strict.py'], 'the F-67.4 tests still pass (9)', 'tests 9  failures 0  errors 0')}


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
