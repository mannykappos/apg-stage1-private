"""The AUIF path reads the same files, under the same source identities, as the M3 path; the stored configuration (definitions, model, packs) is exactly what the
generator makes; and the packs are configuration only: read-only, identity transforms, CANDIDATE."""
import json, os, subprocess, sys, unittest
from ._auif import HERE_ROOT, D, DF, client, layout


class TestLayout(unittest.TestCase):
    def test_the_layout_is_the_m3_m4_m5_file_lists_in_the_same_order(self):
        from apg.det import intake as DI
        want = []
        for t, data, src, name, rev in D.files_for(HERE_ROOT, 'zero_one'):
            want.append(('m3', t['template_id'], name, src, rev))
        want += [('fin', tid, os.path.basename(rel), src, None) for tid, rel, src in DF.FIN_FILES]
        want += [('det', tid, os.path.basename(rel), src, None) for tid, rel, src in DI.DET_FILES]
        got = [(e[0], e[1], e[3], e[4], e[5]) for e in layout.ENTITIES]
        self.assertEqual(got, want)
        folders = {(tid, os.path.dirname(rel)) for tid, rel, src in DF.FIN_FILES + DI.DET_FILES}
        self.assertTrue(folders <= {(e[1], e[2]) for e in layout.ENTITIES})

    def test_every_integration_is_one_source_in_one_folder(self):
        for iid, info in layout.integrations().items():
            for tid, fname, fam, rev in info['files']:
                e = layout.by_template()[tid]
                self.assertEqual((e['source'], e['folder']), (info['source'], info['folder']))


class TestStoredConfiguration(unittest.TestCase):
    def test_the_stored_configuration_is_exactly_what_the_generator_writes(self):
        r = subprocess.run([sys.executable, '-I', '-B', os.path.join(HERE_ROOT, 'tools', 'make_m8_config.py'), '--check'], capture_output=True, text=True,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('differing 0, unexpected 0', r.stdout)

    def test_the_packs_are_configuration_only(self):
        cfg = client.load_config(HERE_ROOT)
        self.assertEqual(len(cfg['packs']), len(layout.integrations()))
        for p in cfg['packs'].values():
            with self.subTest(p['pack_id']):
                self.assertEqual((p['pack_state'], p['contains_governance_logic'], p['contains_secrets'], p['immutable']), ('CANDIDATE', False, False, True))
                self.assertEqual(p['unmapped_field_policy'], {'default_outcome': 'REJECTED', 'ignored_by_rule': [], 'optional_and_unused': []})
                for m in p['mappings']:
                    self.assertEqual(m['outbound']['supported'], False)
                    self.assertEqual(m['inbound']['transform'], {'kind': 'IDENTITY', 'parameters': {}, 'deterministic': True})
                    self.assertEqual((m['mapping_state'], m['proposed_by']), ('VALIDATED', 'DETERMINISTIC_TOOL'))
                    self.assertFalse(str(m['validation_ref']['evidence_id']).startswith('val-ai-'))
                self.assertEqual(len(p['schema_expectations']['compatible_fingerprints']), 1)

    def test_nothing_in_the_configuration_is_locked_or_approved(self):
        for d, _, fs in os.walk(os.path.join(HERE_ROOT, 'auif_m8')):
            for f in fs:
                text = open(os.path.join(d, f), encoding='utf-8').read()
                self.assertNotIn('"LOCKED"', text, f)
                self.assertNotIn('"TRUSTED"', text, f)


if __name__ == '__main__':
    unittest.main()
