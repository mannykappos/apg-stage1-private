import unittest
from . import _path                                         # noqa: F401
from .helpers_det import AMD_H, DetMini, det_world, inv, bud, ctc, po, var
from .helpers_ingest import csvb


def amd(aid='AMD-1', po_id='PO-1', date='2026-08-01', delta='100000', change='', reason='extra'):
    return [aid, po_id, date, delta, change, reason]


class TestR01Budget(unittest.TestCase):
    def world(self, *invoices, **kw):
        m = det_world(**kw)
        if invoices:
            m.invoices(*invoices)
        m.reconcile()
        return m

    def test_cost_above_tolerance_raises_one_finding_with_evidence_and_parameters(self):
        m = self.world(inv('INV-1', ex='5300000', cc='CC-01'))
        r = m.res()
        (s,) = m.sigs(r, 'R01')
        self.assertEqual((s['subject'], s['taxonomy']['subtype'], s['interpretation']), ('CC-01', 'actual_cost_over_budget', 'forecast_exposure'))
        self.assertEqual((s['rule']['id'], s['rule']['version'], s['rule']['params']), ('DET-R01', 1, {'tolerance_bps': 500}))
        q = s['quantification']
        self.assertEqual((q['status'], q['gross_cents'], q['label']), ('quantified', 300000, 'estimate'))
        refs = [e['ref'] for e in s['evidence']]
        self.assertIn('ap_invoice/INV-1', refs)
        self.assertTrue(any(x.startswith('budget_line/') for x in refs))
        self.assertTrue(all(e['revision'] >= 1 for e in s['evidence']))
        self.assertEqual(s['explanation']['observed'][:20], 'actual cost to 2026-')
        self.assertIn('supplier invoices only', ' '.join(s['data_limits']))
        self.assertEqual(s['priority']['severity'], 'low')

    def test_exactly_at_the_tolerance_is_silent_and_one_cent_over_is_not(self):
        m = self.world(inv('INV-1', ex='5250000', cc='CC-01'))
        self.assertEqual(m.sigs(m.res(), 'R01'), [])
        m2 = self.world(inv('INV-1', ex='5250001', cc='CC-01'))
        self.assertEqual(len(m2.sigs(m2.res(), 'R01')), 1)                       # exact comparison: 500.0002 bps does exceed 500

    def test_under_budget_is_silent_and_the_run_counts_it(self):
        m = self.world(inv('INV-1', ex='4900000', cc='CC-01'))
        r = m.res()
        self.assertEqual(m.sigs(r, 'R01'), [])
        run = m.run(r, 'R01')
        self.assertEqual((run['status'], run['evaluated'], run['silent'], run['signals']), ('evaluated', 2, 2, 0))

    def test_a_credit_note_reduces_the_cost_before_the_test(self):
        m = det_world()
        m.invoices(inv('INV-1', ex='6000000', cc='CC-01'))
        m.credits(['CRN-1', 'SUP-001', 'INV-1', '2026-07-25', '1000000', '100000'])
        m.reconcile()
        self.assertEqual(m.sigs(m.res(), 'R01'), [])

    def test_cost_on_another_project_is_not_counted(self):
        m = det_world()
        m.projects(['PRJ-002', 'P2', '1', '2026-01-01', '2027-01-01'])
        m.invoices(inv('INV-1', ex='9000000', cc='CC-01', project='PRJ-002'))
        m.reconcile()
        self.assertEqual(m.sigs(m.res('PRJ-001'), 'R01'), [])

    def test_zero_tolerance_flags_any_overrun(self):
        m = self.world(inv('INV-1', ex='5000001', cc='CC-01'))
        m.rules(R01={'tolerance_bps': 0})
        self.assertEqual(len(m.sigs(m.res(), 'R01')), 1)

    def test_a_non_positive_budget_is_not_assessed_not_divided_by(self):
        m = det_world()
        m.budgets(bud(cc='CC-09', cents='0'))
        m.invoices(inv('INV-1', ex='100', cc='CC-09'))
        m.reconcile()
        run = m.run(m.res(), 'R01')
        self.assertIn({'subject': 'CC-09', 'why': 'BUDGET_NOT_POSITIVE'}, run['not_assessed'])

    def test_a_held_invoice_makes_the_finding_moderate_and_says_the_figure_is_provisional(self):
        m = det_world()
        m.invoices(inv('INV-1', ex='5300000', cc='CC-01'), inv('INV-2', sin='SI-2', ex='100000', cc='CC-02'), inv('INV-3', sin='SI-2', ex='200000', cc='CC-02'))
        m.reconcile()
        (s,) = m.sigs(m.res(), 'R01')
        self.assertEqual(s['confidence']['evidence_strength'], 'moderate')
        self.assertIn('ACTUAL_COST_FIGURE_PROVISIONAL', s['data_limits'])

    def test_unconfigured_rule_says_so_and_names_the_missing_parameter(self):
        m = self.world(inv('INV-1', ex='9900000', cc='CC-01'))
        m.rules(R01=None)
        r = m.res()
        run = m.run(r, 'R01')
        self.assertEqual((run['status'], run['missing_parameters']), ('not_configured', ['tolerance_bps']))
        self.assertEqual(m.sigs(r, 'R01'), [])
        self.assertEqual(r['counts']['rules_not_run'], 1)

    def test_a_switched_off_rule_is_recorded_as_switched_off(self):
        m = self.world(inv('INV-1', ex='9900000', cc='CC-01'))
        m.rules(R01={'enabled': False})
        run = m.run(m.res(), 'R01')
        self.assertEqual((run['status'], run['notes']), ('disabled', ['SWITCHED_OFF_IN_POLICY']))

    def test_a_cost_scope_that_is_not_configured_makes_the_rule_unassessable_not_silent(self):
        m = self.world(inv('INV-1', ex='9900000', cc='CC-01'))
        m.set_policy(cost_scope=None)
        r = m.res()
        run = m.run(r, 'R01')
        self.assertEqual(run['status'], 'cannot_assess')
        self.assertIn('COST_SCOPE_NOT_CONFIGURED', run['notes'])

    def test_unapproved_policy_is_visible_on_the_result(self):
        m = det_world(approved=False)
        m.invoices(inv('INV-1', ex='5300000', cc='CC-01'))
        m.reconcile()
        r = m.res()
        self.assertEqual(r['det_policy']['approved'], False)
        self.assertEqual(len(m.sigs(r, 'R01')), 1)


class TestR02Amendment(unittest.TestCase):
    def world(self, amendment, variations=()):
        m = det_world()
        m.pos(po('PO-1', amount='1000000'))
        if variations:
            m.variations(*variations)
        m.amendments(amendment)
        m.reconcile()
        return m

    def test_amendment_with_no_change_reference_is_flagged_as_exposure(self):
        m = self.world(amd())
        (s,) = m.sigs(m.res(), 'R02')
        self.assertEqual((s['subject'], s['interpretation'], s['quantification']['gross_cents'], s['quantification']['label']), ('AMD-1', 'forecast_exposure', 100000, 'record'))
        self.assertEqual(s['extra'], {'purchase_order': 'PO-1', 'why': 'NO_APPROVED_CHANGE_REFERENCE'})
        self.assertEqual(sorted(e['ref'] for e in s['evidence']), ['po_amendment/AMD-1', 'purchase_order/PO-1'])

    def test_amendment_linked_to_an_approved_variation_is_silent(self):
        m = self.world(amd(change='VAR-1'), [var('VAR-1', status='approved')])
        r = m.res()
        self.assertEqual(m.sigs(r, 'R02'), [])
        self.assertEqual(m.run(r, 'R02')['silent'], 1)

    def test_amendment_linked_to_a_variation_that_is_only_submitted_is_flagged(self):
        m = self.world(amd(change='VAR-1'), [var('VAR-1', status='submitted')])
        (s,) = m.sigs(m.res(), 'R02')
        self.assertIn('CHANGE_NOT_APPROVED', s['extra']['why'])
        self.assertIn('variation/VAR-1', [e['ref'] for e in s['evidence']])

    def test_amendment_naming_a_variation_that_does_not_exist_is_flagged(self):
        m = self.world(amd(change='VAR-NOPE'))
        (s,) = m.sigs(m.res(), 'R02')
        self.assertEqual(s['extra']['why'], 'CHANGE_NOT_APPROVED:VAR-NOPE')

    def test_a_status_map_that_is_not_configured_leaves_linked_amendments_not_assessed_but_still_flags_blank_ones(self):
        m = self.world(amd(change='VAR-1'), [var('VAR-1', status='approved')])
        m.set_policy(variation_status_map=None)
        run = m.run(m.res(), 'R02')
        self.assertEqual(run['signals'], 0)
        self.assertEqual(len(run['not_assessed']), 1)
        m2 = self.world(amd())
        m2.set_policy(variation_status_map=None)
        self.assertEqual(len(m2.sigs(m2.res(), 'R02')), 1)

    def test_po_status_map_missing_means_cannot_assess(self):
        m = self.world(amd())
        m.set_policy(po_status_map=None)
        self.assertEqual(m.run(m.res(), 'R02')['status'], 'cannot_assess')

    def test_amendment_dated_after_the_as_of_date_is_not_flagged_yet(self):
        m = self.world(amd(date='2026-10-05'))
        self.assertEqual(m.sigs(m.res(), 'R02'), [])


class TestR03InvoiceVsOrder(unittest.TestCase):
    def world(self, *invoices, amendments=(), po_amount='1000000'):
        m = det_world()
        m.pos(po('PO-1', amount=po_amount))
        if amendments:
            m.amendments(*amendments)
        m.invoices(*invoices)
        m.reconcile()
        return m

    def test_invoiced_above_the_order_beyond_tolerance_is_flagged(self):
        m = self.world(inv('INV-1', po='PO-1', ex='1076000'))
        (s,) = m.sigs(m.res(), 'R03')
        self.assertEqual((s['subject'], s['quantification']['gross_cents'], s['extra']['over_bps']), ('PO-1', 76000, 760))
        self.assertIn('AMOUNT_COMPARISON_ONLY (finding F-09)', s['data_limits'])
        self.assertEqual(sorted(e['ref'] for e in s['evidence']), ['ap_invoice/INV-1', 'purchase_order/PO-1'])

    def test_exactly_at_tolerance_is_silent_and_one_cent_more_is_flagged(self):
        m = self.world(inv('INV-1', po='PO-1', ex='1010000'))
        self.assertEqual(m.sigs(m.res(), 'R03'), [])
        m = self.world(inv('INV-1', po='PO-1', ex='1010001'))
        self.assertEqual(len(m.sigs(m.res(), 'R03')), 1)

    def test_half_invoiced_order_is_silent(self):
        m = self.world(inv('INV-1', po='PO-1', ex='500000'))
        self.assertEqual(m.sigs(m.res(), 'R03'), [])

    def test_two_invoices_are_added_before_the_test(self):
        m = self.world(inv('INV-1', po='PO-1', ex='600000'), inv('INV-2', sin='SI-2', po='PO-1', ex='500000'))
        (s,) = m.sigs(m.res(), 'R03')
        self.assertEqual(s['quantification']['gross_cents'], 100000)

    def test_an_approved_amendment_raises_the_commitment_an_unapproved_one_does_not(self):
        m = self.world(inv('INV-1', po='PO-1', ex='1100000'), amendments=[amd(change='VAR-1', delta='100000')])
        m.variations(var('VAR-1', status='approved'))
        m.reconcile()
        self.assertEqual(m.sigs(m.res(), 'R03'), [])
        m2 = self.world(inv('INV-1', po='PO-1', ex='1100000'), amendments=[amd(delta='100000')])
        self.assertEqual(len(m2.sigs(m2.res(), 'R03')), 1)

    def test_a_held_invoice_is_listed_as_not_assessed_and_lowers_the_evidence_strength(self):
        m = self.world(inv('INV-1', po='PO-1', ex='1100000'), inv('INV-2', sin='SI-2', po='PO-1', ex='10'), inv('INV-3', sin='SI-2', po='PO-1', ex='20'))
        r = m.res()
        (s,) = m.sigs(r, 'R03')
        self.assertEqual(s['confidence']['evidence_strength'], 'moderate')
        self.assertTrue(m.run(r, 'R03')['not_assessed'])

    def test_unconfigured_tolerance_does_not_run(self):
        m = self.world(inv('INV-1', po='PO-1', ex='2000000'))
        m.rules(R03=None)
        self.assertEqual(m.run(m.res(), 'R03')['status'], 'not_configured')


class TestR09ForecastMovement(unittest.TestCase):
    def world(self, *lines):
        m = det_world()
        m.ctcs(*lines)
        m.reconcile()
        return m

    def test_unexplained_increase_is_flagged_with_both_lines_as_evidence(self):
        m = self.world(ctc(cc='CC-03', version='F-8', date='2026-08-31', cents='5000000', reason='initial'), ctc(cc='CC-03', version='F-9', date='2026-09-30', cents='36000000', reason=''))
        (s,) = m.sigs(m.res(), 'R09')
        self.assertEqual((s['subject'], s['interpretation'], s['quantification']['gross_cents'], s['quantification']['label']), ('CC-03|F-8>F-9', 'forecast_exposure', 31000000, 'record'))
        self.assertEqual(s['priority']['severity'], 'high')
        self.assertEqual(len(s['evidence']), 2)
        self.assertIn('movement bridge', ' '.join(s['data_limits']))

    def test_a_recorded_reason_makes_it_silent(self):
        m = self.world(ctc(cc='CC-03', version='F-8', date='2026-08-31', cents='5000000'), ctc(cc='CC-03', version='F-9', date='2026-09-30', cents='36000000', reason='scope added'))
        self.assertEqual(m.sigs(m.res(), 'R09'), [])

    def test_movement_just_below_the_threshold_is_silent_and_exactly_at_it_is_flagged(self):
        m = self.world(ctc(cc='CC-03', version='F-8', date='2026-08-31', cents='1000000'), ctc(cc='CC-03', version='F-9', date='2026-09-30', cents='5999999', reason=''))
        self.assertEqual(m.sigs(m.res(), 'R09'), [])
        m = self.world(ctc(cc='CC-03', version='F-8', date='2026-08-31', cents='1000000'), ctc(cc='CC-03', version='F-9', date='2026-09-30', cents='6000000', reason=''))
        self.assertEqual(len(m.sigs(m.res(), 'R09')), 1)

    def test_an_unexplained_reduction_is_a_data_quality_signal_and_not_a_loss(self):
        m = self.world(ctc(cc='CC-03', version='F-8', date='2026-08-31', cents='9000000'), ctc(cc='CC-03', version='F-9', date='2026-09-30', cents='1000000', reason=''))
        (s,) = m.sigs(m.res(), 'R09')
        self.assertEqual((s['interpretation'], s['quantification']['status']), ('data_quality_risk', 'unquantified'))
        self.assertEqual(s['extra']['direction'], 'decrease')

    def test_a_single_forecast_has_nothing_to_compare(self):
        m = self.world(ctc(cc='CC-03', version='F-9', date='2026-09-30', cents='36000000', reason=''))
        r = m.res()
        self.assertEqual((m.sigs(r, 'R09'), m.run(r, 'R09')['evaluated']), ([], 0))

    def test_a_forecast_dated_after_the_as_of_date_is_not_compared(self):
        m = self.world(ctc(cc='CC-03', version='F-8', date='2026-08-31', cents='1000000'), ctc(cc='CC-03', version='F-9', date='2026-10-31', cents='90000000', reason=''))
        self.assertEqual(m.sigs(m.res(), 'R09'), [])

    def test_three_versions_are_compared_pairwise_in_date_order(self):
        m = self.world(ctc(cc='CC-03', version='F-7', date='2026-07-31', cents='1000000'), ctc(cc='CC-03', version='F-8', date='2026-08-31', cents='9000000', reason=''), ctc(cc='CC-03', version='F-9', date='2026-09-30', cents='20000000', reason=''))
        subs = sorted(s['subject'] for s in m.sigs(m.res(), 'R09'))
        self.assertEqual(subs, ['CC-03|F-7>F-8', 'CC-03|F-8>F-9'])

    def test_other_cost_codes_are_not_compared_with_each_other(self):
        m = self.world(ctc(cc='CC-03', version='F-8', date='2026-08-31', cents='1000000'), ctc(cc='CC-04', version='F-9', date='2026-09-30', cents='90000000', reason=''))
        self.assertEqual(m.sigs(m.res(), 'R09'), [])

    def test_unconfigured_movement_size_does_not_run(self):
        m = self.world(ctc(cc='CC-03', version='F-8', date='2026-08-31', cents='1000000'), ctc(cc='CC-03', version='F-9', date='2026-09-30', cents='99000000', reason=''))
        m.rules(R09=None)
        self.assertEqual(m.run(m.res(), 'R09')['missing_parameters'], ['movement_abs_cents'])


class TestAggregation(unittest.TestCase):
    def world(self, *orders):
        m = det_world()
        m.pos(*orders)
        m.reconcile()
        return m

    def three(self, d1='2026-08-03', d2='2026-08-09', d3='2026-08-14', amount='900000000', sup='SUP-001', cc='CC-01'):
        return [po('PO-1', supplier=sup, cc=cc, date=d1, amount='9282000'), po('PO-2', supplier=sup, cc=cc, date=d2, amount='9044000'), po('PO-3', supplier=sup, cc=cc, date=d3, amount='8806000')]

    def test_three_orders_inside_the_window_that_reach_the_threshold_together_are_flagged_once(self):
        m = self.world(*self.three())
        (s,) = m.sigs(m.res(), 'AGG')
        self.assertEqual(s['extra']['orders'], ['PO-1', 'PO-2', 'PO-3'])
        self.assertEqual((s['extra']['aggregate_cents'], s['interpretation'], s['quantification']['status']), (27132000, 'compliance_risk', 'unquantified'))
        self.assertTrue(s['hypotheses'])
        self.assertIn('OQ-A1-7', ' '.join(s['data_limits']))

    def test_sixty_days_apart_is_not_aggregated(self):
        m = self.world(*self.three('2026-03-02', '2026-05-04', '2026-07-06'))
        self.assertEqual(m.sigs(m.res(), 'AGG'), [])

    def test_window_edge_is_inclusive_at_thirty_days_and_not_at_thirty_one(self):
        m = self.world(po('PO-1', date='2026-07-01', amount='13000000'), po('PO-2', date='2026-07-31', amount='13000000'))
        self.assertEqual(len(m.sigs(m.res(), 'AGG')), 1)
        m = self.world(po('PO-1', date='2026-07-01', amount='13000000'), po('PO-2', date='2026-08-01', amount='13000000'))
        self.assertEqual(m.sigs(m.res(), 'AGG'), [])

    def test_orders_that_stay_below_the_threshold_together_are_silent(self):
        m = self.world(po('PO-1', date='2026-07-01', amount='12000000'), po('PO-2', date='2026-07-05', amount='12999999'))
        self.assertEqual(m.sigs(m.res(), 'AGG'), [])
        m = self.world(po('PO-1', date='2026-07-01', amount='12000000'), po('PO-2', date='2026-07-05', amount='13000000'))
        self.assertEqual(len(m.sigs(m.res(), 'AGG')), 1)

    def test_a_single_order_at_the_threshold_is_a_material_order_not_a_split(self):
        m = self.world(po('PO-1', date='2026-07-01', amount='25000000'), po('PO-2', date='2026-07-05', amount='100'))
        r = m.res()
        self.assertEqual(m.sigs(r, 'AGG'), [])
        self.assertTrue(any(n.startswith('CLUSTER_WITH_SINGLE_MATERIAL_ORDER') for n in m.run(r, 'AGG')['notes']))

    def test_different_suppliers_are_different_groups_under_the_configured_keys(self):
        m = self.world(po('PO-1', supplier='SUP-001', date='2026-07-01', amount='13000000'), po('PO-2', supplier='SUP-002', date='2026-07-02', amount='13000000'))
        self.assertEqual(m.sigs(m.res(), 'AGG'), [])

    def test_the_grouping_key_decides_the_result_project_only_merges_suppliers(self):
        m = self.world(po('PO-1', supplier='SUP-001', date='2026-07-01', amount='13000000'), po('PO-2', supplier='SUP-002', date='2026-07-02', amount='13000000'))
        m.rules(AGG={'keys': ['project'], 'window_days': 30, 'single_order_abs_cents': 25000000})
        self.assertEqual(len(m.sigs(m.res(), 'AGG')), 1)

    def test_an_order_missing_a_grouping_key_is_left_out_and_listed_not_a_reason_to_flag_everything(self):
        m = det_world()
        m.pos(po('PO-1', date='2026-07-01', amount='13000000'), po('PO-2', date='2026-07-02', amount='13000000'), po('PO-3', cc='', date='2026-07-03', amount='13000000'))
        m.reconcile()
        r = m.res()
        self.assertEqual(len(m.sigs(r, 'AGG')), 1)
        self.assertEqual(m.sigs(r, 'AGG')[0]['extra']['orders'], ['PO-1', 'PO-2'])
        self.assertTrue(any(n['subject'] == 'purchase_order/PO-3' for n in m.run(r, 'AGG')['not_assessed']))

    def test_a_duplicate_delivery_is_not_counted_twice(self):
        m = det_world()
        m.pos(po('PO-1', date='2026-07-01', amount='13000000'))
        m.reconcile()
        self.assertEqual(m.sigs(m.res(), 'AGG'), [])

    def test_an_order_dated_after_the_as_of_date_is_ignored(self):
        m = self.world(po('PO-1', date='2026-09-01', amount='13000000'), po('PO-2', date='2026-10-05', amount='13000000'))
        self.assertEqual(m.sigs(m.res(), 'AGG'), [])

    def test_a_chain_of_orders_each_inside_the_window_of_the_next_forms_one_group(self):
        m = self.world(po('PO-1', date='2026-06-01', amount='9000000'), po('PO-2', date='2026-06-25', amount='9000000'), po('PO-3', date='2026-07-19', amount='9000000'))
        (s,) = m.sigs(m.res(), 'AGG')
        self.assertEqual(s['extra']['orders'], ['PO-1', 'PO-2', 'PO-3'])

    def test_unconfigured_aggregation_names_the_open_decision(self):
        m = self.world(*self.three())
        m.rules(AGG=None)
        run = m.run(m.res(), 'AGG')
        self.assertEqual(run['status'], 'not_configured')
        self.assertIn('DEC-A1-8', run['decision'])

    def test_the_model_policy_is_the_cr02_reference_model_not_a_copy(self):
        from apg import materiality
        from apg.det import rules_cost
        self.assertIs(rules_cost.M, materiality)


class TestD01(unittest.TestCase):
    def test_a_held_invoice_gives_a_data_integrity_signal_that_is_not_a_loss(self):
        m = det_world()
        m.invoices(inv('INV-1', sin='SI-1', ex='1000000'), inv('INV-2', sin='SI-1', ex='1200000'))
        m.reconcile()
        (s,) = m.sigs(m.res(), 'D01')
        self.assertEqual((s['taxonomy']['family'], s['interpretation'], s['quantification']['status']), ('data_integrity', 'data_quality_risk', 'unquantified'))
        self.assertEqual(sorted(e['ref'] for e in s['evidence']), ['ap_invoice/INV-1', 'ap_invoice/INV-2'])
        self.assertEqual(s['extra']['by_class'], {'disputed': 2})

    def test_clean_cost_data_gives_no_signal(self):
        m = det_world()
        m.invoices(inv('INV-1', ex='1000000'))
        m.reconcile()
        self.assertEqual(m.sigs(m.res(), 'D01'), [])

    def test_a_figure_that_cannot_be_assessed_is_reported_not_hidden(self):
        m = det_world()
        m.set_policy(cost_scope=None)
        (s,) = m.sigs(m.res(), 'D01')
        self.assertEqual(s['taxonomy']['subtype'], 'figure_cannot_be_assessed')
