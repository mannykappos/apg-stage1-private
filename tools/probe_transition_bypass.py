#!/usr/bin/env python3
"""Reproduces the defect F-57 (found by the independent audit of APG-M6.4) in a few lines.  Usage (from the package root):  python3 -I tools/probe_transition_bypass.py
On APG-M6.4 the entry point `approve_action` refuses an approval that does not name the finding version, the evidence digest and the proposal reference the approver was shown.  The lower-level
`transition(..., 'action_approved', ...)` accepted an approval that named none of them, one that named only some of them, and one that named a proposal reference but no version or digest, so the
protection could be bypassed by calling the lower-level function.  On APG-M6.5 `transition` itself refuses (APPROVAL_TOKEN_REQUIRED) unless all three are named, and checks each against the record.
Exit 0 only if every bypass is refused and the legitimate approval still works; exit 1 and the words DEFECT PRESENT if any bypass was accepted.  Read-only: it uses the in-memory test world of the unit tests."""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_det_findings import breach, first
from apg.det import findings as FD


def fresh():
    m = breach()
    fid, _ = first(m)
    FD.transition(m.reviewer, m.clock, fid, 'under_review')
    FD.transition(m.reviewer, m.clock, fid, 'confirmed', rationale='yes')
    FD.transition(m.owner, m.clock, fid, 'action_proposed', action_text='renegotiate the supplier')
    return m, fid


def attempt(label, pick):
    m, fid = fresh()
    tok = FD.approval_token(FD.get(m.svc, fid))
    kw = {}
    if 'v' in pick:
        kw['approving_version'] = tok['version']
    if 'd' in pick:
        kw['approving_digest'] = tok['digest']
    if 'p' in pick and 'proposal' in tok:
        kw['approving_proposal'] = tok['proposal']['proposal_ref'] if isinstance(tok['proposal'], dict) else tok['proposal']
    try:
        g = FD.transition(m.approver, m.clock, fid, 'action_approved', rationale='approve', **kw)
        out = 'ACCEPTED ' + g['status']
    except FD.LifecycleError as e:
        out = 'REFUSED ' + e.code
    print(f'{label:<58} -> {out}')
    return out


results = {}
for label, pick in [('no token at all', ''), ('version only', 'v'), ('digest only', 'd'), ('proposal reference only', 'p'), ('version and digest, no proposal reference', 'vd'),
                    ('version and proposal reference, no digest', 'vp'), ('digest and proposal reference, no version', 'dp')]:
    results[label] = attempt(label, pick)
legit = attempt('all three, as shown (legitimate)', 'vdp')
bad = [k for k, v in results.items() if v.startswith('ACCEPTED')]
if bad or not legit.startswith('ACCEPTED'):
    print('DEFECT PRESENT: accepted without a full token:' if bad else 'the legitimate approval failed', bad)
    sys.exit(1)
print('OK: every incomplete approval is refused at transition and the complete one is accepted')
