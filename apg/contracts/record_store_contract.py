"""Contract for RecordStorePort (EDR-02).  Blueprint: Section 04 sections 6, 7, 16; Section 15 section 15.5; Section 05 section 13 (immutable inputs)."""
import copy
from .. import canon, ports
from .framework import case, check, raises, session, AUTH_ERRORS

S = 'record_store'
PE = ports.PayloadInvalid


def two(env):
    return session(env, 'tokA', 'tenant-A', 'alice'), session(env, 'tokB', 'tenant-B', 'bob')


@case(S, 'RS-01', 'put then get returns the stored payload as revision 1, with its hash')
def rs01(env):
    a, _ = two(env)
    r = env.store.put(a, 'invoice', 'INV-1', {'ex_gst_cents': 1000, 'lines': [{'q': 1}]})
    g = env.store.get(a, 'invoice', 'INV-1')
    check(r.revision == 1 and g.revision == 1 and g.payload == {'ex_gst_cents': 1000, 'lines': [{'q': 1}]}, 'roundtrip wrong')
    check(g.tenant_id == 'tenant-A' and g.kind == 'invoice' and g.key == 'INV-1', 'record identity wrong')
    check(g.payload_hash == canon.digest(g.payload), 'payload_hash must equal the canonical SHA-256 of the payload')


@case(S, 'RS-02', 'a changed payload becomes a new revision; history keeps every revision, oldest first')
def rs02(env):
    a, _ = two(env)
    env.store.put(a, 'invoice', 'INV-1', {'v': 1}); r2 = env.store.put(a, 'invoice', 'INV-1', {'v': 2}); env.store.put(a, 'invoice', 'INV-1', {'v': 3})
    h = env.store.history(a, 'invoice', 'INV-1')
    check([x.revision for x in h] == [1, 2, 3] and [x.payload['v'] for x in h] == [1, 2, 3], 'history wrong')
    check(r2.revision == 2 and env.store.get(a, 'invoice', 'INV-1', 1).payload == {'v': 1} and env.store.get(a, 'invoice', 'INV-1').payload == {'v': 3}, 'revision access wrong')


@case(S, 'RS-03', 'putting an identical payload again creates no new revision (retry and replay safe)')
def rs03(env):
    a, _ = two(env)
    r1 = env.store.put(a, 'invoice', 'INV-1', {'v': 1})
    r2 = env.store.put(a, 'invoice', 'INV-1', {'v': 1})
    check(r2.revision == 1 and r2.payload_hash == r1.payload_hash, 'replay created a revision')
    check(len(env.store.history(a, 'invoice', 'INV-1')) == 1, 'history grew on replay')
    env.store.put(a, 'invoice', 'INV-1', {'v': 2}); env.store.put(a, 'invoice', 'INV-1', {'v': 1})
    check([x.revision for x in env.store.history(a, 'invoice', 'INV-1')] == [1, 2, 3], 'returning to an old payload is a legitimate new revision')


@case(S, 'RS-04', 'expected_revision: conflicts are refused and change nothing; 0 means must not exist')
def rs04(env):
    a, _ = two(env)
    env.store.put(a, 'invoice', 'INV-1', {'v': 1}, expected_revision=0)
    raises(ports.ConflictError, lambda: env.store.put(a, 'invoice', 'INV-1', {'v': 2}, expected_revision=0), 'expected 0 on existing')
    raises(ports.ConflictError, lambda: env.store.put(a, 'invoice', 'INV-1', {'v': 2}, expected_revision=5), 'stale expected')
    raises(ports.ConflictError, lambda: env.store.put(a, 'invoice', 'INV-1', {'v': 1}, expected_revision=3), 'stale expected, identical payload')
    raises(ports.ConflictError, lambda: env.store.put(a, 'invoice', 'INV-1', {'v': 2}, expected_revision='1'), 'string expected')
    raises(ports.ConflictError, lambda: env.store.put(a, 'invoice', 'INV-1', {'v': 2}, expected_revision=True), 'bool expected')
    check(len(env.store.history(a, 'invoice', 'INV-1')) == 1, 'a refused put changed state')
    check(env.store.put(a, 'invoice', 'INV-1', {'v': 2}, expected_revision=1).revision == 2, 'correct expected revision refused')


@case(S, 'RS-05', 'tenants never see each other: same kind and key hold separate records; a key held by one tenant is absent for the other')
def rs05(env):
    a, b = two(env)
    env.store.put(a, 'invoice', 'INV-1', {'who': 'A'}); env.store.put(b, 'invoice', 'INV-1', {'who': 'B'}); env.store.put(a, 'invoice', 'ONLY-A', {'who': 'A'})
    check(env.store.get(a, 'invoice', 'INV-1').payload == {'who': 'A'} and env.store.get(b, 'invoice', 'INV-1').payload == {'who': 'B'}, 'cross-read or overwrite')
    check(env.store.get(b, 'invoice', 'ONLY-A') is None, 'tenant B read a record only tenant A holds')
    check(env.store.history(b, 'invoice', 'ONLY-A') == (), 'tenant B saw history of tenant A record')
    check(env.store.get(b, 'invoice', 'ONLY-A', 1) is None, 'tenant B read a revision of tenant A record')


@case(S, 'RS-06', 'colliding identifiers across tenants keep independent revision counters')
def rs06(env):
    a, b = two(env)
    env.store.put(a, 'invoice', 'INV-0001', {'v': 1}); env.store.put(a, 'invoice', 'INV-0001', {'v': 2})
    rb = env.store.put(b, 'invoice', 'INV-0001', {'v': 'b1'})
    check(rb.revision == 1, 'tenant B revision counter was shared with tenant A')
    check([r.revision for r in env.store.history(a, 'invoice', 'INV-0001')] == [1, 2] and len(env.store.history(b, 'invoice', 'INV-0001')) == 1, 'history mixed tenants')


@case(S, 'RS-07', 'query returns only this tenant, only the latest revision, filtered, ordered by key')
def rs07(env):
    a, b = two(env)
    for k, p in (('C', {'s': 'x', 'n': 1}), ('A', {'s': 'x', 'n': 2}), ('B', {'s': 'y', 'n': 3})):
        env.store.put(a, 'po', k, p)
    env.store.put(a, 'po', 'A', {'s': 'y', 'n': 2})
    env.store.put(b, 'po', 'Z', {'s': 'x', 'n': 9})
    allA = env.store.query(a, 'po')
    check([r.key for r in allA] == ['A', 'B', 'C'], 'query order or scope wrong')
    check([r.key for r in env.store.query(a, 'po', {'s': 'x'})] == ['C'], 'filter used an old revision or ignored the filter')
    check([r.key for r in env.store.query(a, 'po', {'s': 'y', 'n': 2})] == ['A'], 'multi-field filter wrong')
    check([r.key for r in env.store.query(b, 'po')] == ['Z'] and env.store.query(a, 'nothing') == (), 'scope or empty result wrong')
    raises(PE, lambda: env.store.query(a, 'po', ['s']), 'where not a dict')


@case(S, 'RS-08', 'a tenant claim inside a payload is data only: it never moves the record to another tenant')
def rs08(env):
    a, b = two(env)
    env.store.put(a, 'invoice', 'INV-1', {'tenant_id': 'tenant-B', 'organisation_id': 'tenant-B', 'v': 1})
    check(env.store.get(b, 'invoice', 'INV-1') is None and env.store.query(b, 'invoice') == (), 'payload tenant claim leaked the record to tenant B')
    g = env.store.get(a, 'invoice', 'INV-1')
    check(g is not None and g.tenant_id == 'tenant-A', 'record not held under the authenticated tenant')


@case(S, 'RS-09', 'floats, NaN, non-string keys, non-dict and unsupported payloads are refused and change nothing')
def rs09(env):
    a, _ = two(env)
    for bad in ({'x': 1.5}, {'x': [1, {'y': 2.0}]}, {'x': float('nan')}, {'x': float('inf')}, {1: 'a'}, {'x': {2: 'a'}}, [1, 2], 'text', None, {'x': object()}, {'x': {1, 2}}, {'x': b'bytes'}):
        raises(PE, lambda p=bad: env.store.put(a, 'invoice', 'INV-X', p), f'put({bad!r})')
    check(env.store.get(a, 'invoice', 'INV-X') is None, 'a refused payload left a record')


@case(S, 'RS-10', 'bad kind or key values are refused')
def rs10(env):
    a, _ = two(env)
    for kind, key in (('', 'k'), ('k', ''), (None, 'k'), ('k', None), (5, 'k'), ('k', 5), ('bad\nkind', 'k'), ('k', 'bad\x00key'), ('k', 'x' * 201), ('x' * 201, 'k')):
        raises(PE, lambda kd=kind, ky=key: env.store.put(a, kd, ky, {'v': 1}), f'put kind={kind!r} key={key!r}')


@case(S, 'RS-11', 'what the store returns is a copy: changing it never changes stored state')
def rs11(env):
    a, _ = two(env)
    env.store.put(a, 'invoice', 'INV-1', {'lines': [{'q': 1}], 'meta': {'k': 'v'}})
    r = env.store.get(a, 'invoice', 'INV-1'); r.payload['lines'][0]['q'] = 999; r.payload['meta']['k'] = 'changed'; r.payload['new'] = 1
    for x in env.store.history(a, 'invoice', 'INV-1'):
        x.payload['lines'].append('junk')
    for x in env.store.query(a, 'invoice'):
        x.payload['meta']['k'] = 'again'
    check(env.store.get(a, 'invoice', 'INV-1').payload == {'lines': [{'q': 1}], 'meta': {'k': 'v'}}, 'stored state changed through a returned object')


@case(S, 'RS-12', 'the input is copied: changing it after put never changes stored state')
def rs12(env):
    a, _ = two(env)
    p = {'lines': [{'q': 1}]}
    env.store.put(a, 'invoice', 'INV-1', p)
    p['lines'][0]['q'] = 999; p['extra'] = True
    check(env.store.get(a, 'invoice', 'INV-1').payload == {'lines': [{'q': 1}]}, 'stored state changed through the caller object')


@case(S, 'RS-13', 'a batch is all-or-nothing: a bad or conflicting op applies none of the batch')
def rs13(env):
    a, _ = two(env)
    env.store.put(a, 'invoice', 'INV-1', {'v': 1})
    raises(PE, lambda: env.store.atomic(a, [('invoice', 'N1', {'v': 1}, None), ('invoice', 'N2', {'v': 1.5}, None)]), 'batch with a float')
    check(env.store.get(a, 'invoice', 'N1') is None, 'first op applied although a later op was invalid')
    raises(ports.ConflictError, lambda: env.store.atomic(a, [('invoice', 'N3', {'v': 1}, None), ('invoice', 'INV-1', {'v': 2}, 7)]), 'batch with a conflict')
    check(env.store.get(a, 'invoice', 'N3') is None and env.store.get(a, 'invoice', 'INV-1').revision == 1, 'a conflicting batch changed state')
    raises(PE, lambda: env.store.atomic(a, [('invoice', 'N4', {'v': 1}, None), ('bad op',)]), 'malformed op')
    check(env.store.get(a, 'invoice', 'N4') is None, 'malformed op left a partial batch')


@case(S, 'RS-14', 'within one batch operations apply in order on the same key, including expected_revision chains')
def rs14(env):
    a, _ = two(env)
    out = env.store.atomic(a, [('invoice', 'K', {'v': 1}, 0), ('invoice', 'K', {'v': 2}, 1), ('invoice', 'K', {'v': 2}, 2)])
    check([r.revision for r in out] == [1, 2, 2], 'batch revisions wrong (third op is an identical replay)')
    check([r.revision for r in env.store.history(a, 'invoice', 'K')] == [1, 2], 'history after batch wrong')


@case(S, 'RS-15', 'unverified, forged, expired or missing contexts are refused by every method and change nothing')
def rs15(env):
    import dataclasses
    a, _ = two(env)
    env.store.put(a, 'invoice', 'INV-1', {'v': 1})
    forged = dataclasses.replace(a, tenant_id='tenant-B')
    calls = (('put', lambda c: env.store.put(c, 'invoice', 'INV-2', {'v': 1})), ('get', lambda c: env.store.get(c, 'invoice', 'INV-1')),
             ('history', lambda c: env.store.history(c, 'invoice', 'INV-1')), ('query', lambda c: env.store.query(c, 'invoice')),
             ('atomic', lambda c: env.store.atomic(c, [('invoice', 'INV-3', {'v': 1}, None)])))
    for name, fn in calls:
        raises((ports.NoContext,), lambda f=fn: f(None), f'{name} with no context at all must raise NoContext')
    for bad in (forged, dataclasses.replace(a, seal='0' * len(a.seal)), 'tenant-A', {'tenant_id': 'tenant-A'}):
        for name, fn in (('put', lambda c: env.store.put(c, 'invoice', 'INV-2', {'v': 1})), ('get', lambda c: env.store.get(c, 'invoice', 'INV-1')),
                         ('history', lambda c: env.store.history(c, 'invoice', 'INV-1')), ('query', lambda c: env.store.query(c, 'invoice')),
                         ('atomic', lambda c: env.store.atomic(c, [('invoice', 'INV-3', {'v': 1}, None)]))):
            raises(AUTH_ERRORS, lambda c=bad, f=fn: f(c), f'{name} with {type(bad).__name__} context')
    env.advance(7200)
    raises(AUTH_ERRORS, lambda: env.store.get(a, 'invoice', 'INV-1'), 'get with expired context')
    fresh = session(env, 'tokA2', 'tenant-A', 'alice')
    check(env.store.get(fresh, 'invoice', 'INV-2') is None and env.store.get(fresh, 'invoice', 'INV-3') is None, 'a refused call left a record')


@case(S, 'RS-16', 'missing records: get is None, history is empty, out-of-range revisions are None')
def rs16(env):
    a, _ = two(env)
    check(env.store.get(a, 'invoice', 'NOPE') is None and env.store.history(a, 'invoice', 'NOPE') == (), 'missing record not reported as missing')
    env.store.put(a, 'invoice', 'INV-1', {'v': 1})
    for rev in (0, 2, -1, 99):
        check(env.store.get(a, 'invoice', 'INV-1', rev) is None, f'revision {rev} should be None')


@case(S, 'RS-17', 'an earlier revision never changes once a later one exists')
def rs17(env):
    a, _ = two(env)
    r1 = env.store.put(a, 'invoice', 'INV-1', {'v': 1})
    for i in range(2, 6):
        env.store.put(a, 'invoice', 'INV-1', {'v': i})
    again = env.store.get(a, 'invoice', 'INV-1', 1)
    check(again.payload == {'v': 1} and again.payload_hash == r1.payload_hash, 'revision 1 changed')


@case(S, 'RS-18', 'keys are compared exactly: no case folding, no Unicode normalisation, kinds are separate')
def rs18(env):
    a, _ = two(env)
    env.store.put(a, 'invoice', 'inv-1', {'v': 'lower'}); env.store.put(a, 'invoice', 'INV-1', {'v': 'upper'})
    env.store.put(a, 'invoice', 'é', {'v': 'composed'}); env.store.put(a, 'invoice', 'é', {'v': 'decomposed'})
    env.store.put(a, 'po', 'INV-1', {'v': 'other kind'}); env.store.put(a, 'invoice', 'INV-1 ', {'v': 'trailing space'})
    got = [env.store.get(a, 'invoice', k).payload['v'] for k in ('inv-1', 'INV-1', 'é', 'é', 'INV-1 ')]
    check(got == ['lower', 'upper', 'composed', 'decomposed', 'trailing space'] and env.store.get(a, 'po', 'INV-1').payload['v'] == 'other kind', 'keys were merged or normalised')
