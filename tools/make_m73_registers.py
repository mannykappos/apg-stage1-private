#!/usr/bin/env python3
"""Adds the APG-M7.3 rows to the programme tables: finding F-69, status rows SR-103 and SR-104, interpretations I-116 and I-117, the Engine handoff entry EDR-36 and the carried-forward
item CF-35.  Usage: make_m73_registers.py <programme_dir>   (runs AFTER make_m7, make_m71 and make_m72_registers.py).  Idempotent; no existing row is changed.  Nothing here closes a finding
or settles a decision; F-64 to F-68 keep their rows and stay open."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402

OPEN = 'Corrected in APG-M7.3 (builder-implemented); open until independently verified'
AUDIT = 'Independent audit of APG-M7.2 (the audit text was relayed by the product owner; reproduced by the auditor, and again by the builder on the delivered M7.2 package with tools/probe_m72_insert_race.py)'
FIND = [
    dict(finding_id='F-69', raised_by=AUDIT, milestone='M7.3', title='A record created during a checked act was caught only by a check after the commit; the act could be committed on sources that had already changed',
         description='M7.2 held existing records at their revisions in the commit, but the record store could not hold a record as absent or a query as unchanged. A new overlapping finding '
                     'created between the check and the commit was caught by a second check after the commit, and the act was reversed: the invalid act had been committed, if only briefly. '
                     'The auditor also created the finding just after that second check returned and the act stood. A further check only shortens the window; it cannot close it.',
         linked_items='apg/ports.py (Guard, RecordStorePort.atomic); apg/reference_impl.py (InMemoryRecordStore guards and lock); apg/tenancy.py (ScopedStore.atomic); apg/rec/lifecycle.py (_commit_checked, source_check); apg/rec/engine.py (current_inputs); apg/contracts/record_store_guard_contract.py; tests/test_rec_m73_insert_race.py; tools/probe_m72_insert_race.py; F-68; I-116; I-117; EDR-36',
         how_it_is_handled_here='The record store contract gains guards in its atomic batch: a record at an exact revision (0 = absent) and a whole query at an exact set of (key, revision). '
                                'The reference store checks them with the writes as one indivisible step, under a lock. The lifecycle commits each checked act with a query guard on every kind its '
                                'check read and a revision guard on every record it read by key, so a record added, changed or removed before the commit fails the commit and nothing is recorded. '
                                'The check after the commit and the reversal are removed.', status=OPEN),
]
STATUS = [
    dict(item_id='SR-103', item='Guards in the record store\'s atomic batch (revision, absence, whole query) and the checked acts committed with them (apg/ports.py, apg/reference_impl.py, apg/tenancy.py, apg/rec/lifecycle.py, apg/rec/engine.py)', milestone='M7.3',
         evidence_ladder_status='Local-tested', evidence='tests/test_rec_m73_insert_race.py; apg/contracts/record_store_guard_contract.py (RG-01 to RG-08); tools/probe_m72_insert_race.py; tools/run_contracts.py and tools/run_faults.py still pass',
         claim_limit=M7.CLAIM + ' The reference store is in memory and single-process; an Engine store must pass the same guard contract (EDR-36).'),
    dict(item_id='SR-104', item='Mutation runs over the corrected apg/rec and over the new store code, and package sabotage checks for M7.3, run fresh by the build', milestone='M7.3',
         evidence_ladder_status='Local-tested', evidence='tools/m7_mutants.py; tools/m73_store_mutants.py; tools/sabotage_m73.py; logs/m73/', claim_limit=M7.CLAIM),
]
INTERP = [
    ('I-116', 'When a checked act takes effect, and what counts as a later change', 'A checked act takes effect at the moment its store batch commits, and only if every guard holds then: the sources are exactly those it was checked against. A record committed before that moment refuses the act and nothing is recorded. A record committed after it is a later change, ordered after the act in the store, and is handled like any later change: the next checked act is refused and the next run ends a submission or approval that no longer matches. This includes a record created after the commit but before the call returns. I-115 no longer applies: there is no check after the commit and no reversal.',
     '10:9; 15:15.8', 'If the product owner wants no overlapping finding to be creatable at all while an act is in progress, detection writes and the acts would need a shared lock or a common guarded record; that changes M5 and is a decision for the product owner.'),
    ('I-117', 'M7.3 changes the shared record store', 'The race could only be closed at the store, so M7.3 changes M2 files: the port contract (apg/ports.py: Guard and the atomic batch), the reference store (apg/reference_impl.py: guards and a lock) and the scoped store (apg/tenancy.py: guards passed on, query filters screened). The change is additive: a batch without guards behaves exactly as before, the 38 M2 contract cases and the 39 faulty implementations give the same results, and every earlier test passes unchanged.',
     '15:15.8; 04:16', 'If the M2 port contract must not change outside an M2 release, the guard contract (EDR-36) would move to its own release and M7.3 would wait for it.'),
]
EDR = dict(edr_id='EDR-36', port='RecordStorePort (guards in atomic batches)', title='Implement and pass the guard contract: revision and absence guards, whole-query guards, all-or-nothing, indivisible for concurrent callers',
           what_apg_needs='RecordStorePort.atomic accepts ports.Guard ops: Guard(\'revision\', kind, key, n) (n = 0: absent) and Guard(\'query\', kind, where, entries). Every guard must hold when the batch commits, together with its writes, as one indivisible step for every concurrent caller; a guard writes nothing and needs no write permission on its kind (EDR-34); a failing guard fails the whole batch with ConflictError. This replaces the M7.2 requests in EDR-35 (identical-payload guards and absence or query guards).',
           why_the_engine_is_needed='The record store is the Engine\'s. APG\'s checked acts (submission, approval, start of work) are safe only if the Engine store honours these guards; the in-memory reference store does, and is not for production.',
           contract_summary='apg/contracts/record_store_guard_contract.py, cases RG-01 to RG-08; run with python3 -I tools/run_guard_contract.py --factory module:attr against an Engine store.',
           contract_test='apg/contracts/record_store_guard_contract.py (the reference store passes all 8; a store that ignores guards, or whose batch is not indivisible, fails it: tests/test_rec_m73_insert_race.py)',
           blueprint_refs='15:15.8; 15:15.11; 10:9; 04:16', capabilities='CAP-02; CAP-30; CAP-31', needed_by_milestones='M9; M12',
           decisions_for_amir='How the Engine store implements guards (for example serialisable transactions, or a conditional write that checks a version per kind and tenant); whether a whole-query guard per kind is affordable at the expected volumes, or the query must be narrowed.', owner='Amir (engine, database, environment)',
           status='Open - contract written; reference store passes; no Engine implementation', evidence_seen='No Engine code, repository or environment seen; no implementation exists')
CF = dict(cf_id='CF-35', audit_section='', topic='Runs the M7.2 audit could not complete',
          what_remains_open='In the M7.2 audit the full mutation run and sabotage case S22 did not finish within the auditor\'s execution limit (S16, S20, S21 and S23 were run and caught); these are incomplete, not passes. The delivered M9.4 ZIP was again not supplied.',
          what_this_package_shows='M7.3 keeps the split commands (tools/run_m73_all.py groups, tools/sabotage_m73.py --only Sxx, tools/m7_mutants.py --only LC, tools/m73_store_mutants.py, under a minute). S22 of M7.2 tested the check after the commit, which M7.3 removes; its place is taken by new cases. The product owner can supply the delivered M9.4, M7, M7.1 and M7.2 ZIPs.',
          linked_records='CF-34; SR-104', who_must_act='Auditor: run the split commands and record which completed; product owner: supply the earlier ZIPs to the auditor', status='Open - for the auditor')

if __name__ == '__main__':
    P = sys.argv[1]
    M7.P = P
    M7.add('FINDINGS_REGISTER.csv', 'finding_id', FIND)
    M7.add('STATUS_REGISTER.csv', 'item_id', STATUS)
    M7.add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=i, milestone='M7.3', topic=t, builder_reading=b, blueprint_ref=r, effect_if_wrong=e, status=M7.RETAINED) for i, t, b, r, e in INTERP])
    M7.add('ENGINE_HANDOFF_REGISTER.csv', 'edr_id', [EDR])
    M7.add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', [CF])
