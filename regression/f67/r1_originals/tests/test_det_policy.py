import copy
import json
import os
import unittest
from . import _path                                         # noqa: F401
from ._path import HERE_ROOT
from .helpers_det import DetMini
from .helpers_ingest import World
from apg.det import demo_det as DD, policy as DP


class TestValidation(unittest.TestCase):
    def good(self):
        return DD.demo_det_policy()

    def test_the_demonstration_policy_is_valid_and_every_rule_has_an_entry(self):
        p = self.good()
        self.assertEqual(DP.validate_policy(p), [])
        self.assertEqual(sorted(p['rules']), sorted(DP.RULES))

    def test_every_parameter_rejects_floats_bools_negatives_and_text(self):
        for rid, (_, params, _) in DP.RULES.items():
            for k in params:
                for bad in (1.5, True, -1, 'x', None):
                    p = self.good()
                    p['rules'][rid][k] = bad
                    self.assertTrue(DP.validate_policy(p), f'{rid}.{k}={bad!r} was accepted')

    def test_unknown_rules_parameters_and_fields_are_refused(self):
        p = self.good()
        p['rules']['R99'] = {}
        self.assertTrue(DP.validate_policy(p))
        p = self.good()
        p['rules']['R01']['mystery'] = 1
        self.assertTrue(DP.validate_policy(p))
        p = self.good()
        p['extra'] = 1
        self.assertTrue(DP.validate_policy(p))

    def test_aggregation_keys_must_include_the_project_and_be_known_and_unique(self):
        for keys in (['supplier'], ['project', 'colour'], ['project', 'project'], []):
            p = self.good()
            p['rules']['AGG']['keys'] = keys
            self.assertTrue(DP.validate_policy(p), keys)

    def test_pairs_have_exactly_the_declared_shape(self):
        for pairs in ([], [{'quote': 'Q'}], [{'quote': 'Q', 'reference_kind': 'invoice', 'reference': 'R'}], [{'quote': '', 'reference_kind': 'quote', 'reference': 'R'}]):
            p = self.good()
            p['rules']['R07']['pairs'] = pairs
            self.assertTrue(DP.validate_policy(p), pairs)

    def test_severity_bands_and_noise_are_validated(self):
        p = self.good()
        p['severity_bands'] = [{'min_cents': 0, 'label': 'a'}, {'min_cents': 0, 'label': 'b'}]
        self.assertTrue(DP.validate_policy(p))
        p = self.good()
        p['noise'] = {'renotify_on': ['something_else']}
        self.assertTrue(DP.validate_policy(p))
        p = self.good()
        p['noise'] = {'suppression_days': -1}
        self.assertTrue(DP.validate_policy(p))

    def test_a_decline_of_more_than_all_of_the_output_or_none_is_refused(self):
        for v in (0, 10001):
            p = self.good()
            p['rules']['LAB']['decline_bps'] = v
            self.assertTrue(DP.validate_policy(p))

    def test_fewer_than_two_events_is_not_a_pattern(self):
        p = self.good()
        p['rules']['DEF']['min_events'] = 1
        self.assertTrue(DP.validate_policy(p))


class TestNoDefaults(unittest.TestCase):
    def test_a_missing_entry_or_parameter_is_reported_as_missing_never_defaulted(self):
        p = self.good_without()
        for rid in DP.RULES:
            params, missing = DP.rule_params(p, rid)
            self.assertIsNone(params)
            self.assertTrue(missing)
        p = DD.demo_det_policy()
        del p['rules']['R01']['tolerance_bps']
        self.assertEqual(DP.rule_params(p, 'R01'), (None, ['tolerance_bps']))

    def good_without(self):
        return DP.new_policy('D-x', 'pat')

    def test_a_rule_with_no_parameters_still_needs_an_entry(self):
        p = DP.new_policy('D-x', 'pat')
        self.assertEqual(DP.rule_params(p, 'R02'), (None, ['(rule entry)']))
        p = DP.new_policy('D-x', 'pat', rules={'R02': {}})
        self.assertEqual(DP.rule_params(p, 'R02'), ({}, []))

    def test_every_value_in_the_demonstration_policy_has_a_stated_origin(self):
        p = DD.demo_det_policy()
        for rid, ent in p['rules'].items():
            for k in ent:
                if k == 'enabled':
                    continue
                self.assertIn(f'{rid}.{k}', DD.ORIGIN, f'{rid}.{k} has no stated origin')

    def test_the_demonstration_values_that_claim_to_come_from_the_test_thresholds_file_do_match_it(self):
        t = json.load(open(os.path.join(HERE_ROOT, 'builder_zero', 'scenarios', 'test_thresholds.json')))
        p = DD.demo_det_policy()
        checked = 0
        for key, origin in DD.ORIGIN.items():
            if not origin.startswith('test_thresholds.json ('):
                continue
            name, value = origin[len('test_thresholds.json ('):-1].split(' ')
            if key.startswith('AGG.keys'):
                continue
            rid, k = key.split('.')
            self.assertEqual(t[name], int(value), key)
            self.assertEqual(p['rules'][rid][k], int(value), key)
            checked += 1
        self.assertEqual(checked, 6)

    def test_the_one_value_that_departs_from_the_test_thresholds_file_says_so(self):
        t = json.load(open(os.path.join(HERE_ROOT, 'builder_zero', 'scenarios', 'test_thresholds.json')))
        self.assertEqual(t['aggregation_keys'], ['project'])
        self.assertNotEqual(DD.demo_det_policy()['rules']['AGG']['keys'], t['aggregation_keys'])
        self.assertIn('F-23', DD.ORIGIN['AGG.keys'])


class TestApproval(unittest.TestCase):
    def test_a_policy_is_approved_only_by_a_different_human_in_the_policy_owner_role(self):
        p = DP.new_policy('D-1', 'pat')
        self.assertFalse(DP.is_approved(p))
        for who, role, kind in (('pat', DP.POLICY_ROLE, 'human'), ('sam', 'someone_else', 'human'), ('sam', DP.POLICY_ROLE, 'service')):
            self.assertFalse(DP.is_approved(DP.approve(p, who, role, kind, '2026-10-01')), (who, role, kind))
        self.assertTrue(DP.is_approved(DP.approve(p, 'sam', DP.POLICY_ROLE, 'human', '2026-10-01')))

    def test_a_stored_version_is_immutable_but_an_approval_can_be_appended(self):
        w = World()
        s = w.who('t', 'zero_one')
        p = DP.new_policy('D-1', 'pat', rules={'R01': {'tolerance_bps': 500}})
        DP.store_policy(s, p)
        DP.store_policy(s, p)                                                                # the same content again is fine
        with self.assertRaises(DP.DetPolicyError):
            DP.store_policy(s, DP.new_policy('D-1', 'pat', rules={'R01': {'tolerance_bps': 600}}))
        DP.store_policy(s, DP.approve(p, 'sam', DP.POLICY_ROLE, 'human', '2026-10-01'))
        self.assertTrue(DP.is_approved(s.get(DP.POLICY_KIND, 'D-1').payload))
        with self.assertRaises(DP.DetPolicyError):                                           # an approval cannot be removed again
            DP.store_policy(s, p)

    def test_an_invalid_policy_is_not_stored(self):
        w = World()
        s = w.who('t', 'zero_one')
        with self.assertRaises(DP.DetPolicyError):
            DP.new_policy('D-2', 'pat', rules={'R01': {'tolerance_bps': -1}})
        self.assertIsNone(s.get(DP.POLICY_KIND, 'D-2'))

    def test_the_view_flags_approval_without_changing_the_policy(self):
        p = DP.new_policy('D-1', 'pat')
        v = DP.view(p)
        self.assertEqual((v['_approved'], 'approvals' in v), (False, True))
        self.assertNotIn('_approved', p)


class TestSeverityBands(unittest.TestCase):
    def test_the_band_is_the_highest_minimum_not_above_the_amount(self):
        p = DP.new_policy('D-1', 'pat', severity_bands=[{'min_cents': 100, 'label': 'b'}, {'min_cents': 0, 'label': 'a'}, {'min_cents': 1000, 'label': 'c'}])
        self.assertEqual([DP.severity_of(p, c) for c in (0, 99, 100, 999, 1000, 10 ** 12)], ['a', 'a', 'b', 'b', 'c', 'c'])
        self.assertEqual([DP.severity_rank(p, x) for x in ('a', 'b', 'c', 'zzz', 'unrated')], [1, 2, 3, 0, 0])

    def test_with_no_band_below_the_amount_the_result_is_unrated_not_the_lowest_band(self):
        p = DP.new_policy('D-1', 'pat', severity_bands=[{'min_cents': 100, 'label': 'b'}])
        self.assertEqual(DP.severity_of(p, 50), 'unrated')
