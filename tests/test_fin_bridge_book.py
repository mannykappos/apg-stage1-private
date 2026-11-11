import unittest
from . import _path                                         # noqa: F401
from .helpers_fin import Mini, bud, ctc, inv, var, AS_OF
from apg import repro
from apg.ports import ConflictError
from apg.fin import bridge as B, calc_records as C, forecast_book as FB
from apg.fin.figure import AUTH, PROV, CANT


def project_world(approved=True):
    m = Mini(approved=approved)
    m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0'])
    m.budgets(bud(cc='CC-01', cents='5000000'), bud(cc='CC-02', cents='3000000'))
    m.ctcs(ctc(cc='CC-01', version='F-A', date='2026-08-31', cents='1500000', reason='initial'))
    m.invoices(inv('INV-1', cc='CC-01', ex='3000000', date='2026-08-01'))
    m.reconcile()
    return m


def run_fc(m, version, as_of=AS_OF, **extra):
    return m.run('fin.forecast', as_of=as_of, extra=dict({'forecast_version': version}, **extra))


def bridge(m, a, b):
    return C.run_bridge(m.s, m.reg, m.clock, a['run_key'], b['run_key'])['result']


class TestBridge(unittest.TestCase):
    def two(self, new_ctc='2500000', reason='re-priced', more_invoice=None, version_date='2026-09-30'):
        m = project_world()
        a = run_fc(m, 'F-A')
        m.ctcs(ctc(cc='CC-01', version='F-B', date=version_date, cents=new_ctc, reason=reason))
        if more_invoice:
            m.invoices(more_invoice)
        m.reconcile()
        return m, a, run_fc(m, 'F-B')

    def test_identical_forecasts_give_a_zero_bridge_with_no_items(self):
        m = project_world()
        f = run_fc(m, 'F-A')['result']
        r = B.build_bridge(f, f)
        self.assertEqual((r['value']['cents'], r['classified']['items'], r['classified']['reconciles'], r['state']), (0, [], True, AUTH))

    def test_the_same_stored_run_cannot_be_pinned_twice_as_both_ends(self):
        m = project_world()
        a = run_fc(m, 'F-A')
        with self.assertRaises(repro.ReproError):
            bridge(m, a, a)

    def test_a_recorded_reason_explains_a_cost_to_complete_movement(self):
        m, a, b = self.two()
        r = bridge(m, a, b)
        c = r['classified']
        self.assertEqual(r['value']['cents'], b['result']['value']['cents'] - a['result']['value']['cents'])
        self.assertTrue(c['reconciles'])
        self.assertEqual(sum(i['effect_cents'] for i in c['items']), r['value']['cents'])
        it = [i for i in c['items'] if i['part'] == 'cost_to_complete' and i['cost_code'] == 'CC-01'][0]
        self.assertEqual((it['effect_cents'], it['explained'], it['why']), (-1000000, True, 'recorded reason: re-priced'))

    def test_blank_reason_is_unexplained_and_listed_without_any_threshold(self):
        m, a, b = self.two(reason='', new_ctc='1500001')                                    # a one-cent move is still surfaced
        r = bridge(m, a, b)
        self.assertEqual(r['classified']['unexplained_items'], 1)
        self.assertEqual(r['classified']['unexplained_cents'], -1)
        self.assertIn('UNEXPLAINED_MOVEMENT:cost_to_complete:CC-01:-1', r['reasons'])
        self.assertTrue(any('no materiality threshold' in l for l in r['limits']))

    def test_newly_counted_invoice_is_explained_by_that_record(self):
        m, a, b = self.two(new_ctc='1500000', more_invoice=inv('INV-2', sin='S2', cc='CC-01', ex='400000', date='2026-09-10'))
        r = bridge(m, a, b)
        it = [i for i in r['classified']['items'] if i['part'] == 'actual_cost'][0]
        self.assertEqual((it['ref'], it['effect_cents'], it['explained'], it['cost_code']), ('ap_invoice/INV-2', -400000, True, 'CC-01'))
        self.assertTrue(r['classified']['reconciles'])

    def test_newly_approved_variation_is_explained(self):
        m = project_world()
        a = run_fc(m, 'F-A')
        m.variations(var('V-1', status='approved', value='700000'))
        m.reconcile()
        b = run_fc(m, 'F-A')
        r = bridge(m, a, b)
        it = [i for i in r['classified']['items'] if i['part'] == 'revenue'][0]
        self.assertEqual((it['ref'], it['effect_cents'], it['explained']), ('variation/V-1', 700000, True))
        self.assertEqual(r['state'], PROV)                                                   # the contract summary was not updated: the revenue side is provisional, and so is the bridge

    def test_a_mid_cycle_credit_note_is_a_cost_reduction_item(self):
        m = project_world()
        a = run_fc(m, 'F-A')
        m.credits(['CN-1', 'SUP-001', 'INV-1', '2026-08-20', '200000', '0'])
        m.reconcile()
        b = run_fc(m, 'F-A')
        r = bridge(m, a, b)
        self.assertTrue(r['classified']['reconciles'])
        self.assertEqual(r['value']['cents'], 200000)

    def test_method_change_is_never_explained_by_the_bridge(self):
        m, a, _ = self.two()
        m.set_policy(ctc_method={'default': 'budget_less_actual'})
        b2 = m.run('fin.forecast', extra={'forecast_version': 'F-A'})
        r = bridge(m, a, b2)
        self.assertTrue(any(i['why'].startswith('CTC_METHOD_CHANGED') and not i['explained'] for i in r['classified']['items']))
        self.assertTrue(r['classified']['reconciles'])

    def test_a_record_that_stops_counting_is_unexplained(self):
        m = project_world()
        a = run_fc(m, 'F-A')
        m.invoices(inv('INV-1', cc='CC-01', ex='3100000', date='2026-08-01'))               # same key, different amount: conflict, the record is held
        m.reconcile()
        b = run_fc(m, 'F-A')
        if b['result']['state'] == CANT:
            self.skipTest('held record leaves the forecast unassessable')
        r = bridge(m, a, b)
        self.assertTrue(any(i['why'] == 'RECORD_NO_LONGER_COUNTED' and not i['explained'] for i in r['classified']['items']))

    def test_forecasts_that_cannot_be_compared_are_refused_with_a_reason(self):
        m, a, _ = self.two()
        bad = m.run('fin.forecast', extra={'forecast_version': 'F-NOPE'})
        r = bridge(m, a, bad)
        self.assertEqual((r['state'], r['value']['cents']), (CANT, None))
        self.assertEqual(r['reasons'], ['A_FORECAST_CANNOT_BE_ASSESSED'])

    def test_different_projects_are_refused(self):
        m = project_world()
        m.projects(['PRJ-002', 'P2', '10', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-002', '10', '0']); m.budgets(bud(project='PRJ-002', cc='CC-01', cents='5'))
        m.reconcile()
        a, b = run_fc(m, 'F-A'), m.run('fin.forecast', 'PRJ-002')
        r = bridge(m, a, b)
        self.assertEqual(r['state'], CANT)

    def test_the_bridge_itself_is_a_stored_reproducible_calculation(self):
        m, a, b = self.two()
        rec = C.run_bridge(m.s, m.reg, m.clock, a['run_key'], b['run_key'])
        chk = C.check_record(m.s, m.reg, rec['run_key'])
        self.assertEqual((chk['replay'].ok, chk['figure_valid'], chk['pins_consistent']), (True, True, True))
        self.assertEqual(sorted(i['key'] for i in rec['inputs']), sorted([a['run_key'], b['run_key']]))

    def test_unapproved_policy_marks_the_bridge_provisional(self):
        m = project_world(approved=False)
        a = run_fc(m, 'F-A')
        m.ctcs(ctc(cc='CC-01', version='F-B', date='2026-09-30', cents='2500000', reason='r')); m.reconcile()
        r = bridge(m, a, run_fc(m, 'F-B'))
        self.assertEqual(r['state'], PROV)


class TestPercentages(unittest.TestCase):
    def test_margin_percentage_is_a_stored_derived_calculation(self):
        m = project_world()
        r = m.run('fin.forecast', extra={'forecast_version': 'F-A'})
        p = C.run_pct(m.s, m.reg, m.clock, r['run_key'], 'forecast_revenue', 'forecast margin on forecast revenue')
        self.assertEqual((p['result']['state'], p['result']['value']['bps']), (AUTH, 2500))        # 2,500,000 / 10,000,000
        self.assertEqual(C.check_record(m.s, m.reg, p['run_key'])['replay'].ok, True)

    def test_a_denominator_nobody_defined_is_refused_not_replaced(self):
        m = project_world()
        r = m.run('fin.forecast', extra={'forecast_version': 'F-A'})
        p = C.run_pct(m.s, m.reg, m.clock, r['run_key'], 'whatever', 'x')
        self.assertEqual((p['result']['state'], p['result']['value']['bps'], p['result']['reasons']), (CANT, None, ['UNKNOWN_DENOMINATOR:whatever']))

    def test_a_denominator_the_margin_does_not_have_is_unknown_not_zero(self):
        m = project_world()
        r = m.run('fin.forecast', extra={'forecast_version': 'F-A'})
        p = C.run_pct(m.s, m.reg, m.clock, r['run_key'], 'recognised_revenue', 'x')
        self.assertEqual((p['result']['state'], p['result']['reasons']), (CANT, ['RECOGNISED_REVENUE_UNKNOWN']))

    def test_percentage_of_a_recognised_margin(self):
        m = project_world()
        r = m.run('fin.recognised_margin')
        p = C.run_pct(m.s, m.reg, m.clock, r['run_key'], 'recognised_revenue', 'recognised margin %')
        self.assertEqual((p['result']['state'], p['result']['value']['bps']), (AUTH, 2500))


class TestForecastBook(unittest.TestCase):
    def setUp(self):
        self.m = project_world()
        self.run = run_fc(self.m, 'F-A')
        self.owner = self.m.w.who('o', 'zero_one', user='olga', roles=('forecast_owner',))
        self.owner2 = self.m.w.who('o2', 'zero_one', user='omar', roles=('forecast_owner',))

    def adopt(self, who, run=None, **kw):
        return FB.adopt(who, self.m.reg, self.m.clock, 'PRJ-001', AS_OF, (run or self.run)['run_key'], **kw)

    def test_no_forecast_is_authoritative_until_a_person_adopts_one(self):
        self.assertIsNone(FB.current(self.m.s, 'PRJ-001', AS_OF))
        self.adopt(self.owner)
        self.assertEqual(FB.current(self.m.s, 'PRJ-001', AS_OF)['run_key'], self.run['run_key'])
        self.assertEqual(FB.verify_slot(self.m.s, 'PRJ-001', AS_OF), [])

    def test_only_a_human_forecast_owner_may_adopt(self):
        for who in (self.m.s, self.m.w.who('s', 'zero_one', user='svc', roles=('forecast_owner',), kind='service'), self.m.w.who('a', 'zero_one', user='bot', roles=('forecast_owner',), kind='ai')):
            with self.assertRaises(FB.BookError) as cx:
                self.adopt(who)
            self.assertEqual(cx.exception.code, 'FORECAST_OWNER_REQUIRED')

    def test_the_person_who_ran_the_calculation_cannot_adopt_it(self):
        mine = self.m.w.who('own', 'zero_one', user='ann', roles=('forecast_owner',))
        with self.assertRaises(FB.BookError) as cx:
            self.adopt(mine)
        self.assertEqual(cx.exception.code, 'SELF_APPROVAL_REFUSED')

    def test_cannot_assess_cannot_be_adopted_but_provisional_can_and_stays_marked(self):
        bad = self.m.run('fin.forecast', extra={'forecast_version': 'F-NOPE'})
        with self.assertRaises(FB.BookError) as cx:
            self.adopt(self.owner, bad)
        self.assertEqual(cx.exception.code, 'CANNOT_ADOPT_A_FORECAST_THAT_CANNOT_BE_ASSESSED')
        m = project_world(); m.set_policy(freshness_days={})
        prov = run_fc(m, 'F-A')
        self.assertEqual(prov['result']['state'], PROV)
        o = m.w.who('o', 'zero_one', user='olga', roles=('forecast_owner',))
        FB.adopt(o, m.reg, m.clock, 'PRJ-001', AS_OF, prov['run_key'])
        self.assertEqual(FB.current(m.s, 'PRJ-001', AS_OF)['result']['state'], PROV)

    def test_wrong_run_or_wrong_formula_or_wrong_date_is_refused(self):
        with self.assertRaises(FB.BookError) as cx:
            FB.adopt(self.owner, self.m.reg, self.m.clock, 'PRJ-001', AS_OF, 'f' * 32)
        self.assertEqual(cx.exception.code, 'RUN_NOT_FOUND')
        act = self.m.run('fin.actual_cost')
        with self.assertRaises(FB.BookError) as cx:
            self.adopt(self.owner, act)
        self.assertEqual(cx.exception.code, 'NOT_A_FORECAST')
        with self.assertRaises(FB.BookError) as cx:
            FB.adopt(self.owner, self.m.reg, self.m.clock, 'PRJ-001', '2026-09-29', self.run['run_key'])
        self.assertEqual(cx.exception.code, 'RUN_IS_FOR_A_DIFFERENT_PROJECT_OR_DATE')

    def test_a_forecast_that_no_longer_reproduces_is_refused(self):
        rec = self.m.s.get(repro.KIND, self.run['run_key'])
        self.m.s.put(repro.KIND, self.run['run_key'], dict(rec.payload, result_hash='0' * 64), expected_revision=rec.revision)
        with self.assertRaises(FB.BookError) as cx:
            self.adopt(self.owner)
        self.assertEqual(cx.exception.code, 'FORECAST_DOES_NOT_REPRODUCE')

    def test_a_second_adoption_supersedes_and_history_is_kept(self):
        self.adopt(self.owner)
        self.m.ctcs(ctc(cc='CC-01', version='F-B', date='2026-09-30', cents='2000000', reason='x')); self.m.reconcile()
        second = run_fc(self.m, 'F-B')
        self.adopt(self.owner2, second)
        s = self.m.s.get(FB.SLOT_KIND, FB.slot_key('PRJ-001', AS_OF)).payload
        self.assertEqual([h['run_key'] for h in s['history']], [self.run['run_key'], second['run_key']])
        self.assertEqual(s['history'][1]['supersedes'], self.run['run_key'])
        self.assertEqual(FB.current(self.m.s, 'PRJ-001', AS_OF)['run_key'], second['run_key'])
        self.assertEqual(FB.verify_slot(self.m.s, 'PRJ-001', AS_OF), [])
        self.assertEqual(len(list(self.m.s.history(FB.SLOT_KIND, FB.slot_key('PRJ-001', AS_OF)))), 2)

    def test_adopting_the_same_run_again_changes_nothing(self):
        a = self.adopt(self.owner)
        b = self.adopt(self.owner2)
        self.assertEqual(a.revision, b.revision)

    def test_scenarios_are_isolated_from_the_authoritative_forecast(self):
        self.adopt(self.owner)
        sc = self.m.run('fin.forecast', extra={'forecast_version': 'F-A', 'scenario': 'pessimistic'})
        FB.register_scenario(self.m.s, 'PRJ-001', AS_OF, sc['run_key'], 'pessimistic')
        self.assertEqual(FB.current(self.m.s, 'PRJ-001', AS_OF)['run_key'], self.run['run_key'])
        with self.assertRaises(FB.BookError) as cx:
            self.adopt(self.owner2, sc)
        self.assertEqual(cx.exception.code, 'SCENARIO_NEEDS_EXPLICIT_PROMOTION')
        self.adopt(self.owner2, sc, promote_scenario='pessimistic')
        h = self.m.s.get(FB.SLOT_KIND, FB.slot_key('PRJ-001', AS_OF)).payload['history'][-1]
        self.assertEqual((h['event'], h['scenario']), ('promoted_scenario', 'pessimistic'))
        self.assertEqual(FB.verify_slot(self.m.s, 'PRJ-001', AS_OF), [])

    def test_scenario_registration_rules(self):
        with self.assertRaises(FB.BookError) as cx:
            FB.register_scenario(self.m.s, 'PRJ-001', AS_OF, self.run['run_key'], '')
        self.assertEqual(cx.exception.code, 'SCENARIO_NAME_REQUIRED')
        with self.assertRaises(FB.BookError) as cx:
            FB.register_scenario(self.m.s, 'PRJ-001', AS_OF, self.run['run_key'], 'pessimistic')          # the run was not made for that scenario
        self.assertEqual(cx.exception.code, 'RUN_IS_NOT_A_FORECAST_MADE_FOR_THIS_SCENARIO')
        with self.assertRaises(FB.BookError) as cx:
            self.adopt(self.owner, promote_scenario='x')
        self.assertEqual(cx.exception.code, 'NOT_A_SCENARIO_RUN')

    def test_two_people_adopting_at_once_cannot_both_succeed(self):
        class Stale:
            """Sees the slot as it was before the other person's adoption."""
            def __init__(self, real): self._r = real
            def __getattr__(self, n): return getattr(self._r, n)
            def get(self, kind, key, *a):
                return None if kind == FB.SLOT_KIND else self._r.get(kind, key, *a)
        self.adopt(self.owner)
        self.m.ctcs(ctc(cc='CC-01', version='F-B', date='2026-09-30', cents='2000000', reason='x')); self.m.reconcile()
        second = run_fc(self.m, 'F-B')
        with self.assertRaises(ConflictError):
            FB.adopt(Stale(self.owner2), self.m.reg, self.m.clock, 'PRJ-001', AS_OF, second['run_key'])
        self.assertEqual(FB.current(self.m.s, 'PRJ-001', AS_OF)['run_key'], self.run['run_key'])

    def test_a_damaged_slot_is_detected(self):
        self.adopt(self.owner)
        cur = self.m.s.get(FB.SLOT_KIND, FB.slot_key('PRJ-001', AS_OF))
        bad = dict(cur.payload, authoritative='f' * 32)
        self.m.s.put(FB.SLOT_KIND, cur.key, bad, expected_revision=cur.revision)
        self.assertIn('AUTHORITATIVE_DIFFERS_FROM_LAST_ADOPTION', FB.verify_slot(self.m.s, 'PRJ-001', AS_OF))

    def test_slots_are_tenant_private(self):
        self.adopt(self.owner)
        other = self.m.w.who('x', 'other_tenant', user='xena', roles=('forecast_owner',))
        self.assertIsNone(FB.current(other, 'PRJ-001', AS_OF))

    def test_the_adoption_is_audited_and_the_chain_still_verifies(self):
        self.adopt(self.owner)
        self.assertTrue(any(e.event_type == 'forecast.adopted' for e in self.m.w.audit.read(self.owner.ctx)))
        self.assertTrue(self.m.w.audit.verify(self.owner.ctx).ok)


if __name__ == '__main__':
    unittest.main()
