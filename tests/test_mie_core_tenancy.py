"""MIE-1 tenancy (IS-01..IS-06, CT-02, CT-07): the tenant is only the verified context; another tenant's record is indistinguishable from a missing one."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_mie import EVAL, World, code, ob, scenario, series, UP
from mie.core import canon, reference as R
from mie.core.ports import ContextInvalid, ContextMissing
from mie.packs import synthetic as SP


def calls(w, token):
    pin = w.pin
    return {'describe': lambda: w.e.describe(token), 'validate_pack': lambda: w.e.validate_pack(token, SP.pack_bytes()),
            'register_pack': lambda: w.e.register_pack(token, SP.pack_bytes()), 'get_pack': lambda: w.e.get_pack(token, pin),
            'withdraw_pack': lambda: w.e.withdraw_pack(token, pin, 'r'), 'activate_pack': lambda: w.e.activate_pack(token, pin, 'APR'),
            'submit_observations': lambda: w.e.submit_observations(token, pin, [ob('2026-09-01', 1)]),
            'get_signals': lambda: w.e.get_signals(token, pin, 'SYN-ITEM-A', EVAL),
            'assess_timing': lambda: w.e.assess_timing(token, pin, 'SYN-ITEM-A', 'BUY', {}, [], EVAL),
            'replay_result': lambda: w.e.replay_result(token, 'RS-' + '0' * 64), 'get_result': lambda: w.e.get_result(token, 'RS-' + '0' * 64),
            'list_audit': lambda: w.e.list_audit(token, 1, 10)}


class TestTenancy(unittest.TestCase):
    def test_IS_01_every_operation_refuses_a_missing_forged_or_expired_context(self):
        """IS-01, AU-09 (no tenant audit event for an unattributable refusal), SB-07, SB-37."""
        w = World()
        before = {t: len(c) for t, c in w.aud.chains.items()}
        for token, want in ((None, 'TENANT_CONTEXT_MISSING'), ('', 'TENANT_CONTEXT_MISSING'), ('forged', 'TENANT_CONTEXT_INVALID'), ('tOld', 'TENANT_CONTEXT_INVALID'),
                            (('T-A',), 'TENANT_CONTEXT_INVALID')):
            for name, fn in calls(w, token).items():
                with self.subTest(token=token, operation=name):
                    self.assertEqual(code(fn), want)
        self.assertEqual({t: len(c) for t, c in w.aud.chains.items()}, before)

    def test_IS_02_a_tenant_field_in_a_payload_is_refused(self):
        """IS-02, FL-09."""
        w = World()
        self.assertEqual(code(lambda: w.submit([ob('2026-09-01', 1, tenant_id='T-B')])), 'REQUEST_MALFORMED')
        self.assertEqual(code(lambda: w.submit([dict(ob('2026-09-01', 1), adapter_notes={'tenant': 'T-B'})])), 'REQUEST_MALFORMED')
        self.assertEqual(code(lambda: w.assess(scenarios=[dict(scenario(), Tenant='T-B')])), 'REQUEST_MALFORMED')
        self.assertEqual(code(lambda: w.e.assess_timing('tA', w.pin, 'SYN-ITEM-A', 'BUY', {'tenant_ref': 'x'}, [], EVAL)), 'REQUEST_MALFORMED')
        self.assertEqual(w.obs.d, {})
        self.assertEqual(w.events()[-1]['code'], 'REQUEST_MALFORMED')

    def test_IS_03_another_tenants_records_look_missing(self):
        """IS-03 (SB-20): the same code and shape as a missing record."""
        w = World()
        w.submit(series(UP))
        r = w.assess()
        w.activate('tB', w.pin)
        missing_rid = 'RS-' + '1' * 64
        self.assertEqual(code(lambda: w.e.get_result('tB', r['result_id'])), code(lambda: w.e.get_result('tB', missing_rid)))
        self.assertEqual(code(lambda: w.e.get_result('tB', r['result_id'])), 'NOT_FOUND')
        self.assertEqual(code(lambda: w.e.replay_result('tB', r['result_id'])), 'NOT_FOUND')
        sb = w.e.get_signals('tB', w.pin, 'SYN-ITEM-A', EVAL)
        self.assertEqual([s['reason'] for s in sb['signals'] if s['signal_id'] == 'SYN-SIG-LEVEL'], ['NO_EVIDENCE'])
        w2 = World(activate=False)
        w2.activate('tA', w2.pin)
        empty = w2.e.get_signals('tA', w2.pin, 'SYN-ITEM-A', EVAL)
        self.assertEqual(canon.dumps(sb['signals']), canon.dumps(empty['signals']))
        w3 = World()
        self.assertEqual(code(lambda: w3.e.assess_timing('tB', w3.pin, 'SYN-ITEM-A', 'BUY', {}, [], EVAL)), 'PACK_NOT_ACTIVE')
        self.assertEqual(code(lambda: w3.e.assess_timing('tB', dict(w3.pin, pack_version='never'), 'SYN-ITEM-A', 'BUY', {}, [], EVAL)), 'PACK_NOT_ACTIVE')

    def test_IS_04_a_licence_for_one_tenant_is_not_a_licence_for_another(self):
        """IS-04 (SB-32): use needs the tenant's own activation of the pack that holds the licence record."""
        w = World()
        self.assertEqual(code(lambda: w.e.submit_observations('tB', w.pin, [ob('2026-09-01', 1)])), 'PACK_NOT_ACTIVE')
        self.assertEqual(code(lambda: w.e.get_signals('tB', w.pin, 'SYN-ITEM-A', EVAL)), 'PACK_NOT_ACTIVE')

    def test_IS_05_returned_values_are_independent_copies(self):
        """IS-05, CT-03, CT-05."""
        w = World()
        w.submit(series(UP))
        r = w.assess()
        r['outcome'] = 'TAMPERED'
        r['signals'].clear()
        again = w.e.get_result('tA', r['result_id'])
        self.assertNotEqual(again['outcome'], 'TAMPERED')
        self.assertTrue(again['signals'])
        p = w.e.get_pack('tA', w.pin)
        p['pack']['field_label'] = 'X'
        self.assertEqual(w.e.get_pack('tA', w.pin)['pack']['field_label'], 'TEST FIELD (SYNTHETIC)')
        o = w.obs.get('T-A', next(iter(w.obs.d))[1])
        o['value'] = 0
        self.assertNotEqual(w.obs.get('T-A', next(iter(w.obs.d))[1])['value'], 0)

    def test_IS_06_stored_keys_are_tenant_scoped(self):
        """IS-06."""
        w = World()
        w.activate('tB', w.pin)
        w.submit(series(UP))
        w.submit(series(UP), token='tB')
        w.assess()
        w.assess(token='tB')
        self.assertEqual({k[0] for k in w.obs.d}, {'T-A', 'T-B'})
        self.assertEqual({k[0] for k in w.res.d}, {'T-A', 'T-B'})
        self.assertEqual({k[0] for k in w.reg.acts}, {'T-A', 'T-B'})
        self.assertEqual(set(w.aud.chains), {'T-A', 'T-B'})

    def test_CT_07_the_reference_context_port(self):
        """CT-07: a registered unexpired token resolves; missing, unknown, wrong-type and expired ones are refused."""
        now = [10]
        p = R.RefContext(lambda: now[0])
        p.register('t', 'T', 20)
        self.assertEqual(p.resolve('t'), 'T')
        for ctx, exc in ((None, ContextMissing), ('', ContextMissing), ('u', ContextInvalid), (5, ContextInvalid)):
            with self.assertRaises(exc):
                p.resolve(ctx)
        now[0] = 20
        with self.assertRaises(ContextInvalid):
            p.resolve('t')

    def test_a_context_port_that_fails_unexpectedly_is_treated_as_invalid(self):
        """MIE-R-38: fail closed on a context the port cannot vouch for."""
        w = World()

        class Broken(R.RefContext):
            def resolve(self, ctx):
                raise RuntimeError('down')
        w.e.context = Broken(lambda: 0)
        self.assertEqual(code(lambda: w.e.describe('tA')), 'TENANT_CONTEXT_INVALID')


if __name__ == '__main__':
    unittest.main()
