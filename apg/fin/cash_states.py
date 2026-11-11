"""Retention release as separate, evidenced states.  Blueprint: Section 12 sections 4 (state separation: no silent promotion), 8 (retention intelligence), 13 gates A and C;
Section 03 section 4.1 ("a retention balance is not automatically a loss"); PG-PC-AC-11.

Retention is held in POOLS that money moves between, one recorded event at a time:
    withheld -> claimed -> approved -> released -> received          claimed or approved -> disputed -> claimed or approved
Rules enforced both when an event is written and again whenever the pools are re-derived from the stored events (so a damaged or forged event sequence is found, not trusted):
  * a transition not in the table above is refused (nothing skips a state: 'released' is not 'received', 'claimed' is not 'approved');
  * an event moves an amount that must be available in the pool it leaves (no negative pool, no money created);
  * every event needs an evidence reference and a named human actor; approval, release and receipt need the role 'retention_approver' (consequential steps are never
    automatic and never taken by a service or an AI);
  * 'received' needs bank evidence: a stored bank transaction for exactly that amount (the rule is exact equality; no tolerance is configured, CR-02 A13);
  * a forecast release date passing moves nothing: pools change only through events (the position reports a REVIEW flag, never an entitlement).
Events are append-only (key = project|sequence, written with expected revision 0, so two writers racing for the same sequence cannot both succeed)."""
from .. import canon

EVENT_KIND = 'retention_event'
POOLS = ('withheld', 'claimed', 'approved', 'disputed', 'released', 'received')
TRANSITIONS = {('withheld', 'claimed'), ('claimed', 'approved'), ('claimed', 'disputed'), ('approved', 'released'), ('approved', 'disputed'), ('disputed', 'claimed'),
               ('disputed', 'approved'), ('released', 'received')}
APPROVER_ROLE = 'retention_approver'
CLERK_ROLES = ('retention_clerk', APPROVER_ROLE)
CONSEQUENTIAL = ('approved', 'released', 'received')


class RetentionError(ValueError):
    def __init__(self, code, msg=''):
        super().__init__(f'{code}: {msg}')
        self.code = code


def baseline(ledger_fields):
    """Starting pools from the ledger record: held money is 'withheld', or 'released' when the ledger itself carries a release date (ledger evidence only)."""
    held = ledger_fields['retention_held_cents']
    pools = {p: 0 for p in POOLS}
    pools['released' if ledger_fields.get('released_date') else 'withheld'] = held
    return pools


def check_event(pools, ev, bank=None):
    """Applies one event to `pools` (mutating a copy is the caller's job).  Raises RetentionError with a code."""
    if (ev['from_state'], ev['to_state']) not in TRANSITIONS:
        raise RetentionError('TRANSITION_NOT_ALLOWED', f"{ev['from_state']} -> {ev['to_state']}")
    amt = ev['amount_cents']
    if not isinstance(amt, int) or isinstance(amt, bool) or amt <= 0:
        raise RetentionError('AMOUNT_INVALID', str(amt))
    if pools[ev['from_state']] < amt:
        raise RetentionError('INSUFFICIENT_IN_POOL', f"{ev['from_state']} holds {pools[ev['from_state']]}, event moves {amt}")
    if not ev.get('evidence_ref'):
        raise RetentionError('EVIDENCE_REQUIRED')
    if ev.get('actor_kind') != 'human' or not ev.get('actor'):
        raise RetentionError('HUMAN_ACTOR_REQUIRED')
    if ev['to_state'] in CONSEQUENTIAL and APPROVER_ROLE not in ev.get('actor_roles', ()):
        raise RetentionError('APPROVER_ROLE_REQUIRED', ev['to_state'])
    if ev['to_state'] not in CONSEQUENTIAL and not set(CLERK_ROLES) & set(ev.get('actor_roles', ())):
        raise RetentionError('CLERK_ROLE_REQUIRED', ev['to_state'])
    if ev['to_state'] == 'received':
        tx = (bank or {}).get(ev['evidence_ref'])
        if tx is None or tx.get('amount_cents') != amt:
            raise RetentionError('BANK_EVIDENCE_REQUIRED', 'received needs a stored bank transaction of exactly this amount')


def fold(ledger_fields, events, bank=None):
    """-> (pools, problems).  Re-derives the pools from stored events in sequence order and re-checks every rule; the first event that breaks one stops the fold."""
    pools = baseline(ledger_fields)
    problems = []
    last = 0
    for ev in sorted(events, key=lambda e: e['seq']):
        if ev['seq'] != last + 1:
            problems.append({'seq': ev['seq'], 'code': 'SEQUENCE_GAP'})
            break
        last = ev['seq']
        try:
            check_event(pools, ev, bank)
        except RetentionError as e:
            problems.append({'seq': ev['seq'], 'code': e.code})
            break
        pools[ev['from_state']] -= ev['amount_cents']
        pools[ev['to_state']] += ev['amount_cents']
    return pools, problems


def record_event(scoped, clock, project, ledger_fields, from_state, to_state, amount_cents, evidence_ref, note='', bank=None):
    """Append one event.  Reads the stored events for the project, re-derives the pools, checks the rules and writes the next sequence number.  Returns the stored record."""
    ctx = scoped.ctx
    existing = [r.payload for r in scoped.query(EVENT_KIND, {'project_ref': project})]
    pools, problems = fold(ledger_fields, existing, bank)
    if problems:
        raise RetentionError('STORED_EVENTS_INCONSISTENT', str(problems[0]))
    seq = len(existing) + 1
    ev = {'project_ref': project, 'seq': seq, 'from_state': from_state, 'to_state': to_state, 'amount_cents': amount_cents, 'evidence_ref': evidence_ref, 'note': note,
          'actor': ctx.user_id, 'actor_kind': ctx.actor_kind, 'actor_roles': list(ctx.roles), 'at': clock.now()}
    check_event(pools, ev, bank)
    rec = scoped.put(EVENT_KIND, f'{project}|{seq:04d}', ev, expected_revision=0)
    scoped.log('retention.event', f'{EVENT_KIND}/{project}|{seq:04d}', 'ok', detail={'from': from_state, 'to': to_state, 'amount_cents': amount_cents, 'evidence': evidence_ref})
    return rec


def events_of(facts, project):
    out = []
    for key, p in facts.kind(EVENT_KIND).items():
        if p.get('project_ref') == project:
            out.append(canon.deep_copy(p))
    return sorted(out, key=lambda e: e['seq'])
