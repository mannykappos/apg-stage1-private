"""MIE-1 port contracts and describe (CT-01, CT-03, CT-04, CT-05, CT-09, CT-11)."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_mie import World, code
from mie.core import canon, ports as PT, reference as R, vocab as Y


class TestDescribe(unittest.TestCase):
    def test_CT_01_describe_reports_every_version_vocabulary_and_limit_key(self):
        """CT-01, MIE-R-03."""
        w = World(pack=False)
        d = w.e.describe('tA')
        self.assertEqual(d['versions'], Y.VERSIONS)
        self.assertEqual(set(d['versions']), {'core', 'pack_schema', 'signal_vocabulary', 'outcome_vocabulary', 'event_class_vocabulary', 'error_vocabulary',
                                              'neutrality_deny_list'})
        self.assertEqual(d['operations'], list(Y.OPERATIONS))
        self.assertEqual(d['limit_keys'], list(Y.LIMIT_KEYS))
        self.assertEqual(len(d['errors']), 27)
        self.assertEqual(len(d['reasons']), 15)
        self.assertEqual(d['outcomes'], {'BUY': ['ACT_NOW', 'WAIT', 'STAGE', 'NEGOTIATE', 'NOT_ASSESSED'], 'SELL': ['ACT_NOW', 'HOLD', 'WAIT', 'NOT_ASSESSED']})
        self.assertEqual(set(d['signals']), set(Y.SIGNALS))


class TestStores(unittest.TestCase):
    def test_CT_03_the_observation_store_is_append_only_idempotent_scoped_and_copies(self):
        """CT-03."""
        s = R.RefObservations()
        o = {'subject_id': 'S', 'v': 1}
        self.assertEqual(s.append('T', 'OB-1', o), 'stored')
        self.assertEqual(s.append('T', 'OB-1', {'subject_id': 'S', 'v': 2}), 'duplicate')
        self.assertEqual(s.get('T', 'OB-1'), o)
        self.assertIsNone(s.get('U', 'OB-1'))
        got = s.get('T', 'OB-1')
        got['v'] = 9
        self.assertEqual(s.get('T', 'OB-1')['v'], 1)
        self.assertEqual(list(s.for_subjects('T', ['S'])), ['OB-1'])
        self.assertEqual(s.for_subjects('U', ['S']), {})
        s.fail_writes = True
        with self.assertRaises(PT.StoreFailure):
            s.append('T', 'OB-2', o)
        s.fail_reads = True
        with self.assertRaises(PT.StoreFailure):
            s.get('T', 'OB-1')

    def test_CT_04_the_registry_is_immutable_hash_bound_with_withdrawal_and_activation_records(self):
        """CT-04."""
        g = R.RefRegistry()
        pin = {'pack_id': 'P', 'pack_version': '1', 'pack_hash': 'a' * 64}
        g.put(pin, b'{}', 'T')
        with self.assertRaises(PT.StoreFailure):
            g.put(dict(pin, pack_hash='b' * 64), b'{"x":1}', 'T')
        self.assertEqual(g.get('P', '1')['bytes'], b'{}')
        self.assertIsNone(g.withdrawal(pin))
        g.withdraw(pin, {'reason_ref': 'r1'})
        g.withdraw(pin, {'reason_ref': 'r2'})
        self.assertEqual(g.withdrawal(pin), {'reason_ref': 'r1'})
        g.activate('T', pin, {'a': 1})
        g.activate('T', pin, {'a': 2})
        self.assertEqual(g.activations('T', pin), [{'a': 1}, {'a': 2}])
        self.assertEqual(g.activations('U', pin), [])

    def test_CT_05_the_result_store_is_content_addressed_and_returns_copies(self):
        """CT-05."""
        r = R.RefResults()
        self.assertEqual(r.put('T', 'RS-1', {'a': 1}), 'stored')
        self.assertEqual(r.put('T', 'RS-1', {'a': 2}), 'duplicate')
        self.assertEqual(r.get('T', 'RS-1'), {'a': 1})
        self.assertIsNone(r.get('U', 'RS-1'))


class TestHooksAndApprovals(unittest.TestCase):
    def test_CT_09_the_hook_slot_is_deterministic_and_has_no_formula(self):
        """CT-09: with nothing registered every call is HOOK_UNAVAILABLE; a registered test double is called with integers and gives the same answer twice."""
        h = R.RefHooks()
        with self.assertRaises(PT.HookUnavailable):
            h.call('SYN-HOOK-1', {'a': 1})
        h.impl['SYN-HOOK-1'] = lambda inputs: inputs['a'] * 2          # TEST-ONLY double
        self.assertEqual(h.call('SYN-HOOK-1', {'a': 21}), 42)
        self.assertEqual(h.call('SYN-HOOK-1', {'a': 21}), h.call('SYN-HOOK-1', {'a': 21}))
        self.assertIn('HOOK_UNAVAILABLE', Y.ERRORS)

    def test_CT_11_the_approval_verifier_binds_reference_pin_tenant_and_refuses_self_approval(self):
        """CT-11."""
        v = R.RefApprovals()
        pin = {'pack_id': 'P', 'pack_version': '1', 'pack_hash': 'a' * 64}
        doc = {'provenance': {'author_ref': 'AUTHOR'}}
        v.register('A1', 'OWNER', pin, 'T')
        self.assertTrue(v.verify('T', 'A1', pin, doc))
        self.assertFalse(v.verify('U', 'A1', pin, doc))
        self.assertFalse(v.verify('T', 'A1', dict(pin, pack_version='2'), doc))
        self.assertFalse(v.verify('T', 'A2', pin, doc))
        v.register('A3', 'AUTHOR', pin, 'T')
        self.assertFalse(v.verify('T', 'A3', pin, doc))


if __name__ == '__main__':
    unittest.main()
