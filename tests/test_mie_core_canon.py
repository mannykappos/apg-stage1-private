"""MIE-1 canonical form, exact values, text and payload screening at their edges (MIE1_SPEC 7.2, 4.2, 9.4; MIE-R-29, MIE-R-38).  Unit tests of mie/core/canon.py, values.py and
observations.tenant_claim, added for the mutation run: each case pins a boundary the operation-level tests did not."""
import unittest
from fractions import Fraction
from . import _path                                         # noqa: F401
from mie.core import canon as C, observations as O, values as V


def nest(n, leaf=0):
    v = leaf
    for _ in range(n):
        v = [v]
    return v


class TestCanon(unittest.TestCase):
    def test_parse_refuses_what_has_no_canonical_form(self):
        """MIE-R-29: bytes only; UTF-8; no duplicate key; no NaN or infinity; JSON only.  A float is handed back marked, never as a float."""
        for bad in (b'{"a":NaN}', b'{"a":Infinity}', b'{"a":-Infinity}', b'{"a":1,"a":2}', b'{"a":', b'\xff\xfe', b'[1,]'):
            with self.subTest(data=bad):
                with self.assertRaises(C.CanonError):
                    C.loads(bad)
        for not_bytes in ('{}', None, 5):
            with self.subTest(data=not_bytes):
                with self.assertRaises(C.CanonError):
                    C.loads(not_bytes)
        v = C.loads(b'{"a":1.5}')
        self.assertIsInstance(v['a'], C.FloatSeen)
        self.assertEqual(C.find_floats(v), ['$.a'])

    def test_nesting_is_bounded_at_exactly_the_maximum_depth(self):
        """The canonical form allows nesting to MAX_DEPTH levels and refuses one more, when writing and when searching for floats."""
        self.assertEqual(C.dumps(nest(C.MAX_DEPTH)), b'[' * C.MAX_DEPTH + b'0' + b']' * C.MAX_DEPTH)
        with self.assertRaises(C.CanonError):
            C.dumps(nest(C.MAX_DEPTH + 1))
        with self.assertRaises(C.CanonError):
            C.dumps({'a': nest(C.MAX_DEPTH)})
        self.assertEqual(C.find_floats(nest(C.MAX_DEPTH, C.FloatSeen('1.0'))), ['$' + '[0]' * C.MAX_DEPTH])
        with self.assertRaises(C.CanonError):
            C.find_floats(nest(C.MAX_DEPTH + 1))
        with self.assertRaises(C.CanonError):
            C.find_floats({'a': nest(C.MAX_DEPTH)})

    def test_lone_surrogates_are_refused_at_both_ends_of_the_range(self):
        for ch in ('\ud800', '\udbff', '\udc00', '\udfff'):
            with self.subTest(code=hex(ord(ch))):
                with self.assertRaises(C.CanonError):
                    C.dumps(ch)
        self.assertEqual(C.dumps('퟿'), '"퟿"'.encode('utf-8'))
        self.assertEqual(C.dumps(''), '""'.encode('utf-8'))

    def test_keys_sort_by_utf8_bytes_and_text_is_nfc_with_minimal_escapes(self):
        self.assertEqual(C.dumps({'b': 1, 'a': [True, False, None], 'é': 'x"\\\n'}), b'{"a":[true,false,null],"b":1,"\xc3\xa9":"x\\"\\\\\\u000a"}')
        with self.assertRaises(C.CanonError):
            C.dumps('é')
        with self.assertRaises(C.CanonError):
            C.dumps({1: 'x'})


class TestValuesAndText(unittest.TestCase):
    def test_exact_values_for_every_sign_of_exponent(self):
        self.assertEqual(V.exact({'mantissa': 12, 'exponent': 0}), Fraction(12))
        self.assertEqual(V.exact({'mantissa': 12, 'exponent': 2}), Fraction(1200))
        self.assertEqual(V.exact({'mantissa': 12, 'exponent': -2}), Fraction(3, 25))

    def test_text_length_is_allowed_up_to_and_including_the_bound(self):
        self.assertIsNone(V.text_problem('a' * 10, 10))
        self.assertEqual(V.text_problem('a' * 11, 10), 'text longer than the configured bound')

    def test_control_and_direction_characters_are_each_refused_on_their_own(self):
        self.assertEqual(V.text_problem('a\x01b', 10), 'control or direction-control characters')
        self.assertEqual(V.text_problem('a‮b', 10), 'control or direction-control characters')
        self.assertIsNone(V.text_problem('a b', 10))


class TestTenantClaim(unittest.TestCase):
    def test_a_payload_nested_past_forty_levels_is_treated_as_naming_a_tenant(self):
        """MIE-R-38: the screen cannot look deeper than forty levels, so anything deeper is refused as if it named a tenant (fail closed)."""
        self.assertFalse(O.tenant_claim(nest(40)))                     # the innermost value sits at level 40
        self.assertTrue(O.tenant_claim(nest(41)))
        self.assertFalse(O.tenant_claim({'a': nest(39)}))
        self.assertTrue(O.tenant_claim({'a': nest(40)}))
        self.assertTrue(O.tenant_claim(nest(5, {'Tenant_Ref': 1})))


if __name__ == '__main__':
    unittest.main()
