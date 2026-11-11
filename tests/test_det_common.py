"""The shared helpers of the detection rules: plain-language text, exact decimal reading, the exact threshold comparisons and the supplier lookup.  The comparisons are the heart of the
boundary behaviour of every rule, so each edge (equal, one above, a zero or negative denominator) is pinned here."""
import unittest
from . import _path                                         # noqa: F401
from apg.det import common as C
from apg.fin import intake as FI


class TestText(unittest.TestCase):
    def test_money_is_shown_in_dollars_and_cents_with_a_sign_only_when_negative(self):
        self.assertEqual(C.money(None), 'unknown')
        self.assertEqual(C.money(0), '0.00')
        self.assertEqual(C.money(1), '0.01')
        self.assertEqual(C.money(-1), '-0.01')
        self.assertEqual(C.money(123456), '1,234.56')
        self.assertEqual(C.money(-123456), '-1,234.56')
        self.assertEqual(C.money(100), '1.00')

    def test_a_percentage_is_shown_from_basis_points(self):
        self.assertEqual(C.pct(None), 'unknown')
        self.assertEqual(C.pct(0), '0.00%')
        self.assertEqual(C.pct(1234), '12.34%')
        self.assertEqual(C.pct(-150), '-1.50%')
        self.assertEqual(C.pct(5), '0.05%')
        self.assertEqual(C.pct(10000), '100.00%')


class TestMicro(unittest.TestCase):
    def test_exact_decimals_become_millionths(self):
        for text, want in (('0', 0), ('12', 12_000_000), ('1.5', 1_500_000), ('1.123456', 1_123_456), ('0.000001', 1), ('1.', 1_000_000), ('007.50', 7_500_000)):
            self.assertEqual(C.micro(text), want, text)

    def test_anything_else_is_not_a_number_here(self):
        for text in (None, 5, 1.5, b'1', '', ' ', '-1', '+1', '1.1234567', '1.a', 'a', '.5', '1,5', '1e3', '1.5.2', '１', '1.５', ' 1', '1 '):
            self.assertIsNone(C.micro(text), repr(text))


class TestComparisons(unittest.TestCase):
    def test_exceeds_is_strict_and_exact(self):
        self.assertFalse(C.exceeds_bps(5, 100, 500))            # exactly 5 percent is within a 5 percent tolerance
        self.assertTrue(C.exceeds_bps(6, 100, 500))
        self.assertTrue(C.exceeds_bps(50_000_001, 1_000_000_000, 500))              # 5.0000001 percent exceeds 5 percent although a rounded ratio would not
        self.assertFalse(C.exceeds_bps(50_000_000, 1_000_000_000, 500))
        self.assertFalse(C.exceeds_bps(0, 100, 0))
        self.assertTrue(C.exceeds_bps(1, 100, 0))

    def test_at_least_includes_the_boundary(self):
        self.assertTrue(C.at_least_bps(5, 100, 500))
        self.assertFalse(C.at_least_bps(4, 100, 500))
        self.assertTrue(C.at_least_bps(0, 100, 0))

    def test_a_zero_or_negative_denominator_has_no_ratio_and_never_qualifies(self):
        for den in (0, -1, -100):
            self.assertFalse(C.exceeds_bps(1, den, 0))
            self.assertFalse(C.exceeds_bps(10 ** 9, den, 0))
            self.assertFalse(C.at_least_bps(1, den, 0))
            self.assertFalse(C.at_least_bps(0, den, 0))
            self.assertFalse(C.at_least_bps(10 ** 9, den, 0))


class _Facts:
    def __init__(self, recon=None, recs=None):
        self._r, self._c = recon or {}, recs or {}

    def recon(self, kind, key):
        return self._r.get((kind, key))

    def get(self, kind, key):
        return self._c.get((kind, key))


class TestUsable(unittest.TestCase):
    def test_a_payload_is_usable_only_when_it_exists_and_its_outcome_is_usable(self):
        self.assertFalse(C.usable_payload(None))
        for outcome in FI.USABLE:
            self.assertTrue(C.usable_payload({'intrinsic': {'outcome': outcome, 'pending': []}}), outcome)
        self.assertFalse(C.usable_payload({'intrinsic': {'outcome': 'held', 'pending': ['X']}}))
        self.assertFalse(C.usable_payload({'conflict': True, 'intrinsic': {'outcome': 'accepted', 'pending': []}}))

    def test_held_codes_name_the_conflict_or_the_pending_reasons_or_say_not_usable(self):
        self.assertEqual(C.held_codes({'conflict': True, 'intrinsic': {'pending': ['A']}}), ['CONFLICT_SAME_KEY'])
        self.assertEqual(C.held_codes({'intrinsic': {'pending': ['A', 'B']}}), ['A', 'B'])
        self.assertEqual(C.held_codes({'intrinsic': {'pending': []}}), ['NOT_USABLE'])


class TestSupplierOf(unittest.TestCase):
    def test_the_reconciled_supplier_wins_then_the_text_the_record_carried_then_nothing(self):
        recs = {('ap_invoice', 'I-1'): {'fields': {'supplier_ref': 'Acme text'}}}
        self.assertEqual(C.supplier_of(_Facts({('ap_invoice', 'I-1'): {'supplier_id': 'SUP-1'}}, recs), 'ap_invoice', 'I-1'), 'SUP-1')
        self.assertEqual(C.supplier_of(_Facts({}, recs), 'ap_invoice', 'I-1'), 'Acme text')
        self.assertEqual(C.supplier_of(_Facts({('ap_invoice', 'I-1'): {'supplier_id': ''}}, recs), 'ap_invoice', 'I-1'), 'Acme text')
        self.assertEqual(C.supplier_of(_Facts({('ap_invoice', 'I-1'): {}}, recs), 'ap_invoice', 'I-1'), 'Acme text')
        self.assertIsNone(C.supplier_of(_Facts(), 'ap_invoice', 'I-1'))
        self.assertIsNone(C.supplier_of(_Facts({('ap_invoice', 'I-9'): {'supplier_id': None}}), 'ap_invoice', 'I-9'))
        self.assertEqual(C.supplier_of(_Facts({('ap_invoice', 'I-9'): {'supplier_id': 'SUP-2'}}), 'ap_invoice', 'I-9'), 'SUP-2')       # reconciled to a supplier even though the record is not pinned


if __name__ == '__main__':
    unittest.main()
