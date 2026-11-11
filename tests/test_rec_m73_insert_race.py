"""APG-M7.3 correction after the independent audit of APG-M7.2.
F-69  a record created during a checked act (a new overlapping finding) was caught only by a second check after the commit, and the act was reversed after the fact; a finding created just
      after that second check returned left the act standing.  The store could not hold "this query is unchanged" or "this record is still absent".
M7.3 adds those guards to the record store (RecordStorePort.atomic, ports.Guard; the reference store implements them under a lock), and the lifecycle commits each checked act together
with a query guard on every kind its check read, so a record added, changed or removed before the commit fails the commit, and nothing is recorded.  The second check and the reversal are gone.
The auditor's interleavings are reproduced deterministically at each boundary (submission, approval, start of work): a new overlapping finding inserted (1) between the check and the commit,
(2) right after the commit, where M7.2 ran its second check, and (3) after the call has returned.  In (1) the act is refused and nothing is recorded; in (2) and (3) the act had already
committed on exactly the sources it was checked against, the store's commit order shows the act first, and the new finding is a later change: the next checked act is refused and the next
run ends the submission or approval, as for any later change (F-64, F-65)."""
import sys, threading, time, unittest
from . import _path                                         # noqa: F401
from .helpers import make_env
from .helpers_rec import RecWorld
from .test_rec_m72_race import Base, EXPECT, Inject, STAGES, code
from apg import ports, tenancy
from apg.contracts.record_store_guard_contract import GUARD_CASES, run_guard_suite
from apg.det import findings as FD
from apg.ports import ConflictError, Guard
from apg.reference_impl import InMemoryRecordStore
from apg.rec import lifecycle as L


class AfterCommit:
    """Runs `change` once, right after the store has committed the batch that writes the recommendation (where M7.2 ran its second check)."""
    def __init__(self, w, change):
        self.w, self.change, self.fired = w, change, False

    def __enter__(self):
        store = self.w.s._store
        real = store.atomic

        def wrapped(ctx, ops):
            out = real(ctx, ops)
            if not self.fired and any(not isinstance(op, Guard) and op[0] == L.KIND for op in ops):
                self.fired = True
                self.change()
            return out
        store.atomic = wrapped
        return self

    def __exit__(self, *exc):
        del self.w.s._store.atomic
        return False


class TestTheAuditorsInterleavings(Base):
    def new_overlap(self, w, f, made):
        ref = w.s.get(FD.KIND, f).payload['signal']['evidence'][0]['ref']
        return lambda: made.append(w.finding(family='quality_defects', gross=900000, refs=[ref]))

    def order(self, w, kind, key, rev):
        return w.s._store._commits.index((w.s.ctx.tenant_id, kind, key, rev))

    def test_1_inserted_between_the_check_and_the_commit_is_refused_and_nothing_is_recorded(self):
        for stage in STAGES:
            for point in ('A', 'B'):
                with self.subTest(stage=stage, point=point):
                    w, f, g, rid = self.world(stage)
                    before, made = w.s.get(L.KIND, rid), []
                    with Inject(w, point, self.new_overlap(w, f, made)) as inj:
                        got = self.act(w, rid, stage)
                    self.assertTrue(inj.fired and made)
                    self.assertEqual(got, 'SOURCE_CHANGED')
                    self.assertEqual(w.s.get(L.KIND, rid).revision, before.revision)
                    self.assertEqual(w.s.get(L.KIND, rid).payload, before.payload)
                    self.assertNotIn((w.s.ctx.tenant_id, L.KIND, rid, before.revision + 1), w.s._store._commits)

    def check_later_change(self, w, rid, stage, made, before):
        r = w.s.get(L.KIND, rid)
        self.assertEqual((r.revision, r.payload['status']), (before.revision + 1, EXPECT[stage]))            # the act stands: it committed first
        self.assertLess(self.order(w, L.KIND, rid, r.revision), self.order(w, FD.KIND, made[0], 1))       # the store's commit order: the act, then the finding
        self.assertEqual(r.payload['history'][-1]['event'], 'status_change')
        if stage == 'submit':
            self.assertEqual(code(lambda: self.approve(w, rid)), 'SOURCE_CHANGED')                      # the next checked act sees the later change
        elif stage == 'approve':
            self.assertEqual(code(lambda: L.transition(w.owner2, w.clock, rid, 'in_progress')), 'SOURCE_CHANGED')
        w.run(as_of='2026-10-01')                                                                        # the next run ends what no longer matches
        r = L.get(w.s, rid)
        self.assertEqual(r['version'], 2)
        state = {'submit': ('submission', 'generated'), 'approve': ('approval', 'generated'), 'start': ('approval', 'in_progress')}[stage]
        self.assertEqual((r[state[0]]['state'], r['status']), ('ended', state[1]))

    def test_2_inserted_right_after_the_commit_is_a_later_change(self):
        for stage in STAGES:
            with self.subTest(stage=stage):
                w, f, g, rid = self.world(stage)
                before, made = w.s.get(L.KIND, rid), []
                with AfterCommit(w, self.new_overlap(w, f, made)) as inj:
                    got = self.act(w, rid, stage)
                self.assertTrue(inj.fired and made)
                self.assertIsNone(got)
                self.check_later_change(w, rid, stage, made, before)

    def test_3_inserted_after_the_call_returns_is_a_later_change(self):
        for stage in STAGES:
            with self.subTest(stage=stage):
                w, f, g, rid = self.world(stage)
                before, made = w.s.get(L.KIND, rid), []
                self.assertIsNone(self.act(w, rid, stage))
                self.new_overlap(w, f, made)()
                self.check_later_change(w, rid, stage, made, before)

    def test_there_is_no_check_after_the_commit_and_no_reversal(self):
        self.assertFalse(hasattr(L, '_guards'))
        w, f, g, rid = self.world('submit')
        calls = []
        real = L.source_check
        L.source_check = lambda *a, **k: calls.append(1) or real(*a, **k)
        try:
            self.assertIsNone(self.act(w, rid, 'submit'))
        finally:
            L.source_check = real
        self.assertEqual(len(calls), 1)                                                                  # the check before the commit, and nothing after it
        self.assertFalse([e for e in w.w.audit.read(w.s.ctx) if e.event_type in ('rec.act_reversed', 'rec.reversal_failed')])

    def test_the_commit_carries_every_guard_of_the_check(self):
        w, f, g, rid = self.world('submit')
        seen = []
        store = w.s._store
        real = store.atomic

        def wrapped(ctx, ops):
            seen.append(list(ops))
            return real(ctx, ops)
        store.atomic = wrapped
        try:
            self.assertIsNone(self.act(w, rid, 'submit'))
        finally:
            del store.atomic
        batch = [b for b in seen if any(not isinstance(op, Guard) and op[0] == L.KIND for op in b)]
        self.assertEqual(len(batch), 1)
        guards = [op for op in batch[0] if isinstance(op, Guard)]
        expect = []
        L.source_check(w.s, dict(L.get(w.s, rid), status='generated'), expect)
        self.assertEqual({(x.check, x.kind) for x in guards}, {(x.check, x.kind) for x in expect})
        self.assertEqual(len(guards), len(expect))
        self.assertEqual([op for op in batch[0] if not isinstance(op, Guard)][0][3], 1)                  # and the recommendation write keeps its expected revision


class TestConcurrentCallers(Base):
    """Real threads, with the interpreter switching between them as often as it can: whatever the interleaving, a submission that stands committed before every overlapping finding
    created alongside it, and one that was refused recorded nothing."""
    def test_threads_submitting_while_findings_are_created(self):
        old = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)
        outcomes = {'stood': 0, 'refused': 0}
        try:
            for round_ in range(12):
                w, f, g, rid = self.world('submit')
                ref = w.s.get(FD.KIND, f).payload['signal']['evidence'][0]['ref']
                made, got, go = [], [], threading.Barrier(2)

                def submit():
                    go.wait()
                    got.append(code(lambda: L.submit(w.owner2, w.clock, rid)))

                def create():
                    go.wait()
                    time.sleep(0.004 * (round_ % 6))                     # from at once to well after the submission
                    made.append(w.finding(family='quality_defects', gross=900000, refs=[ref]))
                ts = [threading.Thread(target=submit), threading.Thread(target=create)]
                for t in ts:
                    t.start()
                for t in ts:
                    t.join()
                commits = w.s._store._commits
                fpos = commits.index((w.s.ctx.tenant_id, FD.KIND, made[0], 1))
                r = w.s.get(L.KIND, rid)
                if got[0] is None:
                    outcomes['stood'] += 1
                    self.assertLess(commits.index((w.s.ctx.tenant_id, L.KIND, rid, r.revision)), fpos)
                else:
                    outcomes['refused'] += 1
                    self.assertIn(got[0], ('SOURCE_CHANGED', 'CONCURRENT_CHANGE'))
                    self.assertEqual(r.payload['status'], 'generated')
                    self.assertNotIn((w.s.ctx.tenant_id, L.KIND, rid, r.revision + 1), commits)
        finally:
            sys.setswitchinterval(old)
        self.assertEqual(sum(outcomes.values()), 12)


class NoGuards(InMemoryRecordStore):
    """A store that ignores guards: the guard contract must fail it."""
    def atomic(self, ctx, ops):
        return InMemoryRecordStore.atomic(self, ctx, [op for op in ops if not isinstance(op, Guard)])


class NoLock(InMemoryRecordStore):
    """A store whose batch is not indivisible (no lock, and a pause between checking and applying): the concurrency case must fail it."""
    def atomic(self, ctx, ops):
        return self._atomic(ctx, ops)

    def _guard(self, t, g):
        out = InMemoryRecordStore._guard(self, t, g)
        time.sleep(0.0005)
        return out


class TestTheStoreGuardContract(unittest.TestCase):
    def factory(self, cls=InMemoryRecordStore):
        def make():
            env, _ = make_env()
            env.store = cls(env.provider)
            return env
        return make

    def test_the_reference_store_passes_every_guard_case(self):
        res = run_guard_suite(self.factory())
        self.assertEqual(len(res), len(GUARD_CASES))
        self.assertEqual([r[0] for r in res if not r[2]], [], [r for r in res if not r[2]])
        self.assertEqual(len(res), 8)

    def test_a_store_that_ignores_guards_fails_the_contract(self):
        failed = {r[0] for r in run_guard_suite(self.factory(NoGuards)) if not r[2]}
        self.assertTrue({'RG-01', 'RG-02', 'RG-03', 'RG-04', 'RG-06', 'RG-07'} <= failed, failed)

    def test_a_store_whose_batch_is_not_indivisible_fails_the_concurrency_case(self):
        res = {r[0]: r for r in run_guard_suite(self.factory(NoLock))}
        self.assertFalse(res['RG-08'][2], res['RG-08'])

    def test_the_conflict_names_what_changed(self):
        env, _ = make_env()
        a = env.provider
        a._contract_register_session('t', 'T', 'u', (), 'human', 3600)
        ctx = a.resolve('t')
        env.store.put(ctx, 'finding', 'F1', {'v': 1}); env.store.put(ctx, 'finding', 'F2', {'v': 1})
        env.store.put(ctx, 'finding', 'F3', {'v': 1}); env.store.put(ctx, 'finding', 'F1', {'v': 2})
        with self.assertRaises(ConflictError) as cm:
            env.store.atomic(ctx, [Guard('query', 'finding', None, (('F1', 1), ('F2', 1), ('F9', 1))), Guard('revision', 'finding', 'F2', 4)])
        msg = str(cm.exception)
        self.assertIn("guard failed: finding query changed: added ['F3'], missing ['F9'], changed ['F1']", msg)
        self.assertIn('finding/F2: guarded at revision 4, current 1', msg)

    def test_the_scoped_store_screens_a_query_guard_filter_and_passes_guards_on(self):
        w = RecWorld()
        f = w.finding()
        rec = w.s.get(FD.KIND, f)
        with self.assertRaises(ports.TenantMismatch):
            w.s.atomic([Guard('query', FD.KIND, {'tenant_id': 'someone_else'}, ())])
        self.assertTrue([e for e in w.w.audit.read(w.s.ctx) if e.event_type == 'tenant_claim.refused'])
        w.s.atomic([Guard('query', FD.KIND, {'tenant_id': w.s.ctx.tenant_id, 'status': rec.payload['status']}, ((f, rec.revision),))])   # a matching claim is removed, not honoured
        w.s.atomic([Guard('revision', FD.KIND, f, rec.revision), Guard('query', FD.KIND, None, ((f, rec.revision),))])
        w.s.atomic([Guard('query', FD.KIND, {}, ((f, rec.revision),))])
        with self.assertRaises(ConflictError):
            w.s.atomic([Guard('revision', FD.KIND, f, rec.revision + 1)])
        odd = '{"tenant_id": "someone_else"}'                                     # a key is an identifier, never screened as a payload (as with get)
        self.assertIsNone(w.s.get(FD.KIND, odd))
        self.assertEqual(w.s.atomic([Guard('revision', FD.KIND, odd, 0)]), ())

    def test_reads_and_writes_from_many_threads_keep_the_store_whole(self):
        env, _ = make_env()
        env.provider._contract_register_session('t', 'T', 'u', (), 'human', 3600)
        ctx = env.provider.resolve('t')
        errors = []

        def writer(n):
            for i in range(200):
                try:
                    env.store.put(ctx, 'k', 'K%d-%d' % (n, i), {'v': i})
                    env.store.query(ctx, 'k')
                except Exception as e:                                      # pragma: no cover - reported as a failure
                    errors.append(repr(e))
        old = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)
        try:
            ts = [threading.Thread(target=writer, args=(n,)) for n in range(4)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
        finally:
            sys.setswitchinterval(old)
        self.assertEqual(errors, [])
        self.assertEqual(len(env.store.query(ctx, 'k')), 800)
        self.assertEqual(len(env.store._commits), 800)


if __name__ == '__main__':
    unittest.main()
