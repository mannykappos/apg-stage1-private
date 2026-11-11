#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/m2_mutants.py (P1-F5, P1-F7, E1-RI10; DP-1.2 (B): tools/m2_mutants.py stays byte-identical).
The mutants are M10's MUT list and EQUIV, loaded from tools/m2_mutants.py, with one change: RI10's target text, which does not occur in M10's
apg/reference_impl.py, is corrected as E1-RI10's proposed fix states (same id, same position, so the id list keeps its 199 ids):
    ('RI10-query-crosses-tenants', 'reference_impl.py', "if t == tenant and k == kind:", "if k == kind:")
Run and judged by tools/evkit.mutation_main: a pinned universe and site hashes, a preflight (each target exactly once, §2.1) before any
mutant, start and end controls, each mutant in its own fresh copy, the kill oracles run_m2_tests_s1 (mode=failfast, caller mutation_tool,
DP-2.3 F3) then run_contracts_s1 (kind=cases), as M10 runs run_m2_tests then run_contracts, a timeout or a crash never a kill (DP-2.1 (a)).
Usage (from the package root):  python3 -I -S tools/m2_mutants_s1.py [--list] [--jobs N] [--only PREFIX] [--ids A,B] [--run-id ID]
                                 python3 -I -S tools/m2_mutants_s1.py --pin --reason TEXT --cause TEXT
Exit codes as §2.4.  The M10 success marker 'MUTATION RUN OK' is printed only on exit 0.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

TOOL = 'm2_mutants_s1'
M = None   # moved into load() under evkit.import_guard (corrective pass 2, C.1)
RI10_M10 = ('RI10-query-crosses-tenants', 'reference_impl.py', "if t == ctx.tenant_id and k == kind:", "if k == kind:")
RI10_FIX = ('RI10-query-crosses-tenants', 'reference_impl.py', "if t == tenant and k == kind:", "if k == kind:")

def load():
    """C.1: the M10 load, and every module-level statement that uses it, after the start checks (evkit.guarded_load)."""
    global M
    with E.import_guard('m2_mutants'):
        M = E.load_tool_module('m2_mutants', ROOT)


def mut_list():
    out = []
    for m in M.MUT:
        if m[0] == RI10_M10[0]:
            assert tuple(m) == RI10_M10, 'M10 RI10 entry differs from the one E1-RI10 records'
            m = RI10_FIX
        out.append(m)
    return out


def mutants():
    return [E.Mutant(mid, 'apg/' + fname, old, (lambda src, old=old, new=new: src.replace(old, new, 1)), text_old=old)
            for mid, fname, old, new in mut_list()]


def commands(work, mutant):
    rid = mutant.id if mutant is not None else 'control'
    return [('run_m2_tests_s1', E.child_cmd(os.path.join(work, 'tools', 'run_m2_tests_s1.py'),
                                            ['-q', '--failfast', '--caller', 'mutation_tool', '--run-id', rid])),
            ('run_contracts_s1', E.child_cmd(os.path.join(work, 'tools', 'run_contracts_s1.py'), ['--run-id', rid]))]


if __name__ == '__main__':
    rc = E.guarded_load(TOOL, 'mutation', load)
    if rc is not None:
        sys.exit(rc)
    sys.exit(E.mutation_main(TOOL, mutants(), commands, sys.argv[1:], equivalents=M.EQUIV, timeout=300, success_marker='MUTATION RUN OK'))
