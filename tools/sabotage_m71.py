#!/usr/bin/env python3
"""Package-level sabotage checks for APG-M7.1 (the M7 cases, now judged by tools/run_regression_m71.py, plus four cases for the M7.1 corrections): each corruption is applied to a COPY of this package, and the named check must then FAIL.  A corruption that the check does not notice is a gap.
Usage: python3 -I tools/sabotage_m71.py [--list] [--only Sxx]   (from the package root; works in temporary folders; changes nothing here)"""
import os, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True

# (id, what, file, old text, new text, the regression step that must fail)
CASES = [
    ('S01', 'the submission gate is switched off', 'apg/rec/lifecycle.py', "        why = _submit_gate(r)\n        if why:\n            _refuse(scoped, rid, 'NOT_SUBMITTABLE'",
     "        why = _submit_gate(r)\n        if False:\n            _refuse(scoped, rid, 'NOT_SUBMITTABLE'", 'R09'),
    ('S02', 'the verification gate stops checking the offsetting costs', 'apg/rec/verify.py', '    if miss or bad:\n', '    if False:\n', 'R09'),
    ('S03', 'the ranking is reversed', 'apg/rec/engine.py', '    ranked.sort(key=key, reverse=True)', '    ranked.sort(key=key)', 'R09'),
    ('S04', 'every member of an overlap component is counted', 'apg/rec/engine.py', "            r['overlap']['counted_in_totals'] = r['rec_id'] in counted", "            r['overlap']['counted_in_totals'] = True", 'R09'),
    ('S05', 'execute stops refusing', 'apg/rec/lifecycle.py', "    raise RecError('NO_AUTONOMOUS_EXECUTION'", "    return None\n    raise RecError('NO_AUTONOMOUS_EXECUTION'", 'R10'),
    ('S06', 'an M9.4 application file changes by one character', 'apg/det/findings.py', "KIND = 'finding'", "KIND = 'finding' ", 'R01'),
    ('S07', 'an earlier status row is edited', 'programme/STATUS_REGISTER.csv', 'Local-tested', 'Accepted', 'R05'),
    ('S08', 'the golden file is edited', 'regression/m7/golden_rec.json', '"findings": 31', '"findings": 32', 'R11'),
    ('S09', 'RFC-01 is shown as approved', 'programme/RFC_REGISTER.csv', 'PROPOSED - not approved', 'APPROVED', 'R06'),
    ('S10', 'an undeclared file is added', None, 'apg/extra_module.py', '"""an undeclared addition"""\n', 'R02'),
    ('S11', 'a recommendation module reaches the operating system', 'apg/rec/engine.py', 'import datetime, hashlib, inspect', 'import datetime, hashlib, inspect, os', 'R08'),
    ('S12', 'an existing test is edited', 'tests/test_det_findings.py', 'import unittest', 'import unittest  ', 'R04'),
    ('S13', 'weak evidence stops routing to investigation', 'apg/rec/engine.py', "        elif not RP.strength_at_least(conf['evidence_strength'], need):", "        elif False:", 'R09'),
    ('S14', 'the approval stops checking the submission reference', 'apg/rec/lifecycle.py', "            if not submission_current(r) or approving_submission != submission_ref(r):",
     "            if not submission_current(r):", 'R09'),
    ('S15', 'a register row stops being what the register tool makes', 'programme/INTERPRETATIONS_REGISTER.csv', 'I-113,M7.1,An unapproved policy blocks submission', 'I-113,M7.1,An unapproved policy blocks submissions', 'R07'),
    ('S16', 'the source-freshness check is switched off (F-64, F-65)', 'apg/rec/lifecycle.py', "        if stale:\n", "        if False:\n", 'R10B'),
    ('S17', 'a policy may again be stored with caller-supplied approvals (F-66)', 'apg/rec/policy.py', "    if p['approvals']:\n        scoped.log('rec.refused'", "    if False:\n        scoped.log('rec.refused'", 'R10B'),
    ('S18', 'a run counts approvals the audit log does not confirm (F-66)', 'apg/rec/engine.py', "    approved = RP.is_approved(pol, set(verified) if isinstance(verified, list) else set())", "    approved = RP.is_approved(pol)", 'R09'),
    ('S19', 'an unchanged M7 module changes', 'apg/rec/inputs.py', "KIND = 'rec_input'", "KIND = 'rec_input' ", 'R01'),
]
SKIP_TOP = {'logs', 'research', 'gap_map', 'catalogue', 'reference', 'data'}


def copy(tmp):
    work = os.path.join(tmp, 'pkg')
    shutil.copytree(ROOT, work, ignore=lambda d, names: [n for n in names if n == '__pycache__' or (os.path.abspath(d) == ROOT and n in SKIP_TOP - {'data'})])
    return work


def main():
    if '--list' in sys.argv:
        for c in CASES:
            print(c[0], c[1], '->', c[5])
        return 0
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
    bad = []
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for cid, what, path, old, new, step in CASES:
        if only and cid != only:
            continue
        with tempfile.TemporaryDirectory(prefix='m71_sab_') as tmp:
            work = copy(tmp)
            if path is None:
                open(os.path.join(work, old), 'w', encoding='utf-8').write(new)
            else:
                p = os.path.join(work, path)
                text = open(p, encoding='utf-8').read()
                if text.count(old) < 1:
                    print('ERROR', cid, 'the text to corrupt is not in', path)
                    return 2
                open(p, 'w', encoding='utf-8').write(text.replace(old, new, 1))
            r = subprocess.run([sys.executable, '-I', 'tools/run_regression_m71.py', '--step', step], cwd=work, env=env, capture_output=True, text=True, timeout=1800)
            caught = r.returncode != 0 and ('FAIL ' + step) in r.stdout
            print('%s %s %s -> %s %s' % ('CAUGHT' if caught else 'MISSED', cid, what, step, '' if caught else (r.stdout.strip().splitlines() or [''])[-1]), flush=True)
            if not caught:
                bad.append(cid)
    print('sabotage cases %d  missed %d%s' % (len([c for c in CASES if not only or c[0] == only]), len(bad), ('  MISSED: %r' % bad) if bad else ''))
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
