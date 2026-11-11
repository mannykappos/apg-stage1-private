#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_m2_tests.py (P1-F5, P1-F6; DP-1.2 (B): tools/run_m2_tests.py stays byte-identical, for historical
reproduction only).  Runs the tests/ unit, adversarial and regression files one at a time, test by test, against their pinned inventory
(tools/expected_counts.json), and prints kind=tests evidence (R1_REQUIREMENTS.md §2.7): TEST and FILE lines, the M10 human line
'tests N  failures F  errors E', any RUN_ERROR lines and one RESULT v=2 line.  APG_ROOT is never read (it is removed).
Usage (from the package root):  python3 -I -S tools/run_m2_tests_s1.py [-q] [--failfast] [--caller NAME] [--run-id ID] [pattern]
  --failfast  mode=failfast (a kill oracle inside a mutation or sabotage tool); otherwise mode=full.  The mode must equal the one pinned
              for this runner and caller (DP-2.3); --caller defaults to 'standalone'.
Exit codes as §2.4: 0 all passed, 1 test failures, 2 evidence or tool error, 3 indeterminate.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import fnmatch
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

TOOL = 'run_m2_tests_s1'


def parse(argv):
    opts = {'caller': 'standalone', 'run_id': 'run', 'failfast': False, 'pattern': None, 'errors': []}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '-q':
            pass
        elif a == '--failfast':
            opts['failfast'] = True
        elif a in ('--caller', '--run-id'):
            if i + 1 >= len(argv):
                opts['errors'].append(E.RunError('SELECTION_INVALID', 'missing value for %s' % a))
                break
            opts['caller' if a == '--caller' else 'run_id'] = argv[i + 1]
            i += 1
        elif a.startswith('-'):
            opts['errors'].append(E.RunError('SELECTION_INVALID', 'unknown option %s' % a))
        elif opts['pattern'] is None:
            opts['pattern'] = a
        else:
            opts['errors'].append(E.RunError('SELECTION_INVALID', 'more than one pattern'))
        i += 1
    return opts


def select(pattern, errors):
    """The files the pattern selects: the pinned tests/ files whose name matches, in sorted (recorded) order.  A file on disk that the
    pattern would load but the pins do not name is TEST_FILE_NOT_IN_PINS; a pattern that selects no pinned file is SELECTION_INVALID."""
    pattern = pattern or 'test_*.py'
    try:
        pins, _ = E.load_pins()
    except E.RunError as e:
        errors.append(e)
        return []
    pinned = sorted(k for k in pins.get('test_files', {}) if k.startswith('tests/') and fnmatch.fnmatch(os.path.basename(k), pattern))
    on_disk = sorted('tests/' + f for f in os.listdir(os.path.join(ROOT, 'tests')) if fnmatch.fnmatch(f, pattern) and f.endswith('.py')
                     and f.startswith('test'))
    for extra in sorted(set(on_disk) - set(pinned)):
        errors.append(E.RunError('TEST_FILE_NOT_IN_PINS', os.path.basename(extra)))
    if not pinned:
        errors.append(E.RunError('SELECTION_INVALID', 'no_file_matches'))
    return pinned


def main(argv):
    opts = parse(argv)
    errors = list(opts['errors'])
    rel = select(opts['pattern'], errors)
    return E.tests_runner_main(TOOL, 'tests', {'relpaths': rel, 'mode': 'failfast' if opts['failfast'] else 'full',
                                               'caller': opts['caller'], 'run_id': opts['run_id'], 'errors': errors})


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
