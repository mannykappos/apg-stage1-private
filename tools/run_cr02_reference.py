#!/usr/bin/env python3
"""Reruns the CR-02 rev 2 reference tests and the 79 CR-02 mutants against the PACKAGED materiality model (apg/materiality.py).
Usage: python3 -I tools/run_cr02_reference.py       Exit 0 only if the tests pass and every mutant is killed or documented equivalent."""
import os, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ref = os.path.join(ROOT, 'reference', 'cr02')
tmp = tempfile.mkdtemp(prefix='cr02pkg_')
try:
    shutil.copy(os.path.join(ROOT, 'apg', 'materiality.py'), os.path.join(tmp, 'cr02_materiality_model.py'))
    for f in ('cr02_materiality_tests.py', 'cr02_materiality_mutants.py'):
        shutil.copy(os.path.join(ref, f), os.path.join(tmp, f))
    env = dict(os.environ, CR02_MUT_JOBS='4')
    t = subprocess.run([sys.executable, '-I', os.path.join(tmp, 'cr02_materiality_tests.py'), '--quiet'], capture_output=True, text=True, cwd=tmp)
    print(t.stdout.strip().splitlines()[-2] if t.stdout.strip() else t.stderr[-500:]); print(t.stdout.strip().splitlines()[-1] if t.stdout.strip() else '')
    m = subprocess.run([sys.executable, '-I', os.path.join(tmp, 'cr02_materiality_mutants.py')], capture_output=True, text=True, cwd=tmp, env=env)
    print('\n'.join(l for l in m.stdout.strip().splitlines() if l.startswith(('mutants', 'MUTATION', 'UNEXPLAINED', 'SURVIVED', 'EQUIVALENT'))))
    ok = t.returncode == 0 and 'ALL PASS' in t.stdout and m.returncode == 0 and 'MUTATION RUN OK' in m.stdout
    print('CR-02 REFERENCE RERUN OK' if ok else 'CR-02 REFERENCE RERUN FAILED')
    sys.exit(0 if ok else 1)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
