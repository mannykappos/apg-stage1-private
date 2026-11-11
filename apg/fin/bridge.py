"""Forecast movement bridge.  Blueprint: Section 05 section 8 and PG-PC-AC-08 (bridges reconcile to forecast version changes, unexplained movements surfaced), PS-09, PG-PC-AC-18
(input changes, rule changes and corrections are distinguishable).

The bridge is a pure function of TWO stored forecast results (immutable calculation records), not of live data, so it reproduces exactly.  It splits the change in forecast final
margin into items - one per revenue record, per cost record and per cost code of cost-to-complete - and the items add up to the change EXACTLY (any remainder is shown as its own
'residual' item, never absorbed).  Each item says whether it is explained:
  * a newly counted invoice, credit, or newly approved variation is explained by that record;
  * a cost-to-complete movement is explained only by the recorded movement reason, or mechanically when the method is budget-less-actual and the budget has not changed;
  * a record that stopped counting, a changed amount on an existing record, a method change, or a cost-to-complete change with a blank reason is UNEXPLAINED and listed.
No materiality threshold is applied: any unexplained movement is surfaced (thresholds are an open decision, CR-02 A1).
The two forecasts must be comparable (same project, same policy-defined bases); otherwise the bridge refuses to compare and says why."""
from .figure import FigureBuilder, CANT


def _contrib(fig, role_prefix=None):
    return {c['ref']: c for c in fig['contributed']}


def _code_of(fig):
    return {c['ref']: c.get('cost_code') for c in fig['contributed']}


def comparable(a, b):
    """-> list of reasons the two forecast results cannot be bridged (empty = comparable)."""
    out = []
    for f in (a, b):
        if f.get('formula') != 'fin.forecast' or f['value']['cents'] is None or not {'forecast_revenue', 'actual_cost', 'cost_to_complete'} <= set(f['components']):
            return ['A_FORECAST_CANNOT_BE_ASSESSED']
    if a['scope'].get('project') != b['scope'].get('project'):
        out.append('DIFFERENT_PROJECTS')
    if a['classified'].get('ffc_basis') != b['classified'].get('ffc_basis'):
        out.append('DIFFERENT_FFC_BASIS')
    if a['components']['forecast_revenue']['classified'].get('tax_basis') != b['components']['forecast_revenue']['classified'].get('tax_basis'):
        out.append('DIFFERENT_TAX_BASIS')
    return out


def build_bridge(older, newer, name='forecast_movement_bridge'):
    """older, newer: forecast figures (dicts).  -> figure whose value is the change in forecast final margin (newer - older) and whose classified.items reconcile to it."""
    pol = {'version': newer['policy']['version'], '_approved': newer['policy']['approved'] and older['policy']['approved']}
    b = FigureBuilder(name, 'forecast_final', 'fin.movement_bridge', 1, {'project': newer['scope'].get('project'), 'from': older['scope'].get('forecast_version'),
                                                                        'to': newer['scope'].get('forecast_version')}, newer['as_of'], pol)
    bad = comparable(older, newer)
    if bad:
        return b.cannot(bad[0])
    items = []
    ra, rb = older['components']['forecast_revenue'], newer['components']['forecast_revenue']
    ca, cb = _contrib(ra), _contrib(rb)
    for ref in sorted(set(ca) | set(cb)):
        old, new = ca.get(ref, {}).get('amount_cents', 0), cb.get(ref, {}).get('amount_cents', 0)
        if old == new:
            continue
        role = (cb.get(ref) or ca.get(ref))['role']
        if ref not in ca and role == 'approved_variation':
            ex, why = True, 'variation newly approved: ' + ref
        elif ref not in cb:
            ex, why = False, 'REVENUE_RECORD_NO_LONGER_COUNTED'
        else:
            ex, why = False, 'REVENUE_RECORD_AMOUNT_CHANGED_WITHOUT_RECORDED_REASON'
        items.append({'part': 'revenue', 'ref': ref, 'cost_code': None, 'effect_cents': new - old, 'explained': ex, 'why': why})
    resid_rev = (rb['value']['cents'] - ra['value']['cents']) - sum(i['effect_cents'] for i in items if i['part'] == 'revenue')
    if resid_rev:
        items.append({'part': 'revenue', 'ref': 'tax_conversion', 'cost_code': None, 'effect_cents': resid_rev, 'explained': True, 'why': 'rounding of the policy tax conversion'})
    aa, ab = older['components']['actual_cost'], newer['components']['actual_cost']
    xa, xb = _contrib(aa), _contrib(ab)
    code_a, code_b = _code_of(aa), _code_of(ab)
    for ref in sorted(set(xa) | set(xb)):
        old, new = xa.get(ref, {}).get('amount_cents', 0), xb.get(ref, {}).get('amount_cents', 0)
        if old == new:
            continue
        code = code_b.get(ref) or code_a.get(ref)
        if ref not in xa:
            ex, why = True, 'newly counted: ' + ref
        elif ref not in xb:
            ex, why = False, 'RECORD_NO_LONGER_COUNTED'
        else:
            ex, why = False, 'COUNTED_RECORD_CHANGED_AMOUNT'
        items.append({'part': 'actual_cost', 'ref': ref, 'cost_code': code, 'effect_cents': -(new - old), 'explained': ex, 'why': why})
    resid_act = -(ab['value']['cents'] - aa['value']['cents']) - sum(i['effect_cents'] for i in items if i['part'] == 'actual_cost')
    if resid_act:
        items.append({'part': 'actual_cost', 'ref': 'residual', 'cost_code': None, 'effect_cents': resid_act, 'explained': False, 'why': 'RESIDUAL_NOT_ATTRIBUTED'})
    ta, tb = older['classified']['ctc_by_code'], newer['classified']['ctc_by_code']
    budget_changed = older['classified'].get('budget_by_code') != newer['classified'].get('budget_by_code')
    for code in sorted(set(ta) | set(tb)):
        ea, eb = ta.get(code) or {}, tb.get(code) or {}
        old, new = ea.get('cents') or 0, eb.get('cents') or 0
        if old == new:
            continue
        if ea.get('cents') is None:
            ex, why = False, 'COST_TO_COMPLETE_NEWLY_KNOWN_WAS_UNKNOWN'
        elif eb.get('cents') is None:
            ex, why = False, 'COST_TO_COMPLETE_NOW_UNKNOWN'
        elif ea.get('method') != eb.get('method'):
            ex, why = False, 'CTC_METHOD_CHANGED:%s>%s' % (ea.get('method'), eb.get('method'))
        elif eb['method'] == 'declared':
            reason = (eb.get('reason') or '').strip()
            ex, why = (True, 'recorded reason: ' + reason) if reason else (False, 'COST_TO_COMPLETE_CHANGED_WITH_BLANK_MOVEMENT_REASON')
        elif not budget_changed:
            ex, why = True, 'derived from budget less actual; budget unchanged'
        else:
            ex, why = False, 'BUDGET_CHANGED_AND_CTC_DERIVED_FROM_IT'
        items.append({'part': 'cost_to_complete', 'ref': eb.get('source') or ea.get('source') or 'budget_less_actual/' + code, 'cost_code': code, 'effect_cents': -(new - old), 'explained': ex, 'why': why})
    delta = newer['value']['cents'] - older['value']['cents']
    residual = delta - sum(i['effect_cents'] for i in items)
    if residual:
        items.append({'part': 'residual', 'ref': 'residual', 'cost_code': None, 'effect_cents': residual, 'explained': False, 'why': 'RESIDUAL_NOT_ATTRIBUTED'})
    unexplained = [i for i in items if not i['explained']]
    for i in unexplained:
        b.reason('UNEXPLAINED_MOVEMENT:%s:%s:%d' % (i['part'], i['cost_code'] or i['ref'], i['effect_cents']))
    b.child('from_forecast', older)
    b.child('to_forecast', newer)
    b.classify('items', items)
    b.classify('explained_cents', sum(i['effect_cents'] for i in items if i['explained']))
    b.classify('unexplained_cents', sum(i['effect_cents'] for i in unexplained))
    b.classify('unexplained_items', len(unexplained))
    b.classify('reconciles', sum(i['effect_cents'] for i in items) == delta)
    b.limit('no materiality threshold is applied: any unexplained movement is listed (CR-02 A1 is open)')
    return b.finish(cents=delta)
