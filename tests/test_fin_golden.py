import json, os, unittest
from . import _path                                          # noqa: F401
from ._path import HERE_ROOT
from apg.fin import golden_fin as GF


class GoldenFin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.G = GF.run_golden_fin(HERE_ROOT)
        cls.O = GF.oracle_fin(HERE_ROOT)

    def test_golden_cases_equal_the_recorded_answers(self):
        want = json.load(open(os.path.join(HERE_ROOT, 'regression', 'GOLDEN_FIN.json')))
        self.assertEqual(GF.dumps({'oracle': self.O, 'golden': self.G}), GF.dumps(want))

    def test_the_run_is_deterministic(self):
        self.assertEqual(GF.dumps(GF.run_golden_fin(HERE_ROOT)), GF.dumps(self.G))

    def test_headline_figures_agree_with_the_independent_oracle(self):
        for p in GF.PROJECTS:
            f, o = self.G['figures'][p], self.O['projects'][p]
            self.assertEqual(f['actual_cost']['cents'], o['actual_cents'], p)
            self.assertEqual(f['revenue']['cents'], o['revenue_cents'], p)
            self.assertEqual(f['forecast']['cents'], o['forecast']['margin_on_known_cents'], p)
            self.assertEqual(f['recognised_margin']['cents'], o['recognised_on_known']['margin_cents'], p)
            self.assertEqual(f['retention_carrying']['cents'], o['carrying_cents'], p)
            self.assertEqual(f['cash_adjusted']['cents'], o['cash_adjusted_on_known'], p)

    def test_the_m4_costs_add_up_to_the_m3_total(self):
        x = self.G['m3_cross_check']
        self.assertEqual(x['sum_of_m4_project_actuals_cents'], x['m3_authoritative_cents'])
        self.assertEqual(x['m3_authoritative_cents'], self.O['sum_of_project_actuals_cents'])

    def test_no_figure_hides_why_it_is_not_authoritative(self):
        for p, figs in self.G['figures'].items():
            for name, f in figs.items():
                if f['state'] != 'authoritative':
                    self.assertTrue(f['reasons'] or f['unknown'] or f['disputed'] or f['excluded'], (p, name))
                if f['cents'] is None:
                    self.assertEqual(f['state'], 'cannot_assess', (p, name))

    def test_the_unattributable_and_held_items_are_named_in_the_figures_they_touch(self):
        f = self.G['figures']
        self.assertIn(['ap_invoice/INV-0187', 'held'], f['PRJ-002']['actual_cost']['excluded'])
        self.assertIn(['ap_invoice/INV-0121', 'disputed'], f['PRJ-003']['actual_cost']['excluded'])
        self.assertIn(['ap_invoice/INV-0183', 'duplicate_delivery'], f['PRJ-001']['actual_cost']['excluded'])

    def test_the_golden_answers_depend_on_the_policy_it_is_not_a_constant(self):
        from apg.fin import calc_records as C, demo_fin as DF, policy as P
        from apg.ingest.golden_m3 import _world
        clock, prov, store, audit, who = _world()
        s = who('t1', 'zero_one', 'ann')
        DF.load_zero(HERE_ROOT, s, clock, 'zero_one')
        pol = DF.demo_policy(version='SYN-FIN-POL-X', proposer='ann', recognition_method='cost_to_cost'); P.store_policy(s, pol)          # proposed, not approved
        reg = C.fin_registry()
        r = C.run_calc(s, reg, clock, 'fin.forecast', 'PRJ-001', GF.AS_OF, 'SYN-FIN-POL-X')['result']
        self.assertEqual((r['state'], r['value']['cents']), ('provisional', self.G['figures']['PRJ-001']['forecast']['cents']))     # same number, honest state
        pol2 = DF.demo_policy(version='SYN-FIN-POL-Y', proposer='ann', ctc_method={'default': 'budget_less_actual'}); P.store_policy(s, pol2)
        r2 = C.run_calc(s, reg, clock, 'fin.forecast', 'PRJ-001', GF.AS_OF, 'SYN-FIN-POL-Y')['result']
        self.assertNotEqual(r2['value']['cents'], self.G['figures']['PRJ-001']['forecast']['cents'])


if __name__ == '__main__':
    unittest.main()
