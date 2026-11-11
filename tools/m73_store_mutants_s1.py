#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/m73_store_mutants.py (P1-F7, P5-B06, P5-S07, P5-S08, E1-RI10; DP-1.2 (B): tools/m73_store_mutants.py stays byte-identical).
The mutants are M10's own, unchanged: every AST site of M10's two record-store guard regions (apg/reference_impl.py and apg/tenancy.py), with M7's five kinds.  They are loaded from M10's tool chain (tools/m73_store_mutants.py, which loads tools/m7_mutants.py), so the targets, the kinds, the traversal
order, the ids, the tests and the documented equivalents are M10's.  What changes is how they are run and judged (R1_REQUIREMENTS.md §2;
tools/evkit.mutation_main): a pinned universe and site hashes, a preflight before any mutant, start and end controls on the same unparse
round trip, each mutant in its own fresh copy, the kill oracle tools/mut_runner_s1.py (mode=failfast, caller mutation_tool, DP-2.3 F1) on
M10's test list in M10's order, a timeout or a crash never a kill (DP-2.1 (a)), and kind=mutation evidence with one RESULT v=3 line.
Usage (from the package root):  python3 -I -S tools/m73_store_mutants_s1.py [--list] [--jobs N] [--only PREFIX] [--ids A,B] [--run-id ID]
                                 python3 -I -S tools/m73_store_mutants_s1.py --baseline   (the start control only: decision W-1A.3 (a))
                                 python3 -I -S tools/m73_store_mutants_s1.py --pin --reason TEXT --cause TEXT
Exit codes as §2.4.  The M10 success marker 'MUTATION RUN OK' is printed only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

TOOL = 'm73_store_mutants_s1'
S = CANDIDATES = SITES = MUTATE = EQUIV = None   # moved into load() under evkit.import_guard (corrective pass 2, C.1)

def load():
    """C.1: the M10 load, and every module-level statement that uses it, after the start checks (evkit.guarded_load)."""
    global S, CANDIDATES, SITES, MUTATE, EQUIV
    with E.import_guard('m73_store_mutants'):
        S = E.load_tool_module('m73_store_mutants', ROOT)
        CANDIDATES, SITES, MUTATE, EQUIV = S.candidates, S.M._sites, S.M.mutate, S.EQUIV


def mutants():
    out = []
    srcs = {}
    for mid, x, kind, idx in CANDIDATES():
        rel = x
        if rel not in srcs:
            with open(os.path.join(ROOT, rel), encoding='utf-8') as fh:
                srcs[rel] = fh.read()
        out.append(E.Mutant(mid, rel, E.ast_site(srcs[rel], SITES, kind, idx),
                            (lambda src, kind=kind, idx=idx: MUTATE(src, kind, idx)), group=x))
    return out


def commands(work, mutant):
    order = list(S.TESTS)
    return [('mut_runner_s1', E.child_cmd(os.path.join(work, 'tools', 'mut_runner_s1.py'),
                                          ['--caller', 'mutation_tool', '--run-id', (mutant.id if mutant else 'control')] + order))]


def main(argv):
    ms, rc = E.list_mutants(TOOL, mutants)   # decision (c) (owner, 2026-11-02 14:24): a failed listing is a refusal, not a crash
    if rc is not None:
        return rc
    if '--batch' in sys.argv:   # M10's --batch K/N slices the universe inside candidates(); here --ids gives exact batches
        return E.refuse_run('mutation', TOOL, [m.id for m in ms], E.RunError('SELECTION_INVALID', '--batch is not supported; use --ids with exact ids'))
    targets = sorted({m.relpath for m in ms})
    return E.mutation_main(TOOL, ms, commands, argv, equivalents=EQUIV, baseline=E.unparse_baseline(targets), timeout=300,
                           success_marker='MUTATION RUN OK', baseline_option=True)   # --baseline: decision W-1A.3 (a)


if __name__ == '__main__':
    rc = E.guarded_load(TOOL, 'mutation', load)
    if rc is not None:
        sys.exit(rc)
    sys.exit(main(sys.argv[1:]))
