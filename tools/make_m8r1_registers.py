#!/usr/bin/env python3
"""APG-M8-R1: appends its rows to the programme tables (after make_m8_registers.py).  Programme rows are never edited.
  * F-82 (M8-F7): the defect the independent audit of APG-M8 reproduced: an empty source left earlier records assessable.  Corrected in M8-R1 by the builder; open until audited.
  * SR-126 (what M8-R1 built and how it was checked; Local-tested); I-141 (the builder's reading of "an empty source", for review); CF-51 (the audit of M8-R1), CF-52 (the
    M3 path's own handling of a header-only file, which M8-R1 does not change) and CF-53 (which record types may validly be empty: an owner decision).
Usage: make_m8r1_registers.py <programme_dir>   (runs AFTER make_m8_registers.py).  Idempotent; no existing row is changed.  Nothing here accepts a release, closes a finding or a
gate, or records a result the auditor did not report.  The Engine handoff register is not changed."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402
import make_m8_registers as M8                                 # noqa: E402

M = 'M8-R1'
CLAIM = M8.CLAIM
FIND = [
    dict(finding_id='F-82', milestone=M, raised_by='Independent audit of APG-M8 (relayed by the product owner, 2026-10-20); reproduced by the builder on the delivered APG-M8 ZIP',
         title='M8-F7: an empty source left earlier records assessable',
         description='After a good import of the synthetic AP invoices (187 records), the source file was replaced by its header alone and imported again through AUIF rev13. AUIF '
                     'reported NO_DATA (empty); apg_auif/intake.py batch_checks() did not treat that as a reason, so the import was "applied" with no reason, the 187 earlier '
                     'records stayed, and the gate answered can_assess. An empty or unexpectedly cleared source could therefore leave old financial records eligible for a '
                     'current assessment, against the M8 requirement that AUIF\'s no-data state becomes an honest "cannot assess". No M8 test covered a source that becomes empty.',
         linked_items='tests_m8/test_m8r1_empty_source.py; apg_auif/intake.py (batch_checks); CF-51; I-141',
         how_it_is_handled_here='Corrected in M8-R1: a full read that brings back no record (NO_DATA, or nothing delivered and no other outcome) is refused with SOURCE_EMPTY, '
                                'whether the source was empty from the start or became empty; the gate answers cannot_assess and the assessment returns no figure and no signal; '
                                'records stored earlier stay stored but are never made current by it; a clean import after the source is restored makes the assessment possible '
                                'again; an event poll with no new event is not an empty source.',
         status='Open - corrected by the builder in M8-R1; not accepted until independently audited (CF-51)'),
]
STATUS = [
    dict(item_id='SR-126', milestone=M, evidence_ladder_status='Local-tested',
         item='M8-R1: the empty-source refusal (SOURCE_EMPTY) in the adapter, the declared consequence for Builder Zero tenant zero_two (eight empty record types: cannot assess through AUIF), its tests (initially empty, became empty, the full assessment withdrawn and resumed, event poll, the '
              'batch rule alone), mutants MI-38 to MI-42, sabotage S15, the declared corpus difference F11, and regression against the delivered APG-M8 ZIP',
         evidence='tests_m8/test_m8r1_empty_source.py; tools/m8_mutants.py; tools/sabotage_m8.py; tools/run_regression_m8.py (R10); logs/m8r1/', claim_limit=CLAIM),
]
INTERP = [
    ('I-141', 'What counts as an empty source', 'A full read (sync) of one record type is empty when AUIF reports NO_DATA, or when the read ends with no delivery and no other '
              'outcome (no invalid or ambiguous object, no failure, not refused by the integration state). It is refused with SOURCE_EMPTY like any other integrity reason: '
              'nothing is written, the earlier records stay stored, and the record type cannot be assessed until a later import is applied. A read whose objects were all '
              'invalid or ambiguous keeps its own reason. An event poll that brings no new event is not a full read and is not empty. No record type is declared as validly '
              'empty: no contract approving an empty delivery exists (the audit allows one only if separately approved).',
     'Independent audit of APG-M8 (required correction); M8 authorisation (no fallback assessment)',
     'If some record type may legitimately be empty, the product owner would have to approve that per record type, and the adapter would then accept an empty read for it only.'),
]
CF = [
    dict(cf_id='CF-51', audit_section='', topic='The independent audit of APG-M8-R1',
         what_remains_open='APG-M8-R1 corrects F-82 (M8-F7) and has not been independently audited. APG-M8 itself was not accepted (the audit refused it pending this correction). '
                           'F-76 to F-81, DEV-M8-01 (CF-47) and every open EDR and CF item stay as they were; the construction definitions are PROPOSED. The AUIF correction '
                           'revision (CF-50) was authorised by the product owner on 2026-10-20 and built separately as AUIF rev14 (not yet audited); M8-R1 still depends on AUIF rev13, unmodified.',
         what_this_package_shows='tests_m8/test_m8r1_empty_source.py; tools/run_m8_all.py; tools/m8_mutants.py; tools/sabotage_m8.py; tools/run_regression_m8.py; logs/m8r1/',
         linked_records='F-82; SR-126; I-141; CF-46; CF-52', who_must_act='Auditor: audit APG-M8-R1.', status='Open - for the auditor'),
    dict(cf_id='CF-52', audit_section='', topic='The M3 path\'s handling of a header-only file',
         what_remains_open='On the M3 path (unchanged since APG-F67.4-R2) a header-only file is "a valid empty delivery, recorded" (corpus case F11): the receipt has 0 rows and does '
                           'not stop the assessment. Whether the M3 path can therefore also assess with earlier records after a source becomes empty was not examined or changed: '
                           'M8-R1 is authorised for the AUIF path only. On the AUIF path F11 is now refused (declared difference).',
         what_this_package_shows='apg/ingest/corpus.py (F11); auif_m8/PATH_EQUIVALENCE_DECLARED_DIFFERENCES.json; logs/m8r1/00_declared_differences_before_comparison.txt',
         linked_records='F-82; I-141', who_must_act='Product owner: whether to examine the M3 path under its own authorisation.', status='Open - not examined; outside M8-R1'),
    dict(cf_id='CF-53', audit_section='', topic='Record types that may validly be empty (an approved contract)',
         what_remains_open='Under M8-R1 every empty full read is refused (SOURCE_EMPTY). Builder Zero tenant zero_two has eight header-only record types (credit notes, notices, '
                           'variations, plant hire, PO amendments, supplier quotes, delay events, defects), so zero_two cannot be assessed through AUIF, although M3 can assess it '
                           'and the stored data agree. The audit allows an empty result only under a separately approved contract. None exists. Not foreseen by the builder: found '
                           'by the first M8-R1 run of the path-equivalence test and declared after it (recorded in the declarations file).',
         what_this_package_shows='auif_m8/PATH_EQUIVALENCE_DECLARED_DIFFERENCES.json (source_empty, corrections); tests_m8/test_m8_path_equivalence.py; logs/m8r1/',
         linked_records='F-82; I-141; CF-51; CF-52', who_must_act='Product owner: decide whether, and for which record types and tenants, an empty delivery is valid.',
         status='Open - owner decision'),
]
if __name__ == '__main__':
    P = sys.argv[1]
    M7.P = P
    M7.add('FINDINGS_REGISTER.csv', 'finding_id', FIND)
    M7.add('STATUS_REGISTER.csv', 'item_id', STATUS)
    M7.add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=i, milestone=M, topic=t, builder_reading=b, blueprint_ref=r, effect_if_wrong=e,
                                                                      status=M7.RETAINED) for i, t, b, r, e in INTERP])
    M7.add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', CF)
