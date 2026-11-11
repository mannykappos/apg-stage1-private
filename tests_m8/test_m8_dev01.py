"""APG-M8.1: DEV-M8-01 has ended.  On AUIF rev14 (finding M8-F1 corrected: the attribute is read after the concept's full name) the packs use the contract form
'module.apg.<Type>.<attribute>'.  (APG-M8 to M8-R2, on AUIF rev13, wrote '<Type>.<attribute>' under DEV-M8-01; this file then pinned the rev13 defect.)
These tests show, on the unmodified rev14: the contract form produces valid module objects with the exact values; invalid input is still rejected; the old deviation form is
refused by rev14 itself when the pack is registered and by APG's own form check; and the path fails closed if a pack in another form is ever used."""
import copy, unittest
from ._auif import HERE_ROOT, PK, client, codes, single, status, records


def _translate(pack, entity, record, model_def=None):
    from auif.canonical import CanonicalModel
    from auif.clock import FakeClock
    from auif.tenancy import TenantAuthority
    from auif.translation import PackRegistry, Translator
    from auif.util import Ids
    cfg = client.load_config(HERE_ROOT)
    reg = PackRegistry()
    reg.register(pack)
    ref = PK.ref(pack)
    return Translator(CanonicalModel(model_def or cfg['model']), reg, Ids(), FakeClock()).translate_inbound(
        TenantAuthority().issue('zero_one', 'p'), ref, entity, record, source_system='bz-master', observation_id='obs-1', schema_fingerprint='0' * 64, source_id='SUP-001')


def _pack(deviation_form=False):
    """The stored bz-master pack (contract form), or the same pack rewritten in the ended DEV-M8-01 form '<Type>.<attribute>'."""
    from auif.translation import pack_hash
    p = copy.deepcopy(client.load_config(HERE_ROOT)['packs']['apg-m8-bz-master'])
    if deviation_form:
        for m in p['mappings']:
            if m['kind'] == 'FIELD':
                m['canonical_ref'] = m['canonical_ref'][len('module.apg.'):]
        p['artifact_hash'] = pack_hash(p)
    return p


GOOD = {'supplier_id': 'SUP-001', 'name': 'SYN Metro Steel Pty Ltd', 'abn_synthetic': '00 000 000 001'}


class TestFindingM8F1Corrected(unittest.TestCase):
    def test_rev14_refuses_the_old_deviation_form_when_the_pack_is_registered(self):
        from auif.errors import PackError
        from auif.translation import PackRegistry
        with self.assertRaises(PackError):
            PackRegistry().register(_pack(deviation_form=True))

    def test_rev14_reads_the_attribute_after_the_concepts_full_name(self):
        import auif.translation as T, inspect
        src = inspect.getsource(T.Translator.translate_inbound)
        self.assertIn('split_ref(m["canonical_ref"])', src)
        self.assertNotIn('attr = m["canonical_ref"].split(".", 1)[1]', src)


class TestContractForm(unittest.TestCase):
    def test_the_contract_form_gives_a_valid_module_object_with_the_exact_values(self):
        o = _translate(_pack(), 'supplier', dict(GOOD))
        self.assertEqual(o['validation_state'], 'VALID')
        self.assertEqual(o['canonical_type'], 'module.apg.Supplier')
        self.assertEqual(o['attributes'], {'source_record_id': 'SUP-001', 'supplier_name': 'SYN Metro Steel Pty Ltd', 'abn_text': '00 000 000 001'})
        self.assertEqual(o['canonical_id'], 'module.apg.supplier:bz-master:SUP-001')

    def test_invalid_input_is_still_rejected_in_the_contract_form(self):
        cases = {'a required column missing': {k: v for k, v in GOOD.items() if k != 'name'},
                 'a value that is not text': dict(GOOD, name=7),
                 'a column the pack does not map': dict(GOOD, tenant_hint='x'),
                 'a null required value': dict(GOOD, name=None)}
        for why, rec in cases.items():
            with self.subTest(why):
                o = _translate(_pack(), 'supplier', rec)
                self.assertEqual(o['validation_state'], 'TRANSLATION_INVALID', why)
                self.assertNotIn('attributes', o)

    def test_every_stored_pack_uses_exactly_the_contract_form(self):
        cfg = client.load_config(HERE_ROOT)
        concepts = {c['name'] for c in cfg['model']['concepts']}
        self.assertTrue(all(c.startswith('module.apg.') for c in concepts))
        n = 0
        for p in cfg['packs'].values():
            self.assertEqual(PK.form_problems(p), [])
            for m in p['mappings']:
                if m['kind'] == 'ENTITY':
                    self.assertIn(m['canonical_ref'], concepts)
                else:
                    n += 1
                    self.assertTrue(m['canonical_ref'].startswith('module.apg.'))
        self.assertGreater(n, 150)

    def test_this_code_generates_exactly_the_stored_packs(self):
        from apg_auif import definitions as DEF
        cfg = client.load_config(HERE_ROOT)
        byent = DEF.by_entity(cfg['definitions'])
        for pid, p in cfg['packs'].items():
            ents = [m['source_ref'] for m in p['mappings'] if m['kind'] == 'ENTITY']
            q = PK.build_pack(pid[len('apg-m8-'):], byent, ents, p['schema_expectations']['compatible_fingerprints'])
            self.assertEqual(q, p, pid)
        self.assertEqual(PK.field_ref('module.apg.Supplier', 'supplier_name'), 'module.apg.Supplier.supplier_name')

    def test_an_entity_mapping_without_the_full_module_name_is_refused(self):
        p = _pack()
        p['mappings'] = [m for m in p['mappings'] if m['kind'] == 'ENTITY']
        self.assertEqual(PK.form_problems(p), [])
        p['mappings'][0]['canonical_ref'] = 'Supplier'
        self.assertTrue(PK.form_problems(p))

    def test_the_form_check_refuses_every_other_form(self):
        ent = {'mapping_id': 'e', 'kind': 'ENTITY', 'canonical_ref': 'module.apg.Supplier'}
        for ref, ok in (('module.apg.Supplier.supplier_name', True), ('Supplier.supplier_name', False), ('module.apg.ApInvoice.supplier_name', False),
                        ('module.apg.Supplier.a.b', False), ('module.apg.Supplier.', False), ('supplier_name', False)):
            with self.subTest(ref):
                self.assertEqual(PK.check_field_ref({'mapping_id': 'f', 'canonical_ref': ref}, ent) == [], ok)


class TestFailClosed(unittest.TestCase):
    def test_a_pack_in_any_other_form_is_refused_before_it_is_used(self):
        cfg = client.load_config(HERE_ROOT)
        cfg['packs']['apg-m8-bz-master'] = _pack(deviation_form=True)
        from auif.translation import PackRegistry
        real_reg = PackRegistry.register
        def register(reg, p, *a, **k):                                    # skip only the altered pack, so the environment is built and APG's own check is reached
            if p['pack_id'] != 'apg-m8-bz-master':
                return real_reg(reg, p, *a, **k)
        PackRegistry.register = register
        try:
            env = client.AuifEnvironment(HERE_ROOT, cfg)                  # rev14's registry would refuse the pack at once; let it through to reach APG's own check
        finally:
            PackRegistry.register = real_reg
        from ._auif import world
        clock, prov, store, audit, who = world()
        env.bind('zero_one', who('t', 'zero_one', 'ann'), clock)
        with self.assertRaises(ValueError):
            env.add_file_integration('zero_one', 'bz-master')

    def test_even_if_apgs_check_were_bypassed_rev14_refuses_the_old_form(self):
        from auif.errors import PackError
        cfg = client.load_config(HERE_ROOT)
        cfg['packs']['apg-m8-bz-master'] = _pack(deviation_form=True)
        real = PK.form_problems
        PK.form_problems = lambda p: []
        try:
            with self.assertRaises(PackError):                          # AUIF rev14 itself refuses the pack: the environment cannot even be built
                single('bz-master', config=cfg)
        finally:
            PK.form_problems = real


if __name__ == '__main__':
    unittest.main()
