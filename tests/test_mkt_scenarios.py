import json, unittest
from . import _path                                         # noqa: F401
from .helpers_mkt import *
from apg import canon
from apg.mkt import compare as CP, demand as DEM, scenarios as SC

M = 1_000_000


def steel(qid='Q-1', rate='265000', valid='2026-12-31', lead='21', sup='SUP-001', basis='delivered', freight='0'):
    return quote(qid, sup, 'MAT-STEEL', 's', '2026-09-10', valid, rate, 'AUD', '', '', freight, basis, lead)


def world(*quotes, qty='40', required='2026-12-01', readings=True, **kw):
    m = mkt_world(**kw)
    m.quote_rows(*quotes)
    if readings:
        m.readings(*[r for q in quotes for r in std_readings(q[0])])
    m.demands(demand('DEM-1', 'PRJ-001', 'MAT-STEEL', qty, 'tonne', required))
    return m


def build(m, as_of='2026-09-30'):
    ctx = m.ctx(as_of=as_of)
    (req,) = [r for r in CP.requirements(ctx) if r['kind'] == 'demand']
    return SC.build(ctx, req, DEM.coverage(ctx, req)), ctx, req


def by(scn, name, offer=None):
    return [x for x in scn['scenarios'] if x['scenario'] == name and (offer is None or x.get('offer') == offer)]


class TestScenarios(unittest.TestCase):
    def test_buy_now_costs_storage_and_financing_are_each_computed_and_added(self):
        s, _, _ = build(world(steel()))
        (b,) = by(s, 'buy_now')
        self.assertEqual((b['quantity_micro'], b['landed_unit_cents'], b['landed_total_cents']), (40 * M, 265000, 10_600_000))
        inc = {i['label'].split(' ')[0]: i['cents'] for i in b['incremental_costs']}
        self.assertEqual(inc, {'storage': 82_000, 'financing': 95_255})                      # 41 days at 0.50 x 40 t; 10.6m x 8% x 41/365
        self.assertEqual(b['total_cost_cents'], 10_777_255)
        self.assertEqual((b['schedule']['order_date'], b['schedule']['delivery_date'], b['schedule']['meets_required_date'], b['schedule']['days_before_required']), ('2026-09-30', '2026-10-21', True, 41))
        self.assertEqual((b['working_capital']['cash_out_date'], b['working_capital']['funded_cents']), ('2026-10-21', 10_600_000))

    def test_wait_orders_on_the_latest_day_that_still_meets_the_date_and_uses_only_the_configured_paths(self):
        s, _, _ = build(world(steel()))
        names = [x['scenario'] for x in by(s, 'wait') + [x for x in s['scenarios'] if x['scenario'].startswith('wait:')]]
        self.assertEqual(sorted(names), ['wait:down_5pct', 'wait:flat', 'wait:up_5pct'])
        flat = by(s, 'wait:flat')[0]
        self.assertEqual((flat['schedule']['order_date'], flat['wait_days'], flat['landed_total_cents'], flat['total_cost_cents']), ('2026-11-03', 34, 10_600_000, 10_630_263))
        up, down = by(s, 'wait:up_5pct')[0], by(s, 'wait:down_5pct')[0]
        self.assertEqual((up['landed_unit_cents'], up['landed_total_cents']), (278_250, 11_130_000))
        self.assertEqual((down['landed_unit_cents'], down['landed_total_cents']), (251_750, 10_070_000))
        self.assertTrue(all('assumption a person configured, not a forecast' in ' '.join(x['uncertainty']) for x in (flat, up, down)))

    def test_stage_splits_by_the_policy_and_adds_the_policy_staging_cost(self):
        s, _, _ = build(world(steel()))
        (st,) = by(s, 'stage')
        self.assertEqual([(t['quantity_micro'], t['order_date']) for t in st['tranches']], [(20 * M, '2026-09-30'), (20 * M, '2026-10-30')])
        self.assertEqual(st['incremental_total_cents'], 142_405)                             # 41,000 + 47,627 + 11,000 + 12,778 + 30,000
        self.assertEqual(st['total_cost_cents'], 10_742_405)
        self.assertEqual(st['schedule']['meets_required_date'], True)

    def test_a_scenario_is_built_for_every_rankable_offer_and_no_winner_is_chosen(self):
        s, _, _ = build(world(steel('Q-1'), steel('Q-2', '255000', sup='SUP-002')))
        offers = sorted({x['offer'] for x in s['scenarios'] if x.get('offer')})
        self.assertEqual(offers, ['supplier_quote/Q-1', 'supplier_quote/Q-2'])
        for o in offers:
            self.assertTrue(by(s, 'buy_now', o) and by(s, 'stage', o))
        self.assertIn('no offer is chosen', s['note'])
        self.assertFalse(any(k in json.dumps(s) for k in ('"recommended"', '"winner"', '"best_offer"')))

    def test_each_scenario_carries_its_offers_class_and_blockers_so_it_cannot_be_read_without_them(self):
        s, _, _ = build(world(steel('Q-1'), steel('Q-2', '255000', sup='SUP-002'), readings=False))
        for x in s['scenarios']:
            if x['scenario'] != 'negotiate':
                self.assertEqual(x['offer_class'], 'partially_comparable')
                self.assertIn('GATE:partially_comparable', x['offer_blockers'])

    def test_every_scenario_is_labelled_scenario_only_and_changes_no_forecast(self):
        s, _, _ = build(world(steel(), steel('Q-2', '255000', sup='SUP-002')))
        self.assertFalse(s['changes_authoritative_forecast'])
        self.assertTrue(s['human_approval_required'])
        for x in s['scenarios']:
            self.assertFalse(x['changes_authoritative_forecast'])
            self.assertTrue(x['human_approval_required'])
            self.assertIn(x.get('status'), ('scenario_only', 'cannot_assess', 'not_available'))

    def test_building_scenarios_writes_nothing(self):
        m = world(steel())
        before = {k: len(m.s.query(k)) for k in ('forecast', 'ctc_line', 'budget_line', 'purchase_order', 'supplier_quote', 'finding', 'repro_run')}
        build(m)
        build(m)
        self.assertEqual({k: len(m.s.query(k)) for k in before}, before)

    def test_without_configured_price_paths_the_wait_scenario_is_not_assessed_and_no_trend_is_assumed(self):
        f = DM.demo_mkt_fields()
        del f['scenarios']['price_paths']
        m = world(steel())
        m.set_mkt(**f)
        m.observations(*[obs('O%d' % i, date='2026-0%d-15' % i, value=str(10000 + i * 300)) for i in (6, 7, 8, 9)])             # a rising index
        s, _, _ = build(m)
        (w,) = by(s, 'wait')
        self.assertEqual(w['status'], 'cannot_assess')
        self.assertIn('APG applies no rule that prices rise or fall', w['why'])
        self.assertEqual(w['latest_order_date'], '2026-11-03')

    def test_a_rising_index_is_shown_as_history_and_changes_no_scenario_number(self):
        m = world(steel())
        s0, _, _ = build(m)
        m.observations(*[obs('O%d' % i, date='2026-0%d-15' % i, value=str(10000 + i * 300)) for i in (6, 7, 8, 9)])
        s1, _, _ = build(m)
        self.assertEqual(s0['context']['status'], 'insufficient_history')
        self.assertEqual((s1['context']['status'], s1['context']['direction'], s1['context']['points'], s1['context']['from'], s1['context']['to']), ('history', 'up', 4, '2026-06-15', '2026-09-15'))
        self.assertEqual(s1['context']['change_bps'], 763)                                   # 11,800 to 12,700 is +7.63%
        self.assertIn('does not predict future prices and feeds no scenario below', s1['context']['note'])
        keep = ('scenario', 'offer', 'landed_unit_cents', 'landed_total_cents', 'incremental_costs', 'total_cost_cents', 'schedule', 'working_capital', 'evidence_gaps')
        strip = lambda s: [{k: x.get(k) for k in keep} for x in s['scenarios']]
        self.assertEqual(strip(s0), strip(s1))                                               # the index changes the qualification of the evidence (a fresh series), never a price or a cost
        self.assertEqual(s0['scenarios'][0]['offer_qualification'], 'qualified')
        self.assertEqual(s1['scenarios'][0]['offer_qualification'], 'current')

    def test_a_falling_index_does_not_invent_a_cheaper_wait_either(self):
        m = world(steel())
        m.observations(*[obs('O%d' % i, date='2026-0%d-15' % i, value=str(14000 - i * 300)) for i in (6, 7, 8, 9)])
        s, _, _ = build(m)
        self.assertEqual(s['context']['direction'], 'down')
        self.assertEqual(by(s, 'wait:flat')[0]['landed_total_cents'], 10_600_000)

    def test_a_quote_that_lapses_before_the_wait_date_says_the_price_is_modelled_not_offered(self):
        s, _, _ = build(world(steel(valid='2026-10-31')))
        w = by(s, 'wait:flat')[0]
        self.assertFalse(w['schedule']['quote_valid_on_order_date'])
        self.assertTrue(any('lapses on 2026-10-31, before the order date 2026-11-03' in g for g in w['evidence_gaps']))
        self.assertTrue(by(s, 'buy_now')[0]['schedule']['quote_valid_on_order_date'])

    def test_when_waiting_is_already_too_late_the_scenario_says_so_and_costs_nothing(self):
        s, _, _ = build(world(steel(lead='60'), required='2026-11-15'))
        (w,) = by(s, 'wait')
        self.assertEqual(w['status'], 'not_available')
        self.assertIn('was 2026-09-09, before the as-of day', w['why'])

    def test_a_delivery_that_cannot_meet_the_required_date_is_flagged_not_hidden(self):
        s, _, _ = build(world(steel(lead='60'), required='2026-11-15'))
        (b,) = by(s, 'buy_now')
        self.assertFalse(b['schedule']['meets_required_date'])
        self.assertEqual(b['schedule']['days_before_required'], -14)

    def test_missing_payment_terms_are_an_evidence_gap_never_assumed_cheaper(self):
        s, _, _ = build(world(steel()))
        self.assertIn('payment terms are not recorded: payment is taken to fall on the delivery date', by(s, 'buy_now')[0]['evidence_gaps'])
        m = world(steel())
        m.terms(['Q-1', 'payment_days', '30'])
        s2, _, _ = build(m)
        b = by(s2, 'buy_now')[0]
        self.assertEqual(b['working_capital']['cash_out_date'], '2026-11-20')
        self.assertEqual(b['working_capital']['days_paid_before_required'], 11)
        self.assertNotIn('payment terms are not recorded', ' '.join(b['evidence_gaps']))

    def test_a_deposit_is_financed_from_the_order_date(self):
        m = world(steel())
        m.terms(['Q-1', 'payment_days', '30'], ['Q-1', 'deposit_bps', '2000'])
        b = by(build(m)[0], 'buy_now')[0]
        self.assertEqual(b['working_capital']['deposit_cents'], 2_120_000)

    def test_a_missing_financing_rate_is_listed_as_a_gap_and_is_not_costed_as_zero(self):
        f = DM.demo_mkt_fields()
        del f['scenarios']['financing_bps_pa']
        m = world(steel())
        m.set_mkt(**f)
        b = by(build(m)[0], 'buy_now')[0]
        self.assertIn('no financing rate or day-count basis is configured: the working-capital cost is not assessed', b['evidence_gaps'])
        self.assertEqual([i['label'].split(' ')[0] for i in b['incremental_costs']], ['storage'])

    def test_a_missing_storage_rate_is_listed_as_a_gap_too(self):
        f = DM.demo_mkt_fields()
        del f['scenarios']['storage_cents_per_unit_per_day']
        m = world(steel())
        m.set_mkt(**f)
        b = by(build(m)[0], 'buy_now')[0]
        self.assertIn('no storage rate is configured: storage cost is not assessed', b['evidence_gaps'])

    def test_a_missing_stage_policy_makes_only_the_stage_scenario_unassessable(self):
        f = DM.demo_mkt_fields()
        del f['scenarios']['stage']
        m = world(steel())
        m.set_mkt(**f)
        s, _, _ = build(m)
        self.assertEqual(by(s, 'stage')[0]['status'], 'cannot_assess')
        self.assertEqual(by(s, 'buy_now')[0]['status'], 'scenario_only')

    def test_an_unknown_lead_time_stops_the_wait_scenario_and_says_why(self):
        s, _, _ = build(world(steel(lead='')))
        (w,) = by(s, 'wait')
        self.assertEqual((w['status'], w['why']), ('cannot_assess', 'lead time is not stated'))
        b = by(s, 'buy_now')[0]
        self.assertIsNone(b['schedule']['delivery_date'])
        self.assertIn('lead time is not stated: the delivery date cannot be computed', b['evidence_gaps'])

    def test_a_minimum_order_buys_more_than_needed_and_the_surplus_is_not_treated_as_reusable(self):
        m = world(steel(), qty='3')
        m.terms(['Q-1', 'moq', '10'])
        b = by(build(m)[0], 'buy_now')[0]
        self.assertEqual((b['landed_total_cents'], b['schedule']['surplus_qty_micro']), (2_650_000, 7 * M))
        self.assertTrue(any('surplus reuse is not assumed' in g for g in b['evidence_gaps']))

    def test_incomplete_landed_cost_is_called_a_lower_bound_in_the_scenario(self):
        s, _, _ = build(world(steel(basis='ex-works', rate='247000', freight='')))
        self.assertTrue(any('lower bound' in g for g in by(s, 'buy_now')[0]['evidence_gaps']))

    def test_negotiate_compares_only_offers_with_a_complete_landed_cost(self):
        s, _, _ = build(world(steel('Q-1'), steel('Q-2', '255000', sup='SUP-002')))
        (n,) = by(s, 'negotiate')
        self.assertEqual(n['lowest_complete_offer'], 'supplier_quote/Q-2')
        self.assertEqual(n['others'], [{'offer': 'supplier_quote/Q-1', 'class': 'comparable', 'landed_gap_cents_per_unit': 10_000, 'potential_difference_cents': 400_000}])
        self.assertIn('not a saving', ' '.join(n['uncertainty']))
        s1, _, _ = build(world(steel('Q-1')))
        self.assertEqual(by(s1, 'negotiate')[0]['status'], 'cannot_assess')
        s2, _, _ = build(world(steel('Q-1'), steel('Q-2', '255000', sup='SUP-002', basis='ex-works', freight='')))
        self.assertEqual(by(s2, 'negotiate')[0]['status'], 'cannot_assess')                  # the lower-priced offer is a lower bound: it is not compared

    def test_when_nothing_is_uncovered_no_scenario_exists(self):
        m = world(steel())
        m.orders(pom('PO-1', qty='40'))
        s, _, _ = build(m)
        self.assertEqual((s['status'], s['scenarios']), ('no_uncovered_demand', []))

    def test_with_no_current_rankable_quote_no_scenario_is_invented(self):
        s, _, _ = build(world(steel(valid='2026-09-01')))
        self.assertEqual((s['status'], s['scenarios']), ('no_rankable_offer', []))
        s2, _, _ = build(world())
        self.assertEqual((s2['status'], s2['scenarios']), ('no_rankable_offer', []))

    def test_a_quote_in_another_unit_gets_no_purchase_scenario(self):
        m = mkt_world()
        m.set_spec(unit_conversions=[{'material': 'MAT-STEEL', 'from_unit': 'kg', 'to_unit': 'tonne', 'factor_micro': 1000}])
        m.quote_rows(steel('Q-1', rate='265'))
        m.readings(reading('Q-1', 'grade', '300PLUS'), reading('Q-1', 'section', '250UB'), reading('Q-1', 'unit', 'kg'))
        m.demands(demand('DEM-1', 'PRJ-001', 'MAT-STEEL', '40', 'tonne', '2026-12-01'))
        s, _, _ = build(m)
        self.assertEqual(s['status'], 'no_scenario_built')
        self.assertIn('priced per kg but needed per tonne', s['scenarios_not_built'][0]['why'])

    def test_timing_is_the_earlier_of_quote_validity_and_the_latest_order_date(self):
        m = world(steel('Q-1', valid='2026-10-31'), steel('Q-2', '255000', valid='2026-12-31', lead='60', sup='SUP-002'))
        ctx = m.ctx()
        (req,) = [r for r in CP.requirements(ctx) if r['kind'] == 'demand']
        rk = CP.rank(ctx, req, 'buy_timing', 40 * M)
        t = {o['offer']['key']: SC.timing(ctx, req, o) for o in rk['offers']}
        self.assertEqual((t['Q-1']['due'], t['Q-1']['binding'], t['Q-1']['latest_order_date']), ('2026-10-31', 'quote validity', '2026-11-03'))
        self.assertEqual((t['Q-2']['due'], t['Q-2']['binding'], t['Q-2']['latest_order_date']), ('2026-09-25', 'lead time', '2026-09-25'))

    def test_the_result_is_canonical_json_and_identical_on_a_second_build(self):
        m = world(steel(), steel('Q-2', '255000', sup='SUP-002'))
        a, b = build(m)[0], build(m)[0]
        self.assertEqual(canon.canonical(a), canon.canonical(b))


if __name__ == '__main__':
    unittest.main()
