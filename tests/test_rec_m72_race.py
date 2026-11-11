"""APG-M7.2 correction after the independent audit of APG-M7.1.
F-68  the source-freshness check and the write of the recommendation were separate operations: a source change that landed between them (a time-of-check/time-of-use race) was not
      seen, and the act was recorded although its finding had just been dismissed.
A competing change is inserted deterministically at two points: A, right after the freshness check returns (lifecycle.source_check is wrapped); B, at the store, immediately before the batch
that writes the recommendation is applied (the record store's atomic batch is wrapped).  Every checked boundary (submission, approval, start of work) is tested at both points.
In M7.2, run against the delivered M7.1 code, 12 of these 18 tests failed or errored.
Changed in APG-M7.3 (F-69): the three tests of TestANewRecordDuringTheAct, which expected a record created during the act to be caught by a check after the commit and the act reversed, now
expect it to be refused with nothing recorded, because the commit now holds the whole query (see tests/test_rec_m73_insert_race.py); and four tests of TestTheGuardItself, which inspected
the M7.2 guard form (records re-written with their own payload), now inspect the M7.3 form (store Guards).  The other 11 tests are unchanged."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_rec import RecWorld
from apg import repro
from apg.det import findings as FD
from apg.ports import ConflictError, Guard
from apg.rec import inputs as IN, lifecycle as L, policy as RP

STAGES = ('submit', 'approve', 'start')
EXPECT = {'submit': 'awaiting_approval', 'approve': 'approved', 'start': 'in_progress'}


def code(fn):
    try:
        fn()
    except (L.RecError, IN.InputError, RP.RecPolicyError) as e:
        return e.code
    return None


class Inject:
    """Runs `change` once, at point A (after the freshness check returns) or B (at the store, just before the batch that writes the recommendation is applied)."""
    def __init__(self, w, point, change):
        self.w, self.point, self.change, self.fired = w, point, change, False

    def __enter__(self):
        if self.point == 'A':
            self.real = L.source_check

            def wrapped(*a, **k):
                out = self.real(*a, **k)
                if not self.fired:
                    self.fired = True
                    self.change()
                return out
            L.source_check = wrapped
        else:
            store = self.w.s._store
            self.real = store.atomic

            def wrapped(ctx, ops):
                if not self.fired and any(op[0] == L.KIND for op in ops):
                    self.fired = True
                    self.change()
                return self.real(ctx, ops)
            store.atomic = wrapped
        return self

    def __exit__(self, *exc):
        if self.point == 'A':
            L.source_check = self.real
        else:
            del self.w.s._store.atomic                  # back to the class method
        return False


class Base(unittest.TestCase):
    def world(self, stage):
        w = RecWorld()
        f = w.finding(family='quality_defects', gross=500000)
        ref = w.s.get(FD.KIND, f).payload['signal']['evidence'][0]['ref']
        g = w.finding(family='quality_defects', gross=300000, refs=[ref])          # rests on the same record: the same overlap component as f
        rid = w.ready(f)
        w.run()
        if stage in ('approve', 'start'):
            self.assertIsNone(code(lambda: L.submit(w.owner2, w.clock, rid)))
        if stage == 'start':
            self.assertIsNone(code(lambda: self.approve(w, rid)))
        return w, f, g, rid

    @staticmethod
    def approve(w, rid):
        t = L.approval_token(L.get(w.s, rid))
        L.approve(w.pm, w.clock, rid, t['version'], t['digest'], t['submission'], 'ok')

    def act(self, w, rid, stage):
        if stage == 'submit':
            return code(lambda: L.submit(w.owner2, w.clock, rid))
        if stage == 'approve':
            return code(lambda: self.approve(w, rid))
        return code(lambda: L.transition(w.owner2, w.clock, rid, 'in_progress'))

    @staticmethod
    def sources(w):
        return {(k, r.key): r.revision for k in (FD.KIND, IN.KIND, RP.POLICY_KIND) for r in w.s.query(k)}

    @staticmethod
    def changes(w, f, g, rid):
        return {
            'the finding is dismissed': lambda: FD.transition(w.rev, w.clock, f, 'dismissed', rationale='not real'),
            'the mandatory review is changed to not cleared': lambda: IN.record_review(w.creview, w.clock, rid, 'quality', 'not_cleared', 'fails the specification'),
            'an incremental cost is changed': lambda: IN.set_inputs(w.owner, w.clock, rid, incremental_costs=[{'component': 'qualification', 'cents': 400000, 'basis': 'a week'}]),
            'the expected benefit is changed': lambda: IN.set_inputs(w.owner, w.clock, rid, expected_benefit={'cents': 1, 'basis': 'revised'}),
            'the policy gets a further approval': lambda: RP.approve_policy(w.w.who('r2', 'zero_one', 'rhea', (RP.POLICY_ROLE,), ttl=10 ** 8), w.clock, w.policy['version'], 'second'),
            'the overlapping finding is dismissed': lambda: FD.transition(w.rev, w.clock, g, 'dismissed', rationale='duplicate'),
            'detection refreshes the finding without a material change': lambda: w.det.put(FD.KIND, f, dict(w.s.get(FD.KIND, f).payload, seen_count=9),
                                                                                          expected_revision=w.s.get(FD.KIND, f).revision),
        }


class TestTheRaceAtEachBoundary(Base):
    """F-68: a change to an existing source between the check and the write makes the whole batch fail; nothing is recorded."""
    def test_each_change_at_each_boundary_and_each_point_is_refused_and_nothing_is_recorded(self):
        n = 0
        for stage in STAGES:
            for point in ('A', 'B'):
                w, f, g, rid = self.world(stage)
                for what in self.changes(w, f, g, rid):
                    with self.subTest(stage=stage, point=point, change=what):
                        w, f, g, rid = self.world(stage)
                        before = w.s.get(L.KIND, rid)
                        with Inject(w, point, self.changes(w, f, g, rid)[what]) as inj:
                            got = self.act(w, rid, stage)
                        self.assertTrue(inj.fired)
                        self.assertEqual(got, 'SOURCE_CHANGED')
                        after = w.s.get(L.KIND, rid)
                        self.assertEqual(after.revision, before.revision)               # nothing was recorded, not even a reversal
                        self.assertEqual(after.payload, before.payload)
                        n += 1
        self.assertEqual(n, 3 * 2 * 7)

    def test_the_refusal_says_nothing_was_recorded_and_what_changed(self):
        w, f, g, rid = self.world('submit')
        with Inject(w, 'B', self.changes(w, f, g, rid)['the finding is dismissed']):
            with self.assertRaises(L.RecError) as cm:
                L.submit(w.owner2, w.clock, rid)
        msg = str(cm.exception)
        self.assertIn('a source changed while this was being decided, so nothing was recorded', msg)
        self.assertIn('the finding %s changed since the run' % f, msg)
        self.assertIn('Run the recommendation engine again', msg)
        ev = [e for e in w.w.audit.read(w.s.ctx) if e.resource == L.KIND + '/' + rid][-1]
        self.assertEqual((ev.event_type, ev.outcome), ('rec.refused', 'refused'))
        self.assertIn('nothing was recorded', ev.reason)
        self.assertFalse([e for e in w.w.audit.read(w.s.ctx) if e.event_type == 'rec.transition' and e.resource == L.KIND + '/' + rid])

    def test_the_competing_change_itself_is_kept(self):
        w, f, g, rid = self.world('approve')
        with Inject(w, 'A', self.changes(w, f, g, rid)['the finding is dismissed']):
            self.act(w, rid, 'approve')
        self.assertEqual(w.s.get(FD.KIND, f).payload['status'], 'dismissed')

    def test_after_the_refusal_a_fresh_run_decides_what_happens_next(self):
        w, f, g, rid = self.world('submit')
        with Inject(w, 'B', self.changes(w, f, g, rid)['the mandatory review is changed to not cleared']):
            self.assertEqual(self.act(w, rid, 'submit'), 'SOURCE_CHANGED')
        w.run(as_of='2026-10-01')
        self.assertIn('quality review did not clear the action', L.get(w.s, rid)['current']['constraints']['blocked_by'])
        self.assertEqual(self.act(w, rid, 'submit'), 'NOT_SUBMITTABLE')


class TestANewRecordDuringTheAct(Base):
    """A record created between the check and the commit fails the commit's query guard: the act is refused and nothing is recorded (F-69; it was reversed after the fact in M7.2)."""
    def new_overlap(self, w, f):
        ref = w.s.get(FD.KIND, f).payload['signal']['evidence'][0]['ref']
        return lambda: w.finding(family='quality_defects', gross=900000, refs=[ref])

    def test_a_new_overlapping_finding_at_each_boundary_and_point_is_refused_and_nothing_is_recorded(self):
        for stage in STAGES:
            for point in ('A', 'B'):
                with self.subTest(stage=stage, point=point):
                    w, f, g, rid = self.world(stage)
                    before = w.s.get(L.KIND, rid)
                    with Inject(w, point, self.new_overlap(w, f)) as inj:
                        got = self.act(w, rid, stage)
                    self.assertTrue(inj.fired)
                    self.assertEqual(got, 'SOURCE_CHANGED')
                    after = w.s.get(L.KIND, rid)
                    self.assertEqual(after.revision, before.revision)
                    self.assertEqual(after.payload, before.payload)
                    self.assertEqual([h.revision for h in w.s.history(L.KIND, rid)], list(range(1, before.revision + 1)))

    def test_the_refusal_says_what_the_new_record_changed(self):
        w, f, g, rid = self.world('submit')
        with Inject(w, 'B', self.new_overlap(w, f)):
            with self.assertRaises(L.RecError) as cm:
                L.submit(w.owner2, w.clock, rid)
        self.assertIn('a source changed while this was being decided, so nothing was recorded: a run now would give this recommendation different content', str(cm.exception))
        self.assertFalse([e for e in w.w.audit.read(w.s.ctx) if e.event_type in ('rec.transition', 'rec.act_reversed') and e.resource == L.KIND + '/' + rid])

    def test_a_new_record_elsewhere_during_the_act_is_a_concurrent_change_and_a_retry_succeeds(self):
        w, f, g, rid = self.world('submit')
        before = w.s.get(L.KIND, rid)
        with Inject(w, 'B', lambda: w.finding(gross=100, project='PRJ-002')):
            self.assertEqual(self.act(w, rid, 'submit'), 'CONCURRENT_CHANGE')
        self.assertEqual(w.s.get(L.KIND, rid).revision, before.revision)
        self.assertIsNone(self.act(w, rid, 'submit'))


class TestAChangeBeforeTheAct(Base):
    def test_a_change_before_the_act_is_refused_by_the_check_itself_and_nothing_is_recorded(self):
        for stage in STAGES:
            with self.subTest(stage=stage):
                w, f, g, rid = self.world(stage)
                before = w.s.get(L.KIND, rid)
                FD.transition(w.rev, w.clock, f, 'dismissed', rationale='not real')
                with self.assertRaises(L.RecError) as cm:
                    {'submit': lambda: L.submit(w.owner2, w.clock, rid), 'approve': lambda: self.approve(w, rid),
                     'start': lambda: L.transition(w.owner2, w.clock, rid, 'in_progress')}[stage]()
                self.assertEqual(cm.exception.code, 'SOURCE_CHANGED')
                self.assertIn('the recommendation no longer matches its sources', str(cm.exception))
                self.assertEqual(w.s.get(L.KIND, rid).revision, before.revision)
                ev = [e for e in w.w.audit.read(w.s.ctx) if e.resource == L.KIND + '/' + rid][-1]
                self.assertEqual(ev.event_type, 'rec.refused')


class TestUnchangedAndUnrelated(Base):
    def test_with_nothing_changed_every_act_goes_through_and_the_guards_write_nothing(self):
        w, f, g, rid = self.world('submit')
        src = self.sources(w)
        events = len(w.w.audit.read(w.s.ctx))
        for stage in STAGES:
            with self.subTest(stage=stage):
                r0 = w.s.get(L.KIND, rid).revision
                self.assertIsNone(self.act(w, rid, stage))
                self.assertEqual(L.get(w.s, rid)['status'], EXPECT[stage])
                self.assertEqual(w.s.get(L.KIND, rid).revision, r0 + 1)              # one revision per act: no reversal
        self.assertEqual(self.sources(w), src)                                      # no finding, input or policy got a new revision
        new = [e.event_type for e in w.w.audit.read(w.s.ctx)[events:]]
        self.assertEqual(new, ['rec.transition'] * 3)

    def test_a_concurrent_change_elsewhere_refuses_without_recording_and_a_retry_succeeds(self):
        w, f, g, rid = self.world('submit')
        other = w.finding(gross=100, project='PRJ-002')
        w.run()
        before = w.s.get(L.KIND, rid)
        change = lambda: FD.transition(w.rev, w.clock, other, 'dismissed', rationale='elsewhere')
        with Inject(w, 'B', change):
            self.assertEqual(self.act(w, rid, 'submit'), 'CONCURRENT_CHANGE')
        self.assertEqual(w.s.get(L.KIND, rid).revision, before.revision)
        self.assertIsNone(self.act(w, rid, 'submit'))                               # nothing about this recommendation changed: no run needed

    def test_the_message_for_a_concurrent_change_elsewhere(self):
        w, f, g, rid = self.world('submit')
        other = w.finding(gross=100, project='PRJ-002')
        w.run()
        with Inject(w, 'A', lambda: FD.transition(w.rev, w.clock, other, 'dismissed', rationale='elsewhere')):
            with self.assertRaises(L.RecError) as cm:
                L.submit(w.owner2, w.clock, rid)
        self.assertEqual(cm.exception.code, 'CONCURRENT_CHANGE')
        self.assertIn('or a record it depends on changed while this was being decided; nothing was recorded; read it again', str(cm.exception))

    def test_a_concurrent_write_of_the_recommendation_itself_is_still_a_concurrent_change(self):
        w, f, g, rid = self.world('submit')
        rec = w.s.get(L.KIND, rid)
        with Inject(w, 'B', lambda: w.svc.put(L.KIND, rid, dict(rec.payload, note='x'), expected_revision=rec.revision)):
            self.assertEqual(self.act(w, rid, 'submit'), 'CONCURRENT_CHANGE')
        self.assertEqual(w.s.get(L.KIND, rid).payload['status'], 'generated')

    def test_acts_that_are_not_source_checked_are_not_guarded(self):
        w, f, g, rid = self.world('submit')
        with Inject(w, 'B', lambda: FD.transition(w.rev, w.clock, f, 'dismissed', rationale='x')) as inj:
            self.assertIsNone(code(lambda: L.transition(w.owner2, w.clock, rid, 'deferred', rationale='later', until='2026-12-01')))
        self.assertTrue(inj.fired)
        self.assertEqual(L.get(w.s, rid)['status'], 'deferred')


class TestTheGuardItself(Base):
    def test_the_store_rules_the_guard_relies_on(self):
        """An op with the latest payload and its revision writes nothing; an op whose revision is no longer the latest fails the whole batch, and nothing in it is applied."""
        w, f, g, rid = self.world('submit')
        fr = w.s.get(FD.KIND, f)
        out = w.s.atomic([(FD.KIND, f, fr.payload, fr.revision)])
        self.assertEqual((out[0].revision, len(w.s.history(FD.KIND, f))), (fr.revision, fr.revision))
        FD.transition(w.rev, w.clock, f, 'dismissed', rationale='x')
        rec = w.s.get(L.KIND, rid)
        with self.assertRaises(ConflictError):
            w.s.atomic([(FD.KIND, f, fr.payload, fr.revision), (L.KIND, rid, dict(rec.payload, note='x'), rec.revision)])
        self.assertEqual(w.s.get(L.KIND, rid).revision, rec.revision)

    def test_the_batch_holds_every_record_the_check_read(self):
        w, f, g, rid = self.world('submit')
        guards = []
        self.assertEqual(L.source_check(w.s, L.get(w.s, rid), guards), [])
        self.assertTrue(all(isinstance(x, Guard) for x in guards))
        q = {x.kind: x.expect for x in guards if x.check == 'query'}
        self.assertEqual(set(q), {FD.KIND, IN.KIND})
        for kind in (FD.KIND, IN.KIND):
            self.assertEqual(set(q[kind]), {(r.key, r.revision) for r in w.s.query(kind)})
        self.assertTrue(all(x.target is None for x in guards if x.check == 'query'))
        rev = {(x.kind, x.target): x.expect for x in guards if x.check == 'revision'}
        run = w.s.get(repro.KIND, L.get(w.s, rid)['run_key'])
        self.assertEqual(rev[(repro.KIND, run.key)], run.revision)
        self.assertEqual(rev[(RP.POLICY_KIND, w.policy['version'])], w.s.get(RP.POLICY_KIND, w.policy['version']).revision)
        for key in (f, g):
            self.assertEqual(rev[(FD.KIND, key)], w.s.get(FD.KIND, key).revision)
        self.assertEqual(rev[(IN.KIND, rid)], w.s.get(IN.KIND, rid).revision)

    def test_a_record_that_is_absent_is_held_as_absent(self):
        """An absent record is held at revision 0: if it appears before the commit, the commit fails."""
        w = RecWorld()
        f = w.finding(gross=500000)
        w.run()                                                                     # no inputs were ever written for this recommendation
        rid = w.rid(f)
        self.assertIsNone(w.s.get(IN.KIND, rid))
        guards = []
        L.source_check(w.s, L.get(w.s, rid), guards)
        self.assertIn(Guard('revision', IN.KIND, rid, 0), guards)
        IN.set_inputs(w.owner, w.clock, rid, risks=['written after the check'])
        with self.assertRaises(ConflictError):
            w.s.atomic(guards)

    def test_a_guard_writes_nothing(self):
        w, f, g, rid = self.world('submit')
        guards = []
        L.source_check(w.s, L.get(w.s, rid), guards)
        n, src = len(w.s._store._commits), self.sources(w)
        self.assertEqual(w.s.atomic(guards), ())
        self.assertEqual((len(w.s._store._commits), self.sources(w)), (n, src))

    def test_a_guard_for_a_record_read_twice_at_different_revisions_refuses(self):
        w, f, g, rid = self.world('submit')
        guards = []
        L.source_check(w.s, L.get(w.s, rid), guards)
        FD.transition(w.rev, w.clock, f, 'dismissed', rationale='x')
        guards.append(Guard('revision', FD.KIND, f, w.s.get(FD.KIND, f).revision))
        with self.assertRaises(ConflictError):
            w.s.atomic(guards)


if __name__ == '__main__':
    unittest.main()
