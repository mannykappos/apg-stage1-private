"""Site and schedule rules.  Blueprint: Section 06 section 5.2 rule 8 and section 5.3 (trend), Section 07 sections 5 and 6 (delay overlap; holding cost needs a counterfactual;
concurrent delays are not added; attribution stays suspected until evidenced), Section 09 (labour: like-for-like, no worker-level ranking), Section 13 (recurrence is not
causation), section 4 (data integrity).

R08  equipment still on hire beyond the evidenced need date
DLY  two delay events that overlap in time: reported once, never added together, holding cost left unquantified without a counterfactual
LAB  output per hour for a work package falling between two windows of COMPLETE weeks (package level only; no worker is ever compared with another)
DEF  repeat defects for the same subcontractor and trade, with the rework cost trend
D02  stored records of the new kinds that are held and so could not be used"""
import datetime
from ..fin import fmath
from ..fin.intake import usable
from . import common as C, signal as S
from .intake import DET_SPECS


def _sc(project):
    return {'level': 'project', 'project': project}


def r08_hire(F, dp, project, as_of):
    rule, params, run = C.start(F, dp, 'R08')
    if rule is None:
        return [], run
    certain, _ = F.of_project('plant_hire', project)
    sigs = []
    for key in certain:
        p = F.get('plant_hire', key)
        run['evaluated'] += 1
        if p.get('conflict') or not usable(p):
            run['not_assessed'].append({'subject': 'plant_hire/' + key, 'why': ','.join(C.held_codes(p))})
            continue
        fl = p['fields']
        need = fl.get('needed_until')
        if need is None:
            run['not_assessed'].append({'subject': 'plant_hire/' + key, 'why': 'no evidenced need date, so hire beyond need cannot be assessed'})
            continue
        if fl['on_hire_date'] > as_of:
            run['silent'] += 1
            continue
        off = fl.get('off_hire_date')
        end = min(off, as_of) if off else as_of
        excess = C.days(need, end)
        if excess <= params['min_excess_days']:
            run['silent'] += 1
            continue
        rate = fl['rate_cents_per_day']
        ev = [S.evidence('plant_hire/' + key, F.rev('plant_hire', key), 'hire', p['intrinsic']['outcome'])]
        sigs.append(S.make(
            rule, _sc(project), key, 'equipment_logistics', 'hire_beyond_need', 'forecast_exposure', ev,
            f'{fl.get("equipment_text") or "equipment"} ({key}) is needed until {need}; ' + (f'it came off hire on {off}' if off else 'no off-hire date is recorded') + f', {excess} days beyond the need date at {C.money(rate)} a day',
            f'hire ending by the evidenced need date, {need}', 'the hire runs past the date the equipment was last needed, by more than the configured days',
            S.quantified(excess * rate, 'days beyond need x recorded daily rate', f'plant_hire/{key}', ['hire is charged per calendar day at the recorded rate', 'the need date is as recorded on the hire record',
                                                                                                  'an unrecorded off-hire date is unknown, not proof the equipment is still on hire'], label='estimate'),
            'moderate', missing=['confirmation that the equipment is still on site', 'the invoiced hire charges (plant cost is not in the financial core, finding F-17)'],
            alternatives=['the need date is out of date because the programme moved', 'off-hire happened but was not recorded'], limits=['hire charges are not checked against hire invoices'],
            urgency={'time_sensitive': off is None, 'date': None, 'basis': 'accruing %s a day while on hire' % C.money(rate)}, impact_cents=excess * rate, owner_role='project_manager',
            extra={'days_beyond_need': excess, 'rate_cents_per_day': rate, 'off_hire_recorded': bool(off)}))
        run['signals'] += 1
    return sigs, run


def dly_overlap(F, dp, project, as_of):
    rule, params, run = C.start(F, dp, 'DLY')
    if rule is None:
        return [], run
    certain, _ = F.of_project('delay_event', project)
    evs = []
    for key in certain:
        p = F.get('delay_event', key)
        if p.get('conflict') or not usable(p):
            run['not_assessed'].append({'subject': 'delay_event/' + key, 'why': ','.join(C.held_codes(p))})
            continue
        fl = p['fields']
        if not fl.get('end_date'):
            run['not_assessed'].append({'subject': 'delay_event/' + key, 'why': 'no end date: an open delay cannot be compared by period'})
            continue
        if fl['start_date'] > as_of or fl['end_date'] < fl['start_date']:
            run['not_assessed'].append({'subject': 'delay_event/' + key, 'why': 'starts after the as-of date or ends before it starts'})
            continue
        evs.append((key, p))
    sigs = []
    for i in range(len(evs)):
        for j in range(i + 1, len(evs)):
            run['evaluated'] += 1
            (k1, p1), (k2, p2) = sorted((evs[i], evs[j]), key=lambda x: x[0])
            a, b = p1['fields'], p2['fields']
            lo, hi = max(a['start_date'], b['start_date']), min(a['end_date'], b['end_date'])
            ov = C.days(lo, hi) + 1 if lo <= hi else 0
            if ov < params['min_overlap_days']:
                run['silent'] += 1
                continue
            union = C.days(min(a['start_date'], b['start_date']), max(a['end_date'], b['end_date'])) + 1
            cal = [C.days(x['start_date'], x['end_date']) + 1 for x in (a, b)]
            act = a.get('activity_ref') if a.get('activity_ref') == b.get('activity_ref') else None
            grp = f'schedule:{project}:{act}' if act else None
            ev = [S.evidence('delay_event/' + k, F.rev('delay_event', k), 'delay_event') for k in (k1, k2)]
            sigs.append(S.make(
                rule, _sc(project), f'{k1}|{k2}', 'schedule_holding', 'delay_events_overlap', 'forecast_exposure', ev,
                f'delay events {k1} ({a["start_date"]} to {a["end_date"]}, recorded cause: {a.get("recorded_cause_text") or "none"}) and {k2} ({b["start_date"]} to {b["end_date"]}, recorded cause: {b.get("recorded_cause_text") or "none"}) overlap for {ov} calendar days',
                'delay periods that are counted once where they run at the same time', 'two recorded delays cover the same days, so their durations and holding costs must not be added',
                S.unquantified('holding cost needs a documented counterfactual (what would have happened without each delay); concurrent delays are not added and no per-day cost is applied without one'),
                'moderate', missing=['a documented counterfactual', 'whether either delay is on the critical path (the schedule network is not ingested)', 'who caused each delay'],
                alternatives=['the two events describe one underlying delay recorded twice', 'one cause delayed the other activity'],
                hypotheses=['each recorded cause is suspected, not evidenced; attribution is not decided here'],
                limits=['calendar days are used; the working-day calendar is not applied', 'the sum of the two durations (%d days) double counts %d days; the combined window is %d days' % (sum(cal), ov, union)],
                urgency={'time_sensitive': False, 'date': None, 'basis': ''}, overlap_group=grp, owner_role='project_manager',
                extra={'overlap_start': lo, 'overlap_end': hi, 'overlap_days': ov, 'union_days': union, 'sum_of_durations_days': sum(cal),
                       'holding_rates_cents_per_day': sorted({x for x in (a.get('holding_rate_cents_per_day'), b.get('holding_rate_cents_per_day')) if x is not None})}))
            run['signals'] += 1
    return sigs, run


def _monday(d):
    x = fmath.parse_date(d)
    return (x - datetime.timedelta(days=x.weekday())).isoformat()


def _add(d, n):
    return (fmath.parse_date(d) + datetime.timedelta(days=n)).isoformat()


def lab_productivity(F, dp, project, as_of):
    rule, params, run = C.start(F, dp, 'LAB')
    if rule is None:
        return [], run
    B, R = params['baseline_weeks'], params['recent_weeks']
    hours, rates, tsrefs, held_weeks = {}, {}, {}, {}
    certain, _ = F.of_project('timesheet', project)
    for key in certain:
        p = F.get('timesheet', key)
        fl = p['fields']
        d = fl.get('work_date')
        if p.get('conflict') or not usable(p):
            if d and d <= as_of:
                held_weeks.setdefault((fl.get('work_package_ref'), _monday(d)), []).append(key)
                run['not_assessed'].append({'subject': 'timesheet/' + key, 'why': ','.join(C.held_codes(p))})
            continue
        if d is None or d > as_of or fl.get('work_package_ref') is None:
            continue
        h = C.micro(fl.get('ordinary_hours'))
        ot = C.micro(fl['overtime_hours']) if fl.get('overtime_hours') is not None else 0
        if h is None or ot is None:
            run['not_assessed'].append({'subject': 'timesheet/' + key, 'why': 'hours are not a plain non-negative decimal'})
            continue
        wk = (fl['work_package_ref'], _monday(d))
        hours[wk] = hours.get(wk, 0) + h + ot
        r = fl.get('rate_cents_per_hour')
        if r is None:
            rates[wk] = None
        elif rates.get(wk, 0) is not None:
            rates[wk] = rates.get(wk, 0) + (h + ot) * r
        tsrefs.setdefault(wk, []).append(key)
    outputs, units = {}, {}
    wo_certain, _ = F.of_project('work_output', project)
    for key in wo_certain:
        p = F.get('work_output', key)
        if p.get('conflict') or not usable(p):
            run['not_assessed'].append({'subject': 'work_output/' + key, 'why': ','.join(C.held_codes(p))})
            continue
        fl = p['fields']
        q = C.micro(fl.get('quantity'))
        if q is None or fl['week_start'] > as_of:
            continue
        outputs[(fl['work_package_ref'], fl['week_start'])] = (q, key)
        units[(fl['work_package_ref'], fl['week_start'])] = fl.get('unit_text')
    sigs = []
    for wp in sorted({k[0] for k in outputs}):
        run['evaluated'] += 1
        weeks = sorted(w for (p_, w) in outputs if p_ == wp and _add(w, 6) <= as_of and (wp, w) in hours and (wp, w) not in held_weeks and _monday(w) == w)
        if len(weeks) < B + R:
            run['not_assessed'].append({'subject': wp, 'why': 'fewer than %d complete weeks with both hours and output' % (B + R)})
            continue
        recent, base = weeks[-R:], weeks[-(R + B):-R]
        window = base + recent
        if any(fmath.days_between(window[i], window[i + 1]) != 7 for i in range(len(window) - 1)):
            run['not_assessed'].append({'subject': wp, 'why': 'the windows are not consecutive weeks (a week is missing or incomplete)'})
            continue
        if len({units[(wp, w)] for w in window}) != 1:
            run['not_assessed'].append({'subject': wp, 'why': 'the unit of measure changes inside the windows'})
            continue
        bq, bh = sum(outputs[(wp, w)][0] for w in base), sum(hours[(wp, w)] for w in base)
        rq, rh = sum(outputs[(wp, w)][0] for w in recent), sum(hours[(wp, w)] for w in recent)
        if bq <= 0 or bh <= 0 or rh <= 0:
            run['not_assessed'].append({'subject': wp, 'why': 'a window has no output or no hours'})
            continue
        decline = fmath.round_div((bq * rh - rq * bh) * 10000, bq * rh)
        if not C.at_least_bps(bq * rh - rq * bh, bq * rh, params['decline_bps']):
            run['silent'] += 1
            continue
        excess_micro_h = rh - fmath.round_div(rq * bh, bq)                     # hours spent beyond what the baseline rate needs for the recent output
        rate_ok = all(rates.get((wp, w)) is not None for w in recent)
        est = fmath.round_div(excess_micro_h * sum(rates[(wp, w)] for w in recent), rh * 1_000_000) if rate_ok else None
        ev = [S.evidence('work_output/' + outputs[(wp, w)][1], F.rev('work_output', outputs[(wp, w)][1]), 'output:' + ('recent' if w in recent else 'baseline')) for w in window]
        ev += [S.evidence('timesheet/' + k, F.rev('timesheet', k), 'hours:' + ('recent' if w in recent else 'baseline')) for w in window for k in sorted(tsrefs[(wp, w)])]
        unit = units[(wp, window[0])]
        quant = (S.quantified(est, 'hours beyond what the baseline rate needs for the recent output x the recent average hourly rate', f'work package {wp}, weeks {recent[0]} to {recent[-1]}',
                              ['the baseline rate was achievable in comparable conditions (like-for-like is not verified)', 'the rate is the average of the recorded hourly rates in the recent window'], label='estimate')
                 if est is not None and est > 0 else S.unquantified('hourly rates are missing or zero for the recent window, so the cost of the lower output cannot be stated'))
        sigs.append(S.make(
            rule, _sc(project), wp, 'labour_productivity', 'output_per_hour_falling', 'forecast_exposure', ev,
            f'{wp}: output per hour fell {C.pct(decline)} between the {B} weeks from {base[0]} and the {R} weeks from {recent[0]} (to week {_add(recent[-1], 6)}); only complete weeks are used',
            f'output per hour within {C.pct(params["decline_bps"])} of the earlier {B} weeks', 'the recent output per hour is lower than the baseline by at least the configured fall',
            quant, 'moderate', missing=['conditions that explain the fall (weather, access, design change, rework, crew)', 'like-for-like confirmation of scope and conditions'],
            alternatives=['scope or conditions changed so the weeks are not comparable', 'output was recorded late'],
            hypotheses=['possible explanations to investigate, none evidenced: rework, access constraints, design change, weather, crew changes'],
            limits=['package level only: no worker is compared with another', 'a week that has not ended or has a held timesheet entry is left out'],
            impact_cents=est if est and est > 0 else None, owner_role='project_manager',
            extra={'decline_bps': decline, 'baseline_weeks': base, 'recent_weeks': recent, 'unit': unit, 'baseline_output_micro': bq, 'baseline_hours_micro': bh, 'recent_output_micro': rq, 'recent_hours_micro': rh}))
        run['signals'] += 1
    run['silent'] = run['evaluated'] - run['signals'] - sum(1 for n in run['not_assessed'] if '/' not in n['subject'])
    return sigs, run


def def_recurrence(F, dp, project, as_of):
    rule, params, run = C.start(F, dp, 'DEF')
    if rule is None:
        return [], run
    certain, _ = F.of_project('defect', project)
    groups = {}
    for key in certain:
        p = F.get('defect', key)
        if p.get('conflict') or not usable(p):
            run['not_assessed'].append({'subject': 'defect/' + key, 'why': ','.join(C.held_codes(p))})
            continue
        fl = p['fields']
        if fl['raised_date'] > as_of:
            continue
        if not fl.get('subcontractor_text') or not fl.get('trade_text'):
            run['not_assessed'].append({'subject': 'defect/' + key, 'why': 'subcontractor or trade is not recorded, so it cannot be grouped'})
            continue
        groups.setdefault((fl['subcontractor_text'], fl['trade_text']), []).append((fl['raised_date'], key, p))
    sigs = []
    for (sub, trade), items in sorted(groups.items()):
        run['evaluated'] += 1
        items.sort(key=lambda x: (x[0], x[1]))
        if len(items) < params['min_events']:
            run['silent'] += 1
            continue
        costs_ = [x[2]['fields'].get('rework_cost_cents') for x in items]
        known = all(c is not None for c in costs_)
        growing = known and all(b > a for a, b in zip(costs_, costs_[1:]))
        total = sum(c for c in costs_ if c is not None)
        ev = [S.evidence('defect/' + k, F.rev('defect', k), 'defect', p['intrinsic']['outcome']) for _, k, p in items]
        sigs.append(S.make(
            rule, _sc(project), f'{sub}|{trade}', 'quality_defects', 'repeat_defect_growing_rework' if growing else 'repeat_defect', 'forecast_exposure', ev,
            f'{len(items)} defects for {sub} in {trade} between {items[0][0]} and {items[-1][0]}' + (f'; rework cost grew each time: {", ".join(C.money(c) for c in costs_)}' if growing else
                                                                                                        ('; rework cost is not known for every defect' if not known else '; rework cost did not grow each time')),
            f'fewer than {params["min_events"]} defects of this kind, or a falling rework cost', 'the same trade and subcontractor repeat defects at least the configured number of times',
            S.quantified(total, 'sum of rework costs as recorded', 'defect records', ['rework costs are as recorded; open defects may cost more or less in the end'], label='record') if total > 0 or known else S.unquantified('no rework cost is recorded'),
            'moderate', missing=['root cause', 'contract responsibility for the rework'], alternatives=['each defect has a separate cause'],
            hypotheses=['a common cause such as workmanship, detailing or supervision may exist (hypothesis; recurrence is not causation)'],
            limits=['responsibility and any back-charge are not concluded from a pattern (Section 13)'], impact_cents=total, owner_role='quality_manager',
            extra={'events': len(items), 'rework_costs_cents': costs_, 'growing': growing}))
        run['signals'] += 1
    return sigs, run


def d02_held_records(kinds):
    def d02(F, dp, project, as_of):
        rule, params, run = C.start(F, dp, 'D02')
        if rule is None:
            return [], run
        scope = {'level': 'project', 'project': project} if project else {'level': 'tenant', 'project': None}
        sigs = []
        for kind in kinds:
            if project:
                keys, _ = F.of_project(kind, project)
            else:
                keys = sorted(F.kind(kind))
            held = []
            for key in keys:
                p = F.get(kind, key)
                run['evaluated'] += 1
                if not p.get('conflict') and usable(p):
                    continue
                codes = C.held_codes(p)
                dates = [p['fields'].get(f) for f in DET_SPECS[kind]['dates']] if not p.get('conflict') else []
                if codes and all(c.startswith('FUTURE_DATED:') for c in codes) and dates and all(d and d > as_of for d in dates):
                    run['notes'].append('OUTSIDE_PERIOD:' + kind + '/' + key)
                    continue
                held.append((key, codes))
            if not held:
                continue
            ev = [S.evidence(f'{kind}/{k}', F.rev(kind, k), 'held', None, ','.join(c)) for k, c in held]
            sigs.append(S.make(rule, scope, f'{kind}|held_records', 'data_integrity', 'detection_input_held', 'data_quality_risk', ev,
                               f'{len(held)} {kind} record(s) are held and were not used by any detection rule', 'every stored record usable, or held for a stated reason that a person has seen',
                               'a held record is neither used nor ignored: rules that read this kind may be missing evidence',
                               S.unquantified('held records are a reporting risk, not a loss'), 'strong', owner_role='finance_reviewer', extra={'kind': kind, 'count': len(held)}))
            run['signals'] += 1
        return sigs, run
    return d02
