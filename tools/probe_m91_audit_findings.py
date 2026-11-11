#!/usr/bin/env python3
"""Reproduces the defects the independent audit of APG-M9.1 found (F-58 to F-60), the audit-consistency risk it raised, and the gap the builder found in the same class (F-61), in a few lines.  Usage (from the package root):
python3 -I tools/probe_m91_audit_findings.py
On APG-M9.1: `present` gives the approval token to a caller who cannot approve; the answer CONCURRENT_CHANGE (a conflict on opening the request record) writes no audit event; a request id ending in a newline is accepted; an
approval whose success audit entry failed to write is noted as done, so the retry never writes the entry; `check_for_execution` refuses a malformed call without an audit event.  On APG-M9.2 each is corrected.
Exit 0 only if all five are corrected; exit 1 and the words DEFECT PRESENT otherwise.  It uses the in-memory test world of the unit tests and changes nothing outside it."""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_api_approval_boundary import Grants, Flaky, once, AB, FD, TEXT1
from tests.test_det_findings import breach, first
from tests.test_det_proposal_binding import proposed

bad = []


def world():
    m = breach()
    fid, _ = first(m)
    proposed(m, fid, TEXT1)
    return m, fid, Grants({('zero_one', 'abby', 'PRJ-001'): ('view', 'approve')})


def req(m, fid, rid, **over):
    tok = FD.approval_token(FD.get(m.svc, fid))
    d = {'request_id': rid, 'finding_id': fid, 'version': tok['version'], 'digest': tok['digest'], 'proposal': tok['proposal'], 'rationale': 'I approve what I was shown'}
    d.update(over)
    return d


def events(m, kind=None):
    return [e for e in m.w.audit.read(m.s.ctx) if e.event_type.startswith('approval_request.') and (kind is None or e.event_type == kind)]


def verdict(label, corrected, what):
    print(f'{label:<66} -> ' + ('corrected' if corrected else 'DEFECT PRESENT: ' + what))
    if not corrected:
        bad.append(label)


class FlakyLog(Flaky):
    def __init__(self, inner, event):
        super().__init__(inner, None)
        self.event, self.left = event, 1

    def log(self, event, *a, **k):
        if event == self.event and self.left:
            self.left -= 1
            raise RuntimeError('audit store unavailable')
        return self._i.log(event, *a, **k)


m, fid, _ = world()
r = AB.present(m.approver, Grants({('zero_one', 'abby', 'PRJ-001'): ('view',)}), m.clock, fid)
verdict('F-58 a viewer who may not approve is shown the screen', r['status'] == 'shown' and r['can_approve'] is False and r['token'] is None, f"can_approve={r.get('can_approve')} token={'given' if r.get('token') else 'none'}")

m, fid, sc = world()
n = len(events(m))
res = AB.request_approval(Flaky(m.approver, once(FD.ConflictError('x'), lambda k, p: k == AB.REQUEST_KIND and p.get('state') == 'pending')), sc, m.clock, req(m, fid, 'R-1'))
verdict('F-59 a conflict on opening the request record is answered', res['code'] == 'CONCURRENT_CHANGE' and len(events(m)) == n + 1, f"answer {res['code']}, audit events written: {len(events(m)) - n}")

m, fid, sc = world()
try:
    res = AB.request_approval(m.approver, sc, m.clock, req(m, fid, 'R-9\n'))
    ok = res['status'] == 'refused' and res['code'] == 'REQUEST_MALFORMED' and FD.get(m.svc, fid)['status'] == 'action_proposed'
    why = f"answer {res['status']} {res['code']}; finding is {FD.get(m.svc, fid)['status']}"
except Exception as e:
    ok, why = False, f'the request id with a newline was accepted and the approval was recorded, then {type(e).__name__}: {e}'[:150]
verdict('F-60 a request id ending in a newline', ok, why)

m, fid, sc = world()
q = req(m, fid, 'R-1')
try:
    AB.request_approval(FlakyLog(m.approver, 'approval_request.accepted'), sc, m.clock, q)
except RuntimeError:
    pass
again = AB.request_approval(m.approver, sc, m.clock, dict(q))
verdict('audit consistency: approval recorded, success audit entry failed', again['status'] == 'approved' and len(events(m, 'approval_request.accepted')) == 1, f"retry answered {again['status']}, replayed={again.get('replayed')}; 'accepted' entries: {len(events(m, 'approval_request.accepted'))}")

m, fid, sc = world()
n = len(events(m))
AB.check_for_execution(m.approver, sc, m.clock, None, 1, 'd', 'p')
verdict('F-61 the executor check refuses a malformed call', len(events(m)) == n + 1, f'audit events written: {len(events(m)) - n}')
if bad:
    print('DEFECT PRESENT in', len(bad), 'of 5:', bad)
    sys.exit(1)
print('THE AUDIT FINDINGS ARE CORRECTED (builder test world; no independent review)')
