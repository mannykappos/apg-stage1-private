#!/usr/bin/env python3
"""Correction release APG-F67.2 (finding F-73, from the independent audit of APG-F67.1): appends its rows to the programme tables.  Programme rows are never edited.
  * F-73: the F-67.1 recovery path completed a planted approval entry with the correct role and kind (all five policy records).
  * SR-115 (the correction) and SR-116 (its auditable runs); I-131 (replace, never complete; the revision binding; what it supersedes in I-130; the limit that remains).
  * CF-43: the audit of APG-F67.2 is outstanding; F-72 and F-73 stay open until it; M8 is not authorised.
Usage: make_f672_registers.py <programme_dir>   (runs AFTER make_f671_registers.py).  Idempotent; no existing row is changed.  Nothing here accepts a release, closes a finding
or a gate, or records a result the auditor did not report."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402

M = 'F-67.2'
OPEN = 'Corrected in APG-F67.2 (builder-implemented); open until independently verified'
CLAIM = ('Builder-run; no independent review has taken place. Direct writes and audit failures are simulated in APG\'s in-memory reference; nothing is integrated with the Anchor '
         'Engine, which must still restrict direct writes (EDR-39) and write a record and its event atomically (EDR-40).')
FIND = [dict(finding_id='F-73', milestone=M,
             raised_by='Independent audit of APG-F67.1 (relayed by the product owner on 2026-10-20; reproduced by the auditor on all five records, and again by the builder on the '
                       'delivered F67.1 package with tools/probe_f672.py)',
             title='The F-67.1 recovery path completed an approval entry written straight into the store when it had the correct role and kind',
             description='When the policy listed an unconfirmed entry in the caller\'s name, APG-F67.1 approve wrote only the confirming event. It checked the entry\'s role and kind, '
                         'not that approve had written it, so an entry planted directly in the store naming the owner, with the owner role and kind human, was confirmed when the '
                         'owner approved; the F-67.1 tests covered only a planted entry with the wrong role. The confirming event named no record revision, so it could not show which '
                         'entry it confirmed. Reproduced on the financial, detection, procurement, specification-register and recommendation policies.',
             linked_items='apg/policy_approval.py (approve, _confirm, confirmed, added_at); apg/rec/policy.py (approve_policy, _confirm, verified_approvers); '
                          'tests/test_f672_forged_entry.py; tests/test_f671_approval_recovery.py (two tests changed); tools/probe_f672.py; I-131',
             how_it_is_handled_here='approve never completes an entry it finds. If the caller has an entry in their name that the log does not confirm, whoever wrote it, approve '
                                    'writes a revision without it, then a revision with a fresh entry of its own, and the confirming event names that revision. A confirming '
                                    'event counts only if the revision it names is the one that added that person\'s entry (it lists the entry and the revision before does '
                                    'not). A planted entry never counts, and is replaced only when the named person approves in person.',
             status=OPEN)]
STATUS = [
    dict(item_id='SR-115', milestone=M, evidence_ladder_status='Local-tested',
         item='The APG-F67.2 correction of F-73 for all five policy records: replace, never complete, an unconfirmed entry in the approver\'s name; each confirmation bound to the '
              'revision approve wrote, and counted only for the revision that added the entry',
         evidence='tests/test_f672_forged_entry.py (11 tests over the five records; 8 fail or error on the delivered APG-F67.1 code, 3 guard properties F-67.1 already had); '
                  'tests/test_f671_approval_recovery.py (2 tests changed to the new behaviour); tools/probe_f672.py (16 cases with one control: 11 defects present on '
                  'APG-F67.1, 0 here); programme/CHANGE_RECORD_APG-F67.2.md', claim_limit=CLAIM),
    dict(item_id='SR-116', milestone=M, evidence_ladder_status='Local-tested',
         item='Independently auditable runs for APG-F67.2: the whole suite in small counted groups, the mutation run in fixed batches with a configurable timeout, sabotage one case '
              'at a time, regression one step at a time',
         evidence='tools/run_f672_all.py; tools/f672_mutants.py; tools/sabotage_f672.py; tools/run_regression_f672.py; logs/f672/', claim_limit=CLAIM),
]
INTERP = [('I-131', 'Replace, never complete; the revision binding',
           'approve cannot tell an entry it wrote from one written into the store directly with the same fields, so it never completes an entry it finds. When the caller (a person '
           'holding the owner role, not the proposer) has an entry in their name that the log does not confirm, approve writes a revision without it, then a revision with a fresh '
           'entry, and the confirming event names that revision. confirmed (and the recommendation policy\'s verified_approvers) counts an event only when the revision it names '
           'lists that person\'s entry and the revision before it does not. Other approvers\' entries are kept. This supersedes the part of I-130 that refused an entry approve '
           'did not write: refusing it would let anyone able to write the store block the named person\'s approval. LIMIT (as I-128): the named person could still write both a '
           'record revision and a matching event directly; restricting direct writes is the Engine\'s (EDR-39), as is writing a record and its event atomically (EDR-40). The binding '
           'reads the revision before the one an event names; it relies on RecordStorePort.get returning None for revision 0 or any revision outside 1..n, as the reference '
           'store does; an Engine store must keep that (the record-store contract does not yet test it).',
           'F-72; F-73; I-128; I-130; EDR-39; EDR-40', 'If a planted entry should instead block the version until an administrator clears it, approve would refuse it; that '
           'reintroduces a state in which the named person cannot approve, which F-72 removed.')]
CF = [dict(cf_id='CF-43', audit_section='', topic='The independent audit of APG-F67.2; M8 not authorised',
           what_remains_open='The F-73 correction (APG-F67.2) has not been independently audited. F-72 and F-73 stay open until then, and F-67 stays open (CF-40). M8 is not '
                             'authorised and must not start.',
           what_this_package_shows='tools/probe_f672.py; tests/test_f672_forged_entry.py; tools/run_f672_all.py (small counted groups); tools/f672_mutants.py --batch K/8 '
                                   '--timeout 30; tools/sabotage_f672.py --only ID; tools/run_regression_f672.py --step Rnn.',
           linked_records='F-72; F-73; SR-115; SR-116; I-131; CF-40; CF-42', who_must_act='Auditor: audit APG-F67.2. Product owner: M8 only under its own authorisation.',
           status='Open - for the auditor')]

if __name__ == '__main__':
    P = sys.argv[1]
    M7.P = P
    M7.add('FINDINGS_REGISTER.csv', 'finding_id', FIND)
    M7.add('STATUS_REGISTER.csv', 'item_id', STATUS)
    M7.add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=i, milestone=M, topic=t, builder_reading=b, blueprint_ref=r, effect_if_wrong=e,
                                                                      status=M7.RETAINED) for i, t, b, r, e in INTERP])
    M7.add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', CF)
