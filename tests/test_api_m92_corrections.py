"""The APG-M9.2 corrections of the approval request boundary (findings F-58 to F-61).  The independent audit of APG-M9.1 reproduced three defects (the screen gave the approval token to a caller who cannot approve; a conflict
on opening the request record answered CONCURRENT_CHANGE without an audit event; the identifier check accepted a trailing newline) and raised the audit-consistency risk (an approval recorded, then the success audit entry
fails).  The builder's own review for the same classes found a fourth gap (check_for_execution refused a malformed or expired call without an audit event) and the same end-anchor flaw in the session-expiry check.
These tests were written BEFORE the corrections and run against the delivered M9.1 code (Blueprint Section 15.4, 15.8, 15.11)."""
import types
import unittest
from . import _path                                         # noqa: F401
from .test_api_approval_boundary import Base, Grants, Flaky, once, AB, FD


class FlakyLog(Flaky):
    """A scoped store whose audit log fails (once) for chosen event names."""
    def __init__(self, inner, events, times=1):
        super().__init__(inner, None)
        self.events, self.times = set(events), times

    def log(self, event, *a, **k):
        if event in self.events and self.times > 0:
            self.times -= 1
            raise RuntimeError('audit store unavailable')
        return self._i.log(event, *a, **k)


class TestTheTokenIsOnlyForACallerWhoCanApprove(Base):
    """F-58.  `present` computed `can_approve` but handed the token whenever the finding itself could be approved."""

    def shown(self, who, scopes):
        return AB.present(who, scopes, self.m.clock, self.fid)

    def assertTokenFollowsCanApprove(self, r):
        self.assertEqual(r['status'], 'shown')
        self.assertEqual(r['token'] is not None, r['can_approve'], r)

    def test_a_viewer_with_the_approver_role_but_no_project_approval_gets_no_token(self):
        view_only = Grants({('zero_one', 'abby', 'PRJ-001'): ('view',)})
        r = self.shown(self.m.approver, view_only)
        self.assertEqual((r['can_approve'], r['token']), (False, None))
        self.assertEqual(r['proposal']['text'], 'renegotiate with the supplier', 'the viewer still sees the proposal')

    def test_a_viewer_without_the_approver_role_gets_no_token(self):
        who = self.human('viewer-1', 'vera', 'reviewer')
        r = self.shown(who, Grants({('zero_one', 'vera', 'PRJ-001'): ('view', 'approve')}))
        self.assertEqual((r['can_approve'], r['token']), (False, None))

    def test_a_person_with_no_role_at_all_gets_no_token(self):
        who = self.human('viewer-2', 'vera')
        r = self.shown(who, Grants({('zero_one', 'vera', 'PRJ-001'): ('view', 'approve')}))
        self.assertEqual((r['can_approve'], r['token']), (False, None))

    def test_the_proposer_gets_no_token_for_their_own_proposal(self):
        r = self.shown(self.m.owner, Grants({('zero_one', 'oscar', 'PRJ-001'): ('view', 'approve')}))
        self.assertEqual((r['can_approve'], r['token']), (False, None))

    def test_a_proposer_who_also_holds_the_approver_role_gets_no_token(self):
        who = self.human('osc-2', 'oscar', FD.APPROVER)                       # the person who wrote the proposal, with the approver role and the project right
        r = self.shown(who, Grants({('zero_one', 'oscar', 'PRJ-001'): ('view', 'approve')}))
        self.assertEqual((r['can_approve'], r['token']), (False, None))

    def test_a_port_that_refuses_approve_gives_no_token_and_a_port_that_allows_it_gives_one(self):
        no = self.shown(self.m.approver, Grants({}))
        self.assertEqual(no['status'], 'refused', 'no view right at all: the same answer as an unknown finding')
        r = self.shown(self.m.approver, self.scopes)
        self.assertEqual((r['can_approve'], r['token']), (True, self.token()))

    def test_the_token_is_never_given_unless_can_approve_is_true_in_any_combination(self):
        who_roles = {'approver': self.m.approver, 'proposer': self.m.owner, 'reviewer': self.human('rv', 'rita', 'reviewer'), 'none': self.human('nn', 'nina')}
        users = {'approver': 'abby', 'proposer': 'oscar', 'reviewer': 'rita', 'none': 'nina'}
        for name, who in who_roles.items():
            for acts in ((), ('view',), ('approve',), ('view', 'approve')):
                r = self.shown(who, Grants({('zero_one', users[name], 'PRJ-001'): acts}))
                if r['status'] == 'shown':
                    self.assertTokenFollowsCanApprove(r)
                else:
                    self.assertNotIn('token', r)

    def test_a_finding_that_cannot_be_approved_now_still_gives_no_token_to_an_approver(self):
        self.ask(self.req())
        r = self.shown(self.m.approver, self.scopes)
        self.assertEqual((r['can_approve'], r['token']), (False, None))


class TestAConflictOnOpeningTheRequestIsAudited(Base):
    """F-59.  The `CONCURRENT_CHANGE` answer given when another copy of the request opened the record first wrote no audit event."""

    def conflicting(self):
        return Flaky(self.m.approver, once(FD.ConflictError('another copy opened it'), lambda kind, p: kind == AB.REQUEST_KIND and p.get('state') == 'pending'))

    def test_the_outcome_is_answered_as_before_and_one_refusal_is_audited(self):
        n = len(self.boundary_events())
        res = self.ask(self.req(rid='R-1'), who=self.conflicting())
        self.assertEqual((res['status'], res['code'], res.get('retry')), ('refused', 'CONCURRENT_CHANGE', True))
        ev = self.boundary_events()[n:]
        self.assertEqual([(e.event_type, e.outcome, e.resource) for e in ev], [('approval_request.refused', 'refused', 'approval_request/R-1')])
        self.assertEqual(self.record()['status'], 'action_proposed')
        self.assertEqual(len(self.stored_requests()), 0)

    def test_the_audit_entry_names_the_code_and_not_the_rationale(self):
        self.ask(self.req(rid='R-1'), who=self.conflicting())
        ev = [e for e in self.boundary_events() if e.event_type == 'approval_request.refused']
        self.assertEqual(len(ev), 1)
        self.assertIn('CONCURRENT_CHANGE', repr(ev[0].__dict__) + repr(getattr(ev[0], 'detail', '')))
        self.assertNotIn('I approve', repr(ev[0].__dict__))

    def test_a_failure_to_write_that_entry_does_not_change_the_answer(self):
        who = FlakyLog(self.conflicting(), ['approval_request.refused'])
        res = self.ask(self.req(rid='R-1'), who=who)
        self.assertEqual((res['status'], res['code'], res.get('retry')), ('refused', 'CONCURRENT_CHANGE', True))

    def test_the_same_request_can_be_sent_again_and_approves_once(self):
        req = self.req(rid='R-1')
        self.ask(req, who=self.conflicting())
        again = self.ask(dict(req))
        self.assertEqual((again['status'], again['code'], again['replayed']), ('approved', 'OK', False))
        self.assertEqual(len(self.approvals_in_history()), 1)
        self.assertEqual(len(self.stored_requests()), 1)

    def test_two_copies_of_one_request_leave_one_approval_and_every_outcome_audited(self):
        req = self.req(rid='R-1')
        copies = {'n': 0}

        def other_copy_first(kind, payload):
            if kind == AB.REQUEST_KIND and payload.get('state') == 'pending' and copies['n'] == 0:
                copies['n'] += 1
                self.ask(dict(req))                                 # the other copy runs to the end
                raise FD.ConflictError('the other copy opened it first')
        res = self.ask(dict(req), who=Flaky(self.m.approver, other_copy_first))
        self.assertEqual(res['code'], 'CONCURRENT_CHANGE')
        self.assertEqual(len(self.approvals_in_history()), 1)
        kinds = [(e.event_type, e.outcome) for e in self.boundary_events()]
        self.assertIn(('approval_request.accepted', 'ok'), kinds)
        self.assertIn(('approval_request.refused', 'refused'), kinds)
        third = self.ask(dict(req))
        self.assertEqual((third['status'], third['replayed']), ('approved', True))


class TestIdentifiersAndTimesAreWholeStrings(Base):
    """F-60.  `$` matches before a final newline, so an identifier ending in one passed.  The same flaw sat in the session-expiry check, which also accepted non-ASCII digits."""

    def test_a_request_id_or_finding_id_with_a_trailing_newline_is_malformed(self):
        for field in ('request_id', 'finding_id'):
            n = len(self.stored_requests())
            res = self.ask(self.req(**{field: self.fid + '\n' if field == 'finding_id' else 'REQ-9\n'}))
            self.assertEqual((res['status'], res['code']), ('refused', 'REQUEST_MALFORMED'), field)
            self.assertEqual(len(self.stored_requests()), n)
        self.assertEqual(self.record()['status'], 'action_proposed')

    def test_other_control_characters_and_a_trailing_space_are_malformed_too(self):
        for bad in ('REQ-1\r', 'REQ-1\t', 'REQ-1 ', ' REQ-1', 'REQ\n-1', 'REQ-1\x00', 'REQ-1 ', 'REQ-١'):
            res = self.ask(self.req(rid=bad))
            self.assertEqual((res['status'], res['code']), ('refused', 'REQUEST_MALFORMED'), repr(bad))

    def test_the_screen_and_the_executor_check_refuse_a_finding_id_with_a_trailing_newline(self):
        r = AB.present(self.m.approver, self.scopes, self.m.clock, self.fid + '\n')
        self.assertEqual((r['status'], r['code']), ('refused', 'NOT_FOUND'))
        tok = self.token()
        res = AB.check_for_execution(self.m.approver, self.scopes, self.m.clock, self.fid + '\n', tok['version'], tok['digest'], tok['proposal'])
        self.assertEqual(res, {'valid': False, 'code': 'NOT_ALLOWED'})

    def test_no_audit_resource_name_can_carry_a_newline(self):
        self.ask(self.req(rid='REQ-9\n'))
        AB.present(self.m.approver, self.scopes, self.m.clock, self.fid + '\n')
        for e in self.m.w.audit.read(self.m.s.ctx):
            self.assertNotIn('\n', e.resource, e.resource)

    def test_a_session_expiry_with_a_trailing_newline_or_non_ascii_digits_is_not_live(self):
        now = self.m.clock.now()
        live = types.SimpleNamespace(expires_at='2999-01-01T00:00:00Z')
        self.assertTrue(AB._session_live(live, self.m.clock))
        for bad in ('2999-01-01T00:00:00Z\n', '٢٩٩٩-01-01T00:00:00Z', '2999-01-01T00:00:00Z ', '2999-01-01T00:00:00', None, 5):
            self.assertFalse(AB._session_live(types.SimpleNamespace(expires_at=bad), self.m.clock), repr(bad))
        self.assertTrue(now < '2999')


class TestAnApprovalIsAuditedAfterAFailedFirstAuditWrite(Base):
    """The audit-consistency risk: the approval is recorded, then the success audit entry cannot be written.  The answer used to be noted first, so a retry returned it as a replay and the `accepted` entry never existed."""

    def test_the_approval_exists_the_caller_is_told_and_a_retry_writes_the_missing_entry(self):
        req = self.req(rid='R-1')
        with self.assertRaises(RuntimeError):
            self.ask(req, who=FlakyLog(self.m.approver, ['approval_request.accepted']))
        self.assertEqual(self.record()['status'], 'action_approved')
        self.assertEqual([e for e in self.boundary_events() if e.event_type == 'approval_request.accepted'], [])
        self.assertEqual(self.stored_requests()[0].payload['state'], 'pending', 'the answer is not noted until the audit entry exists')
        again = self.ask(dict(req))
        self.assertEqual((again['status'], again['code'], again['recovered']), ('approved', 'OK', True))
        acc = [e for e in self.boundary_events() if e.event_type == 'approval_request.accepted']
        self.assertEqual(len(acc), 1)
        self.assertEqual(len(self.approvals_in_history()), 1)
        third = self.ask(dict(req))
        self.assertEqual((third['status'], third['replayed']), ('approved', True))

    def test_a_crash_after_the_audit_entry_and_before_the_answer_is_noted_leaves_at_least_one_entry(self):
        req = self.req(rid='R-1')
        crash = Flaky(self.m.approver, once(RuntimeError('crash'), lambda kind, p: kind == AB.REQUEST_KIND and p.get('state') == 'done'))
        with self.assertRaises(RuntimeError):
            self.ask(req, who=crash)
        self.assertGreaterEqual(len([e for e in self.boundary_events() if e.event_type == 'approval_request.accepted']), 1)
        again = self.ask(dict(req))
        self.assertEqual(again['status'], 'approved')
        self.assertEqual(len(self.approvals_in_history()), 1)
        self.assertGreaterEqual(len([e for e in self.boundary_events() if e.event_type == 'approval_request.accepted']), 1)

    def test_a_refused_request_whose_audit_write_fails_still_gets_its_answer_and_a_replay(self):
        req = self.req(rid='R-1', version=99)
        res = self.ask(req, who=FlakyLog(self.m.approver, ['approval_request.refused']))
        self.assertEqual(res['status'], 'refused')
        again = self.ask(dict(req))
        self.assertEqual((again['status'], again['code'], again['replayed']), (res['status'], res['code'], True))


class TestEveryCallOfTheExecutorCheckIsAudited(Base):
    """F-61 (found by the builder's review for the same class as F-59).  `check_for_execution` returned `NOT_ALLOWED` for a malformed or expired call without an audit event, though the contract says every call is audited."""

    def args(self):
        tok = self.token()
        return (self.fid, tok['version'], tok['digest'], tok['proposal'])

    def test_a_malformed_call_is_refused_and_audited(self):
        n = len(self.boundary_events())
        res = AB.check_for_execution(self.m.approver, self.scopes, self.m.clock, None, 1, 'd', 'p')
        self.assertEqual(res, {'valid': False, 'code': 'NOT_ALLOWED'})
        ev = self.boundary_events()[n:]
        self.assertEqual([(e.event_type, e.outcome) for e in ev], [('approval_request.execution_check', 'refused')])

    def test_an_expired_session_is_refused_and_audited_when_the_log_can_be_reached_and_never_raises_when_it_cannot(self):
        short = self.human('short', 'abby', FD.APPROVER, ttl=60)
        self.m.clock.advance(120)
        res = AB.check_for_execution(short, self.scopes, self.m.clock, *self.args())
        self.assertEqual(res, {'valid': False, 'code': 'NOT_ALLOWED'})
        res2 = AB.check_for_execution(FlakyLog(short, ['approval_request.execution_check'], times=9), self.scopes, self.m.clock, *self.args())
        self.assertEqual(res2, {'valid': False, 'code': 'NOT_ALLOWED'})

    def test_a_call_that_is_not_in_force_is_still_audited_as_before(self):
        n = len(self.boundary_events())
        self.assertEqual(AB.check_for_execution(self.m.approver, self.scopes, self.m.clock, *self.args())['code'], 'NOT_IN_FORCE')
        self.assertEqual(len(self.boundary_events()), n + 1)


if __name__ == '__main__':
    unittest.main()
