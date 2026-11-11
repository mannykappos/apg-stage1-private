"""M7: constraints a high rank cannot bypass, approval authority and scenario comparison (Section 10 sections 3, 7, 9; PG-RS-AC-05, 06, 07, 13: blocked actions)."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_rec import COMPLETE_ALT, RecWorld
from apg.rec import inputs as IN, lifecycle as L


class TestBlocked(unittest.TestCase):
    def setUp(self):
        self.w = RecWorld()

    def test_a_pending_mandatory_review_blocks_submission_even_for_the_first_ranked_line(self):
        self.w.set_policy(rank_order=['magnitude'])
        f = self.w.finding(family='quality_defects', gross=90000000)
        self.w.finding(gross=100)
        rid = self.w.ready(f, reviews=False)
        run = self.w.run()
        e = self.w.entry(run, f)
        self.assertEqual(e['rank'], 1)
        self.assertEqual(e['constraints']['mandatory_reviews'], [{'type': 'quality', 'status': 'pending', 'by': None, 'outcome': None}])
        self.assertIn('quality review pending', e['constraints']['blocked_by'])
        self.assertFalse(e['dimensions']['actionability']['actionable_now'])
        with self.assertRaises(L.RecError) as cm:
            L.submit(self.w.owner2, self.w.clock, rid)
        self.assertEqual(cm.exception.code, 'NOT_SUBMITTABLE')
        self.assertIn('quality review pending', str(cm.exception))

    def test_a_review_that_does_not_clear_the_action_blocks_it(self):
        f = self.w.finding(family='quality_defects', gross=500000)
        rid = self.w.ready(f, reviews=False)
        IN.record_review(self.w.creview, self.w.clock, rid, 'quality', 'not_cleared', 'the substitute fails the specification')
        e = self.w.entry(self.w.run(), f)
        self.assertIn('quality review did not clear the action', e['constraints']['blocked_by'])
        with self.assertRaises(L.RecError):
            L.submit(self.w.owner2, self.w.clock, rid)
        IN.record_review(self.w.creview, self.w.clock, rid, 'quality', 'cleared', 'a compliant substitute was found')
        self.w.run()
        self.assertEqual(L.submit(self.w.owner2, self.w.clock, rid)['status'], 'awaiting_approval')
        hist = [h for h in IN.get(self.w.s, rid)['history'] if h['event'] == 'review_recorded']
        self.assertEqual([h['outcome'] for h in hist], ['not_cleared', 'cleared'])
        self.assertEqual(hist[1]['replaces']['outcome'], 'not_cleared')

    def test_reviews_and_assessments_need_a_reviewer_who_did_not_write_the_inputs(self):
        f = self.w.finding()
        rid = self.w.rid(f)
        IN.set_inputs(self.w.owner, self.w.clock, rid, action_kind='internal_review')
        both = self.w.w.who('both', 'zero_one', 'olly', (IN.REVIEWER,), ttl=10 ** 8)        # same user as the owner
        with self.assertRaises(IN.InputError) as cm:
            IN.record_review(both, self.w.clock, rid, 'quality', 'cleared', 'x')
        self.assertEqual(cm.exception.code, 'SELF_REVIEW')
        with self.assertRaises(IN.InputError):
            IN.record_evidence_assessment(both, self.w.clock, rid, 'x', False, 'y')
        with self.assertRaises(IN.InputError) as cm:
            IN.record_review(self.w.owner, self.w.clock, rid, 'quality', 'cleared', 'x')
        self.assertEqual(cm.exception.code, 'ROLE_REQUIRED')
        for bad in (('vibes', 'cleared', 'x'), ('quality', 'maybe', 'x'), ('quality', 'cleared', ' ')):
            with self.assertRaises(IN.InputError):
                IN.record_review(self.w.creview, self.w.clock, rid, *bad)
        with self.assertRaises(IN.InputError):
            IN.record_evidence_assessment(self.w.creview, self.w.clock, rid, 'x', 'no', 'y')

    def test_no_machine_can_write_inputs_reviews_or_assessments(self):
        f = self.w.finding()
        rid = self.w.rid(f)
        for fn in (lambda: IN.set_inputs(self.w.ai, self.w.clock, rid, action_kind='internal_review'), lambda: IN.record_review(self.w.ai, self.w.clock, rid, 'quality', 'cleared', 'x'),
                   lambda: IN.record_evidence_assessment(self.w.ai, self.w.clock, rid, 'x', False, 'y')):
            with self.assertRaises(IN.InputError) as cm:
                fn()
            self.assertEqual(cm.exception.code, 'HUMAN_REQUIRED')

    def test_the_kind_of_action_must_be_stated_and_consequential_kinds_are_flagged(self):
        f = self.w.finding()
        rid = self.w.ready(f, kind='supplier_change')
        e = self.w.entry(self.w.run(), f)
        self.assertTrue(e['constraints']['consequential_action'])
        self.assertIn("APG does not carry it out", ' '.join(e['dimensions']['risk_and_constraints']))
        g = self.w.finding()
        IN.set_inputs(self.w.owner, self.w.clock, self.w.rid(g), expected_benefit={'cents': 1, 'basis': 'b'}, incremental_costs=[{'component': 'c', 'cents': 0, 'basis': 'none'}],
                      alternatives=[dict(COMPLETE_ALT, baseline_ref='repro_record/' + self.w.baseline['run_key'])])
        self.w.run()
        with self.assertRaises(L.RecError) as cm:
            L.submit(self.w.owner2, self.w.clock, self.w.rid(g))
        self.assertIn('the kind of action is not stated', str(cm.exception))
        self.assertEqual(L.submit(self.w.owner2, self.w.clock, rid)['status'], 'awaiting_approval')

    def test_without_incremental_costs_a_recommendation_cannot_be_submitted(self):
        f = self.w.finding()
        rid = self.w.rid(f)
        IN.set_inputs(self.w.owner, self.w.clock, rid, action_kind='internal_review', expected_benefit={'cents': 1, 'basis': 'b'},
                      alternatives=[dict(COMPLETE_ALT, baseline_ref='repro_record/' + self.w.baseline['run_key'])])
        self.w.run()
        with self.assertRaises(L.RecError) as cm:
            L.submit(self.w.owner2, self.w.clock, rid)
        self.assertIn('incremental costs not estimated', str(cm.exception))

    def test_an_investigation_or_closure_route_cannot_be_submitted_as_an_action(self):
        for kw in (dict(status='detected'), dict(strength='weak'), dict(status='resolved')):
            with self.subTest(kw=kw):
                f = self.w.finding(**kw)
                rid = self.w.ready(f)
                self.w.run()
                with self.assertRaises(L.RecError) as cm:
                    L.submit(self.w.owner2, self.w.clock, rid)
                self.assertIn('not action', str(cm.exception))


class TestAuthority(unittest.TestCase):
    def setUp(self):
        self.w = RecWorld()

    def test_the_approval_role_follows_the_band_of_the_amount(self):
        cases = {1000000: 'project_manager', 2000000: 'commercial_manager', 50000000: 'director', None: 'director'}
        for gross, role in cases.items():
            with self.subTest(gross=gross):
                f = self.w.finding(gross=gross)
                self.assertEqual(self.w.entry(self.w.run(ingest=False), f)['constraints']['approval_role'], role)

    def test_a_person_without_the_band_role_cannot_approve(self):
        f = self.w.finding(gross=50000000)
        rid = self.w.ready(f)
        self.w.run()
        L.submit(self.w.owner2, self.w.clock, rid)
        r = L.get(self.w.s, rid)
        t = L.approval_token(r)
        for who in (self.w.pm, self.w.cm):
            with self.assertRaises(L.RecError) as cm:
                L.approve(who, self.w.clock, rid, t['version'], t['digest'], t['submission'], 'ok')
            self.assertEqual(cm.exception.code, 'ROLE_REQUIRED')
        self.assertEqual(L.approve(self.w.director, self.w.clock, rid, t['version'], t['digest'], t['submission'], 'ok')['status'], 'approved')

    def test_without_bands_nothing_can_be_submitted(self):
        self.w.set_policy(approval_bands=None)
        f = self.w.finding()
        rid = self.w.ready(f)
        e = self.w.entry(self.w.run(), f)
        self.assertIsNone(e['constraints']['approval_role'])
        self.assertIn('no approval authority is configured', e['constraints']['blocked_by'])
        with self.assertRaises(L.RecError):
            L.submit(self.w.owner2, self.w.clock, rid)


class TestScenarios(unittest.TestCase):
    def setUp(self):
        self.w = RecWorld()

    def test_a_material_decision_needs_a_complete_alternative(self):
        f = self.w.finding(gross=5000000)
        rid = self.w.ready(f, alts=[])
        e = self.w.entry(self.w.run(), f)
        self.assertTrue(e['scenarios']['required'])
        self.assertFalse(e['scenarios']['complete'])
        self.assertIn('scenario comparison incomplete', e['constraints']['blocked_by'])
        with self.assertRaises(L.RecError):
            L.submit(self.w.owner2, self.w.clock, rid)

    def test_an_incomplete_alternative_lists_exactly_what_it_lacks(self):
        f = self.w.finding(gross=5000000)
        alt = dict(COMPLETE_ALT, baseline_ref='repro_record/' + self.w.baseline['run_key'])
        alt.pop('invalidating_conditions')
        alt['verification_method'] = ' '
        self.w.ready(f, alts=[alt])
        e = self.w.entry(self.w.run(), f)
        self.assertEqual(e['scenarios']['alternatives'][0]['missing'], ['invalidating_conditions', 'verification_method'])
        self.assertIn("lacks: invalidating_conditions, verification_method", ' '.join(e['scenarios']['gaps']))

    def test_below_the_materiality_amount_no_alternative_is_required_and_no_action_is_always_shown(self):
        f = self.w.finding(gross=500000)
        rid = self.w.ready(f, alts=[])
        e = self.w.entry(self.w.run(), f)
        self.assertFalse(e['scenarios']['required'])
        self.assertEqual([a['name'] for a in e['scenarios']['alternatives']], ['no action (engine-generated reference)'])
        self.assertEqual(L.submit(self.w.owner2, self.w.clock, rid)['status'], 'awaiting_approval')

    def test_without_a_materiality_amount_every_action_needs_an_alternative(self):
        self.w.set_policy(scenario_required_above_cents=None)
        f = self.w.finding(gross=1)
        self.w.ready(f, alts=[])
        self.assertTrue(self.w.entry(self.w.run(), f)['scenarios']['required'])

    def test_an_alternative_must_name_a_stored_forecast_as_its_baseline(self):
        f = self.w.finding()
        rid = self.w.rid(f)
        for ref in ('repro_record/nope', 'fin_forecast_slot/PRJ-001|project|2026-09-30', 'forecast'):
            with self.subTest(ref=ref):
                with self.assertRaises(IN.InputError) as cm:
                    IN.set_inputs(self.w.owner, self.w.clock, rid, alternatives=[dict(COMPLETE_ALT, baseline_ref=ref)])
                self.assertEqual(cm.exception.code, 'BASELINE_UNKNOWN')

    def test_the_cost_of_delay_is_stated_only_where_the_data_supports_it(self):
        a = self.w.finding(interp='potential_opportunity', family='procurement_materials', label='estimate', date='2026-10-20', time_sensitive=True)
        b = self.w.finding()
        c = self.w.finding(date='2026-09-01')
        run = self.w.run(ingest=False)
        self.assertIn('closes on 2026-10-20', self.w.entry(run, a)['explanation']['consequences_of_delay'])
        self.assertIn('not supportable from the data', self.w.entry(run, b)['explanation']['consequences_of_delay'])
        self.assertIn('overdue', self.w.entry(run, c)['explanation']['consequences_of_delay'])


if __name__ == '__main__':
    unittest.main()
