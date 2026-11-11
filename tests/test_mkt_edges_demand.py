"""Edge-case tests written to kill mutation survivors in demand, opportunity, purchasing and suppliers: window boundaries on the as-of day and the window start, tolerance boundaries, the held-docket
note, the unit-key helper, the tax conversion, the savings gap threshold, the reference gate and the supplier lead-time and price-spread filters."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_mkt import *
from apg.mkt import compare as CP, demand as DEM, opportunity as OP, purchasing as PU, suppliers as SU

M = 1_000_000
AS_OF_DAY = '2026-09-30'


# ------------------------------------------------------------------------------------------------------------------------------------------------ demand
def dworld(demand_qty='100', required='2026-12-01', unit='tonne', **kw):
    m = mkt_world(**kw)
    m.demands(demand('DEM-1', 'PRJ-001', 'MAT-STEEL', demand_qty, unit, required))
    return m


def req_of(ctx):
    (req,) = [r for r in CP.requirements(ctx) if r['kind'] == 'demand']
    return req


def cov(m, as_of=AS_OF_DAY):
    ctx = m.ctx('PRJ-001', as_of)
    return DEM.coverage(ctx, req_of(ctx))


class TestDemandEdges(unittest.TestCase):
    def test_a_delivery_above_the_demand_is_over_ordered_only_when_the_surplus_exceeds_the_tolerance(self):
        for accepted, status in (('100', 'covered'), ('102', 'covered'), ('105', 'covered'), ('106', 'over_ordered')):        # tolerance 500 bps of 100 tonne = 5 tonne, strictly above
            m = dworld()
            m.orders(pom('PO-1', qty='100'))
            m.dockets(docket('DK-1', 'PO-1', delivered=accepted, accepted=accepted))
            c = cov(m)
            self.assertEqual(c['status'], status, 'accepted %s against an order and demand of 100' % accepted)
            self.assertEqual(c['surplus_delivered_micro'], max(0, int(accepted) - 100) * M)

    def test_a_delivery_exactly_equal_to_the_demand_is_covered_not_over_ordered(self):
        m = dworld()
        m.orders(pom('PO-1', qty='100'))
        m.dockets(docket('DK-1', 'PO-1', delivered='100', accepted='100'))
        c = cov(m)
        self.assertEqual((c['status'], c['surplus_delivered_micro'], c['surplus_confirmed_micro']), ('covered', 0, 0))

    def test_an_order_of_another_unit_blocks_the_assessment_from_the_window_start_to_the_as_of_day_inclusive(self):
        # the window is 180 days before 2026-12-01: it starts on 2026-06-04 and the as-of day is 2026-09-30
        for day, blocked in (('2026-06-03', False), ('2026-06-04', True), ('2026-06-05', True), ('2026-09-29', True), ('2026-09-30', True)):
            m = dworld()
            m.orders(pom('PO-1', qty='100', unit='kg', date=day))
            c = cov(m)
            self.assertEqual(c['status'] == 'cannot_assess', blocked, day)
            if blocked:
                self.assertIn('PO-1 is in kg but the demand is in tonne', c['why'])
        c = cov(dworld(), AS_OF_DAY)
        self.assertEqual(c['status'], 'uncovered')

    def test_an_order_dated_after_the_as_of_day_is_neither_counted_nor_blocks_the_assessment(self):
        m = dworld()
        m.orders(pom('PO-1', qty='100', unit='kg', date='2026-10-01'), pom('PO-2', qty='100', date='2026-10-02', rate='110000'))
        c = cov(m, '2026-10-01')
        self.assertEqual(c['status'], 'cannot_assess')                                 # as-of 10-01: the kg order is dated on the as-of day
        c = cov(m, AS_OF_DAY)
        self.assertNotEqual(c['status'], 'cannot_assess')
        self.assertEqual(c['ordered_confirmed_micro'], 0)

    def test_an_order_dated_on_the_as_of_day_is_counted_and_one_dated_the_next_day_is_not(self):
        m = dworld()
        m.orders(pom('PO-1', qty='60', date='2026-09-30'), pom('PO-2', qty='40', date='2026-10-01', rate='110000'))
        c = cov(m, AS_OF_DAY)
        self.assertEqual([o['ref'] for o in c['orders']], ['purchase_order/PO-1'])
        self.assertEqual((c['ordered_confirmed_micro'], c['uncovered_micro']), (60 * M, 40 * M))
        c2 = cov(m, '2026-10-01')
        self.assertEqual([o['ref'] for o in c2['orders']], ['purchase_order/PO-1', 'purchase_order/PO-2'])

    def test_matching_orders_directly_the_window_start_and_the_as_of_day_are_inside_the_window(self):
        m = dworld()
        m.orders(pom('PO-1', qty='1', date='2026-06-03'), pom('PO-2', qty='2', date='2026-06-04', rate='110000'), pom('PO-3', qty='3', date='2026-09-30', rate='120000'),
                 pom('PO-4', qty='4', date='2026-10-01', rate='130000'))
        ctx = m.ctx('PRJ-001', AS_OF_DAY)
        confirmed, possible, skipped = DEM.matched_orders(ctx, req_of(ctx))
        self.assertEqual(([po['key'] for po in confirmed], possible, skipped), (['PO-2', 'PO-3'], [], []))

    def test_a_docket_dated_on_the_as_of_day_counts_and_one_dated_after_it_does_not(self):
        m = dworld()
        m.orders(pom('PO-1', qty='100'))
        m.dockets(docket('DK-1', 'PO-1', date='2026-09-29', delivered='10', accepted='10'), docket('DK-2', 'PO-1', date='2026-09-30', delivered='20', accepted='20'),
                  docket('DK-3', 'PO-1', date='2026-10-01', delivered='40', accepted='40'))
        c = cov(m, AS_OF_DAY)
        self.assertEqual((c['accepted_delivered_micro'], c['delivered_micro']), (30 * M, 30 * M))
        self.assertEqual([d['docket'] for d in c['dockets']], ['delivery/DK-1', 'delivery/DK-2'])

    def test_a_held_docket_for_a_counted_order_is_noted_and_one_for_another_order_is_not(self):
        m = dworld()
        m.orders(pom('PO-1', qty='100'), pom('PO-9', qty='5', project='PRJ-002', rate='110000'))
        m.dockets(docket('DK-1', 'PO-1', delivered='-5', accepted='1'), docket('DK-2', 'PO-9', delivered='-5', accepted='1'), docket('DK-3', 'PO-1', delivered='7', accepted='7'))
        c = cov(m)
        held = [n for n in c['notes'] if 'is held' in n]
        self.assertEqual(len(held), 1, c['notes'])
        self.assertEqual(held[0], 'docket DK-1 is held (QUANTITY_INVALID) and is not counted')
        self.assertEqual((c['accepted_delivered_micro'], len(c['dockets'])), (7 * M, 1))

    def test_the_status_map_helper_gives_no_class_without_a_policy_or_without_a_map(self):
        class FakeFacts:
            def __init__(self, policy):
                self.policy = policy
        po = {'status': 'open'}
        self.assertIsNone(DEM._po_class(FakeFacts(None), po))
        self.assertIsNone(DEM._po_class(FakeFacts({}), po))
        self.assertIsNone(DEM._po_class(FakeFacts({'po_status_map': None}), po))
        self.assertEqual(DEM._po_class(FakeFacts({'po_status_map': {'open': 'committed'}}), po), 'committed')
        self.assertIsNone(DEM._po_class(FakeFacts({'po_status_map': {'open': 'committed'}}), {'status': None}))
        self.assertIsNone(DEM._po_class(FakeFacts({'po_status_map': {'open': 'committed'}}), {'status': 'unmapped'}))

    def test_the_unit_key_is_trimmed_and_lower_case_and_blank_or_missing_units_have_none(self):
        for raw, key in ((' Tonne ', 'tonne'), ('M3', 'm3'), ('', None), ('   ', None), (None, None), (5, None), (['kg'], None)):
            self.assertEqual(DEM._unit_key(raw), key, repr(raw))

    def test_a_demand_without_a_unit_has_no_unit_mismatch_whatever_the_orders_are(self):
        m = dworld()
        m.orders(pom('PO-1', qty='100', unit='kg'))
        ctx = m.ctx('PRJ-001', AS_OF_DAY)
        req = req_of(ctx)
        self.assertEqual(len(DEM.unit_mismatches(ctx, req)), 1)
        for blank in (None, '', '  '):
            self.assertEqual(DEM.unit_mismatches(ctx, dict(req, unit=blank)), [], repr(blank))


# ------------------------------------------------------------------------------------------------------------------------------------------------ opportunity
def pb_quote(qid='Q-6', rate='1740'):
    return quote(qid, 'SUP-001', 'MAT-PBOARD', 'Plasterboard 13mm', '2026-09-08', '2026-11-15', rate, 'AUD', '', '', '0', 'delivered', '7')


def pb_readings(qid='Q-6'):
    return [reading(qid, 'thickness_mm', '13', verified_by='alice'), reading(qid, 'unit', 'sheet', verified_by='alice')]


def oworld(quote_rate='1740', order_rate='1850', order_amount=None, **kw):
    m = mkt_world(**kw)
    m.quote_rows(pb_quote(rate=quote_rate))
    m.readings(*pb_readings())
    m.demands(demand('DEM-1', 'PRJ-001', 'MAT-PBOARD', '2000', 'sheet', '2026-12-01'))
    m.orders(pom('PO-1', mat='MAT-PBOARD', unit='sheet', qty='1300', rate=order_rate, date='2026-08-25', amount=order_amount))
    return m


def discover(m, last_paid=None):
    ctx = m.ctx(as_of=AS_OF_DAY)
    out = []
    saved = CP.last_paid
    if last_paid is not None:
        CP.last_paid = lambda c, r: last_paid(saved(c, r))
    try:
        for req in [r for r in CP.requirements(ctx) if r['kind'] == 'demand']:
            out.extend(OP.discover(ctx, req, DEM.coverage(ctx, req)))
    finally:
        CP.last_paid = saved
    return out


class TestOpportunityEdges(unittest.TestCase):
    def test_tax_adjustment_converts_in_the_right_direction_with_a_note_and_only_with_a_configured_rate(self):
        mp = {'basis': {'gst_bps': 1000}}
        self.assertEqual(OP.tax_adjust(mp, 'ex_gst', 'inc_gst', 1000), (1100, 'converted from ex_gst to inc_gst at 1000 basis points'))
        self.assertEqual(OP.tax_adjust(mp, 'inc_gst', 'ex_gst', 1100), (1000, 'converted from inc_gst to ex_gst at 1000 basis points'))
        self.assertEqual(OP.tax_adjust(mp, 'ex_gst', 'inc_gst', 1850), (2035, 'converted from ex_gst to inc_gst at 1000 basis points'))
        self.assertEqual(OP.tax_adjust(mp, 'ex_gst', 'ex_gst', 1234), (1234, ''))
        self.assertEqual(OP.tax_adjust(mp, 'inc_gst', 'inc_gst', 1234), (1234, ''))
        cents, why = OP.tax_adjust({'basis': {}}, 'ex_gst', 'inc_gst', 1000)
        self.assertIsNone(cents)
        self.assertIn('no GST rate is configured', why)

    def test_a_gap_of_exactly_the_policy_minimum_is_an_opportunity_and_one_basis_point_less_is_not(self):
        (o,) = discover(oworld(quote_rate='1940', order_rate='2000'))                       # 60 / 2000 = 300 bps = min_gap_bps
        self.assertEqual((o['unit_gap_cents'], o['gap_bps']), (60, 300))
        self.assertEqual(discover(oworld(quote_rate='1941', order_rate='2000')), [])         # 59 / 2000 = 295 bps
        self.assertEqual(len(discover(oworld(quote_rate='1700', order_rate='2000'))), 1)

    def test_a_quote_whose_landed_cost_equals_a_zero_priced_reference_is_not_an_opportunity_and_has_no_ratio_to_compute(self):
        # a 1 cent USD quote at 1000 USD per AUD lands at 0 AUD cents, the same as an order placed at a zero rate: a gap of exactly zero, with no basis-point ratio to the zero reference
        m = mkt_world()
        m.quote_rows(quote('Q-I', 'SUP-004', 'MAT-STEEL', 's', '2026-09-10', '2026-12-31', '1', 'USD', '1000', '2026-09-30', '0', 'FOB', '28'))
        m.fx(fxrow('2026-09-30', '1000.0000', 'AUD/USD'))
        m.readings(*std_readings('Q-I'))
        m.assumptions(*[['Q-I', c, '0', '', 'AUD', 'allowance', 'none', 'alice', '2026-09-20'] for c in ('insurance', 'clearance')], ['Q-I', 'duty', '', '0', '', 'rate', 'none', 'alice', '2026-09-20'])
        m.checks(*[['Q-I', c, 'resolved', 'EV-%s' % c, 'carol', '2026-09-25'] for c in ('customs_classification', 'duty_rate_confirmed', 'import_permit')])
        m.demands(demand('DEM-1', 'PRJ-001', 'MAT-STEEL', '100', 'tonne', '2026-12-01'))
        m.orders(pom('PO-1', qty='10', rate='0', amount='1000', date='2026-08-25'))
        ctx = m.ctx(as_of=AS_OF_DAY)
        req = req_of(ctx)
        ref = CP.last_paid(ctx, req)
        (q,) = CP.candidates(ctx, req)
        o = CP.eval_quote(ctx, q, req, 'quote_ranking', None)
        self.assertEqual((ref['landed']['unit_cents'], o['landed']['unit_cents'], o['qualification'], o['landed']['complete'], o['gate']['class']), (0, 0, 'current', True, 'comparable_with_adjustment'))
        self.assertEqual(OP.discover(ctx, req, DEM.coverage(ctx, req)), [])

    def test_a_reference_that_differs_from_the_quote_in_anything_but_its_unrecorded_delivery_basis_is_not_used(self):
        def swap(ref, cls=None, codes=None):
            if ref is None:
                return None
            g = dict(ref['gate'])
            if cls is not None:
                g['class'] = cls
            if codes is not None:
                g['codes'] = codes
            return dict(ref, gate=g)
        m = oworld()
        self.assertEqual(len(discover(m, lambda r: swap(r))), 1)
        self.assertEqual(len(discover(m, lambda r: swap(r, 'partially_comparable', ['REFERENCE_BASIS_UNRECORDED']))), 1)
        # another code alone is enough to refuse, whatever the class
        self.assertEqual(discover(m, lambda r: swap(r, 'partially_comparable', ['UNIT_UNVERIFIED', 'REFERENCE_BASIS_UNRECORDED'])), [])
        self.assertEqual(discover(m, lambda r: swap(r, 'comparable', ['QUOTE_TEXT_UNVERIFIED'])), [])
        # a class that cannot be ranked is enough to refuse, whatever the codes
        self.assertEqual(discover(m, lambda r: swap(r, 'not_comparable', ['REFERENCE_BASIS_UNRECORDED'])), [])
        self.assertEqual(discover(m, lambda r: swap(r, 'unverified', [])), [])


# ------------------------------------------------------------------------------------------------------------------------------------------------ purchasing
def pb_order(po, project, rate, date, qty='10', sup='SUP-001', amount=None):
    return pom(po, sup, project, mat='MAT-PBOARD', qty=qty, rate=rate, date=date, unit='sheet', amount=amount)


def portfolio(m, as_of=AS_OF_DAY):
    return PU.opportunities(m.ctx(None, as_of, ['PRJ-001', 'PRJ-002']), {'PRJ-001', 'PRJ-002'})


class TestPortfolioEdges(unittest.TestCase):
    def test_orders_on_the_window_start_and_the_as_of_day_are_inside_the_window_and_those_a_day_outside_are_not(self):
        # window 365 days before the as-of day 2026-09-30: it starts on 2025-09-30
        for day, inside in (('2025-09-29', False), ('2025-09-30', True), ('2026-09-30', True), ('2026-10-01', False)):
            m = mkt_world()
            m.orders(pb_order('PO-1', 'PRJ-001', '100', '2026-08-01'), pb_order('PO-2', 'PRJ-002', '200', day, sup='SUP-002'))
            opps, boundary = portfolio(m, AS_OF_DAY)
            self.assertFalse(boundary, day)
            self.assertEqual(len(opps), 1 if inside else 0, day)
            if inside:
                self.assertEqual((opps[0]['window_start'], opps[0]['window_end'], opps[0]['estimate_cents']), ('2025-09-30', AS_OF_DAY, 1000), day)

    def test_a_project_that_paid_a_zero_rate_gives_no_ratio_and_no_opportunity(self):
        m = mkt_world()
        m.orders(pb_order('PO-1', 'PRJ-001', '0', '2026-08-01', amount='1000'), pb_order('PO-2', 'PRJ-002', '200', '2026-08-02', sup='SUP-002'))
        # the lowest average is zero: no ratio to the lowest exists, so nothing is reported
        self.assertEqual(portfolio(m)[0], [])

    def test_projects_paying_the_same_average_as_the_lowest_add_nothing_to_the_estimate(self):
        m = mkt_world()
        m.projects(['PRJ-003', 'P3', '10000000', '2026-01-01', '2027-01-01'])
        m.orders(pb_order('PO-1', 'PRJ-001', '100', '2026-08-01'), pb_order('PO-2', 'PRJ-002', '100', '2026-08-02', sup='SUP-002'), pb_order('PO-3', 'PRJ-003', '200', '2026-08-03', sup='SUP-002'))
        opps, _ = PU.opportunities(m.ctx(None, AS_OF_DAY, ['PRJ-001', 'PRJ-002', 'PRJ-003']), {'PRJ-001', 'PRJ-002', 'PRJ-003'})
        (o,) = opps
        self.assertEqual((o['lowest_project'], o['highest_project'], o['gap_bps'], o['estimate_cents']), ('PRJ-001', 'PRJ-003', 10000, 1000))


# ------------------------------------------------------------------------------------------------------------------------------------------------ suppliers
def profile(m, sup='SUP-001'):
    return SU.profiles(m.ctx(None, AS_OF_DAY, ['PRJ-001']), None)[sup]


class TestSupplierEdges(unittest.TestCase):
    def test_a_docket_dated_on_the_as_of_day_counts_and_one_dated_after_it_does_not(self):
        m = mkt_world()
        m.orders(pom('PO-1', qty='10', date='2026-09-01'), pom('PO-2', qty='10', date='2026-09-01', rate='110000'))
        m.dockets(docket('DK-1', 'PO-1', date='2026-09-30', delivered='10', accepted='10'), docket('DK-2', 'PO-2', date='2026-10-01', delivered='10', accepted='10'))
        p = profile(m)
        self.assertEqual(p['orders_with_deliveries'], 1)
        self.assertEqual([e for e in p['evidence']], [('purchase_order/PO-1', 1), ('delivery/DK-1', 1)])
        self.assertEqual(p['lead_time_days'], {'min': 29, 'median': 29, 'max': 29, 'n': 1})

    def test_an_order_dated_on_the_as_of_day_is_a_supplier_order_and_one_dated_after_it_is_not(self):
        m = mkt_world()
        m.orders(pom('PO-1', qty='10', date='2026-09-30'), pom('PO-2', qty='10', date='2026-10-01', rate='110000'))
        p = profile(m)
        self.assertEqual((p['orders'], p['period']), (1, {'first_order': '2026-09-30', 'last_order': '2026-09-30'}))
        m2 = mkt_world()
        m2.orders(pom('PO-2', qty='10', date='2026-10-01'))
        self.assertEqual(SU.profiles(m2.ctx(None, AS_OF_DAY, ['PRJ-001']), None), {})

    def test_a_same_day_delivery_is_a_lead_time_of_zero_and_a_docket_before_the_order_is_not_a_lead_time(self):
        m = mkt_world()
        m.orders(pom('PO-1', qty='10', date='2026-08-01'), pom('PO-2', qty='10', date='2026-08-05', rate='110000'), pom('PO-3', qty='10', date='2026-08-10', rate='120000'),
                 pom('PO-4', qty='10', date='2026-08-20', rate='130000'))
        m.dockets(docket('DK-1', 'PO-1', date='2026-08-01'), docket('DK-2', 'PO-2', date='2026-08-09'), docket('DK-3', 'PO-3', date='2026-08-15'), docket('DK-4', 'PO-4', date='2026-08-18'))
        p = profile(m)
        self.assertEqual(p['orders_with_deliveries'], 4)
        self.assertEqual(p['lead_time_days'], {'min': 0, 'median': 4, 'max': 5, 'n': 3})          # 0, 4 and 5 days; the docket two days before its order is left out

    def test_the_price_spread_needs_two_orders_for_the_material_and_a_positive_lowest_rate(self):
        m = mkt_world()
        m.orders(pom('PO-1', qty='10', rate='100', date='2026-08-01'), pom('PO-2', qty='10', rate='110', date='2026-08-02'),
                 pom('PO-3', mat='MAT-PBOARD', unit='sheet', qty='10', rate='500', date='2026-08-03'),
                 pom('PO-4', mat='MAT-CU', unit='metre', qty='10', rate='0', date='2026-08-04', amount='1000'), pom('PO-5', mat='MAT-CU', unit='metre', qty='10', rate='50', date='2026-08-05'))
        p = profile(m)
        self.assertEqual(p['price_spread_bps_by_material'], {'MAT-STEEL': 1000})                    # one order of plasterboard: no spread; a zero lowest rate: no ratio


if __name__ == '__main__':
    unittest.main()
