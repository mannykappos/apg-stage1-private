"""Edge cases of the commercial, cash and supplier rules found by the mutation pass: records that are held but not in conflict, the as-of day itself, quote validity, the exact words
of a 'not assessed' reason and the wording of the observation.  Every value is synthetic."""
import copy
import unittest
from . import _path                                         # noqa: F401
from .helpers_det import det_world, notice, po, quote, var
from .test_det_rules_commercial import bare
from apg.det import demo_det as DD


def with_unusable_copy(m, kind, key, outcome='held', pending=('MANUAL_HOLD',)):
    """Store a later revision of a record that is held by its intrinsic outcome and is not a same-key conflict."""
    rec = m.s.get(kind, key)
    p = copy.deepcopy(rec.payload)
    p['intrinsic']['outcome'] = outcome
    p['intrinsic']['pending'] = list(pending)
    m.s.put(kind, key, p, expected_revision=rec.revision)


class TestHeldButNotInConflict(unittest.TestCase):
    def test_a_future_dated_variation_is_listed_with_its_reason_and_not_assessed(self):
        m = det_world()
        m.variations(var('VAR-3', raised='2099-01-01', status='submitted'))
        m.reconcile()
        r = m.res()
        self.assertEqual(m.sigs(r, 'R04'), [])
        self.assertEqual(m.run(r, 'R04')['not_assessed'], [{'subject': 'variation/VAR-3', 'why': 'FUTURE_DATED:raised_date'}])

    def test_a_future_dated_notice_is_listed_with_its_reason_and_not_assessed(self):
        m = det_world()
        m.notices(notice('N-1', date='2099-01-01'))
        m.reconcile()
        r = m.res()
        self.assertEqual(m.sigs(r, 'R04B'), [])
        self.assertEqual(m.run(r, 'R04B')['not_assessed'], [{'subject': 'notice/N-1', 'why': 'FUTURE_DATED:notice_date'}])

    def test_compliance_evidence_held_for_any_reason_is_listed_not_read(self):
        m = det_world()
        m.compliance(['SUP-001', 'insurance', '2026-09-01'])
        m.reconcile()
        with_unusable_copy(m, 'compliance', 'SUP-001|insurance')
        r = m.tres()
        self.assertEqual(m.sigs(r, 'R06'), [])
        self.assertEqual(m.run(r, 'R06')['not_assessed'], [{'subject': 'compliance/SUP-001|insurance', 'why': 'MANUAL_HOLD'}])


class TestAsOfDayAndAge(unittest.TestCase):
    def test_a_notice_dated_on_the_as_of_day_is_tested_and_flagged_when_the_minimum_age_is_zero(self):
        m = det_world()
        r04b = copy.deepcopy(DD.demo_det_policy()['rules']['R04B'])
        r04b['min_age_days'] = 0
        m.rules(R04B=r04b)
        m.notices(notice('N-1', date='2026-09-30'), notice('N-2', date='2026-10-01'))
        m.reconcile()
        r = m.res()
        (s,) = m.sigs(r, 'R04B')
        self.assertEqual((s['subject'], s['extra']['age_days']), ('N-1', 0))

    def test_the_observation_names_the_description_or_says_there_is_none(self):
        m = det_world()
        m.variations(var('VAR-1', raised='2026-03-01', status='submitted', desc='extra piling'), var('VAR-2', raised='2026-03-01', status='submitted', desc='', value='2500000'))
        m.notices(notice('N-1', date='2026-06-01', desc='move wall'), notice('N-2', date='2026-06-01', desc=''))
        m.reconcile()
        r = m.res()
        obs = {s['subject']: s['explanation']['observed'] for s in m.sigs(r, 'R04') + m.sigs(r, 'R04B')}
        self.assertTrue(obs['VAR-1'].startswith('variation VAR-1 (extra piling) was raised'))
        self.assertTrue(obs['VAR-2'].startswith('variation VAR-2 (no description) was raised'))
        self.assertTrue(obs['N-1'].startswith('notice N-1 (move wall) has no variation'))
        self.assertTrue(obs['N-2'].startswith('notice N-2 (no description) has no variation'))

    def test_the_observation_says_a_value_is_missing_or_gives_the_submitted_value(self):
        m = det_world()
        m.variations(var('VAR-1', raised='2026-03-01', status='submitted', value='3500000'), var('VAR-2', raised='2026-03-01', status='submitted', value=''))
        m.reconcile()
        obs = {s['subject']: s['explanation']['observed'] for s in m.sigs(m.res(), 'R04')}
        self.assertTrue(obs['VAR-1'].endswith('submitted value 35,000.00'), obs['VAR-1'])
        self.assertTrue(obs['VAR-2'].endswith('no value is recorded'), obs['VAR-2'])


class TestRetentionAndSupplierWording(unittest.TestCase):
    def test_no_retention_ledger_gives_the_plain_reason(self):
        m = bare()
        m.reconcile()
        self.assertEqual(m.run(m.res(), 'R05')['not_assessed'], [{'subject': 'retention/PRJ-001', 'why': 'no retention ledger'}])

    def test_the_observation_names_the_supplier_by_name_when_it_is_stored_and_by_id_when_it_is_not(self):
        m = det_world()
        m.compliance(['SUP-001', 'insurance', '2026-10-05'], ['SUP-777', 'insurance', '2026-10-05'])
        m.reconcile()
        obs = {s['extra']['supplier']: s['explanation']['observed'] for s in m.sigs(m.tres(), 'R06')}
        self.assertEqual(obs['SUP-001'], 'Alpha Concrete Pty Ltd (SUP-001) insurance expires on 2026-10-05, in 5 days')
        self.assertEqual(obs['SUP-777'], 'SUP-777 (SUP-777) insurance expires on 2026-10-05, in 5 days')


class TestQuotePairEdges(unittest.TestCase):
    PAIR = {'quote': 'Q-1', 'reference_kind': 'quote', 'reference': 'Q-2'}

    def world(self, *quotes, reconcile=True, pos=(), pairs=None):
        m = det_world()
        if pos:
            m.pos(*pos)
        m.quotes(*quotes)
        if reconcile:
            m.reconcile()
        m.rules(R07={'tolerance_bps': 100, 'pairs': pairs or [self.PAIR]})
        return m

    def test_a_quote_valid_until_the_as_of_day_is_current_and_one_valid_until_the_day_before_is_expired(self):
        m = self.world(quote('Q-1', rate='110000', valid='2026-09-30'), quote('Q-2', supplier='SUP-002', rate='100000'))
        (s,) = m.sigs(m.tres(), 'R07')
        self.assertEqual(s['confidence']['evidence_strength'], 'moderate')
        self.assertFalse([x for x in s['data_limits'] if x.startswith('EXPIRED')])
        m = self.world(quote('Q-1', rate='110000', valid='2026-09-29'), quote('Q-2', supplier='SUP-002', rate='100000'))
        (s,) = m.sigs(m.tres(), 'R07')
        self.assertEqual(s['confidence']['evidence_strength'], 'weak')
        self.assertIn('EXPIRED:quote', s['data_limits'])

    def test_an_expired_reference_is_named_as_the_reference(self):
        m = self.world(quote('Q-1', rate='110000'), quote('Q-2', supplier='SUP-002', rate='100000', valid='2026-09-29'))
        (s,) = m.sigs(m.tres(), 'R07')
        self.assertIn('EXPIRED:reference', s['data_limits'])

    def test_a_quote_that_was_never_reconciled_is_not_used_and_the_reason_says_so(self):
        m = self.world(quote('Q-1', rate='110000'), quote('Q-2', supplier='SUP-002', rate='100000'), reconcile=False)
        r = m.tres()
        self.assertEqual(m.sigs(r, 'R07'), [])
        self.assertEqual(m.run(r, 'R07')['not_assessed'], [{'subject': 'Q-1>quote:Q-2', 'why': 'supplier_quote/Q-1 is not usable (held, disputed or duplicate)'}])

    def test_a_reference_that_is_not_in_the_store_gives_its_own_reason(self):
        m = self.world(quote('Q-1', rate='110000'))
        self.assertEqual(m.run(m.tres(), 'R07')['not_assessed'], [{'subject': 'Q-1>quote:Q-2', 'why': 'record not in the store: supplier_quote/Q-2'}])

    def test_a_reference_order_that_was_never_reconciled_is_not_used(self):
        pair = {'quote': 'Q-1', 'reference_kind': 'purchase_order', 'reference': 'PO-1'}
        m = det_world()
        m.pos(po('PO-1', amount='1000000'))
        m.quotes(quote('Q-1', rate='110000'))
        m.reconcile()
        m.rules(R07={'tolerance_bps': 100, 'pairs': [pair]})
        rec = m.s.get('recon_state', 'purchase_order/PO-1')
        p = copy.deepcopy(rec.payload)
        p['lifecycle'] = 'duplicate_of'
        m.s.put('recon_state', 'purchase_order/PO-1', p, expected_revision=rec.revision)
        r = m.tres()
        self.assertEqual(m.sigs(r, 'R07'), [])
        self.assertEqual(m.run(r, 'R07')['not_assessed'], [{'subject': 'Q-1>purchase_order:PO-1', 'why': 'purchase_order/PO-1 is not usable (held, disputed or duplicate)'}])

    def test_a_quote_whose_reconciliation_outcome_is_not_an_accepted_one_is_not_used(self):
        m = self.world(quote('Q-1', rate='110000'), quote('Q-2', supplier='SUP-002', rate='100000'))
        rec = m.s.get('recon_state', 'supplier_quote/Q-1')
        p = copy.deepcopy(rec.payload)
        p['effective_outcome'] = 'pending_reconciliation'
        m.s.put('recon_state', 'supplier_quote/Q-1', p, expected_revision=rec.revision)
        r = m.tres()
        self.assertEqual(m.sigs(r, 'R07'), [])
        self.assertEqual(len(m.run(r, 'R07')['not_assessed']), 1)


if __name__ == '__main__':
    unittest.main()
