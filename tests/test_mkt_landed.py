import unittest
from . import _path                                         # noqa: F401
from .helpers_mkt import *
from apg.mkt import landed as LD

M = 1_000_000


def comp(ul, name):
    return next(c for c in ul['components'] if c['component'] == name)


class TestLanded(unittest.TestCase):
    def world(self, *quotes, fxr=(), asm=(), tiers=(), terms=(), **mk):
        m = mkt_world()
        if mk:
            m.drop(*mk.get('drop', ())) if mk.get('drop') else m.set_mkt(**mk.get('over', {}))
        m.quote_rows(*quotes)
        if fxr:
            m.fx(*fxr)
        if asm:
            m.assumptions(*asm)
        if tiers:
            m.tiers(*tiers)
        if terms:
            m.terms(*terms)
        return m

    def ul(self, m, key='Q-1', qty=None):
        a = m.analysis()
        return LD.unit_landed(a.F, a.mp, a.ctx.quotes[key], '2026-09-30', qty)

    DEL = quote('Q-1', 'SUP-001', 'MAT-STEEL', 's', '2026-09-10', '2026-10-31', '265000', basis='delivered')
    EXW = quote('Q-1', 'SUP-001', 'MAT-STEEL', 's', '2026-09-10', '2026-10-31', '247000', freight='9500', basis='ex-works')
    FOB = quote('Q-1', 'SUP-004', 'MAT-STEEL', 's', '2026-05-02', '2026-11-30', '6900', cur='USD', fx='0.6612', fxd='2026-05-02', freight='800', basis='FOB', lead='56')

    def test_a_delivered_rate_includes_freight_and_handling_and_is_complete(self):
        u = self.ul(self.world(self.DEL))
        self.assertEqual((u['unit_cents'], u['complete'], u['missing'], u['international']), (265000, True, [], False))
        self.assertEqual([(c['component'], c['status']) for c in u['components']],
                         [('purchase', 'known'), ('freight', 'included_in_rate'), ('insurance', 'not_required'), ('duty', 'not_required'), ('clearance', 'not_required'), ('handling', 'included_in_rate')])
        self.assertEqual(u['tax_treatment'], 'ex_gst')

    def test_freight_stated_on_a_basis_that_already_includes_it_is_not_added_again(self):
        q = quote('Q-1', 'SUP-001', 'MAT-STEEL', 's', '2026-09-10', '2026-10-31', '265000', freight='9500', basis='delivered')
        u = self.ul(self.world(q))
        self.assertEqual(u['unit_cents'], 265000)
        self.assertTrue(any('not added again' in x for x in u['limits']))

    def test_ex_works_with_stated_freight_adds_it_and_is_complete(self):
        u = self.ul(self.world(self.EXW))
        self.assertEqual((u['unit_cents'], u['complete']), (256500, True))
        self.assertEqual((comp(u, 'freight')['status'], comp(u, 'freight')['cents']), ('stated', 9500))
        self.assertEqual(comp(u, 'handling')['status'], 'not_required')

    def test_ex_works_with_no_freight_is_incomplete_and_the_known_part_is_a_lower_bound(self):
        q = quote('Q-1', 'SUP-001', 'MAT-STEEL', 's', '2026-09-10', '2026-10-31', '247000', freight='', basis='ex-works')
        u = self.ul(self.world(q))
        self.assertEqual((u['unit_cents'], u['complete'], u['missing']), (247000, False, ['freight']))
        self.assertEqual(comp(u, 'freight')['status'], 'missing')
        self.assertIsNone(comp(u, 'freight')['cents'])                                       # never a silent zero

    def test_zero_freight_that_the_supplier_stated_is_a_stated_zero_not_a_missing_value(self):
        q = quote('Q-1', 'SUP-001', 'MAT-STEEL', 's', '2026-09-10', '2026-10-31', '247000', freight='0', basis='ex-works')
        u = self.ul(self.world(q))
        self.assertEqual((comp(u, 'freight')['status'], comp(u, 'freight')['cents'], u['complete']), ('stated', 0, True))

    def test_a_delivery_basis_not_in_the_policy_table_is_incomplete_and_says_what_is_unknown(self):
        q = quote('Q-1', 'SUP-001', 'MAT-STEEL', 's', '2026-09-10', '2026-10-31', '265000', basis='dap')
        u = self.ul(self.world(q))
        self.assertFalse(u['complete'])
        self.assertTrue(any("'dap' is not in the policy table" in x for x in u['limits']))

    def test_an_international_quote_converts_every_part_at_the_reference_rate_and_lists_what_is_missing(self):
        m = self.world(self.FOB, fxr=[fxrow('2026-09-30', '0.6540')], asm=[['Q-1', 'insurance', '150', '', 'USD', 'allowance', 'none', 'alice', '2026-09-20']])
        u = self.ul(m)
        self.assertTrue(u['international'])
        self.assertEqual(comp(u, 'purchase')['cents'], 10550)                                # 6900 / 0.6540
        self.assertEqual((comp(u, 'freight')['status'], comp(u, 'freight')['cents']), ('stated', 1223))      # 800 / 0.6540 = 1223.24
        self.assertEqual((comp(u, 'insurance')['status'], comp(u, 'insurance')['cents']), ('assumed', 229))  # 150 / 0.6540 = 229.36
        self.assertEqual((comp(u, 'duty')['status'], comp(u, 'clearance')['status']), ('missing', 'missing'))
        self.assertEqual((u['unit_cents'], u['complete'], u['missing']), (12002, False, ['duty', 'clearance']))
        self.assertEqual((u['conversion']['rate_date'], u['stated_conversion']['rate_micro']), ('2026-09-30', 661200))

    def test_the_freight_currency_policy_decides_whether_stated_freight_is_converted(self):
        base = dict(DM.demo_mkt_fields()['basis'], freight_currency='aud')
        m = mkt_world()
        m.set_mkt(basis=base)
        m.quote_rows(self.FOB)
        m.fx(fxrow('2026-09-30', '0.6540'))
        u = self.ul(m)
        self.assertEqual((comp(u, 'freight')['status'], comp(u, 'freight')['cents']), ('stated', 800))

    def test_without_a_usable_rate_the_purchase_price_is_missing_not_zero_and_nothing_is_guessed(self):
        u = self.ul(self.world(self.FOB))
        self.assertEqual(comp(u, 'purchase')['status'], 'missing')
        self.assertIsNone(comp(u, 'purchase')['cents'])
        self.assertEqual(comp(u, 'freight')['status'], 'missing')
        self.assertFalse(u['complete'])
        self.assertEqual(u['unit_cents'], 0)

    def test_a_duty_assumption_in_basis_points_is_applied_to_the_converted_purchase_cost(self):
        m = self.world(self.FOB, fxr=[fxrow('2026-09-30', '0.6540')], asm=[['Q-1', 'duty', '', '500', '', 'rate', 'ref', 'alice', '2026-09-20']])
        d = comp(self.ul(m), 'duty')
        self.assertEqual((d['status'], d['cents']), ('assumed', 528))                        # 5% of 10550 = 527.5, half away from zero

    def test_an_assumption_nobody_signed_is_held_and_the_component_stays_missing(self):
        m = self.world(self.FOB, fxr=[fxrow('2026-09-30', '0.6540')], asm=[['Q-1', 'duty', '', '500', '', 'rate', 'ref', '', '']])
        u = self.ul(m)
        self.assertEqual(comp(u, 'duty')['status'], 'missing')
        self.assertEqual([h['why'] for h in u['held']], [['ASSUMPTION_INVALID_OR_UNSIGNED']])

    def test_an_assumption_with_both_a_per_unit_amount_and_a_rate_is_ambiguous_and_held(self):
        m = self.world(self.FOB, fxr=[fxrow('2026-09-30', '0.6540')], asm=[['Q-1', 'duty', '100', '500', '', 'x', 'ref', 'alice', '2026-09-20']])
        self.assertEqual(comp(self.ul(m), 'duty')['status'], 'missing')

    def test_a_rate_based_assumption_is_only_for_duty(self):
        m = self.world(self.FOB, fxr=[fxrow('2026-09-30', '0.6540')], asm=[['Q-1', 'insurance', '', '300', '', 'x', 'ref', 'alice', '2026-09-20']])
        u = self.ul(m)
        self.assertEqual(comp(u, 'insurance')['status'], 'missing')
        self.assertEqual([h['why'] for h in u['held']], [['RATE_ONLY_FOR_DUTY']])

    def test_a_tier_applies_from_its_minimum_quantity_and_not_a_unit_before(self):
        m = self.world(self.DEL, tiers=[['Q-1', '100', '262000']])
        self.assertEqual(self.ul(m, qty=100 * M)['unit_cents'], 262000)
        self.assertEqual(self.ul(m, qty=100 * M - 1)['unit_cents'], 265000)
        self.assertEqual(self.ul(m, qty=None)['unit_cents'], 265000)
        self.assertEqual(self.ul(m, qty=100 * M)['tier']['min_quantity_micro'], 100 * M)

    def test_purchase_plan_applies_minimum_order_and_pack_size_and_prices_what_is_actually_bought(self):
        m = self.world(self.DEL, terms=[['Q-1', 'moq', '10'], ['Q-1', 'pack_size', '5']])
        a = m.analysis()
        q = a.ctx.quotes['Q-1']
        p = LD.purchase_plan(a.F, a.mp, q, '2026-09-30', 3 * M)['plain']
        self.assertEqual((p['buy_qty_micro'], p['surplus_qty_micro'], p['total_cents']), (10 * M, 7 * M, 2_650_000))
        self.assertEqual(p['effective_unit_cents_of_need'], 883333)                          # 2,650,000 / 3, rounded once
        p2 = LD.purchase_plan(a.F, a.mp, q, '2026-09-30', 11 * M)['plain']
        self.assertEqual((p2['buy_qty_micro'], p2['surplus_qty_micro']), (15 * M, 4 * M))     # rounded up to a whole pack

    def test_a_larger_tier_is_shown_with_its_total_and_never_assumed_cheaper(self):
        m = self.world(self.DEL, tiers=[['Q-1', '100', '262000']])
        a = m.analysis()
        plan = LD.purchase_plan(a.F, a.mp, a.ctx.quotes['Q-1'], '2026-09-30', 40 * M)
        self.assertEqual(plan['plain']['total_cents'], 10_600_000)
        (opt,) = plan['larger_orders']
        self.assertEqual((opt['buy_qty_micro'], opt['unit_cents'], opt['total_cents'], opt['surplus_qty_micro'], opt['extra_total_cents_vs_plain']), (100 * M, 262000, 26_200_000, 60 * M, 15_600_000))
        self.assertIn('total paid is higher', opt['note'])
        self.assertIn('surplus is not assumed reusable', opt['note'])

    def test_a_reference_order_rate_has_no_known_basis_and_is_never_complete(self):
        m = self.world(self.DEL)
        m.orders(pom('PO-1', rate='250000'))
        a = m.analysis()
        po = a.ctx.pos['PO-1']
        r = LD.reference_landed(po, a.mp)
        self.assertEqual((r['unit_cents'], r['complete'], r['basis_known']), (250000, False, False))
        self.assertIn('delivery basis of a purchase-order rate is not recorded', r['limits'][0])

    def test_rescaling_converts_every_component_and_keeps_the_factor_for_a_hand_check(self):
        u = self.ul(self.world(self.EXW))
        r = LD.rescale(u, 1000, 'kg', 'tonne')
        self.assertEqual(r['unit_cents'], 256500 * 1000)
        self.assertEqual(r['unit_conversion'], {'from_unit': 'kg', 'to_unit': 'tonne', 'factor_micro': 1000, 'rounding': 'each component rounded half away from zero once'})
        self.assertEqual(u['unit_cents'], 256500)                                            # the original record is not altered

    def test_held_tier_and_term_records_are_listed_on_the_landed_record(self):
        m = self.world(self.DEL, tiers=[['Q-1', '10', '0']])
        self.assertEqual([h['why'] for h in self.ul(m)['held']], [['SIGN_CONVENTION:unit_rate_minor_units']])

    def test_every_source_record_used_is_listed_with_its_revision(self):
        m = self.world(self.FOB, fxr=[fxrow('2026-09-30', '0.6540')], asm=[['Q-1', 'insurance', '150', '', 'USD', 'a', 'r', 'alice', '2026-09-20']])
        u = self.ul(m)
        refs = [s[0] for s in u['sources']]
        self.assertIn('supplier_quote/Q-1', refs)
        self.assertIn('landed_assumption/Q-1|insurance', refs)
        self.assertTrue(all(isinstance(s[1], int) and s[1] >= 1 for s in u['sources']))


if __name__ == '__main__':
    unittest.main()
