"""M7: explainable multi-factor prioritisation (Section 10 section 4; PG-RS-AC-01, 02, 13: conflicting priorities)."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_rec import RecWorld
from apg.rec import engine as E, policy as RP


class TestDimensions(unittest.TestCase):
    def setUp(self):
        self.w = RecWorld()

    def test_every_dimension_is_reported_separately_and_there_is_no_combined_score(self):
        f = self.w.finding(date='2026-10-05', time_sensitive=True)
        e = self.w.entry(self.w.run(ingest=False), f)
        self.assertEqual(set(e['dimensions']), {'magnitude', 'urgency', 'confidence', 'time_sensitivity', 'actionability', 'implementation_cost', 'expected_benefit', 'net_benefit',
                                                'dependencies', 'risk_and_constraints'})
        text = repr(e).lower()
        self.assertNotIn('score', text)
        self.assertEqual([x['dimension'] for x in e['rank_factors']], self.w.policy['rank_order'])

    def test_magnitude_urgency_and_confidence_are_distinct_values(self):
        a = self.w.finding(gross=90000000, strength='moderate')                         # large, moderate evidence, no date
        b = self.w.finding(gross=100000, strength='strong', date='2026-10-02', time_sensitive=True)
        run = self.w.run(ingest=False)
        ea, eb = self.w.entry(run, a), self.w.entry(run, b)
        self.assertEqual((ea['dimensions']['magnitude']['cents'], ea['dimensions']['confidence']['evidence_strength'], ea['dimensions']['urgency']['class']), (90000000, 'moderate', 'not_dated'))
        self.assertEqual((eb['dimensions']['magnitude']['cents'], eb['dimensions']['confidence']['evidence_strength'], eb['dimensions']['urgency']['class']), (100000, 'strong', 'soon'))

    def test_magnitude_is_never_called_a_benefit(self):
        f = self.w.finding(gross=5000000)
        e = self.w.entry(self.w.run(ingest=False), f)
        self.assertIn('not a benefit', e['dimensions']['magnitude']['kind'])
        self.assertIsNone(e['dimensions']['expected_benefit']['cents'])
        self.assertIsNone(e['dimensions']['net_benefit']['cents'])


class TestOrder(unittest.TestCase):
    def setUp(self):
        self.w = RecWorld()

    def test_a_large_weak_estimate_does_not_outrank_a_small_well_supported_time_critical_issue(self):
        big = self.w.finding(gross=90000000, strength='weak', label='estimate')
        small = self.w.finding(gross=200000, strength='strong', date='2026-10-03', time_sensitive=True)
        run = self.w.run(ingest=False)
        self.assertLess(self.w.entry(run, small)['rank'], self.w.entry(run, big)['rank'])
        reason = self.w.entry(run, big)['rank_reason']
        self.assertIn('below ' + self.w.rid(small), reason)

    def test_conflicting_priorities_are_settled_by_the_stated_order_and_explained(self):
        urgent = self.w.finding(gross=300000, date='2026-10-02')                         # small, due soon
        large = self.w.finding(gross=50000000)                                          # large, no date
        run = self.w.run(ingest=False)
        eu, el = self.w.entry(run, urgent), self.w.entry(run, large)
        self.assertLess(eu['rank'], el['rank'])
        self.assertIn('urgency', el['rank_reason'])
        self.w.set_policy(rank_order=['magnitude', 'urgency', 'confidence', 'actionability', 'time_sensitivity', 'net_benefit'])
        run2 = self.w.run(ingest=False)
        eu2, el2 = self.w.entry(run2, urgent), self.w.entry(run2, large)
        self.assertLess(el2['rank'], eu2['rank'])
        self.assertIn('financial magnitude', eu2['rank_reason'])

    def test_every_ranked_line_after_the_first_names_the_line_above_and_the_deciding_dimension(self):
        for g in (100000, 200000, 300000, None):
            self.w.finding(gross=g)
        self.w.finding(status='detected')
        self.w.finding(strength='weak')
        run = self.w.run(ingest=False)
        ranked = sorted((e for e in run['result']['recommendations'] if e['rank']), key=lambda e: e['rank'])
        self.assertEqual([e['rank'] for e in ranked], list(range(1, len(ranked) + 1)))
        self.assertEqual(ranked[0]['rank_reason'], 'first')
        for prev, e in zip(ranked, ranked[1:]):
            self.assertTrue(e['rank_reason'].startswith(('below ' + prev['rec_id'], 'ties with ' + prev['rec_id'])), e['rank_reason'])

    def test_a_full_tie_is_broken_by_finding_id_and_says_so(self):
        a = self.w.finding(gross=100000)
        b = self.w.finding(gross=100000)
        run = self.w.run(ingest=False)
        first, second = sorted([a, b])
        self.assertLess(self.w.entry(run, first)['rank'], self.w.entry(run, second)['rank'])
        self.assertIn('tie-breaker and not a judgement', self.w.entry(run, second)['rank_reason'])

    def test_investigation_can_rank_above_action_when_the_order_says_so_and_the_route_stays_visible(self):
        self.w.set_policy(rank_order=['urgency', 'magnitude'])
        inv = self.w.finding(status='detected', gross=100000, date='2026-10-01')
        act = self.w.finding(gross=900000)
        run = self.w.run(ingest=False)
        ei, ea = self.w.entry(run, inv), self.w.entry(run, act)
        self.assertLess(ei['rank'], ea['rank'])
        self.assertEqual((ei['route'], ea['route']), ('investigate', 'action'))
        self.assertFalse(ei['dimensions']['actionability']['actionable_now'])

    def test_unquantified_amounts_are_placed_after_quantified_ones_and_say_so(self):
        self.w.set_policy(rank_order=['magnitude'])
        q = self.w.finding(gross=1)
        u = self.w.finding(gross=None)
        run = self.w.run(ingest=False)
        self.assertLess(self.w.entry(run, q)['rank'], self.w.entry(run, u)['rank'])
        self.assertIn('unquantified (placed after quantified ones)', self.w.entry(run, u)['rank_reason'])

    def test_the_order_is_the_same_whatever_order_the_findings_were_stored_in(self):
        spec = ((100, 'strong'), (100, 'moderate'), (5000, 'strong'), (5000, 'weak'), (None, 'strong'))

        def seq(world, items):
            fids = {world.finding(gross=g, strength=s): (g, s) for g, s in items}
            run = world.run(ingest=False)
            return [fids[e['finding_id']] for e in sorted((e for e in run['result']['recommendations'] if e['rank']), key=lambda e: e['rank'])]
        self.assertEqual(seq(self.w, spec), seq(RecWorld(), tuple(reversed(spec))))

    def test_rank_keys_are_exactly_the_documented_dimensions(self):
        self.assertEqual(set(RP.RANK_KEYS), set(E.LABELS))


if __name__ == '__main__':
    unittest.main()
