#!/usr/bin/env python3
"""Package-level sabotage checks for APG-F67.4 (finding F-75): each corruption undoes one part of the correction, of the per-file test runs, or of the release's records, in a COPY
of this package; the named step of tools/run_regression_f674.py must then FAIL.  A corruption the step does not notice is a gap.  Each case is short.
Usage: python3 -I tools/sabotage_f674.py [--list] [--only Sxx[,Syy]]   (from the package root; works in temporary folders; changes nothing here)"""
import os, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
PA = 'apg/policy_approval.py'
RP = 'apg/rec/policy.py'

# (id, what, file, old text, new text, the regression step that must fail)
CASES = [
    ('S01', 'holds compares the approved content with Python equality again (the F-75 defect restored)', PA,
     "fingerprint(content(r.payload)) != approved or", "content(r.payload) != content(base) or", 'R06'),
    ('S02', 'the re-store check compares with Python equality again', PA, "        if same(p, old) or (same(content(old), content(p)) and p['approvals'] == []):",
     "        if p == old or (content(old) == content(p) and p['approvals'] == []):", 'R06'),
    ('S03', 'the recommendation re-store check compares with Python equality again', RP,
     "        if not PA.same(p, old) and not (PA.same(PA.content(old), PA.content(p)) and p['approvals'] == []):",
     "        if p != old and not (PA.content(old) == PA.content(p) and p['approvals'] == []):", 'R06'),
    ('S04', 'the fingerprint folds booleans into numbers at the top level', PA, "    return canon.digest(x)\n",
     "    return canon.digest({k: int(v) if isinstance(v, bool) else v for k, v in x.items()} if isinstance(x, dict) else x)\n", 'R06'),
    ('S05', 'a value that cannot be fingerprinted counts as the same', PA, "    except canon.CanonError:\n        return False\n\n\ndef holds", "    except canon.CanonError:\n        return True\n\n\ndef holds", 'R07'),
    ('S06', 'content that cannot be fingerprinted holds', PA, "    except canon.CanonError:                                           # content written directly",
     "    except ZeroDivisionError:                                          # content written directly", 'R07'),
    ('S07', 'holds checks only the confirmed revision again (the F-74 defect restored)', PA, "    for n, r in enumerate(hist[revision - 1:at], start=revision):",
     "    for n, r in enumerate(hist[revision - 1:revision], start=revision):", 'R08'),
    ('S08', 'the F-75 row is changed to read verified', 'programme/FINDINGS_REGISTER.csv', 'Corrected in APG-F67.4 (builder-implemented); open until independently verified',
     'Corrected in APG-F67.4; independently verified', 'R03'),
    ('S09', 'the readme says M8 is authorised', 'README.md', 'M8 is not authorised', 'M8 is authorised', 'R05'),
    ('S10', 'an F-74 test is edited', 'tests/test_f673_approval_integrity.py', 'import unittest', 'import unittest  ', 'R10'),
    ('S11', 'an unchanged application file changes by one character', 'apg/fin/policy.py', "POLICY_KIND = 'fin_policy'", "POLICY_KIND = 'fin_policy' ", 'R01'),
    ('S12', 'an undeclared file is added', None, 'apg/extra_module.py', '"""an undeclared addition"""\n', 'R02'),
    ('S13', 'the stored F67.3 original of a changed file is edited', 'regression/f674/f673_originals/apg/policy_approval.py', 'def ', 'def  ', 'R02'),
    ('S14', 'a test file is dropped from the per-file list', 'tools/run_f674_all.py', "    ('test_values.py', 11)", "", 'R13'),
    ('S15', 'a per-file test count is wrong', 'tools/run_f674_all.py', "    ('test_values.py', 11)", "    ('test_values.py', 12)", 'R13'),
    ('S16', 'the history contract loses its out-of-range case', 'apg/contracts/record_store_history_contract.py', "@hcase('RH-03',", "@(lambda *a: (lambda f: f))('RH-03',", 'R12'),
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
        with tempfile.TemporaryDirectory(prefix='f674_sab_') as tmp:
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
                r = subprocess.run([sys.executable, '-I', 'tools/run_regression_f674.py', '--step', step], cwd=work, env=env, capture_output=True, text=True, timeout=1800)
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
