#!/usr/bin/env python3
"""Reproduces finding F-67, and shows whether it is corrected.  It runs unchanged on the delivered MIE-1.1-R1 package (where F-67 is open) and on APG-F67.
F-67: the financial, detection and procurement policies and the specification register accepted an approval that the caller asserted (approver, role and kind as plain fields),
and a calculation or detection run counted it.  For each of the four records, on the Builder Zero data, the probe tries four ways to get a policy counted as approved without the
owner's own approval:
  A  store a new version that already carries a caller-written approval
  B  store the proposal, then store the same version again with a caller-written approval appended
  C  write the record straight into the store with a caller-written approval (bypassing the policy functions)
  D  name somebody else as the proposer, so that the person storing it can then appear as an independent approver
and then runs the calculation or detection that reads it.  DEFECT PRESENT = the run reports the record as approved.  A control shows that the owner's own approval through the
corrected path is counted.
Usage: python3 -I tools/probe_f67.py   Exit 0 only if every case is corrected and the control passes."""
import inspect, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT)
from apg.ingest.golden_m3 import _world                                          # noqa: E402
from apg.fin import calc_records as C, demo_fin as DF, policy as FP               # noqa: E402
from apg.det import demo_det as DD, detect as DT, policy as DP                    # noqa: E402
from apg.mkt import demo_mkt as DM, detect as MD, policy as MP                    # noqa: E402

AS_OF = '2026-09-30'
results = []


def unapproved(fn, version):
    if 'approved' in inspect.signature(fn).parameters:
        p = fn(version=version, approved=False)                                     # the delivered package
    else:
        p = fn(version=version)                                                     # APG-F67: the demonstration builders return proposals only
    return dict(p, approvals=[])


def world():
    clock, prov, store, audit, who = _world()
    s = who('t1', 'zero_one', 'ann')
    DF.load_zero(ROOT, s, clock, 'zero_one')
    DD.load_det(ROOT, s, clock, 'zero_one')
    DM.load_mkt(ROOT, s, clock, 'zero_one')
    owner = who('own', 'zero_one', 'olive', (FP.POLICY_ROLE, DP.POLICY_ROLE, MP.POLICY_ROLE, MP.SPEC_ROLE))
    return clock, s, owner


def base(s, clock, owner, approve_with_owner):
    """Proposed versions of all four records stored by their proposer (ann), approved by the owner only when asked, through the corrected path if it exists."""
    vers = {}
    for name, fn, mod, store, appr, role, ver in (('fin', DF.demo_policy, FP, FP.store_policy, 'approve_policy', FP.POLICY_ROLE, 'PF-1'),
                                                  ('det', DD.demo_det_policy, DP, DP.store_policy, 'approve_policy', DP.POLICY_ROLE, 'PD-1'),
                                                  ('mkt', DM.demo_mkt_policy, MP, MP.store_policy, 'approve_policy', MP.POLICY_ROLE, 'PM-1'),
                                                  ('spec', DM.demo_mkt_spec, MP, MP.store_spec, 'approve_spec', MP.SPEC_ROLE, 'PS-1')):
        p = dict(unapproved(fn, ver), proposer=s.ctx.user_id)
        store(s, p)
        if approve_with_owner and hasattr(mod, appr):
            getattr(mod, appr)(owner, clock, ver, 'probe control: approved by the owner in person')
        vers[name] = ver
    return vers


def approved_in_run(s, clock, vers):
    fig = C.run_calc(s, C.fin_registry(), clock, 'fin.actual_cost', 'PRJ-001', AS_OF, vers['fin'])['result']
    det = DT.run_project(s, DT.det_registry(), clock, 'PRJ-001', AS_OF, vers['fin'], vers['det'])['result']
    mkt = MD.run_project(s, MD.mkt_registry(), clock, 'PRJ-001', AS_OF, vers['fin'], vers['det'], vers['mkt'], vers['spec'])['result']
    return {'fin': fig['policy']['approved'], 'det': det['det_policy']['approved'], 'mkt': mkt['mkt_policy']['approved'], 'spec': mkt['mkt_spec']['approved']}


FORGED = {'fin': FP.POLICY_ROLE, 'det': DP.POLICY_ROLE, 'mkt': MP.POLICY_ROLE, 'spec': MP.SPEC_ROLE}
KINDS = {'fin': (FP.POLICY_KIND, FP.store_policy), 'det': (DP.POLICY_KIND, DP.store_policy), 'mkt': (MP.POLICY_KIND, MP.store_policy), 'spec': (MP.SPEC_KIND, MP.store_spec)}


def forged(role):
    return {'approver': 'mallory', 'role': role, 'kind': 'human', 'date': AS_OF}


def attempt(fn):
    try:
        fn()
        return 'stored'
    except Exception as e:
        return 'refused (%s)' % type(e).__name__


def report(case, ok, seen):
    results.append(ok)
    print('%-15s %-78s %s' % ('CORRECTED' if ok else 'DEFECT PRESENT', case, seen), flush=True)


def main():
    for name in ('fin', 'det', 'mkt', 'spec'):
        kind, store = KINDS[name]
        for case in 'ABCD':
            clock, s, owner = world()
            vers = base(s, clock, owner, approve_with_owner=False)
            new = 'X-%s' % case
            fn = {'fin': DF.demo_policy, 'det': DD.demo_det_policy, 'mkt': DM.demo_mkt_policy, 'spec': DM.demo_mkt_spec}[name]
            p = dict(unapproved(fn, new), proposer=s.ctx.user_id)
            if case == 'A':
                what = attempt(lambda: store(s, dict(p, approvals=[forged(FORGED[name])])))
            elif case == 'B':
                store(s, p)
                what = attempt(lambda: store(s, dict(p, approvals=[forged(FORGED[name])])))
            elif case == 'C':
                what = attempt(lambda: s.put(kind, new, dict(p, approvals=[forged(FORGED[name])]), expected_revision=0))
            else:
                q = dict(p, proposer='someone.else', approvals=[{'approver': s.ctx.user_id, 'role': FORGED[name], 'kind': 'human', 'date': AS_OF}])
                what = attempt(lambda: store(s, q))
            if s.get(kind, new) is None:
                store(s, p)                                                         # the run still needs the version: the plain proposal
            vers[name] = new
            got = approved_in_run(s, clock, vers)[name]
            label = {'A': 'stored with a caller-written approval', 'B': 'caller-written approval appended to the stored proposal',
                     'C': 'caller-written approval written straight into the store', 'D': 'another person named as proposer, the storer as approver'}[case]
            report('F-67 %s_policy %s: %s' % (name, case, label) if name != 'spec' else 'F-67 mkt_spec %s: %s' % (case, label), not got,
                   '-> %s; the run reports approved=%s' % (what, got))
    clock, s, owner = world()
    vers = base(s, clock, owner, approve_with_owner=True)
    got = approved_in_run(s, clock, vers)
    ctl = all(got.values()) and hasattr(FP, 'approve_policy')
    report('control: each record approved by its owner in person through approve_policy/approve_spec', ctl, '-> %s' % got)
    bad = results.count(False)
    print('\ncases %d  defects present %d' % (len(results), bad))
    print('F-67 IS CORRECTED' if not bad else 'F-67 IS NOT CORRECTED')
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
