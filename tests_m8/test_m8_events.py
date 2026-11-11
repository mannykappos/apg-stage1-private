"""Events: in-order, out-of-order, deferred, timed-out, rejected, duplicated and conflicting deliveries follow AUIF's own sequencing contract (no new policy), and the
assessment cannot proceed while any event waits or needs reconciliation.  APG-M8.1: AUIF rev14 also tells the module about every event it did not deliver (finding M8-F3
corrected).  APG reads both channels - the caller's ordering results and AUIF's pending list, and the module's EVENT_NOT_APPLIED notices - and requires them to agree; an
in-order event AUIF has no entity mapping for stays outstanding, so the assessment waits."""
import unittest
from ._auif import HERE_ROOT, PK, client, codes, records, world
from .synthetic_events import SyntheticPaymentEvents, event, EVENT
from apg_auif import definitions as DEF, gate, lineage

IID = 'bz-payment-events'


def ev_world(policy=None):
    cfg = client.load_config(HERE_ROOT)
    conn = SyntheticPaymentEvents()
    p = PK.build_pack(IID, DEF.by_entity(cfg['definitions']), ['payment'], [PK.fingerprint_of(conn)])
    cfg['packs'][p['pack_id']] = p
    clock, prov, store, audit, who = world()
    s = who('t', 'zero_one', 'ann')
    env = client.AuifEnvironment(HERE_ROOT, cfg, sequencer_policy=policy)
    env.bind('zero_one', s, clock)
    env.add_integration('zero_one', IID, conn, p, 'accounting', ['payment'], {'payment': env.entity_config('payment', file_name='payment events')},
                        event_entities={EVENT: 'payment'})
    env.start()
    env.activate('zero_one', IID)
    return env, s


def st(env, s):
    return gate.assessment_status(s, [(IID, 'payment')], env.module)


class TestEvents(unittest.TestCase):
    def test_in_order_events_become_records_with_their_sequence_in_the_lineage(self):
        env, s = ev_world()
        out = env.ingest_events('zero_one', IID, 'payment', [event(1, 'PAY-9001'), event(2, 'PAY-9002'), event(3, 'PAY-9003')])
        self.assertEqual([r['ordering_state'] for r in out['ordering']], ['IN_ORDER'] * 3)
        recs = records(s, 'payment')
        self.assertEqual(sorted(recs), ['PAY-9001', 'PAY-9002', 'PAY-9003'])
        for k, v in recs.items():
            self.assertEqual(lineage.record_problems(v, k), [])
            self.assertEqual((v['provenance']['delivery'], v['provenance']['causal_event_id']), ('event', 'ev-%04d' % int(k[-1])))
            self.assertEqual(v['provenance']['source_sequence'], int(k[-1]))
        self.assertEqual(st(env, s)['status'], 'can_assess')

    def test_an_event_ahead_of_its_predecessor_waits_and_the_assessment_waits_with_it(self):
        env, s = ev_world()
        out = env.ingest_events('zero_one', IID, 'payment', [event(1, 'PAY-9001'), event(3, 'PAY-9003')])
        self.assertEqual([r['ordering_state'] for r in out['ordering']], ['IN_ORDER', 'QUEUED_AWAITING_PREDECESSOR'])
        self.assertEqual(sorted(records(s, 'payment')), ['PAY-9001'])                 # the applied event is kept: AUIF never delivers it again
        self.assertEqual(codes(st(env, s)), ['EVENTS_WAITING'])
        out = env.ingest_events('zero_one', IID, 'payment', [event(2, 'PAY-9002')])
        self.assertEqual([r['ordering_state'] for r in out['ordering']], ['IN_ORDER', 'IN_ORDER'])  # 2, then 3 released from the queue
        self.assertEqual(sorted(records(s, 'payment')), ['PAY-9001', 'PAY-9002', 'PAY-9003'])
        self.assertEqual(st(env, s)['status'], 'can_assess')

    def test_a_wait_that_times_out_goes_to_reconciliation_and_never_invents_the_missing_event(self):
        env, s = ev_world()
        env.ingest_events('zero_one', IID, 'payment', [event(1, 'PAY-9001'), event(3, 'PAY-9003')])
        env.clock.advance(31)
        out = env.tick('zero_one', IID, 'payment')
        self.assertEqual([r['ordering_state'] for r in out['ordering']], ['RECONCILIATION_PENDING'])
        self.assertEqual(sorted(records(s, 'payment')), ['PAY-9001'])
        self.assertEqual(codes(st(env, s)), ['EVENT_RECONCILIATION_PENDING'])

    def test_deferred_and_rejected_events_follow_the_configured_auif_policy(self):
        for pol, want_state, want_code in (({'*': {'on_missing': 'DEFER'}}, 'DEFERRED', 'EVENTS_WAITING'),
                                           ({'*': {'on_missing': 'REJECT'}}, 'REJECTED_BY_POLICY', 'EVENT_REJECTED'),
                                           ({'*': {'on_missing': 'RECONCILE'}}, 'RECONCILIATION_PENDING', 'EVENT_RECONCILIATION_PENDING')):
            with self.subTest(pol):
                env, s = ev_world(pol)
                out = env.ingest_events('zero_one', IID, 'payment', [event(2, 'PAY-9002')])
                self.assertEqual(out['ordering'][0]['ordering_state'], want_state)
                self.assertEqual(len(s.query('payment')), 0)
                self.assertEqual(codes(st(env, s)), [want_code])

    def test_a_repeated_event_has_no_second_effect(self):
        env, s = ev_world()
        env.ingest_events('zero_one', IID, 'payment', [event(1, 'PAY-9001')])
        before = records(s, 'payment')
        out = env.ingest_events('zero_one', IID, 'payment', [event(1, 'PAY-9001')])
        self.assertEqual(out['ordering'][0]['ordering_state'], 'DUPLICATE_SUPPRESSED')
        self.assertEqual(records(s, 'payment'), before)
        self.assertEqual(st(env, s)['status'], 'can_assess')

    def test_the_same_event_id_with_other_content_needs_reconciliation(self):
        env, s = ev_world()
        env.ingest_events('zero_one', IID, 'payment', [event(1, 'PAY-9001')])
        out = env.ingest_events('zero_one', IID, 'payment', [event(1, 'PAY-9001', cents='999')])
        self.assertEqual(out['ordering'][0]['ordering_state'], 'RECONCILIATION_PENDING')
        self.assertEqual(records(s, 'payment')['PAY-9001']['fields']['amount_cents'], 1000)
        self.assertEqual(codes(st(env, s)), ['EVENT_RECONCILIATION_PENDING'])

    def test_a_new_event_for_a_stored_key_with_other_content_follows_the_m3_rule(self):
        env, s = ev_world()
        env.ingest_events('zero_one', IID, 'payment', [event(1, 'PAY-9001'), event(2, 'PAY-9001', cents='2000')])
        p = records(s, 'payment')['PAY-9001']
        self.assertEqual(p['intrinsic']['outcome'], 'quarantined')                     # the M3 contract: different content, no order -> a quarantined conflict
        self.assertEqual(len(p['conflict']['contenders']), 2)
        self.assertEqual(st(env, s)['status'], 'can_assess')                         # a conflict is an exclusion every figure lists, as on the M3 path


class TestEventLineage(unittest.TestCase):
    def test_an_event_object_whose_observation_never_arrives_is_refused(self):
        env, s = ev_world()
        env.module._h['event'] = []                                                  # the observation of every event is lost before APG sees it
        out = env.ingest_events('zero_one', IID, 'payment', [event(1, 'PAY-9001')])
        self.assertEqual(out['status'], 'blocked')
        self.assertIn('LINEAGE_INCOMPLETE', {c for c, _ in out['reasons']})
        self.assertEqual(len(s.query('payment')), 0)
        self.assertIn('LINEAGE_INCOMPLETE', codes(st(env, s)))


class TestFindingM8F3(unittest.TestCase):
    def test_auif_tells_the_module_about_an_event_that_waits_and_both_channels_agree(self):
        env, s = ev_world()
        seen = []
        env.module.on('error', lambda ctx, p: seen.append((p.get('kind'), p.get('event_id'), p.get('ordering_state'), p.get('waiting_on'))))
        out = env.ingest_events('zero_one', IID, 'payment', [event(2, 'PAY-9002')])
        self.assertEqual(out['ordering'][0]['ordering_state'], 'QUEUED_AWAITING_PREDECESSOR')
        self.assertEqual(seen, [('EVENT_NOT_APPLIED', 'ev-0002', 'QUEUED_AWAITING_PREDECESSOR', ['seq:1'])])     # rev14: the module is told
        self.assertEqual((out['status'], [c for c, _ in out['reasons']]), ('applied', ['EVENTS_WAITING']))      # a notice is not an integrity failure: nothing is refused
        self.assertEqual(codes(st(env, s)), ['EVENTS_WAITING'])                        # and the gate still stops, as before

    def test_a_reconciliation_notice_agrees_with_the_tick_result(self):
        env, s = ev_world()
        env.ingest_events('zero_one', IID, 'payment', [event(1, 'PAY-9001'), event(3, 'PAY-9003')])
        env.clock.advance(31)
        out = env.tick('zero_one', IID, 'payment')
        self.assertEqual([r['ordering_state'] for r in out['ordering']], ['RECONCILIATION_PENDING'])
        self.assertNotIn('EVENT_NOTICE_MISMATCH', {c for c, _ in out['reasons']})
        self.assertEqual(codes(st(env, s)), ['EVENT_RECONCILIATION_PENDING'])

    def test_an_in_order_event_auif_cannot_map_stays_outstanding_and_the_in_order_events_are_kept(self):
        env, s = ev_world()
        other = dict(event(2, 'PAY-9002'), type='payment.reversed')                  # a type the integration has no entity mapping for
        out = env.ingest_events('zero_one', IID, 'payment', [event(1, 'PAY-9001'), other])
        self.assertEqual([r['ordering_state'] for r in out['ordering']], ['IN_ORDER', 'IN_ORDER'])
        self.assertEqual(sorted(records(s, 'payment')), ['PAY-9001'])                 # AUIF never delivers an applied event twice, so it is kept
        self.assertEqual(codes(st(env, s)), ['EVENT_NOT_APPLIED'])                     # and the event AUIF could not apply stops the assessment
        out = env.ingest_events('zero_one', IID, 'payment', [event(3, 'PAY-9003')])
        self.assertEqual(codes(st(env, s)), ['EVENT_NOT_APPLIED'])                     # it stays outstanding: nothing resolves it by itself

    def test_a_missing_notice_is_a_reason_and_what_auif_applied_is_kept(self):
        env, s = ev_world()
        real = env.fabric._tell
        env.fabric._tell = lambda ctx, mid, kind, **d: None if kind == 'EVENT_NOT_APPLIED' else real(ctx, mid, kind, **d)      # AUIF's notice is lost
        out = env.ingest_events('zero_one', IID, 'payment', [event(1, 'PAY-9001'), event(3, 'PAY-9003')])
        self.assertEqual(out['status'], 'applied')
        self.assertIn('EVENT_NOTICE_MISMATCH', {c for c, _ in out['reasons']})
        self.assertEqual(sorted(records(s, 'payment')), ['PAY-9001'])
        self.assertIn('EVENT_NOTICE_MISMATCH', codes(st(env, s)))

    def test_notices_that_disagree_with_the_results_are_a_reason_and_nothing_applied_is_lost(self):
        from apg_auif import intake
        b = type('B', (), {})()
        b.errors = [{'kind': 'EVENT_NOT_APPLIED', 'event_id': 'ev-9', 'ordering_state': 'DEFERRED'}]
        self.assertEqual([c for c, _ in intake.notice_problems(b, [{'event_id': 'ev-9', 'ordering_state': 'IN_ORDER'}])], ['EVENT_NOTICE_MISMATCH'])
        b.errors = []
        self.assertEqual([c for c, _ in intake.notice_problems(b, [{'event_id': 'ev-9', 'ordering_state': 'QUEUED_AWAITING_PREDECESSOR'}])], ['EVENT_NOTICE_MISMATCH'])
        b.errors = [{'kind': 'EVENT_NOT_APPLIED', 'event_id': 'ev-9', 'ordering_state': 'QUEUED_AWAITING_PREDECESSOR'}]
        self.assertEqual(intake.notice_problems(b, [{'event_id': 'ev-9', 'ordering_state': 'QUEUED_AWAITING_PREDECESSOR'}]), [])


if __name__ == '__main__':
    unittest.main()
