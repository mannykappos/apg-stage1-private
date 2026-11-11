#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/m8_mutants.py (E1-RI10, P1-F6, P7-B2, P7-B3; DP-1.2 (B): tools/m8_mutants.py stays byte-identical; it is a
Part A shared item, and this stage adds no Part B entry to it).  The mutants are M10's MUTANTS, unchanged, and its documented EQUIVALENT
list.  The tiers are M10's TIER1 without tests_m8/test_m8_boundary.py, and M10's TIER2 (decision M8-T, owner, 2026-10-31 20:57: under P7-B2
the tiers run inside the mutated copy, where the boundary test would flag every mutation as an undeclared file change; under M10 it ran
against the unmutated tree and none of the 213 recorded kills came from it; it stays in run_m8_tests_s1, in run_regression_m8_s1 step R09
and in sabotage_m8_s1 S06 to S08).  The tier lists are pinned with the mutant list (tools/expected_counts.json, oracle).
What changes (P7-B3 (R4); tools/evkit.mutation_main):
  - M10 ran the tests from this tree against the mutated copy through APG_ROOT (m8_mutants.py:148); P7-B2 removes that redirection, so each
    mutant gets its own fresh copy of the whole tree and its tiers run inside that copy;
  - each tier is tools/child_unittest_runner.py under the pinned caller profile child_unittest_runner@m8_tier (failfast, DP-2.3 F7), with
    the §2.8 environment and APG_AUIF_ROOT set to the AUIF copy this process verified (DP-1.3 (a)); tier 2 runs only if tier 1 passes, as
    in M10, and a mutant is KILLED by the first failing tier;
  - a timeout is INDETERMINATE (M10 exited 1 on it; §2.7 gives 3), a tier that crashes without a result is INDETERMINATE, never a kill
    (M10's run_tier counted any non-zero exit as FAIL), a failed control gives exit 3 with every mutant NOT_RUN (M10 exited 2), and there
    are start and end controls (M10 had one, at the start);
  - exact selection (--only and --ids take ids; M10's --batch K/N, with K outside 1..N, selected zero mutants and exited 0: not supported);
  - the AUIF copy is verified again after the run (AUIF_CHANGED_BY_RUN otherwise).
Usage (from the package root):  python3 -I -S tools/m8_mutants_s1.py [--list] [--only ID,ID] [--ids ID,ID] [--jobs N] [--run-id ID]
                                 python3 -I -S tools/m8_mutants_s1.py --pin --reason TEXT --cause TEXT
Exit codes as §2.4.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

TOOL = 'm8_mutants_s1'
M = TIERS = None   # moved into load() under evkit.import_guard (corrective pass 2, C.1)
OMITTED = 'test_m8_boundary'      # decision M8-T

def load():
    """C.1: the M10 load, and every module-level statement that uses it, after the start checks (evkit.guarded_load)."""
    global M, TIERS
    with E.import_guard('m8_mutants'):
        M = E.load_tool_module('m8_mutants', ROOT)
        TIERS = {'tier1': [t for t in M.TIER1 if t != OMITTED], 'tier2': list(M.TIER2)}


def mutants():
    return [E.Mutant(mid, f, old, (lambda src, old=old, new=new: src.replace(old, new)), text_old=old) for mid, f, old, new in M.MUTANTS]


def commands(work, mutant):
    rid = mutant.id if mutant is not None else 'control'
    tier = lambda name, mods: (name, E.child_cmd(os.path.join(work, 'tools', 'child_unittest_runner.py'),
                                                 ['--caller', 'm8_tier', '--mode', 'failfast', '--run-id', rid] + ['tests_m8.' + m for m in mods]))
    return [tier('tier1', TIERS['tier1']), tier('tier2', TIERS['tier2'])]


def main(argv):
    if M.TIER1.count(OMITTED) != 1 or OMITTED in M.TIER2:
        return E.refuse_run('mutation', TOOL, [m.id for m in mutants()],
                            E.RunError('EXPECTED_COUNT_MISMATCH', 'M10 TIER1 does not hold %s exactly once (decision M8-T)' % OMITTED))
    if '--batch' in argv:     # P7-B3 (R4): refused with its RUN_ERROR line and a RESULT v=2 line (every mutant NOT_RUN, exit 2)
        return E.refuse_run('mutation', TOOL, [m.id for m in mutants()], E.RunError('SELECTION_INVALID', '--batch is not supported; use --ids with exact ids'))
    argv = ['--ids' if a == '--only' else a for a in argv]
    if '--list' in argv or '--pin' in argv:
        return E.mutation_main(TOOL, mutants(), commands, argv, equivalents=M.EQUIVALENT, timeout=600, oracle=TIERS)
    from apg_auif import dependency
    saved_path = list(sys.path)
    derr = None
    with E.owning('run_start') as o_start:     # AM-5 (c): the AUIF verification's children are the run's start
        try:
            dep = dependency.ensure()
        except dependency.AuifDependencyError as e:
            derr = e
    if derr is not None:
        return E.refuse_run('mutation', TOOL, [m.id for m in mutants()], E.RunError('AUIF_DEPENDENCY_UNVERIFIED', str(derr)[:200].replace(' ', '_')))
    sys.path[:] = saved_path      # ensure() appends the AUIF copy to sys.path; this process imports nothing from it, and §2.8 checks sys.path
    # AM-5 (c): a leak at the run's start refuses the run (RUN_ERROR PROCESSES_LEFT run_start, every mutant NOT_RUN, exit 2)
    start_errors = [E.RunError('PROCESSES_LEFT', 'run_start')] if o_start.leaked else []

    def after():
        a = dependency.reverify(dep['root'])
        return [] if a['core_tree_sha256'] == dependency.CORE_TREE_SHA256 else [E.RunError('AUIF_CHANGED_BY_RUN', a['core_tree_sha256'])]
    return E.mutation_main(TOOL, mutants(), commands, argv, equivalents=M.EQUIVALENT, timeout=600, auif_root=dep['root'], after_check=after,
                           copy_ignore=E.FULL_TREE_IGNORE, oracle=TIERS, start_errors=start_errors)


if __name__ == '__main__':
    rc = E.guarded_load(TOOL, 'mutation', load)
    if rc is not None:
        sys.exit(rc)
    sys.exit(main(sys.argv[1:]))
