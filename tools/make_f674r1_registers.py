#!/usr/bin/env python3
"""Records-only release APG-F67.4-R1: records the independent auditor's finding-level dispositions from the audit of APG-F67.4 (AD-04 to AD-08 in
programme/AUDIT_DISPOSITION_REGISTER.csv, read as I-127 describes).  F-75 is recorded as independently verified corrected with the auditor's execution-limit qualifications;
F-74, F-73, F-72 and F-67 as independently verified corrected on the auditor's independent reruns.  The findings rows keep their builder text; the disposition register is where
their verification status is read.  Nothing here changes code, a test, a tool or a specification, accepts a release, authorises integration, closes an Engine requirement or
gate, or retroactively authorises the start of APG-F67 (CF-41 stands as recorded).
Usage: make_f674r1_registers.py <programme_dir>   (runs AFTER make_f674_registers.py).  Idempotent; no existing row is changed."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402

DISP_FILE = 'AUDIT_DISPOSITION_REGISTER.csv'
AUDIT = ('Independent audit of APG-F67.4 (ZIP SHA-256 4abaa349e201ae2ffccb589b248b2e5d255a92340acdf2bfed17b1194b56c4cd), relayed by the product owner on 2026-10-20, with the '
         'auditor\'s confirmation of the four earlier findings relayed the same day; recorded on the product owner\'s authorisation of APG-F67.4-R1')
RAN = ('The auditor verified the ZIP hash and integrity and that all 1,186 APG-F67.3 files match the F67.3 manifest; ran tools/probe_f674.py (15 defects on APG-F67.3, 0 on '
       'APG-F67.4, control passed); the 9 F-67.4 tests; the F-74, F-73, F-72 and F-67 probes (all corrected) and their 46 tests in four files (all pass); the static regression '
       '(9 of 9); the golden-output check; the record-store history contract (all four faulty stores caught); all 117 test files individually (expected counts totalling 2,583); '
       'the mutation run (130 killed, 1 documented equivalent, 0 unexplained survivors); and sabotage (16 of 16 caught).')
QUAL = ('EXECUTION-LIMIT QUALIFICATIONS (execution limitations, not failed tests): the combined 23-group runner (tools/run_f674_all.py --range 1-23) timed out after group 3, and '
        'the combined regression step R08 exceeded the limit, so their constituent tests and probes were run individually; mutation batch 1 timed out on the slow path of the '
        'documented equivalent PA-CMP-013, so its 13 other mutants were run separately and batches 2 to 10 completed; no timeout was counted as a kill. PA-CMP-013 is documented '
        'as equivalent under RH-03 of the record-store history contract.')
NOT = ('A finding-level disposition only. It does not accept APG-F67.4 or any APG release, establish production readiness, or approve integration or deployment. EDR-39 '
       '(restricting direct writes), EDR-40 (atomic record and audit event) and EDR-41 (record-store history contract) are unverified on any Engine store and stay open, as do '
       'EDR-34 and EDR-36 to EDR-38, CF-36 to CF-39, BLK-01 to BLK-03, M7.3 final acceptance, M9.4 and DEV-MIE-01. It does not retroactively authorise the start of APG-F67: '
       'CF-41 (started without explicit authorisation, not ratified) stands. M8 is not authorised.')
BASIS = 'The auditor\'s independent reruns against the final package APG-F67.4 (see what_the_auditor_reproduced); no qualification beyond those recorded for the audit as a whole.'


def row(i, f, ref, disposition, reproduced, not_verified):
    return dict(disposition_id=i, finding_id=f, auditor_reference=ref, release_audited='APG-F67.4', audit_relayed=AUDIT, disposition=disposition,
                what_the_auditor_reproduced=reproduced, what_is_not_independently_verified=not_verified, what_this_does_not_mean=NOT, recorded_in='APG-F67.4-R1')


DISP = [
    row('AD-04', 'F-75', 'F-75 (type-changing content edits can preserve approval; audit of APG-F67.3)',
        'Independently verified corrected in APG-F67.4, with the execution-limit qualifications below',
        RAN + ' On all five policy records a type-changing edit invalidates the old approval, the owner can approve the changed content afresh, and a type-changed re-store is '
              'refused. No new F-75 defect was found in the checks completed.', QUAL),
    row('AD-05', 'F-74', 'F-74 (an old confirmation can validate a re-planted approval; audit of APG-F67.2)', 'Independently verified corrected in APG-F67.4',
        'tools/probe_f673.py and tests/test_f673_approval_integrity.py, rerun independently against APG-F67.4: all cases corrected, all tests pass. ' + RAN, BASIS + ' ' + QUAL),
    row('AD-06', 'F-73', 'F-73 (forged approvals can be completed; audit of APG-F67.1)', 'Independently verified corrected in APG-F67.4',
        'tools/probe_f672.py and tests/test_f672_forged_entry.py, rerun independently against APG-F67.4: all cases corrected, all tests pass. ' + RAN, BASIS + ' ' + QUAL),
    row('AD-07', 'F-72', 'F-72 (approval stuck after an audit-write failure; audit of APG-F67)', 'Independently verified corrected in APG-F67.4',
        'tools/probe_f671.py and tests/test_f671_approval_recovery.py, rerun independently against APG-F67.4: all cases corrected, all tests pass. ' + RAN, BASIS + ' ' + QUAL),
    row('AD-08', 'F-67', 'F-67 (caller-supplied approval for the detection, financial and procurement policies and the specification register)',
        'Independently verified corrected in APG-F67.4 (the authorisation-process issue of its start stands as recorded in CF-41)',
        'tools/probe_f67.py and tests/test_f67_policy_approval.py, rerun independently against APG-F67.4: all cases corrected, all tests pass. ' + RAN, BASIS + ' ' + QUAL),
]

if __name__ == '__main__':
    P = sys.argv[1]
    M7.P = P
    M7.add(DISP_FILE, 'disposition_id', DISP)
