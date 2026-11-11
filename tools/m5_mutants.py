#!/usr/bin/env python3
"""Mutation run over the M5 detection-layer modules (apg/det/*, except the demonstration set-up, the golden cases, the corpus, the contract suite, the reference notifier and the faulty notifiers, which are test inputs or have their own checks).  Each mutant is a ONE-place change to a COPY of the package, made on the parsed source:
  CMP  one comparison operator is flipped (== <-> !=, < <-> <=, > <-> >=, in <-> not in, is <-> is not)
  BOL  one 'and' becomes 'or' or the reverse
  NOT  one 'not' is removed
  RSE  one 'raise' statement is replaced by 'pass' (a guard removed)
  ARI  one '+' or '-' that has a whole-number constant as an operand is swapped (an off-by-one in an inclusive count, a window edge)
EVERY such site in the listed modules is a mutant (none is chosen or skipped).  The M5 unit tests, the faulty-input corpus and the golden cases are run against each mutant in ONE interpreter (tools/mut_runner.py), the test file most
likely to kill it first, the slow golden run last; a mutant is KILLED when any of them fails or hangs.  Usage: python3 -I tools/m5_mutants.py [--list] [--jobs N] [--only PREFIX] [--ids A,B] [--baseline] [--verbose]
Exit 0 only if every mutant is killed or is a documented equivalent.  The M4 modules are covered by tools/m4_mutants.py (apg/fin/intake.py, the one M4 file changed in M5, is re-run there with --only IN), the M3 modules by tools/m3_mutants.py and the M2 control modules by tools/m2_mutants.py (unchanged)."""
import ast, os, queue, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
TARGETS = [('SG', 'signal'), ('CM', 'common'), ('PL', 'policy'), ('NZ', 'noise'), ('RC', 'rules_cost'), ('RM', 'rules_commercial'), ('RO', 'rules_ops'), ('GA', 'gather'), ('IN', 'intake'),
           ('DT', 'detect'), ('FN', 'findings'), ('RL', 'relations'), ('PF', 'portfolio'), ('MN', 'monitor')]
ALL_TESTS = ['test_det_signal.py', 'test_det_common.py', 'test_det_policy.py', 'test_det_policy_bounds.py', 'test_det_intake.py', 'test_det_detect.py', 'test_det_rules_cost.py', 'test_det_rules_cost_edges.py', 'test_det_run_edges.py', 'test_det_rules_commercial.py', 'test_det_rules_commercial_edges.py', 'test_det_rules_ops.py', 'test_det_rules_ops_edges.py', 'test_det_noise.py',
             'test_det_findings.py', 'test_det_findings_edges.py', 'test_det_approval_binding.py', 'test_det_proposal_binding.py', 'test_det_version_types.py', 'test_det_proposal_identity.py', 'test_det_transition_gate.py', 'test_det_portfolio.py', 'test_det_monitor.py', 'test_det_static.py', 'test_det_corpus.py', 'test_det_golden.py']
FIRST = {'signal': 'test_det_signal.py', 'common': 'test_det_common.py', 'policy': 'test_det_policy_bounds.py', 'noise': 'test_det_noise.py', 'rules_cost': 'test_det_rules_cost_edges.py',
         'rules_commercial': 'test_det_rules_commercial_edges.py', 'rules_ops': 'test_det_rules_ops_edges.py', 'gather': 'test_det_run_edges.py', 'intake': 'test_det_intake.py', 'detect': 'test_det_run_edges.py',
         'findings': 'test_det_proposal_binding.py', 'relations': 'test_det_findings_edges.py', 'portfolio': 'test_det_portfolio.py', 'monitor': 'test_det_findings_edges.py'}
CMP_FLIP = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.In: ast.NotIn, ast.NotIn: ast.In, ast.Is: ast.IsNot, ast.IsNot: ast.Is}
KINDS = ('CMP', 'BOL', 'NOT', 'RSE', 'ARI')

# Mutants that cannot change observable behaviour, or only change behaviour no caller can reach, with the reason.  Anything else that survives is a test gap.
EQUIV = {
    'NZ-CMP-010': 'proved, not searched for: severity_rank returns 0 for a label that is not in the bands and the 1-based position otherwise, so it is never negative; whenever rank(new) > rank(old) >= 0 it follows that rank(new) >= 1, so the second condition (rank(new) > 0 against >= 0) is already true and cannot change the result.',
    'RC-CMP-029': 'proved, not searched for: R03 tests `over <= 0 or not exceeds_bps(over, commit, tolerance)`.  With over == 0 the original takes the silent branch at once; the mutant (`over < 0`) goes on to exceeds_bps, which is `commit > 0 and 0 * 10000 > tolerance * commit`; the tolerance is a non-negative integer (the policy validator refuses a negative one: test_det_policy_bounds), so that is false and the mutant takes the same silent branch.  For over < 0 and over > 0 the two forms agree.  Same counters, same output.',
    'RC-CMP-032': 'proved, not searched for: in R09 `up = move > 0` is only reached after `abs(move) < movement_abs_cents` was false.  The policy validator requires movement_abs_cents >= 1 (test_det_policy_bounds), so abs(move) >= 1 and move is never 0 at that point; `move >= 0` and `move > 0` agree for every non-zero move.',
    'RM-CMP-028': 'proved, not searched for: in R04 a variation raised ON the as-of day has age 0.  The original goes on to `age <= unresolved_days`, which is true because the policy validator requires unresolved_days >= 0 (test_det_policy_bounds), and counts the variation silent; the mutant (`raised >= as_of`) counts it silent one line earlier.  Same counters, no signal either way.  A variation raised after the as-of day is silent in both and is tested.',
    'RO-CMP-049': 'proved, not searched for: LAB sets `impact_cents=est if est and est > 0 else None`.  The mutant changes `est > 0` to `est >= 0`.  The two differ only at est == 0, where `est and ...` has already short-circuited to 0, which is false, so both forms give None; for est None and for est < 0 both are also None, and for est > 0 both give est.',
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
        src = open(os.path.join(ROOT, 'apg', 'det', mod + '.py'), encoding='utf-8').read()
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
    tmp = tempfile.mkdtemp(prefix='m5_mut_')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    pool = queue.Queue()
    for j in range(jobs):
        pool.put(make_work(tmp, f'w{j}'))
    try:
        if '--baseline' in sys.argv:                          # the unparsed, unmutated modules must pass everything, or the run proves nothing
            w = pool.get()
            for ab, mod in TARGETS:
                p = os.path.join(w, 'apg', 'det', mod + '.py')
                text = ast.unparse(ast.parse(open(p, encoding='utf-8').read())) + '\n'
                open(p, 'w', encoding='utf-8').write(text)
            res = run_tests(w, env, 'signal')
            print('BASELINE', 'OK' if res is None else f'FAILED in {res}'); return 0 if res is None else 2

        def one(c):
            mid, mod, kind, idx = c
            w = pool.get()
            try:
                p = os.path.join(w, 'apg', 'det', mod + '.py')
                orig = open(os.path.join(ROOT, 'apg', 'det', mod + '.py'), encoding='utf-8').read()
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
