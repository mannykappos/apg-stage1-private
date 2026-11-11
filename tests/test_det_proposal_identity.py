"""Approval binds to the exact proposal that was shown (M6.4 correction, finding F-56).  The approval token of M6.3 named the finding version and the evidence digest.  A reviewer can send a finding
back to `confirmed` and the owner can propose a DIFFERENT action against the SAME evidence; version and digest do not change, so a token issued while the first proposal was on screen still matched
and the approval was recorded against text the approver had never seen.  The token must also name the proposal itself (`proposal_ref`), the approval must be refused (PROPOSAL_CHANGED) if the proposal
on record is not the one named, and the ref of the proposal that was approved is kept in the record.  Written before the correction.  The reproduction: show proposal 1, replace it by proposal 2 against
the same evidence, approve with the token that was shown."""
import unittest
from . import _path                                         # noqa: F401
from .test_det_findings import breach, first, person
from .test_det_approval_binding import worsen
from .test_det_proposal_binding import proposed, reproposed
from apg.det import findings as FD
from .helpers_det import approve_filled

TEXT1 = 'renegotiate with the supplier'
TEXT2 = 'terminate the supplier contract'


class Base(unittest.TestCase):
    def setUp(self):
        self.m = breach()
        self.fid, _ = first(self.m)

    def token(self):
        return FD.approval_token(FD.get(self.m.svc, self.fid))

    def approve(self, tok, **over):
        args = dict(approving_version=tok['version'], approving_digest=tok['digest'], rationale='I approve what I was shown', approving_proposal=tok.get('proposal'))
        args.update(over)
        rationale = args.pop('rationale')
        v, d = args.pop('approving_version'), args.pop('approving_digest')
        return FD.approve_action(self.m.approver, self.m.clock, self.fid, v, d, rationale, **args)

    def refused(self, code, tok, **over):
        before = FD.get(self.m.svc, self.fid)
        n = len(self.m.w.audit.read(self.m.s.ctx))
        with self.assertRaises(FD.LifecycleError) as c:
            self.approve(tok, **over)
        self.assertEqual(c.exception.code, code)
        self.assertEqual(FD.get(self.m.svc, self.fid), before, 'a refused approval changes nothing in the record')
        self.assertGreater(len(self.m.w.audit.read(self.m.s.ctx)), n, 'the refusal is audited')
        return before


class TestTheAuditReproduction(Base):
    def test_a_token_shown_for_proposal_1_cannot_approve_proposal_2_written_against_the_same_evidence(self):
        proposed(self.m, self.fid, TEXT1)
        shown = self.token()
        f2 = reproposed(self.m, self.fid, TEXT2)
        self.assertEqual((f2['version'], f2['signal']['state_digest']), (shown['version'], shown['digest']), 'the evidence did not change; only the proposal did')
        f = self.refused('PROPOSAL_CHANGED', shown)
        self.assertEqual((f['status'], f['action']['text'], f['action']['approved_by']), ('action_proposed', TEXT2, None))

    def test_the_same_text_proposed_again_is_still_a_different_proposal(self):
        proposed(self.m, self.fid, TEXT1)
        shown = self.token()
        reproposed(self.m, self.fid, TEXT1)
        self.assertNotEqual(shown['proposal'], self.token()['proposal'])
        self.refused('PROPOSAL_CHANGED', shown)

    def test_a_token_taken_after_the_replacement_approves_the_new_proposal(self):
        proposed(self.m, self.fid, TEXT1)
        reproposed(self.m, self.fid, TEXT2)
        g = self.approve(self.token())
        self.assertEqual((g['status'], g['action']['text'], g['action']['approval_state']), ('action_approved', TEXT2, 'current'))

    def test_the_token_issued_for_the_first_proposal_still_approves_the_first_proposal(self):
        proposed(self.m, self.fid, TEXT1)
        g = self.approve(self.token())
        self.assertEqual((g['status'], g['action']['text']), ('action_approved', TEXT1))


class TestTheTokenNamesTheProposal(Base):
    def test_the_token_has_a_proposal_reference_and_it_is_stable(self):
        proposed(self.m, self.fid, TEXT1)
        t1, t2 = self.token(), self.token()
        self.assertEqual(t1, t2)
        self.assertEqual(set(t1), {'finding_id', 'version', 'digest', 'proposal'})
        self.assertIsInstance(t1['proposal'], str)
        self.assertEqual(len(t1['proposal']), 24)
        self.assertEqual(FD.proposal_ref(FD.get(self.m.svc, self.fid)), t1['proposal'])

    def test_the_reference_changes_with_the_text_the_proposer_the_evidence_and_the_number_of_replacements(self):
        proposed(self.m, self.fid, TEXT1)
        r1 = self.token()['proposal']
        reproposed(self.m, self.fid, TEXT2)
        r2 = self.token()['proposal']
        reproposed(self.m, self.fid, TEXT2)
        r3 = self.token()['proposal']
        self.assertEqual(len({r1, r2, r3}), 3)

    def test_the_reference_is_none_when_there_is_no_usable_proposal(self):
        for bad in (None, {}, [], 'x', 5, {'text': ''}, {'text': 'x'}, {'text': 'x', 'proposed_version': True, 'proposed_digest': 'd', 'proposed_by': 'u', 'proposed_at': 't'},
                    {'text': 'x', 'proposed_version': 1, 'proposed_digest': '', 'proposed_by': 'u', 'proposed_at': 't'}):
            self.assertIsNone(FD.proposal_ref({'action': bad}), repr(bad))
        self.assertIsNone(FD.proposal_ref({}))
        self.assertIsNone(FD.proposal_ref({'action': {'text': 'x', 'proposed_version': 1, 'proposed_digest': 'd', 'proposed_by': 'u'}}), 'a proposal with no recorded time is not usable')

    def test_a_finding_with_no_proposal_has_no_reference_in_its_token(self):
        self.assertIsNone(self.token()['proposal'])


class TestTheEntryPointFailsClosed(Base):
    def test_an_approval_that_does_not_name_the_proposal_is_refused_as_a_missing_token(self):
        proposed(self.m, self.fid, TEXT1)
        tok = self.token()
        for bad in (None, '', '   ', 5, True, 1.0, ['x'], {'p': 1}, b'x'):
            self.refused('APPROVAL_TOKEN_REQUIRED', tok, approving_proposal=bad)

    def test_leaving_the_argument_out_altogether_is_refused_too(self):
        proposed(self.m, self.fid, TEXT1)
        tok = self.token()
        before = FD.get(self.m.svc, self.fid)
        with self.assertRaises(FD.LifecycleError) as c:
            FD.approve_action(self.m.approver, self.m.clock, self.fid, tok['version'], tok['digest'], 'ok')
        self.assertEqual(c.exception.code, 'APPROVAL_TOKEN_REQUIRED')
        self.assertEqual(FD.get(self.m.svc, self.fid), before)

    def test_a_reference_that_is_not_the_one_on_record_is_refused_as_changed(self):
        proposed(self.m, self.fid, TEXT1)
        tok = self.token()
        for wrong in ('0' * 24, 'x', tok['proposal'][:-1], tok['proposal'].upper(), tok['proposal'] + ' '):
            self.refused('PROPOSAL_CHANGED', tok, approving_proposal=wrong)

    def test_the_self_approval_refusal_still_comes_first(self):
        proposed(self.m, self.fid, TEXT1)
        tok = self.token()
        proposer = person(self.m, 'tok-prop', FD.get(self.m.svc, self.fid)['action']['proposed_by'], FD.APPROVER)
        with self.assertRaises(FD.LifecycleError) as c:
            FD.approve_action(proposer, self.m.clock, self.fid, tok['version'], tok['digest'], 'ok', approving_proposal='0' * 24)
        self.assertEqual(c.exception.code, 'SELF_APPROVAL')

    def test_an_older_version_is_still_a_stale_approval_not_a_changed_proposal(self):
        proposed(self.m, self.fid, TEXT1)
        tok = self.token()
        worsen(self.m)
        self.refused('STALE_APPROVAL', tok, approving_proposal='0' * 24)

    def test_the_proposal_on_record_being_stale_is_still_refused_as_stale(self):
        proposed(self.m, self.fid, TEXT1)
        worsen(self.m)
        tok = self.token()
        self.refused('STALE_PROPOSAL', tok)

    def test_a_damaged_proposal_cannot_be_approved_by_any_reference(self):
        proposed(self.m, self.fid, TEXT1)
        tok = self.token()
        rec = FD._load(self.m.svc, self.fid)
        f = FD.canon.deep_copy(rec.payload)
        del f['action']['proposed_at']
        FD._put(self.m.svc, rec, f)
        self.assertIsNone(self.token()['proposal'])
        for ref in (tok['proposal'], 'None', '0' * 24):
            self.refused('PROPOSAL_CHANGED', tok, approving_proposal=ref)


class TestTheRecordKeepsWhatWasApproved(Base):
    def test_the_approval_and_its_event_name_the_approved_proposal(self):
        proposed(self.m, self.fid, TEXT1)
        tok = self.token()
        g = self.approve(tok)
        self.assertEqual(g['action']['approved_proposal'], tok['proposal'])
        ev = g['history'][-1]
        self.assertEqual((ev['to'], ev['detail']['proposal_ref'], ev['detail']['action_text']), ('action_approved', tok['proposal'], TEXT1))
        self.assertTrue(FD.approval_current(g))

    def test_an_ended_approval_keeps_the_reference_of_the_proposal_that_was_approved(self):
        proposed(self.m, self.fid, TEXT1)
        tok = self.token()
        self.approve(tok)
        worsen(self.m)
        f = FD.get(self.m.svc, self.fid)
        ended = f['action']['approval_history'][-1]
        self.assertEqual((ended['approved_proposal'], ended['action_text']), (tok['proposal'], TEXT1))
        self.assertIsNone(f['action']['approved_proposal'])

    def test_an_approval_whose_recorded_proposal_is_not_the_one_on_record_is_not_current(self):
        proposed(self.m, self.fid, TEXT1)
        g = self.approve(self.token())
        self.assertTrue(FD.approval_current(g))
        for bad in (None, '', '0' * 24, 5, True):
            h = FD.canon.deep_copy(g)
            h['action']['approved_proposal'] = bad
            self.assertFalse(FD.approval_current(h), repr(bad))

    def test_the_replaced_proposal_is_kept_in_the_history_with_its_reference(self):
        proposed(self.m, self.fid, TEXT1)
        r1 = self.token()['proposal']
        f = reproposed(self.m, self.fid, TEXT2)
        self.assertEqual(f['action']['proposal_history'][0]['proposal_ref'], r1)
        self.assertEqual(f['action']['proposal_history'][0]['text'], TEXT1)


class TestReplayAndOrdering(Base):
    def test_the_same_approval_sent_twice_is_refused_the_second_time_and_changes_nothing(self):
        proposed(self.m, self.fid, TEXT1)
        tok = self.token()
        g = self.approve(tok)
        n = len(g['history'])
        before = FD.get(self.m.svc, self.fid)
        with self.assertRaises(FD.LifecycleError) as c:
            self.approve(tok)
        self.assertEqual(c.exception.code, 'TRANSITION_NOT_ALLOWED')
        self.assertEqual(FD.get(self.m.svc, self.fid), before)
        self.assertEqual(len(before['history']), n)

    def test_an_old_token_cannot_approve_after_an_approval_was_ended_and_the_proposal_replaced(self):
        proposed(self.m, self.fid, TEXT1)
        old = self.token()
        self.approve(old)
        worsen(self.m)
        reproposed(self.m, self.fid, TEXT2)
        self.refused('STALE_APPROVAL', old)
        self.refused('PROPOSAL_CHANGED', dict(old, version=self.token()['version'], digest=self.token()['digest']))

    def test_after_the_evidence_changes_a_fresh_proposal_and_a_fresh_token_are_needed(self):
        proposed(self.m, self.fid, TEXT1)
        old = self.token()
        self.approve(old)
        worsen(self.m)
        reproposed(self.m, self.fid, TEXT2)
        g = self.approve(self.token())
        self.assertEqual((g['status'], g['action']['text'], g['version']), ('action_approved', TEXT2, 2))


class TestNothingElseMoved(Base):
    def test_the_lifecycle_table_is_unchanged(self):
        self.assertEqual((len(FD.TRANSITIONS), len(FD.STATUSES)), (14, 10))

    def test_the_lower_level_transition_refuses_a_caller_that_names_nothing_and_accepts_the_whole_token(self):
        proposed(self.m, self.fid, TEXT1)
        with self.assertRaises(FD.LifecycleError) as c:
            FD.transition(self.m.approver, self.m.clock, self.fid, 'action_approved', rationale='ok')           # M6.5 (F-57): this was accepted by M6.4
        self.assertEqual(c.exception.code, 'APPROVAL_TOKEN_REQUIRED')
        g = approve_filled(self.m.approver, self.m.clock, self.fid, rationale='ok')
        self.assertEqual(g['status'], 'action_approved')
        self.assertEqual(g['action']['approved_proposal'], FD.proposal_ref(dict(g, action=dict(g['action']))))

    def test_the_lower_level_transition_checks_a_proposal_reference_when_one_is_named(self):
        proposed(self.m, self.fid, TEXT1)
        with self.assertRaises(FD.LifecycleError) as c:
            approve_filled(self.m.approver, self.m.clock, self.fid, rationale='ok', approving_proposal='0' * 24)
        self.assertEqual(c.exception.code, 'PROPOSAL_CHANGED')
        with self.assertRaises(FD.LifecycleError) as c:
            approve_filled(self.m.approver, self.m.clock, self.fid, rationale='ok', approving_proposal=True)
        self.assertEqual(c.exception.code, 'APPROVAL_TOKEN_REQUIRED')


class TestAStoredProposalThatIsEditedIsNotTheOneThatWasShown(Base):
    """A proposal edited in the store after it was shown (a hand edit, a bad migration) is not the proposal named in the token, whichever field changed."""

    def tamper(self, edit):
        rec = FD._load(self.m.svc, self.fid)
        f = FD.canon.deep_copy(rec.payload)
        edit(f['action'])
        FD._put(self.m.svc, rec, f)

    def test_changing_the_text_the_proposer_or_the_time_changes_the_reference_and_the_old_token_is_refused(self):
        for field, value in (('text', 'something else entirely'), ('proposed_by', 'someone-else'), ('proposed_at', '2001-01-01T00:00:00Z')):
            with self.subTest(field=field):
                self.setUp()
                proposed(self.m, self.fid, TEXT1)
                tok = self.token()
                self.tamper(lambda a: a.__setitem__(field, value))
                self.assertNotEqual(self.token()['proposal'], tok['proposal'])
                f = self.refused('PROPOSAL_CHANGED', tok)
                self.assertEqual((f['status'], f['action'][field]), ('action_proposed', value))

    def test_changing_the_number_of_replaced_proposals_changes_the_reference(self):
        proposed(self.m, self.fid, TEXT1)
        tok = self.token()
        self.tamper(lambda a: a.__setitem__('proposal_history', list(a.get('proposal_history') or []) + [{'text': 'x'}]))
        self.assertNotEqual(self.token()['proposal'], tok['proposal'])
        self.refused('PROPOSAL_CHANGED', tok)

    def test_an_edit_after_the_approval_ends_the_approval_in_force(self):
        proposed(self.m, self.fid, TEXT1)
        g = self.approve(self.token())
        self.assertTrue(FD.approval_current(g))
        for field, value in (('text', 'something else entirely'), ('proposed_by', 'someone-else'), ('proposed_at', '2001-01-01T00:00:00Z')):
            with self.subTest(field=field):
                h = dict(g, action=dict(g['action'], **{field: value}))
                self.assertFalse(FD.approval_current(h), 'the approval was of a different proposal')

    def test_the_lower_level_transition_refuses_a_proposal_that_has_no_usable_reference_whatever_reference_is_named(self):
        proposed(self.m, self.fid, TEXT1)
        self.tamper(lambda a: a.pop('proposed_at'))
        before = FD.get(self.m.svc, self.fid)
        with self.assertRaises(FD.LifecycleError) as c:
            approve_filled(self.m.approver, self.m.clock, self.fid, rationale='ok', approving_proposal='r' * 24)
        self.assertEqual(c.exception.code, 'PROPOSAL_CHANGED')
        self.assertEqual(FD.get(self.m.svc, self.fid), before)


if __name__ == '__main__':
    unittest.main()
