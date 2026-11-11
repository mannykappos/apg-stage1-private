import datetime
import unittest
from . import _path                                         # noqa: F401
from .helpers_det import DetMini, bud, defect, delay, det_world, hire


def bare():
    m = DetMini()
    m.projects(['PRJ-001', 'P1', '10000000', '2026-01-01', '2027-01-01'])
    m.contracts(['PRJ-001', '10000000', '0'])
    m.budgets(bud(cc='CC-01', cents='5000000'))
    return m


class TestR08Hire(unittest.TestCase):
    def world(self, *rows):
        m = det_world()
        m.hires(*rows)
        m.reconcile()
        return m

    def test_still_on_hire_long_after_the_need_date_is_flagged_with_days_times_rate(self):
        m = self.world(hire('H-1', need='2026-03-31', rate='100000'))
        (s,) = m.sigs(m.res(), 'R08')
        self.assertEqual((s['subject'], s['extra']['days_beyond_need'], s['quantification']['gross_cents'], s['quantification']['label']), ('H-1', 183, 18300000, 'estimate'))
        self.assertEqual((s['extra']['off_hire_recorded'], s['interpretation']), (False, 'forecast_exposure'))
        self.assertIn('unknown, not proof', ' '.join(s['quantification']['assumptions']))
        self.assertTrue(s['priority']['urgency']['time_sensitive'])
        self.assertEqual(s['priority']['severity'], 'medium')

    def test_seven_days_beyond_need_is_silent_and_eight_is_flagged(self):
        m = self.world(hire('H-1', need='2026-09-23'))
        self.assertEqual(m.sigs(m.res(), 'R08'), [])
        m = self.world(hire('H-1', need='2026-09-22'))
        self.assertEqual(len(m.sigs(m.res(), 'R08')), 1)

    def test_an_off_hire_date_stops_the_count(self):
        m = self.world(hire('H-1', need='2026-03-31', off='2026-04-10', rate='100000'))
        (s,) = m.sigs(m.res(), 'R08')
        self.assertEqual((s['extra']['days_beyond_need'], s['quantification']['gross_cents'], s['extra']['off_hire_recorded']), (10, 1000000, True))
        self.assertFalse(s['priority']['urgency']['time_sensitive'])

    def test_off_hire_before_the_need_date_is_silent(self):
        m = self.world(hire('H-1', need='2026-03-31', off='2026-03-20'))
        self.assertEqual(m.sigs(m.res(), 'R08'), [])

    def test_no_need_date_means_not_assessed_not_in_excess(self):
        m = self.world(hire('H-1', need=''))
        r = m.res()
        self.assertEqual(m.sigs(r, 'R08'), [])
        self.assertEqual(len(m.run(r, 'R08')['not_assessed']), 1)

    def test_hire_starting_after_the_as_of_date_is_silent(self):
        m = self.world(hire('H-1', on='2026-11-01', need='2026-11-15'))
        self.assertEqual(m.sigs(m.res(), 'R08'), [])

    def test_the_excess_threshold_comes_from_the_policy(self):
        m = self.world(hire('H-1', need='2026-09-22'))
        m.rules(R08={'min_excess_days': 8})
        self.assertEqual(m.sigs(m.res(), 'R08'), [])

    def test_the_signal_says_plant_cost_is_not_in_the_core_and_hire_invoices_are_not_checked(self):
        m = self.world(hire('H-1', need='2026-03-31'))
        (s,) = m.sigs(m.res(), 'R08')
        self.assertIn('F-17', ' '.join(s['confidence']['missing_information']))
        self.assertIn('not checked against hire invoices', ' '.join(s['data_limits']))


class TestDelayOverlap(unittest.TestCase):
    def world(self, *rows):
        m = det_world()
        m.delays(*rows)
        m.reconcile()
        return m

    def test_two_overlapping_delays_are_reported_once_never_added_and_never_priced(self):
        m = self.world(delay('D-1', start='2026-07-06', end='2026-07-21'), delay('D-2', act='A-2', start='2026-07-15', end='2026-07-30', rate='500000'))
        (s,) = m.sigs(m.res(), 'DLY')
        self.assertEqual(s['subject'], 'D-1|D-2')
        self.assertEqual((s['extra']['overlap_days'], s['extra']['union_days'], s['extra']['sum_of_durations_days']), (7, 25, 32))
        self.assertEqual(s['quantification']['status'], 'unquantified')
        self.assertIn('counterfactual', s['quantification']['reason'])
        self.assertTrue(s['hypotheses'])
        self.assertEqual(s['extra']['holding_rates_cents_per_day'], [500000, 1000000])
        self.assertIsNone(s['overlap_group'])                                        # different activities: no declared shared overlap group

    def test_the_same_activity_gives_a_shared_overlap_group(self):
        m = self.world(delay('D-1', act='A-1', start='2026-07-06', end='2026-07-21'), delay('D-2', act='A-1', start='2026-07-15', end='2026-07-30'))
        (s,) = m.sigs(m.res(), 'DLY')
        self.assertEqual(s['overlap_group'], 'schedule:PRJ-001:A-1')

    def test_one_shared_day_is_an_overlap_and_none_is_not(self):
        m = self.world(delay('D-1', start='2026-07-06', end='2026-07-21'), delay('D-2', start='2026-07-21', end='2026-07-30'))
        self.assertEqual(m.sigs(m.res(), 'DLY')[0]['extra']['overlap_days'], 1)
        m = self.world(delay('D-1', start='2026-07-06', end='2026-07-21'), delay('D-2', start='2026-07-22', end='2026-07-30'))
        self.assertEqual(m.sigs(m.res(), 'DLY'), [])

    def test_a_delay_with_no_end_date_is_listed_not_compared(self):
        m = self.world(delay('D-1', start='2026-07-06', end='2026-07-21'), delay('D-2', start='2026-07-15', end=''))
        r = m.res()
        self.assertEqual(m.sigs(r, 'DLY'), [])
        self.assertTrue(any(n['subject'] == 'delay_event/D-2' for n in m.run(r, 'DLY')['not_assessed']))

    def test_three_delays_give_a_signal_per_overlapping_pair_and_none_for_the_separate_one(self):
        m = self.world(delay('D-1', start='2026-07-06', end='2026-07-21'), delay('D-2', start='2026-07-15', end='2026-07-30'), delay('D-3', start='2026-09-01', end='2026-09-05'))
        subs = sorted(s['subject'] for s in m.sigs(m.res(), 'DLY'))
        self.assertEqual(subs, ['D-1|D-2'])
        self.assertEqual(m.run(m.res(), 'DLY')['evaluated'], 3)

    def test_the_minimum_overlap_is_configured(self):
        m = self.world(delay('D-1', start='2026-07-06', end='2026-07-21'), delay('D-2', start='2026-07-21', end='2026-07-30'))
        m.rules(DLY={'min_overlap_days': 2})
        self.assertEqual(m.sigs(m.res(), 'DLY'), [])

    def test_the_signal_says_it_does_not_know_the_critical_path(self):
        m = self.world(delay('D-1', start='2026-07-06', end='2026-07-21'), delay('D-2', start='2026-07-15', end='2026-07-30'))
        (s,) = m.sigs(m.res(), 'DLY')
        self.assertIn('critical path', ' '.join(s['confidence']['missing_information']))
        self.assertIn('not decided here', ' '.join(s['hypotheses']))


def monday_weeks(first, n):
    d = datetime.date.fromisoformat(first)
    return [(d + datetime.timedelta(days=7 * i)).isoformat() for i in range(n)]


class TestLabour(unittest.TestCase):
    WEEKS = monday_weeks('2026-07-06', 12)                                  # the last week ends 2026-09-27

    def world(self, recent_out=90, recent_hours=100, wp='WP-1', weeks=None, extra_ts=(), rate='5000'):
        m = bare()
        weeks = weeks or self.WEEKS
        ts, wo = [], []
        for i, w in enumerate(weeks):
            late = i >= len(weeks) - 4
            ts.append(['T-%02d' % i, 'W-A', 'PRJ-001', wp, w, str(recent_hours if late else 100), '0', rate])
            wo.append(['PRJ-001', wp, w, str(recent_out if late else 100), 'm2'])
        m.timesheets(*ts, *extra_ts)
        m.outputs(*wo)
        m.reconcile()
        return m

    def test_output_per_hour_falling_by_the_threshold_is_flagged_at_package_level(self):
        m = self.world(recent_out=80)
        (s,) = m.sigs(m.res(), 'LAB')
        self.assertEqual((s['subject'], s['interpretation'], s['extra']['decline_bps']), ('WP-1', 'forecast_exposure', 2000))
        self.assertEqual((s['extra']['baseline_weeks'][0], s['extra']['recent_weeks'][0]), (self.WEEKS[0], self.WEEKS[8]))
        self.assertEqual(s['quantification']['label'], 'estimate')
        self.assertIn('no worker is compared', ' '.join(s['data_limits']))
        self.assertTrue(s['hypotheses'])
        self.assertTrue(all('W-A' not in e['ref'] for e in s['evidence']))               # evidence names entries, not people

    def test_cost_estimate_is_the_excess_hours_times_the_recent_rate(self):
        m = self.world(recent_out=80)                                                      # 4 weeks x 100h at 5000: needed 4 x 80h/100 x 100 = 320h; excess 80h
        (s,) = m.sigs(m.res(), 'LAB')
        self.assertEqual(s['quantification']['gross_cents'], 80 * 5000)

    def test_a_fall_of_exactly_the_threshold_is_flagged_and_just_under_is_not(self):
        m = self.world(recent_out=90)
        self.assertEqual(len(m.sigs(m.res(), 'LAB')), 1)                                    # exactly 10.00%: "at least" the fall
        m = self.world(recent_out=91)
        self.assertEqual(m.sigs(m.res(), 'LAB'), [])

    def test_steady_output_per_hour_is_silent(self):
        m = self.world(recent_out=100)
        r = m.res()
        self.assertEqual(m.sigs(r, 'LAB'), [])
        self.assertEqual(m.run(r, 'LAB')['silent'], 1)

    def test_improving_output_is_silent(self):
        m = self.world(recent_out=130)
        self.assertEqual(m.sigs(m.res(), 'LAB'), [])

    def test_an_earlier_as_of_date_without_enough_complete_weeks_is_not_assessed(self):
        m = self.world(recent_out=80)
        r = m.res(as_of='2026-08-14')
        self.assertEqual(m.sigs(r, 'LAB'), [])
        self.assertIn('complete weeks', m.run(r, 'LAB')['not_assessed'][0]['why'])

    def test_a_week_that_has_not_ended_is_left_out(self):
        m = self.world(recent_out=80)
        r = m.res(as_of='2026-09-26')                                                       # the last week ends on the 27th
        self.assertEqual(m.sigs(r, 'LAB'), [])
        self.assertEqual(len(m.sigs(m.res(as_of='2026-09-27'), 'LAB')), 1)

    def test_a_missing_week_in_the_windows_stops_the_comparison(self):
        weeks = self.WEEKS[:5] + self.WEEKS[6:] + ['2026-09-28']
        m = self.world(recent_out=80, weeks=weeks)
        r = m.res(as_of='2026-10-04')
        self.assertEqual(m.sigs(r, 'LAB'), [])
        self.assertTrue(m.run(r, 'LAB')['not_assessed'])

    def test_a_held_timesheet_entry_in_a_week_removes_that_week(self):
        m = self.world(recent_out=80, extra_ts=[['T-BAD', 'W-B', 'PRJ-001', 'WP-1', self.WEEKS[11], '8', 'abc', '5000']])
        r = m.res()
        self.assertEqual(m.sigs(r, 'LAB'), [])
        self.assertTrue(any(n['subject'] == 'timesheet/T-BAD' for n in m.run(r, 'LAB')['not_assessed']))

    def test_no_hourly_rate_gives_an_unquantified_signal(self):
        m = self.world(recent_out=80, rate='')
        (s,) = m.sigs(m.res(), 'LAB')
        self.assertEqual(s['quantification']['status'], 'unquantified')

    def test_the_threshold_and_the_windows_come_from_the_policy(self):
        m = self.world(recent_out=80)
        m.rules(LAB={'baseline_weeks': 8, 'recent_weeks': 4, 'decline_bps': 2001})
        self.assertEqual(m.sigs(m.res(), 'LAB'), [])
        m.rules(LAB={'baseline_weeks': 9, 'recent_weeks': 4, 'decline_bps': 1000})
        r = m.res()
        self.assertEqual(m.sigs(r, 'LAB'), [])
        self.assertIn('13 complete weeks', m.run(r, 'LAB')['not_assessed'][0]['why'])

    def test_each_package_is_judged_on_its_own(self):
        m = bare()
        ts, wo = [], []
        for wp, out in (('WP-1', 80), ('WP-2', 100)):
            for i, w in enumerate(self.WEEKS):
                late = i >= 8
                ts.append(['%s-%02d' % (wp, i), 'W-A', 'PRJ-001', wp, w, '100', '0', '5000'])
                wo.append(['PRJ-001', wp, w, str(out if late else 100), 'm2'])
        m.timesheets(*ts)
        m.outputs(*wo)
        m.reconcile()
        r = m.res()
        self.assertEqual([s['subject'] for s in m.sigs(r, 'LAB')], ['WP-1'])
        self.assertEqual(m.run(r, 'LAB')['silent'], 1)


class TestDefects(unittest.TestCase):
    def world(self, *rows):
        m = det_world()
        m.defects(*rows)
        m.reconcile()
        return m

    def three(self, costs=('1000000', '1500000', '2500000'), trade='waterproofing'):
        return [defect('DEF-%d' % i, trade=trade, raised='2026-0%d-01' % (5 + i), cost=c) for i, c in enumerate(costs)]

    def test_three_defects_of_one_subcontractor_and_trade_with_growing_cost_are_flagged(self):
        m = self.world(*self.three())
        (s,) = m.sigs(m.res(), 'DEF')
        self.assertEqual((s['subject'], s['taxonomy']['subtype'], s['extra']['events'], s['extra']['growing']), ('SUB-1|waterproofing', 'repeat_defect_growing_rework', 3, True))
        self.assertEqual((s['quantification']['gross_cents'], s['quantification']['label']), (5000000, 'record'))
        self.assertTrue(s['hypotheses'])
        self.assertIn('recurrence is not causation', ' '.join(s['hypotheses']))
        self.assertIn('Section 13', ' '.join(s['data_limits']))

    def test_two_defects_are_below_the_configured_count(self):
        m = self.world(*self.three()[:2])
        r = m.res()
        self.assertEqual(m.sigs(r, 'DEF'), [])
        self.assertEqual(m.run(r, 'DEF')['silent'], 1)

    def test_costs_that_do_not_grow_each_time_are_a_plain_repeat_not_a_growing_one(self):
        m = self.world(*self.three(('1000000', '900000', '2500000')))
        (s,) = m.sigs(m.res(), 'DEF')
        self.assertEqual((s['taxonomy']['subtype'], s['extra']['growing']), ('repeat_defect', False))

    def test_defects_spread_over_different_trades_do_not_group(self):
        rows = self.three()
        rows[2][3] = 'roofing'
        m = self.world(*rows)
        self.assertEqual(m.sigs(m.res(), 'DEF'), [])

    def test_different_subcontractors_do_not_group(self):
        rows = self.three()
        rows[2][2] = 'SUB-2'
        m = self.world(*rows)
        self.assertEqual(m.sigs(m.res(), 'DEF'), [])

    def test_a_defect_dated_after_the_as_of_date_is_not_counted(self):
        rows = self.three()
        rows[2][4] = '2026-11-01'
        m = self.world(*rows)
        self.assertEqual(m.sigs(m.res(), 'DEF'), [])

    def test_a_defect_without_a_cost_makes_growth_unknown_and_is_said_so(self):
        m = self.world(*self.three(('1000000', '', '2500000')))
        (s,) = m.sigs(m.res(), 'DEF')
        self.assertFalse(s['extra']['growing'])
        self.assertIn('not known for every defect', s['explanation']['observed'])

    def test_the_count_comes_from_the_policy(self):
        m = self.world(*self.three()[:2])
        m.rules(DEF={'min_events': 2})
        self.assertEqual(len(m.sigs(m.res(), 'DEF')), 1)


class TestD02(unittest.TestCase):
    def test_a_held_record_of_a_new_kind_gives_one_integrity_signal_per_kind(self):
        m = det_world()
        m.defects(defect('DEF-1'), defect('DEF-2', cost='abc'))
        m.reconcile()
        r = m.res()
        ss = m.sigs(r, 'D02')
        self.assertEqual([s['subject'] for s in ss], ['defect|held_records'])
        self.assertEqual((ss[0]['quantification']['status'], ss[0]['extra']['count'], ss[0]['interpretation']), ('unquantified', 1, 'data_quality_risk'))
        self.assertEqual([e['ref'] for e in ss[0]['evidence']], ['defect/DEF-2'])

    def test_clean_records_give_no_signal(self):
        m = det_world()
        m.defects(defect('DEF-1'))
        m.reconcile()
        self.assertEqual(m.sigs(m.res(), 'D02'), [])

    def test_a_future_dated_record_is_outside_the_period_not_a_defect_of_the_data(self):
        m = det_world()
        m.defects(defect('DEF-1', raised='2026-12-01'))
        m.reconcile()
        r = m.res()
        self.assertEqual(m.sigs(r, 'D02'), [])
        self.assertIn('OUTSIDE_PERIOD:defect/DEF-1', m.run(r, 'D02')['notes'])

    def test_a_held_record_is_never_used_by_the_rule_that_reads_that_kind(self):
        m = det_world()
        m.defects(*[defect('DEF-%d' % i, raised='2026-0%d-01' % (5 + i), cost=('abc' if i == 2 else '100000')) for i in range(3)])
        m.reconcile()
        self.assertEqual(m.sigs(m.res(), 'DEF'), [])
