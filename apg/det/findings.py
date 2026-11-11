"""Findings: the stored, owned, audited form of a signal.  Blueprint: Section 06 sections 6 (finding contract), 9 (deduplication, relationships), 9.1 (alert noise), 11 (lifecycle
and human review), PG-AI-AC-05, 07, 09, 13, 14, 16.

A SIGNAL is what a rule says in one run.  A FINDING is the one record per condition (identity = rule, scope, subject) that people review.  Detection (`ingest_run`) may only:
create a finding as 'detected', update its signal and history, mark it seen, note that it was not re-detected, and REOPEN a resolved or dismissed finding when material new evidence
arrives.  It can never confirm, dismiss, approve, resolve or supersede: those are people's acts (`transition`), each needing a human, the right role and a recorded rationale.

Lifecycle (the ten statuses of Section 06 section 6):
  detected -> under_review -> confirmed | dismissed;  confirmed -> action_proposed -> action_approved -> in_progress -> resolved;  resolved or dismissed -> reopened -> under_review;
  any status except superseded -> superseded (names the finding that replaces it).
  Separation of duties: the person who approves an action is not the person who proposed it; nothing in APG carries out an action, it only records the decision.
  An approval is bound to the finding version and the evidence digest that were approved (correction APG-M6.1, finding F-52).  If detection later changes the evidence (a new state digest) the
  approval is ended by the service, the finding returns to `action_proposed` and a person must approve again; the ended approval stays in `action['approval_history']`.  No status is added.
  A proposal is bound the same way (correction APG-M6.2, finding F-53): it records the version and digest it was written against, and an action can only be approved while that proposal is
  current.  If the evidence has moved since the proposal was written, approval is refused (STALE_PROPOSAL) whether or not the approver names a version; a reviewer sends the finding back to
  `confirmed` and the owner proposes again.  A replaced proposal is kept in full in `action['proposal_history']`.  Versions and digests are checked strictly (finding F-55, correction APG-M6.3): a stored or named version must be a whole number of at least 1 and not a boolean, a digest a non-empty text; a value that merely equals one under Python's rules (`True`, `1.0`) is never accepted.  `approve_action` is the entry point for screens and APIs: it refuses to act
  without the version and digest the approver was shown.
  An approval is bound to the exact proposal that was shown (finding F-56, correction APG-M6.4): the token also carries `proposal_ref` (a reference to the proposal on record: its text, proposer,
  time, the version and digest it was written against, and how many proposals it replaced); an approval that names another reference is refused (PROPOSAL_CHANGED) and the reference of the
  proposal that was approved is kept in the record.
  The gate is in the lowest-level call (finding F-57, correction APG-M6.5, found by the independent audit of M6.4): `transition(..., 'action_approved', ...)` itself refuses an approval that does not name the
  version, the evidence digest and the proposal reference, each well formed (APPROVAL_TOKEN_REQUIRED), so no path records an approval without all three; `approve_action` is the entry point that says so first.
  Starting the action (`in_progress`) re-checks that the approval is still in force for the proposal and evidence on record (APPROVAL_NOT_CURRENT).
  No path leads to a verified realised saving: that needs the Section 05 verification, which is not built in this milestone (`claim_realised` refuses).

History and notification history are append-only lists inside the record; every write is also an audit event.  A detection run that was already ingested is a no-op (event replay);
a run whose as-of date is older than what the finding has already seen is ignored (out-of-order delivery)."""
from .. import canon, repro
from ..ports import ConflictError
from . import noise, policy as DP, signal as S

KIND = 'finding'
INGEST_KIND = 'det_ingest'
STATUSES = ('detected', 'under_review', 'confirmed', 'dismissed', 'action_proposed', 'action_approved', 'in_progress', 'resolved', 'reopened', 'superseded')
ACTIVE = ('detected', 'under_review', 'confirmed', 'action_proposed', 'action_approved', 'in_progress', 'reopened')
REVIEWER, OWNER, APPROVER, SERVICE = 'finding_reviewer', 'finding_owner', 'action_approver', 'detection_service'
TRANSITIONS = {
    ('detected', 'under_review'): REVIEWER, ('detected', 'dismissed'): REVIEWER, ('under_review', 'confirmed'): REVIEWER, ('under_review', 'dismissed'): REVIEWER,
    ('confirmed', 'action_proposed'): OWNER, ('confirmed', 'dismissed'): REVIEWER, ('action_proposed', 'action_approved'): APPROVER, ('action_proposed', 'confirmed'): REVIEWER,
    ('action_approved', 'in_progress'): OWNER, ('in_progress', 'resolved'): OWNER, ('resolved', 'reopened'): REVIEWER, ('dismissed', 'reopened'): REVIEWER,
    ('reopened', 'under_review'): REVIEWER, ('reopened', 'dismissed'): REVIEWER}
NEEDS_RATIONALE = ('dismissed', 'resolved', 'reopened', 'superseded', 'action_approved', 'confirmed')
FINANCIAL = ('actual_loss', 'forecast_exposure', 'potential_revenue_at_risk', 'cash_timing_exposure', 'potential_opportunity')


class LifecycleError(ValueError):
    def __init__(self, code, msg=''):
        super().__init__(f'{code}: {msg}')
        self.code = code


def scope_key(scope):
    return 'tenant' if scope['level'] == 'tenant' else 'project:' + scope['project']


def _event(f, scoped, clock, event, frm=None, to=None, detail=None, actor=None, actor_kind=None):
    ctx = scoped.ctx
    ev = {'seq': len(f['history']) + 1, 'at': clock.now(), 'actor': actor or ctx.user_id, 'actor_kind': actor_kind or ctx.actor_kind, 'event': event, 'from': frm, 'to': to, 'detail': detail or {}}
    f['history'].append(ev)
    return ev


def _load(scoped, fid):
    rec = scoped.get(KIND, fid)
    if rec is None:
        raise LifecycleError('FINDING_UNKNOWN', fid)
    return rec


def _put(scoped, rec, f):
    try:
        return scoped.put(KIND, f['finding_id'], f, expected_revision=rec.revision)
    except ConflictError:
        raise LifecycleError('CONCURRENT_CHANGE', f['finding_id'] + ' changed while this action was being decided; retry')


def _need_role(scoped, role, what):
    if role not in scoped.ctx.roles:
        scoped.log('finding.refused', what, 'refused', reason='missing role ' + role)
        raise LifecycleError('ROLE_REQUIRED', f'{what} needs the role {role}')


def _need_human(scoped, what):
    if scoped.ctx.actor_kind != 'human':
        scoped.log('finding.refused', what, 'refused', reason='a person is required')
        raise LifecycleError('HUMAN_REQUIRED', f'{what} must be done by a person')


# ---------------------------------------------------------------- detection side
def new_finding(sig, run_key, run_at, as_of, dp_unapproved):
    return {'finding_id': sig['identity'], 'scope': sig['scope'], 'scope_key': scope_key(sig['scope']), 'rule_id': sig['rule']['id'], 'subject': sig['subject'], 'status': 'detected',
            'version': 1, 'signal': canon.deep_copy(sig), 'first_detected': {'run_key': run_key, 'at': run_at, 'as_of': as_of}, 'last_seen': {'run_key': run_key, 'at': run_at, 'as_of': as_of},
            'seen_count': 1, 'not_redetected': None, 'ownership': {'responsible_role': sig['ownership']['responsible_role'], 'reviewer_role': sig['ownership']['reviewer_role'], 'assignee': None,
                                                                     'next_review': None, 'deferred': None}, 'action': None, 'disposition': None, 'relations': [], 'history': [],
            'notifications': [], 'pending_notifications': [], 'reopen_count': 0, 'rule_versions': [{'rule': sig['rule']['id'], 'version': sig['rule']['version']}],
            'policy_unapproved': bool(dp_unapproved)}


def _is_version(x):
    """A version is a whole number of at least 1 and not a boolean (Python treats True as 1 and 1.0 as 1; neither is a version)."""
    return isinstance(x, int) and not isinstance(x, bool) and x >= 1


def _is_digest(x):
    return isinstance(x, str) and bool(x.strip())


def proposal_current(f):
    """True only if an action has been proposed and it was written against exactly this finding version and this evidence digest.  Fail-closed (finding F-55): the finding's version and the stored
    proposal version must both be whole numbers of at least 1 and not booleans, both digests must be non-empty texts, and a proposal explicitly marked stale is never current."""
    a = f.get('action')
    if not isinstance(a, dict):
        return False
    sig = f.get('signal')
    digest = sig.get('state_digest') if isinstance(sig, dict) else None
    pv, fv = a.get('proposed_version'), f.get('version')
    return bool(_is_version(fv) and _is_version(pv) and pv == fv and _is_digest(digest) and _is_digest(a.get('proposed_digest')) and a.get('proposed_digest') == digest and a.get('proposal_state') != 'stale')


def approval_current(f):
    """True only for an approval that is still in force: a person approved it, it has not been ended, it names exactly this finding version and this evidence digest (well-formed, as for a proposal),
    and the proposal it approved was written against that same version and digest."""
    a = f.get('action')
    if not isinstance(a, dict):
        return False
    sig = f.get('signal')
    digest = sig.get('state_digest') if isinstance(sig, dict) else None
    av = a.get('approved_version')
    return bool(a.get('approved_by') and a.get('approval_state') == 'current' and _is_version(av) and av == f.get('version') and _is_digest(a.get('approved_digest')) and a.get('approved_digest') == digest
                and proposal_current(f) and proposal_ref(f) is not None and a.get('approved_proposal') == proposal_ref(f))


def proposal_ref(f):
    """A reference to the exact proposal on record (finding F-56): a digest of its text, proposer, time, the version and evidence digest it was written against, and the number of proposals
    it replaced, so that a proposal written again (even with the same words) is a different proposal.  None if the finding holds no usable proposal."""
    a = f.get('action') if isinstance(f, dict) else None
    if not isinstance(a, dict):
        return None
    text, by, at, pv, pd = a.get('text'), a.get('proposed_by'), a.get('proposed_at'), a.get('proposed_version'), a.get('proposed_digest')
    if not (isinstance(text, str) and text.strip() and isinstance(by, str) and by and isinstance(at, str) and at and _is_version(pv) and _is_digest(pd)):
        return None
    hist = a.get('proposal_history')
    return canon.digest({'text': text, 'by': by, 'at': at, 'version': pv, 'digest': pd, 'replaced': len(hist) if isinstance(hist, list) else 0})[:24]


def approval_token(f):
    """What an approval screen must show and hand back: the finding, its current version, its current evidence digest and the reference of the proposal on record (None if there is none)."""
    return {'finding_id': f['finding_id'], 'version': f['version'], 'digest': f['signal']['state_digest'], 'proposal': proposal_ref(f)}


def _stale_text(f):
    pv = (f.get('action') or {}).get('proposed_version')
    shown = '(not recorded)' if pv is None else str(pv) if _is_version(pv) else '(not a valid version number)'
    return (f'the proposal was written against version {shown} and the finding is now at version {f.get("version")}; '
            'send it back to a reviewer (confirmed) and propose the action again against the current evidence')


def approvable(f):
    """-> (True, '') if an action can be approved now, else (False, why)."""
    if not isinstance(f.get('action'), dict) or not f['action']:
        return False, 'no action has been proposed'
    if f['status'] != 'action_proposed':
        return False, f'the finding is {f["status"]}, not action_proposed'
    if not proposal_current(f):
        return False, _stale_text(f)
    return True, ''


def _end_approval(f, at, because, new_digest):
    """Move the approval in force into the approval history and clear it.  `f['version']` is already the new version.  The finding's status is the caller's to set."""
    a = dict(f['action'])
    hist = list(a.get('approval_history', []))
    hist.append({'approved_by': a.get('approved_by'), 'approved_at': a.get('approved_at'), 'approved_version': a.get('approved_version'), 'approved_digest': a.get('approved_digest'), 'approved_proposal': a.get('approved_proposal'),
                 'approval_rationale': a.get('approval_rationale'), 'action_text': a.get('text'), 'proposed_by': a.get('proposed_by'), 'proposed_at': a.get('proposed_at'),
                 'proposed_version': a.get('proposed_version'), 'proposed_digest': a.get('proposed_digest'), 'ended_by': SERVICE, 'ended_at': at, 'ended_because': because, 'ended_at_version': f['version'], 'ended_at_digest': new_digest})
    a.update(approved_by=None, approved_at=None, approved_version=None, approved_digest=None, approved_proposal=None, approval_rationale=None, approval_state='invalidated', approval_history=hist)
    f['action'] = a
    return hist[-1]


def _mark_proposal_stale(f):
    """Called after the finding has moved to a new version: if an action had been proposed against the old evidence, mark it stale.  -> True if it newly went stale."""
    a = f.get('action')
    if not a or a.get('proposal_state') == 'stale':
        return False
    f['action'] = dict(a, proposal_state='stale')
    return True


def _pending(f, d, subject_body):
    if d['send']:
        subject, body = subject_body
        f['pending_notifications'].append({'dedup_key': d['dedup_key'], 'reason': d['reason'], 'recipient_role': f['ownership']['responsible_role'], 'subject': subject, 'body': body, 'attempts': 0,
                                           'last_error': ''})
    else:
        f['notifications'].append({'seq': len(f['notifications']) + 1, 'at': None, 'reason': d['reason'], 'dedup_key': d['dedup_key'], 'outcome': 'suppressed', 'detail': d['why']})


def _last_sent(f):
    sent = [n['at'] for n in f['notifications'] if n['outcome'] == 'sent' and n['at']]
    return max(sent)[:10] if sent else None


def ingest_run(scoped, clock, registry, run_key):
    """Turn the signals of one stored detection run into findings.  -> summary dict (also stored under det_ingest/<run_key>).  Needs the role detection_service held by a service identity."""
    from . import detect as D
    ctx = scoped.ctx
    if SERVICE not in ctx.roles or ctx.actor_kind != 'service':
        scoped.log('finding.refused', 'det_ingest/' + run_key, 'refused', reason='detection ingestion is a service act')
        raise LifecycleError('SERVICE_REQUIRED', 'only a service identity with the role detection_service ingests detection runs')
    prior = scoped.get(INGEST_KIND, run_key)
    if prior is not None:
        out = canon.deep_copy(prior.payload)
        out['replay'] = True
        scoped.log('finding.ingest_replay', 'det_ingest/' + run_key, 'no_change', reason='this run was already ingested')
        return out
    chk = D.check_record(scoped, registry, run_key)
    if not chk['replay'].ok or not chk['result_valid'] or not chk['pins_consistent']:
        scoped.log('finding.ingest_refused', 'det_ingest/' + run_key, 'refused', reason='the run does not verify: ' + chk['replay'].code)
        raise LifecycleError('RUN_DOES_NOT_VERIFY', chk['replay'].code or 'result invalid or pins inconsistent')
    rec = scoped.get(repro.KIND, run_key)
    p = rec.payload
    if p['formula_id'] not in D.FORMULAS and p['formula_id'] not in D.MKT_FORMULA_IDS:
        raise LifecycleError('NOT_A_DETECTION_RUN', p['formula_id'])
    res, run_at, as_of = p['result'], p['created_at'], p['result']['as_of']
    dpv = res['det_policy']['version']
    pinned = {i['kind'] + '/' + i['key']: i['revision'] for i in p['inputs']}
    dprec = scoped.get(DP.POLICY_KIND, dpv, pinned.get(DP.POLICY_KIND + '/' + dpv))
    dp = dprec.payload if dprec is not None else {'severity_bands': None, 'noise': None}
    unapproved = not res['det_policy']['approved']
    sk = scope_key(res['scope'])
    existing = {r.key: r for r in scoped.query(KIND, {'scope_key': sk})}
    ops, summary = [], {'run_key': run_key, 'scope_key': sk, 'as_of': as_of, 'created': [], 'updated': [], 'approvals_invalidated': [], 'proposals_stale': [], 'seen': [], 'reopened': [], 'ignored_older': [], 'ignored_superseded': [],
                        'kept_dismissed': [], 'not_redetected': [], 'rules_not_run': sorted(k for k, r in res['rule_runs'].items() if r['status'] != 'evaluated'), 'replay': False}
    seen_ids = set()
    for sig in res['signals']:
        fid = sig['identity']
        seen_ids.add(fid)
        sub_body = None
        rec_f = existing.get(fid)
        if rec_f is None:
            f = new_finding(sig, run_key, run_at, as_of, unapproved)
            _event(f, scoped, clock, 'detected', None, 'detected', {'run_key': run_key, 'rule': sig['rule'], 'state_digest': sig['state_digest']})
            _pending(f, noise.decide(fid, 'new', 'first', dp.get('noise'), None, run_at[:10]), noise.message(f, 'new'))
            ops.append((KIND, fid, f, 0))
            summary['created'].append(fid)
            continue
        f = canon.deep_copy(rec_f.payload)
        if f['status'] == 'superseded':
            summary['ignored_superseded'].append(fid)
            continue
        if as_of < f['last_seen']['as_of']:
            summary['ignored_older'].append(fid)
            continue
        changed = sig['state_digest'] != f['signal']['state_digest']
        ev_changed = noise.evidence_changed(f['signal'], sig)
        old_sev, new_sev = f['signal']['priority']['severity'], sig['priority']['severity']
        sev_up = noise.severity_increased(dp, old_sev, new_sev)
        if f['status'] in ('resolved', 'dismissed'):
            d = f['disposition'] or {}
            if run_at <= d.get('at', ''):
                summary['ignored_older'].append(fid)                                  # a run created before the decision cannot undo it
                continue
            if f['status'] == 'dismissed' and sig['state_digest'] == d.get('digest_at_decision'):
                f['last_seen'] = {'run_key': run_key, 'at': run_at, 'as_of': as_of}
                f['seen_count'] += 1
                ops.append((KIND, fid, f, rec_f.revision))
                summary['kept_dismissed'].append(fid)
                continue
            frm = f['status']
            f['status'], f['reopen_count'] = 'reopened', f['reopen_count'] + 1
            f['signal'], f['version'] = canon.deep_copy(sig), f['version'] + 1
            f['last_seen'] = {'run_key': run_key, 'at': run_at, 'as_of': as_of}
            f['seen_count'] += 1
            f['not_redetected'] = None
            old_pv = (f['action'] or {}).get('proposed_version')
            went_stale = _mark_proposal_stale(f)
            ended = _end_approval(f, run_at, 'finding_reopened', sig['state_digest']) if f['action'] and f['action'].get('approval_state') == 'current' else None
            _event(f, scoped, clock, 'reopened', frm, 'reopened', dict({'run_key': run_key, 'why': 'the condition was detected again with changed evidence' if frm == 'dismissed' else 'the condition was detected again after resolution',
                                                                         'state_digest': sig['state_digest']}, **({'approval_ended': ended['approved_version']} if ended else {}),
                                                                        **({'proposal_stale': True, 'proposed_version': old_pv} if went_stale else {})), actor=ctx.user_id, actor_kind='service')
            if went_stale:
                summary['proposals_stale'].append(fid)
            _pending(f, noise.decide(fid, 'reopened', str(f['reopen_count']), dp.get('noise'), _last_sent(f), run_at[:10]), noise.message(f, 'reopened'))
            ops.append((KIND, fid, f, rec_f.revision))
            summary['reopened'].append(fid)
            continue
        f['last_seen'] = {'run_key': run_key, 'at': run_at, 'as_of': as_of}
        f['seen_count'] += 1
        f['not_redetected'] = None
        rv = {'rule': sig['rule']['id'], 'version': sig['rule']['version']}
        if rv not in f['rule_versions']:
            f['rule_versions'].append(rv)
        f['policy_unapproved'] = unapproved
        if changed:
            f['signal'], f['version'] = canon.deep_copy(sig), f['version'] + 1
            old_pv = (f['action'] or {}).get('proposed_version')
            went_stale = _mark_proposal_stale(f)
            _event(f, scoped, clock, 'updated', f['status'], f['status'], dict({'run_key': run_key, 'state_digest': sig['state_digest'], 'evidence_changed': ev_changed, 'severity': [old_sev, new_sev]},
                                                                               **({'proposal_stale': True, 'proposed_version': old_pv} if went_stale else {})), actor_kind='service')
            summary['updated'].append(fid)
            if went_stale:
                summary['proposals_stale'].append(fid)
            if f['status'] in ('action_approved', 'in_progress') and f['action'] and f['action'].get('approved_by'):
                frm = f['status']
                ended = _end_approval(f, run_at, 'evidence_changed', sig['state_digest'])
                f['status'] = 'action_proposed'
                _event(f, scoped, clock, 'status_change', frm, 'action_proposed', {'why': 'approval_invalidated_evidence_changed', 'run_key': run_key, 'state_digest': sig['state_digest'],
                                                                                    'ended_approval': {'approved_by': ended['approved_by'], 'approved_version': ended['approved_version'],
                                                                                                       'approved_digest': ended['approved_digest'], 'action_text': ended['action_text'],
                                                                                                       'proposed_version': ended['proposed_version'], 'proposed_digest': ended['proposed_digest']}}, actor=ctx.user_id, actor_kind='service')
                summary['approvals_invalidated'].append(fid)
                st, sb = noise.message(f, 'status_transition')
                _pending(f, noise.decide(fid, 'status_transition', f'approval_invalidated|{f["version"]}', dp.get('noise'), _last_sent(f), run_at[:10]),
                         (st, sb + f'\nThe earlier approval of version {ended["approved_version"]} no longer stands because the evidence changed; the action needs a fresh approval.'))
            if sev_up:
                _pending(f, noise.decide(fid, 'severity_increase', new_sev, dp.get('noise'), _last_sent(f), run_at[:10]), noise.message(f, 'severity_increase'))
            elif ev_changed:
                _pending(f, noise.decide(fid, 'material_evidence', noise.digest_token(sig), dp.get('noise'), _last_sent(f), run_at[:10]), noise.message(f, 'material_evidence'))
        else:
            f['signal'] = canon.deep_copy(sig)                                      # a figure that only drifts with time is refreshed without a new version or notification
            summary['seen'].append(fid)
        ops.append((KIND, fid, f, rec_f.revision))
    for fid, rec_f in sorted(existing.items()):
        if fid in seen_ids:
            continue
        f = rec_f.payload
        if f['status'] not in ACTIVE or as_of < f['last_seen']['as_of']:
            continue
        rr = res['rule_runs'].get(f['rule_id'].replace('DET-', ''))
        if rr is None or rr['status'] != 'evaluated':
            continue                                                                  # the rule did not run: absence says nothing (Section 06 section 10)
        if f['not_redetected'] and f['not_redetected']['as_of'] == as_of:
            continue
        g = canon.deep_copy(f)
        g['not_redetected'] = {'run_key': run_key, 'as_of': as_of}
        _event(g, scoped, clock, 'not_redetected', g['status'], g['status'], {'run_key': run_key, 'note': 'the rule ran and did not raise this condition; a person decides whether it is resolved'}, actor_kind='service')
        ops.append((KIND, fid, g, rec_f.revision))
        summary['not_redetected'].append(fid)
    summary['rules_not_run_detail'] = {k: {'status': r['status'], 'missing': r['missing_parameters'], 'notes': r['notes']} for k, r in res['rule_runs'].items() if r['status'] != 'evaluated'}
    ops.append((INGEST_KIND, run_key, summary, 0))
    try:
        scoped.atomic(ops)
    except ConflictError:
        scoped.log('finding.ingest_conflict', 'det_ingest/' + run_key, 'not_applied', reason='a finding changed while the run was being ingested; nothing was written')
        raise LifecycleError('CONCURRENT_CHANGE', 'a finding changed while the run was being ingested; nothing was written; retry')
    scoped.log('finding.ingested', 'det_ingest/' + run_key, 'ok', detail={k: len(v) for k, v in summary.items() if isinstance(v, list)})
    return canon.deep_copy(summary)


def flush_notifications(scoped, clock, notifier):
    """Send every pending notification through the port; record the outcome in the finding's notification history.  A failure stays pending and visible.  -> counts."""
    if SERVICE not in scoped.ctx.roles or scoped.ctx.actor_kind != 'service':
        raise LifecycleError('SERVICE_REQUIRED', 'sending notifications is a service act')
    counts = {'sent': 0, 'duplicate': 0, 'failed': 0}
    for rec in scoped.query(KIND):
        f = rec.payload
        if not f['pending_notifications']:
            continue
        g = canon.deep_copy(f)
        still = []
        for n in g['pending_notifications']:
            note = {'dedup_key': n['dedup_key'], 'recipient_role': n['recipient_role'], 'subject': n['subject'], 'body': n['body'], 'finding_id': g['finding_id'], 'reason': n['reason']}
            r = notifier.send(scoped.ctx, note)
            n2 = dict(n, attempts=n['attempts'] + 1)
            if r['status'] == 'failed':
                n2['last_error'] = r['error']
                still.append(n2)
                counts['failed'] += 1
                g['notifications'].append({'seq': len(g['notifications']) + 1, 'at': clock.now(), 'reason': n['reason'], 'dedup_key': n['dedup_key'], 'outcome': 'failed', 'detail': r['error']})
            else:
                counts['sent' if r['status'] == 'delivered' else 'duplicate'] += 1
                g['notifications'].append({'seq': len(g['notifications']) + 1, 'at': clock.now(), 'reason': n['reason'], 'dedup_key': n['dedup_key'],
                                           'outcome': 'sent' if r['status'] == 'delivered' else 'duplicate', 'detail': r['receipt_id']})
        g['pending_notifications'] = still
        _put(scoped, rec, g)
    scoped.log('finding.notifications_flushed', 'tenant', 'ok', detail=counts)
    return counts


def outstanding_notifications(scoped):
    """-> [(finding id, dedup key, attempts, last error)] for notifications that have not been delivered: delivery failure is visible, never silent."""
    out = []
    for rec in scoped.query(KIND):
        for n in rec.payload['pending_notifications']:
            out.append((rec.key, n['dedup_key'], n['attempts'], n['last_error']))
    return out


# ---------------------------------------------------------------- people's acts
def transition(scoped, clock, fid, to, rationale='', evidence_ref='', superseded_by='', action_text='', approving_version=None, approving_digest=None, approving_proposal=None):
    ctx = scoped.ctx
    what = f'{KIND}/{fid}'
    _need_human(scoped, 'a status change')
    rec = _load(scoped, fid)
    f = canon.deep_copy(rec.payload)
    frm = f['status']
    if to not in STATUSES:
        raise LifecycleError('UNKNOWN_STATUS', to)
    if frm == 'superseded':
        raise LifecycleError('TERMINAL', 'a superseded finding is kept for audit and cannot change')
    if to == 'superseded':
        role = REVIEWER
    else:
        role = TRANSITIONS.get((frm, to))
        if role is None:
            scoped.log('finding.refused', what, 'refused', reason=f'transition {frm} -> {to} is not allowed')
            raise LifecycleError('TRANSITION_NOT_ALLOWED', f'{frm} -> {to}')
    _need_role(scoped, role, f'{frm} -> {to}')
    if to in NEEDS_RATIONALE and not (isinstance(rationale, str) and rationale.strip()):
        raise LifecycleError('RATIONALE_REQUIRED', f'{frm} -> {to} must record why')
    if to == 'resolved' and not (isinstance(evidence_ref, str) and evidence_ref.strip()):
        raise LifecycleError('EVIDENCE_REQUIRED', 'resolving a finding needs a reference to the evidence of the outcome')
    if to == 'in_progress' and not approval_current(f):                       # F-57 (CF-22): starting the action re-checks that the approval is still the approval of the proposal on record and of the current evidence
        scoped.log('finding.refused', what, 'refused', reason='the approval is not in force for the proposal and evidence on record')
        raise LifecycleError('APPROVAL_NOT_CURRENT', 'the approval no longer stands for the proposal and evidence on record; it must be approved again')
    if to == 'superseded':
        other = scoped.get(KIND, superseded_by) if isinstance(superseded_by, str) and superseded_by and superseded_by != fid else None
        if other is None:
            raise LifecycleError('SUPERSEDING_FINDING_REQUIRED', 'name another stored finding that replaces this one')
    if to == 'action_proposed':
        if not (isinstance(action_text, str) and action_text.strip()):
            raise LifecycleError('ACTION_REQUIRED', 'describe the proposed action')
        old = f['action'] or {}
        phist = list(old.get('proposal_history', []))
        if old:                                                               # the proposal being replaced is kept in full
            phist.append({'text': old.get('text'), 'proposed_by': old.get('proposed_by'), 'proposed_at': old.get('proposed_at'), 'proposed_version': old.get('proposed_version'),
                          'proposed_digest': old.get('proposed_digest'), 'proposal_ref': proposal_ref(f), 'approval_state': old.get('approval_state'),
                          'proposal_state': 'current' if proposal_current(f) else 'stale', 'approved_by': old.get('approved_by'), 'approved_version': old.get('approved_version'),
                          'replaced_by': ctx.user_id, 'replaced_at': clock.now(), 'replaced_at_version': f['version'], 'replaced_at_digest': f['signal']['state_digest']})
        f['action'] = {'text': action_text, 'proposed_by': ctx.user_id, 'proposed_at': clock.now(), 'proposed_version': f['version'], 'proposed_digest': f['signal']['state_digest'],
                       'proposal_state': 'current', 'approved_by': None, 'approved_at': None, 'approved_version': None, 'approved_digest': None, 'approved_proposal': None, 'approval_rationale': None,
                       'approval_state': 'proposed', 'approval_history': list(old.get('approval_history', [])), 'proposal_history': phist}
    if to == 'action_approved':
        if f['action'] is None or ctx.user_id == f['action']['proposed_by']:
            scoped.log('finding.refused', what, 'refused', reason='the proposer cannot approve their own action')
            raise LifecycleError('SELF_APPROVAL', 'a different person must approve the action')
        if not _token_ok(approving_version, approving_digest, approving_proposal):     # F-57: the gate is here, in the lowest-level call, so that no path can record an approval without all three
            scoped.log('finding.refused', what, 'refused', reason='an approval must name the finding version, the evidence digest and the proposal reference the approver was shown, each well formed')
            raise LifecycleError('APPROVAL_TOKEN_REQUIRED', 'name the version, the evidence digest and the proposal reference you were shown (approval_token) to approve an action; a version is a whole number of at least 1 and a digest and a proposal reference are non-empty texts')
        if approving_version != f['version']:
            scoped.log('finding.refused', what, 'refused', reason=f'the approval names version {approving_version}; the finding is at version {f["version"]}')
            raise LifecycleError('STALE_APPROVAL', f'the approval names version {approving_version} but the finding is now at version {f["version"]}; read it again')
        if approving_digest != f['signal']['state_digest']:
            scoped.log('finding.refused', what, 'refused', reason=f'the approval names evidence digest {approving_digest}; the finding is at version {f["version"]} with a different digest')
            raise LifecycleError('STALE_APPROVAL', f'the approval names evidence that is no longer current (finding is at version {f["version"]}); read it again')
        if not proposal_current(f):                                          # F-53: the proposal itself must have been written against this evidence, whatever the approver names
            why = _stale_text(f)
            scoped.log('finding.refused', what, 'refused', reason='the proposal is out of date: ' + why)
            raise LifecycleError('STALE_PROPOSAL', why)
        ref = proposal_ref(f)
        if ref is None:                                                       # a proposal with no usable reference cannot be shown or approved, whatever is named
            scoped.log('finding.refused', what, 'refused', reason='the proposal on record has no usable reference')
            raise LifecycleError('PROPOSAL_CHANGED', 'the proposal on record cannot be identified; propose the action again')
        if approving_proposal != ref:                                         # F-56: the approver must have been shown the proposal that is on record
            scoped.log('finding.refused', what, 'refused', reason='the approval names a proposal that is not the one on record: it was replaced after it was shown, or it is damaged')
            raise LifecycleError('PROPOSAL_CHANGED', 'the proposal on record is not the one you were shown; read it again')
        f['action'] = dict(f['action'], approved_by=ctx.user_id, approved_at=clock.now(), approved_version=f['version'], approved_digest=f['signal']['state_digest'], approved_proposal=ref,
                           approval_state='current', approval_rationale=rationale)
    if to in ('dismissed', 'resolved'):
        f['disposition'] = {'decision': to, 'rationale': rationale, 'by': ctx.user_id, 'at': clock.now(), 'evidence_ref': evidence_ref, 'digest_at_decision': f['signal']['state_digest'],
                            'verified_outcome': None}
    if to == 'reopened':
        f['reopen_count'] += 1
    f['status'] = to
    detail = {'rationale': rationale}
    if to in ('action_proposed', 'action_approved'):
        a = f['action']
        detail.update(action_text=a['text'], proposed_version=a['proposed_version'], proposed_digest=a['proposed_digest'], proposal_ref=proposal_ref(f))
        if to == 'action_approved':
            detail.update(approved_version=a['approved_version'], approved_digest=a['approved_digest'])
    if evidence_ref:
        detail['evidence_ref'] = evidence_ref
    if to == 'superseded':
        detail['superseded_by'] = superseded_by
        f['superseded_by'] = superseded_by
    _event(f, scoped, clock, 'status_change', frm, to, detail)
    dp = _policy_of(scoped, f)
    subject, body = noise.message(f, 'status_transition')
    d = noise.decide(fid, 'status_transition', f'{to}|{len(f["history"])}', (dp or {}).get('noise'), _last_sent(f), clock.now()[:10])
    _pending(f, d, (subject, body + f'\nChanged by {ctx.user_id}: {frm} -> {to}.'))
    _put(scoped, rec, f)
    scoped.log('finding.transition', what, 'ok', reason=rationale[:200], detail={'from': frm, 'to': to})
    return f


def _token_ok(version, digest, proposal):
    return _is_version(version) and _is_digest(digest) and _is_digest(proposal)


def approve_action(scoped, clock, fid, approving_version, approving_digest, rationale, approving_proposal=None):
    """The approval entry point for screens and APIs.  It fails closed: an approval that does not name the finding version, the evidence digest and the proposal reference the approver was shown
    (see approval_token) is refused before anything is looked at.  Everything else is `transition(... 'action_approved' ...)`, which checks the same things itself (F-57): this entry point does not hold the gate alone."""
    if not _token_ok(approving_version, approving_digest, approving_proposal):
        scoped.log('finding.refused', f'{KIND}/{fid}', 'refused', reason='an approval must name the finding version, the evidence digest and the proposal reference the approver was shown')
        raise LifecycleError('APPROVAL_TOKEN_REQUIRED', 'name the version, the evidence digest and the proposal reference you were shown (approval_token) to approve an action')
    return transition(scoped, clock, fid, 'action_approved', rationale=rationale, approving_version=approving_version, approving_digest=approving_digest, approving_proposal=approving_proposal)


def _policy_of(scoped, f):
    run = scoped.get(repro.KIND, f['last_seen']['run_key'])
    if run is None:
        return None
    v = run.payload['result']['det_policy']['version']
    r = scoped.get(DP.POLICY_KIND, v)
    return r.payload if r is not None else None


def assign(scoped, clock, fid, assignee, next_review=None):
    _need_human(scoped, 'assignment')
    if REVIEWER not in scoped.ctx.roles and OWNER not in scoped.ctx.roles:
        scoped.log('finding.refused', f'{KIND}/{fid}', 'refused', reason='no reviewer or owner role')
        raise LifecycleError('ROLE_REQUIRED', 'assignment needs the role finding_reviewer or finding_owner')
    if not (isinstance(assignee, str) and assignee.strip()):
        raise LifecycleError('ASSIGNEE_REQUIRED')
    rec = _load(scoped, fid)
    f = canon.deep_copy(rec.payload)
    if f['status'] == 'superseded':
        raise LifecycleError('TERMINAL')
    f['ownership'] = dict(f['ownership'], assignee=assignee, next_review=next_review)
    _event(f, scoped, clock, 'assigned', f['status'], f['status'], {'assignee': assignee, 'next_review': next_review})
    _put(scoped, rec, f)
    scoped.log('finding.assigned', f'{KIND}/{fid}', 'ok', detail={'assignee': assignee})
    return f


def defer(scoped, clock, fid, until, rationale):
    """Deferral is not dismissal: the status does not change, the next review date moves, and the reason is on record (Section 06 section 11)."""
    _need_human(scoped, 'deferral')
    _need_role(scoped, REVIEWER, 'deferral')
    if not (isinstance(rationale, str) and rationale.strip()) or not (isinstance(until, str) and len(until) == 10):
        raise LifecycleError('RATIONALE_REQUIRED', 'a deferral needs a date and a reason')
    rec = _load(scoped, fid)
    f = canon.deep_copy(rec.payload)
    if f['status'] not in ACTIVE:
        raise LifecycleError('NOT_ACTIVE', f['status'])
    f['ownership'] = dict(f['ownership'], next_review=until, deferred={'until': until, 'rationale': rationale, 'by': scoped.ctx.user_id, 'at': clock.now()})
    _event(f, scoped, clock, 'deferred', f['status'], f['status'], {'until': until, 'rationale': rationale})
    _put(scoped, rec, f)
    scoped.log('finding.deferred', f'{KIND}/{fid}', 'ok', reason=rationale[:200])
    return f


def link(scoped, clock, fid_a, fid_b, kind, rationale, confirmed=False):
    """Record a relationship between two findings.  kind: 'shared_root_cause_hypothesis' | 'financial_overlap' | 'related'.  A root cause is a hypothesis unless a person confirms it with a rationale."""
    _need_human(scoped, 'linking')
    _need_role(scoped, REVIEWER, 'linking')
    if kind not in ('shared_root_cause_hypothesis', 'financial_overlap', 'related') or fid_a == fid_b or not (isinstance(rationale, str) and rationale.strip()):
        raise LifecycleError('LINK_INVALID')
    ra, rb = _load(scoped, fid_a), _load(scoped, fid_b)
    for rec, other in ((ra, fid_b), (rb, fid_a)):
        f = canon.deep_copy(rec.payload)
        rel = {'with': other, 'kind': kind, 'confirmed': bool(confirmed) and kind != 'financial_overlap', 'rationale': rationale, 'by': scoped.ctx.user_id, 'at': clock.now()}
        f['relations'] = [r for r in f['relations'] if not (r['with'] == other and r['kind'] == kind)] + [rel]
        _event(f, scoped, clock, 'linked', f['status'], f['status'], {'with': other, 'kind': kind})
        _put(scoped, rec, f)
    scoped.log('finding.linked', f'{KIND}/{fid_a}', 'ok', detail={'with': fid_b, 'kind': kind})


def claim_realised(scoped, fid, amount_cents):
    """Refused, always.  An estimated saving or opportunity cannot be reported as realised without the Section 05 verification, which this milestone does not build (PG-AI-AC-16)."""
    scoped.log('finding.refused', f'{KIND}/{fid}', 'refused', reason='realised outcome needs Section 05 verification, not built')
    raise LifecycleError('VERIFICATION_NOT_AVAILABLE', 'a realised outcome needs the Section 05 verification; findings carry estimates and exposures only')


def get(scoped, fid):
    return canon.deep_copy(_load(scoped, fid).payload)


def all_findings(scoped, scope=None):
    where = {'scope_key': scope} if scope else None
    return [canon.deep_copy(r.payload) for r in scoped.query(KIND, where)]
