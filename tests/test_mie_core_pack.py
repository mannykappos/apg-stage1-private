"""MIE-1 pack validation, publication, activation and the signal-influence policy (PK-01..PK-33, AD-13, AD-14, AD-15)."""
import copy, hashlib, unittest
from . import _path                                         # noqa: F401
from .helpers_mie import (EVAL, LIMITS, P_ABSENT, P_ALWAYS, P_QUAL, World, code, ob, p_gap, p_na, p_need, p_sig, pack_with, rule, series, UP)
from mie.core import canon, pack as P
from mie.core.vocab import MieError
from mie.packs import synthetic as SP


def refused(doc_or_bytes):
    b = doc_or_bytes if isinstance(doc_or_bytes, (bytes, bytearray)) else canon.dumps(doc_or_bytes)
    try:
        P.validate(b, LIMITS)
    except MieError as e:
        return e.code
    return None


class TestValidPack(unittest.TestCase):
    def test_PK_01_a_valid_synthetic_pack_publishes_with_its_canonical_hash(self):
        """PK-01."""
        w = World(activate=False)
        self.assertEqual(w.pin['pack_hash'], hashlib.sha256(canon.dumps(SP.pack())).hexdigest())
        self.assertEqual(w.e.validate_pack('tA', SP.pack_bytes())['pin'], w.pin)
        got = w.e.get_pack('tA', w.pin)
        self.assertEqual(got['pack'], SP.pack())
        self.assertIsNone(got['withdrawal'])

    def test_PK_20_canonical_bytes_are_stable_under_key_order_and_whitespace(self):
        """PK-20, RP-06 (property: every key permutation and any whitespace give the same canonical bytes)."""
        import json, random
        rnd = random.Random(7)
        doc = SP.pack()
        base = canon.dumps(doc)

        def shuffled(o):
            if isinstance(o, dict):
                ks = list(o)
                rnd.shuffle(ks)
                return {k: shuffled(o[k]) for k in ks}
            if isinstance(o, list):
                return [shuffled(x) for x in o]
            return o
        for i in range(20):
            text = json.dumps(shuffled(doc), indent=rnd.choice([None, 1, 4]), ensure_ascii=rnd.choice([True, False]))
            self.assertEqual(canon.dumps(canon.loads(text.encode('utf-8'))), base)
        self.assertEqual(canon.dumps({'b': 1, 'a': [3, 2], 'é': 'x'}), '{"a":[3,2],"b":1,"é":"x"}'.encode('utf-8'))
        self.assertEqual(canon.dumps({'k': 'a"b\\c\n'}), b'{"k":"a\\"b\\\\c\\u000a"}')


class TestRefusals(unittest.TestCase):
    def test_PK_02_unknown_key_is_PACK_MALFORMED(self):
        """PK-02."""
        self.assertEqual(refused(dict(SP.pack(), extra_section=[])), 'PACK_MALFORMED')
        doc = SP.pack()
        doc['vocabulary']['units'][0]['colour'] = 'blue'
        self.assertEqual(refused(doc), 'PACK_MALFORMED')

    def test_PK_03_code_like_content_is_refused(self):
        """PK-03."""
        for text in ('__import__("x")', 'lambda x: x', 'eval(1)', '<script>', '${run}'):
            with self.subTest(text=text):
                self.assertEqual(refused(dict(SP.pack(), field_label=text)), 'PACK_MALFORMED')

    def test_PK_04_a_default_freshness_limit_is_an_invariant_override(self):
        """PK-04 (SB-01)."""
        doc = SP.pack()
        doc['freshness_limits'].append({'observation_class': 'DEFAULT', 'days': 30, 'owner_ref': 'x'})
        self.assertEqual(refused(doc), 'PACK_INVARIANT_OVERRIDE')
        doc = SP.pack()
        doc['freshness_limits'][0]['default'] = 30
        self.assertEqual(refused(doc), 'PACK_INVARIANT_OVERRIDE')
        self.assertEqual(refused(dict(SP.pack(), default_freshness_limit=30)), 'PACK_INVARIANT_OVERRIDE')

    def test_PK_05_making_a_non_licensed_status_usable_is_an_invariant_override(self):
        """PK-05 (SB-03)."""
        doc = SP.pack()
        doc['licences'][2]['treat_as_licensed'] = True
        self.assertEqual(refused(doc), 'PACK_INVARIANT_OVERRIDE')
        self.assertEqual(refused(dict(SP.pack(), usable_statuses=['UNKNOWN'])), 'PACK_INVARIANT_OVERRIDE')
        doc = SP.pack()
        doc['licences'][2]['status'] = 'LICENSED_IF_UNKNOWN'
        self.assertEqual(refused(doc), 'PACK_MALFORMED')

    def test_PK_06_an_intention_other_than_BUY_or_SELL_is_refused(self):
        """PK-06."""
        self.assertEqual(refused(dict(SP.pack(), allowed_intentions=['BUY', 'HOLD'])), 'PACK_INVARIANT_OVERRIDE')
        self.assertEqual(refused(dict(SP.pack(), allowed_intentions=[])), 'PACK_MALFORMED')

    def test_PK_07_a_new_signal_type_or_a_redefined_signal_is_refused(self):
        """PK-07."""
        doc = SP.pack()
        doc['signals'].append({'signal_id': 'X', 'type': 'TREND_CONFIRMED', 'selector': {}, 'params': {'lookback_days': 1}, 'parameter_owner_ref': 'x'})
        self.assertEqual(refused(doc), 'PACK_INVARIANT_OVERRIDE')
        doc = SP.pack()
        doc['signals'][0]['meaning'] = 'rising means buy'
        self.assertEqual(refused(doc), 'PACK_INVARIANT_OVERRIDE')
        self.assertEqual(refused(dict(SP.pack(), signal_definitions={})), 'PACK_INVARIANT_OVERRIDE')
        doc = SP.pack()
        doc['signals'].append({'signal_id': 'X2', 'type': 'DATA_STALE', 'selector': {}, 'params': {'lookback_days': 1}, 'parameter_owner_ref': 'x'})
        self.assertEqual(refused(doc), 'PACK_MALFORMED')

    def test_PK_12_unsupported_schema_or_core_version(self):
        """PK-12."""
        self.assertEqual(refused(dict(SP.pack(), pack_schema='mie-pack-2')), 'PACK_SCHEMA_UNSUPPORTED')
        self.assertEqual(refused(dict(SP.pack(), core_compat=['mie-core-0.9'])), 'PACK_CORE_INCOMPATIBLE')
        self.assertEqual(refused({k: v for k, v in SP.pack().items() if k != 'pack_schema'}), 'PACK_MALFORMED')

    def test_PK_13_dangling_references_are_refused(self):
        """PK-13: source to licence, rule to parameter, hook to port; also subject to kind, alias to subject, signal to market."""
        cases = []
        d = SP.pack(); d['sources'][0]['licence_ref'] = 'NO-LIC'; cases.append(d)
        d = SP.pack(); d['decision_table'][0]['predicates'][0]['param'] = 'NO-PARAM'; cases.append(d)
        d = SP.pack(); d['hooks'][0]['port'] = 'ShellPort'; cases.append(d)
        d = SP.pack(); d['vocabulary']['subjects'][0]['kind'] = 'NO-KIND'; cases.append(d)
        d = SP.pack(); d['aliases'][0]['canonical'] = 'NO-SUBJECT'; cases.append(d)
        d = SP.pack(); d['signals'][0]['selector']['market'] = 'NO-MARKET'; cases.append(d)
        d = SP.pack(); d['vocabulary']['subjects'][0]['conversions'] = ['NO-CONV']; cases.append(d)
        for i, d in enumerate(cases):
            with self.subTest(case=i):
                self.assertEqual(refused(d), 'PACK_MALFORMED')

    def test_PK_14_duplicates_non_NFC_floats_and_duplicate_keys_are_refused(self):
        """PK-14, AD-13 (duplicate JSON keys and prototype-style keys)."""
        d = SP.pack(); d['vocabulary']['units'].append(dict(d['vocabulary']['units'][0])); self.assertEqual(refused(d), 'PACK_MALFORMED')
        d = SP.pack(); d['decision_table'].append(dict(d['decision_table'][0])); self.assertEqual(refused(d), 'PACK_MALFORMED')
        b = canon.dumps(SP.pack()).replace(b'"field_label":"TEST FIELD (SYNTHETIC)"', 'field_label":"Café"'.encode('utf-8').join([b'"', b'']))
        self.assertEqual(refused(b), 'PACK_MALFORMED')
        b = canon.dumps(SP.pack()).replace(b'"decimal_scale":2', b'"decimal_scale":2.0', 1)
        self.assertEqual(refused(b), 'PACK_INVARIANT_OVERRIDE')
        b = canon.dumps(SP.pack()).replace(b'{"aliases"', b'{"aliases":[],"aliases"', 1)
        self.assertEqual(refused(b), 'PACK_MALFORMED')
        for k in ('__proto__', 'constructor', 'prototype'):
            self.assertEqual(refused(dict(SP.pack(), **{k: {}})), 'PACK_MALFORMED')
        self.assertEqual(refused(b'{"pack_schema": NaN}'), 'PACK_MALFORMED')
        self.assertEqual(refused(b'\xff\xfe'), 'PACK_MALFORMED')
        self.assertEqual(refused(b'[1, 2]'), 'PACK_MALFORMED')

    def test_UT_21_equivalence_only_where_declared_and_ambiguous_aliases_or_cycles_are_refused(self):
        """UT-21, SB-22."""
        d = SP.pack(); d['aliases'].append({'alias': 'SYN-ITEM-A-ALT', 'canonical': 'SYN-ITEM-B'}); self.assertEqual(refused(d), 'PACK_MALFORMED')
        d = SP.pack(); d['aliases'].append({'alias': 'SYN-ITEM-B', 'canonical': 'SYN-ITEM-A'}); self.assertEqual(refused(d), 'PACK_MALFORMED')
        doc = SP.pack()
        self.assertEqual(P.canonical_subject(doc, 'SYN-ITEM-A-ALT'), 'SYN-ITEM-A')
        self.assertIsNone(P.canonical_subject(doc, 'syn-item-a'))
        self.assertIsNone(P.canonical_subject(doc, 'SYN-ITEM-A '))

    def test_PK_17_a_rule_outcome_outside_the_intention_vocabulary_is_refused(self):
        """PK-17."""
        d = SP.pack(); d['decision_table'][0]['outcome'] = 'HOLD'; self.assertEqual(refused(d), 'PACK_INVARIANT_OVERRIDE')
        d = SP.pack(); d['decision_table'][0]['outcome'] = 'BUY_NOW'; self.assertEqual(refused(d), 'PACK_INVARIANT_OVERRIDE')
        d = SP.pack(); d['decision_table'][5]['outcome'] = 'NEGOTIATE'; self.assertEqual(refused(d), 'PACK_INVARIANT_OVERRIDE')

    def test_PK_26_units_need_a_value_domain_and_conversions_are_positive(self):
        """PK-26."""
        d = SP.pack(); del d['vocabulary']['units'][0]['value_domain']; self.assertEqual(refused(d), 'PACK_MALFORMED')
        d = SP.pack(); d['vocabulary']['units'][4]['value_domain'] = 'SIGNED'; self.assertEqual(refused(d), 'PACK_MALFORMED')
        d = SP.pack(); d['vocabulary']['units'][4]['value_domain'] = 'NON_NEGATIVE'; self.assertEqual(refused(d), 'PACK_MALFORMED')

    def test_PK_27_a_threshold_must_be_an_exact_positive_ratio(self):
        """PK-27."""
        for t in ({'num': 0, 'den': 1}, {'num': -1, 'den': 20}, {'num': 1, 'den': 0}, {'num': 1}, {'num': True, 'den': 20}, '1/20', 5):
            with self.subTest(t=t):
                d = SP.pack()
                d['signals'][0]['params']['threshold'] = t
                self.assertEqual(refused(d), 'PACK_MALFORMED')
        d = SP.pack()
        d['signals'][0]['params']['threshold'] = None
        self.assertIsNone(refused(d))

    def test_freshness_entries_that_are_not_whole_days_refuse_the_pack(self):
        """UT-14 (pack side; decision A2 R1): a negative, boolean, text or null freshness entry refuses the whole pack; zero is valid."""
        for v in (-1, True, '10', None):
            with self.subTest(v=v):
                d = SP.pack()
                d['freshness_limits'][0]['days'] = v
                self.assertEqual(refused(d), 'PACK_MALFORMED')
        d = SP.pack()
        d['freshness_limits'][0]['days'] = 0
        self.assertIsNone(refused(d))

    def test_AD_04_size_and_rule_count_limits(self):
        """AD-04 (pack size and rule count), CT-12 (no limits: LIMIT_NOT_CONFIGURED)."""
        with self.assertRaises(MieError) as cm:
            P.validate(SP.pack_bytes(), dict(LIMITS, max_pack_bytes=100))
        self.assertEqual(cm.exception.code, 'LIMIT_EXCEEDED')
        with self.assertRaises(MieError) as cm:
            P.validate(SP.pack_bytes(), dict(LIMITS, max_rules=3))
        self.assertEqual(cm.exception.code, 'LIMIT_EXCEEDED')
        with self.assertRaises(MieError) as cm:
            P.validate(SP.pack_bytes(), dict(LIMITS, max_string_length=5))
        self.assertEqual(cm.exception.code, 'PACK_MALFORMED')
        w = World(pack=False, limits=None)
        self.assertEqual(code(lambda: w.e.validate_pack('tA', SP.pack_bytes())), 'LIMIT_NOT_CONFIGURED')
        self.assertEqual(code(lambda: w.e.register_pack('tA', SP.pack_bytes())), 'LIMIT_NOT_CONFIGURED')

    def test_the_order_of_checks_fixes_the_code_for_a_pack_with_several_defects(self):
        """Error precedence (decision 2.15): schema version before core version before an override before structure before the rule policy."""
        d = dict(SP.pack(), pack_schema='mie-pack-9', core_compat=['x'], extra=1)
        self.assertEqual(refused(d), 'PACK_SCHEMA_UNSUPPORTED')
        d = dict(SP.pack(), core_compat=['x'], extra=1, default=1)
        self.assertEqual(refused(d), 'PACK_CORE_INCOMPATIBLE')
        d = dict(SP.pack(), extra=1, default=1)
        self.assertEqual(refused(d), 'PACK_INVARIANT_OVERRIDE')
        d = SP.pack(); d['extra'] = 1; d['decision_table'][1]['basis_class'] = 'OBSERVED_EVIDENCE_ONLY'
        self.assertEqual(refused(d), 'PACK_MALFORMED')


class TestPublication(unittest.TestCase):
    def test_PK_08_a_changed_hash_is_refused(self):
        """PK-08 (SB-08)."""
        w = World()
        bad = dict(w.pin, pack_hash='0' * 64)
        self.assertEqual(code(lambda: w.e.get_pack('tA', bad)), 'PACK_HASH_MISMATCH')
        self.assertEqual(code(lambda: w.e.activate_pack('tA', bad, 'x')), 'PACK_HASH_MISMATCH')
        self.assertEqual(code(lambda: w.submit([ob('2026-09-01', 1)], pin=bad)), 'PACK_HASH_MISMATCH')
        self.assertEqual(code(lambda: w.e.get_signals('tA', bad, 'SYN-ITEM-A', EVAL)), 'PACK_HASH_MISMATCH')
        self.assertEqual(code(lambda: w.assess(pin=bad)), 'PACK_HASH_MISMATCH')
        self.assertEqual(code(lambda: w.e.get_pack('tA', dict(w.pin, pack_hash='XYZ'))), 'REQUEST_MALFORMED')

    def test_PK_09_and_PK_10_versions_are_immutable_and_republication_is_idempotent(self):
        """PK-09, PK-10, CT-04 (SB-21)."""
        w = World()
        self.assertEqual(w.e.register_pack('tA', SP.pack_bytes())['registered'], 'already')
        self.assertEqual(w.e.register_pack('tB', SP.pack_bytes())['registered'], 'already')
        self.assertEqual(code(lambda: w.e.register_pack('tA', canon.dumps(dict(SP.pack(), field_label='TEST FIELD (SYNTHETIC) 2')))), 'PACK_VERSION_CONFLICT')
        self.assertEqual(w.e.get_pack('tA', w.pin)['pack']['field_label'], 'TEST FIELD (SYNTHETIC)')
        with self.assertRaises(Exception):
            w.reg.put(w.pin, b'{}', 'T-A')

    def test_PK_11_a_withdrawn_pack_refuses_new_work_and_old_results_still_replay(self):
        """PK-11."""
        w = World()
        w.submit(series(UP))
        r = w.assess()
        self.assertEqual(code(lambda: w.e.withdraw_pack('tB', w.pin, 'TEST-ONLY reason')), 'NOT_FOUND')
        self.assertEqual(w.e.withdraw_pack('tA', w.pin, 'TEST-ONLY reason')['withdrawn'], 'now')
        self.assertEqual(w.e.withdraw_pack('tA', w.pin, 'TEST-ONLY reason')['withdrawn'], 'already')
        self.assertEqual(code(lambda: w.assess()), 'PACK_WITHDRAWN')
        self.assertEqual(code(lambda: w.signals()), 'PACK_WITHDRAWN')
        self.assertEqual(code(lambda: w.submit([ob('2026-09-20', 1)])), 'PACK_WITHDRAWN')
        self.assertEqual(code(lambda: w.activate('tB', w.pin)), 'PACK_WITHDRAWN')
        self.assertTrue(w.e.replay_result('tA', r['result_id'])['identical'])
        self.assertEqual(w.e.get_pack('tA', w.pin)['withdrawal']['reason_ref'], 'TEST-ONLY reason')
        self.assertEqual(w.e.get_pack('tA', w.pin)['pack'], SP.pack())

    def test_PK_15_activation_needs_a_verified_owner_approval(self):
        """PK-15, CT-11 (SB-28): missing, unknown, for another pin, for another tenant, or by the pack's own author: refused."""
        w = World(activate=False)
        self.assertEqual(code(lambda: w.e.activate_pack('tA', w.pin, None)), 'PACK_APPROVAL_MISSING')
        self.assertEqual(code(lambda: w.e.activate_pack('tA', w.pin, '  ')), 'PACK_APPROVAL_MISSING')
        self.assertEqual(code(lambda: w.e.activate_pack('tA', w.pin, 'APR-UNKNOWN')), 'PACK_APPROVAL_MISSING')
        w.appr.register('APR-B', 'TEST-ONLY approver', w.pin, 'T-B')
        self.assertEqual(code(lambda: w.e.activate_pack('tA', w.pin, 'APR-B')), 'PACK_APPROVAL_MISSING')
        w.appr.register('APR-SELF', SP.pack()['provenance']['author_ref'], w.pin, 'T-A')
        self.assertEqual(code(lambda: w.e.activate_pack('tA', w.pin, 'APR-SELF')), 'PACK_APPROVAL_MISSING')
        w.appr.register('APR-OTHERPIN', 'TEST-ONLY approver', dict(w.pin, pack_version='9'), 'T-A')
        self.assertEqual(code(lambda: w.e.activate_pack('tA', w.pin, 'APR-OTHERPIN')), 'PACK_APPROVAL_MISSING')
        self.assertEqual(code(lambda: w.assess()), 'PACK_NOT_ACTIVE')
        self.assertEqual(w.activate('tA', w.pin)['activated'], 'now')
        self.assertIsNone(code(lambda: w.assess()))

    def test_a_later_activation_never_edits_an_earlier_one(self):
        """MIE-R-33: activation records are appended; the result records the approval in force."""
        w = World()
        first = w.reg.activations('T-A', w.pin)
        w.activate('tA', w.pin, 'APR-SECOND')
        acts = w.reg.activations('T-A', w.pin)
        self.assertEqual(acts[:1], first)
        self.assertEqual(len(acts), 2)
        w.submit(series(UP))
        self.assertEqual(w.assess()['activation_approval_ref'], 'APR-SECOND')
        self.assertEqual(w.activate('tA', w.pin, 'APR-SECOND')['activated'], 'already')
        self.assertEqual(len(w.reg.activations('T-A', w.pin)), 2)

    def test_PK_25_an_owner_assumption_pack_activates_only_with_approval_and_results_record_it(self):
        """PK-25."""
        w = World(activate=False)
        self.assertEqual(code(lambda: w.e.activate_pack('tA', w.pin, 'APR-NONE')), 'PACK_APPROVAL_MISSING')
        w.activate('tA', w.pin, 'APR-OWNER-1')
        w.submit(series(UP))
        r = w.assess(need_by='2026-12-31')
        self.assertEqual(r['activation_approval_ref'], 'APR-OWNER-1')
        self.assertEqual(r['rule_fired']['basis_class'], 'OWNER_ASSUMPTION')

    def test_PK_16_an_incomplete_pack_activates_and_every_assessment_lists_the_missing_items(self):
        """PK-16: parameters, freshness limits and the decision table not yet supplied by the owner."""
        doc = SP.pack(version='0.1-incomplete')
        for s in doc['signals']:
            for k in s['params']:
                s['params'][k] = None
        doc['freshness_limits'] = []
        doc['decision_table'] = None
        doc['parameters'] = [dict(p, value=None) for p in doc['parameters']]
        w = World(pack=doc)
        w.submit(series(UP))
        r = w.assess(need_by='2026-12-01')
        self.assertEqual(r['outcome'], 'NOT_ASSESSED')
        reasons = {g['reason'] for g in r['gaps']}
        self.assertTrue({'PARAMETER_MISSING', 'NO_TABLE'} <= reasons or {'PARAMETER_MISSING', 'NO_EVIDENCE'} <= reasons, reasons)
        missing = [s for s in r['signals'] if s.get('reason') == 'PARAMETER_MISSING']
        self.assertEqual(len(missing), 5)
        level = [s for s in missing if s['type'] == 'LEVEL_MOVEMENT'][0]
        self.assertEqual(sorted(level['missing_parameters']), ['min_points', 'movement_basis', 'threshold', 'window_days'])
        self.assertIn({'kind': 'required_evidence', 'evidence_id': 'SYN-REQ-HIST', 'reason': 'FRESHNESS_LIMIT_MISSING'}, r['gaps'])

    def test_an_undeclared_subject_is_PACK_INCOMPLETE_for_an_assessment_and_NOT_FOUND_for_signals(self):
        """OP-09 PACK_INCOMPLETE and OP-08 NOT_FOUND (implementer interpretation, I-120)."""
        w = World()
        self.assertEqual(code(lambda: w.assess(subject='SYN-ITEM-Z')), 'PACK_INCOMPLETE')
        self.assertEqual(code(lambda: w.signals('SYN-ITEM-Z')), 'NOT_FOUND')


def policy_pack(table, profile='SIGNAL_RULES', version='policy'):
    return pack_with(decision_table=table, decision_profile=profile, pack_version=version)


class TestSignalInfluencePolicy(unittest.TestCase):
    """MIE-R-63 and MIE-R-69: one definition for the pack check and for the class of a result."""
    def test_PK_18_a_signal_predicate_under_CONTEXT_ONLY_is_refused(self):
        """PK-18."""
        for pred in (p_sig(), p_na('VARIANT_WITHDRAWN'), p_sig(negate=True)):
            with self.subTest(pred=pred):
                self.assertEqual(refused(policy_pack([rule('R1', 'ACT_NOW', [pred], 'OWNER_ASSUMPTION')], 'CONTEXT_ONLY')), 'PACK_RULE_POLICY_VIOLATION')
        self.assertIsNone(refused(policy_pack([rule('R1', 'ACT_NOW', [P_QUAL]), rule('R2', 'STAGE', [p_sig('DATA_STALE')])], 'CONTEXT_ONLY')))

    def test_PK_19_and_PK_21_a_market_signal_rule_without_owner_basis_is_refused_for_every_outcome(self):
        """PK-19, PK-21 (SB-39, SB-40)."""
        for intention, outs in (('BUY', ('ACT_NOW', 'WAIT', 'STAGE', 'NEGOTIATE', 'NOT_ASSESSED')), ('SELL', ('ACT_NOW', 'HOLD', 'WAIT', 'NOT_ASSESSED'))):
            for out in outs:
                with self.subTest(intention=intention, outcome=out):
                    self.assertEqual(refused(policy_pack([rule('R1', out, [p_sig()], intention=intention)])), 'PACK_RULE_POLICY_VIOLATION')

    def test_PK_22_and_PK_32_an_owner_rule_needs_both_owner_and_statement(self):
        """PK-22, PK-32 (SB-52)."""
        for owner, stmt in (('', 'x'), ('x', ''), (' ', 'x'), ('x', ' ')):
            with self.subTest(owner=owner, stmt=stmt):
                self.assertEqual(refused(policy_pack([rule('R1', 'WAIT', [p_sig()], 'OWNER_ASSUMPTION', owner=owner, assumption=stmt)])),
                                 'PACK_RULE_POLICY_VIOLATION')
                self.assertEqual(refused(policy_pack([rule('R0', 'WAIT', [p_sig()], 'OWNER_ASSUMPTION'),
                                                      rule('R1', 'STAGE', [P_QUAL], 'OWNER_ASSUMPTION', owner=owner, assumption=stmt)])), 'PACK_RULE_POLICY_VIOLATION')
        r = rule('R1', 'WAIT', [p_sig()], 'OWNER_ASSUMPTION')
        del r['assumption']
        self.assertEqual(refused(policy_pack([r])), 'PACK_RULE_POLICY_VIOLATION')

    def test_PK_23_a_downstream_rule_must_be_owner_labelled_whatever_the_earlier_outcome(self):
        """PK-23 (SB-41)."""
        for earlier in ('ACT_NOW', 'WAIT', 'STAGE', 'NEGOTIATE', 'NOT_ASSESSED'):
            with self.subTest(earlier=earlier):
                t = [rule('R1', earlier, [p_sig()], 'OWNER_ASSUMPTION'), rule('R2', 'STAGE', [P_QUAL])]
                self.assertEqual(refused(policy_pack(t)), 'PACK_RULE_POLICY_VIOLATION')

    def test_PK_24_data_quality_and_gap_predicates_are_not_signal_influenced(self):
        """PK-24."""
        t = [rule('R1', 'NEGOTIATE', [p_sig('DATA_STALE'), p_gap('NO_EVIDENCE', negate=True)]), rule('R2', 'STAGE', [p_na('DATA_MISSING'), P_ABSENT]),
             rule('R3', 'ACT_NOW', [p_sig('DATA_CONFLICT')])]
        self.assertIsNone(refused(policy_pack(t)))

    def test_PK_28_PK_29_the_exact_loophole_sequence_is_refused_for_every_later_outcome(self):
        """PK-28, PK-29, PK-31 (SB-50, SB-53): rule 1 signal-influenced and NOT_ASSESSED, rule 2 OBSERVED_EVIDENCE_ONLY."""
        for intention, outs in (('BUY', ('ACT_NOW', 'WAIT', 'STAGE', 'NEGOTIATE')), ('SELL', ('ACT_NOW', 'HOLD', 'WAIT'))):
            for out in outs:
                with self.subTest(intention=intention, outcome=out):
                    t = [rule('R1', 'NOT_ASSESSED', [p_sig(direction='UP')], 'OWNER_ASSUMPTION', intention=intention), rule('R2', out, [P_ALWAYS], intention=intention)]
                    doc = policy_pack(t, version='loop-%s-%s' % (intention, out))
                    self.assertEqual(refused(doc), 'PACK_RULE_POLICY_VIOLATION')
                    w = World(pack=False)
                    self.assertEqual(code(lambda: w.e.validate_pack('tA', canon.dumps(doc))), 'PACK_RULE_POLICY_VIOLATION')
                    self.assertEqual(code(lambda: w.e.register_pack('tA', canon.dumps(doc))), 'PACK_RULE_POLICY_VIOLATION')
                    pin = {'pack_id': doc['pack_id'], 'pack_version': doc['pack_version'], 'pack_hash': canon.digest(doc)}
                    self.assertEqual(code(lambda: w.e.get_pack('tA', pin)), 'NOT_FOUND')
                    w.appr.register('APR', 'TEST-ONLY approver', pin, 'T-A')
                    self.assertEqual(code(lambda: w.e.activate_pack('tA', pin, 'APR')), 'NOT_FOUND')
                    self.assertEqual(code(lambda: w.e.assess_timing('tA', pin, 'SYN-ITEM-A', intention, {}, [], EVAL)), 'PACK_NOT_ACTIVE')
                    self.assertEqual(code(lambda: w.e.get_signals('tA', pin, 'SYN-ITEM-A', EVAL)), 'PACK_NOT_ACTIVE')
                    self.assertEqual(code(lambda: w.e.submit_observations('tA', pin, [ob('2026-09-01', 1)])), 'PACK_NOT_ACTIVE')
                    self.assertEqual(w.reg.packs, {})

    def test_PK_30_no_NOT_ASSESSED_exemption_for_the_downstream_rule_itself(self):
        """PK-30 (SB-51)."""
        t = [rule('R1', 'WAIT', [p_sig()], 'OWNER_ASSUMPTION'), rule('R2', 'NOT_ASSESSED', [P_QUAL])]
        self.assertEqual(refused(policy_pack(t)), 'PACK_RULE_POLICY_VIOLATION')
        t = [rule('R1', 'NOT_ASSESSED', [p_sig()], 'OWNER_ASSUMPTION'), rule('R2', 'NOT_ASSESSED', [P_QUAL])]
        self.assertEqual(refused(policy_pack(t)), 'PACK_RULE_POLICY_VIOLATION')

    def test_PK_33_the_owner_labelled_sequence_is_accepted_and_unlabelled_rules_may_come_first(self):
        """PK-33 (SB-55)."""
        t = [rule('R0', 'ACT_NOW', [p_need('LE', 'SYN-P-SOON')]), rule('R1', 'NOT_ASSESSED', [p_sig(direction='UP')], 'OWNER_ASSUMPTION'),
             rule('R2', 'ACT_NOW', [P_ALWAYS], 'OWNER_ASSUMPTION')]
        doc = policy_pack(t)
        self.assertIsNone(refused(doc))
        w = World(pack=False)
        self.assertTrue(w.e.validate_pack('tA', canon.dumps(doc))['valid'])
        self.assertEqual(w.e.register_pack('tA', canon.dumps(doc))['registered'], 'now')

    def test_AD_14_evasion_attempts_after_a_signal_influenced_NOT_ASSESSED_rule(self):
        """AD-14 (SB-58): a negated SIGNAL_NOT_ASSESSED predicate, several NOT_ASSESSED rules, mixed types; each followed by an unlabelled rule."""
        heads = [[rule('R1', 'NOT_ASSESSED', [p_na('LEVEL_MOVEMENT', negate=True)], 'OWNER_ASSUMPTION')],
                 [rule('R1', 'NOT_ASSESSED', [p_sig()], 'OWNER_ASSUMPTION'), rule('R1b', 'NOT_ASSESSED', [p_sig('AVAILABILITY_CHANGE')], 'OWNER_ASSUMPTION')],
                 [rule('R1', 'NOT_ASSESSED', [p_sig('VARIANT_INTRODUCED'), p_na('CONVERSION_MOVEMENT', 'STALE_EVIDENCE')], 'OWNER_ASSUMPTION')]]
        for i, head in enumerate(heads):
            with self.subTest(case=i):
                self.assertEqual(refused(policy_pack(head + [rule('R9', 'ACT_NOW', [P_ALWAYS])])), 'PACK_RULE_POLICY_VIOLATION')
                self.assertIsNone(refused(policy_pack(head + [rule('R9', 'ACT_NOW', [P_ALWAYS], 'OWNER_ASSUMPTION')])))
        self.assertTrue(P.signal_influenced(rule('R', 'WAIT', [p_na('LEVEL_MOVEMENT', negate=True)])))
        self.assertFalse(P.signal_influenced(rule('R', 'WAIT', [p_na('DATA_STALE', negate=True)])))

    def test_AD_15_the_check_uses_the_submitted_order(self):
        """AD-15 (SB-59): moving an unlabelled rule after a signal-influenced one is refused; before it, accepted."""
        a = rule('A', 'ACT_NOW', [P_QUAL])
        b = rule('B', 'WAIT', [p_sig()], 'OWNER_ASSUMPTION')
        self.assertIsNone(refused(policy_pack([a, b])))
        self.assertEqual(refused(policy_pack([b, a])), 'PACK_RULE_POLICY_VIOLATION')
        z = rule('Z-UNLABELLED', 'ACT_NOW', [P_QUAL])
        aa = rule('AA-INFLUENCED', 'WAIT', [p_sig()], 'OWNER_ASSUMPTION')
        self.assertEqual(refused(policy_pack([aa, z])), 'PACK_RULE_POLICY_VIOLATION')
        self.assertIsNone(refused(policy_pack([z, aa])))

    def test_rules_of_another_intention_count_for_the_position(self):
        """Definition 2 reads the whole table as submitted: a BUY rule placed after a SELL signal-influenced rule is downstream."""
        t = [rule('S1', 'HOLD', [p_sig()], 'OWNER_ASSUMPTION', intention='SELL'), rule('B1', 'ACT_NOW', [P_QUAL])]
        self.assertEqual(refused(policy_pack(t)), 'PACK_RULE_POLICY_VIOLATION')


if __name__ == '__main__':
    unittest.main()
