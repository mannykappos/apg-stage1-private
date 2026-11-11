#!/usr/bin/env python3
"""Adds the APG-M6.4 correction rows to the programme tables and appends one row to the carried-forward register.  Usage: make_m63_registers.py <programme_dir>
Runs AFTER make_m63_registers.py.  Idempotent: a row whose id already exists is left alone.  It changes no existing row.  Nothing here closes a finding, approves an interpretation, settles a
decision, numbers or approves RFC-01, adopts a baseline or configures a finance assumption."""
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


BLD = 'Builder (inspection of the approval gate CF-22 after the M6.3 audit)'
OPEN_FIXED = 'Corrected in APG-M6.4 (builder-implemented); open until independently verified'
FIND = [
    ('F-56', BLD, 'M6.4', 'An approval token named the evidence but not the proposal: an approver could approve a proposal that was written after the one that was shown',
     'Found by the builder while inspecting the approval integration gate (CF-22) after the independent audit of APG-M6.3, and reproduced on the delivered M6.3 package (tools/probe_proposal_swap.py). An approver is shown '
     'proposal 1 and its approval token (finding id, version, evidence digest). Before the approver submits, a reviewer sends the finding back to confirmed and the owner proposes a DIFFERENT action against the '
     'SAME evidence. The finding version and the evidence digest do not change, so the token still matches and approve_action records the approval against the new text, which the approver never saw. It is the same '
     'class as F-53 (an approval that is not of what was shown). The M6.1 to M6.3 tests bound the approval to the evidence and to the proposal\'s evidence, not to the proposal itself; that is the builder\'s omission. '
     'The independent audits of M6.1 to M6.3 did not report it.',
     'apg/det/findings.py; tests/test_det_proposal_identity.py; tools/probe_proposal_swap.py; programme/CHANGE_RECORD_APG-M6.4.md; F-52; F-53; F-55; CF-22; I-75 to I-78',
     'Corrected in the separately versioned release APG-M6.4; the delivered M5, M6, M6.1, M6.2 and M6.3 archives and their hashes are unchanged. The approval token also carries proposal (a reference to the proposal on '
     'record: its text, proposer, time, the version and digest it was written against, and how many proposals it replaced). approve_action refuses without it (APPROVAL_TOKEN_REQUIRED) and an approval that names another '
     'reference is refused (PROPOSAL_CHANGED); the reference of the approved proposal is kept in the record, in the events and in an ended approval. Tests were written first and seen to fail on M6.3. '
     'Builder-implemented and locally tested; no independent review has taken place. F-52, F-53, F-54 and F-55 also stay open until independently verified.',
     OPEN_FIXED),
]
INTERP = [
    ('I-75', 'What makes a proposal "the same" one',
     'A proposal is identified by its exact text, proposer, time, the version and evidence digest it was written against, and the number of proposals it replaced. A proposal written again, even with the same words, '
     'is a new proposal and needs a new approval.',
     '15:15.11', 'A looser reading (the same words are the same proposal) would let an old token approve a re-proposal; a stricter one (a signed proposal) would be an Engine design.'),
    ('I-76', 'The entry point requires the reference; the lower-level call does not',
     'approve_action, the entry point for screens and APIs, requires the proposal reference and fails closed without it. The lower-level transition keeps its optional arguments for existing callers and checks a '
     'reference when one is named. That a screen or API uses approve_action is for the Engine build (CF-22).',
     '15:15.4', 'Requiring it in the lower-level call as well would change every caller that does not display a proposal, such as the existing lifecycle tests.'),
    ('I-77', 'Approvals recorded before M6.4',
     'An approval stored by M6.1 to M6.3 has no approved_proposal, so approval_current is false for it and a person must approve again. This follows the M6.1 rule for records made before a binding existed.',
     '06:11', 'Treating such an approval as current would trust an approval that cannot be tied to the proposal that was approved; moving stored data is for the Engine build (I-64).'),
    ('I-78', 'Order of the refusals',
     'Self-approval, then a malformed named value (APPROVAL_TOKEN_REQUIRED), then an older version or digest (STALE_APPROVAL), then a proposal written against old evidence (STALE_PROPOSAL), then a proposal that is not the '
     'one named or cannot be identified (PROPOSAL_CHANGED). The reference is checked after the evidence so the reason given is the first thing that is wrong.',
     '15:15.4', 'A different order would only change which code a caller sees; every case is refused and audited, and nothing changes in the record.'),
]
SRROWS = [
    ('SR-72', 'Approval bound to the exact proposal that was shown: proposal reference in the approval token, PROPOSAL_CHANGED, approved proposal kept in the record (F-56)', 'Local-tested',
     'apg/det/findings.py; tests/test_det_proposal_identity.py; tools/probe_proposal_swap.py; programme/CHANGE_RECORD_APG-M6.4.md',
     'Builder-implemented and locally tested; no independent review has taken place. Governs the prototype\'s records only: nothing executes an action, and no screen or API exists. The auditor verifies the correction'),
    ('SR-73', 'Repeat of the M5 mutation runs for the four M5 modules after the M6.4 correction', 'Local-tested', 'tools/m5_mutants.py; logs/m64/mutation_run_m5_*.log',
     'Builder-run; no independent review has taken place. Shows the tests notice one-place changes of the kinds listed; the builder\'s own figures. Any run that does not finish is recorded as incomplete, not as a pass'),
]
CF_H = ['cf_id', 'audit_section', 'topic', 'what_remains_open', 'what_this_package_shows', 'linked_records', 'who_must_act', 'status']
CF = [
    ('CF-25', '5', 'The approval request boundary is not built: replay-safe requests, project-level authorisation and boundary audit',
     'CF-22 stays open. Beyond the version, digest and proposal reference now carried by the approval token, a real approval screen or API needs a request boundary that is safe to repeat (a request identifier whose '
     'repeat returns the first result), that authorises the approver for the finding\'s project (the project permission model is an Engine decision, EDR-29) and that refuses another tenant\'s records, with each '
     'outcome audited. None of this exists. Blueprint Section 15 requires authorisation on every request and replay protection where relevant.',
     'approve_action fails closed on a missing or stale version, digest or proposal reference; a second submission of the same approval is refused as not allowed (safe, but not a repeat of the first answer); '
     'the scoped store refuses another tenant\'s records. No project-level check exists; any holder of the approver role in a tenant can approve a finding of any project in it.',
     'CF-22; F-56; F-39; EDR-11; EDR-20; EDR-29', 'Builder (first slice of M9, the API contract, in a later release); Amir (Engine build); the auditor (integration test)', 'Open - not built'),
]
add('FINDINGS_REGISTER.csv', 'finding_id', [dict(finding_id=a, raised_by=b, milestone=c, title=d, description=e, linked_items=f, how_it_is_handled_here=g, status=h) for a, b, c, d, e, f, g, h in FIND])
add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=a, milestone='M6.4', topic=b, builder_reading=c, blueprint_ref=d, effect_if_wrong=e, auditor_note='',
                                                               status='Retained for review - not approved', reviewer_decision='') for a, b, c, d, e in INTERP])
add('STATUS_REGISTER.csv', 'item_id', [dict(item_id=i, item=t, milestone='M6.4', evidence_ladder_status=l, evidence=e, claim_limit=c) for i, t, l, e, c in SRROWS])
add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', [dict(zip(CF_H, r)) for r in CF])
print('M6.4 rows added')
