"""M7: the recommendation lifecycle (Section 10 sections 5, 9, 10; PG-RS-AC-08, 09, 11).  Approval is a person's decision bound to what was shown; nothing is executed."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_rec import RecWorld
from apg.det import findings as FD
from apg.rec import engine as E, inputs as IN, lifecycle as L


class Base(unittest.TestCase):
    def setUp(self):
        self.w = RecWorld()
        self.f = self.w.finding(gross=500000)
        self.rid = self.w.ready(self.f)
        self.w.run()

    def submit(self):
        L.submit(self.w.owner2, self.w.clock, self.rid)
        r = L.get(self.w.s, self.rid)
        return r, L.approval_token(r)

    def code(self, fn):
        with self.assertRaises(L.RecError) as cm:
            fn()
        return cm.exception.code


class TestService(Base):
    def test_a_new_run_creates_one_generated_record_per_finding(self):
        r = L.get(self.w.s, self.rid)
        self.assertEqual((r['status'], r['version'], r['finding_id']), ('generated', 1, self.f))
        self.assertEqual(r['history'][0]['event'], 'generated')

    def test_only_the_recommendation_service_ingests_and_a_replay_is_a_no_op(self):
        run = E.run(self.w.s, self.w.reg, self.w.clock, '2026-09-30', self.w.policy['version'])
        for who in (self.w.owner, self.w.det, self.w.ai):
            with self.subTest(who=who.ctx.user_id):
                self.assertEqual(self.code(lambda: L.ingest_run(who, self.w.clock, self.w.reg, run['run_key'])), 'SERVICE_REQUIRED')
        L.ingest_run(self.w.svc, self.w.clock, self.w.reg, run['run_key'])
        self.assertTrue(L.ingest_run(self.w.svc, self.w.clock, self.w.reg, run['run_key'])['replay'])

    def test_a_run_that_does_not_verify_is_refused(self):
        from apg import repro
        run = E.run(self.w.s, self.w.reg, self.w.clock, '2026-10-01', self.w.policy['version'])
        rec = self.w.s.get(repro.KIND, run['run_key'])
        p = dict(rec.payload)
        p['result'] = dict(p['result'], ranked=[])
        self.w.s.put(repro.KIND, run['run_key'], p, expected_revision=rec.revision)
        self.assertEqual(self.code(lambda: L.ingest_run(self.w.svc, self.w.clock, self.w.reg, run['run_key'])), 'RUN_DOES_NOT_VERIFY')

    def test_an_older_run_cannot_overwrite_a_newer_one(self):
        self.w.run(as_of='2026-10-05')
        r1 = L.get(self.w.s, self.rid)
        old = E.run(self.w.s, self.w.reg, self.w.clock, '2026-09-29', self.w.policy['version'])
        s = L.ingest_run(self.w.svc, self.w.clock, self.w.reg, old['run_key'])
        self.assertIn(self.rid, s['ignored_older'])
        self.assertEqual(L.get(self.w.s, self.rid)['as_of'], r1['as_of'])

    def test_a_material_change_is_a_new_version_and_an_unchanged_one_is_not(self):
        self.w.run(as_of='2026-10-01')
        self.assertEqual(L.get(self.w.s, self.rid)['version'], 1)
        IN.set_inputs(self.w.owner, self.w.clock, self.rid, incremental_costs=[{'component': 'qualification', 'cents': 200000, 'basis': 'three days'}])
        self.w.run(as_of='2026-10-01')
        r = L.get(self.w.s, self.rid)
        self.assertEqual((r['version'], len(r['versions'])), (2, 2))
        self.assertEqual(r['current']['dimensions']['implementation_cost']['cents'], 200000)

    def test_a_dismissed_finding_marks_its_recommendation_excluded_without_deleting_it(self):
        FD.transition(self.w.rev, self.w.clock, self.f, 'superseded', rationale='duplicate', superseded_by=self.w.finding())
        s = L.ingest_run(self.w.svc, self.w.clock, self.w.reg, E.run(self.w.s, self.w.reg, self.w.clock, '2026-10-01', self.w.policy['version'])['run_key'])
        self.assertIn(self.rid, s['finding_excluded'])
        r = L.get(self.w.s, self.rid)
        self.assertEqual(r['status'], 'generated')
        self.assertIn('superseded', r['excluded_since']['why'])


class TestApproval(Base):
    def test_the_full_path_keeps_recommendation_approval_and_outcome_distinct(self):
        r, t = self.submit()
        self.assertEqual(r['status'], 'awaiting_approval')
        self.assertIsNone(r['approval'])
        a = L.approve(self.w.pm, self.w.clock, self.rid, t['version'], t['digest'], t['submission'], 'worth doing')
        self.assertEqual((a['status'], a['approval']['by'], a['approval']['role']), ('approved', 'pete', 'project_manager'))
        self.assertIn('does not prove', a['approval']['note'])
        self.assertIsNone(a['implementation'])
        self.assertIsNone(a['outcome'])
        s = L.transition(self.w.owner2, self.w.clock, self.rid, 'in_progress')
        self.assertIn('outside APG', s['implementation']['note'] + ' outside APG')
        c = L.transition(self.w.owner2, self.w.clock, self.rid, 'completed_pending_verification', evidence_refs=[('ap_invoice', 'INV-1', 1)])
        self.assertEqual(c['status'], 'completed_pending_verification')
        self.assertIsNone(c['outcome'])
        self.assertEqual(self.code(lambda: L.transition(self.w.owner2, self.w.clock, self.rid, 'verified_outcome')), 'USE_VERIFICATION')

    def test_the_approval_token_is_required_whole(self):
        r, t = self.submit()
        for v, d, s in ((None, t['digest'], t['submission']), (t['version'], None, t['submission']), (t['version'], t['digest'], None), (True, t['digest'], t['submission']),
                        (1.0, t['digest'], t['submission']), (t['version'], ' ', t['submission'])):
            with self.subTest(v=v, d=d, s=s):
                self.assertEqual(self.code(lambda: L.approve(self.w.pm, self.w.clock, self.rid, v, d, s, 'x')), 'APPROVAL_TOKEN_REQUIRED')
        self.assertEqual(self.code(lambda: L.transition(self.w.pm, self.w.clock, self.rid, 'approved', rationale='x')), 'APPROVAL_TOKEN_REQUIRED')

    def test_a_stale_or_different_token_is_refused(self):
        r, t = self.submit()
        self.assertEqual(self.code(lambda: L.approve(self.w.pm, self.w.clock, self.rid, t['version'] + 1, t['digest'], t['submission'], 'x')), 'STALE_APPROVAL')
        self.assertEqual(self.code(lambda: L.approve(self.w.pm, self.w.clock, self.rid, t['version'], 'f' * 24, t['submission'], 'x')), 'STALE_APPROVAL')
        self.assertEqual(self.code(lambda: L.approve(self.w.pm, self.w.clock, self.rid, t['version'], t['digest'], 'x' * 24, 'x')), 'SUBMISSION_CHANGED')

    def test_a_withdrawn_and_resubmitted_recommendation_needs_the_new_submission_reference(self):
        r, t = self.submit()
        L.transition(self.w.owner2, self.w.clock, self.rid, 'generated', rationale='more checks')
        L.submit(self.w.owner2, self.w.clock, self.rid)
        self.assertEqual(self.code(lambda: L.approve(self.w.pm, self.w.clock, self.rid, t['version'], t['digest'], t['submission'], 'x')), 'SUBMISSION_CHANGED')
        t2 = L.approval_token(L.get(self.w.s, self.rid))
        self.assertNotEqual(t2['submission'], t['submission'])
        self.assertEqual(L.approve(self.w.pm, self.w.clock, self.rid, t2['version'], t2['digest'], t2['submission'], 'ok')['status'], 'approved')

    def test_separation_of_duties(self):
        sub_and_pm = self.w.w.who('x1', 'zero_one', 'opal', ('project_manager',), ttl=10 ** 8)      # opal submitted it
        author_pm = self.w.w.who('x2', 'zero_one', 'olly', ('project_manager',), ttl=10 ** 8)       # olly wrote the inputs
        r, t = self.submit()
        self.assertEqual(self.code(lambda: L.approve(sub_and_pm, self.w.clock, self.rid, t['version'], t['digest'], t['submission'], 'x')), 'SELF_APPROVAL')
        self.assertEqual(self.code(lambda: L.approve(author_pm, self.w.clock, self.rid, t['version'], t['digest'], t['submission'], 'x')), 'SELF_APPROVAL')
        self.assertEqual(self.code(lambda: L.transition(author_pm, self.w.clock, self.rid, 'rejected', rationale='x')), 'SELF_APPROVAL')

    def test_no_machine_acts_on_a_recommendation(self):
        r, t = self.submit()
        self.assertEqual(self.code(lambda: L.approve(self.w.ai, self.w.clock, self.rid, t['version'], t['digest'], t['submission'], 'x')), 'HUMAN_REQUIRED')
        for to in ('rejected', 'generated', 'deferred', 'closed_without_implementation'):
            self.assertEqual(self.code(lambda: L.transition(self.w.ai, self.w.clock, self.rid, to, rationale='x', until='2026-12-01')), 'HUMAN_REQUIRED')
        self.assertEqual(self.code(lambda: L.transition(self.w.svc, self.w.clock, self.rid, 'rejected', rationale='x')), 'HUMAN_REQUIRED')

    def test_a_change_after_approval_ends_the_approval_and_needs_a_fresh_one(self):
        r, t = self.submit()
        L.approve(self.w.pm, self.w.clock, self.rid, t['version'], t['digest'], t['submission'], 'ok')
        IN.set_inputs(self.w.owner, self.w.clock, self.rid, expected_benefit={'cents': 900000, 'basis': 'revised'})
        s = L.ingest_run(self.w.svc, self.w.clock, self.w.reg, E.run(self.w.s, self.w.reg, self.w.clock, '2026-10-01', self.w.policy['version'])['run_key'])
        self.assertEqual((s['approvals_ended'], s['submissions_ended'], s['new_version']), ([self.rid], [self.rid], [self.rid]))
        r = L.get(self.w.s, self.rid)
        self.assertEqual((r['status'], r['version'], r['approval']['state']), ('generated', 2, 'ended'))
        self.assertEqual(r['approval_history'][0]['ended_because'], 'the recommendation changed after it was approved')
        self.assertFalse(L.approval_current(r))
        self.assertEqual(self.code(lambda: L.transition(self.w.owner2, self.w.clock, self.rid, 'in_progress')), 'TRANSITION_NOT_ALLOWED')

    def test_starting_needs_an_approval_still_in_force(self):
        r, t = self.submit()
        L.approve(self.w.pm, self.w.clock, self.rid, t['version'], t['digest'], t['submission'], 'ok')
        rec = self.w.s.get(L.KIND, self.rid)
        p = dict(rec.payload)
        p['approval'] = dict(p['approval'], version=99)
        self.w.s.put(L.KIND, self.rid, p, expected_revision=rec.revision)
        self.assertEqual(self.code(lambda: L.transition(self.w.owner2, self.w.clock, self.rid, 'in_progress')), 'APPROVAL_NOT_CURRENT')

    def test_evidence_changing_while_in_progress_is_recorded_not_hidden(self):
        r, t = self.submit()
        L.approve(self.w.pm, self.w.clock, self.rid, t['version'], t['digest'], t['submission'], 'ok')
        L.transition(self.w.owner2, self.w.clock, self.rid, 'in_progress')
        IN.set_inputs(self.w.owner, self.w.clock, self.rid, risks=['the supplier may be late'])
        self.w.run(as_of='2026-10-01')
        r = L.get(self.w.s, self.rid)
        self.assertEqual(r['status'], 'in_progress')
        self.assertIn('approval_ended_while_in_progress', [h['event'] for h in r['history']])
        self.assertFalse(L.approval_current(r))

    def test_completion_needs_stored_implementation_evidence(self):
        r, t = self.submit()
        L.approve(self.w.pm, self.w.clock, self.rid, t['version'], t['digest'], t['submission'], 'ok')
        L.transition(self.w.owner2, self.w.clock, self.rid, 'in_progress')
        for refs in ((), [('ap_invoice', 'NOPE', 1)], [('ap_invoice', 'INV-1', 7)], [('ap_invoice', 'INV-1')], ['ap_invoice/INV-1']):
            with self.subTest(refs=refs):
                self.assertEqual(self.code(lambda: L.transition(self.w.owner2, self.w.clock, self.rid, 'completed_pending_verification', evidence_refs=refs)), 'IMPLEMENTATION_EVIDENCE_REQUIRED')

    def test_execute_is_always_refused(self):
        r, t = self.submit()
        L.approve(self.w.pm, self.w.clock, self.rid, t['version'], t['digest'], t['submission'], 'ok')
        for who in (self.w.owner2, self.w.director, self.w.svc, self.w.ai):
            self.assertEqual(self.code(lambda: L.execute(who, self.rid, 'place the order')), 'NO_AUTONOMOUS_EXECUTION')


class TestAuditability(Base):
    def test_rejected_deferred_withdrawn_and_closed_recommendations_stay_with_their_reasons(self):
        r, t = self.submit()
        L.transition(self.w.pm, self.w.clock, self.rid, 'rejected', rationale='not now')
        L.transition(self.w.owner2, self.w.clock, self.rid, 'closed_without_implementation', rationale='rejected by the PM')
        r = L.get(self.w.s, self.rid)
        self.assertEqual(r['status'], 'closed_without_implementation')
        self.assertEqual(r['decision']['rationale'], 'not now')
        self.assertEqual([(h['from'], h['to']) for h in r['history'] if h['event'] == 'status_change'],
                         [('generated', 'awaiting_approval'), ('awaiting_approval', 'rejected'), ('rejected', 'closed_without_implementation')])
        self.assertEqual(self.code(lambda: L.transition(self.w.owner2, self.w.clock, self.rid, 'generated', rationale='x')), 'TERMINAL')
        self.assertIn(self.rid, [x['rec_id'] for x in L.all_recs(self.w.s, 'closed_without_implementation')])
        events = [e for e in self.w.w.audit.read(self.w.s.ctx) if e.resource == L.KIND + '/' + self.rid and e.event_type == 'rec.transition']
        self.assertEqual(len(events), 3)
        self.assertTrue(self.w.w.audit.verify(self.w.s.ctx).ok)

    def test_a_deferral_needs_a_date_and_a_reason_and_ends_when_the_date_comes(self):
        self.assertEqual(self.code(lambda: L.transition(self.w.owner2, self.w.clock, self.rid, 'deferred', rationale='x')), 'DATE_REQUIRED')
        self.assertEqual(self.code(lambda: L.transition(self.w.owner2, self.w.clock, self.rid, 'deferred', until='2026-10-10')), 'RATIONALE_REQUIRED')
        for bad in ('2026-02-30', '2026/10/10', '20261010xx', 20261010):
            self.assertEqual(self.code(lambda: L.transition(self.w.owner2, self.w.clock, self.rid, 'deferred', rationale='x', until=bad)), 'DATE_REQUIRED')
        L.transition(self.w.owner2, self.w.clock, self.rid, 'deferred', rationale='wait for the programme update', until='2026-10-10')
        self.w.run(as_of='2026-10-09')
        self.assertEqual(L.get(self.w.s, self.rid)['status'], 'deferred')
        s = L.ingest_run(self.w.svc, self.w.clock, self.w.reg, E.run(self.w.s, self.w.reg, self.w.clock, '2026-10-10', self.w.policy['version'])['run_key'])
        self.assertIn(self.rid, s['deferrals_ended'])
        r = L.get(self.w.s, self.rid)
        self.assertEqual((r['status'], r['deferral']['rationale']), ('generated', 'wait for the programme update'))

    def test_disallowed_moves_and_roles(self):
        self.assertEqual(self.code(lambda: L.transition(self.w.owner2, self.w.clock, self.rid, 'approved', rationale='x')), 'TRANSITION_NOT_ALLOWED')
        self.assertEqual(self.code(lambda: L.transition(self.w.owner2, self.w.clock, self.rid, 'in_progress')), 'TRANSITION_NOT_ALLOWED')
        self.assertEqual(self.code(lambda: L.transition(self.w.pm, self.w.clock, self.rid, 'awaiting_evidence', rationale='x')), 'ROLE_REQUIRED')
        self.assertEqual(self.code(lambda: L.transition(self.w.owner2, self.w.clock, self.rid, 'awaiting_evidence')), 'RATIONALE_REQUIRED')
        self.assertEqual(self.code(lambda: L.transition(self.w.owner2, self.w.clock, self.rid, 'nonsense')), 'UNKNOWN_STATUS')
        self.assertEqual(self.code(lambda: L.transition(self.w.owner2, self.w.clock, 'REC-nope', 'deferred', rationale='x', until='2026-12-01')), 'RECOMMENDATION_UNKNOWN')

    def test_awaiting_evidence_and_back(self):
        L.transition(self.w.owner2, self.w.clock, self.rid, 'awaiting_evidence', rationale='need the delivery dockets')
        L.transition(self.w.owner2, self.w.clock, self.rid, 'generated', rationale='dockets received')
        self.assertEqual(L.get(self.w.s, self.rid)['status'], 'generated')


class TestTenancy(unittest.TestCase):
    def test_another_tenant_sees_nothing(self):
        a = RecWorld('zero_one')
        a.finding()
        a.run()
        b_who = a.w.who('other', 'zero_two', 'zed', (L.SERVICE,), 'service', ttl=10 ** 8)
        self.assertEqual(L.all_recs(b_who), [])
        run_key = a.s.query('repro_record')[-1].key
        self.assertIsNone(b_who.get('repro_record', run_key))


if __name__ == '__main__':
    unittest.main()
