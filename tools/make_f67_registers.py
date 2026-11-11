#!/usr/bin/env python3
"""Correction release APG-F67 (finding F-67): appends its rows to the programme tables.  Programme rows are never edited.
  * The F-67 row of the findings register keeps its M7.1 text ("Open - not corrected"); the correction is recorded in status row SR-111, and that reading is I-129.  F-67
    stays open until the independent auditor verifies the correction.
  * SR-111 (the correction) and SR-112 (its mutation run and sabotage cases); I-128 (what counts as an approval now, and its limit); EDR-39 (what the Engine must restrict);
    CF-40 (the F-67 audit is outstanding; M8 is not started).
  * AD-03 in the audit disposition register: the auditor's completed MIE-1.1 mutation audit (relayed with the audit of MIE-1.1-R1), with the auditor's timeout qualification.
Usage: make_f67_registers.py <programme_dir>   (runs AFTER make_mie1_1r1_registers.py).  Idempotent; no existing row is changed.  Nothing here accepts a release, closes a
finding or a gate, resolves a blocker or records a result the auditor did not report."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402
import make_mie1_1r1_registers as R1                           # noqa: E402

M = 'F-67'
CLAIM = ('Builder-run; no independent review has taken place. The demonstration policies are synthetic, builder-chosen proposals approved in the demonstrations by a synthetic '
         'owner (synthetic.policy_owner); no real owner has approved any policy. Nothing is integrated with the Anchor Engine.')
STATUS = [
    dict(item_id='SR-111', milestone=M, evidence_ladder_status='Local-tested',
         item='The APG-F67 correction of F-67: the financial policy, the detection policy, the procurement policy and the specification register take the provenance pattern of '
              'F-66. A version is proposed by the person storing it, without approvals; an approval is recorded only by approve_policy or approve_spec from the approver\'s own '
              'verified context (a person holding the owner role, not the proposer, once), with an audit event; a run counts an approval only when the audit log confirms it, '
              'and pins the confirmed approvers in its parameters.',
         evidence='apg/policy_approval.py; apg/fin/policy.py; apg/det/policy.py; apg/mkt/policy.py; tests/test_f67_policy_approval.py (12 tests; every one fails or errors on the '
                  'delivered MIE-1.1-R1 code); tools/probe_f67.py (17 cases with one control: 16 defects present on MIE-1.1-R1 and the control fails there; 0 here); '
                  'programme/CHANGE_RECORD_APG-F67.md', claim_limit=CLAIM),
    dict(item_id='SR-112', milestone=M, evidence_ladder_status='Local-tested',
         item='The mutation run over the F-67 correction and the F-67 sabotage cases',
         evidence='tools/f67_mutants.py; tools/sabotage_f67.py; tools/run_regression_f67.py; logs/f67/', claim_limit=CLAIM),
]
INTERP = [
    ('I-128', 'What counts as an approval of a financial, detection or procurement policy, or of the specification register',
     'An approval counts only when (1) the stored version lists it, by a person holding the owner role who is not the proposer, and (2) the tenant\'s audit log holds the event '
     '<kind>.approved for that kind and version, outcome ok, written under that person\'s own verified human context, naming that person as the approver. A calculation, '
     'detection or procurement run reads the confirmations once, when it gathers its inputs, and pins them in its parameters (approvals_confirmed), so a replay gives the same '
     'answer without reading the log. An approval is a new revision of the version; a run that pinned the earlier revision keeps showing the policy as unapproved. The '
     'demonstration and test policies are proposals approved in person by a synthetic owner (synthetic.policy_owner, holding all four owner roles). LIMIT: the reference audit '
     'events carry no roles, and APG cannot stop code outside these functions from writing the store or the audit log; a person without the owner role who writes BOTH a record '
     'with an approval in their own name AND a matching audit event directly would be counted. Closing that is the Engine\'s (EDR-39).',
     'F-66 (M7.1, I-113 pattern); EDR-34', 'If an approval should also be counted from evidence outside the audit log (for example a signed approval record), the confirmation '
     'source changes; the stored records and the runs\' pinned parameters stay as they are.'),
    ('I-129', 'How the F-67 correction is recorded', 'Programme rows are append-only and are never edited, so the F-67 row of the findings register keeps its M7.1 text ("Open - '
              'not corrected"). The correction is recorded in status row SR-111 and in programme/CHANGE_RECORD_APG-F67.md; F-67 is corrected by the builder and stays open '
              'until the independent auditor verifies it, when the disposition is recorded in programme/AUDIT_DISPOSITION_REGISTER.csv (I-127).',
     'Programme conventions (M0); I-127', 'If the product owner prefers the findings row itself to carry the correction, the append-only rule would need an explicit exception.'),
]
EDR = dict(edr_id='EDR-39', port='RecordKindWriteGuard and AuditLogPort (policy records)',
           title='Policy record kinds writable only through their APG functions; approval events only by approve; audit events carrying the verified roles',
           what_apg_needs='The financial policy (fin_policy), detection policy (det_policy), procurement policy (mkt_policy) and specification register (mkt_spec) must be '
                          'writable only through store_policy / store_spec and approve_policy / approve_spec, and the audit events fin_policy.approved, det_policy.approved, '
                          'mkt_policy.approved and mkt_spec.approved must be writable only by approve. Audit events should carry the verified actor\'s roles, so a confirmation '
                          'can also check the role. This extends EDR-34 (the recommendation kinds) to the policy kinds.',
           why_the_engine_is_needed='The record store and the audit log are the Engine\'s. In APG\'s in-memory reference, any authenticated caller may write any kind and any event, '
                                    'so APG can only check what it reads (I-128 states the limit that remains).',
           contract_summary='apg/policy_approval.py (store, approve, confirmed); tests/test_f67_policy_approval.py', contract_test='tests/test_f67_policy_approval.py',
           blueprint_refs='EDR-34; F-66; F-67', capabilities='', needed_by_milestones='Any use of a policy approval outside tests',
           decisions_for_amir='How the Engine restricts writes by record kind and audit event type; whether audit events carry roles.',
           owner='Amir (engine, database, environment)', status='Open - requested; no Engine implementation',
           evidence_seen='No Engine code, repository or environment seen; no implementation exists')
CF = [
    dict(cf_id='CF-40', audit_section='', topic='The independent audit of the F-67 correction; M8 not started',
         what_remains_open='The F-67 correction (APG-F67) has not been independently audited. F-67 stays open until then. M8 is not started: it needs its own authorisation '
                           'after this audit. The other gates stay open (CF-36 to CF-39; EDR-36 to EDR-39).',
         what_this_package_shows='tools/probe_f67.py, tests/test_f67_policy_approval.py, tools/run_regression_f67.py, tools/f67_mutants.py and tools/sabotage_f67.py, each in '
                                 'short commands (RUN_COMMANDS.txt).',
         linked_records='F-67; SR-111; SR-112; I-128; EDR-39', who_must_act='Auditor: audit APG-F67. Product owner: authorise M8 separately.',
         status='Open - for the auditor'),
]
AD3 = dict(disposition_id='AD-03', finding_id='SR-110 (the MIE-1.1 mutation run; not a finding)', auditor_reference='Audit of APG-MIE-1.1-R1, mutation slices',
           release_audited='APG-MIE-1.1',
           audit_relayed='Independent audit of APG-MIE-1.1-R1 (ZIP SHA-256 6afe8b6116cc46cd1db3161a80bc91bf4bb97b847fcdfa1fa4c2967bf17f1185), which completed the MIE-1.1 '
                         'mutation audit; relayed by the product owner on 2026-10-20',
           disposition='The full MIE-1.1 mutation run independently completed, by slices, with a qualification (below)',
           what_the_auditor_reproduced='All seven slices of tools/mie11_mutants.py: CA 31 of 31 killed; VA 26, 25 killed, 1 documented equivalent; PK 163 of 163; OB 56 of 56; '
                                       'SG 129 of 129; TM 71, 69 killed, 2 documented equivalents; EN 148 of 148. Total 624 mutants, 621 killed, 3 documented equivalents, '
                                       '0 survivors, matching the builder-reported result.',
           what_is_not_independently_verified='QUALIFICATION: the original EN command exceeded the auditor\'s execution limit, so the auditor reran the slices in an isolated '
                                              'extraction with a 30-second per-mutant test timeout instead of the tool\'s 300 seconds. The result is therefore not an identical '
                                              'rerun under the original timeout setting. The full 70-case sabotage run and the whole-suite command R12 remain as recorded in '
                                              'AD-01 and AD-02.',
           what_this_does_not_mean=R1.COMMON_DOES_NOT, recorded_in='APG-F67')

if __name__ == '__main__':
    P = sys.argv[1]
    M7.P = P
    M7.add('STATUS_REGISTER.csv', 'item_id', STATUS)
    M7.add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=i, milestone=M, topic=t, builder_reading=b, blueprint_ref=r, effect_if_wrong=e,
                                                                      status=M7.RETAINED) for i, t, b, r, e in INTERP])
    M7.add('ENGINE_HANDOFF_REGISTER.csv', 'edr_id', [EDR])
    M7.add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', CF)
    M7.add(R1.DISP_FILE, 'disposition_id', [AD3])
