"""APG-M10: the prototype's view model against the APG code it reads.  Synthetic Builder Zero data only.
The model is built once for the module (about 16 s) and the stored ui/data/views.js must equal it byte for byte."""
import json, os, re, unittest
from . import ROOT
from apg_ui import viewmodel as VM, plain as PL
from apg.fin import calc_records as C
from apg.det import findings as FD

MODEL = None
TEXT = None


def setUpModule():
    global MODEL, TEXT
    MODEL = VM.build_views(ROOT)
    TEXT = VM.dumps(MODEL)


def stored():
    t = open(os.path.join(ROOT, 'ui', 'data', 'views.js'), encoding='utf-8').read()
    return t, json.loads(t[t.index('window.APG_VIEWS = ') + len('window.APG_VIEWS = '):].rstrip().rstrip(';'))


def amounts(x, path=''):
    """Every amount object in the model: a dict carrying both 'cents' and 'ev'."""
    if isinstance(x, dict):
        if 'cents' in x and 'ev' in x:
            yield path, x
        for k, v in x.items():
            if k != 'evidence':
                yield from amounts(v, path + '/' + str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from amounts(v, path + '/%d' % i)


class TestTheStoredFileIsTheBuild(unittest.TestCase):
    def test_ui_data_views_js_equals_a_fresh_build_byte_for_byte(self):
        t, m = stored()
        self.assertEqual(m, json.loads(TEXT))
        import importlib.util
        spec = importlib.util.spec_from_file_location('build_m10_views', os.path.join(ROOT, 'tools', 'build_m10_views.py'))
        B = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(B)
        self.assertEqual(t, B.wrap(TEXT))

    def test_the_three_views_are_the_declared_people(self):
        self.assertEqual(MODEL['meta']['order'], ['zero_one-director', 'zero_two-director', 'zero_one-project-manager'])
        self.assertEqual(MODEL['meta']['order'][0], 'zero_one-director')                         # director first, as authorised


class TestEveryAmountIsAnApgValueWithItsEvidence(unittest.TestCase):
    def test_every_amount_names_an_evidence_entry_of_its_own_view(self):
        for vid, v in MODEL['views'].items():
            n = 0
            for path, a in amounts(v):
                n += 1
                self.assertIn(a['ev'], v['evidence'], '%s %s' % (vid, path))
            self.assertGreater(n, 20, vid)

    def test_every_project_figure_equals_a_fresh_apg_calculation_in_value_and_state(self):
        for tenant, vid in (('zero_one', 'zero_one-director'), ('zero_two', 'zero_two-director')):
            W = VM.build_world(ROOT, tenant)
            reg = C.fin_registry()
            v = MODEL['views'][vid]
            for p in v['projects']:
                for key, title, fid, extra in VM.FIGURES:
                    fig = C.run_calc(W['s'], reg, W['clock'], fid, p['id'], VM.AS_OF, W['fv'], extra)['result']
                    shown = p['figures'][key]
                    self.assertEqual((shown['cents'], shown['state']), ((fig.get('value') or {}).get('cents'), fig['state']), (vid, p['id'], key))
                    self.assertEqual(v['evidence'][shown['ev']]['cents'], shown['cents'])
                    self.assertEqual([r['code'] for r in shown['reasons']], list(fig.get('reasons', [])))
                ctc = C.run_calc(W['s'], reg, W['clock'], 'fin.forecast', p['id'], VM.AS_OF, W['fv'], None)['result']['components']['cost_to_complete']
                self.assertEqual((p['figures']['cost_to_complete']['cents'], p['figures']['cost_to_complete']['state']), (ctc['value']['cents'], ctc['state']))
                rec = W['s'].get('project', p['id']).payload['fields']
                self.assertEqual(p['contract_value']['cents'], rec['contract_value_cents'])

    def test_a_figure_that_cannot_be_assessed_has_no_value_and_says_why(self):
        seen = 0
        for v in MODEL['views'].values():
            for p in v['projects']:
                for k, f in p['figures'].items():
                    if f['state'] == 'cannot_assess':
                        seen += 1
                        self.assertIsNone(f['cents'], (p['id'], k))
                        self.assertTrue(f['reasons'], (p['id'], k))
        self.assertEqual(seen, 4)                                    # PRJ-001 cash-adjusted margin and retention carrying cost, in two views of zero_one

    def test_every_finding_amount_is_the_findings_own_quantification(self):
        W = VM.build_world(ROOT, 'zero_two')
        v = MODEL['views']['zero_two-director']
        mine = {f['finding_id']: f for f in FD.all_findings(W['s'])}
        for f in v['findings']:
            q = mine[f['id']]['signal']['quantification']
            self.assertEqual(f['amount']['cents'], q.get('gross_cents') if q.get('status') == 'quantified' else None)
            self.assertEqual(f['amount']['label'], q.get('label') if q.get('status') == 'quantified' else 'none')
        for f in MODEL['views']['zero_one-director']['findings']:
            ev = MODEL['views']['zero_one-director']['evidence'][f['ev']]
            q = ev['quantification']
            self.assertEqual(f['amount']['cents'], q.get('gross_cents') if q.get('status') == 'quantified' else None)

    def test_nothing_is_totalled_across_projects(self):
        for v in MODEL['views'].values():
            self.assertEqual(sorted(v), sorted(['view', 'tenant', 'builder', 'person', 'access', 'as_of', 'projects', 'figure_states', 'exposure', 'findings', 'recommendations',
                                                'recommendation_statement', 'approvals', 'data_health', 'tenant_materials', 'workflow', 'policies', 'evidence']))
            self.assertNotRegex(json.dumps({k: v[k] for k in v if k != 'evidence'}), r'"(portfolio_)?total(_cents)?"')
            for e in v['exposure']:                                  # a range per interpretation, as apg/det/portfolio.py gives it
                self.assertIn(e['lower']['label'], ('range',))


class TestNoEstimateIsARealisedSaving(unittest.TestCase):
    def test_no_amount_is_labelled_realised_or_verified(self):
        for vid, v in MODEL['views'].items():
            for path, a in amounts(v):
                self.assertNotIn(str(a.get('label', '')).lower(), ('realised', 'realized', 'verified', 'saving', 'savings'), (vid, path))
            self.assertNotRegex(json.dumps(v), r'"realised_net_cents"|"verified_outcome"')

    def test_an_estimated_net_benefit_is_shown_only_when_apg_estimated_it_and_is_labelled_estimate(self):
        for v in MODEL['views'].values():
            for r in v['recommendations']:
                if r['net_status'] == 'estimated':
                    self.assertEqual(r['estimated_net']['label'], 'estimate')
                    self.assertIsNotNone(r['estimated_net']['cents'])
                else:
                    self.assertIsNone(r['estimated_net']['cents'])
                self.assertIn('not', (r['not_a_claim'] or '').lower())

    def test_scenarios_never_change_the_forecast_and_are_labelled_scenario(self):
        n = 0
        for p in MODEL['views']['zero_one-director']['projects']:
            for req in (p['materials'] or {}).get('requirements', []):
                for s in req['scenarios']:
                    n += 1
                    self.assertIs(s['changes_authoritative_forecast'], False)
                    for a in (s['landed_total'], s['incremental_total']):
                        if a:
                            self.assertEqual(a['label'], 'scenario')
                    for a in s['potential_difference']:
                        self.assertEqual(a['label'], 'estimate')
        self.assertGreater(n, 10)


class TestWhatEachPersonMaySee(unittest.TestCase):
    def test_the_project_manager_sees_only_prj_001_and_no_builder_wide_material(self):
        v = MODEL['views']['zero_one-project-manager']
        text = json.dumps(v)
        self.assertNotIn('PRJ-002', text)
        self.assertNotIn('PRJ-003', text)
        self.assertEqual(v['access'], {'tenant_level': False, 'projects': ['PRJ-001'], 'approve': []})
        self.assertIsNone(v['data_health'])
        self.assertIsNone(v['tenant_materials'])
        self.assertFalse([f for f in v['findings'] if f['level'] == 'tenant'])
        self.assertTrue(all(a['present']['can_approve'] is False and a.get('token') is None for a in v['approvals']))

    def test_one_builder_never_sees_the_other(self):
        self.assertNotIn('zero_one', json.dumps(MODEL['views']['zero_two-director']))
        self.assertNotIn('zero_two', json.dumps(MODEL['views']['zero_one-director']))

    def test_the_port_is_asked_and_its_answer_must_be_exactly_true(self):
        port = VM.Grants({('zero_one', 'pat', 'PRJ-001'): ('view',)})
        ctx = type('Ctx', (), {'tenant_id': 'zero_one', 'user_id': 'pat'})()
        self.assertIs(port.allows(ctx, {'level': 'project', 'project': 'PRJ-001'}, 'view'), True)
        self.assertIs(port.allows(ctx, {'level': 'project', 'project': 'PRJ-001'}, 'approve'), False)
        self.assertIs(port.allows(ctx, {'level': 'tenant'}, 'view'), False)


class TestApprovals(unittest.TestCase):
    def test_the_request_the_screen_would_send_is_exactly_the_token_present_gave(self):
        v = MODEL['views']['zero_one-director']
        waiting = [a for a in v['approvals'] if a['present']['can_approve']]
        self.assertEqual(len(waiting), 2)
        for a in waiting:
            t = a['token']
            self.assertEqual({k: a['request'][k] for k in ('finding_id', 'version', 'digest', 'proposal')}, {'finding_id': t['finding_id'], 'version': t['version'], 'digest': t['digest'], 'proposal': t['proposal']})

    def test_the_one_approval_is_in_force_for_exactly_its_version_digest_and_proposal(self):
        v = MODEL['views']['zero_one-director']
        done = [a for a in v['approvals'] if a.get('approved')]
        self.assertEqual(len(done), 1)
        self.assertEqual(done[0]['approved']['code'], 'OK')
        self.assertEqual(done[0]['in_force'], {'valid': True, 'code': 'OK'})
        self.assertEqual(done[0]['present']['can_approve'], False)                  # an approved proposal is not offered again


class TestDataHealth(unittest.TestCase):
    def test_zero_two_cannot_be_assessed_through_auif_for_exactly_the_cf53_record_types(self):
        decl = json.load(open(os.path.join(ROOT, 'auif_m8', 'PATH_EQUIVALENCE_DECLARED_DIFFERENCES.json'), encoding='utf-8'))['source_empty']
        cr = MODEL['views']['zero_two-director']['data_health']['connected_route']
        self.assertEqual(cr['status'], 'cannot_assess')
        self.assertEqual(sorted(r['scope'] for r in cr['reasons']), sorted(decl['zero_two']))
        self.assertEqual({r['code'] for r in cr['reasons']}, {'SOURCE_EMPTY'})
        self.assertEqual(MODEL['views']['zero_one-director']['data_health']['connected_route']['status'], 'can_assess')

    def test_the_file_route_gate_is_apg_auifs_receipt_gate(self):
        for vid in ('zero_one-director', 'zero_two-director'):
            self.assertEqual(MODEL['views'][vid]['data_health']['file_route']['gate']['status'], 'can_assess')


class TestThePagesSendNothing(unittest.TestCase):
    def test_the_prototype_code_has_no_network_call_and_loads_only_local_files(self):
        js = open(os.path.join(ROOT, 'ui', 'app.js'), encoding='utf-8').read()
        self.assertNotRegex(js, r'\bfetch\s*\(|XMLHttpRequest|WebSocket|sendBeacon|EventSource|import\s*\(|https?://')
        html = open(os.path.join(ROOT, 'ui', 'index.html'), encoding='utf-8').read()
        self.assertEqual(sorted(re.findall(r'(?:src|href)="([^"#]+)"', html)), ['app.css', 'app.js', 'data/views.js'])
        css = open(os.path.join(ROOT, 'ui', 'app.css'), encoding='utf-8').read()
        self.assertNotRegex(css, r'https?://|@import')


class TestPlainWording(unittest.TestCase):
    def test_the_code_is_always_kept_and_an_unknown_code_gets_no_invented_words(self):
        self.assertEqual(PL.reason('SOURCE_EMPTY')['code'], 'SOURCE_EMPTY')
        self.assertEqual(PL.reason('SOMETHING_NEW:1'), {'code': 'SOMETHING_NEW:1', 'plain': None})
        self.assertEqual(PL.reason('COMPONENT_PROVISIONAL:actual_cost')['code'], 'COMPONENT_PROVISIONAL:actual_cost')


if __name__ == '__main__':
    unittest.main()
