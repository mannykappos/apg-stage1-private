"""The SIGNAL: what one rule says about one condition.  Blueprint: Section 06 section 6 (finding data contract), sections 7 and 8 (classification, quantification, severity
kept apart from urgency and confidence), section 4 (data-integrity findings are distinguishable from confirmed leakage), PG-AI-AC-05..08, 11, 12, 16.

A signal is a plain JSON-able dict (ints, strings, lists, dicts, None; never a float).  A rule makes it with `make`, which refuses a signal that breaks the contract:
  * every signal names the rule id and version, the parameters that were used, and the stored records it rests on (with the revision read);
  * the explanation has the observed condition, the expected condition and the reason;
  * the financial interpretation is ONE of a fixed list, and a data-quality or operational-risk signal carries no financial claim of loss;
  * a signal with no defensible amount says it is unquantified and why (never zero, never a guess);
  * severity, urgency and confidence are separate fields; severity is only ever 'unrated' until an approved band applies;
  * a hypothesis is labelled as one and is never presented as a cause (Section 13: recurrence is not causation);
  * an opportunity is an estimate and can never be 'realised' here (that needs the Section 05 verification, not built in this milestone).
A signal has an IDENTITY (rule, scope, subject) that does not change when the evidence or the amount changes; the lifecycle (findings.py) uses it to update one finding instead of
creating a second.  `state_digest` covers what a person would call a material change."""
from .. import canon

SIGNAL_VERSION = 'apg-signal-1'
INTERPRETATIONS = ('actual_loss', 'forecast_exposure', 'potential_opportunity', 'data_quality_risk', 'operational_risk', 'potential_revenue_at_risk', 'compliance_risk', 'cash_timing_exposure')
FAMILIES = ('commercial_revenue', 'cost_commitments', 'procurement_materials', 'labour_productivity', 'schedule_holding', 'quality_defects', 'suppliers_compliance', 'equipment_logistics',
            'cash_capital', 'data_integrity')
STRENGTH = ('strong', 'moderate', 'weak')
SCOPES = ('project', 'tenant')
NO_FINANCIAL_CLAIM = ('data_quality_risk', 'operational_risk', 'compliance_risk')


class SignalError(ValueError):
    pass


def evidence(ref, revision, role='source', recon=None, note=''):
    e = {'ref': ref, 'revision': revision, 'role': role}
    if recon is not None:
        e['reconciliation'] = recon
    if note:
        e['note'] = note
    return e


def quantified(gross_cents, basis, calc_ref, assumptions=(), incremental_cents=None, net_cents=None, label='estimate'):
    """label: 'figure' = the amount IS the value of a stored M4 figure; 'record' = an amount (or a plain difference) taken directly from stored source records with no model;
    'estimate' = anything that rests on an assumption (Section 06 PG-AI-AC-06: amounts use Section 05 calculations or are labelled estimates)."""
    return {'status': 'quantified', 'reason': '', 'gross_cents': gross_cents, 'incremental_cents': incremental_cents, 'net_cents': net_cents, 'currency': 'AUD', 'basis': basis,
            'calculation_ref': calc_ref, 'assumptions': sorted(assumptions), 'label': label}


def unquantified(reason, assumptions=()):
    return {'status': 'unquantified', 'reason': reason, 'gross_cents': None, 'incremental_cents': None, 'net_cents': None, 'currency': 'AUD', 'basis': '', 'calculation_ref': '',
            'assumptions': sorted(assumptions), 'label': 'none'}


def identity_of(rule_id, scope, subject):
    return 'FND-' + canon.digest({'rule': rule_id, 'scope': scope, 'subject': subject})[:20]


def make(rule, scope, subject, family, subtype, interpretation, evid, observed, expected, reason, quant, strength, missing=(), alternatives=(), hypotheses=(), limits=(), urgency=None,
         impact_cents=None, overlap_group=None, owner_role='project_manager', extra=None):
    """-> signal dict.  rule = {'id','version','params'}; scope = {'level','project'}."""
    s = {'signal_version': SIGNAL_VERSION, 'rule': {'id': rule['id'], 'version': rule['version'], 'params': canon.deep_copy(rule['params'])},
         'taxonomy': {'family': family, 'subtype': subtype, 'method': 'deterministic_rule'}, 'scope': dict(scope), 'subject': subject,
         'identity': identity_of(rule['id'], dict(scope), subject), 'interpretation': interpretation,
         'evidence': sorted(evid, key=lambda e: (e['ref'], e['revision'] if e['revision'] is not None else -1, e['role'])),
         'explanation': {'observed': observed, 'expected': expected, 'reason': reason}, 'quantification': quant,
         'confidence': {'evidence_strength': strength, 'missing_information': sorted(missing), 'alternative_explanations': sorted(alternatives)},
         'hypotheses': sorted(hypotheses), 'data_limits': sorted(set(limits)),
         'priority': {'severity': 'unrated', 'urgency': urgency or {'time_sensitive': False, 'date': None, 'basis': ''}, 'potential_impact_cents': impact_cents},
         'ownership': {'responsible_role': owner_role, 'reviewer_role': 'finance_reviewer'}, 'overlap_group': overlap_group, 'extra': extra or {}}
    s['state_digest'] = state_digest(s)
    validate_signal(s)
    return s


def state_digest(s):
    """What counts as a MATERIAL change of a signal: the evidence it rests on (which records, which revisions), what kind of condition it is, how it is classified, how strong the
    evidence is, what limits it carries, the severity band and whether it is time-sensitive.  A figure that merely drifts with time (hire days, an age in days) is NOT a material
    change by itself: the finding's current signal is refreshed but no new version, history entry or notification results from it."""
    q = s['quantification']
    return canon.digest({'evidence': [[e['ref'], e['revision']] for e in s['evidence']], 'status': q['status'], 'subtype': s['taxonomy']['subtype'], 'interp': s['interpretation'],
                         'strength': s['confidence']['evidence_strength'], 'limits': s['data_limits'], 'severity': s['priority']['severity'],
                         'time_sensitive': s['priority']['urgency']['time_sensitive'], 'urgency_date': s['priority']['urgency']['date']})[:24]


def validate_signal(s):
    if not isinstance(s, dict) or s.get('signal_version') != SIGNAL_VERSION:
        raise SignalError('signal version')
    r = s['rule']
    if not (isinstance(r.get('id'), str) and r['id'] and isinstance(r.get('version'), int) and not isinstance(r['version'], bool) and r['version'] >= 1 and isinstance(r.get('params'), dict)):
        raise SignalError('rule identification')
    if s['scope'].get('level') not in SCOPES or (s['scope']['level'] == 'project' and not s['scope'].get('project')):
        raise SignalError('scope')
    if s['taxonomy']['family'] not in FAMILIES or not s['taxonomy']['subtype']:
        raise SignalError('taxonomy')
    if s['interpretation'] not in INTERPRETATIONS:
        raise SignalError('interpretation')
    if not s['evidence']:
        raise SignalError('a signal must rest on at least one stored record')
    for e in s['evidence']:
        if not (isinstance(e.get('ref'), str) and '/' in e['ref'] and e.get('role')):
            raise SignalError('evidence reference')
    ex = s['explanation']
    if not all(isinstance(ex.get(k), str) and ex[k].strip() for k in ('observed', 'expected', 'reason')):
        raise SignalError('explanation needs observed, expected and reason')
    q = s['quantification']
    if q['status'] == 'quantified':
        for k in ('gross_cents',):
            if not isinstance(q[k], int) or isinstance(q[k], bool):
                raise SignalError('a quantified signal needs a whole-number gross amount')
        for k in ('incremental_cents', 'net_cents'):
            if q[k] is not None and (not isinstance(q[k], int) or isinstance(q[k], bool)):
                raise SignalError(k)
        if not q['basis'] or not q['calculation_ref']:
            raise SignalError('a quantified signal names its basis and calculation')
        if q['label'] not in ('figure', 'record', 'estimate'):
            raise SignalError('amount label')
    elif q['status'] == 'unquantified':
        if not q['reason'].strip() or q['gross_cents'] is not None:
            raise SignalError('an unquantified signal says why and carries no amount')
    else:
        raise SignalError('quantification status')
    if s['interpretation'] in NO_FINANCIAL_CLAIM and q['status'] == 'quantified' and q['label'] == 'figure':
        raise SignalError('a data-quality, operational or compliance signal does not carry a financial figure as if it were a loss')
    if s['interpretation'] == 'actual_loss' and (q['status'] != 'quantified' or q['label'] != 'figure'):
        raise SignalError('only an amount taken from a stored calculation can be called an actual loss; anything else is exposure or potential')
    c = s['confidence']
    if c['evidence_strength'] not in STRENGTH:
        raise SignalError('evidence strength')
    if s['priority']['severity'] != 'unrated' and not s['priority']['severity']:
        raise SignalError('severity')
    if s.get('identity') != identity_of(r['id'], s['scope'], s['subject']):
        raise SignalError('identity does not match rule, scope and subject')
    if s.get('state_digest') != state_digest(s):
        raise SignalError('state digest does not match the signal')
    canon.canonical(s)                                            # no floats, only JSON types
    return True


def with_severity(s, label):
    t = canon.deep_copy(s)
    t['priority']['severity'] = label
    t['state_digest'] = state_digest(t)
    return t
