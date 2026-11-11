#!/usr/bin/env python3
"""Adds the APG-M7.2 rows to the programme tables: finding F-68, status rows SR-101 and SR-102, interpretations I-114 and I-115, the Engine handoff entry EDR-35 and the carried-forward
item CF-34.  Usage: make_m72_registers.py <programme_dir>   (runs AFTER make_m7_registers.py and make_m71_registers.py).  Idempotent; no existing row is changed.  Nothing here closes a finding
or settles a decision; F-64 and F-65 keep their M7.1 rows and stay open."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402

OPEN = 'Corrected in APG-M7.2 (builder-implemented); open until independently verified'
AUDIT = 'Independent audit of APG-M7.1 (the audit text was relayed by the product owner; reproduced by the auditor, and again by the builder on the delivered M7.1 package with tools/probe_m71_race.py)'
FIND = [
    dict(finding_id='F-68', raised_by=AUDIT, milestone='M7.2', title='A source change between the freshness check and the write of the recommendation was not seen (time-of-check/time-of-use race)',
         description='M7.1 checked that the sources were current and then wrote the recommendation in a separate store operation. A change that landed between the two (inserted deterministically by '
                     'the auditor: the finding dismissed right after the check) was not seen, and the submission was recorded although its finding had already been dismissed. The expected-revision '
                     'check covered the recommendation record only, not its sources. The same held at approval and at the start of work.',
         linked_items='apg/rec/lifecycle.py (_commit_checked, _guards, source_check); apg/rec/engine.py (current_inputs); tests/test_rec_m72_race.py; tools/probe_m71_race.py; F-64; F-65; I-114; I-115; EDR-35',
         how_it_is_handled_here='The act and a guard on every stored record the check read are written in ONE atomic store batch. A guard holds a record at the revision the check saw and writes '
                                'nothing; if any of them changed, the whole batch fails, nothing is recorded and the act is refused (SOURCE_CHANGED, or CONCURRENT_CHANGE when the sources still '
                                'match). A record that did not exist when the check ran cannot be guarded through the store contract: the check runs again once the act is recorded and, if it now '
                                'fails, the act is reversed at once, audited and refused (I-115).', status=OPEN),
]
STATUS = [
    dict(item_id='SR-101', item='The source check and the act commit together (apg/rec/lifecycle.py _commit_checked): every record the check read is held at its revision in the same atomic store batch as the recommendation write; records created during the act reverse it', milestone='M7.2',
         evidence_ladder_status='Local-tested', evidence='tests/test_rec_m72_race.py; tools/probe_m71_race.py', claim_limit=M7.CLAIM + ' Tested by inserting the competing change deterministically; the reference store is single-process (EDR-35).'),
    dict(item_id='SR-102', item='Mutation run over the corrected apg/rec and package sabotage checks for M7.2, run fresh by the build', milestone='M7.2',
         evidence_ladder_status='Local-tested', evidence='tools/m7_mutants.py; tools/sabotage_m72.py; logs/m72/', claim_limit=M7.CLAIM),
]
INTERP = [
    ('I-114', 'What a concurrent change refuses', 'Every stored record the check read is held, not only the ones pinned for this recommendation: the recomputation reads every finding and every set of recommendation inputs in the tenant, and any of them can change its result. So a change anywhere in those records during the act refuses it. If the sources of this recommendation still match, the refusal is CONCURRENT_CHANGE and trying again is enough; otherwise it is SOURCE_CHANGED and the engine must run again.',
     '10:9; 15:15.8', 'If refusals from unrelated concurrent changes are too frequent in practice, the guard could be narrowed to the records the recomputation of this recommendation depends on.'),
    ('I-115', 'A record created during the act', 'The store contract can hold an existing record at a revision but cannot hold a record as absent, or a query as unchanged, without writing. A record created between the check and the write (a new overlapping finding, say) is therefore caught by running the check again once the act is recorded; if it now fails, the act is reversed at once with an audited, append-only reversal, and refused. For that moment the stored record shows the act. Every act that could follow from it (approval after a submission, the start of work after an approval) is itself source-checked and refused.',
     '10:9; 15:15.8', 'If even a reversed, momentary record of the act is not acceptable, the Engine store must provide absence or query guards, or serialisable transactions (EDR-35).'),
]
EDR = dict(edr_id='EDR-35', port='RecordStorePort (conditional commit)', title='Read guards in an atomic batch: hold a record at a revision, hold a record as absent, hold a query as unchanged',
           what_apg_needs='APG-M7.2 commits a checked act together with a guard on every record its check read. With the present contract a guard is a write of the identical payload at the expected revision, which appends nothing. A real store must (1) keep that rule, or offer an explicit guard op that asserts a revision and writes nothing, and allow it on record kinds the caller may not write (EDR-34); (2) offer guards that a record is still absent and that a query still returns the same set, or serialisable transactions; (3) make the batch atomic against concurrent callers, as EDR-02 already requires.',
           why_the_engine_is_needed='The record store is the Engine\'s. The reference in-memory store is single-process and holds no lock, and it cannot hold absence or a query, so APG-M7.2 catches records created during an act by checking again and reversing (I-115).',
           contract_summary='To be agreed: guard ops in atomic batches (revision, absence, query), with conflicts failing the whole batch; atomicity under concurrent callers.',
           contract_test='tests/test_rec_m72_race.py (TestTheGuardItself.test_the_store_rules_the_guard_relies_on) pins the rule APG relies on for the reference store; none exists for an Engine store.',
           blueprint_refs='15:15.8; 15:15.11; 10:9', capabilities='CAP-30; CAP-31', needed_by_milestones='M9; M12',
           decisions_for_amir='Whether the Engine store offers conditional commits with read guards, absence and query guards, or serialisable transactions.', owner='Amir (engine, database, environment)',
           status='Open - described only', evidence_seen='No Engine code, repository or environment seen; no implementation exists')
CF = dict(cf_id='CF-34', audit_section='', topic='Runs the M7.1 audit could not complete',
          what_remains_open='In the M7.1 audit the full sabotage suite was incomplete (the new cases S16 to S19 were run and caught) and the full mutation run was not independently completed; these are incomplete, not passes. The delivered M9.4 ZIP was again not supplied, so the M9.4 manifest inside the package could not be compared with the real archive.',
          what_this_package_shows='M7.2 keeps the split commands: tools/run_m72_all.py (the whole suite in ten counted groups), tools/sabotage_m72.py --only Sxx (one case at a time), and tools/m7_mutants.py --only LC --jobs 2 (one module at a time). The product owner can supply the delivered M9.4, M7 and M7.1 ZIPs.',
          linked_records='CF-33; SR-102', who_must_act='Auditor: run the split commands and record which completed; product owner: supply the M9.4, M7 and M7.1 ZIPs to the auditor', status='Open - for the auditor')

if __name__ == '__main__':
    P = sys.argv[1]
    M7.P = P
    M7.add('FINDINGS_REGISTER.csv', 'finding_id', FIND)
    M7.add('STATUS_REGISTER.csv', 'item_id', STATUS)
    M7.add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=i, milestone='M7.2', topic=t, builder_reading=b, blueprint_ref=r, effect_if_wrong=e, status=M7.RETAINED) for i, t, b, r, e in INTERP])
    M7.add('ENGINE_HANDOFF_REGISTER.csv', 'edr_id', [EDR])
    M7.add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', [CF])
