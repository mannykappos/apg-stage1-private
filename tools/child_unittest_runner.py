#!/usr/bin/env python3
"""APG-M11-S1, new (P1-F6; the D-1 row tools/child_unittest_runner.py): the successor replacement for the '-m unittest <module>' children
that M10 starts without -I (run_m8_tests.py:23, m8_mutants.py:148, sabotage_m10.py:55, run_regression_m10.py:137).  It is started by
evkit.child_cmd() with -I -S, sets sys.path[0] to the tree it lives in (so a mutant copy is reached by its own path, never by APG_ROOT),
runs the named test modules file by file against their pinned inventory, and prints kind=tests evidence (R1_REQUIREMENTS.md §2.7).
APG_AUIF_ROOT, the one environment exception (DP-1.3 (a)), is accepted only as a verified AUIF copy outside the tree (checked here,
and again by apg_auif.dependency.ensure), and only that copy may hold non-APG modules (the import check, §2.5).
Usage (from the package root):  python3 -I -S tools/child_unittest_runner.py --caller NAME --mode full|failfast [--run-id ID] module ...
  module: a dotted test module under tests/, tests_m8/ or tests_m10/ (for example tests_m8.test_m8_boundary).
Exit codes as §2.4.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import re
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

TOOL = 'child_unittest_runner'
MODULE = re.compile(r'^(tests|tests_m8|tests_m10)\.(test_[A-Za-z0-9_]+)$')


def main(argv):
    caller, mode, run_id, mods, errors = None, None, 'run', [], []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ('--caller', '--mode', '--run-id'):
            if i + 1 >= len(argv):
                errors.append(E.RunError('SELECTION_INVALID', 'missing value for %s' % a))
                break
            v = argv[i + 1]
            if a == '--caller':
                caller = v
            elif a == '--mode':
                mode = v
            else:
                run_id = v
            i += 1
        elif a.startswith('-'):
            errors.append(E.RunError('SELECTION_INVALID', 'unknown option %s' % a))
        else:
            mods.append(a)
        i += 1
    if mode not in ('full', 'failfast'):
        errors.append(E.RunError('SELECTION_INVALID', 'mode must be given as full or failfast'))
        mode = 'full'
    if not caller:
        errors.append(E.RunError('SELECTION_INVALID', 'caller must be given'))
    rel = []
    for m in mods:
        mm = MODULE.match(m)
        if not mm:
            errors.append(E.RunError('SELECTION_INVALID', 'not a test module: %s' % m))
            continue
        rel.append('%s/%s.py' % (mm.group(1), mm.group(2)))
    if not mods and not errors:
        errors.append(E.RunError('SELECTION_INVALID', 'no_modules'))
    allowed = ()
    try:
        auif = E.check_auif_root(os.environ.get('APG_AUIF_ROOT'))
        if auif:
            allowed = (auif,)
    except E.RunError as e:
        errors.append(e)
    return E.tests_runner_main(TOOL, None, {'relpaths': rel, 'mode': mode, 'caller': caller, 'run_id': run_id, 'errors': errors,
                                            'allowed_paths': allowed})


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
