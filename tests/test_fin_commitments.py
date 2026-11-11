import unittest
from . import _path                                         # noqa: F401
from .helpers_fin import Mini, base_world, inv, po, var, AS_OF, AMD_H
from apg.fin.figure import AUTH, PROV, CANT


def commit(m, project='PRJ-001', as_of=AS_OF):
    return m.fig('fin.commitments', project, as_of)


def lines(f):
    return f['classified']['po_lines']


class TestCommitments(unittest.TestCase):
    def test_open_commitment_is_po_less_invoices(self):
        m = Mini()
        m.pos(po('PO-1', amount='1000000'))
        m.invoices(inv('INV-1', po='PO-1', ex='400000'))
        m.reconcile()
        f = commit(m)
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 600000))
        self.assertEqual(lines(f)['PO-1'], {**lines(f)['PO-1'], 'committed_cents': 1000000, 'invoiced_cents': 400000, 'open_cents': 600000, 'overrun_cents': 0, 'invoices': ['INV-1']})
        self.assertIn('goods received but not yet invoiced', ' '.join(f['limits']))

    def test_po_to_invoice_transition_never_counts_the_same_work_twice(self):
        m = Mini()
        m.pos(po('PO-1', amount='1000000'))
        m.reconcile()
        a0, c0 = m.fig('fin.actual_cost')['value']['cents'], commit(m)['value']['cents']
        self.assertEqual((a0, c0), (0, 1000000))
        for i, ex in enumerate(('300000', '200000', '500000'), 1):
            m.invoices(inv('INV-%d' % i, sin='S%d' % i, po='PO-1', ex=ex))
            m.reconcile()
            a, c = m.fig('fin.actual_cost')['value']['cents'], commit(m)['value']['cents']
            self.assertEqual(a + c, 1000000, i)                                                   # actual + still-open is always exactly the PO value
        self.assertEqual(commit(m)['value']['cents'], 0)

    def test_invoice_above_the_commitment_is_an_overrun_never_a_negative_commitment(self):
        m = Mini()
        m.pos(po('PO-1', amount='1000000'))
        m.invoices(inv('INV-1', po='PO-1', ex='1300000'))
        m.reconcile()
        f = commit(m)
        self.assertEqual(f['value']['cents'], 0)
        self.assertEqual((lines(f)['PO-1']['open_cents'], lines(f)['PO-1']['overrun_cents']), (0, 300000))
        self.assertIn('INVOICED_EXCEEDS_COMMITMENT:PO-1', f['reasons'])

    def test_overrun_on_one_po_does_not_reduce_the_open_amount_of_another(self):
        m = Mini()
        m.pos(po('PO-1', amount='1000000'), po('PO-2', amount='500000'))
        m.invoices(inv('INV-1', po='PO-1', ex='1300000'))
        m.reconcile()
        self.assertEqual(commit(m)['value']['cents'], 500000)

    def test_partial_fulfilment_is_not_full_consumption(self):
        m = Mini()
        m.pos(po('PO-1', amount='1000000'))
        m.invoices(inv('INV-1', po='PO-1', ex='100000'))
        m.reconcile()
        self.assertEqual(commit(m)['value']['cents'], 900000)

    def test_draft_cancelled_and_closed_orders_have_nothing_open(self):
        m = Mini()
        m.set_policy(po_status_map={'open': 'committed', 'draft': 'draft', 'cancelled': 'cancelled', 'closed': 'closed'})
        m.pos(po('PO-1', amount='100', status='open'), po('PO-2', amount='200', status='draft'), po('PO-3', amount='400', status='cancelled'), po('PO-4', amount='800', status='closed'))
        m.reconcile()
        f = commit(m)
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 100))
        self.assertEqual({k: v['open_cents'] for k, v in lines(f).items()}, {'PO-1': 100, 'PO-2': 0, 'PO-3': 0, 'PO-4': 0})
        self.assertEqual([c['ref'] for c in f['contributed']], ['purchase_order/PO-1'])

    def test_unmapped_or_missing_status_keeps_the_order_out_and_is_unknown(self):
        m = Mini()
        m.pos(po('PO-1', amount='100', status='on_hold'))
        m.reconcile()
        f = commit(m)
        self.assertEqual((f['state'], f['value']['cents']), (PROV, 0))
        self.assertEqual(f['excluded'][0]['codes'], ['PO_STATUS_UNMAPPED:on_hold'])
        self.assertIn('CR-02 A12', f['unknown_inputs'][0]['decision'])

    def test_status_map_not_configured_cannot_be_assessed(self):
        m = Mini(); m.set_policy(po_status_map=None)
        m.pos(po('PO-1', amount='100'))
        m.reconcile()
        f = commit(m)
        self.assertEqual((f['state'], f['value']['cents']), (CANT, None))
        self.assertIn('B2', f['unknown_inputs'][0]['decision'])

    def test_amendment_with_an_approved_change_is_committed_without_one_it_is_exposure(self):
        m = Mini()
        m.variations(var('VAR-A', status='approved', value='0'), var('VAR-S', status='submitted'))
        m.pos(po('PO-1', amount='1000000'))
        m.amendments(['AMD-1', 'PO-1', '2026-08-01', '200000', 'VAR-A', 'ok'], ['AMD-2', 'PO-1', '2026-08-02', '300000', '', 'no change ref'], ['AMD-3', 'PO-1', '2026-08-03', '40000', 'VAR-S', 'not approved'],
                     ['AMD-4', 'PO-1', '2026-08-04', '5000', 'VAR-MISSING', 'no such change'])
        m.reconcile()
        f = commit(m)
        l = lines(f)['PO-1']
        self.assertEqual((l['committed_cents'], l['approved_amendments_cents'], l['unapproved_exposure_cents']), (1000000, 200000, 345000))
        self.assertEqual(f['value']['cents'], 1200000)                                            # exposure is in NEITHER the committed nor the open figure
        self.assertEqual(f['classified']['unapproved_exposure_cents'], 345000)
        why = {a['amendment']: a.get('why') or a['treatment'] for a in l['amendments']}
        self.assertEqual(why, {'AMD-1': 'committed', 'AMD-2': 'NO_APPROVED_CHANGE_REFERENCE', 'AMD-3': 'CHANGE_NOT_APPROVED:submitted', 'AMD-4': 'CHANGE_NOT_APPROVED:VAR-MISSING'})

    def test_a_negative_approved_amendment_reduces_the_commitment(self):
        m = Mini()
        m.variations(var('VAR-A', status='approved', value='0'))
        m.pos(po('PO-1', amount='1000000'))
        m.amendments(['AMD-1', 'PO-1', '2026-08-01', '-250000', 'VAR-A', 'descope'])
        m.reconcile()
        self.assertEqual(commit(m)['value']['cents'], 750000)

    def test_amendment_after_cutoff_is_outside_the_period(self):
        m = Mini()
        m.variations(var('VAR-A', status='approved', value='0'))
        m.pos(po('PO-1', amount='1000000'))
        m.amendments(['AMD-1', 'PO-1', '2026-10-01', '200000', 'VAR-A', 'later'])
        m.reconcile('2026-10-05')
        f = commit(m, as_of='2026-09-30')
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 1000000))
        self.assertEqual([e['class'] for e in f['excluded']], ['after_cutoff'])

    def test_variation_map_not_configured_makes_an_amendment_exposure_and_unknown(self):
        m = Mini(); m.set_policy(variation_status_map=None)
        m.variations(var('VAR-A', status='approved'))
        m.pos(po('PO-1', amount='1000000'))
        m.amendments(['AMD-1', 'PO-1', '2026-08-01', '200000', 'VAR-A', 'x'])
        m.reconcile()
        f = commit(m)
        self.assertEqual((f['state'], f['value']['cents'], f['classified']['unapproved_exposure_cents']), (PROV, 1000000, 200000))

    def test_invoices_dated_after_the_cutoff_do_not_use_up_the_commitment(self):
        m = Mini()
        m.pos(po('PO-1', amount='1000000'))
        m.invoices(inv('INV-1', po='PO-1', ex='400000', date='2026-10-01'))
        m.reconcile('2026-10-05')
        self.assertEqual(commit(m, as_of='2026-09-30')['value']['cents'], 1000000)

    def test_credit_effect_on_the_commitment_depends_on_the_policy(self):
        for setting, want, state in ((False, 400000, AUTH), (True, 600000, AUTH), (None, 400000, PROV)):
            m = Mini(); m.set_policy(credit_reopens_commitment=setting)
            m.pos(po('PO-1', amount='1000000'))
            m.invoices(inv('INV-1', po='PO-1', ex='600000'))
            m.credits(['CRN-1', 'SUP-001', 'INV-1', '2026-08-01', '200000', '0'])
            m.reconcile()
            f = commit(m)
            self.assertEqual((f['value']['cents'], f['state']), (want, state), setting)
            if setting is None:
                self.assertIn('CR-02 A12', f['unknown_inputs'][0]['decision'])

    def test_an_unresolved_invoice_for_the_order_makes_the_open_amount_uncertain(self):
        m = Mini()
        m.pos(po('PO-1', amount='1000000'))
        m.invoices(inv('INV-1', po='PO-1', ex='400000'), inv('INV-2', sin='S2', po='PO-1', ex='300000', supplier='Metro Steel'))
        m.reconcile()
        f = commit(m)
        self.assertEqual((f['state'], f['value']['cents']), (PROV, 600000))
        self.assertEqual(lines(f)['PO-1']['unresolved_invoices'], ['INV-2'])
        self.assertTrue(any('INV-2' in u['input'] for u in f['unknown_inputs']))

    def test_identical_orders_are_candidates_and_are_held_not_summed(self):
        m = Mini()
        m.pos(po('PO-1', amount='1000000'), po('PO-2', amount='1000000'))
        m.reconcile()
        f = commit(m)
        self.assertEqual((f['state'], f['value']['cents']), (PROV, 0))
        self.assertEqual(sorted(e['ref'] for e in f['excluded']), ['purchase_order/PO-1', 'purchase_order/PO-2'])
        self.assertEqual(len(f['disputed']), 2)

    def test_order_after_cutoff_and_other_project_orders_are_not_counted(self):
        m = Mini()
        m.pos(po('PO-1', amount='100', date='2026-10-01'), po('PO-2', amount='900', project='PRJ-002', date='2026-01-01'))
        m.reconcile('2026-10-05')
        f = commit(m, as_of='2026-09-30')
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 0))
        self.assertEqual([e['class'] for e in f['excluded']], ['after_cutoff'])
        self.assertEqual(commit(m, 'PRJ-002', '2026-09-30')['value']['cents'], 900)

    def test_open_commitment_by_cost_code_adds_up_to_the_total(self):
        m = Mini()
        m.pos(po('PO-1', cc='CC-01', amount='100'), po('PO-2', cc='CC-02', amount='250', date='2026-01-11'))
        m.invoices(inv('INV-1', po='PO-1', ex='40'))
        m.reconcile()
        f = commit(m)
        self.assertEqual(f['classified']['open_by_cost_code'], {'CC-01': 60, 'CC-02': 250})
        self.assertEqual(sum(f['classified']['open_by_cost_code'].values()), f['value']['cents'])

    def test_stale_approved_change_chain_variation_conflict_is_not_treated_as_approved(self):
        m = Mini()
        m.variations(var('VAR-A', status='approved', value='0'))
        m.variations(var('VAR-A', status='rejected', value='0'))                                   # same key, different content: conflict, so not usable
        m.pos(po('PO-1', amount='1000000'))
        m.amendments(['AMD-1', 'PO-1', '2026-08-01', '200000', 'VAR-A', 'x'])
        m.reconcile()
        f = commit(m)
        self.assertEqual(lines(f)['PO-1']['unapproved_exposure_cents'], 200000)
        self.assertEqual(f['value']['cents'], 1000000)


if __name__ == '__main__':
    unittest.main()
