"""Policy approval with provenance (correction release APG-F67, finding F-67).  The financial policy (fin_policy), the detection policy (det_policy), the procurement policy
(mkt_policy) and the specification register (mkt_spec) take the pattern that APG-M7.1 gave the recommendation policy for F-66.  Until now an approval was a dict the caller wrote
(approver, role, kind and date as plain arguments) and a run counted it on its fields alone.

  * A version is PROPOSED by the person storing it: the proposer named in the record must be the verified context's person, the actor must be a person, and the record must arrive
    without approvals.  Storing the same content again is a no-op; any other content under an existing version is refused (a change is a new version).
  * An approval is recorded ONLY by `approve`, from the approver's own verified context: a person holding the owner role, who is not the proposer and has not approved that
    version already.  It appends the approval to the record and writes the audit event '<kind>.approved' under the approver's context.
  * A run counts an approval only when the audit log CONFIRMS it: an event '<kind>.approved' for that version, written under the approver's own verified human context.  The
    gatherers pin the confirmed approvers of every policy they pin in the run parameters ('approvals_confirmed'), so a replay reads the same answer and never the log.
An approval written into a record by any other means (a caller-supplied field, a direct store write) is not confirmed and does not count.  APG cannot stop code outside these
functions from writing the store or the audit log directly; restricting who may write these kinds and their approval events is the Engine's (EDR-34, EDR-39)."""
from . import canon
from .ports import ConflictError

POLICY_KINDS = ('fin_policy', 'det_policy', 'mkt_policy', 'mkt_spec')


def event_type(kind):
    return kind + '.approved'


def _refuse(scoped, kind, version, err, why):
    scoped.log(kind + '.refused', '%s/%s' % (kind, version), 'refused', reason=why)
    raise err(why)


def store(scoped, kind, p, validate, err, label):
    """Store a PROPOSED version.  -> the stored record."""
    bad = validate(p)
    if bad:
        raise err('; '.join(bad))
    ctx = scoped.ctx
    cur = scoped.get(kind, p['version'])
    if cur is not None:
        old = cur.payload
        if p == old or ({k: v for k, v in old.items() if k != 'approvals'} == {k: v for k, v in p.items() if k != 'approvals'} and p['approvals'] == []):
            return cur
        raise err('%s version %s already exists with different content; a change is a new version (approvals are added only through approve_policy by an authorised person)'
                  % (label, p['version']))
    if ctx.actor_kind != 'human':
        _refuse(scoped, kind, p['version'], err, 'a %s is proposed by a person' % label)
    if p['proposer'] != ctx.user_id:
        _refuse(scoped, kind, p['version'], err, 'the proposer must be the person storing the %s (%s), not %r' % (label, ctx.user_id, p['proposer']))
    if p['approvals']:
        _refuse(scoped, kind, p['version'], err, 'a %s is stored without approvals; approvals are recorded only through approve_policy by an authorised person' % label)
    rec = scoped.put(kind, p['version'], p, expected_revision=0)
    scoped.log(kind + '.proposed', '%s/%s' % (kind, p['version']), 'ok')
    return rec


def approve(scoped, clock, kind, role, version, rationale, err, label):
    """The only way an approval is recorded.  -> the approved record's payload (a copy)."""
    ctx = scoped.ctx
    if ctx.actor_kind != 'human' or role not in ctx.roles:
        _refuse(scoped, kind, version, err, 'a %s is approved only by a person with the role %s' % (label, role))
    if not (isinstance(rationale, str) and rationale.strip()):
        raise err('record why the %s is approved' % label)
    cur = scoped.get(kind, version)
    if cur is None:
        raise err('no stored %s version %r' % (label, version))
    p = canon.deep_copy(cur.payload)
    if p['proposer'] == ctx.user_id:
        _refuse(scoped, kind, version, err, 'the proposer cannot approve their own %s' % label)
    if any(a['approver'] == ctx.user_id for a in p['approvals']):
        raise err('%s has already approved this version' % ctx.user_id)
    p['approvals'] = p['approvals'] + [{'approver': ctx.user_id, 'role': role, 'kind': 'human', 'date': clock.now()[:10]}]
    try:
        rec = scoped.put(kind, version, p, expected_revision=cur.revision)
    except ConflictError:
        raise err('the %s changed while it was being approved; read it again' % label)
    scoped.log(event_type(kind), '%s/%s' % (kind, version), 'ok', reason=rationale[:200], detail={'kind': kind, 'version': version, 'approver': ctx.user_id, 'session': ctx.session_id})
    return canon.deep_copy(rec.payload)


def confirmed(scoped, kind, version):
    """-> the people whose approval of (kind, version) the tenant's audit log confirms: an event '<kind>.approved' for that version, written under that person's own verified
    human context.  Sorted."""
    seen = set()
    res = '%s/%s' % (kind, version)
    for e in scoped._audit.read(scoped.ctx):
        d = e.detail or {}
        if e.event_type == event_type(kind) and e.outcome == 'ok' and e.actor_kind == 'human' and e.resource == res and d.get('kind') == kind \
                and d.get('version') == version and d.get('approver') == e.actor:
            seen.add(e.actor)
    return sorted(seen)


def confirmations(scoped, refs):
    """-> {'kind/version': [confirmed approvers]} for every policy record among the pinned refs (each an InputRef or a (kind, key) pair)."""
    out = {}
    for r in refs:
        kind, key = (r.kind, r.key) if hasattr(r, 'kind') else r
        if kind in POLICY_KINDS:
            out['%s/%s' % (kind, key)] = confirmed(scoped, kind, key)
    return out


def counted(p, role, confirmed_approvers):
    """True when a human holding `role`, who is not the proposer, approved this version AND the audit log confirms that person's approval."""
    ok = set(confirmed_approvers or ())
    return any(a['kind'] == 'human' and a['role'] == role and a['approver'] != p['proposer'] and a['approver'] in ok for a in p.get('approvals', []))


def pinned(params, kind, version):
    """The confirmed approvers a run pinned for (kind, version); none if the run pinned none (an approval the run did not confirm does not count)."""
    return list(((params or {}).get('approvals_confirmed') or {}).get('%s/%s' % (kind, version), []))
