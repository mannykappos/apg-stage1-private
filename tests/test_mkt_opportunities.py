import json, unittest
from . import _path                                         # noqa: F401
from .helpers_mkt import *
from apg.mkt import compare as CP, demand as DEM, opportunity as OP, purchasing as PU, suppliers as SU

M = 1_000_000


def pb_quote(qid='Q-6', rate='1740', valid='2026-11-15', issue='2026-09-08', sup='SUP-001', cur='AUD', basis='delivered'):
    return quote(qid, sup, 'MAT-PBOARD', 'Plasterboard 13mm', issue, valid, rate, cur, '', '', '0', basis, '7')


def pb_readings(qid='Q-6', verified_by='alice'):
    return [reading(qid, 'thickness_mm', '13', verified_by=verified_by), reading(qid, 'unit', 'sheet', verified_by=verified_by)]


def world(quote_rows=(pb_quote(),), readings=True, qty='2000', ordered='1300', rate='1850', **kw):
    m = mkt_world(**kw)
    m.quote_rows(*quote_rows)
    if readings:
        m.readings(*[r for q in quote_rows for r in pb_readings(q[0])])
    m.demands(demand('DEM-1', 'PRJ-001', 'MAT-PBOARD', qty, 'sheet', '2026-12-01'))
    if ordered:
        m.orders(pom('PO-1', mat='MAT-PBOARD', unit='sheet', qty=ordered, rate=rate, date='2026-08-25'))
    return m


def discover(m, as_of='2026-09-30'):
    ctx = m.ctx(as_of=as_of)
    out = []
    for req in [r for r in CP.requirements(ctx) if r['kind'] == 'demand']:
        out.extend(OP.discover(ctx, req, DEM.coverage(ctx, req)))
    return out


class TestOpportunities(unittest.TestCase):
    def test_a_comparable_current_quote_below_the_last_rate_paid_is_an_estimate_for_the_quantity_not_yet_ordered(self):
        (o,) = discover(world())
        self.assertEqual((o['quote'], o['reference'], o['unit_gap_cents'], o['gap_bps'], o['quote_unit_cents'], o['reference_unit_cents']), ('supplier_quote/Q-6', 'purchase_order/PO-1', 110, 595, 1740, 1850))
        self.assertEqual((o['quantity_micro'], o['gross_estimate_cents']), (700 * M, 77_000))        # 110 x 700 sheets not yet ordered
        self.assertEqual((o['status'], o['label'], o['implementation_status'], o['approval_status']), ('estimate', 'indicative', 'not_started', 'not_approved'))
        self.assertEqual(o['baseline'], {'basis': 'last rate paid for this project and material', 'approved': False, 'delivery_basis_recorded': False})
        self.assertTrue(o['human_approval_required'])
        self.assertIn('unknown', o['incremental_costs'])
        self.assertTrue(any('approved comparable baseline' in r for r in o['evidence_required_to_verify']))

    def test_when_nothing_is_left_to_buy_the_gap_is_stated_but_no_amount_is_invented(self):
        (o,) = discover(world(ordered='2000'))
        self.assertEqual((o['unit_gap_cents'], o['quantity_micro'], o['gross_estimate_cents']), (110, None, None))

    def test_a_gap_below_the_policy_minimum_is_not_an_opportunity(self):
        self.assertEqual(discover(world(rate='1760')), [])                                   # 20 / 1760 = 1.14% < 3.00%
        self.assertEqual(len(discover(world(rate='1794'))), 1)                               # 54 / 1794 = 3.01%
        self.assertEqual(discover(world(rate='1793')), [])                                   # 53 / 1793 = 2.96%

    def test_a_dearer_or_equal_quote_is_not_an_opportunity(self):
        self.assertEqual(discover(world((pb_quote(rate='1850'),))), [])
        self.assertEqual(discover(world((pb_quote(rate='1900'),))), [])

    def test_without_a_reference_order_there_is_no_opportunity(self):
        self.assertEqual(discover(world(ordered='')), [])

    def test_a_quote_that_is_not_fully_comparable_never_makes_an_opportunity_however_cheap(self):
        self.assertEqual(discover(world(readings=False)), [])                                # text unverified: partially comparable
        m = world((pb_quote(rate='100'),), readings=False)
        self.assertEqual(discover(m), [])

    def test_an_expired_or_stale_quote_never_makes_an_opportunity(self):
        self.assertEqual(discover(world((pb_quote(valid='2026-09-29'),))), [])
        self.assertEqual(discover(world((pb_quote(issue='2026-06-01'),))), [])

    def test_an_international_quote_with_unresolved_checks_never_makes_an_opportunity(self):
        q = quote('Q-6', 'SUP-004', 'MAT-PBOARD', 's', '2026-09-08', '2026-11-15', '1000', 'USD', '0.6540', '2026-09-30', '10', 'FOB', '7')
        m = world((q,))
        m.fx(fxrow('2026-09-30', '0.6540'))
        self.assertEqual(discover(m), [])

    def test_different_tax_treatments_are_converted_only_with_a_configured_rate(self):
        f = DM.demo_mkt_fields()
        f['basis']['price_tax'] = {'supplier_quote': 'inc_gst', 'purchase_order': 'ex_gst'}
        m = world()
        m.set_mkt(**f)
        self.assertEqual(discover(m), [])                                                    # no GST rate configured: not comparable on tax
        f['basis']['gst_bps'] = 1000
        m.set_mkt(**f)
        (o,) = discover(m)
        self.assertEqual((o['quote_unit_cents'], o['unit_gap_cents']), (1582, 1850 - 1582))        # inc_gst quote taken back to ex_gst: 1740 / 1.1 = 1581.8 -> 1582
        self.assertIn('converted from inc_gst to ex_gst at 1000 basis points', o['tax_note'])

    def test_claiming_a_saving_always_refuses_and_no_code_path_reaches_realised(self):
        (o,) = discover(world())
        with self.assertRaises(OP.SavingNotVerified) as cm:
            OP.claim_saving(o)
        self.assertIn('needs an approved comparable baseline', str(cm.exception))
        for o2 in discover(world()) + discover(world(ordered='2000')):
            self.assertEqual(o2['status'], 'estimate')

    def test_the_reference_held_as_a_possible_duplicate_is_used_only_when_all_candidates_agree_and_says_so(self):
        m = mkt_world()
        m.quote_rows(pb_quote())
        m.readings(*pb_readings())
        m.demands(demand('DEM-1', 'PRJ-001', 'MAT-PBOARD', '2000', 'sheet', '2026-12-01'))
        m.orders(pom('PO-1', mat='MAT-PBOARD', unit='sheet', qty='1300', rate='1850', date='2026-08-25'), pom('PO-2', mat='MAT-PBOARD', unit='sheet', qty='1300', rate='1850', date='2026-08-25'))
        (o,) = discover(m)
        self.assertTrue(o['reference_held_as_duplicate_candidate'])
        m2 = mkt_world()
        m2.quote_rows(pb_quote())
        m2.readings(*pb_readings())
        m2.demands(demand('DEM-1', 'PRJ-001', 'MAT-PBOARD', '2000', 'sheet', '2026-12-01'))
        m2.orders(pom('PO-1', mat='MAT-PBOARD', unit='sheet', qty='1300', rate='1850', date='2026-08-25'), pom('PO-2', mat='MAT-PBOARD', unit='sheet', qty='1300', rate='1900', date='2026-08-25'))
        out = discover(m2)
        self.assertEqual(len(out), 1)                                                        # the two orders differ, so neither is held as a duplicate: the later one by key is the reference
        self.assertFalse(out[0]['reference_held_as_duplicate_candidate'])

    def test_the_opportunity_is_plain_data_with_no_realised_wording(self):
        text = json.dumps([{k: v for k, v in o.items() if k != 'offer_evaluation'} for o in discover(world())])
        self.assertNotIn('realised"', text.replace('not realised', ''))
        self.assertNotIn('saved', text)


class TestPortfolio(unittest.TestCase):
    def world(self, orders, **kw):
        m = mkt_world(**kw)
        m.orders(*orders)
        return m

    def pr(self, m, authorised, as_of='2026-09-30'):
        return PU.opportunities(m.ctx(None, as_of, authorised), set(authorised))

    A = lambda self, po, project, qty, rate, date='2026-08-01', sup='SUP-001': pom(po, sup, project, 'CC-01', date, 'MAT-PBOARD', qty, 'sheet', rate)

    def two(self, r1='100', r2='120'):
        return [pom('PO-1', 'SUP-001', 'PRJ-001', mat='MAT-PBOARD', unit='sheet', qty='10', rate=r1, date='2026-08-01'), pom('PO-2', 'SUP-002', 'PRJ-002', mat='MAT-PBOARD', unit='sheet', qty='20', rate=r2, date='2026-08-02')]

    def test_two_authorised_projects_paying_different_rates_give_an_estimate_for_the_extra_paid_over_the_lowest_average(self):
        opps, boundary = self.pr(self.world(self.two()), ['PRJ-001', 'PRJ-002'])
        self.assertFalse(boundary)
        (o,) = opps
        self.assertEqual((o['material'], o['lowest_project'], o['highest_project'], o['gap_bps'], o['estimate_cents'], o['status'], o['label']), ('MAT-PBOARD', 'PRJ-001', 'PRJ-002', 2000, 400, 'estimate', 'indicative'))
        self.assertEqual([(r['project'], r['average_unit_cents'], r['volume_micro']) for r in o['projects']], [('PRJ-001', 100, 10 * M), ('PRJ-002', 120, 20 * M)])
        self.assertTrue(any('no delivery basis' in c for c in o['caveats']))

    def test_the_average_is_volume_weighted(self):
        orders = [pom('PO-1', mat='MAT-PBOARD', unit='sheet', qty='10', rate='100', date='2026-08-01', project='PRJ-001'), pom('PO-3', mat='MAT-PBOARD', unit='sheet', qty='30', rate='200', date='2026-08-03', project='PRJ-001'),
                  pom('PO-2', mat='MAT-PBOARD', unit='sheet', qty='20', rate='150', date='2026-08-02', project='PRJ-002', supplier='SUP-002')]
        (o,) = self.pr(self.world(orders), ['PRJ-001', 'PRJ-002'])[0]
        self.assertEqual([(r['project'], r['average_unit_cents']) for r in o['projects']], [('PRJ-001', 175), ('PRJ-002', 150)])        # (10x100 + 30x200) / 40
        self.assertEqual((o['lowest_project'], o['highest_project'], o['estimate_cents']), ('PRJ-002', 'PRJ-001', 1000))        # the higher-average project's own volume: (175 - 150) x 40

    def test_a_gap_below_the_policy_threshold_or_too_few_projects_reports_nothing(self):
        self.assertEqual(self.pr(self.world(self.two('100', '104')), ['PRJ-001', 'PRJ-002'])[0], [])         # 4.00% < 5.00%
        self.assertEqual(len(self.pr(self.world(self.two('100', '105')), ['PRJ-001', 'PRJ-002'])[0]), 1)     # exactly 5.00%
        single = [pom('PO-1', mat='MAT-PBOARD', unit='sheet', qty='10', rate='100'), pom('PO-2', mat='MAT-PBOARD', unit='sheet', qty='10', rate='200', date='2026-08-02', supplier='SUP-002')]
        self.assertEqual(self.pr(self.world(single), ['PRJ-001'])[0], [])

    def test_when_the_viewer_cannot_see_every_project_that_bought_it_nothing_is_reported_and_nothing_leaks(self):
        m = self.world(self.two())
        opps, boundary = self.pr(m, ['PRJ-001'])
        self.assertEqual((opps, boundary), ([], True))
        self.assertNotIn('PRJ-002', json.dumps(opps))
        m3 = self.world(self.two())
        r = m3.mtres(authorised=('PRJ-001',))
        self.assertNotIn('PRJ-002', json.dumps([s for s in r['signals'] if s['rule']['id'] == 'DET-MP10']))
        self.assertEqual(r['analyses']['portfolio_boundary_applied'], True)
        self.assertIn('PORTFOLIO_BOUNDARY_APPLIED', r['rule_runs']['MP10']['notes'])

    def test_orders_outside_the_window_or_in_other_units_or_not_committed_are_ignored(self):
        orders = [pom('PO-1', mat='MAT-PBOARD', unit='sheet', qty='10', rate='100', date='2026-08-01'), pom('PO-2', mat='MAT-PBOARD', unit='sheet', qty='10', rate='500', date='2024-01-01', project='PRJ-002', supplier='SUP-002'),
                  pom('PO-3', mat='MAT-PBOARD', unit='each', qty='10', rate='500', date='2026-08-02', project='PRJ-002', supplier='SUP-002'),
                  pom('PO-4', mat='MAT-PBOARD', unit='sheet', qty='10', rate='500', date='2026-08-02', project='PRJ-002', supplier='SUP-002', status='draft')]
        self.assertEqual(self.pr(self.world(orders), ['PRJ-001', 'PRJ-002']), ([], False))

    def test_orders_held_as_duplicates_are_not_used_for_a_rate_gap(self):
        orders = [pom('PO-1', mat='MAT-PBOARD', unit='sheet', qty='10', rate='100', date='2026-08-01'),
                  pom('PO-2', mat='MAT-PBOARD', unit='sheet', qty='10', rate='500', date='2026-08-02', project='PRJ-002', supplier='SUP-002'),
                  pom('PO-3', mat='MAT-PBOARD', unit='sheet', qty='10', rate='500', date='2026-08-02', project='PRJ-002', supplier='SUP-002')]
        self.assertEqual(self.pr(self.world(orders), ['PRJ-001', 'PRJ-002'])[0], [])


class TestSuppliers(unittest.TestCase):
    def world(self, n=3, delivered='10', accepted='10', ordered='10', sup='SUP-001', step=1):
        m = mkt_world()
        m.orders(*[pom('PO-%d' % i, sup, 'PRJ-001', 'MAT-STEEL', ordered, str(100000 + i * step), '2026-08-0%d' % i) for i in range(1, n + 1)])
        m.dockets(*[docket('DK-%d' % i, 'PO-%d' % i, date='2026-08-%02d' % (i * 3 + 1), delivered=delivered, accepted=accepted) for i in range(1, n + 1)])
        return m

    def profile(self, m, sup='SUP-001'):
        return SU.profiles(m.ctx(), None)[sup]

    def test_a_small_sample_is_shown_but_no_conclusion_is_drawn(self):
        p = self.profile(self.world(n=2, accepted='5'))
        self.assertTrue(p['limited_history'])
        self.assertEqual(p['levels'], {'fill_rate': 'limited_history', 'acceptance_rate': 'limited_history'})
        self.assertEqual((p['fill_rate_bps'], p['acceptance_rate_bps']), (5000, 5000))
        self.assertIn('no conclusion is drawn', p['sample_note'])

    def test_a_large_enough_sample_below_the_level_is_flagged_below_level(self):
        p = self.profile(self.world(n=3, accepted='9'))
        self.assertEqual(p['levels'], {'fill_rate': 'below_level', 'acceptance_rate': 'below_level'})            # 90% against 95%
        p2 = self.profile(self.world(n=3, accepted='10'))
        self.assertEqual(p2['levels'], {'fill_rate': 'at_or_above_level', 'acceptance_rate': 'at_or_above_level'})

    def test_exactly_at_the_level_is_not_below_it(self):
        m = self.world(n=3, ordered='20', delivered='20', accepted='19')                         # 95.00%
        self.assertEqual(self.profile(m)['levels']['fill_rate'], 'at_or_above_level')

    def test_orders_without_a_docket_are_not_counted_as_short(self):
        m = self.world(n=3)
        m.orders(pom('PO-9', 'SUP-001', 'PRJ-001', 'MAT-STEEL', '100', '100009', '2026-08-09'))
        p = self.profile(m)
        self.assertEqual((p['orders'], p['orders_with_deliveries'], p['fill_rate_bps']), (4, 3, 10000))

    def test_lead_time_and_price_spread_are_observed_figures(self):        # orders 1-3 Aug, dockets 4, 7, 10 Aug: lead times 3, 5, 7 days
        p = self.profile(self.world(n=3, step=1000))
        self.assertEqual(p['lead_time_days'], {'min': 3, 'median': 5, 'max': 7, 'n': 3})
        self.assertEqual(p['price_spread_bps_by_material'], {'MAT-STEEL': 198})                  # (103,000 - 101,000) / 101,000 = 1.98%
        self.assertEqual(p['period'], {'first_order': '2026-08-01', 'last_order': '2026-08-03'})

    def test_what_is_not_measured_is_stated_and_the_profile_is_not_a_ranking_or_prediction(self):
        p = self.profile(self.world())
        self.assertTrue(any('on-time delivery' in x for x in p['not_measured']))
        self.assertIn('not a prediction and not a ranking', p['note'])

    def test_only_authorised_projects_orders_are_used(self):
        m = self.world()
        self.assertEqual(SU.profiles(m.ctx(), {'PRJ-002'}), {})
        self.assertEqual(SU.profiles(m.ctx(), {'PRJ-001'})['SUP-001']['orders'], 3)


if __name__ == '__main__':
    unittest.main()
