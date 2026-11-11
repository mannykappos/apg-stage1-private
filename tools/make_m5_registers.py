#!/usr/bin/env python3
"""Adds the M5 rows to the programme tables.  Usage: make_m5_registers.py <programme_dir>
Runs AFTER make_m0.py, make_m3_registers.py and make_m4_registers.py.  Idempotent: a row whose id already exists is left alone.  It changes three existing rows only: the status of
milestone M4 (delivered) and M5 (in this delivery) with the M5 handoff list, and the entry EDR-10 (contract test written in M5).  Nothing here closes a finding, approves an
interpretation or settles a decision."""
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
        return                                         # make_m0.py regenerates only the three tables; the findings and interpretations files are written by the earlier register generators
    header, rows = rd(name)
    have = {r[idcol] for r in rows}
    for row in new:
        if row[idcol] not in have:
            rows.append({k: row.get(k, '') for k in header})
    wr(name, header, rows)


NOENGINE = 'No Engine code, repository or environment seen; no implementation exists'
OWNER = 'Amir (engine, database, environment)'
EDR = [
    dict(edr_id='EDR-28', port='RecipientDirectoryPort', title='Resolve an alert recipient role to named people, with preferences and a fallback',
         what_apg_needs='Turn the recipient ROLE on a notification (for example the responsible role or the reviewer role of a finding) into the named people who hold it for that tenant and project, with their channel preference, and say so visibly when nobody holds the role.',
         why_the_engine_is_needed='Who holds a role, how they want to be reached and who covers an absence belong to the Engine user and organisation model. M5 notes carry a role only; the reference notifier delivers to a role name and has no people behind it.',
         contract_summary='Operations: resolve(context, role, project) -> list of {person, channel} or an empty list that the caller must treat as an undelivered alert. Invariants: tenant-scoped; no cross-tenant person; an empty answer is visible (never a silent drop); a person is never added by APG; the answer is time-stamped so a delivery can be explained later.',
         contract_test='recipient_directory_contract (to be written with M9): empty role; role held in another tenant only; two holders; holder removed between two calls; project-specific holder.',
         blueprint_refs='02:8; 06:9.1; 03:6', capabilities='CAP-08; CAP-21', backlog_ids='', needed_by_milestones='M5; M9; M10',
         decisions_for_amir='Which source defines role holders; how a project-specific holder is expressed; fallback when a role is empty (escalate to which role).', owner=OWNER, status='Open - described only', evidence_seen=NOENGINE),
]
SRROWS = [
    ('SR-33', 'Detection policy: every threshold, tolerance, window and pairing is configuration with no default; a rule without its parameters records not_configured and names them', 'tests/test_det_policy.py; tests/test_det_static.py; mutation run',
     'Policy values in the demonstration are SYNTHETIC and illustrative; no threshold has product-owner approval for any real builder; no CR-02 or DEC-A1 decision is made'),
    ('SR-34', 'Detection intake: quotes, purchase orders, amendments, notices, delay events, timesheets, plant hire, compliance, defects and work output, with templates', 'tests/test_det_intake.py; det_templates/; corpus cases; mutation run',
     'Templates are Builder Zero shapes; no real export has been mapped; the M4 delivery loop is now shared through a specs parameter (finding F-23)'),
    ('SR-35', 'Cost and commercial rules R01, R02, R03, R04, R04B, R05, AGG, R09 and data-integrity signals D01 and D02, each with a run record', 'tests/test_det_rules_cost.py; tests/test_det_rules_commercial.py; golden cases; independent oracle; corpus; mutation run',
     'Cost scope is supplier invoices only (F-17); invoices carry an amount only (F-09); the movement bridge is not consulted by R09; AGG severity is value at stake (F-27)'),
    ('SR-36', 'Operations rules R06 compliance expiry, R07 quote against a declared comparable, R08 plant on hire, DLY delay overlap, LAB labour output, DEF repeat defects', 'tests/test_det_rules_ops.py; golden cases; independent oracle; corpus; mutation run',
     'R07 uses pairs a person declared; the comparability and landed-cost model is M6; delay holding cost is not quantified; labour is hours-based at package level only'),
    ('SR-37', 'Signals and detection runs: identity, evidence, amount labels, separate severity, urgency and confidence, material-change digest, reproducible project and tenant formulas', 'tests/test_det_detect.py; tests/test_det_static.py; mutation run',
     'A run that finds nothing says what was assessed and what was not; absence of an alert is not evidence that nothing is wrong'),
    ('SR-38', 'Finding lifecycle: ten statuses, role gates, human-only transitions, separation of duties on action approval, reopening on changed evidence, no path to a realised saving', 'tests/test_det_findings.py; corpus; mutation run',
     'Role names are the builder\'s (I-30); there is no per-project or per-object permission (F-31); nothing carries out an action'),
    ('SR-39', 'Alert-noise control and the NotificationPort: dedup keys, suppression window, re-notify events, pending notifications flushed with failures kept visible; contract suite, reference double and 15 faulty notifiers', 'tests/test_det_noise.py; tests/test_det_contracts.py; tools/run_m5_contracts.py; tools/run_m5_faults.py; mutation run',
     'The reference notifier is a test double, not a design; delivery to people is Engine work (EDR-10, EDR-28)'),
    ('SR-40', 'Monitor: event trigger, sweep, health report with failures logged and partial failure visible', 'tests/test_det_monitor.py; mutation run',
     'Runs when called; scheduling and event delivery are Engine work (EDR-04, EDR-27)'),
    ('SR-41', 'Overlap components and portfolio view with lower and upper bounds per interpretation, never summed', 'tests/test_det_portfolio.py; golden cases; mutation run',
     'Overlap is found from shared groups, shared evidence and human links only; the bounds are arithmetic, not a forecast'),
    ('SR-42', 'M5 golden cases with an independent csv-only oracle, 75-case faulty-input corpus, narrated demonstration and regression against the delivered M4 package', 'tools/run_golden_det.py; tools/run_det_corpus.py; tools/run_demo_m5.py; tools/run_regression_m5.py',
     'Golden values come from the builder\'s own code plus an oracle written by the same builder; synthetic data only; no independent review'),
    ('SR-43', 'M5 mutation run over the detection modules with a single-interpreter runner', 'tools/m5_mutants.py; tools/mut_runner.py',
     'Shows the tests detect one-place changes of the kinds listed; says nothing about changes of other kinds'),
]
FIND = [
    ('F-23', 'Builder (M5)', 'M5', 'The aggregation key list changes what the aggregation rule reports, and the demonstration departs from the Builder Zero file',
     'test_thresholds.json lists the aggregation key as the project alone. With that key 96 of 101 orders count as material (F-01), so the rule would report almost everything. The demonstration policy therefore groups by project, supplier, material and cost code. This is the builder\'s illustrative choice and the open decision DEC-A1-8 is not made.',
     'DEC-A1-8; F-01; apg/det/demo_det.py', 'The policy has no default for the key list; the demonstration says in its ORIGIN table which values come from the file and which are the builder\'s own. Splitting a chain of orders each inside the window of the next is not detected (OQ-A1-7).', 'Open - for the product owner (DEC-A1-8)'),
    ('F-24', 'Auditor (M4 review)', 'M5', 'Carry-forward from the M4 review: verification limits and two weakly justified mutation survivors',
     'The auditor passed the golden, corpus, register and M3 regression checks (201 frozen files byte-identical) but did not reproduce the full M4 wrapper or the 672-mutant run, and holds those as builder-reported. Two M4 survivors (MG-CMP-004 and CO-BOL-013) are justified only by "no input found", which is weaker evidence than a proof of equivalence.',
     'M4 review; tools/m4_mutants.py', 'M4 is kept as delivered and is not edited. The M5 mutation run splits by module (--only) so that any part can be reproduced alone, and the M5 equivalents each state the evidence. The two M4 survivors stay on this register.', 'Carried forward - for the auditor'),
    ('F-25', 'Auditor (M4 review)', 'M5', 'Carry-forward from the M4 review: the financial figures are not a complete or authoritative construction ledger',
     'Actual cost is supplier invoices only. Labour, plant, accruals and overhead are outside every M4 cost figure, and all validation so far is on synthetic data. The unresolved financial policies (revenue recognition, cost to complete, tax, commitment statuses, carrying cost, cash-adjusted margin) stay configuration decisions. EDR-24 scalability remains open.',
     'F-17; F-18; F-21; EDR-24; CR-02 A2 to A13', 'Every M5 amount that builds on an M4 figure says which figure it used and carries the same cost-scope limit. M5 does not treat any M4 figure as final.', 'Open - for the product owner (CR-02 A5 and others)'),
    ('F-26', 'Builder (M5)', 'M5', 'The M4 financial intake loop is now shared',
     'M4 finding F-16 recorded that apg/fin/intake.py repeated the M3 delivery loop. In M5 the loop takes the entity rules as an argument (a specs parameter) and the detection intake calls it, so there is no third copy. This is the one M4 file changed in M5, so the M4 mutation run for that module has to be repeated.',
     'F-16; apg/fin/intake.py; apg/det/intake.py; tools/mut_runner.py', 'The regression against the delivered M4 package lists apg/fin/intake.py and tools/mut_runner.py as the changed files and requires every other M4 file to be byte-identical.', 'Handled in the package; for the auditor to confirm'),
    ('F-27', 'Builder (M5)', 'M5', 'The aggregation severity is the value of the orders, not a loss',
     'A cluster of split orders is reported at the severity of the aggregate order value, which is value at stake. No loss has been shown. The amount is labelled as a record amount, not as an estimate of loss.',
     'Section 06 5.4; CR-02 R5', 'The signal says so in its limits. Using a different basis would change the severity band of every aggregation finding.', 'Open - for the product owner'),
    ('F-28', 'Builder (M5)', 'M5', 'Delay holding cost cannot be quantified',
     'Overlapping delay events are reported with their overlap days, but the cost of holding the site is not estimated: there is no counterfactual and the critical path is not known.',
     'Section 07 5, 6.1', 'The signal is unquantified and states why. No amount is invented.', 'Open - needs a programme source and a decision on counterfactual'),
    ('F-29', 'Builder (M5)', 'M5', 'The comparable-quote rule relies on declared pairs',
     'R07 compares a quote with a reference only where a person declared the pair comparable. The landed-cost adjustment and the comparability gate belong to M6; until then R07 cannot find a comparison nobody declared.',
     'Section 08; M6 (PS-14, PS-15, PS-16, PS-17, PS-23, PS-25)', 'Planted scenarios PS-14, 15, 16, 17, 23 and 25 are M6 items and are not claimed here.', 'Carried to M6'),
    ('F-30', 'Builder (M5)', 'M5', 'The M5 tests found defects in the builder\'s own first drafts',
     'Three gaps were found while writing tests and are corrected: a signal was accepted although its identity or material-change digest did not match its content; a detection run for an unknown project returned an empty, clean-looking result; the contract suite did not catch a notifier that altered the content or delivered out of order until two faulty notifiers were added.',
     'tests/test_det_detect.py; tests/test_det_contracts.py; apg/det/faulty_m5.py', 'Each has a test that fails on the earlier behaviour. An unknown project now raises PROJECT_UNKNOWN.', 'Handled in the package'),
    ('F-31', 'Builder (M5)', 'M5', 'Finding permissions are by tenant role only',
     'A person holding finding_reviewer in a tenant can act on every project\'s findings in it. There is no per-project or per-object permission and no check that a reviewer is independent of the project.',
     'EDR-01; EDR-12; Section 03 6', 'Recorded as a limit. The Engine permission model decides how a role is scoped.', 'Open - handoff entries EDR-01 and EDR-12'),
    ('F-32', 'Builder (M5)', 'M5', 'Detection and the monitor read whole kinds in memory',
     'The gatherer lists every record of a kind for the tenant and the monitor lists all findings. That is fine on Builder Zero and wrong at the size of a real builder.',
     'EDR-24; F-21', 'No new port is needed beyond EDR-24, but the finding list needs the same indexing and the same read point.', 'Open - handoff entry EDR-24'),
    ('F-33', 'Builder (M5)', 'M5', 'The new stored record kinds need write authorisation',
     'det_policy, det_ingest, det_monitor_run and finding are written through the tenant-scoped store. Tamper evidence and kind-level write authorisation are as described in EDR-20 and EDR-21, which are unchanged.',
     'EDR-20; EDR-21; F-20', 'Listed so that Amir includes the four kinds when the kind-level rules are written.', 'Open - handoff entries EDR-20 and EDR-21'),
    ('F-34', 'Builder (M5)', 'M5', 'Plant, labour and compliance data have no real mapping',
     'The M5 intake handles the Builder Zero timesheet, plant hire, compliance, defect, delay and work-output shapes. How a real builder exports these, and whether the hours are paid or worked, is not known.',
     'F-17; Section 09; Section 13', 'Templates are examples; a malformed material field is rejected at intake and a malformed non-material field is held.', 'Open - needs a pilot builder export'),
    ('F-35', 'Builder (M5)', 'M5', 'Out-of-scope planted scenarios and M3 items carried here',
     'M3 findings F-09 (invoice-versus-order amount) and F-10 (identical purchase orders held before detection) were carried to M5. The first is handled by R03 for order totals; unit-price variance needs line data that invoices do not carry. The second is handled by D01, which lists held records instead of using them.',
     'F-09; F-10; D01; R03', 'The limits are stated in each signal.', 'Handled in the package; unit-price variance open'),
]
INTERP = [
    ('I-30', 'M5 role names and separation of duties', 'The roles detection_policy_owner, detection_service, finding_reviewer, finding_owner and action_approver are the builder\'s names. Only a service identity ingests detection runs; only a human can confirm, dismiss, approve, resolve or supersede; the person who proposes an action cannot approve it.', '03:6; 06:11', 'Different names or weaker separation change who can move a finding.'),
    ('I-31', 'Signal and finding identity', 'A condition is identified by rule, scope and subject. There is one finding per identity, however many runs see it; the same condition does not create a second alert.', '06:6; 06:9', 'A different identity rule would merge or split findings and change what is notified.'),
    ('I-32', 'A run always says what it did', 'Every rule yields a run record with status evaluated, not_configured, disabled or cannot_assess. Silence is never the only answer, and a rule that did not run says nothing about its findings.', '06:10', 'Treating a missing run as a clean result would hide a gap.'),
    ('I-33', 'Amount labels and separate severity, urgency and confidence', 'An amount is labelled figure, record or estimate. A signal that cannot be quantified carries a reason and no amount. Severity, urgency and confidence are three values, not one score.', '06:6; 05:8', 'A single score or an unlabelled amount would blur what is known.'),
    ('I-34', 'Threshold comparisons', 'Cost over budget, invoice over order and quote over reference use strictly exceeds, by exact cross-multiplication with no rounding. Other rules use the comparison in their description (at least, longer than, days left not more than the warning). A threshold at exactly its boundary is stated per rule in the tests.', '06:5.2', 'A different boundary changes whether a case exactly at the threshold is reported.'),
    ('I-35', 'Ten-status lifecycle and reopening', 'Detection can create a finding, update it, mark it seen and reopen a resolved or dismissed one only when the material-change digest differs. A decision made after a run is not undone by that run. No path leads to a realised saving; claim_realised refuses.', '06:6; 06:11; 05:8', 'Automatic reopening or resolution would let a rerun overrule a person.'),
    ('I-36', 'A finding that stops being detected', 'It is marked not re-detected with the date, and is never resolved automatically. A person decides.', '06:11', 'Auto-resolution would remove findings because data went missing.'),
    ('I-37', 'Portfolio and overlap', 'Findings overlap when they share an overlap group, share evidence records, or a person linked them as a financial overlap. The portfolio reports lower and upper bounds per interpretation and never sums interpretations; dismissed and superseded findings are excluded.', '06:9; 05:8', 'Summing overlapping findings would overstate the total.'),
    ('I-38', 'Labour output rule', 'Weeks are complete Monday-based weeks; the rule compares output per hour over the recent weeks with the baseline weeks at package level only. A fall of at least the configured amount is reported; its money value is labelled an estimate (hours beyond what the baseline rate needs, times the recent average recorded hourly rate) and is unquantified when rates are missing.', '09; 06:5.3', 'Partial weeks, crew-level comparison or a different rate would change which cases are reported and the estimate.'),
    ('I-39', 'Delay overlap', 'Delay events that overlap for at least the configured days are reported with the days. The cost of holding the site is not estimated.', '07:5; 07:6.1', 'An estimate would assume a critical path nobody has provided.'),
    ('I-40', 'Aggregation severity', 'The severity of a split-order cluster follows the aggregate order value (value at stake). The amount is a record amount, not a loss.', '06:5.4; CR-02 R5', 'Treating it as a loss would overstate exposure.'),
    ('I-41', 'Alert-noise control', 'A notification has a dedup key; the same key is sent once inside the suppression window; a repeat is sent again only for a new finding, a reopening, a severity increase, a status transition or material evidence. A failed delivery stays pending and visible.', '06:9.1; 06:10', 'Different re-notify events change how many alerts a person receives.'),
    ('I-42', 'Comparable quote pairs', 'R07 compares only pairs a person declared comparable. APG does not decide comparability in M5.', '08; 06:5.2', 'Inferring pairs would compare unlike items and report false savings.'),
    ('I-43', 'Demonstration thresholds', 'Every threshold and window in the demonstration detection policy is the builder\'s illustrative choice, or comes from test_thresholds.json where marked. None has product-owner approval.', '06:5.1; 06:8', 'Treating them as defaults would settle open decisions.'),
]
header, rows = rd('PROGRAMME_MILESTONES.csv')
for r in rows:
    if r['milestone_id'] == 'M4':
        r['status'] = 'Delivered - builder-checked'
    if r['milestone_id'] == 'M5':
        r['status'] = 'In this delivery'
        r['handoff_register_entries'] = 'EDR-10; EDR-28'
wr('PROGRAMME_MILESTONES.csv', header, rows)
header, rows = rd('ENGINE_HANDOFF_REGISTER.csv')
for r in rows:
    if r['edr_id'] == 'EDR-10' and 'written in M5' not in r['contract_test']:
        r['contract_test'] = 'notification_contract (written in M5, apg/det/contracts_m5.py, cases NT-*): duplicate suppressed; delivery failure visible; tenant isolation; content unaltered; order kept; malformed notes refused. Run against the in-memory reference and 15 faulty notifiers.'
        r['status'] = 'Open - contract test written'
wr('ENGINE_HANDOFF_REGISTER.csv', header, rows)
add('ENGINE_HANDOFF_REGISTER.csv', 'edr_id', EDR)
add('STATUS_REGISTER.csv', 'item_id', [dict(item_id=i, item=t, milestone='M5', evidence_ladder_status='Local-tested', evidence=e, claim_limit=c) for i, t, e, c in SRROWS])
add('FINDINGS_REGISTER.csv', 'finding_id', [dict(finding_id=a, raised_by=b, milestone=c, title=d, description=e, linked_items=f, how_it_is_handled_here=g, status=h) for a, b, c, d, e, f, g, h in FIND])
add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=a, milestone='M5', topic=b, builder_reading=c, blueprint_ref=d, effect_if_wrong=e, auditor_note='', status='Retained for review - not approved', reviewer_decision='')
                                                           for a, b, c, d, e in INTERP])
print('M5 rows added')
