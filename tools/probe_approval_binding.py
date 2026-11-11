#!/usr/bin/env python3
"""Reproduces the defect F-52 in a few lines and shows what the correction does.  Usage (from the package root):  python3 -I tools/probe_approval_binding.py
Builds a finding, takes it to action_approved, then lets a later detection run change its evidence (version 1 to version 2).  On the delivered M5 and M6 code the finding stayed action_approved
at version 2 with the old approval; on APG-M6.1 the approval is ended, the finding is back at action_proposed and the ended approval is kept in its history.  Exit 0 only if the approval is not
treated as in force after the change.  Read-only: it uses the same in-memory test world as the unit tests and writes nothing."""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers_det import inv
from tests.test_det_findings import breach, first
from apg.det import findings as FD


def as_shown(f, **over):
    """Everything the approver was shown (see approval_token) that this version of the code can take: the earlier versions of `transition` have fewer parameters, so the probe also runs on them.  Since APG-M6.5 an approval
    must name all of it."""
    import inspect
    tok = FD.approval_token(f) if hasattr(FD, 'approval_token') else {'version': f['version'], 'digest': f['signal']['state_digest']}
    wanted = {'approving_version': tok.get('version'), 'approving_digest': tok.get('digest'), 'approving_proposal': tok.get('proposal')}
    wanted.update(over)
    have = inspect.signature(FD.transition).parameters
    return {k: v for k, v in wanted.items() if k in have}

m = breach()
fid, _ = first(m)
FD.transition(m.reviewer, m.clock, fid, 'under_review')
FD.transition(m.reviewer, m.clock, fid, 'confirmed', rationale='yes')
FD.transition(m.owner, m.clock, fid, 'action_proposed', action_text='renegotiate the supplier')
FD.transition(m.approver, m.clock, fid, 'action_approved', rationale='approved on the original figure', **as_shown(FD.get(m.svc, fid)))
f0 = FD.get(m.svc, fid)
print('BEFORE', f0['status'], 'version', f0['version'], 'evidence', f0['signal']['state_digest'][:12], 'approved by', f0['action']['approved_by'])
m.clock.advance(3600)
m.invoices(inv('INV-2', sin='SI-2', ex='4000000', cc='CC-01'))          # a much larger overrun arrives after the approval
m.reconcile()
out = m.ingest(m.detect(as_of='2026-10-01'))
f1 = FD.get(m.svc, fid)
print('AFTER ', f1['status'], 'version', f1['version'], 'evidence', f1['signal']['state_digest'][:12], 'approved by', f1['action']['approved_by'], 'updated', out['updated'])
current = FD.approval_current(f1) if hasattr(FD, 'approval_current') else bool(f1['status'] in ('action_approved', 'in_progress') and f1['action']['approved_by'])     # the earlier code had no such check
print('approval still in force:', current, '| status:', f1['status'], '| ended approvals kept:', len(f1['action'].get('approval_history', [])))
ok = f1['status'] != 'action_approved' and not current and f1['version'] == 2 and len(f1['action'].get('approval_history', [])) == 1
print('APPROVAL IS BOUND TO THE EVIDENCE' if ok else 'DEFECT PRESENT: an approval of the old evidence still stands')
sys.exit(0 if ok else 1)
