"""MIE-1 static checks: neutrality, imports, field names, operations, no clock, no feed call, the isolation gate (NE-01..NE-06, FL-01, IG-01, IG-05, CT-10).
Each check is also run on a copy with a planted defect and must fail there."""
import importlib.util, os, shutil, tempfile, unittest
from . import _path                                         # noqa: F401
from ._path import HERE_ROOT

_spec = importlib.util.spec_from_file_location('mie_static', os.path.join(HERE_ROOT, 'tools', 'mie_static.py'))
ST = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ST)


class Planted(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='mie_static_')
        for d in ('mie', 'tests', 'apg'):
            shutil.copytree(os.path.join(HERE_ROOT, d), os.path.join(self.tmp, d), ignore=shutil.ignore_patterns('__pycache__'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def plant(self, rel, text):
        with open(os.path.join(self.tmp, rel), 'a', encoding='utf-8') as f:
            f.write('\n' + text + '\n')


class TestTheRealTree(unittest.TestCase):
    def test_NE_01_no_deny_listed_term_in_the_core_or_its_tests(self):
        """NE-01."""
        self.assertEqual(ST.neutrality(HERE_ROOT), [])
        self.assertGreaterEqual(len(ST.core_files(HERE_ROOT)), 9)
        self.assertGreaterEqual(len(ST.core_test_files(HERE_ROOT)), 8)
        self.assertEqual(len(ST.deny_terms(HERE_ROOT)), 16)

    def test_NE_03_the_core_imports_only_the_standard_library_and_itself(self):
        """NE-03."""
        self.assertEqual(ST.import_violations(HERE_ROOT), [])

    def test_NE_04_no_forecast_shaped_field(self):
        """NE-04."""
        self.assertEqual(ST.field_violations(HERE_ROOT), [])

    def test_NE_05_the_operations_are_the_twelve_and_none_orders_commits_or_notifies(self):
        """NE-05, CT-02 (the twelve inbound operations)."""
        self.assertEqual(ST.operation_violations(HERE_ROOT), [])

    def test_NE_06_no_clock_random_network_file_or_environment(self):
        """NE-06."""
        self.assertEqual(ST.clock_violations(HERE_ROOT), [])

    def test_FL_01_the_core_never_calls_a_feed(self):
        """FL-01."""
        self.assertEqual(ST.feed_violations(HERE_ROOT), [])

    def test_IG_01_and_IG_05_the_isolation_gate(self):
        """IG-01: no APG module imports MIE; IG-05: no MIE module imports APG, so there is no consumer path from the core into APG."""
        self.assertEqual(ST.apg_imports_mie(HERE_ROOT), [])
        self.assertEqual(ST.mie_imports_apg(HERE_ROOT), [])

    def test_CT_10_the_reference_ports_are_labelled_non_production(self):
        """CT-10."""
        from mie.core import reference as R
        self.assertTrue(R.NON_PRODUCTION)
        self.assertIn('NOT PRODUCTION', R.__doc__)
        self.assertIn('claim no persistence', R.__doc__)


class TestPlantedDefectsAreCaught(Planted):
    def test_NE_02_a_planted_domain_term_fails_the_neutrality_check(self):
        """NE-02: every term of the deny list, planted in turn in a core file (and once in a core test), is found."""
        for term in ST.deny_terms(HERE_ROOT):
            with self.subTest(term=term):
                self.setUp()
                self.plant('mie/core/values.py', '# %s' % term.upper())
                self.assertTrue(ST.neutrality(self.tmp))
        self.setUp()
        self.plant('tests/helpers_mie.py', 'X = "%ss"' % ST.deny_terms(HERE_ROOT)[0])
        self.assertTrue(ST.neutrality(self.tmp))

    def test_planted_import_is_detected(self):
        """NE-03 (a planted APG import, a pack import and an unlisted module)."""
        for line in ('import apg', 'from mie import packs', 'import collections'):
            with self.subTest(line=line):
                self.setUp()
                self.plant('mie/core/pack.py', line)
                self.assertTrue(ST.import_violations(self.tmp))

    def test_planted_forecast_field_is_detected(self):
        """NE-04."""
        for name in ("{'forecast_level': 1}", 'predicted_value = 1', 'def expected_rise(x): pass', "dict(projected=1)"):
            with self.subTest(name=name):
                self.setUp()
                self.plant('mie/core/timing.py', name)
                self.assertTrue(ST.field_violations(self.tmp))

    def test_planted_ordering_operation_is_detected(self):
        """NE-05."""
        path = os.path.join(self.tmp, 'mie', 'core', 'engine.py')
        src = open(path, encoding='utf-8').read().replace('    # ------------------------------------------------------------------ OP-01',
                                                          '    def place_order(self, ctx):\n        pass\n\n    # ------------------------------------------------------------------ OP-01')
        open(path, 'w', encoding='utf-8').write(src)
        self.assertTrue(ST.operation_violations(self.tmp))

    def test_planted_clock_read_is_detected(self):
        """NE-06 (SB-11)."""
        for line in ('import time', 'X = datetime.datetime.now()', 'Y = os.environ', 'Z = open("f")', 'import random'):
            with self.subTest(line=line):
                self.setUp()
                self.plant('mie/core/signals.py', line)
                self.assertTrue(ST.clock_violations(self.tmp))

    def test_planted_feed_call_is_detected(self):
        """FL-01 (SB-46)."""
        for line in ('def g(src):\n    return src.fetch(1, 2, 3)', 'from ..adapters import feed', 'X = ObservationSourcePort'):
            with self.subTest(line=line):
                self.setUp()
                self.plant('mie/core/engine.py', line)
                self.assertTrue(ST.feed_violations(self.tmp))

    def test_planted_apg_wiring_is_detected(self):
        """IG-01 (SB-27): an APG module that imports the core is found; so is a MIE module that imports APG."""
        self.plant('apg/rec/engine.py', 'import mie.core.engine')
        self.assertEqual(ST.apg_imports_mie(self.tmp), ['apg/rec/engine.py'])
        self.plant('mie/adapters/m6.py', 'import apg.rec.lifecycle')
        self.assertEqual(ST.mie_imports_apg(self.tmp), ['mie/adapters/m6.py'])


if __name__ == '__main__':
    unittest.main()
