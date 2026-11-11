"""APG-F67.1: correction of finding F-72 (the independent audit of APG-F67).  An approval writes the approved policy revision and then the confirming audit event.  When the audit
write failed in between, the approval was recorded but not confirmed (so, rightly, not counted), and the owner's retry was refused as "already approved": the policy was stuck.  The
recommendation policy (APG-M7.1) had the same order.  Now the error says the approval is recorded but NOT CONFIRMED, and the same person, with the same identity and role checks, may
call approve again to write only the missing confirming event.  Nobody else can complete it, and nothing is counted twice.
Every test runs over all five policy records.  Run against the delivered APG-F67 code, every test fails or errors."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_mkt import mkt_world, AS_OF
from apg import policy_approval as PA, repro
from apg.det import policy as DP, detect as DT
from apg.fin import policy as FP, calc_records as C
from apg.mkt import policy as MP, detect as MD
from apg.rec import policy as RP, engine as E, demo_rec as DR

ROLES = (FP.POLICY_ROLE, DP.POLICY_ROLE, MP.POLICY_ROLE, MP.SPEC_ROLE, RP.POLICY_ROLE)
# name -> (kind, approval event type, error class, approve, status function name, version attribute on the world)
RECORDS = {
    'fin': (FP.POLICY_KIND, 'fin_policy.approved', FP.PolicyError, FP.approve_policy, (FP, 'approval_status')),
    'det': (DP.POLICY_KIND, 'det_policy.approved', DP.DetPolicyError, DP.approve_policy, (DP, 'approval_status')),
    'mkt': (MP.POLICY_KIND, 'mkt_policy.approved', MP.MktPolicyError, MP.approve_policy, (MP, 'approval_status')),
    'spec': (MP.SPEC_KIND, 'mkt_spec.approved', MP.MktPolicyError, MP.approve_spec, (MP, 'spec_approval_status')),
    'rec': (RP.POLICY_KIND, 'rec.policy_approved', RP.RecPolicyError, RP.approve_policy, (RP, 'approval_status')),
}
EVENTS = {r[1] for r in RECORDS.values()}


class World:
    """The detection-and-procurement test world with every policy proposed and none approved, plus an unapproved recommendation policy; two people hold all five owner roles."""
    def __init__(self):
        self.m = m = mkt_world(approved=False)
        self.s, self.clock = m.s, m.clock
        RP.store_policy(m.s, DR.demo_rec_policy(version='R-1', proposer=m.s.ctx.user_id))
        self.ver = {'fin': m.policy['version'], 'det': m.dp['version'], 'mkt': m.mp['version'], 'spec': m.sp['version'], 'rec': 'R-1'}
        self.olive = self.who('olive')
        self.otto = self.who('otto')

    def who(self, user, roles=ROLES, kind='human'):
        return self.m.w.who('%s-%s-%d' % (user, kind, len(roles)), 'zero_one', user, roles, kind)

    def approve(self, name, scoped, why='approved in person'):
        return RECORDS[name][3](scoped, self.clock, self.ver[name], why)

    def status(self, name):
        mod, fn = RECORDS[name][4]
        return getattr(mod, fn)(self.s, self.ver[name])

    def stored(self, name):
        return self.s.get(RECORDS[name][0], self.ver[name])

    def events(self, name, actor=None):
        return [e for e in self.s._audit.read(self.s.ctx) if e.event_type == RECORDS[name][1] and e.outcome == 'ok' and (actor is None or e.actor == actor)]

    def run(self, name):
        v, m = self.ver, self.m
        if name == 'fin':
            return C.run_calc(self.s, m.reg, self.clock, 'fin.forecast', 'PRJ-001', AS_OF, v['fin'])
        if name == 'det':
            return DT.run_project(self.s, m.detreg, self.clock, 'PRJ-001', AS_OF, v['fin'], v['det'])
        if name in ('mkt', 'spec'):
            return MD.run_project(self.s, m.mreg, self.clock, 'PRJ-001', AS_OF, v['fin'], v['det'], v['mkt'], v['spec'])
        return E.run(self.s, E.registry(), self.clock, AS_OF, v['rec'])

    def approved_in_run(self, name, rec=None):
        r = (rec or self.run(name))['result']
        return {'fin': lambda: r['policy']['approved'], 'det': lambda: r['det_policy']['approved'], 'mkt': lambda: r['mkt_policy']['approved'],
                'spec': lambda: r['mkt_spec']['approved'], 'rec': lambda: r['policy']['approved']}[name]()


def failing(scoped, written=False):
    """The audit write of an approval event fails for this session.  written=True: the event is written, then the sink still raises (an ambiguous failure)."""
    real = scoped.log

    def log(event_type, *a, **k):
        if event_type in EVENTS:
            if written:
                real(event_type, *a, **k)
            raise RuntimeError('audit sink unavailable')
        return real(event_type, *a, **k)
    scoped.log = log
    return lambda: setattr(scoped, 'log', real)


class TestAuditFailure(unittest.TestCase):
    def test_an_audit_failure_leaves_the_approval_recorded_not_confirmed_and_not_counted(self):
        w = World()
        for name, (kind, ev, err, approve, st) in RECORDS.items():
            with self.subTest(record=name):
                restore = failing(w.olive)
                with self.assertRaises(PA.ApprovalNotConfirmed) as cm:
                    w.approve(name, w.olive)
                restore()
                self.assertIsInstance(cm.exception, err)                         # existing callers that catch the record's error still catch it
                self.assertIn('NOT CONFIRMED', str(cm.exception))
                self.assertIn('olive', str(cm.exception))
                self.assertEqual(w.status(name), {'version': w.ver[name], 'recorded': ['olive'], 'confirmed': [], 'recorded_not_confirmed': ['olive']})
                self.assertEqual(w.events(name), [])
                self.assertFalse(w.approved_in_run(name))

    def test_the_same_approver_completes_it_by_retrying_and_only_the_event_is_written(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                restore = failing(w.olive)
                with self.assertRaises(PA.ApprovalNotConfirmed):
                    w.approve(name, w.olive)
                restore()
                before = w.stored(name)
                w.approve(name, w.olive, 'retry after the audit log recovered')
                after = w.stored(name)
                self.assertEqual((after.revision, after.payload), (before.revision, before.payload))        # the retry changes no record
                self.assertEqual(w.status(name)['confirmed'], ['olive'])
                self.assertEqual(w.status(name)['recorded_not_confirmed'], [])
                ev = w.events(name, 'olive')
                self.assertEqual(len(ev), 1)
                self.assertEqual((ev[0].actor_kind, ev[0].detail['approver'], ev[0].detail['completes_recorded_approval']), ('human', 'olive', True))
                self.assertTrue(w.approved_in_run(name))

    def test_a_retry_while_the_log_still_fails_is_not_counted(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                restore = failing(w.olive)
                for _ in range(2):
                    with self.assertRaises(PA.ApprovalNotConfirmed):
                        w.approve(name, w.olive)
                restore()
                self.assertEqual(w.status(name)['recorded_not_confirmed'], ['olive'])
                self.assertEqual(len(w.stored(name).payload['approvals']), 1)
                self.assertFalse(w.approved_in_run(name))

    def test_when_the_log_cannot_be_read_back_either_the_approval_is_not_confirmed(self):
        """Fail closed: after a failed write, a read-back that also fails never counts as a confirmation."""
        w = World()

        class Down:
            def read(self, ctx):
                raise RuntimeError('audit log unavailable')
        for name in RECORDS:
            with self.subTest(record=name):
                restore = failing(w.olive)                                       # the write fails, and the log cannot be read back either
                real = w.olive._audit
                w.olive._audit = Down()
                try:
                    with self.assertRaises(PA.ApprovalNotConfirmed):
                        w.approve(name, w.olive)
                finally:
                    w.olive._audit = real
                    restore()

    def test_an_audit_write_that_lands_but_raises_is_reported_as_confirmed_and_not_repeated(self):
        w = World()
        for name, (kind, ev, err, approve, st) in RECORDS.items():
            with self.subTest(record=name):
                restore = failing(w.olive, written=True)
                w.approve(name, w.olive)                                         # the log confirms it, so the approval succeeded
                restore()
                self.assertEqual(w.status(name)['confirmed'], ['olive'])
                with self.assertRaises(err) as cm:
                    w.approve(name, w.olive, 'again')
                self.assertNotIsInstance(cm.exception, PA.ApprovalNotConfirmed)
                self.assertIn('already approved', str(cm.exception))
                self.assertEqual(len(w.events(name, 'olive')), 1)


class TestOnlyTheApproverCanComplete(unittest.TestCase):
    def stuck(self, w, name):
        restore = failing(w.olive)
        with self.assertRaises(PA.ApprovalNotConfirmed):
            w.approve(name, w.olive)
        restore()

    def test_another_person_with_the_role_adds_their_own_approval_and_does_not_complete_the_first(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                self.stuck(w, name)
                w.approve(name, w.otto)
                self.assertEqual(w.status(name), {'version': w.ver[name], 'recorded': ['olive', 'otto'], 'confirmed': ['otto'], 'recorded_not_confirmed': ['olive']})
                self.assertEqual(w.events(name, 'olive'), [])
                self.assertEqual([e.detail['approver'] for e in w.events(name)], ['otto'])

    def test_the_approver_without_the_role_as_a_service_or_as_an_ai_cannot_complete_it(self):
        w = World()
        for name, (kind, ev, err, approve, st) in RECORDS.items():
            with self.subTest(record=name):
                self.stuck(w, name)
                others = tuple(r for r in ROLES if r != {'fin': FP.POLICY_ROLE, 'det': DP.POLICY_ROLE, 'mkt': MP.POLICY_ROLE, 'spec': MP.SPEC_ROLE, 'rec': RP.POLICY_ROLE}[name])
                for sc in (w.who('olive', others), w.who('olive', ROLES, 'service'), w.who('olive', ROLES, 'ai')):
                    with self.assertRaises(err):
                        w.approve(name, sc)
                self.assertEqual(w.status(name)['recorded_not_confirmed'], ['olive'])
                self.assertEqual(w.events(name, 'olive'), [])
                self.assertFalse(w.approved_in_run(name))

    def test_an_approval_in_the_approvers_name_that_approve_did_not_write_cannot_be_completed(self):
        w = World()
        for name, (kind, ev, err, approve, st) in RECORDS.items():
            with self.subTest(record=name):
                cur = w.stored(name)
                p = dict(cur.payload, approvals=[{'approver': 'olive', 'role': 'some_other_role', 'kind': 'human', 'date': AS_OF}])
                w.s.put(kind, w.ver[name], p, expected_revision=cur.revision)
                with self.assertRaises(err) as cm:
                    w.approve(name, w.olive)
                self.assertIn('did not write', str(cm.exception))
                self.assertEqual(w.events(name, 'olive'), [])
                self.assertFalse(w.approved_in_run(name))


class TestNoDoubleCounting(unittest.TestCase):
    def test_after_recovery_the_approver_is_listed_once_confirmed_once_and_cannot_approve_again(self):
        w = World()
        for name, (kind, ev, err, approve, st) in RECORDS.items():
            with self.subTest(record=name):
                restore = failing(w.olive)
                with self.assertRaises(PA.ApprovalNotConfirmed):
                    w.approve(name, w.olive)
                restore()
                w.approve(name, w.olive, 'complete')
                with self.assertRaises(err) as cm:
                    w.approve(name, w.olive, 'a third time')
                self.assertIn('already approved', str(cm.exception))
                self.assertEqual([a['approver'] for a in w.stored(name).payload['approvals']], ['olive'])
                self.assertEqual(len(w.events(name, 'olive')), 1)
                self.assertEqual(w.status(name)['confirmed'], ['olive'])

    def test_a_run_made_before_the_recovery_stays_unapproved_and_replays_so(self):
        w = World()
        for name in RECORDS:
            with self.subTest(record=name):
                restore = failing(w.olive)
                with self.assertRaises(PA.ApprovalNotConfirmed):
                    w.approve(name, w.olive)
                restore()
                before = w.run(name)
                w.approve(name, w.olive, 'complete')
                after = w.run(name)
                self.assertEqual((w.approved_in_run(name, before), w.approved_in_run(name, after)), (False, True))
                self.assertFalse(w.approved_in_run(name, {'result': w.s.get(repro.KIND, before['run_key']).payload['result']}))
                self.assertTrue(repro.replay(w.s, w.m.reg if name == 'fin' else w.m.detreg if name == 'det' else w.m.mreg if name in ('mkt', 'spec') else E.registry(),
                                             before['run_key']).ok)


class TestStatus(unittest.TestCase):
    def test_status_of_a_proposal_and_of_a_missing_version(self):
        w = World()
        for name, (kind, ev, err, approve, (mod, fn)) in RECORDS.items():
            with self.subTest(record=name):
                self.assertEqual(w.status(name), {'version': w.ver[name], 'recorded': [], 'confirmed': [], 'recorded_not_confirmed': []})
                self.assertIsNone(getattr(mod, fn)(w.s, 'NO-SUCH-VERSION'))
                w.approve(name, w.olive)
                self.assertEqual(w.status(name), {'version': w.ver[name], 'recorded': ['olive'], 'confirmed': ['olive'], 'recorded_not_confirmed': []})


if __name__ == '__main__':
    unittest.main()
