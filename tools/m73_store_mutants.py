#!/usr/bin/env python3
"""Mutation run over the record-store code added in APG-M7.3: the guards of the reference store (apg/reference_impl.py, from InMemoryRecordStore._guard to the point in _atomic where
the writes are staged, which also covers the locked entry point) and the guard branch of the scoped store (apg/tenancy.py, ScopedStore.atomic).  The rest of those files is M2 code that
M7.3 did not change; it is covered by tools/run_contracts.py and tools/run_faults.py, which still pass.  Same method and kinds as tools/m7_mutants.py (whose functions are reused): EVERY site
in those regions is a mutant.  The tests run against each mutant: the M7.3 tests, the M7.2 race tests, the tenancy tests and the recommendation lifecycle tests.
Usage: python3 -I tools/m73_store_mutants.py [--list] [--jobs N] [--ids A,B] [--baseline]      Exit 0 only if every mutant is killed or is a documented equivalent."""
import ast, importlib.util, os, queue, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location('m7m', os.path.join(ROOT, 'tools', 'm7_mutants.py'))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
REGIONS = [('RI', 'apg/reference_impl.py', '    def _guard(self, t, g):', '        staged, plan = {}, []'),
           ('TE', 'apg/tenancy.py', '            if isinstance(op, Guard):', '                continue')]
TESTS = ['test_rec_m73_insert_race.py', 'test_rec_m72_race.py', 'test_tenancy.py', 'test_rec_lifecycle.py']
EQUIV = {}


def lines(src, start, end):
    a = src.index(start)
    b = src.index(end, a)
    return src.count('\n', 0, a) + 1, src.count('\n', 0, b) + 1


def candidates():
    out = []
    for ab, path, start, end in REGIONS:
        src = open(os.path.join(ROOT, path), encoding='utf-8').read()
        lo, hi = lines(src, start, end)
        s = M._sites(ast.parse(src))
        for kind in M.KINDS:
            n = 0
            for i, site in enumerate(s[kind]):
                node = site[0] if kind == 'CMP' else site
                if lo <= node.lineno <= hi:
                    n += 1
                    out.append((f'{ab}-{kind}-{n:03d}', path, kind, i))
    return out


def run_tests(work, env):
    try:
        r = subprocess.run([sys.executable, '-I', 'tools/mut_runner.py'] + TESTS, cwd=work, env=env, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return 'timeout'
    if r.returncode != 0:
        return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else 'crash'
    return None


def main():
    cands = candidates()
    if '--list' in sys.argv:
        print('\n'.join(c[0] for c in cands)); return 0
    if '--ids' in sys.argv:
        want = set(sys.argv[sys.argv.index('--ids') + 1].split(','))
        cands = [c for c in cands if c[0] in want]
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 2
    tmp = tempfile.mkdtemp(prefix='m73_mut_')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    pool = queue.Queue()
    for j in range(jobs):
        pool.put(M.make_work(tmp, f'w{j}'))
    try:
        if '--baseline' in sys.argv:
            w = pool.get()
            for _, path, _, _ in REGIONS:
                p = os.path.join(w, path)
                text = ast.unparse(ast.parse(open(p, encoding='utf-8').read())) + '\n'
                open(p, 'w', encoding='utf-8').write(text)
            res = run_tests(w, env)
            print('BASELINE', 'OK' if res is None else f'FAILED in {res}'); return 0 if res is None else 2

        def one(c):
            mid, path, kind, idx = c
            w = pool.get()
            try:
                p = os.path.join(w, path)
                orig = open(os.path.join(ROOT, path), encoding='utf-8').read()
                try:
                    new = M.mutate(orig, kind, idx)
                except Exception as e:
                    return mid, ('ERROR', repr(e))
                open(p, 'w', encoding='utf-8').write(new)
                res = run_tests(w, env)
                open(p, 'w', encoding='utf-8').write(orig)
                return mid, ('SURVIVED', '') if res is None else ('KILLED', res)
            finally:
                pool.put(w)
        with ThreadPoolExecutor(max_workers=jobs) as ex:
            results = list(ex.map(one, cands))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    killed = equiv = 0; unexplained = []; by = {}
    for mid, st in results:
        if st[0] == 'ERROR':
            print('ERROR', mid, st); return 2
        if st[0] == 'KILLED':
            killed += 1; by[st[1]] = by.get(st[1], 0) + 1
        elif EQUIV.get(mid):
            equiv += 1; print(f'EQUIVALENT {mid}  -- {EQUIV[mid]}')
        else:
            unexplained.append(mid); print(f'SURVIVED   {mid}', flush=True)
    print(f'mutants {len(cands)}  killed {killed} (first failing test file: {dict(sorted(by.items()))})  documented-equivalent {equiv}  unexplained survivors {len(unexplained)}')
    if unexplained:
        print('UNEXPLAINED:', unexplained); return 1
    print('MUTATION RUN OK'); return 0


if __name__ == '__main__':
    sys.exit(main())
