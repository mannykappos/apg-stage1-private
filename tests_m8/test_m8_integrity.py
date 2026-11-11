"""Deliveries that a correct AUIF never makes, forged inside the test to prove that every integrity check of the APG module stands on its own (each case defeats one check
that a mutant removes; tools/m8_mutants.py).  The forgery is done by wrapping an AUIF object in the test (the translator, the observation factory, an integration controller)
or by a handler placed in front of APG's own; AUIF's files are never changed.  Every case: the batch is refused with the named reason, nothing is stored, and the assessment
cannot proceed."""
import copy, unittest
from ._auif import HERE_ROOT, client, codes, single, status, world


def _w():
    w = single('bz-master')
    w['ctx'] = w['env'].ctx['zero_one']
    w['c'] = w['env'].fabric.integration(w['ctx'], 'bz-master')
    return w


def _wrap_translator(w, fn):
    tr = w['env'].fabric.translator
    real = tr.translate_inbound

    def forged(*a, **k):
        o = real(*a, **k)
        fn(o)
        return o
    tr.translate_inbound = forged


def _wrap_observation(w, fn):
    f = w['env'].fabric.obs
    real = f.build

    def forged(*a, **k):
        fn(k)
        return real(*a, **k)
    f.build = forged


def _before_apg(w, kind, fn):
    """A handler placed in FRONT of APG's own handler for `kind`: it changes the payload AUIF hands over, as a faulty runtime would."""
    w['env'].module._h[kind].insert(0, lambda ctx, p: fn(p))


class TestEachIntegrityCheckStandsAlone(unittest.TestCase):
    def _refused(self, w, code):
        s = w['env'].import_entity('zero_one', 'bz-master', 'supplier')
        self.assertEqual(s['status'], 'blocked', s)
        self.assertIn(code, {c for c, _ in s['reasons']})
        self.assertEqual(len(w['s'].query('supplier')), 0)
        st = status(w['s'], w['env'])
        self.assertEqual(st['status'], 'cannot_assess')
        self.assertIn(code, codes(st))

    def test_a_provenance_chain_out_of_order(self):
        w = _w()
        _wrap_translator(w, lambda o: o['provenance_chain'].insert(0, o['provenance_chain'].pop(1)))
        self._refused(w, 'LINEAGE_INCOMPLETE')

    def test_deliveries_under_another_manifest_than_the_one_the_integration_is_active_with(self):
        w = _w()
        _wrap_observation(w, lambda k: k.__setitem__('manifest_version', dict(k['manifest_version'], version='1.0.99', hash='0' * 64)))
        self._refused(w, 'STALE_MANIFEST')

    def test_values_that_are_not_what_auif_observed(self):
        w = _w()
        _wrap_translator(w, lambda o: o['attributes'].__setitem__('supplier_name', o['attributes']['supplier_name'] + ' (changed)'))
        self._refused(w, 'PAYLOAD_MISMATCH')

    def test_a_chain_naming_another_pack_hash(self):
        w = _w()
        _wrap_translator(w, lambda o: next(s for s in o['provenance_chain'] if s['step_kind'] == 'TRANSLATION_PACK').__setitem__('hash', '0' * 64))
        self._refused(w, 'PACK_NOT_PINNED')

    def test_a_schema_fingerprint_the_pinned_pack_does_not_accept(self):
        w = _w()
        w['c'].fp = dict(w['c'].fp, value='1' * 64)
        self._refused(w, 'SCHEMA_DRIFT')

    def test_a_chain_naming_another_source_object(self):
        w = _w()
        _wrap_translator(w, lambda o: next(s for s in o['provenance_chain'] if s['step_kind'] == 'SOURCE_OBJECT').__setitem__('ref', 'supplier/SUP-999'))
        self._refused(w, 'LINEAGE_MISMATCH')

    def test_a_delivery_that_is_not_in_order(self):
        w = _w()
        _wrap_observation(w, lambda k: k.__setitem__('ordering_state', 'DEFERRED'))
        self._refused(w, 'OUT_OF_ORDER')

    def test_an_attribute_that_is_not_text(self):
        w = _w()
        _before_apg(w, 'entity', lambda o: o['attributes'].__setitem__('abn_text', 5))
        self._refused(w, 'TYPE_MISMATCH')

    def test_an_object_of_another_concept(self):
        w = _w()
        _before_apg(w, 'entity', lambda o: o.__setitem__('canonical_type', 'module.apg.Project'))
        self._refused(w, 'TYPE_MISMATCH')

    def test_an_object_that_is_not_valid(self):
        w = _w()
        _before_apg(w, 'entity', lambda o: o.__setitem__('validation_state', 'AMBIGUOUS'))
        self._refused(w, 'TRANSLATION_INVALID')

    def test_a_source_identity_taken_from_the_wrong_field(self):
        clock, prov, store, audit, who = world()
        s = who('t', 'zero_one', 'ann')
        env = client.AuifEnvironment(HERE_ROOT)
        env.bind('zero_one', s, clock)
        from apg_auif import pack as PK
        conn = PK.connector(HERE_ROOT, 'zero_one', 'bz-master', env.templates)
        env._add('zero_one', 'bz-master', conn, env.cfg['packs']['apg-m8-bz-master'], 'master', ['supplier'], {'supplier': env.entity_config('supplier', file_name='suppliers.csv')},
                 identity_fields={'supplier': 'name'})                                  # a misconfigured integration: the supplier NAME as identity
        env.start()
        env.activate('zero_one', 'bz-master')
        self._refused(dict(env=env, s=s), 'IDENTITY_MISMATCH')

    def test_a_delivery_from_another_integration_while_this_one_is_imported(self):
        clock, prov, store, audit, who = world()
        s = who('t', 'zero_one', 'ann')
        env = client.AuifEnvironment(HERE_ROOT)
        env.bind('zero_one', s, clock)
        env.add_file_integration('zero_one', 'bz-master')
        env.add_file_integration('zero_one', 'bz-procurement')
        env.start()
        env.activate('zero_one', 'bz-master')
        env.activate('zero_one', 'bz-procurement')
        real = env.fabric.sync
        env.fabric.sync = lambda ctx, iid, entity, **kw: real(ctx, 'bz-procurement', 'supplier_quote', **kw) and {'pages': 1, 'delivered': 6, 'invalid': 0, 'ambiguous': 0,
                                                                                                                 'empty': False, 'failed': None, 'not_allowed': False}
        self._refused(dict(env=env, s=s), 'LINEAGE_MISMATCH')

    def test_a_state_change_seen_during_the_import_even_if_active_again_at_the_end(self):
        w = _w()
        cur = copy.deepcopy(w['c'].current())
        m = w['env'].module
        seen = []

        def flap(ob):
            if not seen:
                seen.append(1)
                m.receive_integration_state(w['ctx'], dict(cur, state='CONNECTION_FAILED'))
                m.receive_integration_state(w['ctx'], dict(cur))
        _before_apg(w, 'observation', flap)
        self._refused(w, 'INTEGRATION_NOT_ACTIVE')

    def test_a_new_manifest_learned_during_the_import(self):
        w = _w()
        cur = copy.deepcopy(w['c'].current())
        seen = []

        def revalidated(ob):
            if not seen:
                seen.append(1)
                w['binding'].record_state(dict(cur, manifest_ref=dict(cur['manifest_ref'], version='1.0.2', hash='2' * 64)))
        _before_apg(w, 'observation', revalidated)
        self._refused(w, 'STALE_MANIFEST')


    def test_deliveries_from_another_environment(self):
        w = _w()
        _before_apg(w, 'observation', lambda ob: ob.__setitem__('environment_id', 'another-environment'))
        self._refused(w, 'LINEAGE_MISMATCH')


def _invalid(state):
    def f(o):
        o['validation_state'] = state
        o.pop('attributes', None)
        o.pop('attribute_classifications', None)
        o['classification'] = 'INTERNAL'
        o['diagnostics'] = {'diagnostics_id': 'diag-forged', 'reasons': ['forged']}
    return f


class TestTheTransportReportStandsAlone(unittest.TestCase):
    """AUIF reports a problem twice: in the sync report and as an error notification to the module.  With the notification lost, the report alone must stop the import."""
    def _report_only(self, w, code):
        w['env'].module._h['error'] = []                                       # every AUIF error notification is lost before APG sees it
        s = w['env'].import_entity('zero_one', 'bz-master', 'supplier')
        self.assertEqual(s['status'], 'blocked', s)
        self.assertIn(code, {c for c, _ in s['reasons']})
        self.assertEqual(len(w['s'].query('supplier')), 0)
        self.assertIn(code, codes(status(w['s'], w['env'])))

    def test_translation_invalid_counted_only_in_the_report(self):
        w = _w()
        _wrap_translator(w, _invalid('TRANSLATION_INVALID'))
        self._report_only(w, 'TRANSLATION_INVALID')

    def test_ambiguous_counted_only_in_the_report(self):
        w = _w()
        _wrap_translator(w, _invalid('AMBIGUOUS'))
        self._report_only(w, 'AMBIGUOUS')

    def test_a_report_that_says_reading_was_not_allowed(self):
        w = _w()
        w['env'].fabric.sync = lambda ctx, iid, entity, **kw: {'pages': 0, 'delivered': 0, 'invalid': 0, 'ambiguous': 0, 'empty': False, 'failed': None, 'not_allowed': True}
        s = w['env'].import_entity('zero_one', 'bz-master', 'supplier')
        self.assertEqual(s['status'], 'blocked')
        self.assertIn('SYNC_NOT_ALLOWED', {c for c, _ in s['reasons']})

    def test_an_object_outside_any_import_whose_observation_never_comes(self):
        w = _w()
        w['env'].module._h['observation'] = []
        w['env'].fabric.sync(w['ctx'], 'bz-master', 'supplier', max_pages=5, page_size=50)
        self.assertEqual(len(w['s'].query('supplier')), 0)
        self.assertIn('UNSOLICITED_DELIVERY', codes(status(w['s'], w['env'], expected=[('bz-master', 'supplier')])))


class TestGateAndBinding(unittest.TestCase):
    def test_a_module_handler_failure_recorded_by_auif_stops_the_assessment(self):
        w = _w()
        w['env'].import_entity('zero_one', 'bz-master', 'supplier')
        self.assertEqual(status(w['s'], w['env'])['status'], 'can_assess')
        w['env'].module.handler_errors.append({'kind': 'entity', 'error': 'RuntimeError'})
        self.assertEqual(codes(status(w['s'], w['env'])), ['ADAPTER_ERROR'])

    def test_an_auif_tenant_cannot_be_bound_to_another_tenants_store(self):
        clock, prov, store, audit, who = world()
        env = client.AuifEnvironment(HERE_ROOT)
        with self.assertRaises(ValueError):
            env.bind('zero_two', who('t', 'zero_one', 'ann'), clock)


if __name__ == '__main__':
    unittest.main()
