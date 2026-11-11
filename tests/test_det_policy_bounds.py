"""The detection policy validator: every accepted range is pinned on both sides of its edge, and every structural rule of a policy has a test that breaks exactly that rule."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_det import DetMini
from apg.det import policy as DP


class TestBoundariesOfTheValidator(unittest.TestCase):
    def ok(self, **fields):
        base = dict(version='V', proposer='p', approvals=[])
        base.update(fields)
        return DP.validate_policy(base)

    def test_each_numeric_parameter_accepts_its_lowest_value_and_refuses_the_one_below(self):
        for rule, param, lowest in (('R09', 'movement_abs_cents', 1), ('AGG', 'window_days', 1), ('AGG', 'single_order_abs_cents', 1), ('DLY', 'min_overlap_days', 1), ('LAB', 'baseline_weeks', 1),
                                    ('LAB', 'recent_weeks', 1), ('LAB', 'decline_bps', 1), ('DEF', 'min_events', 2), ('R01', 'tolerance_bps', 0), ('R04', 'unresolved_days', 0), ('R04B', 'min_age_days', 0),
                                    ('R05', 'grace_days', 0), ('R06', 'warning_days', 0), ('R08', 'min_excess_days', 0)):
            self.assertEqual(self.ok(rules={rule: {param: lowest}}), [], (rule, param, lowest))
            self.assertTrue(self.ok(rules={rule: {param: lowest - 1}}), (rule, param, lowest - 1))
            self.assertTrue(self.ok(rules={rule: {param: True}}), (rule, param, 'bool'))
            self.assertTrue(self.ok(rules={rule: {param: '5'}}), (rule, param, 'text'))
            self.assertTrue(self.ok(rules={rule: {param: 1.5}}), (rule, param, 'float'))
        self.assertEqual(self.ok(rules={'LAB': {'decline_bps': 10000}}), [])
        self.assertTrue(self.ok(rules={'LAB': {'decline_bps': 10001}}))

    def test_the_version_and_the_proposer_must_be_non_empty_text(self):
        for v in ('', 5, None, ['x']):
            self.assertIn('version', DP.validate_policy({'version': v, 'proposer': 'p', 'approvals': []}), repr(v))
            self.assertIn('proposer', DP.validate_policy({'version': 'V', 'proposer': v, 'approvals': []}), repr(v))
        self.assertEqual(DP.validate_policy({'version': 'V', 'proposer': 'p', 'approvals': []}), [])
        self.assertEqual(DP.validate_policy([]), ['policy must be a dict'])

    def test_an_approval_must_be_a_complete_record_of_text_values(self):
        good = {'approver': 'a', 'role': 'detection_policy_owner', 'kind': 'human', 'date': '2026-09-30'}
        self.assertEqual(self.ok(approvals=[good]), [])
        for ap in (None, 5, [5], [dict(good, extra='x')], [{k: v for k, v in good.items() if k != 'date'}], [dict(good, approver='')], [dict(good, role=5)], [dict(good, kind=None)], [good, 'x']):
            self.assertIn('approvals', DP.validate_policy({'version': 'V', 'proposer': 'p', 'approvals': ap}), repr(ap))

    def test_severity_bands_must_be_a_non_empty_list_of_distinct_named_thresholds(self):
        good = [{'min_cents': 0, 'label': 'low'}, {'min_cents': 10, 'label': 'high'}]
        self.assertEqual(self.ok(severity_bands=good), [])
        for sb in ([], 'x', [5], [{'min_cents': 0}], [{'min_cents': 0, 'label': 'a', 'extra': 1}], [{'min_cents': -1, 'label': 'a'}], [{'min_cents': 'x', 'label': 'a'}], [{'min_cents': 0, 'label': 5}],
                   [{'min_cents': 0, 'label': ''}], [{'min_cents': 0, 'label': 'a'}, {'min_cents': 0, 'label': 'b'}], good + [5]):
            self.assertIn('severity_bands', self.ok(severity_bands=sb), repr(sb))

    def test_instruction_types_must_be_a_non_empty_list_of_non_empty_text(self):
        self.assertEqual(self.ok(rules={'R04B': {'instruction_types': ['client_instruction']}}), [])
        for v in ([], 'x', [5], [''], ['a', 7], None):
            self.assertTrue(self.ok(rules={'R04B': {'instruction_types': v}}), repr(v))

    def test_an_invalid_policy_is_refused_when_stored_and_nothing_is_written(self):
        m = DetMini()
        bad = {'version': 'BAD-1', 'proposer': 'p', 'approvals': [], 'rules': {'R01': {'tolerance_bps': -1}}}
        with self.assertRaises(DP.DetPolicyError):
            DP.store_policy(m.s, bad)
        self.assertIsNone(m.s.get(DP.POLICY_KIND, 'BAD-1'))
        with self.assertRaises(DP.DetPolicyError):
            DP.new_policy('BAD-2', 'p', rules={'R01': {'tolerance_bps': -1}})


if __name__ == '__main__':
    unittest.main()
