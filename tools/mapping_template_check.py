#!/usr/bin/env python3
"""Validates APG file-import mapping templates and dry-runs their headers against sample files. Python 3 standard library only; read-only.
Usage: python3 -I tools/mapping_template_check.py <templates_dir> <builder_zero_dir>      Exit 0 only if every check passes."""
import csv, json, os, re, sys
TD, BZ = sys.argv[1], sys.argv[2]
TYPES = {'string', 'integer', 'date', 'money_cents', 'decimal', 'enum', 'boolean'}
TRANSFORMS = {'none', 'trim', 'upper', 'parse_date', 'dollars_to_cents'}
TENANT_NAMES = {'tenant_id', 'tenant', 'tenant_ref', 'org_id', 'organisation_id'}
fails = []; n = 0
def chk(cid, ok, text):
    global n; n += 1
    print(('PASS ' if ok else 'FAIL ') + cid + ' ' + text)
    if not ok: fails.append(cid)
def validate(t):
    """returns a list of problems (empty = valid)"""
    p = []
    for k in ('format_version', 'template_id', 'status', 'tenant_binding', 'source_category', 'file', 'money', 'natural_key', 'target_entity', 'columns', 'unmapped_columns_policy', 'on_row_error'):
        if k not in t: p.append('missing ' + k)
    if p: return p
    if t['format_version'] != 'apg-mapping-template-1.0': p.append('format_version')
    if t['tenant_binding'] != 'authenticated_context': p.append('tenant must come from the authenticated context, never from the file')
    if not t['status'].startswith('draft'): p.append('status must be a draft until verified against a real export')
    if not re.fullmatch(r'SRC-(0[1-9]|1[0-4])', t['source_category']): p.append('source_category')
    if t['money']['unit'] not in ('cents', 'dollars'): p.append('money.unit')
    tf = [c['target_field'] for c in t['columns']]; sc = [c['source_column'] for c in t['columns']]
    if len(set(tf)) != len(tf): p.append('duplicate target_field')
    if len(set(sc)) != len(sc): p.append('duplicate source_column')
    for c in t['columns']:
        if c['type'] not in TYPES: p.append('type ' + c['type'])
        if c.get('transform', 'none') not in TRANSFORMS: p.append('transform ' + str(c.get('transform')))
        if c['target_field'].lower() in TENANT_NAMES: p.append('a column may not set the tenant: ' + c['target_field'])
        if c['type'] == 'date' and not c.get('date_format'): p.append('date column needs date_format: ' + c['source_column'])
        if c['type'] == 'date' and c.get('transform') != 'parse_date': p.append('date column needs parse_date')
        if c['type'] == 'enum' and not c.get('allowed'): p.append('enum needs allowed list')
        if c['type'] == 'money_cents' and t['money']['unit'] == 'dollars' and c.get('transform') != 'dollars_to_cents': p.append('dollar file: money column needs dollars_to_cents: ' + c['source_column'])
        if c['type'] == 'money_cents' and t['money']['unit'] == 'cents' and c.get('transform') == 'dollars_to_cents': p.append('cents file must not convert dollars')
        if c.get('transform') == 'dollars_to_cents' and c['type'] != 'money_cents': p.append('dollars_to_cents only on money_cents')
        if c['type'] in ('decimal',) and c.get('transform') == 'dollars_to_cents': p.append('decimal conversion')
    if not set(t['natural_key']) <= set(sc): p.append('natural_key must name mapped source columns')
    if not any(c['required'] for c in t['columns']): p.append('no required column')
    return p
tpls = {}
for f in sorted(os.listdir(TD)):
    if f.endswith('.json'): tpls[f] = json.load(open(os.path.join(TD, f)))
chk('M01', len(tpls) >= 4, f'{len(tpls)} example templates found')
allp = {f: validate(t) for f, t in tpls.items()}
chk('M02', all(not p for p in allp.values()), 'every example template passes structural validation ' + str({f: p for f, p in allp.items() if p}))
chk('M03', len({t['template_id'] for t in tpls.values()}) == len(tpls) and all(f == t['template_id'] + '.json' for f, t in tpls.items()), 'template IDs are unique and match file names')
BZMAP = {'TPL-BZ-AP-INVOICES': 'zero_one/SRC-01_accounting/ap_invoices.csv', 'TPL-BZ-PURCHASE-ORDERS': 'zero_one/SRC-03_procurement/purchase_orders.csv', 'TPL-BZ-QUOTES': 'zero_one/SRC-03_procurement/quotes.csv',
         'TPL-EX-ACCOUNTING-DOLLARS': None}
bad = []
for t in tpls.values():
    path = BZMAP.get(t['template_id'])
    full = os.path.join(BZ, path) if path else os.path.join(TD, 'samples/EX_accounting_dollars.csv')
    enc = t['file']['encoding']
    hdr = next(csv.reader(open(full, encoding=enc, newline=''), delimiter=t['file']['delimiter']))
    mapped = [c['source_column'] for c in t['columns']]
    if any(m not in hdr for m in mapped): bad.append((t['template_id'], [m for m in mapped if m not in hdr]))
    if t['template_id'].startswith('TPL-BZ') and [h for h in hdr if h not in mapped]: bad.append((t['template_id'], 'unmapped', [h for h in hdr if h not in mapped]))
chk('M04', not bad, 'dry run: every mapped source column exists in the sample header; the Builder Zero templates cover every column of their file ' + str(bad))
# sabotage self-tests of the validator
good = json.loads(json.dumps(tpls['TPL-BZ-AP-INVOICES.json']))
def mut(fn):
    t = json.loads(json.dumps(good)); fn(t); return validate(t)
tests = {
 'tenant from file': lambda t: t['columns'].append({'source_column': 'x', 'target_field': 'tenant_id', 'type': 'string', 'required': False}),
 'tenant binding changed': lambda t: t.__setitem__('tenant_binding', 'file'),
 'unknown type': lambda t: t['columns'][0].__setitem__('type', 'float'),
 'unknown transform': lambda t: t['columns'][0].__setitem__('transform', 'eval'),
 'date without format': lambda t: t['columns'][6].pop('date_format'),
 'duplicate target': lambda t: t['columns'][1].__setitem__('target_field', 'source_record_id'),
 'natural key unmapped': lambda t: t.__setitem__('natural_key', ['nope']),
 'status claims verified': lambda t: t.__setitem__('status', 'verified'),
 'cents file converts dollars': lambda t: t['columns'][7].__setitem__('transform', 'dollars_to_cents'),
 'enum without list': lambda t: t['columns'].append({'source_column': 'y', 'target_field': 'yy', 'type': 'enum', 'required': False}),
 'bad category': lambda t: t.__setitem__('source_category', 'SRC-99'),
}
missed = [k for k, fn in tests.items() if not mut(fn)]
chk('M05', not missed, f'validator rejects all {len(tests)} deliberately broken templates ' + str(missed))
print(f'\nchecks {n}  failed {len(fails)}')
if fails: print('FAILED:', fails); sys.exit(1)
print('ALL MAPPING-TEMPLATE CHECKS PASS')
