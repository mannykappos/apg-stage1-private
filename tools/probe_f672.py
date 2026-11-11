#!/usr/bin/env python3
"""Reproduces finding F-73 (the independent audit of APG-F67.1), and shows whether it is corrected.  It runs unchanged on the delivered APG-F67.1 package (where F-73 is open)
and on APG-F67.2.  F-73: the F-67.1 recovery path completed an unconfirmed approval entry in the caller's name after checking only its role and kind, so an entry written into the
store directly, with the correct role and kind, was completed by the named person's approve call, which then confirmed the planted entry.  For each of the five policy records:
  A  an entry naming the owner, with the correct role and kind, is written straight into the store       DEFECT if a run counts it
  B  the owner then approves in person                                     DEFECT if the planted entry is still in the record, or the confirming event does not name the
                                                                           revision that added the owner's fresh entry
  C  as B, but the planted entry is byte-identical to the one approve would write (same date)   DEFECT if the confirming event names the planted revision or none
A control shows an ordinary approval is counted and its event names the revision approve wrote.
Usage: python3 -I tools/probe_f672.py   Exit 0 only if every case is corrected and the control passes."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import probe_f671 as P1                                                           # noqa: E402  (the F-67.1 probe's world, approve and run helpers, reused unchanged)
from apg.fin import policy as FP                                                  # noqa: E402
from apg.det import policy as DP                                                  # noqa: E402
from apg.mkt import policy as MP                                                  # noqa: E402
from apg.rec import policy as RP                                                  # noqa: E402

KIND = {'fin': FP.POLICY_KIND, 'det': DP.POLICY_KIND, 'mkt': MP.POLICY_KIND, 'spec': MP.SPEC_KIND, 'rec': RP.POLICY_KIND}
ROLE = {'fin': FP.POLICY_ROLE, 'det': DP.POLICY_ROLE, 'mkt': MP.POLICY_ROLE, 'spec': MP.SPEC_ROLE, 'rec': RP.POLICY_ROLE}
EVENT = dict(zip(('fin', 'det', 'mkt', 'spec', 'rec'), P1.EVENTS))
results = []


def report(case, ok, seen):
    results.append(ok)
    print('%-15s %-74s %s' % ('CORRECTED' if ok else 'DEFECT PRESENT', case, seen), flush=True)


def plant(s, name, v, date):
    cur = s.get(KIND[name], v)
    entry = {'approver': 'olive', 'role': ROLE[name], 'kind': 'human', 'date': date}
    return s.put(KIND[name], v, dict(cur.payload, approvals=cur.payload['approvals'] + [entry]), expected_revision=cur.revision), entry


def olive_events(s, name):
    return [e for e in s._audit.read(s.ctx) if e.event_type == EVENT[name] and e.actor == 'olive' and e.outcome == 'ok']


def main():
    for name in ('fin', 'det', 'mkt', 'spec', 'rec'):
        clock, s, owner, other, vers = P1.world()
        v = vers[name]
        planted, entry = plant(s, name, v, '2000-01-01')
        got = P1.counted(s, clock, vers, name)
        report('F-73 %s A: a planted entry naming the owner, correct role and kind' % name, not got, '-> run approved=%s' % got)
        a = P1.attempt(lambda: P1.APPROVE[name](owner, clock, v))
        now = s.get(KIND[name], v)
        ev = olive_events(s, name)
        bound = ev[-1].detail.get('revision') if ev else None
        still = entry in now.payload['approvals']
        ok = a == 'done' and not still and isinstance(bound, int) and bound > planted.revision and \
            any(x['approver'] == 'olive' for x in s.get(KIND[name], v, bound).payload['approvals'])
        report('F-73 %s B: the owner then approves in person' % name, ok,
               '-> %s; planted entry still in the record=%s; event names revision %s (planted %d, latest %d)' % (a, still, bound, planted.revision, now.revision))
        clock, s, owner, other, vers = P1.world()
        v = vers[name]
        planted, entry = plant(s, name, v, clock.now()[:10])
        a = P1.attempt(lambda: P1.APPROVE[name](owner, clock, v))
        ev = olive_events(s, name)
        bound = ev[-1].detail.get('revision') if ev else None
        ok = a == 'done' and isinstance(bound, int) and bound > planted.revision
        report('F-73 %s C: as B, the planted entry identical to approve\'s own' % name, ok, '-> %s; event names revision %s (planted %d)' % (a, bound, planted.revision))
    clock, s, owner, other, vers = P1.world()
    got, bound_ok = {}, {}
    for name in P1.APPROVE:
        rec = P1.APPROVE[name](owner, clock, vers[name])
        latest = s.get(KIND[name], vers[name])
        bound_ok[name] = olive_events(s, name)[-1].detail.get('revision') == latest.revision
        got[name] = P1.counted(s, clock, vers, name)
    report('control: an ordinary approval is counted and names the revision approve wrote', all(got.values()) and all(bound_ok.values()),
           '-> counted %s; bound %s' % (got, bound_ok))
    bad = results.count(False)
    print('\ncases %d  defects present %d' % (len(results), bad))
    print('F-73 IS CORRECTED' if not bad else 'F-73 IS NOT CORRECTED')
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
