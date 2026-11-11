"""MIE-1 audit and failure behaviour (AU-01..AU-12, AD-01..AD-03, CT-06, CT-12, CT-13).  Sequence: validate, compute, append the audit event, commit, return."""
import copy, unittest
from . import _path                                         # noqa: F401
from .helpers_mie import EVAL, LIMITS, World, code, ob, pack_with, scenario, series, UP
from mie.core import canon, ports as PT, reference as R, vocab as Y
from mie.packs import synthetic as SP


def snapshot(w):
    return canon.dumps({'obs': sorted([list(k), v] for k, v in w.obs.d.items()), 'res': sorted([list(k), v] for k, v in w.res.d.items()),
                        'packs': sorted([list(k), v['pin']] for k, v in w.reg.packs.items()), 'wd': sorted(w.reg.withdrawn.items()),
                        'acts': sorted([list(k), v] for k, v in w.reg.acts.items())})


def ready():
    w = World()
    w.submit(series(UP))
    w.rid = w.assess()['result_id']
    return w


def boom(*a, **k):
    raise RuntimeError('unexpected')


BAD_PIN = {'pack_id': 'SYN-TEST-FIELD', 'pack_version': '1.0.0', 'pack_hash': 'nothex'}


def wrong_hash(w):
    return dict(w.pin, pack_hash='0' * 64)


def withdrawn(w):
    w.e.withdraw_pack('tA', w.pin, 'TEST-ONLY')
    return w


def nolimits(w):
    w.lim.values = None
    return w


def lim(w, **k):
    w.lim.values = dict(LIMITS, **k)
    return w


def buy_only():
    w = World(pack=pack_with(allowed_intentions=['BUY'], pack_version='buy-only',
                             decision_table=[r for r in SP.pack()['decision_table'] if r['intention'] == 'BUY']))
    return w


SC = scenario()
OPS = {   # operation -> code -> how to reach it (each on a fresh world); AU-11 compares the keys with the operation's error list
    'describe': {'AUDIT_UNAVAILABLE': lambda w: (setattr(w.aud, 'down', True), w.e.describe('tA')),
                 'INTERNAL_ERROR_FAIL_CLOSED': lambda w: (setattr(Y, 'OUTCOMES', None), w.e.describe('tA'))},
    'validate_pack': {'REQUEST_MALFORMED': lambda w: w.e.validate_pack('tA', 'text'), 'PACK_MALFORMED': lambda w: w.e.validate_pack('tA', b'{'),
                      'PACK_SCHEMA_UNSUPPORTED': lambda w: w.e.validate_pack('tA', SP.pack_bytes(pack_schema='x')),
                      'PACK_CORE_INCOMPATIBLE': lambda w: w.e.validate_pack('tA', SP.pack_bytes(core_compat=['x'])),
                      'PACK_INVARIANT_OVERRIDE': lambda w: w.e.validate_pack('tA', SP.pack_bytes(allowed_intentions=['RENT'])),
                      'PACK_RULE_POLICY_VIOLATION': lambda w: w.e.validate_pack('tA', SP.pack_bytes(decision_profile='CONTEXT_ONLY')),
                      'LIMIT_NOT_CONFIGURED': lambda w: nolimits(w).e.validate_pack('tA', SP.pack_bytes()),
                      'LIMIT_EXCEEDED': lambda w: lim(w, max_pack_bytes=10).e.validate_pack('tA', SP.pack_bytes()),
                      'AUDIT_UNAVAILABLE': lambda w: (setattr(w.aud, 'down', True), w.e.validate_pack('tA', SP.pack_bytes())),
                      'INTERNAL_ERROR_FAIL_CLOSED': lambda w: (setattr(w.lim, 'limits', boom), w.e.validate_pack('tA', SP.pack_bytes()))},
    'register_pack': {'REQUEST_MALFORMED': lambda w: w.e.register_pack('tA', None), 'PACK_MALFORMED': lambda w: w.e.register_pack('tA', b'[]'),
                      'PACK_SCHEMA_UNSUPPORTED': lambda w: w.e.register_pack('tA', SP.pack_bytes(pack_schema='x')),
                      'PACK_CORE_INCOMPATIBLE': lambda w: w.e.register_pack('tA', SP.pack_bytes(core_compat=['x'])),
                      'PACK_INVARIANT_OVERRIDE': lambda w: w.e.register_pack('tA', SP.pack_bytes(allowed_intentions=['RENT'])),
                      'PACK_RULE_POLICY_VIOLATION': lambda w: w.e.register_pack('tA', SP.pack_bytes(decision_profile='CONTEXT_ONLY')),
                      'PACK_VERSION_CONFLICT': lambda w: w.e.register_pack('tA', SP.pack_bytes(field_label='other')),
                      'LIMIT_NOT_CONFIGURED': lambda w: nolimits(w).e.register_pack('tA', SP.pack_bytes()),
                      'LIMIT_EXCEEDED': lambda w: lim(w, max_rules=1).e.register_pack('tA', SP.pack_bytes('2')),
                      'STORE_UNAVAILABLE': lambda w: (setattr(w.reg, 'fail_writes', True), w.e.register_pack('tA', SP.pack_bytes('2'))),
                      'AUDIT_UNAVAILABLE': lambda w: (setattr(w.aud, 'down', True), w.e.register_pack('tA', SP.pack_bytes('2'))),
                      'INTERNAL_ERROR_FAIL_CLOSED': lambda w: (setattr(w.lim, 'limits', boom), w.e.register_pack('tA', SP.pack_bytes('2')))},
    'get_pack': {'REQUEST_MALFORMED': lambda w: w.e.get_pack('tA', BAD_PIN), 'NOT_FOUND': lambda w: w.e.get_pack('tA', dict(w.pin, pack_version='9')),
                 'PACK_HASH_MISMATCH': lambda w: w.e.get_pack('tA', wrong_hash(w)),
                 'STORE_UNAVAILABLE': lambda w: (setattr(w.reg, 'fail_reads', True), w.e.get_pack('tA', w.pin)),
                 'AUDIT_UNAVAILABLE': lambda w: (setattr(w.aud, 'down', True), w.e.get_pack('tA', w.pin)),
                 'INTERNAL_ERROR_FAIL_CLOSED': lambda w: (setattr(w.reg, 'get', boom), w.e.get_pack('tA', w.pin))},
    'withdraw_pack': {'REQUEST_MALFORMED': lambda w: w.e.withdraw_pack('tA', w.pin, ' '), 'NOT_FOUND': lambda w: w.e.withdraw_pack('tB', w.pin, 'r'),
                      'STORE_UNAVAILABLE': lambda w: (setattr(w.reg, 'fail_writes', True), w.e.withdraw_pack('tA', w.pin, 'r')),
                      'AUDIT_UNAVAILABLE': lambda w: (setattr(w.aud, 'down', True), w.e.withdraw_pack('tA', w.pin, 'r')),
                      'INTERNAL_ERROR_FAIL_CLOSED': lambda w: (setattr(w.reg, 'get', boom), w.e.withdraw_pack('tA', w.pin, 'r'))},
    'activate_pack': {'REQUEST_MALFORMED': lambda w: w.e.activate_pack('tA', BAD_PIN, 'a'), 'NOT_FOUND': lambda w: w.e.activate_pack('tA', dict(w.pin, pack_version='9'), 'a'),
                      'PACK_HASH_MISMATCH': lambda w: w.e.activate_pack('tA', wrong_hash(w), 'a'),
                      'PACK_WITHDRAWN': lambda w: withdrawn(w).e.activate_pack('tA', w.pin, 'a'),
                      'PACK_APPROVAL_MISSING': lambda w: w.e.activate_pack('tA', w.pin, 'unknown'),
                      'STORE_UNAVAILABLE': lambda w: (setattr(w.reg, 'fail_writes', True), w.activate('tB', w.pin)),
                      'AUDIT_UNAVAILABLE': lambda w: (setattr(w.aud, 'down', True), w.activate('tB', w.pin)),
                      'INTERNAL_ERROR_FAIL_CLOSED': lambda w: (setattr(w.reg, 'get', boom), w.activate('tB', w.pin))},
    'submit_observations': {'REQUEST_MALFORMED': lambda w: w.submit('x'), 'PACK_NOT_ACTIVE': lambda w: w.submit([ob('2026-09-01', 1)], token='tB'),
                            'PACK_HASH_MISMATCH': lambda w: w.submit([ob('2026-09-01', 1)], pin=wrong_hash(w)),
                            'PACK_WITHDRAWN': lambda w: withdrawn(w).submit([ob('2026-09-01', 1)]),
                            'LIMIT_NOT_CONFIGURED': lambda w: nolimits(w).submit([ob('2026-09-01', 1)]),
                            'LIMIT_EXCEEDED': lambda w: lim(w, max_batch_items=1).submit([ob('2026-09-01', 1), ob('2026-09-02', 1)]),
                            'STORE_UNAVAILABLE': lambda w: (setattr(w.obs, 'fail_writes', True), w.submit([ob('2026-09-01', 1)])),
                            'AUDIT_UNAVAILABLE': lambda w: (setattr(w.aud, 'down', True), w.submit([ob('2026-09-01', 1)])),
                            'INTERNAL_ERROR_FAIL_CLOSED': lambda w: (setattr(w.reg, 'get', boom), w.submit([ob('2026-09-01', 1)]))},
    'get_signals': {'REQUEST_MALFORMED': lambda w: w.signals(when='x'), 'NOT_FOUND': lambda w: w.signals('SYN-ITEM-Z'),
                    'PACK_NOT_ACTIVE': lambda w: w.signals(token='tB'), 'PACK_HASH_MISMATCH': lambda w: w.e.get_signals('tA', wrong_hash(w), 'SYN-ITEM-A', EVAL),
                    'PACK_WITHDRAWN': lambda w: withdrawn(w).signals(), 'LIMIT_NOT_CONFIGURED': lambda w: nolimits(w).signals(),
                    'LIMIT_EXCEEDED': lambda w: lim(w, max_series_points=1).signals(),
                    'STORE_UNAVAILABLE': lambda w: (setattr(w.obs, 'fail_reads', True), w.signals()),
                    'AUDIT_UNAVAILABLE': lambda w: (setattr(w.aud, 'down', True), w.signals()),
                    'INTERNAL_ERROR_FAIL_CLOSED': lambda w: (setattr(w.reg, 'get', boom), w.signals())},
    'assess_timing': {'REQUEST_MALFORMED': lambda w: w.assess('NONE'), 'INTENTION_NOT_ALLOWED': lambda w: buy_only().assess('SELL'),
                      'PACK_NOT_ACTIVE': lambda w: w.assess(token='tB'), 'PACK_HASH_MISMATCH': lambda w: w.assess(pin=wrong_hash(w)),
                      'PACK_WITHDRAWN': lambda w: withdrawn(w).assess(), 'PACK_INCOMPLETE': lambda w: w.assess(subject='SYN-ITEM-Z'),
                      'SCENARIO_INVALID': lambda w: w.assess(scenarios=[{}]), 'LIMIT_NOT_CONFIGURED': lambda w: nolimits(w).assess(),
                      'LIMIT_EXCEEDED': lambda w: lim(w, max_scenarios=0).assess(scenarios=[SC]),
                      'STORE_UNAVAILABLE': lambda w: (setattr(w.res, 'fail_writes', True), w.assess(need_by='2027-01-01')),
                      'AUDIT_UNAVAILABLE': lambda w: (setattr(w.aud, 'down', True), w.assess()),
                      'INTERNAL_ERROR_FAIL_CLOSED': lambda w: (setattr(w.reg, 'get', boom), w.assess())},
    'replay_result': {'REQUEST_MALFORMED': lambda w: w.e.replay_result('tA', 'x'), 'NOT_FOUND': lambda w: w.e.replay_result('tB', w.rid),
                      'REPLAY_EVIDENCE_UNAVAILABLE': lambda w: (w.obs.d.clear(), w.e.replay_result('tA', w.rid)),
                      'REPLAY_PACK_UNAVAILABLE': lambda w: (w.reg.packs.clear(), w.e.replay_result('tA', w.rid)),
                      'STORE_UNAVAILABLE': lambda w: (setattr(w.res, 'fail_reads', True), w.e.replay_result('tA', w.rid)),
                      'AUDIT_UNAVAILABLE': lambda w: (setattr(w.aud, 'down', True), w.e.replay_result('tA', w.rid)),
                      'INTERNAL_ERROR_FAIL_CLOSED': lambda w: (setattr(w.res, 'get', boom), w.e.replay_result('tA', w.rid))},
    'get_result': {'REQUEST_MALFORMED': lambda w: w.e.get_result('tA', 'x'), 'NOT_FOUND': lambda w: w.e.get_result('tB', w.rid),
                   'STORE_UNAVAILABLE': lambda w: (setattr(w.res, 'fail_reads', True), w.e.get_result('tA', w.rid)),
                   'AUDIT_UNAVAILABLE': lambda w: (setattr(w.aud, 'down', True), w.e.get_result('tA', w.rid)),
                   'INTERNAL_ERROR_FAIL_CLOSED': lambda w: (setattr(w.res, 'get', boom), w.e.get_result('tA', w.rid))},
    'list_audit': {'REQUEST_MALFORMED': lambda w: w.e.list_audit('tA', 0, 5), 'LIMIT_NOT_CONFIGURED': lambda w: nolimits(w).e.list_audit('tA', 1, 5),
                   'LIMIT_EXCEEDED': lambda w: w.e.list_audit('tA', 1, 10 ** 6),
                   'AUDIT_UNAVAILABLE': lambda w: (setattr(w.aud, 'down', True), w.e.list_audit('tA', 1, 5)),
                   'INTERNAL_ERROR_FAIL_CLOSED': lambda w: (setattr(w.aud, 'verify', boom), w.e.list_audit('tA', 1, 5))},
}
CONTEXT = ('TENANT_CONTEXT_MISSING', 'TENANT_CONTEXT_INVALID')        # reached for every operation in test_mie_core_tenancy (IS-01)


def reach(op, c):
    w = ready()
    saved = Y.OUTCOMES
    try:
        return code(lambda: OPS[op][c](w)), w
    finally:
        Y.OUTCOMES = saved


class TestInventory(unittest.TestCase):
    def test_AU_11_every_listed_code_is_reachable_and_the_lists_are_exact(self):
        """AU-11: for every operation the error list equals the common failures plus its own, and each listed code is reached by a case here or in IS-01."""
        self.assertEqual(set(OPS), set(Y.OPERATIONS))
        for op in Y.OPERATIONS:
            self.assertEqual(set(OPS[op]) | set(CONTEXT), set(Y.OPERATION_ERRORS[op]), op)
            for c in Y.COMMON_ERRORS:
                self.assertIn(c, Y.OPERATION_ERRORS[op])
            for c in OPS[op]:
                with self.subTest(operation=op, code=c):
                    self.assertEqual(reach(op, c)[0], c)

    def test_an_error_outside_an_operations_list_fails_closed(self):
        """AU-11 (defence): the engine never returns a code its contract does not list."""
        w = ready()
        from mie.core.vocab import MieError

        def odd(*a, **k):
            raise MieError('SCENARIO_INVALID', 'not in the get_result contract')
        w.res.get = odd
        self.assertEqual(code(lambda: w.e.get_result('tA', w.rid)), 'INTERNAL_ERROR_FAIL_CLOSED')
        self.assertEqual(w.events()[-1]['outcome'], 'FAILED')


class TestSequence(unittest.TestCase):
    def test_AU_06_AD_01_with_the_sink_down_every_operation_returns_AUDIT_UNAVAILABLE_and_changes_nothing(self):
        """AU-06, AD-01 (SB-14, SB-38)."""
        for op, cases in OPS.items():
            with self.subTest(operation=op):
                w = ready()
                before = snapshot(w)
                w.aud.down = True
                self.assertEqual(code(lambda: cases['AUDIT_UNAVAILABLE'](w)), 'AUDIT_UNAVAILABLE')
                self.assertEqual(snapshot(w), before)

    def test_AU_07_the_audit_event_is_appended_before_the_commit(self):
        """AU-07 (SB-36): at the moment each store write happens, the ACCEPTED event for it is already in the chain; a failing append leaves every store untouched."""
        w = World(activate=False)
        seen = []
        for port, name in ((w.reg, 'put'), (w.reg, 'activate'), (w.reg, 'withdraw'), (w.obs, 'append_batch'), (w.res, 'put')):
            real = getattr(port, name)

            def spy(*a, _real=real, _name=name, **k):
                chain = w.aud.chains.get('T-A', [])
                seen.append((_name, chain[-1]['event']['outcome'] if chain else None))
                return _real(*a, **k)
            setattr(port, name, spy)
        w.e.register_pack('tA', SP.pack_bytes('2'))
        pin2 = w.e.validate_pack('tA', SP.pack_bytes('2'))['pin']
        w.activate('tA', pin2)
        w.submit(series(UP), pin=pin2)
        w.assess(pin=pin2)
        w.e.withdraw_pack('tA', pin2, 'r')
        self.assertTrue(seen)
        self.assertEqual({o for _, o in seen}, {'ACCEPTED'})
        self.assertEqual({n for n, _ in seen}, {'put', 'activate', 'append_batch', 'withdraw'})
        w2 = World(activate=False)
        before = snapshot(w2)
        w2.aud.down = True
        for fn in (lambda: w2.e.register_pack('tA', SP.pack_bytes('3')), lambda: w2.activate('tA', w2.pin), lambda: w2.e.withdraw_pack('tA', w2.pin, 'r')):
            self.assertEqual(code(fn), 'AUDIT_UNAVAILABLE')
        self.assertEqual(snapshot(w2), before)

    def test_AU_08_AD_02_a_store_failure_after_the_append_returns_STORE_UNAVAILABLE_and_one_FAILED_event(self):
        """AU-08, AD-02 (SB-29): no result, an ACCEPTED then one FAILED event, no record of a completed change."""
        w = World()
        w.submit(series(UP))
        n = len(w.events())
        w.res.fail_writes = True
        self.assertEqual(code(lambda: w.assess(need_by='2026-12-01')), 'STORE_UNAVAILABLE')
        new = w.events()[n:]
        self.assertEqual([(e['operation'], e['outcome'], e['code']) for e in new], [('assess_timing', 'ACCEPTED', None), ('assess_timing', 'FAILED', 'STORE_UNAVAILABLE')])
        self.assertEqual(w.res.d, {})
        w.res.fail_writes = False
        w.aud.fail_after = 1
        w.obs.fail_writes = True
        self.assertEqual(code(lambda: w.submit([ob('2026-09-20', 5)])), 'STORE_UNAVAILABLE')
        self.assertEqual(w.events()[-1]['outcome'], 'ACCEPTED')

    def test_AD_03_an_unexpected_exception_fails_closed_with_no_outcome(self):
        """AD-03."""
        w = ready()
        before = snapshot(w)
        w.obs.for_subjects = boom
        self.assertEqual(code(lambda: w.assess(need_by='2027-02-01')), 'INTERNAL_ERROR_FAIL_CLOSED')
        self.assertEqual(snapshot(w), before)
        self.assertEqual(w.events()[-1]['code'], 'INTERNAL_ERROR_FAIL_CLOSED')

    def test_AU_12_a_refusal_is_audited_with_REFUSED_and_its_code(self):
        """AU-12."""
        w = World(pack=pack_with(allowed_intentions=['BUY'], pack_version='au12', decision_table=None))
        self.assertEqual(code(lambda: w.assess('SELL')), 'INTENTION_NOT_ALLOWED')
        last = w.events()[-1]
        self.assertEqual((last['operation'], last['outcome'], last['code']), ('assess_timing', 'REFUSED', 'INTENTION_NOT_ALLOWED'))
        w.e.describe('tA')
        self.assertEqual((w.events()[-1]['outcome'], w.events()[-1]['code']), ('OK', None))

    def test_AU_10_events_hold_identifiers_and_digests_only(self):
        """AU-10: a planted licensed value and planted licence terms never appear in any event."""
        doc = SP.pack('au10')
        doc['licences'][0]['terms_ref'] = 'TEST-ONLY PLANTED TERMS TEXT'
        w = World(pack=doc)
        w.submit([ob('2026-08-01', 987654321), ob('2026-09-01', 987654399)])
        w.assess(need_by='2026-12-01', scenarios=[scenario(assumed_level={'mantissa': 55555, 'exponent': 0})])
        w.signals()
        w.e.list_audit('tA', 1, 100)
        flat = canon.dumps([e['event'] for e in w.aud.chains['T-A']]).decode('utf-8')
        for planted in ('987654321', '987654399', 'PLANTED TERMS', '55555', 'TEST-ONLY owner'):
            self.assertNotIn(planted, flat)


class TestAuditReads(unittest.TestCase):
    def test_AU_01_and_AU_02_list_audit_reads_to_a_cutoff_then_appends_one_access_event(self):
        """AU-01, AU-02 (SB-33)."""
        w = ready()
        n = len(w.aud.chains['T-A'])
        out = w.e.list_audit('tA', 1, 500)
        self.assertEqual(out['cutoff_seq'], n)
        self.assertEqual([e['seq'] for e in out['events']], list(range(1, n + 1)))
        self.assertEqual(out['chain'], {'ok': True, 'events': n, 'broken_at': None})
        self.assertEqual(len(w.aud.chains['T-A']), n + 1)
        last = w.aud.chains['T-A'][-1]['event']
        self.assertEqual((last['operation'], last['refs']['type'], last['refs']['cutoff_seq'], last['refs']['returned']), ('list_audit', 'AUDIT_READ', n, n))
        again = w.e.list_audit('tA', n + 1, 500)
        self.assertEqual([e['event']['refs']['type'] for e in again['events']], ['AUDIT_READ'])
        self.assertEqual(len(w.aud.chains['T-A']), n + 2)
        page = w.e.list_audit('tA', 2, 3)
        self.assertEqual([e['seq'] for e in page['events']], [2, 3, 4])

    def test_AU_03_with_the_sink_down_list_audit_returns_nothing(self):
        """AU-03 (SB-35)."""
        w = ready()
        w.aud.down = True
        self.assertEqual(code(lambda: w.e.list_audit('tA', 1, 10)), 'AUDIT_UNAVAILABLE')
        w.aud.down = False
        w.aud.fail_after = 0
        self.assertEqual(code(lambda: w.e.list_audit('tA', 1, 10)), 'AUDIT_UNAVAILABLE')

    def test_AU_04_audit_reads_are_tenant_scoped(self):
        """AU-04 (SB-34)."""
        w = ready()
        w.activate('tB', w.pin)
        a = w.e.list_audit('tA', 1, 500)
        b = w.e.list_audit('tB', 1, 500)
        self.assertNotEqual(len(a['events']), len(b['events']))
        self.assertTrue(all(e['event']['operation'] in ('activate_pack',) for e in b['events']))
        self.assertIsNot(w.aud.chains['T-A'], w.aud.chains['T-B'])

    def test_AU_05_a_tampered_chain_is_reported_and_never_trimmed(self):
        """AU-05."""
        w = ready()
        w.aud.chains['T-A'][2]['event']['outcome'] = 'OK-FORGED'
        n = len(w.aud.chains['T-A'])
        out = w.e.list_audit('tA', 1, 500)
        self.assertEqual(out['chain'], {'ok': False, 'events': n, 'broken_at': 3})
        self.assertEqual(len(out['events']), n)
        self.assertEqual(out['events'][2]['event']['outcome'], 'OK-FORGED')


class TestPortContracts(unittest.TestCase):
    def test_CT_06_the_append_port_surfaces_every_failure(self):
        """CT-06."""
        a = R.RefAudit()
        self.assertEqual(a.append('T', {'x': 1}), {'seq': 1, 'hash': a.chains['T'][0]['hash']})
        a.down = True
        with self.assertRaises(PT.AuditFailure):
            a.append('T', {'x': 2})
        a.down, a.fail_after = False, 1
        a.append('T', {'x': 3})
        with self.assertRaises(PT.AuditFailure):
            a.append('T', {'x': 4})

    def test_CT_13_the_query_port_reads_and_verifies_only(self):
        """CT-13."""
        self.assertFalse(hasattr(PT.AuditQueryPort, 'append'))
        a = R.RefAudit()
        for i in range(5):
            a.append('T', {'i': i})
        a.append('U', {'i': 99})
        got = a.read('T', 2, 4, 10)
        self.assertEqual([e['event']['i'] for e in got], [1, 2, 3])
        self.assertEqual(len(a.read('T', 1, 5, 2)), 2)
        got[0]['event']['i'] = 'changed'
        self.assertEqual(a.read('T', 2, 2, 1)[0]['event']['i'], 1)
        self.assertEqual(a.verify('T'), {'ok': True, 'events': 5, 'broken_at': None})
        self.assertEqual(a.last_seq('U'), 1)
        a.down = True
        for fn in (lambda: a.read('T', 1, 1, 1), lambda: a.verify('T'), lambda: a.last_seq('T')):
            with self.assertRaises(PT.AuditFailure):
                fn()

    def test_CT_12_absent_limits_give_LIMIT_NOT_CONFIGURED(self):
        """CT-12: for every operation that needs host bounds, and for a missing key or a non-integer value."""
        for fn in (lambda w: w.e.validate_pack('tA', SP.pack_bytes()), lambda w: w.submit([ob('2026-09-01', 1)]), lambda w: w.signals(), lambda w: w.assess(),
                   lambda w: w.e.list_audit('tA', 1, 5)):
            w = World()
            w.lim.values = None
            self.assertEqual(code(lambda: fn(w)), 'LIMIT_NOT_CONFIGURED')
            w.lim.values = {k: v for k, v in LIMITS.items() if k != 'max_string_length'}
            w.lim.values['max_audit_page'] = True
            self.assertEqual(code(lambda: fn(w)), 'LIMIT_NOT_CONFIGURED')


if __name__ == '__main__':
    unittest.main()
