"""Approval binding (M5 correction, finding F-52).  An approval of an action is bound to the finding version and the evidence digest that was approved.  When the evidence changes materially the old
approval is invalidated, the finding goes back to `action_proposed` and a person must approve again; the earlier approval stays in the record.  Nothing here adds a status: the ten statuses of
Section 06 section 6 are unchanged.  Written before the correction; the version-1-to-version-2 case is the one the Engine #17 Phase 0 probe reproduced."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_det import approve_filled, det_world, inv
from .test_det_findings import breach, first, person
from apg.det import findings as FD

LATER = '2026-10-01'


def approved(m, fid, to_progress=False):
    FD.transition(m.reviewer, m.clock, fid, 'under_review')
    FD.transition(m.reviewer, m.clock, fid, 'confirmed', rationale='yes')
    FD.transition(m.owner, m.clock, fid, 'action_proposed', action_text='renegotiate the supplier')
    approve_filled(m.approver, m.clock, fid, rationale='approved on the original figure')
    if to_progress:
        FD.transition(m.owner, m.clock, fid, 'in_progress')
    return FD.get(m.svc, fid)


def reproposed(m, fid, text='renegotiate on the larger overrun'):
    """A proposal written against old evidence cannot be approved (M6.2, F-53): a reviewer sends it back and the owner proposes again."""
    FD.transition(m.reviewer, m.clock, fid, 'confirmed', rationale='the evidence changed; back to the owner')
    return FD.transition(m.owner, m.clock, fid, 'action_proposed', action_text=text)


def worsen(m, amount='4000000', as_of=LATER, sin='SI-2', inv_id='INV-2'):
    m.clock.advance(3600)
    m.invoices(inv(inv_id, sin=sin, ex=amount, cc='CC-01'))
    m.reconcile()
    return m.ingest(m.detect(as_of=as_of))


class TestApprovalIsBoundToWhatWasApproved(unittest.TestCase):
    def setUp(self):
        self.m = breach()
        self.fid, _ = first(self.m)

    def test_an_approval_records_the_finding_version_and_the_evidence_digest_it_approved(self):
        f = approved(self.m, self.fid)
        a = f['action']
        self.assertEqual((a['approved_version'], a['approved_digest'], a['approval_state']), (f['version'], f['signal']['state_digest'], 'current'))
        self.assertEqual((a['proposed_version'], a['proposed_digest']), (f['version'], f['signal']['state_digest']))
        self.assertTrue(FD.approval_current(f))

    def test_a_proposal_records_the_version_and_digest_it_was_written_against_and_is_not_yet_an_approval(self):
        m = self.m
        FD.transition(m.reviewer, m.clock, self.fid, 'under_review')
        FD.transition(m.reviewer, m.clock, self.fid, 'confirmed', rationale='yes')
        f = FD.transition(m.owner, m.clock, self.fid, 'action_proposed', action_text='fix')
        a = f['action']
        self.assertEqual((a['proposed_version'], a['proposed_digest'], a['approval_state']), (1, f['signal']['state_digest'], 'proposed'))
        self.assertEqual((a['approved_by'], a['approved_version'], a['approved_digest']), (None, None, None))
        self.assertFalse(FD.approval_current(f))

    def test_the_version_one_to_version_two_case_invalidates_the_approval_and_returns_the_finding_for_fresh_approval(self):
        m = self.m
        f1 = approved(m, self.fid)
        out = worsen(m)
        self.assertEqual(out['updated'], [self.fid])
        f2 = FD.get(m.svc, self.fid)
        self.assertEqual((f1['version'], f2['version']), (1, 2))
        self.assertNotEqual(f1['signal']['state_digest'], f2['signal']['state_digest'])
        self.assertEqual(f2['status'], 'action_proposed', 'an approval of the old evidence no longer stands')
        a = f2['action']
        self.assertEqual((a['approved_by'], a['approved_at'], a['approved_version'], a['approved_digest'], a['approval_state']), (None, None, None, None, 'invalidated'))
        self.assertFalse(FD.approval_current(f2))
        self.assertEqual(a['proposed_by'], f1['action']['proposed_by'])

    def test_the_invalidated_approval_stays_in_the_record_with_who_approved_what_and_why_it_ended(self):
        m = self.m
        f1 = approved(m, self.fid)
        worsen(m)
        f2 = FD.get(m.svc, self.fid)
        (h,) = f2['action']['approval_history']
        self.assertEqual((h['approved_by'], h['approved_at'], h['approved_version'], h['approved_digest']), (f1['action']['approved_by'], f1['action']['approved_at'], 1, f1['signal']['state_digest']))
        self.assertEqual((h['ended_by'], h['ended_because'], h['ended_at_version'], h['ended_at_digest']), ('detection_service', 'evidence_changed', 2, f2['signal']['state_digest']))
        ev = [e for e in f2['history'] if e['event'] == 'status_change' and e['to'] == 'action_proposed' and e['from'] == 'action_approved']
        self.assertEqual(len(ev), 1)
        self.assertEqual((ev[0]['actor_kind'], ev[0]['detail']['why']), ('service', 'approval_invalidated_evidence_changed'))

    def test_an_action_already_in_progress_goes_back_for_fresh_approval_too(self):
        m = self.m
        approved(m, self.fid, to_progress=True)
        worsen(m)
        f = FD.get(m.svc, self.fid)
        self.assertEqual((f['status'], f['action']['approval_state'], len(f['action']['approval_history'])), ('action_proposed', 'invalidated', 1))
        self.assertEqual(f['history'][-1]['from'], 'in_progress')

    def test_unchanged_evidence_in_a_later_run_leaves_the_approval_standing(self):
        m = self.m
        f1 = approved(m, self.fid)
        m.clock.advance(3600)
        out = m.ingest(m.detect(as_of=LATER))
        self.assertNotIn(self.fid, out['updated'])
        f2 = FD.get(m.svc, self.fid)
        self.assertEqual((f2['status'], f2['version'], f2['action'], FD.approval_current(f2)), ('action_approved', 1, f1['action'], True))

    def test_replaying_the_run_that_invalidated_the_approval_changes_nothing(self):
        m = self.m
        approved(m, self.fid)
        m.clock.advance(3600)
        m.invoices(inv('INV-2', sin='SI-2', ex='4000000', cc='CC-01'))
        m.reconcile()
        rec = m.detect(as_of=LATER)
        m.ingest(rec)
        before = FD.get(m.svc, self.fid)
        again = m.ingest(rec)
        after = FD.get(m.svc, self.fid)
        self.assertTrue(again['replay'])
        self.assertEqual((after['history'], after['action'], after['status'], after['version']), (before['history'], before['action'], before['status'], before['version']))
        self.assertEqual(len(after['action']['approval_history']), 1)

    def test_an_older_run_cannot_invalidate_or_restore_an_approval(self):
        m = self.m
        older = m.detect(as_of='2026-09-29')
        approved(m, self.fid)
        worsen(m)
        f2 = FD.get(m.svc, self.fid)
        out = m.ingest(older)
        self.assertEqual(out['ignored_older'], [self.fid])
        f3 = FD.get(m.svc, self.fid)
        self.assertEqual((f3['status'], f3['version'], f3['action']), (f2['status'], f2['version'], f2['action']))


class TestOldApprovalCannotBeReused(unittest.TestCase):
    def setUp(self):
        self.m = breach()
        self.fid, _ = first(self.m)
        approved(self.m, self.fid)
        worsen(self.m)

    def test_work_cannot_start_on_the_strength_of_the_invalidated_approval(self):
        m = self.m
        with self.assertRaises(FD.LifecycleError) as c:
            FD.transition(m.owner, m.clock, self.fid, 'in_progress')
        self.assertEqual(c.exception.code, 'TRANSITION_NOT_ALLOWED')
        self.assertEqual(FD.get(m.svc, self.fid)['status'], 'action_proposed')

    def test_the_proposer_still_cannot_approve_and_a_new_approval_binds_the_new_version_and_digest(self):
        m = self.m
        f2 = FD.get(m.svc, self.fid)
        proposer = person(m, 'tok-prop', f2['action']['proposed_by'], FD.APPROVER)
        with self.assertRaises(FD.LifecycleError) as c:
            approve_filled(proposer, m.clock, self.fid, rationale='me again')
        self.assertEqual(c.exception.code, 'SELF_APPROVAL')
        reproposed(m, self.fid)
        f3 = approve_filled(m.approver, m.clock, self.fid, rationale='approved on the larger overrun')
        a = f3['action']
        self.assertEqual((f3['status'], a['approval_state'], a['approved_version'], a['approved_digest']), ('action_approved', 'current', 2, f3['signal']['state_digest']))
        self.assertEqual(len(a['approval_history']), 1, 'the first approval stays in the record and is not counted again')
        self.assertTrue(FD.approval_current(f3))
        FD.transition(m.owner, m.clock, self.fid, 'in_progress')

    def test_an_approval_that_names_a_version_other_than_the_current_one_is_refused(self):
        m = self.m
        with self.assertRaises(FD.LifecycleError) as c:
            approve_filled(m.approver, m.clock, self.fid, rationale='I read version 1', approving_version=1)
        self.assertEqual(c.exception.code, 'STALE_APPROVAL')
        self.assertEqual(FD.get(m.svc, self.fid)['status'], 'action_proposed')
        reproposed(m, self.fid)
        f = approve_filled(m.approver, m.clock, self.fid, rationale='I read version 2', approving_version=2)
        self.assertEqual(f['action']['approved_version'], 2)

    def test_a_second_change_while_the_finding_awaits_approval_adds_no_second_invalidation(self):
        m = self.m
        before = FD.get(m.svc, self.fid)
        worsen(m, amount='900000', as_of='2026-10-02', sin='SI-3', inv_id='INV-3')
        after = FD.get(m.svc, self.fid)
        self.assertEqual((after['version'], after['status'], len(after['action']['approval_history'])), (before['version'] + 1, 'action_proposed', 1))


class TestApprovalCurrentIsStrict(unittest.TestCase):
    F = {'version': 2, 'signal': {'state_digest': 'd2'}, 'action': {'approved_by': 'abby', 'approval_state': 'current', 'approved_version': 2, 'approved_digest': 'd2',
                                                                                                  'proposed_version': 2, 'proposed_digest': 'd2', 'text': 'x', 'proposed_by': 'p', 'proposed_at': 't'}}
    F['action']['approved_proposal'] = FD.proposal_ref(F)

    def with_(self, **kw):
        f = {k: (dict(v) if isinstance(v, dict) else v) for k, v in self.F.items()}
        f['action'] = dict(f['action'], **kw)
        return f

    def test_only_a_current_approval_of_exactly_this_version_and_digest_counts(self):
        self.assertTrue(FD.approval_current(self.F))
        for kw in ({'approval_state': 'invalidated'}, {'approved_version': 1}, {'approved_digest': 'd1'}, {'approved_by': None}, {'approval_state': 'proposed'}, {'proposed_version': 1}, {'proposed_digest': 'd1'}):
            self.assertFalse(FD.approval_current(self.with_(**kw)), kw)

    def test_an_approval_with_no_binding_at_all_is_not_current(self):
        legacy = {'version': 1, 'signal': {'state_digest': 'd1'}, 'action': {'text': 'x', 'proposed_by': 'p', 'proposed_at': 't', 'approved_by': 'abby', 'approved_at': 't'}}
        self.assertFalse(FD.approval_current(legacy))
        self.assertFalse(FD.approval_current({'version': 1, 'signal': {'state_digest': 'd1'}, 'action': None}))


class TestRunSummaryAndReopening(unittest.TestCase):
    def setUp(self):
        self.m = breach()
        self.fid, _ = first(self.m)

    def test_the_run_summary_names_the_findings_whose_approval_it_ended_and_only_those(self):
        m = self.m
        approved(m, self.fid)
        out = worsen(m)
        self.assertEqual((out['updated'], out['approvals_invalidated']), ([self.fid], [self.fid]))
        out2 = worsen(m, amount='1000', as_of='2026-10-02', sin='SI-3', inv_id='INV-3')
        self.assertEqual(out2['approvals_invalidated'], [])

    def test_a_finding_not_yet_approved_is_updated_without_any_approval_being_ended(self):
        m = self.m
        out = worsen(m)
        self.assertEqual((out['updated'], out['approvals_invalidated']), ([self.fid], []))
        f = FD.get(m.svc, self.fid)
        self.assertEqual((f['status'], f['action']), ('detected', None))

    def test_the_owner_is_told_that_the_approval_no_longer_stands(self):
        m = self.m
        approved(m, self.fid)
        worsen(m)
        f = FD.get(m.svc, self.fid)
        (n,) = [n for n in f['pending_notifications'] if '|approval_invalidated|' in n['dedup_key']]
        self.assertEqual((n['reason'], n['recipient_role']), ('status_transition', f['ownership']['responsible_role']))
        self.assertIn('The earlier approval of version 1 no longer stands because the evidence changed; the action needs a fresh approval.', n['body'])
        self.assertIn('status action_proposed', n['body'])

    def test_resolving_and_then_reopening_on_new_evidence_ends_the_approval_it_rested_on(self):
        m = self.m
        approved(m, self.fid, to_progress=True)
        FD.transition(m.owner, m.clock, self.fid, 'resolved', rationale='done', evidence_ref='EV-1')
        worsen(m)
        f = FD.get(m.svc, self.fid)
        self.assertEqual((f['status'], f['version'], f['action']['approval_state'], len(f['action']['approval_history'])), ('reopened', 2, 'invalidated', 1))
        self.assertEqual((f['action']['approval_history'][0]['ended_because'], f['history'][-1]['detail']['approval_ended']), ('finding_reopened', 1))
        self.assertFalse(FD.approval_current(f))

    def test_a_resolved_finding_reopened_without_an_approval_in_force_records_no_approval_ending(self):
        m = self.m
        FD.transition(m.reviewer, m.clock, self.fid, 'dismissed', rationale='noise')
        worsen(m)
        f = FD.get(m.svc, self.fid)
        self.assertEqual((f['status'], f['action']), ('reopened', None))
        self.assertNotIn('approval_ended', f['history'][-1]['detail'])

    def test_two_endings_leave_two_entries_in_order_in_the_approval_history(self):
        m = self.m
        approved(m, self.fid)
        worsen(m)
        reproposed(m, self.fid)
        approve_filled(m.approver, m.clock, self.fid, rationale='approved on version 2')
        worsen(m, amount='900000', as_of='2026-10-02', sin='SI-3', inv_id='INV-3')
        f = FD.get(m.svc, self.fid)
        h = f['action']['approval_history']
        self.assertEqual((f['version'], f['status'], f['action']['approval_state']), (3, 'action_proposed', 'invalidated'))
        self.assertEqual([(e['approved_version'], e['ended_at_version']) for e in h], [(1, 2), (2, 3)])
        self.assertEqual(h[0]['approved_digest'] != h[1]['approved_digest'], True)
        self.assertEqual(h[1]['ended_at_digest'], f['signal']['state_digest'])

    def test_a_new_proposal_after_an_invalidation_keeps_the_earlier_approval_in_the_record(self):
        m = self.m
        approved(m, self.fid)
        worsen(m)
        FD.transition(m.reviewer, m.clock, self.fid, 'confirmed', rationale='back to the owner to re-propose')
        f = FD.transition(m.owner, m.clock, self.fid, 'action_proposed', action_text='renegotiate, larger scope')
        a = f['action']
        self.assertEqual((a['text'], a['proposed_version'], a['approval_state'], len(a['approval_history'])), ('renegotiate, larger scope', 2, 'proposed', 1))
        f = approve_filled(m.approver, m.clock, self.fid, rationale='ok')
        self.assertEqual((f['action']['approved_version'], len(f['action']['approval_history'])), (2, 1))


if __name__ == '__main__':
    unittest.main()
