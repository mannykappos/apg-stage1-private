"""The approval request boundary (APG-M9.1, carried-forward item CF-25, gate CF-22).  

What a screen or an API needs around `approve_action`: a request that is checked for shape, a person with a live session and the approver role, authorisation for the finding's PROJECT (asked of a port on
every request), one answer for one request id however many times it is sent, recovery of a request that stopped half way, and an audit event for every outcome.  The scenarios of the 14:29 instruction:
version and digest binding (stale approvals), the proposal swap (F-56), malformed input, replay, evidence changing between proposal, approval and execution, other tenants and other projects."""
import unittest
from unittest import mock
from . import _path                                         # noqa: F401
from .test_det_findings import breach, first
from .test_det_approval_binding import worsen
from .test_det_proposal_binding import proposed, reproposed
from apg.det import findings as FD
from apg.api import approval_boundary as AB

TEXT1 = 'renegotiate with the supplier'
TEXT2 = 'terminate the supplier contract'
SECRET = 'SECRET-RATIONALE-7731'


class Grants(AB.ProjectActionPort):
    """Reference port for the tests: grants = {(tenant, user, where): actions}, where `where` is a project id or '*tenant*' for tenant-level findings."""
    def __init__(self, grants):
        self.grants, self.asked = grants, []

    def allows(self, ctx, scope, action):
        where = scope.get('project') if scope.get('level') == 'project' else '*tenant*'
        self.asked.append((ctx.user_id, where, action))
        return action in self.grants.get((ctx.tenant_id, ctx.user_id, where), ())


class Flaky:
    """A scoped store that delegates to the real one but lets a test make a chosen write fail once."""
    def __init__(self, inner, on_put):
        self._i, self.on_put = inner, on_put

    def __getattr__(self, name):
        return getattr(self._i, name)

    def put(self, kind, key, payload, expected_revision=None):
        if self.on_put:
            self.on_put(kind, payload)
        return self._i.put(kind, key, payload, expected_revision)


def once(exc, when):
    box = {'armed': True}

    def on_put(kind, payload):
        if box['armed'] and when(kind, payload):
            box['armed'] = False
            raise exc
    return on_put


class Base(unittest.TestCase):
    propose = True

    def setUp(self):
        self.m = breach()
        self.fid, _ = first(self.m)
        if self.propose:
            proposed(self.m, self.fid, TEXT1)
        self.scopes = Grants({('zero_one', 'abby', 'PRJ-001'): ('view', 'approve')})
        self.n = 0

    def token(self):
        return FD.approval_token(FD.get(self.m.svc, self.fid))

    def req(self, tok=None, rid=None, **over):
        tok = tok or self.token()
        self.n += 1
        d = {'request_id': rid or f'REQ-{self.n}', 'finding_id': tok['finding_id'], 'version': tok['version'], 'digest': tok['digest'], 'proposal': tok['proposal'], 'rationale': 'I approve what I was shown'}
        d.update(over)
        return d

    def ask(self, request, who=None, scopes='default'):
        return AB.request_approval(who or self.m.approver, self.scopes if scopes == 'default' else scopes, self.m.clock, request)

    def human(self, token, user, *roles, ttl=10 ** 8, kind='human'):
        return self.m.w.who(token, 'zero_one', user, roles, kind, ttl=ttl)

    def boundary_events(self):
        return [e for e in self.m.w.audit.read(self.m.s.ctx) if e.event_type.startswith('approval_request.')]

    def record(self):
        return FD.get(self.m.svc, self.fid)

    def stored_requests(self):
        return self.m.s.query(AB.REQUEST_KIND)

    def approvals_in_history(self):
        return [h for h in self.record()['history'] if h['event'] == 'status_change' and h['to'] == 'action_approved']

    def refused_untouched(self, res, code):
        before, n_req, n_ev = self.record(), len(self.stored_requests()), len(self.boundary_events())
        self.assertEqual((res['status'], res['code']), ('refused', code), res)
        return before, n_req, n_ev


class TestThePath(Base):
    def test_the_screen_shows_the_proposal_who_wrote_it_and_the_token_to_hand_back(self):
        r = AB.present(self.m.approver, self.scopes, self.m.clock, self.fid)
        self.assertEqual((r['status'], r['code'], r['finding_status'], r['can_approve']), ('shown', 'OK', 'action_proposed', True))
        self.assertEqual(r['token'], self.token())
        self.assertEqual((r['proposal']['text'], r['proposal']['proposed_by']), (TEXT1, 'oscar'))
        self.assertEqual(r['scope'], {'level': 'project', 'project': 'PRJ-001'})

    def test_a_request_built_from_the_shown_token_approves_exactly_what_was_shown(self):
        shown = AB.present(self.m.approver, self.scopes, self.m.clock, self.fid)['token']
        res = self.ask(self.req(shown))
        self.assertEqual((res['status'], res['code'], res['replayed'], res['finding_status'], res['approved_by']), ('approved', 'OK', False, 'action_approved', 'abby'))
        self.assertEqual((res['approved_version'], res['approved_digest'], res['approved_proposal']), (shown['version'], shown['digest'], shown['proposal']))
        f = self.record()
        self.assertTrue(FD.approval_current(f))
        self.assertEqual(f['action']['text'], TEXT1)
        self.assertEqual(len(self.approvals_in_history()), 1)

    def test_the_approval_is_audited_once_by_the_boundary(self):
        self.ask(self.req())
        ev = self.boundary_events()
        self.assertEqual([e.event_type for e in ev], ['approval_request.accepted'])
        self.assertEqual((ev[0].outcome, ev[0].resource), ('ok', 'approval_request/REQ-1'))

    def test_the_proposer_is_told_they_cannot_approve_and_the_request_is_refused_by_the_lifecycle(self):
        oscar = self.human('own2', 'oscar', FD.OWNER, FD.APPROVER)
        scopes = Grants({('zero_one', 'oscar', 'PRJ-001'): ('view', 'approve')})
        r = AB.present(oscar, scopes, self.m.clock, self.fid)
        self.assertEqual((r['status'], r['can_approve']), ('shown', False))
        res = self.ask(self.req(), who=oscar, scopes=scopes)
        self.assertEqual((res['status'], res['code']), ('refused', 'SELF_APPROVAL'))
        self.assertEqual(self.record()['status'], 'action_proposed')

    def test_the_screen_gives_no_token_for_a_finding_that_cannot_be_approved(self):
        m = breach()
        fid, _ = first(m)                                    # detected, no proposal
        r = AB.present(m.approver, self.scopes, m.clock, fid)
        self.assertEqual((r['status'], r['token'], r['can_approve'], r['proposal']), ('shown', None, False, None))


class TestMalformedRequestsFailClosed(Base):
    def valid(self):
        return self.req()

    def check_refused(self, bad, label=''):
        before, n_req = self.record(), len(self.stored_requests())
        res = self.ask(bad)
        self.assertEqual((res['status'], res['code']), ('refused', 'REQUEST_MALFORMED'), label)
        self.assertEqual(self.record(), before, label)
        self.assertEqual(len(self.stored_requests()), n_req, label)

    def test_a_request_that_is_not_a_dictionary_is_refused_without_an_error(self):
        for bad in (None, [], (), 'x', 5, 1.5, True, b'x', object(), set()):
            self.check_refused(bad, repr(bad))

    def test_every_field_is_needed_and_no_other_field_is_accepted(self):
        for k in AB.FIELDS:
            d = self.valid()
            del d[k]
            self.check_refused(d, 'missing ' + k)
        for extra in ('tenant_id', 'tenant', 'org_id', 'approver', 'user_id', 'roles', 'x'):
            d = self.valid()
            d[extra] = 'zero_one' if 'tenant' in extra or extra == 'org_id' else 'abby'
            self.check_refused(d, 'extra ' + extra)

    def test_a_version_must_be_a_whole_number_of_at_least_1(self):
        for bad in (True, False, 0, -1, 1.0, 1.5, '1', None, [], {}):
            self.check_refused(self.req(version=bad), repr(bad))

    def test_a_digest_and_a_proposal_reference_must_be_short_non_empty_texts(self):
        for k in ('digest', 'proposal'):
            for bad in ('', '   ', 5, None, ['a'], {'a': 1}, 'x' * 129):
                self.check_refused(self.req(**{k: bad}), f'{k} {bad!r}')

    def test_a_rationale_must_be_a_non_empty_text_of_reasonable_length(self):
        for bad in ('', '   ', 5, None, [], 'x' * (AB.MAX_RATIONALE + 1)):
            self.check_refused(self.req(rationale=bad), repr(bad)[:40])

    def test_ids_must_be_plain_identifiers(self):
        for k in ('request_id', 'finding_id'):
            for bad in ('', ' ', 'a b', 'a/b', '../x', 'é', 'a\nb', 'x' * 129, None, 5, ['a']):
                self.check_refused(self.req(**{k: bad}), f'{k} {bad!r}')

    def test_a_refused_request_is_audited_and_the_audit_never_holds_the_rationale(self):
        self.ask(self.req(version=True, rationale=SECRET))
        ev = self.boundary_events()
        self.assertEqual([(e.event_type, e.outcome) for e in ev], [('approval_request.refused', 'refused')])
        self.assertEqual(ev[0].detail['code'], 'REQUEST_MALFORMED')
        self.assertNotIn(SECRET, str(ev[0].__dict__))

    def test_hostile_values_inside_the_request_are_refused_not_raised(self):
        for bad in ({'a': {'b': {'c': {}}}}, [[[]]], 'x' * 100000):
            self.check_refused(self.req(rationale=bad), repr(bad)[:30])

    def test_a_rationale_that_hides_a_claim_about_another_tenant_is_refused_and_nothing_is_approved(self):
        res = self.ask(self.req(rationale='{"tenant_id": "zero_two"}'))
        self.assertEqual((res['status'], res['code']), ('refused', 'TENANT_MISMATCH'))
        self.assertEqual(self.record()['status'], 'action_proposed')
        self.assertEqual(self.record()['action']['approved_by'], None)


class TestWhoMayAsk(Base):
    def test_a_service_identity_cannot_approve_even_with_the_approver_role(self):
        svc = self.human('svc2', 'robot', FD.APPROVER, kind='service')
        scopes = Grants({('zero_one', 'robot', 'PRJ-001'): ('view', 'approve')})
        res = self.ask(self.req(), who=svc, scopes=scopes)
        self.assertEqual((res['status'], res['code']), ('refused', 'HUMAN_REQUIRED'))
        self.assertEqual(self.record()['status'], 'action_proposed')
        self.assertEqual(len(self.stored_requests()), 0)                 # refused at the boundary, before a request record is opened (the lifecycle would refuse the same code later, so the code alone does not show which one answered)
        self.assertEqual([e.outcome for e in self.boundary_events()], ['refused'])

    def test_an_expired_session_cannot_approve_and_nothing_is_stored(self):
        short = self.human('short', 'abby', FD.APPROVER, ttl=60)
        req = self.req()
        self.m.clock.advance(120)
        res = self.ask(req, who=short)
        self.assertEqual((res['status'], res['code']), ('refused', 'SESSION_EXPIRED'))
        self.assertEqual(self.record()['status'], 'action_proposed')
        self.assertEqual(len(self.stored_requests()), 0)

    def test_a_person_without_the_approver_role_is_refused_before_anything_else(self):
        rita = self.m.reviewer
        scopes = Grants({('zero_one', 'rita', 'PRJ-001'): ('view', 'approve')})
        res = self.ask(self.req(), who=rita, scopes=scopes)
        self.assertEqual((res['status'], res['code']), ('refused', 'ROLE_REQUIRED'))
        self.assertEqual(len(self.stored_requests()), 0)

    def test_an_approver_of_another_project_gets_the_same_answer_as_for_a_finding_that_does_not_exist(self):
        other = Grants({('zero_one', 'abby', 'PRJ-999'): ('view', 'approve')})
        res = self.ask(self.req(), scopes=other)
        ghost = self.ask(self.req(finding_id='FND-doesnotexist'))
        self.assertEqual((res['status'], res['code'], res['message']), (ghost['status'], ghost['code'], ghost['message']))
        self.assertEqual(res['code'], 'NOT_FOUND')
        self.assertNotIn('finding_status', res)
        self.assertEqual(self.record()['status'], 'action_proposed')
        self.assertEqual(len(self.stored_requests()), 0)

    def test_a_port_that_is_missing_raises_or_answers_loosely_means_refused(self):
        class Raises(AB.ProjectActionPort):
            def allows(self, ctx, scope, action):
                raise RuntimeError('boom')

        class Loose(AB.ProjectActionPort):
            def __init__(self, answer):
                self.answer = answer

            def allows(self, ctx, scope, action):
                return self.answer
        for port in (None, Raises(), Loose('yes'), Loose(1), Loose(None), Loose([True]), Loose('True'), Loose(0)):
            res = self.ask(self.req(), scopes=port)
            self.assertEqual((res['status'], res['code']), ('refused', 'NOT_FOUND'), repr(port))
            self.assertEqual(self.record()['status'], 'action_proposed')

    def test_view_permission_alone_does_not_allow_approval_but_does_show_the_screen_without_the_right_to_approve(self):
        view_only = Grants({('zero_one', 'abby', 'PRJ-001'): ('view',)})
        r = AB.present(self.m.approver, view_only, self.m.clock, self.fid)
        self.assertEqual((r['status'], r['can_approve']), ('shown', False))
        res = self.ask(self.req(), scopes=view_only)
        self.assertEqual((res['status'], res['code']), ('refused', 'NOT_FOUND'))

    def test_the_screen_hides_a_finding_from_a_person_who_may_not_view_it(self):
        none = Grants({})
        r = AB.present(self.m.approver, none, self.m.clock, self.fid)
        ghost = AB.present(self.m.approver, none, self.m.clock, 'FND-doesnotexist')
        self.assertEqual((r['status'], r['code'], r['message']), (ghost['status'], ghost['code'], ghost['message']))
        self.assertNotIn('token', r)

    def test_a_tenant_level_finding_needs_the_port_to_say_so_and_a_malformed_scope_is_never_allowed(self):
        rec = FD._load(self.m.svc, self.fid)
        f = FD.canon.deep_copy(rec.payload)
        f['signal']['scope'] = {'level': 'tenant'}
        FD._put(self.m.svc, rec, f)
        res = self.ask(self.req())
        self.assertEqual((res['status'], res['code']), ('refused', 'NOT_FOUND'), 'a project grant does not cover a tenant-level finding')
        tenant_grant = Grants({('zero_one', 'abby', '*tenant*'): ('view', 'approve')})
        res = self.ask(self.req(), scopes=tenant_grant)
        self.assertEqual((res['status'], res['code']), ('approved', 'OK'))

    def test_a_finding_whose_scope_is_damaged_cannot_be_approved_even_by_a_port_that_allows_everything(self):
        class Everything(AB.ProjectActionPort):
            def allows(self, ctx, scope, action):
                return True
        for bad in (None, {}, {'level': 'galaxy'}, {'level': 'project'}, {'level': 'project', 'project': ''}, {'level': 'project', 'project': 5}, 'project:PRJ-001'):
            self.setUp()
            rec = FD._load(self.m.svc, self.fid)
            f = FD.canon.deep_copy(rec.payload)
            f['signal']['scope'] = bad
            FD._put(self.m.svc, rec, f)
            res = self.ask(self.req(), scopes=Everything())
            self.assertEqual((res['status'], res['code']), ('refused', 'NOT_FOUND'), repr(bad))

    def test_another_tenant_cannot_reach_the_finding_even_with_a_port_that_allows_everything(self):
        class Everything(AB.ProjectActionPort):
            def allows(self, ctx, scope, action):
                return True
        two = self.m.w.who('apr2', 'zero_two', 'abby', (FD.APPROVER,), ttl=10 ** 8)
        res = self.ask(self.req(), who=two, scopes=Everything())
        self.assertEqual((res['status'], res['code']), ('refused', 'NOT_FOUND'))
        self.assertEqual(len(two.query(AB.REQUEST_KIND)), 0)
        self.assertEqual(self.record()['status'], 'action_proposed')
        r = AB.present(two, Everything(), self.m.clock, self.fid)
        self.assertEqual((r['status'], r['code']), ('refused', 'NOT_FOUND'))

    def test_the_port_is_asked_on_every_request_and_with_the_action(self):
        self.ask(self.req(rid='R-A'))
        self.ask(self.req(rid='R-A'))
        self.assertEqual(self.scopes.asked, [('abby', 'PRJ-001', 'approve')] * 2)


class TestOneAnswerPerRequest(Base):
    def test_the_same_request_sent_again_returns_the_first_answer_and_does_nothing_twice(self):
        req = self.req(rid='R-1')
        with mock.patch.object(FD, 'approve_action', wraps=FD.approve_action) as spy:
            first_ = self.ask(req)
            before = self.record()
            again = self.ask(dict(req))
        self.assertEqual(spy.call_count, 1, 'the lifecycle was asked once')
        self.assertEqual((first_['replayed'], again['replayed']), (False, True))
        self.assertEqual({k: v for k, v in again.items() if k != 'replayed'}, {k: v for k, v in first_.items() if k != 'replayed'})
        self.assertEqual(self.record(), before)
        self.assertEqual(len(self.approvals_in_history()), 1)
        self.assertEqual([e.event_type for e in self.boundary_events()], ['approval_request.accepted', 'approval_request.replayed'])

    def test_the_same_id_with_different_content_is_refused_and_the_first_answer_still_stands(self):
        req = self.req(rid='R-1')
        self.ask(req)
        for over in ({'rationale': 'something else'}, {'version': 2}, {'digest': 'other'}, {'proposal': 'other'}):
            before = self.record()
            res = self.ask(dict(req, **over))
            self.assertEqual((res['status'], res['code']), ('refused', 'REQUEST_ID_REUSED'), over)
            self.assertEqual(self.record(), before)
        again = self.ask(dict(req))
        self.assertEqual((again['status'], again['replayed']), ('approved', True))

    def test_another_person_cannot_use_a_request_id_and_never_sees_the_first_answer(self):
        req = self.req(rid='R-1')
        self.ask(req)
        bob = self.human('bob', 'bob', FD.APPROVER)
        scopes = Grants({('zero_one', 'bob', 'PRJ-001'): ('view', 'approve'), ('zero_one', 'abby', 'PRJ-001'): ('view', 'approve')})
        res = self.ask(dict(req), who=bob, scopes=scopes)
        self.assertEqual((res['status'], res['code']), ('refused', 'REQUEST_ID_REUSED'))
        self.assertNotIn('approved_by', res)

    def test_a_refusal_by_the_lifecycle_is_the_answer_to_that_request_id_too(self):
        shown = self.token()
        reproposed(self.m, self.fid, TEXT2)
        req = self.req(shown, rid='R-1')
        res = self.ask(req)
        self.assertEqual((res['status'], res['code'], res['replayed']), ('refused', 'PROPOSAL_CHANGED', False))
        again = self.ask(dict(req))
        self.assertEqual((again['status'], again['code'], again['replayed']), ('refused', 'PROPOSAL_CHANGED', True))
        fresh = self.ask(self.req(rid='R-2'))
        self.assertEqual((fresh['status'], fresh['replayed']), ('approved', False))

    def test_a_different_request_id_for_the_same_approval_is_refused_not_approved_twice(self):
        self.ask(self.req(rid='R-1'))
        res = self.ask(self.req(rid='R-2'))
        self.assertEqual((res['status'], res['code']), ('refused', 'TRANSITION_NOT_ALLOWED'))
        self.assertEqual(len(self.approvals_in_history()), 1)

    def test_a_replay_is_not_served_to_someone_whose_permission_has_been_taken_away(self):
        req = self.req(rid='R-1')
        self.ask(req)
        res = self.ask(dict(req), scopes=Grants({}))
        self.assertEqual((res['status'], res['code']), ('refused', 'NOT_FOUND'))
        self.assertNotIn('replayed', res)

    def test_request_ids_belong_to_the_tenant_that_used_them(self):
        req = self.req(rid='R-1')
        self.ask(req)

        class Everything(AB.ProjectActionPort):
            def allows(self, ctx, scope, action):
                return True
        two = self.m.w.who('apr2', 'zero_two', 'abby', (FD.APPROVER,), ttl=10 ** 8)
        res = self.ask(dict(req), who=two, scopes=Everything())
        self.assertEqual(res['code'], 'NOT_FOUND', 'tenant two sees neither the finding nor the request of tenant one')
        self.assertEqual(len(self.stored_requests()), 1)


class TestARequestThatStoppedHalfWay(Base):
    def test_a_concurrent_change_does_not_close_the_request_and_the_same_request_can_be_sent_again(self):
        flaky = Flaky(self.m.approver, once(FD.ConflictError('raced'), lambda kind, p: kind == FD.KIND))
        req = self.req(rid='R-1')
        res = self.ask(req, who=flaky)
        self.assertEqual((res['status'], res['code'], res.get('retry')), ('refused', 'CONCURRENT_CHANGE', True))
        self.assertEqual(self.record()['status'], 'action_proposed')
        again = self.ask(dict(req))
        self.assertEqual((again['status'], again['code'], again['replayed']), ('approved', 'OK', False))

    def test_a_crash_before_the_approval_leaves_the_request_open_and_the_retry_approves_once(self):
        flaky = Flaky(self.m.approver, once(RuntimeError('crash'), lambda kind, p: kind == FD.KIND))
        req = self.req(rid='R-1')
        with self.assertRaises(RuntimeError):
            self.ask(req, who=flaky)
        self.assertEqual(self.record()['status'], 'action_proposed')
        again = self.ask(dict(req))
        self.assertEqual((again['status'], again['recovered']), ('approved', False))
        self.assertEqual(len(self.approvals_in_history()), 1)

    def test_a_crash_after_the_approval_is_recognised_from_the_findings_own_history_and_not_repeated(self):
        flaky = Flaky(self.m.approver, once(RuntimeError('crash'), lambda kind, p: kind == AB.REQUEST_KIND and p.get('state') == 'done'))
        req = self.req(rid='R-1')
        with self.assertRaises(RuntimeError):
            self.ask(req, who=flaky)
        self.assertEqual(self.record()['status'], 'action_approved')
        self.assertEqual(self.stored_requests()[0].payload['state'], 'pending')
        before = self.record()
        again = self.ask(dict(req))
        self.assertEqual((again['status'], again['code'], again['recovered'], again['replayed']), ('approved', 'OK', True, False))
        self.assertEqual(self.record(), before, 'nothing is approved a second time')
        self.assertEqual(len(self.approvals_in_history()), 1)
        self.assertEqual(self.stored_requests()[0].payload['state'], 'done')
        third = self.ask(dict(req))
        self.assertEqual(third['replayed'], True)

    def test_a_pending_request_is_not_taken_over_by_different_content(self):
        flaky = Flaky(self.m.approver, once(RuntimeError('crash'), lambda kind, p: kind == FD.KIND))
        req = self.req(rid='R-1')
        with self.assertRaises(RuntimeError):
            self.ask(req, who=flaky)
        res = self.ask(dict(req, rationale='something else'))
        self.assertEqual((res['status'], res['code']), ('refused', 'REQUEST_ID_REUSED'))


class TestEvidenceChangesBetweenProposalApprovalAndExecution(Base):
    def test_evidence_that_changes_after_the_screen_was_shown_makes_the_approval_stale(self):
        shown = AB.present(self.m.approver, self.scopes, self.m.clock, self.fid)['token']
        worsen(self.m)
        self.assertGreater(self.record()['version'], shown['version'])
        res = self.ask(self.req(shown))
        self.assertEqual((res['status'], res['code']), ('refused', 'STALE_APPROVAL'))
        self.assertNotEqual(self.record()['status'], 'action_approved')

    def test_a_proposal_replaced_after_the_screen_was_shown_cannot_be_approved_with_the_old_token(self):
        shown = AB.present(self.m.approver, self.scopes, self.m.clock, self.fid)['token']
        reproposed(self.m, self.fid, TEXT2)
        res = self.ask(self.req(shown))
        self.assertEqual((res['status'], res['code']), ('refused', 'PROPOSAL_CHANGED'))
        f = self.record()
        self.assertEqual((f['status'], f['action']['text'], f['action']['approved_by']), ('action_proposed', TEXT2, None))

    def test_the_executor_check_is_true_only_for_exactly_what_was_approved(self):
        shown = self.token()
        self.ask(self.req(shown))
        ok = AB.check_for_execution(self.m.approver, self.scopes, self.m.clock, self.fid, shown['version'], shown['digest'], shown['proposal'])
        self.assertEqual(ok, {'valid': True, 'code': 'OK'})
        for args in ((shown['version'] + 1, shown['digest'], shown['proposal']), (shown['version'], 'other', shown['proposal']), (shown['version'], shown['digest'], 'other')):
            self.assertEqual(AB.check_for_execution(self.m.approver, self.scopes, self.m.clock, self.fid, *args), {'valid': False, 'code': 'NOT_IN_FORCE'})

    def test_after_the_evidence_changes_the_approval_no_longer_authorises_execution(self):
        shown = self.token()
        self.ask(self.req(shown))
        worsen(self.m)
        self.assertEqual(self.record()['action']['approval_state'], 'invalidated')
        res = AB.check_for_execution(self.m.approver, self.scopes, self.m.clock, self.fid, shown['version'], shown['digest'], shown['proposal'])
        self.assertEqual(res, {'valid': False, 'code': 'NOT_IN_FORCE'})

    def test_an_unapproved_proposal_does_not_authorise_execution(self):
        shown = self.token()
        res = AB.check_for_execution(self.m.approver, self.scopes, self.m.clock, self.fid, shown['version'], shown['digest'], shown['proposal'])
        self.assertEqual(res, {'valid': False, 'code': 'NOT_IN_FORCE'})

    def test_the_executor_check_fails_closed_for_malformed_names_other_projects_and_other_tenants(self):
        shown = self.token()
        self.ask(self.req(shown))
        for args in ((None, shown['version'], shown['digest'], shown['proposal']), (self.fid, True, shown['digest'], shown['proposal']), (self.fid, shown['version'], '', shown['proposal']),
                     (self.fid, shown['version'], shown['digest'], None), ('a b', shown['version'], shown['digest'], shown['proposal'])):
            self.assertEqual(AB.check_for_execution(self.m.approver, self.scopes, self.m.clock, *args), {'valid': False, 'code': 'NOT_ALLOWED'}, repr(args))
        other = Grants({('zero_one', 'abby', 'PRJ-999'): ('view', 'approve')})
        good = (self.fid, shown['version'], shown['digest'], shown['proposal'])
        self.assertEqual(AB.check_for_execution(self.m.approver, other, self.m.clock, *good), {'valid': False, 'code': 'NOT_FOUND'})
        self.assertEqual(AB.check_for_execution(self.m.approver, None, self.m.clock, *good), {'valid': False, 'code': 'NOT_FOUND'})
        two = self.m.w.who('apr2', 'zero_two', 'abby', (FD.APPROVER,), ttl=10 ** 8)

        class Everything(AB.ProjectActionPort):
            def allows(self, ctx, scope, action):
                return True
        self.assertEqual(AB.check_for_execution(two, Everything(), self.m.clock, *good), {'valid': False, 'code': 'NOT_FOUND'})


class TestEveryOutcomeIsAudited(Base):
    def test_each_request_adds_exactly_one_boundary_event_and_none_holds_the_rationale(self):
        steps = [self.req(rid='R-1', version=True, rationale=SECRET),                  # malformed
                 self.req(rid='R-2', rationale=SECRET),                                # approved
                 self.req(rid='R-2', rationale=SECRET),                                # replay
                 self.req(rid='R-2', rationale='x' + SECRET),                          # id reused
                 self.req(rid='R-3', rationale=SECRET)]                                # lifecycle refusal (already approved)
        seen = []
        for r in steps:
            n = len(self.boundary_events())
            self.ask(r)
            seen.append(len(self.boundary_events()) - n)
        self.assertEqual(seen, [1, 1, 1, 1, 1])
        self.assertEqual([e.event_type for e in self.boundary_events()],
                         ['approval_request.refused', 'approval_request.accepted', 'approval_request.replayed', 'approval_request.refused', 'approval_request.refused'])
        for e in self.boundary_events():
            self.assertNotIn(SECRET, str(e.__dict__))
        self.assertTrue(all(e.detail.get('code') for e in self.boundary_events()))

    def test_viewing_the_screen_is_audited_and_so_is_a_refused_view(self):
        AB.present(self.m.approver, self.scopes, self.m.clock, self.fid)
        AB.present(self.m.approver, Grants({}), self.m.clock, self.fid)
        self.assertEqual([(e.event_type, e.outcome) for e in self.boundary_events()], [('approval_request.viewed', 'ok'), ('approval_request.refused', 'refused')])

    def test_the_audit_chain_still_verifies(self):
        self.ask(self.req(rid='R-1'))
        self.ask(self.req(rid='R-1'))
        self.ask(self.req(rid='R-2'))
        self.assertTrue(self.m.w.audit.verify(self.m.s.ctx))


class TestRecoveryAndReplayAreHonest(Base):
    """Added after review of the first version of the boundary: a request is credited only with an approval written after it was opened, and a replay is the first answer, not the finding's present state."""
    def test_an_approval_made_by_another_request_is_never_recovered_as_this_requests(self):
        first = self.req(rid='R-A')
        self.assertEqual(self.ask(first)['status'], 'approved')
        flaky = Flaky(self.m.approver, once(RuntimeError('crash'), lambda kind, p: kind == AB.REQUEST_KIND and p.get('state') == 'done'))
        second = dict(first, request_id='R-B')                           # same person, same version, digest and proposal; a different request id
        with self.assertRaises(RuntimeError):
            self.ask(second, who=flaky)                                  # the lifecycle refused it (already approved); the crash left R-B pending
        self.assertEqual({r.payload['request_id']: r.payload['state'] for r in self.stored_requests()}, {'R-A': 'done', 'R-B': 'pending'})
        before = self.record()
        again = self.ask(dict(second))
        self.assertEqual(again['status'], 'refused', again)
        self.assertFalse(again.get('recovered'), again)
        self.assertEqual(self.record(), before)
        self.assertEqual(len(self.approvals_in_history()), 1)

    def test_a_pending_record_without_a_usable_history_mark_is_never_recovered_from(self):
        flaky = Flaky(self.m.approver, once(RuntimeError('crash'), lambda kind, p: kind == AB.REQUEST_KIND and p.get('state') == 'done'))
        req = self.req(rid='R-1')
        with self.assertRaises(RuntimeError):
            self.ask(req, who=flaky)
        rec = self.stored_requests()[0]
        for bad in (None, -1, True, '3'):
            self.m.s.put(AB.REQUEST_KIND, rec.key, dict(rec.payload, history_len=bad), expected_revision=self.stored_requests()[0].revision)
            res = self.ask(dict(req))
            self.assertEqual(res['status'], 'refused', (bad, res))
            self.assertFalse(res.get('recovered'), (bad, res))
        self.assertEqual(len(self.approvals_in_history()), 1)

    def test_a_replay_is_the_first_answer_and_does_not_say_the_approval_is_still_in_force(self):
        shown = self.token()
        req = self.req(shown, rid='R-1')
        first = self.ask(req)
        worsen(self.m)                                                   # the evidence changes: the approval ends
        self.assertEqual(self.record()['action']['approval_state'], 'invalidated')
        before = self.record()
        again = self.ask(dict(req))
        self.assertEqual((again['status'], again['replayed'], again['finding_status']), ('approved', True, first['finding_status']))
        self.assertEqual(self.record(), before, 'a replay changes nothing')
        self.assertEqual(AB.check_for_execution(self.m.approver, self.scopes, self.m.clock, self.fid, shown['version'], shown['digest'], shown['proposal']), {'valid': False, 'code': 'NOT_IN_FORCE'})

    def test_the_lifecycle_audits_the_approval_itself_whatever_the_boundary_does(self):
        self.ask(self.req(rid='R-1'))
        kinds = [e.event_type for e in self.m.w.audit.read(self.m.s.ctx)]
        self.assertIn('finding.transition', kinds)
        self.assertEqual(kinds.count('approval_request.accepted'), 1)


class Ticking:
    """A clock that moves on by a second each time it is read, so that a time copied from an earlier reading differs from a time read now."""
    def __init__(self, base):
        import datetime
        self._d, self._t, self.n = datetime, datetime.datetime.strptime(base.now(), '%Y-%m-%dT%H:%M:%SZ'), 0

    def now(self):
        self.n += 1
        return (self._t + self._d.timedelta(seconds=self.n)).strftime('%Y-%m-%dT%H:%M:%SZ')


class TestEdgesTheFirstMutationRunFound(Base):
    """Cases the builder's first mutation run of this module left unprotected (17 of 89 mutants survived); each test below was added for one or more of them."""
    def crash_after_approval(self, rid='R-1'):
        flaky = Flaky(self.m.approver, once(RuntimeError('crash'), lambda kind, p: kind == AB.REQUEST_KIND and p.get('state') == 'done'))
        req = self.req(rid=rid)
        with self.assertRaises(RuntimeError):
            self.ask(req, who=flaky)
        return req

    def test_a_session_that_ends_this_very_second_is_not_live(self):
        who = self.human('short', 'abby', FD.APPROVER, ttl=100)
        self.m.clock.advance(99)
        self.assertTrue(AB._session_live(who.ctx, self.m.clock))
        self.m.clock.advance(1)
        res = self.ask(self.req(), who=who)
        self.assertEqual((res['status'], res['code']), ('refused', 'SESSION_EXPIRED'))
        self.assertFalse(AB._session_live(who.ctx, self.m.clock))

    def test_the_liveness_check_reads_only_a_well_formed_expiry(self):
        from types import SimpleNamespace as NS
        for bad in (None, 5, 'tomorrow', '2999-01-01 00:00:00', '2999-01-01T00:00:00', '2999-01-01T00:00:00Z '):
            self.assertFalse(AB._session_live(NS(expires_at=bad), self.m.clock), bad)
        self.assertTrue(AB._session_live(NS(expires_at='2999-01-01T00:00:00Z'), self.m.clock))
        self.assertFalse(AB._session_live(NS(expires_at='2000-01-01T00:00:00Z'), self.m.clock))

    def test_a_refusal_names_the_ids_it_was_given_only_when_they_are_plain(self):
        res = self.ask(self.req(rid='REQ-OK', rationale=''))
        self.assertEqual((res['code'], res['request_id'], res['finding_id']), ('REQUEST_MALFORMED', 'REQ-OK', self.fid))
        res = self.ask(self.req(rid='not plain!', rationale=''))
        self.assertEqual((res['code'], res['request_id'], res['finding_id']), ('REQUEST_MALFORMED', None, self.fid))
        res = self.ask(self.req(rid='REQ-OK2', finding_id='not plain!'))
        self.assertEqual((res['code'], res['request_id'], res['finding_id']), ('REQUEST_MALFORMED', 'REQ-OK2', None))

    def test_the_limits_of_the_request_are_exact(self):
        ok = self.ask(self.req(rid='R-A', rationale='x' * AB.MAX_RATIONALE))
        self.assertEqual(ok['status'], 'approved', ok)
        too_long = self.ask(self.req(rid='R-B', rationale='x' * (AB.MAX_RATIONALE + 1)))
        self.assertEqual(too_long['code'], 'REQUEST_MALFORMED')
        for k in ('digest', 'proposal'):
            fits = self.ask(self.req(rid='R-C' + k, **{k: 'd' * 128}))
            self.assertNotEqual(fits['code'], 'REQUEST_MALFORMED', (k, fits))
            over = self.ask(self.req(rid='R-D' + k, **{k: 'd' * 129}))
            self.assertEqual(over['code'], 'REQUEST_MALFORMED', (k, over))

    def test_a_request_opened_when_the_history_was_empty_still_recognises_its_own_approval(self):
        req = self.crash_after_approval()
        rec = self.stored_requests()[0]
        self.m.s.put(AB.REQUEST_KIND, rec.key, dict(rec.payload, history_len=0), expected_revision=rec.revision)
        again = self.ask(dict(req))
        self.assertEqual((again['status'], again['recovered']), ('approved', True))

    def test_the_stored_request_keeps_when_it_was_opened_and_how_long_the_history_was(self):
        n = len(self.record()['history'])
        t0 = self.m.clock.now()
        req = self.crash_after_approval()
        pending = self.stored_requests()[0].payload
        self.assertEqual((pending['at'], pending['history_len'], pending['state']), (t0, n, 'pending'))
        self.m.clock.advance(500)
        self.ask(dict(req))
        done = self.stored_requests()[0].payload
        self.assertEqual((done['state'], done['at'], done['history_len']), ('done', t0, n))

    def test_a_record_that_says_done_but_holds_no_answer_is_not_a_replay(self):
        req = self.req(rid='R-1')
        h = AB._hash(self.m.approver.ctx, req)
        key = AB.canon.digest({'request_id': 'R-1'})[:40]
        self.m.s.put(AB.REQUEST_KIND, key, {'request_id': 'R-1', 'request_hash': h, 'finding_id': self.fid, 'by': 'abby', 'at': self.m.clock.now(), 'state': 'done', 'history_len': 0, 'result': None}, expected_revision=0)
        res = self.ask(dict(req))
        self.assertEqual((res['status'], res['replayed']), ('approved', False), res)
        self.assertEqual(len(self.approvals_in_history()), 1)

    def test_a_record_that_is_still_pending_is_never_served_as_an_answer(self):
        req = self.req(rid='R-1')
        h = AB._hash(self.m.approver.ctx, req)
        key = AB.canon.digest({'request_id': 'R-1'})[:40]
        fake = {'status': 'approved', 'code': 'OK', 'message': 'forged', 'request_id': 'R-1', 'finding_id': self.fid}
        self.m.s.put(AB.REQUEST_KIND, key, {'request_id': 'R-1', 'request_hash': h, 'finding_id': self.fid, 'by': 'abby', 'at': self.m.clock.now(), 'state': 'pending', 'history_len': 99, 'result': fake}, expected_revision=0)
        res = self.ask(dict(req))
        self.assertEqual((res['status'], res['replayed']), ('approved', False), res)
        self.assertNotEqual(res.get('message'), 'forged')

    def test_the_approval_time_in_the_answer_is_the_time_in_the_findings_history(self):
        tick = Ticking(self.m.clock)
        res = AB.request_approval(self.m.approver, self.scopes, tick, self.req())
        self.assertEqual(res['status'], 'approved', res)
        ev = self.approvals_in_history()[0]
        self.assertEqual((res['approved_at'], res['approved_by']), (ev['at'], ev['actor']))

    def test_an_older_look_alike_event_in_a_damaged_history_is_not_this_requests_approval(self):
        tok = self.token()
        rec = self.m.s.get(FD.KIND, self.fid)
        f = AB.canon.deep_copy(rec.payload)
        f['history'].append({'seq': len(f['history']) + 1, 'at': '2020-01-01T00:00:00Z', 'actor': 'abby', 'actor_kind': 'human', 'event': 'status_change', 'from': 'action_proposed', 'to': 'action_approved',
                             'detail': {'approved_version': tok['version'], 'approved_digest': tok['digest'], 'proposal_ref': tok['proposal']}})
        self.m.s.put(FD.KIND, self.fid, f, expected_revision=rec.revision)
        res = self.ask(self.req(tok))
        self.assertEqual(res['status'], 'approved', res)
        self.assertNotEqual(res['approved_at'], '2020-01-01T00:00:00Z')
        self.assertEqual(res['approved_at'], self.approvals_in_history()[-1]['at'])

    def test_what_counts_as_this_persons_approval_of_this_token_is_exact(self):
        tok = {'version': 3, 'digest': 'dg', 'proposal': 'pr'}
        good = {'event': 'status_change', 'to': 'action_approved', 'actor': 'abby', 'detail': {'approved_version': 3, 'approved_digest': 'dg', 'proposal_ref': 'pr'}}
        f = lambda *evs: {'history': list(evs)}
        self.assertIs(AB._approval_event(f(good), 'abby', tok, 0), good)
        self.assertIsNone(AB._approval_event(f(good), 'abby', tok, 1))
        variants = [dict(good, event='other'), dict(good, to='in_progress'), dict(good, actor='bruno'), dict(good, detail=dict(good['detail'], approved_version=4)),
                    dict(good, detail=dict(good['detail'], approved_digest='x')), dict(good, detail=dict(good['detail'], proposal_ref='x')), dict(good, detail=None), {}]
        for v in variants:
            self.assertIsNone(AB._approval_event(f(v), 'abby', tok, 0), v)
        for bad in (None, True, -1, '0', 1.0):
            self.assertIsNone(AB._approval_event(f(good), 'abby', tok, bad), bad)

    def test_viewing_needs_a_person_with_a_live_session_and_a_plain_finding_id(self):
        svc = self.human('svc1', 'svc-detect', FD.APPROVER, kind='service')
        r = AB.present(svc, self.scopes, self.m.clock, self.fid)
        self.assertEqual((r['status'], r['code']), ('refused', 'NOT_ALLOWED'))
        gone = self.human('gone', 'abby', FD.APPROVER, ttl=10)
        self.m.clock.advance(10)
        r = AB.present(gone, self.scopes, self.m.clock, self.fid)
        self.assertEqual((r['status'], r['code']), ('refused', 'NOT_ALLOWED'))
        for bad in (5, None, ['x'], '', 'a b', 'x' * 129):
            r = AB.present(self.m.approver, self.scopes, self.m.clock, bad)
            self.assertEqual((r['status'], r['code']), ('refused', 'NOT_FOUND'), bad)

    def test_when_another_copy_noted_its_answer_first_that_answer_is_the_one_returned(self):
        marker = {'status': 'approved', 'code': 'OK', 'message': "the other copy's answer", 'request_id': 'R-1', 'finding_id': self.fid}
        box = {'armed': True}
        inner = self.m.approver

        def other_copy_first(kind, payload):
            if kind == AB.REQUEST_KIND and payload.get('state') == 'done' and box['armed']:
                box['armed'] = False
                rec = inner.get(AB.REQUEST_KIND, AB.canon.digest({'request_id': 'R-1'})[:40])
                inner.put(AB.REQUEST_KIND, rec.key, dict(rec.payload, state='done', result=marker), expected_revision=rec.revision)
                raise FD.ConflictError('the other copy was first')
        res = self.ask(self.req(rid='R-1'), who=Flaky(inner, other_copy_first))
        self.assertEqual((res['message'], res['replayed']), ("the other copy's answer", True))
        self.assertEqual(self.stored_requests()[0].payload['result'], marker)
        self.assertEqual(len(self.approvals_in_history()), 1)
        self.assertIn('approval_request.replayed', [e.event_type for e in self.boundary_events()])

    def test_a_conflict_with_something_that_is_not_the_same_requests_finished_answer_changes_nothing_for_the_caller(self):
        marker = {'status': 'approved', 'code': 'OK', 'message': 'not this request\'s answer', 'request_id': 'R-1', 'finding_id': self.fid}
        for label, change in (('still pending', dict(state='pending', result=marker)), ('another request\'s hash', dict(state='done', result=marker, request_hash='0' * 40)),
                              ('done without a usable answer', dict(state='done', result=None)), ('done with an answer that is not a dictionary', dict(state='done', result='x'))):
            with self.subTest(label):
                m = breach()
                fid, _ = first(m)
                proposed(m, fid, TEXT1)
                tok = FD.approval_token(FD.get(m.svc, fid))
                req = {'request_id': 'R-1', 'finding_id': fid, 'version': tok['version'], 'digest': tok['digest'], 'proposal': tok['proposal'], 'rationale': 'ok'}
                box = {'armed': True}
                inner = m.approver

                def hook(kind, payload, inner=inner, change=change, box=box):
                    if kind == AB.REQUEST_KIND and payload.get('state') == 'done' and box['armed']:
                        box['armed'] = False
                        rec = inner.get(AB.REQUEST_KIND, AB.canon.digest({'request_id': 'R-1'})[:40])
                        inner.put(AB.REQUEST_KIND, rec.key, dict(rec.payload, **change), expected_revision=rec.revision)
                        raise FD.ConflictError('raced')
                res = AB.request_approval(Flaky(inner, hook), self.scopes, m.clock, req)
                self.assertEqual((res['status'], res['replayed']), ('approved', False), (label, res))
                self.assertNotEqual(res.get('message'), marker['message'])

    def test_a_revoked_session_approves_nothing_and_stores_nothing(self):
        who = self.human('revoked-1', 'abby', FD.APPROVER)
        self.m.w.provider._contract_revoke('revoked-1')
        before = self.record()
        res = self.ask(self.req(), who=who)
        self.assertEqual((res['status'], res['code']), ('refused', 'NOT_FOUND'))
        shown = AB.present(who, self.scopes, self.m.clock, self.fid)
        self.assertEqual((shown['status'], shown['code']), ('refused', 'NOT_FOUND'))
        self.assertEqual(self.record(), before)
        self.assertEqual(len(self.stored_requests()), 0)
        self.assertEqual(AB.check_for_execution(who, self.scopes, self.m.clock, self.fid, 1, 'a', 'b')['valid'], False)

    def test_the_base_port_answers_no_and_the_boundary_treats_it_as_a_refusal(self):
        port = AB.ProjectActionPort()
        with self.assertRaises(NotImplementedError):
            port.allows(self.m.approver.ctx, {'level': 'tenant'}, 'view')
        res = self.ask(self.req(), scopes=port)
        self.assertEqual((res['status'], res['code']), ('refused', 'NOT_FOUND'))
        self.assertEqual(self.record()['status'], 'action_proposed')


class TestNothingElseMoved(Base):
    def test_the_lifecycle_table_and_the_entry_point_are_as_in_m6_5(self):
        self.assertEqual((len(FD.TRANSITIONS), len(FD.STATUSES)), (14, 10))
        tok = self.token()
        g = FD.approve_action(self.m.approver, self.m.clock, self.fid, tok['version'], tok['digest'], 'ok', approving_proposal=tok['proposal'])
        self.assertEqual(g['status'], 'action_approved')

    def test_the_boundary_adds_no_status_and_changes_no_finding_field(self):
        before = set(self.record())
        self.ask(self.req())
        self.assertEqual(set(self.record()), before)


if __name__ == '__main__':
    unittest.main()
