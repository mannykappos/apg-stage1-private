#!/usr/bin/env python3
"""Regression checks of the records-only release APG-MIE-1.1-R1 against the delivered APG-MIE-1.1 package (ZIP SHA-256
0d2d158c47d5208dfbc3f19a2ad1a75ebed288e038e463241b841ea1de171b4b, 1,033 files; hashes in regression/mie1_1r1/MIE1_1_MANIFEST.sha256, tables in
regression/mie1_1r1/mie1_1_snapshot/).  R1 records the auditor's disposition of F-70 and F-71 and changes no code, test or tool of MIE-1.1.
Usage: python3 -I tools/run_regression_mie1_1r1.py --list | --all | --step Rnn      Exit 0 only if every step run passed."""
import csv, hashlib, os, re, subprocess, sys, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
MAN = os.path.join(ROOT, 'regression', 'mie1_1r1', 'MIE1_1_MANIFEST.sha256')
SNAP = os.path.join(ROOT, 'regression', 'mie1_1r1', 'mie1_1_snapshot')
CHANGED = {'README.md', 'RUN_COMMANDS.txt', 'programme/INTERPRETATIONS_REGISTER.csv'}
ADDED_FILES = {'programme/AUDIT_DISPOSITION_REGISTER.csv', 'programme/CHANGE_RECORD_APG-MIE1.1-R1.md', 'tools/make_mie1_1r1_registers.py', 'tools/run_regression_mie1_1r1.py'}
ADDED_PREFIXES = ('regression/mie1_1r1/', 'logs/mie1_1r1/')
CLAIMS = re.compile(r'production[- ]ready|ready for (production|release|use)|release[- ]ready|\bcertified\b|\bguarantee[sd]?\b|100 ?%|fully (tested|verified|covered)|'
                    r'\b(MIE-1\.1|MIE-1|this release|this package|the release) (is|was|has been) (accepted|approved|signed off)\b', re.I)
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
    return not bad and not same and len(m) == 1033, 'every one of the 1,033 MIE-1.1 files except README.md, RUN_COMMANDS.txt and the interpretations register is byte-identical; no code, test, tool or specification changed', bad[:5] + same


def r02():
    m = manifest()
    extra = [p for p in files() if p not in m]
    undeclared = [p for p in extra if not (p in ADDED_FILES or p.startswith(ADDED_PREFIXES))]
    missing = [p for p in ADDED_FILES if p not in extra]
    return not undeclared and not missing, 'every file beyond MIE-1.1 is a declared R1 addition (the disposition register, the change record, two tools, regression and logs)', undeclared + missing


def r03():
    with tempfile.TemporaryDirectory() as td:
        for n in os.listdir(SNAP):
            shutil.copy(os.path.join(SNAP, n), td)
        r = subprocess.run([sys.executable, '-I', '-B', os.path.join(ROOT, 'tools', 'make_mie1_1r1_registers.py'), td], capture_output=True, text=True)
        bad = [n for n in ('INTERPRETATIONS_REGISTER.csv', 'AUDIT_DISPOSITION_REGISTER.csv') if open(os.path.join(td, n), 'rb').read() != open(os.path.join(ROOT, 'programme', n), 'rb').read()]
    old, new = rows(os.path.join(SNAP, 'INTERPRETATIONS_REGISTER.csv')), rows(os.path.join(ROOT, 'programme', 'INTERPRETATIONS_REGISTER.csv'))
    if new[:len(old)] != old or [r['interpretation_id'] for r in new[len(old):]] != ['I-127']:
        bad.append('the interpretations register is not the MIE-1.1 rows plus I-127')
    if [r['disposition_id'] for r in rows(os.path.join(ROOT, 'programme', 'AUDIT_DISPOSITION_REGISTER.csv'))] != ['AD-01', 'AD-02']:
        bad.append('the disposition register is not exactly AD-01 and AD-02')
    return r.returncode == 0 and not bad, 'the tables are exactly what tools/make_mie1_1r1_registers.py makes from the MIE-1.1 tables: I-127 appended, and the disposition register holds AD-01 and AD-02 only', bad


def r04():
    P = os.path.join(ROOT, 'programme')
    d = {r['finding_id']: r for r in rows(os.path.join(P, 'AUDIT_DISPOSITION_REGISTER.csv'))}
    f = {r['finding_id']: r['status'] for r in rows(os.path.join(P, 'FINDINGS_REGISTER.csv'))}
    cf = {r['cf_id']: r['status'] for r in rows(os.path.join(P, 'CARRIED_FORWARD_REGISTER.csv'))}
    edr = {r['edr_id']: r['status'] for r in rows(os.path.join(P, 'ENGINE_HANDOFF_REGISTER.csv'))}
    bad = []
    if sorted(d) != ['F-70', 'F-71']:
        bad.append('a disposition is recorded for a finding other than F-70 and F-71')
    for k, r in d.items():
        if not r['disposition'].startswith('Independently verified corrected'):
            bad.append(k + ': not recorded as independently verified corrected')
        if 'builder-reported' not in r['what_is_not_independently_verified'] or '624' not in r['what_is_not_independently_verified']:
            bad.append(k + ': the full mutation run is not recorded as builder-reported')
        if 'does not accept the MIE-1.1 release' not in r['what_this_does_not_mean']:
            bad.append(k + ': the disposition does not say it is not a release acceptance')
        for g in ('EDR-36', 'EDR-37', 'EDR-38', 'BLK-01 to BLK-03', 'M9.4', 'DEV-MIE-01'):
            if g not in r['what_this_does_not_mean']:
                bad.append('%s: %s not kept open' % (k, g))
    for k in ('F-70', 'F-71'):
        if 'open until independently verified' not in f[k]:
            bad.append(k + ': the findings row was edited')
    for k in ('CF-36', 'CF-37', 'CF-38', 'CF-39'):
        if not cf[k].startswith('Open'):
            bad.append(k + ' is not open')
    for k in ('EDR-36', 'EDR-37', 'EDR-38'):
        if not edr[k].startswith('Open'):
            bad.append(k + ' is not open')
    return not bad, ('F-70 and F-71 are recorded as independently verified corrected with the audit scope; the full mutation run stays builder-reported; no release acceptance; '
                     'the findings rows are untouched; CF-36 to CF-39 and EDR-36 to EDR-38 stay open'), bad


def r05():
    bad = []
    for p in ('README.md', 'programme/CHANGE_RECORD_APG-MIE1.1-R1.md'):
        text = open(os.path.join(ROOT, p), encoding='utf-8').read()
        if p == 'README.md':
            text = text.split('---- the MIE-1.1 readme follows')[0] if text.startswith('# APG MIE-1.1-R1') else ''
            if not text:
                bad.append('README.md does not start with the R1 section')
        if 'builder-reported' not in text:
            bad.append(p + ' does not say the full mutation run is builder-reported')
        bad += ['%s: %r' % (p, text[max(0, m.start() - 40):m.end() + 20]) for m in CLAIMS.finditer(text)]
    return not bad, 'the R1 text makes no acceptance or readiness claim and keeps the mutation caveat', bad[:5]


def run(args, what, expect):
    r = subprocess.run([sys.executable, '-I'] + args, cwd=ROOT, capture_output=True, text=True, timeout=1800)
    return r.returncode == 0 and expect in r.stdout + r.stderr, what, (r.stdout + r.stderr).strip().splitlines()[-1:]


STEPS = {'R01': r01, 'R02': r02, 'R03': r03, 'R04': r04, 'R05': r05,
         'R06': lambda: run(['tools/probe_mie1_audit_findings.py'], 'the MIE-1 audit-findings probe still reports every case corrected', 'THE MIE-1 AUDIT FINDINGS ARE CORRECTED'),
         'R07': lambda: run(['tools/run_m2_tests.py', '-q', 'test_mie_*.py'], 'the MIE tests still pass (244)', 'tests 244  failures 0  errors 0')}


def main():
    a = sys.argv[1:]
    if not a or a[0] == '--list':
        print('steps:', ' '.join(STEPS))
        return 0
    want = list(STEPS) if a[0] == '--all' else [a[1]]
    for k in want:
        ok, what, detail = STEPS[k]()
        results.append((k, ok))
        print('%s %s %s %s' % ('PASS' if ok else 'FAIL', k, what, detail if not ok or detail else ''))
    failed = [k for k, ok in results if not ok]
    print('\nchecks %d  failed %d' % (len(results), len(failed)) + ('\nFAILED: %r' % failed if failed else ''))
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
