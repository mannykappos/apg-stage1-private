#!/usr/bin/env python3
"""Package-level sabotage checks for APG-F67.1 (finding F-72): each corruption undoes one part of the correction, or of the release's records, in a COPY of this package; the
named step of tools/run_regression_f671.py must then FAIL.  A corruption the step does not notice is a gap.  Each case takes well under a minute.
Usage: python3 -I tools/sabotage_f671.py [--list] [--only Sxx[,Syy]]   (from the package root; works in temporary folders; changes nothing here)"""
import os, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
PA = 'apg/policy_approval.py'
RP = 'apg/rec/policy.py'

# (id, what, file, old text, new text, the regression step that must fail)
CASES = [
    ('S01', 'a retry by the listed approver is refused again (the F-72 defect restored)', PA, "        if ctx.user_id in confirmed(scoped, kind, version):\n            raise err(",
     "        if True:\n            raise err(", 'R06'),
    ('S02', 'a retry writes a second confirming event even when one exists (double counting)', PA, "        if ctx.user_id in confirmed(scoped, kind, version):\n            raise err(",
     "        if False:\n            raise err(", 'R07'),
    ('S03', 'an entry in the approver\'s name that approve did not write can be completed', PA, "        if any(a['role'] != role or a['kind'] != 'human' for a in mine):",
     "        if False:", 'R07'),
    ('S04', 'a failed audit write is reported as success', PA, "        raise _not_confirmed(err)(", "        return\n        raise _not_confirmed(err)(", 'R06'),
    ('S05', 'a failed audit write surfaces as the raw exception again', PA, "    except Exception as e:\n        if _confirmed_after_error(", "    except ZeroDivisionError as e:\n        if _confirmed_after_error(", 'R06'),
    ('S06', 'the error is no longer an ApprovalNotConfirmed', PA, "_NC[err] = type(err.__name__ + 'NotConfirmed', (err, ApprovalNotConfirmed), {})",
     "_NC[err] = type(err.__name__ + 'NotConfirmed', (err,), {})", 'R07'),
    ('S07', 'after a failed write, the approval is treated as confirmed without reading the log', PA, "        return who in read()", "        return True", 'R06'),
    ('S08', 'a failed re-read of the log counts as confirmed (fail open)', PA, "    except Exception:\n        return False", "    except Exception:\n        return True", 'R07'),
    ('S09', 'the completing path rewrites the record (a new revision)', PA, "        return canon.deep_copy(cur.payload)\n    p['approvals']",
     "        scoped.put(kind, version, dict(p, approvals=[dict(a, date='2000-01-01') for a in p['approvals']]), expected_revision=cur.revision)\n        return canon.deep_copy(cur.payload)\n    p['approvals']", 'R07'),
    ('S10', 'the status reports a recorded approval as confirmed', PA, "'confirmed': [a for a in rec if a in ok], 'recorded_not_confirmed': [a for a in rec if a not in ok]}",
     "'confirmed': rec, 'recorded_not_confirmed': []}", 'R07'),
    ('S11', 'the recommendation policy refuses the retry again (F-72 restored there)', RP, "        if ctx.user_id in verified_approvers(scoped, p):\n            raise RecPolicyError(",
     "        if True:\n            raise RecPolicyError(", 'R06'),
    ('S12', 'the recommendation policy reports a failed audit write as success', RP, "        raise PA._not_confirmed(RecPolicyError)(", "        return\n        raise PA._not_confirmed(RecPolicyError)(", 'R06'),
    ('S13', 'the recommendation policy lets an entry approve did not write be completed', RP,
     "        if any(a['role'] != POLICY_ROLE or a['kind'] != 'human' for a in mine):", "        if False:", 'R07'),
    ('S14', 'the completing path no longer checks the approver\'s role', PA, "    if ctx.actor_kind != 'human' or role not in ctx.roles:\n        _refuse(scoped, kind, version, err, 'a %s is approved",
     "    if ctx.actor_kind != 'human':\n        _refuse(scoped, kind, version, err, 'a %s is approved", 'R07'),
    ('S15', 'the F-67 correction is undone (a version may be stored with caller approvals)', PA, "    if p['approvals']:\n        _refuse(", "    if False:\n        _refuse(", 'R08'),
    ('S16', 'CF-41 is changed to read ratified', 'programme/CARRIED_FORWARD_REGISTER.csv', 'Recorded - deviation, not ratified', 'Recorded - deviation, ratified', 'R03'),
    ('S17', 'the F-72 row is changed to read verified', 'programme/FINDINGS_REGISTER.csv', 'Corrected in APG-F67.1 (builder-implemented); open until independently verified',
     'Corrected in APG-F67.1; independently verified', 'R03'),
    ('S18', 'the readme says the original start was ratified', 'README.md', 'not ratified', 'ratified', 'R05'),
    ('S19', 'an existing test file is edited', 'tests/test_f67_policy_approval.py', 'import copy, unittest', 'import copy, unittest  ', 'R10'),
    ('S20', 'an unchanged application file changes by one character', 'apg/rec/engine.py', 'import datetime, hashlib, inspect', 'import datetime, hashlib, inspect ', 'R01'),
    ('S21', 'an undeclared file is added', None, 'apg/extra_module.py', '"""an undeclared addition"""\n', 'R02'),
    ('S22', 'the stored F67 original of a changed file is edited', 'regression/f671/f67_originals/apg/policy_approval.py', 'def ', 'def  ', 'R02'),
    ('S23', 'the confirming event is written directly again, bypassing _confirm', PA, "    _confirm(scoped, kind, version, rationale, err, label, completes=False)\n",
     "    scoped.log(event_type(kind), '%s/%s' % (kind, version), 'ok', detail={'kind': kind, 'version': version, 'approver': ctx.user_id})\n", 'R11'),
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
        with tempfile.TemporaryDirectory(prefix='f671_sab_') as tmp:
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
                r = subprocess.run([sys.executable, '-I', 'tools/run_regression_f671.py', '--step', step], cwd=work, env=env, capture_output=True, text=True, timeout=1800)
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
