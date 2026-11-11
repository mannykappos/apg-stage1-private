"""In-memory reference NotificationPort (a TEST DOUBLE that passes the EDR-10 contract) and the factory that builds the contract environment around it."""
import hashlib
from .. import canon, tenancy
from ..reference_impl import FakeClock, StaticContextProvider, _need
from .contracts_m5 import NotifyEnv
from .ports_m5 import NOTE_FIELDS, MAX_TEXT, NotificationInvalid, NotificationPort


def validate_note(note):
    if not isinstance(note, dict) or set(note) != set(NOTE_FIELDS):
        raise NotificationInvalid('a note has exactly the fields ' + ', '.join(NOTE_FIELDS))
    for k in NOTE_FIELDS:
        v = note[k]
        if not isinstance(v, str) or not v.strip() or len(v) > MAX_TEXT or any(ord(c) < 32 and c not in '\n\t' for c in v):
            raise NotificationInvalid(f'{k} must be a non-empty plain string of at most {MAX_TEXT} characters')


class InMemoryNotifier(NotificationPort):
    def __init__(self, provider, clock):
        self.provider, self.clock = provider, clock
        self._receipts, self._delivered, self._failing = {}, {}, False

    def send(self, ctx, note):
        _need(self.provider, ctx)
        clean, _ = tenancy.screen_payload(ctx, note)               # a note that names another tenant raises TenantMismatch
        validate_note(clean)
        key = (ctx.tenant_id, clean['dedup_key'])
        r = self._receipts.get(key)
        if r is not None and r['status'] == 'delivered':
            return dict(canon.deep_copy(r), status='duplicate')
        rid = hashlib.sha256(('%s|%s' % key).encode()).hexdigest()[:16]
        attempts = (r['attempts'] if r else 0) + 1
        if self._failing:
            r = {'receipt_id': rid, 'dedup_key': clean['dedup_key'], 'status': 'failed', 'attempts': attempts, 'error': 'TRANSPORT_UNAVAILABLE', 'at': self.clock.now()}
        else:
            r = {'receipt_id': rid, 'dedup_key': clean['dedup_key'], 'status': 'delivered', 'attempts': attempts, 'error': '', 'at': self.clock.now()}
            self._delivered.setdefault(ctx.tenant_id, []).append(canon.deep_copy(clean))
        self._receipts[key] = r
        return canon.deep_copy(r)

    def status(self, ctx, receipt_id):
        _need(self.provider, ctx)
        for (t, _), r in self._receipts.items():
            if t == ctx.tenant_id and r['receipt_id'] == receipt_id:
                return canon.deep_copy(r)
        return None

    def outstanding(self, ctx):
        _need(self.provider, ctx)
        return tuple(canon.deep_copy(r) for (t, _), r in sorted(self._receipts.items(), key=lambda kv: kv[1]['receipt_id']) if t == ctx.tenant_id and r['status'] == 'failed')

    def _contract_set_transport_failure(self, failing):
        self._failing = bool(failing)

    def _contract_delivered(self, tenant_id):
        return canon.deep_copy(self._delivered.get(tenant_id, []))


def notify_env(notifier_cls=InMemoryNotifier, provider_cls=StaticContextProvider):
    def factory():
        c = FakeClock()
        p = provider_cls(c)
        return NotifyEnv(p, notifier_cls(p, c), c.advance)
    return factory
