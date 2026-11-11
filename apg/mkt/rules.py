"""The M6 procurement rules.  Blueprint: Section 08 (all), Section 06 sections 5.1 (deterministic first), 6, 7, 8 (amounts are figures, records or labelled estimates; severity, urgency and confidence kept
apart), 10 (a rule that cannot run says so).  Each rule is a pure function of the analysis (pinned records, policy, register, as-of day) and returns (signals, run) in the form the M5 findings
lifecycle already accepts, so a procurement signal becomes a finding with the same identity, history, human-only transitions and noise control as any other.

MP01  market evidence stale, expired or unavailable for a watched material or one with demand
MP02  a cheaper-looking quote that fails the comparability gate (or can only be indicative): not to be ranked on price
MP03  purchase decision due: uncovered demand, a current quote, and the date the quote or the lead time runs out; the scenarios are in the stored analysis
MP04  ordered or delivered above the demand
MP05  possible duplicate order
MP06  international quote priced at an old or diverging FX rate
MP07  international quote with unresolved critical import or compliance checks (blocks a definitive recommendation)
MP08  supplier performance below a configured level on a sufficient sample
MP09  saving opportunity from a comparable current quote (an estimate; never realised)
MP10  portfolio purchasing: one material bought at different rates by several authorised projects
MPD1  held procurement records that no rule could use

No rule recommends a purchase, a supplier or a substitution, and none declares a product compliant.  Every signal carries event records (observation time, effective period, sources, identifiers) for the
later cross-domain engine; M6 draws no conclusions from them."""
from . import common as C, events as EV, fresh as FR, landed as LD, policy as MP, spec as SP
from ..det import signal as S
from ..fin.intake import usable

PROJECT_RULE_IDS = ('MP02', 'MP03', 'MP04', 'MP05', 'MP09', 'MPD1')
TENANT_RULE_IDS = ('MP01', 'MP06', 'MP07', 'MP08', 'MP10', 'MPD1')


def _scope(project):
    return {'level': 'project', 'project': project} if project else {'level': 'tenant', 'project': None}


def rule(rid):
    def deco(fn):
        def wrapped(A, F, mp, as_of, project):
            rl, params, run = C.start(F, mp, rid)
            if rl is None:
                return [], run
            try:
                sigs = fn(A, rl, run, project, as_of)
            except C.MissingParam as e:
                run2 = C.new_run(rid)
                run2['status'] = 'not_configured'
                run2['missing_parameters'] = [str(e)]
                run2['decision'] = MP.RULES[rid][2]
                return [], run2
            run['signals'] = len(sigs)
            return sigs, run
        wrapped.rule_id = rid
        wrapped.__name__ = fn.__name__
        return wrapped
    return deco


def ev(ref, rev, role='source', recon=None, note=''):
    return S.evidence(ref, rev, role, recon, note)


def offer_evidence(o):
    out = [ev(s[0], s[1], 'quote' if s[0].startswith('supplier_quote/') else 'quote_detail') for s in o['landed']['sources']]
    cv = o['landed'].get('conversion')
    if cv and cv.get('rate_source_ref'):
        out.append(ev(cv['rate_source_ref'], cv['rate_revision'], 'fx_rate'))
    out.extend(ev(r[1], r[2], 'reading') for r in o['readings_used'])
    if o.get('international'):
        out.extend(ev(c['ref'], c['revision'], 'import_check') for c in o['international']['checks'] if c['ref'])
    return out


def _dedupe(evs):
    seen, out = set(), []
    for e in evs:
        k = (e['ref'], e['revision'], e['role'])
        if k not in seen:
            seen.add(k)
            out.append(e)
    return out


def event(etype, subject, obs, eff_from, sources, as_of, **kw):
    return EV.make(etype, subject, obs or (as_of + 'T00:00:00Z'), eff_from, sources, **kw)


# ------------------------------------------------------------------------------------------------------------------------------------ MP01
@rule('MP01')
def mp01_stale_market(A, rl, run, project, as_of):
    F, mp = A.F, A.mp
    th = mp['freshness']['benchmark']
    sigs = []
    reg = A.evidence_register()
    pol_ref = '%s/%s' % (MP.POLICY_KIND, F.params['mkt_policy'])
    for m in A.watched_materials():
        run['evaluated'] += 1
        qs, idx = reg[m]['quotes'], reg[m]['index']
        if qs and not any(q['state'] == FR.QUOTE_OK for q in qs):
            evs = [ev(q['subject'], F.rev(*q['subject'].split('/', 1)), 'quote') for q in qs]
            events = []
            for q in qs:
                qv = A.ctx.quotes[q['subject'].split('/', 1)[1]]
                events.append(event('quote_expires', q['subject'], qv['received'], qv['issue'], [(q['subject'], qv['rev'])], as_of, effective_to=qv['valid_until'], material=m, supplier=qv['supplier'],
                                    detail={'state': q['state']}))
            sigs.append(S.make(
                rl, _scope(None), '%s|quote' % m, 'procurement_materials', 'quote_evidence_not_current', 'data_quality_risk', evs,
                'no quote for %s is current as of %s: %s' % (m, as_of, '; '.join('%s is %s' % (q['subject'].split('/')[1], q['state']) for q in qs)),
                'at least one valid quote for %s no older than %d days' % (m, th['quote_max_age_days']),
                'expired or stale quotes stay as history but cannot support an unqualified current recommendation (Section 08 14)',
                S.unquantified('a missing current quote has no amount until a purchase depends on it'), 'strong', missing=['a current quote'], alternatives=['a newer quote exists outside the imported data'],
                limits=['decision: benchmark; quote age at most %d days' % th['quote_max_age_days']] + FR.limitations(qs), urgency={'time_sensitive': False, 'date': None, 'basis': ','.join(sorted({q['state'] for q in qs}))},
                owner_role='procurement_manager', extra={'material': m, 'states': qs, 'events': events}))
        if idx['state'] in ('stale', 'unavailable'):
            ob = idx['observation']
            if ob is None:
                evs = [ev(pol_ref, F.rev(MP.POLICY_KIND, F.params['mkt_policy']), 'policy')]
                observed, events = 'no usable market observation exists for %s on or before %s' % (m, as_of), []
            else:
                evs = [ev(ob['ref'], ob['revision'], 'market_observation')]
                observed = 'the latest %s observation for %s is dated %s, %d days before %s (%s, %s)' % (ob['kind'] or 'market', m, ob['date'], idx['age_days'], as_of, ob['source_label'] or 'source not named', ob['geography'] or 'geography not stated')
                events = [event('market_observed', ob['ref'], ob['retrieved_at'], ob['date'], [(ob['ref'], ob['revision'])], as_of, material=m, detail={'state': idx['state'], 'kind': ob['kind']})]
            sigs.append(S.make(
                rl, _scope(None), '%s|index' % m, 'procurement_materials', 'market_series_' + idx['state'], 'data_quality_risk', evs, observed,
                'an observation no older than %d days for a market-dependent analysis' % th['index_max_age_days'],
                'a stale or missing series must not imply current market visibility, so market-dependent analysis for %s is qualified' % m,
                S.unquantified('stale market data has no amount; it limits what a recommendation may claim'), 'strong', missing=['a current observation'], alternatives=['a newer observation exists outside the imported data'],
                limits=['decision: benchmark; observation age at most %d days' % th['index_max_age_days'], 'an index is a movement series, not a price'], urgency={'time_sensitive': False, 'date': None, 'basis': idx['state']},
                owner_role='procurement_manager', extra={'material': m, 'age_days': idx['age_days'], 'threshold_days': idx['threshold_days'], 'observation': ob, 'events': events}))
    return sigs


# ------------------------------------------------------------------------------------------------------------------------------------ MP02
@rule('MP02')
def mp02_not_comparable(A, rl, run, project, as_of):
    sigs = []
    for req in A.requirements():
        ref = A.last_paid(req)
        rk = A.ranking(req, 'quote_ranking')
        if not rk['offers']:
            continue
        best_ok = next((r for r in rk['ranking'] if r['class'] in SP.DEFINITIVE_OK), None)            # the only fair yardstick without a reference order is a like-for-like offer
        best_unit = best_ok['unit_cents'] if best_ok else None
        for o in rk['offers']:
            run['evaluated'] += 1
            cls = o['gate']['class']
            if cls in SP.DEFINITIVE_OK or o['qualification'] == 'historical_only':
                run['silent'] += 1
                continue
            unit = o['landed']['unit_cents']
            base, base_what = (ref['landed']['unit_cents'], 'the last rate paid (%s, %s)' % (ref['offer']['ref'], ref['offer']['order_date'])) if ref else (best_unit, 'the cheapest like-for-like offer') if best_unit else (None, '')
            if unit <= 0 or base is None or unit >= base:
                run['silent'] += 1
                continue
            gap = base - unit
            q = A.ctx.quotes[o['offer']['key']]
            evs = offer_evidence(o) + [ev(s[0], s[1], 'requirement') for s in req['sources']]
            if ref:
                evs.append(ev(ref['offer']['ref'], ref['offer']['revision'], 'reference'))
            sigs.append(S.make(
                rl, _scope(req['project']), '%s>%s' % (req['id'], o['offer']['key']), 'procurement_materials', 'cheaper_quote_%s' % cls, 'operational_risk', _dedupe(evs),
                '%s (%s, %s) is %s per unit against %s at %s, but it is %s for %s: %s' % (o['offer']['ref'], o['offer']['supplier'], o['offer']['specification_text'] or 'no specification text', ('at least ' if not o['landed']['complete'] else '') + C.money(unit),
                                                                                         base_what, C.money(base), cls.replace('_', ' '), req['material'], '; '.join(o['gate']['reasons'][:3]) or 'see the gate record'),
                'a quote that meets the specification and commercial basis before its price is compared', 'a cheaper substitute must not be recommended on price while specification, approval or basis questions are open (Section 08 4.1)',
                S.unquantified('the apparent difference of %s%s per unit is not a saving: the offers are not like-for-like' % ('up to ' if not o['landed']['complete'] else '', C.money(gap))),
                'strong' if cls == 'not_comparable' else 'moderate', missing=['a verified reading of the quote text', 'approval of any substitution'] if cls != 'not_comparable' else ['approval of any substitution'],
                alternatives=['the quote is for a different product the project could use if the design is changed and approved'],
                limits=['gate class: ' + cls] + o['gate']['reasons'][:4] + o['limitations'], urgency={'time_sensitive': True, 'date': q['valid_until'], 'basis': 'quote validity'}, owner_role='procurement_manager',
                extra={'requirement': req['id'], 'class': cls, 'codes': o['gate']['codes'], 'apparent_unit_difference_cents': gap, 'unit_cents': unit, 'baseline_unit_cents': base,
                       'events': [event('quote_issued', o['offer']['ref'], o['offer']['observed_at'], o['offer']['issue_date'], [(o['offer']['ref'], o['offer']['revision'])], as_of, effective_to=o['offer']['valid_until'],
                                        project=req['project'], material=o['offer']['material'], supplier=o['offer']['supplier'], detail={'class': cls})]}))
    return sigs


# ------------------------------------------------------------------------------------------------------------------------------------ MP03
@rule('MP03')
def mp03_decision_due(A, rl, run, project, as_of):
    sc = A.mp['scenarios']
    window = sc['decision_window_days']
    sigs = []
    for req in A.demands():
        run['evaluated'] += 1
        cov = A.coverage(req)
        if cov['status'] == 'cannot_assess':
            run['not_assessed'].append({'subject': req['id'], 'why': cov['why']})
            continue
        if cov['uncovered_micro'] <= 0:
            run['silent'] += 1
            continue
        scn = A.scenarios(req)
        if scn['status'] != 'scenarios':
            left = C.days(as_of, req['required_date'])
            if left > window:
                run['not_assessed'].append({'subject': req['id'], 'why': 'uncovered demand but no rankable current quote (%s); the required date is %d days away' % (scn['status'], left)})
                continue
            evs = [ev(s[0], s[1], 'requirement') for s in req['sources']] + [ev(o['ref'], o['revision'], 'order') for o in cov['orders']]
            sigs.append(S.make(
                rl, _scope(req['project']), req['id'], 'procurement_materials', 'uncovered_demand_without_quote', 'operational_risk', _dedupe(evs),
                '%s %s of %s are needed on site by %s and no order covers them; no current, rankable quote exists (%s)' % (C.fmt_qty(cov['uncovered_micro']), req['unit'] or 'units', req['material'], req['required_date'], scn['status']),
                'uncovered demand with a current comparable quote well before the required date', 'the required date is within the decision window of %d days' % window,
                S.unquantified('no quote exists to cost the purchase'), 'moderate', missing=['a current quote'], limits=cov.get('notes', []) + [cov['matching_rule']],
                urgency={'time_sensitive': True, 'date': req['required_date'], 'basis': 'required on site'}, owner_role='procurement_manager',
                extra={'requirement': req['id'], 'uncovered_micro': cov['uncovered_micro'], 'events': [event('demand_required', req['id'], req['observed_at'], req['required_date'], req['sources'], as_of, project=req['project'], material=req['material'])]}))
            continue
        cls = {r['offer']: r['class'] for r in scn['ranking']}
        tms = scn['timings']
        definitive = [t for t in tms if cls[t['offer']] in SP.DEFINITIVE_OK]
        pool = definitive or tms
        due = min(t['due'] for t in pool)
        last_due = max(t['due'] for t in pool)
        left = C.days(as_of, due)
        if left > window:
            run['silent'] += 1
            continue
        names = sorted({x['scenario'].split(':')[0] for x in scn['scenarios'] if x.get('status') == 'scenario_only'})
        gaps_n = sum(len(x.get('evidence_gaps', [])) for x in scn['scenarios'])
        ctxm = scn['context']
        hist = ('index history, shown as history only: %s %+d basis points between %s and %s (%s)' % (ctxm['material'], ctxm['change_bps'], ctxm['from'], ctxm['to'], ctxm['freshness'])) if ctxm['status'] == 'history' and ctxm['change_bps'] is not None else 'no index history is available'
        evs = [ev(s[0], s[1], 'requirement') for s in req['sources']] + [ev(o['ref'], o['revision'], 'order') for o in cov['orders']]
        rk = A.ranking(req, 'buy_timing', cov['uncovered_micro'], True)
        for o in rk['offers']:
            if o['offer']['ref'] in cls:
                evs += offer_evidence(o)
        offers_text = '; '.join('%s (%s%s) valid to %s%s' % (t['offer'].split('/', 1)[1], cls[t['offer']].replace('_', ' '), '' if t['unknown'] == [] else ', lead time unknown', t['valid_until'],
                                                         (', latest order date %s' % t['latest_order_date']) if t['latest_order_date'] else '') for t in tms)
        basis = 'the earliest date on which a comparable offer lapses or can no longer arrive in time' if definitive else 'the earliest date on which any current offer lapses (no offer is comparable on a definitive basis)'
        events = [event('decision_deadline', req['id'], req['observed_at'], due, [tuple(s) for s in req['sources']] + [(t['offer'], A.ctx.quotes[t['offer'].split('/', 1)[1]]['rev']) for t in pool], as_of,
                        project=req['project'], material=req['material'], detail={'required_date': req['required_date'], 'basis': basis, 'last_due': last_due}),
                 event('demand_required', req['id'], req['observed_at'], req['required_date'], req['sources'], as_of, project=req['project'], material=req['material'])]
        sigs.append(S.make(
            rl, _scope(req['project']), req['id'], 'procurement_materials', 'purchase_decision_due', 'operational_risk', _dedupe(evs),
            '%s %s of %s are uncovered for %s (required %s); current offers: %s; %s is %s, %d days after %s' % (
                C.fmt_qty(cov['uncovered_micro']), req['unit'] or 'units', req['material'], req['project'], req['required_date'], offers_text, basis, due, left, as_of),
            'a purchase decision made before the offers lapse or the lead time runs out', 'scenarios for buy now, wait, stage and negotiate are in the stored analysis for every rankable offer (%s); %s. APG applies no rule that prices rise or fall and chooses no offer' % (', '.join(names) or 'none computable', hist),
            S.unquantified('scenario outcomes depend on explicit assumptions and are not a forecast; see the scenario records'), 'moderate',
            missing=['payment terms' if any('payment terms' in g for x in scn['scenarios'] for g in x.get('evidence_gaps', [])) else 'confirmation of stock and lead time from the supplier'],
            alternatives=['the demand is already covered by stock or orders outside the imported data'], limits=[cov['matching_rule'], 'ranking is ' + scn['ranking_status']] + scn.get('outstanding', [])[:3],
            urgency={'time_sensitive': True, 'date': due, 'basis': basis}, owner_role='procurement_manager',
            extra={'requirement': req['id'], 'uncovered_micro': cov['uncovered_micro'], 'offers': [t['offer'] for t in tms], 'due_date': due, 'last_due_date': last_due, 'days_left': left, 'evidence_gap_count': gaps_n,
                   'events': events}))
    return sigs


# ------------------------------------------------------------------------------------------------------------------------------------ MP04
@rule('MP04')
def mp04_over_order(A, rl, run, project, as_of):
    sigs = []
    for req in A.demands():
        run['evaluated'] += 1
        cov = A.coverage(req)
        if cov['status'] == 'cannot_assess':
            run['not_assessed'].append({'subject': req['id'], 'why': cov['why']})
            continue
        if cov['status'] != 'over_ordered':
            run['silent'] += 1
            continue
        orders = cov['orders']
        suspected = [o for o in orders if not o['confirmed']]
        surplus = cov['surplus_if_all_genuine_micro']
        rate = max(orders, key=lambda o: (o['date'], o['ref']))['rate_cents']
        evs = [ev(s[0], s[1], 'requirement') for s in req['sources']] + [ev(o['ref'], o['revision'], 'order') for o in orders] + [ev(d['docket'], d['revision'], 'delivery') for d in cov['dockets']]
        delivered_note = ('; dockets record %s accepted' % C.fmt_qty(cov['accepted_delivered_micro'])) if cov['dockets'] else '; no delivery docket is recorded'
        quant = S.quantified(C.mul_div(surplus, rate, C.MICRO), 'surplus quantity valued at the latest order rate', 'mkt.coverage@%s:%s' % (as_of, req['id']),
                             ['all matched orders are genuine' if suspected else 'the matched orders stand', 'surplus valued at the latest order rate %s per unit' % C.money(rate),
                              'surplus stock may be reusable on this or another project: this is exposure, not a loss'], label='estimate') if surplus > 0 and rate is not None else \
            S.unquantified('the surplus is delivered but no order rate is available to value it')
        sigs.append(S.make(
            rl, _scope(req['project']), req['id'], 'procurement_materials', 'ordered_above_demand', 'forecast_exposure', _dedupe(evs),
            '%s %s of %s are required by %s; %s ordered%s%s' % (C.fmt_qty(cov['required_micro']), req['unit'] or 'units', req['material'], req['required_date'],
                                                                 ('%s are confirmed and %s in all if the %d suspected order(s) are genuine' % (C.fmt_qty(cov['ordered_confirmed_micro']), C.fmt_qty(cov['ordered_if_all_genuine_micro']), len(suspected))) if suspected else C.fmt_qty(cov['ordered_confirmed_micro']),
                                                                 ', a surplus of %s' % C.fmt_qty(surplus) if surplus else '', delivered_note),
            'ordered quantity within %s of the demand' % C.pct(cov['tolerance_bps']), 'orders exceed the demand by more than the tolerance; a variance is not automatically waste',
            quant, 'strong' if not suspected else 'moderate',
            missing=['installed, returned and held quantities (the data holds none)', 'any approved allowance or phased delivery for this demand'],
            alternatives=['a legitimate waste allowance or phased delivery', 'the demand record is incomplete or superseded', 'the surplus is reused on another project'],
            limits=[cov['matching_rule'], cov['inventory_note']] + cov['notes'], urgency={'time_sensitive': bool(suspected), 'date': None, 'basis': 'unreturned surplus'}, impact_cents=quant['gross_cents'] if quant['status'] == 'quantified' else None,
            overlap_group='over_order|%s|%s' % (req['project'], req['material']), owner_role='procurement_manager',
            extra={'requirement': req['id'], 'surplus_micro': surplus, 'ordered_confirmed_micro': cov['ordered_confirmed_micro'], 'accepted_delivered_micro': cov['accepted_delivered_micro'], 'suspected_orders': [o['ref'] for o in suspected],
                   'events': [event('surplus_ordered', req['id'], max(o['observed_at'] for o in orders), req['required_date'], req['sources'] + [(o['ref'], o['revision']) for o in orders], as_of,
                                    project=req['project'], material=req['material'], detail={'surplus_micro': surplus})]}))
    return sigs


# ------------------------------------------------------------------------------------------------------------------------------------ MP05
@rule('MP05')
def mp05_duplicate_order(A, rl, run, project, as_of):
    sigs = []
    for g in A.duplicates():
        run['evaluated'] += 1
        if project and g['project'] != project:
            continue
        orders = g['orders']
        first, rest = orders[0], orders[1:]
        extra_amount = sum(o['amount_cents'] for o in rest if o['amount_cents'] is not None)
        known = all(o['amount_cents'] is not None for o in rest)
        evs = [ev(o['ref'], o['revision'], 'order') for o in orders]
        quant = S.quantified(extra_amount, 'amount of the later order(s) on the order records', 'mkt.duplicates@%s' % as_of, ['the later order(s) are duplicates of the first: only suspected from identical details'], label='record') if known and extra_amount > 0 \
            else S.unquantified('an order amount is missing')
        subject = '|'.join(o['ref'].split('/', 1)[1] for o in orders)
        sigs.append(S.make(
            rl, _scope(g['project']), subject, 'procurement_materials', 'possible_duplicate_order', 'forecast_exposure', evs,
            '%d orders for %s %s of %s at %s per unit from %s have identical details and were placed %s' % (len(orders), C.fmt_qty(g['qty_micro']), 'units', g['material'], C.money(g['rate_cents']), g['supplier'],
                                                                                                          'on the same day (%s)' % first['date'] if g['span_days'] == 0 else 'within %d days (%s to %s)' % (g['span_days'], first['date'], orders[-1]['date'])),
            'distinct orders differ in quantity, rate, supplier or date', 'identical orders placed together are a common sign of a duplicate; two real orders are also possible',
            quant, 'moderate' if g['held_as_candidates'] else 'weak', missing=['the supplier\'s confirmation of how many orders it holds', 'whether the project needed both quantities'],
            alternatives=['two deliberate orders for two deliveries', 'a system re-send that created a second record'], limits=['identical details are a suspicion, not proof'] + (['reconciliation holds these orders as duplicate candidates'] if g['held_as_candidates'] else []),
            urgency={'time_sensitive': True, 'date': None, 'basis': 'before the second order is delivered or paid'}, impact_cents=extra_amount if known and extra_amount > 0 else None,
            overlap_group='over_order|%s|%s' % (g['project'], g['material']), owner_role='procurement_manager',
            extra={'orders': [o['ref'] for o in orders], 'events': [event('duplicate_suspected', 'purchase_order/' + subject, None, first['date'], [(o['ref'], o['revision']) for o in orders], as_of, project=g['project'], material=g['material'], supplier=g['supplier'])]}))
        run['signals'] += 0
    return sigs


# ------------------------------------------------------------------------------------------------------------------------------------ MP06
def _intl_quotes(A):
    """Usable, not-expired quotes that are international under the policy."""
    out = []
    for k, q in sorted(A.ctx.quotes.items()):
        if q['ok'] and LD.is_international(A.mp, q) and q['valid_until'] >= A.as_of:
            out.append(q)
    return out


@rule('MP06')
def mp06_fx(A, rl, run, project, as_of):
    F, mp = A.F, A.mp
    th = mp['freshness']['import_costing']
    tol = mp['fx']['divergence_tolerance_bps']
    from . import fx as FX
    sigs = []
    for q in _intl_quotes(A):
        run['evaluated'] += 1
        if q['cur'] == mp['basis']['home_currency']:
            run['silent'] += 1
            continue
        ref_conv = FX.convert(F, mp, q['rate'], q['cur'], as_of)
        stated = FX.convert_stated(q['rate'], q['cur'], mp['basis']['home_currency'], q['fx_used'], q['fx_date'], as_of)
        reasons, evs = [], [ev(q['ref'], q['rev'], 'quote')]
        if ref_conv['status'] != 'converted':
            reasons.append('no usable reference rate: ' + ref_conv['why'])
        else:
            evs.append(ev(ref_conv['rate_source_ref'], ref_conv['rate_revision'], 'fx_rate'))
            if ref_conv['rate_age_days'] > th['fx_max_age_days']:
                reasons.append('the latest reference rate (%s) is %d days old against a limit of %d days' % (ref_conv['rate_date'], ref_conv['rate_age_days'], th['fx_max_age_days']))
        if stated['status'] != 'converted':
            reasons.append('the quote states no usable FX rate, so its own conversion cannot be reproduced')
        elif stated['rate_age_days'] is None or stated['rate_age_days'] > th['fx_max_age_days']:
            reasons.append('the rate stated on the quote (%s) is dated %s, %s against a limit of %d days' % (q['fx_text'], q['fx_date'] or 'with no date', ('%d days before %s' % (stated['rate_age_days'], as_of)) if stated['rate_age_days'] is not None else 'so its age is unknown', th['fx_max_age_days']))
        div = FX.divergence_bps(ref_conv['aud_cents'], stated['aud_cents'])
        if div is not None and abs(div) > tol:
            reasons.append('converting at the reference rate instead of the stated rate changes the unit price by %s (more than %s)' % (C.pct(div), C.pct(tol)))
        if not reasons:
            run['silent'] += 1
            continue
        diff = (ref_conv['aud_cents'] - stated['aud_cents']) if div is not None else None
        sigs.append(S.make(
            rl, _scope(None), q['key'], 'procurement_materials', 'fx_stale_or_diverging', 'forecast_exposure', evs,
            'quote %s (%s %s per unit, %s) converts to %s per unit at the reference rate%s and %s at the quote\'s own stated rate; %s' % (
                q['key'], C.money(q['rate']), q['cur'], q['basis'] or 'basis not stated', C.money(ref_conv['aud_cents']) if ref_conv['aud_cents'] is not None else 'no amount',
                (' (%s, method %s, %d days old)' % (ref_conv['rate_date'], ref_conv['method'], ref_conv['rate_age_days'])) if ref_conv['status'] == 'converted' else '',
                C.money(stated['aud_cents']) if stated['aud_cents'] is not None else 'no amount', '; '.join(reasons)),
            'a conversion at a recorded rate no older than %d days from a named source' % th['fx_max_age_days'], 'FX must be converted at a recorded source, date and method, and an old rate must not stand for today\'s cost (Section 08 6)',
            S.unquantified('the quantity to be bought is not known here: the difference is stated per unit (%s per unit)' % (C.money(diff) if diff is not None else 'not computable')),
            'strong', missing=['the quantity to buy', 'the supplier\'s payment currency terms'], alternatives=['the supplier will honour its stated rate'], limits=['decision: import_costing; FX age at most %d days' % th['fx_max_age_days'],
                                                                                                                                    'reference conversion: %s, rounding %s' % (mp['fx']['method'], FX.ROUNDING)],
            urgency={'time_sensitive': True, 'date': q['valid_until'], 'basis': 'quote validity'}, owner_role='procurement_manager',
            extra={'conversion': ref_conv, 'stated_conversion': stated, 'divergence_bps': div, 'unit_difference_cents': diff,
                   'events': [event('fx_observed', ref_conv['rate_source_ref'], None, ref_conv['rate_date'], [(ref_conv['rate_source_ref'], ref_conv['rate_revision'])], as_of, material=q['material'], supplier=q['supplier'])] if ref_conv['status'] == 'converted' and ref_conv['rate_source_ref'] else []}))
    return sigs


# ------------------------------------------------------------------------------------------------------------------------------------ MP07
@rule('MP07')
def mp07_international_checks(A, rl, run, project, as_of):
    from . import intl as IN
    sigs = []
    for q in _intl_quotes(A):
        run['evaluated'] += 1
        chk = IN.checks(A.F, A.mp, q)
        if not chk['unresolved_critical']:
            run['silent'] += 1
            continue
        evs = [ev(q['ref'], q['rev'], 'quote')] + [ev(c['ref'], c['revision'], 'import_check') for c in chk['checks'] if c['ref']]
        rows = {c['check']: c for c in chk['checks']}
        detail = '; '.join('%s (%s)' % (n, rows[n]['why'] if n in rows else 'not in the configured list of checks') for n in chk['unresolved_critical'])
        sigs.append(S.make(
            rl, _scope(None), q['key'], 'procurement_materials', 'international_checks_unresolved', 'compliance_risk', evs,
            'international quote %s (%s, %s) has %d unresolved critical check(s): %s' % (q['key'], q['supplier'], q['basis'], len(chk['unresolved_critical']), detail),
            'every critical check resolved by a person with an evidence reference, or recorded as not applicable by a person',
            'unresolved critical checks block a definitive recommendation; APG does not declare a product compliant or a supplier cleared (Section 08 12)',
            S.unquantified('an unresolved check has no amount; it blocks a definitive comparison'), 'strong', missing=[n for n in chk['unresolved_critical']],
            alternatives=['the check was done outside the imported data'], limits=['critical checks: ' + ', '.join(A.mp['international']['critical_checks']), chk['note']],
            urgency={'time_sensitive': True, 'date': q['valid_until'], 'basis': 'quote validity'}, owner_role='procurement_manager',
            extra={'unresolved_critical': chk['unresolved_critical'], 'unresolved': chk['unresolved'], 'events': [event('import_check_open', q['ref'], q['received'], q['issue'], [(q['ref'], q['rev'])], as_of, effective_to=q['valid_until'], material=q['material'], supplier=q['supplier'],
                                                                                                                       detail={'unresolved_critical': chk['unresolved_critical']})]}))
    return sigs


# ------------------------------------------------------------------------------------------------------------------------------------ MP08
@rule('MP08')
def mp08_supplier(A, rl, run, project, as_of):
    sp = A.mp['supplier']
    sigs = []
    for sup, p in sorted(A.suppliers().items()):
        run['evaluated'] += 1
        flagged = [n for n, lv in sorted(p['levels'].items()) if lv == 'below_level']
        if p['limited_history'] and any(lv == 'limited_history' for lv in p['levels'].values()):
            run['not_assessed'].append({'subject': sup, 'why': p['sample_note']})
        if not flagged:
            run['silent'] += 1
            continue
        evs = [ev(r, v, 'order' if r.startswith('purchase_order') else 'delivery') for r, v in p['evidence']]
        vals = {'fill_rate': (p['fill_rate_bps'], sp['min_fill_bps']), 'acceptance_rate': (p['acceptance_rate_bps'], sp['min_acceptance_bps'])}
        text = '; '.join('%s %s against a level of %s' % (n.replace('_', ' '), C.pct(vals[n][0]), C.pct(vals[n][1])) for n in flagged)
        sigs.append(S.make(
            rl, _scope(None), sup, 'suppliers_compliance', 'supplier_performance_below_level', 'operational_risk', _dedupe(evs),
            '%s: %s over %d orders with deliveries (%s to %s)' % (sup, text, p['orders_with_deliveries'], p['period']['first_order'], p['period']['last_order']),
            'performance at or above the configured levels on a sample of at least %d orders with deliveries' % sp['min_sample'], 'observed performance below a configured level on a sufficient sample; it is not a prediction and not a ranking',
            S.unquantified('performance has no amount until a consequence (rework, delay, re-order) is evidenced'), 'moderate', missing=['the reason for the shortfall', 'on-time performance (no promised dates are held)'],
            alternatives=['the shortfall is explained by a specification change or a project-specific issue', 'a small number of large orders'], limits=[p['sample_note']] + p['not_measured'],
            urgency={'time_sensitive': False, 'date': None, 'basis': ''}, owner_role='procurement_manager', extra={'supplier': sup, 'profile': {k: v for k, v in p.items() if k != 'evidence'}, 'flagged': flagged}))
    return sigs


# ------------------------------------------------------------------------------------------------------------------------------------ MP09
@rule('MP09')
def mp09_opportunity(A, rl, run, project, as_of):
    sigs = []
    for o in A.opportunities():
        run['evaluated'] += 1
        qty = o['quantity_micro']
        evs = [ev(s[0], s[1], 'quote' if s[0].startswith('supplier_quote') else ('order' if s[0].startswith('purchase_order') else 'source')) for s in o['sources']] + offer_evidence(o['offer_evaluation'])
        quant = S.quantified(o['gross_estimate_cents'], 'unit difference times the quantity not yet ordered', 'mkt.opportunity@%s:%s' % (as_of, o['id']),
                             o['assumptions'] + ['gross, before any implementation, switching or other incremental cost'], label='estimate') if o['gross_estimate_cents'] else \
            S.unquantified('no demand is left uncovered, so there is no quantity to apply the %s per unit difference to' % C.money(o['unit_gap_cents']))
        sigs.append(S.make(
            rl, _scope(o['project']), o['id'], 'procurement_materials', 'saving_opportunity', 'potential_opportunity', _dedupe(evs),
            'quote %s from %s is %s per unit against %s at %s per unit paid on %s (%s below the reference)%s' % (
                o['quote'].split('/', 1)[1], o['supplier'], C.money(o['quote_unit_cents']), o['reference'].split('/', 1)[1], C.money(o['reference_unit_cents']), o['reference_date'], C.pct(o['gap_bps']),
                ' (the reference order is held as a possible duplicate; its rate is the same on every candidate)' if o['reference_held_as_duplicate_candidate'] else ''),
            'no estimated difference in price between comparable offers', 'a comparable, current quote is below the last rate paid by at least the configured gap; an ESTIMATE, not a realised saving',
            quant, 'moderate', missing=['an approved comparable baseline', 'the delivery basis of the last order', 'switching and qualification cost', 'confirmation that the quote can be accepted'],
            alternatives=['the last order rate included services the quote does not', 'the quote has conditions not recorded'], limits=['status: estimate; never realised until verified (Section 05, PG-MP-AC-15)', 'label: indicative'] + o['evidence_required_to_verify'][:2],
            urgency={'time_sensitive': True, 'date': o['offer_evaluation']['offer']['valid_until'], 'basis': 'quote validity'}, impact_cents=o['gross_estimate_cents'], owner_role='procurement_manager',
            extra={'opportunity': {k: v for k, v in o.items() if k not in ('offer_evaluation', 'sources')}, 'events': [event('quote_issued', o['quote'], o['offer_evaluation']['offer']['observed_at'], o['offer_evaluation']['offer']['issue_date'],
                                                                                                                                 [(o['quote'], o['quote_revision'])], as_of, effective_to=o['offer_evaluation']['offer']['valid_until'], project=o['project'], material=o['material'], supplier=o['supplier'])]}))
    return sigs


# ------------------------------------------------------------------------------------------------------------------------------------ MP10
@rule('MP10')
def mp10_portfolio(A, rl, run, project, as_of):
    opps, boundary = A.portfolio()
    if boundary:
        run['notes'].append('PORTFOLIO_BOUNDARY_APPLIED')
    sigs = []
    for o in opps:
        run['evaluated'] += 1
        evs = [ev(r, v, 'order') for r, v in o['sources']]
        quant = S.quantified(o['estimate_cents'], 'extra paid over the lowest project average, for the volume bought', 'mkt.portfolio@%s:%s' % (as_of, o['id']), o['caveats'], label='estimate')
        names = ', '.join('%s %s per unit over %s' % (r['project'], C.money(r['average_unit_cents']), C.fmt_qty(r['volume_micro'])) for r in o['projects'])
        sigs.append(S.make(
            rl, _scope(None), o['id'], 'procurement_materials', 'portfolio_rate_gap', 'potential_opportunity', evs,
            '%s bought by %d authorised projects between %s and %s at volume-weighted average rates: %s; the highest is %s above the lowest' % (o['material'], len(o['projects']), o['window_start'], o['window_end'], names, C.pct(o['gap_bps'])),
            'rates within %s across projects for the same material' % C.pct(A.mp['portfolio']['rate_gap_bps']), 'the same material code was bought at different average rates; pooling or matching the lowest rate might change cost',
            quant, 'weak', missing=['the delivery basis of each order', 'whether the lower rate was available to the other projects', 'pooled-purchase terms'], alternatives=['different sites, volumes or delivery dates explain the gap'],
            limits=o['caveats'] + ['label: indicative; never realised until verified'], urgency={'time_sensitive': False, 'date': None, 'basis': ''}, impact_cents=o['estimate_cents'], owner_role='procurement_manager',
            extra={'portfolio': {k: v for k, v in o.items() if k != 'sources'}, 'events': []}))
    return sigs


# ------------------------------------------------------------------------------------------------------------------------------------ MPD1
PROJECT_HELD_KINDS = ('material_demand', 'spec_requirement')
TENANT_HELD_KINDS = ('material', 'delivery', 'quote_reading', 'quote_tier', 'quote_term', 'landed_assumption', 'import_check', 'fx_rate', 'market_observation', 'supplier_quote')


@rule('MPD1')
def mpd1_held(A, rl, run, project, as_of):
    F = A.F
    sigs = []
    for kind in (PROJECT_HELD_KINDS if project else TENANT_HELD_KINDS):
        keys = F.of_project(kind, project)[0] if project else sorted(F.kind(kind))
        held = []
        for key in keys:
            p = F.get(kind, key)
            run['evaluated'] += 1
            if not p.get('conflict') and usable(p):
                continue
            held.append((key, C.held_codes(p)))
        if not held:
            continue
        evs = [ev('%s/%s' % (kind, k), F.rev(kind, k), 'held', None, ','.join(c)) for k, c in held]
        sigs.append(S.make(
            rl, _scope(project), '%s|held_records' % kind, 'data_integrity', 'procurement_input_held', 'data_quality_risk', evs,
            '%d %s record(s) are held and were not used by any procurement rule' % (len(held), kind), 'every stored record usable, or held for a stated reason that a person has seen',
            'a held record is neither used nor ignored: procurement analyses that read this kind may be missing evidence', S.unquantified('held records are a reporting risk, not a loss'), 'strong',
            owner_role='finance_reviewer', extra={'kind': kind, 'count': len(held), 'events': []}))
    return sigs


PROJECT_RULES = (('MP02', mp02_not_comparable), ('MP03', mp03_decision_due), ('MP04', mp04_over_order), ('MP05', mp05_duplicate_order), ('MP09', mp09_opportunity), ('MPD1', mpd1_held))
TENANT_RULES = (('MP01', mp01_stale_market), ('MP06', mp06_fx), ('MP07', mp07_international_checks), ('MP08', mp08_supplier), ('MP10', mp10_portfolio), ('MPD1', mpd1_held))
