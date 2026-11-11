"""Reference implementations of the outbound ports: IN-MEMORY TEST DOUBLES, NOT PRODUCTION.  They claim no persistence, durability, concurrency or performance (MIE-R-46,
MIE-L-13).  Each has switches that make it fail, for the failure-behaviour tests.  The host supplies the real ones (EDR-37)."""
import hashlib
from . import canon
from .ports import (ApprovalVerifierPort, AuditFailure, AuditLogPort, AuditQueryPort, ContextInvalid, ContextMissing, CostValueHookPort, HookUnavailable, LimitsConfig,
                    ObservationStorePort, PackRegistryPort, ResultStorePort, StoreFailure, TenantContextPort)

NON_PRODUCTION = True


class RefContext(TenantContextPort):
    """Opaque session tokens.  The host's clock is a callable it supplies; the core itself never reads one."""
    def __init__(self, host_clock):
        self.host_clock, self.sessions = host_clock, {}

    def register(self, token, tenant, expires_at):
        self.sessions[token] = (tenant, expires_at)

    def resolve(self, ctx):
        if ctx is None or ctx == '':
            raise ContextMissing()
        if not isinstance(ctx, str) or ctx not in self.sessions:
            raise ContextInvalid()
        tenant, exp = self.sessions[ctx]
        if self.host_clock() >= exp:
            raise ContextInvalid()
        return tenant


class _Failing:
    def __init__(self):
        self.fail_reads = self.fail_writes = False

    def _r(self):
        if self.fail_reads:
            raise StoreFailure()

    def _w(self):
        if self.fail_writes:
            raise StoreFailure()


class RefObservations(_Failing, ObservationStorePort):
    def __init__(self):
        super().__init__()
        self.d = {}
        self.fail_at_item = None

    def append(self, tenant, oid, obs):
        self._w()
        k = (tenant, oid)
        if k in self.d:
            return 'duplicate'
        self.d[k] = canon.copy(obs)
        return 'stored'

    def append_batch(self, tenant, items):
        """Staged, then applied in one step: a failure while staging (fail_writes, or fail_at_item, the index of the item at which to fail) leaves the store unchanged."""
        self._w()
        staged, out = {}, []
        for i, (oid, obs) in enumerate(items):
            if self.fail_at_item == i:
                raise StoreFailure()
            k = (tenant, oid)
            if k in self.d or k in staged:
                out.append('duplicate')
                continue
            staged[k] = canon.copy(obs)
            out.append('stored')
        self.d.update(staged)
        return out

    def get(self, tenant, oid):
        self._r()
        v = self.d.get((tenant, oid))
        return None if v is None else canon.copy(v)

    def for_subjects(self, tenant, subject_ids):
        self._r()
        return {oid: canon.copy(o) for (t, oid), o in sorted(self.d.items()) if t == tenant and o['subject_id'] in subject_ids}


class RefRegistry(_Failing, PackRegistryPort):
    def __init__(self):
        super().__init__()
        self.packs, self.withdrawn, self.acts = {}, {}, {}

    def put(self, pin, pack_bytes, publisher):
        self._w()
        k = (pin['pack_id'], pin['pack_version'])
        if k in self.packs:
            raise StoreFailure('immutable: already bound')
        self.packs[k] = {'pin': dict(pin), 'bytes': bytes(pack_bytes), 'publisher': publisher}

    def get(self, pack_id, pack_version):
        self._r()
        v = self.packs.get((pack_id, pack_version))
        return None if v is None else {'pin': dict(v['pin']), 'bytes': bytes(v['bytes']), 'publisher': v['publisher']}

    def withdraw(self, pin, record):
        self._w()
        self.withdrawn.setdefault(canon.digest(pin), canon.copy(record))

    def withdrawal(self, pin):
        self._r()
        v = self.withdrawn.get(canon.digest(pin))
        return None if v is None else canon.copy(v)

    def activate(self, tenant, pin, record):
        self._w()
        self.acts.setdefault((tenant, canon.digest(pin)), []).append(canon.copy(record))

    def activations(self, tenant, pin):
        self._r()
        return [canon.copy(r) for r in self.acts.get((tenant, canon.digest(pin)), [])]


class RefResults(_Failing, ResultStorePort):
    def __init__(self):
        super().__init__()
        self.d = {}

    def put(self, tenant, rid, body):
        self._w()
        if (tenant, rid) in self.d:
            return 'duplicate'
        self.d[(tenant, rid)] = canon.copy(body)
        return 'stored'

    def get(self, tenant, rid):
        self._r()
        v = self.d.get((tenant, rid))
        return None if v is None else canon.copy(v)


class RefAudit(AuditLogPort, AuditQueryPort):
    """One hash chain per tenant.  `down` makes every append fail; `fail_after` lets that many appends succeed and then fails."""
    def __init__(self):
        self.chains, self.down, self.fail_after = {}, False, None

    def append(self, tenant, event):
        if self.down or (self.fail_after is not None and self.fail_after <= 0):
            raise AuditFailure()
        if self.fail_after is not None:
            self.fail_after -= 1
        chain = self.chains.setdefault(tenant, [])
        prev = chain[-1]['hash'] if chain else '0' * 64
        e = {'seq': len(chain) + 1, 'event': canon.copy(event), 'prev': prev}
        e['hash'] = hashlib.sha256(canon.dumps({'seq': e['seq'], 'event': e['event'], 'prev': prev})).hexdigest()
        chain.append(e)
        return {'seq': e['seq'], 'hash': e['hash']}

    def last_seq(self, tenant):
        if self.down:
            raise AuditFailure()
        return len(self.chains.get(tenant, []))

    def read(self, tenant, from_seq, upto_seq, limit):
        if self.down:
            raise AuditFailure()
        return [canon.copy(e) for e in self.chains.get(tenant, []) if from_seq <= e['seq'] <= upto_seq][:limit]

    def verify(self, tenant):
        if self.down:
            raise AuditFailure()
        prev = '0' * 64
        chain = self.chains.get(tenant, [])
        for e in chain:
            h = hashlib.sha256(canon.dumps({'seq': e['seq'], 'event': e['event'], 'prev': prev})).hexdigest()
            if e['prev'] != prev or e['hash'] != h:
                return {'ok': False, 'events': len(chain), 'broken_at': e['seq']}
            prev = e['hash']
        return {'ok': True, 'events': len(chain), 'broken_at': None}


class RefApprovals(ApprovalVerifierPort):
    """Approval references the host has registered: (approval_ref) -> (approver, pin digest, tenant).  The approver may not be the pack's author (no self-approval)."""
    def __init__(self):
        self.d = {}

    def register(self, approval_ref, approver, pin, tenant):
        self.d[approval_ref] = (approver, canon.digest(pin), tenant)

    def verify(self, tenant, approval_ref, pin, pack_doc):
        v = self.d.get(approval_ref)
        return v is not None and v[1] == canon.digest(pin) and v[2] == tenant and v[0] != pack_doc['provenance']['author_ref']


class RefHooks(CostValueHookPort):
    """A slot with nothing registered: every call is HOOK_UNAVAILABLE (no hook formula exists in MIE-1)."""
    def __init__(self):
        self.impl = {}

    def call(self, hook_id, inputs):
        if hook_id not in self.impl:
            raise HookUnavailable(hook_id)
        return self.impl[hook_id](inputs)


class RefLimits(LimitsConfig):
    def __init__(self, values=None):
        self.values = values

    def limits(self):
        return None if self.values is None else dict(self.values)
