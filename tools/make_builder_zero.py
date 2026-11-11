#!/usr/bin/env python3
"""Builder Zero: a deterministic SYNTHETIC Victorian commercial builder (two fictional tenants) with planted scenarios.
Every name, number and document is invented. All money is integer cents (AUD). Dates are ISO YYYY-MM-DD. As-of date 2026-09-30.
Usage: make_builder_zero.py <output_dir>      (stdlib only; same output every run)"""
import csv, datetime as dt, json, os, random, sys

OUT = sys.argv[1]
ASOF = dt.date(2026, 9, 30)
D = lambda s: dt.date.fromisoformat(s)
iso = lambda d: d.isoformat()
gst = lambda ex: (ex + 5) // 10          # 10% GST, whole cents, rounded half up
GEN_VERSION = 'builder-zero-1.0'

PROJECTS = [  # id, name, contract_cents, start, planned_finish
    ('PRJ-001', 'Synthetic Office Fitout', 480_000_000, '2025-03-03', '2026-11-30'),
    ('PRJ-002', 'Synthetic Mixed-Use Four Storey', 1_850_000_000, '2025-05-01', '2027-02-26'),
    ('PRJ-003', 'Synthetic Warehouse', 920_000_000, '2025-08-01', '2026-12-18'),
]
CODES = [('CC-01', 'Preliminaries', 8), ('CC-02', 'Earthworks', 6), ('CC-03', 'Concrete', 14), ('CC-04', 'Structural steel', 12), ('CC-05', 'Masonry', 6),
         ('CC-06', 'Timber framing', 8), ('CC-07', 'Mechanical services', 12), ('CC-08', 'Electrical', 10), ('CC-09', 'Finishes', 16), ('CC-10', 'External works', 8)]
SUPPLIERS = [  # id, name
    ('SUP-001', 'SYN Ready-Mix Concrete Pty Ltd (synthetic)'), ('SUP-002', 'SYN Timber Frames Pty Ltd (synthetic)'), ('SUP-003', 'SYN Reo and Mesh Pty Ltd (synthetic)'),
    ('SUP-004', 'SYN Metro Steel Pty Ltd (synthetic)'), ('SUP-005', 'SYN Electrical Wholesale Pty Ltd (synthetic)'), ('SUP-006', 'SYN Plasterboard Direct Pty Ltd (synthetic)'),
    ('SUP-007', 'SYN Copper and Pipe Pty Ltd (synthetic)'), ('SUP-008', 'SYN Earthmoving Pty Ltd (synthetic)'), ('SUP-009', 'SYN Metro Steel and Fixings Pty Ltd (synthetic)'),
    ('SUP-010', 'SYN Masonry Supplies Pty Ltd (synthetic)'), ('SUP-011', 'SYN Imported Fixings Pty Ltd (synthetic)'), ('SUP-012', 'SYN Plant Hire Pty Ltd (synthetic)')]
MATERIALS = [('MAT-REO', 'Reinforcing bar N16', 'tonne'), ('MAT-CONC40', 'Concrete 40 MPa', 'm3'), ('MAT-CONC32', 'Concrete 32 MPa', 'm3'),
             ('MAT-STEEL', 'Structural steel sections', 'tonne'), ('MAT-TIMB', 'LVL timber', 'm3'), ('MAT-PBOARD', 'Plasterboard 13mm sheet', 'sheet'), ('MAT-CU', 'Copper pipe 22mm', 'metre')]
BASE_RATE = {'MAT-REO': 245_000, 'MAT-CONC40': 31_500, 'MAT-CONC32': 28_900, 'MAT-STEEL': 245_000, 'MAT-TIMB': 169_000, 'MAT-PBOARD': 1_850, 'MAT-CU': 1_950}   # cents per unit

rows = {}      # relative path -> (header, rows)
def table(path, header):
    rows[path] = (header, [])
    return rows[path][1]
def put(path, *vals): rows[path][1].append(list(vals))
SC = []        # scenario register rows

def build_tenant(code, rnd, full):
    P = f'{code}/'
    projects = table(P + 'reference/projects.csv', ['project_id', 'name', 'contract_value_cents', 'start_date', 'planned_finish'])
    codes = table(P + 'reference/cost_codes.csv', ['cost_code', 'name'])
    sup = table(P + 'reference/suppliers.csv', ['supplier_id', 'name', 'abn_synthetic'])
    mat = table(P + 'reference/materials.csv', ['material_id', 'description', 'unit'])
    for p in PROJECTS[: 3 if full else 1]: put(P + 'reference/projects.csv', *p)
    for c in CODES: put(P + 'reference/cost_codes.csv', c[0], c[1])
    for i, (s, n) in enumerate(SUPPLIERS[: 12 if full else 4]): put(P + 'reference/suppliers.csv', s, n, f'00 000 {i + 1:03d} 000')
    for m in MATERIALS: put(P + 'reference/materials.csv', *m)
    inv = table(P + 'SRC-01_accounting/ap_invoices.csv', ['invoice_id', 'supplier_id', 'supplier_invoice_no', 'project_id', 'cost_code', 'po_id', 'invoice_date', 'ex_gst_cents', 'gst_cents', 'status', 'source_batch'])
    crn = table(P + 'SRC-01_accounting/credit_notes.csv', ['credit_id', 'supplier_id', 'against_invoice_id', 'credit_date', 'ex_gst_cents', 'gst_cents'])
    pay = table(P + 'SRC-01_accounting/payments.csv', ['payment_id', 'invoice_id', 'payment_date', 'amount_cents'])
    bud = table(P + 'SRC-02_costing/budget_lines.csv', ['project_id', 'cost_code', 'budget_cents', 'revision', 'revision_date'])
    fc = table(P + 'SRC-02_costing/forecasts.csv', ['project_id', 'cost_code', 'forecast_version', 'forecast_date', 'cost_to_complete_cents', 'estimate_basis', 'movement_reason'])
    po = table(P + 'SRC-03_procurement/purchase_orders.csv', ['po_id', 'supplier_id', 'project_id', 'cost_code', 'po_date', 'material_id', 'qty', 'unit', 'unit_rate_cents', 'amount_cents', 'status'])
    poa = table(P + 'SRC-03_procurement/po_amendments.csv', ['amendment_id', 'po_id', 'amendment_date', 'delta_cents', 'approved_change_ref', 'reason'])
    qt = table(P + 'SRC-03_procurement/quotes.csv', ['quote_id', 'supplier_id', 'material_id', 'specification', 'issue_date', 'valid_until', 'unit_rate_cents', 'currency', 'fx_rate_used', 'fx_rate_date', 'freight_cents_per_unit', 'incoterm_delivery_basis', 'lead_time_days', 'price_kind'])
    act = table(P + 'SRC-04_programme/activities.csv', ['activity_id', 'project_id', 'name', 'baseline_start', 'baseline_finish', 'forecast_start', 'forecast_finish', 'actual_start', 'actual_finish', 'percent_complete'])
    dly = table(P + 'SRC-04_programme/delay_events.csv', ['event_id', 'project_id', 'activity_id', 'start_date', 'end_date', 'working_days', 'recorded_cause', 'holding_cost_rate_cents_per_day'])
    dem = table(P + 'SRC-05_materials/material_demand.csv', ['demand_id', 'project_id', 'material_id', 'qty', 'unit', 'required_on_site'])
    dlv = table(P + 'SRC-05_materials/deliveries.csv', ['docket_id', 'po_id', 'material_id', 'delivery_date', 'qty_delivered', 'qty_accepted'])
    cmp_ = table(P + 'SRC-06_supplier_compliance/supplier_compliance.csv', ['supplier_id', 'evidence_type', 'expiry_date'])
    con = table(P + 'SRC-07_commercial/contracts.csv', ['project_id', 'original_contract_cents', 'approved_variations_cents'])
    var = table(P + 'SRC-07_commercial/variations.csv', ['variation_id', 'project_id', 'raised_date', 'status', 'value_cents', 'description'])
    not_ = table(P + 'SRC-07_commercial/notices.csv', ['notice_id', 'project_id', 'notice_date', 'notice_type', 'linked_variation_id', 'description'])
    dfc = table(P + 'SRC-08_quality/defects.csv', ['defect_id', 'project_id', 'subcontractor', 'trade', 'raised_date', 'severity', 'rework_cost_cents', 'status'])
    ret = table(P + 'SRC-09_retentions/retention_ledger.csv', ['project_id', 'retention_held_cents', 'release_due_date', 'released_date', 'hold_reason'])
    sec = table(P + 'SRC-09_retentions/security_instruments.csv', ['instrument_id', 'project_id', 'kind', 'face_value_cents', 'expiry_date'])
    mkt = table(P + 'SRC-10_market/market_observations.csv', ['obs_id', 'material_id', 'obs_date', 'value', 'unit', 'kind', 'source_label', 'geography'])
    fx = table(P + 'SRC-10_market/fx_rates.csv', ['fx_date', 'pair', 'rate'])
    ts = table(P + 'SRC-12_labour/timesheets.csv', ['entry_id', 'worker_pseudonym', 'project_id', 'work_package', 'work_date', 'ordinary_hours', 'overtime_hours', 'rate_cents_per_hour'])
    out = table(P + 'SRC-12_labour/work_output.csv', ['project_id', 'work_package', 'week_start', 'quantity', 'unit'])
    hire = table(P + 'SRC-13_plant/plant_hire.csv', ['hire_id', 'project_id', 'equipment', 'on_hire_date', 'off_hire_date', 'needed_until', 'rate_cents_per_day'])
    bank = table(P + 'SRC-14_bank/bank_transactions.csv', ['txn_id', 'txn_date', 'amount_cents', 'description'])
    fac = table(P + 'SRC-14_bank/funding_facility.csv', ['facility_id', 'limit_cents', 'drawn_cents', 'rate_bps', 'as_of'])
    table(P + 'SRC-11_documents/documents_index.csv', ['doc_id', 'file', 'doc_type', 'ground_truth_supplier', 'ground_truth_unit_rate_cents', 'ground_truth_qty', 'ambiguity'])
    n = {'inv': 0, 'po': 0, 'pay': 0}
    def new_inv(): n['inv'] += 1; return f'INV-{n["inv"]:04d}'
    def new_po(): n['po'] += 1; return f'PO-{n["po"]:04d}'
    def new_pay(): n['pay'] += 1; return f'PAY-{n["pay"]:04d}'

    # ---- baseline: budgets, POs, invoices, deliveries, payments
    plist = PROJECTS[: 3 if full else 1]
    cost_budget = {}
    for (pid, _, contract, start, fin) in plist:
        cost_total = contract * 90 // 100
        for (cc, _, share) in CODES:
            b = cost_total * share // 100
            cost_budget[(pid, cc)] = b
            put(P + 'SRC-02_costing/budget_lines.csv', pid, cc, b, 'R0', start)
        put(P + 'SRC-07_commercial/contracts.csv', pid, contract, 0)
        put(P + 'SRC-09_retentions/retention_ledger.csv', pid, contract * 5 // 100 // 2, iso(D(fin)), '', '')
    mat_for_cc = {'CC-02': None, 'CC-03': 'MAT-CONC40', 'CC-04': 'MAT-STEEL', 'CC-06': 'MAT-TIMB', 'CC-09': 'MAT-PBOARD', 'CC-07': 'MAT-CU'}
    for (pid, _, contract, start, fin) in plist:
        s0 = D(start)
        for (cc, _, share) in CODES:
            b = cost_budget[(pid, cc)]
            npo = 3
            for k in range(npo):
                supplier = SUPPLIERS[(rnd.randrange(0, 8) if full else rnd.randrange(0, 3))][0]
                pdate = s0 + dt.timedelta(days=40 + k * 70 + rnd.randrange(0, 10))
                if pdate > ASOF - dt.timedelta(days=20): continue
                amt = b * (22 + rnd.randrange(0, 6)) // 100
                mid = mat_for_cc.get(cc) or 'MAT-CONC40'
                rate = BASE_RATE[mid] + rnd.randrange(-2000, 2000) * (BASE_RATE[mid] // 20000 + 1)
                qty = max(1, amt // rate)
                amt = qty * rate
                poid = new_po()
                put(P + 'SRC-03_procurement/purchase_orders.csv', poid, supplier, pid, cc, iso(pdate), mid, qty, dict((m[0], m[2]) for m in MATERIALS)[mid], rate, amt, 'open')
                dd = pdate + dt.timedelta(days=21)
                if dd < ASOF: put(P + 'SRC-05_materials/deliveries.csv', f'DK-{poid[3:]}', poid, mid, iso(dd), qty, qty)
                for j in range(2):
                    idate = pdate + dt.timedelta(days=28 + 30 * j)
                    if idate > ASOF: continue
                    ex = amt // 2
                    iid = new_inv()
                    put(P + 'SRC-01_accounting/ap_invoices.csv', iid, supplier, f'SI-{rnd.randrange(10000, 99999)}', pid, cc, poid, iso(idate), ex, gst(ex), 'posted', 'B-accounting-001')
                    if idate + dt.timedelta(days=30) <= ASOF:
                        put(P + 'SRC-01_accounting/payments.csv', new_pay(), iid, iso(idate + dt.timedelta(days=30)), ex + gst(ex))
    # programme + labour + market baseline
    for (pid, _, contract, start, fin) in plist:
        s0, f0 = D(start), D(fin)
        span = (f0 - s0).days
        for i, (cc, name, _) in enumerate(CODES):
            bs = s0 + dt.timedelta(days=span * i // 12); bf = bs + dt.timedelta(days=span // 5)
            done = bf < ASOF - dt.timedelta(days=30)
            put(P + 'SRC-04_programme/activities.csv', f'{pid}-A{i + 1:02d}', pid, name, iso(bs), iso(bf), iso(bs), iso(bf), iso(bs) if bs < ASOF else '', iso(bf) if done else '', 100 if done else (50 if bs < ASOF else 0))
    for sidx, (sid, _) in enumerate(SUPPLIERS[: 12 if full else 4]):
        put(P + 'SRC-06_supplier_compliance/supplier_compliance.csv', sid, 'public_liability_insurance', iso(ASOF + dt.timedelta(days=150 + sidx * 11)))
        put(P + 'SRC-06_supplier_compliance/supplier_compliance.csv', sid, 'licence', iso(ASOF + dt.timedelta(days=400 + sidx * 9)))
    months = [dt.date(2025 + (2 + m) // 12, (2 + m) % 12 + 1, 15) for m in range(0, 19)]   # Mar 2025 .. Sep 2026
    k = 0
    for mid in ('MAT-STEEL', 'MAT-TIMB', 'MAT-CU', 'MAT-REO'):
        v = 10000
        for d in months:
            v = v * (1000 + rnd.randrange(-8, 12)) // 1000
            if mid == 'MAT-CU' and d > dt.date(2026, 4, 15): continue
            k += 1
            put(P + 'SRC-10_market/market_observations.csv', f'OBS-{k:04d}', mid, iso(d), v, 'index_points_x100', 'index', 'SYNTHETIC-INDEX', 'AU-national')
    for d in range(0, 20):
        dd = ASOF - dt.timedelta(days=d * 30 // 2)
        put(P + 'SRC-10_market/fx_rates.csv', iso(dd), 'AUD/USD', f'{0.6500 + rnd.randrange(-200, 200) / 10000:.4f}')
    wp_workers = [f'W-{i:03d}' for i in range(1, 9)]
    for wk in range(0, 26):
        wd = dt.date(2026, 4, 6) + dt.timedelta(days=7 * wk)
        if wd > ASOF: break
        for w in wp_workers[:4]:
            for dday in range(5):
                put(P + 'SRC-12_labour/timesheets.csv', f'TS-{w}-{wd.isoformat()}-{dday}', w, plist[0][0], 'WP-PLASTER', iso(wd + dt.timedelta(days=dday)), 8, 0, 6_800)
        put(P + 'SRC-12_labour/work_output.csv', plist[0][0], 'WP-PLASTER', iso(wd), 320, 'm2')
    put(P + 'SRC-14_bank/funding_facility.csv', 'FAC-001', 150_000_000, 62_000_000, 780, iso(ASOF))
    for dd in range(0, 12):
        put(P + 'SRC-14_bank/bank_transactions.csv', f'TX-{dd + 1:04d}', iso(ASOF - dt.timedelta(days=dd * 5)), (1 if dd % 3 else -1) * (12_000_000 + dd * 350_000), 'SYNTHETIC TRANSACTION')
    for (pid, *_ ) in plist:
        put(P + 'SRC-09_retentions/security_instruments.csv', f'BG-{pid[4:]}', pid, 'bank_guarantee', 25_000_000, iso(ASOF + dt.timedelta(days=210)))
    put(P + 'SRC-02_costing/forecasts.csv', plist[0][0], 'CC-09', 'F-2026-08', '2026-08-31', 5_000_000, 'builder estimate', 'initial')
    return P, plist, new_inv, new_po, new_pay


def scenario(sid, kind, title, srcs, rule, acc, records, expected):
    SC.append([sid, kind, title, srcs, rule, acc, records, expected])


def plant(P, new_inv, new_po, new_pay):
    A = P
    # PS-01 / NC-01 : cost over budget tolerance (PRJ-002 CC-04) and a near-miss (PRJ-002 CC-05 at 98%)
    # budgets are rewritten so the planted cost codes sit against explicit budgets
    def set_budget(pid, cc, cents):
        for r in rows[A + 'SRC-02_costing/budget_lines.csv'][1]:
            if r[0] == pid and r[1] == cc: r[2] = cents
    def actual(pid, cc):
        return sum(r[7] for r in rows[A + 'SRC-01_accounting/ap_invoices.csv'][1] if r[3] == pid and r[4] == cc)
    scenario('PS-01', 'positive', 'Actual cost exceeds budget tolerance', 'SRC-01; SRC-02', 'Section 06 §5.2 rule 1', 'PG-AI-AC-01', 'PRJ-002 CC-04 (budget_lines.csv, ap_invoices.csv)', 'Finding raised: actual cost is 118 percent of budget (illustrative tolerance 5 percent)')
    scenario('NC-01', 'negative control', 'Cost at 98 percent of budget', 'SRC-01; SRC-02', 'Section 06 §5.2 rule 1', 'PG-AI-AC-20', 'PRJ-002 CC-05', 'No finding: within tolerance')
    # PS-02 commitment growth without an approved change
    po2 = [r for r in rows[A + 'SRC-03_procurement/purchase_orders.csv'][1] if r[2] == 'PRJ-002' and r[3] == 'CC-03'][0]
    put(A + 'SRC-03_procurement/po_amendments.csv', 'AMD-001', po2[0], '2026-08-12', 8_500_000, '', 'additional pour')
    put(A + 'SRC-03_procurement/po_amendments.csv', 'AMD-002', po2[0], '2026-08-20', 1_200_000, 'VAR-0003', 'client instruction')
    scenario('PS-02', 'positive', 'Commitment increases with no approved change', 'SRC-03; SRC-07', 'Section 06 §5.2 rule 2', 'PG-AI-AC-01', f'{po2[0]} AMD-001 (blank approved_change_ref)', 'Finding raised for AMD-001')
    scenario('NC-02', 'negative control', 'Commitment increase linked to an approved variation', 'SRC-03; SRC-07', 'Section 06 §5.2 rule 2', 'PG-AI-AC-20', f'{po2[0]} AMD-002 -> VAR-0003 (approved)', 'No finding for AMD-002')
    # PS-03 invoice differs from PO (and near miss)
    s4 = 'SUP-004'
    p3 = new_po()
    put(A + 'SRC-03_procurement/purchase_orders.csv', p3, s4, 'PRJ-002', 'CC-04', '2026-07-01', 'MAT-STEEL', 40, 'tonne', 245_000, 40 * 245_000, 'open')
    i3 = new_inv(); i3b = new_inv()
    put(A + 'SRC-01_accounting/ap_invoices.csv', i3, s4, 'SI-70001', 'PRJ-002', 'CC-04', p3, '2026-08-01', 40 * 264_000, gst(40 * 264_000), 'posted', 'B-accounting-001')
    p3b = new_po()
    put(A + 'SRC-03_procurement/purchase_orders.csv', p3b, s4, 'PRJ-002', 'CC-04', '2026-07-02', 'MAT-STEEL', 40, 'tonne', 245_000, 40 * 245_000, 'open')
    put(A + 'SRC-01_accounting/ap_invoices.csv', i3b, s4, 'SI-70002', 'PRJ-002', 'CC-04', p3b, '2026-08-02', 40 * 245_000 + 40 * 980, gst(40 * 245_000 + 40 * 980), 'posted', 'B-accounting-001')
    scenario('PS-03', 'positive', 'Invoice rate exceeds PO rate beyond tolerance', 'SRC-01; SRC-03', 'Section 06 §5.2 rule 3', 'PG-AI-AC-01', f'{i3} vs {p3}', 'Finding raised: rate about 7.8 percent above PO (illustrative tolerance 1 percent)')
    scenario('NC-03', 'negative control', 'Invoice rate within tolerance', 'SRC-01; SRC-03', 'Section 06 §5.2 rule 3', 'PG-AI-AC-20', f'{i3b} vs {p3b}', 'No finding: about 0.4 percent above PO')
    # PS-04 variations
    put(A + 'SRC-07_commercial/variations.csv', 'VAR-0001', 'PRJ-002', '2026-02-10', 'submitted', '', 'Additional basement waterproofing (unpriced)')
    put(A + 'SRC-07_commercial/variations.csv', 'VAR-0002', 'PRJ-002', '2026-09-20', 'submitted', 14_500_000, 'Revised facade fixings (recent)')
    put(A + 'SRC-07_commercial/variations.csv', 'VAR-0003', 'PRJ-002', '2026-08-05', 'approved', 1_200_000, 'Client instruction: extra slab edge')
    put(A + 'SRC-07_commercial/notices.csv', 'NTC-001', 'PRJ-002', '2026-06-18', 'client_instruction', '', 'Instruction to relocate plant room; no variation raised')
    scenario('PS-04', 'positive', 'Variation unpriced and unresolved for months', 'SRC-07', 'Section 06 §5.2 rule 4; Section 11', 'PG-AI-AC-01; PG-CR-AC-03', 'VAR-0001', 'Finding raised: submitted 2026-02-10, no value, unresolved beyond illustrative 60 days')
    scenario('PS-04b', 'positive', 'Client instruction with no variation raised', 'SRC-07', 'Section 06 §4 (commercial and revenue: unsubmitted variations)', 'PG-CR-AC-03', 'NTC-001', 'Finding raised: potential scope change not yet a variation (potential is not entitlement)')
    scenario('NC-04', 'negative control', 'Recent priced variation awaiting decision', 'SRC-07', 'Section 06 §5.2 rule 4', 'PG-AI-AC-20', 'VAR-0002', 'No finding: priced and within the illustrative workflow period')
    # PS-05 retention release overdue
    for r in rows[A + 'SRC-09_retentions/retention_ledger.csv'][1]:
        if r[0] == 'PRJ-001': r[2] = '2026-07-31'; r[3] = ''; r[4] = ''
    scenario('PS-05', 'positive', 'Retention release date passed with no release or hold reason', 'SRC-09', 'Section 06 §5.2 rule 5', 'PG-AI-AC-01', 'PRJ-001 retention_ledger', 'Finding raised: due 2026-07-31, not released, no explained hold')
    # PS-06 supplier compliance
    for r in rows[A + 'SRC-06_supplier_compliance/supplier_compliance.csv'][1]:
        if r[0] == 'SUP-005' and r[1] == 'public_liability_insurance': r[2] = iso(ASOF + dt.timedelta(days=19))
        if r[0] == 'SUP-008' and r[1] == 'licence': r[2] = '2026-08-31'
    scenario('PS-06', 'positive', 'Supplier insurance about to expire; licence expired', 'SRC-06', 'Section 06 §5.2 rule 6', 'PG-AI-AC-01', 'SUP-005 insurance (19 days); SUP-008 licence (expired)', 'Findings raised: SUP-005 expiring within the illustrative 30-day warning; SUP-008 expired')
    scenario('NC-06', 'negative control', 'Insurance expires in many months', 'SRC-06', 'Section 06 §5.2 rule 6', 'PG-AI-AC-20', 'all other suppliers', 'No finding')
    # PS-07 / PS-15 / PS-16 / PS-23 / PS-25 : quotes and market
    q = lambda *v: put(A + 'SRC-03_procurement/quotes.csv', *v)
    q('Q-0001', 'SUP-004', 'MAT-STEEL', 'Grade 300PLUS, 250UB, delivered site', '2026-09-10', '2026-10-31', 265_000, 'AUD', '', '', 0, 'delivered', 21, 'quote')
    q('Q-0002', 'SUP-009', 'MAT-STEEL', 'Grade 300PLUS, 250UB, ex-works', '2026-09-12', '2026-10-31', 247_000, 'AUD', '', '', 9_500, 'ex-works', 28, 'quote')
    scenario('PS-07', 'positive', 'Quote above comparable reference after landed-cost adjustment', 'SRC-03; SRC-10', 'Section 06 §5.2 rule 7; Section 08 §6', 'PG-MP-AC-04; PG-AI-AC-01', 'Q-0001 vs Q-0002 and recent PO rate 245,000 cents per tonne', 'Finding raised: delivered quote is above the landed comparable (ex-works 247,000 plus freight 9,500 = 256,500)')
    q('Q-0003', 'SUP-001', 'MAT-CONC32', 'Concrete 32 MPa', '2026-09-05', '2026-10-31', 27_000, 'AUD', '', '', 0, 'delivered', 3, 'quote')
    scenario('PS-15', 'positive', 'Cheaper quote is for a different specification', 'SRC-03', 'Section 08 §4.1 (comparability gate)', 'PG-MP-AC-02', 'Q-0003 (32 MPa) versus the 40 MPa demand on PRJ-002', 'Definitive ranking blocked: classed not comparable or partially comparable; indicative only')
    q('Q-0004', 'SUP-003', 'MAT-REO', 'N16 bar', '2026-03-01', '2026-06-30', 238_000, 'AUD', '', '', 0, 'delivered', 14, 'quote')
    scenario('PS-14', 'positive', 'Expired quote and stale market observation', 'SRC-03; SRC-10', 'Section 08 §7.1, §14', 'PG-MP-AC-07; PG-DI-AC-13', 'Q-0004 (expired 2026-06-30); MAT-CU observations end 2026-04-15', 'Analysis qualified or downgraded: expired quote cannot support an unqualified current recommendation')
    q('Q-0005', 'SUP-011', 'MAT-STEEL', 'Imported structural fixings kit', '2026-05-02', '2026-11-30', 6_900, 'USD', '0.6612', '2026-05-02', 800, 'FOB', 56, 'quote')
    scenario('PS-23', 'positive', 'International quote converted at an old FX rate', 'SRC-03; SRC-10', 'Section 08 §6, §12', 'PG-MP-AC-05; PG-MP-AC-11', 'Q-0005 (fx_rate_date 2026-05-02) vs fx_rates.csv latest', 'Conversion recorded with source, date and method; stale FX is flagged; unresolved import checks block a definitive recommendation')
    q('Q-0006', 'SUP-006', 'MAT-PBOARD', 'Plasterboard 13mm, delivered', '2026-09-08', '2026-11-15', 1_740, 'AUD', '', '', 0, 'delivered', 7, 'quote')
    scenario('PS-25', 'positive', 'Saving opportunity on an on-budget project', 'SRC-03; SRC-10', 'Section 06 §12 (opportunity discovery when budgets are on track)', 'PG-AI-AC-15', 'Q-0006 (1,740) vs current PBOARD PO rates (about 1,850)', 'Opportunity created (estimate only, never realised until verified)')
    # PS-16 : steel index rises ~9 percent over three months while demand is unplaced
    steel = [r for r in rows[A + 'SRC-10_market/market_observations.csv'][1] if r[1] == 'MAT-STEEL']
    last = steel[-1]
    for k, r in enumerate(steel[-4:]):
        r[3] = int(10000 * (1 + 0.031 * k))
    put(A + 'SRC-05_materials/material_demand.csv', 'DEM-0001', 'PRJ-002', 'MAT-STEEL', 120, 'tonne', '2026-12-01')
    scenario('PS-16', 'positive', 'Steel index rising with demand not yet bought', 'SRC-05; SRC-10; SRC-03; SRC-04', 'Section 08 §8 (buy now, wait, stage, negotiate)', 'PG-MP-AC-09; PG-MP-AC-16', 'market_observations MAT-STEEL last four points; DEM-0001; Q-0001, Q-0002 (valid to 2026-10-31)', 'Scenarios produced with landed cost, quote validity, working capital and uncertainty; no assumption that prices keep rising')
    # PS-08 plant hire beyond need
    put(A + 'SRC-13_plant/plant_hire.csv', 'HIRE-001', 'PRJ-003', '20t excavator (synthetic)', '2026-02-01', '', '2026-03-31', 115_000)
    put(A + 'SRC-13_plant/plant_hire.csv', 'HIRE-002', 'PRJ-003', 'Telehandler (synthetic)', '2026-08-10', '', '2026-12-18', 38_000)
    scenario('PS-08', 'positive', 'Equipment on hire beyond evidenced need', 'SRC-13; SRC-04', 'Section 06 §5.2 rule 8', 'PG-AI-AC-01', 'HIRE-001 (needed until 2026-03-31, still on hire)', 'Finding raised: about 183 days beyond need at 115,000 cents per day')
    scenario('NC-08', 'negative control', 'Hire within the evidenced need period', 'SRC-13', 'Section 06 §5.2 rule 8', 'PG-AI-AC-20', 'HIRE-002', 'No finding')
    # PS-09 forecast movement with no bridge
    put(A + 'SRC-02_costing/forecasts.csv', 'PRJ-002', 'CC-09', 'F-2026-09', '2026-09-30', 36_000_000, 'builder estimate', '')
    put(A + 'SRC-02_costing/forecasts.csv', 'PRJ-002', 'CC-09', 'F-2026-08', '2026-08-31', 5_000_000, 'builder estimate', 'initial')
    scenario('PS-09', 'positive', 'Forecast moves materially with no explained bridge', 'SRC-02', 'Section 06 §5.2 rule 9; Section 05 §5.3', 'PG-PC-AC-08; PG-AI-AC-01', 'PRJ-002 CC-09 F-2026-08 to F-2026-09 (movement_reason blank)', 'Finding raised: unexplained forecast movement')
    # PS-10 split purchase (+ negative control outside window)
    for k, (d, amt) in enumerate([('2026-08-03', 9_500_000), ('2026-08-09', 9_200_000), ('2026-08-14', 9_000_000)]):
        qty = amt // 238_000
        put(A + 'SRC-03_procurement/purchase_orders.csv', new_po(), 'SUP-003', 'PRJ-002', 'CC-03', d, 'MAT-REO', qty, 'tonne', 238_000, qty * 238_000, 'open')
    split_ids = [r[0] for r in rows[A + 'SRC-03_procurement/purchase_orders.csv'][1] if r[1] == 'SUP-003' and r[4] in ('2026-08-03', '2026-08-09', '2026-08-14')]
    scenario('PS-10', 'positive', 'Purchase split into three orders inside a short window', 'SRC-03', 'CR-02 R5 (aggregation); Section 06 §5.4', 'PG-AI-AC-10', '; '.join(split_ids), 'Aggregated assessment is material even though each order is below the illustrative single-order threshold')
    for d, amt in [('2026-03-02', 9_500_000), ('2026-05-04', 9_200_000), ('2026-07-06', 9_000_000)]:
        qty = amt // 238_000
        put(A + 'SRC-03_procurement/purchase_orders.csv', new_po(), 'SUP-010', 'PRJ-002', 'CC-05', d, 'MAT-REO', qty, 'tonne', 238_000, qty * 238_000, 'open')
    nc10 = [r[0] for r in rows[A + 'SRC-03_procurement/purchase_orders.csv'][1] if r[1] == 'SUP-010' and r[4] in ('2026-03-02', '2026-05-04', '2026-07-06')]
    scenario('NC-10', 'negative control', 'Same pattern but 60 days apart (outside the illustrative window)', 'SRC-03', 'CR-02 R5 (aggregation window)', 'PG-AI-AC-10', '; '.join(nc10), 'Not aggregated at an illustrative 30-day window (known limitation: chain splitting, OQ-A1-7)')
    # PS-11 duplicate invoice, PS-12 credit lineage, PS-13 conflict between sources, PS-21 missing critical, PS-22 ambiguous supplier
    base_inv = [r for r in rows[A + 'SRC-01_accounting/ap_invoices.csv'][1] if r[3] == 'PRJ-001'][0]
    dup = list(base_inv); dup[0] = new_inv(); dup[10] = 'B-accounting-002-replay'
    rows[A + 'SRC-01_accounting/ap_invoices.csv'][1].append(dup)
    scenario('PS-11', 'positive', 'Same invoice delivered twice (replay)', 'SRC-01', 'Section 04 §7', 'PG-DI-AC-08', f'{base_inv[0]} and {dup[0]} (same supplier, invoice number, amount; different batch)', 'Recognised as a duplicate delivery: no second financial effect')
    oi = new_inv(); ci = 'CRN-0001'; ri = new_inv()
    put(A + 'SRC-01_accounting/ap_invoices.csv', oi, 'SUP-002', 'SI-80001', 'PRJ-002', 'CC-06', '', '2026-07-10', 6_000_000, gst(6_000_000), 'posted', 'B-accounting-001')
    put(A + 'SRC-01_accounting/credit_notes.csv', ci, 'SUP-002', oi, '2026-07-25', 6_000_000, gst(6_000_000))
    put(A + 'SRC-01_accounting/ap_invoices.csv', ri, 'SUP-002', 'SI-80001R', 'PRJ-002', 'CC-06', '', '2026-07-26', 5_800_000, gst(5_800_000), 'posted', 'B-accounting-001')
    scenario('PS-12', 'positive', 'Invoice credited and reissued', 'SRC-01', 'Section 04 §7; Section 05 §6', 'PG-DI-AC-09; PG-PC-AC-06', f'{oi}, {ci}, {ri}', 'Lineage preserved: net cost is the reissued amount, not a sum of three events')
    pm = table(A + 'conflicting_sources/pm_system_invoices.csv', ['invoice_ref', 'supplier_id', 'project_id', 'ex_gst_cents', 'source'])
    conf_inv = [r for r in rows[A + 'SRC-01_accounting/ap_invoices.csv'][1] if r[3] == 'PRJ-003'][0]
    put(A + 'conflicting_sources/pm_system_invoices.csv', conf_inv[0], conf_inv[1], conf_inv[3], conf_inv[7] + 900_000, 'pm-system-export')
    scenario('PS-13', 'positive', 'Two systems disagree on an invoice amount', 'SRC-01; SRC-03', 'Section 04 §9 (quarantine) and §5 (authority)', 'PG-DI-AC-03; PG-DI-AC-04', f'{conf_inv[0]}: accounting {conf_inv[7]} vs PM system {conf_inv[7] + 900_000}', 'Conflicting material record excluded from authoritative calculation until resolved; visible to reviewers as quarantined')
    mp = new_po()
    put(A + 'SRC-03_procurement/purchase_orders.csv', mp, 'SUP-002', 'PRJ-003', '', '2026-08-20', 'MAT-TIMB', 10, 'm3', 169_000, 1_690_000, 'open')
    mi = new_inv()
    put(A + 'SRC-01_accounting/ap_invoices.csv', mi, 'SUP-002', 'SI-80002', 'PRJ-003', 'CC-06', mp, '2026-09-02', 1_690_000, '', 'posted', 'B-accounting-001')
    scenario('PS-21', 'positive', 'Critical values missing', 'SRC-01; SRC-03', 'Section 04 §8 (semantic validation)', 'PG-DI-AC-11', f'{mp} (no cost code); {mi} (no GST amount)', 'Not silently defaulted: held with a qualification or sent to reconciliation')
    ai = new_inv()
    put(A + 'SRC-01_accounting/ap_invoices.csv', ai, 'SYN Metro Steel (synthetic)', 'SI-90001', 'PRJ-002', 'CC-04', '', '2026-09-15', 3_200_000, gst(3_200_000), 'posted', 'B-accounting-001')
    scenario('PS-22', 'positive', 'Supplier name matches two suppliers', 'SRC-01', 'Section 04 §11', 'PG-DI-AC-12', f'{ai} supplier text "SYN Metro Steel (synthetic)" vs SUP-004 and SUP-009', 'Not forced to either supplier: pending reconciliation')
    # PS-17 over-ordering
    put(A + 'SRC-05_materials/material_demand.csv', 'DEM-0002', 'PRJ-001', 'MAT-PBOARD', 2000, 'sheet', '2026-10-15')
    for _ in range(2):
        pid_ = new_po()
        put(A + 'SRC-03_procurement/purchase_orders.csv', pid_, 'SUP-006', 'PRJ-001', 'CC-09', '2026-08-25', 'MAT-PBOARD', 1300, 'sheet', 1_850, 1300 * 1_850, 'open')
        put(A + 'SRC-05_materials/deliveries.csv', f'DK-X{pid_[3:]}', pid_, 'MAT-PBOARD', '2026-09-05', 1300, 1300)
    scenario('PS-17', 'positive', 'Ordered and delivered more than the demand; duplicate order', 'SRC-03; SRC-05', 'Section 08 §13', 'PG-MP-AC-01; PG-MP-AC-14', 'DEM-0002 (2,000) vs two POs of 1,300', 'Finding raised: surplus about 600 sheets, possible duplicate order')
    # PS-18 delay events with overlap
    put(A + 'SRC-04_programme/delay_events.csv', 'DLY-001', 'PRJ-002', 'PRJ-002-A03', '2026-07-06', '2026-07-21', 12, 'crane access', 1_850_000)
    put(A + 'SRC-04_programme/delay_events.csv', 'DLY-002', 'PRJ-002', 'PRJ-002-A03', '2026-07-13', '2026-07-24', 10, 'design hold', 1_850_000)
    scenario('PS-18', 'positive', 'Two overlapping delay events', 'SRC-04', 'Section 07 §5, §6.1', 'PG-SD-AC-08; PG-SD-AC-06', 'DLY-001 and DLY-002 (overlap 2026-07-13 to 2026-07-21)', 'Overlap not double-counted; holding cost needs a counterfactual; causes stay suspected until evidenced')
    # PS-19 productivity deterioration (rewrite last 8 weeks outputs)
    outs = [r for r in rows[A + 'SRC-12_labour/work_output.csv'][1] if r[1] == 'WP-PLASTER']
    for k, r in enumerate(outs[-8:]):
        r[3] = int(320 * (1 - 0.045 * k))
    scenario('PS-19', 'positive', 'Labour output per hour falling', 'SRC-12', 'Section 09; Section 06 §5.3', 'PG-LR-AC-04; PG-LR-AC-05', 'PRJ-001 WP-PLASTER last 8 weeks', 'Trend finding with a documented basis; cause is a hypothesis, not an assertion')
    # PS-20 repeated defect and rework cost growth
    for k, (d, c) in enumerate([('2026-05-12', 1_200_000), ('2026-07-03', 2_600_000), ('2026-09-01', 4_900_000)]):
        put(A + 'SRC-08_quality/defects.csv', f'DEF-{k + 1:03d}', 'PRJ-002', 'SUB-004 (synthetic)', 'waterproofing', d, 'major', c, 'open')
    scenario('PS-20', 'positive', 'Repeat defect, same trade, growing rework cost', 'SRC-08', 'Section 13 §13.5, §13.7', 'PGR-13-A001; PGR-13-A002', 'DEF-001, DEF-002, DEF-003', 'Recurrence finding; responsibility not concluded from pattern alone')
    # PS-26 documents for extraction
    docs = {
        'SRC-11_documents/quote_clear_SUP-006.txt': 'SYNTHETIC SUPPLIER QUOTE\nSupplier: SYN Plasterboard Direct Pty Ltd (synthetic)\nItem: Plasterboard 13mm sheet\nQuantity: 2000 sheets\nUnit price: $17.40 per sheet ex GST\nValid until: 15 November 2026\nDelivery: delivered to site within 7 days\n',
        'SRC-11_documents/quote_ambiguous_SUP-004.txt': 'SYNTHETIC SUPPLIER QUOTE (poor scan)\nSupplier: SYN Metro Steel Pty Ltd (synthetic)\nItem: Structural steel 250UB\nQuantity: 4O tonnes   [letter O or zero?]\nRate: $2.650 / t   [decimal point or thousands separator?]\nValid until: 31/10/26\n',
    }
    for p, t in docs.items():
        os.makedirs(os.path.dirname(f'{OUT}/{A}{p}'), exist_ok=True); open(f'{OUT}/{A}{p}', 'w', newline='\n').write(t)
    put(A + 'SRC-11_documents/documents_index.csv', 'DOC-001', 'quote_clear_SUP-006.txt', 'quote', 'SUP-006', 1_740, 2000, '')
    put(A + 'SRC-11_documents/documents_index.csv', 'DOC-002', 'quote_ambiguous_SUP-004.txt', 'quote', 'SUP-004', 265_000, 40, 'quantity "4O" and rate "$2.650" are ambiguous')
    # budgets for the two cost-code scenarios are set LAST, after every planted invoice exists
    set_budget('PRJ-002', 'CC-04', int(actual('PRJ-002', 'CC-04') * 100 // 118))     # actual is 118% of budget
    set_budget('PRJ-002', 'CC-05', int(actual('PRJ-002', 'CC-05') * 100 // 98))      # actual is 98% of budget
    scenario('PS-26', 'positive', 'Document reading with an ambiguous value', 'SRC-11', 'Section 04 §12 (human verification of material AI-extracted values)', 'PG-DI-AC-07; PG-MP-AC-03', 'DOC-002', 'Extracted quantity and rate must not become authoritative until a person verifies them')


def tenant_b_collisions(P, new_inv, new_po, new_pay):
    # Tenant B reuses identifiers that exist in tenant A, with different content
    put(P + 'SRC-01_accounting/ap_invoices.csv', 'INV-0001', 'SUP-001', 'SI-B-0001', 'PRJ-001', 'CC-03', 'PO-0001', '2026-04-01', 777_700, gst(777_700), 'posted', 'B-accounting-tenantB')
    scenario('PS-24', 'positive', 'Second tenant reuses identifiers', 'all', 'Section 04 §16', 'PG-DI-AC-14', 'zero_two INV-0001, PRJ-001, PO-0001 collide with zero_one', 'No record, figure or finding crosses tenants; payload tenant claims are not trusted')


def main():
    tenants = [('zero_one', 20261013, True), ('zero_two', 20261014, False)]
    for code, seed, full in tenants:
        rnd = random.Random(seed)
        P, plist, ni, npo, npay = build_tenant(code, rnd, full)
        if full: plant(P, ni, npo, npay)
        else: tenant_b_collisions(P, ni, npo, npay)
    # write
    for path, (hdr, rs) in sorted(rows.items()):
        full_path = f'{OUT}/{path}'; os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f, lineterminator='\n'); w.writerow(hdr); w.writerows(rs)
    os.makedirs(f'{OUT}/scenarios', exist_ok=True)
    with open(f'{OUT}/scenarios/SCENARIO_REGISTER.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['scenario_id', 'kind', 'title', 'source_categories', 'blueprint_rule_ref', 'acceptance_ids', 'records_involved', 'expected_behaviour'])
        for r in sorted(SC, key=lambda x: (x[0][:2] != 'PS', x[0])): w.writerow(r)
    json.dump({'NOTE': 'ILLUSTRATIVE TEST VALUES ONLY. They are not defaults and not proposed thresholds. Real thresholds come from CR-02 decisions and pilot practice.',
               'as_of': iso(ASOF), 'budget_tolerance_bps': 500, 'invoice_vs_po_tolerance_bps': 100, 'single_order_materiality_abs_cents': 25_000_000,
               'aggregation_window_days': 30, 'aggregation_keys': ['project'], 'insurance_expiry_warning_days': 30, 'variation_unresolved_days': 60},
              open(f'{OUT}/scenarios/test_thresholds.json', 'w'), indent=1, sort_keys=True)
    open(f'{OUT}/README.txt', 'w').write(f'BUILDER ZERO ({GEN_VERSION})\nA SYNTHETIC builder for testing. Every name, number and document is invented. Not real data.\nTenants: zero_one (three projects, all planted scenarios), zero_two (one project, colliding identifiers).\nAs-of date {iso(ASOF)}. Money in integer AUD cents. See scenarios/SCENARIO_REGISTER.csv for what is planted and what each should do.\nRegenerate: python3 -I make_builder_zero.py <dir> (deterministic).\n')

main()
