"""Cost and commitment rules.  Blueprint: Section 06 section 5.2 rules 1, 2, 3 and 9, section 5.4 and CR-02 R5 (aggregation), section 4 (data integrity).

Every rule is a pure function of the pinned snapshot (snap.Facts) and the detection policy, and returns (signals, run).  Amounts come from the M4 builders over the SAME pinned
records (costs.build_actual, commitments.build_commitments, forecast.budget_by_code), so a finding's number is the number a financial figure would show, with the same held,
disputed and unknown inputs.  A rule never writes a financial result.

R01  actual cost above budget by more than the tolerance (strictly more; equal is within tolerance)
R02  a purchase-order amendment that no approved change stands behind
R03  invoiced amount above the order's committed amount by more than the tolerance (invoices carry an amount only, so this is an AMOUNT comparison; quantity and unit rate are
     not ingested - finding F-09)
R09  a forecast cost-to-complete movement of at least the configured size with no recorded reason
AGG  orders inside one aggregation group and window that together reach the single-order threshold although none does alone (the M2 CR-02 reference model decides this)
D01  records held out of the actual cost figure (a data-integrity signal, kept apart from leakage)"""
from .. import materiality as M
from ..fin import commitments, costs, fmath, forecast
from ..fin.figure import HELD
from ..fin.intake import usable
from . import common as C, signal as S

LIMIT_SCOPE = 'actual cost is supplier invoices only; labour, plant, accruals and overhead are not in it (finding F-17, CR-02 A5)'


def _budget_refs(F, project, code):
    out = []
    certain, _ = F.of_project('budget_line', project)
    for key in certain:
        b, st = F.get('budget_line', key), F.recon('budget_line', key)
        if (b['fields'].get('cost_code_ref') or costs.NO_CODE) == code and st is not None:
            out.append(S.evidence('budget_line/' + key, F.rev('budget_line', key), 'budget', st['effective_outcome']))
    return out


def r01_budget(F, dp, project, as_of):
    rule, params, run = C.start(F, dp, 'R01')
    if rule is None:
        return [], run
    fig = costs.build_actual(F, project, as_of)
    if fig['state'] == 'cannot_assess':
        return C.cannot(run, *fig['reasons'])
    budget, _, bexcl, _ = forecast.budget_by_code(F, project)
    for ref, cls, codes in bexcl:
        run['not_assessed'].append({'subject': ref, 'why': cls + ':' + ','.join(codes)})
    by_code = fig['classified']['by_cost_code']
    sigs = []
    for code in sorted(budget):
        run['evaluated'] += 1
        b = budget[code]
        if b <= 0:
            run['not_assessed'].append({'subject': code, 'why': 'BUDGET_NOT_POSITIVE'})
            continue
        actual = by_code.get(code, 0)
        over = fmath.bps_of(actual - b, b)
        if not C.exceeds_bps(actual - b, b, params['tolerance_bps']):
            run['silent'] += 1
            continue
        ev = [S.evidence(e['ref'], e['revision'], 'actual_cost:' + e['role']) for e in fig['contributed'] if e.get('cost_code') == code] + _budget_refs(F, project, code)
        prov = fig['state'] != 'authoritative'
        sigs.append(S.make(
            rule, {'level': 'project', 'project': project}, code, 'cost_commitments', 'actual_cost_over_budget', 'forecast_exposure', ev,
            f'actual cost to {as_of} is {C.money(actual)} against a budget of {C.money(b)} ({C.pct(over)} over)',
            f'actual cost within {C.pct(params["tolerance_bps"])} above the budget of {C.money(b)}',
            f'the cost already incurred exceeds the budget for cost code {code} by more than the configured tolerance',
            S.quantified(actual - b, 'actual cost (M4 fin.actual_cost, supplier invoices net of credits) less budget (M4 budget lines)', f'fin.actual_cost@{as_of}:{code}',
                         ['cost already incurred above the budget; the effect on margin is not computed here', 'the budget is taken as stored (revisions: see the budget line records)'], label='estimate'),
            'moderate' if prov else 'strong', missing=['whether the budget was revised', 'labour, plant and accruals for this code (not in actual cost)'],
            alternatives=['the budget was not revised after an approved change', 'invoices were coded to the wrong cost code'], limits=[LIMIT_SCOPE] + (['ACTUAL_COST_FIGURE_PROVISIONAL'] if prov else []),
            impact_cents=actual - b, owner_role='project_manager', extra={'budget_cents': b, 'actual_cents': actual, 'over_bps': over, 'figure_state': fig['state']}))
        run['signals'] += 1
    return sigs, run


def r02_amendment(F, dp, project, as_of):
    rule, params, run = C.start(F, dp, 'R02')
    if rule is None:
        return [], run
    fig = commitments.build_commitments(F, project, as_of)
    if fig['state'] == 'cannot_assess':
        return C.cannot(run, *fig['reasons'])
    sigs = []
    for pk, pl in sorted(fig['classified']['po_lines'].items()):
        for am in pl['amendments']:
            run['evaluated'] += 1
            if am['treatment'] == 'committed':
                run['silent'] += 1
                continue
            if am['treatment'] == 'held':
                run['not_assessed'].append({'subject': 'po_amendment/' + am['amendment'], 'why': 'held'})
                continue
            if am.get('why') == 'VARIATION_STATUS_MAP_NOT_CONFIGURED':
                run['not_assessed'].append({'subject': 'po_amendment/' + am['amendment'], 'why': 'VARIATION_STATUS_MAP_NOT_CONFIGURED (CR-02 A12)'})
                continue
            ak = am['amendment']
            ev = [S.evidence('po_amendment/' + ak, F.rev('po_amendment', ak), 'amendment', (F.recon('po_amendment', ak) or {}).get('effective_outcome')),
                  S.evidence('purchase_order/' + pk, F.rev('purchase_order', pk), 'order')]
            chg = (F.get('po_amendment', ak)['fields'] or {}).get('approved_change_ref')
            if chg and F.get('variation', chg) is not None:
                ev.append(S.evidence('variation/' + chg, F.rev('variation', chg), 'named_change'))
            blank = am['why'] == 'NO_APPROVED_CHANGE_REFERENCE'
            sigs.append(S.make(
                rule, {'level': 'project', 'project': project}, ak, 'cost_commitments', 'commitment_without_approved_change', 'forecast_exposure', ev,
                f'amendment {ak} adds {C.money(am["delta_cents"])} to order {pk} and ' + ('names no approved change' if blank else f'names change {chg}, which is not approved ({am["why"].split(":", 1)[1]})'),
                'a commitment increase that stands behind an approved change',
                'the order value increased without an approved change behind it, so the extra is exposure rather than an approved commitment',
                S.quantified(am['delta_cents'], 'amendment amount as recorded', 'po_amendment/' + ak, ['the amount is the recorded amendment; whether it is recoverable or owed is not assessed'], label='record'),
                'strong', missing=['the reason the change was not recorded'] if blank else ['the status of the named change'], alternatives=['an approval exists but was not linked to the amendment'],
                limits=[], impact_cents=am['delta_cents'], owner_role='commercial_manager', extra={'purchase_order': pk, 'why': am['why']}))
            run['signals'] += 1
    return sigs, run


def r03_invoice_vs_order(F, dp, project, as_of):
    rule, params, run = C.start(F, dp, 'R03')
    if rule is None:
        return [], run
    fig = commitments.build_commitments(F, project, as_of)
    if fig['state'] == 'cannot_assess':
        return C.cannot(run, *fig['reasons'])
    sigs = []
    for pk, pl in sorted(fig['classified']['po_lines'].items()):
        if pl['class'] != 'committed' or not pl['invoices']:
            continue
        run['evaluated'] += 1
        for u in pl['unresolved_invoices']:
            run['not_assessed'].append({'subject': 'ap_invoice/' + u, 'why': 'invoice for ' + pk + ' is held, so the invoiced total may be higher'})
        commit = pl['committed_cents'] + pl['approved_amendments_cents']
        over = pl['overrun_cents']
        bps = fmath.bps_of(over, commit)
        if over <= 0 or not C.exceeds_bps(over, commit, params['tolerance_bps']):
            run['silent'] += 1
            continue
        ev = [S.evidence('purchase_order/' + pk, F.rev('purchase_order', pk), 'order')] + [S.evidence('ap_invoice/' + k, F.rev('ap_invoice', k), 'invoice', (F.recon('ap_invoice', k) or {}).get('effective_outcome')) for k in pl['invoices']]
        sigs.append(S.make(
            rule, {'level': 'project', 'project': project}, pk, 'procurement_materials', 'invoiced_above_order', 'forecast_exposure', ev,
            f'invoices counted against order {pk} total {C.money(pl["invoiced_cents"])} against a committed {C.money(commit)} ({C.pct(bps)} above)',
            f'invoiced amount within {C.pct(params["tolerance_bps"])} above the committed amount',
            'the invoiced amount is above what the order commits, by more than the configured tolerance; invoices carry an amount only, so quantity and unit rate cannot be compared',
            S.quantified(over, 'invoiced total less committed total (M4 fin.commitments)', f'fin.commitments@{as_of}:{pk}', ['the extra may be an authorised extra, an overcharge or a pricing error; this is not decided here'],
                         label='record'),
            'strong' if not pl['unresolved_invoices'] else 'moderate', missing=['invoice quantity and unit rate (not ingested)', 'whether the extra was authorised'],
            alternatives=['an authorised extra not yet recorded as an amendment', 'a part-delivery priced above the order rate'], limits=['AMOUNT_COMPARISON_ONLY (finding F-09)'], impact_cents=over,
            owner_role='procurement_manager', extra={'committed_cents': commit, 'invoiced_cents': pl['invoiced_cents'], 'over_bps': bps}))
        run['signals'] += 1
    return sigs, run


def r09_forecast_movement(F, dp, project, as_of):
    rule, params, run = C.start(F, dp, 'R09')
    if rule is None:
        return [], run
    certain, _ = F.of_project('ctc_line', project)
    by_code = {}
    for key in certain:
        p = F.get('ctc_line', key)
        if p.get('conflict') or not usable(p) or p['fields'].get('cost_to_complete_cents') is None or not p['fields'].get('forecast_date') or p['fields']['forecast_date'] > as_of:
            run['not_assessed'].append({'subject': 'ctc_line/' + key, 'why': 'held, disputed, undated or after the as-of date'})
            continue
        by_code.setdefault(p['fields'].get('cost_code_ref') or costs.NO_CODE, []).append((p['fields']['forecast_date'], p['fields'].get('forecast_version') or '', key, p))
    sigs = []
    for code in sorted(by_code):
        lines = sorted(by_code[code], key=lambda x: (x[0], x[1], x[2]))
        for (d0, v0, k0, p0), (d1, v1, k1, p1) in zip(lines, lines[1:]):
            run['evaluated'] += 1
            move = p1['fields']['cost_to_complete_cents'] - p0['fields']['cost_to_complete_cents']
            explained = bool(p1['fields'].get('movement_reason_text'))
            if abs(move) < params['movement_abs_cents'] or explained:
                run['silent'] += 1
                continue
            up = move > 0
            ev = [S.evidence('ctc_line/' + k0, F.rev('ctc_line', k0), 'earlier_forecast'), S.evidence('ctc_line/' + k1, F.rev('ctc_line', k1), 'later_forecast')]
            sigs.append(S.make(
                rule, {'level': 'project', 'project': project}, f'{code}|{v0}>{v1}', 'cost_commitments', 'forecast_movement_unexplained', 'forecast_exposure' if up else 'data_quality_risk', ev,
                f'cost to complete for {code} moved from {C.money(p0["fields"]["cost_to_complete_cents"])} ({v0}, {d0}) to {C.money(p1["fields"]["cost_to_complete_cents"])} ({v1}, {d1}): {C.money(move)}, and no movement reason is recorded',
                'a movement of this size carries a recorded reason', 'the forecast moved by at least the configured size and the later forecast gives no reason',
                S.quantified(move, 'difference between two stored cost-to-complete lines', f'ctc_line/{k0} to ctc_line/{k1}', ['the later forecast is taken as stated; it is not tested'], label='record') if up
                else S.unquantified('a reduction in forecast cost is not a loss; the finding is that it is unexplained'),
                'strong', missing=['the reason for the movement'], alternatives=['a scope change', 'a correction of an earlier forecast error', 'a new quote or order'],
                limits=['a recorded reason is accepted as stated; its adequacy is a person\'s judgement', 'the M4 movement bridge between two adopted forecast runs is not consulted by this rule'],
                impact_cents=abs(move), owner_role='project_manager', extra={'direction': 'increase' if up else 'decrease', 'movement_cents': move}))
            run['signals'] += 1
    return sigs, run


def _placeable(F, key, keys, as_of):
    """-> (record for the M2 model or None, why not)."""
    p, st = F.get('purchase_order', key), F.recon('purchase_order', key)
    if st is None or st['lifecycle'] == 'duplicate_of' or st['effective_outcome'] not in costs.AUTH_OUTCOMES or st['amount_cents'] is None:
        return None, 'not usable (' + ('no reconciliation state' if st is None else st['lifecycle'] if st['lifecycle'] != 'current' else st['effective_outcome']) + ')'
    fl = p['fields']
    date = fl.get('order_date')
    if not date or date > as_of:
        return None, 'undated or after the as-of date'
    src = {'project': fl.get('project_ref'), 'supplier': C.supplier_of(F, 'purchase_order', key), 'material': fl.get('material_ref'), 'cost_code': fl.get('cost_code_ref')}
    grp = {k: src[k] for k in keys}
    if any(not v for v in grp.values()):                                        # a blank field is absent from the stored record, never an empty string or a non-text value
        return None, 'a grouping key is missing: ' + ','.join(k for k in keys if not src[k])
    return {'id': key, 'subject': 'purchase_order', 'amount_cents': st['amount_cents'], 'date': date, 'group': grp}, ''


def agg_split_orders(F, dp, project, as_of):
    rule, params, run = C.start(F, dp, 'AGG')
    if rule is None:
        return [], run
    spec = {'keys': params['keys'], 'window_days': params['window_days']}
    model = {'version': 'DET-AGG/' + dp['version'], 'rules': {'purchase_order': {'abs_cents': params['single_order_abs_cents']}}, 'always_material': [], 'aggregate': True, 'aggregation': spec}
    certain, _ = F.of_project('purchase_order', project)
    recs = {}
    for key in certain:
        r, why = _placeable(F, key, params['keys'], as_of)
        if r is None:
            run['not_assessed'].append({'subject': 'purchase_order/' + key, 'why': why})
        else:
            recs[key] = r
    parent = {k: k for k in recs}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    split = {}
    for key in sorted(recs):
        run['evaluated'] += 1
        others = [recs[k] for k in sorted(recs) if k != key]
        res = M.assess_with_context(recs[key], others, model)
        members, _ = M.select_group(recs[key], others, spec)
        if 'M-ABS' in res['reasons']:
            split[key] = 'single'
        elif 'M-AGG' in res['reasons'] and members:
            split[key] = 'agg'
            for m in members:
                parent[find(m['id'])] = find(key)
        else:
            split.setdefault(key, 'none')
    clusters = {}
    for key in recs:
        if split.get(key) == 'agg':
            clusters.setdefault(find(key), set()).add(key)
    sigs = []
    for root, seeds in sorted(clusters.items()):
        members = sorted(k for k in recs if find(k) == root)
        if any(split.get(k) == 'single' for k in members):
            run['notes'].append('CLUSTER_WITH_SINGLE_MATERIAL_ORDER:' + ','.join(members))
            continue
        first = min(recs[k]['date'] for k in members)
        total = sum(recs[k]['amount_cents'] for k in members)
        g = recs[members[0]]['group']
        ev = [S.evidence('purchase_order/' + k, F.rev('purchase_order', k), 'order', (F.recon('purchase_order', k) or {}).get('effective_outcome')) for k in members]
        sigs.append(S.make(
            rule, {'level': 'project', 'project': project}, '|'.join([g.get(k, '') for k in params['keys']]) + '|' + first, 'cost_commitments', 'orders_split_inside_window', 'compliance_risk', ev,
            f'{len(members)} orders in one group ({", ".join(f"{k}={v}" for k, v in sorted(g.items()))}) inside {params["window_days"]} days total {C.money(total)}; each is below the single-order threshold of {C.money(params["single_order_abs_cents"])}',
            'orders that stand alone, or a combined value below the single-order threshold', 'together the orders reach the threshold that none reaches alone (CR-02 R5)',
            S.unquantified('no loss is asserted: the finding is about an approval threshold, not an amount lost'), 'moderate',
            missing=['whether the orders are separate genuine requirements'], alternatives=['separate deliveries scheduled by the programme', 'a framework agreement'],
            hypotheses=['the orders may have been split to stay under an approval threshold (hypothesis, not a conclusion)'],
            limits=['grouping uses the configured keys and window; a chain of orders each inside the window of the next but spread wider than it can be missed (OQ-A1-7)'],
            impact_cents=total, owner_role='procurement_manager', extra={'aggregate_cents': total, 'orders': members, 'keys': params['keys'], 'window_days': params['window_days'], 'first_order_date': first}))
        run['signals'] += 1
    run['silent'] = run['evaluated'] - sum(len(c) for c in clusters.values())
    return sigs, run


def d01_held_cost_records(F, dp, project, as_of):
    rule, params, run = C.start(F, dp, 'D01')
    if rule is None:
        return [], run
    fig = costs.build_actual(F, project, as_of)
    if fig['state'] == 'cannot_assess':
        sig = S.make(rule, {'level': 'project', 'project': project}, 'actual_cost|cannot_assess', 'data_integrity', 'figure_cannot_be_assessed', 'data_quality_risk', [S.evidence('fin_policy/' + str(F.params.get('policy')), F.rev('fin_policy', F.params.get('policy')), 'policy')],
                     'the actual cost figure cannot be produced: ' + ', '.join(fig['reasons']), 'an actual cost figure for the project', 'a needed method or input is not configured, so detection that rests on actual cost cannot run',
                     S.unquantified('a missing figure is not a loss'), 'strong', limits=[LIMIT_SCOPE], owner_role='finance_reviewer')
        run['evaluated'] = 1
        run['signals'] = 1
        return [sig], run
    held = [e for e in fig['excluded'] if e['class'] in HELD]
    run['evaluated'] = len(fig['contributed']) + len(fig['excluded'])
    if not held:
        run['silent'] = 1
        return [], run
    by_class = {}
    cand = 0
    for e in held:
        by_class[e['class']] = by_class.get(e['class'], 0) + 1
        cand += e['amount_cents'] or 0
    kind_rev = lambda ref: F.rev(*ref.split('/', 1))
    ev = [S.evidence(e['ref'], kind_rev(e['ref']), 'held:' + e['class'], None, ','.join(e['codes'])) for e in held]
    sig = S.make(rule, {'level': 'project', 'project': project}, 'actual_cost|held_records', 'data_integrity', 'records_held_out_of_cost', 'data_quality_risk', ev,
                 f'{len(held)} stored record(s) are held out of the actual cost figure ({", ".join(f"{k}: {v}" for k, v in sorted(by_class.items()))})',
                 'every invoice and credit counted or excluded for a stated benign reason', 'a held record is neither counted nor ignored; the figure is provisional until a person resolves it',
                 S.unquantified('held records are a reporting risk, not a loss; their candidate amounts are listed in the detail', ), 'strong', limits=[LIMIT_SCOPE],
                 owner_role='finance_reviewer', extra={'by_class': dict(sorted(by_class.items())), 'candidate_amount_cents_known': cand, 'figure_state': fig['state']})
    run['signals'] = 1
    return [sig], run
