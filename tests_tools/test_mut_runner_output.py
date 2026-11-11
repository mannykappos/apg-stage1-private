"""Stage 1 (APG-M11-S1), Workstream T, E1-C8, P1-F5 and T-0: the kill oracle reports proof of work.  On M10, tools/mut_runner.py prints
nothing when every file passes (E1-C8: exit 0 with no counts and no import identity).  The successor tools/mut_runner_s1.py prints a FILE
line per named file with the pinned counts, keeps the 'FAIL <short name>' attribution, and ends with a RESULT v=2 line that the checker
reconciles against the pins.  Each case runs on an M10 view (test_apg_root.m10_view) and on the successor.
Run from the package root:  python3 -I -S tests_tools/test_mut_runner_output.py      BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.evkit as E  # noqa: E402
from tests_tools.test_apg_root import m10_view  # noqa: E402


def env(tmp):
    return {'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': tmp, 'PYTHONDONTWRITEBYTECODE': '1'}


def run(cmd, cwd, tmp):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=600, env=env(tmp))
    return p.returncode, p.stdout, p.stderr


def evidence(out):
    return '\n'.join(l for l in out.splitlines() if not l.startswith(('ENV ', 'IMPORT ', 'IMPORT_END ')))


class MutRunnerOutput(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='s1_mutrunner_')
        self.pins, _ = E.load_pins()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_m10_prints_nothing_on_success(self):
        view = m10_view(os.path.join(self.tmp, 'm10'))
        code, out, err = run([sys.executable, '-I', 'tools/mut_runner.py', 'test_values.py'], view, self.tmp)
        self.assertEqual((code, out), (0, ''))

    def test_successor_prints_the_pinned_counts_and_reconciles(self):
        code, out, err = run([sys.executable, '-I', '-S', 'tools/mut_runner_s1.py', 'test_values.py'], ROOT, self.tmp)
        self.assertEqual(code, 0, out[-2000:] + err[-2000:])
        n = len(self.pins['test_files']['tests/test_values.py']['ids'])
        self.assertRegex(out, r'(?m)^FILE test_values\.py state=COMPLETED tests=%d passed=%d failed=0 errors=0 skipped=0 tests_not_run=0 ' % (n, n))
        last = [l for l in out.splitlines() if l.strip()][-1]
        self.assertTrue(last.startswith('RESULT v=2 kind=tests tool=mut_runner_s1 mode=failfast '), last)
        self.assertIn(' files_selected=1 files_started=1 files_completed=1 ', last)
        self.assertIn(' status=OK exit=0', last)
        fp = E.test_file_pins(self.pins, ['tests/test_values.py'])
        self.assertEqual(E.check_output(evidence(out), code, pins=fp, selected=['test_values.py']), [])

    def mutated_copy(self):
        dest = os.path.join(self.tmp, 'mutant')
        shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__'))
        p = os.path.join(dest, 'apg', 'canon.py')
        src = open(p).read()
        old = "return ''.join(out).lower()"  # M10's CA07-case-kept mutant
        self.assertEqual(src.count(old), 1)
        with open(p, 'w') as f:
            f.write(src.replace(old, "return ''.join(out)"))
        return dest

    def test_successor_failure_attribution_and_skipped_files(self):
        dest = self.mutated_copy()
        code, out, err = run([sys.executable, '-I', '-S', 'tools/mut_runner_s1.py', 'test_values.py', 'test_tenancy.py'], dest, self.tmp)
        self.assertEqual(code, 1, out[-3000:] + err[-2000:])
        self.assertIn('FAIL test_values', out.splitlines())  # M10's short name for test_values.py (mut_runner.py:12)
        self.assertRegex(out, r'(?m)^FILE test_tenancy\.py state=SKIPPED_AFTER_FAILURE tests=0 ')
        self.assertIn(' files_skipped_after_failure=1 ', out)
        self.assertIn(' status=FAILED exit=1', out)
        fp = E.test_file_pins(self.pins, ['tests/test_values.py', 'tests/test_tenancy.py'])
        self.assertEqual(E.check_output(evidence(out), code, pins=fp, selected=['test_values.py', 'test_tenancy.py']), [])

    def test_m10_failure_prints_only_the_short_name(self):
        dest = self.mutated_copy()
        m10 = m10_view(os.path.join(self.tmp, 'm10mut'))
        shutil.copy(os.path.join(dest, 'apg', 'canon.py'), os.path.join(m10, 'apg', 'canon.py'))
        code, out, err = run([sys.executable, '-I', 'tools/mut_runner.py', 'test_values.py', 'test_tenancy.py'], m10, self.tmp)
        self.assertEqual((code, out), (1, 'test_values\n'))

    def test_unpinned_name_and_no_names(self):
        code, out, err = run([sys.executable, '-I', '-S', 'tools/mut_runner_s1.py', 'test_values.py', 'test_no_such_file.py'], ROOT, self.tmp)
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR TEST_FILE_NOT_IN_PINS test_no_such_file.py', out)
        self.assertRegex(out, r'(?m)^FILE test_values\.py state=NOT_RUN ')  # every file NOT_RUN: the names are checked before any runs
        code, out, err = run([sys.executable, '-I', '-S', 'tools/mut_runner_s1.py'], ROOT, self.tmp)
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR SELECTION_INVALID no_files', out)
        code, out, err = run([sys.executable, '-I', 'tools/mut_runner.py'], ROOT, self.tmp)
        self.assertEqual((code, out), (0, ''))  # M10: no names at all is a silent success (zero work, P1-F5)


    C8 = ['test_adversarial_builder_zero.py', 'test_golden.py', 'test_materiality_engine.py', 'test_repro.py', 'test_source_authority.py',
          'test_status_model.py', 'test_tenancy.py', 'test_values.py']


    # corrective pass 2, E point 22: the standalone pin, and F11 on mut_runner_s1's failing file, asserted directly
    def test_e22_the_standalone_pin_and_f11_on_the_failing_file(self):
        import re
        self.assertEqual(self.pins['runner_profiles']['mut_runner_s1@standalone'], {'mode': 'failfast'})
        dest = self.mutated_copy()
        code, out, err = run([sys.executable, '-I', '-S', 'tools/mut_runner_s1.py', 'test_values.py', 'test_tenancy.py'], dest, self.tmp)
        self.assertEqual(code, 1, out[-3000:] + err[-2000:])
        self.assertIn(' mode=failfast ', out.strip().splitlines()[-1])        # no --caller: the standalone profile, as pinned
        pin = self.pins['test_files']['tests/test_values.py']
        m = re.search(r'(?m)^FILE test_values\.py state=COMPLETED tests=(\d+) passed=\d+ failed=([1-9]\d*) errors=\d+ skipped=\d+ '
                      r'tests_not_run=(\d+) file_sha256=(\S+) ', out)
        self.assertTrue(m, out[-3000:])
        self.assertEqual(int(m.group(1)) + int(m.group(3)), len(pin['ids']))
        self.assertEqual(m.group(4), pin['sha256'])
        tests = re.findall(r'(?m)^TEST test_values\.py::(\S+) (\S+)$', out)
        self.assertEqual([t[0] for t in tests], pin['ids'])                     # one TEST line per pinned test, in pinned order
        self.assertEqual(sum(1 for t in tests if t[1] == 'NOT_RUN_AFTER_FAILURE'), int(m.group(3)))
        self.assertEqual(sum(1 for t in tests if t[1] == 'FAIL'), int(m.group(2)))
        self.assertNotRegex(out, r'(?m)^TEST test_tenancy\.py::\S+ (PASS|FAIL|ERROR)$')

    # corrective pass 2, E point 20: E1-C8's genuine-kill attribution compared with M10's, on the eight C8 files
    def test_e20_the_c8_kill_attribution_matches_m10(self):
        import re
        dest = self.mutated_copy()
        m10 = m10_view(os.path.join(self.tmp, 'm10c8'))
        shutil.copy(os.path.join(dest, 'apg', 'canon.py'), os.path.join(m10, 'apg', 'canon.py'))
        code, out, err = run([sys.executable, '-I', 'tools/mut_runner.py'] + self.C8, m10, self.tmp)
        self.assertEqual(code, 1, out + err[-1500:])
        m10_name = out.strip()
        self.assertTrue(m10_name and '\n' not in m10_name, out)
        code, out, err = run([sys.executable, '-I', '-S', 'tools/mut_runner_s1.py'] + self.C8, dest, self.tmp)
        self.assertEqual(code, 1, out[-3000:] + err[-2000:])
        self.assertEqual([l[5:] for l in out.splitlines() if l.startswith('FAIL ')], [m10_name])
        first = [n for n, f in re.findall(r'(?m)^FILE (\S+) state=COMPLETED .* failed=(\d+) ', out) if f != '0']
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0].replace('.py', ''), m10_name)
        rels = ['tests/' + f for f in self.C8]
        self.assertEqual(E.check_output(evidence(out), code, pins=E.test_file_pins(self.pins, rels), selected=self.C8), [])

    def test_the_eight_c8_files(self):
        # E1-C8 (R4/R5): the P1 run record's command C8 (M10: exit 0 and no output at all); the successor prints the eight pinned counts
        rels = ['tests/' + f for f in self.C8]
        view = m10_view(os.path.join(self.tmp, 'm10'))
        code, out, err = run([sys.executable, '-I', 'tools/mut_runner.py'] + self.C8, view, self.tmp)
        self.assertEqual((code, out), (0, ''))
        code, out, err = run([sys.executable, '-I', '-S', 'tools/mut_runner_s1.py'] + self.C8, ROOT, self.tmp)
        self.assertEqual(code, 0, out[-3000:] + err[-2000:])
        for r in rels:
            n = len(self.pins['test_files'][r]['ids'])
            self.assertRegex(out, r'(?m)^FILE %s state=COMPLETED tests=%d passed=%d failed=0 errors=0 skipped=0 tests_not_run=0 '
                             % (os.path.basename(r).replace('.', r'\.'), n, n))
        self.assertIn(' files_selected=8 files_started=8 files_completed=8 ', out.strip().splitlines()[-1])
        self.assertEqual(E.check_output(evidence(out), code, pins=E.test_file_pins(self.pins, rels), selected=self.C8), [])

    def test_a_known_and_an_unpinned_name(self):
        # P1-F5 (R4): a run error before any file started: both files NOT_RUN, files_not_run=2, exit 2, the known file not run
        code, out, err = run([sys.executable, '-I', '-S', 'tools/mut_runner_s1.py', 'test_values.py', 'test_nope.py'], ROOT, self.tmp)
        self.assertEqual(code, 2, out[-2000:])
        self.assertIn('RUN_ERROR TEST_FILE_NOT_IN_PINS test_nope.py', out)
        self.assertRegex(out, r'(?m)^FILE test_values\.py state=NOT_RUN ')
        self.assertRegex(out, r'(?m)^FILE test_nope\.py state=NOT_RUN ')
        self.assertNotRegex(out, r'(?m)^TEST test_values\.py::')
        last = out.strip().splitlines()[-1]
        self.assertIn(' files_selected=2 files_started=0 ', last)
        self.assertIn(' files_not_run=2 ', last)
        self.assertTrue(last.endswith(' status=EVIDENCE_ERROR exit=2'))
        self.assertEqual(E.check_output(evidence(out), code), [])

    def test_no_names(self):
        # P1-F5: M10 with no arguments exits 0 having run nothing; the successor exits 2 with its RUN_ERROR and RESULT lines
        view = m10_view(os.path.join(self.tmp, 'm10n'))
        self.assertEqual(run([sys.executable, '-I', 'tools/mut_runner.py'], view, self.tmp)[:2], (0, ''))
        code, out, err = run([sys.executable, '-I', '-S', 'tools/mut_runner_s1.py'], ROOT, self.tmp)
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR SELECTION_INVALID no_files', out)
        self.assertTrue(out.strip().splitlines()[-1].endswith(' status=EVIDENCE_ERROR exit=2'))
        self.assertEqual(E.check_output(evidence(out), code), [])

    def test_failfast_and_full_on_the_three_named_files(self):
        # P1-F5 (R5): with test_values.py failing (here through M10's CA07 mutant of apg/canon.py, which test_values.py catches: the test
        # file itself cannot be edited, its hash is pinned), mut_runner_s1 (failfast) completes it with a failure and skips the other two;
        # run_test_files_s1 (full) completes all three; both exit 1
        dest = self.mutated_copy()
        names = ['test_values.py', 'test_fin_arith.py', 'test_fin_intake.py']
        fp = E.test_file_pins(self.pins, ['tests/' + n for n in names])
        code, out, err = run([sys.executable, '-I', '-S', 'tools/mut_runner_s1.py'] + names, dest, self.tmp)
        self.assertEqual(code, 1, out[-3000:])
        self.assertRegex(out, r'(?m)^FILE test_values\.py state=COMPLETED .* failed=[1-9]')
        for n in names[1:]:
            self.assertRegex(out, r'(?m)^FILE %s state=SKIPPED_AFTER_FAILURE ' % n.replace('.', r'\.'))
        last = out.strip().splitlines()[-1]
        self.assertIn(' mode=failfast ', last)
        self.assertIn(' files_not_run=0 files_skipped_after_failure=2 ', last)
        self.assertTrue(last.endswith(' status=FAILED exit=1'))
        self.assertEqual(E.check_output(evidence(out), code, pins=fp, selected=names), [])
        code, out, err = run([sys.executable, '-I', '-S', 'tools/run_test_files_s1.py', '-q'] + names, dest, self.tmp)
        self.assertEqual(code, 1, out[-3000:])
        for n in names:
            self.assertRegex(out, r'(?m)^FILE %s state=COMPLETED ' % n.replace('.', r'\.'))
        last = out.strip().splitlines()[-1]
        self.assertIn(' mode=full ', last)
        self.assertIn(' files_completed=3 ', last)
        self.assertIn(' files_skipped_after_failure=0 ', last)
        self.assertTrue(last.endswith(' status=FAILED exit=1'))
        self.assertEqual(E.check_output(evidence(out), code, pins=fp, selected=names), [])

    def test_run_m2_tests_s1_in_each_of_its_pinned_modes(self):
        # DP-2.3 F3, F4 and F11 on the real runner (authorisation §4.6), in a copy where M10's CA07 mutant makes test_materiality_engine.py
        # fail: as a mutation tool's kill oracle (--failfast --caller mutation_tool, pinned failfast) the failing file stops at its first
        # failing test and is COMPLETED with tests_not_run recorded (F11), and every later file is SKIPPED_AFTER_FAILURE; as a wrapper's child
        # (--caller wrapper, pinned full) it runs every test of every file past the failure and never reports SKIPPED_AFTER_FAILURE
        dest = self.mutated_copy()
        pattern = 'test_m[ai]*.py'
        rels = sorted(k for k in self.pins['test_files'] if k.startswith('tests/test_m') and os.path.basename(k)[6] in 'ai')
        names = [os.path.basename(r) for r in rels]
        self.assertEqual(names[0], 'test_materiality_engine.py')
        self.assertGreater(len(names), 5)
        fp = E.test_file_pins(self.pins, rels)
        code, out, err = run([sys.executable, '-I', '-S', 'tools/run_m2_tests_s1.py', '-q', '--failfast', '--caller', 'mutation_tool', pattern],
                             dest, self.tmp)
        self.assertEqual(code, 1, out[-3000:] + err[-2000:])
        import re
        m = re.search(r'(?m)^FILE test_materiality_engine\.py state=COMPLETED tests=(\d+) passed=\d+ failed=[1-9]\d* .* tests_not_run=(\d+) ', out)
        self.assertTrue(m, out[-3000:])
        self.assertEqual(int(m.group(1)) + int(m.group(2)), len(fp['test_materiality_engine.py']['ids']))
        self.assertGreater(int(m.group(2)), 0)
        for n in names[1:]:
            self.assertRegex(out, r'(?m)^FILE %s state=SKIPPED_AFTER_FAILURE ' % re.escape(n))
        last = out.strip().splitlines()[-1]
        self.assertIn(' mode=failfast ', last)
        self.assertIn(' files_skipped_after_failure=%d ' % (len(names) - 1), last)
        self.assertEqual(E.check_output(evidence(out), code, pins=fp, selected=names), [])
        code, out, err = run([sys.executable, '-I', '-S', 'tools/run_m2_tests_s1.py', '-q', '--caller', 'wrapper', pattern], dest, self.tmp)
        self.assertEqual(code, 1, out[-3000:] + err[-2000:])
        for n in names:
            self.assertRegex(out, r'(?m)^FILE %s state=COMPLETED .* tests_not_run=0 ' % re.escape(n))
        self.assertNotIn('SKIPPED_AFTER_FAILURE', out)
        last = out.strip().splitlines()[-1]
        self.assertIn(' mode=full ', last)
        self.assertIn(' files_completed=%d ' % len(names), last)
        self.assertEqual(E.check_output(evidence(out), code, pins=fp, selected=names), [])
        # the same runner refuses a mode its caller is not pinned to (F10): --failfast for the wrapper caller
        code, out, err = run([sys.executable, '-I', '-S', 'tools/run_m2_tests_s1.py', '-q', '--failfast', '--caller', 'wrapper', pattern],
                             dest, self.tmp)
        self.assertEqual(code, 2, out[-2000:])
        self.assertIn('RUN_ERROR RUNNER_MODE_NOT_PINNED run_m2_tests_s1@wrapper mode=failfast pinned=full', out)


if __name__ == '__main__':
    unittest.main()
