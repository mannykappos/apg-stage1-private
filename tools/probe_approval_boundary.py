#!/usr/bin/env python3
"""Shows the APG-M9.1 approval request boundary in a few lines.  Usage (from the package root):  python3 -I tools/probe_approval_boundary.py
It walks six situations through `present`, `request_approval` and `check_for_execution` in the in-memory test world of the unit tests, and prints what each returns: the normal path; the same request sent twice; evidence that
changes after the approval; a proposal replaced after it was shown; a person who may not approve in the finding's project; a request with a field it should not have.
Exit 0 only if every situation ends as the contract says.  It shows what the builder's code does in the builder's test world; it does not show that the contract is right or that any real screen, API or permission model exists
(none does).  Read-only."""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_api_approval_boundary import Grants, AB, FD, TEXT1, TEXT2
from tests.test_det_findings import breach, first
from tests.test_det_proposal_binding import proposed, reproposed
from tests.test_det_approval_binding import worsen

bad = []


def world():
    m = breach()
    fid, _ = first(m)
    proposed(m, fid, TEXT1)
    return m, fid, Grants({('zero_one', 'abby', 'PRJ-001'): ('view', 'approve')})


def req(m, fid, rid, tok=None, **over):
    tok = tok or FD.approval_token(FD.get(m.svc, fid))
    d = {'request_id': rid, 'finding_id': fid, 'version': tok['version'], 'digest': tok['digest'], 'proposal': tok['proposal'], 'rationale': 'I approve what I was shown'}
    d.update(over)
    return d


def line(label, got, want):
    ok = all(got.get(k) == v for k, v in want.items())
    print(f'{label:<64} -> {got.get("status", "valid=" + str(got.get("valid")))} {got.get("code")}' + (' (replayed)' if got.get('replayed') else '') + ('' if ok else '   <-- NOT AS THE CONTRACT SAYS'))
    if not ok:
        bad.append(label)


m, fid, sc = world()
shown = AB.present(m.approver, sc, m.clock, fid)
line('1. the approval screen shows the proposal and a token', shown, {'status': 'shown', 'can_approve': True})
r1 = AB.request_approval(m.approver, sc, m.clock, req(m, fid, 'REQ-1', shown['token']))
line('1. the approver asks to approve what was shown', r1, {'status': 'approved', 'code': 'OK'})
r2 = AB.request_approval(m.approver, sc, m.clock, req(m, fid, 'REQ-1', shown['token']))
line('2. the same request is sent again', r2, {'status': 'approved', 'replayed': True})
n = len([h for h in FD.get(m.svc, fid)['history'] if h['event'] == 'status_change' and h['to'] == 'action_approved'])
print(f'2. approvals recorded in the finding history after two sends        -> {n}')
if n != 1:
    bad.append('replay approved twice')
tok = shown['token']
chk = AB.check_for_execution(m.approver, sc, m.clock, fid, tok['version'], tok['digest'], tok['proposal'])
line('3. whoever carries the action out asks: is it still approved?', chk, {'valid': True})
worsen(m)
chk2 = AB.check_for_execution(m.approver, sc, m.clock, fid, tok['version'], tok['digest'], tok['proposal'])
line('3. the evidence changed after the approval; asked again', chk2, {'valid': False})

m, fid, sc = world()
old = FD.approval_token(FD.get(m.svc, fid))
reproposed(m, fid, TEXT2)
r = AB.request_approval(m.approver, sc, m.clock, req(m, fid, 'REQ-2', old))
line('4. approval of a proposal that was replaced after it was shown', r, {'status': 'refused'})
print(f'4. the finding is still {FD.get(m.svc, fid)["status"]!r}, not approved' if FD.get(m.svc, fid)['status'] != 'action_approved' else '4. DEFECT: the finding was approved')
if FD.get(m.svc, fid)['status'] == 'action_approved':
    bad.append('swap approved')

m, fid, _ = world()
other = Grants({('zero_one', 'abby', 'PRJ-OTHER'): ('view', 'approve')})
r = AB.request_approval(m.approver, other, m.clock, req(m, fid, 'REQ-3'))
unknown = AB.request_approval(m.approver, other, m.clock, req(m, fid, 'REQ-4', finding_id='F-NO-SUCH'))
line('5. a person with no right to approve in the finding\'s project', r, {'status': 'refused', 'code': 'NOT_FOUND'})
same = (r['code'], r['message']) == (unknown['code'], unknown['message'])
print(f'5. the same answer as for a finding that does not exist             -> {same}')
if not same:
    bad.append('project refusal differs from unknown finding')

m, fid, sc = world()
r = AB.request_approval(m.approver, sc, m.clock, req(m, fid, 'REQ-5', approved_by='someone-else'))
line('6. a request with a field the contract does not have', r, {'status': 'refused', 'code': 'REQUEST_MALFORMED'})
if bad:
    print('BOUNDARY DOES NOT BEHAVE AS THE CONTRACT SAYS:', bad)
    sys.exit(1)
print('THE BOUNDARY BEHAVES AS THE CONTRACT SAYS in these six situations (builder test world; no independent review)')
