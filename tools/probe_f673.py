#!/usr/bin/env python3
"""Reproduces finding F-74 (the independent audit of APG-F67.2) and the rest of its defect class, and shows whether they are corrected.  It runs unchanged on the delivered
APG-F67.2 package and on APG-F67.3.  Threat model (the product owner's authorisation of F-67.3): whoever can append arbitrary revisions to the store, but cannot write an audit
event as another person, rewrite a past revision or audit event, or change what a pinned revision reads on replay.  For each of the five policy records, after the owner's
genuine approval (confirmed, counted):
  A  the entry is removed, then re-planted identical, by direct writes             DEFECT if a new run counts it
  B  the entry is changed in place (its date) by a direct write                    DEFECT if a new run counts it
  C  the approved content is rewritten, the entry kept, by a direct write          DEFECT if a new run counts it
  D  the content is rewritten and then restored                                    DEFECT if a new run counts it (the approved content did not stay unchanged)
  E  the same content and entry are written as a NEW version                       DEFECT if a run of that version counts the old confirmation
  F  a run made before C, replayed after it                                        DEFECT if the replay fails or no longer shows the approval it pinned
  G  another person approves after the owner                                       DEFECT if the owner's approval stops counting (adding approvals must keep it)
  H  after C, the owner approves again                                             DEFECT if that is refused, or the new approval does not count
A control shows an ordinary approval counts.  Usage: python3 -I tools/probe_f673.py   Exit 0 only if every case is corrected and the control passes."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import probe_f671 as P1                                                           # noqa: E402  (the F-67.1 probe's world, approve and run helpers, reused unchanged)
from apg import repro                                                             # noqa: E402
from apg.fin import calc_records as C, policy as FP                               # noqa: E402
from apg.det import detect as DT, policy as DP                                    # noqa: E402
from apg.mkt import detect as MD, policy as MP                                    # noqa: E402
from apg.rec import engine as E, policy as RP                                     # noqa: E402

AS_OF = P1.AS_OF
KIND = {'fin': FP.POLICY_KIND, 'det': DP.POLICY_KIND, 'mkt': MP.POLICY_KIND, 'spec': MP.SPEC_KIND, 'rec': RP.POLICY_KIND}
results = []


def run(s, clock, vers, name):
    """-> (the stored run record payload, its registry, whether it counts the record's approval)."""
    if name == 'fin':
        reg = C.fin_registry(); r = C.run_calc(s, reg, clock, 'fin.actual_cost', 'PRJ-001', AS_OF, vers['fin']); a = r['result']['policy']['approved']
    elif name == 'det':
        reg = DT.det_registry(); r = DT.run_project(s, reg, clock, 'PRJ-001', AS_OF, vers['fin'], vers['det']); a = r['result']['det_policy']['approved']
    elif name in ('mkt', 'spec'):
        reg = MD.mkt_registry(); r = MD.run_project(s, reg, clock, 'PRJ-001', AS_OF, vers['fin'], vers['det'], vers['mkt'], vers['spec'])
        a = r['result']['mkt_policy' if name == 'mkt' else 'mkt_spec']['approved']
    else:
        reg = E.registry(); r = E.run(s, reg, clock, AS_OF, vers['rec']); a = r['result']['policy']['approved']
    return r, reg, a


def put(s, name, v, **change):
    cur = s.get(KIND[name], v)
    return s.put(KIND[name], v, dict(cur.payload, **change), expected_revision=cur.revision)


def approved_world(name):
    clock, s, owner, other, vers = P1.world()
    P1.APPROVE[name](owner, clock, vers[name])
    return clock, s, owner, other, vers


def report(case, ok, seen):
    results.append(ok)
    print('%-15s %-74s %s' % ('CORRECTED' if ok else 'DEFECT PRESENT', case, seen), flush=True)


def main():
    for name in ('fin', 'det', 'mkt', 'spec', 'rec'):
        v = None
        clock, s, owner, other, vers = approved_world(name); v = vers[name]
        entry = [a for a in s.get(KIND[name], v).payload['approvals'] if a['approver'] == 'olive'][0]
        put(s, name, v, approvals=[]); put(s, name, v, approvals=[entry])
        got = run(s, clock, vers, name)[2]
        report('F-74 %s A: entry removed, then re-planted identical' % name, not got, '-> new run approved=%s' % got)

        clock, s, owner, other, vers = approved_world(name); v = vers[name]
        cur = s.get(KIND[name], v).payload
        put(s, name, v, approvals=[dict(a, date='2001-01-01') if a['approver'] == 'olive' else a for a in cur['approvals']])
        got = run(s, clock, vers, name)[2]
        report('F-74 %s B: the entry changed in place' % name, not got, '-> new run approved=%s' % got)

        clock, s, owner, other, vers = approved_world(name); v = vers[name]
        before, reg, was = run(s, clock, vers, name)
        put(s, name, v, note='rewritten after the approval')
        got = run(s, clock, vers, name)[2]
        report('F-74 %s C: the approved content rewritten, the entry kept' % name, not got, '-> new run approved=%s' % got)
        rp = repro.replay(s, reg, before['run_key'])
        still = s.get(repro.KIND, before['run_key']).payload['result']
        shown = run_result_approved(name, still)
        report('F-74 %s F: a run made before C, replayed after it' % name, was and rp.ok and shown, '-> replay ok=%s; the stored run still shows approved=%s' % (rp.ok, shown))
        h = P1.attempt(lambda: P1.APPROVE[name](owner, clock, v))
        got = run(s, clock, vers, name)[2]
        report('F-74 %s H: after C, the owner approves again' % name, h == 'done' and got, '-> %s; new run approved=%s' % (h, got))

        clock, s, owner, other, vers = approved_world(name); v = vers[name]
        orig = s.get(KIND[name], v).payload
        put(s, name, v, note='rewritten'); s.put(KIND[name], v, orig, expected_revision=s.get(KIND[name], v).revision)
        got = run(s, clock, vers, name)[2]
        report('F-74 %s D: the content rewritten, then restored' % name, not got, '-> new run approved=%s' % got)

        clock, s, owner, other, vers = approved_world(name); v = vers[name]
        p = dict(s.get(KIND[name], v).payload, version=v + '-COPY')
        s.put(KIND[name], v + '-COPY', p, expected_revision=0)
        got = run(s, clock, dict(vers, **{name: v + '-COPY'}), name)[2]
        report('F-74 %s E: the same content and entry written as a new version' % name, not got, '-> run of the copy approved=%s' % got)

        clock, s, owner, other, vers = approved_world(name); v = vers[name]
        P1.APPROVE[name](other, clock, v)
        conf = (RP.approval_status(s, v) if name == 'rec' else (MP.spec_approval_status(s, v) if name == 'spec' else
                {'fin': FP, 'det': DP, 'mkt': MP}[name].approval_status(s, v)))['confirmed']
        got = run(s, clock, vers, name)[2]
        report('F-74 %s G: another person approves after the owner' % name, got and conf == ['olive', 'otto'], '-> run approved=%s; confirmed %s' % (got, conf))
    clock, s, owner, other, vers = P1.world()
    got = {}
    for name in P1.APPROVE:
        P1.APPROVE[name](owner, clock, vers[name])
        got[name] = run(s, clock, vers, name)[2]
    report('control: an ordinary approval of each record is counted', all(got.values()), '-> %s' % got)
    bad = results.count(False)
    print('\ncases %d  defects present %d' % (len(results), bad))
    print('F-74 IS CORRECTED' if not bad else 'F-74 IS NOT CORRECTED')
    return 0 if not bad else 1


def run_result_approved(name, r):
    return {'fin': lambda: r['policy']['approved'], 'det': lambda: r['det_policy']['approved'], 'mkt': lambda: r['mkt_policy']['approved'],
            'spec': lambda: r['mkt_spec']['approved'], 'rec': lambda: r['policy']['approved']}[name]()


if __name__ == '__main__':
    sys.exit(main())
