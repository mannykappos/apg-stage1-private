"""Contract for TenantContextPort (EDR-01).  Blueprint: Section 04 section 6, Section 15 section 15.5 (client-supplied tenant is never proof of access)."""
import dataclasses
from .. import ports
from .framework import case, check, raises, session, AUTH_ERRORS

S = 'tenant_context'


@case(S, 'TC-01', 'a valid credential gives a context for exactly its tenant and user, and the context verifies')
def tc01(env):
    ctx = session(env, 'tokA', 'tenant-A', 'alice', ('reviewer',))
    check(ctx.tenant_id == 'tenant-A' and ctx.user_id == 'alice' and ctx.roles == ('reviewer',), 'context fields wrong')
    check(env.provider.verify(ctx) is True, 'fresh context did not verify')


@case(S, 'TC-02', 'empty, whitespace, None, non-string, unknown and tenant-bearing credentials are refused')
def tc02(env):
    session(env, 'tokA', 'tenant-A')
    for bad in ('', ' ', None, 123, 'unknown', 'tokA ', 'tokA;tenant_id=tenant-B', 'TOKA', b'tokA'):
        raises(ports.Unauthenticated, lambda b=bad: env.provider.resolve(b), f'resolve({bad!r})')


@case(S, 'TC-03', 'a revoked credential is refused, and contexts already issued from it stop verifying')
def tc03(env):
    ctx = session(env, 'tokA', 'tenant-A')
    env.provider._contract_revoke('tokA')
    raises(ports.Unauthenticated, lambda: env.provider.resolve('tokA'), 'resolve after revoke')
    check(env.provider.verify(ctx) is False, 'revoked session still verifies')


@case(S, 'TC-04', 'an expired session is refused, and its context stops verifying')
def tc04(env):
    ctx = session(env, 'tokA', 'tenant-A', ttl=60)
    check(env.provider.verify(ctx), 'should verify before expiry')
    env.advance(61)
    check(env.provider.verify(ctx) is False, 'expired context still verifies')
    raises(ports.Unauthenticated, lambda: env.provider.resolve('tokA'), 'resolve after expiry')


@case(S, 'TC-05', 'a context altered after issue (tenant, user, roles, expiry, seal) does not verify')
def tc05(env):
    ctx = session(env, 'tokA', 'tenant-A', 'alice', ('reviewer',), ttl=60)
    for ch in ({'tenant_id': 'tenant-B'}, {'user_id': 'bob'}, {'roles': ('reviewer', 'admin')}, {'expires_at': '2099-01-01T00:00:00Z'},
               {'actor_kind': 'service'}, {'seal': 'x' * len(ctx.seal)}, {'session_id': 'S-other'}):
        forged = dataclasses.replace(ctx, **ch)
        check(env.provider.verify(forged) is False, f'forged context {list(ch)} verified')


@case(S, 'TC-06', 'two tenants are kept apart even when they use the same user id')
def tc06(env):
    a = session(env, 'tokA', 'tenant-A', 'same-user')
    b = session(env, 'tokB', 'tenant-B', 'same-user')
    check(a.tenant_id != b.tenant_id and a.session_id != b.session_id, 'contexts not distinct')
    check(env.provider.verify(a) and env.provider.verify(b), 'both should verify')
    check(env.provider.verify(None) is False and env.provider.verify('tokA') is False and env.provider.verify({'tenant_id': 'tenant-A'}) is False, 'non-context objects must not verify')
