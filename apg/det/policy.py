"""Detection policy: every threshold, tolerance, window and pairing a rule needs is CONFIGURATION here, with NO default.  Blueprint: Section 06 section 5.1 ("thresholds must be
configurable within approved governance boundaries and may not be silently changed by AI"), section 8 ("thresholds and weights must be documented, testable and approved"),
section 9.1 (alert-noise control), CR-02 (materiality, aggregation).

A policy is a versioned record.  A version is immutable (a change is a new version; only approvals may be appended).  A rule whose entry or parameter is missing does not run
and does not stay silent about it: the run records `not_configured` for that rule and names the missing parameter (no alert is never proof of no issue, Section 06 section 10).
A policy is APPROVED only when a human 'detection_policy_owner' who is not the proposer has approved it through `approve_policy`, from that person's own verified context, and the
audit log confirms it (correction APG-F67, finding F-67; apg/policy_approval.py); findings produced under an unapproved policy say so.

This module chooses no value.  The values in the demonstration policy (det/demo_det.py) are SYNTHETIC and ILLUSTRATIVE: some come from the Builder Zero test_thresholds.json,
the others are the builder's own, labelled as such."""
from .. import canon, policy_approval as PA

POLICY_KIND = 'det_policy'
POLICY_ROLE = 'detection_policy_owner'

# rule -> (human name, parameters that must be configured, the decision the parameters stand for)
RULES = {
    'R01': ('Actual cost above budget tolerance (Section 06 5.2 rule 1)', ('tolerance_bps',), 'tolerance for actual cost against budget'),
    'R02': ('Commitment increase with no approved change (rule 2)', (), 'no threshold; needs the variation status map of the financial policy (CR-02 A12)'),
    'R03': ('Invoiced amount above order amount beyond tolerance (rule 3)', ('tolerance_bps',), 'tolerance for invoiced against ordered'),
    'R04': ('Variation unpriced or unresolved beyond the workflow period (rule 4)', ('unresolved_days',), 'workflow period for an unresolved variation'),
    'R04B': ('Client instruction with no variation raised (Section 06 4, Section 11)', ('min_age_days', 'instruction_types'), 'age after which an instruction without a variation is raised, and which source notice types are instructions'),
    'R05': ('Retention release date passed with no release or explained hold (rule 5)', ('grace_days',), 'grace period after the due date'),
    'R06': ('Supplier insurance or licence near expiry or expired (rule 6)', ('warning_days',), 'warning period before expiry'),
    'R07': ('Quote above a comparable reference after landed-cost adjustment (rule 7)', ('tolerance_bps', 'pairs'), 'tolerance and the people-declared comparable pairs (Section 08 comparability gate is M6)'),
    'R08': ('Equipment on hire beyond evidenced need (rule 8)', ('min_excess_days',), 'days beyond need before a finding is raised'),
    'R09': ('Forecast moves materially with no explained movement (rule 9)', ('movement_abs_cents',), 'what counts as a material forecast movement'),
    'AGG': ('Orders split inside a short window (CR-02 R5, Section 06 5.4)', ('keys', 'window_days', 'single_order_abs_cents'), 'aggregation key list, window and single-order threshold (DEC-A1-8, OQ-A1-7)'),
    'DLY': ('Overlapping delay events (Section 07 5, 6.1)', ('min_overlap_days',), 'overlap that is reported'),
    'LAB': ('Labour output per hour falling (Section 09, Section 06 5.3)', ('baseline_weeks', 'recent_weeks', 'decline_bps'), 'comparison windows and the fall that is reported'),
    'DEF': ('Repeat defect, same trade, growing rework cost (Section 13)', ('min_events',), 'number of events that makes a pattern'),
}
RULE_IDS = tuple(RULES)
NOISE_KEYS = ('suppression_days', 'renotify_on')
RENOTIFY_EVENTS = ('severity_increase', 'status_transition', 'material_evidence')
AGG_KEYS = ('project', 'supplier', 'material', 'cost_code')


class DetPolicyError(ValueError):
    pass


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _nonneg(v):
    return _int(v) and v >= 0


PARAM_CHECKS = {
    'tolerance_bps': _nonneg, 'unresolved_days': _nonneg, 'min_age_days': _nonneg, 'grace_days': _nonneg, 'warning_days': _nonneg, 'min_excess_days': _nonneg,
    'movement_abs_cents': lambda v: _int(v) and v >= 1, 'window_days': lambda v: _int(v) and v >= 1, 'single_order_abs_cents': lambda v: _int(v) and v >= 1,
    'min_overlap_days': lambda v: _int(v) and v >= 1, 'baseline_weeks': lambda v: _int(v) and v >= 1, 'recent_weeks': lambda v: _int(v) and v >= 1,
    'decline_bps': lambda v: _int(v) and 1 <= v <= 10000, 'min_events': lambda v: _int(v) and v >= 2,
    'keys': lambda v: isinstance(v, list) and bool(v) and 'project' in v and len(set(v)) == len(v) and all(k in AGG_KEYS for k in v),
    'pairs': lambda v: isinstance(v, list) and bool(v) and all(isinstance(p, dict) and set(p) == {'quote', 'reference_kind', 'reference'} and p['reference_kind'] in ('quote', 'purchase_order')
                                                              and all(isinstance(p[k], str) and p[k] for k in ('quote', 'reference')) for p in v),
    'instruction_types': lambda v: isinstance(v, list) and bool(v) and all(isinstance(x, str) and x for x in v),
    'enabled': lambda v: isinstance(v, bool),
}


def validate_policy(p):
    bad = []
    if not isinstance(p, dict):
        return ['policy must be a dict']
    for k in p:
        if k not in ('version', 'proposer', 'approvals', 'rules', 'severity_bands', 'noise', 'note'):
            bad.append('unknown field ' + str(k))
    if not isinstance(p.get('version'), str) or not p.get('version'):
        bad.append('version')
    if not isinstance(p.get('proposer'), str) or not p.get('proposer'):
        bad.append('proposer')
    ap = p.get('approvals', [])
    if not isinstance(ap, list) or not all(isinstance(a, dict) and set(a) == {'approver', 'role', 'kind', 'date'} and all(isinstance(v, str) and v for v in a.values()) for a in ap):
        bad.append('approvals')
    rules = p.get('rules', {})
    if not isinstance(rules, dict):
        bad.append('rules')
    else:
        for rid, ent in rules.items():
            if rid not in RULES:
                bad.append('unknown rule ' + str(rid))
                continue
            if not isinstance(ent, dict):
                bad.append('rule ' + rid)
                continue
            for k, v in ent.items():
                if (k not in RULES[rid][1] and k != 'enabled') or not PARAM_CHECKS[k](v):
                    bad.append(f'rule {rid} parameter {k}')
    sb = p.get('severity_bands')
    if sb is not None:
        if not isinstance(sb, list) or not sb or any(not isinstance(b, dict) or set(b) != {'min_cents', 'label'} or not _nonneg(b['min_cents']) or not isinstance(b['label'], str) or not b['label'] for b in sb) \
                or len({b['min_cents'] for b in sb}) != len(sb):
            bad.append('severity_bands')
    nz = p.get('noise')
    if nz is not None:
        if not isinstance(nz, dict) or set(nz) - set(NOISE_KEYS) or ('suppression_days' in nz and not _nonneg(nz['suppression_days'])) \
                or ('renotify_on' in nz and (not isinstance(nz['renotify_on'], list) or any(x not in RENOTIFY_EVENTS for x in nz['renotify_on']))):
            bad.append('noise')
    return bad


def new_policy(version, proposer, **fields):
    """A policy as proposed: it never carries an approval (APG-F67)."""
    if 'approvals' in fields:
        raise DetPolicyError('a proposed policy carries no approval; approvals are recorded only through approve_policy by an authorised person')
    p = {'version': version, 'proposer': proposer, 'approvals': []}
    p.update(fields)
    bad = validate_policy(p)
    if bad:
        raise DetPolicyError('; '.join(bad))
    return canon.deep_copy(p)


def is_approved(p, confirmed=()):
    """A human 'detection_policy_owner', not the proposer, approved this version AND the audit log confirms it (`confirmed`, pinned by the run)."""
    return PA.counted(p, POLICY_ROLE, confirmed)


def view(p, confirmed=()):
    q = canon.deep_copy(p)
    q['_approved'] = is_approved(p, confirmed)
    return q


def rule_params(p, rid):
    """-> (params dict or None, missing [param names]).  None = the rule does not run.  `enabled: False` is a recorded switch-off, reported as such, never silent."""
    ent = (p.get('rules') or {}).get(rid)
    need = RULES[rid][1]
    if ent is None:
        return None, list(need) or ['(rule entry)']
    miss = [k for k in need if ent.get(k) is None]
    if miss:
        return None, miss
    return dict(ent), []


def severity_of(p, cents):
    """-> label from the approved bands, or 'unrated' (never a guess).  The band is the largest min_cents not above the amount."""
    bands = p.get('severity_bands')
    if bands is None or cents is None:
        return 'unrated'
    best = None
    for b in sorted(bands, key=lambda b: b['min_cents']):
        if cents >= b['min_cents']:
            best = b['label']
    return best or 'unrated'


def severity_rank(p, label):
    bands = sorted((p.get('severity_bands') or []), key=lambda b: b['min_cents'])
    labels = [b['label'] for b in bands]
    return labels.index(label) + 1 if label in labels else 0


def store_policy(scoped, p):
    """Store a PROPOSED detection-policy version, as the person storing it, without approvals (APG-F67).  The same content again is a no-op; other content is a new version."""
    return PA.store(scoped, POLICY_KIND, p, validate_policy, DetPolicyError, 'detection policy')


def approve_policy(scoped, clock, version, rationale):
    """The only way a detection-policy approval is recorded (APG-F67): by a person holding 'detection_policy_owner', not the proposer, from that person's own verified context; an
    audit event det_policy.approved is written, and a run counts the approval only when the log confirms it."""
    return PA.approve(scoped, clock, POLICY_KIND, POLICY_ROLE, version, rationale, DetPolicyError, 'detection policy')



def approval_status(scoped, version):
    """APG-F67.1 (F-72): which approvals of this version are recorded in the policy, which the audit log confirms, and which are recorded but not confirmed (they do not count)."""
    return PA.status(scoped, POLICY_KIND, version)
