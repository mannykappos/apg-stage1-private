"""Stage 1 (APG-M11-S1), Workstream T, P3-B04 (DP-4.3 (c)): a candidate cannot shadow the trusted harness.
Helper level (tools/evkit.load_candidate and candidate_check) and runner level: each kind=cases successor against its M10 runner, with a
candidate directory that carries its own copy of the harness (the M10 runners put --path first on sys.path, so the fake harness runs).
Run from the package root:  python3 -I -S tests_tools/test_harness_isolation.py      BUILDER-EXECUTED: NOT INDEPENDENT."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def base_env(tmp):
    return {'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': tmp,
            'PYTHONDONTWRITEBYTECODE': '1'}


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(text)


class CandidateLoading(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='s1_cand_')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def load(self, spec):
        """Run load_candidate in a fresh isolated child (so a refused candidate cannot affect this process); return its output."""
        script = ('import sys; sys.path.insert(0, %r); import tools.evkit as E\n'
                  'import apg, apg.det\n'
                  'm, errs = E.load_candidate(%r, %r)\n'
                  'print("LOADED" if m is not None else "REFUSED")\n'
                  'print("\\n".join(e.line() for e in errs))\n') % (ROOT, self.dir, spec)
        p = subprocess.run([sys.executable, '-I', '-S', '-c', script], cwd=ROOT, capture_output=True, text=True, timeout=60,
                           env=base_env(tempfile.gettempdir()))
        return p.stdout + p.stderr

    def test_fake_harness_in_the_candidate_directory_is_refused(self):
        # the M10 attack: a candidate directory carrying its own apg/det/contracts_m5.py whose run_all passes everything
        write(os.path.join(self.dir, 'apg', '__init__.py'), '')
        write(os.path.join(self.dir, 'apg', 'det', '__init__.py'), '')
        write(os.path.join(self.dir, 'apg', 'det', 'contracts_m5.py'), 'def run_all(*a, **k):\n    return []\n')
        write(os.path.join(self.dir, 'engine_adapter', '__init__.py'), 'X = 1\n')
        out = self.load('engine_adapter')
        self.assertIn('REFUSED', out)
        self.assertIn('RUN_ERROR CANDIDATE_SHADOWS_TRUSTED apg', out)

    def test_each_trusted_name_is_refused(self):
        for name in ('tools', 'mie', 'apg_ui', 'tests', 'tests_m10', 'apg_auif', 'auif_m8', 'tests_m8'):
            d = os.path.join(self.dir, name)
            write(os.path.join(d, '__init__.py'), '')
            out = self.load('nothing_here')
            self.assertIn('RUN_ERROR CANDIDATE_SHADOWS_TRUSTED %s' % name, out, name)
            shutil.rmtree(d)

    def test_tools_evkit_file_in_the_candidate_is_refused(self):
        write(os.path.join(self.dir, 'tools', 'evkit.py'), 'TRUSTED_PACKAGES = ()\n')
        out = self.load('nothing_here')
        self.assertIn('RUN_ERROR CANDIDATE_SHADOWS_TRUSTED tools', out)

    def test_a_trusted_spec_name_is_refused(self):
        write(os.path.join(self.dir, 'adapter', '__init__.py'), '')
        for spec in ('tests_m10.x', 'apg.det.contracts_m5', 'tools', 'mie.core'):
            out = self.load(spec)
            self.assertIn('REFUSED', out, spec)
            self.assertIn('RUN_ERROR CANDIDATE_SHADOWS_TRUSTED %s' % spec, out, spec)

    def test_a_clean_candidate_in_its_own_package_loads(self):
        write(os.path.join(self.dir, 'engine_adapter', '__init__.py'), 'X = 1\n')
        out = self.load('engine_adapter')
        self.assertIn('LOADED', out)
        self.assertNotIn('RUN_ERROR', out)

    def test_the_candidate_path_is_appended_not_inserted_first(self):
        write(os.path.join(self.dir, 'engine_adapter', '__init__.py'), 'X = 1\n')
        script = ('import sys; sys.path.insert(0, %r); import tools.evkit as E\n'
                  'm, errs = E.load_candidate(%r, "engine_adapter")\n'
                  'print(sys.path[-1] == %r, sys.path[0] == %r)\n') % (ROOT, self.dir, os.path.realpath(self.dir), ROOT)
        p = subprocess.run([sys.executable, '-I', '-S', '-c', script], cwd=ROOT, capture_output=True, text=True, timeout=60,
                           env=base_env(tempfile.gettempdir()))
        self.assertIn('True True', p.stdout, p.stdout + p.stderr)

    def test_a_candidate_that_fails_to_import_is_a_run_error(self):
        write(os.path.join(self.dir, 'engine_adapter', '__init__.py'), 'raise RuntimeError("boom")\n')
        out = self.load('engine_adapter')
        self.assertIn('REFUSED', out)
        self.assertIn('RUN_ERROR CANDIDATE_IMPORT_FAILED engine_adapter RuntimeError', out)


FAKE_HARNESS = {  # the trusted harness module each M10 runner imports, replaced by one that runs no case and reports nothing
    'run_contracts': ('apg/contracts/run.py', 'def run(*a, **k):\n    return []\ndef summarise(res):\n    return 0, 0, None\n',
                      ['apg/contracts/framework.py'], 'class ContractEnv: pass\n', '--factory'),
    'run_m5_contracts': ('apg/det/contracts_m5.py', 'def run_all(*a, **k):\n    return []\n',
                         ['apg/det/reference_m5.py'], 'def notify_env():\n    return None\n', '--notify'),
    'run_det_corpus': ('apg/det/corpus_det.py', 'def cases():\n    return []\n', [], '', '--world'),
    'run_fin_corpus': ('apg/fin/corpus_fin.py', 'def cases():\n    return []\n', [], '', '--world'),
    'run_m3_contracts': ('apg/ingest/contracts_m3.py', 'def run_all(*a, **k):\n    return []\n', ['apg/ingest/reference_m3.py'],
                         'def file_env():\n    return None\ndef job_env():\n    return None\n', '--files'),
    'run_ingest_corpus': ('apg/ingest/corpus.py', 'def cases():\n    return []\n',
                          ['apg/tenancy.py', 'apg/ports.py', 'apg/reference_impl.py', 'apg/ingest/demo_setup.py', 'apg/ingest/pipeline.py',
                           'apg/ingest/mapping.py'],
                          'TenantMismatch = FakeClock = InMemoryAuditLog = InMemoryRecordStore = StaticContextProvider = Limits = None\n'
                          'DEMO_POLICY = None\ndef ingest_file(*a, **k):\n    return None\n', '--ingest'),
    'run_m6_contracts': ('apg/mkt/contracts_m6.py', 'def run_all(*a, **k):\n    return []\n', ['apg/mkt/reference_m6.py'],
                         'def feed_env():\n    return None\ndef extract_env():\n    return None\n', '--feed'),
    'run_m91_contracts': ('apg/api/contracts_m9.py', 'def run_all(*a, **k):\n    return []\n', ['apg/api/reference_m9.py'],
                          'def action_env():\n    return None\n', '--action'),
}


class RunnerLevel(unittest.TestCase):
    """P3-B04 at runner level.  The M10 runners are byte-identical in this tree (DP-1.2 (B)) and none of them reads tests/_path.py or
    tests_m8/_auif.py, so they are run here as they are."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='s1_fakeh_')
        self.tmp = tempfile.mkdtemp(prefix='s1_fakeh_tmp_')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def plant(self, tool):
        rel, text, others, other_text, opt = FAKE_HARNESS[tool]
        for d in ('apg', os.path.dirname(rel)):
            write(os.path.join(self.dir, d, '__init__.py'), '')
        write(os.path.join(self.dir, rel), text)
        for o in others:
            write(os.path.join(self.dir, o), other_text)
        write(os.path.join(self.dir, 'engine_adapter', '__init__.py'), 'def F(*a, **k):\n    raise AssertionError("never called")\n')
        return opt

    def run_tool(self, script, *args):
        p = subprocess.run([sys.executable, '-I', '-S', os.path.join('tools', script)] + list(args), cwd=ROOT, capture_output=True,
                           text=True, timeout=600, env=base_env(self.tmp))
        return p.returncode, p.stdout, p.stderr

    def test_m10_runners_run_the_fake_harness_and_report_success(self):
        for tool in FAKE_HARNESS:
            opt = self.plant(tool)
            code, out, err = self.run_tool(tool + '.py', '--path', self.dir, opt, 'engine_adapter:F')
            self.assertEqual(code, 0, tool + out + err)
            self.assertRegex(out, r'(contract|corpus) cases 0  failed 0', tool)  # zero cases, reported as a pass
            self.assertRegex(out, r'ALL (CONTRACT|CORPUS) CASES PASS', tool)
            shutil.rmtree(self.dir)
            os.makedirs(self.dir)

    def test_successors_refuse_the_fake_harness(self):
        for tool in FAKE_HARNESS:
            opt = self.plant(tool)
            code, out, err = self.run_tool(tool + '_s1.py', '--path', self.dir, opt, 'engine_adapter:F')
            self.assertEqual(code, 2, tool + out[-2000:] + err[-2000:])
            self.assertIn('RUN_ERROR CANDIDATE_SHADOWS_TRUSTED apg', out, tool)
            self.assertNotRegex(out, r'(?m)^CASE \S+ (PASS|FAIL) ', tool)  # every case NOT_RUN
            self.assertNotIn('CASES PASS', out, tool)
            self.assertRegex(out.strip().splitlines()[-1], r' started=0 .* status=EVIDENCE_ERROR exit=2$', tool)
            shutil.rmtree(self.dir)
            os.makedirs(self.dir)

    def test_successor_runners_refuse_every_trusted_name_in_the_candidate(self):
        # P3-B04 (R4) at runner level: a candidate directory holding tools/evkit.py, a top-level tools package, mie/ or apg_ui/, or a
        # candidate module named tests_m10.x, is refused with exit 2 before any case
        cases = [('tools/evkit.py', 'tools', 'engine_adapter:F'), ('tools/__init__.py', 'tools', 'engine_adapter:F'),
                 ('mie/__init__.py', 'mie', 'engine_adapter:F'), ('apg_ui/__init__.py', 'apg_ui', 'engine_adapter:F'),
                 (None, 'tests_m10', 'tests_m10.x:F')]
        for rel, name, spec in cases:
            with self.subTest(rel=rel, spec=spec):
                write(os.path.join(self.dir, 'engine_adapter', '__init__.py'), 'def F(*a, **k):\n    raise AssertionError("never called")\n')
                if rel:
                    write(os.path.join(self.dir, rel), 'X = 1\n')
                code, out, err = self.run_tool('run_m5_contracts_s1.py', '--path', self.dir, '--notify', spec)
                self.assertEqual(code, 2, out[-2000:] + err[-2000:])
                self.assertIn('RUN_ERROR CANDIDATE_SHADOWS_TRUSTED %s' % name, out)
                self.assertNotRegex(out, r'(?m)^CASE \S+ (PASS|FAIL) ')
                self.assertTrue(out.strip().splitlines()[-1].endswith(' status=EVIDENCE_ERROR exit=2'))
                shutil.rmtree(self.dir)
                os.makedirs(self.dir)

    def test_successor_runs_a_clean_candidate_from_its_own_package(self):
        write(os.path.join(self.dir, 'engine_adapter', '__init__.py'),
              'from apg.det import reference_m5 as _R\nF = _R.notify_env()\n')  # the reference, wrapped as a candidate
        code, out, err = self.run_tool('run_m5_contracts_s1.py', '--path', self.dir, '--notify', 'engine_adapter:F')
        self.assertEqual(code, 0, out[-2000:] + err[-2000:])
        self.assertEqual(len(re.findall(r'(?m)^CASE notification/\S+ PASS cause=ok$', out)), 12)
        self.assertIn('IMPORT_END apg %s' % os.path.join(ROOT, 'apg', '__init__.py'), out)  # apg from this tree, not the candidate

    def test_successor_reports_a_failing_candidate_as_failed(self):
        write(os.path.join(self.dir, 'engine_adapter', '__init__.py'), 'def F(approved):\n    raise RuntimeError("engine down")\n')
        code, out, err = self.run_tool('run_det_corpus_s1.py', '--path', self.dir, '--world', 'engine_adapter:F', '--only', 'B01')
        self.assertEqual(code, 1, out[-2000:] + err[-2000:])
        self.assertRegex(out, r'(?m)^CASE det_corpus/B01 FAIL cause=\S+$')
        self.assertTrue(out.strip().splitlines()[-1].endswith(' status=FAILED exit=1'))
        self.assertNotIn('CASES PASS', out)

    def test_path_without_a_factory_and_a_factory_without_path(self):
        code, out, err = self.run_tool('run_m5_contracts_s1.py', '--path', self.dir)
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR SELECTION_INVALID --path without a candidate factory', out)
        code, out, err = self.run_tool('run_m5_contracts_s1.py', '--notify', 'engine_adapter:F')
        self.assertEqual(code, 2)
        self.assertIn('RUN_ERROR SELECTION_INVALID a candidate factory needs --path', out)


if __name__ == '__main__':
    unittest.main()
