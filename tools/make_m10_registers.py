#!/usr/bin/env python3
"""APG-M10: appends its rows to the programme tables (after make_m81r1_registers.py).  Programme rows are never edited, except the M10 milestone row's status, as each milestone
release has set its own row (M7, M9.1, M8.1-R1).
  * SR-128 (what M10 built and how it was checked; Local-tested); I-145 to I-151 (the builder's readings, for review); CF-56 (the audit of APG-M10) and CF-57 (the product
    owner's decisions the prototype leaves open).
Usage: make_m10_registers.py <programme_dir>.  Idempotent.  Nothing here accepts a release, closes a finding or a gate, approves a definition or a design, or records a result the
auditor did not report.  The Engine handoff register is not changed (EDR-12 already describes the interface hosting the Engine owns)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m7_registers as M7                                 # noqa: E402

M = 'M10'
AUTH = 'product owner, 2026-10-21: "Authorise M10 as proposed, director first"'
CLAIM = ('Builder-run; no independent review of APG-M10 has taken place. A prototype over synthetic data only (Builder Zero): not a production screen, not an API, no login, no '
         'session, no live system, no network call; the approval screen sends nothing. Not integrated with the Anchor Engine.')
STATUS = [
    dict(item_id='SR-128', milestone=M, evidence_ladder_status='Local-tested',
         item='M10: the UX/UI prototype, director first (' + AUTH + '). Six screens (portfolio, projects with findings and recommendations, data health, imports, approvals, '
              'materials buy-timing) over the existing APG code run on Builder Zero. apg_ui/viewmodel.py computes no amount: every amount is an APG calculation, record, '
              'finding, recommendation or scenario value with its state or label and an evidence entry. Access is read from a project-action port of the M9 contract '
              '(EDR-31; a fixed synthetic stand-in); the approval screen is the real present() answer and shows the exact request; three views (two directors, one '
              'project manager)',
         evidence='apg_ui/; ui/; tools/build_m10_views.py; tests_m10/ (19 tests); ui_tests/run_ui_tests.js (browser and accessibility checks); tools/sabotage_m10.py; '
                  'tools/run_regression_m10.py; logs/m10/', claim_limit=CLAIM),
]
INTERP = [
    ('I-145', 'No total across projects', 'APG calculates no portfolio-level financial figure, and the project figures carry different states (authoritative, provisional, '
              'cannot assess). The prototype shows each project figure as calculated and adds nothing up; the portfolio headline counts the figures by state instead. '
              'Detection exposure is shown per interpretation as the range apg/det/portfolio.py gives, never as one total.', 'Section 06 section 9; EDR-12',
     'If a total is wanted, APG would need a defined portfolio calculation with its own state rules; a screen-side sum would mix states and could present a provisional or '
     'missing amount as settled.'),
    ('I-146', 'The approval screen sends nothing', 'The approvals screen shows what apg.api.approval_boundary.present() returned for that person: the proposal, can_approve, '
              'and the token (finding version, evidence digest, proposal reference). Approving in the prototype shows the exact request request_approval would receive and '
              'sends nothing. The one recorded approval was made by the scripted demonstration (I-149) through the real boundary, and its standing is the real '
              'check_for_execution() answer.', 'CF-22, CF-25, CF-26; programme/APPROVAL_REQUEST_BOUNDARY.md',
     'If the screen sent approvals, it would need a session, an HTTP layer and the Engine\'s project-action port, none of which this prototype has.'),
    ('I-147', 'Which route the figures come from', 'Every APG engine (financial core, detection, procurement, recommendations) runs on the file-import route (M3), so the '
              'figures come from there. The connected-systems route (AUIF rev14, M8) is imported into a separate synthetic world and only its gate answer and import '
              'results are shown, on the data-health and imports screens. For Builder Zero tenant zero_two that route cannot assess (eight SOURCE_EMPTY reasons, CF-53), '
              'and the portfolio says so next to the file-route figures.', 'M8; CF-53; apg_auif/gate.py',
     'If the connected-systems route should be the only basis, zero_two would show no figure until CF-53 is decided, and zero_one\'s figures would be computed from the AUIF '
     'world instead.'),
    ('I-148', 'Whole dollars on screen, cents in the evidence', 'Screens show amounts rounded to whole Australian dollars (cents / 100, rounded half up by the browser\'s '
              'Math.round); the evidence panel shows the exact cents APG returned. A count is shown as a count. A missing value is words (Cannot assess, No defensible '
              'amount), never zero.', 'Section 04 (money in whole cents)',
     'If whole dollars hide a difference a director needs, the screens would show cents, at a cost in readability.'),
    ('I-149', 'The demonstration state is scripted', 'So that every screen has something to show, synthetic people move the findings along as the M7 golden runs do '
              '(apg/rec/golden_rec.py): a reviewer confirms every detected finding, a constraint reviewer assesses the cost findings\' missing information as not critical, '
              'an owner enters an estimated benefit and cost for two cost recommendations and proposes actions on three findings, and the director approves one through the '
              'approval boundary. The portfolio lists these steps. None is a real decision.', 'apg/rec/golden_rec.py; Section 10',
     'If a reader took the demonstration state for a real review, the routes, approvals and estimates would look decided when they are not.'),
    ('I-150', 'An amount in a collapsed row\'s summary', 'A disclosure summary may not contain a button (axe rule nested-interactive). Where a finding or approval row shows '
              'its amount in the summary, the amount is plain text there and the same amount is an evidence button inside the row; the browser tests check that every '
              'summary amount has that button.', 'WCAG 2.2 4.1.2; EDR-12',
     'If the summary amount were the only one, an amount would have no route to its evidence.'),
    ('I-151', 'Plain wording for APG codes', 'Screens put the builder\'s plain wording next to each code APG returned, and always keep the code itself; a code without wording '
              'is shown as recorded, with no invented explanation (apg_ui/plain.py). The detection subtype saving_opportunity is shown as "Possible lower cost (an '
              'opportunity, not a saving)", so that no screen names a saving; the subtype is kept in the data.', 'Section 05 section 10.1; EDR-12',
     'If the wording misstates a code, a director could misread a reason; the code next to it is the check.'),
]
CF = [
    dict(cf_id='CF-56', audit_section='', topic='The independent audit of APG-M10 (the UX/UI prototype)',
         what_remains_open='APG-M10 has not been independently audited. It is a prototype over synthetic data only, with no login, no session, no API, no live system and no '
                           'network call. CF-53, CF-52 and every open EDR and CF item stay open; the construction definitions are PROPOSED.',
         what_this_package_shows='tests_m10/; ui_tests/run_ui_tests.js; tools/sabotage_m10.py; tools/run_regression_m10.py; logs/m10/ (screenshots in logs/m10/screens/)',
         linked_records='SR-128; I-145 to I-151; CF-57; EDR-12; EDR-29; EDR-31', who_must_act='Auditor: audit APG-M10.', status='Open - for the auditor'),
    dict(cf_id='CF-57', audit_section='', topic='Product decisions the prototype leaves open',
         what_remains_open='(1) Whether the director\'s first screen should be the standing of the figures (as built) or something else. (2) Whether any portfolio total is '
                           'wanted, which would need a defined APG calculation (I-145). (3) Which route is the basis of the figures once the connected-systems route is in use '
                           '(I-147, CF-53). (4) The people and access model: the prototype\'s three views use fixed synthetic grants in place of the Engine\'s project-action '
                           'port (EDR-31) and session (EDR-12). (5) Whole dollars or cents on screen (I-148). (6) The product name shown on screen ("Profit Guardian") and '
                           'the visual design, which are the builder\'s proposal.',
         what_this_package_shows='ui/; logs/m10/screens/', linked_records='CF-56; I-145; I-147; I-148; EDR-12; EDR-31', who_must_act='Product owner: decide each, in his own words.',
         status='Open - for the product owner'),
]
M10_STATUS = 'In this delivery (prototype over synthetic data, builder-tested; not independently reviewed)'


def edit_m10():
    name = 'PROGRAMME_MILESTONES.csv'
    if not os.path.exists(os.path.join(M7.P, name)):
        return
    header, rows = M7.rd(name)
    for r in rows:
        if r['milestone_id'] == 'M10':
            r['status'] = M10_STATUS
    M7.wr(name, header, rows)


if __name__ == '__main__':
    M7.P = sys.argv[1]
    M7.add('STATUS_REGISTER.csv', 'item_id', STATUS)
    M7.add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=i, milestone=M, topic=t, builder_reading=b, blueprint_ref=r, effect_if_wrong=e,
                                                                      status=M7.RETAINED) for i, t, b, r, e in INTERP])
    M7.add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', CF)
    edit_m10()
