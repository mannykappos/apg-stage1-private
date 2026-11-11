#!/usr/bin/env python3
"""Mutation run over the APG-F67 correction (finding F-67).  It reuses the M7 mutation method unchanged (tools/m7_mutants.py: the same five kinds CMP, BOL, NOT, RSE, ARI,
made on the parsed source of a COPY of the package, every site a mutant, none chosen or skipped) over:
  PA  apg/policy_approval.py                        the whole module (new in APG-F67)
  FP  apg/fin/policy.py   } only the functions APG-F67 changed or added: new_policy, new_spec, is_approved, view, spec_view, store_policy, store_spec, approve_policy,
  DP  apg/det/policy.py   } approve_spec (the validation and parameter functions are unchanged M4 to M6 code, covered by the earlier mutation runs)
  MP  apg/mkt/policy.py   }
The tests that read these records are run against each mutant in ONE interpreter (tools/mut_runner.py), the F-67 correction tests first; a mutant is KILLED when any of them fails
or hangs.  Usage: python3 -I tools/f67_mutants.py [--list] [--jobs N] [--only PREFIX] [--ids A,B] [--baseline] [--verbose] [--timeout SECONDS]
Exit 0 only if every mutant is killed or is a documented equivalent."""
import ast, importlib.util, os, queue, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location('m7_mutants', os.path.join(ROOT, 'tools', 'm7_mutants.py'))
M7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M7)

CHANGED = ('new_policy', 'new_spec', 'is_approved', 'view', 'spec_view', 'store_policy', 'store_spec', 'approve_policy', 'approve_spec')
TARGETS = [('PA', 'apg/policy_approval.py', None), ('FP', 'apg/fin/policy.py', CHANGED), ('DP', 'apg/det/policy.py', CHANGED), ('MP', 'apg/mkt/policy.py', CHANGED)]
TESTS = ['test_f67_policy_approval.py', 'test_det_policy.py', 'test_mkt_policy.py', 'test_mkt_edges_policy.py', 'test_fin_arith.py', 'test_fin_records.py',
         'test_fin_boundaries.py', 'test_fin_golden.py', 'test_det_golden.py', 'test_mkt_golden.py']
EQUIV = {}
TIMEOUT = 300


def _line(handle):
    return (handle[0] if isinstance(handle, tuple) else handle).lineno


def candidates():
    out = []
    for ab, path, funcs in TARGETS:
        tree = ast.parse(open(os.path.join(ROOT, path), encoding='utf-8').read())
        spans = [(n.lineno, n.end_lineno) for n in tree.body if isinstance(n, ast.FunctionDef) and (funcs is None or n.name in funcs)]
        if funcs is not None:
            assert len(spans) == len([f for f in funcs if any(isinstance(n, ast.FunctionDef) and n.name == f for n in tree.body)]), path
        sites = M7._sites(tree)
        for kind in M7.KINDS:
            for i, h in enumerate(sites[kind]):
                if any(a <= _line(h) <= b for a, b in spans):
                    out.append(('%s-%s-%03d' % (ab, kind, len([c for c in out if c[0].startswith('%s-%s-' % (ab, kind))]) + 1), path, kind, i))
    return out


def run_tests(work, env):
    try:
        r = subprocess.run([sys.executable, '-I', 'tools/mut_runner.py'] + TESTS, cwd=work, env=env, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return 'timeout'
    if r.returncode != 0:
        return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else 'crash'
    return None


def main():
    global TIMEOUT
    if '--timeout' in sys.argv:
        TIMEOUT = int(sys.argv[sys.argv.index('--timeout') + 1])
    cands = candidates()
    ids = [c[0] for c in cands]
    assert len(set(ids)) == len(ids)
    if '--list' in sys.argv:
        print('\n'.join('%s  %s' % (c[0], c[1]) for c in cands))
        print('mutants %d' % len(cands))
        return 0
    if '--only' in sys.argv:
        cands = [c for c in cands if c[0].startswith(sys.argv[sys.argv.index('--only') + 1])]
    if '--ids' in sys.argv:
        want = set(sys.argv[sys.argv.index('--ids') + 1].split(','))
        cands = [c for c in cands if c[0] in want]
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 2
    tmp = tempfile.mkdtemp(prefix='f67_mut_')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    pool = queue.Queue()
    for j in range(jobs):
        pool.put(M7.make_work(tmp, 'w%d' % j))
    try:
        if '--baseline' in sys.argv:                          # the unparsed, unmutated modules must pass every test, or the run proves nothing
            w = pool.get()
            for ab, path, funcs in TARGETS:
                p = os.path.join(w, path)
                src = open(p, encoding='utf-8').read()
                text = ast.unparse(ast.parse(src)) + '\n'
                open(p, 'w', encoding='utf-8').write(text)
            res = run_tests(w, env)
            print('BASELINE', 'OK' if res is None else 'FAILED in %s' % res)
            return 0 if res is None else 2

        def one(c):
            mid, path, kind, idx = c
            w = pool.get()
            try:
                p = os.path.join(w, path)
                orig = open(os.path.join(ROOT, path), encoding='utf-8').read()
                try:
                    new = M7.mutate(orig, kind, idx)
                except Exception as e:
                    return mid, ('ERROR', repr(e))
                open(p, 'w', encoding='utf-8').write(new)
                try:
                    res = run_tests(w, env)
                finally:
                    open(p, 'w', encoding='utf-8').write(orig)
                return mid, ('SURVIVED', '') if res is None else ('KILLED', res)
            finally:
                pool.put(w)
        with ThreadPoolExecutor(max_workers=jobs) as ex:
            results = list(ex.map(one, cands))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    killed = equiv = 0
    unexplained, by = [], {}
    for mid, st in results:
        if st[0] == 'ERROR':
            print('ERROR', mid, st)
            return 2
        if st[0] == 'KILLED':
            killed += 1
            by[st[1]] = by.get(st[1], 0) + 1
            if '--verbose' in sys.argv:
                print('KILLED     %s  (by %s)' % (mid, st[1]), flush=True)
        elif EQUIV.get(mid):
            equiv += 1
            print('EQUIVALENT %s  -- %s' % (mid, EQUIV[mid]))
        else:
            unexplained.append(mid)
            print('SURVIVED   %s' % mid, flush=True)
    print('mutants %d  killed %d (first failing test file: %s)  documented-equivalent %d  unexplained survivors %d' % (len(cands), killed, dict(sorted(by.items())), equiv, len(unexplained)))
    if unexplained:
        print('UNEXPLAINED:', unexplained)
        return 1
    print('MUTATION RUN OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
