"""Contract for AuditLogPort (EDR-03).  Blueprint: Section 15 section 15.8 (audit evidence integrity), Section 04 section 17, Section 17 section 10."""
import dataclasses
from .. import ports
from .framework import case, check, raises, session, AUTH_ERRORS

S = 'audit_log'
PE = ports.PayloadInvalid


def two(env):
    return session(env, 'tokA', 'tenant-A', 'alice'), session(env, 'tokB', 'tenant-B', 'bob')


@case(S, 'AL-01', 'the first event has seq 1, a zero previous hash, and actor and tenant come from the context, never from arguments')
def al01(env):
    a, _ = two(env)
    e = env.audit.append(a, 'ingest.accept', 'invoice/INV-1', 'accepted', reason='ok', correlation_id='c1', detail={'n': 1})
    check(e.seq == 1 and e.prev_hash == '0' * 64 and len(e.hash) == 64, 'first event wrong')
    check(e.tenant_id == 'tenant-A' and e.actor == 'alice' and e.actor_kind == 'human', 'tenant or actor not taken from the context')
    check(env.audit.verify(a) == ports.VerifyResult(True, 1, None), 'a one-event chain should verify')


@case(S, 'AL-02', 'events chain: seq increases by one, each prev_hash is the previous hash, and the chain verifies')
def al02(env):
    a, _ = two(env)
    evs = [env.audit.append(a, 'e', f'r{i}', 'ok') for i in range(6)]
    check([e.seq for e in evs] == [1, 2, 3, 4, 5, 6], 'seq wrong')
    check(all(evs[i].prev_hash == evs[i - 1].hash for i in range(1, 6)) and len({e.hash for e in evs}) == 6, 'chain links wrong')
    v = env.audit.verify(a)
    check(v.ok and v.checked == 6, 'chain did not verify')


@case(S, 'AL-03', 'each tenant has its own chain: events are invisible across tenants and both chains start at seq 1')
def al03(env):
    a, b = two(env)
    env.audit.append(a, 'e', 'secret-resource-A', 'ok'); env.audit.append(a, 'e', 'r2', 'ok')
    eb = env.audit.append(b, 'e', 'r1', 'ok')
    check(eb.seq == 1 and eb.prev_hash == '0' * 64, 'tenant B chain shares tenant A chain')
    check([e.resource for e in env.audit.read(b)] == ['r1'] and len(env.audit.read(a)) == 2, 'read crossed tenants')
    check(env.audit.verify(a).ok and env.audit.verify(b).ok, 'chains should verify')


FACTORY_HOLDER = {}


@case(S, 'AL-04', 'tampering with any stored field of any event is detected, at or before that event')
def al04(env):
    for field_name, new in (('outcome', 'refused'), ('reason', 'edited'), ('actor', 'mallory'), ('resource', 'other'), ('event_type', 'x'), ('detail', {'forged': 1}),
                            ('time', '1999-01-01T00:00:00Z'), ('prev_hash', 'f' * 64), ('hash', 'f' * 64), ('correlation_id', 'forged')):
        env2 = FACTORY_HOLDER['factory']()
        a = session(env2, 'tokA', 'tenant-A', 'alice')
        for i in range(5):
            env2.audit.append(a, 'e', f'r{i}', 'ok', reason='fine', detail={'i': i})
        check(env2.audit.verify(a).ok, 'clean chain should verify')
        env2.audit._contract_tamper('tenant-A', 3, field_name, new)
        v = env2.audit.verify(a)
        check(v.ok is False and v.first_bad_seq is not None and v.first_bad_seq <= 3, f'tampering with {field_name} of event 3 not detected ({v})')


@case(S, 'AL-05', 'secrets and tokens in event detail are redacted at any depth and never stored or returned')
def al05(env):
    a, _ = two(env)
    env.audit.append(a, 'connector.config', 'conn/1', 'ok', detail={'password': 'hunter2', 'nested': {'api_key': 'KEY123', 'list': [{'Authorization': 'Bearer tok999'}]}, 'safe': 'visible'})
    ev = env.audit.read(a)[0]
    text = repr(ev)
    check(all(s not in text for s in ('hunter2', 'KEY123', 'tok999')), 'a secret value appears in the stored event')
    check(ev.detail['safe'] == 'visible', 'non-secret detail should be kept')
    check(env.audit.verify(a).ok, 'redaction must happen before hashing so the chain verifies')


@case(S, 'AL-06', 'floats, bad types and empty names are refused and add nothing')
def al06(env):
    a, _ = two(env)
    raises(PE, lambda: env.audit.append(a, 'e', 'r', 'ok', detail={'x': 1.5}), 'float detail')
    raises(PE, lambda: env.audit.append(a, 'e', 'r', 'ok', detail={1: 'x'}), 'non-string detail key')
    raises(PE, lambda: env.audit.append(a, '', 'r', 'ok'), 'empty event type')
    raises(PE, lambda: env.audit.append(a, 'e', None, 'ok'), 'resource None')
    raises(PE, lambda: env.audit.append(a, 'e', 'r', 'ok', reason=5), 'reason not a string')
    check(env.audit.read(a) == (), 'a refused append left an event')


@case(S, 'AL-07', 'returned events are copies: changing them never changes the log')
def al07(env):
    a, _ = two(env)
    env.audit.append(a, 'e', 'r', 'ok', detail={'k': {'v': 1}})
    ev = env.audit.read(a)[0]; ev.detail['k']['v'] = 999; ev.detail['x'] = 1
    check(env.audit.read(a)[0].detail == {'k': {'v': 1}} and env.audit.verify(a).ok, 'log changed through a returned event')


@case(S, 'AL-08', 'unverified, forged or missing contexts are refused by append, read and verify and add nothing')
def al08(env):
    a, _ = two(env)
    env.audit.append(a, 'e', 'r', 'ok')
    forged = dataclasses.replace(a, tenant_id='tenant-B')
    for call in (lambda c: env.audit.append(c, 'e', 'r', 'ok'), lambda c: env.audit.read(c), lambda c: env.audit.verify(c)):
        raises((ports.NoContext,), lambda f=call: f(None), 'a call with no context at all must raise NoContext')
    for bad in (forged, dataclasses.replace(a, seal='0' * len(a.seal)), 'tenant-A'):
        raises(AUTH_ERRORS, lambda c=bad: env.audit.append(c, 'e', 'r', 'ok'), 'append')
        raises(AUTH_ERRORS, lambda c=bad: env.audit.read(c), 'read')
        raises(AUTH_ERRORS, lambda c=bad: env.audit.verify(c), 'verify')
    check(len(env.audit.read(a)) == 1, 'a refused call added an event')


@case(S, 'AL-09', 'read supports from_seq and limit without skipping or repeating events')
def al09(env):
    a, _ = two(env)
    for i in range(7):
        env.audit.append(a, 'e', f'r{i}', 'ok')
    check([e.seq for e in env.audit.read(a, from_seq=4)] == [4, 5, 6, 7], 'from_seq wrong')
    check([e.seq for e in env.audit.read(a, from_seq=2, limit=3)] == [2, 3, 4], 'limit wrong')
    check([e.seq for e in env.audit.read(a)] == [1, 2, 3, 4, 5, 6, 7] and env.audit.read(a, from_seq=99) == (), 'default read or empty read wrong')


@case(S, 'AL-10', 'the port offers no way to change or remove events')
def al10(env):
    for name in ('update', 'delete', 'remove', 'clear', 'truncate', 'edit', 'replace', 'pop', 'set'):
        check(not hasattr(env.audit, name), f'audit log exposes a mutating method: {name}')


@case(S, 'AL-11', 'event time comes from the platform clock at the moment of append')
def al11(env):
    a, _ = two(env)
    e1 = env.audit.append(a, 'e', 'r', 'ok'); env.advance(90); e2 = env.audit.append(a, 'e', 'r', 'ok')
    check(e2.time > e1.time, 'time did not move with the clock')


@case(S, 'AL-12', 'the actor kind (human, service, ai) is recorded as authenticated')
def al12(env):
    ai = session(env, 'tokAI', 'tenant-A', 'assistant', kind='ai')
    sv = session(env, 'tokSV', 'tenant-A', 'worker', kind='service')
    check(env.audit.append(ai, 'e', 'r', 'ok').actor_kind == 'ai' and env.audit.append(sv, 'e', 'r', 'ok').actor_kind == 'service', 'actor kind not recorded')


@case(S, 'AL-13', 'a careful rewrite that recomputes the altered event\'s own hash is still detected, because the next event no longer links to it')
def al13(env):
    for field_name, new in (('outcome', 'refused'), ('actor', 'mallory'), ('detail', {'forged': 1}), ('resource', 'other'), ('time', '1999-01-01T00:00:00Z')):
        env2 = FACTORY_HOLDER['factory']()
        a = session(env2, 'tokA', 'tenant-A', 'alice')
        for i in range(5):
            env2.audit.append(a, 'e', f'r{i}', 'ok', detail={'i': i})
        env2.audit._contract_rewrite('tenant-A', 3, field_name, new)
        v = env2.audit.verify(a)
        check(v.ok is False and v.first_bad_seq is not None and v.first_bad_seq <= 4, f'a hash-recomputing rewrite of {field_name} on event 3 not detected ({v})')


@case(S, 'AL-14', 'an event that names another tenant, even with a recomputed hash and in last position, is detected')
def al14(env):
    env2 = FACTORY_HOLDER['factory']()
    a = session(env2, 'tokA', 'tenant-A', 'alice')
    for i in range(4):
        env2.audit.append(a, 'e', f'r{i}', 'ok')
    env2.audit._contract_rewrite('tenant-A', 4, 'tenant_id', 'tenant-B')
    v = env2.audit.verify(a)
    check(v.ok is False and v.first_bad_seq == 4, f'a foreign tenant_id on the last event not detected ({v})')
