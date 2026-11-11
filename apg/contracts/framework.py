"""Tiny contract-test framework (standard library only).

An implementation supplies a FACTORY: a zero-argument callable that returns a fresh ContractEnv.  Every case gets a fresh environment, so cases
cannot depend on each other.  A case passes if it returns without raising.  Cases check behaviour, including failure behaviour."""
import dataclasses, traceback
from .. import ports


@dataclasses.dataclass
class ContractEnv:
    provider: object          # TenantContextPort
    store: object             # RecordStorePort
    audit: object             # AuditLogPort
    advance: object           # callable(seconds): moves the clock the implementation uses


class Fail(AssertionError):
    pass


def check(cond, msg):
    if not cond:
        raise Fail(msg)


def raises(types, fn, msg=''):
    try:
        fn()
    except types:
        return
    except Exception as e:                                           # wrong exception type is a failure
        raise Fail(f'{msg or "call"} raised {type(e).__name__}: {e}; expected {types}')
    raise Fail(f'{msg or "call"} did not raise {types}')


def session(env, token, tenant, user='user-1', roles=(), kind='human', ttl=3600):
    env.provider._contract_register_session(token, tenant, user, roles, kind, ttl)
    return env.provider.resolve(token)


AUTH_ERRORS = (ports.Unauthenticated, ports.NoContext)

CASES = []          # (suite, case_id, description, function)


def case(suite, cid, text):
    def deco(fn):
        CASES.append((suite, cid, text, fn))
        return fn
    return deco


def run_suite(factory, suites=None):
    """-> list of (suite, case_id, description, passed, detail)."""
    from . import tenant_context_contract, record_store_contract, audit_log_contract   # noqa: F401  (register cases)
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
