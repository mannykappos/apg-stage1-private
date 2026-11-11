"""End-to-end lineage, no laundering (M8 acceptance): no stored record, no figure input and no signal's evidence lacks lineage.  Builder Zero zero_one through AUIF into
APG, reconciled, then every financial figure and both detection runs; every input they pinned and every evidence reference of every signal is traced back.
The lineage is also checked for TRUTH, not only presence: it must match the source row, the pinned pack, AUIF's own stored observation and the record's business date."""
import csv, hashlib, json, os, unittest
from ._auif import AS_OF, HERE_ROOT, load_full
from apg_auif import assess, lineage
from apg.det import detect as DET


class TestLineage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = load_full()
        cls.kinds = lineage.source_kinds(HERE_ROOT)

    def test_every_revision_of_every_source_record_has_complete_lineage(self):
        probs, n = lineage.store_problems(self.w['s'], self.kinds)
        self.assertEqual(probs, [])
        self.assertEqual(n, 1220)                                                      # every row of the 26 zero_one files is one record revision

    def test_every_figure_input_and_every_signal_evidence_traces_to_lineage(self):
        w, total = self.w, {'source': 0, 'derived': 0, 'config': 0, 'untraced': 0}
        for prj in ('PRJ-001', 'PRJ-002', 'PRJ-003'):
            a = assess.run_assessment(w['s'], w['clock'], w['expected'], prj, AS_OF, w['fv'], w['dv'], w['env'].module)
            self.assertEqual(a['status'], 'assessed')
            for k in a['run_keys']:
                probs, c = lineage.trace_run(w['s'], w['s'].get('repro_record', k).payload, self.kinds)
                self.assertEqual(probs, [], k)
                for x in c:
                    total[x] += c[x]
            probs, n = lineage.trace_signals(w['s'], a, self.kinds)
            self.assertEqual(probs, [])
        t = DET.run_tenant(w['s'], DET.det_registry(), w['clock'], AS_OF, w['dv'])
        probs, c = lineage.trace_run(w['s'], t, self.kinds)
        self.assertEqual(probs, [])
        self.assertEqual(lineage.trace_signals(w['s'], t['result'], self.kinds)[0], [])
        self.assertEqual(total['untraced'], 0)
        self.assertGreater(total['source'], 1000)

    def test_the_lineage_is_true_to_the_source_the_pack_and_auif(self):
        from auif.util import sha
        w = self.w
        rows = list(csv.DictReader(open(os.path.join(HERE_ROOT, 'builder_zero', 'zero_one', 'SRC-01_accounting', 'ap_invoices.csv'), encoding='utf-8', newline='')))
        pin = w['env'].bindings['zero_one'].integrations['bz-accounting']['pack_ref']
        ctx = w['env'].ctx['zero_one']
        for i, row in enumerate(rows):
            p = w['s'].get('ap_invoice', row['invoice_id']).payload['provenance']
            self.assertEqual((p['source_record_id'], p['row_no'], p['integration_id'], p['source']), (row['invoice_id'], i + 1, 'bz-accounting', 'accounting'))
            self.assertEqual((p['translation_pack_id'], p['translation_pack_version'], p['translation_pack_hash']), (pin['id'], pin['version'], pin['hash']))
            self.assertEqual(p['payload_hash'], sha(row))                                   # exactly the row AUIF read
            self.assertEqual(p['canonical_id'], 'module.apg.apinvoice:bz-accounting:' + row['invoice_id'])
            self.assertEqual((p['effective_at'], p['effective_time_basis']), (row['invoice_date'], 'field:invoice_date'))
            ob = w['env'].store.get(ctx, 'observations', p['observation_id'])          # AUIF's own record of the observation
            self.assertEqual((ob['payload_hash'], ob['observed_at'], ob['source_object']['object_id']), (p['payload_hash'], p['observed_at'], row['invoice_id']))
            co = w['env'].store.get(ctx, 'canonical_objects', p['canonical_id'])['object']
            self.assertEqual(co['provenance_chain'], p['provenance_chain'])

    def test_a_record_type_without_a_business_date_says_so(self):
        p = self.w['s'].get('supplier', 'SUP-001').payload['provenance']
        self.assertEqual((p['effective_at'], p['effective_time_basis']), (None, 'none: this record type carries no business date'))


class TestTheLineageCheckerItself(unittest.TestCase):
    """The checker is not vacuous: it refuses a record whose lineage is missing, altered or not from AUIF."""
    @classmethod
    def setUpClass(cls):
        w = load_full(families=('m3',))
        cls.good = w['s'].get('ap_invoice', 'INV-0001').payload

    def test_the_good_record_passes(self):
        self.assertEqual(lineage.record_problems(self.good), [])

    def test_an_input_of_an_unknown_kind_is_untraced(self):
        probs, c = lineage.trace_run(None, {'run_key': 'x' * 16, 'inputs': [{'kind': 'something_else', 'key': 'k', 'revision': 1}]}, ('ap_invoice',))
        self.assertEqual((len(probs), c['untraced']), (1, 1))

    def test_each_missing_or_broken_part_is_found(self):
        import copy
        from apg_auif.intake import LINEAGE_FIELDS
        for f in LINEAGE_FIELDS:
            p = copy.deepcopy(self.good)
            p['provenance'].pop(f)
            self.assertTrue(lineage.record_problems(p), f)
        p = copy.deepcopy(self.good)
        p['provenance']['provenance_chain'] = [s for s in p['provenance']['provenance_chain'] if s['step_kind'] != 'TRANSLATION_PACK']
        self.assertTrue(lineage.record_problems(p))
        p = copy.deepcopy(self.good)
        p['provenance']['effective_at'] = None
        p['provenance']['effective_time_basis'] = 'field:invoice_date'
        self.assertTrue(lineage.record_problems(p))
        p = copy.deepcopy(self.good)
        p['provenance']['path'] = 'm3'                                                     # every field present, but not lineage from AUIF
        self.assertTrue(lineage.record_problems(p))
        p = copy.deepcopy(self.good)
        p['provenance'] = {'file_sha256': 'x', 'source': 'accounting'}                    # an M3 file provenance is not AUIF lineage
        self.assertTrue(lineage.record_problems(p))


if __name__ == '__main__':
    unittest.main()
