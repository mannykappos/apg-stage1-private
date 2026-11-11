"""DELIBERATELY BROKEN implementations of the ports.  They exist only to prove that the contract suites have teeth: every fault below must
make at least the listed contract cases fail.  Never use these for anything else.

FAULTS maps a fault id to (description, factory, expected failing case ids)."""
import copy, hashlib
from . import canon
from .contracts.framework import ContractEnv
from .ports import AuditEvent, AuthenticatedContext, Record, Unauthenticated, VerifyResult
from .reference_impl import (FakeClock, InMemoryAuditLog, InMemoryRecordStore, StaticContextProvider, ZERO_HASH, _event_hash, _need, redact)


def env_with(provider_cls=None, store_cls=None, audit_cls=None):
    def factory():
        c = FakeClock()
        p = (provider_cls or StaticContextProvider)(c)
        s = (store_cls or InMemoryRecordStore)(p)
        a = (audit_cls or InMemoryAuditLog)(p, c)
        return ContractEnv(p, s, a, c.advance)
    return factory


# ------------------------------------------------------------------ context provider faults
class AcceptsEmptyToken(StaticContextProvider):
    def resolve(self, credentials):
        if credentials in ('', None):
            self._contract_register_session('__default__', 'default-tenant', 'anonymous')
            return super().resolve('__default__')
        return super().resolve(credentials)


class NoSealCheck(StaticContextProvider):
    def verify(self, ctx):
        return isinstance(ctx, AuthenticatedContext)


class IgnoresRevocation(StaticContextProvider):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)

    def _contract_revoke(self, token):
        pass


class IgnoresExpiry(StaticContextProvider):
    def resolve(self, credentials):
        if credentials in self._sessions and credentials not in self._revoked:
            t, u, roles, kind, exp = self._sessions[credentials]
            self._sessions[credentials] = (t, u, roles, kind, '2999-01-01T00:00:00Z')
        return super().resolve(credentials)

    def verify(self, ctx):
        if not isinstance(ctx, AuthenticatedContext):
            return False
        import hmac
        return hmac.compare_digest(self._seal(ctx.fields()), ctx.seal)


class TenantFromCredentialString(StaticContextProvider):
    """Trusts a ';tenant_id=...' suffix on the credential."""
    def resolve(self, credentials):
        if isinstance(credentials, str) and ';tenant_id=' in credentials:
            tok, t = credentials.split(';tenant_id=', 1)
            ctx = super().resolve(tok)
            f = dict(ctx.fields(), tenant_id=t)
            return AuthenticatedContext(t, ctx.user_id, ctx.roles, ctx.actor_kind, ctx.session_id, ctx.expires_at, self._seal(f))
        return super().resolve(credentials)


class CaseInsensitiveToken(StaticContextProvider):
    def resolve(self, credentials):
        if isinstance(credentials, str):
            for k in self._sessions:
                if k.lower() == credentials.lower():
                    return super().resolve(k)
        return super().resolve(credentials)


# ------------------------------------------------------------------ record store faults
class GlobalNamespace(InMemoryRecordStore):
    """Keys are shared across tenants (the identifier-collision defect)."""
    def _view(self, ctx):
        return AuthenticatedContext('__shared__', ctx.user_id, ctx.roles, ctx.actor_kind, ctx.session_id, ctx.expires_at, ctx.seal)

    def _wrap(self, name):
        inner = getattr(InMemoryRecordStore, name)
        def f(ctx, *a, **k):
            _need(self.provider, ctx)
            real = self.provider.verify
            self.provider.verify = lambda c: True
            try:
                return inner(self, self._view(ctx), *a, **k)
            finally:
                self.provider.verify = real
        return f

    def put(self, ctx, *a, **k): return self._wrap('put')(ctx, *a, **k)
    def get(self, ctx, *a, **k): return self._wrap('get')(ctx, *a, **k)
    def history(self, ctx, *a, **k): return self._wrap('history')(ctx, *a, **k)
    def query(self, ctx, *a, **k): return self._wrap('query')(ctx, *a, **k)
    def atomic(self, ctx, *a, **k): return self._wrap('atomic')(ctx, *a, **k)


class QueryNoTenantFilter(InMemoryRecordStore):
    def query(self, ctx, kind, where=None):
        _need(self.provider, ctx)
        out = []
        for (t, k, key), h in self._d.items():
            if k == kind and all(f in h[-1].payload and h[-1].payload[f] == v for f, v in (where or {}).items()):
                out.append(self._mk(*(h[-1].tenant_id, h[-1].kind, h[-1].key, h[-1].revision, h[-1].payload, h[-1].payload_hash)))
        return tuple(sorted(out, key=lambda r: r.key))


class HistoryNoTenantFilter(InMemoryRecordStore):
    def history(self, ctx, kind, key):
        _need(self.provider, ctx)
        for (t, k, ky), h in self._d.items():
            if k == kind and ky == key:
                return tuple(self._mk(r.tenant_id, r.kind, r.key, r.revision, r.payload, r.payload_hash) for r in h)
        return ()


class PayloadTenantTrusted(InMemoryRecordStore):
    def atomic(self, ctx, ops):
        _need(self.provider, ctx)
        out = []
        for kind, key, payload, exp in ops:
            t = payload.get('tenant_id', ctx.tenant_id) if isinstance(payload, dict) else ctx.tenant_id
            if t != ctx.tenant_id:
                forged = AuthenticatedContext(t, ctx.user_id, ctx.roles, ctx.actor_kind, ctx.session_id, ctx.expires_at, ctx.seal)
                real = self.provider.verify; self.provider.verify = lambda c: True
                try:
                    out.extend(InMemoryRecordStore.atomic(self, forged, [(kind, key, payload, exp)]))
                finally:
                    self.provider.verify = real
            else:
                out.extend(InMemoryRecordStore.atomic(self, ctx, [(kind, key, payload, exp)]))
        return tuple(out)


class AcceptsFloats(InMemoryRecordStore):
    def _validate(self, kind, key, payload):
        import json
        return json.loads(json.dumps(payload)), hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class OverwritesInPlace(InMemoryRecordStore):
    def atomic(self, ctx, ops):
        res = InMemoryRecordStore.atomic(self, ctx, ops)
        for r in res:                                   # keep only the newest revision
            h = self._d[(ctx.tenant_id, r.kind, r.key)]
            self._d[(ctx.tenant_id, r.kind, r.key)] = [h[-1]]
        return res


class NotIdempotent(InMemoryRecordStore):
    def atomic(self, ctx, ops):
        _need(self.provider, ctx)
        out = []
        for kind, key, payload, exp in ops:
            p, h = self._validate(kind, key, payload)
            cur = self._latest(ctx.tenant_id, kind, key)
            rev = (cur.revision if cur else 0) + 1
            if exp is not None and exp != (rev - 1):
                from .ports import ConflictError
                raise ConflictError('conflict')
            rec = self._mk(ctx.tenant_id, kind, key, rev, p, h)
            self._d.setdefault((ctx.tenant_id, kind, key), []).append(rec)
            out.append(rec)
        return tuple(out)


class NoExpectedRevisionCheck(InMemoryRecordStore):
    def atomic(self, ctx, ops):
        return InMemoryRecordStore.atomic(self, ctx, [(k, ky, p, None) for k, ky, p, e in ops])


class AliasesReturned(InMemoryRecordStore):
    def _mk(self, t, kind, key, rev, payload, h):
        return Record(t, kind, key, rev, payload, h)          # no copy


class AliasesInput(InMemoryRecordStore):
    """Keeps the caller's own dict as the stored payload (reads still copy), so later changes by the caller change stored state."""
    def atomic(self, ctx, ops):
        res = InMemoryRecordStore.atomic(self, ctx, ops)
        for (kind, key, payload, exp), r in zip(ops, res):
            h = self._d[(ctx.tenant_id, kind, key)]
            h[-1] = Record(h[-1].tenant_id, h[-1].kind, h[-1].key, h[-1].revision, payload, h[-1].payload_hash)
        return res


class NonAtomicBatch(InMemoryRecordStore):
    def atomic(self, ctx, ops):
        out = []
        for op in ops:
            out.extend(InMemoryRecordStore.atomic(self, ctx, [op]))
        return tuple(out)


class NoVerifyOnGet(InMemoryRecordStore):
    def get(self, ctx, kind, key, revision=None):
        if isinstance(ctx, AuthenticatedContext):
            self.provider, real = _Always(self.provider), self.provider
            try:
                return InMemoryRecordStore.get(self, ctx, kind, key, revision)
            finally:
                self.provider = real
        return InMemoryRecordStore.get(self, ctx, kind, key, revision)


class _Always:
    def __init__(self, p): self.p = p
    def verify(self, ctx): return True


class CaseFoldKeys(InMemoryRecordStore):
    def atomic(self, ctx, ops):
        return InMemoryRecordStore.atomic(self, ctx, [(k, ky.lower() if isinstance(ky, str) else ky, p, e) for k, ky, p, e in ops])

    def get(self, ctx, kind, key, revision=None):
        return InMemoryRecordStore.get(self, ctx, kind, key.lower() if isinstance(key, str) else key, revision)


class QueryUsesFirstRevision(InMemoryRecordStore):
    def query(self, ctx, kind, where=None):
        _need(self.provider, ctx)
        out = []
        for (t, k, key), h in self._d.items():
            if t == ctx.tenant_id and k == kind and all(f in h[0].payload and h[0].payload[f] == v for f, v in (where or {}).items()):
                r = h[-1]
                out.append(self._mk(r.tenant_id, r.kind, r.key, r.revision, r.payload, r.payload_hash))
        return tuple(sorted(out, key=lambda r: r.key))


class WrongHash(InMemoryRecordStore):
    def _validate(self, kind, key, payload):
        p, h = InMemoryRecordStore._validate(self, kind, key, payload)
        return p, hashlib.sha256(repr(payload).encode()).hexdigest()


class ControlCharKeysAllowed(InMemoryRecordStore):
    def _validate(self, kind, key, payload):
        import re
        k2 = re.sub(r'[\x00-\x1f\x7f]', '_', key) if isinstance(key, str) else key
        kd2 = re.sub(r'[\x00-\x1f\x7f]', '_', kind) if isinstance(kind, str) else kind
        return InMemoryRecordStore._validate(self, kd2 or 'x', k2 or 'x', payload)


# ------------------------------------------------------------------ audit log faults
class VerifyAlwaysOk(InMemoryAuditLog):
    def verify(self, ctx):
        _need(self.provider, ctx)
        return VerifyResult(True, len(self._d.get(ctx.tenant_id, [])), None)


class HashIgnoresDetail(InMemoryAuditLog):
    def append(self, ctx, event_type, resource, outcome, reason='', correlation_id='', detail=None):
        ev = InMemoryAuditLog.append(self, ctx, event_type, resource, outcome, reason, correlation_id, detail)
        return ev


def _hash_nodetail(e):
    d = {k: getattr(e, k) for k in ('tenant_id', 'seq', 'time', 'actor', 'actor_kind', 'event_type', 'resource', 'outcome', 'reason', 'correlation_id', 'prev_hash')}
    return hashlib.sha256(canon.canonical(d).encode('ascii')).hexdigest()


class DetailNotHashed(InMemoryAuditLog):
    def append(self, ctx, event_type, resource, outcome, reason='', correlation_id='', detail=None):
        ev = InMemoryAuditLog.append(self, ctx, event_type, resource, outcome, reason, correlation_id, detail)
        chain = self._d[ctx.tenant_id]
        proto = AuditEvent(**{**ev.__dict__, 'hash': ''})
        chain[-1] = AuditEvent(**{**ev.__dict__, 'hash': _hash_nodetail(proto)})
        return chain[-1]

    def verify(self, ctx):
        _need(self.provider, ctx)
        prev = ZERO_HASH
        for i, e in enumerate(self._d.get(ctx.tenant_id, []), 1):
            if e.seq != i or e.prev_hash != prev or _hash_nodetail(e) != e.hash:
                return VerifyResult(False, i - 1, i)
            prev = e.hash
        return VerifyResult(True, len(self._d.get(ctx.tenant_id, [])), None)


class SharedChain(InMemoryAuditLog):
    def append(self, ctx, *a, **k):
        _need(self.provider, ctx)
        chain = self._d.setdefault('__all__', [])
        ev = InMemoryAuditLog.append(self, AuthenticatedContext('__all__', ctx.user_id, ctx.roles, ctx.actor_kind, ctx.session_id, ctx.expires_at, ctx.seal), *a, **{**k, **{}}) if False else None
        # emulate: one global chain that records the real tenant in the event
        prev = chain[-1].hash if chain else ZERO_HASH
        kw = dict(zip(('event_type', 'resource', 'outcome', 'reason', 'correlation_id', 'detail'), a))
        kw.update(k)
        proto = AuditEvent(ctx.tenant_id, len(chain) + 1, self.clock.now(), ctx.user_id, ctx.actor_kind, kw['event_type'], kw['resource'], kw['outcome'], kw.get('reason', ''), kw.get('correlation_id', ''), redact(canon.deep_copy(kw.get('detail') or {})), prev, '')
        ev = AuditEvent(**{**proto.__dict__, 'hash': _event_hash(proto)})
        chain.append(ev)
        return ev

    def read(self, ctx, from_seq=1, limit=None):
        _need(self.provider, ctx)
        sel = [e for e in self._d.get('__all__', []) if e.seq >= from_seq]
        return tuple(sel[:limit] if limit is not None else sel)

    def verify(self, ctx):
        _need(self.provider, ctx)
        return VerifyResult(True, len(self._d.get('__all__', [])), None)


class NoRedaction(InMemoryAuditLog):
    def append(self, ctx, event_type, resource, outcome, reason='', correlation_id='', detail=None):
        import apg.reference_impl as R
        real = R.redact
        R.redact = lambda x: x
        try:
            return InMemoryAuditLog.append(self, ctx, event_type, resource, outcome, reason, correlation_id, detail)
        finally:
            R.redact = real


class ActorKindAlwaysHuman(InMemoryAuditLog):
    def append(self, ctx, *a, **k):
        ev = InMemoryAuditLog.append(self, ctx, *a, **k)
        chain = self._d[ctx.tenant_id]
        proto = AuditEvent(**{**ev.__dict__, 'actor_kind': 'human', 'hash': ''})
        chain[-1] = AuditEvent(**{**proto.__dict__, 'hash': _event_hash(proto)})
        return chain[-1]


class MutableReturn(InMemoryAuditLog):
    def read(self, ctx, from_seq=1, limit=None):
        _need(self.provider, ctx)
        sel = [e for e in self._d.get(ctx.tenant_id, []) if e.seq >= from_seq]
        return tuple(sel[:limit] if limit is not None else sel)


class HasDelete(InMemoryAuditLog):
    def delete(self, ctx, seq):
        _need(self.provider, ctx)
        del self._d[ctx.tenant_id][seq - 1]


class NoAuthOnRead(InMemoryAuditLog):
    def read(self, ctx, from_seq=1, limit=None):
        if isinstance(ctx, AuthenticatedContext):
            chain = self._d.get(ctx.tenant_id, [])
            sel = [e for e in chain if e.seq >= from_seq]
            return tuple(sel[:limit] if limit is not None else sel)
        return InMemoryAuditLog.read(self, ctx, from_seq, limit)


class ChainLinkOnly(InMemoryAuditLog):
    """verify checks only that prev_hash links up, never recomputes any hash."""
    def verify(self, ctx):
        _need(self.provider, ctx)
        chain = self._d.get(ctx.tenant_id, [])
        prev = ZERO_HASH
        for i, e in enumerate(chain, 1):
            if e.prev_hash != prev:
                return VerifyResult(False, i - 1, i)
            prev = e.hash
        return VerifyResult(True, len(chain), None)


class HashOnlyNoLinks(InMemoryAuditLog):
    """verify recomputes each event's own hash but never checks that events link to each other."""
    def verify(self, ctx):
        _need(self.provider, ctx)
        chain = self._d.get(ctx.tenant_id, [])
        for i, e in enumerate(chain, 1):
            if e.seq != i or e.tenant_id != ctx.tenant_id or _event_hash(e) != e.hash:
                return VerifyResult(False, i - 1, i)
        return VerifyResult(True, len(chain), None)


class VerifyIgnoresEventTenant(InMemoryAuditLog):
    """verify checks links and hashes but not which tenant an event names."""
    def verify(self, ctx):
        _need(self.provider, ctx)
        chain = self._d.get(ctx.tenant_id, [])
        prev = ZERO_HASH
        for i, e in enumerate(chain, 1):
            if e.seq != i or e.prev_hash != prev or _event_hash(e) != e.hash:
                return VerifyResult(False, i - 1, i)
            prev = e.hash
        return VerifyResult(True, len(chain), None)


class AuditNoneContextUnauthenticated(InMemoryAuditLog):
    """a call with no context at all raises Unauthenticated instead of NoContext."""
    def append(self, ctx, *a, **k):
        if ctx is None: raise Unauthenticated('no credentials')
        return super().append(ctx, *a, **k)


class StoreNoneContextUnauthenticated(InMemoryRecordStore):
    """a call with no context at all raises Unauthenticated instead of NoContext."""
    def get(self, ctx, *a, **k):
        if ctx is None: raise Unauthenticated('no credentials')
        return super().get(ctx, *a, **k)


class ConstantTime(InMemoryAuditLog):
    def __init__(self, provider, clock):
        super().__init__(provider, FakeClock('2000-01-01T00:00:00Z'))


class AcceptsFloatDetail(InMemoryAuditLog):
    def append(self, ctx, event_type, resource, outcome, reason='', correlation_id='', detail=None):
        det = {k: v for k, v in (detail or {}).items() if not isinstance(v, float)}
        return InMemoryAuditLog.append(self, ctx, event_type, resource, outcome, reason, correlation_id, det)


class RedactAfterHash(InMemoryAuditLog):
    """Hash is computed over the raw detail, then the secrets are redacted: the chain no longer verifies."""
    def append(self, ctx, event_type, resource, outcome, reason='', correlation_id='', detail=None):
        ev = InMemoryAuditLog.append(self, ctx, event_type, resource, outcome, reason, correlation_id, detail)
        chain = self._d[ctx.tenant_id]
        raw = AuditEvent(**{**ev.__dict__, 'detail': canon.deep_copy(detail or {}), 'hash': ''})
        chain[-1] = AuditEvent(**{**ev.__dict__, 'hash': _event_hash(raw)})
        return chain[-1]


class ReadLimitOffByOne(InMemoryAuditLog):
    def read(self, ctx, from_seq=1, limit=None):
        return InMemoryAuditLog.read(self, ctx, from_seq, None if limit is None else limit + 1)


class SeqRestartsAfterGap(InMemoryAuditLog):
    """seq is taken from the number of retained events plus one, so events recorded after a purge would reuse a number."""
    pass


S = 'RS-'
FAULTS = {
 'F-TC-01': ('empty credential gets a default tenant', env_with(provider_cls=AcceptsEmptyToken), ['TC-02']),
 'F-TC-02': ('context seal is not checked', env_with(provider_cls=NoSealCheck), ['TC-05', 'RS-15', 'AL-08']),
 'F-TC-03': ('revocation is ignored', env_with(provider_cls=IgnoresRevocation), ['TC-03']),
 'F-TC-04': ('expiry is ignored', env_with(provider_cls=IgnoresExpiry), ['TC-04', 'RS-15']),
 'F-TC-05': ('tenant is read from the credential string', env_with(provider_cls=TenantFromCredentialString), ['TC-02']),
 'F-TC-06': ('credentials are case-insensitive', env_with(provider_cls=CaseInsensitiveToken), ['TC-02']),
 'F-RS-01': ('keys shared across tenants (identifier collision)', env_with(store_cls=GlobalNamespace), ['RS-05', 'RS-06']),
 'F-RS-02': ('query ignores the tenant', env_with(store_cls=QueryNoTenantFilter), ['RS-07']),
 'F-RS-03': ('history ignores the tenant', env_with(store_cls=HistoryNoTenantFilter), ['RS-05']),
 'F-RS-04': ('tenant taken from the payload', env_with(store_cls=PayloadTenantTrusted), ['RS-08']),
 'F-RS-05': ('floats are accepted', env_with(store_cls=AcceptsFloats), ['RS-09']),
 'F-RS-06': ('revisions are overwritten in place', env_with(store_cls=OverwritesInPlace), ['RS-02', 'RS-17']),
 'F-RS-07': ('identical replay appends a revision', env_with(store_cls=NotIdempotent), ['RS-03']),
 'F-RS-08': ('expected_revision is ignored', env_with(store_cls=NoExpectedRevisionCheck), ['RS-04']),
 'F-RS-09': ('returned payloads alias stored state', env_with(store_cls=AliasesReturned), ['RS-11']),
 'F-RS-10': ('input payload is stored by reference', env_with(store_cls=AliasesInput), ['RS-12']),
 'F-RS-11': ('batch is not atomic', env_with(store_cls=NonAtomicBatch), ['RS-13']),
 'F-RS-12': ('get does not verify the context', env_with(store_cls=NoVerifyOnGet), ['RS-15']),
 'F-RS-13': ('keys are case-folded', env_with(store_cls=CaseFoldKeys), ['RS-18']),
 'F-RS-14': ('query filters on the first revision', env_with(store_cls=QueryUsesFirstRevision), ['RS-07']),
 'F-RS-15': ('payload hash is not the canonical hash', env_with(store_cls=WrongHash), ['RS-01']),
 'F-RS-16': ('control characters in keys are rewritten', env_with(store_cls=ControlCharKeysAllowed), ['RS-10']),
 'F-AL-01': ('verify always reports ok', env_with(audit_cls=VerifyAlwaysOk), ['AL-04']),
 'F-AL-02': ('detail is not covered by the hash', env_with(audit_cls=DetailNotHashed), ['AL-04']),
 'F-AL-03': ('one chain shared by all tenants', env_with(audit_cls=SharedChain), ['AL-03']),
 'F-AL-04': ('secrets are not redacted', env_with(audit_cls=NoRedaction), ['AL-05']),
 'F-AL-05': ('actor kind always recorded as human', env_with(audit_cls=ActorKindAlwaysHuman), ['AL-12']),
 'F-AL-06': ('read returns live events', env_with(audit_cls=MutableReturn), ['AL-07']),
 'F-AL-07': ('log exposes a delete method', env_with(audit_cls=HasDelete), ['AL-10']),
 'F-AL-08': ('read does not verify the context', env_with(audit_cls=NoAuthOnRead), ['AL-08']),
 'F-AL-09': ('verify checks links but never recomputes hashes', env_with(audit_cls=ChainLinkOnly), ['AL-04']),
 'F-AL-10': ('event time does not follow the clock', env_with(audit_cls=ConstantTime), ['AL-11']),
 'F-AL-11': ('float detail is silently dropped, not refused', env_with(audit_cls=AcceptsFloatDetail), ['AL-06']),
 'F-AL-12': ('hash taken before redaction', env_with(audit_cls=RedactAfterHash), ['AL-05']),
 'F-AL-13': ('read limit off by one', env_with(audit_cls=ReadLimitOffByOne), ['AL-09']),
 'F-AL-14': ('verify checks each event\'s own hash but not the links between events', env_with(audit_cls=HashOnlyNoLinks), ['AL-13']),
 'F-AL-15': ('verify does not check which tenant an event names', env_with(audit_cls=VerifyIgnoresEventTenant), ['AL-14']),
 'F-AL-16': ('append with no context raises Unauthenticated, not NoContext', env_with(audit_cls=AuditNoneContextUnauthenticated), ['AL-08']),
 'F-RS-17': ('get with no context raises Unauthenticated, not NoContext', env_with(store_cls=StoreNoneContextUnauthenticated), ['RS-15']),
}
