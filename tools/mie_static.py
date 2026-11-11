#!/usr/bin/env python3
"""Static checks of the MIE-1 core (NE-01 to NE-06, FL-01, IG-01, IG-05).  Each check takes a root folder, so a test can run it on a copy with a planted defect and show that it
fails.  Usage: python3 -I tools/mie_static.py [root]   -> one line per check; exit 0 only if every check passes.
The deny list is data (mie/neutrality/deny_list.txt), kept outside the scanned files so that the scan does not find its own list."""
import ast, glob, os, re, sys
sys.dont_write_bytecode = True

STDLIB_ALLOWED = {'hashlib', 'json', 'unicodedata', 'fractions', 'datetime', 're'}
FORBIDDEN_FIELD_WORDS = {'forecast', 'predicted', 'expected', 'projected'}
CLOCK_MODULES = {'time', 'random', 'os', 'sys', 'socket', 'urllib', 'http', 'pathlib', 'subprocess', 'secrets', 'uuid', 'shutil', 'tempfile', 'glob', 'io', 'requests',
                 'threading', 'asyncio', 'ssl', 'ftplib', 'smtplib', 'sqlite3', 'importlib'}
CLOCK_ATTRS = {'now', 'today', 'utcnow', 'time', 'environ', 'getenv', 'urandom', 'random', 'localtime', 'gmtime', 'perf_counter', 'monotonic'}
CLOCK_NAMES = {'open', 'input', 'eval', 'exec', '__import__', 'compile'}
FEED_NAMES = {'ObservationSourcePort', 'fetch', 'retrieve', 'FeedAdapter', 'IngestionDriver', 'MarketFeedPort'}
ORDERING_WORDS = {'order', 'commit', 'notify', 'forecast', 'purchase', 'buy_now', 'execute', 'send'}


def core_files(root):
    return sorted(glob.glob(os.path.join(root, 'mie', 'core', '*.py')))


def core_test_files(root):
    t = os.path.join(root, 'tests')
    return sorted(glob.glob(os.path.join(t, 'test_mie_core_*.py')) + [os.path.join(t, n) for n in ('helpers_mie.py', 'test_mie_flow.py', 'test_mie_portability.py')
                                                                      if os.path.exists(os.path.join(t, n))])


def deny_terms(root):
    lines = open(os.path.join(root, 'mie', 'neutrality', 'deny_list.txt'), encoding='utf-8').read().splitlines()
    return [l.strip().lower() for l in lines[1:] if l.strip() and not l.startswith('#')]


def words(text):
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    return re.findall(r'[a-z]+', text.lower().replace('_', ' ').replace('-', ' '))


def neutrality(root):
    """NE-01: -> [(file, word)] for every deny-listed term (or its simple plural) in the core source and the core's tests."""
    deny = set(deny_terms(root))
    forms = deny | {d + 's' for d in deny} | {d + 'es' for d in deny}
    out = []
    for f in core_files(root) + core_test_files(root):
        for w in words(open(f, encoding='utf-8').read()):
            if w in forms:
                out.append((os.path.relpath(f, root), w))
    return out


def _imports(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                yield a.name.split('.')[0], 0
        elif isinstance(n, ast.ImportFrom):
            yield (n.module or '').split('.')[0], n.level


def import_violations(root):
    """NE-03: the core imports only the allowed standard-library modules and itself (relative imports); no apg, pack, adapter or consumer module."""
    out = []
    for f in core_files(root):
        for mod, level in _imports(ast.parse(open(f, encoding='utf-8').read())):
            if level == 0 and mod not in STDLIB_ALLOWED:
                out.append((os.path.relpath(f, root), mod))
            if level >= 2:
                out.append((os.path.relpath(f, root), 'parent-package import'))
    return out


def _field_names(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.Dict):
            for k in n.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    yield k.value
        elif isinstance(n, ast.Name):
            yield n.id
        elif isinstance(n, ast.Attribute):
            yield n.attr
        elif isinstance(n, ast.arg):
            yield n.arg
        elif isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            yield n.name
        elif isinstance(n, ast.keyword) and n.arg:
            yield n.arg
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'dict':
            pass


def field_violations(root):
    """NE-04: no field, key, argument, function or class name in the core is named forecast, predicted, expected or projected."""
    out = []
    for f in core_files(root):
        for name in _field_names(ast.parse(open(f, encoding='utf-8').read())):
            if set(words(name)) & FORBIDDEN_FIELD_WORDS:
                out.append((os.path.relpath(f, root), name))
    return out


def operation_violations(root):
    """NE-05: the engine's public operations are exactly the twelve, and none orders, commits, notifies or reads or writes a forecast."""
    tree = ast.parse(open(os.path.join(root, 'mie', 'core', 'engine.py'), encoding='utf-8').read())
    eng = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Engine'][0]
    public = sorted(n.name for n in eng.body if isinstance(n, ast.FunctionDef) and not n.name.startswith('_'))
    vocab = open(os.path.join(root, 'mie', 'core', 'vocab.py'), encoding='utf-8').read()
    ops = sorted(re.search(r"OPERATIONS = \(([^)]*)\)", vocab, re.S).group(1).replace("'", '').replace('\n', ' ').replace(' ', '').split(','))
    bad = [p for p in public if set(words(p)) & ORDERING_WORDS]
    return ([('engine.py', 'operations %r differ from %r' % (public, ops))] if public != ops else []) + [('engine.py', p) for p in bad]


def clock_violations(root):
    """NE-06: no clock, random source, network, file system or environment is read: no such module imported, no such attribute or built-in used."""
    out = []
    for f in core_files(root):
        tree = ast.parse(open(f, encoding='utf-8').read())
        for mod, level in _imports(tree):
            if level == 0 and mod in CLOCK_MODULES:
                out.append((os.path.relpath(f, root), 'import ' + mod))
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and n.attr in CLOCK_ATTRS:
                out.append((os.path.relpath(f, root), '.' + n.attr))
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in CLOCK_NAMES:
                out.append((os.path.relpath(f, root), n.func.id + '()'))
    return out


def feed_violations(root):
    """FL-01: no path in the core calls an observation source or any feed: no such name or attribute, no adapter import."""
    out = []
    for f in core_files(root):
        tree = ast.parse(open(f, encoding='utf-8').read())
        for n in ast.walk(tree):
            if isinstance(n, ast.Name) and n.id in FEED_NAMES or isinstance(n, ast.Attribute) and n.attr in FEED_NAMES:
                out.append((os.path.relpath(f, root), getattr(n, 'id', None) or n.attr))
        for mod, level in _imports(tree):
            if mod == 'adapters':
                out.append((os.path.relpath(f, root), 'import adapters'))
    return out


def apg_imports_mie(root):
    """IG-01: -> APG modules that import the MIE core, a pack or an adapter (none may)."""
    out = []
    for f in sorted(glob.glob(os.path.join(root, 'apg', '**', '*.py'), recursive=True)):
        for mod, level in _imports(ast.parse(open(f, encoding='utf-8').read())):
            if level == 0 and mod == 'mie':
                out.append(os.path.relpath(f, root))
    return out


def mie_imports_apg(root):
    """IG-05: -> MIE modules (core, packs, adapters) that import APG.  None does: APG objects are handed in by the caller, so no consumer path from the core into APG exists."""
    out = []
    for f in sorted(glob.glob(os.path.join(root, 'mie', '**', '*.py'), recursive=True)):
        for mod, level in _imports(ast.parse(open(f, encoding='utf-8').read())):
            if level == 0 and mod == 'apg':
                out.append(os.path.relpath(f, root))
    return out


CHECKS = [('NE-01 neutrality', neutrality), ('NE-03 imports', import_violations), ('NE-04 field names', field_violations), ('NE-05 operations', operation_violations),
          ('NE-06 clock, random, network, files, environment', clock_violations), ('FL-01 no feed call in the core', feed_violations),
          ('IG-01 no APG module imports MIE', apg_imports_mie), ('IG-05 no MIE module imports APG', mie_imports_apg)]


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bad = 0
    for name, fn in CHECKS:
        v = fn(root)
        print('%s %s %s' % ('PASS' if not v else 'FAIL', name, v[:5] if v else ''))
        bad += bool(v)
    print('static checks %d  failed %d' % (len(CHECKS), bad))
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
