"""The APG-M9.4 correction of the approval request boundary (finding F-63).  The independent audit of APG-M9.3 found that `_session_live` read the clock without protection: a clock whose `now()` raised made
`present`, `request_approval` and `check_for_execution` raise to the caller, with no audit event and no refusal.  Nothing was approved by it (the audit did not claim a bypass); the failure handling was wrong.
A clock that cannot be read, or that gives anything but a real UTC moment, now ends the session: the three calls give their ordinary refusal, nothing is approved or executable, and the refusal is audited
(best-effort, as every refusal is).  The boundary reads the clock ONCE per call, so a clock that fails on a later read cannot fail half way through an approval.
These tests were written BEFORE the correction and run against the delivered M9.3 code (Blueprint Section 15.4, 15.11).  The doubles below are test doubles: the real clock and the sealed context are the Engine's."""
import types
import unittest
from unittest import mock
from . import _path                                         # noqa: F401
from .test_api_approval_boundary import Base, Grants, Flaky, AB, FD
from .test_api_m93_corrections import Expiring, Fixed

NOW = '2026-10-01T09:00:00Z'                                 # what the test world's clock says
FUTURE = '2999-01-01T00:00:00Z'


class RaisingClock:
    """A clock whose now() raises the chosen exception every time."""
    def __init__(self, exc):
        self.exc, self.reads = exc, 0

    def now(self):
        self.reads += 1
        raise self.exc


class FailsAfter:
    """A clock that answers `good` for the first `n` reads and raises from then on."""
    def __init__(self, good, n, exc=None):
        self.good, self.n, self.exc, self.reads = good, n, exc or RuntimeError('clock unavailable'), 0

    def now(self):
        self.reads += 1
        if self.reads > self.n:
            raise self.exc
        return self.good


class Counting:
    def __init__(self, good):
        self.good, self.reads = good, 0

    def now(self):
        self.reads += 1
        return self.good


class Advancing:
    """A clock that moves on one second at every read, from 09:00:00."""
    def __init__(self):
        self.reads = 0

    def now(self):
        self.reads += 1
        return '2026-10-01T09:00:%02dZ' % (self.reads - 1)


class NoNow:
    """Not a clock at all: no now()."""


class NotCallable:
    now = 'tuesday'


class Boom(Exception):
    pass


class WithCtx(Flaky):
    """The real scoped store in every respect except that the context it presents is the given one."""
    def __init__(self, inner, ctx):
        super().__init__(inner, None)
        self._ctx = ctx

    @property
    def ctx(self):
        return self._ctx


class WithBrokenWrites(Flaky):
    """The real scoped store, except that writing an audit event raises."""
    def log(self, *a, **k):
        raise Boom('audit store unavailable')


def broken_ctx(c, attr, exc, expires_at=FUTURE):
    """A copy of the context in which reading `attr` raises `exc`."""
    def boom(self):
        raise exc
    o = type('BrokenCtx', (), {attr: property(boom)})()
    for n in ('tenant_id', 'user_id', 'roles', 'actor_kind', 'session_id', 'seal', 'expires_at'):
        if n != attr:
            setattr(o, n, expires_at if n == 'expires_at' else getattr(c, n))
    return o


EXCEPTIONS = [RuntimeError('clock unavailable'), ValueError('bad'), OSError('io'), KeyError('k'), TypeError('t'), ZeroDivisionError('z'), AttributeError('a'), LookupError('l'), Boom('custom'), Exception('plain')]
BAD_READINGS = [None, 5, 5.5, True, [], ['2026-10-01T09:00:00Z'], {}, b'2026-10-01T09:00:00Z', '', 'garbage', '2026-10-01T09:00:00', '2026-10-01T09:00:00Z\n', ' 2026-10-01T09:00:00Z', '2026-10-01T09:00:00Z ',
                '٢٠٢٦-10-01T09:00:00Z', '2026-13-01T09:00:00Z', '2026-02-30T09:00:00Z', '2026-10-01T25:00:00Z', '2026-10-01T09:60:00Z', '2026-10-01T09:00:60Z', '0000-10-01T09:00:00Z', '2026-10-01 09:00:00Z']


class Calls(Base):
    """The three entry points, called with a given clock; the helpers return the answer, or the exception that escaped (so a test can say 'nothing escaped')."""

    def present_with(self, clock, who=None):
        return AB.present(who or self.m.approver, self.scopes, clock, self.fid)

    def request_with(self, clock, rid, who=None):
        return AB.request_approval(who or self.m.approver, self.scopes, clock, self.req(rid=rid))

    def check_with(self, clock, who=None):
        tok = self.token()
        return AB.check_for_execution(who or self.m.approver, self.scopes, clock, self.fid, tok['version'], tok['digest'], tok['proposal'])

    def assert_all_three_refuse(self, clock, label):
        """No exception escapes; each call gives its ordinary refusal; nothing is approved; one audit event for each call."""
        n0, rq0, rec0 = len(self.boundary_events()), len(self.stored_requests()), self.record()
        r = self.present_with(clock)
        self.assertEqual((r['status'], r['code']), ('refused', 'NOT_ALLOWED'), label)
        self.assertIsNone(r.get('token'), label)
        self._k = getattr(self, '_k', 0) + 1
        res = self.request_with(clock, f'CLK-{self._k}')
        self.assertEqual((res['status'], res['code']), ('refused', 'SESSION_EXPIRED'), label)
        self.assertEqual(self.check_with(clock), {'valid': False, 'code': 'NOT_ALLOWED'}, label)
        new = self.boundary_events()[n0:]
        self.assertEqual(sorted(e.event_type for e in new), ['approval_request.execution_check', 'approval_request.refused', 'approval_request.refused'], label)
        self.assertEqual({e.outcome for e in new}, {'refused'}, label)
        self.assertEqual(len(self.stored_requests()), rq0, 'nothing is stored for a session that cannot be checked: ' + label)
        self.assertEqual(self.record(), rec0, 'the finding is untouched: ' + label)
        self.assertEqual(self.record()['status'], 'action_proposed', label)
        self.assertEqual(self.approvals_in_history(), [], label)


class TestAClockThatRaisesNeverEscapesAndNeverApproves(Calls):

    def test_every_ordinary_exception_type_is_a_refusal_at_all_three_entry_points(self):
        for exc in EXCEPTIONS:
            self.assert_all_three_refuse(RaisingClock(exc), type(exc).__name__)

    def test_the_audit_names_the_clock_not_a_missing_person(self):
        n0 = len(self.boundary_events())
        self.present_with(RaisingClock(RuntimeError('clock unavailable')))
        self.request_with(RaisingClock(RuntimeError('clock unavailable')), 'WHY-1')
        self.check_with(RaisingClock(RuntimeError('clock unavailable')))
        for e in self.boundary_events()[n0:]:
            self.assertIn('clock', e.reason, e.reason)
            self.assertNotIn('clock unavailable', repr((e.resource, e.reason, e.detail)), 'the text of the exception is not copied into the audit trail')

    def test_the_clock_is_read_once_per_call_and_a_failed_read_is_not_retried(self):
        c = RaisingClock(RuntimeError('clock unavailable'))
        self.present_with(c)
        self.assertEqual(c.reads, 1)
        c = RaisingClock(RuntimeError('clock unavailable'))
        self.request_with(c, 'ONCE-1')
        self.assertEqual(c.reads, 1)
        c = RaisingClock(RuntimeError('clock unavailable'))
        self.check_with(c)
        self.assertEqual(c.reads, 1)

    def test_a_clock_that_is_missing_or_not_a_clock_ends_the_session(self):
        for clock in (None, NoNow(), NotCallable(), object(), 'now', 5):
            self.assert_all_three_refuse(clock, repr(clock)[:40])

    def test_a_clock_that_raises_a_base_exception_is_not_swallowed(self):
        """Only ordinary exceptions are a refusal; an interrupt still stops the program."""
        for exc in (KeyboardInterrupt(), SystemExit(2)):
            with self.assertRaises(type(exc)):
                self.present_with(RaisingClock(exc))
        self.assertEqual(self.record()['status'], 'action_proposed')


class TestAClockThatSaysSomethingElseEndsTheSession(Calls):

    def test_every_reading_that_is_not_a_real_moment_is_a_refusal_at_all_three_entry_points(self):
        for i, bad in enumerate(BAD_READINGS):
            self.assert_all_three_refuse(Fixed(bad), f'{i}:{bad!r}')

    def test_a_reading_that_is_a_real_moment_but_wrong_for_the_session_is_the_ordinary_ended_session(self):
        """Equal to the expiry, or later: the session has ended.  Earlier: it is live."""
        for now in ('2999-01-01T00:00:00Z', '2999-01-01T00:00:01Z', '9999-12-31T23:59:59Z'):
            r = AB.present(Expiring(self.m.approver, FUTURE), self.scopes, Fixed(now), self.fid)
            self.assertEqual((r['status'], r['code']), ('refused', 'NOT_ALLOWED'), now)
            res = AB.request_approval(Expiring(self.m.approver, FUTURE), self.scopes, Fixed(now), self.req(rid='LATE-' + now[:4] + now[-3:-1]))
            self.assertEqual((res['status'], res['code']), ('refused', 'SESSION_EXPIRED'), now)
            tok = self.token()
            self.assertEqual(AB.check_for_execution(Expiring(self.m.approver, FUTURE), self.scopes, Fixed(now), self.fid, tok['version'], tok['digest'], tok['proposal']), {'valid': False, 'code': 'NOT_ALLOWED'}, now)
        self.assertEqual(self.approvals_in_history(), [])
        self.assertEqual(self.record()['status'], 'action_proposed')

    def test_a_reading_earlier_than_the_expiry_is_live_at_the_screen(self):
        for now in ('2026-10-01T09:00:00Z', '2998-12-31T23:59:59Z', '0001-01-01T00:00:00Z'):
            r = AB.present(Expiring(self.m.approver, FUTURE), self.scopes, Fixed(now), self.fid)
            self.assertEqual((r['status'], r['can_approve']), ('shown', True), now)

    def test_a_reading_earlier_than_the_expiry_is_live_at_the_request(self):
        res = AB.request_approval(Expiring(self.m.approver, FUTURE), self.scopes, Fixed('2998-12-31T23:59:59Z'), self.req(rid='EARLY-1'))
        self.assertEqual((res['status'], res['code']), ('approved', 'OK'))
        self.assertEqual(len(self.approvals_in_history()), 1)

    def test_a_reading_earlier_than_the_expiry_is_live_at_the_executor_check(self):
        self.ask(self.req())
        tok = self.token()
        self.assertEqual(AB.check_for_execution(Expiring(self.m.approver, FUTURE), self.scopes, Fixed('2998-12-31T23:59:59Z'), self.fid, tok['version'], tok['digest'], tok['proposal'])['valid'], True)


class TestTheClockIsReadOnceSoALaterFailureCannotHalveAnApproval(Calls):

    def test_a_clock_that_fails_after_its_first_read_still_completes_the_whole_request(self):
        """The first read decides the session; the lifecycle then uses that reading, not the clock."""
        c = FailsAfter(NOW, 1)
        res = self.request_with(c, 'ONE-1', who=Expiring(self.m.approver, FUTURE))
        self.assertEqual((res['status'], res['code']), ('approved', 'OK'))
        self.assertEqual(c.reads, 1, 'the clock was read once and never again in the call')
        self.assertEqual(len(self.approvals_in_history()), 1)
        self.assertEqual(self.approvals_in_history()[0]['at'], NOW, 'the approval carries the reading that decided the session')
        self.assertEqual(self.stored_requests()[0].payload['state'], 'done')
        self.assertEqual(self.record()['status'], 'action_approved')

    def test_every_call_reads_the_clock_exactly_once(self):
        c = Counting(NOW)
        self.present_with(c)
        self.assertEqual(c.reads, 1)
        c = Counting(NOW)
        self.request_with(c, 'COUNT-1')
        self.assertEqual(c.reads, 1)
        c = Counting(NOW)
        self.request_with(c, 'COUNT-1')                           # the replay
        self.assertEqual(c.reads, 1)
        c = Counting(NOW)
        self.check_with(c)
        self.assertEqual(c.reads, 1)

    def test_the_answer_carries_the_one_reading_even_when_the_clock_moves_on(self):
        c = Advancing()
        res = self.request_with(c, 'MOVE-1')
        self.assertEqual((res['status'], res['code']), ('approved', 'OK'))
        self.assertEqual(c.reads, 1)
        h = self.approvals_in_history()[0]
        self.assertEqual((h['at'], res['approved_at'], res['approved_by']), ('2026-10-01T09:00:00Z', '2026-10-01T09:00:00Z', 'abby'), 'the history entry, the answer and the session check share one instant')

    def test_if_the_history_holds_no_entry_the_answer_still_names_the_approver_and_the_reading(self):
        """The fallback of the answer (the lifecycle approved, its history entry cannot be found): the approver of the call and the reading of the call."""
        with mock.patch.object(AB, '_approval_event', return_value=None):
            res = self.request_with(Advancing(), 'FALL-1')
        self.assertEqual((res['status'], res['code'], res['approved_by'], res['approved_at']), ('approved', 'OK', 'abby', '2026-10-01T09:00:00Z'))

    def test_a_clock_that_fails_on_the_second_read_does_not_change_the_screen_or_the_executor_check(self):
        self.assertEqual(self.present_with(FailsAfter(NOW, 1))['status'], 'shown')
        self.ask(self.req())
        self.assertEqual(self.check_with(FailsAfter(NOW, 1))['valid'], True)

    def test_a_clock_that_fails_on_every_read_after_the_first_cannot_make_a_session_live(self):
        """The failing second read is never made; the first read already said the session had ended."""
        c = FailsAfter('2999-01-01T00:00:01Z', 1)
        res = AB.request_approval(Expiring(self.m.approver, FUTURE), self.scopes, c, self.req(rid='END-1'))
        self.assertEqual((res['status'], res['code']), ('refused', 'SESSION_EXPIRED'))
        self.assertEqual(c.reads, 1)
        self.assertEqual(self.approvals_in_history(), [])


class TestAccessorFailuresOfTheSession(Calls):

    def test_an_expiry_that_cannot_be_read_ends_the_session(self):
        for exc in (RuntimeError('x'), AttributeError('x'), Boom('x')):
            who = WithCtx(self.m.approver, broken_ctx(self.m.approver.ctx, 'expires_at', exc))
            self.assert_all_three_refuse_with(who, type(exc).__name__)

    def test_an_actor_kind_that_cannot_be_read_is_not_a_person(self):
        who = WithCtx(self.m.approver, broken_ctx(self.m.approver.ctx, 'actor_kind', RuntimeError('x')))
        r = AB.present(who, self.scopes, self.m.clock, self.fid)
        self.assertEqual((r['status'], r['code']), ('refused', 'NOT_ALLOWED'))
        res = AB.request_approval(who, self.scopes, self.m.clock, self.req(rid='KIND-1'))
        self.assertEqual((res['status'], res['code']), ('refused', 'HUMAN_REQUIRED'))
        self.assertEqual(self.approvals_in_history(), [])
        self.assertEqual(self.record()['status'], 'action_proposed')

    def assert_all_three_refuse_with(self, who, label):
        n0 = len(self.boundary_events())
        r = AB.present(who, self.scopes, self.m.clock, self.fid)
        self.assertEqual((r['status'], r['code']), ('refused', 'NOT_ALLOWED'), label)
        res = AB.request_approval(who, self.scopes, self.m.clock, self.req(rid='ACC-' + label))
        self.assertEqual((res['status'], res['code']), ('refused', 'SESSION_EXPIRED'), label)
        tok = self.token()
        self.assertEqual(AB.check_for_execution(who, self.scopes, self.m.clock, self.fid, tok['version'], tok['digest'], tok['proposal']), {'valid': False, 'code': 'NOT_ALLOWED'}, label)
        self.assertEqual(len(self.boundary_events()) - n0, 3, label)
        self.assertEqual(self.approvals_in_history(), [], label)
        self.assertEqual(len(self.stored_requests()), 0, label)


class TestFailurePathsKeepTheInvariants(Calls):

    def test_repeated_refusals_leave_no_state_and_the_same_request_id_can_be_used_afterwards(self):
        for k in range(5):
            res = self.request_with(RaisingClock(RuntimeError('clock unavailable')), 'AGAIN-1')
            self.assertEqual((res['status'], res['code']), ('refused', 'SESSION_EXPIRED'))
        self.assertEqual(len(self.stored_requests()), 0)
        self.assertEqual(self.approvals_in_history(), [])
        res = self.request_with(self.m.clock, 'AGAIN-1')
        self.assertEqual((res['status'], res['code'], res['replayed']), ('approved', 'OK', False), 'the id was never used: the refusals stored nothing')
        self.assertEqual(len(self.approvals_in_history()), 1)
        again = self.request_with(self.m.clock, 'AGAIN-1')
        self.assertEqual((again['status'], again['replayed']), ('approved', True))
        self.assertEqual(len(self.approvals_in_history()), 1)

    def test_a_replay_with_a_failing_clock_is_a_refusal_not_the_stored_answer(self):
        self.request_with(self.m.clock, 'REPLAY-1')
        before = self.record()
        res = self.request_with(RaisingClock(RuntimeError('clock unavailable')), 'REPLAY-1')
        self.assertEqual((res['status'], res['code']), ('refused', 'SESSION_EXPIRED'))
        self.assertEqual(self.record(), before)
        self.assertEqual(len(self.approvals_in_history()), 1)
        self.assertEqual(self.request_with(self.m.clock, 'REPLAY-1')['replayed'], True, 'the stored answer is intact for a working clock')

    def test_a_failing_clock_does_not_change_an_approved_action_and_the_executor_check_recovers(self):
        self.request_with(self.m.clock, 'EXEC-1')
        before = self.record()
        for exc in EXCEPTIONS[:4]:
            self.assertEqual(self.check_with(RaisingClock(exc)), {'valid': False, 'code': 'NOT_ALLOWED'})
        self.assertEqual(self.record(), before, 'the approval is neither lost nor changed by a clock that failed')
        self.assertEqual(self.check_with(self.m.clock)['valid'], True)

    def test_no_failing_clock_ever_approves_whatever_else_is_true(self):
        """Approver role, project permission, a live-looking session: only the clock is bad."""
        for i, clock in enumerate([RaisingClock(e) for e in EXCEPTIONS] + [Fixed(b) for b in BAD_READINGS] + [None, NoNow(), NotCallable()]):
            res = AB.request_approval(Expiring(self.m.approver, FUTURE), self.scopes, clock, self.req(rid=f'NEVER-{i}'))
            self.assertEqual((res['status'], res['code']), ('refused', 'SESSION_EXPIRED'), i)
            tok = AB.present(Expiring(self.m.approver, FUTURE), self.scopes, clock, self.fid)
            self.assertIsNone(tok.get('token'), i)
        self.assertEqual(self.approvals_in_history(), [])
        self.assertEqual(self.record()['status'], 'action_proposed')
        self.assertEqual(len(self.stored_requests()), 0)

    def test_an_audit_write_that_fails_during_a_clock_refusal_is_still_a_refusal_and_is_not_reported_as_audited(self):
        """Refusals are audited best-effort (as before): the failure is swallowed, the refusal stands, and no event exists to claim."""
        who = WithBrokenWrites(self.m.approver, None)
        n0 = len(self.boundary_events())
        r = AB.present(who, self.scopes, RaisingClock(RuntimeError('clock unavailable')), self.fid)
        self.assertEqual((r['status'], r['code']), ('refused', 'NOT_ALLOWED'))
        res = AB.request_approval(who, self.scopes, RaisingClock(RuntimeError('clock unavailable')), self.req(rid='AUDF-1'))
        self.assertEqual((res['status'], res['code']), ('refused', 'SESSION_EXPIRED'))
        tok = self.token()
        self.assertEqual(AB.check_for_execution(who, self.scopes, RaisingClock(RuntimeError('clock unavailable')), self.fid, tok['version'], tok['digest'], tok['proposal']), {'valid': False, 'code': 'NOT_ALLOWED'})
        self.assertEqual(len(self.boundary_events()), n0, 'no event was written, so none is claimed')
        for answer in (r, res):
            self.assertNotIn('audited', answer)
        self.assertEqual(self.approvals_in_history(), [])

    def test_an_audit_write_that_fails_after_a_good_clock_still_raises_as_before(self):
        """The M9.2 rule is unchanged: a failed first audit write of an APPROVAL raises and leaves the request open (CF-29)."""
        box = {'n': 0}

        class FailLog(Flaky):
            def log(inner_self, *a, **k):
                if a and a[0] == 'approval_request.accepted' and box['n'] == 0:
                    box['n'] = 1
                    raise Boom('audit store unavailable')
                return inner_self._i.log(*a, **k)
        who = FailLog(self.m.approver, None)
        with self.assertRaises(Boom):
            AB.request_approval(who, self.scopes, self.m.clock, self.req(rid='M92-1'))
        res = AB.request_approval(who, self.scopes, self.m.clock, self.req(rid='M92-1'))
        self.assertEqual((res['status'], res['code']), ('approved', 'OK'))
        self.assertEqual(len(self.approvals_in_history()), 1)

    def test_a_working_clock_behaves_exactly_as_before(self):
        r = self.present_with(self.m.clock)
        self.assertEqual((r['status'], r['can_approve']), ('shown', True))
        res = self.request_with(self.m.clock, 'OK-1')
        self.assertEqual((res['status'], res['code'], res['replayed']), ('approved', 'OK', False))
        self.assertEqual(self.check_with(self.m.clock)['valid'], True)
        self.assertEqual(self.request_with(self.m.clock, 'OK-1')['replayed'], True)

    def test_another_tenants_session_with_a_failing_clock_is_refused_and_with_a_working_one_still_does_not_see_the_finding(self):
        two = self.m.w.who('apr2', 'zero_two', 'abby', (FD.APPROVER,), ttl=10 ** 8)
        sc2 = Grants({('zero_two', 'abby', 'PRJ-001'): ('view', 'approve')})
        bad = AB.request_approval(two, sc2, RaisingClock(RuntimeError('clock unavailable')), self.req(rid='T2-1'))
        self.assertEqual((bad['status'], bad['code']), ('refused', 'SESSION_EXPIRED'))
        good = AB.request_approval(two, sc2, self.m.clock, self.req(rid='T2-2'))
        self.assertEqual((good['status'], good['code']), ('refused', 'NOT_FOUND'))
        self.assertEqual(self.approvals_in_history(), [])

    def test_a_person_without_the_approver_role_with_a_failing_clock_gets_the_clock_refusal_first_and_the_role_refusal_otherwise(self):
        viewer = self.human('viewer-1', 'abby', FD.REVIEWER)
        self.assertEqual(self.request_with(RaisingClock(RuntimeError('clock unavailable')), 'ROLE-1', who=viewer)['code'], 'SESSION_EXPIRED')
        self.assertEqual(self.request_with(self.m.clock, 'ROLE-2', who=viewer)['code'], 'ROLE_REQUIRED')


class TestTheSessionRuleOfM93StillHolds(unittest.TestCase):
    """The helper keeps its M9.3 meaning: a boolean, strict, ASCII, whole string, strictly later than a real moment."""

    def test_the_helper_still_answers_true_or_false_and_never_raises_for_a_failing_clock_or_expiry(self):
        ctx = types.SimpleNamespace(expires_at=FUTURE)
        self.assertIs(AB._session_live(ctx, Fixed(NOW)), True)
        self.assertIs(AB._session_live(ctx, Fixed(FUTURE)), False)
        for exc in EXCEPTIONS:
            self.assertIs(AB._session_live(ctx, RaisingClock(exc)), False, type(exc).__name__)
        for clock in (None, NoNow(), NotCallable()):
            self.assertIs(AB._session_live(ctx, clock), False)
        self.assertIs(AB._session_live(broken_ctx(types.SimpleNamespace(tenant_id='t', user_id='u', roles=(), actor_kind='human', session_id='s', seal='x'), 'expires_at', RuntimeError('x')), Fixed(NOW)), False)
        self.assertIs(AB._session_live(types.SimpleNamespace(), Fixed(NOW)), False, 'a context with no expiry at all has no live session')

    def test_the_helper_does_not_swallow_an_interrupt(self):
        with self.assertRaises(KeyboardInterrupt):
            AB._session_live(types.SimpleNamespace(expires_at=FUTURE), RaisingClock(KeyboardInterrupt()))


if __name__ == '__main__':
    unittest.main()
