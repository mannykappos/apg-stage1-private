#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/mut_runner.py (P1-F5, P1-F6, E1-C8; DP-1.2 (B): tools/mut_runner.py stays byte-identical).
The kill oracle of the mutation tools: runs the named tests/ files in order inside one interpreter, stopping at the first failing file
(mode=failfast, DP-2.3 rows F1 and F2).  Unlike M10, which printed nothing on success and only the failing file's short name on failure
(E1-C8), it prints the full kind=tests evidence (R1_REQUIREMENTS.md §2.7): TEST and FILE lines (one per named file), the line
'FAIL <short name>' for the failing file (kept, so the first-failing-file attribution still works), RUN_ERROR lines and one RESULT v=2
line.  The files after the failing one are SKIPPED_AFTER_FAILURE.  Every name is checked against the pins before any file runs.
Usage (from the package root):  python3 -I -S tools/mut_runner_s1.py [--caller NAME] [--run-id ID] file1 file2 ...
Exit codes as §2.4.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

TOOL = 'mut_runner_s1'


def short(name):
    """M10's short name for the failing file (mut_runner.py:12)."""
    return name.replace('test_det_', '').replace('test_fin_', '').replace('.py', '')


def main(argv):
    caller, run_id, names, errors = 'standalone', 'run', [], []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ('--caller', '--run-id'):
            if i + 1 >= len(argv):
                errors.append(E.RunError('SELECTION_INVALID', 'missing value for %s' % a))
                break
            if a == '--caller':
                caller = argv[i + 1]
            else:
                run_id = argv[i + 1]
            i += 1
        elif a.startswith('-'):
            errors.append(E.RunError('SELECTION_INVALID', 'unknown option %s' % a))
        else:
            names.append(a)
        i += 1
    if not names and not errors:
        errors.append(E.RunError('SELECTION_INVALID', 'no_files'))
    rel = ['tests/' + n for n in names]
    return E.tests_runner_main(TOOL, 'tests', {'relpaths': rel, 'mode': 'failfast', 'caller': caller, 'run_id': run_id,
                                               'errors': errors}, name_map=short)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
