# INDEPENDENT READ-ONLY (agent) re-check of APG Data Readiness CR, revision 4 (after the fixes)

Pack: `APG_DATA_READINESS_CR_REV4_PACK` (folder), 2026-11-12. This is a scoped re-check of what changed after the first agent check (`AUDIT.txt`). I edited nothing in the pack. I recomputed every count with `python3 -I` from the CSVs. I re-ran the five generators in a temporary copy outside the pack, then deleted the copy and my helper scripts.

References used below:
- `CR n` is a line of `01_CHANGE_REQUEST_REV4.md`.
- `RIC row n` is a line of `RULE_INPUT_CONTRACTS.csv`, with the header as row 1.
- `D7 n` is a line of `07_decisions/DATA_SUPPLY_SYSTEM_DRAFT7.md`.
- Code paths are relative to `04_code_read/apg/`.

**Totals: 0 BLOCKING, 5 SHOULD FIX, 16 MINOR.** Of the 28 earlier findings, 24 are FIXED, 4 are PARTLY fixed (4, 5, 15 and 16) and none is NOT FIXED. The numbers all reproduce, and the generators give byte-identical output. Nothing found needs to stop the pack going to GPT, but the five SHOULD FIX items are small, and fixing them first would save a GPT round.

---

## 1. The 28 findings: is each fix made, and does it resolve the finding?

| # | Verdict | Evidence |
| --- | --- | --- |
| 1 | FIXED | RIC row 10 and CR 65 now say reconciliation links credits through against_invoice_ref (reconcile.py 194-213, 241). They name CREDIT_TARGET_NOT_VISIBLE, CREDIT_EXCEEDS_INVOICE, CREDIT_SUPPLIER_MISMATCH and LINKED_CREDIT_UNRESOLVED, and note the "information only" comment. A small residue is in M9. |
| 2 | FIXED | build_field_coverage.py 93-94 now matches one-word fields of the current kind. work_output.quantity, material_demand.quantity and purchase_order.quantity are checked. The counts are 155 fields and 33 material. |
| 3 | FIXED | Every field the first check listed is now named: RIC rows 9, 17, 21, 22, 44, 45, 46 and 49. Retention-event fields are listed separately. CR 146 states the limit. |
| 4 | PARTLY | The authority column is split 6 / 48 / 101. But the "link, duplicate and supplier checks" label is wrong for 15 of the 48 (S1). The script docstring was not corrected: build_field_coverage.py line 19 still says the 11 reference kinds come "with authority and reconciliation", although the fix list says it was corrected. |
| 5 | PARTLY | D "partly" now applies only to E30, E35 and E83, and the chart's D row is 3 / 20. But the "accepted today" row still counts 19 fields as accepted by document capture (S2). |
| 6 | FIXED | The specification register is named in RIC rows 5 and 45, with its fields and approver, and attributed to N01 (ENTITY_REGISTER N01, the required field groups). |
| 7 | FIXED | RIC row 45 lists the gate, blocker and record-state codes. RIC rows 49 and 50 give UNIT_MISMATCH. RIC row 5 gives MKT_POLICY_NOT_PINNED, SWITCHED_OFF_IN_POLICY and not_configured (mkt/common.py 60-78). |
| 8 | FIXED | The silent cases are stated in RIC rows 45, 47, 48, 51, 54, 55 and 56. E90 is in the configuration of every MP row that needs the PO status map. They are listed as DC-4 to DC-6, with DC-3 added. |
| 9 | FIXED | RIC row 46 and CR 121 read payment_days, deposit_bps, moq and pack_size, and give the settings and the statuses no_uncovered_demand, no_rankable_offer and no_scenario_built (scenarios.py 24-43, 211-237). |
| 10 | FIXED | RIC row 42 and CR 70 state the partial-cost case (rules_ops.py 240-247), listed as DC-9. A small residue is in M16. |
| 11 | FIXED | RIC row 44 now has required_components, international_bases, freight_currency and price_tax. RIC row 49 has the order fields, RIC row 50 the docket rule, and RIC row 56 min_projects. The remaining field omissions are in M6. |
| 12 | FIXED | RIC row 35, CR 67 and the DC table (CR 90) put the scope question about a rejected linked variation to the owner. |
| 13 | FIXED | RIC rows 12 and 29 and CR 100 and 106 state the behaviour (commitments.py 93-104), listed as DC-7. |
| 14 | FIXED | RIC row 3 gives NO_APPROVED_REGISTER, NO_AUTHORITY_RULE and AUTHORITATIVE_SOURCE_ABSENT as not clearable (reconcile.py 24), and SUPPLIER_UNVERIFIABLE_NO_MASTER or SUPPLIER_NOT_CHECKED (reconcile.py 148-153). E03 and E20 are its configuration. |
| 15 | PARTLY | N01 is reworded and is now partial with S partly, and the counts move as the first check asked: 0/4/6, 11/42/47 and 2/12. But the "APG today" cell of E90 in ENTITY_REGISTER is unchanged ("partly: apg/fin/policy.py (variation_status_map, ...)"), although the fix list says "E90's wording corrected the same way". D7 89 still describes the financial policy as "the policy object exists in code" (M11). |
| 16 | PARTLY | The E03 wording is fixed in ENTITY_REGISTER and FIELD_SUPPLY_ROUTES, and D7 33 corrects draft 6. But D7 186 still says the authority register's rows are written directly (S5). |
| 17 | FIXED | `06_previous/01_CHANGE_REQUEST_REV2.md` is present. CR 16 and CR 124 say so. |
| 18 | FIXED | The flag is labelled as a proxy and a lower bound (CR 137 and the CSV column header), documents.py's list is noted, "must add" for a material field now applies only to a value read from a document, and CR 144 gives the reasons. |
| 19 | FIXED | CR 131 and the docstring now say "one per contract row that names configuration, per settings entity". |
| 20 | FIXED | The GPT prompt is in the pack, the README is corrected, and build_entities.py's docstring says revision 4. |
| 21 | FIXED | CR 154 header, the SYSTEMS_SURVEY EXT row, the Procore row (CR 156) and CR 173 ("would work ... once built"). |
| 22 | FIXED | CR 201 now says a verified date "is kept as text and does not reach the authority logic". Draft 7 was not aligned (M12). |
| 23 | FIXED (as asked) | RIC rows 2, 4 and 28 add the policy-approval line and DC-8 (rules_cost.py 45). However, the wording the first check proposed for detection findings is not what the code does (S4). |
| 24 | FIXED | CR 285 and 286. |
| 25 | FIXED | CR 19 and CR 177 say "5 of those 52 are partial". The five are E03, E05, E16, E53 and E98, matching the CSV. |
| 26 | FIXED | CR 177 explains why the two metrics differ (47 / 53 against 48 / 52). |
| 27 | FIXED | CR 19 identifies PG-DS-AC-12 as a data supply design criterion. |
| 28 | FIXED | fin/figure.py, fin/snap.py, fin/fmath.py, det/common.py, det/signal.py, det/detect.py, policy_approval.py and materiality.py are all present. |

---

## 2. The new defect candidates, checked against the code

| Candidate | Accurate? | Evidence |
| --- | --- | --- |
| DC-3 | Yes in substance; the wording is imprecise (S3) | `fin/policy.py` validate_policy lines 91-94 skip a None map (`if mp is not None and ...`), so `po_status_map=None` validates to `[]`. I confirmed this by running validate_policy. `mkt/compare.py` line 170 calls `ctx.F.policy.get('po_status_map', {}).get(...)`, and the map is None, so it raises AttributeError. I reproduced this by calling the extracted last_paid with a stub context: `'NoneType' object has no attribute 'get'`. An empty dict `{}` is rejected by validation (`not mp`), and would not crash anyway, so "explicit empty value" is the wrong description: the trigger is an explicit None. The error occurs only when an order exists for the same project and material with a rate, a date and a status (compare.py 163-170). It is not caught: analysis.py 86-90 catches only MissingParam, and Analysis.block calls last_paid for every demand. So it stops the whole M6 run (mkt/detect.py 61), not only MP02 and MP09. demand.py 17 and 48 and fin/commitments.py 28 handle None correctly. Because fin/policy.py line 4 says "Each field is None until somebody configures it", an explicit None is a natural way to hold an unconfigured map, so this is likely to happen in practice. |
| DC-4 | Yes, with one wording point (M3) | MP05 (demand.py 136 `_po_class`), MP08 (suppliers.py 33) and MP10 (purchasing.py 22) find no qualifying order and evaluate nothing, with the run status still "evaluated". MP09: when last_paid returns None, discover returns [] (opportunity.py 45-47). The tax drop is at opportunity.py 26-31 and 57-58, where gst_bps is OPTIONAL (mkt/policy.py 97). MP02 does not evaluate nothing: it falls back to the cheapest like-for-like offer (rules.py 145). |
| DC-5 | Partly (M2) | rules.py 93 `if qs and not any(...)`. But `qs` holds only usable quotes (analysis.py 72 `q['ok']`), so a watched material whose quotes are all held also raises no quote signal. "No quote recorded at all" is too narrow. |
| DC-6 | Yes | compare.py 38-39 and 46-47 skip views that are not usable. demand_view sets QUANTITY_NOT_POSITIVE (common.py 199-201). MPD1 checks only the intake outcome (rules.py 481), so a usable zero-quantity demand is reported nowhere. |
| DC-7 | Yes | commitments.py 93-104 use the variation's class when it is stored and not in conflict, with no check of its reconciliation state. R02 is silent on "committed" (rules_cost.py 83-85). |
| DC-8 | Yes | rules_cost.py 45 loops over budget codes only, so actual cost on a code with no budget line, NO_CODE included, is never looked at. |
| DC-9 | Yes (M16) | rules_ops.py 240-247. The finding is quantified at the partial sum with the label "record". The observation text does say "rework cost is not known for every defect". |
| DC-1 scope | Yes | rules_commercial.py 78-80 is silent for any stored variation, whatever its class. |
| Quote validity note | Cannot be settled as written (M5) | The stage 1 intake policy instance is in `ingest/demo_setup.py`, which is not in the pack, so the claim "the stage 1 policy does not tolerate a missing validity date" cannot be checked. The pack does settle the case another way. TPL-BZ-QUOTES marks valid_until as required (FIELD_REGISTER.csv row 114), and a blank required cell is rejected at mapping (ingest/mapping.py 271-273). The default IngestPolicy also holds any missing optional value (specs.py 5-6; pipeline.py 61-65). The note understates where the error would arise: besides MP06 (rules.py 313) and buy timing (scenarios.py 65), `mkt/fresh.py` quote_state line 21 (`C.days(as_of, q['valid_until'])`, which parses None) would raise in every ranking (compare.py 86), MP01, MP02, MP03 and MP09. |

---

## 3. Numbers recomputed (all match)

- **Entities:** 100 in total: 11 covered, 42 partial, 47 missing.

  | Class | Total | Covered | Partial | Missing |
  | --- | --- | --- | --- | --- |
  | B | 60 | 9 | 27 | 24 |
  | I | 20 | 1 | 7 | 12 |
  | C | 10 | 0 | 4 | 6 |
  | V | 5 | 0 | 0 | 5 |
  | D | 3 | 1 | 2 | 0 |
  | X | 2 | 0 | 2 | 0 |

  Gap and status are consistent on every row.
- **Built paths:**
  - 38 entities have a path marked exists: 11 covered and 27 partial. 37 of them have T exists; E84 has only A.
  - 10 are partly-only: E01, N01, E44, E45, E46, E62, E77, E83, E90 and E96.
  - 52 have no built path: the 47 missing plus 5 partial (E03, E05, E16, E53 and E98).
- **Chart** (built / not built, from both the CSV and the recount): E 0/47, T 37/29, I 0/24, P 0/14, S 2/12, A 8/9, D 3/20. D built means E30, E35 and E83; S built means N01 and E90.
- **Contracts:** 56 rows and 47 distinct names. Removing the 4 group names gives 43: 13 M4, 16 detection and 14 M6. Five rows start with "every" (see M1).
- **Field coverage:** 56 rows. FIELD_SUPPLY_ROUTES has 211 rows, which is 155 fields plus 56 settings rows.
  - The 155 fields sit in 33 entities. All 155 have T built; 19 also have D (13 supplier_quote and 6 quote_reading). 33 are material.
  - Authority: 6 resolved, 48 on the reference intake (37 plus 11) and 101 on the second loop.
  - Settings rows by entity: N01 28, E90 24, E03 2, E20 1, E04 1.
  - "149 fields" is the 74 + 48 + 27 rows needing field authority, that is 155 - 6. "101 fields" is the 74 + 27 rows needing one intake. All 155 rows need the template check.
- **Others:** 65 B/V entities, of which 33 are supported by a cited source. 18 survey rows. 36 templates (29 BZ, 6 MKT, 1 EX), all draft. 215 template fields in 35 kinds.
- **Generators:** I ran build_systems, build_entities, build_rule_contracts, build_chart_data and build_field_coverage in that order in a copy, each as `python3 -I <script> .`. `diff -r` against the pack showed no difference and no stray file. The pack's files were not modified (`find -newer` was empty).

---

## 4. Problems

### BLOCKING

None.

### SHOULD FIX

**S1. "48 pass the reference intake's link, duplicate and supplier checks" is not true for 15 of them.**
- **Where:** CR 19 and CR 139, D7 146, and the FIELD_SUPPLY_ROUTES budget_line rows.
- **No checks at all:** fx_rate (3 fields), market_observation (7) and supplier (1) have `composite=()`, `strong=()` and `supplier_field=None` (specs.py 11, 28-29), and no relationship check applies to them (reconcile.py 173-243). Their records get none of the three checks.
- **Budget lines:** the same holds for budget_line (specs.py 27), but its 4 non-material fields are labelled "link, duplicate and supplier checks on the record".
- **The docstring:** build_field_coverage.py line 19 still says the 11 reference kinds come "with authority and reconciliation". This is the residue of finding 4.
- **Fix:** split the 48 into 33 (record-level duplicate, supplier or link checks: ap_invoice, credit_note, po_amendment, purchase_order and supplier_quote) and 15 (intrinsic checks only). Correct the docstring.

**S2. Document capture is still counted as accepting 19 fields today.**
- **Where:** CR 136 ("155, all by a synthetic import template; 19 of them ... also by document capture") and D7 146. In FIELD_SUPPLY_ROUTES, "built today (exists or partly)" is "D T" for those 19 fields.
- **What the code does:** CR 201 itself says documents.py "is not linked to the intake". Its stand-in extractor reads four values (quantity, unit_rate_cents, valid_until, supplier_text; documents.py 17), whose names do not match the supplier_quote fields. It reads none of the 6 quote_reading fields.
- **Why it matters:** this is the "accepted today" claim the first check (finding 5) asked to remove. It presents something unbuilt as a working intake.
- **Fix:** "accepted today: 155, all by a synthetic template; document capture accepts none of them into the intake yet (a stand-in quote extractor and the verification control exist, not linked)". In the CSV, either leave D out of "built today" or rename the column so that "partly" plainly means "not linked".

**S3. DC-3 is described as "an explicit empty value"; the trigger is an explicit None.**
- **Where:** CR 83 and RIC row 48.
- **Why it matters:** validation rejects `{}` (fin/policy.py 93), and `{}` would not crash. A reader testing with `{}` would conclude that DC-3 is false.
- **Also missing:**
  - The DC-3 note is absent from MP09's row (RIC row 55) and from the comparison row's reference. The CR table names both.
  - Nothing says the error is uncaught and stops the whole M6 run (analysis.py 86-90 catches only MissingParam).
  - The condition is not given: a matching order with a rate, a date and a status.
- **Fix:** "holds po_status_map as an explicit null (None), which validation accepts; when any order for the requirement's project and material has a rate, date and status, last_paid raises AttributeError and the M6 run stops". Add DC-3 to RIC row 55.

**S4. The new "every detection rule" row (RIC row 4) is incomplete, and one of its claims is not what the code does.**
- **Missing states:** it omits DET_POLICY_NOT_PINNED (run status cannot_assess) and SWITCHED_OFF_IN_POLICY (disabled), at det/common.py 24-33. The M6 row (RIC row 5) states the equivalents.
- **The approval claim:** "findings under a policy whose approval the audit log does not confirm say so" comes from the det/policy.py docstring, but no code does it.
  - Signals carry no approval mark. Only the run result records `det_policy.approved` (det/detect.py 54).
  - Severity bands are applied from the pinned policy whether or not it is approved (det/detect.py 45; det/policy.py 141-149 does not check approval). This contradicts det/signal.py line 9: "severity is only ever 'unrated' until an approved band applies".
  - M6 does the same (mkt/detect.py 45 and 66).
  - RIC row 5 says nothing about an unapproved procurement policy, which only sets a flag on the run record.
- **Fix:** add the two states. Reword the approval line to "the run record says whether the detection policy is approved; individual findings do not, and severity uses the pinned policy's bands even when unapproved". Add the same line to RIC row 5. Offer the severity point to the owner as a further candidate (the prompt allows additions to the DC list).

**S5. Draft 7 contradicts its own correction about the authority register.**
- **The contradiction:** D7 186 says "The three records written directly today (retention events, authority register rows, extracted documents)". D7 33, the fix for finding 16, says the register "is not stored at all" and that draft 6 was wrong to say its rows were written to the store. D7 260 agrees with D7 33.
- **Fix:** "The two direct writes (retention events, extracted documents) and the in-code authority register are not part of this migration ...".

### MINOR

**M1. The number of group rows is understated.** "three of the rows state behaviour shared by a group" appears in CR 12, in the GPT prompt (line 9) and in D7 13. Five rows start with "every": two "every M4 figure" rows (RIC rows 2 and 6), plus the reference-intake, detection and M6 rows. Say "five rows (four groups)".

**M2. DC-5 and RIC row 47 are too narrow.** They say "no quote recorded at all"; the behaviour also covers quotes that are all held, because only usable quotes are considered (analysis.py 72). Held quotes are listed by MPD1. Fix: "no usable quote (none recorded, or all held)".

**M3. The DC-4 table cell lumps MP02 in with rules that evaluate nothing.** It reads "MP02 and MP09's reference ... no order qualifies, so these evaluate nothing". MP02 still evaluates, against the cheapest like-for-like offer (rules.py 145); only the last-paid reference is lost. RIC row 48 states this correctly; align CR 84.

**M4. The candidates are wrongly attributed to the agent check.**
- **Where:** CR 5 ("its check also found seven more behaviours"), CR 79 and OWNER_DECISIONS item 4 ("found by revision 4's agent check") say the agent check found DC-3 to DC-9.
- **The conflict:** the AUDIT.txt fix list (line 30 and item 8) says Claude found DC-3 while checking the agent's findings.
- **Fix:** "six from the agent check; DC-3 found by Claude while checking them". Separately, CR 122 calls DC-3 to DC-5 "the silent cases", but DC-3 is an error, not silence.

**M5. The quote-validity note (CR 92) needs rewording.** Its stated reason cannot be verified from the pack, and it understates where the error would arise (see the last row of the table in part 2). Base it on the template's required flag and the default IngestPolicy. Name fresh.quote_state as the first failure point. Note that a real builder's template could mark valid_until optional.

**M6. Some fields a rule reads are missing from its row**, so FIELD_SUPPLY_ROUTES's "read by" is incomplete. The field counts are not affected.
- **MP10 (RIC row 56):** orders are grouped by material and unit (purchasing.py 22-24), and filtered by status through _po_class. The row omits purchase_order unit_of_measure and source_status.
- **MP05 (RIC row 51):** omits source_status.
- **MP06 and MP07 (RIC rows 52-53):** omit supplier_quote delivery_basis and valid_until (rules.py 313; landed.py 77).
- **MP02 (RIC row 48):** omits the order's project_ref, material_ref and unit_of_measure (compare.py 163; eval_po 136).
- **quote_term moq:** the script silently drops `moq` (build_field_coverage.py 91-94 ignore an unknown one-word token), so moq appears in neither output.

**M7. A possible further candidate of the DC-6 kind.**
- **What happens:** po_view returns early, leaving project unset, for an order that is held at intake, unreconciled, or has no positive quantity (common.py 149-160). matched_orders then skips it before the not_counted list (demand.py 53). So MP03 and MP04 coverage, MP05, MP08, MP10 and last_paid omit such orders without listing them.
- **Not reported elsewhere:** MPD1's kinds do not include purchase_order (rules.py 467-468). Whether D02 lists them cannot be verified, because det/gather.py (PROJECT_DET_KINDS) is not in the pack.
- **Fix:** state it in RIC rows 49 and 50, or put it to the owner.

**M8. RIC row 9 (M4 actual cost, duplicates) has two inaccuracies.**
- **Misattributed setting:** the row names "Source Authority Register (E03)" as its configuration, but duplicate detection reads only the strong and composite keys (reconcile.py 103-136). As a result an E03 settings row appears for "M4 actual cost".
- **Missing case:** the row also omits the second candidate case, the same supplier invoice number with different details (reconcile.py 125-136).

**M9. RIC row 10 says too much with "only".** It says against_invoice_ref "is read again only to classify a credit no invoice applied". It is also how a credit is attributed to a project (fin/snap.py 36-37).

**M10. RIC row 2 does not name the reason code.** "at most provisional" could name its code, POLICY_NOT_APPROVED:<version> (fin/figure.py 119-120).

**M11. The policy wording is inconsistent.**
- **E90:** the ENTITY_REGISTER "APG today" cell for E90 is not reworded (the residue of finding 15).
- **Draft 7:** D7 89 says "'Partly' (the financial policy) means the policy object exists in code". N01 is now partly too, and D7 83 and 87 call both "versioned policy records".
- **"Approved":** "versioned, approved policy records" (CR 48, D7 87, ENTITY_REGISTER N01 "... in code") reads as if the records are approved. In the code a record counts as approved only after an audited approval (fin/policy.py 131-134; det/policy.py 5-8). Suggest "versioned policy records, counted as approved only once an audited approval exists; the schema and approval logic are in code".

**M12. Draft 7 is not aligned with the finding 22 fix.** D7 75 still says document capture "cannot verify dates yet". CR 201 has the corrected wording.

**M13. Draft 7's release section has inconsistencies and cites files the pack lacks.**
- **Release B:** D7 204 says release B is "mostly templates (14 of the 22, 13 still to build)". The table (D7 132) gives 1 built template and 14 to build, which is 15 templates.
- **The document record:** D7 196 says the middle path moves E83 into release A. The table's release A has only 1 document capture (quote readings), and "Later" has 1.
- **Settings counts:** D7 178 gives "29 rows need N01, 23 name E90, 9 both". This cannot be checked, because RELEASE_A_COVERAGE.csv and SUPPLY_PLAN.csv are not in the pack. By FIELD_SUPPLY_ROUTES, 28 contract rows name N01 and 24 name E90 (by rule: 28, 21 and 9 both).
- **Fix:** reconcile the figures, or add the two CSVs to the pack.

**M14. Some FIELD_SUPPLY_ROUTES rows and one CR cell are inaccurate.**
- **E20 settings row:** its verification route is "S: a versioned setup answer" and its source authority is "a setting is approved, not sourced". But E20's ways in are T and E, and supplier records are sourced data.
- **quote_reading.value_text:** it is labelled "carried unverified". M6 treats a reading as verified when the file's verified_by differs from extracted_by (spec.py 37-38). CR 120 rightly calls this "asserted by the file".
- **CR 141:** the settings cell does not mention E20.

**M15. RIC row 45 overstates the effect of some codes.** It says BASIS_NOT_IN_TABLE, CURRENCY_NOT_CONVERTED and the others "lower the offer to indicative or not comparable". Those codes give partially_comparable or are blockers (spec.py 136-141; compare.py 106-118); none of them makes an offer not_comparable.

**M16. DC-9 could note what the text already says.** CR 89 and RIC row 42 could say that the observation text already discloses "rework cost is not known for every defect" (rules_ops.py 248). What is missing is a lower-bound label on the amount, not disclosure.

---

## 5. What I could not verify from the pack

- **The stage 1 intake policy:** `ingest/demo_setup.py` is absent (see M5).
- **The draft 7 supply figures:** SUPPLY_PLAN.csv, RELEASE_A_COVERAGE.csv and build_supply_plan.py are absent, so D7 114, 129-137 and 178-179 are taken as stated. The 47 / 53 figure is plausible: N01 moved to partly and E16 lost its D path.
- **D02's kinds:** det/gather.py is absent (M7).
- **Running the code from the pack:** `canon`, `values` and `repro` are not in the pack. The code cannot be imported as a package, so I reproduced DC-3 by extracting compare.last_paid and fin/policy.validate_policy and calling them directly.
- **The freeze:** "freeze ee1ce3ec" cannot be checked (no hashes or repository in the pack).
