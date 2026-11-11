"""The APG-M9.3 correction of the approval request boundary (finding F-62).  The independent audit of APG-M9.2 found that `_session_live` checked the SHAPE of the session expiry time and then compared it as a string, so impossible
values such as 2999-99-99T99:99:99Z, 2999-13-01T00:00:00Z and 2999-01-01T25:61:61Z counted as live.  An expiry is live only if it is a real UTC moment written YYYY-MM-DDTHH:MM:SSZ in ASCII and is strictly later than the current time;
the current time is held to the same rule (fail closed).  These tests were written BEFORE the correction and run against the delivered M9.2 code (Blueprint Section 15.4, 15.11)."""
import types
import unittest
from . import _path                                         # noqa: F401
from .test_api_approval_boundary import Base, Grants, Flaky, AB, FD


class Expiring(Flaky):
    """A scoped store that is the real one in every respect except that the context it presents carries a chosen expiry time."""
    def __init__(self, inner, expires_at):
        super().__init__(inner, None)
        c = inner.ctx
        self._ctx = types.SimpleNamespace(**{n: getattr(c, n) for n in ('tenant_id', 'user_id', 'roles', 'actor_kind', 'session_id', 'seal')}, expires_at=expires_at)

    @property
    def ctx(self):
        return self._ctx


class Fixed:
    """A clock that says one chosen thing."""
    def __init__(self, now):
        self._now = now

    def now(self):
        return self._now


def live(expires_at, now='2026-10-01T09:00:00Z'):
    return AB._session_live(types.SimpleNamespace(expires_at=expires_at), Fixed(now))


class Stringy:
    """Not a string; str() of it is a valid future moment.  A check that converted the value to text before matching would accept it."""
    def __str__(self):
        return '2999-01-01T00:00:00Z'


# values the audit gave, and the other ways a well-shaped string can fail to be a moment
IMPOSSIBLE = ['2999-99-99T99:99:99Z', '2999-13-01T00:00:00Z', '2999-01-01T25:61:61Z',
              '2999-00-10T00:00:00Z', '2999-13-10T00:00:00Z', '2999-99-10T00:00:00Z',                       # months
              '2999-01-00T00:00:00Z', '2999-01-32T00:00:00Z', '2999-01-99T00:00:00Z',                       # days
              '2999-01-01T24:00:00Z', '2999-01-01T25:00:00Z', '2999-01-01T99:00:00Z',                       # hours
              '2999-01-01T00:60:00Z', '2999-01-01T00:61:00Z', '2999-01-01T00:99:00Z',                       # minutes
              '2999-01-01T00:00:60Z', '2999-01-01T00:00:61Z', '2999-01-01T00:00:99Z',                       # seconds (a leap second is refused too, I-94)
              '2999-02-30Z'.replace('Z', 'T00:00:00Z'), '2999-02-31T00:00:00Z', '2999-04-31T00:00:00Z', '2999-06-31T00:00:00Z', '2999-09-31T00:00:00Z', '2999-11-31T00:00:00Z',   # days a month does not have
              '2999-02-29T00:00:00Z', '2100-02-29T00:00:00Z', '2300-02-29T00:00:00Z', '2999-02-29T23:59:59Z', '3001-02-29T00:00:00Z',                                       # 29 February in years that are not leap years
              '0000-01-01T00:00:00Z', '0000-12-31T23:59:59Z']                                               # there is no year 0000 (I-94)
VALID_FUTURE = ['2999-01-01T00:00:00Z', '2999-12-31T23:59:59Z', '2028-02-29T12:00:00Z', '2400-02-29T00:00:00Z', '2096-02-29T23:59:59Z', '2999-01-31T00:00:00Z', '2999-03-31T00:00:00Z', '2999-04-30T00:00:00Z',
                '2999-05-31T00:00:00Z', '2999-06-30T00:00:00Z', '2999-07-31T00:00:00Z', '2999-08-31T00:00:00Z', '2999-09-30T00:00:00Z', '2999-10-31T00:00:00Z', '2999-11-30T00:00:00Z', '2999-12-01T09:00:00Z',
                '9999-12-31T23:59:59Z', '2999-02-28T00:00:00Z']
BAD_SHAPE = ['2999-01-01T00:00:00Z\n', '٢٩٩٩-01-01T00:00:00Z', '2999-01-01T00:00:00Z ', ' 2999-01-01T00:00:00Z', '2999-01-01T00:00:00', '2999-01-01 00:00:00Z', '2999-01-01T00:00:00+00:00',
             '2999-01-01T00:00:00.000Z', '2999-1-1T0:0:0Z', '2999-01-01T00:00:00z', '2999-01-01t00:00:00Z', '', 'Z', None, 5, 2999, b'2999-01-01T00:00:00Z', ['2999-01-01T00:00:00Z'], True, Stringy()]                                      # Stringy: not a string, but its text form is a valid future moment


class TestTheExpiryMustBeARealMomentInTime(unittest.TestCase):
    """The helper on its own: every boundary of month, day, hour, minute, second and leap year, from both sides."""

    def test_the_impossible_values_the_audit_found_are_not_live(self):
        for bad in ('2999-99-99T99:99:99Z', '2999-13-01T00:00:00Z', '2999-01-01T25:61:61Z'):
            self.assertFalse(live(bad), bad)

    def test_no_impossible_month_day_hour_minute_second_or_year_is_live(self):
        for bad in IMPOSSIBLE:
            self.assertFalse(live(bad), bad)

    def test_real_moments_in_the_future_are_live_including_the_last_day_of_every_month(self):
        for good in VALID_FUTURE:
            self.assertTrue(live(good), good)

    def test_leap_days_are_live_only_in_leap_years(self):
        for y in (2028, 2032, 2096, 2400, 2800, 2999 - 3):
            self.assertEqual(live(f'{y}-02-29T00:00:00Z'), (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)), y)
        for y, ok in ((2100, False), (2200, False), (2300, False), (2400, True), (2500, False), (2600, False), (2800, True), (2900, False), (3000, False), (2996, True), (2997, False), (2998, False), (2999, False)):
            self.assertEqual(live(f'{y}-02-29T00:00:00Z'), ok, y)
        self.assertTrue(live('2999-02-28T23:59:59Z'))
        self.assertFalse(live('2999-02-30T00:00:00Z'))

    def test_each_part_is_live_at_its_last_valid_value_and_not_one_past_it(self):
        edges = (('2999-12-01T00:00:00Z', '2999-13-01T00:00:00Z'), ('2999-01-31T00:00:00Z', '2999-01-32T00:00:00Z'), ('2999-01-01T23:00:00Z', '2999-01-01T24:00:00Z'),
                 ('2999-01-01T00:59:00Z', '2999-01-01T00:60:00Z'), ('2999-01-01T00:00:59Z', '2999-01-01T00:00:60Z'), ('2999-01-01T00:00:00Z', '2999-00-01T00:00:00Z'), ('2999-01-01T00:00:00Z', '2999-01-00T00:00:00Z'))
        for ok, bad in edges:
            self.assertTrue(live(ok), ok)
            self.assertFalse(live(bad), bad)
        self.assertFalse(live('0001-01-01T00:00:00Z', now='0000-01-01T00:00:00Z'), 'a clock that says year 0000 is not a moment either')

    def test_year_0001_is_the_first_year_and_year_0000_does_not_exist(self):
        self.assertTrue(AB._is_moment('0001-01-01T00:00:00Z'))
        self.assertTrue(AB._is_moment('0001-12-31T23:59:59Z'))
        self.assertFalse(AB._is_moment('0000-01-01T00:00:00Z'))
        self.assertTrue(live('0001-01-01T00:00:01Z', now='0001-01-01T00:00:00Z'), 'the first second of year 1 is a moment')
        self.assertFalse(live('0001-01-01T00:00:00Z', now='0001-01-01T00:00:00Z'))
        self.assertFalse(AB._is_moment('0004-02-30T00:00:00Z'))
        self.assertTrue(AB._is_moment('0004-02-29T00:00:00Z'), 'year 4 is a leap year')
        self.assertFalse(AB._is_moment('0100-02-29T00:00:00Z'))
        self.assertTrue(AB._is_moment('0400-02-29T00:00:00Z'))

    def test_a_value_with_a_wrong_shape_is_not_live(self):
        for bad in BAD_SHAPE:
            self.assertFalse(live(bad), repr(bad))

    def test_an_expiry_that_is_not_strictly_later_than_now_is_not_live(self):
        now = '2026-10-01T09:00:00Z'
        self.assertFalse(live('2026-10-01T09:00:00Z', now), 'equal to now')
        self.assertTrue(live('2026-10-01T09:00:01Z', now), 'one second later')
        self.assertFalse(live('2026-10-01T08:59:59Z', now), 'one second earlier')
        self.assertFalse(live('2000-01-01T00:00:00Z', now))
        self.assertFalse(live('2026-09-30T23:59:59Z', now))
        self.assertTrue(live('2026-10-01T09:01:00Z', now))
        self.assertTrue(live('2026-10-02T00:00:00Z', now))
        self.assertTrue(live('2027-01-01T00:00:00Z', now))

    def test_a_clock_that_does_not_give_a_real_moment_makes_every_session_not_live(self):
        for now in ('2026-10-01T09:00:00Z\n', '2026-13-01T09:00:00Z', '2026-10-01T25:00:00Z', 'now', '', None, 5, '2026-10-01T09:00:00'):
            self.assertFalse(live('2999-01-01T00:00:00Z', now), repr(now))


class TestTheSessionCheckThroughTheBoundaryEntryPoints(Base):
    """The same values, offered in the session the caller presents to the three calls."""

    def present(self, expires_at):
        return AB.present(Expiring(self.m.approver, expires_at), self.scopes, self.m.clock, self.fid)

    def ask_with(self, expires_at, rid):
        return AB.request_approval(Expiring(self.m.approver, expires_at), self.scopes, self.m.clock, self.req(rid=rid))

    def check_with(self, expires_at):
        tok = self.token()
        return AB.check_for_execution(Expiring(self.m.approver, expires_at), self.scopes, self.m.clock, self.fid, tok['version'], tok['digest'], tok['proposal'])

    def test_the_screen_refuses_an_impossible_expiry_and_shows_a_real_one(self):
        for bad in IMPOSSIBLE[:12] + ['2999-02-29T00:00:00Z', '0000-01-01T00:00:00Z']:
            r = self.present(bad)
            self.assertEqual((r['status'], r['code']), ('refused', 'NOT_ALLOWED'), bad)
            self.assertNotIn('token', r)
        for good in ('2999-01-01T00:00:00Z', '2400-02-29T00:00:00Z'):
            r = self.present(good)
            self.assertEqual((r['status'], r['can_approve']), ('shown', True), good)

    def test_a_request_with_an_impossible_expiry_is_refused_as_an_ended_session_and_approves_nothing(self):
        n = 0
        for bad in ('2999-99-99T99:99:99Z', '2999-13-01T00:00:00Z', '2999-01-01T25:61:61Z', '2999-02-30T00:00:00Z', '2100-02-29T00:00:00Z', '2999-01-01T00:00:60Z', '0000-01-01T00:00:00Z'):
            n += 1
            res = self.ask_with(bad, f'BAD-{n}')
            self.assertEqual((res['status'], res['code']), ('refused', 'SESSION_EXPIRED'), bad)
            self.assertEqual(self.record()['status'], 'action_proposed', bad)
            self.assertEqual(self.approvals_in_history(), [], bad)
            self.assertEqual(len(self.stored_requests()), 0, 'nothing is stored for a session that is not live')

    def test_a_request_with_a_real_future_expiry_is_approved(self):
        res = self.ask_with('2400-02-29T00:00:00Z', 'GOOD-1')
        self.assertEqual((res['status'], res['code']), ('approved', 'OK'))
        self.assertEqual(len(self.approvals_in_history()), 1)

    def test_the_executor_check_is_false_for_an_impossible_expiry_and_true_for_a_real_one_once_approved(self):
        self.ask(self.req())
        tok = self.token()
        for bad in ('2999-99-99T99:99:99Z', '2999-13-01T00:00:00Z', '2999-01-01T25:61:61Z', '2999-04-31T00:00:00Z'):
            self.assertEqual(self.check_with(bad), {'valid': False, 'code': 'NOT_ALLOWED'}, bad)
        self.assertEqual(self.check_with('2999-12-31T23:59:59Z')['valid'], True)
        self.assertEqual(tok['version'], self.token()['version'])

    def test_each_refusal_is_audited_and_no_event_carries_the_impossible_value_as_a_resource(self):
        before = len(self.boundary_events())
        self.present('2999-13-01T00:00:00Z')
        self.ask_with('2999-13-01T00:00:00Z', 'AUD-1')
        self.check_with('2999-13-01T00:00:00Z')
        new = self.boundary_events()[before:]
        self.assertEqual(sorted(e.event_type for e in new), ['approval_request.execution_check', 'approval_request.refused', 'approval_request.refused'])
        for e in new:
            self.assertNotIn('2999-13-01', repr((e.resource, e.reason)))

    def test_a_clock_that_is_not_a_real_moment_ends_every_session_at_all_three_calls(self):
        for now in ('2026-13-01T09:00:00Z', 'garbage', '2026-10-01T09:00:00Z\n'):
            clock = Fixed(now)
            r = AB.present(self.m.approver, self.scopes, clock, self.fid)
            self.assertEqual((r['status'], r['code']), ('refused', 'NOT_ALLOWED'), now)
            res = AB.request_approval(self.m.approver, self.scopes, clock, self.req(rid='CLK-1'))
            self.assertEqual((res['status'], res['code']), ('refused', 'SESSION_EXPIRED'), now)
            tok = self.token()
            self.assertEqual(AB.check_for_execution(self.m.approver, self.scopes, clock, self.fid, tok['version'], tok['digest'], tok['proposal']), {'valid': False, 'code': 'NOT_ALLOWED'}, now)
        self.assertEqual(self.record()['status'], 'action_proposed')

    def test_a_session_that_ended_in_the_past_still_ends_at_the_boundary(self):
        res = self.ask_with('2026-10-01T08:59:59Z', 'PAST-1')
        self.assertEqual((res['status'], res['code']), ('refused', 'SESSION_EXPIRED'))
        res = self.ask_with('2026-10-01T09:00:00Z', 'PAST-2')
        self.assertEqual((res['status'], res['code']), ('refused', 'SESSION_EXPIRED'), 'an expiry equal to now has ended')
        res = self.ask_with('2026-10-01T09:00:01Z', 'PAST-3')
        self.assertEqual((res['status'], res['code']), ('approved', 'OK'), 'one second later is live')


class TestTheSameShapeFlawsStayClosed(Base):
    """The corrections of M9.2 (F-60) must still hold: whole strings, ASCII only."""

    def test_a_trailing_newline_and_non_ascii_digits_in_the_expiry_are_refused_at_the_entry_points(self):
        for bad in ('2999-01-01T00:00:00Z\n', '٢٩٩٩-01-01T00:00:00Z', '2999-01-01T00:00:00Z '):
            res = AB.request_approval(Expiring(self.m.approver, bad), self.scopes, self.m.clock, self.req(rid='NL-1'))
            self.assertEqual((res['status'], res['code']), ('refused', 'SESSION_EXPIRED'), repr(bad))
        self.assertEqual(self.approvals_in_history(), [])

    def test_every_value_that_is_not_live_is_refused_the_same_way_by_a_request(self):
        for i, bad in enumerate(IMPOSSIBLE + BAD_SHAPE):
            res = AB.request_approval(Expiring(self.m.approver, bad), self.scopes, self.m.clock, self.req(rid=f'ALL-{i}'))
            self.assertEqual((res['status'], res['code']), ('refused', 'SESSION_EXPIRED'), repr(bad))
        self.assertEqual(self.approvals_in_history(), [])
        self.assertEqual(self.record()['status'], 'action_proposed')


if __name__ == '__main__':
    unittest.main()
