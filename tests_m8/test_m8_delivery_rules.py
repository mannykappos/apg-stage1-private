"""Duplicates, revisions, replays and atomicity on the AUIF path follow the existing contracts: the M3 delivery decision (new / revision / duplicate / stale / conflict),
"running the same file again is a recorded no-op", and "one atomic write per file" (here: per batch).  No new policy."""
import os, shutil, unittest
from ._auif import codes, copy_folder, records, rewrite_csv, single, status
from apg.ports import ConflictError


class TestDeliveryRules(unittest.TestCase):
    def test_the_same_delivery_again_is_a_recorded_no_op(self):
        w = single('bz-accounting')
        a = w['env'].import_entity('zero_one', 'bz-accounting', 'ap_invoice')
        before = {r.key: r.revision for r in w['s'].query('ap_invoice')}
        b = w['env'].import_entity('zero_one', 'bz-accounting', 'ap_invoice')
        self.assertEqual((a['status'], b['status'], b['receipt']['replay']), ('applied', 'replay', True))
        self.assertEqual({r.key: r.revision for r in w['s'].query('ap_invoice')}, before)
        self.assertEqual(len(w['s'].query('ingest_receipt')), 1)
        self.assertEqual(status(w['s'], w['env'], expected=[('bz-accounting', 'ap_invoice')])['status'], 'can_assess')

    def test_a_duplicate_delivery_inside_the_source_is_counted_once(self):
        w = single('bz-accounting')
        s = w['env'].import_entity('zero_one', 'bz-accounting', 'ap_invoice')
        self.assertEqual(s['receipt']['counts']['duplicate'], 0)             # Builder Zero repeats INV-0001's content under INV-0183: a different key, found by reconciliation
        from apg.ingest import demo_setup as D, reconcile as R3
        R3.reconcile(w['s'], D.demo_register(), '2026-09-30')
        self.assertEqual(w['s'].get('recon_state', 'ap_invoice/INV-0183').payload['lifecycle'], 'duplicate_of')

    def test_a_higher_revision_is_applied_and_the_older_one_kept_in_history(self):
        d = copy_folder('zero_one', 'SRC-02_costing')
        try:
            w = single('bz-job-costing', base_dir=d)
            w['env'].import_entity('zero_one', 'bz-job-costing', 'budget_line')
            def newer(h, b):
                b[0][h.index('revision')] = 'R1'
                b[0][h.index('budget_cents')] = '40000000'
                return h, b
            rewrite_csv(os.path.join(d, 'budget_lines.csv'), newer)
            s = w['env'].import_entity('zero_one', 'bz-job-costing', 'budget_line')
            self.assertEqual(s['receipt']['counts']['revision'], 1)
            h = w['s'].history('budget_line', 'PRJ-001|CC-01')
            self.assertEqual([x.payload['fields']['budget_cents'] for x in h], [34560000, 40000000])
            self.assertEqual(status(w['s'], w['env'], expected=[('bz-job-costing', 'budget_line')])['status'], 'can_assess')
        finally:
            shutil.rmtree(d)

    def test_a_blocked_batch_writes_nothing_but_its_own_evidence(self):
        w = single('bz-master')
        w['env'].module.close_batch = (lambda real: (lambda t: (lambda b: (b.refusals.append(('ADAPTER_ERROR', 'synthetic')), b)[1])(real(t))))(w['env'].module.close_batch)
        s = w['env'].import_entity('zero_one', 'bz-master', 'supplier')
        self.assertEqual(s['status'], 'blocked')
        for kind in ('supplier', 'ingest_receipt', 'ingest_reject', 'ingest_duplicate', 'ingest_stale'):
            self.assertEqual(len(w['s'].query(kind)), 0, kind)
        self.assertEqual([r.payload['status'] for r in w['s'].query('auif_batch')], ['blocked'])

    def test_a_concurrent_write_during_the_apply_leaves_nothing_half_written(self):
        w = single('bz-master')
        real = w['s'].atomic
        calls = []

        def racing(ops):
            if not calls and any(op[0] == 'supplier' for op in ops if isinstance(op, tuple)):
                calls.append(1)
                raise ConflictError('synthetic concurrent writer')
            return real(ops)
        w['s'].atomic = racing
        s = w['env'].import_entity('zero_one', 'bz-master', 'supplier')
        self.assertEqual(s['status'], 'blocked')
        self.assertEqual(len(w['s'].query('supplier')), 0)
        self.assertIn('COMMIT_CONFLICT', codes(status(w['s'], w['env'])))
        w['s'].atomic = real
        self.assertEqual(w['env'].import_entity('zero_one', 'bz-master', 'supplier')['status'], 'applied')
        self.assertEqual(status(w['s'], w['env'])['status'], 'can_assess')


if __name__ == '__main__':
    unittest.main()
