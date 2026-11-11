"""MIE-1 signals: movement mathematics, freshness, time rules, gaps, events, conversions and data-quality signals (UT-06, UT-08, UT-13..UT-25, UT-31, UT-42..UT-49)."""
import random, unittest
from fractions import Fraction
from . import _path                                         # noqa: F401
from .helpers_mie import EVAL, World, ev, ob, pack_with, rate, series, signal_cfg, DOWN, FLAT, UP
from mie.core import canon, signals as S, values as V
from mie.packs import synthetic as SP


def sig(view, sid='SYN-SIG-LEVEL'):
    return [s for s in view['signals'] if s['signal_id'] == sid][0]


def level_world(basis='RELATIVE', num=1, den=20, unit='SYN-UNIT', window=90, min_points=2, version=None):
    doc = SP.pack(version or 'mv-%s-%d-%d-%s' % (basis, num, den, unit))
    cfg = signal_cfg(doc, 'SYN-SIG-LEVEL')
    cfg['params'].update(movement_basis=basis, threshold={'num': num, 'den': den}, window_days=window, min_points=min_points)
    cfg['selector']['unit'] = unit
    doc['required_evidence'][0]['unit'] = unit
    return World(pack=doc)


def move(s_val, e_val, basis='RELATIVE', num=1, den=20, unit='SYN-SIGNED', exp=0):
    w = level_world(basis, num, den, unit)
    w.submit([ob('2026-08-01', s_val, exp, unit=unit), ob('2026-09-01', e_val, exp, unit=unit)])
    return sig(w.signals())


class TestMovement(unittest.TestCase):
    def test_UT_18_up_down_unchanged_with_exact_ratio_endpoints_window_and_evidence(self):
        """UT-18."""
        for pts, direction, ratio in ((UP, 'UP', {'num': 1, 'den': 10}), (DOWN, 'DOWN', {'num': -1, 'den': 11}), (FLAT, 'UNCHANGED', {'num': 1, 'den': 50})):
            with self.subTest(direction=direction):
                w = World()
                ids = [r['observation_id'] for r in w.submit(series(pts))['receipts']]
                s = sig(w.signals())
                self.assertEqual((s['status'], s['direction'], s['ratio']), ('ASSESSED', direction, ratio))
                self.assertEqual(s['start']['as_of'], pts[0][0])
                self.assertEqual(s['end']['as_of'], pts[-1][0])
                self.assertEqual(s['start']['value'], {'mantissa': pts[0][1], 'exponent': -2})
                self.assertEqual(s['window'], {'from': '2026-07-02', 'to': EVAL, 'days': 90})
                self.assertEqual(sorted(s['evidence_ids']), sorted(ids))
                self.assertEqual(s['basis'], {'observations': 3, 'distinct_sources': 1, 'conflicts': 0, 'gaps': 0})
                self.assertEqual(s['vocabulary'], 'mie-signal-1')

    def test_UT_42_relative_with_a_zero_start_is_ZERO_BASE_for_every_end(self):
        """UT-42, UT-19 (SB-43)."""
        for end in (5, -5, 0):
            with self.subTest(end=end):
                s = move(0, end)
                self.assertEqual((s['status'], s['reason']), ('NOT_ASSESSED', 'ZERO_BASE'))
                self.assertNotIn('ratio', s)
        w = level_world('RELATIVE', unit='SYN-SIGNED', version='zb-gap')
        w.submit([ob('2026-08-01', 0, 0, unit='SYN-SIGNED'), ob('2026-09-01', 5, 0, unit='SYN-SIGNED')])
        self.assertIn({'kind': 'signal', 'signal_id': 'SYN-SIG-LEVEL', 'reason': 'ZERO_BASE'}, w.signals()['gaps'])

    def test_UT_43_relative_with_a_negative_start_is_direction_safe(self):
        """UT-43 (SB-42)."""
        s = move(-10, -5)
        self.assertEqual((s['direction'], s['ratio']), ('UP', {'num': 1, 'den': 2}))
        s = move(-10, -15)
        self.assertEqual((s['direction'], s['ratio']), ('DOWN', {'num': -1, 'den': 2}))

    def test_UT_44_movement_across_zero_is_flagged(self):
        """UT-44 (SB-44)."""
        s = move(-10, 10)
        self.assertEqual((s['direction'], s['ratio'], s['crosses_zero']), ('UP', {'num': 2, 'den': 1}, True))
        s = move(10, -10)
        self.assertEqual((s['direction'], s['ratio'], s['crosses_zero']), ('DOWN', {'num': -2, 'den': 1}, True))
        self.assertFalse(move(10, 20)['crosses_zero'])
        self.assertFalse(move(0, 20, 'ABSOLUTE', 5, 1)['crosses_zero'])

    def test_UT_45_absolute_is_defined_for_zero_and_negative_starts_with_the_boundary_at_T(self):
        """UT-45."""
        cases = [(0, 5, 'UP'), (-5, 0, 'UP'), (5, 0, 'DOWN'), (0, 4, 'UNCHANGED'), (0, -5, 'DOWN'), (0, -4, 'UNCHANGED')]
        for s0, e0, want in cases:
            with self.subTest(s=s0, e=e0):
                s = move(s0, e0, 'ABSOLUTE', 5, 1)
                self.assertEqual((s['status'], s['direction']), ('ASSESSED', want))
                self.assertEqual(s['difference'], {'mantissa': e0 - s0, 'exponent': 0})
        s = move(100, 150, 'ABSOLUTE', 1, 2, exp=-2)        # 1.00 to 1.50, threshold 1/2 in the unit itself
        self.assertEqual(s['direction'], 'UP')
        s = move(100, 149, 'ABSOLUTE', 1, 2, exp=-2)
        self.assertEqual(s['direction'], 'UNCHANGED')

    def test_the_relative_boundary_is_exactly_at_T(self):
        """UT-18 (the threshold is inclusive)."""
        self.assertEqual(move(100, 105, unit='SYN-UNIT')['direction'], 'UP')
        self.assertEqual(move(100, 104, unit='SYN-UNIT')['direction'], 'UNCHANGED')
        self.assertEqual(move(100, 95, unit='SYN-UNIT')['direction'], 'DOWN')
        self.assertEqual(move(100, 96, unit='SYN-UNIT')['direction'], 'UNCHANGED')

    def test_UT_46_negating_a_signed_series_negates_and_swaps_under_both_bases(self):
        """UT-46, UT-25 (SB-17): a property test over random signed pairs; mirrored histories give mirrored signals, and no direction is preferred."""
        rnd = random.Random(11)
        swap = {'UP': 'DOWN', 'DOWN': 'UP', 'UNCHANGED': 'UNCHANGED'}
        for basis in ('ABSOLUTE', 'RELATIVE'):
            for _ in range(12):
                a, b = rnd.randint(-500, 500), rnd.randint(-500, 500)
                if basis == 'RELATIVE' and a == 0:
                    a = 7
                with self.subTest(basis=basis, a=a, b=b):
                    s1, s2 = move(a, b, basis, 3, 1), move(-a, -b, basis, 3, 1)
                    self.assertEqual(s2['difference']['mantissa'], -s1['difference']['mantissa'])
                    self.assertEqual(Fraction(s2['ratio']['num'], s2['ratio']['den']), -Fraction(s1['ratio']['num'], s1['ratio']['den']))
                    self.assertEqual(s2['direction'], swap[s1['direction']])
        up = World()
        up.submit(series(UP))
        down = World()
        down.submit(series(DOWN[::-1] and [(d, 21000 - m) for d, m in UP]))
        a, b = sig(up.signals()), sig(down.signals())
        self.assertEqual((a['direction'], b['direction']), ('UP', 'DOWN'))

    def test_UT_17_and_UT_48_each_missing_parameter_gives_PARAMETER_MISSING_and_no_basis_is_assumed(self):
        """UT-17, UT-48."""
        for k in ('window_days', 'min_points', 'movement_basis', 'threshold'):
            with self.subTest(parameter=k):
                doc = SP.pack('pm-' + k)
                signal_cfg(doc, 'SYN-SIG-LEVEL')['params'][k] = None
                w = World(pack=doc)
                w.submit(series(UP))
                s = sig(w.signals())
                self.assertEqual((s['status'], s['reason'], s['missing_parameters']), ('NOT_ASSESSED', 'PARAMETER_MISSING', [k]))
                self.assertNotIn('direction', s)
        doc = SP.pack('pm-lookback')
        signal_cfg(doc, 'SYN-SIG-AVAIL')['params']['lookback_days'] = None
        w = World(pack=doc)
        self.assertEqual(sig(w.signals(), 'SYN-SIG-AVAIL')['reason'], 'PARAMETER_MISSING')

    def test_insufficient_points_and_no_evidence(self):
        """MIE-R-18: fewer distinct dates than min_points gives INSUFFICIENT_POINTS; nothing at all gives NO_EVIDENCE."""
        w = World()
        self.assertEqual(sig(w.signals())['reason'], 'NO_EVIDENCE')
        w.submit([ob('2026-09-01', 100), ob('2026-09-01', 100, source_id='SYN-SRC-1', revision=0)])
        self.assertEqual(sig(w.signals())['reason'], 'INSUFFICIENT_POINTS')

    def test_UT_20_unit_market_or_group_mismatch_gives_UNIT_MISMATCH(self):
        """UT-20: a selector that does not pin the unit meets two series."""
        doc = SP.pack('um')
        del signal_cfg(doc, 'SYN-SIG-LEVEL')['selector']['unit']
        w = World(pack=doc)
        w.submit(series(UP) + [ob('2026-09-10', 100, unit='SYN-UNIT-2'), ob('2026-09-11', 100, unit='SYN-UNIT-2')])
        s = sig(w.signals())
        self.assertEqual((s['status'], s['reason']), ('NOT_ASSESSED', 'UNIT_MISMATCH'))
        self.assertEqual(len(s['series']), 2)
        self.assertIn({'kind': 'signal', 'signal_id': 'SYN-SIG-LEVEL', 'reason': 'UNIT_MISMATCH'}, w.signals()['gaps'])

    def test_a_conflicting_endpoint_gives_CONFLICT_IN_EVIDENCE(self):
        """MIE-R-12: the core never chooses between two values."""
        w = World()
        w.submit(series(UP) + [ob('2026-09-15', 12000, source_id='SYN-SRC-1', revision=0)])
        s = sig(w.signals())
        self.assertEqual((s['status'], s['reason'], s['conflicting_dates']), ('NOT_ASSESSED', 'CONFLICT_IN_EVIDENCE', ['2026-09-15']))


class TestTimeAndFreshness(unittest.TestCase):
    def test_UT_06_observations_after_the_evaluation_date_are_excluded_and_reported(self):
        """UT-06 (SB-04)."""
        w = World()
        late = w.submit(series(UP) + [ob('2026-10-15', 50000, retrieved_at='2026-10-15')])['receipts'][-1]['observation_id']
        v = w.signals()
        self.assertEqual(sig(v)['end']['as_of'], '2026-09-15')
        self.assertIn({'kind': 'observation', 'observation_id': late, 'reason': 'OBSERVATION_AFTER_EVALUATION_DATE'}, v['gaps'])
        self.assertNotIn(late, [i['observation_id'] for g in v['evidence'].values() for i in g])

    def test_UT_08_no_interpolation_carry_forward_or_borrowing(self):
        """UT-08, FL-06: a missing day stays missing; only observed dates are points."""
        w = World()
        w.submit([ob('2026-07-15', 10000), ob('2026-09-15', 11000)])
        s = sig(w.signals())
        self.assertEqual(s['basis']['observations'], 2)
        self.assertEqual([s['start']['as_of'], s['end']['as_of']], ['2026-07-15', '2026-09-15'])
        early = w.e.get_signals('tA', w.pin, 'SYN-ITEM-A', '2026-08-30')
        self.assertEqual(sig(early)['reason'], 'INSUFFICIENT_POINTS')
        self.assertEqual(sig(early)['points'], 1)

    def test_UT_13_exactly_at_the_limit_is_fresh_and_one_day_past_is_stale(self):
        """UT-13."""
        w = World()
        w.submit(series(UP))
        at = w.e.get_signals('tA', w.pin, 'SYN-ITEM-A', V.shift('2026-09-15', 45))
        past = w.e.get_signals('tA', w.pin, 'SYN-ITEM-A', V.shift('2026-09-15', 46))
        self.assertFalse(sig(at)['freshness']['stale'])
        self.assertEqual(sig(at)['freshness'], {'limit_days': 45, 'limit_source': 'pack', 'age_days': 45, 'stale': False})
        self.assertTrue(sig(past)['freshness']['stale'])
        self.assertNotIn('DATA_STALE', [s['type'] for s in at['signals']])
        self.assertIn('DATA_STALE', [s['type'] for s in past['signals']])

    def test_UT_15_stale_evidence_qualifies_emits_DATA_STALE_and_stays_as_history(self):
        """UT-15 (SB-13)."""
        w = World()
        w.submit(series(UP))
        v = w.e.get_signals('tA', w.pin, 'SYN-ITEM-A', '2026-11-05')
        ds = [s for s in v['signals'] if s['type'] == 'DATA_STALE'][0]
        self.assertIn({'signal_id': 'SYN-SIG-LEVEL', 'age_days': 51, 'limit_days': 45}, ds['items'])
        self.assertIn({'evidence_id': 'SYN-REQ-HIST'}, ds['items'])
        self.assertEqual(v['qualification']['status'], 'QUALIFIED')
        self.assertIn('STALE_EVIDENCE', v['qualification']['reasons'])
        self.assertEqual({i['state'] for i in v['evidence']['historical_movement']}, {'stale'})
        self.assertEqual(sig(v)['status'], 'ASSESSED')

    def test_UT_16_expired_evidence_is_history_and_qualifies(self):
        """UT-16."""
        w = World()
        r = w.submit([ob('2026-09-20', 100, valid_until='2026-09-25')])['receipts'][0]['observation_id']
        v = w.signals()
        self.assertIn({'kind': 'observation', 'observation_id': r, 'reason': 'EXPIRED_EVIDENCE'}, v['gaps'])
        self.assertEqual(v['qualification']['reasons'], ['EXPIRED_EVIDENCE'])
        item = v['evidence']['historical_movement'][0]
        self.assertEqual((item['state'], item['reason']), ('history', 'EXPIRED_EVIDENCE'))

    def test_UT_14_request_side_missing_or_invalid_limits_give_FRESHNESS_LIMIT_MISSING(self):
        """UT-14 (request side; decision A2 R2, R3): a class with no pack limit is NOT_ASSESSED unless the request supplies a valid one; an invalid request value counts as
        none; a request limit for a class the pack already limits is refused (SB-01)."""
        doc = SP.pack('nofresh')
        doc['freshness_limits'] = [f for f in doc['freshness_limits'] if f['observation_class'] != 'HISTORICAL_MOVEMENT']
        w = World(pack=doc)
        w.submit(series(UP))
        r = w.assess(need_by='2026-12-01')
        self.assertEqual(sig(r)['reason'], 'FRESHNESS_LIMIT_MISSING')
        for bad in (None, True, -1, 1.5, '30'):
            with self.subTest(limit=bad):
                r = w.assess(need_by='2026-12-01', limits={'HISTORICAL_MOVEMENT': bad})
                self.assertEqual(sig(r)['reason'], 'FRESHNESS_LIMIT_MISSING')
        r = w.assess(need_by='2026-12-01', limits={'HISTORICAL_MOVEMENT': 60})
        self.assertEqual(sig(r)['freshness']['limit_source'], 'request')
        self.assertEqual(sig(r)['status'], 'ASSESSED')
        from .helpers_mie import code
        self.assertEqual(code(lambda: w.assess(limits={'CURRENT_REFERENCE': 100})), 'REQUEST_MALFORMED')
        self.assertEqual(code(lambda: w.assess(limits={'CURRENT_REFERENCE': None})), None)
        self.assertEqual(code(lambda: w.assess(limits={'SOMETHING': 1})), 'REQUEST_MALFORMED')

    def test_get_signals_takes_no_request_limit(self):
        """Decision A2 R4: the context view uses the pack's limits only."""
        import inspect
        from mie.core import engine as E
        self.assertEqual(list(inspect.signature(E.Engine.get_signals).parameters), ['self', 'ctx', 'pin', 'subject_id', 'evaluation_date'])


class TestOtherSignals(unittest.TestCase):
    def test_UT_22_conversion_movement_comes_only_from_a_declared_conversion_series(self):
        """UT-22."""
        w = World()
        w.submit([rate('2026-08-01', 6000), rate('2026-09-20', 6300)])
        s = sig(w.signals(), 'SYN-SIG-CONV')
        self.assertEqual((s['status'], s['direction'], s['subject_id'], s['unit']), ('ASSESSED', 'UP', 'SYN-RATE-1', 'SYN-RATE-UNIT'))
        self.assertNotIn('SYN-SIG-CONV', [x['signal_id'] for x in w.signals('SYN-ITEM-B')['signals']])
        w.submit([ob('2026-08-01', 6000, -4, unit='SYN-RATE-UNIT', observation_class='CURRENT_REFERENCE'),
                  ob('2026-09-20', 9000, -4, unit='SYN-RATE-UNIT', observation_class='CURRENT_REFERENCE')])
        self.assertEqual(sig(w.signals(), 'SYN-SIG-CONV')['ratio'], {'num': 1, 'den': 20})

    def test_UT_23_event_signals_come_only_from_mapped_event_observations(self):
        """UT-23."""
        w = World()
        w.submit([ev('2026-09-10', 'SYN-AVAIL-DOWN'), ev('2026-09-20', 'SYN-VARIANT-END'), ev('2026-05-01', 'SYN-VARIANT-NEW')])
        v = w.signals()
        a = sig(v, 'SYN-SIG-AVAIL')
        self.assertEqual((a['status'], a['direction'], a['events'][0]['event_class']), ('ASSESSED', 'DECREASED', 'AVAILABILITY_CHANGED'))
        self.assertEqual(sig(v, 'SYN-SIG-END')['status'], 'ASSESSED')
        self.assertEqual(sig(v, 'SYN-SIG-NEW')['reason'], 'NO_EVIDENCE')
        w.submit([ev('2026-09-25', 'SYN-AVAIL-UP')])
        self.assertEqual(sig(w.signals(), 'SYN-SIG-AVAIL')['direction'], 'INCREASED')

    def test_UT_24_the_basis_statement_holds_counts_only(self):
        """UT-24: no probability or confidence number exists anywhere in a view."""
        w = World()
        w.submit(series(UP))
        v = w.signals()
        self.assertEqual(set(sig(v)['basis']), {'observations', 'distinct_sources', 'conflicts', 'gaps'})
        flat = canon.dumps(v).decode('utf-8').lower()
        for word in ('probability', 'confidence', 'likely', 'chance'):
            self.assertNotIn(word, flat)
        self.assertEqual(set(v['uncertainty']), {'observations', 'distinct_sources', 'conflicts', 'gaps', 'statement'})

    def test_DATA_MISSING_lists_each_required_gap_and_DATA_CONFLICT_covers_comparison_groups(self):
        """UT-31 (every gap listed with its reason), SIG-07, SIG-08."""
        w = World()
        v = w.signals()
        dm = [s for s in v['signals'] if s['type'] == 'DATA_MISSING'][0]
        self.assertEqual(dm['items'], [{'evidence_id': 'SYN-REQ-HIST', 'reason': 'NO_EVIDENCE'}])
        w.submit([ob('2026-09-28', 1500, observation_class='CURRENT_REFERENCE', value_basis='ASKING'),
                  ob('2026-09-28', 1600, observation_class='CURRENT_REFERENCE', value_basis='ASKING', source_id='SYN-SRC-2')])
        dc = [s for s in w.signals()['signals'] if s['type'] == 'DATA_CONFLICT'][0]
        grp = [i for i in dc['items'] if 'group_id' in i]
        self.assertEqual([g['group_id'] for g in grp], ['SYN-GROUP-ASK'])
        self.assertEqual(len(grp[0]['evidence_ids']), 2)

    def test_UT_31_a_missing_input_is_a_listed_gap_and_never_a_zero(self):
        """UT-31 (SB-06): with no evidence nothing is computed from zero; every gap has a reason."""
        w = World()
        v = w.signals()
        self.assertTrue(all('reason' in g and g['reason'] for g in v['gaps']))
        self.assertTrue(all('difference' not in s and 'ratio' not in s for s in v['signals']))
        flat = canon.dumps(v['signals'])
        self.assertNotIn(b'"mantissa":0', flat)


if __name__ == '__main__':
    unittest.main()
