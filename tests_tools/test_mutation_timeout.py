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
T.load()        # corrective pass 2, C.1
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
        T.load()        # corrective pass 2, C.1
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


# corrective pass 2, E point 8: M10's literal kill attribution, (for a timeout, for a crash), as M10 prints it in this tree
M10_ATTRIBUTION = dict({t: ('timeout', 'crash') for t in MUT_TOOLS}, m2=('timeout', 'tests'), m3=('timeout', 'mapping'),
                       f672=('timeout (also under 300 s)', 'crash'), f673=('timeout (also under 300 s)', 'crash'),
                       f674=('timeout (also under 300 s)', 'crash'))


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
        if mode in ('sleep', 'crash'):
            # corrective pass 2, E point 8: M10's attribution asserted in M10's literal text.  Recorded as found: M10's m2 and m3
            # attribute a crash to the tests, exactly as a genuine failure ('(by tests)', the first test file's name)
            want = M10_ATTRIBUTION[tool][0 if mode == 'sleep' else 1]
            if tool == 'm2':
                self.assertRegex(out, r'(?m)^KILLED     %s  \(by %s\)$' % (_re.escape(mid), want), out[-1500:])
                self.assertRegex(out, r'(?m)^mutants 1  killed 1 \(tests %d, contracts 0\) ' % (mode == 'crash'), out[-1500:])
            else:
                self.assertRegex(out, r"(?m)^mutants 1  killed 1 \(first failing test file: \{'%s': 1\}\)  " % _re.escape(want),
                                 out[-1500:])
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
            # corrective pass 2, E point 9 (D13): the TIMEOUT line's command has a timing for the same command on the CONTROL end line
            cmd = _re.search(r'(?m)^TIMEOUT %s cmd=(\S+) ' % _re.escape(mid), out).group(1)
            end = [l for l in out.splitlines() if l.startswith('CONTROL end ')]
            self.assertEqual(len(end), 1, out[-2000:])
            self.assertRegex(end[0], r' %s=\d+\.\d{3}s( |$)' % _re.escape(cmd), (cmd, end[0]))

        def t_crash(self, tool=tool):
            self.m10_killed(tool, 'crash')
            self.s1(tool, 'crash', 3, r'INDETERMINATE cause=crash_no_result$')

        def t_genuine_kill(self, tool=tool):
            self.m10_killed(tool, 'failed')
            mid, out = self.s1(tool, 'failed', 0, r'KILLED cause=\S+$')
            self.assertIn(' killed=1 ', out.strip().splitlines()[-1])
            # authorisation §4.5, third point: the end control is recorded separately, by its own line and its own RESULT field
            self.assertRegex(out, r'(?m)^CONTROL start CONTROL_PASS ')
            self.assertRegex(out, r'(?m)^CONTROL end CONTROL_PASS ')
            self.assertIn(' control_start=PASS ', out.strip().splitlines()[-1])
            self.assertIn(' control_end=PASS ', out.strip().splitlines()[-1])

        def t_control(self, tool=tool):
            mid, out = self.s1(tool, 'control_fail', 3, r'NOT_RUN cause=control_start_FAIL$')
            self.assertRegex(out, r'(?m)^CONTROL start CONTROL_FAIL cause=CHILD_FAILED ')
            self.assertIn(' control_start=FAIL started=0 ', out.strip().splitlines()[-1])

        for name, fn in (('test_timeout_', t_timeout), ('test_crash_', t_crash), ('test_genuine_kill_', t_genuine_kill),
                         ('test_failed_start_control_', t_control)):
            setattr(ToolLevelTimeoutCrashKill, name + tool, fn)


_add_tool_cases()




class E12M3NonMatchingPattern(unittest.TestCase):
    """Corrective pass 2, E point 12: a real pattern that selects no test file, through m3_mutants_s1 and its real kill oracle
    (run_m2_tests_s1).  In a temporary copy, the mutant's commands start with a pattern that matches no file; the controls keep M10's
    TEST_ORDER.  M10 half, recorded as found: M10's run_m2_tests.py exits 0 for such a pattern ('NO TESTS RAN'), so M10's m3 would read
    it as that pattern passing.  BUILDER-EXECUTED: NOT INDEPENDENT."""

    PAT = 'test_ingest_nosuch.py'

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_e12_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_m10_runner_passes_a_pattern_that_selects_no_file(self):
        code, out, err = run_tool(ROOT, 'run_m2_tests.py', ['-q', '--failfast', self.PAT], site=True)
        self.assertEqual(code, 0, out[-1500:] + err[-1500:])
        self.assertIn('NO TESTS RAN', out + err)

    def test_successor_reports_the_mutant_item_error(self):
        tree = os.path.join(self.tmp, 't')
        shutil.copytree(ROOT, tree, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
        _patch(os.path.join(tree, 'tools', 'm3_mutants_s1.py'), '            for pat in M.TEST_ORDER]\n',
               '            for pat in (M.TEST_ORDER if mutant is None else [%r] + M.TEST_ORDER)]\n' % self.PAT)
        mid = first_mutant('m3')
        code, out, err = run_tool(tree, 'm3_mutants_s1.py', ['--ids', mid])
        self.assertEqual(code, 2, out[-2000:] + err[-1500:])
        self.assertRegex(out, r'(?m)^MUTANT %s ITEM_ERROR cause=\S+$' % _re.escape(mid))
        self.assertNotRegex(out, r'(?m)^MUTANT %s KILLED ' % _re.escape(mid))
        self.assertRegex(out, r'(?m)^CONTROL start CONTROL_PASS ')
        self.assertRegex(out, r'(?m)^CONTROL end CONTROL_PASS ')
        last = out.strip().splitlines()[-1]
        self.assertIn(' item_errors=1 ', last)
        self.assertTrue(last.endswith(' status=EVIDENCE_ERROR exit=2'), last)
        self.assertEqual(E.check_output(out, code, selected=[mid]), [], out[-2000:])



class E1KillOracleNamesAMissingTestFile(unittest.TestCase):
    """Corrective pass 2, E point 1: a real mutation tool (m4) whose kill oracle names a test file that does not exist, with the real
    child runners.  In a temporary copy, the mutant's oracle starts with test_fin_missing.py (the controls keep M10's order).  M10: its
    mut_runner.py finds no test, prints the short name and exits 1, so M10 counts the mutant KILLED by 'missing'.  Successor:
    mut_runner_s1 refuses the unpinned name (exit 2), so the mutant is ITEM_ERROR, never KILLED.  BUILDER-EXECUTED: NOT INDEPENDENT."""

    MISSING = 'test_fin_missing.py'

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_e1_')
        self.mid = first_mutant('m4')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def tree(self, name):
        t = os.path.join(self.tmp, name)
        shutil.copytree(ROOT, t, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
        self.assertFalse(os.path.exists(os.path.join(t, 'tests', self.MISSING)))
        return t

    def test_m10_counts_it_as_a_kill(self):
        t = self.tree('m10')
        _patch(os.path.join(t, 'tools', 'm4_mutants.py'), "    order = [FIRST[mod]] + [t for t in ALL_TESTS if t != FIRST[mod]]\n",
               "    order = [%r, FIRST[mod]] + [t for t in ALL_TESTS if t != FIRST[mod]]\n" % self.MISSING)
        code, out, err = run_tool(t, 'm4_mutants.py', ['--ids', self.mid], site=True)
        self.assertEqual(code, 0, out[-1500:] + err[-1500:])
        self.assertRegex(out, r"(?m)^mutants 1  killed 1 \(first failing test file: \{'missing': 1\}\)  ")
        self.assertIn('MUTATION RUN OK', out)

    def test_successor_reports_item_error_never_killed(self):
        t = self.tree('s1')
        _patch(os.path.join(t, 'tools', 'm4_mutants_s1.py'), "    order = [M.FIRST[mod]] + [t for t in M.ALL_TESTS if t != M.FIRST[mod]]\n",
               "    order = ([] if mutant is None else [%r]) + [M.FIRST[mod]] + [t for t in M.ALL_TESTS if t != M.FIRST[mod]]\n" % self.MISSING)
        code, out, err = run_tool(t, 'm4_mutants_s1.py', ['--ids', self.mid])
        self.assertEqual(code, 2, out[-2000:] + err[-1500:])
        self.assertRegex(out, r'(?m)^MUTANT %s ITEM_ERROR cause=\S+$' % _re.escape(self.mid))
        self.assertNotRegex(out, r'(?m)^MUTANT \S+ KILLED ')
        self.assertNotIn('MUTATION RUN OK', out)
        self.assertRegex(out, r'(?m)^CONTROL start CONTROL_PASS ')
        self.assertRegex(out, r'(?m)^CONTROL end CONTROL_PASS ')
        self.assertTrue(out.strip().splitlines()[-1].endswith(' status=EVIDENCE_ERROR exit=2'))
        self.assertEqual(E.check_output(out, code, selected=[self.mid]), [], out[-2000:])



TEE_PROBE = (
    "import sys as _ts, os as _to\n"
    "class _Tee:\n"
    "    def __init__(self, a, b):\n"
    "        self.a, self.b = a, b\n"
    "    def write(self, x):\n"
    "        self.b.write(x)\n"
    "        return self.a.write(x)\n"
    "    def flush(self):\n"
    "        self.b.flush()\n"
    "        self.a.flush()\n"
    "    def __getattr__(self, n):\n"
    "        return getattr(self.a, n)\n"
    "_ts.stdout = _Tee(_ts.stdout, open(_to.path.join(%r, '%%d.txt' %% _to.getpid()), 'w'))\n")


class E26RealFailFast(unittest.TestCase):
    """Corrective pass 2, E points 26 and 22: real fail-fast on the real child runner, with a real failing first test file, inside a
    mutation tool (F1: m4_mutants_s1 and mut_runner_s1, mutant FG-CMP-001), an M8 tier (F7: m8_mutants_s1 and child_unittest_runner,
    mutant ML-01) and a sabotage tool (F8: sabotage_m10_s1 and child_unittest_runner, plant V01).  A probe prepended to the child runner in
    a temporary copy copies its stdout to one log file per child process, so the child's own FILE and TEST lines are asserted directly
    and through check_output with the pins: the failing file is COMPLETED with tests + tests_not_run equal to its pin (F11), its TEST
    lines are its pinned ids in order, and the files after it are SKIPPED_AFTER_FAILURE.  Reading: a sabotage check names one test file,
    so in F8 the fail-fast shows as the stop inside that file.  BUILDER-EXECUTED: NOT INDEPENDENT."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_e26_')
        self.pins = E.load_pins()[0]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def tree(self, runner):
        t = os.path.join(self.tmp, 't')
        shutil.copytree(ROOT, t, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
        self.logs = os.path.join(self.tmp, 'child_logs')
        os.makedirs(self.logs)
        p = os.path.join(t, 'tools', runner)
        with open(p, encoding='utf-8') as fh:
            src = fh.read()
        head, rest = src.split('\n', 1)
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(head + '\n' + TEE_PROBE % self.logs + rest)
        return t

    def child_run(self, run_id):
        """The output of the child whose RESULT line has run=<run_id>; exactly one."""
        outs = []
        for f in sorted(os.listdir(self.logs)):
            with open(os.path.join(self.logs, f)) as fh:
                o = fh.read()
            if _re.search(r'(?m)^RESULT v=2 kind=tests .* run=%s ' % _re.escape(run_id), o):
                outs.append(o)
        self.assertEqual(len(outs), 1, (run_id, os.listdir(self.logs)))
        return outs[0]

    def f11(self, out, failing, later, rel_prefix):
        rel = rel_prefix + failing
        ids = self.pins['test_files'][rel]['ids']
        m = _re.search(r'(?m)^FILE %s state=COMPLETED tests=(\d+) passed=\d+ failed=(\d+) errors=(\d+) skipped=\d+ tests_not_run=(\d+) '
                       r'file_sha256=(\S+) ' % _re.escape(failing), out)
        self.assertTrue(m, [l for l in out.splitlines() if l.startswith('FILE ')])
        failed, errors, not_run = int(m.group(2)), int(m.group(3)), int(m.group(4))
        self.assertGreaterEqual(failed + errors, 1)
        self.assertEqual(int(m.group(1)) + not_run, len(ids))
        self.assertEqual(m.group(5), self.pins['test_files'][rel]['sha256'])
        tests = _re.findall(r'(?m)^TEST %s::(\S+) (\S+)$' % _re.escape(failing), out)
        self.assertEqual([t[0] for t in tests], ids)
        self.assertEqual(sum(1 for t in tests if t[1] == 'NOT_RUN_AFTER_FAILURE'), not_run)
        self.assertEqual(sum(1 for t in tests if t[1] == 'FAIL'), failed)
        self.assertEqual(sum(1 for t in tests if t[1] == 'ERROR'), errors)
        for n in later:
            self.assertRegex(out, r'(?m)^FILE %s state=SKIPPED_AFTER_FAILURE tests=0 ' % _re.escape(n))
            self.assertNotRegex(out, r'(?m)^TEST %s::\S+ (PASS|FAIL|ERROR)$' % _re.escape(n))
        names = _re.findall(r'(?m)^FILE (\S+) state=', out)
        rels = [rel_prefix + n for n in names]
        self.assertEqual(E.check_output(out, 1, pins=E.test_file_pins(self.pins, rels), selected=names), [], out[-3000:])
        return not_run

    def test_f1_mut_runner_s1_inside_m4_mutants_s1(self):
        t = self.tree('mut_runner_s1.py')
        code, out, err = run_tool(t, 'm4_mutants_s1.py', ['--ids', 'FG-CMP-001'])
        self.assertEqual(code, 0, out[-2000:] + err[-1500:])
        self.assertRegex(out, r'(?m)^MUTANT FG-CMP-001 KILLED cause=arith$')
        child = self.child_run('FG-CMP-001')
        names = _re.findall(r'(?m)^FILE (\S+) state=', child)
        self.assertEqual(names[0], 'test_fin_arith.py')
        self.f11(child, 'test_fin_arith.py', names[1:], 'tests/')
        self.assertIn('FAIL arith', child.splitlines())
        self.assertIn(' mode=failfast ', child.strip().splitlines()[-1])

    def test_f7_an_m8_tier_inside_m8_mutants_s1(self):
        t = self.tree('child_unittest_runner.py')
        code, out, err = run_tool(t, 'm8_mutants_s1.py', ['--ids', 'ML-01'], timeout=3600)
        self.assertEqual(code, 0, out[-2000:] + err[-1500:])
        self.assertRegex(out, r'(?m)^MUTANT ML-01 KILLED cause=test_m8_lineage\.py$')
        child = self.child_run('ML-01')            # tier 1 only: tier 2 does not run after a tier-1 kill
        names = _re.findall(r'(?m)^FILE (\S+) state=', child)
        k = names.index('test_m8_lineage.py')
        for n in names[:k]:
            self.assertRegex(child, r'(?m)^FILE %s state=COMPLETED .* failed=0 errors=0 skipped=0 tests_not_run=0 ' % _re.escape(n))
        self.assertGreater(self.f11(child, 'test_m8_lineage.py', names[k + 1:], 'tests_m8/'), 0)
        self.assertIn(' mode=failfast ', child.strip().splitlines()[-1])

    def test_f8_child_unittest_runner_inside_sabotage_m10_s1(self):
        t = self.tree('child_unittest_runner.py')
        code, out, err = run_tool(t, 'sabotage_m10_s1.py', ['--ids', 'V01'], timeout=3600)
        self.assertEqual(code, 0, out[-2000:] + err[-1500:])
        self.assertRegex(out, r'(?m)^PLANT V01 CAUGHT ')
        child = self.child_run('V01')
        self.assertEqual(_re.findall(r'(?m)^FILE (\S+) state=', child), ['test_m10_viewmodel.py'])
        self.f11(child, 'test_m10_viewmodel.py', [], 'tests_m10/')
        self.assertIn(' mode=failfast ', child.strip().splitlines()[-1])

    def test_e17_ml01_kill_attribution_matches_m10(self):
        # corrective pass 2, E point 17 (second half): ML-01's kill attribution compared with M10's.  M10's m8_mutants runs on an M10 view
        # (test_apg_root.m10_view) with test_m8_boundary dropped from its TIER1 list, as decision M8-T drops it from the successor's: in any
        # copy of this tree M10's own control fails at that stage 1 module (E7ChildIsolationM10Halves).  Both name the same failing test.
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from test_apg_root import m10_view
        view = m10_view(os.path.join(self.tmp, 'm10'))
        _patch(os.path.join(view, 'tools', 'm8_mutants.py'), "'test_m8_layout_config', 'test_m8_boundary', ", "'test_m8_layout_config', ")
        code, out, err = run_tool(view, 'm8_mutants.py', ['--only', 'ML-01', '--jobs', '1'], site=True, timeout=3600)
        self.assertEqual(code, 0, out[-2000:] + err[-1500:])
        self.assertRegex(out, r'(?m)^CONTROL \(unmutated copy\): passes ')
        m = _re.search(r'(?m)^ML-01  KILLED +\d+s tier 1: FAIL: (\w+) \((tests_m8\.(\w+)\.\S+)\)$', out)
        self.assertTrue(m, out[-2000:])
        m10_test, m10_file = m.group(2), m.group(3) + '.py'
        self.assertTrue(m10_test.endswith('.' + m.group(1)))
        t = self.tree('child_unittest_runner.py')
        code, out, err = run_tool(t, 'm8_mutants_s1.py', ['--ids', 'ML-01'], timeout=3600)
        self.assertEqual(code, 0, out[-2000:] + err[-1500:])
        self.assertRegex(out, r'(?m)^MUTANT ML-01 KILLED cause=%s$' % _re.escape(m10_file))
        child = self.child_run('ML-01')
        self.assertEqual(_re.findall(r'(?m)^TEST %s::(\S+) FAIL$' % _re.escape(m10_file), child), [m10_test])


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
        # corrective pass 2, E point 8: M10's literal text
        self.assertRegex(out, r'(?m)^%s  TIMEOUT +\d+s tier 1 ran out of time \(neither a kill nor a survival\)$' % _re.escape(self.mid))
        self.assertRegex(out, r'(?m)^mutants 1: killed 0, documented equivalent 0, survived 0, timeout 1 \| ')
        code, out, err = self.s1('sleep')
        self.assertEqual(code, 3, out[-2000:] + err[-1500:])
        self.assertIn('MUTANT %s INDETERMINATE cause=timeout' % self.mid, out)
        self.assertRegex(out, r'(?m)^TIMEOUT %s cmd=tier1 limit=%ss ' % (self.mid, TIMEOUT_S))

    def test_crash_m8(self):
        code, out, err = self.m10('crash')
        self.assertEqual(code, 0, out[-1500:] + err[-1500:])
        self.assertRegex(out, r'(?m)^%s +KILLED ' % self.mid)
        # corrective pass 2, E point 8: M10's literal text; recorded as found: a tier that crashed with no failing test is a kill
        # attributed to tier 1 with an empty failure list
        self.assertRegex(out, r'(?m)^%s  KILLED +\d+s tier 1: \[\]$' % _re.escape(self.mid))
        self.assertRegex(out, r'(?m)^mutants 1: killed 1, documented equivalent 0, survived 0, timeout 0 \| ')
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
            out = self.s1(tool, 'failed', 0, r'CAUGHT ')
            self.assertRegex(out, r'(?m)^CONTROL start CONTROL_PASS ')
            self.assertRegex(out, r'(?m)^CONTROL end CONTROL_PASS ')
            self.assertIn(' control_end=PASS ', out.strip().splitlines()[-1])

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


# ---------------------------------------------------------------------------------------------------------------------------------------
# Corrective pass 2 (paper 23d2adb9...f0ea5, amendments 1 and 2), at tool level, in temporary copies with P's time constants shortened:
# F.1 (the disk floor during a run), F.2 (SIGINT and SIGTERM at each point), K.1 (the end control's forms) on m2_mutants_s1 and
# sabotage_m7_s1 with their children stubbed; the descendants of each run are shown gone after its RESULT line.
# ---------------------------------------------------------------------------------------------------------------------------------------
import signal as _p2sig
import time as _p2t

P2_FAST = [('T_GRACE = 10 ', 'T_GRACE = 1 '), ('T_GRACE_CANCELLED = 2 ', 'T_GRACE_CANCELLED = 1 '), ('T_ESCALATE = 10 ', 'T_ESCALATE = 2 '),
           ('T_KILL_VERIFY = 5 ', 'T_KILL_VERIFY = 2 '), ('T_EXIT_AFTER_RESULT = 2 ', 'T_EXIT_AFTER_RESULT = 1 ')]


def p2_patch_evkit(tree, extra=()):
    p = os.path.join(tree, 'tools', 'evkit.py')
    with open(p, encoding='utf-8') as fh:
        src = fh.read()
    for old, new in list(P2_FAST) + list(extra):
        assert src.count(old) == 1, old
        src = src.replace(old, new)
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write(src)


def p2_descendants(pid):
    """Every live descendant of pid: (pid, start, cwd)."""
    tab = E.proc_table()
    kids = {}
    for p, (st, pp, s) in tab.items():
        kids.setdefault(pp, []).append(p)
    out, todo = [], [pid]
    while todo:
        x = todo.pop()
        for c in kids.get(x, ()):
            try:
                cwd = os.readlink('/proc/%d/cwd' % c)
            except OSError:
                cwd = ''
            if tab[c][0] != 'Z':
                out.append((c, tab[c][2], cwd))
            todo.append(c)
    return out


def p2_run(tree, script, args, when=None, sig=_p2sig.SIGINT, again=None, delay=0.0, timeout=600):
    """Run a tool in the tree; when(descendants) -> True decides the moment to send sig (then again, if given, 0.3 s later).  Returns
    (exit code, output, the identities of the descendants seen at the signal, plus every identity seen while it ran)."""
    tmp = tempfile.mkdtemp(prefix='s1_p2r_')
    env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': tmp,
           'PYTHONDONTWRITEBYTECODE': '1'}
    p = _sp.Popen([sys.executable, '-I', '-S', os.path.join('tools', script)] + list(args), cwd=tree, env=env, stdin=_sp.DEVNULL,
                  stdout=_sp.PIPE, stderr=_sp.STDOUT, text=True, start_new_session=True)
    seen = set()
    sent = False
    t_end = _p2t.monotonic() + timeout
    try:
        while p.poll() is None and _p2t.monotonic() < t_end:
            d = p2_descendants(p.pid)
            seen |= {(x[0], x[1]) for x in d}
            if when is not None and not sent and when(d):
                if delay:
                    _p2t.sleep(delay)
                    seen |= {(x[0], x[1]) for x in p2_descendants(p.pid)}
                p.send_signal(sig)
                sent = True
                if again is not None:
                    _p2t.sleep(0.3)
                    p.send_signal(again)
            _p2t.sleep(0.05)
        out, _ = p.communicate(timeout=max(1, t_end - _p2t.monotonic()))
    finally:
        if p.poll() is None:
            os.killpg(p.pid, 9)
            p.wait()
        shutil.rmtree(tmp, ignore_errors=True)
    return p.returncode, out, seen, sent


def p2_in(needle):
    return lambda d: any(needle in x[2] for x in d)


def p2_gone(test, seen):
    for i in seen:
        st = E.proc_stat(i[0])
        test.assertFalse(st is not None and st[2] == i[1], 'a descendant is still present: %r %r' % (i, st))


P2_M2_STUB = r"""import os, sys, time, subprocess, signal
# planted by tests_tools/test_mutation_timeout.py (corrective pass 2): the m2 kill-oracle children, replaced in a temporary copy
MODE, OK, MARK = %(mode)r, %(ok)r, %(mark)r
a = sys.argv[1:]
rid = a[a.index('--run-id') + 1] if '--run-id' in a else ''
name = os.path.basename(sys.argv[0])
ctl = rid.startswith('control')
k = 0
if ctl and name == 'run_m2_tests_s1.py':
    with open(os.path.join(MARK, 'controls'), 'a') as fh:
        fh.write('x')
    k = len(open(os.path.join(MARK, 'controls')).read())
end = ctl and (k == 2 or 'control_end' in os.getcwd())
if MODE == 'end_hang' and end:
    time.sleep(60)
if (MODE == 'end_leak' and end and name == 'run_m2_tests_s1.py') or (MODE == 'end_leak_last' and end and name == 'run_contracts_s1.py'):
    subprocess.Popen([sys.executable, '-c', 'import signal, sys, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); '
                      'open(sys.argv[1], "w").close(); time.sleep(30)', os.path.join(MARK, 'leaked')])
if MODE in ('item_hang', 'item_slow') and not ctl and name == 'run_m2_tests_s1.py':
    time.sleep(60 if MODE == 'item_hang' else 3)
print(OK)
sys.exit(0)
"""


class P2MutationFamily(unittest.TestCase):
    """F.1, F.2 and K.1 at tool level, on m2_mutants_s1 (its two kill oracles stubbed) and sabotage_m7_s1 (its check stubbed)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_p2mf_')
        doc, _ = E.load_pins()
        self.ids = doc['mutation_lists']['m2_mutants_s1']['ids'][:2]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def m2_tree(self, mode, extra=()):
        tree = os.path.join(self.tmp, 'm2_' + mode)
        shutil.copytree(ROOT, tree, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
        mark = os.path.join(tree, '_p2mark')
        os.makedirs(mark)
        for f in ('run_m2_tests_s1.py', 'run_contracts_s1.py'):
            with open(os.path.join(tree, 'tools', f), 'w', encoding='utf-8') as fh:
                fh.write(P2_M2_STUB % {'mode': mode, 'ok': _stub_text('ok')[0], 'mark': mark})
        p2_patch_evkit(tree, extra)
        return tree

    def last(self, out):
        return out.strip().splitlines()[-1]

    def check(self, out, code, sel):
        self.assertEqual(E.check_output(out, code, selected=sel), [], out[-3000:])

    def test_f2_sigint_while_a_child_runs(self):
        tree = self.m2_tree('item_hang')
        code, out, seen, sent = p2_run(tree, 'm2_mutants_s1.py', ['--ids', ','.join(self.ids), '--jobs', '1'], when=p2_in('/m_'))
        self.assertTrue(sent)
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^MUTANT %s INDETERMINATE cause=interrupted$' % _re.escape(self.ids[0]))
        self.assertRegex(out, r'(?m)^MUTANT %s NOT_RUN cause=run_stopped$' % _re.escape(self.ids[1]))
        lines = out.strip().splitlines()
        self.assertEqual(lines[-2], 'INTERRUPTED signal=SIGINT at=%s received=1' % self.ids[0])
        self.assertIn(' control_end=NOT_RUN ', lines[-1])
        self.assertNotRegex(out, r'(?m)^RUN_ERROR ')
        self.check(out, code, self.ids)
        p2_gone(self, seen)

    def test_f2_a_second_signal_is_counted_without_cutting_the_output(self):
        tree = self.m2_tree('item_hang')
        code, out, seen, sent = p2_run(tree, 'm2_mutants_s1.py', ['--ids', self.ids[0]], when=p2_in('/m_'), sig=_p2sig.SIGTERM,
                                       again=_p2sig.SIGTERM)
        self.assertEqual(code, 3, out[-2000:])
        self.assertEqual(out.strip().splitlines()[-2], 'INTERRUPTED signal=SIGTERM at=%s received=2' % self.ids[0])
        self.check(out, code, [self.ids[0]])
        p2_gone(self, seen)

    def test_f2_during_the_end_control(self):
        tree = self.m2_tree('end_hang')
        code, out, seen, sent = p2_run(tree, 'm2_mutants_s1.py', ['--ids', self.ids[0]], when=p2_in('control_end'))
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^CONTROL end CONTROL_NOT_RUN cause=interrupted$')
        self.assertEqual(out.strip().splitlines()[-2], 'INTERRUPTED signal=SIGINT at=control_end received=1')
        self.assertRegex(out, r'(?m)^MUTANT %s (SURVIVED|EQUIVALENT) ' % _re.escape(self.ids[0]))     # an outcome fixed before the signal is kept
        self.assertIn(' control_end=NOT_RUN ', self.last(out))
        self.check(out, code, [self.ids[0]])
        p2_gone(self, seen)

    def test_f2_and_k1_during_the_end_controls_cleanup(self):
        # K.1: the end control's last command returned a valid result and left a background process; the interrupt comes during its
        # cleanup: control_end=FAIL cause=processes_left (a completed outcome), and the signal is SIGNAL_AFTER_COMPLETION
        tree = self.m2_tree('end_leak_last')
        code, out, seen, sent = p2_run(tree, 'm2_mutants_s1.py', ['--ids', self.ids[0]],
                                       when=lambda d: os.path.exists(os.path.join(tree, '_p2mark', 'leaked')), delay=1.5)
        self.assertTrue(sent)
        self.assertRegex(out, r'(?m)^CONTROL end CONTROL_FAIL cause=processes_left ')
        self.assertRegex(out, r'(?m)^SIGNAL_AFTER_COMPLETION signal=SIGINT$')
        self.assertNotIn('INTERRUPTED', out)
        self.assertIn(' control_end=FAIL ', self.last(out))
        self.assertRegex(out, r'(?m)^CLEANUP control_end:run_contracts_s1 ')
        self.check(out, code, [self.ids[0]])
        p2_gone(self, seen)

    def test_reading_7_an_interrupt_during_an_earlier_commands_cleanup(self):
        # AM2-4 reading 7: a leak found by the cleanup of an otherwise successful earlier command fixes the end control at that
        # cleanup's end, so an interrupt during that cleanup comes before the outcome is fixed: CONTROL_NOT_RUN cause=interrupted
        tree = self.m2_tree('end_leak')
        code, out, seen, sent = p2_run(tree, 'm2_mutants_s1.py', ['--ids', self.ids[0]],
                                       when=lambda d: os.path.exists(os.path.join(tree, '_p2mark', 'leaked')), delay=1.5)
        self.assertTrue(sent)
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^CONTROL end CONTROL_NOT_RUN cause=interrupted$')
        self.assertRegex(out, r'(?m)^CLEANUP control_end:run_m2_tests_s1 .* killed=\d+:\d+ ')
        self.assertEqual(out.strip().splitlines()[-2], 'INTERRUPTED signal=SIGINT at=control_end received=1')
        self.assertIn(' control_end=NOT_RUN ', self.last(out))
        self.assertNotIn('run_contracts_s1=', [l for l in out.splitlines() if l.startswith('CONTROL end')][0])
        self.check(out, code, [self.ids[0]])
        p2_gone(self, seen)

    def test_f2_between_items(self):
        hold = ('        def begin(mid):\n            with flock:\n',
                '        def begin(mid):\n            if begun[0] == 1:\n                open(os.path.join(root, "_p2mark", "between"), "w")'
                '.close()\n                _time.sleep(3)\n            with flock:\n')
        tree = self.m2_tree('ok', extra=[hold])
        code, out, seen, sent = p2_run(tree, 'm2_mutants_s1.py', ['--ids', ','.join(self.ids), '--jobs', '1'],
                                       when=lambda d: os.path.exists(os.path.join(tree, '_p2mark', 'between')))
        self.assertEqual(code, 3, out[-2000:])
        self.assertEqual(out.strip().splitlines()[-2], 'INTERRUPTED signal=SIGINT at=between received=1')
        self.assertRegex(out, r'(?m)^MUTANT %s NOT_RUN cause=run_stopped$' % _re.escape(self.ids[1]))
        self.check(out, code, self.ids)

    def disk_at(self, n):
        return [('    free = shutil.disk_usage(os.path.dirname(dest) or \'.\').free\n',
                 '    _P2N.append(1)\n    if len(_P2N) == %d:\n        raise RunError(\'ENV_DISK_BELOW_FLOOR\', \'free=1 floor=2\')\n'
                 '    free = shutil.disk_usage(os.path.dirname(dest) or \'.\').free\n' % n),
                ('def fresh_copy(root, dest,', '_P2N = []\n\n\ndef fresh_copy(root, dest,')]

    def test_f1_the_floor_during_the_items_with_jobs_2(self):
        # copy 1 is the start control's, 2 and 3 the two items': the second item's copy is refused while the first is in flight
        tree = self.m2_tree('item_slow', extra=self.disk_at(3))
        code, out, seen, sent = p2_run(tree, 'm2_mutants_s1.py', ['--ids', ','.join(self.ids), '--jobs', '2'])
        self.assertEqual(code, 2, out[-2000:])
        for mid in self.ids:
            self.assertRegex(out, r'(?m)^MUTANT %s INDETERMINATE cause=run_stopped$' % _re.escape(mid))
        self.assertRegex(out, r'(?m)^RUN_ERROR ENV_DISK_BELOW_FLOOR items free=1 floor=2$')
        self.assertIn(' control_end=NOT_RUN ', self.last(out))
        self.assertNotRegex(out, r'(?m)^CONTROL end ')
        self.check(out, code, self.ids)
        p2_gone(self, seen)

    def test_f1_the_floor_at_the_start_controls_copy(self):
        tree = self.m2_tree('ok', extra=self.disk_at(1))
        code, out, seen, sent = p2_run(tree, 'm2_mutants_s1.py', ['--ids', ','.join(self.ids)])
        self.assertEqual(code, 2, out[-2000:])
        self.assertRegex(out, r'(?m)^CONTROL start CONTROL_FAIL cause=disk_below_floor$')
        self.assertRegex(out, r'(?m)^RUN_ERROR ENV_DISK_BELOW_FLOOR control_start free=1 floor=2$')
        self.assertIn(' control_start=FAIL ', self.last(out))
        for mid in self.ids:
            self.assertRegex(out, r'(?m)^MUTANT %s NOT_RUN ' % _re.escape(mid))
        self.check(out, code, self.ids)

    def test_f1_the_floor_at_the_end_controls_copy(self):
        tree = self.m2_tree('ok', extra=self.disk_at(3))
        code, out, seen, sent = p2_run(tree, 'm2_mutants_s1.py', ['--ids', self.ids[0]])
        self.assertEqual(code, 2, out[-2000:])
        self.assertRegex(out, r'(?m)^MUTANT %s (SURVIVED|EQUIVALENT) ' % _re.escape(self.ids[0]))         # the item line is kept
        self.assertRegex(out, r'(?m)^CONTROL end CONTROL_NOT_RUN cause=disk_below_floor$')
        self.assertRegex(out, r'(?m)^RUN_ERROR ENV_DISK_BELOW_FLOOR control_end free=1 floor=2$')
        self.assertIn(' control_end=NOT_RUN ', self.last(out))
        self.check(out, code, [self.ids[0]])

    def sab_tree(self, mode, extra=()):
        tree = os.path.join(self.tmp, 'm7_' + mode)
        pid = sabotage_tree(tree, 'm7', mode)
        p2_patch_evkit(tree, extra)
        return tree, pid

    def test_sabotage_m7_f2_sigint_and_sigterm_while_a_child_runs(self):
        for sig in (_p2sig.SIGINT, _p2sig.SIGTERM):
            with self.subTest(sig=sig):
                tree, pid = self.sab_tree('sleep')
                code, out, seen, sent = p2_run(tree, 'sabotage_m7_s1.py', ['--ids', pid], when=p2_in('/m_'), sig=sig)
                shutil.rmtree(tree, ignore_errors=True)
                self.assertEqual(code, 3, out[-2000:])
                self.assertRegex(out, r'(?m)^PLANT %s INDETERMINATE cause=interrupted$' % _re.escape(pid))
                self.assertEqual(out.strip().splitlines()[-2], 'INTERRUPTED signal=%s at=%s received=1' % (sig.name, pid))
                self.assertEqual(E.check_output(out, code, selected=[pid]), [], out[-3000:])
                p2_gone(self, seen)

    def test_sabotage_m7_f1_the_floor_at_the_end_controls_copy(self):
        tree, pid = self.sab_tree('failed', extra=self.disk_at(3))
        code, out, seen, sent = p2_run(tree, 'sabotage_m7_s1.py', ['--ids', pid])
        self.assertEqual(code, 2, out[-2000:])
        self.assertRegex(out, r'(?m)^CONTROL end CONTROL_NOT_RUN cause=disk_below_floor$')
        self.assertRegex(out, r'(?m)^RUN_ERROR ENV_DISK_BELOW_FLOOR control_end ')
        self.assertEqual(E.check_output(out, code, selected=[pid]), [], out[-3000:])

    def test_sabotage_m7_f1_the_floor_at_the_start_controls_copy(self):
        tree, pid = self.sab_tree('failed', extra=self.disk_at(1))
        code, out, seen, sent = p2_run(tree, 'sabotage_m7_s1.py', ['--ids', pid])
        self.assertEqual(code, 2, out[-2000:])
        self.assertRegex(out, r'(?m)^CONTROL start CONTROL_FAIL cause=disk_below_floor$')
        self.assertEqual(E.check_output(out, code, selected=[pid]), [], out[-3000:])


if __name__ == '__main__':
    unittest.main()
