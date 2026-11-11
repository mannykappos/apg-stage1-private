"""DELIBERATELY BROKEN NotificationPort implementations.  They exist only to prove the M5 contract suite has teeth: each fault must make at least the listed cases fail.  Never use
these for anything else.   FAULTS maps id -> (description, factory, expected failing case ids)."""
from .. import canon, tenancy
from ..reference_impl import _need
from .reference_m5 import InMemoryNotifier, notify_env, validate_note
import hashlib


class DuplicatesDelivered(InMemoryNotifier):
    def send(self, ctx, note):
        _need(self.provider, ctx)
        clean, _ = tenancy.screen_payload(ctx, note)
        validate_note(clean)
        self._delivered.setdefault(ctx.tenant_id, []).append(canon.deep_copy(clean))
        rid = hashlib.sha256(('%s|%s' % (ctx.tenant_id, clean['dedup_key'])).encode()).hexdigest()[:16]
        r = {'receipt_id': rid, 'dedup_key': clean['dedup_key'], 'status': 'delivered', 'attempts': 1, 'error': '', 'at': self.clock.now()}
        self._receipts[(ctx.tenant_id, clean['dedup_key'])] = r
        return canon.deep_copy(r)


class GlobalDedup(InMemoryNotifier):
    def send(self, ctx, note):
        _need(self.provider, ctx)
        clean, _ = tenancy.screen_payload(ctx, note)
        validate_note(clean)
        for (t, k), r in self._receipts.items():
            if k == clean['dedup_key'] and r['status'] == 'delivered':
                return dict(canon.deep_copy(r), status='duplicate')
        return super().send(ctx, note)


class SilentFailure(InMemoryNotifier):
    def send(self, ctx, note):
        r = super().send(ctx, note)
        if r['status'] == 'failed':
            r = dict(r, status='delivered', error='')
            self._receipts[(ctx.tenant_id, note['dedup_key'])] = dict(r)
        return r


class FailureBlocksRetry(InMemoryNotifier):
    def send(self, ctx, note):
        _need(self.provider, ctx)
        key = (ctx.tenant_id, note.get('dedup_key'))
        if key in self._receipts:
            return dict(canon.deep_copy(self._receipts[key]), status='duplicate')
        return super().send(ctx, note)


class FailureNotListed(InMemoryNotifier):
    def outstanding(self, ctx):
        _need(self.provider, ctx)
        return ()


class TrustsTenantClaim(InMemoryNotifier):
    def send(self, ctx, note):
        _need(self.provider, ctx)
        note = dict(note)
        tenant = note.pop('tenant_id', ctx.tenant_id)
        validate_note(note)
        self._delivered.setdefault(tenant, []).append(canon.deep_copy(note))
        return {'receipt_id': 'x', 'dedup_key': note['dedup_key'], 'status': 'delivered', 'attempts': 1, 'error': '', 'at': self.clock.now()}


class NoAuthentication(InMemoryNotifier):
    def send(self, ctx, note):
        class Fake:
            tenant_id = 'tenant-A'
        return super().send(ctx, note) if ctx is not None else InMemoryNotifier.send(self, _AnyCtx(self), note)

    def status(self, ctx, receipt_id):
        return None

    def outstanding(self, ctx):
        return ()


class _AnyCtx:
    def __init__(self, n):
        self.tenant_id = 'tenant-A'


class SharesReceipts(InMemoryNotifier):
    def status(self, ctx, receipt_id):
        _need(self.provider, ctx)
        for (t, _), r in self._receipts.items():
            if t == ctx.tenant_id and r['receipt_id'] == receipt_id:
                return r
        return None


class StatusAcrossTenants(InMemoryNotifier):
    def status(self, ctx, receipt_id):
        _need(self.provider, ctx)
        for (_, _k), r in self._receipts.items():
            if r['receipt_id'] == receipt_id:
                return canon.deep_copy(r)
        return None


class AcceptsMalformed(InMemoryNotifier):
    def send(self, ctx, note):
        _need(self.provider, ctx)
        self._delivered.setdefault(ctx.tenant_id, []).append(dict(note))
        return {'receipt_id': 'x', 'dedup_key': str(note.get('dedup_key')), 'status': 'delivered', 'attempts': 1, 'error': '', 'at': self.clock.now()}


class OutstandingListsEverything(InMemoryNotifier):
    def outstanding(self, ctx):
        _need(self.provider, ctx)
        return tuple(canon.deep_copy(r) for (t, _), r in sorted(self._receipts.items(), key=lambda kv: kv[1]['receipt_id']) if t == ctx.tenant_id)


class DuplicateGetsNewReceipt(InMemoryNotifier):
    def send(self, ctx, note):
        r = super().send(ctx, note)
        if r['status'] == 'duplicate':
            r = dict(r, receipt_id=r['receipt_id'][::-1])
        return r


class FailureLosesAttempts(InMemoryNotifier):
    def send(self, ctx, note):
        r = super().send(ctx, note)
        if r['status'] == 'delivered' and r['attempts'] > 1:
            r = dict(r, attempts=1)
            self._receipts[(ctx.tenant_id, note['dedup_key'])] = dict(r)
        return r


class AltersContent(InMemoryNotifier):
    def send(self, ctx, note):
        r = super().send(ctx, note)
        if r['status'] == 'delivered':
            self._delivered[ctx.tenant_id][-1]['body'] = self._delivered[ctx.tenant_id][-1]['body'][:10]
        return r


class DeliversOutOfOrder(InMemoryNotifier):
    def send(self, ctx, note):
        r = super().send(ctx, note)
        if r['status'] == 'delivered' and len(self._delivered[ctx.tenant_id]) > 1:
            self._delivered[ctx.tenant_id].reverse()
        return r


FAULTS = {
    'NF-01': ('every send is delivered, repeats included', notify_env(DuplicatesDelivered), ['NT-02', 'NT-06']),
    'NF-02': ('the dedup key is shared across tenants', notify_env(GlobalDedup), ['NT-04']),
    'NF-03': ('a transport failure is reported as delivered', notify_env(SilentFailure), ['NT-05']),
    'NF-04': ('a failed note blocks every later attempt as a duplicate', notify_env(FailureBlocksRetry), ['NT-06']),
    'NF-05': ('failed notes are not listed as outstanding', notify_env(FailureNotListed), ['NT-05', 'NT-12']),
    'NF-06': ('a tenant named in the note is trusted', notify_env(TrustsTenantClaim), ['NT-08']),
    'NF-07': ('no check that the caller is authenticated', notify_env(NoAuthentication), ['NT-09']),
    'NF-08': ('a receipt is returned as the stored object', notify_env(SharesReceipts), ['NT-10']),
    'NF-09': ('a receipt can be read by another tenant', notify_env(StatusAcrossTenants), ['NT-04', 'NT-11']),
    'NF-10': ('malformed notes are accepted', notify_env(AcceptsMalformed), ['NT-07']),
    'NF-11': ('outstanding lists delivered notes too', notify_env(OutstandingListsEverything), ['NT-12']),
    'NF-12': ('a duplicate is answered with a new receipt', notify_env(DuplicateGetsNewReceipt), ['NT-02']),
    'NF-13': ('the attempt count is lost on a successful retry', notify_env(FailureLosesAttempts), ['NT-06']),
    'NF-14': ('the delivered content is shortened', notify_env(AltersContent), ['NT-01']),
    'NF-15': ('later notes are delivered ahead of earlier ones', notify_env(DeliversOutOfOrder), ['NT-03']),
}
