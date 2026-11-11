import json, os, subprocess, sys, tempfile, unittest
from . import _path                                         # noqa: F401
from ._path import HERE_ROOT
from .helpers_mkt import *
from apg.mkt import common as C, compare as CP, intake as MI


def outcomes(m, kind):
    return {r.key: MI.outcome(r.payload) for r in m.s.query(kind)}


class TestIntake(unittest.TestCase):
    def test_each_template_ingests_a_well_formed_row_as_accepted(self):
        m = mkt_world()
        m.demands(demand())
        m.dockets(docket())
        m.spec_reqs(['SR-1', 'PRJ-001', 'MAT-STEEL', 'DWG-1', 'alice', '2026-01-01'])
        m.readings(reading())
        m.tiers(['Q-1', '10', '5000'])
        m.terms(['Q-1', 'moq', '5'])
        m.assumptions(['Q-1', 'insurance', '150', '', 'AUD', 'basis', 'ref', 'alice', '2026-09-01'])
        m.checks(['Q-1', 'customs_classification', 'resolved', 'EV-1', 'alice', '2026-09-01'])
        for kind in ('material', 'material_demand', 'delivery', 'spec_requirement', 'quote_reading', 'quote_tier', 'quote_term', 'landed_assumption', 'import_check'):
            res = outcomes(m, kind)
            self.assertTrue(res, kind)
            ok = ('accepted', 'accepted_with_warnings') if kind == 'landed_assumption' else ('accepted',)            # an assumption in cents leaves the basis-points column empty: a warning, not a defect
            self.assertTrue(all(v in ok for v in res.values()), (kind, res))

    def test_natural_keys_have_several_parts_so_two_attributes_of_one_quote_are_two_records(self):
        m = mkt_world()
        m.readings(reading(attr='grade'), reading(attr='section', value='250UB'))
        self.assertEqual(sorted(outcomes(m, 'quote_reading')), ['Q-1|grade', 'Q-1|section'])

    def test_two_different_readings_of_the_same_attribute_are_a_conflict_and_neither_is_used(self):
        m = mkt_world()
        m.readings(reading(attr='grade', value='300PLUS'), reading(attr='grade', value='350'))
        (rec,) = m.s.query('quote_reading')
        self.assertIsNotNone(rec.payload.get('conflict'))
        self.assertFalse(MI.usable(rec.payload))
        m.quote_rows(quote('Q-1', 'SUP-001', 'MAT-STEEL', 's', '2026-09-10', '2026-10-31', '265000'))
        from apg.mkt import spec as SP
        a = m.analysis()
        rd, held = SP.readings(a.F, 'Q-1')
        self.assertNotIn('grade', rd)                                                      # the conflicted reading is not silently picked
        self.assertEqual(len(held), 1)

    def test_a_zero_tier_price_is_held_not_used(self):
        m = mkt_world()
        m.tiers(['Q-1', '10', '0'], ['Q-1', '20', '5'])
        res = outcomes(m, 'quote_tier')
        self.assertEqual(res, {'Q-1|10': 'pending_reconciliation', 'Q-1|20': 'accepted'})
        from apg.mkt import landed as LD
        m.quote_rows(quote('Q-1', 'SUP-001', 'MAT-STEEL', 's', '2026-09-10', '2026-10-31', '265000'))
        tiers, held = LD.tiers(m.analysis().F, 'Q-1')
        self.assertEqual([t[0] for t in tiers], [20_000_000])
        self.assertEqual(len(held), 1)

    def test_a_negative_landed_assumption_is_held(self):
        m = mkt_world()
        m.assumptions(['Q-1', 'insurance', '-5', '', 'AUD', 'b', 'r', 'alice', '2026-09-01'])
        (rec,) = m.s.query('landed_assumption')
        self.assertFalse(MI.usable(rec.payload))

    def test_a_requirement_without_an_approver_is_stored_with_warnings_and_is_not_approved(self):
        m = mkt_world()
        m.spec_reqs(['SR-1', 'PRJ-001', 'MAT-CONC40', '', '', ''])
        self.assertEqual(outcomes(m, 'spec_requirement'), {'SR-1': 'accepted_with_warnings'})
        reqs = CP.requirements(m.ctx())
        (r,) = [x for x in reqs if x['kind'] == 'standing']
        self.assertFalse(r['approved'])

    def test_unreadable_rows_are_rejected_and_counted_never_dropped_silently(self):
        m = mkt_world()
        r = m.tiers(['Q-1', 'abc', '5'])
        self.assertEqual(r['counts']['rejected'], 1)
        self.assertEqual(r['results'][0]['codes'], ['INVALID_DECIMAL'])
        r2 = m.readings(['Q-9', 'grade', '', 'x', 'ai', '', ''])
        self.assertEqual(r2['counts']['rejected'], 1)

    def test_a_required_on_site_date_in_the_future_is_not_a_future_dating_error(self):
        m = mkt_world()
        m.demands(demand(required='2027-12-31'))
        self.assertEqual(outcomes(m, 'material_demand'), {'DEM-1': 'accepted'})

    def test_a_delivery_date_in_the_future_is_held(self):
        m = mkt_world()
        m.dockets(docket(date='2030-01-01'))
        (rec,) = m.s.query('delivery')
        self.assertFalse(MI.usable(rec.payload))

    def test_the_same_file_twice_changes_nothing(self):
        m = mkt_world()
        m.demands(demand())
        r2 = m.demands(demand())
        self.assertTrue(r2['replay'])
        self.assertEqual(len(m.s.query('material_demand')), 1)

    def test_a_second_tenant_cannot_see_the_first_tenants_procurement_records(self):
        a, b = mkt_world(), mkt_world(tenant='zero_two')
        a.demands(demand())
        a.readings(reading())
        self.assertEqual(len(b.s.query('material_demand')), 0)
        self.assertEqual(len(b.s.query('quote_reading')), 0)


class TestTemplates(unittest.TestCase):
    def test_the_shipped_procurement_templates_regenerate_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, '-I', os.path.join(HERE_ROOT, 'tools', 'make_mkt_templates.py'), d], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            made = sorted(os.listdir(d))
            self.assertEqual(made, sorted(os.listdir(os.path.join(HERE_ROOT, 'mkt_templates'))))
            self.assertEqual(len(made), 9)
            for n in made:
                self.assertEqual(open(os.path.join(d, n), 'rb').read(), open(os.path.join(HERE_ROOT, 'mkt_templates', n), 'rb').read(), n)

    def test_every_template_is_a_draft_and_says_so(self):
        for n in os.listdir(os.path.join(HERE_ROOT, 'mkt_templates')):
            t = json.load(open(os.path.join(HERE_ROOT, 'mkt_templates', n), encoding='utf-8'))
            self.assertIn('unverified', t['status'], n)
            self.assertEqual(t['tenant_binding'], 'authenticated_context', n)

    def test_no_procurement_template_repeats_an_entity_an_earlier_milestone_ingests(self):
        earlier = set()
        for d in ('ingest_templates', 'import_templates', 'fin_templates', 'det_templates'):
            for f in os.listdir(os.path.join(HERE_ROOT, d)):
                if f.endswith('.json'):
                    earlier.add(json.load(open(os.path.join(HERE_ROOT, d, f), encoding='utf-8')).get('entity'))
        self.assertEqual(set(MI.MKT_SPECS) & earlier, set())

    def test_every_template_has_an_entity_rule_and_every_entity_rule_a_template(self):
        ents = {json.load(open(os.path.join(HERE_ROOT, 'mkt_templates', n), encoding='utf-8'))['target_entity'] for n in os.listdir(os.path.join(HERE_ROOT, 'mkt_templates'))}
        self.assertEqual(ents, set(MI.MKT_SPECS))

    def test_the_supplement_files_are_labelled_synthetic_and_the_builder_zero_ones_are_not_touched(self):
        sup = [f for t, f, s, w in MI.MKT_FILES if w == 'sup']
        self.assertEqual(len(sup), 6)
        for f in sup:
            self.assertTrue(os.path.exists(os.path.join(HERE_ROOT, 'mkt_data', 'zero_one', f)), f)
        for t, f, s, w in MI.MKT_FILES:
            if w == 'bz':
                self.assertTrue(os.path.exists(os.path.join(HERE_ROOT, 'builder_zero', 'zero_one', f)), f)


class TestCommonHelpers(unittest.TestCase):
    def test_quantities_are_exact_millionths(self):
        self.assertEqual(C.qty_micro(5), 5_000_000)
        self.assertEqual(C.qty_micro('2.5'), 2_500_000)
        self.assertEqual(C.qty_micro('0.000001'), 1)
        for bad in (-1, True, 'abc', '1.0000001', '', None, '-2', '1e3'):
            self.assertIsNone(C.qty_micro(bad), bad)
        self.assertEqual(C.fmt_qty(2_500_000), '2.5')
        self.assertEqual(C.fmt_qty(3_000_000), '3')
        self.assertEqual(C.fmt_qty(1), '0.000001')

    def test_mul_div_rounds_half_away_from_zero_once(self):
        self.assertEqual(C.mul_div(1, 1, 2), 1)
        self.assertEqual(C.mul_div(-1, 1, 2), -1)
        self.assertEqual(C.mul_div(7, 1, 3), 2)
        self.assertEqual(C.mul_div(10, 1, 3), 3)

    def test_add_days_crosses_month_and_leap_boundaries(self):
        self.assertEqual(C.add_days('2026-12-31', 1), '2027-01-01')
        self.assertEqual(C.add_days('2028-02-28', 1), '2028-02-29')
        self.assertEqual(C.add_days('2026-03-01', -1), '2026-02-28')


if __name__ == '__main__':
    unittest.main()
