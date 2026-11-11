#!/usr/bin/env python3
"""Reproduces the defect F-53 (the audit of APG-M6.1, section 5) in a few lines and shows what the M6.2 correction does.  Usage (from the package root):  python3 -I tools/probe_stale_proposal.py
Builds a finding, proposes an action against its version-1 evidence, lets a later detection run change the evidence to version 2 while the finding is still action_proposed, then has a different person
approve WITHOUT naming a version.  On APG-M6.1 the approval was accepted and bound to version 2.  On APG-M6.2 it is refused (STALE_PROPOSAL), also when the current version is named, and the proposal can
only be approved after a reviewer sends it back and the owner proposes again.  Exit 0 only if the stale proposal is NOT approved.  Read-only: it uses the same in-memory test world as the unit tests."""
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
f1 = FD.transition(m.owner, m.clock, fid, 'action_proposed', action_text='renegotiate based on the original figure')
print('PROPOSED ', f1['status'], 'version', f1['version'], 'evidence', f1['signal']['state_digest'][:12], 'action written against version', f1['action'].get('proposed_version'))
m.clock.advance(3600)
m.invoices(inv('INV-2', sin='SI-2', ex='4000000', cc='CC-01'))          # a much larger overrun arrives while the proposal waits
m.reconcile()
out = m.ingest(m.detect(as_of='2026-10-01'))
f2 = FD.get(m.svc, fid)
print('CHANGED  ', f2['status'], 'version', f2['version'], 'evidence', f2['signal']['state_digest'][:12], 'action still written against version', f2['action'].get('proposed_version'), '| stale proposals reported by the run:', out.get('proposals_stale', '(not reported)'))
results = []
for label, kw in (('no version named', {}), ('current version named', {'approving_version': f2['version']}), ('the whole token as shown', as_shown(f2))):
    try:
        g = FD.transition(m.approver, m.clock, fid, 'action_approved', rationale='approve', **kw)
        results.append((label, 'ACCEPTED', g['status'], g['action']['approved_version']))
        break                                                          # the first acceptance is the defect; the finding is no longer action_proposed
    except FD.LifecycleError as e:
        results.append((label, 'REFUSED ' + e.code, '', None))
for r in results:
    print('APPROVE  ', r[0], '->', r[1], (r[2] + ' at version ' + str(r[3])) if r[1] == 'ACCEPTED' else '')
accepted = any(r[1] == 'ACCEPTED' for r in results)
ok = not accepted and len(results) == 3 and results[2][1] == 'REFUSED STALE_PROPOSAL' and all(r[1] in ('REFUSED STALE_PROPOSAL', 'REFUSED APPROVAL_TOKEN_REQUIRED') for r in results)       # M6.5: an incomplete token is refused before staleness is looked at
if ok:
    FD.transition(m.reviewer, m.clock, fid, 'confirmed', rationale='the evidence changed; back to the owner')
    FD.transition(m.owner, m.clock, fid, 'action_proposed', action_text='renegotiate on the larger overrun')
    g = FD.transition(m.approver, m.clock, fid, 'action_approved', rationale='approve the new proposal', **as_shown(FD.get(m.svc, fid)))
    old = g['action']['proposal_history']
    print('REPROPOSE', g['status'], 'version', g['version'], '| approved version', g['action']['approved_version'], '| the replaced proposal is kept:', [(e['text'], e['proposed_version'], e['proposal_state']) for e in old])
    ok = g['status'] == 'action_approved' and len(old) == 1 and old[0]['proposed_version'] == 1 and old[0]['proposal_state'] == 'stale' and FD.approval_current(g)
print('PROPOSAL IS BOUND TO THE EVIDENCE' if ok else 'DEFECT PRESENT: a proposal written against old evidence was approved')
sys.exit(0 if ok else 1)
