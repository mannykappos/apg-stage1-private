"""The M8 boundary: no other change to any earlier release, AUIF unchanged (rev14 from APG-M8.1; rev13 before), synthetic only, no network, credential, Governor wiring,
Engine port or outbound action.
APG-M11-S1 (stage 1, amendment 2 of the build authorisation, product owner 2026-10-31 13:18, option (iii) of the stop report): this successor copy is edited in place.
M10's file (SHA-256 074969a7cc93e8818e5d1589cc93492af8be7f98e4950710a0a2ad526f608ac2) runs unchanged against the immutable M10 archive as the historical-baseline run.
Here, and only in the two TestNoOtherChange checks that compare the tree with M8's declarations, the frozen stage 1 manifest (programme/APG-M11-S1_MANIFEST.csv) is
one more source of permitted differences: read from the tree at run time, validated in full first (load_s1_manifest; amendment 2 §2.1), and every file it declares must
have exactly the hash it records.  On the successor the two checks therefore mean: nothing changed beyond what M8 declared and what the frozen stage 1 manifest declares.
Every other test is unchanged.     BUILDER-EXECUTED: NOT INDEPENDENT."""
import ast, csv, hashlib, os, re, stat, unittest
from ._auif import DEP, HERE_ROOT, client, dependency, single

ADDED = ('apg_auif/', 'tests_m8/', 'auif_m8/', 'third_party/auif_rev13/', 'regression/m8/', 'logs/m8/', 'regression/m8r1/', 'logs/m8r1/', 'regression/m8r2/', 'logs/m8r2/',
         'third_party/auif_rev14/', 'regression/m81/', 'logs/m81/',      # M8-R1, M8-R2 and M8.1: their regression baselines and logs; M8.1 carries AUIF rev14
         'regression/m81r1/', 'logs/m81r1/',      # M8.1-R1 (records only)
         'apg_ui/', 'ui/', 'ui_tests/', 'tests_m10/', 'regression/m10/', 'logs/m10/')      # M10 (the prototype)
ADDED_FILES = {'tools/make_m8_config.py', 'tools/run_m8_tests.py', 'tools/run_m8_all.py', 'tools/m8_mutants.py', 'tools/sabotage_m8.py', 'tools/run_regression_m8.py',
               'tools/make_m8_registers.py', 'programme/CHANGE_RECORD_APG-M8.md', 'tools/make_m8r1_registers.py', 'programme/CHANGE_RECORD_APG-M8R1.md',
               'tools/make_m8r2_registers.py', 'tools/run_regression_m8r2.py', 'programme/CHANGE_RECORD_APG-M8R2.md',
               'tools/make_m81_registers.py', 'tools/run_regression_m81.py', 'programme/CHANGE_RECORD_APG-M8.1.md',
               'tools/make_m81r1_registers.py', 'tools/run_regression_m81r1.py', 'programme/CHANGE_RECORD_APG-M8.1-R1.md',
               'tools/build_m10_views.py', 'tools/sabotage_m10.py', 'tools/make_m10_registers.py', 'tools/run_regression_m10.py', 'programme/CHANGE_RECORD_APG-M10.md'}      # M10 five      # M8-R1 adds two; M8-R2 (records only) three; M8.1 three; M8.1-R1 (records only) three
CHANGED = {'README.md', 'RUN_COMMANDS.txt', 'programme/FINDINGS_REGISTER.csv', 'programme/STATUS_REGISTER.csv', 'programme/INTERPRETATIONS_REGISTER.csv',
           'programme/CARRIED_FORWARD_REGISTER.csv', 'programme/AUDIT_DISPOSITION_REGISTER.csv',   # M8-R2 appends the auditor's dispositions; the Engine handoff register is NOT changed
           'programme/PROGRAMME_MILESTONES.csv'}      # M8.1-R1 (records only) sets the M8 milestone row's status


def manifest():
    return {line[66:].rstrip('\n'): line[:64] for line in open(os.path.join(HERE_ROOT, 'regression', 'm8', 'R2_MANIFEST.sha256'), encoding='utf-8')}


# ---- APG-M11-S1 (amendment 2): the stage 1 manifest, its fixed schema and its validation (§2.1).  Literal constants: the schema cannot change without this file's
# pinned hash changing (tools/expected_counts.json).
S1_MANIFEST = 'programme/APG-M11-S1_MANIFEST.csv'          # the one exemption, this exact path only
S1_HEADER = ['section', 'path', 'status', 'm10_sha256', 's1_sha256', 'successor', 'detail']
S1_SECTIONS = ['identity', 'd1', 'supplementary', 'records', 'changed']
S1_IDENTITY = ['identity', '-', '-', 'bd5c592a198581808237e5a5e563aa15c3be977d3f3e0d68511499d755435192', '-', '-', 'stage=APG-M11-S1;base=APG-M10']
S1_D1_LINES = 89                                            # amendment 1
S1_SUPPLEMENTARY = ('tests_m8/test_m8_boundary.py', '074969a7cc93e8818e5d1589cc93492af8be7f98e4950710a0a2ad526f608ac2', 'amendment 2')
S1_RECORD_DETAIL = 'stage 1 record'
_HEX = re.compile(r'^[0-9a-f]{64}$')
_PATH = re.compile(r'^[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*$')
_FINDINGS = re.compile(r'^findings=[A-Z0-9-]+( [A-Z0-9-]+)*$')


class S1ManifestRejected(AssertionError):
    pass


def _reject(reason, detail=''):
    raise S1ManifestRejected('S1_MANIFEST_REJECTED %s %s' % (reason, detail))


def _safe_path(p, root):
    """Amendment 2 §2.1 'Unsafe paths' (and E2: no symbolic link anywhere below the root, checked component by component without following links)."""
    if not _PATH.match(p) or any(c in ('', '.', '..') for c in p.split('/')):
        _reject('UNSAFE_PATH', p)
    if '.git' in p.split('/'):
        _reject('UNSAFE_PATH', p)
    if p == S1_MANIFEST:
        _reject('MANIFEST_DECLARES_ITSELF', p)
    cur = root
    for c in p.split('/'):
        cur = os.path.join(cur, c)
        try:
            st = os.lstat(cur)
        except OSError:
            return False                                    # missing: judged by the caller
        if stat.S_ISLNK(st.st_mode):
            _reject('SYMBOLIC_LINK', p)
    return True


def _file_hash(root, p):
    full = os.path.join(root, p)
    if not _safe_path(p, root):
        _reject('DECLARED_FILE_MISSING', p)
    if not stat.S_ISREG(os.lstat(full).st_mode):
        _reject('DECLARED_NOT_A_REGULAR_FILE', p)
    with open(full, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load_s1_manifest(root, r2):
    """Parse and validate the whole stage 1 manifest before any declaration is used (amendment 2 §2.1, with E1 and E2).  Any failure raises S1ManifestRejected
    naming its reason; nothing in the manifest is then used.  Returns {'modified': {path: hash}, 'new': {path: hash}} from the 'changed' section."""
    mp = os.path.join(root, S1_MANIFEST)
    for part in (os.path.join(root, 'programme'), mp):
        try:
            if stat.S_ISLNK(os.lstat(part).st_mode):
                _reject('WRONG_IDENTITY', 'symbolic link %s' % os.path.relpath(part, root))
        except OSError:
            _reject('MANIFEST_MISSING', S1_MANIFEST)
    try:
        with open(mp, encoding='utf-8', newline='') as fh:
            rows = list(csv.reader(fh))
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        _reject('MALFORMED', type(e).__name__)
    if not rows or rows[0] != S1_HEADER:
        _reject('WRONG_IDENTITY', 'header')
    body = rows[1:]
    if any(len(r) != len(S1_HEADER) for r in body):
        _reject('WRONG_STRUCTURE', 'field count')
    order = []
    for r in body:
        if r[0] not in S1_SECTIONS:
            _reject('WRONG_STRUCTURE', 'unknown section %s' % r[0])
        if not order or order[-1] != r[0]:
            order.append(r[0])
    if order != S1_SECTIONS:
        _reject('WRONG_STRUCTURE', 'sections %s' % '/'.join(order))
    sec = {n: [r for r in body if r[0] == n] for n in S1_SECTIONS}
    if len(sec['identity']) != 1 or sec['identity'][0] != S1_IDENTITY:
        _reject('WRONG_IDENTITY', 'identity line')
    if len(sec['d1']) != S1_D1_LINES:
        _reject('WRONG_STRUCTURE', 'd1 lines %d' % len(sec['d1']))
    if len(sec['supplementary']) != 1:
        _reject('WRONG_STRUCTURE', 'supplementary lines %d' % len(sec['supplementary']))
    if not sec['records'] or not sec['changed']:
        _reject('WRONG_STRUCTURE', 'empty section')
    for name in ('d1', 'supplementary', 'records', 'changed'):
        paths = [r[1] for r in sec[name]]
        if len(set(paths)) != len(paths):
            _reject('DUPLICATE_PATH', name)
        for p in paths:
            _safe_path(p, root)
    succ = [r[5] for r in sec['d1'] if r[5] != '-']
    if len(set(succ)) != len(succ) or set(succ) & {r[1] for r in sec['d1']}:
        _reject('DUPLICATE_PATH', 'd1 successor')
    for p in succ:
        _safe_path(p, root)
    # field values per section (malformed or ambiguous status/hash combinations)
    for r in sec['d1']:
        _, p, st, m10, s1, sc, det = r
        ok = _HEX.match(s1) and _FINDINGS.match(det) and (sc == '-' or _PATH.match(sc)) and (
            (st == 'modified' and _HEX.match(m10) and m10 != s1) or (st == 'new' and m10 == '-') or (st == 'unchanged' and m10 == s1 and _HEX.match(m10)))
        if not ok:
            _reject('MALFORMED_STATUS_HASH', 'd1 %s' % p)
    sp = sec['supplementary'][0]
    if sp[1] != S1_SUPPLEMENTARY[0] or sp[2] != 'modified' or sp[3] != S1_SUPPLEMENTARY[1] or not _HEX.match(sp[4]) or sp[4] == sp[3] or sp[5] != '-' \
            or sp[6] != S1_SUPPLEMENTARY[2]:
        _reject('MALFORMED_STATUS_HASH', 'supplementary')
    for r in sec['records']:
        if r[2] != 'new' or r[3] != '-' or not _HEX.match(r[4]) or r[5] != '-' or r[6] != S1_RECORD_DETAIL:
            _reject('MALFORMED_STATUS_HASH', 'records %s' % r[1])
    changed = {}
    for r in sec['changed']:
        _, p, st, m10, s1, sc, det = r
        if sc != '-' or det != '-' or not _HEX.match(s1) or not ((st == 'modified' and _HEX.match(m10) and m10 != s1) or (st == 'new' and m10 == '-')):
            _reject('MALFORMED_STATUS_HASH', 'changed %s' % p)
        if st == 'new' and p in r2:
            _reject('MALFORMED_STATUS_HASH', 'new but in R2 %s' % p)
        if st == 'modified' and p in r2 and p not in CHANGED and m10 != r2[p]:
            _reject('MALFORMED_STATUS_HASH', 'M10 hash differs from R2 %s' % p)
        changed[p] = (st, m10, s1)
    # cross-section accounting: each changed path is accounted for exactly once; each declared change appears in changed with the same status and hashes
    owner = {}
    def own(p, who):
        if p in owner:
            _reject('UNACCOUNTED_OR_CONFLICTING', 'accounted twice %s' % p)
        owner[p] = who
    for r in sec['d1']:
        if r[2] in ('modified', 'new'):
            own(r[1], 'd1')
            if changed.get(r[1]) != (r[2], r[3], r[4]):
                _reject('UNACCOUNTED_OR_CONFLICTING', 'd1 %s' % r[1])
        elif r[1] in changed:
            _reject('UNACCOUNTED_OR_CONFLICTING', 'd1 unchanged but changed %s' % r[1])
        if r[5] != '-':
            own(r[5], 'd1-successor')
            if changed.get(r[5], ('',))[0] != 'new':
                _reject('UNACCOUNTED_OR_CONFLICTING', 'successor %s' % r[5])
    own(sp[1], 'supplementary')
    if changed.get(sp[1]) != ('modified', sp[3], sp[4]):
        _reject('UNACCOUNTED_OR_CONFLICTING', 'supplementary')
    for r in sec['records']:
        own(r[1], 'records')
        if changed.get(r[1]) != ('new', '-', r[4]):
            _reject('UNACCOUNTED_OR_CONFLICTING', 'records %s' % r[1])
    for p in changed:
        if p not in owner:
            _reject('UNACCOUNTED_OR_CONFLICTING', 'unaccounted %s' % p)
    # every declaration must hold: the file exists, is regular, and has exactly the recorded hash; a d1 'unchanged' file has exactly its M10 hash
    for p, (st, m10, s1) in changed.items():
        if _file_hash(root, p) != s1:
            _reject('DECLARATION_DOES_NOT_HOLD', p)
    for r in sec['d1']:
        if r[2] == 'unchanged' and _file_hash(root, r[1]) != r[4]:
            _reject('DECLARATION_DOES_NOT_HOLD', r[1])
    return {'modified': {p: v[2] for p, v in changed.items() if v[0] == 'modified'}, 'new': {p: v[2] for p, v in changed.items() if v[0] == 'new'}}


class TestNoOtherChange(unittest.TestCase):
    def test_every_r2_file_is_byte_identical_except_the_declared_record_files(self):
        m = manifest()
        self.assertEqual(len(m), 1222)
        s1 = load_s1_manifest(HERE_ROOT, m)                 # APG-M11-S1, amendment 2: validated in full before use
        bad = [p for p, h in m.items() if p not in CHANGED and p not in s1['modified']
               and hashlib.sha256(open(os.path.join(HERE_ROOT, p), 'rb').read()).hexdigest() != h]
        self.assertEqual(bad, [])
        for p in CHANGED:
            self.assertIn(p, m)

    def test_no_existing_application_code_or_test_changed(self):
        m = manifest()
        self.assertFalse(any(p.startswith(('apg/', 'tests/', 'mie/', 'spec/')) for p in CHANGED))
        self.assertEqual(len([p for p in m if p.startswith(('apg/', 'tests/'))]), len([p for p in m if p.startswith(('apg/', 'tests/')) and p not in CHANGED]))

    def test_every_added_file_is_declared(self):
        m = manifest()
        s1 = load_s1_manifest(HERE_ROOT, m)                 # APG-M11-S1, amendment 2: validated in full before use
        extra = []
        for d, ds, fs in os.walk(HERE_ROOT):
            ds[:] = [x for x in ds if x != '__pycache__']
            for f in fs:
                rel = os.path.relpath(os.path.join(d, f), HERE_ROOT).replace(os.sep, '/')
                if rel not in m and not rel.startswith(ADDED) and rel not in ADDED_FILES and rel not in s1['new'] and rel != S1_MANIFEST:
                    extra.append(rel)
        self.assertEqual(extra, [])

    def test_the_auif_dependency_in_the_package_is_the_exact_rev14_zip(self):
        self.assertEqual(dependency.sha256_file(dependency.ZIP), 'd534a6e6541b6d1a58e0389161d08698a1d7ac92ee9ad880a51fcee36497c649')
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
