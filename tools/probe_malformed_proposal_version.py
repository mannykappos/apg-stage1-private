#!/usr/bin/env python3
"""Reproduces the defect F-55 (the independent audit of APG-M6.2, section 3) in a few lines and shows what the M6.3 correction does.  Usage (from the package root):  python3 -I tools/probe_malformed_proposal_version.py
Builds a finding and a normal version-1 proposal, then writes the boolean True into the stored proposal version (simulating malformed, legacy or damaged persisted state; the lifecycle itself never writes it),
obtains the current approval token and calls approve_action.  On APG-M6.2 Python's True == 1 made the proposal count as current and the approval was accepted.  On APG-M6.3 it is refused (STALE_PROPOSAL), also
for a stored False, 0 and the text '1', and a boolean or text version named by the approver is refused as a malformed token.  Exit 0 only if every malformed case is refused and a normal proposal is still approvable.
Read-only: it uses the same in-memory test world as the unit tests."""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from apg import canon
from tests.test_det_findings import breach, first
from apg.det import findings as FD


def fresh():
    m = breach()
    fid, _ = first(m)
    FD.transition(m.reviewer, m.clock, fid, 'under_review')
    FD.transition(m.reviewer, m.clock, fid, 'confirmed', rationale='yes')
    FD.transition(m.owner, m.clock, fid, 'action_proposed', action_text='renegotiate the supplier')
    return m, fid


def damage(m, fid, value):
    rec = FD._load(m.svc, fid)
    f = canon.deep_copy(rec.payload)
    f['action']['proposed_version'] = value
    FD._put(m.svc, rec, f)


results = []
for label, value in (('True', True), ('False', False), ('0', 0), ("the text '1'", '1')):
    m, fid = fresh()
    damage(m, fid, value)
    f = FD.get(m.svc, fid)
    t = FD.approval_token(f)
    current = FD.proposal_current(f) if hasattr(FD, 'proposal_current') else None
    try:
        g = FD.approve_action(m.approver, m.clock, fid, t['version'], t['digest'], 'approve', approving_proposal=t['proposal'] or 'r' * 24)
        outcome = 'ACCEPTED ' + g['status']
    except FD.LifecycleError as e:
        outcome = 'REFUSED ' + e.code
    results.append((label, outcome))
    print(f'STORED proposal version {label:<13} proposal_current={current!s:<5} approve_action -> {outcome}')
named = []
for label, v in (('True', True), ('1.0', 1.0), ("'1'", '1')):
    m, fid = fresh()
    try:
        t0 = FD.approval_token(FD.get(m.svc, fid))
        FD.transition(m.approver, m.clock, fid, 'action_approved', rationale='approve', approving_version=v, approving_digest=t0['digest'], approving_proposal=t0['proposal'])
        named.append((label, 'ACCEPTED'))
    except FD.LifecycleError as e:
        named.append((label, 'REFUSED ' + e.code))
for label, outcome in named:
    print(f'NAMED version {label:<5} -> {outcome}')
m, fid = fresh()
t = FD.approval_token(FD.get(m.svc, fid))
g = FD.approve_action(m.approver, m.clock, fid, t['version'], t['digest'], 'approve a normal proposal', approving_proposal=t['proposal'])
print('NORMAL proposal ->', g['status'], '| approval current:', FD.approval_current(g))
ok = all(o == 'REFUSED STALE_PROPOSAL' for _, o in results) and all(o == 'REFUSED APPROVAL_TOKEN_REQUIRED' for _, o in named) and g['status'] == 'action_approved' and FD.approval_current(g)
print('MALFORMED VERSIONS ARE REFUSED' if ok else 'DEFECT PRESENT: a malformed stored or named version was accepted')
sys.exit(0 if ok else 1)
