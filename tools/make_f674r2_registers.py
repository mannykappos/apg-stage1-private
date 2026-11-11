#!/usr/bin/env python3
"""Records-only correction APG-F67.4-R2: corrects a wording defect the independent auditor found in APG-F67.4-R1.  In AD-05 to AD-08 the field
what_is_not_independently_verified began with a sentence describing the auditor's evidence ("The auditor's independent reruns ..."), which contradicts the field.  Programme
rows are append-only and never edited, so AD-09 to AD-12 are appended, each superseding one of AD-05 to AD-08 (F-74, F-73, F-72, F-67).  Each is identical to the row it
supersedes except: what_is_not_independently_verified (the corrected sentence followed by the unchanged execution-limit qualifications), disposition_id, and recorded_in (which
names the row it supersedes).  The reading rule - a finding's current disposition is its latest row - is recorded as I-134.  No disposition or finding status changes.
Usage: make_f674r2_registers.py <programme_dir>   (runs AFTER make_f674r1_registers.py).  Idempotent; no existing row is changed."""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402
import make_f674r1_registers as R1                             # noqa: E402

CORRECTED = 'No finding-specific qualification beyond the execution-limit qualifications recorded for the APG-F67.4 audit as a whole.'
SUPERSEDES = (('AD-09', 'AD-05'), ('AD-10', 'AD-06'), ('AD-11', 'AD-07'), ('AD-12', 'AD-08'))
INTERP = ('I-134', 'Superseding rows in the audit disposition register; which row is current',
          'The audit disposition register is append-only like every programme table: a row is never edited. A row is corrected by appending a new row for the same finding '
          'whose recorded_in field names the row it supersedes ("supersedes AD-nn"). A finding\'s current disposition is its latest row in the register; a superseded row stays '
          'as the history of what was first recorded. First used in APG-F67.4-R2: AD-09 to AD-12 supersede AD-05 to AD-08 (F-74, F-73, F-72, F-67) to correct the wording of '
          'what_is_not_independently_verified only; no disposition or finding status changed. This extends I-127.',
          'I-127; programme conventions (M0)', 'If the product owner prefers corrections by an explicit edit exception, the register would be edited in place instead; the '
          'dispositions themselves would not change.')


def rows(P):
    with open(os.path.join(P, R1.DISP_FILE), encoding='utf-8', newline='') as f:
        return {r['disposition_id']: r for r in csv.DictReader(f)}


def corrected_rows(P):
    have = rows(P)
    out = []
    for new, old in SUPERSEDES:
        r = dict(have[old])
        r['disposition_id'] = new
        r['what_is_not_independently_verified'] = CORRECTED + ' ' + R1.QUAL
        r['recorded_in'] = 'APG-F67.4-R2; supersedes %s (corrects the wording of what_is_not_independently_verified only)' % old
        out.append(r)
    return out


if __name__ == '__main__':
    P = sys.argv[1]
    M7.P = P
    M7.add(R1.DISP_FILE, 'disposition_id', corrected_rows(P))
    i, t, b, ref, e = INTERP
    M7.add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=i, milestone='F-67.4-R2', topic=t, builder_reading=b, blueprint_ref=ref, effect_if_wrong=e,
                                                                      status=M7.RETAINED)])
