#!/usr/bin/env python3
"""APG-M8.1: appends its rows to the programme tables (after make_m8r2_registers.py).  Programme rows are never edited.
  * SR-127 (what M8.1 built and how it was checked; Local-tested); I-142 to I-144 (the builder's readings, for review); CF-54 (the audit of APG-M8.1, on a dependency audited
    with qualifications) and CF-55 (DEV-M8-01 ended; the CF-47 row is not edited).
Usage: make_m81_registers.py <programme_dir>.  Idempotent; no existing row is changed.  Nothing here accepts a release, closes a finding or a gate, approves a definition or
records a result the auditor did not report.  The Engine handoff register is not changed."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402

M = 'M8.1'
AUTH = 'product owner, 2026-10-21: "Authorise M8.1 as written, on AUIF rev14 as audited with its stated qualifications"'
REV14 = 'AUIF rev14 (ZIP SHA-256 d534a6e6541b6d1a58e0389161d08698a1d7ac92ee9ad880a51fcee36497c649)'
CLAIM = ('Builder-run; no independent review of APG-M8.1 has taken place. Synthetic data only (Builder Zero); ' + REV14 + ' unmodified and run on its own reference ports '
         '(memory persistence, reference tenant authority, in-memory secrets, fake clock); no real system, credential, Engine port, Governor wiring or outbound action; not '
         'integrated with the Anchor Engine.')
STATUS = [
    dict(item_id='SR-127', milestone=M, evidence_ladder_status='Local-tested',
         item='M8.1: APG as a module client of ' + REV14 + ' (' + AUTH + '): the packs in the contract form module.apg.<Type>.<attribute> (DEV-M8-01 ended); every composite '
              'natural key declared to AUIF as a composite source identity (a stable canonical id; checked against APG\'s own rule); the rev14 sync report used (refused, '
              'conflict and module-failed records, and whether the read is complete); AUIF\'s EVENT_NOT_APPLIED notices read and checked against the ordering results; '
              'SOURCE_EMPTY kept; the M8 tests that pinned rev13\'s defects replaced by tests that the corrections are used',
         evidence='tests_m8/ (15 test files); tools/run_m8_tests.py; tools/run_m8_all.py; tools/m8_mutants.py; tools/sabotage_m8.py; tools/run_regression_m81.py; logs/m81/', claim_limit=CLAIM),
]
INTERP = [
    ('I-142', 'An in-order event AUIF cannot apply', 'AUIF rev14 tells the module (EVENT_NOT_APPLIED, ordering state IN_ORDER) about an in-order event it has no entity mapping '
              'for. APG records it as outstanding (EVENT_NOT_APPLIED), exactly like an event that waits or needs reconciliation: the assessment cannot proceed while it is '
              'outstanding, and nothing resolves it by itself. The batch is NOT refused, because AUIF never delivers an applied event twice: refusing the batch would lose '
              'the in-order events delivered with it.', 'AUIF rev14 (finding M8-F3 corrected); M8 authorisation (no fallback assessment)',
     'If such events should be ignored, a source event APG cannot read would never stop an assessment; if the batch should be refused, events AUIF applied would be lost.'),
    ('I-143', 'AUIF\'s two reports of an event it did not apply must agree', 'AUIF rev14 reports an unapplied event twice: in the ordering results its caller receives and as a '
              'notice to the module. APG requires every notice to match a result (same event, same ordering state) and every waiting, deferred or '
              'reconciliation-pending result to have its notice. A disagreement is a pending reason (EVENT_NOTICE_MISMATCH): the assessment waits, and what AUIF applied '
              'is kept. An event refused by AUIF\'s input guard has its own error (EVENT_REJECTED) and no notice.', 'AUIF rev14 (fabric._record_decision)',
     'If either channel alone were trusted, a lost or wrong notice could go unnoticed.'),
    ('I-144', 'A blank value in a source identity, single or composite', 'On AUIF rev14 a blank identity value is refused as one record (IDENTITY_MISSING) and the read goes '
              'on; APG refuses the whole batch (as for every integrity reason), so the AUIF path is stricter than M3, which rejects the row. On rev13 a single-field '
              'identity made sync raise and a composite one fell back to a content hash, so M3\'s row rejection was reproduced for composite keys; that difference is '
              'gone (tests_m8/test_m8_definitions.py).', 'AUIF rev14 (findings M8-F2, M8-F6 corrected); I-137 (a sync batch applied whole or not at all)',
     'If row-level tolerance is wanted, APG would have to apply part of a batch, which I-137 rules out.'),
]
CF = [
    dict(cf_id='CF-54', audit_section='', topic='The independent audit of APG-M8.1 (on AUIF rev14 as audited with its qualifications)',
         what_remains_open='APG-M8.1 has not been independently audited. Its dependency, AUIF rev14, was audited with no defect found but with stated qualifications '
                           '(AD-15 to AD-20): the full fresh-ZIP verifier did not complete in one run, the real-Governor extension tests were not repeated, only the '
                           'revision-specific mutants were rerun, and Python 3.12 was not reproduced. The product owner authorised building on it as audited. CF-53, CF-52 and '
                           'every open EDR and CF item stay open; the construction definitions are PROPOSED.',
         what_this_package_shows='tools/run_regression_m81.py; tools/run_m8_all.py; tools/run_m8_tests.py; tools/m8_mutants.py; tools/sabotage_m8.py; logs/m81/',
         linked_records='SR-127; I-142 to I-144; CF-55; AD-15 to AD-20', who_must_act='Auditor: audit APG-M8.1.', status='Open - for the auditor'),
    dict(cf_id='CF-55', audit_section='', topic='DEV-M8-01 ended (outcome of CF-47)',
         what_remains_open='APG-M8.1 writes every FIELD mapping in the contract form module.apg.<Type>.<attribute>, which AUIF rev14 reads correctly (F-76, AD-15). AUIF '
                           'rev14 itself refuses the old deviation form when a pack is registered, and APG\'s own form check refuses it too. The CF-47 row is not edited '
                           '(append-only); this row records its outcome. Not accepted until APG-M8.1 is audited (CF-54).',
         what_this_package_shows='apg_auif/pack.py; auif_m8/packs/; tests_m8/test_m8_dev01.py', linked_records='CF-47; F-76; AD-15; CF-54',
         who_must_act='Auditor: audit APG-M8.1.', status='Recorded - DEV-M8-01 ended in APG-M8.1 (builder); not accepted until audited'),
]
if __name__ == '__main__':
    M7.P = sys.argv[1]
    M7.add('STATUS_REGISTER.csv', 'item_id', STATUS)
    M7.add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=i, milestone=M, topic=t, builder_reading=b, blueprint_ref=r, effect_if_wrong=e,
                                                                      status=M7.RETAINED) for i, t, b, r, e in INTERP])
    M7.add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', CF)
