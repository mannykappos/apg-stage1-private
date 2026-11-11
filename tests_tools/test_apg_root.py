"""Stage 1 (APG-M11-S1), Workstream T, P1-F6, P7-B2 and T-0: APG_ROOT can no longer redirect a test run to other code.
Each case runs on M10 and on the successor.  M10 is reproduced as an 'M10 view': a temporary copy of this tree with M10's own
tests/_path.py and tests_m8/_auif.py restored, each checked against its M10 SHA-256 (the M10 tools themselves are byte-identical here,
DP-1.2 (B)).  A decoy tree outside the package holds an apg package that writes a marker file when imported.
Also (class BoundaryManifest) amendment 2's planted faults: the stage 1 manifest that tests_m8/test_m8_boundary.py validates in full before its two
TestNoOtherChange checks use it.  These need the tree's frozen manifest (programme/APG-M11-S1_MANIFEST.csv) to be current; each plant is made in a copy.
Run from the package root:  python3 -I -S tests_tools/test_apg_root.py      BUILDER-EXECUTED: NOT INDEPENDENT."""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

M10_PATH_PY = ('"""Make the package under test importable.  APG_ROOT (used by the mutation run) overrides the default location."""\n'
               'import os, sys\nsys.dont_write_bytecode = True\n'
               "ROOT = os.environ.get('APG_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
               'if ROOT not in sys.path:\n    sys.path.insert(0, ROOT)\n'
               'HERE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # the package root that holds builder_zero/ etc.\n')
M10_PATH_SHA = 'ef0cb5f7d80f247ed1483d0f7ab24eea76ec240050b1ada16c9bdd143ed043d3'
M10_AUIF_SHA = 'efc14287f0c72aa8f3619c024262477a1441e22b2052ab23b4428b36c6a1cb2f'
S1_AUIF_HEAD_START = '"""Shared set-up for the M8 tests.'
S1_AUIF_HEAD_END = "    raise ImportError('apg resolves outside this package root: %s (expected under %s)' % (_apg.__file__, HERE_ROOT))\n"
M10_AUIF_HEAD = ('"""Shared set-up for the M8 tests.  Importing it makes APG importable, VERIFIES the AUIF rev13 dependency by hash (ZIP, manifest, '
                 'core tree) and makes AUIF importable from a\nfresh verified extraction (apg_auif.dependency.ensure).  Nothing here changes AUIF '
                 'or any APG release file.  Everything is synthetic."""\nimport os, shutil, sys, tempfile\nsys.dont_write_bytecode = True\n'
                 "ROOT = os.environ.get('APG_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
                 'if ROOT not in sys.path:\n    sys.path.insert(0, ROOT)\nHERE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n')


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def m10_view(dest):
    """A copy of this tree with M10's two path helpers restored, each verified against its M10 hash."""
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
    assert sha(M10_PATH_PY) == M10_PATH_SHA
    with open(os.path.join(dest, 'tests', '_path.py'), 'w') as f:
        f.write(M10_PATH_PY)
    p = os.path.join(dest, 'tests_m8', '_auif.py')
    s1 = open(p).read()
    a, b = s1.index(S1_AUIF_HEAD_START), s1.index(S1_AUIF_HEAD_END) + len(S1_AUIF_HEAD_END)
    m10 = s1[:a] + M10_AUIF_HEAD + s1[b:]
    assert sha(m10) == M10_AUIF_SHA, 'the reconstructed M10 tests_m8/_auif.py does not match its M10 hash'
    with open(p, 'w') as f:
        f.write(m10)
    return dest


def env(tmp, **extra):
    e = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': tmp, 'PYTHONDONTWRITEBYTECODE': '1'}
    e.update(extra)
    return e


class ApgRootRedirect(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_apgroot_')
        self.decoy = os.path.join(self.tmp, 'decoy')
        self.marker = os.path.join(self.tmp, 'DECOY_IMPORTED')
        os.makedirs(os.path.join(self.decoy, 'apg'))
        with open(os.path.join(self.decoy, 'apg', '__init__.py'), 'w') as f:
            f.write('open(%r, "a").write("decoy apg imported\\n")\n' % self.marker)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_m10_run_m2_tests_imports_the_decoy(self):
        view = m10_view(os.path.join(self.tmp, 'm10'))
        subprocess.run([sys.executable, '-I', 'tools/run_m2_tests.py', '-q', 'test_values.py'], cwd=view, capture_output=True, text=True,
                       timeout=300, env=env(self.tmp, APG_ROOT=self.decoy))
        self.assertTrue(os.path.exists(self.marker), 'on M10, APG_ROOT redirected the test run to the decoy package')

    def test_successor_never_imports_the_decoy(self):
        p = subprocess.run([sys.executable, '-I', '-S', 'tools/run_m2_tests_s1.py', '-q', 'test_values.py'], cwd=ROOT, capture_output=True,
                           text=True, timeout=300, env=env(self.tmp, APG_ROOT=self.decoy))
        self.assertFalse(os.path.exists(self.marker))
        self.assertIn('ENV APG_ROOT was set; removed', p.stdout)
        self.assertIn('IMPORT_END apg %s' % os.path.join(ROOT, 'apg', '__init__.py'), p.stdout)  # recorded at the end of the run (§2.5)
        self.assertEqual(p.returncode, 0, p.stdout[-2000:] + p.stderr[-2000:])

    def test_m10_auif_helper_reads_apg_root(self):
        view = m10_view(os.path.join(self.tmp, 'm10'))
        subprocess.run([sys.executable, '-I', '-c', 'import sys; sys.path.insert(0, %r); import tests_m8._auif' % view], cwd=view,
                       capture_output=True, text=True, timeout=300, env=env(self.tmp, APG_ROOT=self.decoy))
        self.assertTrue(os.path.exists(self.marker), 'on M10, tests_m8/_auif.py honoured APG_ROOT')

    def test_successor_path_helpers_ignore_apg_root(self):
        for mod in ('tests._path', 'tests_m8._auif'):
            code = 'import sys; sys.path.insert(0, %r); import %s; import apg; print(apg.__file__)' % (ROOT, mod)
            if mod == 'tests_m8._auif':
                code = 'import sys; sys.path.insert(0, %r); import importlib.util, os\n' % ROOT + \
                       'spec = importlib.util.spec_from_file_location("g", os.path.join(%r, "tests_m8", "_auif.py"))\n' % ROOT + \
                       'src = open(spec.origin).read(); head = src[:src.index("from apg_auif import dependency")]\n' + \
                       'exec(compile(head, spec.origin, "exec"), {"__file__": spec.origin}); import apg; print(apg.__file__)'
            p = subprocess.run([sys.executable, '-I', '-S', '-c', code], cwd=ROOT, capture_output=True, text=True, timeout=120,
                               env=env(self.tmp, APG_ROOT=self.decoy))
            self.assertFalse(os.path.exists(self.marker), mod)
            self.assertIn(os.path.join(ROOT, 'apg', '__init__.py'), p.stdout, mod + p.stderr)

    def test_m10_run_m8_tests_imports_the_decoy(self):
        # P7-B2: M10's run_m8_tests pops APG_ROOT only when it was not set (run_m8_tests.py:45-46), so a set APG_ROOT reaches the children
        view = m10_view(os.path.join(self.tmp, 'm10_m8'))
        subprocess.run([sys.executable, '-I', 'tools/run_m8_tests.py', '--file', 'test_m8_dependency.py'], cwd=view, capture_output=True,
                       text=True, timeout=900, env=env(self.tmp, APG_ROOT=self.decoy))
        self.assertTrue(os.path.exists(self.marker), 'on M10, APG_ROOT redirected the M8 test run to the decoy package')

    def test_successor_run_m8_tests_ignores_apg_root(self):
        p = subprocess.run([sys.executable, '-I', '-S', 'tools/run_m8_tests_s1.py', '--file', 'test_m8_dependency.py'], cwd=ROOT,
                           capture_output=True, text=True, timeout=900, env=env(self.tmp, APG_ROOT=self.decoy))
        self.assertFalse(os.path.exists(self.marker))
        self.assertIn('ENV APG_ROOT was set; removed', p.stdout)
        self.assertIn('IMPORT tools.evkit %s' % os.path.join(ROOT, 'tools', 'evkit.py'), p.stdout)
        self.assertEqual(p.returncode, 0, p.stdout[-2000:] + p.stderr[-2000:])
        self.assertRegex(p.stdout, r'(?m)^FILE test_m8_dependency\.py state=COMPLETED ')

    def test_e17_the_p7_b2_run_imports_the_real_apg_in_its_child(self):
        # corrective pass 2, E point 17 (first half), under the reading proposed as AM3-3: the P7-B2 run imports no apg in its own process
        # (it prints no apg record on either freeze); its child imports apg through tests_m8/_auif.py.  The child probe of
        # test_exec_env.ChildrenStartIsolated, prepended to the child runner in a copy, records each child's apg.__file__.
        import json
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from test_exec_env import CHILD_PROBE
        tree = os.path.join(self.tmp, 't')
        shutil.copytree(ROOT, tree, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
        log = os.path.join(self.tmp, 'children.jsonl')
        cp = os.path.join(tree, 'tools', 'child_unittest_runner.py')
        src = open(cp, encoding='utf-8').read()
        head, rest = src.split('\n', 1)
        with open(cp, 'w', encoding='utf-8') as f:
            f.write(head + '\n' + CHILD_PROBE % log + rest)
        p = subprocess.run([sys.executable, '-I', '-S', 'tools/run_m8_tests_s1.py', '--file', 'test_m8_dependency.py'], cwd=tree,
                           capture_output=True, text=True, timeout=900, env=env(self.tmp, APG_ROOT=self.decoy))
        self.assertEqual(p.returncode, 0, p.stdout[-2000:] + p.stderr[-2000:])
        self.assertFalse(os.path.exists(self.marker))
        self.assertNotRegex(p.stdout, r'(?m)^IMPORT(_END)? apg ')          # recorded as found: no apg in the runner's own process
        with open(log) as fh:
            kids = [json.loads(l) for l in fh]
        self.assertEqual(len(kids), 1, kids)
        self.assertEqual(os.path.realpath(kids[0]['apg']), os.path.realpath(os.path.join(tree, 'apg', '__init__.py')))

    def test_successor_early_guard_refuses_an_apg_from_elsewhere(self):
        os.remove(os.path.join(self.decoy, 'apg', '__init__.py'))
        with open(os.path.join(self.decoy, 'apg', '__init__.py'), 'w') as f:
            f.write('X = 1\n')
        code = 'import sys; sys.path.insert(0, %r); sys.path.insert(0, %r); import tests._path' % (ROOT, self.decoy)
        p = subprocess.run([sys.executable, '-I', '-S', '-c', code], cwd=ROOT, capture_output=True, text=True, timeout=60, env=env(self.tmp))
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('ImportError: apg resolves outside this package root', p.stderr)



class E4DecoyWorkingDirectory(unittest.TestCase):
    """Corrective pass 2, E point 4.  M10 half: M10's run_m2_tests.py, on an M10 view, started -I (its run instruction) from a working
    directory holding a decoy apg package; a probe appended to the view's tests/test_values.py records which apg the run imported.
    Recorded as found: M10 imports the view's own apg, never the decoy (with -I the working directory is not on sys.path), so M10 does
    not have this defect.  Successor half: real runners started from a directory other than the root are refused with ENV_CWD before any
    work, the decoy never imported, each output through check_output.  BUILDER-EXECUTED: NOT INDEPENDENT."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_e4_')
        self.decoy = os.path.join(self.tmp, 'decoy')
        self.marker = os.path.join(self.tmp, 'DECOY_IMPORTED')
        os.makedirs(os.path.join(self.decoy, 'apg'))
        with open(os.path.join(self.decoy, 'apg', '__init__.py'), 'w') as f:
            f.write('open(%r, "a").write("decoy apg imported\\n")\n' % self.marker)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_m10_from_a_decoy_working_directory_imports_its_own_apg(self):
        view = m10_view(os.path.join(self.tmp, 'm10'))
        probe = os.path.join(self.tmp, 'APG_FILE')
        with open(os.path.join(view, 'tests', 'test_values.py'), 'a') as f:
            f.write('\nimport apg as _probe_apg\nopen(%r, "w").write(_probe_apg.__file__)\n' % probe)
        p = subprocess.run([sys.executable, '-I', os.path.join(view, 'tools', 'run_m2_tests.py'), '-q', 'test_values.py'], cwd=self.decoy,
                           capture_output=True, text=True, timeout=300, env=env(self.tmp))
        self.assertEqual(p.returncode, 0, p.stdout[-2000:] + p.stderr[-2000:])
        self.assertFalse(os.path.exists(self.marker), 'M10 imported the decoy from its working directory')
        with open(probe) as f:
            self.assertEqual(os.path.realpath(f.read()), os.path.realpath(os.path.join(view, 'apg', '__init__.py')))

    def test_successor_runners_refuse_a_working_directory_other_than_the_root(self):
        sys.path.insert(0, ROOT)
        import tools.evkit as E
        pins = E.load_pins()[0]
        mid = pins['mutation_lists']['m2_mutants_s1']['ids'][0]
        for cwd in (self.decoy, os.path.join(ROOT, 'tools')):
            for script, args, kw in (('run_m2_tests_s1.py', ['-q', 'test_values.py'], {}),
                                     ('run_contracts_s1.py', [], {'pins': pins['case_inventories']['run_contracts_s1']}),
                                     # amendment 3, AM3-1 (b): a start refusal names every pinned item (C.1's form)
                                     ('m2_mutants_s1.py', ['--ids', mid], {'selected': pins['mutation_lists']['m2_mutants_s1']['ids']})):
                with self.subTest(cwd=cwd, script=script):
                    p = subprocess.run([sys.executable, '-I', '-S', os.path.join(ROOT, 'tools', script)] + args, cwd=cwd, capture_output=True,
                                       text=True, timeout=600, env=env(self.tmp))
                    self.assertEqual(p.returncode, 2, p.stdout[-2000:] + p.stderr[-2000:])
                    self.assertRegex(p.stdout, r'(?m)^RUN_ERROR ENV_CWD ')
                    self.assertFalse(os.path.exists(self.marker))
                    self.assertNotRegex(p.stdout, r'(?m)^(CASE \S+ (PASS|FAIL)|MUTANT \S+ (KILLED|SURVIVED)|FILE \S+ state=COMPLETED) ')
                    self.assertEqual(E.check_output(p.stdout, p.returncode, **kw), [], p.stdout[-3000:])


MANIFEST = 'programme/APG-M11-S1_MANIFEST.csv'
CHECKS = 'tests_m8.test_m8_boundary.TestNoOtherChange'


def boundary_copy(dest):
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns('.git', '__pycache__'), symlinks=True)
    return dest


def run_checks(tree, tmp):
    code = ('import sys, unittest; sys.path.insert(0, %r)\n'
            'r = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(%r))\n'
            'sys.exit(0 if r.wasSuccessful() else 1)\n') % (tree, CHECKS)
    p = subprocess.run([sys.executable, '-I', '-S', '-c', code], cwd=tree, capture_output=True, text=True, timeout=600, env=env(tmp))
    return p.returncode, p.stdout + p.stderr


def rows(tree):
    import csv
    with open(os.path.join(tree, MANIFEST), encoding='utf-8', newline='') as f:
        return list(csv.reader(f))


def write_rows(tree, rs):
    import csv
    with open(os.path.join(tree, MANIFEST), 'w', encoding='utf-8', newline='') as f:
        csv.writer(f, lineterminator='\n').writerows(rs)


def sec(rs, name):
    return [i for i, r in enumerate(rs) if r and r[0] == name]


class BoundaryManifest(unittest.TestCase):
    """Amendment 2 (product owner, 2026-10-31 13:18) §4 item 4: each plant must make a check fail, with the exact reason."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_bman_')
        self.tree = boundary_copy(os.path.join(self.tmp, 't'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def rejected(self, reason):
        code, out = run_checks(self.tree, self.tmp)
        self.assertEqual(code, 1, out[-3000:])
        self.assertIn('S1_MANIFEST_REJECTED %s' % reason, out, out[-3000:])

    def edit(self, fn):
        rs = rows(self.tree)
        fn(rs)
        write_rows(self.tree, rs)

    def first(self, rs, name, status=None):
        return next(i for i in sec(rs, name) if status is None or rs[i][2] == status)

    def test_the_frozen_manifest_passes_both_checks(self):
        code, out = run_checks(self.tree, self.tmp)
        self.assertEqual(code, 0, out[-3000:])

    # ---- the tree, not the manifest
    def test_an_undeclared_change_to_an_r2_file(self):
        with open(os.path.join(self.tree, 'apg', 'ingest', 'pipeline.py'), 'a') as f:
            f.write('\n# changed\n')
        code, out = run_checks(self.tree, self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("apg/ingest/pipeline.py", out)

    def test_an_undeclared_added_file(self):
        with open(os.path.join(self.tree, 'apg', 'extra_module.py'), 'w') as f:
            f.write('X = 1\n')
        code, out = run_checks(self.tree, self.tmp)
        self.assertEqual(code, 1)
        self.assertIn('apg/extra_module.py', out)

    def test_a_copy_of_the_manifest_elsewhere_is_not_exempted(self):
        shutil.copy(os.path.join(self.tree, MANIFEST), os.path.join(self.tree, 'programme', 'APG-M11-S1_MANIFEST_copy.csv'))
        code, out = run_checks(self.tree, self.tmp)
        self.assertEqual(code, 1)
        self.assertIn('programme/APG-M11-S1_MANIFEST_copy.csv', out)

    def test_a_declared_file_edited_after_the_freeze(self):
        with open(os.path.join(self.tree, 'tools', 'evkit.py'), 'a') as f:
            f.write('\n# edited after the manifest was frozen\n')
        self.rejected('DECLARATION_DOES_NOT_HOLD tools/evkit.py')

    def test_a_declared_file_that_does_not_exist(self):
        os.remove(os.path.join(self.tree, 'tools', 'run_contracts_s1.py'))
        self.rejected('DECLARED_FILE_MISSING tools/run_contracts_s1.py')

    def test_the_manifest_removed(self):
        os.remove(os.path.join(self.tree, MANIFEST))
        self.rejected('MANIFEST_MISSING')

    # ---- identity and structure
    def test_a_wrong_header(self):
        self.edit(lambda rs: rs[0].__setitem__(6, 'details'))
        self.rejected('WRONG_IDENTITY header')

    def test_a_wrong_stage_name_or_base(self):
        for value in ('stage=APG-M11-S2;base=APG-M10', 'stage=APG-M11-S1;base=APG-M9'):
            self.edit(lambda rs: rs[sec(rs, 'identity')[0]].__setitem__(6, value))
            self.rejected('WRONG_IDENTITY identity line')

    def test_the_manifest_as_a_symbolic_link(self):
        real = os.path.join(self.tree, 'programme', 'real_manifest.csv')
        os.rename(os.path.join(self.tree, MANIFEST), real)
        os.symlink(real, os.path.join(self.tree, MANIFEST))
        self.rejected('WRONG_IDENTITY')

    def test_an_unknown_section(self):
        self.edit(lambda rs: rs.append(['extras', 'x', 'new', '-', '0' * 64, '-', '-']))
        self.rejected('WRONG_STRUCTURE unknown section extras')

    def test_a_missing_section(self):
        self.edit(lambda rs: [rs.pop(i) for i in reversed(sec(rs, 'records'))])
        self.rejected('WRONG_STRUCTURE sections')

    def test_a_repeated_section(self):
        def f(rs):
            line = rs.pop(sec(rs, 'd1')[0])
            rs.insert(sec(rs, 'records')[0], line)
        self.edit(f)
        self.rejected('WRONG_STRUCTURE sections')

    def test_a_second_supplementary_line(self):
        self.edit(lambda rs: rs.insert(sec(rs, 'supplementary')[0], list(rs[sec(rs, 'supplementary')[0]])))
        self.rejected('WRONG_STRUCTURE supplementary lines 2')

    def test_an_extra_field(self):
        self.edit(lambda rs: rs[sec(rs, 'changed')[0]].append('x'))
        self.rejected('WRONG_STRUCTURE field count')

    def test_a_field_value_the_section_does_not_permit(self):
        self.edit(lambda rs: rs[sec(rs, 'records')[0]].__setitem__(6, 'a record'))
        self.rejected('MALFORMED_STATUS_HASH records')

    # ---- duplicates and accounting
    def test_a_duplicate_path(self):
        self.edit(lambda rs: rs.insert(sec(rs, 'changed')[0], list(rs[sec(rs, 'changed')[0]])))
        self.rejected('DUPLICATE_PATH changed')

    def test_a_path_repeated_within_d1(self):
        self.edit(lambda rs: rs.__setitem__(sec(rs, 'd1')[1], list(rs[sec(rs, 'd1')[0]])))   # still 89 lines, one path twice
        self.rejected('DUPLICATE_PATH d1')

    def test_the_same_path_declared_both_modified_and_new(self):
        def f(rs):
            i = next(i for i in sec(rs, 'changed') if rs[i][2] == 'new' and rs[i][1] == 'tools/evkit.py')
            rs[i][2], rs[i][3] = 'modified', 'a' * 64
        self.edit(f)
        self.rejected('UNACCOUNTED_OR_CONFLICTING d1 tools/evkit.py')

    def test_conflicting_stage1_hashes(self):
        def f(rs):
            i = next(i for i in sec(rs, 'd1') if rs[i][1] == 'tests/_path.py')
            rs[i][4] = 'b' * 64
        self.edit(f)
        self.rejected('UNACCOUNTED_OR_CONFLICTING d1 tests/_path.py')

    def test_a_changed_path_that_nothing_accounts_for(self):
        with open(os.path.join(self.tree, 'apg', 'extra_module.py'), 'w') as f:
            f.write('X = 1\n')
        import hashlib
        h = hashlib.sha256(b'X = 1\n').hexdigest()
        self.edit(lambda rs: rs.append(['changed', 'apg/extra_module.py', 'new', '-', h, '-', '-']))
        self.rejected('UNACCOUNTED_OR_CONFLICTING unaccounted apg/extra_module.py')

    def test_a_d1_modified_path_missing_from_changed(self):
        self.edit(lambda rs: rs.pop(next(i for i in sec(rs, 'changed') if rs[i][1] == 'tests/_path.py')))
        self.rejected('UNACCOUNTED_OR_CONFLICTING d1 tests/_path.py')

    def test_a_path_accounted_for_by_both_d1_and_records(self):
        def f(rs):
            ev = next(rs[i] for i in sec(rs, 'changed') if rs[i][1] == 'tools/evkit.py')
            rs.insert(sec(rs, 'records')[0], ['records', 'tools/evkit.py', 'new', '-', ev[4], '-', 'stage 1 record'])
        self.edit(f)
        self.rejected('UNACCOUNTED_OR_CONFLICTING accounted twice tools/evkit.py')

    # ---- unsafe paths
    def plant_path(self, path, reason):
        self.edit(lambda rs: rs.append(['changed', path, 'new', '-', 'c' * 64, '-', '-']))
        self.rejected(reason)

    def test_an_absolute_path(self):
        self.plant_path('/etc/passwd', 'UNSAFE_PATH /etc/passwd')

    def test_a_dotdot_path(self):
        self.plant_path('tools/../../outside.py', 'UNSAFE_PATH tools/../../outside.py')

    def test_a_backslash_path(self):
        self.plant_path('tools\\evkit.py', 'UNSAFE_PATH tools\\evkit.py')

    def test_a_git_path(self):
        self.plant_path('.git/config', 'UNSAFE_PATH .git/config')

    def test_the_manifest_declaring_itself(self):
        self.plant_path(MANIFEST, 'MANIFEST_DECLARES_ITSELF')

    def test_a_declared_file_that_is_a_link_to_an_in_tree_file(self):
        p = os.path.join(self.tree, 'tools', 'run_contracts_s1.py')
        os.remove(p)
        os.symlink(os.path.join(self.tree, 'tools', 'run_contracts.py'), p)
        self.rejected('SYMBOLIC_LINK tools/run_contracts_s1.py')

    def test_a_declared_path_through_a_linked_folder(self):
        d = os.path.join(self.tree, 'tests_tools')
        os.rename(d, d + '_real')
        os.symlink(d + '_real', d)
        self.rejected('SYMBOLIC_LINK tests_tools/')

    def test_a_declared_link_to_a_file_outside_the_tree(self):
        outside = os.path.join(self.tmp, 'outside.py')
        p = os.path.join(self.tree, 'tools', 'run_contracts_s1.py')
        shutil.copy(p, outside)
        os.remove(p)
        os.symlink(outside, p)
        self.rejected('SYMBOLIC_LINK tools/run_contracts_s1.py')

    # ---- status and hash forms
    def test_an_upper_case_or_short_hash(self):
        for bad in (lambda h: h.upper(), lambda h: h[:40]):
            self.edit(lambda rs, bad=bad: rs[self.first(rs, 'changed', 'new')].__setitem__(4, bad(rs[self.first(rs, 'changed', 'new')][4])))
            self.rejected('MALFORMED_STATUS_HASH changed')
            shutil.rmtree(self.tree)
            self.tree = boundary_copy(os.path.join(self.tmp, 't'))

    def test_a_modified_line_with_no_m10_hash(self):
        self.edit(lambda rs: rs[self.first(rs, 'changed', 'modified')].__setitem__(3, '-'))
        self.rejected('MALFORMED_STATUS_HASH changed')

    def test_a_new_line_for_a_path_the_r2_manifest_holds(self):
        def f(rs):
            i = next(i for i in sec(rs, 'changed') if rs[i][1] == 'tests/_path.py')
            rs[i][2], rs[i][3] = 'new', '-'
        self.edit(f)
        self.rejected('MALFORMED_STATUS_HASH new but in R2 tests/_path.py')

    def test_an_unknown_status(self):
        self.edit(lambda rs: rs[self.first(rs, 'changed', 'new')].__setitem__(2, 'added'))
        self.rejected('MALFORMED_STATUS_HASH changed')


STEPS_W1A = (('run_regression_m8_s1.py', 'R01'), ('run_regression_m8_s1.py', 'R02'), ('run_regression_m8_s1.py', 'R10'),
             ('run_regression_m81_s1.py', 'R01'), ('run_regression_m81_s1.py', 'R02'))


def run_step(tree, tmp, tool, step):
    p = subprocess.run([sys.executable, '-I', '-S', os.path.join('tools', tool), '--step', step], cwd=tree, capture_output=True, text=True,
                       timeout=900, env=env(tmp))
    line = next((l for l in p.stdout.splitlines() if l.startswith(('PASS %s ' % step, 'FAIL %s ' % step))), '')
    return p.returncode, line, p.stdout + p.stderr


class RegressionManifestW1A(unittest.TestCase):
    """Decision W-1A.2 (ii) (a) (owner, 2026-11-01 06:22): run_regression_m8_s1 R01, R02, R10 and run_regression_m81_s1 R01, R02 also
    permit exactly what the frozen stage 1 manifest declares, validated by amendment 2's validator, each declared file only at its exact
    recorded stage 1 hash.  The planted faults: an undeclared added file, an undeclared changed file, a declared file with other contents,
    a missing manifest and a malformed one; each must make the steps fail.  Like BoundaryManifest, these need the tree's manifest to be
    current; each plant is made in a copy."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_regman_')
        self.tree = boundary_copy(os.path.join(self.tmp, 't'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def results(self, steps=STEPS_W1A):
        return {(t, s): run_step(self.tree, self.tmp, t, s) for t, s in steps}

    def test_the_frozen_manifest_passes_the_five_steps(self):
        for k, (code, line, out) in self.results().items():
            self.assertEqual(code, 0, (k, out[-2000:]))
            self.assertIn('[APG-M11-S1, decision W-1A.2 (ii) (a): also permitted, and only at their exact recorded stage 1 hashes', line)

    def test_an_undeclared_added_file_fails(self):
        with open(os.path.join(self.tree, 'tools', 'zz_undeclared_by_stage1.py'), 'w') as f:
            f.write('# planted by tests_tools/test_apg_root.py\n')
        r = self.results([('run_regression_m8_s1.py', 'R02'), ('run_regression_m81_s1.py', 'R02')])
        for k, (code, line, out) in r.items():
            self.assertEqual(code, 1, (k, out[-2000:]))
            self.assertTrue(line.startswith('FAIL') and 'zz_undeclared_by_stage1.py' in line, (k, line))

    def test_an_undeclared_changed_file_fails(self):
        with open(os.path.join(self.tree, 'apg', 'tenancy.py'), 'a') as f:
            f.write('\n# planted by tests_tools/test_apg_root.py\n')
        r = self.results([('run_regression_m8_s1.py', 'R01'), ('run_regression_m8_s1.py', 'R10'), ('run_regression_m81_s1.py', 'R01')])
        for k, (code, line, out) in r.items():
            self.assertEqual(code, 1, (k, out[-2000:]))
            self.assertTrue(line.startswith('FAIL') and 'apg/tenancy.py' in line, (k, line))

    def test_a_declared_file_with_other_contents_fails(self):
        rs = rows(self.tree)
        new = [rs[i][1] for i in sec(rs, 'changed') if rs[i][2] == 'new' and rs[i][1].startswith('programme/')][0]
        with open(os.path.join(self.tree, new), 'a') as f:
            f.write('\nplanted by tests_tools/test_apg_root.py\n')
        for k, (code, line, out) in self.results().items():
            self.assertEqual(code, 1, (k, out[-2000:]))
            self.assertIn('the frozen stage 1 manifest was rejected, so the step was not judged (S1_MANIFEST_REJECTED DECLARATION_DOES_NOT_HOLD %s' % new, line)

    def test_a_missing_manifest_fails(self):
        os.remove(os.path.join(self.tree, MANIFEST))
        for k, (code, line, out) in self.results().items():
            self.assertEqual(code, 1, (k, out[-2000:]))
            self.assertIn('(S1_MANIFEST_REJECTED MANIFEST_MISSING', line)

    def test_a_malformed_manifest_fails(self):
        rs = rows(self.tree)
        rs[0] = rs[0][:-1] + ['details']
        write_rows(self.tree, rs)
        for k, (code, line, out) in self.results().items():
            self.assertEqual(code, 1, (k, out[-2000:]))
            self.assertIn('(S1_MANIFEST_REJECTED WRONG_IDENTITY header', line)


if __name__ == '__main__':
    unittest.main()
