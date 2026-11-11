"""The M8 boundary: no other change to any earlier release, AUIF unchanged, synthetic only, no network, credential, Governor wiring, Engine port or outbound action."""
import ast, hashlib, os, unittest
from ._auif import DEP, HERE_ROOT, client, dependency, single

ADDED = ('apg_auif/', 'tests_m8/', 'auif_m8/', 'third_party/auif_rev13/', 'regression/m8/', 'logs/m8/', 'regression/m8r1/', 'logs/m8r1/')      # M8-R1: its regression baseline and logs
ADDED_FILES = {'tools/make_m8_config.py', 'tools/run_m8_tests.py', 'tools/run_m8_all.py', 'tools/m8_mutants.py', 'tools/sabotage_m8.py', 'tools/run_regression_m8.py',
               'tools/make_m8_registers.py', 'programme/CHANGE_RECORD_APG-M8.md', 'tools/make_m8r1_registers.py', 'programme/CHANGE_RECORD_APG-M8R1.md'}      # M8-R1 adds two
CHANGED = {'README.md', 'RUN_COMMANDS.txt', 'programme/FINDINGS_REGISTER.csv', 'programme/STATUS_REGISTER.csv', 'programme/INTERPRETATIONS_REGISTER.csv',
           'programme/CARRIED_FORWARD_REGISTER.csv'}                          # the Engine handoff register is NOT changed


def manifest():
    return {line[66:].rstrip('\n'): line[:64] for line in open(os.path.join(HERE_ROOT, 'regression', 'm8', 'R2_MANIFEST.sha256'), encoding='utf-8')}


class TestNoOtherChange(unittest.TestCase):
    def test_every_r2_file_is_byte_identical_except_the_declared_record_files(self):
        m = manifest()
        self.assertEqual(len(m), 1222)
        bad = [p for p, h in m.items() if p not in CHANGED and hashlib.sha256(open(os.path.join(HERE_ROOT, p), 'rb').read()).hexdigest() != h]
        self.assertEqual(bad, [])
        for p in CHANGED:
            self.assertIn(p, m)

    def test_no_existing_application_code_or_test_changed(self):
        m = manifest()
        self.assertFalse(any(p.startswith(('apg/', 'tests/', 'mie/', 'spec/')) for p in CHANGED))
        self.assertEqual(len([p for p in m if p.startswith(('apg/', 'tests/'))]), len([p for p in m if p.startswith(('apg/', 'tests/')) and p not in CHANGED]))

    def test_every_added_file_is_declared(self):
        m = manifest()
        extra = []
        for d, ds, fs in os.walk(HERE_ROOT):
            ds[:] = [x for x in ds if x != '__pycache__']
            for f in fs:
                rel = os.path.relpath(os.path.join(d, f), HERE_ROOT).replace(os.sep, '/')
                if rel not in m and not rel.startswith(ADDED) and rel not in ADDED_FILES:
                    extra.append(rel)
        self.assertEqual(extra, [])

    def test_the_auif_dependency_in_the_package_is_the_exact_rev13_zip(self):
        self.assertEqual(dependency.sha256_file(dependency.ZIP), '61748ddeba21e8c1d71b56bd0d3ad7a376ea051f4ae6fbe56c6464c0de76e070')
        self.assertEqual(dependency.reverify(DEP['root'])['core_tree_sha256'], dependency.CORE_TREE_SHA256)


class TestBoundary(unittest.TestCase):
    STD_OK = {'atexit', 'csv', 'io', 'json', 'math', 'os', 'copy', 'hashlib', 'shutil', 'subprocess', 'sys', 'tempfile', 'zipfile', 'collections', 're'}

    def test_the_adapter_imports_nothing_that_reaches_a_network_or_the_governor(self):
        for f in sorted(os.listdir(os.path.join(HERE_ROOT, 'apg_auif'))):
            if not f.endswith('.py'):
                continue
            with open(os.path.join(HERE_ROOT, 'apg_auif', f), encoding='utf-8') as fh:
                tree = ast.parse(fh.read())
            for n in ast.walk(tree):
                names = [a.name for a in n.names] if isinstance(n, ast.Import) else ([n.module] if isinstance(n, ast.ImportFrom) and n.level == 0 else [])
                for mod in names:
                    top = mod.split('.')[0]
                    with self.subTest(file=f, module=mod):
                        self.assertTrue(top in self.STD_OK or top in ('apg', 'auif', 'auif_ext', 'auif_ref'), mod)
                        self.assertNotIn('governor', mod)
                        self.assertNotIn(mod, ('auif_ext.connectors.rest', 'auif_ext.connectors.http_client', 'auif_ext.connectors.oauth2', 'auif_ext.connectors.webhook'))

    def test_no_credential_no_governed_operation_and_no_grant(self):
        w = single('bz-accounting')
        env, ctx = w['env'], w['env'].ctx['zero_one']
        c = env.fabric.integration(ctx, 'bz-accounting')
        self.assertEqual(c.governed_operations, [])
        self.assertEqual(c.runtime.desc['authentication']['handling'], 'NONE')
        self.assertEqual(env.fabric.secrets._s if hasattr(env.fabric.secrets, '_s') else {}, {})
        self.assertEqual(env.governor.request_decision(ctx, {})['status'], 'UNAVAILABLE')
        self.assertEqual(env.governor.report_condition(ctx, {}), {'acknowledged': False})

    def test_the_persistence_tenancy_and_secret_ports_are_auif_reference_implementations(self):
        w = single('bz-master')
        env = w['env']
        self.assertEqual(type(env.store.inner).__module__, 'auif_ref.persistence')
        self.assertEqual(type(env.auth).__module__, 'auif.tenancy')
        self.assertEqual(type(env.fabric.secrets).__module__, 'auif_ref.secrets')

    def test_every_source_is_synthetic_builder_zero(self):
        for iid, i in client.layout.integrations().items():
            self.assertTrue(iid.startswith('bz-'))
        cfg = client.load_config(HERE_ROOT)
        self.assertTrue(all(p['target_system_kind'] == 'synthetic-builder-zero-csv-export' for p in cfg['packs'].values()))


if __name__ == '__main__':
    unittest.main()
