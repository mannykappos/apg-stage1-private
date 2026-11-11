#!/usr/bin/env python3
"""Package-level sabotage checks for APG-F67.2 (finding F-73): each corruption undoes one part of the correction, or of the release's records, in a COPY of this package; the
named step of tools/run_regression_f672.py must then FAIL.  A corruption the step does not notice is a gap.  Each case takes well under a minute.
Usage: python3 -I tools/sabotage_f672.py [--list] [--only Sxx[,Syy]]   (from the package root; works in temporary folders; changes nothing here)"""
import os, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
PA = 'apg/policy_approval.py'
RP = 'apg/rec/policy.py'
REMOVE = "            p['approvals'] = [a for a in p['approvals'] if a['approver'] != ctx.user_id]\n"

# (id, what, file, old text, new text, the regression step that must fail)
CASES = [
    ('S01', 'approve completes an entry it finds again (the F-73 defect restored)', PA, "        if mine:                                  # F-73",
     "        if mine:\n            _confirm(scoped, kind, version, rationale, err, label, cur.revision, replaced=0)\n            return canon.deep_copy(cur.payload)\n        if mine:  # F-73", 'R06'),
    ('S02', 'the entry found in the caller\'s name is kept next to the fresh one', PA, REMOVE, "            p['approvals'] = list(p['approvals'])\n", 'R07'),
    ('S03', 'the confirmation names the revision before approve wrote', PA, "_confirm(scoped, kind, version, rationale, err, label, rec.revision,",
     "_confirm(scoped, kind, version, rationale, err, label, cur.revision,", 'R06'),
    ('S04', 'confirmed no longer checks the revision binding', PA, " and added_at(scoped, kind, version, d.get('revision'), e.actor):", ":", 'R07'),
    ('S05', 'the binding accepts any revision that lists the entry, not only the one that added it', PA, "    return lists(at) and not lists(before)", "    return lists(at)", 'R07'),
    ('S06', 'the binding accepts a revision that is not a positive whole number', PA,
     "    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:\n        return False\n", "    if revision is None:\n        return False\n", 'R07'),
    ('S07', 'the recommendation policy completes an entry it finds again', RP, "        if mine:                                  # F-73",
     "        if mine:\n            _confirm(scoped, what, version, rationale, cur.revision, replaced=0)\n            return canon.deep_copy(cur.payload)\n        if mine:  # F-73", 'R06'),
    ('S08', 'the recommendation policy no longer checks the revision binding', RP,
     " \\\n                and PA.added_at(scoped, POLICY_KIND, p['version'], (e.detail or {}).get('revision'), e.actor):", ":", 'R07'),
    ('S09', 'the recommendation confirmation names the revision before approve wrote', RP, "_confirm(scoped, what, version, rationale, rec.revision,",
     "_confirm(scoped, what, version, rationale, cur.revision,", 'R06'),
    ('S10', 'a confirmed approver may approve again (double counting)', PA, "    if mine and ctx.user_id in confirmed(scoped, kind, version):\n        raise err(",
     "    if False:\n        raise err(", 'R08'),
    ('S11', 'an unconfirmed entry blocks its own owner again (the F-72 defect restored)', PA, "    if mine and ctx.user_id in confirmed(scoped, kind, version):\n        raise err(",
     "    if mine:\n        raise err(", 'R06'),
    ('S12', 'the confirmation no longer reports how many entries it replaced', PA, "rec.revision, replaced=len(mine))", "rec.revision, replaced=0)", 'R07'),
    ('S13', 'the F-73 row is changed to read verified', 'programme/FINDINGS_REGISTER.csv', 'Corrected in APG-F67.2 (builder-implemented); open until independently verified',
     'Corrected in APG-F67.2; independently verified', 'R03'),
    ('S14', 'the readme says M8 is authorised', 'README.md', 'M8 is not authorised', 'M8 is authorised', 'R05'),
    ('S15', 'a test is removed from the changed F-67.1 test file', 'tests/test_f671_approval_recovery.py', '    def test_', '    def _removed_', 'R10'),
    ('S16', 'another existing test file is edited', 'tests/test_f67_policy_approval.py', 'import copy, unittest', 'import copy, unittest  ', 'R10'),
    ('S17', 'an unchanged application file changes by one character', 'apg/fin/policy.py', "POLICY_KIND = 'fin_policy'", "POLICY_KIND = 'fin_policy' ", 'R01'),
    ('S18', 'an undeclared file is added', None, 'apg/extra_module.py', '"""an undeclared addition"""\n', 'R02'),
    ('S19', 'the stored F67.1 original of a changed file is edited', 'regression/f672/f671_originals/apg/policy_approval.py', 'def ', 'def  ', 'R02'),
    ('S20', 'approve keeps a completing path that returns early', PA, "    _confirm(scoped, kind, version, rationale, err, label, rec.revision, replaced=len(mine))\n",
     "    if mine:\n        return canon.deep_copy(cur.payload)\n    _confirm(scoped, kind, version, rationale, err, label, rec.revision, replaced=len(mine))\n", 'R11'),
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
        with tempfile.TemporaryDirectory(prefix='f672_sab_') as tmp:
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
                r = subprocess.run([sys.executable, '-I', 'tools/run_regression_f672.py', '--step', step], cwd=work, env=env, capture_output=True, text=True, timeout=1800)
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
