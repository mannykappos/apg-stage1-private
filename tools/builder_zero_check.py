#!/usr/bin/env python3
"""Checks the Builder Zero synthetic data set. Python 3 standard library only; read-only except for a temporary regeneration.
It recomputes every planted fact from the CSV files themselves (it does not trust the generator's own statements).
Usage: python3 -I tools/builder_zero_check.py <builder_zero_dir> [--rtm path/to/RTM.csv] [--write-manifest]
Exit 0 only if every check passes."""
import csv, datetime as dt, hashlib, json, os, re, subprocess, sys, tempfile
args = [a for a in sys.argv[1:] if not a.startswith('--')]
root = args[0]
flags = sys.argv[1:]
HERE = os.path.dirname(os.path.abspath(__file__))
rtm_path = flags[flags.index('--rtm') + 1] if '--rtm' in flags else None
if rtm_path and rtm_path in args: args.remove(rtm_path)
fails = []; n = 0
def chk(cid, ok, text):
    global n; n += 1
    print(('PASS ' if ok else 'FAIL ') + cid + ' ' + text)
    if not ok: fails.append(cid)
def rd(rel):
    return list(csv.DictReader(open(os.path.join(root, rel), encoding='utf-8', newline='')))
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def files(base):
    out = []
    for d, _, fs in os.walk(base):
        for f in fs: out.append(os.path.relpath(os.path.join(d, f), base))
    return sorted(out)
D = dt.date.fromisoformat
ASOF = D('2026-09-30')
A, B = 'zero_one/', 'zero_two/'
mf = os.path.join(root, 'MANIFEST.sha256')
if '--write-manifest' in flags:
    with open(mf, 'w', newline='\n') as f:
        for p in files(root):
            if p != 'MANIFEST.sha256': f.write(f'{sha(os.path.join(root, p))}  {p}\n')
    print('manifest written'); sys.exit(0)

# Z01 manifest and regeneration
man = {}
for line in open(mf, encoding='utf-8'):
    h, p = line.rstrip('\n').split('  ', 1); man[p] = h
actual = {p: sha(os.path.join(root, p)) for p in files(root) if p != 'MANIFEST.sha256'}
chk('Z01', man == actual, f'manifest lists exactly the {len(actual)} files and every SHA-256 matches')
tmp = tempfile.mkdtemp()
gen = os.path.join(HERE, 'make_builder_zero.py')
subprocess.run([sys.executable, '-I', gen, tmp], check=True)
regen = {p: sha(os.path.join(tmp, p)) for p in files(tmp)}
chk('Z02', regen == actual, 'regenerating from the generator reproduces every file byte for byte (deterministic)')

# Z03 labelling
sup = rd(A + 'reference/suppliers.csv'); prj = rd(A + 'reference/projects.csv')
chk('Z03', all('(synthetic)' in s['name'] for s in sup) and all('Synthetic' in p['name'] for p in prj) and 'SYNTHETIC' in open(os.path.join(root, 'README.txt')).read(),
    'every supplier and project name is labelled synthetic; README says so')
deny = re.compile(r'\b(Procore|Xero|MYOB|Aconex|Hutchies|Lendlease|CIMIC|Multiplex|BlueScope|Boral|Holcim|Bunnings|Reece)\b', re.I)
alltext = ''.join(open(os.path.join(root, p), encoding='utf-8').read() for p in actual if p.endswith(('.csv', '.txt')))
chk('Z04', not deny.search(alltext), 'no real company or product name appears anywhere in the data')

# Z05 coverage of the 14 source categories
srcs = sorted({p.split('/')[1] for p in actual if p.startswith(A + 'SRC-')})
chk('Z05', [s[:6] for s in srcs] == [f'SRC-{i:02d}' for i in range(1, 15)], 'zero_one holds data for SRC-01 to SRC-14')
# Z06 integer money, GST rule
moneycols = ('cents',)
bad = []
for p in actual:
    if p.endswith('.csv'):
        for r in csv.DictReader(open(os.path.join(root, p), encoding='utf-8', newline='')):
            for k, v in r.items():
                if k and k.endswith(('_cents', '_cents_per_day', '_cents_per_hour', '_cents_per_unit')) and v not in ('', None):
                    if not re.fullmatch(r'-?\d+', v): bad.append((p, k, v))
chk('Z06', not bad, 'every money column holds whole integer cents ' + str(bad[:3]))
inv = rd(A + 'SRC-01_accounting/ap_invoices.csv')
gbad = [r['invoice_id'] for r in inv if r['gst_cents'] != '' and int(r['gst_cents']) != (int(r['ex_gst_cents']) + 5) // 10]
chk('Z07', not gbad, 'GST equals (ex + 5) // 10 on every invoice that states GST ' + str(gbad[:3]))
# Z08 date sanity
dbad = []
for r in inv:
    d = D(r['invoice_date'])
    if d > ASOF: dbad.append(r['invoice_id'])
pos = rd(A + 'SRC-03_procurement/purchase_orders.csv')
for r in pos:
    if D(r['po_date']) > ASOF: dbad.append(r['po_id'])
chk('Z08', not dbad, 'no invoice or purchase order is dated after the as-of date 2026-09-30 ' + str(dbad[:3]))
chk('Z09', len({r['invoice_id'] for r in inv}) == len(inv) and len({r['po_id'] for r in pos}) == len(pos), 'invoice IDs and PO IDs are unique within the tenant')

# Z10 tenant isolation set-up
invB = rd(B + 'SRC-01_accounting/ap_invoices.csv'); posB = rd(B + 'SRC-03_procurement/purchase_orders.csv')
ida = {r['invoice_id']: r for r in inv}
coll = [r['invoice_id'] for r in invB if r['invoice_id'] in ida]
diff = [i for i in coll if {k: v for k, v in ida[i].items()} != next(r for r in invB if r['invoice_id'] == i)]
chk('Z10', len(coll) >= 40 and diff and {r['project_id'] for r in rd(B + 'reference/projects.csv')} <= {r['project_id'] for r in prj}
    and {r['po_id'] for r in posB} & {r['po_id'] for r in pos},
    f'tenant two reuses {len(coll)} invoice IDs, PO IDs and a project ID that exist in tenant one, and {len(diff)} of those differ in content')
chk('Z11', [r for r in invB if r['invoice_id'] == 'INV-0001' and r['ex_gst_cents'] == '777700'] != [] and ida['INV-0001']['ex_gst_cents'] != '777700',
    'PS-24: INV-0001 exists in both tenants with different amounts')

# ---- recompute planted facts
bud = {(r['project_id'], r['cost_code']): int(r['budget_cents']) for r in rd(A + 'SRC-02_costing/budget_lines.csv')}
def act(p, c): return sum(int(r['ex_gst_cents']) for r in inv if r['project_id'] == p and r['cost_code'] == c and r['ex_gst_cents'])
chk('Z12', 117.9 < 100 * act('PRJ-002', 'CC-04') / bud[('PRJ-002', 'CC-04')] < 118.1, 'PS-01: PRJ-002 CC-04 actual is 118 percent of budget (recomputed from invoices and budget lines)')
chk('Z13', 97.9 < 100 * act('PRJ-002', 'CC-05') / bud[('PRJ-002', 'CC-05')] < 98.1, 'NC-01: PRJ-002 CC-05 actual is 98 percent of budget')
amd = {r['amendment_id']: r for r in rd(A + 'SRC-03_procurement/po_amendments.csv')}
var = {r['variation_id']: r for r in rd(A + 'SRC-07_commercial/variations.csv')}
chk('Z14', amd['AMD-001']['approved_change_ref'] == '' and var[amd['AMD-002']['approved_change_ref']]['status'] == 'approved', 'PS-02/NC-02: AMD-001 has no approved change; AMD-002 links to an approved variation')
po = {r['po_id']: r for r in pos}
def inv_for(sn): return next(r for r in inv if r['supplier_invoice_no'] == sn)
i1, i2 = inv_for('SI-70001'), inv_for('SI-70002')
def dev(i): p = po[i['po_id']]; return (int(i['ex_gst_cents']) / int(p['qty']) - int(p['unit_rate_cents'])) / int(p['unit_rate_cents'])
chk('Z15', dev(i1) > 0.07 and 0 < dev(i2) < 0.01, f'PS-03/NC-03: invoice rate is {dev(i1)*100:.1f} percent above PO (planted), {dev(i2)*100:.1f} percent above PO (control, within 1 percent)')
v1, v2 = var['VAR-0001'], var['VAR-0002']
chk('Z16', v1['value_cents'] == '' and (ASOF - D(v1['raised_date'])).days > 60 and v2['value_cents'] != '' and (ASOF - D(v2['raised_date'])).days <= 60, 'PS-04/NC-04: VAR-0001 is unpriced and over 60 days old; VAR-0002 is priced and recent')
ntc = rd(A + 'SRC-07_commercial/notices.csv')
chk('Z17', any(r['notice_type'] == 'client_instruction' and r['linked_variation_id'] == '' for r in ntc), 'PS-04b: a client instruction exists with no linked variation')
ret = [r for r in rd(A + 'SRC-09_retentions/retention_ledger.csv') if r['project_id'] == 'PRJ-001'][0]
chk('Z18', D(ret['release_due_date']) < ASOF and ret['released_date'] == '' and ret['hold_reason'] == '', 'PS-05: PRJ-001 retention is past its release date, unreleased, with no hold reason')
comp = {(r['supplier_id'], r['evidence_type']): D(r['expiry_date']) for r in rd(A + 'SRC-06_supplier_compliance/supplier_compliance.csv')}
others = [d for (s, t), d in comp.items() if (s, t) not in (('SUP-005', 'public_liability_insurance'), ('SUP-008', 'licence'))]
chk('Z19', 0 < (comp[('SUP-005', 'public_liability_insurance')] - ASOF).days <= 30 and comp[('SUP-008', 'licence')] < ASOF and all((d - ASOF).days > 30 for d in others), 'PS-06/NC-06: one insurance expires within 30 days, one licence has expired, all others are more than 30 days out')
q = {r['quote_id']: r for r in rd(A + 'SRC-03_procurement/quotes.csv')}
landed2 = int(q['Q-0002']['unit_rate_cents']) + int(q['Q-0002']['freight_cents_per_unit'])
chk('Z20', int(q['Q-0001']['unit_rate_cents']) > landed2 > int(po['PO-0001']['unit_rate_cents']) * 0 and q['Q-0001']['incoterm_delivery_basis'] == 'delivered' and q['Q-0002']['incoterm_delivery_basis'] == 'ex-works',
    f'PS-07: delivered quote {q["Q-0001"]["unit_rate_cents"]} exceeds landed ex-works {landed2}; bases differ (needs landed-cost adjustment)')
chk('Z21', q['Q-0003']['specification'] != '' and 'MPa' in q['Q-0003']['specification'] and q['Q-0003']['material_id'] == 'MAT-CONC32', 'PS-15: the cheaper concrete quote is for 32 MPa, a different specification from the 40 MPa demand')
mk = rd(A + 'SRC-10_market/market_observations.csv')
cu_last = max(D(r['obs_date']) for r in mk if r['material_id'] == 'MAT-CU')
chk('Z22', D(q['Q-0004']['valid_until']) < ASOF and (ASOF - cu_last).days > 120, 'PS-14: quote Q-0004 has expired and the last copper observation is more than 120 days old')
fx = rd(A + 'SRC-10_market/fx_rates.csv')
chk('Z23', q['Q-0005']['currency'] == 'USD' and q['Q-0005']['fx_rate_used'] != '' and (max(D(r['fx_date']) for r in fx) - D(q['Q-0005']['fx_rate_date'])).days > 90, 'PS-23: USD quote carries an FX rate more than 90 days older than the latest rate on file')
pb = [int(r['unit_rate_cents']) for r in pos if r['material_id'] == 'MAT-PBOARD' and r['unit_rate_cents']]
mean_pb = sum(pb) / len(pb)
chk('Z24', len(pb) >= 5 and (mean_pb - int(q['Q-0006']['unit_rate_cents'])) / mean_pb > 0.05, f'PS-25: the plasterboard quote is {100*(mean_pb-int(q["Q-0006"]["unit_rate_cents"]))/mean_pb:.1f} percent below the mean plasterboard PO rate')
pbad = [r['po_id'] for r in pos if r['unit_rate_cents'] and (int(r['unit_rate_cents']) <= 0 or int(r['qty']) * int(r['unit_rate_cents']) != int(r['amount_cents']))]
chk('Z43', not pbad, 'every PO amount equals quantity times unit rate and every rate is positive ' + str(pbad[:3]))
st = [int(r['value']) for r in sorted([r for r in mk if r['material_id'] == 'MAT-STEEL'], key=lambda r: r['obs_date'])][-4:]
dem = [r for r in rd(A + 'SRC-05_materials/material_demand.csv') if r['demand_id'] == 'DEM-0001'][0]
chk('Z25', st == sorted(st) and 100 * (st[-1] - st[0]) / st[0] > 8 and dem['material_id'] == 'MAT-STEEL' and D(q['Q-0001']['valid_until']) >= ASOF,
    f'PS-16: steel index rose {100*(st[-1]-st[0])/st[0]:.1f} percent over the last four observations; demand is unplaced; quotes still valid')
hire = {r['hire_id']: r for r in rd(A + 'SRC-13_plant/plant_hire.csv')}
h1 = hire['HIRE-001']; h2 = hire['HIRE-002']
chk('Z26', h1['off_hire_date'] == '' and (ASOF - D(h1['needed_until'])).days == 183 and h2['off_hire_date'] == '' and D(h2['needed_until']) >= ASOF, 'PS-08/NC-08: HIRE-001 is 183 days past need; HIRE-002 is within need')
fc = {(r['project_id'], r['cost_code'], r['forecast_version']): r for r in rd(A + 'SRC-02_costing/forecasts.csv')}
a_, b_ = fc[('PRJ-002', 'CC-09', 'F-2026-08')], fc[('PRJ-002', 'CC-09', 'F-2026-09')]
chk('Z27', b_['movement_reason'] == '' and int(b_['cost_to_complete_cents']) > 5 * int(a_['cost_to_complete_cents']), 'PS-09: PRJ-002 CC-09 forecast moved by more than 5 times with no movement reason')
split = [r for r in pos if r['supplier_id'] == 'SUP-003' and r['project_id'] == 'PRJ-002' and r['po_date'] in ('2026-08-03', '2026-08-09', '2026-08-14')]
thr = json.load(open(os.path.join(root, 'scenarios/test_thresholds.json')))['single_order_materiality_abs_cents']
ds = sorted(D(r['po_date']) for r in split)
chk('Z28', len(split) == 3 and all(int(r['amount_cents']) < thr for r in split) and sum(int(r['amount_cents']) for r in split) >= thr and (ds[-1] - ds[0]).days <= 30, 'PS-10: three POs each below the illustrative single-order level, together above it, inside 30 days')
nc = [r for r in pos if r['supplier_id'] == 'SUP-010' and r['po_date'] in ('2026-03-02', '2026-05-04', '2026-07-06')]
dn = sorted(D(r['po_date']) for r in nc)
chk('Z29', len(nc) == 3 and all(int(r['amount_cents']) < thr for r in nc) and sum(int(r['amount_cents']) for r in nc) >= thr and all((dn[i + 1] - dn[i]).days > 30 for i in range(2)), 'NC-10: same amounts but each pair more than 30 days apart (outside the window)')
dups = {}
for r in inv: dups.setdefault((r['supplier_id'], r['supplier_invoice_no'], r['ex_gst_cents']), []).append(r)
dd = [v for v in dups.values() if len(v) == 2 and v[0]['source_batch'] != v[1]['source_batch'] and v[0]['invoice_id'] != v[1]['invoice_id']]
chk('Z30', len(dd) == 1, 'PS-11: exactly one invoice appears twice (same supplier, number and amount) from two different batches')
cn = rd(A + 'SRC-01_accounting/credit_notes.csv')
c1 = cn[0]; oi = ida[c1['against_invoice_id']]; ri = inv_for('SI-80001R')
chk('Z31', len(cn) == 1 and c1['ex_gst_cents'] == oi['ex_gst_cents'] and ri['supplier_id'] == oi['supplier_id'] and int(ri['ex_gst_cents']) < int(oi['ex_gst_cents']), 'PS-12: one credit note fully reverses an invoice and a smaller replacement invoice follows')
pm = rd(A + 'conflicting_sources/pm_system_invoices.csv')
chk('Z32', len(pm) == 1 and pm[0]['invoice_ref'] in ida and int(pm[0]['ex_gst_cents']) != int(ida[pm[0]['invoice_ref']]['ex_gst_cents']), 'PS-13: the PM-system record disagrees with the accounting record on the amount')
mp = [r for r in pos if r['cost_code'] == ''][0]; mi = inv_for('SI-80002')
chk('Z33', mp['project_id'] and mi['gst_cents'] == '' and mi['po_id'] == mp['po_id'], 'PS-21: a PO with no cost code and an invoice with no GST amount are present and linked')
names = {s['name'] for s in sup}
am = inv_for('SI-90001')
mstyle = [s for s in sup if 'Metro Steel' in s['name']]
chk('Z34', len(mstyle) == 2 and am['supplier_id'] not in {s['supplier_id'] for s in sup} and 'Metro Steel' in am['supplier_id'], 'PS-22: the invoice supplier text matches two supplier records and no supplier ID')
dl = rd(A + 'SRC-05_materials/deliveries.csv')
sur = [r for r in pos if r['project_id'] == 'PRJ-001' and r['material_id'] == 'MAT-PBOARD' and r['po_date'] == '2026-08-25']
d2 = [r for r in rd(A + 'SRC-05_materials/material_demand.csv') if r['demand_id'] == 'DEM-0002'][0]
chk('Z35', len(sur) == 2 and sum(int(r['qty']) for r in sur) - int(d2['qty']) == 600, 'PS-17: two same-day POs exceed demand by 600 sheets')
de = rd(A + 'SRC-04_programme/delay_events.csv')
def wd(a, b):
    x, c = D(a), 0
    while x <= D(b):
        c += x.weekday() < 5; x += dt.timedelta(days=1)
    return c
ov = (D(de[0]['end_date']) - D(de[1]['start_date'])).days + 1
chk('Z36', len(de) == 2 and wd(de[0]['start_date'], de[0]['end_date']) == int(de[0]['working_days']) and wd(de[1]['start_date'], de[1]['end_date']) == int(de[1]['working_days']) and ov > 0 and de[0]['activity_id'] == de[1]['activity_id'], f'PS-18: two delay events on one activity overlap by {ov} days; stated working days match the calendar')
ts = rd(A + 'SRC-12_labour/timesheets.csv'); wo = sorted([r for r in rd(A + 'SRC-12_labour/work_output.csv')], key=lambda r: r['week_start'])
hrs = {}
for r in ts: hrs[r['work_date'][:0] or None] = 0
byweek = {}
for r in ts:
    d = D(r['work_date']); wk = (d - dt.timedelta(days=d.weekday())).isoformat(); byweek[wk] = byweek.get(wk, 0) + int(r['ordinary_hours']) + int(r['overtime_hours'])
prod = [int(r['quantity']) / byweek[r['week_start']] for r in wo if r['week_start'] in byweek]
chk('Z37', len(prod) >= 8 and all(prod[i] > prod[i + 1] for i in range(len(prod) - 8, len(prod) - 1)) and prod[-1] < 0.75 * prod[-8], f'PS-19: output per hour falls every week across the last 8 weeks (down {100*(1-prod[-1]/prod[-8]):.0f} percent)')
df = sorted(rd(A + 'SRC-08_quality/defects.csv'), key=lambda r: r['raised_date'])
cs = [int(r['rework_cost_cents']) for r in df]
chk('Z38', len(df) == 3 and len({(r['subcontractor'], r['trade']) for r in df}) == 1 and cs == sorted(cs) and cs[-1] > 2 * cs[0], 'PS-20: three defects, same subcontractor and trade, rework cost more than doubling')
docs = rd(A + 'SRC-11_documents/documents_index.csv')
tx = open(os.path.join(root, A + 'SRC-11_documents/quote_ambiguous_SUP-004.txt')).read()
chk('Z39', len(docs) == 2 and docs[1]['ambiguity'] != '' and '4O' in tx and all(os.path.exists(os.path.join(root, A + 'SRC-11_documents/' + d['file'])) for d in docs), 'PS-26: two documents exist; the ambiguous one contains an O-for-zero reading problem')

# register
reg = rd('scenarios/SCENARIO_REGISTER.csv')
rids = [r['scenario_id'] for r in reg]
ps = [r for r in reg if r['scenario_id'].startswith('PS-')]
chk('Z40', len(rids) == len(set(rids)) and len([r for r in ps if r['scenario_id'][3:].isdigit()]) == 26 and all(r['expected_behaviour'] and r['acceptance_ids'] and r['blueprint_rule_ref'] for r in reg), f'register: {len(reg)} scenarios, PS-01 to PS-26 all present, every row has a rule, acceptance IDs and expected behaviour')
chk('Z41', not any(re.search(r'\b(passed|proved|validated|confirmed)\b', r['expected_behaviour'], re.I) for r in reg) and 'ILLUSTRATIVE' in open(os.path.join(root, 'scenarios/test_thresholds.json')).read(), 'register states expected behaviour only (no result claims); thresholds file is marked illustrative')
if rtm_path:
    rtm = list(csv.DictReader(open(rtm_path, encoding='utf-8-sig')))
    known = {r['requirement_id'] for r in rtm} | {r['source_explicit_id'] for r in rtm if r['source_explicit_id']}
    miss = [(r['scenario_id'], a.strip()) for r in reg for a in r['acceptance_ids'].split(';') if a.strip() not in known]
    chk('Z42', not miss, 'every acceptance ID cited in the register exists in the RTM ' + str(miss))
else:
    print('SKIP Z42 (no --rtm given)')
print(f'\nchecks {n}  failed {len(fails)}')
if fails: print('FAILED:', fails); sys.exit(1)
print('ALL BUILDER ZERO CHECKS PASS')
