import copy, json, os, unittest
from . import _path                                         # noqa: F401
from .helpers_fin import Mini, base_world, inv, bud, po, AS_OF, CRN_H, PO_H
from .helpers_ingest import csvb, inv_file, tpl
from apg.fin import costs, demo_fin as DF
from apg.fin.figure import AUTH, PROV, CANT
from apg.ingest import review, pipeline as P3, demo_setup as D
from apg.ingest.specs import IngestPolicy


def cost(m, project='PRJ-001', as_of=AS_OF, **kw):
    return m.fig('fin.actual_cost', project, as_of, **kw)


def refs(f, cls=None):
    return sorted(e['ref'] for e in f['excluded'] if cls is None or e['class'] == cls)


class TestActualCost(unittest.TestCase):
    def test_sums_counted_invoices_by_cost_code_and_cites_them(self):
        m = Mini()
        m.invoices(inv('INV-1', ex='1000000', cc='CC-01'), inv('INV-2', sin='SI-2', ex='2500000', cc='CC-02'), inv('INV-3', sin='SI-3', ex='300000', cc='CC-01'))
        m.reconcile()
        f = cost(m)
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 3800000))
        self.assertEqual(f['classified']['by_cost_code'], {'CC-01': 1300000, 'CC-02': 2500000})
        self.assertEqual(f['classified']['counted_invoices'], 3)
        self.assertEqual([c['ref'] for c in f['contributed']], ['ap_invoice/INV-1', 'ap_invoice/INV-2', 'ap_invoice/INV-3'])
        self.assertTrue(all(c['revision'] == 1 for c in f['contributed']))                       # the pinned revision of each record is cited
        self.assertEqual(f['value']['cents'], sum(c['amount_cents'] for c in f['contributed']))      # the value IS the sum of what it cites
        self.assertIn('labour, plant, accruals', ' '.join(f['limits']))

    def test_empty_project_is_a_real_zero_not_unknown(self):
        m = Mini(); m.reconcile()
        f = cost(m)
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 0))

    def test_duplicate_delivery_counts_once_and_is_listed(self):
        m = Mini()
        m.invoices(inv('INV-1', sin='SI-9', ex='1000000'), inv('INV-2', sin='SI-9', ex='1000000', batch='B-2'))
        m.reconcile()
        f = cost(m)
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 1000000))
        self.assertEqual(f['applied']['duplicates'], [{'ref': 'ap_invoice/INV-2', 'duplicate_of': 'ap_invoice/INV-1'}])
        self.assertEqual(refs(f, 'duplicate_delivery'), ['ap_invoice/INV-2'])

    def test_same_number_different_details_is_a_candidate_that_holds_both(self):
        m = Mini()
        m.invoices(inv('INV-1', sin='SI-9', ex='1000000'), inv('INV-2', sin='SI-9', ex='1200000'))
        m.reconcile()
        f = cost(m)
        self.assertEqual((f['state'], f['value']['cents']), (PROV, 0))
        self.assertEqual(refs(f, 'disputed'), ['ap_invoice/INV-1', 'ap_invoice/INV-2'])
        self.assertEqual(len(f['disputed']), 2)

    def test_credit_and_reissue_is_net_not_a_sum_of_three_events(self):
        m = Mini()
        m.invoices(inv('INV-A', sin='SI-5', ex='6000000'), inv('INV-B', sin='SI-5R', ex='5800000'))
        m.credits(['CRN-1', 'SUP-001', 'INV-A', '2026-07-25', '6000000', '600000'])
        m.reconcile()
        f = cost(m)
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 5800000))
        self.assertEqual(f['applied']['credits'], [{'ref': 'credit_note/CRN-1', 'against': 'ap_invoice/INV-A', 'amount_cents': -6000000}])
        self.assertEqual(f['classified']['gross_cents'], 11800000)
        self.assertEqual(f['classified']['credits_applied_cents'], 6000000)
        self.assertEqual(f['value']['cents'], sum(c['amount_cents'] for c in f['contributed']))      # invoices and the negative credit add up to the value

    def test_partial_credit(self):
        m = Mini()
        m.invoices(inv('INV-A', ex='1000000'))
        m.credits(['CRN-1', 'SUP-001', 'INV-A', '2026-07-25', '250000', '25000'])
        m.reconcile()
        self.assertEqual(cost(m)['value']['cents'], 750000)

    def test_credit_larger_than_the_invoice_holds_the_invoice_out_rather_than_counting_gross(self):
        m = Mini()
        m.invoices(inv('INV-A', ex='1000000'))
        m.credits(['CRN-1', 'SUP-001', 'INV-A', '2026-07-25', '1500000', '0'])
        m.reconcile()
        f = cost(m)
        self.assertEqual((f['state'], f['value']['cents']), (PROV, 0))
        self.assertIn('ap_invoice/INV-A', refs(f))
        self.assertTrue(any('LINKED_CREDIT_UNRESOLVED' in c for e in f['excluded'] for c in e['codes']))

    def test_credit_with_no_visible_invoice_stays_visible_on_every_project(self):
        m = Mini()
        m.invoices(inv('INV-A', ex='1000000'))
        m.credits(['CRN-1', 'SUP-001', 'INV-GONE', '2026-07-25', '400000', '0'])
        m.reconcile()
        for p in ('PRJ-001', 'PRJ-002'):
            f = cost(m, p)
            self.assertEqual(f['state'], PROV, p)
            self.assertIn('credit_note/CRN-1', refs(f, 'unattributed'), p)
        self.assertEqual(cost(m)['value']['cents'], 1000000)              # never netted against a guess

    def test_credit_dated_after_the_cutoff_is_not_yet_applied(self):
        m = Mini()
        m.invoices(inv('INV-A', ex='1000000'))
        m.credits(['CRN-1', 'SUP-001', 'INV-A', '2026-09-20', '250000', '0'])
        m.reconcile()
        self.assertEqual(cost(m, as_of='2026-09-30')['value']['cents'], 750000)
        f = cost(m, as_of='2026-09-10')
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 1000000))
        self.assertEqual(refs(f, 'after_cutoff'), ['credit_note/CRN-1'])

    def test_invoice_after_the_cutoff_is_outside_the_period_not_an_error(self):
        m = Mini()
        m.invoices(inv('INV-1', date='2026-09-30', ex='100'), inv('INV-2', sin='S2', date='2026-10-01', ex='200'))
        m.reconcile('2026-10-05')
        f = cost(m, as_of='2026-09-30')
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 100))                       # the boundary day is inside
        self.assertEqual(refs(f, 'after_cutoff'), ['ap_invoice/INV-2'])
        self.assertEqual(f['classified']['after_cutoff'][0]['amount_cents'], 200)

    def test_other_projects_are_not_in_this_figure(self):
        m = Mini()
        m.invoices(inv('INV-1', project='PRJ-001', ex='100'), inv('INV-2', sin='S2', project='PRJ-002', ex='900'))
        m.reconcile()
        self.assertEqual(cost(m, 'PRJ-001')['value']['cents'], 100)
        self.assertEqual(cost(m, 'PRJ-002')['value']['cents'], 900)
        self.assertNotIn('ap_invoice/INV-2', refs(cost(m, 'PRJ-001')) + [c['ref'] for c in cost(m, 'PRJ-001')['contributed']])

    def test_two_systems_disagree_the_invoice_is_disputed_and_left_out(self):
        m = Mini()
        m.invoices(inv('INV-1', ex='1000000'), inv('INV-2', sin='S2', ex='7280125'))
        m.m3('TPL-BZ-PM-INVOICES', csvb(['invoice_ref', 'supplier_id', 'project_id', 'ex_gst_cents', 'source'], [['INV-2', 'SUP-001', 'PRJ-001', '8180125', 'pm']]), 'pm_system')
        m.reconcile()
        f = cost(m)
        self.assertEqual((f['state'], f['value']['cents']), (PROV, 1000000))
        self.assertEqual(refs(f, 'disputed'), ['ap_invoice/INV-2'])
        self.assertEqual(f['excluded'][0]['amount_cents'], 7280125)                          # its size is shown to the reviewer; it is not in the value

    def test_conflict_marker_is_attributed_to_the_project_all_contenders_name(self):
        m = Mini()
        m.invoices(inv('INV-1', ex='100'))
        m.invoices(inv('INV-1', ex='900'))                                                    # same key, different content, no way to order -> conflict marker
        m.invoices(inv('INV-3', sin='S3', project='PRJ-002', ex='50'))
        m.reconcile()
        f1, f2 = cost(m, 'PRJ-001'), cost(m, 'PRJ-002')
        self.assertEqual(refs(f1, 'disputed'), ['ap_invoice/INV-1'])
        self.assertEqual(f1['state'], PROV)
        self.assertEqual((f2['state'], f2['value']['cents']), (AUTH, 50))                    # the conflict does not touch PRJ-002

    def test_conflict_between_contenders_naming_different_projects_shows_on_every_project(self):
        m = Mini()
        m.invoices(inv('INV-1', project='PRJ-001', ex='100'))
        m.invoices(inv('INV-1', project='PRJ-002', ex='100'))
        m.reconcile()
        for p in ('PRJ-001', 'PRJ-002', 'PRJ-009'):
            f = cost(m, p)
            self.assertEqual((f['state'], refs(f, 'unattributed')), (PROV, ['ap_invoice/INV-1']), p)

    def test_ambiguous_supplier_is_held(self):
        m = Mini()
        m.invoices(inv('INV-1', ex='100'), inv('INV-2', sin='S2', supplier='Metro Steel', ex='900'))
        m.reconcile()
        f = cost(m)
        self.assertEqual((f['state'], f['value']['cents']), (PROV, 100))
        self.assertEqual(refs(f), ['ap_invoice/INV-2'])
        self.assertTrue(any(c.startswith('SUPPLIER_') for c in f['excluded'][0]['codes']))

    def test_missing_gst_does_not_hold_the_cost(self):
        m = Mini()
        m.invoices(inv('INV-1', ex='100', gst=''))
        m.reconcile()
        f = cost(m)
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 100))

    def test_missing_cost_code_holds_the_invoice_unless_the_policy_tolerates_it(self):
        m = Mini()
        m.invoices(inv('INV-1', ex='100', cc=''))
        m.reconcile()
        f = cost(m)
        self.assertEqual((f['state'], f['value']['cents'], refs(f)), (PROV, 0, ['ap_invoice/INV-1']))
        self.assertEqual(f['excluded'][0]['class'], 'unknown_value')
        m2 = Mini()
        pol = IngestPolicy(warn_unknown={'ap_invoice': ('gst_cents', 'purchase_order_ref', 'source_status', 'source_batch_ref', 'cost_code_ref')})
        P3.ingest_file(m2.s, m2.clock, tpl('TPL-BZ-AP-INVOICES'), inv_file(inv('INV-1', ex='100', cc='')), 'accounting', 'a.csv', pol)
        m2.reconcile()
        f2 = cost(m2)
        self.assertEqual(f2['classified']['by_cost_code'], {costs.NO_CODE: 100})                # a tolerated gap is bucketed, never given another code

    def test_invoice_missing_a_required_value_is_rejected_at_intake_and_cannot_be_in_cost(self):
        m = Mini()
        r = m.invoices(inv('INV-1', ex=''), inv('INV-2', sin='S2', ex='50'))
        self.assertEqual(r['counts']['rejected'], 1)
        m.reconcile()
        self.assertEqual(cost(m)['value']['cents'], 50)

    def test_payments_are_never_read_cost_is_not_cash(self):
        m = Mini()
        m.invoices(inv('INV-1', ex='1000000', gst='100000'))
        m.reconcile()
        before = cost(m)
        m.m3('TPL-BZ-PAYMENTS', csvb(['payment_id', 'invoice_id', 'payment_date', 'amount_cents'], [['PAY-1', 'INV-1', '2026-08-01', '1100000']]), 'accounting')
        m.reconcile()
        after = cost(m)
        self.assertEqual(before['value'], after['value'])
        self.assertEqual(before['contributed'], after['contributed'])

    def test_human_correction_is_used_and_labelled(self):
        m = Mini()
        m.invoices(inv('INV-1', ex='1000000'), inv('INV-2', sin='S2', ex='7280125'))
        m.m3('TPL-BZ-PM-INVOICES', csvb(['invoice_ref', 'supplier_id', 'project_id', 'ex_gst_cents', 'source'], [['INV-2', 'SUP-001', 'PRJ-001', '8180125', 'pm']]), 'pm_system')
        m.reconcile()
        rec = m.w.who('rec', user='rita', roles=('reconciler',))
        review.decide(rec, 'ap_invoice/INV-2', 'correct', 'confirmed with the supplier statement', 7280125)
        m.reconcile()
        f = cost(m)
        self.assertEqual(f['value']['cents'], 8280125)
        self.assertIn('HUMAN_CORRECTION_APPLIED:ap_invoice/INV-2', f['reasons'])
        self.assertEqual(f['state'], AUTH)

    def test_rejection_by_a_person_is_a_by_design_exclusion(self):
        m = Mini()
        m.invoices(inv('INV-1', ex='1000000'), inv('INV-2', sin='S2', ex='7280125'))
        m.m3('TPL-BZ-PM-INVOICES', csvb(['invoice_ref', 'supplier_id', 'project_id', 'ex_gst_cents', 'source'], [['INV-2', 'SUP-001', 'PRJ-001', '8180125', 'pm']]), 'pm_system')
        m.reconcile()
        review.decide(m.w.who('rec', user='rita', roles=('reconciler',)), 'ap_invoice/INV-2', 'reject', 'not ours')
        m.reconcile()
        f = cost(m)
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 1000000))
        self.assertEqual(refs(f, 'rejected_by_review'), ['ap_invoice/INV-2'])

    def test_a_revision_is_cited_when_the_stored_record_has_more_than_one(self):
        m = Mini()
        t = tpl('TPL-BZ-AP-INVOICES')
        t['columns'].append({'required': False, 'source_column': 'rev', 'target_field': 'source_revision_label', 'transform': 'trim', 'type': 'string', 'missing_means': 'unknown_not_zero'})
        hdr = ['invoice_id', 'supplier_id', 'supplier_invoice_no', 'project_id', 'cost_code', 'po_id', 'invoice_date', 'ex_gst_cents', 'gst_cents', 'status', 'source_batch', 'rev']
        row = lambda ex, rev: [['INV-1', 'SUP-001', 'SI-1', 'PRJ-001', 'CC-01', '', '2026-05-01', ex, '0', 'posted', 'B', rev]]
        P3.ingest_file(m.s, m.clock, t, csvb(hdr, row('100', 'R1')), 'accounting', 'a.csv', D.DEMO_POLICY, 'source_revision_label')
        P3.ingest_file(m.s, m.clock, t, csvb(hdr, row('150', 'R2')), 'accounting', 'b.csv', D.DEMO_POLICY, 'source_revision_label')
        P3.ingest_file(m.s, m.clock, t, csvb(hdr, row('100', 'R1')), 'accounting', 'c.csv', D.DEMO_POLICY, 'source_revision_label')      # stale: must not revert
        m.reconcile()
        f = cost(m)
        self.assertEqual(f['value']['cents'], 150)
        self.assertEqual(f['applied']['revisions'], [{'ref': 'ap_invoice/INV-1', 'revision': 2, 'source_revision': 2}])
        self.assertEqual(f['contributed'][0]['revision'], 2)

    def test_arrival_order_does_not_change_the_figure(self):
        rows = [inv('INV-%d' % i, sin='S%d' % i, ex=str(100 * i), cc='CC-0%d' % (1 + i % 2)) for i in range(1, 8)]
        a, b = Mini(), Mini()
        a.invoices(*rows); b.invoices(*reversed(rows))
        a.reconcile(); b.reconcile()
        fa, fb = cost(a), cost(b)
        self.assertEqual(fa, fb)

    def test_rerunning_the_same_file_changes_nothing(self):
        m = Mini()
        m.invoices(inv('INV-1', ex='100'))
        m.reconcile()
        f1 = cost(m)
        m.invoices(inv('INV-1', ex='100'))
        m.reconcile()
        self.assertEqual(cost(m), f1)

    def test_unapproved_policy_makes_the_figure_provisional(self):
        m = Mini(approved=False)
        m.invoices(inv('INV-1', ex='100'))
        m.reconcile()
        f = cost(m)
        self.assertEqual((f['state'], f['value']['cents']), (PROV, 100))
        self.assertFalse(f['policy']['approved'])

    def test_cost_scope_not_configured_is_cannot_assess_naming_the_decision(self):
        m = Mini()
        m.set_policy(cost_scope=None)
        m.invoices(inv('INV-1', ex='100'))
        m.reconcile()
        f = cost(m)
        self.assertEqual((f['state'], f['value']['cents']), (CANT, None))
        self.assertIn('CR-02 A5', f['unknown_inputs'][0]['decision'])

    def test_unreconciled_record_is_held_not_counted(self):
        m = Mini()
        m.invoices(inv('INV-1', ex='100'))
        f = cost(m)                                                                           # reconcile has not run
        self.assertEqual((f['state'], f['value']['cents']), (PROV, 0))
        self.assertEqual(f['excluded'][0]['codes'], ['NO_RECONCILIATION_STATE'])

    def test_single_cost_code_view_and_sum_of_codes_equals_total(self):
        m = Mini()
        m.invoices(inv('INV-1', ex='100', cc='CC-01'), inv('INV-2', sin='S2', ex='250', cc='CC-02'))
        m.reconcile()
        total = cost(m)['value']['cents']
        from apg.fin import snap, gather
        from apg.repro import _load
        refs_, params = gather.gather(m.s, 'PRJ-001', AS_OF, m.policy['version'])
        F = snap.Facts(_load(m.s, refs_), params)
        parts = {cc: costs.build_actual(F, 'PRJ-001', AS_OF, cost_code=cc)['value']['cents'] for cc in ('CC-01', 'CC-02')}
        self.assertEqual(parts, {'CC-01': 100, 'CC-02': 250})
        self.assertEqual(sum(parts.values()), total)


if __name__ == '__main__':
    unittest.main()
