#!/usr/bin/env python3
"""APG-M11-S1 successor of tools/sabotage_m10.py (E1-RI10, P1-F6, P7-B3; decision K-1 K18: kind=sabotage; DP-1.2 (B): the M10 file stays
byte-identical).  The plants are M10's CASES (id, what, file, old, new, check), unchanged.  Their checks:
  - ('py', test id): the test's module run by tools/child_unittest_runner.py under the pinned caller profile child_unittest_runner@
    sabotage_tool (failfast, DP-2.3 F8), kind=tests.  A plant is CAUGHT only if that named test fails; if another test of the module fails
    first, the plant is INDETERMINATE (cause other_test_failed_first), never caught (M10 ran the one test);
  - ('ui', group): M10's ui_tests/run_ui_tests.js --only group under node, read by its own 'checks N  failed K' summary (F9).  The node
    binary is found on this process's PATH at start; the child environment stays the §2.8 allowlist (DP-1.3 (a)), so a check that needs
    more (Playwright's browser path) fails its control and its plants are not judged (exit 3), never caught.
Preflight exactly once (M10 also required exactly once, but per case, mid-run), start and end controls on the unbroken tree with every
selected plant's check (M10 had a start control per check only), exact selection, one RESULT v=2 kind=sabotage line.
Usage: python3 -I -S tools/sabotage_m10_s1.py [--list] [--only ID[,ID]] [--jobs N] [--run-id ID] | --pin --reason TEXT --cause TEXT
Exit codes as §2.4.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import shutil
import sys

sys.dont_write_bytecode = True
ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402

TOOL = 'sabotage_m10_s1'
M = E.load_tool_module('sabotage_m10', ROOT)
NODE = shutil.which('node') or 'node'


def label(check):
    return '%s:%s' % (check[0], check[1].split('.')[-1])


def named_test_judge(test_id):
    module = test_id.rsplit('.', 2)[0]
    fname = module.split('.')[-1] + '.py'

    def judge(stdout):
        lines = stdout.splitlines()
        if any(l in ('TEST %s::%s FAIL' % (fname, test_id), 'TEST %s::%s ERROR' % (fname, test_id)) for l in lines):
            return None
        return ('INDETERMINATE', 'other_test_failed_first')
    return judge


def plants():
    out = []
    for cid, what, f, old, new, check in M.CASES:
        p = E.text_plant(cid, what, f, old, new, label(check))
        p.m10_check = check
        if check[0] == 'py':
            p.judge = named_test_judge(check[1])
        out.append(p)
    return out


def cmd(work, check, run_id):
    if check[0] == 'py':
        module = check[1].rsplit('.', 2)[0]
        return (label(check), E.child_cmd(os.path.join(work, 'tools', 'child_unittest_runner.py'),
                                          ['--caller', 'sabotage_tool', '--mode', 'failfast', '--run-id', run_id, module]))
    return (label(check), [NODE, os.path.join(work, 'ui_tests', 'run_ui_tests.js'), '--only', check[1]], E.static_summary_classifier('checks'))


def commands(work, plant):
    return [cmd(work, plant.m10_check, plant.id)]


def control_commands(work, items):
    seen, out = [], []
    for p in items:
        if p.m10_check not in seen:
            seen.append(p.m10_check)
            out.append(cmd(work, p.m10_check, 'control'))
    return out


if __name__ == '__main__':
    argv = ['--ids' if a == '--only' else a for a in sys.argv[1:]]
    sys.exit(E.mutation_main(TOOL, plants(), commands, argv, timeout=1800, kind='sabotage', control_commands=control_commands))
