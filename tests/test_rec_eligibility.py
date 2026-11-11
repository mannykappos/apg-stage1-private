"""M7: eligibility gates before ranking (Section 10 section 3; PG-RS-AC-03, 13: missing evidence, expired opportunities, blocked actions)."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_rec import RecWorld
from apg.rec import inputs as IN


class TestRoutes(unittest.TestCase):
    def setUp(self):
        self.w = RecWorld()

    def route(self, fid, **kw):
        e = self.w.entry(self.w.run(ingest=False, **kw), fid)
        return e['route'], e['category'], e['eligibility']['codes']

    def test_a_confirmed_well_evidenced_finding_is_routed_to_action_with_its_policy_category(self):
        f = self.w.finding()
        self.assertEqual(self.route(f), ('action', 'prevent', []))

    def test_an_unreviewed_finding_is_investigation_only(self):
        for st in ('detected', 'under_review'):
            with self.subTest(st=st):
                f = self.w.finding(status=st)
                r, c, codes = self.route(f)
                self.assertEqual((r, c), ('investigate', 'investigate'))
                self.assertIn('FINDING_NOT_REVIEWED', codes)

    def test_weak_evidence_is_investigation_only(self):
        f = self.w.finding(strength='weak')
        self.assertEqual(self.route(f)[:2], ('investigate', 'investigate'))
        self.assertIn('EVIDENCE_WEAK', self.route(f)[2])
        g = self.w.finding(strength='moderate')
        self.assertEqual(self.route(g)[0], 'action')

    def test_missing_information_counts_as_critical_until_a_reviewer_says_otherwise(self):
        f = self.w.finding(missing=('the signed delivery docket', 'the supplier statement'))
        self.assertIn('EVIDENCE_MISSING', self.route(f)[2])
        rid = self.w.rid(f)
        IN.record_evidence_assessment(self.w.creview, self.w.clock, rid, 'the signed delivery docket', False, 'the invoice shows delivery')
        r, _, codes = self.route(f)
        self.assertEqual(r, 'investigate')
        e = self.w.entry(self.w.run(ingest=False), f)
        self.assertEqual(e['dimensions']['confidence']['critical_missing'], ['the supplier statement'])
        IN.record_evidence_assessment(self.w.creview, self.w.clock, rid, 'the supplier statement', False, 'not needed to prevent the overrun')
        self.assertEqual(self.route(f)[0], 'action')
        IN.record_evidence_assessment(self.w.creview, self.w.clock, rid, 'the supplier statement', True, 'on reflection it is needed')
        self.assertEqual(self.route(f)[0], 'investigate')

    def test_an_assessment_naming_an_item_the_finding_does_not_list_changes_nothing(self):
        f = self.w.finding(missing=('the supplier statement',))
        IN.record_evidence_assessment(self.w.creview, self.w.clock, self.w.rid(f), 'the supplier  statement', False, 'typo')
        self.assertIn('EVIDENCE_MISSING', self.route(f)[2])

    def test_stale_evidence_is_investigation_only(self):
        f = self.w.finding(as_of='2026-08-01')
        r, _, codes = self.route(f)
        self.assertEqual(r, 'investigate')
        self.assertIn('EVIDENCE_STALE', codes)
        e = self.w.entry(self.w.run(ingest=False), f)
        self.assertEqual((e['dimensions']['confidence']['freshness'], e['dimensions']['confidence']['evidence_age_days']), ('stale', 60))
        g = self.w.finding(as_of='2026-08-31')
        self.assertEqual(self.route(g)[0], 'action')                        # 30 days: at the limit, not over it

    def test_without_an_age_limit_freshness_cannot_be_judged_and_the_finding_is_not_actionable(self):
        self.w.set_policy(eligibility={'min_strength_for_action': 'moderate', 'due_soon_days': 14})
        f = self.w.finding()
        r, _, codes = self.route(f)
        self.assertEqual(r, 'investigate')
        self.assertIn('FRESHNESS_NOT_CONFIGURED', codes)

    def test_without_a_minimum_strength_no_action_is_offered(self):
        self.w.set_policy(eligibility={'stale_after_days': 30, 'due_soon_days': 14})
        f = self.w.finding()
        self.assertIn('STRENGTH_RULE_NOT_CONFIGURED', self.route(f)[2])

    def test_a_data_integrity_finding_is_always_investigation(self):
        f = self.w.finding(interp='data_quality_risk', family='data_integrity', gross=None)
        r, c, codes = self.route(f)
        self.assertEqual((r, c), ('investigate', 'investigate'))
        self.assertIn('DATA_QUALITY_FINDING', codes)

    def test_an_interpretation_with_no_category_is_investigated_not_dropped(self):
        cats = dict(self.w.policy['categories'])
        cats.pop('forecast_exposure')
        self.w.set_policy(categories=cats)
        f = self.w.finding()
        r, c, codes = self.route(f)
        self.assertEqual((r, c), ('investigate', 'investigate'))
        self.assertIn('CATEGORY_NOT_CONFIGURED', codes)

    def test_a_resolved_finding_is_routed_to_close(self):
        f = self.w.finding(status='resolved')
        self.assertEqual(self.route(f), ('close', 'close', ['FINDING_RESOLVED']))

    def test_an_expired_opportunity_is_routed_to_close_not_ranked(self):
        f = self.w.finding(interp='potential_opportunity', family='procurement_materials', label='estimate', date='2026-09-29', time_sensitive=True)
        run = self.w.run(ingest=False)
        e = self.w.entry(run, f)
        self.assertEqual((e['route'], e['category'], e['rank']), ('close', 'close', None))
        self.assertIn('WINDOW_EXPIRED', e['eligibility']['codes'])
        self.assertNotIn(e['rec_id'], run['result']['ranked'])
        self.assertFalse(e['overlap']['counted_in_totals'])

    def test_an_opportunity_on_its_last_day_is_still_actionable(self):
        f = self.w.finding(interp='potential_opportunity', family='procurement_materials', label='estimate', date='2026-09-30', time_sensitive=True)
        e = self.w.entry(self.w.run(ingest=False), f)
        self.assertEqual((e['route'], e['dimensions']['time_sensitivity']['state']), ('action', 'closing'))

    def test_an_exposure_whose_date_has_passed_is_overdue_not_expired(self):
        f = self.w.finding(interp='cash_timing_exposure', family='cash_capital', date='2026-09-01', time_sensitive=True)
        e = self.w.entry(self.w.run(ingest=False), f)
        self.assertEqual((e['route'], e['dimensions']['time_sensitivity']['state'], e['dimensions']['urgency']['class']), ('action', 'passed', 'overdue'))

    def test_an_action_already_in_hand_is_tracked_not_ranked(self):
        for st in ('action_approved', 'in_progress'):
            with self.subTest(st=st):
                f = self.w.finding(status=st)
                e = self.w.entry(self.w.run(ingest=False), f)
                self.assertEqual((e['route'], e['rank']), ('in_hand', None))

    def test_dismissed_and_superseded_findings_are_excluded_never_ranked_never_counted(self):
        d = self.w.finding(status='dismissed', gross=99999999)
        s = self.w.finding(status='superseded', gross=88888888)
        run = self.w.run(ingest=False)
        ex = {x['finding_id']: x for x in run['result']['excluded']}
        self.assertEqual(set(ex) & {d, s}, {d, s})
        self.assertFalse(any(e['finding_id'] in (d, s) for e in run['result']['recommendations']))
        self.assertTrue(all(t['potential_gross_counted_cents'] < 88888888 for t in run['result']['totals'].values()))

    def test_amount_status_and_unapproved_detection_policy_are_qualified_on_the_line(self):
        f = self.w.finding(label='estimate')
        g = self.w.finding(gross=None)
        h = self.w.finding()
        from apg.det import findings as FD
        rec = self.w.det.get(FD.KIND, h)
        p = dict(rec.payload, policy_unapproved=True)
        self.w.det.put(FD.KIND, h, p, expected_revision=rec.revision)
        run = self.w.run(ingest=False)
        self.assertIn('AMOUNT_QUALIFIED', self.w.entry(run, f)['eligibility']['codes'])
        self.assertIn('AMOUNT_UNQUANTIFIED', self.w.entry(run, g)['eligibility']['codes'])
        self.assertIn('DETECTION_POLICY_UNAPPROVED', self.w.entry(run, h)['eligibility']['codes'])

    def test_an_unreadable_date_is_not_dated_and_the_finding_is_investigated(self):
        f = self.w.finding(date='2026-02-30', time_sensitive=True)
        e = self.w.entry(self.w.run(ingest=False), f)
        self.assertEqual((e['route'], e['dimensions']['urgency']['class'], e['dimensions']['time_sensitivity']['state']), ('investigate', 'not_dated', 'none'))
        self.assertIn('DATE_UNREADABLE', e['eligibility']['codes'])
        self.assertIn('cannot be read', e['dimensions']['urgency']['basis'])

    def test_a_run_dated_before_the_evidence_cannot_use_it(self):
        f = self.w.finding(as_of='2026-10-05')
        e = self.w.entry(self.w.run(ingest=False), f)
        self.assertEqual(e['route'], 'investigate')
        self.assertIn('EVIDENCE_AFTER_RUN_DATE', e['eligibility']['codes'])

    def test_project_filter(self):
        a = self.w.finding(project='PRJ-001')
        b = self.w.finding(project='PRJ-002')
        run = self.w.run(ingest=False, project='PRJ-002')
        ids = [e['finding_id'] for e in run['result']['recommendations']]
        self.assertEqual(ids, [b])
        self.assertNotIn(a, ids)


if __name__ == '__main__':
    unittest.main()
