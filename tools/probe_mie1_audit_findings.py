#!/usr/bin/env python3
"""Reproduces the two findings of the independent audit of APG MIE-1, and shows whether they are corrected.  Runs unchanged on the delivered MIE-1 package and on MIE-1.1.
  F-70 (auditor F-MIE1-01) an unexpected exception from a store at the commit escaped the core as a raw exception, after an ACCEPTED event, with no FAILED event;
       the same class: an unexpected exception from the audit sink, and a store failure part-way through a batch of observations (part of the batch stored).
  F-71 (auditor F-MIE1-02) an observation could name, as the one it supersedes, an observation of another subject or series, and that evidence silently became history.
Usage: python3 -I tools/probe_mie1_audit_findings.py   Exit 0 only if every case is corrected."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT)
from tests.helpers_mie import EVAL, World, code, ob, series, UP      # noqa: E402
from mie.core import canon, reference as R                           # noqa: E402
from mie.core.vocab import MieError                                  # noqa: E402
from mie.packs import synthetic as SP                                # noqa: E402

results = []


def report(case, ok, seen):
    results.append(ok)
    print('%-15s %-70s %s' % ('CORRECTED' if ok else 'DEFECT PRESENT', case, seen), flush=True)


def outcome(fn):
    try:
        fn()
        return 'returned'
    except MieError as e:
        return e.code
    except Exception as e:
        return 'raw %s escaped' % type(e).__name__


def tail(w, n=2, tenant='T-A'):
    return [(e['operation'], e['outcome'], e['code']) for e in w.events(tenant)[-n:]]


def boom(*a, **k):
    raise RuntimeError('unexpected store error')


def f70_commit():
    cases = {
        'register_pack: registry.put raises RuntimeError': (lambda w: setattr(w.reg, 'put', boom), lambda w: w.e.register_pack('tA', SP.pack_bytes('9.9.9')),
                                                             lambda w: w.reg.get('SYN-TEST-FIELD', '9.9.9') is None),
        'activate_pack: registry.activate raises RuntimeError': (lambda w: setattr(w.reg, 'activate', boom), lambda w: w.activate('tB', w.pin),
                                                                lambda w: w.reg.activations('T-B', w.pin) == []),
        'withdraw_pack: registry.withdraw raises RuntimeError': (lambda w: setattr(w.reg, 'withdraw', boom), lambda w: w.e.withdraw_pack('tA', w.pin, 'r'),
                                                                lambda w: w.reg.withdrawal(w.pin) is None),
        'submit_observations: the observation store raises RuntimeError': (lambda w: (setattr(w.obs, 'append', boom), setattr(w.obs, 'append_batch', boom)),
                                                                          lambda w: w.submit(series(UP)), lambda w: w.obs.d == {}),
        'assess_timing: results.put raises RuntimeError': (lambda w: setattr(w.res, 'put', boom), lambda w: w.assess(), lambda w: w.res.d == {}),
    }
    for name, (sabotage, call, nothing_stored) in cases.items():
        w = World()
        if 'assess' in name:
            w.submit(series(UP))
        sabotage(w)
        got = outcome(lambda: call(w))
        ev = tail(w, tenant='T-B' if 'activate' in name else 'T-A')         # the activation is made by tenant T-B
        ok = got == 'INTERNAL_ERROR_FAIL_CLOSED' and ev[-1][1:] == ('FAILED', 'INTERNAL_ERROR_FAIL_CLOSED') and nothing_stored(w)
        report('F-70 ' + name, ok, '-> %s; last events %s; nothing stored: %s' % (got, ev, nothing_stored(w)))


def f70_audit():
    w = World()
    n = len(w.obs.d)

    def bad_append(tenant, event):
        raise RuntimeError('unexpected audit error')
    w.aud.append = bad_append
    got = outcome(lambda: w.submit(series(UP)))
    ok = got == 'AUDIT_UNAVAILABLE' and len(w.obs.d) == n
    report('F-70 the audit sink raises RuntimeError at submit_observations', ok, '-> %s; observations stored: %d' % (got, len(w.obs.d) - n))


def f70_batch():
    class FailsOnSecondItem(R.RefObservations):
        def __init__(self):
            super().__init__()
            self.calls = 0
            self.fail_at_item = 1                       # used by MIE-1.1's batch write; MIE-1 writes item by item

        def append(self, tenant, oid, obs):
            self.calls += 1
            if self.calls == 2:
                raise R.StoreFailure()
            return super().append(tenant, oid, obs)
    w = World()
    w.obs = FailsOnSecondItem()
    w.e.obs = w.obs
    got = outcome(lambda: w.submit(series(UP)))
    ok = got == 'STORE_UNAVAILABLE' and w.obs.d == {}
    report('F-70 the store fails while writing the 2nd of 3 observations', ok, '-> %s; observations left stored: %d' % (got, len(w.obs.d)))


def f71():
    base = ob('2026-09-01', 10000)
    variants = {
        'another subject (SYN-ITEM-B)': dict(subject_id='SYN-ITEM-B'),
        'another subject that is in scope (the conversion series SYN-RATE-1)': dict(subject_id='SYN-RATE-1', unit='SYN-RATE-UNIT', observation_class='CURRENT_REFERENCE'),
        'another unit': dict(unit='SYN-UNIT-2'),
        'another market': dict(market='SYN-MARKET-2'),
        'another value basis': dict(value_basis='ASKING'),
        'another observation class and value basis': dict(observation_class='CURRENT_REFERENCE', value_basis='ASKING'),
        'another observation class only': dict(observation_class='CURRENT_REFERENCE'),
        'another source and value basis': dict(source_id='SYN-SRC-2', value_basis='ASKING'),
        'another source only': dict(source_id='SYN-SRC-W', licence_ref='SYN-LIC-4'),
        'another date': dict(as_of='2026-09-02', retrieved_at='2026-09-02'),
    }
    for name, change in variants.items():
        w = World()
        w.submit([ob('2026-07-15', 9000), base] + ([dict(base, value_basis='ASKING', value={'mantissa': 1, 'exponent': 0})] if 'basis' in name or 'source' in name else []))
        first = [r for r in w.submit([base])['receipts']][0]['observation_id']
        before = canon.dumps(w.signals()['evidence'])
        item = dict(ob('2026-09-01', 12000), supersedes=first, **change)
        r = w.submit([item])['receipts'][0]
        after_a = [i for i in w.signals()['evidence']['historical_movement'] if i['observation_id'] == first]
        ok = r['status'] == 'REJECTED' and r['fields'] == ['supersedes'] and after_a and after_a[0]['state'] != 'history'
        report('F-71 a correction naming an observation of %s' % name, ok, '-> %s; the original is now %s' % (r['status'], after_a[0]['state'] if after_a else '?'))
    w = World()
    first = w.submit([base])['receipts'][0]['observation_id']
    r = w.submit([dict(ob('2026-09-01', 12000), supersedes=first)])['receipts'][0]
    st = {i['observation_id']: i['state'] for i in w.signals()['evidence']['historical_movement']}
    report('F-71 control: a true correction (same series, source and date)', r['status'] == 'ACCEPTED' and st[first] == 'history',
           '-> %s; the original is now %s' % (r['status'], st[first]))


if __name__ == '__main__':
    f70_commit()
    f70_audit()
    f70_batch()
    f71()
    bad = results.count(False)
    print('\ncases %d  defects present %d' % (len(results), bad))
    print('THE MIE-1 AUDIT FINDINGS ARE CORRECTED' if not bad else 'THE MIE-1 AUDIT FINDINGS ARE NOT CORRECTED')
    sys.exit(0 if not bad else 1)
