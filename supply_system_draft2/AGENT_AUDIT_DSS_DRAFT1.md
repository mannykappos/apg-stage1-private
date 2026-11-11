# INDEPENDENT READ-ONLY (agent) audit: APG Data Supply System, draft 1

Auditor: a fresh Claude agent, read-only. I did not edit, move or create any file except this report. I used only the synthetic material in `audit_in/` and no network.

Scope: `DRAFT1_EXPORT.md` (212 lines; "line N" below means a line of that file) against `rev3/` (CR_REV3_DOC_EXPORT.md and four CSVs), `SUPPLY_PLAN.csv`, `PHASE1_CHECK.csv`, `build_supply_plan.py`, `blueprint/` (S04, S06, S10, Section_18, 8-layer 11), `stage1_ingest_code/` and `rules_code/`. I covered everything in one pass.

## How I verified

- I ran `python3 -I build_supply_plan.py rev3` in place. The SHA-256 of both CSVs was the same before and after (SUPPLY_PLAN `5e91946e…`, PHASE1_CHECK `6a9c35d2…`), so the CSVs match the script.
- I recomputed every count independently from ENTITY_REGISTER.csv and RULE_INPUT_CONTRACTS.csv with my own code, run in memory with nothing written.
- Numbers that are correct as stated: the counts per way in (T 37/29, D 17/6, E 0/47, S 1/12, A 8/9, P 0/14, I 0/24; these equal CHART_DATA_PATHS.csv), 99 entities, 48 built or partly built against 51 not built (this equals rev3's 38 + 10 against 51), phases 29/17/48/5, every cell of the per-phase breakdown table (lines 111–117), 21 phase-1 templates that exist, 39 contract rows with 0 failing, "12 of the 17, of which 10 still to build", and the five file-only phase-1 facts (E15, E21, E24, E57, E73).
- So the arithmetic is right for the rule as the script codes it. The problems are in that rule, in what it reads, and in what the numbers are said to mean.

---

## Findings

### 1. BLOCKING: the stage 1 "shared intake" covers 11 record kinds only. Most phase-1 data reaches the rules through other intake paths.

**Quote.**
- Line 25: "The shared intake … already exists … the stage 1 code holds a working reference version … It does not add a second intake."
- Line 119: "'Built' here means the stage 1 code accepts it."
- Lines 34–35: the table marks "Validation outcomes and quarantine" and "Entity resolution and reconciliation" as "Nothing new".

**What is wrong.**
- `pipeline.ingest_file` refuses any entity that is not in `specs.SPECS`. That list has 11 kinds: supplier, ap_invoice, credit_note, payment, purchase_order, po_amendment, supplier_quote, pm_invoice, budget_line, fx_rate, market_observation.
- `reconcile` loops over the same `ENTITIES` tuple only.
- `entities.py` resolves supplier references only.
- The rules and figures read 16 other kinds (contract, variation, notice, project, ctc_line, delay_event, timesheet, work_output, plant_hire, defect, compliance, retention, security, bank_txn, facility, retention_event). None of them is in SPECS.
- Those kinds reach the rules through `apg/fin/intake.py` (`usable`) and `apg/det/intake.py` (`DET_SPECS`). Neither file is in the pack. There are also two direct writers: `source_authority.ingest_batch`, which stores rows with `scoped.put`, and `fin/cash_states.record_event`.
- Result: of the 21 phase-1 entities counted "built" by template (line 113), only 6 are accepted by the cited Section 04 intake: E21, E22, E23, E24, E30 and E38. The other 15 get no S04 reconciliation, no authority resolution through `reconcile`, and no entity resolution.
- Stage 1 therefore already has several intakes. Moving these kinds onto the shared one means changing `apg/fin/intake.py` and `apg/det/intake.py`, which PG-DS-AC-03 (line 186) forbids.

**Evidence.**
- `stage1_ingest_code/pipeline.py` lines 132–134: `if entity not in SPECS: raise IngestError`.
- `specs.py` lines 9–29 (the SPECS list).
- `reconcile.py` line 78 (`for kind in ENTITIES`).
- `entities.py` docstring ("supplier reference").
- `rules_code/det/rules_ops.py` lines 12 and 14, and `fin/revenue.py`, `forecast.py`, `cashview.py` (each imports `.intake`).
- `source_authority.py` lines 361–366.
- `cash_states.py` line 92.
- The kind list comes from grepping `F.get` / `F.kind` / `F.of_project` across `rules_code`.

**Fix.**
- Restate the stage 1 position. The S04 reference intake covers 11 kinds. The phase-1 kinds read by rules enter through milestone intakes under `apg/fin` and `apg/det`, plus two direct writers.
- Recount "built" against the S04 intake: 6 of 21. Alternatively, define "built" honestly, for example "a synthetic template exists".
- Add to "What this amendment adds": SPECS, reconciliation and authority rules for the 16 kinds, and entity resolution beyond suppliers (S04 §11 lists projects, contracts, variations, activities and defects).
- Reword AC-03 so that the planned migration of `apg/fin/intake.py` and `apg/det/intake.py` is allowed, while rule and figure logic stays fixed.

### 2. BLOCKING: the script reads entity ranges as two endpoints, so phase 2 is short by five entities. "Mechanical, from revision 3's input contracts" is not true as coded.

**Quote.**
- Line 104: "Also mechanical, from revision 3's input contracts".
- Lines 114–115 and 163: "Phase 2 (17 entities) … root cause and closure of defects", "the programme (versions, calendars, progress)".

**What is wrong.**
- `ids()` (script line 17) is `re.findall(r'E\d\d')`. The known-limit text "E47 to E50" (DLY) therefore yields only E47 and E50, and "E68 to E72" (DEF) yields only E68 and E72.
- Applying the draft's own rule (anything that closes a known limit goes to phase 2) adds E48 programme activity, E49 activity dependency, E69 confirmed cause, E70 rectification action and E71 quality cost.
- The current plan is also internally inconsistent. Phase-2 progress records (E51) link to activities (E48, register "links to"), but E48 is in "later".

**Evidence.**
- RULE_INPUT_CONTRACTS.csv line 37 (DLY: "calendar days only (E47 to E50)") and line 39 (DEF: "(E68 to E72)").
- Recomputed with ranges expanded, the phases are 1 = 29, 2 = 22, later = 43, optional = 5.
- Corrected phase-2 row: 3 built or partly built; 19 not built (12 templates, 4 entry screens, 1 setup question, 2 APG records).
- Corrected later row: 21 built or partly built; 22 not built (8 T, 4 E, 5 S, 5 A).
- Corrected template sentence: "14 of the 22, of which 12 still to build".
- The overall 48/51 does not change.

**Fix.**
- Expand ranges in `ids()`.
- Regenerate the CSVs and every count in lines 111–117 and 163, after findings 3–5 are applied as well.

### 3. BLOCKING: "Phase 1 feeds every current rule and financial figure" leaves out the current M6 market figures. Their inputs are labelled "needed by insights not yet built".

**Quote.**
- Line 143: "Phase 1 feeds every current rule and financial figure".
- Line 165: "Later (48 entities). These feed insights the blueprint specifies but stage 1 has not built".

**What is wrong.**
- Revision 3 says the M6 market figures (landed cost, indicative comparison, buy timing) exist but that their contracts are not written. Six M6 templates exist.
- The phase rule reads only the 39 contract rows. The M6 inputs therefore fall into "later", with SUPPLY_PLAN reason "needed by insights not yet built". That is false for:
  - E33 landed-cost component and E34 import check (both "covered");
  - E31 and E32 quote tiers and terms;
  - E36 market observation and E37 FX rate (both in SPECS);
  - E26 material and E28 material demand;
  - probably E35 quote reading as well.

**Evidence.**
- CR_REV3_DOC_EXPORT.md lines 12, 54 and 114 (36 templates including "6 M6 supplements").
- SUPPLY_PLAN.csv rows E26, E28 and E31–E37.

**Fix.**
- Either write the M6 input contracts first, or state plainly that phase 1 covers the 29 contracted rules and figures and not M6.
- Correct the "why this phase" text for these entities and the sentence on line 165.

### 4. BLOCKING: the supplier master (E20) is missing from phase 1, yet without it no invoice, credit, order or quote can be used.

**Quote.**
- Line 106: "Phase 1: what a current rule or financial figure reads …".
- Line 147: phase-1 build item 1 lists the templates to check and does not include suppliers.

**What is wrong.**
- With the default `supplier_master_required=True`, `reconcile` holds every supplier-bearing record as `SUPPLIER_UNVERIFIABLE_NO_MASTER` when no supplier list has been ingested. That covers ap_invoice, credit_note, purchase_order, supplier_quote and pm_invoice.
- So M4 actual cost, commitments, R03, R07 and AGG get no usable records without E20.
- R06 also reads the supplier record directly (contract field "supplier supplier_name").
- E20 is in "later" only because the phase rule reads the `entity` column and not the `record kinds and fields` column, and because the intake's own dependencies are not counted.

**Evidence.**
- `reconcile.py` lines 31 and 148–150.
- `rules_commercial.py` lines 148–149.
- RULE_INPUT_CONTRACTS.csv R06 row.
- SUPPLY_PLAN.csv E20: later, template exists.

**Fix.**
- Put E20 in phase 1 (it already has a template).
- Change the phase rule to include what the intake itself needs in order to accept a phase-1 record, and the entities named in the "record kinds and fields" column.

### 5. BLOCKING: detection-rule parameters and other configuration the contracts name have no entity and no way in. The phase-1 check cannot see them.

**Quote.**
- Line 143: "every configuration its contract names has a Level 1 way in in phase 1. All 39 pass".

**What is wrong.**
- The script picks up configuration only when it carries an E-number, which finds just E90, E04 and E03.
- 27 contract rows name configuration without an E-number. Some are policy fields that plausibly belong to E90 (cost_scope, po_status_map, ctc_method, carrying, cash_adjustment, credit_reopens_commitment).
- But every detection rule also needs its parameters (tolerance_bps, unresolved_days, instruction_types, warning_days, min_excess_days, window_days, baseline_weeks and others).
- R07 also needs "pairs declared comparable by a person", which is a human declaration.
- These parameters are passed as `dp` to `C.start`. When the rule is not configured, the rule returns nothing (`if rule is None: return [], run`).
- No entity in the register holds them. E90's field groups do not include rule thresholds or comparable pairs. No setup question or entry screen supplies them.
- So the statement that the check covers "every configuration its contract names" is not true.

**Evidence.**
- Recomputed: 27 rows have configuration text with no E-number.
- `rules_cost.py` lines 33–36 (the same pattern appears in every rule).
- ENTITY_REGISTER.csv E90 "required field groups".
- `apg/det/common.py` is not in the pack, so where `dp` comes from cannot be confirmed.

**Fix.**
- Add an entity for detection parameters (with R07 comparable pairs and R04B instruction types), give it a setup-question way in, and place it in phase 1.
- Map the named policy fields to E90 explicitly.
- Restrict the claim to what the check actually tests.

### 6. BLOCKING: "the rules never change for a new way in" conflicts with the phase plan. Receivables in phase 1, and phase 2 as a whole, need rule and figure code changes.

**Quote.**
- Line 19: "The rules never change for a new way in."
- Line 11: "Out of scope: … changes to any detection rule or figure".
- Line 147: "one new template for receivables and receipts (E15)".
- Line 161: "Phase 2 lifts the known limits of today's insights."
- PG-DS-AC-03: "changes no file under `apg/det` or `apg/fin`".

**What is wrong.**
- `build_overdue_receivables` returns `cannot('NO_RECEIVABLES_DATA')` unconditionally and reads no record. The contract row's `record kinds and fields` is "-". E15 counts as "read by a current rule" only because the `entity` column names it. A receivables template on its own changes no figure. The same applies to security carrying cost (always "cannot").
- Every phase-2 limit-closer needs the consuming code changed before it has any effect:
  - claims and certificates (E13, E14): `revenue.py` reads only contract plus approved variations;
  - accruals and overhead (E42, E43): `costs.py` reads supplier invoices only (F-17);
  - deliveries (E29): `commitments.py` reads no receipt data;
  - calendars and programme (E47 to E50): DLY uses calendar days;
  - retention from trades (E76) and payables, payroll and statutory outflows (E79 to E81): `cashview.py`.
- Phase 2 as described therefore breaks rule 3, AC-03 and the scope statement.

**Evidence.**
- `rules_code/fin/cashview.py` lines 172–174 and 134–135.
- `revenue.py` line 32.
- RULE_INPUT_CONTRACTS.csv "known limit" column.

**Fix.**
- State that supplying a limit-closing entity has no effect until the consuming rule or figure changes, and that each such change is a Section 18 CR with its own tests.
- Move E15 to phase 2 alongside E13 and E14, or name the figure change it needs.
- Reword rule 3 to say that adding a way in never changes a rule. Extending a rule to use new data is a separate, governed change.

### 7. SHOULD FIX: the phase-1 check is circular, and the draft overstates what it shows.

**Quote.**
- Line 143: "The script checks this … All 39 pass … The check follows from the phase rule by design; its value is that no current insight is shown to need phone capture or an integration."

**What is wrong.**
- The check cannot fail for any register:
  - P1 is defined as a superset of read ∪ config (script line 21);
  - the minimum is chosen only from Level 1 codes (line 32);
  - `assert l1` (line 33) already aborts if any entity has no Level 1 code.
- The "value" the draft claims is therefore also true by construction. It restates that rev3's register lists some Level 1 code for each entity, which rev3 designed in.
- The check also has these gaps:
  - it ignores build state ("fed in phase 1: yes" for E02, E03, E04 and E15, which are proposed);
  - it passes 6 rows vacuously with no entity checked (forecast final margin, recognised margin, cash-adjusted margin, R01, D01, D02);
  - it ignores the `record kinds and fields` column (finding 4) and non-E-number configuration (finding 5);
  - it says nothing about fields (for example E23 has no line quantity or rate, F-09).
- "The script checks this" (that phase 1 feeds every rule) is an overclaim.

**Evidence.**
- `build_supply_plan.py` lines 21, 32–33 and 58–61.
- PHASE1_CHECK.csv rows with "-" in the entities column.

**Fix.**
- Say plainly that the check is a consistency check of the plan against the register and cannot fail by construction.
- Either drop it, or make it test something independent: the `record kinds and fields` column, configuration names, whether the intake accepts the kind (finding 1), and the build state per input.
- Add a test that proves the check can fail.

### 8. SHOULD FIX: retention events (E77) take "APG creates" as their minimum way in, but a person records them. The class-I preference rule gives other wrong minimums as well.

**Quote.**
- Line 76: "Records APG creates … APG generates these from other records; the builder never types them."
- Line 149: "finishing … retention events (E77)".

**What is wrong.**
- A retention event (claimed, approved, released) is recorded by a named person with role and evidence. `record_event` stores `actor: ctx.user_id`.
- The register gap is "no entry screen to record the events", and the contract's known limit says the same.
- The minimum phase-1 build has no entry screen, so a builder cannot record E77 at all.
- `record_event` also writes straight to the store with `scoped.put`. That is outside the S04 intake and conflicts with AC-01.
- The same rule ("class I → A where listed") picks "APG creates" for E88 Outcome, which S10 §10 says needs human verification. It also picks it for E71 quality cost, which includes observed amounts, and for E68 and E97. E69 and E87 (class I, entry screen only) contradict "the builder never types them".

**Evidence.**
- `rules_code/fin/cash_states.py` lines 82–95.
- ENTITY_REGISTER.csv rows E77, E69, E87 and E88.
- RULE_INPUT_CONTRACTS.csv line 18.

**Fix.**
- Make E77's minimum the entry screen, and add it to the phase-1 minimum or flag it as the gap.
- Route `record_event` through the intake.
- Review the class-I preference so that facts people record are not labelled APG-created.
- Correct line 76.

### 9. SHOULD FIX: Organisation, users and roles (E05) are left in "later", but every approval in the design needs roles.

**Quote.**
- Line 74: "approved by the owner's approver role".
- Line 60: "A person confirms …".
- Line 33: "route it for approval".

**What is wrong.**
- E05 ("tenant, users, roles", no setup screen) is in "later".
- The stage 1 controls need named roles: `authority_owner` for the register, `document_verifier`, `reconciler` and `entity_steward`.
- Section 18 §8 puts identity, tenant isolation and permissions in its first control phase.
- A "first usable release" without them cannot approve anything. This may belong to the Anchor platform rather than APG. If so, the draft should say so.

**Evidence.**
- SUPPLY_PLAN.csv E05.
- `source_authority.py` line 93.
- `documents.py` line 13.
- `review.py` line 7.
- `demo_setup.py` line 11.
- Section_18.txt lines 272–274.

**Fix.**
- Place E05 (users and roles) in phase 1, or state that it comes from the platform under Section 01.

### 10. SHOULD FIX: "built" and "partly built" overstate what works for document capture, setup and templates.

**Quote.**
- Line 57: "Document and email capture (17 built or partly, 6 not)".
- Line 114: phase 2 "1 document capture (subcontracts)" counted as built.
- Line 51: "a CSV or spreadsheet … saved to Excel".

**What is wrong.**
- All 17 D paths are "partly", and none exists. The only built pieces are:
  - the generic verification control;
  - a stand-in text parser for quotes (`MATERIAL_FIELDS` are quote fields);
  - no link from extraction into the pipeline.
- E16 subcontract is counted as a built or partly built minimum, but no subcontract record kind exists (register: "purchase_order serves for orders; no subcontract kind").
- E90's "setup question (partly)" is a policy object with "no builder setup".
- The mapping code accepts CSV only (`file.type == 'csv'`). Excel files, and the XER or MS Project XML named in the register for E47 to E49, are not accepted today.

**Evidence.**
- `documents.py` lines 1–17 and 46–64.
- `mapping.py` lines 103–104.
- ENTITY_REGISTER.csv E16 and E90.
- golden_m3.py (documents and pipeline are used separately).

**Fix.**
- Say in plain words what "partly" means for each way in.
- Do not count E16 as built.
- Say that import is CSV only today.

### 11. SHOULD FIX: the recommended phase-1 document capture leaves out real extraction and the document record.

**Quote.**
- Line 155: "Document and email capture, finished: the inbox and the verification screen …"
- Compare line 61: "The gap is the inbox, real extraction and the verification screen."

**What is wrong.**
- The recommendation drops real extraction. That needs an OCR or AI vendor and the Engine (EDR-22).
- Without it, a person keys every value. The feature is then an entry screen with an attachment, and the stated benefit in line 157 is overstated.
- E83 Document (the original file and its hash) and E35 Quote reading would be needed in phase 1 under this option, but both are "later".

**Evidence.**
- `documents.py` lines 8–9.
- SUPPLY_PLAN.csv E35 and E83.

**Fix.**
- Make line 155 match line 61.
- Add E83 and E35 to the "minimum plus" option.
- State the vendor dependency.

### 12. SHOULD FIX: the Section 01 gate is moved from "before feature code" to "before production use".

**Quote.**
- Line 201: "the Section 01 discovery gate (S04 §16, §20) all come before any production use."

**What is wrong.**
- S04 §20 says "Do not begin production feature code or core integration logic until Section 01's Discovery Exit Report is signed off."
- Revision 3's status line states this correctly.
- Under the draft's wording, the phase-1 build (mapping screen, setup, inbox) could appear able to start before discovery.

**Evidence.**
- S04.txt line 170.
- CR_REV3_DOC_EXPORT.md line 7.

**Fix.**
- Quote §20 accurately.
- State that every phase-1 build item waits for the Discovery Exit Report and the owner's authorisation.

### 13. SHOULD FIX: S04 §6, §16 and §18 controls for the new channels are not addressed, and neither is privacy.

**Quote.**
- Line 59: "forwards an email to an APG address for their organisation".
- Line 83: "The person, time, place and any photo are kept as evidence."

**What is wrong.**
- Email: the tenant is taken from the receiving address, which is a payload-supplied identifier. S04 §6 forbids trusting that "without validating them against the authenticated integration context". Sender spoofing is not addressed.
- Phone capture: device identity, trust in the device clock, and offline capture are not discussed.
- Malware and content-handling controls (§18) for uploads, emails and photos are not mentioned. The stage 1 scan-gated path (`filestore.py` / FileStorePort) exists but is not cited.
- Tenant isolation must be tested on every new path (§16, PG-DI-AC-14).
- Location data and photos of workers raise the labour-privacy rule (S09 §14, flagged by rev3 line 169). The draft does not mention it.
- The intake table (lines 29–39) also omits S04 §3's first stage, "Source registration and connector authentication/authorisation".

**Evidence.**
- S04.txt lines 24, 57–59, 131–133 and 147.
- `ports_m3.py` lines 4–9.
- CR_REV3_DOC_EXPORT.md line 169.

**Fix.**
- Add an authentication and tenant-binding row to the intake table, with a design note per channel (email sender verification, device enrolment, scan before parse).
- Add the privacy constraints for phone capture.

### 14. SHOULD FIX: using the general entry screen to correct a held record would bypass the review workflow.

**Quote.**
- Line 154: "The general entry screen … and for correcting a held record."

**What is wrong.**
- S04 §9 and §13 require promotion and corrections to be governed: resolution, the required approvals and a recorded disposition.
- In stage 1, a correction happens only through the review queue (`review.decide` → `QuarantineQueue.dispose`), with a role, distinct approvers and a blocking digest. The reconcile docstring says "a human correction replaces it only through the review queue".
- A generic form that writes a corrected value would sidestep this.

**Evidence.**
- S04.txt lines 80–82 and 114.
- `reconcile.py` line 7.
- `review.py` lines 11–21.

**Fix.**
- State that corrections of held records go through the review queue's roles and approvals. The entry feature may only open that workflow.

### 15. SHOULD FIX: import rows are described as accepted or rejected, but S04 §8 has five outcomes.

**Quote.**
- Line 54: "Each row is accepted or rejected with a reason the builder can fix."

**What is wrong.**
- The pipeline also stores rows as accepted with warnings or pending reconciliation (held at intake), and conflicts are quarantined.
- A non-technical reader would think a row is either in or out. The draft's own line 34 says "five outcomes".

**Evidence.**
- `pipeline.py` lines 103–106 and 186–187.
- S04.txt line 73.

**Fix.**
- Say "each row gets one of the five Section 04 outcomes, with the reason".

### 16. SHOULD FIX: PG-DS-AC-01, 02 and 03 conflict with the blueprint or with the code.

**Quote.** Lines 184–186.

**What is wrong.**
- **AC-02** ("the same fact … through any two ways in gives the same canonical record and the same rule outcome") conflicts with S04 §5 and with the draft's own line 178. Authority is per source and field, so the same value from an informational source must not become authoritative.
- It also conflicts with §12. A document-captured value is unverified, and so quarantined or provisional, until a person confirms it. The same value from an approved template is accepted.
- And it conflicts with AC-04, because provenance differs by channel, so the canonical record is not "the same".
- **AC-01** ("nothing writes canonical records directly") is already broken by `cash_states.record_event` and `source_authority.ingest_batch`. It also does not say how "records APG creates" (findings, readiness, baselines) are written. The diagram places them under the intake.
- **AC-03** conflicts with findings 1 and 6.

**Evidence.**
- S04.txt lines 47 and 103–108.
- `cash_states.py` line 92.
- `source_authority.py` line 364.

**Fix.**
- **AC-02**: "once the same authority and verification conditions are met, the same field values and the same rule outcome result; only provenance differs".
- **AC-01**: scope it to supplied facts, and state how APG-derived records are written.
- **AC-03**: reword it as in finding 1.

### 17. SHOULD FIX: the acceptance criteria are too narrow and leave out key Section 04 controls.

**Quote.** Lines 182–190.

**What is wrong.**
- **AC-05** covers only entry screens and phone capture. S04 §18 covers manual uploads and controlled entry, which includes templates and documents. Setup answers matter most of all: they set the authority register and the policy maps that stop or start figures. They have no acceptance criterion for approval and versioning.
- **AC-06** covers only "after every intake". Line 131 also names setup, schedule, correction, quarantine, supersession and revocation.
- There are no criteria for:
  - applicability of PG-DI-AC-01 to 18 to every way in;
  - tenant isolation per new channel (PG-DI-AC-14);
  - human verification of extracted values (PG-DI-AC-07);
  - quarantine and provisional isolation for manual values (PG-DI-AC-03 to 05);
  - file scanning;
  - readiness correctness (an insight is never shown as eligible while an input is missing, unverified or stale);
  - the nudge noise control in finding 18.

**Evidence.**
- S04.txt lines 144–166.
- Draft line 131.

**Fix.**
- Widen AC-05 to all manual ways in, including setup.
- Align AC-06 with line 131.
- Add the missing criteria, each with a test.

### 18. SHOULD FIX: nudges and the missing-data list do not follow S06 §9.1 or S10 §4.

**Quote.**
- Line 136: "A missing-data list, ranked by money at risk together with urgency …"
- Line 137: "Nudges …"

**What is wrong.**
- A missing input is a data-integrity finding in the S06 §4 taxonomy. S06 §9.1 is mandatory: repeated detections must update the existing item rather than create new notifications, with suppression and re-notification rules.
- The design reassesses readiness after every intake, so nudges could repeat on every cycle.
- S10 §4 requires the dimensions to be shown separately and not collapsed into one unexplained score. "Ranked by … together with" reads like a composite ranking.
- "Money at risk" for a data gap sits close to the S06 §4 rule that a gap is not a loss.

**Evidence.**
- S06.txt lines 36–37 and 98–99.
- S10.txt lines 19–30.

**Fix.**
- Add deduplication and suppression rules for nudges.
- Show the ranking factors separately.
- Call the money factor "amount affected", not "at risk".

### 19. SHOULD FIX: there is no Section 18 cascade impact assessment, yet the owner is asked to approve.

**Quote.**
- Line 210: "This amendment and revision 3 go through Section 18's change process (S18 §6)".
- Decisions 1, 3 and 4 (lines 206–209).

**What is wrong.**
- S18 §6 says "A CR must not be approved until the cascade assessment is complete." The assessment must name the affected locked sections, requirement IDs, RTM rows, tests and fixtures.
- The draft names no affected requirement IDs.
- It creates a new acceptance namespace (PG-DS-AC) with no RTM rows.
- It asks the owner to approve the architecture, phase rule and acceptance criteria before any of this exists.

**Evidence.** Section_18.txt lines 187–219.

**Fix.**
- Present decisions 1, 3 and 4 as approvals in principle.
- List the affected sections. At least: S04 (new ways in and acceptance criteria), S06 and S10 (readiness, nudges), S03 and 8-layer 11.2 (new entities including E89), and the RTM.
- Make the cascade impact assessment a stated precondition for approval.

### 20. SHOULD FIX: the draft changes revision 3's position on phone capture without saying so.

**Quote.**
- Line 18: "Phone site capture and integrations add convenience on top."
- Line 169: build phone capture when "discovery shows …".

**What is wrong.**
- Revision 3 lists phone site capture among the APG paths in its design principle.
- Rev3 decision 3 asks the owner to approve it "as required features, not add-ons".
- Rev3 also states that phone capture is "the designed path that depends on no system" for site-level records.
- The draft demotes it to Level 2 and defers it, which may be reasonable. But it does not record this as a change from rev3, which the owner may already be approving.

**Evidence.** CR_REV3_DOC_EXPORT.md lines 22, 103 and 162.

**Fix.**
- State the change and the reason: every phone-served entity also has an entry screen or template.
- Reconcile it with rev3 decision 3.

### 21. SHOULD FIX: "Phase 1 / Phase 2" collides with Section 18's phases and with "stage" and milestone terms.

**Quote.** Line 141: "Phase 1: the first usable release", and the "Phase" columns throughout.

**What is wrong.**
- Section 18 §8 already defines "Phase 1 — Control foundations" and "Phase 2 — Authoritative financial core".
- The draft also uses "stage 1 / stage 2" (lines 7 and 25) and the code uses M2, M3 and M4.
- A non-technical owner reading "phase 1" will not know which scheme is meant.

**Evidence.** Section_18.txt lines 257–294.

**Fix.**
- Rename the phases, for example "Supply release A / B / later".
- Add one line that maps them to Section 18's phases.

### 22. SHOULD FIX: several unbuilt features are written in the present tense, as if they work.

**Quotes and what is wrong.**
- Line 18: "Each of the 99 entities can be supplied through at least one Level 1 way in". Today, 51 entities can be supplied only through a way in that is not built.
- Line 139: "until instruction capture is built its results say 'recorded instructions only'". R04B does not produce this label. It is a designed readiness behaviour (rev3: "will be labelled").
- Line 123: "It joins three things that already exist". The supply plan is this draft, and the intake states exist for 11 kinds only (finding 1).
- Line 37: "The owner's thresholds (revision 3's table)". These are values proposed for the owner to set (rev3 decision 5), not yet set.

**Evidence.**
- `rules_commercial.py` r04b (lines 60–100; there is no such label).
- CR_REV3_DOC_EXPORT.md lines 133, 135 and 164.

**Fix.**
- Use "has a designed …", "will say", "proposed thresholds".

### 23. MINOR: templates and entities are confused.

**Quote.** Line 147: "the 21 existing templates".

**What is wrong.** 21 is a count of entities with a template that exists. Rev3 counts 36 template files covering 37 entities, and one kind can serve two entities (notice serves E10 and E11).

**Evidence.** CR_REV3_DOC_EXPORT.md line 114.

**Fix.** "the existing templates for 21 entities".

### 24. MINOR: file paths are inconsistent and unqualified.

**Quote.** `ingest/pipeline.py` alongside `apg/source_authority.py` (lines 31–39).

**What is wrong.** The prefixes are mixed. The pack holds these files under `stage1_ingest_code/`. Rev3 says source_authority.py was "not read for this revision".

**Evidence.** ENTITY_REGISTER.csv E03 and E83.

**Fix.** Use one path convention and note which files the reviewer can see.

### 25. MINOR: the survey is described as "16 builder systems".

**Quote.** Line 9: "the survey of 16 builder systems".

**What is wrong.** The survey covers 16 systems that builders and developers use. They include EstateMaster, Excel and email, and the survey also lists 2 data sources (BANK, EXT).

**Evidence.**
- SYSTEMS_SURVEY.csv (18 rows).
- Rev3 line 13.

**Fix.** Use rev3's wording.

### 26. MINOR: "source profile (S04 §4)".

**Quote.** Line 90.

**What is wrong.** S04 §4 defines a "source registry", not a "source profile". "Source profile" is a rev2 term.

**Fix.** Say "a source registry entry (S04 §4), described in revision 2 as a source profile".

### 27. MINOR: the S06 §4 citation is too broad.

**Quote.** Line 137: "A money figure in a nudge comes from a traceable calculation, and a data gap is never called confirmed leakage (S06 §4)".

**What is wrong.** S06 §4 supports only the second half. The traceable-calculation requirement is S06 §2 and §7 (PG-AI-AC-06).

**Fix.** Cite both sections.

### 28. MINOR: the diagram cannot be reviewed in the export.

**Quote.** Line 41: `&#91;embedded content: … \]`

**What is wrong.**
- GPT and the owner reviewing the export cannot see the diagram, and the bracket is escaped.
- As described, the diagram puts "Records APG creates" under the intake, which conflicts with finding 16.

**Fix.** Add a text description or an image to the export, and show APG-derived records as derived, not supplied.

### 29. MINOR: minimum-rule step 2 is stated without its condition.

**Quote.** Line 101: "A record APG keeps itself takes 'APG creates'."

**What is wrong.** The script applies this only "where listed". E69 and E87 have no A path.

**Evidence.** `build_supply_plan.py` lines 34–36.

**Fix.** Add "where the register lists one".

### 30. MINOR: an unexplained reference to GPT.

**Quote.** Line 25: "The shared intake GPT describes already exists."

**What is wrong.** GPT's description is not in the pack, and the reader does not know what it refers to.

**Fix.** Drop the reference or quote it.

### 31. MINOR: Payapps is named as a feed.

**Quote.** Line 88: "Recurring feeds from … Payapps".

**What is wrong.** The survey says "no API or export described; access to confirm with the vendor".

**Evidence.** SYSTEMS_SURVEY.csv, Payapps row.

**Fix.** Mark it "to confirm".

### 32. MINOR: the onboarding checklist wording.

**Quote.** Line 135: "APG shows which insights those systems can feed … This is the survey's judgement".

**What is wrong.**
- Until AUIF exists, a system can feed APG only through its export file and an unverified template. Under AC-07 the checklist must not imply that a feed is available.
- "The survey's judgement" mixes sourced survey entries with Claude's "likely also" column.

**Fix.** Say "through its export file and a template", and label the judgement column as Claude's.

### 33. MINOR: "a person" should be an authorised person.

**Quote.** Line 60: "A person confirms or corrects every material value".

**What is wrong.**
- S04 §12 and the code require an authorised human (role `document_verifier`).
- `verify_field` takes only a whole number or text. Dates such as `valid_until` cannot be verified as dates yet.

**Evidence.** `documents.py` lines 79–85.

**Fix.** Say "an authorised person (verifier role)", and note the date gap.

### 34. MINOR: the template "draft" status lock affects phase-1 build item 1.

**Quote.** Line 147: "the 21 existing templates checked and adjusted against one real builder's files".

**What is wrong.** `validate_template` refuses any template whose status does not start with "draft". A template promoted after checking against real files would be refused until `mapping.py` changes.

**Evidence.** `mapping.py` lines 95–96.

**Fix.** Add this to item 1.

### 35. OPTIONAL: the readiness record's basis.

**What is missing.** Revision 3 says revision 2's per-insight contracts (gate, completeness, freshness, verification, behaviour below the gate) "remain in force". These are what define eligible, qualified, blocked and unavailable. The draft cites only the rev3 input contracts and does not say that M6 figures cannot yet have a readiness record.

**Evidence.** CR_REV3_DOC_EXPORT.md line 78.

**Fix.** Name both sets of contracts, and note the M6 gap.

### 36. OPTIONAL: API documentation for new channels.

**What is missing.** The 8-layer section 11.6 requires each proposed endpoint to be documented: purpose, schema, authentication, validation, errors, audit, idempotency and tests. The entry, email and phone channels will need this.

**Fix.** Add one line to "What this amendment adds".

### 37. OPTIONAL: regenerate everything after the fixes.

**Why.** Findings 2–6 and 8–9 change the phase membership. The phase table, line 163, PHASE1_CHECK.csv and the "five file-only facts" (E20 adds a sixth candidate, although E20 also has an entry screen) all need recomputing.

**Fix.** Add a test that fails when the register changes in a way the plan does not reflect.

---

## Totals

| Class | Count | Findings |
| --- | --- | --- |
| BLOCKING | 6 | 1–6 |
| SHOULD FIX | 16 | 7–22 |
| MINOR | 12 | 23–34 |
| OPTIONAL | 3 | 35–37 |
| **Total** | **37** | |

## Verdict

Draft 1 is honest in tone: no build authorised, no cost estimate, synthetic data flagged. Its arithmetic matches its own script exactly. The script itself regenerates the CSVs byte for byte.

The supply plan is not yet sound, because the phase rule rests on an incomplete and partly mis-parsed reading of the contracts:

- it drops five phase-2 entities;
- it leaves the supplier master, detection parameters and the current M6 figures out of phase 1;
- it places receivables in phase 1 although no figure reads them;
- its phase-1 check cannot fail.

The architecture claim that a working shared Section 04 intake already exists does not match the stage 1 code. That intake accepts 11 record kinds, while most phase-1 rule inputs arrive through separate intakes under `apg/fin` and `apg/det`. The "rules never change" principle, with PG-DS-AC-03, also conflicts with phase 2, whose stated purpose needs rule and figure changes.

These six blocking points, and the S04 §20, §6 and §9 gaps, should be fixed and the plan regenerated before the package goes to GPT. The design direction itself (one intake, many ways in, a core way in for every entity) is sound and consistent with Section 04.
