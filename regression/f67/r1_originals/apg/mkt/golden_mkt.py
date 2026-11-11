"""Golden cases for the M6 procurement layer on Builder Zero (Blueprint Section 08 and the planted scenarios PS-14, PS-15, PS-16, PS-17, PS-23 and PS-25 of builder_zero/scenarios/SCENARIO_REGISTER.csv).

`run_golden_mkt()` runs the REAL pipeline - M3, M4, M5 and M6 intake, reconciliation with the SYNTHETIC register, the stored procurement runs, finding ingestion and a second tenant - over the synthetic
builder's CSV files.  `oracle_mkt()` recomputes the same facts straight from the CSV files with the csv module, `datetime.date` and `fractions.Fraction`, using NOTHING from apg, so the expected answers
cannot simply agree with the code that wrote them.

The oracle restates the demonstration policy and the demonstration specification register (SYNTHETIC, ILLUSTRATIVE values; the golden test checks they equal apg/mkt/demo_mkt.py) and four conventions that
are interpretations rather than facts of the data (logged in the programme interpretation register): orders are matched to a demand line by project, material and a date window; an order held only because
it looks like a duplicate is counted as 'possible', never silently dropped; a weighted-average rate is rounded once to whole cents before two projects are compared; a conversion rounds half away from zero
once per component.  It is written by the same builder as the code, so it is a second calculation path and not an independent audit."""
import csv, datetime, json, os
from fractions import Fraction

AS_OF = '2026-09-30'
PROJECTS = ('PRJ-001', 'PRJ-002', 'PRJ-003')
T = dict(watch=('MAT-CU', 'MAT-PBOARD', 'MAT-REO', 'MAT-STEEL'),
         bench=dict(quote=90, index=45, fx=45), buy=dict(quote=30, index=45, fx=14), rank=dict(quote=45, index=45, fx=30), imp=dict(quote=45, index=45, fx=30),
         match_window=180, surplus_tol=500, dup_window=0, decision_window=45, financing=800, storage=50, lead_var=7, day_basis=365, stage_splits=(5000, 5000), stage_offsets=(0, 30), stage_extra=25000,
         stage_admin=5000, fx_tol=100, sup_min=3, sup_acc=9500, sup_fill=9500, port_window=365, port_min=2, port_gap=500, sav_gap=300, critical=('customs_classification', 'duty_rate_confirmed', 'import_permit'))
FAMILY = {'MAT-CONC40': 'concrete', 'MAT-CONC32': 'concrete', 'MAT-STEEL': 'steel_section', 'MAT-PBOARD': 'plasterboard', 'MAT-REO': 'reinforcing_bar', 'MAT-CU': 'copper_pipe'}
ATTR = {'MAT-CONC40': {'strength_mpa': ('40', 'at_least')}, 'MAT-CONC32': {'strength_mpa': ('32', 'at_least')}, 'MAT-STEEL': {'grade': ('300PLUS', 'exact'), 'section': ('250UB', 'exact')},
        'MAT-PBOARD': {'thickness_mm': ('13', 'exact')}, 'MAT-REO': {'bar_size': ('N16', 'exact')}, 'MAT-CU': {'diameter_mm': ('22', 'exact')}}
UNIT = {'MAT-CONC40': 'm3', 'MAT-CONC32': 'm3', 'MAT-STEEL': 'tonne', 'MAT-PBOARD': 'sheet', 'MAT-REO': 'tonne', 'MAT-CU': 'metre'}
OK_CLASSES = ('comparable', 'comparable_with_adjustment')


def _rows(root, rel, tenant='zero_one', where='builder_zero'):
    p = os.path.join(root, where, tenant, rel)
    if not os.path.exists(p):
        return []
    with open(p, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def _d(s):
    return datetime.date.fromisoformat(s)


def _days(a, b):
    return (_d(b) - _d(a)).days


def _add(s, n):
    return (_d(s) + datetime.timedelta(days=n)).isoformat()


def _round(fr):
    """Half away from zero."""
    n, d = fr.numerator, fr.denominator
    q, r = divmod(abs(n), d)
    if 2 * r >= d:
        q += 1
    return q if n >= 0 else -q


def _median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if len(xs) % 2 else (xs[len(xs) // 2 - 1] + xs[len(xs) // 2]) // 2


class _World:
    def __init__(self, root, tenant):
        r = lambda rel, w='builder_zero': _rows(root, rel, tenant, w)
        self.suppliers = {x['supplier_id'] for x in r('reference/suppliers.csv')}
        self.pos = r('SRC-03_procurement/purchase_orders.csv')
        self.quotes = {x['quote_id']: x for x in r('SRC-03_procurement/quotes.csv')}
        self.demand = r('SRC-05_materials/material_demand.csv')
        self.dockets = r('SRC-05_materials/deliveries.csv')
        self.fx = r('SRC-10_market/fx_rates.csv')
        self.obs = r('SRC-10_market/market_observations.csv')
        self.readings = r('quote_readings.csv', 'mkt_data')
        self.terms = r('quote_terms.csv', 'mkt_data')
        self.tiers = r('quote_tiers.csv', 'mkt_data')
        self.assump = r('landed_assumptions.csv', 'mkt_data')
        self.checks = r('import_checks.csv', 'mkt_data')
        self.spec_reqs = r('spec_requirements.csv', 'mkt_data')
        # orders: usable = a known supplier, a positive quantity, a date; held as possible duplicates = identical project/supplier/material/quantity/rate/date (window 0)
        self.po = []
        groups = {}
        for x in self.pos:
            if x['supplier_id'] not in self.suppliers or not x['qty'].isdigit() or int(x['qty']) <= 0:
                continue
            groups.setdefault((x['project_id'], x['supplier_id'], x['material_id'], x['qty'], x['unit_rate_cents']), []).append(x)
        dup = set()
        for g in groups.values():
            g.sort(key=lambda p: (p['po_date'], p['po_id']))
            chain = [g[0]]
            for p in g[1:]:
                if _days(chain[-1]['po_date'], p['po_date']) <= T['dup_window']:
                    chain.append(p)
                else:
                    if len(chain) > 1:
                        dup |= {c['po_id'] for c in chain}
                    chain = [p]
            if len(chain) > 1:
                dup |= {c['po_id'] for c in chain}
        self.dup = dup
        for x in self.pos:
            if x['supplier_id'] in self.suppliers and x['qty'].isdigit() and int(x['qty']) > 0 and x['status'] in ('open', 'closed'):
                self.po.append(dict(x, qty=int(x['qty']), rate=int(x['unit_rate_cents']), amount=int(x['amount_cents']), dup=x['po_id'] in dup))

    # ---- market
    def ref_rate(self, cur, as_of=AS_OF):
        c = [r for r in self.fx if r['pair'] == 'AUD/' + cur and r['fx_date'] <= as_of]
        return max(c, key=lambda r: r['fx_date']) if c else None

    def to_aud(self, minor, cur, as_of=AS_OF):
        if cur == 'AUD':
            return minor, 0
        rr = self.ref_rate(cur, as_of)
        return _round(Fraction(minor) / Fraction(rr['rate'])), _days(rr['fx_date'], as_of)

    def landed(self, q, as_of=AS_OF):
        """-> (unit cents, complete).  Delivered: the rate.  Ex-works: the rate plus the stated freight.  Other bases: the rate plus every stated or assumed component; duty and clearance missing."""
        cur = q['currency']
        rate, _ = self.to_aud(int(q['unit_rate_cents']), cur, as_of)
        basis = q['incoterm_delivery_basis'].strip().lower()
        if cur == 'AUD' and basis == 'delivered':
            return rate, True
        total = rate
        if int(q['freight_cents_per_unit'] or 0) > 0 or basis == 'ex-works':
            total += self.to_aud(int(q['freight_cents_per_unit'] or 0), cur, as_of)[0]
        if cur == 'AUD' and basis == 'ex-works':
            return total, True
        for a in self.assump:
            if a['quote_id'] == q['quote_id'] and a['component'] == 'insurance' and a['per_unit_cents']:
                total += self.to_aud(int(a['per_unit_cents']), a['currency'], as_of)[0]
        return total, False

    def state(self, q, th, as_of=AS_OF):
        age, left = _days(q['issue_date'], as_of), _days(as_of, q['valid_until'])
        return 'future' if age < 0 else 'expired' if left < 0 else 'stale' if age > th['quote'] else 'current'

    def verified(self, r):
        return bool(r['verified_by'].strip() and r['verified_on'].strip() and r['verified_by'] != r['extracted_by'])

    def gate(self, q, req_material):
        """-> comparability class of quote q against a requirement for req_material (restated gate: evidence of failure from any source blocks; a pass needs a reading verified by another person)."""
        want = ATTR[req_material]
        for source in (ATTR[q['material_id']], {r['attribute']: (r['value'], None) for r in self.readings if r['quote_id'] == q['quote_id']}):
            for a, (val, _) in want.items():
                if a in source:
                    have = source[a][0]
                    mode = want[a][1]
                    if (mode == 'exact' and have != val) or (mode == 'at_least' and int(have) < int(val)):
                        return 'not_comparable'
        rd = {r['attribute']: r for r in self.readings if r['quote_id'] == q['quote_id']}
        partial = any(a not in rd or not self.verified(rd[a]) for a in want) or 'unit' not in rd or not self.verified(rd['unit']) or rd['unit']['value'] != UNIT[req_material]
        basis = q['incoterm_delivery_basis'].strip().lower()
        if q['currency'] != 'AUD' or basis not in ('delivered', 'ex-works'):
            partial = True
        if partial:
            return 'partially_comparable'
        return 'comparable_with_adjustment' if basis == 'ex-works' else 'comparable'

    # ---- demand
    def coverage(self, d, as_of=AS_OF):
        start = _add(d['required_on_site'], -T['match_window'])
        orders = [p for p in self.po if p['project_id'] == d['project_id'] and p['material_id'] == d['material_id'] and start <= p['po_date'] <= as_of]
        conf, poss = [p for p in orders if not p['dup']], [p for p in orders if p['dup']]
        need = int(d['qty'])
        ordered = sum(p['qty'] for p in conf + poss)
        refs = {p['po_id'] for p in conf + poss}
        acc = sum(int(k['qty_accepted'] or k['qty_delivered']) for k in self.dockets if k['po_id'] in refs and k['delivery_date'] <= as_of)
        return dict(need=need, confirmed=sum(p['qty'] for p in conf), ordered_all=ordered, uncovered=max(0, need - ordered), surplus=max(0, ordered - need), accepted=acc, orders=conf + poss)

    def last_paid(self, project, material, as_of=AS_OF):
        c = [p for p in self.pos if p['project_id'] == project and p['material_id'] == material and p['po_date'] <= as_of and p['supplier_id'] in self.suppliers and p['status'] in ('open', 'closed')]
        if not c:
            return None
        best = max(c, key=lambda p: (p['po_date'], p['po_id']))
        return dict(best, rate=int(best['unit_rate_cents']))


def oracle_mkt(root, tenant='zero_one'):
    w = _World(root, tenant)
    out = {'expected': {}}

    def put(rule, scope, subject, **facts):
        out['expected'][f'{rule}|{scope}|{subject}'] = facts

    # MP01 stale or unavailable market evidence for a watched material (tenant scope)
    for m in T['watch']:
        qs = [q for q in w.quotes.values() if q['material_id'] == m]
        if qs and not any(w.state(q, T['bench']) == 'current' for q in qs):
            put('MP01', 'tenant', f'{m}|quote', states=sorted([f"supplier_quote/{q['quote_id']}", w.state(q, T['bench'])] for q in qs))
        obs = [o for o in w.obs if o['material_id'] == m and o['obs_date'] <= AS_OF]
        if not obs:
            put('MP01', 'tenant', f'{m}|index', state='unavailable', age_days=None)
        else:
            age = _days(max(o['obs_date'] for o in obs), AS_OF)
            if age > T['bench']['index']:
                put('MP01', 'tenant', f'{m}|index', state='stale', age_days=age)
    # requirements: demand lines and standing specification requirements
    reqs = [dict(id='demand/' + d['demand_id'], project=d['project_id'], material=d['material_id'], d=d) for d in w.demand]
    reqs += [dict(id='spec_requirement/' + s['requirement_id'], project=s['project_id'], material=s['material_id'], d=None) for s in w.spec_reqs]
    # MP02 a cheaper quote that is not like for like
    for rq in reqs:
        ref = w.last_paid(rq['project'], rq['material'])
        for q in sorted(w.quotes.values(), key=lambda x: x['quote_id']):
            if FAMILY[q['material_id']] != FAMILY[rq['material']]:
                continue
            if w.state(q, T['rank']) in ('expired', 'future'):
                continue
            cls = w.gate(q, rq['material'])
            if cls in OK_CLASSES or ref is None:
                continue
            unit, _ = w.landed(q)
            if 0 < unit < ref['rate']:
                put('MP02', rq['project'], f"{rq['id']}>{q['quote_id']}", cls=cls, unit_cents=unit, baseline_unit_cents=ref['rate'])
    # MP03 purchase decision due, MP04 ordered above demand
    for rq in reqs:
        d = rq['d']
        if d is None:
            continue
        cov = w.coverage(d)
        need_micro = lambda n: n * 1000000
        if cov['surplus'] * 10000 > T['surplus_tol'] * cov['need'] and cov['surplus'] > 0:
            latest = max(cov['orders'], key=lambda p: (p['po_date'], p['po_id']))
            put('MP04', rq['project'], rq['id'], surplus_micro=need_micro(cov['surplus']), gross_cents=cov['surplus'] * latest['rate'])
        if cov['uncovered'] > 0:
            offers = []
            for q in w.quotes.values():
                if q['material_id'] != d['material_id']:
                    continue
                st = w.state(q, T['buy'])
                cls = w.gate(q, d['material_id'])
                if st in ('expired', 'future') or cls == 'not_comparable':
                    continue
                due = min(q['valid_until'], _add(d['required_on_site'], -(int(q['lead_time_days']) + T['lead_var'])))
                offers.append((q['quote_id'], cls, st, due))
            if offers:
                pool = [o for o in offers if o[1] in OK_CLASSES] or offers
                due = min(o[3] for o in pool)
                left = _days(AS_OF, due)
                if left <= T['decision_window']:
                    put('MP03', rq['project'], rq['id'], uncovered_micro=need_micro(cov['uncovered']), due_date=due, days_left=left, offers=sorted('supplier_quote/' + o[0] for o in offers))
    # MP05 possible duplicate orders
    groups = {}
    for p in w.pos:
        if p['supplier_id'] in w.suppliers and p['status'] in ('open', 'closed'):
            groups.setdefault((p['project_id'], p['supplier_id'], p['material_id'], p['qty'], p['unit_rate_cents']), []).append(p)
    for key, g in sorted(groups.items()):
        g.sort(key=lambda p: (p['po_date'], p['po_id']))
        chain = [g[0]]
        for p in g[1:] + [None]:
            if p is not None and _days(chain[-1]['po_date'], p['po_date']) <= T['dup_window']:
                chain.append(p)
                continue
            if len(chain) > 1:
                put('MP05', key[0], '|'.join(c['po_id'] for c in chain), orders=sorted('purchase_order/' + c['po_id'] for c in chain), gross_cents=sum(int(c['amount_cents']) for c in chain[1:]))
            chain = [p] if p is not None else []
    # MP06 / MP07 international quotes (not expired)
    for q in sorted(w.quotes.values(), key=lambda x: x['quote_id']):
        if q['currency'] == 'AUD' or q['valid_until'] < AS_OF:
            continue
        ref, _ = w.to_aud(int(q['unit_rate_cents']), q['currency'])
        stated = _round(Fraction(int(q['unit_rate_cents'])) / Fraction(q['fx_rate_used'])) if q['fx_rate_used'] else None
        age = _days(q['fx_rate_date'], AS_OF) if q['fx_rate_date'] else None
        div = _round(Fraction((ref - stated) * 10000, stated)) if stated else None
        if stated is None or age is None or age > T['imp']['fx'] or (div is not None and abs(div) > T['fx_tol']):
            put('MP06', 'tenant', q['quote_id'], reference_aud_cents=ref, stated_aud_cents=stated, divergence_bps=div, stated_rate_age_days=age)
        done = {c['check'] for c in w.checks if c['quote_id'] == q['quote_id'] and c['status'] in ('resolved', 'not_applicable') and c['evidence_ref'] and c['checked_by'] and c['checked_on']}
        open_ = [c for c in T['critical'] if c not in done]
        if open_:
            put('MP07', 'tenant', q['quote_id'], unresolved_critical=sorted(open_))
    # MP08 supplier performance: expected to stay silent on this data (all dockets accepted in full); the figures are returned for the test
    sup = {}
    for p in w.po:
        if p['dup']:
            continue
        ds = [k for k in w.dockets if k['po_id'] == p['po_id'] and k['delivery_date'] <= AS_OF]
        if ds:
            sup.setdefault(p['supplier_id'], []).append((p['qty'], sum(int(k['qty_accepted'] or k['qty_delivered']) for k in ds), sum(int(k['qty_delivered']) for k in ds if k['qty_accepted']), sum(int(k['qty_accepted']) for k in ds if k['qty_accepted'])))
    out['supplier_levels'] = {}
    for s, rows in sorted(sup.items()):
        ordered, accepted = sum(r[0] for r in rows), sum(r[1] for r in rows)
        dl, ac = sum(r[2] for r in rows), sum(r[3] for r in rows)
        fill = _round(Fraction(accepted * 10000, ordered)) if ordered else None
        acc = _round(Fraction(ac * 10000, dl)) if dl else None
        out['supplier_levels'][s] = dict(orders=len(rows), fill_bps=fill, acceptance_bps=acc)
        if len(rows) >= T['sup_min'] and ((fill is not None and fill < T['sup_fill']) or (acc is not None and acc < T['sup_acc'])):
            put('MP08', 'tenant', s, fill_bps=fill, acceptance_bps=acc)
    # MP09 a comparable current quote below the last rate paid (an estimate, never realised)
    for rq in reqs:
        d = rq['d']
        if d is None:
            continue
        ref = w.last_paid(rq['project'], rq['material'])
        if ref is None:
            continue
        cov = w.coverage(d)
        for q in sorted(w.quotes.values(), key=lambda x: x['quote_id']):
            if q['material_id'] != d['material_id'] or w.state(q, T['rank']) != 'current' or w.gate(q, d['material_id']) not in OK_CLASSES:
                continue
            unit, complete = w.landed(q)
            gap = ref['rate'] - unit
            if complete and gap > 0 and _round(Fraction(gap * 10000, ref['rate'])) >= T['sav_gap']:
                put('MP09', rq['project'], f"OPP-{rq['id'].split('/')[1]}-{q['quote_id']}", unit_gap_cents=gap, gap_bps=_round(Fraction(gap * 10000, ref['rate'])), gross_cents=gap * cov['uncovered'] if cov['uncovered'] else None)
    # MP10 portfolio purchasing: one material bought by several authorised projects, volume-weighted average rate per project rounded once to cents
    start = _add(AS_OF, -T['port_window'])
    by = {}
    for p in w.po:
        if p['dup'] or not (start <= p['po_date'] <= AS_OF) or p['unit'] != UNIT.get(p['material_id']):
            continue
        by.setdefault(p['material_id'], {}).setdefault(p['project_id'], []).append(p)
    for m, projs in sorted(by.items()):
        if len(projs) < T['port_min']:
            continue
        avg = {pr: (_round(Fraction(sum(p['qty'] * p['rate'] for p in ps), sum(p['qty'] for p in ps))), sum(p['qty'] for p in ps)) for pr, ps in projs.items()}
        low = min(avg, key=lambda k: (avg[k][0], k))
        high = max(avg, key=lambda k: (avg[k][0], k))
        gap = _round(Fraction((avg[high][0] - avg[low][0]) * 10000, avg[low][0]))
        if gap >= T['port_gap']:
            put('MP10', 'tenant', f'PORT-{m}', gap_bps=gap, estimate_cents=(avg[high][0] - avg[low][0]) * avg[high][1], lowest=low, highest=high)
    # scenario arithmetic for the declared steel offer Q-0001 (40 tonnes uncovered on DEM-0001): buy now, wait with a flat path, stage 50/50
    q = w.quotes.get('Q-0001')
    d = next((x for x in w.demand if x['demand_id'] == 'DEM-0001'), None)
    if q and d:
        cov = w.coverage(d)
        qty, unit, lead, req = cov['uncovered'], int(q['unit_rate_cents']), int(q['lead_time_days']), d['required_on_site']
        base = qty * unit

        def leg(n, order_day):
            delivery = _add(order_day, lead)
            held = _days(delivery, req)
            money = n * unit
            return n * T['storage'] * held + _round(Fraction(money * T['financing'] * held, 10000 * T['day_basis']))
        wait_day = _add(req, -(lead + T['lead_var']))
        half = qty * T['stage_splits'][0] // 10000
        stage = base + leg(half, _add(AS_OF, T['stage_offsets'][0])) + leg(qty - half, _add(AS_OF, T['stage_offsets'][1])) + T['stage_extra'] + T['stage_admin'] * (len(T['stage_splits']) - 1)
        out['scenario_totals'] = {'offer': 'supplier_quote/Q-0001', 'quantity': qty, 'buy_now': base + leg(qty, AS_OF), 'wait_flat': base + leg(qty, wait_day), 'stage': stage}
    out['expected_count'] = len(out['expected'])
    return out


def _facts(s):
    """The facts of a pipeline signal that the oracle also computes, in the oracle's own names."""
    e, rid, q = s['extra'], s['rule']['id'].replace('DET-', ''), s['quantification']
    if rid == 'MP01':
        return {'state': s['taxonomy']['subtype'].replace('market_series_', ''), 'age_days': e['age_days']} if s['subject'].endswith('|index') else {'states': sorted([x['subject'], x['state']] for x in e['states'])}
    if rid == 'MP02':
        return {'cls': e['class'], 'unit_cents': e['unit_cents'], 'baseline_unit_cents': e['baseline_unit_cents']}
    if rid == 'MP03':
        return {'days_left': e['days_left'], 'due_date': e['due_date'], 'offers': sorted(e['offers']), 'uncovered_micro': e['uncovered_micro']}
    if rid == 'MP04':
        return {'surplus_micro': e['surplus_micro'], 'gross_cents': q['gross_cents']}
    if rid == 'MP05':
        return {'orders': sorted(e['orders']), 'gross_cents': q['gross_cents']}
    if rid == 'MP06':
        return {'reference_aud_cents': e['conversion']['aud_cents'], 'stated_aud_cents': e['stated_conversion']['aud_cents'], 'divergence_bps': e['divergence_bps'], 'stated_rate_age_days': e['stated_conversion']['rate_age_days']}
    if rid == 'MP07':
        return {'unresolved_critical': sorted(e['unresolved_critical'])}
    if rid == 'MP09':
        return {'unit_gap_cents': e['opportunity']['unit_gap_cents'], 'gap_bps': e['opportunity']['gap_bps'], 'gross_cents': q['gross_cents']}
    if rid == 'MP10':
        pf = e['portfolio']
        return {'gap_bps': pf['gap_bps'], 'estimate_cents': pf['estimate_cents'], 'lowest': pf['lowest_project'], 'highest': pf['highest_project']}
    return None


def summarise(res):
    return [{'rule': s['rule']['id'], 'subject': s['subject'], 'subtype': s['taxonomy']['subtype'], 'interpretation': s['interpretation'], 'severity': s['priority']['severity'], 'status': s['quantification']['status'],
             'gross_cents': s['quantification']['gross_cents'], 'label': s['quantification']['label'], 'strength': s['confidence']['evidence_strength'], 'impact_cents': s['priority']['potential_impact_cents'],
             'evidence_records': len(s['evidence']), 'facts': _facts(s)} for s in res['signals']]


def run_golden_mkt(root):
    from ..ingest.golden_m3 import _world
    from ..det import findings as FD, portfolio as PF
    from . import demo_mkt as DM, detect as MD
    clock, prov, store, audit, who = _world()
    s1, s2 = who('t1', 'zero_one', 'ann'), who('t2', 'zero_two', 'bob')
    svc1 = who('svc1', 'zero_one', 'detsvc', ('detection_service',), 'service')
    svc2 = who('svc2', 'zero_two', 'detsvc2', ('detection_service',), 'service')
    _, fv1, dv1, mv1, sv1 = DM.load_mkt_all(root, s1, clock, 'zero_one')
    _, fv2, dv2, mv2, sv2 = DM.load_mkt_all(root, s2, clock, 'zero_two')
    reg = MD.mkt_registry()
    G = {'policy_versions': [fv1, dv1, mv1, sv1], 'signals': {}, 'rule_runs': {}, 'scenarios': {}}
    runs = {}
    for scope in PROJECTS + ('tenant',):
        rec = MD.run_tenant(s1, reg, clock, AS_OF, fv1, dv1, mv1, sv1, list(PROJECTS)) if scope == 'tenant' else MD.run_project(s1, reg, clock, scope, AS_OF, fv1, dv1, mv1, sv1)
        runs[scope] = rec
        res = rec['result']
        G['signals'][scope] = summarise(res)
        G['rule_runs'][scope] = {k: [r['status'], r['evaluated'], r['signals'], r['silent'], len(r['not_assessed'])] for k, r in res['rule_runs'].items()}
        for rid, rq in (res['analyses'].get('requirements') or {}).items():
            for x in (rq.get('scenarios') or {}).get('scenarios', []):
                if x.get('total_cost_cents') is not None:
                    G['scenarios'].setdefault(scope, {})[f"{rid}|{x['offer']}|{x['scenario']}"] = x['total_cost_cents']
    chk = {k: MD.check_record(s1, reg, r['run_key']) for k, r in runs.items()}
    G['all_runs_reproduce'] = all(c['replay'].ok and c['result_valid'] and c['pins_consistent'] for c in chk.values())
    G['runs_checked'] = len(chk)
    G['event_count'] = {k: len(r['result']['events']) for k, r in runs.items()}
    # a signal never claims a recommendation, a chosen supplier or a realised saving; every ranking says a person must approve
    G['no_definitive_recommendation_when_a_gate_fails'] = all(not (rq['ranking']['definitive'] and rq['ranking']['status'] != 'definitive') for r in runs.values() for rq in (r['result']['analyses'].get('requirements') or {}).values())
    G['rankings'] = {f'{k}|{rid}': {'status': rq['ranking']['status'], 'definitive': rq['ranking']['definitive'], 'human_approval_required': rq['ranking']['human_approval_required']}
                     for k, r in runs.items() for rid, rq in sorted((r['result']['analyses'].get('requirements') or {}).items())}
    ingested = {k: FD.ingest_run(svc1, clock, reg, r['run_key']) for k, r in runs.items()}
    G['findings_created'] = {k: len(v['created']) for k, v in ingested.items()}
    G['replay_of_ingest_is_a_no_op'] = FD.ingest_run(svc1, clock, reg, runs['PRJ-002']['run_key'])['replay']
    G['findings_total'] = len(FD.all_findings(svc1))
    pv = PF.portfolio_view(svc1)
    G['portfolio'] = {k: {x: v[x] for x in ('findings', 'quantified', 'unquantified', 'quantified_amount_available', 'range_display', 'lower_bound_cents', 'upper_bound_cents', 'amount_labels')} for k, v in sorted(pv['by_interpretation'].items())}
    # second tenant: its own records, its own answer; the first builder's runs are invisible to it
    prj2 = sorted(r.key for r in s2.query('project'))
    r2 = {sc: (MD.run_tenant(s2, reg, clock, AS_OF, fv2, dv2, mv2, sv2, prj2) if sc == 'tenant' else MD.run_project(s2, reg, clock, sc, AS_OF, fv2, dv2, mv2, sv2)) for sc in prj2 + ['tenant']}
    G['zero_two_signals'] = {sc: summarise(r['result']) for sc, r in sorted(r2.items())}
    G['tenant_isolation'] = {'zero_one_run_visible_to_zero_two': s2.get('repro_record', runs['PRJ-002']['run_key']) is not None,
                             'every_zero_two_pin_resolves_in_its_own_tenant': all(s2.get(i['kind'], i['key']) is not None for r in r2.values() for i in r['inputs']),
                             'zero_two_findings_before_ingest': len(FD.all_findings(svc2)), 'zero_one_findings': len(FD.all_findings(svc1))}
    G['audit_chain_ok'] = [audit.verify(s1.ctx).ok, audit.verify(s2.ctx).ok]
    return G


def dumps(g):
    return json.dumps(g, indent=1, sort_keys=True, ensure_ascii=True) + '\n'
