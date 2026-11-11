"""The approval request boundary (APG-M9.1, the first slice of M9; carried-forward item CF-25, gate CF-22; corrected in APG-M9.2).  Blueprint: Section 15 sections 15.4, 15.5, 15.8, 15.11.

`findings.approve_action` is the lifecycle's own entry point: it binds an approval to the finding version, the evidence digest and the proposal that was shown.  A screen or an API needs more around it,
and this module is that "more", as logic with no network, no storage of its own and no clock of its own:

* the request is checked for shape before anything is looked at, and an unknown field is refused (a tenant or an approver named in the request is a claim, never a choice);
* the person must be a human with a live session and the approver role;
* the approver must be authorised for the finding's PROJECT: asked of a `ProjectActionPort` (EDR-31; the real project-permission model is the Engine's decision, see also EDR-29) on every request, replays included;
  a missing port, a port that raises or a port that answers anything but exactly True means refused;
* a finding that does not exist in this tenant and a finding the person may not see give the same answer (NOT_FOUND);
* the request carries a request id; the same request sent again returns the FIRST answer and does nothing twice; the same id with different content, or from another person, is refused (REQUEST_ID_REUSED);
* a request that stopped half way (a crash between the approval and the note of it) is recognised on the next try from the finding's own history and is not approved twice;
* every outcome, replays and refusals included, is written to the audit log with the request id, never with the rationale text;
* the approval's audit entry is written BEFORE the answer is noted under the request id, so an approval whose entry could not be written is not noted as done: the retry recognises the approval and writes the entry (at least once);
* the clock is read ONCE per call, and a clock that cannot be read or that does not say a real UTC moment ends the session (F-63): the call gives its ordinary refusal and is audited best-effort, never an exception, and the one reading is
  what every timestamp of the call and the lifecycle use, so a clock that fails later cannot fail half way through an approval.

What this module does NOT do: it has no HTTP, session or role directory (the Engine's EDR-11 and EDR-20), it does not decide who may approve in which project (EDR-31, EDR-29), it does not execute anything, and nothing here has
been independently reviewed.  Results are plain dictionaries, so an API layer can map them (a suggested mapping is in programme/APPROVAL_REQUEST_BOUNDARY.md, for the Engine's author to accept or replace)."""
import re
from .. import canon
from ..ports import ConflictError, TenantMismatch
from ..det import findings as FD

REQUEST_KIND = 'approval_request'
FIELDS = ('request_id', 'finding_id', 'version', 'digest', 'proposal', 'rationale')
_ID = re.compile(r'[A-Za-z0-9._:\-]{1,128}')                  # used with fullmatch only: `$` would let a final newline through (F-60)
_TIME = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z')          # ASCII digits only, whole string
MAX_RATIONALE = 2000                                      # input-size limit of the boundary (I-81); not a policy value
ACTIONS = ('view', 'approve')
TRANSIENT = ('CONCURRENT_CHANGE',)                        # outcomes that are not final: the same request may be sent again and tried again


class ProjectActionPort:
    """EDR-31 (Engine-owned; the per-action sibling of EDR-29).  `allows(ctx, scope, action)` -> True only if this verified context may `action` ('view' or 'approve') findings of `scope`, where scope is the finding's own
    {'level': 'project', 'project': id} or {'level': 'tenant'}.  It must not raise; anything other than exactly True is a refusal, and so is an exception."""
    def allows(self, ctx, scope, action):
        raise NotImplementedError


def _result(request_id, fid, status, code, message, f=None, **extra):
    r = {'status': status, 'code': code, 'message': message, 'request_id': request_id, 'finding_id': fid}
    if f is not None:
        r.update(finding_status=f.get('status'), finding_version=f.get('version'))
    r.update(extra)
    return r


def _is_id(x):
    return isinstance(x, str) and _ID.fullmatch(x) is not None


def _safe(x):
    return x if _is_id(x) else '-'


def _log_refusal(scoped, event, resource, reason, **kw):
    """The audit entry for a refusal.  A context that no longer verifies cannot write to the tenant's log; the refusal still stands, so a failure here is not raised.  (Entries for a success are
    written without this protection: an approval, a screen or a valid check that cannot be audited is not given.)"""
    try:
        scoped.log(event, resource, 'refused', reason=reason, **kw)
    except Exception:
        pass


def _refuse(scoped, request_id, fid, code, message, why, f=None):
    _log_refusal(scoped, 'approval_request.refused', 'approval_request/' + _safe(request_id), why, detail={'code': code, 'finding': _safe(fid)})
    return _result(_safe(request_id) if _safe(request_id) != '-' else None, _safe(fid) if _safe(fid) != '-' else None, 'refused', code, message, f)


def _shape(request):
    """-> reason text if the request is not well formed, else None."""
    if not isinstance(request, dict):
        return 'the request is not a dictionary'
    if set(request) != set(FIELDS):
        return 'the request must carry exactly ' + ', '.join(FIELDS)
    for k in ('request_id', 'finding_id'):
        if not _is_id(request[k]):
            return k + ' is not a plain identifier of 1 to 128 characters'
    if not FD._is_version(request['version']):
        return 'version is not a whole number of at least 1'
    for k in ('digest', 'proposal'):
        if not (FD._is_digest(request[k]) and len(request[k]) <= 128):
            return k + ' is not a text of 1 to 128 characters'
    r = request['rationale']
    if not (isinstance(r, str) and r.strip() and len(r) <= MAX_RATIONALE):
        return f'rationale is not a text of 1 to {MAX_RATIONALE} characters'
    return None


_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _is_moment(x):
    """True only for a real UTC moment written exactly YYYY-MM-DDTHH:MM:SSZ in ASCII digits: a month 1 to 12, a day the month has in that year (29 February only in a leap year of the Gregorian calendar), hour 0 to 23, minute and second 0 to 59 (a leap second
    is refused), year 0001 to 9999.  A string of the right SHAPE is not enough: 2999-99-99T99:99:99Z has the shape (F-62).  Fixed-width ASCII, so for two such moments the string order is the time order."""
    if not (isinstance(x, str) and _TIME.fullmatch(x)):
        return False
    y, mo, d, h, mi, s = int(x[0:4]), int(x[5:7]), int(x[8:10]), int(x[11:13]), int(x[14:16]), int(x[17:19])
    if not (y >= 1 and 1 <= mo <= 12 and h <= 23 and mi <= 59 and s <= 59):
        return False
    leap = y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
    return 1 <= d <= (29 if mo == 2 and leap else _DAYS[mo - 1])


class _Pinned:
    """The one reading of the clock that a call takes.  It answers that reading every time, so the lifecycle's timestamps are the instant the session was checked and the clock is not asked again (F-63)."""
    __slots__ = ('_t',)

    def __init__(self, t):
        self._t = t

    def now(self):
        return self._t


CLOCK_WHY = 'the clock gave no usable time, so the session could not be checked and is treated as ended'      # the audit reason when the clock fails or does not say a real moment (F-63)


def _check_session(ctx, clock):
    """-> (pinned_clock, None) if the session is live, else (None, why) with why 'clock', 'expiry' or 'ended'.  Never raises an ordinary exception: whatever cannot be read, or is not a real UTC moment, ends the session
    (fail closed).  The session is live only if its expiry is a real moment and strictly later than the present one, which must be a real moment too (F-62).  An interrupt (KeyboardInterrupt, SystemExit) is not caught."""
    try:
        now = clock.now()
    except Exception:
        return None, 'clock'
    try:
        e = ctx.expires_at
    except Exception:
        return None, 'expiry'
    if not _is_moment(now):
        return None, 'clock'
    if not _is_moment(e):
        return None, 'expiry'
    if not e > now:
        return None, 'ended'
    return _Pinned(now), None


def _session_live(ctx, clock):
    """True only if the session is live (see _check_session); False for anything else, including a clock or an expiry that cannot be read."""
    return _check_session(ctx, clock)[0] is not None


def _is_human(ctx):
    try:
        return ctx.actor_kind == 'human'
    except Exception:                                      # a kind that cannot be read is not a person
        return False


def _scope_of(f):
    sig = f.get('signal') if isinstance(f, dict) else None
    sc = sig.get('scope') if isinstance(sig, dict) else None
    if not isinstance(sc, dict):
        return None
    if sc.get('level') == 'project' and isinstance(sc.get('project'), str) and sc['project']:
        return {'level': 'project', 'project': sc['project']}
    if sc.get('level') == 'tenant':
        return {'level': 'tenant'}
    return None


def _allowed(scoped, scopes, f, action):
    """Asked on every request.  Fails closed."""
    sc = _scope_of(f)
    if sc is None or scopes is None:
        return False
    try:
        return scopes.allows(scoped.ctx, dict(sc), action) is True
    except Exception:                                      # a broken port is a refusal, never an approval
        return False


def _find(scoped, fid):
    try:
        rec = scoped.get(FD.KIND, fid)
    except Exception:
        return None
    return rec.payload if rec is not None else None


def present(scoped, scopes, clock, finding_id):
    """What an approval screen shows: the proposal, who wrote it and when, and the token to hand back.  -> a result dictionary with `status` 'shown' or 'refused'.
    The token is given only to a caller who can approve the finding now: the proposal is current and not yet approved, the caller has the approver role, is not the proposer, and the port allows `approve` in the finding's project."""
    ctx = scoped.ctx
    if not _is_id(finding_id):
        return _refuse(scoped, None, finding_id, 'NOT_FOUND', 'no such finding', 'the finding id is not a plain identifier')
    pinned, why = _check_session(ctx, clock) if _is_human(ctx) else (None, 'person')
    if pinned is None:
        return _refuse(scoped, None, finding_id, 'NOT_ALLOWED', 'not allowed', CLOCK_WHY if why == 'clock' else 'a person with a live session is required to view an approval')
    f = _find(scoped, finding_id)
    if f is None or not _allowed(scoped, scopes, f, 'view'):
        return _refuse(scoped, None, finding_id, 'NOT_FOUND', 'no such finding', 'unknown finding or not authorised for its project')
    a = f.get('action') if isinstance(f.get('action'), dict) else {}
    ok_now = FD.approvable(f)[0] is True                 # approvable() answers (bool, why): never test the pair itself
    can = ok_now and FD.APPROVER in ctx.roles and a.get('proposed_by') != ctx.user_id and _allowed(scoped, scopes, f, 'approve')
    r = {'status': 'shown', 'code': 'OK', 'finding_id': finding_id, 'finding_status': f.get('status'), 'finding_version': f.get('version'), 'scope': _scope_of(f),
         'proposal': {'text': a.get('text'), 'proposed_by': a.get('proposed_by'), 'proposed_at': a.get('proposed_at')} if a else None,
         'can_approve': can, 'token': FD.approval_token(f) if can else None}          # the token goes only to a caller who can approve now (F-58)
    scoped.log('approval_request.viewed', 'finding/' + finding_id, 'ok', reason='approval screen data shown', detail={'can_approve': can})
    return r


def _hash(ctx, req):
    return canon.digest({'by': ctx.user_id, 'finding_id': req['finding_id'], 'version': req['version'], 'digest': req['digest'], 'proposal': req['proposal'], 'rationale': req['rationale']})


def _approval_event(f, user, req, start):
    """The history entry proving that this person approved exactly this version, digest and proposal, written AFTER this request was opened (`start` = the length of the finding's history
    then), or None.  An approval made earlier, by another request, is not this request's."""
    if not (isinstance(start, int) and not isinstance(start, bool) and start >= 0):
        return None
    for ev in (f.get('history') or [])[start:]:
        d = ev.get('detail') or {}
        if (ev.get('event') == 'status_change' and ev.get('to') == 'action_approved' and ev.get('actor') == user and d.get('approved_version') == req['version']
                and d.get('approved_digest') == req['digest'] and d.get('proposal_ref') == req['proposal']):
            return ev
    return None


def _approved_result(rid, fid, f, ev, recovered=False):
    a = f.get('action') or {}
    return _result(rid, fid, 'approved', 'OK', 'the action was approved', f, approved_by=ev.get('actor'), approved_at=ev.get('at'),
                   approved_version=a.get('approved_version'), approved_digest=a.get('approved_digest'), approved_proposal=a.get('approved_proposal'), recovered=recovered)


def request_approval(scoped, scopes, clock, request):
    """Approve the proposed action of one finding, once.  -> a result dictionary: status 'approved' or 'refused', a code, and `replayed` True when this is the answer to an earlier identical request.
    Nothing is raised for a bad request.  A crash inside the lifecycle leaves the request open, and sending it again completes or refuses it without approving twice."""
    ctx = scoped.ctx
    why = _shape(request)
    if why:
        return _refuse(scoped, request.get('request_id') if isinstance(request, dict) else None, request.get('finding_id') if isinstance(request, dict) else None, 'REQUEST_MALFORMED', 'the request is not well formed', why)
    rid, fid = request['request_id'], request['finding_id']
    if not _is_human(ctx):
        return _refuse(scoped, rid, fid, 'HUMAN_REQUIRED', 'an approval must be made by a person', 'a person is required')
    pinned, why = _check_session(ctx, clock)
    if pinned is None:
        return _refuse(scoped, rid, fid, 'SESSION_EXPIRED', 'the session has ended', CLOCK_WHY if why == 'clock' else 'the session has expired or carries no valid expiry')
    clock = pinned                                          # from here on the call uses this one reading (F-63)
    if FD.APPROVER not in ctx.roles:
        return _refuse(scoped, rid, fid, 'ROLE_REQUIRED', 'the approver role is required', 'missing role ' + FD.APPROVER)
    f = _find(scoped, fid)
    if f is None or not _allowed(scoped, scopes, f, 'approve'):
        return _refuse(scoped, rid, fid, 'NOT_FOUND', 'no such finding', 'unknown finding or not authorised to approve for its project')
    key = canon.digest({'request_id': rid})[:40]
    h = _hash(ctx, request)
    try:
        rec = scoped.get(REQUEST_KIND, key)
    except Exception:
        return _refuse(scoped, rid, fid, 'REQUEST_UNREADABLE', 'the request record could not be read', 'the request store could not be read')
    if rec is not None:
        p = rec.payload
        if not (isinstance(p, dict) and p.get('request_id') == rid and p.get('request_hash') == h):
            return _refuse(scoped, rid, fid, 'REQUEST_ID_REUSED', 'this request id was used for a different request', 'the request id was used for different content or by another person')
        if p.get('state') == 'done' and isinstance(p.get('result'), dict):
            scoped.log('approval_request.replayed', 'approval_request/' + rid, 'ok', reason='the first answer was returned again', detail={'code': p['result'].get('code'), 'finding': fid})
            return dict(canon.deep_copy(p['result']), replayed=True)
        ev = _approval_event(f, ctx.user_id, request, p.get('history_len'))    # an earlier try stopped half way
        if ev is not None:
            res = _approved_result(rid, fid, f, ev, recovered=True)
            return _finish(scoped, rec, key, rid, fid, h, res, ctx, clock, 'recovered')
    else:
        try:
            rec = scoped.put(REQUEST_KIND, key, {'request_id': rid, 'request_hash': h, 'finding_id': fid, 'by': ctx.user_id, 'at': clock.now(), 'state': 'pending', 'history_len': len(f.get('history') or []), 'result': None}, expected_revision=0)
        except ConflictError:                                            # another copy of the same request got there first
            _log_refusal(scoped, 'approval_request.refused', 'approval_request/' + rid, 'another copy of the same request opened the record first; the request stays open', detail={'code': 'CONCURRENT_CHANGE', 'finding': fid})          # F-59
            return _result(rid, fid, 'refused', 'CONCURRENT_CHANGE', 'the same request is being processed; send it again', f, retry=True)
    try:
        g = FD.approve_action(scoped, clock, fid, request['version'], request['digest'], request['rationale'], approving_proposal=request['proposal'])
    except FD.LifecycleError as e:
        res = _result(rid, fid, 'refused', e.code, str(e), _find(scoped, fid))
        if e.code in TRANSIENT:
            res['retry'] = True
            _log_refusal(scoped, 'approval_request.refused', 'approval_request/' + rid, 'a concurrent change; the request stays open', detail={'code': e.code, 'finding': fid})
            return res
        return _finish(scoped, rec, key, rid, fid, h, res, ctx, clock, 'refused')
    except TenantMismatch:
        res = _result(rid, fid, 'refused', 'TENANT_MISMATCH', 'the request names another tenant', _find(scoped, fid))
        return _finish(scoped, rec, key, rid, fid, h, res, ctx, clock, 'refused')
    ev = _approval_event(g, ctx.user_id, request, len(f.get('history') or []))
    res = _approved_result(rid, fid, g, ev or {'actor': ctx.user_id, 'at': clock.now()})
    return _finish(scoped, rec, key, rid, fid, h, res, ctx, clock, 'accepted')


def _finish(scoped, rec, key, rid, fid, h, res, ctx, clock, kind):
    """Audit an approval, then note the final answer under the request id (so a repeat gets it).  The approval's audit entry comes FIRST and is not protected: if it cannot be written the call raises, the answer is not noted, the request
    stays pending, and the retry recognises the approval from the finding's history and writes the entry (at least once: a crash between the entry and the note can leave two).  A refusal is noted first and audited best-effort."""
    if kind != 'refused':
        scoped.log('approval_request.accepted', 'approval_request/' + rid, 'ok',
                   reason={'accepted': 'the approval was recorded', 'recovered': 'an earlier try had recorded the approval; it was not made again'}[kind], detail={'code': res.get('code'), 'finding': fid})
    cur = scoped.get(REQUEST_KIND, key)
    try:
        scoped.put(REQUEST_KIND, key, {'request_id': rid, 'request_hash': h, 'finding_id': fid, 'by': ctx.user_id, 'at': (cur.payload.get('at') if cur is not None else clock.now()), 'state': 'done', 'history_len': (cur.payload.get('history_len') if cur is not None else None),
                                       'result': canon.deep_copy(res)}, expected_revision=cur.revision if cur is not None else 0)
    except ConflictError:                                              # another copy of this request noted its answer first: that is the answer to the request id, whatever this copy found
        other = scoped.get(REQUEST_KIND, key)
        q = other.payload if other is not None else None
        if isinstance(q, dict) and q.get('request_hash') == h and q.get('state') == 'done' and isinstance(q.get('result'), dict):
            scoped.log('approval_request.replayed', 'approval_request/' + rid, 'ok', reason='another copy of the request had already noted its answer; that answer was returned', detail={'code': q['result'].get('code'), 'finding': fid})
            return dict(canon.deep_copy(q['result']), replayed=True)
    if kind == 'refused':
        _log_refusal(scoped, 'approval_request.refused', 'approval_request/' + rid, 'the lifecycle refused: ' + str(res.get('code')), detail={'code': res.get('code'), 'finding': fid})
    return dict(res, replayed=False)


def check_for_execution(scoped, scopes, clock, finding_id, version, digest, proposal):
    """For whoever carries the action out (outside APG): is the approval still the one in force for exactly this version, evidence digest and proposal?  -> {'valid': bool, 'code': ...}.
    False after the evidence changed, the proposal was replaced or the approval ended, and for anyone not authorised to view the finding."""
    ctx = scoped.ctx
    ok_shape = _is_id(finding_id) and FD._is_version(version) and FD._is_digest(digest) and FD._is_digest(proposal)
    pinned, why = _check_session(ctx, clock) if ok_shape else (None, 'shape')
    if pinned is None:
        _log_refusal(scoped, 'approval_request.execution_check', 'finding/' + _safe(finding_id), CLOCK_WHY if why == 'clock' else 'a malformed call or a session that has ended')          # F-61
        return {'valid': False, 'code': 'NOT_ALLOWED'}
    f = _find(scoped, finding_id)
    if f is None or not _allowed(scoped, scopes, f, 'view'):
        _log_refusal(scoped, 'approval_request.execution_check', 'finding/' + _safe(finding_id), 'unknown finding or not authorised for its project')
        return {'valid': False, 'code': 'NOT_FOUND'}
    a = f.get('action') if isinstance(f.get('action'), dict) else {}
    good = bool(f.get('status') == 'action_approved' and FD.approval_current(f) and a.get('approved_version') == version and a.get('approved_digest') == digest and a.get('approved_proposal') == proposal)
    if good:
        scoped.log('approval_request.execution_check', 'finding/' + finding_id, 'ok', reason='the approval is in force for exactly this version, digest and proposal')
    else:
        _log_refusal(scoped, 'approval_request.execution_check', 'finding/' + finding_id, 'the approval is not in force for what was named')
    return {'valid': good, 'code': 'OK' if good else 'NOT_IN_FORCE'}
