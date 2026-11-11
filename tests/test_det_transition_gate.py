"""The approval gate lives in the lowest-level call (M6.5 correction, finding F-57, found by the independent audit of APG-M6.4).  M6.4 made `approve_action` require the finding version, the evidence
digest and the proposal reference the approver was shown, but `transition(..., 'action_approved', ...)` still accepted an approval that named none of them, or only some of them: the protection
could be bypassed by calling the lower-level function.  The gate is now in `transition` itself, so no public path can record an approval unless all three are named, well formed and current; the start
of the action (`in_progress`) also re-checks that the approval is still in force.  Written before the correction.  The reproduction is tools/probe_transition_bypass.py."""
import itertools
import unittest
from . import _path                                         # noqa: F401
from .test_det_findings import breach, first, person
from .test_det_approval_binding import worsen
from .test_det_proposal_binding import proposed, reproposed
from apg.det import findings as FD

TEXT1 = 'renegotiate with the supplier'
TEXT2 = 'terminate the supplier contract'


class Base(unittest.TestCase):
    def setUp(self):
        self.m = breach()
        self.fid, _ = first(self.m)

    def rec(self):
        return FD.get(self.m.svc, self.fid)

    def token(self):
        return FD.approval_token(self.rec())

    def tr(self, who=None, to='action_approved', **kw):
        return FD.transition(who or self.m.approver, self.m.clock, self.fid, to, rationale=kw.pop('rationale', 'ok'), **kw)

    def full(self, tok=None, **over):
        tok = tok or self.token()
        kw = dict(approving_version=tok['version'], approving_digest=tok['digest'], approving_proposal=tok['proposal'])
        kw.update(over)
        return kw

    def refused(self, code, who=None, to='action_approved', **kw):
        """The call is refused with `code`, the record is exactly as it was, and the refusal is in the audit log."""
        before = self.rec()
        n = len(self.m.w.audit.read(self.m.s.ctx))
        with self.assertRaises(FD.LifecycleError) as c:
            self.tr(who, to, **kw)
        self.assertEqual(c.exception.code, code)
        self.assertEqual(self.rec(), before, 'a refused call changes nothing in the record')
        self.assertGreater(len(self.m.w.audit.read(self.m.s.ctx)), n, 'the refusal is audited')
        return before


class TestEveryIncompleteApprovalIsRefusedAtTheLowerLevelCall(Base):
    def setUp(self):
        super().setUp()
        proposed(self.m, self.fid, TEXT1)

    def test_the_audit_reproduction_an_approval_that_names_nothing_is_refused(self):
        f = self.refused('APPROVAL_TOKEN_REQUIRED')
        self.assertEqual((f['status'], f['action']['approved_by'], f['action']['approval_state'], FD.approval_current(f)), ('action_proposed', None, 'proposed', False))

    def test_every_proper_subset_of_the_three_items_is_refused(self):
        names = ('approving_version', 'approving_digest', 'approving_proposal')
        for r in range(0, 3):
            for chosen in itertools.combinations(names, r):
                with self.subTest(named=chosen):
                    tok = self.token()
                    full = self.full(tok)
                    f = self.refused('APPROVAL_TOKEN_REQUIRED', **{k: full[k] for k in chosen})
                    self.assertEqual(f['status'], 'action_proposed')

    def test_naming_the_three_items_each_as_none_is_the_same_as_leaving_them_out(self):
        for missing in ('approving_version', 'approving_digest', 'approving_proposal'):
            with self.subTest(missing=missing):
                self.refused('APPROVAL_TOKEN_REQUIRED', **self.full(**{missing: None}))

    def test_the_complete_token_is_accepted_and_the_record_matches_the_entry_point(self):
        g = self.tr(**self.full())
        self.assertEqual((g['status'], g['action']['approval_state'], g['action']['approved_by'], g['action']['approved_proposal'], FD.approval_current(g)),
                        ('action_approved', 'current', 'abby', FD.proposal_ref(g), True))
        m2 = breach()
        fid2, _ = first(m2)
        proposed(m2, fid2, TEXT1)
        tok = FD.approval_token(FD.get(m2.svc, fid2))
        h = FD.approve_action(m2.approver, m2.clock, fid2, tok['version'], tok['digest'], 'ok', approving_proposal=tok['proposal'])
        self.assertEqual({k: v for k, v in g['action'].items() if k != 'approved_at'}, {k: v for k, v in h['action'].items() if k != 'approved_at'})
        self.assertEqual((g['status'], g['version']), (h['status'], h['version']))


class TestMalformedItemsFailClosedAtTheLowerLevelCall(Base):
    BAD_VERSIONS = (None, True, False, 0, -1, 1.0, '1', '', [], {}, 10 ** 30 + 0.5)
    BAD_TEXTS = (None, True, 1, 1.5, '', '   ', [], {}, b'x')

    def setUp(self):
        super().setUp()
        proposed(self.m, self.fid, TEXT1)

    def test_a_version_that_is_not_a_whole_number_of_at_least_one_is_refused(self):
        for bad in self.BAD_VERSIONS:
            with self.subTest(version=bad):
                self.refused('APPROVAL_TOKEN_REQUIRED', **self.full(approving_version=bad))

    def test_a_digest_that_is_not_a_non_empty_text_is_refused(self):
        for bad in self.BAD_TEXTS:
            with self.subTest(digest=bad):
                self.refused('APPROVAL_TOKEN_REQUIRED', **self.full(approving_digest=bad))

    def test_a_proposal_reference_that_is_not_a_non_empty_text_is_refused(self):
        for bad in self.BAD_TEXTS:
            with self.subTest(proposal=bad):
                self.refused('APPROVAL_TOKEN_REQUIRED', **self.full(approving_proposal=bad))

    def test_the_token_dict_itself_or_a_whole_record_is_not_a_proposal_reference(self):
        tok = self.token()
        self.refused('APPROVAL_TOKEN_REQUIRED', **self.full(tok, approving_proposal=tok))
        self.refused('APPROVAL_TOKEN_REQUIRED', **self.full(tok, approving_version=tok))


class TestWellFormedButWrongItemsAreRefusedAtTheLowerLevelCall(Base):
    def setUp(self):
        super().setUp()
        proposed(self.m, self.fid, TEXT1)

    def test_another_version_is_a_stale_approval(self):
        self.refused('STALE_APPROVAL', **self.full(approving_version=2))
        self.refused('STALE_APPROVAL', **self.full(approving_version=10 ** 6))

    def test_another_digest_is_a_stale_approval(self):
        self.refused('STALE_APPROVAL', **self.full(approving_digest='0' * 24))

    def test_another_proposal_reference_is_refused_as_a_changed_proposal(self):
        self.refused('PROPOSAL_CHANGED', **self.full(approving_proposal='0' * 24))

    def test_the_reference_of_the_finding_or_the_digest_is_not_the_reference_of_the_proposal(self):
        tok = self.token()
        self.refused('PROPOSAL_CHANGED', **self.full(tok, approving_proposal=tok['digest']))
        self.refused('PROPOSAL_CHANGED', **self.full(tok, approving_proposal=tok['finding_id']))


class TestAProposalThatWasReplacedAfterItWasShown(Base):
    def test_the_token_of_proposal_1_cannot_approve_proposal_2_written_against_the_same_evidence(self):
        proposed(self.m, self.fid, TEXT1)
        shown = self.token()
        f2 = reproposed(self.m, self.fid, TEXT2)
        self.assertEqual((f2['version'], f2['signal']['state_digest']), (1, shown['digest']))
        self.refused('PROPOSAL_CHANGED', **self.full(shown))
        g = self.tr(**self.full())
        self.assertEqual((g['status'], g['action']['text']), ('action_approved', TEXT2))

    def test_a_proposal_written_again_with_the_same_words_is_still_a_different_proposal(self):
        proposed(self.m, self.fid, TEXT1)
        shown = self.token()
        reproposed(self.m, self.fid, TEXT1)
        self.assertNotEqual(self.token()['proposal'], shown['proposal'])
        self.refused('PROPOSAL_CHANGED', **self.full(shown))

    def test_the_proposal_edited_in_the_store_after_it_was_shown_is_refused(self):
        proposed(self.m, self.fid, TEXT1)
        shown = self.token()
        rec = FD._load(self.m.svc, self.fid)
        f = FD.canon.deep_copy(rec.payload)
        f['action']['text'] = 'something else entirely'
        FD._put(self.m.svc, rec, f)
        self.refused('PROPOSAL_CHANGED', **self.full(shown))

    def test_a_proposal_with_no_usable_reference_is_refused_whatever_is_named(self):
        proposed(self.m, self.fid, TEXT1)
        shown = self.token()
        rec = FD._load(self.m.svc, self.fid)
        f = FD.canon.deep_copy(rec.payload)
        f['action'].pop('proposed_at')
        FD._put(self.m.svc, rec, f)
        self.refused('PROPOSAL_CHANGED', **self.full(shown))
        with self.assertRaises(FD.LifecycleError) as c:
            self.tr(**self.full(shown))
        self.assertIn('cannot be identified', str(c.exception), 'the approver is told that reading the proposal again will not help: it has to be proposed again')
        self.assertNotIn('read it again', str(c.exception))
        self.refused('APPROVAL_TOKEN_REQUIRED')


class TestStaleVersionsAndDigestsAtTheLowerLevelCall(Base):
    def test_a_token_from_before_the_evidence_moved_is_a_stale_approval_not_a_stale_proposal(self):
        proposed(self.m, self.fid, TEXT1)
        shown = self.token()
        worsen(self.m)
        self.assertEqual(self.rec()['version'], 2)
        self.refused('STALE_APPROVAL', **self.full(shown))

    def test_the_fresh_token_of_a_proposal_written_against_older_evidence_is_a_stale_proposal(self):
        proposed(self.m, self.fid, TEXT1)
        worsen(self.m)
        self.refused('STALE_PROPOSAL', **self.full())

    def test_after_the_owner_proposes_again_against_the_new_evidence_the_new_token_approves(self):
        proposed(self.m, self.fid, TEXT1)
        old = self.token()
        worsen(self.m)
        reproposed(self.m, self.fid, TEXT2)
        self.refused('STALE_APPROVAL', **self.full(old))
        g = self.tr(**self.full())
        self.assertEqual((g['status'], g['action']['approved_version'], FD.approval_current(g)), ('action_approved', 2, True))


class TestReplayAndIdempotency(Base):
    def test_a_second_submission_of_the_same_approval_is_refused_and_changes_nothing(self):
        proposed(self.m, self.fid, TEXT1)
        tok = self.token()
        g = self.tr(**self.full(tok))
        n = len(g['history'])
        with self.assertRaises(FD.LifecycleError) as c:
            self.tr(**self.full(tok))
        self.assertEqual(c.exception.code, 'TRANSITION_NOT_ALLOWED')
        after = self.rec()
        self.assertEqual((len(after['history']), after['action']['approved_by'], after['action']['approved_at']), (n, 'abby', g['action']['approved_at']))

    def test_a_second_submission_through_the_entry_point_is_refused_the_same_way(self):
        proposed(self.m, self.fid, TEXT1)
        tok = self.token()
        FD.approve_action(self.m.approver, self.m.clock, self.fid, tok['version'], tok['digest'], 'ok', approving_proposal=tok['proposal'])
        before = self.rec()
        with self.assertRaises(FD.LifecycleError) as c:
            FD.approve_action(self.m.approver, self.m.clock, self.fid, tok['version'], tok['digest'], 'ok', approving_proposal=tok['proposal'])
        self.assertEqual(c.exception.code, 'TRANSITION_NOT_ALLOWED')
        self.assertEqual(self.rec(), before)

    def test_an_approval_ended_by_new_evidence_cannot_be_replayed_with_its_old_token(self):
        proposed(self.m, self.fid, TEXT1)
        tok = self.token()
        self.tr(**self.full(tok))
        worsen(self.m)
        f = self.rec()
        self.assertEqual((f['status'], f['action']['approval_state']), ('action_proposed', 'invalidated'))
        self.refused('STALE_APPROVAL', **self.full(tok))


class TestWhoMayApproveIsStillChecked(Base):
    def setUp(self):
        super().setUp()
        proposed(self.m, self.fid, TEXT1)

    def test_the_proposer_is_refused_as_self_approver_before_the_token_is_looked_at(self):
        proposer = person(self.m, 'both', 'oscar2', FD.OWNER, FD.APPROVER)
        FD.transition(self.m.reviewer, self.m.clock, self.fid, 'confirmed', rationale='back')
        FD.transition(proposer, self.m.clock, self.fid, 'action_proposed', action_text=TEXT2)
        self.refused('SELF_APPROVAL', who=proposer)
        self.refused('SELF_APPROVAL', who=proposer, **self.full())

    def test_a_person_without_the_approver_role_is_refused_with_a_complete_token(self):
        self.refused('ROLE_REQUIRED', who=self.m.reviewer, **self.full())
        self.refused('ROLE_REQUIRED', who=self.m.owner, **self.full())

    def test_a_service_is_refused_with_a_complete_token(self):
        self.refused('HUMAN_REQUIRED', who=self.m.svc, **self.full())

    def test_a_person_of_another_tenant_cannot_see_the_finding(self):
        other = self.m.w.who('apr2', 'zero_two', 'mallory', (FD.APPROVER,))
        with self.assertRaises(FD.LifecycleError) as c:
            FD.transition(other, self.m.clock, self.fid, 'action_approved', rationale='ok', **self.full())
        self.assertEqual(c.exception.code, 'FINDING_UNKNOWN')
        self.assertEqual(self.rec()['status'], 'action_proposed')


class TestTheEntryPointStillRefusesFirst(Base):
    """`approve_action` is the entry point for screens and APIs. It refuses an incomplete token before it looks at anything (the lower-level call checks the same things later and says the same thing)."""

    def test_an_incomplete_token_is_refused_before_the_finding_is_looked_up(self):
        n = len(self.m.w.audit.read(self.m.s.ctx))
        with self.assertRaises(FD.LifecycleError) as c:
            FD.approve_action(self.m.approver, self.m.clock, 'FND-does-not-exist', None, None, 'ok')
        self.assertEqual(c.exception.code, 'APPROVAL_TOKEN_REQUIRED', 'not FINDING_UNKNOWN: nothing was looked at')
        self.assertGreater(len(self.m.w.audit.read(self.m.s.ctx)), n, 'the refusal is audited')

    def test_an_incomplete_token_from_the_proposer_is_refused_for_the_token_first(self):
        proposed(self.m, self.fid, TEXT1)
        proposer = person(self.m, 'prop', 'oscar', FD.OWNER, FD.APPROVER)
        before = self.rec()
        with self.assertRaises(FD.LifecycleError) as c:
            FD.approve_action(proposer, self.m.clock, self.fid, 1, self.token()['digest'], 'me', approving_proposal=None)
        self.assertEqual(c.exception.code, 'APPROVAL_TOKEN_REQUIRED')
        self.assertEqual(self.rec(), before)

    def test_a_complete_token_through_the_entry_point_gives_the_same_record_as_through_the_lower_level_call(self):
        proposed(self.m, self.fid, TEXT1)
        tok = self.token()
        g = FD.approve_action(self.m.approver, self.m.clock, self.fid, tok['version'], tok['digest'], 'ok', approving_proposal=tok['proposal'])
        self.assertEqual((g['status'], g['action']['approved_proposal'], FD.approval_current(g)), ('action_approved', tok['proposal'], True))


class TestNothingElseMoved(Base):
    def test_the_lifecycle_table_is_unchanged(self):
        self.assertEqual((len(FD.TRANSITIONS), len(FD.STATUSES)), (14, 10))

    def test_the_transitions_that_are_not_approvals_need_no_token(self):
        f = self.tr(self.m.reviewer, 'under_review')
        self.assertEqual(f['status'], 'under_review')
        self.assertEqual(self.tr(self.m.reviewer, 'confirmed')['status'], 'confirmed')
        self.assertEqual(self.tr(self.m.owner, 'action_proposed', action_text=TEXT1)['status'], 'action_proposed')
        self.assertEqual(self.tr(self.m.reviewer, 'confirmed')['status'], 'confirmed')
        self.assertEqual(self.tr(self.m.owner, 'action_proposed', action_text=TEXT2)['status'], 'action_proposed')
        g = self.tr(**self.full())
        self.assertEqual(g['status'], 'action_approved')
        self.assertEqual(self.tr(self.m.owner, 'in_progress')['status'], 'in_progress')
        self.assertEqual(self.tr(self.m.owner, 'resolved', evidence_ref='EV-1')['status'], 'resolved')
        self.assertEqual(self.tr(self.m.reviewer, 'reopened')['status'], 'reopened')

    def test_a_dismissal_and_a_supersession_need_no_token(self):
        self.tr(self.m.reviewer, 'under_review')
        self.assertEqual(self.tr(self.m.reviewer, 'dismissed')['status'], 'dismissed')

    def test_naming_a_token_on_a_transition_that_is_not_an_approval_does_not_approve_anything(self):
        self.tr(self.m.reviewer, 'under_review')
        self.tr(self.m.reviewer, 'confirmed')
        tok = self.token()
        f = self.tr(self.m.owner, 'action_proposed', action_text=TEXT1, **self.full(tok, approving_proposal='x'))
        self.assertEqual((f['status'], f['action']['approved_by'], f['action']['approval_state']), ('action_proposed', None, 'proposed'))


class TestStartingTheActionRechecksThatTheApprovalIsStillInForce(Base):
    """CF-22 (evidence between approval and execution): a finding whose stored approval is no longer the approval of the proposal on record cannot be moved to in_progress."""

    def setUp(self):
        super().setUp()
        proposed(self.m, self.fid, TEXT1)
        self.tr(**self.full())

    def tamper(self, edit):
        rec = FD._load(self.m.svc, self.fid)
        f = FD.canon.deep_copy(rec.payload)
        edit(f)
        FD._put(self.m.svc, rec, f)

    def test_an_approval_in_force_starts_the_action(self):
        f = self.tr(self.m.owner, 'in_progress')
        self.assertEqual((f['status'], FD.approval_current(f)), ('in_progress', True))

    def test_an_approval_that_is_no_longer_in_force_does_not(self):
        edits = {'approval ended': lambda f: f['action'].__setitem__('approval_state', 'invalidated'),
                 'no approver recorded': lambda f: f['action'].__setitem__('approved_by', None),
                 'approved another digest': lambda f: f['action'].__setitem__('approved_digest', '0' * 24),
                 'approved another version': lambda f: f['action'].__setitem__('approved_version', 7),
                 'approved another proposal': lambda f: f['action'].__setitem__('approved_proposal', '0' * 24),
                 'no proposal reference kept': lambda f: f['action'].__setitem__('approved_proposal', None),
                 'proposal text edited after approval': lambda f: f['action'].__setitem__('text', 'something else entirely'),
                 'proposal marked stale': lambda f: f['action'].__setitem__('proposal_state', 'stale'),
                 'evidence moved without the service': lambda f: f['signal'].__setitem__('state_digest', 'f' * 24)}
        for name, edit in edits.items():
            with self.subTest(case=name):
                self.setUp()
                self.tamper(edit)
                self.refused('APPROVAL_NOT_CURRENT', who=self.m.owner, to='in_progress')
                self.assertEqual(self.rec()['status'], 'action_approved')

    def test_the_role_is_still_checked_before_the_approval(self):
        self.tamper(lambda f: f['action'].__setitem__('approval_state', 'invalidated'))
        self.refused('ROLE_REQUIRED', who=self.m.approver, to='in_progress')


if __name__ == '__main__':
    unittest.main()
