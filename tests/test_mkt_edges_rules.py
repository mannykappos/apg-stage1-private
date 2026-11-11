"""Edge-case tests written to kill mutation survivors in the procurement rules (MP01..MPD1), the per-run analysis object, the run/replay checks and the event records.  Each case sits exactly on a
boundary, or has exactly one of two conditions true, so that no single comparison, `and`/`or` or guard can be flipped or dropped without a failure here.  Synthetic hand-made worlds only; the
demonstration as-of day is 2026-09-30."""
import copy, unittest
from . import _path                                         # noqa: F401
from .helpers_mkt import *
from .test_mkt_rules import conc, steel, with_quotes, S_
from apg import canon, repro
from apg.mkt import common as C, demo_mkt as DM, detect as MD, events as EV, fx as FX, rules as R

STEEL_DEM = [demand('DEM-1', 'PRJ-001', 'MAT-STEEL', '100', 'tonne', '2026-12-01')]
CONC_DEM = [demand('DEM-1', 'PRJ-001', 'MAT-CONC40', '100', 'm3', '2026-12-01')]
SRC = [('supplier_quote/Q-1', 1)]


# ------------------------------------------------------------------------------------------------------------------------------------ events
def raw_event(**over):
    """A well-formed event dict with its identity recomputed, so that a test breaks exactly one property."""
    e = EV.make('quote_issued', 'supplier_quote/Q-1', '2026-09-01T00:00:00Z', '2026-09-01', SRC)
    e.update(over)
    e['event_id'] = 'EV-' + canon.digest({k: v for k, v in e.items() if k != 'event_id'})[:20]
    return e


class TestEventRecords(unittest.TestCase):
    def test_a_one_day_period_is_valid_and_a_period_ending_before_it_starts_is_not(self):
        e = EV.make('quote_expires', 'supplier_quote/Q-1', '2026-09-01T00:00:00Z', '2026-09-15', SRC, effective_to='2026-09-15')
        self.assertTrue(EV.validate(e))                                                      # effective_to equal to effective_from: the fact applies on that one day
        self.assertEqual((e['effective_from'], e['effective_to']), ('2026-09-15', '2026-09-15'))
        with self.assertRaisesRegex(EV.EventError, 'effective period'):
            EV.make('quote_expires', 'supplier_quote/Q-1', '2026-09-01T00:00:00Z', '2026-09-15', SRC, effective_to='2026-09-14')

    def test_sources_are_listed_in_reference_then_revision_order_with_an_unknown_revision_first(self):
        e = EV.make('quote_issued', 'supplier_quote/Q-1', '2026-09-01T00:00:00Z', '2026-09-01',
                    [('supplier_quote/Q-2', 1), ('supplier_quote/Q-1', 3), ('supplier_quote/Q-1', 1), ('supplier_quote/Q-1', None)])
        self.assertEqual([(s['ref'], s['revision']) for s in e['sources']],
                         [('supplier_quote/Q-1', None), ('supplier_quote/Q-1', 1), ('supplier_quote/Q-1', 3), ('supplier_quote/Q-2', 1)])

    def test_the_detail_given_is_kept_and_missing_detail_is_an_empty_record(self):
        e = EV.make('quote_issued', 'supplier_quote/Q-1', '2026-09-01T00:00:00Z', '2026-09-01', SRC, detail={'class': 'comparable'})
        self.assertEqual(e['detail'], {'class': 'comparable'})
        self.assertEqual(EV.make('quote_issued', 'supplier_quote/Q-1', '2026-09-01T00:00:00Z', '2026-09-01', SRC)['detail'], {})
        self.assertEqual(EV.make('quote_issued', 'supplier_quote/Q-1', '2026-09-01T00:00:00Z', '2026-09-01', SRC, detail={})['detail'], {})

    def test_an_event_of_another_version_or_not_an_event_at_all_is_refused_as_an_event_error(self):
        self.assertTrue(EV.validate(raw_event()))
        with self.assertRaisesRegex(EV.EventError, 'event version'):
            EV.validate(raw_event(event_version='apg-event-0'))                           # identity recomputed: only the version is wrong
        for bad in ('not an event', None, 7, ['apg-event-1']):
            with self.assertRaisesRegex(EV.EventError, 'event version'):
                EV.validate(bad)
        with self.assertRaisesRegex(EV.EventError, 'event version'):
            EV.validate({})                                                                  # a dict with no version at all


# ------------------------------------------------------------------------------------------------------------------------------------ analysis
class TestAnalysisBlockAndDuplicates(unittest.TestCase):
    def test_duplicates_are_limited_to_the_authorised_projects_and_unlimited_when_none_are_named(self):
        m = mkt_world()
        m.orders(pom('PO-1', qty='10', rate='100000', date='2026-08-25'), pom('PO-2', qty='10', rate='100000', date='2026-08-25'),
                 pom('PO-3', qty='10', rate='100000', date='2026-08-25', project='PRJ-002'), pom('PO-4', qty='10', rate='100000', date='2026-08-25', project='PRJ-002'))
        self.assertEqual(sorted(g['project'] for g in m.analysis(authorised=['PRJ-001']).duplicates()), ['PRJ-001'])
        self.assertEqual(sorted(g['project'] for g in m.analysis(authorised=['PRJ-002']).duplicates()), ['PRJ-002'])
        self.assertEqual(m.analysis(authorised=[]).duplicates(), [])
        self.assertEqual(sorted(g['project'] for g in m.analysis(authorised=['PRJ-001', 'PRJ-002']).duplicates()), ['PRJ-001', 'PRJ-002'])
        self.assertEqual(sorted(g['project'] for g in m.analysis(project='PRJ-001').duplicates()), ['PRJ-001'])
        a = m.analysis()                                                                     # no project and no authorised list: nothing is filtered out
        self.assertIsNone(a.authorised)
        self.assertEqual(sorted(g['project'] for g in a.duplicates()), ['PRJ-001', 'PRJ-002'])

    def test_the_stored_requirement_drops_only_its_sources(self):
        m = with_quotes(steel('Q-1'), dem=STEEL_DEM)
        a = m.analysis('PRJ-001')
        req = a.demands()[0]
        stored = a.block()['requirements'][req['id']]['requirement']
        self.assertNotIn('sources', stored)
        self.assertEqual(stored, {k: v for k, v in req.items() if k != 'sources'})
        self.assertEqual((stored['id'], stored['material'], stored['project'], stored['qty_micro']), ('demand/DEM-1', 'MAT-STEEL', 'PRJ-001', 100_000_000))

    def test_the_stored_ranking_is_priced_for_the_quantity_not_yet_covered(self):
        m = with_quotes(steel('Q-1', valid='2026-12-27'), dem=STEEL_DEM, orders=[pom('PO-1', qty='30', rate='100000', date='2026-08-25')])
        m.tiers(['Q-1', '50', '90000'])                                                      # the tier applies from 50 tonnes; 70 tonnes are uncovered, 30 are ordered
        a = m.analysis('PRJ-001')
        ent = a.block()['requirements']['demand/DEM-1']
        self.assertEqual(ent['coverage']['uncovered_micro'], 70_000_000)
        self.assertEqual([r['unit_cents'] for r in ent['ranking']['ranking']], [90000])
        self.assertEqual([r['unit_cents'] for r in a.ranking(a.demands()[0], 'quote_ranking', None)['ranking']], [100000])      # the same offer priced without a quantity
        m2 = with_quotes(steel('Q-1', valid='2026-12-27'), dem=STEEL_DEM, orders=[pom('PO-1', qty='100', rate='100000', date='2026-08-25')])
        m2.tiers(['Q-1', '50', '90000'])                                                     # nothing uncovered: no quantity, the base rate
        self.assertEqual([r['unit_cents'] for r in m2.analysis('PRJ-001').block()['requirements']['demand/DEM-1']['ranking']['ranking']], [100000])


# ------------------------------------------------------------------------------------------------------------------------------------ the run record
def planted_run():
    m = with_quotes(steel('Q-1', valid='2026-10-27'), dem=STEEL_DEM)
    return m, m.mdetect()


class Tampered:
    """A view of a scoped store whose stored run carries altered parameters (the store itself is append-only)."""
    def __init__(self, base, run_key, change):
        self.base, self.run_key, self.change = base, run_key, change

    def __getattr__(self, name):
        return getattr(self.base, name)

    def get(self, kind, key, *rest):
        rec = self.base.get(kind, key, *rest)
        if kind == repro.KIND and key == self.run_key and rec is not None:
            payload = copy.deepcopy(rec.payload)
            self.change(payload)
            return type('Rec', (), {'payload': payload, 'revision': rec.revision})()
        return rec


class TestRunRecordChecks(unittest.TestCase):
    def pins_consistent(self, change):
        m, rec = planted_run()
        return MD.check_record(Tampered(m.s, rec['run_key'], change), m.mreg, rec['run_key'])['pins_consistent']

    def test_the_claimed_pins_must_match_the_pinned_inputs_exactly(self):
        self.assertTrue(self.pins_consistent(lambda p: None))
        self.assertTrue(self.pins_consistent(lambda p: p['params'].pop('pins')))              # a run that claims no pins has nothing to contradict
        first = lambda p: sorted(p['params']['pins'])[0]

        def moved(p):
            p['params']['pins'][first(p)] += 7                                                # a claimed revision that is not the pinned one
        self.assertFalse(self.pins_consistent(moved))

        def unknown(p):
            p['params']['pins']['zzz/yyy'] = 1                                                # a claimed pin on a record that is not an input
        self.assertFalse(self.pins_consistent(unknown))

        def unknown_none(p):
            p['params']['pins']['zzz/yyy'] = None                                             # absent from the inputs: a missing value must not read as a match
        self.assertFalse(self.pins_consistent(unknown_none))

        def fewer(p):
            del p['params']['pins'][first(p)]                                                 # fewer claims than inputs: what is claimed still matches
        self.assertTrue(self.pins_consistent(fewer))

    def test_a_result_without_its_analyses_block_or_without_the_not_assessed_list_is_invalid(self):
        m, rec = planted_run()
        res = rec['result']
        self.assertTrue(MD.validate_result(res))
        no_block = copy.deepcopy(res)
        del no_block['analyses']
        with self.assertRaisesRegex(ValueError, 'analyses block'):
            MD.validate_result(no_block)
        no_list = copy.deepcopy(res)
        del no_list['analyses']['not_assessed']
        with self.assertRaisesRegex(ValueError, 'analyses block'):
            MD.validate_result(no_list)


class TestRunFormula(unittest.TestCase):
    def run_rules(self, m, rules, project='PRJ-001'):
        refs, params = MD.G.gather_project(m.s, project, AS_OF, m.policy['version'], m.dp['version'], m.mp['version'], m.sp['version'])
        return MD._run(repro._load(m.s, refs), params, rules, {'level': 'project', 'project': project})

    def test_a_rule_that_returns_a_malformed_run_record_stops_the_run(self):
        m = mkt_world()

        def rule_with(**over):
            def fn(A, F, mp, as_of, project):
                run = C.new_run('MP05')
                run.update(over)
                return [], run
            return fn
        ok = self.run_rules(m, [('MP05', rule_with())])
        self.assertEqual(ok['rule_runs']['MP05']['status'], 'evaluated')
        for over, what in (({'status': 'sleeping'}, 'an unknown status'), ({'rule': 'MP99'}, 'a record naming another rule'), ({'status': 'sleeping', 'rule': 'MP99'}, 'both')):
            with self.assertRaisesRegex(ValueError, 'rule run record is malformed: MP05', msg=what):
                self.run_rules(m, [('MP05', rule_with(**over))])

    def test_two_signals_with_one_identity_stop_the_run(self):
        m = mkt_world()
        m.orders(pom('PO-1', qty='10', rate='100000', date='2026-08-25'), pom('PO-2', qty='10', rate='100000', date='2026-08-25'))
        one = self.run_rules(m, [('MP05', R.mp05_duplicate_order)])
        self.assertEqual(one['counts']['signals'], 1)
        with self.assertRaisesRegex(ValueError, 'two signals share one identity'):
            self.run_rules(m, [('MP05', R.mp05_duplicate_order), ('MP05', R.mp05_duplicate_order)])

    def test_the_policy_blocks_report_the_version_pinned_and_whether_it_is_approved(self):
        for approved in (True, False):
            m = mkt_world(approved=approved)
            res = m.mres()
            self.assertEqual(res['det_policy'], {'version': m.dp['version'], 'approved': approved})
            self.assertEqual(res['mkt_policy'], {'version': m.mp['version'], 'approved': approved})
            self.assertEqual(res['mkt_spec'], {'version': m.sp['version'], 'approved': approved})
            self.assertEqual(res['fin_policy'], {'version': m.policy['version'], 'approved': bool(m.policy['approvals'])})
            self.assertEqual(res['fin_policy']['version'], 'SYN-FIN-POL-1')


# ------------------------------------------------------------------------------------------------------------------------------------ MP01
class TestMP01Wording(unittest.TestCase):
    def test_the_stale_index_observation_is_described_with_its_kind_its_source_and_its_geography(self):
        m = mkt_world()
        m.observations(obs('OBS-1', 'MAT-STEEL', '2026-06-01'))
        (x,) = [s for s in S_(m.mtres(), 'MP01') if s['subject'].endswith('MAT-STEEL|index')]
        self.assertEqual(x['explanation']['observed'], 'the latest index observation for MAT-STEEL is dated 2026-06-01, 121 days before 2026-09-30 (SYNTHETIC-INDEX, AU-national)')


# ------------------------------------------------------------------------------------------------------------------------------------ MP02
class TestMP02Edges(unittest.TestCase):
    def cheap(self, qid='Q-B', rate='30000', basis='delivered', freight='0', strength='32', verified=True, spec='s'):
        q = quote(qid, 'SUP-002', 'MAT-CONC40', spec, '2026-09-10', '2026-12-31', rate, 'AUD', '', '', freight, basis, '7')
        rd = [reading(qid, 'strength_mpa', strength, verified_by='alice'), reading(qid, 'unit', 'm3', verified_by='alice')] if verified else []
        return q, rd

    def test_a_non_comparable_quote_at_exactly_the_like_for_like_price_is_not_cheaper_and_is_silent(self):
        for rate, flagged in (('33999', True), ('34000', False), ('34001', False)):
            m = with_quotes(conc('Q-A'), self.cheap(rate=rate), dem=CONC_DEM)
            self.assertEqual(len(S_(m.mres(), 'MP02')), 1 if flagged else 0, rate)

    def test_a_quote_whose_price_comes_to_nothing_is_never_called_cheaper(self):
        qb = quote('Q-B', 'SUP-002', 'MAT-CONC40', 's', '2026-09-10', '2026-12-31', '1', 'USD', '1000', '2026-09-25', '0', 'delivered', '7')
        rb = [reading('Q-B', 'strength_mpa', '32', verified_by='alice'), reading('Q-B', 'unit', 'm3', verified_by='alice')]
        m = with_quotes(conc('Q-A'), (qb, rb), dem=CONC_DEM)
        m.fx(fxrow('2026-09-30', '1000'))                                                   # 0.01 USD at 1000 USD per AUD rounds to no cents at all
        a = m.analysis('PRJ-001')
        offers = {o['offer']['ref']: o for o in a.ranking(a.requirements()[0], 'quote_ranking')['offers']}
        self.assertEqual((offers['supplier_quote/Q-B']['gate']['class'], offers['supplier_quote/Q-B']['landed']['unit_cents']), ('not_comparable', 0))
        self.assertEqual(S_(m.mres(), 'MP02'), [])

    def test_the_wording_names_the_specification_text_the_reasons_and_whether_the_price_is_complete(self):
        m = with_quotes(conc('Q-A'), self.cheap(), dem=CONC_DEM)
        (x,) = S_(m.mres(), 'MP02')
        self.assertEqual(x['explanation']['observed'], 'supplier_quote/Q-B (SUP-002, s) is 300.00 per unit against the cheapest like-for-like offer at 340.00, but it is not comparable for MAT-CONC40: '
                                                       'attribute strength_mpa: 32 offered against 40 required (at_least)')
        self.assertEqual(x['quantification']['reason'], 'the apparent difference of 40.00 per unit is not a saving: the offers are not like-for-like')
        self.assertEqual(x['confidence']['missing_information'], ['approval of any substitution'])
        self.assertEqual(x['confidence']['evidence_strength'], 'strong')

    def test_a_price_missing_a_component_is_stated_as_at_least_and_the_difference_as_up_to(self):
        m = with_quotes(conc('Q-A'), self.cheap(basis='ex-works', freight=''), dem=CONC_DEM)
        (x,) = S_(m.mres(), 'MP02')
        self.assertIn('supplier_quote/Q-B (SUP-002, s) is at least 300.00 per unit against', x['explanation']['observed'])
        self.assertEqual(x['quantification']['reason'], 'the apparent difference of up to 40.00 per unit is not a saving: the offers are not like-for-like')

    def test_a_partly_comparable_quote_also_lacks_a_verified_reading_and_is_only_moderately_evidenced(self):
        m = with_quotes(conc('Q-A'), self.cheap(strength='40', verified=False), dem=CONC_DEM)
        (x,) = S_(m.mres(), 'MP02')
        self.assertEqual(x['taxonomy']['subtype'], 'cheaper_quote_partially_comparable')
        self.assertEqual(x['confidence']['missing_information'], ['a verified reading of the quote text', 'approval of any substitution'])
        self.assertEqual(x['confidence']['evidence_strength'], 'moderate')

    def test_the_reasons_quoted_are_the_first_three_of_the_gate(self):
        m = with_quotes(conc('Q-A'), self.cheap(strength='40', verified=False), dem=CONC_DEM)
        (x,) = S_(m.mres(), 'MP02')
        a = m.analysis('PRJ-001')
        offers = {o['offer']['ref']: o for o in a.ranking(a.requirements()[0], 'quote_ranking')['offers']}
        reasons = offers['supplier_quote/Q-B']['gate']['reasons']
        self.assertTrue(reasons)
        self.assertTrue(x['explanation']['observed'].endswith('but it is partially comparable for MAT-CONC40: ' + '; '.join(reasons[:3])))


# ------------------------------------------------------------------------------------------------------------------------------------ MP03
class TestMP03Edges(unittest.TestCase):
    def test_uncovered_demand_with_no_quote_is_flagged_up_to_the_window_and_reported_as_not_assessed_after_it(self):
        for required, days, flagged in (('2026-11-14', 45, True), ('2026-11-15', 46, False)):                 # decision_window_days is 45
            m = with_quotes(dem=[demand('DEM-1', 'PRJ-001', 'MAT-STEEL', '100', 'tonne', required)])
            r = m.mres()
            if flagged:
                (x,) = S_(r, 'MP03')
                self.assertEqual(x['explanation']['observed'], '100 tonne of MAT-STEEL are needed on site by %s and no order covers them; no current, rankable quote exists (no_rankable_offer)' % required)
                self.assertEqual(r['rule_runs']['MP03']['not_assessed'], [])
            else:
                self.assertEqual(S_(r, 'MP03'), [])
                self.assertEqual(r['rule_runs']['MP03']['not_assessed'], [{'subject': 'demand/DEM-1', 'why': 'uncovered demand but no rankable current quote (no_rankable_offer); the required date is %d days away' % days}])

    def test_the_decision_text_lists_each_offer_with_its_dates_and_any_unknown_lead_time(self):
        m = with_quotes(steel('Q-1', valid='2026-10-27'), dem=STEEL_DEM)
        q9 = quote('Q-9', 'SUP-002', 'MAT-STEEL', 's', '2026-09-10', '2026-10-30', '101000', 'AUD', '', '', '0', 'delivered', '')
        m.quote_rows(q9)
        m.readings(*std_readings('Q-9'))
        (x,) = S_(m.mres(), 'MP03')
        self.assertEqual(x['explanation']['observed'],
                         '100 tonne of MAT-STEEL are uncovered for PRJ-001 (required 2026-12-01); current offers: Q-1 (comparable) valid to 2026-10-27, latest order date 2026-11-17; '
                         'Q-9 (comparable, lead time unknown) valid to 2026-10-30; the earliest date on which a comparable offer lapses or can no longer arrive in time is 2026-10-27, 27 days after 2026-09-30')

    def test_the_reason_names_the_scenarios_that_can_be_computed_and_the_index_history_as_history_only(self):
        m = with_quotes(steel('Q-1', valid='2026-10-27'), dem=STEEL_DEM)
        (x,) = S_(m.mres(), 'MP03')
        self.assertEqual(x['explanation']['reason'], 'scenarios for buy now, wait, stage and negotiate are in the stored analysis for every rankable offer (buy_now, stage, wait); '
                                                     'no index history is available. APG applies no rule that prices rise or fall and chooses no offer')
        m.observations(obs('OBS-0', 'MAT-STEEL', '2026-06-15', '10400'), obs('OBS-1', 'MAT-STEEL', '2026-07-15', '10500'), obs('OBS-2', 'MAT-STEEL', '2026-08-15', '10700'),
                       obs('OBS-3', 'MAT-STEEL', '2026-09-15', '10930'))
        (y,) = S_(m.mres(), 'MP03')
        self.assertEqual(y['explanation']['reason'], 'scenarios for buy now, wait, stage and negotiate are in the stored analysis for every rankable offer (buy_now, stage, wait); '
                                                     'index history, shown as history only: MAT-STEEL +510 basis points between 2026-06-15 and 2026-09-15 (fresh). '
                                                     'APG applies no rule that prices rise or fall and chooses no offer')

    def test_missing_information_names_payment_terms_only_when_a_scenario_lacks_them(self):
        m = with_quotes(steel('Q-1', valid='2026-10-27'), dem=STEEL_DEM)
        (x,) = S_(m.mres(), 'MP03')
        self.assertEqual(x['confidence']['missing_information'], ['payment terms'])
        m.terms(['Q-1', 'payment_days', '30'])
        (y,) = S_(m.mres(), 'MP03')
        self.assertEqual(y['confidence']['missing_information'], ['confirmation of stock and lead time from the supplier'])


# ------------------------------------------------------------------------------------------------------------------------------------ MP04
class TestMP04Edges(unittest.TestCase):
    def test_a_delivery_above_the_demand_with_orders_within_it_is_flagged_but_has_no_surplus_to_value(self):
        m = with_quotes(dem=STEEL_DEM, orders=[pom('PO-1', qty='100', rate='100000', date='2026-08-25')])
        m.dockets(docket('DK-1', 'PO-1', 'MAT-STEEL', '2026-09-10', '120', '120'))
        (x,) = S_(m.mres(), 'MP04')
        self.assertEqual(x['explanation']['observed'], '100 tonne of MAT-STEEL are required by 2026-12-01; 100 ordered; dockets record 120 accepted')
        self.assertEqual(x['extra']['surplus_micro'], 0)                                        # the orders do not exceed the demand: nothing to value at an order rate
        self.assertEqual((x['quantification']['status'], x['quantification']['gross_cents']), ('unquantified', None))
        self.assertIsNone(x['priority']['potential_impact_cents'])

    def test_the_wording_of_a_valued_surplus(self):
        m = with_quotes(dem=STEEL_DEM, orders=[pom('PO-1', qty='70', rate='100000', date='2026-08-01'), pom('PO-2', qty='50', rate='100000', date='2026-08-25')])
        (x,) = S_(m.mres(), 'MP04')
        self.assertEqual(x['explanation']['observed'], '100 tonne of MAT-STEEL are required by 2026-12-01; 120 ordered, a surplus of 20; no delivery docket is recorded')
        self.assertEqual(x['priority']['potential_impact_cents'], 2_000_000)


# ------------------------------------------------------------------------------------------------------------------------------------ MP05
class TestMP05Edges(unittest.TestCase):
    """The duplicate groups come from the analysis; a group may hold an order whose amount is unknown (an order a person rejected after it had been held as a duplicate candidate)."""
    def group(self, amounts, dates=None, project='PRJ-001'):
        dates = dates or ['2026-08-25'] * len(amounts)
        orders = [{'ref': 'purchase_order/PO-%d' % (i + 1), 'revision': 1, 'date': d, 'confirmed': True, 'amount_cents': a} for i, (a, d) in enumerate(zip(amounts, dates))]
        return {'project': project, 'supplier': 'SUP-001', 'material': 'MAT-STEEL', 'qty_micro': 10_000_000, 'rate_cents': 100000, 'orders': orders, 'span_days': C.days(dates[0], dates[-1]),
                'held_as_candidates': False}

    def signals(self, group):
        m = mkt_world()
        a = m.analysis('PRJ-001')
        a._m['dups'] = [group]
        sigs, run = R.mp05_duplicate_order(a, a.F, a.mp, AS_OF, 'PRJ-001')
        self.assertEqual(run['status'], 'evaluated')
        return sigs

    def test_only_a_positive_known_amount_of_the_later_orders_is_quantified_and_counted_as_impact(self):
        cases = ((([1_000_000, 500_000],), 'record', 500_000), (([1_000_000, 500_000, 250_000],), 'record', 750_000),
                 (([1_000_000, 0],), 'none', None), (([1_000_000, 500_000, None],), 'none', None), (([1_000_000, None],), 'none', None), (([None, 500_000],), 'record', 500_000))
        for (amounts,), label, gross in cases:
            (x,) = self.signals(self.group(amounts))
            self.assertEqual((x['quantification']['label'], x['quantification']['gross_cents']), (label, gross), amounts)
            self.assertEqual(x['priority']['potential_impact_cents'], gross, amounts)
            self.assertEqual(x['quantification']['status'], 'quantified' if gross else 'unquantified', amounts)

    def test_the_wording_distinguishes_orders_on_one_day_from_orders_over_several_days(self):
        (same,) = self.signals(self.group([1_000_000, 1_000_000]))
        self.assertEqual(same['explanation']['observed'], '2 orders for 10 units of MAT-STEEL at 1,000.00 per unit from SUP-001 have identical details and were placed on the same day (2026-08-25)')
        (span,) = self.signals(self.group([1_000_000, 1_000_000], dates=['2026-08-25', '2026-08-28']))
        self.assertEqual(span['explanation']['observed'], '2 orders for 10 units of MAT-STEEL at 1,000.00 per unit from SUP-001 have identical details and were placed within 3 days (2026-08-25 to 2026-08-28)')


# ------------------------------------------------------------------------------------------------------------------------------------ MP06 and MP07
def intl_quote(qid='Q-1', fx='0.6612', fxd='2026-05-02', rate='1000', valid='2026-11-15'):
    return quote(qid, 'SUP-004', 'MAT-STEEL', 's', '2026-09-08', valid, rate, 'USD', fx, fxd, '0', 'FOB', '7')


def intl_world(*quotes, ref_date='2026-09-30', ref='0.6540', **mk):
    m = mkt_world(**mk)
    m.quote_rows(*quotes)
    if ref:
        m.fx(fxrow(ref_date, ref))
    return m


class TestMP06Edges(unittest.TestCase):
    def test_an_international_quote_is_looked_at_up_to_and_including_its_last_valid_day(self):
        for valid, looked_at in (('2026-09-30', True), ('2026-09-29', False)):
            m = intl_world(intl_quote(valid=valid))
            self.assertEqual(len(S_(m.mtres(), 'MP06')), 1 if looked_at else 0, valid)                 # the stated rate is five months old
            self.assertEqual(len(S_(m.mtres(), 'MP07')), 1 if looked_at else 0, valid)                 # and no import check is recorded

    def test_the_reference_rate_may_be_exactly_as_old_as_the_limit_but_not_older(self):
        for ref_date, flagged in (('2026-08-31', False), ('2026-08-30', True)):                         # import_costing fx_max_age_days is 30
            m = intl_world(intl_quote(fx='0.6540', fxd='2026-09-25'), ref_date=ref_date)
            s = S_(m.mtres(), 'MP06')
            self.assertEqual(len(s), 1 if flagged else 0, ref_date)
            if flagged:
                self.assertTrue(s[0]['explanation']['observed'].endswith('the latest reference rate (2026-08-30) is 31 days old against a limit of 30 days'))

    def test_the_stated_rate_may_be_exactly_as_old_as_the_limit_but_not_older(self):
        for fxd, flagged in (('2026-08-31', False), ('2026-08-30', True)):
            m = intl_world(intl_quote(fx='0.6540', fxd=fxd))
            s = S_(m.mtres(), 'MP06')
            self.assertEqual(len(s), 1 if flagged else 0, fxd)
            if flagged:
                self.assertTrue(s[0]['explanation']['observed'].endswith('the rate stated on the quote (0.6540) is dated 2026-08-30, 31 days before 2026-09-30 against a limit of 30 days'))

    def test_a_divergence_exactly_at_the_tolerance_is_silent_and_one_basis_point_more_is_flagged(self):
        for stated in ('0.6612', '0.6470'):                                                               # the reference conversion dearer, then cheaper than the stated one
            m = intl_world(intl_quote(fx=stated, fxd='2026-09-25'))
            a = m.analysis()
            qv = a.ctx.quotes['Q-1']
            ref = FX.convert(a.F, a.mp, qv['rate'], qv['cur'], AS_OF)
            own = FX.convert_stated(qv['rate'], qv['cur'], 'AUD', qv['fx_used'], qv['fx_date'], AS_OF)
            d = abs(FX.divergence_bps(ref['aud_cents'], own['aud_cents']))
            self.assertGreater(d, 50, stated)
            fields = DM.demo_mkt_fields()
            for tol, flagged in ((d, False), (d - 1, True)):
                m.set_mkt(fx=dict(fields['fx'], divergence_tolerance_bps=tol))
                self.assertEqual(len(S_(m.mtres(), 'MP06')), 1 if flagged else 0, (stated, tol))

    def test_the_wording_of_a_stale_diverging_rate_gives_both_conversions_and_the_unit_difference(self):
        (x,) = S_(intl_world(intl_quote()).mtres(), 'MP06')
        self.assertEqual(x['explanation']['observed'],
                         "quote Q-1 (10.00 USD per unit, fob) converts to 15.29 per unit at the reference rate (2026-09-30, method latest_on_or_before, 0 days old) and 15.12 at the quote's own stated rate; "
                         'the rate stated on the quote (0.6612) is dated 2026-05-02, 151 days before 2026-09-30 against a limit of 30 days; '
                         'converting at the reference rate instead of the stated rate changes the unit price by 1.12% (more than 1.00%)')
        self.assertEqual(x['quantification']['reason'], 'the quantity to be bought is not known here: the difference is stated per unit (0.17 per unit)')
        self.assertEqual([(e['type'], e['subject']) for e in x['extra']['events']], [('fx_observed', 'fx_rate/2026-09-30|AUD/USD')])

    def test_the_wording_without_a_reference_rate_or_without_a_stated_rate(self):
        (a,) = S_(intl_world(intl_quote(fx='0.6540', fxd='2026-09-25'), ref=None).mtres(), 'MP06')
        self.assertEqual(a['explanation']['observed'], "quote Q-1 (10.00 USD per unit, fob) converts to no amount per unit at the reference rate and 15.29 at the quote's own stated rate; "
                                                       'no usable reference rate: no usable AUD/USD rate on or before 2026-09-30')
        self.assertEqual(a['quantification']['reason'], 'the quantity to be bought is not known here: the difference is stated per unit (not computable per unit)')
        self.assertEqual(a['extra']['events'], [])
        (b,) = S_(intl_world(intl_quote(fx='', fxd='')).mtres(), 'MP06')
        self.assertEqual(b['explanation']['observed'], "quote Q-1 (10.00 USD per unit, fob) converts to 15.29 per unit at the reference rate (2026-09-30, method latest_on_or_before, 0 days old) and no amount at the quote's own stated rate; "
                                                       'the quote states no usable FX rate, so its own conversion cannot be reproduced')
        self.assertEqual(b['quantification']['reason'], 'the quantity to be bought is not known here: the difference is stated per unit (not computable per unit)')

    def test_a_stated_rate_with_no_date_has_an_unknown_age_and_a_zero_difference_is_still_a_difference(self):
        (x,) = S_(intl_world(intl_quote(fx='0.6540', fxd='')).mtres(), 'MP06')
        self.assertTrue(x['explanation']['observed'].endswith('the rate stated on the quote (0.6540) is dated with no date, so its age is unknown against a limit of 30 days'))
        self.assertEqual(x['quantification']['reason'], 'the quantity to be bought is not known here: the difference is stated per unit (0.00 per unit)')


class TestMP07Edges(unittest.TestCase):
    def test_a_critical_check_missing_from_the_configured_list_is_unresolved_and_named_as_such(self):
        m = intl_world(intl_quote(fx='0.6540', fxd='2026-09-25'))
        m.set_mkt(international=dict(checks=['customs_classification', 'duty_rate_confirmed', 'import_permit', 'supplier_vetting'],
                                     critical_checks=['customs_classification', 'duty_rate_confirmed', 'import_permit', 'sanctions_screening']))
        (x,) = S_(m.mtres(), 'MP07')
        self.assertEqual(x['explanation']['observed'], 'international quote Q-1 (SUP-004, fob) has 4 unresolved critical check(s): customs_classification (no record of this check); '
                                                       'duty_rate_confirmed (no record of this check); import_permit (no record of this check); sanctions_screening (not in the configured list of checks)')
        self.assertEqual(x['extra']['unresolved_critical'], ['customs_classification', 'duty_rate_confirmed', 'import_permit', 'sanctions_screening'])


# ------------------------------------------------------------------------------------------------------------------------------------ MP08
class TestMP08Edges(unittest.TestCase):
    def test_the_stored_profile_keeps_the_measures_and_leaves_the_evidence_list_to_the_signal(self):
        m = mkt_world()
        orders = [pom('PO-%d' % i, qty='10', rate='100000', date='2026-08-%02d' % (i + 1)) for i in (1, 2, 3)]
        m.orders(*orders)
        m.dockets(*[docket('DK-%d' % i, 'PO-%d' % i, 'MAT-STEEL', '2026-08-%02d' % (i + 10), '10', '8') for i in (1, 2, 3)])
        (x,) = S_(m.mtres(), 'MP08')
        prof = x['extra']['profile']
        self.assertNotIn('evidence', prof)
        self.assertEqual((prof['acceptance_rate_bps'], prof['orders_with_deliveries']), (8000, 3))
        self.assertIn('levels', prof)
        self.assertEqual(x['extra']['flagged'], ['acceptance_rate', 'fill_rate'])


class TestConversionStatusAndSourceMoveTogether(unittest.TestCase):
    """Pins the invariant behind a documented equivalent mutant (EQUIV, RU-BOL-028): for a foreign-currency amount the reference conversion is `converted` exactly when it names the stored
    rate it used, and `not_converted` with no source otherwise, so the two conditions MP06 tests before it writes an fx_observed event always agree."""

    def test_a_foreign_conversion_is_converted_with_a_source_or_not_converted_with_none(self):
        for rows, status, has_source in (([fxrow('2026-09-30', '0.6540')], 'converted', True), ([fxrow('2026-10-15', '0.7000')], 'not_converted', False), ([], 'not_converted', False)):
            m = mkt_world()
            if rows:
                m.fx(*rows)
            a = m.analysis(as_of='2026-09-30')
            c = FX.convert(a.F, a.mp, 6900, 'USD', '2026-09-30')
            self.assertEqual(c['status'], status)
            self.assertEqual(bool(c['rate_source_ref']), has_source, 'status %s, source %r' % (c['status'], c['rate_source_ref']))
            if has_source:
                self.assertTrue(c['rate_source_ref'].startswith('fx_rate/'))


if __name__ == '__main__':
    unittest.main()
