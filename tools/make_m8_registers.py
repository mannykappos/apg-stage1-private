#!/usr/bin/env python3
"""APG-M8: appends its rows to the programme tables.  Programme rows are never edited.
  * Findings F-76 to F-81 (M8-F1 to M8-F6), found while integrating APG with the frozen AUIF rev13 as a module client.  They are defects in the builder's OWN AUIF build
    (rev13), which the authorisation froze for M8, so none was patched here; fixing them needs an authorised AUIF correction revision (CF-50).  They are not Engine work and
    are NOT entered in the Engine handoff register.
  * SR-121 to SR-125 (what M8 built and how it was checked; Local-tested); I-135 to I-140 (the builder's readings, for review); CF-46 to CF-50 (what stays open, including the
    audit of M8, the deviation DEV-M8-01 and the AUIF correction revision).
Usage: make_m8_registers.py <programme_dir>   (runs AFTER make_f674r2_registers.py).  Idempotent; no existing row is changed.  Nothing here accepts a release, closes a finding or
a gate, approves a definition, or records a result the auditor did not report.  The Engine handoff register is not changed: EDR-05, EDR-06, EDR-18, EDR-39, EDR-40, EDR-41 and every other open EDR and CF row stay as they are."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402

M = 'M8'
AUTH = ('product owner, 2026-10-20: "AUTHORISE M8" (APG integration with the frozen AUIF rev13 module interface, synthetic data only), and after the stop report, '
        '"Authorise M8 continuation under DEV-M8-01 as written"')
OPEN_AUIF = ("Open - defect in the builder's own frozen AUIF rev13; not patched in M8 (rev13 is frozen); handled on the APG side as described; the fix needs an authorised "
             "AUIF correction revision (CF-50)")
CLAIM = ('Builder-run; no independent review has taken place. Synthetic data only (Builder Zero); AUIF rev13 unmodified and run on its own reference ports (memory persistence, '
         'reference tenant authority, in-memory secrets, fake clock); no real system, credential, Engine port, Governor wiring or outbound action; not integrated with the Anchor Engine.')
FIND = [
    dict(finding_id='F-76', milestone=M, raised_by='Builder, during M8, in the builder\'s own AUIF rev13 (frozen); reproduced with AUIF alone (its own synthetic module concept), Python 3.12 and 3.13',
         title='M8-F1: AUIF rev13 cannot translate a field into any MODULE-namespace concept',
         description='auif/translation.py line 152 (translate_inbound) takes a field mapping\'s attribute as everything after the FIRST dot of its canonical reference. A module '
                     'concept is named module.<module>.<Type>, so the contract form module.<module>.<Type>.<attribute> yields "<module>.<Type>.<attribute>": every object of a '
                     'MODULE concept is TRANSLATION_INVALID ("unknown attribute", "required attribute missing"). Line 177 (translate_outbound) and auif_onboard/review.py '
                     'line 228 (the accelerator\'s approval check) make the same assumption. rev13\'s tests never map a field into a module concept.',
         linked_items='tests_m8/test_m8_dev01.py (pins the defect and the deviation); DEV-M8-01 (CF-47); CF-50; I-135',
         how_it_is_handled_here='M8 stopped and reported it (stop report, 2026-10-20). The product owner authorised DEV-M8-01: FIELD mappings write "<Type>.<attribute>", which '
                                'rev13 reads correctly; ENTITY mappings and the model keep "module.apg.<Type>". apg_auif/pack.py produces only that form and refuses any '
                                'other (the client refuses a pack in another form before use). AUIF is unmodified.', status=OPEN_AUIF),
    dict(finding_id='F-77', milestone=M, raised_by='Builder, during M8', title='M8-F2: a composite natural key cannot be AUIF\'s source identity',
         description='AUIF identifies a source record by ONE field (identity_fields); with none it falls back to the first 12 hex digits of a hash of the whole record. Five '
                     'Builder Zero record types have composite keys (budget lines, FX rates, cost-to-complete lines, compliance evidence, work output), so their canonical id '
                     'is a content hash that changes whenever any value changes and does not identify the business record across revisions.',
         linked_items='tests_m8/test_m8_findings.py (TestM8F2CompositeIdentity); apg_auif/intake.py (check_delivery); CF-50',
         how_it_is_handled_here='APG keys every record by its full natural key with the M3 rule, keeps AUIF\'s canonical id as lineage only, and checks that the delivered '
                                'identity is exactly the hash AUIF computes (IDENTITY_MISMATCH otherwise). Stated in each affected construction definition.', status=OPEN_AUIF),
    dict(finding_id='F-78', milestone=M, raised_by='Builder, during M8', title='M8-F3: AUIF never tells the module about an event that waits',
         description='auif/fabric.py _record_decision delivers only IN_ORDER events to the module. An event that is QUEUED, DEFERRED, RECONCILIATION_PENDING or '
                     'REJECTED_BY_POLICY reaches only the caller of ingest_events (its results) and AUIF\'s sequencer; a module that does not drive ingestion itself cannot '
                     'know that data is missing.',
         linked_items='tests_m8/test_m8_events.py (TestFindingM8F3); apg_auif/client.py (ingest_events, tick); CF-50',
         how_it_is_handled_here='The APG client reads the ordering results and the sequencer\'s pending list on every call and records the outstanding events; the assessment '
                                'cannot proceed while any is outstanding (EVENTS_WAITING, EVENT_RECONCILIATION_PENDING, EVENT_REJECTED).', status=OPEN_AUIF),
    dict(finding_id='F-79', milestone=M, raised_by='Builder, during M8', title='M8-F4: AUIF\'s BaseModule swallows a handler\'s exception',
         description='auif_ext/module_client/client.py BaseModule._dispatch catches every exception a handler raises and keeps only its type name in handler_errors; AUIF '
                     'counts the delivery as made. A module bug therefore loses data silently unless the module checks handler_errors itself.',
         linked_items='tests_m8/test_m8_findings.py (TestM8F4SwallowedHandlerErrors); tests_m8/test_m8_no_fallback.py (a failure inside the adapter is never silent); CF-50',
         how_it_is_handled_here='Every APG handler catches its own failure and records it (ADAPTER_ERROR): the batch is refused, or an alert stops the assessment; the gate also '
                                'refuses while BaseModule.handler_errors is not empty.', status=OPEN_AUIF),
    dict(finding_id='F-80', milestone=M, raised_by='Builder, during M8', title='M8-F5: AUIF\'s sync report does not say whether the read reached the end',
         description='auif/fabric.py sync stops after max_pages (default 10 pages of 3) and reports pages, delivered, invalid, ambiguous, empty, failed and not_allowed, but '
                     'not whether the source had more: a read cut short looks like a complete one.',
         linked_items='tests_m8/test_m8_findings.py (TestM8F5SyncReportCompleteness); tests_m8/test_m8_no_fallback.py (page limit); CF-50',
         how_it_is_handled_here='The APG client sizes pages so a complete read of the largest file the importer allows always ends before the page limit, and treats reaching the '
                                'limit as incomplete (SYNC_INCOMPLETE); it also checks that AUIF\'s delivered count equals what APG received.', status=OPEN_AUIF),
    dict(finding_id='F-81', milestone=M, raised_by='Builder, during M8', title='M8-F6: AUIF\'s sync raises instead of reporting in two cases',
         description='(a) For an integration that drifted before its first validation (no baseline), IntegrationController.entity_readable reads base["snapshot"] of None and '
                     'raises TypeError. (b) A blank value in the identity field gives an Observation whose source_object.object_id is empty, which AUIF\'s own contract refuses, '
                     'so sync raises ContractViolation part way through a read (earlier rows were already delivered).',
         linked_items='tests_m8/test_m8_findings.py (TestM8F6SyncRaises); tests_m8/test_m8_definitions.py (blank identifier); CF-50',
         how_it_is_handled_here='The APG client catches any exception from AUIF, refuses the batch (AUIF_RAISED) and writes nothing; nothing is retried around it. For (b) the AUIF '
                                'path is therefore stricter than M3, which rejects only the row (declared: corpus case R03).', status=OPEN_AUIF),
]
STATUS = [
    dict(item_id='SR-121', milestone=M, evidence_ladder_status='Local-tested',
         item='APG as an AUIF module client: apg_auif (module on AUIF BaseModule; intake under the unchanged M3 rules with lineage; batches applied whole or not at all; '
              'client on AUIF reference ports, no outbound action); AUIF rev13 carried as its ZIP and verified by hash before every run',
         evidence='tests_m8/test_m8_conformance.py (AUIF ModulePortContract), test_m8_dependency.py, test_m8_boundary.py, test_m8_delivery_rules.py; tools/run_m8_tests.py', claim_limit=CLAIM),
    dict(item_id='SR-122', milestone=M, evidence_ladder_status='Local-tested',
         item='Construction definitions for 26 record types in the MODULE namespace (module.apg.*), status PROPOSED, with the AUIF canonical model (PROPOSED) and 15 '
              'CANDIDATE synthetic translation packs (configuration only) under DEV-M8-01',
         evidence='auif_m8/definitions/; auif_m8/packs/; tools/make_m8_config.py --check; tests_m8/test_m8_definitions.py (a demonstration per definition); test_m8_dev01.py',
         claim_limit=CLAIM + ' The definitions are proposed for review; none is approved or locked.'),
    dict(item_id='SR-123', milestone=M, evidence_ladder_status='Local-tested',
         item='Lineage on every record and "cannot assess" instead of any old, default or partial value (the assessment gate and entry point)',
         evidence='tests_m8/test_m8_lineage.py; test_m8_no_fallback.py; test_m8_events.py; apg_auif/gate.py; apg_auif/assess.py', claim_limit=CLAIM),
    dict(item_id='SR-124', milestone=M, evidence_ladder_status='Local-tested',
         item='Path equivalence: M3 and AUIF paths give the same records, figures, detection outputs, exclusions and assessment status on Builder Zero (both tenants); the M3 '
              'fault corpus through AUIF; every difference declared before the comparison',
         evidence='tests_m8/test_m8_path_equivalence.py; test_m8_corpus.py; auif_m8/PATH_EQUIVALENCE_DECLARED_DIFFERENCES.json; logs/m8/00_declared_differences_before_comparison.txt',
         claim_limit=CLAIM),
    dict(item_id='SR-125', milestone=M, evidence_ladder_status='Local-tested',
         item='M8 verification runs: baselines; every M8 test file and every existing test file as its own group, on Python 3.12 and 3.13; mutation over the adapter in batches; '
              'sabotage one case at a time; regression against APG-F67.4-R2 one step at a time',
         evidence='tools/run_m8_all.py; tools/run_m8_tests.py; tools/m8_mutants.py; tools/sabotage_m8.py; tools/run_regression_m8.py; logs/m8/', claim_limit=CLAIM),
]
INTERP = [
    ('I-135', 'DEV-M8-01: the field-reference form', 'Under DEV-M8-01 (authorised by the product owner) a FIELD mapping\'s canonical_ref is "<Type>.<attribute>", where <Type> is the '
              'last segment of the module concept its ENTITY mapping names; ENTITY mappings and the canonical model keep "module.apg.<Type>". No other form is produced or '
              'accepted. Once a corrected AUIF revision is authorised, built and audited (CF-50), the packs must be regenerated in the contract form under a new authorisation; until then a pack in the '
              'deviation form would be refused by the corrected translator and the assessment would fail closed.', 'F-76; CF-47; CF-50',
     'If the reference form should be something else, only apg_auif/pack.py field_ref and the stored packs change.'),
    ('I-136', 'What stops an assessment ("cannot assess")', 'The gate refuses when an expected integration is not ACTIVE or has no state; a record type has no applied import; '
              'the latest import has a reason (integrity: TRANSLATION_INVALID, AMBIGUOUS, SCHEMA_DRIFT, LINEAGE_*, WRONG_TENANT, MISSING_FIELD, TYPE_MISMATCH, SYNC_*, '
              'AUIF_RAISED, STALE_MANIFEST, PACK_NOT_PINNED, ADAPTER_ERROR; record level: ROW_REJECTED, VALUE_INVALID, STALE_DELIVERY; events: EVENTS_WAITING, '
              'EVENT_RECONCILIATION_PENDING, EVENT_REJECTED); the import was made under an earlier manifest; an alert is newer than the integration\'s imports; or a module '
              'handler failed. The record-level reasons are the builder\'s reading of "partial" and "type-mismatched": a rejected row or an unreadable optional value means a '
              'figure would silently lack or mis-state an input; a stale delivery means source and APG disagree on the current version. Conflicts, duplicates and held '
              'records are NOT reasons: under the existing M3 contract they are exclusions every figure lists.', 'M8 authorisation (no fallback assessment); Section 04',
     'If held records or conflicts should also stop an assessment, Builder Zero itself (which contains them on purpose) could never be assessed; if rejected rows should not, '
     'a figure could be shown without an input the source sent.'),
    ('I-137', 'A sync batch is applied whole or not at all; an event is applied as AUIF applies it', 'A sync (one record type of one integration) is the AUIF counterpart of '
              'one M3 file: any integrity reason means nothing from it is written. AUIF never delivers an applied event twice, so in-order events are written as they '
              'arrive and the events that wait are recorded as outstanding; the assessment cannot proceed until none is.', 'M3 pipeline (one atomic write per file); AUIF sequencer',
     'If events should also be all-or-nothing, an event AUIF has applied would be lost to APG.'),
    ('I-138', 'AUIF\'s VALIDATED mapping state is not an approval', 'AUIF executes only VALIDATED or TRUSTED mappings; in AUIF VALIDATED means "deterministic validation '
              'performed". The M8 packs carry VALIDATED mappings proposed by DETERMINISTIC_TOOL (tools/make_m8_config.py checks each against the APG template), but the '
              'packs are pack_state CANDIDATE and the model they target is PROPOSED: nothing is approved.', 'AUIF translation contract; M8 authorisation (definitions PROPOSED)',
     'If AUIF VALIDATED is read as an approval, the packs would need an owner\'s sign-off before any use; they are synthetic and for tests only.'),
    ('I-139', 'Observed and effective time', 'observed_at is AUIF\'s observation time. effective_at is the record\'s own business date - the first event date its intake rules '
              'name (invoice_date, payment_date, ...) - or null with a stated basis: "none" for a record type that carries no business date (suppliers, projects, '
              'contracts, ...) or "unknown" when the date is blank or unreadable. Nothing is defaulted.', 'M8 authorisation (lineage fields)',
     'If an effective time is wanted for record types without a business date, the source would have to supply one.'),
    ('I-140', 'Where the AUIF path differs from M3 on faulty files', 'Through AUIF\'s own file importer the AUIF path is STRICTER than M3 for a ragged row, a control character, '
              'a blank line, an extra column (schema drift) and a blank identity value (the whole batch is refused, not one row), and MORE LENIENT for a byte-order mark '
              '(an encoding marker, not data). Every case of the M3 fault corpus is declared and tested.', 'apg/ingest/corpus.py; auif_m8/PATH_EQUIVALENCE_DECLARED_DIFFERENCES.json',
     'If row-level tolerance is wanted on the AUIF path, AUIF\'s importer and input guard would have to change (an AUIF correction revision, CF-50).'),
]
CF = [
    dict(cf_id='CF-46', audit_section='', topic='The independent audit of APG-M8',
         what_remains_open='APG-M8 has not been independently audited. Nothing in it is accepted. F-76 to F-81 are open defects in the builder\'s own AUIF rev13 (CF-50). The construction definitions are '
                           'PROPOSED. EDR-05, EDR-06, EDR-18, EDR-39, EDR-40, EDR-41 and every other open EDR and CF item stay open; CF-41 stands.',
         what_this_package_shows='tools/run_m8_all.py (groups, one test file per group); tools/run_m8_tests.py; tools/m8_mutants.py; tools/sabotage_m8.py; tools/run_regression_m8.py',
         linked_records='SR-121 to SR-125; F-76 to F-81; I-135 to I-140; CF-47 to CF-50', who_must_act='Auditor: audit APG-M8.', status='Open - for the auditor'),
    dict(cf_id='CF-47', audit_section='', topic='Deviation DEV-M8-01 (field-reference form, because of AUIF finding M8-F1)',
         what_remains_open='Authorised by the product owner on 2026-10-20 ("Authorise M8 continuation under DEV-M8-01 as written"). It lasts while AUIF rev13 is the dependency. '
                           'Once a corrected AUIF revision is authorised, built and audited (CF-50), the packs must be regenerated in the contract form under a new authorisation; reference formats are never '
                           'changed silently and no revision is substituted.',
         what_this_package_shows='apg_auif/pack.py (field_ref, check_field_ref, form_problems); tests_m8/test_m8_dev01.py', linked_records='F-76; I-135; CF-50',
         who_must_act='Product owner: any change of dependency (CF-50).', status='Open - deviation recorded and authorised; not a release acceptance'),
    dict(cf_id='CF-48', audit_section='', topic='Mapping APG record types onto the AUIF CORE concepts',
         what_remains_open='The M8 definitions are MODULE-namespace only, as authorised. Whether APG record types should also map onto CORE concepts (Party, Agreement, Document, '
                           'Change, ...) is the canonical-model owner\'s decision (AUIF OD-08) and has not been made.',
         what_this_package_shows='apg_auif/definitions.py (module docstring)', linked_records='SR-122', who_must_act='Canonical-model owner', status='Open - owner decision'),
    dict(cf_id='CF-49', audit_section='', topic='Market data (M6) through AUIF',
         what_remains_open='M8 carries the files the financial core and detection read (26 record types). The M6 market files (mkt_templates) are not carried through AUIF.',
         what_this_package_shows='apg_auif/layout.py', linked_records='SR-124', who_must_act='Product owner: whether a later milestone carries them', status='Open - out of M8 scope'),
    dict(cf_id='CF-50', audit_section='', topic='An AUIF correction revision for M8-F1 to M8-F6 (defects in the builder\'s own AUIF rev13)',
         what_remains_open='AUIF is the builder\'s own build; rev13 is frozen and audited and was not changed in M8. The six defects need a separately authorised AUIF correction '
                           'revision: (F-76) take a field\'s attribute after the concept name in translate_inbound, translate_outbound and the accelerator\'s review check; (F-77) '
                           'a composite source identity, never a content-hash fallback; (F-78) notify the module of events that wait and of their release; (F-79) report a '
                           'module handler failure instead of only keeping its type name; (F-80) say in the sync report whether the read reached the end; (F-81) report, not '
                           'raise, for drift before the first validation and for a blank identity value. That revision would end DEV-M8-01 (the packs regenerated in the '
                           'contract form). This is not Engine work: nothing here needs the Anchor Engine, a database or an environment; Amir receives the corrected '
                           'revision only for his Engine-dependent work.',
         what_this_package_shows='tests_m8/test_m8_dev01.py, test_m8_findings.py, test_m8_events.py (each defect pinned on rev13; the M8-F1 pin fails on purpose once fixed)',
         linked_records='F-76 to F-81; CF-47; I-135', who_must_act='Product owner: authorise the correction revision. Builder: build it. Auditor: audit it.',
         status='Open - not authorised; not started'),
]
if __name__ == '__main__':
    P = sys.argv[1]
    M7.P = P
    M7.add('FINDINGS_REGISTER.csv', 'finding_id', FIND)
    M7.add('STATUS_REGISTER.csv', 'item_id', STATUS)
    M7.add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=i, milestone=M, topic=t, builder_reading=b, blueprint_ref=r, effect_if_wrong=e,
                                                                      status=M7.RETAINED) for i, t, b, r, e in INTERP])
    M7.add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', CF)
