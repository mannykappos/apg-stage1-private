import unittest
from . import _path                                         # noqa: F401
from apg.det import noise as N, policy as DP
from apg.det.demo_det import demo_det_policy

NZ = {'suppression_days': 7, 'renotify_on': ['severity_increase', 'status_transition', 'material_evidence']}


class TestDecide(unittest.TestCase):
    def d(self, event, noise=NZ, last=None, today='2026-10-10', token='t'):
        return N.decide('F1', event, token, noise, last, today)

    def test_new_and_reopened_always_send_even_with_no_noise_policy(self):
        for ev in ('new', 'reopened'):
            self.assertTrue(self.d(ev, None)['send'])
            self.assertTrue(self.d(ev, {'suppression_days': 30, 'renotify_on': []}, last='2026-10-09')['send'])

    def test_with_no_noise_policy_nothing_else_is_sent_and_the_reason_says_why(self):
        for ev in ('severity_increase', 'status_transition', 'material_evidence'):
            r = self.d(ev, None)
            self.assertFalse(r['send'])
            self.assertIn('NOISE_POLICY_NOT_CONFIGURED', r['why'])

    def test_an_event_the_policy_does_not_list_is_held(self):
        r = self.d('status_transition', {'suppression_days': 7, 'renotify_on': ['material_evidence']})
        self.assertEqual((r['send'], r['why']), (False, 'EVENT_NOT_LISTED_FOR_RENOTIFICATION'))
        self.assertFalse(self.d('status_transition', {'suppression_days': 7, 'renotify_on': []})['send'])

    def test_a_severity_increase_ignores_the_window(self):
        self.assertTrue(self.d('severity_increase', last='2026-10-10')['send'])

    def test_inside_the_window_status_and_evidence_changes_are_held_and_outside_they_are_sent(self):
        for ev in ('status_transition', 'material_evidence'):
            self.assertFalse(self.d(ev, last='2026-10-04')['send'])                           # 6 days
            self.assertIn('INSIDE_SUPPRESSION_WINDOW', self.d(ev, last='2026-10-04')['why'])
            self.assertTrue(self.d(ev, last='2026-10-03')['send'])                            # exactly 7 days: the window has passed

    def test_nothing_sent_yet_means_nothing_to_suppress(self):
        self.assertTrue(self.d('material_evidence', last=None)['send'])

    def test_a_listed_event_with_no_window_configured_is_held_after_a_first_send(self):
        r = self.d('material_evidence', {'renotify_on': ['material_evidence']}, last='2026-01-01')
        self.assertEqual(r['send'], False)
        self.assertIn('NO_SUPPRESSION_WINDOW_CONFIGURED', r['why'])

    def test_the_dedup_key_names_the_finding_the_event_and_the_state(self):
        a = self.d('material_evidence', token='x')['dedup_key']
        self.assertEqual(a, 'F1|material_evidence|x')
        self.assertNotEqual(a, self.d('material_evidence', token='y')['dedup_key'])
        self.assertNotEqual(a, N.decide('F2', 'material_evidence', 'x', NZ, None, '2026-10-10')['dedup_key'])

    def test_the_decision_is_pure(self):
        self.assertEqual(self.d('status_transition', last='2026-10-04'), self.d('status_transition', last='2026-10-04'))


class TestSeverity(unittest.TestCase):
    def setUp(self):
        self.dp = demo_det_policy()

    def test_a_rise_is_an_increase_and_a_fall_or_the_same_is_not(self):
        self.assertTrue(N.severity_increased(self.dp, 'low', 'medium'))
        self.assertTrue(N.severity_increased(self.dp, 'medium', 'high'))
        self.assertFalse(N.severity_increased(self.dp, 'high', 'medium'))
        self.assertFalse(N.severity_increased(self.dp, 'medium', 'medium'))

    def test_moving_from_unrated_is_not_a_rise_of_a_band(self):
        self.assertFalse(N.severity_increased(self.dp, 'low', 'unrated'))

    def test_severity_comes_from_the_policy_bands_and_is_unrated_without_them(self):
        self.assertEqual([DP.severity_of(self.dp, a) for a in (0, 4999999, 5000000, 24999999, 25000000)], ['low', 'low', 'medium', 'medium', 'high'])
        self.assertEqual(DP.severity_of(self.dp, None), 'unrated')
        pol = dict(self.dp, severity_bands=None)
        self.assertEqual(DP.severity_of(pol, 99999999), 'unrated')


class TestMessage(unittest.TestCase):
    def finding(self, status='detected', quantified=True):
        q = ({'status': 'quantified', 'gross_cents': 123456, 'label': 'estimate', 'reason': ''} if quantified else {'status': 'unquantified', 'gross_cents': None, 'label': None, 'reason': 'no value recorded'})
        return {'finding_id': 'F1', 'scope_key': 'project:P', 'status': status, 'signal': {'taxonomy': {'subtype': 'x'}, 'quantification': q, 'explanation': {'observed': 'o', 'expected': 'e'},
                                                                                                'priority': {'severity': 'low'}, 'confidence': {'evidence_strength': 'moderate'}}}

    def test_the_message_states_the_amount_with_its_label_and_that_a_person_decides(self):
        s, b = N.message(self.finding(), 'new')
        self.assertIn('1,234.56 (estimate)', b)
        self.assertIn('A signal is not a conclusion', b)
        self.assertTrue(s.startswith('F1 new'))

    def test_an_unquantified_finding_says_so_with_the_reason_not_zero(self):
        _, b = N.message(self.finding(quantified=False), 'new')
        self.assertIn('not quantified: no value recorded', b)
        self.assertNotIn('0.00', b)
