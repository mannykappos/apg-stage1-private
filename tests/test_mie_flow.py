"""MIE-1 observation-feed flow with test doubles (FL-03..FL-09, CT-08).  Ingestion driver -> feed adapter -> ObservationSourcePort double; the core validates and
returns receipts.  A feed failure stays on the adapter side."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_mie import EVAL, World, code, ob
from mie.adapters import feed as F
from mie.core import canon

MAPPING = {'SYN-SERIES-A': {'subject_id': 'SYN-ITEM-A', 'source_id': 'SYN-SRC-1', 'licence_ref': 'SYN-LIC-1', 'market': 'SYN-MARKET-1', 'unit': 'SYN-UNIT',
                            'observation_class': 'HISTORICAL_MOVEMENT', 'value_basis': 'INDEX'}}       # TEST-ONLY mapping
ROWS = [{'as_of': '2026-07-15', 'retrieved_at': '2026-07-16', 'value': {'mantissa': 10000, 'exponent': -2}},
        {'as_of': '2026-08-15', 'retrieved_at': '2026-08-16', 'value': {'mantissa': 10500, 'exponent': -2}},
        {'as_of': '2026-09-15', 'retrieved_at': '2026-09-16', 'value': {'mantissa': 11000, 'exponent': -2}}]


def flow():
    w = World()
    src = F.RefSource()
    src.load('T-A', 'SYN-SERIES-A', ROWS)
    return w, src, F.IngestionDriver(w.e, F.FeedAdapter(src, MAPPING))


class TestFlow(unittest.TestCase):
    def test_FL_03_end_to_end_the_driver_gets_per_item_receipts(self):
        """FL-03, CT-08 (what the double hands over meets the observation invariants)."""
        w, src, drv = flow()
        rep = drv.run('tA', 'T-A', w.pin, ['SYN-SERIES-A'], EVAL)
        self.assertEqual(rep['SYN-SERIES-A']['result']['counts'], {'ACCEPTED': 3, 'DUPLICATE': 0, 'REJECTED': 0})
        self.assertEqual(len(w.obs.d), 3)
        self.assertEqual([s['direction'] for s in w.signals()['signals'] if s['signal_id'] == 'SYN-SIG-LEVEL'], ['UP'])

    def test_FL_04_a_retried_batch_is_all_duplicates(self):
        """FL-04."""
        w, src, drv = flow()
        drv.run('tA', 'T-A', w.pin, ['SYN-SERIES-A'], EVAL)
        rep = drv.run('tA', 'T-A', w.pin, ['SYN-SERIES-A'], EVAL)
        self.assertEqual(rep['SYN-SERIES-A']['result']['counts'], {'ACCEPTED': 0, 'DUPLICATE': 3, 'REJECTED': 0})
        self.assertEqual(len(w.obs.d), 3)

    def test_FL_05_a_feed_failure_is_adapter_side_and_changes_nothing_in_the_core(self):
        """FL-05: unavailable, malformed and empty feeds: no core operation, no core state change, no feed error in the core vocabulary."""
        from mie.core import vocab as Y
        for mode in ('down', 'malformed', 'empty'):
            with self.subTest(mode=mode):
                w, src, drv = flow()
                before = (len(w.events()), dict(w.obs.d))
                src.mode = mode
                rep = drv.run('tA', 'T-A', w.pin, ['SYN-SERIES-A'], EVAL)
                self.assertFalse(rep['SYN-SERIES-A']['submitted'])
                self.assertEqual((len(w.events()), dict(w.obs.d)), before)
        self.assertFalse([c for c in Y.ERRORS + Y.REASONS if 'FEED' in c or 'SOURCE' in c])

    def test_FL_06_a_partial_feed_leaves_gaps_and_nothing_is_filled(self):
        """FL-06."""
        w = World()
        src = F.RefSource()
        src.load('T-A', 'SYN-SERIES-A', [ROWS[0]])
        F.IngestionDriver(w.e, F.FeedAdapter(src, MAPPING)).run('tA', 'T-A', w.pin, ['SYN-SERIES-A'], EVAL)
        v = w.signals()
        self.assertEqual([s['reason'] for s in v['signals'] if s['signal_id'] == 'SYN-SIG-LEVEL'], ['INSUFFICIENT_POINTS'])
        r = w.assess(need_by='2026-12-01')
        self.assertIn('STALE_EVIDENCE', r['qualification']['reasons'])
        self.assertEqual(len(w.obs.d), 1)

    def test_FL_07_signals_and_assessment_retrieve_nothing(self):
        """FL-07: a source that fails on any call is never called by get_signals or assess_timing."""
        w, src, drv = flow()
        drv.run('tA', 'T-A', w.pin, ['SYN-SERIES-A'], EVAL)
        calls = len(src.calls)
        src.mode = 'down'
        w.signals()
        w.assess(need_by='2026-12-01')
        self.assertEqual(len(src.calls), calls)

    def test_FL_08_a_licence_status_asserted_by_the_feed_never_grants_use(self):
        """FL-08 (SB-48)."""
        w = World()
        src = F.RefSource()
        mapping = {'SYN-SERIES-U': dict(MAPPING['SYN-SERIES-A'], source_id='SYN-SRC-K', licence_ref='SYN-LIC-3'),
                   'SYN-SERIES-A': MAPPING['SYN-SERIES-A']}
        src.load('T-A', 'SYN-SERIES-U', [dict(ROWS[0], licence_status='LICENSED')])
        src.load('T-A', 'SYN-SERIES-A', [dict(ROWS[1], licence_status='UNLICENSED')])
        rep = F.IngestionDriver(w.e, F.FeedAdapter(src, mapping)).run('tA', 'T-A', w.pin, ['SYN-SERIES-U', 'SYN-SERIES-A'], EVAL)
        self.assertEqual(rep['SYN-SERIES-U']['result']['receipts'][0]['code'], 'LICENCE_NOT_PERMITTED')
        self.assertEqual(rep['SYN-SERIES-A']['result']['receipts'][0]['status'], 'ACCEPTED')
        stored = list(w.obs.d.values())[0]
        self.assertEqual(stored['feed_licence_status'], 'UNLICENSED')
        self.assertEqual([i['state'] for i in w.signals()['evidence']['historical_movement']], ['stale'])

    def test_FL_09_a_batch_cannot_name_a_tenant(self):
        """FL-09, IS-02: the tenant is the verified context the driver supplies."""
        w = World()
        src = F.RefSource()
        src.load('T-A', 'SYN-SERIES-A', [ROWS[0]])
        mapping = {'SYN-SERIES-A': dict(MAPPING['SYN-SERIES-A'], tenant='T-B')}
        drv = F.IngestionDriver(w.e, F.FeedAdapter(src, mapping))
        self.assertEqual(code(lambda: drv.run('tA', 'T-A', w.pin, ['SYN-SERIES-A'], EVAL)), 'REQUEST_MALFORMED')
        self.assertEqual(w.obs.d, {})


if __name__ == '__main__':
    unittest.main()
