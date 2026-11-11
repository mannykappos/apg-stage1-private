"""The AUIF dependency, exactly as audited.  APG-M8.1 carries the AUIF rev14 ZIP byte for byte (third_party/auif_rev14/) and NEVER a copy of its source tree (APG-M8 to
M8-R2 carried rev13 the same way; product owner, 2026-10-21: "Authorise M8.1 as written, on AUIF rev14 as audited with its stated qualifications").  Before AUIF is
imported, `ensure()`:
  1. checks the ZIP's SHA-256 against the pinned value (d534a6e6...) and against the sidecar file shipped with it;
  2. extracts it into a fresh private folder (never into this package);
  3. runs AUIF's own manifest check (tools/verify_package.py: all 253 files, sizes, hashes, no extra file, tree hash 4918c2a6...);
  4. recomputes AUIF's core tree hash with AUIF's own function (tools/static_checks.tree_hash: 923de510...);
  5. puts the extracted root at the END of sys.path, so APG's own packages always win a name clash.
Any mismatch raises AuifDependencyError and nothing is imported.  `reverify(root)` repeats steps 3 and 4 after a test run (to show the run changed no AUIF file).
Standard library only."""
import atexit, hashlib, json, os, shutil, subprocess, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIP = os.path.join(HERE, 'third_party', 'auif_rev14', 'AUIF_Independent_Build_v1.0_rev14.zip')
SIDECAR = ZIP + '.sha256'
ZIP_SHA256 = 'd534a6e6541b6d1a58e0389161d08698a1d7ac92ee9ad880a51fcee36497c649'
TREE_SHA256 = '4918c2a6eb9480e5cfaf5089395c5352af0c7571b7070849f562128b18c2faf3'     # FILE_MANIFEST.json of rev14
CORE_TREE_SHA256 = '923de5100f95debbbf63d5ab6e960cee2091ee57abce403792403ff049ac7839'
TOP = 'AUIF_Independent_Build_v1.0'
FILES = 253
ENV = 'APG_AUIF_ROOT'                 # set by tools/run_m8_tests.py to a root it has just verified; still re-checked here


class AuifDependencyError(Exception):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def check_zip(path=ZIP):
    """-> the ZIP's SHA-256.  Raises unless it equals the pinned value and the shipped sidecar names the same value and file."""
    if not os.path.isfile(path):
        raise AuifDependencyError('the AUIF rev14 ZIP is missing: %s' % path)
    got = sha256_file(path)
    if got != ZIP_SHA256:
        raise AuifDependencyError('AUIF ZIP hash %s is not the pinned rev14 hash %s' % (got, ZIP_SHA256))
    side = open(SIDECAR, encoding='ascii').read().split() if os.path.isfile(SIDECAR) else []
    if side[:2] != [ZIP_SHA256, os.path.basename(path)]:
        raise AuifDependencyError('the sidecar %s does not name the frozen hash and file' % SIDECAR)
    return got


def verify_tree(root):
    """AUIF's own manifest check plus its own core tree hash, run in a separate interpreter (-I -B: nothing from here leaks in, no bytecode is written).  -> dict."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    r = subprocess.run([sys.executable, '-I', '-B', os.path.join(root, 'tools', 'verify_package.py'), root], capture_output=True, text=True, env=env, timeout=600)
    try:
        man = json.loads(r.stdout)
    except ValueError:
        raise AuifDependencyError('verify_package gave no result: %s' % (r.stdout + r.stderr)[-300:])
    if r.returncode != 0 or not man.get('ok') or man.get('tree_sha256') != TREE_SHA256 or man.get('files_checked') != FILES:
        raise AuifDependencyError('AUIF manifest check failed: %s' % json.dumps(man)[:400])
    code = 'import sys; sys.path.insert(0, sys.argv[1]); import os; os.chdir(sys.argv[1]); from tools import static_checks as S; print(S.tree_hash())'
    r2 = subprocess.run([sys.executable, '-I', '-B', '-c', code, root], capture_output=True, text=True, env=env, timeout=600)
    core = r2.stdout.strip().splitlines()[-1] if r2.stdout.strip() else ''
    if r2.returncode != 0 or core != CORE_TREE_SHA256:
        raise AuifDependencyError('AUIF core tree hash %r is not %s %s' % (core, CORE_TREE_SHA256, r2.stderr[-200:]))
    return {'files_checked': man['files_checked'], 'tree_sha256': man['tree_sha256'], 'core_tree_sha256': core}


def extract(dest=None):
    """Extract the verified ZIP into a fresh folder (refusing any member that would land outside it).  -> the AUIF root."""
    check_zip()
    dest = dest or tempfile.mkdtemp(prefix='apg_m8_auif_')
    with zipfile.ZipFile(ZIP) as z:
        base = os.path.realpath(dest)
        for n in z.namelist():
            t = os.path.realpath(os.path.join(dest, n))
            if not (t == base or t.startswith(base + os.sep)):
                raise AuifDependencyError('ZIP member outside the folder: %r' % n)
        z.extractall(dest)
    root = os.path.join(dest, TOP)
    if not os.path.isdir(root):
        raise AuifDependencyError('the ZIP does not contain %s/' % TOP)
    return root


_READY = {}


def ensure(root=None):
    """Verify (and if needed extract) AUIF, then make it importable.  -> {'root', 'zip_sha256', 'tree_sha256', 'core_tree_sha256', 'files_checked'}."""
    if 'root' in _READY:
        return dict(_READY)
    zsha = check_zip()
    root = root or os.environ.get(ENV)
    if not root:
        root = extract()
        atexit.register(shutil.rmtree, os.path.dirname(root), True)      # this process made the extraction, so it removes it on exit
    info = verify_tree(root)
    if root not in sys.path:
        sys.path.append(root)
    _READY.update(info, root=root, zip_sha256=zsha)
    return dict(_READY)


def reverify(root):
    """After a run: the extracted AUIF tree is still exactly rev14."""
    return verify_tree(root)
