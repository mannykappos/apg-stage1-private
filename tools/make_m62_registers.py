#!/usr/bin/env python3
"""Adds the APG-M6.2 correction rows to the programme tables and writes the carried-forward register.  Usage: make_m62_registers.py <programme_dir>
Runs AFTER make_m61_registers.py.  Idempotent: a row whose id already exists is left alone.  It changes no existing row.  Nothing here closes a finding, approves an interpretation, settles a
decision, numbers or approves RFC-01, adopts a baseline or configures a finance assumption."""
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


AUD = 'Auditor (M6.1 independent review)'
OPEN_FIXED = 'Corrected in APG-M6.2 (builder-implemented); open until independently verified'
FIND = [
    ('F-53', AUD, 'M6.2', 'A proposal written against old evidence could still be approved after the evidence changed, also when the approver named no version',
     'The independent audit of APG-M6.1 reproduced it: an action is proposed at finding version 1; a later detection run changes the evidence to version 2 while the finding is still action_proposed; a person '
     'other than the proposer approves without naming a version. In M6.1 that approval was accepted and bound to version 2 and the version-2 digest, although the proposal text and the case for it were '
     'written against the version-1 evidence. M6.1 recorded proposed_version and proposed_digest on the action but nothing compared them with the finding at approval, and the M6.1 tests did not '
     'cover the case. The builder reproduced it on the delivered M6.1 tree with the same digests and accepts that the tests were incomplete. The same gap existed after an approval had been ended '
     'by changed evidence (the old proposal could be approved again). The suggested identifier was F-53; this release is the change control it is recorded under.',
     'apg/det/findings.py; tests/test_det_proposal_binding.py; tests/test_det_approval_binding.py; tools/probe_stale_proposal.py; programme/CHANGE_RECORD_APG-M6.2.md; F-52; F-54; I-65 to I-70',
     'Corrected in the separately versioned release APG-M6.2; the delivered M5, M6 and M6.1 archives and their hashes are unchanged. An approval is now refused (STALE_PROPOSAL) unless the proposal was '
     'written against the finding\'s current version and evidence digest, whether or not the approver names a version; a stale proposal is marked stale by the run that changed the evidence and is sent '
     'back by a reviewer and proposed again against the current evidence (no new status or transition). The approval entry point approve_action fails closed without the version and digest the approver '
     'was shown. Tests were written first and seen to fail on M6.1. Builder-implemented and locally tested; no independent review has taken place. F-52 also stays open until independently verified.',
     OPEN_FIXED),
    ('F-54', AUD, 'M6.2', 'The exact text and context of a replaced proposal and of an ended approval were not kept in the audit trail',
     'In M6.1 a new action_proposed transition overwrote the action record and kept only the approval history. The proposal text, who proposed it and when, and the version and digest it was written '
     'against were lost when a proposal was replaced; the history event for a proposal or approval named neither the action text nor the versions; and an ended approval kept who approved and when but not '
     'the text that was approved or the approver\'s rationale. The auditor asked whether the immutable history must retain this and said it is distinct from the stale-proposal defect.',
     'apg/det/findings.py; tests/test_det_proposal_binding.py; programme/CHANGE_RECORD_APG-M6.2.md; I-69',
     'Corrected in APG-M6.2 on the builder\'s reading that it must (I-69, retained for review). A replaced proposal is kept in full in action.proposal_history; the proposal and approval events carry the exact '
     'action text and the versions and digests; an ended approval keeps the text, the proposer, the proposal version and digest and the approval rationale. Nothing is deleted and earlier events are '
     'unchanged. Builder-implemented and locally tested; no independent review has taken place.',
     OPEN_FIXED),
]
INTERP = [
    ('I-65', 'A proposal is current only if written against the current version and digest',
     'An action proposal is current when the version and the evidence digest it records equal the finding\'s present version and digest. Any change of digest makes it stale (the same measure as I-59; no size '
     'threshold is applied because none has been set). A proposal with no recorded version or digest (made before M6.1) is never current.',
     '06:6; 06:11', 'A threshold would be a policy decision. Without one, any change of evidence asks for a fresh proposal, which is the safe direction but may ask more often than the business wants.'),
    ('I-66', 'A stale proposal is sent back by a reviewer; it is not refreshed in place',
     'A stale proposal cannot be approved and is not silently rewritten to the new evidence. The route is the one the lifecycle already has: a reviewer returns the finding to confirmed with a reason, and the '
     'owner proposes the action again. No status and no transition are added; the table of 14 allowed transitions is unchanged.',
     '06:6; 06:11', 'A direct owner re-proposal or an automatic refresh would be a new transition, which is a lifecycle decision no one has made and the auditor has directed against.'),
    ('I-67', 'The refusal does not depend on what the approver names',
     'The stale-proposal check runs in the approval step itself. Naming the current version or digest does not make a stale proposal approvable; naming an older one is refused as a stale approval first. '
     'The proposer is still refused as a self-approver before anything else.',
     '06:11', 'If the check depended on the optional version, an approver who named nothing, or the current version, would still approve a proposal written against other evidence.'),
    ('I-68', 'Fail-closed approval entry point',
     'approve_action(scoped, clock, finding, version, digest, rationale) refuses to act unless the version (a whole number of at least 1) and the evidence digest (a non-empty text) are given, and approval_token(finding) '
     'gives what a screen must show and hand back. The lower-level transition keeps its optional version for the existing callers. That a screen or API calls approve_action, and passes what it displayed, is a '
     'handoff point this package cannot enforce.',
     '06:11', 'Without it an approval screen can approve a version it did not display; with the optional argument alone nothing makes a caller supply it.'),
    ('I-69', 'What the audit trail keeps when a proposal is replaced or an approval ends',
     'The audit trail keeps the exact action text, who proposed it and when, the finding version and digest it was written against, the approval and its rationale, and what ended it. A replaced proposal is '
     'appended to action.proposal_history (with who replaced it and at which version and digest); the proposal and approval events carry the text and the versions; an ended approval keeps the same. Nothing is '
     'removed and earlier events are unchanged. Records made before M6.2 lack some of these fields and show them as empty.',
     '06:11', 'If less is needed the extra fields are harmless; if more is needed (for example a rationale for each re-proposal) it is a small addition. Losing the text would leave an approval impossible to reconstruct.'),
    ('I-70', 'A reopened finding makes its proposal stale',
     'When a resolved or dismissed finding is reopened by a run with changed evidence, an action proposed earlier is marked stale in the same step, as it is for a finding that is simply updated. The finding goes '
     'to reopened as before; a reviewer and the owner then follow the same route as for any stale proposal.',
     '06:11', 'Leaving the old proposal current would let a reopened finding carry a proposal for evidence it no longer has.'),
]
SRROWS = [
    ('SR-66', 'Proposal binding: an action can only be approved while its proposal was written against the current finding version and evidence digest; a stale proposal is refused, marked, and kept in full (F-53, F-54)',
     'Local-tested', 'apg/det/findings.py; tests/test_det_proposal_binding.py; tests/test_det_approval_binding.py; programme/CHANGE_RECORD_APG-M6.2.md',
     'Builder-implemented and locally tested; no independent review has taken place. Governs the prototype\'s records only: nothing executes an action. The auditor verifies the correction and its audit trail'),
    ('SR-67', 'Fail-closed approval entry point (approve_action, approval_token, approvable)', 'Local-tested', 'apg/det/findings.py; tests/test_det_proposal_binding.py',
     'Builder-implemented and locally tested; no independent review has taken place. No screen or API exists in this package; that a real one calls it and passes the version it displayed is for the Engine build'),
    ('SR-68', 'Repeat of the M5 mutation runs for the four M5 modules after the M6.2 correction', 'Local-tested', 'tools/m5_mutants.py; logs/m62/mutation_run_m5_*.log',
     'Builder-run; no independent review has taken place. Shows the tests notice one-place changes of the kinds listed; the builder\'s own figures, not independently reproduced. Any run that does not finish is recorded as incomplete, not as a pass'),
    ('SR-69', 'Register of the open issues carried forward from the earlier M6 audit and the M6.1 audit (tenant isolation, cost coverage, synthetic data, events and provenance, portfolio purchasing, governance)',
     'Specified', 'programme/CARRIED_FORWARD_REGISTER.csv', 'A record of what stays open. It closes nothing, settles no decision and adds no evidence. Tenant and project isolation was not reproduced in the M6.1 audit and is not fixed here'),
]
CF_H = ['cf_id', 'audit_section', 'topic', 'what_remains_open', 'what_this_package_shows', 'linked_records', 'who_must_act', 'status']
OPEN = 'Open - carried forward'
CF = [
    ('CF-01', '7.1', 'Synthetic data only', 'No real supplier feed, quote source, FX feed, duty rate or builder export was connected. All M6 data is synthetic.',
     'Rules and limits are tested on synthetic data and the faulty-input corpus only.', 'F-43; F-44; F-40; EDR-08; EDR-09', 'Product owner and a pilot builder (real exports); data-licence confirmation', OPEN),
    ('CF-02', '7.1', 'Ports tested against in-memory references only', 'MarketFeedPort and ExtractionRuntimePort were tested only against in-memory references. The 24 passing contract cases do not show that any live provider works.',
     'The contract suites and the 25 faulty implementations show the suites catch the faults the builder thought of.', 'EDR-08; EDR-09; F-43', 'Amir (Engine build); the live provider', OPEN),
    ('CF-03', '7.1', 'No Anchor Engine, production database, event bus, AUIF or Governor repository integrated', 'None was supplied or integrated. No separate reusable Market Intelligence Engine implementation was evidenced.',
     'The package runs on its in-memory reference world; each Engine need is a handoff entry.', 'EDR-02; EDR-03; EDR-16; EDR-18; EDR-19; DEC-MIE-01', 'Amir (Engine build); product owner (DEC-MIE-01, MIE evidence)', OPEN),
    ('CF-04', '7.1', 'Event and provenance gaps in apg-event-1', 'The Phase 0 inspection found no event store or bus, no recorded_at, no single provenance_id, no explicit correction or supersession links, and no baseline_version_id or baseline_hash. Currency, unit and quantity sit in an unvalidated detail payload.',
     'M6 writes event hooks with observation and effective time and references; the fields above are not present.', 'EDR-30; F-47; programme/E17_PHASE_0_REPOSITORY_DISCOVERY.md', 'Product owner (RFC-01); Amir (event store)', OPEN),
    ('CF-05', '7.1', 'Tenant and project isolation (EDR-29)', 'A tenant-wide procurement run pins identifiers of orders in projects the caller is not authorised for, even though no signal names such a project. EDR-29 and project-level authorisation must be resolved and tested adversarially before any real multi-tenant use. Not independently reproduced in the M6.1 audit.',
     'Nothing in M6.2 changes this. No fix is claimed, and there is no multi-tenant deployment evidence.', 'F-39; EDR-29; F-31; F-33', 'Amir (Engine build); the auditor (adversarial test)', OPEN),
    ('CF-06', '7.2', 'Cost components not comprehensively modelled', 'Installation labour, crane and plant, redesign, certification, warranty and cancellation costs are not comprehensively modelled.',
     'The landed-cost model covers the components it lists and no more.', 'F-48; F-40', 'Product owner (scope); finance owner', OPEN),
    ('CF-07', '7.2', 'Quantity reconciliation inputs absent', 'No approved takeoff or BOQ revisions, verified installed quantities, returns or reusable surplus are held.',
     'Demand coverage compares orders and deliveries with the demand lines it is given.', 'G-05 (V2 rule, proposed)', 'Project commercial or QS authority', OPEN),
    ('CF-08', '7.2', 'Payment-term economics absent', 'Early-payment discount economics, alternative security options and liquidity constraints are largely absent.',
     'Nothing is computed for them; no cost-of-capital rate exists.', 'G-06 (V3 rule, proposed); G-09', 'Commercial authority; finance owner', OPEN),
    ('CF-09', '7.2', 'M6 portfolio purchasing is not the specified forward aggregation', 'The M6 portfolio comparison is a backward-looking rate-gap estimate from rates already paid. The specified aggregation of compatible, uncommitted demand across projects is not built.',
     'The M6 check groups demand and does not approve it.', 'G-07 (V4 rule, proposed); programme/E17_GOVERNANCE_RECORD.md', 'Each affected project\'s commercial authority; delegated procurement authority', OPEN),
    ('CF-10', '7.2', 'Capacity, delivery windows and double-count controls', 'Supplier capacity, multi-project delivery windows and portfolio overlap and double-count controls need further evidence.',
     'Not modelled beyond what M6 lists.', 'F-45; F-48', 'Product owner', OPEN),
    ('CF-11', '7.2', 'The $0 to $0 display of unquantified portfolio exposure', 'The auditor reports the display issue appears corrected and the M6 golden check passes. That does not close unrelated M6 findings.',
     'F-36 is recorded as handled in the package; the golden check passes in the builder\'s runs.', 'F-36', 'Auditor: confirm', 'For the auditor to confirm'),
    ('CF-12', '7.3', 'Invoice-only cost coverage', 'Actual cost is supplier invoices only. Labour, plant, accruals and overheads are not fully in the cost base; M4 and M5 cost coverage is not a complete construction ledger.',
     'Reference prices are the last paid order rates, not a cost ledger.', 'F-40; F-34', 'Product owner and a pilot builder (cost ledger export)', OPEN),
    ('CF-13', '7.3', 'No finance assumptions and no realised-outcome workflow', 'No approved cost-of-capital or overhead assumption is configured. The realised-outcome and counterfactual and attribution workflow is not built. The system refuses to claim realised savings.',
     'No rate, allocation or offset cost is set anywhere.', 'G-09', 'Finance owner', OPEN),
    ('CF-14', '7.4', 'Engine #17 is not built', 'The Phase 0 inspection found no Engine #17 code. M6 covers portions of V1 and V2 and a different, backward-looking version of V4; V3 is largely absent.',
     'Nothing of Engine #17 is started in M6.2; the foundations, E1 to E5 and M7 are not started.', 'G-11; programme/E17_PHASE_0_REPOSITORY_DISCOVERY.md', 'Product owner (RFC-01, then sequence)', OPEN),
    ('CF-15', '7.4', 'The Engine #17 pack is a specification', 'The pack is a specification and handoff artefact, not implementation evidence.',
     'It is recorded as such in the governance record.', 'G-12', 'None; this waits for the product owner to approve and number RFC-01', OPEN),
    ('CF-16', '7.5', 'RFC-01 is proposed, unnumbered and unapproved', 'M7 Recommendations remains the existing locked milestone. Engine #17 is folded into M7 only after the change request is formally approved and numbered.',
     'RFC-01 is unchanged and PROPOSED; M7 is not started.', 'F-47; G-01; RFC-01', 'Product owner (Emmanuel)', OPEN),
    ('CF-17', '7.5', 'Engine #1 to #18 mapping not authoritative', 'The labels are provisional until the blueprint owner approves a mapping.',
     'No map has been made.', 'G-02', 'Blueprint author or product owner', OPEN),
    ('CF-18', '7.5', 'V1 to V4 baseline rules are proposed only', 'The four baseline rules are proposed, not approved and not implemented.',
     'Recorded as PROPOSED in the governance register.', 'G-03 to G-07', 'Product owner; each baseline owner', OPEN),
    ('CF-19', '7.5', 'Finance assumptions unconfigured', 'Cost of capital, overhead rates and offset-cost rules stay unconfigured pending finance-owner approval.',
     'Nothing is configured.', 'G-09', 'Finance owner', OPEN),
    ('CF-20', '7.5', 'No third lifecycle', 'Section 05 section 10 governs benefit states; the M5 statuses govern finding review.',
     'M6.2 adds no status and no transition: the ten statuses and the 14 allowed transitions are unchanged.', 'G-08; I-66', 'None', 'Followed - nothing added'),
    ('CF-21', '7.5', 'Existing open decisions', 'DEC-A1-1 to DEC-A1-8, DEC-MIE-01, B7, the independent review of the ten classifications, MIE evidence, AUIF reconciliation, legal confirmation of the bank-data route, market-data licences, pilot builders and the go for CR-02 Stage 2 all remain open.',
     'None is settled here.', 'DEC-A1-1 to DEC-A1-8; DEC-MIE-01; B7; CR-02', 'Product owner; Amir; the auditor (as each decision names)', OPEN),
    ('CF-22', '5', 'Approval screens and APIs must pass the version they displayed', 'A separate integration gate: an approval screen must pass the exact version it displayed, and the API boundary must fail closed when the version is missing or stale.',
     'approve_action and approval_token fail closed in this package\'s code and are tested. No screen or API exists here, so the gate is not met until the Engine build uses them. For the handoff package at M12.', 'F-53; I-68; SR-67', 'Amir (Engine build); the auditor (integration test)', 'Open - function built and tested; screen and API for the Engine build'),
    ('CF-23', '1, 3', 'Independent verification limits', 'In the auditor\'s environment the full unit-test suite and the full wrapper timed out and are not recorded as pass or fail. The mutation and sabotage results are builder-reported only.',
     'The build\'s run times are stated in the documents so a timeout can be compared with them. A run that does not finish is recorded here as incomplete.', 'F-40; SR-68', 'Auditor: rerun with enough time, or split the runs', 'Open - for the auditor'),
]
add('FINDINGS_REGISTER.csv', 'finding_id', [dict(finding_id=a, raised_by=b, milestone=c, title=d, description=e, linked_items=f, how_it_is_handled_here=g, status=h) for a, b, c, d, e, f, g, h in FIND])
add('INTERPRETATIONS_REGISTER.csv', 'interpretation_id', [dict(interpretation_id=a, milestone='M6.2', topic=b, builder_reading=c, blueprint_ref=d, effect_if_wrong=e, auditor_note='',
                                                               status='Retained for review - not approved', reviewer_decision='') for a, b, c, d, e in INTERP])
add('STATUS_REGISTER.csv', 'item_id', [dict(item_id=i, item=t, milestone='M6.2', evidence_ladder_status=l, evidence=e, claim_limit=c) for i, t, l, e, c in SRROWS])
if not os.path.exists(os.path.join(P, 'CARRIED_FORWARD_REGISTER.csv')):
    wr('CARRIED_FORWARD_REGISTER.csv', CF_H, [dict(zip(CF_H, r)) for r in CF])
print('M6.2 rows added')
