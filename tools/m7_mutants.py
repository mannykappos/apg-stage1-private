#!/usr/bin/env python3
"""Mutation run over the M7 recommendation modules (as corrected in M7.1, M7.2 and M7.3) (apg/rec/engine.py, lifecycle.py, inputs.py, policy.py, verify.py; demo_rec.py holds demonstration values and golden_rec.py is the golden
driver, both exercised by the tests but not mutated).  Same method as tools/m91_mutants.py and tools/m5_mutants.py.  Each mutant is a ONE-place change to a COPY of the package, made on the parsed source:
  CMP  one comparison operator is flipped (== <-> !=, < <-> <=, > <-> >=, in <-> not in, is <-> is not)
  BOL  one 'and' becomes 'or' or the reverse
  NOT  one 'not' is removed
  RSE  one 'raise' statement is replaced by 'pass' (a guard removed)
  ARI  one '+' or '-' that has a whole-number constant as an operand is swapped
EVERY such site in the listed modules is a mutant (none is chosen or skipped).  The M7 tests are run against each mutant in ONE interpreter (tools/mut_runner.py), the test file most likely to kill
it first and the golden run last; a mutant is KILLED when any of them fails or hangs.  Usage: python3 -I tools/m7_mutants.py [--list] [--jobs N] [--only PREFIX] [--ids A,B] [--baseline] [--verbose]
Exit 0 only if every mutant is killed or is a documented equivalent."""
import ast, os, queue, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
TARGETS = [('EN', 'engine'), ('LC', 'lifecycle'), ('IN', 'inputs'), ('PO', 'policy'), ('VF', 'verify')]
ALL_TESTS = ['test_rec_policy.py', 'test_rec_eligibility.py', 'test_rec_ranking.py', 'test_rec_money.py', 'test_rec_constraints.py', 'test_rec_lifecycle.py', 'test_rec_verify.py',
             'test_rec_repro.py', 'test_rec_isolation.py', 'test_rec_edges.py', 'test_rec_m71_corrections.py', 'test_rec_m72_race.py', 'test_rec_m73_insert_race.py', 'test_rec_golden.py']
FIRST = {'engine': 'test_rec_eligibility.py', 'lifecycle': 'test_rec_lifecycle.py', 'inputs': 'test_rec_constraints.py', 'policy': 'test_rec_policy.py', 'verify': 'test_rec_verify.py'}
CMP_FLIP = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.In: ast.NotIn, ast.NotIn: ast.In, ast.Is: ast.IsNot, ast.IsNot: ast.Is}
KINDS = ('CMP', 'BOL', 'NOT', 'RSE', 'ARI')

# Mutants that cannot change observable behaviour, or only change behaviour no caller can reach, with the reason.  Anything else that survives is a test gap.
EQUIV = {
    'EN-ARI-002': 'proved: the first element of the confidence key is the strength index plus 1; minus 1 shifts every recommendation by the same amount (2), so every comparison between two keys is unchanged, and the value is never shown (the shown text is built separately).',
    'LC-BOL-017': 'proved: approve() is the entry point and transition() repeats the same whole-token check (F-57 style, killed as LC-BOL-026); with the entry check weakened a partial token reaches transition(), which refuses it with the same code APPROVAL_TOKEN_REQUIRED, the same message and the same audit entry, before anything is read or written.',
    'VF-BOL-013': 'proved unreachable: the message alternative is used only when the forecast replays cleanly (empty code) but the figure is invalid or the pins are inconsistent; the pins and the stored figure are covered by the record body and result hashes that the replay checks first, so a clean replay with an invalid figure or inconsistent pins cannot be stored through the M2 record rules.',
}


def _sites(tree):
    """-> {kind: [handle, ...]} in a fixed traversal order."""
    out = {k: [] for k in KINDS}
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare):
            for i, op in enumerate(n.ops):
                if type(op) in CMP_FLIP:
                    out['CMP'].append((n, i))
        elif isinstance(n, ast.BoolOp):
            out['BOL'].append(n)
        elif isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            out['NOT'].append(n)
        elif isinstance(n, ast.Raise):
            out['RSE'].append(n)
        elif isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub)) and any(isinstance(x, ast.Constant) and isinstance(x.value, int) and not isinstance(x.value, bool) for x in (n.left, n.right)):
            out['ARI'].append(n)
    return out


def _apply(tree, kind, idx):
    s = _sites(tree)[kind][idx]
    if kind == 'CMP':
        n, i = s
        n.ops[i] = CMP_FLIP[type(n.ops[i])]()
    elif kind == 'BOL':
        s.op = ast.Or() if isinstance(s.op, ast.And) else ast.And()
    elif kind == 'NOT':
        s.op = ast.UAdd()                                   # +x : the same operand without the negation (bool + is int(x); truthiness is unchanged, so replace below)
        s.__class__ = ast.UnaryOp
    elif kind == 'RSE':
        s.__class__ = ast.Pass
        s.__dict__.clear()
    elif kind == 'ARI':
        s.op = ast.Sub() if isinstance(s.op, ast.Add) else ast.Add()
    return tree


class _NotRemover(ast.NodeTransformer):
    def __init__(self, idx):
        self.idx, self.n, self.done = idx, -1, False

    def visit(self, node):
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            pass
        return super().visit(node)


def mutate(src, kind, idx):
    tree = ast.parse(src)
    if kind == 'NOT':
        nodes = [n for n in ast.walk(tree) if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not)]
        target = nodes[idx]
        parent = None
        for p in ast.walk(tree):
            for fld, val in ast.iter_fields(p):
                if val is target:
                    parent = (p, fld, None)
                elif isinstance(val, list) and any(v is target for v in val):
                    parent = (p, fld, [j for j, v in enumerate(val) if v is target][0])
        p, fld, j = parent
        if j is None:
            setattr(p, fld, target.operand)
        else:
            getattr(p, fld)[j] = target.operand
    elif kind == 'RSE':
        nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Raise)]
        target = nodes[idx]
        for p in ast.walk(tree):
            for fld, val in ast.iter_fields(p):
                if isinstance(val, list):
                    for j, v in enumerate(val):
                        if v is target:
                            val[j] = ast.Pass()
    else:
        _apply(tree, kind, idx)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + '\n'


def candidates():
    out = []
    for ab, mod in TARGETS:
        src = open(os.path.join(ROOT, 'apg', 'rec', mod + '.py'), encoding='utf-8').read()
        s = _sites(ast.parse(src))
        for kind in KINDS:
            for i in range(len(s[kind])):
                out.append((f'{ab}-{kind}-{i + 1:03d}', mod, kind, i))
    return out


def run_tests(work, env, mod):
    order = [FIRST[mod]] + [t for t in ALL_TESTS if t != FIRST[mod]]
    try:
        r = subprocess.run([sys.executable, '-I', 'tools/mut_runner.py'] + order, cwd=work, env=env, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return 'timeout'
    if r.returncode != 0:
        return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else 'crash'
    return None


def make_work(tmp, name):
    work = os.path.join(tmp, name)
    top = {'logs', 'dist', 'research', 'gap_map', 'catalogue', 'reference', 'data'}                     # top-level folders the tests never read
    shutil.copytree(ROOT, work, ignore=lambda d, names: [n for n in names if n in ('__pycache__', '.git') or (os.path.abspath(d) == ROOT and n in top)])
    return work


def main():
    cands = candidates()
    ids = [c[0] for c in cands]
    assert len(set(ids)) == len(ids)
    if '--list' in sys.argv:
        print('\n'.join(ids)); return 0
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
    if only:
        cands = [c for c in cands if c[0].startswith(only)]
    if '--ids' in sys.argv:                                    # re-run just these mutants (comma-separated ids)
        want = set(sys.argv[sys.argv.index('--ids') + 1].split(','))
        cands = [c for c in cands if c[0] in want]
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 2
    tmp = tempfile.mkdtemp(prefix='m7_mut_')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    pool = queue.Queue()
    for j in range(jobs):
        pool.put(make_work(tmp, f'w{j}'))
    try:
        if '--baseline' in sys.argv:                          # the unparsed, unmutated modules must pass everything, or the run proves nothing
            w = pool.get()
            for ab, mod in TARGETS:
                p = os.path.join(w, 'apg', 'rec', mod + '.py')
                text = ast.unparse(ast.parse(open(p, encoding='utf-8').read())) + '\n'
                open(p, 'w', encoding='utf-8').write(text)
            res = run_tests(w, env, 'engine')
            print('BASELINE', 'OK' if res is None else f'FAILED in {res}'); return 0 if res is None else 2

        def one(c):
            mid, mod, kind, idx = c
            w = pool.get()
            try:
                p = os.path.join(w, 'apg', 'rec', mod + '.py')
                orig = open(os.path.join(ROOT, 'apg', 'rec', mod + '.py'), encoding='utf-8').read()
                try:
                    new = mutate(orig, kind, idx)
                except Exception as e:
                    return mid, 'ERROR', repr(e)
                open(p, 'w', encoding='utf-8').write(new)
                res = run_tests(w, env, mod)
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
        if st[0] == 'ERROR' or mid == 'ERROR':
            print('ERROR', mid, st); return 2
        if st[0] == 'KILLED':
            killed += 1; by[st[1]] = by.get(st[1], 0) + 1
            if '--verbose' in sys.argv:
                print(f'KILLED     {mid}  (by {st[1]})')
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
