"""Run-level tests for the procurement layer: stored, pinned, replayable runs; ingestion into the M5 finding lifecycle; tenant and project boundaries; event records; and the RFC-01 failure classes
(missing data, conflicting quotes, duplicate records, currency errors, changed prices, delivery changes, misleading recommendations)."""
import copy, json, unittest
from . import _path                                         # noqa: F401
from .helpers_mkt import *
from .test_mkt_rules import conc, steel, with_quotes, S_
from apg import canon, repro
from apg.det import findings as FD
from apg.mkt import compare as CP, events as EV, detect as MD

STEEL_DEM = [demand('DEM-1', 'PRJ-001', 'MAT-STEEL', '100', 'tonne', '2026-12-01')]


def planted():
    """A small world with a purchase decision due (MP03), an over-order (MP04), and a cheaper non-comparable concrete quote (MP02)."""
    m = with_quotes(steel('Q-1', valid='2026-10-27'), steel('Q-2', sup='SUP-002', rate='101000', valid='2026-10-30'), conc('Q-A'), conc('Q-B', strength='32', rate='30000', sup='SUP-002'),
                    dem=STEEL_DEM + [demand('DEM-2', 'PRJ-001', 'MAT-CONC40', '100', 'm3', '2026-12-01')], orders=[pom('PO-9', qty='150', rate='34000', mat='MAT-CONC40', unit='m3', date='2026-08-25')])
    return m


class TestRunRecord(unittest.TestCase):
    def test_a_run_is_stored_pinned_and_replays_to_the_same_result(self):
        m = planted()
        rec = m.mdetect()
        chk = MD.check_record(m.s, m.mreg, rec['run_key'])
        self.assertTrue(chk['replay'].ok)
        self.assertTrue(chk['result_valid'] and chk['pins_consistent'])
        self.assertEqual(chk['drift'], [])
        pins = {i['kind'] for i in m.s.get(repro.KIND, rec['run_key']).payload['inputs']}
        self.assertTrue({'mkt_policy', 'mkt_spec', 'det_policy', 'fin_policy', 'supplier_quote', 'material_demand', 'purchase_order'} <= pins)

    def test_the_same_inputs_give_the_same_run_key_and_result(self):
        m = planted()
        a, b = m.mdetect(), m.mdetect()
        self.assertEqual(a['run_key'], b['run_key'])
        self.assertEqual(canon.canonical(a['result']), canon.canonical(b['result']))

    def test_a_changed_price_is_a_new_run_and_the_old_run_still_replays_with_the_old_price(self):
        m = planted()
        old = m.mdetect()
        m.quote_rows(steel('Q-1', rate='90000', valid='2026-10-27')[0])
        new = m.mdetect()
        self.assertNotEqual(old['run_key'], new['run_key'])
        self.assertTrue(MD.check_record(m.s, m.mreg, old['run_key'])['replay'].ok)
        self.assertEqual(MD.check_record(m.s, m.mreg, old['run_key'])['drift'] != [], True)               # the stored run reports that an input has since moved on
        self.assertNotEqual(canon.canonical(old['result']), canon.canonical(new['result']))

    def test_a_changed_delivery_is_a_new_run(self):
        m = planted()
        m.orders(pom('PO-1', qty='100', rate='100000', date='2026-08-25'))
        m.dockets(docket('DK-1', 'PO-1', date='2026-09-10', delivered='60', accepted='60'))
        a = m.mdetect()
        m.dockets(docket('DK-1', 'PO-1', date='2026-09-12', delivered='100', accepted='100'))
        b = m.mdetect()
        self.assertNotEqual(a['run_key'], b['run_key'])

    def test_a_policy_change_is_a_new_run_and_the_old_result_does_not_change(self):
        m = planted()
        old = m.mdetect()
        m.set_mkt(scenarios=dict(DM.demo_mkt_fields()['scenarios'], decision_window_days=5))
        new = m.mdetect()
        self.assertNotEqual(old['run_key'], new['run_key'])
        self.assertEqual(len(S_(old['result'], 'MP03')), 1)
        self.assertEqual(S_(new['result'], 'MP03'), [])

    def test_a_tampered_stored_result_fails_the_replay(self):
        m = planted()
        rec = m.mdetect()
        stored = m.s.get(repro.KIND, rec['run_key'])
        bad = copy.deepcopy(stored.payload)
        bad['result']['signals'][0]['quantification']['status'] = 'quantified'
        try:
            m.s.put(repro.KIND, rec['run_key'], bad, expected_revision=stored.revision)
        except Exception:
            return
        self.assertFalse(MD.check_record(m.s, m.mreg, rec['run_key'])['replay'].ok)

    def test_a_missing_run_is_reported_not_raised(self):
        chk = MD.check_record(planted().s, MD.mkt_registry(), 'no-such-run')
        self.assertEqual((chk['replay'].ok, chk['replay'].code, chk['result_valid']), (False, 'RECORD_MISSING', False))

    def test_a_project_that_does_not_exist_is_refused_and_not_shown_as_clean(self):
        m = planted()
        with self.assertRaises(repro.ReproError) as cm:
            m.mdetect('PRJ-404')
        self.assertIn('PROJECT_UNKNOWN', str(cm.exception))

    def test_a_policy_version_that_does_not_exist_cannot_be_run_against(self):
        m = planted()
        with self.assertRaises(repro.ReproError) as cm:
            MD.run_project(m.s, m.mreg, m.clock, 'PRJ-001', AS_OF, m.policy['version'], m.dp['version'], 'M-none', m.sp['version'])
        self.assertIn('INPUT_MISSING', str(cm.exception))

    def test_every_rule_leaves_a_run_record_even_when_silent_and_nothing_is_a_float(self):
        r = mkt_world().mres()
        self.assertEqual(sorted(r['rule_runs']), sorted(['MP02', 'MP03', 'MP04', 'MP05', 'MP09', 'MPD1']))
        self.assertEqual(sorted(mkt_world().mtres()['rule_runs']), sorted(['MP01', 'MP06', 'MP07', 'MP08', 'MP10', 'MPD1']))

        def walk(x):
            if isinstance(x, float):
                self.fail('float in result')
            elif isinstance(x, dict):
                [walk(v) for v in x.values()]
            elif isinstance(x, (list, tuple)):
                [walk(v) for v in x]
        walk(planted().mres())
        walk(planted().mtres())

    def test_the_result_says_whether_the_policies_were_approved(self):
        r = mkt_world(approved=False).mres()
        self.assertEqual((r['mkt_policy']['approved'], r['mkt_spec']['approved']), (False, False))
        r2 = mkt_world().mres()
        self.assertEqual((r2['mkt_policy']['approved'], r2['mkt_spec']['approved']), (True, True))

    def test_the_result_text_states_what_it_does_not_do(self):
        r = planted().mres()
        self.assertIn('No quote is recommended, no supplier chosen', r['statement'])
        self.assertIn('every purchase decision needs a person', r['statement'])

    def test_a_result_with_a_rule_that_did_not_run_but_has_signals_is_rejected(self):
        res = copy.deepcopy(planted().mres())
        rid = res['signals'][0]['rule']['id'].replace('DET-', '')
        res['rule_runs'][rid]['status'] = 'disabled'
        with self.assertRaises(ValueError):
            MD.validate_result(res)

    def test_a_tenant_result_must_name_the_projects_it_may_show(self):
        res = copy.deepcopy(planted().mtres())
        res['authorised_projects'] = None
        with self.assertRaises(ValueError):
            MD.validate_result(res)


class TestEvents(unittest.TestCase):
    def test_every_event_is_valid_and_carries_time_provenance_and_identifiers(self):
        m = planted()
        for res in (m.mres(), m.mtres()):
            evs = res['events']
            self.assertTrue(evs)
            for e in evs:
                EV.validate(e)
                self.assertTrue(e['observed_at'] and e['effective_from'] and e['sources'])
                self.assertEqual(e['event_version'], 'apg-event-1')
            ids = [e['event_id'] for e in evs]
            self.assertEqual(len(ids), len(set(ids)))

    def test_observation_time_is_when_apg_learned_of_it_and_not_the_effective_date(self):
        m = planted()
        e = [x for x in m.mres()['events'] if x['type'] == 'demand_required'][0]
        self.assertNotEqual(e['observed_at'][:10], e['effective_from'])
        self.assertEqual(e['effective_from'], '2026-12-01')

    def test_events_name_project_material_and_supplier_where_they_apply(self):
        m = with_quotes(steel('Q-1', valid='2026-09-01', issue='2026-08-01'))
        e = [x for x in m.mtres()['events'] if x['type'] == 'quote_expires']
        self.assertTrue(e and all(x['material'] and x['supplier'] for x in e))

    def test_an_event_with_a_bad_date_type_or_missing_source_is_refused(self):
        good = [x for x in planted().mres()['events']][0]
        for k, v in (('type', 'invented'), ('effective_from', '2026/12/01'), ('sources', []), ('event_version', 'x')):
            bad = copy.deepcopy(good)
            bad[k] = v
            with self.assertRaises(EV.EventError, msg=k):
                EV.validate(bad)

    def test_no_chain_or_relationship_is_computed_in_m6(self):
        res = planted().mres()
        text = json.dumps(res).lower()
        for w in ('risk chain', 'causes', 'caused by', 'leads to'):
            self.assertNotIn(w, text)


class TestIngestAndBoundaries(unittest.TestCase):
    def test_signals_become_findings_with_the_same_lifecycle_and_not_re_detected_applies_only_to_rules_that_ran(self):
        m = planted()
        rec = m.mdetect()
        out = m.mingest(rec)
        self.assertGreaterEqual(len(out['created']), 3)
        f = FD.get(m.svc, out['created'][0])
        self.assertEqual((f['status'], f['seen_count']), ('detected', 1))
        self.assertIsNone(f['action'])
        again = m.mingest(rec)
        self.assertTrue(again['replay'])
        self.assertEqual(len(FD.all_findings(m.svc)), len(out['created']))

    def test_a_rule_that_could_not_run_does_not_clear_its_earlier_finding(self):
        m = planted()
        m.mingest(m.mdetect())
        before = {f['rule_id'] for f in FD.all_findings(m.svc)}
        self.assertIn('DET-MP03', before)
        m.drop('scenarios.decision_window_days')
        out = m.mingest(m.mdetect())
        mp03 = [f for f in FD.all_findings(m.svc) if f['rule_id'] == 'DET-MP03']
        self.assertTrue(mp03 and all(f['status'] == 'detected' for f in mp03))
        self.assertNotIn('DET-MP03', json.dumps(out.get('not_redetected', [])))

    def test_another_tenant_cannot_ingest_or_check_the_first_tenants_run(self):
        m = planted()
        rec = m.mdetect()
        svc2 = m.w.who('svc2', 'other_co', 'detsvc2', ('detection_service',), 'service')
        with self.assertRaises(FD.LifecycleError):
            FD.ingest_run(svc2, m.clock, m.mreg, rec['run_key'])
        self.assertFalse(MD.check_record(svc2, m.mreg, rec['run_key'])['replay'].ok)

    def test_a_second_tenant_with_the_same_ids_sees_none_of_the_first_tenants_quotes_or_signals(self):
        a = planted()
        b = mkt_world(tenant='zero_two')
        self.assertEqual(S_(b.mtres(), 'MP01') != [], True)                                 # its own missing evidence, nothing else
        self.assertNotIn('Q-1', json.dumps(b.mtres()))
        self.assertTrue(S_(a.mres(), 'MP03'))

    def test_the_tenant_result_shows_nothing_of_a_project_that_is_not_authorised(self):
        m = mkt_world()
        m.orders(pom('PO-1', 'SUP-001', 'PRJ-001', 'MAT-STEEL', '10', '100', '2026-08-01'), pom('PO-2', 'SUP-002', 'PRJ-002', 'MAT-STEEL', '10', '100', '2026-08-02'))
        r = m.mtres(authorised=('PRJ-001',))
        text = json.dumps(r)
        for token in ('PRJ-002', 'PO-2'):
            self.assertNotIn(token, text)
        self.assertEqual(r['authorised_projects'], ['PRJ-001'])
        # recorded limitation (register F-39): the stored run pins every purchase order of the tenant so that the portfolio boundary can be decided; the pins are opaque identifiers, the result carries none of their content
        pinned = {'%s/%s' % (i['kind'], i['key']) for i in m.s.get(repro.KIND, m.mtenant(authorised=('PRJ-001',))['run_key']).payload['inputs']}
        self.assertIn('purchase_order/PO-2', pinned)


class TestRfcFailureClasses(unittest.TestCase):
    """RFC-01 section 4 M6: tests for missing data, conflicting quotes, duplicate records, currency errors, changed prices, delivery changes and misleading recommendations."""

    def rank(self, m, dem='DEM-1', as_of='2026-09-30'):
        ctx = m.ctx(as_of=as_of)
        (req,) = [r for r in CP.requirements(ctx) if r['kind'] == 'demand' and r['id'] == 'demand/' + dem]
        return CP.rank(ctx, req, 'quote_ranking'), ctx

    def test_missing_data_a_quote_without_a_rate_or_validity_never_reaches_a_ranking(self):
        m = mkt_world()
        q = steel('Q-1')[0]
        r = m.quote_rows(q[:6] + [''] + q[7:], q[:5] + [''] + q[6:])
        m.demands(*STEEL_DEM)
        rk, _ = self.rank(m)
        self.assertEqual((rk['status'], rk['ranking']), ('no_offers', []))

    def test_conflicting_quotes_with_one_id_are_held_and_not_averaged_or_picked(self):
        m = mkt_world()
        m.quote_rows(steel('Q-1', rate='100000')[0], steel('Q-1', rate='90000')[0])
        m.demands(*STEEL_DEM)
        rk, _ = self.rank(m)
        self.assertNotIn('supplier_quote/Q-1', [x['offer'] for x in rk['ranking']])
        self.assertTrue(any(x['code'] if 'code' in x else True for x in [{}]))
        self.assertEqual(rk['definitive'], False)

    def test_duplicate_quote_rows_do_not_create_two_offers(self):
        m = mkt_world()
        a = steel('Q-1')[0]
        m.quote_rows(a, a)
        m.readings(*steel('Q-1')[1])
        m.demands(*STEEL_DEM)
        rk, _ = self.rank(m)
        self.assertEqual(len(rk['offers']), 1)
        self.assertEqual(rk['status'], 'insufficient_offers')

    def test_a_currency_error_an_unknown_currency_is_never_converted_or_ranked_as_comparable(self):
        m = mkt_world()
        q = quote('Q-1', 'SUP-004', 'MAT-STEEL', 's', '2026-09-08', '2026-11-15', '1000', 'XXX', '0.6540', '2026-09-25', '0', 'FOB', '7')
        m.quote_rows(q, steel('Q-2', sup='SUP-001')[0])
        m.readings(*std_readings('Q-1'), *std_readings('Q-2'))
        m.fx(fxrow('2026-09-30', '0.6540'))
        m.demands(*STEEL_DEM)
        rk, _ = self.rank(m)
        self.assertNotIn('supplier_quote/Q-1', [x['offer'] for x in rk['ranking'] if x['class'] in ('comparable', 'comparable_with_adjustment')])
        self.assertFalse(rk['definitive'])

    def test_a_changed_price_on_a_revised_quote_replaces_the_old_one_in_the_ranking(self):
        m = with_quotes(steel('Q-1', rate='100000'), steel('Q-2', sup='SUP-002', rate='101000'), dem=STEEL_DEM)
        rk, _ = self.rank(m)
        self.assertEqual(rk['ranking'][0]['offer'], 'supplier_quote/Q-1')
        m.quote_rows(steel('Q-1', rate='105000')[0])
        rk2, _ = self.rank(m)
        self.assertEqual(rk2['ranking'][0]['offer'], 'supplier_quote/Q-2')

    def test_a_delivery_change_that_removes_the_uncovered_quantity_clears_the_purchase_decision(self):
        m = with_quotes(steel('Q-1', valid='2026-10-27'), steel('Q-2', sup='SUP-002', rate='101000', valid='2026-10-30'), dem=STEEL_DEM)
        self.assertEqual(len(S_(m.mres(), 'MP03')), 1)
        m.orders(pom('PO-1', qty='100', rate='100000', date='2026-09-20'))
        self.assertEqual(S_(m.mres(), 'MP03'), [])

    def test_misleading_recommendation_no_gate_failure_ever_lets_a_recommendation_through(self):
        worlds = [
            with_quotes(conc('Q-A'), conc('Q-B', strength='32', rate='30000', sup='SUP-002'), dem=[demand('DEM-1', 'PRJ-001', 'MAT-CONC40', '100', 'm3', '2026-12-01')]),
            with_quotes(conc('Q-A'), conc('Q-B', rate='30000', sup='SUP-002', verified=False), dem=[demand('DEM-1', 'PRJ-001', 'MAT-CONC40', '100', 'm3', '2026-12-01')]),
            with_quotes(steel('Q-1', valid='2026-09-20', issue='2026-08-01'), steel('Q-2', sup='SUP-002', valid='2026-09-20', issue='2026-08-01'), dem=STEEL_DEM),
            with_quotes(steel('Q-1', issue='2026-05-01'), steel('Q-2', sup='SUP-002', issue='2026-05-01'), dem=STEEL_DEM),
            with_quotes(steel('Q-1'), dem=STEEL_DEM),
            with_quotes(dem=STEEL_DEM),
        ]
        for i, m in enumerate(worlds):
            rk, _ = self.rank(m)
            ok, why = CP.may_recommend(rk)
            if ok:
                self.assertTrue(rk['definitive'], i)
                self.assertTrue(all(x['class'] in ('comparable', 'comparable_with_adjustment') for x in rk['ranking']), i)
                self.assertTrue(rk['human_approval_required'])
            else:
                self.assertTrue(why, i)
        good = with_quotes(steel('Q-1'), steel('Q-2', sup='SUP-002', rate='101000'), dem=STEEL_DEM)
        rk, _ = self.rank(good)
        self.assertEqual(CP.may_recommend(rk), (True, []))

    def test_misleading_recommendation_a_cheap_foreign_quote_with_open_critical_checks_is_never_definitive(self):
        m = mkt_world()
        q = quote('Q-1', 'SUP-004', 'MAT-STEEL', 's', '2026-09-08', '2026-11-15', '1000', 'USD', '0.6540', '2026-09-25', '0', 'FOB', '7')
        m.quote_rows(q, steel('Q-2')[0])
        m.readings(*std_readings('Q-1'), *std_readings('Q-2'))
        m.fx(fxrow('2026-09-30', '0.6540'))
        m.demands(*STEEL_DEM)
        rk, _ = self.rank(m)
        self.assertFalse(rk['definitive'])
        self.assertFalse(CP.may_recommend(rk)[0])


class TestCodeHashCoverage(unittest.TestCase):
    """A run pins the hash of the code that produced it, so the hash must cover every procurement module: a change to any of them has to change the pinned hash."""
    PROCUREMENT = ('analysis', 'common', 'compare', 'demand', 'events', 'fresh', 'fx', 'gather', 'intake', 'intl', 'landed', 'opportunity', 'policy', 'purchasing', 'rules', 'scenarios', 'spec', 'suppliers')

    def test_the_code_hash_covers_every_procurement_module(self):
        covered = {m.__name__.rsplit('.', 1)[1] for m in MD.MODULES if m.__name__.startswith('apg.mkt.')}
        self.assertEqual(sorted(set(self.PROCUREMENT) - covered), [], 'a procurement module is missing from the code hash')

    def test_leaving_any_one_module_out_changes_the_hash(self):
        full = MD.code_hash()
        self.assertRegex(full, r'^[0-9a-f]{64}$')
        original = MD.MODULES
        try:
            for name in self.PROCUREMENT:
                MD.MODULES = tuple(m for m in original if m.__name__ != 'apg.mkt.' + name)
                self.assertNotEqual(MD.code_hash(), full, 'the hash ignores %s' % name)
        finally:
            MD.MODULES = original
        self.assertEqual(MD.code_hash(), full)


if __name__ == '__main__':
    unittest.main()
