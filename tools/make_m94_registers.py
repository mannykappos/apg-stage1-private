#!/usr/bin/env python3
"""Adds the APG-M9.4 rows to the programme tables: the finding F-63, the status rows SR-87 to SR-89, the interpretations I-96 to I-98 and the carried-forward item CF-31.
Usage: make_m94_registers.py <programme_dir>
Runs AFTER make_m93_registers.py.  Idempotent: a row whose id already exists is left alone.  It changes NO existing row.  Nothing here settles a decision, numbers or approves RFC-01, adopts a baseline, configures a finance assumption, closes a finding or starts M7 or Engine #17."""
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


OPEN = 'Corrected in APG-M9.4 (builder-implemented); open until independently verified'
FIND = [
    dict(finding_id='F-63', raised_by='Independent audit of APG-M9.3 (the audit text was relayed by the product owner; the failure was reproduced by the auditor at all three entry points, and again by the builder on the delivered M9.3 package with tests/test_api_m94_corrections.py)', milestone='M9.4',
         title='A clock that raises escaped the approval boundary: present, request_approval and check_for_execution raised to the caller, with no refusal and no audit event',
         description='_session_live() read clock.now() without protection, so a clock whose now() raised an ordinary exception made the three public calls raise it to the caller. Severity medium: a failure-handling and auditability defect. The auditor observed an uncaught RuntimeError, zero new audit events and (for request_approval) a finding that stayed action_proposed; no approval or execution bypass was demonstrated and none is claimed. The builder found the same class in two more places: a clock that works once and fails on a later read (request_approval reads the clock again for timestamps and passes it to the lifecycle, so a failure could come after the request was opened), and an expiry or actor kind whose accessor raises. The F-62 contract (a session is live only for a real moment strictly later than a real clock reading) is not complete until this is corrected, so F-62 stays open as well.',
         linked_items='apg/api/approval_boundary.py; tests/test_api_m94_corrections.py; tools/probe_m93_clock_failure.py; programme/CHANGE_RECORD_APG-M9.4.md; programme/APPROVAL_REQUEST_BOUNDARY.md; I-96; I-97; I-98; SR-87; F-62',
         how_it_is_handled_here='Corrected in the separately versioned release APG-M9.4; the delivered M9.1, M9.2 and M9.3 archives and their hashes are unchanged. The tests that reproduce it (tests/test_api_m94_corrections.py) were run against the delivered M9.3 code and the ones that fail there are listed in logs/m94/new_tests_on_delivered_m93.log. A clock or an expiry that cannot be read, or that is not a real UTC moment, ends the session: the call gives its ordinary refusal (no new code), no approval is made and nothing is stored, and the refusal is audited best-effort with a reason that names the clock. The clock is read once per call. Builder-implemented and locally tested; no independent review has taken place, so it stays open until the auditor verifies it. F-52 to F-62, CF-22, CF-25 and CF-29 also stay open.', status=OPEN),
]
SRROWS = [
    ('SR-87', 'Correction of the clock and session failure handling in the approval request boundary after the M9.3 audit: a clock or expiry that cannot be read, or is not a real moment, ends the session as an ordinary audited refusal; the clock is read once per call (F-63)', 'Local-tested',
     'apg/api/approval_boundary.py; tests/test_api_m94_corrections.py; programme/CHANGE_RECORD_APG-M9.4.md',
     'Builder-implemented and locally tested; no independent review has taken place. The audit found the failure on M9.3; it has not reviewed the correction. The session issuer, the sealed context and the real clock are the Engine\'s; CF-22, CF-25 and CF-29 stay open'),
    ('SR-88', 'Contract document for the approval request boundary, revision for M9.4: what happens when the clock or the expiry cannot be read', 'Specified', 'programme/APPROVAL_REQUEST_BOUNDARY.md',
     'A specification written by the builder; no independent review has taken place. The suggested mapping is for the Engine\'s author to accept or replace and is not an approved API specification'),
    ('SR-89', 'Mutation run over the corrected apg/api/approval_boundary.py and package-level sabotage checks for M9.4, run fresh by the build', 'Local-tested', 'tools/m91_mutants.py; logs/m94/mutation_run_m94.log; logs/m94/sabotage_m94.log',
     'Builder-run; no independent review has taken place. Shows the tests notice one-place changes of the kinds listed; the builder\'s own figures, not a substitute for an independent run. Any run that does not finish is recorded as incomplete, not as a pass'),
]
INTERP = [
    ('I-96', 'A clock or expiry that cannot be read ends the session as an ordinary refusal',
     'If clock.now() raises an ordinary exception, the clock is missing or not callable, or the context\'s expiry (or actor kind) cannot be read, the session is treated as ended. The call gives the refusal it already gives for an ended session (present: NOT_ALLOWED; request_approval: SESSION_EXPIRED, or HUMAN_REQUIRED for an actor kind that cannot be read; check_for_execution: valid False, NOT_ALLOWED). No new result code is added. The refusal is audited best-effort like every refusal, with a reason that says the clock gave no usable time; the text of the exception is not copied into the audit trail.',
     '15:15.4', 'If the API layer wants a distinct code for an unavailable clock (for example a retryable error), one code is added at the Engine\'s mapping; until then the caller sees an ended session and signs in again.'),
    ('I-97', 'The clock is read once per call and that reading is the time of the call',
     'The boundary reads the clock once, at the session check. The lifecycle and the boundary then use that one reading for every timestamp of the call, so the session check and the approval carry the same instant and a clock that fails after its first read cannot stop an approval half way. A clock that moves on during one call is therefore read once rather than at each write.',
     '15:15.4', 'If a caller needs each write stamped at its own moment, the stamps would be equal within one call; the audit log has its own times. Reverting means reading the clock again inside the lifecycle and guarding every read.'),
    ('I-98', 'Only ordinary exceptions are a refusal; other context attributes are the Engine\'s',
     'The guard catches ordinary exceptions (Exception). An interrupt (KeyboardInterrupt, SystemExit) is not caught. The attributes the boundary reads to decide the session (the clock, the expiry, the actor kind) are guarded; the others (tenant, user, roles, session id, seal) belong to the Engine\'s sealed context and are read as before.',
     '15:15.11', 'If the Engine\'s context can raise when its other attributes are read, those calls would still raise; the Engine\'s context contract should say whether they may.'),
]
CF = [
    dict(cf_id='CF-31', audit_section='6', topic='Independent verification limits of the M9.3 audit',
         what_remains_open='In the M9.3 audit some long nested regression wrappers did not complete independently, and a fresh, complete independent mutation-test result was not obtained; the mutation logs in the packages are the builder\'s artefacts and are not independently verified execution. The auditor also noted that one approval-boundary invocation reported 67 tests, which is one test file and not evidence that every intended suite ran in that command. These are recorded as incomplete, not as passes. The auditor reported as independently run and passed: the 18 M9.3 correction tests, the M9.3 and M9.2 static regressions (14 and 16 checks), the M9.1 baseline check, and individually run test groups including reruns of groups that timed out in batches.',
         what_this_package_shows='M9.4 keeps the split commands (tools/run_m94_all.py --list, --group N and --range; tools/run_regression_m94.py --step; mutation chunks of 10) and gives the expected test count of every API test file so that one invocation can be matched to the suite it ran. The build ran the mutation run fresh on the final source and keeps its output with the exit status. Builder-run only.',
         linked_records='CF-27; CF-28; CF-30; SR-86; SR-89', who_must_act='Auditor: run the split commands and the mutation chunks and record which completed', status='Open - for the auditor'),
]
add('FINDINGS_REGISTER.csv', 'finding_id', FIND)
add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=a, milestone='M9.4', topic=b, builder_reading=c, blueprint_ref=d, effect_if_wrong=e, auditor_note='',
                                                               status='Retained for review - not approved', reviewer_decision='') for a, b, c, d, e in INTERP])
add('STATUS_REGISTER.csv', 'item_id', [dict(item_id=i, item=t, milestone='M9.4', evidence_ladder_status=l, evidence=e, claim_limit=c) for i, t, l, e, c in SRROWS])
add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', CF)
print('M9.4 rows added')
