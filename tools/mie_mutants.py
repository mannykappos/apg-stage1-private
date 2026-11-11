#!/usr/bin/env python3
"""Mutation run over the MIE-1 core logic: mie/core/canon.py, values.py, pack.py, observations.py, signals.py, timing.py and engine.py.  vocab.py holds constants, ports.py holds
the port definitions (every one of its statements raises NotImplementedError or defines an exception) and reference.py holds the non-production reference ports (exercised by the
contract tests CT-03 to CT-13, not mutated).  Same method and kinds as tools/m7_mutants.py, whose functions are reused: each mutant is a ONE-place change to a COPY of the package
  CMP  one comparison operator flipped   BOL  one 'and' <-> 'or'   NOT  one 'not' removed   RSE  one 'raise' replaced by 'pass'   ARI  one '+'/'-' with a whole-number constant swapped
and EVERY such site in those modules is a mutant (none is chosen or skipped).  The MIE core tests (the thirteen synthetic-pack files) run against each mutant in one interpreter,
the file most likely to kill it first; a mutant is KILLED when any of them fails or hangs.  The construction tests are not in the loop (they take about 25 seconds and use APG data).
Usage: python3 -I tools/mie_mutants.py [--list] [--jobs N] [--only PREFIX] [--ids A,B] [--baseline]   Exit 0 only if every mutant is killed or is a documented equivalent."""
import ast, importlib.util, os, queue, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location('m7m', os.path.join(ROOT, 'tools', 'm7_mutants.py'))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
TARGETS = [('CA', 'canon'), ('VA', 'values'), ('PK', 'pack'), ('OB', 'observations'), ('SG', 'signals'), ('TM', 'timing'), ('EN', 'engine')]
ALL_TESTS = ['test_mie_core_pack.py', 'test_mie_core_observations.py', 'test_mie_core_signals.py', 'test_mie_core_timing.py', 'test_mie_core_replay.py',
             'test_mie_core_tenancy.py', 'test_mie_core_audit.py', 'test_mie_core_ports.py', 'test_mie_core_adversarial.py', 'test_mie_core_canon.py',
             'test_mie_core_boundaries.py', 'test_mie_flow.py', 'test_mie_portability.py']
FIRST = {'canon': 'test_mie_core_pack.py', 'values': 'test_mie_core_observations.py', 'pack': 'test_mie_core_pack.py', 'observations': 'test_mie_core_observations.py',
         'signals': 'test_mie_core_signals.py', 'timing': 'test_mie_core_timing.py', 'engine': 'test_mie_core_audit.py'}

# Mutants that cannot change observable behaviour, with the reason.  Anything else that survives is a test gap.
EQUIV = {
    'VA-CMP-010': 'proved: exact() with exponent 0 computes Fraction(m * 10 ** 0) on one branch and Fraction(m, 10 ** 0) on the other; both are Fraction(m), so moving the 0 case '
                  'from one branch to the other changes nothing.',
    'TM-CMP-028': 'proved: first is the smallest index whose rule is signal-influenced, so at i == first the rule is signal-influenced and the DIRECT branch above is taken '
                  'before this comparison is reached; i > first and i >= first therefore select the same rules.',
    'TM-RSE-001': 'proved unreachable: evaluate() already raises FailClosed for a fired rule whose outcome is outside the vocabulary of the intention, and every other decision '
                  'build() can receive is NOT_ASSESSED, which is in the vocabulary of both intentions; this second check can never see an outside outcome.',
}


def candidates():
    out = []
    for ab, mod in TARGETS:
        src = open(os.path.join(ROOT, 'mie', 'core', mod + '.py'), encoding='utf-8').read()
        s = M._sites(ast.parse(src))
        for kind in M.KINDS:
            for i in range(len(s[kind])):
                out.append(('%s-%s-%03d' % (ab, kind, i + 1), mod, kind, i))
    return out


def make_work(tmp, name):
    w = os.path.join(tmp, name)
    shutil.copytree(ROOT, w, ignore=shutil.ignore_patterns('__pycache__', 'logs', '*.zip', 'regression', 'builder_zero', 'data', 'catalogue', 'gap_map', '*_templates'))
    return w


def run_tests(work, env, mod):
    order = [FIRST[mod]] + [t for t in ALL_TESTS if t != FIRST[mod]]
    try:
        r = subprocess.run([sys.executable, '-I', 'tools/mut_runner.py'] + order, cwd=work, env=env, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return 'timeout'
    if r.returncode != 0:
        return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else 'crash'
    return None


def main():
    cands = candidates()
    if '--only' in sys.argv:
        pre = sys.argv[sys.argv.index('--only') + 1]
        cands = [c for c in cands if c[0].startswith(pre)]
    if '--ids' in sys.argv:
        want = set(sys.argv[sys.argv.index('--ids') + 1].split(','))
        cands = [c for c in cands if c[0] in want]
    if '--list' in sys.argv:
        print('\n'.join(c[0] for c in cands))
        print('mutants %d' % len(cands))
        return 0
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 2
    tmp = tempfile.mkdtemp(prefix='mie_mut_')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    pool = queue.Queue()
    for j in range(jobs):
        pool.put(make_work(tmp, 'w%d' % j))
    try:
        if '--baseline' in sys.argv:
            w = pool.get()
            for _, mod in TARGETS:
                p = os.path.join(w, 'mie', 'core', mod + '.py')
                text = ast.unparse(ast.parse(open(p, encoding='utf-8').read())) + '\n'          # read before the file is opened for writing
                open(p, 'w', encoding='utf-8').write(text)
            res = run_tests(w, env, 'engine')
            print('BASELINE', 'OK' if res is None else 'FAILED in %s' % res)
            return 0 if res is None else 2

        def one(c):
            mid, mod, kind, idx = c
            w = pool.get()
            try:
                p = os.path.join(w, 'mie', 'core', mod + '.py')
                orig = open(os.path.join(ROOT, 'mie', 'core', mod + '.py'), encoding='utf-8').read()
                try:
                    new = M.mutate(orig, kind, idx)
                except Exception as e:
                    return mid, ('ERROR', repr(e))
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
    killed = equiv = 0
    unexplained, by = [], {}
    for mid, st in results:
        if st[0] == 'ERROR':
            print('ERROR', mid, st)
            return 2
        if st[0] == 'KILLED':
            killed += 1
            by[st[1]] = by.get(st[1], 0) + 1
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
