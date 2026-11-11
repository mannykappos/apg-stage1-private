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
functions from writing the store or the audit log directly; restricting who may write these kinds and their approval events is the Engine's (EDR-34, EDR-39).

Correction APG-F67.1 (finding F-72): `approve` writes the approved revision and then the confirming event.  If the audit write fails in between, the approval is RECORDED in the
policy but NOT CONFIRMED by the log, so it does not count; `approve` then raises an error that says so (an ApprovalNotConfirmed, which is also the record's own error class).  The
SAME person, with the same identity and role checks, may call `approve` again: when the policy already lists their approval and the log does not confirm it, the call writes only the
missing confirming event (it changes no record) and the approval counts from then on.  Nobody else can complete it: the event is always written under the caller's own context and
names the caller.  `status` reports, per version, which listed approvals are confirmed and which are recorded but not confirmed.  Writing the record and the event in one atomic
step is a property of the Engine's store and audit log (EDR-40); APG does not claim it."""
from . import canon
from .ports import ConflictError

POLICY_KINDS = ('fin_policy', 'det_policy', 'mkt_policy', 'mkt_spec')


def event_type(kind):
    return kind + '.approved'


class ApprovalNotConfirmed(Exception):
    """An approval is recorded in the policy but the audit log does not confirm it (the confirming audit write failed).  It does not count.  The same person can call approve again
    to complete it.  Raised as a subclass of the record's own error class as well (see _not_confirmed), so existing callers that catch that class still catch it."""


_NC = {}


def _not_confirmed(err):
    if err not in _NC:
        _NC[err] = type(err.__name__ + 'NotConfirmed', (err, ApprovalNotConfirmed), {})
    return _NC[err]


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
    """The only way an approval is recorded, or (F-72) the same person's recorded but unconfirmed approval completed.  -> the approved record's payload (a copy)."""
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
    mine = [a for a in p['approvals'] if a['approver'] == ctx.user_id]
    if mine:
        if ctx.user_id in confirmed(scoped, kind, version):
            raise err('%s has already approved this version' % ctx.user_id)
        if any(a['role'] != role or a['kind'] != 'human' for a in mine):
            _refuse(scoped, kind, version, err, 'the %s lists an approval in the name of %s that approve did not write; it cannot be completed' % (label, ctx.user_id))
        _confirm(scoped, kind, version, rationale, err, label, completes=True)      # F-72: complete this person's own recorded, unconfirmed approval; no record changes
        return canon.deep_copy(cur.payload)
    p['approvals'] = p['approvals'] + [{'approver': ctx.user_id, 'role': role, 'kind': 'human', 'date': clock.now()[:10]}]
    try:
        rec = scoped.put(kind, version, p, expected_revision=cur.revision)
    except ConflictError:
        raise err('the %s changed while it was being approved; read it again' % label)
    _confirm(scoped, kind, version, rationale, err, label, completes=False)
    return canon.deep_copy(rec.payload)


def _confirm(scoped, kind, version, rationale, err, label, completes):
    """Write the confirming audit event under the approver's own context.  If the write fails, the approval stays recorded but unconfirmed, and the error says so (F-72)."""
    ctx = scoped.ctx
    try:
        scoped.log(event_type(kind), '%s/%s' % (kind, version), 'ok', reason=rationale[:200],
                   detail={'kind': kind, 'version': version, 'approver': ctx.user_id, 'session': ctx.session_id, 'completes_recorded_approval': completes})
    except Exception as e:
        if _confirmed_after_error(lambda: confirmed(scoped, kind, version), ctx.user_id):
            return                                                          # the event was written although the sink reported an error: the approval is confirmed
        raise _not_confirmed(err)('approval NOT CONFIRMED: the approval by %s of %s %s is recorded in the policy but the audit log does not confirm it (the audit write failed: %s), '
                                  'so it does not count; %s can call approve again to complete it' % (ctx.user_id, label, version, type(e).__name__, ctx.user_id)) from e


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


def _confirmed_after_error(read, who):
    """After a failed audit write: does the log, read again, confirm `who`?  A read that fails counts as no (fail closed)."""
    try:
        return who in read()
    except Exception:
        return False


def status(scoped, kind, version):
    """-> what is recorded and what is confirmed for one version: {'version', 'recorded', 'confirmed', 'recorded_not_confirmed'} (sorted approver names), or None if no such
    version.  Only 'confirmed' approvals by a holder of the owner role who is not the proposer count (`counted`)."""
    cur = scoped.get(kind, version)
    if cur is None:
        return None
    rec = sorted({a['approver'] for a in cur.payload.get('approvals', [])})
    ok = set(confirmed(scoped, kind, version))
    return {'version': version, 'recorded': rec, 'confirmed': [a for a in rec if a in ok], 'recorded_not_confirmed': [a for a in rec if a not in ok]}


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
