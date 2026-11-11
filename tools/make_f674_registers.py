#!/usr/bin/env python3
"""Correction release APG-F67.4 (finding F-75, from the independent audit of APG-F67.3): appends its rows to the programme tables.  Programme rows are never edited.
  * F-75: type-changing edits (False -> 0, 1 -> True, 0 -> False) kept an approval, because content was compared with Python equality.
  * SR-119 (the correction) and SR-120 (its auditable runs, including one test file per group); I-133 (what "unchanged" means); CF-45 (the audit of APG-F67.4; M8 not authorised).
Usage: make_f674_registers.py <programme_dir>   (runs AFTER make_f673_registers.py).  Idempotent; no existing row is changed.  Nothing here accepts a release, closes a finding
or a gate, or records a result the auditor did not report."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402

M = 'F-67.4'
OPEN = 'Corrected in APG-F67.4 (builder-implemented); open until independently verified'
CLAIM = ('Builder-run; no independent review has taken place. Direct writes are simulated in APG\'s in-memory reference; nothing is integrated with the Anchor Engine, which '
         'must still restrict direct writes (EDR-39), write a record and its event atomically (EDR-40) and pass the record-store history contract (EDR-41).')
FIND = [dict(finding_id='F-75', milestone=M,
             raised_by='Independent audit of APG-F67.3 (relayed by the product owner on 2026-10-20; reproduced by the auditor on the financial, detection and procurement '
                       'policies, and by the builder on all five records with tools/probe_f674.py)',
             title='A type-changing edit of approved content kept the approval, because "unchanged" was judged by Python equality',
             description='APG-F67.3 compared the approved content of each revision with Python dictionary equality, under which False == 0 and True == 1. A direct write that '
                         'changed an approved value\'s type (False -> 0, 1 -> True, 0 -> False) appended a new revision, yet the confirmation still held and the run still '
                         'counted the approval; the owner could not approve the changed content afresh ("already approved"). The builder found the same loose comparison in the '
                         're-store checks of the shared policy store and of the recommendation policy store: a re-store with True for 1 was treated as the same content (no '
                         'write; with today\'s schemas the schema check refuses such content first).',
             linked_items='apg/policy_approval.py (fingerprint, same, holds, store); apg/rec/policy.py (store_policy); tests/test_f674_type_strict.py; tools/probe_f674.py; I-133',
             how_it_is_handled_here='"Unchanged" means unchanged by the store\'s own canonical, type-preserving fingerprint (canon.digest, the payload hash the store uses): holds '
                                    'compares the approved content and the approver\'s entries by fingerprint, and both re-store checks do the same. Key order alone is not '
                                    'a change; content that cannot be fingerprinted never holds.',
             status=OPEN)]
STATUS = [
    dict(item_id='SR-119', milestone=M, evidence_ladder_status='Local-tested',
         item='The APG-F67.4 correction of F-75 for all five policy records: approved content, approval entries and re-stored versions compared by the canonical fingerprint',
         evidence='tests/test_f674_type_strict.py (9 tests over the five records; 7 fail or error on the delivered APG-F67.3 code, 2 guard behaviour it already had); '
                  'tools/probe_f674.py (16 cases with one control: 15 defects present on APG-F67.3, 0 here); programme/CHANGE_RECORD_APG-F67.4.md', claim_limit=CLAIM),
    dict(item_id='SR-120', milestone=M, evidence_ladder_status='Local-tested',
         item='Finer-grained independent audit runs: one test file per group (117 files with their counts, which add up to the whole suite), the earlier small groups, the '
              'mutation run in fixed batches, sabotage one case at a time, regression one step at a time',
         evidence='tools/run_f674_all.py (--files-list, --file N, --files A-B); tools/f674_mutants.py; tools/sabotage_f674.py; tools/run_regression_f674.py; logs/f674/',
         claim_limit=CLAIM),
]
INTERP = [('I-133', 'What "unchanged" means for approved content and approval entries',
           'Unchanged means unchanged by the store\'s own canonical, type-preserving fingerprint (canon.digest, the payload hash the store uses to tell whether a write changed '
           'anything; RH-04 of the history contract). True and 1, False and 0, and 1 and "1" are different; the order of a record\'s keys is not a difference (the store '
           'appends nothing for it); a list in another order is a difference. holds (I-132) compares the approved content and the approver\'s entries by fingerprint; the '
           're-store checks of the shared policy store and of the recommendation policy compare a re-stored version by fingerprint too. Content that cannot be fingerprinted '
           '(for example a float written directly, which the canonical data rules refuse) never holds. This replaces Python equality wherever I-132 says unchanged.',
           'F-74; F-75; I-132; EDR-41', 'If some type change should not count as a change (for example 1 and true in a field whose schema reads them alike), the comparison '
           'would need a per-field normal form, which would itself need review; the fingerprint is the strict default.')]
CF = [dict(cf_id='CF-45', audit_section='', topic='The independent audit of APG-F67.4; M8 not authorised',
           what_remains_open='The F-75 correction (APG-F67.4) has not been independently audited. F-75, F-74, F-73, F-72 and F-67 stay open until independent verification. M8 '
                             'is not authorised and must not start. EDR-39, EDR-40 and EDR-41 stay open.',
           what_this_package_shows='tools/probe_f674.py; tests/test_f674_type_strict.py; tools/run_f674_all.py --files-list / --file N (one test file per group, each with its '
                                   'count) and the earlier groups; tools/f674_mutants.py --batch K/10 --timeout 30; tools/sabotage_f674.py --only ID; '
                                   'tools/run_regression_f674.py --step Rnn.',
           linked_records='F-67; F-72; F-73; F-74; F-75; SR-119; SR-120; I-133; CF-40; CF-42 to CF-44',
           who_must_act='Auditor: audit APG-F67.4. Product owner: M8 only under its own authorisation.', status='Open - for the auditor')]

if __name__ == '__main__':
    P = sys.argv[1]
    M7.P = P
    M7.add('FINDINGS_REGISTER.csv', 'finding_id', FIND)
    M7.add('STATUS_REGISTER.csv', 'item_id', STATUS)
    M7.add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=i, milestone=M, topic=t, builder_reading=b, blueprint_ref=r, effect_if_wrong=e,
                                                                      status=M7.RETAINED) for i, t, b, r, e in INTERP])
    M7.add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', CF)
