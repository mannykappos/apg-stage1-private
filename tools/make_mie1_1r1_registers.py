#!/usr/bin/env python3
"""Records-only release APG-MIE-1.1-R1: records the independent auditor's disposition of F-70 and F-71.  Programme rows are never edited, so a verification is recorded in a
new append-only table, programme/AUDIT_DISPOSITION_REGISTER.csv (created here with its header if absent), and the reading is recorded as interpretation I-127.  The F-70 and F-71
rows of the findings register keep their builder text; the disposition register is where their verification status is read.
Usage: make_mie1_1r1_registers.py <programme_dir>   (runs AFTER make_mie1_1_registers.py).  Idempotent; no existing row is changed.  Nothing here accepts a release, closes a
gate, resolves a blocker or records a result the auditor did not reproduce."""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402

M = 'MIE-1.1-R1'
DISP_FILE = 'AUDIT_DISPOSITION_REGISTER.csv'
DISP_HEADER = ['disposition_id', 'finding_id', 'auditor_reference', 'release_audited', 'audit_relayed', 'disposition', 'what_the_auditor_reproduced',
               'what_is_not_independently_verified', 'what_this_does_not_mean', 'recorded_in']
AUDIT = ('Independent audit of APG-MIE-1.1 (ZIP SHA-256 0d2d158c47d5208dfbc3f19a2ad1a75ebed288e038e463241b841ea1de171b4b), relayed by the product owner on 2026-10-20; '
         'the product owner and the auditor agreed to record it in the programme registers')
COMMON_NOT = ('The full 624-mutant run (624 changes, 621 killed, 3 documented equivalents, 0 survivors) is builder-reported: the auditor ran selected mutants only, which '
              'were killed. The full whole-suite command R12 timed out in the auditor\'s environment; the counted groups 9 to 19 (2,528 tests) passed separately.')
COMMON_DOES_NOT = ('It does not accept the MIE-1.1 release, make it production-ready or integrate it with the Anchor Engine. The host-side contracts EDR-36, EDR-37 and EDR-38 '
                   'are unverified on any real store, and the core cannot undo a write a real store has committed before raising an exception. BLK-01 to BLK-03, M7.3 final '
                   'acceptance, the M9.4 comparison and the development deviation DEV-MIE-01 stay open (CF-36 to CF-39).')
DISP = [
    dict(disposition_id='AD-01', finding_id='F-70', auditor_reference='F-MIE1-01', release_audited='APG-MIE-1.1', audit_relayed=AUDIT,
         disposition='Independently verified corrected (audit scope below)',
         what_the_auditor_reproduced='The probe tools/probe_mie1_audit_findings.py on the delivered MIE-1 ZIP (17 of 18 cases defective; the control passed) and on MIE-1.1 '
                                     '(0 of 18). The ten correction tests pass on MIE-1.1 and fail or error on MIE-1. Unexpected commit errors fail closed with the failure '
                                     'audit attempted; audit-sink failures are treated as unavailable; observation batches use an all-or-nothing store call. Sabotage cases '
                                     'C-01 to C-05 (and all 70 cases) were caught.',
         what_is_not_independently_verified=COMMON_NOT, what_this_does_not_mean=COMMON_DOES_NOT, recorded_in='APG-MIE-1.1-R1'),
    dict(disposition_id='AD-02', finding_id='F-71', auditor_reference='F-MIE1-02', release_audited='APG-MIE-1.1', audit_relayed=AUDIT,
         disposition='Independently verified corrected (audit scope below)',
         what_the_auditor_reproduced='The same probe and correction tests. A correction cannot supersede an observation of a different series, source, date or kind, and '
                                     'classification ignores an incompatible supersession link, so existing evidence is protected. Sabotage cases C-06 to C-10 (and all 70 '
                                     'cases) were caught.',
         what_is_not_independently_verified=COMMON_NOT + ' I-125 (the strict reading of what a correction may supersede) is still retained for review.',
         what_this_does_not_mean=COMMON_DOES_NOT, recorded_in='APG-MIE-1.1-R1'),
]
INTERP = [
    ('I-127', 'How an independent verification is recorded', 'Programme rows are append-only and are never edited, so the findings register keeps the builder\'s status text '
              '("open until independently verified") for F-70 and F-71. The auditor\'s disposition is recorded in a separate append-only table, '
              'programme/AUDIT_DISPOSITION_REGISTER.csv, one row per finding and audit, with what the auditor reproduced, what was not reproduced and what the disposition '
              'does not mean. A reader takes a finding\'s verification status from that table. Earlier findings are not back-filled: only F-70 and F-71 were agreed for recording.',
     'Programme conventions (M0); CF-39', 'If the product owner prefers the finding rows themselves to carry the verified status, the append-only rule for the findings register '
              'would need an explicit exception; nothing else changes.'),
]


def add_dispositions(P):
    path = os.path.join(P, DISP_FILE)
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8', newline='') as f:
            csv.DictWriter(f, fieldnames=DISP_HEADER, lineterminator='\n').writeheader()
    M7.add(DISP_FILE, 'disposition_id', DISP)


if __name__ == '__main__':
    P = sys.argv[1]
    M7.P = P
    add_dispositions(P)
    M7.add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=i, milestone=M, topic=t, builder_reading=b, blueprint_ref=r, effect_if_wrong=e,
                                                                      status=M7.RETAINED) for i, t, b, r, e in INTERP])
