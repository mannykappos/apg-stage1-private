"""Buy now, wait, stage or negotiate.  Blueprint: Section 08 section 8 (for each scenario show landed cost, incremental costs, schedule implications, working-capital effects, uncertainty and evidence
gaps; do NOT apply a universal rule that prices will rise or fall; lowest-price scenarios are not automatically best), section 2 (procurement scenarios cannot silently alter the approved project
forecast), PG-MP-AC-09, 16.

Scenarios are PURE COMPUTATIONS over pinned records and policy values.  They write nothing, change no forecast, order nothing and recommend nothing; every record says so
(`changes_authoritative_forecast: False`, `status: scenario_only`, `human_approval_required: True`).

What a scenario may use:
  * today's quotes (their landed cost, validity and lead time)             - recorded
  * the policy's EXPLICIT price paths (a named change in basis points)     - assumptions a person set, not forecasts; with none configured, the wait scenario is NOT assessed
  * historical index movement                                              - shown beside the scenarios as history only; it feeds no calculation
Every cost that cannot be computed (no financing rate, no storage rate, no payment terms) is listed as an evidence gap instead of being counted as zero.

Quantity: the demand that no order covers yet (`coverage.uncovered_micro`).  Timing: buy now orders on the as-of day; wait orders on the latest day the lead time plus the policy's lead-time variation
allows; stage splits the quantity as the policy says.  Financing: the funded balance times the annual rate times the days the money is out before the material is needed, rounded once."""
from . import common as C, compare as CP, fresh as FR, landed as LD
from ..fin import fmath


def _financing(cents, bps_pa, days, basis):
    return fmath.carrying_cents(cents, bps_pa, days, basis) if days > 0 else 0


def _cash_out(terms, delivery_date):
    """-> (date of payment, deposit_bps or None, gaps)."""
    gaps = []
    pd = C.qty_micro(terms['payment_days']['value']) if 'payment_days' in terms else None
    if pd is None:
        gaps.append('payment terms are not recorded: payment is taken to fall on the delivery date' if 'payment_days' not in terms else
                    'payment terms %r cannot be read as a number of days: payment is taken to fall on the delivery date' % terms['payment_days']['value'])
        pay = delivery_date
    else:
        pay = C.add_days(delivery_date, pd // C.MICRO)
    dep = None
    if 'deposit_bps' in terms:
        d = C.qty_micro(terms['deposit_bps']['value'])
        dep = None if d is None else d // C.MICRO
        if dep is not None and not 0 <= dep <= 10000:
            gaps.append('the deposit %r basis points is outside 0 to 10000 (0%% to 100%%): no deposit is assumed' % terms['deposit_bps']['value'])
            dep = None
        elif d is None:
            gaps.append('the deposit %r cannot be read as basis points: no deposit is assumed' % terms['deposit_bps']['value'])
    return pay, dep, gaps


def _costs(ctx, o, qty, order_date, req, extra_orders=0, price_bps=0):
    """-> (landed_unit, landed_total, incrementals, schedule, working_capital, gaps) for buying `qty` from offer `o` on `order_date`."""
    sc = ctx.mp['scenarios']
    q = ctx.quotes[o['offer']['key']]
    plan = LD.purchase_plan(ctx.F, ctx.mp, q, ctx.as_of, qty)['plain']
    unit = fmath.round_div(plan['unit_cents'] * (10000 + price_bps), 10000) if price_bps else plan['unit_cents']
    total = C.mul_div(unit, plan['buy_qty_micro'], C.MICRO)
    gaps = [] if plan['complete'] else ['the landed cost is incomplete (missing: %s); the figures are a lower bound' % ', '.join(plan['landed']['missing'] or ['delivery basis'])]
    inc, sched, wc = [], {}, {}
    lead = q['lead']
    if lead is None:
        gaps.append('lead time is not stated: the delivery date cannot be computed')
        delivery = None
    else:
        delivery = C.add_days(order_date, lead)
    sched.update(order_date=order_date, delivery_date=delivery, required_date=req['required_date'], lead_time_days=lead)
    if delivery is not None:
        sched['days_before_required'] = C.days(delivery, req['required_date'])
        sched['meets_required_date'] = sched['days_before_required'] >= 0
    if q['valid_until'] < order_date:
        gaps.append('the quote %s lapses on %s, before the order date %s: a new quote is needed and the price is a modelled value, not an offer' % (q['key'], q['valid_until'], order_date))
        sched['quote_valid_on_order_date'] = False
    else:
        sched['quote_valid_on_order_date'] = True
    surplus = plan['buy_qty_micro'] - qty
    if surplus > 0:
        gaps.append('the minimum order or pack size means %s units more than needed are bought; surplus reuse is not assumed' % C.fmt_qty(surplus))
        sched['surplus_qty_micro'] = surplus
    if delivery is not None and sched['days_before_required'] > 0:
        if 'storage_cents_per_unit_per_day' in sc:
            st = C.mul_div(sc['storage_cents_per_unit_per_day'] * sched['days_before_required'], plan['buy_qty_micro'], C.MICRO)
            inc.append({'label': 'storage for %d days before the material is needed' % sched['days_before_required'], 'cents': st, 'basis': 'policy storage rate x days x quantity'})
        else:
            gaps.append('no storage rate is configured: storage cost is not assessed')
    if delivery is not None and 'financing_bps_pa' in sc and 'day_count_basis' in sc:
        pay, dep, g = _cash_out(LD.terms(ctx.F, q['key'])[0], delivery)
        gaps.extend(g)
        wc.update(cash_out_date=pay, days_paid_before_required=max(0, C.days(pay, req['required_date'])))
        fin = _financing(total, sc['financing_bps_pa'], wc['days_paid_before_required'], sc['day_count_basis'])
        if dep:
            dep_amt = C.mul_div(total, dep, 10000)
            early = max(0, C.days(order_date, req['required_date']))
            # the deposit leaves at order, the balance at payment: financing is on each part for its own days
            fin = _financing(dep_amt, sc['financing_bps_pa'], early, sc['day_count_basis']) + _financing(total - dep_amt, sc['financing_bps_pa'], wc['days_paid_before_required'], sc['day_count_basis'])
            wc['deposit_cents'] = dep_amt
        wc['funded_cents'] = total
        wc['financing_cents'] = fin
        if fin:
            inc.append({'label': 'financing the purchase for the days it is paid before it is needed', 'cents': fin, 'basis': 'funded balance x policy annual rate x days / day-count basis'})
    else:
        gaps.append('no financing rate or day-count basis is configured: the working-capital cost is not assessed')
    if extra_orders:
        if 'stage' in sc:
            inc.append({'label': 'extra delivery and administration for %d additional order(s)' % extra_orders, 'cents': extra_orders * (sc['stage']['extra_delivery_cents'] + sc['stage']['admin_cents_per_order']),
                        'basis': 'policy staging costs'})
    return unit, total, inc, sched, wc, gaps


def _scenario(name, o, qty, unit, total, inc, sched, wc, gaps, uncertainty, assumptions=(), extra=None):
    d = {'scenario': name, 'offer': o['offer']['ref'], 'supplier': o['offer']['supplier'], 'quantity_micro': qty, 'landed_unit_cents': unit, 'landed_total_cents': total,
         'incremental_costs': inc, 'incremental_total_cents': sum(i['cents'] for i in inc), 'total_cost_cents': total + sum(i['cents'] for i in inc), 'schedule': sched, 'working_capital': wc,
         'uncertainty': list(uncertainty), 'evidence_gaps': sorted(set(gaps)), 'assumptions': sorted(assumptions), 'status': 'scenario_only', 'changes_authoritative_forecast': False,
         'human_approval_required': True}
    d.update(extra or {})
    return d


def market_context(ctx, material):
    """History of the index over the policy's number of points, beside the scenarios and feeding none of them."""
    sc = ctx.mp['scenarios']
    n = sc.get('context_points')
    th = ctx.mp['freshness']['buy_timing']
    st = FR.index_state(ctx.F, material, ctx.as_of, th)
    if n is None:
        return {'status': 'not_configured', 'why': 'scenarios.context_points is not configured', 'freshness': st['state']}
    pts = []
    for key in C.keys_of(ctx.F, 'market_observation'):
        v = C.simple_view(ctx.F, 'market_observation', key, ('material_ref', 'obs_date', 'value_scaled'))
        if v is None or not v['ok'] or v['f']['material_ref'] != material or v['f']['obs_date'] > ctx.as_of:
            continue
        pts.append((v['f']['obs_date'], v['f']['value_scaled'], v['ref'], v['rev'], v['f'].get('kind_text'), v['f'].get('unit_text'), v['f'].get('source_label_text'), v['f'].get('geography_text')))
    pts.sort()
    pts = pts[-n:]
    if len(pts) < n:
        return {'status': 'insufficient_history', 'why': '%d usable observations, %d wanted' % (len(pts), n), 'freshness': st['state'], 'observations': [p[2] for p in pts]}
    first, last = pts[0], pts[-1]
    change = fmath.bps_of(last[1] - first[1], first[1]) if first[1] > 0 else None
    return {'status': 'history', 'material': material, 'points': n, 'from': first[0], 'to': last[0], 'first_value': first[1], 'last_value': last[1], 'change_bps': change,
            'direction': 'up' if last[1] > first[1] else ('down' if last[1] < first[1] else 'flat'), 'kind': last[4], 'unit': last[5], 'source': last[6], 'geography': last[7], 'freshness': st['state'],
            'observations': [p[2] for p in pts], 'note': 'history of an index, not a price; it does not predict future prices and feeds no scenario below'}


def timing(ctx, req, offer):
    """-> the dates that bind one offer for a demand: the quote's last valid day, and the latest day to order that still meets the required date after the quoted lead time plus the policy's
    allowance for variation.  `due` is the earlier of the two (None parts are listed, never guessed)."""
    sc = ctx.mp['scenarios']
    q = ctx.quotes[offer['offer']['key']]
    lead, var = q['lead'], sc.get('lead_time_variation_days')
    latest = C.add_days(req['required_date'], -(lead + var)) if lead is not None and var is not None else None
    cands = [(q['valid_until'], 'quote validity')] + ([(latest, 'lead time')] if latest else [])
    due, binding = min(cands)
    return {'offer': offer['offer']['ref'], 'valid_until': q['valid_until'], 'lead_time_days': lead, 'latest_order_date': latest, 'due': due, 'binding': binding,
            'unknown': [] if latest else ['lead time is not stated' if lead is None else 'scenarios.lead_time_variation_days is not configured']}


def _for_offer(ctx, req, o, need, paths, sc):
    """The buy-now, wait (one record per configured price path) and stage scenarios for ONE offer.  Each record carries the offer's class and blockers so it cannot be read without them."""
    tag = {'offer_class': o['gate']['class'], 'offer_qualification': o['qualification'], 'offer_blockers': o['blockers']}
    out = []
    unit, total, inc, sched, wc, gaps = _costs(ctx, o, need, ctx.as_of, req)
    out.append(_scenario('buy_now', o, need, unit, total, inc, sched, wc, gaps,
                         ['the price is as quoted; the quote is an offer, not a commitment', 'an early purchase carries storage, financing and obsolescence risk that is only partly costed'],
                         ['order placed on the as-of day', 'quote accepted at the quoted rate'], tag))
    tm = timing(ctx, req, o)
    if tm['latest_order_date'] is None:
        out.append(dict({'scenario': 'wait', 'offer': o['offer']['ref'], 'status': 'cannot_assess', 'why': tm['unknown'][0], 'changes_authoritative_forecast': False, 'human_approval_required': True}, **tag))
    elif tm['latest_order_date'] < ctx.as_of:
        out.append(dict({'scenario': 'wait', 'offer': o['offer']['ref'], 'status': 'not_available',
                         'why': 'the latest order date that still meets %s with a lead time of %d days and %d days of variation was %s, before the as-of day' % (
                             req['required_date'], tm['lead_time_days'], sc['lead_time_variation_days'], tm['latest_order_date']),
                         'changes_authoritative_forecast': False, 'human_approval_required': True}, **tag))
    elif not paths:
        out.append(dict({'scenario': 'wait', 'offer': o['offer']['ref'], 'status': 'cannot_assess', 'latest_order_date': tm['latest_order_date'],
                         'why': 'no explicit future-price paths are configured (scenarios.price_paths); APG applies no rule that prices rise or fall',
                         'changes_authoritative_forecast': False, 'human_approval_required': True}, **tag))
    else:
        latest = tm['latest_order_date']
        for pth in paths:
            unit_w, total_w, inc_w, sched_w, wc_w, gaps_w = _costs(ctx, o, need, latest, req, 0, pth['change_bps'])
            wait_days = C.days(ctx.as_of, latest)
            unc = ['price path %r (%+d basis points) is an assumption a person configured, not a forecast' % (pth['name'], pth['change_bps'])]
            if pth['horizon_days'] < wait_days:
                unc.append('the path covers %d days but the wait is %d days: no further movement is assumed after the horizon' % (pth['horizon_days'], wait_days))
            extra = dict(tag, price_path=pth, wait_days=wait_days)
            out.append(_scenario('wait:' + pth['name'], o, need, unit_w, total_w, inc_w, sched_w, wc_w, [g for g in gaps_w],
                                 unc + ['availability and the lead time at the later date are not known; the policy allows %d days of variation' % sc['lead_time_variation_days']],
                                 ['order placed on the latest day that still meets the required date: %s' % latest], extra))
    stg = sc.get('stage')
    if stg is None:
        out.append(dict({'scenario': 'stage', 'offer': o['offer']['ref'], 'status': 'cannot_assess', 'why': 'scenarios.stage is not configured', 'changes_authoritative_forecast': False,
                         'human_approval_required': True}, **tag))
    else:
        parts, rem = [], need
        for i, bps in enumerate(stg['splits_bps']):
            qi = rem if i == len(stg['splits_bps']) - 1 else C.mul_div(need, bps, 10000)
            parts.append(qi)
            rem -= qi
        tr, tot_total, tot_inc, gaps_s = [], 0, [], []
        for i, (qi, off) in enumerate(zip(parts, stg['offsets_days'])):
            order_date = C.add_days(ctx.as_of, off)
            u, t, inc_i, sch_i, wc_i, g_i = _costs(ctx, o, qi, order_date, req, 0)
            tr.append({'tranche': i + 1, 'quantity_micro': qi, 'order_date': order_date, 'landed_unit_cents': u, 'landed_total_cents': t, 'incremental_total_cents': sum(x['cents'] for x in inc_i),
                       'schedule': sch_i, 'working_capital': wc_i, 'evidence_gaps': sorted(set(g_i))})
            tot_total += t
            tot_inc.extend(inc_i)
            gaps_s.extend(g_i)
        extra_n = len(parts) - 1
        tot_inc.append({'label': 'extra delivery and administration for %d additional order(s)' % extra_n, 'cents': extra_n * (stg['extra_delivery_cents'] + stg['admin_cents_per_order']), 'basis': 'policy staging costs'})
        sched_s = {'order_dates': [t['order_date'] for t in tr], 'meets_required_date': all(t['schedule'].get('meets_required_date', False) for t in tr), 'required_date': req['required_date']}
        out.append(_scenario('stage', o, need, None, tot_total, tot_inc, sched_s, {'financing_cents': sum(t['working_capital'].get('financing_cents', 0) for t in tr)}, gaps_s,
                             ['later tranches are priced at today\'s quote: a later price movement or a lapsed quote is not modelled here (see the wait scenario for explicit paths)',
                              'split-delivery freight, storage and handling economics beyond the policy staging costs are not known'], ['tranches as the policy splits them'], dict(tag, tranches=tr)))
    return out


def build(ctx, req, cov):
    """-> scenario analysis for a demand requirement with its coverage record.  Scenarios are built for EVERY rankable offer: APG does not pick a winner to model (a ranking that is only
    indicative, or an offer with an incomplete landed cost, is shown with its own scenarios and its own caveats)."""
    mp, sc = ctx.mp, ctx.mp['scenarios']
    base = {'requirement': req['id'], 'project': req['project'], 'material': req['material'], 'required_date': req['required_date'], 'as_of': ctx.as_of, 'human_approval_required': True,
            'changes_authoritative_forecast': False, 'context': market_context(ctx, req['material'])}
    if cov.get('status') == 'cannot_assess':
        return dict(base, status='cannot_assess', why=cov['why'], scenarios=[])
    need = cov['uncovered_micro']
    if need <= 0:
        return dict(base, status='no_uncovered_demand', scenarios=[], quantity_micro=0)
    rk = CP.rank(ctx, req, 'buy_timing', need, with_index=True)
    base.update(quantity_micro=need, ranking_status=rk['status'], ranking=rk['ranking'], outstanding=rk['outstanding'], excluded=rk['excluded'])
    if not rk['ranking']:
        return dict(base, status='no_rankable_offer', scenarios=[])
    paths = sc.get('price_paths')
    out, timings, skipped = [], [], []
    for r in rk['ranking']:
        o = next(x for x in rk['offers'] if x['offer']['ref'] == r['offer'])
        if o['landed'].get('unit_conversion'):
            skipped.append({'offer': r['offer'], 'why': 'priced per %s but needed per %s: tiers, minimum orders and pack sizes are in the quoted unit, so no purchase scenario is built' % (
                o['landed']['unit_conversion']['from_unit'], o['landed']['unit_conversion']['to_unit'])})
            continue
        out.extend(_for_offer(ctx, req, o, need, paths, sc))
        timings.append(timing(ctx, req, o))
    if not out:
        return dict(base, status='no_scenario_built', scenarios=[], timings=[], scenarios_not_built=skipped)
    # ---- negotiate / alternatives: only between offers whose landed cost is complete, so a lower bound is never compared as if it were a cost
    full = [r for r in rk['ranking'] if r['complete']]
    if len(full) < 2:
        out.append({'scenario': 'negotiate', 'status': 'cannot_assess', 'changes_authoritative_forecast': False, 'human_approval_required': True,
                    'why': 'fewer than two rankable offers have a complete landed cost, so there is nothing to compare or to negotiate against'})
    else:
        low = full[0]
        others = [{'offer': r['offer'], 'class': r['class'], 'landed_gap_cents_per_unit': r['unit_cents'] - low['unit_cents'], 'potential_difference_cents': C.mul_div(r['unit_cents'] - low['unit_cents'], need, C.MICRO)}
                  for r in full[1:]]
        out.append({'scenario': 'negotiate', 'status': 'scenario_only', 'lowest_complete_offer': low['offer'], 'lowest_class': low['class'], 'ranking_status': rk['status'], 'others': others,
                    'uncertainty': ['an estimate of what matching the lowest offer or using an alternative supplier might change, not a saving: no baseline is verified (Section 05)',
                                    'supplier qualification, approval and switching costs are not in the data'],
                    'evidence_gaps': ['qualification and switching cost are not recorded'] + ([] if rk['status'] == 'definitive' else ['the comparison is %s: %s' % (rk['status'], '; '.join(rk['outstanding'][:3]))]),
                    'changes_authoritative_forecast': False, 'human_approval_required': True})
    return dict(base, status='scenarios', scenarios=out, timings=timings, scenarios_not_built=skipped,
                note='scenarios are not recommendations and no offer is chosen; the lowest total is not automatically best (schedule, uncertainty, class and evidence gaps are shown with each)')
