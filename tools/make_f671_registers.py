#!/usr/bin/env python3
"""Correction release APG-F67.1 (finding F-72, from the independent audit of APG-F67): appends its rows to the programme tables.  Programme rows are never edited.
  * F-72: an approval stuck after an audit-write failure (all five policy records, including the APG-M7.1 recommendation policy).
  * SR-113 (the correction) and SR-114 (the small audit groups, the mutation batches and the sabotage cases); I-130 (the recovery rule); EDR-40 (the record and its approval
    event written atomically, alongside EDR-39).
  * CF-41: the product owner's decision of 2026-10-20 on APG-F67: it is recorded as started WITHOUT the required explicit authorisation, and is NOT retroactively ratified.
  * CF-42: the audit of APG-F67.1 is outstanding; M8 is not authorised.
Usage: make_f671_registers.py <programme_dir>   (runs AFTER make_f67_registers.py).  Idempotent; no existing row is changed.  Nothing here accepts a release, closes a finding
or a gate, ratifies a deviation or records a result the auditor did not report."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402

M = 'F-67.1'
OPEN = 'Corrected in APG-F67.1 (builder-implemented); open until independently verified'
CLAIM = ('Builder-run; no independent review has taken place. The audit failures in the tests are simulated in APG\'s in-memory reference; nothing is integrated with the Anchor '
         'Engine, whose store and audit log decide whether a record and its event can be written together (EDR-40).')
FIND = [dict(finding_id='F-72', milestone=M,
             raised_by='Independent audit of APG-F67 (relayed by the product owner on 2026-10-20; reproduced by the auditor, and again by the builder on the delivered F67 package '
                       'with tools/probe_f671.py)',
             title='An approval became stuck when the audit write failed after the policy record was updated',
             description='approve wrote the approved policy revision and then the confirming audit event. When the audit write failed in between, the policy listed the approval, '
                         'the log confirmed nobody, so the approval was rightly not counted (fail-closed), but the owner\'s retry was refused as "already approved": the policy '
                         'stayed unapproved with no supported way on. The failure surfaced as the raw audit exception, without saying the approval was recorded but not confirmed. '
                         'The builder found the same order in the recommendation policy of APG-M7.1 (F-66), so all five policy records were affected: financial, detection, '
                         'procurement, the specification register and recommendations.',
             linked_items='apg/policy_approval.py (approve, _confirm, status); apg/rec/policy.py (approve_policy, _confirm, approval_status); approval_status in apg/fin, det, mkt '
                          'policy; tests/test_f671_approval_recovery.py; tools/probe_f671.py; I-130; EDR-40',
             how_it_is_handled_here='A failed confirming write raises ApprovalNotConfirmed (also the record\'s own error class) saying the approval is recorded but NOT CONFIRMED and '
                                    'does not count. The same person, with the same identity and role checks, may call approve again: if the policy lists their approval and the '
                                    'log does not confirm it, only the missing confirming event is written, under their own context. Nobody else can complete it. If the event '
                                    'was in fact written although the sink reported an error, the approval is reported as confirmed and is not repeated. approval_status shows, '
                                    'per version, what is recorded, confirmed, and recorded but not confirmed.',
             status=OPEN)]
STATUS = [
    dict(item_id='SR-113', milestone=M, evidence_ladder_status='Local-tested',
         item='The APG-F67.1 correction of F-72 for all five policy records: a clear recorded-but-not-confirmed failure, completion by the same approver only, no double counting',
         evidence='tests/test_f671_approval_recovery.py (11 tests over the five records; every one fails or errors on the delivered APG-F67 code); tools/probe_f671.py (21 cases with '
                  'one control: 10 defects present on APG-F67, 0 here); programme/CHANGE_RECORD_APG-F67.1.md', claim_limit=CLAIM),
    dict(item_id='SR-114', milestone=M, evidence_ladder_status='Local-tested',
         item='Independently auditable runs: the whole suite in small counted groups, the mutation run in fixed batches with a configurable per-mutant timeout, and the F-67.1 '
              'sabotage cases one at a time; the whole suite also stays runnable as one command',
         evidence='tools/run_f671_all.py; tools/run_test_files.py; tools/f671_mutants.py (--batch K/N, --timeout); tools/sabotage_f671.py; tools/run_regression_f671.py; logs/f671/',
         claim_limit=CLAIM),
]
INTERP = [('I-130', 'Completing an approval whose confirming audit write failed',
           'An approval counts only when the policy lists it AND the audit log confirms it (I-128). If the confirming write fails, the approval is recorded but not confirmed: it '
           'does not count, and approve raises ApprovalNotConfirmed. Only the person the policy lists can complete it, by calling approve again from their own verified context '
           'while holding the owner role (a human, not the proposer): approve then writes only the confirming event, naming that person, and changes no record. An entry in '
           'their name that approve did not write (another role or kind) is refused. A second person approving adds and confirms their own approval only. If the sink raised '
           'but the event is in the log, the approval is confirmed and nothing is repeated. A run made while the approval was unconfirmed pinned no confirmation and stays '
           'unapproved on replay. The recommendation policy follows the same rule with its own event type (rec.policy_approved).',
           'F-66; F-67; I-128; EDR-39; EDR-40', 'If the product owner prefers an unconfirmed approval to be withdrawn and re-approved rather than completed, approve would remove '
           'the entry (a new revision) instead of writing the event; the tests of completion would change.')]
EDR = dict(edr_id='EDR-40', port='RecordStorePort and AuditLogPort (one atomic write)',
           title='Write a policy approval and its confirming audit event in one atomic step',
           what_apg_needs='For the five policy kinds (fin_policy, det_policy, mkt_policy, mkt_spec, rec_policy), the approved revision and its approval event (<kind>.approved, '
                          'rec.policy_approved) should be written together or not at all. Until then APG fails closed: an approval whose event is missing does not count, the '
                          'error says so, and the same approver can complete it (I-130). This sits alongside EDR-39 (who may write these kinds and events).',
           why_the_engine_is_needed='The record store and the audit log are the Engine\'s, and are separate ports in APG\'s reference; APG cannot make two ports atomic.',
           contract_summary='apg/policy_approval.py (approve, _confirm); apg/rec/policy.py (approve_policy, _confirm); tests/test_f671_approval_recovery.py',
           contract_test='tests/test_f671_approval_recovery.py', blueprint_refs='EDR-34; EDR-39; F-72', capabilities='', needed_by_milestones='Any use of a policy approval outside tests',
           decisions_for_amir='Whether the Engine writes the record and the audit event in one transaction, or offers an outbox or similar so the event follows the record reliably.',
           owner='Amir (engine, database, environment)', status='Open - requested; no Engine implementation',
           evidence_seen='No Engine code, repository or environment seen; no implementation exists')
CF = [
    dict(cf_id='CF-41', audit_section='', topic='Governance deviation: APG-F67 was started without the required explicit authorisation (DEV-F67-01)',
         what_remains_open='The audit of APG-MIE-1.1-R1 said the F-67 correction release needed the product owner\'s explicit authorisation. The builder started APG-F67 when the '
                           'product owner relayed that audit, without the explicit authorisation, and disclosed this in the APG-F67 change record and readme. On 2026-10-20 the '
                           'product owner decided: record APG-F67 as started without explicit authorisation; do not ratify it retroactively. APG-F67.1 was then explicitly '
                           'authorised ("Authorise F-67.1 correction release").',
         what_this_package_shows='The APG-F67 ZIP (17badf419b26753caaa7a20592322738d6eee9b4e1be5b940f4453629bbaa958) and its records are unchanged; the deviation is recorded '
                                 'here, not waived and not rewritten as authorised. APG-F67 stays unaccepted until independent verification (CF-40).',
         linked_records='CF-40; CF-42; F-67; F-72', who_must_act='None further: recorded as the product owner decided',
         status='Recorded - deviation, not ratified (product owner decision 2026-10-20)'),
    dict(cf_id='CF-42', audit_section='', topic='The independent audit of APG-F67.1; M8 not authorised',
         what_remains_open='The F-72 correction (APG-F67.1) has not been independently audited; F-72 stays open until then. The auditor could not complete the whole suite or all '
                           'F-67 mutants within the execution limits in the APG-F67 audit (CF-40); those runs are now in small groups and batches. M8 is not authorised and '
                           'must not start.',
         what_this_package_shows='tools/run_f671_all.py (small counted groups); tools/f671_mutants.py --batch K/N --timeout 30; tools/sabotage_f671.py --only ID; '
                                 'tools/run_regression_f671.py; tools/probe_f671.py; tests/test_f671_approval_recovery.py.',
         linked_records='F-72; SR-113; SR-114; I-130; EDR-40; CF-40', who_must_act='Auditor: audit APG-F67.1. Product owner: M8 only under its own authorisation.',
         status='Open - for the auditor'),
]

if __name__ == '__main__':
    P = sys.argv[1]
    M7.P = P
    M7.add('FINDINGS_REGISTER.csv', 'finding_id', FIND)
    M7.add('STATUS_REGISTER.csv', 'item_id', STATUS)
    M7.add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=i, milestone=M, topic=t, builder_reading=b, blueprint_ref=r, effect_if_wrong=e,
                                                                      status=M7.RETAINED) for i, t, b, r, e in INTERP])
    M7.add('ENGINE_HANDOFF_REGISTER.csv', 'edr_id', [EDR])
    M7.add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', CF)
