"""The APG module against AUIF's own module-port conformance cases (port_contracts.other_contracts.ModulePortContract, unchanged), plus what M8 adds: it is built on
AUIF's BaseModule, receives every kind of delivery, and has no outbound path."""
import ast, os, unittest
from ._auif import HERE_ROOT, single
from port_contracts.other_contracts import ModulePortContract


def _module():
    return single('bz-master')['env'].module


class TestAuifModulePortConformance(ModulePortContract, unittest.TestCase):
    """AUIF's own cases: identity and descriptors; valid objects, states and errors are accepted without raising (here for a tenant APG is not bound to, which the
    module refuses and never stores)."""
    def make_module(self):
        return _module()

    def test_the_conformance_object_for_an_unbound_tenant_was_refused_not_stored(self):
        self.m.ingest_canonical_entity(self.ctx, dict(self.OBJ))
        self.assertTrue(any(r[0] == 'UNBOUND_TENANT' for r in self.m.unbound_refusals))


class TestModuleShape(unittest.TestCase):
    def test_it_is_auif_basemodule_and_a_moduleport(self):
        from auif.ports import ModulePort
        from auif_ext.module_client.client import BaseModule
        m = _module()
        self.assertIsInstance(m, BaseModule)
        self.assertIsInstance(m, ModulePort)
        self.assertEqual(m.module_id, 'apg')
        self.assertEqual({k for k, v in m._h.items() if v}, {'entity', 'observation', 'event', 'state', 'error'})

    def test_it_declares_its_requirements_from_the_definitions_and_no_outbound_capability(self):
        w = single('bz-accounting')
        m = w['env'].module
        self.assertEqual(sorted(r['concept'] for r in m.semantic_requirements()), ['module.apg.ApInvoice', 'module.apg.CreditNote', 'module.apg.Payment'])
        self.assertEqual(m.module_capabilities()['outbound_actions'], [])
        self.assertFalse(any(hasattr(m, n) for n in ('request_action', 'build_action', 'dispatch')))
        self.assertFalse(any(hasattr(w['env'], n) for n in ('request_action', 'build_action')))

    def test_no_adapter_code_requests_an_action_or_touches_the_governor_adapter(self):
        bad = []
        for f in sorted(os.listdir(os.path.join(HERE_ROOT, 'apg_auif'))):
            if not f.endswith('.py'):
                continue
            with open(os.path.join(HERE_ROOT, 'apg_auif', f), encoding='utf-8') as fh:
                tree = ast.parse(fh.read())
            for n in ast.walk(tree):
                if isinstance(n, ast.Attribute) and n.attr in ('request_action', 'build_action', 'dispatch', 'apply_pack_upgrade', 'propose_pack_upgrade'):
                    bad.append((f, n.attr))
                if isinstance(n, (ast.Import, ast.ImportFrom)):
                    mod = n.module if isinstance(n, ast.ImportFrom) else n.names[0].name
                    if mod and ('governor_adapter' in mod or mod.split('.')[0] in ('socket', 'ssl', 'http', 'urllib', 'ftplib', 'smtplib', 'asyncio')
                                or mod in ('auif_ext.connectors.rest', 'auif_ext.connectors.http_client', 'auif_ext.connectors.oauth2', 'auif_ext.connectors.webhook')):
                        bad.append((f, mod))
        self.assertEqual(bad, [])

    def test_a_delivery_with_no_import_open_is_refused_and_recorded_as_an_alert(self):
        w = single('bz-master')
        ctx = w['env'].ctx['zero_one']
        rep = w['env'].fabric.sync(ctx, 'bz-master', 'supplier', max_pages=5, page_size=50)       # someone reads around the APG client
        self.assertEqual(rep['delivered'], 12)
        self.assertEqual([r.payload['code'] for r in w['s'].query('auif_alert')][:1], ['UNSOLICITED_DELIVERY'])
        self.assertEqual(len(w['s'].query('supplier')), 0)


if __name__ == '__main__':
    unittest.main()
