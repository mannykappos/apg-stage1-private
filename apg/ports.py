"""PORTS: the written contracts between APG's logic and the Anchor Engine (handoff register EDR-01, EDR-02, EDR-03).

Amir implements these on the real Engine.  The contract suites in apg/contracts/ define what each implementation must guarantee,
including failure behaviour.  The reference implementations in apg/reference_impl.py are in-memory test doubles that pass the contracts;
they are not a design for production storage.

Rules that apply to every port:
  * The tenant is taken ONLY from a verified AuthenticatedContext.  No port reads a tenant from a payload, key or filter.
  * Money and quantities are integers.  A float anywhere in a payload is refused.
  * Anything a port returns is an independent copy: changing it never changes stored state.
"""
from dataclasses import dataclass, field
from typing import NamedTuple, Optional


class PortError(Exception):
    pass


class Unauthenticated(PortError):
    """No credentials, unknown or expired or revoked session, or a context that fails verification."""


class NoContext(PortError):
    """A call was made without a context."""


class TenantMismatch(PortError):
    """A payload, key or argument claimed a tenant other than the authenticated one."""


class ConflictError(PortError):
    """expected_revision did not match the current revision."""


class PayloadInvalid(PortError):
    """Payload not storable: floats, non-string keys, unsupported types, bad kind/key."""


@dataclass(frozen=True)
class AuthenticatedContext:
    tenant_id: str
    user_id: str
    roles: tuple
    actor_kind: str          # 'human' | 'service' | 'ai'
    session_id: str
    expires_at: str          # ISO date-time, UTC, 'YYYY-MM-DDTHH:MM:SSZ'
    seal: str                # set by the issuing context port; proves the other fields were not altered

    def __post_init__(self):
        for f in ('tenant_id', 'user_id', 'session_id', 'expires_at', 'seal'):
            v = getattr(self, f)
            if not isinstance(v, str) or not v:
                raise NoContext(f'context field {f} must be a non-empty string')
        if not isinstance(self.roles, tuple) or not all(isinstance(r, str) and r for r in self.roles):
            raise NoContext('context roles must be a tuple of non-empty strings')
        if self.actor_kind not in ('human', 'service', 'ai'):
            raise NoContext('actor_kind must be human, service or ai')

    def fields(self):
        return {'tenant_id': self.tenant_id, 'user_id': self.user_id, 'roles': list(self.roles), 'actor_kind': self.actor_kind,
                'session_id': self.session_id, 'expires_at': self.expires_at}


@dataclass(frozen=True)
class Record:
    tenant_id: str
    kind: str
    key: str
    revision: int
    payload: dict
    payload_hash: str


@dataclass(frozen=True)
class AuditEvent:
    tenant_id: str
    seq: int
    time: str
    actor: str
    actor_kind: str
    event_type: str
    resource: str
    outcome: str
    reason: str
    correlation_id: str
    detail: dict
    prev_hash: str
    hash: str


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    checked: int
    first_bad_seq: Optional[int]


class TenantContextPort:
    """EDR-01.  Turns credentials into a verified context and verifies contexts presented later."""
    def resolve(self, credentials):
        """-> AuthenticatedContext.  Raises Unauthenticated for empty, unknown, expired or revoked credentials.  Takes NO payload."""
        raise NotImplementedError

    def verify(self, ctx):
        """-> bool.  True only if ctx is exactly what resolve issued and the session is still valid."""
        raise NotImplementedError

    # contract-test seams (test environments only; a real Engine implements them against its test session store)
    def _contract_register_session(self, token, tenant_id, user_id, roles=(), actor_kind='human', ttl_seconds=3600):
        raise NotImplementedError

    def _contract_revoke(self, token):
        raise NotImplementedError


class Guard(NamedTuple):
    """A condition in an atomic batch (APG-M7.3, EDR-35); see RecordStorePort.atomic.
      Guard('revision', kind, key, n)        the latest revision of kind/key is exactly n; n = 0 means the record must not exist
      Guard('query', kind, where, entries)   the latest records of this kind that query(kind, where) would return are exactly `entries`, a tuple of (key, revision): no record added,
                                             none changed, none missing.  where = None or {} means every record of the kind in the tenant."""
    check: str
    kind: str
    target: object
    expect: object


class RecordStorePort:
    """EDR-02.  Tenant-scoped, append-only-revision storage with atomic batches."""
    def put(self, ctx, kind, key, payload, expected_revision=None):
        """Append a revision and return the Record.  If payload equals the latest revision, nothing is appended and the latest is returned.
        expected_revision: None = no check; 0 = the record must not exist; n = latest must be n, else ConflictError."""
        raise NotImplementedError

    def get(self, ctx, kind, key, revision=None):
        """-> Record or None.  revision=None means the latest."""
        raise NotImplementedError

    def history(self, ctx, kind, key):
        """-> tuple of every Record revision, oldest first."""
        raise NotImplementedError

    def query(self, ctx, kind, where=None):
        """-> tuple of latest Records of this kind in this tenant whose payload has every top-level (field, value) in `where`; ordered by key."""
        raise NotImplementedError

    def atomic(self, ctx, ops):
        """ops = list of (kind, key, payload, expected_revision).  All succeed or none is applied.  -> tuple of Records.
        An op may instead be a Guard (added in APG-M7.3, EDR-35): a condition on the tenant's stored state that must hold when the batch commits, checked together with the writes as one
        indivisible step.  A guard writes nothing, returns nothing and needs no write permission for its kind.  If any guard does not hold, ConflictError is raised and nothing in the batch
        is applied.  Guards are evaluated against the state before the writes of the same batch.  A malformed guard raises PayloadInvalid.
        The whole batch is atomic with respect to every other call on the same store, including calls from concurrent callers."""
        raise NotImplementedError


class AuditLogPort:
    """EDR-03.  Append-only, tamper-evident, per-tenant event chain."""
    def append(self, ctx, event_type, resource, outcome, reason='', correlation_id='', detail=None):
        raise NotImplementedError

    def read(self, ctx, from_seq=1, limit=None):
        raise NotImplementedError

    def verify(self, ctx):
        """-> VerifyResult.  Recomputes the chain from what is stored."""
        raise NotImplementedError

    def _contract_tamper(self, tenant_id, seq, field_name, new_value):
        """Contract-test seam: alter stored data directly, as a database administrator or fault would."""
        raise NotImplementedError

    def _contract_rewrite(self, tenant_id, seq, field_name, new_value):
        """Contract-test seam: like _contract_tamper, but the attacker also recomputes that one event's own hash (a careful rewrite)."""
        raise NotImplementedError


class Clock:
    def now(self):
        raise NotImplementedError
