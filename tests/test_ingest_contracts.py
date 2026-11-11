"""The M3 port contracts: the references pass, every faulty implementation is caught; the scan-gated import path; the faulty-file corpus."""
import json, unittest
from . import _path                                         # noqa: F401
from .helpers_ingest import INV_H, World, csvb, inv, inv_file, tpl
from apg import tenancy
from apg.ingest import contracts_m3 as C, corpus, demo_setup as D, faulty_m3, pipeline as P, reference_m3 as REF
from apg.ingest.filestore import InMemoryFileStore, ingest_stored_file
from apg.ingest.mapping import Limits
from apg.ingest.ports_m3 import SCANNER_ROLE
from apg.ports import TenantMismatch

INVT = tpl('TPL-BZ-AP-INVOICES')


class TestContractsOnReferences(unittest.TestCase):
    def test_every_case_passes_on_the_references(self):
        res = C.run_all(REF.file_env(), REF.job_env())
        self.assertEqual([r for r in res if not r[3]], [])
        self.assertEqual((len([r for r in res if r[0] == C.FS]), len([r for r in res if r[0] == C.JR])), (10, 14))

    def test_every_faulty_implementation_is_caught_for_the_intended_reason(self):
        for fid, (text, kind, factory, expect) in faulty_m3.FAULTS.items():
            with self.subTest(fault=fid):
                suite = C.FS if kind == 'files' else C.JR
                res = C.run_all(factory if kind == 'files' else REF.file_env(), factory if kind == 'jobs' else REF.job_env(), [suite])
                failed = {r[1] for r in res if not r[3]}
                self.assertTrue(set(expect) <= failed, f'{fid} {text}: failed {failed}')

    def test_every_case_is_hit_by_at_least_one_fault(self):
        hit = set()
        for fid, (_, kind, factory, expect) in faulty_m3.FAULTS.items():
            hit |= set(expect)
        missing = {c[1] for c in C.CASES} - hit
        self.assertEqual(missing, set())


class TestScanGatedImport(unittest.TestCase):
    def setUp(self):
        self.w = World(); self.s = self.w.who('a'); self.files = InMemoryFileStore(self.w.provider)
        self.sc = self.w.who('scan', user='scanner-svc', roles=(SCANNER_ROLE,), kind='service').ctx
        self.data = inv_file(inv('INV-S1'))

    def put(self):
        return self.files.put(self.s.ctx, 'inv.csv', self.data)

    def test_an_unscanned_file_is_not_parsed_and_nothing_is_written(self):
        m = self.put()
        r = ingest_stored_file(self.s, self.files, self.w.clock, INVT, m.file_id, 'accounting', D.DEMO_POLICY)
        self.assertEqual((r['status'], r['code']), ('not_ingested', 'SCAN_REQUIRED'))
        for k in ('ap_invoice', 'ingest_receipt', 'ingest_reject'):
            self.assertEqual(self.s.query(k), ())
        self.assertIn('ingest.file_not_ingested', [e.event_type for e in self.w.audit.read(self.s.ctx)])

    def test_an_infected_file_is_never_parsed_even_after_a_later_clean_attempt(self):
        m = self.put()
        self.files.record_scan(self.sc, m.file_id, 'infected')
        r = ingest_stored_file(self.s, self.files, self.w.clock, INVT, m.file_id, 'accounting', D.DEMO_POLICY)
        self.assertEqual(r['code'], 'SCAN_INFECTED')
        self.assertEqual(self.s.query('ap_invoice'), ())

    def test_a_clean_file_is_ingested_once_and_replay_is_a_recorded_no_op(self):
        m = self.put(); self.files.record_scan(self.sc, m.file_id, 'clean')
        a = ingest_stored_file(self.s, self.files, self.w.clock, INVT, m.file_id, 'accounting', D.DEMO_POLICY)
        b = ingest_stored_file(self.s, self.files, self.w.clock, INVT, m.file_id, 'accounting', D.DEMO_POLICY)
        self.assertEqual((a['status'], a['replay'], a['file_id'], a['counts']['new']), ('ingested', False, m.file_id, 1))
        self.assertEqual((b['replay'], len(self.s.query('ap_invoice'))), (True, 1))
        self.assertEqual(self.s.get('ap_invoice', 'INV-S1').payload['provenance']['file_sha256'], m.sha256) if 'provenance' in self.s.get('ap_invoice', 'INV-S1').payload else None

    def test_damaged_bytes_are_refused_not_parsed(self):
        m = self.put(); self.files.record_scan(self.sc, m.file_id, 'clean')
        self.files._contract_corrupt('zero_one', m.file_id)
        r = ingest_stored_file(self.s, self.files, self.w.clock, INVT, m.file_id, 'accounting', D.DEMO_POLICY)
        self.assertEqual(r['code'], 'FILE_INTEGRITY')
        self.assertEqual(self.s.query('ap_invoice'), ())

    def test_another_tenants_file_id_is_just_missing(self):
        m = self.put(); self.files.record_scan(self.sc, m.file_id, 'clean')
        s2 = self.w.who('b', 'zero_two', 'bob')
        r = ingest_stored_file(s2, self.files, self.w.clock, INVT, m.file_id, 'accounting', D.DEMO_POLICY)
        self.assertEqual(r['code'], 'FILE_NOT_FOUND')
        self.assertEqual(s2.query('ap_invoice'), ())

    def test_a_hostile_file_id_does_not_crash_and_a_foreign_claim_inside_a_clean_file_is_still_refused(self):
        self.assertEqual(ingest_stored_file(self.s, self.files, self.w.clock, INVT, '', 'accounting', D.DEMO_POLICY)['code'], 'FILE_NOT_FOUND')
        bad = csvb(INV_H + ['tenant_id'], [inv('INV-S2') + ['zero_two']])
        m = self.files.put(self.s.ctx, 'bad.csv', bad); self.files.record_scan(self.sc, m.file_id, 'clean')
        with self.assertRaises(TenantMismatch):
            ingest_stored_file(self.s, self.files, self.w.clock, INVT, m.file_id, 'accounting', D.DEMO_POLICY)
        self.assertEqual(self.s.query('ap_invoice'), ())

    def test_a_job_can_run_a_stored_file_through_the_runner_with_one_effect(self):
        from apg.ingest.jobs import JobRunner
        m = self.put(); self.files.record_scan(self.sc, m.file_id, 'clean')
        def handler(scoped, payload):
            r = ingest_stored_file(scoped, self.files, self.w.clock, INVT, payload['file_id'], 'accounting', D.DEMO_POLICY)
            return {'new': r['counts']['new']}
        run = JobRunner(self.w.provider, self.w.store, self.w.audit, handler)
        j = {'job_id': 'J-ing-1', 'credentials': 'a', 'payload': {'file_id': m.file_id}}
        r1, r2 = run.run(j), run.run(j)
        self.assertEqual((r1['result'], r2['replay'], len(self.s.query('ap_invoice'))), ({'new': 1}, True, 1))


class TestCorpus(unittest.TestCase):
    def test_all_cases_give_the_required_outcome(self):
        cs = corpus.cases()
        self.assertEqual(len(cs), 44)
        self.assertEqual(len({c['id'] for c in cs}), 44)
        for case in cs:
            with self.subTest(case=case['id']):
                w = World(); s = w.who('a')
                ok, msg = corpus.check_case(case, s, w.clock, INVT, D.DEMO_POLICY, P.ingest_file, Limits, TenantMismatch)
                self.assertTrue(ok, f"{case['id']} {case['desc']}: {msg}")

    def test_the_corpus_has_teeth_a_pipeline_that_stores_everything_fails_it(self):
        def lenient(scoped, clock, template, data, source, name='', policy=None, revision_field=None):
            try:
                return P.ingest_file(scoped, clock, template, data, source, name, D.DEMO_POLICY.__class__(), revision_field)
            except TenantMismatch:
                return {'status': 'ingested', 'counts': {'rows': 0, 'new': 0, 'revision': 0}, 'results': [], 'stripped_scope_columns': []}
        fails = 0
        for case in corpus.cases():
            w = World(); s = w.who('a')
            ok, _ = corpus.check_case(case, s, w.clock, INVT, D.DEMO_POLICY, lenient, Limits, TenantMismatch)
            fails += not ok
        self.assertGreater(fails, 0)                          # swallowing tenant refusals and dropping the severity policy is caught


if __name__ == '__main__':
    unittest.main()
