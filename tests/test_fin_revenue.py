import unittest
from . import _path                                         # noqa: F401
from .helpers_fin import Mini, var, AS_OF, CON_H
from .helpers_ingest import csvb
from apg.fin.figure import AUTH, PROV, CANT


def rev(m, project='PRJ-001', as_of=AS_OF):
    return m.fig('fin.revenue', project, as_of)


def world(summary='0', **kw):
    m = Mini(**kw)
    m.projects(['PRJ-001', 'P1', '10000000', '2026-01-01', '2027-01-01'])
    m.contracts(['PRJ-001', '10000000', summary])
    return m


class TestRevenue(unittest.TestCase):
    def test_contract_only(self):
        m = world()
        f = rev(m)
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 10000000))
        self.assertEqual([c['role'] for c in f['contributed']], ['original_contract'])

    def test_only_approved_variations_are_secured_the_rest_are_classified_apart(self):
        m = world(summary='100000')
        m.variations(var('V-A', status='approved', value='100000'), var('V-S', status='submitted', value='700000'), var('V-R', status='rejected', value='9000'),
                     var('V-U', status='submitted', value=''))
        f = rev(m)
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 10100000))
        c = f['classified']
        self.assertEqual(c['variation_classes_cents'], {'approved': 100000, 'unapproved': 700000, 'disputed': 0, 'rejected': 9000})
        self.assertEqual(c['variation_refs']['unapproved'], ['V-S', 'V-U'])
        self.assertEqual([x['ref'] for x in f['contributed']], ['contract/PRJ-001', 'variation/V-A'])
        self.assertIn('NOT in secured revenue', ' '.join(f['limits']))

    def test_a_submitted_variation_is_never_secured_even_if_large(self):
        m = world()
        m.variations(var('V-S', status='submitted', value='999999999'))
        self.assertEqual(rev(m)['value']['cents'], 10000000)

    def test_disputed_variation_is_listed_as_disputed_and_makes_the_figure_provisional(self):
        m = world(); m.set_policy(variation_status_map={'approved': 'approved', 'contested': 'disputed', 'submitted': 'unapproved'})
        m.variations(var('V-D', status='contested', value='500'))
        f = rev(m)
        self.assertEqual((f['state'], f['value']['cents'], f['classified']['variation_classes_cents']['disputed']), (PROV, 10000000, 500))
        self.assertEqual(f['disputed'][0]['ref'], 'variation/V-D')

    def test_approved_but_unpriced_variation_means_revenue_is_not_fully_known(self):
        m = world()
        m.variations(var('V-A', status='approved', value=''))
        f = rev(m)
        self.assertEqual((f['state'], f['value']['cents']), (PROV, 10000000))
        self.assertEqual(f['classified']['variation_refs']['approved_unpriced'], ['V-A'])
        self.assertTrue(f['unknown_inputs'])

    def test_unmapped_status_is_left_out_and_unknown(self):
        m = world()
        m.variations(var('V-X', status='pending legal', value='100'))
        f = rev(m)
        self.assertEqual(f['state'], PROV)
        self.assertEqual(f['excluded'][0]['codes'], ['VARIATION_STATUS_UNMAPPED:pending legal'])
        self.assertIn('CR-02 A12', f['unknown_inputs'][0]['decision'])

    def test_summary_and_register_disagree_both_are_disputed_register_is_used(self):
        m = world(summary='0')
        m.variations(var('V-A', status='approved', value='1200000'))
        f = rev(m)
        self.assertEqual((f['state'], f['value']['cents']), (PROV, 11200000))
        self.assertIn('CONTRACT_SUMMARY_DISAGREES_WITH_REGISTER', f['reasons'])
        self.assertEqual(sorted(d['ref'] for d in f['disputed']), ['contract/PRJ-001', 'variation/*'])

    def test_exact_equality_is_required_when_no_tolerance_is_configured_and_a_configured_one_is_honoured(self):
        m = world(summary='1199999')
        m.variations(var('V-A', status='approved', value='1200000'))
        self.assertEqual(rev(m)['state'], PROV)                                           # one cent apart, no tolerance: disputed (interpretation I-17)
        m.set_policy(reconciliation_tolerance_cents=1)
        self.assertEqual(rev(m)['state'], AUTH)                                           # the policy owner's own tolerance, not a built-in one
        m.set_policy(reconciliation_tolerance_cents=0)
        self.assertEqual(rev(m)['state'], PROV)

    def test_missing_summary_is_unknown_not_zero(self):
        m = world(summary='')
        m.variations(var('V-A', status='approved', value='5'))
        f = rev(m)
        self.assertEqual((f['state'], f['value']['cents']), (PROV, 10000005))
        self.assertTrue(any('approved_variations_cents' in u['input'] for u in f['unknown_inputs']))

    def test_project_master_disagreeing_with_the_contract_is_disputed(self):
        m = Mini()
        m.projects(['PRJ-001', 'P1', '9000000', '2026-01-01', '2027-01-01'])
        m.contracts(['PRJ-001', '10000000', '0'])
        f = rev(m)
        self.assertEqual((f['state'], len(f['disputed'])), (PROV, 2))

    def test_variation_raised_after_the_as_of_date_is_outside_the_period(self):
        m = world()
        m.variations(var('V-A', raised='2026-10-01', status='approved', value='100'))
        m.reconcile()
        f = rev(m, as_of='2026-09-30')
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 10000000))
        self.assertEqual(f['excluded'][0]['class'], 'after_cutoff')

    def test_other_projects_variations_are_not_included(self):
        m = world()
        m.variations(var('V-A', project='PRJ-002', status='approved', value='100'))
        self.assertEqual(rev(m)['value']['cents'], 10000000)

    def test_no_contract_means_no_figure(self):
        m = Mini()
        f = rev(m)
        self.assertEqual((f['state'], f['value']['cents']), (CANT, None))
        self.assertEqual(f['unknown_inputs'][0]['input'], 'contract/PRJ-001')

    def test_conflicting_contract_records_are_disputed_and_unusable(self):
        m = Mini()
        m.contracts(['PRJ-001', '10000000', '0'])
        m.fin('TPL-BZ-CONTRACTS', csvb(CON_H, [['PRJ-001', '12000000', '0']]), 'commercial', name='b.csv')
        f = rev(m)
        self.assertEqual((f['state'], f['value']['cents']), (CANT, None))
        self.assertEqual(f['excluded'][0]['class'], 'disputed')
        self.assertEqual(len(f['disputed']), 1)

    def test_held_contract_is_not_used(self):
        m = Mini()
        m.contracts(['PRJ-001', '-5', '0'])
        f = rev(m)
        self.assertEqual(f['state'], CANT)
        self.assertEqual(f['excluded'][0]['codes'], ['SIGN_CONVENTION:original_contract_cents'])

    def test_conflicting_variation_is_disputed_and_not_counted(self):
        m = world()
        m.variations(var('V-A', status='approved', value='100'))
        m.variations(var('V-A', status='approved', value='999'))
        f = rev(m)
        self.assertEqual((f['state'], f['value']['cents']), (PROV, 10000000))
        self.assertEqual(f['disputed'][0]['ref'], 'variation/V-A')

    def test_tax_basis_must_be_configured_mixing_bases_is_refused(self):
        m = world(); m.set_policy(tax_basis=None)
        f = rev(m)
        self.assertEqual((f['state'], f['value']['cents']), (CANT, None))
        self.assertIn('CR-02 A6', f['unknown_inputs'][0]['decision'])

    def test_inc_gst_revenue_is_converted_exactly_with_the_policy_rate(self):
        m = world(); m.set_policy(tax_basis='inc_gst', gst_rate_bps=1000)
        f = rev(m)
        self.assertEqual(f['value']['cents'], 9090909)                                    # 10,000,000 / 1.10 = 9,090,909.09 -> rounded once, half away from zero
        self.assertIn('CONVERTED_FROM_INC_GST_AT_POLICY_RATE', f['reasons'])
        m.set_policy(tax_basis='inc_gst', gst_rate_bps=0)
        self.assertEqual(rev(m)['value']['cents'], 10000000)
        m.set_policy(tax_basis='inc_gst', gst_rate_bps=None)
        self.assertEqual(rev(m)['state'], CANT)

    def test_variation_status_map_not_configured_cannot_be_assessed(self):
        m = world(); m.set_policy(variation_status_map=None)
        f = rev(m)
        self.assertEqual(f['state'], CANT)
        self.assertIn('A12', f['unknown_inputs'][0]['decision'])

    def test_unapproved_policy_is_provisional(self):
        self.assertEqual(rev(world(approved=False))['state'], PROV)


if __name__ == '__main__':
    unittest.main()
