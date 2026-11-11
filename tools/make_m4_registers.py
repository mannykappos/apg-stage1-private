#!/usr/bin/env python3
"""Adds the M4 rows to the programme tables.  Usage: make_m4_registers.py <programme_dir>
Runs AFTER make_m0.py and make_m3_registers.py (which write the M0 to M3 content).  It is idempotent: a row whose id already exists is left alone.  It changes two existing rows
only: the status of milestone M3 (delivered) and of M4 (in this delivery) and the M4 handoff list.  Nothing here closes a finding, approves an interpretation or settles a decision."""
import csv, os, sys
P = sys.argv[1]
SRC = 'Blueprint Section 05; Section 12; Section 03 sections 4 to 6; CR-02 preparation brief items A2 to A13 (not approved text)'


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
        return                                         # make_m0.py regenerates only the three tables; the findings and interpretations files are written by make_m3_registers.py
    header, rows = rd(name)
    have = {r[idcol] for r in rows}
    for row in new:
        if row[idcol] not in have:
            rows.append({k: row.get(k, '') for k in header})
    wr(name, header, rows)


NOENGINE = 'No Engine code, repository or environment seen; no implementation exists'
OWNER = 'Amir (engine, database, environment)'
EDR = [
    dict(edr_id='EDR-24', port='SnapshotReadPort', title='Consistent project-scoped and time-scoped reads for calculations',
         what_apg_needs='Read the records one calculation needs (all records of a few kinds that belong to one project, plus the tenant-wide facility and bank kinds) as of one consistent read point, with the revision and payload hash of each, and read any older revision by key and revision number.',
         why_the_engine_is_needed='The reference store has no project index and no read point: the gatherer lists every record of a kind for the tenant and filters in memory. At the size of a real builder this must be indexed and consistent, and only the Engine database can do that.',
         contract_summary='Operations: read_snapshot(context, kinds, filters, read_point) -> records with kind, key, revision, payload and payload hash; get_revision(context, kind, key, revision). Invariants: two reads at the same read point return identical results even if writes happen between them; a write after the read point is not visible; superseded revisions stay readable; no cross-tenant results; the result carries enough to pin each record (revision and hash).',
         contract_test='snapshot_read_contract (to be written with M11): colliding keys across tenants; a write after the read point is invisible; a superseded revision is still returned by revision number; the pinned hash equals the stored hash; results are stable under concurrent writes.',
         blueprint_refs='05:13; 04:16; 14:14.10', capabilities='CAP-31; CAP-10; CAP-11', backlog_ids='', needed_by_milestones='M4; M5; M9',
         decisions_for_amir='Read-point mechanism (transaction snapshot, revision watermark or timestamp); indexes for project-scoped reads; whether a calculation runs inside one database transaction.', owner=OWNER, status='Open - described only', evidence_seen=NOENGINE),
    dict(edr_id='EDR-25', port='BankDataFeedPort', title='Bank transaction and facility statement feed with provenance',
         what_apg_needs='Receive bank transactions and funding facility statements (rate, limit, drawn, statement date) from the builder\'s bank or accounting system, each with its source, statement date and a stable identifier, so that a retention receipt can be tied to a stored bank transaction of exactly that amount and a carrying cost can use an evidenced rate.',
         why_the_engine_is_needed='The route to bank data (file export, accounting-system feed or open banking) and the credentials for it belong to the Engine and the builder\'s systems; the legal basis for the route is not confirmed. M4 reads a CSV delivery of the same shape.',
         contract_summary='Input: a delivery of transactions or facility statements with source identity. Output: stored bank_txn and facility records with idempotent keys (transaction id; facility id and statement date). Invariants: a repeated delivery adds nothing; a changed amount under the same id is held as a conflict; amounts are signed integer cents; a statement dated after its delivery is held.',
         contract_test='bank_feed_contract (to be written with M8): repeated delivery; conflicting amount; future-dated statement; negative and positive amounts; two facilities.',
         blueprint_refs='12:12.4; 12:12.7; 04:5', capabilities='CAP-11; CAP-02', backlog_ids='', needed_by_milestones='M4; M8',
         decisions_for_amir='Which route is used per builder; how a statement is dated; how several facilities are told apart (M4 refuses to choose between them).', owner=OWNER, status='Open - described only', evidence_seen=NOENGINE),
    dict(edr_id='EDR-26', port='ReceivablesFeedPort', title='Client invoices, certificates and receipts',
         what_apg_needs='Receive client-side data: progress claims or certificates, client invoices with due dates, and receipts, so that overdue receivables (a component of the cash-position-adjusted margin) can be assessed.',
         why_the_engine_is_needed='The data lives in the builder\'s accounting or project system and arrives through connectors and credentials that the Engine owns. M4 has no receivables data at all, so that component always reports that it cannot be assessed.',
         contract_summary='Input: client invoice, certificate and receipt deliveries with source identity. Output: stored records keyed by their own identifiers, with revisions. Invariants: the same rules as the supplier-side deliveries (duplicate, revision, stale, conflict); a receipt is matched to an invoice only by an explicit reference, never by amount alone.',
         contract_test='receivables_feed_contract (to be written with M8): duplicate receipt; receipt for an unknown invoice; partial receipt; credit against a client invoice.',
         blueprint_refs='12:12.4; 05:5', capabilities='CAP-11; CAP-10', backlog_ids='', needed_by_milestones='M4; M5; M8',
         decisions_for_amir='Which systems supply client-side data; certificate versus invoice as the receivable event; legal basis for the route.', owner=OWNER, status='Open - described only', evidence_seen=NOENGINE),
    dict(edr_id='EDR-27', port='InputChangeNotificationPort', title='Tell dependants when a pinned input gets a new revision',
         what_apg_needs='When a record that a stored calculation pinned receives a newer revision, mark the calculation as having newer inputs and let a job recompute it, without altering the stored calculation.',
         why_the_engine_is_needed='Finding the calculations that depend on a record needs a reverse index and an event on write, both of which are database features. M4 can report newer inputs when asked (drift report) but cannot find dependants cheaply or trigger anything.',
         contract_summary='Operations: subscribe(kind, key pattern), list_dependants(kind, key, revision) -> run keys. Invariants: a write of a new revision produces one notification per dependant; a stored calculation is never changed by it; notifications are tenant-scoped and audited; a job (EDR-04) performs the recompute.',
         contract_test='input_change_contract (to be written with M9): new revision notifies exactly the dependants; no notification for an identical re-delivery; no cross-tenant notification.',
         blueprint_refs='05:13; 04:7', capabilities='CAP-31', backlog_ids='', needed_by_milestones='M4; M5; M9',
         decisions_for_amir='Whether dependants are found by an index table or by scanning pinned inputs; how often recomputation may run.', owner=OWNER, status='Open - described only', evidence_seen=NOENGINE),
]
SRROWS = [
    ('SR-24', 'Financial figure model, integer arithmetic and the calculation policy (open CR-02 decisions as configuration with no default)', 'tests/test_fin_arith.py; tests/test_fin_static.py; mutation run',
     'Policy values in the demonstration are SYNTHETIC and illustrative; no CR-02 decision (A2 to A13) is made or approved'),
    ('SR-25', 'Financial intake: projects, contracts, variations, cost-to-complete lines, retention, security instruments, facility, bank transactions, with templates', 'tests/test_fin_intake.py; fin_templates/; corpus cases R03 to R10; mutation run',
     'Templates are Builder Zero shapes; no real export has been mapped; the intake loop repeats the M3 loop (finding F-16)'),
    ('SR-26', 'Actual cost, commitments and secured revenue with credits, duplicates, held records and unattributable records stated in every figure', 'tests/test_fin_costs.py; tests/test_fin_commitments.py; tests/test_fin_revenue.py; golden cases; corpus K, C and V cases; mutation run',
     'Cost scope is supplier invoices only (finding F-17); the reconciliation register used is SYNTHETIC'),
    ('SR-27', 'Forecast final cost and margin, cost to complete by method, recognised margin and cash-position-adjusted margin, kept as distinct views', 'tests/test_fin_forecast.py; tests/test_fin_cash.py; golden cases; independent oracle; corpus F, M and R cases; mutation run',
     'Methods are configuration; the demonstration policy is illustrative; no accounting-standard compliance is asserted'),
    ('SR-28', 'Retention pools with evidenced events, security instruments, carrying cost on a stated rate and the review flags that never move money', 'tests/test_fin_cash.py; corpus R cases; mutation run',
     'Forward carrying cost only; no balance history, no receivables data (finding F-18); roles are the builder\'s names (interpretation I-23)'),
    ('SR-29', 'Forecast movement bridge that reconciles exactly and lists unexplained movements; forecast book with one authoritative forecast per slot and isolated scenarios', 'tests/test_fin_bridge_book.py; golden bridge case; mutation run',
     'No materiality threshold is applied (CR-02 A1 is open); adoption roles are the builder\'s names'),
    ('SR-30', 'Immutable calculation records: pinned inputs, replay, formula-drift detection, input-versus-rule diff, explain', 'tests/test_fin_records.py; golden cases (27 stored runs replay); mutation run',
     'Tamper-evident, not tamper-proof (finding F-20); never run on an Engine store'),
    ('SR-31', 'M4 golden cases with an independent oracle, faulty-input corpus, narrated demonstration and regression against the delivered M3 package', 'tools/run_golden_fin.py; tools/run_fin_corpus.py; tools/run_demo_m4.py; tools/run_regression_m4.py',
     'Golden values come from the builder\'s own code plus an oracle written by the same builder; no independent review'),
    ('SR-32', 'M4 mutation run over the financial-core modules with a single-interpreter runner', 'tools/m4_mutants.py; tools/mut_runner.py',
     'Shows the tests detect one-place changes of the kinds listed; says nothing about changes of other kinds'),
]
FIND = [
    ('F-14', 'Builder (M4)', 'M4', 'The M3 project-filtered cost view skips conflict markers',
     'The M3 invoice cost view, when given a project, reads each record\'s project field and a conflict marker has none, so a conflicted invoice would silently drop out of one project\'s figure. The unfiltered tenant total is correct and is unchanged.',
     'M3 apg/ingest/views.py; snap.project_of', 'M3 is not changed. M4 attributes records with one rule shared by the gatherer and the calculations; a conflict marker whose versions name one project counts as held on that project, and one that names several is listed as unattributed on every project.', 'Handled in the package (M3 files unchanged)'),
    ('F-15', 'Builder (M4)', 'M4', 'The M4 tests found defects in the builder\'s own first drafts',
     'While writing tests, five defects in the first drafts were found and corrected: retention events were not read when a calculation gathered its inputs; a set of security instruments that were all held showed zero instead of unknown; the percentage calculation quietly used forecast revenue for any unrecognised denominator; a negative retention balance, cost-to-complete, facility figure or project value was accepted; a figure that was not authoritative could carry no reason.',
     'tests/test_fin_cash.py; tests/test_fin_bridge_book.py; tests/test_fin_intake.py; tests/test_fin_arith.py', 'Each has a test that fails on the earlier behaviour. The figure rule is now: a figure that is not authoritative must say why, and a parent names the component it is waiting on.', 'Handled in the package'),
    ('F-16', 'Builder (M4)', 'M4', 'The financial intake repeats the M3 delivery loop',
     'To leave M3 files unchanged, apg/fin/intake.py repeats the M3 file-ingestion loop for the new entities. Two copies can drift apart.',
     'apg/ingest/pipeline.py; apg/fin/intake.py', 'Recommended after M4: one loop that takes the entity rules as an argument. Not done here because it would change delivered M3 files.', 'Carried to a later milestone'),
    ('F-17', 'Builder (M4)', 'M4', 'Cost scope is supplier invoices only',
     'Labour, plant, accruals and overhead are not in any M4 cost figure. Builder Zero has timesheet and plant files but M4 does not ingest them, and what counts as cost is open decision CR-02 A5.',
     'CR-02 A5; policy field cost_scope', 'Every cost figure carries a limit saying so. The policy field has one allowed value today.', 'Open - for the product owner (CR-02 A5)'),
    ('F-18', 'Builder (M4)', 'M4', 'No receivables data and no balance history',
     'Without client invoices, certificates and receipts the overdue-receivables component always reports that it cannot be assessed. Without a history of retention balances only a forward carrying cost can be estimated.',
     'EDR-26; EDR-25; CR-02 A2; CR-02 A7', 'A cash-adjusted margin whose policy lists the receivables component cannot be assessed, by design. The default demonstration policy lists only the retention carrying cost.', 'Open - handoff entries EDR-25 and EDR-26'),
    ('F-19', 'Builder (M4)', 'M4', 'A rejected row leaves no trace in a figure',
     'A row refused at intake (for example an invoice with a blank amount) is never stored, so no figure can list it. It appears on the intake receipt only.',
     'Section 04 section 7; M3 receipts', 'A later data-health view (M9, M10) must show rejected rows next to the figures they would have changed. Until then a reader must check the receipts.', 'Carried to M9'),
    ('F-20', 'Builder (M4)', 'M4', 'Calculation records are tamper-evident, not tamper-proof',
     'Hashes detect a changed result, changed parameters or a changed pinned input. A writer who can delete a record, or who can write a different record under a new key, is not stopped by them.',
     'EDR-20; EDR-21; EDR-02', 'The new record kinds (fin_policy, retention_event, fin_forecast_slot, repro_record and the financial entities) need the kind-level write authorisation and the audit anchor already described in EDR-20 and EDR-21; those entries are unchanged.', 'Open - handoff entries EDR-20 and EDR-21'),
    ('F-21', 'Builder (M4)', 'M4', 'The gatherer lists every record of a kind',
     'To pin a project\'s records the gatherer lists all records of each needed kind in the tenant and filters in memory. That is fine for Builder Zero and wrong at the size of a real builder.',
     'EDR-24', 'Described in EDR-24 with the read operations required.', 'Open - handoff entry EDR-24'),
    ('F-22', 'Auditor (M3 review)', 'M4', 'The M3 wrapper and the 561-mutant run were too slow to reproduce in one sitting',
     'The auditor could not reproduce run_m3_all.py or the full M3 mutation run within the execution limit and therefore holds them as builder-reported.',
     'tools/run_m4_all.py; tools/m4_mutants.py; tools/mut_runner.py', 'M4 splits its checks into named groups that each run on their own (RUN_COMMANDS.txt), prints the time of each step, and runs each mutant in one interpreter (the M4 mutation run can be split by module with --only). The M3 runs are unchanged.', 'Handled in the package; for the auditor to confirm'),
]
INTERP = [
    ('I-17', 'Reconciliation tolerance', 'With no tolerance configured, amounts must be exactly equal (for example a retention receipt and its bank transaction). No tolerance value is chosen.', '05:13; CR-02 A13', 'A tolerance would let a near-miss count as evidence.'),
    ('I-18', 'Forecast final cost basis', 'Forecast final cost is the actual cost up to the forecast date plus the cost to complete declared or derived at that date. Invoices dated after the forecast date are shown separately and are never added.', '05:5; CR-02 A4', 'Adding later actuals to a cost to complete that already expects them would count them twice.'),
    ('I-19', 'Carrying cost runs forward', 'Carrying cost is estimated from the as-of date to the expected release date on the funded share of the withheld balance. Cost already incurred is not estimated because no balance history is ingested. A release date that has passed with money still withheld gives cannot be assessed.', '12:7; CR-02 A7', 'A backward or flat estimate would state a cost that no evidence supports.'),
    ('I-20', 'Variation values when sources disagree', 'Secured revenue uses the variation register; when the contract summary disagrees, the figure is provisional and both numbers are listed. Submitted, disputed and rejected variations are never revenue.', '05:5; CR-02 A12', 'Using the summary instead would hide an approved variation, or count an unapproved one.'),
    ('I-21', 'Records that cannot be attributed to a project', 'A record whose project cannot be told appears as an unattributed exclusion on every project figure, so it cannot be missed. It is not added to any total.', '04:7; 05:13', 'Dropping it would hide cost; adding it would count it on the wrong project.'),
    ('I-22', 'What a total of included records means', 'A cost, commitment or revenue total is the sum of the records that can be used. If any record is held, disputed or unknown the figure is provisional and lists it. Cannot be assessed is used only when no figure can be formed at all.', '04:8; 05:13', 'Showing zero or hiding the total when one record is held would mislead in the other direction.'),
    ('I-23', 'M4 role names and separation of duties', 'The roles policy_owner, forecast_owner, retention_clerk and retention_approver are the builder\'s names, like I-2. Whoever proposes a policy cannot approve it; whoever runs a forecast cannot adopt it; approval, release and receipt of retention need the approver role and a human.', '03:6; 12:4', 'Different names or weaker separation change who can make a figure authoritative or move retention between states.'),
    ('I-24', 'Recognition method', 'Cost-to-cost is the only method implemented (recognised revenue is secured revenue times cost to date over forecast final cost). Selecting a method is a policy choice; with none selected there is no recognised margin.', '05:5; CR-02 A5', 'A different method (for example certified progress) gives a different recognised margin.'),
    ('I-25', 'Demonstration policy', 'Every method, funded share and freshness limit in the demonstration policy is the builder\'s illustrative choice. The policy has no default for any open decision; an unset one gives cannot be assessed and names the decision.', 'CR-02 A2 to A13', 'Treating the demonstration values as defaults would settle open decisions.'),
    ('I-26', 'Cost-to-complete methods', 'Three methods are offered as configuration: declared, budget less actual, and declared else budget less actual. A held declared line is never replaced by a budget figure. A budget already exceeded gives an unknown cost to complete, never a negative one.', '05:5; CR-02 A3', 'Falling back silently would hide a disputed estimate; a negative figure would understate cost.'),
    ('I-27', 'Retention pools', 'Retention moves withheld, claimed, approved, released, received with a disputed side state, one evidenced event at a time. Released is not received; received needs a bank transaction of exactly that amount. A due date passing moves nothing and only raises a review flag.', '12:4; 12:8', 'Promoting a state on a date would assert entitlement or cash that no one has evidenced.'),
    ('I-28', 'Movement bridge', 'The bridge splits the change in forecast margin into items that add up to it exactly. A newly counted record or a recorded reason explains an item; a method change, a changed amount or a blank reason does not. No materiality threshold is applied.', '05:8; CR-02 A1', 'A threshold would hide small unexplained movements; none is chosen.'),
    ('I-29', 'Commitments', 'Open commitment is the committed amount less what is invoiced, never below zero, with any overrun shown separately. Unapproved amendments are exposure, not commitment. Draft and cancelled orders are not commitments.', '05:5; CR-02 A12', 'Counting exposure as commitment would overstate the cost to come.'),
]
header, rows = rd('PROGRAMME_MILESTONES.csv')
for r in rows:
    if r['milestone_id'] == 'M3':
        r['status'] = 'Delivered - builder-checked'
    if r['milestone_id'] == 'M4':
        r['status'] = 'In this delivery'
        r['handoff_register_entries'] = 'EDR-24; EDR-25; EDR-26; EDR-27'
wr('PROGRAMME_MILESTONES.csv', header, rows)
add('ENGINE_HANDOFF_REGISTER.csv', 'edr_id', EDR)
add('STATUS_REGISTER.csv', 'item_id', [dict(item_id=i, item=t, milestone='M4', evidence_ladder_status='Local-tested', evidence=e, claim_limit=c) for i, t, e, c in SRROWS])
add('FINDINGS_REGISTER.csv', 'finding_id', [dict(finding_id=a, raised_by=b, milestone=c, title=d, description=e, linked_items=f, how_it_is_handled_here=g, status=h) for a, b, c, d, e, f, g, h in FIND])
add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=a, milestone='M4', topic=b, builder_reading=c, blueprint_ref=d, effect_if_wrong=e, auditor_note='', status='Retained for review - not approved', reviewer_decision='')
                                                           for a, b, c, d, e in INTERP])
print('M4 rows added')
