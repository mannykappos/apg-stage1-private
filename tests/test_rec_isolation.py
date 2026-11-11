"""M7: scenario isolation and the action boundary (Section 10 sections 7.1 and 9; Section 05 section 11; PG-RS-AC-07, 08).  Scenarios never change the official forecast."""
import ast, os, unittest
from . import _path                                         # noqa: F401
from ._path import HERE_ROOT
from .helpers_rec import AS_OF, RecWorld
from apg import canon
from apg.fin import forecast_book as FB
from apg.rec import verify as V

REC_DIR = os.path.join(HERE_ROOT, 'apg', 'rec')


def _sources():
    return {n: open(os.path.join(REC_DIR, n), encoding='utf-8').read() for n in sorted(os.listdir(REC_DIR)) if n.endswith('.py')}


class TestForecastUntouched(unittest.TestCase):
    def test_the_whole_recommendation_path_leaves_the_authoritative_forecast_and_its_slot_unchanged(self):
        w = RecWorld()
        key = FB.slot_key('PRJ-001', AS_OF)
        before_slot = canon.deep_copy(w.s.get(FB.SLOT_KIND, key).payload)
        before_rev = w.s.get(FB.SLOT_KIND, key).revision
        before_current = canon.digest(FB.current(w.s, 'PRJ-001', AS_OF))
        f = w.finding(gross=5000000)
        w.to_completed(f)
        V.verify(w.verifier, w.clock, w.reg, w.m.reg, w.rid(f), w.baseline['run_key'], 1, w.offsets(), 'checked', w.policy)
        w.run(as_of='2026-10-02')
        self.assertEqual(w.s.get(FB.SLOT_KIND, key).payload, before_slot)
        self.assertEqual(w.s.get(FB.SLOT_KIND, key).revision, before_rev)
        self.assertEqual(canon.digest(FB.current(w.s, 'PRJ-001', AS_OF)), before_current)
        self.assertEqual(FB.verify_slot(w.s, 'PRJ-001', AS_OF), [])
        self.assertEqual(len(w.s.query(FB.SLOT_KIND)), 1)

    def test_every_alternative_says_it_does_not_change_the_forecast(self):
        w = RecWorld()
        f = w.finding(gross=5000000)
        w.ready(f)
        e = w.entry(w.run(), f)
        self.assertFalse(e['scenarios']['changes_authoritative_forecast'])
        self.assertTrue(all(a['changes_authoritative_forecast'] is False for a in e['scenarios']['alternatives']))

    def test_the_formula_writes_nothing(self):
        w = RecWorld()
        w.finding()
        before = {k: len(v) for k, v in w.w.store._d.items()}
        from apg import repro
        from apg.rec import engine as E
        r = E.run(w.s, w.reg, w.clock, AS_OF, w.policy['version'])
        after = {k: len(v) for k, v in w.w.store._d.items()}
        changed = {k for k in after if before.get(k) != after[k]}
        self.assertEqual(changed, {('zero_one', repro.KIND, r['run_key'])})


class TestStaticBoundary(unittest.TestCase):
    def test_no_recommendation_module_adopts_registers_or_writes_a_forecast(self):
        for n, src in _sources().items():
            with self.subTest(n=n):
                self.assertNotIn('adopt(', src)
                self.assertNotIn('register_scenario', src)
                tree = ast.parse(src)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ('put', 'atomic'):
                        self.assertNotIn('SLOT_KIND', ast.unparse(node), n)
                        self.assertNotIn('fin_forecast', ast.unparse(node), n)

    def test_no_recommendation_module_reaches_outside_the_record_store(self):
        banned = {'socket', 'subprocess', 'urllib', 'http', 'requests', 'smtplib', 'os', 'shutil', 'threading', 'asyncio', 'random', 'time'}
        for n, src in _sources().items():
            for node in ast.walk(ast.parse(src)):
                names = [a.name.split('.')[0] for a in node.names] if isinstance(node, ast.Import) else ([node.module.split('.')[0]] if isinstance(node, ast.ImportFrom) and node.module and node.level == 0 else [])
                with self.subTest(n=n):
                    self.assertFalse(set(names) & banned, (n, names))

    def test_only_the_verification_gate_sets_a_verified_outcome(self):
        for n, src in _sources().items():
            for node in ast.walk(ast.parse(src)):
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and node.value.value == 'verified_outcome':
                    self.assertEqual(n, 'verify.py')

    def test_no_float_anywhere_in_the_recommendation_code(self):
        for n, src in _sources().items():
            for node in ast.walk(ast.parse(src)):
                self.assertFalse(isinstance(node, ast.Constant) and isinstance(node.value, float), n)
                self.assertFalse(isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div), (n, getattr(node, 'lineno', None)))

    def test_every_module_states_its_blueprint_basis(self):
        for n, src in _sources().items():
            doc = ast.get_docstring(ast.parse(src)) or ''
            with self.subTest(n=n):
                self.assertTrue('Section' in doc or n == '__init__.py' and 'Section 10' in doc, n)


if __name__ == '__main__':
    unittest.main()
