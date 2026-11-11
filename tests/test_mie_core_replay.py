"""MIE-1 reproducibility: result identity, byte-for-byte replay from stored evidence, drift reports (RP-01..RP-06, CT-05)."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_mie import EVAL, World, code, ob, scenario, series, UP
from mie.core import canon, timing as T, vocab as Y
from mie.packs import synthetic as SP


class TestReplay(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.w.submit(series(UP))
        self.r = self.w.assess(need_by='2026-12-01', scenarios=[scenario()])

    def test_RP_01_the_same_request_and_pins_replay_byte_identically(self):
        """RP-01, CT-05 (content-addressed, idempotent store)."""
        rep = self.w.e.replay_result('tA', self.r['result_id'])
        self.assertTrue(rep['identical'])
        self.assertEqual(rep['stored_digest'], rep['replayed_digest'])
        again = self.w.assess(need_by='2026-12-01', scenarios=[scenario()])
        self.assertEqual(canon.dumps(again), canon.dumps(self.r))
        self.assertEqual(len(self.w.res.d), 1)
        self.assertEqual(self.w.e.get_result('tA', self.r['result_id']), self.r)

    def test_RP_02_the_result_id_changes_with_any_pinned_input(self):
        """RP-02."""
        rid = self.r['result_id']
        req = self.r['request']
        pin = self.r['pack']
        ev = self.r['evidence_set']
        self.assertEqual(T.result_id(pin, req, ev), rid)
        self.assertNotEqual(T.result_id(dict(pin, pack_hash='f' * 64), req, ev), rid)
        self.assertNotEqual(T.result_id(pin, dict(req, evaluation_date='2026-10-01'), ev), rid)
        self.assertNotEqual(T.result_id(pin, req, ev[:-1]), rid)
        self.assertNotEqual(T.result_id(pin, req, ev[:-1] + ['OB-' + '0' * 64]), rid)
        old = dict(Y.VERSIONS)
        try:
            Y.VERSIONS['core'] = 'mie-core-9.9.9'
            self.assertNotEqual(T.result_id(pin, req, ev), rid)
        finally:
            Y.VERSIONS.clear()
            Y.VERSIONS.update(old)

    def test_RP_03_later_observations_do_not_change_a_replay(self):
        """RP-03 (SB-15)."""
        self.w.submit([ob('2026-09-25', 20000), ob('2026-09-26', 1)])
        rep = self.w.e.replay_result('tA', self.r['result_id'])
        self.assertTrue(rep['identical'])
        new = self.w.assess(need_by='2026-12-01', scenarios=[scenario()])
        self.assertNotEqual(new['result_id'], self.r['result_id'])

    def test_RP_04_missing_stored_evidence_gives_REPLAY_EVIDENCE_UNAVAILABLE(self):
        """RP-04."""
        oid = self.r['evidence_set'][0]
        del self.w.obs.d[('T-A', oid)]
        self.assertEqual(code(lambda: self.w.e.replay_result('tA', self.r['result_id'])), 'REPLAY_EVIDENCE_UNAVAILABLE')

    def test_a_missing_pack_gives_REPLAY_PACK_UNAVAILABLE(self):
        """MIE-R-37."""
        self.w.reg.packs.clear()
        self.assertEqual(code(lambda: self.w.e.replay_result('tA', self.r['result_id'])), 'REPLAY_PACK_UNAVAILABLE')

    def test_RP_05_replay_under_another_pack_is_a_drift_report_and_the_original_stays(self):
        """RP-05."""
        doc2 = SP.pack('1.0.1')
        doc2['signals'][0]['params']['threshold'] = {'num': 1, 'den': 5}
        pin2 = self.w.e.register_pack('tA', canon.dumps(doc2))['pin']
        stored = self.w.e.get_result('tA', self.r['result_id'])
        rep = self.w.e.replay_result('tA', self.r['result_id'], pin2)
        self.assertTrue(rep['drift_report'])
        self.assertIn('$.pack.pack_hash', rep['differences'])
        self.assertTrue(any('direction' in d for d in rep['differences']))
        self.assertNotEqual(rep['replayed_result_id'], self.r['result_id'])
        self.assertEqual(self.w.e.get_result('tA', self.r['result_id']), stored)
        self.assertEqual(code(lambda: self.w.e.replay_result('tA', self.r['result_id'], dict(pin2, pack_hash='0' * 64))), 'REPLAY_PACK_UNAVAILABLE')
        self.assertEqual(code(lambda: self.w.e.replay_result('tA', self.r['result_id'], {'pack_id': 'x'})), 'REQUEST_MALFORMED')

    def test_a_stored_result_under_another_core_version_replays_as_drift(self):
        """RP-05 (core version): a result whose recorded versions differ from this core's is reported as drift, never as identical."""
        key = ('T-A', self.r['result_id'])
        self.w.res.d[key]['versions'] = dict(self.w.res.d[key]['versions'], core='mie-core-0.9.0')
        rep = self.w.e.replay_result('tA', self.r['result_id'])
        self.assertTrue(rep['drift_report'])
        self.assertIn('$.versions.core', rep['differences'])

    def test_RP_06_canonical_serialisation_is_stable(self):
        """RP-06 (with PK-20): the same record serialises to the same bytes across runs and key orders; floats and non-NFC text have no canonical form."""
        a = canon.dumps(self.r)
        b = canon.dumps(canon.loads(a))
        self.assertEqual(a, b)
        self.assertEqual(canon.dumps(dict(reversed(list(self.r.items())))), a)
        for bad in ({'x': 1.0}, {'x': 'é'}, {1: 2}, {'x': {1}}, {'x': b'b'}):
            with self.assertRaises(canon.CanonError):
                canon.dumps(bad)

    def test_result_identifiers_are_checked_and_scoped(self):
        """OP-10, OP-11: a malformed identifier is REQUEST_MALFORMED; an unknown one is NOT_FOUND."""
        for bad in ('RS-x', 'XX-' + 'a' * 64, None, 5):
            self.assertEqual(code(lambda: self.w.e.get_result('tA', bad)), 'REQUEST_MALFORMED')
            self.assertEqual(code(lambda: self.w.e.replay_result('tA', bad)), 'REQUEST_MALFORMED')
        self.assertEqual(code(lambda: self.w.e.get_result('tA', 'RS-' + '0' * 64)), 'NOT_FOUND')


if __name__ == '__main__':
    unittest.main()
