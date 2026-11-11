#!/usr/bin/env python3
"""Builder tool (outside the tree), written in the 2026-11-11 recovery for amendment 5 row 68 / discrepancy 6 (the 303b6414-era check was
lost): a fresh check, on an extraction of the freeze, of every process start in tests_tools (AM-2: "all ... process starts in tests_tools
set a time limit"), each with its file, line, enclosing class and function, the call, and the time limit applied there.
Process starts: subprocess.run / Popen / call / check_call / check_output (any alias), os.fork / forkpty / system / popen / exec* /
spawn* / posix_spawn*, multiprocessing.Process / Pool, and the freeze's evkit.run_unit / run_forked / run_child (any alias).
The limit: a timeout= keyword; for evkit run_unit, run_forked and run_child their third positional argument (the timeout); for Popen and
os.fork, a timed wait in the same function (.wait(timeout=...), .communicate(timeout=...), or a deadline loop with time.monotonic /
signal.alarm); otherwise NONE.  A NONE row is printed for the builder to read; this tool decides nothing by itself.
Usage: python3 -I -S tset_start_scan_s1.py EXTRACTION_ROOT OUT.txt        BUILDER-EXECUTED: NOT INDEPENDENT."""
import ast, glob, os, re, sys

SUB = {'run', 'Popen', 'call', 'check_call', 'check_output'}
OS = re.compile(r'^(fork|forkpty|system|popen|exec\w*|spawn\w*|posix_spawn\w*)$')
EVK = {'run_unit': 2, 'run_forked': 2, 'run_child': 1}       # index of the timeout argument


def kind(call):
    if not isinstance(call.func, ast.Attribute):
        return None
    mod, att = ast.unparse(call.func.value), call.func.attr
    last = mod.split('.')[-1]
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


def main(root, outp):
    rows = []
    for p in sorted(glob.glob(os.path.join(root, 'tests_tools', '*.py'))):
        for r in scan(p):
            rows.append((os.path.relpath(p, root),) + r)
    none = [r for r in rows if r[5] == 'NONE']
    with open(outp, 'w') as fh:
        fh.write('BUILDER-EXECUTED: NOT INDEPENDENT. Process starts in tests_tools on %s (amendment 5 row 68)\n' % root)
        fh.write('file\tline\tclass\tfunction\tcall\tlimit\n')
        for r in rows:
            fh.write('\t'.join(str(x) for x in r) + '\n')
        fh.write('sites %d; with a limit found %d; NONE %d\n' % (len(rows), len(rows) - len(none), len(none)))
    print('sites %d; with a limit found %d; NONE %d' % (len(rows), len(rows) - len(none), len(none)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
