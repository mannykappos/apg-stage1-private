"""Cost-to-complete, forecast final cost and forecast final margin.  Blueprint: Section 05 sections 3, 5, 6, 8; Section 03 sections 5.2 and 6.3; PG-PC-AC-02, 03, 04, 07, 15; PS-09.

  Forecast Final Cost   = actual cost to the FORECAST DATE + cost to complete (CR-02 A4 basis 'actual_to_forecast_date_plus_ctc').  A cost-to-complete estimate is made at a
                          date; actuals after that date were part of what it estimated, so adding them would count the same cost twice.  Actuals are therefore cut off at the
                          forecast date, and anything invoiced since is shown separately (classified.since_forecast_actual_cents), never added.
  Forecast Final Margin = secured forecast revenue - Forecast Final Cost.
  Cost-to-complete is built per cost code, each by the method the policy names (CR-02 A3); the components add up to the total exactly (classified.ctc_by_code) and a code
  with no usable basis is listed as UNKNOWN, never counted as zero.  If a cost-to-complete line exists for a code but is held (disputed, missing value) the code is unknown:
  there is no silent fall-back to another method.  With no cost-to-complete information at all the forecast cannot be assessed.
  A forecast is provisional (never silently authoritative) when any code is unknown, an input is stale or its freshness is not configured, or revenue is not fully known."""
from . import policy as P
from .costs import NO_CODE, build_actual, hold_class
from .figure import FigureBuilder
from .fmath import days_between
from .intake import usable
from .revenue import build_revenue

AUTH_OUTCOMES = ('accepted', 'accepted_with_warnings')
DERIVED = '(derived from budget)'


def budget_by_code(F, project):
    """-> (by_code {code: cents}, labels set, exclusions [(ref, cls, codes)], possible refs)."""
    certain, possible = F.of_project('budget_line', project)
    out, labels, excl = {}, set(), []
    for key in certain:
        base, st = F.get('budget_line', key), F.recon('budget_line', key)
        ref = 'budget_line/' + key
        if st is None or st['effective_outcome'] not in AUTH_OUTCOMES or st['amount_cents'] is None:
            cls, codes = hold_class(st) if st is not None else ('held', ['NO_RECONCILIATION_STATE'])
            excl.append((ref, cls, codes))
            continue
        code = base['fields'].get('cost_code_ref') or NO_CODE
        out[code] = out.get(code, 0) + st['amount_cents']
        labels.add(base['fields'].get('source_revision_label') or '(no label)')
    return out, labels, excl, ['budget_line/' + k for k in possible]


def select_version(F, project, as_of, wanted=None):
    """-> (version, date, usable_lines {code: (key, payload)}, excluded [(ref, cls, codes)], problem or None, possible refs)."""
    certain, possible = F.of_project('ctc_line', project)
    lines, excl, versions = {}, [], {}
    for key in certain:
        p = F.get('ctc_line', key)
        if p.get('conflict'):
            for c in p['conflict']['contenders']:
                v = c['fields'].get('forecast_version')
                if v is not None:
                    versions.setdefault(v, set()).add(c['fields'].get('forecast_date'))
            continue
        v, d = p['fields'].get('forecast_version'), p['fields'].get('forecast_date')
        if d is not None and d > as_of:
            continue
        versions.setdefault(v, set()).add(d)
    if wanted is None:
        dated = sorted(((max(d for d in ds if d), v) for v, ds in versions.items() if any(ds)), reverse=True)
        if not dated:
            return None, None, {}, [], 'NO_FORECAST_VERSION', ['ctc_line/' + k for k in possible]
        if len(dated) > 1 and dated[0][0] == dated[1][0]:
            return None, None, {}, [], 'AMBIGUOUS_LATEST_FORECAST:' + ','.join(sorted(v for d, v in dated if d == dated[0][0])), ['ctc_line/' + k for k in possible]
        wanted = dated[0][1]
    if wanted not in versions:
        return None, None, {}, [], 'FORECAST_VERSION_NOT_FOUND:' + str(wanted), ['ctc_line/' + k for k in possible]
    dates = {d for d in versions[wanted] if d}
    if len(dates) != 1:
        return wanted, None, {}, [], 'FORECAST_VERSION_DATES_DISAGREE:' + wanted, ['ctc_line/' + k for k in possible]
    date = next(iter(dates))
    for key in certain:
        p = F.get('ctc_line', key)
        ref = 'ctc_line/' + key
        if p.get('conflict'):
            if any(c['fields'].get('forecast_version') == wanted for c in p['conflict']['contenders']):
                excl.append((ref, 'disputed', ['CONFLICT_SAME_KEY'], p['conflict']['contenders'][0]['fields'].get('cost_code_ref')))
            continue
        if p['fields'].get('forecast_version') != wanted:
            continue
        code = p['fields'].get('cost_code_ref') or NO_CODE
        if usable(p) and p['fields'].get('cost_to_complete_cents') is not None:
            lines[code] = (key, p)
        else:
            excl.append((ref, 'unknown_value' if p['intrinsic']['pending'] else 'held', p['intrinsic']['pending'] or ['NOT_USABLE'], code))
    return wanted, date, lines, excl, None, ['ctc_line/' + k for k in possible]


def _fresh(b, pol, cls, newest, as_of, label):
    lim = (pol.get('freshness_days') or {}).get(cls)
    if lim is None:
        b.unknown(f'{label} freshness', 'method_not_configured', P.OPEN_DECISIONS['freshness_days'])
        return None
    age = days_between(newest, as_of)
    if age > lim:
        b.unknown(f'{label} is {age} days old, beyond the {lim} configured', 'stale')
        b.reason('STALE:' + label)
    return age


def build_ctc(F, project, version, date, lines, excl, budget, actual_by_code, as_of, possible):
    pol = F.policy
    b = FigureBuilder('cost_to_complete', 'component', 'fin.forecast', 1, {'project': project, 'forecast_version': version}, date, pol)
    method = pol['ctc_method']
    by_code, total, known = {}, 0, 0
    codes = sorted(set(budget) | set(lines) | set(actual_by_code) | {e[3] for e in excl if e[3]})
    held_codes = {e[3]: e for e in excl}
    for ref, cls, cd, code in excl:
        b.exclude(ref, cls, cd)
        if cls == 'disputed':
            b.dispute(ref, ','.join(cd))
    for ref in possible:
        b.exclude(ref, 'unattributed', ['PROJECT_UNKNOWN_OR_AMBIGUOUS'])
    for code in codes:
        m = method.get('by_cost_code', {}).get(code, method['default'])
        a = actual_by_code.get(code, 0)
        entry = {'method': m, 'cents': None, 'source': None, 'reason': None, 'basis': None, 'unknown': None}
        if code == NO_CODE:
            entry['unknown'] = 'COST_NOT_ALLOCATED_TO_A_COST_CODE'
        elif code in held_codes and code not in lines:
            entry['unknown'] = 'DECLARED_LINE_HELD:' + held_codes[code][0]
        elif m == 'declared' or (m == 'declared_else_budget_less_actual' and code in lines):
            if code in lines:
                key, p = lines[code]
                entry.update(cents=p['fields']['cost_to_complete_cents'], source='ctc_line/' + key, reason=p['fields'].get('movement_reason_text'), basis=p['fields'].get('estimate_basis_text'), method='declared')
            else:
                entry['unknown'] = 'NO_DECLARED_LINE'
        else:                                                   # budget_less_actual (or the fallback of declared_else_budget_less_actual)
            if code in lines:
                b.exclude('ctc_line/' + lines[code][0], 'not_counted', ['DECLARED_LINE_NOT_USED_BY_METHOD:' + m])
            if code not in budget:
                entry['unknown'] = 'NO_BUDGET_FOR_CODE'
            elif budget[code] - a < 0:
                entry['unknown'] = f'BUDGET_EXCEEDED_BY:{a - budget[code]}'
            else:
                entry.update(cents=budget[code] - a, source='budget_less_actual', method='budget_less_actual')
        if entry['cents'] is None:
            b.unknown(f'cost to complete for {code}', 'no_data' if entry['unknown'] in ('NO_DECLARED_LINE', 'NO_BUDGET_FOR_CODE') else 'invalid', entry['unknown'])
            b.reason('CTC_UNKNOWN:' + code)
        else:
            total += entry['cents']
            known += 1
            b.contribute(entry['source'] if entry['source'] != 'budget_less_actual' else f'budget_less_actual/{code}', F.rev('ctc_line', lines[code][0]) if code in lines and entry['method'] == 'declared' else None, entry['cents'], 'ctc')
        by_code[code] = entry
    b.classify('ctc_by_code', by_code)
    if known == 0 and by_code:
        return b.cannot('NO_COST_TO_COMPLETE_INFORMATION')
    if not by_code:
        return b.cannot('NO_COST_CODES')
    return b.finish(cents=total)


def build_forecast(F, project, as_of):
    pol = F.policy
    b = FigureBuilder('forecast_final_margin', 'forecast_final', 'fin.forecast', 1, {'project': project, 'forecast_version': None}, as_of, pol)
    if pol is None:
        return b.cannot('POLICY_NOT_PINNED')
    for fld in ('ctc_method', 'ffc_basis', 'cost_scope'):
        if pol.get(fld) is None:
            return b.cannot(fld.upper() + '_NOT_CONFIGURED', P.OPEN_DECISIONS[fld])
    version, date, lines, excl, problem, possible = select_version(F, project, as_of, F.params.get('forecast_version'))
    if problem == 'NO_FORECAST_VERSION' and F.params.get('forecast_version') is None and 'declared' not in [pol['ctc_method']['default']] + list(pol['ctc_method'].get('by_cost_code', {}).values()):
        version, date, lines, excl, problem = DERIVED, as_of, {}, [], None           # the policy's methods need no declared estimate: every code is budget less actual
        b.reason('FORECAST_DERIVED_FROM_BUDGET_NO_DECLARED_VERSION')
    if problem:
        return b.cannot(problem)
    b.f['scope']['forecast_version'] = version
    revenue = build_revenue(F, project, as_of)
    actual = build_actual(F, project, date, 'actual_cost_to_forecast_date')
    budget, labels, bexcl, bposs = budget_by_code(F, project)
    for ref, cls, cd in bexcl:
        b.exclude(ref, cls, cd)
        if cls == 'disputed':
            b.dispute(ref, ','.join(cd))
    for ref in bposs:
        b.exclude(ref, 'unattributed', ['PROJECT_UNKNOWN_OR_AMBIGUOUS'])
    if len(labels) > 1:
        b.dispute('budget_line/*', 'budget lines carry different revision labels: ' + ','.join(sorted(labels)))
        b.reason('MIXED_BUDGET_REVISIONS')
    if not budget:
        b.unknown('budget', 'no_data')
    a_by_code = actual['classified'].get('by_cost_code', {}) if actual['state'] != 'cannot_assess' else {}
    ctc = build_ctc(F, project, version, date, lines, excl, budget, a_by_code, as_of, possible)
    b.child('forecast_revenue', revenue)
    b.child('actual_cost', actual)
    b.child('cost_to_complete', ctc)
    _fresh(b, pol, 'forecast', date, as_of, 'forecast ' + version)
    newest_budget = max([F.get('budget_line', k)['fields'].get('revision_date') for k in F.of_project('budget_line', project)[0]] or [None], key=lambda x: x or '')
    if newest_budget:
        _fresh(b, pol, 'budget', newest_budget, as_of, 'budget')
    classified = {'forecast_version': version, 'forecast_date': date, 'actual_by_code': a_by_code, 'ctc_by_code': ctc['classified'].get('ctc_by_code', {}), 'budget_by_code': budget,
                  'budget_revision_labels': sorted(labels), 'ffr_cents': revenue['value']['cents'], 'ffc_basis': pol['ffc_basis']}
    if revenue['value']['cents'] is None or actual['value']['cents'] is None or ctc['value']['cents'] is None:
        for k, v in classified.items():
            b.classify(k, v)
        return b.cannot('A_COMPONENT_CANNOT_BE_ASSESSED')
    ffc = actual['value']['cents'] + ctc['value']['cents']
    classified.update(actual_cents=actual['value']['cents'], ctc_cents=ctc['value']['cents'], ffc_cents=ffc)
    cv = {'total_cents': None, 'by_code': {}}
    if budget:
        cv['by_code'] = {c: (a_by_code.get(c, 0) + ((classified['ctc_by_code'].get(c) or {}).get('cents') or 0)) - budget.get(c, 0) for c in sorted(set(budget) | set(a_by_code)) if (classified['ctc_by_code'].get(c) or {}).get('cents') is not None}
        if ctc['state'] == 'authoritative' and set(cv['by_code']) >= set(budget):
            cv['total_cents'] = ffc - sum(budget.values())
    classified['cost_variance'] = cv
    if as_of != date:
        since = build_actual(F, project, as_of, 'actual_cost_to_as_of')
        classified['since_forecast_actual_cents'] = None if since['value']['cents'] is None else since['value']['cents'] - actual['value']['cents']
        b.reason('ACTUALS_AFTER_FORECAST_DATE_NOT_ADDED')
    for k, v in classified.items():
        b.classify(k, v)
    return b.finish(cents=revenue['value']['cents'] - ffc)
