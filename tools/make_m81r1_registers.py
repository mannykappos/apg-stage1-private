#!/usr/bin/env python3
"""APG-M8.1-R1 (records only): records the independent auditor's result for APG-M8.1.
  * AD-21  appended to the audit disposition register: the audit of APG-M8.1, "scoped audit passed" (qualified).  Disposition rows are never edited.
  * The M8 row of the programme milestones table: its status changes from "Not started" to what was delivered and audited.  This follows the earlier releases that set
    their own milestone row (M7, M9.1).  No other row or column of that table changes.
The findings, status, interpretations, carried-forward and Engine handoff registers are not changed.  CF-54 (the audit of APG-M8.1) is not edited: AD-21 records its outcome.
Nothing here accepts a release, closes a gate, approves a definition, decides CF-53, or records a result the auditor did not report.
Usage: make_m81r1_registers.py <programme_dir>   (after make_m81_registers.py).  Idempotent."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402

M81_ZIP = '60d4a47318782cdab2f59d54696c1cd493a365ce261ae269bdde52e41c9e2251'
REC = 'APG-M8.1-R1'
AUTH = 'recorded on the product owner\'s authorisation of the records-only release ("Authorise the records-only release for the M8.1 audit result")'
DISP = [dict(
    disposition_id='AD-21', finding_id='SR-127 (the APG-M8.1 release; not a finding)',
    auditor_reference='APG-M8.1: APG as a module client of AUIF rev14; DEV-M8-01 ended (the audit carried forward as CF-54; the end of DEV-M8-01 as CF-55)',
    release_audited='APG-M8.1',
    audit_relayed='Independent audit of APG-M8.1 (ZIP SHA-256 %s), relayed by the product owner on 2026-10-21 (an interim report, then the final verdict); %s' % (M81_ZIP, AUTH),
    disposition='Scoped audit passed: no defect found in the audited APG-M8.1 scope (the auditor\'s words: "APG-M8.1 has passed its scoped independent audit"; '
                '"No correction build is indicated by the results"); qualified, see what is not independently verified',
    what_the_auditor_reproduced='The auditor verified the ZIP hash, its integrity and the 1,368 files; ran the 172 M8 tests (172 of 172 pass), the 11 path-equivalence tests (11 of '
                                '11), the M8 regression and boundary checks (pass) and the nine M8.1 regression steps (verified through the regression and group checks); the 17 '
                                'sabotage cases (17 caught); all 150 verification groups on Python 3.13.5 (150 passed, none failed or incomplete; they include the 2,583 '
                                'existing APG tests); and the full mutation campaign (82 classified: 79 killed, 3 documented equivalent - MD-02, MI-36, MI-39, their '
                                'rationales retained - 0 survived, 0 timed out; the unmutated control passed first; the ten new mutants MI-43 to MI-52 and the previously '
                                'escaping MC-03 were killed). The embedded AUIF rev14 dependency remained unchanged during verification. The auditor stated that the audit '
                                'establishes: APG uses the pinned AUIF rev14 dependency; the contract-form translation packs and composite identity handling passed their '
                                'targeted tests and regression checks; the rev14 import-completeness, refusal and event-notice safeguards passed their targeted tests and '
                                'mutation checks; SOURCE_EMPTY remains in place; the original M3 comparison passed without changing the declared differences to force equivalence.',
    what_is_not_independently_verified='QUALIFIED: (1) Python 3.12 was unavailable to the auditor: the builder\'s Python 3.12 results remain builder evidence, not independently '
                                       'reproduced results. (2) The extension tests against the exact real-Governor ZIP were not independently rerun; this qualification is '
                                       'inherited from the audit of AUIF rev14 (AD-15 to AD-20), whose other qualifications also still stand.',
    what_this_does_not_mean='A pass for the audited scope (APG-M8.1), not acceptance of the APG programme and not production readiness; it does not prove integration with a real '
                            'Anchor Engine or Governor integration. CF-53 (which record types may validly be empty) stays open: no record type has been approved as legitimately '
                            'empty, and Builder Zero tenant zero_two still cannot be assessed through AUIF under the current strict rule. CF-52 stays open. The CF-54 and CF-55 '
                            'rows are not edited (append-only); this disposition records the outcome of CF-54. EDR-05, EDR-06, EDR-18, EDR-39, EDR-40, EDR-41 and every other '
                            'open EDR and CF item stay open; CF-41 stands; the construction definitions are PROPOSED.',
    recorded_in=REC)]

M8_STATUS = ('Delivered - builder-checked, in APG-M8, M8-R1, M8-R2 (records) and M8.1 (on AUIF rev14). APG-M8.1 passed its scoped independent audit, qualified (AD-21). '
             'Not accepted as a release; Builder Zero tenant zero_two cannot be assessed through AUIF until the product owner decides CF-53')


def edit_m8():
    """The one existing row this release edits: the status of M8.  Idempotent.  Nothing else in the table changes."""
    name = 'PROGRAMME_MILESTONES.csv'
    if not os.path.exists(os.path.join(M7.P, name)):
        return
    header, rows = M7.rd(name)
    for r in rows:
        if r['milestone_id'] == 'M8':
            r['status'] = M8_STATUS
    M7.wr(name, header, rows)


if __name__ == '__main__':
    M7.P = sys.argv[1]
    M7.add('AUDIT_DISPOSITION_REGISTER.csv', 'disposition_id', DISP)
    edit_m8()
