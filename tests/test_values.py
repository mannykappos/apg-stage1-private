import unittest
from . import _path                                          # noqa: F401
from apg import canon
from apg.values import Known, Unknown, UnknownValueError, as_value, total, ratio_bps, NO_DATA, INVALID


class KnownUnknown(unittest.TestCase):
    def test_known_needs_an_int_not_a_bool_or_float(self):
        for bad in (True, 1.5, '5', None):
            with self.assertRaises(TypeError): Known(bad)

    def test_truthiness_and_arithmetic_on_unknown_are_refused(self):
        u = Unknown(NO_DATA)
        for fn in (lambda: bool(u), lambda: u.cents, lambda: u + 1, lambda: 2 * u, lambda: int(u), lambda: u >= 0, lambda: u - u):
            with self.assertRaises(UnknownValueError): fn()
        with self.assertRaises(UnknownValueError): bool(Known(0))                      # a zero amount must never be mistaken for "no amount"

    def test_unknown_reason_must_be_a_listed_one(self):
        with self.assertRaises(ValueError): Unknown('whatever')


class AsValue(unittest.TestCase):
    def test_conversions(self):
        self.assertEqual(as_value(5), Known(5)); self.assertEqual(as_value('12'), Known(12)); self.assertEqual(as_value(' -7 '), Known(-7)); self.assertEqual(as_value('0'), Known(0))
        for bad in (True, False, 1.0, '1.5', '١٢', '１２', '1e3', '--1', '-', '12 3', [], {}, b'1'):
            v = as_value(bad); self.assertIsInstance(v, Unknown, repr(bad)); self.assertEqual(v.reason, INVALID)
        for blank in (None, ''):
            self.assertEqual(as_value(blank).reason, NO_DATA)
        self.assertEqual(as_value(None, 'stale').reason, 'stale')
        k = Known(3); self.assertIs(as_value(k), k)


class Totals(unittest.TestCase):
    def test_total_lists_what_it_leaves_out(self):
        t = total([('a', 5), ('b', None), ('c', 'x'), ('d', Known(-2))])
        self.assertEqual((t.cents, t.complete, t.included), (3, False, ('a', 'd'))); self.assertEqual([x[0] for x in t.left_out], ['b', 'c'])
        with self.assertRaises(UnknownValueError): t.require_complete()
        t2 = total([('a', 1)]); self.assertEqual((t2.require_complete(), t2.complete), (1, True))
        self.assertEqual(total([]).cents, 0)

    def test_ratio_bps_rounding_sign_and_unknown(self):
        self.assertEqual(ratio_bps(1, 3), Known(3333)); self.assertEqual(ratio_bps(2, 3), Known(6667)); self.assertEqual(ratio_bps(1, 2), Known(5000)); self.assertEqual(ratio_bps(1, 8), Known(1250))
        self.assertEqual(ratio_bps(1, 40000), Known(0))
        self.assertEqual(ratio_bps(-1, 3), Known(-3333)); self.assertEqual(ratio_bps(-1, 8), Known(-1250)); self.assertEqual(ratio_bps(-3, 8), Known(-3750))
        for d in (0, -5, None, '', 'x'):
            self.assertIsInstance(ratio_bps(5, d), Unknown, repr(d))
        self.assertIsInstance(ratio_bps(None, 5), Unknown); self.assertEqual(ratio_bps(None, 5).reason, NO_DATA)
        self.assertEqual(ratio_bps(Unknown('stale'), 0).reason, 'stale')

    def test_half_rounds_away_from_zero(self):
        self.assertEqual(ratio_bps(1, 20000), Known(1)); self.assertEqual(ratio_bps(-1, 20000), Known(-1)); self.assertEqual(ratio_bps(3, 20000), Known(2))


class Canon(unittest.TestCase):
    def test_floats_nan_and_odd_keys_refused(self):
        for bad in (1.5, float('nan'), float('inf'), {1: 'a'}, {'a': {2: 3}}, [1, 2.0], {'a': {1, 2}}, b'x', object()):
            with self.assertRaises(canon.CanonError, msg=repr(bad)): canon.canonical(bad)

    def test_canonical_is_order_independent_and_digest_is_stable(self):
        a, b = {'x': 1, 'y': [1, 2, {'q': 'é'}]}, {'y': [1, 2, {'q': 'é'}], 'x': 1}
        self.assertEqual(canon.canonical(a), canon.canonical(b)); self.assertEqual(canon.digest(a), canon.digest(b))
        self.assertEqual(canon.canonical(a), '{"x":1,"y":[1,2,{"q":"\\u00e9"}]}'); self.assertNotEqual(canon.digest({'x': 1}), canon.digest({'x': 2}))
        self.assertEqual(len(canon.digest({})), 64)

    def test_deep_copy_is_independent(self):
        a = {'x': [1, {'y': 2}]}; b = canon.deep_copy(a); b['x'][1]['y'] = 9; self.assertEqual(a['x'][1]['y'], 2)

    def test_norm_key(self):
        n = canon.norm_key
        self.assertEqual(n('Tenant-ID'), 'tenant_id'); self.assertEqual(n('tenant.id'), 'tenant_id'); self.assertEqual(n('tenant id'), 'tenant_id'); self.assertEqual(n('TENANT­_ID'), 'tenant_id')
        self.assertEqual(n('t​enant'), 'tenant'); self.assertEqual(n('ｔｅnant'), 'tenant'); self.assertEqual(n('te\u0000nant'), 'tenant'); self.assertEqual(n('A B'), 'a_b')


if __name__ == '__main__':
    unittest.main()
