"""MIE-1.1 corrections after the independent audit of MIE-1.
  F-70 (auditor F-MIE1-01): an unexpected exception at the commit fails closed (INTERNAL_ERROR_FAIL_CLOSED, one attempted FAILED event, nothing stored); an audit sink that
       fails in any way is AUDIT_UNAVAILABLE; a batch of observations is stored all or nothing.
  F-71 (auditor F-MIE1-02): an observation may supersede only an observation of the same series (subject, market, unit, class, basis), source, date and kind; anything else
       is rejected with the field named and changes no existing evidence.
Every test in the first four classes fails or errors against the delivered MIE-1 code.  TestEdgesOfTheNewCode guards an edge of the new code that the MIE-1.1
mutation run found untested; it passes on MIE-1 as well."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_mie import EVAL, World, code, ev, ob, series, UP
from mie.core import canon, reference as R, signals as S
from mie.core.ports import StoreFailure
from mie.packs import synthetic as SP


def boom(*a, **k):
    raise RuntimeError('unexpected store error')


def last(w, tenant='T-A', n=2):
    return [(e['operation'], e['outcome'], e['code']) for e in w.events(tenant)[-n:]]


def state(w):
    return canon.dumps({'obs': sorted(w.obs.d), 'packs': sorted(w.reg.packs), 'acts': sorted(w.reg.acts), 'withdrawn': sorted(w.reg.withdrawn), 'res': sorted(w.res.d)})


COMMITS = {
    'register_pack': (lambda w: setattr(w.reg, 'put', boom), lambda w: w.e.register_pack('tA', SP.pack_bytes('9.9.9')), 'T-A'),
    'activate_pack': (lambda w: setattr(w.reg, 'activate', boom), lambda w: w.activate('tB', w.pin), 'T-B'),
    'withdraw_pack': (lambda w: setattr(w.reg, 'withdraw', boom), lambda w: w.e.withdraw_pack('tA', w.pin, 'r'), 'T-A'),
    'submit_observations': (lambda w: (setattr(w.obs, 'append', boom), setattr(w.obs, 'append_batch', boom)), lambda w: w.submit(series(UP)), 'T-A'),
    'assess_timing': (lambda w: setattr(w.res, 'put', boom), lambda w: w.assess(), 'T-A'),
}


class TestF70UnexpectedCommitErrors(unittest.TestCase):
    def test_an_unexpected_store_exception_at_the_commit_fails_closed_with_a_FAILED_event(self):
        """F-70: for every operation that commits, a RuntimeError from the store is INTERNAL_ERROR_FAIL_CLOSED, after ACCEPTED one FAILED event is attempted and
        recorded, no result is returned and nothing is stored."""
        for op, (sabotage, call, tenant) in COMMITS.items():
            with self.subTest(operation=op):
                w = World()
                if op == 'assess_timing':
                    w.submit(series(UP))
                before = state(w)
                sabotage(w)
                self.assertEqual(code(lambda: call(w)), 'INTERNAL_ERROR_FAIL_CLOSED')
                self.assertEqual(last(w, tenant), [(op, 'ACCEPTED', None), (op, 'FAILED', 'INTERNAL_ERROR_FAIL_CLOSED')])
                self.assertEqual(state(w), before)

    def test_the_FAILED_event_is_attempted_once_and_its_own_failure_does_not_change_the_answer(self):
        """F-70: if the audit sink also fails when the FAILED event is attempted, the caller still gets INTERNAL_ERROR_FAIL_CLOSED, never a raw exception."""
        w = World()
        w.reg.put = boom
        w.aud.fail_after = 1                                   # the ACCEPTED event is recorded; the FAILED event cannot be
        self.assertEqual(code(lambda: w.e.register_pack('tA', SP.pack_bytes('9.9.8'))), 'INTERNAL_ERROR_FAIL_CLOSED')
        self.assertEqual(last(w, n=1), [('register_pack', 'ACCEPTED', None)])

    def test_an_audit_sink_that_fails_in_any_way_is_AUDIT_UNAVAILABLE_with_no_state_change(self):
        """F-70: a RuntimeError from the audit sink is treated as an unavailable sink, for a commit, a read and a refusal."""
        w = World()
        before = state(w)

        def bad(tenant, event):
            raise RuntimeError('unexpected audit error')
        w.aud.append = bad
        self.assertEqual(code(lambda: w.submit(series(UP))), 'AUDIT_UNAVAILABLE')
        self.assertEqual(code(lambda: w.e.describe('tA')), 'AUDIT_UNAVAILABLE')
        self.assertEqual(code(lambda: w.e.get_result('tA', 'bad')), 'AUDIT_UNAVAILABLE')
        self.assertEqual(code(lambda: w.e.register_pack('tA', SP.pack_bytes('9.9.7'))), 'AUDIT_UNAVAILABLE')
        self.assertEqual(state(w), before)


class TestF70AtomicBatch(unittest.TestCase):
    def test_a_store_failure_part_way_through_a_batch_stores_nothing(self):
        """F-70: the batch is written in one store call that is all or nothing; a failure at the second of three items leaves no observation, and a retry stores all."""
        w = World()
        w.obs.fail_at_item = 1
        self.assertEqual(code(lambda: w.submit(series(UP))), 'STORE_UNAVAILABLE')
        self.assertEqual(w.obs.d, {})
        self.assertEqual(last(w), [('submit_observations', 'ACCEPTED', None), ('submit_observations', 'FAILED', 'STORE_UNAVAILABLE')])
        w.obs.fail_at_item = None
        self.assertEqual(w.submit(series(UP))['counts']['ACCEPTED'], 3)
        self.assertEqual(len(w.obs.d), 3)

    def test_the_reference_batch_store_contract(self):
        """CT-03 for the batch write: all or nothing, duplicates left as they are, scoped by tenant, copies stored."""
        s = R.RefObservations()
        o = {'subject_id': 'S', 'v': 1}
        self.assertEqual(s.append_batch('T', [('OB-1', o), ('OB-2', o), ('OB-1', o)]), ['stored', 'stored', 'duplicate'])
        o['v'] = 9
        self.assertEqual(s.get('T', 'OB-1')['v'], 1)
        self.assertEqual(s.append_batch('T', [('OB-1', o), ('OB-3', o)]), ['duplicate', 'stored'])
        self.assertIsNone(s.get('U', 'OB-1'))
        s.fail_at_item = 1
        with self.assertRaises(StoreFailure):
            s.append_batch('T', [('OB-4', o), ('OB-5', o)])
        self.assertIsNone(s.get('T', 'OB-4'))
        s.fail_at_item, s.fail_writes = None, True
        with self.assertRaises(StoreFailure):
            s.append_batch('T', [('OB-6', o)])
        self.assertIsNone(s.get('T', 'OB-6'))


BASE = ob('2026-09-01', 10000)
INCOMPATIBLE = {
    'another subject': dict(subject_id='SYN-ITEM-B'),
    'another subject in scope (the conversion series)': dict(subject_id='SYN-RATE-1', unit='SYN-RATE-UNIT', observation_class='CURRENT_REFERENCE'),
    'another unit': dict(unit='SYN-UNIT-2'),
    'another market': dict(market='SYN-MARKET-2'),
    'another value basis': dict(value_basis='ASKING'),
    'another observation class and value basis': dict(observation_class='CURRENT_REFERENCE', value_basis='ASKING'),
    'another observation class only': dict(observation_class='CURRENT_REFERENCE'),
    'another source and value basis': dict(source_id='SYN-SRC-2', value_basis='ASKING'),
    'another source only': dict(source_id='SYN-SRC-W', licence_ref='SYN-LIC-4'),
    'another date': dict(as_of='2026-09-02', retrieved_at='2026-09-02'),
}


class TestF71Supersession(unittest.TestCase):
    def test_an_incompatible_supersession_is_rejected_and_changes_no_evidence(self):
        """F-71: every incompatible correction is REJECTED with the field supersedes, nothing is stored, and the signal view is byte-identical before and after."""
        for name, change in INCOMPATIBLE.items():
            with self.subTest(case=name):
                w = World()
                w.submit([ob('2026-07-15', 9000)])
                first = w.submit([BASE])['receipts'][0]['observation_id']
                before_view, before_obs = canon.dumps(w.signals()), dict(w.obs.d)
                r = w.submit([dict(ob('2026-09-01', 12000), supersedes=first, **change)])['receipts'][0]
                self.assertEqual((r['status'], r['code'], r['fields']), ('REJECTED', 'OBSERVATION_INVALID', ['supersedes']))
                self.assertEqual(w.obs.d, before_obs)
                self.assertEqual(canon.dumps(w.signals()), before_view)

    def test_a_level_cannot_supersede_an_event_or_the_reverse(self):
        w = World()
        e_id = w.submit([ev('2026-09-01', 'SYN-AVAIL-DOWN')])['receipts'][0]['observation_id']
        r = w.submit([dict(ob('2026-09-01', 100), supersedes=e_id)])['receipts'][0]
        self.assertEqual((r['status'], r['fields']), ('REJECTED', ['supersedes']))
        l_id = w.submit([BASE])['receipts'][0]['observation_id']
        r = w.submit([dict(ev('2026-09-01', 'SYN-AVAIL-UP'), supersedes=l_id)])['receipts'][0]
        self.assertEqual((r['status'], r['fields']), ('REJECTED', ['supersedes']))

    def test_a_true_correction_is_accepted_also_within_one_batch(self):
        """The control: same series, source, date and kind.  The original becomes history and is kept for replay; inside one batch the same rule applies."""
        w = World()
        first = w.submit([BASE])['receipts'][0]['observation_id']
        self.assertEqual(w.submit([dict(ob('2026-09-01', 12000), supersedes=first)])['receipts'][0]['status'], 'ACCEPTED')
        states = {i['observation_id']: i['state'] for i in w.signals()['evidence']['historical_movement']}
        self.assertEqual(states[first], 'history')
        w2 = World()
        a = ob('2026-09-03', 100)
        a_id = 'OB-' + canon.digest(a)
        rs = w2.submit([a, dict(ob('2026-09-03', 101), supersedes=a_id), dict(ob('2026-09-03', 102, subject_id='SYN-ITEM-B'), supersedes=a_id)])['receipts']
        self.assertEqual([x['status'] for x in rs], ['ACCEPTED', 'ACCEPTED', 'REJECTED'])

    def test_an_incompatible_link_already_in_a_store_never_hides_evidence(self):
        """F-71, defence in depth: classification ignores a supersedes link that is not a correction of the same series, source, date and kind, so an observation
        written by an older or faulty store path cannot remove evidence."""
        old = dict(BASE, observation_class='HISTORICAL_MOVEMENT')
        stray = dict(ob('2026-09-01', 5, subject_id='SYN-ITEM-B'), supersedes='OB-OLD')
        doc = SP.pack()
        states = S.classify(doc, {'OB-OLD': old, 'OB-STRAY': stray}, EVAL)
        self.assertEqual(states['OB-OLD'], ('ELIGIBLE', None))
        good = dict(ob('2026-09-01', 7), supersedes='OB-OLD')
        self.assertEqual(S.classify(doc, {'OB-OLD': old, 'OB-NEW': good}, EVAL)['OB-OLD'], ('HISTORY', None))
        self.assertTrue(S.corrects(good, old))
        self.assertFalse(S.corrects(stray, old))



class TestEdgesOfTheNewCode(unittest.TestCase):
    def test_a_supersedes_value_that_is_not_text_is_rejected_not_an_internal_error(self):
        """The split of the supersedes check in MIE-1.1 keeps the shape check first: a number, a list or text without the OB- prefix is REJECTED with the field
        named, before any store lookup."""
        w = World()
        for bad in (5, ['OB-x'], {'id': 1}, 'X-1', True):
            with self.subTest(value=bad):
                r = w.submit([dict(ob('2026-09-01', 100), supersedes=bad)])['receipts'][0]
                self.assertEqual((r['status'], r['fields']), ('REJECTED', ['supersedes']))


if __name__ == '__main__':
    unittest.main()
