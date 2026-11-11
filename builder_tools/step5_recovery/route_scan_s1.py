#!/usr/bin/env python3
"""Builder tool (outside the successor tree): the static part of the route proof (R1 §3.3), on the frozen stage 1 ZIP.
Old names are the M10 originals of the 73 successor tools (tools/X.py for every tools/X_s1.py).  In every file stage 1 added or changed
(the manifest's 'changed' section), every code string literal that names an old file or old module (X.py, X, tools/X.py) is listed with its
file, line and the enclosing function, outside docstrings and comments.  Each is then classified by hand in the report: a route (the old file
executed or imported as the tool) or a data read (the old file read by hash, as M10's own source of a table or list).
Usage: python3 -I route_scan_s1.py S1.zip OUT.csv     BUILDER-EXECUTED: NOT INDEPENDENT."""
import ast, csv, io, sys, zipfile


def main(zp, out):
    z = zipfile.ZipFile(zp)
    names = [n.split('/', 1)[1] for n in z.namelist()]
    succ = sorted(n for n in names if n.startswith('tools/') and n.endswith('_s1.py'))
    old = {n[len('tools/'):-len('_s1.py')] for n in succ}
    man = list(csv.DictReader(io.TextIOWrapper(z.open('APG-M11-S1/programme/APG-M11-S1_MANIFEST.csv'), encoding='utf-8')))
    changed = sorted(r['path'] for r in man if r['section'] == 'changed' and r['path'].endswith('.py'))
    rows = []
    for p in changed:
        src = z.read('APG-M11-S1/' + p).decode('utf-8')
        tree = ast.parse(src)
        docs = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body and \
                    isinstance(node.body[0], ast.Expr) and isinstance(getattr(node.body[0], 'value', None), ast.Constant):
                docs.add(id(node.body[0].value))
        funcs = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for sub in ast.walk(node):
                    funcs.setdefault(id(sub), node.name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
                v = node.value
                hits = sorted(o for o in old if v in (o, o + '.py', 'tools/' + o + '.py') or v.endswith('/' + o + '.py'))
                for h in hits:
                    rows.append([p, node.lineno, funcs.get(id(node), '<module>'), h, v])
    with open(out, 'w', newline='') as fh:
        w = csv.writer(fh, lineterminator='\n')
        w.writerow(['file', 'line', 'function', 'old_tool', 'literal'])
        w.writerows(rows)
    print('changed .py files %d, successor tools %d, code literals naming an old tool %d' % (len(changed), len(succ), len(rows)))
    by = {}
    for r in rows:
        by.setdefault((r[0], r[2]), []).append(r[3])
    for (f, fn), hs in sorted(by.items()):
        print('  %s :: %s  -> %s' % (f, fn, ' '.join(sorted(set(hs)))))
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:3]))
