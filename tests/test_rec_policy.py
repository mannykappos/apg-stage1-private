"""M7: the recommendation policy (configuration with no default; versioned; approved by a second person)."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_rec import RecWorld
from apg.rec import demo_rec as DR, engine as E, policy as RP


class TestPolicyShape(unittest.TestCase):
    def test_demo_policy_is_valid_and_complete(self):
        p = DR.demo_rec_policy()
        self.assertEqual(RP.validate_policy(p), [])
        self.assertEqual(RP.missing(p), [])
        self.assertIn('SYNTHETIC', p['note'])

    def test_a_policy_with_nothing_configured_is_valid_but_says_what_is_missing(self):
        p = RP.new_policy('P0', 'pat')
        self.assertEqual(RP.missing(p), ['eligibility.stale_after_days', 'eligibility.min_strength_for_action', 'eligibility.due_soon_days', 'categories', 'approval_bands', 'rank_order',
                                         'scenario_required_above_cents', 'verification'])

    def test_bad_values_are_refused(self):
        cases = [dict(eligibility={'stale_after_days': -1}), dict(eligibility={'min_strength_for_action': 'certain'}), dict(eligibility={'due_soon_days': True}),
                 dict(eligibility={'other': 1}), dict(categories={'actual_loss': 'investigate'}), dict(categories={'made_up': 'recover'}), dict(categories={'actual_loss': 'close'}),
                 dict(mandatory_reviews={'quality_defects': ['vibes']}), dict(mandatory_reviews={'quality_defects': []}), dict(mandatory_reviews={'no_family': ['quality']}),
                 dict(approval_bands=[]), dict(approval_bands=[{'min_cents': 100, 'role': 'pm'}]), dict(approval_bands=[{'min_cents': 0, 'role': 'pm'}, {'min_cents': 0, 'role': 'cm'}]),
                 dict(approval_bands=[{'min_cents': 0, 'role': ''}]), dict(approval_bands=[{'min_cents': 0.5, 'role': 'pm'}]), dict(rank_order=[]), dict(rank_order=['score']),
                 dict(rank_order=['urgency', 'urgency']), dict(scenario_required_above_cents=-5), dict(verification={'offset_components': []}),
                 dict(verification={'offset_components': ['a', 'a']}), dict(verification={'other': 1}), dict(unknown_field=1), dict(note='')]
        for c in cases:
            with self.subTest(c=c):
                with self.assertRaises(RP.RecPolicyError):
                    RP.new_policy('P1', 'pat', **c)

    def test_approval_needs_a_human_policy_owner_who_is_not_the_proposer(self):
        p = RP.new_policy('P1', 'pat')
        self.assertFalse(RP.is_approved(p))
        ap = lambda who, role, kind: dict(p, approvals=[{'approver': who, 'role': role, 'kind': kind, 'date': '2026-10-19'}])
        self.assertFalse(RP.is_approved(ap('pat', RP.POLICY_ROLE, 'human')))
        self.assertFalse(RP.is_approved(ap('quinn', RP.POLICY_ROLE, 'ai')))
        self.assertFalse(RP.is_approved(ap('quinn', 'project_manager', 'human')))
        self.assertTrue(RP.is_approved(ap('quinn', RP.POLICY_ROLE, 'human')))
        self.assertFalse(RP.is_approved(ap('quinn', RP.POLICY_ROLE, 'human'), verified=set()))           # M7.1: at a run only audit-confirmed approvers count
        self.assertTrue(RP.is_approved(ap('quinn', RP.POLICY_ROLE, 'human'), verified={'quinn'}))

    def test_authority_bands(self):
        p = DR.demo_rec_policy()
        self.assertEqual([RP.authority_for(p, c) for c in (0, 1999999, 2000000, -2500000, 10000000, None)],
                         ['project_manager', 'project_manager', 'commercial_manager', 'commercial_manager', 'director', 'director'])
        self.assertIsNone(RP.authority_for(RP.new_policy('P', 'pat'), 5))


class TestPolicyStore(unittest.TestCase):
    def setUp(self):
        self.w = RecWorld()

    def test_a_stored_version_cannot_change_except_by_appending_approvals(self):
        p = DR.demo_rec_policy(version='V-X', proposer='paula')
        RP.store_policy(self.w.polprop, p)
        RP.approve_policy(self.w.polown, self.w.clock, 'V-X', 'ok')
        self.assertTrue(RP.is_approved(self.w.s.get(RP.POLICY_KIND, 'V-X').payload))
        q = DR.demo_rec_policy(version='V-X', proposer='paula', scenario_required_above_cents=1)
        with self.assertRaises(RP.RecPolicyError):
            RP.store_policy(self.w.polprop, q)

    def test_a_run_needs_a_rank_order(self):
        p = self.w.set_policy(rank_order=None)
        self.w.finding()
        with self.assertRaises(E.EngineError) as cm:
            E.run(self.w.s, self.w.reg, self.w.clock, '2026-09-30', p['version'])
        self.assertEqual(cm.exception.code, 'RANK_ORDER_NOT_CONFIGURED')

    def test_a_run_under_an_unapproved_policy_says_so(self):
        w = RecWorld(approved=False)
        w.finding()
        res = w.run()['result']
        self.assertFalse(res['policy']['approved'])

    def test_unknown_policy_version_is_refused(self):
        from apg import repro
        with self.assertRaises(repro.ReproError):
            E.run(self.w.s, self.w.reg, self.w.clock, '2026-09-30', 'NO-SUCH')


if __name__ == '__main__':
    unittest.main()
