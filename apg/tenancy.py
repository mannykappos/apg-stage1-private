"""Tenant-scope guards (EDR-01).  Blueprint: Section 04 section 6, Section 15 section 15.5.

Rule: the tenant is whatever the VERIFIED context says.  A tenant, organisation or similar identifier found anywhere in a payload, a filter,
a header-like field, or JSON hidden inside a string is a CLAIM.  It is never used to choose a tenant.  A claim that names a different tenant
is refused and audited; a claim that matches is removed from the data so nothing can later mistake it for scope."""
import json
from . import canon
from .ports import AuthenticatedContext, Guard, NoContext, PayloadInvalid, TenantMismatch, Unauthenticated

_ORG_NAMES = {'orgid', 'org', 'organisation', 'organization', 'organisationid', 'organizationid', 'organisationname', 'organizationname', 'orguuid', 'customerid', 'companyid', 'clientid'}
MAX_DEPTH = 32


def is_claim_key(key):
    n = canon.norm_key(key).replace('_', '')
    return 'tenant' in n or n in _ORG_NAMES


def find_claims(obj, path='$', depth=0, _embedded=False):
    """-> list of (path, key, value, embedded) for every tenant-like key at any depth, including inside JSON text held in strings."""
    if depth > MAX_DEPTH:
        raise TenantMismatch('payload nesting too deep to inspect safely')
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and is_claim_key(k):
                out.append((f'{path}.{k}', k, v, _embedded))
            out.extend(find_claims(v, f'{path}.{k}', depth + 1, _embedded))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            out.extend(find_claims(v, f'{path}[{i}]', depth + 1, _embedded))
    elif isinstance(obj, str):
        t = obj.strip()
        if t[:1] in ('{', '[') and len(t) < 1_000_000:
            try:
                inner = json.loads(t)
            except ValueError:
                inner = None
            if inner is not None:
                out.extend(find_claims(inner, path + '(json)', depth + 1, True))
    return out


def _strip(obj, depth=0):
    if depth > MAX_DEPTH:
        raise TenantMismatch('payload nesting too deep to inspect safely')
    if isinstance(obj, dict):
        return {k: _strip(v, depth + 1) for k, v in obj.items() if not (isinstance(k, str) and is_claim_key(k))}
    if isinstance(obj, (list, tuple)):
        return [_strip(v, depth + 1) for v in obj]
    if isinstance(obj, str) and find_claims(obj, depth=depth + 1):                 # a matching claim hidden in JSON text: remove it there too
        inner = json.loads(obj.strip())
        return json.dumps(_strip(inner, depth + 1), sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return obj


def _same(value, tenant_id):
    return isinstance(value, str) and canon.norm_key(value) == canon.norm_key(tenant_id) and value == tenant_id


def screen_payload(ctx, payload, audit=None):
    """-> (clean_payload, matching_claims).  Raises TenantMismatch if any claim names another tenant (or is not a plain matching string).
    The refusal is written to the audit log when `audit` is given."""
    if not isinstance(ctx, AuthenticatedContext):
        raise NoContext('a verified context is required')
    claims = find_claims(payload)
    bad = [c for c in claims if not _same(c[2], ctx.tenant_id)]
    if bad:
        if audit is not None:
            audit.append(ctx, 'tenant_claim.refused', bad[0][0], 'refused', reason='payload named a different tenant',
                         detail={'claims': [{'path': c[0], 'embedded': c[3]} for c in bad]})
        raise TenantMismatch(f'payload names another tenant at {bad[0][0]}')
    return _strip(payload), [(c[0], c[2]) for c in claims]


class ScopedStore:
    """A store and audit log bound to one verified context.  Callers cannot choose another tenant: there is no argument for it."""
    def __init__(self, store, audit, ctx):
        if not isinstance(ctx, AuthenticatedContext):
            raise NoContext('a verified context is required')
        self._store, self._audit, self.ctx = store, audit, ctx

    def put(self, kind, key, payload, expected_revision=None):
        clean, _ = screen_payload(self.ctx, payload, self._audit)
        return self._store.put(self.ctx, kind, key, clean, expected_revision)

    def atomic(self, ops):
        """An op may be a Guard (APG-M7.3; see RecordStorePort.atomic): it is passed on unchanged, except that a query guard's `where` is screened like a query filter (a tenant-like field
        is refused or removed, never honoured)."""
        cleaned = []
        for op in ops:
            if isinstance(op, Guard):
                if op.check == 'query' and isinstance(op.target, dict) and op.target:
                    screen_payload(self.ctx, op.target, self._audit)
                    op = op._replace(target=screen_payload(self.ctx, op.target)[0])
                cleaned.append(op)
                continue
            kind, key, payload, exp = op
            clean, _ = screen_payload(self.ctx, payload, self._audit)
            cleaned.append((kind, key, clean, exp))
        return self._store.atomic(self.ctx, cleaned)

    def get(self, kind, key, revision=None):
        return self._store.get(self.ctx, kind, key, revision)

    def history(self, kind, key):
        return self._store.history(self.ctx, kind, key)

    def query(self, kind, where=None):
        if where:
            screen_payload(self.ctx, where, self._audit)         # a tenant-like filter field is refused or ignored, never honoured
            where, _ = screen_payload(self.ctx, where)
        return self._store.query(self.ctx, kind, where)

    def log(self, event_type, resource, outcome, reason='', correlation_id='', detail=None):
        return self._audit.append(self.ctx, event_type, resource, outcome, reason, correlation_id, detail)


def bind_job(provider, store, audit, job):
    """Workers, retries and replays do not inherit a tenant from the message.  They re-authenticate: `job` = {'credentials': str, 'payload': dict,
    optional 'claimed_tenant'}.  Returns (ScopedStore, clean_payload)."""
    if not isinstance(job, dict) or 'credentials' not in job:
        raise Unauthenticated('job carries no credentials')
    ctx = provider.resolve(job['credentials'])
    scoped = ScopedStore(store, audit, ctx)
    claimed = job.get('claimed_tenant')
    if claimed is not None and not _same(claimed, ctx.tenant_id):
        audit.append(ctx, 'tenant_claim.refused', 'job', 'refused', reason='job named a different tenant')
        raise TenantMismatch('job names another tenant')
    clean, _ = screen_payload(ctx, job.get('payload', {}), audit)
    return scoped, clean
