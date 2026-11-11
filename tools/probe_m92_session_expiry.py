#!/usr/bin/env python3
"""Reproduces the gap the independent audit of APG-M9.2 found (F-62) in a few lines each:  python3 -I tools/probe_m92_session_expiry.py
On APG-M9.2 a session whose expiry has the right shape but is not a real moment (2999-99-99T99:99:99Z, 2999-13-01T00:00:00Z, 2999-01-01T25:61:61Z, 2999-02-30T00:00:00Z) counts as live, so a request carrying it is APPROVED, and a clock that says something that is not a moment
does not end the session.  On APG-M9.3 each is refused and nothing is approved; a real leap day (2400-02-29) is still accepted.
Exit 0 only if all are corrected; exit 1 and the words DEFECT PRESENT otherwise.  It uses the in-memory test world of the unit tests and changes nothing outside it."""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_api_approval_boundary import Grants, AB, FD, TEXT1
from tests.test_api_m93_corrections import Expiring, Fixed
from tests.test_det_findings import breach, first
from tests.test_det_proposal_binding import proposed

bad = []


def world():
    m = breach()
    fid, _ = first(m)
    proposed(m, fid, TEXT1)
    return m, fid, Grants({('zero_one', 'abby', 'PRJ-001'): ('view', 'approve')})


def req(m, fid, rid):
    tok = FD.approval_token(FD.get(m.svc, fid))
    return {'request_id': rid, 'finding_id': fid, 'version': tok['version'], 'digest': tok['digest'], 'proposal': tok['proposal'], 'rationale': 'I approve what I was shown'}


def verdict(label, corrected, what):
    print(f'{label:<66} -> ' + ('corrected' if corrected else 'DEFECT PRESENT: ' + what))
    if not corrected:
        bad.append(label)


for i, value in enumerate(('2999-99-99T99:99:99Z', '2999-13-01T00:00:00Z', '2999-01-01T25:61:61Z', '2999-02-30T00:00:00Z'), 1):
    m, fid, sc = world()
    res = AB.request_approval(Expiring(m.approver, value), sc, m.clock, req(m, fid, f'R-{i}'))
    st = FD.get(m.svc, fid)['status']
    verdict(f'F-62 a session that expires {value}', res['status'] == 'refused' and res['code'] == 'SESSION_EXPIRED' and st == 'action_proposed', f"answer {res['status']} {res['code']}; the finding is {st}")

m, fid, sc = world()
res = AB.request_approval(m.approver, sc, Fixed('2026-13-01T09:00:00Z'), req(m, fid, 'R-5'))
verdict('F-62 a clock that does not say a real moment', res['status'] == 'refused' and FD.get(m.svc, fid)['status'] == 'action_proposed', f"answer {res['status']} {res['code']}")

m, fid, sc = world()
res = AB.request_approval(Expiring(m.approver, '2400-02-29T00:00:00Z'), sc, m.clock, req(m, fid, 'R-6'))
verdict('a real leap day in the future is still a live session', res['status'] == 'approved', f"answer {res['status']} {res['code']}")
if bad:
    print('DEFECT PRESENT in', len(bad), 'of 6:', bad)
    sys.exit(1)
print('THE SESSION EXPIRY CHECK IS CORRECTED (builder test world; no independent review)')
