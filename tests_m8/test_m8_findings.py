"""APG-M8.1: findings M8-F2 to M8-F6, corrected in AUIF rev14, and how APG now uses each correction.  (APG-M8 to M8-R2, on AUIF rev13, pinned each defect here.)
  M8-F2  a composite natural key is AUIF's source identity: the canonical id is stable across revisions; a missing identity is refused per record, never hashed
  M8-F4  a module handler failure is reported to AUIF, not swallowed (APG's own handlers never let one escape, and the gate still reads them)
  M8-F5  AUIF's sync report says whether the read reached the end; APG refuses a read that is not complete
  M8-F6  sync reports instead of raising: drift before the first validation, and a blank identity value
  (M8-F1 is in test_m8_dev01.py; M8-F3 in test_m8_events.py.)"""
import os, shutil, unittest
from types import SimpleNamespace
from ._auif import codes, copy_folder, records, rewrite_csv, single, status
from apg_auif import intake


class TestM8F2CompositeIdentity(unittest.TestCase):
    def test_the_canonical_id_of_a_composite_key_is_the_natural_key_and_stays_the_same_across_revisions(self):
        d = copy_folder('zero_one', 'SRC-02_costing')
        try:
            w = single('bz-job-costing', base_dir=d)
            w['env'].import_entity('zero_one', 'bz-job-costing', 'budget_line')
            p1 = records(w['s'], 'budget_line')['PRJ-001|CC-01']['provenance']

            def newer(h, b):
                b[0][h.index('revision')] = 'R1'
                b[0][h.index('budget_cents')] = '40000000'
                return h, b
            rewrite_csv(os.path.join(d, 'budget_lines.csv'), newer)
            w['env'].import_entity('zero_one', 'bz-job-costing', 'budget_line')
            p2 = records(w['s'], 'budget_line')['PRJ-001|CC-01']['provenance']
            self.assertEqual(p1['source_record_id'], 'PRJ-001|CC-01')
            self.assertEqual(p1['canonical_id'], p2['canonical_id'])                  # the same business record, the same canonical id
            self.assertEqual(len(w['s'].history('budget_line', 'PRJ-001|CC-01')), 2)
        finally:
            shutil.rmtree(d)

    def test_apgs_own_identity_rule_matches_rev14s(self):
        from auif.fabric import source_identity as auif_rule
        for vals in (['PRJ-001', 'CC-01'], ['a|b', 'c'], ['a', 'b|c'], ['a\\', '|b'], ['a\\|', 'b'], ['only']):
            keys = ['k%d' % i for i in range(len(vals))]
            self.assertEqual(intake.source_identity(vals), auif_rule(keys if len(keys) > 1 else keys[0], dict(zip(keys, vals)))[0], vals)
        self.assertNotEqual(intake.source_identity(['a\\', 'b|c']), intake.source_identity(['a|b\\', 'c']))

    def test_every_composite_record_type_is_declared_to_auif_with_its_full_key(self):
        w = single('bz-job-costing')
        cfg = w['env'].fabric.cfg[('zero_one', 'bz-job-costing')]['identity']
        for ent, e in w['binding'].integrations['bz-job-costing']['entities'].items():
            nk = e['template']['natural_key']
            self.assertEqual(cfg[ent], nk[0] if len(nk) == 1 else nk, ent)


class TestM8F4HandlerFailures(unittest.TestCase):
    def test_basemodule_reports_a_failing_handler_and_apg_records_it(self):
        from auif_ext.module_client.client import BaseModule
        m = BaseModule('x', [])
        m.on('entity', lambda ctx, o: (_ for _ in ()).throw(ValueError('lost detail')))
        self.assertEqual(m.ingest_canonical_entity(None, {}), {'handler_failures': 1})       # rev14: the failure is returned to the fabric
        self.assertEqual(m.handler_errors, [{'kind': 'entity', 'error': 'ValueError'}])
        w = single('bz-master')
        w['env'].module.handler_errors.append({'kind': 'entity', 'error': 'RuntimeError'})
        self.assertIn('ADAPTER_ERROR', codes(status(w['s'], w['env'])))                     # APG's gate still refuses on any handler failure


class TestM8F5SyncReportCompleteness(unittest.TestCase):
    def test_a_read_cut_short_by_the_page_limit_is_reported_and_refused(self):
        w = single('bz-accounting')
        rep = w['env'].fabric.sync(w['env'].ctx['zero_one'], 'bz-accounting', 'ap_invoice', max_pages=1, page_size=50)
        self.assertEqual((rep['delivered'], rep['complete'], rep['stopped_at_page_limit']), (50, False, True))
        ref = {'id': 'p', 'version': '1', 'hash': 'h'}
        bnd = SimpleNamespace(state=lambda iid: {'state': 'ACTIVE', 'manifest_ref': ref})
        batch = SimpleNamespace(mode='sync', deliveries=['x'] * 50, errors=[], states=[], refusals=[], entity='ap_invoice', integration_id='i', expect={'max_pages': 5, 'manifest_ref': ref})
        bad, _ = intake.batch_checks(bnd, batch, rep, None)
        self.assertEqual(sorted({c for c, _ in bad}), ['SYNC_INCOMPLETE'])

    def test_a_report_that_does_not_say_the_read_is_complete_is_refused(self):
        ref = {'id': 'p', 'version': '1', 'hash': 'h'}
        bnd = SimpleNamespace(state=lambda iid: {'state': 'ACTIVE', 'manifest_ref': ref})
        batch = SimpleNamespace(mode='sync', deliveries=['x'], errors=[], states=[], refusals=[], entity='ap_invoice', integration_id='i', expect={'max_pages': 5, 'manifest_ref': ref})
        self.assertEqual(sorted({c for c, _ in intake.batch_checks(bnd, batch, {'pages': 1, 'delivered': 1}, None)[0]}), ['SYNC_INCOMPLETE'])
        self.assertEqual(intake.batch_checks(bnd, batch, {'pages': 1, 'delivered': 1, 'complete': True}, None)[0], [])


class TestM8F6SyncReports(unittest.TestCase):
    def test_drift_before_the_first_validation_is_reported_not_raised(self):
        d = copy_folder('zero_one', 'reference')
        try:
            rewrite_csv(os.path.join(d, 'suppliers.csv'), lambda h, b: (h[:-1], [r[:-1] for r in b]))
            w = single('bz-master', base_dir=d)
            rep = w['env'].fabric.sync(w['env'].ctx['zero_one'], 'bz-master', 'supplier')
            self.assertTrue(rep['not_allowed'])
            s = w['env'].import_entity('zero_one', 'bz-master', 'supplier')
            self.assertEqual(s['status'], 'blocked')
            self.assertNotIn('AUIF_RAISED', {c for c, _ in s['reasons']})
            self.assertIn('SYNC_NOT_ALLOWED', {c for c, _ in s['reasons']})
        finally:
            shutil.rmtree(d)

    def test_a_blank_source_identity_is_one_refused_record_and_the_batch_is_refused(self):
        d = copy_folder('zero_one', 'reference')
        try:
            def blank(h, b):
                b[3][h.index('supplier_id')] = ''
                return h, b
            rewrite_csv(os.path.join(d, 'suppliers.csv'), blank)
            w = single('bz-master', base_dir=d)
            rep = w['env'].fabric.sync(w['env'].ctx['zero_one'], 'bz-master', 'supplier', max_pages=5, page_size=50)
            self.assertEqual((rep['refused'], rep['complete']), (1, True))
            w2 = single('bz-master', base_dir=d)
            s = w2['env'].import_entity('zero_one', 'bz-master', 'supplier')
            self.assertEqual(s['status'], 'blocked')
            self.assertTrue({'IDENTITY_MISSING', 'RECORD_REFUSED'} <= {c for c, _ in s['reasons']}, s['reasons'])
            self.assertEqual(records(w2['s'], 'supplier'), {})
        finally:
            shutil.rmtree(d)


class TestAnAuifExceptionIsStillRefused(unittest.TestCase):
    """rev14 no longer raises in the M8-F6 cases, but the APG client keeps its guard: if AUIF ever raises during an import, an event call or a tick, the batch is refused
    as AUIF_RAISED, nothing is written and nothing is retried around it."""
    def test_every_auif_call_that_raises_is_refused_as_auif_raised(self):
        from .test_m8_events import IID as EV_IID, ev_world
        from .synthetic_events import event
        w = single('bz-master')
        env = w['env']

        def boom(*a, **k):
            raise RuntimeError('synthetic AUIF failure')
        for name, call in (('sync', lambda: env.import_entity('zero_one', 'bz-master', 'supplier')),):
            real = getattr(env.fabric, name)
            setattr(env.fabric, name, boom)
            try:
                s = call()
            finally:
                setattr(env.fabric, name, real)
            self.assertEqual((s['status'], sorted(c for c, _ in s['reasons'])), ('blocked', ['AUIF_RAISED', 'SYNC_FAILED']), name)      # no transport report either
        self.assertEqual(records(w['s'], 'supplier'), {})
        ev, s2 = ev_world()
        for name, call in (('ingest_events', lambda: ev.ingest_events('zero_one', EV_IID, 'payment', [event(1, 'PAY-9001')])),
                           ('tick', lambda: ev.tick('zero_one', EV_IID, 'payment'))):
            real = getattr(ev.fabric, name)
            setattr(ev.fabric, name, boom)
            try:
                out = call()
            finally:
                setattr(ev.fabric, name, real)
            self.assertEqual(out['status'], 'blocked', name)
            self.assertIn('AUIF_RAISED', {c for c, _ in out['reasons']}, name)
        self.assertEqual(records(s2, 'payment'), {})


class TestInputGuardPageLimit(unittest.TestCase):
    def test_a_page_with_more_than_2000_keys_is_refused_whole_so_the_client_sizes_pages(self):
        w = single('bz-accounting')
        rep = w['env'].fabric.sync(w['env'].ctx['zero_one'], 'bz-accounting', 'ap_invoice', max_pages=5, page_size=200)    # 187 rows x 11 columns + 3 > 2000
        self.assertEqual((rep['delivered'], rep['failed']), (0, 'MALFORMED_RESPONSE'))
        ex = w['env']._expect('zero_one', 'bz-accounting', 'ap_invoice')
        self.assertLessEqual(ex['page_size'] * 11 + 3, 2000)


if __name__ == '__main__':
    unittest.main()
