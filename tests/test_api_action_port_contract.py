"""The ProjectActionPort contract (EDR-31): the in-memory reference passes, every deliberately faulty port is caught for the intended reason, and every case is hit by at least one fault."""
import unittest
from . import _path                                         # noqa: F401
from apg.api import contracts_m9 as C, faulty_m9 as F, reference_m9 as REF


class TestActionPortContract(unittest.TestCase):
    def test_every_case_passes_on_the_reference(self):
        res = C.run_all(REF.action_env())
        self.assertEqual([r for r in res if not r[3]], [])
        self.assertEqual(len(res), 14)

    def test_every_faulty_port_is_caught_for_the_intended_reason(self):
        self.assertEqual(len(F.FAULTS), 16)
        for fid, (text, factory, expect) in F.FAULTS.items():
            with self.subTest(fault=fid):
                failed = {r[1] for r in C.run_all(factory) if not r[3]}
                self.assertTrue(set(expect) <= failed, f'{fid} {text}: failed {sorted(failed)}')

    def test_every_case_is_hit_by_at_least_one_fault(self):
        hit = set()
        for _, (_, _, expect) in F.FAULTS.items():
            hit |= set(expect)
        self.assertEqual({c[1] for c in C.CASES} - hit, set())

    def test_the_reference_port_drives_the_boundary_end_to_end(self):
        from .test_api_approval_boundary import Base
        from apg.api import approval_boundary as AB
        from apg.det import findings as FD
        b = Base()
        b.setUp()
        port = REF.InMemoryActionPort(b.m.w.provider)
        req = b.req()
        res = AB.request_approval(b.m.approver, port, b.m.clock, req)
        self.assertEqual((res['status'], res['code']), ('refused', 'NOT_FOUND'))          # nothing granted: refused, and it looks like a missing finding
        port._contract_grant('zero_one', 'abby', 'PRJ-001', 'view')
        res = AB.request_approval(b.m.approver, port, b.m.clock, b.req())
        self.assertEqual((res['status'], res['code']), ('refused', 'NOT_FOUND'))          # view alone does not allow approval
        port._contract_grant('zero_one', 'abby', 'PRJ-001', 'approve')
        okreq = b.req()
        res = AB.request_approval(b.m.approver, port, b.m.clock, okreq)
        self.assertEqual((res['status'], res['code']), ('approved', 'OK'))
        self.assertTrue(FD.approval_current(b.record()))
        port._contract_revoke_grant('zero_one', 'abby', 'PRJ-001', 'approve')
        again = AB.request_approval(b.m.approver, port, b.m.clock, okreq)
        self.assertEqual((again['status'], again['code']), ('refused', 'NOT_FOUND'))      # the revoked person is not served the old answer


if __name__ == '__main__':
    unittest.main()
