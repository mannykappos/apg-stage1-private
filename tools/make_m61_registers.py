#!/usr/bin/env python3
"""Adds the APG-M6.1 correction rows to the programme tables and writes the Engine #17 governance register.  Usage: make_m61_registers.py <programme_dir>
Runs AFTER make_m6_registers.py.  Idempotent: a row whose id already exists is left alone.  It changes no existing row.  Nothing here closes a finding, approves an interpretation, settles a
decision, numbers or approves RFC-01, or adopts a baseline."""
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


BUILDER = 'Builder (Engine #17 Phase 0)'
FIND = [
    ('F-52', BUILDER, 'M6.1', 'Defect E, found in the Engine #17 Phase 0 discovery: an action approval stayed in force after the finding\'s evidence changed',
     'In M5 and M6 the approved action of a finding recorded who approved it and when, but not the finding version or the evidence it was approved against. When a later detection run changed the evidence '
     '(version 1 to version 2, a new state digest) the signal and the version were replaced, but the status stayed action_approved and the approval fields were not touched, so an approval given on the '
     'old figures still read as an approval of the new ones. A probe on the delivered M6 tree showed it: the finding was action_approved at version 1 and action_approved at version 2 with the same '
     'approver. APG does not carry out actions or move money, so this is a defect in the integrity of the record, not a loss. It was reported to the auditor in the Phase 0 report (gate E17-A23); on '
     '2026-10-15 the auditor directed a labelled, separately versioned correction under change control.',
     'apg/det/findings.py; tests/test_det_approval_binding.py; tools/m5_mutants.py; programme/CHANGE_RECORD_APG-M6.1.md; programme/E17_GOVERNANCE_REGISTER.csv (G-10)',
     'Corrected in the separately versioned release APG-M6.1; the delivered M5 and M6 archives and their hashes are unchanged. An approval now records the finding version and the evidence digest it '
     'names. A changed digest ends the approval (kept in the action\'s approval history), returns the finding to action_proposed with no new status, and needs a fresh approval by a person other than '
     'the proposer. Regression tests cover version 1 to version 2, unchanged evidence, replay, an older run, and reuse of the ended approval. The change record names the defect, the impact and the exact '
     'files changed. Builder-implemented and locally tested; no independent review has taken place.',
     'Handled in the correction release; for the auditor to confirm'),
]
INTERP = [
    ('I-59', 'Material evidence change that ends an approval',
     'The evidence has changed materially when the signal\'s state digest differs from the digest the approval names. This is the same test M5 already uses to raise a new finding version. No size threshold is '
     'applied, because none has been set; a change that only drifts with time and leaves the digest alone does not end an approval.',
     '06:6; 06:11', 'A threshold would be a policy decision. Without one, any change to the evidence asks for a fresh approval, which is the safe direction but may ask more often than the business wants.'),
    ('I-60', 'Approval ended while the action is in progress',
     'When the approval is ended while the finding is in_progress, the finding returns to action_proposed like any other. The record shows that the approval of the old evidence no longer stands. It does '
     'not say that work stopped or was undone: APG never carries out an action, so what happens to work already under way is for the people involved.',
     '06:6; 06:11', 'A separate holding status would be a new lifecycle state, which the auditor directed against. A wrong reading would hide that work had started under an approval that has since ended.'),
    ('I-61', 'A reopened finding ends the approval it rested on',
     'When a resolved or dismissed finding is reopened by a detection run, an approval still in force is ended in the same step (reason finding_reopened), because the reopened finding is a new version. '
     'The finding goes to reopened as before and nothing else changes.',
     '06:11', 'Leaving it in force would let a reopened finding keep a bound approval of a version it no longer is.'),
    ('I-62', 'Optional version named by the approver',
     'The approval step accepts an optional version number. When it is given and is not the finding\'s current version the approval is refused (STALE_APPROVAL). When it is not given the approval binds to '
     'the version and digest current at that moment. Screens built on the Engine are expected to pass it; that is a handoff point, not something this package can enforce.',
     '06:11', 'Without the version an approver who read an older screen binds an approval to a newer version without having seen it.'),
    ('I-63', 'The ending of an approval is a service act, not a role transition',
     'The table of allowed transitions is unchanged. Only a detection run, acting as the service, can move an approved or in-progress finding back to action_proposed, and only because the evidence '
     'changed. A person still cannot make that move.',
     '06:6; 06:11', 'Adding it to the table would let a reviewer undo an approval without a cause, which the lifecycle does not allow.'),
    ('I-64', 'Records written before the correction',
     'A finding stored before APG-M6.1 has no version or digest on its approval. It is never treated as bound: it does not count as an approval in force, and if its evidence then changes the ending is '
     'recorded with no version or digest. No such record exists outside the builder\'s own tests; moving real data is for the Engine build.',
     '06:11', 'Treating an unbound approval as current would repeat the defect for old data.'),
]
SRROWS = [
    ('SR-62', 'Approval binding: an approval names the finding version and evidence digest; a changed digest ends it and sends the finding back for a fresh approval (F-52)', 'Local-tested',
     'apg/det/findings.py; tests/test_det_approval_binding.py; programme/CHANGE_RECORD_APG-M6.1.md',
     'Builder-implemented and locally tested; no independent review has taken place. Governs the prototype\'s records only: nothing executes an action. The auditor confirms the correction and the change record'),
    ('SR-63', 'Repeat of the M5 mutation runs for the four M5 modules after the correction', 'Local-tested', 'tools/m5_mutants.py; logs/mutation_run_m61_*.log',
     'Shows the tests notice one-place changes of the kinds listed; the builder\'s own figures, not independently reproduced'),
    ('SR-64', 'Record of the auditor\'s 2026-10-15 directions on Engine #17 and the proposed baseline rules for the four vectors', 'Specified',
     'programme/E17_GOVERNANCE_RECORD.md; programme/E17_GOVERNANCE_REGISTER.csv',
     'A record of directions and PROPOSED rules. None is implemented. RFC-01 is still proposed and unnumbered; no baseline owner or finance owner has agreed anything'),
    ('SR-65', 'Engine #17 Phase 0 repository discovery report (no code changed in that phase)', 'Research record', 'programme/E17_PHASE_0_REPOSITORY_DISCOVERY.md',
     'Builder-produced. Its clean rerun of the M6 package is the builder\'s own run, not an independent audit'),
]
GOV_H = ['record_id', 'topic', 'direction_as_received', 'builder_recording', 'status', 'who_must_act', 'blocks']
GOV = [
    dict(record_id='G-01', topic='Authority and placement',
         direction_as_received='Fold Engine #17 into M7 Recommendations as a controlled extension; no separate engine or lifecycle. RFC-01 must be formally approved and numbered before implementation under that authority.',
         builder_recording='Recorded. RFC-01 stays PROPOSED and is not numbered by the builder. M7 has not started. The only implementation done is the approval-binding correction in APG-M6.1, which was directed separately.',
         status='Recorded - RFC-01 still proposed and unnumbered', who_must_act='Product owner (Emmanuel): approve and number RFC-01 as a change request, with Engine #17\'s revised specification as an annex (draft text in programme/E17_GOVERNANCE_RECORD.md)',
         blocks='Any Engine #17 implementation beyond the correction'),
    dict(record_id='G-02', topic='Engine numbering',
         direction_as_received='Do not invent a canonical #1-#18 map. Treat the pack\'s numbering as provisional labels until the blueprint author supplies or approves the mapping.',
         builder_recording='Recorded. The pack\'s Engine #1-#18 labels are used only as the pack\'s own provisional labels. The locked Sections 00-18 and the milestone and capability ids are the navigation structure. No map has been made.',
         status='Recorded - mapping not supplied', who_must_act='Blueprint author or product owner: supply or approve a mapping', blocks='Cross-references from Engine #17 to other engines'),
    dict(record_id='G-03', topic='Approved baselines (general rule)',
         direction_as_received='Baselines are versioned source records with canonical hashes and explicit human-approved adoption, defined separately for each opportunity type. The last paid rate is never an approved baseline by default.',
         builder_recording='Recorded as the rule the foundations are to follow. Not implemented. The existing forecast adoption (apg/fin/forecast_book.py) is the nearest pattern in the code and is not a baseline register.',
         status='Recorded - not implemented', who_must_act='Product owner: confirm the per-vector rules below; each baseline owner approves the underlying records', blocks='Versioned-baseline foundations'),
    dict(record_id='G-04', topic='Baseline rule, V1 value engineering (PROPOSED)',
         direction_as_received='Compare against the current approved specification, scope, design revision and the commercial estimate or comparable quote for the original solution. Technical authority approves equivalence; commercial authority approves the cost comparison.',
         builder_recording='Recorded as PROPOSED by the auditor, subject to the owners approving the underlying records. Not implemented.', status='PROPOSED - not implemented',
         who_must_act='Technical authority; commercial authority', blocks='V1 build'),
    dict(record_id='G-05', topic='Baseline rule, V2 quantity and waste (PROPOSED)',
         direction_as_received='Compare against the approved takeoff or BOQ and drawing revision, reconciled with orders, deliveries and verified installed quantities. Project commercial or quantity-surveying authority approves; technical review where revisions affect scope.',
         builder_recording='Recorded as PROPOSED. Not implemented. M6 holds orders and deliveries; it holds no takeoff, BOQ or verified installed quantity.', status='PROPOSED - not implemented',
         who_must_act='Project commercial or QS authority; technical reviewer', blocks='V2 build'),
    dict(record_id='G-06', topic='Baseline rule, V3 payment terms (PROPOSED)',
         direction_as_received='Compare against the existing contractual payment terms, the approved funding or cost-of-capital assumptions and the cash-flow position. Commercial authority approves terms; the finance owner approves the financial assumptions.',
         builder_recording='Recorded as PROPOSED. Not implemented. No cost-of-capital rate is configured or invented (G-09).', status='PROPOSED - not implemented',
         who_must_act='Commercial authority; finance owner', blocks='V3 build; any net-benefit figure for V3'),
    dict(record_id='G-07', topic='Baseline rule, V4 portfolio aggregation (PROPOSED)',
         direction_as_received='Compare against compatible, approved demand that remains genuinely uncommitted, with specification, quantity, delivery window and project constraints recorded. Each affected project\'s commercial authority approves, plus the delegated procurement authority for a portfolio purchase.',
         builder_recording='Recorded as PROPOSED. Not implemented. The M6 portfolio purchasing check (apg/mkt/purchasing.py) groups demand but does not approve it.', status='PROPOSED - not implemented',
         who_must_act='Each affected project\'s commercial authority; delegated procurement authority', blocks='V4 build'),
    dict(record_id='G-08', topic='Lifecycle',
         direction_as_received='Locked Section 05 section 10 governs benefit states; M5\'s finding statuses govern finding review. No third lifecycle.',
         builder_recording='Recorded and followed. The correction adds no status. The ten statuses are unchanged and the table of allowed transitions is unchanged (I-63). Benefit states are not built.',
         status='Recorded - followed in the correction', who_must_act='None for now', blocks='Nothing'),
    dict(record_id='G-09', topic='Finance assumptions',
         direction_as_received='Cost of capital, overhead rates and opportunity-specific offset categories stay configuration-only until approved. Missing required values block a definitive net-benefit claim.',
         builder_recording='Recorded. No rate, allocation or offset cost is set anywhere. A figure that depends on a missing value may be shown as a qualified scenario and never as a verified net saving.',
         status='Recorded - nothing configured', who_must_act='Finance owner: approve cost of capital, overhead rates and offset categories', blocks='A definitive net-benefit claim'),
    dict(record_id='G-10', topic='M5 approval defect (F-52)',
         direction_as_received='Correction approved. Preserve the original frozen M5 ZIP and hash; separately versioned correction with a change record (defect, impact, exact files changed); bind each approval to the finding version and evidence digest; on material change invalidate or suspend and require fresh review and approval; regression tests for version 1 to 2, unchanged evidence, replay and reuse; re-run the M5 regression and verify the new archive independently.',
         builder_recording='Done in APG-M6.1 as builder-implemented and locally tested; no independent review has taken place. The M5 and M6 archives are untouched. The independent verification of the new archive is the auditor\'s.',
         status='Corrected in APG-M6.1; for the auditor to confirm', who_must_act='Auditor: verify the new archive independently and confirm the change record', blocks='Approval-dependent value-realisation work, until confirmed'),
    dict(record_id='G-11', topic='Sequence',
         direction_as_received='Do not start the full Engine #17 build yet. Approve scope and governance direction, resolve baseline definitions and programme authority, then begin with the approval-binding correction and the versioned-baseline foundations. Then E1-E5 with acceptance gates and independent review intact.',
         builder_recording='The approval-binding correction is done. The versioned-baseline foundations, E1-E5 and M7 are not started and wait for G-01 and the baseline definitions (G-03 to G-07).',
         status='In sequence - foundations not started', who_must_act='Product owner', blocks='Foundations, E1-E5, M7'),
    dict(record_id='G-12', topic='Evidence limit of the Phase 0 report',
         direction_as_received='The Phase 0 report is a builder-produced discovery report; its M6 results are a clean rerun of the builder\'s own package, not an independent audit, and do not establish production readiness.',
         builder_recording='Recorded in SR-65 and carried in every document of this release.', status='Recorded', who_must_act='Auditor: independent verification', blocks='Nothing'),
]
add('FINDINGS_REGISTER.csv', 'finding_id', [dict(finding_id=a, raised_by=b, milestone=c, title=d, description=e, linked_items=f, how_it_is_handled_here=g, status=h) for a, b, c, d, e, f, g, h in FIND])
add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=a, milestone='M6.1', topic=b, builder_reading=c, blueprint_ref=d, effect_if_wrong=e, auditor_note='',
                                                               status='Retained for review - not approved', reviewer_decision='') for a, b, c, d, e in INTERP])
add('STATUS_REGISTER.csv', 'item_id', [dict(item_id=i, item=t, milestone='M6.1', evidence_ladder_status=l, evidence=e, claim_limit=c) for i, t, l, e, c in SRROWS])
if not os.path.exists(os.path.join(P, 'E17_GOVERNANCE_REGISTER.csv')):
    wr('E17_GOVERNANCE_REGISTER.csv', GOV_H, GOV)
print('M6.1 rows added')
