"""Stage 1 (APG-M11-S1), Workstream T, P1-F7, AX-4 and T-0 (DP-2.1 (a)): a timeout is never a kill, and a crash is never a kill.
Helper level (tools/evkit.map_mutant, map_plant, classify_timeout, run_child); M10's behaviour is shown on its own m2 tool; and the census
of every mutation tool's source (Census).
Run from the package root:  python3 -I -S tests_tools/test_no_timeout_kill.py      BUILDER-EXECUTED: NOT INDEPENDENT."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402


def env():
    return {'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': tempfile.gettempdir(),
            'PYTHONDONTWRITEBYTECODE': '1'}


class SuccessorNeverCountsATimeoutOrCrash(unittest.TestCase):
    def test_timeout_is_indeterminate_in_every_kind(self):
        for kind in ('mutation', 'sabotage', 'cases', 'tests'):
            (o, cause), line = E.classify_timeout(kind, 'M1', 'run_m2_tests_s1', 300, {('start', 'run_m2_tests_s1'): 12.5})
            self.assertEqual((o, cause), ('INDETERMINATE', 'timeout'), kind)
            if kind in ('mutation', 'sabotage'):
                self.assertEqual(line, 'TIMEOUT M1 cmd=run_m2_tests_s1 limit=300s control_start=12.500s control_end=NA')
            else:
                self.assertIsNone(line)  # R7: no same-load control exists for cases and tests

    def test_mapping(self):
        self.assertEqual(E.map_mutant('TIMEOUT', 'run_m2_tests_s1'), ('INDETERMINATE', 'timeout'))
        self.assertEqual(E.map_mutant('CRASH_NO_RESULT', 'run_m2_tests_s1'), ('INDETERMINATE', 'crash_no_result'))
        self.assertEqual(E.map_mutant('CHILD_INDETERMINATE', 'x'), ('INDETERMINATE', 'child_indeterminate'))
        self.assertEqual(E.map_mutant('CHILD_EVIDENCE_ERROR', 'x'), ('ITEM_ERROR', 'child_evidence_error'))
        self.assertEqual(E.map_mutant('LAUNCH_ERROR', 'x'), ('ITEM_ERROR', 'launch_error'))
        self.assertEqual(E.map_mutant('CHILD_FAILED', 'run_m2_tests_s1'), ('KILLED', 'run_m2_tests_s1'))
        self.assertEqual(E.map_mutant('CHILD_OK', None), ('SURVIVED', 'none'))
        self.assertEqual(E.map_mutant('CHILD_OK', None, equivalent=True), ('EQUIVALENT', 'documented'))
        self.assertEqual(E.map_plant('TIMEOUT', 'x'), ('INDETERMINATE', 'timeout'))
        self.assertEqual(E.map_plant('CRASH_NO_RESULT', 'x'), ('INDETERMINATE', 'crash_no_result'))
        self.assertEqual(E.map_plant('CHILD_FAILED', 'x'), ('CAUGHT', 'x'))
        self.assertEqual(E.map_plant('CHILD_OK', None), ('MISSED', 'none'))

    def test_run_child_timeout_and_crash(self):
        o = E.run_child([sys.executable, '-I', '-S', '-c', 'import time; time.sleep(5)'], 0.5, env(), ROOT)[0]
        self.assertEqual(o, 'TIMEOUT')
        o = E.run_child([sys.executable, '-I', '-S', '-c', 'import os; os.abort()'], 30, env(), ROOT)[0]
        self.assertEqual(o, 'CRASH_NO_RESULT')
        o = E.run_child([sys.executable, '-I', '-S', '-c', 'raise SystemExit(1)'], 30, env(), ROOT)[0]
        self.assertEqual(o, 'CRASH_NO_RESULT')  # a non-zero exit with no RESULT line is a crash, never a failure (so never a kill)
        o = E.run_child(['/nonexistent/interpreter'], 30, env(), ROOT)[0]
        self.assertEqual(o, 'LAUNCH_ERROR')

    def test_killed_by_a_signal_after_printing_a_result_is_still_a_crash(self):
        lines, _ = E.finish_tests('t', 'full', 'r', ['a.py'], {}, {'a.py': {'sha256': '0' * 64, 'ids': []}})
        code = 'import os\nprint(%r, flush=True)\nos.kill(os.getpid(), 9)' % '\n'.join(lines)
        self.assertEqual(E.run_child([sys.executable, '-I', '-S', '-c', code], 30, env(), ROOT)[0], 'CRASH_NO_RESULT')


class M10CountsATimeoutAsAKill(unittest.TestCase):
    """The M10 behaviour the fix removes: m2_mutants.run_one returns KILLED (by timeout) when its child times out (m2_mutants.py:240-243),
    and KILLED when the child exits non-zero for any reason, a crash included (:244-245)."""

    def setUp(self):
        spec = importlib.util.spec_from_file_location('m10_m2_mutants', os.path.join(ROOT, 'tools', 'm2_mutants.py'))
        self.m2 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m2)
        self.item = [m for m in self.m2.MUT if m[0] == 'CA03-keys-not-sorted'][0]
        self.tmp = tempfile.mkdtemp(prefix='s1_m10_')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_m10_timeout_is_killed(self):
        with mock.patch.object(self.m2.subprocess, 'run', side_effect=subprocess.TimeoutExpired('x', 300)), \
                mock.patch.object(self.m2.shutil, 'copytree', side_effect=lambda src, dst, **k: os.makedirs(os.path.join(dst, 'apg'))):
            self.assertEqual(self.m2.run_one(self.item, self.tmp), ('CA03-keys-not-sorted', 'KILLED', 'timeout'))

    def test_m10_crash_is_killed(self):
        crash = subprocess.CompletedProcess(args='x', returncode=-11, stdout='', stderr='Segmentation fault')
        with mock.patch.object(self.m2.subprocess, 'run', return_value=crash), \
                mock.patch.object(self.m2.shutil, 'copytree', side_effect=lambda src, dst, **k: os.makedirs(os.path.join(dst, 'apg'))):
            self.assertEqual(self.m2.run_one(self.item, self.tmp), ('CA03-keys-not-sorted', 'KILLED', 'tests'))



def census_problems(path):
    """The census rule (P1-F7 (R4), AX-4), read from the source without importing it: a handler for TimeoutExpired that returns a value or
    names a kill; a run_tests, run_tier or run_one of the tool's own that starts a child itself (subprocess) instead of through
    tools/evkit.run_child; any direct use of subprocess.  Returns the problems as strings."""
    import ast
    with open(path, encoding='utf-8') as fh:
        tree = ast.parse(fh.read())
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is not None and 'TimeoutExpired' in ast.dump(node.type):
            body = ast.dump(ast.Module(body=node.body, type_ignores=[]))
            if any(isinstance(n, ast.Return) and n.value is not None for b in node.body for n in ast.walk(b)) or 'KILLED' in body:
                out.append('line %d: a TimeoutExpired handler returns a result' % node.lineno)
        if isinstance(node, ast.FunctionDef) and node.name in ('run_tests', 'run_tier', 'run_one'):
            text = ast.dump(node)
            if 'subprocess' in text and 'run_child' not in text:
                out.append('line %d: %s starts its own child, not through evkit.run_child' % (node.lineno, node.name))
        if isinstance(node, (ast.Import, ast.ImportFrom)) and any(a.name == 'subprocess' for a in node.names):
            out.append('line %d: imports subprocess' % node.lineno)
    return out


class Census(unittest.TestCase):
    """P1-F7 (R4), P4-B13, P5-S08, AX-4: the census.  Every M10 mutation tool has a successor tools/<name>_s1.py (DP-1.2 (B): M10's own
    file stays byte-identical), and no successor contains a TimeoutExpired handler that returns a kill or starts a child of its own: each
    goes through tools/evkit.mutation_main, whose children run through run_child.  On M10 the same census finds the pattern in every tool
    of the inventory that defines its own runner (rows 1 to 9, 11, 13 and 15; rows 10, 12 and 14 inherit their parent's)."""

    M10_WITH_OWN_RUNNER = {'m2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm73_store', 'm91', 'f67', 'f672', 'mie', 'm8'}

    def tools(self):
        return sorted(f[:-len('_mutants.py')] for f in os.listdir(os.path.join(ROOT, 'tools')) if f.endswith('_mutants.py'))

    def test_every_m10_mutation_tool_has_a_successor_and_the_successors_are_clean(self):
        tools = self.tools()
        self.assertEqual(len(tools), 16)
        for t in tools:
            with self.subTest(tool=t):
                s1 = os.path.join(ROOT, 'tools', '%s_mutants_s1.py' % t)
                self.assertTrue(os.path.exists(s1), t)
                self.assertEqual(census_problems(s1), [])
                with open(s1, encoding='utf-8') as fh:
                    self.assertIn('E.mutation_main(', fh.read())

    def test_the_census_finds_the_m10_pattern(self):
        found = {t for t in self.tools() if census_problems(os.path.join(ROOT, 'tools', '%s_mutants.py' % t))}
        self.assertEqual(found, self.M10_WITH_OWN_RUNNER)
        self.assertTrue(any('TimeoutExpired handler returns' in x for x in census_problems(os.path.join(ROOT, 'tools', 'm6_mutants.py'))))

    def test_the_census_would_catch_a_successor_that_kept_the_pattern(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'x_mutants_s1.py')
            with open(p, 'w') as fh:
                fh.write('import subprocess\ndef run_tests(w):\n    try:\n        subprocess.run(["x"], timeout=1)\n'
                         '    except subprocess.TimeoutExpired:\n        return "timeout"\n')
            self.assertEqual(len(census_problems(p)), 3)


if __name__ == '__main__':
    unittest.main()
