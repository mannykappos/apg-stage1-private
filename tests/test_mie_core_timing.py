"""MIE-1 timing assessment: intentions and outcomes, the decision table, scenarios, qualification, the result record and the signal-influence class
(UT-04, UT-26..UT-41, UT-50..UT-54, AD-08, AD-09, AD-11)."""
import copy, unittest
from . import _path                                         # noqa: F401
from .helpers_mie import (EVAL, P_ABSENT, P_ALWAYS, P_QUAL, World, code, ev, ob, p_gap, p_na, p_need, p_sig, pack_with, rule, scenario, series, DOWN, FLAT, UP)
from mie.core import canon, pack as P, timing as T, vocab as Y
from mie.packs import synthetic as SP


def world_with(table, profile='SIGNAL_RULES', intentions=('BUY', 'SELL'), version=None, points=UP, **more):
    doc = pack_with(decision_table=table, decision_profile=profile, allowed_intentions=list(intentions), **more)
    doc['pack_version'] = version or 't-%s' % canon.digest([table, profile, list(intentions)])[:12]
    w = World(pack=doc)
    if points:
        w.submit(series(points))
    return w


class TestIntentions(unittest.TestCase):
    def test_UT_26_and_UT_27_a_buy_only_pack_refuses_SELL_and_can_never_produce_a_sell_outcome(self):
        """UT-26, UT-27 (SB-10): every input combination on a BUY-only pack yields only BUY outcomes."""
        table = [rule('B1', 'ACT_NOW', [p_need('LE', 'SYN-P-SOON')]), rule('B2', 'NEGOTIATE', [P_QUAL]), rule('B3', 'STAGE', [P_ALWAYS])]
        w = world_with(table, intentions=['BUY'])
        self.assertEqual(code(lambda: w.assess('SELL')), 'INTENTION_NOT_ALLOWED')
        self.assertEqual(code(lambda: w.assess('HOLD')), 'REQUEST_MALFORMED')
        seen = set()
        for need in (None, '2026-10-01', '2027-01-01'):
            for when in (EVAL, '2026-12-31', '2026-07-01'):
                for sc in ([], [scenario()]):
                    seen.add(w.assess('BUY', need, sc, when)['outcome'])
        self.assertTrue(seen <= set(Y.OUTCOMES['BUY']))
        self.assertFalse(seen & {'HOLD'})
        doc = pack_with(allowed_intentions=['BUY'], decision_table=[rule('S1', 'HOLD', [P_QUAL], intention='SELL')])
        from .test_mie_core_pack import refused
        self.assertIn(refused(doc), ('PACK_MALFORMED', 'PACK_INVARIANT_OVERRIDE'))

    def test_a_forced_outcome_outside_the_intention_fails_closed(self):
        """UT-26 (defence in depth): even a table that slipped past validation cannot emit an outcome outside the intention's vocabulary."""
        doc = SP.pack()
        doc['decision_table'] = [rule('X', 'HOLD', [P_ALWAYS], intention='BUY')]
        with self.assertRaises(T.FailClosed):
            T.evaluate(doc, 'BUY', {'signals': [], 'gaps': [], 'days_to_need_by': None, 'params': {}, 'scenarios': [], 'qualified': False})


class TestDecisionTable(unittest.TestCase):
    def test_UT_28_first_match_wins_in_the_order_given(self):
        """UT-28 (SB-19)."""
        a = rule('A', 'ACT_NOW', [P_ALWAYS])
        b = rule('B', 'STAGE', [P_ALWAYS])
        self.assertEqual(world_with([a, b]).assess()['rule_fired']['rule_id'], 'A')
        self.assertEqual(world_with([b, a]).assess()['rule_fired']['rule_id'], 'B')
        r = world_with([rule('A', 'ACT_NOW', [P_QUAL])]).assess()
        self.assertEqual((r['outcome'], r['outcome_reason'], r['rule_fired']), ('NOT_ASSESSED', 'NO_RULE_MATCHED', None))

    def test_UT_29_no_table_gives_NO_TABLE(self):
        """UT-29."""
        r = world_with(None).assess()
        self.assertEqual((r['outcome'], r['outcome_reason']), ('NOT_ASSESSED', 'NO_TABLE'))
        self.assertIn({'kind': 'assessment', 'reason': 'NO_TABLE'}, r['gaps'])

    def test_UT_35_need_by_compared_with_a_pack_parameter_and_the_missing_cases(self):
        """UT-35."""
        w = world_with([rule('A', 'ACT_NOW', [p_need('LE', 'SYN-P-SOON')]), rule('B', 'STAGE', [P_ALWAYS])])
        self.assertEqual(w.assess(need_by='2026-10-03')['rule_fired']['rule_id'], 'A')
        self.assertEqual(w.assess(need_by='2026-10-04')['rule_fired']['rule_id'], 'B')
        r = w.assess()
        self.assertEqual((r['outcome'], r['outcome_reason'], r['undecided_at_rule']), ('NOT_ASSESSED', 'CONSTRAINT_MISSING', 'A'))
        params = [dict(p, value=None) if p['param_id'] == 'SYN-P-SOON' else p for p in SP.pack()['parameters']]
        w2 = world_with([rule('A', 'ACT_NOW', [p_need('LE', 'SYN-P-SOON')])], parameters=params)
        r = w2.assess(need_by='2026-10-01')
        self.assertEqual((r['outcome'], r['outcome_reason']), ('NOT_ASSESSED', 'PARAMETER_MISSING'))
        w3 = world_with([rule('A', 'ACT_NOW', [P_ABSENT]), rule('B', 'STAGE', [P_ALWAYS])])
        self.assertEqual(w3.assess()['rule_fired']['rule_id'], 'A')
        self.assertEqual(w3.assess(need_by='2027-01-01')['rule_fired']['rule_id'], 'B')
        for cmp, days, want in (('LT', 3, False), ('LT', 2, True), ('EQ', 3, True), ('GE', 3, True), ('GE', 2, False), ('GT', 4, True)):
            with self.subTest(cmp=cmp, days=days):
                r = world_with([rule('A', 'ACT_NOW', [p_need(cmp, 'SYN-P-SOON')])], version='cmp-%s' % cmp).assess(need_by='2026-10-%02d' % days)
                self.assertEqual(r['outcome'] == 'ACT_NOW', want)

    def test_predicates_and_negation(self):
        """The closed predicate language: SIGNAL_PRESENT with class and direction, SIGNAL_NOT_ASSESSED with reason, GAP_PRESENT, SCENARIO_PRESENT, QUALIFIED; each negatable."""
        base = [rule('Z', 'NOT_ASSESSED', [P_ALWAYS], 'OWNER_ASSUMPTION')]
        cases = [([p_sig(direction='UP')], UP, True), ([p_sig(direction='DOWN')], UP, False), ([p_sig(direction='UP', negate=True)], UP, False),
                 ([p_sig(cls='CURRENT_REFERENCE')], UP, False), ([p_sig(cls='HISTORICAL_MOVEMENT')], UP, True),
                 ([p_na('AVAILABILITY_CHANGE', 'NO_EVIDENCE')], UP, True), ([p_na('LEVEL_MOVEMENT')], UP, False),
                 ([p_gap('NO_EVIDENCE')], UP, True), ([p_gap('ZERO_BASE')], UP, False)]
        for i, (preds, pts, want) in enumerate(cases):
            with self.subTest(case=i):
                w = world_with([rule('R', 'WAIT', preds, 'OWNER_ASSUMPTION')] + base, version='pred-%d' % i, points=pts)
                self.assertEqual(w.assess()['rule_fired']['rule_id'] == 'R', want)
        w = world_with([rule('R', 'WAIT', [{'p': 'SCENARIO_PRESENT', 'label': 'SYN-LABEL', 'negate': False}])] + base, version='pred-sc')
        self.assertEqual(w.assess(scenarios=[scenario()])['rule_fired']['rule_id'], 'R')
        self.assertEqual(w.assess()['rule_fired']['rule_id'], 'Z')

    def test_a_stale_signal_counts_as_NOT_ASSESSED_STALE_EVIDENCE_for_a_predicate(self):
        """MIE-R-27."""
        w = world_with([rule('R1', 'WAIT', [p_na('LEVEL_MOVEMENT', 'STALE_EVIDENCE')], 'OWNER_ASSUMPTION'),
                        rule('R2', 'ACT_NOW', [p_sig(direction='UP')], 'OWNER_ASSUMPTION')], version='stale-pred')
        w.submit([ob('2026-11-01', 100, observation_class='CURRENT_REFERENCE', value_basis='ASKING', retrieved_at='2026-11-01')])
        self.assertEqual(w.assess(when='2026-11-05')['rule_fired']['rule_id'], 'R1')
        self.assertEqual(w.assess()['rule_fired']['rule_id'], 'R2')


class TestRecord(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.w.submit(series(UP) + [ob('2026-09-28', 1500, observation_class='CURRENT_REFERENCE', value_basis='ASKING'),
                                    ob('2026-09-29', 1450, observation_class='COUNTERPARTY_OFFER', value_basis='OFFER', source_id='SYN-SRC-2')])

    def test_UT_30_every_result_discloses_its_full_content(self):
        """UT-30, UT-34 (no commit or order state; a person decides), MIE-R-23."""
        r = self.w.assess(need_by='2026-12-01', scenarios=[scenario()])
        for k in ('result_id', 'versions', 'pack', 'intention', 'constraints', 'evidence', 'signals', 'rule_fired', 'outcome', 'signal_influence', 'assumption',
                  'uncertainty', 'gaps', 'qualification', 'advisory', 'activation_approval_ref', 'evaluation_date', 'days_to_need_by'):
            self.assertIn(k, r)
        self.assertEqual(r['advisory'], Y.ADVISORY)
        self.assertEqual(r['uncertainty']['statement'], Y.MOVEMENT_STATEMENT)
        self.assertEqual(r['versions'], Y.VERSIONS)
        for item in r['evidence']['historical_movement']:
            self.assertEqual(set(item), {'observation_id', 'subject_id', 'observation_class', 'value_basis', 'as_of', 'age_days', 'freshness_limit_days', 'state', 'reason'})
        flat = canon.dumps(r).decode('utf-8')
        for word in ('"ordered"', '"committed"', '"notified"', 'order_id', 'purchase_order', '"executed"'):
            self.assertNotIn(word, flat)

    def test_UT_04_the_four_evidence_groups_stay_separate(self):
        """UT-04, SB-25, SB-31."""
        r = self.w.assess(scenarios=[scenario()])
        ev_ = r['evidence']
        self.assertEqual(set(ev_), {'historical_movement', 'current_reference', 'counterparty_offer', 'scenarios'})
        self.assertEqual({i['value_basis'] for i in ev_['historical_movement']}, {'INDEX'})
        self.assertEqual([i['value_basis'] for i in ev_['current_reference']], ['ASKING'])
        self.assertEqual([i['value_basis'] for i in ev_['counterparty_offer']], ['OFFER'])
        self.assertEqual(ev_['scenarios'][0]['label_kind'], 'ASSUMPTION')
        self.assertNotIn('assumed_level', canon.dumps(ev_['current_reference']).decode())

    def test_UT_04_different_value_bases_are_never_one_series(self):
        """UT-04 (SB-25): an index and an asking value of the same subject, market, unit and class on the same date are not a conflict, and a movement selector
        that names no basis sees two series (UNIT_MISMATCH), not one merged movement."""
        doc = SP.pack('ut04-bases')
        cfg = [s for s in doc['signals'] if s['signal_id'] == 'SYN-SIG-LEVEL'][0]
        del cfg['selector']['value_basis']
        w = World(pack=doc)
        w.submit([ob('2026-08-01', 10000), ob('2026-09-01', 11000), ob('2026-08-01', 20000, value_basis='ASKING'), ob('2026-09-01', 15000, value_basis='ASKING')])
        r = w.assess()
        self.assertFalse([g for g in r['gaps'] if g['kind'] == 'conflict'])
        level = [s for s in r['signals'] if s['signal_id'] == 'SYN-SIG-LEVEL'][0]
        self.assertEqual((level['status'], level['reason']), ('NOT_ASSESSED', 'UNIT_MISMATCH'))
        self.assertEqual(sorted(s[4] for s in level['series']), ['ASKING', 'INDEX'])

    def test_UT_32_a_scenario_is_a_labelled_assumption_and_none_is_derived_from_history(self):
        """UT-32 (SB-18)."""
        r = self.w.assess()
        self.assertEqual(r['evidence']['scenarios'], [])
        r = self.w.assess(scenarios=[scenario()])
        self.assertEqual(r['evidence']['scenarios'][0]['note'], 'a caller-supplied assumption, not a forecast and not derived from history')
        self.assertEqual(r['evidence']['scenarios'][0]['assumed_level'], {'mantissa': 12000, 'exponent': -2})

    def test_UT_33_a_forecast_shaped_scenario_is_refused(self):
        """UT-33: anything beyond the closed scenario shape (including any reference to a forecast) is SCENARIO_INVALID."""
        bad = [dict(scenario(), forecast_ref='F-1'), dict(scenario(), derived_from='history'), {k: v for k, v in scenario().items() if k != 'owner_ref'},
               dict(scenario(), assumed_level=1.5), dict(scenario(), unit='SYN-UNIT-X'), dict(scenario(), basis_statement=' '), 'scenario']
        for i, sc in enumerate(bad):
            with self.subTest(case=i):
                self.assertEqual(code(lambda: self.w.assess(scenarios=[sc])), 'SCENARIO_INVALID')
        self.assertEqual(code(lambda: self.w.e.assess_timing('tA', self.w.pin, 'SYN-ITEM-A', 'BUY', {}, {'s': 1}, EVAL)), 'SCENARIO_INVALID')

    def test_UT_36_an_owner_assumption_outcome_is_labelled_with_owner_and_statement(self):
        """UT-36."""
        w = world_with([rule('R0', 'STAGE', [P_ALWAYS], 'OWNER_ASSUMPTION', owner='TEST-ONLY owner X', assumption='TEST-ONLY statement X')])
        r = w.assess()
        self.assertEqual(r['assumption'], {'assumption_based': True, 'statement': Y.ASSUMPTION_LABEL, 'owner_ref': 'TEST-ONLY owner X',
                                           'assumption': 'TEST-ONLY statement X'})
        self.assertEqual(r['signal_influence']['class'], 'NONE')

    def test_request_shape_is_checked(self):
        """AD-08 (evaluation date missing or not ISO), REQUEST_MALFORMED for constraints."""
        w = self.w
        for bad in (None, '30/09/2026', '2026-09-31', 20260930):
            with self.subTest(date=bad):
                self.assertEqual(code(lambda: w.assess(when=bad)), 'REQUEST_MALFORMED')
                self.assertEqual(code(lambda: w.e.get_signals('tA', w.pin, 'SYN-ITEM-A', bad)), 'REQUEST_MALFORMED')
        self.assertEqual(code(lambda: w.e.assess_timing('tA', w.pin, 'SYN-ITEM-A', 'BUY', {'budget': 1}, [], EVAL)), 'REQUEST_MALFORMED')
        self.assertEqual(code(lambda: w.e.assess_timing('tA', w.pin, 'SYN-ITEM-A', 'BUY', {'need_by': 'soon'}, [], EVAL)), 'REQUEST_MALFORMED')
        self.assertEqual(code(lambda: w.e.assess_timing('tA', w.pin, 7, 'BUY', {}, [], EVAL)), 'REQUEST_MALFORMED')

    def test_AD_08_an_evaluation_date_earlier_than_all_data_assesses_nothing(self):
        """AD-08."""
        r = self.w.assess(when='2026-01-01')
        self.assertEqual((r['outcome'], r['outcome_reason']), ('NOT_ASSESSED', 'NO_EVIDENCE'))
        self.assertTrue(all(g['reason'] == 'OBSERVATION_AFTER_EVALUATION_DATE' for g in r['gaps'] if g['kind'] == 'observation'))


class TestNoOutcomeFromNothing(unittest.TestCase):
    def test_AD_09_all_stale_all_conflicting_all_unlicensed_or_empty_worlds_give_NOT_ASSESSED(self):
        """AD-09 (SB-13, SB-26)."""
        table = [rule('A', 'ACT_NOW', [P_ALWAYS]), rule('B', 'STAGE', [P_QUAL])]
        empty = world_with(table, points=None, version='ad09-empty')
        self.assertEqual(empty.assess()['outcome_reason'], 'NO_EVIDENCE')
        stale = world_with(table, version='ad09-stale')
        self.assertEqual(stale.assess(when='2026-12-31')['outcome_reason'], 'NO_EVIDENCE')
        conf = world_with(table, points=None, version='ad09-conf')
        conf.submit([ob('2026-09-20', 100, revision=1), ob('2026-09-20', 110, revision=1)])
        self.assertEqual(conf.assess()['outcome_reason'], 'NO_EVIDENCE')
        unl = world_with(table, points=None, version='ad09-unl')
        unl.submit([ob('2026-09-20', 100, source_id='SYN-SRC-W', licence_ref='SYN-LIC-4')])
        self.assertEqual(unl.assess()['outcome_reason'], 'NO_EVIDENCE')
        for w in (empty, stale, conf, unl):
            r = w.assess(when='2026-12-31' if w is stale else EVAL)
            self.assertIsNone(r['rule_fired'])
            self.assertIn({'kind': 'assessment', 'reason': 'NO_EVIDENCE'}, r['gaps'])

    def test_AD_11_a_long_one_directional_history_with_no_rule_produces_no_outcome(self):
        """AD-11 (SB-17)."""
        pts = [('2026-%02d-15' % m, 10000 + 500 * m) for m in range(1, 10)]
        doc = SP.pack('ad11')
        doc['signals'][0]['params']['window_days'] = 365
        doc['decision_table'] = [rule('A', 'STAGE', [p_gap('ZERO_BASE')])]
        w = World(pack=doc)
        w.submit(series(pts))
        r = w.assess(need_by='2027-01-01')
        self.assertEqual([s['direction'] for s in r['signals'] if s['signal_id'] == 'SYN-SIG-LEVEL'], ['UP'])
        self.assertEqual((r['outcome'], r['outcome_reason']), ('NOT_ASSESSED', 'NO_RULE_MATCHED'))


class TestInfluenceClass(unittest.TestCase):
    def test_UT_37_every_signal_driven_outcome_carries_the_label(self):
        """UT-37 (SB-39)."""
        for intention, outs in (('BUY', ('ACT_NOW', 'WAIT', 'STAGE', 'NEGOTIATE')), ('SELL', ('ACT_NOW', 'HOLD', 'WAIT'))):
            for out in outs:
                with self.subTest(intention=intention, outcome=out):
                    w = world_with([rule('R', out, [p_sig(direction='UP')], 'OWNER_ASSUMPTION', intention=intention)], version='ut37-%s-%s' % (intention, out))
                    r = w.assess(intention)
                    self.assertEqual((r['outcome'], r['signal_influence']['class']), (out, 'DIRECT'))
                    self.assertTrue(r['assumption']['assumption_based'])
                    self.assertEqual(r['assumption']['owner_ref'], 'TEST-ONLY owner')
                    self.assertEqual(r['signal_influence']['signal_influenced_rules_evaluated'], ['R'])

    def test_UT_51_the_class_matrix_on_one_pack(self):
        """UT-51, UT-38, UT-39 (SB-54)."""
        table = [rule('N', 'ACT_NOW', [p_need('LE', 'SYN-P-SOON')]),
                 rule('D', 'WAIT', [p_sig(direction='DOWN'), p_need('GT', 'SYN-P-LEAD')], 'OWNER_ASSUMPTION'),
                 rule('P', 'STAGE', [P_ABSENT], 'OWNER_ASSUMPTION'),
                 rule('DD', 'NEGOTIATE', [p_sig(direction='UP')], 'OWNER_ASSUMPTION')]
        w = world_with(table, version='ut51', points=DOWN)
        r = w.assess(need_by='2026-10-02')
        self.assertEqual((r['rule_fired']['rule_id'], r['signal_influence']['class'], r['assumption']['assumption_based']), ('N', 'NONE', False))
        r = w.assess(need_by='2026-12-31')
        self.assertEqual((r['rule_fired']['rule_id'], r['signal_influence']['class']), ('D', 'DIRECT'))
        r = w.assess()
        self.assertEqual((r['outcome'], r['outcome_reason']), ('NOT_ASSESSED', 'CONSTRAINT_MISSING'))
        w2 = world_with([rule('D', 'WAIT', [p_sig(direction='DOWN')], 'OWNER_ASSUMPTION'), table[2], table[3]], version='ut51b', points=UP)
        r = w2.assess()
        self.assertEqual((r['rule_fired']['rule_id'], r['signal_influence']['class']), ('P', 'PRECEDENCE'))
        r = w2.assess(need_by='2026-12-31')
        self.assertEqual((r['rule_fired']['rule_id'], r['signal_influence']['class']), ('DD', 'DIRECT'))

    def test_UT_50_and_UT_53_the_owner_labelled_sequence_gives_PRECEDENCE_with_the_label(self):
        """UT-50, UT-53: a firing downstream rule (actionable or NOT_ASSESSED) is PRECEDENCE and labelled."""
        t = [rule('R1', 'NOT_ASSESSED', [p_sig(direction='DOWN')], 'OWNER_ASSUMPTION'), rule('R2', 'ACT_NOW', [P_ALWAYS], 'OWNER_ASSUMPTION', owner='O2', assumption='A2')]
        r = world_with(t, version='ut50').assess()
        self.assertEqual((r['outcome'], r['signal_influence']['class'], r['assumption']['owner_ref'], r['assumption']['assumption']), ('ACT_NOW', 'PRECEDENCE', 'O2', 'A2'))
        self.assertEqual(r['signal_influence']['signal_influenced_rules_evaluated'], ['R1'])
        t = [rule('R1', 'ACT_NOW', [p_sig(direction='DOWN')], 'OWNER_ASSUMPTION'), rule('R2', 'NOT_ASSESSED', [P_ALWAYS], 'OWNER_ASSUMPTION')]
        r = world_with(t, version='ut53').assess()
        self.assertEqual((r['outcome'], r['signal_influence']['class'], r['assumption']['assumption_based']), ('NOT_ASSESSED', 'PRECEDENCE', True))

    def test_UT_52_NO_TABLE_and_NO_RULE_MATCHED_have_class_NONE_and_list_the_evaluated_rules(self):
        """UT-52 (SB-57)."""
        r = world_with(None, version='ut52a').assess()
        self.assertEqual((r['signal_influence'], r['assumption']), ({'class': 'NONE', 'signal_influenced_rules_evaluated': []}, {'assumption_based': False}))
        t = [rule('A', 'ACT_NOW', [P_QUAL]), rule('S1', 'WAIT', [p_sig(direction='DOWN')], 'OWNER_ASSUMPTION'),
             rule('S2', 'HOLD', [p_sig(direction='DOWN')], 'OWNER_ASSUMPTION', intention='SELL'), rule('S3', 'STAGE', [p_sig(direction='DOWN')], 'OWNER_ASSUMPTION')]
        r = world_with(t, version='ut52b').assess()
        self.assertEqual((r['outcome_reason'], r['signal_influence']['class']), ('NO_RULE_MATCHED', 'NONE'))
        self.assertEqual(r['signal_influence']['signal_influenced_rules_evaluated'], ['S1', 'S3'])

    def test_UT_40_under_CONTEXT_ONLY_signals_are_context_and_the_class_is_NONE(self):
        """UT-40."""
        t = [rule('A', 'NEGOTIATE', [P_QUAL], 'OWNER_ASSUMPTION'), rule('B', 'ACT_NOW', [P_ALWAYS])]
        w = world_with(t, profile='CONTEXT_ONLY', version='ut40')
        r = w.assess()
        self.assertEqual((r['signal_influence']['class'], r['decision_profile']), ('NONE', 'CONTEXT_ONLY'))
        self.assertIn('SYN-SIG-LEVEL', [s['signal_id'] for s in r['signals']])
        r = world_with(t, profile='CONTEXT_ONLY', version='ut40b', points=None)
        r.submit([ob('2026-08-01', 100), ob('2026-09-28', 100, observation_class='CURRENT_REFERENCE', value_basis='ASKING')])
        res = r.assess()
        self.assertEqual(res['qualification']['reasons'], ['STALE_EVIDENCE'])
        self.assertEqual((res['rule_fired']['rule_id'], res['signal_influence']['class'], res['assumption']['assumption_based']), ('A', 'NONE', True))

    def test_UT_41_a_signal_driven_outcome_on_qualified_evidence_is_qualified_and_never_a_forecast(self):
        """UT-41."""
        w = world_with([rule('R', 'ACT_NOW', [p_sig(direction='UP')], 'OWNER_ASSUMPTION')], version='ut41')
        w.submit([ob('2026-09-25', 100, valid_until='2026-09-26', observation_class='CURRENT_REFERENCE', value_basis='ASKING')])
        doc_req = w.doc
        r = w.assess()
        self.assertEqual(r['signal_influence']['class'], 'DIRECT')
        self.assertEqual(r['assumption']['statement'], Y.ASSUMPTION_LABEL)
        self.assertIn('not a forecast', r['assumption']['statement'])
        self.assertIn('not a tendency', r['assumption']['statement'])
        w2 = world_with([rule('R', 'ACT_NOW', [p_sig(direction='UP')], 'OWNER_ASSUMPTION')], version='ut41b',
                        required_evidence=[{'evidence_id': 'REQ-ASK', 'observation_class': 'CURRENT_REFERENCE'}] + SP.pack()['required_evidence'])
        w2.submit([ob('2026-09-01', 100, observation_class='CURRENT_REFERENCE', value_basis='ASKING')])
        r = w2.assess()
        self.assertEqual((r['outcome'], r['qualification']['status'], r['qualification']['reasons']), ('ACT_NOW', 'QUALIFIED', ['STALE_EVIDENCE']))

    def test_UT_54_an_unlabelled_signal_influenced_firing_fails_closed(self):
        """UT-54 (SB-56): a test double hands the evaluator a table whose firing rule is DIRECT or PRECEDENCE without the owner label."""
        w = World()
        w.submit(series(UP))
        bad_tables = [[rule('R', 'ACT_NOW', [p_sig(direction='UP')])],
                      [rule('R1', 'WAIT', [p_sig(direction='DOWN')], 'OWNER_ASSUMPTION'), rule('R2', 'ACT_NOW', [P_ALWAYS])],
                      [rule('R', 'ACT_NOW', [p_sig(direction='UP')], 'OWNER_ASSUMPTION', owner=' ')]]
        for i, table in enumerate(bad_tables):
            with self.subTest(case=i):
                real = copy.deepcopy(w.doc)
                tampered = copy.deepcopy(real)
                tampered['decision_table'] = table
                before_results = dict(w.res.d)
                from mie.core import canon as C
                orig = C.loads
                C.loads = lambda b, _t=tampered, _o=orig: copy.deepcopy(_t) if b == C.dumps(real) else _o(b)
                try:
                    self.assertEqual(code(lambda: w.assess()), 'INTERNAL_ERROR_FAIL_CLOSED')
                finally:
                    C.loads = orig
                self.assertEqual(w.res.d, before_results)
                last = w.events()[-1]
                self.assertEqual((last['operation'], last['outcome'], last['code']), ('assess_timing', 'FAILED', 'INTERNAL_ERROR_FAIL_CLOSED'))


if __name__ == '__main__':
    unittest.main()
