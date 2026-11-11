#!/usr/bin/env python3
"""Adds the APG-M6.3 correction rows to the programme tables and appends one row to the carried-forward register.  Usage: make_m63_registers.py <programme_dir>
Runs AFTER make_m62_registers.py.  Idempotent: a row whose id already exists is left alone.  It changes no existing row.  Nothing here closes a finding, approves an interpretation, settles a
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


AUD = 'Auditor (M6.2 independent review)'
OPEN_FIXED = 'Corrected in APG-M6.3 (builder-implemented); open until independently verified'
FIND = [
    ('F-55', AUD, 'M6.3', 'A stored proposal version that merely equals the finding version under Python\'s rules (True, 1.0) was accepted as current and approved',
     'The independent audit of APG-M6.2 reproduced it through the real approval path: a normal version-1 proposal is made; the stored proposal version is changed to the boolean True (simulating malformed, '
     'legacy or damaged persisted state, which the lifecycle itself never writes); the current approval token is obtained; approve_action accepts the action as action_approved with the stored version '
     'still True. proposal_current compared the stored version with the finding version by ordinary equality, and in Python True == 1 and 1.0 == 1. The approval token validator already refused '
     'booleans, so the stored side was less strict than the argument side. The builder repeated it on the delivered M6.2 tree and found the same weakness on the argument side of the lower-level '
     'transition: a named approving_version of True was also accepted for a version-1 finding. The store refuses floats, so a stored 1.0 can only reach proposal_current by a direct call; the function '
     'did not refuse it either. The M6.2 tests used well-formed integers only; that is the builder\'s omission.',
     'apg/det/findings.py; tests/test_det_version_types.py; tools/probe_malformed_proposal_version.py; programme/CHANGE_RECORD_APG-M6.3.md; F-53; I-71 to I-74',
     'Corrected in the separately versioned release APG-M6.3; the delivered M5, M6, M6.1 and M6.2 archives and their hashes are unchanged. A version (stored or named) must be a whole number of at least 1 '
     'and not a boolean, and a digest a non-empty text; proposal_current and approval_current return false for anything else, so the approval is refused (STALE_PROPOSAL), and a malformed version or digest '
     'named by the approver is refused as a malformed token (APPROVAL_TOKEN_REQUIRED). A proposal explicitly marked stale is never current. Tests were written first and seen to fail on M6.2. '
     'Builder-implemented and locally tested; no independent review has taken place. F-52, F-53 and F-54 also stay open until independently verified.',
     OPEN_FIXED),
]
INTERP = [
    ('I-71', 'What counts as a version and as a digest',
     'A version, stored or named, is a whole number of at least 1 and not a boolean; a digest is a non-empty text. The same test applies to the finding\'s version, the stored proposal version and digest, the '
     'approved version and digest, and what an approver names. A malformed stored value means the proposal or approval is not current; a malformed named value is refused as a malformed token '
     '(APPROVAL_TOKEN_REQUIRED) before any comparison.',
     '06:11', 'A looser test lets a value that only equals a version under Python\'s rules stand in for it; a stricter one (for example a format for the digest) would be a further decision.'),
    ('I-72', 'A proposal marked stale is honoured',
     'A proposal whose record says it is stale is never current, even if its version and digest happen to match the finding. Where no mark exists (records made in M6.1) the version and digest alone decide.',
     '06:11', 'Ignoring the mark would let a damaged or hand-edited record override the run that marked it stale.'),
    ('I-73', 'Floats',
     'The record store refuses floats, so a stored 1.0 cannot be written; it can only reach the check by a direct call. The check refuses it there as well, so the rule does not depend on the store.',
     '06:11', 'Relying on the store alone would leave the function unsafe when used on records from another store.'),
    ('I-74', 'Damaged records are not repaired in place',
     'The package does not correct a malformed stored value. A proposal that is not current is replaced by the normal route (a reviewer sends it back, the owner proposes again) and the damaged value is kept as found '
     'in the proposal history.',
     '06:11', 'Repairing in place would hide the damage; a repair tool for real stored data is for the Engine build.'),
]
SRROWS = [
    ('SR-70', 'Strict version and digest validation in proposal_current, approval_current and the named approval arguments (F-55)', 'Local-tested',
     'apg/det/findings.py; tests/test_det_version_types.py; tools/probe_malformed_proposal_version.py; programme/CHANGE_RECORD_APG-M6.3.md',
     'Builder-implemented and locally tested; no independent review has taken place. Governs the prototype\'s records only: nothing executes an action. The auditor verifies the correction'),
    ('SR-71', 'Repeat of the M5 mutation runs for the four M5 modules after the M6.3 correction', 'Local-tested', 'tools/m5_mutants.py; logs/m63/mutation_run_m5_*.log',
     'Builder-run; no independent review has taken place. Shows the tests notice one-place changes of the kinds listed; the builder\'s own figures. Any run that does not finish is recorded as incomplete, not as a pass'),
]
CF_H = ['cf_id', 'audit_section', 'topic', 'what_remains_open', 'what_this_package_shows', 'linked_records', 'who_must_act', 'status']
CF = [
    ('CF-24', '4', 'Independent verification limits of the M6.2 audit',
     'In the M6.2 audit the full 1,820-test suite, the full wrapper and the older wrappers timed out in the auditor\'s environment and are incomplete, not failures; the 230-mutant result and the clean-extraction run '
     'are builder-reported, not independently reproduced. The same limits apply to M6.3.',
     'The build\'s run times are stated in the documents so a limit can be set above them, and the checks can be run in groups.', 'F-55; CF-23; SR-71', 'Auditor: rerun with enough time, or split the runs', 'Open - for the auditor'),
]
add('FINDINGS_REGISTER.csv', 'finding_id', [dict(finding_id=a, raised_by=b, milestone=c, title=d, description=e, linked_items=f, how_it_is_handled_here=g, status=h) for a, b, c, d, e, f, g, h in FIND])
add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=a, milestone='M6.3', topic=b, builder_reading=c, blueprint_ref=d, effect_if_wrong=e, auditor_note='',
                                                               status='Retained for review - not approved', reviewer_decision='') for a, b, c, d, e in INTERP])
add('STATUS_REGISTER.csv', 'item_id', [dict(item_id=i, item=t, milestone='M6.3', evidence_ladder_status=l, evidence=e, claim_limit=c) for i, t, l, e, c in SRROWS])
add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', [dict(zip(CF_H, r)) for r in CF])
print('M6.3 rows added')
