"""Recommendation policy: every value the recommendation engine needs to decide eligibility, categories, ranking order, approval authority and the verification gate is CONFIGURATION here,
with NO default.  Blueprint: Section 10 sections 3 (eligibility), 4 (explainable multi-factor prioritisation: "ranking logic and factor values must be explainable and auditable"), 5 (categories),
7 (scenario comparison for material decisions), 9 (approval attributable to an authorised person), Section 05 section 10.1 (the realised-savings verification gate), Section 06 section 5.1
(thresholds may not be silently changed by AI).

A policy is a versioned record.  A version is immutable: a change is a new version, and only approvals may be appended to a stored version.  A policy is APPROVED only when a human
'recommendation_policy_owner' who is not the proposer has approved it through `approve_policy`, from that person's own verified context, and the audit log confirms the approval (correction
APG-M7.1, finding F-66: in M7 an approval could be asserted by caller-supplied fields).  A run made under an unapproved policy says so on every recommendation, and no recommendation of such a run
can be submitted for approval.

What a missing value does (never a silent default):
  * a finding whose interpretation has no category in `categories` gets no action category: it is routed to INVESTIGATE with the reason CATEGORY_NOT_CONFIGURED;
  * a recommendation whose magnitude falls in no approval band has no approval authority and cannot be submitted for approval (AUTHORITY_NOT_CONFIGURED);
  * an absent `rank_order` stops the run: ranking without a stated order would be an unexplained order.
This module chooses no value.  The demonstration policy (rec/demo_rec.py) is SYNTHETIC and ILLUSTRATIVE; its values are the builder's own, labelled as such."""
from .. import canon
from ..det import signal as S
from ..ports import ConflictError

POLICY_KIND = 'rec_policy'
POLICY_ROLE = 'recommendation_policy_owner'

CATEGORIES = ('investigate', 'prevent', 'correct', 'recover', 'optimise', 'negotiate', 'escalate', 'monitor', 'close')
ACTION_CATEGORIES = ('prevent', 'correct', 'recover', 'optimise', 'negotiate', 'escalate', 'monitor')     # a category a policy may map an interpretation to; investigate and close are set by the gates
RANK_KEYS = ('actionability', 'time_sensitivity', 'urgency', 'confidence', 'net_benefit', 'magnitude')
STRENGTH_ORDER = ('weak', 'moderate', 'strong')
REVIEW_TYPES = ('safety', 'quality', 'legal', 'contractual')
FIELDS = ('version', 'proposer', 'approvals', 'note', 'eligibility', 'categories', 'mandatory_reviews', 'approval_bands', 'rank_order', 'scenario_required_above_cents', 'verification')


class RecPolicyError(ValueError):
    pass


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _nonneg(v):
    return _int(v) and v >= 0


def _text(v):
    return isinstance(v, str) and bool(v.strip())


def validate_policy(p):
    """-> list of problems (empty = valid).  Validates shape only; it never fills in a value."""
    bad = []
    if not isinstance(p, dict):
        return ['policy must be a dict']
    for k in p:
        if k not in FIELDS:
            bad.append('unknown field ' + str(k))
    if not _text(p.get('version')):
        bad.append('version')
    if not _text(p.get('proposer')):
        bad.append('proposer')
    ap = p.get('approvals', [])
    if not isinstance(ap, list) or not all(isinstance(a, dict) and set(a) == {'approver', 'role', 'kind', 'date'} and all(_text(v) for v in a.values()) for a in ap):
        bad.append('approvals')
    el = p.get('eligibility')
    if el is not None:
        if not isinstance(el, dict) or set(el) - {'stale_after_days', 'min_strength_for_action', 'due_soon_days'}:
            bad.append('eligibility')
        else:
            if 'stale_after_days' in el and not _nonneg(el['stale_after_days']):
                bad.append('eligibility.stale_after_days')
            if 'min_strength_for_action' in el and el['min_strength_for_action'] not in STRENGTH_ORDER:
                bad.append('eligibility.min_strength_for_action')
            if 'due_soon_days' in el and not _nonneg(el['due_soon_days']):
                bad.append('eligibility.due_soon_days')
    cat = p.get('categories')
    if cat is not None:
        if not isinstance(cat, dict) or any(k not in S.INTERPRETATIONS or v not in ACTION_CATEGORIES for k, v in cat.items()):
            bad.append('categories')
    mr = p.get('mandatory_reviews')
    if mr is not None:
        if not isinstance(mr, dict) or any(k not in S.FAMILIES or not isinstance(v, list) or not v or len(set(v)) != len(v) or any(x not in REVIEW_TYPES for x in v) for k, v in mr.items()):
            bad.append('mandatory_reviews')
    bands = p.get('approval_bands')
    if bands is not None:
        if not isinstance(bands, list) or not bands or any(not isinstance(b, dict) or set(b) != {'min_cents', 'role'} or not _nonneg(b['min_cents']) or not _text(b['role']) for b in bands) \
                or len({b['min_cents'] for b in bands}) != len(bands) or min(b['min_cents'] for b in bands) != 0:
            bad.append('approval_bands (a list of {min_cents, role}, distinct thresholds, the lowest at 0 so that every amount has an authority)')
    ro = p.get('rank_order')
    if ro is not None:
        if not isinstance(ro, list) or not ro or len(set(ro)) != len(ro) or any(k not in RANK_KEYS for k in ro):
            bad.append('rank_order')
    sr = p.get('scenario_required_above_cents')
    if sr is not None and not _nonneg(sr):
        bad.append('scenario_required_above_cents')
    vf = p.get('verification')
    if vf is not None:
        if not isinstance(vf, dict) or set(vf) != {'offset_components'} or not isinstance(vf['offset_components'], list) or not vf['offset_components'] \
                or len(set(vf['offset_components'])) != len(vf['offset_components']) or not all(_text(x) for x in vf['offset_components']):
            bad.append('verification (offset_components: the hidden or offsetting cost components every verification must address)')
    if not _text(p.get('note', 'x')):
        bad.append('note')
    return bad


def new_policy(version, proposer, **fields):
    """A policy as proposed: it never carries an approval.  Approvals are added only by `approve_policy`, from the approver's own verified context (finding F-66, correction APG-M7.1)."""
    if 'approvals' in fields:
        raise RecPolicyError('a proposed policy carries no approval; approvals are recorded only through approve_policy by an authorised person')
    p = {'version': version, 'proposer': proposer, 'approvals': []}
    p.update(fields)
    bad = validate_policy(p)
    if bad:
        raise RecPolicyError('; '.join(bad))
    return canon.deep_copy(p)


def is_approved(p, verified=None):
    """True if a human policy owner other than the proposer approved it.  `verified`: the set of approvers whose approval the audit log confirms (`verified_approvers`); when given, only those
    count.  The shape of a stored approval alone is never enough at a run (engine.run passes `verified`)."""
    return any(a['kind'] == 'human' and a['role'] == POLICY_ROLE and a['approver'] != p['proposer'] and (verified is None or a['approver'] in verified) for a in p.get('approvals', []))


def store_policy(scoped, p):
    """Store a PROPOSED policy version.  The proposer is the person storing it (from the verified context, never from the payload), the actor must be a person, and the policy must carry no
    approval: an approval cannot be supplied by a caller (F-66).  Storing the same version again with the same content is a no-op; a different content is refused (a change is a new version)."""
    bad = validate_policy(p)
    if bad:
        raise RecPolicyError('; '.join(bad))
    ctx = scoped.ctx
    cur = scoped.get(POLICY_KIND, p['version'])
    if cur is not None:
        old = cur.payload
        if p != old and not ({k: v for k, v in old.items() if k != 'approvals'} == {k: v for k, v in p.items() if k != 'approvals'} and p['approvals'] == []):
            raise RecPolicyError(f'recommendation policy version {p["version"]} already exists with different content; a change is a new version (approvals are added only by approve_policy)')
        return cur
    if ctx.actor_kind != 'human':
        scoped.log('rec.refused', POLICY_KIND + '/' + p['version'], 'refused', reason='a policy is proposed by a person')
        raise RecPolicyError('a recommendation policy is proposed by a person')
    if p['proposer'] != ctx.user_id:
        scoped.log('rec.refused', POLICY_KIND + '/' + p['version'], 'refused', reason='the proposer named in the policy is not the person storing it')
        raise RecPolicyError('the proposer must be the person storing the policy (%s), not %r' % (ctx.user_id, p['proposer']))
    if p['approvals']:
        scoped.log('rec.refused', POLICY_KIND + '/' + p['version'], 'refused', reason='a stored policy cannot arrive with approvals')
        raise RecPolicyError('a policy is stored without approvals; approvals are recorded only through approve_policy by an authorised person')
    rec = scoped.put(POLICY_KIND, p['version'], p, expected_revision=0)
    scoped.log('rec.policy_proposed', POLICY_KIND + '/' + p['version'], 'ok')
    return rec


def approve_policy(scoped, clock, version, rationale):
    """The only way a policy approval is recorded (F-66).  The approver is the verified context's person: a human holding the role recommendation_policy_owner who is not the proposer and has not
    approved this version already.  The approval and an audit event of type rec.policy_approved are written; a run counts an approval only when the audit log confirms it."""
    ctx = scoped.ctx
    what = POLICY_KIND + '/' + str(version)
    if ctx.actor_kind != 'human' or POLICY_ROLE not in ctx.roles:
        scoped.log('rec.refused', what, 'refused', reason='policy approval needs a human with the role ' + POLICY_ROLE)
        raise RecPolicyError('a policy is approved only by a person with the role ' + POLICY_ROLE)
    if not (isinstance(rationale, str) and rationale.strip()):
        raise RecPolicyError('record why the policy is approved')
    cur = scoped.get(POLICY_KIND, version)
    if cur is None:
        raise RecPolicyError('no stored policy version %r' % (version,))
    p = canon.deep_copy(cur.payload)
    if p['proposer'] == ctx.user_id:
        scoped.log('rec.refused', what, 'refused', reason='the proposer cannot approve their own policy')
        raise RecPolicyError('the proposer cannot approve their own policy')
    if any(a['approver'] == ctx.user_id for a in p['approvals']):
        raise RecPolicyError('%s has already approved this version' % ctx.user_id)
    p['approvals'] = p['approvals'] + [{'approver': ctx.user_id, 'role': POLICY_ROLE, 'kind': 'human', 'date': clock.now()[:10]}]
    try:
        rec = scoped.put(POLICY_KIND, version, p, expected_revision=cur.revision)
    except ConflictError:
        raise RecPolicyError('the policy changed while it was being approved; read it again')
    scoped.log('rec.policy_approved', what, 'ok', reason=rationale[:200], detail={'version': version, 'approver': ctx.user_id, 'session': ctx.session_id})
    return canon.deep_copy(rec.payload)


def verified_approvers(scoped, p):
    """-> the approvers of `p` whose approval the tenant's audit log confirms: an event rec.policy_approved for this version, written under the approver's own verified human context.  An approval
    written into the record by any other means (a caller-supplied field, a direct store write) is not confirmed and does not count."""
    seen = set()
    for e in scoped._audit.read(scoped.ctx):
        if e.event_type == 'rec.policy_approved' and e.outcome == 'ok' and e.actor_kind == 'human' and e.resource == POLICY_KIND + '/' + p['version'] \
                and (e.detail or {}).get('version') == p['version'] and (e.detail or {}).get('approver') == e.actor:
            seen.add(e.actor)
    return sorted(a['approver'] for a in p.get('approvals', []) if a['approver'] in seen)


def missing(p):
    """-> the configuration a run needs and does not have (names), so a run can say exactly what it could not do."""
    out = []
    el = p.get('eligibility') or {}
    for k in ('stale_after_days', 'min_strength_for_action', 'due_soon_days'):
        if k not in el:
            out.append('eligibility.' + k)
    for k in ('categories', 'approval_bands', 'rank_order', 'scenario_required_above_cents', 'verification'):
        if p.get(k) is None:
            out.append(k)
    return out


def authority_for(p, cents):
    """-> the role that must approve an action of this size, or None when no band applies (no bands, or no amount: an unquantified recommendation is approved at the highest band's role,
    because nothing shows it is small)."""
    bands = p.get('approval_bands')
    if not bands:
        return None
    ordered = sorted(bands, key=lambda b: b['min_cents'])
    if cents is None:
        return ordered[-1]['role']
    role = None
    for b in ordered:
        if abs(cents) >= b['min_cents']:
            role = b['role']
    return role


def strength_at_least(have, need):
    return have in STRENGTH_ORDER and need in STRENGTH_ORDER and STRENGTH_ORDER.index(have) >= STRENGTH_ORDER.index(need)
