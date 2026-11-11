"""Outbound ports of the core (MIE1_SPEC section 10.2; MIE1_PORTS.csv PT-01 to PT-10, without PT-06, which is adapter-side).  Everything the core needs from its environment
comes through these; none assumes a database, queue, scheduler, vendor or deployment.  The core has no clock port because it reads no clock."""


class StoreFailure(Exception):
    """A store port failed.  The core turns it into STORE_UNAVAILABLE and fails closed."""


class AuditFailure(Exception):
    """The audit sink failed.  The core turns it into AUDIT_UNAVAILABLE and fails closed."""


class ContextMissing(Exception):
    pass


class ContextInvalid(Exception):
    pass


class HookUnavailable(Exception):
    pass


class TenantContextPort:          # PT-01 (the shape of EDR-01)
    def resolve(self, ctx):
        """-> the verified tenant identifier.  Raises ContextMissing for no context and ContextInvalid for a forged, expired or unverifiable one."""
        raise NotImplementedError


class ObservationStorePort:       # PT-02: append-only, tenant-scoped
    def append(self, tenant, observation_id, observation):
        """-> 'stored' or 'duplicate'.  Never overwrites."""
        raise NotImplementedError

    def append_batch(self, tenant, items):
        """items: [(observation_id, observation)].  All or nothing (MIE-1.1): either every item is stored (an identifier already held is left as it is) or, if
        the store fails, none is, and StoreFailure is raised.  -> ['stored' or 'duplicate', ...] in order."""
        raise NotImplementedError

    def get(self, tenant, observation_id):
        """-> an independent copy, or None."""
        raise NotImplementedError

    def for_subjects(self, tenant, subject_ids):
        """-> {observation_id: copy} for every observation of these subjects held for this tenant."""
        raise NotImplementedError


class PackRegistryPort:           # PT-03: immutable, hash-bound; withdrawal and activation records beside the bytes
    def put(self, pin, pack_bytes, publisher):
        raise NotImplementedError

    def get(self, pack_id, pack_version):
        """-> {'pin', 'bytes', 'publisher'} or None."""
        raise NotImplementedError

    def withdraw(self, pin, record):
        raise NotImplementedError

    def withdrawal(self, pin):
        raise NotImplementedError

    def activate(self, tenant, pin, record):
        """Appends an activation record; a later activation never edits an earlier one."""
        raise NotImplementedError

    def activations(self, tenant, pin):
        """-> the list of this tenant's activation records for the pin, oldest first."""
        raise NotImplementedError


class ResultStorePort:            # PT-04: content-addressed
    def put(self, tenant, result_id, body):
        """-> 'stored' or 'duplicate'."""
        raise NotImplementedError

    def get(self, tenant, result_id):
        raise NotImplementedError


class AuditLogPort:               # PT-05: append only (the shape of EDR-03 append)
    def append(self, tenant, event):
        """-> {'seq', 'hash'}.  Raises AuditFailure; a failure is surfaced, never swallowed."""
        raise NotImplementedError


class CostValueHookPort:          # PT-07: a declared slot; no hook formula exists in MIE-1
    def call(self, hook_id, inputs):
        """Pure and deterministic, integers in and out.  Raises HookUnavailable."""
        raise NotImplementedError


class ApprovalVerifierPort:       # PT-08
    def verify(self, tenant, approval_ref, pin, pack_doc):
        """-> True only if the reference is a genuine owner approval of exactly this pin.  The core cannot approve a pack."""
        raise NotImplementedError


class LimitsConfig:               # PT-09: host-supplied bounds; the core ships no value
    def limits(self):
        """-> a dict with every key of vocab.LIMIT_KEYS, or None."""
        raise NotImplementedError


class AuditQueryPort:             # PT-10: read-only, tenant-scoped (the shape of EDR-03 read and verify)
    def last_seq(self, tenant):
        raise NotImplementedError

    def read(self, tenant, from_seq, upto_seq, limit):
        """-> copies of this tenant's events with from_seq <= seq <= upto_seq, at most limit."""
        raise NotImplementedError

    def verify(self, tenant):
        """-> {'ok': bool, 'events': n, 'broken_at': seq or None}."""
        raise NotImplementedError
