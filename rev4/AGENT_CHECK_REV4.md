# INDEPENDENT READ-ONLY (agent) check of APG Data Readiness CR, revision 4

Pack checked: `APG_DATA_READINESS_CR_REV4_PACK` (folder), 2026-11-12. I edited nothing in the pack. I recomputed every count with `python3 -I` from the CSVs and the code. I also re-ran the five generator scripts in memory, with file writes intercepted so nothing was written to disk; each script's output is byte-identical to the CSV in the pack. A temporary helper script I used for this has been deleted. As the brief says, the absence of AUDIT.txt is not counted as a finding.

Line references: `CR` is `01_CHANGE_REQUEST_REV4.md`, `RIC row n` is a line of `RULE_INPUT_CONTRACTS.csv` counted with the header as row 1, and code paths are relative to `04_code_read/apg/`.

---

## Part 1. GPT's points: is each one answered?

| GPT point | Verdict | One-line reason |
| --- | --- | --- |
| Blocking 1: contract accuracy (as a whole) | PARTLY | R04B and LAB are now exact. The credits row says application is "not from against_invoice_ref", but reconcile.py builds the lineage credits from against_invoice_ref (finding 1). |
| Blocking 1a: M4 actual cost, credits | PARTLY | The costs.py side is now right. The upstream dependency is misstated and two credit holds are left out (finding 1). |
| Blocking 1b: R04B, any stored variation silences it | ANSWERED | RIC row 32 matches rules_commercial.py lines 76-80. DC-1's approved fix covers only held, quarantined or conflicting variations, not a usable but rejected one (finding 12). |
| Blocking 1c: LAB, missing overtime counted as 0 | ANSWERED | RIC row 38 matches rules_ops.py line 142 and det/intake.py lines 23-27, where overtime_hours is only a warning. |
| Blocking 2: M6 contracts absent | PARTLY | 14 rows now exist. They leave out the specification register that gates every comparison, about 15 reason codes, policy pinning, and several silent passes (findings 6, 7, 8, 11). |
| Blocking 3: field-level coverage (4.1) | PARTLY | The report exists and reproduces exactly. It drops fields the contracts name, leaves out fields the code reads, and overstates both "authority checked" and "accepted by document capture" (findings 2 to 5). |
| Should fix: DEF missing cost | PARTLY | "No cost: unquantified" is right. When some defects have a cost and others do not, the finding is quantified at the partial sum and presented as a record; the contract does not say this (finding 10). |
| Should fix: R07 expired quote | ANSWERED | RIC row 35 matches rules_commercial.py lines 216 and 223-224. |
| Should fix: security carrying configuration order | ANSWERED | RIC row 22 matches cashview.py lines 129-135. |
| Should fix: survey 4.2, capability is not a feed | ANSWERED | The CSV entity header now says "holds; holding is not a confirmed APG feed", and Procore's E65/E66 and HammerTech's fields are marked as not established. Wording leftovers are in finding 21. |
| Should fix: MS Project 4.3 | ANSWERED | The CSV row and CR line 148 call it an unverified assumption. |
| Should fix: documents.py not in the pack (4.4) | ANSWERED | The file is in the pack and CR line 181 is broadly right. With the file now visible, the "D partly" path claims can be checked, and most are not supported (finding 5). |
| Should fix: templates are not validated coverage (4.5) | ANSWERED | CR line 176 states it and makes it a release A gate. |
| PARTLY: New 2, exact rule inputs | PARTLY | Same as Blocking 1 and 2. The response table has no row of its own for it (finding 24). |
| PARTLY: New 8, owner's CR list | ANSWERED (as far as the pack can) | 00_README.txt lines 17-20 give the list as the owner's own record. CR-05 and CR-06 are one-line scopes only, which is acceptable once labelled as the owner's record. |
| PARTLY: B3/S4/S6, field-level contracts | PARTLY | Same as Blocking 3. No row of its own in the response table (finding 24). |
| PARTLY: B5, schema register, validation and tests | PARTLY (unchanged) | Honestly restated as future work (CR line 242). Nothing was done, so GPT's PARTLY stands. |
| PARTLY: S3, financial foundation decisions | PARTLY (unchanged) | Restated as required before production (CR line 235). |
| PARTLY: S19, connector detail | PARTLY (unchanged) | Restated as waiting for the Section 01 discovery. |
| PARTLY: Gemini evidence 5, Master RTM cross-check | PARTLY (unchanged) | Still a next step (CR line 243). |
| PARTLY: agent audit | (this report) | Not assessed, per the brief. |
| GPT's separate list of blueprint gaps | ANSWERED | Listed under "Required before production" (CR line 235); the M6 contracts are now written. |

---

## Part 2. Numbers recomputed from the CSVs

Every count in CR and README matches the CSVs:

- **Entities:** 100 = 11 covered, 41 partial, 48 missing. By class: B 60 (9/27/24), I 20 (1/7/12), C 10 (0/3/7), V 5 (0/0/5), D 3 (1/2/0), X 2 (0/2/0).
- **Gaps:** every covered row lists no gap, and every partial or missing row lists one.
- **Built paths:** 38 entities have a path marked exists (11 covered, 27 partial). 37 of them have T exists; E84 has only A exists. 10 more have partly-only paths, and 52 have proposed-only paths (48 missing plus 4 partial: E03, E05, E53, E98).
- **Chart:** T 37/29, E 0/47, I 0/24, P 0/14, S 1/13, A 8/9, D 17/6.
- **Contracts:** 53 rows and 43 rules and figures (13 M4, 16 detection, 14 M6; "every M4 figure" is not counted as a rule). 14 M6 rows.
- **Field routes:** 135 fields in 31 entities. T built 135, D built 59, material 29, "authority checked" 46. 48 settings rows (N01 26, E90 20, E04 1, E03 1).
- **Survey and templates:** survey 18 rows (16 systems, 2 data sources); 33 of 65 B/V entities are supported by a cited source. 36 templates (29 BZ, 6 MKT, 1 EX); 215 fields in 35 kinds.
- **Material list:** the script's MATERIAL dict is identical to the `material` tuples in ingest/specs.py, fin/intake.py, det/intake.py and mkt/intake.py (checked by parsing the code).

The arithmetic is right. Several of these figures do not mean what the document says they mean: 135, 29, 46 and 59 are covered in findings 2 to 5, and 48 in finding 19.

---

## Part 3. Findings

### BLOCKING

**1. The M4 credits contract misstates the dependency GPT asked to be corrected.**
- **Evidence:** RIC row 7 and CR line 64 say which credits apply comes "from the invoice's reconciliation state (its lineage credits), not from against_invoice_ref". But reconcile.py lines 193-204 build `credits_by_inv` from `credit_note.against_invoice_ref`, and line 241 writes that list as the invoice's `lineage.credits`. against_invoice_ref is therefore the field that decides application; costs.py lines 72-90 only read the result.
- **Missing holds:** RIC row 7 leaves out the reconciliation holds on credits: CREDIT_TARGET_NOT_VISIBLE (line 201) and CREDIT_EXCEEDS_INVOICE (line 210).
- **Code contradiction:** reconcile.py line 234 says the lineage is "information only; it never changes arithmetic", yet costs.py nets the lineage credits into the figure.
- **Fix:** "Reconciliation links each live credit to the invoice named in its against_invoice_ref, if that invoice is visible (otherwise the credit is held: CREDIT_TARGET_NOT_VISIBLE; credits above the invoice amount are held: CREDIT_EXCEEDS_INVOICE). costs.py applies a linked credit only when ..." (keep the rest). Raise the comment-versus-code contradiction as a note for the code owner; do not change the code in this CR.

**2. The field check drops fields the contracts name, so "135 fields, none missing" and "29 material" are undercounts.**
- **Evidence:** build_field_coverage.py line 60 tokenises, and line 73 checks only tokens that contain "_". Single-word fields are never checked and never mapped:
  - `work_output.quantity` (LAB, RIC row 38; material in DET_SPECS)
  - `material_demand.quantity` (RIC rows 42, 43, 46, 47; material in MKT_SPECS)
  - `purchase_order.quantity` (RIC rows 47, 48, 51, 53)

  The script's assertion that it "fails on a gap" is blind to all three.
- **Recomputed:** 138 named fields and 31 material.
- **Fix:** add `quantity` to ALIAS for those kinds, or match register fields without requiring "_". Regenerate, then update CR lines 13, 18, 112, 117-120 and 254 and README line 5.

**3. "Every field the 43 rules and figures read is mapped" is not true: fields the code reads but the contracts do not name are absent.**
- **Evidence (M4 retention, RIC rows 18-19):** retention_event fields `seq, from_state, to_state, amount_cents, evidence_ref, actor, actor_kind, actor_roles` (fin/cash_states.py lines 41-78) and `bank_txn.amount_cents` (line 58; material in FIN_SPECS) are missing. So E73 and E77 are not among the 31 entities.
- **Evidence (M6):**
  - `quote_ref` on quote_tier, quote_term, landed_assumption and quote_reading (landed.py lines 26, 44, 58; spec.py line 28)
  - `quote_reading.extracted_by`, which decides `verified` (spec.py line 38)
  - `delivery.purchase_order_ref`, `delivery_date` (material) and `material_ref` (common.py line 208)
  - `purchase_order.unit_of_measure` (demand.py line 39; purchasing.py line 170)
  - `supplier_quote.supplier_ref`, `specification_text` and `price_kind` (common.py lines 122, 135-137)
- **Evidence (M4):** `project.contract_value_cents` (revenue.py line 46); `ap_invoice.supplier_ref` and `supplier_invoice_number` (reconcile.py lines 117-136 and 143-166, which decide duplicates and holds that M4 actual cost depends on).
- **Disclosure gap:** draft 6 itself lists "fields the contracts do not name" and "the fields of retention events" as limits of the check (07_decisions/DATA_SUPPLY_SYSTEM_DRAFT6.md line 143). CR line 126 ("What the report does not do") leaves both out.
- **Fix:** either name these fields in the contracts and regenerate, or reword CR lines 13 and 18 to "every field the contracts name" and add these to "What the report does not do".

**4. "Source authority checked today: 46" is overstated; the code checks authority for 6 of the 135 fields.**
- **Evidence:** reconcile.py lines 258-271 call `resolve_field` only for each SPECS kind's `material` fields, and skip kinds with no material field and the secondary kind pm_invoice. Of the 135 fields, only these 6 get a field-authority check:
  - ap_invoice.amount_ex_gst_cents
  - credit_note.amount_ex_gst_cents
  - purchase_order.amount_ex_gst_cents
  - po_amendment.delta_cents
  - supplier_quote.unit_rate_minor_units
  - budget_line.budget_cents
- **No check at all:** fx_rate (3 fields), market_observation (7) and supplier (1) have `material=()` (specs.py lines 65, 82-83), so they get no authority check of any kind.
- **Other checks are not authority:** the remaining fields on the reference kinds are checked only for links, duplicates or supplier resolution, if at all. FIELD_SUPPLY_ROUTES marks all 46 "checked by the reference intake", and the script docstring says "with authority and reconciliation" (build_field_coverage.py line 19).
- **Fix:** split the column into "authority resolved (6)", "link, duplicate or supplier check only (list)" and "neither". Update CR lines 18 and 120 ("source authority is checked for 6 fields, the material amounts of the reference intake; 129 are not checked").

**5. Document capture "partly built" is claimed for 14 entities and 59 fields; the code supports, at most, quotes.**
- **What the code does:** ingest/documents.py has one extractor, `standin_extract_quote` (lines 109-126). It reads four fields: quantity, unit_rate_cents, valid_until and supplier_text (line 80). It also has a generic store and verify control, which is not linked to the intake: no other module calls it (checked by grep). Even for quotes, the names do not match the supplier_quote record (`unit_rate_minor_units`).
- **What the register claims:** "D partly" also appears on E08 contract, E09 variation, E10 notice, E23 invoice, E27 spec requirement, E64 plant hire, E74 facility, E75 retention, E78 security and E82 compliance (ENTITY_REGISTER.csv, path status column). CR line 118 counts 59 fields as "accepted today by a built way in ... 59 also by document capture", but CR line 181 itself says document capture "is not linked to the intake".
- **Fix:**
  - Remove "59 also by document capture" from the "accepted today" row.
  - Mark D "proposed" wherever no extractor exists, or define "partly" explicitly as "the generic verification store exists; no extractor for this document type".
  - Recompute the chart's D row (17/6) and the "10 partly built" count.

**6. The M6 comparison contract omits the specification register, the input that decides whether any offer can be ranked.**
- **Evidence:** M6 runs pin a separate `mkt_spec` register (mkt/detect.py lines 34 and 67; mkt/policy.py lines 10-11 and 219-294). It holds families, attributes and match rules, the catalogue specification of each material, units and unit conversions, and it is approved by `specification_owner`. If it is missing or unapproved, `classify` returns `unverified` / SPEC_REGISTER_UNAPPROVED (spec.py lines 123-124). An unverified offer is not rankable (spec.py line 19; compare.py line 124), so there is no ranking, MP03 has no scenarios, MP09 has no opportunities, and MP02 reports "cheaper_quote_unverified".
- **Where it is missing:** RIC row 42 lists "unit conversions" under the procurement policy (N01), but they are in the register (spec.py line 113). Neither N01 (ENTITY_REGISTER N01, required field groups) nor any settings row holds the register.
- **Fix:** name the specification register in RIC rows 42, 43, 45 and 52 (configuration column and missing-input behaviour). Attribute it to an entity (N01's description, or a row of its own, as the owner prefers) and regenerate the settings rows.

**7. The M6 rows leave out reason codes and run states, though the contract claims "each failure has its reason code".**
- **Missing from RIC row 42 and CR line 102:**
  - spec.py lines 123-138: SPEC_REGISTER_UNAPPROVED, REQUIREMENT_UNAPPROVED, ATTRIBUTE_FAILS, UNIT_INCOMPATIBLE, ATTRIBUTE_UNKNOWN, QUOTE_TEXT_UNVERIFIED, UNIT_UNVERIFIED
  - compare.py lines 72 and 107-110: COMPONENT_MISSING:&lt;component&gt;, GATE:&lt;class&gt;, FRESHNESS:&lt;qualification&gt;
  - common.py lines 128-131, 158 and 201: NOT_RECONCILED, RECONCILIATION:&lt;outcome&gt;, DUPLICATE_OF, QUANTITY_NOT_POSITIVE
  - demand.py line 103 (MP03 and MP04): UNIT_MISMATCH
- **Missing from every MP row:** common.py lines 63-77 give MKT_POLICY_NOT_PINNED (cannot assess), SWITCHED_OFF_IN_POLICY (disabled) and not_configured with the missing parameter names. Only the last is stated (RIC row 44). M4 has its POLICY_NOT_PINNED row (RIC row 2); M6 has none.
- **Fix:** add the codes to each row, and add one "every M6 figure and rule" row for pinning and switch-off.

**8. Several M6 rules pass silently when an input is missing. The contracts do not say so; this is the class of behaviour GPT blocked for R04B and LAB.**
- **No PO status map:** MP05, MP08 and MP10 need the financial policy's po_status_map (E90). Without it no order qualifies (demand.py lines 15-19 and 135; suppliers.py line 33; purchasing.py line 168), so the rules evaluate nothing and raise nothing, without even a "not assessed". RIC rows 48, 51 and 53 omit E90 from configuration. The same map feeds `last_paid` (compare.py line 170), so MP02 and MP09 lose their reference without saying why.
- **MP09, tax:** an opportunity is silently dropped when tax treatments differ and `basis.gst_bps` is not set (opportunity.py lines 123-125). gst_bps is an optional setting (mkt/policy.py line 96).
- **MP01, no quote:** a watched material with no usable quote gives no quote signal (rules.py line 93: `if qs and not any(...)`). RIC row 44 and CR line 104 say "no quote current: signal".
- **Unusable requirements:** demand lines and spec requirements that are not usable are silently left out of the requirements (compare.py lines 38-39 and 46-47). MPD1 lists held ones, but a usable demand with quantity 0 (QUANTITY_NOT_POSITIVE) is dropped unreported.
- **Fix:** state each behaviour in its RIC row and add E90 to the configuration of rows 48, 51, 52 and 53. Raising these as defect candidates (like DC-1 and DC-2) is the owner's decision; the contract only has to describe today's code.

### SHOULD FIX

**9. M6 buy timing says "payment terms are not ingested (E32)"; the code reads them.**
- **Evidence:** scenarios.py `_cash_out` (lines 24-43) reads quote_term `payment_days` and `deposit_bps`, and landed.py `purchase_plan` (lines 168-173) reads `moq` and `pack_size`. E32 (quote_term) is marked "covered". The claim appears in RIC row 43 and CR line 103.
- **Configuration gaps in RIC row 43:**
  - settings not listed: price_paths, financing_bps_pa, storage_cents_per_unit_per_day, stage costs, day_count_basis, context_points
  - statuses not listed: no_uncovered_demand, no_rankable_offer and no_scenario_built for unit-converted offers (scenarios.py lines 220-237)
  - effects not listed: "wait" and "stage" are cannot_assess when their settings are missing (lines 167-186)
- **Fix:** "payment terms are read from quote terms (payment_days, deposit_bps) when recorded; otherwise payment is taken at delivery and listed as an evidence gap". Add the settings and statuses.

**10. DEF: the partial-cost case is not stated.**
- **Evidence:** rules_ops.py lines 240-250. If some defects have rework_cost_cents and others do not, `total > 0` and the finding is quantified at the partial sum ("sum of rework costs as recorded", label "record", impact_cents = partial total). RIC row 39 and CR line 69 state only the no-cost case.
- **Fix:** "if only some defects carry a cost, the finding is quantified at the sum of the recorded costs (a lower bound; the text says the cost is not known for every defect)".

**11. M6 field and configuration lists are incomplete beyond findings 3 and 6.**
- **RIC row 41:** omits the policy settings that decide "missing" and "international": required_components, international_bases, freight_currency and price_tax (landed.py lines 76-102 and 145).
- **RIC row 46 (MP03):** names orders only as "matched by project, material, window and status", so purchase_order project_ref, material_ref, order_date, source_status, quantity and unit_of_measure are not mapped to MP03.
- **RIC row 47 (MP04):** omits "a docket with no accepted quantity counts at the delivered quantity" (demand.py lines 85-87).
- **RIC row 53 (MP10):** omits min_projects (purchasing.py line 177).
- **Fix:** add these to the rows and regenerate.

**12. DC-1's approved behaviour does not cover what the R04B contract says silences an instruction.**
- **Evidence:** RIC row 32 says "whatever that variation's state, held or rejected included". The DC-1 fix (CR line 73) turns only held, quarantined or conflicting variations into "not assessed", so a usable variation whose status maps to rejected would still silence the instruction. GPT's point was that the code does not check whether the variation is "approved, usable or reconciled".
- **Fix:** state whether a rejected (or other non-resolving) linked variation still silences the instruction after DC-1. It is an owner decision; record it either way.

**13. The same held-variation behaviour exists in M4 commitments and R02, and the contract does not state it.**
- **Evidence:** commitments.py lines 93-96 take the class of a linked variation when it is merely not in conflict. A held (pending) variation with an "approved" status therefore makes its amendment "committed", and R02 stays silent (rules_cost.py lines 83-85). RIC row 9 says "named change not approved or not found: unapproved exposure".
- **Fix:** add this to RIC rows 9 and 26 and the CR line 83 summary. Whether it joins DC-1 is for the owner.

**14. The reference-intake contracts leave out the register and supplier-master dependencies that hold every record.**
- **Register:** with no approved Source Authority Register, or no rule for the field, `resolve_field` returns NO_APPROVED_REGISTER / NO_AUTHORITY_RULE / AUTHORITATIVE_SOURCE_ABSENT (source_authority.py lines 177-186). These cannot be cleared by a reviewer (reconcile.py line 24). Every invoice, credit, PO, amendment, budget line and quote is then held.
- **Supplier master:** with no supplier list, every record carrying a supplier is held: SUPPLIER_UNVERIFIABLE_NO_MASTER (reconcile.py lines 147-150).
- **Where it is missing:** RIC rows 4, 8, 11, 27, 35 and 41-43 do not name these. E03 appears only on the duplicate row (RIC row 6), and E20 is not named for M4 actual cost.
- **Fix:** add both conditions to the "if missing" and configuration columns of those rows (one line each).

**15. The N01 description contradicts det/policy.py and mkt/policy.py, and is inconsistent with E90.**
- **Evidence:** CR line 47 says N01 settings "are passed to each rule as parameters (det) or held in mkt/policy.py; no entity holds them". ENTITY_REGISTER N01 says "no builder setup, approval or versioning" and "S proposed". The code says otherwise:
  - det/policy.py lines 5-8: "A policy is a versioned record ... immutable ... APPROVED only when a human 'detection_policy_owner' who is not the proposer has approved it ... and the audit log confirms it."
  - mkt/policy.py lines 5-13 say the same, and the module "chooses no value": the values live in stored mkt_policy records, not in the module.
  - fin/policy.py lines 3-6 uses the same pattern for E90, which is marked "partial, S partly".
- **Fix:** reword N01 as "held as versioned, approved policy records (det_policy, mkt_policy); no builder setup question and no owner-approved defaults or ranges". Decide N01's status on the same basis as E90. If it moves to partial/S partly, the counts move: Configuration 0/4/6, total 11/42/47, Setup questions built 2/12. Similarly, "E90 is held in fin/policy.py" should read "held as versioned fin_policy records (schema and approval in fin/policy.py)".

**16. E03 descriptions are stale or unsupported now that source_authority.py is in the pack.**
- **Stale:** ENTITY_REGISTER E03 still says "per the builder inventory, not read for this revision".
- **Unsupported:** the FIELD_SUPPLY_ROUTES E03 row (build_field_coverage.py line 134) says "rows written straight to the store (source_authority.py)". But source_authority.py builds `AuthorityRegister` objects in code (lines 72-103), keeps `RegisterHistory` in memory (lines 106-126) and writes no register rows. The register is passed to `reconcile()` as an argument. Its approval is an asserted approvals tuple (lines 93-95), not the audited approval used for the policies.
- **Fix:** "an in-code register object passed to reconciliation; its approval is asserted on the object, not audited; no builder setup".

**17. CR line 106 says "revision 2 is in the pack". It is not.**
- **Evidence:** 06_previous holds only revision 3, its audit and GPT's check. The sentence was carried over from revision 3 (06_previous/01_CHANGE_REQUEST_REV3.md line 78).
- **Fix:** delete the clause, or add revision 2 to 06_previous.

**18. The "material" flag is a proxy, but the document treats it as the S04 §12 list. The "none meets PG-DS-AC-12" conclusion is fair, but its stated reasons are partly wrong.**
- **What the flag is:** the intake `material` tuples mean "cannot be relaxed when missing" (specs.py lines 59-60 and 96-98). S04 §12 is about AI/OCR-extracted values that "materially affect financial calculations". documents.py has its own material list for quotes (line 80), which includes valid_until and supplier; supplier_quote.valid_until (read by R07, M6 and MP01) is flagged "no". variation.value_cents, which drives revenue, is also "no".
- **Per-row "must add":** every material field is told it needs "document capture linked into the intake, a person verifying the value" (build_field_coverage.py line 130). PG-DS-AC-12 needs only one built way in that meets its requirement, and S04 §12 applies only to values read from documents, not to a system export through a template.
- **Fairness of "none":** the conclusion holds because of synthetic templates, authority resolved for only 6 fields (finding 4) and no setup questions; that is a fair conservative reading.
- **Fix:** label the flag "intake non-relaxable fields (a proxy for S04 §12; a lower bound)", note documents.py's list, and give the corrected reasons for "none".

### MINOR

**19. "48 settings rows ... per setting a contract reads" overstates the granularity.**
- **Evidence:** the rows are one per contract row and settings entity (build_field_coverage.py lines 135-153). Some bundle many settings, for example "procurement policy (N01): home currency, delivery-basis table, FX method". Others repeat: variation_status_map appears in 4 rows. E03 appears once, although every reference-intake material field needs it.
- **Fix:** CR line 113: "48 rows, one per contract row that names configuration, per settings entity".

**20. README inaccuracies.**
- 00_README.txt line 3 lists `02_GPT_CHECK_PROMPT.md`, which is not in the pack (add it before sending).
- Line 8 says "build_systems.py and build_entities.py as in revision 3", but both changed: the N01 row (build_entities.py line 108) and the "holds" header (build_systems.py line 54). build_entities.py's docstring still says "Revision 3".

**21. Survey wording leftovers.**
- CR's table header (line 134) is still "What the source supports", while the response table (line 256) says the column was renamed to "holds". Align the header.
- In the CSV, the EXT row's "how data can be got out" says "APG market intelligence engine". The code has only MarketFeedPort with test doubles that "connect to no feed" (mkt/ports_m6.py lines 1-4). Say "proposed: MarketFeedPort (EDR-09); no provider yet".
- Procore's evidence level says variations and progress claims are also vendor-page items, but only E65 and E66 are called "not established". Either state which of E09 and E13 the API's change events and payment applications cover, or mark them too.
- **Not yet built:** CR line 153, "document capture is the way in that works for every builder", describes something unbuilt (claims capture does not exist). Write "would work ... once built".

**22. documents.py "cannot verify dates yet" is slightly inexact.**
- **Evidence:** `verify_field` accepts a text value for valid_until, and `verified_text` returns it (documents.py lines 154, 186-192). But `observation()` gives `human_verified` only for whole numbers (line 179), so a verified date never reaches the authority logic.
- **Fix:** "a person can record a verified date as text, but it does not reach the authority logic".

**23. "Every M4 figure" and the detection rows omit policy-approval behaviour.**
- Under an unapproved financial policy, figures are "at most provisional" (fin/policy.py lines 5-6).
- Detection rules record not_configured with the missing parameter, and findings under an unapproved detection policy say so (det/policy.py lines 5-8).
- The R01 contract (RIC row 25, CR line 88) omits that actual cost on a code with no budget line, including "(no cost code)", is never assessed or listed, because rules_cost.py line 45 iterates budget codes only.
- **Fix:** one line each.

**24. The response table has no explicit rows for GPT's PARTLY items "New 2" and "B3/S4/S6".**
- **Evidence:** they are covered only by the blocking rows (CR lines 252-254).
- **Fix:** add two pointer rows.

**25. "52 ... can be supplied only through features designed but not built" (CR lines 18 and 157) is slightly inexact.**
- **Evidence:** the 52 include four partial entities whose existing fields already arrive through another entity's built template: E53 holding rate via delay_event, and E98 work package via timesheet and work_output. E03 and E05 are in code.
- **Fix:** add "(4 of them partial, their present fields arriving through another entity's record)".

**26. Draft 6 and revision 4 use different entity-level metrics without saying so.**
- **Evidence:** draft 6 line 114 has "47 of the 100 ... built or partly built; for 53 it is not" (the minimum way in). CR has 48 and 52 (any path). GPT has both documents.
- **Fix:** one clarifying clause in CR line 157.

**27. PG-DS-AC-12 is not identified as a draft criterion.**
- **Evidence:** it comes from the draft 6 design (line 245) and is approved in principle under decision 11; it is not a locked blueprint ID. CR line 18 uses it without saying so.
- **Fix:** say so at first use.

**28. "The pack carries the code it cites" (CR line 16) is mostly true, but some modules the contracts depend on are absent.**
- **Evidence:** RIC row 2 cites `fin/*.py FigureBuilder`, but fin/figure.py is not in the pack. Also absent: fin/snap.py (F.get, F.recon, of_project), det/common.py, det/signal.py, det/detect.py (D02's kinds), fin/fmath.py, policy_approval.py and materiality.py.
- **Fix:** list the absent modules, or add them.

---

## Part 4. What I could not verify from the pack

- **Snapshot behaviour:** fin/snap.py is absent, so I could not confirm that `F.get` returns held records. DC-1's "held ... included" and finding 13 rest on this. It is consistent with how cashview.py and rules use it (they call `usable()` after `F.get`).
- **FigureBuilder semantics:** fin/figure.py is absent, so I could not check how cannot, unknown and finish set the figure state (provisional or authoritative), or how R05 sees the state of a missing ledger.
- **Reference intake policy:** the M3 IngestPolicy instance (its warn_unknown) is not in the pack. So I cannot tell whether a supplier_quote with no valid_until or lead_time_days is held or usable. If usable, mkt/rules.py line 313 (`q['valid_until'] >= A.as_of`) and scenarios.py line 65 would compare None with text and raise an error.
- **Freeze:** "freeze ee1ce3ec; unchanged since revision 3" (CR line 58; README line 10). No hashes or repository are in the pack.
- **Owner decisions:** the owner's decisions of 2026-11-12 (DC-1 and DC-2; approval in principle of the 12 decisions) are recorded only in the owner's chat.
- **Survey sources:** I did not re-fetch the vendor pages, so the vendor claims are taken as cited.
- **Revision 2:** its insight contracts are cited as "in force", but revision 2 is not in the pack (finding 17).
- **Blueprint text:** I read Section 04 §12 from the docx to check the S04 §12 wording. I did not cross-check the other locked sections or the Master RTM.

---

**Totals: 8 BLOCKING, 10 SHOULD FIX, 10 MINOR (28 findings).** Of the 21 verdict rows in Part 1 (excluding the agent-audit row, which is this report), 10 are ANSWERED, 11 PARTLY (4 of them unchanged open items: B5, S3, S19, Gemini evidence 5) and none NOT ANSWERED.
