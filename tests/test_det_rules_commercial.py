import unittest
from . import _path                                         # noqa: F401
from .helpers_det import DetMini, bud, comp, det_world, inv, notice, po, quote, var


def bare():
    m = DetMini()
    m.projects(['PRJ-001', 'P1', '10000000', '2026-01-01', '2027-01-01'])
    m.contracts(['PRJ-001', '10000000', '0'])
    m.budgets(bud(cc='CC-01', cents='5000000'))
    return m


class TestR04Variation(unittest.TestCase):
    def world(self, *variations):
        m = det_world()
        m.variations(*variations)
        m.reconcile()
        return m

    def test_submitted_variation_open_longer_than_the_period_is_flagged_as_potential_revenue_not_entitlement(self):
        m = self.world(var('VAR-2', raised='2026-06-01', status='submitted', value='3500000'))
        (s,) = m.sigs(m.res(), 'R04')
        self.assertEqual((s['subject'], s['interpretation'], s['taxonomy']['subtype']), ('VAR-2', 'potential_revenue_at_risk', 'variation_unresolved'))
        self.assertEqual((s['quantification']['gross_cents'], s['quantification']['label']), (3500000, 'record'))
        self.assertIn('submission is not entitlement', ' '.join(s['quantification']['assumptions']))
        self.assertIn('not an entitlement', ' '.join(s['data_limits']))
        self.assertEqual(s['extra'], {'age_days': 121, 'status': 'submitted'})

    def test_sixty_days_is_not_beyond_sixty_and_sixty_one_is(self):
        m = self.world(var('VAR-2', raised='2026-08-01', status='submitted'))
        self.assertEqual(m.sigs(m.res(), 'R04'), [])
        m = self.world(var('VAR-2', raised='2026-07-31', status='submitted'))
        self.assertEqual(len(m.sigs(m.res(), 'R04')), 1)

    def test_an_approved_variation_is_silent_however_old(self):
        m = self.world(var('VAR-2', raised='2026-01-01', status='approved'))
        self.assertEqual(m.sigs(m.res(), 'R04'), [])

    def test_a_rejected_variation_is_not_flagged_as_open(self):
        m = self.world(var('VAR-2', raised='2026-01-01', status='rejected'))
        self.assertEqual(m.sigs(m.res(), 'R04'), [])

    def test_a_disputed_variation_is_treated_as_open(self):
        m = self.world(var('VAR-2', raised='2026-01-01', status='disputed'))
        self.assertEqual(len(m.sigs(m.res(), 'R04')), 1)

    def test_a_variation_without_a_value_is_flagged_but_never_given_an_amount(self):
        m = self.world(var('VAR-2', raised='2026-06-01', status='submitted', value=''))
        (s,) = m.sigs(m.res(), 'R04')
        self.assertEqual((s['taxonomy']['subtype'], s['quantification']['status']), ('variation_unpriced_unresolved', 'unquantified'))
        self.assertTrue(s['quantification']['reason'])

    def test_a_variation_raised_after_the_as_of_date_is_not_yet_open(self):
        m = self.world(var('VAR-2', raised='2026-10-20', status='submitted'))
        self.assertEqual(m.sigs(m.res(), 'R04'), [])

    def test_a_status_the_policy_does_not_map_is_listed_not_guessed(self):
        m = self.world(var('VAR-2', raised='2026-06-01', status='pending-ish'))
        r = m.res()
        self.assertEqual(m.sigs(r, 'R04'), [])
        self.assertTrue(any(n['subject'] == 'variation/VAR-2' for n in m.run(r, 'R04')['not_assessed']) or m.run(r, 'R04')['evaluated'] == 0)

    def test_without_the_status_map_the_rule_cannot_assess(self):
        m = self.world(var('VAR-2', raised='2026-06-01', status='submitted'))
        m.set_policy(variation_status_map=None)
        run = m.run(m.res(), 'R04')
        self.assertEqual(run['status'], 'cannot_assess')
        self.assertIn('CR-02 A12', ' '.join(run['notes']))

    def test_another_project_variation_is_not_read(self):
        m = det_world()
        m.projects(['PRJ-002', 'P2', '1', '2026-01-01', '2027-01-01'])
        m.variations(var('VAR-2', project='PRJ-002', raised='2026-01-01', status='submitted'))
        m.reconcile()
        self.assertEqual(m.sigs(m.res('PRJ-001'), 'R04'), [])

    def test_a_larger_period_is_a_policy_choice_not_a_constant(self):
        m = self.world(var('VAR-2', raised='2026-06-01', status='submitted'))
        m.rules(R04={'unresolved_days': 200})
        self.assertEqual(m.sigs(m.res(), 'R04'), [])


class TestR04B(unittest.TestCase):
    def world(self, *notices, variations=()):
        m = det_world()
        if variations:
            m.variations(*variations)
        m.notices(*notices)
        m.reconcile()
        return m

    def test_old_client_instruction_with_no_variation_is_flagged_without_an_amount(self):
        m = self.world(notice('N-1', date='2026-08-01'))
        (s,) = m.sigs(m.res(), 'R04B')
        self.assertEqual((s['taxonomy']['subtype'], s['interpretation'], s['quantification']['status']), ('instruction_without_variation', 'potential_revenue_at_risk', 'unquantified'))
        self.assertEqual(s['extra']['age_days'], 60)

    def test_age_thirty_is_flagged_and_twenty_nine_is_not(self):
        m = self.world(notice('N-1', date='2026-08-31'))
        self.assertEqual(len(m.sigs(m.res(), 'R04B')), 1)
        m = self.world(notice('N-1', date='2026-09-01'))
        self.assertEqual(m.sigs(m.res(), 'R04B'), [])

    def test_an_instruction_with_a_variation_in_the_store_is_silent(self):
        m = self.world(notice('N-1', date='2026-06-01', link='VAR-1'), variations=[var('VAR-1', status='submitted')])
        self.assertEqual(m.sigs(m.res(), 'R04B'), [])

    def test_a_link_to_a_variation_that_does_not_exist_is_a_data_quality_signal_not_revenue(self):
        m = self.world(notice('N-1', date='2026-06-01', link='VAR-NOPE'))
        (s,) = m.sigs(m.res(), 'R04B')
        self.assertEqual((s['taxonomy']['subtype'], s['interpretation']), ('instruction_link_unresolved', 'data_quality_risk'))

    def test_other_notice_types_are_not_instructions(self):
        m = self.world(notice('N-1', date='2026-06-01', typ='delay_notice'))
        self.assertEqual(m.sigs(m.res(), 'R04B'), [])

    def test_a_notice_after_the_as_of_date_is_not_tested(self):
        m = self.world(notice('N-1', date='2026-10-15'))
        self.assertEqual(m.sigs(m.res(), 'R04B'), [])

    def test_the_instruction_types_come_from_the_policy(self):
        m = self.world(notice('N-1', date='2026-06-01', typ='delay_notice'))
        m.rules(R04B={'min_age_days': 30, 'instruction_types': ['delay_notice']})
        self.assertEqual(len(m.sigs(m.res(), 'R04B')), 1)


class TestR05Retention(unittest.TestCase):
    def world(self, row):
        m = bare()
        m.retention(row)
        m.facility(['FAC-1', '50000000', '20000000', '800', '2026-09-30'])
        m.reconcile()
        return m

    def test_release_date_passed_with_no_release_and_no_reason_is_flagged_as_a_cash_timing_exposure(self):
        m = self.world(['PRJ-001', '500000', '2026-08-01', '', ''])
        (s,) = m.sigs(m.res(), 'R05')
        self.assertEqual((s['interpretation'], s['quantification']['gross_cents'], s['quantification']['label']), ('cash_timing_exposure', 500000, 'figure'))
        self.assertEqual(s['extra']['days_late'], 60)
        self.assertIn('not a loss', ' '.join(s['data_limits']))
        self.assertEqual(s['priority']['severity'], 'low')

    def test_a_recorded_hold_reason_makes_it_silent(self):
        m = self.world(['PRJ-001', '500000', '2026-08-01', '', 'defects period'])
        self.assertEqual(m.sigs(m.res(), 'R05'), [])

    def test_a_release_date_in_the_future_is_silent(self):
        m = self.world(['PRJ-001', '500000', '2027-02-01', '', ''])
        self.assertEqual(m.sigs(m.res(), 'R05'), [])

    def test_a_recorded_release_is_silent(self):
        m = self.world(['PRJ-001', '500000', '2026-08-01', '2026-08-20', ''])
        self.assertEqual(m.sigs(m.res(), 'R05'), [])

    def test_no_retention_ledger_is_not_assessed_and_not_called_clean(self):
        m = bare()
        m.reconcile()
        r = m.res()
        self.assertEqual(m.sigs(r, 'R05'), [])
        self.assertTrue(m.run(r, 'R05')['not_assessed'])

    def test_a_grace_period_in_the_policy_delays_the_flag(self):
        m = self.world(['PRJ-001', '500000', '2026-08-01', '', ''])
        m.rules(R05={'grace_days': 61})
        self.assertEqual(m.sigs(m.res(), 'R05'), [])
        m.rules(R05={'grace_days': 60})
        self.assertEqual(m.sigs(m.res(), 'R05'), [])                             # 60 days late is not beyond 60
        m.rules(R05={'grace_days': 59})
        self.assertEqual(len(m.sigs(m.res(), 'R05')), 1)


class TestR06Compliance(unittest.TestCase):
    def world(self, *rows):
        m = det_world()
        m.compliance(*rows)
        m.reconcile()
        return m

    def test_expired_evidence_is_flagged_at_tenant_scope_with_no_amount(self):
        m = self.world(comp('SUP-001', 'insurance', '2026-09-01'))
        r = m.tres()
        (s,) = m.sigs(r, 'R06')
        self.assertEqual((s['scope']['level'], s['taxonomy']['subtype'], s['interpretation'], s['quantification']['status']), ('tenant', 'compliance_expired', 'compliance_risk', 'unquantified'))
        self.assertEqual(s['extra']['days_to_expiry'], -29)
        self.assertEqual(m.sigs(m.res(), 'R06'), [])                              # a project run does not run tenant rules

    def test_expiring_inside_the_warning_period_is_flagged_as_expiring(self):
        m = self.world(comp('SUP-001', 'licence', '2026-10-20'))
        (s,) = m.sigs(m.tres(), 'R06')
        self.assertEqual((s['taxonomy']['subtype'], s['extra']['days_to_expiry']), ('compliance_expiring', 20))

    def test_thirty_days_left_is_flagged_and_thirty_one_is_silent(self):
        m = self.world(comp('SUP-001', 'licence', '2026-10-30'))
        self.assertEqual(len(m.sigs(m.tres(), 'R06')), 1)
        m = self.world(comp('SUP-001', 'licence', '2026-10-31'))
        self.assertEqual(m.sigs(m.tres(), 'R06'), [])

    def test_expiring_today_is_expiring_not_expired(self):
        m = self.world(comp('SUP-001', 'licence', '2026-09-30'))
        (s,) = m.sigs(m.tres(), 'R06')
        self.assertEqual(s['taxonomy']['subtype'], 'compliance_expiring')
        m = self.world(comp('SUP-001', 'licence', '2026-09-29'))
        (s,) = m.sigs(m.tres(), 'R06')
        self.assertEqual(s['taxonomy']['subtype'], 'compliance_expired')

    def test_current_evidence_for_all_suppliers_is_silent_and_counted(self):
        m = self.world(comp('SUP-001', 'insurance', '2027-12-31'), comp('SUP-002', 'licence', '2028-01-31'))
        r = m.tres()
        self.assertEqual(m.sigs(r, 'R06'), [])
        self.assertEqual(m.run(r, 'R06')['silent'], 2)

    def test_the_warning_period_is_configured_not_built_in(self):
        m = self.world(comp('SUP-001', 'licence', '2026-12-01'))
        self.assertEqual(m.sigs(m.tres(), 'R06'), [])
        m.rules(R06={'warning_days': 90})
        self.assertEqual(len(m.sigs(m.tres(), 'R06')), 1)

    def test_the_statement_that_a_missing_certificate_record_is_not_tested_is_carried(self):
        m = self.world(comp('SUP-001', 'insurance', '2026-09-01'))
        (s,) = m.sigs(m.tres(), 'R06')
        self.assertIn('absence of a certificate record', ' '.join(s['data_limits']))


class TestR07QuoteVsReference(unittest.TestCase):
    PAIR = {'quote': 'Q-1', 'reference_kind': 'quote', 'reference': 'Q-2'}

    def world(self, *quotes, pairs=None, pos=()):
        m = det_world()
        if pos:
            m.pos(*pos)
        m.quotes(*quotes)
        m.reconcile()
        m.rules(R07={'tolerance_bps': 100, 'pairs': pairs or [self.PAIR]})
        return m

    def test_a_declared_pair_with_a_quote_above_the_reference_is_flagged_per_unit_only(self):
        m = self.world(quote('Q-1', rate='110000'), quote('Q-2', supplier='SUP-002', rate='100000'))
        (s,) = m.sigs(m.tres(), 'R07')
        self.assertEqual((s['subject'], s['scope']['level'], s['interpretation'], s['quantification']['status']), ('Q-1>quote:Q-2', 'tenant', 'forecast_exposure', 'unquantified'))
        self.assertEqual((s['extra']['unit_difference_cents'], s['extra']['over_bps']), (10000, 1000))
        self.assertIn('quantity', s['quantification']['reason'])
        self.assertIn('comparability gate is M6', ' '.join(s['confidence']['missing_information']))

    def test_exactly_at_the_tolerance_is_silent_and_a_little_over_is_flagged(self):
        m = self.world(quote('Q-1', rate='101000'), quote('Q-2', supplier='SUP-002', rate='100000'))
        self.assertEqual(m.sigs(m.tres(), 'R07'), [])
        m = self.world(quote('Q-1', rate='101001'), quote('Q-2', supplier='SUP-002', rate='100000'))
        self.assertEqual(len(m.sigs(m.tres(), 'R07')), 1)

    def test_a_cheaper_quote_is_silent(self):
        m = self.world(quote('Q-1', rate='90000'), quote('Q-2', supplier='SUP-002', rate='100000'))
        self.assertEqual(m.sigs(m.tres(), 'R07'), [])

    def test_ex_works_is_compared_after_adding_freight(self):
        m = self.world(quote('Q-1', rate='95000', basis='ex-works', freight='10000'), quote('Q-2', supplier='SUP-002', rate='100000'))
        (s,) = m.sigs(m.tres(), 'R07')
        self.assertEqual(s['extra']['unit_difference_cents'], 5000)
        m = self.world(quote('Q-1', rate='95000', basis='ex-works', freight='4000'), quote('Q-2', supplier='SUP-002', rate='100000'))
        self.assertEqual(m.sigs(m.tres(), 'R07'), [])

    def test_a_foreign_currency_quote_is_not_converted_here_and_is_listed(self):
        m = self.world(quote('Q-1', rate='110000', cur='USD', fx='1.5', fxd='2026-09-01'), quote('Q-2', supplier='SUP-002', rate='100000'))
        r = m.tres()
        self.assertEqual(m.sigs(r, 'R07'), [])
        self.assertIn('M6', ' '.join(n['why'] for n in m.run(r, 'R07')['not_assessed']))

    def test_different_materials_in_a_declared_pair_are_not_compared(self):
        m = self.world(quote('Q-1', material='MAT-X', rate='110000'), quote('Q-2', supplier='SUP-002', material='MAT-Y', rate='100000'))
        r = m.tres()
        self.assertEqual(m.sigs(r, 'R07'), [])
        self.assertIn('different materials', m.run(r, 'R07')['not_assessed'][0]['why'])

    def test_a_pair_naming_a_quote_that_is_not_there_is_listed_as_not_assessed(self):
        m = self.world(quote('Q-1', rate='110000'))
        r = m.tres()
        self.assertEqual(m.sigs(r, 'R07'), [])
        self.assertEqual(len(m.run(r, 'R07')['not_assessed']), 1)

    def test_a_purchase_order_rate_can_be_the_reference(self):
        pair = {'quote': 'Q-1', 'reference_kind': 'purchase_order', 'reference': 'PO-9'}
        m = self.world(quote('Q-1', rate='110000'), pairs=[pair], pos=[po('PO-9', amount='100000')])
        (s,) = m.sigs(m.tres(), 'R07')
        self.assertEqual(s['extra']['unit_difference_cents'], 10000)
        self.assertEqual(sorted(e['ref'] for e in s['evidence']), ['purchase_order/PO-9', 'supplier_quote/Q-1'])

    def test_no_pairs_declared_means_the_rule_is_not_configured_never_that_all_quotes_are_fine(self):
        m = self.world(quote('Q-1', rate='110000'), quote('Q-2', supplier='SUP-002', rate='100000'))
        m.rules(R07=None)
        run = m.run(m.tres(), 'R07')
        self.assertEqual((run['status'], run['missing_parameters']), ('not_configured', ['tolerance_bps', 'pairs']))

    def test_a_signal_is_independent_of_the_project_run(self):
        m = self.world(quote('Q-1', rate='110000'), quote('Q-2', supplier='SUP-002', rate='100000'))
        self.assertNotIn('R07', m.res()['rule_runs'])
