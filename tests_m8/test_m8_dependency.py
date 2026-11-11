"""The AUIF dependency is exactly AUIF rev14 as delivered and audited (APG-M8.1; APG-M8 to M8-R2 used rev13): ZIP hash, sidecar, manifest, whole-tree and core-tree
hashes; it is carried as the ZIP only and imported from a verified extraction.  A changed byte anywhere is refused."""
import os, shutil, tempfile, unittest
from ._auif import DEP, HERE_ROOT, dependency

DELIVERED_ZIP_SHA256 = 'd534a6e6541b6d1a58e0389161d08698a1d7ac92ee9ad880a51fcee36497c649'      # AUIF rev14 as delivered (audited with its stated qualifications)


class TestFrozenDependency(unittest.TestCase):
    def test_the_hashes_are_the_authorised_baselines(self):
        self.assertEqual(dependency.ZIP_SHA256, DELIVERED_ZIP_SHA256)
        self.assertEqual(DEP['zip_sha256'], DELIVERED_ZIP_SHA256)
        self.assertEqual(DEP['tree_sha256'], '4918c2a6eb9480e5cfaf5089395c5352af0c7571b7070849f562128b18c2faf3')
        self.assertEqual(DEP['core_tree_sha256'], '923de5100f95debbbf63d5ab6e960cee2091ee57abce403792403ff049ac7839')
        self.assertEqual(DEP['files_checked'], 253)
        self.assertEqual(dependency.sha256_file(dependency.ZIP), DELIVERED_ZIP_SHA256)

    def test_auif_is_imported_from_the_verified_extraction_not_from_this_package(self):
        import auif, auif_ext
        for m in (auif, auif_ext):
            self.assertTrue(os.path.realpath(m.__file__).startswith(os.path.realpath(DEP['root']) + os.sep), m.__file__)
            self.assertFalse(os.path.realpath(m.__file__).startswith(os.path.realpath(HERE_ROOT) + os.sep))

    def test_the_package_carries_the_zip_and_no_copy_of_auif_source(self):
        found = []
        for d, ds, fs in os.walk(HERE_ROOT):
            ds[:] = [x for x in ds if x != '__pycache__']
            rel = os.path.relpath(d, HERE_ROOT)
            for x in ds:
                if x in ('auif', 'auif_ext', 'auif_onboard', 'auif_ref', 'port_contracts', 'synthetic'):
                    found.append(os.path.join(rel, x))
        self.assertEqual(found, [])
        self.assertEqual(sorted(os.listdir(os.path.join(HERE_ROOT, 'third_party'))), ['auif_rev14'])          # rev13 is not carried any more
        self.assertEqual(sorted(os.listdir(os.path.join(HERE_ROOT, 'third_party', 'auif_rev14'))),
                         ['AUIF_Independent_Build_v1.0_rev14.zip', 'AUIF_Independent_Build_v1.0_rev14.zip.sha256'])

    def test_a_changed_zip_is_refused(self):
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, os.path.basename(dependency.ZIP))                     # the same file name: only the hash can tell
            b = bytearray(open(dependency.ZIP, 'rb').read())
            b[len(b) // 2] ^= 1
            open(p, 'wb').write(bytes(b))
            with self.assertRaises(dependency.AuifDependencyError):
                dependency.check_zip(p)
        finally:
            shutil.rmtree(d)

    def test_a_changed_file_in_the_extraction_is_refused_by_the_manifest_and_a_core_change_by_the_core_hash(self):
        d = tempfile.mkdtemp()
        try:
            root = dependency.extract(d)
            self.assertEqual(dependency.verify_tree(root)['core_tree_sha256'], dependency.CORE_TREE_SHA256)
            p = os.path.join(root, 'auif', 'translation.py')
            open(p, 'a').write('\n# changed\n')
            with self.assertRaises(dependency.AuifDependencyError):
                dependency.verify_tree(root)
        finally:
            shutil.rmtree(d)

    def test_a_consistently_re_manifested_auif_is_refused(self):
        """A changed AUIF file (outside the core) with a manifest rewritten to match: AUIF's own check passes, the pinned tree hash does not."""
        import hashlib, json, subprocess, sys
        d = tempfile.mkdtemp()
        try:
            root = dependency.extract(d)
            rel = 'auif_ext/module_client/client.py'
            p = os.path.join(root, rel)
            open(p, 'a').write('\n# changed\n')
            mpath = os.path.join(root, 'FILE_MANIFEST.json')
            m = json.load(open(mpath))
            b = open(p, 'rb').read()
            for f in m['files']:
                if f['path'] == rel:
                    f.update(sha256=hashlib.sha256(b).hexdigest(), bytes=len(b))
            m['tree_sha256'] = hashlib.sha256('\n'.join('%s %s' % (f['path'], f['sha256']) for f in sorted(m['files'], key=lambda x: x['path'])).encode()).hexdigest()
            json.dump(m, open(mpath, 'w'), indent=1)
            r = subprocess.run([sys.executable, '-I', '-B', os.path.join(root, 'tools', 'verify_package.py'), root], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout[-300:])                     # AUIF's own check is satisfied
            with self.assertRaises(dependency.AuifDependencyError):
                dependency.verify_tree(root)
        finally:
            shutil.rmtree(d)

    def test_the_tree_in_use_is_still_rev14_after_the_tests_ran_so_far(self):
        self.assertEqual(dependency.reverify(DEP['root'])['tree_sha256'], dependency.TREE_SHA256)


if __name__ == '__main__':
    unittest.main()
