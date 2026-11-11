#!/usr/bin/env python3
"""Builder tool (outside the tree), corrective pass 2, P.9 audit part 1, the mechanical half: an AST scan of tools/evkit.py and every
tools/*_s1.py in an extraction of the freeze for process-start calls (subprocess.run/Popen/call/check_call/check_output, os.fork/
system/popen/exec*/spawn*/posix_spawn*, multiprocessing, ProcessPoolExecutor, pty.spawn), each with its enclosing function; a grep of
the M10 tools for any *_s1 name; and the counts of section E of the 2026-11-05 inventory (sockets, port 2024, process starts).
Usage: python3 -I -S child_start_scan_s1.py EXTRACTION_ROOT OUT.txt        BUILDER-EXECUTED: NOT INDEPENDENT."""
import ast, glob, os, re, sys

SUB = {'run', 'Popen', 'call', 'check_call', 'check_output'}
OS = re.compile(r'^(fork|forkpty|system|popen|exec\w*|spawn\w*|posix_spawn\w*)$')


def sites(path):
    tree = ast.parse(open(path, encoding='utf-8').read(), path)
    out = []

    def walk(node, fn):
        for ch in ast.iter_child_nodes(node):
            f = ch.name if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)) else fn
            if isinstance(ch, ast.Call) and isinstance(ch.func, ast.Attribute):
                mod, att = ast.unparse(ch.func.value), ch.func.attr      # any alias or chain: _subprocess, E._subprocess, ...
                last = mod.split('.')[-1]
                if ('subprocess' in last and att in SUB) or (last in ('os', '_os') and OS.match(att)) \
                        or (last == 'pty' and att == 'spawn') or ('multiprocessing' in last and att in ('Process', 'Pool')):
                    out.append((ch.lineno, f, '%s.%s' % (mod, att)))
            if isinstance(ch, ast.Name) and ch.id == 'ProcessPoolExecutor':
                out.append((ch.lineno, f, 'ProcessPoolExecutor'))
            walk(ch, f)
    walk(tree, '<module>')
    return sorted(set(out))


def main(root, outp):
    L = ['BUILDER-EXECUTED: NOT INDEPENDENT. Corrective pass 2, P.9 audit part 1 (mechanical scan), from %s' % root, '']
    files = [os.path.join(root, 'tools', 'evkit.py')] + sorted(glob.glob(os.path.join(root, 'tools', '*_s1.py')))
    L.append('A. Process-start calls in successor code (AST scan of tools/evkit.py and %d tools/*_s1.py)' % (len(files) - 1))
    n = 0
    for p in files:
        for line, fn, call in sites(p):
            n += 1
            L.append('  %s:%d  %-32s %s' % (os.path.relpath(p, root), line, fn, call))
    L.append('  total: %d' % n)
    shim = [os.path.relpath(p, root) for p in files if 'subprocess.run =' in open(p, encoding='utf-8').read()
            or re.search(r'subprocess\s*,\s*[\'"]run[\'"]', open(p, encoding='utf-8').read())]
    L.append('  files that replace subprocess.run with a shim: %s' % shim)
    L.append('')
    m10 = [p for p in sorted(glob.glob(os.path.join(root, 'tools', '*.py'))) if not p.endswith('_s1.py') and not p.endswith('evkit.py')]
    named = [os.path.relpath(p, root) for p in m10 if re.search(r'\b\w+_s1\b', open(p, encoding='utf-8', errors='replace').read())]
    L.append('D. M10 tools in tools/ (%d) that name any *_s1 tool: %d %s' % (len(m10), len(named), named))
    L.append('')
    dirs = ['apg', 'apg_auif', 'apg_ui', 'mie', 'auif_m8', 'tests', 'tests_m8', 'tests_m10', 'tools', 'reference']
    sock = re.compile(r'^\s*(import|from)\s+(socket|http|urllib|asyncio)\b', re.M)
    port = re.compile(r'\b2024\b.*(port|connect)|cc-socks|process_api', re.I)
    proc = re.compile(r'\bsubprocess\b|os\.(fork|system|popen|exec|spawn)|child_process|spawnSync|execSync')
    L.append('E. Code under test and tools (grep of *.py, and *.js/*.mjs for process starts)')
    for d in dirs:
        base = os.path.join(root, d)
        py = glob.glob(os.path.join(base, '**', '*.py'), recursive=True)
        js = glob.glob(os.path.join(base, '**', '*.js'), recursive=True) + glob.glob(os.path.join(base, '**', '*.mjs'), recursive=True)
        rd = lambda p: open(p, encoding='utf-8', errors='replace').read()
        L.append('  %-10s py=%-4d socket/http/urllib/asyncio imports=%-3d port-2024/cc-socks/process_api=%-3d process starts=%d' % (
            d, len(py), sum(1 for p in py if sock.search(rd(p))), sum(1 for p in py + js if port.search(rd(p))),
            sum(1 for p in py + js if proc.search(rd(p)))))
    open(outp, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
