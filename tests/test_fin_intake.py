import json, os, unittest
from . import _path                                         # noqa: F401
from ._path import HERE_ROOT
from .helpers_fin import *                                  # noqa: F401,F403
from .helpers_fin import Mini, ctc, var, CTC_H, CON_H, FAC_H, RET_H, SEC_H, BANK_H, PRJ_H, VAR_H
from .helpers_ingest import csvb
from apg.fin import intake
from apg.fin.demo_fin import FIN_INTAKE_POLICY as DF_POLICY
from apg.ports import TenantMismatch
from apg.ingest import pipeline as P3, mapping


class TestFinIntake(unittest.TestCase):
    def setUp(self):
        self.m = Mini(with_suppliers=False)

    def stored(self, kind, key):
        r = self.m.s.get(kind, key)
        return None if r is None else r.payload

    def test_every_template_is_valid_and_has_a_spec(self):
        for t in sorted(os.listdir(os.path.join(HERE_ROOT, 'fin_templates'))):
            d = json.load(open(os.path.join(HERE_ROOT, 'fin_templates', t)))
            self.assertEqual(mapping.validate_template(d), [], t)
            self.assertIn(d['target_entity'], intake.FIN_SPECS, t)
        self.assertEqual(len(os.listdir(os.path.join(HERE_ROOT, 'fin_templates'))), len(intake.FIN_SPECS))

    def test_contract_stored_with_provenance_and_original_text(self):
        r = self.m.contracts(['PRJ-001', '10000000', '0'])
        self.assertEqual(r['counts']['new'], 1)
        p = self.stored('contract', 'PRJ-001')
        self.assertEqual(p['fields'], {'project_ref': 'PRJ-001', 'original_contract_cents': 10000000, 'approved_variations_cents': 0})
        self.assertEqual(p['raw']['original_contract_cents'], '10000000')
        self.assertEqual(p['provenance']['template_id'], 'TPL-BZ-CONTRACTS')
        self.assertEqual(p['provenance']['uploaded_by'], 'ann')
        self.assertTrue(intake.usable(p))

    def test_same_file_twice_is_a_recorded_replay(self):
        self.m.contracts(['PRJ-001', '10000000', '0'])
        before = len(self.m.s.history('contract', 'PRJ-001'))
        r = self.m.contracts(['PRJ-001', '10000000', '0'])
        self.assertTrue(r['replay'])
        self.assertEqual(len(self.m.s.history('contract', 'PRJ-001')), before)

    def test_repeat_row_in_another_file_is_a_duplicate_not_a_second_record(self):
        self.m.contracts(['PRJ-001', '10000000', '0'])
        r = self.m.fin('TPL-BZ-CONTRACTS', csvb(CON_H, [['PRJ-001', '10000000', '0'], ['PRJ-002', '5', '0']]), 'commercial', name='other.csv')
        self.assertEqual((r['counts']['duplicate'], r['counts']['new']), (1, 1))
        self.assertEqual(len(self.m.s.history('contract', 'PRJ-001')), 1)

    def test_different_content_with_no_order_is_a_quarantined_conflict(self):
        self.m.contracts(['PRJ-001', '10000000', '0'])
        r = self.m.fin('TPL-BZ-CONTRACTS', csvb(CON_H, [['PRJ-001', '12000000', '0']]), 'commercial', name='b.csv')
        self.assertEqual(r['counts']['conflict'], 1)
        p = self.stored('contract', 'PRJ-001')
        self.assertEqual(len(p['conflict']['contenders']), 2)
        self.assertEqual(intake.outcome(p), 'quarantined')
        self.assertFalse(intake.usable(p))

    def test_conflict_is_independent_of_arrival_order(self):
        a, b = Mini(with_suppliers=False), Mini(with_suppliers=False)
        a.contracts(['PRJ-001', '1000', '0']); a.fin('TPL-BZ-CONTRACTS', csvb(CON_H, [['PRJ-001', '2000', '0']]), 'commercial', name='b.csv')
        b.contracts(['PRJ-001', '2000', '0']); b.fin('TPL-BZ-CONTRACTS', csvb(CON_H, [['PRJ-001', '1000', '0']]), 'commercial', name='b.csv')
        ca, cb = (x.s.get('contract', 'PRJ-001').payload['conflict']['contenders'] for x in (a, b))
        self.assertEqual([(c['content_hash'], c['fields']) for c in ca], [(c['content_hash'], c['fields']) for c in cb])

    def test_blank_required_material_cell_rejects_the_row_and_keeps_it(self):
        r = self.m.contracts(['PRJ-001', '', '0'])
        self.assertEqual((r['counts']['rejected'], r['counts']['new']), (1, 0))
        self.assertIsNone(self.stored('contract', 'PRJ-001'))

    def _optional_template(self, field):
        t = json.load(open(os.path.join(HERE_ROOT, 'fin_templates', 'TPL-BZ-CONTRACTS.json')))
        for c in t['columns']:
            if c['target_field'] == field:
                c['required'] = False
                c['missing_means'] = 'unknown_not_zero'
        return t

    def test_material_value_unknown_holds_the_record(self):
        t = self._optional_template('original_contract_cents')
        intake.ingest_fin_file(self.m.s, self.m.clock, t, csvb(CON_H, [['PRJ-001', '', '0']]), 'commercial', 'c.csv', DF_POLICY)
        p = self.stored('contract', 'PRJ-001')
        self.assertEqual(p['intrinsic']['pending'], ['MATERIAL_VALUE_UNKNOWN:original_contract_cents'])
        self.assertFalse(intake.usable(p))

    def test_optional_value_missing_is_only_a_warning_when_declared_tolerable(self):
        self.m.contracts(['PRJ-001', '10000000', ''])
        p = self.stored('contract', 'PRJ-001')
        self.assertEqual((p['intrinsic']['outcome'], p['intrinsic']['warnings']), ('accepted_with_warnings', ['VALUE_MISSING:approved_variations_cents']))
        self.assertNotIn('approved_variations_cents', p['fields'])                      # a blank is unknown, never zero
        self.assertIn('approved_variations_cents', p['unknown'])

    def test_optional_value_missing_but_not_tolerated_holds_the_record(self):
        intake.ingest_fin_file(self.m.s, self.m.clock, json.load(open(os.path.join(HERE_ROOT, 'fin_templates', 'TPL-BZ-CONTRACTS.json'))), csvb(CON_H, [['PRJ-001', '10000000', '']]),
                               'commercial', 'c.csv', intake.FinIntakePolicy())
        p = self.stored('contract', 'PRJ-001')
        self.assertEqual(p['intrinsic']['pending'], ['CRITICAL_VALUE_MISSING:approved_variations_cents'])
        self.assertFalse(intake.usable(p))

    def test_unpriced_variation_is_kept_with_a_warning_not_a_zero(self):
        self.m.variations(var('VAR-1', value=''))
        p = self.stored('variation', 'VAR-1')
        self.assertTrue(intake.usable(p))
        self.assertNotIn('value_cents', p['fields'])

    def test_sign_conventions(self):
        self.m.contracts(['PRJ-001', '0', '0'], ['PRJ-002', '-5', '0'])
        for k in ('PRJ-001', 'PRJ-002'):
            self.assertEqual(self.stored('contract', k)['intrinsic']['pending'], ['SIGN_CONVENTION:original_contract_cents'])
        self.m.security(['BG-1', 'PRJ-001', 'bank_guarantee', '0', '2027-01-01'])
        self.assertEqual(self.stored('security', 'BG-1')['intrinsic']['pending'], ['SIGN_CONVENTION:face_value_cents'])

    def test_negative_amounts_that_cannot_be_negative_are_held_and_zero_is_a_value(self):
        self.m.retention(['PRJ-001', '-500', '2027-02-01', '', ''], ['PRJ-002', '0', '2027-02-01', '', ''])
        self.assertEqual(self.stored('retention', 'PRJ-001')['intrinsic']['pending'], ['SIGN_CONVENTION:retention_held_cents'])
        self.assertTrue(intake.usable(self.stored('retention', 'PRJ-002')))                 # nothing withheld is a real value
        self.m.ctcs(ctc(cents='-1'))
        self.assertEqual(self.stored('ctc_line', 'PRJ-001|CC-01|F-1')['intrinsic']['pending'], ['SIGN_CONVENTION:cost_to_complete_cents'])
        self.m.facility(['FAC-1', '100', '-5', '800', '2026-09-30'])
        self.assertEqual(self.stored('facility', 'FAC-1')['intrinsic']['pending'], ['SIGN_CONVENTION:drawn_cents'])
        self.m.projects(['PRJ-009', 'x', '-1', '2026-01-01', '2027-01-01'])
        self.assertEqual(self.stored('project', 'PRJ-009')['intrinsic']['pending'], ['SIGN_CONVENTION:contract_value_cents'])

    def test_negative_bank_amounts_are_normal(self):
        self.m.bank(['TX-1', '2026-09-01', '-500', 'x'])
        self.assertTrue(intake.usable(self.stored('bank_txn', 'TX-1')))

    def test_future_dated_event_is_held(self):
        self.m.ctcs(ctc(date='2026-12-31'))                                             # the world's clock says 2026-10-01
        self.assertEqual(self.stored('ctc_line', 'PRJ-001|CC-01|F-1')['intrinsic']['pending'], ['FUTURE_DATED:forecast_date'])

    def test_bad_cells_reject_the_row_and_report_it(self):
        r = self.m.fin('TPL-BZ-FACILITY', csvb(FAC_H, [['F1', '100', '10', '7.8', '2026-09-30'], ['F2', '100', '10', '780', '2026-09-30'], ['F3', '1e3', '10', '780', '2026-09-30'],
                                                  ['F4', '100', '10', '780', '30/09/2026']]), 'bank')
        self.assertEqual((r['counts']['new'], r['counts']['rejected']), (1, 3))
        self.assertIsNone(self.stored('facility', 'F1'))
        self.assertIsNotNone(self.stored('facility', 'F2'))

    def test_non_ascii_identifier_is_rejected(self):
        r = self.m.contracts(['PRJ‑001', '10', '0'])
        self.assertEqual(r['counts']['rejected'], 1)

    def test_a_file_that_cannot_be_read_is_refused_whole(self):
        r = self.m.fin('TPL-BZ-CONTRACTS', b'wrong,header\n1,2\n', 'commercial')
        self.assertEqual(r['status'], 'file_rejected')
        r = self.m.fin('TPL-BZ-CONTRACTS', b'project_id,original_contract_cents,approved_variations_cents\n\x00,1,2\n', 'commercial', name='n.csv')
        self.assertEqual(r['status'], 'file_rejected')

    def test_a_tenant_claim_in_a_file_refuses_the_whole_file(self):
        with self.assertRaises(TenantMismatch):
            self.m.fin('TPL-BZ-CONTRACTS', b'project_id,original_contract_cents,approved_variations_cents,tenant_id\nPRJ-1,10,0,other\n', 'commercial')
        self.assertIsNone(self.stored('contract', 'PRJ-1'))
        r = self.m.fin('TPL-BZ-CONTRACTS', b'project_id,original_contract_cents,approved_variations_cents,tenant_id\nPRJ-1,10,0,zero_one\n', 'commercial', name='m.csv')
        self.assertEqual(r['stripped_scope_columns'], ['tenant_id'])
        self.assertNotIn('tenant_id', json.dumps(self.stored('contract', 'PRJ-1')['raw']))

    def test_entity_and_source_guards(self):
        with self.assertRaises(P3.IngestError):
            intake.ingest_fin_file(self.m.s, self.m.clock, json.load(open(os.path.join(HERE_ROOT, 'ingest_templates', 'TPL-BZ-BUDGET-LINES.json'))), b'x', 'job_costing')
        with self.assertRaises(P3.IngestError):
            self.m.fin('TPL-BZ-CONTRACTS', b'x', '  ')

    def test_receipt_keeps_what_was_done_and_the_atomic_write_leaves_nothing_half_done(self):
        r = self.m.fin('TPL-BZ-VARIATIONS', csvb(VAR_H, [var('V1'), var('V2', status='submitted', value='')]), 'commercial')
        self.assertEqual(r['counts']['rows'], 2)
        self.assertEqual({x['key']: x['result'] for x in r['results']}, {'V1': 'new', 'V2': 'new'})
        self.assertIsNotNone(self.m.s.get('ingest_receipt', P3.receipt_key(r['file_sha256'], r['mapping_version'], 'commercial')))

    def test_outcome_helpers(self):
        p = {'conflict': None, 'intrinsic': {'outcome': 'pending_reconciliation'}}
        self.assertEqual(intake.outcome(p), 'pending_reconciliation')
        self.assertFalse(intake.usable(p))
        self.assertEqual(intake.outcome({'conflict': {'contenders': []}, 'intrinsic': {'outcome': 'accepted'}}), 'quarantined')
        self.assertTrue(intake.usable({'conflict': None, 'intrinsic': {'outcome': 'accepted_with_warnings'}}))

    def test_intake_policy_never_relaxes_a_material_field(self):
        pol = intake.FinIntakePolicy(warn_unknown={'contract': ('original_contract_cents',)})
        self.assertFalse(pol.tolerates_missing('contract', 'original_contract_cents'))
        self.assertTrue(intake.FinIntakePolicy(warn_unknown={'contract': ('approved_variations_cents',)}).tolerates_missing('contract', 'approved_variations_cents'))


if __name__ == '__main__':
    unittest.main()
