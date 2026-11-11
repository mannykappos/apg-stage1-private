#!/usr/bin/env python3
"""Package-level sabotage checks for APG-F67 (finding F-67): each corruption undoes one part of the correction, or one part of the release's records, in a COPY of this package;
the named step of tools/run_regression_f67.py must then FAIL.  A corruption that the step does not notice is a gap.
Usage: python3 -I tools/sabotage_f67.py [--list] [--only Sxx[,Syy]]   (from the package root; works in temporary folders; changes nothing here)"""
import os, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
PA = 'apg/policy_approval.py'

# (id, what, file, old text, new text, the regression step that must fail)
CASES = [
    ('S01', 'a version may again be stored with caller-written approvals', PA, "    if p['approvals']:\n        _refuse(", "    if False:\n        _refuse(", 'R07'),
    ('S02', 'a version may name somebody else as its proposer', PA, "    if p['proposer'] != ctx.user_id:\n        _refuse(", "    if False:\n        _refuse(", 'R07'),
    ('S03', 'a service may propose a version', PA, "    if ctx.actor_kind != 'human':\n        _refuse(", "    if False:\n        _refuse(", 'R07'),
    ('S04', 'a stored version may be overwritten with an approval appended', PA, "        raise err('%s version %s already exists", "        return scoped.put(kind, p['version'], p, expected_revision=cur.revision)\n        raise err('%s version %s already exists", 'R07'),
    ('S05', 'the proposer may approve their own version', PA, "    if p['proposer'] == ctx.user_id:\n        _refuse(", "    if False:\n        _refuse(", 'R07'),
    ('S06', 'a person without the owner role may approve', PA, "if ctx.actor_kind != 'human' or role not in ctx.roles:", "if ctx.actor_kind != 'human':", 'R07'),
    ('S07', 'the confirmation no longer checks that the approver wrote the event', PA, " and d.get('approver') == e.actor:", ":", 'R07'),
    ('S08', 'the confirmation accepts an event written by a service', PA, "e.actor_kind == 'human' and ", "", 'R07'),
    ('S09', 'the confirmation accepts a refused event', PA, "e.outcome == 'ok' and ", "", 'R07'),
    ('S10', 'the confirmation accepts the event of another version', PA, "e.resource == res and ", "", 'R07'),
    ('S26', 'the confirmation no longer checks the version named in the event', PA, "and d.get('version') == version and ", "and ", 'R07'),
    ('S27', 'the confirmation no longer checks the record kind named in the event', PA, " and d.get('kind') == kind", "", 'R07'),
    ('S11', 'a run counts approvals the audit log does not confirm', PA, " and a['approver'] in ok for a in", " for a in", 'R06'),
    ('S12', 'the financial gatherer pins no confirmations', 'apg/fin/gather.py', "'approvals_confirmed': PA.confirmations(scoped, sorted(refs))", "'approvals_confirmed': {}", 'R07'),
    ('S13', 'the detection loader counts every stored approval as confirmed', 'apg/det/common.py', "DP.view(p, PA.pinned(F.params, DP.POLICY_KIND, ver))",
     "DP.view(p, [a['approver'] for a in p['approvals']])", 'R06'),
    ('S14', 'the specification loader counts every stored approval as confirmed', 'apg/mkt/common.py',
     "MP.spec_view(p, PA.pinned(F.params, MP.SPEC_KIND, ver))", "MP.spec_view(p, [a['approver'] for a in p['approvals']])", 'R06'),
    ('S15', 'the caller-asserted approve() is restored in the financial policy', 'apg/fin/policy.py', "def approve_policy(scoped, clock, version, rationale):",
     "def approve(p, approver, role, kind, date):\n    return dict(p, approvals=p['approvals'] + [{'approver': approver, 'role': role, 'kind': kind, 'date': date}])\n\n\n"
     "def approve_policy(scoped, clock, version, rationale):", 'R11'),
    ('S16', 'the demonstration policy again carries an approval', 'apg/fin/demo_fin.py', "    fields = dict(\n        recognition_method='cost_to_cost',",
     "    fields = dict(approvals=[{'approver': 'synthetic.policy_owner', 'role': 'policy_owner', 'kind': 'human', 'date': '2026-01-01'}],\n        recognition_method='cost_to_cost',", 'R09'),
    ('S17', 'the F-67 findings row is edited to read corrected', 'programme/FINDINGS_REGISTER.csv', 'Open - not corrected', 'Corrected', 'R01'),
    ('S18', 'AD-03 loses the timeout qualification', 'programme/AUDIT_DISPOSITION_REGISTER.csv', 'a 30-second per-mutant test timeout', 'the tool\'s per-mutant test timeout', 'R03'),
    ('S19', 'an R1 status row is edited', 'programme/STATUS_REGISTER.csv', 'SR-110,"The mutation run', 'SR-110,"The full mutation run', 'R03'),
    ('S20', 'the readme claims the correction is verified', 'README.md', 'open until', 'F-67 is verified; open until', 'R05'),
    ('S21', 'an undeclared file is added', None, 'apg/extra_module.py', '"""an undeclared addition"""\n', 'R02'),
    ('S22', 'an unchanged application file changes by one character', 'apg/rec/policy.py', "KIND = 'rec_policy'", "KIND = 'rec_policy' ", 'R01'),
    ('S23', 'a test is removed from an edited test file', 'tests/test_fin_records.py', '    def test_', '    def _removed_', 'R10'),
    ('S24', 'the stored R1 original of a changed file is edited', 'regression/f67/r1_originals/apg/fin/policy.py', 'def ', 'def  ', 'R02'),
    ('S25', 'the earlier F-66 correction is undone (the M7 probe must still catch it)', 'apg/rec/policy.py', "    if p['approvals']:\n        scoped.log('rec.refused'",
     "    if False:\n        scoped.log('rec.refused'", 'R08'),
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
        with tempfile.TemporaryDirectory(prefix='f67_sab_') as tmp:
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
                r = subprocess.run([sys.executable, '-I', 'tools/run_regression_f67.py', '--step', step], cwd=work, env=env, capture_output=True, text=True, timeout=3600)
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
