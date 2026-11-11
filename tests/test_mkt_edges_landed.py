"""Edge-case tests for landed cost, the comparability application / ranking / purchase-order reference, and the buy-now / wait / stage / negotiate scenarios (boundaries, both-conditions-needed cases,
guards).  Fixed dates only: the demonstration as-of day is 2026-09-30."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_mkt import *
from apg.mkt import compare as CP, demand as DEM, landed as LD, scenarios as SC

M = 1_000_000
AS_OF_DAY = '2026-09-30'


def steel(qid='Q-1', rate='265000', valid='2026-12-31', lead='21', sup='SUP-001', basis='delivered', freight='0', cur='AUD', fx='', fxd=''):
    return quote(qid, sup, 'MAT-STEEL', 's', '2026-09-10', valid, rate, cur, fx, fxd, freight, basis, lead)


def comp(ul, name):
    return next(c for c in ul['components'] if c['component'] == name)


def swld(*quotes, qty='40', required='2026-12-01', readings=True, **kw):
    m = mkt_world(**kw)
    m.quote_rows(*quotes)
    if readings:
        m.readings(*[r for q in quotes for r in std_readings(q[0])])
    m.demands(demand('DEM-1', 'PRJ-001', 'MAT-STEEL', qty, 'tonne', required))
    return m


def sbuild(m, as_of=AS_OF_DAY):
    ctx = m.ctx(as_of=as_of)
    (req,) = [r for r in CP.requirements(ctx) if r['kind'] == 'demand']
    return SC.build(ctx, req, DEM.coverage(ctx, req)), ctx, req


def by(scn, name):
    return [x for x in scn['scenarios'] if x['scenario'] == name]


def costs(m, order_date=AS_OF_DAY, qty=40 * M, required='2026-12-01', extra_orders=0, price_bps=0, key='Q-1'):
    ctx = m.ctx()
    req = {'id': 'demand/DEM-1', 'project': 'PRJ-001', 'material': 'MAT-STEEL', 'required_date': required, 'approved': True, 'kind': 'demand'}
    o = {'offer': {'key': key, 'ref': 'supplier_quote/' + key}}
    return SC._costs(ctx, o, qty, order_date, req, extra_orders, price_bps)


class TestLandedEdges(unittest.TestCase):
    DEL = steel()

    def world(self, *quotes, fxr=(), asm=(), tiers=(), terms=()):
        m = mkt_world()
        m.quote_rows(*quotes)
        if fxr:
            m.fx(*fxr)
        if asm:
            m.assumptions(*asm)
        if tiers:
            m.tiers(*tiers)
        if terms:
            m.terms(*terms)
        return m

    def ul(self, m, key='Q-1', qty=None):
        a = m.analysis()
        return LD.unit_landed(a.F, a.mp, a.ctx.quotes[key], AS_OF_DAY, qty)

    def plan(self, m, need):
        a = m.analysis()
        return LD.purchase_plan(a.F, a.mp, a.ctx.quotes['Q-1'], AS_OF_DAY, need)

    def test_a_tier_that_starts_exactly_at_the_quantity_already_bought_is_not_a_larger_order(self):
        m = self.world(self.DEL, tiers=[['Q-1', '100', '262000']])
        self.assertEqual(self.plan(m, 100 * M)['larger_orders'], [], 'the tier begins at the quantity that is bought anyway: nothing larger is offered')
        self.assertEqual(len(self.plan(m, 100 * M - 1)['larger_orders']), 1, 'one micro-unit short of the tier: the tier is a larger order')
        m2 = self.world(self.DEL, tiers=[['Q-1', '10', '262000']], terms=[['Q-1', 'moq', '10']])
        p = self.plan(m2, 3 * M)
        self.assertEqual((p['plain']['buy_qty_micro'], p['larger_orders']), (10 * M, []), 'the minimum order already reaches the tier start')

    def test_tier_minimums_of_zero_or_less_or_unreadable_are_invalid_and_held_not_used(self):
        for minimum in ('0', '-5'):
            m = self.world(self.DEL, tiers=[['Q-1', minimum, '262000'], ['Q-1', '100', '261000']])
            out, held = LD.tiers(m.analysis().F, 'Q-1')
            self.assertEqual([(t[0], t[1]) for t in out], [(100 * M, 261000)], 'minimum %s: only the valid tier is usable' % minimum)
            self.assertEqual([h['why'] for h in held], [['TIER_INVALID']], 'minimum %s must be held as TIER_INVALID' % minimum)

    def test_stated_freight_on_a_basis_that_includes_it_adds_exactly_one_limit_and_only_when_freight_is_stated(self):
        cases = [('9500', 1), ('', 0), ('0', 0)]
        for freight, expected in cases:
            u = self.ul(self.world(steel(freight=freight)))
            self.assertEqual(len([x for x in u['limits'] if 'not added again' in x]), expected, 'freight %r on a delivered basis' % freight)
            self.assertEqual(len(u['limits']), expected, 'freight %r: no other limit is expected for a delivered quote' % freight)
        u = self.ul(self.world(steel(freight='9500')))
        self.assertTrue(u['limits'][0].startswith('freight '), u['limits'])
        self.assertEqual((u['unit_cents'], comp(u, 'freight')['status']), (265000, 'included_in_rate'))

    def test_the_freight_warning_is_about_freight_being_included_not_about_any_other_included_component(self):
        bases = dict(DM.demo_mkt_fields()['basis'])
        bases['delivery_bases'] = {'delivered': {'includes': ['freight', 'handling']}, 'ex-works': {'includes': []}, 'fob': {'includes': []},
                                   'handled': {'includes': ['handling']}, 'carted': {'includes': ['freight']}}
        m = mkt_world()
        m.set_mkt(basis=bases)
        m.quote_rows(steel('Q-1', basis='handled', freight='9500'), steel('Q-2', sup='SUP-002', basis='carted', freight='9500'))
        a = m.analysis()
        u1 = LD.unit_landed(a.F, a.mp, a.ctx.quotes['Q-1'], AS_OF_DAY)
        self.assertEqual((comp(u1, 'freight')['status'], comp(u1, 'handling')['status'], u1['unit_cents']), ('stated', 'included_in_rate', 274500))
        self.assertEqual(u1['limits'], [], 'freight is not included by this basis, so freight stated on the quote is added and nothing is warned')
        u2 = LD.unit_landed(a.F, a.mp, a.ctx.quotes['Q-2'], AS_OF_DAY)
        self.assertEqual((comp(u2, 'freight')['status'], u2['unit_cents']), ('included_in_rate', 265000))
        self.assertEqual(len(u2['limits']), 1, u2['limits'])
        self.assertIn('not added again', u2['limits'][0])

    def test_an_international_purchase_is_either_a_foreign_currency_or_an_international_delivery_basis(self):
        a = self.world(self.DEL).analysis()
        mp = a.mp
        table = [('AUD', 'delivered', False), ('USD', 'delivered', True), ('AUD', 'fob', True), ('USD', 'fob', True), ('AUD', 'cif', True), ('AUD', 'ex-works', False)]
        for cur, basis, expected in table:
            self.assertEqual(LD.is_international(mp, {'cur': cur, 'basis': basis}), expected, '%s on %s' % (cur, basis))

    def test_an_international_flag_follows_into_the_landed_record_and_its_required_components(self):
        m = self.world(steel(basis='FOB', freight=''))              # home currency but an international basis
        u = self.ul(m)
        self.assertTrue(u['international'])
        self.assertEqual(u['missing'], ['freight', 'insurance', 'duty', 'clearance'])
        m2 = self.world(steel(rate='6900', cur='USD', fx='0.6612', fxd='2026-05-02', freight=''), fxr=[fxrow('2026-09-30', '0.6540')])   # foreign currency on a domestic basis
        u2 = self.ul(m2)
        self.assertTrue(u2['international'])
        self.assertIn('insurance', u2['missing'])

    def test_a_per_unit_assumption_quotes_its_basis_text_or_says_there_is_none(self):
        for basis_text, shown in (('allowance for the run', '(allowance for the run)'), ('', '(no basis text)')):
            m = self.world(steel(basis='ex-works', freight='9500'), asm=[['Q-1', 'insurance', '150', '', '', basis_text, 'none', 'alice', '2026-09-20']])
            c = comp(self.ul(m), 'insurance')
            self.assertEqual((c['status'], c['cents']), ('assumed', 150))
            self.assertEqual(c['note'], 'assumption set by alice %s' % shown)

    def test_a_basis_point_duty_assumption_quotes_its_basis_text_or_says_there_is_none(self):
        for basis_text, shown in (('tariff schedule 7', '(tariff schedule 7)'), ('', '(no basis text)')):
            m = self.world(steel(rate='6900', basis='FOB', cur='USD', fx='0.6612', fxd='2026-05-02', freight='800', lead='56'), fxr=[fxrow('2026-09-30', '0.6540')],
                           asm=[['Q-1', 'duty', '', '500', '', basis_text, 'ref', 'alice', '2026-09-20']])
            c = comp(self.ul(m), 'duty')
            self.assertEqual((c['status'], c['cents']), ('assumed', 528))
            self.assertEqual(c['note'], '500 basis points of the purchase cost, assumption set by alice %s' % shown)

    def test_a_larger_tier_with_exactly_the_same_total_is_never_described_as_a_lower_total(self):
        m = self.world(self.DEL, tiers=[['Q-1', '100', '106000']])       # 100 x 106,000 = 40 x 265,000 = 10,600,000
        (opt,) = self.plan(m, 40 * M)['larger_orders']
        self.assertEqual((opt['total_cents'], opt['extra_total_cents_vs_plain']), (10_600_000, 0))
        self.assertNotIn('total paid is lower', opt['note'], 'an equal total is not a saving: a larger order is never assumed cheaper')

    def test_a_larger_tier_with_a_genuinely_lower_total_says_lower(self):
        m = self.world(self.DEL, tiers=[['Q-1', '41', '250000']])        # 41 x 250,000 = 10,250,000 < 10,600,000
        (opt,) = self.plan(m, 40 * M)['larger_orders']
        self.assertEqual((opt['total_cents'], opt['extra_total_cents_vs_plain']), (10_250_000, -350_000))
        self.assertIn('total paid is lower', opt['note'])
        self.assertIn('surplus is not assumed reusable', opt['note'])


class TestCompareEdges(unittest.TestCase):
    def setUp(self):
        self.req = {'id': 'demand/DEM-1', 'project': 'PRJ-001', 'material': 'MAT-STEEL', 'required_date': '2026-12-01', 'approved': True, 'kind': 'demand'}

    def test_a_standing_requirement_is_approved_only_with_both_the_approver_and_the_date(self):
        m = mkt_world()
        m.spec_reqs(['SR-1', 'PRJ-001', 'MAT-STEEL', 'ref', 'alice', '2026-09-01'], ['SR-2', 'PRJ-001', 'MAT-STEEL', 'ref', 'alice', ''],
                    ['SR-3', 'PRJ-001', 'MAT-STEEL', 'ref', '', '2026-09-01'], ['SR-4', 'PRJ-001', 'MAT-STEEL', 'ref', '', ''])
        got = {r['id']: r['approved'] for r in CP.requirements(m.ctx())}
        self.assertEqual(got, {'spec_requirement/SR-1': True, 'spec_requirement/SR-2': False, 'spec_requirement/SR-3': False, 'spec_requirement/SR-4': False})

    def test_currency_conversion_is_listed_as_an_adjustment_only_when_the_conversion_happened(self):
        usd = steel('Q-1', rate='6900', cur='USD', fx='0.6612', fxd='2026-05-02', freight='800', basis='FOB', lead='56')
        for with_rate, expected in ((True, True), (False, False)):
            m = swld(usd)
            if with_rate:
                m.fx(fxrow('2026-09-30', '0.6540'))
            ctx = m.ctx()
            (req,) = [r for r in CP.requirements(ctx) if r['kind'] == 'demand']
            o = CP.eval_quote(ctx, ctx.quotes['Q-1'], req, 'quote_ranking')
            kinds = [a['kind'] for a in o['gate']['adjustments']]
            self.assertEqual('currency_converted' in kinds, expected, 'rate recorded: %s -> %s' % (with_rate, kinds))
        m = swld(steel('Q-1'))
        ctx = m.ctx()
        (req,) = [r for r in CP.requirements(ctx) if r['kind'] == 'demand']
        o = CP.eval_quote(ctx, ctx.quotes['Q-1'], req, 'quote_ranking')
        self.assertNotIn('currency_converted', [a['kind'] for a in o['gate']['adjustments']], 'a home-currency quote is not converted')

    def test_an_offer_whose_known_cost_is_zero_is_never_rankable(self):
        usd = steel('Q-1', rate='6900', cur='USD', fx='0.6612', fxd='2026-05-02', freight='800', basis='FOB', lead='56')
        m = swld(usd, steel('Q-2', sup='SUP-002'))                 # no exchange rate: the USD offer has nothing it can price
        ctx = m.ctx()
        (req,) = [r for r in CP.requirements(ctx) if r['kind'] == 'demand']
        o = CP.eval_quote(ctx, ctx.quotes['Q-1'], req, 'quote_ranking')
        self.assertEqual(o['landed']['unit_cents'], 0)
        self.assertFalse(o['rankable'])
        r = CP.rank(ctx, req, 'quote_ranking')
        self.assertEqual([x['offer'] for x in r['ranking']], ['supplier_quote/Q-2'])
        self.assertEqual([x['offer'] for x in r['excluded']], ['supplier_quote/Q-1'])
        self.assertEqual(r['status'], 'insufficient_offers')

    def po_world(self, *orders):
        m = mkt_world()
        m.orders(*orders)
        return m

    def test_an_order_rate_is_stale_only_when_older_than_the_benchmark_limit(self):
        # benchmark limit: 90 days; the as-of day is 2026-09-30
        for date, state in (('2026-07-02', 'current'), ('2026-07-01', 'stale'), ('2026-07-03', 'current')):
            m = self.po_world(pom('PO-1', date=date, rate='250000'))
            ctx = m.ctx('PRJ-001')
            ev = CP.eval_po(ctx, ctx.pos['PO-1'], self.req)
            (st,) = ev['freshness']
            self.assertEqual((st['threshold_days'], st['state']), (90, state), 'order dated %s is %s days old' % (date, st['age_days']))
        self.assertEqual(st['age_days'], 89)
        ctx = self.po_world(pom('PO-1', date='2026-07-02', rate='250000')).ctx('PRJ-001')
        self.assertEqual(CP.eval_po(ctx, ctx.pos['PO-1'], self.req)['freshness'][0]['age_days'], 90)

    def test_a_purchase_order_is_a_substitution_only_when_its_material_differs_from_the_requirement(self):
        m = self.po_world(pom('PO-1', date='2026-08-01', rate='250000'))
        ctx = m.ctx('PRJ-001')
        po = ctx.pos['PO-1']
        self.assertFalse(CP.eval_po(ctx, po, self.req)['substitution'])
        other = dict(self.req, material='MAT-CONC40')
        self.assertTrue(CP.eval_po(ctx, po, other)['substitution'])
        ref = CP.last_paid(ctx, self.req)
        self.assertFalse(ref['substitution'], 'the last-paid reference is for the same material')

    def test_an_order_held_for_a_reason_other_than_a_possible_duplicate_is_never_the_reference(self):
        m = self.po_world(pom('PO-1', supplier='SUP-999', date='2026-08-25', rate='185000', qty='13'))
        ctx = m.ctx('PRJ-001')
        po = ctx.pos['PO-1']
        self.assertEqual((po['ok'], po['dup_candidates'], po['rate'], po['project']), (False, [], 185000, 'PRJ-001'))
        self.assertIsNone(CP.last_paid(ctx, self.req), 'an order reconciliation holds back for another reason must not be the reference')
        m2 = self.po_world(pom('PO-1', supplier='SUP-999', date='2026-08-25', rate='185000', qty='13'), pom('PO-2', date='2026-06-01', rate='170000'))
        self.assertEqual(CP.last_paid(m2.ctx('PRJ-001'), self.req)['offer']['key'], 'PO-2', 'the newer held order is skipped; the older accepted one is used')

    def test_a_possible_duplicate_whose_candidate_carries_a_different_rate_is_not_the_reference(self):
        m = self.po_world(pom('PO-1', date='2026-08-25', rate='185000', qty='13'), pom('PO-2', date='2026-08-25', rate='185000', qty='13'))
        ctx = m.ctx('PRJ-001')
        self.assertTrue(CP.last_paid(ctx, self.req)['held_as_duplicate_candidate'])        # identical records corroborate the rate
        ctx.pos['PO-2']['rate'] = 190000                            # the candidates now disagree on the rate
        self.assertIsNone(CP.last_paid(ctx, self.req), 'candidates that disagree on the rate do not corroborate it')

    def test_three_identical_orders_held_as_duplicates_name_each_other_one_by_one_and_corroborate_the_reference(self):
        m = self.po_world(*[pom('PO-%d' % i, date='2026-08-25', rate='185000', qty='13') for i in (1, 2, 3)])
        ctx = m.ctx('PRJ-001')
        self.assertEqual(sorted(ctx.pos), ['PO-1', 'PO-2', 'PO-3'])
        self.assertEqual([ctx.pos['PO-%d' % i]['dup_candidates'] for i in (1, 2, 3)], [['PO-2', 'PO-3'], ['PO-1', 'PO-3'], ['PO-1', 'PO-2']],
                         'reconciliation joins the candidates with commas: each one is a separate order, never one name such as "PO-2,PO-3"')
        r = CP.last_paid(ctx, self.req)
        self.assertIsNotNone(r, 'three identical orders carry one rate on every candidate: it corroborates the reference')
        self.assertEqual(r['landed']['unit_cents'], 185000)
        self.assertTrue(r['held_as_duplicate_candidate'])
        self.assertIn('possible duplicate of PO-1, PO-2;', ' '.join(r['landed']['limits']), 'ties on the date go to the highest key, and the limit names the other two orders separately')

    def test_an_order_rate_in_another_unit_is_rescaled_to_the_requirement_unit_like_a_quote(self):
        m = self.po_world(pom('PO-1', date='2026-08-01', rate='265', unit='kg'))
        m.set_spec(unit_conversions=[{'material': 'MAT-STEEL', 'from_unit': 'kg', 'to_unit': 'tonne', 'factor_micro': 1000}])
        ctx = m.ctx('PRJ-001')
        ref = CP.last_paid(ctx, self.req)
        self.assertEqual(ref['landed']['unit_cents'], 265000, '265 cents per kg is 265,000 cents per tonne at the declared factor')
        self.assertEqual(ref['landed']['unit_conversion']['from_unit'], 'kg')
        self.assertEqual(ref['landed']['unit_conversion']['to_unit'], 'tonne')
        self.assertIn('unit_converted', [a['kind'] for a in ref['gate']['adjustments']])
        self.assertEqual(ref['blockers'], ['REFERENCE_ONLY'])
        self.assertFalse(ref['rankable'])
        # a rate already in the requirement unit is left exactly as recorded
        m2 = self.po_world(pom('PO-1', date='2026-08-01', rate='265000', unit='tonne'))
        ref2 = CP.last_paid(m2.ctx('PRJ-001'), self.req)
        self.assertEqual(ref2['landed']['unit_cents'], 265000)
        self.assertIsNone(ref2['landed'].get('unit_conversion'))


class TestScenarioEdges(unittest.TestCase):
    def test_a_quote_is_still_valid_on_its_last_valid_day_and_lapsed_the_day_after(self):
        m = swld(steel(valid='2026-09-30'))
        unit, total, inc, sched, wc, gaps = costs(m, order_date='2026-09-30')
        self.assertTrue(sched['quote_valid_on_order_date'])
        self.assertFalse(any('lapses' in g for g in gaps))
        unit, total, inc, sched, wc, gaps = costs(m, order_date='2026-10-01')
        self.assertFalse(sched['quote_valid_on_order_date'])
        self.assertTrue(any('lapses on 2026-09-30, before the order date 2026-10-01' in g for g in gaps))

    def test_surplus_is_reported_only_when_more_than_the_need_is_bought(self):
        m = swld(steel())
        _, _, _, sched, _, gaps = costs(m)
        self.assertNotIn('surplus_qty_micro', sched, 'buying exactly the need leaves no surplus')
        self.assertFalse(any('more than needed' in g for g in gaps))
        _, _, _, sched, _, gaps = costs(swld_with_terms(['Q-1', 'moq', '45']))
        self.assertEqual(sched['surplus_qty_micro'], 5 * M)
        self.assertTrue(any('5 units more than needed' in g for g in gaps))

    def test_financing_for_zero_days_is_zero_and_computes_nothing(self):
        self.assertEqual(SC._financing(10_600_000, 800, 0, 365), 0)
        self.assertEqual(SC._financing(-100, 800, 0, 365), 0, 'no days, no financing: nothing is evaluated')
        self.assertEqual(SC._financing(10_600_000, 800, 41, 365), 95_255)
        self.assertEqual(SC._financing(10_600_000, 800, -3, 365), 0)

    def test_storage_is_costed_only_for_days_before_the_required_date(self):
        m = swld(steel())                                           # delivery 2026-10-21
        _, _, inc, sched, _, gaps = costs(m, required='2026-10-21')
        self.assertEqual((sched['delivery_date'], sched['days_before_required'], sched['meets_required_date']), ('2026-10-21', 0, True))
        self.assertFalse([i for i in inc if i['label'].startswith('storage')], 'delivery on the required day is stored for no days')
        _, _, inc, sched, _, gaps = costs(m, required='2026-10-22')
        (st,) = [i for i in inc if i['label'].startswith('storage')]
        self.assertEqual((sched['days_before_required'], st['cents']), (1, 50 * 40))
        _, _, inc, sched, _, gaps = costs(m, required='2026-10-20')
        self.assertEqual((sched['days_before_required'], sched['meets_required_date']), (-1, False))
        self.assertFalse([i for i in inc if i['label'].startswith('storage')])

    def test_without_a_storage_rate_the_gap_is_listed_only_when_there_are_days_to_store(self):
        f = DM.demo_mkt_fields()
        del f['scenarios']['storage_cents_per_unit_per_day']
        m = swld(steel())
        m.set_mkt(**f)
        _, _, _, _, _, gaps = costs(m, required='2026-10-21')
        self.assertNotIn('no storage rate is configured: storage cost is not assessed', gaps)
        _, _, _, _, _, gaps = costs(m, required='2026-10-22')
        self.assertIn('no storage rate is configured: storage cost is not assessed', gaps)

    def test_extra_orders_add_the_policy_staging_cost_and_none_adds_nothing(self):
        m = swld(steel())
        _, _, inc0, _, _, _ = costs(m, extra_orders=0)
        self.assertFalse([i for i in inc0 if 'additional order' in i['label']])
        _, _, inc2, _, _, _ = costs(m, extra_orders=2)
        (x,) = [i for i in inc2 if 'additional order' in i['label']]
        self.assertEqual((x['label'], x['cents']), ('extra delivery and administration for 2 additional order(s)', 2 * (25000 + 5000)))

    def test_an_incomplete_landed_cost_names_what_is_missing_or_the_unknown_delivery_basis(self):
        m = swld(steel(basis='ex-works', freight=''))
        gaps = costs(m)[5]
        self.assertIn('the landed cost is incomplete (missing: freight); the figures are a lower bound', gaps)
        m2 = swld(steel(basis='dap'))
        gaps2 = costs(m2)[5]
        self.assertIn('the landed cost is incomplete (missing: delivery basis); the figures are a lower bound', gaps2)
        self.assertFalse(any('incomplete' in g for g in costs(swld(steel()))[5]))

    def test_the_context_history_uses_only_this_materials_observations_on_or_before_the_as_of_day(self):
        m = swld(steel())
        m.observations(obs('O1', date='2026-06-15', value='10000'), obs('O2', date='2026-07-15', value='10100'), obs('O3', date='2026-08-15', value='10200'), obs('O4', date='2026-09-15', value='10300'),
                       obs('O5', date='2026-09-30', value='10400'),                                        # on the as-of day: counted
                       obs('O6', date='2026-10-05', value='99999'),                                        # after the as-of day: not known yet
                       obs('X1', mat='MAT-CONC40', date='2026-09-20', value='1'))                          # another material
        ctx = m.ctx()
        c = SC.market_context(ctx, 'MAT-STEEL')
        self.assertEqual((c['status'], c['points'], c['from'], c['to'], c['first_value'], c['last_value']), ('history', 4, '2026-07-15', '2026-09-30', 10100, 10400))
        self.assertEqual(c['observations'], ['market_observation/O2', 'market_observation/O3', 'market_observation/O4', 'market_observation/O5'])
        self.assertEqual(c['direction'], 'up')
        self.assertEqual(c['change_bps'], 297)                       # 300 / 10100

    def test_the_context_direction_is_flat_when_the_first_and_last_values_are_equal(self):
        m = swld(steel())
        m.observations(obs('O1', date='2026-06-15', value='10000'), obs('O2', date='2026-07-15', value='10500'), obs('O3', date='2026-08-15', value='9800'), obs('O4', date='2026-09-15', value='10000'))
        c = SC.market_context(m.ctx(), 'MAT-STEEL')
        self.assertEqual((c['status'], c['direction'], c['change_bps']), ('history', 'flat', 0))
        m2 = swld(steel())
        m2.observations(obs('O1', date='2026-06-15', value='10000'), obs('O2', date='2026-07-15', value='10500'), obs('O3', date='2026-08-15', value='9800'), obs('O4', date='2026-09-15', value='9999'))
        self.assertEqual(SC.market_context(m2.ctx(), 'MAT-STEEL')['direction'], 'down')
        m3 = swld(steel())
        m3.observations(obs('O1', date='2026-06-15', value='10000'), obs('O2', date='2026-07-15', value='10500'), obs('O3', date='2026-08-15', value='9800'), obs('O4', date='2026-09-15', value='10001'))
        self.assertEqual(SC.market_context(m3.ctx(), 'MAT-STEEL')['direction'], 'up')

    def test_a_first_value_of_zero_gives_no_percentage_change(self):
        m = swld(steel())
        m.observations(obs('O1', date='2026-06-15', value='0'), obs('O2', date='2026-07-15', value='100'), obs('O3', date='2026-08-15', value='200'), obs('O4', date='2026-09-15', value='300'))
        c = SC.market_context(m.ctx(), 'MAT-STEEL')
        self.assertEqual((c['status'], c['first_value'], c['last_value'], c['direction']), ('history', 0, 300, 'up'))
        self.assertIsNone(c['change_bps'], 'no ratio against a zero start')

    def test_waiting_is_assessable_on_the_latest_order_day_and_not_available_the_day_after(self):
        # lead 21 + variation 7: the latest order day for a required date D is D - 28 days
        s, _, _ = sbuild(swld(steel(), required='2026-10-28'))      # latest order date = the as-of day itself
        self.assertEqual(by(s, 'wait'), [])
        self.assertEqual(sorted(x['scenario'] for x in s['scenarios'] if x['scenario'].startswith('wait:')), ['wait:down_5pct', 'wait:flat', 'wait:up_5pct'])
        flat = by(s, 'wait:flat')[0]
        self.assertEqual((flat['schedule']['order_date'], flat['wait_days']), (AS_OF_DAY, 0))
        s2, _, _ = sbuild(swld(steel(), required='2026-10-27'))     # latest order date = the day before the as-of day
        (w,) = by(s2, 'wait')
        self.assertEqual(w['status'], 'not_available')
        self.assertIn('was 2026-09-29, before the as-of day', w['why'])

    def test_the_horizon_note_appears_only_when_the_wait_is_longer_than_the_price_path_horizon(self):
        # path horizons are 30 days; wait_days = days from the as-of day to the latest order day
        for required, wait_days, note in (('2026-11-27', 30, False), ('2026-11-28', 31, True), ('2026-11-26', 29, False)):
            s, _, _ = sbuild(swld(steel(), required=required))
            flat = by(s, 'wait:flat')[0]
            self.assertEqual(flat['wait_days'], wait_days)
            self.assertEqual(any('covers 30 days but the wait is %d days' % wait_days in u for u in flat['uncertainty']), note, 'required %s' % required)

    def test_staging_keeps_every_unit_of_the_need_and_numbers_the_tranches_from_one(self):
        s, _, _ = sbuild(swld(steel(), qty='40.000001'))            # an odd micro-unit: the halves round up, the last tranche takes the remainder
        (st,) = by(s, 'stage')
        self.assertEqual([t['quantity_micro'] for t in st['tranches']], [20_000_001, 20_000_000])
        self.assertEqual(sum(t['quantity_micro'] for t in st['tranches']), s['quantity_micro'])
        self.assertEqual([t['tranche'] for t in st['tranches']], [1, 2])

    def test_the_negotiate_scenario_lists_the_comparison_status_as_a_gap_unless_it_is_definitive(self):
        quotes = (steel('Q-1'), steel('Q-2', '255000', sup='SUP-002'))
        s, _, _ = sbuild(swld(*quotes))
        self.assertEqual(s['ranking_status'], 'indicative')         # no fresh index series yet: the evidence is only qualified
        (n,) = by(s, 'negotiate')
        self.assertEqual(n['status'], 'scenario_only')
        self.assertEqual(n['evidence_gaps'][0], 'qualification and switching cost are not recorded')
        self.assertEqual(len(n['evidence_gaps']), 2)
        self.assertTrue(n['evidence_gaps'][1].startswith('the comparison is indicative: '))
        m = swld(*quotes)
        m.observations(*[obs('O%d' % i, date='2026-0%d-15' % i, value=str(10000 + i * 300)) for i in (6, 7, 8, 9)])
        s2, _, _ = sbuild(m)
        self.assertEqual(s2['ranking_status'], 'definitive')
        (n2,) = by(s2, 'negotiate')
        self.assertEqual(n2['evidence_gaps'], ['qualification and switching cost are not recorded'])
        self.assertEqual(n2['lowest_complete_offer'], 'supplier_quote/Q-2')


class TestDepositTermEdges(unittest.TestCase):
    def deposit(self, text):
        m = swld(steel())
        m.terms(['Q-1', 'payment_days', '30'], ['Q-1', 'deposit_bps', text])
        _, _, _, _, wc, gaps = costs(m)
        return wc, gaps

    def test_a_deposit_of_zero_to_one_hundred_percent_is_accepted(self):
        for text, has_dep in (('0', False), ('2000', True), ('10000', True)):
            wc, gaps = self.deposit(text)
            self.assertEqual('deposit_cents' in wc, has_dep, text)
            self.assertFalse(any('deposit' in g for g in gaps), (text, gaps))

    def test_a_deposit_above_one_hundred_percent_is_a_gap_and_assumes_no_deposit(self):
        wc, gaps = self.deposit('10001')
        self.assertNotIn('deposit_cents', wc)
        self.assertTrue(any('outside 0 to 10000' in g and 'no deposit is assumed' in g for g in gaps), gaps)
        wc, gaps = self.deposit('-5')                       # a negative number is not a readable quantity: still a gap, still no deposit
        self.assertNotIn('deposit_cents', wc)
        self.assertTrue(any('no deposit is assumed' in g for g in gaps), gaps)

    def test_a_deposit_that_is_not_a_number_is_a_gap_and_assumes_no_deposit(self):
        wc, gaps = self.deposit('some')
        self.assertNotIn('deposit_cents', wc)
        self.assertTrue(any('cannot be read as basis points' in g for g in gaps), gaps)


def swld_with_terms(*terms):
    m = swld(steel())
    m.terms(*terms)
    return m


class TestInvariantsBehindDocumentedEquivalentMutants(unittest.TestCase):
    """The mutation tool lists a few single-site changes as unable to change behaviour (tools/m6_mutants.py, EQUIV).  Each rests on an invariant stated there; these tests pin the invariants, so
    a later change that breaks one is noticed even though the equivalent mutant itself cannot be killed."""

    def test_a_source_reference_appears_once_per_landed_record_so_the_revision_never_breaks_a_tie(self):
        usd = steel('Q-1', rate='6900', cur='USD', fx='0.6612', fxd='2026-05-02', freight='800', basis='FOB', lead='56')
        m = mkt_world()
        m.quote_rows(usd)
        m.fx(fxrow('2026-09-30', '0.6540'))
        m.assumptions(['Q-1', 'insurance', '150', '', 'USD', 'a', 'r', 'alice', '2026-09-20'])
        m.tiers(['Q-1', '10', '6800'], ['Q-1', '100', '6700'])
        m.terms(['Q-1', 'moq', '5'])
        a = m.analysis()
        for qty in (None, 120 * M):
            refs = [x[0] for x in LD.unit_landed(a.F, a.mp, a.ctx.quotes['Q-1'], AS_OF_DAY, qty)['sources']]
            self.assertEqual(len(refs), len(set(refs)), 'a record is listed once, with the one revision that was pinned for the run: %s' % refs)

    def test_a_larger_tier_always_buys_strictly_more_than_the_need(self):
        m = TestLandedEdges().world(steel(), tiers=[['Q-1', '10', '262000'], ['Q-1', '50', '261000']], terms=[['Q-1', 'moq', '4'], ['Q-1', 'pack_size', '3']])
        a = m.analysis()
        for need in (1 * M, 3 * M, 4 * M, 9 * M, 10 * M - 1, 49 * M, 100 * M):
            plan = LD.purchase_plan(a.F, a.mp, a.ctx.quotes['Q-1'], AS_OF_DAY, need)
            for o in plan['larger_orders']:
                self.assertGreater(o['buy_qty_micro'], need, 'need %d: a larger tier that buys no more than the need would not be a larger order' % need)

    def test_a_purchase_order_view_carries_the_key_it_is_listed_under(self):
        m = mkt_world()
        m.pos(pom('PO-1'), pom('PO-2', date='2026-08-05'), pom('PO-3', date='2026-08-05'))
        ctx = m.ctx()
        self.assertTrue(ctx.pos)
        for k, po in ctx.pos.items():
            self.assertEqual(po['key'], k)


if __name__ == '__main__':
    unittest.main()
