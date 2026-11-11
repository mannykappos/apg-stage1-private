"""Edge cases of the cost and commitment rules found by the mutation pass: the as-of day itself, the exact words of a 'not assessed' reason, and the reconciliation outcome written into
each piece of evidence.  Every value is synthetic."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_det import det_world, inv, po
from .test_det_rules_cost import amd


def two_orders(**kw):
    m = det_world(**kw)
    m.pos(po('PO-1', date='2026-07-01', amount='13000000'), po('PO-2', date='2026-07-02', amount='13000000'))
    m.reconcile()
    return m


class TestAggregationAsOfAndReasons(unittest.TestCase):
    def test_an_order_dated_on_the_as_of_day_counts_and_one_dated_the_next_day_does_not(self):
        m = two_orders()
        r = m.res(as_of='2026-07-02')
        self.assertEqual([s['extra']['orders'] for s in m.sigs(r, 'AGG')], [['PO-1', 'PO-2']])
        self.assertEqual(m.run(r, 'AGG')['not_assessed'], [])
        r = m.res(as_of='2026-07-01')
        self.assertEqual(m.sigs(r, 'AGG'), [])
        self.assertEqual(m.run(r, 'AGG')['not_assessed'], [{'subject': 'purchase_order/PO-2', 'why': 'undated or after the as-of date'}])

    def test_an_order_with_no_reconciliation_state_is_not_assessed_and_says_so(self):
        m = det_world()
        m.pos(po('PO-1', date='2026-07-01', amount='13000000'), po('PO-2', date='2026-07-02', amount='13000000'))
        r = m.res()                                                                       # never reconciled
        self.assertEqual(m.sigs(r, 'AGG'), [])
        self.assertEqual(m.run(r, 'AGG')['not_assessed'], [{'subject': 'purchase_order/PO-1', 'why': 'not usable (no reconciliation state)'},
                                                           {'subject': 'purchase_order/PO-2', 'why': 'not usable (no reconciliation state)'}])

    def test_an_order_still_pending_reconciliation_names_that_outcome(self):
        m = det_world()
        m.pos(po('PO-1', date='2026-07-01', amount='13000000'), po('PO-2', date='2026-07-02', amount='13000000'), po('PO-3', cc='', date='2026-07-03', amount='13000000'))
        m.reconcile()
        self.assertEqual(m.run(m.res(), 'AGG')['not_assessed'], [{'subject': 'purchase_order/PO-3', 'why': 'not usable (pending_reconciliation)'}])

    def test_an_order_with_a_blank_grouping_key_is_named_with_the_key_that_is_blank(self):
        m = det_world()
        blank = po('PO-2', date='2026-07-02', amount='13000000')
        blank[5] = ''                                                                     # no material
        m.pos(po('PO-1', date='2026-07-01', amount='13000000'), blank)
        m.reconcile()
        r = m.res()
        self.assertEqual(m.sigs(r, 'AGG'), [])
        self.assertEqual(m.run(r, 'AGG')['not_assessed'], [{'subject': 'purchase_order/PO-2', 'why': 'a grouping key is missing: material'}])
        m.rules(AGG={'keys': ['project'], 'window_days': 30, 'single_order_abs_cents': 25000000})        # the blank key is not one of the configured keys: the order counts
        r = m.res()
        self.assertEqual(m.run(r, 'AGG')['not_assessed'], [])
        self.assertEqual([s['extra']['orders'] for s in m.sigs(r, 'AGG')], [['PO-1', 'PO-2']])

    def test_the_evidence_carries_each_orders_reconciliation_outcome(self):
        m = two_orders()
        (s,) = m.sigs(m.res(), 'AGG')
        self.assertEqual([(e['ref'], e.get('reconciliation')) for e in s['evidence']], [('purchase_order/PO-1', 'accepted'), ('purchase_order/PO-2', 'accepted')])


class TestEvidenceOutcomes(unittest.TestCase):
    def test_r02_evidence_carries_the_amendments_outcome_and_names_no_change_that_does_not_exist(self):
        m = det_world()
        m.pos(po('PO-1', amount='1000000'))
        m.amendments(amd(change='VAR-9'))
        m.reconcile()
        (s,) = m.sigs(m.res(), 'R02')
        self.assertEqual([(e['ref'], e.get('reconciliation')) for e in s['evidence']], [('po_amendment/AMD-1', 'accepted'), ('purchase_order/PO-1', None)])
        self.assertIn('names change VAR-9', s['explanation']['observed'])

    def test_r02_cites_the_named_change_when_it_is_stored(self):
        from .helpers_det import var
        m = det_world()
        m.pos(po('PO-1', amount='1000000'))
        m.variations(var('VAR-9', status='draft'))
        m.amendments(amd(change='VAR-9'))
        m.reconcile()
        (s,) = m.sigs(m.res(), 'R02')
        self.assertIn('variation/VAR-9', [e['ref'] for e in s['evidence']])

    def test_r03_evidence_carries_each_invoices_outcome(self):
        m = det_world()
        m.pos(po('PO-1', amount='1000000'))
        m.invoices(inv('INV-1', po='PO-1', ex='1076000'))
        m.reconcile()
        (s,) = m.sigs(m.res(), 'R03')
        self.assertEqual([(e['ref'], e.get('reconciliation')) for e in s['evidence']], [('ap_invoice/INV-1', 'accepted'), ('purchase_order/PO-1', None)])        # evidence is kept in reference order


if __name__ == '__main__':
    unittest.main()
