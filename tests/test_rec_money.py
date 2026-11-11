"""M7: net-benefit discipline and overlap (Section 10 section 6; PG-RS-AC-04, 06, 13: overlapping benefits)."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_rec import RecWorld
from apg.rec import inputs as IN


class TestNetBenefit(unittest.TestCase):
    def setUp(self):
        self.w = RecWorld()

    def e(self, fid):
        return self.w.entry(self.w.run(ingest=False), fid)

    def test_no_net_benefit_without_an_expected_benefit_and_every_incremental_cost(self):
        f = self.w.finding(gross=5000000)
        rid = self.w.rid(f)
        self.assertEqual(self.e(f)['dimensions']['net_benefit']['status'], 'unquantified')
        IN.set_inputs(self.w.owner, self.w.clock, rid, expected_benefit={'cents': 700000, 'basis': 'owner estimate'})
        n = self.e(f)['dimensions']['net_benefit']
        self.assertEqual((n['status'], n['cents']), ('unquantified', None))
        self.assertIn('every incremental cost', n['formula'])
        IN.set_inputs(self.w.owner, self.w.clock, rid, incremental_costs=[{'component': 'labour', 'cents': 150000, 'basis': 'two days'}, {'component': 'freight', 'cents': 50000, 'basis': 'one run'}])
        n = self.e(f)['dimensions']['net_benefit']
        self.assertEqual((n['status'], n['cents'], n['label']), ('estimated', 500000, 'estimate'))

    def test_a_net_benefit_can_be_negative_and_is_shown_as_such(self):
        f = self.w.finding()
        IN.set_inputs(self.w.owner, self.w.clock, self.w.rid(f), expected_benefit={'cents': 10000, 'basis': 'b'}, incremental_costs=[{'component': 'c', 'cents': 30000, 'basis': 'x'}])
        e = self.e(f)
        self.assertEqual(e['dimensions']['net_benefit']['cents'], -20000)
        self.assertIn('-$200.00', e['explanation']['benefits_costs_tradeoffs'])

    def test_a_zero_cost_needs_a_basis_and_invalid_inputs_are_refused(self):
        f = self.w.finding()
        rid = self.w.rid(f)
        bad = [dict(incremental_costs=[{'component': 'c', 'cents': 0, 'basis': ''}]), dict(incremental_costs=[]), dict(incremental_costs=[{'component': 'c', 'cents': -1, 'basis': 'x'}]),
               dict(incremental_costs=[{'component': 'c', 'cents': 1, 'basis': 'x'}, {'component': 'c', 'cents': 2, 'basis': 'y'}]),
               dict(expected_benefit={'cents': 1.5, 'basis': 'x'}), dict(expected_benefit={'cents': True, 'basis': 'x'}), dict(expected_benefit={'cents': 1}),
               dict(action_kind='launch_missiles'), dict(dependencies=['']), dict(alternatives=[{'name': 'a', 'unknown': 'x'}]), dict(alternatives=[{'name': 'a'}, {'name': 'a'}])]
        for b in bad:
            with self.subTest(b=b):
                with self.assertRaises(IN.InputError):
                    IN.set_inputs(self.w.owner, self.w.clock, rid, **b)
        with self.assertRaises(IN.InputError):
            IN.set_inputs(self.w.owner, self.w.clock, rid, surprise=1)
        IN.set_inputs(self.w.owner, self.w.clock, rid, incremental_costs=[{'component': 'c', 'cents': 0, 'basis': 'no extra cost: the same crew is on site'}])
        self.assertEqual(self.e(f)['dimensions']['implementation_cost']['cents'], 0)

    def test_the_explanation_keeps_gross_benefit_cost_and_net_apart(self):
        f = self.w.finding(gross=5000000)
        IN.set_inputs(self.w.owner, self.w.clock, self.w.rid(f), expected_benefit={'cents': 700000, 'basis': 'b'}, incremental_costs=[{'component': 'c', 'cents': 200000, 'basis': 'x'}])
        t = self.e(f)['explanation']['benefits_costs_tradeoffs']
        self.assertIn('Potential gross $50000.00; expected benefit $7000.00; incremental costs $2000.00; estimated net $5000.00', t)


class TestOverlap(unittest.TestCase):
    def setUp(self):
        self.w = RecWorld()

    def test_findings_in_one_overlap_group_are_counted_once(self):
        a = self.w.finding(gross=3000000, overlap='activity-A-delay')
        b = self.w.finding(gross=5000000, overlap='activity-A-delay')
        c = self.w.finding(gross=1000000)
        run = self.w.run(ingest=False)
        ea, eb, ec = (self.w.entry(run, x) for x in (a, b, c))
        self.assertEqual((ea['overlap']['counted_in_totals'], eb['overlap']['counted_in_totals'], ec['overlap']['counted_in_totals']), (False, True, True))
        self.assertIn('overlaps with ' + eb['rec_id'], ea['overlap']['note'])
        t = run['result']['totals']['forecast_exposure']
        self.assertEqual((t['potential_gross_counted_cents'], t['counted'], t['not_counted_overlap']), (6000000, 2, [ea['rec_id']]))
        self.assertIn('overlaps with', ' '.join(ea['dimensions']['dependencies']))

    def test_findings_resting_on_the_same_record_are_one_overlap_component(self):
        a = self.w.finding(gross=3000000, refs=['ap_invoice/INV-9'])
        b = self.w.finding(gross=2000000, refs=['ap_invoice/INV-9', 'purchase_order/PO-1'])
        run = self.w.run(ingest=False)
        self.assertEqual(self.w.entry(run, a)['overlap']['component'], self.w.entry(run, b)['overlap']['component'])
        self.assertEqual(run['result']['totals']['forecast_exposure']['potential_gross_counted_cents'], 3000000)

    def test_a_person_linked_financial_overlap_is_respected(self):
        from apg.det import findings as FD
        a = self.w.finding(gross=3000000)
        b = self.w.finding(gross=2000000)
        FD.link(self.w.rev, self.w.clock, a, b, 'financial_overlap', 'same retention')
        run = self.w.run(ingest=False)
        self.assertEqual(run['result']['totals']['forecast_exposure']['potential_gross_counted_cents'], 3000000)

    def test_net_benefit_totals_count_only_the_counted_line(self):
        a = self.w.finding(gross=3000000, overlap='g')
        b = self.w.finding(gross=5000000, overlap='g')
        for f, net in ((a, 400000), (b, 900000)):
            IN.set_inputs(self.w.owner, self.w.clock, self.w.rid(f), expected_benefit={'cents': net, 'basis': 'b'}, incremental_costs=[{'component': 'c', 'cents': 0, 'basis': 'none'}])
        t = self.w.run(ingest=False)['result']['totals']['forecast_exposure']
        self.assertEqual((t['estimated_net_counted_cents'], t['net_quantified_counted']), (900000, 1))

    def test_interpretations_are_never_added_together_and_unquantified_is_not_zero(self):
        self.w.finding(gross=3000000)
        self.w.finding(interp='potential_opportunity', family='procurement_materials', label='estimate', gross=7000000)
        u = self.w.finding(gross=None)
        res = self.w.run(ingest=False)['result']
        self.assertEqual(set(res['totals']), {'forecast_exposure', 'potential_opportunity'})
        self.assertEqual(res['totals']['forecast_exposure']['potential_gross_counted_cents'], 3000000)
        self.assertIn(self.w.rid(u), res['totals']['forecast_exposure']['unquantified'])
        self.assertIn('never added across interpretations', res['totals']['forecast_exposure']['label'])
        self.assertNotIn('grand_total', repr(res).lower())
        self.assertIn('Nothing here is an approved action, a verified outcome or a change to any forecast', res['statement'])

    def test_a_shared_root_cause_hypothesis_does_not_merge_amounts(self):
        from apg.det import findings as FD
        a = self.w.finding(gross=3000000)
        b = self.w.finding(gross=2000000)
        FD.link(self.w.rev, self.w.clock, a, b, 'shared_root_cause_hypothesis', 'maybe the same crane')
        self.assertEqual(self.w.run(ingest=False)['result']['totals']['forecast_exposure']['potential_gross_counted_cents'], 5000000)


if __name__ == '__main__':
    unittest.main()
