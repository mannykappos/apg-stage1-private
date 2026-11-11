#!/usr/bin/env python3
"""Adds the APG-M9.3 rows to the programme tables: the finding F-62, the status rows SR-84 to SR-86, the interpretations I-93 to I-95 and the carried-forward item CF-30.
Usage: make_m93_registers.py <programme_dir>
Runs AFTER make_m92_registers.py.  Idempotent: a row whose id already exists is left alone.  It changes NO existing row.  Nothing here settles a decision, numbers or approves RFC-01, adopts a baseline, configures a finance assumption, closes a finding or starts M7 or Engine #17."""
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


OPEN = 'Corrected in APG-M9.3 (builder-implemented); open until independently verified'
FIND = [
    dict(finding_id='F-62', raised_by='Independent audit of APG-M9.2 (the audit text was relayed by the product owner; the values were reproduced by the auditor, and again by the builder on the delivered M9.2 package with tests/test_api_m93_corrections.py)', milestone='M9.3',
         title='The session expiry check accepted impossible timestamps: it checked the shape of the string and then compared strings',
         description='_session_live() matched the expiry against a whole-string ASCII pattern (the M9.2 correction of F-60) and then compared it with the present time as a string. The pattern checks shape only, so 2999-99-99T99:99:99Z, 2999-13-01T00:00:00Z and 2999-01-01T25:61:61Z counted as live sessions, and so did impossible calendar dates such as 2999-02-30. The auditor did not demonstrate an end-to-end bypass with a normally issued, sealed session (the context is immutable and the session issuer is the Engine\'s); the helper itself, which every entry point of the boundary relies on, treated impossible future times as live. The builder showed on M9.2, through a test double that presents the context of the caller with a chosen expiry (it bypasses the seal, which the real context carries), that a request carrying such an expiry was approved; that shows what the helper does, not that a real sealed session can be forged. The present time (the clock) was not validated either.',
         linked_items='apg/api/approval_boundary.py; tests/test_api_m93_corrections.py; programme/CHANGE_RECORD_APG-M9.3.md; programme/APPROVAL_REQUEST_BOUNDARY.md; I-93; I-94; I-95; SR-84',
         how_it_is_handled_here='Corrected in the separately versioned release APG-M9.3; the delivered M9.1 and M9.2 archives and their hashes are unchanged. The tests that reproduce it (tests/test_api_m93_corrections.py) were run against the delivered M9.2 code and the ones that fail there are listed in logs/m93/new_tests_on_delivered_m92.log. An expiry is now live only if it is a real UTC moment written YYYY-MM-DDTHH:MM:SSZ in ASCII, strictly later than the present time, and the present time is a real moment too (fail closed). Builder-implemented and locally tested; no independent review has taken place, so it stays open until the auditor verifies it. F-52 to F-61, CF-22, CF-25 and CF-29 also stay open.', status=OPEN),
]
SRROWS = [
    ('SR-84', 'Correction of the session expiry check in the approval request boundary after the M9.2 audit: an expiry is live only if it is a real UTC moment (month, day, hour, minute, second, leap year) strictly later than a present time that is itself a real moment (F-62)', 'Local-tested',
     'apg/api/approval_boundary.py; tests/test_api_m93_corrections.py; programme/CHANGE_RECORD_APG-M9.3.md',
     'Builder-implemented and locally tested; no independent review has taken place. The audit found the gap on M9.2; it has not reviewed the correction. The session issuer, the sealed context and the real clock are the Engine\'s; CF-22, CF-25 and CF-29 stay open'),
    ('SR-85', 'Contract document for the approval request boundary, revision for M9.3: what counts as a live session', 'Specified', 'programme/APPROVAL_REQUEST_BOUNDARY.md',
     'A specification written by the builder; no independent review has taken place. The suggested mapping is for the Engine\'s author to accept or replace and is not an approved API specification'),
    ('SR-86', 'Mutation run over the corrected apg/api/approval_boundary.py and package-level sabotage checks for M9.3', 'Local-tested', 'tools/m91_mutants.py; logs/m93/mutation_run_m93.log; logs/m93/sabotage_m93.log',
     'Builder-run; no independent review has taken place. Shows the tests notice one-place changes of the kinds listed; the builder\'s own figures. Any run that does not finish is recorded as incomplete, not as a pass'),
]
INTERP = [
    ('I-93', 'A session expiry is live only if it is a real UTC moment strictly later than now',
     'The expiry must be exactly YYYY-MM-DDTHH:MM:SSZ in ASCII digits AND a moment that exists: month 1 to 12, a day the month has in that year (29 February only in a Gregorian leap year: divisible by 4, not by 100 unless by 400), hour 0 to 23, minute 0 to 59, second 0 to 59. It is live only if it is strictly later than the present time; an expiry equal to now has ended. Nothing else (a zone offset, fractional seconds, a lower-case letter) is a moment.',
     '15:15.4', 'If the Engine issues expiries in another format (an offset, fractional seconds) every session would be refused until the format or this rule is agreed: a fail-closed effect, visible at once. If an expiry equal to now should still be live, one comparison changes.'),
    ('I-94', 'A leap second and the year 0000 are not accepted',
     'Second 60 is refused, and so is year 0000; years run 0001 to 9999. This is stricter than ISO 8601, which allows a leap second in some timescales, and matches what most programming-language date types accept. A session that lasts into a leap second simply ends one second earlier in the worst case.',
     '15:15.4', 'If the Engine\'s clock can emit second 60, sessions in that second would be refused (fail closed); the table of accepted ranges is one line.'),
    ('I-95', 'A clock that does not give a real moment ends every session',
     'The present time comes from the clock the caller supplies. If it is not itself a real UTC moment in the same format, no session is live (fail closed) rather than comparing an expiry with a meaningless string. The real clock and its format are the Engine\'s.',
     '15:15.11', 'If a deployment\'s clock uses another format the boundary would refuse everything until they agree; it would not approve anything wrongly.'),
]
CF = [
    dict(cf_id='CF-30', audit_section='6', topic='Independent verification limits of the M9.2 audit',
         what_remains_open='In the M9.2 audit the full nested M5 and M6 regression wrappers did not complete within the auditor\'s execution limits. They are recorded as incomplete, not as passes. The auditor reported as independently run and passed: the 24 correction tests, the approval-boundary tests, the permission-port contract, the earlier approval probes, the 27 lifecycle test files run one by one (605 tests), the mutation run in chunks (91 of 92 killed, one documented equivalent), the ZIP hash and integrity, the M9.2 static regression and register checks, the M6.1 to M6.5 static regression checks, the golden checks and the demonstrations. The auditor\'s record of which wrapper commands ran is for the auditor to confirm.',
         what_this_package_shows='M9.3 keeps the split commands of M9.2 (tools/run_m93_all.py --list and --group N; tools/run_regression_m93.py --step; mutation chunks of 10) and adds the recorded time of each group. The builder ran every group on a clean extraction. Builder-run only.',
         linked_records='CF-27; CF-28; SR-80; SR-86', who_must_act='Auditor: run the split commands and record which completed', status='Open - for the auditor'),
]
add('FINDINGS_REGISTER.csv', 'finding_id', FIND)
add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=a, milestone='M9.3', topic=b, builder_reading=c, blueprint_ref=d, effect_if_wrong=e, auditor_note='',
                                                               status='Retained for review - not approved', reviewer_decision='') for a, b, c, d, e in INTERP])
add('STATUS_REGISTER.csv', 'item_id', [dict(item_id=i, item=t, milestone='M9.3', evidence_ladder_status=l, evidence=e, claim_limit=c) for i, t, l, e, c in SRROWS])
add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', CF)
print('M9.3 rows added')
