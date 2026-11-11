"""evkit: the shared evidence helper for the APG-M11-S1 evidence tools (stage 1, Workstream T).

Its contract is R13 Part A, R1_REQUIREMENTS.md §2.  It is built in small steps, each with its own adversarial tests in tests_tools/:
  step 1  §2.8 the trusted execution environment, and §2.5 import identity                 (this section)
  step 2  §2.7 the RESULT v=2 schema, reconciliation, the derived status and exit, and the checker
  step 3  §2.2 pins, §2.1 preflight, §2.3 controls, and §2.6 timeout classification
Standard library only.  It changes no M10 file.  BUILDER-EXECUTED: NOT INDEPENDENT.
"""
import hashlib
import os
import re
import shutil
import sys

# ---------------------------------------------------------------------------------------------------------------------------------------
# Step 1: §2.8 the trusted execution environment, and §2.5 import identity
# ---------------------------------------------------------------------------------------------------------------------------------------

# §2.5 (R4): one list, used by every check.  There is no second list.
TRUSTED_PACKAGES = ('apg', 'apg_auif', 'apg_ui', 'mie', 'auif_m8', 'tests', 'tests_m8', 'tests_m10', 'tools')

# §2.8: the child environment is built from this allowlist, never from os.environ.
ENV_ALLOWLIST = ('PATH', 'LANG', 'LC_ALL', 'TZ', 'TMPDIR', 'PYTHONDONTWRITEBYTECODE')
FIXED_PATH = '/usr/local/bin:/usr/bin:/bin'
# DP-1.3 (a): the one listed exception.  Its value is only ever the AUIF copy the runner itself has just extracted and verified.
ENV_EXCEPTIONS = ('APG_AUIF_ROOT',)

TOKEN = re.compile(r'^[A-Za-z0-9_.:-]+$')

ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# tools/ has no __init__.py, so 'tools' is a namespace package whose __path__ Python recomputes whenever sys.path changes.  A later
# sys.path entry holding its own tools/ (for example the AUIF extraction, which apg_auif.dependency appends) would silently join it.  So
# the namespace path is fixed here to this tree's tools/ only, the first time evkit is imported as tools.evkit (§2.5).
_tools_pkg = sys.modules.get('tools')
if _tools_pkg is not None and getattr(_tools_pkg, '__file__', None) is None and __name__ == 'tools.evkit':
    _tools_pkg.__path__ = [os.path.join(ROOT, 'tools')]

# §2.5 'loaded before the runner set its path': every stage 1 runner sets sys.path[0] to its own root and then imports tools.evkit
# before anything else, so the trusted modules already loaded at this point were loaded by the interpreter's start-up, not by the
# runner.  A runner whose trusted harness must be imported before the start sequence (the kind=cases tools: the harness defines the
# cases) passes this snapshot as its preloaded set, so its own harness imports are not reported but a start-up preload still is.
PRELOADED_AT_EVKIT_IMPORT = tuple(k for k in sys.modules if k.split('.')[0] in TRUSTED_PACKAGES and k not in ('tools', 'tools.evkit'))


class RunError(Exception):
    """A run-level error (§2.7): printed as one 'RUN_ERROR <code> <detail>' line, never attributed to an item."""

    def __init__(self, code, detail=''):
        if not TOKEN.match(code):
            raise ValueError('a RUN_ERROR code must match [A-Za-z0-9_.:-]+: %r' % (code,))
        self.code = code
        self.detail = one_line(detail)
        super().__init__('%s %s' % (code, self.detail))

    def line(self):
        return ('RUN_ERROR %s %s' % (self.code, self.detail)).rstrip()


def one_line(text):
    """Make a detail safe for one output line: no newlines or control characters."""
    return re.sub(r'[\x00-\x1f\x7f]+', ' ', str(text)).strip()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sha256_lines(items):
    """The SHA-256 of the sorted items joined by newlines (§2.7: ids_sha256, inventory hashes)."""
    return hashlib.sha256('\n'.join(sorted(items)).encode('utf-8')).hexdigest()


def clean_env(tmpdir, auif_root=None, path_value=FIXED_PATH):
    """§2.8: the complete child environment, from the allowlist only.  Nothing is inherited, so APG_ROOT, PYTHONPATH, PYTHONHOME,
    PYTHONSTARTUP, PYTHONUSERBASE and every other variable never reach a child.  auif_root, if given, must be the AUIF copy the caller
    has itself extracted and verified (DP-1.3 (a)); the child re-checks it (check_auif_root)."""
    if not tmpdir or not os.path.isabs(tmpdir) or not os.path.isdir(tmpdir):
        raise RunError('ENV_TMPDIR_INVALID', tmpdir)
    env = {'PATH': path_value, 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'TMPDIR': tmpdir, 'PYTHONDONTWRITEBYTECODE': '1'}
    if auif_root is not None:
        if not os.path.isabs(auif_root) or not os.path.isdir(auif_root):
            raise RunError('ENV_AUIF_ROOT_INVALID', auif_root)
        env['APG_AUIF_ROOT'] = os.path.realpath(auif_root)
    return env


def child_cmd(script, args=(), interpreter=None, site=False):
    """§2.8: every Python child starts with -I (isolated) and, unless the run instruction excepts the tool, -S (no site)."""
    cmd = [interpreter or sys.executable, '-I']
    if not site:
        cmd.append('-S')
    return cmd + [script] + [str(a) for a in args]


def child_module_cmd(module, args=(), interpreter=None, site=False):
    """As child_cmd, for '-m <module>' children (for example -m unittest): they too start with -I and -S (§2.8 R4)."""
    cmd = [interpreter or sys.executable, '-I']
    if not site:
        cmd.append('-S')
    return cmd + ['-m', module] + [str(a) for a in args]


def check_auif_root(value, expected_digest_fn=None):
    """DP-1.3 (a), the child side: APG_AUIF_ROOT is accepted only if it is an absolute, existing directory, is not inside the APG
    extraction root, and (when the caller supplies a verifier) passes that verifier.  Any other value is refused."""
    if value is None:
        return None
    real = os.path.realpath(value)
    if not os.path.isabs(value) or not os.path.isdir(real):
        raise RunError('ENV_AUIF_ROOT_INVALID', value)
    if real == ROOT or real.startswith(ROOT + os.sep):
        raise RunError('ENV_AUIF_ROOT_INSIDE_EXTRACTION', value)
    if expected_digest_fn is not None and not expected_digest_fn(real):
        raise RunError('ENV_AUIF_ROOT_UNVERIFIED', value)
    return real


SCRUBBED_VARIABLES = ('APG_ROOT', 'PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP', 'PYTHONUSERBASE', 'PYTHONSAFEPATH', 'PYTHONINSPECT')


def scrub_inherited():
    """§2.5 / P1-F6, P7-B2: APG_ROOT is removed unconditionally from this process's environment, and so are the Python variables -I
    already ignores (so that nothing this process starts can inherit them).  Returns the 'ENV ...' lines to print, one per variable
    that was present:  'ENV APG_ROOT was set; removed' and 'ENV DROPPED <name>'."""
    lines = []
    for var in SCRUBBED_VARIABLES:
        if var in os.environ:
            os.environ.pop(var, None)
            lines.append('ENV APG_ROOT was set; removed' if var == 'APG_ROOT' else 'ENV DROPPED %s' % var)
    return lines


def _inside(path, base):
    path = os.path.realpath(path)
    base = os.path.realpath(base)
    return path == base or path.startswith(base + os.sep)


def prefix_dirs():
    """§2.8: the recorded interpreter's sys.prefix and sys.base_prefix (where every sys.path entry other than the root must lie)."""
    return sorted({os.path.realpath(sys.prefix), os.path.realpath(sys.base_prefix)})


def stdlib_dirs():
    """§2.5 (R4, by file): the interpreter's own standard-library directories, where a loaded module that is not in the extraction
    must lie.  Narrower than prefix_dirs: site-packages and dist-packages are not standard library."""
    import sysconfig
    out = set()
    for key in ('stdlib', 'platstdlib'):
        p = sysconfig.get_paths().get(key)
        if p:
            out.add(os.path.realpath(p))
    for entry in sys.path:
        if entry.endswith('.zip') and any(_inside(entry, b) for b in prefix_dirs()):
            out.add(os.path.realpath(entry))
    return sorted(out)


def env_check(root=ROOT, allow_site=False, interpreter_sha256=None, disk_floor_bytes=10 * 1024 ** 3, path0_required=True):
    """§2.8 start checks.  Returns a list of RunError; an empty list means every check passed."""
    errs = []
    root = os.path.realpath(root)
    if sys.flags.isolated != 1:
        errs.append(RunError('ENV_NOT_ISOLATED', 'sys.flags.isolated=%d' % sys.flags.isolated))
    if not allow_site and sys.flags.no_site != 1:
        errs.append(RunError('ENV_SITE_LOADED', 'sys.flags.no_site=%d' % sys.flags.no_site))
    for name in ('sitecustomize', 'usercustomize'):
        if name in sys.modules:
            errs.append(RunError('ENV_CUSTOMIZE_LOADED', name))
    if path0_required and (not sys.path or os.path.realpath(sys.path[0] or '.') != root):
        errs.append(RunError('ENV_PATH0', 'sys.path[0]=%s expected %s' % (sys.path[0] if sys.path else '', root)))
    allowed = [root] + prefix_dirs()
    for entry in sys.path:
        if not entry:
            errs.append(RunError('ENV_SYS_PATH', 'empty entry (the working directory)'))
            continue
        if not any(_inside(entry, a) for a in allowed):
            errs.append(RunError('ENV_SYS_PATH', entry))
    if os.path.realpath(os.getcwd()) != root:
        errs.append(RunError('ENV_CWD', os.getcwd()))
    for var in SCRUBBED_VARIABLES:
        if var in os.environ:  # scrub_inherited() runs first; a variable still present means it was not called
            errs.append(RunError('ENV_NOT_SCRUBBED', var))
    if interpreter_sha256 is not None:
        got = sha256_file(os.path.realpath(sys.executable))
        if got != interpreter_sha256:
            errs.append(RunError('ENV_INTERPRETER', 'sha256=%s' % got))
    free = shutil.disk_usage(root).free
    if free < disk_floor_bytes:
        errs.append(RunError('ENV_DISK_BELOW_FLOOR', 'free=%d floor=%d' % (free, disk_floor_bytes)))
    return errs


def env_record(root=ROOT):
    """§2.8: what is recorded with every run (printed by the runner as ENV lines)."""
    return {
        'interpreter': os.path.realpath(sys.executable),
        'version': sys.version.split()[0],
        'interpreter_sha256': sha256_file(os.path.realpath(sys.executable)),
        'flags_isolated': sys.flags.isolated,
        'flags_no_site': sys.flags.no_site,
        'sys_path': list(sys.path),
        'cwd': os.getcwd(),
        'free_disk_bytes': shutil.disk_usage(root).free,
    }


def set_path0(root=ROOT):
    """§2.8: the runner sets sys.path[0] explicitly to the extraction root."""
    root = os.path.realpath(root)
    while root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)


def _module_file(mod):
    f = getattr(mod, '__file__', None)
    if f:
        return f
    spec = getattr(mod, '__spec__', None)
    if spec is not None and spec.origin not in (None, 'built-in', 'frozen', 'namespace'):
        return spec.origin
    return None


def _tool_stems(root):
    tools = os.path.join(root, 'tools')
    try:
        return {f[:-3] for f in os.listdir(tools) if f.endswith('.py')}
    except OSError:
        return set()


def import_identity(root=ROOT, preloaded=(), candidate_paths=()):
    """§2.5: every loaded module of a trusted package (and every submodule of one) must resolve inside the extraction, must not have
    been loaded before the runner set its path (preloaded: the names loaded before that point), and must have a resolvable file
    (namespace packages: every __path__ entry inside the extraction).  By file (R4): every loaded module with a file must resolve inside
    the extraction or inside the interpreter's own standard-library directories; modules under tools/ are recorded by file path.
    candidate_paths: directories a candidate was legitimately loaded from (load_candidate); a non-trusted module there is allowed.
    Returns (errors, records) where records is a sorted list of (module name, resolved file) for the IMPORT lines."""
    root = os.path.realpath(root)
    errs, records = [], []
    allowed_other = stdlib_dirs() + [os.path.realpath(c) for c in candidate_paths]
    stems = _tool_stems(root)
    for name, mod in sorted(list(sys.modules.items())):
        if mod is None:
            continue
        top = name.split('.')[0]
        f = _module_file(mod)
        trusted = top in TRUSTED_PACKAGES or name in stems
        if f is None and name == '__main__':
            continue
        if trusted:
            if name in preloaded:
                errs.append(RunError('IMPORT_PRELOADED', name))
            if f is None:
                paths = list(getattr(mod, '__path__', []) or [])
                if not paths:
                    errs.append(RunError('IMPORT_NO_FILE', name))
                for p in paths:
                    if not _inside(p, root):
                        errs.append(RunError('IMPORT_OUTSIDE_EXTRACTION', '%s %s' % (name, p)))
                    records.append((name, os.path.realpath(p)))
                continue
            if not _inside(f, root):
                errs.append(RunError('IMPORT_OUTSIDE_EXTRACTION', '%s %s' % (name, f)))
            if name in stems and not _inside(f, os.path.join(root, 'tools')):
                errs.append(RunError('IMPORT_TOOL_OUTSIDE_TOOLS', '%s %s' % (name, f)))
            records.append((name, os.path.realpath(f)))
        elif f is not None:
            if _inside(f, os.path.join(root, 'tools')):
                records.append((name, os.path.realpath(f)))
            elif not (_inside(f, root) or any(_inside(f, a) for a in allowed_other)):
                errs.append(RunError('IMPORT_UNTRUSTED_LOCATION', '%s %s' % (name, f)))
    main = sys.modules.get('__main__')
    mf = getattr(main, '__file__', None) if main is not None else None
    if mf and not _inside(mf, root) and not any(_inside(mf, a) for a in allowed_other):
        errs.append(RunError('IMPORT_MAIN_OUTSIDE_EXTRACTION', mf))
    return errs, sorted(set(records))


def import_lines(records):
    return ['IMPORT %s %s' % (name, path) for name, path in records]


def candidate_check(path):
    """P3-B04 / DP-4.3 (c): a candidate directory may contain no top-level module or package of a trusted name.
    Returns a list of RunError."""
    errs = []
    path = os.path.realpath(path)
    if not os.path.isdir(path):
        return [RunError('CANDIDATE_PATH_INVALID', path)]
    for entry in sorted(os.listdir(path)):
        stem = entry[:-3] if entry.endswith('.py') else entry
        full = os.path.join(path, entry)
        is_mod = entry.endswith('.py') or (os.path.isdir(full) and (os.path.exists(os.path.join(full, '__init__.py')) or not entry.startswith('.')))
        if is_mod and (stem in TRUSTED_PACKAGES or any(stem.startswith(t + '.') for t in TRUSTED_PACKAGES)):
            errs.append(RunError('CANDIDATE_SHADOWS_TRUSTED', '%s %s' % (stem, full)))
    return errs


def load_candidate(path, spec, root=ROOT):
    """P3-B04 / DP-4.3 (c): the trusted harness is imported first; the candidate directory is APPENDED to sys.path (never inserted
    first); a candidate module whose name equals or starts with a trusted package name is refused; after loading, import_identity runs
    and every candidate module must resolve under the candidate path.  Returns (module, errors)."""
    import importlib
    errs = []
    top = spec.split('.')[0]
    if top in TRUSTED_PACKAGES:
        return None, [RunError('CANDIDATE_SHADOWS_TRUSTED', '%s %s' % (spec, path))]
    errs.extend(candidate_check(path))
    if errs:
        return None, errs
    cpath = os.path.realpath(path)
    if cpath not in sys.path:
        sys.path.append(cpath)
    try:
        mod = importlib.import_module(spec)
    except Exception as e:  # the candidate failed to import: a run error, never a pass
        return None, [RunError('CANDIDATE_IMPORT_FAILED', '%s %s' % (spec, type(e).__name__))]
    f = _module_file(mod)
    if f is None or not _inside(f, cpath):
        errs.append(RunError('CANDIDATE_OUTSIDE_PATH', '%s %s' % (spec, f)))
    for name, m in list(sys.modules.items()):
        if m is None or not (name == top or name.startswith(top + '.')):
            continue
        mf = _module_file(m)
        if mf is not None and not _inside(mf, cpath):
            errs.append(RunError('CANDIDATE_OUTSIDE_PATH', '%s %s' % (name, mf)))
    ierrs, _ = import_identity(root, candidate_paths=(cpath,))
    for e in ierrs:
        if e.code == 'IMPORT_OUTSIDE_EXTRACTION':
            errs.append(RunError('HARNESS_SHADOWED', e.detail))
        else:
            errs.append(e)
    return mod, errs

# ---------------------------------------------------------------------------------------------------------------------------------------
# Step 2: §2.7 the RESULT v=2 schema, reconciliation, the derived status and exit (§2.4), and the checker
# ---------------------------------------------------------------------------------------------------------------------------------------

HEX64 = re.compile(r'^[0-9a-f]{64}$')
INT = re.compile(r'^(0|[1-9][0-9]*)$')
CONTROL_VALUES = ('PASS', 'FAIL', 'TIMEOUT', 'NOT_RUN')
STATUS_EXIT = {'EVIDENCE_ERROR': 2, 'INDETERMINATE': 3, 'FAILED': 1, 'OK': 0,
               'OK_WITH_EXCLUSIONS': 0}   # W-1 (owner, 2026-10-31 20:57): kind=wrapper only; derive_status gives it for no other kind

# the field order of each kind's RESULT line, exactly as §2.7 gives it ('tok' token, 'int' count, 'hex' 64-hex, tuples = enumerations)
RESULT_FIELDS = {
    'mutation': [('tool', 'tok'), ('run', 'tok'), ('selected', 'int'), ('preflight', ('PASS', 'FAIL', 'NOT_RUN')),
                 ('control_start', CONTROL_VALUES), ('started', 'int'), ('completed', 'int'), ('killed', 'int'), ('survived', 'int'),
                 ('equivalent', 'int'), ('indeterminate', 'int'), ('item_errors', 'int'), ('not_run', 'int'),
                 ('control_end', CONTROL_VALUES), ('run_errors', 'int'), ('ids_sha256', 'hex')],
    'sabotage': [('tool', 'tok'), ('run', 'tok'), ('selected', 'int'), ('preflight', ('PASS', 'FAIL', 'NOT_RUN')),
                 ('control_start', CONTROL_VALUES), ('started', 'int'), ('completed', 'int'), ('caught', 'int'), ('missed', 'int'),
                 ('indeterminate', 'int'), ('item_errors', 'int'), ('not_run', 'int'), ('control_end', CONTROL_VALUES),
                 ('run_errors', 'int'), ('ids_sha256', 'hex')],
    'cases': [('tool', 'tok'), ('run', 'tok'), ('suites_selected', 'int'), ('selected', 'int'), ('started', 'int'), ('completed', 'int'),
              ('passed', 'int'), ('failed', 'int'), ('indeterminate', 'int'), ('item_errors', 'int'), ('not_run', 'int'),
              ('run_errors', 'int'), ('case_inventory_sha256', 'hex')],
    'tests': [('tool', 'tok'), ('mode', ('full', 'failfast')), ('run', 'tok'), ('files_selected', 'int'), ('files_started', 'int'),
              ('files_completed', 'int'), ('files_indeterminate', 'int'), ('files_errored', 'int'), ('files_not_run', 'int'),
              ('files_skipped_after_failure', 'int'), ('tests', 'int'), ('passed', 'int'), ('failed', 'int'), ('errors', 'int'),
              ('skipped', 'int'), ('run_errors', 'int'), ('inventory_sha256', 'hex')],
    # W-1 (APG_D14_STAGE1_DECISION_W1_REV2.md draft 2 §1.3): the successor wrappers' line
    'wrapper': [('tool', 'tok'), ('mode', ('full',)), ('run', 'tok'), ('groups_selected', 'int'), ('files_selected', 'int'),
                ('files_started', 'int'), ('files_completed', 'int'), ('files_indeterminate', 'int'), ('files_errored', 'int'),
                ('files_not_run', 'int'), ('files_skipped_after_failure', 'int'), ('tests', 'int'), ('passed', 'int'), ('failed', 'int'),
                ('errors', 'int'), ('skipped', 'int'), ('checks_selected', 'int'), ('checks_passed', 'int'), ('checks_failed', 'int'),
                ('checks_indeterminate', 'int'), ('checks_errored', 'int'), ('checks_not_run', 'int'), ('excluded_historical', 'int'),
                ('run_errors', 'int'), ('inventory_sha256', 'hex'), ('checks_sha256', 'hex'), ('exclusions_sha256', 'hex')],
}
TAIL_FIELDS = [('status', tuple(STATUS_EXIT)), ('exit', ('0', '1', '2', '3'))]
# Corrective pass 2 (A.2, K.3): kind=cases, mutation and sabotage are written at v=3; tests and wrapper stay v=2.  RESULT_FIELDS above is
# the frozen v=2 schema, which the checker keeps reading for the historical evidence.  cases v=3 adds suites after suites_selected (A.1);
# mutation and sabotage v=3 have v=2's fields in v=2's order, and change the consistency rules (K.1, B.4).
RESULT_FIELDS_V3 = {
    'cases': RESULT_FIELDS['cases'][:2] + [('suites_selected', 'int'), ('suites', 'suites')] + RESULT_FIELDS['cases'][3:],
    'mutation': list(RESULT_FIELDS['mutation']),
    'sabotage': list(RESULT_FIELDS['sabotage']),
}
WRITE_VERSION = {'cases': 3, 'mutation': 3, 'sabotage': 3, 'tests': 2, 'wrapper': 2}
EMPTY_SHA256 = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'   # A.1: sha256_lines([])
SUITES_RE = re.compile(r'^(-|[A-Za-z0-9_.:-]+(,[A-Za-z0-9_.:-]+)*)$')

ITEM_LINE = {'mutation': 'MUTANT', 'sabotage': 'PLANT', 'cases': 'CASE'}
ITEM_OUTCOMES = {
    'mutation': ('KILLED', 'SURVIVED', 'EQUIVALENT', 'INDETERMINATE', 'ITEM_ERROR', 'NOT_RUN'),
    'sabotage': ('CAUGHT', 'MISSED', 'INDETERMINATE', 'ITEM_ERROR', 'NOT_RUN'),
    'cases': ('PASS', 'FAIL', 'INDETERMINATE', 'ITEM_ERROR', 'NOT_RUN'),
}
COMPLETED_OUTCOMES = {'mutation': ('KILLED', 'SURVIVED', 'EQUIVALENT'), 'sabotage': ('CAUGHT', 'MISSED'), 'cases': ('PASS', 'FAIL')}
FILE_STATES = ('COMPLETED', 'INDETERMINATE', 'ITEM_ERROR', 'NOT_RUN', 'SKIPPED_AFTER_FAILURE')
TEST_STATUSES = ('PASS', 'FAIL', 'ERROR', 'SKIP', 'NOT_RUN_AFTER_FAILURE')


def _item_id(kind, value):
    """An item id: a token; for kind=cases it is '<suite>/<case_id>', each part a token (§2.7)."""
    value = str(value)
    if kind == 'cases':
        parts = value.split('/', 1)
        if len(parts) != 2 or not TOKEN.match(parts[0]) or not TOKEN.match(parts[1]):
            raise ValueError('a case id must be <suite>/<case_id>, each part a token: %r' % value)
        return value
    return _tok(value, 'item id')


def _tok(value, what):
    value = str(value)
    if not TOKEN.match(value):
        raise ValueError('%s must match [A-Za-z0-9_.:-]+: %r' % (what, value))
    return value


def derive_status(kind, c):
    """§2.7: the status and exit, derived from the counts by the fixed precedence 2, then 3, then 1, then 0.
    c: the RESULT fields (ints for counts).  'reconciled' (bool) says whether every reconciliation held."""
    if not c.get('reconciled', True) or c['run_errors'] > 0:
        return 'EVIDENCE_ERROR'
    if kind == 'wrapper':     # W-1 §1.4
        if c['files_errored'] > 0 or c['checks_errored'] > 0 or c['files_selected'] + c['checks_selected'] == 0:
            return 'EVIDENCE_ERROR'
        if c['files_not_run'] > 0 or c['files_indeterminate'] > 0 or c['checks_indeterminate'] > 0 or c['checks_not_run'] > 0:
            return 'INDETERMINATE'
        if c['failed'] + c['errors'] > 0 or c['files_skipped_after_failure'] > 0 or c['checks_failed'] > 0:
            return 'FAILED'
        return 'OK' if c['excluded_historical'] == 0 else 'OK_WITH_EXCLUSIONS'
    if kind in ('mutation', 'sabotage', 'cases'):
        if c['item_errors'] > 0 or c['selected'] == 0:
            return 'EVIDENCE_ERROR'
        if c['not_run'] > 0 or c['indeterminate'] > 0:
            return 'INDETERMINATE'
        if kind in ('mutation', 'sabotage') and (c['control_start'] != 'PASS' or c['control_end'] != 'PASS'):
            return 'INDETERMINATE'
        fail = {'mutation': 'survived', 'sabotage': 'missed', 'cases': 'failed'}[kind]
        return 'FAILED' if c[fail] > 0 else 'OK'
    if c['files_errored'] > 0 or c['files_selected'] == 0:
        return 'EVIDENCE_ERROR'
    if c['files_not_run'] > 0 or c['files_indeterminate'] > 0:
        return 'INDETERMINATE'
    return 'FAILED' if c['failed'] + c['errors'] > 0 or c['files_skipped_after_failure'] > 0 else 'OK'


def result_line(kind, fields):
    v = WRITE_VERSION[kind]
    names = [n for n, _ in (RESULT_FIELDS_V3 if v == 3 else RESULT_FIELDS)[kind]] + [n for n, _ in TAIL_FIELDS]
    head = 'RESULT v=%d kind=%s' % (v, kind)
    return head + ''.join(' %s=%s' % (n, fields[n]) for n in names)


def finish_items(kind, tool, run_id, selected, outcomes, run_errors=(), preflight='PASS', control_start='PASS', control_end='PASS',
                 not_run_cause='not_started', suites_selected=None, case_inventory_sha256=None, suites=None):
    """§2.7 for kind=mutation, sabotage or cases.  selected: the selected ids, in order.  outcomes: id -> (outcome, cause) for the items
    that STARTED only; no worker ever creates NOT_RUN.  Every selected id with no outcome gets one NOT_RUN line with not_run_cause.
    Returns (lines, exit_code): the per-item lines, the RUN_ERROR lines and the one RESULT line, in that order."""
    tool = _tok(tool, 'tool')
    run_id = _tok(run_id, 'run')
    errs = list(run_errors) + _SUP.close_run()
    sel = list(selected)
    seen = set()
    for i in sel:
        _item_id(kind, i)
        if i in seen:
            errs.append(RunError('SELECTION_INVALID', 'duplicate %s' % i))
        seen.add(i)
    if not sel and not errs:
        errs.append(RunError('SELECTION_INVALID', 'zero_selected'))
    for i in outcomes:
        if i not in seen:
            errs.append(RunError('RESULT_FOR_UNSELECTED_ITEM', i))
    if kind in ('mutation', 'sabotage'):
        if preflight != 'PASS' or control_start != 'PASS':
            if any(i in outcomes for i in sel):
                errs.append(RunError('ITEM_STARTED_WITHOUT_PREFLIGHT_AND_CONTROL', '%s %s' % (preflight, control_start)))
            outcomes = {}
            control_end = 'NOT_RUN'
    lines = []
    counts = dict.fromkeys(ITEM_OUTCOMES[kind], 0)
    for i in dict.fromkeys(sel):
        if i in outcomes:
            o, cause = outcomes[i]
            if o not in ITEM_OUTCOMES[kind] or o == 'NOT_RUN':
                errs.append(RunError('WORKER_OUTCOME_INVALID', '%s %s' % (i, o)))
                o, cause = 'ITEM_ERROR', 'worker_outcome_invalid'
        else:
            o, cause = 'NOT_RUN', not_run_cause
        counts[o] += 1
        lines.append('%s %s %s cause=%s' % (ITEM_LINE[kind], i, o, _tok(cause, 'cause')))
    not_run = counts['NOT_RUN']
    started = len(dict.fromkeys(sel)) - not_run
    completed = sum(counts[o] for o in COMPLETED_OUTCOMES[kind])
    if kind in ('mutation', 'sabotage') and not_run > 0 and control_start == 'PASS' and preflight == 'PASS':
        control_end = 'NOT_RUN'  # §2.7: control_end=NOT_RUN if the run was stopped before the last item
    f = {'tool': tool, 'run': run_id, 'selected': len(sel), 'started': started, 'completed': completed,
         'indeterminate': counts['INDETERMINATE'], 'item_errors': counts['ITEM_ERROR'], 'not_run': not_run}
    if kind == 'mutation':
        f.update(killed=counts['KILLED'], survived=counts['SURVIVED'], equivalent=counts['EQUIVALENT'])
    elif kind == 'sabotage':
        f.update(caught=counts['CAUGHT'], missed=counts['MISSED'])
    else:
        # A.1 (v=3): suites is the resolved selection, sorted; None means no resolved selection.  cases_main always passes it; a direct
        # caller that passes none with selected cases has its suites taken from those cases' ids ('<suite>/<case>')
        if suites is None and sel:
            suites = [x.split('/', 1)[0] for x in sel]
        sl = sorted(dict.fromkeys(suites)) if suites is not None else []
        f.update(passed=counts['PASS'], failed=counts['FAIL'], suites_selected=len(sl) if suites is not None else 0,
                 suites=','.join(sl) or '-', case_inventory_sha256=case_inventory_sha256 or sha256_lines(sel))
    if kind in ('mutation', 'sabotage'):
        f.update(preflight=preflight, control_start=control_start, control_end=control_end, ids_sha256=sha256_lines(sel))
    f['run_errors'] = len(errs)
    status = derive_status(kind, f)
    f.update(status=status, exit=STATUS_EXIT[status])
    out = lines + [e.line() for e in errs] + [result_line(kind, f)]
    return out, STATUS_EXIT[status]


class FileResult:
    """One test file's observed result (kind=tests).  tests: [(test id, 'PASS'|'FAIL'|'ERROR'|'SKIP')] in execution order.
    not_run_after_failure: the pinned ids that did not run because the file stopped at its first failing test (mode=failfast only).
    state: 'COMPLETED', 'INDETERMINATE' or 'ITEM_ERROR' (a worker never creates NOT_RUN or SKIPPED_AFTER_FAILURE)."""

    def __init__(self, name, state, tests, file_sha256, not_run_after_failure=(), cause=''):
        self.name, self.state, self.tests, self.file_sha256 = name, state, list(tests), file_sha256
        self.not_run_after_failure = list(not_run_after_failure)
        self.cause = cause


def finish_tests(tool, mode, run_id, selected, results, pins, run_errors=()):
    """§2.7 for kind=tests.  selected: the selected file names, in run order.  results: name -> FileResult for the files that STARTED.
    pins: name -> {'sha256': file hash, 'ids': [pinned test ids]} (§2.2).  Returns (lines, exit_code).
    The TEST lines of each file come before its FILE line; then the RUN_ERROR lines; then the one RESULT line."""
    tool = _tok(tool, 'tool')
    run_id = _tok(run_id, 'run')
    if mode not in ('full', 'failfast'):
        raise ValueError('mode must be full or failfast')
    errs = list(run_errors) + _SUP.close_run()
    sel = list(selected)
    if len(set(sel)) != len(sel):
        errs.append(RunError('SELECTION_INVALID', 'duplicate file'))
    if not sel and not errs:
        errs.append(RunError('SELECTION_INVALID', 'zero_selected'))
    for n in sel:
        _tok(n, 'file name')
        if n not in pins:
            errs.append(RunError('TEST_FILE_NOT_IN_PINS', n))
    for n in results:
        if n not in sel:
            errs.append(RunError('RESULT_FOR_UNSELECTED_FILE', n))
    lines = []
    c = dict(files_completed=0, files_indeterminate=0, files_errored=0, files_not_run=0, files_skipped_after_failure=0,
             tests=0, passed=0, failed=0, errors=0, skipped=0)
    failed_seen = False
    for n in dict.fromkeys(sel):
        r = results.get(n)
        pin = pins.get(n, {'sha256': '0' * 64, 'ids': []})
        if r is None:
            state = 'SKIPPED_AFTER_FAILURE' if (mode == 'failfast' and failed_seen) else 'NOT_RUN'
            ran, nraf, fsha = [], [], pin['sha256']
        else:
            state, ran, nraf, fsha = r.state, r.tests, r.not_run_after_failure, r.file_sha256
            if state not in ('COMPLETED', 'INDETERMINATE', 'ITEM_ERROR'):
                errs.append(RunError('WORKER_STATE_INVALID', '%s %s' % (n, state)))
                state = 'ITEM_ERROR'
            if mode == 'failfast' and failed_seen:
                errs.append(RunError('FILE_STARTED_AFTER_FAILURE', n))
        for tid, st in ran:
            if st not in ('PASS', 'FAIL', 'ERROR', 'SKIP'):
                errs.append(RunError('TEST_STATUS_INVALID', '%s %s' % (n, st)))
            lines.append('TEST %s::%s %s' % (n, tid, st))
        for tid in nraf:
            lines.append('TEST %s::%s NOT_RUN_AFTER_FAILURE' % (n, tid))
        k = {s: sum(1 for _, x in ran if x == s) for s in ('PASS', 'FAIL', 'ERROR', 'SKIP')}
        tests_not_run = len(nraf) if state == 'COMPLETED' else 0
        if state == 'COMPLETED':
            ran_ids = [t for t, _ in ran]
            if fsha != pin['sha256']:
                errs.append(RunError('TEST_INVENTORY_MISMATCH', '%s file_sha256' % n))
            if nraf:
                if mode != 'failfast' or not (k['FAIL'] + k['ERROR'] == 1 and ran and ran[-1][1] in ('FAIL', 'ERROR')):
                    errs.append(RunError('TEST_INVENTORY_MISMATCH', '%s stopped_without_one_last_failure' % n))
                if set(ran_ids) & set(nraf) or sorted(ran_ids + nraf) != sorted(pin['ids']):
                    errs.append(RunError('TEST_INVENTORY_MISMATCH', '%s ids' % n))
            elif sorted(ran_ids) != sorted(pin['ids']) or len(set(ran_ids)) != len(ran_ids):
                errs.append(RunError('TEST_INVENTORY_MISMATCH', '%s ids' % n))
            c['files_completed'] += 1
            c['tests'] += len(ran)
            c['passed'] += k['PASS']
            c['failed'] += k['FAIL']
            c['errors'] += k['ERROR']
            c['skipped'] += k['SKIP']
            if k['FAIL'] + k['ERROR'] > 0:
                failed_seen = True
        else:
            if nraf:
                errs.append(RunError('TEST_INVENTORY_MISMATCH', '%s not_run_after_failure_on_%s' % (n, state)))
            if state in ('NOT_RUN', 'SKIPPED_AFTER_FAILURE') and ran:
                errs.append(RunError('TESTS_ON_FILE_NOT_STARTED', n))
            key = {'INDETERMINATE': 'files_indeterminate', 'ITEM_ERROR': 'files_errored', 'NOT_RUN': 'files_not_run',
                   'SKIPPED_AFTER_FAILURE': 'files_skipped_after_failure'}[state]
            c[key] += 1
        lines.append('FILE %s state=%s tests=%d passed=%d failed=%d errors=%d skipped=%d tests_not_run=%d file_sha256=%s ids_sha256=%s'
                     % (n, state, len(ran), k['PASS'], k['FAIL'], k['ERROR'], k['SKIP'], tests_not_run, fsha,
                        sha256_lines([t for t, _ in ran])))
    if mode == 'full' and c['files_skipped_after_failure']:
        errs.append(RunError('SKIPPED_AFTER_FAILURE_IN_FULL_MODE', str(c['files_skipped_after_failure'])))
    inv = sha256_lines(['%s::%s' % (n, t) for n in dict.fromkeys(sel) for t in pins.get(n, {'ids': []})['ids']])
    f = dict(c, tool=tool, mode=mode, run=run_id, files_selected=len(sel),
             files_started=c['files_completed'] + c['files_indeterminate'] + c['files_errored'], run_errors=len(errs), inventory_sha256=inv)
    status = derive_status('tests', f)
    f.update(status=status, exit=STATUS_EXIT[status])
    return lines + [e.line() for e in errs] + [result_line('tests', f)], STATUS_EXIT[status]


def refuse_run(kind, tool, ids, error, run_id='run'):
    """§2.7: a run the tool refuses before any work (an option it does not take, a tool-definition error) still ends with one RESULT v=2
    line: the RUN_ERROR line, every item NOT_RUN cause=run_error, exit 2.  ids: the tool's universe (duplicates collapsed)."""
    out, code = finish_items(kind, tool, run_id, list(dict.fromkeys(ids)), {}, run_errors=[error], preflight='NOT_RUN',
                             control_start='NOT_RUN', not_run_cause='run_error')
    return emit(out, code)


def list_mutants(tool, build, kind='mutation'):
    """Decision (c) (owner, 2026-11-02 14:24): the tool's own listing of its mutants (build(), which reads the target files) is part of
    the run.  If it fails (a target file missing, a region marker gone), the run is refused before any work: RUN_ERROR
    MUTANT_LIST_INVALID, every pinned mutant NOT_RUN cause=run_error, one RESULT v=2 line, exit 2, never a traceback.
    Returns (mutants, None), or (None, the exit code of the refusal it printed)."""
    try:
        return build(), None
    except Exception as e:
        try:
            ids = load_pins()[0]['mutation_lists' if kind == 'mutation' else 'plant_lists'][tool]['ids']
        except Exception:
            ids = []
        return None, refuse_run(kind, tool, ids, RunError('MUTANT_LIST_INVALID', '%s %s' % (type(e).__name__, one_line(str(e))[:200])))


def emit(lines, exit_code, success_marker=None, stream=None, before_result=()):
    """Print the lines; print the tool's existing success marker, verbatim, only on exit 0 (§2.4); return the exit code for sys.exit.
    The marker goes immediately before the RESULT line, so the RESULT line stays the last non-empty line (§2.7 format rules) and the
    marker is still present for the M10 substring consumers (T_tooling.md, 'Compatibility')."""
    stream = stream or sys.stdout
    lines = list(lines)
    # P.5 step 8 and F.2: the CLEANUP records and the CLEANUP_SUMMARY line (a supervisor), and the INTERRUPTED or
    # SIGNAL_AFTER_COMPLETION record, come before the RESULT line.  In an output with no RESULT line (amendment 2, AM2-2 (a)) the P lines
    # and SIGNAL_AFTER_COMPLETION come before its last line, and INTERRUPTED is the last line.
    has_result = any(l.startswith('RESULT ') for l in lines)
    # an output with no RESULT line carries P's lines only when it is a run's output (the 6 supervisors of AM2-2 and a mutation tool's
    # --baseline); a listing or a pin write (--list, --pin) has none
    is_run = has_result or _SUP.run_without_result
    rec = CANCEL.record() if is_run and (_SUP.supervisor or CANCEL.installed) else None
    p_lines = (_SUP.final_lines() if is_run else []) + ([rec] if rec and rec.startswith('SIGNAL_AFTER_COMPLETION') else [])
    tail = [rec] if rec and rec.startswith('INTERRUPTED') else []
    at = max((i for i, l in enumerate(lines) if l.startswith('RESULT ')), default=max(len(lines) - 1, 0))
    lines[at:at] = p_lines
    at += len(p_lines)
    if has_result and before_result:      # a caller's own marker lines, kept immediately before the RESULT line (§2.4)
        lines[at:at] = list(before_result)
        at += len(before_result)
    if success_marker and exit_code == 0:
        lines.insert(at if has_result else len(lines), success_marker)
        at += 1 if has_result else 0
    if has_result:
        lines[at:at] = tail
    else:
        lines += tail
    try:
        for line in lines:
            print(line, file=stream)
        stream.flush()
    except BrokenPipeError:  # a reader that closed early (for example '| head'): the exit code still stands
        pass
    return exit_code


def parse_result_line(line):
    """Parse one RESULT line under §2.7's format rules.  Returns (kind, fields) or raises ValueError with the reason."""
    parts = line.split(' ')
    if line != line.strip() or '' in parts:
        raise ValueError('RESULT line spacing')
    if parts[0] != 'RESULT' or len(parts) < 3 or parts[1] not in ('v=2', 'v=3') or not parts[2].startswith('kind='):
        raise ValueError('RESULT line head (v=2, or v=3 for kind=cases, mutation and sabotage, is read)')
    kind = parts[2][5:]
    if kind not in RESULT_FIELDS:
        raise ValueError('RESULT kind %r' % kind)
    v = int(parts[1][2:])
    if v == 3 and kind not in RESULT_FIELDS_V3:
        raise ValueError('RESULT v=3 is not defined for kind=%s' % kind)
    spec = (RESULT_FIELDS_V3 if v == 3 else RESULT_FIELDS)[kind] + TAIL_FIELDS
    if len(parts) - 3 != len(spec):
        raise ValueError('RESULT field count')
    fields = {}
    for part, (name, typ) in zip(parts[3:], spec):
        if '=' not in part:
            raise ValueError('RESULT field %r' % part)
        k, v = part.split('=', 1)
        if k != name:
            raise ValueError('RESULT field order: %s where %s expected' % (k, name))
        if typ == 'int':
            if not INT.match(v):
                raise ValueError('RESULT %s not a count' % k)
            v = int(v)
        elif typ == 'hex':
            if not HEX64.match(v):
                raise ValueError('RESULT %s not 64 hex' % k)
        elif typ == 'tok':
            if not TOKEN.match(v):
                raise ValueError('RESULT %s not a token' % k)
        elif typ == 'suites':
            if not SUITES_RE.match(v):
                raise ValueError('RESULT suites malformed')
        elif v not in typ:
            raise ValueError('RESULT %s=%s not allowed' % (k, v))
        fields[k] = v
    fields['exit'] = int(fields['exit'])
    fields['v'] = int(parts[1][2:])
    return kind, fields


def check_output(text, actual_exit=None, pins=None, selected=None):
    """The checker (§2.7): re-derive everything from the output alone (and the pins and selection, when given) and return the list of
    problems; an empty list means the output is valid evidence.  Rejects malformed, missing, duplicated or contradictory records.
    pins (kind=tests): name -> {'sha256', 'ids'}; (kind=cases) the tool's pinned case inventories, suite -> {'ids', ...}: with them the
    checker verifies case_inventory_sha256 (decision (a'), owner 2026-11-02 15:33); without them it cannot verify that field.
    selected: the ids or file names the run was asked for, in order."""
    problems = []
    lines = [l for l in text.splitlines() if l.strip()]
    rlines = [i for i, l in enumerate(lines) if l.startswith('RESULT')]
    if not rlines:
        return ['no RESULT line']
    if len(rlines) > 1:
        return ['more than one RESULT line']
    if rlines[0] != len(lines) - 1:
        return ['RESULT is not the last non-empty line']
    try:
        kind, f = parse_result_line(lines[-1])
    except ValueError as e:
        return [str(e)]
    if actual_exit is not None and f['exit'] != actual_exit:
        problems.append('exit=%d but the process exited %d' % (f['exit'], actual_exit))
    if STATUS_EXIT[f['status']] != f['exit']:
        problems.append('status %s contradicts exit %d' % (f['status'], f['exit']))
    run_errors = [l for l in lines if l.startswith('RUN_ERROR ')]
    if len(run_errors) != f['run_errors']:
        problems.append('run_errors=%d but %d RUN_ERROR lines' % (f['run_errors'], len(run_errors)))
    if kind in ITEM_LINE:
        # corrective pass 2 (K.3): dispatched by kind and version together; a v=2 line is never read under v=3's rules
        problems += _check_items(kind, f, lines, selected)
        if kind == 'cases' and f['v'] == 2 and pins is not None:
            problems += _check_case_inventory(f, lines, pins)
        if kind == 'cases' and f['v'] == 3:
            problems += _check_suites_v3(f, lines, pins)
    elif kind == 'wrapper':
        problems += _check_wrapper(f, lines, pins, selected)
    else:
        problems += _check_tests(f, lines, pins, selected)
    derived = derive_status(kind, dict(f, reconciled=not problems))
    if derived != f['status']:
        problems.append('status %s but the counts give %s' % (f['status'], derived))
    return problems


def _check_case_inventory(f, lines, case_pins):
    """Decision (a') (owner, 2026-11-02 15:33).  case_inventory_sha256 is the hash of the selected suites' PINNED inventories (R1 §2.7),
    not of the cases a partial (--only) run printed.  The suites named by the CASE records are among the selected suites, in the order
    the run took them; a selected suite may print no CASE record (an --only that picks cases from another suite; a refusal prints none).
    So the expected hash is sha256_lines('<suite>/<case>' over the pinned cases of the selected suites), for some choice of
    suites_selected pinned suites that contains the CASE records' suites.  sha256_lines sorts its lines, so the hash depends only on the
    set of suites, not on their order: the ordered search below is redundant (corrective pass 2, mistake 17, which corrects the earlier
    wording 'in their order').  A field matching no such choice, or a CASE suite that is not pinned, is a problem.  Without the pins
    (check_output pins=None) this field cannot be verified."""
    import itertools
    seen = []
    for l in lines:
        m = re.match(r'^CASE (\S+?)/\S+ ', l)
        if m and m.group(1) not in seen:
            seen.append(m.group(1))
    p = ['CASE suite %s is not in the pinned case inventories' % s for s in seen if s not in case_pins]
    k = f['suites_selected']
    if p or k < len(seen):
        return p or ['suites_selected=%d but the CASE records name %d suites' % (k, len(seen))]
    others = sorted(s for s in case_pins if s not in seen)
    if k - len(seen) > len(others):
        return ['suites_selected=%d is more than the pinned suites' % k]

    def merges(a, b):          # every interleaving of a and b that keeps the order of each
        if not a or not b:
            yield list(a) + list(b)
            return
        for rest in merges(a[1:], b):
            yield [a[0]] + rest
        for rest in merges(a, b[1:]):
            yield [b[0]] + rest
    for extra in itertools.permutations(others, k - len(seen)):
        for order in merges(seen, list(extra)):
            if sha256_lines(['%s/%s' % (s, c) for s in order for c in case_pins[s]['ids']]) == f['case_inventory_sha256']:
                return []
    return ['case_inventory_sha256 does not match the pinned inventories of the selected suites']


def _check_items(kind, f, lines, selected):
    p = []
    tag = ITEM_LINE[kind]
    items = []
    for l in lines:
        if l.startswith(tag + ' '):
            m = re.match(r'^%s (\S+) (\S+) cause=(\S+)$' % tag, l)
            try:
                good_id = m is not None and _item_id(kind, m.group(1)) is not None
            except ValueError:
                good_id = False
            if not m or not good_id or m.group(2) not in ITEM_OUTCOMES[kind] or not TOKEN.match(m.group(3)):
                p.append('malformed %s line: %s' % (tag, l))
                continue
            items.append((m.group(1), m.group(2)))
    ids = [i for i, _ in items]
    if len(set(ids)) != len(ids):
        p.append('duplicate %s ids' % tag)
    if f['selected'] != len(ids):
        p.append('selected=%d but %d %s lines' % (f['selected'], len(ids), tag))
    if selected is not None and list(dict.fromkeys(selected)) != ids:
        p.append('%s ids differ from the selection' % tag)
    cnt = {o: sum(1 for _, x in items if x == o) for o in ITEM_OUTCOMES[kind]}
    names = {'mutation': {'killed': 'KILLED', 'survived': 'SURVIVED', 'equivalent': 'EQUIVALENT'},
             'sabotage': {'caught': 'CAUGHT', 'missed': 'MISSED'}, 'cases': {'passed': 'PASS', 'failed': 'FAIL'}}[kind]
    names = dict(names, indeterminate='INDETERMINATE', item_errors='ITEM_ERROR', not_run='NOT_RUN')
    for field, o in names.items():
        if f[field] != cnt[o]:
            p.append('%s=%d but %d %s lines' % (field, f[field], cnt[o], o))
    if f['started'] + f['not_run'] != f['selected']:
        p.append('started + not_run != selected')
    if f['completed'] + f['indeterminate'] + f['item_errors'] != f['started']:
        p.append('completed + indeterminate + item_errors != started')
    done = sum(f[k] for k in names if k not in ('indeterminate', 'item_errors', 'not_run'))
    if done != f['completed']:
        p.append('completed != the sum of the completed outcomes')
    if kind in ('mutation', 'sabotage'):
        if f['ids_sha256'] != sha256_lines(ids):
            p.append('ids_sha256 does not match the %s ids' % tag)
        if (f['preflight'] != 'PASS' or f['control_start'] != 'PASS') and f['started'] != 0:
            p.append('items started without preflight=PASS and control_start=PASS')
        if f['preflight'] == 'NOT_RUN' and f['started'] != 0:
            p.append('preflight=NOT_RUN with started items')
        if f['v'] == 2:
            stopped = f['not_run'] > 0
            if (f['control_end'] == 'NOT_RUN') != (f['control_start'] != 'PASS' or f['preflight'] != 'PASS' or stopped):
                p.append('control_end=NOT_RUN must hold exactly when the start control did not pass or the run stopped')
        else:
            p += _check_controls_v3(f, lines, [l for l in lines if l.startswith(tag + ' ')])
    return p


CONTROL_LINE = re.compile(r'^CONTROL (start|end) (\S+) cause=(\S+)')
INTERRUPTED_RE = re.compile(r'^INTERRUPTED signal=(SIGINT|SIGTERM) at=(\S+) received=([1-9][0-9]*)$')


def _check_controls_v3(f, lines, item_lines):
    """K.1 and B.4 (kind=mutation and sabotage, v=3).
    - control_end=NOT_RUN if and only if control_start (or the preflight) is not PASS, or the run was stopped before its last item (an
      item NOT_RUN, or an item stopped in flight: cause interrupted or run_stopped), or the run was stopped after its last item and
      before the end control's outcome was fixed.  That last case needs the stop record for that moment (RUN_ERROR ENV_DISK_BELOW_FLOOR
      control_end ..., or INTERRUPTED ... at=control_end) and no completed CONTROL end record.  A stop record for another phase never
      permits it.  An end control that completed reports its own outcome.
    - 'CONTROL start CONTROL_INTERRUPTED' only with control_start=FAIL and INTERRUPTED ... at=control_start; 'CONTROL end
      CONTROL_NOT_RUN' only with control_end=NOT_RUN and the stop record of K.1 with the matching cause; a completed CONTROL line's value
      equal to its field.
    - INTERRUPTED: at most one, immediately before the RESULT line, never beside SIGNAL_AFTER_COMPLETION, never with status OK or
      FAILED; INTERRUPTED ... at=control_end never beside a completed end control."""
    p = []
    ints = [l for l in lines if l.startswith('INTERRUPTED')]
    sacs = [l for l in lines if l.startswith('SIGNAL_AFTER_COMPLETION')]
    at = None
    if len(ints) > 1:
        p.append('more than one INTERRUPTED line')
    if ints:
        m = INTERRUPTED_RE.match(ints[0])
        if not m:
            p.append('malformed INTERRUPTED line: %s' % ints[0])
        else:
            at = m.group(2)
        if lines.index(ints[-1]) != len(lines) - 2:
            p.append('INTERRUPTED is not immediately before the RESULT line')
        if sacs:
            p.append('INTERRUPTED beside SIGNAL_AFTER_COMPLETION')
        if f['status'] in ('OK', 'FAILED'):
            p.append('INTERRUPTED with status %s' % f['status'])
    for l in sacs:
        if not re.match(r'^SIGNAL_AFTER_COMPLETION signal=(SIGINT|SIGTERM)$', l):
            p.append('malformed SIGNAL_AFTER_COMPLETION line: %s' % l)
    disk_end = any(re.match(r'^RUN_ERROR ENV_DISK_BELOW_FLOOR control_end ', l) for l in lines)
    ctl = {}
    for l in lines:
        m = CONTROL_LINE.match(l)
        if m:
            ctl.setdefault(m.group(1), []).append((m.group(2), m.group(3)))
    for ph in ctl:
        if len(ctl[ph]) > 1:
            p.append('more than one CONTROL %s line' % ph)
    end_completed = False
    for ph, field in (('start', 'control_start'), ('end', 'control_end')):
        for value, cause in ctl.get(ph, [])[:1]:
            if value == 'CONTROL_INTERRUPTED':
                if ph != 'start' or f['control_start'] != 'FAIL' or at != 'control_start' or cause != 'interrupted':
                    p.append('CONTROL %s CONTROL_INTERRUPTED needs control_start=FAIL and INTERRUPTED at=control_start' % ph)
            elif value == 'CONTROL_NOT_RUN':
                ok_cause = (cause == 'interrupted' and at == 'control_end') or (cause == 'disk_below_floor' and disk_end)
                if ph != 'end' or f['control_end'] != 'NOT_RUN' or not ok_cause:
                    p.append('CONTROL %s CONTROL_NOT_RUN needs control_end=NOT_RUN and the matching stop record' % ph)
            else:
                v = value[8:] if value.startswith('CONTROL_') else value
                if v not in ('PASS', 'FAIL', 'TIMEOUT'):
                    p.append('CONTROL %s value %s' % (ph, value))
                elif v != f[field]:
                    p.append('CONTROL %s %s but %s=%s' % (ph, value, field, f[field]))
                if ph == 'end':
                    end_completed = True
    causes = [l.rsplit('cause=', 1)[-1] for l in item_lines]
    before_last = f['not_run'] > 0 or any(c in ('interrupted', 'run_stopped') for c in causes)
    after_last = (at == 'control_end' or disk_end) and not end_completed
    if at == 'control_end' and end_completed:
        p.append('INTERRUPTED at=control_end beside a completed end control (a signal after its outcome is SIGNAL_AFTER_COMPLETION)')
    want = f['control_start'] != 'PASS' or f['preflight'] != 'PASS' or before_last or after_last
    if (f['control_end'] == 'NOT_RUN') != want:
        p.append('control_end=NOT_RUN must hold exactly when the start control did not pass, the run stopped before its last item, or '
                 'it stopped after its last item and before the end control\'s outcome was fixed (K.1)')
    return p


def _check_suites_v3(f, lines, case_pins):
    """A.3 (kind=cases, v=3): suites sorted, each once, well formed, pinned; its count equal to suites_selected; every suite a CASE
    record names in it; suites=- only with suites_selected=0, selected=0 and the empty-selection hash; case_inventory_sha256 the
    sha256_lines of the pinned case ids of exactly the listed suites, in the listed order (verified when the pins are given)."""
    p = []
    sv = f['suites']
    ids = [] if sv == '-' else sv.split(',')
    if ids != sorted(ids):
        p.append('suites is not sorted')
    if len(set(ids)) != len(ids):
        p.append('suites has a duplicate')
    if len(ids) != f['suites_selected']:
        p.append('suites lists %d but suites_selected=%d' % (len(ids), f['suites_selected']))
    named = []
    for l in lines:
        m = re.match(r'^CASE (\S+?)/\S+ ', l)
        if m and m.group(1) not in named:
            named.append(m.group(1))
    for s_ in named:
        if s_ not in ids:
            p.append('CASE suite %s is not in suites' % s_)
    if sv == '-':
        if f['suites_selected'] != 0 or f['selected'] != 0:
            p.append('suites=- with suites_selected or selected not 0')
        if f['case_inventory_sha256'] != EMPTY_SHA256:
            p.append('suites=- with a case_inventory_sha256 other than the empty selection\'s')
    if case_pins is not None:
        for s_ in named:
            if s_ not in case_pins:
                p.append('CASE suite %s is not in the pinned case inventories' % s_)
        for s_ in ids:
            if s_ not in case_pins:
                p.append('suites names %s, which is not pinned' % s_)
        if not any(s_ not in case_pins for s_ in ids):
            want = sha256_lines(['%s/%s' % (s_, c) for s_ in ids for c in case_pins[s_]['ids']])
            if f['case_inventory_sha256'] != want:
                p.append('case_inventory_sha256 does not match the pinned inventories of the selected suites')
    return p


def _check_tests(f, lines, pins, selected):
    p = []
    files, tests_by_file, order = [], {}, []
    fre = re.compile(r'^FILE (\S+) state=(\S+) tests=(\d+) passed=(\d+) failed=(\d+) errors=(\d+) skipped=(\d+) tests_not_run=(\d+) '
                     r'file_sha256=([0-9a-f]{64}) ids_sha256=([0-9a-f]{64})$')
    pending = []
    for l in lines:
        if l.startswith('TEST '):
            m = re.match(r'^TEST (\S+?)::(\S+) (\S+)$', l)
            if not m or m.group(3) not in TEST_STATUSES:
                p.append('malformed TEST line: %s' % l)
                continue
            pending.append((m.group(1), m.group(2), m.group(3)))
        elif l.startswith('FILE '):
            m = fre.match(l)
            if not m or m.group(2) not in FILE_STATES:
                p.append('malformed FILE line: %s' % l)
                pending = []
                continue
            name = m.group(1)
            if any(t[0] != name for t in pending):
                p.append('TEST lines of another file before FILE %s' % name)
            files.append((name, m.group(2)) + tuple(int(m.group(i)) for i in range(3, 9)) + (m.group(9), m.group(10)))
            tests_by_file[name] = [(t[1], t[2]) for t in pending if t[0] == name]
            pending = []
    if pending:
        p.append('TEST lines after the last FILE line')
    names = [x[0] for x in files]
    if len(set(names)) != len(names):
        p.append('duplicate FILE names')
    if f['files_selected'] != len(files):
        p.append('files_selected=%d but %d FILE lines' % (f['files_selected'], len(files)))
    if selected is not None and list(selected) != names:
        p.append('FILE names differ from the selection')
    st = {s: sum(1 for x in files if x[1] == s) for s in FILE_STATES}
    for field, s in (('files_completed', 'COMPLETED'), ('files_indeterminate', 'INDETERMINATE'), ('files_errored', 'ITEM_ERROR'),
                     ('files_not_run', 'NOT_RUN'), ('files_skipped_after_failure', 'SKIPPED_AFTER_FAILURE')):
        if f[field] != st[s]:
            p.append('%s=%d but %d FILE lines in state %s' % (field, f[field], st[s], s))
    if f['files_started'] + f['files_not_run'] + f['files_skipped_after_failure'] != f['files_selected']:
        p.append('files_started + files_not_run + files_skipped_after_failure != files_selected')
    if f['files_completed'] + f['files_indeterminate'] + f['files_errored'] != f['files_started']:
        p.append('files_completed + files_indeterminate + files_errored != files_started')
    if f['mode'] == 'full' and f['files_skipped_after_failure']:
        p.append('SKIPPED_AFTER_FAILURE in mode=full')
    tot = dict(tests=0, passed=0, failed=0, errors=0, skipped=0)
    failing_completed = []
    for (name, state, tests, passed, failed, errors, skipped, tnr, fsha, isha) in files:
        ts = tests_by_file.get(name, [])
        ran = [(i, s) for i, s in ts if s != 'NOT_RUN_AFTER_FAILURE']
        nraf = [i for i, s in ts if s == 'NOT_RUN_AFTER_FAILURE']
        k = {s: sum(1 for _, x in ran if x == s) for s in ('PASS', 'FAIL', 'ERROR', 'SKIP')}
        if (tests, passed, failed, errors, skipped) != (len(ran), k['PASS'], k['FAIL'], k['ERROR'], k['SKIP']):
            p.append('FILE %s counts differ from its TEST lines' % name)
        if isha != sha256_lines([i for i, _ in ran]):
            p.append('FILE %s ids_sha256 does not match its TEST lines' % name)
        if state in ('NOT_RUN', 'SKIPPED_AFTER_FAILURE') and ts:
            p.append('FILE %s in state %s has TEST lines' % (name, state))
        if state != 'COMPLETED':
            if tnr != 0 or nraf:
                p.append('FILE %s not COMPLETED but tests_not_run or NOT_RUN_AFTER_FAILURE' % name)
            continue
        for key, val in (('tests', tests), ('passed', passed), ('failed', failed), ('errors', errors), ('skipped', skipped)):
            tot[key] += val
        if failed + errors > 0:
            failing_completed.append(name)
        if tnr != len(nraf):
            p.append('FILE %s tests_not_run differs from its NOT_RUN_AFTER_FAILURE lines' % name)
        if nraf:
            if f['mode'] != 'failfast' or failed + errors != 1 or not ran or ran[-1][1] not in ('FAIL', 'ERROR'):
                p.append('FILE %s stopped early without exactly one last failure in mode=failfast' % name)
            if set(nraf) & {i for i, _ in ran}:
                p.append('FILE %s ran and not-run ids overlap' % name)
        if pins is not None:
            pin = pins.get(name)
            if pin is None:
                p.append('FILE %s is not in the pins' % name)
                continue
            if fsha != pin['sha256']:
                p.append('FILE %s file_sha256 differs from the pin' % name)
            observed = [i for i, _ in ran] + nraf
            if sorted(observed) != sorted(pin['ids']) or len(set(observed)) != len(observed):
                p.append('FILE %s test ids differ from the pinned inventory' % name)
    for key in tot:
        if f[key] != tot[key]:
            p.append('%s=%d but the COMPLETED files sum to %d' % (key, f[key], tot[key]))
    if f['files_skipped_after_failure']:
        started = [x for x in files if x[1] in ('COMPLETED', 'INDETERMINATE', 'ITEM_ERROR')]
        if len(failing_completed) != 1 or not started or started[-1][0] != failing_completed[0]:
            p.append('SKIPPED_AFTER_FAILURE needs exactly one failing COMPLETED file, the last started')
        first_skip = next(i for i, x in enumerate(files) if x[1] == 'SKIPPED_AFTER_FAILURE')
        if any(x[1] in ('COMPLETED', 'INDETERMINATE', 'ITEM_ERROR') for x in files[first_skip:]):
            p.append('a file started after a SKIPPED_AFTER_FAILURE file')
    if pins is not None:
        inv = sha256_lines(['%s::%s' % (n, t) for n in names for t in pins.get(n, {'ids': []})['ids']])
        if f['inventory_sha256'] != inv:
            p.append('inventory_sha256 differs from the pinned inventory of the selected files')
    return p


# ---------------------------------------------------------------------------------------------------------------------------------------
# Corrective pass 2, section P (paper 23d2adb9…f0ea5 as amended by amendment 1 211971…d382): one process model for every child.
# P.2 containment (the child subreaper; descriptors 0, 1, 2 only, 0 on /dev/null (AM-4); the environment allowlist), P.3 identity and
# membership by (pid, start time), P.4 one wait owner per child (the register, its lock, the Popen hook of AM-5 (a)), P.5 one cleanup
# contract, P.6 leak classification, P.7 nesting, P.8 when an outcome is fixed (AM-6 (b): the forked message and its bounded drain), and
# F.2's cancellation.  Containment covers every descendant of a unit; a process an outside service starts is not a descendant and is
# not contained (AM-1, open finding 11).  BUILDER-EXECUTED: NOT INDEPENDENT.
# ---------------------------------------------------------------------------------------------------------------------------------------
import json as _json
import signal as _signal
import struct as _struct
import subprocess as _subprocess
import threading as _threading
import time as _time

T_EXIT_AFTER_RESULT = 2      # P.5: a forked unit's direct child may take this long to exit after its message (AM-6 (b): and the drain)
T_GRACE = 10                 # P.5: the SIGTERM grace for a supervisor's own units, in ordinary cleanup
T_GRACE_CANCELLED = 2        # P.5: the grace when the supervisor is itself cleaning up because it was cancelled by a signal (F.2)
T_ESCALATE = 10              # P.5, P.7: for a unit whose child is a nested supervisor, before its whole remaining tree is killed
T_KILL_VERIFY = 5            # P.5: after SIGKILL, how long the scans wait for the members to be gone
FAULT_ITEM_TIMEOUT_S = 300   # B.2: per plant and per control
CASE_ITEM_TIMEOUT_S = 300    # K.2: per case
SCAN_INTERVAL_S = 0.1        # P.5 step 4: the re-scan interval
CANCEL_POLL_S = 0.2          # F.2: every wait on a child sees the cancellation flag at least this often
FORK_MESSAGE_MAX = 1024 * 1024   # P.8: the 1 MiB framing limit
CHILD_ERROR_EXIT = 70        # B.1, K.2: reserved for a forked child whose own message could not be written
_LIBC = 'libc.so.6'
_PR_SET_CHILD_SUBREAPER = 36
_PR_GET_CHILD_SUBREAPER = 37
_pidfd_open = getattr(os, 'pidfd_open', None)
_pidfd_send_signal = getattr(_signal, 'pidfd_send_signal', None)

# AM-6 (c): the 71 supervisors (each counted once) and the 3 leaves.  child_unittest_runner is a supervisor whenever it verifies an
# AUIF copy (AM-2); it is listed here because a unit whose child is child_unittest_runner is given a supervisor unit's escalation.
WRAPPER_STEMS = ('run_f671_all_s1', 'run_f672_all_s1', 'run_f673_all_s1', 'run_f674_all_s1', 'run_f67_all_s1', 'run_m3_all_s1',
                 'run_m4_all_s1', 'run_m6_all_s1', 'run_m71_all_s1', 'run_m72_all_s1', 'run_m73_all_s1', 'run_m7_all_s1', 'run_m8_all_s1',
                 'run_m91_all_s1', 'run_m92_all_s1', 'run_m93_all_s1', 'run_m94_all_s1', 'run_mie1_1_all_s1', 'run_mie1_all_s1')
MUTATION_MAIN_STEMS = ('f671_mutants_s1', 'f672_mutants_s1', 'f673_mutants_s1', 'f674_mutants_s1', 'f67_mutants_s1', 'm2_mutants_s1',
                       'm3_mutants_s1', 'm4_mutants_s1', 'm5_mutants_s1', 'm6_mutants_s1', 'm73_store_mutants_s1', 'm7_mutants_s1',
                       'm8_mutants_s1', 'm91_mutants_s1', 'mie11_mutants_s1', 'mie_mutants_s1', 'sabotage_m10_s1', 'sabotage_m8_s1')
REGRESSION_SABOTAGE_STEMS = ('sabotage_f671_s1', 'sabotage_f672_s1', 'sabotage_f673_s1', 'sabotage_f674_s1', 'sabotage_f67_s1',
                             'sabotage_m71_s1', 'sabotage_m72_s1', 'sabotage_m73_s1', 'sabotage_m7_s1')
MIE_SABOTAGE_STEMS = ('sabotage_mie1_1_s1', 'sabotage_mie1_s1')
FAULT_RUNNER_STEMS = ('run_faults_s1', 'run_history_contract_s1', 'run_m3_faults_s1', 'run_m5_faults_s1', 'run_m6_faults_s1')
CASE_RUNNER_STEMS = ('run_contracts_s1', 'run_det_corpus_s1', 'run_fin_corpus_s1', 'run_guard_contract_s1', 'run_ingest_corpus_s1',
                     'run_m3_contracts_s1', 'run_m5_contracts_s1', 'run_m6_contracts_s1', 'run_m91_contracts_s1', 'run_mkt_corpus_s1')
REGRESSION_SUCCESSOR_STEMS = ('run_regression_m10_s1', 'run_regression_m81_s1', 'run_regression_m81r1_s1', 'run_regression_m8_s1',
                              'run_regression_m8r2_s1')
SUPERVISOR_STEMS = (WRAPPER_STEMS + MUTATION_MAIN_STEMS + REGRESSION_SABOTAGE_STEMS + MIE_SABOTAGE_STEMS + FAULT_RUNNER_STEMS
                    + CASE_RUNNER_STEMS + ('run_m8_tests_s1', 'child_unittest_runner') + REGRESSION_SUCCESSOR_STEMS
                    + ('run_cr02_reference_s1',))
LEAF_STEMS = ('run_m2_tests_s1', 'mut_runner_s1', 'run_test_files_s1')


def limit_line(item_s=None):
    """P.5: the time values in force, printed by every supervisor beside its SELECTED line (or at start), with its item limit."""
    head = 'LIMIT' + ('' if item_s is None else ' item=%ss' % item_s)
    return head + ' exit_after_result=%ds grace=%ds grace_cancelled=%ds escalate=%ds kill_verify=%ds' % (
        T_EXIT_AFTER_RESULT, T_GRACE, T_GRACE_CANCELLED, T_ESCALATE, T_KILL_VERIFY)


def proc_stat(pid):
    """P.3: (state, ppid, start time) from /proc/<pid>/stat, or None.  The fields are counted after the LAST ')' of the line, because the
    command name in field 2 can hold spaces and parentheses: after it come field 3 (state), field 4 (ppid) ... field 22 (start time)."""
    try:
        with open('/proc/%d/stat' % pid, 'rb') as fh:
            data = fh.read()
    except OSError:
        return None
    i = data.rfind(b')')
    if i < 0:
        return None
    rest = data[i + 1:].split()
    try:
        return rest[0].decode('ascii'), int(rest[1]), int(rest[19])
    except (IndexError, ValueError, UnicodeDecodeError):
        return None


def proc_table():
    """One read of /proc: pid -> (state, ppid, start time)."""
    out = {}
    for name in os.listdir('/proc'):
        if name.isdigit():
            st = proc_stat(int(name))
            if st is not None:
                out[int(name)] = st
    return out


def _ident_text(idents):
    return ','.join('%d:%d' % i for i in sorted(idents)) or '-'


class _Reg:
    """One registered direct child (P.4): its identity, a pidfd on it, its owner, and its wait owner (a Popen, or a fork handle)."""
    __slots__ = ('pid', 'start', 'pidfd', 'owner', 'popen', 'status')

    def __init__(self, pid, start, pidfd, owner, popen):
        self.pid, self.start, self.pidfd, self.owner, self.popen, self.status = pid, start, pidfd, owner, popen, None

    def reaped(self):
        return (self.popen.returncode is not None) if self.popen is not None else (self.status is not None)


class _Owner:
    """What a child is attributed to (P.3, AM-5 (c)): a unit started under P (a subprocess or a forked child), or a phase or step of a
    run inside which in-process code starts children (the run's start or end, a test file in child_unittest_runner, a regression step)."""

    def __init__(self, sup, uid, kind, nested=False):
        self.id, self.kind, self.nested = uid, kind, nested
        sup.seq += 1
        self.seq = sup.seq
        self.direct = []          # its registered direct children (_Reg)
        self.members = {}         # every identity ever seen as a member -> its parent's identity
        self.ambiguous = {}       # identities whose only link was an equal-start-time parent that is not a direct child
        self.first_scan = self.last_scan = None
        self.leaked = False
        self.conservative = set()  # amendment 5, S15: orphans with no recorded parent, attributed to this owner conservatively (P.3)
        self.remaining = ()
        self.record = None


class _Supervision:
    """The process-wide supervision state: one per process (shared by every copy of evkit loaded into it, through the subprocess
    module), created when tools.evkit is imported (AM-5 (a))."""

    def __init__(self):
        self.lock = _threading.RLock()
        self.pid = os.getpid()
        self.local = _threading.local()
        self.regs = {}            # pid -> _Reg: the register of direct children
        self.owners = []          # every owner of this run, in creation order
        self.in_flight = []       # owners whose cleanup is not complete
        self.adopted = {}         # identity -> [owners]: adopted orphans and their attribution
        self.reaped_orphans = set()
        self.scan_id = 0
        self.seq = 0
        self.errors = []          # RunError lines P adds (CLEANUP_INCOMPLETE, PROCESSES_LEFT)
        self.problem = None       # why supervision is unavailable (P.2), or None
        self.supervisor = False   # this process supervises units (P.1); a leaf only reaps exited orphans before its RESULT line
        self.run_without_result = False   # a run whose output has no RESULT line (AM2-2's 6 supervisors, --baseline)
        self.tool = None
        self._default = None
        self.table = proc_table   # replaceable by the tests that simulate pid reuse and equal start times (P.10)
        self.send = None          # likewise; None means _send_pidfd

    def reset(self):
        """For the in-process tests only: forget the owners and records of earlier runs in this process."""
        with self.lock:
            self.owners, self.in_flight, self.adopted, self.errors = [], [], {}, []
            self.reaped_orphans = set()
            self._default = None

    # ---- the register (P.4) ----------------------------------------------------------------------------------------------------------
    def current_owner(self):
        o = getattr(self.local, 'owner', None)
        if o is not None:
            return o
        if self._default is None:
            self._default = _Owner(self, 'run_end', 'phase')
            self.owners.append(self._default)
        return self._default

    def register(self, pid, popen=None, owner=None):
        """Called with the lock held, at creation, before the lock is released (P.4, AM-5 (a))."""
        for old_pid, old in list(self.regs.items()):     # entries whose wait owner has collected the child are dropped (and their pidfd)
            if old.reaped():
                if old.pidfd is not None:
                    try:
                        os.close(old.pidfd)
                    except OSError:
                        pass
                    old.pidfd = None
                del self.regs[old_pid]
        st = proc_stat(pid)
        try:
            fd = _pidfd_open(pid) if _pidfd_open else None
        except OSError:
            fd = None
        o = owner or self.current_owner()
        r = _Reg(pid, st[2] if st else None, fd, o, popen)
        self.regs[pid] = r
        o.direct.append(r)
        if r.start is not None:
            o.members[(pid, r.start)] = (self.pid, None)
        if o not in self.in_flight and o is not self._default:
            self.in_flight.append(o)
        return r

    def new_owner(self, uid, kind, nested=False):
        with self.lock:
            o = _Owner(self, uid, kind, nested)
            self.owners.append(o)
            self.in_flight.append(o)
            return o

    def _is_direct(self, ident):
        r = self.regs.get(ident[0])
        return r is not None and r.start == ident[1]

    # ---- one scan: the reaper, then each owner's members (P.3, P.4) -------------------------------------------------------------------
    def scan(self, owners=(), reap=True):
        """Under the lock: read /proc; register every adopted child of this process (alive or zombie) with its attribution and reap
        the adopted zombies (only by WNOHANG on that pid); then compute each given owner's live members.  Returns {owner: set(idents)}."""
        with self.lock:
            self.scan_id += 1
            # the reaped registrations are pruned BEFORE the table is read (corrective pass 2, mistake 29): a direct child's own handle
            # waits without this lock, so a child reaped between a table read and the pruning would still be a zombie in that table but
            # no longer registered, and would be taken for an adopted orphan (P.4: the reaper never sees an unregistered direct child)
            for pid, r in list(self.regs.items()):
                if r.reaped():
                    if r.pidfd is not None:
                        try:
                            os.close(r.pidfd)
                        except OSError:
                            pass
                        r.pidfd = None
                    del self.regs[pid]
            tab = self.table()
            me = self.pid
            for pid, (state, ppid, start) in (tab.items() if reap else ()):
                if ppid != me or self._is_direct((pid, start)):
                    continue
                ident = (pid, start)
                if ident in self.reaped_orphans:
                    continue
                if ident not in self.adopted:
                    who = [o for o in self.owners if ident in o.members]
                    conservative = not who
                    if conservative:      # created and orphaned between two scans: attributed to every unit in flight (P.3)
                        who = list(self.in_flight) or [self.current_owner()]
                    for o in who:
                        o.members.setdefault(ident, (me, None))
                        if conservative:
                            # amendment 5, S15 (owner, 2026-11-08 12:47, option A): each owner it is attributed to records it as a
                            # leak (P.6) and names it in its CLEANUP record, even when it has exited before that owner's cleanup
                            o.conservative.add(ident)
                            o.leaked = True
                    self.adopted[ident] = who
                if state == 'Z':
                    try:
                        rpid, _ = os.waitpid(pid, os.WNOHANG)
                    except ChildProcessError:
                        rpid = pid
                    if rpid == pid:
                        self.reaped_orphans.add(ident)
            out = {}
            for o in owners:
                out[o] = self._members(o, tab)
            return out

    def _members(self, o, tab):
        present = {i for i in o.members if i[0] in tab and tab[i[0]][2] == i[1]}
        kids = {}
        for pid, (_, ppid, _s) in tab.items():
            kids.setdefault(ppid, []).append(pid)
        frontier = list(present)
        while frontier:
            par = frontier.pop()
            for c in kids.get(par[0], ()):
                ci = (c, tab[c][2])
                if ci in present:
                    continue
                if par[1] > ci[1]:
                    continue           # the parent started after the child: a reused pid, never a link (P.3)
                if par[1] == ci[1] and not self._is_direct(par):
                    o.ambiguous[ci] = par
                    continue           # ambiguous: not proven membership, never signalled on this link alone (P.3)
                o.members[ci] = par
                present.add(ci)
                frontier.append(ci)
        if o.first_scan is None:
            o.first_scan = self.scan_id
        o.last_scan = self.scan_id
        return {i for i in present if tab[i[0]][0] != 'Z'}

    # ---- signalling (P.3) ------------------------------------------------------------------------------------------------------------
    def signal(self, ident, sig):
        fn = self.send or _send_pidfd
        return fn(ident, sig)

    # ---- the cleanup contract (P.5) --------------------------------------------------------------------------------------------------
    def cleanup(self, o, reap_direct=None, direct=None):
        """P.5 steps 2 to 8 for one owner.  direct: the identity of the unit's direct child (for a nested supervisor's escalation).
        Returns True when the owner had members alive at step 3, or (amendment 5, S15) a conservatively attributed orphan: a leak, P.6."""
        reap = reap_direct or (lambda: None)
        cancelled = CANCEL.cancelled()
        grace = T_ESCALATE if o.nested else (T_GRACE_CANCELLED if cancelled else T_GRACE)
        reap()
        live = self.scan([o])[o]
        first = self.scan_id
        left = set(live)
        seen = set(live)
        termed, killed = set(), set()
        nterm = nkill = 0
        scans = 1
        deadline = 'none'
        t0 = _time.monotonic()
        escalated = None

        def term(idents):
            nonlocal nterm
            for i in sorted(idents - termed):
                # a nested supervisor is stopped through its own child (P.7): its units are its own to clean up while it lives
                if o.nested and direct is not None and direct in live and i != direct:
                    continue
                termed.add(i)
                if self.signal(i, _signal.SIGTERM):
                    nterm += 1
        if live:      # S15: the signal steps run only when a member is alive; a conservatively attributed orphan alone is recorded
            o.leaked = True
            term(live)
            end = t0 + grace
            empty = 0
            while True:
                _time.sleep(SCAN_INTERVAL_S)
                reap()
                live = self.scan([o])[o]
                scans += 1
                seen |= live
                if not live:
                    empty += 1
                    if empty >= 2:
                        break
                    continue
                empty = 0
                term(live)
                if _time.monotonic() >= end:
                    deadline = 'grace'
                    break
        if live:
            escalated = _time.monotonic() - t0
            kend = _time.monotonic() + T_KILL_VERIFY
            for i in sorted(live):
                killed.add(i)
                if self.signal(i, _signal.SIGKILL):
                    nkill += 1
            empty = 0
            while True:
                _time.sleep(SCAN_INTERVAL_S)
                reap()
                live = self.scan([o])[o]
                scans += 1
                seen |= live
                if not live:
                    empty += 1
                    if empty >= 2:
                        break
                    continue
                empty = 0
                for i in sorted(live - killed):
                    killed.add(i)
                    if self.signal(i, _signal.SIGKILL):
                        nkill += 1
                if _time.monotonic() >= kend:
                    deadline = 'kill_verify'
                    break
        elif o.nested and left:
            escalated = _time.monotonic() - t0
        o.remaining = tuple(sorted(live))
        last, ambiguous = self.scan_id, _ident_text(o.ambiguous)     # S15: the record's scan range and ambiguous set, before step 6
        self._settle(o, reap)
        if not left and not o.conservative:
            return False
        o.leaked = True
        child = next(((r.pid, r.start) for r in o.direct), None)
        o.record = ('CLEANUP %s by=%s:%d child=%s pgid=%s scan=%d-%d left=%s exited_in_grace=%s killed=%s sigterm=%d sigkill=%d '
                    'scans=%d deadline=%s escalated_after=%s ambiguous=%s remaining=%s' % (
                        o.id, self.tool or 'evkit', self.pid, '%d:%d' % child if child else '-',
                        child[0] if (child and o.kind == 'unit') else '-',
                        first, last, _ident_text(left | o.conservative), _ident_text(seen - killed), _ident_text(killed), nterm, nkill,
                        scans, deadline, ('%.1fs' % escalated) if (o.nested and escalated is not None) else '-', ambiguous,
                        _ident_text(live)))
        if live:
            self.errors.append(RunError('CLEANUP_INCOMPLETE', '%s %s' % (o.id, _ident_text(live))))
        return True

    def _settle(self, o, reap):
        """P.5 step 6: the direct child reaped by its owner, the adopted orphans by the reaper; then the owner is no longer in flight."""
        reap()
        if any(not r.reaped() for r in o.direct) or any(i not in self.reaped_orphans and i in self.adopted
                                                          for i in o.members if i not in o.remaining):
            t_end = _time.monotonic() + T_KILL_VERIFY
            while _time.monotonic() < t_end:
                reap()
                self.scan([o])
                if all(r.reaped() for r in o.direct) and all(i in self.reaped_orphans or i not in self.adopted or i in o.remaining
                                                             for i in o.members):
                    break
                _time.sleep(SCAN_INTERVAL_S)
        with self.lock:
            if o in self.in_flight:
                self.in_flight.remove(o)

    # ---- the records (P.5 step 8) ----------------------------------------------------------------------------------------------------
    def final_lines(self):
        """The CLEANUP, CLEANUP_AMBIGUOUS and CLEANUP_SUMMARY lines, in the order of the units' ids (their creation order)."""
        if not self.supervisor:
            return []
        out = []
        for o in sorted(self.owners, key=lambda x: x.seq):
            if o.record:
                out.append(o.record)
            elif o.ambiguous:
                for ci, par in sorted(o.ambiguous.items()):
                    out.append('CLEANUP_AMBIGUOUS %d:%d parent=%d:%d' % (ci + par))
        units = [o for o in self.owners if o.kind == 'unit' or o.direct or o.record]
        out.append('CLEANUP_SUMMARY units=%d leaked=%d remaining=%d' % (
            len(units), sum(1 for o in self.owners if o.leaked), sum(len(o.remaining) for o in self.owners)))
        return out

    def close_run(self):
        """Before the RESULT line (P.5 step 9): sweep what no unit or phase owns (attributed to the run's end), and return the run
        errors P added.  A leaf instead reaps, by WNOHANG on each pid, the adopted orphans that have already exited (AM-5 (a))."""
        if not self.supervisor:
            self.reap_exited_orphans()
            return []
        d = self._default
        if d is not None and d in self.owners:
            if self.cleanup(d, reap_direct=lambda: _poll_popens(d)):
                self.errors.append(RunError('PROCESSES_LEFT', 'run_end'))
        errs, self.errors = self.errors, []
        return errs

    def reap_exited_orphans(self):
        with self.lock:
            tab = self.table()
            for pid, (state, ppid, start) in tab.items():
                if ppid == self.pid and state == 'Z' and not self._is_direct((pid, start)):
                    try:
                        os.waitpid(pid, os.WNOHANG)
                    except ChildProcessError:
                        pass


def _poll_popens(o):
    for r in o.direct:
        if r.popen is not None and r.popen.returncode is None:
            try:
                r.popen.poll()
            except Exception:
                pass


def _send_pidfd(ident, sig):
    """P.3: open a pidfd, re-check the start time, then signal through the pidfd.  A reused pid never receives the signal."""
    pid, start = ident
    try:
        fd = _pidfd_open(pid)
    except OSError:
        return False
    try:
        st = proc_stat(pid)
        if st is None or st[2] != start or st[0] == 'Z':
            return False
        _pidfd_send_signal(fd, sig)
        return True
    except OSError:
        return False
    finally:
        os.close(fd)


# ---- the process-wide state and the Popen hook (AM-5 (a)), installed when tools.evkit is imported ---------------------------------------
_SUP = getattr(_subprocess, '_apg_supervision', None)
if _SUP is None or _SUP.pid != os.getpid():
    _SUP = _Supervision()
    _subprocess._apg_supervision = _SUP


def _install_hook():
    real = _subprocess.Popen.__init__
    if getattr(real, '_apg_child_register', False):
        return

    def child_register(self, *args, **kwargs):
        sup = _subprocess._apg_supervision
        if os.getpid() != sup.pid:     # a forked child (B, K.2) never uses the register or its lock (P.2)
            return real(self, *args, **kwargs)
        with sup.lock:
            real(self, *args, **kwargs)
            sup.register(self.pid, popen=self)
    child_register._apg_child_register = True
    child_register._apg_real = real
    _subprocess.Popen.__init__ = child_register


def _install_subreaper():
    """P.2: mark this process a child subreaper and read it back; set SIGCHLD to SIG_DFL and read it back.  A failure is recorded and
    a supervisor refuses at its start (ENV_NO_PROCESS_SUPERVISION)."""
    try:
        if not os.path.isfile('/proc/self/stat'):
            return 'proc_unavailable'
        if _pidfd_open is None or _pidfd_send_signal is None:
            return 'pidfd_unavailable'
        try:
            os.close(_pidfd_open(os.getpid()))
        except OSError as e:
            return 'pidfd_open_failed_%s' % type(e).__name__
        import ctypes
        libc = ctypes.CDLL(_LIBC, use_errno=True)
        if libc.prctl(_PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0:
            return 'prctl_set_failed_errno_%d' % ctypes.get_errno()
        v = ctypes.c_int(0)
        if libc.prctl(_PR_GET_CHILD_SUBREAPER, ctypes.byref(v), 0, 0, 0) != 0 or v.value != 1:
            return 'prctl_readback_failed'
        if _threading.current_thread() is _threading.main_thread():
            _signal.signal(_signal.SIGCHLD, _signal.SIG_DFL)
        if _signal.getsignal(_signal.SIGCHLD) != _signal.SIG_DFL:
            return 'sigchld_not_default'
        return None
    except Exception as e:
        return 'unavailable_%s' % type(e).__name__


def is_subreaper():
    try:
        import ctypes
        v = ctypes.c_int(0)
        ctypes.CDLL(_LIBC, use_errno=True).prctl(_PR_GET_CHILD_SUBREAPER, ctypes.byref(v), 0, 0, 0)
        return v.value == 1
    except Exception:
        return False


def supervision_errors():
    """P.2: the refusal a supervisor makes at its start when containment cannot be set up (SIGCHLD is checked again here)."""
    p = _SUP.problem
    if p is None:
        try:
            if _signal.getsignal(_signal.SIGCHLD) != _signal.SIG_DFL:
                _signal.signal(_signal.SIGCHLD, _signal.SIG_DFL)
            if _signal.getsignal(_signal.SIGCHLD) != _signal.SIG_DFL:
                p = 'sigchld_not_default'
        except (ValueError, OSError):
            p = 'sigchld_not_default'
    return [RunError('ENV_NO_PROCESS_SUPERVISION', p)] if p else []


def declare_supervisor(tool):
    _SUP.supervisor = True
    _SUP.tool = tool


# ---- F.2: cancellation ---------------------------------------------------------------------------------------------------------------
class _Cancel:
    """F.2 (a): one cancellation mechanism.  The handler only records the signal and sets the flag; a further signal adds 1 to a
    count.  It does no output and no cleanup.  done: the run's last unit's outcome has been fixed (P.8)."""

    def __init__(self):
        self.set = False
        self.signal = None
        self.at = None
        self.received = 0
        self.phase = 'between'
        self.done = False
        self.after_done = False
        self.installed = False

    def handler(self, signum, frame):
        self.received += 1
        if not self.set:
            self.signal = _signal.Signals(signum).name
            self.at = self.phase
            self.after_done = self.done
            self.set = True

    def install(self):
        if self.installed or _threading.current_thread() is not _threading.main_thread():
            return
        _signal.signal(_signal.SIGINT, self.handler)
        _signal.signal(_signal.SIGTERM, self.handler)
        self.installed = True

    def cancelled(self):
        """The run was cancelled before its last unit's outcome was fixed."""
        return self.set and not self.after_done

    def fix(self, last=False):
        """Called at the moment a unit's outcome is fixed (P.8).  False when a signal came first: the unit is interrupted.  For the
        run's last unit, done is set first, so a signal is either before it (interrupted) or after it (SIGNAL_AFTER_COMPLETION)."""
        if last:
            self.done = True
        if self.set and not self.after_done:
            if last:
                self.done = False
            return False
        return True

    def nothing_cut(self):
        """A tests runner (leaf, or child_unittest_runner) whose every selected test ran in full although a signal came: no work was
        cut, so the run is complete and the signal is recorded as SIGNAL_AFTER_COMPLETION (an in-process test cannot be stopped)."""
        if self.set:
            self.after_done = True

    def record(self):
        """The line before the RESULT line: INTERRUPTED, SIGNAL_AFTER_COMPLETION, or nothing."""
        if not self.set:
            return None
        if self.after_done:
            return 'SIGNAL_AFTER_COMPLETION signal=%s' % self.signal
        return 'INTERRUPTED signal=%s at=%s received=%d' % (self.signal, self.at, self.received)


CANCEL = getattr(_subprocess, '_apg_cancel', None)
if CANCEL is None or _SUP.pid != getattr(CANCEL, '_pid', None):
    CANCEL = _Cancel()
    CANCEL._pid = os.getpid()
    _subprocess._apg_cancel = CANCEL


def set_phase(phase):
    CANCEL.phase = phase


# ---- a subprocess unit (P.1 to P.8) --------------------------------------------------------------------------------------------------
def _cmd_stem(cmd):
    script = next((a for a in cmd if isinstance(a, str) and a.endswith('.py')), None)
    return os.path.basename(script)[:-3] if script else None


def is_supervisor_cmd(cmd):
    """P.7: a supervisor knows from the command it starts whether the unit's child is a nested supervisor."""
    return _cmd_stem(cmd) in SUPERVISOR_STEMS


class UnitResult:
    __slots__ = ('how', 'returncode', 'stdout', 'stderr', 'seconds', 'leaked')

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


def _decode(data):
    """The child's output decoded exactly as subprocess.run(text=True) decodes it (the locale encoding, universal newlines)."""
    import io
    return io.TextIOWrapper(io.BytesIO(data)).read()


def _pump(bufs, open_fds, timeout):
    """Read what is available on the open pipes, for up to timeout seconds.  bufs: {fd: [chunks]}; open_fds: the fds not yet at end of
    file (an fd at end of file is removed from it; the file object that owns it closes it later)."""
    import select
    fds = sorted(open_fds)
    if not fds:
        if timeout > 0:
            _time.sleep(timeout)
        return
    r, _, _ = select.select(fds, [], [], max(0.0, timeout))
    for fd in r:
        try:
            chunk = os.read(fd, 65536)
        except OSError:
            chunk = b''
        if chunk:
            bufs[fd].append(chunk)
        else:
            open_fds.discard(fd)


def run_unit(uid, cmd, timeout, env, cwd, stop=None, last=False):
    """Start one subprocess unit under P and see it to its end.  The child: stdin /dev/null (AM-4), stdout and stderr to pipes,
    close_fds, the given environment (the allowlist), its own process group; created through the Popen hook (registered under the
    lock, P.4).  The wait polls every CANCEL_POLL_S at most for the deadline, the cancellation flag (F.2) and stop() (F.1).
    P.8: the outcome is fixed when the child has exited and its output is in (the pipes drained for at most T_EXIT_AFTER_RESULT; a
    member still holding them is found by the scan that follows); a signal before that moment makes the unit interrupted.  last: this
    unit is the run's last unit (fixing it marks the run done, F.2); a callable last(returncode, stdout) decides it at that moment.  Cleanup (P.5) always follows; P.6's verdict is leaked.
    Returns a UnitResult: how is 'exit', 'timeout', 'interrupted', 'stopped' or 'launch_error'."""
    o = _SUP.new_owner(uid, 'unit', nested=is_supervisor_cmd(cmd))
    t0 = _time.monotonic()
    prev = getattr(_SUP.local, 'owner', None)
    _SUP.local.owner = o
    try:
        p = _subprocess.Popen(cmd, cwd=cwd, env=env, stdin=_subprocess.DEVNULL, stdout=_subprocess.PIPE, stderr=_subprocess.PIPE,
                              close_fds=True, process_group=0)
    except OSError as e:
        with _SUP.lock:
            if o in _SUP.in_flight:
                _SUP.in_flight.remove(o)
        return UnitResult(how='launch_error', returncode=None, stdout='', stderr=str(e), seconds=_time.monotonic() - t0,
                          leaked=False)
    finally:
        _SUP.local.owner = prev
    direct = (p.pid, o.direct[0].start) if o.direct else None
    out_fd, err_fd = p.stdout.fileno(), p.stderr.fileno()
    bufs = {out_fd: [], err_fd: []}
    open_fds = {out_fd, err_fd}
    deadline = t0 + timeout if timeout is not None else None
    how = None
    while how is None:
        wait = CANCEL_POLL_S if deadline is None else max(0.0, min(CANCEL_POLL_S, deadline - _time.monotonic()))
        _pump(bufs, open_fds, wait)
        if p.poll() is not None:
            how = 'exit'
        elif deadline is not None and _time.monotonic() >= deadline:
            how = 'timeout'
        elif CANCEL.set:
            how = 'interrupted'
        elif stop is not None and stop():
            how = 'stopped'
    if how == 'exit':
        t_end = _time.monotonic() + T_EXIT_AFTER_RESULT
        while open_fds and _time.monotonic() < t_end:
            _pump(bufs, open_fds, min(CANCEL_POLL_S, max(0.0, t_end - _time.monotonic())))
        is_last = last(p.returncode, _decode(b''.join(bufs[out_fd]))) if callable(last) else last
        if not CANCEL.fix(last=is_last):
            how = 'interrupted'
    elif how == 'timeout':      # the deadline fixes a timeout outcome (B.4: TIMEOUT is a completed control outcome)
        if not CANCEL.fix(last=last(None, None) if callable(last) else last):
            how = 'interrupted'
    leaked = _SUP.cleanup(o, reap_direct=p.poll, direct=direct)
    t_end = _time.monotonic() + T_KILL_VERIFY
    while open_fds and _time.monotonic() < t_end:
        _pump(bufs, open_fds, CANCEL_POLL_S)
    for f in (p.stdout, p.stderr):
        try:
            f.close()
        except OSError:
            pass
    return UnitResult(how=how, returncode=p.returncode, stdout=_decode(b''.join(bufs[out_fd])), stderr=_decode(b''.join(bufs[err_fd])),
                      seconds=_time.monotonic() - t0, leaked=leaked)


# ---- a forked unit (B, K.2; P.8 as amended by AM-6 (b)) --------------------------------------------------------------------------------
def fork_threads_ok():
    """AM-6 (a): immediately before each fork, one Python thread and exactly one entry in /proc/self/task."""
    try:
        return _threading.active_count() == 1 and len(os.listdir('/proc/self/task')) == 1
    except OSError:
        return False


def _write_all(fd, data):
    view = memoryview(data)
    while view:
        n = os.write(fd, view)
        view = view[n:]


def _frame(obj):
    data = _json.dumps(obj).encode('utf-8')
    return _struct.pack('>I', len(data)) + data


def run_forked(uid, fn, timeout, env, last=False, on_end=None):
    """One forked unit.  The child (P.2): its own process group; every descriptor closed but 0, 1, 2 and its pipe's write end; 0 on
    /dev/null (AM-4); its environment replaced by env; SIGINT and SIGTERM to their defaults; then fn() -> a JSON-able message, written
    as a 4-byte big-endian length and exactly that many bytes; an exception escaping fn is {"exception": "<type>"}; a failure to encode
    or write is caught and {"child_error": "<type>"} tried once, else os._exit(70) (B.1).
    The parent (AM-6 (b)): reads the length and the message within the limit, then drains without blocking until end of file or
    T_EXIT_AFTER_RESULT after the message completed; then polls the child's exit for up to T_EXIT_AFTER_RESULT; then cleans up (P.5).
    Returns a dict: how ('message', 'eof', 'timeout', 'interrupted', 'too_long'), message (bytes or None), trailing (bool), status (the
    wait status, or None), leaked (bool).  Raises RunError ENV_THREADS_AT_FORK when the process is not single-threaded.
    on_end(): called when the unit's outcome is about to be fixed, before the fix is decided (F.2's phase moves first, reading 6)."""
    if not fork_threads_ok():
        raise RunError('ENV_THREADS_AT_FORK', 'threads=%d' % _threading.active_count())
    o = _SUP.new_owner(uid, 'unit')
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    r, w = os.pipe()
    t0 = _time.monotonic()
    with _SUP.lock:
        pid = os.fork()
        if pid == 0:
            code = 0
            try:
                os.setpgid(0, 0)
                os.close(r)
                fd0 = os.open(os.devnull, os.O_RDONLY)
                if fd0 != 0:
                    os.dup2(fd0, 0)
                    os.close(fd0)
                os.closerange(3, w)
                os.closerange(w + 1, max(w + 2, os.sysconf('SC_OPEN_MAX')))
                os.environ.clear()
                os.environ.update(env)
                for s in (_signal.SIGINT, _signal.SIGTERM):
                    _signal.signal(s, _signal.SIG_DFL)
                try:
                    msg = fn()
                except BaseException as e:
                    msg = {'exception': type(e).__name__}
                try:
                    _write_all(w, _frame(msg))
                except BaseException as e:
                    try:
                        _write_all(w, _frame({'child_error': type(e).__name__}))
                    except BaseException:
                        code = CHILD_ERROR_EXIT
            except BaseException:
                code = CHILD_ERROR_EXIT
            finally:
                try:
                    sys.stdout.flush()
                    sys.stderr.flush()
                except BaseException:
                    pass
                os._exit(code)
        reg = _SUP.register(pid, owner=o)
    os.close(w)
    direct = (pid, reg.start)

    def reap():
        if reg.status is None:
            try:
                rp, st = os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                rp, st = pid, -1
            if rp == pid:
                reg.status = st
    deadline = t0 + timeout
    buf = b''
    need = 4
    how = None
    complete_at = None
    msg = None
    trailing = False
    eof = False
    import select
    while how is None:
        left = deadline - _time.monotonic()
        if left <= 0:
            how = 'timeout'
            if on_end is not None:
                on_end()
            if not CANCEL.fix(last=last):     # the deadline fixes a timeout outcome (B.4)
                how = 'interrupted'
            break
        if CANCEL.set:
            how = 'interrupted'
            break
        rr, _, _ = select.select([r], [], [], min(CANCEL_POLL_S, left))
        if not rr:
            continue
        chunk = os.read(r, 65536)
        if not chunk:
            eof = True
            how = 'eof'
            break
        buf += chunk
        if len(buf) >= 4 and need == 4:
            n = _struct.unpack('>I', buf[:4])[0]
            if n > FORK_MESSAGE_MAX:
                how = 'too_long'
                break
            need = 4 + n
        if need > 4 and len(buf) >= need:
            msg, trailing = buf[4:need], len(buf) > need
            complete_at = _time.monotonic()
            how = 'message'
    if how == 'message':
        # the drain: without blocking, until end of file or T_EXIT_AFTER_RESULT after the message completed
        while not eof and _time.monotonic() < complete_at + T_EXIT_AFTER_RESULT:
            rr, _, _ = select.select([r], [], [], max(0.0, min(CANCEL_POLL_S, complete_at + T_EXIT_AFTER_RESULT - _time.monotonic())))
            if rr:
                chunk = os.read(r, 65536)
                if chunk:
                    trailing = True
                else:
                    eof = True
        t_end = _time.monotonic() + T_EXIT_AFTER_RESULT
        reap()
        while reg.status is None and _time.monotonic() < t_end:
            _time.sleep(SCAN_INTERVAL_S / 2)
            reap()
        if on_end is not None:
            on_end()
        if not CANCEL.fix(last=last):
            how = 'interrupted'
    elif how == 'eof':
        # end of file with no complete message: the child's exit status decides crash or child_error (B.3), within the item's limit
        reap()
        while reg.status is None and _time.monotonic() < deadline and not CANCEL.set:
            _time.sleep(SCAN_INTERVAL_S / 2)
            reap()
        if reg.status is None:
            how = 'timeout' if not CANCEL.set else 'interrupted'
        if how == 'eof' and on_end is not None:
            on_end()
        if how == 'eof' and not CANCEL.fix(last=last):
            how = 'interrupted'
    elif how == 'too_long':
        if on_end is not None:
            on_end()
        if not CANCEL.fix(last=last):
            how = 'interrupted'
    try:
        os.close(r)
    except OSError:
        pass
    leaked = _SUP.cleanup(o, reap_direct=reap, direct=direct)
    return {'how': how, 'message': msg, 'trailing': trailing, 'status': reg.status, 'leaked': leaked, 'eof': eof,
            'seconds': _time.monotonic() - t0, 'pid': pid, 'start': reg.start}


def forked_exit_status(status):
    """(exit code or None, signal or None) of a wait status."""
    if status is None or status < 0:
        return None, None
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status), None
    if os.WIFSIGNALED(status):
        return None, os.WTERMSIG(status)
    return None, None


def parse_forked_message(res, forms):
    """P.8 steps 2 to 4 for a forked unit's message.  forms: {key: validator(value) -> bool}; the object must have exactly one key, one of
    forms, and its value must pass that form's validator.  Returns ('crash'|'child_error'|'bad_result'|'timeout'|'interrupted', None)
    or ('ok', (key, value))."""
    if res['how'] in ('timeout', 'interrupted'):
        return res['how'], None
    if res['how'] == 'too_long':
        return 'bad_result', None
    if res['how'] == 'eof':
        code, _sig = forked_exit_status(res['status'])
        return ('child_error', None) if code == CHILD_ERROR_EXIT else ('crash', None)
    if res['trailing']:
        return 'bad_result', None
    try:
        obj = _json.loads(res['message'].decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        return 'bad_result', None
    if not isinstance(obj, dict) or len(obj) != 1:
        return 'bad_result', None
    (key, value), = obj.items()
    if key not in forms or not forms[key](value):
        return 'bad_result', None
    return 'ok', (key, value)


# ---- in-process code that starts children (AM-5 (c)): a phase, a step or a test file owns them ------------------------------------------
class owning:
    """with owning('run_start') as o: every child the code in this block starts (in this thread) is attributed to o; at the end of the
    block o is cleaned up under P.5, and o.leaked says whether it had members alive (P.6, AM-5 (c))."""

    def __init__(self, uid):
        self.uid = uid
        self.o = None
        self.prev = None

    def __enter__(self):
        self.o = _SUP.new_owner(self.uid, 'phase')
        self.prev = getattr(_SUP.local, 'owner', None)
        _SUP.local.owner = self.o
        return self.o

    def __exit__(self, *exc):
        _SUP.local.owner = self.prev
        o = self.o
        _SUP.cleanup(o, reap_direct=lambda: _poll_popens(o))
        return False


_install_hook()
_SUP.problem = _install_subreaper()


CHILD_OUTCOMES = ('CHILD_OK', 'CHILD_FAILED', 'CHILD_EVIDENCE_ERROR', 'CHILD_INDETERMINATE', 'TIMEOUT', 'CRASH_NO_RESULT', 'LAUNCH_ERROR')


def classify_child(text, exit_code, pins=None, selected=None):
    """run_child's classification (T-0, R4) of a finished child: returns (outcome, kind, fields or None, problems)."""
    if not any(l.startswith('RESULT') for l in text.splitlines()):
        return 'CRASH_NO_RESULT', None, None, ['no RESULT line']
    problems = check_output(text, actual_exit=exit_code, pins=pins, selected=selected)
    if problems:
        return 'CHILD_EVIDENCE_ERROR', None, None, problems
    kind, f = parse_result_line([l for l in text.splitlines() if l.strip()][-1])
    if kind == 'wrapper':     # W-1 §1.9: no stage 1 tool accepts a successor wrapper as its child
        return 'CHILD_EVIDENCE_ERROR', None, None, ['wrapper child not accepted']
    return {0: 'CHILD_OK', 1: 'CHILD_FAILED', 2: 'CHILD_EVIDENCE_ERROR', 3: 'CHILD_INDETERMINATE'}[exit_code], kind, f, []


CHILD_UNIT_OUTCOMES = ('INTERRUPTED', 'STOPPED', 'PROCESSES_LEFT', 'CHILD_INTERRUPTED')   # corrective pass 2: P.6, F.1, F.2, AM2-2


def run_child(cmd, timeout, env, cwd, pins=None, selected=None, classify=None, unit=None, stop=None, last=False):
    """Run one child and classify it (T-0, R4).  Returns (outcome, stdout, stderr, seconds, kind, fields).
    classify(stdout, returncode) -> outcome: only for a check that is not a stage 1 runner (T_tooling.md T-F row F9: an M10 regression
    step, a static checker or the UI tests, which report their own result); it must return CHILD_OK or CHILD_FAILED only when the
    check's own result is recognised exactly, and CRASH_NO_RESULT otherwise.  A child killed by a signal is always CRASH_NO_RESULT.
    Corrective pass 2: the child is a unit under P (run_unit: its own process group, stdin /dev/null, the cleanup contract), named unit
    (its CLEANUP id).  Three more outcomes: INTERRUPTED (F.2, a signal before its outcome was fixed), STOPPED (F.1, stop() became true
    while it ran) and PROCESSES_LEFT (P.6: members alive after its outcome was fixed, the direct child included).  A leak on a child
    already classified CHILD_EVIDENCE_ERROR or LAUNCH_ERROR keeps that classification (an item error, the more severe result; the leak is
    on its CLEANUP line).  last: the run's last unit (F.2)."""
    r = run_unit(unit or 'child', cmd, timeout, env, cwd, stop=stop, last=last)
    if r.how == 'launch_error':
        return 'LAUNCH_ERROR', '', r.stderr, r.seconds, None, None
    if r.how == 'timeout':
        return 'TIMEOUT', r.stdout, '', r.seconds, None, None
    if r.how == 'interrupted':
        return 'INTERRUPTED', r.stdout, r.stderr, r.seconds, None, None
    if r.how == 'stopped':
        return 'STOPPED', r.stdout, r.stderr, r.seconds, None, None
    outcome, kind, fields = classify_exited(cmd, r.returncode, r.stdout, pins=pins, selected=selected, classify=classify)
    if r.leaked and outcome not in ('CHILD_EVIDENCE_ERROR', 'LAUNCH_ERROR'):
        outcome, kind, fields = 'PROCESSES_LEFT', None, None
    return outcome, r.stdout, r.stderr, r.seconds, kind, fields


INTERRUPTED_RECORD = re.compile(r'^INTERRUPTED signal=(SIGINT|SIGTERM) at=\S+ received=[1-9][0-9]*$')


def is_interrupted_child(rc, stdout):
    """Amendment 2, AM2-2 (d): an interrupted no-kind child (one of the 5 regression successors or run_cr02_reference_s1): its exit is 3
    and its last line is the INTERRUPTED record.  An exit 3 without the record is not one."""
    ls = [l for l in (stdout or '').splitlines() if l.strip()]
    return rc == 3 and bool(ls) and bool(INTERRUPTED_RECORD.match(ls[-1]))


def classify_exited(cmd, rc, stdout, pins=None, selected=None, classify=None):
    """run_child's classification of a child that exited (unchanged from the current freeze): (outcome, kind, fields).
    Amendment 2, AM2-2 (d): a no-kind child (classify given) that is an interrupted child is CHILD_INTERRUPTED, a completed child
    outcome (not a stop of the parent): an item INDETERMINATE cause=child_interrupted, a control FAIL cause=child_interrupted."""
    if classify is not None and is_interrupted_child(rc, stdout):
        return 'CHILD_INTERRUPTED', None, None
    if classify is not None:
        outcome = classify(stdout, rc) if rc >= 0 else 'CRASH_NO_RESULT'
        if outcome not in ('CHILD_OK', 'CHILD_FAILED', 'CRASH_NO_RESULT'):
            outcome = 'CRASH_NO_RESULT'
        return outcome, None, None
    outcome, kind, fields, _ = classify_child(stdout, rc if rc >= 0 else 2, pins=pins, selected=selected)
    if rc < 0 and outcome != 'CRASH_NO_RESULT':
        outcome = 'CRASH_NO_RESULT'  # killed by a signal: no result is trusted, whatever was printed before
    if outcome == 'CRASH_NO_RESULT' and fields is None:
        fields = {'returncode': rc}      # read by a wrapper (T-0 expect_line): how the child ended without its line
    if kind == 'tests' and outcome in ('CHILD_OK', 'CHILD_FAILED', 'CHILD_INDETERMINATE'):
        # T-0 (R5), DP-2.3 F10: a stage 1 test runner's child whose mode= differs from the mode pinned for its caller profile is
        # CHILD_EVIDENCE_ERROR (so ITEM_ERROR in a mutation or sabotage tool), never a kill, a survival or a pass
        want = _pinned_child_mode(cmd)
        if want is not None and fields.get('mode') != want:
            outcome = 'CHILD_EVIDENCE_ERROR'
    return outcome, kind, fields


CHILD_TEST_RUNNERS = ('run_m2_tests_s1', 'mut_runner_s1', 'run_test_files_s1', 'child_unittest_runner', 'run_m8_tests_s1')


def _pinned_child_mode(cmd):
    """The mode pinned for a stage 1 kind=tests runner started as this child (runner_profiles '<runner>@<caller>', the caller from its
    --caller argument, else 'standalone'); None when the child is not one of those runners; 'unpinned' when no profile is pinned (which
    no child line can match)."""
    script = next((a for a in cmd if isinstance(a, str) and a.endswith('.py')), None)
    runner = os.path.basename(script)[:-3] if script else None
    if runner not in CHILD_TEST_RUNNERS:
        return None
    caller = cmd[cmd.index('--caller') + 1] if '--caller' in cmd and cmd.index('--caller') + 1 < len(cmd) else 'standalone'
    try:
        pins, _ = load_pins()
        return runner_mode(pins, runner, caller)
    except RunError:
        return 'unpinned'

# ---------------------------------------------------------------------------------------------------------------------------------------
# Step 3: §2.2 pins, §2.1 preflight, §2.3 controls, §2.6 timeout classification, and the mutation outcome mapping
# ---------------------------------------------------------------------------------------------------------------------------------------

import json

PINS_PATH = os.path.join(ROOT, 'tools', 'expected_counts.json')


def _content_sha256(doc):
    """The SHA-256 of the pins' content: every key except 'change_records', canonical JSON (sorted keys, no spaces)."""
    body = {k: v for k, v in doc.items() if k != 'change_records'}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def load_pins(path=PINS_PATH, expected_file_sha256=None):
    """§2.2: load the pinned counts.  The content must equal what the last change record says (a change without a change record
    fails closed, EXPECTED_COUNT_UNRECORDED_CHANGE); the file's version must equal the last record's; if the run instruction gives the
    file's SHA-256, it must match.  Returns (pins, file_sha256) or raises RunError."""
    try:
        with open(path, 'rb') as fh:
            raw = fh.read()
    except OSError as e:
        raise RunError('EXPECTED_COUNTS_MISSING', '%s %s' % (path, type(e).__name__))
    fsha = hashlib.sha256(raw).hexdigest()
    if expected_file_sha256 is not None and fsha != expected_file_sha256:
        raise RunError('EXPECTED_COUNTS_HASH', fsha)
    try:
        doc = json.loads(raw.decode('utf-8'))
    except ValueError:
        raise RunError('EXPECTED_COUNTS_MALFORMED', path)
    recs = doc.get('change_records') or []
    if not recs:
        raise RunError('EXPECTED_COUNT_UNRECORDED_CHANGE', 'no change record')
    last = recs[-1]
    if doc.get('version') != last.get('version') or [r.get('version') for r in recs] != list(range(1, len(recs) + 1)):
        raise RunError('EXPECTED_COUNT_UNRECORDED_CHANGE', 'version %r' % doc.get('version'))
    if _content_sha256(doc) != last.get('content_sha256'):
        raise RunError('EXPECTED_COUNT_UNRECORDED_CHANGE', 'content differs from change record %d' % last.get('version'))
    return doc, fsha


def write_pins(doc, reason, cause, changes, path=PINS_PATH, date=None):
    """§2.2: the only way the pins change: a new version with a change record (old value, new value, reason, cause)."""
    import datetime
    if not reason or not cause:
        raise ValueError('a change record needs a reason and a cause')
    recs = list(doc.get('change_records') or [])
    doc = dict(doc, version=len(recs) + 1)
    rec = {'version': len(recs) + 1, 'date': date or datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
           'reason': reason, 'cause': cause, 'changes': changes}
    rec['content_sha256'] = _content_sha256(dict(doc, change_records=[]))
    doc['change_records'] = recs + [rec]
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=1, sort_keys=True)
        f.write('\n')
    os.replace(tmp, path)
    return doc


def test_file_pins(pins, relpaths):
    """For finish_tests and check_output: <file name> -> {'sha256', 'ids'}, from the pins' test_files section (keyed by the path
    relative to the root).  §2.7 allows no '/' in a FILE name, so a run's FILE names are the files' base names, which must be unique
    within the run (else RunError SELECTION_INVALID).  An unpinned path is absent (finish_tests then reports TEST_FILE_NOT_IN_PINS)."""
    tf = pins.get('test_files', {})
    names = [os.path.basename(r) for r in relpaths]
    if len(set(names)) != len(names):
        raise RunError('SELECTION_INVALID', 'duplicate file base names in one run')
    return {os.path.basename(r): {'sha256': tf[r]['sha256'], 'ids': list(tf[r]['ids'])} for r in relpaths if r in tf}


def runner_mode(pins, runner, caller):
    """§2.2 (R5) / DP-2.3: the one mode pinned for this runner and caller profile.  Raises RunError if there is none."""
    key = '%s@%s' % (runner, caller)
    prof = pins.get('runner_profiles', {}).get(key)
    if not prof or prof.get('mode') not in ('full', 'failfast'):
        raise RunError('RUNNER_PROFILE_NOT_PINNED', key)
    return prof['mode']


def preflight_text(mutants, root):
    """§2.1: every mutant's target text must occur exactly once in its file, or exactly its declared 'occurrences' N ('all' means at
    least one).  mutants: [(id, relative path, old, new, occurrences)] with occurrences None for 'exactly once'.
    Returns a list of RunError (PREFLIGHT_INVALID_TARGET), one per failing mutant, and the human lines 'PREFLIGHT FAILED <id>: ...'."""
    errs, human = [], []
    for mid, rel, old, new, occ in mutants:
        path = os.path.join(root, rel)
        try:
            with open(path, encoding='utf-8') as fh:
                n = fh.read().count(old)
        except OSError:
            n = None
        if n is None:
            reason = 'file_missing'
        elif occ == 'all':
            reason = None if n >= 1 else 'occurrences=0'
        elif n != (occ or 1):
            reason = 'occurrences=%d expected=%d' % (n, occ or 1)
        else:
            reason = None
        if reason:
            errs.append(RunError('PREFLIGHT_INVALID_TARGET', '%s:%s' % (mid, reason.replace(' ', ','))))
            human.append('PREFLIGHT FAILED %s: %s in %s' % (mid, reason, rel))
    return errs, human


COPY_IGNORE = ('logs', '__pycache__', '.git', 'dist')


FULL_TREE_IGNORE = ('__pycache__', '.git')   # for a check that reads the whole package, logs/ included (the M8 boundary test; M10's sabotage_m8)


def fresh_copy(root, dest, disk_floor_bytes=10 * 1024 ** 3, ignore=COPY_IGNORE):
    """A fresh copy of the tree for one control or mutant (§2.3), after re-checking free disk (§2.8, before each tree copy).  ignore: the
    names left out, as the M10 tool did (its mutation tools leave out logs/; sabotage_m8 copied the whole package)."""
    free = shutil.disk_usage(os.path.dirname(dest) or '.').free
    if free < disk_floor_bytes:
        raise RunError('ENV_DISK_BELOW_FLOOR', 'free=%d floor=%d' % (free, disk_floor_bytes))
    shutil.copytree(root, dest, ignore=shutil.ignore_patterns(*ignore))
    return dest


def run_sequence(commands, env, cwd, timeout, unit='seq', stop=None, last=False, on_end=None):
    """Run a test sequence [(label, cmd)] in order, stopping at the first command that is not CHILD_OK.  Returns
    (outcome, label of the first command that is not CHILD_OK or None, [(label, outcome, seconds)]).
    Corrective pass 2: each command is a unit under P, named '<unit>:<label>'.  last: the sequence is the run's last unit (the end
    control, F.2): its outcome is fixed by the command whose outcome ends the sequence (the last command, or one that is not CHILD_OK
    at the moment it is fixed); a leak found by the cleanup of an earlier command ends the sequence at that cleanup's end.
    on_end(): called at that same moment for any sequence (an item's: F.2's phase moves on before the fix is decided)."""
    timings = []
    cmds = list(commands)
    for n, c in enumerate(cmds):
        label, cmd, classify = (c + (None,))[:3]
        final = n == len(cmds) - 1

        ended = []

        def ends(rc, out, cmd=cmd, classify=classify, final=final):
            e = final or rc is None or classify_exited(cmd, rc, out, classify=classify)[0] != 'CHILD_OK'
            if e:
                ended.append(1)
                if on_end is not None:
                    on_end()
            return e and last
        outcome, out, err, secs, kind, fields = run_child(cmd, timeout, env, cwd, classify=classify, unit='%s:%s' % (unit, label),
                                                          stop=stop, last=ends)
        timings.append((label, outcome, round(secs, 3)))
        if outcome != 'CHILD_OK':
            if outcome == 'PROCESSES_LEFT' and not ended:
                if on_end is not None:
                    on_end()
                if not CANCEL.fix(last=last):
                    outcome = 'INTERRUPTED'
            elif not ended and on_end is not None:
                on_end()
            return outcome, label, timings, out
    return 'CHILD_OK', None, timings, ''


def regression_step_classifier(step):
    """For an M10 regression tool run as 'run_regression_<x>.py --step <step>' (the check of a sabotage tool; T_tooling.md F9): it prints
    exactly one 'PASS <step> ...' or 'FAIL <step> ...' line and the summary 'checks 1  failed <0|1>', and exits 0 or 1.  CHILD_OK only for
    PASS, 'failed 0' and exit 0; CHILD_FAILED only for FAIL, 'failed 1' and exit 1; anything else is CRASH_NO_RESULT (not recognised),
    which is never a catch."""
    def classify(stdout, rc):
        lines = stdout.splitlines()
        hits = [l for l in lines if l.split(' ')[:2] in (['PASS', step], ['FAIL', step])]
        summ = [l for l in lines if l in ('checks 1  failed 0', 'checks 1  failed 1')]
        if len(hits) != 1 or len(summ) != 1:
            return 'CRASH_NO_RESULT'
        if hits[0].startswith('PASS ') and summ[0].endswith('failed 0') and rc == 0:
            return 'CHILD_OK'
        if hits[0].startswith('FAIL ') and summ[0].endswith('failed 1') and rc == 1:
            return 'CHILD_FAILED'
        return 'CRASH_NO_RESULT'
    return classify


def load_and_disk():
    try:
        la = os.getloadavg()[0]
    except OSError:
        la = -1.0
    return la


def control(root, workdir, phase, commands_fn, env, timeout, disk_floor_bytes=10 * 1024 ** 3, ignore=COPY_IGNORE, last=None):
    """§2.3: one unmutated control run in its own fresh copy, with the same commands, limits and parallelism as the items.
    Returns (value, lines, run_error): value is PASS, FAIL or TIMEOUT; lines are the CONTROL line, with per-command timings, the load
    average and free disk (§2.6); run_error is a CONTROL_TOOL_ERROR RunError when the copy could not be made, else None.
    A control is never an item result.
    Corrective pass 2:
    - F.1: the copy refused by the disk floor: the start control FAIL cause=disk_below_floor; the end control NOT_RUN with
      'CONTROL end CONTROL_NOT_RUN cause=disk_below_floor'; each with RUN_ERROR ENV_DISK_BELOW_FLOOR <phase word> free= floor=.
    - F.2: a signal before the control starts, or before its outcome is fixed (P.8): the start control FAIL with
      'CONTROL start CONTROL_INTERRUPTED cause=interrupted' (one that had not started has the same line: it did not pass, and every
      item is NOT_RUN); the end control NOT_RUN, with 'CONTROL end CONTROL_NOT_RUN cause=interrupted' only if it had started (K.1).
    - B.4: a control whose unit left processes is FAIL cause=processes_left."""
    dest = os.path.join(workdir, 'control_%s' % phase)
    word = 'control_%s' % phase
    set_phase(word)
    if CANCEL.set:
        if phase == 'start':
            return 'FAIL', ['CONTROL start CONTROL_INTERRUPTED cause=interrupted'], None
        return 'NOT_RUN', [], None
    try:
        fresh_copy(root, dest, disk_floor_bytes, ignore=ignore)
    except RunError as e:
        if e.code == 'ENV_DISK_BELOW_FLOOR':
            err = RunError('ENV_DISK_BELOW_FLOOR', '%s %s' % (word, e.detail))
            if phase == 'start':
                return 'FAIL', ['CONTROL start CONTROL_FAIL cause=disk_below_floor'], err
            return 'NOT_RUN', ['CONTROL end CONTROL_NOT_RUN cause=disk_below_floor'], err
        return 'FAIL', ['CONTROL %s FAIL cause=control_tool_error' % phase], RunError('CONTROL_TOOL_ERROR', '%s %s' % (phase, e))
    except OSError as e:
        return 'FAIL', ['CONTROL %s FAIL cause=control_tool_error' % phase], RunError('CONTROL_TOOL_ERROR', '%s %s' % (phase, e))
    try:
        outcome, label, timings, _ = run_sequence(commands_fn(dest), env, dest, timeout, unit=word,
                                                  last=(phase == 'end') if last is None else last)
    finally:
        shutil.rmtree(dest, ignore_errors=True)
    if outcome == 'INTERRUPTED':
        if phase == 'start':
            return 'FAIL', ['CONTROL start CONTROL_INTERRUPTED cause=interrupted'], None
        return 'NOT_RUN', ['CONTROL end CONTROL_NOT_RUN cause=interrupted'], None
    value = 'PASS' if outcome == 'CHILD_OK' else ('TIMEOUT' if outcome == 'TIMEOUT' else 'FAIL')
    if phase == 'start' and value == 'PASS':
        set_phase('between')
    t = ' '.join('%s=%.3fs' % (l, s) for l, _, s in timings)
    cause = 'ok' if value == 'PASS' else {'PROCESSES_LEFT': 'processes_left', 'CHILD_INTERRUPTED': 'child_interrupted'}.get(outcome, outcome)
    lines = ['CONTROL %s %s cause=%s %s load=%.2f free_disk_bytes=%d' % (
        phase, 'CONTROL_' + value, cause, t, load_and_disk(), shutil.disk_usage(workdir).free)]
    return value, lines, None


def classify_timeout(kind, item, cmd_label, limit, control_times):
    """§2.6 / DP-2.1 (a): a timeout is never a kill, in every kind.  Always INDETERMINATE cause=timeout.  The measurement (the command,
    the limit and the start and end control times for that command) is returned as a TIMEOUT line, recorded for mutation and sabotage
    only (R7); for cases and tests no control measurement exists."""
    if kind in ('mutation', 'sabotage'):
        st, en = control_times.get(('start', cmd_label)), control_times.get(('end', cmd_label))
        line = 'TIMEOUT %s cmd=%s limit=%ss control_start=%s control_end=%s' % (item, cmd_label, limit,
                                                                                  'NA' if st is None else '%.3fs' % st,
                                                                                  'NA' if en is None else '%.3fs' % en)
    else:
        line = None
    return ('INDETERMINATE', 'timeout'), line


def map_mutant(sequence_outcome, failing_label, equivalent=False):
    """T-0 (R4): the one mapping every successor mutation tool uses.  CHILD_FAILED -> KILLED cause=<the failing command>; every
    command CHILD_OK -> SURVIVED (or EQUIVALENT when documented); TIMEOUT -> INDETERMINATE (classify_timeout); CRASH_NO_RESULT and
    CHILD_INDETERMINATE -> INDETERMINATE; CHILD_EVIDENCE_ERROR and LAUNCH_ERROR -> ITEM_ERROR.  A crash is never a kill."""
    if sequence_outcome == 'CHILD_OK':
        return ('EQUIVALENT', 'documented') if equivalent else ('SURVIVED', 'none')
    if sequence_outcome == 'CHILD_FAILED':
        return 'KILLED', failing_label
    if sequence_outcome == 'TIMEOUT':
        return 'INDETERMINATE', 'timeout'
    if sequence_outcome == 'CRASH_NO_RESULT':
        return 'INDETERMINATE', 'crash_no_result'
    if sequence_outcome == 'CHILD_INDETERMINATE':
        return 'INDETERMINATE', 'child_indeterminate'
    if sequence_outcome == 'PROCESSES_LEFT':      # corrective pass 2, P.6
        return 'INDETERMINATE', 'processes_left'
    if sequence_outcome == 'INTERRUPTED':         # F.2
        return 'INDETERMINATE', 'interrupted'
    if sequence_outcome == 'STOPPED':             # F.1
        return 'INDETERMINATE', 'run_stopped'
    if sequence_outcome == 'CHILD_INTERRUPTED':   # amendment 2, AM2-2 (d)
        return 'INDETERMINATE', 'child_interrupted'
    return 'ITEM_ERROR', sequence_outcome.lower()


def map_plant(sequence_outcome, failing_label):
    """The same mapping for kind=sabotage: the checks failing on a plant is CAUGHT; passing is MISSED; a timeout or a crash is
    INDETERMINATE, never caught."""
    o, cause = map_mutant(sequence_outcome, failing_label)
    return {'KILLED': ('CAUGHT', cause), 'SURVIVED': ('MISSED', 'none')}.get(o, (o, cause))


def list_test_ids(relpath, root=ROOT):
    """The ids (module.Class.method) of the tests in one test file, loaded the way the runners load it.  Raises on an import error."""
    import importlib
    import unittest
    mod = relpath[:-3].replace(os.sep, '.')
    m = importlib.import_module(mod)
    suite = unittest.defaultTestLoader.loadTestsFromModule(m)
    out = []

    def walk(s):
        for t in s:
            if isinstance(t, unittest.TestSuite):
                walk(t)
            else:
                out.append(t.id())
    walk(suite)
    return out


def pin_test_files(relpaths, root=ROOT, interpreter=None, timeout=600):
    """§2.2: compute the pin of each test file (its SHA-256 and its exact inventory of test ids), each in its own isolated child
    (python3 -I -S tools/evkit.py --list-test-ids <relpath>).  Returns {relpath: {'sha256', 'ids', 'ids_sha256'}}; raises RunError if a
    file cannot be listed."""
    tmp = os.environ.get('TMPDIR') or '/tmp'
    out = {}
    for rel in relpaths:
        cmd = child_cmd(os.path.join(root, 'tools', 'evkit.py'), ['--list-test-ids', rel], interpreter=interpreter)
        p = run_unit('pin:%s' % rel, cmd, timeout, clean_env(tmp), root)      # P.9: every evkit child start is a unit under P
        if p.how != 'exit' or p.leaked or p.returncode != 0:
            raise RunError('PIN_LIST_FAILED', '%s %s exit=%s %s' % (rel, p.how, p.returncode, (p.stderr.strip().splitlines() or [''])[-1]))
        ids = [l[3:] for l in p.stdout.splitlines() if l.startswith('ID ')]
        out[rel] = {'sha256': sha256_file(os.path.join(root, rel)), 'ids': sorted(ids), 'ids_sha256': sha256_lines(ids)}
    return out


TEST_DIRS = ('tests', 'tests_m8', 'tests_m10', 'tests_tools')


def all_test_files(root=ROOT):
    """Every test file a runner can load: <dir>/test_*.py for each test directory, as paths relative to the root, sorted."""
    out = []
    for d in TEST_DIRS:
        full = os.path.join(root, d)
        if os.path.isdir(full):
            out += ['%s/%s' % (d, f) for f in sorted(os.listdir(full)) if f.startswith('test_') and f.endswith('.py')]
    return out


def update_pins(reason, cause, profiles=(), root=ROOT, path=PINS_PATH, files=None):
    """§2.2's recorded process: recompute the test-file pins (all test files, or the named ones), apply runner-profile settings
    ('runner@caller=mode'), and write a new version with one change record listing every entry whose value changed (old -> new).
    Returns the new document."""
    try:
        doc, _ = load_pins(path)
    except RunError as e:
        if e.code != 'EXPECTED_COUNTS_MISSING':
            raise
        doc = {'schema': 'APG-M11-S1 expected counts', 'test_files': {}, 'runner_profiles': {}, 'mutation_lists': {},
               'case_inventories': {}, 'plants': {}, 'timeout_kill_factor': None, 'change_records': []}
    old_tf = dict(doc.get('test_files', {}))
    new_tf = dict(old_tf)
    targets = files if files is not None else all_test_files(root)
    new_tf.update(pin_test_files(targets, root))
    if files is None:
        for gone in [k for k in new_tf if k not in targets]:
            del new_tf[gone]
    changes = []
    for k in sorted(set(old_tf) | set(new_tf)):
        o, n = old_tf.get(k), new_tf.get(k)
        if o != n:
            changes.append({'entry': 'test_files/' + k, 'old': None if o is None else {'sha256': o['sha256'], 'tests': len(o['ids']),
                            'ids_sha256': o['ids_sha256']}, 'new': None if n is None else {'sha256': n['sha256'], 'tests': len(n['ids']),
                            'ids_sha256': n['ids_sha256']}})
    prof = dict(doc.get('runner_profiles', {}))
    for setting in profiles:
        key, mode = setting.rsplit('=', 1)
        if mode not in ('full', 'failfast') or '@' not in key:
            raise ValueError('a profile is runner@caller=full|failfast: %r' % setting)
        if prof.get(key, {}).get('mode') != mode:
            changes.append({'entry': 'runner_profiles/' + key, 'old': prof.get(key), 'new': {'mode': mode}})
            prof[key] = {'mode': mode}
    if not changes:
        return doc
    doc = dict(doc, test_files=new_tf, runner_profiles=prof)
    return write_pins(doc, reason, cause, changes, path=path)

# ---------------------------------------------------------------------------------------------------------------------------------------
# Step 4: running one test file, test by test, against its pinned inventory (the engine of every successor kind=tests runner)
# ---------------------------------------------------------------------------------------------------------------------------------------


def _flatten(suite):
    import unittest
    out = []
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            out += _flatten(t)
        else:
            out.append(t)
    return out


def run_test_file(relpath, pinned_ids, mode, root=ROOT):
    """Run one test file in this process and return (FileResult, run_errors).
    - The file's module is imported the way the runners import it.  If the import itself fails, that is the code under test failing
      (§2.7: 'an import error inside the code under test is an error'): in mode=full every pinned test is ERROR; in mode=failfast the
      first pinned test is ERROR and the rest NOT_RUN_AFTER_FAILURE.
    - The tests loaded must equal the pinned ids exactly, before any runs; otherwise the file is ITEM_ERROR, with
      RUN_ERROR TEST_INVENTORY_MISMATCH (a runner-side evidence error, exit 2).
    - Tests run through their suite, so class and module fixtures run as unittest runs them; each test's status is recorded in
      execution order.  mode=failfast stops at the first FAIL or ERROR (F11), and the pinned tests that did not run are
      NOT_RUN_AFTER_FAILURE.  A class or module fixture error is recorded as ERROR on each test it prevented."""
    import importlib
    import unittest
    name = os.path.basename(relpath)
    path = os.path.join(root, relpath)
    pinned = list(pinned_ids)
    try:
        fsha = sha256_file(path)
    except OSError:
        return FileResult(name, 'ITEM_ERROR', [], '0' * 64, cause='file_unreadable'), [RunError('TEST_FILE_UNREADABLE', relpath)]
    modname = relpath[:-3].replace('/', '.')
    try:
        mod = importlib.import_module(modname)
    except Exception:
        if not pinned:
            return FileResult(name, 'ITEM_ERROR', [], fsha, cause='import_failed'), [RunError('TEST_INVENTORY_MISMATCH', '%s ids' % name)]
        if mode == 'failfast':
            return FileResult(name, 'COMPLETED', [(sorted(pinned)[0], 'ERROR')], fsha, not_run_after_failure=sorted(pinned)[1:]), []
        return FileResult(name, 'COMPLETED', [(i, 'ERROR') for i in sorted(pinned)], fsha), []
    tests = _flatten(unittest.defaultTestLoader.loadTestsFromModule(mod))
    loaded = [t.id() for t in tests]
    if sorted(loaded) != sorted(pinned) or len(set(loaded)) != len(loaded):
        return (FileResult(name, 'ITEM_ERROR', [], fsha, cause='inventory'),
                [RunError('TEST_INVENTORY_MISMATCH', '%s ids loaded=%d pinned=%d' % (name, len(loaded), len(pinned)))])
    by_class = {}
    for t in tests:
        by_class.setdefault(type(t).__module__ + '.' + type(t).__qualname__, []).append(t.id())

    class Collector(unittest.TestResult):
        def __init__(self):
            self._stop_asked = False
            super().__init__()
            self.order = []
            self.status = {}

        # F.2 and AM-2: an interrupt is honoured between tests.  The suite checks shouldStop before each test, and the handler's flag
        # makes this result stop(): the test that is running finishes, and no further test starts.
        @property
        def shouldStop(self):
            if CANCEL.set and not self._stop_asked:
                self.stop()
            return self._stop_asked

        @shouldStop.setter
        def shouldStop(self, v):
            self._stop_asked = bool(v)

        def _put(self, test, st):
            tid = test.id()
            if tid in self.status:
                return
            self.status[tid] = st
            self.order.append((tid, st))

        def addSuccess(self, test):
            super().addSuccess(test)
            self._put(test, 'PASS')

        def addFailure(self, test, err):
            super().addFailure(test, err)
            self._put(test, 'FAIL')

        def addError(self, test, err):
            super().addError(test, err)
            if isinstance(test, unittest.TestCase):
                self._put(test, 'ERROR')
                return
            # a class or module fixture failed (an _ErrorHolder): every test it prevented gets ERROR
            desc = str(test)
            hit = [cls for cls in by_class if cls in desc] or ([] if 'setUpClass' in desc or 'setUpModule' in desc else [])
            if not hit and ('setUpModule' in desc or 'tearDownModule' in desc):
                hit = list(by_class)
            for cls in hit:
                for tid in by_class[cls]:
                    if tid not in self.status:
                        self.status[tid] = 'ERROR'
                        self.order.append((tid, 'ERROR'))

        def addSkip(self, test, reason):
            super().addSkip(test, reason)
            self._put(test, 'SKIP')

        def addExpectedFailure(self, test, err):
            super().addExpectedFailure(test, err)
            self._put(test, 'PASS')

        def addUnexpectedSuccess(self, test):
            super().addUnexpectedSuccess(test)
            self._put(test, 'FAIL')

        def addSubTest(self, test, subtest, err):
            super().addSubTest(test, subtest, err)
            if err is not None:
                st = 'FAIL' if issubclass(err[0], test.failureException) else 'ERROR'
                tid = test.id()
                if tid not in self.status:
                    self.status[tid] = st
                    self.order.append((tid, st))

    res = Collector()
    res.failfast = (mode == 'failfast')
    suite = unittest.defaultTestLoader.loadTestsFromModule(mod)
    import io
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        if _SUP.supervisor:
            # AM-5 (c): in child_unittest_runner as a supervisor, the children a test module starts are that file's; a leak makes the
            # file INDETERMINATE (its cause on its CLEANUP line)
            with owning(name) as o_file:
                suite.run(res)
        else:
            o_file = None
            suite.run(res)
    ran = list(res.order)
    missing = [i for i in loaded if i not in res.status]
    errs = []
    if o_file is not None and o_file.leaked:
        return FileResult(name, 'INDETERMINATE', ran, fsha, cause='processes_left'), errs
    if mode == 'failfast' and any(s in ('FAIL', 'ERROR') for _, s in ran):
        # stopped at the first failure: keep the ran tests up to and including it; the rest did not run
        cut = next(k for k, (_, s) in enumerate(ran) if s in ('FAIL', 'ERROR'))
        extra = ran[cut + 1:]
        ran = ran[:cut + 1]
        nraf = sorted(set(missing) | {i for i, _ in extra})
        return FileResult(name, 'COMPLETED', ran, fsha, not_run_after_failure=nraf), errs
    if missing and res._stop_asked and CANCEL.set:
        # F.2: tests of this file did not start because of the interrupt: the file is INDETERMINATE, with no run error
        return FileResult(name, 'INDETERMINATE', ran, fsha, cause='interrupted'), errs
    if missing:
        errs.append(RunError('TEST_NOT_RUN_IN_FULL_FILE', '%s %d' % (name, len(missing))))
        return FileResult(name, 'ITEM_ERROR', ran, fsha, cause='tests_not_run'), errs
    return FileResult(name, 'COMPLETED', ran, fsha), errs


def verified_auif_root():
    """The AUIF copy that APG's own loader verified by hash in this process (apg_auif.dependency.ensure: ZIP hash, AUIF's manifest check,
    core tree hash), or None.  Non-APG modules are allowed only from it."""
    dep = sys.modules.get('apg_auif.dependency')
    ready = getattr(dep, '_READY', None) if dep is not None else None
    root = ready.get('root') if isinstance(ready, dict) else None
    return os.path.realpath(root) if root else None


def tests_runner_main(tool, test_dir, argv, caller_default='standalone', human_counts_line=True, name_map=None):
    """The common main of the successor kind=tests runners (run_m2_tests_s1, mut_runner_s1, run_test_files_s1, child_unittest_runner).
    argv: the file selection (base names or patterns, as the tool defines it) is resolved by the caller into relpaths; this function
    takes argv as a dict: {'relpaths': [...], 'mode': 'full'|'failfast', 'caller': str, 'run_id': str, 'errors': [RunError]}.
    Prints ENV and IMPORT lines, the TEST/FILE lines, the human counts line, RUN_ERROR lines and the RESULT line; returns the exit code."""
    preloaded = tuple(k for k in sys.modules if k.split('.')[0] in TRUSTED_PACKAGES and k not in ('tools', 'tools.evkit'))
    allowed = tuple(argv.get('allowed_paths', ()))
    lines, errs = start(ROOT, preloaded=preloaded)
    errs = errs + list(argv.get('errors', []))
    mode = argv['mode']
    rel = argv['relpaths']
    try:
        pins, _ = load_pins()
        expected_mode = runner_mode(pins, tool, argv.get('caller') or caller_default)
        if expected_mode != mode:
            errs.append(RunError('RUNNER_MODE_NOT_PINNED', '%s@%s mode=%s pinned=%s' % (tool, argv.get('caller') or caller_default, mode, expected_mode)))
        fpins = test_file_pins(pins, rel)
    except RunError as e:
        errs.append(e)
        pins, fpins = {}, {}
    names = [os.path.basename(r) for r in rel]
    results = {}
    end_imports = []
    fail_lines = []
    # decision (f) (owner, 2026-11-02 14:24): a child given APG_AUIF_ROOT verifies that copy itself, with AUIF's own loader, before any
    # test; a copy that cannot be verified is a refusal (ENV_AUIF_ROOT_UNVERIFIED, exit 2), never a test failure.  The loader caches the
    # verified copy, so the test modules' own ensure() reuses it.
    if not errs and argv.get('verify_auif'):
        # AM-2, amendment 2 reading 14: child_unittest_runner is a supervisor whenever it verifies an AUIF copy; it declares itself here,
        # immediately before the verification, and refuses with ENV_NO_PROCESS_SUPERVISION if containment cannot be set up
        declare_supervisor(tool_stem())
        errs += supervision_errors()
    if not errs and argv.get('verify_auif'):
        with owning('run_start') as o_start:     # AM-5 (c): the verification's children are the run's start
            try:
                from apg_auif import dependency as _auif_dependency
                _auif_dependency.ensure(argv['verify_auif'])
            except Exception as e:
                errs.append(RunError('ENV_AUIF_ROOT_UNVERIFIED', '%s %s' % (argv['verify_auif'], one_line(str(e))[:200])))
        if o_start.leaked:
            errs.append(RunError('PROCESSES_LEFT', 'run_start'))
    # every name is checked against the pins before any file runs: one unpinned name and no file runs (finish_tests reports it)
    if not errs and all(n in fpins for n in names):
        failed = False
        for r, n in zip(rel, names):
            if n not in fpins:
                continue
            if mode == 'failfast' and failed:
                break
            if CANCEL.set:          # F.2: no further file starts; the files not started are NOT_RUN
                break
            set_phase(n)
            fr, ferrs = run_test_file(r, fpins[n]['ids'], mode, ROOT)
            results[n] = fr
            errs += ferrs
            if fr.state == 'COMPLETED' and any(s in ('FAIL', 'ERROR') for _, s in fr.tests):
                failed = True
                fail_lines.append('FAIL %s' % ((name_map or (lambda x: x))(n)))
        set_phase('between')
        if CANCEL.set and len(results) == len(names) and all(fr.cause != 'interrupted' for fr in results.values()):
            CANCEL.nothing_cut()    # amendment 2 reading for leaves: the signal cut no test, so the run completed (SIGNAL_AFTER_COMPLETION)
        verified = verified_auif_root()
        if verified and allowed and os.path.realpath(verified) not in allowed:
            errs.append(RunError('ENV_AUIF_ROOT_UNVERIFIED', 'loaded %s, given %s' % (verified, ' '.join(allowed))))
        ierrs, recs = import_identity(ROOT, preloaded=preloaded, candidate_paths=allowed + ((verified,) if verified else ()))
        # §2.5: again at the end of the run; the only non-APG modules allowed are those of the AUIF copy apg_auif.dependency verified
        errs += ierrs
        end_imports = ['IMPORT_END %s %s' % (n, p) for n, p in recs]
    out, code = finish_tests(tool, mode, argv.get('run_id') or 'run', names, results, fpins, errs)
    t = sum(len(r.tests) for r in results.values() if r.state == 'COMPLETED')
    f = sum(1 for r in results.values() if r.state == 'COMPLETED' for _, s in r.tests if s == 'FAIL')
    e = sum(1 for r in results.values() if r.state == 'COMPLETED' for _, s in r.tests if s == 'ERROR')
    human = ['tests %d  failures %d  errors %d' % (t, f, e)] if human_counts_line else []
    k = next(i for i, l in enumerate(out) if l.startswith('RUN_ERROR') or l.startswith('RESULT'))
    return emit(lines + out[:k] + end_imports + human + fail_lines + out[k:], code)


def file_result_from_child(name, outcome, stdout):
    """A wrapper's view of one child group (T-0 expect_line, R4): the child's own TEST and FILE lines for the file, when the child's
    output is valid evidence (CHILD_OK or CHILD_FAILED); ITEM_ERROR for CHILD_EVIDENCE_ERROR and LAUNCH_ERROR; INDETERMINATE for
    CHILD_INDETERMINATE, TIMEOUT and CRASH_NO_RESULT.  The child's results are never inferred from a partial or invalid log."""
    if outcome in ('CHILD_EVIDENCE_ERROR', 'LAUNCH_ERROR'):
        return FileResult(name, 'ITEM_ERROR', [], '0' * 64, cause=outcome.lower())
    if outcome not in ('CHILD_OK', 'CHILD_FAILED'):
        return FileResult(name, 'INDETERMINATE', [], '0' * 64, cause=outcome.lower())
    tests, nraf, state, fsha = [], [], None, '0' * 64
    for l in stdout.splitlines():
        m = re.match(r'^TEST (\S+?)::(\S+) (\S+)$', l)
        if m and m.group(1) == name:
            (nraf.append(m.group(2)) if m.group(3) == 'NOT_RUN_AFTER_FAILURE' else tests.append((m.group(2), m.group(3))))
        m = re.match(r'^FILE (\S+) state=(\S+) .* file_sha256=([0-9a-f]{64}) ', l)
        if m and m.group(1) == name:
            state, fsha = m.group(2), m.group(3)
    if state not in ('COMPLETED', 'INDETERMINATE', 'ITEM_ERROR'):
        return FileResult(name, 'ITEM_ERROR', [], fsha, cause='child_file_state_%s' % state)
    return FileResult(name, state, tests, fsha, not_run_after_failure=nraf)

# ---------------------------------------------------------------------------------------------------------------------------------------
# Step 5: the mutation driver every successor mutation tool uses (kind=mutation)
# ---------------------------------------------------------------------------------------------------------------------------------------


class Mutant:
    """One mutant.  relpath: the file it changes (relative to the root).  site: a short text identifying the exact target (for a text
    mutant, the target text; for an AST mutant, '<kind>|<ast.unparse(node)>|<operand index>'), whose SHA-256 is pinned.
    apply(src) -> the mutated source.  occurrences: text mutants only (§2.1)."""

    def __init__(self, mid, relpath, site, apply, group=None, occurrences=None, text_old=None, creates=False, what=None, check=None):
        self.id, self.relpath, self.site, self.apply, self.group = mid, relpath, site, apply, group
        self.occurrences, self.text_old = occurrences, text_old
        self.creates, self.what, self.check = creates, what, check   # kind=sabotage: a plant that adds a file; its description; its check

    def site_sha256(self):
        return hashlib.sha256(self.site.encode('utf-8')).hexdigest()


def load_tool_module(name, root=ROOT):
    """Load an M10 tool (byte-identical in the successor, DP-1.2 (B)) by file path, for its definitions only (main() is guarded).
    Its module name is the file's stem, so import identity records it under tools/ (§2.5)."""
    import importlib.util
    path = os.path.join(root, 'tools', name + '.py')
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _parse_selection(argv, universe):
    """--only PREFIX and --ids A,B select a subset; with neither, the full pinned universe.  Returns (selected ids, errors, opts)."""
    opts = {'jobs': 2, 'run_id': 'run', 'list': False, 'pin': False, 'reason': '', 'cause': '', 'baseline': False}
    errs, only, ids = [], None, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ('--jobs', '--run-id', '--only', '--ids', '--reason', '--cause'):
            if i + 1 >= len(argv):
                errs.append(RunError('SELECTION_INVALID', 'missing value for %s' % a))
                break
            v = argv[i + 1]
            i += 1
            if a == '--jobs':
                if not INT.match(v) or int(v) < 1:
                    errs.append(RunError('SELECTION_INVALID', 'jobs %s' % v))
                else:
                    opts['jobs'] = int(v)
            elif a == '--run-id':
                opts['run_id'] = v
            elif a == '--only':
                only = v
            elif a == '--ids':
                ids = [x for x in v.split(',') if x]
            elif a == '--reason':
                opts['reason'] = v
            else:
                opts['cause'] = v
        elif a == '--list':
            opts['list'] = True
        elif a == '--pin':
            opts['pin'] = True
        elif a == '--baseline':
            opts['baseline'] = True
        else:
            errs.append(RunError('SELECTION_INVALID', 'unknown argument %s' % a))
        i += 1
    sel = list(universe)
    if only is not None:
        sel = [m for m in sel if m.startswith(only)]
        if not sel:
            errs.append(RunError('SELECTION_INVALID', 'only %s selects nothing' % only))
    if ids is not None:
        unknown = [x for x in ids if x not in universe]
        if unknown:
            errs.append(RunError('SELECTION_INVALID', 'unknown ids %s' % ','.join(unknown[:5])))
        if len(set(ids)) != len(ids):
            errs.append(RunError('SELECTION_INVALID', 'duplicate ids'))
        sel = [m for m in sel if m in set(ids)]
    return sel, errs, opts


def first_failing(stdout):
    """The child's first-failing-file attribution: its 'FAIL <short name>' line (mut_runner_s1), else its first FILE line with a failure,
    else its first failing CASE line."""
    for l in stdout.splitlines():
        if l.startswith('FAIL '):
            return l[5:].strip()
    for l in stdout.splitlines():
        m = re.match(r'^FILE (\S+) state=COMPLETED tests=\d+ passed=\d+ failed=(\d+) errors=(\d+) ', l)
        if m and int(m.group(2)) + int(m.group(3)) > 0:
            return m.group(1)
    for l in stdout.splitlines():
        m = re.match(r'^CASE (\S+) FAIL ', l)
        if m:
            return m.group(1).split('/')[0]
    return None


def mutation_main(tool, mutants, commands, argv, equivalents=None, baseline=None, timeout=300, root=ROOT, success_marker=None,
                  kind='mutation', control_commands=None, auif_root=None, after_check=None, copy_ignore=COPY_IGNORE, oracle=None,
                  baseline_option=False, start_errors=()):
    """The successor mutation run (kind=mutation; R1 §2.1 to §2.7; T-0).  In order, each step failing closed:
      start checks (§2.8, §2.5) -> selection against the pinned universe (§2.2) -> preflight: every selected mutant's site present and
      matching its pinned SHA-256, and for text mutants exactly once (§2.1) -> start control (§2.3) -> each mutant in its own fresh copy
      -> end control -> end import check -> finish (§2.7).
    kind='sabotage' (T-K R5, decision K-1): the items are plants (PLANT lines, CAUGHT/MISSED, map_plant).  A plant may add a file
      (creates=True: the file must not exist, checked in the preflight).  control_commands(dest, [selected items]) gives the checks the
      unsabotaged tree runs at the start and at the end: the union of every selected plant's checks, so a check that fails on the clean
      tree stops the run before any plant.  M10's CAUGHT/MISSED human lines come before the PLANT lines.
    auif_root: the AUIF copy this process verified (DP-1.3 (a)); the children get it as APG_AUIF_ROOT, the one allowlist exception.
    after_check() -> [RunError]: checks made after the end control (for example that the run left the AUIF copy unchanged).
    baseline_option (decision W-1A.3 (a), owner 2026-11-01 06:22; only the nine tools it names pass True): --baseline runs only the start
      control of the full run (the same commands, a fresh copy, the same unparse round trip), executes no mutant and prints no RESULT line
      (it is not a mutation run); it prints the CONTROL line and, only when the control passes, M10's marker BASELINE OK.  Exit 0 when the
      control passes, 1 when it fails, 3 when it times out, 2 for a tool error (the start checks, the pins, the copy).
    oracle: a JSON value naming the kill oracle (for m8_mutants_s1, its two tier lists: decision M8-T), pinned with the list; a run whose
      oracle differs from the pinned one is EXPECTED_COUNT_MISMATCH (exit 2).
    mutants: [Mutant] in the tool's order.  commands(work, mutant or None) -> [(label, cmd)] (the kill oracle).  baseline(work): applied to
    the control copies (for AST tools, the same unparse round trip as the mutants, without the mutation).  A timeout and a crash are never
    kills (DP-2.1 (a)).  --pin writes the tool's universe and site hashes to tools/expected_counts.json with a change record."""
    equivalents = equivalents or {}
    LIST_KEY = 'mutation_lists' if kind == 'mutation' else 'plant_lists'   # §2.2: mutant lists and plant lists pinned apart
    by_id = {m.id: m for m in mutants}
    if len(by_id) != len(mutants):
        return refuse_run(kind, tool, [m.id for m in mutants], RunError('MUTANT_IDS_DUPLICATED', tool))
    universe = [m.id for m in mutants]
    sel, sel_errs, opts = _parse_selection(argv, universe)
    if opts['baseline'] and not baseline_option:
        opts['baseline'] = False
        sel_errs.append(RunError('SELECTION_INVALID', 'unknown argument --baseline'))
    if opts['baseline']:
        if kind != 'mutation' or opts['list'] or opts['pin'] or len(sel) != len(universe) or sel_errs:
            return emit(['RUN_ERROR SELECTION_INVALID --baseline takes no selection, --list or --pin'] + [e.line() for e in sel_errs], 2)
        return _baseline_only(tool, mutants, commands, baseline, timeout, root, auif_root, copy_ignore, oracle)
    if opts['list']:
        return emit(universe, 0)
    if opts['pin']:
        if sel_errs or not opts['reason'] or not opts['cause']:
            return emit(['RUN_ERROR SELECTION_INVALID --pin needs no selection and a --reason and --cause'], 2)
        doc, _ = load_pins()
        old = doc.get(LIST_KEY, {}).get(tool)
        new = {'ids': universe, 'ids_sha256': sha256_lines(universe), 'sites': {m.id: {'file': m.relpath, 'site_sha256': m.site_sha256()}
                                                                              for m in mutants}}
        if oracle is not None:
            new['oracle'] = oracle
        if old == new:
            return emit(['PINS unchanged for %s' % tool], 0)
        ml = dict(doc.get(LIST_KEY, {}))
        ml[tool] = new
        d = write_pins(dict(doc, **{LIST_KEY: ml}), opts['reason'], opts['cause'],
                       [{'entry': LIST_KEY + '/' + tool, 'old': None if old is None else {'count': len(old['ids']), 'ids_sha256': old['ids_sha256']},
                         'new': dict({'count': len(universe), 'ids_sha256': new['ids_sha256']}, **({'oracle': oracle} if oracle is not None else {}))}])
        return emit(['PINS version %d %s %d %s ids_sha256 %s' % (d['version'], tool, len(universe), 'mutants' if kind == 'mutation' else 'plants', new['ids_sha256'])], 0)
    # the tool set its path and imported tools.evkit before loading the M10 definitions (and any trusted module they import), so the
    # preloaded set is the start-up snapshot (as for cases_main)
    preloaded = PRELOADED_AT_EVKIT_IMPORT
    lines, errs = start(root, preloaded=preloaded)
    errs += sel_errs + list(start_errors)
    set_phase('control_start')   # amendment 2, reading 6: from the run's start until the start control's outcome is fixed
    run_id = opts['run_id']
    human = []
    # selection against the pins (§2.2): the tool's universe must equal the pinned one
    try:
        pins, _ = load_pins()
        pin = pins.get(LIST_KEY, {}).get(tool)
        if pin is None:
            errs.append(RunError('MUTATION_LIST_NOT_PINNED' if kind == 'mutation' else 'PLANT_LIST_NOT_PINNED', tool))
        elif pin['ids'] != universe or pin['ids_sha256'] != sha256_lines(universe):
            errs.append(RunError('EXPECTED_COUNT_MISMATCH', '%s universe %d pinned %d' % (tool, len(universe), len(pin['ids']))))
        elif pin.get('oracle') != oracle:
            errs.append(RunError('EXPECTED_COUNT_MISMATCH', '%s oracle differs from the pinned oracle' % tool))
    except RunError as e:
        errs.append(e)
        pin = None
    if errs:
        out, code = finish_items(kind, tool, run_id, sel or universe, {}, run_errors=errs, preflight='NOT_RUN', control_start='NOT_RUN',
                                 not_run_cause='run_error')
        return emit(lines + out, code)
    lines.append('SELECTED %d ids_sha256 %s' % (len(sel), sha256_lines(sel)))
    lines.append(limit_line(timeout))
    # preflight (§2.1): every selected mutant's site present and matching its pin; text mutants exactly once
    pre_errs = []
    for mid in sel:
        m = by_id[mid]
        if pin['sites'].get(mid, {}).get('site_sha256') != m.site_sha256() or pin['sites'][mid].get('file') != m.relpath:
            pre_errs.append(RunError('PREFLIGHT_INVALID_TARGET', '%s:site_differs_from_pin' % mid))
            human.append('PREFLIGHT FAILED %s: its site differs from the pinned site' % mid)
    text = [(m.id, m.relpath, m.text_old, None, m.occurrences) for m in (by_id[x] for x in sel) if m.text_old is not None]
    te, th = preflight_text(text, root)
    pre_errs += te
    human += th
    for m in (by_id[x] for x in sel):
        if m.creates and os.path.lexists(os.path.join(root, m.relpath)):
            pre_errs.append(RunError('PREFLIGHT_INVALID_TARGET', '%s:file_exists' % m.id))
            human.append('PREFLIGHT FAILED %s: the file it adds already exists: %s' % (m.id, m.relpath))
    # P2-S3 / P3-S01 / P4-S14 / P5-S07: the mutation is dry-run on the source for every selected mutant before any work, so a mutate() that
    # raises (or changes nothing) stops the run with every mutant NOT_RUN, instead of failing inside a worker
    srcs = {}
    for m in (by_id[x] for x in sel):
        if m.creates or m.relpath == '' or any(e.detail.startswith(m.id + ':') for e in pre_errs):
            continue
        try:
            if m.relpath not in srcs:
                with open(os.path.join(root, m.relpath), encoding='utf-8') as fh:
                    srcs[m.relpath] = fh.read()
            out_src = m.apply(srcs[m.relpath])
            reason = None if out_src != srcs[m.relpath] else 'mutation_changes_nothing'
        except Exception as e:
            reason = 'mutate_raised'
        if reason:
            pre_errs.append(RunError('PREFLIGHT_INVALID_TARGET', '%s:%s' % (m.id, reason)))
            human.append('PREFLIGHT FAILED %s: %s' % (m.id, reason.replace('_', ' ')))
    if pre_errs:
        out, code = finish_items(kind, tool, run_id, sel, {}, run_errors=pre_errs, preflight='FAIL', control_start='NOT_RUN',
                                 not_run_cause='preflight_failed')
        return emit(lines + human + out, code)
    workdir = tempfile_dir(tool)
    control_times = {}
    try:
        def control_cmds(dest):
            if baseline:
                baseline(dest)
            if control_commands is not None:
                return control_commands(dest, [by_id[x] for x in sel])
            return commands(dest, None)
        env = clean_env(workdir, auif_root=auif_root) if auif_root else clean_env(workdir)
        cs, cl, cerr = control(root, workdir, 'start', control_cmds, env, timeout, ignore=copy_ignore)
        lines += cl
        for part in cl[0].split(' '):
            if '=' in part and part.endswith('s') and part.split('=')[0] not in ('cause',):
                try:
                    control_times[('start', part.split('=')[0])] = float(part.split('=')[1][:-1])
                except ValueError:
                    pass
        if cerr:
            errs.append(cerr)
        if cs != 'PASS':
            out, code = finish_items(kind, tool, run_id, sel, {}, run_errors=errs, control_start=cs,
                                     not_run_cause='run_stopped' if CANCEL.set else 'control_start_%s' % cs)
            return emit(lines + out, code)
        outcomes = {}
        timeouts = []
        # F.1 and F.2: the run stops starting items when the disk floor is reached at an item's copy (stop_ev) or a signal is caught;
        # the phase F.2 records is the first item in flight, 'between', or (once the last item's outcome is fixed) 'control_end'
        stop_ev = _threading.Event()
        disk = []
        flight = []
        flock = _threading.Lock()
        order = {x: i for i, x in enumerate(sel)}
        begun = [0]

        def phase_now():
            if flight:
                set_phase(min(flight, key=order.get))
            else:
                set_phase('control_end' if begun[0] >= len(sel) else 'between')

        def begin(mid):
            with flock:
                if CANCEL.set or stop_ev.is_set():
                    return False
                flight.append(mid)
                begun[0] += 1
                phase_now()
            return True

        def end(mid):
            with flock:
                if mid in flight:
                    flight.remove(mid)
                    phase_now()

        def one(mid):
            m = by_id[mid]
            if not begin(mid):
                return mid, None, None
            work = os.path.join(workdir, 'm_' + re.sub(r'[^A-Za-z0-9_.-]', '_', mid))
            try:
                try:
                    fresh_copy(root, work, ignore=copy_ignore)
                except RunError as e:
                    if e.code != 'ENV_DISK_BELOW_FLOOR':
                        raise
                    stop_ev.set()
                    disk.append(e.detail)
                    shutil.rmtree(work, ignore_errors=True)
                    end(mid)
                    return mid, ('INDETERMINATE', 'run_stopped'), None
                p = os.path.join(work, m.relpath)
                if m.creates:
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    with open(p, 'x', encoding='utf-8') as fh:
                        fh.write(m.apply(None))
                elif m.text_old is None and m.relpath == '':   # a plant that edits the copy itself (apply(work))
                    m.apply(work)
                else:
                    with open(p, encoding='utf-8') as fh:
                        src = fh.read()
                    with open(p, 'w', encoding='utf-8') as fh:
                        fh.write(m.apply(src))
            except Exception as e:
                shutil.rmtree(work, ignore_errors=True)
                end(mid)
                return mid, ('ITEM_ERROR', 'worker_exception'), None   # P2-S3 (R4): the worker's exception is this item's error, never the run's crash
            try:
                outcome, label, timings, out = run_sequence(commands(work, m), env, work, timeout, unit=mid, stop=stop_ev.is_set,
                                                            on_end=lambda: end(mid))
            finally:
                shutil.rmtree(work, ignore_errors=True)
                end(mid)
            if outcome == 'TIMEOUT':
                (o, cause), tline = classify_timeout(kind, mid, label, timeout, control_times)
                return mid, (o, cause), tline
            if kind == 'sabotage':
                o, cause = map_plant(outcome, label)
                judge = getattr(m, 'judge', None)   # a check that names one test inside a file: CAUGHT only if that test failed
                if o == 'CAUGHT' and judge is not None:
                    verdict = judge(out)
                    if verdict is not None:
                        o, cause = verdict
            else:
                o, cause = map_mutant(outcome, (first_failing(out) or label) if outcome == 'CHILD_FAILED' else label,
                                      equivalent=bool(equivalents.get(mid)))
            return mid, (o, re.sub(r'[^A-Za-z0-9_.:-]', '_', cause or 'none')), None

        import concurrent.futures as _cf
        with _cf.ThreadPoolExecutor(max_workers=opts['jobs']) as ex:
            futs = [ex.submit(one, x) for x in sel]
            pending = set(futs)
            while pending:     # the main thread waits in short steps, so the F.2 handler runs promptly
                _done, pending = _cf.wait(pending, timeout=CANCEL_POLL_S)
        for fu in futs:
            mid, oc, tline = fu.result()
            if oc is not None:
                outcomes[mid] = oc
            if tline:
                timeouts.append(tline)
        stopped = bool(disk) or CANCEL.set
        if disk:
            errs.append(RunError('ENV_DISK_BELOW_FLOOR', 'items %s' % disk[0]))
            ce = 'NOT_RUN'
        else:
            ce, cel, cerr2 = control(root, workdir, 'end', control_cmds, env, timeout, ignore=copy_ignore)
            lines += cel
            if cerr2:
                errs.append(cerr2)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    ierrs, recs = import_identity(root, preloaded=preloaded)
    errs += ierrs
    if after_check is not None:
        with owning('run_end') as o_end:      # AM-5 (c): children of the after check (m8_mutants_s1's AUIF reverify) are the run's end
            errs += list(after_check())
        if o_end.leaked:
            errs.append(RunError('PROCESSES_LEFT', 'run_end'))
    for mid in sel:
        if outcomes.get(mid, ('',))[0] == 'EQUIVALENT':
            human.append('EQUIVALENT %s  -- %s' % (mid, equivalents[mid]))
    out, code = finish_items(kind, tool, run_id, sel, outcomes, run_errors=errs, control_end=ce,
                             not_run_cause='run_stopped' if stopped else 'not_started')
    k = next(i for i, l in enumerate(out) if l.startswith('RUN_ERROR') or l.startswith('RESULT'))
    f = parse_result_line(out[-1])[1]
    if kind == 'sabotage':
        before = ['%s %s %s -> %s' % (outcomes[x][0] if x in outcomes else 'NOT_RUN', x, by_id[x].what or '', by_id[x].check or '')
                  for x in sel]
        human.append('sabotage cases %d  caught %d  missed %d  indeterminate %d  item_errors %d  not_run %d'
                     % (f['selected'], f['caught'], f['missed'], f['indeterminate'], f['item_errors'], f['not_run']))
        return emit(lines + before + out[:k] + timeouts + ['IMPORT_END %s %s' % r for r in recs] + human + out[k:], code,
                    success_marker=success_marker)
    human.append('mutants %d  killed %d  documented-equivalent %d  survived %d  indeterminate %d  item_errors %d  not_run %d'
                 % (f['selected'], f['killed'], f['equivalent'], f['survived'], f['indeterminate'], f['item_errors'], f['not_run']))
    return emit(lines + out[:k] + timeouts + ['IMPORT_END %s %s' % r for r in recs] + human + out[k:], code, success_marker=success_marker)


def _baseline_only(tool, mutants, commands, baseline, timeout, root, auif_root, copy_ignore, oracle):
    """W-1A.3 (a): the start control of the tool's full run, and nothing else (see mutation_main, baseline_option)."""
    lines, errs = start(root, preloaded=PRELOADED_AT_EVKIT_IMPORT)
    lines.append(limit_line(timeout))
    set_phase('control_start')
    _SUP.run_without_result = True
    universe = [m.id for m in mutants]
    try:
        pins, _ = load_pins()
        pin = pins.get('mutation_lists', {}).get(tool)
        if pin is None:
            errs.append(RunError('MUTATION_LIST_NOT_PINNED', tool))
        elif pin['ids'] != universe or pin['ids_sha256'] != sha256_lines(universe) or pin.get('oracle') != oracle:
            errs.append(RunError('EXPECTED_COUNT_MISMATCH', '%s universe or oracle differs from the pin' % tool))
    except RunError as e:
        errs.append(e)
    if errs:
        return emit(lines + [e.line() for e in errs] + ['BASELINE NOT RUN: tool error'], 2)
    workdir = tempfile_dir(tool)
    try:
        def control_cmds(dest):
            if baseline:
                baseline(dest)
            return commands(dest, None)
        env = clean_env(workdir, auif_root=auif_root) if auif_root else clean_env(workdir)
        value, cl, cerr = control(root, workdir, 'start', control_cmds, env, timeout, ignore=copy_ignore, last=True)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    if CANCEL.cancelled():
        # F.2: the start control is this mode's only unit; an interrupt is INDETERMINATE (exit 3, W-1A.3 (a)), never a failure
        return emit(lines + cl + [e.line() for e in ([cerr] if cerr else [])] +
                    ['BASELINE INDETERMINATE: the start control was interrupted (no mutant was run)'], 3)
    if cerr:
        return emit(lines + cl + [cerr.line(), 'BASELINE NOT RUN: tool error'], 2)
    if value == 'PASS':
        return emit(lines + cl + ['baseline: the start control of the full run passed (no mutant was run)', 'BASELINE OK'], 0)
    if value == 'TIMEOUT':
        return emit(lines + cl + ['BASELINE INDETERMINATE: the start control timed out (no mutant was run)'], 3)
    return emit(lines + cl + ['BASELINE FAILED: the start control failed (no mutant was run)'], 1)


def tempfile_dir(tool):
    import tempfile
    return tempfile.mkdtemp(prefix='s1_%s_' % tool)


def ast_site(src, sites_fn, kind, idx):
    """The site text of an M10 AST mutant: '<kind>|<ast.unparse(node)>|<operand index>' (node and index from the M10 tool's _sites)."""
    import ast
    s = sites_fn(ast.parse(src))[kind]
    if idx >= len(s):
        return '%s|<missing>|%d' % (kind, idx)
    h = s[idx]
    node, op = (h if isinstance(h, tuple) else (h, -1))
    return '%s|%s|%d' % (kind, ast.unparse(node), op)


def unparse_baseline(relpaths):
    """For AST tools: the control applies the same ast.unparse round trip to the target files as the mutants get, without a mutation."""
    import ast

    def apply(work):
        for rel in relpaths:
            p = os.path.join(work, rel)
            with open(p, encoding='utf-8') as fh:
                text = ast.unparse(ast.parse(fh.read())) + '\n'
            with open(p, 'w', encoding='utf-8') as fh:
                fh.write(text)
    return apply

# ---------------------------------------------------------------------------------------------------------------------------------------
# Step 6: the cases driver every successor contract and corpus runner uses (kind=cases; T-K R5; P3-B04 / DP-4.3 (c))
# ---------------------------------------------------------------------------------------------------------------------------------------


def _case_token(text):
    return re.sub(r'[^A-Za-z0-9_.:-]', '_', str(text)) or '_'


def import_guard(module):
    """C.1: with import_guard('<module>'): the runner's module-level loads, moved into its guarded start path.  Any exception inside is
    RunError IMPORT_FAILED '<module> <type> <message>' (a new code), never a traceback."""
    return _ImportGuard(module)


class _ImportGuard:
    def __init__(self, module):
        self.module = module

    def __enter__(self):
        return self

    def __exit__(self, t, e, tb):
        if t is None or issubclass(t, RunError) or not issubclass(t, Exception):
            return False
        raise RunError('IMPORT_FAILED', '%s %s %s' % (self.module, t.__name__, one_line(str(e))[:200] or '-')) from e


_PRESTART = None


def guarded_load(tool, kind, load, root=None, run_id='run'):
    """C.1 for the fault runners and the 18 mutation and sabotage successors: the start checks run first (start()), then the tool's
    module-level loads (load(), using import_guard), then (amendment 3, AM3-1 (a)) the import identity check of what the load imported.
    A start error (AM3-1 (b): the load is then never called), a load failure (RUN_ERROR IMPORT_FAILED) or an identity error is refused
    here in C.1's form: every pinned item NOT_RUN cause=run_error, preflight=NOT_RUN, control_start=NOT_RUN, one RESULT line, exit 2.
    Returns None when all passed: the main's own start() then returns this same start result once (the checks are not run twice)."""
    global _PRESTART
    root = root or ROOT
    lines, errs = start(root, preloaded=PRELOADED_AT_EVKIT_IMPORT)
    if not errs:
        # amendment 3, AM3-1 (b): the load runs only after start checks that passed
        try:
            load()
        except RunError as e:
            errs = [e]
        else:
            # AM3-1 (a): the identity of what the load imported, checked at once, before any item
            errs = import_identity(root, preloaded=PRELOADED_AT_EVKIT_IMPORT)[0]
            if not errs:
                # the main's own start() returns this start result once (the checks are not run twice)
                _PRESTART = (lines, errs)
                return None
    try:
        ids = load_pins()[0]['mutation_lists' if kind == 'mutation' else 'plant_lists'][tool]['ids']
    except Exception:
        ids = []
    out, code = finish_items(kind, tool, run_id, list(dict.fromkeys(ids)), {}, run_errors=errs, preflight='NOT_RUN',
                             control_start='NOT_RUN', not_run_cause='run_error')
    return emit(lines + out, code)


def _case_unit_outcome(res, forms):
    """The K.2 and AM2-1 precedence for one forked case unit: (state, cause, value).  Interrupted, timeout, child_error (message or
    status 70), bad_result and crash are decided first; only a message that passed every validation step can be processes_left
    (amendment 2, AM2-1 (d); AM-6 (b))."""
    how, kv = parse_forked_message(res, forms)
    if how == 'interrupted':
        return 'INDETERMINATE', 'interrupted', None
    if how == 'timeout':
        return 'INDETERMINATE', 'timeout', None
    if how == 'child_error' or (how == 'ok' and kv[0] == 'child_error'):
        return 'ITEM_ERROR', 'child_error', None
    if how in ('bad_result', 'crash'):
        return 'INDETERMINATE', how, None
    return 'MESSAGE', None, kv


# amendment 5, S17 (b): a candidate factory spec is a dotted module name, one colon, and one attribute name; anything else (a missing
# part, a second colon, a space, a path) is a step 3 refusal, SELECTION_INVALID '<option> must be module:attr'
FACTORY_SPEC = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*:[A-Za-z_][A-Za-z0-9_]*\Z')


def cases_main(tool, enumerate_cases, run_case, argv, candidate_options=(), success_marker=None, human_label='contract cases',
               root=ROOT, load=None, batch=None):
    """The successor contract and corpus run (kind=cases, RESULT v=3).
    enumerate_cases(candidate) -> [(suite, case_id)] in order: the cases the harness defines (never the candidate).
    run_case(candidate, suite, case_id) -> (ok, detail): one case, run by the trusted harness against the candidate (or the reference).
      An exception inside it is the code under test failing (FAIL cause=exception_<Type>), never a pass.
    candidate_options: the option names that take a 'module:attr' candidate factory (for example ('--factory',)); --path gives the
      candidate directory.  The trusted harness is imported before the candidate; the candidate path is appended, never first; a
      candidate of a trusted name is refused (DP-4.3 (c), §2.5).
    Selection: --suite NAME (repeatable) and --only ID1,ID2 select a subset; with neither, every pinned case.  The case inventory per
    suite is pinned (§2.2); a case the pins do not list, or a pinned case not found, is a RUN_ERROR.  --pin writes the inventory.
    Corrective pass 2:
    - A.1's order: (1) the start checks, process supervision included; (2) the pins; (3) the selection, resolved from the pins (an
      argument error is a step 3 refusal, amendment 2 reading 10); (4) the guarded imports, load() (C); (5) the candidate; (6) the
      inventory comparison; (7) the cases; (8) the end checks.  A refusal at steps 1 to 3 has no resolved selection (suites=-); from
      step 4 on, the resolved selection is kept, its cases NOT_RUN.
    - load(): the runner's moved module-level loads, under import_guard; returns {'enumerate_cases': f, 'run_case': g} or
      {'batch': h}, which replace the arguments of the same names.
    - K.2: each selected case is a forked unit under P (CASE_ITEM_TIMEOUT_S), whose child calls the unchanged run_case.
    - Amendment 2, AM2-1: batch(candidate) -> [[suite, case id, ok, detail], ...] is the 7 batch runners' one harness call, which both
      lists and runs every case: one forked unit for steps 6 and 7, started only when steps 1 to 5 refused nothing, with no selection
      applied to it; the inventory comparison and each selected case's verdict are made in the parent from its validated message."""
    opts = {'path': None, 'suites': [], 'only': None, 'run_id': 'run', 'pin': False, 'reason': '', 'cause': '', 'factories': {}}
    argerrs = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ('--path', '--suite', '--only', '--run-id', '--reason', '--cause') + tuple(candidate_options):
            if i + 1 >= len(argv):
                argerrs.append(RunError('SELECTION_INVALID', 'missing value for %s' % a))
                break
            v = argv[i + 1]
            i += 1
            if a == '--path':
                opts['path'] = v
            elif a == '--suite':
                opts['suites'].append(v)
            elif a == '--only':
                opts['only'] = [x for x in v.split(',') if x]
            elif a == '--run-id':
                opts['run_id'] = v
            elif a == '--reason':
                opts['reason'] = v
            elif a == '--cause':
                opts['cause'] = v
            else:
                opts['factories'][a] = v
        elif a == '--pin':
            opts['pin'] = True
        else:
            argerrs.append(RunError('SELECTION_INVALID', 'unknown argument %s' % a))
        i += 1
    # the candidate options' consistency is part of the selection (step 3, amendment 2 reading 10)
    if opts['factories'] and not opts['path']:
        argerrs.append(RunError('SELECTION_INVALID', 'a candidate factory needs --path (its own top-level package)'))
    elif opts['path'] and not opts['factories']:
        argerrs.append(RunError('SELECTION_INVALID', '--path without a candidate factory'))
    for opt_name, spec in opts['factories'].items():
        if not FACTORY_SPEC.match(spec):     # amendment 5, S17 (b) (owner, 2026-11-08 12:47, option A): exactly module:attr
            argerrs.append(RunError('SELECTION_INVALID', '%s must be module:attr' % opt_name))
    preloaded = PRELOADED_AT_EVKIT_IMPORT
    # (1) the start checks (amendment 3, AM3-1 (c): also for --pin, which then runs the guarded load, the post-load identity check and the
    # harness only after checks that passed, and writes no pin after any refusal)
    lines, errs = start(root, preloaded=preloaded)
    lines = list(lines) + ([] if opts['pin'] else [limit_line(CASE_ITEM_TIMEOUT_S)])
    set_phase('between')
    resolved = None          # (suites, sel_pairs) once step 3 has passed
    pinned = {}
    # (2) the pins (not for --pin, which writes them)
    if not errs and not opts['pin']:
        try:
            pins, _ = load_pins()
            pinned = pins.get('case_inventories', {}).get(tool)
            if pinned is None:
                errs.append(RunError('CASE_INVENTORY_NOT_PINNED', tool))
                pinned = {}
        except RunError as e:
            errs.append(e)
    # (3) the selection, from the pins
    if not errs and not opts['pin'] and not argerrs:
        e3 = []
        suites = list(dict.fromkeys(opts['suites'])) or sorted(pinned)
        for s_ in opts['suites']:
            if s_ not in pinned:
                e3.append(RunError('SELECTION_INVALID', 'unknown suite %s' % s_))
        sel_pairs = [(s_, c) for s_ in suites if s_ in pinned for c in pinned[s_]['ids']]
        if opts['only'] is not None:
            unknown = [x for x in opts['only'] if x not in {c for _, c in sel_pairs}]
            if unknown:
                e3.append(RunError('SELECTION_INVALID', 'unknown cases %s' % ','.join(unknown[:5])))
            sel_pairs = [(s_, c) for s_, c in sel_pairs if c in set(opts['only'])]
        if e3:
            errs += e3
        else:
            resolved = ([x for x in suites if x in pinned], sel_pairs)
    errs += argerrs
    go = resolved is not None or (opts['pin'] and not errs)
    # (4) the guarded imports
    if go and load is not None:
        try:
            got = load()
        except RunError as e:
            errs.append(e)
        else:
            # amendment 3, AM3-1 (a): the identity of what the load imported, checked at once, before the candidate, the inventory and any case
            errs += import_identity(root, preloaded=preloaded)[0]
            enumerate_cases = got.get('enumerate_cases', enumerate_cases)
            run_case = got.get('run_case', run_case)
            batch = got.get('batch', batch)
    # (5) the candidate, loaded after the trusted harness, its path appended
    candidate = {}
    cpaths = ()
    if go and not errs and opts['factories']:
        cpaths = (os.path.realpath(opts['path']),)
        for opt_name, spec in opts['factories'].items():
            modname, attr = spec.split(':', 1)
            mod, cerrs = load_candidate(opts['path'], modname, root)
            errs += cerrs
            if mod is not None and not cerrs:
                try:
                    candidate[opt_name] = getattr(mod, attr)
                except AttributeError:
                    errs.append(RunError('CANDIDATE_IMPORT_FAILED', '%s has no %s' % (modname, attr)))
    # (6) the inventory: in the parent from the static list, or (AM2-1) from the batch unit's validated message
    outcomes, human, extra = {}, [], []
    found, rows, batch_fail = None, None, None
    tmp = None
    if go and not errs:
        import tempfile as _tf
        tmp = _tf.mkdtemp(prefix='s1_cases_')
    try:
        if go and not errs:
            env = clean_env(tmp)
            if batch is not None:
                set_phase(('%s/%s' % resolved[1][0]) if resolved and resolved[1] else 'between')

                def child(batch=batch, candidate=candidate):
                    out = []
                    for r in batch(candidate):
                        out.append([r[0], r[1], r[2], r[3]])
                    return {'results': out}

                def rows_ok(v):
                    if not isinstance(v, list):
                        return False
                    seen = set()
                    for r in v:
                        if not (isinstance(r, list) and len(r) == 4 and isinstance(r[0], str) and isinstance(r[1], str)
                                and isinstance(r[2], bool) and isinstance(r[3], str)):
                            return False
                        k = (_case_token(r[0]), _case_token(r[1]))
                        if k in seen:
                            return False
                        seen.add(k)
                    return True
                forms = {'results': rows_ok, 'exception': lambda v: isinstance(v, str), 'child_error': lambda v: isinstance(v, str)}
                try:
                    res = run_forked('%s:batch' % tool, child, CASE_ITEM_TIMEOUT_S, env, last=True)
                except RunError as e:
                    errs.append(e)
                    res = None
                if res is not None:
                    state, cause, kv = _case_unit_outcome(res, forms)
                    if state != 'MESSAGE':
                        batch_fail = (state, cause)
                        if cause == 'timeout':
                            extra.append('TIMEOUT %s:batch cmd=batch limit=%ss control_start=NA control_end=NA' % (tool, CASE_ITEM_TIMEOUT_S))
                    elif kv[0] == 'exception':
                        errs.append(RunError('CASES_ENUMERATION_FAILED', _case_token(kv[1])))
                    else:
                        rows = kv[1]
                        found = [(r[0], r[1]) for r in rows]
                        if res['leaked']:
                            batch_fail = ('LEAK', None)
            else:
                try:
                    found = list(enumerate_cases(candidate))
                except Exception as e:
                    errs.append(RunError('CASES_ENUMERATION_FAILED', type(e).__name__))
        inv = {}
        for suite, cid in (found or []):
            inv.setdefault(_case_token(suite), []).append(_case_token(cid))
        if opts['pin']:
            if errs or batch_fail or found is None or not opts['reason'] or not opts['cause']:
                return emit([e.line() for e in errs] + ['RUN_ERROR SELECTION_INVALID --pin needs a --reason and a --cause, and a run '
                                                        'of the harness that completed'], 2)
            doc, _ = load_pins()
            new = {s_: {'ids': ids, 'ids_sha256': sha256_lines(ids)} for s_, ids in inv.items()}
            old = doc.get('case_inventories', {}).get(tool)
            if old == new:
                return emit(['PINS unchanged for %s' % tool], 0)
            ci = dict(doc.get('case_inventories', {}))
            ci[tool] = new
            d = write_pins(dict(doc, case_inventories=ci), opts['reason'], opts['cause'],
                           [{'entry': 'case_inventories/' + tool, 'old': None if old is None else {s_: len(v['ids']) for s_, v in old.items()},
                             'new': {s_: len(v['ids']) for s_, v in new.items()}}])
            return emit(['PINS version %d %s %d suites %d cases' % (d['version'], tool, len(new), sum(len(v['ids']) for v in new.values()))], 0)
        if found is not None and not errs:
            for s_ in sorted(set(inv) | set(pinned)):
                have, want = inv.get(s_, []), pinned.get(s_, {}).get('ids', [])
                if sorted(have) != sorted(want) or len(set(have)) != len(have):
                    errs.append(RunError('CASE_INVENTORY_MISMATCH', '%s found=%d pinned=%d' % (s_, len(have), len(want))))
        sel_pairs = resolved[1] if resolved else []
        # (7) the cases
        if resolved and not errs:
            if batch is not None:
                if batch_fail is not None:
                    st, cause = batch_fail if batch_fail[0] != 'LEAK' else ('INDETERMINATE', 'processes_left')
                    for (s_, c) in sel_pairs:
                        outcomes['%s/%s' % (s_, c)] = (st, cause)
                else:
                    by = {(_case_token(r[0]), _case_token(r[1])): r for r in rows}
                    for (s_, c) in sel_pairs:
                        r = by[(s_, c)]
                        outcomes['%s/%s' % (s_, c)] = ('PASS', 'ok') if r[2] else ('FAIL', 'expected_outcome_differs')
                        human.append(('PASS ' if r[2] else 'FAIL ') + '%s/%s' % (s_, c) + ('' if r[2] else '  -> ' + one_line(r[3])[:300]))
            else:
                orig = {(_case_token(s_), _case_token(c)): (s_, c) for s_, c in found}
                forms = {'ok': lambda v: False, 'exception': lambda v: isinstance(v, str), 'child_error': lambda v: isinstance(v, str)}
                for n, (s_, c) in enumerate(sel_pairs):
                    item = '%s/%s' % (s_, c)
                    if CANCEL.set:
                        break
                    set_phase(item)
                    rs, rc = orig.get((s_, c), (s_, c))

                    def child(rs=rs, rc=rc):
                        try:
                            ok, detail = run_case(candidate, rs, rc)
                        except Exception as e:
                            return {'exception': type(e).__name__}
                        return {'ok': bool(ok), 'detail': str(detail)}
                    try:
                        res = run_forked(item, child, CASE_ITEM_TIMEOUT_S, env, last=(n == len(sel_pairs) - 1))
                    except RunError as e:
                        errs.append(e)
                        break
                    # the ok form is two keys: validated here (P.8 step 4)
                    how, kv = 'x', None
                    if res['how'] == 'message' and not res['trailing']:
                        try:
                            obj = _json.loads(res['message'].decode('utf-8'))
                        except (UnicodeDecodeError, ValueError):
                            obj = None
                        if (isinstance(obj, dict) and set(obj) == {'ok', 'detail'} and isinstance(obj['ok'], bool)
                                and isinstance(obj['detail'], str)):
                            how, kv = 'ok', ('ok', obj)
                    if how == 'ok':
                        state = 'MESSAGE'
                    else:
                        state, cause, kv = _case_unit_outcome(res, forms)
                    if state == 'MESSAGE' and kv[0] == 'ok':
                        ok, detail = kv[1]['ok'], kv[1]['detail']
                        outcomes[item] = ('PASS', 'ok') if ok else ('FAIL', 'expected_outcome_differs')
                        human.append(('PASS ' if ok else 'FAIL ') + item + ('' if ok else '  -> ' + one_line(detail)[:300]))
                    elif state == 'MESSAGE' and kv[0] == 'exception':
                        outcomes[item] = ('FAIL', 'exception_%s' % _case_token(kv[1]))
                        human.append('FAIL %s  -> raised %s' % (item, kv[1]))
                    elif state == 'MESSAGE':
                        outcomes[item] = ('INDETERMINATE', 'bad_result')
                    else:
                        outcomes[item] = (state, cause)
                        if cause == 'timeout':
                            extra.append('TIMEOUT %s cmd=case limit=%ss control_start=NA control_end=NA' % (item, CASE_ITEM_TIMEOUT_S))
                    if res['leaked'] and state == 'MESSAGE':
                        outcomes[item] = ('INDETERMINATE', 'processes_left')
                set_phase('between')
        # (8) the end checks
        if go and not opts['pin']:
            ierrs, recs = import_identity(root, preloaded=preloaded, candidate_paths=cpaths)
            errs += ierrs
            lines += ['IMPORT_END %s %s' % r for r in recs]
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    stopped = CANCEL.set
    sel = ['%s/%s' % p_ for p_ in (resolved[1] if resolved else [])]
    rsuites = resolved[0] if resolved else None
    ci_sha = sha256_lines(['%s/%s' % (s_, c) for s_ in sorted(rsuites or []) for c in pinned[s_]['ids']])
    out, code = finish_items('cases', tool, opts['run_id'], sel, outcomes, run_errors=errs,
                             not_run_cause='run_error' if errs else ('run_stopped' if stopped else 'not_started'),
                             suites=rsuites, case_inventory_sha256=ci_sha)
    k = next(i for i, l in enumerate(out) if l.startswith('RUN_ERROR') or l.startswith('RESULT'))
    nfail = sum(1 for o in outcomes.values() if o[0] != 'PASS')
    human.append('%s %d  failed %d' % (human_label, len(outcomes), nfail))
    return emit(lines + out[:k] + extra + human + out[k:], code, success_marker=success_marker)


def env_lines(record):
    """The ENV lines that record the environment (§2.8)."""
    return ['ENV interpreter %s' % record['interpreter'], 'ENV version %s' % record['version'],
            'ENV interpreter_sha256 %s' % record['interpreter_sha256'],
            'ENV flags isolated=%d no_site=%d' % (record['flags_isolated'], record['flags_no_site']),
            'ENV sys_path %s' % ' '.join(record['sys_path']), 'ENV cwd %s' % record['cwd'],
            'ENV free_disk_bytes %d' % record['free_disk_bytes']]


def tool_stem():
    """The running tool's stem (sys.argv[0]), as the supervisor list names it."""
    a0 = os.path.basename(sys.argv[0] or '')
    return a0[:-3] if a0.endswith('.py') else a0


def start(root=ROOT, allow_site=False, interpreter_sha256=None, disk_floor_bytes=10 * 1024 ** 3, preloaded=None, supervisor=None):
    """The start sequence every stage 1 runner uses (§2.8 then §2.5): scrub inherited variables, set sys.path[0], run the start
    checks, record the environment, check import identity.  Returns (lines, errors): the ENV and IMPORT lines to print, and the run
    errors (a non-empty list means the run must stop before any work, every item NOT_RUN, exit 2).
    Corrective pass 2: the F.2 handler is installed; a supervisor (AM-6 (c); supervisor=None means 'from the tool's name', and
    child_unittest_runner declares itself only when it verifies an AUIF copy, AM-2) declares itself and refuses with
    ENV_NO_PROCESS_SUPERVISION when P.2's containment cannot be set up."""
    global _PRESTART
    if _PRESTART is not None:        # C.1: guarded_load already ran these checks before the tool's loads
        r, _PRESTART = _PRESTART, None
        return list(r[0]), list(r[1])
    if preloaded is None:
        preloaded = ()
    CANCEL.install()
    stem = tool_stem()
    if supervisor is None:
        supervisor = stem in SUPERVISOR_STEMS and stem != 'child_unittest_runner'
    lines = scrub_inherited()
    set_path0(root)
    errs = env_check(root, allow_site=allow_site, interpreter_sha256=interpreter_sha256, disk_floor_bytes=disk_floor_bytes)
    if supervisor:
        declare_supervisor(stem)
        errs = errs + supervision_errors()
    lines += env_lines(env_record(root))
    ierrs, recs = import_identity(root, preloaded=preloaded)
    return lines + import_lines(recs), errs + ierrs


def _self_check(argv):
    """python3 -I -S tools/evkit.py --self-check [--floor-bytes N] [--interpreter-sha256 H] [--allow-site]
    Runs the start sequence and prints its ENV, IMPORT and RUN_ERROR lines; exit 2 on any run error, else 0.  Used by the step 1 tests."""
    floor = 10 * 1024 ** 3
    isha = None
    allow_site = '--allow-site' in argv
    if '--floor-bytes' in argv:
        floor = int(argv[argv.index('--floor-bytes') + 1])
    if '--interpreter-sha256' in argv:
        isha = argv[argv.index('--interpreter-sha256') + 1]
    lines, errs = start(ROOT, allow_site=allow_site, interpreter_sha256=isha, disk_floor_bytes=floor)
    probe = os.environ.get('EVKIT_PROBE_IMPORT')  # never set by clean_env; the tests set it only to prove a decoy is not imported
    if probe:
        import importlib
        try:
            m = importlib.import_module(probe)
            lines.append('PROBE %s %s' % (probe, _module_file(m)))
        except Exception as e:
            lines.append('PROBE %s failed %s' % (probe, type(e).__name__))
        ierrs, recs = import_identity(ROOT)
        errs += ierrs
        lines += import_lines(recs)
    for line in lines:
        print(line)
    for e in errs:
        print(e.line())
    return 2 if errs else 0


if __name__ == '__main__':
    if sys.argv[1:2] == ['--self-check']:
        sys.exit(_self_check(sys.argv[2:]))
    if sys.argv[1:2] == ['--update-pins']:
        a = sys.argv[2:]
        reason = a[a.index('--reason') + 1] if '--reason' in a else ''
        cause = a[a.index('--cause') + 1] if '--cause' in a else ''
        profiles = [a[i + 1] for i, x in enumerate(a) if x == '--profile']
        files = [a[i + 1] for i, x in enumerate(a) if x == '--file'] or None
        scrub_inherited()
        set_path0(ROOT)
        d = update_pins(reason, cause, profiles, files=files)
        print('PINS version %d content_sha256 %s' % (d['version'], d['change_records'][-1]['content_sha256']))
        sys.exit(0)
    if sys.argv[1:2] == ['--list-test-ids'] and len(sys.argv) == 3:
        scrub_inherited()
        set_path0(ROOT)
        for tid in list_test_ids(sys.argv[2]):
            print('ID ' + tid)
        sys.exit(0)
    print('evkit is a library; its commands are --self-check and --list-test-ids <relpath>', file=sys.stderr)
    sys.exit(2)

# ---------------------------------------------------------------------------------------------------------------------------------------
# Step 7: kind=sabotage (T-K R5, decision K-1, 2026-10-31 13:18)
# ---------------------------------------------------------------------------------------------------------------------------------------


def text_plant(pid, what, path, old, new, check, occurrences=None):
    """One M10 sabotage case as a plant.  path None means M10's 'add a file' form: old is the new file's path and new its text."""
    if path is None:
        return Mutant(pid, old, 'create|%s|%s' % (old, new), (lambda _src, new=new: new), creates=True, what=what, check=check)
    if occurrences is None:
        apply = (lambda src, old=old, new=new: src.replace(old, new, 1))
    else:
        apply = (lambda src, old=old, new=new: src.replace(old, new))
    return Mutant(pid, path, old, apply, occurrences=occurrences, text_old=old, what=what, check=check)


def regression_sabotage_main(tool, m10_tool, regression_tool, argv, timeout=1800, root=ROOT, success_marker=None, cases=None):
    """The successor of an M10 sabotage tool whose cases are (id, what, path or None, old, new, step) and whose check is the step of an
    M10 regression tool (sabotage_m7, _m71, _m72, _m73, sabotage_f67 to _f674).  The cases are M10's own, loaded from the M10 tool and
    unchanged; the regression tool is M10's, unchanged and out of stage 1's scope.  What changes (K-1, kind=sabotage):
      - the preflight: each target text occurs exactly once (§2.1; M10 required at least once and replaced the first);
      - the start and end controls: the unsabotaged tree runs every selected plant's step and must pass every one, else no plant runs;
      - a step's result is read from its own PASS/FAIL line and summary (regression_step_classifier); anything else is not a catch;
      - a timeout is INDETERMINATE (DP-2.1 (a)), never CAUGHT or MISSED;
      - exact selection (--only, --ids), one PLANT line per selected plant, one RESULT v=2 kind=sabotage line."""
    M = load_tool_module(m10_tool, root)
    items = [text_plant(c[0], c[1], c[2], c[3], c[4], c[5]) for c in (cases if cases is not None else M.CASES)]

    def cmd(work, step):
        return (step, child_cmd(os.path.join(work, 'tools', regression_tool + '.py'), ['--step', step]),
                regression_step_classifier(step))

    def commands(work, plant):
        return [cmd(work, plant.check)]

    def control_commands(work, plants):
        steps = []
        for p in plants:
            if p.check not in steps:
                steps.append(p.check)
        return [cmd(work, s) for s in steps]
    argv = ['--ids' if a == '--only' else a for a in argv]   # M10's --only takes ids (comma-separated): exact ids, never prefixes
    return mutation_main(tool, items, commands, argv, timeout=timeout, root=root, success_marker=success_marker, kind='sabotage',
                         control_commands=control_commands)


def load_m10_prefix(name, stop, expected_sha256, root=ROOT):
    """Load the definitions of an M10 script that runs at import (no __main__ guard): the source up to the first line equal to `stop`,
    from the M10 file whose SHA-256 must equal expected_sha256 (else RunError M10_SOURCE_CHANGED), executed with sys.argv set to the
    script alone, so no option of the successor's command line reaches it (for example its '--path first' insertion, P3-B04)."""
    import types
    path = os.path.join(root, 'tools', name + '.py')
    with open(path, 'rb') as fh:
        data = fh.read()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise RunError('M10_SOURCE_CHANGED', '%s %s' % (name, hashlib.sha256(data).hexdigest()))
    src = data.decode('utf-8')
    lines = src.split('\n')
    if lines.count(stop) != 1:
        raise RunError('M10_SOURCE_CHANGED', '%s stop line found %d times' % (name, lines.count(stop)))
    prefix = '\n'.join(lines[:lines.index(stop)]) + '\n'
    mod = types.ModuleType(name + '_definitions')
    mod.__file__ = path
    saved = sys.argv
    sys.argv = [path]
    try:
        exec(compile(prefix, path, 'exec'), mod.__dict__)
    finally:
        sys.argv = saved
    return mod


def faults_main(tool, plants, run_reference, argv, success_marker=None, root=ROOT, total_label='faulty implementations'):
    """The successor of an M10 fault runner (kind=sabotage, decision K-1; T_tooling.md T-K R5).  plants: [(id, text, run, must_fail)]
    where run() -> the set of failed case ids for that faulty implementation and must_fail its M10 list of cases it must fail.
    run_reference() -> the set of failed case ids for the reference implementation, the start and end control: it must fail none.
      - pinned: the plant ids and each plant's must-fail list (§2.2, plant_lists);
      - preflight: every selected plant's must-fail list is non-empty and equals its pin;
      - CAUGHT: every listed case fails (M10: some case fails and every listed one does); MISSED otherwise;
      - an exception escaping a plant's whole run is ITEM_ERROR, never CAUGHT;
      - one RESULT v=2 kind=sabotage line; the M10 CAUGHT/MISSED lines are kept, before the PLANT lines."""
    import time
    by_id = {p[0]: p for p in plants}
    if len(by_id) != len(plants):
        return refuse_run('sabotage', tool, [p[0] for p in plants], RunError('MUTANT_IDS_DUPLICATED', tool))
    universe = [p[0] for p in plants]
    sel, sel_errs, opts = _parse_selection(argv, universe)
    if opts['list']:
        return emit(universe, 0)
    new = {'ids': universe, 'ids_sha256': sha256_lines(universe), 'must_fail': {p[0]: sorted(p[3]) for p in plants}}
    if opts['pin']:
        if sel_errs or not opts['reason'] or not opts['cause']:
            return emit(['RUN_ERROR SELECTION_INVALID --pin needs no selection and a --reason and --cause'], 2)
        doc, _ = load_pins()
        old = doc.get('plant_lists', {}).get(tool)
        if old == new:
            return emit(['PINS unchanged for %s' % tool], 0)
        pl = dict(doc.get('plant_lists', {}))
        pl[tool] = new
        d = write_pins(dict(doc, plant_lists=pl), opts['reason'], opts['cause'],
                       [{'entry': 'plant_lists/' + tool, 'old': None if old is None else {'count': len(old['ids'])}, 'new': {'count': len(universe)}}])
        return emit(['PINS version %d %s %d plants ids_sha256 %s' % (d['version'], tool, len(universe), new['ids_sha256'])], 0)
    preloaded = PRELOADED_AT_EVKIT_IMPORT
    lines, errs = start(root, preloaded=preloaded)
    errs += sel_errs
    run_id = opts['run_id']
    pin = None
    try:
        pins, _ = load_pins()
        pin = pins.get('plant_lists', {}).get(tool)
        if pin is None:
            errs.append(RunError('PLANT_LIST_NOT_PINNED', tool))
        elif pin['ids'] != universe or pin['ids_sha256'] != sha256_lines(universe):
            errs.append(RunError('EXPECTED_COUNT_MISMATCH', '%s universe %d pinned %d' % (tool, len(universe), len(pin['ids']))))
    except RunError as e:
        errs.append(e)
    if errs:
        out, code = finish_items('sabotage', tool, run_id, sel or universe, {}, run_errors=errs, preflight='NOT_RUN',
                                 control_start='NOT_RUN', not_run_cause='run_error')
        return emit(lines + out, code)
    lines.append('SELECTED %d ids_sha256 %s' % (len(sel), sha256_lines(sel)))
    pre, human = [], []
    for pid in sel:
        mf = sorted(by_id[pid][3])
        if not mf:
            pre.append(RunError('PREFLIGHT_INVALID_TARGET', '%s:no_must_fail_cases' % pid))
        elif pin['must_fail'].get(pid) != mf:
            pre.append(RunError('PREFLIGHT_INVALID_TARGET', '%s:must_fail_differs_from_pin' % pid))
    if pre:
        out, code = finish_items('sabotage', tool, run_id, sel, {}, run_errors=pre, preflight='FAIL', control_start='NOT_RUN',
                                 not_run_cause='preflight_failed')
        return emit(lines + out, code)

    lines.append(limit_line(FAULT_ITEM_TIMEOUT_S))
    # B (corrective pass 2): every plant and both controls are forked units under P (FAULT_ITEM_TIMEOUT_S); the message is
    # {"failed": [case ids]}, {"exception": "<type>"} or {"child_error": "<type>"}; a failed id must be a case of the paired case runner's
    # pinned inventory (P.8 step 5, amendment 2 reading 12)
    pair = FAULT_CASE_PAIRS.get(tool)
    known = None
    if pair is not None:
        known = {c for sv in pins.get('case_inventories', {}).get(pair, {}).values() for c in sv['ids']}

    def failed_ok(v):
        return isinstance(v, list) and all(isinstance(x, str) for x in v) and len(set(v)) == len(v) and (
            known is None or all(_case_token(x) in known for x in v))
    forms = {'failed': failed_ok, 'exception': lambda v: isinstance(v, str), 'child_error': lambda v: isinstance(v, str)}
    import tempfile as _tf
    tmp = _tf.mkdtemp(prefix='s1_faults_')
    env = clean_env(tmp)
    ctimes = {}

    def forked(uid, fn, last=False, on_end=None):
        def child():
            try:
                return {'failed': sorted(set(fn()))}
            except Exception as e:
                return {'exception': type(e).__name__}
        res = run_forked(uid, child, FAULT_ITEM_TIMEOUT_S, env, last=last, on_end=on_end)
        state, cause, kv = _case_unit_outcome(res, forms)
        return res, state, cause, kv

    def control_run(phase):
        set_phase('control_%s' % phase)
        if CANCEL.set:
            if phase == 'start':
                return 'FAIL', 'CONTROL start CONTROL_INTERRUPTED cause=interrupted'
            return 'NOT_RUN', None
        t0 = time.monotonic()
        res, state, cause, kv = forked('control_%s' % phase, run_reference, last=(phase == 'end'))
        secs = time.monotonic() - t0
        ctimes[(phase, 'reference')] = secs
        if cause == 'interrupted':
            if phase == 'start':
                return 'FAIL', 'CONTROL start CONTROL_INTERRUPTED cause=interrupted'
            return 'NOT_RUN', 'CONTROL end CONTROL_NOT_RUN cause=interrupted'
        if state == 'MESSAGE' and kv[0] == 'failed':
            value, cause = ('PASS', 'ok') if not kv[1] else ('FAIL', 'reference_failed_%d' % len(kv[1]))
        elif state == 'MESSAGE':
            value, cause = 'FAIL', 'exception_%s' % _case_token(kv[1])
        elif cause == 'timeout':
            value = 'TIMEOUT'
        else:
            value = 'FAIL'
        if res['leaked'] and state == 'MESSAGE':
            value, cause = 'FAIL', 'processes_left'
        if phase == 'start' and value == 'PASS':
            set_phase('between')
        try:
            free = shutil.disk_usage(root).free
        except OSError:
            free = -1
        return value, 'CONTROL %s CONTROL_%s cause=%s reference=%.3fs load=%.2f free_disk_bytes=%d' % (
            phase, value, cause, secs, load_and_disk(), free)
    outcomes, tlines, run_errs = {}, [], []
    try:
        set_phase('control_start')
        try:
            cs, cl = control_run('start')
        except RunError as e:
            cs, cl = 'FAIL', None
            run_errs.append(e)
        if cl:
            lines.append(cl)
        if cs != 'PASS':
            out, code = finish_items('sabotage', tool, run_id, sel, {}, run_errors=run_errs, control_start=cs,
                                     not_run_cause='run_stopped' if CANCEL.set else 'control_start_%s' % cs)
            return emit(lines + out, code)
        for n, pid in enumerate(sel):
            if CANCEL.set:
                break
            set_phase(pid)
            _, text, run, must = by_id[pid]
            last_item = n == len(sel) - 1
            try:
                res, state, cause, kv = forked(pid, run, on_end=(lambda: set_phase('control_end')) if last_item else
                                               (lambda: set_phase('between')))
            except RunError as e:
                run_errs.append(e)
                break
            if state == 'MESSAGE' and kv[0] == 'failed':
                failed = set(kv[1])
                ok = bool(failed) and set(must) <= failed
                outcomes[pid] = ('CAUGHT', 'listed_cases_fail') if ok else ('MISSED', 'none')
                human.append(('CAUGHT ' if ok else 'MISSED ') + '%s %s: failed %s; expected at least %s' % (pid, text, sorted(failed), list(must)))
                if res['leaked']:
                    outcomes[pid] = ('INDETERMINATE', 'processes_left')
            elif state == 'MESSAGE':
                outcomes[pid] = ('ITEM_ERROR', 'exception_%s' % _case_token(kv[1]))
                human.append('ITEM_ERROR %s %s: raised %s' % (pid, text, kv[1]))
            else:
                outcomes[pid] = (state, cause)
                if cause == 'timeout':
                    tlines.append(pid)
        ce, cel = 'NOT_RUN', None
        if not run_errs:       # a run error (ENV_THREADS_AT_FORK) stops the run; an interrupt is handled by control_run itself
            try:
                ce, cel = control_run('end')
            except RunError as e:
                run_errs.append(e)
        if cel:
            lines.append(cel)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for pid in tlines:
        lines.append(classify_timeout('sabotage', pid, 'reference', FAULT_ITEM_TIMEOUT_S, ctimes)[1])
    ierrs, recs = import_identity(root, preloaded=preloaded)
    out, code = finish_items('sabotage', tool, run_id, sel, outcomes, run_errors=run_errs + ierrs, control_end=ce,
                             not_run_cause='run_stopped' if CANCEL.set else ('run_error' if run_errs else 'not_started'))
    k = next(i for i, l in enumerate(out) if l.startswith('RUN_ERROR') or l.startswith('RESULT'))
    missed = sum(1 for o in outcomes.values() if o[0] != 'CAUGHT')
    return emit(lines + human + out[:k] + ['IMPORT_END %s %s' % r for r in recs] + ['%s %d  missed %d' % (total_label, len(sel), missed)]
                + out[k:], code, success_marker=success_marker)


FAULT_CASE_PAIRS = {'run_faults_s1': 'run_contracts_s1', 'run_m3_faults_s1': 'run_m3_contracts_s1', 'run_m5_faults_s1': 'run_m5_contracts_s1',
                    'run_m6_faults_s1': 'run_m6_contracts_s1', 'run_history_contract_s1': 'run_history_contract_s1'}


def static_summary_classifier(label='static checks'):
    """For an M10 static checker that ends with '<label> N  failed K' (tools/mie_static.py, T_tooling.md F9): CHILD_OK only for exactly
    one such line with K 0 and exit 0; CHILD_FAILED only for K > 0 and a non-zero exit; anything else is CRASH_NO_RESULT (never a catch)."""
    pat = re.compile(r'^%s (\d+)  failed (\d+)$' % re.escape(label))

    def classify(stdout, rc):
        hits = [pat.match(l) for l in stdout.splitlines() if pat.match(l)]
        if len(hits) != 1 or int(hits[0].group(1)) == 0:
            return 'CRASH_NO_RESULT'
        k = int(hits[0].group(2))
        if k == 0 and rc == 0:
            return 'CHILD_OK'
        if k > 0 and rc != 0:
            return 'CHILD_FAILED'
        return 'CRASH_NO_RESULT'
    return classify


def mie_sabotage_main(tool, m10_tool, regression_tool, argv, catalogue=None, root=ROOT, success_marker=None, timeout=1800):
    """The successor of sabotage_mie1 / sabotage_mie1_1 (kind=sabotage, K-1).  The plants are M10's CASES (id, what, path, old, new,
    target), loaded from the M10 tool and unchanged.  Each target is one of:
      - 'STATIC': M10's tools/mie_static.py, read by static_summary_classifier (F9);
      - 'Rnn': a step of M10's regression tool, read by regression_step_classifier (F9);
      - a test file name: run by tools/run_m2_tests_s1.py under the pinned caller profile run_m2_tests_s1@sabotage_tool (failfast,
        DP-2.3 F8), read from its RESULT v=2 line (M10 ran tools/run_m2_tests.py and parsed its summary).
    catalogue: the spec catalogue the plant ids must equal one to one, in order (M10's own check, kept as a run error)."""
    M = load_tool_module(m10_tool, root)
    cases = list(M.CASES)
    if catalogue is not None:
        import csv
        with open(os.path.join(root, catalogue), encoding='utf-8', newline='') as fh:
            ids = [r['mutant_id'] for r in csv.DictReader(fh)]
        if [c[0] for c in cases] != ids:
            return refuse_run('sabotage', tool, [c[0] for c in cases], RunError('CATALOGUE_MISMATCH', catalogue))
    items = [text_plant(c[0], c[1], c[2], c[3], c[4], c[5]) for c in cases]

    def cmd(work, target, run_id):
        if target == 'STATIC':
            return ('STATIC', child_cmd(os.path.join(work, 'tools', 'mie_static.py')), static_summary_classifier())
        if re.match(r'^R\d+[A-Z]?$', target):
            return (target, child_cmd(os.path.join(work, 'tools', regression_tool + '.py'), ['--step', target]),
                    regression_step_classifier(target))
        return (target, child_cmd(os.path.join(work, 'tools', 'run_m2_tests_s1.py'),
                                  ['-q', '--failfast', '--caller', 'sabotage_tool', '--run-id', run_id, target]))

    def commands(work, plant):
        return [cmd(work, plant.check, plant.id)]

    def control_commands(work, plants):
        seen = []
        for p in plants:
            if p.check not in seen:
                seen.append(p.check)
        return [cmd(work, t, 'control') for t in seen]
    argv = ['--ids' if a == '--only' else a for a in argv]
    return mutation_main(tool, items, commands, argv, timeout=timeout, root=root, success_marker=success_marker, kind='sabotage',
                         control_commands=control_commands)


# ---------------------------------------------------------------------------------------------------------------------------------------
# Step 9: the M8/M10 regression tools (P1-F6: 'builds its child environment from os.environ today; moves to clean_env(), §2.8')
# ---------------------------------------------------------------------------------------------------------------------------------------

REGRESSION_REDIRECTS = {   # M10 child -> (stage 1 successor, its arguments prefix, caller); judged by its RESULT v=2 line (CHILD_OK) and M10's marker
    'tools/run_m2_tests.py': ('tools/run_m2_tests_s1.py', ['--caller', 'wrapper']),
    'tools/run_m8_tests.py': ('tools/run_m8_tests_s1.py', ['--caller', 'wrapper']),
    'tools/run_regression_m8.py': ('tools/run_regression_m8_s1.py', []),
    'tools/run_regression_m81.py': ('tools/run_regression_m81_s1.py', []),
}


S1_BOUNDARY_TEST = 'tests_m8/test_m8_boundary.py'


def s1_manifest_view(root=ROOT):
    """Decision W-1A.2 (ii) (a) (owner, 2026-11-01 06:22): the frozen stage 1 manifest, validated by exactly amendment 2's validator
    (load_s1_manifest in tests_m8/test_m8_boundary.py, whose pinned file hash is checked first; its definitions are executed without the
    test's AUIF set-up, and nothing else of the test runs).  Returns (view, None) or (None, reason): view = {'modified': {path: (m10_sha256,
    s1_sha256)}, 'new': {path: s1_sha256}, 'manifest': path}.  Any rejection means no declaration is used."""
    import ast
    import csv as _csv
    path = os.path.join(root, S1_BOUNDARY_TEST)
    try:
        pins, _ = load_pins(os.path.join(root, 'tools', 'expected_counts.json'))
        want = pins['test_files'][S1_BOUNDARY_TEST]['sha256']
        with open(path, 'rb') as fh:
            data = fh.read()
    except (RunError, KeyError, OSError) as e:
        return None, 'VALIDATOR_UNAVAILABLE %s' % type(e).__name__
    if hashlib.sha256(data).hexdigest() != want:
        return None, 'VALIDATOR_CHANGED %s' % S1_BOUNDARY_TEST
    tree = ast.parse(data.decode('utf-8'), path)
    keep = [n for n in tree.body if isinstance(n, (ast.Import, ast.Assign, ast.FunctionDef))
            or (isinstance(n, ast.ClassDef) and n.name == 'S1ManifestRejected')]
    ns = {'__name__': 's1_manifest_validator', 'HERE_ROOT': root}
    exec(compile(ast.Module(body=keep, type_ignores=[]), path, 'exec'), ns)
    try:
        ns['load_s1_manifest'](root, ns['manifest']())
    except ns['S1ManifestRejected'] as e:
        return None, str(e)
    except OSError as e:
        return None, 'MANIFEST_UNREADABLE %s' % type(e).__name__
    with open(os.path.join(root, ns['S1_MANIFEST']), encoding='utf-8', newline='') as fh:
        rows = [r for r in _csv.reader(fh)][1:]
    view = {'modified': {}, 'new': {}, 'manifest': ns['S1_MANIFEST']}
    for sec, p, st, m10, s1, _, _ in rows:
        if sec == 'changed':
            if st == 'modified':
                view['modified'][p] = (m10, s1)
            else:
                view['new'][p] = s1
    return view, None


def _s1_step(M, step, root):
    """Wrap one M10 regression step so that it also permits exactly what the frozen stage 1 manifest declares (W-1A.2 (ii) (a)): while it
    runs, a file the manifest declares modified is seen with its M10 hash only if its contents have exactly the recorded stage 1 hash; a
    file it declares new is not seen only if its contents have exactly the recorded stage 1 hash; the manifest itself is not seen (its
    exact-path exemption).  Everything else is the M10 step unchanged, so an undeclared change, or a declared file with other contents,
    still fails."""
    orig = M.STEPS[step]

    def wrapped():
        view, why = s1_manifest_view(root)
        if view is None:
            return False, 'the frozen stage 1 manifest was rejected, so the step was not judged (%s)' % why, []
        osh, ofiles = M.sh, M.files

        def sh(p):
            h = osh(p)
            d = view['modified'].get(p)
            return d[0] if d is not None and h == d[1] else h

        def files():
            return [p for p in ofiles() if p != view['manifest'] and not (p in view['new'] and osh(p) == view['new'][p])]
        M.sh, M.files = sh, files
        try:
            ok, what, detail = orig()
        finally:
            M.sh, M.files = osh, ofiles
        return ok, what + (' [APG-M11-S1, decision W-1A.2 (ii) (a): also permitted, and only at their exact recorded stage 1 hashes, the %d '
                           'modified and %d new files the frozen stage 1 manifest declares, and the manifest itself]'
                           % (len(view['modified']), len(view['new']))), detail
    M.STEPS[step] = wrapped


class _HoldLast:
    """Amendment 2, AM2-2 (a): standard output with its last non-empty line held back, so that the P lines can be printed before the
    tool's own final line (and the INTERRUPTED record after it).  Everything else passes through at once."""

    def __init__(self, real):
        self.real, self.buf = real, ''

    def write(self, data):
        self.buf += data
        parts = self.buf.split('\n')
        idx = max((i for i, l in enumerate(parts) if l.strip()), default=None)
        if idx is not None and idx > 0:
            self.real.write('\n'.join(parts[:idx]) + '\n')
            self.buf = '\n'.join(parts[idx:])
        return len(data)

    def flush(self):
        self.real.flush()

    def __getattr__(self, name):
        return getattr(self.real, name)


def finish_no_result_run(held, real, exit_code):
    """Amendment 2, AM2-2 (a): the end of a run of one of the 6 supervisors with no RESULT line.  P's run errors (RUN_ERROR lines), the
    CLEANUP lines, CLEANUP_SUMMARY and SIGNAL_AFTER_COMPLETION, then the tool's own held last line, then INTERRUPTED as the last line;
    an interrupted run exits 3.  Returns the exit code."""
    errs = _SUP.close_run()
    rec = CANCEL.record()
    pre = [e.line() for e in errs] + _SUP.final_lines() + ([rec] if rec and rec.startswith('SIGNAL_AFTER_COMPLETION') else [])
    for l in pre:
        real.write(l + '\n')
    if held:
        real.write(held if held.endswith('\n') else held + '\n')
    if rec and rec.startswith('INTERRUPTED'):
        real.write(rec + '\n')
        exit_code = 3
    real.flush()
    return exit_code


def _start_watcher(current):
    """Amendment 2, AM2-2 (b): the regression successors' watcher thread.  It blocks SIGINT and SIGTERM in itself, so the main thread's
    handler always receives them; every 0.2 s (F.2) it checks the flag; once set, it signals the live members of the in-flight step's
    owner phase (current[0]) as P.5 steps 4 and 5 do: SIGTERM, then SIGKILL after T_GRACE_CANCELLED.  Its scans, 0.1 s apart, do not run
    the reaper; it never waits on or reaps any child and never prints.  The step's own wrapper completes P.5's cleanup in the main thread."""
    def watch():
        try:
            _signal.pthread_sigmask(_signal.SIG_BLOCK, {_signal.SIGINT, _signal.SIGTERM})
        except (AttributeError, OSError, ValueError):
            pass
        while not CANCEL.set:
            _time.sleep(CANCEL_POLL_S)
        handled = set()
        while True:
            o = current[0]
            if o is not None and id(o) not in handled:
                handled.add(id(o))
                termed = set()
                t_end = _time.monotonic() + T_GRACE_CANCELLED
                while _time.monotonic() < t_end:
                    live = _SUP.scan([o], reap=False)[o]
                    for i in sorted(live - termed):
                        termed.add(i)
                        _SUP.signal(i, _signal.SIGTERM)
                    if not live:
                        break
                    _time.sleep(SCAN_INTERVAL_S)
                for i in sorted(_SUP.scan([o], reap=False)[o]):
                    _SUP.signal(i, _signal.SIGKILL)
            _time.sleep(CANCEL_POLL_S)
    t = _threading.Thread(target=watch, name='apg-watcher', daemon=True)
    t.start()
    return t


def regression_successor_main(m10_tool, argv, root=ROOT, s1_manifest_steps=()):
    """The successor of an M10 regression tool (run_regression_m8, _m81, _m81r1, _m8r2, _m10; P1-F6).  M10's steps, checks and output
    format are kept unchanged (no result kind is assigned to these tools, T_tooling.md T-K); what changes:
      - the start sequence (§2.8, §2.5) runs first, and this process's own environment is replaced by the allowlist (clean_env), so every
        child, including the register generators the steps start directly, inherits only that;
      - every Python child this successor starts itself starts with -I -S (the children M10's in-process code starts, R03's and the
        AUIF verification's, keep M10's command and environment: AM-5 (b), open finding 13; mistake 20 corrected this docstring);
      - a child that has a stage 1 successor is redirected to it (REGRESSION_REDIRECTS; the route proof, R1 §3.3) and passes only with a
        valid RESULT line with status OK (CHILD_OK) and M10's marker, which the successor prints unchanged ('Ran N tests' for the M10
        unittest step is read as RESULT tests=N);
      - M10's unittest step (run_regression_m10 R07) runs through tools/child_unittest_runner.py under its pinned profile
        child_unittest_runner@run_regression_m10_s1 (full, DP-2.3 F6).
    Corrective pass 2: every child is a unit under P (a leak: '(INCOMPLETE: processes left)'); each M10 step is wrapped and owns the
    children its in-process code starts (AM-5 (c)); F.2's cancellation with amendment 2's AM2-2 (b) (a step not started is
    '(INCOMPLETE: interrupted)', a child unit in flight is stopped, a blocked in-process step's children are signalled by the watcher);
    AM2-2 (a)'s output (M10's last line held back; INTERRUPTED the last line; exit 3); AM2-2 (d) (a redirected successor that was
    interrupted is '(INCOMPLETE: interrupted)', and this successor then exits 3)."""
    import tempfile
    lines, errs = start(root, preloaded=PRELOADED_AT_EVKIT_IMPORT)
    listing = not argv or argv[0] == '--list'
    if not listing:          # a listing is not a run: no LIMIT line and no P lines
        _SUP.run_without_result = True
        lines = list(lines) + [limit_line(3600)]
    for l in lines:
        print(l)
    if errs:
        for e in errs:
            print(e.line())
        print('\nchecks 0  failed 0\nRUN_ERRORS: the start sequence failed; no step ran')
        return 2
    tmp = tempfile.mkdtemp(prefix='s1_regr_')
    env = clean_env(tmp)
    os.environ.clear()
    os.environ.update(env)
    M = load_tool_module(m10_tool, root)
    tool_self = m10_tool + '_s1'
    for step in s1_manifest_steps:      # decision W-1A.2 (ii) (a)
        _s1_step(M, step, root)
    child_interrupted = []
    seq = [0]

    def run(args, what, expect, timeout=3600, py=True):
        args = list(args)
        if args and args[0] == '-I':
            args = args[1:]
        cmd, classify = None, None
        if args[:4] == ['-B', '-W', 'ignore', '-m'] and args[4] == 'unittest':
            cmd = child_cmd(os.path.join(root, 'tools', 'child_unittest_runner.py'),
                            ['--caller', 'run_regression_m10_s1', '--mode', 'full', '--run-id', tool_self] + args[5:])
            want = re.match(r'^Ran (\d+) tests$', expect)
            classify = ('tests', int(want.group(1)) if want else None)
        elif args and args[0] in REGRESSION_REDIRECTS:
            succ, pre = REGRESSION_REDIRECTS[args[0]]
            cmd = child_cmd(os.path.join(root, succ), pre + args[1:])
            classify = ('result', None) if succ.endswith(('run_m2_tests_s1.py', 'run_m8_tests_s1.py')) else ('marker', None)
        else:
            cmd = child_cmd(os.path.join(root, args[0]), args[1:]) if args and args[0].endswith('.py') else [sys.executable, '-I', '-S'] + args
        if CANCEL.set:
            return False, what + ' (INCOMPLETE: interrupted)', []
        seq[0] += 1
        r = run_unit('%s:%d' % (CANCEL.phase, seq[0]), cmd, timeout, env, root)
        if r.how == 'launch_error':
            raise OSError(r.stderr)          # as subprocess.run raised it before (unchanged)
        if r.how == 'timeout':
            return False, what + ' (INCOMPLETE: cut off by the time limit)', []
        if r.how == 'interrupted':
            return False, what + ' (INCOMPLETE: interrupted)', []
        out = r.stdout + r.stderr
        tail = out.strip().splitlines()[-1:]
        if r.leaked:
            return False, what + ' (INCOMPLETE: processes left)', tail
        if classify is not None and classify[0] == 'marker' and is_interrupted_child(r.returncode, r.stdout):
            child_interrupted.append(1)      # AM2-2 (d): the redirected successor was interrupted; this one exits 3 at its end
            return False, what + ' (INCOMPLETE: interrupted)', tail
        if classify is None or classify[0] == 'marker':
            return r.returncode == 0 and expect in out, what, tail
        outcome, kind, fields, _ = classify_child(r.stdout, r.returncode if r.returncode >= 0 else 2)
        ok = outcome == 'CHILD_OK'
        if classify[0] == 'tests' and classify[1] is not None:
            ok = ok and fields is not None and fields.get('tests') == classify[1]
        elif classify[0] == 'result':
            ok = ok and expect in out
        return ok, what, tail
    M.run = run
    a = list(argv)
    names = list(M.STEPS)
    if a and a[0] == '--all':
        last_step = names[-1] if names else None
    elif len(a) >= 2 and a[0] == '--step':
        last_step = a[1]
    else:
        last_step = None
    current = [None]

    def wrap(k, fn):
        def step():
            if CANCEL.set:      # AM2-2 (b): a step not started once the flag is set is not run
                return False, '%s (INCOMPLETE: interrupted)' % k, []
            set_phase(k)
            was_set = CANCEL.set
            with owning(k) as o:
                current[0] = o
                try:
                    ok, what, detail = fn()
                finally:
                    current[0] = None
            fixed = CANCEL.fix(last=(k == last_step))
            if CANCEL.set and not was_set and not fixed:
                return False, '%s (INCOMPLETE: interrupted)' % (what if 'INCOMPLETE' not in what else what.split(' (INCOMPLETE')[0]), detail
            if o.leaked and 'INCOMPLETE' not in what:
                return False, what + ' (INCOMPLETE: processes left)', detail
            return ok, what, detail
        return step
    for k in names:
        M.STEPS[k] = wrap(k, M.STEPS[k])
    _start_watcher(current)
    saved = sys.argv
    sys.argv = [os.path.join(root, 'tools', tool_self + '.py')] + list(argv)
    real = sys.stdout
    hold = _HoldLast(real)
    sys.stdout = hold
    try:
        code = M.main()
    finally:
        sys.stdout = real
        sys.argv = saved
        shutil.rmtree(tmp, ignore_errors=True)
    if child_interrupted and code != 2:
        code = 3
    if listing:
        real.write(hold.buf)
        real.flush()
        return code
    return finish_no_result_run(hold.buf, real, code)


# ---------------------------------------------------------------------------------------------------------------------------------------
# W-1 (owner decision, 2026-10-31 20:57; APG_D14_STAGE1_DECISION_W1_REV2.md draft 2 §1): the successor wrappers' result (kind=wrapper),
# the CHECK and EXCLUDED records, OK_WITH_EXCLUSIONS, the canonical hashing (§1.8) and the consumer rule (§1.9)
# ---------------------------------------------------------------------------------------------------------------------------------------

CHECK_OUTCOMES = ('PASS', 'FAIL', 'INDETERMINATE', 'ITEM_ERROR', 'NOT_RUN')
CHECK_SOURCES = ('child', 'wrapper')
EXCLUSION_REASONS = ('regression_against_its_prior_release', 'records_check_of_its_own_release', 'wrapper_of_an_earlier_release')
GROUP_ID = re.compile(r'^G[0-9]{2,3}$')
EMPTY_SHA256 = hashlib.sha256(b'').hexdigest()
FILE_RE = re.compile(r'^FILE (\S+) state=(\S+) tests=(\d+) passed=(\d+) failed=(\d+) errors=(\d+) skipped=(\d+) tests_not_run=(\d+) '
                     r'file_sha256=([0-9a-f]{64}) ids_sha256=([0-9a-f]{64})$')
CHECK_RE = re.compile(r'^CHECK (\S+) (\S+) source=(\S+) exit=(\S+) marker=(\S+) command_sha256=([0-9a-f]{64}) tool_sha256=([0-9a-f]{64}) '
                      r'marker_sha256=([0-9a-f]{64})$')
EXCLUDED_RE = re.compile(r'^EXCLUDED (\S+) NOT_RUN_HISTORICAL release=(\S+) reason=(\S+) command_sha256=([0-9a-f]{64})$')


def group_id(n):
    """§1.8: the group's 1-based position in the M10 wrapper's run order, as a token: G01, G02, ..."""
    return 'G%02d' % n


def command_sha256(args):
    """§1.8: the SHA-256 of the UTF-8 bytes of the arguments (interpreter and its flags excluded), joined by single spaces, no newline.
    An argument that is empty or contains whitespace is refused (RunError PIN_INVALID), so the join is never ambiguous."""
    args = list(args)
    if not args:
        raise RunError('PIN_INVALID', 'empty command')
    for a in args:
        if not isinstance(a, str) or not a or any(ch.isspace() for ch in a):
            raise RunError('PIN_INVALID', 'argument empty or with whitespace: %r' % (a,))
    return hashlib.sha256(' '.join(args).encode('utf-8')).hexdigest()


def text_sha256(text):
    """§1.8: the SHA-256 of a text's exact UTF-8 bytes, no newline added (marker_sha256; the empty string for a group with no marker)."""
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()


def check_identity(gid, source, cmd_sha, tool_sha, marker_sha):
    """§1.8: one item of checks_sha256: '<group_id> <source> <command_sha256> <tool_sha256> <marker_sha256>' (identity only)."""
    return '%s %s %s %s %s' % (gid, source, cmd_sha, tool_sha, marker_sha)


def check_line(gid, outcome, source, exit_code, marker, cmd_sha, tool_sha, marker_sha):
    return 'CHECK %s %s source=%s exit=%s marker=%s command_sha256=%s tool_sha256=%s marker_sha256=%s' % (
        gid, outcome, source, '-' if exit_code is None else str(exit_code), marker, cmd_sha, tool_sha, marker_sha)


def excluded_line(gid, release, reason, cmd_sha):
    return 'EXCLUDED %s NOT_RUN_HISTORICAL release=%s reason=%s command_sha256=%s' % (_tok(gid, 'group id'), _tok(release, 'release'),
                                                                                      _tok(reason, 'reason'), cmd_sha)


def check_outcome(returncode, marker_seen, timed_out=False, launch_error=False, pin_mismatch=False, interrupted_child=False):
    """§1.2 (b): the fixed outcome of a CHECK whose child is an M10 tool with no result kind.  exit 0 with the marker -> PASS; exit 1 ->
    FAIL (a traceback exits 1 too, and is a failure, never a pass); exit 0 without the marker -> ITEM_ERROR; any other exit, a signal,
    a launch error, or a tool or command that does not match its pin -> ITEM_ERROR; a timeout -> INDETERMINATE.
    Returns (outcome, exit field, marker field).
    Amendment 2, AM2-2 (d): an interrupted no-kind child (exit 3 and its last line the INTERRUPTED record, is_interrupted_child) is
    INDETERMINATE, exit=3, its marker field as observed; every other exit keeps the mapping above."""
    if pin_mismatch or launch_error:
        return 'ITEM_ERROR', None, '-'
    if timed_out:
        return 'INDETERMINATE', None, '-'
    if interrupted_child and returncode == 3:
        return 'INDETERMINATE', 3, ('seen' if marker_seen else 'absent')
    marker = 'seen' if marker_seen else 'absent'
    if returncode == 0:
        return ('PASS' if marker_seen else 'ITEM_ERROR'), 0, marker
    if returncode == 1:
        return 'FAIL', 1, marker
    return 'ITEM_ERROR', (returncode if returncode is not None and returncode >= 0 else None), marker


def group_inventory_sha256(entries):
    """T-0 R6: a wrapper FILE line's file_sha256, the hash of the group's pinned inventory: sha256_lines over '<name> <sha256>' items
    (for a kind=tests child, its test files with their pinned file hashes; for a kind=cases or kind=sabotage child, one item, the tool
    with its pinned case_inventory_sha256 or ids_sha256)."""
    return sha256_lines(['%s %s' % (n, h) for n, h in entries])


class WrapperGroup:
    """One S group's result as the wrapper reports it: its FILE line and the child lines it relays (TEST, CASE or PLANT, unchanged)."""

    def __init__(self, gid, state, relayed, counts, file_sha256, observed_ids, cause=''):
        self.gid, self.state, self.relayed, self.counts = gid, state, list(relayed), dict(counts)
        self.file_sha256, self.observed_ids, self.cause = file_sha256, list(observed_ids), cause


def wrapper_group_from_child(gid, inventory_sha, outcome, stdout, kind):
    """T-0 R4 to R6 for one S group: only a valid child result (CHILD_OK or CHILD_FAILED) is reported as COMPLETED, with its TEST, CASE or
    PLANT lines relayed unchanged; CHILD_EVIDENCE_ERROR and LAUNCH_ERROR give ITEM_ERROR; CHILD_INDETERMINATE, TIMEOUT and CRASH_NO_RESULT
    give INDETERMINATE.  kind=cases and kind=sabotage use the adopted mapping: tests = items, passed = PASS or CAUGHT, failed = FAIL or
    MISSED, errors = skipped = 0."""
    zero = dict(tests=0, passed=0, failed=0, errors=0, skipped=0)
    if outcome in ('CHILD_EVIDENCE_ERROR', 'LAUNCH_ERROR'):
        return WrapperGroup(gid, 'ITEM_ERROR', [], zero, inventory_sha, [], cause=outcome.lower())
    if outcome not in ('CHILD_OK', 'CHILD_FAILED'):
        return WrapperGroup(gid, 'INDETERMINATE', [], zero, inventory_sha, [], cause=outcome.lower())
    rel, ids, c = [], [], dict(zero)
    for l in stdout.splitlines():
        if kind == 'tests' and l.startswith('TEST '):
            m = re.match(r'^TEST (\S+?)::(\S+) (\S+)$', l)
            rel.append(l)
            if m.group(3) != 'NOT_RUN_AFTER_FAILURE':
                ids.append('%s::%s' % (m.group(1), m.group(2)))
                c['tests'] += 1
                c[{'PASS': 'passed', 'FAIL': 'failed', 'ERROR': 'errors', 'SKIP': 'skipped'}[m.group(3)]] += 1
        elif kind in ITEM_LINE and l.startswith(ITEM_LINE[kind] + ' '):
            m = re.match(r'^\S+ (\S+) (\S+) cause=\S+$', l)
            rel.append(l)
            ids.append(m.group(1))
            c['tests'] += 1
            if m.group(2) in ('PASS', 'CAUGHT'):
                c['passed'] += 1
            elif m.group(2) in ('FAIL', 'MISSED'):
                c['failed'] += 1
    return WrapperGroup(gid, 'COMPLETED', rel, c, inventory_sha, ids)


def finish_wrapper(tool, run_id, records, run_errors=()):
    """W-1 §1.2 to §1.4: the wrapper's lines and exit code.  records, in M10's group order: ('file', WrapperGroup) for S groups (state may
    also be 'NOT_RUN'), ('check', (gid, outcome, source, exit, marker, cmd_sha, tool_sha, marker_sha)) for P and W groups, and
    ('excluded', (gid, release, reason, cmd_sha)) for H groups.  Returns (lines, exit_code)."""
    tool, run_id = _tok(tool, 'tool'), _tok(run_id, 'run')
    errs = list(run_errors) + _SUP.close_run()
    lines, files, checks, excl = [], [], [], []
    for typ, r in records:
        if typ == 'file':
            g = r
            lines += g.relayed
            c = g.counts if g.state == 'COMPLETED' else dict(tests=0, passed=0, failed=0, errors=0, skipped=0)
            lines.append('FILE %s state=%s tests=%d passed=%d failed=%d errors=%d skipped=%d tests_not_run=0 file_sha256=%s ids_sha256=%s'
                         % (g.gid, g.state, c['tests'], c['passed'], c['failed'], c['errors'], c['skipped'], g.file_sha256,
                            sha256_lines(g.observed_ids if g.state == 'COMPLETED' else [])))
            files.append((g, c))
        elif typ == 'check':
            gid, outcome, source, ex, marker, cs, ts, ms = r
            lines.append(check_line(gid, outcome, source, ex, marker, cs, ts, ms))
            checks.append((outcome, check_identity(gid, source, cs, ts, ms)))
        else:
            gid, release, reason, cs = r
            line = excluded_line(gid, release, reason, cs)
            lines.append(line)
            excl.append(line)
    st = {s: sum(1 for g, _ in files if g.state == s) for s in FILE_STATES}
    tot = {k: sum(c[k] for g, c in files if g.state == 'COMPLETED') for k in ('tests', 'passed', 'failed', 'errors', 'skipped')}
    co = {o: sum(1 for x, _ in checks if x == o) for o in CHECK_OUTCOMES}
    f = dict(tot, tool=tool, mode='full', run=run_id, groups_selected=len(files) + len(checks) + len(excl), files_selected=len(files),
             files_started=st['COMPLETED'] + st['INDETERMINATE'] + st['ITEM_ERROR'], files_completed=st['COMPLETED'],
             files_indeterminate=st['INDETERMINATE'], files_errored=st['ITEM_ERROR'], files_not_run=st['NOT_RUN'],
             files_skipped_after_failure=st['SKIPPED_AFTER_FAILURE'], checks_selected=len(checks), checks_passed=co['PASS'],
             checks_failed=co['FAIL'], checks_indeterminate=co['INDETERMINATE'], checks_errored=co['ITEM_ERROR'], checks_not_run=co['NOT_RUN'],
             excluded_historical=len(excl), run_errors=len(errs),
             inventory_sha256=sha256_lines(['%s %s' % (g.gid, g.file_sha256) for g, _ in files]),
             checks_sha256=sha256_lines([i for _, i in checks]), exclusions_sha256=sha256_lines(excl))
    status = derive_status('wrapper', f)
    f.update(status=status, exit=STATUS_EXIT[status])
    return lines + [e.line() for e in errs] + [result_line('wrapper', f)], STATUS_EXIT[status]


def _check_wrapper(f, lines, pins, selected):
    """The checker for kind=wrapper (W-1 §1.2 to §1.4, §1.8).  pins (optional): {'files': {gid: file_sha256}, 'checks': {gid: identity},
    'exclusions': {gid: EXCLUDED line}, 'classes': {gid: class}} for the wrapper (wrapper_check_pins); selected (optional): the selected
    group ids in order.  Amendment 3, AM3-4: a child CHECK INDETERMINATE exit=3 is accepted only for a group whose class is given as N or B."""
    p = []
    files, checks, excl, pending, order = [], [], [], [], []
    # amendment 5, S16 (owner, 2026-11-08 12:47, option A): the groups whose unit has a CLEANUP record (P.5 step 8); a leak makes a
    # check INDETERMINATE whatever its exit (P.6), so for these groups an INDETERMINATE CHECK is accepted in the forms below
    cleaned = {l.split(' ', 2)[1] for l in lines if l.startswith('CLEANUP ') and len(l.split(' ', 2)) == 3}
    for l in lines:
        if l.startswith(('TEST ', 'CASE ', 'PLANT ')):
            pending.append(l)
            continue
        if l.startswith('FILE '):
            m = FILE_RE.match(l)
            if not m or m.group(2) not in FILE_STATES or not GROUP_ID.match(m.group(1)):
                p.append('malformed FILE line: %s' % l)
                pending = []
                continue
            vals = tuple(int(m.group(i)) for i in range(3, 9))
            files.append((m.group(1), m.group(2)) + vals + (m.group(9), m.group(10), pending))
            order.append(m.group(1))
            pending = []
        elif l.startswith('CHECK '):
            if pending:
                p.append('child lines before a CHECK line')
                pending = []
            m = CHECK_RE.match(l)
            if (not m or not GROUP_ID.match(m.group(1)) or m.group(2) not in CHECK_OUTCOMES or m.group(3) not in CHECK_SOURCES
                    or not re.match(r'^(-|[0-9]+)$', m.group(4)) or m.group(5) not in ('seen', 'absent', '-')):
                p.append('malformed CHECK line: %s' % l)
                continue
            gid, outcome, source, ex, marker = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
            cls = ((pins or {}).get('classes') or {}).get(gid)
            if source == 'child':
                ok = {'PASS': ex == '0' and marker == 'seen', 'FAIL': ex == '1',
                      # amendment 3, AM3-4: INDETERMINATE with exit=3 and an observed marker only for a class N group (AM2-2 (d),
                      # an interrupted no-kind child) or a class B group (W-1A.3 (a), a --baseline that exited 3), by the group's
                      # pinned class given in pins['classes']; with no class for the group the form is refused (fail closed)
                      'INDETERMINATE': ex == '-' or (ex == '3' and marker in ('seen', 'absent') and cls in ('N', 'B')),
                      'NOT_RUN': ex == '-' and marker == '-',
                      'ITEM_ERROR': not (ex == '0' and marker == 'seen') and ex != '1'}[outcome]
            else:
                ok = ex == '-' and marker == '-' and outcome in ('PASS', 'FAIL', 'ITEM_ERROR', 'NOT_RUN')
            if not ok and outcome == 'INDETERMINATE' and gid in cleaned and (source == 'child' or (ex == '-' and marker == '-')):
                ok = True      # S16: the group's unit leaked and was cleaned up (its CLEANUP record is in this output)
            if not ok:
                if source == 'child' and outcome == 'INDETERMINATE' and ex == '3' and marker in ('seen', 'absent'):
                    p.append('CHECK %s outcome INDETERMINATE exit=3 needs a pinned class N or B (class: %s)' % (gid, cls or 'not given'))
                else:
                    p.append('CHECK %s outcome %s contradicts exit=%s marker=%s' % (gid, outcome, ex, marker))
            checks.append((gid, outcome, check_identity(gid, source, m.group(6), m.group(7), m.group(8))))
            order.append(gid)
        elif l.startswith('EXCLUDED '):
            if pending:
                p.append('child lines before an EXCLUDED line')
                pending = []
            m = EXCLUDED_RE.match(l)
            if not m or not GROUP_ID.match(m.group(1)) or not TOKEN.match(m.group(2)) or m.group(3) not in EXCLUSION_REASONS:
                p.append('malformed EXCLUDED line: %s' % l)
                continue
            excl.append((m.group(1), l))
            order.append(m.group(1))
    if pending:
        p.append('child lines after the last FILE line')
    if len(set(order)) != len(order):
        p.append('duplicate group ids')
    if selected is not None and list(selected) != order:
        p.append('group ids differ from the selection')
    if f['mode'] != 'full':
        p.append('a wrapper is mode=full')
    tot = dict(tests=0, passed=0, failed=0, errors=0, skipped=0)
    for (gid, state, tests, passed, failed, errors, skipped, tnr, fsha, isha, rel) in files:
        if tnr != 0:
            p.append('FILE %s tests_not_run=%d (a wrapper child is full)' % (gid, tnr))
        if state != 'COMPLETED':
            if rel or (tests, passed, failed, errors, skipped) != (0, 0, 0, 0, 0) or isha != sha256_lines([]):
                p.append('FILE %s in state %s carries results' % (gid, state))
            continue
        kinds = {l.split(' ', 1)[0] for l in rel}
        if len(kinds) > 1:
            p.append('FILE %s relays lines of more than one kind' % gid)
        ids, k = [], dict(tests=0, passed=0, failed=0, errors=0, skipped=0)
        for l in rel:
            if l.startswith('TEST '):
                m = re.match(r'^TEST (\S+?)::(\S+) (\S+)$', l)
                if not m or m.group(3) not in TEST_STATUSES:
                    p.append('malformed TEST line: %s' % l)
                    continue
                if m.group(3) == 'NOT_RUN_AFTER_FAILURE':
                    p.append('FILE %s: NOT_RUN_AFTER_FAILURE in a full wrapper child' % gid)
                    continue
                ids.append('%s::%s' % (m.group(1), m.group(2)))
                k['tests'] += 1
                k[{'PASS': 'passed', 'FAIL': 'failed', 'ERROR': 'errors', 'SKIP': 'skipped'}[m.group(3)]] += 1
            else:
                m = re.match(r'^(CASE|PLANT) (\S+) (\S+) cause=(\S+)$', l)
                kind = 'cases' if l.startswith('CASE') else 'sabotage'
                if not m or m.group(3) not in ITEM_OUTCOMES[kind]:
                    p.append('malformed %s line: %s' % (m.group(1) if m else 'item', l))
                    continue
                if m.group(3) not in COMPLETED_OUTCOMES[kind]:
                    p.append('FILE %s is COMPLETED but relays %s %s' % (gid, m.group(2), m.group(3)))
                ids.append(m.group(2))
                k['tests'] += 1
                k['passed' if m.group(3) in ('PASS', 'CAUGHT') else 'failed'] += 1
        if (tests, passed, failed, errors, skipped) != (k['tests'], k['passed'], k['failed'], k['errors'], k['skipped']):
            p.append('FILE %s counts differ from its relayed lines' % gid)
        if isha != sha256_lines(ids):
            p.append('FILE %s ids_sha256 does not match its relayed lines' % gid)
        for key in tot:
            tot[key] += {'tests': tests, 'passed': passed, 'failed': failed, 'errors': errors, 'skipped': skipped}[key]
    st = {s: sum(1 for x in files if x[1] == s) for s in FILE_STATES}
    co = {o: sum(1 for x in checks if x[1] == o) for o in CHECK_OUTCOMES}
    want = dict(tot, files_selected=len(files), files_completed=st['COMPLETED'], files_indeterminate=st['INDETERMINATE'],
                files_errored=st['ITEM_ERROR'], files_not_run=st['NOT_RUN'], files_skipped_after_failure=st['SKIPPED_AFTER_FAILURE'],
                files_started=st['COMPLETED'] + st['INDETERMINATE'] + st['ITEM_ERROR'], checks_selected=len(checks),
                checks_passed=co['PASS'], checks_failed=co['FAIL'], checks_indeterminate=co['INDETERMINATE'], checks_errored=co['ITEM_ERROR'],
                checks_not_run=co['NOT_RUN'], excluded_historical=len(excl), groups_selected=len(files) + len(checks) + len(excl),
                inventory_sha256=sha256_lines(['%s %s' % (x[0], x[8]) for x in files]),
                checks_sha256=sha256_lines([x[2] for x in checks]), exclusions_sha256=sha256_lines([l for _, l in excl]))
    for key, val in want.items():
        if f[key] != val:
            p.append('%s=%s but the lines give %s' % (key, f[key], val))
    if pins is not None:
        for x in files:
            if pins.get('files', {}).get(x[0]) != x[8]:
                p.append('FILE %s file_sha256 differs from the pin' % x[0])
        for gid, _, ident in checks:
            if pins.get('checks', {}).get(gid) != ident:
                p.append('CHECK %s identity differs from the pin' % gid)
        for gid, l in excl:
            if pins.get('exclusions', {}).get(gid) != l:
                p.append('EXCLUDED %s differs from the pin' % gid)
    return p



def wrapper_check_pins(tool, doc=None):
    """Amendment 3, AM3-4: the pins argument of check_output for a successor wrapper's output, built from the pins (this tree's, or doc):
    {'files': {gid: file_sha256}, 'checks': {gid: identity}, 'exclusions': {gid: EXCLUDED line}, 'classes': {gid: class}}.  With it the
    checker compares every FILE, CHECK and EXCLUDED line against the pins, and accepts a child CHECK INDETERMINATE exit=3 only for a
    class N or B group."""
    if doc is None:
        doc = load_pins()[0]
    inv = doc['wrapper_inventories'][tool]
    return {'files': dict(inv.get('files', {})), 'checks': dict(doc.get('check_lists', {}).get(tool, {})),
            'exclusions': dict(doc.get('exclusion_lists', {}).get(tool, {})), 'classes': {g['id']: g['class'] for g in inv['groups']}}


def wrapper_verdict(text, exit_code):
    """§1.9: the one way an operator script or the stage 1 report reads a successor wrapper's result.  Returns 'OK' only for a valid
    kind=wrapper line with status=OK and exit 0; 'OK_WITH_EXCLUSIONS' for that status; otherwise the line's status, or EVIDENCE_ERROR
    when the output is not valid kind=wrapper evidence.  The exit code alone never decides."""
    if check_output(text, actual_exit=exit_code):
        return 'EVIDENCE_ERROR'
    kind, f = parse_result_line([l for l in text.splitlines() if l.strip()][-1])
    if kind != 'wrapper':
        return 'EVIDENCE_ERROR'
    return f['status']


# ---------------------------------------------------------------------------------------------------------------------------------------
# The 19 successor wrappers (decision W-1, owner 2026-10-31 20:57, as corrected by W-1A, owner 2026-11-01 06:22)
# ---------------------------------------------------------------------------------------------------------------------------------------

W1A_GROUPS_CSV_SHA256 = '0fe5b28b00920610acd5348ec17c96740daf52434bc0c92224617053f27f899a'      # wrapper_groups_v2.csv, 657 groups (W-1A)
W1A_EXCLUSIONS_CSV_SHA256 = 'e2f80c2299806c5db89296330c0f7471abfbf600a708c579ea33779398a9cfd3'  # W1_EXCLUSION_LIST_v2.csv, 97 rows (W-1A.1)
# W-1B (owner, 2026-11-01 11:32) replaces both: the files --pin accepts are now these two (the W-1A values above are kept as the record).
W1B_GROUPS_CSV_SHA256 = 'f559ec57a50a045c36e8faedb9d1574315fb45c023046287264568fbe2fbb7c9'      # wrapper_groups_v3.csv, 657 groups
W1B_EXCLUSIONS_CSV_SHA256 = '266eea0dd870452921a19b52bff2c64eb9aa0b42a5f579ecffba33da9a28e479'  # W1_EXCLUSION_LIST_v3.csv, 100 rows
WRAPPER_STOP = {'run_m3_all': 'ok = True', 'run_m4_all': 'ok = True', 'run_m6_all': 'ok = True', 'run_m91_all': 'ok = True',
                'run_m92_all': 'only = None', 'run_m93_all': 'only = None', 'run_m94_all': 'only = None'}   # the others: 'def main():'
WRAPPER_TEST_RUNNERS = {'tools/run_m2_tests.py': ('tools/run_m2_tests_s1.py', 'tests'), 'tools/run_test_files.py': ('tools/run_test_files_s1.py', 'tests'),
                        'tools/run_m8_tests.py': ('tools/run_m8_tests_s1.py', 'tests_m8')}
WRAPPER_RESULT_SUCC = ('run_contracts', 'run_faults', 'run_m3_contracts', 'run_m3_faults', 'run_ingest_corpus', 'run_fin_corpus', 'run_det_corpus',
                       'run_mkt_corpus', 'run_guard_contract', 'run_history_contract', 'run_m5_contracts', 'run_m5_faults', 'run_m6_contracts',
                       'run_m6_faults', 'run_m91_contracts')
WRAPPER_NOKIND_SUCC = ('run_regression_m8', 'run_regression_m81', 'run_cr02_reference')
WRAPPER_NAMES = ('run_m3_all', 'run_m4_all', 'run_m6_all', 'run_m7_all', 'run_m71_all', 'run_m72_all', 'run_m73_all', 'run_m8_all', 'run_m91_all',
                 'run_m92_all', 'run_m93_all', 'run_m94_all', 'run_f67_all', 'run_f671_all', 'run_f672_all', 'run_f673_all', 'run_f674_all',
                 'run_mie1_all', 'run_mie1_1_all')
WRAPPER_TIMEOUT = 3600


def m10_wrapper_table(m10_name, expected_sha256, root=ROOT):
    """The M10 wrapper's own group table, in its run order, read without running any check: the source up to the line where its run
    starts (load_m10_prefix, hash checked), then its table (GROUPS, STEPS or G; run_m8_all's groups()).  Returns (module, [(label, cmd or
    None, marker, count)]).  sys.path is restored afterwards (run_m8_all's prefix inserts tools/)."""
    saved = list(sys.path)
    sys.path.insert(0, os.path.join(root, 'tools'))
    try:
        m = load_m10_prefix(m10_name, WRAPPER_STOP.get(m10_name, 'def main():'), expected_sha256, root=root)
        if m10_name == 'run_m8_all':
            table = [(n, list(c), e, None) for n, c, e in m.groups()]
        elif hasattr(m, 'GROUPS'):
            table = [(g[0], list(g[1]) if g[1] is not None else None, g[2], g[3] if len(g) > 3 else None) for g in m.GROUPS]
        elif hasattr(m, 'STEPS'):
            table = [(n, ['tools/' + t] + list(a), mk, None) for n, t, a, mk in m.STEPS]
        else:
            table = [(n, ['tools/' + t] + list(a), mk, None) for n, t, a, mk in m.G]
    finally:
        sys.path[:] = saved
    return m, table


def wrapper_class(cmd):
    """The mechanical class of a group from its child (W-1A §1): S-T, S-R, N, B, NW or W; P and H are not mechanical (they come from the
    clean-M10 result recorded in the adopted inventory) and are returned as 'P|H'."""
    if cmd is None:
        return 'W'
    tool = cmd[0].split('/')[-1][:-3]
    if cmd[0] in WRAPPER_TEST_RUNNERS:
        return 'S-T'
    if tool in WRAPPER_RESULT_SUCC:
        return 'S-R'
    if tool in WRAPPER_NOKIND_SUCC:
        return 'N'
    if tool.endswith('_mutants') and '--baseline' in cmd:
        return 'B'
    if tool in WRAPPER_NAMES and '--file' in cmd:
        return 'NW'
    return 'P|H'


def _resolve_tests(cmd, pins, root):
    """S-T and NW groups: the stage 1 runner command and the test files it runs, as pinned relative paths."""
    import fnmatch
    succ, folder = WRAPPER_TEST_RUNNERS[cmd[0]]
    args = [a for a in cmd[1:] if a != '-q']
    tf = pins.get('test_files', {})
    if cmd[0] == 'tools/run_m2_tests.py':
        pattern = args[0] if args else 'test_*.py'
        rel = sorted(k for k in tf if k.startswith('tests/') and fnmatch.fnmatch(os.path.basename(k), pattern))
        return [succ, '--caller', 'wrapper', '-q'] + args, rel
    if cmd[0] == 'tools/run_test_files.py':
        return [succ, '--caller', 'wrapper', '-q'] + args, ['tests/' + a for a in args]
    return [succ, '--caller', 'wrapper'] + args, ['tests_m8/' + a for a in args[1:]]   # run_m8_tests.py --file F


def wrapper_plan(tool, m10_name, root=ROOT, pins=None, m10_sha256=None):
    """The successor wrapper's plan: one record per M10 group, in M10's order, with its group id, class, the command it runs (or none),
    and its identity (§1.8).  P and H classes are taken from the pins (wrapper_inventories), which were checked against the adopted
    W-1A inventory when they were written.  Raises RunError if the M10 table cannot be read."""
    m, table = m10_wrapper_table(m10_name, m10_sha256, root)
    pinned = {g['id']: g for g in (pins or {}).get('wrapper_inventories', {}).get(tool, {}).get('groups', [])}
    f674 = None
    plan = []
    for i, (label, cmd, marker, count) in enumerate(table, 1):
        gid = group_id(i)
        cls = wrapper_class(cmd)
        if cls == 'P|H':
            cls = pinned.get(gid, {}).get('class', 'P|H')
        elif cls == 'W' and pinned.get(gid, {}).get('class') == 'H':
            cls = 'H'       # W-1B.1: a built-in check that fails on clean M10 and is listed individually in the adopted exclusion list
        g = {'id': gid, 'label': label, 'class': cls, 'm10_cmd': cmd, 'marker': marker or ''}
        if cls in ('S-T', 'NW'):
            if cls == 'NW':
                if f674 is None:
                    f674 = sys.modules.get('run_f674_all') or m10_wrapper_table('run_f674_all', sha256_file(os.path.join(root, 'tools', 'run_f674_all.py')), root)[0]
                n = int(cmd[cmd.index('--file') + 1])
                name, _cnt = f674.PER_FILE[n - 1]
                cmd = ['tools/run_test_files.py', '-q', name]
            g['run'], g['files'] = _resolve_tests(cmd, pins or {}, root)
        elif cls == 'S-R':
            t = cmd[0].split('/')[-1][:-3]
            g['run'], g['succ'] = ['tools/%s_s1.py' % t] + cmd[1:], t + '_s1'
        elif cls == 'N':
            t = cmd[0].split('/')[-1][:-3]
            g['run'] = ['tools/%s_s1.py' % t] + cmd[1:]
        elif cls == 'B':
            t = cmd[0].split('/')[-1][:-3]
            g['run'] = ['tools/%s_s1.py' % t, '--baseline']
        elif cls == 'P':
            g['run'] = list(cmd)
        plan.append(g)
    return m, plan


def pinned_case_inventory_sha256(pins, tool):
    """The case_inventory_sha256 a full run of a kind=cases tool prints (cases_main): sha256_lines of '<suite>/<case>' over its pinned
    suites and cases."""
    inv = pins['case_inventories'][tool]
    return sha256_lines(['%s/%s' % (s, c) for s in sorted(inv) for c in inv[s]['ids']])   # amendment 2 reading 11: suites sorted


def _group_identity(g, pins, root):
    """The pinned identity of one group: S groups their inventory hash, CHECK groups their §1.8 identity, H groups their EXCLUDED line."""
    cls = g['class']
    if cls in ('S-T', 'NW'):
        tf = pins.get('test_files', {})
        return 'file', group_inventory_sha256([(os.path.basename(r), tf.get(r, {}).get('sha256', '0' * 64)) for r in g['files']])
    if cls == 'S-R':
        s = g['succ']
        if s in pins.get('case_inventories', {}):
            return 'file', group_inventory_sha256([(s, pinned_case_inventory_sha256(pins, s))])
        return 'file', group_inventory_sha256([(s, pins['plant_lists'][s]['ids_sha256'])])
    return None, None


def wrapper_pin(tool, m10_name, groups_csv, exclusions_csv, reason, cause, root=ROOT):
    """--pin: write this wrapper's pins (wrapper_inventories, check_lists, exclusion_lists) after checking them against the adopted W-1A
    files (W-1B's v3 files): both CSVs must have their adopted SHA-256; every group read from M10's table must equal its inventory row (group id, label,
    command, marker, class); the H groups must be exactly this wrapper's rows of the exclusion list, with their release, reason and
    command hash.  Returns (lines, exit code)."""
    import csv as _csv
    for p, want in ((groups_csv, W1B_GROUPS_CSV_SHA256), (exclusions_csv, W1B_EXCLUSIONS_CSV_SHA256)):
        if sha256_file(p) != want:
            return ['RUN_ERROR PIN_INVALID %s is not the adopted file (SHA-256 %s)' % (os.path.basename(p), want)], 2
    inv = [r for r in _csv.DictReader(open(groups_csv, encoding='utf-8', newline='')) if r['wrapper'] == m10_name]
    exc = {r['group_id']: r for r in _csv.DictReader(open(exclusions_csv, encoding='utf-8', newline='')) if r['wrapper'] == m10_name}
    doc, _ = load_pins()
    m10_sha = sha256_file(os.path.join(root, 'tools', m10_name + '.py'))
    tmp_pins = dict(doc, wrapper_inventories=dict(doc.get('wrapper_inventories', {}),
                                                 **{tool: {'groups': [{'id': r['group_id'], 'class': r['class']} for r in inv]}}))
    _, plan = wrapper_plan(tool, m10_name, root, tmp_pins, m10_sha)
    problems = []
    if len(plan) != len(inv):
        problems.append('groups %d, inventory rows %d' % (len(plan), len(inv)))
    cmdtxt_of = lambda g: ' '.join(g['m10_cmd']) if g['m10_cmd'] else '(built in)'     # W-1B: a built-in group has no command
    for g, r in zip(plan, inv):
        cmdtxt = cmdtxt_of(g)
        if (g['id'], g['label'], cmdtxt, g['marker'], g['class']) != (r['group_id'], r['label'], r['command'], r['marker'], r['class']):
            problems.append('%s differs from its inventory row' % g['id'])
    hs = [g for g in plan if g['class'] == 'H']
    if sorted(g['id'] for g in hs) != sorted(exc):
        problems.append('H groups differ from the exclusion list')
    groups, checks, excls, files = [], {}, {}, {}
    for g in plan:
        rec = {'id': g['id'], 'label': g['label'], 'class': g['class'], 'command_sha256': command_sha256(g['m10_cmd']) if g['m10_cmd'] else EMPTY_SHA256}
        typ, ident = _group_identity(g, tmp_pins, root)
        if typ == 'file':
            files[g['id']] = ident
            rec['files'] = list(g.get('files', [])) or [g.get('succ')]
        elif g['class'] == 'H':
            e = exc.get(g['id'])
            if e is None or e['command_sha256'] != rec['command_sha256'] or e['command'] != cmdtxt_of(g):
                problems.append('%s differs from its exclusion row' % g['id'])
                continue
            excls[g['id']] = excluded_line(g['id'], e['release'], e['reason'], e['command_sha256'])
        else:
            source = 'wrapper' if g['class'] == 'W' else 'child'
            run = g.get('run')
            tool_path = os.path.join(root, 'tools', m10_name + '.py') if g['class'] == 'W' else os.path.join(root, run[0])
            cs = EMPTY_SHA256 if g['class'] == 'W' else command_sha256(run)
            checks[g['id']] = check_identity(g['id'], source, cs, sha256_file(tool_path), text_sha256(g['marker']))
            rec['run'] = run
        groups.append(rec)
    if problems:
        return ['RUN_ERROR PIN_INVALID %s' % p.replace(' ', '_') for p in problems[:20]], 2
    new = {'m10': m10_name, 'm10_sha256': m10_sha, 'groups': groups, 'files': files}
    old = (doc.get('wrapper_inventories', {}).get(tool), doc.get('check_lists', {}).get(tool), doc.get('exclusion_lists', {}).get(tool))
    if old == (new, checks, excls):
        return ['PINS unchanged for %s' % tool], 0
    d = write_pins(dict(doc, wrapper_inventories=dict(doc.get('wrapper_inventories', {}), **{tool: new}),
                        check_lists=dict(doc.get('check_lists', {}), **{tool: checks}),
                        exclusion_lists=dict(doc.get('exclusion_lists', {}), **{tool: excls})), reason, cause,
                   [{'entry': 'wrapper_inventories/' + tool, 'old': None if old[0] is None else {'groups': len(old[0]['groups'])},
                     'new': {'groups': len(groups), 'files': len(files), 'checks': len(checks), 'excluded': len(excls),
                             'inventory_sha256': sha256_lines(['%s %s' % kv for kv in sorted(files.items())]),
                             'checks_sha256': sha256_lines(list(checks.values())), 'exclusions_sha256': sha256_lines(list(excls.values()))}}])
    return ['PINS version %d %s groups %d (FILE %d, CHECK %d, EXCLUDED %d)' % (d['version'], tool, len(groups), len(files), len(checks), len(excls))], 0


def _run_check(g, ident, root, env, wrapper_module, last=False):
    """One CHECK group (P, N, B, W): its pinned identity is re-checked against the files before it runs (§1.2 (b)).
    Corrective pass 2: the child is a unit under P (its CLEANUP id the group id); a leak (P.6) or the wrapper's own interrupt (F.2 (b))
    makes the group INDETERMINATE, the cause on its CLEANUP line; a W group's in-process coverage() owns its children (AM-5 (c))."""
    gid, source = g['id'], ('wrapper' if g['class'] == 'W' else 'child')
    _, _, cs, ts, ms = ident.split(' ')
    if g['class'] == 'W':
        with owning(gid) as o_w:
            try:
                ok, detail = wrapper_module.coverage()
                err = None
            except Exception as e:      # the M10 coverage function itself failed
                err = e
        if err is not None:
            return (gid, 'ITEM_ERROR', source, None, '-', cs, ts, ms), 'coverage check raised %s' % type(err).__name__
        if o_w.leaked:
            return (gid, 'INDETERMINATE', source, None, '-', cs, ts, ms), 'processes left (see its CLEANUP line)'
        return (gid, 'PASS' if ok else 'FAIL', source, None, '-', cs, ts, ms), detail
    run = g['run']
    if command_sha256(run) != cs or sha256_file(os.path.join(root, run[0])) != ts or text_sha256(g['marker']) != ms:
        o, ex, mk = check_outcome(None, False, pin_mismatch=True)
        return (gid, o, source, ex, mk, cs, ts, ms), 'the tool, command or marker differs from the pin'
    p = run_unit(gid, [sys.executable, '-I', '-S'] + run, WRAPPER_TIMEOUT, env, root, last=last)
    if p.how == 'timeout':
        o, ex, mk = check_outcome(None, False, timed_out=True)
        return (gid, o, source, ex, mk, cs, ts, ms), 'cut off by the time limit (%ds)' % WRAPPER_TIMEOUT
    if p.how == 'launch_error':
        o, ex, mk = check_outcome(None, False, launch_error=True)
        return (gid, o, source, ex, mk, cs, ts, ms), 'could not be started'
    if p.how == 'interrupted':
        return (gid, 'INDETERMINATE', source, None, '-', cs, ts, ms), 'interrupted (F.2)'
    out = p.stdout + p.stderr
    # AM2-2 (d), scoped by amendment 3, AM3-4: the interrupted no-kind child reading applies to class N groups only
    o, ex, mk = check_outcome(p.returncode, g['marker'] in out,
                              interrupted_child=(g['class'] == 'N' and is_interrupted_child(p.returncode, p.stdout)))
    if p.leaked and o != 'ITEM_ERROR':
        return (gid, 'INDETERMINATE', source, ex, mk, cs, ts, ms), 'processes left (see its CLEANUP line)'
    if g['class'] == 'B' and p.returncode == 3:      # W-1A.3 (a): exit 3 of the successor --baseline is INDETERMINATE (B groups only)
        o, ex, mk = 'INDETERMINATE', 3, ('seen' if g['marker'] in out else 'absent')
    return (gid, o, source, ex, mk, cs, ts, ms), (out.strip().splitlines() or [''])[-1][:200]


def _run_file_group(g, pins, inv_sha, root, env, last=False):
    """One S-T, NW or S-R group: its stage 1 runner or successor, judged by its RESULT v=2 line (T-0 R4 to R6, run_child)."""
    if g['class'] == 'S-R':
        s = g['succ']
        kind = 'cases' if s in pins.get('case_inventories', {}) else 'sabotage'
        outcome, out, err, secs, k, f = run_child(child_cmd(os.path.join(root, g['run'][0]), g['run'][1:]), WRAPPER_TIMEOUT, env, root,
                                                  unit=g['id'], last=last)
        if outcome in ('CHILD_OK', 'CHILD_FAILED'):
            want = pinned_case_inventory_sha256(pins, s) if kind == 'cases' else pins['plant_lists'][s]['ids_sha256']
            got = f.get('case_inventory_sha256') if kind == 'cases' else f.get('ids_sha256')
            if k != kind or got != want or f.get('selected') == 0:
                outcome = 'CHILD_EVIDENCE_ERROR'
    else:
        kind = 'tests'
        fp = test_file_pins(pins, g['files'])
        names = [os.path.basename(r) for r in g['files']]
        outcome, out, err, secs, k, f = run_child(child_cmd(os.path.join(root, g['run'][0]), g['run'][1:]), WRAPPER_TIMEOUT, env, root,
                                                  pins=fp, selected=names, unit=g['id'], last=last)
        if outcome in ('CHILD_OK', 'CHILD_FAILED') and (k != 'tests' or f.get('mode') != 'full'):
            outcome = 'CHILD_EVIDENCE_ERROR'
    if outcome == 'CRASH_NO_RESULT' and f and f.get('returncode') in (0, 1, 2):
        # T-0 (R4) expect_line, adopted for S groups by W-1 §1.2 (a), P4-B17 (R4): a child that ended through its own exit 0, 1 or 2 with
        # its RESULT line missing is that group's ITEM_ERROR.  A child that died (a signal, or any other exit) with no structured result
        # stays INDETERMINATE (§2.7: a crash of the child process with no structured result).
        outcome = 'CHILD_EVIDENCE_ERROR'
    return wrapper_group_from_child(g['id'], inv_sha, outcome, out, kind), outcome


def wrapper_main(tool, m10_name, argv, success_marker=None, root=ROOT):
    """The common main of the 19 successor wrappers (W-1 §1, W-1A).  Usage, as M10's: --list | --group N | --range A-B [--run-id ID];
    with no option, M10's default (the 12 wrappers with a main() list their groups; run_m3/m4/m6/m91/m92/m93/m94_all run them all);
    --all (the 12 only) runs every group;  --pin --reason TEXT --cause TEXT --groups-csv PATH --exclusions-csv PATH.
    Every group runs in M10's order (mode full: a failure never stops the run).  S-T, S-R and NW groups print FILE lines (with the child's
    TEST, CASE or PLANT lines relayed); P, N, B and W groups print CHECK lines; H groups print EXCLUDED lines and are never run.  The
    M10 success marker is printed only with status=OK; with OK_WITH_EXCLUSIONS the wrapper says how many historical checks were not run."""
    import tempfile as _tf
    opts = {'run_id': 'run', 'group': None, 'range': None, 'list': False, 'pin': False, 'reason': '', 'cause': '', 'groups_csv': None,
            'exclusions_csv': None}
    errs, i = [], 0
    while i < len(argv):
        a = argv[i]
        if a in ('--run-id', '--group', '--range', '--reason', '--cause', '--groups-csv', '--exclusions-csv'):
            if i + 1 >= len(argv):
                errs.append(RunError('SELECTION_INVALID', 'missing value for %s' % a))
                break
            opts[a[2:].replace('-', '_')] = argv[i + 1]
            i += 1
        elif a in ('--list', '--pin'):
            opts[a[2:]] = True
        elif a == '--all' and m10_name not in WRAPPER_STOP:
            opts['all'] = True
        else:
            errs.append(RunError('SELECTION_INVALID', 'unknown argument %s (the successor takes --list, --group N, --range A-B, --run-id ID)' % a))
        i += 1
    if opts['pin']:
        if errs or not (opts['reason'] and opts['cause'] and opts['groups_csv'] and opts['exclusions_csv']):
            return emit(['RUN_ERROR SELECTION_INVALID --pin needs --reason, --cause, --groups-csv and --exclusions-csv'], 2)
        lines, code = wrapper_pin(tool, m10_name, opts['groups_csv'], opts['exclusions_csv'], opts['reason'], opts['cause'], root)
        return emit(lines, code)
    if not argv and m10_name not in WRAPPER_STOP:
        opts['list'] = True       # as M10: these wrappers list their groups when given no option
    lines, serrs = start(root, preloaded=PRELOADED_AT_EVKIT_IMPORT)
    if not opts['list']:
        lines = list(lines) + [limit_line(WRAPPER_TIMEOUT)]
    errs = serrs + errs
    pins, plan, module = {}, [], None
    try:
        pins, _ = load_pins()
        winv = pins.get('wrapper_inventories', {}).get(tool)
        if winv is None:
            raise RunError('WRAPPER_NOT_PINNED', tool)
        module, plan = wrapper_plan(tool, m10_name, root, pins, winv['m10_sha256'])
    except RunError as e:
        errs.append(e)
    if opts['list']:
        out = ['%s [%s] %s    (%s)' % (g['id'], g['class'], g['label'], ' '.join(['python3 -I -S'] + g['run']) if g.get('run') else
                                       ('built in' if g['class'] == 'W' else 'not run: historical, excluded')) for g in plan]
        return emit(out + [e.line() for e in errs], 2 if errs else 0)
    sel = [g['id'] for g in plan]
    try:
        if opts['group'] is not None:
            n = int(opts['group'])
            if not 1 <= n <= len(plan):
                raise ValueError
            sel = [group_id(n)]
        elif opts['range'] is not None:
            lo, hi = (int(x) for x in opts['range'].split('-'))
            if not 1 <= lo <= hi <= len(plan):
                raise ValueError
            sel = [group_id(n) for n in range(lo, hi + 1)]
    except ValueError:
        errs.append(RunError('SELECTION_INVALID', 'group or range outside 1 to %d' % len(plan)))
    checks = pins.get('check_lists', {}).get(tool, {})
    excl = pins.get('exclusion_lists', {}).get(tool, {})
    winv = pins.get('wrapper_inventories', {}).get(tool, {})
    if plan and not errs:
        # the plan read now must equal the pins (§2.2): the groups, their classes and identities, the check list and the exclusion list
        pg = {g['id']: g for g in winv.get('groups', [])}
        for g in plan:
            p = pg.get(g['id'])
            cs = command_sha256(g['m10_cmd']) if g['m10_cmd'] else EMPTY_SHA256
            if p is None or (p['label'], p['class'], p['command_sha256']) != (g['label'], g['class'], cs):
                errs.append(RunError('EXPECTED_COUNT_MISMATCH', '%s group %s differs from the pin' % (tool, g['id'])))
                continue
            typ, ident = _group_identity(g, pins, root)
            if typ == 'file' and winv.get('files', {}).get(g['id']) != ident:
                errs.append(RunError('EXPECTED_COUNT_MISMATCH', '%s group %s inventory differs from the pin' % (tool, g['id'])))
        hs = sorted(g['id'] for g in plan if g['class'] == 'H')
        if hs != sorted(excl):
            errs.append(RunError('EXCLUSION_LIST_MISMATCH', '%s pinned %d, table %d' % (tool, len(excl), len(hs))))
        cks = sorted(g['id'] for g in plan if g['class'] in ('P', 'N', 'B', 'W'))
        if cks != sorted(checks):
            errs.append(RunError('CHECK_LIST_MISMATCH', '%s pinned %d, table %d' % (tool, len(checks), len(cks))))
        if len(pg) != len(plan):
            errs.append(RunError('EXPECTED_COUNT_MISMATCH', '%s groups %d pinned %d' % (tool, len(plan), len(pg))))
    by_id = {g['id']: g for g in plan}
    records, human = [], []
    tmp = _tf.mkdtemp(prefix='s1_wrap_')
    try:
        env = clean_env(tmp)
        runnable = [x for x in sel if by_id.get(x) is not None and by_id[x]['class'] != 'H']
        last_gid = runnable[-1] if runnable else None
        for gid in sel:
            g = by_id.get(gid)
            if g is None:
                continue
            cls = g['class']
            stop_now = CANCEL.set and cls != 'H'      # F.2: no further group starts; an H group never runs and keeps its line
            if cls != 'H':
                set_phase(gid)
            if cls == 'H':
                line = excl.get(gid)
                if line:
                    _, _, _, rel, rea, cs = line.split(' ')
                    records.append(('excluded', (gid, rel.split('=', 1)[1], rea.split('=', 1)[1], cs.split('=', 1)[1])))
                human.append('NOT RUN %s: %s (historical check of an earlier release, excluded)' % (gid, g['label']))
                continue
            if cls in ('P', 'N', 'B', 'W'):
                ident = checks.get(gid)
                if errs or ident is None or stop_now:
                    parts = (ident or check_identity(gid, 'wrapper' if cls == 'W' else 'child', EMPTY_SHA256, EMPTY_SHA256, EMPTY_SHA256)).split(' ')
                    records.append(('check', (gid, 'NOT_RUN', parts[1], None, '-', parts[2], parts[3], parts[4])))
                    continue
                rec, detail = _run_check(g, ident, root, env, module, last=(gid == last_gid))
                records.append(('check', rec))
                human.append('%s %s: %s | %s' % (rec[1], gid, g['label'], detail))
                continue
            inv_sha = winv.get('files', {}).get(gid, '0' * 64)
            if errs or stop_now:
                records.append(('file', WrapperGroup(gid, 'NOT_RUN', [], dict(tests=0, passed=0, failed=0, errors=0, skipped=0), inv_sha, [],
                                                     **({'cause': 'run_stopped'} if stop_now and not errs else {}))))
                continue
            wg, outcome = _run_file_group(g, pins, inv_sha, root, env, last=(gid == last_gid))
            records.append(('file', wg))
            human.append('%s %s: %s | %s' % (wg.state if wg.state != 'COMPLETED' else ('FAILED' if wg.counts['failed'] + wg.counts['errors'] else 'PASS'),
                                              gid, g['label'], outcome.lower()))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out, code = finish_wrapper(tool, opts['run_id'], records, errs)
    k = next(i for i, l in enumerate(out) if l.startswith('RUN_ERROR') or l.startswith('RESULT'))
    status = parse_result_line(out[-1])[1]['status']
    tail = []
    if status == 'OK' and success_marker:
        tail = [success_marker % len(sel) if '%d' in success_marker else success_marker]
    elif status == 'OK_WITH_EXCLUSIONS':
        n = sum(1 for t, _ in records if t == 'excluded')
        tail = ['PASSED WITH %d HISTORICAL CHECK%s NOT RUN (listed above as EXCLUDED)' % (n, '' if n == 1 else 'S')]
    return emit(lines + out[:k] + human + out[k:], code, before_result=tail)
