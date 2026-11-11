"""APG-M7.1 corrections after the independent audit of APG-M7.
F-64  submission and approval accepted a recommendation whose finding or mandatory review had changed after the run (the record was a stale snapshot);
F-65  the start of work was accepted after the finding changed following approval;
F-66  a policy approval could be asserted by caller-supplied approver, role and kind fields.
Run against the delivered M7 code, the tests of the first three classes and most of the fourth fail or error; here they pass."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_rec import COMPLETE_ALT, RecWorld
from apg import canon, repro
from apg.det import findings as FD
from apg.rec import demo_rec as DR, engine as E, inputs as IN, lifecycle as L, policy as RP


def code(fn):
    try:
        fn()
    except (L.RecError, IN.InputError, RP.RecPolicyError) as e:
        return e.code if hasattr(e, 'code') else 'REFUSED'
    return None


class Base(unittest.TestCase):
    family = 'quality_defects'

    def setUp(self):
        self.w = RecWorld()
        self.f = self.w.finding(family=self.family, gross=500000, missing=('the inspection report',))
        self.rid = self.w.ready(self.f)
        self.w.run()

    def submit(self):
        return code(lambda: L.submit(self.w.owner2, self.w.clock, self.rid))

    def approve(self):
        r = L.get(self.w.s, self.rid)
        t = L.approval_token(r)
        return code(lambda: L.approve(self.w.pm, self.w.clock, self.rid, t['version'], t['digest'], t['submission'], 'ok'))

    def start(self):
        return code(lambda: L.transition(self.w.owner2, self.w.clock, self.rid, 'in_progress'))


class TestStaleAtSubmission(Base):
    """F-64: every change to a source after the run is refused at submission until the engine runs again."""
    def changes(self):
        w, f, rid = self.w, self.f, self.rid
        return {
            'the finding is dismissed': lambda: FD.transition(w.rev, w.clock, f, 'dismissed', rationale='not real'),
            'the finding is superseded': lambda: FD.transition(w.rev, w.clock, f, 'superseded', rationale='duplicate', superseded_by=w.finding()),
            'the mandatory review is changed to not cleared': lambda: IN.record_review(w.creview, w.clock, rid, 'quality', 'not_cleared', 'fails the specification'),
            'the mandatory review is recorded again as cleared (a favourable change is still a change)': lambda: IN.record_review(w.creview, w.clock, rid, 'quality', 'cleared', 'again'),
            'an incremental cost is changed': lambda: IN.set_inputs(w.owner, w.clock, rid, incremental_costs=[{'component': 'qualification', 'cents': 400000, 'basis': 'a week'}]),
            'the expected benefit is changed': lambda: IN.set_inputs(w.owner, w.clock, rid, expected_benefit={'cents': 1, 'basis': 'revised'}),
            'an evidence assessment is reversed': lambda: IN.record_evidence_assessment(w.creview, w.clock, rid, 'the inspection report', True, 'needed after all'),
            'the alternatives are changed': lambda: IN.set_inputs(w.owner, w.clock, rid, alternatives=[]),
            'the policy gets a further approval': lambda: RP.approve_policy(w.w.who('r2', 'zero_one', 'rhea', (RP.POLICY_ROLE,), ttl=10 ** 8), w.clock, w.policy['version'], 'second'),
            'the finding is refreshed by detection without a material change': lambda: w.det.put(FD.KIND, f, dict(w.s.get(FD.KIND, f).payload, seen_count=9), expected_revision=w.s.get(FD.KIND, f).revision),
        }

    def test_each_change_is_refused_at_submission(self):
        for what in self.changes():
            with self.subTest(change=what):
                self.setUp()
                self.changes()[what]()
                self.assertEqual(self.submit(), 'SOURCE_CHANGED', what)
                self.assertEqual(L.get(self.w.s, self.rid)['status'], 'generated')

    def test_the_refusal_says_what_changed(self):
        FD.transition(self.w.rev, self.w.clock, self.f, 'dismissed', rationale='not real')
        with self.assertRaises(L.RecError) as cm:
            L.submit(self.w.owner2, self.w.clock, self.rid)
        self.assertIn('the finding %s changed since the run' % self.f, str(cm.exception))
        self.assertIn('no longer recommended on', str(cm.exception))
        self.assertIn('Run the recommendation engine again', str(cm.exception))
        ev = [e for e in self.w.w.audit.read(self.w.s.ctx) if e.event_type == 'rec.refused' and e.resource == L.KIND + '/' + self.rid]
        self.assertTrue(ev and 'no longer matches its sources' in ev[-1].reason)

    def test_the_refusal_names_the_revisions(self):
        IN.record_review(self.w.creview, self.w.clock, self.rid, 'quality', 'not_cleared', 'fails')
        with self.assertRaises(L.RecError) as cm:
            L.submit(self.w.owner2, self.w.clock, self.rid)
        n = self.w.s.get(IN.KIND, self.rid).revision
        self.assertIn('changed since the run (revision %d then, %d now)' % (n - 1, n), str(cm.exception))
        w = RecWorld()
        f = w.finding(gross=500000)
        w.run()
        IN.set_inputs(w.owner, w.clock, w.rid(f), risks=['first inputs after the run'])
        with self.assertRaises(L.RecError) as cm:
            L.submit(w.owner2, w.clock, w.rid(f))
        self.assertIn('(revision absent then, 1 now)', str(cm.exception))

    def test_after_a_fresh_run_the_new_version_is_what_counts(self):
        IN.record_review(self.w.creview, self.w.clock, self.rid, 'quality', 'not_cleared', 'fails')
        self.w.run(as_of='2026-10-01')
        r = L.get(self.w.s, self.rid)
        self.assertEqual(r['version'], 2)
        self.assertIn('quality review did not clear the action', r['current']['constraints']['blocked_by'])
        self.assertEqual(self.submit(), 'NOT_SUBMITTABLE')
        FD.transition(self.w.rev, self.w.clock, self.f, 'dismissed', rationale='not real')
        self.w.run(as_of='2026-10-02')
        self.assertEqual(self.submit(), 'SOURCE_CHANGED')                  # dismissed: excluded from the run, so the record can never be current again

    def test_a_new_finding_that_overlaps_is_caught_by_the_recomputation(self):
        refs = self.w.s.get(FD.KIND, self.f).payload['signal']['evidence'][0]['ref']
        self.w.finding(family='quality_defects', gross=900000, refs=[refs])          # rests on the same record: same overlap component, not pinned by the run
        with self.assertRaises(L.RecError) as cm:
            L.submit(self.w.owner2, self.w.clock, self.rid)
        self.assertEqual(cm.exception.code, 'SOURCE_CHANGED')
        self.assertIn('a run now would give this recommendation different content', str(cm.exception))

    def test_an_unchanged_recommendation_is_submitted_normally(self):
        self.assertIsNone(self.submit())
        self.assertIsNone(self.approve())
        self.assertIsNone(self.start())

    def test_a_change_elsewhere_in_the_tenant_does_not_block_it(self):
        self.w.finding(gross=100, project='PRJ-002')
        self.assertIsNone(self.submit())

    def test_a_check_that_cannot_be_completed_refuses(self):
        rec = self.w.s.get(L.KIND, self.rid)
        self.w.s.put(L.KIND, self.rid, dict(rec.payload, run_key='0' * 32), expected_revision=rec.revision)
        self.assertEqual(self.submit(), 'SOURCE_CHANGED')


class TestStaleBetweenSubmissionAndApproval(Base):
    def test_a_change_after_submission_is_refused_at_approval(self):
        self.assertIsNone(self.submit())
        FD.transition(self.w.rev, self.w.clock, self.f, 'dismissed', rationale='not real')
        self.assertEqual(self.approve(), 'SOURCE_CHANGED')
        IN.record_review(self.w.creview, self.w.clock, self.rid, 'quality', 'not_cleared', 'fails')
        self.assertEqual(self.approve(), 'SOURCE_CHANGED')
        self.assertIsNone(L.get(self.w.s, self.rid)['approval'])

    def test_a_non_material_refresh_needs_a_run_and_then_the_submission_stands(self):
        self.assertIsNone(self.submit())
        rec = self.w.s.get(FD.KIND, self.f)
        self.w.det.put(FD.KIND, self.f, dict(rec.payload, seen_count=rec.payload['seen_count'] + 1), expected_revision=rec.revision)
        self.assertEqual(self.approve(), 'SOURCE_CHANGED')
        self.w.run(as_of='2026-09-30')
        r = L.get(self.w.s, self.rid)
        self.assertEqual((r['status'], r['version']), ('awaiting_approval', 1))      # nothing material changed: the submission is still the one on record
        self.assertIsNone(self.approve())


class TestStaleBetweenApprovalAndStart(Base):
    """F-65."""
    def setUp(self):
        super().setUp()
        self.assertIsNone(self.submit())
        self.assertIsNone(self.approve())

    def test_each_change_after_approval_is_refused_at_the_start(self):
        for what, fn in (('the finding is dismissed', lambda: FD.transition(self.w.rev, self.w.clock, self.f, 'dismissed', rationale='not real')),
                         ('the review is changed', lambda: IN.record_review(self.w.creview, self.w.clock, self.rid, 'quality', 'not_cleared', 'fails')),
                         ('a cost is changed', lambda: IN.set_inputs(self.w.owner, self.w.clock, self.rid, incremental_costs=[{'component': 'c', 'cents': 9, 'basis': 'x'}]))):
            with self.subTest(change=what):
                self.setUp()
                fn()
                self.assertEqual(self.start(), 'SOURCE_CHANGED', what)
                self.assertEqual(L.get(self.w.s, self.rid)['status'], 'approved')

    def test_a_fresh_run_after_a_material_change_ends_the_approval(self):
        IN.record_review(self.w.creview, self.w.clock, self.rid, 'quality', 'not_cleared', 'fails')
        self.w.run(as_of='2026-10-01')
        r = L.get(self.w.s, self.rid)
        self.assertEqual((r['status'], r['approval']['state']), ('generated', 'ended'))
        self.assertEqual(self.start(), 'TRANSITION_NOT_ALLOWED')


class TestPolicyApprovalBoundary(unittest.TestCase):
    """F-66."""
    def setUp(self):
        self.w = RecWorld()

    def test_there_is_no_function_that_approves_from_caller_supplied_fields(self):
        self.assertFalse(hasattr(RP, 'approve'))
        with self.assertRaises(RP.RecPolicyError):
            RP.new_policy('P', 'paula', approvals=[{'approver': 'x', 'role': RP.POLICY_ROLE, 'kind': 'human', 'date': '2026-10-19'}])

    def test_a_policy_cannot_be_stored_with_an_approval(self):
        p = dict(DR.demo_rec_policy(version='F-1', proposer='paula'), approvals=[{'approver': 'someone.unrelated', 'role': RP.POLICY_ROLE, 'kind': 'human', 'date': '2026-10-19'}])
        with self.assertRaises(RP.RecPolicyError):
            RP.store_policy(self.w.polprop, p)
        self.assertIsNone(self.w.s.get(RP.POLICY_KIND, 'F-1'))

    def test_the_proposer_is_the_person_storing_it_and_a_machine_cannot_propose(self):
        with self.assertRaises(RP.RecPolicyError):
            RP.store_policy(self.w.polprop, DR.demo_rec_policy(version='F-2', proposer='someone.else'))
        with self.assertRaises(RP.RecPolicyError):
            RP.store_policy(self.w.ai, DR.demo_rec_policy(version='F-3', proposer='assistant'))

    def test_approval_needs_the_owner_role_a_person_and_not_the_proposer(self):
        RP.store_policy(self.w.polprop, DR.demo_rec_policy(version='F-4', proposer='paula'))
        paula_owner = self.w.w.who('paula-o', 'zero_one', 'paula', (RP.POLICY_ROLE,), ttl=10 ** 8)
        ai_owner = self.w.w.who('ai-o', 'zero_one', 'bot', (RP.POLICY_ROLE,), 'ai', ttl=10 ** 8)
        for who, why in ((self.w.pm, 'no role'), (ai_owner, 'not a person'), (paula_owner, 'the proposer')):
            with self.subTest(why=why):
                with self.assertRaises(RP.RecPolicyError):
                    RP.approve_policy(who, self.w.clock, 'F-4', 'ok')
        with self.assertRaises(RP.RecPolicyError):
            RP.approve_policy(self.w.polown, self.w.clock, 'F-4', ' ')
        RP.approve_policy(self.w.polown, self.w.clock, 'F-4', 'ok')
        with self.assertRaises(RP.RecPolicyError):
            RP.approve_policy(self.w.polown, self.w.clock, 'F-4', 'again')
        with self.assertRaises(RP.RecPolicyError):
            RP.approve_policy(self.w.polown, self.w.clock, 'NO-SUCH', 'ok')
        p = self.w.s.get(RP.POLICY_KIND, 'F-4').payload
        self.assertEqual(p['approvals'], [{'approver': 'quentin', 'role': RP.POLICY_ROLE, 'kind': 'human', 'date': self.w.clock.now()[:10]}])
        self.assertEqual(RP.verified_approvers(self.w.s, p), ['quentin'])

    def test_an_approval_written_into_the_store_directly_does_not_count_at_a_run(self):
        p = DR.demo_rec_policy(version='F-5', proposer='paula')
        RP.store_policy(self.w.polprop, p)
        rec = self.w.s.get(RP.POLICY_KIND, 'F-5')
        forged = dict(rec.payload, approvals=[{'approver': 'quentin', 'role': RP.POLICY_ROLE, 'kind': 'human', 'date': '2026-10-19'}])
        self.w.s.put(RP.POLICY_KIND, 'F-5', forged, expected_revision=rec.revision)       # bypasses approve_policy: quentin never approved it
        self.assertTrue(RP.is_approved(forged))                                         # the shape alone looks approved...
        self.assertEqual(RP.verified_approvers(self.w.s, forged), [])                   # ...but the audit log does not confirm it
        f = self.w.finding()
        rid = self.w.ready(f)
        run = E.run(self.w.s, self.w.reg, self.w.clock, '2026-09-30', 'F-5')
        L.ingest_run(self.w.svc, self.w.clock, self.w.reg, run['run_key'])
        self.assertFalse(run['result']['policy']['approved'])
        self.assertEqual(run['result']['policy']['approvers_confirmed_by_audit'], [])
        e = self.w.entry(run, f)
        self.assertIn('the recommendation policy is not approved by a policy owner', e['constraints']['blocked_by'])
        self.assertEqual(code(lambda: L.submit(self.w.owner2, self.w.clock, rid)), 'NOT_SUBMITTABLE')

    def test_an_audit_event_logged_by_someone_else_does_not_confirm_another_persons_approval(self):
        p = DR.demo_rec_policy(version='F-6', proposer='paula')
        RP.store_policy(self.w.polprop, p)
        self.w.pm.log('rec.policy_approved', RP.POLICY_KIND + '/F-6', 'ok', detail={'version': 'F-6', 'approver': 'quentin'})     # pete pretends to be quentin
        rec = self.w.s.get(RP.POLICY_KIND, 'F-6')
        forged = dict(rec.payload, approvals=[{'approver': 'quentin', 'role': RP.POLICY_ROLE, 'kind': 'human', 'date': '2026-10-19'}])
        self.assertEqual(RP.verified_approvers(self.w.s, forged), [])

    def test_a_run_under_an_unapproved_policy_blocks_every_submission(self):
        w = RecWorld(approved=False)
        f = w.finding()
        rid = w.ready(f)
        e = w.entry(w.run(), f)
        self.assertIn('the recommendation policy is not approved by a policy owner', e['constraints']['blocked_by'])
        self.assertEqual(code(lambda: L.submit(w.owner2, w.clock, rid)), 'NOT_SUBMITTABLE')

    def test_storing_the_same_proposal_again_is_a_no_op_before_and_after_approval(self):
        p = DR.demo_rec_policy(version='F-7', proposer='paula')
        RP.store_policy(self.w.polprop, p)
        RP.store_policy(self.w.polprop, p)
        approved = RP.approve_policy(self.w.polown, self.w.clock, 'F-7', 'ok')
        for again in (p, approved):
            rec = RP.store_policy(self.w.polprop, again)
            self.assertEqual(rec.payload['approvals'], approved['approvals'])
        self.assertEqual(self.w.s.get(RP.POLICY_KIND, 'F-7').revision, 2)

    def test_an_invalid_policy_is_never_stored_even_by_its_proposer(self):
        with self.assertRaises(RP.RecPolicyError):
            RP.store_policy(self.w.polprop, {'version': 'F-8', 'proposer': 'paula', 'approvals': [], 'rank_order': ['score']})
        self.assertIsNone(self.w.s.get(RP.POLICY_KIND, 'F-8'))

    def test_a_concurrent_change_during_approval_is_refused(self):
        from .test_rec_edges import Racing
        RP.store_policy(self.w.polprop, DR.demo_rec_policy(version='F-9', proposer='paula'))
        with self.assertRaises(RP.RecPolicyError) as cm:
            RP.approve_policy(Racing(self.w.polown, RP.POLICY_KIND), self.w.clock, 'F-9', 'ok')
        self.assertIn('changed while it was being approved', str(cm.exception))
        self.assertEqual(self.w.s.get(RP.POLICY_KIND, 'F-9').payload['approvals'], [])

    def test_the_confirmed_approvers_are_part_of_the_run_and_replay(self):
        f = self.w.finding()
        run = self.w.run(ingest=False)
        self.assertEqual(run['params']['policy_verified_approvers'], ['quentin'])
        self.assertTrue(run['result']['policy']['approved'])
        self.assertTrue(repro.replay(self.w.s, self.w.reg, run['run_key']).ok)
        self.assertEqual(self.w.entry(run, f)['route'], 'action')


if __name__ == '__main__':
    unittest.main()
