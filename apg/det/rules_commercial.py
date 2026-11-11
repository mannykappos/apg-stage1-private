"""Commercial, cash and supplier rules.  Blueprint: Section 06 section 5.2 rules 4 to 7, section 4 (unsubmitted variations, delayed retention, supplier compliance), Section 11
(a potential variation is not an entitlement), Section 12 (retention is face value, not a loss), Section 04 (a quote and its basis).

R04   a variation still open (an unapproved or disputed class under the financial policy) for more than the configured days; priced or unpriced
R04B  a client instruction (source notice types the policy names) with no variation recorded against it, after the configured days
R05   a retention release date passed with no release evidence and no recorded hold reason (the M4 retention figure supplies the facts)
R06   supplier evidence (insurance, licence, anything the compliance file lists) expired, or expiring inside the warning period  [tenant scope]
R07   a quote above a comparable reference after landed-cost adjustment, for pairs a person declared comparable  [tenant scope]"""
from ..fin import cashview, commitments, fmath
from ..fin.intake import usable
from . import common as C, signal as S


def _proj_sc(project):
    return {'level': 'project', 'project': project}


def r04_variation(F, dp, project, as_of):
    rule, params, run = C.start(F, dp, 'R04')
    if rule is None:
        return [], run
    if F.policy is None or F.policy.get('variation_status_map') is None:
        return C.cannot(run, 'VARIATION_STATUS_MAP_NOT_CONFIGURED (CR-02 A12)')
    certain, _ = F.of_project('variation', project)
    sigs = []
    for key in certain:
        p = F.get('variation', key)
        run['evaluated'] += 1
        if p.get('conflict') or not usable(p):
            run['not_assessed'].append({'subject': 'variation/' + key, 'why': ','.join(C.held_codes(p))})
            continue
        fl = p['fields']
        cls = commitments.variation_class(F, fl.get('source_status'))
        raised = fl.get('raised_date')
        if cls not in ('unapproved', 'disputed') or not raised or raised > as_of:
            if cls is None:
                run['not_assessed'].append({'subject': 'variation/' + key, 'why': 'status %r is not mapped by the financial policy' % (fl.get('source_status'),)})
            else:
                run['silent'] += 1
            continue
        age = C.days(raised, as_of)
        if age <= params['unresolved_days']:
            run['silent'] += 1
            continue
        val = fl.get('value_cents')
        ev = [S.evidence('variation/' + key, F.rev('variation', key), 'variation', p['intrinsic']['outcome'])]
        quant = (S.quantified(val, 'variation value as submitted', 'variation/' + key, ['potential revenue only: submission is not entitlement (Section 11)'], label='record') if val is not None
                 else S.unquantified('the variation has no recorded value, so no amount can be stated; the scope may still carry cost'))
        sigs.append(S.make(
            rule, _proj_sc(project), key, 'commercial_revenue', 'variation_unpriced_unresolved' if val is None else 'variation_unresolved', 'potential_revenue_at_risk', ev,
            f'variation {key} ({fl.get("description_text") or "no description"}) was raised {raised} and is still {fl.get("source_status")}, {age} days later; ' + ('no value is recorded' if val is None else f'submitted value {C.money(val)}'),
            f'a variation decided or escalated within {params["unresolved_days"]} days', 'the variation has been open for longer than the configured workflow period',
            quant, 'strong', missing=['whether the work has been done', 'client correspondence on the variation'], alternatives=['the client has decided but the decision is not recorded'],
            limits=['an unresolved variation is potential revenue, not an entitlement'], urgency={'time_sensitive': True, 'date': None, 'basis': 'open for %d days' % age},
            impact_cents=val, owner_role='commercial_manager', extra={'age_days': age, 'status': fl.get('source_status')}))
        run['signals'] += 1
    return sigs, run


def r04b_instruction(F, dp, project, as_of):
    rule, params, run = C.start(F, dp, 'R04B')
    if rule is None:
        return [], run
    certain, _ = F.of_project('notice', project)
    sigs = []
    for key in certain:
        p = F.get('notice', key)
        run['evaluated'] += 1
        if p.get('conflict') or not usable(p):
            run['not_assessed'].append({'subject': 'notice/' + key, 'why': ','.join(C.held_codes(p))})
            continue
        fl = p['fields']
        if fl.get('notice_type_text') not in params['instruction_types'] or not fl.get('notice_date') or fl['notice_date'] > as_of:
            run['silent'] += 1
            continue
        link = fl.get('linked_variation_ref')
        age = C.days(fl['notice_date'], as_of)
        if link and F.get('variation', link) is not None:
            run['silent'] += 1
            continue
        if age < params['min_age_days']:
            run['silent'] += 1
            continue
        ev = [S.evidence('notice/' + key, F.rev('notice', key), 'instruction', p['intrinsic']['outcome'])]
        if link:
            sub, reason = 'instruction_link_unresolved', f'notice {key} names variation {link}, which is not in the store'
            interp, quant = 'data_quality_risk', S.unquantified('a broken link is a reporting risk, not a loss')
        else:
            sub, reason = 'instruction_without_variation', f'notice {key} ({fl.get("description_text") or "no description"}) has no variation recorded against it'
            interp, quant = 'potential_revenue_at_risk', S.unquantified('no value is recorded for the instructed work; a potential scope change is not an entitlement (Section 11)')
        sigs.append(S.make(
            rule, _proj_sc(project), key, 'commercial_revenue', sub, interp, ev,
            f'{reason}; the instruction is dated {fl["notice_date"]}, {age} days before {as_of}', 'an instruction that changes scope has a variation raised against it',
            'a client instruction with no variation may be unpriced scope change; the absence of a link in the data does not prove that none was raised elsewhere',
            quant, 'moderate', missing=['whether a variation was raised outside the imported data', 'the cost of the instructed work'], alternatives=['the instruction is within the original scope'],
            limits=['the link is as recorded in the source; a blank link means none is recorded'], urgency={'time_sensitive': True, 'date': None, 'basis': 'instruction %d days old' % age},
            owner_role='commercial_manager', extra={'age_days': age}))
        run['signals'] += 1
    return sigs, run


def r05_retention(F, dp, project, as_of):
    rule, params, run = C.start(F, dp, 'R05')
    if rule is None:
        return [], run
    if F.policy is None:
        return C.cannot(run, 'POLICY_NOT_PINNED')
    fig = cashview.build_retention(F, project, as_of)
    run['evaluated'] = 1
    if fig['state'] == 'cannot_assess':
        run['not_assessed'].append({'subject': 'retention/' + project, 'why': ','.join(fig['reasons']) or 'no retention ledger'})
        return [], run
    flags, due = fig['classified'].get('flags', []), fig['classified'].get('release_due_date')
    if 'RELEASE_REVIEW_DUE' not in flags or 'HELD_WITH_REASON' in flags or not due or C.days(due, as_of) <= params['grace_days']:
        run['silent'] = 1
        return [], run
    late = C.days(due, as_of)
    withheld = fig['classified']['pools_cents']['withheld']
    ev = [S.evidence(c['ref'], c['revision'], 'retention') for c in fig['contributed']]
    sig = S.make(rule, _proj_sc(project), project, 'cash_capital', 'retention_release_overdue', 'cash_timing_exposure', ev,
                 f'retention of {C.money(withheld)} was due for release on {due} ({late} days before {as_of}); no release and no hold reason are recorded',
                 'a release, or a recorded reason for holding it, by the due date', 'the release date has passed with the money still withheld; a review prompt, not an entitlement',
                 S.quantified(withheld, 'retention withheld, face value (M4 fin.cash_position)', f'fin.cash_position@{as_of}:retention', ['face value only: not a loss and not available cash'], label='figure'),
                 'strong', missing=['the contract release conditions', 'whether a claim has been lodged'], alternatives=['the release is conditional on defects or practical completion'],
                 limits=['retention is a cash-timing exposure, not a loss; the carrying cost is a separate calculation'], urgency={'time_sensitive': True, 'date': due, 'basis': '%d days past the due date' % late},
                 impact_cents=withheld, owner_role='commercial_manager', extra={'days_late': late, 'figure_state': fig['state']})
    run['signals'] = 1
    return [sig], run


def r06_compliance(F, dp, project, as_of):
    rule, params, run = C.start(F, dp, 'R06')
    if rule is None:
        return [], run
    sigs = []
    for key in sorted(F.kind('compliance')):
        p = F.get('compliance', key)
        run['evaluated'] += 1
        if p.get('conflict') or not usable(p):
            run['not_assessed'].append({'subject': 'compliance/' + key, 'why': ','.join(C.held_codes(p))})
            continue
        fl = p['fields']
        exp = fl['expiry_date']
        left = C.days(as_of, exp)
        if left > params['warning_days']:
            run['silent'] += 1
            continue
        sup = fl.get('supplier_ref')
        name = ((F.get('supplier', sup) or {}).get('fields', {}) or {}).get('supplier_name') or sup
        expired = left < 0
        ev = [S.evidence('compliance/' + key, F.rev('compliance', key), 'evidence_record', p['intrinsic']['outcome'])]
        sigs.append(S.make(
            rule, {'level': 'tenant', 'project': None}, key, 'suppliers_compliance', 'compliance_expired' if expired else 'compliance_expiring', 'compliance_risk', ev,
            f'{name} ({sup}) {fl.get("evidence_type_text")} ' + (f'expired on {exp}, {-left} days before {as_of}' if expired else f'expires on {exp}, in {left} days'),
            f'current {fl.get("evidence_type_text")} evidence, not expiring within {params["warning_days"]} days', 'the evidence has expired or is inside the warning period',
            S.unquantified('an expiry has no financial amount until a consequence (uninsured work, a stop-work) is evidenced'), 'strong',
            missing=['whether a renewal exists but is not recorded', 'whether the supplier has work in progress'], alternatives=['the renewed certificate has been issued but not received'],
            limits=['absence of a certificate record for a supplier is not tested here'], urgency={'time_sensitive': True, 'date': exp, 'basis': ('expired %d days ago' % -left) if expired else ('%d days to expiry' % left)},
            owner_role='procurement_manager', extra={'days_to_expiry': left, 'supplier': sup, 'evidence_type': fl.get('evidence_type_text')}))
        run['signals'] += 1
    return sigs, run


def _landed(F, kind, key, as_of):
    """-> (unit landed cents, basis text, qualifiers, limits) or (None, why)."""
    p, st = F.get(kind, key), F.recon(kind, key)
    if p is None:
        return None, 'record not in the store: ' + kind + '/' + key
    if p.get('conflict') or st is None or st['effective_outcome'] not in ('accepted', 'accepted_with_warnings') or st['lifecycle'] == 'duplicate_of':
        return None, kind + '/' + key + ' is not usable (held, disputed or duplicate)'
    fl = p['fields']
    q, limits = [], []
    if kind == 'purchase_order':
        rate = fl.get('unit_rate_cents')
        if rate is None:
            return None, 'purchase order has no unit rate'
        limits.append('the delivery basis of a purchase-order rate is not recorded; it is taken as the price paid on the order')
        return {'cents': rate, 'basis': 'purchase order unit rate', 'currency': 'AUD', 'material': fl.get('material_ref'), 'valid_until': None, 'limits': limits, 'rev': F.rev(kind, key)}, ''
    rate, cur, basis = fl.get('unit_rate_minor_units'), fl.get('currency_code'), (fl.get('delivery_basis') or '').lower()
    if cur != 'AUD':
        return None, 'currency %s: conversion is not done here (FX handling belongs to M6)' % cur
    if basis == 'delivered':
        landed, how = rate, 'delivered rate'
    elif basis == 'ex-works':
        fr = fl.get('freight_per_unit_cents')
        if fr is None:
            return None, 'ex-works quote with no freight, so a landed cost cannot be built'
        landed, how = rate + fr, f'ex-works rate {C.money(rate)} plus freight {C.money(fr)} per unit'
    else:
        return None, 'delivery basis %r needs the landed-cost model (M6)' % (fl.get('delivery_basis'),)
    limits.append('the unit of measure is not recorded on quotes')
    return {'cents': landed, 'basis': how, 'currency': cur, 'material': fl.get('material_ref'), 'valid_until': fl.get('valid_until'), 'limits': limits, 'rev': F.rev(kind, key)}, ''


def r07_quote_vs_reference(F, dp, project, as_of):
    rule, params, run = C.start(F, dp, 'R07')
    if rule is None:
        return [], run
    sigs = []
    for pr in params['pairs']:
        run['evaluated'] += 1
        subject = f'{pr["quote"]}>{pr["reference_kind"]}:{pr["reference"]}'
        a, why = _landed(F, 'supplier_quote', pr['quote'], as_of)
        rk = 'supplier_quote' if pr['reference_kind'] == 'quote' else 'purchase_order'
        b, why2 = (None, why) if a is None else _landed(F, rk, pr['reference'], as_of)
        if a is None or b is None:
            run['not_assessed'].append({'subject': subject, 'why': why or why2})
            continue
        if a['material'] != b['material']:
            run['not_assessed'].append({'subject': subject, 'why': 'the declared pair names different materials (%s, %s)' % (a['material'], b['material'])})
            continue
        over = fmath.bps_of(a['cents'] - b['cents'], b['cents'])
        if not C.exceeds_bps(a['cents'] - b['cents'], b['cents'], params['tolerance_bps']):
            run['silent'] += 1
            continue
        expired = [k for k, x in (('quote', a), ('reference', b)) if x['valid_until'] and x['valid_until'] < as_of]
        ev = [S.evidence('supplier_quote/' + pr['quote'], a['rev'], 'quote'), S.evidence(rk + '/' + pr['reference'], b['rev'], 'reference')]
        sigs.append(S.make(
            rule, {'level': 'tenant', 'project': None}, subject, 'procurement_materials', 'quote_above_reference', 'forecast_exposure', ev,
            f'quote {pr["quote"]} landed at {C.money(a["cents"])} per unit ({a["basis"]}) is {C.pct(over)} above the reference {pr["reference"]} at {C.money(b["cents"])} ({b["basis"]})',
            f'a quote within {C.pct(params["tolerance_bps"])} above the comparable reference after landed-cost adjustment', 'the declared comparable reference is cheaper by more than the tolerance',
            S.unquantified('the quantity to be bought is not known here, so the difference is stated per unit only (%s per unit)' % C.money(a['cents'] - b['cents'])),
            'weak' if expired else 'moderate', missing=['quantity to buy', 'whether the two offers meet the same specification (declared comparable by a person; the comparability gate is M6)'],
            alternatives=['the quote includes services the reference does not'], limits=a['limits'] + b['limits'] + (['EXPIRED:' + ','.join(expired)] if expired else []),
            urgency={'time_sensitive': bool(a['valid_until']), 'date': a['valid_until'], 'basis': 'quote validity'}, owner_role='procurement_manager',
            extra={'unit_difference_cents': a['cents'] - b['cents'], 'over_bps': over}))
        run['signals'] += 1
    return sigs, run
