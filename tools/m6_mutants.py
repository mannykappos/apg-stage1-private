#!/usr/bin/env python3
"""Mutation run over the M6 materials-and-market modules (apg/mkt/*, except the demonstration set-up, the golden oracle, the two port definitions, the reference test doubles, the faulty implementations and the contract suite, which are test inputs or have their own checks).  Each mutant is
  CMP  one comparison operator is flipped (== <-> !=, < <-> <=, > <-> >=, in <-> not in, is <-> is not)
  BOL  one 'and' becomes 'or' or the reverse
  NOT  one 'not' is removed
  RSE  one 'raise' statement is replaced by 'pass' (a guard removed)
  ARI  one '+' or '-' that has a whole-number constant as an operand is swapped (an off-by-one in an inclusive count, a window edge)
EVERY such site in the listed modules is a mutant (none is chosen or skipped).  The M6 unit tests, the faulty-input corpus and the golden cases are run against each mutant in ONE interpreter (tools/mut_runner.py), the test file most
likely to kill it first, the slow golden run last; a mutant is KILLED when any of them fails or hangs.  Usage: python3 -I tools/m6_mutants.py [--list] [--jobs N] [--only PREFIX] [--ids A,B] [--baseline] [--verbose]
Exit 0 only if every mutant is killed or is a documented equivalent.  The M5 detection modules are covered by tools/m5_mutants.py (the four M5 files changed in M6 - detect, findings, relations, portfolio - need their M5 run repeated, see the M6 documents), the M4 modules by tools/m4_mutants.py, the M3 modules by tools/m3_mutants.py and the M2 control
modules by tools/m2_mutants.py.  Single-site changes of these five kinds are all this run covers; it says nothing about other kinds of change, and it does not show the code is correct."""
import ast, os, queue, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
TARGETS = [('CM', 'common'), ('PL', 'policy'), ('FX', 'fx'), ('FR', 'fresh'), ('IN', 'intake'), ('GA', 'gather'), ('SP', 'spec'), ('LD', 'landed'), ('IT', 'intl'), ('CP', 'compare'), ('DM', 'demand'),
           ('SC', 'scenarios'), ('OP', 'opportunity'), ('PU', 'purchasing'), ('SU', 'suppliers'), ('EV', 'events'), ('AN', 'analysis'), ('RU', 'rules'), ('DT', 'detect')]
ALL_TESTS = ['test_mkt_policy.py', 'test_mkt_fx_fresh.py', 'test_mkt_intake.py', 'test_mkt_spec.py', 'test_mkt_landed.py', 'test_mkt_compare.py', 'test_mkt_demand.py', 'test_mkt_scenarios.py', 'test_mkt_opportunities.py',
             'test_mkt_rules.py', 'test_mkt_detect.py', 'test_mkt_edges_base.py', 'test_mkt_edges_policy.py', 'test_mkt_edges_landed.py', 'test_mkt_edges_demand.py', 'test_mkt_edges_rules.py', 'test_mkt_static.py', 'test_mkt_corpus.py', 'test_mkt_golden.py']
FIRST = {'common': 'test_mkt_policy.py', 'policy': 'test_mkt_policy.py', 'fx': 'test_mkt_fx_fresh.py', 'fresh': 'test_mkt_fx_fresh.py', 'intake': 'test_mkt_intake.py', 'gather': 'test_mkt_detect.py', 'spec': 'test_mkt_spec.py',
         'landed': 'test_mkt_landed.py', 'intl': 'test_mkt_rules.py', 'compare': 'test_mkt_compare.py', 'demand': 'test_mkt_demand.py', 'scenarios': 'test_mkt_scenarios.py', 'opportunity': 'test_mkt_opportunities.py',
         'purchasing': 'test_mkt_opportunities.py', 'suppliers': 'test_mkt_opportunities.py', 'events': 'test_mkt_rules.py', 'analysis': 'test_mkt_detect.py', 'rules': 'test_mkt_rules.py', 'detect': 'test_mkt_detect.py'}
CMP_FLIP = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.In: ast.NotIn, ast.NotIn: ast.In, ast.Is: ast.IsNot, ast.IsNot: ast.Is}
KINDS = ('CMP', 'BOL', 'NOT', 'RSE', 'ARI')

# Mutants that cannot change observable behaviour, or only change behaviour no caller can reach, with the reason.  Anything else that survives is a test gap.
EQUIV = {
    'FX-CMP-006': 'proved, not searched for: in fx.divergence_bps the guard `stated_aud <= 0` becomes `< 0`.  The two differ only at stated_aud == 0, where the mutant goes on to fmath.bps_of(reference_aud - 0, 0).  bps_of returns None for every denominator <= 0 (apg/fin/fmath.py, first line of its body), which is exactly what the guard returned.  Pinned by test_fin_arith (bps_of with 0 and a negative denominator), test_mkt_fx_fresh (divergence_bps(100, 0)) and test_mkt_edges_base (a stated conversion of zero or less).',
    'FX-CMP-012': 'proved, not searched for: in the choice of the latest stored rate `f[fx_date] > best[date]` becomes `>=`.  The two differ only when two usable rates for the same pair carry the same date.  The natural key of an fx_rate record is exactly `<fx_date>|<pair>` (ingest_templates/TPL-BZ-FX-RATES.json natural_key [fx_date, pair]; both fields are read from the same two columns), so the same pair and date is the same key: a second delivery is a revision or a conflict (a conflict is skipped before this line), never a second usable record.  Non-canonical dates are refused at intake (INVALID_DATE) and a differently written pair is a different pair that the pair test skips.  Pinned by test_mkt_edges_base (a stored rate is keyed by its own day and pair, so two never tie).',
    'LD-CMP-012': 'proved, not searched for: in landed.tiers `unit_rate_minor_units <= 0` becomes `< 0`.  A rate of zero or less never reaches that line: apg/mkt/intake.py lists unit_rate_minor_units as a positive field of quote_tier, and the M4 delivery loop it calls (apg/fin/intake.py) marks a value <= 0 pending with SIGN_CONVENTION:unit_rate_minor_units, so the record is not usable and simple_view returns ok=False and tiers() holds it before the line.  Pinned by test_mkt_landed (a tier with rate 0 is held as SIGN_CONVENTION) and test_mkt_edges_landed (tier minimums).',
    'LD-CMP-040': 'proved, not searched for: the sort key of the landed sources `(s[0], s[1] if s[1] is not None else -1)` becomes `... is None ...`.  Python compares the second element of two key tuples only when their first elements are equal, and every source is a (record reference, pinned revision) pair where F.rev gives one revision per reference for the whole run (apg/fin/snap.py Facts.rev reads the pins), the list is a set, and each tier, term and assumption is listed once.  So no two sources share a reference and the second element never decides the order.  Pinned by test_mkt_edges_landed (a source reference appears once per landed record).',
    'LD-CMP-042': 'proved, not searched for: in landed.purchase_plan the note test `alt[buy_qty_micro] > need_micro` becomes `>=`.  An alternative exists only when its tier start t[0] is strictly above base[buy_qty_micro] (the guard on the line above, whose mutant LD-CMP-008 is killed), the alternative buys at least t[0], and base[buy_qty_micro] = max(need, minimum order) rounded up to a pack size, which is at least need.  So alt buy > t[0]-1 >= base buy >= need: strictly greater, and `>=` gives the same answer.  Pinned by test_mkt_edges_landed (a larger tier always buys strictly more than the need).',
    'CP-CMP-039': 'proved, not searched for: in compare.last_paid `(po[date], k) > (best[date], best[key])` becomes `>=`.  The loop runs over sorted(ctx.pos.items()), so each k is visited once, and every order view carries key == the key it is listed under, so the tuple of the candidate can never equal the tuple of the current best (they differ in the second element).  `>` and `>=` therefore agree for every input.  Pinned by test_mkt_edges_landed (a purchase-order view carries the key it is listed under).',
    'SC-CMP-024': 'proved, not searched for: in scenarios.market_context `first[1] > 0` becomes `>= 0` in `bps_of(last - first, first) if first[1] > 0 else None`.  They differ only at first[1] == 0, where the mutant calls bps_of(x, 0), and bps_of returns None for every denominator <= 0 (apg/fin/fmath.py), the same as the else branch.  Pinned by test_fin_arith (bps_of with a zero denominator) and test_mkt_edges_landed (a first value of zero gives no percentage change).',
    'DM-CMP-011': 'proved, not searched for: in demand.coverage `over_all > 0` becomes `>= 0` in `over_all * 10000 > tol * need and over_all > 0`.  over_all is max(0, ...), so the two differ only at over_all == 0, where the first conjunct is `0 > tol * need`.  tol is demand.surplus_tolerance_bps, validated to 0..10000 (policy tests: test_mkt_edges_policy, basis-point bounds) and need is a quantity read by qty_micro, which refuses negatives, so tol * need >= 0 and `0 > tol * need` is false for every input: the second conjunct is redundant at 0.',
    'DM-CMP-013': 'proved, not searched for: the same reasoning as DM-CMP-011 for `over_deliv > 0` becoming `>= 0` in `delivered_material = over_deliv * 10000 > tol * need and over_deliv > 0`: over_deliv is max(0, ...), at 0 the first conjunct `0 > tol * need` is false because tol (0..10000, validated) and need (non-negative, qty_micro) give tol * need >= 0.',
    'OP-CMP-013': 'proved, not searched for: the sort key of an opportunity\'s sources `(s[0], s[1] if s[1] is not None else -1)` becomes `... is None ...`.  The same argument as LD-CMP-040: the sources are a set of (reference, pinned revision) pairs, one revision per reference in a run (Facts.rev reads the pins), landed sources, the requirement\'s sources and the reference\'s sources are joined and de-duplicated by the set, so no two entries share a reference and the second key element is never compared.  Pinned by test_mkt_edges_landed (a source reference appears once per landed record).',
    'PU-CMP-008': 'proved, not searched for: in purchasing.opportunities `lo[average_unit_cents] > 0` becomes `>= 0` in `bps_of(hi - lo, lo) if lo > 0 else None`.  They differ only at lo == 0, where the mutant calls bps_of(x, 0), which returns None (apg/fin/fmath.py: no ratio for a denominator <= 0), the same as the else branch.  Pinned by test_mkt_edges_demand (a project that paid a zero rate gives no ratio and no opportunity).',
    'PU-CMP-012': 'proved, not searched for: in purchasing.opportunities the estimate `sum(mul_div(r.average - lo.average, r.volume, MICRO) for r in rows if r.average > lo.average)` becomes `>=`.  lo is the minimum average, so a row that now also qualifies has average == lo and contributes mul_div(0, volume, MICRO) = round_div(0, MICRO) = 0.  The sum is unchanged for every input.  Pinned by test_mkt_edges_demand (projects paying the same average as the lowest add nothing).',
    'RU-BOL-028': 'proved, not searched for: in rules MP06 the condition for writing an fx_observed event `ref_conv[status] == converted and ref_conv[rate_source_ref]` becomes `or`.  MP06 skips home-currency quotes before this line, so fx.convert takes its foreign-currency path, where a found rate returns status converted with rate_source_ref = fx_rate/<key> (never empty) and a missing rate returns not_converted with rate_source_ref None.  The two operands are therefore always both true or both false (the only status/source split, none_same_currency, is unreachable here), and `and` and `or` give the same answer.  Pinned by test_mkt_edges_rules (a foreign conversion is converted with a source, or not converted with none).',
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
        src = open(os.path.join(ROOT, 'apg', 'mkt', mod + '.py'), encoding='utf-8').read()
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
    tmp = tempfile.mkdtemp(prefix='m6_mut_')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    pool = queue.Queue()
    for j in range(jobs):
        pool.put(make_work(tmp, f'w{j}'))
    try:
        if '--baseline' in sys.argv:                          # the unparsed, unmutated modules must pass everything, or the run proves nothing
            w = pool.get()
            for ab, mod in TARGETS:
                p = os.path.join(w, 'apg', 'mkt', mod + '.py')
                text = ast.unparse(ast.parse(open(p, encoding='utf-8').read())) + '\n'
                open(p, 'w', encoding='utf-8').write(text)
            res = run_tests(w, env, 'common')
            print('BASELINE', 'OK' if res is None else f'FAILED in {res}'); return 0 if res is None else 2

        def one(c):
            mid, mod, kind, idx = c
            w = pool.get()
            try:
                p = os.path.join(w, 'apg', 'mkt', mod + '.py')
                orig = open(os.path.join(ROOT, 'apg', 'mkt', mod + '.py'), encoding='utf-8').read()
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
