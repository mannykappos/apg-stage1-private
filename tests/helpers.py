import csv, os
from . import _path                                         # noqa: F401
from apg.contracts.framework import ContractEnv
from apg.reference_impl import FakeClock, InMemoryAuditLog, InMemoryRecordStore, StaticContextProvider


def make_env():
    c = FakeClock(); p = StaticContextProvider(c)
    return ContractEnv(p, InMemoryRecordStore(p), InMemoryAuditLog(p, c), c.advance), c


def login(env, token, tenant, user='u1', roles=(), kind='human'):
    env.provider._contract_register_session(token, tenant, user, roles, kind, 3600)
    return env.provider.resolve(token)


def bz_rows(rel):
    from ._path import HERE_ROOT
    with open(os.path.join(HERE_ROOT, 'builder_zero', rel), encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))
