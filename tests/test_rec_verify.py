"""M7: the realised-benefit verification gate (Section 05 section 10.1; Section 10 section 10; PG-RS-AC-10).  Savings count only with evidence."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_rec import AS_OF, RecWorld
from apg import repro
from apg.det import findings as FD
from apg.fin import forecast_book as FB
from apg.rec import lifecycle as L, verify as V


class Base(unittest.TestCase):
    def setUp(self):
        self.w = RecWorld()
        self.f = self.w.finding(gross=500000)
        self.rid = self.w.rid(self.f)
        self.w.to_completed(self.f)

    def verify(self, who=None, base=None, observed=550000, offsets=None, rationale='checked the invoices against the adopted forecast'):
        return V.verify(who or self.w.verifier, self.w.clock, self.w.reg, self.w.m.reg, self.rid, base or self.w.baseline['run_key'], observed,
                        self.w.offsets() if offsets is None else offsets, rationale, self.w.policy)

    def code(self, fn):
        with self.assertRaises(V.VerifyError) as cm:
            fn()
        return cm.exception.code


class TestGate(Base):
    def test_a_complete_verification_records_a_reproducible_realised_figure(self):
        r = self.verify(offsets=self.w.offsets(freight_and_handling={'cents': 20000, 'basis': 'one extra delivery'}))
        res = r['outcome']['result']
        self.assertEqual(r['status'], 'verified_outcome')
        self.assertEqual((res['observed_benefit_cents'], res['offsetting_costs_cents'], res['realised_net_cents'], res['expected_net_cents'], res['variance_cents']), (550000, 20000, 530000, 500000, 30000))
        self.assertEqual(res['baseline']['adopted_by'], 'olga')
        self.assertTrue(repro.replay(self.w.s, self.w.reg, r['outcome']['run_key']).ok)
        self.assertEqual(self.code(lambda: self.verify()), 'NOT_COMPLETED')

    def test_a_verified_outcome_can_show_that_no_benefit_was_realised(self):
        r = self.verify(observed=100000, offsets=self.w.offsets(rework_and_delay={'cents': 250000, 'basis': 'two days of standing time'}))
        self.assertEqual((r['outcome']['result']['realised_net_cents'], r['outcome']['result']['label']), (-150000, 'verified: no realised net benefit'))

    def test_only_an_independent_person_with_the_verifier_role(self):
        self.assertEqual(self.code(lambda: self.verify(who=self.w.ai)), 'HUMAN_REQUIRED')
        self.assertEqual(self.code(lambda: self.verify(who=self.w.owner)), 'ROLE_REQUIRED')
        for user in ('olly', 'opal', 'pete'):                                       # wrote the inputs, submitted/started/completed, approved
            v = self.w.w.who('v-' + user, 'zero_one', user, (L.VERIFIER,), ttl=10 ** 8)
            with self.subTest(user=user):
                self.assertEqual(self.code(lambda: self.verify(who=v)), 'VERIFIER_NOT_INDEPENDENT')

    def test_every_offsetting_cost_component_must_be_addressed(self):
        o = self.w.offsets()
        o.pop('financing')
        self.assertEqual(self.code(lambda: self.verify(offsets=o)), 'OFFSETS_NOT_ADDRESSED')
        for bad in ({'cents': -1, 'basis': 'x'}, {'cents': 1}, {'cents': 1.0, 'basis': 'x'}, {'not_applicable': ''}, {'cents': 1, 'basis': 'x', 'not_applicable': 'y'}, 'none'):
            with self.subTest(bad=bad):
                self.assertEqual(self.code(lambda: self.verify(offsets=self.w.offsets(financing=bad))), 'OFFSETS_NOT_ADDRESSED')
        self.assertEqual(self.code(lambda: self.verify(offsets=None or 'x')), 'OFFSETS_REQUIRED')

    def test_without_configured_offset_components_nothing_can_be_verified(self):
        pol = {k: v for k, v in self.w.policy.items() if k != 'verification'}
        with self.assertRaises(V.VerifyError) as cm:
            V.verify(self.w.verifier, self.w.clock, self.w.reg, self.w.m.reg, self.rid, self.w.baseline['run_key'], 1, self.w.offsets(), 'x', pol)
        self.assertEqual(cm.exception.code, 'VERIFICATION_NOT_CONFIGURED')

    def test_the_observed_benefit_and_rationale_are_required(self):
        self.assertEqual(self.code(lambda: self.verify(observed=1.5)), 'OBSERVED_REQUIRED')
        self.assertEqual(self.code(lambda: self.verify(observed=None)), 'OBSERVED_REQUIRED')
        self.assertEqual(self.code(lambda: self.verify(rationale=' ')), 'RATIONALE_REQUIRED')


class TestBaseline(Base):
    def test_the_baseline_must_be_an_adopted_forecast(self):
        unadopted = self.w.m.run('fin.forecast', extra={'forecast_version': 'F-A', 'note': 'another'})
        self.assertEqual(self.code(lambda: self.verify(base=unadopted['run_key'])), 'BASELINE_NOT_APPROVED')
        other = self.w.m.run('fin.actual_cost')
        self.assertEqual(self.code(lambda: self.verify(base=other['run_key'])), 'BASELINE_NOT_A_FORECAST')
        self.assertEqual(self.code(lambda: self.verify(base='nope')), 'BASELINE_NOT_A_FORECAST')

    def test_a_baseline_adopted_after_the_action_started_is_refused(self):
        w = RecWorld(with_baseline=False)
        f = w.finding(gross=500000)
        w.baseline = w.m.run('fin.forecast', extra={'forecast_version': 'F-A'})
        w.to_completed(f)
        w.clock.advance(3600)
        FB.adopt(w.fcowner, w.m.reg, w.clock, 'PRJ-001', AS_OF, w.baseline['run_key'])
        with self.assertRaises(V.VerifyError) as cm:
            V.verify(w.verifier, w.clock, w.reg, w.m.reg, w.rid(f), w.baseline['run_key'], 1, w.offsets(), 'x', w.policy)
        self.assertEqual(cm.exception.code, 'BASELINE_AFTER_START')

    def test_a_baseline_that_no_longer_reproduces_is_refused(self):
        rec = self.w.s.get(repro.KIND, self.w.baseline['run_key'])
        p = dict(rec.payload)
        p['result'] = dict(p['result'], note='altered')
        self.w.s.put(repro.KIND, self.w.baseline['run_key'], p, expected_revision=rec.revision)
        self.assertEqual(self.code(lambda: self.verify()), 'BASELINE_DOES_NOT_REPRODUCE')


class TestEvidence(Base):
    def test_implementation_evidence_that_changed_since_it_was_named_is_refused(self):
        rec = self.w.s.get(L.KIND, self.rid)
        p = dict(rec.payload)
        impl = dict(p['implementation'])
        impl['evidence_refs'] = [[k, key, rev, 'f' * 64] for k, key, rev, _ in impl['evidence_refs']]
        p['implementation'] = impl
        self.w.s.put(L.KIND, self.rid, p, expected_revision=rec.revision)
        self.assertEqual(self.code(lambda: self.verify()), 'IMPLEMENTATION_EVIDENCE_CHANGED')

    def test_no_shortcut_to_a_realised_saving(self):
        with self.assertRaises(FD.LifecycleError):
            FD.claim_realised(self.w.s, self.f, 1)
        from apg.mkt import opportunity as OP
        with self.assertRaises(OP.SavingNotVerified):
            OP.claim_saving({'id': 'x'})
        with self.assertRaises(L.RecError):
            L.transition(self.w.owner2, self.w.clock, self.rid, 'verified_outcome')

    def test_an_approved_but_not_completed_recommendation_cannot_be_verified(self):
        w = RecWorld()
        f = w.finding(gross=500000)
        w.to_approved(f)
        with self.assertRaises(V.VerifyError) as cm:
            V.verify(w.verifier, w.clock, w.reg, w.m.reg, w.rid(f), w.baseline['run_key'], 1, w.offsets(), 'x', w.policy)
        self.assertEqual(cm.exception.code, 'NOT_COMPLETED')

    def test_the_verified_figure_is_reported_apart_from_the_estimate(self):
        r = self.verify()
        self.assertEqual(r['current']['dimensions']['net_benefit']['label'], 'estimate')
        self.assertIn('Section 05 section 10.1', r['outcome']['result']['label'])
        self.assertEqual(r['approval']['expected']['net_benefit_cents'], 500000)


if __name__ == '__main__':
    unittest.main()
