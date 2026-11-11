#!/usr/bin/env python3
"""Correction release APG-F67.3 (finding F-74, from the independent audit of APG-F67.2, and the defect class of F-73 and F-74): appends its rows to the programme tables.
Programme rows are never edited.
  * F-74: an old confirmation still counted for a re-planted entry; the builder found the same for a changed entry and for rewritten approved content (all five records).
  * SR-117 (the correction) and SR-118 (its auditable runs and the history contract); I-132 (the rule, the threat model, the store guarantees); EDR-41 (the record-store history
    contract an Engine store must pass); CF-44 (the audit of APG-F67.3; M8 not authorised).
Usage: make_f673_registers.py <programme_dir>   (runs AFTER make_f672_registers.py).  Idempotent; no existing row is changed.  Nothing here accepts a release, closes a finding
or a gate, or records a result the auditor did not report."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402

M = 'F-67.3'
OPEN = 'Corrected in APG-F67.3 (builder-implemented); open until independently verified'
CLAIM = ('Builder-run; no independent review has taken place. Direct writes are simulated in APG\'s in-memory reference; nothing is integrated with the Anchor Engine, which '
         'must still restrict direct writes (EDR-39), write a record and its event atomically (EDR-40) and pass the record-store history contract (EDR-41).')
FIND = [dict(finding_id='F-74', milestone=M,
             raised_by='Independent audit of APG-F67.2 (relayed by the product owner on 2026-10-20; reproduced by the auditor on all five records, and again by the builder on the '
                       'delivered F67.2 package with tools/probe_f673.py)',
             title='An old confirmation still counted after the approval it confirmed was removed and re-planted, changed, or its approved content rewritten',
             description='APG-F67.2 counted a confirming event when the revision it named had added the approver\'s entry, but did not check what happened after that revision. A '
                         'genuine approval (revision 2, event naming revision 2) whose entry was removed (revision 3) and re-planted (revision 4) by direct store writes still '
                         'counted (auditor, all five records). The builder found the same class: an entry changed in place, the approved content rewritten with the entry kept, '
                         'and content rewritten then restored, all still counted; and the owner could not approve the changed content again ("already approved").',
             linked_items='apg/policy_approval.py (holds, content, confirmed, confirmations); apg/rec/policy.py (verified_approvers); apg/rec/engine.py; apg/fin, det, mkt gather.py; '
                          'apg/contracts/record_store_history_contract.py; tests/test_f673_approval_integrity.py; tools/probe_f673.py; tools/run_history_contract.py; I-132; EDR-41',
             how_it_is_handled_here='A confirmation counts only while the approval it confirms HOLDS at the revision being judged, for a run the exact revision it pinned: the '
                                    'revision the event names added the approver\'s entry, and in every revision from there through the judged one that entry is present and '
                                    'unchanged and the approved content (every field except the approvals) is unchanged. Adding other people\'s approvals keeps it. A broken '
                                    'confirmation never counts again; the owner approves afresh. The gatherers and the recommendation run judge at the pinned revisions.',
             status=OPEN)]
STATUS = [
    dict(item_id='SR-117', milestone=M, evidence_ladder_status='Local-tested',
         item='The APG-F67.3 correction of F-74 and its defect class for all five policy records: a confirmation counts only while the approver\'s entry and the approved content '
              'stay unchanged from the confirmed revision through the revision a run pins',
         evidence='tests/test_f673_approval_integrity.py (12 tests over the five records; 10 fail or error on the delivered APG-F67.2 code, 2 guard properties F-67.2 already '
                  'had); tools/probe_f673.py (41 cases with one control: 25 defects present on APG-F67.2, 0 here); programme/CHANGE_RECORD_APG-F67.3.md', claim_limit=CLAIM),
    dict(item_id='SR-118', milestone=M, evidence_ladder_status='Local-tested',
         item='The record-store history contract (RH-01 to RH-06) against the reference store and four faulty stores; the APG-F67.3 auditable runs',
         evidence='apg/contracts/record_store_history_contract.py; tools/run_history_contract.py; tools/run_f673_all.py; tools/f673_mutants.py; tools/sabotage_f673.py; '
                  'tools/run_regression_f673.py; logs/f673/', claim_limit=CLAIM),
]
INTERP = [('I-132', 'When a confirmation counts: the approval must still hold at the revision judged',
           'Threat model (the product owner\'s authorisation of F-67.3): the attacker can append arbitrary revisions of a policy record directly to the store - plant, remove, '
           're-plant or modify approval entries, rewrite policy content while keeping entries - at any time between approval, confirmation and a run; the attacker cannot write '
           'an audit event as another person, rewrite or delete a past revision or audit event, or change what a pinned revision reads on replay. Rule: a confirmation counts '
           'at revision R (a run\'s pinned revision; otherwise the latest) only if it is authentic (I-128), names the revision that added the approver\'s entry (I-131), and in '
           'every revision from that one through R the approver\'s entry is present and unchanged and the approved content - every field except the approvals - is unchanged. '
           'Content changed and changed back does not count (the content must stay unchanged throughout). Adding other people\'s approvals keeps it. A broken confirmation '
           'never counts again; the owner approves afresh (never stuck). The store guarantees this relies on are stated and tested as a contract (EDR-41: revisions numbered '
           '1..n; a past revision reads back the same for ever and cannot be changed through what a caller reads; a revision outside 1..n reads as nothing; an identical write '
           'appends nothing; history and get agree; per tenant). LIMIT: whoever can write both the store and an audit event in the approver\'s name is outside APG\'s checks '
           '(EDR-39, EDR-40).',
           'F-73; F-74; I-128; I-131; EDR-39; EDR-40; EDR-41', 'If content changed and changed back should keep an approval, holds would compare the content only at the '
           'confirmed and the judged revision; test_content_rewritten_and_then_restored_no_longer_counts would change.')]
EDR = dict(edr_id='EDR-41', port='RecordStorePort (revision history)',
           title='Pass the record-store history contract: revisions 1..n, immutable history, out-of-range reads as nothing, identical writes append nothing',
           what_apg_needs='APG judges a policy approval by reading the revision an event names, the one before it and every revision up to the one a run pinned (I-132), and a run '
                          'replays the exact revisions it pinned. An Engine store must pass apg/contracts/record_store_history_contract.py (RH-01 to RH-06): revisions numbered '
                          '1..n in the order written; a past revision reads back the same for ever and cannot be changed through any object a caller holds; a revision outside '
                          '1..n (0, negative, beyond n, a boolean, text or a fraction) reads as nothing; an identical payload appends nothing and any other appends exactly one; '
                          'history and get agree; per tenant. Run with: python3 -I tools/run_history_contract.py --factory module:attr.',
           why_the_engine_is_needed='Persistence is the Engine\'s; the reference store passes the contract and four deliberately faulty stores fail it, but no Engine store has been seen.',
           contract_summary='apg/contracts/record_store_history_contract.py; tools/run_history_contract.py', contract_test='tools/run_history_contract.py',
           blueprint_refs='F-73; F-74; I-132; EDR-02; EDR-39; EDR-40', capabilities='', needed_by_milestones='Any use of a policy approval outside tests',
           decisions_for_amir='How the Engine store keeps revision history immutable, and returns nothing for a revision outside 1..n.',
           owner='Amir (engine, database, environment)', status='Open - contract written; reference store passes; no Engine implementation',
           evidence_seen='No Engine code, repository or environment seen; no implementation exists')
CF = [dict(cf_id='CF-44', audit_section='', topic='The independent audit of APG-F67.3; M8 not authorised',
           what_remains_open='The F-74 correction (APG-F67.3) has not been independently audited. F-74, F-73, F-72 and F-67 stay open until independent verification. The '
                             'authorisation of F-67.3 does not accept the release or authorise M8; M8 is not authorised and must not start. EDR-39, EDR-40 and EDR-41 stay open.',
           what_this_package_shows='tools/probe_f673.py; tests/test_f673_approval_integrity.py; tools/run_history_contract.py; tools/run_f673_all.py (small counted groups); '
                                   'tools/f673_mutants.py --batch K/9 --timeout 30; tools/sabotage_f673.py --only ID; tools/run_regression_f673.py --step Rnn.',
           linked_records='F-67; F-72; F-73; F-74; SR-117; SR-118; I-132; EDR-41; CF-40; CF-42; CF-43',
           who_must_act='Auditor: audit APG-F67.3 against the invariants of I-132 and the agreed threat model. Product owner: M8 only under its own authorisation.',
           status='Open - for the auditor')]

if __name__ == '__main__':
    P = sys.argv[1]
    M7.P = P
    M7.add('FINDINGS_REGISTER.csv', 'finding_id', FIND)
    M7.add('STATUS_REGISTER.csv', 'item_id', STATUS)
    M7.add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=i, milestone=M, topic=t, builder_reading=b, blueprint_ref=r, effect_if_wrong=e,
                                                                      status=M7.RETAINED) for i, t, b, r, e in INTERP])
    M7.add('ENGINE_HANDOFF_REGISTER.csv', 'edr_id', [EDR])
    M7.add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', CF)
