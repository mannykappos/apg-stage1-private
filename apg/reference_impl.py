"""Reference (in-memory) implementations of the ports.  TEST DOUBLES that pass the contracts.  Not a production design."""
import datetime, hashlib, hmac, re, threading
from . import canon
from .ports import (AuditEvent, AuditLogPort, AuthenticatedContext, Clock, ConflictError, Guard, NoContext, PayloadInvalid, Record,
                    RecordStorePort, TenantContextPort, Unauthenticated, VerifyResult)

ZERO_HASH = '0' * 64
_SECRET_KEY = re.compile(r'(pass(word|wd)?|secret|token|api[_-]?key|authorization|credential|bearer|private[_-]?key)', re.I)
_ID_BAD = re.compile(r'[\x00-\x1f\x7f]')


class FakeClock(Clock):
    def __init__(self, start='2026-10-14T00:00:00Z'):
        self.t = datetime.datetime.strptime(start, '%Y-%m-%dT%H:%M:%SZ')

    def now(self):
        return self.t.strftime('%Y-%m-%dT%H:%M:%SZ')

    def advance(self, seconds):
        self.t += datetime.timedelta(seconds=seconds)


class StaticContextProvider(TenantContextPort):
    def __init__(self, clock, secret=b'reference-secret-not-for-production'):
        self.clock, self._secret, self._sessions, self._revoked = clock, secret, {}, set()

    def _seal(self, fields):
        return hmac.new(self._secret, canon.canonical(fields).encode('ascii'), hashlib.sha256).hexdigest()

    def _contract_register_session(self, token, tenant_id, user_id, roles=(), actor_kind='human', ttl_seconds=3600):
        exp = (datetime.datetime.strptime(self.clock.now(), '%Y-%m-%dT%H:%M:%SZ') + datetime.timedelta(seconds=ttl_seconds)).strftime('%Y-%m-%dT%H:%M:%SZ')
        self._sessions[token] = (tenant_id, user_id, tuple(roles), actor_kind, exp)

    def _contract_revoke(self, token):
        self._revoked.add(token)

    def resolve(self, credentials):
        if not isinstance(credentials, str) or not credentials or credentials not in self._sessions or credentials in self._revoked:
            raise Unauthenticated('credentials missing, unknown or revoked')
        t, u, roles, kind, exp = self._sessions[credentials]
        if exp <= self.clock.now():
            raise Unauthenticated('session expired')
        f = {'tenant_id': t, 'user_id': u, 'roles': list(roles), 'actor_kind': kind, 'session_id': 'S-' + hashlib.sha256(credentials.encode()).hexdigest()[:16], 'expires_at': exp}
        return AuthenticatedContext(t, u, roles, kind, f['session_id'], exp, self._seal(f))

    def verify(self, ctx):
        if not isinstance(ctx, AuthenticatedContext):
            return False
        if not hmac.compare_digest(self._seal(ctx.fields()), ctx.seal):
            return False
        if ctx.expires_at <= self.clock.now():
            return False
        for tok in self._revoked:
            if 'S-' + hashlib.sha256(tok.encode()).hexdigest()[:16] == ctx.session_id:
                return False
        return True


def _need(provider, ctx):
    if ctx is None:
        raise NoContext('no context supplied')
    if not provider.verify(ctx):
        raise Unauthenticated('context failed verification')


def _check_id(name, v):
    if not isinstance(v, str) or not v or len(v) > 200 or _ID_BAD.search(v):
        raise PayloadInvalid(f'{name} must be a non-empty string without control characters, at most 200 characters')


class InMemoryRecordStore(RecordStorePort):
    def __init__(self, provider):
        self.provider, self._d = provider, {}
        self._lock = threading.RLock()                          # APG-M7.3: every call is one indivisible step, also for concurrent callers
        self._commits = []                                      # the order in which revisions were appended: (tenant, kind, key, revision); read only by tests

    def _latest(self, t, kind, key):
        h = self._d.get((t, kind, key))
        return h[-1] if h else None

    def _validate(self, kind, key, payload):
        _check_id('kind', kind); _check_id('key', key)
        if not isinstance(payload, dict):
            raise PayloadInvalid('payload must be a dict')
        try:
            return canon.deep_copy(payload), canon.digest(payload)
        except canon.CanonError as e:
            raise PayloadInvalid(str(e))

    def _mk(self, t, kind, key, rev, payload, h):
        return Record(t, kind, key, rev, canon.deep_copy(payload), h)

    def put(self, ctx, kind, key, payload, expected_revision=None):
        return self.atomic(ctx, [(kind, key, payload, expected_revision)])[0]

    def _guard(self, t, g):
        """-> None if the guard holds, else the reason.  Raises PayloadInvalid if it is malformed."""
        if g.check not in ('revision', 'query'):
            raise PayloadInvalid("a guard is Guard('revision', kind, key, n) or Guard('query', kind, where, entries)")
        if g[0] == 'revision':
            _, kind, key, n = g
            _check_id('kind', kind); _check_id('key', key)
            if not isinstance(n, int) or isinstance(n, bool) or n < 0:
                raise PayloadInvalid('a revision guard needs a whole number of 0 or more')
            cur = self._latest(t, kind, key)
            have = cur.revision if cur else 0
            return None if have == n else f'{kind}/{key}: guarded at revision {n}, current {have}'
        _, kind, where, entries = g
        _check_id('kind', kind)
        if where is not None and not isinstance(where, dict):
            raise PayloadInvalid('where must be a dict or None')
        try:
            want = {(k, n) for k, n in entries}
        except (TypeError, ValueError):
            raise PayloadInvalid('query guard entries must be (key, revision) pairs')
        if len({k for k, _ in want}) != len(want) or not all(isinstance(k, str) and isinstance(n, int) and not isinstance(n, bool) and n >= 1 for k, n in want):
            raise PayloadInvalid('query guard entries must be distinct (key, revision) pairs with revisions of 1 or more')
        have = {(r.key, r.revision) for r in self._query(t, kind, where or {})}
        if have == want:
            return None
        added = sorted(k for k, _ in have - want if k not in {x for x, _ in want})
        gone = sorted(k for k, _ in want - have if k not in {x for x, _ in have})
        moved = sorted({k for k, _ in have ^ want} - set(added) - set(gone))
        return f'{kind} query changed: added {added}, missing {gone}, changed {moved}'

    def atomic(self, ctx, ops):
        with self._lock:
            return self._atomic(ctx, ops)

    def _atomic(self, ctx, ops):
        _need(self.provider, ctx)
        t = ctx.tenant_id
        guards = [op for op in ops if isinstance(op, Guard)]
        ops = [op for op in ops if not isinstance(op, Guard)]
        failed = [why for why in (self._guard(t, g) for g in guards) if why]
        if failed:
            raise ConflictError('guard failed: ' + '; '.join(failed))
        staged, plan = {}, []
        for op in ops:
            if not (isinstance(op, (tuple, list)) and len(op) == 4):
                raise PayloadInvalid('each op is (kind, key, payload, expected_revision)')
            kind, key, payload, exp = op
            p, h = self._validate(kind, key, payload)
            cur = staged.get((kind, key))
            if cur is None:
                cur = self._latest(t, kind, key)
            cur_rev = cur.revision if cur else 0
            if exp is not None and (not isinstance(exp, int) or isinstance(exp, bool) or exp != cur_rev):
                raise ConflictError(f'{kind}/{key}: expected revision {exp}, current {cur_rev}')
            if cur is not None and cur.payload_hash == h:
                plan.append(cur); continue                      # identical to latest: idempotent
            rec = self._mk(t, kind, key, cur_rev + 1, p, h)
            staged[(kind, key)] = rec
            plan.append(('new', rec))
        out = []
        for item in plan:                                       # nothing above mutated stored state: apply now
            if isinstance(item, tuple):
                rec = item[1]
                self._d.setdefault((t, rec.kind, rec.key), []).append(rec)
                self._commits.append((t, rec.kind, rec.key, rec.revision))
                out.append(self._mk(t, rec.kind, rec.key, rec.revision, rec.payload, rec.payload_hash))
            else:
                out.append(self._mk(t, item.kind, item.key, item.revision, item.payload, item.payload_hash))
        return tuple(out)

    def get(self, ctx, kind, key, revision=None):
        with self._lock:
            return self._get(ctx, kind, key, revision)

    def _get(self, ctx, kind, key, revision):
        _need(self.provider, ctx)
        h = self._d.get((ctx.tenant_id, kind, key))
        if not h:
            return None
        if revision is None:
            r = h[-1]
        elif isinstance(revision, int) and not isinstance(revision, bool) and 1 <= revision <= len(h):
            r = h[revision - 1]
        else:
            return None
        return self._mk(r.tenant_id, r.kind, r.key, r.revision, r.payload, r.payload_hash)

    def history(self, ctx, kind, key):
        with self._lock:
            _need(self.provider, ctx)
            return tuple(self._mk(r.tenant_id, r.kind, r.key, r.revision, r.payload, r.payload_hash) for r in self._d.get((ctx.tenant_id, kind, key), []))

    def query(self, ctx, kind, where=None):
        with self._lock:
            _need(self.provider, ctx)
            where = where or {}
            if not isinstance(where, dict):
                raise PayloadInvalid('where must be a dict')
            return self._query(ctx.tenant_id, kind, where)

    def _query(self, tenant, kind, where):
        out = []
        for (t, k, key), h in self._d.items():
            if t == tenant and k == kind:
                r = h[-1]
                if all(f in r.payload and r.payload[f] == v for f, v in where.items()):
                    out.append(self._mk(r.tenant_id, r.kind, r.key, r.revision, r.payload, r.payload_hash))
        return tuple(sorted(out, key=lambda r: r.key))


def redact(obj):
    """Replace the value of any key that looks like a secret, at any depth."""
    if isinstance(obj, dict):
        return {k: ('[REDACTED]' if _SECRET_KEY.search(k) else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    return obj


def _event_hash(e):
    d = {k: getattr(e, k) for k in ('tenant_id', 'seq', 'time', 'actor', 'actor_kind', 'event_type', 'resource', 'outcome', 'reason', 'correlation_id', 'detail', 'prev_hash')}
    return hashlib.sha256(canon.canonical(d).encode('ascii')).hexdigest()


class InMemoryAuditLog(AuditLogPort):
    def __init__(self, provider, clock):
        self.provider, self.clock, self._d = provider, clock, {}

    def append(self, ctx, event_type, resource, outcome, reason='', correlation_id='', detail=None):
        _need(self.provider, ctx)
        for n, v in (('event_type', event_type), ('resource', resource), ('outcome', outcome)):
            _check_id(n, v)
        for n, v in (('reason', reason), ('correlation_id', correlation_id)):
            if not isinstance(v, str):
                raise PayloadInvalid(n + ' must be a string')
        try:
            det = redact(canon.deep_copy(detail or {}))
        except canon.CanonError as e:
            raise PayloadInvalid(str(e))
        chain = self._d.setdefault(ctx.tenant_id, [])
        prev = chain[-1].hash if chain else ZERO_HASH
        proto = AuditEvent(ctx.tenant_id, len(chain) + 1, self.clock.now(), ctx.user_id, ctx.actor_kind, event_type, resource, outcome, reason, correlation_id, det, prev, '')
        ev = AuditEvent(**{**proto.__dict__, 'hash': _event_hash(proto)})
        chain.append(ev)
        return ev

    def read(self, ctx, from_seq=1, limit=None):
        _need(self.provider, ctx)
        chain = self._d.get(ctx.tenant_id, [])
        sel = [e for e in chain if e.seq >= from_seq]
        if limit is not None:
            sel = sel[:limit]
        return tuple(AuditEvent(**{**e.__dict__, 'detail': canon.deep_copy(e.detail)}) for e in sel)

    def verify(self, ctx):
        _need(self.provider, ctx)
        chain = self._d.get(ctx.tenant_id, [])
        prev = ZERO_HASH
        for i, e in enumerate(chain, 1):
            if e.seq != i or e.prev_hash != prev or e.tenant_id != ctx.tenant_id or _event_hash(e) != e.hash:
                return VerifyResult(False, i - 1, i)
            prev = e.hash
        return VerifyResult(True, len(chain), None)

    def _contract_tamper(self, tenant_id, seq, field_name, new_value):
        chain = self._d[tenant_id]
        e = chain[seq - 1]
        chain[seq - 1] = AuditEvent(**{**e.__dict__, field_name: new_value})

    def _contract_rewrite(self, tenant_id, seq, field_name, new_value):
        chain = self._d[tenant_id]
        e = chain[seq - 1]
        changed = AuditEvent(**{**e.__dict__, field_name: new_value})
        chain[seq - 1] = AuditEvent(**{**changed.__dict__, 'hash': _event_hash(changed)})
