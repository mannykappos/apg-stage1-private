"""Edge cases of the site and schedule rules found by the mutation pass: the as-of day itself, single-day and reversed events, zero values in a comparison, held records that are not in
conflict, which evidence belongs to which window, and the exact words of an observation.  Every value is synthetic."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_det import defect, delay, det_world, hire
from .test_det_rules_ops import bare, monday_weeks

WEEKS = monday_weeks('2026-07-06', 12)                                  # the last week ends on Sunday 2026-09-27


def lab_world(base_out=100, base_hours=100, recent_out=80, recent_hours=100, extra_ts=(), extra_wo=(), rate='5000', wp='WP-1'):
    m = bare()
    ts, wo = [], []
    for i, w in enumerate(WEEKS):
        late = i >= 8
        ts.append(['%s-T-%02d' % (wp, i), 'W-A', 'PRJ-001', wp, w, str(recent_hours if late else base_hours), '0', rate])
        wo.append(['PRJ-001', wp, w, str(recent_out if late else base_out), 'm2'])
    m.timesheets(*ts, *extra_ts)
    m.outputs(*wo, *extra_wo)
    m.reconcile()
    return m


class TestHireEdges(unittest.TestCase):
    def test_hire_that_starts_on_the_as_of_day_is_tested(self):
        m = det_world()
        m.hires(hire('H-1', on='2026-09-30', need='2026-08-01'))
        m.reconcile()
        (s,) = m.sigs(m.res(), 'R08')
        self.assertEqual(s['extra']['days_beyond_need'], 60)

    def test_the_observation_names_the_equipment_on_the_hire_record(self):
        m = det_world()
        m.hires(hire('H-1', equip='excavator', need='2026-06-01'))
        m.reconcile()
        (s,) = m.sigs(m.res(), 'R08')
        self.assertTrue(s['explanation']['observed'].startswith('excavator (H-1) is needed until 2026-06-01; '), s['explanation']['observed'])


class TestDelayEdges(unittest.TestCase):
    def world(self, *rows):
        m = det_world()
        m.delays(*rows)
        m.reconcile()
        return m

    def test_a_delay_of_a_single_day_is_compared(self):
        m = self.world(delay('D-1', start='2026-07-06', end='2026-07-06'), delay('D-2', start='2026-07-01', end='2026-07-10'))
        (s,) = m.sigs(m.res(), 'DLY')
        self.assertEqual((s['subject'], s['extra']['overlap_days']), ('D-1|D-2', 1))

    def test_a_delay_that_starts_on_the_as_of_day_is_compared_and_one_that_starts_after_it_is_not(self):
        m = self.world(delay('D-5', start='2026-09-30', end='2026-10-05'), delay('D-6', start='2026-09-01', end='2026-10-05', act='A-9'), delay('D-4', start='2026-10-01', end='2026-10-10'))
        r = m.res()
        self.assertEqual([s['subject'] for s in m.sigs(r, 'DLY')], ['D-5|D-6'])
        self.assertEqual(m.run(r, 'DLY')['not_assessed'], [{'subject': 'delay_event/D-4', 'why': 'starts after the as-of date or ends before it starts'}])

    def test_a_delay_that_ends_before_it_starts_is_not_compared(self):
        m = self.world(delay('D-3', start='2026-08-10', end='2026-08-01'), delay('D-2', start='2026-07-01', end='2026-08-30'))
        r = m.res()
        self.assertEqual(m.sigs(r, 'DLY'), [])
        self.assertEqual(m.run(r, 'DLY')['not_assessed'], [{'subject': 'delay_event/D-3', 'why': 'starts after the as-of date or ends before it starts'}])

    def test_a_future_dated_delay_that_is_not_in_conflict_is_listed_with_its_reason(self):
        m = self.world(delay('D-1', start='2099-01-01', end='2099-01-05'))
        self.assertEqual(m.run(m.res(), 'DLY')['not_assessed'], [{'subject': 'delay_event/D-1', 'why': 'FUTURE_DATED:start_date'}])

    def test_the_observation_gives_each_recorded_cause_or_none(self):
        m = self.world(delay('D-1', start='2026-07-01', end='2026-07-10', cause='crane'), delay('D-2', start='2026-07-05', end='2026-07-12', cause=''))
        (s,) = m.sigs(m.res(), 'DLY')
        self.assertIn('D-1 (2026-07-01 to 2026-07-10, recorded cause: crane)', s['explanation']['observed'])
        self.assertIn('D-2 (2026-07-05 to 2026-07-12, recorded cause: none)', s['explanation']['observed'])
        m = self.world(delay('D-1', start='2026-07-01', end='2026-07-10', cause=''), delay('D-2', start='2026-07-05', end='2026-07-12', cause='rain'))
        (s,) = m.sigs(m.res(), 'DLY')
        self.assertIn('D-1 (2026-07-01 to 2026-07-10, recorded cause: none)', s['explanation']['observed'])
        self.assertIn('D-2 (2026-07-05 to 2026-07-12, recorded cause: rain)', s['explanation']['observed'])


class TestLabourEdges(unittest.TestCase):
    def test_an_entry_on_the_last_day_of_the_last_complete_week_counts_when_that_day_is_the_as_of_day(self):
        m = lab_world(extra_ts=[['T-SUN', 'W-B', 'PRJ-001', 'WP-1', '2026-09-27', '10', '0', '5000']])
        r = m.res(as_of='2026-09-27')
        (s,) = m.sigs(r, 'LAB')
        self.assertEqual(s['extra']['recent_hours_micro'], 410 * 1_000_000)
        self.assertEqual(s['quantification']['gross_cents'], 90 * 5000)                  # 410 h worked, 320 h needed at the baseline rate: 90 h at 5,000 a hour
        self.assertIn('timesheet/T-SUN', [e['ref'] for e in s['evidence']])

    def test_overtime_is_added_to_ordinary_hours_and_a_blank_overtime_is_zero(self):
        m = lab_world(extra_ts=[['T-OT', 'W-B', 'PRJ-001', 'WP-1', '2026-09-21', '0', '10', '5000'], ['T-NO', 'W-B', 'PRJ-001', 'WP-1', '2026-09-22', '10', '', '5000']])
        (s,) = m.sigs(m.res(), 'LAB')
        self.assertEqual(s['extra']['recent_hours_micro'], 420 * 1_000_000)
        self.assertEqual(s['quantification']['gross_cents'], 100 * 5000)

    def test_hours_that_are_not_a_plain_decimal_are_listed_and_the_entry_is_not_used(self):
        m = lab_world(extra_ts=[['T-NEG', 'W-B', 'PRJ-001', 'WP-1', '2026-09-22', '-5', '', '5000']])
        r = m.res()
        self.assertIn({'subject': 'timesheet/T-NEG', 'why': 'hours are not a plain non-negative decimal'}, m.run(r, 'LAB')['not_assessed'])

    def test_an_entry_after_the_as_of_date_is_not_looked_at_at_all(self):
        m = lab_world(extra_ts=[['T-NEG', 'W-B', 'PRJ-001', 'WP-1', '2026-09-29', '-5', '', '5000']])
        r = m.res(as_of='2026-09-27')
        self.assertFalse([n for n in m.run(r, 'LAB')['not_assessed'] if n['subject'] == 'timesheet/T-NEG'])

    def test_a_quantity_that_is_not_a_plain_decimal_leaves_that_week_out(self):
        m = lab_world(recent_out=80, extra_wo=[])
        m2 = bare()
        ts = [['T-%02d' % i, 'W-A', 'PRJ-001', 'WP-1', w, '100', '0', '5000'] for i, w in enumerate(WEEKS)]
        wo = [['PRJ-001', 'WP-1', w, '-3' if i == 4 else '100', 'm2'] for i, w in enumerate(WEEKS)]
        m2.timesheets(*ts)
        m2.outputs(*wo)
        m2.reconcile()
        r = m2.res()
        self.assertEqual(m2.sigs(r, 'LAB'), [])
        self.assertEqual(m2.run(r, 'LAB')['not_assessed'], [{'subject': 'WP-1', 'why': 'fewer than 12 complete weeks with both hours and output'}])
        self.assertEqual(len(m.sigs(m.res(), 'LAB')), 1)

    def test_a_package_whose_only_output_starts_on_the_as_of_day_is_evaluated_and_one_that_starts_later_is_not(self):
        m = lab_world(extra_wo=[['PRJ-001', 'WP-NEW', '2026-09-29', '5', 'm2'], ['PRJ-001', 'WP-LATE', '2026-09-30', '5', 'm2']])
        r = m.res(as_of='2026-09-29')
        subjects = [n['subject'] for n in m.run(r, 'LAB')['not_assessed']]
        self.assertIn('WP-NEW', subjects)
        self.assertNotIn('WP-LATE', subjects)

    def test_a_window_with_no_baseline_output_no_baseline_hours_or_no_recent_hours_is_not_assessed(self):
        for kw in ({'base_out': 0}, {'base_hours': 0}, {'recent_hours': 0}):
            m = lab_world(**kw)
            r = m.res()
            self.assertEqual(m.sigs(r, 'LAB'), [], kw)
            self.assertEqual(m.run(r, 'LAB')['not_assessed'], [{'subject': 'WP-1', 'why': 'a window has no output or no hours'}], kw)

    def test_a_zero_hourly_rate_gives_an_unquantified_signal_with_no_impact_amount(self):
        m = lab_world(rate='0')
        (s,) = m.sigs(m.res(), 'LAB')
        self.assertEqual((s['quantification']['status'], s['priority']['potential_impact_cents']), ('unquantified', None))
        self.assertIn('missing or zero', s['quantification']['reason'])

    def test_the_evidence_says_which_window_each_record_belongs_to(self):
        m = lab_world()
        (s,) = m.sigs(m.res(), 'LAB')
        roles = {}
        for e in s['evidence']:
            roles.setdefault(e['role'], []).append(e['ref'])
        self.assertEqual(sorted((k, len(v)) for k, v in roles.items()), [('hours:baseline', 8), ('hours:recent', 4), ('output:baseline', 8), ('output:recent', 4)])
        self.assertTrue(all(r.startswith('work_output/') for r in roles['output:recent'] + roles['output:baseline']))
        self.assertEqual(sorted(roles['hours:recent']), ['timesheet/WP-1-T-%02d' % i for i in range(8, 12)])

    def test_the_silent_count_leaves_out_the_packages_that_could_not_be_assessed(self):
        m = bare()
        ts, wo = [], []
        for wp, out, weeks in (('WP-1', 80, WEEKS), ('WP-2', 100, WEEKS), ('WP-3', 100, WEEKS[:3])):
            for i, w in enumerate(weeks):
                late = i >= 8
                ts.append(['%s-%02d' % (wp, i), 'W-A', 'PRJ-001', wp, w, '100', '0', '5000'])
                wo.append(['PRJ-001', wp, w, str(out if late else 100), 'm2'])
        m.timesheets(*ts)
        m.outputs(*wo)
        m.reconcile()
        run = m.run(m.res(), 'LAB')
        self.assertEqual((run['evaluated'], run['signals'], run['silent'], len(run['not_assessed'])), (3, 1, 1, 1))

    def test_a_held_timesheet_entry_dated_on_the_as_of_day_is_listed_and_one_dated_later_is_not(self):
        m = bare()
        m.timesheets(['T-A', 'W', 'PRJ-001', 'WP-1', '2026-10-31', '8', '0', '5000'], ['T-B', 'W', 'PRJ-001', 'WP-1', '2026-11-02', '8', '0', '5000'])
        m.reconcile()
        r = m.res(as_of='2026-10-31')
        self.assertEqual(m.run(r, 'LAB')['not_assessed'], [{'subject': 'timesheet/T-A', 'why': 'FUTURE_DATED:work_date'}])

    def test_a_held_output_record_that_is_not_in_conflict_is_listed(self):
        m = bare()
        m.outputs(['PRJ-001', 'WP-1', '2026-10-26', '5', 'm2'])
        m.reconcile()
        r = m.res(as_of='2026-10-31')
        self.assertEqual(m.run(r, 'LAB')['not_assessed'], [{'subject': 'work_output/PRJ-001|WP-1|2026-10-26', 'why': 'FUTURE_DATED:week_start'}])


class TestDefectEdges(unittest.TestCase):
    def world(self, *rows, as_of=None):
        m = det_world()
        m.defects(*rows)
        m.reconcile()
        return m

    def test_a_defect_raised_on_the_as_of_day_counts(self):
        m = self.world(defect('DEF-1', raised='2026-07-01'), defect('DEF-2', raised='2026-08-01'), defect('DEF-3', raised='2026-09-30'))
        (s,) = m.sigs(m.res(), 'DEF')
        self.assertEqual(s['extra']['events'], 3)

    def test_costs_that_stay_the_same_are_not_growing(self):
        m = self.world(defect('DEF-1', raised='2026-07-01', cost='1000000'), defect('DEF-2', raised='2026-08-01', cost='1000000'), defect('DEF-3', raised='2026-09-01', cost='2000000'))
        (s,) = m.sigs(m.res(), 'DEF')
        self.assertEqual((s['taxonomy']['subtype'], s['extra']['growing']), ('repeat_defect', False))

    def test_a_defect_with_no_subcontractor_or_no_trade_is_listed_and_not_grouped(self):
        m = self.world(defect('DEF-1', sub=''), defect('DEF-2', trade=''), defect('DEF-3'))
        r = m.res()
        why = 'subcontractor or trade is not recorded, so it cannot be grouped'
        self.assertEqual(m.run(r, 'DEF')['not_assessed'], [{'subject': 'defect/DEF-1', 'why': why}, {'subject': 'defect/DEF-2', 'why': why}])

    def test_no_recorded_rework_cost_at_all_is_unquantified(self):
        m = self.world(defect('DEF-1', raised='2026-07-01', cost=''), defect('DEF-2', raised='2026-08-01', cost=''), defect('DEF-3', raised='2026-09-01', cost=''))
        (s,) = m.sigs(m.res(), 'DEF')
        self.assertEqual((s['quantification']['status'], s['quantification']['reason']), ('unquantified', 'no rework cost is recorded'))

    def test_some_costs_missing_gives_the_recorded_total_as_a_record_not_a_forecast(self):
        m = self.world(defect('DEF-1', raised='2026-07-01', cost='1000000'), defect('DEF-2', raised='2026-08-01', cost=''), defect('DEF-3', raised='2026-09-01', cost='2000000'))
        (s,) = m.sigs(m.res(), 'DEF')
        self.assertEqual((s['quantification']['status'], s['quantification']['gross_cents'], s['quantification']['label']), ('quantified', 3000000, 'record'))
        self.assertIn('not known for every defect', s['explanation']['observed'])


class TestD02Edges(unittest.TestCase):
    def test_a_future_dated_record_is_a_data_signal_once_the_as_of_day_has_reached_its_date(self):
        m = det_world()
        m.defects(defect('DEF-1', raised='2026-12-01'))
        m.reconcile()
        for as_of, expect in (('2026-11-30', 0), ('2026-12-01', 1), ('2026-12-31', 1)):
            r = m.res(as_of=as_of)
            self.assertEqual(len(m.sigs(r, 'D02')), expect, as_of)
            self.assertEqual('OUTSIDE_PERIOD:defect/DEF-1' in m.run(r, 'D02')['notes'], expect == 0, as_of)


if __name__ == '__main__':
    unittest.main()
