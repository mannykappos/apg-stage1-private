"""The recommendation run: findings -> eligibility gates -> explainable ranking -> plain-language recommendation, as ONE reproducible formula over pinned records.
Blueprint: Section 10 sections 2 to 8 and PG-RS-AC-01 to 07, 12, 13; Section 05 sections 10 and 13; Section 06 section 9 (overlapping exposures are not summed).

`rec.prioritise` is registered with the M2 reproducibility module.  It reads only what the run pinned: the findings in scope (each at the revision read), the recommendation policy version and
the recommendation inputs people wrote (rec/inputs.py).  It writes nothing, changes no finding, no forecast and no financial record; turning its output into recommendation records is a
separate, audited service step (rec/lifecycle.py).  Every factor is reported SEPARATELY; there is no combined score.

Eligibility (Section 10 section 3).  Each finding gets one ROUTE:
  action        - may be offered as an action of its policy category (prevent, correct, recover, optimise, negotiate, escalate, monitor);
  investigate   - the valuable next action is to obtain evidence or a review first (never presented as a ready-to-execute action);
  in_hand       - an action on the finding is already approved or in progress: tracked, not ranked again;
  close         - resolved, or an opportunity whose decision window has passed (loss of actionability): a person records the closure;
  excluded      - dismissed or superseded findings: listed with the reason, never ranked, never counted.
Time sensitivity: a decision window that closes (open, closing); for an opportunity a window that has closed ends the opportunity (route close); for an exposure a date that has passed means the
matter is overdue (state passed, ranked with closing windows).  Missing information is treated as CRITICAL until a constraint reviewer records that an item is not critical, with a reason
(rec/inputs.py record_evidence_assessment): unresolved critical evidence routes the finding to investigate (section 3).
Policy approval: a run counts an approval of its policy only when the audit log confirms it (policy.verified_approvers, F-66); the confirmed approvers are part of the run's parameters, so a
replay gives the same answer.  Under an unapproved policy every recommendation is blocked from submission.
Ranking (section 4) is LEXICOGRAPHIC in the order the policy names (rank_order); the order of two recommendations is always explained by the first dimension in which they differ, and two that
tie on every configured dimension are ordered by finding id, which is stated as a tie-breaker and not a judgement.  Recommendations routed `action` and `investigate` are ranked together, because
investigation can be the most valuable next action; the route is shown on every line.
Money (section 6).  Potential gross amount, estimated benefit, incremental costs and estimated net benefit are separate fields; a net benefit is stated only when a person has entered both the
expected benefit and every incremental cost; inside one overlap component (det/relations.py) only one recommendation is counted in the totals, and totals are kept per financial interpretation and
never added across interpretations.  Nothing here is a realised saving."""
import datetime, hashlib, inspect
from .. import canon, repro
from ..ports import Guard
from ..det import findings as FD, relations as RL, signal as S
from . import inputs as IN, policy as RP

FORMULA_ID, FORMULA_VERSION = 'rec.prioritise', 1
ENGINE_VERSION = 'apg-rec-1'
ROUTES = ('action', 'investigate', 'in_hand', 'close', 'excluded')
NOT_REVIEWED = ('detected', 'under_review', 'reopened')
IN_HAND = ('action_approved', 'in_progress')
CLOSED_FINDING = ('resolved',)
EXCLUDED_FINDING = ('dismissed', 'superseded')
FIN_STATUS = {'figure': 'authoritative', 'record': 'authoritative', 'estimate': 'qualified', 'none': 'unquantified'}
URGENCY_VALUE = {'overdue': 4, 'soon': 3, 'later': 2, 'not_dated': 1}
WINDOW_VALUE = {'passed': 3, 'closing': 3, 'open': 2, 'none': 1, 'expired': 0}
LABELS = {'actionability': 'actionability', 'time_sensitivity': 'time sensitivity', 'urgency': 'urgency', 'confidence': 'confidence', 'net_benefit': 'estimated net benefit',
          'magnitude': 'financial magnitude'}


class EngineError(ValueError):
    def __init__(self, code, msg=''):
        super().__init__(f'{code}: {msg}')
        self.code = code


def _date(s):
    if not (isinstance(s, str) and len(s) == 10 and s[4] == '-' and s[7] == '-'):
        raise ValueError('not a YYYY-MM-DD date: %r' % (s,))
    return datetime.date.fromisoformat(s)


def _readable(s):
    try:
        _date(s)
        return True
    except (ValueError, TypeError):
        return False


def _days(a, b):
    """b - a in days, both 'YYYY-MM-DD'."""
    return (_date(b) - _date(a)).days


def money(c):
    return 'unquantified' if c is None else '%s$%d.%02d' % ('-' if c < 0 else '', abs(c) // 100, abs(c) % 100)


def rec_id_of(finding_id):
    return 'REC-' + finding_id[4:] if finding_id.startswith('FND-') else 'REC-' + finding_id


# ---------------------------------------------------------------- the factors
def _confidence(f, el, as_of):
    sig = f['signal']
    q = sig['quantification']
    seen = (f.get('last_seen') or {}).get('as_of')
    age = _days(seen, as_of) if _readable(seen) else None
    stale_after = el.get('stale_after_days')
    fresh = 'unassessed' if stale_after is None or age is None else ('after_run_date' if age < 0 else 'stale' if age > stale_after else 'current')
    return {'evidence_strength': sig['confidence']['evidence_strength'], 'missing_information': list(sig['confidence']['missing_information']),
            'alternative_explanations': list(sig['confidence']['alternative_explanations']), 'financial_status': FIN_STATUS.get(q['label'], 'unquantified') if q['status'] == 'quantified' else 'unquantified',
            'amount_label': q['label'], 'freshness': fresh, 'evidence_age_days': age, 'stale_after_days': stale_after, 'detection_policy_unapproved': bool(f.get('policy_unapproved')),
            'data_limits': list(sig['data_limits'])}


def _timing(sig, el, as_of, interp=None):
    """-> (urgency, time_sensitivity).  Urgency: how soon the dated condition falls due (overdue, soon, later, not dated).  Time sensitivity: whether a decision window closes (a quote
    expiry, a milestone) and its state.  'not dated' is not 'not urgent': it means the data names no date."""
    u = sig['priority']['urgency']
    date = u.get('date')
    if date is not None and not _readable(date):
        date = None
        u = dict(u, basis='the date in the evidence cannot be read (%r): treated as not dated' % (sig['priority']['urgency'].get('date'),))
    soon = el.get('due_soon_days')
    if date:
        left = _days(as_of, date)
        if left < 0:
            cls = 'overdue'
        elif soon is None:
            cls = 'later' if left > 0 else 'soon'
        else:
            cls = 'soon' if left <= soon else 'later'
    else:
        left, cls = None, 'not_dated'
    urgency = {'class': cls, 'date': date, 'days_left': left, 'basis': u.get('basis', '') or ('no date in the evidence' if not date else ''), 'due_soon_days': soon}
    if u.get('time_sensitive') and date:
        if left < 0:
            st = 'expired' if interp == 'potential_opportunity' else 'passed'
        elif soon is not None and left <= soon:
            st = 'closing'
        else:
            st = 'open'
    else:
        st = 'none'
    window = {'state': st, 'window_date': date if st != 'none' else None, 'days_left': left if st != 'none' else None, 'basis': u.get('basis', '') if st != 'none' else 'no decision window in the evidence'}
    return urgency, window


def _money_dims(sig, inp):
    q = sig['quantification']
    gross = q['gross_cents'] if q['status'] == 'quantified' else None
    exp = (inp or {}).get('expected_benefit')
    costs = (inp or {}).get('incremental_costs')
    if costs is None:
        cost = {'status': 'not_estimated', 'cents': None, 'components': [], 'note': 'no incremental cost has been entered: the net benefit cannot be stated'}
    else:
        cost = {'status': 'estimated', 'cents': sum(c['cents'] for c in costs), 'components': canon.deep_copy(costs), 'note': 'entered by ' + (inp.get('author') or 'unknown')}
    if exp is not None and cost['status'] == 'estimated':
        net = {'status': 'estimated', 'cents': exp['cents'] - cost['cents'], 'label': 'estimate', 'formula': 'expected benefit - incremental costs (Section 10 section 6)'}
    else:
        need = [x for x, ok in (('the expected benefit of the action', exp is not None), ('every incremental cost', cost['status'] == 'estimated')) if not ok]
        net = {'status': 'unquantified', 'cents': None, 'label': 'none', 'formula': 'needs ' + ' and '.join(need)}
    magnitude = {'cents': gross, 'interpretation': sig['interpretation'], 'label': q['label'] if gross is not None else 'none', 'basis': q['basis'] if gross is not None else q['reason'],
                 'kind': 'potential gross amount (exposure or opportunity), not a benefit'}
    benefit = {'status': 'estimated' if exp is not None else 'not_estimated', 'cents': exp['cents'] if exp is not None else None, 'basis': exp['basis'] if exp is not None else ''}
    return magnitude, benefit, cost, net


def _value(dim, d):
    """The comparable value of one dimension (larger ranks first) and how it is shown."""
    if dim == 'actionability':
        return (1 if d['actionability']['actionable_now'] else 0), ('actionable now' if d['actionability']['actionable_now'] else 'not actionable now: ' + '; '.join(d['actionability']['why']))
    if dim == 'time_sensitivity':
        w = d['time_sensitivity']
        shown = {'passed': ' (%s passed: the matter is overdue)' % w['window_date'], 'open': ' (%s, %s day(s) left)' % (w['window_date'], w['days_left']), 'closing': ' (%s, %s day(s) left)' % (w['window_date'], w['days_left'])}
        return WINDOW_VALUE[w['state']], 'decision window %s%s' % (w['state'], shown.get(w['state'], ''))
    if dim == 'urgency':
        u = d['urgency']
        return URGENCY_VALUE[u['class']], 'urgency %s%s' % (u['class'].replace('_', ' '), (' (%s)' % u['date']) if u['date'] else '')
    if dim == 'confidence':
        c = d['confidence']
        return (RP.STRENGTH_ORDER.index(c['evidence_strength']) + 1, -len(c['critical_missing']), 0 if c['freshness'] == 'stale' else 1), \
            '%s evidence, %d critical missing item(s), %s' % (c['evidence_strength'], len(c['critical_missing']), c['freshness'])
    if dim == 'net_benefit':
        n = d['net_benefit']
        return ((1, n['cents']) if n['cents'] is not None else (0, 0)), ('estimated net benefit ' + money(n['cents']) if n['cents'] is not None else 'net benefit unquantified (placed after quantified ones)')
    m = d['magnitude']
    return ((1, abs(m['cents'])) if m['cents'] is not None else (0, 0)), ('potential gross ' + money(m['cents']) if m['cents'] is not None else 'magnitude unquantified (placed after quantified ones)')


# ---------------------------------------------------------------- one finding
def assess(f, pol, inp, as_of, component, comp_members, pol_approved=False):
    sig = f['signal']
    el = pol.get('eligibility') or {}
    codes, detail = [], []
    route = None
    status = f['status']
    if status in EXCLUDED_FINDING:
        return None
    conf = _confidence(f, el, as_of)
    assessed = {a['item']: a for a in (inp or {}).get('evidence_assessments', [])}
    conf['assessed_not_critical'] = [{'item': m, 'by': assessed[m]['by'], 'rationale': assessed[m]['rationale']} for m in conf['missing_information'] if m in assessed and assessed[m]['critical'] is False]
    conf['critical_missing'] = [m for m in conf['missing_information'] if not (m in assessed and assessed[m]['critical'] is False)]
    urgency, window = _timing(sig, el, as_of, sig['interpretation'])
    magnitude, benefit, cost, net = _money_dims(sig, inp)
    interp = sig['interpretation']
    category = (pol.get('categories') or {}).get(interp)
    if status in CLOSED_FINDING:
        route, category = 'close', 'close'
        codes.append('FINDING_RESOLVED')
        detail.append('the finding was resolved by %s; a person records the closure of the recommendation' % ((f.get('disposition') or {}).get('by') or 'a person'))
    elif interp == 'potential_opportunity' and window['state'] == 'expired':
        route, category = 'close', 'close'
        codes.append('WINDOW_EXPIRED')
        detail.append('the decision window closed on %s: the opportunity is no longer actionable as recorded' % window['window_date'])
    elif status in IN_HAND:
        route = 'in_hand'
        codes.append('ACTION_IN_HAND')
        detail.append('an action on the finding is already %s' % status.replace('_', ' '))
    if route is None:
        inv = []
        if status in NOT_REVIEWED:
            inv.append(('FINDING_NOT_REVIEWED', 'the finding is %s: a reviewer must confirm it before an action is recommended' % status.replace('_', ' ')))
        need = el.get('min_strength_for_action')
        if need is None:
            inv.append(('STRENGTH_RULE_NOT_CONFIGURED', 'the policy sets no minimum evidence strength for an action'))
        elif not RP.strength_at_least(conf['evidence_strength'], need):
            inv.append(('EVIDENCE_WEAK', 'the evidence is %s; an action needs at least %s' % (conf['evidence_strength'], need)))
        if conf['critical_missing']:
            inv.append(('EVIDENCE_MISSING', 'missing and not assessed as non-critical: ' + '; '.join(conf['critical_missing'])))
        if conf['freshness'] == 'stale':
            inv.append(('EVIDENCE_STALE', 'the finding was last confirmed by detection %d day(s) before %s (limit %d)' % (conf['evidence_age_days'], as_of, conf['stale_after_days'])))
        elif conf['freshness'] == 'after_run_date':
            inv.append(('EVIDENCE_AFTER_RUN_DATE', 'the finding was last confirmed on %s, after the run date %s: the run cannot use evidence it could not have had' % (f['last_seen']['as_of'], as_of)))
        elif conf['freshness'] == 'unassessed':
            inv.append(('FRESHNESS_NOT_CONFIGURED', 'the policy sets no evidence age limit, so freshness cannot be judged'))
        raw_date = sig['priority']['urgency'].get('date')
        if raw_date is not None and not _readable(raw_date):
            inv.append(('DATE_UNREADABLE', 'the date in the evidence cannot be read (%r)' % (raw_date,)))
        if interp == 'data_quality_risk':
            inv.append(('DATA_QUALITY_FINDING', 'a data-integrity finding: the next action is to resolve the data, not a commercial action'))
        if category is None and interp != 'data_quality_risk':
            inv.append(('CATEGORY_NOT_CONFIGURED', 'the policy maps no action category to %s' % interp))
        if inv:
            route = 'investigate'
            category = 'investigate'
            codes += [c for c, _ in inv]
            detail += [t for _, t in inv]
        else:
            route = 'action'
    if conf['financial_status'] != 'authoritative':
        codes.append('AMOUNT_' + conf['financial_status'].upper())
    if conf['detection_policy_unapproved']:
        codes.append('DETECTION_POLICY_UNAPPROVED')
    # constraints that a high rank can never bypass (PG-RS-AC-05)
    reviews_needed = list((pol.get('mandatory_reviews') or {}).get(sig['taxonomy']['family'], []))
    done = {r['type']: r for r in (inp or {}).get('reviews', [])}
    reviews = [{'type': t, 'status': 'recorded' if t in done else 'pending', 'by': done[t]['by'] if t in done else None, 'outcome': done[t]['outcome'] if t in done else None} for t in reviews_needed]
    failed_reviews = [r['type'] for r in reviews if r['outcome'] == 'not_cleared']
    authority = RP.authority_for(pol, magnitude['cents'])
    action_kind = (inp or {}).get('action_kind')
    consequential = action_kind in IN.CONSEQUENTIAL_KINDS
    blocked_by = ['%s review pending' % r['type'] for r in reviews if r['status'] == 'pending'] + ['%s review did not clear the action' % t for t in failed_reviews]
    if authority is None:
        blocked_by.append('no approval authority is configured')
    if not pol_approved:
        blocked_by.append('the recommendation policy is not approved by a policy owner')
    if route == 'action' and cost['status'] != 'estimated':
        blocked_by.append('incremental costs not estimated')
    # scenarios (section 7)
    req_above = pol.get('scenario_required_above_cents')
    scen_required = route == 'action' and (req_above is None or magnitude['cents'] is None or abs(magnitude['cents']) >= req_above)
    alts = [IN.check_alternative(a) for a in (inp or {}).get('alternatives', [])]
    complete_alts = [a for a in alts if a['complete']]
    no_action = {'name': 'no action (engine-generated reference)', 'complete': True, 'generated': True, 'changes_authoritative_forecast': False,
                 'consequence_of_delay': _delay_text(interp, urgency, window, magnitude)}
    scen_gaps = []
    if scen_required and not complete_alts:
        scen_gaps.append('a material decision needs at least one complete alternative beside no action (Section 10 section 7)')
        blocked_by.append('scenario comparison incomplete')
    for a in alts:
        if not a['complete']:
            scen_gaps.append('alternative %r lacks: %s' % (a['name'], ', '.join(a['missing'])))
    actionable = route == 'action' and not blocked_by
    why_not = []
    if route != 'action':
        why_not.append({'investigate': 'evidence or review needed first', 'in_hand': 'already in hand', 'close': 'no longer actionable'}[route])
    why_not += blocked_by if route == 'action' else []
    deps = list((inp or {}).get('dependencies', [])) + ['approval by a person with the role %s' % authority if authority else 'an approval authority (not configured)'] + \
        ['%s review' % r['type'] for r in reviews if r['status'] == 'pending'] + ['overlaps with %s (amounts not added)' % m for m in comp_members if m != f['finding_id']]
    risks = list((inp or {}).get('risks', [])) + (['consequential external action (%s): APG does not carry it out; a person acts in the builder\'s own systems after approval' % action_kind] if consequential else []) + \
        ['data limit: %s' % x for x in sig['data_limits']]
    d = {'magnitude': magnitude, 'urgency': urgency, 'confidence': conf, 'time_sensitivity': window, 'actionability': {'actionable_now': actionable, 'why': why_not or ['nothing blocks it']},
         'implementation_cost': cost, 'expected_benefit': benefit, 'net_benefit': net, 'dependencies': deps, 'risk_and_constraints': risks}
    out = {'rec_id': rec_id_of(f['finding_id']), 'finding_id': f['finding_id'], 'finding_version': f['version'], 'finding_status': status, 'finding_digest': sig['state_digest'],
           'scope': canon.deep_copy(f['scope']), 'subject': f['subject'], 'rule_id': f['rule_id'], 'family': sig['taxonomy']['family'], 'subtype': sig['taxonomy']['subtype'], 'interpretation': interp,
           'route': route, 'category': category, 'eligibility': {'codes': codes, 'detail': detail}, 'dimensions': d,
           'overlap': {'component': component, 'members': list(comp_members), 'counted_in_totals': None, 'note': ''},
           'constraints': {'mandatory_reviews': reviews, 'approval_role': authority, 'action_kind': action_kind, 'consequential_action': consequential, 'blocked_by': blocked_by,
                           'human_approval_required': True, 'autonomous_execution': False},
           'scenarios': {'required': scen_required, 'alternatives': alts + [no_action], 'complete': not scen_gaps or not scen_required, 'gaps': scen_gaps, 'changes_authoritative_forecast': False},
           'inputs_author': (inp or {}).get('author'), 'inputs_written_at': (inp or {}).get('written_at')}
    out['explanation'] = explain(f, out)
    return out


def _delay_text(interp, urgency, window, magnitude):
    if window['state'] in ('open', 'closing'):
        return 'the decision window closes on %s; after that the option as recorded is no longer available' % window['window_date']
    if window['state'] == 'passed':
        return 'the date %s has passed and the matter is overdue; the evidence does not show what further delay costs' % window['window_date']
    if urgency['class'] == 'overdue':
        return 'the condition was due on %s and is overdue; the evidence does not show what further delay costs' % urgency['date']
    if urgency['date']:
        return 'the condition falls due on %s; the evidence does not show what further delay costs' % urgency['date']
    return 'not supportable from the data: the evidence names no date and no cost of delay'


def explain(f, r):
    """Plain-language transparency of Section 10 section 8, built only from recorded values (no generated prose, no AI)."""
    sig, d, c = f['signal'], r['dimensions'], r['constraints']
    ex = sig['explanation']
    alts = [a['name'] for a in r['scenarios']['alternatives']]
    reviews = ', '.join('%s review %s' % (x['type'], x['status']) for x in c['mandatory_reviews']) or 'no mandatory review applies to this kind of finding'
    route_text = {'action': 'Recommended action category: %s.' % r['category'], 'investigate': 'Recommended next step: investigate before any action (%s).' % '; '.join(r['eligibility']['detail']),
                  'in_hand': 'An action is already in hand; this is tracked, not recommended again.', 'close': 'Recommended: record the closure (%s).' % '; '.join(r['eligibility']['detail'])}[r['route']]
    return {'what_and_why_now': '%s Observed: %s Expected: %s Why it matters: %s Timing: %s.' % (route_text, ex['observed'], ex['expected'], ex['reason'], _timing_text(d)),
            'evidence_and_uncertainty': '%d stored record(s); evidence %s; amount %s (%s); missing and treated as critical: %s; missing, assessed not critical: %s; alternative explanations: %s; freshness: %s.' % (
                len(sig['evidence']), d['confidence']['evidence_strength'], money(d['magnitude']['cents']), d['confidence']['financial_status'],
                '; '.join(d['confidence']['critical_missing']) or 'none', '; '.join('%s (by %s: %s)' % (x['item'], x['by'], x['rationale']) for x in d['confidence']['assessed_not_critical']) or 'none',
                '; '.join(d['confidence']['alternative_explanations']) or 'none recorded', d['confidence']['freshness']),
            'actions_and_alternatives': 'Alternatives on record: %s.' % '; '.join(alts),
            'benefits_costs_tradeoffs': 'Potential gross %s; expected benefit %s; incremental costs %s; estimated net %s (%s). Risks and constraints: %s.' % (
                money(d['magnitude']['cents']), money(d['expected_benefit']['cents']), money(d['implementation_cost']['cents']) if d['implementation_cost']['status'] == 'estimated' else 'not estimated',
                money(d['net_benefit']['cents']), d['net_benefit']['formula'], '; '.join(d['risk_and_constraints']) or 'none recorded'),
            'consequences_of_delay': [a for a in r['scenarios']['alternatives'] if a.get('generated')][0]['consequence_of_delay'],
            'required_approval': 'Approval by a person with the role %s; %s. APG records the decision; it does not carry out any action.' % (c['approval_role'] or '(not configured)', reviews),
            'outcome_measurement': 'An outcome counts as realised only after an approved baseline, implementation evidence and an authorised verification that addresses every offsetting cost (Section 05 section 10.1); until then every amount here is an estimate.',
            'not_a_claim': 'This is a recommendation, not an approved action and not a verified outcome.'}


def _timing_text(d):
    u, w = d['urgency'], d['time_sensitivity']
    return 'urgency %s%s; decision window %s' % (u['class'].replace('_', ' '), (' (date %s)' % u['date']) if u['date'] else '', w['state'])


# ---------------------------------------------------------------- the run
def _order(recs, rank_order):
    def key(r):
        return tuple(_value(k, r['dimensions'])[0] for k in rank_order)
    ranked = [r for r in recs if r['route'] in ('action', 'investigate')]
    ranked.sort(key=lambda r: r['finding_id'])
    ranked.sort(key=key, reverse=True)
    for i, r in enumerate(ranked):
        r['rank'] = i + 1
        r['rank_factors'] = [{'dimension': k, 'shown': _value(k, r['dimensions'])[1]} for k in rank_order]
        r['rank_reason'] = 'first' if i == 0 else _why(ranked[i - 1], r, rank_order)
    for r in recs:
        if r['route'] not in ('action', 'investigate'):
            r['rank'], r['rank_factors'], r['rank_reason'] = None, [], 'not ranked: route %s' % r['route']
    return ranked


def _why(a, b, rank_order):
    for k in rank_order:
        va, vb = _value(k, a['dimensions']), _value(k, b['dimensions'])
        if va[0] != vb[0]:
            return 'below %s on %s: %s, against %s' % (a['rec_id'], LABELS[k], vb[1], va[1])
    return 'ties with %s on every configured dimension (%s); placed after it by finding id, a stated tie-breaker and not a judgement' % (a['rec_id'], ', '.join(LABELS[k] for k in rank_order))


def _totals(recs):
    """Per financial interpretation, never added across interpretations.  Inside an overlap component only the largest potential gross amount counts (ties: lowest finding id)."""
    by_comp = {}
    for r in recs:
        if r['route'] in ('action', 'investigate', 'in_hand') and r['dimensions']['magnitude']['cents'] is not None:
            by_comp.setdefault((r['interpretation'], r['overlap']['component']), []).append(r)
    counted = set()
    for members in by_comp.values():
        members.sort(key=lambda r: (-abs(r['dimensions']['magnitude']['cents']), r['finding_id']))
        counted.add(members[0]['rec_id'])
        for m in members[1:]:
            m['overlap']['note'] = 'overlaps with %s: its amount is not added to the totals' % members[0]['rec_id']
    out = {}
    for r in recs:
        if r['route'] in ('close', 'excluded'):
            r['overlap']['counted_in_totals'] = False
            continue
        if r['dimensions']['magnitude']['cents'] is None:
            r['overlap']['counted_in_totals'] = False
            r['overlap']['note'] = r['overlap']['note'] or 'unquantified: listed, not counted as zero'
        else:
            r['overlap']['counted_in_totals'] = r['rec_id'] in counted
        t = out.setdefault(r['interpretation'], {'recommendations': 0, 'counted': 0, 'potential_gross_counted_cents': 0, 'estimated_net_counted_cents': 0, 'net_quantified_counted': 0,
                                                 'not_counted_overlap': [], 'unquantified': []})
        t['recommendations'] += 1
        if r['overlap']['counted_in_totals']:
            t['counted'] += 1
            t['potential_gross_counted_cents'] += r['dimensions']['magnitude']['cents']
            if r['dimensions']['net_benefit']['cents'] is not None:
                t['estimated_net_counted_cents'] += r['dimensions']['net_benefit']['cents']
                t['net_quantified_counted'] += 1
        elif r['dimensions']['magnitude']['cents'] is None:
            t['unquantified'].append(r['rec_id'])
        else:
            t['not_counted_overlap'].append(r['rec_id'])
    for t in out.values():
        t['label'] = 'estimate - not realised; one amount per overlap component; never added across interpretations'
    return out


def compute(inputs, params):
    """The formula.  inputs: {'finding/<id>': payload, 'rec_policy/<v>': payload, 'rec_input/<rec id>': payload}; params: {'as_of', 'policy', 'project' (or None), 'pins'}."""
    as_of = params['as_of']
    _date(as_of)
    pol = inputs.get(RP.POLICY_KIND + '/' + params['policy'])
    if pol is None:
        raise EngineError('POLICY_NOT_PINNED', params['policy'])
    if RP.validate_policy(pol):
        raise EngineError('POLICY_INVALID', '; '.join(RP.validate_policy(pol)))
    rank_order = pol.get('rank_order')
    if not rank_order:
        raise EngineError('RANK_ORDER_NOT_CONFIGURED', 'a ranking needs a stated order of dimensions (Section 10 section 4)')
    verified = params.get('policy_verified_approvers')
    approved = RP.is_approved(pol, set(verified) if isinstance(verified, list) else set())
    findings = sorted((v for k, v in inputs.items() if k.startswith(FD.KIND + '/')), key=lambda f: f['finding_id'])
    if params.get('project'):
        findings = [f for f in findings if f['scope'].get('project') == params['project']]
    live = [f for f in findings if f['status'] not in EXCLUDED_FINDING]
    comp = RL.components(live)
    members = {}
    for fid, c in comp.items():
        members.setdefault(c, []).append(fid)
    recs, excluded = [], []
    for f in findings:
        if f['status'] in EXCLUDED_FINDING:
            excluded.append({'finding_id': f['finding_id'], 'rec_id': rec_id_of(f['finding_id']), 'status': f['status'], 'why': 'the finding is %s: never ranked, never counted' % f['status']})
            continue
        inp = inputs.get(IN.KIND + '/' + rec_id_of(f['finding_id']))
        r = assess(f, pol, inp, as_of, comp[f['finding_id']], sorted(members[comp[f['finding_id']]]), approved)
        recs.append(r)
    ranked = _order(recs, rank_order)
    totals = _totals(recs)
    for r in recs:
        r['state_digest'] = state_digest(r)
    return {'engine_version': ENGINE_VERSION, 'as_of': as_of, 'project': params.get('project'), 'policy': {'version': pol['version'], 'approved': approved, 'approvers_confirmed_by_audit': sorted(verified) if isinstance(verified, list) else [], 'missing': RP.missing(pol)},
            'rank_order': list(rank_order), 'ranked': [r['rec_id'] for r in ranked], 'recommendations': recs, 'excluded': excluded, 'totals': totals,
            'statement': 'Recommendations and estimates only. Nothing here is an approved action, a verified outcome or a change to any forecast; APG carries out no action.'}


def state_digest(r):
    """What makes a recommendation a NEW version that must be approved again: the finding version and evidence it rests on, its route and category, its money fields and their bases, its
    constraints, reviews and evidence assessments, its dependencies and risks, and its alternatives in full: anything the approver was shown.  The rank position alone is not material (other
    findings move it), and neither is the evidence age while it stays within the policy limit."""
    d = r['dimensions']
    return canon.digest({'finding': [r['finding_id'], r['finding_version'], r['finding_digest']], 'route': r['route'], 'category': r['category'], 'codes': r['eligibility']['codes'],
                         'money': [d['magnitude']['cents'], d['expected_benefit']['cents'], d['implementation_cost']['cents'], d['net_benefit']['cents']],
                         'constraints': [r['constraints']['approval_role'], r['constraints']['action_kind'], [[x['type'], x['status'], x['outcome']] for x in r['constraints']['mandatory_reviews']]],
                         'alternatives': r['scenarios']['alternatives'], 'urgency': [d['urgency']['class'], d['time_sensitivity']['state']],
                         'dependencies': d['dependencies'], 'risks': d['risk_and_constraints'], 'costs': d['implementation_cost']['components'],
                         'benefit_basis': d['expected_benefit']['basis'], 'assessed': d['confidence']['assessed_not_critical']})[:24]


MODULES = (RP, IN, RL, S)


def code_hash():
    h = hashlib.sha256()
    for m in MODULES:
        h.update(inspect.getsource(m).encode('utf-8'))
    for fn in (compute, assess, explain, _confidence, _timing, _money_dims, _value, _order, _why, _totals, _delay_text, _timing_text, state_digest, _date, _readable, _days):
        h.update(inspect.getsource(fn).encode('utf-8'))
    return h.hexdigest()


def registry(reg=None):
    reg = reg or repro.FormulaRegistry()
    reg.register(FORMULA_ID, FORMULA_VERSION, compute, code_hash())
    return reg


def run(scoped, reg, clock, as_of, policy_version, project=None):
    """Pin every finding of the tenant (its latest revision), the policy and every recommendation input, and run the formula.  -> the stored reproducibility record payload."""
    refs = [repro.pin_latest(scoped, RP.POLICY_KIND, policy_version)]
    for rec in scoped.query(FD.KIND):
        refs.append(repro.InputRef(FD.KIND, rec.key, rec.revision, rec.payload_hash))
    for rec in scoped.query(IN.KIND):
        refs.append(repro.InputRef(IN.KIND, rec.key, rec.revision, rec.payload_hash))
    pins = {f'{r.kind}/{r.key}': r.revision for r in refs}
    pol = scoped.get(RP.POLICY_KIND, policy_version).payload
    return repro.run(scoped, reg, clock, FORMULA_ID, FORMULA_VERSION, refs, {'as_of': as_of, 'policy': policy_version, 'project': project, 'pins': pins,
                                                                            'policy_verified_approvers': RP.verified_approvers(scoped, pol, refs[0].revision)})


def current_inputs(scoped, policy_version, guards=None):
    """The inputs a run made NOW would read (latest revisions), without storing anything: used by the lifecycle to check that a recommendation still matches its sources (F-64).
    guards: if a list is given, a store guard for each read is appended to it (F-68, F-69): for each kind read by query, the exact set of (key, revision) it returned, so that a record added,
    changed or removed before the lifecycle commits makes the commit fail; for the policy, its exact revision (0 if absent)."""
    out = {}
    held = guards if guards is not None else []
    for kind in (FD.KIND, IN.KIND):
        recs = scoped.query(kind)
        for rec in recs:
            out[f'{kind}/{rec.key}'] = rec.payload
        held.append(Guard('query', kind, None, tuple((rec.key, rec.revision) for rec in recs)))
    p = scoped.get(RP.POLICY_KIND, policy_version)
    if p is not None:
        out[f'{RP.POLICY_KIND}/{policy_version}'] = p.payload
    held.append(Guard('revision', RP.POLICY_KIND, policy_version, p.revision if p is not None else 0))
    return out


def check_record(scoped, reg, run_key):
    rec = scoped.get(repro.KIND, run_key)
    if rec is None:
        return {'replay': repro.ReplayResult(False, 'RECORD_MISSING', run_key), 'pins_consistent': False, 'is_rec_run': False}
    p = rec.payload
    rp = repro.replay(scoped, reg, run_key)
    pinned = {f"{i['kind']}/{i['key']}": i['revision'] for i in p['inputs']}
    claimed = p['params'].get('pins') or {}
    return {'replay': rp, 'pins_consistent': claimed == pinned, 'is_rec_run': p['formula_id'] == FORMULA_ID}
