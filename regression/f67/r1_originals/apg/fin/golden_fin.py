"""Golden cases for the M4 financial core on Builder Zero.  The REAL pipeline (M3 ingestion, M4 intake, reconciliation with the SYNTHETIC register, then the stored calculations)
runs over the synthetic builder's CSV files; `regression/GOLDEN_FIN.json` holds the expected dict.  `oracle_fin()` recomputes the headline numbers straight from the CSV files with
the csv module, `datetime.date` and `fractions.Fraction`, using NOTHING from apg, so the golden file cannot simply agree with the code that wrote it.

The oracle restates the rules of the DEMONSTRATION policy (apg/fin/demo_fin.py) in plain code; that policy is synthetic and illustrative and is not a product decision.  Where the
oracle simplifies (it does not model every held-record class), the golden test only compares the quantities the simplification cannot affect, and says so."""
import csv, datetime, json, os
from fractions import Fraction
from .. import tenancy
from ..ingest import demo_setup as D, views as V3
from ..ingest.golden_m3 import _world
from . import calc_records as C, demo_fin as DF, policy as P

AS_OF = '2026-09-30'
PROJECTS = ('PRJ-001', 'PRJ-002', 'PRJ-003')
POLICY_VERSION = 'SYN-FIN-POL-1'


def _rows(root, rel, tenant='zero_one'):
    with open(os.path.join(root, 'builder_zero', tenant, rel), encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def _round_half_away(fr):
    """Fraction -> int, halves away from zero (written independently of apg.fin.fmath)."""
    n, d = fr.numerator, fr.denominator
    q, r = divmod(abs(n), d)
    if 2 * r >= d:
        q += 1
    return q if n >= 0 else -q


def _days(a, b):
    return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days


def oracle_fin(root):
    """Independent recomputation: csv module and arithmetic only."""
    inv = _rows(root, 'SRC-01_accounting/ap_invoices.csv'); crn = _rows(root, 'SRC-01_accounting/credit_notes.csv')
    sup = {r['supplier_id'] for r in _rows(root, 'reference/suppliers.csv')}
    pm = {r['invoice_ref']: r['ex_gst_cents'] for r in _rows(root, 'conflicting_sources/pm_system_invoices.csv')}
    bud = _rows(root, 'SRC-02_costing/budget_lines.csv'); fc = _rows(root, 'SRC-02_costing/forecasts.csv')
    con = {r['project_id']: r for r in _rows(root, 'SRC-07_commercial/contracts.csv')}; prj = {r['project_id']: r for r in _rows(root, 'reference/projects.csv')}
    var = _rows(root, 'SRC-07_commercial/variations.csv'); ret = {r['project_id']: r for r in _rows(root, 'SRC-09_retentions/retention_ledger.csv')}
    sec = _rows(root, 'SRC-09_retentions/security_instruments.csv'); fac = _rows(root, 'SRC-14_bank/funding_facility.csv')
    # which invoices are left out (the demonstration reconciliation register's three classes)
    seen, dup = {}, set()
    for r in inv:
        k = (r['supplier_id'], r['supplier_invoice_no']); sig = (r['project_id'], r['po_id'], r['invoice_date'], r['ex_gst_cents'], r['gst_cents'])
        if k in seen and seen[k] == sig:
            dup.add(r['invoice_id'])
        else:
            seen.setdefault(k, sig)
    unknown_sup = {r['invoice_id'] for r in inv if r['supplier_id'] not in sup}
    conflicted = {r['invoice_id'] for r in inv if r['invoice_id'] in pm and pm[r['invoice_id']] != r['ex_gst_cents']}
    held = unknown_sup | conflicted
    out = {'duplicate_delivery_ids': sorted(dup), 'held_invoice_ids': sorted(held), 'projects': {}}

    def actual_by_code(p, cutoff):
        a = {}
        proj_of = {r['invoice_id']: r for r in inv}
        for r in inv:
            if r['project_id'] == p and r['invoice_id'] not in dup | held and r['invoice_date'] <= cutoff:
                a[r['cost_code']] = a.get(r['cost_code'], 0) + int(r['ex_gst_cents'])
        for c in crn:
            i = proj_of.get(c['against_invoice_id'])
            if i and i['project_id'] == p and i['invoice_id'] not in dup | held and c['credit_date'] <= cutoff:
                a[i['cost_code']] = a.get(i['cost_code'], 0) - int(c['ex_gst_cents'])
        return a

    for p in PROJECTS:
        o = {}
        a_asof = actual_by_code(p, AS_OF)
        o['actual_cents'] = sum(a_asof.values())
        o['held_for_project'] = sorted(i for i in held if next(r['project_id'] for r in inv if r['invoice_id'] == i) == p)
        approved = sum(int(v['value_cents']) for v in var if v['project_id'] == p and v['status'] == 'approved' and v['value_cents'] != '')
        o['revenue_cents'] = int(con[p]['original_contract_cents']) + approved
        o['revenue_summary_agrees'] = int(con[p]['approved_variations_cents']) == approved
        o['actual_provisional'] = bool(o['held_for_project'])
        # forecast: latest declared version on or before the as-of date; otherwise derived from the budget
        b = {}
        for r in bud:
            if r['project_id'] == p:
                b[r['cost_code']] = b.get(r['cost_code'], 0) + int(r['budget_cents'])
        versions = sorted({(r['forecast_date'], r['forecast_version']) for r in fc if r['project_id'] == p and r['forecast_date'] <= AS_OF})
        if versions:
            fdate, fver = versions[-1]
            declared = {r['cost_code']: int(r['cost_to_complete_cents']) for r in fc if r['project_id'] == p and r['forecast_version'] == fver}
        else:
            fdate, fver, declared = AS_OF, None, {}
        a_fd = actual_by_code(p, fdate)
        ctc, unknown = {}, []
        for code in sorted(set(b) | set(declared) | set(a_fd)):
            if code in declared:
                ctc[code] = declared[code]
            elif code in b and b[code] - a_fd.get(code, 0) >= 0:
                ctc[code] = b[code] - a_fd.get(code, 0)
            else:
                unknown.append(code)
        ffc = sum(a_fd.values()) + sum(ctc.values())
        o['forecast'] = {'version': fver, 'date': fdate, 'actual_to_forecast_date_cents': sum(a_fd.values()), 'ctc_known_cents': sum(ctc.values()), 'ctc_unknown_codes': unknown,
                         'ffc_known_cents': ffc, 'margin_on_known_cents': o['revenue_cents'] - ffc, 'complete': not unknown}
        o['recognised_on_known'] = {'revenue_cents': _round_half_away(Fraction(o['revenue_cents'] * sum(a_fd.values()), ffc)), 'cost_cents': sum(a_fd.values())}
        o['recognised_on_known']['margin_cents'] = o['recognised_on_known']['revenue_cents'] - o['recognised_on_known']['cost_cents']
        o['retention_cents'] = int(ret[p]['retention_held_cents']); o['retention_due'] = ret[p]['release_due_date']
        o['security_cents'] = sum(int(s['face_value_cents']) for s in sec if s['project_id'] == p)
        if o['retention_due'] <= AS_OF and o['retention_cents'] > 0:
            o['carrying_cents'] = None
        else:
            funded = Fraction(o['retention_cents'] * 5000, 10000)          # funded share 50% (ILLUSTRATIVE, the demonstration policy's)
            o['carrying_cents'] = _round_half_away(Fraction(_round_half_away(funded)) * int(fac[0]['rate_bps']) * _days(AS_OF, o['retention_due']) / (10000 * 365))
        o['cash_adjusted_on_known'] = None if o['carrying_cents'] is None else o['forecast']['margin_on_known_cents'] - o['carrying_cents']
        out['projects'][p] = o
    out['sum_of_project_actuals_cents'] = sum(v['actual_cents'] for v in out['projects'].values())
    return out


def summ(f):
    """The part of a stored figure the golden file keeps."""
    return {'state': f['state'], 'cents': f['value']['cents'], 'bps': f['value']['bps'], 'contributed': len(f['contributed']), 'excluded': sorted([e['ref'], e['class']] for e in f['excluded']),
            'unknown': sorted(u['input'] for u in f['unknown_inputs']), 'disputed': sorted(d['ref'] for d in f['disputed']), 'reasons': sorted(f['reasons']),
            'applied': {k: len(v) for k, v in sorted(f['applied'].items())}, 'policy_approved': f['policy']['approved']}


def run_golden_fin(root):
    clock, prov, store, audit, who = _world()
    s1, s2 = who('t1', 'zero_one', 'ann'), who('t2', 'zero_two', 'bob')
    G = {}
    r1 = DF.load_zero(root, s1, clock, 'zero_one'); r2 = DF.load_zero(root, s2, clock, 'zero_two')
    G['fin_ingest_counts_zero_one'] = {n: dict(r['counts']) for n, r in sorted(r1.items()) if n in {os.path.basename(x[1]) for x in DF.FIN_FILES}}
    pol = DF.demo_policy(); P.store_policy(s1, pol); P.store_policy(s2, pol)
    reg = C.fin_registry()
    runs, figs = {}, {}
    for p in PROJECTS:
        for name, fid, extra in (('actual_cost', 'fin.actual_cost', None), ('commitments', 'fin.commitments', None), ('revenue', 'fin.revenue', None), ('forecast', 'fin.forecast', None),
                                 ('recognised_margin', 'fin.recognised_margin', None), ('cash_adjusted', 'fin.cash_adjusted', None), ('retention', 'fin.cash_position', {'what': 'retention'}),
                                 ('security', 'fin.cash_position', {'what': 'security'}), ('retention_carrying', 'fin.cash_position', {'what': 'retention_carrying'})):
            rec = C.run_calc(s1, reg, clock, fid, p, AS_OF, POLICY_VERSION, extra)
            runs[(p, name)] = rec
            figs.setdefault(p, {})[name] = summ(rec['result'])
    G['figures'] = figs
    G['forecast_classified'] = {p: {k: runs[(p, 'forecast')]['result']['classified'].get(k) for k in ('forecast_version', 'forecast_date', 'ffr_cents', 'actual_cents', 'ctc_cents', 'ffc_cents', 'since_forecast_actual_cents')} for p in PROJECTS}
    G['ctc_by_code_PRJ-002'] = {k: [v.get('method'), v.get('cents'), v.get('unknown')] for k, v in sorted(runs[('PRJ-002', 'forecast')]['result']['classified']['ctc_by_code'].items()) if v.get('cents') is None or v.get('method') == 'declared'}
    G['recognised_classified'] = {p: {k: runs[(p, 'recognised_margin')]['result']['classified'].get(k) for k in ('recognised_revenue_cents', 'recognised_cost_cents', 'percent_complete_bps')} for p in PROJECTS}
    G['carrying_inputs'] = {p: runs[(p, 'retention_carrying')]['result']['classified'].get('inputs') for p in PROJECTS}
    # every stored calculation replays, its figure is valid and its pins agree
    checks = {f'{p}/{n}': (lambda c: [c['replay'].ok, c['figure_valid'], c['pins_consistent']])(C.check_record(s1, reg, rec['run_key'])) for (p, n), rec in sorted(runs.items())}
    G['all_runs_reproduce'] = all(v == [True, True, True] for v in checks.values())
    G['runs_checked'] = len(checks)
    # the movement bridge between the two stored PRJ-002 forecasts
    a = C.run_calc(s1, reg, clock, 'fin.forecast', 'PRJ-002', '2026-08-31', POLICY_VERSION, {'forecast_version': 'F-2026-08'})
    b = C.run_calc(s1, reg, clock, 'fin.forecast', 'PRJ-002', AS_OF, POLICY_VERSION, {'forecast_version': 'F-2026-09'})
    br = C.run_bridge(s1, reg, clock, a['run_key'], b['run_key'])['result']
    G['bridge_PRJ-002'] = {'state': br['state'], 'delta_cents': br['value']['cents'], 'reconciles': br['classified']['reconciles'], 'explained_cents': br['classified']['explained_cents'],
                           'unexplained_cents': br['classified']['unexplained_cents'], 'items': [[i['part'], i['cost_code'], i['effect_cents'], i['explained'], i['why']] for i in br['classified']['items']
                                                                                              if i['part'] != 'actual_cost'], 'actual_cost_items': len([i for i in br['classified']['items'] if i['part'] == 'actual_cost'])}
    # M3 cross-check: the per-project actual costs add up to the M3 authoritative invoice cost total
    m3, _ = V3.invoice_cost_view(s1, AS_OF)
    G['m3_cross_check'] = {'m3_authoritative_cents': m3.cents, 'sum_of_m4_project_actuals_cents': sum(runs[(p, 'actual_cost')]['result']['value']['cents'] for p in PROJECTS),
                           'm3_excluded': sorted(e[0] for e in m3.excluded)}
    # tenant isolation: the second builder's figures come from its own records only
    s2_before = C.run_calc(s2, reg, clock, 'fin.actual_cost', 'PRJ-001', AS_OF, POLICY_VERSION)
    G['tenant_isolation'] = {'zero_two_PRJ-001_actual': s2_before['result']['value']['cents'], 'zero_two_state': s2_before['result']['state'],
                             'zero_one_PRJ-001_actual': runs[('PRJ-001', 'actual_cost')]['result']['value']['cents'],
                             'zero_one_run_visible_to_zero_two': s2.get('repro_record', runs[('PRJ-001', 'actual_cost')]['run_key']) is not None,
                             'every_zero_two_pin_resolves_in_its_own_tenant': all(s2.get(i['kind'], i['key']) is not None for i in s2_before['inputs'])}
    G['audit_chain_ok'] = [audit.verify(s1.ctx).ok, audit.verify(s2.ctx).ok]
    return G


def dumps(g):
    return json.dumps(g, indent=1, sort_keys=True, ensure_ascii=True) + '\n'
