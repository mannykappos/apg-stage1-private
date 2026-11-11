#!/usr/bin/env python3
"""Adds the APG-M9.2 rows to the programme tables: the findings F-58 to F-61, the handoff entry EDR-32, the status rows SR-81 to SR-83, the interpretations I-88 to I-92 and the carried-forward items CF-28 and CF-29.
Usage: make_m92_registers.py <programme_dir>
Runs AFTER make_m91_registers.py.  Idempotent: a row whose id already exists is left alone.  It changes no existing row except the M9 milestone row, whose handoff list gains EDR-32 (the Phase 0 check requires every handoff entry to be named by the milestone that first describes it).  Nothing here settles a
decision, numbers or approves RFC-01, adopts a baseline, configures a finance assumption, closes a finding or starts M7 or Engine #17."""
import csv, os, sys
P = sys.argv[1]


def rd(n):
    with open(os.path.join(P, n), encoding='utf-8', newline='') as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def wr(n, header, rows):
    with open(os.path.join(P, n), 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def add(name, idcol, new):
    if not os.path.exists(os.path.join(P, name)):
        return                                           # the findings and interpretations files are made by the package build, not by make_m0.py
    header, rows = rd(name)
    have = {r[idcol] for r in rows}
    for row in new:
        if row[idcol] not in have:
            rows.append({k: row.get(k, '') for k in header})
    wr(name, header, rows)


AUD = 'Independent audit of APG-M9.1 (the audit text was relayed by the product owner; the defect was reproduced by the auditor and again by the builder on the delivered M9.1 package with tools/probe_m91_audit_findings.py)'
OPEN = 'Corrected in APG-M9.2 (builder-implemented); open until independently verified'
HOW = ('Corrected in the separately versioned release APG-M9.2; the delivered M9.1 archive and its hashes are unchanged. The tests that reproduce it (tests/test_api_m92_corrections.py) were written before the correction and fail on the delivered M9.1 code '
       '(logs/m92/new_tests_on_delivered_m91.log); the probe tools/probe_m91_audit_findings.py prints DEFECT PRESENT on M9.1 and passes on M9.2. Builder-implemented and locally tested; no independent review has taken place, so it stays open until the auditor verifies it. '
       'F-52 to F-57, CF-22 and CF-25 also stay open.')
FIND = [
    dict(finding_id='F-58', raised_by=AUD, milestone='M9.2', title='The approval screen gave the approval token to a caller who cannot approve',
         description='present() computed can_approve from the approver role, the proposer check and the project permission for approve, but returned the token whenever the finding itself could be approved. A caller with project view permission and no approve permission (also: no approver role, or the proposer) received status shown, can_approve False and a non-null token. The contract said the token is given only for a finding that can be approved now, which the builder read as a property of the finding (I-88 records the corrected reading). The request endpoint still checked role, port and self-approval, so this did not by itself let an unauthorised person approve; it disclosed the whole token (version, evidence digest, proposal reference) to a viewer.',
         linked_items='apg/api/approval_boundary.py; tests/test_api_m92_corrections.py; tools/probe_m91_audit_findings.py; programme/CHANGE_RECORD_APG-M9.2.md; programme/APPROVAL_REQUEST_BOUNDARY.md; I-88; SR-81', how_it_is_handled_here=HOW + ' present() now returns the token only when can_approve is true.', status=OPEN),
    dict(finding_id='F-59', raised_by=AUD, milestone='M9.2', title='A conflict on opening the request record was answered CONCURRENT_CHANGE without an audit event',
         description='In request_approval the first write of the request record uses expected revision 0. When another copy of the same request had opened the record, the write raised a conflict and the boundary returned CONCURRENT_CHANGE with retry True, but no audit event was written, although the contract says every outcome is audited. The other transient outcome (a concurrent change of the finding) was already audited; this one was missed.',
         linked_items='apg/api/approval_boundary.py; tests/test_api_m92_corrections.py; tools/probe_m91_audit_findings.py; programme/CHANGE_RECORD_APG-M9.2.md; I-90; SR-81', how_it_is_handled_here=HOW + ' The outcome is now written as an approval_request.refused event with the code CONCURRENT_CHANGE, best-effort like every refusal (a failure to write it does not change the answer).', status=OPEN),
    dict(finding_id='F-60', raised_by=AUD, milestone='M9.2', title='The identifier check accepted a request or finding id ending in a newline (and the session-expiry check had the same flaw)',
         description='The identifier pattern was anchored with ^ and $ and applied with match(); in Python $ also matches before a final newline, so an id ending in a newline passed the plain-identifier rule. The builder reproduced the worse consequence on M9.1: a request id ending in a newline was accepted, the approval was recorded, and the audit write then raised because the audit store rejects a resource name with a control character, leaving an approval without its boundary audit entry. The same end-anchor flaw was in the session-expiry check, which also accepted non-ASCII digits (the builder found this in its own review for the same class).',
         linked_items='apg/api/approval_boundary.py; tests/test_api_m92_corrections.py; tools/probe_m91_audit_findings.py; programme/CHANGE_RECORD_APG-M9.2.md; I-91; SR-81', how_it_is_handled_here=HOW + ' Identifiers and the expiry time are now matched with fullmatch against ASCII-only patterns.', status=OPEN),
    dict(finding_id='F-61', raised_by="The builder's own review of the M9.1 boundary after the audit (same class as F-59: an outcome without an audit event)", milestone='M9.2', title='check_for_execution refused a malformed call or an ended session without an audit event',
         description='check_for_execution returned NOT_ALLOWED for a malformed call or a session that had ended without writing an audit event, though the contract says every call is audited. The other refusals of the same call were audited. Not reported by the audit.',
         linked_items='apg/api/approval_boundary.py; tests/test_api_m92_corrections.py; tools/probe_m91_audit_findings.py; programme/CHANGE_RECORD_APG-M9.2.md; I-92; SR-81', how_it_is_handled_here=HOW + ' The refusal is now audited best-effort (a session that no longer verifies cannot write to the log; the answer stands).', status=OPEN),
]
EDR = [dict(edr_id='EDR-32', port='AuditedChangePort', title='A consequential state change and its audit record must persist together or be reconciled',
            what_apg_needs='When the approval boundary records an approval it writes the lifecycle change, then its own audit entry, then notes the answer under the request id. Each is a separate write against the store. APG needs the Engine either to commit a state change and its audit record in one transaction, or to provide a reconciliation that finds a state change without its audit record. Until then APG relies on a retry: if the audit entry cannot be written the call raises, the answer is not noted, and sending the same request again writes the entry (at least once; a crash between the entry and the note can leave two).',
            why_the_engine_is_needed='Transactions across record kinds and the audit log belong to the Engine store. APG has only an in-memory store in which every write succeeds or raises on its own, which cannot show atomicity.',
            contract_summary='Operation (to be agreed with the Engine): commit(context, changes, audit_entries) -> all of them persist or none does. Invariants: no state change of a consequential kind (an approval, a status change, a materiality or ledger entry) is visible without its audit entry once the call has returned; a failed commit leaves neither; the audit entry never carries free text rationale.',
            contract_test='None written: the in-memory store of this package cannot show atomicity. The Engine would supply a store factory and a test that kills the process between the two writes.',
            blueprint_refs='15:15.8; 15:15.11', capabilities='CAP-05; CAP-30', backlog_ids='', needed_by_milestones='M9; M10',
            decisions_for_amir='Whether the Engine store offers a transaction across record kinds and the audit log; whether a reconciliation job is preferred; where audit records live.',
            owner='Amir (engine, database, environment)', status='Open - described only', evidence_seen='No Engine code, repository or environment seen; no implementation exists')]
SRROWS = [
    ('SR-81', 'Corrections to the approval request boundary after the M9.1 audit: the token only for a caller who can approve (F-58), the conflict outcome audited (F-59), whole-string identifier and expiry checks (F-60), the executor-check refusals audited (F-61), and the approval audit entry written before the answer is noted', 'Local-tested',
     'apg/api/approval_boundary.py; tests/test_api_m92_corrections.py; tools/probe_m91_audit_findings.py; programme/CHANGE_RECORD_APG-M9.2.md',
     'Builder-implemented and locally tested; no independent review has taken place. The audit reproduced the defects on M9.1; it has not reviewed the corrections. Atomic persistence of a state change and its audit record is the Engine\'s (EDR-32); CF-22 and CF-25 stay open'),
    ('SR-82', 'Contract document for the approval request boundary, revision for M9.2: the token rule, the audit-first ordering and the strict identifiers', 'Specified', 'programme/APPROVAL_REQUEST_BOUNDARY.md',
     'A specification written by the builder; no independent review has taken place. The suggested mapping is for the Engine\'s author to accept or replace and is not an approved API specification'),
    ('SR-83', 'Mutation run over the corrected apg/api/approval_boundary.py and package-level sabotage checks for M9.2', 'Local-tested', 'tools/m91_mutants.py; logs/m92/mutation_run_m92.log; logs/m92/sabotage_m92.log',
     'Builder-run; no independent review has taken place. Shows the tests notice one-place changes of the kinds listed; the builder\'s own figures. Any run that does not finish is recorded as incomplete, not as a pass'),
]
INTERP = [
    ('I-88', 'The approval token goes only to a caller who can approve now',
     'M9.1 read "the token is given only for a finding that can be approved now" as a property of the finding. M9.2 reads it as a property of the caller as well: the token is returned only when can_approve is true (the proposal is current and not yet approved, the caller has the approver role, is not the proposer, and the port allows approve in the finding\'s project). A caller who may only view still sees the proposal and the status, and can_approve false. This withdraws the M9.1 reading without rewriting it.',
     '15:15.4', 'If a viewer should be able to hand a token to someone else (for example to paste into a ticket), the token would have to be requested separately; nothing in the lifecycle needs that. The effect of the old reading was to disclose the version, digest and proposal reference to a viewer.'),
    ('I-89', 'The approval\'s audit entry is written before the answer is noted, so the audit is at least once',
     'In M9.1 the answer was noted under the request id first and audited second. If the audit entry failed, the retry returned the noted answer as a replay and the entry never existed. M9.2 writes the entry first and unprotected: if it fails the call raises, the answer is not noted, and the retry recognises the approval from the finding\'s history and writes the entry. A crash between the entry and the note can leave two entries for one approval; the second says it was recovered. Exactly-once needs the Engine (EDR-32).',
     '15:15.8', 'A reader who counts accepted entries as approvals would over-count after such a crash; the entries carry the request id and the finding, so duplicates are recognisable. Exactly-once would need a transaction across the state change and the log.'),
    ('I-90', 'A conflict on opening the request record is audited as a refusal with the code CONCURRENT_CHANGE',
     'No new event type was added: the outcome is written as approval_request.refused with the code CONCURRENT_CHANGE in the detail, as the other transient outcome already was. It is best-effort like every refusal.',
     '15:15.8', 'If the Engine wants transient outcomes under their own event type, it is a one-line change in the boundary and in the contract document.'),
    ('I-91', 'Identifiers and the session expiry time are matched as whole strings of ASCII characters',
     'An identifier is 1 to 128 characters of ASCII letters, digits and . _ : - and nothing else, so a final newline, a space, a control character or a non-ASCII digit makes the request malformed. The session expiry must be exactly YYYY-MM-DDTHH:MM:SSZ in ASCII digits, otherwise the session is not live.',
     '15:15.4', 'A looser rule lets a control character reach the audit log or a comparison; a stricter one (for example refusing a colon) would refuse identifiers the Engine may use. The pattern is one line.'),
    ('I-92', 'A refused call of the executor check is audited best-effort',
     'check_for_execution now writes an audit event for a malformed call or an ended session as it already did for the other refusals. A session that no longer verifies cannot write to the tenant\'s log; the answer (NOT_ALLOWED) stands and nothing is raised.',
     '15:15.8', 'If every refusal must be recorded even when the session cannot write, the Engine needs a system-level log for it; that is not designed here.'),
]
CF = [
    dict(cf_id='CF-28', audit_section='6', topic='Independent verification limits of the M9.1 audit',
         what_remains_open='In the M9.1 audit the full regression and the complete mutation suite were reported as incomplete because of execution timeouts in the auditor\'s environment. They are recorded as incomplete, not as passes. The 78 new tests, the 14 contract cases, the probes, the static and register checks and the golden and demonstration checks were reported as independently run and passed. The auditor\'s written record should say which runs completed.',
         what_this_package_shows='M9.2 makes every long run splittable: tools/run_m92_all.py --list prints the groups and --group N runs one; tools/run_regression_m92.py --step runs one step; the mutation run is listed in chunks of 10 mutants in RUN_COMMANDS.txt. The builder ran them on a clean extraction. Builder-run only.',
         linked_records='CF-27; SR-80; SR-83', who_must_act='Auditor: run the split commands and record which completed', status='Open - for the auditor'),
    dict(cf_id='CF-29', audit_section='5', topic='The approval and its audit entry are not written atomically',
         what_remains_open='The boundary writes the lifecycle change, then its audit entry, then notes the answer. If the audit entry cannot be written the call raises, the approval exists, and the retry writes the entry (built and tested here, I-89); a crash between the entry and the note can leave two entries. A transaction across the state change and the audit record, or a reconciliation, is the Engine\'s (EDR-32). No independent review has taken place.',
         what_this_package_shows='tests in tests/test_api_m92_corrections.py for a failed audit write and for a crash between the entry and the note; the contract document section 4 and 6. Builder-run only.',
         linked_records='F-59; EDR-20; EDR-32; I-89; SR-81', who_must_act='Auditor (review of the retry rule); Amir (Engine persistence)', status='Open - function built and tested (APG-M9.2); atomic persistence for the Engine build (EDR-32)'),
]
def edit_m9():
    """The one existing row this release edits: EDR-32 is first described under M9.  Idempotent.  Nothing else in the table changes."""
    name = 'PROGRAMME_MILESTONES.csv'
    if not os.path.exists(os.path.join(P, name)):
        return
    header, rows = rd(name)
    for r in rows:
        if r['milestone_id'] == 'M9' and 'EDR-32' not in r['handoff_register_entries']:
            r['handoff_register_entries'] = r['handoff_register_entries'] + '; EDR-32'
    wr(name, header, rows)


edit_m9()
add('FINDINGS_REGISTER.csv', 'finding_id', FIND)
add('ENGINE_HANDOFF_REGISTER.csv', 'edr_id', EDR)
add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=a, milestone='M9.2', topic=b, builder_reading=c, blueprint_ref=d, effect_if_wrong=e, auditor_note='',
                                                               status='Retained for review - not approved', reviewer_decision='') for a, b, c, d, e in INTERP])
add('STATUS_REGISTER.csv', 'item_id', [dict(item_id=i, item=t, milestone='M9.2', evidence_ladder_status=l, evidence=e, claim_limit=c) for i, t, l, e, c in SRROWS])
add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', CF)
print('M9.2 rows added')
