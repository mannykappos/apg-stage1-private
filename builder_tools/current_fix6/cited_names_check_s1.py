#!/usr/bin/env python3
"""Builder tool (packaging, step 7; decision paper I.3 "the check of the cited test names"; amendment 5 row 120).

Reads the given text files (the documents and the package README) and checks every cited test name against the freeze:
- `test_<name>.py` file names: the file exists under tests_tools/, tests/ or tests_m8/;
- `test_<name>` identifiers: a function or method of that name is defined in some test file of the freeze;
- `<Class>.test_<name>` and `<Class>::test_<name>`: that class defines that method;
- class names that look like test classes (`P2…`, `AM5…`, `AM6…`, `E1…` and so on, cited in backticks): the class exists;
- `<file>.py:<line>`: the file exists in the freeze and has at least that many lines.
Prints one line per citation (OK or MISSING) and a RESULT line; exit 1 if anything is missing.
Usage: python3 -I -S cited_names_check_s1.py FREEZE.zip FILE...        BUILDER-EXECUTED: NOT INDEPENDENT."""
import ast, re, sys, zipfile

z = zipfile.ZipFile(sys.argv[1])
files = {n.split('/', 1)[1]: n for n in z.namelist() if not n.endswith('/') and '/' in n}
pyfiles = {k: v for k, v in files.items() if k.endswith('.py')}
defs, classes = set(), {}
for k, n in pyfiles.items():
    if not (k.startswith('tests_tools/') or k.startswith('tests/') or k.startswith('tests_m8/') or k.startswith('tests_m10/')):
        continue
    try:
        tree = ast.parse(z.read(n))
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.add(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.setdefault(node.name, set()).update(
                b.name for b in node.body if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)))
by_base = {}
for k in pyfiles:
    by_base.setdefault(k.rsplit('/', 1)[-1], []).append(k)

text = '\n'.join(open(p, encoding='utf-8').read() for p in sys.argv[2:])
cites = set()
for m in re.finditer(r'`([^`\n]+)`', text):
    cites.add(m.group(1))
for m in re.finditer(r'\b(test_[A-Za-z0-9_]+(?:\.py)?)\b', text):
    cites.add(m.group(1))
for m in re.finditer(r'\b([A-Za-z0-9_]+\.py:\d+)\b', text):
    cites.add(m.group(1))

rows, missing = [], 0
def out(kind, c, ok):
    global missing
    rows.append('%-8s %-9s %s' % ('OK' if ok else 'MISSING', kind, c))
    missing += 0 if ok else 1

for c in sorted(cites):
    c = c.strip()
    m = re.fullmatch(r'(?:[\w./-]*/)?([A-Za-z0-9_]+\.py):(\d+)(?:[-,]\d+)*', c)
    if m:
        base, line = m.group(1), int(m.group(2))
        cands = by_base.get(base, [])
        out('file:line', c, any(z.read(pyfiles[k]).count(b'\n') + 1 >= line for k in cands))
        continue
    m = re.fullmatch(r'([A-Z][A-Za-z0-9_]*)(?:\.|::)(test_[A-Za-z0-9_]+)', c)
    if m:
        out('method', c, m.group(2) in classes.get(m.group(1), set()))
        continue
    m = re.fullmatch(r'(?:[\w/]+/)?(test_[A-Za-z0-9_]+\.py)', c)
    if m:
        out('file', c, bool(by_base.get(m.group(1))))
        continue
    if re.fullmatch(r'test_[A-Za-z0-9_]+', c):
        out('test', c, c in defs or ('%s.py' % c) in by_base)
        continue
    if re.fullmatch(r'(P2|AM5|AM6|E\d+|AM3|AM2|AM4)[A-Za-z0-9_]+', c):
        out('class', c, c in classes)
        continue
print('BUILDER-EXECUTED: NOT INDEPENDENT. Cited test names checked against', sys.argv[1].rsplit('/', 1)[-1])
print('\n'.join(rows))
print('RESULT cited_names %s (%d checked, %d missing)' % ('HOLDS' if not missing else 'FAILS', len(rows), missing))
sys.exit(1 if missing else 0)
