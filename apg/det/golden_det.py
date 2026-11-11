"""Golden cases for the M5 detection layer on Builder Zero (Blueprint Section 06 section 5.2 and the planted scenarios of builder_zero/scenarios/SCENARIO_REGISTER.csv).

`run_golden_det()` runs the REAL pipeline - M3 ingestion, M4 and M5 intake, reconciliation with the SYNTHETIC register, the stored detection runs, finding ingestion, notification delivery,
a second sweep a day later and a second tenant - over the synthetic builder's CSV files.  `oracle_det()` recomputes which conditions the demonstration thresholds make a finding straight from
the CSV files with the csv module, `datetime.date` and `fractions.Fraction`, using NOTHING from apg, so the expected answers cannot simply agree with the code that wrote them.

The oracle restates the demonstration rules (illustrative thresholds, apg/det/demo_det.py) in plain code.  It does not model every held-record class: it leaves out the invoices the
demonstration reconciliation register holds (unknown supplier text, conflicting amount) or marks as a duplicate delivery, the same simplification the M4 oracle makes."""
import csv, datetime, json, os
from fractions import Fraction

AS_OF = '2026-09-30'
PROJECTS = ('PRJ-001', 'PRJ-002', 'PRJ-003')
T = dict(tol_budget=500, tol_po=100, var_days=60, instr_days=30, grace=0, warn=30, tol_quote=100, hire_days=7, move=5000000, agg_days=30, agg_abs=25000000, overlap=1,
         base_w=8, recent_w=4, decline=1000, def_n=3)           # restated here from the demonstration policy; the golden test also checks they equal it


def _rows(root, rel, tenant='zero_one'):
    with open(os.path.join(root, 'builder_zero', tenant, rel), encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def _d(s):
    return datetime.date.fromisoformat(s)


def _days(a, b):
    return (_d(b) - _d(a)).days


def _round_half_away(fr):
    n, d = fr.numerator, fr.denominator
    q, r = divmod(abs(n), d)
    if 2 * r >= d:
        q += 1
    return q if n >= 0 else -q


def oracle_det(root, tenant='zero_one'):
    inv = _rows(root, 'SRC-01_accounting/ap_invoices.csv', tenant); crn = _rows(root, 'SRC-01_accounting/credit_notes.csv', tenant)
    sup = {r['supplier_id'] for r in _rows(root, 'reference/suppliers.csv', tenant)}
    pm = {r['invoice_ref']: r['ex_gst_cents'] for r in _rows(root, 'conflicting_sources/pm_system_invoices.csv', tenant)} if os.path.exists(os.path.join(root, 'builder_zero', tenant, 'conflicting_sources')) else {}
    bud = _rows(root, 'SRC-02_costing/budget_lines.csv', tenant); fc = _rows(root, 'SRC-02_costing/forecasts.csv', tenant)
    pos = _rows(root, 'SRC-03_procurement/purchase_orders.csv', tenant); amd = _rows(root, 'SRC-03_procurement/po_amendments.csv', tenant); quotes = {r['quote_id']: r for r in _rows(root, 'SRC-03_procurement/quotes.csv', tenant)}
    var = {r['variation_id']: r for r in _rows(root, 'SRC-07_commercial/variations.csv', tenant)}; notes = _rows(root, 'SRC-07_commercial/notices.csv', tenant)
    ret = _rows(root, 'SRC-09_retentions/retention_ledger.csv', tenant); comp = _rows(root, 'SRC-06_supplier_compliance/supplier_compliance.csv', tenant)
    hire = _rows(root, 'SRC-13_plant/plant_hire.csv', tenant); dly = _rows(root, 'SRC-04_programme/delay_events.csv', tenant); dfx = _rows(root, 'SRC-08_quality/defects.csv', tenant)
    ts = _rows(root, 'SRC-12_labour/timesheets.csv', tenant); wo = _rows(root, 'SRC-12_labour/work_output.csv', tenant)
    seen, dup = {}, set()
    for r in inv:
        k = (r['supplier_id'], r['supplier_invoice_no']); sig = (r['project_id'], r['po_id'], r['invoice_date'], r['ex_gst_cents'], r['gst_cents'])
        if k in seen and seen[k] == sig:
            dup.add(r['invoice_id'])
        else:
            seen.setdefault(k, sig)
    held = {r['invoice_id'] for r in inv if r['supplier_id'] not in sup} | {r['invoice_id'] for r in inv if r['invoice_id'] in pm and pm[r['invoice_id']] != r['ex_gst_cents']}
    ids = [r['invoice_id'] for r in inv]
    held |= {i for i in ids if ids.count(i) > 1}                    # one identifier delivered twice with different content is a conflict, not two invoices (the second builder's INV-0001)
    left_out = dup | held
    by_id = {r['invoice_id']: r for r in inv if r['invoice_id'] not in held}
    out = {'excluded_invoices': sorted(left_out), 'expected': {}}

    def put(rule, scope, subject, **facts):
        out['expected'][f'{rule}|{scope}|{subject}'] = facts

    # R01 actual cost above budget tolerance, per project and cost code (all invoices to the as-of date, credits netted)
    actual = {}
    for r in inv:
        if r['invoice_id'] not in left_out and r['invoice_date'] <= AS_OF:
            actual[(r['project_id'], r['cost_code'])] = actual.get((r['project_id'], r['cost_code']), 0) + int(r['ex_gst_cents'])
    for c in crn:
        i = by_id.get(c['against_invoice_id'])
        if i and i['invoice_id'] not in left_out and c['credit_date'] <= AS_OF:
            actual[(i['project_id'], i['cost_code'])] -= int(c['ex_gst_cents'])
    budget = {}
    for r in bud:
        budget[(r['project_id'], r['cost_code'])] = budget.get((r['project_id'], r['cost_code']), 0) + int(r['budget_cents'])
    out['ratio_bps'] = {}
    for (p, cc), b in sorted(budget.items()):
        a = actual.get((p, cc), 0)
        if b > 0:
            out['ratio_bps'][f'{p}|{cc}'] = _round_half_away(Fraction(a * 10000, b))
        if b > 0 and a * 10000 > b * (10000 + T['tol_budget']):
            put('R01', p, cc, excess_cents=a - b)
    # R02 amendment with no approved change
    for a in amd:
        v = var.get(a['approved_change_ref'])
        if a['amendment_date'] <= AS_OF and (not a['approved_change_ref'] or v is None or v['status'] != 'approved'):
            put('R02', next(p['project_id'] for p in pos if p['po_id'] == a['po_id']), a['amendment_id'], delta_cents=int(a['delta_cents']))
    # R03 invoiced above order
    approved_delta = {}
    for a in amd:
        v = var.get(a['approved_change_ref'])
        if a['amendment_date'] <= AS_OF and v is not None and v['status'] == 'approved':
            approved_delta[a['po_id']] = approved_delta.get(a['po_id'], 0) + int(a['delta_cents'])
    out['po_over_bps'] = {}
    for po in pos:
        billed = sum(int(r['ex_gst_cents']) for r in inv if r['po_id'] == po['po_id'] and r['invoice_id'] not in left_out and r['invoice_date'] <= AS_OF)
        billed -= sum(int(c['ex_gst_cents']) for c in crn if by_id.get(c['against_invoice_id'], {}).get('po_id') == po['po_id'] and by_id[c['against_invoice_id']]['invoice_id'] not in left_out)
        commit = int(po['amount_cents']) + approved_delta.get(po['po_id'], 0)
        if billed > commit:
            out['po_over_bps'][po['po_id']] = _round_half_away(Fraction((billed - commit) * 10000, commit))
        if commit > 0 and billed * 10000 > commit * (10000 + T['tol_po']):
            put('R03', po['project_id'], po['po_id'], excess_cents=billed - commit)
    # R04 variation unresolved; R04B instruction without a variation
    for v in var.values():
        if v['status'] in ('submitted', 'disputed') and v['raised_date'] <= AS_OF and _days(v['raised_date'], AS_OF) > T['var_days']:
            put('R04', v['project_id'], v['variation_id'], age_days=_days(v['raised_date'], AS_OF), value_cents=int(v['value_cents']) if v['value_cents'] else None)
    for n in notes:
        if n['notice_type'] == 'client_instruction' and n['notice_date'] <= AS_OF and not n['linked_variation_id'] and _days(n['notice_date'], AS_OF) >= T['instr_days']:
            put('R04B', n['project_id'], n['notice_id'], age_days=_days(n['notice_date'], AS_OF))
    # R05 retention release date passed, nothing released, no hold reason
    for r in ret:
        if r['release_due_date'] and r['release_due_date'] < AS_OF and not r['released_date'] and not r['hold_reason'] and int(r['retention_held_cents']) > 0 and _days(r['release_due_date'], AS_OF) > T['grace']:
            put('R05', r['project_id'], r['project_id'], withheld_cents=int(r['retention_held_cents']), days_late=_days(r['release_due_date'], AS_OF))
    # R06 supplier evidence (tenant scope)
    for r in comp:
        left = _days(AS_OF, r['expiry_date'])
        if left <= T['warn']:
            put('R06', 'tenant', f"{r['supplier_id']}|{r['evidence_type']}", days_to_expiry=left)
    # R07 declared pair Q-0001 against Q-0002 (landed: ex-works plus freight)
    def landed(q):
        return int(q['unit_rate_cents']) + (int(q['freight_cents_per_unit']) if q['incoterm_delivery_basis'] == 'ex-works' else 0)
    if 'Q-0001' in quotes and 'Q-0002' in quotes:                 # the declared pair; a builder without both quotes has nothing to compare
        a, b = landed(quotes['Q-0001']), landed(quotes['Q-0002'])
        out['quote_landed'] = {'Q-0001': a, 'Q-0002': b}
    if 'Q-0001' in quotes and 'Q-0002' in quotes and a * 10000 > b * (10000 + T['tol_quote']):
        put('R07', 'tenant', 'Q-0001>quote:Q-0002', unit_difference_cents=a - b)
    # R08 hire beyond evidenced need
    for h in hire:
        if h['needed_until'] and h['on_hire_date'] <= AS_OF:
            end = min(h['off_hire_date'], AS_OF) if h['off_hire_date'] else AS_OF
            excess = _days(h['needed_until'], end)
            if excess > T['hire_days']:
                put('R08', h['project_id'], h['hire_id'], days_beyond_need=excess, cost_cents=excess * int(h['rate_cents_per_day']))
    # R09 forecast movement with no recorded reason
    groups = {}
    for r in fc:
        if r['forecast_date'] <= AS_OF:
            groups.setdefault((r['project_id'], r['cost_code']), []).append(r)
    for (p, cc), rs in sorted(groups.items()):
        rs.sort(key=lambda r: (r['forecast_date'], r['forecast_version']))
        for x, y in zip(rs, rs[1:]):
            mv = int(y['cost_to_complete_cents']) - int(x['cost_to_complete_cents'])
            if abs(mv) >= T['move'] and not y['movement_reason'].strip():
                put('R09', p, f"{cc}|{x['forecast_version']}>{y['forecast_version']}", movement_cents=mv)
    # AGG orders split inside a window (keys: project, supplier, material, cost code; chain of gaps <= window)
    cl = {}
    for po in pos:
        if po['po_date'] <= AS_OF and po['cost_code'] and po['supplier_id'] and po['material_id'] and po['project_id']:
            cl.setdefault((po['project_id'], po['supplier_id'], po['material_id'], po['cost_code']), []).append(po)
    for key, ps in sorted(cl.items()):
        ps.sort(key=lambda p: (p['po_date'], p['po_id']))
        run = [ps[0]]
        for p in ps[1:]:
            if _days(run[-1]['po_date'], p['po_date']) <= T['agg_days']:
                run.append(p)
            else:
                _agg(out, key, run); run = [p]
        _agg(out, key, run)
    # DLY overlapping delay events
    for i in range(len(dly)):
        for j in range(i + 1, len(dly)):
            x, y = sorted((dly[i], dly[j]), key=lambda r: r['event_id'])
            if x['project_id'] != y['project_id']:
                continue
            lo, hi = max(x['start_date'], y['start_date']), min(x['end_date'], y['end_date'])
            if lo <= hi and _days(lo, hi) + 1 >= T['overlap']:
                put('DLY', x['project_id'], f"{x['event_id']}|{y['event_id']}", overlap_days=_days(lo, hi) + 1, union_days=_days(min(x['start_date'], y['start_date']), max(x['end_date'], y['end_date'])) + 1,
                    sum_days=sum(_days(r['start_date'], r['end_date']) + 1 for r in (x, y)))
    # LAB output per hour falling, per project and work package, complete weeks only
    def monday(s):
        return (_d(s) - datetime.timedelta(days=_d(s).weekday())).isoformat()
    for p in sorted(r['project_id'] for r in _rows(root, 'reference/projects.csv', tenant)):
        for wp in sorted({r['work_package'] for r in wo if r['project_id'] == p}):
            hrs, pay = {}, {}
            for r in ts:
                if r['project_id'] == p and r['work_package'] == wp and r['work_date'] <= AS_OF:
                    w = monday(r['work_date']); h = Fraction(r['ordinary_hours']) + Fraction(r['overtime_hours'] or 0)
                    hrs[w] = hrs.get(w, 0) + h; pay[w] = pay.get(w, 0) + h * int(r['rate_cents_per_hour'])
            qty = {r['week_start']: Fraction(r['quantity']) for r in wo if r['project_id'] == p and r['work_package'] == wp and r['week_start'] <= AS_OF}
            weeks = sorted(w for w in qty if w in hrs and _days(w, AS_OF) >= 6)
            if len(weeks) < T['base_w'] + T['recent_w']:
                continue
            rec, base = weeks[-T['recent_w']:], weeks[-(T['recent_w'] + T['base_w']):-T['recent_w']]
            bq, bh, rq, rh = (sum(qty[w] for w in base), sum(hrs[w] for w in base), sum(qty[w] for w in rec), sum(hrs[w] for w in rec))
            decline = (bq * rh - rq * bh) / (bq * rh)
            out.setdefault('lab_decline_bps', {})[f'{p}|{wp}'] = _round_half_away(decline * 10000)
            if decline * 10000 >= T['decline']:
                excess_h = rh - rq * bh / bq
                put('LAB', p, wp, decline_bps=_round_half_away(decline * 10000), cost_cents=_round_half_away(excess_h * sum(pay[w] for w in rec) / rh))
    # DEF repeat defects, same subcontractor and trade
    dg = {}
    for r in dfx:
        if r['raised_date'] <= AS_OF:
            dg.setdefault((r['project_id'], r['subcontractor'], r['trade']), []).append(r)
    for (p, s, t), rs in sorted(dg.items()):
        if len(rs) >= T['def_n']:
            rs.sort(key=lambda r: (r['raised_date'], r['defect_id']))
            cs = [int(r['rework_cost_cents']) for r in rs]
            put('DEF', p, f'{s}|{t}', events=len(rs), total_cents=sum(cs), growing=all(b > a for a, b in zip(cs, cs[1:])))
    out['expected_count'] = len(out['expected'])
    return out


def _agg(out, key, run):
    if len(run) >= 2 and all(int(p['amount_cents']) < T['agg_abs'] for p in run) and sum(int(p['amount_cents']) for p in run) >= T['agg_abs']:
        out['expected'][f"AGG|{key[0]}|{'|'.join(key)}|{run[0]['po_date']}"] = {'orders': sorted(p['po_id'] for p in run), 'aggregate_cents': sum(int(p['amount_cents']) for p in run)}


def summarise(res):
    return [{'rule': s['rule']['id'], 'subject': s['subject'], 'subtype': s['taxonomy']['subtype'], 'interpretation': s['interpretation'], 'severity': s['priority']['severity'],
             'status': s['quantification']['status'], 'gross_cents': s['quantification']['gross_cents'], 'label': s['quantification']['label'], 'strength': s['confidence']['evidence_strength'],
             'impact_cents': s['priority']['potential_impact_cents'], 'evidence_records': len(s['evidence']), 'extra': s['extra']} for s in res['signals']]


def run_golden_det(root):
    from ..ingest.golden_m3 import _world
    from . import demo_det as DD, detect as D, findings as FD, monitor as MON, portfolio as PF
    from .reference_m5 import InMemoryNotifier
    clock, prov, store, audit, who = _world()
    long = 10 ** 8
    s1, s2 = who('t1', 'zero_one', 'ann'), who('t2', 'zero_two', 'bob')
    svc1 = who('svc1', 'zero_one', 'detsvc', ('detection_service',), 'service')
    svc2 = who('svc2', 'zero_two', 'detsvc2', ('detection_service',), 'service')
    o1, o2 = who('o1', 'zero_one', DD.DEMO_OWNER, DD.OWNER_ROLES), who('o2', 'zero_two', DD.DEMO_OWNER, DD.OWNER_ROLES)      # APG-F67
    _, fv1, dv1 = DD.load_zero_all(root, s1, clock, 'zero_one', owner=o1)
    _, fv2, dv2 = DD.load_zero_all(root, s2, clock, 'zero_two', owner=o2)
    reg = D.det_registry()
    G = {'policy_versions': [fv1, dv1], 'signals': {}, 'rule_runs': {}, 'runs': {}}
    runs = {}
    for scope in PROJECTS + ('tenant',):
        rec = D.run_tenant(s1, reg, clock, AS_OF, dv1) if scope == 'tenant' else D.run_project(s1, reg, clock, scope, AS_OF, fv1, dv1)
        runs[scope] = rec
        res = rec['result']
        G['signals'][scope] = summarise(res)
        G['rule_runs'][scope] = {k: [r['status'], r['evaluated'], r['signals'], r['silent'], len(r['not_assessed'])] for k, r in res['rule_runs'].items()}
    chk = {k: D.check_record(s1, reg, r['run_key']) for k, r in runs.items()}
    G['all_runs_reproduce'] = all(c['replay'].ok and c['result_valid'] and c['pins_consistent'] for c in chk.values())
    G['runs_checked'] = len(chk)
    # findings, notifications, a repeat sweep a day later
    ingested = {k: FD.ingest_run(svc1, clock, reg, r['run_key']) for k, r in runs.items()}
    G['findings_created'] = {k: len(v['created']) for k, v in ingested.items()}
    note = InMemoryNotifier(prov, clock)
    G['first_flush'] = FD.flush_notifications(svc1, clock, note)
    G['replay_of_ingest_is_a_no_op'] = FD.ingest_run(svc1, clock, reg, runs['PRJ-002']['run_key'])['replay']
    clock.advance(86400)
    second = {}
    for scope in PROJECTS + ('tenant',):
        r2 = D.run_tenant(s1, reg, clock, '2026-10-01', dv1) if scope == 'tenant' else D.run_project(s1, reg, clock, scope, '2026-10-01', fv1, dv1)
        second[scope] = FD.ingest_run(svc1, clock, reg, r2['run_key'])
    G['second_sweep'] = {k: {x: len(second[k][x]) for x in ('created', 'updated', 'reopened', 'seen', 'not_redetected')} for k in second}
    G['second_flush'] = FD.flush_notifications(svc1, clock, note)
    G['findings_total'] = len(FD.all_findings(svc1))
    G['delivered_notes'] = len(note._contract_delivered('zero_one'))
    G['outstanding'] = len(FD.outstanding_notifications(svc1))
    pv = PF.portfolio_view(svc1)
    G['portfolio'] = {k: {x: v[x] for x in ('findings', 'quantified', 'components', 'lower_bound_cents', 'upper_bound_cents', 'overlap_adjusted', 'amount_labels')} for k, v in sorted(pv['by_interpretation'].items())}
    G['portfolio_unquantified'] = len(pv['unquantified'])
    h = MON.health(svc1, '2026-10-01')
    G['health_statement_present'] = 'not evidence that nothing is wrong' in h['statement']
    # a time-driven condition only a later sweep finds: VAR-0002 (priced, raised 2026-09-20, silent now) after more than 60 days
    later = D.run_project(s1, reg, clock, 'PRJ-002', '2026-11-30', fv1, dv1)['result']
    G['later_sweep_finds_VAR-0002'] = any(s['rule']['id'] == 'DET-R04' and s['subject'] == 'VAR-0002' for s in later['signals'])
    G['earlier_asof_labour_not_assessed'] = D.run_project(s1, reg, clock, 'PRJ-001', '2026-08-14', fv1, dv1)['result']['rule_runs']['LAB']['signals'] == 0
    # second tenant
    prj2 = sorted(r.key for r in s2.query('project'))
    r2 = {sc: (D.run_tenant(s2, reg, clock, AS_OF, dv2) if sc == 'tenant' else D.run_project(s2, reg, clock, sc, AS_OF, fv2, dv2)) for sc in prj2 + ['tenant']}
    G['zero_two_signals'] = {sc: summarise(r['result']) for sc, r in sorted(r2.items())}
    G['tenant_isolation'] = {'zero_one_run_visible_to_zero_two': s2.get('repro_record', runs['PRJ-002']['run_key']) is not None,
                             'every_zero_two_pin_resolves_in_its_own_tenant': all(s2.get(i['kind'], i['key']) is not None for r in r2.values() for i in r['inputs']),
                             'zero_two_findings_before_ingest': len(FD.all_findings(svc2)), 'zero_one_findings': len(FD.all_findings(svc1))}
    G['audit_chain_ok'] = [audit.verify(s1.ctx).ok, audit.verify(s2.ctx).ok]
    return G


def dumps(g):
    return json.dumps(g, indent=1, sort_keys=True, ensure_ascii=True) + '\n'
