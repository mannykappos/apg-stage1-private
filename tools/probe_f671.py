#!/usr/bin/env python3
"""Reproduces finding F-72 (the independent audit of APG-F67), and shows whether it is corrected.  It runs unchanged on the delivered APG-F67 package (where F-72 is open) and on
APG-F67.1.  F-72: an approval writes the approved policy revision and then the confirming audit event.  If the audit write fails in between, the policy lists the approval, the
log confirms nobody (so the approval rightly does not count), and the owner's retry is refused as "already approved": the policy is stuck unapproved with no supported way on.
The same order holds for the recommendation policy (APG-M7.1, F-66).  For each of the five policy records the probe:
  A  approves as the owner while the audit write fails     DEFECT if the run then counts the approval (it must fail closed), or if the error does not say the
                                                           approval is recorded in the policy but NOT CONFIRMED by the audit log
  B  retries as the same owner once the log works again    DEFECT if the retry is refused, or the run does not then count the approval
  C  has another person with the role approve while the owner's approval is unconfirmed   DEFECT if that confirms the owner's approval
  D  retries as the same owner while the log is still failing   DEFECT if the run then counts the approval
A control shows an ordinary approval is counted.  Usage: python3 -I tools/probe_f671.py   Exit 0 only if every case is corrected and the control passes."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT)
from apg.ingest.golden_m3 import _world                                          # noqa: E402
from apg.fin import calc_records as C, demo_fin as DF, policy as FP               # noqa: E402
from apg.det import demo_det as DD, detect as DT, policy as DP                    # noqa: E402
from apg.mkt import demo_mkt as DM, detect as MD, policy as MP                    # noqa: E402
from apg.rec import demo_rec as DR, engine as E, policy as RP                     # noqa: E402

AS_OF = '2026-09-30'
ROLES = (FP.POLICY_ROLE, DP.POLICY_ROLE, MP.POLICY_ROLE, MP.SPEC_ROLE, RP.POLICY_ROLE)
EVENTS = ('fin_policy.approved', 'det_policy.approved', 'mkt_policy.approved', 'mkt_spec.approved', 'rec.policy_approved')
results = []


def world():
    clock, prov, store, audit, who = _world()
    s = who('t1', 'zero_one', 'ann')
    DF.load_zero(ROOT, s, clock, 'zero_one')
    DD.load_det(ROOT, s, clock, 'zero_one')
    DM.load_mkt(ROOT, s, clock, 'zero_one')
    owner = who('own', 'zero_one', 'olive', ROLES)
    other = who('oth', 'zero_one', 'otto', ROLES)
    vers = {}
    for name, fn, store_fn, ver in (('fin', DF.demo_policy, FP.store_policy, 'PF-1'), ('det', DD.demo_det_policy, DP.store_policy, 'PD-1'),
                                    ('mkt', DM.demo_mkt_policy, MP.store_policy, 'PM-1'), ('spec', DM.demo_mkt_spec, MP.store_spec, 'PS-1')):
        store_fn(s, dict(fn(version=ver), proposer='ann', approvals=[]))
        vers[name] = ver
    RP.store_policy(s, DR.demo_rec_policy(version='PR-1', proposer='ann'))
    vers['rec'] = 'PR-1'
    return clock, s, owner, other, vers


APPROVE = {'fin': lambda sc, c, v: FP.approve_policy(sc, c, v, 'probe'), 'det': lambda sc, c, v: DP.approve_policy(sc, c, v, 'probe'),
           'mkt': lambda sc, c, v: MP.approve_policy(sc, c, v, 'probe'), 'spec': lambda sc, c, v: MP.approve_spec(sc, c, v, 'probe'),
           'rec': lambda sc, c, v: RP.approve_policy(sc, c, v, 'probe')}


def counted(s, clock, vers, name):
    if name == 'fin':
        return C.run_calc(s, C.fin_registry(), clock, 'fin.actual_cost', 'PRJ-001', AS_OF, vers['fin'])['result']['policy']['approved']
    if name == 'det':
        return DT.run_project(s, DT.det_registry(), clock, 'PRJ-001', AS_OF, vers['fin'], vers['det'])['result']['det_policy']['approved']
    if name in ('mkt', 'spec'):
        r = MD.run_project(s, MD.mkt_registry(), clock, 'PRJ-001', AS_OF, vers['fin'], vers['det'], vers['mkt'], vers['spec'])['result']
        return r['mkt_policy' if name == 'mkt' else 'mkt_spec']['approved']
    return E.run(s, E.registry(), clock, AS_OF, vers['rec'])['result']['policy']['approved']


def failing(scoped):
    """Make the audit write of the approval event fail for this session (the store write before it succeeds)."""
    real = scoped.log

    def log(event_type, *a, **k):
        if event_type in EVENTS:
            raise RuntimeError('audit sink unavailable')
        return real(event_type, *a, **k)
    scoped.log = log
    return lambda: setattr(scoped, 'log', real)


def attempt(fn):
    try:
        fn()
        return 'done'
    except Exception as e:
        return 'refused (%s: %s)' % (type(e).__name__, str(e)[:110])


def report(case, ok, seen):
    results.append(ok)
    print('%-15s %-74s %s' % ('CORRECTED' if ok else 'DEFECT PRESENT', case, seen), flush=True)


def main():
    for name in ('fin', 'det', 'mkt', 'spec', 'rec'):
        clock, s, owner, other, vers = world()
        v = vers[name]
        restore = failing(owner)
        a = attempt(lambda: APPROVE[name](owner, clock, v))
        restore()
        got = counted(s, clock, vers, name)
        report('F-72 %s A: approval while the audit write fails' % name, not got and 'NOT CONFIRMED' in a, '-> %s; run approved=%s' % (a, got))
        restore = failing(owner)
        d = attempt(lambda: APPROVE[name](owner, clock, v))
        restore()
        got = counted(s, clock, vers, name)
        report('F-72 %s D: the owner retries while the audit write still fails' % name, not got, '-> %s; run approved=%s' % (d, got))
        c = attempt(lambda: APPROVE[name](other, clock, v))
        listed = [x['approver'] for x in s.get(RP.POLICY_KIND if name == 'rec' else {'fin': FP.POLICY_KIND, 'det': DP.POLICY_KIND, 'mkt': MP.POLICY_KIND, 'spec': MP.SPEC_KIND}[name], v).payload['approvals']]
        own_confirmed = any(e.event_type in EVENTS and e.actor == 'olive' and e.outcome == 'ok' for e in s._audit.read(s.ctx))
        report('F-72 %s C: another person with the role approves meanwhile' % name, not own_confirmed, '-> %s; listed %s; olive confirmed=%s' % (c, listed, own_confirmed))
        b = attempt(lambda: APPROVE[name](owner, clock, v))
        got = counted(s, clock, vers, name)
        own_confirmed = any(e.event_type in EVENTS and e.actor == 'olive' and e.outcome == 'ok' for e in s._audit.read(s.ctx))
        report('F-72 %s B: the owner retries once the audit log works' % name, b == 'done' and got and own_confirmed, '-> %s; run approved=%s; olive confirmed=%s' % (b, got, own_confirmed))
    clock, s, owner, other, vers = world()
    for name in APPROVE:
        APPROVE[name](owner, clock, vers[name])
    got = {n: counted(s, clock, vers, n) for n in APPROVE}
    report('control: an ordinary approval of each record is counted', all(got.values()), '-> %s' % got)
    bad = results.count(False)
    print('\ncases %d  defects present %d' % (len(results), bad))
    print('F-72 IS CORRECTED' if not bad else 'F-72 IS NOT CORRECTED')
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
