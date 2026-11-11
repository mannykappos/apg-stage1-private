#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/run_test_files.py (P1-F6, T-F; DP-1.2 (B): tools/run_test_files.py stays byte-identical).  Runs the named
test files (exact file names in tests/, as M10) one at a time, test by test, against their pinned inventory, and prints kind=tests evidence
(R1_REQUIREMENTS.md §2.7): TEST and FILE lines, the M10 human line 'tests N  failures F  errors E', any RUN_ERROR lines and one RESULT v=2
line; mode=full (DP-2.3 F4).  M10 printed only the human line and exited 1 on zero tests; here a name that is not a pinned tests/ file,
a repeated name, or no name at all is a RUN_ERROR, exit 2, before any file runs.
Usage (from the package root):  python3 -I -S tools/run_test_files_s1.py [-q] [--caller NAME] [--run-id ID] test_a.py test_b.py ...
Exit codes as §2.4.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

TOOL = 'run_test_files_s1'


def main(argv):
    opts = {'caller': 'standalone', 'run_id': 'run'}
    names, errors = [], []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '-q':
            pass
        elif a in ('--caller', '--run-id'):
            if i + 1 >= len(argv):
                errors.append(E.RunError('SELECTION_INVALID', 'missing value for %s' % a))
                break
            opts['caller' if a == '--caller' else 'run_id'] = argv[i + 1]
            i += 1
        elif a.startswith('-'):
            errors.append(E.RunError('SELECTION_INVALID', 'unknown option %s' % a))
        else:
            names.append(a)
        i += 1
    if not names:
        errors.append(E.RunError('SELECTION_INVALID', 'no_files'))
    if len(set(names)) != len(names):
        errors.append(E.RunError('SELECTION_INVALID', 'duplicate'))
    try:
        pins, _ = E.load_pins()
    except E.RunError as e:
        errors.append(e)
        pins = {}
    rel = []
    for n in names:
        if os.path.basename(n) != n or not n.endswith('.py'):
            errors.append(E.RunError('SELECTION_INVALID', 'not a file name %s' % n))
        elif 'tests/' + n not in pins.get('test_files', {}):
            errors.append(E.RunError('TEST_FILE_NOT_IN_PINS', n))
        elif ('tests/' + n) not in rel:
            rel.append('tests/' + n)
    return E.tests_runner_main(TOOL, 'tests', {'relpaths': rel, 'mode': 'full', 'caller': opts['caller'], 'run_id': opts['run_id'],
                                               'errors': errors})


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
