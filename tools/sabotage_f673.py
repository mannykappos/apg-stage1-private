#!/usr/bin/env python3
"""Package-level sabotage checks for APG-F67.3 (finding F-74 and its defect class): each corruption undoes one part of the correction, of the store contract, or of the release's
records, in a COPY of this package; the named step of tools/run_regression_f673.py must then FAIL.  A corruption the step does not notice is a gap.  Each case is short.
Usage: python3 -I tools/sabotage_f673.py [--list] [--only Sxx[,Syy]]   (from the package root; works in temporary folders; changes nothing here)"""
import os, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
PA = 'apg/policy_approval.py'
RP = 'apg/rec/policy.py'
LOOP = "        if r.revision != n or content(r.payload) != approved or any(e not in r.payload.get('approvals', []) for e in entries):"

# (id, what, file, old text, new text, the regression step that must fail)
CASES = [
    ('S01', 'holds no longer checks the approved content', PA, LOOP, "        if r.revision != n or any(e not in r.payload.get('approvals', []) for e in entries):", 'R06'),
    ('S02', 'holds no longer checks that the entry stays present and unchanged', PA, LOOP, "        if r.revision != n or content(r.payload) != approved:", 'R06'),
    ('S03', 'holds checks only the judged revision, not every revision in between', PA, "    for n, r in enumerate(hist[revision - 1:at], start=revision):",
     "    for n, r in enumerate(hist[at - 1:at], start=at):", 'R06'),
    ('S04', 'confirmed ignores the revision it is asked to judge at', PA, "and holds(scoped, kind, version, d.get('revision'), e.actor, at):",
     "and holds(scoped, kind, version, d.get('revision'), e.actor, None):", 'R07'),
    ('S05', 'confirmations judge a pinned reference at the latest revision', PA, "kind, key, at = (r.kind, r.key, r.revision) if hasattr(r, 'kind') else (r[0], r[1], None)",
     "kind, key, at = (r.kind, r.key, None) if hasattr(r, 'kind') else (r[0], r[1], None)", 'R07'),
    ('S06', 'the recommendation run judges at the latest revision, not the pinned one', 'apg/rec/engine.py', "RP.verified_approvers(scoped, pol, refs[0].revision)",
     "RP.verified_approvers(scoped, pol)", 'R11'),
    ('S07', 'confirmed checks only the binding again (the F-74 defect restored)', PA, "and holds(scoped, kind, version, d.get('revision'), e.actor, at):",
     "and added_at(scoped, kind, version, d.get('revision'), e.actor):", 'R06'),
    ('S08', 'the recommendation policy checks only the binding again', RP, "and PA.holds(scoped, POLICY_KIND, p['version'], (e.detail or {}).get('revision'), e.actor, at):",
     "and PA.added_at(scoped, POLICY_KIND, p['version'], (e.detail or {}).get('revision'), e.actor):", 'R06'),
    ('S09', 'the approved content includes the approvals, so another person\'s approval breaks it', PA, "    return {k: v for k, v in p.items() if k != 'approvals'}",
     "    return dict(p)", 'R06'),
    ('S10', 'holds accepts a judged revision before the confirmed one', PA, "or at < revision or at > len(hist):", "or at > len(hist):", 'R07'),
    ('S11', 'the reference store reads revision 0 as the latest', 'apg/reference_impl.py', "elif isinstance(revision, int) and not isinstance(revision, bool) and 1 <= revision <= len(h):",
     "elif isinstance(revision, int) and not isinstance(revision, bool) and revision <= len(h):", 'R12'),
    ('S12', 'the history contract loses its out-of-range case', 'apg/contracts/record_store_history_contract.py', "@hcase('RH-03',", "@(lambda *a: (lambda f: f))('RH-03',", 'R12'),
    ('S13', 'the detection gatherer passes bare keys again (judged at the latest)', 'apg/det/gather.py', "PA.confirmations(scoped, [pins[k] for k in sorted(pins)])",
     "PA.confirmations(scoped, sorted(pins))", 'R11'),
    ('S14', 'approve completes an entry it finds again (the F-73 defect restored)', PA, "        if mine:                                  # F-73",
     "        if mine:\n            _confirm(scoped, kind, version, rationale, err, label, cur.revision, replaced=0)\n            return canon.deep_copy(cur.payload)\n        if mine:  # F-73", 'R08'),
    ('S15', 'the F-74 row is changed to read verified', 'programme/FINDINGS_REGISTER.csv', 'Corrected in APG-F67.3 (builder-implemented); open until independently verified',
     'Corrected in APG-F67.3; independently verified', 'R03'),
    ('S16', 'the readme says M8 is authorised', 'README.md', 'M8 is not authorised', 'M8 is authorised', 'R05'),
    ('S17', 'an existing test file is edited', 'tests/test_f672_forged_entry.py', 'import unittest', 'import unittest  ', 'R10'),
    ('S18', 'an unchanged application file changes by one character', 'apg/fin/policy.py', "POLICY_KIND = 'fin_policy'", "POLICY_KIND = 'fin_policy' ", 'R01'),
    ('S19', 'an undeclared file is added', None, 'apg/extra_module.py', '"""an undeclared addition"""\n', 'R02'),
    ('S20', 'the stored F67.2 original of a changed file is edited', 'regression/f673/f672_originals/apg/policy_approval.py', 'def ', 'def  ', 'R02'),
]
SKIP_TOP = {'logs', 'research', 'gap_map', 'catalogue', 'reference'}


def copy(tmp):
    work = os.path.join(tmp, 'pkg')
    shutil.copytree(ROOT, work, ignore=lambda d, names: [n for n in names if n == '__pycache__' or (os.path.abspath(d) == ROOT and n in SKIP_TOP)])
    return work


def main():
    if '--list' in sys.argv:
        for c in CASES:
            print(c[0], c[1], '->', c[5])
        return 0
    only = set(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else None
    bad, n = [], 0
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for cid, what, path, old, new, step in CASES:
        if only and cid not in only:
            continue
        n += 1
        with tempfile.TemporaryDirectory(prefix='f673_sab_') as tmp:
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
            try:
                r = subprocess.run([sys.executable, '-I', 'tools/run_regression_f673.py', '--step', step], cwd=work, env=env, capture_output=True, text=True, timeout=1800)
                out = r.stdout
                caught = r.returncode != 0 and ('FAIL ' + step) in out
            except subprocess.TimeoutExpired:
                caught, out = False, 'INCOMPLETE: cut off by the time limit'
            print('%s %s %s -> %s %s' % ('CAUGHT' if caught else 'MISSED', cid, what, step, '' if caught else (out.strip().splitlines() or [''])[-1]), flush=True)
            if not caught:
                bad.append(cid)
    print('sabotage cases %d  missed %d%s' % (n, len(bad), ('  MISSED: %r' % bad) if bad else ''))
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
