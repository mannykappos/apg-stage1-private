"""APG-F67: correction of finding F-67.  The financial policy, the detection policy, the procurement policy and the specification register accepted an approval the caller
asserted (approver, role and kind as plain fields), and a run counted it.  Now a version is proposed by the person storing it and never arrives with an approval; an approval
is recorded only by approve_policy / approve_spec from the approver's own verified context; and a run counts an approval only when the audit log confirms it, pinning the
confirmed approvers in its parameters (apg/policy_approval.py).
Each test runs over all four records.  The tests in TestForged, TestMissingAndInvalidEvidence and TestReproduction fail or error against the delivered MIE-1.1-R1 code."""
import copy, unittest
from . import _path                                         # noqa: F401
from .helpers_mkt import mkt_world, AS_OF
from apg import repro
try:
    from apg import policy_approval as PA
except ImportError:                                         # the delivered MIE-1.1-R1 package has no approval provenance; the tests then fail or error case by case
    PA = None
from apg.det import policy as DP
from apg.fin import policy as FP
from apg.mkt import policy as MP

# name -> (kind, role, store, approve, error, the run's answer for it)
RECORDS = {
    'fin': (FP.POLICY_KIND, FP.POLICY_ROLE, FP.store_policy, getattr(FP, 'approve_policy', None), FP.PolicyError, lambda m, v: fin_run(m, v)['result']['policy']['approved']),
    'det': (DP.POLICY_KIND, DP.POLICY_ROLE, DP.store_policy, getattr(DP, 'approve_policy', None), DP.DetPolicyError, lambda m, v: m.res(dpol=v)['det_policy']['approved']),
    'mkt': (MP.POLICY_KIND, MP.POLICY_ROLE, MP.store_policy, getattr(MP, 'approve_policy', None), MP.MktPolicyError,
            lambda m, v: MP_run(m, mkt=v)['mkt_policy']['approved']),
    'spec': (MP.SPEC_KIND, MP.SPEC_ROLE, MP.store_spec, getattr(MP, 'approve_spec', None), MP.MktPolicyError, lambda m, v: MP_run(m, spec=v)['mkt_spec']['approved']),
}


def fin_run(m, version=None):
    from apg.fin import calc_records as C
    return C.run_calc(m.s, m.reg, m.clock, 'fin.forecast', 'PRJ-001', AS_OF, version or m.policy['version'])


def MP_run(m, mkt=None, spec=None):
    from apg.mkt import detect as MD
    return MD.run_project(m.s, m.mreg, m.clock, 'PRJ-001', AS_OF, m.policy['version'], m.dp['version'], mkt or m.mp['version'], spec or m.sp['version'])['result']


def current(m, name):
    return {'fin': m.policy, 'det': m.dp, 'mkt': m.mp, 'spec': m.sp}[name]


def proposal(m, name, version):
    p = copy.deepcopy(current(m, name))
    p.update(version=version, proposer=m.s.ctx.user_id, approvals=[])
    return p


def forged(role, who='mallory'):
    return {'approver': who, 'role': role, 'kind': 'human', 'date': AS_OF}


class TestForged(unittest.TestCase):
    """F-67: none of the ways a caller could assert an approval is accepted or counted."""
    def test_a_version_arriving_with_an_approval_is_refused_and_nothing_is_stored(self):
        m = mkt_world(approved=False)
        for name, (kind, role, store, approve, err, run) in RECORDS.items():
            with self.subTest(record=name):
                with self.assertRaises(err):
                    store(m.s, dict(proposal(m, name, 'A-1'), approvals=[forged(role)]))
                self.assertIsNone(m.s.get(kind, 'A-1'))
                self.assertEqual(m.w.audit.read(m.s.ctx)[-1].event_type, kind + '.refused')

    def test_an_approval_appended_to_the_stored_proposal_is_refused(self):
        m = mkt_world(approved=False)
        for name, (kind, role, store, approve, err, run) in RECORDS.items():
            with self.subTest(record=name):
                p = proposal(m, name, 'B-1')
                store(m.s, p)
                with self.assertRaises(err):
                    store(m.s, dict(p, approvals=[forged(role)]))
                self.assertEqual(m.s.get(kind, 'B-1').payload['approvals'], [])
                self.assertFalse(run(m, 'B-1'))

    def test_an_approval_written_straight_into_the_store_is_not_counted(self):
        m = mkt_world(approved=False)
        for name, (kind, role, store, approve, err, run) in RECORDS.items():
            with self.subTest(record=name):
                m.s.put(kind, 'C-1', dict(proposal(m, name, 'C-1'), approvals=[forged(role)]), expected_revision=0)
                self.assertFalse(run(m, 'C-1'))

    def test_naming_another_proposer_so_the_storer_can_approve_is_refused(self):
        m = mkt_world(approved=False)
        for name, (kind, role, store, approve, err, run) in RECORDS.items():
            with self.subTest(record=name):
                with self.assertRaises(err):
                    store(m.s, dict(proposal(m, name, 'D-1'), proposer='someone.else'))
                with self.assertRaises(err):
                    store(m.s, dict(proposal(m, name, 'D-2'), proposer='someone.else', approvals=[forged(role, m.s.ctx.user_id)]))
                self.assertIsNone(m.s.get(kind, 'D-1'))

    def test_a_proposal_from_a_service_or_carrying_an_approval_field_is_refused(self):
        m = mkt_world(approved=False)
        svc = m.w.who('svcx', 'zero_one', 'ann', ('importer',), 'service')
        for name, (kind, role, store, approve, err, run) in RECORDS.items():
            with self.subTest(record=name):
                with self.assertRaises(err):
                    store(svc, proposal(m, name, 'E-1'))
        for name, new, err in (('fin', FP.new_policy, FP.PolicyError), ('det', DP.new_policy, DP.DetPolicyError), ('mkt', MP.new_policy, MP.MktPolicyError),
                               ('spec', MP.new_spec, MP.MktPolicyError)):
            with self.subTest(builder=name):
                fields = {k: v for k, v in current(m, name).items() if k not in ('version', 'proposer', 'approvals')}
                self.assertEqual(new('E-2', 'ann', **fields)['approvals'], [])          # the same fields without an approval are a valid proposal
                with self.assertRaises(err) as cm:
                    new('E-2', 'ann', approvals=[forged(RECORDS[name][1])], **fields)
                self.assertIn('carries no approval', str(cm.exception))


class TestMissingAndInvalidEvidence(unittest.TestCase):
    """An approval counts only with valid audit evidence: an event '<kind>.approved' for that version, ok, written under the approver's own human context."""
    def plant(self, m, name, version, event_kwargs):
        """A record listing an approval, and one audit event that is wrong in exactly one respect.  -> (the people the log confirms for this version, the run's answer)."""
        kind, role, store, approve, err, run = RECORDS[name]
        listed = event_kwargs.pop('listed', 'bob')
        m.s.put(kind, version, dict(proposal(m, name, version), approvals=[forged(role, listed)]), expected_revision=0)
        actor = event_kwargs.pop('actor', m.w.who('bob-' + version, 'zero_one', 'bob', (role,)))
        detail = {'kind': kind, 'version': version, 'approver': 'bob'}
        detail.update(event_kwargs.pop('detail', {}))
        actor.log(event_kwargs.pop('event_type', kind + '.approved'), event_kwargs.pop('resource', '%s/%s' % (kind, version)), event_kwargs.pop('outcome', 'ok'), detail=detail)
        return PA.confirmed(m.s, kind, version), run(m, version)

    def test_no_audit_event_means_no_approval(self):
        m = mkt_world(approved=False)
        for name, (kind, role, store, approve, err, run) in RECORDS.items():
            with self.subTest(record=name):
                m.s.put(kind, 'M-1', dict(proposal(m, name, 'M-1'), approvals=[forged(role, 'bob')]), expected_revision=0)
                self.assertFalse(run(m, 'M-1'))
                self.assertEqual(PA.confirmed(m.s, kind, 'M-1'), [])

    def test_evidence_that_is_wrong_in_any_one_respect_is_not_counted(self):
        m = mkt_world(approved=False)
        for name in RECORDS:
            kind = RECORDS[name][0]
            other_kind = 'det_policy' if kind != 'det_policy' else 'fin_policy'
            cases = {
                'another version': {'detail': {'version': 'OTHER'}, 'resource': '%s/OTHER' % kind},
                'a refusal, not an approval': {'outcome': 'refused'},
                'the event of another record kind': {'event_type': other_kind + '.approved'},
                'naming an approver who did not write it': {'actor': m.w.who('eve-' + name, 'zero_one', 'eve', ('importer',))},
                'written by the listed approver but naming another': {'actor': m.w.who('eve2-' + name, 'zero_one', 'eve', (RECORDS[name][1],)), 'listed': 'eve'},
                'written by a service': {'actor': m.w.who('svc-' + name, 'zero_one', 'bob', ('importer',), 'service')},
                'for another resource': {'resource': '%s/ELSEWHERE' % kind},
                'whose detail names another version': {'detail': {'version': 'OTHER'}},
                'whose detail names another record kind': {'detail': {'kind': other_kind}},
            }
            for i, (what, kw) in enumerate(cases.items()):
                with self.subTest(record=name, evidence=what):
                    self.assertEqual(self.plant(m, name, 'I-%d' % i, dict(kw)), ([], False))

    def test_the_owner_approval_through_the_corrected_path_is_counted(self):
        """The control."""
        m = mkt_world(approved=False)
        for name, (kind, role, store, approve, err, run) in RECORDS.items():
            with self.subTest(record=name):
                p = proposal(m, name, 'OK-1')
                store(m.s, p)
                self.assertFalse(run(m, 'OK-1'))
                approve(m.pown, m.clock, 'OK-1', 'approved by the owner in person')
                self.assertTrue(run(m, 'OK-1'))
                self.assertEqual(PA.confirmed(m.s, kind, 'OK-1'), [m.pown.ctx.user_id])
                ev = [e for e in m.w.audit.read(m.s.ctx) if e.event_type == kind + '.approved'][-1]
                self.assertEqual((ev.actor, ev.actor_kind, ev.detail['version']), (m.pown.ctx.user_id, 'human', 'OK-1'))


    def test_an_approval_that_meets_a_concurrent_change_is_refused_and_leaves_no_event(self):
        m = mkt_world(approved=False)
        from apg.ports import ConflictError
        for name, (kind, role, store, approve, err, run) in RECORDS.items():
            with self.subTest(record=name):
                p = proposal(m, name, 'CC-1')
                store(m.s, p)
                real = m.pown.put

                def racing(*a, **kw):
                    raise ConflictError('changed concurrently')
                m.pown.put = racing
                try:
                    with self.assertRaises(err) as cm:
                        approve(m.pown, m.clock, 'CC-1', 'ok')
                finally:
                    m.pown.put = real
                self.assertIn('changed while it was being approved', str(cm.exception))
                self.assertEqual(PA.confirmed(m.s, kind, 'CC-1'), [])
                self.assertEqual(m.s.get(kind, 'CC-1').payload['approvals'], [])


class TestReproduction(unittest.TestCase):
    def test_a_run_pins_the_confirmed_approvers_and_replays_without_reading_the_log(self):
        """A run made before the approval stays unapproved on replay; one made after is approved and replays as approved.  The confirmed approvers are in the parameters."""
        m = mkt_world(approved=False)
        ver = m.policy['version']
        before = fin_run(m)
        FP.approve_policy(m.pown, m.clock, ver, 'ok')
        after = fin_run(m)
        self.assertEqual((before['result']['policy']['approved'], after['result']['policy']['approved']), (False, True))
        self.assertEqual(before['params']['approvals_confirmed']['fin_policy/' + ver], [])
        self.assertEqual(after['params']['approvals_confirmed']['fin_policy/' + ver], [m.pown.ctx.user_id])
        from apg.fin import calc_records as C
        for rec in (before, after):
            self.assertTrue(C.check_record(m.s, m.reg, rec['run_key'])['replay'].ok)
        stored = m.s.get(repro.KIND, before['run_key']).payload
        self.assertFalse(stored['result']['policy']['approved'])

    def test_a_detection_and_a_procurement_run_pin_every_policy_they_read(self):
        m = mkt_world()
        params = m.mdetect()['params']
        keys = sorted(params['approvals_confirmed'])
        self.assertEqual(keys, sorted(['det_policy/' + m.dp['version'], 'fin_policy/' + m.policy['version'], 'mkt_policy/' + m.mp['version'], 'mkt_spec/' + m.sp['version']]))
        self.assertTrue(all(v == [m.pown.ctx.user_id] for v in params['approvals_confirmed'].values()))
        self.assertEqual(sorted(m.detect()['params']['approvals_confirmed']), sorted(['det_policy/' + m.dp['version'], 'fin_policy/' + m.policy['version']]))


class TestApprovalRules(unittest.TestCase):
    def test_who_may_approve(self):
        """A human holding the record's owner role, not the proposer, once; with a rationale; a version that exists."""
        m = mkt_world(approved=False)
        for name, (kind, role, store, approve, err, run) in RECORDS.items():
            with self.subTest(record=name):
                ver = current(m, name)['version']
                for tok, user, roles, kind_ in (('r1-' + name, m.s.ctx.user_id, (role,), 'human'), ('r2-' + name, 'bob', ('importer',), 'human'),
                                                ('r3-' + name, 'bob', (role,), 'service'), ('r4-' + name, 'bob', (role,), 'ai')):
                    with self.assertRaises(err):
                        approve(m.w.who(tok, 'zero_one', user, roles, kind_), m.clock, ver, 'ok')
                bob = m.w.who('r5-' + name, 'zero_one', 'bob', (role,))
                with self.assertRaises(err):
                    approve(bob, m.clock, ver, '   ')
                with self.assertRaises(err):
                    approve(bob, m.clock, 'NO-SUCH-VERSION', 'ok')
                approve(bob, m.clock, ver, 'ok')
                with self.assertRaises(err):
                    approve(bob, m.clock, ver, 'twice')
                self.assertEqual([a['approver'] for a in m.s.get(kind, ver).payload['approvals']], ['bob'])


if __name__ == '__main__':
    unittest.main()
