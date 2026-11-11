#!/usr/bin/env python3
"""APG-M8-R2 (records only): appends the independent auditor's dispositions from three audits to the audit disposition register.  Disposition rows are never edited.
  * AD-13  F-82 (M8-F7)        audit of APG-M8:     the defect raised and reproduced; APG-M8 not accepted pending correction
  * AD-14  F-82 (M8-F7)        audit of APG-M8-R1:  independently verified corrected in APG-M8-R1 (scoped audit passed)
  * AD-15 to AD-20  F-76 to F-81 (M8-F1 to M8-F6)   audit of AUIF rev14: no defect found in the rev14 changes audited (qualified)
The findings rows keep their builder text and status; a finding's disposition is read from this register (interpretation I-127).  Nothing here accepts a release, closes a gate,
approves a definition, or records a result the auditor did not report.  Usage: make_m8r2_registers.py <programme_dir>   (after make_m8r1_registers.py).  Idempotent."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402

M8_ZIP = 'f1b634d36f2ac57eefed6910cdc86273b30b5bdcc13d8be778d1b2f21a81157c'
R1_ZIP = '6e326a6ea02c0df4c7c40952294efcffdd2e74b52340aa1127437f17c7d16fe8'
REV14_ZIP = 'd534a6e6541b6d1a58e0389161d08698a1d7ac92ee9ad880a51fcee36497c649'
REC = 'APG-M8-R2'
GATES = ('EDR-05, EDR-06, EDR-18, EDR-39, EDR-40, EDR-41 and every other open EDR and CF item stay open; CF-41 stands; the construction definitions are PROPOSED. '
         'It does not establish production readiness, integration with a real Anchor Engine, or Governor integration.')
REV14_REPRO = ('The auditor verified the ZIP hash, its integrity and the 254 files; ran the six rev14 test classes individually (31 of 31 pass), the full core suite (441 of 441), the '
               'extension suite (347 pass, 20 skipped: the real-Governor tests) and the accelerator suite (422 of 422); the three static-check scripts (no violations); the '
               'package manifest and the verifier self-test; the three audit replay suites; both reverse-contamination checks; the onboarding evidence consistency check; and '
               'all 51 revision-specific mutants (core M134 to M174: 41 killed; extension E177 to E183: 7 killed; accelerator: 3 killed, as the auditor counted them; the builder\'s record names V119 and V120 as new and V86 as re-anchored).')
REV14_NOT = ('QUALIFIED: (1) the full fresh-ZIP verifier (tools/verify_fresh_zip.py) exceeded the auditor\'s execution limit, so it did not complete in one run; its constituent '
             'checks above were run separately and passed. (2) The R14 Governor ZIP was not available to the auditor, so the extension tests against the real Governor were not '
             'repeated; the builder\'s recorded result (347 run, 0 skipped) remains builder evidence. (3) The full historical mutation suites (core 174, extension 194, '
             'accelerator 437) were not rerun in full; only the 51 revision-specific mutants were. (4) The builder\'s Python 3.12 runs were not reproduced.')
REV14_DOES_NOT = ('A finding-level disposition of the correction in AUIF rev14 only, as the auditor stated it ("no defect found in the rev14 changes audited"); it is not an '
                  'unqualified acceptance of rev14. AUIF rev13 is unchanged. APG still depends on AUIF rev13 and DEV-M8-01 (CF-47) continues: moving APG onto rev14 (M8.1) is '
                  'not authorised. The CF-50 row is not edited (append-only); this disposition is its outcome. ' + GATES)


def rev14(ad, fid, ref):
    return dict(disposition_id=ad, finding_id=fid, auditor_reference=ref + ' (defect in the builder\'s own AUIF rev13; correction audited in AUIF rev14)', release_audited='AUIF rev14',
                audit_relayed='Independent audit of AUIF rev14 (ZIP SHA-256 %s), relayed by the product owner on 2026-10-21; recorded on the product owner\'s authorisation of '
                              'the records-only release ("Authorise the records-only release for the M8, M8-R1 and rev14 audit results, after the rev14 audit")' % REV14_ZIP,
                disposition='No defect found in the AUIF rev14 correction (qualified; see what is not independently verified)',
                what_the_auditor_reproduced=REV14_REPRO, what_is_not_independently_verified=REV14_NOT, what_this_does_not_mean=REV14_DOES_NOT, recorded_in=REC)


AUTH = 'recorded on the product owner\'s authorisation of the records-only release ("Authorise the records-only release for the M8, M8-R1 and rev14 audit results, after the rev14 audit")'
DISP = [
    dict(disposition_id='AD-13', finding_id='F-82', auditor_reference='M8-F7 (empty source data can leave APG assessing stale records; raised by the audit of APG-M8)',
         release_audited='APG-M8',
         audit_relayed='Independent audit of APG-M8 (ZIP SHA-256 %s), relayed by the product owner on 2026-10-20; %s' % (M8_ZIP, AUTH),
         disposition='Defect raised and reproduced by the auditor; APG-M8 not accepted pending its correction (an acceptance blocker)',
         what_the_auditor_reproduced='The auditor verified the ZIP hash, its integrity, the 1,307 files and the embedded AUIF rev13 ZIP hash; reran all 141 verification groups '
                                     '(141 passed: the 154 M8 tests, all 2,583 existing APG tests, the 224 M3 import tests and the nine regression steps); the AUIF rev13 '
                                     'fresh-package verifier (core 410, extension 343 with 20 skipped, accelerator 418, static checks, package verification, the three audit '
                                     'replays); and the 14 sabotage cases (14 caught). The auditor then reproduced the defect: after a good import of the AP invoices (187 '
                                     'records), the source cut to its header was imported as "applied" with no reason, the 187 records stayed and the gate answered can_assess.',
         what_is_not_independently_verified='Python 3.12 was unavailable to the auditor; the 67-mutant campaign was not rerun; the real-Governor tests of AUIF rev13 were not rerun '
                                            '(the Governor package was not supplied).',
         what_this_does_not_mean='It does not accept APG-M8. F-76 to F-81 and DEV-M8-01 were not judged by this disposition. ' + GATES, recorded_in=REC),
    dict(disposition_id='AD-14', finding_id='F-82', auditor_reference='M8-F7 (empty source data can leave APG assessing stale records)', release_audited='APG-M8-R1',
         audit_relayed='Independent audit of APG-M8-R1 (ZIP SHA-256 %s), relayed by the product owner on 2026-10-21; %s' % (R1_ZIP, AUTH),
         disposition='Independently verified corrected in APG-M8-R1 (the auditor\'s words: "scoped audit passed")',
         what_the_auditor_reproduced='The auditor verified the ZIP hash, its integrity and the 1,328 files; ran the 9 empty-source tests (initially empty, became empty after 187 '
                                     'records, the assessment withdrawn, recovery after restoring the source, the event-poll guard) and 47 tests across eight M8 test files '
                                     '(all pass, AUIF rev13 unchanged); regression R01 to R10 (10 of 10); the 11 path-equivalence tests one at a time (11 of 11); sabotage S01 '
                                     'to S15 (15 caught); and the full mutation run (72: 69 killed, 3 documented equivalent - MD-02, MI-36, MI-39 - 0 survived, 0 timed '
                                     'out; the unmutated control passed first).',
         what_is_not_independently_verified='Python 3.12 was unavailable to the auditor: the builder\'s Python 3.12 results remain builder evidence. The audit ran on Python 3.13.5.',
         what_this_does_not_mean='A pass for the audited scope (the empty-source correction), not acceptance of the APG programme and not a production-readiness certification. '
                                 'CF-53 (which record types may validly be empty) stays open: the auditor approved no empty record type and did not weaken the rule; Builder '
                                 'Zero tenant zero_two still cannot be assessed through AUIF. CF-52 stays open. AUIF rev13 is the dependency; rev14 is not used. ' + GATES,
         recorded_in=REC),
    rev14('AD-15', 'F-76', 'M8-F1 (a field reference into a MODULE concept was read after the first dot)'),
    rev14('AD-16', 'F-77', 'M8-F2 (a composite identity fell back silently to a content hash)'),
    rev14('AD-17', 'F-78', 'M8-F3 (events that wait, defer, go to reconciliation or are rejected were not told to the module)'),
    rev14('AD-18', 'F-79', 'M8-F4 (BaseModule swallowed a handler failure; the delivery counted as made)'),
    rev14('AD-19', 'F-80', 'M8-F5 (the sync report did not say whether the read reached the end)'),
    rev14('AD-20', 'F-81', 'M8-F6 (sync raised instead of reporting)'),
]
if __name__ == '__main__':
    M7.P = sys.argv[1]
    M7.add('AUDIT_DISPOSITION_REGISTER.csv', 'disposition_id', DISP)
