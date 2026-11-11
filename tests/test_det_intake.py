import json, os, unittest
from . import _path                                         # noqa: F401
from ._path import HERE_ROOT
from .helpers_det import *                                  # noqa: F401,F403
from .helpers_det import DetMini, comp, hire, delay, defect, notice, COMP_H, HIRE_H, TS_H, WO_H, DEF_H, NOTICE_H, DELAY_H
from .helpers_ingest import csvb
from apg.det import intake as DI
from apg.ingest import mapping
from apg.ports import TenantMismatch


class TestDetIntake(unittest.TestCase):
    def setUp(self):
        self.m = DetMini(with_suppliers=False)

    def stored(self, kind, key):
        r = self.m.s.get(kind, key)
        return None if r is None else r.payload

    def test_every_template_is_valid_and_has_a_spec(self):
        names = sorted(os.listdir(os.path.join(HERE_ROOT, 'det_templates')))
        for t in names:
            d = json.load(open(os.path.join(HERE_ROOT, 'det_templates', t)))
            self.assertEqual(mapping.validate_template(d), [], t)
            self.assertIn(d['target_entity'], DI.DET_SPECS, t)
        self.assertEqual(len(names), len(DI.DET_SPECS))

    def test_template_ids_do_not_collide_with_earlier_milestones(self):
        seen = {}
        for d in ('import_templates', 'ingest_templates', 'fin_templates', 'det_templates'):
            for t in os.listdir(os.path.join(HERE_ROOT, d)):
                if t.endswith('.json'):
                    tid = json.load(open(os.path.join(HERE_ROOT, d, t)))['template_id']
                    self.assertNotIn(tid, seen, f'{tid} is in {d} and {seen.get(tid)}')
                    seen[tid] = d

    def test_every_template_marks_itself_a_draft_never_verified_against_a_real_export(self):
        for t in os.listdir(os.path.join(HERE_ROOT, 'det_templates')):
            self.assertIn('draft', json.load(open(os.path.join(HERE_ROOT, 'det_templates', t)))['status'])

    def test_compliance_record_is_stored_with_provenance_and_original_text(self):
        r = self.m.compliance(comp())
        self.assertEqual(r['counts']['new'], 1)
        p = self.stored('compliance', 'SUP-001|licence')
        self.assertEqual(p['fields'], {'supplier_ref': 'SUP-001', 'evidence_type_text': 'licence', 'expiry_date': '2027-12-31'})
        self.assertEqual(p['raw']['expiry_date'], '2027-12-31')
        self.assertEqual(p['provenance']['template_id'], 'TPL-BZ-COMPLIANCE')
        self.assertTrue(DI.usable(p))

    def test_same_file_twice_is_a_recorded_replay(self):
        self.m.compliance(comp())
        n = len(self.m.s.history('compliance', 'SUP-001|licence'))
        self.assertTrue(self.m.compliance(comp())['replay'])
        self.assertEqual(len(self.m.s.history('compliance', 'SUP-001|licence')), n)

    def test_different_content_for_one_key_with_no_order_is_a_quarantined_conflict(self):
        self.m.compliance(comp())
        r = self.m.det('TPL-BZ-COMPLIANCE', csvb(COMP_H, [comp(expiry='2028-01-01')]), 'compliance', 'b.csv')
        self.assertEqual(r['counts']['conflict'], 1)
        self.assertFalse(DI.usable(self.stored('compliance', 'SUP-001|licence')))

    def test_expiry_date_is_material_a_blank_one_holds_the_record(self):
        r = self.m.compliance(comp(expiry=''))
        self.assertEqual(r['counts']['rejected'] + r['counts']['held_at_intake'], 1)
        p = self.stored('compliance', 'SUP-001|licence')
        if p is not None:
            self.assertFalse(DI.usable(p))

    def test_an_expiry_in_the_future_is_not_held_as_future_dated(self):
        self.m.compliance(comp(expiry='2099-01-01'))
        self.assertTrue(DI.usable(self.stored('compliance', 'SUP-001|licence')))

    def test_plant_hire_blank_off_hire_is_unknown_not_a_date_and_only_a_warning(self):
        self.m.hires(hire())
        p = self.stored('plant_hire', 'H-1')
        self.assertTrue(DI.usable(p))
        self.assertNotIn('off_hire_date', p['fields'])
        self.assertIn('VALUE_MISSING:off_hire_date', p['intrinsic']['warnings'])

    def test_plant_hire_rate_zero_or_negative_is_held(self):
        for rate in ('0', '-5'):
            m = DetMini(with_suppliers=False)
            m.hires(hire(rate=rate))
            self.assertFalse(DI.usable(m.s.get('plant_hire', 'H-1').payload), rate)

    def test_plant_hire_without_a_rate_is_held_rate_is_material(self):
        self.m.hires(hire(rate=''))
        p = self.stored('plant_hire', 'H-1')
        self.assertTrue(p is None or not DI.usable(p))

    def test_timesheet_dated_after_the_receipt_date_is_held_future_dated(self):
        self.m.timesheets(['T-1', 'W-1', 'PRJ-001', 'WP-1', '2099-01-01', '8', '0', '6800'])
        p = self.stored('timesheet', 'T-1')
        self.assertFalse(DI.usable(p))
        self.assertIn('FUTURE_DATED:work_date', p['intrinsic']['pending'])

    def test_timesheet_overtime_and_rate_may_be_missing_with_a_warning(self):
        self.m.timesheets(['T-1', 'W-1', 'PRJ-001', 'WP-1', '2026-05-04', '8', '', ''])
        p = self.stored('timesheet', 'T-1')
        self.assertTrue(DI.usable(p))
        self.assertEqual(sorted(w for w in p['intrinsic']['warnings'] if w.startswith('VALUE_MISSING')), ['VALUE_MISSING:overtime_hours', 'VALUE_MISSING:rate_cents_per_hour'])

    def test_timesheet_with_a_non_numeric_hours_value_is_rejected_not_guessed(self):
        r = self.m.timesheets(['T-1', 'W-1', 'PRJ-001', 'WP-1', '2026-05-04', 'eight', '', ''])
        self.assertEqual(r['counts']['rejected'], 1)
        self.assertIsNone(self.stored('timesheet', 'T-1'))

    def test_work_output_key_is_project_package_and_week(self):
        self.m.outputs(['PRJ-001', 'WP-1', '2026-05-04', '320', 'm2'])
        self.assertIsNotNone(self.stored('work_output', 'PRJ-001|WP-1|2026-05-04'))

    def test_defect_negative_rework_cost_is_held_a_sign_error(self):
        self.m.defects(defect(cost='-100'))
        p = self.stored('defect', 'DEF-1')
        self.assertFalse(DI.usable(p))
        self.assertIn('SIGN_CONVENTION:rework_cost_cents', p['intrinsic']['pending'])

    def test_defect_zero_rework_cost_is_a_real_value(self):
        self.m.defects(defect(cost='0'))
        self.assertTrue(DI.usable(self.stored('defect', 'DEF-1')))

    def test_notice_without_a_linked_variation_is_usable_with_a_warning(self):
        self.m.notices(notice())
        p = self.stored('notice', 'N-1')
        self.assertTrue(DI.usable(p))
        self.assertIn('VALUE_MISSING:linked_variation_ref', p['intrinsic']['warnings'])

    def test_delay_event_with_an_open_end_is_usable_the_end_is_unknown(self):
        self.m.delays(delay(end=''))
        p = self.stored('delay_event', 'D-1')
        self.assertTrue(DI.usable(p))
        self.assertNotIn('end_date', p['fields'])

    def test_a_tenant_column_in_a_file_is_stripped_and_a_claim_for_another_tenant_refuses_the_file(self):
        data = csvb(COMP_H + ['tenant_id'], [comp() + ['zero_one']])
        r = self.m.det('TPL-BZ-COMPLIANCE', data, 'compliance')
        self.assertEqual(r['counts']['new'], 1)
        with self.assertRaises(TenantMismatch):
            self.m.det('TPL-BZ-COMPLIANCE', csvb(COMP_H + ['tenant_id'], [comp('SUP-002') + ['zero_two']]), 'compliance', 'c.csv')
        self.assertIsNone(self.stored('compliance', 'SUP-002|licence'))

    def test_records_are_invisible_to_another_tenant(self):
        self.m.compliance(comp())
        other = DetMini(tenant='zero_two', with_suppliers=False)
        self.assertIsNone(other.s.get('compliance', 'SUP-001|licence'))

    def test_unknown_entity_is_refused(self):
        t = json.load(open(os.path.join(HERE_ROOT, 'det_templates', 'TPL-BZ-COMPLIANCE.json')))
        t['target_entity'] = 'nonsense'
        with self.assertRaises(Exception):
            DI.ingest_det_file(self.m.s, self.m.clock, t, csvb(COMP_H, [comp()]), 'compliance')

    def test_a_source_identity_is_required(self):
        t = json.load(open(os.path.join(HERE_ROOT, 'det_templates', 'TPL-BZ-COMPLIANCE.json')))
        with self.assertRaises(Exception):
            DI.ingest_det_file(self.m.s, self.m.clock, t, csvb(COMP_H, [comp()]), '  ')

    def test_the_builder_zero_files_all_ingest_with_the_expected_counts(self):
        m = DetMini(with_suppliers=False)
        rc = DD.load_det(HERE_ROOT, m.s, m.clock, 'zero_one')
        self.assertEqual({k: v['counts']['new'] for k, v in rc.items()}, {'supplier_compliance.csv': 24, 'notices.csv': 1, 'delay_events.csv': 2, 'plant_hire.csv': 2,
                                                                          'timesheets.csv': 520, 'work_output.csv': 26, 'defects.csv': 3})
        self.assertEqual(sum(v['counts']['rejected'] for v in rc.values()), 0)
        held = [k for k in (m.s.query('timesheet')) if not DI.usable(k.payload)]
        self.assertEqual(len(held), 4)                              # the entries dated after the receipt date
