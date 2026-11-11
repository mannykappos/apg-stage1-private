#!/usr/bin/env python3
"""Runs every check in this package. Python 3 standard library only; read-only (regenerates into temporary folders and compares).
Usage (from the package root):  python3 -I tools/run_all_checks.py        Exit 0 only if everything passes."""
import hashlib, os, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, 'tools')
py = lambda *a: subprocess.run([sys.executable, '-I', *a], capture_output=True, text=True, cwd=ROOT)
def files(base):
    out = {}
    for d, _, fs in os.walk(base):
        for f in fs:
            p = os.path.join(d, f); out[os.path.relpath(p, base)] = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    return out
ok = True
def report(name, r, ok_marker):
    global ok
    good = r.returncode == 0 and ok_marker in r.stdout
    last = [l for l in r.stdout.strip().splitlines() if l.startswith('checks ')]
    print(('PASS ' if good else 'FAIL ') + name + (' (' + last[0] + ')' if last else ''))
    if not good: ok = False; print(r.stdout[-1500:], r.stderr[-800:])
report('Builder Zero data', py(f'{T}/builder_zero_check.py', f'{ROOT}/builder_zero', '--rtm', f'{ROOT}/data/RTM_v2.1_CANDIDATE.csv'), 'ALL BUILDER ZERO CHECKS PASS')
report('Mapping templates', py(f'{T}/mapping_template_check.py', f'{ROOT}/import_templates', f'{ROOT}/builder_zero'), 'ALL MAPPING-TEMPLATE CHECKS PASS')
report('Programme, catalogue, translation drafts', py(f'{T}/programme_check.py', ROOT), 'ALL PROGRAMME CHECKS PASS')
# regeneration of shipped derived files
tmp = tempfile.mkdtemp()
os.makedirs(f'{tmp}/cat'); os.makedirs(f'{tmp}/prog'); os.makedirs(f'{tmp}/tpl')
r1 = py(f'{T}/merge_catalogue.py', f'{ROOT}/research', f'{tmp}/cat/CANDIDATE_SYSTEMS_CATALOGUE.csv')
r2 = py(f'{T}/make_m0.py', f'{tmp}/prog', f'{tmp}/cat')
r3 = py(f'{T}/make_templates.py', f'{tmp}/tpl')
same = (r1.returncode == r2.returncode == r3.returncode == 0)
for rel, shipped in [('cat/CANDIDATE_SYSTEMS_CATALOGUE.csv', 'catalogue/CANDIDATE_SYSTEMS_CATALOGUE.csv'), ('cat/TRANSLATION_PACK_DRAFTS.csv', 'catalogue/TRANSLATION_PACK_DRAFTS.csv'),
                     ('prog/PROGRAMME_MILESTONES.csv', 'programme/PROGRAMME_MILESTONES.csv'), ('prog/ENGINE_HANDOFF_REGISTER.csv', 'programme/ENGINE_HANDOFF_REGISTER.csv'), ('prog/STATUS_REGISTER.csv', 'programme/STATUS_REGISTER.csv')]:
    same = same and open(f'{tmp}/{rel}', 'rb').read() == open(f'{ROOT}/{shipped}', 'rb').read()
same = same and files(f'{tmp}/tpl') == files(f'{ROOT}/import_templates')
print(('PASS ' if same else 'FAIL ') + 'Derived files regenerate byte for byte from their inputs (catalogue, programme tables, translation drafts, templates)')
ok = ok and same
print('\nALL CHECKS PASS' if ok else '\nSOME CHECKS FAILED')
sys.exit(0 if ok else 1)
