"""Contract suite for the M5 port: NotificationPort (EDR-10, cases NT-*).  Same method as the M2 and M3 suites: an implementation supplies a FACTORY returning a fresh
NotifyEnv(provider, notifier, advance) for every case; a case passes if it returns without raising; failure behaviour is tested as hard as success."""
import dataclasses
from .. import ports
from ..contracts.framework import check, raises, session

CASES = []
NT = 'notification'
AUTH = (ports.Unauthenticated, ports.NoContext)


@dataclasses.dataclass
class NotifyEnv:
    provider: object
    notifier: object
    advance: object


def case(suite, cid, text):
    def deco(fn):
        CASES.append((suite, cid, text, fn))
        return fn
    return deco


def two(env):
    return session(env, 'tokA', 'tenant-A', 'svc-a', ('detection_service',), kind='service'), session(env, 'tokB', 'tenant-B', 'svc-b', ('detection_service',), kind='service')


def note(key='K-1', **kw):
    n = {'dedup_key': key, 'recipient_role': 'project_manager', 'subject': 'Finding FND-1 detected', 'body': 'Actual cost is above budget.', 'finding_id': 'FND-1', 'reason': 'new'}
    n.update(kw)
    return n


@case(NT, 'NT-01', 'a first note is delivered exactly once, with its content unchanged, and the receipt says delivered')
def nt01(env):
    a, _ = two(env)
    r = env.notifier.send(a, note())
    check(r['status'] == 'delivered' and r['attempts'] == 1 and r['dedup_key'] == 'K-1' and r['receipt_id'], 'receipt wrong: %r' % (r,))
    got = env.notifier._contract_delivered('tenant-A')
    check(got == [note()], 'the delivered content differs from what was sent: %r' % (got,))


@case(NT, 'NT-02', 'the same dedup key again is answered duplicate with the first receipt and nothing is delivered twice')
def nt02(env):
    a, _ = two(env)
    r1 = env.notifier.send(a, note())
    r2 = env.notifier.send(a, note(body='A different body but the same key'))
    check(r2['status'] == 'duplicate' and r2['receipt_id'] == r1['receipt_id'], 'a repeat must be answered duplicate with the first receipt: %r' % (r2,))
    check(len(env.notifier._contract_delivered('tenant-A')) == 1, 'the repeat was delivered')


@case(NT, 'NT-03', 'different dedup keys are different notifications and are both delivered, in order')
def nt03(env):
    a, _ = two(env)
    env.notifier.send(a, note('K-1'))
    r = env.notifier.send(a, note('K-2', reason='reopened'))
    check(r['status'] == 'delivered', 'second key not delivered')
    check([n['dedup_key'] for n in env.notifier._contract_delivered('tenant-A')] == ['K-1', 'K-2'], 'order or content wrong')


@case(NT, 'NT-04', 'tenants are separate: the same key in another tenant is delivered on its own, and one tenant cannot see the other\'s receipt')
def nt04(env):
    a, b = two(env)
    ra = env.notifier.send(a, note())
    rb = env.notifier.send(b, note())
    check(rb['status'] == 'delivered', 'tenant B\'s first note was treated as a duplicate of tenant A\'s')
    check(env.notifier.status(b, ra['receipt_id']) is None, 'tenant B can read tenant A\'s receipt')
    check(len(env.notifier._contract_delivered('tenant-A')) == 1 and len(env.notifier._contract_delivered('tenant-B')) == 1, 'a note reached the wrong tenant')
    check(env.notifier.outstanding(b) == (), 'outstanding must be empty')


@case(NT, 'NT-05', 'a delivery failure is visible: the receipt says failed, the note is listed as outstanding and nothing is reported delivered')
def nt05(env):
    a, _ = two(env)
    env.notifier._contract_set_transport_failure(True)
    r = env.notifier.send(a, note())
    check(r['status'] == 'failed' and r['error'], 'a failure must be reported as failed with an error code: %r' % (r,))
    out = env.notifier.outstanding(a)
    check(len(out) == 1 and out[0]['dedup_key'] == 'K-1' and out[0]['status'] == 'failed', 'a failed note must be listed as outstanding: %r' % (out,))
    check(env.notifier._contract_delivered('tenant-A') == [], 'a failed note was reported delivered')
    check(env.notifier.status(a, r['receipt_id'])['status'] == 'failed', 'status must say failed')


@case(NT, 'NT-06', 'a later attempt with the same key after a failure is delivered (a failure is not a duplicate); outstanding then clears')
def nt06(env):
    a, _ = two(env)
    env.notifier._contract_set_transport_failure(True)
    r1 = env.notifier.send(a, note())
    env.notifier._contract_set_transport_failure(False)
    r2 = env.notifier.send(a, note())
    check(r2['status'] == 'delivered' and r2['receipt_id'] == r1['receipt_id'] and r2['attempts'] == 2, 'the retry must deliver on the same receipt: %r' % (r2,))
    check(env.notifier.outstanding(a) == () and len(env.notifier._contract_delivered('tenant-A')) == 1, 'outstanding must clear and exactly one note be delivered')
    check(env.notifier.send(a, note())['status'] == 'duplicate', 'after delivery a repeat is a duplicate')


@case(NT, 'NT-07', 'a note that is not well formed is refused and nothing is delivered or recorded')
def nt07(env):
    a, _ = two(env)
    for bad in (note(dedup_key=''), note(subject='   '), note(body=5), note(reason=None), note(body='x' * 2001), note(body='bad\x00char'), {'dedup_key': 'K'}, note(extra='field')):
        raises(ports.PortError, lambda b=bad: env.notifier.send(a, b), 'a malformed note')
    check(env.notifier._contract_delivered('tenant-A') == [] and env.notifier.outstanding(a) == (), 'a refused note left a trace')


@case(NT, 'NT-08', 'a note that names another tenant is refused; a note naming the caller\'s own tenant has the claim stripped, never trusted')
def nt08(env):
    a, _ = two(env)
    raises(ports.TenantMismatch, lambda: env.notifier.send(a, dict(note(), tenant_id='tenant-B')), 'a note naming another tenant')
    check(env.notifier._contract_delivered('tenant-B') == [] and env.notifier._contract_delivered('tenant-A') == [], 'a refused note was delivered')
    r = env.notifier.send(a, dict(note('K-OWN'), tenant_id='tenant-A'))
    check(r['status'] == 'delivered' and env.notifier._contract_delivered('tenant-A') == [note('K-OWN')], 'a claim naming the caller\'s own tenant must be stripped, not stored')


@case(NT, 'NT-09', 'no context, a forged context and an expired session are refused for every method')
def nt09(env):
    a, _ = two(env)
    env.provider._contract_register_session('short', 'tenant-A', 'svc', ('detection_service',), 'service', 5)
    short = env.provider.resolve('short')
    env.advance(10)
    for ctx in (None, short):
        raises(AUTH, lambda c=ctx: env.notifier.send(c, note()), 'send without a valid context')
        raises(AUTH, lambda c=ctx: env.notifier.status(c, 'x'), 'status without a valid context')
        raises(AUTH, lambda c=ctx: env.notifier.outstanding(c), 'outstanding without a valid context')
    check(env.notifier._contract_delivered('tenant-A') == [], 'a note was delivered without a valid context')


@case(NT, 'NT-10', 'receipts returned to a caller are independent copies')
def nt10(env):
    a, _ = two(env)
    r = env.notifier.send(a, note())
    r['status'] = 'failed'
    r['attempts'] = 99
    again = env.notifier.status(a, r['receipt_id'])
    check(again['status'] == 'delivered' and again['attempts'] == 1, 'a receipt was shared with stored state')
    d = env.notifier.send(a, note())
    d['dedup_key'] = 'tampered'
    check(env.notifier.status(a, r['receipt_id'])['dedup_key'] == 'K-1', 'a duplicate answer was shared with stored state')
    s = env.notifier.status(a, r['receipt_id'])
    s['status'] = 'failed'
    check(env.notifier.status(a, r['receipt_id'])['status'] == 'delivered', 'a receipt returned by status was the stored object')


@case(NT, 'NT-11', 'status of an unknown receipt is None, not an error and not another tenant\'s receipt')
def nt11(env):
    a, b = two(env)
    check(env.notifier.status(a, 'no-such-receipt') is None, 'unknown receipt must be None')
    ra = env.notifier.send(a, note())
    check(env.notifier.status(b, ra['receipt_id']) is None, 'another tenant\'s receipt must look like a missing one')


@case(NT, 'NT-12', 'outstanding lists only this tenant\'s failures, in a stable order, and a delivered note never appears there')
def nt12(env):
    a, b = two(env)
    env.notifier.send(a, note('K-A'))
    env.notifier._contract_set_transport_failure(True)
    env.notifier.send(a, note('K-2'))
    env.notifier.send(a, note('K-3'))
    env.notifier.send(b, note('K-B'))
    out = env.notifier.outstanding(a)
    check(sorted(r['dedup_key'] for r in out) == ['K-2', 'K-3'], 'outstanding must list exactly this tenant\'s failed notes: %r' % ([r['dedup_key'] for r in out],))
    check([r['receipt_id'] for r in out] == sorted(r['receipt_id'] for r in out), 'order must be stable')


def run_all(factory, suites=None):
    """-> list of (suite, case_id, description, passed, detail)."""
    out = []
    for suite, cid, text, fn in CASES:
        if suites and suite not in suites:
            continue
        try:
            fn(factory())
            out.append((suite, cid, text, True, ''))
        except Exception as e:
            out.append((suite, cid, text, False, f'{type(e).__name__}: {e}'))
    return out
