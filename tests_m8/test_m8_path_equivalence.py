"""Path equivalence (M8 acceptance): the M3 path and the AUIF path give the same APG records, figures, detection outputs, exclusions and assessment status, on both Builder
Zero tenants.  Every intended difference is declared in auif_m8/PATH_EQUIVALENCE_DECLARED_DIFFERENCES.json (written before these tests ran; its hash and one recorded
correction are in logs/m8/00_declared_differences_before_comparison.txt).  An undeclared difference fails; a declared difference that does not happen also fails.

1. The existing golden runs (GOLDEN_M3, GOLDEN_FIN, GOLDEN_DET) are repeated with the AUIF-path loaders swapped in for the M3 ones, and compared with the stored answers.
2. Every stored record of every collection, M3 path against AUIF path, provenance apart.
3. The figures and detection results the assessment returns, against the same calculations run on the M3-path store; and the assessment status on both paths.
M8-R1 (finding M8-F7): an empty source is refused on the AUIF path (SOURCE_EMPTY). Builder Zero tenant zero_two has header-only record types, declared in the 'source_empty'
section: their batches are refused, M3's empty receipts for them have no AUIF counterpart, and zero_two cannot be assessed through AUIF; its records, figures and detection
results are still compared with the M3 path, by running the calculations on both stores."""
import json, os, unittest
from ._auif import AS_OF, HERE_ROOT, D, DD, DF, GM, comparable, gate, world
from apg_auif import assess, loaders as L
from apg.det import golden_det as GDET
from apg.fin import calc_records as C, golden_fin as GFIN
from apg.det import detect as DET
from apg.ingest import views

DECL = json.load(open(os.path.join(HERE_ROOT, 'auif_m8', 'PATH_EQUIVALENCE_DECLARED_DIFFERENCES.json'), encoding='utf-8'))
EMPTY = {t: set(v) for t, v in DECL['source_empty'].items() if t in ('zero_one', 'zero_two')}          # M8-R1: (integration/record type) refused as SOURCE_EMPTY


def _diff(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        out = {}
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                out[path + '/' + str(k)] = (a.get(k, '<absent>'), b.get(k, '<absent>'))
            else:
                out.update(_diff(a[k], b[k], path + '/' + str(k)))
        return out
    return {} if a == b else {path: (a, b)}


class _Swap:
    """The AUIF loaders in place of the M3 loaders, for one run only (restored even if the run fails)."""
    def __enter__(self):
        self.real = (GM._load, DF.load_zero, DD.load_det)
        GM._load, DF.load_zero, DD.load_det = L.load_m3, L.load_zero, L.load_det

    def __exit__(self, *a):
        GM._load, DF.load_zero, DD.load_det = self.real


class TestGoldenRunsOnTheAuifPath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with _Swap():
            cls.got = {'M3': GM.run_golden_m3(HERE_ROOT), 'FIN': GFIN.run_golden_fin(HERE_ROOT), 'DET': GDET.run_golden_det(HERE_ROOT)}
        cls.want = {n: json.load(open(os.path.join(HERE_ROOT, 'regression', 'GOLDEN_%s.json' % n)))['golden'] for n in ('M3', 'FIN', 'DET')}

    def _check(self, name):
        d = _diff(json.loads(json.dumps(self.got[name])), self.want[name])
        declared = {x['path']: x for x in DECL['golden'][name]}
        self.assertEqual(sorted(d), sorted(declared), 'undeclared or missing differences in GOLDEN_%s' % name)
        for p, x in declared.items():
            self.assertEqual(list(d[p]), [x['auif_value'], x['m3_value']], p)

    def test_golden_m3(self):
        self._check('M3')

    def test_golden_fin_financial_core(self):
        self._check('FIN')

    def test_golden_det_detection_findings_and_portfolio(self):
        self._check('DET')

    def test_every_batch_was_applied_by_the_auif_path_not_blocked(self):
        for tenant, envs in L.RUNS.items():
            for env in envs:
                for r in env.bindings[tenant].scoped.query('auif_latest'):
                    if r.key in EMPTY[tenant]:                                     # M8-R1: a declared empty source is refused, and for that reason alone
                        self.assertEqual((r.payload['status'], [c for c, _ in r.payload['reasons']]), ('blocked', ['SOURCE_EMPTY']), (tenant, r.key))
                    else:
                        self.assertEqual((r.payload['status'], r.payload['reasons']), ('applied', []), (tenant, r.key))


def _load_both(tenant):
    """The same tenant loaded through M3 and through AUIF, each into its own world, with the demonstration policies approved in person."""
    out = {}
    for path in ('m3', 'auif'):
        clock, prov, store, audit, who = world()
        s = who('t-' + tenant, tenant, 'ann')
        owner = who('o-' + tenant, tenant, DD.DEMO_OWNER, DD.OWNER_ROLES)
        if path == 'auif':
            with _Swap():
                rc, fv, dv = DD.load_zero_all(HERE_ROOT, s, clock, tenant, owner=owner)
            env = L.RUNS[tenant][-2:]
        else:
            rc, fv, dv = DD.load_zero_all(HERE_ROOT, s, clock, tenant, owner=owner)
            env = None
        out[path] = dict(s=s, clock=clock, store=store, audit=audit, receipts=rc, fv=fv, dv=dv, env=env)
    return out


EVIDENCE = ('ingest_reject', 'ingest_duplicate', 'ingest_stale')
AUIF_ONLY = set(DECL['records']['auif_only_collections'])
RECEIPT_FIELDS = ('status', 'entity', 'template_id', 'mapping_version', 'ingest_version', 'source', 'file_name', 'received_at', 'uploaded_by', 'counts', 'blank_rows',
                  'unmapped_columns', 'stripped_scope_columns', 'results')


class TestRecordsAndAssessment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.both = {t: _load_both(t) for t in ('zero_one', 'zero_two')}

    def _kinds(self, w):
        t = w['s'].ctx.tenant_id
        return sorted({k[1] for k in w['store']._d if k[0] == t})

    def test_the_same_collections_exist_on_both_paths_apart_from_the_declared_ones(self):
        for t, b in self.both.items():
            m3, au = set(self._kinds(b['m3'])), set(self._kinds(b['auif']))
            self.assertTrue(au - m3 <= AUIF_ONLY, (t, au - m3))
            self.assertEqual(au - m3, AUIF_ONLY - {'auif_alert'}, t)              # the alert collection is declared as possible; on clean data no alert is raised
            self.assertEqual(m3 - au, set(), t)

    def test_every_record_of_every_collection_is_the_same_apart_from_provenance(self):
        n = 0
        for t, b in self.both.items():
            for kind in self._kinds(b['m3']):
                if kind in EVIDENCE + ('ingest_receipt',):
                    continue
                m3 = {r.key: [comparable(h.payload) for h in b['m3']['s'].history(kind, r.key)] for r in b['m3']['s'].query(kind)}
                au = {r.key: [comparable(h.payload) for h in b['auif']['s'].history(kind, r.key)] for r in b['auif']['s'].query(kind)}
                if kind == 'repro_record':
                    continue                     # run records pin payload hashes, which include provenance: compared through their results below
                with self.subTest(tenant=t, kind=kind):
                    self.assertEqual(sorted(au), sorted(m3))
                    self.assertEqual(au, m3)
                    n += sum(len(v) for v in au.values())
        self.assertGreater(n, 2000)

    def test_rejected_duplicate_and_stale_evidence_and_receipts_match(self):
        for t, b in self.both.items():
            for kind in EVIDENCE:
                f = lambda w: sorted(json.dumps(comparable(r.payload), sort_keys=True) for r in w['s'].query(kind))
                self.assertEqual(f(b['auif']), f(b['m3']), (t, kind))
            empty = {r.payload['file_name'] for r in b['m3']['s'].query('ingest_receipt') if r.payload['counts']['rows'] == 0}
            g = lambda w: sorted(json.dumps({k: r.payload[k] for k in RECEIPT_FIELDS}, sort_keys=True) for r in w['s'].query('ingest_receipt') if r.payload['file_name'] not in empty)
            self.assertEqual(g(b['auif']), g(b['m3']), t)
            self.assertEqual(len(empty), len(EMPTY[t]), t)                                  # M8-R1: one M3 empty receipt per declared empty source ...
            self.assertFalse([r for r in b['auif']['s'].query('ingest_receipt') if r.payload['file_name'] in empty], t)     # ... and no AUIF receipt for it
            self.assertEqual({n: r['counts'] for n, r in b['auif']['receipts'].items() if n not in empty}, {n: r['counts'] for n, r in b['m3']['receipts'].items() if n not in empty}, t)
            self.assertEqual({b['auif']['receipts'][n]['status'] for n in empty}, {'blocked'} if empty else set(), t)

    def test_exclusions_are_the_same(self):
        for t, b in self.both.items():
            a, p = views.invoice_cost_view(b['auif']['s'], AS_OF)
            a3, p3 = views.invoice_cost_view(b['m3']['s'], AS_OF)
            self.assertEqual((a.cents, a.excluded, a.included, p.cents), (a3.cents, a3.excluded, a3.included, p3.cents), t)
            self.assertEqual(views.gst_view(b['auif']['s']).left_out, views.gst_view(b['m3']['s']).left_out, t)
            self.assertEqual(views.review_table(b['auif']['s']), views.review_table(b['m3']['s']), t)

    def test_the_assessment_returns_the_figures_and_detection_results_the_m3_path_gives(self):
        for t, b in self.both.items():
            au, m3 = b['auif'], b['m3']
            expected = sorted({p for env in au['env'] for p in env.bindings[t].expected()})
            for prj in sorted(r.key for r in m3['s'].query('project')):
                with self.subTest(tenant=t, project=prj):
                    a = assess.run_assessment(au['s'], au['clock'], expected, prj, AS_OF, au['fv'], au['dv'])
                    reg = C.fin_registry()
                    d3 = DET.run_project(m3['s'], DET.det_registry(), m3['clock'], prj, AS_OF, m3['fv'], m3['dv'])['result']
                    if EMPTY[t]:                                                        # M8-R1: the assessment refuses; the data still agree with the M3 path
                        self.assertEqual((a['status'], a['figures'], a['signals']), ('cannot_assess', None, None))
                        self.assertEqual(sorted((r['code'], r['scope']) for r in a['reasons']), sorted(('SOURCE_EMPTY', x) for x in EMPTY[t]))
                        for name, fid, extra in assess.FIGURES:
                            self.assertEqual(C.run_calc(au['s'], reg, au['clock'], fid, prj, AS_OF, au['fv'], extra)['result'], C.run_calc(m3['s'], reg, m3['clock'], fid, prj, AS_OF, m3['fv'], extra)['result'], name)
                        da = DET.run_project(au['s'], DET.det_registry(), au['clock'], prj, AS_OF, au['fv'], au['dv'])['result']
                        self.assertEqual((da['signals'], da['rule_runs']), (d3['signals'], d3['rule_runs']))
                        continue
                    self.assertEqual(a['status'], 'assessed', a['reasons'][:3])
                    for name, fid, extra in assess.FIGURES:
                        self.assertEqual(a['figures'][name], C.run_calc(m3['s'], reg, m3['clock'], fid, prj, AS_OF, m3['fv'], extra)['result'], name)
                    self.assertEqual((a['signals'], a['rule_runs']), (d3['signals'], d3['rule_runs']))
            ta = DET.run_tenant(au['s'], DET.det_registry(), au['clock'], AS_OF, au['dv'])['result']
            tm = DET.run_tenant(m3['s'], DET.det_registry(), m3['clock'], AS_OF, m3['dv'])['result']
            self.assertEqual(ta, tm, t)

    def test_the_assessment_status_is_the_same_on_both_paths(self):
        for t, b in self.both.items():
            expected = sorted({p for env in b['auif']['env'] for p in env.bindings[t].expected()})
            st_auif = gate.assessment_status(b['auif']['s'], expected)
            st_m3 = gate.receipt_status(b['m3']['receipts'], sorted(b['m3']['receipts']))
            if EMPTY[t]:                                                               # M8-R1: refused for exactly the declared empty sources
                self.assertEqual((st_auif['status'], sorted((r['code'], r['scope']) for r in st_auif['reasons'])), ('cannot_assess', sorted(('SOURCE_EMPTY', x) for x in EMPTY[t])), t)
            else:
                self.assertEqual((st_auif['status'], st_auif['reasons']), ('can_assess', []), t)
            self.assertEqual((st_m3['status'], st_m3['reasons']), ('can_assess', []), t)
            self.assertEqual(len(expected), len(b['m3']['receipts']), t)

    def test_audit_chains_are_valid_on_both_paths(self):
        for t, b in self.both.items():
            for p in ('m3', 'auif'):
                self.assertTrue(b[p]['audit'].verify(b[p]['s'].ctx).ok, (t, p))


if __name__ == '__main__':
    unittest.main()
