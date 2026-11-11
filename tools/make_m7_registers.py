#!/usr/bin/env python3
"""Adds the APG-M7 rows to the programme tables: status rows SR-90 to SR-97, interpretations I-99 to I-109, the Engine handoff entry EDR-33 and the carried-forward item CF-32, and sets the
status and handoff entry of the M7 milestone row.  Usage: make_m7_registers.py <programme_dir>
Idempotent: a row whose id already exists is left alone.  No other existing row is changed.  Nothing here settles a decision, approves a policy, numbers or approves RFC-01, or closes a finding."""
import csv, os, sys
P = sys.argv[1]
CLAIM = 'Builder-run; no independent review has taken place. The demonstration policy values are synthetic and builder-chosen; nothing is integrated with the Anchor Engine.'
RETAINED = 'Retained for review - not approved'


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
    header, rows = rd(name)
    have = {r[idcol] for r in rows}
    for row in new:
        assert set(row) <= set(header), (name, set(row) - set(header))
        if row[idcol] not in have:
            rows.append({k: row.get(k, '') for k in header})
    wr(name, header, rows)


STATUS = [
    dict(item_id='SR-90', item='Recommendation run (apg/rec/engine.py): eligibility routes (action, investigate, in hand, close, excluded), every factor reported separately, a lexicographic ranking in the policy-stated order with the deciding dimension named for every line, overlap-counted totals per interpretation, plain-language transparency', milestone='M7',
         evidence_ladder_status='Local-tested', evidence='tests/test_rec_eligibility.py; tests/test_rec_ranking.py; tests/test_rec_money.py; tests/test_rec_constraints.py', claim_limit=CLAIM),
    dict(item_id='SR-91', item='Recommendation records and the human decision path (apg/rec/lifecycle.py, apg/rec/inputs.py): ten statuses, gated submission, approval bound to version, digest and submission, separation of duties, deferral, closure, append-only history', milestone='M7',
         evidence_ladder_status='Local-tested', evidence='tests/test_rec_lifecycle.py; tests/test_rec_constraints.py', claim_limit=CLAIM + ' There is no screen or API for these calls.'),
    dict(item_id='SR-92', item='Realised-benefit verification gate (apg/rec/verify.py): adopted forecast baseline set before the action started, stored implementation evidence, an independent verifier, every offsetting cost component addressed, a reproducible realised figure', milestone='M7',
         evidence_ladder_status='Local-tested', evidence='tests/test_rec_verify.py', claim_limit=CLAIM + ' The gate makes the people\'s statements complete, attributable and reproducible; it does not measure anything on site.'),
    dict(item_id='SR-93', item='Scenario isolation and the action boundary: no recommendation path writes a forecast or forecast slot; execute() refuses always; alternatives say they do not change the authoritative forecast', milestone='M7',
         evidence_ladder_status='Local-tested', evidence='tests/test_rec_isolation.py', claim_limit=CLAIM),
    dict(item_id='SR-94', item='Reproducible recommendation runs (formula rec.prioritise v1) and reconstruction of a past recommendation version from its pinned run', milestone='M7',
         evidence_ladder_status='Local-tested', evidence='tests/test_rec_repro.py', claim_limit=CLAIM),
    dict(item_id='SR-95', item='Golden Builder Zero run of the whole chain (M3 to M7) with an independent standard-library oracle for routes, categories and counted totals', milestone='M7',
         evidence_ladder_status='Local-tested', evidence='apg/rec/golden_rec.py; tests/test_rec_golden.py; regression/m7/golden_rec.json', claim_limit=CLAIM + ' The oracle restates the demonstration rules; it is not an independent specification.'),
    dict(item_id='SR-96', item='Mutation run over apg/rec (engine, lifecycle, inputs, policy, verify) and package-level sabotage checks for M7, run fresh by the build', milestone='M7',
         evidence_ladder_status='Local-tested', evidence='tools/m7_mutants.py; logs/m7/mutation_run_m7.log; logs/m7/sabotage_m7.log', claim_limit=CLAIM + ' Shows the tests notice one-place changes of the listed kinds; the builder\'s own figures.'),
    dict(item_id='SR-97', item='Recommendation policy (apg/rec/policy.py): every eligibility value, category, mandatory review, approval band, ranking order, materiality amount and offsetting-cost list is configuration with no default; versioned; approved by a second person', milestone='M7',
         evidence_ladder_status='Local-tested', evidence='tests/test_rec_policy.py', claim_limit=CLAIM + ' No real value has been chosen by the product owner.'),
]

INTERP = [
    ('I-99', 'Unresolved critical evidence', 'Every item of missing information a finding lists is treated as critical until a constraint reviewer records, with a reason, that it is not critical for acting. Unresolved critical evidence routes the finding to investigate (never to a ready action).', '10:3', 'If the product owner wants some items to be non-critical by rule, the reviewer step is extra work; nothing unsafe follows.'),
    ('I-100', 'Urgency and time sensitivity', 'Urgency is how soon the dated condition falls due (overdue, soon within the policy days, later, not dated); time sensitivity is whether a decision window closes. For an opportunity a closed window ends the opportunity (route close); for an exposure a passed date means the matter is overdue (state passed, ranked with closing windows). The signal carries one date, so the two dimensions use the same date in different ways.', '10:4', 'A separate deterioration measure may be wanted; the signal contract of M5 would need it.'),
    ('I-101', 'Explainable ranking', 'The ranking is lexicographic in the order the policy names; there are no weights and no combined score. The deciding dimension and both values are stated for every line; a full tie is broken by finding id and says so.', '10:4; PG-RS-AC-01', 'If weights are wanted, the explanation would need the contribution of each factor; a policy change, not a code change of the lifecycle.'),
    ('I-102', 'Net benefit', 'A net benefit is stated only from an expected benefit and every incremental cost that a person entered, each with a basis. The finding amount (exposure or opportunity) is shown as potential gross, never as a benefit.', '10:6; 05:10', 'None for safety; the owner must enter the figures for every action.'),
    ('I-103', 'Overlapping benefits', 'Inside an overlap component (the M5 rule: same overlap group, a shared stored record, or a person\'s financial_overlap link) only the recommendation with the largest potential gross is counted in the totals; the others are listed as overlapping. Totals are per interpretation and never added across interpretations.', '10:6; 06:9; PG-RS-AC-04', 'The counted amount is a lower bound of the component, as in the M5 portfolio view.'),
    ('I-104', 'Approval authority', 'The approval role comes from policy bands on the absolute potential gross amount; an unquantified recommendation needs the highest band, because nothing shows it is small.', '10:9', 'The product owner may prefer bands on net benefit or on the commitment value.'),
    ('I-105', 'Approved, versioned baseline', 'A baseline for verification is an M4 forecast calculation that a forecast owner adopted (or explicitly promoted) in a forecast slot, that still replays, and that was adopted no later than the time the action was started.', '05:10.1', 'Some benefit types may need another baseline kind (a procurement baseline, an approved rate); the gate would accept more kinds by a change.'),
    ('I-106', 'Evidence changing while an action is in progress', 'People are already acting outside APG, which APG cannot stop: the status stays in progress, the approval is ended and the event is recorded and visible.', '10:9; 10:10', 'The product owner may want such a recommendation to move back to awaiting approval; the M5 finding lifecycle does that for findings.'),
    ('I-107', 'Closing a recommendation', 'Route close (a resolved finding, an expired opportunity) is a recommendation to close; a person records the closure with a reason. No service closes a recommendation.', '10:5', 'None for safety.'),
    ('I-108', 'Material decisions and scenarios', 'A decision is material when the potential gross reaches the policy amount; without that amount every action is treated as material. A material decision needs at least one complete alternative (all nine Section 10 section 7 items) beside the engine-generated no-action reference, and every alternative names a stored forecast calculation as its reference baseline.', '10:7; 10:7.1', 'A lower bar would let more recommendations through without a comparison.'),
    ('I-109', 'Two approval paths', 'M5 findings carry their own action approval (findings.approve_action, the M9 boundary); M7 recommendations carry theirs. M7 does not change the finding lifecycle: a finding whose action is already approved or in progress is tracked, not recommended again. Whether the two approvals should become one is for the product owner.', '06:11; 10:9', 'Duplicate approvals for one action until the product owner decides.'),
]

EDR = dict(edr_id='EDR-33', port='RecommendationWorkflowPort', title='Map the recommendation lifecycle to the Anchor finding, workflow, Governor and audit contracts',
           what_apg_needs='Section 10 section 12 asks that the recommendation lifecycle (ten statuses, gated submission, bound approval, verification) use the actual Anchor workflow, Governor and audit contracts found in Section 01 discovery. APG-M7 implements the lifecycle as APG records over the M2 store; the Engine is needed for: who may hold each approval role per project (the bands name roles only), notification of approvers, the screen and API, and the Governor checks of a consequential approval.',
           why_the_engine_is_needed='Roles, workflow, notification, Governor and the API layer belong to the Engine. APG has none of them and assumes none.',
           contract_summary='To be agreed with the Engine: map each M7 status and act to an Engine workflow step; supply the role directory per project (as EDR-11 and EDR-31 for findings); carry the approval token (version, digest, submission reference) unchanged through the API.',
           contract_test='None written: no Engine contract is known. The M7 tests run against the in-memory reference store only.',
           blueprint_refs='10:9; 10:12; 02:7', capabilities='CAP-27; CAP-28; CAP-29; CAP-30', needed_by_milestones='M9; M10; M12',
           decisions_for_amir='Whether recommendations become Engine workflow items or stay APG records; where approval roles per project are held; how the Governor sees a consequential approval.',
           owner='Amir (engine, database, environment)', status='Open - described only', evidence_seen='No Engine code, repository or environment seen; no implementation exists')

CF = dict(cf_id='CF-32', audit_section='', topic='Independent verification of APG-M7 and the earlier regression tools',
          what_remains_open='APG-M7 is builder-implemented and builder-tested only. The per-release regression tools of M6 to M9.4 were not changed in M7: each checks its own release, so run on this package they report the M7 files as undeclared additions (for example R04 of run_regression_m94.py). Run them on their own delivered ZIPs.',
          what_this_package_shows='tools/run_regression_m7.py checks the M7 delta against the delivered M9.4 package (a stored manifest of its 795 files); the whole unit suite, including every earlier test, passes unchanged.',
          linked_records='SR-90 to SR-97; I-99 to I-109; EDR-33', who_must_act='Auditor: independent review of APG-M7', status='Open - for the auditor')

if __name__ == '__main__':
    add('STATUS_REGISTER.csv', 'item_id', STATUS)
    add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=i, milestone='M7', topic=t, builder_reading=b, blueprint_ref=r, effect_if_wrong=e, status=RETAINED) for i, t, b, r, e in INTERP])
    add('ENGINE_HANDOFF_REGISTER.csv', 'edr_id', [EDR])
    add('CARRIED_FORWARD_REGISTER.csv', 'cf_id', [CF])
    header, rows = rd('PROGRAMME_MILESTONES.csv')
    for r in rows:
        if r['milestone_id'] == 'M7':
            r['status'], r['handoff_register_entries'] = 'In this delivery (draft, builder-tested; not independently reviewed)', 'EDR-33'
    wr('PROGRAMME_MILESTONES.csv', header, rows)
