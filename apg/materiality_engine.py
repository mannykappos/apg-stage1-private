"""Materiality policy engine around the CR-02 rev 2 reference model (apg/materiality.py, byte-identical to the reference; a test pins its hash).

CR-02 is still PROPOSED.  This module makes its logic run inside APG's controls; it does not make any decision the product owner has not made:
  * no threshold, always-material list, aggregation key or window is supplied here - a policy is DATA that a tenant proposes, people approve and APG activates;
  * with no active policy, or a rule with no threshold, the answer is MATERIAL with a visible reason (fail-safe, R2/R3);
  * the eight open decisions DEC-A1-1..8 live in a ledger that only a human product owner can write to; every assessment states which still-open
    decisions its policy leans on, so nobody can mistake a provisional rule set for a settled one.

Identities come from the verified AuthenticatedContext, never from the payload."""
from dataclasses import dataclass
from . import materiality as M
import hashlib
from .canon import digest, deep_copy, canonical, CanonError
from .ports import ConflictError
from .tenancy import screen_payload
from .values import Known, Unknown

POLICY_KIND, APPROVAL_KIND, ACTIVE_KIND, ACTIVE_KEY = 'materiality_policy', 'materiality_approval', 'materiality_active', 'current'
DECISION_KIND, LEDGER_KIND = 'materiality_decision', 'decision_ledger'
NO_ACTIVE = 'M-NO-ACTIVE-POLICY'

# The open decisions from CR-02 Stage 1 rev 2 section 7.  Text is a short label only; the controlling text is the CR-02 document.
DECISIONS = {
    'DEC-A1-1': 'Accept the fail-safe default: until thresholds exist, everything is material (R3)',
    'DEC-A1-2': 'Confirm or amend the always-material list (R4)',
    'DEC-A1-3': 'Approve the explicit all_records rule form and which subject types use it (R3a)',
    'DEC-A1-4': 'Any measure triggers, versus all measures must trigger (R8)',
    'DEC-A1-5': 'Roles and the two-person rule for loosening, including the equivalent class (section 5)',
    'DEC-A1-6': 'Programme materiality for process rows: Option P or Q (section 6) - not applied by this engine',
    'DEC-A1-7': 'Whether suspected inventory rows are corrected before thresholds are written - not applied by this engine',
    'DEC-A1-8': 'Aggregation key list and window, and whether known limitations are acceptable (section 4a)',
}


class PolicyError(ValueError):
    def __init__(self, code, msg=''):
        super().__init__(f'{code}: {msg}')
        self.code = code


def _has(ctx, role):
    return role in ctx.roles


def _need_human(ctx, what):
    if ctx.actor_kind != 'human':
        raise PolicyError('HUMAN_REQUIRED', f'{what} must be done by a human')


# ---------------------------------------------------------------- which open decisions a policy leans on
def decisions_relied_on(policy):
    """-> sorted DEC ids this policy's content depends on.  Pure function of the policy; it never decides anything."""
    deps = {'DEC-A1-5'}                                          # the way any policy is activated
    if not M.policy_valid(policy):
        return sorted(deps)
    for rule in policy['rules'].values():
        st, m = M._rule_state(rule)
        if st == 'unset':
            deps.add('DEC-A1-1')
        if st == 'all':
            deps.add('DEC-A1-3')
        if st == 'ok' and sum(1 for k in ('abs_cents', 'rel_bps', 'delay_days') if k in m) >= 2:
            deps.add('DEC-A1-4')
    if policy.get('always_material'):
        deps.add('DEC-A1-2')
    if 'aggregation' in policy or not policy.get('aggregate', True):
        deps.add('DEC-A1-8')
    if not policy['rules']:
        deps.add('DEC-A1-1')
    return sorted(deps)


# ---------------------------------------------------------------- decision ledger (open until a human product owner records it)
def record_decision(scoped, decision_id, outcome, rationale):
    ctx = scoped.ctx
    if decision_id not in DECISIONS:
        raise PolicyError('UNKNOWN_DECISION', decision_id)
    _need_human(ctx, 'recording a decision')
    if not _has(ctx, 'product_owner'):
        scoped.log('decision.refused', f'{LEDGER_KIND}/{decision_id}', 'refused', reason='not the product owner')
        raise PolicyError('NOT_PRODUCT_OWNER', decision_id)
    if not isinstance(outcome, str) or not outcome.strip() or not isinstance(rationale, str) or not rationale.strip():
        raise PolicyError('DECISION_INCOMPLETE', 'an outcome and a rationale are required')
    rec = scoped.put(LEDGER_KIND, decision_id, {'decision_id': decision_id, 'outcome': outcome, 'rationale': rationale, 'decided_by': ctx.user_id})
    scoped.log('decision.recorded', f'{LEDGER_KIND}/{decision_id}', 'ok', detail={'revision': rec.revision})
    return rec


def decision_status(scoped):
    """-> {DEC id: 'open' | 'decided'}"""
    out = {}
    for d in DECISIONS:
        r = scoped.get(LEDGER_KIND, d)
        out[d] = 'decided' if (r is not None and r.payload.get('decided_by')) else 'open'
    return out


# ---------------------------------------------------------------- policy lifecycle
def baseline_policy():
    """The fail-safe starting point: no rules at all, so nothing can be below any threshold."""
    return {'version': 'BASELINE-FAILSAFE', 'rules': {}, 'always_material': [], 'aggregate': True}


def _load_policy(scoped, version):
    rec = scoped.get(POLICY_KIND, version)
    if rec is None:
        raise PolicyError('POLICY_UNKNOWN', version)
    p = rec.payload
    if digest(p['policy']) != p['policy_digest'] or p['policy'].get('version') != version:
        raise PolicyError('POLICY_TAMPERED', version)
    return p


def propose_policy(scoped, policy):
    """Store a policy version as PROPOSED.  Versions are immutable; the proposer is the authenticated user."""
    ctx = scoped.ctx
    if not M.policy_valid(policy):
        raise PolicyError('POLICY_INVALID', 'not a valid materiality policy')
    for subj, rule in policy['rules'].items():
        if M._rule_state(rule)[0] == 'invalid':
            raise PolicyError('RULE_INVALID', subj)
    payload = {'policy': deep_copy(policy), 'policy_digest': digest(policy), 'proposer': ctx.user_id, 'proposer_kind': ctx.actor_kind}
    try:
        rec = scoped.put(POLICY_KIND, policy['version'], payload, expected_revision=0)
    except ConflictError:
        existing = scoped.get(POLICY_KIND, policy['version'])
        if existing.payload['policy_digest'] == payload['policy_digest']:
            return existing
        raise PolicyError('VERSION_EXISTS', 'that version already exists with different content; use a new version')
    scoped.log('policy.proposed', f'{POLICY_KIND}/{policy["version"]}', 'ok', detail={'digest': payload['policy_digest']})
    return rec


def approve_policy(scoped, version):
    """Record the CALLING user's approval.  The approver and role come from the context; a role the user does not hold cannot be claimed."""
    ctx = scoped.ctx
    p = _load_policy(scoped, version)
    _need_human(ctx, 'approval')
    if ctx.user_id == p['proposer']:
        scoped.log('policy.approval_refused', f'{POLICY_KIND}/{version}', 'refused', reason='proposer cannot approve')
        raise PolicyError('SELF_APPROVAL', version)
    role = 'materiality_owner' if _has(ctx, 'materiality_owner') else ('policy_reviewer' if _has(ctx, 'policy_reviewer') else None)
    if role is None:
        scoped.log('policy.approval_refused', f'{POLICY_KIND}/{version}', 'refused', reason='no approval role')
        raise PolicyError('NO_APPROVAL_ROLE', version)
    _, against, _ = active_policy(scoped)                  # an approval is for a change FROM the policy active now; it goes stale if another policy is activated first
    rec = scoped.put(APPROVAL_KIND, f'{version}|{ctx.user_id}', {'version': version, 'policy_digest': p['policy_digest'], 'approver': ctx.user_id, 'role': role, 'kind': 'human',
                                                                 'against': against or ''})
    scoped.log('policy.approved', f'{APPROVAL_KIND}/{version}|{ctx.user_id}', 'ok', detail={'role': role})
    return rec


def active_policy(scoped):
    """-> (policy dict, version, active revision) or (None, None, 0)."""
    cur = scoped.get(ACTIVE_KIND, ACTIVE_KEY)
    if cur is None:
        return None, None, 0
    p = _load_policy(scoped, cur.payload['version'])
    if cur.payload['policy_digest'] != p['policy_digest']:
        raise PolicyError('ACTIVE_POINTER_TAMPERED', cur.payload['version'])
    return deep_copy(p['policy']), cur.payload['version'], cur.revision


def activate_policy(scoped, version):
    """Make a proposed version the tenant's active policy, if the CR-02 change-control rule is satisfied by the approvals on file for exactly this content."""
    ctx = scoped.ctx
    p = _load_policy(scoped, version)
    old, old_version, rev = active_policy(scoped)
    old_policy = old if old is not None else baseline_policy()
    approvals = []
    for key_rec in scoped.query(APPROVAL_KIND, {'version': version}):
        a = key_rec.payload
        if a['policy_digest'] != p['policy_digest'] or key_rec.key != f"{version}|{a['approver']}" or a.get('against') != (old_version or ''):
            continue                                                      # approval of other content, of a different change, or under a forged key: does not count
        approvals.append({'approver': a['approver'], 'role': a['role'], 'kind': a['kind']})
    change = {'proposer': p['proposer'], 'proposer_kind': p['proposer_kind'], 'approvals': approvals}
    ok, code = M.change_allowed(old_policy, p['policy'], change)
    kind = M.classify_change(old_policy, p['policy'])
    if not ok:
        scoped.log('policy.activation_refused', f'{POLICY_KIND}/{version}', 'refused', reason=code, detail={'change_kind': kind})
        raise PolicyError(code, f'{version}: change is {kind}')
    try:
        scoped.put(ACTIVE_KIND, ACTIVE_KEY, {'version': version, 'policy_digest': p['policy_digest'], 'activated_by': ctx.user_id, 'previous_version': old_version or '', 'change_kind': kind},
                   expected_revision=rev)
    except ConflictError:
        raise PolicyError('ACTIVATION_RACE', 'the active policy changed while this activation was being decided; retry')
    scoped.log('policy.activated', f'{POLICY_KIND}/{version}', 'ok', detail={'change_kind': kind, 'previous': old_version or ''})
    return kind


# ---------------------------------------------------------------- assessment
def _num(v):
    """Known -> int cents; Unknown -> None (so the model reports it missing); anything else unchanged (the model will judge it)."""
    if isinstance(v, Known):
        return v.cents
    if isinstance(v, Unknown):
        return None
    return v


def normalise(record):
    """Convert Known/Unknown values in a record to what the model reads.  An Unknown never becomes a number or a zero."""
    if not isinstance(record, dict):
        return record
    r = dict(record)
    for k in ('amount_cents', 'delay_days'):
        if k in r:
            r[k] = _num(r[k])
    if isinstance(r.get('bases'), dict):
        r['bases'] = {k: _num(v) for k, v in r['bases'].items()}
    return r


@dataclass(frozen=True)
class Assessment:
    key: str
    material: bool
    reasons: tuple
    policy_version: str
    policy_digest: str
    open_decisions: tuple
    stored: dict

    @property
    def settled(self):
        """True only when no open decision underlies the result.  Material-by-fail-safe results are still correct to act on; 'not material' results under open decisions are provisional."""
        return not self.open_decisions


def assess_record(scoped, record, candidates=()):
    ctx = scoped.ctx
    rec, _ = screen_payload(ctx, normalise(record), scoped._audit)
    cands = []
    for c in candidates:
        cc, _ = screen_payload(ctx, normalise(c), scoped._audit)
        cands.append(cc)
    policy, version, _ = active_policy(scoped)
    status = decision_status(scoped)
    if policy is None:
        result = {'material': True, 'reasons': [NO_ACTIVE], 'rule_version': None, 'digest': digest({'record': rec, 'candidates': cands})}
        pol_digest, open_d = '', sorted(d for d, s in status.items() if s == 'open')
    else:
        result = M.assess_with_context(rec, cands, policy)
        pol_digest = digest(policy)
        open_d = [d for d in decisions_relied_on(policy) if status[d] == 'open']
    replayable = True
    try:
        canonical({'record': rec, 'candidates': cands})
    except CanonError:
        # a float, NaN or other unstorable value: the model has already treated it as unusable (material).  Keep an honest, non-replayable trace.
        replayable = False
        shown = repr((rec, cands))
        key = hashlib.sha256((pol_digest + shown).encode('utf-8', 'replace')).hexdigest()[:32]
        rec, cands = {'unstorable_repr': shown[:2000]}, []
        result = {k: result[k] for k in ('material', 'reasons', 'rule_version')}
        result['digest'] = key
    else:
        key = digest({'policy': pol_digest, 'record': rec, 'candidates': cands})[:32]
    payload = {'result': result, 'policy_version': version or '', 'policy_digest': pol_digest, 'record': rec, 'candidates': cands, 'open_decisions': open_d,
               'assessed_by': ctx.user_id, 'model': M.MODEL_VERSION, 'replayable': replayable}
    existing = scoped.get(DECISION_KIND, key)
    stored = existing if existing is not None else scoped.put(DECISION_KIND, key, payload, expected_revision=0)
    if existing is None:
        scoped.log('materiality.assessed', f'{DECISION_KIND}/{key}', 'ok', detail={'material': result['material'], 'reasons': result['reasons']})
    s = stored.payload
    return Assessment(key, s['result']['material'], tuple(s['result']['reasons']), s['policy_version'], s['policy_digest'], tuple(s['open_decisions']), deep_copy(s))


def verify_assessment(scoped, key):
    """Re-run a stored assessment from its stored inputs and the policy version it names.  -> (ok, code)."""
    rec = scoped.get(DECISION_KIND, key)
    if rec is None:
        return False, 'DECISION_MISSING'
    s = rec.payload
    if not s.get('replayable', True):
        return False, 'NOT_REPLAYABLE'
    if digest({'policy': s['policy_digest'], 'record': s['record'], 'candidates': s['candidates']})[:32] != key:
        return False, 'DECISION_INPUTS_ALTERED'
    if s['policy_version'] == '':
        again = {'material': True, 'reasons': [NO_ACTIVE], 'rule_version': None, 'digest': digest({'record': s['record'], 'candidates': s['candidates']})}
    else:
        try:
            p = _load_policy(scoped, s['policy_version'])
        except PolicyError as e:
            return False, e.code
        if p['policy_digest'] != s['policy_digest']:
            return False, 'POLICY_CONTENT_DIFFERS'
        again = M.assess_with_context(s['record'], s['candidates'], p['policy'])
    return (True, '') if digest(again) == digest(s['result']) else (False, 'RESULT_DIFFERS')
