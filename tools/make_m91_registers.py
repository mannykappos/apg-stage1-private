#!/usr/bin/env python3
"""Adds the APG-M9.1 rows to the programme tables: the handoff entry EDR-31, the status rows SR-76 to SR-80, the interpretations I-81 to I-87 and the carried-forward
items CF-26 and CF-27.  Usage: make_m91_registers.py <programme_dir>
Runs AFTER make_m65_registers.py.  Idempotent: a row whose id already exists is left alone.  It changes no existing row except the M9 row of the milestones table (its status becomes 'In this delivery' and its handoff entries gain EDR-31; EDR-20 and EDR-29 stay where they were first described).  Nothing here closes a finding or a carried-forward item, approves an interpretation,
settles a decision, numbers or approves RFC-01, adopts a baseline, configures a finance assumption or starts M7 or Engine #17."""
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


EDR = [dict(edr_id='EDR-31', port='ProjectActionPort', title='May this person view or approve the findings of this project?',
            what_apg_needs='The approval request boundary asks, on every request and on every replay of a request, whether the authenticated caller may \'view\' or \'approve\' the findings of one project (or the tenant-level findings of the tenant). Without an answer from this port the boundary refuses.',
            why_the_engine_is_needed='Who may do what in which project belongs to the Engine permission model. APG cannot decide it, and an answer supplied by the caller would let the caller widen their own rights. A reference double in the tests stands in; it is not a permission model.',
            contract_summary='Operation: allows(context, scope, action) -> exactly True or False. scope is exactly {\'level\': \'project\', \'project\': id} or {\'level\': \'tenant\'}; action is exactly \'view\' or \'approve\'. Invariants: derived from the authenticated context, never from request input; kept apart by tenant, by person and by project; view does not carry approve; a project grant is not a tenant-level grant; a grant added or taken away is seen on the next question; a session that has ended, was revoked or was not issued by the context port is never allowed; an unknown action or a malformed scope is refused, never raised; the scope given is not changed.',
            contract_test='tools/run_m91_contracts.py (14 cases AP-01 to AP-14, with a reference and 16 deliberately faulty ports in this package). The Engine supplies a factory returning apg.api.contracts_m9.ActionEnv(provider, port, advance) with the seams _contract_grant and _contract_revoke_grant.',
            blueprint_refs='15:15.4; 15:15.5; 15:15.11', capabilities='CAP-05; CAP-30', backlog_ids='', needed_by_milestones='M9; M10',
            decisions_for_amir='How project-level permission is expressed; whether \'approve\' needs \'view\'; whether a tenant-level grant covers every project; how a revoked project is handled in stored records; whether EDR-29 and EDR-31 read from one permission table; that the record kind approval_request is one of those writable only through the control functions (EDR-20).',
            owner='Amir (engine, database, environment)', status='Open - described only', evidence_seen='No Engine code, repository or environment seen; no implementation exists')]
SRROWS = [
    ('SR-76', 'Approval request boundary: a request checked for shape, a person with a live session and the approver role, authorisation for the finding\'s project asked of a port on every request, one answer per request id, recovery of a half-finished request, and an audit event for every outcome (CF-25, first slice)', 'Local-tested',
     'apg/api/approval_boundary.py; tests/test_api_approval_boundary.py; programme/CHANGE_RECORD_APG-M9.1.md',
     'Builder-implemented and locally tested; no independent review has taken place. Logic only: no screen, API, HTTP layer, session store, role directory or project permission model exists, and nothing executes an action. CF-22 and CF-25 stay open'),
    ('SR-77', 'Execution-time check for whoever carries the action out: true only for the exact version, evidence digest and proposal that were approved and are still in force (check_for_execution)', 'Local-tested',
     'apg/api/approval_boundary.py; tests/test_api_approval_boundary.py',
     'Builder-implemented and locally tested; no independent review has taken place. Nothing in APG executes an action or calls this check; the Engine or whoever executes would'),
    ('SR-78', 'ProjectActionPort contract suite (EDR-31): 14 cases, an in-memory reference and 16 deliberately faulty ports, each case hit by at least one fault', 'Local-tested',
     'apg/api/contracts_m9.py; apg/api/reference_m9.py; apg/api/faulty_m9.py; tests/test_api_action_port_contract.py; tools/run_m91_contracts.py',
     'Builder-implemented and locally tested; no independent review has taken place. The reference is a test double, not a permission model; no Engine implementation has been seen or run against the suite'),
    ('SR-79', 'Contract document for the approval request boundary: the three calls, the request, the order of checks, the replay and audit rules, the result codes, a suggested mapping and what the Engine must provide', 'Specified',
     'programme/APPROVAL_REQUEST_BOUNDARY.md',
     'A specification written by the builder; no independent review has taken place. The suggested mapping is for the Engine\'s author to accept or replace and is not an approved API specification'),
    ('SR-80', 'Mutation run over apg/api/approval_boundary.py and package-level sabotage checks for M9.1', 'Local-tested', 'tools/m91_mutants.py; logs/m91/mutation_run_m91.log; logs/m91/sabotage_m91.log',
     'Builder-run; no independent review has taken place. Shows the tests notice one-place changes of the kinds listed; the builder\'s own figures. Any run that does not finish is recorded as incomplete, not as a pass'),
]
INTERP = [
    ('I-81', 'Input limits of the approval request boundary',
     'A request carries exactly six fields. Identifiers are 1 to 128 characters of letters, digits and . _ : -; the digest and the proposal reference are texts of at most 128 characters; the rationale is a non-empty text of at most 2000 characters. These are bounds on input, chosen so that a request is cheap to check. They are not policy values and nothing in the locked blueprint sets them.',
     '15:15.4', 'A limit that is too small refuses a legitimate request (a longer rationale); one that is too large lets a request carry more text than anything needs. Either is a one-line change.'),
    ('I-82', 'The per-action port (EDR-31) is separate from the list of visible projects (EDR-29)',
     'The boundary needs to ask "may this person view / approve in this project", per request. EDR-29 (M6) is the list of projects a caller may see, for a portfolio comparison. They may be answered from one permission table, but they are different questions with different contracts, so the per-action question is a new entry, EDR-31, and EDR-29 is not rewritten. The EDR-29 contract (project_scope_contract, "to be written with M9") is not written in M9.1.',
     '15:15.5', 'If the Engine decides one operation should serve both, EDR-31 can be folded into EDR-29 or the other way round; the boundary would change in one place.'),
    ('I-83', 'A finding that does not exist and a finding the person may not approve get the same answer',
     'Every refusal that comes from the finding lookup or the project check is NOT_FOUND, so a person cannot tell a missing finding from one in a project they have no right to. The true reason is written to the audit log, not to the answer.',
     '15:15.5', 'A distinct "forbidden" answer would tell a person that a finding exists in a project they cannot approve in. A more informative answer could be added for people who may view but not approve; the screen already says can_approve is false.'),
    ('I-84', 'A replay returns the first answer, not the finding\'s present state',
     'Sending the same request again returns the answer the request id first got (marked replayed), even if the approval has since ended because the evidence changed. Only the execution-time check says whether an approval is in force now. The port is still asked on every replay, so a person whose permission was taken away is not served the old answer.',
     '15:15.11', 'A replay that reported the present state would not be a repeat of the first answer. Someone who reads a replayed "approved" as "still in force" would be wrong; the documents say so.'),
    ('I-85', 'Refusals before a request record is opened are not replayed',
     'A request that is malformed, from a service identity, from an ended session, from someone without the approver role, or for a finding the person may not approve in is refused and audited each time, but nothing is stored under its request id; the id is "used" only once the person has passed those checks. The lifecycle\'s own refusals (stale, replaced proposal, self-approval) are stored as the answer to the id.',
     '15:15.4', 'Storing every refusal would let any caller fill the request store with ids it cannot use for anything; storing none would let a refused id be re-used with different content. The first is the choice made here.'),
    ('I-86', 'The execution-time check is open to anyone who may view the finding',
     'check_for_execution does not need the approver role: it reports whether an approval is in force, to whoever carries the action out, provided the port says that person may view the finding. It is audited. It is advisory: APG executes nothing and nothing in APG calls it.',
     '15:15.11', 'If only approvers or a dedicated execution right should be able to ask, the port would need a third action and the Engine would decide who holds it.'),
    ('I-87', 'A half-finished request is credited with an approval only if its own history shows it',
     'If a request stopped between the approval and the note of it, the next try recognises the approval from the finding\'s own history, but only an approval written after the request was opened, by the same person, of exactly the same version, digest and proposal. An earlier approval, or one made by another request, is not credited; the request is then refused by the lifecycle like any other.',
     '15:15.11', 'A looser rule could report "approved" for a request that approved nothing; a stricter one would approve a second time after a crash. The first is the error to avoid.'),
]
CF = [
    dict(cf_id='CF-26', audit_section='5', topic='The approval request boundary: first slice built in APG-M9.1; the parts that belong to the Engine remain',
         what_remains_open='CF-25 and CF-22 stay open. The request boundary exists as logic, a port contract and a contract document, but no approval screen or API exists; the session store, the role directory and the project permission model (EDR-11, EDR-20, EDR-29, EDR-31) are the Engine\'s; the record kind approval_request must be writable only through the boundary (EDR-20); nothing executes an action. No independent review of the boundary has taken place.',
         what_this_package_shows='apg/api/approval_boundary.py with tests, a 14-case contract suite for the per-action port with 16 deliberately faulty ports, a mutation run over the new module, and programme/APPROVAL_REQUEST_BOUNDARY.md. Builder-run only.',
         linked_records='CF-22; CF-25; EDR-11; EDR-20; EDR-29; EDR-31; I-81 to I-87; SR-76 to SR-80', who_must_act='Auditor (review of the boundary); Amir (Engine build and integration test)',
         status='Open - function built and tested (APG-M9.1); screen, API and project permission model for the Engine build'),
    dict(cf_id='CF-27', audit_section='6', topic='Independent verification limits of the M6.5 audit',
         what_remains_open='In the M6.5 audit the full wrapper, the RL and FN mutation runs and the non-static regression timed out in the auditor\'s environment and were incomplete, not failures. After the builder\'s split-run runbook (revision 2) the relayed verdict reports the split regression checks R12 to R26 as passed and states the mutation results (248 of 248) and the M6.4 negative control; the same relayed message also said the chunked mutation runs and the remaining wrapper commands were still being run. The auditor\'s written record should say which independent runs completed.',
         what_this_package_shows='The runbook splits every long run into commands of at most 70 seconds (RL-CMP-001, killed by its 300-second timeout, is the one exception) and was run by the builder on a clean extraction. Builder-run only.',
         linked_records='F-57; CF-23; CF-24; SR-75', who_must_act='Auditor: confirm in writing which independent runs completed', status='Open - for the auditor'),
]


def edit_m9():
    """The one existing row this release edits: M9 now has its first slice in this delivery and EDR-31 is first described there.  Idempotent.  Nothing else in the table changes."""
    name = 'PROGRAMME_MILESTONES.csv'
    if not os.path.exists(os.path.join(P, name)):
        return
    header, rows = rd(name)
    for r in rows:
        if r['milestone_id'] == 'M9':
            r['handoff_register_entries'] = 'EDR-11; EDR-31'
            r['status'] = 'In this delivery'
    wr(name, header, rows)


edit_m9()
add('ENGINE_HANDOFF_REGISTER.csv', 'edr_id', EDR)
add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=a, milestone='M9.1', topic=b, builder_reading=c, blueprint_ref=d, effect_if_wrong=e, auditor_note='',
                                                               status='Retained for review - not approved', reviewer_decision='') for a, b, c, d, e in INTERP])
add('STATUS_REGISTER.csv', 'item_id', [dict(item_id=i, item=t, milestone='M9.1', evidence_ladder_status=l, evidence=e, claim_limit=c) for i, t, l, e, c in SRROWS])
add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', CF)
print('M9.1 rows added')
