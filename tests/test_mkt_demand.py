import unittest
from . import _path                                         # noqa: F401
from .helpers_mkt import *
from apg.mkt import compare as CP, demand as DM

M = 1_000_000


def world(demand_qty='100', required='2026-12-01', material='MAT-STEEL', unit='tonne', project='PRJ-001', **kw):
    m = mkt_world(**kw)
    m.demands(demand('DEM-1', project, material, demand_qty, unit, required))
    return m


def cov(m, as_of='2026-09-30', project='PRJ-001'):
    ctx = m.ctx(project, as_of)
    (req,) = [r for r in CP.requirements(ctx) if r['kind'] == 'demand']
    return DM.coverage(ctx, req)


class TestCoverage(unittest.TestCase):
    def test_orders_that_add_up_to_the_demand_cover_it(self):
        m = world()
        m.orders(pom('PO-1', qty='60', date='2026-08-01'), pom('PO-2', qty='40', date='2026-09-01', rate='110000'))
        c = cov(m)
        self.assertEqual((c['status'], c['required_micro'], c['ordered_confirmed_micro'], c['uncovered_micro'], c['surplus_confirmed_micro']), ('covered', 100 * M, 100 * M, 0, 0))
        self.assertEqual([o['ref'] for o in c['orders']], ['purchase_order/PO-1', 'purchase_order/PO-2'])

    def test_a_shortfall_is_uncovered_by_exactly_the_missing_quantity(self):
        m = world()
        m.orders(pom('PO-1', qty='60'))
        c = cov(m)
        self.assertEqual((c['status'], c['uncovered_micro']), ('uncovered', 40 * M))

    def test_no_order_at_all_leaves_the_whole_demand_uncovered(self):
        c = cov(world())
        self.assertEqual((c['status'], c['uncovered_micro'], c['orders']), ('uncovered', 100 * M, []))

    def test_over_ordering_is_judged_against_the_tolerance_exactly(self):
        for qty, status in (('105', 'covered'), ('106', 'over_ordered'), ('100', 'covered')):                  # tolerance 500 bps = 5.00%
            m = world()
            m.orders(pom('PO-1', qty=qty))
            c = cov(m)
            self.assertEqual(c['status'], status, qty)
        m = world()
        m.orders(pom('PO-1', qty='106'))
        c = cov(m)
        self.assertEqual((c['surplus_confirmed_micro'], c['surplus_if_all_genuine_micro']), (6 * M, 6 * M))

    def test_orders_for_another_project_or_material_are_not_counted(self):
        m = world()
        m.orders(pom('PO-1', qty='100', project='PRJ-002'), pom('PO-2', qty='100', mat='MAT-CONC40', unit='m3'))
        self.assertEqual(cov(m)['uncovered_micro'], 100 * M)

    def test_the_matching_window_is_a_policy_choice_and_is_reported(self):
        m = world()                                                    # window 180 days before 2026-12-01: 2026-06-04
        m.orders(pom('PO-1', qty='50', date='2026-06-03'), pom('PO-2', qty='50', date='2026-06-04', rate='110000'))
        c = cov(m)
        self.assertEqual((c['ordered_confirmed_micro'], c['window_start']), (50 * M, '2026-06-04'))
        self.assertIn('a policy choice', c['matching_rule'])
        self.assertIn('180 days', c['matching_rule'])

    def test_orders_in_draft_or_cancelled_are_not_counted_and_the_reason_is_listed(self):
        m = world()
        m.orders(pom('PO-1', qty='50', status='draft'), pom('PO-2', qty='50', status='cancelled', rate='110000'), pom('PO-3', qty='10', status='closed', rate='120000'))
        c = cov(m)
        self.assertEqual(c['ordered_confirmed_micro'], 10 * M)
        self.assertEqual(sorted(r for r, _ in c['not_counted']), ['purchase_order/PO-1', 'purchase_order/PO-2'])

    def test_identical_same_day_orders_held_as_duplicates_are_possible_not_confirmed_and_both_figures_are_shown(self):
        m = world('20', '2026-10-15', 'MAT-PBOARD', 'sheet')
        m.orders(pom('PO-1', mat='MAT-PBOARD', unit='sheet', qty='13', rate='1850', date='2026-08-25'), pom('PO-2', mat='MAT-PBOARD', unit='sheet', qty='13', rate='1850', date='2026-08-25'))
        c = cov(m)
        self.assertEqual((c['ordered_confirmed_micro'], c['ordered_if_all_genuine_micro']), (0, 26 * M))
        self.assertEqual((c['uncovered_micro'], c['uncovered_if_suspected_not_genuine_micro']), (0, 20 * M))
        self.assertEqual((c['surplus_confirmed_micro'], c['surplus_if_all_genuine_micro']), (0, 6 * M))
        self.assertEqual(c['status'], 'over_ordered')
        self.assertEqual([o['confirmed'] for o in c['orders']], [False, False])

    def test_accepted_quantity_is_what_a_delivery_counts_and_a_missing_one_falls_back_with_a_note(self):
        m = world()
        m.orders(pom('PO-1', qty='100'))
        m.dockets(docket('DK-1', 'PO-1', delivered='40', accepted='38'), docket('DK-2', 'PO-1', delivered='30', accepted=''))
        c = cov(m)
        self.assertEqual((c['accepted_delivered_micro'], c['delivered_micro']), (68 * M, 70 * M))
        self.assertTrue(any('DK-2 records no accepted quantity' in n for n in c['notes']))

    def test_a_delivery_above_the_demand_makes_it_over_ordered_even_when_the_orders_were_not(self):
        m = world()
        m.orders(pom('PO-1', qty='100'))
        m.dockets(docket('DK-1', 'PO-1', delivered='110', accepted='110'))
        c = cov(m)
        self.assertEqual((c['status'], c['surplus_delivered_micro'], c['surplus_confirmed_micro']), ('over_ordered', 10 * M, 0))
        self.assertIn('not a stock count', c['inventory_note'])

    def test_a_docket_for_another_order_or_a_held_docket_is_not_counted(self):
        m = world()
        m.orders(pom('PO-1', qty='100'), pom('PO-9', qty='5', project='PRJ-002', date='2026-08-01', rate='110000'))
        m.dockets(docket('DK-1', 'PO-9', delivered='5', accepted='5'), docket('DK-2', 'PO-1', delivered='abc'), docket('DK-3', 'PO-1', delivered='0', accepted='0', date='2026-08-20'))
        c = cov(m)
        self.assertEqual(c['accepted_delivered_micro'], 0)

    def test_coverage_cannot_be_assessed_without_the_financial_policys_status_map_and_says_why(self):
        m = world()
        m.orders(pom('PO-1', qty='100'))
        a = m.analysis()
        a.F.policy.pop('po_status_map')
        self.assertEqual(DM.coverage(a.ctx, CP.requirements(a.ctx)[0]), {'requirement': 'demand/DEM-1', 'status': 'cannot_assess', 'why': 'PO_STATUS_MAP_NOT_CONFIGURED'})


class TestUnits(unittest.TestCase):
    def test_orders_in_another_unit_than_the_demand_cannot_be_compared_and_coverage_says_so(self):
        m = world(demand_qty='100', unit='kg')
        m.orders(pom('PO-1', qty='300', rate='100000', unit='tonne'))
        c = cov(m)
        self.assertEqual(c['status'], 'cannot_assess')
        self.assertIn('UNIT_MISMATCH', c['why'])
        self.assertIn('PO-1 is in tonne but the demand is in kg', c['why'])

    def test_the_same_unit_in_another_case_or_with_spaces_is_the_same_unit(self):
        m = world(demand_qty='100', unit='tonne')
        m.orders(pom('PO-1', qty='100', rate='100000', unit=' Tonne '))
        self.assertEqual(cov(m)['status'], 'covered')

    def test_an_order_for_another_project_in_another_unit_does_not_block_the_assessment(self):
        m = world(demand_qty='100', unit='tonne')
        m.orders(pom('PO-1', qty='100', rate='100000'), pom('PO-2', qty='5', rate='100000', unit='kg', project='PRJ-002'))
        self.assertEqual(cov(m)['status'], 'covered')


class TestDuplicates(unittest.TestCase):
    def groups(self, m, window=None, project='PRJ-001'):
        if window is not None:
            f = DM_fields = None
            from apg.mkt import demo_mkt as DMK
            fields = DMK.demo_mkt_fields()
            fields['demand']['duplicate_window_days'] = window
            m.set_mkt(**fields)
        return DM.duplicate_groups(m.ctx(project))

    def test_same_project_supplier_material_quantity_rate_on_the_same_day_is_a_group(self):
        m = mkt_world()
        m.orders(pom('PO-1', qty='13', rate='1850', date='2026-08-25'), pom('PO-2', qty='13', rate='1850', date='2026-08-25'))
        (g,) = self.groups(m)
        self.assertEqual((g['project'], g['supplier'], g['material'], g['qty_micro'], g['rate_cents'], g['span_days'], g['held_as_candidates']), ('PRJ-001', 'SUP-001', 'MAT-STEEL', 13 * M, 1850, 0, True))
        self.assertEqual([o['ref'] for o in g['orders']], ['purchase_order/PO-1', 'purchase_order/PO-2'])

    def test_any_difference_in_the_details_means_no_group(self):
        for kw in (dict(qty='14'), dict(rate='1851'), dict(supplier='SUP-002'), dict(mat='MAT-CONC40', unit='m3'), dict(project='PRJ-002')):
            m = mkt_world()
            m.orders(pom('PO-1', qty='13', rate='1850', date='2026-08-25'), pom('PO-2', **dict(dict(qty='13', rate='1850', date='2026-08-25'), **kw)))
            self.assertEqual(self.groups(m), [], kw)
            self.assertEqual(self.groups(m, project='PRJ-002'), [], kw)

    def test_the_window_is_the_policys_and_orders_a_day_apart_are_not_a_group_with_a_zero_day_window(self):
        m = mkt_world()
        m.orders(pom('PO-1', qty='13', rate='1850', date='2026-08-25'), pom('PO-2', qty='13', rate='1850', date='2026-08-26'))
        self.assertEqual(self.groups(m), [])
        (g,) = self.groups(m, window=1)
        self.assertEqual(g['span_days'], 1)

    def test_a_chain_of_orders_each_within_the_window_of_the_previous_is_one_group(self):
        m = mkt_world()
        m.orders(pom('PO-1', qty='13', rate='1850', date='2026-08-25'), pom('PO-2', qty='13', rate='1850', date='2026-08-26'), pom('PO-3', qty='13', rate='1850', date='2026-08-27'))
        (g,) = self.groups(m, window=1)
        self.assertEqual(len(g['orders']), 3)

    def test_orders_not_committed_are_never_suspected(self):
        m = mkt_world()
        m.orders(pom('PO-1', qty='13', rate='1850', date='2026-08-25'), pom('PO-2', qty='13', rate='1850', date='2026-08-25', status='cancelled'))
        self.assertEqual(self.groups(m), [])


if __name__ == '__main__':
    unittest.main()
