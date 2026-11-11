import copy, unittest
from . import _path                                         # noqa: F401
from .helpers_mkt import *
from apg.mkt import common as C, demo_mkt as DM, policy as MP


class TestPolicyValidation(unittest.TestCase):
    def test_the_demonstration_policy_is_valid_and_labelled_illustrative(self):
        p = DM.demo_mkt_policy()
        self.assertEqual(MP.validate_policy(p), [])
        self.assertIn('ILLUSTRATIVE', p['note'])
        self.assertIn('ILLUSTRATIVE', DM.demo_mkt_spec()['note'])

    def test_a_policy_needs_an_approval_by_a_human_with_the_role_who_is_not_the_proposer(self):
        p = DM.demo_mkt_policy(approved=False)
        self.assertFalse(MP.is_approved(p))
        self.assertFalse(MP.is_approved(MP.approve(p, 'synthetic.proposer', MP.POLICY_ROLE, 'human', '2026-09-30')))        # the proposer cannot approve
        self.assertFalse(MP.is_approved(MP.approve(p, 'bob', 'some_other_role', 'human', '2026-09-30')))
        self.assertFalse(MP.is_approved(MP.approve(p, 'bob', MP.POLICY_ROLE, 'service', '2026-09-30')))                       # a service cannot approve
        self.assertTrue(MP.is_approved(MP.approve(p, 'bob', MP.POLICY_ROLE, 'human', '2026-09-30')))

    def test_the_two_records_have_different_approval_roles(self):
        sp = DM.demo_mkt_spec(approved=False)
        self.assertFalse(MP.is_approved(MP.approve(sp, 'bob', MP.POLICY_ROLE, 'human', '2026-09-30'), MP.SPEC_ROLE))
        self.assertTrue(MP.is_approved(MP.approve(sp, 'bob', MP.SPEC_ROLE, 'human', '2026-09-30'), MP.SPEC_ROLE))

    def test_unknown_fields_and_bad_values_are_refused_naming_the_parameter(self):
        for bad, name in (({'freshness': {'quote_ranking': {'quote_max_age_days': -1, 'index_max_age_days': 1, 'fx_max_age_days': 1}}}, 'freshness'),
                          ({'fx': {'method': 'average', 'convention': 'foreign_per_aud', 'divergence_tolerance_bps': 1}}, 'fx.method'),
                          ({'demand': {'order_match_window_days': 0}}, 'demand.order_match_window_days'),
                          ({'portfolio': {'min_projects': 1}}, 'portfolio.min_projects'),
                          ({'scenarios': {'day_count_basis': 364}}, 'scenarios.day_count_basis'),
                          ({'basis': {'freight_currency': 'euro'}}, 'basis.freight_currency'),
                          ({'savings': {'min_gap_bps': 0}}, 'savings.min_gap_bps'),
                          ({'surprise': {}}, 'surprise')):
            f = DM.demo_mkt_fields()
            for k, v in bad.items():
                f[k] = dict(f.get(k, {}), **v) if isinstance(v, dict) and k not in ('surprise',) else v
            with self.assertRaises(MP.MktPolicyError, msg=name):
                MP.new_policy('X', 'p', **f)

    def test_price_paths_must_have_unique_names_and_sane_values(self):
        f = DM.demo_mkt_fields()
        f['scenarios']['price_paths'] = [{'name': 'a', 'change_bps': 0, 'horizon_days': 1}, {'name': 'a', 'change_bps': 5, 'horizon_days': 1}]
        with self.assertRaises(MP.MktPolicyError):
            MP.new_policy('X', 'p', **f)
        f['scenarios']['price_paths'] = [{'name': 'a', 'change_bps': -10000, 'horizon_days': 1}]
        with self.assertRaises(MP.MktPolicyError):
            MP.new_policy('X', 'p', **f)                                                         # a 100% fall to zero is not a price path

    def test_stage_splits_must_sum_to_the_whole_and_offsets_must_not_go_backwards(self):
        f = DM.demo_mkt_fields()
        f['scenarios']['stage'] = dict(f['scenarios']['stage'], splits_bps=[5000, 4000])
        with self.assertRaises(MP.MktPolicyError):
            MP.new_policy('X', 'p', **f)
        f = DM.demo_mkt_fields()
        f['scenarios']['stage'] = dict(f['scenarios']['stage'], offsets_days=[30, 0])
        with self.assertRaises(MP.MktPolicyError):
            MP.new_policy('X', 'p', **f)

    def test_a_stored_version_is_immutable_except_for_added_approvals(self):
        m = MktMini(approved=False)
        p = m.mp
        MP.store_policy(m.s, MP.approve(p, 'bob', MP.POLICY_ROLE, 'human', '2026-09-30'))                       # adding an approval to the same content is allowed
        changed = copy.deepcopy(p)
        changed['savings']['min_gap_bps'] = 999
        with self.assertRaises(MP.MktPolicyError):
            MP.store_policy(m.s, changed)                                                                        # same version, different content: a change is a new version

    def test_a_specification_register_validates_families_materials_and_conversions(self):
        base = dict(families={'f': {'attributes': {'a': {'match': 'exact'}, 'n': {'match': 'at_least'}}}}, materials={'M': {'family': 'f', 'attributes': {'a': 'x', 'n': 5}, 'unit': 'u'}})
        MP.new_spec('S', 'p', **base)
        for bad in (dict(base, materials={'M': {'family': 'missing', 'attributes': {}, 'unit': 'u'}}),
                    dict(base, materials={'M': {'family': 'f', 'attributes': {'zzz': 'x'}, 'unit': 'u'}}),
                    dict(base, materials={'M': {'family': 'f', 'attributes': {'n': 'five'}, 'unit': 'u'}}),                  # a numeric comparison needs a whole number
                    dict(base, materials={'M': {'family': 'f', 'attributes': {'a': 'x'}, 'unit': ''}}),
                    dict(base, unit_conversions=[{'material': 'M', 'from_unit': 'a', 'to_unit': 'b', 'factor_micro': 0}]),
                    dict(base, families={'f': {'attributes': {'a': {'match': 'roughly'}}}})):
            with self.assertRaises(MP.MktPolicyError):
                MP.new_spec('S', 'p', **bad)


class TestNoDefaults(unittest.TestCase):
    def test_every_rule_names_the_parameters_it_needs_and_none_is_defaulted(self):
        pol = MP.view(DM.demo_mkt_policy())
        for rid in MP.RULE_IDS:
            params, missing = MP.rule_params(pol, rid)
            self.assertIsNotNone(params, rid)
            self.assertEqual(missing, [])
            self.assertEqual(sorted(params), sorted(MP.RULES[rid][1]), rid)

    def test_removing_one_parameter_stops_exactly_the_rules_that_need_it_and_says_which(self):
        f = DM.demo_mkt_fields()
        del f['savings']
        pol = MP.view(MP.approve(MP.new_policy('X', 'p', **f), 'bob', MP.POLICY_ROLE, 'human', '2026-09-30'))
        for rid in MP.RULE_IDS:
            params, missing = MP.rule_params(pol, rid)
            if 'savings.min_gap_bps' in MP.RULES[rid][1]:
                self.assertIsNone(params)
                self.assertEqual(missing, ['savings.min_gap_bps'])
            else:
                self.assertIsNotNone(params, rid)

    def test_the_strict_view_raises_with_the_dotted_path_and_get_still_allows_a_test_for_absence(self):
        f = DM.demo_mkt_fields()
        del f['scenarios']['storage_cents_per_unit_per_day']
        pol = C.Strict(MP.view(MP.new_policy('X', 'p', **f)))
        with self.assertRaises(C.MissingParam) as cm:
            pol['scenarios']['storage_cents_per_unit_per_day']
        self.assertEqual(str(cm.exception), 'scenarios.storage_cents_per_unit_per_day')
        self.assertIsNone(pol['scenarios'].get('storage_cents_per_unit_per_day'))
        self.assertEqual(pol['scenarios']['financing_bps_pa'], 800)
        with self.assertRaises(C.MissingParam):
            pol['no_such_section']

    def test_every_policy_rule_is_a_rule_the_run_registers(self):
        from apg.mkt import rules as R
        self.assertEqual(set(R.PROJECT_RULE_IDS) | set(R.TENANT_RULE_IDS), set(MP.RULE_IDS))
        self.assertEqual([r for r, _ in R.PROJECT_RULES], list(R.PROJECT_RULE_IDS))
        self.assertEqual([r for r, _ in R.TENANT_RULES], list(R.TENANT_RULE_IDS))


class TestRunWithoutPolicy(unittest.TestCase):
    def test_a_run_pinned_to_a_missing_policy_value_reports_not_configured_per_rule(self):
        m = mkt_world()
        m.drop('savings.min_gap_bps')
        r = m.mres()
        runs = r['rule_runs']
        self.assertEqual(runs['MP09']['status'], 'not_configured')
        self.assertEqual(runs['MP09']['missing_parameters'], ['savings.min_gap_bps'])
        self.assertTrue(runs['MP09']['decision'])
        self.assertEqual(runs['MP02']['status'], 'evaluated')
        self.assertEqual(r['counts']['rules_not_run'], 1)

    def test_an_unapproved_policy_still_runs_but_the_result_says_it_is_unapproved(self):
        m = mkt_world(approved=False)
        r = m.mres()
        self.assertFalse(r['mkt_policy']['approved'])
        self.assertFalse(r['mkt_spec']['approved'])

    def test_a_rule_switched_off_in_the_policy_is_reported_as_switched_off(self):
        m = mkt_world()
        m.set_mkt(rules={'MP05': {'enabled': False}})
        r = m.mres()
        self.assertEqual((r['rule_runs']['MP05']['status'], r['rule_runs']['MP05']['notes']), ('disabled', ['SWITCHED_OFF_IN_POLICY']))


if __name__ == '__main__':
    unittest.main()
