# INDEPENDENT READ-ONLY (agent) audit: APG Data Readiness Change Request, revision 3

Pack: `.../dd/pack3/APG_DATA_READINESS_CR_REV3_PACK/`. Section texts: `.../dd/in/txt/Section_XX.txt`. The only file written is this report. CSV counts were recomputed with `python3 -I`. The 13 survey source URLs were fetched read-only on 2026-11-12. "Doc Lnn" means a line of `01_CHANGE_REQUEST_REV3.md`. "RIC Lnn" means a file line of `RULE_INPUT_CONTRACTS.csv` (the header is L1).

## Findings

### Entity register and blueprint coverage

**1. BLOCKING: two entities named in the sources GPT cited for blocking 1 have no row.**
- **Location:** ENTITY_REGISTER.csv; Doc L11, L31, L186.
- **Problem:** 8-layer §11.2 lists **FinancialRecord** as a core logical entity, and no row maps to it (no row cites "8-layer 11 FinancialRecord"). Its `value_status` enum (actual, committed, forecast, assumption, claimed, disputed, potential, scenario) is the cross-cutting state model. Section 13 §13.3 lists nine distinct records, but the register has eight (E65 to E72). **Prevention opportunity** is missing. E86 Recommendation cites S10 only.
- **Evidence:** `05_blueprint_sources/11_DATA_CONTRACTS_AND_INTERFACES.md` "### FinancialRecord". `Section_13.txt` L81-109 ("Prevention opportunity — a recommendation to reduce the likelihood..."). Doc L186: "quality: E65 to E72".
- **Fix:** Add a FinancialRecord row (or state explicitly which rows realise it and how `value_status` is carried), and add a Prevention opportunity row. Then recompute 95 / 12 / 37 / 46, the class table, 38 / 9 / 48 and the path counts.

**2. SHOULD FIX: S03 §2 canonical entities have no row (work package, schedule milestone).**
- **Location:** ENTITY_REGISTER.csv.
- **Problem:** Section 03 §2's entity table, which the register cites throughout as "S03 s2", includes Work package, Schedule milestone and Calculation run. No row covers Work package, even though timesheet, work_output, S09 §3 work allocation and S13 §13.3 ("Each record must preserve its project, work package, location...") all key on it. Milestones (S03 §2; S07 §3 "relevant milestones and contractual dates") have no row either.
- **Evidence:** `Section_03.txt` L32-120. `FIELD_REGISTER.csv` (`work_package_ref` on timesheet and work_output).
- **Fix:** Add rows for Work package and Schedule milestone/contractual date, or say which rows carry them. Map Calculation run to E45 explicitly.

**3. SHOULD FIX: "16 entities not clearly held by any system" is a by-product of the survey's entity lists, not a finding.**
- **Location:** Doc L79, L100; ENTITY_REGISTER "usually held in"; build_entities.py.
- **Problem:** The "usually held in" column is not authored per entity. It is rebuilt as a reverse index of SYSTEMS_SURVEY's entity lists. The authored judgement in `ROWS` column 9 is thrown away, and any entity the survey rows did not happen to tag becomes "no surveyed system: APG capture only".
  - The authored values contradict the output. E29 Delivery was authored 'PM, SITE'. E51 Progress was 'SCH, PM, SITE'. E56 Crew was 'SITE, PAY'. E58 was 'SITE, PM'. E61 was 'SITE, PM'. E64 was 'PM, ACC, SITE'. E67 was 'SITE, PM'. E27 was 'DOC, EST'. E34 was 'DOC'. E92 was 'DEV, ACC'. E93 was 'DEV, BANK'. All 11 come out as "no surveyed system". Likewise E04 was authored 'ERP, ACC, XLS' but comes out as 'XLS'.
  - The survey itself contradicts the conclusion for progress: the P6 row says "actual dates and percent complete to confirm in a sample file", and HammerTech syncs site diaries.
  - So the Doc L100 conclusion ("the site-level records that no system holds can only come from APG's own capture") is not supported.
- **Evidence:** `build_entities.py` L119-127 (`held = ', '.join(sorted(HELD[r[0]])) or (...'no surveyed system: APG capture only')`, which ignores r[8]). Compare the ROWS entries for E29, E51 and E64.
- **Fix:** Either use the authored column, merged with the survey, or retag the survey rows. Then recompute the 16 and its 7 / 4 / 3 / 2 split, and soften L100 to "not shown in any surveyed system's documentation".

**4. SHOULD FIX: the design principle fails for programme entities.**
- **Location:** Doc L14, L22; E47, E48, E49.
- **Problem:** The principle says every entity has "at least one way to supply it inside APG [that] does not depend on the builder's software". E47 Programme version offers only "T (XER or MS Project XML), I". E48 and E49 offer only "T, I". A P6 or MS Project export template depends on the builder's scheduling software. There is no E (entry) or P (phone) path for versions, activities or dependencies, so a builder without scheduling software has no path.
- **Fix:** Add an entry or spreadsheet path (a simple activity and dependency template), or narrow the principle.

**5. SHOULD FIX: "38 can be supplied today" overstates what is suppliable.**
- **Location:** Doc L16, L104.
- **Problem:** 27 of the 38 entities with a built path have status partial: the built template carries only some of their required field groups. Examples: E07 (no legal entity, type, currency) and E08 (no terms, clauses). Only 11 of the 38 are covered.
- **Fix:** Say "38 have a built path for the fields APG holds today (11 complete, 27 partial)".

**6. SHOULD FIX: E35 path is mislabelled, which changes the headline counts.**
- **Location:** E35.
- **Problem:** quote_reading has an import template (TPL-MKT-QUOTE-READINGS, 7 fields), but E35 lists only "D / D partly". Every other template-backed kind has "T exists".
- **Evidence:** `TEMPLATE_REGISTER.csv` (TPL-MKT-QUOTE-READINGS, record_kind quote_reading).
- **Fix:** Set E35 to "T, D / T exists; D partly". The counts then become 39 built / 8 partly / 48 proposed, and template-only 37, if E35 is counted as template-only.

**7. SHOULD FIX: "new import templates (29)" is wrong.**
- **Location:** Doc L16.
- **Problem:** Entities that list T without "T exists" number 27: 22 "T proposed" plus 5 developer rows. 63 entities list T and 36 have it existing.
- **Fix:** Correct to 27, or state what 29 counts.
- **Other path counts:** entry screens 40, integrations 24, phone 14 and setup 11 (12 listed, 1 partly) are correct.
- **Chart:** the "[chart in the Claude doc]" (Doc L106) is not in the pack, so its values could not be checked. Recomputed built / not built per path: T 36/27, E 0/40, I 0/24, D 17/5, A 7/8, P 0/14, S 1/11. If the chart shows D as 16/6 it is off by one.

**8. SHOULD FIX: blueprint section references are off by one in several rows.**
- **Location:** ENTITY_REGISTER blueprint column.
- **Problem:** Checked against the section texts:
  - E74 Funding facility "S12 s10" should be s7 (§12.10 is payment delays and receivables; §12.7 is financing).
  - E75, E76 and E77 "S12 s7" should be s8 (§12.8 Retention intelligence).
  - E78 "S12 s8-9" should be s9.
  - E46 Scenario "S12 s13" should be §12.11 (or S05 §11, S10 §7.1); §12.13 is integration.
  - E68 and E69 "S13 s6" should be s7 (§13.6 is baseline and counterfactual; §13.7 is root cause).
  - E70 Rectification "S13 s7" should be s8.
  - E11 Contract notice "S07 s3; S11 s6" should be S07 §11 and S11 §7.
  - E12 Deadline "S11 s6, s7.1" should be s7 and s7.1.
  - E08 Head contract "S11 s4" should be s3 (contract and commercial baseline).
  - E10 "S11 s4-5": §5 is progress claims.
  - E28 Material demand "S08 s5" should be s4.
  - E29 Delivery "S08 s5" should be §9 or §13 (S03 §8.2).
  - E34 Import compliance "S08 s6" should be §12.
  - E64 Plant hire "S07 s5" should be §6 (S06 §5.2 rule 8).
  - E36 "S03 s11.1" and E80 "S03 s11.4" are weak (currency; tax inclusions).
  - Notation is inconsistent: "S12 s3-5" and "S12 s12.4-12.5" refer to the same numbering scheme.
- **Evidence:** `Section_12.txt` L193-315 headings. `Section_13.txt` L197, L227, L254. `Section_11.txt` L51-144. `Section_08.txt` L91-272. `Section_07.txt` L105-148.
- **Note on GPT:** revision 2 used "S12 §7" for retention and "S12 §8-9" for security. GPT's re-check called "S12 §§3–5 and 7–13: Correct" and said it found no wrong section reference, so GPT missed this.

**9. MINOR: some status and "APG today" text is inconsistent.**
- **Location:** E46, E01, E77, Doc L47.
- **Problems:**
  - E46 says "partial (in the mkt and fin modules)" and "A partly", but its status is **missing**.
  - E01 says "source_record_id ... on every kind", but FIELD_REGISTER shows 13 kinds without source_record_id (contract, ctc_line, project, retention, work_output, budget_line, fx_rate, import_check, landed_assumption, quote_reading, quote_term, quote_tier, compliance).
  - E77 says "covered: created by APG" with "A exists", but `cash_states.record_event` requires a named human actor, role and evidence (cash_states.py L48-55). It is entered by a person, and no entry screen exists.
  - Doc L47 lists E13 to E19 as having "no record kind", but E16 is partial.
- **Fix:** Correct each one.

**10. MINOR: gap columns understate what the blueprint requires.**
- **Location:** E07, E08, E09, E57, E66.
- **Problems:**
  - E07's gap omits "status".
  - E08's gap omits parties and form.
  - E09's required groups omit 8-layer Variation fields (potential entitlement, accounting treatment, contract references, approval history).
  - E57's gap ("allowances and premiums") is not among its required groups, while S09 §3 time records (absences, breaks, adjustments) and interruptions have no row or group.
  - E66 lists only "location" although S13 §13.3 requires work package, evidence, responsible parties and change history.
- **Fix:** Align the required groups and gaps with the cited source.

**11. MINOR: Doc L111 says all "36 templates are Builder Zero layouts".**
- **Problem:** 6 are "M6 synthetic supplement" and 1 is "Example only: a different layout" (TPL-EX-ACCOUNTING-DOLLARS).
- **Evidence:** TEMPLATE_REGISTER.csv.
- **Fix:** Say "synthetic layouts (29 Builder Zero, 6 M6 supplements, 1 example)".

### Rule input contracts

**12. BLOCKING: some RULE_INPUT_CONTRACTS rows state behaviour the code does not have (CSV claims "read from the code"; Doc L75 says "The inputs themselves are established").**

| Row | What the CSV says | What the code does |
| --- | --- | --- |
| RIC L5 (M4 actual cost, `ap_invoice.purchase_order_ref`) | "qualify: not linked to an order" | costs.py reads `po` (L60) but never qualifies or excludes on it. The order link is used only by commitments and R03. The behaviour is invented. The Doc L58 summary also lists "order link" as an actual-cost input. |
| RIC L4 (cost_code_ref) | `COST_NOT_ALLOCATED_TO_A_COST_CODE` attributed to `fin/costs.py invoice_lines` | The code exists only in forecast.py L115 (cost to complete). In actual cost an uncoded invoice is simply counted under '(no cost code)' (costs.py L18, L60) with no qualification. |
| RIC L7 (every M4 figure) | "PROJECT_UNKNOWN_OR_AMBIGUOUS: the figure cannot be assessed" | Such records are excluded as 'unattributed' and the figure still finishes (costs.py L108, L154-155; commitments.py L129-132; forecast.py L108-109, L171-172; revenue.py L86-87). The list of modules also omits revenue.py. |
| RIC L8 | "duplicate ... held" | A duplicate delivery counts once (the survivor) and the repeat is ignored, not held (costs.py L35-36, docstring L4). |
| RIC L11 | "status not mapped: amendment held" | It is put in the unapproved exposure class (`CHANGE_NOT_APPROVED:...`, commitments.py L105-107), not held. |
| RIC L16 (M4 recognised margin, `fin/margins.py`) | `A_COMPONENT_CANNOT_BE_ASSESSED` | margins.py does not contain it. It is forecast.py L192 (forecast final margin). margins.py stops with RECOGNITION_METHOD_NOT_CONFIGURED, FORECAST_BASIS_CANNOT_BE_ASSESSED, FORECAST_FINAL_COST_NOT_POSITIVE and REVENUE_NOT_POSITIVE (L19-30), none of which are listed. The needed policy is `recognition_method`. |
| RIC L17 (M4 retention, `build_retention`) | RETENTION_POSITION_CANNOT_BE_ASSESSED; NO_EXPECTED_RELEASE_DATE | Both are emitted by `build_carrying` (cashview.py L139, L142). In build_retention a missing ledger or due date is an "unknown" (L36-38, L57-58). |
| RIC L20 (security) | "not listed" | Held instruments are listed as exclusions, and if all are held the total is unknown, not zero (cashview.py L84-86, L105-106). |

- **Fix:** Correct each row against the code, and replace "established" (Doc L75) with "read from the code in det/ and fin/; confirmed against tests when the rules next change". GPT's New 2 explicitly said the design "cannot claim that the exact input requirements have already been established".

**13. SHOULD FIX: inputs and stop conditions the code reads are missing from the contracts.**
- **Location:** RIC rows; Doc L58-73.
- **Missing items:**
  - **M4 commitments (RIC L9-L11; Doc L60):** the figure reads the invoices linked to each order (`invoice_lines`, `ln['po']`, commitments.py L31-40, L109-114) and the policy `credit_reopens_commitment` (L111-113). Neither is listed. Its LIMIT (goods received but not invoiced are unknown, L15) is not listed either. `PO_STATUS_UNMAPPED` (L70-74) and the `po_amendment.purchase_order_ref` link are omitted.
  - **M4 revenue (RIC L14; Doc L59):** revenue cannot be assessed at all without `variation_status_map` or `tax_basis`, and with inc-GST and no `gst_rate_bps` (revenue.py L27-31). The CSV lists only per-variation "not counted" and "cannot assess revenue". The stop on the variation map also stops forecast final margin, recognised margin and cash-adjusted margin.
  - **M4 budget and forecast (RIC L12-L13):** policy `ffc_basis`, `cost_scope` and `freshness_days` ('forecast', 'budget') (forecast.py L154-156, L183-186) are omitted. So are AMBIGUOUS_LATEST_FORECAST, FORECAST_VERSION_DATES_DISAGREE, CTC_UNKNOWN and BUDGET_EXCEEDED_BY.
  - **M4 carrying (RIC L21):** it also reads the retention position and release_due_date. It needs `carrying.rate_source`, `overlap`, `eligibility` and `freshness_days['facility']`, and stops on FACILITY_RECORD_HELD, SEVERAL_FACILITIES and EXPECTED_RELEASE_DATE_PASSED_AND_NOT_RELEASED (cashview.py L110-169).
  - **M4 cash-adjusted (RIC L22):** the components are `retention_carrying`, `security_carrying` and `overdue_receivables`, not "retention, security, carrying". Two of them always return cannot (cashview.py L135, L174), so any policy that lists them makes the whole figure unassessable. The base margin, recognised or forecast (L189), is an unlisted input.
  - **R02 and R03 (RIC L24-L25; Doc L62):**
    - Both inherit `build_commitments` and stop with PO_STATUS_MAP_NOT_CONFIGURED (rules_cost.py L76-78, L115-117).
    - Amendments on orders that are held, duplicate, after the cut-off, status-unknown or unmapped are skipped before amendments are examined (commitments.py L53-74). R02 neither assesses nor reports them, which is a real "known limit".
    - So Doc L62's "none beyond the variation status map" is wrong.
- **Fix:** Add these to the rows and to the summary table.

**14. SHOULD FIX: the scope claim "every financial figure" is wider than what was read.**
- **Location:** Doc L12, L54; build_rule_contracts.py L1-3.
- **Problem:** Only det/ and fin/ were read. The M6 market module computes figures the document itself relies on (landed cost, indicative market comparison, buy timing; Doc L146; record kinds landed_assumption, quote_tier, import_check). None of them has a contract.
- **Fix:** Add the M6 figures, or narrow the claim to "detection rules R01 to R09, AGG, D01, D02, DLY, LAB, DEF and the M4 figures".

**15. MINOR: smaller problems with the rule contracts.**
- **Problems:**
  - "26 rules and figures" (Doc L54) counts the label "every M4 figure", which is not a rule or figure; there are 25 real ones.
  - The summary table (16 rows) omits recognised margin, budget and forecast, retention, security, carrying, cash-adjusted, AGG, D01 and D02, yet response S1 (Doc L188) points to "recognised margin" in the rule contracts.
  - "identical in M10 and stage 1" (Doc L54) cannot be verified from the pack.
  - Several files the register and doc rely on are not in 04_code_read: figure.py, snap.py, policy.py, findings.py, source_authority.py, ingest/documents.py, intake.py and det/common.py (E01, E03, E44, E45, E83, E84, E90; Doc L116).
- **Fix:** Add those files or mark the claims as "per builder inventory, not read".

**Rule contracts checked and correct:** R01, R03 (fields), R04, R04B, R05 (fields), R06, R07, R08, R09, AGG, D01, DLY, LAB, DEF and D02. Their fields, parameters and not-assessed reasons match the code. All 28 upper-case reason codes quoted in the CSV exist somewhere in 04_code_read, though RIC L4, L16 and L17 put some in the wrong module or figure.

### Systems survey

**16. SHOULD FIX: Procore holdings are overclaimed at the "developer docs" level.**
- **Location:** SYSTEMS_SURVEY PM/Procore; Doc L83.
- **Problem:** The cited tutorial-financial-tools page covers budget, cost codes, direct costs, commitments, commitment change orders, change events, subcontractor invoices, payment applications, payments, prime contract and vendor insurances. It does **not** mention RFIs, inspections, quality or defect tools, or daily logs. The CSV access column claims "RFIs, inspections, quality and defect tools", and the entity list includes E10, E52, E57, E66, E70 and E72; the Doc row lists "defects". The AU page check (variations and progress claims yes, Security of Payment not mentioned) is correct.
- **Fix:** Cite a source for those tools or drop them from the "developer docs" row.

**17. SHOULD FIX: the Aconex evidence does not support the row.**
- **Location:** PM/Aconex; Doc L84.
- **Problem:** The cited URL is a landing page. It links to Swagger docs and a PDF guide, and says nothing about site instructions, notices, RFIs, mail types configured per project, a Documents API or supplier documents.
- **Fix:** Cite the PDF guide or Swagger content, or downgrade to "Mail API exists; contents to confirm".

**18. SHOULD FIX: Jobpac is overclaimed.**
- **Location:** ERP/Jobpac; Doc L86.
- **Problem:** The page supports job and labour costing, forecasting, payroll, AP and AR, and "managing subcontractors". It does **not** mention progress claims or subcontract agreements, and it gives no company size ("mid to large" is unsupported).
  - The entity list includes E13, E17 and E18 (claims and assessments) and E59 (rates).
  - The evidence level says "vendor; third-party", but no third-party source is given (the Payapps page does name Jobpac Connect as an integration).
- **Fix:** Drop claims and size, or source them.

**19. MINOR: other survey rows go slightly beyond their sources.**
- **Problems:**
  - MYOB (Doc L88 "bank"; CSV "AccountRight Live API; MYOB Acumatica API"; E73): the Apideck article covers the MYOB Business API for AccountRight and MYOB Business only. It does not mention Acumatica or bank objects.
  - Xero: aged debtors and creditors are also beta on the Apideck page, not only bank feed statements.
  - Buildxact: the entity list includes E21 PO and E38 budget, which the page does not mention (the Doc row is fine).
  - Databuild: E41 CTC forecast is not on the page.
  - HammerTech: the Doc says it holds "compliance", but the cited page says compliance and inductions are not synced and the access route is the Procore sync. E65 quality observation is not supported.
  - KeyPay: pay rates are not mentioned; only award interpretation, timesheets and pay runs are.
  - P6: the cited page is the Primavera Cloud import-objects reference, not P6 export documentation. It does not mention actual dates or percent complete (the CSV correctly says "to confirm").
  - EstateMaster: the Mastt page does not mention ARGUS.
  - "18 systems builders and developers use" (Doc L13) counts "Market and FX feeds" (typical users: APG) and "Bank feeds" (sourced to the Xero page). The Doc table shows 16 of the 18 rows.
- **Fix:** Correct the rows and wording.

**Survey rows confirmed:** Payapps (claims, payment schedules, variations, retention and compliance documents; integrations with Xero, MYOB, Jobpac Connect and Procore; no API or export described), CostX (takeoff and estimating, Excel integration listed, no API), Buildxact Doc row (partner approval, subscription key plus bearer token, estimates, catalogues, jobs via OData, webhooks), Databuild Doc row (estimates, orders, budgets) and EstateMaster (feasibility, actuals against feasibility; sales and settlement not described). Microsoft Project, Excel and Email rows are marked not checked or APG design.

### Answers to GPT

**20. SHOULD FIX: New 3 and B5 are answered by text that does not exist.**
- **Location:** Doc L177, L187.
- **Problem:** The response says "the register is stated as a template inventory; the field-level schema register ... stays a build task", but no sentence in the body says this. FIELD_REGISTER.csv and TEMPLATE_REGISTER.csv are not mentioned anywhere in the body, and revision 2's next step to generate the schema register was dropped.
- **Fix:** Add the sentence to the import-templates bullet (L111) and add the schema register to next steps.

**21. SHOULD FIX: New 4 is only partly answered.**
- **Location:** Doc L118, L178; ENTITY_REGISTER path status.
- **Problem:** Integration (I) paths are listed for 24 entities but never given a status in "path status". build_entities.py L8 says "I is always 'needs S01 discovery...'", but the CSV never says it. E91 to E95 carry a bare "proposed" with no per-path marks. The "features chart" the answer points to is not in the pack.
- **Fix:** Mark I as "proposed (after S01 discovery and AUIF)" on every row and per-path statuses on the developer rows, and include the chart data.

**22. SHOULD FIX: New 1 is only partly answered.**
- **Location:** Doc L175.
- **Problem:** GPT's fix also asked to "identify relationships between them". The register has no relationship or link column (for example E17 to E16, E18 to E17, E19 to E18, E67 to E66, E44 to E45), and two required entities are missing (finding 1).
- **Fix:** Add a "links to" column.

**23. SHOULD FIX: revision 3 is not self-contained for the items GPT found resolved.**
- **Location:** Doc L171, L193.
- **Problem:** The document says resolved items "stand as they were", but revision 3 dropped revision 2's insight-contract table (blueprint gate, completeness, verification and below-the-gate behaviour per insight) and its source-profile section. GPT's resolutions of S5, S8, S9, S10, S11 and S16 to S20 point into those sections, and S19's answer cites "source profiles (revision 2)". A reader of revision 3 alone cannot see them, and revision 3 does not say the insight contracts are carried forward.
- **Fix:** State explicitly which revision 2 sections remain in force (or re-include them), and say how the rule contracts and the insight contracts relate.

**24. MINOR: other responses are incomplete or loose.**
- **Problems:**
  - S3 (Doc L189) is unanswered: GPT asked for the forecast's tax and currency basis, but E41 neither lists nor gaps a tax or currency basis, and ctc_line has no such field.
  - S19: pagination is still not mentioned.
  - Gemini evidence 5 (L199) says "still a next step", but the next-steps list (L165-167) does not contain the RTM cross-check.
  - New 8 (L182) now asserts "CR-01 to CR-08 and CR-10 are used" (L156), which is still not evidenced in the pack (S18 §6 itself is now correctly included and cited).
- **Fix:** Add a tax/currency basis group to E41, add RTM mapping to next steps, and attribute the CR numbering to the owner's register.

### Other

**25. MINOR: the freshness table misses classes the code already requires.**
- **Location:** Doc L134-142.
- **Problem:** forecast.py and cashview.py read `freshness_days` for 'forecast', 'budget' and 'facility', but the table has no budget or facility-statement row. Programme, timesheets, delays, defects and plant hire have no values either.
- **Fix:** Add the rows.

**26. MINOR: wording presents proposed things as existing.**
- **Location:** Doc L22, L130, L167.
- **Problems:**
  - "the split ... changes the builder's effort, never what APG can do" (present tense; 48 entities have only proposed paths).
  - "its results are labelled 'recorded instructions only'" (a proposed behaviour, not current code).
  - "then build" (L167) conflicts with L7 (no production feature code until the Section 01 Discovery Exit Report).
- **Fix:** Use "will", and "then proceed under the S04 §20 gate".

**27. MINOR: the reassessment triggers are cited to the wrong section.**
- **Location:** Doc L124.
- **Problem:** The triggers (setup, intake, schedule, correction, quarantine, supersession, revocation) are cited to S04 §14, which covers freshness and completeness tracking. The trigger list is S06 §10 ("Continuous monitoring and reassessment").
- **Evidence:** `Section_06.txt` L308-320.
- **Fix:** Cite S06 §10 together with S04 §14.

**28. MINOR: the nudge example relies on concepts APG does not hold.**
- **Location:** Doc L126.
- **Problem:** It names a "May claim period", but APG holds no claim-period record (E13 missing). "Subcontractor invoices" are ap_invoice records; subcontractor claims (E17) do not exist.
- **Fix:** Use "May" or an invoice-date period.

## Checked and found correct

- **Totals:** 95 entities; 12 covered, 37 partial, 46 missing. The per-class table matches exactly: B 58 (9/26/23), I 18 (2/4/12), C 9 (0/3/6), V 5 (0/0/5), D 3 (1/2/0), X 2 (0/2/0).
- **"Covered only when no gap":** holds; no covered row lists a gap and no partial or missing row has "-".
- **Path split:** 38 / 9 / 48. 36 entities rely on templates alone; the other 2 (E77, E84) are APG-created.
- **Path counts:** entry screens 40, integrations 24, phone 14, setup questions 11.
- **Unheld split:** 16 entities as the CSV stands, split 7 / 4 / 3 / 2 with the membership the Doc describes (see finding 3 for why the 16 itself is unsound).
- **Registers:** 37 contract rows; 18 survey rows; 215 field rows; 36 templates covering 35 record kinds; per-template field counts equal the declared column counts; all templates are marked "draft - unverified".
- **"APG today" fields:** spot-checked against FIELD_REGISTER for E07 to E11, E20 to E38, E41, E48, E52, E54, E57 to E59, E61, E64, E66, E67, E73 to E75, E78, E79 and E82. All match apart from the items in findings 6 and 9.
- **Entities required by §11.2 and S13 §3:** all have rows except those in finding 1 (Project, EstimateLine, Baseline, Assessment, Variation, Alert, Scenario, Decision/Approval; observation through closure verification).
- **Blueprint citations in the Doc body that are correct:** S04 §20 (Discovery Exit Report gate), S04 §8 (five outcomes), S04 §12, S04 §18, S06 §4 (data gap is not leakage), S10 §4 (multi-factor prioritisation, so "one factor of five" is right), S07 §4.1, S08 §7.1, S11 §7.1, S09 §14, S18 §6 (controlled CR with cascade impact assessment; Section_18.txt is identical to the txt copy), 8-layer 02 §2.11 (ten decisions; E90's list matches).
- **Responses that answer GPT:** New 5, New 6, New 7 (30/60 days adopted), New 9, New 10, Gemini design 2, 4 and 6, and evidence 1 and 4. S7 (E75 and E76 separate), S12 (E59, E60) and S14 (E79 to E81) are answered at entity level.
- **Header:** the GPT tally in Doc L5 (2 / 6 / 1 / 1) matches the re-check.

## Totals

| Severity | Count |
| --- | --- |
| BLOCKING | 2 (findings 1 and 12) |
| SHOULD FIX | 16 (findings 2, 3, 4, 5, 6, 7, 8, 13, 14, 16, 17, 18, 20, 21, 22, 23) |
| MINOR | 10 (findings 9, 10, 11, 15, 19, 24, 25, 26, 27, 28) |
| **Total** | **28** |

### Process notes

- GPT's re-check missed the S12 §7/§8 and §8/§9 citation errors (finding 8) while stating it found no wrong section reference.
- Every finding here is a mechanical correction to the CSVs or wording. None needs a new design round, so after fixing them the next step should be the single, limited confirmation pass the document already proposes, not another full review cycle.
