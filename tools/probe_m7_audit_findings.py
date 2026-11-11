#!/usr/bin/env python3
"""Reproduces the findings of the independent audit of APG-M7 (F-64, F-65, F-66) the way the auditor reproduced them, and says for each whether the defect is present.
On the delivered M7 package it prints DEFECT PRESENT for each one and exits 1; on M7.1 it prints THE AUDIT FINDINGS ARE CORRECTED and exits 0.
Usage: python3 -I tools/probe_m7_audit_findings.py   (from the package root; writes nothing to disk).  To try it on M7, copy this file into the extracted M7 package's tools/ folder."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT)
from tests.helpers_rec import RecWorld                              # noqa: E402
from apg.det import findings as FD                                  # noqa: E402
from apg.rec import inputs as IN, lifecycle as L, policy as RP      # noqa: E402

present = []


def report(fid, what, defect):
    present.append(defect)
    print(('DEFECT PRESENT  ' if defect else 'corrected       ') + fid + ' ' + what)


def accepted(fn):
    """True if the call went through (the defect), False if it was refused."""
    try:
        fn()
        return True
    except (L.RecError, IN.InputError, RP.RecPolicyError):
        return False


# F-64 (a): the finding is dismissed after the run; submission without a fresh run
w = RecWorld()
f = w.finding(gross=500000)
rid = w.ready(f)
w.run()
FD.transition(w.rev, w.clock, f, 'dismissed', rationale='not a real issue after all')
report('F-64', 'submission accepted after the underlying finding was dismissed, without a fresh run', accepted(lambda: L.submit(w.owner2, w.clock, rid)))

# F-64 (b): the mandatory review is changed to not_cleared after the run; submission without a fresh run
w = RecWorld()
f = w.finding(family='quality_defects', gross=500000)
rid = w.ready(f)
w.run()
IN.record_review(w.creview, w.clock, rid, 'quality', 'not_cleared', 'the substitute fails the specification')
report('F-64', 'submission accepted after a mandatory review was changed to not_cleared, without a fresh run', accepted(lambda: L.submit(w.owner2, w.clock, rid)))

# F-65: approved with a correct token, then the finding is dismissed; starting the action
w = RecWorld()
f = w.finding(gross=500000)
rid = w.ready(f)
w.run()
L.submit(w.owner2, w.clock, rid)
t = L.approval_token(L.get(w.s, rid))
L.approve(w.pm, w.clock, rid, t['version'], t['digest'], t['submission'], 'ok')
FD.transition(w.rev, w.clock, f, 'dismissed', rationale='not a real issue after all')
report('F-65', 'start of work accepted after the underlying finding was dismissed following approval', accepted(lambda: L.transition(w.owner2, w.clock, rid, 'in_progress')))

# F-66: a policy approval asserted by caller-supplied fields, by someone who is not a policy owner and has no session
w = RecWorld()
if hasattr(RP, 'approve'):
    p = RP.approve(RP.new_policy('FAKE-1', w.s.ctx.user_id), 'someone.unrelated', RP.POLICY_ROLE, 'human', '2026-10-19')
    defect = RP.is_approved(p) and accepted(lambda: RP.store_policy(w.s, p))
else:
    p = dict(RP.new_policy('FAKE-1', w.s.ctx.user_id), approvals=[{'approver': 'someone.unrelated', 'role': RP.POLICY_ROLE, 'kind': 'human', 'date': '2026-10-19'}])
    defect = accepted(lambda: RP.store_policy(w.s, p))
report('F-66', 'a policy accepted as approved on caller-supplied approver, role and kind fields', defect)

print('DEFECT PRESENT' if any(present) else 'THE AUDIT FINDINGS ARE CORRECTED', '(%d of %d present)' % (sum(present), len(present)))
sys.exit(1 if any(present) else 0)
