"""No fallback assessment (M8 acceptance): for invalid, ambiguous, stale, deferred, partial, wrong-tenant, missing-field and type-mismatched data, and degraded states, the
assessment is "cannot assess" with a reason; no old, default or partial value is shown as current.  Each case also checks that a blocked import wrote NOTHING to the record
collections, and (where the fault can be cleared) that a clean re-import makes the assessment possible again.  Deferred and out-of-order events: test_m8_events.py."""
import copy, csv, io, json, os, shutil, tempfile, unittest
from ._auif import (AS_OF, HERE_ROOT, PK, client, codes, copy_folder, load_full, records, rewrite_csv, single, status, world)
from apg_auif import assess, definitions as DEF

CSV_HEADERS = {'payment': ['payment_id', 'invoice_id', 'payment_date', 'amount_cents'],
               'credit_note': ['credit_id', 'supplier_id', 'against_invoice_id', 'credit_date', 'ex_gst_cents', 'gst_cents']}


def _rows(folder, fname):
    with open(os.path.join(HERE_ROOT, 'builder_zero', 'zero_one', folder, fname), encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def json_world(entity, items, filename):
    """An integration reading `items` from a JSON file through AUIF's own file importer, with a pack generated for the GOOD layout (all keys present, all text)."""
    from auif_ext.connectors.file_import import FileImportConnector, FileSpec
    cfg = client.load_config(HERE_ROOT)
    defs = DEF.by_entity(cfg['definitions'])
    d = tempfile.mkdtemp()
    good = [{k: str(v) for k, v in it.items()} for it in items]
    for it in good:
        for k in CSV_HEADERS[entity]:
            it.setdefault(k, 'x')
    open(os.path.join(d, filename), 'w').write(json.dumps(good))
    fp = PK.fingerprint_of(FileImportConnector(d, {entity: FileSpec(filename, fmt='json')}))
    p = PK.build_pack('json-' + entity.replace('_', '-'), defs, [entity], [fp])
    cfg['packs'][p['pack_id']] = p
    open(os.path.join(d, filename), 'w').write(json.dumps(items))
    clock, prov, store, audit, who = world()
    s = who('t', 'zero_one', 'ann')
    env = client.AuifEnvironment(HERE_ROOT, cfg)
    env.bind('zero_one', s, clock)
    iid = p['pack_id'][len('apg-m8-'):]
    conn = FileImportConnector(d, {entity: FileSpec(filename, fmt='json')}, connector_id=PK.CONNECTOR[0], version=PK.CONNECTOR[1])
    env.add_integration('zero_one', iid, conn, p, 'accounting', [entity], {entity: env.entity_config(entity, file_name=filename)})
    env.start()
    env.activate('zero_one', iid)
    return dict(env=env, s=s, iid=iid, dir=d, clock=clock)


def _blocked(t, w, entity, code, summary=None):
    s = summary or w['env'].import_entity('zero_one', w['iid'], entity)
    t.assertEqual(s['status'], 'blocked', s)
    t.assertIn(code, {c for c, _ in s['reasons']})
    t.assertEqual(len(w['s'].query(entity)), 0, 'a blocked import wrote records')
    st = status(w['s'], w['env'], expected=[(w['iid'], entity)])
    t.assertEqual(st['status'], 'cannot_assess')
    t.assertIn(code, codes(st))
    return st


class TestInvalidAmbiguousAndTypeMismatched(unittest.TestCase):
    def test_a_value_that_is_not_text_is_translation_invalid(self):
        items = [dict(r) for r in _rows('SRC-01_accounting', 'payments.csv')[:3]]
        items[1]['amount_cents'] = 12500
        w = json_world('payment', items, 'payments.json')
        try:
            _blocked(self, w, 'payment', 'TRANSLATION_INVALID')
        finally:
            shutil.rmtree(w['dir'])

    def test_a_required_key_missing_from_one_object_is_translation_invalid(self):
        items = [dict(r) for r in _rows('SRC-01_accounting', 'payments.csv')[:3]]
        del items[2]['payment_date']
        w = json_world('payment', items, 'payments.json')
        try:
            _blocked(self, w, 'payment', 'TRANSLATION_INVALID')
        finally:
            shutil.rmtree(w['dir'])

    def test_an_optional_key_missing_from_one_object_is_a_missing_field(self):
        items = [dict(r) for r in _rows('SRC-01_accounting', 'credit_notes.csv')] * 1
        items = [dict(items[0]), dict(items[0], credit_id='CRN-9002')]
        del items[1]['gst_cents']
        w = json_world('credit_note', items, 'credit_notes.json')
        try:
            _blocked(self, w, 'credit_note', 'MISSING_FIELD')
        finally:
            shutil.rmtree(w['dir'])

    def test_an_unparseable_required_amount_is_rejected_as_m3_rejects_it_and_stops_the_assessment(self):
        d = copy_folder('zero_one', 'SRC-01_accounting')
        try:
            def bad(h, b):
                b[3][h.index('ex_gst_cents')] = '12.5'
                return h, b
            rewrite_csv(os.path.join(d, 'ap_invoices.csv'), bad)
            w = single('bz-accounting', base_dir=d)
            s = w['env'].import_entity('zero_one', 'bz-accounting', 'ap_invoice')
            self.assertEqual((s['status'], s['receipt']['counts']['rejected']), ('applied', 1))
            st = status(w['s'], w['env'], expected=[('bz-accounting', 'ap_invoice')])
            self.assertEqual(codes(st), ['ROW_REJECTED'])
        finally:
            shutil.rmtree(d)

    def test_an_unparseable_optional_value_is_held_as_m3_holds_it_and_stops_the_assessment(self):
        d = copy_folder('zero_one', 'SRC-01_accounting')
        try:
            def bad(h, b):
                b[3][h.index('gst_cents')] = 'abc'
                return h, b
            rewrite_csv(os.path.join(d, 'ap_invoices.csv'), bad)
            w = single('bz-accounting', base_dir=d)
            w['env'].import_entity('zero_one', 'bz-accounting', 'ap_invoice')
            self.assertEqual(codes(status(w['s'], w['env'], expected=[('bz-accounting', 'ap_invoice')])), ['VALUE_INVALID'])
        finally:
            shutil.rmtree(d)

    def test_an_ambiguous_object_is_not_delivered_and_stops_the_assessment(self):
        from auif.translation import pack_hash
        cfg = client.load_config(HERE_ROOT)
        p = copy.deepcopy(cfg['packs']['apg-m8-bz-master'])
        p['mappings'] = [m for m in p['mappings'] if m['source_ref'] != 'supplier.abn_synthetic']
        p['unmapped_field_policy']['default_outcome'] = 'AMBIGUOUS'
        p['artifact_hash'] = pack_hash(p)
        cfg['packs'][p['pack_id']] = p
        w = single('bz-master', config=cfg)
        w['iid'] = 'bz-master'
        _blocked(self, w, 'supplier', 'AMBIGUOUS')

    def test_a_pack_with_an_ambiguous_mapping_never_activates(self):
        from auif.translation import pack_hash
        cfg = client.load_config(HERE_ROOT)
        p = copy.deepcopy(cfg['packs']['apg-m8-bz-master'])
        m = next(x for x in p['mappings'] if x['source_ref'] == 'supplier.abn_synthetic')
        m.update(mapping_state='AMBIGUOUS', ambiguity={'candidate_meanings': ['tax number', 'company number'], 'resolution_required': True})
        m.pop('validation_ref'); m.pop('deterministic_validation_performed')
        p['artifact_hash'] = pack_hash(p)
        cfg['packs'][p['pack_id']] = p
        w = single('bz-master', config=cfg)
        self.assertEqual(w['binding'].state('bz-master')['state'], 'SEMANTIC_AMBIGUITY')
        w['iid'] = 'bz-master'
        st = _blocked(self, w, 'supplier', 'INTEGRATION_NOT_ACTIVE')


class TestStaleDriftedAndDegraded(unittest.TestCase):
    def test_schema_drift_after_activation_stops_the_assessment_and_keeps_the_stored_records_unchanged(self):
        d = copy_folder('zero_one', 'reference')
        try:
            w = single('bz-master', base_dir=d)
            w['env'].import_entity('zero_one', 'bz-master', 'supplier')
            before = records(w['s'], 'supplier')
            self.assertEqual(status(w['s'], w['env'])['status'], 'can_assess')
            rewrite_csv(os.path.join(d, 'suppliers.csv'), lambda h, b: (h + ['extra'], [r + ['x'] for r in b]))
            w['env'].fabric.integration(w['env'].ctx['zero_one'], 'bz-master').check_drift()
            self.assertEqual(w['binding'].state('bz-master')['state'], 'SCHEMA_DRIFT')
            st = status(w['s'], w['env'])
            self.assertIn('INTEGRATION_NOT_ACTIVE', codes(st))
            s = w['env'].import_entity('zero_one', 'bz-master', 'supplier')
            self.assertEqual(s['status'], 'blocked')
            self.assertEqual(records(w['s'], 'supplier'), before)
        finally:
            shutil.rmtree(d)

    def test_a_revalidated_integration_makes_earlier_imports_stale_until_reimported(self):
        w = single('bz-master')
        env, ctx = w['env'], w['env'].ctx['zero_one']
        env.import_entity('zero_one', 'bz-master', 'supplier')
        old = w['binding'].state('bz-master')['manifest_ref']['version']
        c = env.fabric.integration(ctx, 'bz-master')
        c.suspend('operator check')
        self.assertIn('INTEGRATION_NOT_ACTIVE', codes(status(w['s'], env)))
        c.resume()
        new = w['binding'].state('bz-master')['manifest_ref']['version']
        self.assertNotEqual(old, new)
        st = status(w['s'], env)
        self.assertEqual(codes(st), ['STALE_MANIFEST'])
        env.import_entity('zero_one', 'bz-master', 'supplier')
        self.assertEqual(status(w['s'], env)['status'], 'can_assess')

    def test_a_pack_upgrade_apg_has_not_pinned_is_refused(self):
        from auif.translation import pack_hash
        cfg = client.load_config(HERE_ROOT)
        w = single('bz-master', config=cfg)
        env, ctx = w['env'], w['env'].ctx['zero_one']
        p2 = copy.deepcopy(cfg['packs']['apg-m8-bz-master'])
        p2['pack_version'] = '0.1.1'
        p2['artifact_hash'] = pack_hash(p2)
        env.packs.register(p2)
        env.fabric.integration(ctx, 'bz-master').apply_pack_upgrade(PK.ref(p2))       # an operator action in AUIF; APG's binding still pins 0.1.0
        w['iid'] = 'bz-master'
        _blocked(self, w, 'supplier', 'PACK_NOT_PINNED')

    def test_a_stale_delivery_is_recorded_not_applied_and_stops_the_assessment(self):
        d = copy_folder('zero_one', 'SRC-02_costing')
        try:
            def label(rev, cents):
                def f(h, b):
                    b[0][h.index('revision')] = rev
                    b[0][h.index('budget_cents')] = cents
                    return h, b
                return f
            rewrite_csv(os.path.join(d, 'budget_lines.csv'), label('R2', '34560000'))        # the source says revision 2
            w = single('bz-job-costing', base_dir=d)
            w['env'].import_entity('zero_one', 'bz-job-costing', 'budget_line')
            before = records(w['s'], 'budget_line')
            key = 'PRJ-001|CC-01'
            self.assertEqual(before[key]['source_revision'], 2)
            older = label('R1', '1')                                                            # later the source sends revision 1 with other content
            rewrite_csv(os.path.join(d, 'budget_lines.csv'), older)
            s = w['env'].import_entity('zero_one', 'bz-job-costing', 'budget_line')
            self.assertEqual(s['receipt']['counts']['stale'], 1)
            self.assertEqual(records(w['s'], 'budget_line')[key], before[key])
            self.assertEqual(codes(status(w['s'], w['env'], expected=[('bz-job-costing', 'budget_line')])), ['STALE_DELIVERY'])
        finally:
            shutil.rmtree(d)

    def test_a_source_that_cannot_be_reached_at_activation(self):
        d = tempfile.mkdtemp()
        os.rmdir(d)
        w = single('bz-master', base_dir=d)
        self.assertNotEqual(w['binding'].state('bz-master')['state'], 'ACTIVE')
        w['iid'] = 'bz-master'
        _blocked(self, w, 'supplier', 'INTEGRATION_NOT_ACTIVE')

    def test_an_integration_that_never_reported_a_state(self):
        clock, prov, store, audit, who = world()
        s = who('t', 'zero_one', 'ann')
        env = client.AuifEnvironment(HERE_ROOT)
        env.bind('zero_one', s, clock)
        env.add_file_integration('zero_one', 'bz-master')
        env.start()
        st = gate.assessment_status(s, env.bindings['zero_one'].expected(), env.module)
        self.assertEqual(codes(st), ['NOT_IMPORTED', 'NO_STATE'])


from apg_auif import gate  # noqa: E402


class TestPartial(unittest.TestCase):
    def test_a_file_removed_after_activation(self):
        d = copy_folder('zero_one', 'reference')
        w = single('bz-master', base_dir=d)
        shutil.rmtree(d)
        w['iid'] = 'bz-master'
        st = _blocked(self, w, 'supplier', 'SOURCE_UNAVAILABLE')
        self.assertIn('SYNC_FAILED', codes(st))

    def test_a_read_that_fails_after_the_first_page_writes_nothing(self):
        from auif_ext.connectors.file_import import FileImportConnector
        from auif.errors import TransportError
        w = single('bz-accounting')
        c = w['env'].fabric.integration(w['env'].ctx['zero_one'], 'bz-accounting')
        real, calls = c.runtime.c.read, []

        def flaky(req):
            calls.append(req)
            if len(calls) >= 2:                                                  # the outage persists past AUIF's own retries
                raise TransportError('UNAVAILABLE', applied='NOT_APPLIED', message='synthetic outage')
            return real(req)
        c.runtime.c.read = flaky
        w['iid'] = 'bz-accounting'
        s = w['env'].import_entity('zero_one', 'bz-accounting', 'ap_invoice')
        self.assertGreater(len([1 for _ in calls]), 1)
        _blocked(self, w, 'ap_invoice', 'SYNC_FAILED', s)

    def test_a_delivery_lost_between_auif_and_apg(self):
        w = single('bz-master')
        m = w['env'].module
        real = m._pair
        n = []

        def lossy(ctx, ob, kind):
            n.append(1)
            if len(n) != 5:
                real(ctx, ob, kind)
            else:
                m.current[ctx.tenant_id].waiting.pop(ob['observation_id'])        # the object and its observation vanish together
        m._pair = lossy
        w['iid'] = 'bz-master'
        _blocked(self, w, 'supplier', 'SYNC_INCOMPLETE')

    def test_a_read_that_stops_at_the_page_limit_is_incomplete(self):
        w = single('bz-accounting')
        env = w['env']
        real = env._expect
        env._expect = lambda t, i, e: dict(real(t, i, e), page_size=50, max_pages=2)
        w['iid'] = 'bz-accounting'
        _blocked(self, w, 'ap_invoice', 'SYNC_INCOMPLETE')


class TestWrongTenant(unittest.TestCase):
    def test_deliveries_for_a_tenant_apg_is_not_bound_to_are_refused_and_stored_nowhere(self):
        w = single('bz-master')
        env = w['env']
        ctx2 = env.auth.issue('zero_two', 'apg-m8-import')
        conn = PK.connector(HERE_ROOT, 'zero_two', 'bz-master', env.templates)
        env.fabric.add_integration(ctx2, integration_id='bz-master', anchor_module='apg', connector=conn, pack_ref=w['binding'].integrations['bz-master']['pack_ref'],
                                   target_system_id='bz-master', environment_id=client.ENVIRONMENT_ID, entities=['supplier'], identity_fields={'supplier': 'supplier_id'})
        env.fabric.integration(ctx2, 'bz-master').activate()
        env.fabric.sync(ctx2, 'bz-master', 'supplier', max_pages=5, page_size=50)
        self.assertTrue(any(r[0] == 'UNBOUND_TENANT' for r in env.module.unbound_refusals))
        self.assertEqual(len(w['s'].query('supplier')), 0)

    def test_an_object_naming_another_tenant_is_refused(self):
        w = single('bz-master')
        tr = w['env'].fabric.translator
        real = tr.translate_inbound

        def forged(*a, **k):
            o = real(*a, **k)
            o['tenant_id'] = 'zero_two'
            return o
        tr.translate_inbound = forged
        w['iid'] = 'bz-master'
        _blocked(self, w, 'supplier', 'WRONG_TENANT')

    def test_a_value_naming_another_tenant_is_refused_by_the_apg_tenant_screen(self):
        d = copy_folder('zero_one', 'reference')
        try:
            def claim(h, b):
                b[0][h.index('name')] = '{"tenantId": "zero_two"}'
                return h, b
            rewrite_csv(os.path.join(d, 'suppliers.csv'), claim)
            w = single('bz-master', base_dir=d)
            w['iid'] = 'bz-master'
            _blocked(self, w, 'supplier', 'WRONG_TENANT')
        finally:
            shutil.rmtree(d)


class TestAlertsAndAdapterFailures(unittest.TestCase):
    def test_an_auif_error_outside_an_import_blocks_until_the_integration_is_imported_again(self):
        d = copy_folder('zero_one', 'reference')
        try:
            w = single('bz-master', base_dir=d)
            env = w['env']
            env.import_entity('zero_one', 'bz-master', 'supplier')
            os.rename(os.path.join(d, 'suppliers.csv'), os.path.join(d, 'gone'))
            env.fabric.sync(env.ctx['zero_one'], 'bz-master', 'supplier')         # someone reads around the APG client; AUIF reports an error to the module
            self.assertIn('AUIF_ERROR_OUTSIDE_IMPORT', codes(status(w['s'], env)))
            os.rename(os.path.join(d, 'gone'), os.path.join(d, 'suppliers.csv'))
            env.import_entity('zero_one', 'bz-master', 'supplier')
            self.assertEqual(status(w['s'], env)['status'], 'can_assess')
        finally:
            shutil.rmtree(d)

    def test_a_failure_inside_the_adapter_is_never_silent(self):
        w = single('bz-master')
        m = w['env'].module

        def boom(ctx, obj):
            raise RuntimeError('synthetic adapter fault')
        m._on_entity = boom
        m._h['entity'] = [m._guarded('entity')]
        w['iid'] = 'bz-master'
        _blocked(self, w, 'supplier', 'ADAPTER_ERROR')


class TestNoOldValueShownAsCurrent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = load_full()

    def test_a_degraded_integration_withdraws_the_assessment_and_returns_no_earlier_figure(self):
        w = self.w
        good = assess.run_assessment(w['s'], w['clock'], w['expected'], 'PRJ-002', AS_OF, w['fv'], w['dv'], w['env'].module)
        self.assertEqual(good['status'], 'assessed')
        c = w['env'].fabric.integration(w['env'].ctx['zero_one'], 'bz-accounting')
        c.suspend('synthetic outage')
        try:
            bad = assess.run_assessment(w['s'], w['clock'], w['expected'], 'PRJ-002', AS_OF, w['fv'], w['dv'], w['env'].module)
            self.assertEqual((bad['status'], bad['figures'], bad['signals'], bad['run_keys']), ('cannot_assess', None, None, []))
            self.assertIn('INTEGRATION_NOT_ACTIVE', {r['code'] for r in bad['reasons']})
            self.assertNotIn(good['run_keys'][0], json.dumps(bad))
            self.assertIsNotNone(w['s'].get('repro_record', good['run_keys'][0]))           # the earlier run is still stored, under its own as-of: never presented as current
        finally:
            c.resume()
            for iid, ent, f in w['plan']:
                if iid == 'bz-accounting':
                    w['env'].import_entity('zero_one', iid, ent)
        self.assertEqual(assess.run_assessment(w['s'], w['clock'], w['expected'], 'PRJ-002', AS_OF, w['fv'], w['dv'], w['env'].module)['status'], 'assessed')

    def test_a_change_while_the_figures_are_computed_withdraws_the_result(self):
        w = self.w
        from apg.fin import calc_records as C
        real, n = C.run_calc, []

        def racing(*a, **k):
            n.append(1)
            if len(n) == 3:
                w['env'].fabric.integration(w['env'].ctx['zero_one'], 'bz-market').suspend('changed mid-run')
            return real(*a, **k)
        C.run_calc = racing
        try:
            r = assess.run_assessment(w['s'], w['clock'], w['expected'], 'PRJ-001', AS_OF, w['fv'], w['dv'], w['env'].module)
        finally:
            C.run_calc = real
            c = w['env'].fabric.integration(w['env'].ctx['zero_one'], 'bz-market')
            c.resume()
            for iid, ent, f in w['plan']:
                if iid == 'bz-market':
                    w['env'].import_entity('zero_one', iid, ent)
        self.assertEqual((r['status'], r['figures'], r['signals']), ('cannot_assess', None, None))


if __name__ == '__main__':
    unittest.main()
