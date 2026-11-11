import dataclasses, unittest
from . import _path                                          # noqa: F401
from apg import status_model as S

H = 'a' * 64
R = 'REQ-1'


def E(kind, **kw):
    d = dict(kind=kind, ref=f'ev-{kind}', requirement_ids=(R,), build='b1', environment='local', result='pass', actor='builder1', actor_kind='human', role='', mock_only=False,
             tests=('T1',), components=(), integrity_hash=H, reason='', next_action='')
    d.update(kw); return S.Evidence(**d)


APPROVE = lambda **k: E('approval', **{'role': 'product_owner', 'actor': 'emmanuel', 'environment': 'n/a', 'tests': (), 'integrity_hash': '', **k})
IMPL = lambda **k: E('implementation', **{'environment': 'n/a', 'tests': (), **k})
LOCAL = lambda **k: E('test_run', **k)
INTEG = lambda **k: E('integration_run', **{'environment': 'integration', 'components': ('store', 'connector'), **k})
STAGE = lambda **k: E('staging_run', **{'environment': 'staging', **k})
OPER = lambda **k: E('operational', **{'environment': 'target', **k})
REVIEW = lambda **k: E('review', **{'role': 'authorised_reviewer', 'actor': 'auditor', 'environment': 'n/a', 'tests': (), **k})
CLOSE = lambda **k: E('closure', **{'role': 'closure_authority', 'actor': 'emmanuel', 'environment': 'n/a', 'tests': (), 'reason': 'all gates passed', **k})


def to(level, **over):
    st = S.new_requirement(R, over.pop('required_level', 'Staging-verified'), over.pop('mandatory_tests', ('T1',)))
    steps = [('Specified', APPROVE()), ('Implemented', IMPL()), ('Local-tested', LOCAL()), ('Integration-tested', INTEG()), ('Staging-verified', STAGE()), ('Operationally verified', OPER()),
             ('Accepted', REVIEW()), ('Closed', CLOSE())]
    for tgt, ev in steps:
        st = S.advance(st, tgt, ev)
        if tgt == level:
            return st
    raise AssertionError(level)


def code(fn):
    try:
        fn()
    except S.StatusError as e:
        return e.code
    return None


class Happy(unittest.TestCase):
    def test_full_path_and_history(self):
        st = to('Closed')
        self.assertEqual(st.status, 'Closed'); self.assertEqual([h[1] for h in st.history], list(S.LADDER))

    def test_builder_recorded_from_implementation(self):
        self.assertEqual(to('Implemented').builder, 'builder1')


class Rungs(unittest.TestCase):
    def test_cannot_skip_a_rung(self):
        st = to('Implemented')
        self.assertEqual(code(lambda: S.advance(st, 'Integration-tested', INTEG())), 'SKIPPED_RUNG')
        self.assertEqual(code(lambda: S.advance(st, 'Closed', CLOSE())), 'SKIPPED_RUNG')
        self.assertEqual(code(lambda: S.advance(S.new_requirement(R), 'Implemented', IMPL())), 'SKIPPED_RUNG')

    def test_cannot_go_backwards_or_repeat(self):
        st = to('Local-tested')
        self.assertEqual(code(lambda: S.advance(st, 'Specified', APPROVE())), 'SKIPPED_RUNG'); self.assertEqual(code(lambda: S.advance(st, 'Local-tested', LOCAL())), 'SKIPPED_RUNG')

    def test_unknown_status(self):
        self.assertEqual(code(lambda: S.advance(to('Specified'), 'Done', IMPL())), 'UNKNOWN_STATUS')

    def test_states_are_immutable(self):
        st = to('Specified')
        with self.assertRaises(dataclasses.FrozenInstanceError): st.status = 'Closed'
        S.advance(st, 'Implemented', IMPL()); self.assertEqual(st.status, 'Specified')


class Evidence(unittest.TestCase):
    def test_non_passing_evidence_never_advances(self):
        st = to('Implemented')
        for res in ('fail', 'skipped', 'skip', 'blocked', 'not_run', 'PASS', 'passed', ''):
            self.assertIn(code(lambda r=res: S.advance(st, 'Local-tested', LOCAL(result=r))), ('EVIDENCE_NOT_PASSING',), res)

    def test_evidence_for_another_requirement_is_refused(self):
        st = to('Implemented')
        self.assertEqual(code(lambda: S.advance(st, 'Local-tested', LOCAL(requirement_ids=('REQ-2',)))), 'EVIDENCE_NOT_FOR_REQUIREMENT')
        self.assertEqual(code(lambda: S.advance(st, 'Local-tested', LOCAL(requirement_ids=()))), 'EVIDENCE_NOT_FOR_REQUIREMENT')

    def test_evidence_for_a_different_build_is_refused(self):
        st = to('Implemented')
        self.assertEqual(code(lambda: S.advance(st, 'Local-tested', LOCAL(build='b2'))), 'STALE_OR_DIFFERENT_BUILD')
        self.assertEqual(code(lambda: S.advance(st, 'Local-tested', LOCAL(build=''))), 'STALE_OR_DIFFERENT_BUILD')

    def test_hash_and_tests_required(self):
        st = to('Implemented')
        for h in ('', 'xyz', 'A' * 64, 'a' * 63):
            self.assertEqual(code(lambda x=h: S.advance(st, 'Local-tested', LOCAL(integrity_hash=x))), 'NO_INTEGRITY_HASH', h)
        self.assertEqual(code(lambda: S.advance(st, 'Local-tested', LOCAL(tests=()))), 'NO_TESTS_NAMED')

    def test_incomplete_evidence_is_refused(self):
        st = to('Implemented')
        self.assertEqual(code(lambda: S.advance(st, 'Local-tested', LOCAL(ref=''))), 'EVIDENCE_INCOMPLETE'); self.assertEqual(code(lambda: S.advance(st, 'Local-tested', LOCAL(actor=''))), 'EVIDENCE_INCOMPLETE')
        for k in ('robot', '', 'AI', None):
            self.assertEqual(code(lambda x=k: S.advance(st, 'Local-tested', LOCAL(actor_kind=x))), 'EVIDENCE_INCOMPLETE', str(k))

    def test_implemented_needs_an_implementation_record_with_a_build(self):
        st = to('Specified')
        self.assertEqual(code(lambda: S.advance(st, 'Implemented', LOCAL())), 'NO_IMPLEMENTATION')
        self.assertEqual(code(lambda: S.advance(st, 'Implemented', IMPL(build=''))), 'NO_IMPLEMENTATION')

    def test_wrong_kind_and_environment(self):
        st = to('Implemented')
        self.assertEqual(code(lambda: S.advance(st, 'Local-tested', INTEG())), 'WRONG_EVIDENCE_KIND')
        self.assertEqual(code(lambda: S.advance(st, 'Local-tested', LOCAL(environment='staging'))), 'WRONG_ENVIRONMENT')
        st2 = to('Local-tested')
        self.assertEqual(code(lambda: S.advance(st2, 'Integration-tested', INTEG(environment='local'))), 'WRONG_ENVIRONMENT')

    def test_mock_only_ok_locally_but_not_for_integration_or_above(self):
        st = to('Implemented'); st = S.advance(st, 'Local-tested', LOCAL(mock_only=True)); self.assertEqual(st.status, 'Local-tested')
        self.assertEqual(code(lambda: S.advance(st, 'Integration-tested', INTEG(mock_only=True))), 'MOCK_ONLY')
        st = to('Integration-tested')
        self.assertEqual(code(lambda: S.advance(st, 'Staging-verified', STAGE(mock_only=True))), 'MOCK_ONLY')
        st = to('Staging-verified')
        self.assertEqual(code(lambda: S.advance(st, 'Operationally verified', OPER(mock_only=True))), 'MOCK_ONLY')

    def test_integration_must_name_components(self):
        self.assertEqual(code(lambda: S.advance(to('Local-tested'), 'Integration-tested', INTEG(components=()))), 'NO_COMPONENTS')


class Authority(unittest.TestCase):
    def test_specified_needs_human_product_owner_or_spec_approver(self):
        st = S.new_requirement(R)
        for kw in ({'actor_kind': 'ai'}, {'role': 'builder'}, {'actor_kind': 'service'}, {'role': ''}):
            self.assertEqual(code(lambda k=kw: S.advance(st, 'Specified', dataclasses.replace(APPROVE(), **k))), 'NOT_APPROVED', str(kw))
        self.assertEqual(S.advance(st, 'Specified', dataclasses.replace(APPROVE(), role='spec_approver')).status, 'Specified')

    def test_acceptance_needs_authorised_human_reviewer_who_is_not_the_builder(self):
        st = to('Operationally verified')
        for kw, c in (({'actor_kind': 'ai'}, 'NOT_AUTHORISED'), ({'role': 'builder'}, 'NOT_AUTHORISED'), ({'actor': 'builder1'}, 'SELF_ACCEPTANCE'), ({'build': 'b9'}, 'STALE_OR_DIFFERENT_BUILD')):
            self.assertEqual(code(lambda k=kw: S.advance(st, 'Accepted', dataclasses.replace(REVIEW(), **k))), c, str(kw))

    def test_acceptance_needs_the_required_level_and_operational_evidence_only_where_applicable(self):
        for lvl in ('Specified', 'Implemented', 'Local-tested', 'Integration-tested'):
            st = to(lvl)                                                                         # required level is Staging-verified
            self.assertEqual(code(lambda s=st: S.advance(s, 'Accepted', REVIEW())), 'BELOW_REQUIRED_LEVEL', lvl)
        st = to('Staging-verified'); self.assertEqual(S.advance(st, 'Accepted', REVIEW()).status, 'Accepted')          # operational rung not applicable here
        self.assertEqual(S.advance(S.advance(st, 'Operationally verified', OPER()), 'Accepted', REVIEW()).status, 'Accepted')
        st = to('Staging-verified', required_level='Operationally verified')
        self.assertEqual(code(lambda: S.advance(st, 'Accepted', REVIEW())), 'BELOW_REQUIRED_LEVEL')
        low = to('Local-tested', required_level='Local-tested'); self.assertEqual(S.advance(low, 'Accepted', REVIEW()).status, 'Accepted')
        acc = S.advance(to('Staging-verified'), 'Accepted', REVIEW()); self.assertEqual(code(lambda: S.advance(acc, 'Accepted', REVIEW())), 'SKIPPED_RUNG')

    def test_a_lower_required_level_can_be_closed_without_the_higher_gates(self):
        st = S.advance(to('Staging-verified'), 'Accepted', REVIEW()); self.assertEqual(S.advance(st, 'Closed', CLOSE()).status, 'Closed')

    def test_required_level_must_be_one_of_the_verification_levels(self):
        for bad in ('Closed', 'Accepted', 'Specified', 'Implemented', 'nonsense', ''):
            self.assertEqual(code(lambda b=bad: S.new_requirement(R, b)), 'LEVEL', bad)

    def test_closure_needs_authority_rationale_gates_and_mandatory_tests(self):
        st = to('Accepted')
        self.assertEqual(code(lambda: S.advance(st, 'Closed', dataclasses.replace(CLOSE(), actor_kind='ai'))), 'NOT_AUTHORISED')
        self.assertEqual(code(lambda: S.advance(st, 'Closed', dataclasses.replace(CLOSE(), reason=''))), 'NOT_AUTHORISED')
        self.assertEqual(code(lambda: S.advance(st, 'Closed', dataclasses.replace(CLOSE(), role='auditor'))), 'NOT_AUTHORISED')
        stm = to('Accepted', mandatory_tests=('T1', 'T-NEVER-RUN'))
        self.assertEqual(code(lambda: S.advance(stm, 'Closed', CLOSE())), 'MANDATORY_TEST_MISSING')

    def test_closure_counts_only_evidence_for_the_current_build(self):
        old = S.advance(S.advance(S.advance(S.advance(S.advance(S.new_requirement(R, 'Staging-verified', ('T-OLD',)), 'Specified', APPROVE()), 'Implemented', IMPL()),
                                            'Local-tested', LOCAL(tests=('T-OLD',))), 'Integration-tested', INTEG(tests=('T-OLD',))), 'Staging-verified', STAGE(tests=('T-OLD',)))
        n = S.change_build(old, 'b2', 'dev2')
        for tgt, ev in (('Local-tested', LOCAL(build='b2')), ('Integration-tested', INTEG(build='b2')), ('Staging-verified', STAGE(build='b2')), ('Accepted', REVIEW(build='b2'))):
            n = S.advance(n, tgt, ev)
        self.assertEqual(code(lambda: S.advance(n, 'Closed', CLOSE(build='b2'))), 'MANDATORY_TEST_MISSING')       # T-OLD was only ever run on build b1

    def test_closure_evidence_must_be_for_the_current_build(self):
        self.assertEqual(code(lambda: S.advance(to('Accepted'), 'Closed', CLOSE(build='b9'))), 'STALE_OR_DIFFERENT_BUILD')

    def test_closure_blocked_when_a_gate_has_no_evidence_for_this_build(self):
        st = to('Accepted')
        stripped = dataclasses.replace(st, evidence=tuple(e for e in st.evidence if e.kind != 'staging_run'))
        self.assertEqual(code(lambda: S.advance(stripped, 'Closed', CLOSE())), 'GATE_MISSING')


class SideStates(unittest.TestCase):
    def test_failure_blocks_progress_until_new_passing_evidence(self):
        st = to('Local-tested'); f = S.record_failure(st, LOCAL(result='fail'))
        self.assertEqual((f.status, f.last_good), ('Failed', 'Local-tested'))
        self.assertEqual(code(lambda: S.advance(f, 'Integration-tested', INTEG())), 'NOT_ADVANCEABLE')
        r = S.recover(f, LOCAL()); self.assertEqual(r.status, 'Local-tested')

    def test_recovery_cannot_jump_above_last_good_and_needs_current_build(self):
        f = S.record_failure(to('Local-tested'), LOCAL(result='fail'))
        self.assertEqual(code(lambda: S.recover(f, LOCAL(build='old'))), 'STALE_OR_DIFFERENT_BUILD')
        self.assertEqual(code(lambda: S.recover(f, LOCAL(result='skipped'))), 'EVIDENCE_NOT_PASSING')
        self.assertEqual(S.recover(f, STAGE(environment='staging')).status, 'Local-tested')

    def test_failure_record_must_be_a_failure_for_this_requirement(self):
        st = to('Local-tested')
        self.assertEqual(code(lambda: S.record_failure(st, LOCAL(result='pass'))), 'NOT_A_FAILURE_RECORD')
        self.assertEqual(code(lambda: S.record_failure(st, LOCAL(result='fail', requirement_ids=('X',)))), 'NOT_A_FAILURE_RECORD')

    def test_block_needs_reason_and_next_action_and_cannot_advance(self):
        st = to('Implemented')
        self.assertEqual(code(lambda: S.block(st, '', 'x')), 'BLOCK_NEEDS_REASON_AND_NEXT_ACTION'); self.assertEqual(code(lambda: S.block(st, 'x', '')), 'BLOCK_NEEDS_REASON_AND_NEXT_ACTION')
        b = S.block(st, 'no database', 'Amir provisions DB'); self.assertEqual(b.status, 'Blocked')
        self.assertEqual(code(lambda: S.advance(b, 'Local-tested', LOCAL())), 'NOT_ADVANCEABLE')
        self.assertEqual(S.recover(b, LOCAL()).status, 'Implemented')

    def test_build_change_demotes_to_implemented_and_old_evidence_does_not_carry(self):
        st = to('Staging-verified'); n = S.change_build(st, 'b2', 'builder2')
        self.assertEqual((n.status, n.build, n.builder), ('Implemented', 'b2', 'builder2')); self.assertTrue(n.stale_note)
        self.assertEqual(code(lambda: S.advance(n, 'Local-tested', LOCAL(build='b1'))), 'STALE_OR_DIFFERENT_BUILD')
        self.assertEqual(S.advance(n, 'Local-tested', LOCAL(build='b2')).status, 'Local-tested')
        self.assertIs(S.change_build(st, 'b1', 'x'), st)
        self.assertEqual(code(lambda: S.change_build(S.new_requirement(R), 'b', 'x')), 'NOT_IMPLEMENTED_YET')

    def test_only_blocked_or_failed_states_can_recover(self):
        self.assertEqual(code(lambda: S.recover(to('Local-tested'), LOCAL())), 'NOT_BLOCKED_OR_FAILED')

    def test_closed_requirement_loses_closure_on_build_change(self):
        n = S.change_build(to('Closed'), 'b2', 'builder2'); self.assertEqual(n.status, 'Implemented')


class Replay(unittest.TestCase):
    def test_supported_status_replays_evidence(self):
        steps = [('Specified', APPROVE()), ('Implemented', IMPL()), ('Local-tested', LOCAL())]
        st, err = S.supported_status(R, steps); self.assertEqual((st.status, err), ('Local-tested', None))

    def test_claimed_status_beyond_evidence_is_exposed(self):
        steps = [('Specified', APPROVE()), ('Implemented', IMPL()), ('Local-tested', LOCAL()), ('Staging-verified', STAGE())]
        st, err = S.supported_status(R, steps)
        self.assertEqual(st.status, 'Local-tested'); self.assertEqual(err.code, 'SKIPPED_RUNG')

    def test_mock_only_integration_claim_is_exposed(self):
        steps = [('Specified', APPROVE()), ('Implemented', IMPL()), ('Local-tested', LOCAL()), ('Integration-tested', INTEG(mock_only=True))]
        st, err = S.supported_status(R, steps); self.assertEqual((st.status, err.code), ('Local-tested', 'MOCK_ONLY'))


if __name__ == '__main__':
    unittest.main()
