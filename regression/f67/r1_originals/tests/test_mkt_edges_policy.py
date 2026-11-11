"""Edge-case tests for the procurement policy validators, the version store and the specification comparability gate.  Each table row violates exactly one conjunct of a validator (or sits exactly
on a boundary) so that no single condition can be dropped, flipped or turned into an `or` without a failure here.  Everything is synthetic."""
import copy, unittest
from . import _path                                         # noqa: F401
from .helpers_mkt import *
from apg.mkt import demo_mkt as DM, policy as MP, spec as SP


def pol_errors(section, key, value):
    """validate_policy on a policy whose only section carries one parameter."""
    return MP.validate_policy({'version': 'V', 'proposer': 'p', 'approvals': [], section: {key: value}})


class TestPolicyParameterValidators(unittest.TestCase):
    OK_FRESH = {'quote_max_age_days': 1, 'index_max_age_days': 1, 'fx_max_age_days': 1}

    def check_table(self, section, key, good, bad):
        path = f'{section}.{key}'
        for v in good:
            self.assertEqual(pol_errors(section, key, v), [], f'{path} = {v!r} must be accepted')
        for v in bad:
            self.assertEqual(pol_errors(section, key, v), [path], f'{path} = {v!r} must be refused and named by its dotted path')

    def test_positive_integer_parameters_start_at_one(self):
        for sec, key in (('demand', 'order_match_window_days'), ('supplier', 'min_sample'), ('portfolio', 'window_days'), ('portfolio', 'rate_gap_bps'), ('savings', 'min_gap_bps')):
            self.check_table(sec, key, good=[1, 2, 10 ** 6], bad=[0, -1, 1.5, True, '1', None])

    def test_minimum_counts_of_two(self):
        self.check_table('portfolio', 'min_projects', good=[2, 3], bad=[1, 0, 2.5, True, '2'])
        self.check_table('scenarios', 'context_points', good=[2, 3, 100], bad=[1, 0, -2, 2.5, 3.0, True, '2'])

    def test_basis_points_parameters_run_from_zero_to_ten_thousand_inclusive(self):
        for sec, key in (('basis', 'gst_bps'), ('scenarios', 'financing_bps_pa'), ('supplier', 'min_acceptance_bps'), ('supplier', 'min_fill_bps')):
            self.check_table(sec, key, good=[0, 1, 9999, 10000], bad=[-1, 10001, 5.5, 1000.0, True, '100', None])

    def test_non_negative_integer_parameters_accept_zero(self):
        for sec, key in (('fx', 'divergence_tolerance_bps'), ('demand', 'surplus_tolerance_bps'), ('demand', 'duplicate_window_days'), ('scenarios', 'decision_window_days'),
                         ('scenarios', 'storage_cents_per_unit_per_day'), ('scenarios', 'lead_time_variation_days')):
            self.check_table(sec, key, good=[0, 1, 500], bad=[-1, 0.5, True, '0'])

    def test_day_count_basis_is_360_or_365_only(self):
        self.check_table('scenarios', 'day_count_basis', good=[360, 365], bad=[364, 366, 0, '365', None])

    def test_watch_materials_is_a_list_of_unique_non_blank_text(self):
        self.check_table('scope', 'watch_materials', good=[[], ['A'], ['A', 'B']],
                         bad=['abc', 'A', {}, None, 5, ['A', 'A'], [''], ['  '], [1], ['A', None]])

    def test_international_bases_is_a_list_of_lower_case_text(self):
        self.check_table('basis', 'international_bases', good=[[], ['fob'], ['fob', 'cif']],
                         bad=['fob', 'ab', {}, None, ['FOB'], ['fob', 'CIF'], [''], ['  '], [5]])

    def test_critical_checks_and_checks_are_non_empty_unique_text_lists(self):
        for key in ('critical_checks', 'checks'):
            self.check_table('international', key, good=[['a'], ['a', 'b']], bad=[[], ['a', 'a'], [''], ['a', ' '], 'ab', 'a', {}, None, [1]])

    def test_price_tax_needs_exactly_the_two_sources_with_known_treatments(self):
        ok = {'supplier_quote': 'ex_gst', 'purchase_order': 'inc_gst'}
        self.check_table('basis', 'price_tax', good=[ok, {'supplier_quote': 'inc_gst', 'purchase_order': 'ex_gst'}],
                         bad=[{'supplier_quote': 'ex_gst'}, {'purchase_order': 'ex_gst'}, {}, dict(ok, extra='ex_gst'), dict(ok, purchase_order='gst_free'), dict(ok, supplier_quote=None),
                              'ex_gst', ['supplier_quote', 'purchase_order'], None])

    def test_delivery_bases_each_entry_is_a_lower_case_name_with_a_unique_list_of_known_components(self):
        good = {'delivered': {'includes': ['freight', 'handling']}, 'ex-works': {'includes': []}}
        self.check_table('basis', 'delivery_bases', good=[good],
                         bad=[{}, 'delivered', ['delivered'], None,
                              {'Delivered': {'includes': []}},                                  # not lower case
                              {'': {'includes': []}}, {' ': {'includes': []}},                  # blank name
                              {'delivered': 'freight'},                                         # entry not a dict
                              {'delivered': {'includes': [], 'extra': 1}},                      # keys other than 'includes'
                              {'delivered': {}},
                              {'delivered': {'includes': 'freight'}},                           # not a list
                              {'delivered': {'includes': ['bogus']}},                           # unknown component
                              {'delivered': {'includes': ['freight', 'freight']}},              # duplicate component
                              dict(good, bad={'includes': ['bogus']})])                         # one bad entry among good ones

    def test_required_components_need_domestic_and_international_lists_of_unique_known_components(self):
        ok = {'domestic': ['freight'], 'international': ['freight', 'duty']}
        self.check_table('basis', 'required_components', good=[ok, {'domestic': [], 'international': []}],
                         bad=[{'domestic': ['freight']}, {'international': ['freight']}, {}, dict(ok, extra=[]),
                              dict(ok, domestic='freight'),                                     # a string is not a list (its letters are not components either, but 'freight' has no repeats)
                              dict(ok, domestic='duty'),
                              dict(ok, domestic=['bogus']), dict(ok, international=['bogus']),
                              dict(ok, domestic=['freight', 'freight']), dict(ok, international=['duty', 'duty']),
                              dict(ok, domestic=None), 'domestic', None])

    def test_freshness_needs_exactly_the_three_non_negative_ages(self):
        for d in MP.DECISIONS:
            self.check_table('freshness', d, good=[dict(self.OK_FRESH, quote_max_age_days=0), self.OK_FRESH],
                             bad=[{}, {'quote_max_age_days': 1}, dict(self.OK_FRESH, extra=1), dict(self.OK_FRESH, fx_max_age_days=-1), dict(self.OK_FRESH, index_max_age_days=1.5),
                                  dict(self.OK_FRESH, quote_max_age_days=True), 5, None])

    def test_price_paths_boundaries_names_and_shape(self):
        def path(**kw):
            return dict({'name': 'a', 'change_bps': 0, 'horizon_days': 0}, **kw)
        self.check_table('scenarios', 'price_paths',
                         good=[[path()], [path(change_bps=-9999)], [path(change_bps=100000)], [path(horizon_days=0)], [path(), path(name='b')]],
                         bad=[[], None, 'a', [path(change_bps=-10000)], [path(change_bps=-10001)], [path(change_bps=100001)], [path(change_bps=0.5)], [path(change_bps=True)],
                              [path(horizon_days=-1)], [path(horizon_days=1.5)], [path(name='')], [path(name=' ')], [path(), path()], ['a'],
                              [{'name': 'a', 'change_bps': 0}], [dict(path(), extra=1)]])

    def test_stage_needs_two_positive_splits_summing_to_the_whole_and_ordered_offsets(self):
        def stage(**kw):
            return dict({'splits_bps': [5000, 5000], 'offsets_days': [0, 30], 'extra_delivery_cents': 0, 'admin_cents_per_order': 0}, **kw)
        self.check_table('scenarios', 'stage',
                         good=[stage(), stage(offsets_days=[10, 10]), stage(splits_bps=[1, 9999]), stage(splits_bps=[2500, 2500, 5000], offsets_days=[0, 1, 2])],
                         bad=[None, {}, stage(splits_bps=[10000]), stage(splits_bps=[10000], offsets_days=[0]), stage(splits_bps=[0, 10000]), stage(splits_bps=[5000, 4999]),
                              stage(splits_bps=[5000, 5001]), stage(splits_bps='ab'), stage(offsets_days=[0]), stage(offsets_days=[0, 30, 40]), stage(offsets_days=[30, 0]),
                              stage(offsets_days=[-1, 5]), stage(offsets_days='ab'), stage(extra_delivery_cents=-1), stage(admin_cents_per_order=-1), dict(stage(), extra=1),
                              {k: v for k, v in stage().items() if k != 'splits_bps'}])

    def test_fx_and_freight_choices_are_closed_lists(self):
        self.check_table('fx', 'method', good=['latest_on_or_before'], bad=['average', '', None])
        self.check_table('fx', 'convention', good=['foreign_per_aud'], bad=['aud_per_foreign', None])
        self.check_table('basis', 'freight_currency', good=['aud', 'quote_currency'], bad=['euro', 'AUD', None])
        self.check_table('basis', 'home_currency', good=['AUD'], bad=['', '  ', None, 5])

    def test_unknown_parameter_and_non_dict_section_are_named(self):
        self.assertEqual(pol_errors('fx', 'surprise', 1), ['fx.surprise'])
        self.assertEqual(MP.validate_policy({'version': 'V', 'proposer': 'p', 'fx': 'x'}), ['section fx'])
        self.assertEqual(MP.validate_policy([]), ['policy must be a dict'])
        self.assertEqual(MP.validate_policy({'version': 'V', 'proposer': 'p', 'zzz': 1}), ['unknown field zzz'])
        self.assertEqual(sorted(MP.validate_policy({'version': ' ', 'proposer': 5})), ['proposer', 'version'])


class TestPolicyRulesSwitchAndApprovals(unittest.TestCase):
    def errs(self, **extra):
        return MP.validate_policy(dict({'version': 'V', 'proposer': 'p'}, **extra))

    def test_a_rule_entry_may_only_carry_a_boolean_enabled_for_a_known_rule(self):
        for rules in ({}, {'MP05': {}}, {'MP05': {'enabled': False}}, {'MP05': {'enabled': True}}, {'MP01': {'enabled': True}, 'MPD1': {}}):
            self.assertEqual(self.errs(rules=rules), [], rules)
        for rules, msg in (({'MP99': {'enabled': True}}, 'rule MP99'),            # unknown rule id (entry itself fine)
                           ({'MP05': 'off'}, 'rule MP05'), ({'MP05': None}, 'rule MP05'), ({'MP05': True}, 'rule MP05'),       # entry not a dict
                           ({'MP05': {'enabled': True, 'x': 1}}, 'rule MP05'), ({'MP05': {'other': True}}, 'rule MP05'),         # key other than enabled
                           ({'MP05': {'enabled': 'yes'}}, 'rule MP05'), ({'MP05': {'enabled': 1}}, 'rule MP05'), ({'MP05': {'enabled': None}}, 'rule MP05')):
            self.assertEqual(self.errs(rules=rules), [msg], rules)
        self.assertEqual(self.errs(rules=['MP05']), ['rules'])

    def test_each_rule_error_names_its_own_rule(self):
        self.assertEqual(self.errs(rules={'MP01': {'enabled': 'x'}, 'MP02': {'enabled': True}, 'MP03': 5}), ['rule MP01', 'rule MP03'])

    BAD_APPROVALS = (
        {},                                                         # not a list, yet nothing in it fails
        'x', None, 5,                                               # not a list
        ['a'], [None],                                              # entries not dicts
        [{'approver': 'bob'}],                                      # wrong key set
        [{'approver': 'bob', 'role': 'r', 'kind': 'human', 'date': '2026-09-30', 'extra': 'x'}],
        [{'approver': 'bob', 'role': 'r', 'kind': 'human', 'date': ''}],           # right keys, blank value
        [{'approver': 'bob', 'role': 'r', 'kind': 'human', 'date': 5}],
        [{'approver': ' ', 'role': 'r', 'kind': 'human', 'date': '2026-09-30'}],
    )
    GOOD_APPROVAL = {'approver': 'bob', 'role': 'r', 'kind': 'human', 'date': '2026-09-30'}

    def test_approvals_must_be_a_list_of_complete_entries_in_a_policy(self):
        self.assertEqual(self.errs(approvals=[]), [])
        self.assertEqual(self.errs(approvals=[self.GOOD_APPROVAL, dict(self.GOOD_APPROVAL, approver='carol')]), [])
        for ap in self.BAD_APPROVALS:
            try:
                got = self.errs(approvals=ap)
            except Exception as e:                              # a validator must report, not crash
                self.fail(f'approvals {ap!r} raised {e!r}')
            self.assertEqual(got, ['approvals'], f'approvals {ap!r}')
        self.assertEqual(self.errs(approvals=[self.GOOD_APPROVAL, {'approver': 'x'}]), ['approvals'])      # one bad entry among good ones

    def test_approvals_must_be_a_list_of_complete_entries_in_a_specification_register(self):
        def spec_errs(ap):
            return MP.validate_spec({'version': 'V', 'proposer': 'p', 'approvals': ap, 'families': {'f': {'attributes': {'a': {'match': 'exact'}}}},
                                     'materials': {'M': {'family': 'f', 'attributes': {}, 'unit': 'u'}}})
        self.assertEqual(spec_errs([]), [])
        self.assertEqual(spec_errs([self.GOOD_APPROVAL]), [])
        for ap in self.BAD_APPROVALS:
            try:
                got = spec_errs(ap)
            except Exception as e:
                self.fail(f'approvals {ap!r} raised {e!r}')
            self.assertEqual(got, ['approvals'], f'approvals {ap!r}')
        self.assertEqual(spec_errs([self.GOOD_APPROVAL, {'approver': 'x'}]), ['approvals'])


class TestSpecRegisterValidation(unittest.TestCase):
    FAM = {'f': {'attributes': {'a': {'match': 'exact'}, 'n': {'match': 'at_least'}}}}
    MAT = {'M': {'family': 'f', 'attributes': {'a': 'x', 'n': 5}, 'unit': 'u'}}

    def errs(self, **kw):
        return MP.validate_spec(dict({'version': 'V', 'proposer': 'p', 'families': copy.deepcopy(self.FAM), 'materials': copy.deepcopy(self.MAT)}, **kw))

    def test_the_valid_register_has_no_errors(self):
        self.assertEqual(self.errs(), [])
        self.assertEqual(MP.validate_spec([]), ['register must be a dict'])

    def test_families_must_be_a_non_empty_dict(self):
        for fam in ({}, [], 'f', None, [{'a': 1}]):
            got = MP.validate_spec({'version': 'V', 'proposer': 'p', 'families': fam, 'materials': {}})
            self.assertIn('families', got, f'families {fam!r}')
        self.assertIn('families', MP.validate_spec({'version': 'V', 'proposer': 'p', 'materials': {}}))

    def test_materials_must_be_a_non_empty_dict(self):
        for mats in ({}, [], 'M', None, [{'M': 1}]):
            got = MP.validate_spec({'version': 'V', 'proposer': 'p', 'families': copy.deepcopy(self.FAM), 'materials': mats})
            self.assertIn('materials', got, f'materials {mats!r}')
        self.assertIn('materials', MP.validate_spec({'version': 'V', 'proposer': 'p', 'families': copy.deepcopy(self.FAM)}))

    def test_each_family_entry_violating_one_condition_is_named(self):
        ok_attr = {'a': {'match': 'exact'}}
        cases = (('f', {'attributes': {}}),                                    # no attributes
                 ('f', {'attributes': 'a'}),                                   # attributes not a dict
                 ('f', {'attributes': ['a']}),
                 ('f', {'attributes': ok_attr, 'extra': 1}),                   # keys other than 'attributes'
                 ('f', {}),
                 ('f', 'attributes'),                                          # entry not a dict
                 ('f', None),
                 (' ', {'attributes': ok_attr}),                               # blank family name
                 ('', {'attributes': ok_attr}))
        for f, ent in cases:
            got = MP.validate_spec({'version': 'V', 'proposer': 'p', 'families': {f: ent}, 'materials': {}})
            self.assertIn('family ' + f, got, (f, ent))

    def test_each_family_attribute_violating_one_condition_is_named(self):
        cases = ((' ', {'match': 'exact'}),                                    # blank attribute name
                 ('', {'match': 'exact'}),
                 ('a', 'exact'), ('a', None),                                  # rule not a dict
                 ('a', {'match': 'exact', 'extra': 1}), ('a', {}), ('a', {'other': 'exact'}),   # keys other than 'match'
                 ('a', {'match': 'roughly'}), ('a', {'match': 'EXACT'}), ('a', {'match': None}))
        for a, rule in cases:
            got = MP.validate_spec({'version': 'V', 'proposer': 'p', 'families': {'f': {'attributes': {a: rule}}}, 'materials': {}})
            self.assertIn(f'family f attribute {a}', got, (a, rule))
        for mode in MP.MATCH_MODES:
            got = MP.validate_spec({'version': 'V', 'proposer': 'p', 'families': {'f': {'attributes': {'a': {'match': mode}}}}, 'materials': {'M': {'family': 'f', 'attributes': {}, 'unit': 'u'}}})
            self.assertEqual(got, [], mode)

    def test_each_material_entry_violating_one_condition_is_named(self):
        good = {'family': 'f', 'attributes': {'a': 'x'}, 'unit': 'u'}
        for m, ent in (('M', dict(good, family='nope')), ('M', dict(good, unit='')), ('M', dict(good, unit=' ')), ('M', dict(good, unit=5)), ('M', dict(good, attributes=['a'])),
                       ('M', dict(good, attributes='a')), ('M', dict(good, extra=1)), ('M', {k: v for k, v in good.items() if k != 'unit'}), ('M', 'f'), ('M', None),
                       (' ', good), ('', good)):
            got = self.errs(materials={m: ent})
            self.assertIn('material ' + m, got, (m, ent))

    def test_each_material_attribute_violating_one_condition_is_named(self):
        for attrs in ({'zzz': 'x'}, {'a': ''}, {'a': ' '}, {'a': 1.5}, {'a': None}, {'n': 'five'}, {'n': 5.0}, {'n': True}, {'n': ''}):
            (a,) = attrs
            got = self.errs(materials={'M': {'family': 'f', 'attributes': attrs, 'unit': 'u'}})
            self.assertEqual(got, [f'material M attribute {a}'], attrs)
        for attrs in ({'a': 'x'}, {'a': 5}, {'n': 5}, {'n': 0}, {'a': 'x', 'n': 5}):             # an exact attribute may be text or a whole number; at_least needs a whole number
            self.assertEqual(self.errs(materials={'M': {'family': 'f', 'attributes': attrs, 'unit': 'u'}}), [], attrs)

    def test_unit_conversions_must_be_complete_and_positive(self):
        c = {'material': 'M', 'from_unit': 'kg', 'to_unit': 'tonne', 'factor_micro': 1000}
        self.assertEqual(self.errs(unit_conversions=[c]), [])
        self.assertEqual(self.errs(unit_conversions=[]), [])
        self.assertEqual(self.errs(unit_conversions=[dict(c, factor_micro=1)]), [])
        for bad in ('x', {}, None, [dict(c, factor_micro=0)], [dict(c, factor_micro=-5)], [dict(c, factor_micro=1.5)], [dict(c, factor_micro=True)], [dict(c, material='')],
                    [dict(c, from_unit=' ')], [dict(c, to_unit='')], [dict(c, extra=1)], [{'material': 'M'}], ['M'], [c, dict(c, to_unit='')]):
            self.assertEqual(self.errs(unit_conversions=bad), ['unit_conversions'], bad)

    def test_unknown_field_version_and_proposer_are_named(self):
        self.assertEqual(self.errs(surprise=1), ['unknown field surprise'])
        self.assertEqual(sorted(MP.validate_spec({'version': '', 'proposer': None, 'families': copy.deepcopy(self.FAM), 'materials': copy.deepcopy(self.MAT)})), ['proposer', 'version'])


class TestPolicyStoreAndErrors(unittest.TestCase):
    def test_new_policy_and_new_spec_refuse_a_bad_record_and_name_every_problem(self):
        with self.assertRaises(MP.MktPolicyError) as cm:
            MP.new_policy('V', 'p', fx={'method': 'average', 'convention': 'foreign_per_aud', 'divergence_tolerance_bps': -1})
        self.assertEqual(str(cm.exception), 'fx.method; fx.divergence_tolerance_bps')
        with self.assertRaises(MP.MktPolicyError) as cm:
            MP.new_spec('V', 'p', families={}, materials={})
        self.assertEqual(str(cm.exception), 'families; materials')

    def test_the_store_refuses_an_invalid_record_that_bypassed_the_constructors(self):
        m = MktMini(approved=False)
        bad_p = copy.deepcopy(m.mp)
        bad_p['version'] = 'BAD-P'
        bad_p['savings'] = {'min_gap_bps': 0}
        with self.assertRaises(MP.MktPolicyError) as cm:
            MP.store_policy(m.s, bad_p)
        self.assertEqual(str(cm.exception), 'savings.min_gap_bps')
        self.assertIsNone(m.s.get(MP.POLICY_KIND, 'BAD-P'))
        bad_s = copy.deepcopy(m.sp)
        bad_s['version'] = 'BAD-S'
        bad_s['materials'] = {}
        with self.assertRaises(MP.MktPolicyError) as cm:
            MP.store_spec(m.s, bad_s)
        self.assertEqual(str(cm.exception), 'materials')
        self.assertIsNone(m.s.get(MP.SPEC_KIND, 'BAD-S'))

    def test_a_stored_version_refuses_changed_content_even_when_the_earlier_approvals_are_kept(self):
        m = MktMini(approved=False)
        approved = MP.approve(m.mp, 'bob', MP.POLICY_ROLE, 'human', '2026-09-30')
        MP.store_policy(m.s, approved)
        changed = copy.deepcopy(approved)
        changed['savings']['min_gap_bps'] = 999                                  # same approvals, different content
        with self.assertRaises(MP.MktPolicyError) as cm:
            MP.store_policy(m.s, changed)
        self.assertIn('already exists with different content', str(cm.exception))
        extended = MP.approve(changed, 'carol', MP.POLICY_ROLE, 'human', '2026-10-01')       # new approval does not excuse a changed content either
        with self.assertRaises(MP.MktPolicyError):
            MP.store_policy(m.s, extended)

    def test_a_stored_version_refuses_a_rewritten_or_removed_approval_with_identical_content(self):
        m = MktMini(approved=False)
        approved = MP.approve(m.mp, 'bob', MP.POLICY_ROLE, 'human', '2026-09-30')
        MP.store_policy(m.s, approved)
        removed = copy.deepcopy(approved)
        removed['approvals'] = []
        with self.assertRaises(MP.MktPolicyError):
            MP.store_policy(m.s, removed)                                           # content identical, an approval withdrawn
        rewritten = copy.deepcopy(approved)
        rewritten['approvals'][0]['approver'] = 'mallory'
        with self.assertRaises(MP.MktPolicyError):
            MP.store_policy(m.s, rewritten)                                         # content identical, an approval altered
        self.assertEqual(m.s.get(MP.POLICY_KIND, m.mp['version']).payload['approvals'], approved['approvals'])

    def test_a_stored_version_accepts_only_appended_approvals_and_the_same_for_a_register(self):
        m = MktMini(approved=False)
        a1 = MP.approve(m.mp, 'bob', MP.POLICY_ROLE, 'human', '2026-09-30')
        a2 = MP.approve(a1, 'carol', MP.POLICY_ROLE, 'human', '2026-10-01')
        MP.store_policy(m.s, a1)
        MP.store_policy(m.s, a2)
        self.assertEqual(m.s.get(MP.POLICY_KIND, m.mp['version']).payload['approvals'], a2['approvals'])
        s1 = MP.approve(m.sp, 'bob', MP.SPEC_ROLE, 'human', '2026-09-30')
        MP.store_spec(m.s, s1)
        self.assertEqual(m.s.get(MP.SPEC_KIND, m.sp['version']).payload['approvals'], s1['approvals'])
        changed = copy.deepcopy(s1)
        changed['materials']['MAT-STEEL']['unit'] = 'kg'
        with self.assertRaises(MP.MktPolicyError):
            MP.store_spec(m.s, changed)
        removed = copy.deepcopy(s1)
        removed['approvals'] = []
        with self.assertRaises(MP.MktPolicyError):
            MP.store_spec(m.s, removed)

    def test_a_new_version_is_stored_alongside_the_old_one(self):
        m = MktMini(approved=False)
        v2 = copy.deepcopy(m.mp)
        v2['version'] = 'V2'
        v2['savings'] = {'min_gap_bps': 999}
        MP.store_policy(m.s, v2)
        self.assertEqual(m.s.get(MP.POLICY_KIND, 'V2').payload['savings']['min_gap_bps'], 999)
        self.assertEqual(m.s.get(MP.POLICY_KIND, m.mp['version']).payload['savings']['min_gap_bps'], 300)


# ------------------------------------------------------------------------------------------------ the specification gate
def rdg(value, verified=True):
    return {'value': value, 'verified': verified, 'extracted_by': 'ai', 'verified_by': 'bob' if verified else None, 'ref': 'quote_reading/x', 'revision': 1}


def spec_of(**kw):
    fields = dict(families={'f': {'attributes': {'ex': {'match': 'exact'}, 'lo': {'match': 'at_least'}, 'hi': {'match': 'at_most'}}}},
                  materials={'REQ': {'family': 'f', 'attributes': {'ex': 'x', 'lo': 10, 'hi': 10}, 'unit': 'tonne'},
                             'SAME': {'family': 'f', 'attributes': {'ex': 'x', 'lo': 10, 'hi': 10}, 'unit': 'tonne'},
                             'UP': {'family': 'f', 'attributes': {'ex': 'x', 'lo': 11, 'hi': 11}, 'unit': 'tonne'},
                             'DOWN': {'family': 'f', 'attributes': {'ex': 'x', 'lo': 9, 'hi': 9}, 'unit': 'tonne'},
                             'BARE': {'family': 'f', 'attributes': {}, 'unit': 'tonne'}})
    fields.update(kw)
    return MP.spec_view(MP.new_spec('S', 'p', **fields))


class TestComparisonRules(unittest.TestCase):
    def test_cmp_boundaries_for_each_rule(self):
        # (rule, required, offered, expected)
        for rule, req, off, want in (('exact', 'x', 'x', True), ('exact', 'x', 'y', False), ('exact', 5, '5', True), ('exact', 5, 6, False),
                                     ('at_least', 10, 10, True), ('at_least', 10, 11, True), ('at_least', 10, 9, False),
                                     ('at_most', 10, 10, True), ('at_most', 10, 9, True), ('at_most', 10, 11, False),
                                     ('at_least', 10, None, None), ('at_most', 10, None, None)):
            self.assertIs(SP._cmp(rule, req, off), want, (rule, req, off))

    def test_at_most_attribute_passes_at_the_limit_and_below_and_fails_above(self):
        sp = spec_of(families={'f': {'attributes': {'hi': {'match': 'at_most'}}}},
                     materials={'REQ': {'family': 'f', 'attributes': {'hi': 10}, 'unit': 'u'}, 'EQ': {'family': 'f', 'attributes': {'hi': 10}, 'unit': 'u'},
                                'LOW': {'family': 'f', 'attributes': {'hi': 9}, 'unit': 'u'}, 'HIGH': {'family': 'f', 'attributes': {'hi': 11}, 'unit': 'u'}})
        for off, status in (('EQ', 'pass'), ('LOW', 'pass'), ('HIGH', 'fail')):
            r = SP.attribute_check(sp, 'REQ', off, {}, 'purchase_order')
            self.assertEqual(r['status'], status, off)
        r = SP.attribute_check(sp, 'REQ', 'EQ', {'hi': rdg('10')}, 'quote')                  # a verified reading exactly at the limit
        self.assertEqual((r['status'], r['verified']), ('pass', True))
        r = SP.attribute_check(sp, 'REQ', 'EQ', {'hi': rdg('11')}, 'quote')
        self.assertEqual(r['status'], 'fail')

    def test_at_least_and_at_most_together_on_boundaries_through_the_catalogue(self):
        sp = spec_of()
        for off, want in (('SAME', 'pass'), ('UP', 'fail'), ('DOWN', 'fail')):     # 'lo' passes for SAME/UP, 'hi' passes for SAME/DOWN: only SAME meets both
            self.assertEqual(SP.attribute_check(sp, 'REQ', off, {}, 'purchase_order')['status'], want, off)


class TestAttributeReasons(unittest.TestCase):
    def test_a_fully_passing_check_carries_no_reasons(self):
        sp = spec_of()
        r = SP.attribute_check(sp, 'REQ', 'SAME', {}, 'purchase_order')
        self.assertEqual((r['status'], r['reasons']), ('pass', []))
        r = SP.attribute_check(sp, 'REQ', 'SAME', {'ex': rdg('x'), 'lo': rdg('10'), 'hi': rdg('10')}, 'quote')
        self.assertEqual((r['status'], r['reasons'], r['verified']), ('pass', [], True))

    def test_only_an_unassessable_attribute_adds_the_cannot_be_assessed_reason(self):
        sp = spec_of()
        r = SP.attribute_check(sp, 'REQ', 'BARE', {'ex': rdg('x'), 'lo': rdg('10')}, 'quote')       # ex and lo verified-pass, hi has nothing
        self.assertEqual(r['status'], 'unknown')
        self.assertEqual(r['reasons'], ['attribute hi cannot be assessed (nothing usable offered)'])
        self.assertEqual([(a['attribute'], a['result']) for a in r['attributes']], [('ex', 'pass'), ('hi', 'unknown'), ('lo', 'pass')])

    def test_a_failing_attribute_reason_is_not_also_reported_as_unassessable(self):
        sp = spec_of()
        r = SP.attribute_check(sp, 'REQ', 'DOWN', {}, 'purchase_order')
        self.assertEqual(r['reasons'], ['attribute lo: 9 offered against 10 required (at_least)'])

    def test_a_verified_reading_that_agrees_with_the_catalogue_raises_no_disagreement(self):
        sp = spec_of()
        r = SP.attribute_check(sp, 'REQ', 'SAME', {'ex': rdg('x'), 'lo': rdg('10'), 'hi': rdg('10')}, 'quote')
        self.assertFalse(any('disagrees' in x for x in r['reasons']))
        self.assertEqual(r['reasons'], [])

    def test_a_verified_exact_reading_that_differs_from_the_catalogue_is_reported_once_with_both_values(self):
        sp = spec_of()
        r = SP.attribute_check(sp, 'REQ', 'SAME', {'ex': rdg('y'), 'lo': rdg('10'), 'hi': rdg('10')}, 'quote')
        self.assertEqual(r['status'], 'fail')
        self.assertEqual(r['reasons'][0], 'attribute ex: the verified reading (y) disagrees with the catalogue (x)')
        self.assertEqual(len(r['reasons']), 2)                                      # the disagreement and the resulting failure

    def test_a_verified_numeric_reading_that_differs_from_the_catalogue_is_not_a_disagreement(self):
        sp = spec_of()                                                              # 'lo' is at_least and 'hi' is at_most: the reading simply replaces the catalogue value
        r = SP.attribute_check(sp, 'REQ', 'SAME', {'lo': rdg('50'), 'hi': rdg('3')}, 'quote')
        self.assertEqual(r['status'], 'pass')
        self.assertEqual(r['reasons'], [])
        self.assertEqual({a['attribute']: (a['offered'], a['source']) for a in r['attributes']}['lo'], (50, 'verified_reading'))

    def test_a_verified_exact_reading_with_no_catalogue_value_is_not_a_disagreement(self):
        sp = spec_of(families={'f': {'attributes': {'a': {'match': 'exact'}}}}, materials={'REQ': {'family': 'f', 'attributes': {'a': 'x'}, 'unit': 'u'}, 'OFF': {'family': 'f', 'attributes': {}, 'unit': 'u'}})
        for value, status, reasons in (('x', 'pass', []), ('y', 'fail', ['attribute a: y offered against x required (exact)'])):
            r = SP.attribute_check(sp, 'REQ', 'OFF', {'a': rdg(value)}, 'quote')
            self.assertEqual((r['status'], r['reasons']), (status, reasons), value)


class TestUnitCheckEdges(unittest.TestCase):
    CONV = [{'material': 'MAT-B', 'from_unit': 'kg', 'to_unit': 'tonne', 'factor_micro': 1000}]

    def spec(self, conversions=None):
        return spec_of(families={'f': {'attributes': {'a': {'match': 'exact'}}}},
                       materials={'MAT-A': {'family': 'f', 'attributes': {'a': 'x'}, 'unit': 'tonne'}, 'MAT-B': {'family': 'f', 'attributes': {'a': 'x'}, 'unit': 'kg'}},
                       unit_conversions=self.CONV if conversions is None else conversions)

    def test_the_required_unit_comes_from_the_register_even_when_the_master_has_none(self):
        u = SP.unit_check(self.spec(), 'MAT-A', 'MAT-A', {'unit': rdg('tonne')}, None, 'tonne')
        self.assertEqual((u['status'], u['to'], u['from'], u['inferred']), ('same', 'tonne', 'tonne', False))

    def test_the_required_unit_falls_back_to_the_master_when_the_material_is_not_in_the_register(self):
        u = SP.unit_check(self.spec(), 'MAT-NOPE', 'MAT-A', {'unit': rdg('tonne')}, 'tonne', None)
        self.assertEqual((u['status'], u['to'], u['from']), ('same', 'tonne', 'tonne'))

    def test_the_offered_unit_comes_from_the_register_when_there_is_no_verified_reading_even_if_the_master_has_none(self):
        u = SP.unit_check(self.spec(), 'MAT-A', 'MAT-B', {}, 'tonne', None)
        self.assertEqual((u['from'], u['to']), ('kg', 'tonne'))
        self.assertEqual((u['status'], u['inferred']), ('unverified', True))                  # conversion declared but the offered unit is only inferred
        self.assertEqual(u['factor_micro'], 1000)
        self.assertEqual(u['why'], 'conversion declared, but the offered unit is inferred, not verified')

    def test_the_offered_unit_falls_back_to_the_master_when_the_material_is_not_in_the_register(self):
        u = SP.unit_check(self.spec(), 'MAT-A', 'MAT-NOPE', {}, 'tonne', 'tonne')
        self.assertEqual((u['from'], u['status'], u['inferred']), ('tonne', 'unverified', True))
        u = SP.unit_check(self.spec(), 'MAT-A', 'MAT-NOPE', {'unit': rdg('tonne')}, 'tonne', 'kg')          # a verified reading outranks the master
        self.assertEqual((u['from'], u['status'], u['inferred']), ('tonne', 'same', False))

    def test_one_unit_missing_is_unverified_whichever_side_is_missing(self):
        sp = self.spec()
        u = SP.unit_check(sp, 'MAT-NOPE', 'MAT-A', {}, None, 'tonne')                           # required unit unknown, offered known
        self.assertEqual((u['status'], u['from'], u['to'], u['why']), ('unverified', 'tonne', None, 'a unit is not recorded'))
        u = SP.unit_check(sp, 'MAT-A', 'MAT-NOPE', {}, 'tonne', None)                           # offered unit unknown, required known
        self.assertEqual((u['status'], u['from'], u['to'], u['why']), ('unverified', None, 'tonne', 'a unit is not recorded'))
        u = SP.unit_check(sp, 'MAT-NOPE', 'MAT-NOPE', {}, None, None)
        self.assertEqual(u['status'], 'unverified')
        u = SP.unit_check(sp, 'MAT-NOPE', 'MAT-A', {'unit': rdg('kg')}, None, None)             # verified offered unit, required unit unknown
        self.assertEqual((u['status'], u['from'], u['to'], u['why']), ('unverified', 'kg', None, 'a unit is not recorded'))

    def test_inferred_follows_whether_the_offered_unit_was_verified_in_every_branch(self):
        sp = self.spec()
        # no unit recorded: a verified offered unit is not inferred (required unit unknown), no reading with the offered unit unknown is inferred
        self.assertFalse(SP.unit_check(sp, 'MAT-NOPE', 'MAT-A', {'unit': rdg('kg')}, None, None)['inferred'])
        self.assertTrue(SP.unit_check(sp, 'MAT-NOPE', 'MAT-A', {}, None, None)['inferred'])
        # same unit
        self.assertFalse(SP.unit_check(sp, 'MAT-A', 'MAT-A', {'unit': rdg('tonne')}, 'tonne', 'tonne')['inferred'])
        self.assertTrue(SP.unit_check(sp, 'MAT-A', 'MAT-A', {}, 'tonne', 'tonne')['inferred'])
        # converted / unverified conversion
        v = SP.unit_check(sp, 'MAT-A', 'MAT-B', {'unit': rdg('kg')}, 'tonne', 'kg')
        self.assertEqual((v['status'], v['inferred'], v['why'], v['factor_micro']), ('converted', False, '', 1000))
        u = SP.unit_check(sp, 'MAT-A', 'MAT-B', {}, 'tonne', 'kg')
        self.assertEqual((u['status'], u['inferred']), ('unverified', True))
        # no declared conversion
        v = SP.unit_check(sp, 'MAT-A', 'MAT-A', {'unit': rdg('lb')}, 'tonne', 'tonne')
        self.assertEqual((v['status'], v['inferred'], v['factor_micro'], v['why']), ('incompatible', False, None, 'no declared conversion from lb to tonne'))
        u = SP.unit_check(sp, 'MAT-A', 'MAT-B', {'unit': rdg('kg', verified=False)}, 'tonne', 'kg')           # unverified reading is ignored; kg->tonne is declared for MAT-B
        self.assertEqual((u['status'], u['inferred']), ('unverified', True))
        sp2 = self.spec(conversions=[])
        u = SP.unit_check(sp2, 'MAT-A', 'MAT-B', {}, 'tonne', 'kg')
        self.assertEqual((u['status'], u['inferred'], u['from']), ('incompatible', True, 'kg'))

    def test_a_declared_conversion_needs_the_material_and_both_units_to_match(self):
        verified = {'unit': rdg('kg')}
        # the right units declared for some other material: not applicable
        sp = self.spec([{'material': 'MAT-OTHER', 'from_unit': 'kg', 'to_unit': 'tonne', 'factor_micro': 1000}])
        self.assertEqual(SP.unit_check(sp, 'MAT-A', 'MAT-B', verified, 'tonne', 'kg')['status'], 'incompatible')
        # the right material but a different from-unit
        sp = self.spec([{'material': 'MAT-B', 'from_unit': 'g', 'to_unit': 'tonne', 'factor_micro': 1000}])
        self.assertEqual(SP.unit_check(sp, 'MAT-A', 'MAT-B', verified, 'tonne', 'kg')['status'], 'incompatible')
        # the right material and from-unit but a different to-unit
        sp = self.spec([{'material': 'MAT-B', 'from_unit': 'kg', 'to_unit': 'lb', 'factor_micro': 1000}])
        self.assertEqual(SP.unit_check(sp, 'MAT-A', 'MAT-B', verified, 'tonne', 'kg')['status'], 'incompatible')
        # a conversion in the wrong direction
        sp = self.spec([{'material': 'MAT-B', 'from_unit': 'tonne', 'to_unit': 'kg', 'factor_micro': 1000}])
        self.assertEqual(SP.unit_check(sp, 'MAT-A', 'MAT-B', verified, 'tonne', 'kg')['status'], 'incompatible')
        # declared against either material of the pair is honoured
        for mat in ('MAT-A', 'MAT-B'):
            sp = self.spec([{'material': mat, 'from_unit': 'kg', 'to_unit': 'tonne', 'factor_micro': 7}])
            u = SP.unit_check(sp, 'MAT-A', 'MAT-B', verified, 'tonne', 'kg')
            self.assertEqual((u['status'], u['factor_micro']), ('converted', 7), mat)
        # the first matching declaration is used when others do not match
        sp = self.spec([{'material': 'MAT-OTHER', 'from_unit': 'kg', 'to_unit': 'tonne', 'factor_micro': 1},
                        {'material': 'MAT-B', 'from_unit': 'kg', 'to_unit': 'tonne', 'factor_micro': 9}])
        self.assertEqual(SP.unit_check(sp, 'MAT-A', 'MAT-B', verified, 'tonne', 'kg')['factor_micro'], 9)


if __name__ == '__main__':
    unittest.main()
