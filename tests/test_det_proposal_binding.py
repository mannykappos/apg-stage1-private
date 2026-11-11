"""Proposal binding (M6.2 correction, finding F-53, and the audit-trail point F-54).  An action may only be approved while its proposal was written against the finding's CURRENT version and
evidence digest.  If the evidence has changed since the proposal was written (while the finding waited for approval, or after an approval was ended) the approval is refused whether or not the
approver names a version, and the action has to be sent back through a reviewer and proposed again.  A replaced proposal and an ended approval keep their exact text and context in the record, and
the approval entry point for screens and APIs refuses to act without the version and digest the approver was shown.  Written before the correction.  The reproduction is the one in the independent
audit of M6.1 (section 5): propose against version 1, let the evidence move to version 2 while the finding is still action_proposed, approve without naming a version."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_det import inv
from .test_det_findings import breach, first, person
from .test_det_approval_binding import LATER, approved, worsen
from apg.det import findings as FD
from .helpers_det import approve_filled

TEXT1 = 'renegotiate based on original figure'


def proposed(m, fid, text=TEXT1):
    FD.transition(m.reviewer, m.clock, fid, 'under_review')
    FD.transition(m.reviewer, m.clock, fid, 'confirmed', rationale='yes')
    return FD.transition(m.owner, m.clock, fid, 'action_proposed', action_text=text)


def reproposed(m, fid, text='renegotiate on the larger overrun'):
    """The route the lifecycle already allows for a proposal that no longer fits the evidence: a reviewer sends it back, the owner proposes again."""
    FD.transition(m.reviewer, m.clock, fid, 'confirmed', rationale='the evidence changed; back to the owner')
    return FD.transition(m.owner, m.clock, fid, 'action_proposed', action_text=text)


class Base(unittest.TestCase):
    def setUp(self):
        self.m = breach()
        self.fid, _ = first(self.m)

    def refused(self, code, **kw):
        with self.assertRaises(FD.LifecycleError) as c:
            approve_filled(self.m.approver, self.m.clock, self.fid, rationale='ok', **kw)
        self.assertEqual(c.exception.code, code)
        f = FD.get(self.m.svc, self.fid)
        self.assertEqual((f['status'], f['action']['approved_by'], f['action']['approval_state']), ('action_proposed', None, f['action']['approval_state']))
        return f


class TestStaleProposalCannotBeApproved(Base):
    def test_the_audit_reproduction_a_proposal_for_version_1_cannot_be_approved_once_the_finding_is_at_version_2(self):
        f1 = proposed(self.m, self.fid)
        self.assertEqual((f1['version'], f1['action']['proposed_version']), (1, 1))
        worsen(self.m)
        f2 = FD.get(self.m.svc, self.fid)
        self.assertEqual((f2['version'], f2['status'], f2['action']['proposed_version'], f2['action']['proposed_digest']), (2, 'action_proposed', 1, f1['signal']['state_digest']))
        f = self.refused('STALE_PROPOSAL')
        self.assertEqual(f['action']['approval_state'], 'proposed')
        self.assertFalse(FD.approval_current(f))

    def test_naming_the_current_version_does_not_make_a_stale_proposal_approvable(self):
        proposed(self.m, self.fid)
        worsen(self.m)
        self.refused('STALE_PROPOSAL', approving_version=2)

    def test_naming_an_older_version_is_refused_as_a_stale_approval(self):
        proposed(self.m, self.fid)
        worsen(self.m)
        self.refused('STALE_APPROVAL', approving_version=1)

    def test_naming_the_current_evidence_digest_does_not_make_a_stale_proposal_approvable(self):
        proposed(self.m, self.fid)
        worsen(self.m)
        f = FD.get(self.m.svc, self.fid)
        self.refused('STALE_PROPOSAL', approving_version=2, approving_digest=f['signal']['state_digest'])

    def test_naming_an_older_digest_is_refused_as_a_stale_approval(self):
        f1 = proposed(self.m, self.fid)
        worsen(self.m)
        self.refused('STALE_APPROVAL', approving_version=2, approving_digest=f1['signal']['state_digest'])

    def test_the_refusal_is_audited_with_the_reason(self):
        proposed(self.m, self.fid)
        worsen(self.m)
        self.refused('STALE_PROPOSAL')
        refused = [e for e in self.m.w.audit.read(self.m.s.ctx) if e.event_type == 'finding.refused' and 'proposal' in (e.reason or '')]
        self.assertEqual(len(refused), 1)
        self.assertIn('version 1', refused[0].reason)
        self.assertIn('version 2', refused[0].reason)

    def test_an_approval_ended_by_changed_evidence_cannot_be_given_again_on_the_old_proposal(self):
        approved(self.m, self.fid)
        worsen(self.m)
        f = self.refused('STALE_PROPOSAL')
        self.assertEqual((f['action']['approval_state'], len(f['action']['approval_history'])), ('invalidated', 1))

    def test_evidence_that_changes_again_after_a_fresh_proposal_makes_that_proposal_stale_too(self):
        approved(self.m, self.fid)
        worsen(self.m)
        reproposed(self.m, self.fid)
        worsen(self.m, amount='900000', as_of='2026-10-02', sin='SI-3', inv_id='INV-3')
        f = FD.get(self.m.svc, self.fid)
        self.assertEqual((f['version'], f['action']['proposed_version']), (3, 2))
        self.refused('STALE_PROPOSAL')

    def test_the_proposer_is_still_refused_as_self_approver_before_anything_else(self):
        proposed(self.m, self.fid)
        worsen(self.m)
        proposer = person(self.m, 'tok-prop', FD.get(self.m.svc, self.fid)['action']['proposed_by'], FD.APPROVER)
        with self.assertRaises(FD.LifecycleError) as c:
            approve_filled(proposer, self.m.clock, self.fid, rationale='me')
        self.assertEqual(c.exception.code, 'SELF_APPROVAL')

    def test_a_refused_approval_leaves_the_record_exactly_as_it_was(self):
        proposed(self.m, self.fid)
        worsen(self.m)
        before = FD.get(self.m.svc, self.fid)
        self.refused('STALE_PROPOSAL')
        self.assertEqual(FD.get(self.m.svc, self.fid), before)


class TestTheEvidenceDigestAloneCanBeNamed(Base):
    def test_the_current_digest_alone_approves_a_fresh_proposal(self):
        f1 = proposed(self.m, self.fid)
        f = approve_filled(self.m.approver, self.m.clock, self.fid, rationale='ok', approving_digest=f1['signal']['state_digest'])
        self.assertEqual((f['status'], FD.approval_current(f)), ('action_approved', True))

    def test_an_older_digest_alone_is_refused_as_a_stale_approval_and_the_current_digest_alone_cannot_approve_a_stale_proposal(self):
        f1 = proposed(self.m, self.fid)
        worsen(self.m)
        self.refused('STALE_APPROVAL', approving_digest=f1['signal']['state_digest'])
        self.refused('STALE_PROPOSAL', approving_digest=FD.get(self.m.svc, self.fid)['signal']['state_digest'])

    def test_a_proposal_with_no_recorded_version_is_never_approvable_and_the_reason_says_so(self):
        legacy = {'finding_id': 'F', 'status': 'action_proposed', 'version': 2, 'signal': {'state_digest': 'd2'}, 'action': {'text': 'x', 'proposed_by': 'p', 'proposed_at': 't'}}
        ok, why = FD.approvable(legacy)
        self.assertFalse(ok)
        self.assertIn('not recorded', why)
        self.assertIn('version 2', why)


class TestFreshProposalIsApprovable(Base):
    def test_a_proposal_and_approval_with_no_change_in_between_still_work_with_and_without_the_version(self):
        proposed(self.m, self.fid)
        f = approve_filled(self.m.approver, self.m.clock, self.fid, rationale='ok')
        self.assertEqual((f['status'], f['action']['proposed_version'], f['action']['approved_version'], FD.approval_current(f)), ('action_approved', 1, 1, True))

    def test_the_same_with_the_version_and_digest_named(self):
        f1 = proposed(self.m, self.fid)
        f = approve_filled(self.m.approver, self.m.clock, self.fid, rationale='ok', approving_version=1, approving_digest=f1['signal']['state_digest'])
        self.assertEqual((f['status'], FD.approval_current(f)), ('action_approved', True))

    def test_after_a_change_a_reviewer_and_owner_can_propose_again_and_the_new_proposal_is_approvable(self):
        proposed(self.m, self.fid)
        worsen(self.m)
        f = reproposed(self.m, self.fid)
        self.assertEqual((f['status'], f['version'], f['action']['proposed_version'], f['action']['proposed_digest'], f['action']['approval_state']), ('action_proposed', 2, 2, f['signal']['state_digest'], 'proposed'))
        g = approve_filled(self.m.approver, self.m.clock, self.fid, rationale='ok on the larger overrun', approving_version=2)
        a = g['action']
        self.assertEqual((g['status'], a['proposed_version'], a['approved_version'], a['approved_digest'] == a['proposed_digest'], FD.approval_current(g)), ('action_approved', 2, 2, True, True))

    def test_after_an_ended_approval_a_fresh_proposal_and_a_fresh_approval_work_and_work_can_start(self):
        approved(self.m, self.fid)
        worsen(self.m)
        reproposed(self.m, self.fid)
        approve_filled(self.m.approver, self.m.clock, self.fid, rationale='fresh approval')
        f = FD.transition(self.m.owner, self.m.clock, self.fid, 'in_progress')
        self.assertEqual((f['status'], len(f['action']['approval_history'])), ('in_progress', 1))

    def test_the_owner_cannot_propose_again_straight_from_action_proposed_the_table_of_transitions_is_unchanged(self):
        proposed(self.m, self.fid)
        worsen(self.m)
        with self.assertRaises(FD.LifecycleError) as c:
            FD.transition(self.m.owner, self.m.clock, self.fid, 'action_proposed', action_text='again')
        self.assertEqual(c.exception.code, 'TRANSITION_NOT_ALLOWED')
        self.assertEqual(len(FD.TRANSITIONS), 14)
        self.assertNotIn(('action_proposed', 'action_proposed'), FD.TRANSITIONS)

    def test_only_a_reviewer_can_send_a_stale_proposal_back(self):
        proposed(self.m, self.fid)
        worsen(self.m)
        with self.assertRaises(FD.LifecycleError) as c:
            FD.transition(self.m.owner, self.m.clock, self.fid, 'confirmed', rationale='me')
        self.assertEqual(c.exception.code, 'ROLE_REQUIRED')


class TestReplayAndOlderRuns(Base):
    def test_replaying_the_run_that_made_the_proposal_stale_changes_nothing_and_the_proposal_stays_stale(self):
        proposed(self.m, self.fid)
        self.m.clock.advance(3600)
        self.m.invoices(inv('INV-2', sin='SI-2', ex='4000000', cc='CC-01'))
        self.m.reconcile()
        rec = self.m.detect(as_of=LATER)
        self.m.ingest(rec)
        before = FD.get(self.m.svc, self.fid)
        self.assertTrue(self.m.ingest(rec)['replay'])
        self.assertEqual(FD.get(self.m.svc, self.fid), before)
        self.refused('STALE_PROPOSAL')

    def test_an_older_run_arriving_late_neither_refreshes_nor_restores_the_proposal(self):
        older = self.m.detect(as_of='2026-09-29')
        proposed(self.m, self.fid)
        worsen(self.m)
        before = FD.get(self.m.svc, self.fid)
        self.assertEqual(self.m.ingest(older)['ignored_older'], [self.fid])
        self.assertEqual(FD.get(self.m.svc, self.fid), before)
        self.refused('STALE_PROPOSAL')

    def test_a_later_run_with_the_same_evidence_does_not_make_a_stale_proposal_current(self):
        proposed(self.m, self.fid)
        worsen(self.m)
        self.m.clock.advance(3600)
        self.m.ingest(self.m.detect(as_of='2026-10-02'))
        self.refused('STALE_PROPOSAL')

    def test_a_later_run_with_the_same_evidence_leaves_a_current_proposal_current(self):
        proposed(self.m, self.fid)
        self.m.clock.advance(3600)
        out = self.m.ingest(self.m.detect(as_of=LATER))
        self.assertNotIn(self.fid, out['updated'])
        f = FD.get(self.m.svc, self.fid)
        self.assertEqual((f['action']['proposal_state'], FD.proposal_current(f)), ('current', True))


class TestTheRecordSaysWhenAProposalWentStale(Base):
    def test_the_run_summary_names_the_proposals_that_went_stale_and_only_those(self):
        proposed(self.m, self.fid)
        out = worsen(self.m)
        self.assertEqual((out['updated'], out['proposals_stale']), ([self.fid], [self.fid]))
        out2 = worsen(self.m, amount='900000', as_of='2026-10-02', sin='SI-3', inv_id='INV-3')
        self.assertEqual(out2['proposals_stale'], [], 'it is already stale and is not announced twice')

    def test_the_stored_action_is_marked_stale_and_the_history_says_which_version_it_was_written_against(self):
        proposed(self.m, self.fid)
        worsen(self.m)
        f = FD.get(self.m.svc, self.fid)
        self.assertEqual((f['action']['proposal_state'], FD.proposal_current(f)), ('stale', False))
        upd = [e for e in f['history'] if e['event'] == 'updated'][-1]
        self.assertEqual((upd['detail']['proposal_stale'], upd['detail']['proposed_version']), (True, 1))

    def test_a_finding_with_no_action_has_no_stale_proposal_to_report(self):
        out = worsen(self.m)
        self.assertEqual(out['proposals_stale'], [])
        self.assertNotIn('proposal_stale', [e for e in FD.get(self.m.svc, self.fid)['history'] if e['event'] == 'updated'][-1]['detail'])

    def test_a_proposal_made_stale_by_an_ended_approval_is_marked_stale_in_the_same_step(self):
        approved(self.m, self.fid)
        out = worsen(self.m)
        f = FD.get(self.m.svc, self.fid)
        self.assertEqual((out['proposals_stale'], f['action']['proposal_state'], f['action']['approval_state']), ([self.fid], 'stale', 'invalidated'))

    def test_a_resolved_finding_reopened_on_new_evidence_has_its_old_proposal_marked_stale(self):
        approved(self.m, self.fid, to_progress=True)
        FD.transition(self.m.owner, self.m.clock, self.fid, 'resolved', rationale='done', evidence_ref='EV-1')
        out = worsen(self.m)
        f = FD.get(self.m.svc, self.fid)
        self.assertEqual((f['status'], f['version'], out['reopened'], out['proposals_stale']), ('reopened', 2, [self.fid], [self.fid]))
        self.assertEqual((f['action']['proposal_state'], FD.proposal_current(f), f['action']['proposed_version']), ('stale', False, 1))
        ev = f['history'][-1]
        self.assertEqual((ev['event'], ev['detail']['proposal_stale'], ev['detail']['proposed_version']), ('reopened', True, 1))

    def test_a_dismissed_finding_with_no_action_reopened_has_no_proposal_to_mark(self):
        FD.transition(self.m.reviewer, self.m.clock, self.fid, 'dismissed', rationale='noise')
        out = worsen(self.m)
        f = FD.get(self.m.svc, self.fid)
        self.assertEqual((f['status'], f['action'], out['proposals_stale']), ('reopened', None, []))
        self.assertNotIn('proposal_stale', f['history'][-1]['detail'])

    def test_proposal_current_is_strict(self):
        ok = {'version': 2, 'signal': {'state_digest': 'd2'}, 'action': {'proposed_version': 2, 'proposed_digest': 'd2'}}
        self.assertTrue(FD.proposal_current(ok))
        for bad in ({'proposed_version': 1, 'proposed_digest': 'd2'}, {'proposed_version': 2, 'proposed_digest': 'd1'}, {'proposed_version': None, 'proposed_digest': None}, {}):
            self.assertFalse(FD.proposal_current(dict(ok, action=bad)), bad)
        self.assertFalse(FD.proposal_current(dict(ok, action=None)))
        self.assertFalse(FD.proposal_current({'version': 1, 'signal': {'state_digest': 'd1'}, 'action': {'text': 'x', 'proposed_by': 'p', 'proposed_at': 't'}}), 'a proposal made before binding existed is not current')

    def test_approval_current_also_needs_a_current_proposal(self):
        f = {'version': 2, 'signal': {'state_digest': 'd2'}, 'action': {'approved_by': 'abby', 'approval_state': 'current', 'approved_version': 2, 'approved_digest': 'd2',
                                                                         'proposed_version': 1, 'proposed_digest': 'd1', 'text': 'x', 'proposed_by': 'p', 'proposed_at': 't'}}
        f['action']['approved_proposal'] = FD.proposal_ref(f)
        self.assertFalse(FD.approval_current(f))
        f['action'].update(proposed_version=2, proposed_digest='d2')
        f['action']['approved_proposal'] = FD.proposal_ref(f)
        self.assertTrue(FD.approval_current(f))


class TestExactTextAndContextAreKept(Base):
    def test_the_proposal_event_carries_the_exact_action_text_and_what_it_was_written_against(self):
        f = proposed(self.m, self.fid, text='renegotiate exactly: 3 % off, 30 days')
        ev = [e for e in f['history'] if e['event'] == 'status_change' and e['to'] == 'action_proposed'][-1]
        self.assertEqual((ev['detail']['action_text'], ev['detail']['proposed_version'], ev['detail']['proposed_digest']), ('renegotiate exactly: 3 % off, 30 days', 1, f['signal']['state_digest']))

    def test_the_approval_event_carries_the_text_the_proposal_version_and_the_version_approved(self):
        proposed(self.m, self.fid)
        f = approve_filled(self.m.approver, self.m.clock, self.fid, rationale='looks right', approving_version=1)
        ev = [e for e in f['history'] if e['event'] == 'status_change' and e['to'] == 'action_approved'][-1]
        d = ev['detail']
        self.assertEqual((d['action_text'], d['proposed_version'], d['proposed_digest'], d['approved_version'], d['approved_digest'], d['rationale']),
                         (TEXT1, 1, f['signal']['state_digest'], 1, f['signal']['state_digest'], 'looks right'))

    def test_a_refused_stale_approval_adds_nothing_to_the_history(self):
        proposed(self.m, self.fid)
        worsen(self.m)
        n = len(FD.get(self.m.svc, self.fid)['history'])
        self.refused('STALE_PROPOSAL')
        self.assertEqual(len(FD.get(self.m.svc, self.fid)['history']), n)

    def test_an_ended_approval_keeps_the_exact_text_the_proposer_and_the_approval_rationale(self):
        f1 = approved(self.m, self.fid)
        worsen(self.m)
        (h,) = FD.get(self.m.svc, self.fid)['action']['approval_history']
        self.assertEqual((h['action_text'], h['proposed_by'], h['proposed_at'], h['proposed_version'], h['proposed_digest'], h['approval_rationale']),
                         ('renegotiate the supplier', f1['action']['proposed_by'], f1['action']['proposed_at'], 1, f1['signal']['state_digest'], 'approved on the original figure'))
        ev = [e for e in FD.get(self.m.svc, self.fid)['history'] if e['detail'].get('why') == 'approval_invalidated_evidence_changed'][0]
        self.assertEqual(ev['detail']['ended_approval']['action_text'], 'renegotiate the supplier')

    def test_a_replaced_stale_proposal_is_kept_in_full_in_the_proposal_history(self):
        f1 = proposed(self.m, self.fid)
        worsen(self.m)
        f3 = reproposed(self.m, self.fid, text='the new wording')
        (old,) = f3['action']['proposal_history']
        self.assertEqual((old['text'], old['proposed_by'], old['proposed_at'], old['proposed_version'], old['proposed_digest'], old['approval_state'], old['proposal_state']),
                         (TEXT1, f1['action']['proposed_by'], f1['action']['proposed_at'], 1, f1['signal']['state_digest'], 'proposed', 'stale'))
        self.assertEqual((old['replaced_by'], old['replaced_at_version'], old['replaced_at_digest']), ('oscar', 2, f3['signal']['state_digest']))
        self.assertEqual(f3['action']['text'], 'the new wording')

    def test_a_replaced_proposal_that_had_been_approved_keeps_its_approval_in_the_history_too(self):
        approved(self.m, self.fid)
        worsen(self.m)
        f = reproposed(self.m, self.fid)
        (old,) = f['action']['proposal_history']
        self.assertEqual((old['text'], old['approval_state'], old['proposal_state']), ('renegotiate the supplier', 'invalidated', 'stale'))
        self.assertEqual(len(f['action']['approval_history']), 1)
        self.assertEqual(f['action']['approval_history'][0]['action_text'], 'renegotiate the supplier')

    def test_two_replacements_leave_two_entries_in_order_and_the_event_history_only_grows(self):
        proposed(self.m, self.fid, text='first')
        worsen(self.m)
        f2 = reproposed(self.m, self.fid, text='second')
        worsen(self.m, amount='900000', as_of='2026-10-02', sin='SI-3', inv_id='INV-3')
        f3 = reproposed(self.m, self.fid, text='third')
        self.assertEqual([(e['text'], e['proposed_version']) for e in f3['action']['proposal_history']], [('first', 1), ('second', 2)])
        self.assertEqual((f3['action']['text'], f3['action']['proposed_version']), ('third', 3))
        self.assertEqual(f3['history'][:len(f2['history'])], f2['history'], 'the earlier events are unchanged; the history only grows')
        self.assertEqual([e['seq'] for e in f3['history']], list(range(1, len(f3['history']) + 1)))
        texts = [e['detail']['action_text'] for e in f3['history'] if e['event'] == 'status_change' and e['to'] == 'action_proposed']
        self.assertEqual(texts, ['first', 'second', 'third'], 'every proposal ever made is still readable from the event history')

    def test_a_proposal_made_after_nothing_was_replaced_has_an_empty_proposal_history(self):
        f = proposed(self.m, self.fid)
        self.assertEqual((f['action']['proposal_history'], f['action']['approval_history'], f['action']['proposal_state']), ([], [], 'current'))


class TestApprovalEntryPointFailsClosed(Base):
    def token(self):
        f = FD.get(self.m.svc, self.fid)
        return FD.approval_token(f)

    def test_the_token_names_what_the_approver_is_shown(self):
        proposed(self.m, self.fid)
        f = FD.get(self.m.svc, self.fid)
        self.assertEqual(FD.approval_token(f), {'finding_id': self.fid, 'version': 1, 'digest': f['signal']['state_digest'], 'proposal': FD.proposal_ref(f)})

    def test_approve_action_with_the_shown_token_approves_and_binds_exactly_that(self):
        proposed(self.m, self.fid)
        t = self.token()
        f = FD.approve_action(self.m.approver, self.m.clock, self.fid, t['version'], t['digest'], 'ok', approving_proposal=t['proposal'])
        self.assertEqual((f['status'], f['action']['approved_version'], f['action']['approved_digest'], FD.approval_current(f)), ('action_approved', 1, t['digest'], True))

    def test_missing_or_malformed_token_parts_are_refused_before_anything_is_looked_at(self):
        proposed(self.m, self.fid)
        t = self.token()
        for v, d in ((None, t['digest']), (1, None), (None, None), ('1', t['digest']), (True, t['digest']), (0, t['digest']), (1, ''), (1, 5)):
            with self.assertRaises(FD.LifecycleError) as c:
                FD.approve_action(self.m.approver, self.m.clock, self.fid, v, d, 'ok', approving_proposal=t['proposal'])
            self.assertEqual(c.exception.code, 'APPROVAL_TOKEN_REQUIRED', (v, d))
        self.assertEqual(FD.get(self.m.svc, self.fid)['status'], 'action_proposed')

    def test_a_token_for_an_older_version_or_digest_is_refused(self):
        proposed(self.m, self.fid)
        t = self.token()
        worsen(self.m)
        for v, d in ((t['version'], t['digest']), (2, t['digest']), (t['version'], FD.get(self.m.svc, self.fid)['signal']['state_digest'])):
            with self.assertRaises(FD.LifecycleError) as c:
                FD.approve_action(self.m.approver, self.m.clock, self.fid, v, d, 'ok', approving_proposal=t['proposal'])
            self.assertEqual(c.exception.code, 'STALE_APPROVAL', (v, d))

    def test_the_current_token_still_cannot_approve_a_stale_proposal(self):
        proposed(self.m, self.fid)
        worsen(self.m)
        t = self.token()
        with self.assertRaises(FD.LifecycleError) as c:
            FD.approve_action(self.m.approver, self.m.clock, self.fid, t['version'], t['digest'], 'ok', approving_proposal=t['proposal'])
        self.assertEqual(c.exception.code, 'STALE_PROPOSAL')

    def test_the_other_gates_still_apply_through_the_entry_point(self):
        proposed(self.m, self.fid)
        t = self.token()
        with self.assertRaises(FD.LifecycleError) as c:
            FD.approve_action(self.m.owner, self.m.clock, self.fid, t['version'], t['digest'], 'ok', approving_proposal=t['proposal'])
        self.assertEqual(c.exception.code, 'ROLE_REQUIRED')
        proposer = person(self.m, 'tok-prop', FD.get(self.m.svc, self.fid)['action']['proposed_by'], FD.APPROVER)
        with self.assertRaises(FD.LifecycleError) as c:
            FD.approve_action(proposer, self.m.clock, self.fid, t['version'], t['digest'], 'ok', approving_proposal=t['proposal'])
        self.assertEqual(c.exception.code, 'SELF_APPROVAL')
        with self.assertRaises(FD.LifecycleError) as c:
            FD.approve_action(self.m.approver, self.m.clock, self.fid, t['version'], t['digest'], '  ', approving_proposal=t['proposal'])
        self.assertEqual(c.exception.code, 'RATIONALE_REQUIRED')

    def test_approvable_says_why_not(self):
        f = FD.get(self.m.svc, self.fid)
        self.assertEqual(FD.approvable(f), (False, 'no action has been proposed'))
        proposed(self.m, self.fid)
        self.assertEqual(FD.approvable(FD.get(self.m.svc, self.fid)), (True, ''))
        worsen(self.m)
        ok, why = FD.approvable(FD.get(self.m.svc, self.fid))
        self.assertFalse(ok)
        self.assertIn('version 1', why)
        self.assertIn('version 2', why)
        reproposed(self.m, self.fid)
        self.assertEqual(FD.approvable(FD.get(self.m.svc, self.fid)), (True, ''))

    def test_an_approved_finding_is_not_approvable_again(self):
        approved(self.m, self.fid)
        self.assertEqual(FD.approvable(FD.get(self.m.svc, self.fid)), (False, 'the finding is action_approved, not action_proposed'))


if __name__ == '__main__':
    unittest.main()
