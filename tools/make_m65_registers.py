#!/usr/bin/env python3
"""Adds the APG-M6.5 correction rows to the programme tables (no carried-forward row is added).  Usage: make_m65_registers.py <programme_dir>
Runs AFTER make_m64_registers.py.  Idempotent: a row whose id already exists is left alone.  It changes no existing row.  Nothing here closes a finding, approves an interpretation, settles a
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


BLD = 'Independent audit of APG-M6.4 (reported to the builder by the product owner; reproduced by the builder)'
OPEN_FIXED = 'Corrected in APG-M6.5 (builder-implemented); open until independently verified'
FIND = [
    ('F-57', BLD, 'M6.5', 'The lower-level transition accepted an approval that named no version, evidence digest or proposal reference: the M6.4 gate could be bypassed',
     'Reported by the independent audit of APG-M6.4 and reproduced by the builder on the delivered M6.4 package (tools/probe_transition_bypass.py). M6.4 made the entry point approve_action refuse an approval that does '
     'not name the finding version, the evidence digest and the proposal reference the approver was shown, but left the arguments of transition(..., \'action_approved\', ...) optional (I-76, a builder reading retained '
     'for review). transition accepted an approval that named none of the three, or only some of them, so the protection could be bypassed by calling the lower-level function; the version and the digest had been '
     'optional there since M6.1. The probe shows all seven incomplete combinations accepted on M6.4. It is the same class as F-52, F-53 and F-56 (an approval that is not of what was shown) and the builder\'s omission: '
     'M6.4 documented the optional arguments instead of closing them.',
     'apg/det/findings.py; tests/test_det_transition_gate.py; tools/probe_transition_bypass.py; programme/CHANGE_RECORD_APG-M6.5.md; F-52; F-53; F-55; F-56; CF-22; CF-25; I-76; I-79; I-80',
     'Corrected in the separately versioned release APG-M6.5; the delivered M5, M6, M6.1, M6.2, M6.3 and M6.4 archives and their hashes are unchanged. transition itself now refuses an approval unless the version, the '
     'evidence digest and the proposal reference are all named and well formed (APPROVAL_TOKEN_REQUIRED), then checks each against the record (STALE_APPROVAL, STALE_PROPOSAL, PROPOSAL_CHANGED). Starting the action '
     '(in_progress) also re-checks that the approval is still in force (APPROVAL_NOT_CURRENT). 33 of the 36 new tests were written before the change (the ones that cover the defect fail on the M6.4 code, the rest cover behaviour that was already right); 3 were added after the builder\'s first mutation run left one mutant alive. Builder-implemented and locally tested; no independent review has '
     'taken place. F-52, F-53, F-54, F-55 and F-56 also stay open until independently verified; CF-22 stays open.',
     OPEN_FIXED),
]
INTERP = [
    ('I-79', 'The approval gate is in the lowest-level call (withdraws the reading I-76)',
     'transition(..., \'action_approved\', ...) requires the finding version, the evidence digest and the proposal reference, each well formed, whoever calls it; approve_action is the entry point for screens and APIs and '
     'refuses an incomplete token before it looks at the finding at all (so it answers APPROVAL_TOKEN_REQUIRED even for an unknown finding or for the proposer); transition checks the same things after the person and self-approval checks. The reading I-76 (M6.4: the lower-level call keeps its arguments optional for existing callers) was wrong and is withdrawn; I-76 itself is not rewritten because earlier rows are append-only. '
     'Existing callers that approve without naming anything are refused; the tests that did so were updated to name what the approver was shown.',
     '15:15.4', 'Leaving the arguments optional lets any caller of the lower-level function record an approval of something the approver was not shown. A caller that legitimately has no token has no way to approve.'),
    ('I-80', 'Starting the action re-checks the approval',
     'Moving a finding from action_approved to in_progress requires approval_current to be true for the finding as stored (APPROVAL_NOT_CURRENT otherwise). Through the lifecycle this can only differ from the status when a '
     'stored record was changed outside it (a hand edit, a bad migration); detection already returns an approved finding to action_proposed when the evidence changes. It is a second check, not a new rule.',
     '15:15.11', 'A stricter or looser reading changes only whether a damaged stored record can start work; it does not change what a person can approve. A finding left in action_approved by M6.1 to M6.3 code with an old approval has to be approved again before work starts (I-77).'),
]
SRROWS = [
    ('SR-74', 'Approval gate in the lowest-level call: transition requires the version, the evidence digest and the proposal reference; starting the action re-checks the approval (F-57)', 'Local-tested',
     'apg/det/findings.py; tests/test_det_transition_gate.py; tools/probe_transition_bypass.py; programme/CHANGE_RECORD_APG-M6.5.md',
     'Builder-implemented and locally tested; no independent review has taken place. Governs the prototype\'s records only: nothing executes an action, and no screen or API exists. The auditor verifies the correction'),
    ('SR-75', 'Repeat of the M5 mutation runs for the four M5 modules after the M6.5 correction', 'Local-tested', 'tools/m5_mutants.py; logs/m65/mutation_run_m5_*.log',
     'Builder-run; no independent review has taken place. Shows the tests notice one-place changes of the kinds listed; the builder\'s own figures. Any run that does not finish is recorded as incomplete, not as a pass'),
]
add('FINDINGS_REGISTER.csv', 'finding_id', [dict(finding_id=a, raised_by=b, milestone=c, title=d, description=e, linked_items=f, how_it_is_handled_here=g, status=h) for a, b, c, d, e, f, g, h in FIND])
add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=a, milestone='M6.5', topic=b, builder_reading=c, blueprint_ref=d, effect_if_wrong=e, auditor_note='',
                                                               status='Retained for review - not approved', reviewer_decision='') for a, b, c, d, e in INTERP])
add('STATUS_REGISTER.csv', 'item_id', [dict(item_id=i, item=t, milestone='M6.5', evidence_ladder_status=l, evidence=e, claim_limit=c) for i, t, l, e, c in SRROWS])
print('M6.5 rows added')
