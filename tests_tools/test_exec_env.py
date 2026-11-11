"""Stage 1 (APG-M11-S1), Workstream T, P1-F6 and T-0: the trusted execution environment (R1_REQUIREMENTS.md §2.8) and import identity
(§2.5), as enforced by tools/evkit.py.  Each case runs a child process; decoys live in temporary directories outside the tree.
Run from the package root:  python3 -I -S -m unittest discover -s tests_tools -t .      BUILDER-EXECUTED: NOT INDEPENDENT."""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVKIT = os.path.join(ROOT, 'tools', 'evkit.py')


def run(cmd, env=None, cwd=ROOT, timeout=120):
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def base_env(tmp, **extra):
    env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': tmp,
           'PYTHONDONTWRITEBYTECODE': '1'}
    env.update(extra)
    return env


def run_errors(out):
    return [l for l in out.splitlines() if l.startswith('RUN_ERROR ')]


class Decoy:
    """A temporary tree, outside the extraction, holding decoy apg/ and tests/ packages and a sitecustomize, each of which writes a
    marker file when imported."""

    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix='s1_decoy_')
        self.marker = os.path.join(self.dir, 'IMPORTED')
        code = 'open(%r, "a").write(__name__ + "\\n")\nDECOY = True\n' % self.marker
        for pkg in ('apg', 'tests', 'tools'):
            os.makedirs(os.path.join(self.dir, pkg))
            with open(os.path.join(self.dir, pkg, '__init__.py'), 'w') as f:
                f.write(code)
        with open(os.path.join(self.dir, 'sitecustomize.py'), 'w') as f:
            f.write(code)
        with open(os.path.join(self.dir, 'decoy.pth'), 'w') as f:
            f.write('import os; open(%r, "a").write("pth\\n")\n' % self.marker)

    def imported(self):
        return os.path.exists(self.marker)

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class CleanEnvAndCommands(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, ROOT)
        import tools.evkit as evkit
        self.E = evkit
        self.tmp = tempfile.mkdtemp(prefix='s1_env_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_clean_env_is_the_allowlist_only(self):
        os.environ['APG_ROOT'] = '/nonexistent/decoy'
        os.environ['PYTHONPATH'] = '/nonexistent/decoy'
        try:
            env = self.E.clean_env(self.tmp)
        finally:
            os.environ.pop('APG_ROOT', None)
            os.environ.pop('PYTHONPATH', None)
        self.assertEqual(sorted(env), sorted(self.E.ENV_ALLOWLIST))
        self.assertEqual(env['TZ'], 'UTC')
        self.assertEqual(env['LC_ALL'], 'C.UTF-8')
        self.assertEqual(env['PYTHONDONTWRITEBYTECODE'], '1')

    def test_clean_env_auif_root_is_the_only_exception(self):
        env = self.E.clean_env(self.tmp, auif_root=self.tmp)
        self.assertEqual(sorted(env), sorted(self.E.ENV_ALLOWLIST + ('APG_AUIF_ROOT',)))
        with self.assertRaises(self.E.RunError) as c:
            self.E.clean_env(self.tmp, auif_root='relative/path')
        self.assertEqual(c.exception.code, 'ENV_AUIF_ROOT_INVALID')

    def test_clean_env_refuses_a_missing_tmpdir(self):
        with self.assertRaises(self.E.RunError) as c:
            self.E.clean_env(os.path.join(self.tmp, 'missing'))
        self.assertEqual(c.exception.code, 'ENV_TMPDIR_INVALID')

    def test_child_commands_start_isolated_without_site(self):
        self.assertEqual(self.E.child_cmd('x.py', ['a'])[1:4], ['-I', '-S', 'x.py'])
        self.assertEqual(self.E.child_module_cmd('unittest', ['m'])[1:5], ['-I', '-S', '-m', 'unittest'])
        self.assertEqual(self.E.child_cmd('x.py', site=True)[1:3], ['-I', 'x.py'])

    def test_auif_root_child_side_check(self):
        self.assertEqual(self.E.check_auif_root(self.tmp), os.path.realpath(self.tmp))
        for bad, code in ((ROOT, 'ENV_AUIF_ROOT_INSIDE_EXTRACTION'), (os.path.join(ROOT, 'apg'), 'ENV_AUIF_ROOT_INSIDE_EXTRACTION'),
                          ('relative', 'ENV_AUIF_ROOT_INVALID'), (os.path.join(self.tmp, 'missing'), 'ENV_AUIF_ROOT_INVALID')):
            with self.assertRaises(self.E.RunError) as c:
                self.E.check_auif_root(bad)
            self.assertEqual(c.exception.code, code, bad)
        with self.assertRaises(self.E.RunError) as c:
            self.E.check_auif_root(self.tmp, expected_digest_fn=lambda p: False)
        self.assertEqual(c.exception.code, 'ENV_AUIF_ROOT_UNVERIFIED')

    def test_run_error_codes_are_tokens_and_details_one_line(self):
        with self.assertRaises(ValueError):
            self.E.RunError('BAD CODE')
        self.assertEqual(self.E.RunError('X_Y', 'a\nb\tc').line(), 'RUN_ERROR X_Y a b c')


class StartChecksInAChild(unittest.TestCase):
    """The start sequence, run as 'python3 -I -S tools/evkit.py --self-check' under the conditions of each case."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_env_')
        self.decoy = Decoy()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.decoy.close()

    def test_clean_start_passes(self):
        code, out, err = run([sys.executable, '-I', '-S', EVKIT, '--self-check'], env=base_env(self.tmp))
        self.assertEqual(code, 0, out + err)
        self.assertEqual(run_errors(out), [])
        self.assertIn('ENV flags isolated=1 no_site=1', out)
        self.assertIn('ENV cwd %s' % ROOT, out)

    def test_started_without_isolation_is_a_run_error(self):
        code, out, err = run([sys.executable, '-S', EVKIT, '--self-check'], env=base_env(self.tmp))
        self.assertEqual(code, 2)
        self.assertIn('ENV_NOT_ISOLATED', ' '.join(run_errors(out)))

    def test_started_with_site_is_a_run_error(self):
        code, out, err = run([sys.executable, '-I', EVKIT, '--self-check'], env=base_env(self.tmp))
        self.assertEqual(code, 2)
        self.assertIn('ENV_SITE_LOADED', ' '.join(run_errors(out)))

    def test_pythonpath_decoy_is_dropped_and_never_imported(self):
        env = base_env(self.tmp, PYTHONPATH=self.decoy.dir, EVKIT_PROBE_IMPORT='apg')
        code, out, err = run([sys.executable, '-I', '-S', EVKIT, '--self-check'], env=env)
        self.assertEqual(code, 0, out + err)
        self.assertIn('ENV DROPPED PYTHONPATH', out)
        self.assertIn('PROBE apg %s' % os.path.join(ROOT, 'apg', '__init__.py'), out)
        self.assertFalse(self.decoy.imported())

    def test_apg_root_is_removed_unconditionally(self):
        env = base_env(self.tmp, APG_ROOT=self.decoy.dir, EVKIT_PROBE_IMPORT='apg')
        code, out, err = run([sys.executable, '-I', '-S', EVKIT, '--self-check'], env=env)
        self.assertEqual(code, 0, out + err)
        self.assertIn('ENV APG_ROOT was set; removed', out)
        self.assertNotIn(self.decoy.dir, out.replace('ENV APG_ROOT was set; removed', ''))
        self.assertFalse(self.decoy.imported())

    def test_sitecustomize_and_pth_decoys_do_not_run(self):
        env = base_env(self.tmp, PYTHONPATH=self.decoy.dir, PYTHONUSERBASE=self.decoy.dir)
        code, out, err = run([sys.executable, '-I', '-S', EVKIT, '--self-check'], env=env)
        self.assertEqual(code, 0, out + err)
        self.assertIn('ENV flags isolated=1 no_site=1', out)
        self.assertFalse(self.decoy.imported())

    def test_a_decoy_in_the_working_directory_is_not_imported(self):
        env = base_env(self.tmp, EVKIT_PROBE_IMPORT='apg')
        code, out, err = run([sys.executable, '-I', '-S', EVKIT, '--self-check'], env=env, cwd=self.decoy.dir)
        self.assertFalse(self.decoy.imported())
        self.assertIn('PROBE apg %s' % os.path.join(ROOT, 'apg', '__init__.py'), out)
        # the working directory is not the extraction root, which the start checks refuse
        self.assertEqual(code, 2)
        self.assertIn('ENV_CWD', ' '.join(run_errors(out)))

    def test_interpreter_hash_mismatch_is_a_run_error(self):
        code, out, err = run([sys.executable, '-I', '-S', EVKIT, '--self-check', '--interpreter-sha256', '0' * 64], env=base_env(self.tmp))
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR ENV_INTERPRETER ', out)
        with open(os.path.realpath(sys.executable), 'rb') as f:
            good = hashlib.sha256(f.read()).hexdigest()
        code, out, err = run([sys.executable, '-I', '-S', EVKIT, '--self-check', '--interpreter-sha256', good], env=base_env(self.tmp))
        self.assertEqual(code, 0, out + err)

    def test_disk_floor_above_free_space_is_a_run_error(self):
        code, out, err = run([sys.executable, '-I', '-S', EVKIT, '--self-check', '--floor-bytes', str(10 ** 18)], env=base_env(self.tmp))
        self.assertEqual(code, 2)
        self.assertIn('ENV_DISK_BELOW_FLOOR', ' '.join(run_errors(out)))


class ImportIdentity(unittest.TestCase):
    """§2.5: a trusted package loaded from outside the extraction, or before the runner set its path, is a run error."""

    def setUp(self):
        sys.path.insert(0, ROOT)
        import tools.evkit as evkit
        self.E = evkit
        self.decoy = Decoy()

    def tearDown(self):
        self.decoy.close()

    def probe(self, code):
        script = ('import sys; sys.path.insert(0, %r); import tools.evkit as E\n' % ROOT) + code + \
                 '\nerrs, recs = E.import_identity(E.ROOT)\nprint("\\n".join(e.line() for e in errs))\n'
        p = subprocess.run([sys.executable, '-I', '-S', '-c', script], cwd=ROOT, capture_output=True, text=True, timeout=60,
                           env=base_env(tempfile.gettempdir()))
        return p.stdout + p.stderr

    def test_real_packages_pass(self):
        out = self.probe('import apg, tests._path')
        self.assertNotIn('RUN_ERROR', out, out)

    def test_trusted_package_from_outside_the_extraction(self):
        out = self.probe('sys.path.insert(0, %r); sys.modules.pop("apg", None); import apg' % self.decoy.dir)
        self.assertIn('RUN_ERROR IMPORT_OUTSIDE_EXTRACTION apg %s' % os.path.join(self.decoy.dir, 'apg', '__init__.py'), out)

    def test_tools_namespace_shadowed(self):
        out = self.probe('import importlib.util\nspec = importlib.util.spec_from_file_location("m2_mutants", %r)\n'
                         'm = importlib.util.module_from_spec(spec); sys.modules["m2_mutants"] = m; spec.loader.exec_module(m)'
                         % os.path.join(self.decoy.dir, 'tools', '__init__.py'))
        self.assertIn('RUN_ERROR IMPORT_OUTSIDE_EXTRACTION m2_mutants', out)

    def test_preloaded_trusted_module(self):
        script = ('import sys; sys.path.insert(0, %r); import apg; import tools.evkit as E\n'
                  'errs, recs = E.import_identity(E.ROOT, preloaded=("apg",))\nprint("\\n".join(e.line() for e in errs))' % ROOT)
        p = subprocess.run([sys.executable, '-I', '-S', '-c', script], cwd=ROOT, capture_output=True, text=True, timeout=60,
                           env=base_env(tempfile.gettempdir()))
        self.assertIn('RUN_ERROR IMPORT_PRELOADED apg', p.stdout)

    def test_untrusted_module_outside_stdlib_by_file(self):
        with open(os.path.join(self.decoy.dir, 'stray_mod.py'), 'w') as f:
            f.write('X = 1\n')
        out = self.probe('sys.path.append(%r); import stray_mod' % self.decoy.dir)
        self.assertIn('RUN_ERROR IMPORT_UNTRUSTED_LOCATION stray_mod', out)



def tree_copy(dest):
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
    return dest


class RunnerLevelStartChecks(unittest.TestCase):
    """P1-F6 (R4), on a runner in a temporary copy, each case on M10 (tools/run_m2_tests.py) and on the successor
    (tools/run_m2_tests_s1.py), running -q test_values.py.  M10 has no start check: started without -I, with the site module, with a
    decoy sitecustomize on PYTHONPATH (which then runs) or from a working directory outside the root, it runs the file and exits 0.  The
    successor, started without -I or with the site module, refuses before any file (RUN_ERROR ENV_NOT_ISOLATED or ENV_SITE_LOADED, the
    file NOT_RUN, exit 2); started as its run instruction says (-I -S) with the decoy on PYTHONPATH, the decoy never runs, the run records
    isolated=1 no_site=1 and passes; started from a working directory holding a decoy apg/, it imports nothing from there and refuses the
    run (RUN_ERROR ENV_CWD, exit 2).  (The plan's wording for that case, 'the recorded working directory is the extraction root', is
    met more strictly: the successor only runs from the root.  The interpreter-hash and disk-floor cases are checked by the start sequence
    that every runner shares, in StartChecksInAChild: M10 has neither check.)"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_rl_env_')
        self.tree = tree_copy(os.path.join(self.tmp, 't'))
        self.decoy = Decoy()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.decoy.close()

    def go(self, side, flags, cwd=None, **extra):
        script = os.path.join(self.tree, 'tools', 'run_m2_tests.py' if side == 'm10' else 'run_m2_tests_s1.py')
        return run([sys.executable] + flags + [script, '-q', 'test_values.py'], env=base_env(self.tmp, **extra), cwd=cwd or self.tree, timeout=600)

    def refused(self, out, code, error):
        self.assertEqual(code, 2, out[-2000:])
        self.assertIn(error, ' '.join(run_errors(out)))
        self.assertRegex(out, r'(?m)^FILE test_values\.py state=NOT_RUN ')
        sys.path.insert(0, self.tree)
        import tools.evkit as E
        self.assertEqual(E.check_output(out, code), [])

    def test_without_isolation(self):
        code, out, err = self.go('m10', [])
        self.assertEqual(code, 0, out + err)
        self.assertIn('failures 0  errors 0', out)
        code, out, err = self.go('s1', ['-S'])
        self.refused(out, code, 'ENV_NOT_ISOLATED')

    def test_with_the_site_module(self):
        code, out, err = self.go('m10', ['-I'])
        self.assertEqual(code, 0, out + err)
        code, out, err = self.go('s1', ['-I'])
        self.refused(out, code, 'ENV_SITE_LOADED')

    def test_a_decoy_sitecustomize_on_pythonpath(self):
        code, out, err = self.go('m10', [], PYTHONPATH=self.decoy.dir)
        self.assertEqual(code, 0, out + err)
        self.assertTrue(self.decoy.imported(), 'on M10 the decoy sitecustomize ran and the run still passed')
        os.remove(self.decoy.marker)
        code, out, err = self.go('s1', ['-I', '-S'], PYTHONPATH=self.decoy.dir, PYTHONUSERBASE=self.decoy.dir)
        self.assertEqual(code, 0, out + err)
        self.assertFalse(self.decoy.imported())
        self.assertIn('ENV flags isolated=1 no_site=1', out)
        self.assertIn('ENV DROPPED PYTHONPATH', out)

    def test_a_decoy_pth_file_in_the_user_site_directory(self):
        # a .pth file runs only from a site-packages directory: here the user site of a decoy PYTHONUSERBASE
        import sysconfig
        site_dir = sysconfig.get_path('purelib', 'posix_user', {'userbase': self.decoy.dir})
        os.makedirs(site_dir, exist_ok=True)
        with open(os.path.join(site_dir, 'decoy.pth'), 'w') as f:
            f.write('import os; open(%r, "a").write("pth\\n")\n' % self.decoy.marker)
        code, out, err = self.go('m10', [], PYTHONUSERBASE=self.decoy.dir)
        self.assertEqual(code, 0, out + err)
        self.assertTrue(self.decoy.imported(), 'on M10 the decoy .pth ran and the run still passed')
        os.remove(self.decoy.marker)
        code, out, err = self.go('s1', ['-I', '-S'], PYTHONUSERBASE=self.decoy.dir)
        self.assertEqual(code, 0, out + err)
        self.assertFalse(self.decoy.imported())
        self.assertIn('ENV flags isolated=1 no_site=1', out)

    def test_a_working_directory_with_a_decoy_apg(self):
        code, out, err = self.go('m10', ['-I'], cwd=self.decoy.dir)
        self.assertEqual(code, 0, out + err)
        code, out, err = self.go('s1', ['-I', '-S'], cwd=self.decoy.dir)
        self.assertFalse(self.decoy.imported())
        self.refused(out, code, 'ENV_CWD')


CHILD_PROBE = (
    "import sys as _s, json as _j, atexit as _a\n"
    "def _probe():\n"
    "    m = _s.modules.get('apg')\n"
    "    open(%r, 'a').write(_j.dumps({'argv': _s.orig_argv, 'isolated': _s.flags.isolated, 'no_site': _s.flags.no_site,\n"
    "                                  'site': 'site' in _s.modules, 'apg': getattr(m, '__file__', None)}) + '\\n')\n"
    "_a.register(_probe)\n")


class ChildrenStartIsolated(unittest.TestCase):
    """P1-F6 (R4), last case, and P7-B2: run_m8_tests_s1, m8_mutants_s1 (one mutant, ML-01, with its two controls), sabotage_m10_s1 (one
    plant) and run_regression_m10_s1 --step R07, each started with APG_ROOT and PYTHONPATH pointing at a decoy.  Each child the successor
    starts through tools/child_unittest_runner.py is recorded by a probe prepended to that file in the copy: every child starts with -I -S
    (sys.flags isolated=1, no_site=1, no site module) and imports the real apg package, never the decoy.  For m8_mutants_s1 the start and
    end controls pass and ML-01 is still killed (P7-B2: the tiers now run inside the mutated copy)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_children_')
        self.tree = tree_copy(os.path.join(self.tmp, 't'))
        self.decoy = Decoy()
        self.log = os.path.join(self.tmp, 'children.jsonl')
        p = os.path.join(self.tree, 'tools', 'child_unittest_runner.py')
        with open(p, encoding='utf-8') as f:
            src = f.read()
        head, rest = src.split('\n', 1) if src.startswith('#!') else ('', src)
        with open(p, 'w', encoding='utf-8') as f:
            f.write((head + '\n' if head else '') + CHILD_PROBE % self.log + rest)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.decoy.close()

    def go(self, *args):
        import json
        code, out, err = run([sys.executable, '-I', '-S'] + [os.path.join('tools', args[0])] + list(args[1:]),
                             env=base_env(self.tmp, APG_ROOT=self.decoy.dir, PYTHONPATH=self.decoy.dir), cwd=self.tree, timeout=1800)
        kids = []
        if os.path.exists(self.log):
            with open(self.log) as fh:
                kids = [json.loads(l) for l in fh]
        self.assertTrue(kids, (args, out[-2000:], err[-1500:]))
        for k in kids:
            self.assertEqual(k['argv'][1:3], ['-I', '-S'], k)
            self.assertEqual((k['isolated'], k['no_site'], k['site']), (1, 1, False), k)
            self.assertTrue(k['apg'] and k['apg'].endswith(os.path.join('apg', '__init__.py')) and self.decoy.dir not in k['apg'], k)
        self.assertFalse(self.decoy.imported())
        self.assertIn('ENV APG_ROOT was set; removed', out)
        os.remove(self.log)
        return code, out, kids

    def test_run_m8_tests(self):
        code, out, kids = self.go('run_m8_tests_s1.py', '--file', 'test_m8_dependency.py')
        self.assertEqual(code, 0, out[-2000:])

    def test_m8_mutants_controls_and_a_known_kill(self):
        code, out, kids = self.go('m8_mutants_s1.py', '--ids', 'ML-01')
        self.assertEqual(code, 0, out[-2000:])
        self.assertRegex(out, r'(?m)^CONTROL start CONTROL_PASS ')
        self.assertRegex(out, r'(?m)^CONTROL end CONTROL_PASS ')
        self.assertRegex(out, r'(?m)^MUTANT ML-01 KILLED cause=\S+$')
        self.assertGreaterEqual(len(kids), 5)          # two tiers per control, and the mutant's first tier

    def test_sabotage_m10_one_plant(self):
        # V01: a view-model plant whose check is one Python test, run through the child runner
        code, out, kids = self.go('sabotage_m10_s1.py', '--ids', 'V01')
        self.assertEqual(code, 0, out[-2000:])
        self.assertRegex(out, r'(?m)^PLANT V01 CAUGHT ')

    def test_run_regression_m10_step_r07(self):
        code, out, kids = self.go('run_regression_m10_s1.py', '--step', 'R07')
        self.assertEqual(code, 0, out[-2000:])


if __name__ == '__main__':
    unittest.main()
