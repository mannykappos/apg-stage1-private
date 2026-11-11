"""Edge cases of the finding lifecycle, the monitor and the relationship view found by the mutation pass: runs on the same as-of day, runs created at the instant of a decision,
how history and notification entries are numbered and attributed, what a refusal says, and how links replace one another.  Every value is synthetic."""
import copy
import types
import unittest
from . import _path                                         # noqa: F401
from .helpers_det import AS_OF, bud, det_world, inv, po
from .test_det_findings import FID, breach, first, person
from .test_det_monitor import args
from apg import repro
from apg.det import detect as D, findings as FD, gather as G, monitor as MON, relations as RL
from .helpers_det import approve_filled


def uncovered(m, scoped, kind='CC-01'):
    """Remove the overrun (a credit note) so a later run does not detect the condition."""
    m.credits(['CRN-1', 'SUP-001', 'INV-1', '2026-09-25', '1000000', '100000'])
    m.reconcile()


class TestSameDayAndOrdering(unittest.TestCase):
    def test_a_second_run_for_the_same_as_of_day_is_not_called_older(self):
        m = breach()
        first(m)
        m.invoices(inv('INV-2', sin='SI-2', ex='100000', cc='CC-01'))
        m.reconcile()
        out = m.ingest(m.detect())                                                       # same as-of day, new evidence
        self.assertEqual((out['updated'], out['ignored_older']), ([FID], []))
        self.assertEqual(FD.get(m.svc, FID)['seen_count'], 2)

    def test_a_condition_that_is_gone_is_noted_by_a_second_run_for_the_same_as_of_day(self):
        m = breach()
        first(m)
        uncovered(m, m.svc)
        out = m.ingest(m.detect())
        self.assertEqual(out['not_redetected'], [FID])

    def test_not_redetected_is_noted_once_per_as_of_day_and_moves_with_the_day(self):
        m = breach()
        first(m)
        uncovered(m, m.svc)
        m.clock.advance(86400)
        self.assertEqual(m.ingest(m.detect(as_of='2026-10-01'))['not_redetected'], [FID])
        m.invoices(inv('INV-3', sin='SI-3', ex='100000', cc='CC-02'))                      # an unrelated change, so this is a different run
        m.reconcile()
        self.assertEqual(m.ingest(m.detect(as_of='2026-10-01'))['not_redetected'], [])
        f = FD.get(m.svc, FID)
        self.assertEqual([h['event'] for h in f['history']].count('not_redetected'), 1)
        m.clock.advance(86400)
        self.assertEqual(m.ingest(m.detect(as_of='2026-10-02'))['not_redetected'], [FID])
        self.assertEqual(FD.get(m.svc, FID)['not_redetected']['as_of'], '2026-10-02')

    def test_a_finding_a_person_has_dismissed_is_never_marked_not_redetected(self):
        m = breach()
        first(m)
        m.clock.advance(3600)
        FD.transition(m.reviewer, m.clock, FID, 'dismissed', rationale='accepted')
        uncovered(m, m.svc)
        m.clock.advance(86400)
        out = m.ingest(m.detect(as_of='2026-10-01'))
        self.assertEqual(out['not_redetected'], [])
        self.assertIsNone(FD.get(m.svc, FID)['not_redetected'])

    def test_the_rule_version_is_listed_once(self):
        m = breach()
        first(m)
        m.clock.advance(86400)
        m.ingest(m.detect(as_of='2026-10-01'))
        self.assertEqual(FD.get(m.svc, FID)['rule_versions'], [{'rule': 'DET-R01', 'version': 1}])

    def test_a_run_created_at_the_instant_of_the_decision_does_not_undo_it_and_one_a_second_later_does(self):
        m = breach()
        first(m)
        m.clock.advance(3600)
        FD.transition(m.reviewer, m.clock, FID, 'dismissed', rationale='accepted')
        m.invoices(inv('INV-2', sin='SI-2', ex='400000', cc='CC-01'))
        m.reconcile()
        out = m.ingest(m.detect(as_of='2026-10-01'))                                      # no time has passed since the decision
        self.assertEqual((out['ignored_older'], out['reopened']), ([FID], []))
        m.clock.advance(1)
        m.invoices(inv('INV-3', sin='SI-3', ex='100000', cc='CC-02'))
        m.reconcile()
        out = m.ingest(m.detect(as_of='2026-10-01'))
        self.assertEqual(out['reopened'], [FID])

    def test_the_reason_recorded_for_a_reopening_depends_on_what_it_was_reopened_from(self):
        m = breach()
        first(m)
        m.clock.advance(3600)
        FD.transition(m.reviewer, m.clock, FID, 'dismissed', rationale='accepted')
        m.clock.advance(3600)
        m.invoices(inv('INV-2', sin='SI-2', ex='400000', cc='CC-01'))
        m.reconcile()
        m.ingest(m.detect(as_of='2026-10-01'))
        self.assertEqual(FD.get(m.svc, FID)['history'][-1]['detail']['why'], 'the condition was detected again with changed evidence')
        for to, kw in (('under_review', {}), ('confirmed', {'rationale': 'yes'})):
            FD.transition(m.reviewer, m.clock, FID, to, **kw)
        FD.transition(m.owner, m.clock, FID, 'action_proposed', action_text='fix')
        approve_filled(m.approver, m.clock, FID, rationale='ok')
        FD.transition(m.owner, m.clock, FID, 'in_progress')
        FD.transition(m.owner, m.clock, FID, 'resolved', rationale='fixed', evidence_ref='x/y')
        m.clock.advance(3600)
        m.invoices(inv('INV-3', sin='SI-3', ex='500000', cc='CC-01'))
        m.reconcile()
        m.ingest(m.detect(as_of='2026-10-02'))
        f = FD.get(m.svc, FID)
        self.assertEqual((f['status'], f['history'][-1]['detail']['why']), ('reopened', 'the condition was detected again after resolution'))


class TestHistoryAndNotificationEntries(unittest.TestCase):
    def test_history_entries_are_numbered_attributed_and_carry_their_detail(self):
        m = breach()
        first(m)
        FD.transition(m.reviewer, m.clock, FID, 'under_review')
        FD.transition(m.reviewer, m.clock, FID, 'confirmed', rationale='checked')
        h = FD.get(m.svc, FID)['history']
        self.assertEqual([x['seq'] for x in h], [1, 2, 3])
        self.assertEqual((h[0]['actor'], h[0]['actor_kind'], h[0]['event']), ('detsvc', 'service', 'detected'))
        self.assertEqual(h[0]['detail']['rule']['id'], 'DET-R01')
        self.assertTrue(h[0]['detail']['run_key'])
        self.assertEqual((h[1]['actor'], h[1]['actor_kind'], h[1]['from'], h[1]['to'], h[1]['detail']), ('rita', 'human', 'detected', 'under_review', {'rationale': ''}))
        self.assertEqual(h[2]['detail'], {'rationale': 'checked'})

    def test_notification_entries_are_numbered_in_the_order_they_were_made(self):
        m = breach()
        first(m)
        m.notifier._contract_set_transport_failure(True)
        FD.flush_notifications(m.svc, m.clock, m.notifier)                                 # 1: failed
        m.notifier._contract_set_transport_failure(False)
        FD.flush_notifications(m.svc, m.clock, m.notifier)                                 # 2: sent
        FD.transition(m.reviewer, m.clock, FID, 'under_review')                            # 3: suppressed (inside the window after a send)
        n = FD.get(m.svc, FID)['notifications']
        self.assertEqual([(x['seq'], x['outcome']) for x in n], [(1, 'failed'), (2, 'sent'), (3, 'suppressed')])

    def test_a_note_that_failed_to_send_does_not_start_the_suppression_window(self):
        m = breach()
        first(m)
        m.notifier._contract_set_transport_failure(True)
        FD.flush_notifications(m.svc, m.clock, m.notifier)
        m.notifier._contract_set_transport_failure(False)
        m.clock.advance(86400)
        m.invoices(inv('INV-2', sin='SI-2', ex='100000', cc='CC-01'))
        m.reconcile()
        m.ingest(m.detect(as_of='2026-10-01'))
        reasons = [p['reason'] for p in FD.get(m.svc, FID)['pending_notifications']]
        self.assertEqual(reasons, ['new', 'material_evidence'])

    def test_a_suppressed_note_is_not_taken_for_a_sent_one(self):
        m = breach()
        first(m)
        FD.flush_notifications(m.svc, m.clock, m.notifier)
        FD.transition(m.reviewer, m.clock, FID, 'under_review')                            # suppressed inside the window: at is None
        m.clock.advance(8 * 86400)
        FD.transition(m.reviewer, m.clock, FID, 'confirmed', rationale='yes')              # outside the window of the one real send
        self.assertEqual([p['reason'] for p in FD.get(m.svc, FID)['pending_notifications']], ['status_transition'])


class TestRefusals(unittest.TestCase):
    def tampered(self, m, change):
        rec = m.detect()
        bad = copy.deepcopy(m.s.get(repro.KIND, rec['run_key']).payload)
        change(bad)
        m.s.put(repro.KIND, 'tampered-1', bad)
        return 'tampered-1'

    def test_a_run_whose_stored_result_was_changed_is_refused_and_says_why(self):
        m = breach()
        key = self.tampered(m, lambda p: p['result']['signals'][0]['quantification'].update(gross_cents=1))
        with self.assertRaises(FD.LifecycleError) as cm:
            FD.ingest_run(m.svc, m.clock, m.detreg, key)
        self.assertEqual(cm.exception.code, 'RUN_DOES_NOT_VERIFY')
        chk = D.check_record(m.s, m.detreg, key)
        self.assertFalse(chk['replay'].ok)
        self.assertIn(chk['replay'].code, str(cm.exception))
        self.assertEqual(FD.all_findings(m.svc), [])

    def test_a_run_whose_pins_do_not_match_what_was_read_is_refused(self):
        m = breach()
        key = self.tampered(m, lambda p: p['params']['pins'].update({'notice/N-GHOST': 1}))
        with self.assertRaises(FD.LifecycleError) as cm:
            FD.ingest_run(m.svc, m.clock, m.detreg, key)
        self.assertEqual(cm.exception.code, 'RUN_DOES_NOT_VERIFY')
        self.assertEqual(FD.all_findings(m.svc), [])

    def test_a_stored_run_of_some_other_formula_is_not_a_detection_run(self):
        m = breach()
        result = m.res()
        reg = D.det_registry()
        reg.register('fake.detect', 1, lambda inputs, params: copy.deepcopy(result), code_hash='fake')
        refs, params = G.gather_project(m.s, 'PRJ-001', AS_OF, m.policy['version'], m.dp['version'])
        rec = repro.run(m.s, reg, m.clock, 'fake.detect', 1, refs, params)
        with self.assertRaises(FD.LifecycleError) as cm:
            FD.ingest_run(m.svc, m.clock, reg, rec['run_key'])
        self.assertEqual(cm.exception.code, 'NOT_A_DETECTION_RUN')

    def test_an_unknown_finding_is_named_not_invented(self):
        m = breach()
        first(m)
        for call in (lambda: FD.get(m.svc, 'FND-none'), lambda: FD.transition(m.reviewer, m.clock, 'FND-none', 'under_review'), lambda: FD.assign(m.owner, m.clock, 'FND-none', 'carol'),
                     lambda: FD.defer(m.reviewer, m.clock, 'FND-none', '2026-11-15', 'later')):
            with self.assertRaises(FD.LifecycleError) as cm:
                call()
            self.assertEqual(cm.exception.code, 'FINDING_UNKNOWN')

    def test_a_superseded_finding_cannot_be_assigned(self):
        m = breach(extra=(inv('INV-9', sin='SI-9', ex='3300000', cc='CC-02'),))
        out = m.ingest(m.detect())
        a, b = sorted(out['created'])
        FD.transition(m.reviewer, m.clock, a, 'superseded', rationale='replaced', superseded_by=b)
        with self.assertRaises(FD.LifecycleError) as cm:
            FD.assign(m.owner, m.clock, a, 'carol')
        self.assertEqual(cm.exception.code, 'TERMINAL')

    def test_a_deferral_needs_a_text_date_of_ten_characters(self):
        m = breach()
        first(m)
        for until in (None, 20261115, '2026-11-5', '2026-11-155'):
            with self.assertRaises(FD.LifecycleError) as cm:
                FD.defer(m.reviewer, m.clock, FID, until, 'later')
            self.assertEqual(cm.exception.code, 'RATIONALE_REQUIRED', until)

    def test_sending_notifications_needs_both_the_role_and_a_service_identity(self):
        m = breach()
        first(m)
        human_with_role = person(m, 'hr', 'hana', FD.SERVICE)
        service_without_role = m.w.who('sw', 'zero_one', 'svcnorole', (), 'service')
        for who in (human_with_role, service_without_role, m.reviewer):
            with self.assertRaises(FD.LifecycleError) as cm:
                FD.flush_notifications(who, m.clock, m.notifier)
            self.assertEqual(cm.exception.code, 'SERVICE_REQUIRED')

    def test_ingestion_needs_both_the_role_and_a_service_identity(self):
        m = breach()
        rec = m.detect()
        service_without_role = m.w.who('sw', 'zero_one', 'svcnorole', (), 'service')
        for who in (service_without_role, person(m, 'hr', 'hana', FD.SERVICE)):
            with self.assertRaises(FD.LifecycleError) as cm:
                FD.ingest_run(who, m.clock, m.detreg, rec['run_key'])
            self.assertEqual(cm.exception.code, 'SERVICE_REQUIRED')


class Stale:
    """A view of the store that shows every record one revision behind, as if another person had just changed it."""
    def __init__(self, scoped):
        self._s = scoped

    def __getattr__(self, name):
        return getattr(self._s, name)

    def _old(self, rec):
        return None if rec is None else types.SimpleNamespace(key=rec.key, payload=rec.payload, revision=rec.revision - 1)

    def get(self, kind, key, *a):
        rec = self._s.get(kind, key, *a)
        return self._old(rec) if kind == FD.KIND else rec

    def query(self, kind, where=None):
        recs = self._s.query(kind, where) if where is not None else self._s.query(kind)
        return [self._old(r) for r in recs] if kind == FD.KIND else recs


class TestConcurrentChange(unittest.TestCase):
    def test_a_decision_made_on_a_stale_view_is_refused_not_written(self):
        m = breach()
        first(m)
        FD.assign(m.reviewer, m.clock, FID, 'carol')                                       # revision 2 now exists
        with self.assertRaises(FD.LifecycleError) as cm:
            FD.transition(Stale(m.reviewer), m.clock, FID, 'under_review')
        self.assertEqual(cm.exception.code, 'CONCURRENT_CHANGE')
        self.assertEqual(FD.get(m.svc, FID)['status'], 'detected')

    def test_an_ingestion_that_meets_a_changed_finding_writes_nothing(self):
        m = breach()
        first(m)
        FD.assign(m.reviewer, m.clock, FID, 'carol')
        m.clock.advance(86400)
        rec = m.detect(as_of='2026-10-01')
        with self.assertRaises(FD.LifecycleError) as cm:
            FD.ingest_run(Stale(m.svc), m.clock, m.detreg, rec['run_key'])
        self.assertEqual(cm.exception.code, 'CONCURRENT_CHANGE')
        self.assertIsNone(m.s.get(FD.INGEST_KIND, rec['run_key']))
        self.assertEqual(FD.get(m.svc, FID)['seen_count'], 1)

    def test_a_flush_that_meets_a_changed_finding_is_refused(self):
        m = breach()
        first(m)
        FD.assign(m.reviewer, m.clock, FID, 'carol')
        with self.assertRaises(FD.LifecycleError) as cm:
            FD.flush_notifications(Stale(m.svc), m.clock, m.notifier)
        self.assertEqual(cm.exception.code, 'CONCURRENT_CHANGE')


class TestLinks(unittest.TestCase):
    def setUp(self):
        m = det_world()
        m.budgets(bud(cc='CC-03', cents='1000000'))
        m.invoices(inv('INV-1', ex='5300000', cc='CC-01'), inv('INV-2', sin='SI-2', ex='3300000', cc='CC-02'), inv('INV-3', sin='SI-3', ex='1200000', cc='CC-03'))
        m.reconcile()
        out = m.ingest(m.detect())
        self.a, self.b, self.c = sorted(out['created'])
        self.m = m

    def rel(self, fid):
        return [(r['with'], r['kind'], r['rationale']) for r in FD.get(self.m.svc, fid)['relations']]

    def test_linking_the_same_pair_in_the_same_way_again_replaces_the_earlier_link(self):
        m = self.m
        FD.link(m.reviewer, m.clock, self.a, self.b, 'related', 'first look')
        FD.link(m.reviewer, m.clock, self.a, self.b, 'related', 'second look')
        self.assertEqual(self.rel(self.a), [(self.b, 'related', 'second look')])
        self.assertEqual(self.rel(self.b), [(self.a, 'related', 'second look')])

    def test_a_different_kind_or_a_different_finding_adds_a_link_and_keeps_the_others(self):
        m = self.m
        FD.link(m.reviewer, m.clock, self.a, self.b, 'related', 'one')
        FD.link(m.reviewer, m.clock, self.a, self.b, 'financial_overlap', 'two')
        FD.link(m.reviewer, m.clock, self.a, self.c, 'related', 'three')
        self.assertEqual(sorted(self.rel(self.a)), sorted([(self.b, 'related', 'one'), (self.b, 'financial_overlap', 'two'), (self.c, 'related', 'three')]))
        self.assertEqual(sorted(self.rel(self.b)), sorted([(self.a, 'related', 'one'), (self.a, 'financial_overlap', 'two')]))
        self.assertEqual(self.rel(self.c), [(self.a, 'related', 'three')])


class TestRelatedView(unittest.TestCase):
    @staticmethod
    def f(fid, refs):
        return {'finding_id': fid, 'signal': {'overlap_group': None, 'evidence': [{'ref': r} for r in refs]}, 'relations': []}

    def test_three_shared_records_are_listed_in_full_and_a_fourth_adds_an_ellipsis(self):
        a, b = self.f('A', ['x/1', 'x/2', 'x/3']), self.f('B', ['x/1', 'x/2', 'x/3'])
        self.assertEqual(RL.related([a, b])['A'], [{'with': 'B', 'because': ['shared_records:x/1,x/2,x/3']}])
        a, b = self.f('A', ['x/1', 'x/2', 'x/3', 'x/4']), self.f('B', ['x/1', 'x/2', 'x/3', 'x/4'])
        self.assertEqual(RL.related([a, b])['A'], [{'with': 'B', 'because': ['shared_records:x/1,x/2,x/3...']}])


class TestMonitorEdges(unittest.TestCase):
    def test_an_order_event_runs_its_project_and_the_tenant_an_amendment_event_only_its_project(self):
        m = det_world()
        m.projects(['PRJ-002', 'P2', '1', '2026-01-01', '2027-01-01'])
        m.pos(po('PO-1', amount='1000000'))
        m.amendments(['AMD-1', 'PO-1', '2026-08-01', '100000', '', 'extra'])
        m.reconcile()
        self.assertEqual(MON.scopes_for_event(m.s, {'kind': 'purchase_order', 'key': 'PO-1'}), (['PRJ-001'], True))
        self.assertEqual(MON.scopes_for_event(m.s, {'kind': 'po_amendment', 'key': 'AMD-1'}), (['PRJ-001'], False))

    def test_the_log_is_audited_as_ok_for_a_good_run_and_failed_for_a_bad_one(self):
        m = det_world()
        (s, c, r), a, fp, dpv = args(m)
        MON.run_scopes(s, c, r, ['tenant'], a, fp, dpv, 'manual')
        MON.run_scopes(s, c, r, ['PRJ-NOPE'], a, fp, dpv, 'manual')
        outcomes = [e.outcome for e in m.w.audit.read(m.s.ctx) if e.event_type == 'monitor.run']
        self.assertEqual(outcomes, ['ok', 'failed'])

    def test_health_names_the_failure_of_each_failing_scope(self):
        m = det_world()
        (s, c, r), a, fp, dpv = args(m)
        MON.run_scopes(s, c, r, ['PRJ-NOPE', 'tenant'], a, fp, dpv, 'manual')
        h = MON.health(m.s, a)
        self.assertEqual(sorted(h['scopes_currently_failing']), ['PRJ-NOPE'])
        self.assertEqual(h['scopes_currently_failing']['PRJ-NOPE']['failure']['code'], 'PROJECT_UNKNOWN')
        self.assertEqual(h['scopes_currently_failing']['PRJ-NOPE']['failure']['scope'], 'PRJ-NOPE')


if __name__ == '__main__':
    unittest.main()
