"""MIE-1 edges and boundaries of the pack checks, observations, signals, timing and the operation sequence.  Added for the mutation run: each case pins a boundary or a branch
that the operation-level tests reached only on one side.  Synthetic pack only (inside the neutrality scan)."""
import copy, unittest
from . import _path                                         # noqa: F401
from .helpers_mie import EVAL, LIMITS, World, code, ev, ob, p_need, p_na, pack_with, rule, scenario, series, signal_cfg, P_ALWAYS, UP
from mie.core import canon, reference as R, signals as S, timing as T
from mie.packs import synthetic as SP


def sig(view, sid='SYN-SIG-LEVEL'):
    return [s for s in view['signals'] if s['signal_id'] == sid][0]


def refused(doc, limits=LIMITS):
    w = World(pack=False, limits=limits)
    return code(lambda: w.e.validate_pack('tA', canon.dumps(doc)))


def world_with(table, version, **more):
    doc = pack_with(decision_table=table, **more)
    doc['pack_version'] = version
    return World(pack=doc)


class TestPackEdges(unittest.TestCase):
    def test_size_and_rule_bounds_allow_exactly_the_configured_maximum(self):
        """AD-04 at the boundary: a pack of exactly max_pack_bytes and a table of exactly max_rules are accepted; one more is refused."""
        doc = SP.pack()
        n = len(canon.dumps(doc))
        self.assertIsNone(refused(doc, dict(LIMITS, max_pack_bytes=n)))
        self.assertEqual(refused(doc, dict(LIMITS, max_pack_bytes=n - 1)), 'LIMIT_EXCEEDED')
        rules = len(doc['decision_table'])
        self.assertIsNone(refused(doc, dict(LIMITS, max_rules=rules)))
        self.assertEqual(refused(doc, dict(LIMITS, max_rules=rules - 1)), 'LIMIT_EXCEEDED')

    def test_core_compat_must_be_a_list_of_text(self):
        for cc in ('mie-core-1.0.0', 'other', ['mie-core-1.0.0', 5], None):
            with self.subTest(core_compat=cc):
                self.assertEqual(refused(pack_with(core_compat=cc)), 'PACK_MALFORMED')

    def test_a_list_field_given_as_text_or_object_is_refused(self):
        for k, v in (('hooks', ''), ('hooks', {}), ('aliases', ''), ('comparison_groups', 'x')):
            with self.subTest(field=k, value=v):
                self.assertEqual(refused(pack_with(**{k: v})), 'PACK_MALFORMED')

    def test_unit_scale_licence_dates_and_parameter_floors(self):
        """A decimal scale is a whole number of 0 or more; a licence window is two real dates in order (a one-day window is allowed); movement windows, point counts
        and lookbacks have floors."""
        doc = SP.pack()
        for scale in (-1, True, '2'):
            d = copy.deepcopy(doc)
            d['vocabulary']['units'][0]['decimal_scale'] = scale
            self.assertEqual(refused(d), 'PACK_MALFORMED', scale)
        for a, b, want in (('2026-13-01', '2030-12-31', 'PACK_MALFORMED'), ('2020-01-01', 'x', 'PACK_MALFORMED'), ('2030-01-02', '2030-01-01', 'PACK_MALFORMED'),
                           ('2030-01-01', '2030-01-01', None)):
            d = copy.deepcopy(doc)
            d['licences'][0].update(valid_from=a, valid_to=b)
            self.assertEqual(refused(d), want, (a, b))
        for key, value in (('window_days', 0), ('min_points', 1), ('window_days', 'x')):
            d = copy.deepcopy(doc)
            signal_cfg(d, 'SYN-SIG-LEVEL')['params'][key] = value
            self.assertEqual(refused(d), 'PACK_MALFORMED', (key, value))
        d = copy.deepcopy(doc)
        signal_cfg(d, 'SYN-SIG-AVAIL')['params']['lookback_days'] = -1
        self.assertEqual(refused(d), 'PACK_MALFORMED')
        d = copy.deepcopy(doc)
        signal_cfg(d, 'SYN-SIG-AVAIL')['params']['lookback_days'] = 0
        self.assertIsNone(refused(d))

    def test_each_undeclared_reference_in_a_group_or_requirement_is_refused_on_its_own(self):
        doc = SP.pack()
        for k, v in (('unit', 'SYN-UNIT-X'), ('market', 'SYN-MARKET-X'), ('subject_id', 'SYN-ITEM-X')):
            d = copy.deepcopy(doc)
            d['comparison_groups'][0][k] = v
            self.assertEqual(refused(d), 'PACK_MALFORMED', k)
        for k, v in (('unit', 'SYN-UNIT-X'), ('market', 'SYN-MARKET-X')):
            d = copy.deepcopy(doc)
            d['required_evidence'][0][k] = v
            self.assertEqual(refused(d), 'PACK_MALFORMED', k)

    def test_predicates_and_rules_of_the_wrong_shape_are_malformed_not_internal_errors(self):
        base = SP.pack()['decision_table']
        for bad in (['QUALIFIED'], [{'p': 'NO_SUCH_PREDICATE', 'negate': False}], [5]):
            t = copy.deepcopy(base)
            t[0]['predicates'] = bad
            self.assertEqual(refused(pack_with(decision_table=t)), 'PACK_MALFORMED', bad)
        t = copy.deepcopy(base)
        del t[0]['outcome']
        self.assertEqual(refused(pack_with(decision_table=t)), 'PACK_MALFORMED')
        self.assertEqual(refused(pack_with(decision_table=base + ['rule as text'])), 'PACK_MALFORMED')

    def test_a_direction_applies_only_to_the_signals_that_have_one(self):
        """A movement takes UP, DOWN or UNCHANGED; an availability change takes its availability; a variant event takes none."""
        good = rule('R', 'WAIT', [{'p': 'SIGNAL_PRESENT', 'type': 'AVAILABILITY_CHANGE', 'evidence_class': None, 'direction': 'DECREASED', 'negate': False}], 'OWNER_ASSUMPTION')
        self.assertIsNone(refused(pack_with(decision_table=[good])))
        for typ, d in (('VARIANT_INTRODUCED', 'DECREASED'), ('AVAILABILITY_CHANGE', 'UP'), ('LEVEL_MOVEMENT', 'DECREASED')):
            bad = rule('R', 'WAIT', [{'p': 'SIGNAL_PRESENT', 'type': typ, 'evidence_class': None, 'direction': d, 'negate': False}], 'OWNER_ASSUMPTION')
            self.assertEqual(refused(pack_with(decision_table=[bad])), 'PACK_MALFORMED', (typ, d))


class TestObservationEdges(unittest.TestCase):
    def test_a_negative_revision_is_rejected_and_zero_is_accepted(self):
        w = World()
        r = w.submit([ob('2026-09-01', 100, revision=-1), ob('2026-09-02', 100, revision=0)])['receipts']
        self.assertEqual((r[0]['status'], r[0]['fields']), ('REJECTED', ['revision']))
        self.assertEqual(r[1]['status'], 'ACCEPTED')

    def test_batch_and_series_bounds_allow_exactly_the_configured_maximum(self):
        w = World(limits=dict(LIMITS, max_batch_items=3, max_series_points=3))
        self.assertEqual(w.submit(series(UP))['counts']['ACCEPTED'], 3)
        self.assertEqual(code(lambda: w.submit(series(UP) + [ob('2026-09-20', 1)])), 'LIMIT_EXCEEDED')
        self.assertEqual(sig(w.signals())['status'], 'ASSESSED')
        w.submit([ob('2026-09-20', 11100)])
        self.assertEqual(code(lambda: w.signals()), 'LIMIT_EXCEEDED')


class TestSignalEdges(unittest.TestCase):
    def test_window_and_evaluation_date_are_both_inclusive(self):
        """An observation dated exactly on the evaluation date is used, and so is one exactly at the start of the window."""
        w = World()
        w.submit([ob('2026-07-02', 10000), ob(EVAL, 11000)])
        s = sig(w.signals())
        self.assertEqual((s['status'], s['start']['as_of'], s['end']['as_of'], s['direction']), ('ASSESSED', '2026-07-02', EVAL, 'UP'))

    def test_an_event_exactly_at_the_lookback_start_or_on_the_evaluation_date_is_used(self):
        for d in ('2026-08-31', EVAL):
            with self.subTest(as_of=d):
                w = World()
                w.submit([ev(d, 'SYN-AVAIL-DOWN')])
                s = sig(w.signals(), 'SYN-SIG-AVAIL')
                self.assertEqual((s['status'], s['direction']), ('ASSESSED', 'DECREASED'))

    def test_staleness_and_freshness_are_inclusive_of_the_limit(self):
        """Age equal to the limit is fresh, for a movement, an event and an evidence-group entry; one more day is stale."""
        for age, stale in ((45, False), (46, True)):
            with self.subTest(age=age):
                w = World()
                from mie.core import values as V
                last = V.shift(EVAL, -age)
                w.submit([ob(V.shift(last, -30), 10000), ob(last, 11000), ev(last, 'SYN-VARIANT-NEW')])
                v = w.signals()
                self.assertEqual(sig(v)['freshness']['stale'], stale)
                self.assertEqual(sig(v, 'SYN-SIG-NEW')['freshness']['stale'], stale)
                states = {i['as_of']: i['state'] for i in v['evidence']['historical_movement']}
                self.assertEqual(states[last], 'stale' if stale else 'current')

    def test_a_request_freshness_limit_of_zero_is_a_limit(self):
        """A class the pack does not limit takes a request limit of 0 days: same-day evidence is current and the limit is echoed in the result."""
        w = World()
        w.submit([ob(EVAL, 100, observation_class='COUNTERPARTY_OFFER', value_basis='OFFER'), ob('2026-09-29', 100, observation_class='COUNTERPARTY_OFFER',
                                                                                                 value_basis='OFFER', source_id='SYN-SRC-1')])
        r = w.assess(limits={'COUNTERPARTY_OFFER': 0})
        self.assertEqual(r['request_freshness_limits'], {'COUNTERPARTY_OFFER': 0})
        self.assertEqual(sorted(i['state'] for i in r['evidence']['counterparty_offer']), ['current', 'stale'])
        self.assertEqual(S.freshness_for(SP.pack(), {'COUNTERPARTY_OFFER': 0}, 'COUNTERPARTY_OFFER'), (0, 'request'))

    def test_crosses_zero_needs_a_strict_change_of_sign(self):
        """Moving to or from exactly zero does not cross zero."""
        from .test_mie_core_signals import move
        self.assertFalse(move(-5, 0, 'ABSOLUTE', 1, 1)['crosses_zero'])
        self.assertFalse(move(5, 0, 'ABSOLUTE', 1, 1)['crosses_zero'])
        self.assertFalse(move(0, -5, 'ABSOLUTE', 1, 1)['crosses_zero'])
        self.assertTrue(move(5, -5, 'ABSOLUTE', 1, 1)['crosses_zero'])

    def test_a_licence_window_includes_its_first_and_last_day(self):
        doc = SP.pack('lic-edges')
        doc['licences'][0].update(valid_from='2026-09-30', valid_to='2026-09-30')
        w = World(pack=doc)
        w.submit([ob('2026-08-01', 10000), ob('2026-09-01', 11000)])
        self.assertEqual(sig(w.signals())['status'], 'ASSESSED')
        for day in ('2026-09-29', '2026-10-01'):
            self.assertEqual(sig(w.signals(when=day))['reason'], 'NO_EVIDENCE', day)

    def test_evidence_valid_until_the_evaluation_date_is_still_valid(self):
        w = World()
        w.submit([ob('2026-08-01', 10000, valid_until=EVAL), ob('2026-09-01', 11000, valid_until=EVAL)])
        self.assertEqual(sig(w.signals())['status'], 'ASSESSED')
        self.assertEqual(sig(w.signals(when='2026-10-01'))['reason'], 'NO_EVIDENCE')

    def test_a_comparison_group_disagreement_needs_two_sources_two_values_and_current_evidence(self):
        """UT-12 edges: one source with two values is a series conflict but not a group disagreement; two sources with one value is neither; an expired contender
        does not count."""
        def asking(src, m, **kw):
            return ob('2026-09-29', m, observation_class='CURRENT_REFERENCE', value_basis='ASKING', source_id=src, **kw)
        cases = (([asking('SYN-SRC-1', 100), asking('SYN-SRC-1', 120)], 0, 1), ([asking('SYN-SRC-1', 100), asking('SYN-SRC-2', 100, retrieved_at='2026-09-30')], 0, 0),
                 ([asking('SYN-SRC-1', 100), asking('SYN-SRC-2', 120, valid_until='2026-09-29')], 0, 0), ([asking('SYN-SRC-1', 100), asking('SYN-SRC-2', 120)], 1, 1))
        for items, groups, series_conf in cases:
            with self.subTest(items=[(i['source_id'], i['value']['mantissa']) for i in items]):
                w = World()
                w.submit(items)
                g = w.signals()['gaps']
                self.assertEqual(len([x for x in g if x['kind'] == 'group_conflict']), groups)
                self.assertEqual(len([x for x in g if x['kind'] == 'conflict']), series_conf)

    def test_required_evidence_names_only_its_latest_observations(self):
        w = World()
        ids = [r['observation_id'] for r in w.submit(series(UP))['receipts']]
        q = w.signals()['qualification']['required_evidence'][0]
        self.assertEqual((q['status'], q['evidence_ids']), ('OK', [ids[-1]]))

    def test_stale_or_conflicting_required_evidence_is_not_reported_as_missing(self):
        w = World()
        w.submit([ob('2026-07-01', 100), ob('2026-07-15', 110)])
        v = w.signals()
        self.assertEqual(v['qualification']['reasons'], ['STALE_EVIDENCE'])
        self.assertNotIn('DATA_MISSING', [s['signal_id'] for s in v['signals']])
        self.assertIn('DATA_STALE', [s['signal_id'] for s in v['signals']])

    def test_the_uncertainty_statement_counts_only_usable_observations_and_their_sources(self):
        w = World()
        w.submit(series(UP) + [ob('2026-09-01', 100, source_id='SYN-SRC-W', licence_ref='SYN-LIC-4')])
        u = w.signals()['uncertainty']
        self.assertEqual((u['observations'], u['distinct_sources']), (3, 1))


class TestTimingEdges(unittest.TestCase):
    def test_a_fired_not_assessed_rule_gives_its_rationale_as_the_reason_and_no_assessment_gap(self):
        w = world_with([rule('R-NA', 'NOT_ASSESSED', [P_ALWAYS]), rule('R-ACT', 'ACT_NOW', [{'p': 'QUALIFIED', 'negate': False}])], 'na-reason')
        w.submit(series(UP))
        r = w.assess()
        self.assertEqual((r['outcome'], r['outcome_reason'], r['rule_fired']['rule_id']), ('NOT_ASSESSED', 'TEST-ONLY-R-NA', 'R-NA'))
        self.assertFalse([g for g in r['gaps'] if g['kind'] == 'assessment'])
        w2 = world_with([rule('R-ACT', 'ACT_NOW', [P_ALWAYS])], 'act-reason')
        w2.submit(series(UP))
        r2 = w2.assess()
        self.assertEqual((r2['outcome'], r2['outcome_reason']), ('ACT_NOW', None))

    def test_GT_is_strict_at_equality(self):
        w = world_with([rule('R-GT', 'WAIT', [p_need('GT', 'SYN-P-LEAD')]), rule('R-ELSE', 'ACT_NOW', [P_ALWAYS])], 'gt-eq')
        w.submit(series(UP))
        self.assertEqual(w.assess(need_by='2026-10-14')['rule_fired']['rule_id'], 'R-ELSE')            # 14 days, parameter 14
        self.assertEqual(w.assess(need_by='2026-10-15')['rule_fired']['rule_id'], 'R-GT')

    def test_SIGNAL_NOT_ASSESSED_with_and_without_a_reason(self):
        """No reason matches any not-assessed signal of the type; a reason matches only that reason."""
        table = [rule('R-ANY', 'WAIT', [p_na(reason=None)], 'OWNER_ASSUMPTION'), rule('R-ELSE', 'ACT_NOW', [P_ALWAYS], 'OWNER_ASSUMPTION')]
        w = world_with(table, 'na-any')
        w.submit([ob('2026-09-01', 100)])                                                              # one point: INSUFFICIENT_POINTS
        self.assertEqual(w.assess()['rule_fired']['rule_id'], 'R-ANY')
        table = [rule('R-ZB', 'WAIT', [p_na(reason='ZERO_BASE')], 'OWNER_ASSUMPTION'), rule('R-ELSE', 'ACT_NOW', [P_ALWAYS], 'OWNER_ASSUMPTION')]
        w = world_with(table, 'na-zb')
        w.submit([ob('2026-09-01', 100)])
        self.assertEqual(w.assess()['rule_fired']['rule_id'], 'R-ELSE')

    def test_a_scenario_with_a_blank_owner_or_basis_is_refused(self):
        w = World()
        w.submit(series(UP))
        for k in ('owner_ref', 'basis_statement'):
            with self.assertRaises(Exception) as cm:
                w.assess(scenarios=[scenario(**{k: '   '})])
            self.assertEqual((cm.exception.code, cm.exception.detail), ('SCENARIO_INVALID', '%s: empty' % k))

    def test_an_unknown_predicate_fails_closed_in_the_evaluator(self):
        """Pack validation never lets one through; the evaluator still refuses rather than guessing."""
        doc = pack_with(decision_table=[{'rule_id': 'R', 'intention': 'BUY', 'outcome': 'ACT_NOW', 'rationale_code': 'X', 'basis_class': 'OBSERVED_EVIDENCE_ONLY',
                                         'predicates': [{'p': 'SOMETHING_ELSE', 'negate': False}]}])
        with self.assertRaises(T.FailClosed):
            T.evaluate(doc, 'BUY', {'signals': [], 'gaps': [], 'days_to_need_by': None, 'params': {}, 'scenarios': [], 'qualified': False})


class TestOperationEdges(unittest.TestCase):
    def test_scenario_count_bound_allows_exactly_the_maximum(self):
        w = World(limits=dict(LIMITS, max_scenarios=2))
        w.submit(series(UP))
        self.assertEqual(len(w.assess(scenarios=[scenario('S1'), scenario('S2')])['evidence']['scenarios']), 2)
        self.assertEqual(code(lambda: w.assess(scenarios=[scenario('S1'), scenario('S2'), scenario('S3')])), 'LIMIT_EXCEEDED')

    def test_request_shapes_are_refused_with_the_request_codes(self):
        w = World()
        self.assertEqual(code(lambda: w.e.assess_timing('tA', w.pin, 'SYN-ITEM-A', 'BUY', {}, 5, EVAL)), 'SCENARIO_INVALID')
        self.assertEqual(code(lambda: w.e.assess_timing('tA', w.pin, 'SYN-ITEM-A\x00', 'BUY', {}, [], EVAL)), 'REQUEST_MALFORMED')
        self.assertEqual(code(lambda: w.e.get_signals('tA', w.pin, 5, EVAL)), 'REQUEST_MALFORMED')
        self.assertEqual(w.e.list_audit('tA', 1, 1)['events'][0]['seq'], 1)

    def test_a_missing_limit_is_named_in_the_refusal(self):
        lim = dict(LIMITS)
        del lim['max_batch_items']
        w = World(limits=lim)
        try:
            w.submit([ob('2026-09-01', 1)])
            self.fail('no refusal')
        except Exception as e:
            self.assertEqual(e.code, 'LIMIT_NOT_CONFIGURED')
            self.assertIn('max_batch_items', e.detail)
            self.assertNotIn('max_string_length', e.detail)

    def test_the_core_checks_the_approval_reference_before_asking_the_port(self):
        """A blank or non-text approval reference is refused even by a verifier that would accept anything."""
        w = World(activate=False)

        class Lenient(R.RefApprovals):
            def verify(self, tenant, ref, pin, doc):
                return True
        w.e.approvals = Lenient()
        for ref in ('', '   ', 5, None, 'a\x00b'):
            self.assertEqual(code(lambda: w.e.activate_pack('tA', w.pin, ref)), 'PACK_APPROVAL_MISSING', ref)
        self.assertEqual(w.reg.acts, {})

    def test_with_the_audit_sink_down_a_refusal_is_AUDIT_UNAVAILABLE(self):
        """AU-06 for refusals: the refusal cannot be recorded, so the caller is told the audit is unavailable, not the refusal code."""
        w = World()
        w.aud.down = True
        self.assertEqual(code(lambda: w.e.get_result('tA', 'bad')), 'AUDIT_UNAVAILABLE')
        self.assertEqual(code(lambda: w.e.list_audit('tA', 0, 1)), 'AUDIT_UNAVAILABLE')

    def test_a_fail_closed_evaluation_with_the_audit_sink_down_is_AUDIT_UNAVAILABLE(self):
        w = World()
        w.submit(series(UP))
        real = copy.deepcopy(w.doc)
        tampered = copy.deepcopy(real)
        tampered['decision_table'] = [rule('R', 'ACT_NOW', [{'p': 'SIGNAL_PRESENT', 'type': 'LEVEL_MOVEMENT', 'evidence_class': None, 'direction': 'UP', 'negate': False}])]
        orig = canon.loads
        canon.loads = lambda b, _t=tampered, _o=orig: copy.deepcopy(_t) if b == canon.dumps(real) else _o(b)
        try:
            self.assertEqual(code(lambda: w.assess()), 'INTERNAL_ERROR_FAIL_CLOSED')
            w.aud.down = True
            self.assertEqual(code(lambda: w.assess()), 'AUDIT_UNAVAILABLE')
        finally:
            canon.loads = orig

    def test_audit_refs_carry_the_operation_references_and_the_correlation_separately(self):
        w = World()
        w.submit(series(UP))
        r = w.assess()
        e = w.events()[-1]
        self.assertEqual(e['refs']['result_id'], r['result_id'])
        self.assertNotIn('correlation_id', e['refs'])
        self.assertRegex(e['correlation_id'], '^[0-9a-f]{32}$')

    def test_correlation_ids_distinguish_requests_and_survive_any_payload(self):
        """The correlation id is a digest of the request: different whole numbers, and values at the deepest kept level, give different ids; an unhashable or very
        deep payload still gets one."""
        w = World()

        def corr(result_id):
            code(lambda: w.e.get_result('tA', result_id))
            return w.events()[-1]['correlation_id']

        def nest(n, leaf):
            v = leaf
            for _ in range(n):
                v = [v]
            return v
        self.assertNotEqual(corr(5), corr(6))
        self.assertNotEqual(corr(nest(29, 'a')), corr(nest(29, 'b')))
        self.assertEqual(corr(nest(30, 'a')), corr(nest(30, 'b')))
        for odd in (object(), {1: 'x'}, nest(1500, 'a')):
            self.assertRegex(corr(odd), '^[0-9a-f]{32}$')


if __name__ == '__main__':
    unittest.main()
