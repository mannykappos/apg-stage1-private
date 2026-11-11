import unittest
from . import _path                                         # noqa: F401
from .helpers_det import AS_OF, DetMini, Mini, bud, det_world, inv
from apg.det import findings as FD
from .helpers_det import approve_filled

from apg.det import signal as SG
FID = SG.identity_of('DET-R01', {'level': 'project', 'project': 'PRJ-001'}, 'CC-01')


def breach(extra=()):
    m = det_world()
    m.invoices(inv('INV-1', ex='5300000', cc='CC-01'), *extra)
    m.reconcile()
    return m


def first(m):
    out = m.ingest(m.detect())
    (fid,) = out['created']
    return fid, out


def person(m, token, user, *roles):
    return m.w.who(token, 'zero_one', user, roles)


class TestIngest(unittest.TestCase):
    def test_a_signal_becomes_one_finding_in_detected_status_with_history_and_a_pending_notification(self):
        m = breach()
        fid, out = first(m)
        f = FD.get(m.svc, fid)
        self.assertEqual((f['status'], f['version'], f['seen_count'], f['rule_id'], f['scope_key']), ('detected', 1, 1, 'DET-R01', 'project:PRJ-001'))
        self.assertEqual([h['event'] for h in f['history']], ['detected'])
        self.assertEqual(len(f['pending_notifications']), 1)
        self.assertEqual(f['pending_notifications'][0]['reason'], 'new')
        self.assertEqual(f['policy_unapproved'], False)
        self.assertEqual(out['rules_not_run'], [])
        self.assertIsNone(f['action'])
        self.assertEqual(f['signal']['rule']['params'], {'tolerance_bps': 500})

    def test_only_a_service_identity_with_the_service_role_can_ingest(self):
        m = breach()
        rec = m.detect()
        for who in (m.s, m.reviewer, person(m, 'x', 'xena', FD.SERVICE)):
            with self.assertRaises(FD.LifecycleError) as cm:
                FD.ingest_run(who, m.clock, m.detreg, rec['run_key'])
            self.assertEqual(cm.exception.code, 'SERVICE_REQUIRED')
        self.assertEqual(FD.all_findings(m.svc), [])

    def test_ingesting_the_same_run_twice_changes_nothing(self):
        m = breach()
        rec = m.detect()
        a = m.ingest(rec)
        before = FD.get(m.svc, FID)
        b = m.ingest(rec)
        self.assertTrue(b['replay'])
        self.assertEqual(FD.get(m.svc, FID), before)
        self.assertEqual(len(FD.all_findings(m.svc)), 1)
        self.assertEqual(a['created'], b['created'])

    def test_a_run_that_does_not_replay_is_refused(self):
        m = breach()
        with self.assertRaises(FD.LifecycleError) as cm:
            FD.ingest_run(m.svc, m.clock, m.detreg, 'no-such-run')
        self.assertEqual(cm.exception.code, 'RUN_DOES_NOT_VERIFY')

    def test_a_financial_calculation_run_is_not_accepted_as_a_detection_run(self):
        m = breach()
        fin = Mini.run(m, 'fin.actual_cost')
        with self.assertRaises(FD.LifecycleError):
            FD.ingest_run(m.svc, m.clock, m.detreg, fin['run_key'])
        self.assertEqual(FD.all_findings(m.svc), [])

    def test_the_same_condition_seen_again_updates_the_one_finding_and_never_creates_a_second(self):
        m = breach()
        first(m)
        m.clock.advance(86400)
        out = m.ingest(m.detect(as_of='2026-10-01'))
        self.assertEqual((out['created'], len(FD.all_findings(m.svc))), ([], 1))
        f = FD.get(m.svc, FID)
        self.assertEqual((f['seen_count'], f['version']), (2, 1))

    def test_a_figure_that_only_drifts_with_time_refreshes_without_a_new_version_or_notification(self):
        m = breach()
        first(m)
        m.flush = FD.flush_notifications(m.svc, m.clock, m.notifier)
        m.clock.advance(86400)
        out = m.ingest(m.detect(as_of='2026-10-01'))
        self.assertEqual(out['seen'], [FID])
        f = FD.get(m.svc, FID)
        self.assertEqual((f['version'], f['pending_notifications']), (1, []))
        self.assertEqual(f['signal']['explanation']['observed'][:22], 'actual cost to 2026-10')

    def test_new_evidence_makes_a_new_version_and_a_material_evidence_notification_outside_the_window_rules(self):
        m = breach()
        first(m)
        FD.flush_notifications(m.svc, m.clock, m.notifier)
        m.clock.advance(8 * 86400)                                                           # outside the 7 day window
        m.invoices(inv('INV-2', sin='SI-2', ex='100000', cc='CC-01'))
        m.reconcile()
        out = m.ingest(m.detect(as_of='2026-10-09'))
        self.assertEqual(out['updated'], [FID])
        f = FD.get(m.svc, FID)
        self.assertEqual(f['version'], 2)
        self.assertEqual([p['reason'] for p in f['pending_notifications']], ['material_evidence'])
        self.assertEqual(f['history'][-1]['event'], 'updated')

    def test_new_evidence_inside_the_suppression_window_is_recorded_as_suppressed_not_lost(self):
        m = breach()
        first(m)
        FD.flush_notifications(m.svc, m.clock, m.notifier)
        m.clock.advance(86400)
        m.invoices(inv('INV-2', sin='SI-2', ex='100000', cc='CC-01'))
        m.reconcile()
        m.ingest(m.detect(as_of='2026-10-01'))
        f = FD.get(m.svc, FID)
        self.assertEqual(f['pending_notifications'], [])
        self.assertEqual(f['notifications'][-1]['outcome'], 'suppressed')
        self.assertIn('INSIDE_SUPPRESSION_WINDOW', f['notifications'][-1]['detail'])

    def test_a_severity_increase_notifies_even_inside_the_window(self):
        m = breach()
        first(m)
        FD.flush_notifications(m.svc, m.clock, m.notifier)
        m.clock.advance(86400)
        m.invoices(inv('INV-2', sin='SI-2', ex='5000000', cc='CC-01'))                      # overrun 5.3M -> medium band
        m.reconcile()
        m.ingest(m.detect(as_of='2026-10-01'))
        f = FD.get(m.svc, FID)
        self.assertEqual([p['reason'] for p in f['pending_notifications']], ['severity_increase'])
        self.assertEqual(f['signal']['priority']['severity'], 'medium')

    def test_a_condition_that_is_not_redetected_is_marked_never_resolved_by_the_system(self):
        m = breach()
        fid, _ = first(m)
        m.clock.advance(86400)
        m.credits(['CRN-1', 'SUP-001', 'INV-1', '2026-09-25', '1000000', '100000'])
        m.reconcile()
        out = m.ingest(m.detect(as_of='2026-10-01'))
        self.assertEqual(out['not_redetected'], [fid])
        f = FD.get(m.svc, fid)
        self.assertEqual(f['status'], 'detected')
        self.assertEqual(f['not_redetected']['as_of'], '2026-10-01')
        self.assertEqual(f['history'][-1]['event'], 'not_redetected')

    def test_a_rule_that_did_not_run_says_nothing_about_its_findings(self):
        m = breach()
        fid, _ = first(m)
        m.clock.advance(86400)
        m.rules(R01={'enabled': False})
        out = m.ingest(m.detect(as_of='2026-10-01'))
        self.assertEqual((out['not_redetected'], out['rules_not_run']), ([], ['R01']))
        self.assertIsNone(FD.get(m.svc, fid)['not_redetected'])
        self.assertEqual(out['rules_not_run_detail']['R01']['status'], 'disabled')

    def test_an_older_run_cannot_overwrite_a_newer_one(self):
        m = breach()
        first(m)
        m.clock.advance(86400)
        old = m.detect(as_of='2026-09-29')
        m.clock.advance(86400)
        new = m.detect(as_of='2026-10-02')
        m.ingest(new)
        out = m.ingest(old)
        self.assertEqual(out['ignored_older'], [FID])
        self.assertEqual(FD.get(m.svc, FID)['last_seen']['as_of'], '2026-10-02')

    def test_an_unapproved_policy_marks_the_finding(self):
        m = det_world(approved=False)
        m.invoices(inv('INV-1', ex='5300000', cc='CC-01'))
        m.reconcile()
        first(m)
        self.assertTrue(FD.get(m.svc, FID)['policy_unapproved'])

    def test_ingest_leaves_an_audit_entry_and_the_summary(self):
        m = breach()
        rec = m.detect()
        m.ingest(rec)
        self.assertEqual(m.s.get(FD.INGEST_KIND, rec['run_key']).payload['created'], [FID])
        self.assertTrue(any(e.event_type == 'finding.ingested' for e in m.w.audit.read(m.s.ctx)))
        self.assertTrue(m.w.audit.verify(m.s.ctx))


class TestLifecycle(unittest.TestCase):
    def setUp(self):
        self.m = breach()
        self.fid, _ = first(self.m)
        self.clock = self.m.clock

    def t(self, who, to, **kw):
        if to == 'action_approved':                         # M6.5 (F-57): the lowest-level call refuses an approval that names less than the token
            return approve_filled(who, self.clock, self.fid, **kw)
        return FD.transition(who, self.clock, self.fid, to, **kw)

    def test_the_full_path_from_detected_to_resolved_with_role_and_evidence_gates(self):
        m = self.m
        self.assertEqual(self.t(m.reviewer, 'under_review')['status'], 'under_review')
        self.assertEqual(self.t(m.reviewer, 'confirmed', rationale='invoice and budget checked')['status'], 'confirmed')
        f = self.t(m.owner, 'action_proposed', action_text='re-forecast CC-01 and raise a variation')
        self.assertEqual((f['status'], f['action']['approved_by']), ('action_proposed', None))
        f = self.t(m.approver, 'action_approved', rationale='agreed')
        self.assertEqual(f['action']['approved_by'], 'abby')
        self.assertEqual(self.t(m.owner, 'in_progress')['status'], 'in_progress')
        f = self.t(m.owner, 'resolved', rationale='budget revised', evidence_ref='budget_line/PRJ-001|CC-01@R1')
        self.assertEqual((f['status'], f['disposition']['decision'], f['disposition']['by']), ('resolved', 'resolved', 'oscar'))
        self.assertEqual([h['to'] for h in f['history'] if h['event'] == 'status_change'], ['under_review', 'confirmed', 'action_proposed', 'action_approved', 'in_progress', 'resolved'])
        self.assertIsNone(f['disposition']['verified_outcome'])

    def test_a_transition_the_model_does_not_allow_is_refused(self):
        with self.assertRaises(FD.LifecycleError) as cm:
            self.t(self.m.reviewer, 'resolved', rationale='x', evidence_ref='y')
        self.assertEqual(cm.exception.code, 'TRANSITION_NOT_ALLOWED')
        with self.assertRaises(FD.LifecycleError) as cm:
            self.t(self.m.reviewer, 'confirmed', rationale='x')                                  # skips under_review
        self.assertEqual(cm.exception.code, 'TRANSITION_NOT_ALLOWED')

    def test_the_wrong_role_is_refused_and_the_refusal_is_audited(self):
        for who in (self.m.owner, self.m.approver, self.m.s):
            with self.assertRaises(FD.LifecycleError) as cm:
                self.t(who, 'under_review')
            self.assertEqual(cm.exception.code, 'ROLE_REQUIRED')
        refused = [e for e in self.m.w.audit.read(self.m.s.ctx) if e.event_type == 'finding.refused']
        self.assertEqual(len(refused), 3)
        self.assertEqual(FD.get(self.m.svc, self.fid)['status'], 'detected')

    def test_a_service_cannot_change_a_finding_status_even_with_the_role(self):
        svc = self.m.w.who('svc9', 'zero_one', 'detsvc9', (FD.REVIEWER,), 'service')
        with self.assertRaises(FD.LifecycleError) as cm:
            self.t(svc, 'under_review')
        self.assertEqual(cm.exception.code, 'HUMAN_REQUIRED')

    def test_dismiss_confirm_and_resolve_need_a_reason_and_resolve_needs_evidence(self):
        m = self.m
        with self.assertRaises(FD.LifecycleError) as cm:
            self.t(m.reviewer, 'dismissed')
        self.assertEqual(cm.exception.code, 'RATIONALE_REQUIRED')
        with self.assertRaises(FD.LifecycleError):
            self.t(m.reviewer, 'dismissed', rationale='   ')
        self.t(m.reviewer, 'under_review')
        self.t(m.reviewer, 'confirmed', rationale='ok')
        self.t(m.owner, 'action_proposed', action_text='do it')
        self.t(m.approver, 'action_approved', rationale='ok')
        self.t(m.owner, 'in_progress')
        with self.assertRaises(FD.LifecycleError) as cm:
            self.t(m.owner, 'resolved', rationale='done')
        self.assertEqual(cm.exception.code, 'EVIDENCE_REQUIRED')

    def test_an_action_needs_text(self):
        self.t(self.m.reviewer, 'under_review')
        self.t(self.m.reviewer, 'confirmed', rationale='ok')
        with self.assertRaises(FD.LifecycleError) as cm:
            self.t(self.m.owner, 'action_proposed')
        self.assertEqual(cm.exception.code, 'ACTION_REQUIRED')

    def test_nobody_approves_their_own_action(self):
        m = self.m
        both = person(m, 'both', 'bea', FD.OWNER, FD.APPROVER, FD.REVIEWER)
        self.t(both, 'under_review')
        self.t(both, 'confirmed', rationale='ok')
        self.t(both, 'action_proposed', action_text='do it')
        with self.assertRaises(FD.LifecycleError) as cm:
            self.t(both, 'action_approved', rationale='me too')
        self.assertEqual(cm.exception.code, 'SELF_APPROVAL')
        self.assertEqual(self.t(m.approver, 'action_approved', rationale='independent')['action']['approved_by'], 'abby')

    def test_dismissal_is_recorded_with_who_why_and_the_digest_it_was_decided_on(self):
        f = self.t(self.m.reviewer, 'dismissed', rationale='tolerance is wider on this job')
        d = f['disposition']
        self.assertEqual((d['decision'], d['by'], d['rationale']), ('dismissed', 'rita', 'tolerance is wider on this job'))
        self.assertEqual(d['digest_at_decision'], f['signal']['state_digest'])

    def test_supersede_names_another_stored_finding_and_is_terminal(self):
        m = self.m
        m.invoices(inv('INV-5', sin='SI-5', ex='9000000', cc='CC-02'))
        m.reconcile()
        m.ingest(m.detect(as_of='2026-09-29'))
        other = [f['finding_id'] for f in FD.all_findings(m.svc) if f['finding_id'] != self.fid][0]
        with self.assertRaises(FD.LifecycleError) as cm:
            self.t(m.reviewer, 'superseded', rationale='dup', superseded_by='nope')
        self.assertEqual(cm.exception.code, 'SUPERSEDING_FINDING_REQUIRED')
        with self.assertRaises(FD.LifecycleError):
            self.t(m.reviewer, 'superseded', rationale='dup', superseded_by=self.fid)
        f = self.t(m.reviewer, 'superseded', rationale='replaced by the cost code 2 finding', superseded_by=other)
        self.assertEqual(f['superseded_by'], other)
        with self.assertRaises(FD.LifecycleError) as cm:
            self.t(m.reviewer, 'under_review')
        self.assertEqual(cm.exception.code, 'TERMINAL')

    def test_an_unknown_status_is_refused(self):
        with self.assertRaises(FD.LifecycleError) as cm:
            self.t(self.m.reviewer, 'closed')
        self.assertEqual(cm.exception.code, 'UNKNOWN_STATUS')

    def test_a_realised_outcome_can_never_be_claimed(self):
        for who in (self.m.reviewer, self.m.owner, self.m.approver, self.m.svc):
            with self.assertRaises(FD.LifecycleError) as cm:
                FD.claim_realised(who, self.fid, 100)
            self.assertEqual(cm.exception.code, 'VERIFICATION_NOT_AVAILABLE')
        self.assertIsNone(FD.get(self.m.svc, self.fid)['disposition'])

    def test_a_status_change_notifies_only_as_the_policy_and_window_allow(self):
        m = self.m
        FD.flush_notifications(m.svc, self.clock, m.notifier)
        f = self.t(m.reviewer, 'under_review')
        self.assertEqual(f['pending_notifications'], [])                                    # inside the window after the first send
        self.assertEqual(f['notifications'][-1]['outcome'], 'suppressed')
        self.clock.advance(8 * 86400)
        f = self.t(m.reviewer, 'dismissed', rationale='no')
        self.assertEqual([p['reason'] for p in f['pending_notifications']], ['status_transition'])

    def test_concurrent_edits_are_refused_not_overwritten(self):
        m = self.m
        rec = m.s.get(FD.KIND, self.fid)
        FD.assign(m.reviewer, self.clock, self.fid, 'carol')                               # another person changes the finding first
        with self.assertRaises(Exception):
            m.s.put(FD.KIND, self.fid, rec.payload, expected_revision=rec.revision)

    def test_assignment_defer_and_link_rules(self):
        m = self.m
        f = FD.assign(m.owner, self.clock, self.fid, 'carol', next_review='2026-10-20')
        self.assertEqual((f['ownership']['assignee'], f['ownership']['next_review']), ('carol', '2026-10-20'))
        with self.assertRaises(FD.LifecycleError):
            FD.assign(m.approver, self.clock, self.fid, 'x')
        with self.assertRaises(FD.LifecycleError):
            FD.assign(m.owner, self.clock, self.fid, ' ')
        f = FD.defer(m.reviewer, self.clock, self.fid, '2026-11-15', 'waiting for the forecast')
        self.assertEqual((f['status'], f['ownership']['deferred']['until']), ('detected', '2026-11-15'))
        with self.assertRaises(FD.LifecycleError):
            FD.defer(m.reviewer, self.clock, self.fid, '2026-11-15', '')
        with self.assertRaises(FD.LifecycleError):
            FD.defer(m.owner, self.clock, self.fid, '2026-11-15', 'x')                          # deferral is a reviewer act
        self.t(m.reviewer, 'dismissed', rationale='no')
        with self.assertRaises(FD.LifecycleError) as cm:
            FD.defer(m.reviewer, self.clock, self.fid, '2026-12-01', 'later')
        self.assertEqual(cm.exception.code, 'NOT_ACTIVE')


class TestReopening(unittest.TestCase):
    def setUp(self):
        self.m = breach()
        self.fid, _ = first(self.m)
        self.m.clock.advance(3600)
        FD.transition(self.m.reviewer, self.m.clock, self.fid, 'dismissed', rationale='accepted overrun')

    def test_a_dismissed_finding_stays_dismissed_while_the_evidence_is_unchanged(self):
        self.m.clock.advance(86400)
        out = self.m.ingest(self.m.detect(as_of='2026-10-01'))
        self.assertEqual((out['kept_dismissed'], out['reopened']), ([self.fid], []))
        f = FD.get(self.m.svc, self.fid)
        self.assertEqual((f['status'], f['seen_count']), ('dismissed', 2))

    def test_a_dismissed_finding_reopens_when_the_evidence_changes_and_notifies(self):
        m = self.m
        m.clock.advance(86400)
        m.invoices(inv('INV-2', sin='SI-2', ex='400000', cc='CC-01'))
        m.reconcile()
        out = m.ingest(m.detect(as_of='2026-10-01'))
        self.assertEqual(out['reopened'], [self.fid])
        f = FD.get(m.svc, self.fid)
        self.assertEqual((f['status'], f['reopen_count'], f['version']), ('reopened', 1, 2))
        self.assertIn('reopened', [p['reason'] for p in f['pending_notifications']])
        self.assertEqual(f['history'][-1]['event'], 'reopened')

    def test_a_run_created_before_the_decision_cannot_undo_it(self):
        m = self.m
        m.invoices(inv('INV-2', sin='SI-2', ex='400000', cc='CC-01'))                      # new evidence: a later run would reopen
        m.reconcile()
        run_before = m.detect(as_of='2026-10-01')                                            
        m.clock.advance(7200)
        FD.transition(m.reviewer, m.clock, self.fid, 'reopened', rationale='look')
        FD.transition(m.reviewer, m.clock, self.fid, 'dismissed', rationale='accepted again')
        out = m.ingest(run_before)
        self.assertEqual((out['reopened'], out['ignored_older']), ([], [self.fid]))
        self.assertEqual(FD.get(m.svc, self.fid)['status'], 'dismissed')

    def test_a_person_can_reopen_a_dismissed_finding_with_a_reason(self):
        f = FD.transition(self.m.reviewer, self.m.clock, self.fid, 'reopened', rationale='new information')
        self.assertEqual((f['status'], f['reopen_count']), ('reopened', 1))
        with self.assertRaises(FD.LifecycleError):
            FD.transition(self.m.reviewer, self.m.clock, self.fid, 'confirmed', rationale='x')

    def test_a_resolved_finding_reappearing_is_reopened_by_the_system_for_a_person_to_judge(self):
        m = self.m
        FD.transition(m.reviewer, m.clock, self.fid, 'reopened', rationale='look again')
        FD.transition(m.reviewer, m.clock, self.fid, 'under_review')
        FD.transition(m.reviewer, m.clock, self.fid, 'confirmed', rationale='yes')
        FD.transition(m.owner, m.clock, self.fid, 'action_proposed', action_text='fix')
        approve_filled(m.approver, m.clock, self.fid, rationale='ok')
        FD.transition(m.owner, m.clock, self.fid, 'in_progress')
        FD.transition(m.owner, m.clock, self.fid, 'resolved', rationale='fixed', evidence_ref='x/y')
        m.clock.advance(86400)
        out = m.ingest(m.detect(as_of='2026-10-01'))
        self.assertEqual(out['reopened'], [self.fid])
        self.assertEqual(FD.get(m.svc, self.fid)['status'], 'reopened')


class TestNotifications(unittest.TestCase):
    def setUp(self):
        self.m = breach()
        self.fid, _ = first(self.m)

    def test_flush_sends_each_pending_note_once_and_records_the_receipt(self):
        m = self.m
        self.assertEqual(FD.flush_notifications(m.svc, m.clock, m.notifier), {'sent': 1, 'duplicate': 0, 'failed': 0})
        f = FD.get(m.svc, self.fid)
        self.assertEqual((f['pending_notifications'], f['notifications'][-1]['outcome']), ([], 'sent'))
        self.assertEqual(FD.flush_notifications(m.svc, m.clock, m.notifier), {'sent': 0, 'duplicate': 0, 'failed': 0})
        delivered = m.notifier._contract_delivered('zero_one')
        self.assertEqual(len(delivered), 1)
        self.assertEqual(delivered[0]['recipient_role'], 'project_manager')
        self.assertIn('A signal is not a conclusion', delivered[0]['body'])

    def test_a_delivery_failure_stays_pending_and_visible_then_is_sent_later_without_a_duplicate(self):
        m = self.m
        m.notifier._contract_set_transport_failure(True)
        self.assertEqual(FD.flush_notifications(m.svc, m.clock, m.notifier), {'sent': 0, 'duplicate': 0, 'failed': 1})
        out = FD.outstanding_notifications(m.svc)
        self.assertEqual((len(out), out[0][2], out[0][3]), (1, 1, 'TRANSPORT_UNAVAILABLE'))
        self.assertEqual(FD.get(m.svc, self.fid)['notifications'][-1]['outcome'], 'failed')
        m.notifier._contract_set_transport_failure(False)
        self.assertEqual(FD.flush_notifications(m.svc, m.clock, m.notifier)['sent'], 1)
        self.assertEqual(FD.outstanding_notifications(m.svc), [])
        self.assertEqual(len(m.notifier._contract_delivered('zero_one')), 1)

    def test_a_port_that_already_has_the_note_reports_a_duplicate_which_is_recorded(self):
        m = self.m
        f = FD.get(m.svc, self.fid)
        note = dict(f['pending_notifications'][0])
        m.notifier.send(m.svc.ctx, {'dedup_key': note['dedup_key'], 'recipient_role': note['recipient_role'], 'subject': note['subject'], 'body': note['body'], 'finding_id': self.fid, 'reason': note['reason']})
        self.assertEqual(FD.flush_notifications(m.svc, m.clock, m.notifier), {'sent': 0, 'duplicate': 1, 'failed': 0})
        self.assertEqual(FD.get(m.svc, self.fid)['notifications'][-1]['outcome'], 'duplicate')
        self.assertEqual(len(m.notifier._contract_delivered('zero_one')), 1)

    def test_only_a_service_flushes(self):
        with self.assertRaises(FD.LifecycleError):
            FD.flush_notifications(self.m.reviewer, self.m.clock, self.m.notifier)

    def test_the_note_never_states_a_conclusion_and_says_when_nothing_is_quantified(self):
        m = self.m
        n = FD.get(m.svc, self.fid)['pending_notifications'][0]
        self.assertNotIn('saving', n['body'].lower())
        self.assertNotIn('realised', n['body'].lower())
        self.assertIn('estimate', n['body'])
