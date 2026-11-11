#!/usr/bin/env python3
"""Reproduces the defect F-56 (found by the builder while inspecting the approval integration gate CF-22 after the M6.3 audit) in a few lines.  Usage (from the package root):  python3 -I tools/probe_proposal_swap.py
An approver is shown proposal 1 and its approval token.  Before the approver submits, a reviewer sends the finding back to `confirmed` and the owner proposes a DIFFERENT action against the SAME evidence
(the finding version and the evidence digest do not change).  On APG-M6.3 the token still matched and the approval was recorded against the new text, which the approver never saw.  On APG-M6.4 the token also names
the proposal (`proposal`), and the approval is refused (PROPOSAL_CHANGED).  Also shown: the token of the proposal that was shown still approves that proposal, and a second submission of the same approval is
refused and changes nothing.  Exit 0 only if every check holds; exit 1 and the words DEFECT PRESENT if the swapped proposal was approved.  Read-only: it uses the same in-memory test world as the unit tests."""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_det_findings import breach, first
from apg.det import findings as FD


def fresh(text):
    m = breach()
    fid, _ = first(m)
    FD.transition(m.reviewer, m.clock, fid, 'under_review')
    FD.transition(m.reviewer, m.clock, fid, 'confirmed', rationale='yes')
    FD.transition(m.owner, m.clock, fid, 'action_proposed', action_text=text)
    return m, fid


def submit(m, fid, tok, note):
    kw = {'approving_proposal': tok['proposal']} if 'proposal' in tok else {}
    return FD.approve_action(m.approver, m.clock, fid, tok['version'], tok['digest'], note, **kw)


results = []
m, fid = fresh('P1: renegotiate with the supplier')
tok = FD.approval_token(FD.get(m.svc, fid))
print('the approver is shown: P1: renegotiate with the supplier   token', tok)
FD.transition(m.reviewer, m.clock, fid, 'confirmed', rationale='sent back to the owner')
f2 = FD.transition(m.owner, m.clock, fid, 'action_proposed', action_text='P2: terminate the supplier contract')
print(f'the proposal on record is now: {f2["action"]["text"]}   (version {f2["version"]}, evidence digest {f2["signal"]["state_digest"]}: unchanged)')
try:
    g = submit(m, fid, tok, 'I approve what I was shown')
    swapped = 'ACCEPTED ' + g['status'] + ' | approved text: ' + g['action']['text']
except FD.LifecycleError as e:
    swapped = 'REFUSED ' + e.code
print('SUBMIT the token of proposal 1 ->', swapped)
results.append(swapped == 'REFUSED PROPOSAL_CHANGED')
after = FD.get(m.svc, fid)
print('record afterwards:', after['status'], '| approver recorded:', after['action']['approved_by'])
results.append(after['status'] == 'action_proposed' and after['action']['approved_by'] is None)

m2, fid2 = fresh('P1: renegotiate with the supplier')
tok2 = FD.approval_token(FD.get(m2.svc, fid2))
g2 = submit(m2, fid2, tok2, 'approve what I was shown')
print('SUBMIT the token of the proposal that is on record ->', g2['status'], '| approved text:', g2['action']['text'], '| approval current:', FD.approval_current(g2))
results.append(g2['status'] == 'action_approved' and g2['action']['text'].startswith('P1') and FD.approval_current(g2))
n = len(g2['history'])
try:
    submit(m2, fid2, tok2, 'the same approval sent again')
    again = 'ACCEPTED'
except FD.LifecycleError as e:
    again = 'REFUSED ' + e.code
same = FD.get(m2.svc, fid2)
print('SUBMIT the same approval again ->', again, '| history events unchanged:', len(same['history']) == n)
results.append(again.startswith('REFUSED') and len(same['history']) == n)
ok = all(results)
print('APPROVAL IS BOUND TO THE EXACT PROPOSAL' if ok else 'DEFECT PRESENT: an approval was recorded against a proposal the approver was not shown, or a check failed')
sys.exit(0 if ok else 1)
