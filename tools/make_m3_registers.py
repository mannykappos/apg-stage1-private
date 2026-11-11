#!/usr/bin/env python3
"""Writes the findings register and the interpretations register.  Usage: make_m3_registers.py <out_programme_dir>
FINDINGS_REGISTER: what the auditor's M2 review asked to be preserved, plus what the builder found while building M3.  None of these is closed by the builder.
INTERPRETATIONS_REGISTER: every place the builder had to read the blueprint or a change request.  Each is RETAINED FOR REVIEW and is NOT approved; the reviewer
decision column stays empty until the auditor or the product owner fills it in."""
import csv, os, sys
OP = sys.argv[1]
os.makedirs(OP, exist_ok=True)
def wcsv(path, header, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(header); w.writerows(rows)

FIND = [  # id, raised_by, milestone, title, description, links, how_it_is_handled_here, status
 ('F-01', 'Auditor (M2 review)', 'M2', 'Materiality: 96 of 101 orders are material under the illustrative project aggregation',
  'With the illustrative test thresholds (single order 25,000,000 cents; 30-day window; project as the only grouping key) the materiality engine marks 96 of the 101 Builder Zero purchase orders material. That is a calibration issue with an illustrative key and window, not a default and not a finding about the engine.',
  'DEC-A1-8 (aggregation key and window); DEC-A1-1; golden materiality_summary', 'Kept in the programme record. No threshold, key or window is chosen by the builder; the golden file records the observation, and later milestones use the policy as configuration.', 'Open - for the product owner (DEC-A1-8)'),
 ('F-02', 'Auditor (M2 review)', 'M2', 'Audit chain: a careful rewrite of the newest events cannot be detected by the chain alone',
  'A hash chain detects edits that break a link. An attacker who recomputes the hashes of the last events leaves a chain that verifies. Detecting that needs an independent anchor of the chain head.',
  'EDR-21 (AuditAnchorPort)', 'Stated limit in the M2 contract suite; entry EDR-21 carries the full description. No change in M3.', 'Open - handoff entry EDR-21'),
 ('F-03', 'Auditor (M2 review)', 'M2', 'Tenant isolation alone does not stop an authorised tenant user writing directly to a policy or decision record',
  'The control functions check roles, but a session that holds only a tenant role could call the store directly and write a protected record kind. The port contract scopes by tenant and does not know roles.',
  'EDR-20 (RecordKindAuthorisationPort)', 'Stated limit in M2. M3 adds new kinds (recon_state, quarantine, entity_alias, entity_resolution, extracted_document, job) that need the same protection; they are named here for the Engine to decide under EDR-20, whose text is unchanged from M2.', 'Open - handoff entry EDR-20'),
 ('F-04', 'Auditor (M2 review)', 'M2', 'The full M2 wrapper run was too slow for the auditor in one sitting',
  'The auditor re-ran each M2 check separately but not the single wrapper that runs them all, which exceeded the auditor time limit.',
  'tools/run_m2_all.py; tools/run_m3_all.py', 'The M3 wrapper prints the time taken by each step and every step can be run on its own (RUN_COMMANDS.txt). The long mutation runs are separate commands, not part of the wrapper.', 'Handled in the package; for the auditor to confirm'),
 ('F-05', 'Builder (M3)', 'M3', 'The source name on a delivery is trusted',
  'ingest_file receives a source name (for example accounting) and uses it to decide which authority rule applies. Nothing in this build checks that the person or connector delivering the file is registered for that source.',
  'EDR-22 (SourceIdentityPort); EDR-05; EDR-20', 'Stated in the handoff register. Tests show the pipeline refuses tenant spoofing; they cannot show source spoofing is refused because that needs the Engine.', 'Open - handoff entry EDR-22'),
 ('F-06', 'Builder (M3)', 'M3', 'A job worker needs its own service identity to record a terminal failure',
  'If the credentials that submitted a job are revoked or expire during retries, the tenant store refuses the dead-letter record. The reference runner keeps the failure in an unrecorded list and reports recorded false, so it is not lost silently, but a real worker needs an identity of its own to write it.',
  'EDR-04 (JobRunnerPort); contract case JR-08', 'Contract case JR-08 requires the failure to be reported; the identity question is in the EDR-04 decisions for Amir.', 'Open - handoff entry EDR-04'),
 ('F-07', 'Builder (M3)', 'M3', 'A whole file is written as one all-or-nothing batch',
  'The pipeline writes a file as one atomic batch so a failed file leaves nothing behind. A real database may limit batch size or duration; splitting a file removes the all-or-nothing guarantee unless the receipt design is changed.',
  'EDR-23 (BatchWriteLimitsPort); EDR-02', 'This build limits a file to 100,000 rows and 5 MB by default (configuration, not a product decision).', 'Open - handoff entry EDR-23'),
 ('F-08', 'Builder (M3)', 'M3', 'The document extractor is a stand-in',
  'The text reader handles the two Builder Zero quote documents. It exists to test the human-verification rule and the ambiguity handling. It is not an extraction product and was not run on any real PDF, scan or email.',
  'EDR-08 (ExtractionRuntimePort); PS-26', 'Extracted values are never authoritative until a person with the document_verifier role verifies them against the document hash.', 'Open - handoff entry EDR-08'),
 ('F-09', 'Builder (M3)', 'M3', 'Invoice-versus-order amount and price variance is not an ingestion check',
  'Ingestion checks that an order exists and is consistent with the invoice link (PO_NOT_VISIBLE and the PO mismatch codes). Whether an invoice exceeds its order or a rate drifts is detection, and is left to M5 with thresholds from the product owner.',
  'M5; DEC-A1-1 to DEC-A1-8', 'No variance threshold exists in M3.', 'Carried to M5'),
 ('F-10', 'Builder (M3)', 'M3', 'Identical purchase orders are held for a person before detection can use them (PS-17)',
  'PO-0100 and PO-0101 are identical. Ingestion holds both as DUPLICATE_CANDIDATE and does not choose one. The M5 rule for surplus ordering will therefore see both as pending until a reviewer decides.',
  'PS-17; M5', 'Recorded so M5 handles pending orders explicitly rather than assuming both count.', 'Carried to M5'),
 ('F-11', 'Builder (M3)', 'M3', 'Which missing optional values are tolerable is configuration, and the demonstration set is the builder choice',
  'The default policy blocks use of any record with a missing optional value. Builder Zero needs a short tolerated list (for example GST amount on an invoice) so that most records are usable. That list is a demonstration choice, not a product decision.',
  'I-9; DEC-A1-1', 'The list lives in demo_setup.DEMO_POLICY; a real list comes from the product owner and pilot builders. Material fields can never be tolerated.', 'Open - for the product owner'),
 ('F-12', 'Builder (M3)', 'M3', 'A stored job result loses tenant-like keys',
  'The tenant-scope guard removes tenant-like keys from anything written to the store, including a job result. The runner now returns the stored form, so a replay returns exactly what the first run returned.',
  'JR-09; tenancy.screen_payload', 'Behaviour is tested. Handlers should not return tenant-like keys.', 'Handled in the package'),
 ('F-13', 'Builder (M3)', 'M3', 'Reissue detection is a naming pattern only',
  'INV-0185 is shown as a reissue candidate of INV-0184 because of the invoice-number pattern and the credit link. That is lineage information only. It never changes a total; a person must decide.',
  'PS-12; I-12', 'Stated in the lineage record itself.', 'Handled in the package'),
]
wcsv(f'{OP}/FINDINGS_REGISTER.csv', ['finding_id', 'raised_by', 'milestone', 'title', 'description', 'linked_items', 'how_it_is_handled_here', 'status'], [list(f) for f in FIND])

NOT = 'Retained for review - not approved'
INT = [  # id, milestone, topic, builder_reading, blueprint_ref, effect_if_wrong, auditor_note
 ('I-1', 'M2', 'Evidence rungs that are "applicable"', 'Section 17 section 2 calls Operationally verified evidence "applicable". Each requirement has a required level; every rung up to that level is mandatory; higher rungs may be left out.', '17:2', 'Affects requirement closure evidence: a requirement could be closed on fewer rungs than the auditor intends.', 'Auditor: affects requirement closure evidence.'),
 ('I-2', 'M2', 'Role names', 'The role names product_owner, spec_approver, authorised_reviewer, closure_authority, authority_owner, materiality_owner, policy_reviewer and finance_reviewer are placeholders.', 'DEC-A1-5; 04:6', 'Affects the mapping to the real platform roles; every check keyed on a role name must be re-mapped.', 'Auditor: affects the mapping to real platform roles.'),
 ('I-3', 'M2', 'First materiality policy', 'The first policy is compared with a fail-safe baseline (no rules), so it counts as a loosening that needs two humans including the owner.', 'CR-02 R7', 'The first policy could be activated with fewer approvers than intended.', ''),
 ('I-4', 'M2', 'Reason code M-NO-ACTIVE-POLICY', 'The engine adds this reason code; the CR-02 model has no such reason.', 'CR-02 reasons', 'A downstream consumer may not expect the code.', ''),
 ('I-5', 'M2', 'Integrity metadata on run evidence', 'Evidence for run-type statuses carries an artefact hash and names its tests; the exact form is the builder.', '17:3', 'The form of integrity metadata may not match what the auditor wants.', ''),
 ('I-6', 'M3', 'Outcome vocabulary', 'A row has an intrinsic outcome at intake (accepted, accepted_with_warnings, pending_reconciliation, quarantined, rejected) and an effective outcome after reconciliation. Rejected rows are never stored as records; they are kept as reject evidence with the reason.', '04:8; 04:9', 'Reviewers may expect a different set of states or a different place for rejected rows.', ''),
 ('I-7', 'M3', 'Exact duplicate delivery versus duplicate candidate', 'Two invoices are an exact duplicate delivery only if supplier and supplier invoice number match AND every business field is equal. Anything less (same details, different or missing invoice number) is a DUPLICATE_CANDIDATE held for a person. The lowest key is treated as the original so the result does not depend on arrival order.', '04:7', 'Too strict leaves real duplicates for people; too loose counts a repeat once when it was two events.', ''),
 ('I-8', 'M3', 'Same key, different content', 'A second delivery with the same key and different content at the same or unknown revision is a conflict: the record becomes a quarantined marker that keeps every version, sorted so arrival order does not matter. A higher declared revision supersedes an open conflict. A lower revision is stale evidence, not an update.', '04:7; 04:9', 'Different treatment of corrections could overwrite financial data or hide a conflict.', ''),
 ('I-9', 'M3', 'Missing optional values', 'Fail-safe: any optional value that is missing and not declared tolerable blocks use of the record (CRITICAL_VALUE_MISSING). Material fields can never be declared tolerable. The tolerated list in the demonstration is illustrative.', '04:8', 'Too strict floods reviewers; too loose lets an unknown be treated as usable.', ''),
 ('I-10', 'M3', 'Secondary sources', 'A secondary source that disagrees with the primary quarantines the primary. A secondary source that disagrees with itself holds the primary for a person. With no approved register nothing is authoritative.', '04:5; 04:9', 'A different reading could let a disagreeing system pass or block more than intended.', ''),
 ('I-11', 'M3', 'Supplier resolution ladder', 'Stable identifier, then a person-approved alias, then the exact full name with legal words kept, then resemblance, which only shows candidates and never chooses. SYN Metro Steel is not SYN Metro Steel Pty Ltd.', '04:11', 'A looser ladder risks a forced merge; a stricter one sends more to review.', ''),
 ('I-12', 'M3', 'Credits and reissues', 'A credit note is netted against its invoice only if the credit itself is trusted; otherwise the invoice is left out of the authoritative total. A reissue found by invoice-number pattern is lineage information only.', '04:7; 05:6', 'Netting an untrusted credit would understate cost.', ''),
 ('I-13', 'M3', 'Freshness thresholds', 'No built-in thresholds. A limit is configuration per use; with none configured the answer is cannot_assess, never fresh.', 'PG-DI-AC-13; 08:14', 'A built-in limit would be an invented threshold.', ''),
 ('I-14', 'M3', 'Extracted document values', 'Extracted values stay unverified until a person with the document_verifier role verifies them, tied to the document hash. Ambiguous readings offer candidates and are never chosen by software.', '04:12', 'A weaker rule would let an OCR guess drive a financial figure.', ''),
 ('I-15', 'M3', 'Job retry defaults', 'The reference runner uses three attempts and waits of 1, 2 and 4 seconds as configuration defaults. They are engineering defaults, not product decisions.', '04:15', 'Different bounds change load and delay, not correctness.', ''),
 ('I-16', 'M3', 'Replay key', 'A delivery is identified by the file hash, the mapping version and the source name. The same bytes under another mapping version or from another source are a separate delivery.', '04:7', 'A different key would change what counts as a replay.', ''),
]
wcsv(f'{OP}/INTERPRETATIONS_REGISTER.csv', ['interpretation_id', 'milestone', 'topic', 'builder_reading', 'blueprint_ref', 'effect_if_wrong', 'auditor_note', 'status', 'reviewer_decision'],
     [list(i) + [NOT, ''] for i in INT])
print(len(FIND), 'findings;', len(INT), 'interpretations')
