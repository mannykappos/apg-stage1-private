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

    def test_the_census_of_tools_evkit(self):
        # the successors' shared runner lives in tools/evkit.py, which must start children itself.  Corrective pass 2 (P.9): every
        # child start is a unit under P.  Its census: the only function that starts a subprocess is run_unit (through the Popen hook,
        # registered under the lock), and the only one that forks is run_forked; no TimeoutExpired handler remains (the deadline is the
        # unit's own, polled); a unit's timeout is how='timeout', which run_child returns as TIMEOUT, and the shared mappings turn that
        # outcome into INDETERMINATE, never a kill, a catch or a pass
        import ast
        path = os.path.join(ROOT, 'tools', 'evkit.py')
        with open(path, encoding='utf-8') as fh:
            tree = ast.parse(fh.read())
        starts, forks, handlers = set(), set(), []

        def visit(node, fname):
            for n in ast.iter_child_nodes(node):
                name = ((fname + '.') if fname else '') + n.name if isinstance(n, ast.FunctionDef) else fname     # e.g. outer.inner
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) \
                        and n.func.value.id in ('subprocess', '_subprocess') and n.func.attr in ('run', 'Popen', 'call', 'check_call',
                                                                                              'check_output'):
                    starts.add(name)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) \
                        and n.func.value.id == 'os' and n.func.attr in ('fork', 'system', 'popen', 'spawnv', 'posix_spawn', 'execv'):
                    forks.add(name)
                if isinstance(n, ast.ExceptHandler) and n.type is not None and 'TimeoutExpired' in ast.dump(n.type):
                    handlers.append((name, ast.unparse(n)))
                visit(n, name)
        visit(tree, None)
        self.assertEqual(starts, {'run_unit'})
        self.assertEqual(forks, {'run_forked'})
        self.assertEqual(handlers, [])
        src = ast.unparse([n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run_child'][0])
        self.assertIn("return ('TIMEOUT'", src)
        for word in ("'KILLED'", "'CAUGHT'", "'PASS'"):
            self.assertNotIn(word, src)
        self.assertEqual(E.map_mutant('TIMEOUT', None), ('INDETERMINATE', 'timeout'))
        self.assertEqual(E.map_plant('TIMEOUT', None)[0], 'INDETERMINATE')
        self.assertEqual(E.check_outcome(None, False, timed_out=True)[0], 'INDETERMINATE')

    def test_the_census_would_catch_a_successor_that_kept_the_pattern(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'x_mutants_s1.py')
            with open(p, 'w') as fh:
                fh.write('import subprocess\ndef run_tests(w):\n    try:\n        subprocess.run(["x"], timeout=1)\n'
                         '    except subprocess.TimeoutExpired:\n        return "timeout"\n')
            self.assertEqual(len(census_problems(p)), 3)


# ---------------------------------------------------------------------------------------------------------------------------------------
# Corrective pass 2, section P (paper 23d2adb9...f0ea5 as amended by amendments 1 and 2): the process model's own tests (P.10, AM-4, AM-5,
# AM-6), at helper level, in this process (which imported tools.evkit, so it is a child subreaper with the Popen hook).  The time constants
# are shortened for the tests (P5Times); every identity a test records is shown gone (not alive, not a zombie) afterwards.
# ---------------------------------------------------------------------------------------------------------------------------------------
import json as _json
import signal as _sig
import threading as _thr
import time as _t

PY = sys.executable


def p2_alive(ident):
    st = E.proc_stat(ident[0])
    return st is not None and st[2] == ident[1] and st[0] != 'Z'


def p2_exists(ident):
    st = E.proc_stat(ident[0])
    return st is not None and st[2] == ident[1]


def p2_read_idents(path):
    out = []
    if os.path.exists(path):
        with open(path) as fh:
            for l in fh:
                if l.strip():
                    pid, start = l.split()
                    out.append((int(pid), int(start)))
    return out


# a child script fragment: record this process's identity (pid and start time) in a file
P2_REC = ('import os\n'
          'def rec(path):\n'
          '    d = open("/proc/self/stat").read(); s = d[d.rindex(")") + 2:].split()[19]\n'
          '    open(path, "a").write("%d %s\\n" % (os.getpid(), s))\n')


class P2Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix='s1_p2_')
        self.rec = os.path.join(self.d, 'ids.txt')
        self.saved = (E.T_GRACE, E.T_GRACE_CANCELLED, E.T_ESCALATE, E.T_KILL_VERIFY, E.T_EXIT_AFTER_RESULT)
        E.T_GRACE, E.T_GRACE_CANCELLED, E.T_ESCALATE, E.T_KILL_VERIFY, E.T_EXIT_AFTER_RESULT = 1, 1, 2, 2, 1
        E._SUP.reset()
        E._SUP.send = None
        E._SUP.table = E.proc_table
        E._SUP.supervisor = True
        E._SUP.tool = 'p2test'

    def tearDown(self):
        E.T_GRACE, E.T_GRACE_CANCELLED, E.T_ESCALATE, E.T_KILL_VERIFY, E.T_EXIT_AFTER_RESULT = self.saved
        E._SUP.send = None
        E._SUP.table = E.proc_table
        for i in p2_read_idents(self.rec):       # never leave anything behind, whatever a test did
            try:
                if p2_alive(i):
                    os.kill(i[0], 9)
            except OSError:
                pass
        E._SUP.reap_exited_orphans()
        E._SUP.supervisor = False
        E._SUP.reset()
        import shutil
        shutil.rmtree(self.d, ignore_errors=True)

    def script(self, name, body):
        p = os.path.join(self.d, name)
        with open(p, 'w') as fh:
            fh.write(P2_REC + body)
        return p

    def assert_all_gone(self, idents):
        self.assertTrue(idents, 'the test recorded no identities')
        for i in idents:
            self.assertFalse(p2_exists(i), 'still present (alive or an unreaped zombie): %r %r' % (i, E.proc_stat(i[0])))

    def env(self):
        return E.clean_env(self.d)


class P2SubprocessUnits(P2Base):
    def test_the_supervisor_is_a_subreaper_and_supervision_is_available(self):
        self.assertTrue(E.is_subreaper())
        self.assertIsNone(E._SUP.problem)
        self.assertEqual(E.supervision_errors(), [])

    def test_normal_path_background_grandchild_after_a_passing_result_is_a_leak(self):
        s = self.script('bg.py', 'import subprocess, sys\nrec(%r)\n'
                                 'subprocess.Popen([sys.executable, "-c", %r])\nprint("ok")\n'
                        % (self.rec, P2_REC + 'rec(%r)\nimport time\ntime.sleep(60)\n' % self.rec))
        r = E.run_unit('u1', [PY, '-I', '-S', s], 30, self.env(), self.d)
        self.assertEqual((r.how, r.returncode, r.stdout.strip()), ('exit', 0, 'ok'))
        self.assertTrue(r.leaked)
        self.assert_all_gone(p2_read_idents(self.rec))
        lines = E._SUP.final_lines()
        self.assertTrue(lines[0].startswith('CLEANUP u1 by=p2test:%d child=' % os.getpid()), lines)
        self.assertIn('CLEANUP_SUMMARY units=1 leaked=1 remaining=0', lines)
        self.assertEqual(E.run_child([PY, '-I', '-S', s], 30, self.env(), self.d, unit='u2')[0], 'PROCESSES_LEFT')

    def test_hang_timeout_and_setsid_double_fork_are_contained(self):
        inner = P2_REC + 'import os, time\nrec(%r)\nos.setsid()\nif os.fork() == 0:\n    rec(%r)\n    time.sleep(60)\nos._exit(0)\n' % (
            self.rec, self.rec)
        s = self.script('hang.py', 'import subprocess, sys, time\nrec(%r)\nsubprocess.Popen([sys.executable, "-c", %r])\n'
                                   'time.sleep(60)\n' % (self.rec, inner))
        t0 = _t.monotonic()
        r = E.run_unit('u1', [PY, '-I', '-S', s], 2, self.env(), self.d)
        self.assertEqual(r.how, 'timeout')
        self.assertLess(_t.monotonic() - t0, 2 + E.T_GRACE + E.T_KILL_VERIFY + 3)
        ids = p2_read_idents(self.rec)
        self.assertEqual(len(ids), 3, ids)       # the child, its setsid child, and that one's double-forked child
        self.assert_all_gone(ids)
        self.assertEqual(E.run_child([PY, '-I', '-S', s], 1, self.env(), self.d, unit='u2')[0], 'TIMEOUT')

    def test_a_member_that_ignores_sigterm_is_killed(self):
        s = self.script('ign.py', 'import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\nrec(%r)\ntime.sleep(60)\n'
                        % self.rec)
        r = E.run_unit('u1', [PY, '-I', '-S', s], 1, self.env(), self.d)
        self.assertEqual(r.how, 'timeout')
        self.assert_all_gone(p2_read_idents(self.rec))
        rec = [l for l in E._SUP.final_lines() if l.startswith('CLEANUP u1 ')][0]
        self.assertIn(' sigkill=1 ', rec)
        self.assertIn(' deadline=grace ', rec)

    def test_a_member_that_cannot_be_killed_is_cleanup_incomplete(self):
        s = self.script('ign.py', 'import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\nrec(%r)\ntime.sleep(60)\n'
                        % self.rec)
        real = E._send_pidfd
        E._SUP.send = lambda ident, sig: False if sig == _sig.SIGKILL else real(ident, sig)     # simulated: SIGKILL does not take
        t0 = _t.monotonic()
        r = E.run_unit('u1', [PY, '-I', '-S', s], 1, self.env(), self.d)
        # the run does not wait on it: bounded by the grace, the kill verification, the settling and the drain (each T_KILL_VERIFY)
        self.assertLess(_t.monotonic() - t0, 1 + E.T_GRACE + 3 * E.T_KILL_VERIFY + 2)
        E._SUP.send = None
        ids = p2_read_idents(self.rec)
        self.assertTrue(p2_alive(ids[0]))
        errs = E._SUP.close_run()
        self.assertTrue(any(e.code == 'CLEANUP_INCOMPLETE' and e.detail.startswith('u1 ') for e in errs), [e.line() for e in errs])
        self.assertIn('remaining=1', E._SUP.final_lines()[-1])
        out, code = E.finish_items('mutation', 't', 'r', ['m1'], {'m1': ('KILLED', 'c')}, run_errors=errs)
        self.assertEqual(code, 2)

    def test_what_a_unit_child_inherits(self):
        # P.2 and AM-4: descriptors 0, 1 and 2 only, 0 on /dev/null; the environment exactly the one given; its own process group
        r_fd, w_fd = os.pipe()
        os.environ['APG_P2_PARENT_ONLY'] = 'secret-not-for-children'
        try:
            s = self.script('inh.py', 'import os, json\nprint(json.dumps({"fds": sorted(int(x) for x in os.listdir("/proc/self/fd")), '
                                      '"stdin": os.readlink("/proc/self/fd/0"), "env": sorted(os.environ), '
                                      '"pgid": os.getpgid(0), "pid": os.getpid()}))\n')
            r = E.run_unit('u1', [PY, '-I', '-S', s], 30, self.env(), self.d)
            info = _json.loads(r.stdout)
            self.assertEqual([f for f in info['fds'] if f > 2], [3])     # the listing's own descriptor only
            self.assertEqual(info['stdin'], '/dev/null')
            self.assertEqual(info['env'], sorted(self.env()))
            self.assertEqual(info['pgid'], info['pid'])
        finally:
            os.close(r_fd)
            os.close(w_fd)
            del os.environ['APG_P2_PARENT_ONLY']

    def test_the_registration_race_child_exits_immediately(self):
        # the reaper scans at the same moment as the creation; the child's status is collected only by its own handle
        stop = [False]

        def scanner():
            while not stop[0]:
                E._SUP.scan()
        th = _thr.Thread(target=scanner)
        th.start()
        try:
            for i in range(20):
                r = E.run_unit('u%d' % i, [PY, '-I', '-S', '-c', 'raise SystemExit(7)'], 30, self.env(), self.d)
                self.assertEqual((r.how, r.returncode), ('exit', 7))
        finally:
            stop[0] = True
            th.join()
        self.assertEqual(E._SUP.adopted, {})

    def test_the_registration_race_with_the_window_widened(self):
        # corrective pass 2, mistake 29: the same race made deterministic.  The reaper's table read is made slow, so a direct child is
        # always reaped by its own handle between the reaper's table read and its pruning of reaped registrations; the reaper must
        # still never take it for an adopted orphan (P.4), because the pruning comes before the read
        real = E._SUP.table

        def slow_table():
            t = real()
            _t.sleep(0.02)
            return t
        E._SUP.table = slow_table
        stop = [False]

        def scanner():
            while not stop[0]:
                E._SUP.scan()
                _t.sleep(0.001)
        th = _thr.Thread(target=scanner)
        th.start()
        try:
            for i in range(20):
                r = E.run_unit('w%d' % i, [PY, '-I', '-S', '-c', 'raise SystemExit(7)'], 30, self.env(), self.d)
                self.assertEqual((r.how, r.returncode), ('exit', 7))
        finally:
            stop[0] = True
            th.join()
        self.assertEqual(E._SUP.adopted, {})

    def test_wait_ownership_two_concurrent_units_and_an_adopted_zombie(self):
        orphan = P2_REC + 'import time\nrec(%r)\ntime.sleep(0.5)\n' % self.rec
        a = self.script('a.py', 'import subprocess, sys, time\nsubprocess.Popen([sys.executable, "-c", %r])\ntime.sleep(0.2)\n'
                                'raise SystemExit(3)\n' % orphan)
        b = self.script('b.py', 'import time\ntime.sleep(1.5)\nraise SystemExit(4)\n')
        res = {}

        def go(k, s):
            res[k] = E.run_unit(k, [PY, '-I', '-S', s], 30, self.env(), self.d)
        ths = [_thr.Thread(target=go, args=('ua', a)), _thr.Thread(target=go, args=('ub', b))]
        [t.start() for t in ths]
        [t.join() for t in ths]
        self.assertEqual((res['ua'].returncode, res['ub'].returncode), (3, 4))      # each status collected by its own handle
        ids = p2_read_idents(self.rec)
        self.assert_all_gone(ids)                       # the adopted orphan exited and was reaped by the reaper
        self.assertTrue(set(ids) <= E._SUP.reaped_orphans)
        for i in ids:
            with self.assertRaises(ChildProcessError):
                os.waitpid(i[0], os.WNOHANG)

    def test_concurrent_orphan_attribution_and_an_unrelated_process_survives(self):
        unrelated = subprocess.Popen(['sleep', '30'], start_new_session=True)
        try:
            u_ident = (unrelated.pid, E.proc_stat(unrelated.pid)[2])
            g = self.script('g.py', 'import time\nrec(%r)\ntime.sleep(60)\n' % self.rec)
            m = self.script('m.py', 'import subprocess, sys\nsubprocess.Popen([sys.executable, %r])\n' % g)     # exits at once: g is orphaned
            a = self.script('a.py', 'import subprocess, sys, time\np = subprocess.Popen([sys.executable, %r])\np.wait()\ntime.sleep(1)\n' % m)
            b = self.script('b.py', 'import time\ntime.sleep(2)\n')
            res = {}

            def go(k, s):
                res[k] = E.run_unit(k, [PY, '-I', '-S', s], 30, self.env(), self.d)
            ths = [_thr.Thread(target=go, args=('ua', a)), _thr.Thread(target=go, args=('ub', b))]
            [t.start() for t in ths]
            [t.join() for t in ths]
            self.assert_all_gone(p2_read_idents(self.rec))
            self.assertTrue(p2_alive(u_ident))         # outside the supervisor's tree: never touched
            # P.3: the orphan, created and orphaned between scans, is attributed conservatively to every unit in flight; whichever
            # unit's cleanup finds it alive at its step 3 records the leak (P.6) and kills it
            g_ident = p2_read_idents(self.rec)[0]
            self.assertEqual(sorted(o.id for o in E._SUP.adopted[g_ident]), ['ua', 'ub'])
            self.assertTrue(res['ua'].leaked or res['ub'].leaked)
            recs = [l for l in E._SUP.final_lines() if l.startswith('CLEANUP ')]
            self.assertTrue(any(('%d:%d' % g_ident) in l for l in recs), recs)
        finally:
            unrelated.kill()
            unrelated.wait()


class P2Identity(P2Base):
    def test_a_reused_pid_is_never_signalled(self):
        p = subprocess.Popen(['sleep', '30'])
        try:
            st = E.proc_stat(p.pid)
            self.assertFalse(E._send_pidfd((p.pid, st[2] + 1), _sig.SIGKILL))     # a remembered identity whose start differs
            self.assertTrue(p2_alive((p.pid, st[2])))
        finally:
            p.kill()
            p.wait()

    def test_a_reused_parent_pid_with_a_child_of_its_own_is_not_a_member(self):
        o = E._Owner(E._SUP, 'sim', 'unit')
        o.members[(100, 50)] = (os.getpid(), None)     # a recorded member, pid 100 started at tick 50
        # pid 100 is now an unrelated process (start 80) with a child 101 of its own
        E._SUP.table = lambda: {100: ('S', 1, 80), 101: ('S', 100, 90)}
        self.assertEqual(E._SUP._members(o, E._SUP.table()), set())

    def test_equal_start_times_are_ambiguous_and_recorded(self):
        o = E._Owner(E._SUP, 'sim', 'unit')
        o.members[(200, 60)] = (os.getpid(), None)
        E._SUP.table = lambda: {200: ('S', 1, 60), 201: ('S', 200, 60)}       # 200 is not a registered direct child
        self.assertEqual(E._SUP._members(o, E._SUP.table()), {(200, 60)})
        self.assertEqual(o.ambiguous, {(201, 60): (200, 60)})


class P2ForkedUnits(P2Base):
    def run_f(self, fn, timeout=10, **kw):
        return E.run_forked('f', fn, timeout, self.env(), **kw)

    def test_message_forms_and_classification(self):
        forms = {'failed': lambda v: isinstance(v, list), 'exception': lambda v: isinstance(v, str),
                 'child_error': lambda v: isinstance(v, str)}
        self.assertEqual(E.parse_forked_message(self.run_f(lambda: {'failed': ['a']}), forms), ('ok', ('failed', ['a'])))

        def boom():
            raise KeyError('x')
        self.assertEqual(E.parse_forked_message(self.run_f(boom), forms), ('ok', ('exception', 'KeyError')))

        def crash():
            os._exit(1)
        self.assertEqual(E.parse_forked_message(self.run_f(crash), forms)[0], 'crash')

        def seventy():
            os._exit(70)
        self.assertEqual(E.parse_forked_message(self.run_f(seventy), forms)[0], 'child_error')

        def unencodable():
            return {'failed': {1, 2}}            # a set: json cannot encode it -> the child writes child_error
        self.assertEqual(E.parse_forked_message(self.run_f(unencodable), forms), ('ok', ('child_error', 'TypeError')))

        def killed_while_writing():
            os.write(3 if False else 1, b'')
            os.kill(os.getpid(), 9)
        self.assertEqual(E.parse_forked_message(self.run_f(killed_while_writing), forms)[0], 'crash')

        def hangs():
            _t.sleep(60)
        self.assertEqual(E.parse_forked_message(self.run_f(hangs, timeout=1), forms)[0], 'timeout')

    def test_framing_limit(self):
        forms = {'failed': lambda v: True}
        big = 'x' * (E.FORK_MESSAGE_MAX - len('{"failed": ""}'))
        self.assertEqual(E.parse_forked_message(self.run_f(lambda: {'failed': big}), forms)[0], 'ok')
        self.assertEqual(E.parse_forked_message(self.run_f(lambda: {'failed': big + 'y'}), forms)[0], 'bad_result')

    def test_valid_result_then_hangs(self):
        rec = self.rec

        def child():
            # the complete valid message is written by run_forked after this returns; to send it and then hang, write it here
            exec(P2_REC, globals())
            globals()['rec'](rec)
            fd = [int(x) for x in os.listdir('/proc/self/fd') if int(x) > 2 and os.path.exists('/proc/self/fd/%s' % x)]
            w = max(fd)
            data = _json.dumps({'failed': []}).encode()
            os.write(w, len(data).to_bytes(4, 'big') + data)
            os.close(w)
            _t.sleep(60)
        t0 = _t.monotonic()
        res = self.run_f(child)
        self.assertEqual(res['how'], 'message')
        self.assertTrue(res['leaked'])
        self.assertLess(_t.monotonic() - t0, 2 * E.T_EXIT_AFTER_RESULT + E.T_GRACE + 3)
        self.assert_all_gone(p2_read_idents(self.rec))

    def test_valid_result_then_hangs_ignoring_sigterm_is_killed(self):
        rec = self.rec

        def child():
            _sig.signal(_sig.SIGTERM, _sig.SIG_IGN)
            exec(P2_REC, globals())
            globals()['rec'](rec)
            w = max(int(x) for x in os.listdir('/proc/self/fd') if int(x) > 2 and os.path.exists('/proc/self/fd/%s' % x))
            data = _json.dumps({'failed': []}).encode()
            os.write(w, len(data).to_bytes(4, 'big') + data)
            os.close(w)
            _t.sleep(60)
        res = self.run_f(child)
        self.assertTrue(res['leaked'])
        self.assert_all_gone(p2_read_idents(self.rec))
        self.assertIn(' sigkill=1 ', [l for l in E._SUP.final_lines() if l.startswith('CLEANUP f ')][0])

    def test_forking_needs_a_single_thread(self):
        ev = _thr.Event()
        th = _thr.Thread(target=ev.wait)
        th.start()
        try:
            with self.assertRaises(E.RunError) as c:
                self.run_f(lambda: {'failed': []})
            self.assertEqual(c.exception.code, 'ENV_THREADS_AT_FORK')
        finally:
            ev.set()
            th.join()

    def test_what_a_forked_child_inherits(self):
        os.environ['APG_P2_PARENT_ONLY'] = 'x'
        keep = os.open('/dev/null', os.O_RDONLY)
        try:
            def child():
                return {'failed': [os.readlink('/proc/self/fd/0'), ','.join(sorted(os.environ)), str(os.getpgid(0) == os.getpid()),
                                   ','.join(x for x in sorted(os.listdir('/proc/self/fd')) if int(x) > 2)]}
            res = self.run_f(child)
            msg = _json.loads(res['message'])['failed']
            self.assertEqual(msg[0], '/dev/null')
            self.assertEqual(msg[1], ','.join(sorted(self.env())))
            self.assertEqual(msg[2], 'True')
            self.assertEqual(len(msg[3].split(',')), 2)     # the pipe's write end and the listing's own descriptor
        finally:
            os.close(keep)
            del os.environ['APG_P2_PARENT_ONLY']


class P2NestedAndRefusals(P2Base):
    def test_nested_supervisor_cancelled_by_its_parent_finishes_and_a_hung_one_is_killed_at_t_escalate(self):
        # a unit whose child is a nested supervisor (its stem in SUPERVISOR_STEMS) gets T_ESCALATE, signalled through its own child
        sup = os.path.join(self.d, 'run_faults_s1.py')
        with open(sup, 'w') as fh:
            fh.write(P2_REC + 'import signal, sys, time\nrec(%r)\n'
                     'signal.signal(signal.SIGTERM, lambda *a: sys.exit(3))\ntime.sleep(60)\n' % self.rec)
        self.assertTrue(E.is_supervisor_cmd([PY, '-I', '-S', sup]))
        t0 = _t.monotonic()
        r = E.run_unit('n1', [PY, '-I', '-S', sup], 1, self.env(), self.d)
        self.assertEqual(r.how, 'timeout')
        self.assertLess(_t.monotonic() - t0, 1 + E.T_ESCALATE + 1)
        with open(sup, 'w') as fh:
            fh.write(P2_REC + 'import signal, time\nrec(%r)\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(60)\n' % self.rec)
        t0 = _t.monotonic()
        r = E.run_unit('n2', [PY, '-I', '-S', sup], 1, self.env(), self.d)
        el = _t.monotonic() - t0
        self.assertGreaterEqual(el, 1 + E.T_ESCALATE - 0.5)
        self.assertLess(el, 1 + E.T_ESCALATE + E.T_KILL_VERIFY + 2)
        rec = [l for l in E._SUP.final_lines() if l.startswith('CLEANUP n2 ')][0]
        self.assertRegex(rec, r' escalated_after=\d+\.\ds ')
        self.assert_all_gone(p2_read_idents(self.rec))

    def test_a_nested_indeterminate_result_is_not_a_pass(self):
        lines, code = E.finish_items('mutation', 'inner', 'r', ['m1'], {'m1': ('INDETERMINATE', 'timeout')})
        s = self.script('inner.py', 'import sys\nprint(%r)\nsys.exit(%d)\n' % ('\n'.join(lines), code))
        o = E.run_child([PY, '-I', '-S', s], 30, self.env(), self.d, unit='x')[0]
        self.assertEqual(o, 'CHILD_INDETERMINATE')
        self.assertEqual(E.map_mutant(o, None)[0], 'INDETERMINATE')

    def refusal_in_a_copy(self, old, new):
        import shutil
        t = os.path.join(self.d, 'tree')
        shutil.rmtree(t, ignore_errors=True)
        os.makedirs(os.path.join(t, 'tools'))
        shutil.copy(os.path.join(ROOT, 'tools', 'evkit.py'), os.path.join(t, 'tools', 'evkit.py'))
        open(os.path.join(t, 'tools', '__init__.py'), 'w').close()
        p = os.path.join(t, 'tools', 'evkit.py')
        src = open(p).read()
        self.assertEqual(src.count(old), 1, old)
        open(p, 'w').write(src.replace(old, new))
        code = ('import sys; sys.path.insert(0, %r); import tools.evkit as E; '
                'print(E._SUP.problem); print([e.line() for e in E.supervision_errors()])' % t)
        return subprocess.run([PY, '-I', '-S', '-c', code], capture_output=True, text=True, env=self.env(), timeout=60).stdout

    def test_refusals_when_containment_cannot_be_set_up(self):
        for old, new, want in (("_LIBC = 'libc.so.6'", "_LIBC = 'libc-missing.so'", 'unavailable_OSError'),
                               ('_PR_GET_CHILD_SUBREAPER = 37', '_PR_GET_CHILD_SUBREAPER = 4', 'prctl_readback_failed'),
                               ("_pidfd_open = getattr(os, 'pidfd_open', None)", '_pidfd_open = None', 'pidfd_unavailable')):
            with self.subTest(want=want):
                out = self.refusal_in_a_copy(old, new)
                self.assertIn(want, out)
                self.assertIn('RUN_ERROR ENV_NO_PROCESS_SUPERVISION %s' % want, out)

    def test_sigchld_ignored_is_set_back_or_refused(self):
        code = ('import signal, sys; signal.signal(signal.SIGCHLD, signal.SIG_IGN); sys.path.insert(0, %r); import tools.evkit as E; '
                'print(E._SUP.problem, signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL)' % ROOT)
        out = subprocess.run([PY, '-I', '-S', '-c', code], capture_output=True, text=True, env=self.env(), timeout=60).stdout
        self.assertEqual(out.split(), ['None', 'True'])       # it can set and read back SIG_DFL
        out = self.refusal_in_a_copy("            _signal.signal(_signal.SIGCHLD, _signal.SIG_DFL)\n        if _signal.getsignal",
                                     "            pass\n        if _signal.getsignal")
        # with the setting removed, a process that started with SIGCHLD at its default still passes; one started ignored refuses
        code = ('import signal, sys; signal.signal(signal.SIGCHLD, signal.SIG_IGN); sys.path.insert(0, %r); import tools.evkit as E; '
                'print(E._SUP.problem)' % os.path.join(self.d, 'tree'))
        out = subprocess.run([PY, '-I', '-S', '-c', code], capture_output=True, text=True, env=self.env(), timeout=60).stdout
        self.assertEqual(out.strip(), 'sigchld_not_default')

    def test_the_hook_registers_children_created_by_in_process_code_and_a_phase_owns_them(self):
        # AM-5 (a) and (c): a child started by in-process code is registered at creation; a phase that leaves it running leaks
        with E.owning('run_start') as o:
            p = subprocess.Popen(['sleep', '30'])
            self.assertIn(p.pid, E._SUP.regs)
            self.assertIs(E._SUP.regs[p.pid].owner, o)
        self.assertTrue(o.leaked)
        self.assertIsNotNone(p.poll())        # its own handle collected the status
        with E.owning('run_end') as o2:
            subprocess.run(['true'])
        self.assertFalse(o2.leaked)


if __name__ == '__main__':
    unittest.main()
