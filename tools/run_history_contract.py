#!/usr/bin/env python3
"""Run the record-store history contract (APG-F67.3, EDR-41: apg/contracts/record_store_history_contract.py, cases RH-01 to RH-06) against the in-memory reference store, and
show that it catches four deliberately faulty stores (each must fail at least the named case).
Usage: python3 -I tools/run_history_contract.py [--factory module:attr] [--path dir]
With --factory, runs the cases against that store only (the factory returns a fresh ContractEnv, as for tools/run_contracts.py).  Exit 0 only if everything expected holds."""
import importlib, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True
args = sys.argv[1:]


def opt(n):
    return args[args.index(n) + 1] if n in args else None


if opt('--path'):
    sys.path.insert(0, opt('--path'))
from apg.contracts.framework import ContractEnv                              # noqa: E402
from apg.contracts.record_store_history_contract import run_history_suite    # noqa: E402
from apg.reference_impl import FakeClock, StaticContextProvider, InMemoryRecordStore, InMemoryAuditLog   # noqa: E402


class OutOfRangeReadsLatest(InMemoryRecordStore):
    """Reads revision 0 or a negative revision like a list index (so 0 reads the latest)."""
    def _get(self, ctx, kind, key, revision):
        h = self._d.get((ctx.tenant_id, kind, key))
        if h and isinstance(revision, int) and not isinstance(revision, bool) and revision < 1:
            r = h[revision - 1]
            return self._mk(r.tenant_id, r.kind, r.key, r.revision, r.payload, r.payload_hash)
        return super()._get(ctx, kind, key, revision)


class LeaksStoredObjects(InMemoryRecordStore):
    """Hands callers the stored payload object itself, so a caller can change history."""
    def _get(self, ctx, kind, key, revision):
        h = self._d.get((ctx.tenant_id, kind, key))
        if h and isinstance(revision, int) and not isinstance(revision, bool) and 1 <= revision <= len(h):
            return h[revision - 1]
        return super()._get(ctx, kind, key, revision)


class AppendsIdentical(InMemoryRecordStore):
    """Appends a revision even for a payload identical to the latest."""
    def _atomic(self, ctx, ops):
        out = []
        for op in ops:
            kind, key, payload, exp = op
            cur = self._latest(ctx.tenant_id, kind, key)
            if cur is not None and cur.payload == payload:
                rec = self._mk(ctx.tenant_id, kind, key, cur.revision + 1, payload, cur.payload_hash)
                self._d[(ctx.tenant_id, kind, key)].append(rec)
                out.append(rec)
            else:
                out.extend(super()._atomic(ctx, [op]))
        return tuple(out)


class RewritesHistory(InMemoryRecordStore):
    """Rewrites the previous revision in place when a new one is written."""
    def _atomic(self, ctx, ops):
        res = super()._atomic(ctx, ops)
        for r in res:
            h = self._d.get((ctx.tenant_id, r.kind, r.key), [])
            if len(h) >= 2:
                prev = h[-2]
                h[-2] = self._mk(prev.tenant_id, prev.kind, prev.key, prev.revision, dict(r.payload), r.payload_hash)
        return res


def env_for(cls):
    def factory():
        c = FakeClock(); p = StaticContextProvider(c)
        return ContractEnv(p, cls(p), InMemoryAuditLog(p, c), c.advance)
    return factory


def show(res):
    for cid, text, ok, detail in res:
        print(('PASS ' if ok else 'FAIL ') + cid + ' ' + text + ('' if ok else '  -> ' + detail))


if opt('--factory'):
    mod, attr = opt('--factory').split(':')
    res = run_history_suite(getattr(importlib.import_module(mod), attr))
    show(res)
    bad = [r for r in res if not r[2]]
    print(f'\nhistory cases {len(res)}  failed {len(bad)}')
    print('ALL HISTORY CASES PASS' if not bad else 'HISTORY CONTRACT NOT MET')
    sys.exit(1 if bad else 0)
print('== the reference store (InMemoryRecordStore)')
res = run_history_suite(env_for(InMemoryRecordStore))
show(res)
ref_ok = all(r[2] for r in res)
missed = []
for cls, must in ((OutOfRangeReadsLatest, 'RH-03'), (LeaksStoredObjects, 'RH-06'), (AppendsIdentical, 'RH-04'), (RewritesHistory, 'RH-02')):
    failed = [r[0] for r in run_history_suite(env_for(cls)) if not r[2]]
    caught = must in failed
    print('%s faulty store %s (%s): fails %s' % ('CAUGHT' if caught else 'MISSED', cls.__name__, cls.__doc__.strip(), failed))
    if not caught:
        missed.append(cls.__name__)
print('\nhistory cases %d  reference failed %d  faulty stores 4  missed %d' % (len(res), len([r for r in res if not r[2]]), len(missed)))
ok = ref_ok and not missed
print('ALL HISTORY CASES PASS AND EVERY FAULTY STORE IS CAUGHT' if ok else 'HISTORY CONTRACT NOT MET')
sys.exit(0 if ok else 1)
