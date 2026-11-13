#!/usr/bin/env python3
"""Builder tool (outside the tree), written in the 2026-11-11 recovery for amendment 5 row 68 / discrepancy 6 (the 303b6414-era check was
lost): a fresh check, on an extraction of the freeze, of every process start in tests_tools (AM-2: "all ... process starts in tests_tools
set a time limit"), each with its file, line, enclosing class and function, the call, and the time limit applied there.
Process starts: subprocess.run / Popen / call / check_call / check_output (any alias), os.fork / forkpty / system / popen / exec* /
spawn* / posix_spawn*, multiprocessing.Process / Pool, and the freeze's evkit.run_unit / run_forked / run_child (any alias).
The limit: a timeout= keyword; for evkit run_unit, run_forked and run_child their third positional argument (the timeout); for Popen and
os.fork, a timed wait in the same function (.wait(timeout=...), .communicate(timeout=...), or a deadline loop with time.monotonic /
signal.alarm); otherwise NONE.  A NONE row is printed for the builder to read; this tool decides nothing by itself.
Fix 6 (step 6 re-mapping, discrepancy D6-1): the aliases are now read from each file's own imports ("import subprocess as _p2sp",
"from subprocess import Popen as P", "import tools.evkit as E" and the like), so every alias is matched, not only names containing
"subprocess" or sp/_sp; and a second table lists every call in tests_tools that names a leaf tests runner (run_m2_tests_s1,
mut_runner_s1, run_test_files_s1) or child_unittest_runner, with its file, line, function, the helper it goes through and that
helper's limit (AM-2's "parent, limit and leaf").
Usage: python3 -I -S tset_start_scan_s1.py EXTRACTION_ROOT OUT.txt        BUILDER-EXECUTED: NOT INDEPENDENT."""
import ast, glob, os, re, sys

SUB = {'run', 'Popen', 'call', 'check_call', 'check_output'}
OS = re.compile(r'^(fork|forkpty|system|popen|exec\w*|spawn\w*|posix_spawn\w*)$')
EVK = {'run_unit': 2, 'run_forked': 2, 'run_child': 1}       # index of the timeout argument


ALIASES = {'subprocess': set(), 'os': set(), 'multiprocessing': set(), 'evkit': set(), 'direct': {}}


def read_aliases(tree):
    """Fix 6 (D6-1): the names this file binds to subprocess, os, multiprocessing and evkit, and the functions imported directly."""
    a = {'subprocess': {'subprocess'}, 'os': {'os'}, 'multiprocessing': {'multiprocessing'}, 'evkit': {'evkit'}, 'direct': {}}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for al in n.names:
                base = al.name.split('.')[-1]
                for mod in ('subprocess', 'os', 'multiprocessing', 'evkit'):
                    if base == mod:
                        a[mod].add(al.asname or al.name.split('.')[0])
        elif isinstance(n, ast.ImportFrom) and n.module:
            base = n.module.split('.')[-1]
            for al in n.names:
                if al.name == 'evkit':
                    a['evkit'].add(al.asname or al.name)
                if base == 'subprocess' and al.name in SUB:
                    a['direct'][al.asname or al.name] = 'subprocess.' + al.name
                if base == 'os' and OS.match(al.name):
                    a['direct'][al.asname or al.name] = 'os.' + al.name
                if base == 'evkit' and al.name in EVK:
                    a['direct'][al.asname or al.name] = 'evkit.' + al.name
    return a


def kind(call):
    if isinstance(call.func, ast.Name) and call.func.id in ALIASES['direct']:
        return ALIASES['direct'][call.func.id]
    if not isinstance(call.func, ast.Attribute):
        return None
    mod, att = ast.unparse(call.func.value), call.func.attr
    last = mod.split('.')[-1]
    if last in ALIASES['subprocess'] and att in SUB:
        return 'subprocess.' + att
    if last in ALIASES['os'] and OS.match(att):
        return 'os.' + att
    if last in ALIASES['multiprocessing'] and att in ('Process', 'Pool'):
        return 'multiprocessing.' + att
    if last in ALIASES['evkit'] and att in EVK:
        return 'evkit.' + att
    if 'subprocess' in last.lower() or last in ('sp', '_sp'):
        return ('subprocess.' + att) if att in SUB else None
    if last in ('os', '_os') and OS.match(att):
        return 'os.' + att
    if 'multiprocessing' in last and att in ('Process', 'Pool'):
        return 'multiprocessing.' + att
    if att in EVK and last in ('E', 'evkit', 'EV', 'K'):
        return 'evkit.' + att
    return None


def limit(call, k, fn_src):
    for kw in call.keywords:
        if kw.arg == 'timeout':
            return 'timeout=' + ast.unparse(kw.value)
    if k.startswith('evkit.'):
        i = EVK[k.split('.')[1]]
        if len(call.args) > i:
            return 'timeout(arg %d)=%s' % (i + 1, ast.unparse(call.args[i]))
    if k in ('subprocess.Popen', 'os.fork', 'os.forkpty'):
        hits = [p for p in (r'\.wait\(\s*timeout=', r'\.communicate\(\s*timeout=', r'\.wait\(\s*\d', r'monotonic\(\)', r'(?:signal|_sig|_signal)\.alarm\(')
                if re.search(p, fn_src)]
        if hits:
            return 'timed wait in the same function (%s)' % ', '.join(h.replace('\\', '') for h in hits)
    return 'NONE'


def scan(path):
    src = open(path, encoding='utf-8').read()
    tree = ast.parse(src, path)
    lines = src.splitlines()
    out = []
    ALIASES.clear()
    ALIASES.update(read_aliases(tree))

    def walk(node, cls, fn, fn_src):
        for ch in ast.iter_child_nodes(node):
            c, f, s = cls, fn, fn_src
            if isinstance(ch, ast.ClassDef):
                c = ch.name
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                f, s = ch.name, '\n'.join(lines[ch.lineno - 1:ch.end_lineno])
            if isinstance(ch, ast.Call):
                k = kind(ch)
                if k:
                    out.append((ch.lineno, c or '-', f or '<module>', k, limit(ch, k, s)))
            walk(ch, c, f, s)
    walk(tree, None, None, src)
    return out


LEAVES = ('run_m2_tests_s1', 'mut_runner_s1', 'run_test_files_s1', 'child_unittest_runner')


def leaf_calls(path):
    """Fix 6 (AM-2's leaf column): every call whose arguments name a leaf tests runner (or child_unittest_runner) in a string, with
    the function it is in, the callee (the helper it goes through) and the callee's timeout keyword or default where visible here."""
    src = open(path, encoding='utf-8').read()
    tree = ast.parse(src, path)
    defaults = {}
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = n.args.args[-len(n.args.defaults):] if n.args.defaults else []
            for a, d in zip(args, n.args.defaults):
                if a.arg == 'timeout':
                    defaults[n.name] = ast.unparse(d)
    out = []

    def walk(node, fn):
        for ch in ast.iter_child_nodes(node):
            f = ch.name if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)) else fn
            if isinstance(ch, ast.Call):
                strs = [x.value for a in list(ch.args) + [k.value for k in ch.keywords] for x in ast.walk(a)
                        if isinstance(x, ast.Constant) and isinstance(x.value, str)]
                named = sorted({l for l in LEAVES for t in strs if l in t})
                callee = ast.unparse(ch.func)
                if named and not callee.startswith(('os.path.', 'open', 'self.assert', 'print', 'fh.write', 're.', '_re.', '_p2re.', '_am5re.')):
                    kw = [ast.unparse(k.value) for k in ch.keywords if k.arg == 'timeout']
                    lim = ('timeout=' + kw[0]) if kw else ('the helper default timeout=%s' % defaults[callee.split('.')[-1]]
                                                           if callee.split('.')[-1] in defaults else 'the helper\'s own (see its process-start row)')
                    out.append((ch.lineno, f or '<module>', callee, ','.join(named), lim))
            walk(ch, f)
    walk(tree, None)
    return out


def main(root, outp):
    rows, leaves = [], []
    for p in sorted(glob.glob(os.path.join(root, 'tests_tools', '*.py'))):
        for r in scan(p):
            rows.append((os.path.relpath(p, root),) + r)
        for r in leaf_calls(p):
            leaves.append((os.path.relpath(p, root),) + r)
    none = [r for r in rows if r[5] == 'NONE']
    with open(outp, 'w') as fh:
        fh.write('BUILDER-EXECUTED: NOT INDEPENDENT. Process starts in tests_tools on %s (amendment 5 row 68)\n' % root)
        fh.write('file\tline\tclass\tfunction\tcall\tlimit\n')
        for r in rows:
            fh.write('\t'.join(str(x) for x in r) + '\n')
        fh.write('sites %d; with a limit found %d; NONE %d\n' % (len(rows), len(rows) - len(none), len(none)))
        fh.write('\nLeaf invocations (AM-2: parent, limit and leaf): file\tline\tfunction (parent)\thelper\tleaf\tlimit\n')
        for r in leaves:
            fh.write('\t'.join(str(x) for x in r) + '\n')
        fh.write('leaf invocations %d\n' % len(leaves))
    print('sites %d; with a limit found %d; NONE %d' % (len(rows), len(rows) - len(none), len(none)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
