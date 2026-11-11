"""Contract suite for the M9.1 port: ProjectActionPort (EDR-31, cases AP-*).  Same method as the M2, M3 and M5 suites: an implementation supplies a FACTORY returning a fresh
ActionEnv(provider, port, advance) for every case; a case passes if it returns without raising; failure behaviour (the refusals) is tested as hard as success.
The port answers one question: may this verified context `action` ('view' or 'approve') the findings of `scope`?  Exactly True means yes; anything else, or an exception, is a refusal."""
import dataclasses
from .. import ports
from ..contracts.framework import check, session

CASES = []
AP = 'action'
TENANT = '*tenant*'                                               # the `where` of a tenant-level grant in the contract seams


@dataclasses.dataclass
class ActionEnv:
    provider: object          # TenantContextPort (contract seams: _contract_register_session, _contract_revoke)
    port: object              # ProjectActionPort, plus the seams _contract_grant(tenant, user, where, action) and _contract_revoke_grant(tenant, user, where, action)
    advance: object           # callable(seconds): moves the clock the implementation uses


def case(suite, cid, text):
    def deco(fn):
        CASES.append((suite, cid, text, fn))
        return fn
    return deco


def prj(p='PRJ-001'):
    return {'level': 'project', 'project': p}


TEN = {'level': 'tenant'}


def who(env, tenant='tenant-A', user='abby', token=None, ttl=3600):
    return session(env, token or f'tok-{tenant}-{user}', tenant, user, ('approver',), ttl=ttl)


def can(env, ctx, scope, action):
    """-> the port's answer, with an exception counted as a refusal (as the boundary does), and the answer must not be anything but a bool."""
    try:
        r = env.port.allows(ctx, scope, action)
    except Exception:
        return False
    check(r is True or r is False or r is None, 'the answer must be True or False, not %r' % (r,))
    return r is True


def exact(env, ctx, scope, action, want, msg):
    try:
        r = env.port.allows(ctx, scope, action)
    except Exception as e:
        raise AssertionError(msg + ': the port raised %s; it must answer, not raise' % type(e).__name__)
    check(r is want, '%s: expected exactly %r, got %r' % (msg, want, r))


@case(AP, 'AP-01', 'a granted action on a granted project is answered exactly True, for view and for approve separately')
def ap01(env):
    a = who(env)
    env.port._contract_grant('tenant-A', 'abby', 'PRJ-001', 'view')
    exact(env, a, prj(), 'view', True, 'view granted')
    exact(env, a, prj(), 'approve', False, 'approve not granted')
    env.port._contract_grant('tenant-A', 'abby', 'PRJ-001', 'approve')
    exact(env, a, prj(), 'approve', True, 'approve granted')


@case(AP, 'AP-02', 'with no grant at all the answer is exactly False, for every action')
def ap02(env):
    a = who(env)
    for act in ('view', 'approve'):
        exact(env, a, prj(), act, False, 'nothing granted, ' + act)
        exact(env, a, TEN, act, False, 'nothing granted at tenant level, ' + act)


@case(AP, 'AP-03', 'the right to view does not carry the right to approve')
def ap03(env):
    a = who(env)
    env.port._contract_grant('tenant-A', 'abby', 'PRJ-001', 'view')
    exact(env, a, prj(), 'approve', False, 'view only')


@case(AP, 'AP-04', 'a grant for one project is not a grant for another project')
def ap04(env):
    a = who(env)
    env.port._contract_grant('tenant-A', 'abby', 'PRJ-001', 'approve')
    exact(env, a, prj('PRJ-002'), 'approve', False, 'another project')
    exact(env, a, prj('prj-001'), 'approve', False, 'the same letters in another case')
    exact(env, a, prj('PRJ-001 '), 'approve', False, 'the same id with a trailing space')


@case(AP, 'AP-05', 'a project grant is not a tenant-level grant; a tenant-level grant is its own thing')
def ap05(env):
    a = who(env)
    env.port._contract_grant('tenant-A', 'abby', 'PRJ-001', 'approve')
    exact(env, a, TEN, 'approve', False, 'project grant, tenant-level scope')
    env.port._contract_grant('tenant-A', 'abby', TENANT, 'view')
    exact(env, a, TEN, 'view', True, 'tenant-level grant')
    exact(env, a, TEN, 'approve', False, 'tenant-level view, approve not granted')


@case(AP, 'AP-06', 'a grant belongs to its tenant: the same user id and project id in another tenant is refused')
def ap06(env):
    a = who(env, 'tenant-A')
    b = who(env, 'tenant-B')
    env.port._contract_grant('tenant-A', 'abby', 'PRJ-001', 'approve')
    exact(env, a, prj(), 'approve', True, 'own tenant')
    exact(env, b, prj(), 'approve', False, 'same user id and project in another tenant')


@case(AP, 'AP-07', 'a grant added or taken away is seen on the very next question (nothing is kept from an earlier answer)')
def ap07(env):
    a = who(env)
    exact(env, a, prj(), 'approve', False, 'before')
    env.port._contract_grant('tenant-A', 'abby', 'PRJ-001', 'approve')
    exact(env, a, prj(), 'approve', True, 'after the grant')
    env.port._contract_revoke_grant('tenant-A', 'abby', 'PRJ-001', 'approve')
    exact(env, a, prj(), 'approve', False, 'after the grant was taken away')
    env.port._contract_grant('tenant-A', 'abby', 'PRJ-001', 'approve')
    exact(env, a, prj(), 'approve', True, 'granted again')


@case(AP, 'AP-08', 'an action that is not exactly "view" or "approve" is refused, never raised, never granted by a near match')
def ap08(env):
    a = who(env)
    env.port._contract_grant('tenant-A', 'abby', 'PRJ-001', 'view')
    env.port._contract_grant('tenant-A', 'abby', 'PRJ-001', 'approve')
    for bad in ('delete', '', None, 'APPROVE', 'Approve', ' approve', 'approve ', ['approve'], 1, True, 'approve\x00'):
        exact(env, a, prj(), bad, False, 'action %r' % (bad,))


@case(AP, 'AP-09', 'a scope that is not exactly a project or the tenant is refused without raising')
def ap09(env):
    a = who(env)
    env.port._contract_grant('tenant-A', 'abby', 'PRJ-001', 'approve')
    for bad in (None, {}, 'PRJ-001', ['PRJ-001'], {'level': 'project'}, {'level': 'project', 'project': ''}, {'level': 'project', 'project': None}, {'level': 'project', 'project': ['PRJ-001']},
                {'level': 'galaxy'}, {'level': 'project', 'project': 7}, {'project': 'PRJ-001'}):
        exact(env, a, bad, 'approve', False, 'scope %r' % (bad,))


@case(AP, 'AP-10', 'the question does not change what it was given')
def ap10(env):
    a = who(env)
    env.port._contract_grant('tenant-A', 'abby', 'PRJ-001', 'approve')
    sc = prj()
    env.port.allows(a, sc, 'approve')
    check(sc == prj(), 'the scope was changed by the port: %r' % (sc,))
    sc2 = {'level': 'project', 'project': 'PRJ-009'}
    env.port.allows(a, sc2, 'approve')
    check(sc2 == {'level': 'project', 'project': 'PRJ-009'}, 'the scope was changed by the port for a refused project')


@case(AP, 'AP-11', 'a session that has ended is not allowed, whatever was granted')
def ap11(env):
    a = who(env, ttl=60)
    env.port._contract_grant('tenant-A', 'abby', 'PRJ-001', 'approve')
    exact(env, a, prj(), 'approve', True, 'live session')
    env.advance(61)
    check(not can(env, a, prj(), 'approve'), 'an expired session was allowed')


@case(AP, 'AP-12', 'a revoked session is not allowed')
def ap12(env):
    a = who(env, token='tok-revoke')
    env.port._contract_grant('tenant-A', 'abby', 'PRJ-001', 'approve')
    exact(env, a, prj(), 'approve', True, 'before the revocation')
    env.provider._contract_revoke('tok-revoke')
    check(not can(env, a, prj(), 'approve'), 'a revoked session was allowed')


@case(AP, 'AP-13', 'a context that was not issued by the context port (a forged one) is not allowed')
def ap13(env):
    a = who(env)
    env.port._contract_grant('tenant-A', 'abby', 'PRJ-001', 'approve')
    forged = ports.AuthenticatedContext(a.tenant_id, a.user_id, a.roles, a.actor_kind, a.session_id, a.expires_at, 'forged-seal')
    check(not can(env, forged, prj(), 'approve'), 'a forged context was allowed')
    other_user = ports.AuthenticatedContext(a.tenant_id, 'mallory', a.roles, a.actor_kind, a.session_id, a.expires_at, a.seal)
    check(not can(env, other_user, prj(), 'approve'), 'a context with a changed user was allowed')


@case(AP, 'AP-14', 'one person\'s grant is not another person\'s')
def ap14(env):
    a = who(env, user='abby')
    b = who(env, user='bruno')
    env.port._contract_grant('tenant-A', 'abby', 'PRJ-001', 'approve')
    exact(env, a, prj(), 'approve', True, 'the person granted')
    exact(env, b, prj(), 'approve', False, 'another person of the same tenant')


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
