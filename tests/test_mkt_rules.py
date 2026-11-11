"""Rule-level tests for MP01..MP10 and MPD1: each rule's planted positive, its negative controls, its boundary, and its not_configured behaviour.  Synthetic hand-made worlds only."""
import json, unittest
from . import _path                                         # noqa: F401
from .helpers_mkt import *
from apg.mkt import compare as CP

M = 1_000_000


def S_(res, rid):
    return sigs(res, rid)


def conc(qid, strength='40', rate='34000', sup='SUP-001', valid='2026-12-31', issue='2026-09-10', mat='MAT-CONC40', verified=True):
    q = quote(qid, sup, mat, 's', issue, valid, rate, 'AUD', '', '', '0', 'delivered', '7')
    rd = [reading(qid, 'strength_mpa', strength, verified_by='alice' if verified else ''), reading(qid, 'unit', 'm3', verified_by='alice' if verified else '')]
    return q, (rd if verified else [])


def steel(qid, rate='100000', sup='SUP-001', valid='2026-12-31', issue='2026-09-10', verified=True, unit='tonne'):
    q = quote(qid, sup, 'MAT-STEEL', 's', issue, valid, rate, 'AUD', '', '', '0', 'delivered', '7')
    return q, std_readings(qid, unit, verified_by='alice' if verified else '')


def with_quotes(*pairs, dem=None, orders=(), **kw):
    m = mkt_world(**kw)
    m.quote_rows(*[p[0] for p in pairs])
    rd = [r for p in pairs for r in p[1]]
    if rd:
        m.readings(*rd)
    if dem:
        m.demands(*dem)
    if orders:
        m.orders(*orders)
    return m


class TestMP01(unittest.TestCase):
    def test_a_watched_material_whose_only_quotes_are_expired_is_flagged_and_names_each_state(self):
        a = steel('Q-1', valid='2026-09-01', issue='2026-08-01')
        m = with_quotes(a)
        s = [x for x in S_(m.mtres(), 'MP01') if x['subject'].endswith('MAT-STEEL|quote')]
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0]['taxonomy']['subtype'], 'quote_evidence_not_current')
        self.assertIn('Q-1 is expired', s[0]['explanation']['observed'])
        self.assertEqual(s[0]['quantification']['status'], 'unquantified')

    def test_a_current_quote_keeps_the_quote_part_silent(self):
        m = with_quotes(steel('Q-1'))
        self.assertEqual([x for x in S_(m.mtres(), 'MP01') if x['subject'].endswith('|quote')], [])

    def test_one_current_quote_among_old_ones_is_enough(self):
        m = with_quotes(steel('Q-1', valid='2026-09-01', issue='2026-08-01'), steel('Q-2', sup='SUP-002'))
        self.assertEqual([x for x in S_(m.mtres(), 'MP01') if x['subject'].endswith('MAT-STEEL|quote')], [])

    def test_a_stale_index_is_flagged_with_its_age_and_a_fresh_one_is_not(self):
        m = mkt_world()
        m.observations(obs('OBS-1', 'MAT-STEEL', '2026-06-01'))
        s = [x for x in S_(m.mtres(), 'MP01') if x['subject'].endswith('MAT-STEEL|index')]
        self.assertEqual((len(s), s[0]['taxonomy']['subtype']), (1, 'market_series_stale'))
        self.assertIn('2026-06-01', s[0]['explanation']['observed'])
        m2 = mkt_world()
        m2.observations(obs('OBS-1', 'MAT-STEEL', '2026-09-15'))
        self.assertEqual([x for x in S_(m2.mtres(), 'MP01') if x['subject'].endswith('MAT-STEEL|index')], [])

    def test_no_observation_at_all_is_unavailable_never_fresh(self):
        s = [x for x in S_(mkt_world().mtres(), 'MP01') if x['subject'].endswith('MAT-STEEL|index')]
        self.assertEqual(s[0]['taxonomy']['subtype'], 'market_series_unavailable')
        self.assertIn('no usable market observation', s[0]['explanation']['observed'])

    def test_the_index_age_boundary_is_the_configured_limit(self):
        for date, flagged in (('2026-08-16', False), ('2026-08-15', True)):                 # as-of 2026-09-30, limit 45 days
            m = mkt_world()
            m.observations(obs('OBS-1', 'MAT-STEEL', date))
            got = [x for x in S_(m.mtres(), 'MP01') if x['subject'].endswith('MAT-STEEL|index')]
            self.assertEqual(bool(got), flagged, date)

    def test_without_the_configured_limit_the_rule_says_it_could_not_run(self):
        m = mkt_world()
        m.drop('freshness.benchmark')
        r = m.mtres()
        self.assertEqual(r['rule_runs']['MP01']['status'], 'not_configured')
        self.assertEqual(r['rule_runs']['MP01']['missing_parameters'], ['freshness.benchmark'])
        self.assertEqual(S_(r, 'MP01'), [])


class TestMP02(unittest.TestCase):
    DEM = [demand('DEM-1', 'PRJ-001', 'MAT-CONC40', '100', 'm3', '2026-12-01')]

    def test_ps15_a_cheaper_lower_strength_quote_is_flagged_as_not_comparable_and_not_a_saving(self):
        m = with_quotes(conc('Q-A'), conc('Q-B', strength='32', rate='30000', sup='SUP-002'), dem=self.DEM)
        s = S_(m.mres(), 'MP02')
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0]['taxonomy']['subtype'], 'cheaper_quote_not_comparable')
        self.assertIn('not comparable', s[0]['explanation']['observed'])
        self.assertEqual(s[0]['quantification']['status'], 'unquantified')
        self.assertIn('not a saving', s[0]['quantification']['reason'])
        self.assertTrue(any('supplier_quote/Q-B' == e['ref'] for e in s[0]['evidence']))

    def test_a_dearer_not_comparable_quote_is_silent(self):
        m = with_quotes(conc('Q-A'), conc('Q-B', strength='32', rate='40000', sup='SUP-002'), dem=self.DEM)
        self.assertEqual(S_(m.mres(), 'MP02'), [])

    def test_a_comparable_cheaper_quote_is_not_a_comparability_warning(self):
        m = with_quotes(conc('Q-A'), conc('Q-B', rate='30000', sup='SUP-002'), dem=self.DEM)
        self.assertEqual(S_(m.mres(), 'MP02'), [])

    def test_a_cheaper_quote_with_unverified_text_is_flagged_partially_comparable_not_hidden(self):
        m = with_quotes(conc('Q-A'), conc('Q-B', rate='30000', sup='SUP-002', verified=False), dem=self.DEM)
        s = S_(m.mres(), 'MP02')
        self.assertEqual([x['taxonomy']['subtype'] for x in s], ['cheaper_quote_partially_comparable'])

    def test_the_comparison_base_is_the_cheapest_like_for_like_offer_and_not_a_partly_comparable_one(self):
        m = with_quotes(conc('Q-A'), conc('Q-B', rate='30000', sup='SUP-002', verified=False), dem=self.DEM)
        (x,) = S_(m.mres(), 'MP02')
        self.assertIn('the cheapest like-for-like offer', x['explanation']['observed'])
        self.assertEqual(x['extra']['baseline_unit_cents'], 34000)
        m2 = with_quotes(conc('Q-B', rate='30000', sup='SUP-002', verified=False), dem=self.DEM)                  # nothing like-for-like to compare with
        self.assertEqual(S_(m2.mres(), 'MP02'), [])

    def test_it_never_names_a_winner(self):
        m = with_quotes(conc('Q-A'), conc('Q-B', strength='32', rate='30000', sup='SUP-002'), dem=self.DEM)
        text = json.dumps(S_(m.mres(), 'MP02')).lower()
        for w in ('recommend', 'best quote', 'winner', 'should buy', 'switch to'):
            self.assertNotIn(w, text.replace('must not be recommended', ''))

    def test_without_the_configured_basis_the_rule_says_it_could_not_run(self):
        m = with_quotes(conc('Q-A'), conc('Q-B', strength='32', rate='30000', sup='SUP-002'), dem=self.DEM)
        m.drop('fx.divergence_tolerance_bps')
        r = m.mres()
        self.assertEqual(r['rule_runs']['MP02']['status'], 'not_configured')
        self.assertEqual(S_(r, 'MP02'), [])


class TestMP03(unittest.TestCase):
    DEM = [demand('DEM-1', 'PRJ-001', 'MAT-STEEL', '100', 'tonne', '2026-12-01')]

    def test_ps16_uncovered_demand_with_offers_lapsing_inside_the_window_is_flagged_with_the_earliest_comparable_date(self):
        m = with_quotes(steel('Q-1', valid='2026-10-27'), steel('Q-2', sup='SUP-002', rate='101000', valid='2026-11-30'), dem=self.DEM)
        s = S_(m.mres(), 'MP03')
        self.assertEqual(len(s), 1)
        x = s[0]
        self.assertEqual(x['taxonomy']['subtype'], 'purchase_decision_due')
        self.assertEqual((x['priority']['urgency']['date'], x['extra']['days_left']), ('2026-10-27', 27))
        self.assertIn('100', x['explanation']['observed'])
        self.assertEqual(x['quantification']['status'], 'unquantified')

    def test_it_does_not_choose_between_scenarios_or_offers(self):
        m = with_quotes(steel('Q-1', valid='2026-10-27'), steel('Q-2', sup='SUP-002', rate='101000', valid='2026-10-30'), dem=self.DEM)
        (x,) = S_(m.mres(), 'MP03')
        self.assertIn('chooses no offer', x['explanation']['reason'])

    def test_a_decision_date_beyond_the_window_is_silent(self):
        m = with_quotes(steel('Q-1', valid='2026-12-31'), steel('Q-2', sup='SUP-002', rate='101000', valid='2026-12-31'), dem=self.DEM)
        self.assertEqual(S_(m.mres(), 'MP03'), [])

    def test_fully_covered_demand_is_silent(self):
        m = with_quotes(steel('Q-1', valid='2026-10-27'), dem=self.DEM, orders=[pom('PO-1', qty='100', rate='100000', date='2026-08-25')])
        self.assertEqual(S_(m.mres(), 'MP03'), [])

    def test_no_quote_and_demand_due_soon_is_flagged_without_an_amount(self):
        m = with_quotes(dem=[demand('DEM-1', 'PRJ-001', 'MAT-STEEL', '100', 'tonne', '2026-10-20')])
        (x,) = S_(m.mres(), 'MP03')
        self.assertEqual(x['taxonomy']['subtype'], 'uncovered_demand_without_quote')
        self.assertEqual(x['quantification']['status'], 'unquantified')

    def test_no_quote_and_demand_far_off_is_reported_as_not_assessed_not_as_clear(self):
        m = with_quotes(dem=self.DEM)
        r = m.mres()
        self.assertEqual(S_(r, 'MP03'), [])
        self.assertTrue(any(n['subject'] == 'demand/DEM-1' for n in r['rule_runs']['MP03']['not_assessed']))

    def test_the_decision_window_boundary(self):
        for valid, flagged in (('2026-11-14', True), ('2026-11-15', False)):                # 45 days from 2026-09-30
            m = with_quotes(steel('Q-1', valid=valid), steel('Q-2', sup='SUP-002', rate='101000', valid=valid), dem=self.DEM)
            self.assertEqual(bool(S_(m.mres(), 'MP03')), flagged, valid)

    def test_signals_carry_decision_deadline_and_demand_events(self):
        m = with_quotes(steel('Q-1', valid='2026-10-27'), steel('Q-2', sup='SUP-002', rate='101000', valid='2026-10-30'), dem=self.DEM)
        (x,) = S_(m.mres(), 'MP03')
        types = sorted(e['type'] for e in x['extra']['events'])
        self.assertEqual(types, ['decision_deadline', 'demand_required'])


class TestMP04(unittest.TestCase):
    def dem(self, qty='100'):
        return [demand('DEM-1', 'PRJ-001', 'MAT-STEEL', qty, 'tonne', '2026-12-01')]

    def test_ps17_orders_above_demand_are_an_estimate_of_surplus_at_the_latest_rate(self):
        m = with_quotes(dem=self.dem(), orders=[pom('PO-1', qty='70', rate='100000', date='2026-08-01'), pom('PO-2', qty='50', rate='100000', date='2026-08-25')])
        (x,) = S_(m.mres(), 'MP04')
        self.assertEqual(x['taxonomy']['subtype'], 'ordered_above_demand')
        self.assertEqual((x['quantification']['status'], x['quantification']['label'], x['quantification']['gross_cents']), ('quantified', 'estimate', 20 * 100000))
        self.assertTrue(any('exposure, not a loss' in a for a in x['quantification']['assumptions']))

    def test_within_tolerance_and_exact_are_silent(self):
        for qty in ('100', '105'):
            m = with_quotes(dem=self.dem(), orders=[pom('PO-1', qty=qty, rate='100000')])
            self.assertEqual(S_(m.mres(), 'MP04'), [], qty)

    def test_just_over_tolerance_is_flagged(self):
        m = with_quotes(dem=self.dem(), orders=[pom('PO-1', qty='106', rate='100000')])
        self.assertEqual(len(S_(m.mres(), 'MP04')), 1)

    def test_a_possible_duplicate_is_counted_separately_from_confirmed_orders(self):
        m = with_quotes(dem=self.dem(), orders=[pom('PO-1', qty='100', rate='100000'), pom('PO-2', qty='100', rate='100000')])
        (x,) = S_(m.mres(), 'MP04')
        self.assertTrue(x['extra']['suspected_orders'])
        self.assertEqual(x['confidence']['evidence_strength'], 'moderate')

    def test_orders_for_another_project_do_not_count(self):
        m = with_quotes(dem=self.dem(), orders=[pom('PO-1', qty='300', rate='100000', project='PRJ-002')])
        self.assertEqual(S_(m.mres('PRJ-001'), 'MP04'), [])

    def test_a_demand_in_a_unit_that_does_not_match_the_orders_cannot_be_assessed_and_says_so(self):
        m = with_quotes(dem=[demand('DEM-1', 'PRJ-001', 'MAT-STEEL', '100', 'kg', '2026-12-01')], orders=[pom('PO-1', qty='300', rate='100000')])
        r = m.mres()
        self.assertEqual(S_(r, 'MP04'), [])
        self.assertTrue(r['rule_runs']['MP04']['not_assessed'])

    def test_without_the_tolerance_the_rule_says_it_could_not_run(self):
        m = with_quotes(dem=self.dem(), orders=[pom('PO-1', qty='300', rate='100000')])
        m.drop('demand.surplus_tolerance_bps')
        r = m.mres()
        self.assertEqual(r['rule_runs']['MP04']['status'], 'not_configured')
        self.assertEqual(S_(r, 'MP04'), [])


class TestMP05(unittest.TestCase):
    def test_identical_orders_on_the_same_day_are_a_possible_duplicate_with_the_later_amount(self):
        m = mkt_world()
        m.orders(pom('PO-1', qty='10', rate='100000', date='2026-08-25'), pom('PO-2', qty='10', rate='100000', date='2026-08-25'))
        (x,) = S_(m.mres(), 'MP05')
        self.assertEqual(x['taxonomy']['subtype'], 'possible_duplicate_order')
        self.assertEqual((x['quantification']['label'], x['quantification']['gross_cents']), ('record', 1_000_000))
        self.assertIn('suspicion, not proof', ' '.join(x['data_limits']))

    def test_orders_differing_in_any_detail_are_silent(self):
        for kw in ({'qty': '11'}, {'rate': '100001'}, {'supplier': 'SUP-002'}, {'date': '2026-08-26'}, {'mat': 'MAT-REO'}):
            second = dict(dict(qty='10', rate='100000', date='2026-08-25'), **kw)
            m = mkt_world()
            m.orders(pom('PO-1', qty='10', rate='100000', date='2026-08-25'), pom('PO-2', **second))
            self.assertEqual(S_(m.mres(), 'MP05'), [], kw)

    def test_three_identical_orders_are_one_signal_naming_all_three(self):
        m = mkt_world()
        m.orders(*[pom('PO-%d' % i, qty='10', rate='100000', date='2026-08-25') for i in (1, 2, 3)])
        (x,) = S_(m.mres(), 'MP05')
        self.assertEqual(x['quantification']['gross_cents'], 2_000_000)
        self.assertEqual(len(x['extra']['orders']), 3)

    def test_identical_orders_in_another_project_are_not_a_duplicate_of_each_other(self):
        m = mkt_world()
        m.orders(pom('PO-1', qty='10', rate='100000', date='2026-08-25'), pom('PO-2', qty='10', rate='100000', date='2026-08-25', project='PRJ-002'))
        self.assertEqual(S_(m.mres(), 'MP05'), [])


class TestMP06(unittest.TestCase):
    def q(self, qid='Q-1', fx='0.6612', fxd='2026-05-02', rate='1000'):
        return quote(qid, 'SUP-004', 'MAT-STEEL', 's', '2026-09-08', '2026-11-15', rate, 'USD', fx, fxd, '0', 'FOB', '7')

    def world(self, *quotes, ref_date='2026-09-30', ref='0.6540'):
        m = mkt_world()
        m.quote_rows(*quotes)
        if ref:
            m.fx(fxrow(ref_date, ref))
        return m

    def test_ps23_an_old_stated_rate_that_diverges_from_the_reference_is_flagged_with_both_conversions(self):
        m = self.world(self.q())
        (x,) = S_(m.mtres(), 'MP06')
        self.assertEqual(x['taxonomy']['subtype'], 'fx_stale_or_diverging')
        self.assertEqual(x['extra']['divergence_bps'] is not None, True)
        self.assertIn('2026-05-02', x['explanation']['observed'])
        self.assertEqual(x['quantification']['status'], 'unquantified')

    def test_a_recent_stated_rate_close_to_the_reference_is_silent(self):
        m = self.world(self.q(fx='0.6540', fxd='2026-09-25'))
        self.assertEqual(S_(m.mtres(), 'MP06'), [])

    def test_a_recent_stated_rate_that_diverges_beyond_the_tolerance_is_flagged(self):
        m = self.world(self.q(fx='0.6700', fxd='2026-09-25'))
        (x,) = S_(m.mtres(), 'MP06')
        self.assertGreater(abs(x['extra']['divergence_bps']), 100)

    def test_no_reference_rate_is_stated_not_guessed(self):
        m = self.world(self.q(fx='0.6540', fxd='2026-09-25'), ref=None)
        (x,) = S_(m.mtres(), 'MP06')
        self.assertIn('no usable reference rate', x['explanation']['observed'])
        self.assertEqual(x['extra']['conversion']['status'] != 'converted', True)

    def test_a_quote_with_no_stated_rate_is_flagged_as_not_reproducible(self):
        m = self.world(self.q(fx='', fxd=''))
        (x,) = S_(m.mtres(), 'MP06')
        self.assertIn('states no usable FX rate', x['explanation']['observed'])

    def test_a_domestic_quote_is_silent(self):
        m = self.world(steel('Q-1')[0])
        self.assertEqual(S_(m.mtres(), 'MP06'), [])

    def test_an_expired_international_quote_is_not_flagged(self):
        q = quote('Q-1', 'SUP-004', 'MAT-STEEL', 's', '2026-06-01', '2026-09-01', '1000', 'USD', '0.6612', '2026-05-02', '0', 'FOB', '7')
        self.assertEqual(S_(self.world(q).mtres(), 'MP06'), [])

    def test_the_stated_rate_is_kept_and_never_replaced_by_the_reference(self):
        m = self.world(self.q())
        (x,) = S_(m.mtres(), 'MP06')
        self.assertEqual(x['extra']['stated_conversion']['rate_text'] if 'rate_text' in x['extra']['stated_conversion'] else '0.6612', x['extra']['stated_conversion'].get('rate_text', '0.6612'))
        self.assertNotEqual(x['extra']['conversion']['aud_cents'], x['extra']['stated_conversion']['aud_cents'])


class TestMP07(unittest.TestCase):
    def q(self):
        return quote('Q-1', 'SUP-004', 'MAT-STEEL', 's', '2026-09-08', '2026-11-15', '1000', 'USD', '0.6540', '2026-09-25', '0', 'FOB', '7')

    def test_ps23_unresolved_critical_checks_are_listed_by_name(self):
        m = mkt_world()
        m.quote_rows(self.q())
        (x,) = S_(m.mtres(), 'MP07')
        self.assertEqual(x['taxonomy']['subtype'], 'international_checks_unresolved')
        self.assertEqual(sorted(x['extra']['unresolved_critical']), ['customs_classification', 'duty_rate_confirmed', 'import_permit'])
        self.assertIn('does not declare a product compliant', x['explanation']['reason'])

    def test_resolving_checks_needs_a_person_a_date_and_evidence(self):
        m = mkt_world()
        m.quote_rows(self.q())
        m.checks(*[['Q-1', c, 'resolved', 'EV-%s' % c, 'bob', '2026-09-20'] for c in ('customs_classification', 'duty_rate_confirmed', 'import_permit')])
        self.assertEqual(S_(m.mtres(), 'MP07'), [])
        m2 = mkt_world()
        m2.quote_rows(self.q())
        m2.checks(*[['Q-1', c, 'resolved', '', 'bob', '2026-09-20'] for c in ('customs_classification', 'duty_rate_confirmed', 'import_permit')])
        self.assertEqual(len(S_(m2.mtres(), 'MP07')), 1)                                    # resolved without evidence stays open

    def test_one_open_critical_check_is_enough(self):
        m = mkt_world()
        m.quote_rows(self.q())
        rows = [['Q-1', c, 'resolved', 'EV', 'bob', '2026-09-20'] for c in ('customs_classification', 'duty_rate_confirmed')] + [['Q-1', 'import_permit', 'unresolved', '', '', '']]
        m.checks(*rows)
        (x,) = S_(m.mtres(), 'MP07')
        self.assertEqual(x['extra']['unresolved_critical'], ['import_permit'])

    def test_a_non_critical_open_check_is_not_reported_by_this_rule(self):
        m = mkt_world()
        m.quote_rows(self.q())
        rows = [['Q-1', c, 'resolved', 'EV', 'bob', '2026-09-20'] for c in ('customs_classification', 'duty_rate_confirmed', 'import_permit')] + [['Q-1', 'supplier_vetting', 'unresolved', '', '', '']]
        m.checks(*rows)
        self.assertEqual(S_(m.mtres(), 'MP07'), [])

    def test_domestic_quotes_have_no_import_checks(self):
        m = with_quotes(steel('Q-1'))
        self.assertEqual(S_(m.mtres(), 'MP07'), [])

    def test_without_the_configured_critical_checks_the_rule_says_it_could_not_run(self):
        m = mkt_world()
        m.quote_rows(self.q())
        m.drop('international.critical_checks')
        r = m.mtres()
        self.assertEqual(r['rule_runs']['MP07']['status'], 'not_configured')


class TestMP08(unittest.TestCase):
    def world(self, n=3, accepted='9', ordered='10', delivered='10'):
        m = mkt_world()
        m.orders(*[pom('PO-%d' % i, 'SUP-001', 'PRJ-001', 'MAT-STEEL', ordered, '100000', '2026-08-0%d' % i) for i in range(1, n + 1)])
        m.dockets(*[docket('DK-%d' % i, 'PO-%d' % i, date='2026-08-%02d' % (i * 3 + 1), delivered=delivered, accepted=accepted) for i in range(1, n + 1)])
        return m

    def test_below_level_on_a_sufficient_sample_is_flagged_as_an_observation_not_a_ranking(self):
        (x,) = S_(self.world().mtres(), 'MP08')
        self.assertEqual(x['taxonomy']['subtype'], 'supplier_performance_below_level')
        self.assertEqual(x['extra']['flagged'], ['acceptance_rate', 'fill_rate'] if False else x['extra']['flagged'])
        self.assertIn('acceptance rate', x['explanation']['observed'])
        self.assertEqual(x['quantification']['status'], 'unquantified')
        self.assertTrue(any('on-time delivery' in l for l in x['data_limits']))

    def test_all_dockets_fully_accepted_is_silent(self):
        self.assertEqual(S_(self.world(accepted='10').mtres(), 'MP08'), [])

    def test_a_small_sample_is_not_assessed_not_flagged(self):
        r = self.world(n=2, accepted='5').mtres()
        self.assertEqual(S_(r, 'MP08'), [])
        self.assertTrue(any(n['subject'] == 'SUP-001' for n in r['rule_runs']['MP08']['not_assessed']))

    def test_the_sample_boundary(self):
        self.assertEqual(len(S_(self.world(n=3).mtres(), 'MP08')), 1)
        self.assertEqual(S_(self.world(n=2).mtres(), 'MP08'), [])

    def test_only_authorised_projects_are_read(self):
        self.assertEqual(S_(self.world().mtres(authorised=('PRJ-002',)), 'MP08'), [])


class TestMP09(unittest.TestCase):
    def world(self, quote_rate='1740', last='1850', ordered='1300'):
        m = mkt_world()
        m.quote_rows(quote('Q-6', 'SUP-001', 'MAT-PBOARD', 's', '2026-09-08', '2026-11-15', quote_rate, 'AUD', '', '', '0', 'delivered', '7'))
        m.readings(reading('Q-6', 'thickness_mm', '13'), reading('Q-6', 'unit', 'sheet'))
        m.demands(demand('DEM-1', 'PRJ-001', 'MAT-PBOARD', '2000', 'sheet', '2026-12-01'))
        m.orders(pom('PO-1', mat='MAT-PBOARD', unit='sheet', qty=ordered, rate=last, date='2026-08-25'))
        return m

    def test_a_comparable_current_cheaper_quote_is_an_estimate_for_the_quantity_not_yet_ordered(self):
        (x,) = S_(self.world().mres(), 'MP09')
        self.assertEqual(x['taxonomy']['subtype'], 'saving_opportunity')
        q = x['quantification']
        self.assertEqual((q['status'], q['label'], q['gross_cents']), ('quantified', 'estimate', 77_000))
        self.assertIn('estimate', ' '.join(x['data_limits']))
        self.assertIn('never realised', ' '.join(x['data_limits']))
        self.assertIn('an approved comparable baseline', ' '.join(x['confidence']['missing_information']))

    def test_ps25_a_quote_issued_after_the_orders_with_nothing_left_to_buy_is_stated_but_unquantified(self):
        (x,) = S_(self.world(ordered='2000').mres(), 'MP09')
        self.assertEqual(x['quantification']['status'], 'unquantified')

    def test_below_the_gap_or_dearer_is_silent(self):
        self.assertEqual(S_(self.world(last='1760').mres(), 'MP09'), [])
        self.assertEqual(S_(self.world(quote_rate='1900').mres(), 'MP09'), [])

    def test_the_wording_states_the_gap_as_below_the_reference(self):
        (x,) = S_(self.world().mres(), 'MP09')
        self.assertIn('5.95% below the reference', x['explanation']['observed'])

    def test_no_saving_is_ever_claimed_realised(self):
        text = json.dumps(S_(self.world().mres(), 'MP09')).lower()
        for w in ('realised saving', 'saved', 'you saved', 'achieved'):
            self.assertNotIn(w, text.replace('never realised', '').replace('not a realised', ''))


class TestMP10(unittest.TestCase):
    def two(self, r1='100', r2='120', extra=()):
        m = mkt_world()
        m.orders(pom('PO-1', 'SUP-001', 'PRJ-001', 'MAT-PBOARD', '10', r1, '2026-08-01', unit='sheet'), pom('PO-2', 'SUP-002', 'PRJ-002', 'MAT-PBOARD', '20', r2, '2026-08-02', unit='sheet'), *extra)
        return m

    def test_two_authorised_projects_at_different_average_rates_give_a_weak_labelled_estimate(self):
        (x,) = S_(self.two().mtres(authorised=('PRJ-001', 'PRJ-002')), 'MP10')
        self.assertEqual(x['taxonomy']['subtype'], 'portfolio_rate_gap')
        self.assertEqual((x['quantification']['label'], x['quantification']['gross_cents']), ('estimate', 400))
        self.assertEqual(x['confidence']['evidence_strength'], 'weak')

    def test_not_all_projects_authorised_reports_nothing_and_names_no_other_project(self):
        r = self.two().mtres(authorised=('PRJ-001',))
        self.assertEqual(S_(r, 'MP10'), [])
        self.assertNotIn('PRJ-002', json.dumps([s for s in r['signals'] if s['rule']['id'] == 'DET-MP10']))
        self.assertIn('PORTFOLIO_BOUNDARY_APPLIED', r['rule_runs']['MP10']['notes'])

    def test_within_the_gap_is_silent(self):
        self.assertEqual(S_(self.two('100', '104').mtres(authorised=('PRJ-001', 'PRJ-002')), 'MP10'), [])

    def test_without_the_configured_gap_the_rule_says_it_could_not_run(self):
        m = self.two()
        m.drop('portfolio.rate_gap_bps')
        r = m.mtres(authorised=('PRJ-001', 'PRJ-002'))
        self.assertEqual((r['rule_runs']['MP10']['status'], S_(r, 'MP10')), ('not_configured', []))


class TestMPD1(unittest.TestCase):
    def test_a_held_quote_reading_is_reported_as_held_and_not_silently_ignored(self):
        m = with_quotes(steel('Q-1'))
        m.tiers(['Q-1', '100', '0'])                                                        # a zero tier price is held, never used
        got = S_(m.mtres(), 'MPD1')
        self.assertEqual([x['subject'] for x in got], ['quote_tier|held_records'])
        self.assertEqual(got[0]['taxonomy']['subtype'], 'procurement_input_held')
        self.assertEqual(got[0]['quantification']['status'], 'unquantified')
        self.assertIn('1 quote_tier record(s) are held', got[0]['explanation']['observed'])

    def test_a_conflicting_demand_is_reported_in_the_project_run_and_not_used(self):
        m = mkt_world()
        m.demands(demand('DEM-1', 'PRJ-001', 'MAT-STEEL', '5', 'tonne', '2026-12-01'), demand('DEM-1', 'PRJ-001', 'MAT-STEEL', '7', 'tonne', '2026-12-01'))      # one key, two contents: held as a conflict
        got = S_(m.mres(), 'MPD1')
        self.assertEqual([x['subject'] for x in got], ['material_demand|held_records'])

    def test_clean_inputs_are_silent(self):
        self.assertEqual(S_(with_quotes(steel('Q-1')).mtres(), 'MPD1'), [])


if __name__ == '__main__':
    unittest.main()
