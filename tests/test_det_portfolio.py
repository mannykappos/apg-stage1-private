import copy
import unittest
from . import _path                                         # noqa: F401
from .helpers_det import det_world, inv, po, delay
from apg.det import findings as FD, portfolio as PF, relations as RL


def finding(fid, interp='forecast_exposure', cents=100, label='estimate', status='detected', refs=('ap_invoice/A',), group=None, relations=(), project='PRJ-001', reason=''):
    q = ({'status': 'quantified', 'gross_cents': cents, 'label': label, 'reason': ''} if cents is not None else {'status': 'unquantified', 'gross_cents': None, 'label': None, 'reason': reason or 'why not'})
    return {'finding_id': fid, 'scope': {'level': 'project', 'project': project}, 'status': status, 'relations': list(relations),
            'signal': {'interpretation': interp, 'quantification': q, 'evidence': [{'ref': r, 'revision': 1, 'role': 'x'} for r in refs], 'overlap_group': group}}


class TestAggregate(unittest.TestCase):
    def test_separate_findings_are_added_and_the_range_has_no_width(self):
        v = PF.aggregate([finding('A', cents=100, refs=('r/1',)), finding('B', cents=250, refs=('r/2',))])
        e = v['by_interpretation']['forecast_exposure']
        self.assertEqual((e['lower_bound_cents'], e['upper_bound_cents'], e['overlap_adjusted'], e['components']), (350, 350, False, 2))

    def test_findings_that_share_a_record_form_a_range_never_a_sum(self):
        v = PF.aggregate([finding('A', cents=100, refs=('ap_invoice/X',)), finding('B', cents=250, refs=('ap_invoice/X', 'purchase_order/P'))])
        e = v['by_interpretation']['forecast_exposure']
        self.assertEqual((e['lower_bound_cents'], e['upper_bound_cents'], e['overlap_adjusted'], e['components']), (250, 350, True, 1))
        self.assertIn('a range, not a total', e['note'])

    def test_a_shared_overlap_group_or_a_person_link_also_joins_findings(self):
        v = PF.aggregate([finding('A', cents=100, refs=('r/1',), group='g'), finding('B', cents=250, refs=('r/2',), group='g')])
        self.assertEqual(v['by_interpretation']['forecast_exposure']['lower_bound_cents'], 250)
        link = {'with': 'B', 'kind': 'financial_overlap', 'confirmed': False}
        v = PF.aggregate([finding('A', cents=100, refs=('r/1',), relations=[link]), finding('B', cents=250, refs=('r/2',))])
        self.assertEqual(v['by_interpretation']['forecast_exposure']['lower_bound_cents'], 250)

    def test_a_root_cause_hypothesis_link_does_not_merge_anything(self):
        link = {'with': 'B', 'kind': 'shared_root_cause_hypothesis', 'confirmed': True}
        v = PF.aggregate([finding('A', cents=100, refs=('r/1',), relations=[link]), finding('B', cents=250, refs=('r/2',))])
        e = v['by_interpretation']['forecast_exposure']
        self.assertEqual((e['lower_bound_cents'], e['upper_bound_cents']), (350, 350))

    def test_policy_records_in_the_evidence_do_not_make_findings_overlap(self):
        v = PF.aggregate([finding('A', cents=100, refs=('r/1', 'det_policy/D-1', 'fin_policy/P-1')), finding('B', cents=250, refs=('r/2', 'det_policy/D-1', 'fin_policy/P-1'))])
        self.assertFalse(v['by_interpretation']['forecast_exposure']['overlap_adjusted'])

    def test_interpretations_are_never_added_together(self):
        v = PF.aggregate([finding('A', 'forecast_exposure', 100, refs=('r/1',)), finding('B', 'cash_timing_exposure', 250, 'figure', refs=('r/2',)),
                          finding('C', 'potential_revenue_at_risk', 70, 'record', refs=('r/3',))])
        self.assertEqual(sorted(v['by_interpretation']), ['cash_timing_exposure', 'forecast_exposure', 'potential_revenue_at_risk'])
        self.assertNotIn('total', v)
        self.assertIn('interpretations are never added together', v['not_reported'])

    def test_unquantified_findings_are_listed_with_the_reason_and_never_counted_as_zero(self):
        v = PF.aggregate([finding('A', cents=100, refs=('r/1',)), finding('B', cents=None, refs=('r/2',), reason='no value recorded')])
        e = v['by_interpretation']['forecast_exposure']
        self.assertEqual((e['findings'], e['quantified'], e['upper_bound_cents']), (2, 1, 100))
        self.assertEqual(v['unquantified'], [{'finding_id': 'B', 'interpretation': 'forecast_exposure', 'why': 'no value recorded'}])

    def test_when_nothing_is_quantified_the_headline_says_so_and_never_prints_a_range_of_zero(self):
        # M5 independent review, issue 1 (corrected in M6): two unquantified findings must not read as "$0 - $0"
        v = PF.aggregate([finding('A', cents=None, refs=('r/1',)), finding('B', cents=None, refs=('r/2',))])
        e = v['by_interpretation']['forecast_exposure']
        self.assertFalse(e['quantified_amount_available'])
        self.assertEqual(e['range_display'], 'no quantified amount available (2 finding(s) have no defensible amount; this is not zero exposure)')
        self.assertEqual(e['unquantified'], 2)

    def test_the_range_display_states_a_single_amount_a_range_and_the_unquantified_remainder(self):
        one = PF.aggregate([finding('A', cents=12345, refs=('r/1',))])['by_interpretation']['forecast_exposure']
        self.assertEqual((one['quantified_amount_available'], one['range_display']), (True, '123.45'))
        rng = PF.aggregate([finding('A', cents=100, refs=('ap_invoice/X',)), finding('B', cents=250, refs=('ap_invoice/X', 'purchase_order/P')), finding('C', cents=None, refs=('r/3',))])['by_interpretation']['forecast_exposure']
        self.assertEqual(rng['range_display'], '2.50 to 3.50; 1 further finding(s) are unquantified and not included')

    def test_dismissed_and_superseded_findings_are_excluded_and_named(self):
        v = PF.aggregate([finding('A', cents=100, refs=('r/1',)), finding('B', cents=250, status='dismissed', refs=('r/2',)), finding('C', cents=999, status='superseded', refs=('r/3',))])
        self.assertEqual(v['by_interpretation']['forecast_exposure']['upper_bound_cents'], 100)
        self.assertEqual(v['excluded'], ['B', 'C'])

    def test_a_resolved_or_reopened_finding_still_counts_until_a_person_dismisses_it(self):
        v = PF.aggregate([finding('A', cents=100, status='resolved', refs=('r/1',)), finding('B', cents=250, status='reopened', refs=('r/2',))])
        self.assertEqual(v['by_interpretation']['forecast_exposure']['upper_bound_cents'], 350)

    def test_data_quality_and_compliance_findings_carry_no_financial_total(self):
        v = PF.aggregate([finding('A', 'data_quality_risk', None, refs=('r/1',)), finding('B', 'compliance_risk', None, refs=('r/2',))])
        self.assertEqual(v['by_interpretation'], {})
        self.assertIn('data-integrity, compliance and operational findings carry no financial amount here', v['not_reported'])

    def test_labels_are_reported_so_an_estimate_is_not_read_as_a_figure(self):
        v = PF.aggregate([finding('A', cents=100, label='figure', refs=('r/1',)), finding('B', cents=1, label='estimate', refs=('r/2',))])
        self.assertEqual(v['by_interpretation']['forecast_exposure']['amount_labels'], ['figure', 'estimate'])
        self.assertIn('no amount here is a verified realised saving', ' '.join(v['not_reported']))

    def test_a_project_filter_leaves_out_other_projects(self):
        v = PF.aggregate([finding('A', cents=100, refs=('r/1',)), finding('B', cents=250, refs=('r/2',), project='PRJ-002')], project='PRJ-002')
        self.assertEqual(v['by_interpretation']['forecast_exposure']['upper_bound_cents'], 250)

    def test_the_input_is_not_changed(self):
        fs = [finding('A', cents=100, refs=('r/1',)), finding('B', cents=250, refs=('r/1',))]
        before = copy.deepcopy(fs)
        PF.aggregate(fs)
        self.assertEqual(fs, before)

    def test_findings_of_a_tenant_come_only_from_that_tenants_store(self):
        m = det_world()
        m.invoices(inv('INV-1', ex='5300000', cc='CC-01'))
        m.reconcile()
        m.ingest(m.detect())
        other = m.w.who('t2', 'other_co', 'olga', ('importer',))
        self.assertEqual(PF.portfolio_view(other)['by_interpretation'], {})
        self.assertEqual(PF.portfolio_view(m.s)['by_interpretation']['forecast_exposure']['findings'], 1)


class TestRelations(unittest.TestCase):
    def test_related_lists_the_reason_for_each_pair(self):
        a = finding('A', refs=('ap_invoice/X', 'r/1'), group='g', relations=[{'with': 'B', 'kind': 'shared_root_cause_hypothesis', 'confirmed': False}])
        b = finding('B', refs=('ap_invoice/X',), group='g')
        c = finding('C', refs=('r/9',))
        rel = RL.related([a, b, c])
        because = rel['A'][0]['because']
        self.assertEqual(rel['A'][0]['with'], 'B')
        self.assertIn('overlap_group:g', because)
        self.assertIn('shared_records:ap_invoice/X', because)
        self.assertIn('suspected shared_root_cause_hypothesis', because)
        self.assertEqual(rel['C'], [])

    def test_components_are_transitive(self):
        fs = [finding('A', refs=('r/1',)), finding('B', refs=('r/1', 'r/2')), finding('C', refs=('r/2',)), finding('D', refs=('r/9',))]
        c = RL.components(fs)
        self.assertEqual(len({c['A'], c['B'], c['C']}), 1)
        self.assertNotEqual(c['A'], c['D'])


class TestRealOverlap(unittest.TestCase):
    def test_a_budget_overrun_and_an_over_invoiced_order_that_share_an_invoice_are_one_component_in_a_real_run(self):
        m = det_world()
        m.pos(po('PO-1', amount='1000000'))
        m.invoices(inv('INV-1', po='PO-1', ex='5300000', cc='CC-01'))                      # over the budget line AND over its order
        m.reconcile()
        m.ingest(m.detect())
        fs = FD.all_findings(m.svc)
        self.assertEqual(sorted(f['rule_id'] for f in fs), ['DET-R01', 'DET-R03'])
        comp = RL.components(fs)
        self.assertEqual(len(set(comp.values())), 1)
        e = PF.aggregate(fs)['by_interpretation']['forecast_exposure']
        self.assertTrue(e['overlap_adjusted'])
        self.assertLess(e['lower_bound_cents'], e['upper_bound_cents'])
        self.assertEqual(e['upper_bound_cents'], sum(f['signal']['quantification']['gross_cents'] for f in fs))

    def test_two_delay_events_on_one_activity_share_an_overlap_group(self):
        m = det_world()
        m.delays(delay('D-1', act='A-1', start='2026-07-06', end='2026-07-21'), delay('D-2', act='A-1', start='2026-07-15', end='2026-07-30'))
        m.reconcile()
        m.ingest(m.detect())
        fs = [f for f in FD.all_findings(m.svc) if f['rule_id'] == 'DET-DLY']
        self.assertEqual(len(fs), 1)
        self.assertEqual(fs[0]['signal']['overlap_group'], 'schedule:PRJ-001:A-1')

    def test_a_person_can_link_findings_as_financial_overlap_and_the_range_follows(self):
        m = det_world()
        m.invoices(inv('INV-1', ex='5300000', cc='CC-01'), inv('INV-2', sin='SI-2', ex='4000000', cc='CC-02'))
        m.reconcile()
        m.ingest(m.detect())
        fs = FD.all_findings(m.svc)
        self.assertEqual(len(fs), 2)
        self.assertFalse(PF.aggregate(fs)['by_interpretation']['forecast_exposure']['overlap_adjusted'])
        FD.link(m.reviewer, m.clock, fs[0]['finding_id'], fs[1]['finding_id'], 'financial_overlap', 'same remediation scope')
        e = PF.portfolio_view(m.s)['by_interpretation']['forecast_exposure']
        self.assertTrue(e['overlap_adjusted'])

    def test_linking_needs_a_person_with_the_reviewer_role_and_a_reason_and_a_valid_kind(self):
        m = det_world()
        m.invoices(inv('INV-1', ex='5300000', cc='CC-01'), inv('INV-2', sin='SI-2', ex='4000000', cc='CC-02'))
        m.reconcile()
        m.ingest(m.detect())
        a, b = [f['finding_id'] for f in FD.all_findings(m.svc)]
        for who, kind, why in ((m.owner, 'related', 'x'), (m.reviewer, 'related', ''), (m.reviewer, 'friends', 'x')):
            with self.assertRaises(FD.LifecycleError):
                FD.link(who, m.clock, a, b, kind, why)
        with self.assertRaises(FD.LifecycleError):
            FD.link(m.reviewer, m.clock, a, a, 'related', 'x')
        FD.link(m.reviewer, m.clock, a, b, 'shared_root_cause_hypothesis', 'same crew', confirmed=True)
        self.assertTrue(FD.get(m.svc, a)['relations'][0]['confirmed'])
        FD.link(m.reviewer, m.clock, a, b, 'financial_overlap', 'x', confirmed=True)
        self.assertFalse([r for r in FD.get(m.svc, a)['relations'] if r['kind'] == 'financial_overlap'][0]['confirmed'])         # overlap is never "confirmed"


class TestMoneyDisplay(unittest.TestCase):
    def test_a_quantified_zero_prints_as_zero_without_a_sign_and_only_a_loss_below_zero_has_one(self):
        self.assertEqual(PF._money(0), '0.00')
        self.assertEqual(PF._money(5), '0.05')
        self.assertEqual(PF._money(-5), '-0.05')
        self.assertEqual(PF._money(-12345), '-123.45')
        # a quantified amount of zero is shown as such; it is different from "no quantified amount"
        self.assertEqual(PF._range_display(0, 0, 1, 0), '0.00')
