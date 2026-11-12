"""Data Readiness revision 4 (after GPT's check of revision 4): the fields each rule's and figure's code path reads, taken from the code, so
the input contracts can be checked against the code and not only against themselves.  Builder work (Claude), not independent.

For every row of RULE_INPUT_CONTRACTS.csv whose 'code' column names entry functions (rows starting 'every' state shared behaviour and
are skipped), it parses the production modules with Python's ast
module and follows the code path (the modules are those of fin, det, mkt and ingest, plus source_authority.py, policy_approval.py and
materiality.py):
  - the entry functions named in the 'code' column, and every function they call, transitively: a call by name resolves to a function
    of the same module or one it imports; a call through a module alias resolves to that module; a method call (x.name(...)) resolves to
    every function or method of that name in the scanned modules, unless the name is a common built-in method (GENERIC);
  - an attribute read of the M6 context (ctx.quotes, ctx.pos) adds the view functions Ctx.__init__ builds it with;
  - a module-level name a function on the path uses, its own or imported (for example SPECS, DET_SPECS), adds that assignment's string
    constants.
On that path, every string constant that is a field name of a record kind the row names is a field the path reads (FIELD_REGISTER.csv
gives each kind's fields).  Within the kinds a row names it over-includes: a shared helper on the path (a view of every purchase order,
say) counts every field it reads for every row that reaches it.  It does not count kinds the row's text does not name, and it skips the
rows that name no entry function (the 'every' rows and five rows that describe part of another row's path).  It is a check against the
code by these rules, not a proof.  GENERIC lists common method names a call is never resolved to; function-local imports are not
followed (none matters today).
It writes CODE_READS.csv (one row per contract row that names entry functions: the kinds named, the entry functions found, how many
functions the path holds, and the fields the path reads) and fails if an entry function cannot be found.  build_field_coverage.py then
adds every field the path reads to the field-level report, so the report no longer rests only on the fields the contract text names.
usage: python3 -I build_code_reads.py <the apg folder> <folder with RULE_INPUT_CONTRACTS.csv and FIELD_REGISTER.csv>"""
import ast, csv, os, re, sys, collections

APG, REG = sys.argv[1], sys.argv[2]
SKIP = re.compile(r'(corpus|demo_|faulty|golden|reference_|contracts_|ports_)')
GENERIC = {'get', 'items', 'keys', 'values', 'append', 'extend', 'update', 'setdefault', 'pop', 'sort', 'join', 'split', 'strip', 'lower', 'upper',
           'startswith', 'endswith', 'format', 'replace', 'add', 'count', 'index', 'copy', 'encode', 'decode', 'isoformat', 'fromisoformat', 'read',
           'write', 'close', 'group', 'match', 'search', 'fullmatch', 'sub', 'findall', 'reason', 'limit', 'finish', 'cannot', 'unknown', 'exclude',
           'dispute', 'classify', 'contribute', 'child', 'say', 'log'}

# ---- parse the modules
mods = {}
for top in ('fin', 'det', 'mkt', 'ingest'):
    for dp, dn, fn in os.walk(os.path.join(APG, top)):
        if '__pycache__' in dp:
            continue
        for f in sorted(fn):
            if f.endswith('.py') and not SKIP.search(f):
                mods[os.path.relpath(os.path.join(dp, f), APG).replace(os.sep, '/')] = None
for x in ('source_authority.py', 'policy_approval.py', 'materiality.py'):
    if os.path.exists(os.path.join(APG, x)):
        mods[x] = None
for m in list(mods):
    mods[m] = ast.parse(open(os.path.join(APG, m)).read())

def modpath(cur, level, name):
    """resolve a relative import to a module path in mods, or None"""
    base = cur.split('/')[:-1]
    if level:
        base = base[:len(base) - (level - 1)] if level > 1 else base
    parts = base + (name.split('.') if name else [])
    p = '/'.join(parts) + '.py'
    return p if p in mods else None

funcs = {}                     # (module, qualname) -> node
byname = collections.defaultdict(list)
modconst = {}                  # (module, NAME) -> set of string constants
alias = collections.defaultdict(dict)       # module -> {alias: module}
imported = collections.defaultdict(dict)    # module -> {name: (module, name)}
for m, tree in mods.items():
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs[(m, node.name)] = node; byname[node.name].append((m, node.name))
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    q = node.name + '.' + sub.name
                    funcs[(m, q)] = sub; byname[sub.name].append((m, q))
            byname[node.name].append((m, node.name + '.__init__'))
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            strs = {c.value for c in ast.walk(node.value) if isinstance(c, ast.Constant) and isinstance(c.value, str)}
            for nm in names:
                modconst[(m, nm)] = strs
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                tgt = modpath(m, node.level, (node.module or '') + ('' if node.module is None else ''))
                sub = modpath(m, node.level, ((node.module + '.') if node.module else '') + a.name)
                if sub:
                    alias[m][a.asname or a.name] = sub
                elif tgt:
                    imported[m][a.asname or a.name] = (tgt, a.name)

# M6 context attributes -> the functions that build them (Ctx.__init__: self.attr = ...)
ctx_attr = collections.defaultdict(set)
for (m, q), node in funcs.items():
    if q.endswith('Ctx.__init__'):
        for st in ast.walk(node):
            if isinstance(st, ast.Assign) and isinstance(st.targets[0], ast.Attribute):
                for c in ast.walk(st.value):
                    if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and isinstance(c.func.value, ast.Name):
                        tm = alias[m].get(c.func.value.id)
                        if tm and (tm, c.func.attr) in funcs:
                            ctx_attr[st.targets[0].attr].add((tm, c.func.attr))

def callees(m, node):
    out = set()
    for c in ast.walk(node):
        if isinstance(c, ast.Call):
            f = c.func
            if isinstance(f, ast.Name):
                if (m, f.id) in funcs:
                    out.add((m, f.id))
                elif f.id in imported[m] and imported[m][f.id] in funcs:
                    out.add(imported[m][f.id])
                elif f.id in byname and any(q.endswith('.__init__') for _, q in byname[f.id]):
                    out |= {k for k in byname[f.id] if k in funcs}
            elif isinstance(f, ast.Attribute):
                if isinstance(f.value, ast.Name) and f.value.id in alias[m]:
                    k = (alias[m][f.value.id], f.attr)
                    if k in funcs:
                        out.add(k)
                elif f.attr not in GENERIC:
                    out |= {k for k in byname.get(f.attr, []) if k in funcs}
        if isinstance(c, ast.Attribute) and c.attr in ctx_attr:
            out |= ctx_attr[c.attr]
    return out

def closure(entries):
    seen, todo = set(), list(entries)
    while todo:
        k = todo.pop()
        if k in seen or k not in funcs:
            continue
        seen.add(k)
        todo += list(callees(k[0], funcs[k]))
    return seen

def strings(keys):
    out = set()
    for (m, q) in keys:
        node = funcs[(m, q)]
        for c in ast.walk(node):
            if isinstance(c, ast.Constant) and isinstance(c.value, str):
                out.add(c.value)
            if isinstance(c, ast.Name) and (m, c.id) in modconst:
                out |= modconst[(m, c.id)]
            if isinstance(c, ast.Name) and c.id in imported[m] and imported[m][c.id] in modconst:      # an imported constant (SPECS, DET_SPECS)
                out |= modconst[imported[m][c.id]]
            if isinstance(c, ast.Attribute) and isinstance(c.value, ast.Name) and c.value.id in alias[m] and (alias[m][c.value.id], c.attr) in modconst:
                out |= modconst[(alias[m][c.value.id], c.attr)]
    return out

# ---- the registers
reg = collections.defaultdict(set)
for f in csv.DictReader(open(os.path.join(REG, 'FIELD_REGISTER.csv'))):
    reg[f['record_kind']].add(f['field'])
contracts = list(csv.DictReader(open(os.path.join(REG, 'RULE_INPUT_CONTRACTS.csv'))))

def entries_of(code):
    """'mkt/rules.py mp02_not_comparable; mkt/demand.py coverage' -> [(module, function)]; a part with no function names gives none"""
    out, cur = [], None
    for part in [p.strip() for p in code.split(';')]:
        toks = re.findall(r'[A-Za-z_][\w./*]*', part)
        names = []
        for t in toks:
            if t.endswith('.py'):
                cur = t if t in mods else ('/'.join((cur or '').split('/')[:-1] + [t]) if cur and '/' not in t else t)
            else:
                names.append(t)
        for n in names:
            hits = [k for k in funcs if k[0] == cur and (k[1] == n or k[1].endswith('.' + n))]
            if not hits:
                sys.exit('entry function not found: %s in %s' % (n, cur))
            out += hits
    return out

rows = []
for i, r in enumerate(contracts):
    if r['rule or figure'].startswith('every '):
        continue
    ent = entries_of(r['code'])
    kinds = sorted({t for t in re.findall(r'[a-z][a-z_]*[a-z]', r['record kinds and fields']) if t in reg})
    if not ent:
        rows.append({'contract row': i + 2, 'rule or figure': r['rule or figure'], 'kinds named': ' '.join(kinds) or '-', 'entry functions': '-', 'functions on the path': 0,
                     'fields the code path reads (upper bound)': '-', 'note': 'no entry function named: the row describes a part of another row\'s path'})
        continue
    path = closure(ent)
    s = strings(path)
    read = sorted({'%s.%s' % (k, f) for k in kinds for f in reg[k] if f in s})
    rows.append({'contract row': i + 2, 'rule or figure': r['rule or figure'], 'kinds named': ' '.join(kinds) or '-', 'entry functions': ' '.join('%s:%s' % k for k in ent),
                 'functions on the path': len(path), 'fields the code path reads (upper bound)': ' '.join(read) or '-', 'note': ''})
with open('CODE_READS.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)
print('rows', len(rows), 'fields read on the paths', sum(len(x['fields the code path reads (upper bound)'].split()) for x in rows if x['fields the code path reads (upper bound)'] != '-'))
