import json, os, unittest
from . import _path                                          # noqa: F401
from ._path import HERE_ROOT
from apg.det import demo_det as DD, golden_det as GD


class GoldenDet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.G = GD.run_golden_det(HERE_ROOT)
        cls.O = GD.oracle_det(HERE_ROOT)
        cls.O2 = GD.oracle_det(HERE_ROOT, 'zero_two')

    def test_golden_cases_equal_the_recorded_answers(self):
        want = json.load(open(os.path.join(HERE_ROOT, 'regression', 'GOLDEN_DET.json')))
        self.assertEqual(GD.dumps({'oracle': self.O, 'oracle_zero_two': self.O2, 'golden': self.G}), GD.dumps(want))

    def test_the_run_is_deterministic(self):
        self.assertEqual(GD.dumps(GD.run_golden_det(HERE_ROOT)), GD.dumps(self.G))

    def test_the_oracle_thresholds_are_the_demonstration_policy_thresholds(self):
        r = DD.demo_det_policy()['rules']
        T = GD.T
        self.assertEqual((T['tol_budget'], T['tol_po'], T['var_days'], T['instr_days'], T['grace'], T['warn'], T['tol_quote'], T['hire_days'], T['move']),
                         (r['R01']['tolerance_bps'], r['R03']['tolerance_bps'], r['R04']['unresolved_days'], r['R04B']['min_age_days'], r['R05']['grace_days'], r['R06']['warning_days'],
                          r['R07']['tolerance_bps'], r['R08']['min_excess_days'], r['R09']['movement_abs_cents']))
        self.assertEqual((T['agg_days'], T['agg_abs'], T['overlap'], T['base_w'], T['recent_w'], T['decline'], T['def_n']),
                         (r['AGG']['window_days'], r['AGG']['single_order_abs_cents'], r['DLY']['min_overlap_days'], r['LAB']['baseline_weeks'], r['LAB']['recent_weeks'], r['LAB']['decline_bps'], r['DEF']['min_events']))

    def test_the_oracle_expects_the_fifteen_planted_positives_and_no_negative_control(self):
        keys = sorted(self.O['expected'])
        self.assertEqual(len(keys), 15)
        for neg in ('R01|PRJ-002|CC-05', 'R02|PRJ-002|AMD-002', 'R03|PRJ-002|PO-0092', 'R04|PRJ-002|VAR-0002', 'R08|PRJ-003|HIRE-002'):
            self.assertNotIn(neg, keys)
        self.assertFalse([k for k in keys if k.startswith('AGG|PRJ-002|PRJ-002|SUP-010')])

    def test_every_planted_positive_is_raised_and_every_negative_control_stays_silent(self):
        raised = {f'{s["rule"].replace("DET-", "")}|{sc}|{s["subject"]}' for sc, sigs in self.G['signals'].items() for s in sigs if s['rule'] not in ('DET-D01', 'DET-D02')}
        self.assertEqual(raised, set(self.O['expected']))

    def test_the_second_builder_has_its_own_conflicting_invoice_and_its_own_answer(self):
        self.assertEqual(self.O2['excluded_invoices'], ['INV-0001'])
        self.assertEqual(self.O2['expected'], {})
        self.assertEqual([s['rule'] for s in self.G['zero_two_signals']['PRJ-001']], ['DET-D01'])
        self.assertEqual(self.G['zero_two_signals']['tenant'], [])

    def test_no_signal_hides_its_basis(self):
        for sc, sigs in self.G['signals'].items():
            for s in sigs:
                self.assertGreaterEqual(s['evidence_records'], 1, (sc, s['subject']))
                self.assertTrue((s['status'] == 'unquantified') == (s['gross_cents'] is None), (sc, s['subject']))

    def test_the_golden_answers_depend_on_the_policy_they_are_not_a_constant(self):
        from apg import tenancy
        from apg.det import detect as D
        from apg.ingest.golden_m3 import _world
        clock, prov, store, audit, who = _world()
        s = who('t1', 'zero_one', 'ann')
        _, fv, dv = DD.load_zero_all(HERE_ROOT, s, clock, 'zero_one')
        from apg.det import policy as DP
        rules = DD.demo_det_policy()['rules']
        rules['R01'] = {'tolerance_bps': 5000}
        DP.store_policy(s, DD.demo_det_policy(version='SYN-DET-POL-X', rules=rules))
        r = D.run_project(s, D.det_registry(), clock, 'PRJ-002', GD.AS_OF, fv, 'SYN-DET-POL-X')['result']
        self.assertFalse([x for x in r['signals'] if x['rule']['id'] == 'DET-R01'])                  # 115.7 percent is inside a 50 percent tolerance
        self.assertTrue([x for x in D.run_project(s, D.det_registry(), clock, 'PRJ-002', GD.AS_OF, fv, dv)['result']['signals'] if x['rule']['id'] == 'DET-R01'])


if __name__ == '__main__':
    unittest.main()
