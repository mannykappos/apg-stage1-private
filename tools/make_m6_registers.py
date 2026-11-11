#!/usr/bin/env python3
"""Adds the M6 rows to the programme tables and writes the RFC register.  Usage: make_m6_registers.py <programme_dir>
Runs AFTER make_m0.py, make_m3_registers.py, make_m4_registers.py and make_m5_registers.py.  Idempotent: a row whose id already exists is left alone.  It changes three existing rows only: the status of
milestone M5 (delivered) and M6 (in this delivery) with the M6 handoff list, and the entries EDR-08 and EDR-09 (contract tests written in M6).  Nothing here closes a finding, approves an
interpretation, settles a decision or approves RFC-01."""
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
        return
    header, rows = rd(name)
    have = {r[idcol] for r in rows}
    for row in new:
        if row[idcol] not in have:
            rows.append({k: row.get(k, '') for k in header})
    wr(name, header, rows)


NOENGINE = 'No Engine code, repository or environment seen; no implementation exists'
OWNER = 'Amir (engine, database, environment)'
EDR = [
    dict(edr_id='EDR-29', port='ProjectScopePort', title='The projects the caller may see, for information-boundary rules',
         what_apg_needs='For a tenant-wide purchasing comparison across projects, the checked list of projects the caller is authorised to see. M6 takes the list as a parameter and reports a portfolio comparison only when the list covers every project that bought the material in the window; it names no project outside the list.',
         why_the_engine_is_needed='Who may see which project belongs to the Engine permission model. M6 cannot decide it, and a list supplied by the caller would let the caller widen their own view.',
         contract_summary='Operations: authorised_projects(context) -> sorted list of project ids with a version or time stamp. Invariants: derived from the authenticated context and never from request input; tenant-scoped; an empty list is a valid answer and means no cross-project view; a change between two calls is visible; the list is the same one the permission layer enforces elsewhere.',
         contract_test='project_scope_contract (to be written with M9): empty set; set narrower than the buying projects; project added between two calls; project removed; a project id from another tenant; a caller-supplied list is ignored.',
         blueprint_refs='15:15.5; 03:6', capabilities='CAP-26', backlog_ids='', needed_by_milestones='M6; M9; M10',
         decisions_for_amir='How project-level permission is expressed; whether a cross-project view needs a separate permission from seeing each project; how a revoked project is handled in stored runs (finding F-39 records that tenant-run pins name order identifiers of unauthorised projects).', owner=OWNER, status='Open - described only', evidence_seen=NOENGINE),
    dict(edr_id='EDR-30', port='EventStorePort', title='Time-aware event store for the later cross-domain engine (RFC-01, proposed)',
         what_apg_needs='Persist and query the apg-event-1 events that M6 writes with each procurement condition (event type, observation time, effective time, source and provenance, project, material, supplier, evidence references), so that a later engine can relate events across domains by time. M6 writes the fields and chains nothing.',
         why_the_engine_is_needed='A time-indexed, tenant-scoped, append-only store with supersession belongs to the Engine database. It is needed from M6 only to keep the events M6 writes; the cross-domain use is the later RFC-01 engine, which is only proposed: this entry describes the need, and nothing in it has been agreed.',
         contract_summary='Operations: append(context, events) -> receipts; query(context, filter: time window on observation or effective time, project, material, supplier, event type) -> events in a stable order; supersede(context, event_id, new_event). Invariants: tenant-scoped; both times kept and never merged; nothing is deleted; a query as of a past date returns what was known then; every event keeps its source provenance and a link to the run that wrote it.',
         contract_test='event_store_contract (to be written with the milestone that builds chain detection): ordering; time-window boundaries on both times; supersession; as-of query; tenant isolation; duplicate append.',
         blueprint_refs='03:11.3; 06:9.1', capabilities='CAP-18; CAP-27', backlog_ids='', needed_by_milestones='M6',
         decisions_for_amir='Storage model and indexes for time-window queries; retention; how a person-asserted relation differs from a proposed one in storage.', owner=OWNER, status='Open - described only', evidence_seen=NOENGINE),
]
SRROWS = [
    ('SR-44', 'Procurement policy and specification register: versioned and immutable, approval needs a person who is not the proposer, no defaults, a missing parameter stops the rule and names itself', 'tests/test_mkt_policy.py; tests/test_mkt_static.py; mutation run',
     'Policy and register values in the demonstration are SYNTHETIC and illustrative; no limit, basis or specification has product-owner approval; roles are the builder\'s names (I-44)'),
    ('SR-45', 'Procurement intake: materials, demand, delivery dockets, specification requirements, quote readings, tiers and terms, landed-cost assumptions and import checks, with templates', 'tests/test_mkt_intake.py; mkt_templates/; corpus cases; mutation run',
     'Templates are Builder Zero shapes; no real export has been mapped; the supplements in mkt_data/ are synthetic and were written by the builder (F-44)'),
    ('SR-46', 'Exchange rates and freshness: latest-on-or-before rate, exact conversion rounded once per component, four decision classes with their own limits, stale and expired states', 'tests/test_mkt_fx_fresh.py; golden cases; independent oracle; corpus; mutation run',
     'Every limit is illustrative; no rate source exists (EDR-09); the reference rate for a date is whatever the file says'),
    ('SR-47', 'Comparability gate: five classes, failure from any evidence blocks, a pass needs a reading verified by someone other than the extractor, units verified or partial', 'tests/test_mkt_spec.py; tests/test_mkt_compare.py; corpus; mutation run',
     'The specification register is a demonstration; a real register is the specification owner\'s; "verified" means a named person said so, not that the product is compliant'),
    ('SR-48', 'Landed cost: purchase, freight, insurance, duty, clearance and handling by delivery basis, tiers and terms, foreign conversion, explicit missing components', 'tests/test_mkt_landed.py; golden cases; independent oracle; corpus; mutation run',
     'Allowances are entered by a person; duty and clearance are not looked up; GST is treated as a stated basis only (I-49); no freight rate source'),
    ('SR-49', 'Ranking and the recommendation gate: definitive, indicative, insufficient or no offers; may_recommend is the only gate; human approval always required', 'tests/test_mkt_compare.py; tests/test_mkt_corpus.py; golden cases; mutation run',
     'Nothing in M6 names a winner or recommends a purchase; "definitive" means only that the gates passed on the stored records (I-46, F-45)'),
    ('SR-50', 'Demand coverage and over-ordering, including possible duplicate orders and units that do not match', 'tests/test_mkt_demand.py; tests/test_mkt_rules.py; golden cases; mutation run',
     'The matching window and the surplus tolerance are illustrative (I-50); order units are never converted; a surplus is an exposure, not a loss'),
    ('SR-51', 'Scenario generator: buy now, wait (policy price paths only), stage and negotiate, each with storage, financing, schedule and evidence gaps; writes nothing', 'tests/test_mkt_scenarios.py; golden cases; independent oracle; corpus; mutation run',
     'Scenarios are arithmetic on stated assumptions, not forecasts; no price is predicted; scenarios never change the official forecast and are never ranked against each other'),
    ('SR-52', 'Opportunities and the savings gate: an opportunity is an unapproved estimate against the last paid rate; claim_saving always refuses', 'tests/test_mkt_opportunities.py; corpus; mutation run',
     'The last paid rate is not an approved baseline (I-52); no saving is verified or realised; verification needs the Section 05 evidence that is not built'),
    ('SR-53', 'Supplier performance and portfolio purchasing, with the information boundary', 'tests/test_mkt_opportunities.py; tests/test_mkt_rules.py; corpus; mutation run',
     'Supplier levels are observations, not rankings; portfolio gaps are weak estimates; the Builder Zero rate gaps are artefacts of random synthetic order rates (F-44); the boundary depends on EDR-29'),
    ('SR-54', 'International safeguards: critical checks listed by name, resolution needs a person, a date and evidence, no compliance claim', 'tests/test_mkt_rules.py; tests/test_mkt_static.py; corpus; mutation run',
     'The list of critical checks is illustrative; APG does not decide customs, permits or duty; legal and customs confirmation is outside the build'),
    ('SR-55', 'Rules MP01 to MP10 and MPD1 with run records, the two reproducible formulas (project, tenant), and findings through the unchanged M5 lifecycle', 'tests/test_mkt_rules.py; tests/test_mkt_detect.py; golden cases; mutation run',
     'A run that finds nothing says what it assessed and what it could not; absence of a signal is not evidence that nothing is wrong'),
    ('SR-56', 'Event hooks (apg-event-1): observation time, effective time, source provenance, project, material and supplier on procurement conditions, for the later engine', 'tests/test_mkt_rules.py; tests/test_mkt_detect.py; golden cases',
     'Hooks only. No relationship is stored and no chain is detected; RFC-01 is proposed, not approved; the event store is EDR-30'),
    ('SR-57', 'Port contracts for EDR-09 (market feed, 13 cases) and EDR-08 (extraction, 11 cases), reference test doubles and 25 faulty implementations', 'tests/test_mkt_contracts.py; tools/run_m6_contracts.py; tools/run_m6_faults.py',
     'The feed holds only what a test loads and names no provider; the extractor wraps the M3 text stand-in and was run on no PDF, scan or e-mail; both are test doubles, not designs'),
    ('SR-58', 'M6 golden cases with an independent csv-only oracle, 78-case faulty-input corpus, narrated demonstration and regression against the delivered M5 package', 'tools/run_golden_mkt.py; tools/run_mkt_corpus.py; tools/run_demo_m6.py; tools/run_regression_m6.py',
     'Golden values come from the builder\'s own code plus an oracle written by the same builder; synthetic data only; the corpus is not yet storage-neutral (F-49); no independent review'),
    ('SR-59', 'M6 mutation run over the procurement modules with a single-interpreter runner, and the repeat of the M5 run for the four M5 files M6 changed', 'tools/m6_mutants.py; tools/m5_mutants.py; tools/mut_runner.py',
     'Shows the tests detect one-place changes of the kinds listed; says nothing about changes of other kinds; the builder\'s own figures, not independently reproduced'),
    ('SR-60', 'Correction of the M5 portfolio display (M5 review, issue 1): when nothing is quantified the headline says "no quantified amount available", never a range of zero', 'tests/test_det_portfolio.py; tools/run_demo_m5.py; tools/run_regression_m6.py',
     'This changes four M5 code files, one M5 test file and the M5 demonstration output; they are recorded as baseline-changed (F-46). The auditor confirms the correction'),
    ('SR-61', 'RFC-01 recorded as PROPOSED in programme/RFC_REGISTER.csv with its scope, evidence levels, conflicts, unresolved decisions and approvals', 'programme/RFC_REGISTER.csv; programme/RFC-01_LATENT_RISK_AND_INTERVENTION_ENGINE.md; tools/programme_check_m6.py',
     'A record, not an approval: the locked sections, CR-09 and its change register, the RTM and every historical hash are unchanged'),
]
FIND = [
    ('F-36', 'Auditor (M5 review)', 'M6', 'The M5 portfolio could print $0-$0 for exposure that is unquantified',
     'The M5 demonstration prints "between $0.00 and $0.00" for an interpretation with two findings and none quantified. The findings were listed separately as unquantified, so nothing was calculated as zero, but the headline could read as no exposure.',
     'M5 review issue 1; apg/det/portfolio.py; tools/run_demo_m5.py', 'Corrected in M6: the portfolio now carries range_display and quantified_amount_available; with nothing quantified the headline reads "no quantified amount available ... this is not zero exposure". Four M5 code files, one M5 test file and the M5 demonstration output changed (F-46); new tests cover it.', 'Handled in the package; for the auditor to confirm'),
    ('F-37', 'Auditor (M5 review)', 'M6', 'Carry-forward from the M5 review: split-order detection still depends on an unresolved grouping decision',
     'The aggregation key changes the M5 result substantially; the demonstration uses project, supplier, material and cost code, while the Builder Zero threshold file groups by project alone. M6 does not change the key and adds no grouping of its own that is presented as a default.',
     'DEC-A1-8; F-01; F-23; F-27', 'Retained as an open product-owner decision. M6\'s own grouping choices (demand matching, duplicate window, portfolio grouping) are logged as interpretations I-50 and I-53, not defaults.', 'Open - for the product owner (DEC-A1-8)'),
    ('F-38', 'Auditor (M5 review)', 'M6', 'Carry-forward from the M5 review: detection is not scalable or integrated',
     'The M5 gatherer reads whole record types and filters in memory, and the monitor reads all findings. The M6 gatherer follows the same pattern for materials, demand, quotes, readings, dockets, orders and observations.',
     'EDR-24; F-21; F-32', 'Preserved as a prototype. Engine-backed, tenant-scoped, indexed reads, durable stores, scheduled sweeps and delivery to named recipients are engineering requirements for Amir, not documentation: EDR-24, EDR-27 and EDR-28 stay open.', 'Open - handoff entries EDR-24, EDR-27, EDR-28'),
    ('F-39', 'Builder (M6)', 'M6', 'A tenant-wide procurement run pins identifiers of orders in projects the caller is not authorised for',
     'The tenant run reads every order of the tenant so that it can recognise the information boundary, and its pin list (the exact records it read, which makes it replayable) therefore names order identifiers of projects outside the authorised set. No signal names such a project or order and a test asserts that; the pins do.',
     'EDR-29; EDR-20; EDR-21; Section 15', 'Documented and asserted in a test, not changed. Whether pins of unauthorised records may be stored or shown to the caller is an Engine permission decision (EDR-29).', 'Open - handoff entry EDR-29'),
    ('F-40', 'Auditor (M5 review)', 'M6', 'Carry-forward from the M5 review: financial scope, synthetic validation and the unreproduced M5 results',
     'Actual cost is supplier invoices only, so M6 reference prices are the last paid order rates, not a cost ledger. Every rule and limit has been tested on synthetic data only. The auditor could not complete the full M5 wrapper in their environment and did not rerun the 678-mutant run, so those stay builder-reported.',
     'F-24; F-25; CR-02 A2 to A13; EDR-24; M5 review', 'Every M6 amount says which record it came from; the M6 mutation figures and test counts are the builder\'s own and are not independently reproduced. The M6 wrapper keeps the M5 steps as named groups so each can be run alone.', 'Open - for the auditor and the product owner'),
    ('F-41', 'Builder (M6)', 'M6', 'Defect A, found by the M6 tests: demand coverage ignored units',
     'The first draft compared an order quantity with a demand quantity without checking that both were in the same unit, so 300 kg of orders could cover a demand of 100 tonne. Orders in a different unit are now not assessed.',
     'apg/mkt/demand.py; tests/test_mkt_demand.py; corpus E08', 'Coverage returns cannot_assess (UNIT_MISMATCH) and the over-order rule records that it could not assess; order units are never converted (I-50). A test fails on the earlier behaviour.', 'Handled in the package'),
    ('F-42', 'Builder (M6)', 'M6', 'Defect B, found by the M6 tests: a cheaper partly comparable quote could be its own baseline',
     'The comparability warning (MP02) took the cheapest comparable or partly comparable offer as the baseline, so a partly comparable quote could hide a cheaper not-comparable one: the warning stayed silent although a cheaper wrong-specification quote existed.',
     'apg/mkt/rules.py; tests/test_mkt_rules.py; corpus D10', 'The baseline is now the cheapest like-for-like offer and the wording says so. A test fails on the earlier behaviour.', 'Handled in the package'),
    ('F-43', 'Builder (M6)', 'M6', 'The extractor and the market feed are test doubles',
     'The extraction stand-in reads two Builder Zero text documents; no language model, PDF, scan or e-mail was involved. The market feed holds only series a test loads. No market-data provider is connected, named or assumed, and no licence has been confirmed.',
     'EDR-08; EDR-09; F-08; DEC-MIE-01', 'The contract suites define what any real implementation must do and 25 faulty implementations show the suites catch the intended faults. Which sources are licensed and how data is retrieved remain with Amir and the product owner.', 'Open - handoff entries EDR-08 and EDR-09'),
    ('F-44', 'Builder (M6)', 'M6', 'The M6 Builder Zero supplements are synthetic, and some signals come from random synthetic data',
     'The quote readings, tiers, terms, landed-cost assumptions, import checks and specification requirements in mkt_data/ were written by the builder for tenant zero_one only (none for zero_two). The three portfolio rate-gap signals (MP10) come from random synthetic order rates; the copper gap is thousands of percent and means nothing. PS-25 is reported without an amount because no demand is left uncovered.',
     'mkt_data/; builder_zero; Section 08', 'The demonstration and the documents say so; the golden file records the signals as they are; none of these values is used as an expectation about any real price.', 'Handled in the package; no real data exists'),
    ('F-45', 'Builder (M6)', 'M6', 'A ranking built from one supplier\'s own offers can be definitive',
     'The ranking needs at least two rankable offers, not two suppliers. Two quotes from one supplier for the same specification can therefore give a definitive ranking of that supplier\'s options. M6 adds an information note saying so ("not a comparison between suppliers") and does not change the gate.',
     'apg/mkt/compare.py; corpus B04; Section 08 4', 'Left as a product-owner decision: whether a one-supplier ranking may be definitive, and whether the gate should demand two suppliers.', 'Open - for the product owner'),
    ('F-46', 'Builder (M6)', 'M6', 'M5 files changed in M6 (baseline-changed) and the M5 checks they require',
     'To register the procurement formulas and fix F-36, M6 changed: apg/det/detect.py (the registered procurement formula ids), apg/det/findings.py (accepts those ids), apg/det/relations.py (policy reference prefixes mkt_policy/ and mkt_spec/), apg/det/portfolio.py (display), tests/test_det_portfolio.py, tools/run_demo_m5.py and regression/DEMO_OUTPUT_M5.txt, plus the M5 and earlier register-check and regression tools that would otherwise fail on the extended tables. All other M5 files are byte-identical.',
     'regression/BASELINE_M5.json; tools/run_regression_m6.py', 'The regression lists every changed file against its delivered M5 hash and requires the rest to be identical. The M5 tests and the M5 mutation run for the four changed code modules were repeated (see the M6 documents).', 'Handled in the package; for the auditor to confirm'),
    ('F-47', 'Builder (M6)', 'M6', 'RFC-01 conflicts with the programme numbering and overlaps reserved sections',
     'RFC-01 calls its planned engine "M7", the programme table already has M7 "Recommendations", and the RFC capabilities overlap reserved Sections 19 to 24 and parts of locked Sections 06, 10 and 12.',
     'programme/RFC_REGISTER.csv; CR-09 P4 and P7; CR-01 A1', 'Reported in the RFC record and left unresolved: the M7 row, CR-09 and the locked sections are not edited. M7 (either meaning) is not started.', 'Open - for the product owner and the blueprint author'),
    ('F-48', 'Builder (M6)', 'M6', 'Minor limits of the M6 rules',
     'MP03 (decision due) pools offers by gate class only and not by qualification, so a stale comparable offer can set the decision date; a demand of zero quantity is accepted at intake but produces no purchase requirement; the supplier rule reports observations over a minimum sample and nothing below it; the larger-tier note says the total paid is "higher" when the totals are in fact equal (a test pins that it never says "lower"); an order rate at exactly 90 days is current and from 91 days stale, the same rule as a quote.',
     'apg/mkt/rules.py; apg/mkt/landed.py; corpus A15, E11, E12', 'Each is covered by a test or corpus case so a change is noticed.', 'Handled in the package; for the product owner to confirm'),
    ('F-49', 'Builder (M6)', 'M6', 'The M6 corpus runs against the builder\'s reference pipeline, not a storage-neutral world',
     'The M5 corpus could be run by Amir against the Engine\'s storage through a world interface. The M6 corpus (tests/corpus_mkt.py) builds its worlds with the builder\'s own test helpers.',
     'F-38; EDR-24', 'Recorded; porting it to a world interface is Engine-integration work for the handoff at M12.', 'Open - handoff'),
    ('F-50', 'Builder (M6)', 'M6', 'Defect C, found by the mutation work: three or more identical orders never served as the last-paid reference',
     'The orders reconciliation holds back as possible duplicates name each other in one comma-joined code. The M6 reading of that code kept the joined text as a single name (for example "PO-2,PO-3"), so with three or more identical orders the lookup found no order of that name and skipped the reference. With two identical orders it worked.',
     'apg/mkt/common.py; tests/test_mkt_edges_landed.py', 'Each candidate is now named separately, and a test with three identical orders pins the candidate lists and the limit text. A test fails on the earlier behaviour.', 'Handled in the package'),
    ('F-51', 'Builder (M6)', 'M6', 'Defect D, found by the mutation work: an order rate in another unit was not rescaled, and a deposit above 100% could crash a scenario',
     'A last-paid reference was shown per the order unit even when the specification register declares a conversion to the requirement unit, while a quote is rescaled; the same material could therefore carry two bases. Separately, a payment-term deposit above 10000 basis points reached the financing arithmetic with a negative balance and could raise an error.',
     'apg/mkt/compare.py; apg/mkt/scenarios.py; tests/test_mkt_edges_landed.py', 'The order reference is rescaled with the declared factor exactly as a quote is, and says so; a deposit outside 0 to 10000 or not readable as a number is reported as an evidence gap and no deposit is assumed. Tests cover both. Order rates of zero or below, and orders with no unit, are held at intake and never reach the reference.', 'Handled in the package'),
]
INTERP = [
    ('I-44', 'M6 roles and approvals', 'The roles procurement_policy_owner and specification_owner approve the procurement policy and the specification register. A policy or register version is immutable; the person who proposes a version cannot approve it; an unapproved version still runs but the result says it is unapproved. There are no defaults: a missing parameter makes the rule report not_configured and name it.', '08; 06:5.1', 'Other role names or a weaker approval would change who may set a limit; a default would settle an open decision.'),
    ('I-45', 'Comparability', 'An offer is comparable, comparable with adjustment, partly comparable, not comparable or unverified. A failure from any evidence (the catalogue or a reading) blocks. A pass needs a reading verified by someone other than the extractor, with a date. The unit must be verified, otherwise the offer is only partly comparable. A rescaled offer is shown but gets no purchase scenario.', '08:4', 'Lenient rules would let an unlike item rank; strict rules would exclude usable offers.'),
    ('I-46', 'Ranking status', 'A ranking is definitive only with at least two offers, all comparable or comparable with adjustment, all current, landed cost complete, no unresolved critical international check, no substitution and no held supporting record. Anything short of that is indicative, including a partly comparable offer (the conservative choice). may_recommend is the only gate and human approval is always required.', '08:4; 10', 'A less strict gate would let a recommendation pass when it should not (the M6 acceptance wording).'),
    ('I-47', 'Freshness', 'There are four decision classes (quote ranking, buy timing, benchmark, import costing), each with its own limit for a quote, an index and a rate. A stale quote is still an offer but cannot make a ranking definitive; an expired or not-yet-issued quote is historical only; no observation is unavailable, never fresh. The age equal to the limit is fresh.', '08:7; 04', 'Different limits or boundaries change which offers can be definitive.'),
    ('I-48', 'Exchange rates', 'The rate is the latest on or before the as-of day, expressed as foreign units per AUD. An amount in AUD is the foreign amount divided by the rate, rounded half away from zero once per component. The supplier\'s stated rate is kept and never replaced; the divergence is stated in basis points of the stated amount against the reference conversion, and the tolerance is configuration.', '08:7; 05', 'A different convention changes every foreign landed cost.'),
    ('I-49', 'Landed-cost basis', 'The delivery basis decides which components are included in the rate (delivered includes freight and handling; ex-works and FOB include none). Required components differ for domestic and international offers. Prices are compared on the tax basis the policy states (ex GST) and GST is not computed. Tier price is chosen by quantity. A unit conversion uses only a factor declared in the specification register (in millionths) and only when the offered unit is verified; with no declared conversion the units are incompatible and with an unverified unit the offer is only partly comparable.', '08:5; 03', 'A different basis changes which offer is cheapest.'),
    ('I-50', 'Demand and orders', 'An order covers a demand when project, material and window match: orders from 180 days before the required date up to the as-of day with status committed or closed. Identical orders held as duplicate candidates are counted as possible, not confirmed. Surplus beyond 500 basis points is flagged. An order unit that differs from the demand unit is not converted: coverage is cannot_assess.', '08:9', 'A different window, status set or tolerance changes which orders count as cover.'),
    ('I-51', 'Scenarios', 'Buy now orders on the as-of day. Wait orders on the latest day that still meets the required date after the lead time and its variation, with price paths only from the policy. Stage splits the quantity as the policy says with its extra delivery and admin costs. Storage and financing use the policy rates over days / 365. Negotiate sets the lowest complete offer beside the others and asserts no price; with fewer than two rankable complete offers it says it cannot assess. A scenario never changes the forecast and is never ranked.', '08:8; 10', 'A different timing or cost rule changes every scenario total.'),
    ('I-52', 'Savings reference', 'An opportunity compares a comparable current quote with the last paid order rate for the same material (not an approved baseline), for the quantity not yet ordered. It is always an estimate; claim_saving always refuses.', '08:10; 05', 'Using a different reference would change the size of every opportunity; treating it as a saving would overstate.'),
    ('I-53', 'Portfolio purchasing', 'A cross-project rate comparison is made only when the authorised project set covers every project that bought the material in the window. Each project\'s weighted average rate is rounded once to cents; the estimate is (higher average - lower average) x the higher project\'s volume; the gap is relative to the lower average.', '08:11', 'A different grouping or rounding changes the gap; reporting with an incomplete set would reveal other projects.'),
    ('I-54', 'Supplier performance', 'Fill rate is accepted quantity over ordered quantity across the orders that have at least one docket (open orders are not counted as short); acceptance rate is accepted over delivered across dockets that record an accepted quantity. Below a minimum sample the rule says it could not assess. The signal is an observation, not a ranking of suppliers.', '08:12', 'Different measures or sample sizes change which supplier is flagged.'),
    ('I-55', 'International safeguards', 'The critical checks are a configured list (illustratively customs classification, duty rate confirmed, import permit). A check is resolved only with a status, evidence reference, a named person and a date. Any open critical check keeps a ranking from being definitive. APG states what is unresolved and does not declare a product compliant.', '08:13', 'A shorter list would pass an import with open checks.'),
    ('I-56', 'Event fields', 'Each procurement condition writes an apg-event-1 record with event type, observation time, effective time, source provenance, project, material and supplier. Nothing is related, chained or inferred in M6.', 'RFC-01 (proposed)', 'Different fields would force rework when the later engine is developed; extra inference would assert a design that has not been agreed.'),
    ('I-57', 'Demonstration limits', 'Every limit, window, tolerance, path and specification in the M6 demonstration policy and register is the builder\'s illustrative choice. None has product-owner approval.', '08:15; 06:8', 'Treating them as defaults would settle open decisions.'),
    ('I-58', 'One supplier', 'The ranking gate counts offers, not suppliers; a note says when all ranked offers come from one supplier.', '08:4', 'Requiring two suppliers would make a one-supplier market never definitive.'),
]
RFC_H = ['rfc_id', 'title', 'status', 'received', 'source', 'summary', 'scope_proposed', 'affected_components', 'dependencies', 'acceptance_criteria', 'unresolved_decisions', 'required_approvals', 'locked_baseline_effect', 'conflicts_reported', 'evidence_level_reached', 'm6_contribution', 'later_milestone_status', 'document']
RFC = [dict(
    rfc_id='RFC-01', title='Latent Risk & Intervention Engine', status='PROPOSED - not approved; not yet a numbered change request', received='2026-10-14', source='Product owner architecture directive in the APG project conversation',
    summary='Cross-domain financial-risk intelligence and intervention engine: six strategic capabilities (latent risk chains; unearned margin and physical progress; contractual time-bar; landed cost and procurement; cost of capital and trapped cash; closed-loop intervention efficacy) under seven governing principles, with a planned engine milestone built on tested M6 interfaces.',
    scope_proposed='M6 under the existing process supplies comparable quotes, landed cost, freshness, scenarios and event hooks. The later engine (cross-domain relationships, chains, progress reconciliation, time-bar monitoring, cost of capital, intervention efficacy, alert prioritisation) is planned only.',
    affected_components='New (not built): relationship/event store, chain detection, intervention outcome record, counterfactual method. Reused unchanged: signal contract, finding lifecycle, noise control, repro formulas, tenancy. M6 adds apg/mkt and the apg-event-1 fields.',
    dependencies='Anchor Engine (storage, scheduling, permissions; EDR-24, EDR-29, EDR-30); CR-04 (Section 19), CR-05 (Section 24), CR-06 (Section 22; legal review), CR-10 (Section 20), CR-03 (Section 23), CR-07 (Section 21), CR-02 financial policies, CR-08 pilot builders.',
    acceptance_criteria='Ultimate: earlier detection than the builder\'s process, reliable evidence, an actionable intervention and a defensibly measured financial outcome on real projects. Pilot target (a test target, not hard-coded, not a guarantee): detection at least 72 hours before a relevant commitment and an effective $2,000 mitigation of a substantiated $10,000 loss. M6: no definitive recommendation passes the comparability or freshness gates when it should not.',
    unresolved_decisions='CR number and section placement; relation to the existing M7 row; contractual rule sources and legal reviewer; counterfactual baseline method; relationship model and evidence for proposed relations; DEC-A1-1..8; DEC-MIE-01; CR-02 A1..A13; whether a one-supplier ranking may be definitive.',
    required_approvals='Product owner; independent review not by the Builder; G1 review; CR number and owner assigned in the CR-09 change register by its maintainer; CR-01 where reserved sections are involved; qualified legal review for contract content; builder access and data-handling basis for any pilot claim. None has happened.',
    locked_baseline_effect='None. Sections 00-18 v1.0 (SHA-256 487becabdf47796800937d13a706a19b63b7b8230ecc5354b2f01a647ae5d960), CR-09 and its P4 change register, the RTM, historical packages and every hash are unchanged.',
    conflicts_reported='Programme M7 "Recommendations" vs RFC "M7 Latent Risk and Intervention Engine"; overlap with reserved Sections 19-24 (CR-03, CR-04, CR-05, CR-06, CR-07, CR-10) and with locked Sections 06, 10 and 12. None resolved here.',
    evidence_level_reached='Capability 4: builder-implemented and locally tested on synthetic data, not independently reviewed. Capabilities 5 and 6: partial building blocks at the same level. Capabilities 1, 2 and 3: design only. Nothing independently verified or production accepted.',
    m6_contribution='Comparable quotes with explicit failures; currency, tax and unit normalisation; landed cost; lead times, validity and required-on-site dates; stale-data handling; buy-versus-wait scenarios; provenance and reproducible records; apg-event-1 hook fields; 78-case corpus; 24 port-contract cases.',
    later_milestone_status='Not started. The RFC engine milestone and the programme M7 are both untouched.', document='programme/RFC-01_LATENT_RISK_AND_INTERVENTION_ENGINE.md')]
header, rows = rd('PROGRAMME_MILESTONES.csv')
for r in rows:
    if r['milestone_id'] == 'M5':
        r['status'] = 'Delivered - builder-checked'
    if r['milestone_id'] == 'M6':
        r['status'] = 'In this delivery'
        r['handoff_register_entries'] = 'EDR-08; EDR-09; EDR-29; EDR-30'
wr('PROGRAMME_MILESTONES.csv', header, rows)
header, rows = rd('ENGINE_HANDOFF_REGISTER.csv')
for r in rows:
    if r['edr_id'] == 'EDR-08' and 'written in M6' not in r['contract_test']:
        r['contract_test'] = 'extraction_contract (written in M6, apg/mkt/contracts_m6.py, cases EX-*): every field starts unverified; an unclear reading is ambiguous with candidates and no value; a missing field is not invented; text inside a document is data; the hash is checked; deterministic; tenant claim refused; copies independent. Run against the in-memory stand-in and 11 faulty extractors.'
        r['status'] = 'Open - contract test written'
    if r['edr_id'] == 'EDR-09' and 'written in M6' not in r['contract_test']:
        r['contract_test'] = 'market_feed_contract (written in M6, apg/mkt/contracts_m6.py, cases MF-*): stale series downgraded and the age boundary exact; unavailable never filled; unlicensed and unknown-licence series refused; licence per tenant; invalid observations counted and not returned; conflicting values reported; no default age limit; no future data. Run against the in-memory reference and 14 faulty feeds.'
        r['status'] = 'Open - contract test written'
wr('ENGINE_HANDOFF_REGISTER.csv', header, rows)
add('ENGINE_HANDOFF_REGISTER.csv', 'edr_id', EDR)
add('STATUS_REGISTER.csv', 'item_id', [dict(item_id=i, item=t, milestone='M6', evidence_ladder_status='Local-tested', evidence=e, claim_limit=c) for i, t, e, c in SRROWS])
add('FINDINGS_REGISTER.csv', 'finding_id', [dict(finding_id=a, raised_by=b, milestone=c, title=d, description=e, linked_items=f, how_it_is_handled_here=g, status=h) for a, b, c, d, e, f, g, h in FIND])
add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=a, milestone='M6', topic=b, builder_reading=c, blueprint_ref=d, effect_if_wrong=e, auditor_note='', status='Retained for review - not approved', reviewer_decision='')
                                                           for a, b, c, d, e in INTERP])
if not os.path.exists(os.path.join(P, 'RFC_REGISTER.csv')):
    wr('RFC_REGISTER.csv', RFC_H, RFC)
print('M6 rows added')
