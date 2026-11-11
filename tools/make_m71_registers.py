#!/usr/bin/env python3
"""Adds the APG-M7.1 rows to the programme tables: findings F-64 to F-67, status rows SR-98 to SR-100, interpretations I-110 to I-113, the Engine handoff entry EDR-34 and the carried-forward
item CF-33.  Usage: make_m71_registers.py <programme_dir>   (runs AFTER make_m7_registers.py).  Idempotent; no existing row is changed.  Nothing here closes a finding or settles a decision."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402

OPEN = 'Corrected in APG-M7.1 (builder-implemented); open until independently verified'
AUDIT = 'Independent audit of APG-M7 (the audit text was relayed by the product owner; reproduced by the auditor, and again by the builder on the delivered M7 package with tools/probe_m7_audit_findings.py)'
FIND = [
    dict(finding_id='F-64', raised_by=AUDIT, milestone='M7.1', title='Submission and approval accepted a recommendation whose finding or mandatory review had changed after the run',
         description='A recommendation record is a snapshot of the run that produced it. M7 checked the submission gate and the approval token against that snapshot only, so a recommendation stayed submittable and approvable after its finding was dismissed or its mandatory review was changed to not_cleared, until someone ran the engine again. The same held for changed costs, benefit, alternatives, evidence assessments and policy.',
         linked_items='apg/rec/lifecycle.py (source_check); tests/test_rec_m71_corrections.py; tools/probe_m7_audit_findings.py; I-110', how_it_is_handled_here='Submission, approval and the start of work each check first that the finding, its overlapping findings, its inputs and reviews and its policy are at exactly the revisions the run pinned, and that a run made now would give the same recommendation; otherwise the act is refused (SOURCE_CHANGED) until the engine runs again.', status=OPEN),
    dict(finding_id='F-65', raised_by=AUDIT, milestone='M7.1', title='The start of work was accepted after the finding changed following a valid approval',
         description='The approval token bound the decision to the recommendation version, but the version was not invalidated when the underlying finding changed, so in_progress was accepted after the finding was dismissed.',
         linked_items='apg/rec/lifecycle.py (source_check at in_progress); tests/test_rec_m71_corrections.py (TestStaleBetweenApprovalAndStart); F-64', how_it_is_handled_here='Corrected with F-64: the start of work is source-checked too; a fresh run after a material change ends the approval as before.', status=OPEN),
    dict(finding_id='F-66', raised_by=AUDIT, milestone='M7.1', title='A recommendation-policy approval could be asserted by caller-supplied approver, role and kind fields',
         description='policy.approve() took the approver name, role and actor kind as ordinary arguments with no authenticated context, and store_policy accepted the result, so an unrelated person could be recorded as the approving human policy owner. No API exists in M7, so no external path was shown; the module itself did not enforce the safeguard.',
         linked_items='apg/rec/policy.py (store_policy, approve_policy, verified_approvers); apg/rec/engine.py (run); tests/test_rec_m71_corrections.py (TestPolicyApprovalBoundary); I-112; EDR-34', how_it_is_handled_here='approve() is removed. A policy is stored only by its proposer (from the verified context) and only without approvals; approve_policy records an approval from the approver\'s own verified context (human, policy-owner role, not the proposer) and writes an audit event; a run counts only approvals the audit log confirms, records them in its parameters, and under an unapproved policy blocks every submission.', status=OPEN),
    dict(finding_id='F-67', raised_by='Builder (same-class sweep of F-66 in M7.1)', milestone='M7.1', title='The detection, financial and procurement policies have the same caller-supplied approval function',
         description='det/policy.approve, fin/policy.approve and mkt/policy.approve (and the procurement specification register) take the approver, role and kind as arguments, like the recommendation policy did before F-66. Their demonstration policies are approved that way.',
         linked_items='apg/det/policy.py; apg/fin/policy.py; apg/mkt/policy.py; F-66', how_it_is_handled_here='NOT corrected here: M7.1 is a correction of M7 and changes no M2 to M6 file. Recorded so that it is not lost; it needs its own correction release (the same pattern as F-66) when the product owner authorises it.', status='Open - not corrected'),
]
STATUS = [
    dict(item_id='SR-98', item='Source-freshness check at submission, approval and the start of work (apg/rec/lifecycle.py source_check): exact pinned revisions of the finding, overlapping findings, inputs and policy, plus an in-memory recomputation', milestone='M7.1',
         evidence_ladder_status='Local-tested', evidence='tests/test_rec_m71_corrections.py; tools/probe_m7_audit_findings.py', claim_limit=M7.CLAIM),
    dict(item_id='SR-99', item='Recommendation-policy approval boundary (apg/rec/policy.py approve_policy, store_policy, verified_approvers): approvals only from the approver\'s own verified context and confirmed by the audit log at every run', milestone='M7.1',
         evidence_ladder_status='Local-tested', evidence='tests/test_rec_m71_corrections.py (TestPolicyApprovalBoundary)', claim_limit=M7.CLAIM + ' Who may write the policy record kind and the audit log is the Engine\'s (EDR-34).'),
    dict(item_id='SR-100', item='Mutation run over the corrected apg/rec and package sabotage checks for M7.1, run fresh by the build', milestone='M7.1',
         evidence_ladder_status='Local-tested', evidence='tools/m7_mutants.py; tools/sabotage_m71.py; logs/m71/', claim_limit=M7.CLAIM),
]
INTERP = [
    ('I-110', 'What counts as a changed source', 'Any new revision of the finding, an overlapping finding, the recommendation inputs or the policy refuses submission, approval and start, even when nothing material changed (for example a detection sweep that only refreshes when the finding was last seen). A fresh run then either keeps the version (the submission or approval stands) or makes a new one. This is fail-closed and asks for more runs.', '10:3; 10:9', 'If refusing after every detection sweep is too strict, the exact check could ignore the fields detection refreshes; the recomputation would still catch material changes.'),
    ('I-111', 'Completion and verification are not source-checked', 'After people have started the work, a source change is recorded and ends the approval (I-106) but does not stop completion or verification: they record what happened, and the verifier sees the history.', '10:9; 10:10; 05:10.1', 'If the product owner wants completion blocked after a source change, add in_progress -> completed to the checked moves.'),
    ('I-112', 'What confirms a policy approval', 'A policy approval counts only when the tenant\'s audit log holds a rec.policy_approved event for that version written under the approver\'s own verified human context. APG cannot stop code outside its functions from writing the store or the audit log directly; restricting who may write these record kinds is the Engine\'s (EDR-34).', '15:15.8; 10:9', 'With an Engine that lets any caller write the policy record kind and the audit log under their own name, a person could still approve as themselves without the role check.'),
    ('I-113', 'An unapproved policy blocks submission', 'Recommendations computed under a policy that no policy owner has approved (as confirmed by the audit log) are shown and ranked but cannot be submitted for approval.', '06:5.1; 10:4', 'If the product owner wants unapproved policies usable in a pilot, this gate would need a recorded exception.'),
]
EDR = dict(edr_id='EDR-34', port='RecordKindWriteGuard', title='Record kinds that only their APG boundary may write, and audit events bound to the verified actor',
           what_apg_needs='The recommendation policy (rec_policy), recommendation records (recommendation), recommendation inputs (rec_input) and verification records (rec_verification) must be writable only through their APG functions (policy.store_policy and approve_policy, lifecycle, inputs, verify), as the approval_request kind of M9 (EDR-31 family). Audit events must carry the verified actor (as the reference audit log does).',
           why_the_engine_is_needed='The record store and the audit log are the Engine\'s. APG\'s in-memory store lets any authenticated caller write any kind, so APG can only check what it reads (the audit confirmation of F-66, the source check of F-64).',
           contract_summary='To be agreed: a per-kind write guard (only the named service or function identity may write the kind); audit append binds actor and actor kind from the verified context and cannot be written with another actor.',
           contract_test='None written: the in-memory store has no per-kind guard.', blueprint_refs='15:15.8; 15:15.11; 10:9', capabilities='CAP-30; CAP-31', needed_by_milestones='M9; M12',
           decisions_for_amir='Whether the Engine store can restrict writes per record kind; how APG functions are identified to it.', owner='Amir (engine, database, environment)', status='Open - described only',
           evidence_seen='No Engine code, repository or environment seen; no implementation exists')
CF = dict(cf_id='CF-33', audit_section='', topic='Runs the M7 audit could not complete',
          what_remains_open='In the M7 audit the whole unit suite and the package sabotage suite did not complete within the auditor\'s execution limit (three sabotage cases ran), and the mutation suite was not run; these are incomplete, not passes. The delivered M9.4 ZIP was not supplied, so the M9.4 comparison used the manifest and snapshots inside M7.',
          what_this_package_shows='M7.1 splits the whole suite into ten counted groups (groups 6 to 15 of tools/run_m71_all.py, 2,254 tests), the sabotage suite into single cases (--only Sxx), and the mutation run by module and kind (--only EN-CMP etc.). The product owner can supply the delivered M9.4 and M7 ZIPs so that the manifests can be compared with the real archives.',
          linked_records='CF-32; SR-100', who_must_act='Auditor: run the split commands and record which completed; product owner: supply the M9.4 and M7 ZIPs to the auditor', status='Open - for the auditor')

if __name__ == '__main__':
    P = sys.argv[1]
    M7.P = P
    M7.add('FINDINGS_REGISTER.csv', 'finding_id', FIND)
    M7.add('STATUS_REGISTER.csv', 'item_id', STATUS)
    M7.add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=i, milestone='M7.1', topic=t, builder_reading=b, blueprint_ref=r, effect_if_wrong=e, status=M7.RETAINED) for i, t, b, r, e in INTERP])
    M7.add('ENGINE_HANDOFF_REGISTER.csv', 'edr_id', [EDR])
    M7.add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', [CF])
