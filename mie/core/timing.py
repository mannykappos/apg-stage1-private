"""Timing assessment (MIE1_SPEC section 6; MIE-R-21 to 27, 63, 69).  The core ships no rules: the pack's ordered decision table is evaluated first-match, over a closed,
total predicate language.  Every result discloses its evidence, signals, gaps, qualification, the rule fired, the signal-influence class and the advisory statement.
The result is a record of an assessment; it orders, commits and notifies nothing."""
from . import canon, pack as P, values as V, vocab as Y

SCENARIO_KEYS = ('scenario_id', 'label', 'owner_ref', 'basis_statement', 'assumed_level', 'unit')


class FailClosed(Exception):
    """Raised when the evaluator would emit a DIRECT or PRECEDENCE result from a rule without the owner label: nothing is emitted (UT-54)."""


class Indeterminate(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def scenario_problem(sc, doc, limits):
    """-> None or why a caller scenario is refused (closed shape: anything else, including any forecast-shaped field, is refused)."""
    if not isinstance(sc, dict) or set(sc) != set(SCENARIO_KEYS):
        return 'a scenario is exactly {%s}' % ', '.join(SCENARIO_KEYS)
    for k in ('scenario_id', 'label', 'unit'):
        p = V.id_problem(sc[k], limits['max_string_length'])
        if p:
            return '%s: %s' % (k, p)
    for k in ('owner_ref', 'basis_statement'):
        p = V.text_problem(sc[k], limits['max_string_length'])
        if p or not sc[k].strip():
            return '%s: %s' % (k, p or 'empty')
    p = V.value_problem(sc['assumed_level'], limits)
    if p:
        return 'assumed_level: %s' % p
    if sc['unit'] not in {u['unit_id'] for u in doc['vocabulary']['units']}:
        return 'unit: a unit the pack does not declare'
    return None


def _view(sig):
    """The decision-table view of a signal: a stale signal counts as NOT_ASSESSED with reason STALE_EVIDENCE (section 4.8)."""
    if sig['status'] == 'ASSESSED' and sig.get('freshness', {}).get('stale'):
        return 'NOT_ASSESSED', 'STALE_EVIDENCE'
    return sig['status'], sig.get('reason')


def _pred(p, ctx):
    k = p['p']
    if k == 'SIGNAL_PRESENT':
        v = any(s['type'] == p['type'] and _view(s)[0] == 'ASSESSED'
                and (p['evidence_class'] is None or s.get('evidence_class') == p['evidence_class'])
                and (p['direction'] is None or s.get('direction') == p['direction']) for s in ctx['signals'])
    elif k == 'SIGNAL_NOT_ASSESSED':
        v = any(s['type'] == p['type'] and _view(s)[0] == 'NOT_ASSESSED' and (p['reason'] is None or _view(s)[1] == p['reason']) for s in ctx['signals'])
    elif k == 'GAP_PRESENT':
        v = any(g['reason'] == p['reason'] for g in ctx['gaps'])
    elif k == 'CONSTRAINT_COMPARE':
        days = ctx['days_to_need_by']
        if days is None:
            raise Indeterminate('CONSTRAINT_MISSING')
        val = ctx['params'][p['param']]
        if val is None:
            raise Indeterminate('PARAMETER_MISSING')
        v = {'LT': days < val, 'LE': days <= val, 'EQ': days == val, 'GE': days >= val, 'GT': days > val}[p['comparison']]
    elif k == 'CONSTRAINT_ABSENT':
        v = ctx['days_to_need_by'] is None
    elif k == 'SCENARIO_PRESENT':
        v = any(s['label'] == p['label'] for s in ctx['scenarios'])
    elif k == 'QUALIFIED':
        v = ctx['qualified']
    else:
        raise FailClosed('unknown predicate')
    return (not v) if p['negate'] else v


def evaluate(doc, intention, ctx):
    """-> decision dict.  First match wins, in the order the pack lists its rules; rules for another intention are not tried."""
    table = doc['decision_table']
    if table is None:
        return {'outcome': 'NOT_ASSESSED', 'reason': 'NO_TABLE', 'rule': None, 'influence_class': 'NONE', 'signal_influenced_rules_evaluated': []}
    first = P.first_influenced(table)
    evaluated = []
    for i, rule in enumerate(table):
        if rule['intention'] != intention:
            continue
        if P.signal_influenced(rule):
            evaluated.append(rule['rule_id'])
        try:
            hit = True
            for p in rule['predicates']:
                if not _pred(p, ctx):
                    hit = False
                    break
        except Indeterminate as e:
            return {'outcome': 'NOT_ASSESSED', 'reason': e.reason, 'rule': None, 'influence_class': 'NONE', 'signal_influenced_rules_evaluated': evaluated,
                    'undecided_at_rule': rule['rule_id']}
        if not hit:
            continue
        if doc['decision_profile'] == 'CONTEXT_ONLY':
            cls = 'NONE'
        elif P.signal_influenced(rule):
            cls = 'DIRECT'
        elif first is not None and i > first:
            cls = 'PRECEDENCE'
        else:
            cls = 'NONE'
        if cls != 'NONE' and not P.owner_labelled(rule):
            raise FailClosed('a %s result from the rule %r, which has no owner label' % (cls, rule['rule_id']))
        if rule['outcome'] not in Y.OUTCOMES[intention]:
            raise FailClosed('an outcome outside the vocabulary of the intention')
        return {'outcome': rule['outcome'], 'reason': None if rule['outcome'] != 'NOT_ASSESSED' else rule['rationale_code'],
                'rule': {'rule_id': rule['rule_id'], 'position': i, 'basis_class': rule['basis_class'], 'rationale_code': rule['rationale_code'],
                         'owner_ref': rule.get('owner_ref'), 'assumption': rule.get('assumption')},
                'influence_class': cls, 'signal_influenced_rules_evaluated': evaluated}
    return {'outcome': 'NOT_ASSESSED', 'reason': 'NO_RULE_MATCHED', 'rule': None, 'influence_class': 'NONE', 'signal_influenced_rules_evaluated': evaluated}


def build(doc, pin, request, observations, ev, approval_ref):
    """The timing result record (section 6.5) from the evidence view `ev` (signals.assess_evidence)."""
    params = {p['param_id']: p['value'] for p in doc['parameters']}
    need_by = request['constraints'].get('need_by')
    days = V.days(request['evaluation_date'], need_by) if need_by else None
    gaps = list(ev['gaps'])
    if ev['usable_evidence'] == 0:
        decision = {'outcome': 'NOT_ASSESSED', 'reason': 'NO_EVIDENCE', 'rule': None, 'influence_class': 'NONE', 'signal_influenced_rules_evaluated': []}
    else:
        decision = evaluate(doc, request['intention'], {'signals': ev['signals'], 'gaps': gaps, 'days_to_need_by': days, 'params': params,
                                                         'scenarios': request['scenarios'], 'qualified': ev['qualification']['status'] == 'QUALIFIED'})
    if decision['outcome'] == 'NOT_ASSESSED' and decision['reason'] in ('NO_EVIDENCE', 'NO_TABLE', 'NO_RULE_MATCHED', 'CONSTRAINT_MISSING', 'PARAMETER_MISSING'):
        gaps.append({'kind': 'assessment', 'reason': decision['reason']})
    if decision['outcome'] not in Y.OUTCOMES[request['intention']]:
        raise FailClosed('an outcome outside the vocabulary of the intention')
    rule = decision['rule']
    labelled = rule is not None and rule['basis_class'] == 'OWNER_ASSUMPTION'
    evidence = dict(ev['evidence'])
    evidence['scenarios'] = [dict(s, label_kind='ASSUMPTION', note='a caller-supplied assumption, not a forecast and not derived from history') for s in request['scenarios']]
    uncertainty = dict(ev['uncertainty'], gaps=len(gaps))
    body = {
        'record': 'mie-timing-assessment',
        'versions': dict(Y.VERSIONS),
        'pack': pin,
        'activation_approval_ref': approval_ref,
        'subject_id': request['subject_id'],
        'evaluation_date': request['evaluation_date'],
        'intention': request['intention'],
        'constraints': request['constraints'],
        'request_freshness_limits': request['freshness_limits'],
        'days_to_need_by': days,
        'evidence': evidence,
        'signals': ev['signals'],
        'decision_profile': doc['decision_profile'],
        'outcome': decision['outcome'],
        'outcome_reason': decision['reason'],
        'rule_fired': rule,
        'signal_influence': {'class': decision['influence_class'], 'signal_influenced_rules_evaluated': decision['signal_influenced_rules_evaluated']},
        'assumption': ({'assumption_based': True, 'statement': Y.ASSUMPTION_LABEL, 'owner_ref': rule['owner_ref'], 'assumption': rule['assumption']}
                       if labelled else {'assumption_based': False}),
        'uncertainty': uncertainty,
        'gaps': gaps,
        'qualification': {'status': ev['qualification']['status'], 'reasons': ev['qualification']['reasons'],
                          'required_evidence': ev['qualification']['required_evidence']},
        'advisory': Y.ADVISORY,
    }
    if 'undecided_at_rule' in decision:
        body['undecided_at_rule'] = decision['undecided_at_rule']
    return body


def result_id(pin, request, evidence_ids):
    """RS- + SHA-256 over the canonical bytes of the core and vocabulary versions, the pack pin, the request and the evidence set (section 8)."""
    return 'RS-' + canon.digest({'versions': dict(Y.VERSIONS), 'pack': pin, 'request': request, 'evidence': sorted(evidence_ids)})
