#!/usr/bin/env python3
"""Regression checks of the records-only correction APG-F67.4-R2 against the delivered APG-F67.4-R1 package (ZIP SHA-256
33a149796293622398d0c1fae7fbf4d41b0dcb4649c4bae388f00cd737e9c407, 1,215 files; hashes in regression/f674r2/F674R1_MANIFEST.sha256, the two registers before R2 in
regression/f674r2/f674r1_snapshot/).  R2 appends AD-09 to AD-12 (superseding AD-05 to AD-08, wording only) and I-134 (the reading rule), and changes no code, test, tool,
specification, disposition or finding status.  Every step is short.
Usage: python3 -I tools/run_regression_f674r2.py --list | --all | --step Rnn      Exit 0 only if every step run passed."""
import csv, hashlib, os, re, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(ROOT, 'tools'))
G = os.path.join(ROOT, 'regression', 'f674r2')
MAN = os.path.join(G, 'F674R1_MANIFEST.sha256')
SNAP = os.path.join(G, 'f674r1_snapshot')
DISP, INT = 'programme/AUDIT_DISPOSITION_REGISTER.csv', 'programme/INTERPRETATIONS_REGISTER.csv'
CHANGED = {'README.md', 'RUN_COMMANDS.txt', DISP, INT}
ADDED_FILES = {'tools/make_f674r2_registers.py', 'tools/run_regression_f674r2.py', 'programme/CHANGE_RECORD_APG-F67.4-R2.md'}
ADDED_PREFIXES = ('regression/f674r2/', 'logs/f674r2/')
CORRECTED = 'No finding-specific qualification beyond the execution-limit qualifications recorded for the APG-F67.4 audit as a whole.'
PAIRS = (('AD-09', 'AD-05', 'F-74'), ('AD-10', 'AD-06', 'F-73'), ('AD-11', 'AD-07', 'F-72'), ('AD-12', 'AD-08', 'F-67'))
CLAIMS = re.compile(r'production[- ]ready|ready for (production|release|use)|release[- ]ready|\bcertified\b|\bguarantee[sd]?\b|100 ?%|fully (tested|verified|covered)|'
                    r'\b(APG-F67(\.[1-4])?(-R[12])?|this release|this package|the release) (is|was|has been) (accepted|approved|signed off)\b|M8 (is|was|has been) (authorised|started)|'
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
    return (not bad and not same and len(m) == 1215, 'every one of the 1,215 APG-F67.4-R1 files is byte-identical except README.md, RUN_COMMANDS.txt, the audit disposition '
            'register and the interpretations register; no code, test, tool or specification changed', bad[:5] + same)


def r02():
    m = manifest()
    extra = [p for p in files() if p not in m]
    undeclared = [p for p in extra if not (p in ADDED_FILES or p.startswith(ADDED_PREFIXES))]
    missing = [p for p in ADDED_FILES if p not in extra]
    return not undeclared and not missing, 'every file beyond APG-F67.4-R1 is a declared R2 addition (two R2 verification tools, the change record, regression and logs)', undeclared + missing


def r03():
    with tempfile.TemporaryDirectory() as td:
        for n in os.listdir(SNAP):
            shutil.copy(os.path.join(SNAP, n), td)
        r = subprocess.run([sys.executable, '-I', '-B', os.path.join(ROOT, 'tools', 'make_f674r2_registers.py'), td], capture_output=True, text=True)
        bad = [n for n in (DISP, INT) if open(os.path.join(td, os.path.basename(n)), 'rb').read() != open(os.path.join(ROOT, n), 'rb').read()]
    for n, ids in ((DISP, ['AD-09', 'AD-10', 'AD-11', 'AD-12']), (INT, ['I-134'])):
        old, new = rows(os.path.join(SNAP, os.path.basename(n))), rows(os.path.join(ROOT, n))
        if new[:len(old)] != old or [list(x.values())[0] for x in new[len(old):]] != ids:
            bad.append('%s is not the R1 rows plus %s' % (n, ids))
    return r.returncode == 0 and not bad, ('the two registers are exactly what tools/make_f674r2_registers.py makes from the R1 registers: AD-09 to AD-12 and I-134 appended; '
                                           'AD-01 to AD-08 and every other row unchanged'), bad + ([r.stderr[-300:]] if r.returncode else [])


def r04():
    import make_f674r1_registers as R1
    d = {r['disposition_id']: r for r in rows(os.path.join(ROOT, DISP))}
    P = os.path.join(ROOT, 'programme')
    f = {r['finding_id']: r['status'] for r in rows(os.path.join(P, 'FINDINGS_REGISTER.csv'))}
    cf = {r['cf_id']: r['status'] for r in rows(os.path.join(P, 'CARRIED_FORWARD_REGISTER.csv'))}
    edr = {r['edr_id']: r['status'] for r in rows(os.path.join(P, 'ENGINE_HANDOFF_REGISTER.csv'))}
    bad = []
    for new, old, fid in PAIRS:
        a, b = d[new], d[old]
        diff = sorted(k for k in a if a[k] != b[k])
        if diff != ['disposition_id', 'recorded_in', 'what_is_not_independently_verified']:
            bad.append('%s differs from %s in %s' % (new, old, diff))
        if a['finding_id'] != fid or a['what_is_not_independently_verified'] != CORRECTED + ' ' + R1.QUAL:
            bad.append(new + ': the corrected field is not the agreed sentence followed by the unchanged qualifications')
        if not b['what_is_not_independently_verified'].endswith(R1.QUAL):
            bad.append(old + ': the qualifications it carried are not the ones carried forward')
        if "The auditor's independent reruns" in a['what_is_not_independently_verified']:
            bad.append(new + ': the contradictory sentence is still there')
        if 'supersedes %s' % old not in a['recorded_in'] or not a['recorded_in'].startswith('APG-F67.4-R2'):
            bad.append(new + ': does not name the row it supersedes')
    latest = {}
    for r in rows(os.path.join(ROOT, DISP)):
        latest[r['finding_id']] = r['disposition_id']
    if [latest[k] for k in ('F-75', 'F-74', 'F-73', 'F-72', 'F-67')] != ['AD-04', 'AD-09', 'AD-10', 'AD-11', 'AD-12']:
        bad.append('the latest row per finding is not AD-04 (F-75) and AD-09 to AD-12')
    i134 = {r['interpretation_id']: r for r in rows(os.path.join(ROOT, INT))}.get('I-134', {})
    if "current disposition is its latest row" not in i134.get('builder_reading', ''):
        bad.append('I-134 does not record the reading rule')
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
    return not bad, ('AD-09 to AD-12 are identical to AD-05 to AD-08 except the corrected field (the agreed sentence followed by the unchanged qualifications), their id and '
                     'recorded_in, which names the row superseded; the latest row per finding is AD-04 and AD-09 to AD-12; I-134 records the reading rule; dispositions, '
                     'findings rows, CF-41 and every open gate are unchanged'), bad


def r05():
    bad = []
    for p in ('README.md', 'programme/CHANGE_RECORD_APG-F67.4-R2.md'):
        text = open(os.path.join(ROOT, p), encoding='utf-8').read()
        if p == 'README.md':
            text = text.split('---- the APG-F67.4-R1 readme follows')[0] if text.startswith('# APG F-67.4-R2') else ''
            if not text:
                bad.append('README.md does not start with the R2 section')
        for need in ('records-only', 'No existing application code, tests, tools or specifications were modified; two R2 verification tools were added.', 'M8', 'CF-41',
                     'supersede', 'Authorise F-67.4-R2 records correction'):
            if need not in text:
                bad.append('%s does not mention %r' % (p, need))
        bad += ['%s: %r' % (p, text[max(0, m.start() - 40):m.end() + 20]) for m in CLAIMS.finditer(text)]
    return not bad, 'the R2 text makes no acceptance, readiness, integration or ratification claim, keeps M8 unauthorised and uses the agreed wording', bad[:5]


STEPS = {'R01': r01, 'R02': r02, 'R03': r03, 'R04': r04, 'R05': r05}


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
