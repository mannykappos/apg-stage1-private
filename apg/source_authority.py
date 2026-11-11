"""Source authority, quarantine and the authoritative / provisional split.  Blueprint: Section 04 sections 5, 8, 9, 13; acceptance PG-DI-AC-01 to 07.

What this module enforces
  * A source may set a material field only if an APPROVED field-level rule says so (AC-01).  No rule, or an unapproved register: the value goes
    to controlled reconciliation as PROVISIONAL.  It is never silently taken from whichever source arrived (Section 04 section 5).
  * Different sources can govern different fields; registers are versioned and keep history (AC-02).
  * The newest timestamp never decides.  Revisions are ordered by source revision numbers; two different values at the same revision,
    or at unknown revisions, are a conflict.
  * Conflicting material records are QUARANTINED and left out of authoritative totals, but stay visible to reviewers (AC-03, AC-04).
  * Provisional totals are a different type, labelled, and cannot be added to authoritative ones (AC-05).
  * Promotion needs a resolver with the right role, enough distinct human approvals and a recorded disposition; it is idempotent and keeps the
    original evidence (AC-06).  AI/OCR-extracted material values need human verification first (AC-07).
This module has no clock and no storage of its own; QuarantineQueue uses a ScopedStore."""
import re
from dataclasses import dataclass, field
from . import canon
from .values import AMBIGUOUS, CONFLICTED, EXCLUDED, INVALID, NO_DATA, Known, Unknown, UnknownValueError, as_value

ACCEPTED, ACCEPTED_W, PENDING, QUARANTINED, REJECTED = 'accepted', 'accepted_with_warnings', 'pending_reconciliation', 'quarantined', 'rejected'
OUTCOMES = (ACCEPTED, ACCEPTED_W, PENDING, QUARANTINED, REJECTED)
AUTHORITATIVE_OUTCOMES = (ACCEPTED, ACCEPTED_W)
NATURES = ('source_owned', 'derived', 'human_approved', 'provisional')
DISAGREE = ('quarantine', 'authoritative_wins_with_warning')
_DATE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')


class AuthorityError(ValueError):
    pass


@dataclass(frozen=True)
class AuthorityRule:
    entity_kind: str
    field: str
    authoritative_source: str
    permitted_secondary: tuple
    nature: str
    on_secondary_disagreement: str
    conflict_resolver_role: str
    required_approvals: int
    effective_from: str
    effective_to: object            # None or 'YYYY-MM-DD'
    owner: str
    evidence_basis: str

    def __post_init__(self):
        for f in ('entity_kind', 'field', 'authoritative_source', 'conflict_resolver_role', 'owner', 'evidence_basis'):
            if not isinstance(getattr(self, f), str) or not getattr(self, f).strip():
                raise AuthorityError(f'rule field {f} is required')
        if not isinstance(self.permitted_secondary, tuple) or self.authoritative_source in self.permitted_secondary:
            raise AuthorityError('permitted_secondary must be a tuple that does not repeat the authoritative source')
        if self.nature not in NATURES or self.on_secondary_disagreement not in DISAGREE:
            raise AuthorityError('nature or on_secondary_disagreement invalid')
        if not isinstance(self.required_approvals, int) or isinstance(self.required_approvals, bool) or self.required_approvals < 1:
            raise AuthorityError('required_approvals must be an integer of at least 1')
        if not (isinstance(self.effective_from, str) and _DATE.fullmatch(self.effective_from)) or not (self.effective_to is None or (isinstance(self.effective_to, str) and _DATE.fullmatch(self.effective_to))):
            raise AuthorityError('effective dates must be YYYY-MM-DD')
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise AuthorityError('effective_to is before effective_from')

    def covers(self, as_of):
        return self.effective_from <= as_of and (self.effective_to is None or as_of <= self.effective_to)


@dataclass(frozen=True)
class Approval:
    approver: str
    role: str
    kind: str
    date: str


@dataclass(frozen=True)
class AuthorityRegister:
    version: str
    rules: tuple
    proposer: str
    approvals: tuple
    supersedes: object = None

    def __post_init__(self):
        if not isinstance(self.version, str) or not self.version.strip():
            raise AuthorityError('register needs a version')
        seen = {}
        for r in self.rules:
            for other in seen.get((r.entity_kind, r.field), []):
                lo = max(r.effective_from, other.effective_from)
                hi = min(r.effective_to or '9999-12-31', other.effective_to or '9999-12-31')
                if lo <= hi:
                    raise AuthorityError(f'overlapping rules for {r.entity_kind}.{r.field}')
            seen.setdefault((r.entity_kind, r.field), []).append(r)

    def approved(self):
        """Approved = at least one HUMAN approval, by someone other than the proposer, in the role 'authority_owner'."""
        return any(a.kind == 'human' and a.role == 'authority_owner' and a.approver != self.proposer for a in self.approvals)

    def rule_for(self, entity_kind, field_name, as_of):
        for r in self.rules:
            if r.entity_kind == entity_kind and r.field == field_name and r.covers(as_of):
                return r
        return None


class RegisterHistory:
    """Registers are never edited: a change is a new version.  Old versions stay available so a historical record can show the rule used."""
    def __init__(self):
        self._v = {}
        self._order = []

    def add(self, register):
        if register.version in self._v:
            raise AuthorityError('a register version cannot be replaced')
        if self._order and register.supersedes != self._order[-1]:
            raise AuthorityError('a new register must name the version it supersedes')
        if not self._order and register.supersedes is not None:
            raise AuthorityError('first register supersedes nothing')
        self._v[register.version] = register
        self._order.append(register.version)

    def current(self):
        return self._v[self._order[-1]] if self._order else None

    def get(self, version):
        return self._v[version]

    def versions(self):
        return tuple(self._order)


@dataclass(frozen=True)
class Observation:
    source: str
    value: object                     # Known | Unknown | raw
    record_ref: str                   # e.g. 'accounting:INV-0007@3'
    received_at: str                  # recorded, NEVER used to pick a winner
    source_revision: object = None    # int or None
    cancelled: bool = False
    origin: str = 'system'            # 'system' | 'ai_extracted'
    human_verified: bool = False
    approved_by_role: object = None   # for human_approved fields


@dataclass(frozen=True)
class Resolution:
    entity_ref: str
    field: str
    outcome: str
    value: object                     # Known | Unknown
    reasons: tuple
    warnings: tuple
    register_version: object
    rule_nature: object
    sources_used: tuple
    candidates: tuple                 # ((source, value-as-text), ...) shown to reviewers; NOT authoritative

    @property
    def authoritative(self):
        return self.outcome in AUTHORITATIVE_OUTCOMES and self.rule_nature != 'provisional' and isinstance(self.value, Known)


def _txt(v):
    v = as_value(v)
    return f'unknown:{v.reason}' if isinstance(v, Unknown) else str(v.cents)


def resolve_field(register, entity_ref, entity_kind, field_name, observations, as_of):
    """Decide what, if anything, may be used as the authoritative value of one field.  Never raises for bad input: it fails safe."""
    cands = tuple((o.source, _txt(o.value)) for o in observations)

    def out(outcome, value, reasons, warnings=(), rule=None, used=()):
        return Resolution(entity_ref, field_name, outcome, value, tuple(reasons), tuple(warnings), register.version if register else None, rule.nature if rule else None, tuple(used), cands)

    if register is None or not register.approved():
        return out(PENDING, Unknown(NO_DATA, 'no approved source authority register'), ['NO_APPROVED_REGISTER'])
    if not (isinstance(as_of, str) and _DATE.fullmatch(as_of)):
        return out(PENDING, Unknown(INVALID, 'as-of date invalid'), ['AS_OF_INVALID'])
    rule = register.rule_for(entity_kind, field_name, as_of)
    if rule is None:
        return out(PENDING, Unknown(NO_DATA, 'no field-level authority rule'), ['NO_AUTHORITY_RULE'])
    allowed = {rule.authoritative_source, *rule.permitted_secondary}
    live = [o for o in observations if not o.cancelled]
    foreign = [o for o in live if o.source not in allowed]
    live = [o for o in live if o.source in allowed]
    warnings = [f'SOURCE_NOT_PERMITTED:{o.source}' for o in foreign]
    auth = [o for o in live if o.source == rule.authoritative_source]
    sec = [o for o in live if o.source != rule.authoritative_source]
    if not auth:
        return out(PENDING, Unknown(NO_DATA, 'authoritative source has not supplied a value'), ['AUTHORITATIVE_SOURCE_ABSENT'], warnings, rule)
    # revision lineage: highest source_revision wins; the timestamp never does
    revs = [o.source_revision for o in auth]
    if any(r is not None and (not isinstance(r, int) or isinstance(r, bool)) for r in revs):
        return out(QUARANTINED, Unknown(INVALID, 'revision number invalid'), ['REVISION_INVALID'], warnings, rule)
    vals = {_txt(o.value) for o in auth}
    if len(vals) > 1:
        if any(r is None for r in revs):
            return out(QUARANTINED, Unknown(CONFLICTED, 'differing values with unknown revision order'), ['AMBIGUOUS_REVISION'], warnings, rule)
        top = max(revs)
        at_top = [o for o in auth if o.source_revision == top]
        if len({_txt(o.value) for o in at_top}) > 1:
            return out(QUARANTINED, Unknown(CONFLICTED, 'differing values at the same revision'), ['CONFLICT_SAME_REVISION'], warnings, rule)
        auth = at_top
    chosen = auth[0]
    val = as_value(chosen.value)
    if isinstance(val, Unknown):
        return out(PENDING, val, ['AUTHORITATIVE_VALUE_UNKNOWN:' + val.reason], warnings, rule, [chosen.source])
    if chosen.origin != 'system' and not chosen.human_verified:
        return out(PENDING, Unknown(AMBIGUOUS, 'AI/OCR-extracted value awaits human verification'), ['AWAITING_HUMAN_VERIFICATION'], warnings, rule, [chosen.source])
    if rule.nature == 'human_approved' and chosen.approved_by_role is None:
        return out(PENDING, Unknown(NO_DATA, 'field needs human approval'), ['AWAITING_HUMAN_APPROVAL'], warnings, rule, [chosen.source])
    disagree = [o for o in sec if isinstance(as_value(o.value), Known) and as_value(o.value).cents != val.cents]
    if disagree:
        if rule.on_secondary_disagreement == 'quarantine':
            return out(QUARANTINED, Unknown(CONFLICTED, 'sources disagree'), ['SECONDARY_DISAGREES:' + ','.join(sorted({o.source for o in disagree}))], warnings, rule, [chosen.source])
        warnings.append('SECONDARY_DISAGREES:' + ','.join(sorted({o.source for o in disagree})))
    if warnings:
        return out(ACCEPTED_W, val, ['AUTHORITATIVE_RULE_APPLIED'], warnings, rule, [chosen.source])
    return out(ACCEPTED, val, ['AUTHORITATIVE_RULE_APPLIED'], (), rule, [chosen.source])


def record_status(resolutions):
    """A record is only as trustworthy as its worst material field."""
    outs = [r.outcome for r in resolutions]
    for bad in (REJECTED, QUARANTINED, PENDING):
        if bad in outs:
            return bad
    if any(r.rule_nature == 'provisional' for r in resolutions):
        return PENDING
    return ACCEPTED_W if ACCEPTED_W in outs else ACCEPTED


@dataclass(frozen=True)
class AuthoritativeTotal:
    cents: int
    complete: bool
    included: tuple
    excluded: tuple                   # ((record_id, status, reasons), ...)  visible to reviewers
    register_version: object

    def __add__(self, other):
        raise TypeError('an authoritative total cannot be added to anything else; combine inside a recorded calculation')
    __radd__ = __add__


@dataclass(frozen=True)
class ProvisionalTotal:
    label: str
    cents: int
    unverified: tuple                 # ((record_id, status, candidate_value_text), ...)
    assumptions: tuple
    as_of: str

    def __add__(self, other):
        raise TypeError('a provisional total cannot be added to an authoritative total')
    __radd__ = __add__


def authoritative_total(rows, as_of_register_version=None):
    """rows: iterable of (record_id, status, Known|Unknown|raw amount, reasons).  Only accepted records with a known amount are counted;
    everything else is listed in `excluded` with its status, never counted as zero."""
    s, inc, exc = 0, [], []
    for rid, status, amount, reasons in rows:
        v = as_value(amount)
        if status in AUTHORITATIVE_OUTCOMES and isinstance(v, Known):
            s += v.cents; inc.append(rid)
        else:
            exc.append((rid, status, tuple(reasons) if reasons else (('AMOUNT_UNKNOWN:' + v.reason,) if isinstance(v, Unknown) else ())))
    return AuthoritativeTotal(s, not exc, tuple(inc), tuple(exc), as_of_register_version)


def provisional_total(rows, as_of, assumptions=('candidate values are unverified and may be wrong',)):
    """rows: iterable of (record_id, status, candidate Known|Unknown|raw).  Counts known candidates of NON-authoritative records only."""
    s, un = 0, []
    for rid, status, cand in rows:
        v = as_value(cand)
        if status not in AUTHORITATIVE_OUTCOMES and isinstance(v, Known):
            s += v.cents; un.append((rid, status, str(v.cents)))
        elif status not in AUTHORITATIVE_OUTCOMES:
            un.append((rid, status, 'unknown'))
    return ProvisionalTotal('PROVISIONAL - not authoritative', s, tuple(un), tuple(assumptions), as_of)


def compare_views(auth, prov):
    """The only sanctioned way to look at both: two labelled numbers and their difference."""
    if not isinstance(auth, AuthoritativeTotal) or not isinstance(prov, ProvisionalTotal):
        raise TypeError('compare_views needs one authoritative and one provisional total')
    return {'authoritative_cents': auth.cents, 'authoritative_complete': auth.complete, 'provisional_label': prov.label, 'provisional_only_cents': prov.cents,
            'if_all_provisional_were_confirmed_cents': auth.cents + prov.cents, 'unresolved_records': len(auth.excluded)}


class QuarantineQueue:
    """Held records stay visible to reviewers.  Dispositions are appended as new revisions; nothing is deleted or overwritten."""
    KIND = 'quarantine'

    def __init__(self, scoped):
        self.s = scoped

    def hold(self, record_ref, resolution, resolver_role, required_approvals=1, observations=()):
        payload = {'status': 'held', 'record_ref': record_ref, 'outcome': resolution.outcome, 'reasons': list(resolution.reasons), 'field': resolution.field,
                   'register_version': resolution.register_version or '', 'resolver_role': resolver_role, 'required_approvals': required_approvals,
                   'candidates': [list(c) for c in resolution.candidates], 'evidence': list(observations), 'approvals': [], 'disposition': None}
        rec = self.s.put(self.KIND, record_ref, payload)
        self.s.log('quarantine.hold', record_ref, resolution.outcome, reason=','.join(resolution.reasons))
        return rec

    def open_items(self):
        return tuple(r for r in self.s.query(self.KIND) if r.payload['status'] in ('held', 'retained'))

    def dispose(self, approver_ctx, record_ref, action, note, corrected_cents=None):
        """action: accept | correct | reject | merge | retain.  The approver must be a human holding the item's resolver role, must differ from
        earlier approvers, and the item is promoted only when enough distinct approvals exist.  Idempotent."""
        item = self.s.get(self.KIND, record_ref)
        if item is None:
            raise AuthorityError('no such quarantined record')
        p = canon.deep_copy(item.payload)
        if p['status'] in ('promoted', 'rejected', 'merged'):
            return item                                     # already finally disposed: a second call changes nothing
        if action not in ('accept', 'correct', 'reject', 'merge', 'retain'):
            raise AuthorityError('unknown action')
        if approver_ctx.actor_kind != 'human' or p['resolver_role'] not in approver_ctx.roles:
            self.s.log('quarantine.refused', record_ref, 'refused', reason='approver lacks role or is not human')
            raise AuthorityError('approver must be a human holding the resolver role')
        if not isinstance(note, str) or not note.strip():
            raise AuthorityError('a disposition note is required')
        if action == 'correct' and (not isinstance(corrected_cents, int) or isinstance(corrected_cents, bool)):
            raise AuthorityError('a correction needs a whole-cent value')
        if action in ('reject', 'retain'):
            p['status'] = 'rejected' if action == 'reject' else 'retained'
            p['disposition'] = {'action': action, 'note': note, 'by': approver_ctx.user_id}
        else:
            if any(a['by'] == approver_ctx.user_id for a in p['approvals']):
                raise AuthorityError('the same person cannot approve twice')
            p['approvals'].append({'by': approver_ctx.user_id, 'action': action, 'note': note, 'corrected_cents': corrected_cents})
            if len({a['action'] for a in p['approvals']}) > 1 or (action == 'correct' and len({a['corrected_cents'] for a in p['approvals']}) > 1):
                raise AuthorityError('approvers must agree on the action and the corrected value')
            if len(p['approvals']) >= p['required_approvals']:
                p['status'] = 'promoted' if action in ('accept', 'correct') else 'merged'
                p['disposition'] = {'action': action, 'note': note, 'corrected_cents': corrected_cents, 'approvals': len(p['approvals'])}
        rec = self.s.put(self.KIND, record_ref, p, expected_revision=item.revision)
        self.s.log('quarantine.dispose', record_ref, p['status'], reason=action)
        return rec


# ---------------------------------------------------------------- batch intake guard
def batch_conflicts(rows, key_field):
    """-> (clean_rows, conflicts).  Within ONE batch, the same identifier carrying DIFFERENT content is a conflict: neither row is clean.
    Identical repeats are collapsed (the first is kept).  A row with no usable identifier is also a conflict.  `conflicts` = {key: [rows...]}."""
    first, seen, bad = {}, {}, {}
    for r in rows:
        k = r.get(key_field) if isinstance(r, dict) else None
        if not isinstance(k, str) or not k.strip():
            bad.setdefault('<no identifier>', []).append(r); continue
        d = canon.digest(r)
        if k not in first:
            first[k] = r; seen[k] = {d}
        elif d not in seen[k]:
            seen[k].add(d); bad.setdefault(k, [first[k]]).append(r)
    clean = [r for k, r in first.items() if k not in bad]
    return clean, bad


def ingest_batch(scoped, kind, rows, key_field):
    """Store the clean rows (tenant-screened, revisioned) and return (stored_keys, conflicts).  Conflicting rows are NOT stored; the caller holds them for review."""
    clean, bad = batch_conflicts(rows, key_field)
    stored = [scoped.put(kind, r[key_field], r).key for r in clean]
    for k in bad:
        scoped.log('ingest.conflict', f'{kind}/{k}', 'held', reason='same identifier, different content in one batch', detail={'rows': len(bad[k])})
    return stored, bad
