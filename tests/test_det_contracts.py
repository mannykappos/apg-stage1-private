"""The NotificationPort contract (EDR-10): the in-memory reference passes, every deliberately faulty port is caught for the intended reason, and every case is hit by at least one fault."""
import unittest
from . import _path                                         # noqa: F401
from apg.det import contracts_m5 as C, faulty_m5 as F, reference_m5 as REF


class TestNotificationContract(unittest.TestCase):
    def test_every_case_passes_on_the_reference(self):
        res = C.run_all(REF.notify_env())
        self.assertEqual([r for r in res if not r[3]], [])
        self.assertEqual(len(res), 12)

    def test_every_faulty_port_is_caught_for_the_intended_reason(self):
        self.assertEqual(len(F.FAULTS), 15)
        for fid, (text, factory, expect) in F.FAULTS.items():
            with self.subTest(fault=fid):
                failed = {r[1] for r in C.run_all(factory) if not r[3]}
                self.assertTrue(set(expect) <= failed, f'{fid} {text}: failed {sorted(failed)}')

    def test_every_case_is_hit_by_at_least_one_fault(self):
        hit = set()
        for _, (_, _, expect) in F.FAULTS.items():
            hit |= set(expect)
        self.assertEqual({c[1] for c in C.CASES} - hit, set())

    def test_the_pipeline_never_double_delivers_through_a_port_that_keeps_the_dedup_promise(self):
        from .helpers_det import det_world, inv
        from apg.det import findings as FD
        m = det_world()
        m.invoices(inv('INV-1', ex='5300000', cc='CC-01'))
        m.reconcile()
        m.ingest(m.detect())
        for _ in range(3):
            FD.flush_notifications(m.svc, m.clock, m.notifier)
        self.assertEqual(len(m.notifier._contract_delivered('zero_one')), 1)


if __name__ == '__main__':
    unittest.main()
