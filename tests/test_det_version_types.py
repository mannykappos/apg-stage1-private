"""Fail-closed validation of stored versions and digests (M6.3 correction, finding F-55).  The independent audit of M6.2 found that `proposal_current` compared the stored proposal version with the
finding version using Python equality, so a stored `True` or `1.0` counted as version 1 and `approve_action` accepted the proposal.  A stored or named version is a whole number of at least 1 and
not a boolean; a digest is a non-empty text; anything else is never current, never approvable, and never matches.  The approval token validator already refused such values; the stored side and the
optional arguments of `transition` did not.  Written before the correction.  The corrupt records are made by writing the malformed value into the stored finding, as the audit did, to simulate
malformed, legacy or damaged persisted state; the lifecycle itself never writes them."""
import unittest
from . import _path                                         # noqa: F401
from apg import canon
from .test_det_findings import breach, first, person
from .test_det_approval_binding import worsen
from .test_det_proposal_binding import proposed, reproposed
from apg.det import findings as FD
from .helpers_det import approve_filled


def damage(m, fid, action=None, version=None, digest=None):
    """Write a malformed value into the stored finding, as damaged or legacy persisted state would."""
    rec = FD._load(m.svc, fid)
    f = canon.deep_copy(rec.payload)
    if action:
        f['action'].update(action)
    if version is not None:
        f['version'] = version
    if digest is not None:
        f['signal']['state_digest'] = digest
    FD._put(m.svc, rec, f)
    return f


class Base(unittest.TestCase):
    def setUp(self):
        self.m = breach()
        self.fid, _ = first(self.m)

    def token_of(self):
        return FD.approval_token(FD.get(self.m.svc, self.fid))

    def refused_by_entry_point(self, code, version, digest):
        before = FD.get(self.m.svc, self.fid)
        n = len(self.m.w.audit.read(self.m.s.ctx))
        with self.assertRaises(FD.LifecycleError) as c:
            FD.approve_action(self.m.approver, self.m.clock, self.fid, version, digest, 'ok', approving_proposal=FD.proposal_ref(before) or 'r' * 24)
        self.assertEqual(c.exception.code, code)
        self.assertEqual(FD.get(self.m.svc, self.fid), before, 'a refused approval changes nothing in the record')
        self.assertGreater(len(self.m.w.audit.read(self.m.s.ctx)), n, 'the refusal is audited')

    def refused_by_transition(self, code, **kw):
        before = FD.get(self.m.svc, self.fid)
        kw.setdefault('approving_proposal', FD.proposal_ref(before) or 'r' * 24)       # M6.5: transition refuses an approval that names no proposal reference; a damaged record gives none, so a placeholder is named
        with self.assertRaises(FD.LifecycleError) as c:
            approve_filled(self.m.approver, self.m.clock, self.fid, rationale='ok', **kw)
        self.assertEqual(c.exception.code, code)
        self.assertEqual(FD.get(self.m.svc, self.fid), before)


class TestTheAuditReproduction(Base):
    def test_a_stored_proposal_version_of_true_is_not_current_and_the_audit_path_refuses_it(self):
        proposed(self.m, self.fid)
        t = self.token_of()
        damage(self.m, self.fid, action={'proposed_version': True})
        f = FD.get(self.m.svc, self.fid)
        self.assertIs(FD.proposal_current(f), False)
        self.refused_by_entry_point('STALE_PROPOSAL', t['version'], t['digest'])
        self.assertEqual(FD.get(self.m.svc, self.fid)['status'], 'action_proposed')

    def test_the_store_itself_refuses_a_float_so_1_point_0_can_only_reach_the_function_directly_and_is_refused_there(self):
        proposed(self.m, self.fid)
        with self.assertRaises(Exception) as c:
            damage(self.m, self.fid, action={'proposed_version': 1.0})
        self.assertEqual(type(c.exception).__name__, 'PayloadInvalid')
        f = FD.get(self.m.svc, self.fid)
        self.assertIs(type(f['action']['proposed_version']), int)
        direct = dict(f, action=dict(f['action'], proposed_version=1.0))
        self.assertIs(FD.proposal_current(direct), False)
        self.assertEqual(FD.approvable(direct)[0], False)

    def test_the_same_through_the_lower_level_transition_with_and_without_a_version_named(self):
        proposed(self.m, self.fid)
        damage(self.m, self.fid, action={'proposed_version': True})
        self.refused_by_transition('STALE_PROPOSAL')
        self.refused_by_transition('STALE_PROPOSAL', approving_version=1)
        self.refused_by_transition('STALE_PROPOSAL', approving_version=1, approving_digest=FD.get(self.m.svc, self.fid)['signal']['state_digest'])

    def test_the_refusal_reason_says_the_version_is_not_valid_and_names_the_finding_version(self):
        proposed(self.m, self.fid)
        damage(self.m, self.fid, action={'proposed_version': True})
        ok, why = FD.approvable(FD.get(self.m.svc, self.fid))
        self.assertFalse(ok)
        self.assertIn('not a valid version number', why)
        self.assertIn('version 1', why)


class TestProposalCurrentIsStrictAboutTypes(unittest.TestCase):
    def finding(self, pv, fv=1, pd='d1', fd='d1', **extra):
        return {'version': fv, 'signal': {'state_digest': fd}, 'action': dict({'proposed_version': pv, 'proposed_digest': pd}, **extra)}

    def test_a_normal_integer_version_and_digest_is_current(self):
        self.assertIs(FD.proposal_current(self.finding(1)), True)
        self.assertIs(FD.proposal_current(self.finding(7, 7)), True)

    def test_a_malformed_stored_proposal_version_is_never_current_even_where_python_equality_holds(self):
        for bad in (True, 1.0, 1 + 0j):
            self.assertIs(FD.proposal_current(self.finding(bad, 1)), False, repr(bad))
        self.assertIs(FD.proposal_current(self.finding(False, 0)), False)
        self.assertIs(FD.proposal_current(self.finding(0, 0)), False, 'version 0 is not a version')
        self.assertIs(FD.proposal_current(self.finding(-1, -1)), False)
        self.assertIs(FD.proposal_current(self.finding(2.0, 2)), False)

    def test_missing_text_and_container_versions_are_never_current(self):
        for bad in (None, '1', '', [1], (1,), {'v': 1}):
            self.assertIs(FD.proposal_current(self.finding(bad, 1)), False, repr(bad))

    def test_a_malformed_finding_version_is_never_current(self):
        for bad in (True, 1.0, 0, -1, None, '1'):
            self.assertIs(FD.proposal_current(self.finding(1, bad)), False, repr(bad))

    def test_a_malformed_or_empty_digest_is_never_current(self):
        for bad in (None, '', '   ', 5, ['d1'], b'd1'):
            self.assertIs(FD.proposal_current(self.finding(1, 1, pd=bad, fd=bad)), False, repr(bad))
        self.assertIs(FD.proposal_current(self.finding(1, 1, pd='d1', fd='d2')), False)
        self.assertIs(FD.proposal_current(self.finding(1, 1, pd='D1', fd='d1')), False, 'digests are compared exactly')

    def test_a_proposal_explicitly_marked_stale_is_not_current_even_if_version_and_digest_match(self):
        self.assertIs(FD.proposal_current(self.finding(1, proposal_state='stale')), False)
        self.assertIs(FD.proposal_current(self.finding(1, proposal_state='current')), True)
        self.assertIs(FD.proposal_current(self.finding(1)), True, 'a record without a proposal_state (made in M6.1) is judged by version and digest')

    def test_a_non_mapping_action_is_never_current(self):
        for bad in (None, [], 'x', 5):
            self.assertIs(FD.proposal_current({'version': 1, 'signal': {'state_digest': 'd1'}, 'action': bad}), False, repr(bad))

    def test_the_result_is_always_a_real_boolean(self):
        for pv in (1, True, 1.0, None):
            self.assertIn(FD.proposal_current(self.finding(pv)), (True, False))
            self.assertIsInstance(FD.proposal_current(self.finding(pv)), bool)


class TestApprovalCurrentIsStrictAboutTypes(unittest.TestCase):
    def finding(self, av, fv=1, ad='d1', pv=1):
        good = {'version': 1, 'signal': {'state_digest': 'd1'}, 'action': {'text': 'x', 'proposed_by': 'p', 'proposed_at': 't', 'proposed_version': 1, 'proposed_digest': 'd1'}}
        return {'version': fv, 'signal': {'state_digest': 'd1'}, 'action': {'approved_by': 'abby', 'approval_state': 'current', 'approved_version': av, 'approved_digest': ad, 'proposed_version': pv, 'proposed_digest': 'd1',
                                                                             'text': 'x', 'proposed_by': 'p', 'proposed_at': 't', 'approved_proposal': FD.proposal_ref(good)}}

    def test_a_normal_approval_is_current(self):
        self.assertIs(FD.approval_current(self.finding(1)), True)

    def test_a_malformed_approved_version_is_never_current(self):
        for bad in (True, 1.0, 0, None, '1'):
            self.assertIs(FD.approval_current(self.finding(bad)), False, repr(bad))

    def test_a_malformed_approved_digest_is_never_current(self):
        for bad in (None, '', 5):
            self.assertIs(FD.approval_current(self.finding(1, ad=bad)), False, repr(bad))

    def test_a_malformed_proposal_version_behind_an_approval_means_the_approval_is_not_current(self):
        for bad in (True, 1.0):
            self.assertIs(FD.approval_current(self.finding(1, pv=bad)), False, repr(bad))

    def test_a_malformed_finding_version_means_no_approval_is_current(self):
        self.assertIs(FD.approval_current(self.finding(True, fv=True)), False)
        self.assertIs(FD.approval_current(self.finding(1.0, fv=1.0)), False)


class TestNamedVersionAndDigestAreValidated(Base):
    def test_a_named_version_that_is_not_a_whole_number_is_refused_as_a_malformed_token_even_if_it_equals_the_version(self):
        proposed(self.m, self.fid)
        for bad in (True, 1.0, '1', False, 0, -1, [1]):
            self.refused_by_transition('APPROVAL_TOKEN_REQUIRED', approving_version=bad)

    def test_a_named_digest_that_is_not_text_is_refused_as_a_malformed_token(self):
        proposed(self.m, self.fid)
        for bad in (5, '', '  ', ['d'], b'x', True):
            self.refused_by_transition('APPROVAL_TOKEN_REQUIRED', approving_digest=bad)

    def test_an_older_whole_number_is_still_a_stale_approval_not_a_malformed_token(self):
        proposed(self.m, self.fid)
        worsen(self.m)
        self.refused_by_transition('STALE_APPROVAL', approving_version=1)

    def test_a_well_formed_current_token_still_approves_a_fresh_proposal(self):
        proposed(self.m, self.fid)
        t = self.token_of()
        f = FD.approve_action(self.m.approver, self.m.clock, self.fid, t['version'], t['digest'], 'ok', approving_proposal=t['proposal'])
        self.assertEqual((f['status'], FD.approval_current(f)), ('action_approved', True))

    def test_the_lower_level_transition_approves_a_fresh_proposal_when_the_whole_token_is_named(self):
        proposed(self.m, self.fid)
        f = approve_filled(self.m.approver, self.m.clock, self.fid, rationale='ok')
        self.assertEqual(f['status'], 'action_approved')

    def test_the_self_approval_refusal_still_comes_first_for_a_malformed_token(self):
        proposed(self.m, self.fid)
        proposer = person(self.m, 'tok-prop', FD.get(self.m.svc, self.fid)['action']['proposed_by'], FD.APPROVER)
        with self.assertRaises(FD.LifecycleError) as c:
            approve_filled(proposer, self.m.clock, self.fid, rationale='me', approving_version=True)
        self.assertEqual(c.exception.code, 'SELF_APPROVAL')


class TestDamagedStoredRecordsFailClosed(Base):
    def test_every_malformed_stored_proposal_version_blocks_approval_through_the_entry_point(self):
        proposed(self.m, self.fid)
        t = self.token_of()
        for bad in (True, False, 0, -1, None, '1', [1]):
            damage(self.m, self.fid, action={'proposed_version': bad})
            self.refused_by_entry_point('STALE_PROPOSAL', t['version'], t['digest'])

    def test_a_malformed_stored_finding_version_blocks_approval_and_cannot_even_make_a_token(self):
        proposed(self.m, self.fid)
        damage(self.m, self.fid, version=True)
        self.assertIs(FD.proposal_current(FD.get(self.m.svc, self.fid)), False)
        self.refused_by_transition('APPROVAL_TOKEN_REQUIRED', approving_version=None)       # M6.5: a damaged record gives no token to name, and the lower-level call no longer accepts an approval that names none
        self.refused_by_transition('STALE_PROPOSAL', approving_version=1, approving_digest=FD.get(self.m.svc, self.fid)['signal']['state_digest'])
        t = self.token_of()
        self.refused_by_entry_point('APPROVAL_TOKEN_REQUIRED', t['version'], t['digest'])

    def test_a_malformed_stored_digest_blocks_approval(self):
        proposed(self.m, self.fid)
        damage(self.m, self.fid, action={'proposed_digest': 5}, digest=5)
        self.assertIs(FD.proposal_current(FD.get(self.m.svc, self.fid)), False)
        self.refused_by_transition('APPROVAL_TOKEN_REQUIRED', approving_digest=None)        # M6.5: a damaged record gives no token to name
        self.refused_by_transition('APPROVAL_TOKEN_REQUIRED', approving_digest=5)           # a damaged stored digest is not a digest that can be named back
        self.refused_by_transition('STALE_APPROVAL', approving_version=1, approving_digest='a' * 24)

    def test_a_proposal_marked_stale_in_the_record_is_refused_even_if_its_version_and_digest_match(self):
        proposed(self.m, self.fid)
        t = self.token_of()
        damage(self.m, self.fid, action={'proposal_state': 'stale'})
        self.refused_by_entry_point('STALE_PROPOSAL', t['version'], t['digest'])

    def test_a_damaged_proposal_can_be_replaced_by_the_normal_route_and_the_new_one_is_approvable(self):
        proposed(self.m, self.fid)
        damage(self.m, self.fid, action={'proposed_version': True})
        f = reproposed(self.m, self.fid, text='proposed again')
        self.assertEqual((f['action']['proposed_version'], type(f['action']['proposed_version']), FD.proposal_current(f)), (1, int, True))
        (old,) = f['action']['proposal_history']
        self.assertIs(old['proposed_version'], True, 'the damaged value is kept as found in the history')
        self.assertEqual(old['proposal_state'], 'stale')
        g = approve_filled(self.m.approver, self.m.clock, self.fid, rationale='ok')
        self.assertEqual(g['status'], 'action_approved')

    def test_a_replaced_proposal_that_was_damaged_is_recorded_as_stale_not_current(self):
        proposed(self.m, self.fid)
        damage(self.m, self.fid, action={'proposed_version': False})
        f = reproposed(self.m, self.fid)
        self.assertEqual(f['action']['proposal_history'][0]['proposal_state'], 'stale')

    def test_the_approvable_reason_distinguishes_a_missing_version_from_an_invalid_one(self):
        base = {'finding_id': 'F', 'status': 'action_proposed', 'version': 3, 'signal': {'state_digest': 'd'}}
        ok1, why1 = FD.approvable(dict(base, action={'text': 'x'}))
        ok2, why2 = FD.approvable(dict(base, action={'text': 'x', 'proposed_version': 3.0, 'proposed_digest': 'd'}))
        self.assertEqual((ok1, ok2), (False, False))
        self.assertIn('not recorded', why1)
        self.assertIn('not a valid version number', why2)
        self.assertNotIn('not recorded', why2)

    def test_approvable_says_no_action_for_every_shape_that_is_not_a_proposal(self):
        base = {'finding_id': 'F', 'status': 'action_proposed', 'version': 3, 'signal': {'state_digest': 'd'}}
        for shape in (None, {}, '', 'x', 'proposal text', 0, 5, True, [], ['x']):
            ok, why = FD.approvable(dict(base, action=shape))
            self.assertEqual((ok, why), (False, 'no action has been proposed'), repr(shape))
        self.assertEqual(FD.approvable({k: v for k, v in base.items()})[0], False)
        for shape in ('x', 5, True, ['x'], {}):
            self.assertFalse(FD.proposal_current(dict(base, action=shape)), repr(shape))


class TestNothingElseMoved(Base):
    def test_the_transition_table_and_status_set_are_unchanged(self):
        self.assertEqual(len(FD.TRANSITIONS), 14)
        self.assertEqual(len(FD.STATUSES), 10)

    def test_a_normal_stale_proposal_is_still_refused_as_before(self):
        proposed(self.m, self.fid)
        worsen(self.m)
        self.refused_by_transition('STALE_PROPOSAL')
        self.refused_by_transition('STALE_PROPOSAL', approving_version=2)

    def test_a_normal_proposal_records_plain_integers(self):
        f = proposed(self.m, self.fid)
        self.assertIs(type(f['action']['proposed_version']), int)
        self.assertIs(type(f['version']), int)


if __name__ == '__main__':
    unittest.main()
