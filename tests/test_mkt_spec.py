import unittest
from . import _path                                         # noqa: F401
from .helpers_mkt import *
from apg.mkt import compare as CP, demo_mkt as DM, policy as MP, spec as SP

SPEC = MP.spec_view(DM.demo_mkt_spec())


def rd(value, verified=True, by='bob', ext='ai'):
    return {'value': value, 'verified': verified, 'extracted_by': ext, 'verified_by': by if verified else None, 'ref': 'quote_reading/x', 'revision': 1}


class TestAttributeCheck(unittest.TestCase):
    def chk(self, req, offer, readings=None, kind='quote'):
        return SP.attribute_check(SPEC, req, offer, readings or {}, kind)

    def test_a_verified_reading_that_meets_every_required_attribute_passes_as_verified(self):
        r = self.chk('MAT-STEEL', 'MAT-STEEL', {'grade': rd('300PLUS'), 'section': rd('250UB')})
        self.assertEqual((r['status'], r['verified']), ('pass', True))
        self.assertTrue(all(a['source'] == 'verified_reading' for a in r['attributes']))

    def test_the_catalogue_code_alone_cannot_vouch_for_a_suppliers_quote(self):
        r = self.chk('MAT-STEEL', 'MAT-STEEL')
        self.assertEqual((r['status'], r['verified']), ('pass', False))
        self.assertTrue(all(a['source'] == 'catalogue' for a in r['attributes']))

    def test_the_catalogue_code_does_vouch_for_a_purchase_order_rate(self):
        r = self.chk('MAT-STEEL', 'MAT-STEEL', kind='purchase_order')
        self.assertEqual((r['status'], r['verified']), ('pass', True))

    def test_a_lower_strength_fails_from_the_catalogue_alone(self):
        r = self.chk('MAT-CONC40', 'MAT-CONC32')
        self.assertEqual(r['status'], 'fail')
        (a,) = r['attributes']
        self.assertEqual((a['attribute'], a['match'], a['required'], a['offered'], a['result']), ('strength_mpa', 'at_least', 40, 32, 'fail'))
        self.assertIn('32 offered against 40 required (at_least)', r['reasons'][0])

    def test_a_higher_strength_meets_an_at_least_requirement_and_a_lower_one_does_not_meet_it_the_other_way(self):
        self.assertEqual(self.chk('MAT-CONC32', 'MAT-CONC40', {'strength_mpa': rd('40')})['status'], 'pass')
        self.assertEqual(self.chk('MAT-CONC40', 'MAT-CONC32', {'strength_mpa': rd('32')})['status'], 'fail')

    def test_different_product_families_fail(self):
        r = self.chk('MAT-STEEL', 'MAT-PBOARD')
        self.assertEqual(r['status'], 'fail')
        self.assertIn('different product families', r['reasons'][0])

    def test_a_material_missing_from_the_register_is_unknown_not_a_pass(self):
        r = self.chk('MAT-STEEL', 'MAT-UNLISTED')
        self.assertEqual((r['status'], r['verified']), ('unknown', False))
        self.assertIn('MAT-UNLISTED is not in the specification register', r['reasons'][0])
        self.assertEqual(self.chk('MAT-UNLISTED', 'MAT-STEEL')['status'], 'unknown')

    def test_a_verified_reading_that_contradicts_the_catalogue_fails_on_the_reading_and_says_so(self):
        r = self.chk('MAT-STEEL', 'MAT-STEEL', {'grade': rd('350'), 'section': rd('250UB')})
        self.assertEqual(r['status'], 'fail')
        self.assertTrue(any('disagrees with the catalogue' in x for x in r['reasons']))

    def test_an_unverified_reading_never_decides_alone_and_the_catalogue_value_is_used(self):
        r = self.chk('MAT-STEEL', 'MAT-STEEL', {'grade': rd('350', verified=False), 'section': rd('250UB', verified=False)})
        self.assertEqual((r['status'], r['verified']), ('pass', False))
        self.assertTrue(all(a['source'] == 'catalogue' for a in r['attributes']))

    def test_with_no_catalogue_value_an_unverified_reading_is_shown_but_passes_nothing(self):
        spec = MP.spec_view(MP.new_spec('S', 'p', families={'f': {'attributes': {'a': {'match': 'exact'}}}}, materials={'REQ': {'family': 'f', 'attributes': {'a': 'x'}, 'unit': 'u'},
                                                                                                                              'OFF': {'family': 'f', 'attributes': {}, 'unit': 'u'}}))
        r = SP.attribute_check(spec, 'REQ', 'OFF', {'a': rd('x', verified=False)}, 'quote')
        self.assertEqual((r['status'], r['attributes'][0]['result'], r['attributes'][0]['source']), ('unknown', 'unknown', 'unverified_reading'))
        r2 = SP.attribute_check(spec, 'REQ', 'OFF', {'a': rd('x')}, 'quote')
        self.assertEqual((r2['status'], r2['verified']), ('pass', True))
        r3 = SP.attribute_check(spec, 'REQ', 'OFF', {}, 'quote')
        self.assertEqual(r3['status'], 'unknown')                                            # nothing usable offered: unknown on both sides

    def test_a_numeric_attribute_read_as_a_non_whole_number_cannot_be_used(self):
        r = self.chk('MAT-CONC32', 'MAT-CONC40', {'strength_mpa': rd('40.5')})
        self.assertEqual(r['attributes'][0]['source'], 'catalogue')


class TestUnitCheck(unittest.TestCase):
    def test_a_verified_unit_equal_to_the_required_unit_is_same(self):
        u = SP.unit_check(SPEC, 'MAT-STEEL', 'MAT-STEEL', {'unit': rd('tonne')}, 'tonne', 'tonne')
        self.assertEqual((u['status'], u['inferred']), ('same', False))

    def test_an_unrecorded_unit_is_only_inferred_and_is_unverified(self):
        u = SP.unit_check(SPEC, 'MAT-STEEL', 'MAT-STEEL', {}, 'tonne', 'tonne')
        self.assertEqual((u['status'], u['inferred']), ('unverified', True))
        self.assertIn('inferred from the material master', u['why'])

    def test_a_different_unit_with_no_declared_conversion_is_incompatible(self):
        u = SP.unit_check(SPEC, 'MAT-STEEL', 'MAT-STEEL', {'unit': rd('kg')}, 'tonne', 'tonne')
        self.assertEqual(u['status'], 'incompatible')

    def test_a_declared_conversion_is_applied_only_on_a_verified_unit(self):
        spec = MP.spec_view(DM.demo_mkt_spec(unit_conversions=[{'material': 'MAT-STEEL', 'from_unit': 'kg', 'to_unit': 'tonne', 'factor_micro': 1000}]))
        v = SP.unit_check(spec, 'MAT-STEEL', 'MAT-STEEL', {'unit': rd('kg')}, 'tonne', 'tonne')
        self.assertEqual((v['status'], v['factor_micro']), ('converted', 1000))
        u = SP.unit_check(spec, 'MAT-STEEL', 'MAT-STEEL', {'unit': rd('kg', verified=False)}, 'tonne', 'tonne')
        self.assertEqual((u['status'], u['inferred'], u['from']), ('unverified', True, 'tonne'))   # an unverified reading is ignored: the register's unit stands, as an inference

    def test_no_unit_anywhere_is_unverified_not_assumed(self):
        u = SP.unit_check(SPEC, 'MAT-X', 'MAT-Y', {}, None, None)
        self.assertEqual(u['status'], 'unverified')


class TestClassify(unittest.TestCase):
    OK_ATTR = {'status': 'pass', 'verified': True, 'reasons': [], 'attributes': []}
    SAME = {'status': 'same', 'factor_micro': 1_000_000, 'why': ''}
    COMM = {'adjustments': [], 'unquantified': []}

    def c(self, attr=None, unit=None, comm=None, spec_ok=True, req_ok=True, kind='quote'):
        return SP.classify(spec_ok, attr or self.OK_ATTR, unit or self.SAME, comm or self.COMM, req_ok, kind)

    def test_the_five_classes(self):
        self.assertEqual(self.c()[0], 'comparable')
        self.assertEqual(self.c(comm={'adjustments': [{'kind': 'freight_added'}], 'unquantified': []})[0], 'comparable_with_adjustment')
        self.assertEqual(self.c(unit={'status': 'converted', 'factor_micro': 1000, 'why': ''})[0], 'comparable_with_adjustment')
        self.assertEqual(self.c(attr=dict(self.OK_ATTR, verified=False))[0], 'partially_comparable')
        self.assertEqual(self.c(attr={'status': 'fail', 'reasons': ['x'], 'verified': False})[0], 'not_comparable')
        self.assertEqual(self.c(attr={'status': 'unknown', 'reasons': ['y'], 'verified': False})[0], 'unverified')

    def test_an_unapproved_register_or_requirement_makes_everything_unverified_even_a_perfect_match(self):
        self.assertEqual(self.c(spec_ok=False)[:2], ('unverified', ['SPEC_REGISTER_UNAPPROVED']))
        self.assertEqual(self.c(req_ok=False)[:2], ('unverified', ['REQUIREMENT_UNAPPROVED']))

    def test_a_failure_outranks_every_other_condition(self):
        cls, codes, _ = self.c(attr={'status': 'fail', 'reasons': ['x'], 'verified': False}, unit={'status': 'unverified', 'why': 'u', 'factor_micro': None}, comm={'adjustments': [], 'unquantified': [('COMPONENT_MISSING:freight', 'f')]})
        self.assertEqual((cls, codes), ('not_comparable', ['ATTRIBUTE_FAILS']))
        self.assertEqual(self.c(unit={'status': 'incompatible', 'why': 'u', 'factor_micro': None})[:2], ('not_comparable', ['UNIT_INCOMPATIBLE']))

    def test_every_unquantified_commercial_item_adds_a_stable_code_and_a_reason(self):
        cls, codes, reasons = self.c(attr=dict(self.OK_ATTR, verified=False), unit={'status': 'unverified', 'why': 'inferred', 'factor_micro': None},
                                     comm={'adjustments': [], 'unquantified': [('BASIS_NOT_IN_TABLE', 'b'), ('COMPONENT_MISSING:duty', 'd')]})
        self.assertEqual((cls, codes), ('partially_comparable', ['QUOTE_TEXT_UNVERIFIED', 'UNIT_UNVERIFIED', 'BASIS_NOT_IN_TABLE', 'COMPONENT_MISSING:duty']))
        self.assertEqual(len(reasons), 4)


class TestGateEndToEnd(unittest.TestCase):
    """The gate as the run applies it: real quotes, readings and register through the real intake."""

    def setup(self, quotes, readings=(), spec_kw=None, approved=True, reqs=True):
        m = mkt_world(approved=approved)
        if spec_kw is not None:
            m.set_spec(**spec_kw)
        m.quote_rows(*quotes)
        if readings:
            m.readings(*readings)
        m.demands(demand('DEM-1', 'PRJ-001', 'MAT-STEEL', '100', 'tonne', '2026-12-01'))
        return m

    def offer(self, m, qkey='Q-1'):
        ctx = m.ctx()
        (req,) = CP.requirements(ctx)
        return CP.eval_quote(ctx, ctx.quotes[qkey], req, 'quote_ranking'), req

    Q = quote('Q-1', 'SUP-001', 'MAT-STEEL', 'Grade 300PLUS 250UB', '2026-09-10', '2026-10-31', '265000', basis='delivered')

    def test_verified_readings_domestic_delivered_is_comparable(self):
        m = self.setup([self.Q], std_readings('Q-1'))
        o, _ = self.offer(m)
        self.assertEqual((o['gate']['class'], o['gate']['codes'], o['blockers'], o['definitive_ok']), ('comparable', [], [], True))

    def test_ex_works_with_freight_stated_is_comparable_with_adjustment_and_the_adjustment_is_recorded(self):
        q = quote('Q-1', 'SUP-001', 'MAT-STEEL', 's', '2026-09-10', '2026-10-31', '247000', freight='9500', basis='ex-works')
        m = self.setup([q], std_readings('Q-1'))
        o, _ = self.offer(m)
        self.assertEqual(o['gate']['class'], 'comparable_with_adjustment')
        self.assertEqual([(a['kind'], a['cents']) for a in o['gate']['adjustments']], [('freight_added', 9500)])
        self.assertEqual(o['landed']['unit_cents'], 256500)

    def test_unverified_text_is_partially_comparable_and_never_definitive(self):
        m = self.setup([self.Q])
        o, _ = self.offer(m)
        self.assertEqual(o['gate']['class'], 'partially_comparable')
        self.assertIn('QUOTE_TEXT_UNVERIFIED', o['gate']['codes'])
        self.assertIn('UNIT_UNVERIFIED', o['gate']['codes'])
        self.assertFalse(o['definitive_ok'])
        self.assertTrue(o['rankable'])

    def test_a_reading_verified_by_the_person_who_extracted_it_is_not_verified(self):
        rows = [reading('Q-1', a, v, by='carol', verified_by='carol') for a, v in (('grade', '300PLUS'), ('section', '250UB'), ('unit', 'tonne'))]
        m = self.setup([self.Q], rows)
        o, _ = self.offer(m)
        self.assertEqual(o['gate']['class'], 'partially_comparable')

    def test_a_reading_with_a_verifier_but_no_date_is_not_verified(self):
        rows = [reading('Q-1', a, v, verified_by='alice', verified_on='') for a, v in (('grade', '300PLUS'), ('section', '250UB'), ('unit', 'tonne'))]
        m = self.setup([self.Q], rows)
        o, _ = self.offer(m)
        self.assertEqual(o['gate']['class'], 'partially_comparable')

    def test_a_cheaper_quote_for_the_wrong_strength_is_not_comparable_even_with_no_reading(self):
        m = mkt_world()
        m.quote_rows(quote('Q-3', 'SUP-001', 'MAT-CONC32', 'Concrete 32 MPa', '2026-09-05', '2026-10-31', '27000'))
        m.spec_reqs(['SR-1', 'PRJ-001', 'MAT-CONC40', 'DWG', 'alice', '2026-01-01'])
        ctx = m.ctx()
        (req,) = CP.requirements(ctx)
        o = CP.eval_quote(ctx, ctx.quotes['Q-3'], req, 'quote_ranking')
        self.assertEqual((o['gate']['class'], o['gate']['codes']), ('not_comparable', ['ATTRIBUTE_FAILS']))
        self.assertFalse(o['rankable'] and o['definitive_ok'])
        self.assertIn('SUBSTITUTION_NEEDS_APPROVAL', o['blockers'])

    def test_a_quote_for_another_unit_with_no_declared_conversion_is_not_comparable(self):
        rows = [reading('Q-1', 'grade', '300PLUS'), reading('Q-1', 'section', '250UB'), reading('Q-1', 'unit', 'kg')]
        m = self.setup([self.Q], rows)
        o, _ = self.offer(m)
        self.assertEqual((o['gate']['class'], o['gate']['codes']), ('not_comparable', ['UNIT_INCOMPATIBLE']))

    def test_a_declared_unit_conversion_rescales_the_price_and_is_an_adjustment(self):
        q = quote('Q-1', 'SUP-001', 'MAT-STEEL', 's', '2026-09-10', '2026-10-31', '265', basis='delivered')
        rows = [reading('Q-1', 'grade', '300PLUS'), reading('Q-1', 'section', '250UB'), reading('Q-1', 'unit', 'kg')]
        m = self.setup([q], rows, spec_kw=dict(unit_conversions=[{'material': 'MAT-STEEL', 'from_unit': 'kg', 'to_unit': 'tonne', 'factor_micro': 1000}]))
        o, _ = self.offer(m)
        self.assertEqual((o['gate']['class'], o['landed']['unit_cents']), ('comparable_with_adjustment', 265000))      # 265 per kg x 1000 kg per tonne
        self.assertEqual(o['landed']['unit_conversion']['factor_micro'], 1000)
        self.assertIn('unit_converted', [a['kind'] for a in o['gate']['adjustments']])

    def test_an_unapproved_register_makes_the_quote_unverified(self):
        m = self.setup([self.Q], std_readings('Q-1'), approved=False)
        o, _ = self.offer(m)
        self.assertEqual((o['gate']['class'], o['gate']['codes']), ('unverified', ['SPEC_REGISTER_UNAPPROVED']))
        self.assertFalse(o['rankable'])

    def test_a_standing_requirement_no_person_approved_makes_the_quote_unverified(self):
        m = mkt_world()
        m.quote_rows(quote('Q-3', 'SUP-001', 'MAT-CONC40', 's', '2026-09-05', '2026-10-31', '27000'))
        m.spec_reqs(['SR-1', 'PRJ-001', 'MAT-CONC40', 'DWG', '', ''])
        ctx = m.ctx()
        (req,) = CP.requirements(ctx)
        self.assertFalse(req['approved'])
        o = CP.eval_quote(ctx, ctx.quotes['Q-3'], req, 'quote_ranking')
        self.assertEqual(o['gate']['codes'], ['REQUIREMENT_UNAPPROVED'])

    def test_a_substitute_in_the_same_family_needs_approval_and_is_flagged_even_when_every_attribute_passes(self):
        m = mkt_world()
        m.quote_rows(quote('Q-4', 'SUP-001', 'MAT-CONC40', 's', '2026-09-05', '2026-10-31', '34000'))
        m.readings(reading('Q-4', 'strength_mpa', '40'), reading('Q-4', 'unit', 'm3'))
        m.spec_reqs(['SR-1', 'PRJ-001', 'MAT-CONC32', 'DWG', 'alice', '2026-01-01'])
        ctx = m.ctx()
        (req,) = CP.requirements(ctx)
        o = CP.eval_quote(ctx, ctx.quotes['Q-4'], req, 'quote_ranking')
        self.assertEqual(o['gate']['class'], 'comparable')
        self.assertTrue(o['substitution'])
        self.assertIn('SUBSTITUTION_NEEDS_APPROVAL', o['blockers'])
        self.assertFalse(o['definitive_ok'])

    def test_a_held_supporting_reading_blocks_a_definitive_result(self):
        rows = std_readings('Q-1') + [reading('Q-1', 'grade', '350', verified_by='alice')]            # a conflicting second reading of the grade
        m = self.setup([self.Q], rows)
        o, _ = self.offer(m)
        self.assertIn('HELD_SUPPORTING_RECORDS', o['blockers'])
        self.assertFalse(o['definitive_ok'])

    def test_a_purchase_order_reference_is_never_more_than_partially_comparable(self):
        m = self.setup([self.Q], std_readings('Q-1'))
        m.orders(pom('PO-1', mat='MAT-STEEL', qty='10', rate='250000', date='2026-08-01'))
        ctx = m.ctx()
        (req,) = CP.requirements(ctx)
        ref = CP.last_paid(ctx, req)
        self.assertEqual((ref['gate']['class'], ref['gate']['codes'], ref['blockers'], ref['rankable']), ('partially_comparable', ['REFERENCE_BASIS_UNRECORDED'], ['REFERENCE_ONLY'], False))


if __name__ == '__main__':
    unittest.main()
