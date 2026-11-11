#!/usr/bin/env python3
"""Adds the APG-MIE-1.1 rows to the programme tables: findings F-70 and F-71 (the auditor's F-MIE1-01 and F-MIE1-02), status rows SR-109 and SR-110, interpretations I-125
and I-126, the Engine handoff entry EDR-38, and the carried-forward items CF-38 (the development deviation from the MIE1_SPEC v0.3 stop condition) and CF-39 (the runs the
MIE-1 audit did not complete).  Usage: make_mie1_1_registers.py <programme_dir>   (runs AFTER make_mie1_registers.py).  Idempotent; no existing row is changed.  Nothing here
closes a finding, resolves a blocker or settles a decision."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402

M = 'MIE-1.1'
OPEN = 'Corrected in APG-MIE-1.1 (builder-implemented); open until independently verified'
AUDIT = 'Independent audit of APG-MIE-1 (the audit text was relayed by the product owner; reproduced by the auditor, and again by the builder on the delivered MIE-1 package with tools/probe_mie1_audit_findings.py)'
CLAIM = ('Builder-run; no independent review has taken place. Every owner value in the tests is a TEST-ONLY fixture value; nothing is integrated with the Anchor Engine and no APG '
         'finding or recommendation consumes the core.')
FIND = [
    dict(finding_id='F-70', raised_by=AUDIT + ' - auditor reference F-MIE1-01', milestone=M,
         title='An unexpected exception from a store at the commit escaped the core, after an ACCEPTED event and with no FAILED event',
         description='Engine._run caught StoreFailure at the commit but no other exception. A store whose put raised RuntimeError during register_pack made a raw RuntimeError '
                     'escape instead of INTERNAL_ERROR_FAIL_CLOSED, after the ACCEPTED event had been written, with no FAILED event. The builder found the same class at every '
                     'committing operation, for an audit sink raising an unexpected exception (it escaped raw), and for a store failing part-way through a batch of observations '
                     '(the items before the failure stayed stored).',
         linked_items='mie/core/engine.py (_run, _append, submit_observations); mie/core/ports.py (ObservationStorePort.append_batch); mie/core/reference.py (RefObservations.append_batch); '
                      'tests/test_mie_core_m11_corrections.py; tools/probe_mie1_audit_findings.py; I-126; EDR-38',
         how_it_is_handled_here='Any exception at the commit other than StoreFailure is INTERNAL_ERROR_FAIL_CLOSED, with one attempted FAILED event; no result is returned. An audit sink '
                                'that fails in any way is treated as unavailable (AUDIT_UNAVAILABLE, no state change). The observations of a batch are written in one store call that is '
                                'all or nothing (ObservationStorePort.append_batch); the reference store stages the batch and applies it in one step.', status=OPEN),
    dict(finding_id='F-71', raised_by=AUDIT + ' - auditor reference F-MIE1-02', milestone=M,
         title='An observation could supersede an observation of another subject or series, and that evidence silently became history',
         description='submit_observations checked only that the observation named in supersedes existed for the tenant. An observation of SYN-ITEM-B could name an observation of '
                     'SYN-ITEM-A; both were accepted and the original was reclassified as history wherever both were in scope, removing evidence from an assessment without a gap. '
                     'The builder reproduced it for another subject in scope, unit, market, value basis, class, source and date.',
         linked_items='mie/core/observations.py (check); mie/core/signals.py (corrects, classify); tests/test_mie_core_m11_corrections.py; tools/probe_mie1_audit_findings.py; I-125',
         how_it_is_handled_here='A correction must be of the same series (subject, market, unit, class, basis), from the same source, for the same as_of date and of the same kind; '
                                'anything else is REJECTED (OBSERVATION_INVALID, field supersedes) and nothing is stored. Classification also ignores an incompatible link, so an '
                                'observation written by any other path cannot hide evidence.', status=OPEN),
]
STATUS = [
    dict(item_id='SR-109', item='The MIE-1.1 corrections of F-70 (commit and audit failures fail closed; observation batches all or nothing) and F-71 (a correction only of the same '
                                'series, source, date and kind)', milestone=M, evidence_ladder_status='Local-tested',
         evidence='tests/test_mie_core_m11_corrections.py (10 tests: 9 fail or error on the delivered MIE-1 code; the tenth guards an edge of the new code found by the mutation run); tools/probe_mie1_audit_findings.py', claim_limit=CLAIM),
    dict(item_id='SR-110', item='The mutation run and the sabotage catalogue rerun on MIE-1.1, with cases for the corrections', milestone=M, evidence_ladder_status='Local-tested',
         evidence='tools/mie11_mutants.py; tools/sabotage_mie1_1.py; logs/mie1_1/', claim_limit=CLAIM),
]
INTERP = [
    ('I-125', 'What a correction may supersede', 'A correction (an observation naming another in supersedes) is valid only for an observation of the same series (subject, market, '
              'unit, observation class, value basis), from the same source, for the same as_of date, and of the same kind (both a LEVEL value or both an EVENT). This reads '
              'section 4.7 ("for one series and as_of") strictly. A changed date or source is a new observation, not a correction.',
     'MIE1_SPEC 4.3, 4.7; MIE-R-12', 'If a correction may change its as_of date or its source, signals.corrects would allow it; the correction tests would change.'),
    ('I-126', 'What fails closed at the commit and at the audit sink', 'An audit sink that raises anything is unavailable: AUDIT_UNAVAILABLE, nothing proceeds. A store that '
              'raises StoreFailure at the commit is STORE_UNAVAILABLE; any other exception there is INTERNAL_ERROR_FAIL_CLOSED. In both, one FAILED event is attempted after the '
              'ACCEPTED event, and no result is returned. Whether the ACCEPTED event and the commit are atomic remains the host\'s (BLK-01).',
     'MIE1_SPEC 9.2; MIE-R-40, MIE-R-61', 'If an unexpected store exception should be reported as STORE_UNAVAILABLE, the engine would map it so; the outcome stays fail-closed.'),
]
EDR = dict(edr_id='EDR-38', port='ObservationStorePort.append_batch (all or nothing)',
           title='Store a batch of observations in one all-or-nothing write, and fail only by raising StoreFailure',
           what_apg_needs='The core now writes the observations of one submit_observations call in one append_batch call. The host store must store every item or none; an '
                          'identifier already held is left as it is; on any failure it raises StoreFailure and leaves nothing of the batch. This adds to EDR-37.',
           why_the_engine_is_needed='Persistence is the Engine\'s. The reference store stages the batch in memory and is not for production.',
           contract_summary='mie/core/ports.py ObservationStorePort.append_batch; tests/test_mie_core_m11_corrections.py test_the_reference_batch_store_contract',
           contract_test='tests/test_mie_core_m11_corrections.py', blueprint_refs='MIE1_SPEC 9.2, 10.2; MIE1_PORTS.csv PT-02', capabilities='',
           needed_by_milestones='Any use of the core outside tests', decisions_for_amir='How the Engine store makes a batch atomic (one transaction per batch).',
           owner='Amir (engine, database, environment)', status='Open - contract written; reference store passes; no Engine implementation',
           evidence_seen='No Engine code, repository or environment seen; no implementation exists')
CF = [
    dict(cf_id='CF-38', audit_section='', topic='Development deviation from the MIE1_SPEC v0.3 stop condition (DEV-MIE-01)',
         what_remains_open='MIE1_SPEC v0.3 (line 6, unchanged in spec/MIE1_SPEC_v0.3/) says no implementation code is written or authorised until the specification has been '
                           'reviewed, the blockers BLK-01 to BLK-03 are cleared, and the product owner separately authorises implementation. The product owner authorised '
                           'development of MIE-1 as code while BLK-01 to BLK-03 are still open. MIE-1 and MIE-1.1 are therefore built under an explicit development deviation; they do '
                           'not claim unconditional conformity with that wording.',
         what_this_package_shows='The specification is not edited and the deviation does not clear any blocker or gate (CF-36, CF-37 stay open). The deviation covers development '
                                 'and builder testing only; release would still need the blockers and gates closed.',
         linked_records='CF-36; CF-37; SR-105 to SR-110', who_must_act='Product owner: confirm the deviation is recorded as intended; auditor: check it is stated wherever conformity is described',
         status='Open - deviation recorded, not a release decision'),
    dict(cf_id='CF-39', audit_section='', topic='Runs the MIE-1 audit could not complete',
         what_remains_open='In the MIE-1 audit the full mutation run and the full 60-case sabotage run were not independently completed (five selected sabotage cases were run and '
                           'caught), and the multi-group commands timed out in the auditor\'s environment; these are incomplete, not passes.',
         what_this_package_shows='MIE-1.1 keeps the split commands: tools/run_mie1_1_all.py groups, tools/sabotage_mie1_1.py --only ID, tools/mie11_mutants.py --only PREFIX.',
         linked_records='CF-35; SR-107; SR-110', who_must_act='Auditor: run the split commands and record which completed', status='Open - for the auditor'),
]

if __name__ == '__main__':
    P = sys.argv[1]
    M7.P = P
    M7.add('FINDINGS_REGISTER.csv', 'finding_id', FIND)
    M7.add('STATUS_REGISTER.csv', 'item_id', STATUS)
    M7.add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=i, milestone=M, topic=t, builder_reading=b, blueprint_ref=r, effect_if_wrong=e, status=M7.RETAINED)
                                                                 for i, t, b, r, e in INTERP])
    M7.add('ENGINE_HANDOFF_REGISTER.csv', 'edr_id', [EDR])
    M7.add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', CF)
