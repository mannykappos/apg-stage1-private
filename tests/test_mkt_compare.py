import copy, unittest
from . import _path                                         # noqa: F401
from .helpers_mkt import *
from apg.mkt import compare as CP


def cq(qid, mat='MAT-CONC40', rate='34000', issue='2026-09-10', valid='2026-12-31', basis='delivered', sup='SUP-001', freight='0', lead='7', cur='AUD', fx='', fxd=''):
    return quote(qid, sup, mat, 's', issue, valid, rate, cur, fx, fxd, freight, basis, lead)


def cread(qid, mat='MAT-CONC40', verified_by='alice'):
    strength = '32' if mat == 'MAT-CONC32' else '40'
    return [reading(qid, 'strength_mpa', strength, verified_by=verified_by), reading(qid, 'unit', 'm3', verified_by=verified_by)]


def world(quotes, readings_for=(), dem=True, **kw):
    m = mkt_world(**kw)
    m.quote_rows(*quotes)
    rows = []
    for q in quotes:
        if q[0] in readings_for:
            rows += cread(q[0], q[2])
    if rows:
        m.readings(*rows)
    if dem:
        m.demands(demand('DEM-1', 'PRJ-001', 'MAT-CONC40', '100', 'm3', '2026-12-01'))
    return m


def rank(m, decision='quote_ranking', qty=None, with_index=False, as_of='2026-09-30'):
    ctx = m.ctx(as_of=as_of)
    (req,) = [r for r in CP.requirements(ctx) if r['kind'] == 'demand']
    return CP.rank(ctx, req, decision, qty, with_index), ctx, req


class TestRanking(unittest.TestCase):
    def test_two_comparable_current_complete_offers_give_a_definitive_ranking_cheapest_first(self):
        m = world([cq('Q-A', rate='34000'), cq('Q-B', rate='33000', sup='SUP-002')], ('Q-A', 'Q-B'))
        r, _, _ = rank(m)
        self.assertEqual((r['status'], r['definitive'], r['outstanding']), ('definitive', True, []))
        self.assertEqual([(x['rank'], x['offer'], x['unit_cents'], x['label']) for x in r['ranking']], [(1, 'supplier_quote/Q-B', 33000, 'definitive'), (2, 'supplier_quote/Q-A', 34000, 'definitive')])
        self.assertTrue(r['human_approval_required'])
        self.assertEqual(CP.may_recommend(r), (True, []))

    def test_one_offer_is_never_a_ranking(self):
        m = world([cq('Q-A')], ('Q-A',))
        r, _, _ = rank(m)
        self.assertEqual((r['status'], r['definitive']), ('insufficient_offers', False))
        self.assertEqual(r['ranking'][0]['label'], 'single_offer')
        ok, why = CP.may_recommend(r)
        self.assertFalse(ok)
        self.assertIn('fewer than two offers can be ranked', why[0])

    def test_no_quote_is_no_offers(self):
        m = world([], ())
        r, _, _ = rank(m)
        self.assertEqual((r['status'], r['ranking'], r['definitive']), ('no_offers', [], False))
        self.assertFalse(CP.may_recommend(r)[0])

    def test_a_cheaper_offer_for_the_wrong_specification_is_excluded_and_explained_and_does_not_win(self):
        m = world([cq('Q-A', rate='34000'), cq('Q-B', rate='33000', sup='SUP-002'), cq('Q-C', mat='MAT-CONC32', rate='27000', sup='SUP-003')], ('Q-A', 'Q-B', 'Q-C'))
        r, _, _ = rank(m)
        self.assertEqual([x['offer'] for x in r['ranking']], ['supplier_quote/Q-B', 'supplier_quote/Q-A'])
        (ex,) = r['excluded']
        self.assertEqual((ex['offer'], ex['class']), ('supplier_quote/Q-C', 'not_comparable'))
        self.assertIn('strength_mpa', ' '.join(ex['why']))
        self.assertTrue(CP.may_recommend(r)[0])                                              # the remaining two are clean; the excluded one is explained, not hidden

    def test_a_partially_comparable_offer_makes_the_whole_ranking_indicative(self):
        m = world([cq('Q-A', rate='34000'), cq('Q-B', rate='33000', sup='SUP-002')], ('Q-A',))
        r, _, _ = rank(m)
        self.assertEqual(r['status'], 'indicative')
        self.assertTrue(any('GATE:partially_comparable' in x for x in r['outstanding']))
        self.assertEqual(r['ranking'][0]['label'], 'indicative')
        ok, why = CP.may_recommend(r)
        self.assertFalse(ok)
        self.assertTrue(why)

    def test_an_expired_offer_is_history_not_a_ranked_offer_even_when_it_is_the_cheapest(self):
        m = world([cq('Q-A', rate='34000'), cq('Q-B', rate='33000', sup='SUP-002'), cq('Q-X', rate='20000', sup='SUP-003', issue='2026-03-01', valid='2026-06-30')], ('Q-A', 'Q-B', 'Q-X'))
        r, _, _ = rank(m)
        self.assertEqual([x['offer'] for x in r['ranking']], ['supplier_quote/Q-B', 'supplier_quote/Q-A'])
        self.assertEqual([(e['offer'], e['qualification']) for e in r['excluded']], [('supplier_quote/Q-X', 'historical_only')])
        self.assertTrue(any('expired' in w for e in r['excluded'] for w in e['why']))

    def test_a_stale_offer_is_ranked_but_qualified_so_the_ranking_is_indicative(self):
        m = world([cq('Q-A', rate='34000'), cq('Q-B', rate='33000', sup='SUP-002', issue='2026-07-01')], ('Q-A', 'Q-B'))
        r, _, _ = rank(m)
        self.assertEqual(r['status'], 'indicative')
        self.assertIn('supplier_quote/Q-B: FRESHNESS:qualified', r['outstanding'])

    def test_the_freshness_threshold_belongs_to_the_decision(self):
        m = world([cq('Q-A', rate='34000', issue='2026-08-21'), cq('Q-B', rate='33000', sup='SUP-002', issue='2026-08-21')], ('Q-A', 'Q-B'))      # 40 days old
        self.assertEqual(rank(m, 'quote_ranking')[0]['status'], 'definitive')              # limit 45
        self.assertEqual(rank(m, 'buy_timing')[0]['status'], 'indicative')                  # limit 30
        self.assertEqual(rank(m, 'benchmark')[0]['status'], 'definitive')                   # limit 90

    def test_a_stale_market_index_blocks_a_definitive_buy_timing_ranking_only_when_the_index_is_part_of_the_question(self):
        m = world([cq('Q-A', rate='34000'), cq('Q-B', rate='33000', sup='SUP-002')], ('Q-A', 'Q-B'))
        m.observations(obs('O1', 'MAT-CONC40', '2026-03-01'))
        self.assertEqual(rank(m, 'buy_timing', with_index=False)[0]['status'], 'definitive')
        r = rank(m, 'buy_timing', with_index=True)[0]
        self.assertEqual(r['status'], 'indicative')
        self.assertTrue(any('FRESHNESS:qualified' in x for x in r['outstanding']))

    def test_incomplete_landed_cost_makes_the_ranking_indicative(self):
        m = world([cq('Q-A', rate='34000'), cq('Q-B', rate='33000', sup='SUP-002', basis='ex-works', freight='')], ('Q-A', 'Q-B'))
        r, _, _ = rank(m)
        self.assertEqual(r['status'], 'indicative')
        self.assertIn('supplier_quote/Q-B: LANDED_COST_INCOMPLETE', r['outstanding'])

    def test_equal_landed_costs_are_ordered_by_offer_reference_so_the_result_is_reproducible(self):
        m = world([cq('Q-B', rate='33000', sup='SUP-002'), cq('Q-A', rate='33000')], ('Q-A', 'Q-B'))
        r, _, _ = rank(m)
        self.assertEqual([x['offer'] for x in r['ranking']], ['supplier_quote/Q-A', 'supplier_quote/Q-B'])

    def test_a_clean_international_offer_can_be_definitive_only_when_every_gate_is_passed(self):
        stl = lambda qid, **k: quote(qid, k.pop('sup', 'SUP-004'), 'MAT-STEEL', 's', '2026-09-10', '2026-12-31', k.pop('rate', '6900'), 'USD', '0.6540', '2026-09-30', '800', 'FOB', '28')
        m = mkt_world()
        m.quote_rows(stl('Q-I'), quote('Q-D', 'SUP-001', 'MAT-STEEL', 's', '2026-09-10', '2026-12-31', '14000', basis='delivered'))
        m.fx(fxrow('2026-09-30', '0.6540'))
        m.readings(*(std_readings('Q-I') + std_readings('Q-D')))
        m.demands(demand())
        ctx = m.ctx()
        (req,) = CP.requirements(ctx)
        r = CP.rank(ctx, req, 'quote_ranking')
        self.assertEqual(r['status'], 'indicative')                                          # insurance, duty, clearance missing and the checks unrecorded
        m.assumptions(*[['Q-I', c, '10', '', 'USD', 'allowance', 'none', 'alice', '2026-09-20'] for c in ('insurance', 'clearance')], ['Q-I', 'duty', '', '300', '', 'rate', 'none', 'alice', '2026-09-20'])
        r = CP.rank(m.ctx(), req, 'quote_ranking')
        self.assertIn('supplier_quote/Q-I: INTERNATIONAL_CHECKS_UNRESOLVED', r['outstanding'])
        self.assertNotIn('supplier_quote/Q-I: LANDED_COST_INCOMPLETE', r['outstanding'])
        m.checks(*[['Q-I', c, 'resolved', 'EV-%s' % c, 'carol', '2026-09-25'] for c in ('customs_classification', 'duty_rate_confirmed', 'import_permit')])
        r = CP.rank(m.ctx(), req, 'quote_ranking')
        self.assertEqual((r['status'], r['outstanding']), ('definitive', []))
        self.assertTrue(CP.may_recommend(r)[0])

    def test_a_resolved_import_check_without_evidence_does_not_count(self):
        from apg.mkt import intl as IN
        m = mkt_world()
        m.quote_rows(quote('Q-I', 'SUP-004', 'MAT-STEEL', 's', '2026-09-10', '2026-12-31', '6900', 'USD', '0.6540', '2026-09-30', '800', 'FOB', '28'))
        m.checks(['Q-I', 'customs_classification', 'resolved', '', 'carol', '2026-09-25'], ['Q-I', 'duty_rate_confirmed', 'resolved', 'EV', '', '2026-09-25'],
                 ['Q-I', 'import_permit', 'not_applicable', '', '', ''], ['Q-I', 'supplier_vetting', 'maybe', 'EV', 'carol', '2026-09-25'])
        a = m.analysis()
        c = IN.checks(a.F, a.mp, a.ctx.quotes['Q-I'])
        self.assertEqual(c['unresolved_critical'], ['customs_classification', 'duty_rate_confirmed', 'import_permit'])
        self.assertEqual({r['check']: r['status'] for r in c['checks']}, {'customs_classification': 'unresolved', 'duty_rate_confirmed': 'unresolved', 'import_permit': 'unresolved', 'supplier_vetting': 'unresolved'})
        self.assertIn('not one of', [r for r in c['checks'] if r['check'] == 'supplier_vetting'][0]['why'])

    def test_not_applicable_needs_a_person_and_a_date_and_then_counts_as_resolved(self):
        from apg.mkt import intl as IN
        m = mkt_world()
        m.quote_rows(quote('Q-I', 'SUP-004', 'MAT-STEEL', 's', '2026-09-10', '2026-12-31', '6900', 'USD', '0.6540', '2026-09-30', '800', 'FOB', '28'))
        m.checks(['Q-I', 'import_permit', 'not_applicable', '', 'carol', '2026-09-25'])
        a = m.analysis()
        c = IN.checks(a.F, a.mp, a.ctx.quotes['Q-I'])
        self.assertEqual({r['check']: r['status'] for r in c['checks']}['import_permit'], 'not_applicable')
        self.assertNotIn('import_permit', c['unresolved_critical'])
        self.assertIn('does not decide', c['note'])

    def test_a_critical_check_missing_from_the_configured_list_is_still_unresolved(self):
        from apg.mkt import intl as IN
        f = DM.demo_mkt_fields()
        f['international'] = {'critical_checks': ['customs_classification', 'dangerous_goods'], 'checks': ['customs_classification']}
        m = mkt_world()
        m.set_mkt(**f)
        m.quote_rows(quote('Q-I', 'SUP-004', 'MAT-STEEL', 's', '2026-09-10', '2026-12-31', '6900', 'USD', '0.6540', '2026-09-30', '800', 'FOB', '28'))
        m.checks(['Q-I', 'customs_classification', 'resolved', 'EV', 'carol', '2026-09-25'])
        a = m.analysis()
        c = IN.checks(a.F, a.mp, a.ctx.quotes['Q-I'])
        self.assertEqual((c['unresolved_critical'], c['unlisted_critical']), (['dangerous_goods'], ['dangerous_goods']))

    def test_may_recommend_refuses_a_ranking_whose_offer_carries_a_blocker_even_if_the_status_says_definitive(self):
        m = world([cq('Q-A', rate='34000'), cq('Q-B', rate='33000', sup='SUP-002')], ('Q-A', 'Q-B'))
        r, _, _ = rank(m)
        bad = copy.deepcopy(r)
        bad['offers'][0]['blockers'] = ['FRESHNESS:qualified']
        ok, why = CP.may_recommend(bad)
        self.assertFalse(ok)
        self.assertIn('FRESHNESS:qualified', why[0])
        bad2 = copy.deepcopy(r)
        bad2['definitive'] = False
        self.assertFalse(CP.may_recommend(bad2)[0])
        for st in ('indicative', 'insufficient_offers', 'no_offers'):
            self.assertFalse(CP.may_recommend(dict(r, status=st))[0], st)

    def test_ranking_never_places_a_substitute_without_flagging_it(self):
        m = mkt_world()
        m.quote_rows(cq('Q-A', mat='MAT-CONC32', rate='30000'), cq('Q-B', mat='MAT-CONC32', rate='31000', sup='SUP-002'))
        m.readings(*(cread('Q-A', 'MAT-CONC32') + cread('Q-B', 'MAT-CONC32')))
        m.demands(demand('DEM-1', 'PRJ-001', 'MAT-CONC32', '10', 'm3', '2026-12-01'))
        r, _, _ = rank(m)
        self.assertEqual(r['status'], 'definitive')                                          # same material: no substitution
        m2 = mkt_world()
        m2.quote_rows(cq('Q-A', mat='MAT-CONC40', rate='30000'), cq('Q-B', mat='MAT-CONC40', rate='31000', sup='SUP-002'))
        m2.readings(*(cread('Q-A') + cread('Q-B')))
        m2.demands(demand('DEM-1', 'PRJ-001', 'MAT-CONC32', '10', 'm3', '2026-12-01'))
        r2, _, _ = rank(m2)
        self.assertEqual(r2['status'], 'indicative')
        self.assertTrue(all('SUBSTITUTION_NEEDS_APPROVAL' in o['blockers'] for o in r2['offers']))


class TestLastPaid(unittest.TestCase):
    def ref(self, m, project='PRJ-001', material='MAT-STEEL'):
        ctx = m.ctx(project)
        req = {'id': 'x', 'project': project, 'material': material, 'approved': True, 'kind': 'demand'}
        return CP.last_paid(ctx, req)

    def test_the_most_recent_committed_order_for_the_project_and_material_is_the_reference(self):
        m = mkt_world()
        m.orders(pom('PO-1', date='2026-06-01', rate='250000'), pom('PO-2', date='2026-08-01', rate='260000'), pom('PO-3', date='2026-07-01', rate='999999'))
        r = self.ref(m)
        self.assertEqual((r['offer']['key'], r['landed']['unit_cents'], r['offer']['order_date']), ('PO-2', 260000, '2026-08-01'))

    def test_other_projects_other_materials_drafts_and_cancelled_orders_are_not_the_reference(self):
        m = mkt_world()
        m.orders(pom('PO-1', project='PRJ-002', date='2026-09-01', rate='1'), pom('PO-2', mat='MAT-CONC40', unit='m3', date='2026-09-01', rate='2'), pom('PO-3', date='2026-09-02', rate='3', status='draft'),
                 pom('PO-4', date='2026-09-03', rate='4', status='cancelled'), pom('PO-5', date='2026-05-01', rate='250000'))
        r = self.ref(m)
        self.assertEqual(r['offer']['key'], 'PO-5')

    def test_no_order_means_no_reference_and_never_a_zero_baseline(self):
        self.assertIsNone(self.ref(mkt_world()))

    def test_a_duplicate_candidate_order_counts_only_when_every_candidate_carries_the_same_rate(self):
        m = mkt_world()
        m.orders(pom('PO-1', date='2026-08-25', rate='185000', qty='13'), pom('PO-2', date='2026-08-25', rate='185000', qty='13'))
        r = self.ref(m)
        self.assertIsNotNone(r)
        self.assertEqual(r['landed']['unit_cents'], 185000)
        self.assertTrue(r['held_as_duplicate_candidate'])
        self.assertTrue(any('possible duplicate' in x for x in r['landed']['limits']))

    def test_a_reference_is_never_rankable(self):
        m = mkt_world()
        m.orders(pom('PO-1', date='2026-06-01', rate='250000'))
        r = self.ref(m)
        self.assertFalse(r['rankable'])
        self.assertEqual(r['blockers'], ['REFERENCE_ONLY'])


if __name__ == '__main__':
    unittest.main()
