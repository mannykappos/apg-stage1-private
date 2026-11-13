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
        # a .pth file is processed only from a site-packages directory: here the user site of this tree used as PYTHONUSERBASE
        import sysconfig
        site_dir = sysconfig.get_path('purelib', 'posix_user', {'userbase': self.dir})
        os.makedirs(site_dir, exist_ok=True)
        with open(os.path.join(site_dir, 'decoy.pth'), 'w') as f:
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
        # the decoys are live: an interpreter started with site and without -I runs both
        code, out, err = run([sys.executable, '-c', 'pass'], env=env)
        with open(self.decoy.marker) as fh:
            self.assertEqual(sorted(fh.read().split()), ['pth', 'sitecustomize'])
        os.remove(self.decoy.marker)
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

    def test_free_disk_below_the_floor_stops_a_runner_and_a_mutation_tool_before_any_work(self):
        # D5 at runner level: the floor every runner's start sequence applies (evkit.start, 10 GB) is raised in the copy above the free
        # space; the runner refuses before any file, and a mutation tool before any control or mutant
        p = os.path.join(self.tree, 'tools', 'evkit.py')
        with open(p, encoding='utf-8') as fh:
            src = fh.read()
        old = 'def start(root=ROOT, allow_site=False, interpreter_sha256=None, disk_floor_bytes=10 * 1024 ** 3, preloaded=None, supervisor=None):'
        self.assertEqual(src.count(old), 1)
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(src.replace(old, old.replace('10 * 1024 ** 3', '10 ** 18')))
        code, out, err = self.go('s1', ['-I', '-S'])
        self.refused(out, code, 'ENV_DISK_BELOW_FLOOR')
        import json
        with open(os.path.join(self.tree, 'tools', 'expected_counts.json'), encoding='utf-8') as fh:
            ids = json.load(fh)['mutation_lists']['m5_mutants_s1']['ids']
        mid = ids[0]
        sys.path.insert(0, ROOT)
        import tools.evkit as E
        code, out, err = run([sys.executable, '-I', '-S', os.path.join(self.tree, 'tools', 'm5_mutants_s1.py'), '--ids', mid],
                             env=base_env(self.tmp), cwd=self.tree, timeout=600)
        self.assertEqual(code, 2, out[-2000:])
        self.assertIn('ENV_DISK_BELOW_FLOOR', ' '.join(run_errors(out)))
        self.assertIn('MUTANT %s NOT_RUN cause=run_error' % mid, out)
        self.assertNotRegex(out, r'(?m)^CONTROL ')
        # corrective pass 2, amendment 3, AM3-1 (b): a failed start check stops the guarded load, so the selection is not resolved and
        # the refusal names every pinned item (C.1's form); before, it named the selection (selected=[mid])
        self.assertIn(' selected=%d ' % len(ids), out.strip().splitlines()[-1])
        self.assertEqual(E.check_output(out, code, selected=ids), [])


class AuifRootAtRunnerLevel(unittest.TestCase):
    """Authorisation §4.3 (APG_AUIF_ROOT: accepted only as the runner's own verified AUIF copy, the child re-checking the path and the
    package identity, any other value refused; DP-1.3 (a), P7-B2 (R4), T-E (a)), through the real runners:
      - an APG_AUIF_ROOT inherited by run_m8_tests_s1 that is not a verified AUIF copy is refused (AUIF_DEPENDENCY_UNVERIFIED, exit 2)
        and nothing from it is imported;
      - every child run_m8_tests_s1 starts gets APG_AUIF_ROOT set to exactly the copy the runner verified (its 'AUIF verified_before'
        line), outside the tree, and nothing inherited (the child environment is the allowlist);
      - the child runner itself (tools/child_unittest_runner.py) refuses a relative, missing or inside-the-tree value before any test
        (ENV_AUIF_ROOT_INVALID / ENV_AUIF_ROOT_INSIDE_EXTRACTION, exit 2);
      - given a path that passes those checks but is a tampered AUIF copy, the child never imports from it."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_auif_rl_')
        self.decoy = Decoy()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.decoy.close()

    def check(self, out, code):
        sys.path.insert(0, ROOT)
        import tools.evkit as E
        self.assertEqual(E.check_output(out, code), [], out[-2000:])

    def test_an_inherited_value_that_is_not_a_verified_copy_is_refused(self):
        code, out, err = run([sys.executable, '-I', '-S', os.path.join('tools', 'run_m8_tests_s1.py'), '--file', 'test_m8_dependency.py'],
                             env=base_env(self.tmp, APG_AUIF_ROOT=self.decoy.dir), timeout=1800)
        self.assertEqual(code, 2, out[-2000:])
        self.assertIn('RUN_ERROR AUIF_DEPENDENCY_UNVERIFIED', out)
        self.assertRegex(out, r'(?m)^FILE test_m8_dependency\.py state=NOT_RUN ')
        self.assertFalse(self.decoy.imported())
        self.check(out, code)

    def test_children_get_only_the_copy_the_runner_verified(self):
        import json
        tree = tree_copy(os.path.join(self.tmp, 't'))
        log = os.path.join(self.tmp, 'children.jsonl')
        p = os.path.join(tree, 'tools', 'child_unittest_runner.py')
        with open(p, encoding='utf-8') as f:
            src = f.read()
        head, rest = src.split('\n', 1)
        probe = ("import os as _o, json as _j\nopen(%r, 'a').write(_j.dumps({'auif': _o.environ.get('APG_AUIF_ROOT'), "
                 "'env': sorted(_o.environ)}) + '\\n')\n" % log)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(head + '\n' + probe + rest)
        code, out, err = run([sys.executable, '-I', '-S', os.path.join('tools', 'run_m8_tests_s1.py'), '--file', 'test_m8_dependency.py'],
                             env=base_env(self.tmp, PYTHONPATH=self.decoy.dir), cwd=tree, timeout=1800)
        self.assertEqual(code, 0, out[-2000:])
        import re
        m = re.search(r'(?m)^AUIF verified_before .* root=(\S+)$', out)
        self.assertTrue(m, out[-2000:])
        with open(log) as fh:
            kids = [json.loads(l) for l in fh]
        self.assertTrue(kids)
        for k in kids:
            self.assertEqual(k['auif'], os.path.realpath(m.group(1)))
            self.assertFalse(k['auif'].startswith(tree + os.sep))
            self.assertEqual(k['env'], sorted(['PATH', 'LANG', 'LC_ALL', 'TZ', 'TMPDIR', 'PYTHONDONTWRITEBYTECODE', 'APG_AUIF_ROOT']))

    def child(self, value, module='tests_m8.test_m8_dependency'):
        return run([sys.executable, '-I', '-S', os.path.join('tools', 'child_unittest_runner.py'), '--caller', 'run_m8_tests_s1',
                    '--mode', 'full', module], env=base_env(self.tmp, APG_AUIF_ROOT=value), timeout=1800)

    def test_the_child_refuses_a_bad_path_before_any_test(self):
        for value, error in (('relative/path', 'ENV_AUIF_ROOT_INVALID'), (os.path.join(self.tmp, 'missing'), 'ENV_AUIF_ROOT_INVALID'),
                             (ROOT, 'ENV_AUIF_ROOT_INSIDE_EXTRACTION'), (os.path.join(ROOT, 'apg'), 'ENV_AUIF_ROOT_INSIDE_EXTRACTION')):
            with self.subTest(value=value):
                code, out, err = self.child(value)
                self.assertEqual(code, 2, out[-2000:])
                self.assertIn('RUN_ERROR %s ' % error, out)
                self.assertRegex(out, r'(?m)^FILE test_m8_dependency\.py state=NOT_RUN ')
                self.assertNotRegex(out, r'(?m)^TEST ')
                self.check(out, code)

    def test_the_child_never_imports_from_a_tampered_copy(self):
        r = subprocess.run([sys.executable, '-I', '-S', '-c', 'import sys; sys.path.insert(0, %r)\nfrom apg_auif import dependency as d\n'
                            'print(d.extract(sys.argv[1]))' % ROOT, os.path.join(self.tmp, 'auif')], cwd=ROOT, capture_output=True,
                           text=True, env=base_env(self.tmp), timeout=600)
        root = r.stdout.strip().splitlines()[-1]
        with open(os.path.join(root, 'auif', '__init__.py'), 'a') as fh:
            fh.write('\nopen(%r, "a").write("tampered auif\\n")\n' % self.decoy.marker)
        code, out, err = self.child(root)
        # decision (f): a refusal before any test (exit 2), not a test failure; nothing from the copy ran
        self.assertEqual(code, 2, out[-2000:] + err[-1500:])
        self.assertIn('RUN_ERROR ENV_AUIF_ROOT_UNVERIFIED %s ' % root, out)
        self.assertRegex(out, r'(?m)^FILE test_m8_dependency\.py state=NOT_RUN ')
        self.assertNotRegex(out, r'(?m)^TEST ')
        self.assertFalse(self.decoy.imported(), 'code from the tampered AUIF copy ran')
        self.check(out, code)

    def test_the_child_accepts_the_copy_its_runner_verified(self):
        # the control case for (f): an untouched verified copy is accepted, and the file runs and passes
        r = subprocess.run([sys.executable, '-I', '-S', '-c', 'import sys; sys.path.insert(0, %r)\nfrom apg_auif import dependency as d\n'
                            'print(d.extract(sys.argv[1]))' % ROOT, os.path.join(self.tmp, 'auif_ok')], cwd=ROOT, capture_output=True,
                           text=True, env=base_env(self.tmp), timeout=600)
        code, out, err = self.child(r.stdout.strip().splitlines()[-1])
        self.assertEqual(code, 0, out[-2000:] + err[-1500:])
        self.assertRegex(out, r'(?m)^FILE test_m8_dependency\.py state=COMPLETED ')
        self.check(out, code)


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
        # DP-2.3 F7 on the real tiers: every tier child runs in its pinned mode for this caller (failfast)
        for k in kids:
            a = k['argv']
            self.assertEqual((a[a.index('--caller') + 1], a[a.index('--mode') + 1]), ('m8_tier', 'failfast'), a)     # the pinned caller profile child_unittest_runner@m8_tier

    def test_sabotage_m10_one_plant(self):
        # V01: a view-model plant whose check is one Python test, run through the child runner
        code, out, kids = self.go('sabotage_m10_s1.py', '--ids', 'V01')
        self.assertEqual(code, 0, out[-2000:])
        self.assertRegex(out, r'(?m)^PLANT V01 CAUGHT ')

    def test_run_regression_m10_step_r07(self):
        code, out, kids = self.go('run_regression_m10_s1.py', '--step', 'R07')
        self.assertEqual(code, 0, out[-2000:])
        # DP-2.3 F6: R07's test children run full
        for k in kids:
            a = k['argv']
            self.assertEqual(a[a.index('--mode') + 1], 'full', a)



class E7ChildIsolationM10Halves(unittest.TestCase):
    """Corrective pass 2, E point 7: the M10 halves of ChildrenStartIsolated's four cases.  Each M10 tool runs on an M10 view
    (test_apg_root.m10_view) as its run instruction says (python3 -I), with APG_ROOT and PYTHONPATH pointing at the same decoy as the
    successor half.  Recorded as found: M10's parent starts isolated, but its children do not (they start without -I), so the decoy's
    sitecustomize on PYTHONPATH runs in them; in these four runs the decoy apg itself is not imported (each child's working directory, or
    a path entry ahead of the decoy, supplies the real one).  M10's m8_mutants on the view fails its own control at the stage 1 boundary
    test (tests_m8.test_m8_boundary.TestNoOtherChange), which is why the successor omits that tier module (decision M8-T).
    BUILDER-EXECUTED: NOT INDEPENDENT."""

    def setUp(self):
        sys.path.insert(0, ROOT)
        from tests_tools.test_apg_root import m10_view
        self.tmp = tempfile.mkdtemp(prefix='s1_e7_')
        self.view = m10_view(os.path.join(self.tmp, 'm10'))
        self.decoy = Decoy()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.decoy.close()

    def go(self, *args):
        code, out, err = run([sys.executable, '-I', os.path.join('tools', args[0])] + list(args[1:]), cwd=self.view, timeout=3600,
                             env=base_env(self.tmp, APG_ROOT=self.decoy.dir, PYTHONPATH=self.decoy.dir))
        names = open(self.decoy.marker).read().split() if self.decoy.imported() else []
        self.assertIn('sitecustomize', names, 'the M10 children ran isolated after all: %r' % ((args, out[-1500:]),))
        self.assertNotIn('apg', names)
        return code, out, err

    def test_run_m8_tests(self):
        code, out, err = self.go('run_m8_tests.py', '--file', 'test_m8_dependency.py')
        self.assertEqual(code, 0, out[-2000:] + err[-1500:])
        self.assertIn('M8 tests 7 in 1 files, failed files 0', out)

    def test_m8_mutants_control_is_killed_at_tier_1_and_ml01_never_runs(self):
        # fix 6, D17: renamed from test_m8_mutants_controls_and_a_known_kill, so the name says what it asserts.  Amendment 5, discrepancy 17: the known kill on the M10 view is the control's own: M10's unmutated copy is KILLED at tier 1 by
        # the stage 1 boundary test (decision M8-T), and M10 then stops (its main returns 2 after a failed control), so ML-01 itself
        # never runs here; the successor half (ChildrenStartIsolated) asserts ML-01 KILLED
        code, out, err = self.go('m8_mutants.py', '--only', 'ML-01', '--jobs', '1')
        self.assertEqual(code, 2, out[-2000:] + err[-1500:])
        self.assertRegex(out, r'(?m)^CONTROL \(unmutated copy\): KILLED tier 1: FAIL: test_every_added_file_is_declared '
                              r'\(tests_m8\.test_m8_boundary\.TestNoOtherChange\.test_every_added_file_is_declared\)')
        self.assertNotRegex(out, r'(?m)^ML-01\b')
        self.assertNotIn('mutants 1:', out)

    def test_sabotage_m10_one_plant(self):
        code, out, err = self.go('sabotage_m10.py', '--only', 'V01')
        self.assertEqual(code, 0, out[-2000:] + err[-1500:])
        self.assertRegex(out, r'(?m)^CAUGHT V01 ')

    def test_run_regression_m10_step_r07(self):
        code, out, err = self.go('run_regression_m10.py', '--step', 'R07')
        self.assertEqual(code, 0, out[-2000:] + err[-1500:])
        self.assertRegex(out, r'(?m)^PASS R07 ')


# ---------------------------------------------------------------------------------------------------------------------------------------
# Amendment 5 (owner, 2026-11-08 11:26, AM5-4 option A): Appendix A part 1, row 29 (P.10, two-level nesting) and row 22 (a tests-kind
# FILE leak).  Rewritten after the workspace loss of 2026-11-11 from the amendment (recovery authorisation, rebuild rule).
# ---------------------------------------------------------------------------------------------------------------------------------------
import re as _am5re

AM5_TEE = ('import sys as _am5s\n'
           'class _AM5Tee:\n'
           '    def __init__(self, a, f):\n        self.a, self.f = a, open(f, "a")\n'
           '    def write(self, x):\n        self.f.write(x); self.f.flush(); return self.a.write(x)\n'
           '    def flush(self):\n        self.f.flush(); self.a.flush()\n'
           '    def __getattr__(self, k):\n        return getattr(self.a, k)\n'
           '_am5s.stdout = _AM5Tee(_am5s.stdout, %r)\n')

AM5_CHAIN = r'''


def _am5_chain():
    """amendment 5, row 29 (test only, in a copy): a test file's run starts a process that starts a child (test -> process -> child);
    in mode hang the leaf then blocks, so its parent's limit or a signal ends it."""
    import os as _o, subprocess as _sp, sys as _s, time as _tm
    mode = open(_o.path.join(%(root)r, '_p2', 'mode')).read().strip()
    _sp.Popen([_s.executable, '-c', 'import subprocess, sys, time; subprocess.Popen([sys.executable, "-c", "import time; '
               'time.sleep(60)"]); open(sys.argv[1], "w").close(); time.sleep(60)', _o.path.join(%(root)r, '_p2', 'chain')],
              stdin=_sp.DEVNULL, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
    if mode == 'hang':
        _tm.sleep(60)
'''


class AM5SecondChain(unittest.TestCase):
    """Row 29: tool -> leaf -> test -> process -> child, through run_m8_tests_s1 and child_unittest_runner (a supervisor, since it
    verifies its AUIF copy), on the normal, timeout and interrupt paths; the CLEANUP attribution of each level."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_am5sc_')
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import test_runner_zero_work as Z
        self.Z = Z
        self.E = Z.E

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def tree(self, mode, edits=()):
        root = os.path.join(self.tmp, mode)
        self.Z.p2b_copy(root, [('tools/evkit.py', '            with owning(name) as o_file:\n                suite.run(res)\n',
                                '            with owning(name) as o_file:\n                _am5_chain()\n                suite.run(res)\n')]
                        + list(edits))
        with open(os.path.join(root, 'tools', 'evkit.py'), 'a', encoding='utf-8') as fh:
            fh.write(AM5_CHAIN % {'root': root})
        p = os.path.join(root, 'tools', 'child_unittest_runner.py')
        src = open(p, encoding='utf-8').read()
        head, rest = src.split('\n', 1)
        open(p, 'w', encoding='utf-8').write(head + '\n' + AM5_TEE % os.path.join(root, '_p2', 'leaf.txt') + rest)
        os.makedirs(os.path.join(root, '_p2'))
        open(os.path.join(root, '_p2', 'mode'), 'w').write(mode)
        return root

    def leaf(self, root):
        p = os.path.join(root, '_p2', 'leaf.txt')
        return open(p).read() if os.path.exists(p) else ''

    def record(self, seen, out):
        import test_runner_zero_work as Z
        Z.p2_identity_record(self, seen, out)

    def test_row29_the_second_chain_through_run_m8_tests_s1(self):
        # normal path; row 22: the leaf's test file leaked, so its FILE is INDETERMINATE cause=processes_left, and its CLEANUP record
        # (by the leaf) names the process and its child; the parent reads the leaf's exit 3 as an INDETERMINATE file
        root = self.tree('normal')
        code, out, seen = self.Z.p2b_run(root, ['tools/run_m8_tests_s1.py', '--file', 'test_m8_dependency.py'])
        leaf = self.leaf(root)
        self.record(seen, out + '\n' + leaf)
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(leaf, r'(?m)^FILE test_m8_dependency\.py state=INDETERMINATE ')
        rec = _am5re.search(r'(?m)^CLEANUP test_m8_dependency\.py by=child_unittest_runner:\d+ .* left=(\S+) ', leaf)
        self.assertTrue(rec, leaf[-2000:])
        self.assertEqual(len(rec.group(1).split(',')), 2)        # the process and its child
        self.assertRegex(out, r'(?m)^FILE test_m8_dependency\.py state=INDETERMINATE ')
        self.assertEqual(self.E.check_output(out, code), [], out[-3000:])
        self.Z.p2b_gone(self, seen)

    def test_row29_the_second_chain_through_run_m8_tests_s1_timeout(self):
        # the leaf blocks after starting the chain: the parent's limit (8 s here) ends the unit; the parent's cleanup kills the leaf,
        # the process and its child, and its CLEANUP record (by run_m8_tests_s1) names them
        root = self.tree('hang', [('tools/run_m8_tests_s1.py', 'E.run_child(cmd, 3600,', 'E.run_child(cmd, 8,')])
        code, out, seen = self.Z.p2b_run(root, ['tools/run_m8_tests_s1.py', '--file', 'test_m8_dependency.py'])
        self.record(seen, out)
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^FILE test_m8_dependency\.py state=INDETERMINATE ')
        rec = _am5re.search(r'(?m)^CLEANUP test_m8_dependency\.py by=run_m8_tests_s1:\d+ .* left=(\S+) ', out)
        self.assertTrue(rec, out[-2000:])
        self.assertGreaterEqual(len(rec.group(1).split(',')), 3)  # the leaf, the process and its child
        self.assertEqual(self.E.check_output(out, code), [], out[-3000:])
        self.Z.p2b_gone(self, seen)

    def test_row29_the_second_chain_through_run_m8_tests_s1_interrupt(self):
        root = self.tree('hang')
        code, out, seen = self.Z.p2b_run(root, ['tools/run_m8_tests_s1.py', '--file', 'test_m8_dependency.py'],
                                         when=self.Z.p2b_mark('chain'), delay=0.5)
        self.record(seen, out)
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(out.strip().splitlines()[-2], r'^INTERRUPTED signal=SIGINT at=\S+ received=1$')   # before the RESULT line
        self.assertTrue(out.strip().splitlines()[-1].startswith('RESULT v=2 kind=tests '))
        self.assertRegex(out, r'(?m)^FILE test_m8_dependency\.py state=INDETERMINATE ')
        # fix 6, row 29: the CLEANUP attribution on the interrupt path: run_m8_tests_s1's record names the leaf, the process and its child
        rec = _am5re.search(r'(?m)^CLEANUP test_m8_dependency\.py by=run_m8_tests_s1:\d+ .* left=(\S+) ', out)
        self.assertTrue(rec, out[-2000:])
        self.assertGreaterEqual(len(rec.group(1).split(',')), 3)
        self.assertEqual(self.E.check_output(out, code), [], out[-3000:])
        self.Z.p2b_gone(self, seen)


class AM6FirstChain(unittest.TestCase):
    """Fix 6, row 29: the first chain, a mutation tool -> its leaf (run_m2_tests_s1) -> a test -> a process -> its child, on
    m3_mutants_s1 in a copy (its commands cut to the first test pattern), on the normal and interrupt paths, with the CLEANUP attribution
    of the mutation tool's unit."""

    setUp = AM5SecondChain.setUp
    tearDown = AM5SecondChain.tearDown

    def tree(self, mode):
        root = os.path.join(self.tmp, 'first_' + mode)
        self.Z.p2b_copy(root, [('tools/evkit.py', '            with owning(name) as o_file:\n                suite.run(res)\n',
                                '            with owning(name) as o_file:\n                _am5_chain()\n                suite.run(res)\n'),
                               ('tools/evkit.py', '            o_file = None\n            suite.run(res)\n',
                                '            o_file = None\n            _am5_chain()\n            suite.run(res)\n'),
                               ('tools/m3_mutants_s1.py', '            for pat in M.TEST_ORDER]', '            for pat in M.TEST_ORDER[:1]]')])
        with open(os.path.join(root, 'tools', 'evkit.py'), 'a', encoding='utf-8') as fh:
            fh.write(AM5_CHAIN % {'root': root})
        os.makedirs(os.path.join(root, '_p2'))
        with open(os.path.join(root, '_p2', 'mode'), 'w') as fh:
            fh.write(mode)
        return root

    def test_row29_the_first_chain_normal_path(self):
        # the leaf's test leaves a process and its child; the leaf is not a supervisor, so the mutation tool's cleanup of the start
        # control's unit finds them: CONTROL start CONTROL_FAIL cause=processes_left, every mutant NOT_RUN, and the record names both
        first = self.E.load_pins()[0]['mutation_lists']['m3_mutants_s1']['ids'][0]
        root = self.tree('normal')
        code, out, seen = self.Z.p2b_run(root, ['tools/m3_mutants_s1.py', '--ids', first])
        self.Z.p2_identity_record(self, seen, out)
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^CONTROL start CONTROL_FAIL cause=processes_left ')
        rec = _am5re.search(r'(?m)^CLEANUP control_start\S* by=m3_mutants_s1:\d+ .* left=(\S+) ', out)
        self.assertTrue(rec, out[-2000:])
        self.assertGreaterEqual(len(rec.group(1).split(',')), 2)        # the process and its child
        self.assertRegex(out, r'(?m)^MUTANT %s NOT_RUN ' % _am5re.escape(first))
        self.assertEqual(self.E.check_output(out, code, selected=[first]), [], out[-3000:])
        self.Z.p2b_gone(self, seen)

    def test_row29_the_first_chain_interrupt_path(self):
        # the leaf blocks after starting the chain; SIGINT to the mutation tool: CONTROL start CONTROL_INTERRUPTED, and its cleanup's
        # record names the leaf, the process and its child
        first = self.E.load_pins()[0]['mutation_lists']['m3_mutants_s1']['ids'][0]
        root = self.tree('hang')
        code, out, seen = self.Z.p2b_run(root, ['tools/m3_mutants_s1.py', '--ids', first], when=self.Z.p2b_mark('chain'), delay=0.5)
        self.Z.p2_identity_record(self, seen, out)
        self.assertEqual(code, 3, out[-2000:])
        self.assertRegex(out, r'(?m)^CONTROL start CONTROL_INTERRUPTED cause=interrupted$')
        self.assertRegex(out.strip().splitlines()[-2], r'^INTERRUPTED signal=SIGINT at=control_start received=1$')
        rec = _am5re.search(r'(?m)^CLEANUP control_start\S* by=m3_mutants_s1:\d+ .* left=(\S+) ', out)
        self.assertTrue(rec, out[-2000:])
        self.assertGreaterEqual(len(rec.group(1).split(',')), 3)        # the leaf, the process and its child
        self.assertEqual(self.E.check_output(out, code, selected=[first]), [], out[-3000:])
        self.Z.p2b_gone(self, seen)


if __name__ == '__main__':
    unittest.main()
