#!/usr/bin/env python3
"""Mutation run over the M4 financial-core modules (apg/fin/*, except the demonstration set-up, the golden cases and the corpus, which are test inputs).  Each mutant is a ONE-place change to a COPY of the package, made on the parsed source:
  CMP  one comparison operator is flipped (== <-> !=, < <-> <=, > <-> >=, in <-> not in, is <-> is not)
  BOL  one 'and' becomes 'or' or the reverse
  NOT  one 'not' is removed
  RSE  one 'raise' statement is replaced by 'pass' (a guard removed)
EVERY such site in the listed modules is a mutant (none is chosen or skipped).  The M4 unit tests, the faulty-input corpus and the golden cases are run against each mutant in ONE interpreter (tools/mut_runner.py), the test file most
likely to kill it first, the slow golden run last; a mutant is KILLED when any of them fails or hangs.  Usage: python3 -I tools/m4_mutants.py [--list] [--jobs N] [--only PREFIX] [--ids A,B] [--baseline] [--verbose]
Exit 0 only if every mutant is killed or is a documented equivalent.  The M3 modules are covered by tools/m3_mutants.py (unchanged) and the M2 control modules by tools/m2_mutants.py (unchanged)."""
import ast, os, queue, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
TARGETS = [('FG', 'figure'), ('FM', 'fmath'), ('PO', 'policy'), ('SN', 'snap'), ('GA', 'gather'), ('IN', 'intake'), ('CO', 'costs'), ('CM', 'commitments'), ('RV', 'revenue'), ('FC', 'forecast'),
           ('MG', 'margins'), ('CS', 'cash_states'), ('CV', 'cashview'), ('BR', 'bridge'), ('FB', 'forecast_book'), ('CR', 'calc_records')]
ALL_TESTS = ['test_fin_arith.py', 'test_fin_intake.py', 'test_fin_costs.py', 'test_fin_commitments.py', 'test_fin_revenue.py', 'test_fin_forecast.py', 'test_fin_cash.py', 'test_fin_bridge_book.py',
             'test_fin_records.py', 'test_fin_boundaries.py', 'test_fin_corpus.py', 'test_fin_golden.py']
FIRST = {'figure': 'test_fin_arith.py', 'fmath': 'test_fin_arith.py', 'policy': 'test_fin_arith.py', 'snap': 'test_fin_costs.py', 'gather': 'test_fin_records.py', 'intake': 'test_fin_intake.py',
         'costs': 'test_fin_costs.py', 'commitments': 'test_fin_commitments.py', 'revenue': 'test_fin_revenue.py', 'forecast': 'test_fin_forecast.py', 'margins': 'test_fin_forecast.py',
         'cash_states': 'test_fin_cash.py', 'cashview': 'test_fin_cash.py', 'bridge': 'test_fin_bridge_book.py', 'forecast_book': 'test_fin_bridge_book.py', 'calc_records': 'test_fin_records.py'}
CMP_FLIP = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.In: ast.NotIn, ast.NotIn: ast.In, ast.Is: ast.IsNot, ast.IsNot: ast.Is}
KINDS = ('CMP', 'BOL', 'NOT', 'RSE')

# Mutants that cannot change observable behaviour, or only change behaviour no caller can reach, with the reason.  Anything else that survives is a test gap.
EQUIV = {
    'FG-CMP-024': 'swaps which of the two values is checked for being a whole number in each pass of a loop that visits both; every value is still checked once, with the same message',
    'FM-CMP-006': 'only differs for n == 0, where -0 and 0 are the same integer',
    'PO-CMP-009': 'the branch body is `pass` (a documented "allowed" case): flipping its condition changes nothing',
    'PO-CMP-010': 'the branch body is `pass` (a documented "allowed" case): flipping its condition changes nothing',
    'PO-BOL-006': 'the branch body is `pass` (a documented "allowed" case): flipping its condition changes nothing',
    'IN-CMP-020': 'repeat deliveries of an already-held version are classified "duplicate" by the pipeline before this line is reached, so the guard here can never be false for a repeat (defence in depth)',
    'MG-BOL-001': 'a forecast that cannot be assessed never carries a forecast final cost, so "cannot assess OR no final cost" and "cannot assess AND no final cost" select the same cases',
    'MG-CMP-004': 'NO INPUT FOUND: a revenue of exactly zero cannot reach this line, because intake holds a zero or negative contract or variation amount (SIGN_CONVENTION) and a held amount is not counted',
    'CO-BOL-013': 'NO INPUT FOUND: a credit that reaches this line is, in every case tried (held credit, supplier mismatch, unresolved link), either in its invoice\'s credit list with the same key or in none; the case "another credit of the invoice is after the cut-off but this one is not listed" was not producible',
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
        src = open(os.path.join(ROOT, 'apg', 'fin', mod + '.py'), encoding='utf-8').read()
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
    tmp = tempfile.mkdtemp(prefix='m4_mut_')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    pool = queue.Queue()
    for j in range(jobs):
        pool.put(make_work(tmp, f'w{j}'))
    try:
        if '--baseline' in sys.argv:                          # the unparsed, unmutated modules must pass everything, or the run proves nothing
            w = pool.get()
            for ab, mod in TARGETS:
                p = os.path.join(w, 'apg', 'fin', mod + '.py')
                text = ast.unparse(ast.parse(open(p, encoding='utf-8').read())) + '\n'
                open(p, 'w', encoding='utf-8').write(text)
            res = run_tests(w, env, 'figure')
            print('BASELINE', 'OK' if res is None else f'FAILED in {res}'); return 0 if res is None else 2

        def one(c):
            mid, mod, kind, idx = c
            w = pool.get()
            try:
                p = os.path.join(w, 'apg', 'fin', mod + '.py')
                orig = open(os.path.join(ROOT, 'apg', 'fin', mod + '.py'), encoding='utf-8').read()
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
