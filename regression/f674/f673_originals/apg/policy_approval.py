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
SAME person, with the same identity and role checks, may call `approve` again (as APG-F67.2 below now does it: by recording and confirming a fresh approval, never by
completing the old entry).  Nobody else can do it for them: the event is always written under the caller's own context and names the caller.  `status` reports, per version, which listed approvals are confirmed and which are recorded but not confirmed.  Writing the record and the event in one atomic
step is a property of the Engine's store and audit log (EDR-40); APG does not claim it.

Correction APG-F67.2 (finding F-73): `approve` never completes an approval entry it finds in the caller's name, because it cannot tell an entry it wrote from one written into the
store directly with the same fields.  If the caller has an unconfirmed entry, whoever wrote it, `approve` first writes a revision without it and then a revision with a fresh entry
of its own, and the confirming event names that revision ('revision').  `confirmed` counts an event only if the revision it names is the one that ADDED that person's entry (the
revision lists it and the one before does not).  So every approval that counts was written by `approve` in the same call as its confirming event; a planted entry never counts,
and can only be replaced by the named person approving in person.

Correction APG-F67.3 (finding F-74 and the defect class of F-73 and F-74; I-132): a confirmation counts only while the approval it confirms still HOLDS at the revision being
judged - for a run, the exact revision it pinned.  `holds`: the revision the event names added the person's entry (added_at), and in every revision from that one through the
judged one the person's entry is present and unchanged and the approved content (every field except the approvals) is unchanged.  Adding other people's approvals keeps it;
removing and re-planting the entry, changing it, or rewriting the content breaks it, and a broken confirmation never counts again (the person approves afresh).  Threat model:
whoever can append arbitrary revisions to the store, but cannot write an audit event as another person, rewrite or delete a past revision or audit event, or change what a pinned
revision reads on replay.  Those last guarantees are the store's: apg/contracts/record_store_history_contract.py (EDR-41)."""
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
    """The only way an approval is recorded.  An unconfirmed entry in the caller's name is replaced by a fresh one, never completed (F-72, F-73).  -> the approved record's payload
    (a copy)."""
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
    if mine and ctx.user_id in confirmed(scoped, kind, version):
        raise err('%s has already approved this version' % ctx.user_id)
    try:
        if mine:                                  # F-73: never complete an entry found in the caller's name; remove it (a new revision), whoever wrote it
            p['approvals'] = [a for a in p['approvals'] if a['approver'] != ctx.user_id]
            cur = scoped.put(kind, version, p, expected_revision=cur.revision)
            p = canon.deep_copy(cur.payload)
        p['approvals'] = p['approvals'] + [{'approver': ctx.user_id, 'role': role, 'kind': 'human', 'date': clock.now()[:10]}]
        rec = scoped.put(kind, version, p, expected_revision=cur.revision)
    except ConflictError:
        raise err('the %s changed while it was being approved; read it again' % label)
    _confirm(scoped, kind, version, rationale, err, label, rec.revision, replaced=len(mine))
    return canon.deep_copy(rec.payload)


def _confirm(scoped, kind, version, rationale, err, label, revision, replaced):
    """Write the confirming audit event under the approver's own context, naming the revision `approve` just wrote (F-73).  If the write fails, the approval stays recorded but
    unconfirmed, and the error says so (F-72)."""
    ctx = scoped.ctx
    try:
        scoped.log(event_type(kind), '%s/%s' % (kind, version), 'ok', reason=rationale[:200],
                   detail={'kind': kind, 'version': version, 'approver': ctx.user_id, 'session': ctx.session_id, 'revision': revision, 'replaced_unconfirmed_entries': replaced})
    except Exception as e:
        if _confirmed_after_error(lambda: confirmed(scoped, kind, version), ctx.user_id):
            return                                                          # the event was written although the sink reported an error: the approval is confirmed
        raise _not_confirmed(err)('approval NOT CONFIRMED: the approval by %s of %s %s is recorded in the policy but the audit log does not confirm it (the audit write failed: %s), '
                                  'so it does not count; %s can call approve again, which records and confirms a fresh approval' % (ctx.user_id, label, version, type(e).__name__, ctx.user_id)) from e


def confirmed(scoped, kind, version, at=None):
    """-> the people whose approval of (kind, version) the tenant's audit log confirms at revision `at` (default: the latest): an event '<kind>.approved' for that version, written
    under that person's own verified human context, naming the revision that ADDED that person's entry (APG-F67.2, F-73), and the approval still HOLDS at `at` (APG-F67.3, F-74).
    Sorted."""
    seen = set()
    res = '%s/%s' % (kind, version)
    for e in scoped._audit.read(scoped.ctx):
        d = e.detail or {}
        if e.event_type == event_type(kind) and e.outcome == 'ok' and e.actor_kind == 'human' and e.resource == res and d.get('kind') == kind \
                and d.get('version') == version and d.get('approver') == e.actor and holds(scoped, kind, version, d.get('revision'), e.actor, at):
            seen.add(e.actor)
    return sorted(seen)


def added_at(scoped, kind, version, revision, who):
    """True when `revision` of (kind, version) is the revision that added an entry for `who`: it lists one and the revision before it does not (APG-F67.2, F-73)."""
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        return False
    at = scoped.get(kind, version, revision)
    before = scoped.get(kind, version, revision - 1) if revision > 1 else None
    lists = lambda r: r is not None and any(a.get('approver') == who for a in r.payload.get('approvals', []))
    return lists(at) and not lists(before)


def content(p):
    """The approved content of a policy record: every field except the approvals (APG-F67.3)."""
    return {k: v for k, v in p.items() if k != 'approvals'}


def holds(scoped, kind, version, revision, who, at=None):
    """True when the approval of `who` that the revision `revision` added still holds at revision `at` (default: the latest) (APG-F67.3, F-74): `revision` added the entry
    (added_at), `at` is that revision or a later one, and in every revision from `revision` through `at` the entry is present unchanged and the approved content is unchanged."""
    if not added_at(scoped, kind, version, revision, who):
        return False
    hist = scoped.history(kind, version)
    if at is None:
        at = len(hist)
    if not isinstance(at, int) or isinstance(at, bool) or at < revision or at > len(hist):
        return False
    base = hist[revision - 1].payload
    entries = [a for a in base.get('approvals', []) if a.get('approver') == who]
    approved = content(base)
    for n, r in enumerate(hist[revision - 1:at], start=revision):
        if r.revision != n or content(r.payload) != approved or any(e not in r.payload.get('approvals', []) for e in entries):
            return False
    return True


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
    """-> {'kind/version': [confirmed approvers]} for every policy record among the pinned refs.  An InputRef is judged at the exact revision it pinned (APG-F67.3); a
    (kind, key) pair at the latest."""
    out = {}
    for r in refs:
        kind, key, at = (r.kind, r.key, r.revision) if hasattr(r, 'kind') else (r[0], r[1], None)
        if kind in POLICY_KINDS:
            out['%s/%s' % (kind, key)] = confirmed(scoped, kind, key, at)
    return out


def counted(p, role, confirmed_approvers):
    """True when a human holding `role`, who is not the proposer, approved this version AND the audit log confirms that person's approval."""
    ok = set(confirmed_approvers or ())
    return any(a['kind'] == 'human' and a['role'] == role and a['approver'] != p['proposer'] and a['approver'] in ok for a in p.get('approvals', []))


def pinned(params, kind, version):
    """The confirmed approvers a run pinned for (kind, version); none if the run pinned none (an approval the run did not confirm does not count)."""
    return list(((params or {}).get('approvals_confirmed') or {}).get('%s/%s' % (kind, version), []))
