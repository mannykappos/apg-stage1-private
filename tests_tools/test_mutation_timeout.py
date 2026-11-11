"""Stage 1 (APG-M11-S1), Workstream T, P1-F7, P4-B13, P5-S08, AX-4 and T-0: the start and end controls (R1_REQUIREMENTS.md §2.3) and
the timeout measurement (§2.6).  Each control runs in its own fresh copy; a control that is not CONTROL_PASS stops the run before any
item; the end control never rescues a failed start control; a timeout stays INDETERMINATE whatever the measurement (DP-2.1 (a)).
Helper level (tools/evkit.control, fresh_copy, classify_timeout), and at tool level: every mutation tool, M10's and the successor's, with
its child replaced by a stub (ToolLevelTimeoutCrashKill, ToolLevelM8), and every sabotage tool (SabotageToolLevel).
Run from the package root:  python3 -I -S tests_tools/test_mutation_timeout.py      BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402


def ok_child_code():
    lines, _ = E.finish_items('cases', 'probe', 'r', ['S/c1'], {'S/c1': ('PASS', 'ok')}, suites_selected=1)
    return 'print(%r)' % '\n'.join(lines)


def failed_child_code():
    lines, _ = E.finish_items('cases', 'probe', 'r', ['S/c1'], {'S/c1': ('FAIL', 'x')}, suites_selected=1)
    return 'import sys\nprint(%r)\nsys.exit(1)' % '\n'.join(lines)


class Controls(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp(prefix='s1_ctl_')
        self.tree = tempfile.mkdtemp(prefix='s1_tree_')
        with open(os.path.join(self.tree, 'marker.txt'), 'w') as f:
            f.write('tree\n')
        self.env = E.clean_env(self.work)

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)
        shutil.rmtree(self.tree, ignore_errors=True)

    def cmds(self, *codes):
        return lambda dest: [('c%d' % i, [sys.executable, '-I', '-S', '-c', code]) for i, code in enumerate(codes)]

    def test_pass(self):
        value, lines, err = E.control(self.tree, self.work, 'start', self.cmds(ok_child_code(), ok_child_code()), self.env, 30)
        self.assertEqual((value, err), ('PASS', None))
        self.assertRegex(lines[0], r'^CONTROL start CONTROL_PASS cause=ok c0=\d+\.\d{3}s c1=\d+\.\d{3}s load=-?\d+\.\d\d free_disk_bytes=\d+$')
        self.assertEqual(os.listdir(self.work), [])  # the fresh copy is removed afterwards

    def test_each_control_runs_in_a_fresh_copy_of_the_tree(self):
        probe = 'import os\nassert os.path.exists("marker.txt")\nassert os.getcwd() != %r\n' % self.tree + ok_child_code()
        value, lines, err = E.control(self.tree, self.work, 'start', self.cmds(probe), self.env, 30)
        self.assertEqual(value, 'PASS', lines)

    def test_fail_and_timeout(self):
        value, lines, err = E.control(self.tree, self.work, 'start', self.cmds(failed_child_code()), self.env, 30)
        self.assertEqual(value, 'FAIL')
        self.assertIn('CONTROL_FAIL cause=CHILD_FAILED', lines[0])
        value, lines, err = E.control(self.tree, self.work, 'end', self.cmds('import time; time.sleep(5)'), self.env, 0.5)
        self.assertEqual(value, 'TIMEOUT')
        value, lines, err = E.control(self.tree, self.work, 'start', self.cmds('raise SystemExit(0)'), self.env, 30)
        self.assertEqual(value, 'FAIL')  # exit 0 with no RESULT line is a crash, not a pass
        self.assertIn('cause=CRASH_NO_RESULT', lines[0])

    def test_a_control_copy_that_cannot_be_made_is_a_tool_error(self):
        value, lines, err = E.control(os.path.join(self.tree, 'missing'), self.work, 'start', self.cmds(ok_child_code()), self.env, 30)
        self.assertEqual(value, 'FAIL')
        self.assertEqual(err.code, 'CONTROL_TOOL_ERROR')

    def test_the_disk_floor_is_checked_before_each_copy(self):
        with self.assertRaises(E.RunError) as c:
            E.fresh_copy(self.tree, os.path.join(self.work, 'x'), disk_floor_bytes=10 ** 18)
        self.assertEqual(c.exception.code, 'ENV_DISK_BELOW_FLOOR')

    def test_a_failed_start_control_stops_every_item_and_the_end_control(self):
        sel = ['M1', 'M2']
        lines, code = E.finish_items('mutation', 't', 'r', sel, {}, control_start='FAIL', not_run_cause='control_start_FAIL')
        f = E.parse_result_line(lines[-1])[1]
        self.assertEqual((f['started'], f['control_end'], code), (0, 'NOT_RUN', 3))


class TimeoutStaysIndeterminate(unittest.TestCase):
    def test_even_far_beyond_the_controls(self):
        times = {('start', 'run_m2_tests_s1'): 1.0, ('end', 'run_m2_tests_s1'): 1.0}
        (o, cause), line = E.classify_timeout('mutation', 'M1', 'run_m2_tests_s1', 300, times)
        self.assertEqual((o, cause), ('INDETERMINATE', 'timeout'))  # 300 s is 300 x the control: under DP-2.1 (a) still not a kill
        self.assertEqual(line, 'TIMEOUT M1 cmd=run_m2_tests_s1 limit=300s control_start=1.000s control_end=1.000s')

    def test_a_run_with_one_timeout_is_indeterminate_not_ok(self):
        sel = ['M1', 'M2']
        lines, code = E.finish_items('mutation', 't', 'r', sel, {'M1': ('KILLED', 'f'), 'M2': E.classify_timeout('mutation', 'M2', 'c', 1, {})[0]})
        self.assertEqual(code, 3)


def _run(tree, *args):
    import subprocess
    tmp = tempfile.mkdtemp(prefix='s1_bl_')
    try:
        p = subprocess.run([sys.executable, '-I', '-S'] + list(args), cwd=tree, capture_output=True, text=True, timeout=1800,
                           env={'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': tmp})
        return p.returncode, p.stdout, p.stderr
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


TIMEOUT_PROBE = """import os, sys
ROOT = os.path.realpath(os.getcwd())
sys.path.insert(0, ROOT)
import tools.evkit as E
T = E.load_tool_module('m73_store_mutants_s1', ROOT)
ms = T.mutants()
sleeper = lambda work, mutant: [('sleeper', [sys.executable, '-I', '-S', '-c', 'import time; time.sleep(30)'])]
sys.exit(E._baseline_only(T.TOOL, ms, sleeper, None, 2, ROOT, None, E.COPY_IGNORE, None))
"""


class BaselineOptionW1A(unittest.TestCase):
    """Decision W-1A.3 (a) (owner, 2026-11-01 06:22): --baseline in the nine successor mutation tools runs only the start control of the
    full run, executes no mutant, prints no RESULT line, prints BASELINE OK only on a pass, and exits 0 (pass), 1 (control failed),
    3 (control timed out) or 2 (tool error).  Each path is tested; m73_store_mutants_s1 is the smallest of the nine."""
    NINE = ('m7', 'm73_store', 'f67', 'f671', 'f672', 'f673', 'f674', 'mie', 'mie11')

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_baseline_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def copy(self, name):
        d = os.path.join(self.tmp, name)
        shutil.copytree(ROOT, d, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
        return d

    def assert_no_run(self, out):
        self.assertNotIn('RESULT ', out)
        self.assertNotRegex(out, r'(?m)^MUTANT ')

    def test_only_the_nine_tools_take_the_option(self):
        for t in self.NINE:
            with open(os.path.join(ROOT, 'tools', t + '_mutants_s1.py'), encoding='utf-8') as f:
                self.assertIn('baseline_option=True', f.read(), t)
        others = [f for f in os.listdir(os.path.join(ROOT, 'tools')) if f.endswith('_mutants_s1.py') and f[:-len('_mutants_s1.py')] not in self.NINE]
        self.assertTrue(others)
        for f in others:
            with open(os.path.join(ROOT, 'tools', f), encoding='utf-8') as fh:
                self.assertNotIn('baseline_option=True', fh.read(), f)
        code, out, err = _run(ROOT, 'tools/m3_mutants_s1.py', '--baseline')
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR SELECTION_INVALID unknown argument --baseline', out)

    def test_pass(self):
        code, out, err = _run(ROOT, 'tools/m73_store_mutants_s1.py', '--baseline')
        self.assertEqual(code, 0, out[-1500:] + err[-1500:])
        self.assertRegex(out, r'(?m)^CONTROL start CONTROL_PASS cause=ok ')
        self.assertEqual(out.strip().splitlines()[-1], 'BASELINE OK')
        self.assert_no_run(out)

    def test_control_failure(self):
        tree = self.copy('fail')
        T = E.load_tool_module('m73_store_mutants_s1', ROOT)
        target = sorted({m.relpath for m in T.mutants()})[0]
        with open(os.path.join(tree, target), 'a', encoding='utf-8') as f:
            f.write("\nraise RuntimeError('planted by test_mutation_timeout: the baseline control must fail')\n")
        code, out, err = _run(tree, 'tools/m73_store_mutants_s1.py', '--baseline')
        self.assertEqual(code, 1, out[-1500:] + err[-1500:])
        self.assertRegex(out, r'(?m)^CONTROL start CONTROL_FAIL ')
        self.assertNotIn('BASELINE OK', out)
        self.assertIn('BASELINE FAILED', out)
        self.assert_no_run(out)

    def test_timeout(self):
        tree = self.copy('timeout')
        code, out, err = _run(tree, '-c', TIMEOUT_PROBE)
        self.assertEqual(code, 3, out[-1500:] + err[-1500:])
        self.assertRegex(out, r'(?m)^CONTROL start CONTROL_TIMEOUT ')
        self.assertNotIn('BASELINE OK', out)
        self.assert_no_run(out)

    def test_tool_error(self):
        tree = self.copy('toolerr')
        import json
        p = os.path.join(tree, 'tools', 'expected_counts.json')
        doc = json.load(open(p))
        del doc['mutation_lists']['m73_store_mutants_s1']
        E.write_pins(doc, 'test: the tool is not pinned', 'tests_tools planted fault', [], path=p)
        code, out, err = _run(tree, 'tools/m73_store_mutants_s1.py', '--baseline')
        self.assertEqual(code, 2, out[-1500:] + err[-1500:])
        self.assertIn('RUN_ERROR MUTATION_LIST_NOT_PINNED m73_store_mutants_s1', out)
        self.assertNotIn('BASELINE OK', out)
        self.assertNotRegex(out, r'(?m)^CONTROL ')
        code, out, err = _run(ROOT, 'tools/m73_store_mutants_s1.py', '--baseline', '--ids', 'X')
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR SELECTION_INVALID --baseline takes no selection, --list or --pin', out)


# ---------------------------------------------------------------------------------------------------------------------------------------
# Tool level (P1-F7 (R4), AX-4, P2-B8 (R4), P3-B03 (R4), P4-B13, P5-S08): each mutation tool, M10's and its successor's, run on a temporary
# copy of this tree restricted to one mutant, with its child test command replaced in the copy by a stub.  The M10 tools are byte-identical
# in this tree (DP-1.2 (B)), so the copy runs M10's behaviour.  The stub, for a mutant (M10 never passes --run-id; the successor passes
# --run-id <mutant id>): (i) 'sleep' sleeps past the tool's timeout, patched in the copy to TIMEOUT_S seconds; (ii) 'crash' exits 139 with
# no output; (iii) 'evidence' exits 2 with a valid RESULT v=2 EVIDENCE_ERROR line (tests in test_consumer_exit_codes.py, P1-F5 (R4));
# (iv) 'failed' exits 1 with a valid FAILED line (a genuine kill).  The successor's controls (--run-id control) get a valid OK line, except
# in 'control_fail', where the start control gets a valid FAILED line.
# ---------------------------------------------------------------------------------------------------------------------------------------

import re as _re
import subprocess as _sp

TIMEOUT_S = 4
STUB_PIN = {'test_stub.py': {'sha256': '0' * 64, 'ids': ['tests.test_stub.T.test_a']}}


def _stub_text(state):
    if state == 'evidence':
        lines, code = E.finish_tests('stub_child', 'failfast', 'stub', [], {}, {})
    else:
        res = {'test_stub.py': E.FileResult('test_stub.py', 'COMPLETED', [('tests.test_stub.T.test_a', 'PASS' if state == 'ok' else 'FAIL')],
                                            '0' * 64)}
        lines, code = E.finish_tests('stub_child', 'failfast', 'stub', ['test_stub.py'], res, STUB_PIN)
    return '\n'.join(lines), code


STUB = r"""import sys, time
# planted by tests_tools/test_mutation_timeout.py: the child test command of a mutation tool, replaced in a temporary copy
MODE = %(mode)r
OK, FAILED, EVIDENCE = %(ok)r, %(failed)r, %(evidence)r
a = sys.argv[1:]
rid = a[a.index('--run-id') + 1] if '--run-id' in a else None
if rid is not None and rid.startswith('control'):
    if MODE == 'control_fail':
        print(FAILED); sys.exit(1)
    print(OK); sys.exit(0)
if MODE == 'sleep':
    time.sleep(%(sleep)d); print(OK); sys.exit(0)
if MODE == 'crash':
    sys.exit(139)
if MODE == 'evidence':
    print(EVIDENCE); sys.exit(2)
if MODE in ('failed', 'control_fail'):
    print(FAILED); sys.exit(1)
print(OK); sys.exit(0)
"""

# tool: (M10 child files, successor child files, M10 timeout text or None when --timeout is used, successor timeout text)
MUT_TOOLS = {
    'm2': (['run_m2_tests.py', 'run_contracts.py'], ['run_m2_tests_s1.py', 'run_contracts_s1.py'], ('m2_mutants.py', 'timeout=300)'), 'timeout=300,'),
    'm3': (['run_m2_tests.py'], ['run_m2_tests_s1.py'], ('m3_mutants.py', 'timeout=240)'), 'timeout=240,'),
    'm4': (['mut_runner.py'], ['mut_runner_s1.py'], ('m4_mutants.py', 'timeout=300)'), 'timeout=300,'),
    'm5': (['mut_runner.py'], ['mut_runner_s1.py'], ('m5_mutants.py', 'timeout=300)'), 'timeout=300,'),
    'm6': (['mut_runner.py'], ['mut_runner_s1.py'], ('m6_mutants.py', 'timeout=300)'), 'timeout=300,'),
    'm7': (['mut_runner.py'], ['mut_runner_s1.py'], ('m7_mutants.py', 'timeout=300)'), 'timeout=300,'),
    'm73_store': (['mut_runner.py'], ['mut_runner_s1.py'], ('m73_store_mutants.py', 'timeout=300)'), 'timeout=300,'),
    'm91': (['mut_runner.py'], ['mut_runner_s1.py'], ('m91_mutants.py', 'timeout=300)'), 'timeout=300,'),
    'f67': (['mut_runner.py'], ['mut_runner_s1.py'], None, 'timeout=300,'),
    'f671': (['mut_runner.py'], ['mut_runner_s1.py'], None, 'timeout=300,'),
    'f672': (['mut_runner.py'], ['mut_runner_s1.py'], None, 'timeout=300,'),
    'f673': (['mut_runner.py'], ['mut_runner_s1.py'], None, 'timeout=300,'),
    'f674': (['mut_runner.py'], ['mut_runner_s1.py'], None, 'timeout=300,'),
    'mie': (['mut_runner.py'], ['mut_runner_s1.py'], ('mie_mutants.py', 'timeout=300)'), 'timeout=300,'),
    'mie11': (['mut_runner.py'], ['mut_runner_s1.py'], ('mie_mutants.py', 'timeout=300)'), 'timeout=300,'),
}
# M10's f672 reruns a timeout under a short --timeout once more under 300 s (f672_mutants.py:30-35); f673 and f674 load that rule
F672_RERUN = ('f672_mutants.py', 'short, F_timeout = F.TIMEOUT, 300')


def first_mutant(tool):
    doc, _ = E.load_pins()
    return doc['mutation_lists']['%s_mutants_s1' % tool]['ids'][0]


def _patch(path, old, new):
    with open(path, encoding='utf-8') as f:
        src = f.read()
    assert src.count(old) == 1, (path, old, src.count(old))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(src.replace(old, new))


def stub_tree(dest, tool, mode, side, sleep=60):
    """A copy of this tree for one tool run: the child files of `side` ('m10' or 's1') replaced by the stub in `mode`, the timeout
    patched to TIMEOUT_S (for M10's f67 family through its --timeout option, and its f672 rerun's 300 s patched too), and for M10's m2,
    which has no selection option, its mutant list trimmed to the one mutant."""
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
    m10_files, s1_files, m10_timeout, s1_timeout = MUT_TOOLS[tool]
    ok, failed, evidence = _stub_text('ok')[0], _stub_text('failed')[0], _stub_text('evidence')[0]
    for f in (m10_files if side == 'm10' else s1_files):
        with open(os.path.join(dest, 'tools', f), 'w', encoding='utf-8') as fh:
            fh.write(STUB % {'mode': mode, 'ok': ok, 'failed': failed, 'evidence': evidence, 'sleep': sleep})
    if side == 's1':
        _patch(os.path.join(dest, 'tools', '%s_mutants_s1.py' % tool), s1_timeout, 'timeout=%d,' % TIMEOUT_S)
    else:
        if m10_timeout:
            _patch(os.path.join(dest, 'tools', m10_timeout[0]), m10_timeout[1], m10_timeout[1].replace(m10_timeout[1].split('=')[1][:-1], str(TIMEOUT_S)))
        if tool in ('f672', 'f673', 'f674'):
            _patch(os.path.join(dest, 'tools', F672_RERUN[0]), F672_RERUN[1], F672_RERUN[1].replace('300', str(TIMEOUT_S)))
        if tool == 'm2':
            _patch(os.path.join(dest, 'tools', 'm2_mutants.py'), '\ndef main():\n',
                   '\nMUT = [m for m in MUT if m[0] == %r]     # planted by tests_tools: one mutant\n\n\ndef main():\n' % first_mutant('m2'))
    return dest


def run_tool(tree, script, args, site=False, timeout=900):
    tmp = tempfile.mkdtemp(prefix='s1_tl_')
    try:
        cmd = [sys.executable, '-I'] + ([] if site else ['-S']) + [os.path.join('tools', script)] + list(args)
        p = _sp.run(cmd, cwd=tree, capture_output=True, text=True, timeout=timeout,
                    env={'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': tmp,
                         'PYTHONDONTWRITEBYTECODE': '1'})
        return p.returncode, p.stdout, p.stderr
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_m10_tool(tmpdir, tool, mode):
    mid = first_mutant(tool)
    tree = stub_tree(os.path.join(tmpdir, '%s_m10_%s' % (tool, mode)), tool, mode, 'm10')
    args = [] if tool == 'm2' else ['--ids', mid]
    if MUT_TOOLS[tool][2] is None:
        args += ['--timeout', str(TIMEOUT_S)]
    code, out, err = run_tool(tree, '%s_mutants.py' % tool, args, site=True)
    shutil.rmtree(tree, ignore_errors=True)
    return mid, code, out, err


def run_s1_tool(tmpdir, tool, mode, ids=None):
    mid = first_mutant(tool)
    tree = stub_tree(os.path.join(tmpdir, '%s_s1_%s' % (tool, mode)), tool, mode, 's1')
    code, out, err = run_tool(tree, '%s_mutants_s1.py' % tool, ['--ids', ids or mid])
    shutil.rmtree(tree, ignore_errors=True)
    return mid, code, out, err


class ToolLevelTimeoutCrashKill(unittest.TestCase):
    """P1-F7 (R4), AX-4, P2-B8 (R4), P3-B03 (R4), P4-B13, P5-S08: per tool, on M10 a hanging child and a crashing child are both KILLED,
    exit 0; on the successor a timeout is INDETERMINATE cause=timeout with its TIMEOUT measurement line, exit 3, a crash INDETERMINATE
    cause=crash_no_result, exit 3, and a genuine failure KILLED, exit 0; a failed start control leaves every mutant NOT_RUN, exit 3.
    (The plan's added line was called TIMING; the line the successor prints is TIMEOUT <id> cmd=... limit=... control_start=...
    control_end=..., R1 §2.6.)  m8, whose oracle is a unittest tier, is in ToolLevelM8 below."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_tool_level_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def m10_killed(self, tool, mode):
        mid, code, out, err = run_m10_tool(self.tmp, tool, mode)
        self.assertEqual(code, 0, (tool, mode, out[-1500:], err[-1500:]))
        # M10 prints a KILLED line per mutant (some tools only with --verbose) and its summary 'mutants 1  killed 1 ...'
        self.assertTrue(_re.search(r'(?m)^KILLED +%s +\(by ' % _re.escape(mid), out) or _re.search(r'(?m)^mutants 1 +killed 1 ', out),
                        (tool, mode, out[-1500:]))
        self.assertIn('MUTATION RUN OK', out)
        if mode == 'sleep':
            self.assertIn('timeout', out)          # M10 attributes the kill to the timeout ('(by timeout)' or {'timeout': 1})
        return out

    def s1(self, tool, mode, want_code, want_line):
        mid, code, out, err = run_s1_tool(self.tmp, tool, mode)
        self.assertEqual(code, want_code, (tool, mode, out[-2000:], err[-1500:]))
        self.assertRegex(out, r'(?m)^MUTANT %s %s' % (_re.escape(mid), want_line))
        self.assertEqual(E.check_output(out, code, selected=[mid]), [], out[-2000:])
        self.assertTrue(out.strip().splitlines()[-1].endswith(' exit=%d' % want_code))
        return mid, out


def _add_tool_cases():
    for tool in MUT_TOOLS:
        def t_timeout(self, tool=tool):
            out = self.m10_killed(tool, 'sleep')
            if tool in ('f672', 'f673', 'f674'):
                self.assertIn('timeout (also under 300 s)', out)      # M10 reran it and timed out a second time: still a kill
            mid, out = self.s1(tool, 'sleep', 3, r'INDETERMINATE cause=timeout$')
            self.assertRegex(out, r'(?m)^TIMEOUT %s cmd=\S+ limit=%ss control_start=\d+\.\d{3}s control_end=(\d+\.\d{3}s|NA)$'
                             % (_re.escape(mid), TIMEOUT_S))
            self.assertIn(' indeterminate=1 ', out.strip().splitlines()[-1])

        def t_crash(self, tool=tool):
            self.m10_killed(tool, 'crash')
            self.s1(tool, 'crash', 3, r'INDETERMINATE cause=crash_no_result$')

        def t_genuine_kill(self, tool=tool):
            self.m10_killed(tool, 'failed')
            mid, out = self.s1(tool, 'failed', 0, r'KILLED cause=\S+$')
            self.assertIn(' killed=1 ', out.strip().splitlines()[-1])

        def t_control(self, tool=tool):
            mid, out = self.s1(tool, 'control_fail', 3, r'NOT_RUN cause=control_start_FAIL$')
            self.assertRegex(out, r'(?m)^CONTROL start CONTROL_FAIL cause=CHILD_FAILED ')
            self.assertIn(' control_start=FAIL started=0 ', out.strip().splitlines()[-1])

        for name, fn in (('test_timeout_', t_timeout), ('test_crash_', t_crash), ('test_genuine_kill_', t_genuine_kill),
                         ('test_failed_start_control_', t_control)):
            setattr(ToolLevelTimeoutCrashKill, name + tool, fn)


_add_tool_cases()



M8_M10_TIER_STUB = r"""import os, time, unittest
# planted by tests_tools/test_mutation_timeout.py: an M8 tier module, replaced in a temporary copy (M10's m8_mutants runs
# 'python -m unittest -f tests_m8.<tier modules>' against APG_ROOT=<the mutated copy>, m8_mutants.py:146-155)
MODE, TARGET, OLD = %(mode)r, %(target)r, %(old)r
with open(os.path.join(os.environ['APG_ROOT'], TARGET), encoding='utf-8') as fh:
    control = OLD in fh.read()
if MODE == 'control_fail' or not control:
    if MODE == 'sleep':
        time.sleep(%(sleep)d)
    elif MODE == 'crash':
        os._exit(139)


class T(unittest.TestCase):
    def test_a(self):
        self.assertTrue(control and MODE != 'control_fail' or MODE not in ('failed', 'control_fail'))
"""

M8_S1_END_FAIL = r"""import os, sys
# planted by tests_tools/test_mutation_timeout.py: m8's tier runner in a temporary copy; the start control passes, the mutant fails, and
# every control after the mutant fails (a failing end control)
OK, FAILED, SEEN = %(ok)r, %(failed)r, %(seen)r
a = sys.argv[1:]
rid = a[a.index('--run-id') + 1]
if rid.startswith('control') and not os.path.exists(SEEN):
    print(OK); sys.exit(0)
if not rid.startswith('control'):
    open(SEEN, 'w').close()
print(FAILED); sys.exit(1)
"""


class ToolLevelM8(unittest.TestCase):
    """P7-B3 (R4), row 15 of the P1-F7 inventory: m8_mutants on M10 marks a timeout TIMEOUT but exits 1, counts a tier that crashes with
    no FAIL:/ERROR: line as KILLED, and exits 2 on a failed control; the successor gives INDETERMINATE (exit 3), INDETERMINATE
    cause=crash_no_result (exit 3), and exit 3 with every mutant NOT_RUN; a failing end control keeps the mutant's line and exits 3."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_tool_m8_')
        self.M = E.load_tool_module('m8_mutants', ROOT)
        self.mid, self.target, self.old = self.M.MUTANTS[0][:3]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def m10(self, mode):
        tree = os.path.join(self.tmp, 'm10_' + mode)
        shutil.copytree(ROOT, tree, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
        for mod in self.M.TIER1 + self.M.TIER2:
            with open(os.path.join(tree, 'tests_m8', mod + '.py'), 'w', encoding='utf-8') as fh:
                fh.write(M8_M10_TIER_STUB % {'mode': mode, 'target': self.target, 'old': self.old, 'sleep': 60})
        return run_tool(tree, 'm8_mutants.py', ['--only', self.mid, '--timeout', str(TIMEOUT_S), '--jobs', '1'], site=True)

    def s1(self, mode, stub=None):
        tree = os.path.join(self.tmp, 's1_' + mode)
        shutil.copytree(ROOT, tree, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
        ok, failed, evidence = _stub_text('ok')[0], _stub_text('failed')[0], _stub_text('evidence')[0]
        with open(os.path.join(tree, 'tools', 'child_unittest_runner.py'), 'w', encoding='utf-8') as fh:
            fh.write(stub or STUB % {'mode': mode, 'ok': ok, 'failed': failed, 'evidence': evidence, 'sleep': 60})
        p = os.path.join(tree, 'tools', 'm8_mutants_s1.py')
        with open(p, encoding='utf-8') as fh:
            src = fh.read()
        assert src.count('timeout=600') == 2
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(src.replace('timeout=600', 'timeout=%d' % TIMEOUT_S))
        code, out, err = run_tool(tree, 'm8_mutants_s1.py', ['--ids', self.mid])
        self.assertEqual(E.check_output(out, code, selected=[self.mid]), [], out[-2000:])
        return code, out, err

    def test_timeout_m8(self):
        code, out, err = self.m10('sleep')
        self.assertEqual(code, 1, out[-1500:] + err[-1500:])
        self.assertRegex(out, r'(?m)^%s +TIMEOUT ' % self.mid)
        code, out, err = self.s1('sleep')
        self.assertEqual(code, 3, out[-2000:] + err[-1500:])
        self.assertIn('MUTANT %s INDETERMINATE cause=timeout' % self.mid, out)
        self.assertRegex(out, r'(?m)^TIMEOUT %s cmd=tier1 limit=%ss ' % (self.mid, TIMEOUT_S))

    def test_crash_m8(self):
        code, out, err = self.m10('crash')
        self.assertEqual(code, 0, out[-1500:] + err[-1500:])
        self.assertRegex(out, r'(?m)^%s +KILLED ' % self.mid)
        code, out, err = self.s1('crash')
        self.assertEqual(code, 3, out[-2000:])
        self.assertIn('MUTANT %s INDETERMINATE cause=crash_no_result' % self.mid, out)

    def test_genuine_kill_m8(self):
        code, out, err = self.m10('failed')
        self.assertEqual(code, 0, out[-1500:] + err[-1500:])
        self.assertRegex(out, r'(?m)^%s +KILLED +\S+ tier 1: ' % self.mid)
        code, out, err = self.s1('failed')
        self.assertEqual(code, 0, out[-2000:])
        self.assertRegex(out, r'(?m)^MUTANT %s KILLED cause=\S+$' % self.mid)     # cause: the first failing file

    def test_failed_start_control_m8(self):
        code, out, err = self.m10('control_fail')
        self.assertEqual(code, 2, out[-1500:] + err[-1500:])
        self.assertRegex(out, r'(?m)^CONTROL \(unmutated copy\): (?!passes)')
        code, out, err = self.s1('control_fail')
        self.assertEqual(code, 3, out[-2000:])
        self.assertIn('MUTANT %s NOT_RUN cause=control_start_FAIL' % self.mid, out)

    def test_failing_end_control_m8(self):
        seen = os.path.join(self.tmp, 'mutant_seen')
        stub = M8_S1_END_FAIL % {'ok': _stub_text('ok')[0], 'failed': _stub_text('failed')[0], 'seen': seen}
        code, out, err = self.s1('end_fail', stub=stub)
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^MUTANT %s KILLED cause=\S+$' % self.mid)          # the mutant's line is kept
        self.assertRegex(out, r'(?m)^CONTROL end CONTROL_FAIL ')
        self.assertIn(' control_start=PASS ', out.strip().splitlines()[-1])
        self.assertIn(' control_end=FAIL ', out.strip().splitlines()[-1])



# ---------------------------------------------------------------------------------------------------------------------------------------
# Sabotage tools at tool level (authorisation §4.5; T-K (R5), decision K-1): each successor sabotage tool on a temporary copy, restricted to
# one plant, with the check that plant's step runs replaced in the copy by a stub.
# ---------------------------------------------------------------------------------------------------------------------------------------

REG_STUB = r"""import os, sys, time
# planted by tests_tools/test_mutation_timeout.py: an M10 regression tool run as '<tool> --step S' by a sabotage tool, replaced in a copy
import hashlib
MODE, PATH, CLEAN_SHA256 = %(mode)r, %(path)r, %(sha)r
a = sys.argv[1:]
step = a[a.index('--step') + 1]
with open(os.path.join(os.getcwd(), PATH), 'rb') as fh:
    clean = hashlib.sha256(fh.read()).hexdigest() == CLEAN_SHA256      # the plant's file as it is in the unsabotaged tree
if clean and MODE != 'control_fail':
    print('PASS %%s stub' %% step); print('checks 1  failed 0'); sys.exit(0)
if MODE == 'sleep':
    time.sleep(%(sleep)d)
if MODE == 'crash':
    sys.exit(139)
print('FAIL %%s stub' %% step); print('checks 1  failed 1'); sys.exit(1)
"""

TESTS_STUB = r"""import sys, time
# planted by tests_tools/test_mutation_timeout.py: the test runner a sabotage tool starts for a plant's check, replaced in a copy
MODE = %(mode)r
OK, FAILED = %(ok)r, %(failed)r
a = sys.argv[1:]
rid = a[a.index('--run-id') + 1] if '--run-id' in a else ''
if rid.startswith('control') and MODE != 'control_fail':
    print(OK); sys.exit(0)
if MODE == 'sleep':
    time.sleep(%(sleep)d)
if MODE == 'crash':
    print('Segmentation fault (core dumped)'); sys.exit(139)
print(FAILED); sys.exit(1)
"""

# tool: (successor timeout text in the tool file, or the text after which ' timeout=N,' is inserted; the check kind; the stubbed file;
#        the plant)
REGRESSION_SABOTAGE = {'f67': 'run_regression_f67', 'f671': 'run_regression_f671', 'f672': 'run_regression_f672',
                       'f673': 'run_regression_f673', 'f674': 'run_regression_f674', 'm7': 'run_regression_m7',
                       'm71': 'run_regression_m71', 'm72': 'run_regression_m72', 'm73': 'run_regression_m73'}


def _tests_text(state, mode):
    res = {'test_stub.py': E.FileResult('test_stub.py', 'COMPLETED', [('tests.test_stub.T.test_a', 'PASS' if state == 'ok' else 'FAIL')],
                                        '0' * 64)}
    return '\n'.join(E.finish_tests('stub_child', mode, 'stub', ['test_stub.py'], res, STUB_PIN)[0])


def sabotage_case(tool):
    """(plant id, the check's kind, the stubbed file, its stub text template values)."""
    if tool in REGRESSION_SABOTAGE:
        M = E.load_tool_module('sabotage_' + tool, ROOT)
        try:
            import test_mutant_targets as T
        except ImportError:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import test_mutant_targets as T
        bad = {d.split(':')[0] for d in T.NOT_EXACTLY_ONCE['sabotage_' + tool]}
        c = next(c for c in M.CASES if c[2] is not None and c[0] not in bad)
        return c[0], 'regression', REGRESSION_SABOTAGE[tool] + '.py', {'path': c[2], 'sha': E.sha256_file(os.path.join(ROOT, c[2]))}
    if tool in ('mie1', 'mie1_1'):
        M = E.load_tool_module('sabotage_' + tool, ROOT)
        c = next(c for c in M.CASES if c[5].endswith('.py'))
        return c[0], 'tests', 'run_m2_tests_s1.py', {'ok': _tests_text('ok', 'failfast'), 'failed': _tests_text('failed', 'failfast')}
    if tool == 'm8':
        return 'S01', 'tests', 'run_m8_tests_s1.py', {'ok': _tests_text('ok', 'full'), 'failed': _tests_text('failed', 'full')}
    if tool == 'm10':       # its judge needs the plant's own named test to fail
        tid = E.load_tool_module('sabotage_m10', ROOT).CASES[0][5][1]
        name = tid.rsplit('.', 2)[0].split('.')[-1] + '.py'
        pin = {name: {'sha256': '0' * 64, 'ids': [tid]}}
        failed = '\n'.join(E.finish_tests('stub_child', 'failfast', 'stub', [name],
                                           {name: E.FileResult(name, 'COMPLETED', [(tid, 'FAIL')], '0' * 64)}, pin)[0])
        return 'V01', 'tests', 'child_unittest_runner.py', {'ok': _tests_text('ok', 'failfast'), 'failed': failed}
    raise KeyError(tool)


def sabotage_tree(dest, tool, mode, sleep=60):
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
    pid, kind, stubbed, vals = sabotage_case(tool)
    with open(os.path.join(dest, 'tools', stubbed), 'w', encoding='utf-8') as fh:
        fh.write((REG_STUB if kind == 'regression' else TESTS_STUB) % dict(vals, mode=mode, sleep=sleep))
    p = os.path.join(dest, 'tools', 'sabotage_%s_s1.py' % tool)
    with open(p, encoding='utf-8') as fh:
        src = fh.read()
    if tool in ('mie1', 'mie1_1'):
        old, new = 'sys.argv[1:],', 'sys.argv[1:], timeout=%d,' % TIMEOUT_S
    else:
        old = next(t for t in ('timeout=3600', 'timeout=1800', 'timeout=900') if t in src)
        new = 'timeout=%d' % TIMEOUT_S
    assert src.count(old) == 1, (tool, old)
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write(src.replace(old, new))
    return pid


SABOTAGE_TOOLS = list(REGRESSION_SABOTAGE) + ['mie1', 'mie1_1', 'm8', 'm10']


class SabotageToolLevel(unittest.TestCase):
    """Authorisation §4.5 for every sabotage tool (sabotage_f67, f671 to f674, m7, m71, m72, m73, mie1, mie1_1, m8, m10), each with one plant
    and its check replaced in the copy by a stub: the check fails on the sabotaged tree -> CAUGHT, exit 0; the check hangs past the
    (patched) timeout -> INDETERMINATE cause=timeout, exit 3, never caught; the check dies with no structured result -> INDETERMINATE,
    exit 3, never caught; the check fails on the clean tree too -> the start control fails, the plant is NOT_RUN, exit 3.  The preflight
    cases are in test_mutant_targets.py (NOT_EXACTLY_ONCE) and in test_runner_zero_work.py (a plant target not exactly once is refused).
    On M10, sabotage_m10 counts any non-zero exit of the check as a catch, so a crashing check is CAUGHT; the successor never counts it."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_sab_tl_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def s1(self, tool, mode, want_code, want):
        tree = os.path.join(self.tmp, '%s_%s' % (tool, mode))
        pid = sabotage_tree(tree, tool, mode)
        code, out, err = run_tool(tree, 'sabotage_%s_s1.py' % tool, ['--ids', pid])
        shutil.rmtree(tree, ignore_errors=True)
        self.assertEqual(code, want_code, (tool, mode, out[-2000:], err[-1500:]))
        self.assertRegex(out, r'(?m)^PLANT %s %s' % (_re.escape(pid), want))
        self.assertEqual(E.check_output(out, code, selected=[pid]), [], out[-2000:])
        return out

    def test_m10_sabotage_m10_counts_a_crash_as_caught(self):
        tree = os.path.join(self.tmp, 'm10_m10')
        shutil.copytree(ROOT, tree, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
        M = E.load_tool_module('sabotage_m10', ROOT)
        cid, what, path, old, new, check = M.CASES[0]
        mod, cls, meth = check[1].rsplit('.', 2)
        with open(os.path.join(tree, *mod.split('.')) + '.py', 'w', encoding='utf-8') as fh:
            fh.write('import os, unittest\nROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n'
                     'with open(os.path.join(ROOT, %r), encoding="utf-8") as fh:\n    clean = %r in fh.read()\n'
                     'if not clean:\n    os._exit(139)\n\n\nclass %s(unittest.TestCase):\n    def %s(self):\n        pass\n'
                     % (path, old, cls, meth))
        code, out, err = run_tool(tree, 'sabotage_m10.py', ['--only', cid], site=True)
        self.assertRegex(out, r'(?m)^\s*CAUGHT\b.*\b%s\b|\b%s\b.*\bCAUGHT\b' % (cid, cid))
        self.assertIn('sabotage 1  caught 1', out)
        self.assertEqual(code, 0, out[-1500:] + err[-1500:])


def _add_sabotage_cases():
    for tool in SABOTAGE_TOOLS:
        def t_caught(self, tool=tool):
            self.s1(tool, 'failed', 0, r'CAUGHT ')

        def t_timeout(self, tool=tool):
            self.s1(tool, 'sleep', 3, r'INDETERMINATE cause=timeout$')

        def t_crash(self, tool=tool):
            self.s1(tool, 'crash', 3, r'INDETERMINATE cause=\S+$')

        def t_control(self, tool=tool):
            out = self.s1(tool, 'control_fail', 3, r'NOT_RUN cause=control_start_FAIL$')
            self.assertRegex(out, r'(?m)^CONTROL start CONTROL_FAIL ')
        for name, fn in (('test_sabotage_caught_', t_caught), ('test_sabotage_timeout_', t_timeout), ('test_sabotage_crash_', t_crash),
                         ('test_sabotage_failed_start_control_', t_control)):
            setattr(SabotageToolLevel, name + tool, fn)


_add_sabotage_cases()



class PreflightBeforeAnyItem(unittest.TestCase):
    """Authorisation §4.5, first point, for every successor mutation tool (16) and sabotage tool (13): preflight=PASS is required before any
    item starts.  In a temporary copy the pinned site of the tool's first item is changed (tools/expected_counts.json, with its change
    record), so the item's real site no longer matches its pin; the run selects that item and stops in the preflight: RUN_ERROR
    PREFLIGHT_INVALID_TARGET <id>:site_differs_from_pin, the item NOT_RUN cause=preflight_failed, no CONTROL line (no control ran),
    preflight=FAIL control_start=NOT_RUN started=0, exit 2, and the checker accepts the output.  (The missing-target cases on the real lists
    are in test_mutant_targets.py; the fault runners, which run in one process and pin no sites, are in test_runner_zero_work.py.)"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_preflight_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def _add_preflight_cases():
    tools = [('mutation_lists', '%s_mutants_s1' % t) for t in list(MUT_TOOLS) + ['m8']] + \
            [('plant_lists', 'sabotage_%s_s1' % t) for t in SABOTAGE_TOOLS]
    for key, tool in tools:
        def t(self, key=key, tool=tool):
            tree = os.path.join(self.tmp, tool)
            shutil.copytree(ROOT, tree, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
            pp = os.path.join(tree, 'tools', 'expected_counts.json')
            import json
            with open(pp, encoding='utf-8') as fh:
                doc = json.load(fh)
            first = doc[key][tool]['ids'][0]
            doc[key][tool]['sites'][first]['site_sha256'] = '0' * 64
            E.write_pins(doc, 'test: one pinned site changed', 'tests_tools planted fault', [], path=pp)
            code, out, err = run_tool(tree, tool + '.py', ['--ids', first])
            self.assertEqual(code, 2, (tool, out[-2000:], err[-1500:]))
            self.assertIn('RUN_ERROR PREFLIGHT_INVALID_TARGET %s:site_differs_from_pin' % first, out)
            self.assertRegex(out, r'(?m)^(MUTANT|PLANT) %s NOT_RUN cause=preflight_failed$' % _re.escape(first))
            self.assertNotRegex(out, r'(?m)^CONTROL ')
            last = out.strip().splitlines()[-1]
            self.assertIn(' preflight=FAIL control_start=NOT_RUN started=0 ', last)
            self.assertTrue(last.endswith(' status=EVIDENCE_ERROR exit=2'), last)
            self.assertEqual(E.check_output(out, code, selected=[first]), [])
        setattr(PreflightBeforeAnyItem, 'test_preflight_' + tool, t)


_add_preflight_cases()


if __name__ == '__main__':
    unittest.main()
