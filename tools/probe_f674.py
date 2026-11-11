#!/usr/bin/env python3
"""Reproduces finding F-75 (the independent audit of APG-F67.3), and shows whether it is corrected.  It runs unchanged on the delivered APG-F67.3 package and on APG-F67.4.
F-75: "unchanged" content was compared with Python equality, under which False == 0 and True == 1, so a direct write that changed an approved value's type (0 -> False,
1 -> True, True -> 1) kept the approval.  For each of the five policy records, on approved content that holds a 0, a 1 or a boolean (for the specification register, whose
demonstration content holds none, a version with a conversion factor of 1, which its schema permits):
  A  the value's type is changed by a direct write (a new revision)          DEFECT if the approval is still confirmed, or a run still counts it
  B  the owner approves the changed content afresh                          DEFECT if that is refused or not confirmed
  C  the same version is stored again with the type-changed content         DEFECT if the re-store comparison accepts it as "the same content" (it must be refused: a
     change is a new version).  With today's schemas the schema check refuses such content first, so the comparison is exercised with the schema check stubbed out
A control shows an ordinary approval is confirmed.  Usage: python3 -I tools/probe_f674.py   Exit 0 only if every case is corrected and the control passes."""
import copy, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import probe_f671 as P1                                                           # noqa: E402  (the F-67.1 probe's world, approve and run helpers, reused unchanged)
from apg.fin import policy as FP                                                  # noqa: E402
from apg.det import policy as DP                                                  # noqa: E402
from apg.mkt import demo_mkt as DM, policy as MP                                  # noqa: E402
from apg.rec import policy as RP                                                  # noqa: E402
from apg import policy_approval as PA                                             # noqa: E402

KIND = {'fin': FP.POLICY_KIND, 'det': DP.POLICY_KIND, 'mkt': MP.POLICY_KIND, 'spec': MP.SPEC_KIND, 'rec': RP.POLICY_KIND}
STORE = {'fin': FP.store_policy, 'det': DP.store_policy, 'mkt': MP.store_policy, 'spec': MP.store_spec, 'rec': RP.store_policy}
STATUS = {'fin': FP.approval_status, 'det': DP.approval_status, 'mkt': MP.approval_status, 'spec': MP.spec_approval_status, 'rec': RP.approval_status}
results = []


def swappable(x, pre=()):
    """-> the path of the first 0, 1 or boolean in x (depth first, in key order), or None."""
    if isinstance(x, bool) or (isinstance(x, int) and x in (0, 1)):
        return pre
    items = sorted(x.items()) if isinstance(x, dict) else enumerate(x) if isinstance(x, list) else ()
    for k, v in items:
        p = swappable(v, pre + (k,))
        if p is not None:
            return p
    return None


def swapped(p, path):
    q = copy.deepcopy(p)
    c = q
    for k in path[:-1]:
        c = c[k]
    v = c[path[-1]]
    c[path[-1]] = int(v) if isinstance(v, bool) else bool(v)
    return q, v, c[path[-1]]


def world(name):
    clock, s, owner, other, vers = P1.world()
    if name == 'spec':                                                            # a version whose approved content holds a 1 that the schema permits
        p = dict(DM.demo_mkt_spec(version='PS-2'), proposer=s.ctx.user_id, approvals=[])
        p['unit_conversions'] = list(p.get('unit_conversions', [])) + [{'material': 'MAT-CU', 'from_unit': 'm', 'to_unit': 'length', 'factor_micro': 1}]
        MP.store_spec(s, p)
        vers['spec'] = 'PS-2'
    P1.APPROVE[name](owner, clock, vers[name])
    return clock, s, owner, other, vers


def report(case, ok, seen):
    results.append(ok)
    print('%-15s %-74s %s' % ('CORRECTED' if ok else 'DEFECT PRESENT', case, seen), flush=True)


def main():
    for name in ('fin', 'det', 'mkt', 'spec', 'rec'):
        clock, s, owner, other, vers = world(name)
        v, k = vers[name], KIND[name]
        cur = s.get(k, v)
        path = swappable({x: y for x, y in cur.payload.items() if x != 'approvals'})
        new, old_v, new_v = swapped(cur.payload, path)
        r = s.put(k, v, new, expected_revision=cur.revision)
        conf = STATUS[name](s, v)['confirmed']
        run = P1.attempt(lambda: P1.counted(s, clock, vers, name))
        got = P1.counted(s, clock, vers, name) if run == 'done' else 'run refused'
        report('F-75 %s A: %s changed from %r to %r (revision %d)' % (name, '/'.join(map(str, path)), old_v, new_v, r.revision), conf == [] and got is not True,
               '-> confirmed %s; run approved=%s' % (conf, got))
        b = P1.attempt(lambda: P1.APPROVE[name](owner, clock, v))
        conf = STATUS[name](s, v)['confirmed']
        report('F-75 %s B: the owner approves the changed content afresh' % name, b == 'done' and conf == ['olive'], '-> %s; confirmed %s' % (b, conf))
        clock, s, owner, other, vers = world(name)
        v, k = vers[name], KIND[name]
        cur = s.get(k, v)
        path = swappable({x: y for x, y in cur.payload.items() if x != 'approvals'})
        new, old_v, new_v = swapped(dict(cur.payload, approvals=[]), path)
        if name == 'rec':                                                       # the recommendation policy has its own store; stub its schema check
            real, RP.validate_policy = RP.validate_policy, (lambda p: [])
            try:
                c = P1.attempt(lambda: RP.store_policy(s, new))
            finally:
                RP.validate_policy = real
        else:
            c = P1.attempt(lambda: PA.store(s, k, new, lambda p: [], RuntimeError, name))
        after = s.get(k, v)
        report('F-75 %s C: the version stored again with %r for %r' % (name, new_v, old_v), c.startswith('refused') and after.revision == cur.revision,
               '-> %s; revision %d -> %d' % (c[:90], cur.revision, after.revision))
    clock, s, owner, other, vers = P1.world()
    got = {}
    for name in P1.APPROVE:
        P1.APPROVE[name](owner, clock, vers[name])
        got[name] = STATUS[name](s, vers[name])['confirmed'] == ['olive']
    report('control: an ordinary approval of each record is confirmed', all(got.values()), '-> %s' % got)
    bad = results.count(False)
    print('\ncases %d  defects present %d' % (len(results), bad))
    print('F-75 IS CORRECTED' if not bad else 'F-75 IS NOT CORRECTED')
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
