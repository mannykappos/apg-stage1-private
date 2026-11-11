"""Recommendations: the stored, owned, audited form of a recommendation run.  Blueprint: Section 10 sections 5 (keep a recommendation, an approved action and a verified outcome distinct),
9 (human approval and action boundaries; the ten states), 10 (outcome tracking; history reconstructable), PG-RS-AC-08 to 12; Section 02 section 7 (no autonomous consequential external action).

One record per finding: `recommendation/<rec id>`.  The recommendation service (`ingest_run`, a service identity with the role recommendation_service) may only create a record as `generated`,
refresh what the latest verified run says, give it a new VERSION when the run says something material changed (engine.state_digest), end a submission or an approval that no longer matches the
current version, and end a deferral whose date has come.  Every other change is a person's act with a role and a reason:

  generated              -> awaiting_evidence | awaiting_approval | deferred | closed_without_implementation      (recommendation_owner)
  awaiting_evidence      -> generated | deferred | closed_without_implementation                                   (recommendation_owner)
  awaiting_approval      -> approved | rejected                       (the approval role the policy band names for the amount; not the submitter, not the author of the inputs)
  awaiting_approval      -> generated                                 (recommendation_owner withdraws it)
  deferred               -> generated | closed_without_implementation (recommendation_owner)
  rejected               -> closed_without_implementation             (recommendation_owner)
  approved               -> in_progress | closed_without_implementation   (recommendation_owner; in_progress records that PEOPLE started the action outside APG)
  in_progress            -> completed_pending_verification | closed_without_implementation   (recommendation_owner; completion names the implementation evidence)
  completed_pending_verification -> verified_outcome                  (benefit_verifier through rec/verify.py only)

Source freshness (correction APG-M7.1, findings F-64 and F-65): a recommendation is a snapshot of a run.  Submission, approval and the start of work each check first that the finding, its
overlapping findings, its inputs and reviews and its policy are still exactly what that run read, and that a run now would give the same recommendation (`source_check`).  If anything changed
the act is refused (SOURCE_CHANGED) until the engine runs again and people review the new version.
The check and the act commit together (corrections APG-M7.2 and APG-M7.3, findings F-68 and F-69): the check returns a store guard for everything it read, and the act is written in ONE
atomic store batch with those guards (`_commit_checked`).  For each kind the check reads by query (findings, recommendation inputs) the guard is the exact set of (key, revision) the query
returned, so a record added, changed or removed in between fails the batch; for each record read by key (the run, the policy, the pinned records) it is the exact revision, 0 for a record that
was absent.  A guard writes nothing.  If any guard no longer holds, nothing is recorded and the act is refused.  Once the batch has committed, the act took effect with exactly the sources it
was checked against; a change after that is a later change, refused at the next checked act and ending submissions and approvals at the next run, as any other later change.
Submission is gated: only a recommendation routed `action`, with every incremental cost estimated, every mandatory review recorded and cleared, an approval authority, and (for a material decision)
a complete alternative, can be submitted.  A high rank never opens the gate (PG-RS-AC-05).
Approval is bound to the version, its digest and the submission (as the M6.1 to M6.5 corrections bound finding approvals): the approver names all three (`approval_token`) and the call refuses a
stale or partial token.  Approval is a decision, not an execution: no function here or anywhere in apg/rec carries out an action (`execute` refuses, always).
History is append-only inside the record; every write is also an audit event; rejected, deferred, withdrawn and closed recommendations stay stored with their reasons (PG-RS-AC-11)."""
from .. import canon, repro
from ..det import findings as FD
from ..ports import ConflictError, Guard
from . import engine as E, inputs as IN, policy as RP

KIND = 'recommendation'
INGEST_KIND = 'rec_ingest'
SERVICE = 'recommendation_service'
OWNER = IN.OWNER
VERIFIER = 'benefit_verifier'
STATUSES = ('generated', 'awaiting_evidence', 'awaiting_approval', 'approved', 'rejected', 'deferred', 'in_progress', 'completed_pending_verification', 'verified_outcome',
            'closed_without_implementation')
OWNER_MOVES = {('generated', 'awaiting_evidence'), ('generated', 'awaiting_approval'), ('generated', 'deferred'), ('generated', 'closed_without_implementation'),
               ('awaiting_evidence', 'generated'), ('awaiting_evidence', 'deferred'), ('awaiting_evidence', 'closed_without_implementation'),
               ('awaiting_approval', 'generated'), ('deferred', 'generated'), ('deferred', 'closed_without_implementation'), ('rejected', 'closed_without_implementation'),
               ('approved', 'in_progress'), ('approved', 'closed_without_implementation'), ('in_progress', 'completed_pending_verification'), ('in_progress', 'closed_without_implementation')}
DECIDER_MOVES = {('awaiting_approval', 'approved'), ('awaiting_approval', 'rejected')}
NEEDS_RATIONALE = ('awaiting_evidence', 'deferred', 'rejected', 'approved', 'closed_without_implementation', 'generated')
TERMINAL = ('verified_outcome', 'closed_without_implementation')


class RecError(ValueError):
    def __init__(self, code, msg=''):
        super().__init__(f'{code}: {msg}')
        self.code = code


def _text(v):
    return isinstance(v, str) and bool(v.strip())


def _is_version(x):
    return isinstance(x, int) and not isinstance(x, bool) and x >= 1


def _event(r, scoped, clock, event, frm=None, to=None, detail=None, actor_kind=None):
    ctx = scoped.ctx
    r['history'].append({'seq': len(r['history']) + 1, 'at': clock.now(), 'actor': ctx.user_id, 'actor_kind': actor_kind or ctx.actor_kind, 'event': event, 'from': frm, 'to': to,
                         'version': r['version'], 'detail': detail or {}})


def _load(scoped, rid):
    rec = scoped.get(KIND, rid)
    if rec is None:
        raise RecError('RECOMMENDATION_UNKNOWN', rid)
    return rec


def _put(scoped, rec, r):
    try:
        return scoped.put(KIND, r['rec_id'], r, expected_revision=rec.revision)
    except ConflictError:
        raise RecError('CONCURRENT_CHANGE', r['rec_id'] + ' changed while this was being decided; read it again')


def _refuse(scoped, rid, code, why):
    scoped.log('rec.refused', f'{KIND}/{rid}', 'refused', reason=why[:200])
    raise RecError(code, why)


def _need_human(scoped, rid, what):
    if scoped.ctx.actor_kind != 'human':
        _refuse(scoped, rid, 'HUMAN_REQUIRED', what + ' must be done by a person')


def submission_ref(r):
    s = r.get('submission')
    if not isinstance(s, dict) or not _is_version(s.get('version')) or not _text(s.get('digest')) or not _text(s.get('by')) or not _text(s.get('at')):
        return None
    return canon.digest({'by': s['by'], 'at': s['at'], 'version': s['version'], 'digest': s['digest'], 'n': s.get('n', 0)})[:24]


def submission_current(r):
    s = r.get('submission')
    return bool(isinstance(s, dict) and s.get('state') == 'current' and s.get('version') == r['version'] and _is_version(r['version']) and s.get('digest') == r['current']['state_digest']
                and _text(s.get('digest')))


def approval_current(r):
    a = r.get('approval')
    return bool(isinstance(a, dict) and a.get('state') == 'current' and a.get('version') == r['version'] and _is_version(a.get('version')) and a.get('digest') == r['current']['state_digest']
                and _text(a.get('digest')) and submission_current(r) and a.get('submission') == submission_ref(r) and submission_ref(r) is not None)


def approval_token(r):
    """What an approval screen shows and hands back: the recommendation, its version, its digest and the reference of the submission on record."""
    return {'rec_id': r['rec_id'], 'version': r['version'], 'digest': r['current']['state_digest'], 'submission': submission_ref(r)}


def _end(r, which, at, because):
    """Move a current submission or approval into its history."""
    x = r.get(which)
    if not isinstance(x, dict) or x.get('state') != 'current':
        return None
    r[which + '_history'] = list(r.get(which + '_history', [])) + [dict(x, state='ended', ended_at=at, ended_because=because, ended_at_version=r['version'])]
    r[which] = dict(x, state='ended')
    return r[which + '_history'][-1]


# ---------------------------------------------------------------- the service side
def _new(entry, run_key, as_of, policy):
    return {'rec_id': entry['rec_id'], 'finding_id': entry['finding_id'], 'status': 'generated', 'version': 1, 'current': canon.deep_copy(entry), 'run_key': run_key, 'as_of': as_of,
            'policy': canon.deep_copy(policy), 'versions': [{'version': 1, 'run_key': run_key, 'state_digest': entry['state_digest'], 'as_of': as_of}], 'history': [], 'submission': None,
            'approval': None, 'deferral': None, 'implementation': None, 'outcome': None, 'closure': None}


def ingest_run(scoped, clock, reg, run_key):
    """Turn one stored, verified recommendation run into recommendation records.  -> summary (also stored under rec_ingest/<run key>)."""
    ctx = scoped.ctx
    if SERVICE not in ctx.roles or ctx.actor_kind != 'service':
        scoped.log('rec.refused', INGEST_KIND + '/' + run_key, 'refused', reason='ingesting a recommendation run is a service act')
        raise RecError('SERVICE_REQUIRED', 'only a service identity with the role recommendation_service ingests recommendation runs')
    prior = scoped.get(INGEST_KIND, run_key)
    if prior is not None:
        out = canon.deep_copy(prior.payload)
        out['replay'] = True
        return out
    chk = E.check_record(scoped, reg, run_key)
    if not chk['replay'].ok or not chk['pins_consistent'] or not chk['is_rec_run']:
        scoped.log('rec.ingest_refused', INGEST_KIND + '/' + run_key, 'refused', reason='the run does not verify: ' + (chk['replay'].code or 'pins or formula'))
        raise RecError('RUN_DOES_NOT_VERIFY', chk['replay'].code or 'pins or formula')
    p = scoped.get(repro.KIND, run_key).payload
    res, as_of = p['result'], p['result']['as_of']
    existing = {r.key: r for r in scoped.query(KIND)}
    ops = []
    summary = {'run_key': run_key, 'as_of': as_of, 'created': [], 'new_version': [], 'refreshed': [], 'submissions_ended': [], 'approvals_ended': [], 'deferrals_ended': [],
               'ignored_older': [], 'terminal_unchanged': [], 'finding_excluded': [], 'replay': False}
    for entry in res['recommendations']:
        rid = entry['rec_id']
        rec = existing.get(rid)
        if rec is None:
            r = _new(entry, run_key, as_of, res['policy'])
            _event(r, scoped, clock, 'generated', None, 'generated', {'run_key': run_key, 'route': entry['route'], 'category': entry['category'], 'rank': entry['rank']})
            ops.append((KIND, rid, r, 0))
            summary['created'].append(rid)
            continue
        r = canon.deep_copy(rec.payload)
        if as_of < r['as_of']:
            summary['ignored_older'].append(rid)
            continue
        if r['status'] in TERMINAL:
            r['latest_run'] = {'run_key': run_key, 'as_of': as_of, 'route': entry['route']}
            ops.append((KIND, rid, r, rec.revision))
            summary['terminal_unchanged'].append(rid)
            continue
        material = entry['state_digest'] != r['current']['state_digest']
        r['current'], r['run_key'], r['as_of'], r['policy'] = canon.deep_copy(entry), run_key, as_of, canon.deep_copy(res['policy'])
        if material:
            r['version'] += 1
            r['versions'].append({'version': r['version'], 'run_key': run_key, 'state_digest': entry['state_digest'], 'as_of': as_of})
            _event(r, scoped, clock, 'new_version', r['status'], r['status'], {'run_key': run_key, 'state_digest': entry['state_digest']}, actor_kind='service')
            summary['new_version'].append(rid)
            ended_s = _end(r, 'submission', clock.now(), 'the recommendation changed after it was submitted')
            ended_a = _end(r, 'approval', clock.now(), 'the recommendation changed after it was approved')
            if ended_s:
                summary['submissions_ended'].append(rid)
            if ended_a:
                summary['approvals_ended'].append(rid)
            if r['status'] in ('awaiting_approval', 'approved'):
                frm = r['status']
                r['status'] = 'generated'
                _event(r, scoped, clock, 'status_change', frm, 'generated', {'why': 'the recommendation changed (new version %d); it must be submitted and approved again' % r['version']}, actor_kind='service')
            elif r['status'] == 'in_progress' and ended_a:
                _event(r, scoped, clock, 'approval_ended_while_in_progress', 'in_progress', 'in_progress', {'why': 'the evidence changed after people started the action; the approval no longer matches it'}, actor_kind='service')
        else:
            summary['refreshed'].append(rid)
        d = r.get('deferral')
        if r['status'] == 'deferred' and isinstance(d, dict) and d.get('until') and as_of >= d['until']:
            r['status'] = 'generated'
            _event(r, scoped, clock, 'status_change', 'deferred', 'generated', {'why': 'the deferral date %s has come' % d['until']}, actor_kind='service')
            summary['deferrals_ended'].append(rid)
        ops.append((KIND, rid, r, rec.revision))
    for x in res['excluded']:
        rec = existing.get(x['rec_id'])
        if rec is not None and rec.payload.get('excluded_since') is None:
            r = canon.deep_copy(rec.payload)
            r['excluded_since'] = {'run_key': run_key, 'as_of': as_of, 'why': x['why']}
            _event(r, scoped, clock, 'finding_excluded', r['status'], r['status'], {'why': x['why']}, actor_kind='service')
            ops.append((KIND, x['rec_id'], r, rec.revision))
            summary['finding_excluded'].append(x['rec_id'])
    ops.append((INGEST_KIND, run_key, summary, 0))
    try:
        scoped.atomic(ops)
    except ConflictError:
        raise RecError('CONCURRENT_CHANGE', 'a recommendation changed while the run was being ingested; nothing was written; retry')
    scoped.log('rec.ingested', INGEST_KIND + '/' + run_key, 'ok', detail={k: len(v) for k, v in summary.items() if isinstance(v, list)})
    return canon.deep_copy(summary)


# ---------------------------------------------------------------- source freshness (finding F-64, F-65; correction APG-M7.1)
SOURCE_CHECKED = ('awaiting_approval', 'approved', 'in_progress')


def source_check(scoped, r, guards=None):
    """-> the reasons a recommendation no longer matches its sources (empty = it does).  Two checks, both fail-closed:
      1. EXACT: the recommendation's finding, every finding of its overlap component, its inputs (costs, alternatives, reviews, evidence assessments) and its policy are each at exactly the
         revision the run that produced the current version pinned (a record that was absent then must still be absent);
      2. RECOMPUTED: the engine, run in memory on the records as they are now, with the same date and policy, still gives this recommendation the same state digest (this also catches a new
         finding that joined its overlap component, or a policy approval that is no longer confirmed).
    Anything that cannot be checked counts as a change.
    guards: if a list is given, a store guard for everything the check read is appended to it; `_commit_checked` commits the act only if every one of them still holds."""
    why = []
    held = guards if guards is not None else []
    try:
        run = scoped.get(repro.KIND, r['run_key'])
        held.append(Guard('revision', repro.KIND, r['run_key'], run.revision if run is not None else 0))
        if run is None:
            return ['the run that produced this version is missing']
        pinned = {(i['kind'], i['key']): i['revision'] for i in run.payload['inputs']}
        params = run.payload['params']
        c = r['current']
        keys = [(FD.KIND, m) for m in c['overlap']['members']] + [(IN.KIND, r['rec_id']), (RP.POLICY_KIND, params['policy'])]
        names = {FD.KIND: 'finding', IN.KIND: 'the recommendation inputs (costs, alternatives, reviews or evidence assessments)', RP.POLICY_KIND: 'the recommendation policy'}
        for kind, key in keys:
            now = scoped.get(kind, key)
            held.append(Guard('revision', kind, key, now.revision if now is not None else 0))
            have, then = (now.revision if now is not None else None), pinned.get((kind, key))
            if have != then:
                label = names[kind] if kind != FD.KIND else ('the finding %s' % key if key == r['finding_id'] else 'the overlapping finding %s' % key)
                why.append('%s changed since the run (revision %s then, %s now)' % (label, then if then is not None else 'absent', have if have is not None else 'absent'))
        cur = E.current_inputs(scoped, params['policy'], held)
        pol = cur.get(RP.POLICY_KIND + '/' + params['policy'])
        p2 = dict(params, policy_verified_approvers=RP.verified_approvers(scoped, pol) if pol else [])
        res = E.compute(cur, p2)
        mine = [e for e in res['recommendations'] if e['rec_id'] == r['rec_id']]
        if not mine:
            why.append('the finding is no longer recommended on (it is dismissed, superseded or out of scope now)')
        elif mine[0]['state_digest'] != c['state_digest']:
            why.append('a run now would give this recommendation different content (route %s, category %s)' % (mine[0]['route'], mine[0]['category']))
    except Exception as e:                                                  # fail closed: a check that cannot be completed is a refusal
        why.append('the sources could not be checked (%s)' % type(e).__name__)
    return why


# ---------------------------------------------------------------- people's acts
def _submit_gate(r):
    c = r['current']
    why = []
    if c['route'] != 'action':
        why.append('the recommendation is routed %s, not action' % c['route'])
    why += c['constraints']['blocked_by']
    if c['dimensions']['implementation_cost']['status'] != 'estimated' and 'incremental costs not estimated' not in why:
        why.append('incremental costs not estimated')
    if c['constraints']['action_kind'] is None:
        why.append('the kind of action is not stated')
    if not c['scenarios']['complete'] and 'scenario comparison incomplete' not in why:
        why.append('scenario comparison incomplete')
    return why


def transition(scoped, clock, rid, to, rationale='', evidence_refs=(), until='', approving_version=None, approving_digest=None, approving_submission=None):
    ctx = scoped.ctx
    what = f'{KIND}/{rid}'
    _need_human(scoped, rid, 'a recommendation status change')
    if to not in STATUSES:
        raise RecError('UNKNOWN_STATUS', str(to))
    if to == 'verified_outcome':
        _refuse(scoped, rid, 'USE_VERIFICATION', 'a verified outcome is recorded only through the verification gate (rec/verify.py)')
    rec = _load(scoped, rid)
    r = canon.deep_copy(rec.payload)
    frm = r['status']
    if frm in TERMINAL:
        _refuse(scoped, rid, 'TERMINAL', 'a %s recommendation is kept for audit and cannot change' % frm.replace('_', ' '))
    if (frm, to) in OWNER_MOVES:
        role = OWNER
    elif (frm, to) in DECIDER_MOVES:
        role = r['current']['constraints']['approval_role']
        if role is None:
            _refuse(scoped, rid, 'AUTHORITY_NOT_CONFIGURED', 'no approval role is configured for this amount')
    else:
        _refuse(scoped, rid, 'TRANSITION_NOT_ALLOWED', f'{frm} -> {to}')
    if role not in ctx.roles:
        _refuse(scoped, rid, 'ROLE_REQUIRED', f'{frm} -> {to} needs the role {role}')
    if to in NEEDS_RATIONALE and not _text(rationale):
        raise RecError('RATIONALE_REQUIRED', f'{frm} -> {to} must record why')
    guards = []
    if to in SOURCE_CHECKED:
        stale = source_check(scoped, r, guards)
        if stale:
            _refuse(scoped, rid, 'SOURCE_CHANGED', 'the recommendation no longer matches its sources: %s. Run the recommendation engine again and review the new version' % '; '.join(stale))
    detail = {'rationale': rationale}
    if to == 'awaiting_approval':
        why = _submit_gate(r)
        if why:
            _refuse(scoped, rid, 'NOT_SUBMITTABLE', '; '.join(why))
        n = len(r.get('submission_history', []))
        r['submission'] = {'by': ctx.user_id, 'at': clock.now(), 'version': r['version'], 'digest': r['current']['state_digest'], 'state': 'current', 'n': n,
                           'inputs_author': r['current'].get('inputs_author')}
        detail['submission'] = submission_ref(r)
    if to in ('approved', 'rejected'):
        s = r.get('submission') or {}
        if ctx.user_id == s.get('by'):
            _refuse(scoped, rid, 'SELF_APPROVAL', 'the person who submitted the recommendation cannot decide it')
        if ctx.user_id == s.get('inputs_author'):
            _refuse(scoped, rid, 'SELF_APPROVAL', 'the person who wrote the recommendation inputs cannot decide it')
        if to == 'approved':
            if not (_is_version(approving_version) and _text(approving_digest) and _text(approving_submission)):
                _refuse(scoped, rid, 'APPROVAL_TOKEN_REQUIRED', 'name the version, digest and submission you were shown (approval_token)')
            if approving_version != r['version'] or approving_digest != r['current']['state_digest']:
                _refuse(scoped, rid, 'STALE_APPROVAL', 'the recommendation is now at version %d; read it again' % r['version'])
            if not submission_current(r) or approving_submission != submission_ref(r):
                _refuse(scoped, rid, 'SUBMISSION_CHANGED', 'the submission on record is not the one you were shown; read it again')
            why = _submit_gate(r)
            if why:
                _refuse(scoped, rid, 'NOT_APPROVABLE', '; '.join(why))
            r['approval'] = {'by': ctx.user_id, 'role': role, 'at': clock.now(), 'version': r['version'], 'digest': r['current']['state_digest'], 'submission': submission_ref(r), 'state': 'current',
                             'rationale': rationale, 'expected': {'net_benefit_cents': r['current']['dimensions']['net_benefit']['cents'],
                                                                  'expected_benefit_cents': r['current']['dimensions']['expected_benefit']['cents'],
                                                                  'incremental_cost_cents': r['current']['dimensions']['implementation_cost']['cents']},
                             'note': 'an approval is a decision; it does not prove that any predicted outcome will be achieved'}
            detail.update(approved_version=r['version'], digest=r['current']['state_digest'])
        else:
            _end(r, 'submission', clock.now(), 'rejected')
            r['decision'] = {'decision': 'rejected', 'by': ctx.user_id, 'at': clock.now(), 'rationale': rationale, 'version': r['version']}
    if frm == 'awaiting_approval' and to == 'generated':
        _end(r, 'submission', clock.now(), 'withdrawn by the owner')
    if to == 'deferred':
        if not E._readable(until):
            raise RecError('DATE_REQUIRED', 'a deferral needs a real date (YYYY-MM-DD)')
        r['deferral'] = {'until': until, 'by': ctx.user_id, 'at': clock.now(), 'rationale': rationale}
        detail['until'] = until
    if to == 'in_progress':
        if not approval_current(r):
            _refuse(scoped, rid, 'APPROVAL_NOT_CURRENT', 'the approval no longer stands for this version; it must be submitted and approved again')
        r['implementation'] = {'started_by': ctx.user_id, 'started_at': clock.now(), 'note': 'people carry out the action in the builder\'s own systems; APG records that it started',
                               'evidence_refs': [], 'completed_at': None}
    if to == 'completed_pending_verification':
        refs = [x for x in evidence_refs]
        bad = [x for x in refs if not (isinstance(x, (list, tuple)) and len(x) == 3 and _text(x[0]) and _text(x[1]) and _is_version(x[2]) and scoped.get(x[0], x[1], x[2]) is not None)]
        if not refs or bad:
            _refuse(scoped, rid, 'IMPLEMENTATION_EVIDENCE_REQUIRED', 'name at least one stored record (kind, key, revision) that shows the action was carried out')
        r['implementation'] = dict(r['implementation'] or {}, completed_by=ctx.user_id, completed_at=clock.now(), evidence_refs=[[k, key, rev, scoped.get(k, key, rev).payload_hash] for k, key, rev in refs])
        detail['evidence_refs'] = [list(x) for x in refs]
    if to == 'closed_without_implementation':
        r['closure'] = {'by': ctx.user_id, 'at': clock.now(), 'rationale': rationale, 'from': frm}
        _end(r, 'submission', clock.now(), 'closed')
        _end(r, 'approval', clock.now(), 'closed without implementation')
    r['status'] = to
    _event(r, scoped, clock, 'status_change', frm, to, detail)
    if to in SOURCE_CHECKED:
        _commit_checked(scoped, rec, r, guards)
    else:
        _put(scoped, rec, r)
    scoped.log('rec.transition', what, 'ok', reason=rationale[:200], detail={'from': frm, 'to': to})
    return r


def _commit_checked(scoped, rec, r, guards):
    """Records a source-checked act (submission, approval, start of work) in ONE atomic store batch together with the guards its check returned (F-68, F-69).
    If any guard no longer holds (a record the check read was changed, added or removed), the batch fails, nothing is recorded and the act is refused: SOURCE_CHANGED when the recommendation
    no longer matches its sources (the engine must run again), otherwise CONCURRENT_CHANGE (another change landed meanwhile; read it again)."""
    rid = r['rec_id']
    try:
        scoped.atomic(list(guards) + [(KIND, rid, r, rec.revision)])
    except ConflictError:
        stale = source_check(scoped, r)
        if stale:
            _refuse(scoped, rid, 'SOURCE_CHANGED', 'a source changed while this was being decided, so nothing was recorded: %s. Run the recommendation engine again and review the new version'
                    % '; '.join(stale))
        raise RecError('CONCURRENT_CHANGE', rid + ' or a record it depends on changed while this was being decided; nothing was recorded; read it again')


def submit(scoped, clock, rid, rationale='submitted for approval'):
    return transition(scoped, clock, rid, 'awaiting_approval', rationale=rationale)


def approve(scoped, clock, rid, approving_version, approving_digest, approving_submission, rationale):
    if not (_is_version(approving_version) and _text(approving_digest) and _text(approving_submission)):
        _refuse(scoped, rid, 'APPROVAL_TOKEN_REQUIRED', 'name the version, digest and submission you were shown (approval_token)')
    return transition(scoped, clock, rid, 'approved', rationale=rationale, approving_version=approving_version, approving_digest=approving_digest, approving_submission=approving_submission)


def execute(scoped, rid, *args, **kwargs):
    """Refused, always.  APG must not autonomously execute consequential external actions (Section 02 section 7, Section 10 section 9): people carry out an approved action in their own systems."""
    scoped.log('rec.refused', f'{KIND}/{rid}', 'refused', reason='APG carries out no action')
    raise RecError('NO_AUTONOMOUS_EXECUTION', 'APG records decisions; it does not place orders, issue contracts, claims or variations, change suppliers or substitute materials')


def get(scoped, rid):
    return canon.deep_copy(_load(scoped, rid).payload)


def all_recs(scoped, status=None):
    out = [canon.deep_copy(r.payload) for r in scoped.query(KIND)]
    return [r for r in out if status is None or r['status'] == status]


def reconstruct(scoped, reg, rid, version):
    """Rebuild a past version of a recommendation from the run that produced it: replay the run from its pinned inputs and return that recommendation's entry as the run computed it, with whether it
    matches the digest recorded for the version (PG-RS-AC-12)."""
    r = get(scoped, rid)
    v = [x for x in r['versions'] if x['version'] == version]
    if not v:
        raise RecError('VERSION_UNKNOWN', '%s has no version %r' % (rid, version))
    chk = E.check_record(scoped, reg, v[0]['run_key'])
    p = scoped.get(repro.KIND, v[0]['run_key']).payload
    entry = [e for e in p['result']['recommendations'] if e['rec_id'] == rid][0]
    return {'replay_ok': chk['replay'].ok, 'replay_code': chk['replay'].code, 'entry': entry, 'matches_recorded_digest': entry['state_digest'] == v[0]['state_digest'],
            'rank_in_that_run': entry['rank'], 'rank_order': p['result']['rank_order'], 'policy': p['result']['policy']}
