# INDEPENDENT READ-ONLY (agent) check 3 of APG Data Readiness CR, revision 4 (scoped to the last changes)

Pack: `pack4/APG_DATA_READINESS_CR_REV4_PACK/`, 2026-11-12. I edited nothing in the pack. I ran every script with `python3 -I` in a temporary copy, which I have since deleted along with my helper scripts. All data is synthetic and no network was used.

References:
- `CR n` is a line of `01_CHANGE_REQUEST_REV4.md`.
- `D7 n` is a line of `07_decisions/DATA_SUPPLY_SYSTEM_DRAFT7.md`.
- `OD n` is a line of `07_decisions/OWNER_DECISIONS_2026-11-12.md`.
- `RIC row n` and `MSG row n` are lines of `RULE_INPUT_CONTRACTS.csv` and `NOT_ASSESSED_MESSAGES.csv`, with the header as line 1.
- Code paths are relative to `04_code_read/apg/`.

**Totals: 1 BLOCKING, 7 SHOULD FIX, 13 MINOR.**

The re-check fixes are almost all made: 17 FIXED, 4 PARTLY, 0 NOT FIXED. Every number reproduces, and every generator gives byte-identical output.

The blocking problem is the new message list. It is presented as complete ("the script fails if the code gives a message the list does not cover, so none is missed"), but it is not. Its patterns miss at least 17 reason codes, and the contracts register itself names some of them. It also misses whole classes of not-assessed reasons in modules it does not scan.

---

## 1. The re-check fixes (S1–S5, M1–M16)

| # | Verdict | Evidence |
| --- | --- | --- |
| S1 | FIXED | CR 20, 137-138 and D7 147 give 6 / 33 / 15 / 101. In FIELD_SUPPLY_ROUTES, budget_line's 4 non-material fields, fx_rate, market_observation and supplier read "reference intake: field validation only (no duplicate, supplier, link or field-authority c...)". `build_field_coverage.py` lines 18-20 are corrected, and RECORD_CHECKS is at line 123. Residue: the docstring line 17 still says "Data Supply System draft 6" (MINOR-3). |
| S2 | FIXED | CR 134 says "document capture accepts none of them into the intake yet". The CSV marks the 19 quote fields "D (partly: not linked to the intake; accepts none of these fields today) T". D7 147 agrees. |
| S3 | FIXED | CR 79, RIC row 48, RIC row 55 (MP09) and RIC row 45 (comparison) say "explicit null (None), which validation accepts", give the condition, and say the error is uncaught and stops the whole run. This matches fin/policy.py 91-94, mkt/compare.py 170 and mkt/analysis.py 86-90. A small imprecision in the condition remains (MINOR-4). |
| S4 | PARTLY | RIC row 4 gives DET_POLICY_NOT_PINNED and SWITCHED_OFF_IN_POLICY, and RIC row 5 and CR 102 and 116 add the approval line. But the wording adopted, "individual findings do not [say whether the policy is approved]", is wrong: the stored finding record carries `policy_unapproved` (det/findings.py 96, 230, 294). See SF-2. |
| S5 | FIXED | D7 189 says "The two direct writes (retention events, extracted documents) and the in-code authority register are not part of this migration". |
| M1 | FIXED | "five rows state behaviour shared by four groups": CR 12, D7 13, GPT prompt line 9. |
| M2 | FIXED | CR 81 and RIC row 47 say "no usable quote (none recorded, or all held) ... held quotes are listed by MPD1". |
| M3 | FIXED | CR 80: "MP02 still evaluates, against the cheapest like-for-like offer, but loses its last-paid reference". |
| M4 | PARTLY | CR 73 and CR 120 are corrected. OD 10 still reads "**DC-3 to DC-9 and the DC-1 scope question** (found by revision 4's agent check)". The new text also calls DC-3 silent again: MSG row 274 "silent today (DC-3)", CR 270 "the silent cases (DC-1 to DC-11)", D7 172 "the 11 silent cases DC-1 to DC-11", and the `build_message_list.py` docstring line 11 "the silent cases (DC-3 to DC-11)" (which is also the wrong range). See MINOR-1. |
| M5 | FIXED | CR 89 rests the note on the required flag, the mapping rejection and the default IngestPolicy, and names `mkt/fresh.py` quote_state. |
| M6 | FIXED | MP10 (RIC row 56) has unit_of_measure and source_status. MP05 (RIC row 51) has source_status. MP06 and MP07 (RIC rows 52-53) have delivery_basis and valid_until. MP02 (RIC row 48) has project_ref, material_ref and unit_of_measure. moq is listed (`build_field_coverage.py` KNOWN). |
| M7 | FIXED | DC-10 is in CR 86 and in RIC rows 48-51, 54 and 56. |
| M8 | FIXED | RIC row 9 no longer names E03, and the second duplicate case is added. Settings rows for E03 are now 1. |
| M9 | FIXED | RIC row 10: "against_invoice_ref is also how a credit is attributed to its project (fin/snap.py)". |
| M10 | FIXED | RIC row 2: "POLICY_NOT_APPROVED:<version> (fin/figure.py)". |
| M11 | FIXED | The E90 and N01 "APG today" cells, CR 49 and D7 87 and 90 say "versioned policy records, counted as approved only once an audited approval exists". |
| M12 | PARTLY | D7 75 is corrected. D7 46 (the intake-stage table, "Human verification of document values") still says "not linked to the intake; dates cannot be verified yet". See MINOR-2. |
| M13 | FIXED | D7 207 gives 15 templates (1 built, 14 to build). D7 199 handles E83, giving 45 and 28. D7 181 explains 29 / 23 / 9 against 28 / 24. The supply plan files are in the pack, and D7 182 gives 47 gap rows. |
| M14 | FIXED | In the FIELD_SUPPLY_ROUTES E20 settings row, the verification route is "T: intake validation ... E: the person entering it is recorded", and the source authority is "supplier records are sourced data ...". quote_reading.value_text reads "asserted by the file". CR 140 names E20. |
| M15 | FIXED | RIC row 45: "make the offer partially comparable or block a definitive ranking (none of them makes it not comparable)". |
| M16 | FIXED | CR 71, CR 85 and RIC row 42 say the text already discloses this, and that what is missing is the lower-bound label. |

---

## 2. Defect candidates DC-1 to DC-11 against the code and the owner's record

| DC | Today's behaviour: accurate? | Decided fix: matches OD? |
| --- | --- | --- |
| DC-1 | Yes. det/rules_commercial.py 77-80 is silent whenever `F.get('variation', link) is not None`, whatever the variation's class or state. | Yes in substance (OD 8, 12). The CR 77 gloss "a warning that the work may not be paid" adds to OD's "a warning that the client rejected the variation" (MINOR-7). |
| DC-2 | Yes. det/rules_ops.py 142 does `ot = ... if fl.get('overtime_hours') is not None else 0`, and det/intake.py 27 puts overtime_hours in warn_unknown, so it gets VALUE_MISSING. | Yes (OD 9). |
| DC-3 | Yes. fin/policy.py 92-93 skips a None map. mkt/compare.py 170 calls `.get('po_status_map', {}).get(...)`, which raises on an explicit None. mkt/analysis.py 86-90 catches only MissingParam, and mkt/detect.py 61 calls A.block(). The condition is slightly overstated (MINOR-4). | Yes. OD 11-12 settle the rule and leave the wording to the fix. |
| DC-4 | Yes. mkt/opportunity.py 26-31 and 57-58 drop the opportunity (`if quote_unit is None: continue`), and the MP02 fallback is correct. | Yes. |
| DC-5 | Yes. mkt/rules.py 93 has `if qs and not any(...)`, and mkt/analysis.py 72 keeps only `q['ok']` quotes. | Yes. |
| DC-6 | Yes. mkt/common.py 199-201 is QUANTITY_NOT_POSITIVE. MPD1 lists only intake-held records (mkt/rules.py 476-480). | Yes. |
| DC-7 | Yes. fin/commitments.py 93-104 reads `vcls` from any stored, non-conflicting variation without checking its state. | Yes. |
| DC-8 | Yes. det/rules_cost.py 45 loops `for code in sorted(budget)`. | Yes. |
| DC-9 | Yes. det/rules_ops.py 240-250 quantifies at the sum, labelled 'record', and the text says "not known for every defect". | Yes. |
| DC-10 | Yes for M6. mkt/common.py po_view 149-160 returns early, before `project` is set, for an order that is held, unreconciled or has no positive quantity. matched_orders (mkt/demand.py 53-54) and last_paid (compare.py 163-164) then skip it by project mismatch before any not-counted list. MPD1's kinds (mkt/rules.py 466-467) do not include purchase_order. **det/gather.py and D02 do not list such orders either.** det/detect.py 19 runs project D02 over PROJECT_DET_KINDS (notice, delay_event, plant_hire, timesheet, work_output, defect; det/gather.py 13), and det/detect.py 20 runs tenant D02 over compliance only. purchase_order is pinned for tenant runs (det/gather.py 14) but not reported. M4 commitments does list held and unreconciled orders among its exclusions (fin/commitments.py 53-62), but not zero-quantity ones. The CR does not say any of this (MINOR-5). | Yes (OD 19). |
| DC-11 | **Partly wrong.** Severity is applied from the pinned bands with no approval check (det/detect.py 46, mkt/detect.py 45, det/policy.py 141-149), and det/signal.py 9 says otherwise: both accurate. But "individual findings do not [say whether the policy is approved]" is wrong. det/findings.py 96 stores `'policy_unapproved': bool(dp_unapproved)` on every new finding, and line 294 refreshes it on update, from `res['det_policy']['approved']` (line 230). M6 runs are ingested by the same code (line 224 accepts MKT_FORMULA_IDS), so M6 findings carry the *detection* policy flag but not the procurement policy's. See SF-2. | Yes (OD 20). |

---

## 3. NOT_ASSESSED_MESSAGES.csv and build_message_list.py

**(c) Reproduction.** `python3 -I build_message_list.py <copy>/04_code_read/apg <tmp>` prints "messages 283 codes 243 rule texts 25 states 4 silent 11 by audience {'person': 31, 'information': 48, 'builder': 178, 'system': 26}". The CSV is byte-identical to the pack's.

**(a) Completeness.** It is not complete; see BLOCKING-1. An AST scan of every string constant, concatenation and f-string in the production modules finds the gaps listed there.

**(b) Correctness.** I checked all 283 entries against the code that gives them; the code context for every code was extracted and read. The wrong or misleading entries are in SF-1 (four entries that are wrong) and MINOR-6 (lesser ones). The remaining entries are correct in meaning, audience and action for the code that gives them.

---

## 4. Problems

### BLOCKING

**B1. The message list is presented as complete, and it is not.**

**Where the claim is made:**
- CR 270: "lists every reason code and every not-assessed message the production modules can give ... the script fails if the code gives a message the list does not cover, so none is missed".
- D7 172: "it fails if the code gives a message it does not cover".
- PG-DS-AC-14 is presented as met by it (D7 253 and 282).
- GPT prompt line 9.
- `build_message_list.py` docstring lines 10-11: "So the list is complete for the code it was run on".
- AUDIT.txt 532.

**What the scanner can see.** Its own check can only fail on what its patterns see:
- CODE (line 321) needs two or more characters before the first underscore and at least one underscore, followed by a quote or a colon.
- WHY (line 322) runs only on det/rules_*, det/common, mkt/rules, mkt/demand, mkt/suppliers and mkt/analysis.
- policy_approval.py is not scanned, though the README calls it a production module.

**Missed reason codes.** All are absent from the CSV; I grepped for each.

| Code | Where the code gives it | Note |
| --- | --- | --- |
| `TAX_BASIS_NOT_CONFIGURED` | fin/revenue.py 25-27, built as `fld.upper() + '_NOT_CONFIGURED'` | CR 98 itself names it ("TAX_BASIS ... not configured stops it") |
| `CTC_METHOD_NOT_CONFIGURED`, `FFC_BASIS_NOT_CONFIGURED` | fin/forecast.py 154-156 | CR 99 and RIC row 16 name them ("each *_NOT_CONFIGURED stops it") |
| `A_COMPONENT_CANNOT_BE_ASSESSED` | fin/forecast.py 192 | named in RIC row 16 |
| `A_DEFINED_COMPONENT_CANNOT_BE_ASSESSED` | fin/cashview.py 203 | named in RIC row 27 |
| `A_FORECAST_CANNOT_BE_ASSESSED` | fin/bridge.py 28 | |
| `EXPIRED:<refs>` | det/rules_commercial.py 224 | R07's limit; CR 69 and RIC row 38 name it |
| `STALE:<label>` | fin/forecast.py 93 | |
| `RECONCILIATION:<outcome>`, `MISSING:<fields>` | mkt/common.py 131, 168, 187 | RIC row 45 names RECONCILIATION |
| `GATE:<class>`, `FRESHNESS:<qualification>` | mkt/compare.py 108, 110 | RIC row 45 names both |
| `CLEARED:<code>` | ingest/reconcile.py 320 | |
| `ENCODING` | ingest/mapping.py 223 | a file-level rejection the builder sees |
| `TERMINAL` | det/findings.py 401, 519 | |
| `AMOUNT_COMPARISON_ONLY` | det/rules_cost.py 140 | R03's limit; followed by a space, so not matched |
| `PERCENT_COMPLETE_RESTS_ON_A_FORECAST_THAT_IS_<STATE>` | fin/margins.py 39 | |
| `<label>_UNKNOWN` | fin/margins.py 51, with labels from fin/calc_records.py 72, 75 | gives RECOGNISED_REVENUE_UNKNOWN and FORECAST_REVENUE_UNKNOWN; the list instead has RECOGNISED_REVENUE and FORECAST_REVENUE as "labels", which is wrong (SF-1) |

**Missed plain-language reasons inside the scanned modules:**
- det/rules_commercial.py 170: R07 `kind + '/' + key + ' is not usable (held, disputed or duplicate)'`.
- mkt/demand.py 61: the coverage not-counted reason `'status %r maps to %s'`.

**Missed reasons in modules not scanned:**
- **fin figure unknowns.** About 23 `b.unknown(...)` calls carry no code. Some are builder setup gaps:
  - fin/revenue.py 34: no contract.
  - fin/revenue.py 74: an approved variation with no value.
  - fin/forecast.py 88 and fin/cashview.py 154: freshness not configured.
  - fin/cashview.py 163: carrying overlap not configured.
  - fin/commitments.py 113: credit_reopens_commitment not configured.
  - fin/forecast.py 177: no budget.
- **mkt/scenarios.py:**
  - 120: `'scenarios.context_points is not configured'`.
  - 130: insufficient_history.
  - 169: no price paths.
  - 185: `'scenarios.stage is not configured'`.
  - 231 and 242.
- **mkt/intl.py 33-37:** unresolved import-check reasons.
- **mkt/fx.py 38:** `'no usable %s rate on or before %s'`.
- **mkt/spec.py 109-117** (unit reasons) and **mkt/compare.py 96, 142** (`'no approved register'`).
- **mkt/opportunity.py 31:** the MP09 tax reason.
- **policy_approval.py:** the approver-facing refusals at lines 97-130.
- **ingest/freshness.py 10:** the freshness states (stale, missing, unconfigured, future_dated).

**Why it matters.** Decision 13 and PG-DS-AC-14 rest on this list, and the owner is told none is missed. Among the misses are setup gaps that stop M4 figures: the tax basis, the cost-to-complete method and the forecast basis. GPT is asked exactly this question (prompt line 21) and will find them.

**Fix:**
1. Scan with an AST over all production modules, policy_approval.py included. Treat every upper-case string constant as a candidate code, with or without an underscore, including the left side of a `+` or an f-string prefix.
2. Expand `fld.upper() + '_NOT_CONFIGURED'` and `label + '_UNKNOWN'` from their literal tuples.
3. Include `b.unknown(...)` and the `'why'` and `not_assessed` texts of every module.
4. Add the missing entries, regenerate, and recount the 283 and its splits.
5. Until then, reword CR 270, D7 172 and 282, the prompt and the docstring: "every message its patterns find (patterns listed); the list is checked against the code but cannot prove completeness".

### SHOULD FIX

**SF-1. Four message-list entries are wrong for the code that gives them.**
- **MSG row 159, PO_STATUS_MAP_NOT_CONFIGURED.** It says "set up the purchase-order statuses (open, committed, closed)". The classes are `committed, draft, cancelled, closed` (fin/policy.py 38); there is no "open". Fix: "(map each of your order statuses to committed, draft, cancelled or closed)".
- **MSG row 242, VARIATION_STATUS_MAP_NOT_CONFIGURED.** It says "(approved, submitted, rejected, disputed)". The classes are `approved, unapproved, disputed, rejected` (fin/policy.py 37). Fix the class names in the same way.
- **MSG row 73, EXPIRY_REVIEW.** It says "a security instrument is close to expiry". The code is `review = bool(exp and exp <= as_of)` (fin/cashview.py 89-93), which means expired on or before the as-of date (RIC row 23 says "expired"). Fix: "a security instrument has reached its expiry date".
- **MSG rows 176 and 85, RECOGNISED_REVENUE and FORECAST_REVENUE.** They say "the result is labelled recognised / forecast revenue" (information). These strings are only the denominator label used to build `RECOGNISED_REVENUE_UNKNOWN` and `FORECAST_REVENUE_UNKNOWN`: the margin percentage cannot be assessed because its revenue basis is unknown (fin/calc_records.py 70-79, fin/margins.py 51). Fix: replace them with the two `_UNKNOWN` codes (builder: resolve what stops the revenue figure).

**SF-2. DC-11's "today's behaviour" says findings do not carry the policy's approval. They do.**
- **Where:** CR 87 ("individual findings do not"), CR 102, CR 116, RIC rows 4 and 5, MSG row 282 ("and do not say so").
- **What the code does:** det/findings.py 96 and 294 store `policy_unapproved` on each finding. M6 findings get the detection policy's flag, not the procurement policy's or the specification register's. The reopened path (det/findings.py about 266-285) does not refresh the flag.
- **What is true:** the signal does not carry it, and severity is graded from unapproved bands.
- **Fix:** "the run record and each stored finding (`policy_unapproved`, det/findings.py) say whether the detection policy is approved; the rule's signal does not; severity uses the pinned bands even when the policy is not approved; M6 findings carry only the detection policy's flag". Whether the flag is shown to the builder is not verifiable from the pack.

**SF-3. The severity text rests on a premise the code does not support: "The code already measures against the job's size (`materiality.py`: contract value, forecast final cost or forecast margin)".**
- **Where:** CR 272, D7 89, and the question as put to the owner (OD 20).
- **What the code does:**
  - Severity grading is `det/policy.py severity_of` (141-149): absolute `min_cents` bands only, with no percentage basis.
  - `materiality.py`'s relative bases (BASES, line 25) belong to the CR-02 materiality model.
  - The only production user is AGG (det/rules_cost.py 204, 224), which builds a model with `abs_cents` only.
- **Why it matters:** the owner chose "% and $" on the premise that the code already measures this way. Grading by a percentage of the job is new design and new code, not an existing capability.
- **Fix:** "Today severity bands are dollar amounts only (det/policy.py severity_of). The CR-02 materiality model can measure against contract value, forecast final cost or forecast margin, but no severity grading uses it." Tell the owner the premise was wrong (his decision likely stands).

**SF-4. "His setting them is the approval" conflicts, unstated, with the approval controls the pack keeps elsewhere.**
- **Where:** CR 272, D7 89, OD 20.
- **The conflicts:**
  - D7 90: "Every answer is versioned, submitted through the intake, and approved by the right role before it takes effect".
  - PG-DS-AC-05 (D7 244).
  - det/policy.py lines 6-8 and F-67: the detection policy counts as approved only when a `detection_policy_owner` who is not the proposer approves it, and severity bands live in that policy.
  - S06 §8: "Thresholds and weights must be documented, testable and approved".
- **Fix:** do not decide this here. State that how the builder's own setting relates to the existing two-person policy approval (F-67, PG-DS-AC-05) is to be settled in the Section 18 assessment. If the owner meant "the builder's organisation approves its own levels through its approver", say so. Add S06 §8 to the D7 286 cascade item.

**SF-5. RIC row 35 (R04B) still says the DC-1 scope question is undecided.**
- **What it says:** "whether a usable variation whose status maps to rejected should still silence it is not yet decided".
- **The conflict:** the owner decided it on 2026-11-12 (OD 12), and CR 68 and 77 say so.
- **Fix:** update the row in `build_rule_contracts.py` to the decided warning and regenerate. The field files read the contracts, so re-run `build_field_coverage.py` too.

**SF-6. Draft 7's added decisions 9–11 collide with the decisions document's numbering.**
- **What the list says:** D7 269 introduces "the eight below"; the added items are numbered 9, 10 and 11 (D7 282-284), and item 9 is titled "Decision 13".
- **The collision:**
  - CR 49 and CR 272 use "decision 9" for the default rule settings (decisions document §9).
  - D7 276 uses "(decision 11)" for the route.
  - D7 103 uses "(decision 4)" for phone capture, which is decisions document 6; CR 197 says "Decision 6".
- **Why it matters:** a reader of D7 meets "decision 9" meaning decision 13, and "replaces decision 9's owner-approved defaults" (CR 272) cannot be resolved.
- **Fix:** label the added items "Decision 13", "Owner requirement: extras and variations panel" and "Owner decision: severity grading", without list numbers. Use the decisions document's numbers throughout D7, or say once that D7's list numbers are its own.

**SF-7. A silent case of the DC kind, already stated in the contracts, is missing from the "silent cases" list.**
- **What the contracts say:** RIC row 12 ("amendments on an order that is held, duplicate, after the cut-off or status-unknown are never examined") and RIC row 29 (R02: "amendments on orders the commitments figure skips ... are neither assessed nor reported").
- **The claim it contradicts:** CR 270 and D7 172 present the list as listing "the silent cases".
- **Code:** fin/commitments.py 53-73 `continue`s before the amendment loop. The parent order is listed as an exclusion, but its amendments are not.
- **Fix:** put it to the owner as a further candidate (the prompt allows additions), or say why the parent order's listing is enough. Either way, say the silent list holds the candidates found so far, not all.

### MINOR

1. **M4 residue (attribution and labels).** Several places still call DC-3 silent or misattribute it:
   - OD 10 still attributes DC-3 to the agent check.
   - MSG row 274 is "silent today (DC-3)", though DC-3 is an error.
   - The docstring line 11 says "DC-3 to DC-11", but SILENT holds DC-1 to DC-11.
   - CR 270 and D7 172 call all eleven "silent".

   Fix: "the eleven cases (ten silent, DC-3 an uncaught error)", and correct OD 10.
2. **M12 residue.** D7 46: "dates cannot be verified yet". Use CR 200's wording: a verified date is kept as text and does not reach the authority logic.
3. **Stale reference.** The `build_field_coverage.py` docstring line 17 says "Data Supply System draft 6"; it should say draft 7.
4. **DC-3 condition (CR 79, RIC row 48).** The text says "whenever an order ... has a rate, a date and a status". In fact the order must also be usable, or held only as a duplicate candidate whose rate every candidate shares (compare.py 165-168); held, unreconciled and zero-quantity views carry no project and are skipped first. Add "usable (or a corroborated duplicate candidate)".
5. **DC-10 (CR 86).** Add that D02 does not list orders either (det/detect.py 19-20; det/gather.py 13-14). Also say that M4 commitments does list held and unreconciled orders as exclusions (fin/commitments.py 53-62), but not zero-quantity ones.
6. **Lesser message-list entries:**
   - MSG row 26, BUDGET_EXCEEDED_BY: marked information, but it makes the cost to complete unknown and the action falls to the builder. Make it builder.
   - MSG row 52, CRITICAL_VALUE_MISSING: the code gives it for any blank value the intake policy does not declare tolerable (ingest/pipeline.py 60-65; specs.py 5-6), not only for "critical" values. Add "or have it declared optional in the intake settings".
   - MSG row 122, NON_ASCII_IDENTIFIER: the code says "plain ASCII", not "letters and digits".
   - MSG row 185, RELEASE_REVIEW_DUE: "lodge the claim" asserts entitlement, while the code says "a review prompt, NOT an entitlement" (fin/cashview.py 60). Say "review whether release is due and, if so, claim it".
   - MSG row 129, NOT_RECONCILED: it says "the order", but it is also given for quotes (mkt/common.py 128).
   - MSG rows 129 and 144: whether "run reconciliation" is an action open to the builder is not verifiable from the pack.
   - MSG row 75, FACILITY_STATEMENT_AFTER_AS_OF: it stops carrying cost, so it should be builder, not information.
   - MSG row 99, INPUT_MISSING: it is "given by" only a docstring (fin/gather.py 20); the raise is in `repro`, which is not in the pack.
   - MSG rows 252 and 269: they treat "after the as-of date" as a gap ("enter the order date").
   - ACTUALS_AFTER_FORECAST_DATE_NOT_ADDED: "none; update the forecast" contradicts itself.
7. **DC-1 decided fix (CR 77).** "a warning that the work may not be paid": OD 12 records "a warning that the client rejected the variation, with what to do". Use the recorded wording.
8. **Citations.** CR 271 cites "S11 §3, §4, §8.1 and PG-CR-AC-09; S03 §5 and §6.1; S05 §3.2 and §7", while D7 283 cites "S03 §5; S05 §7" only; align them. I checked the locked docx files: S11 §3, §8.1, §11 and PG-CR-AC-09, S03 §5 and §6.1 and S05 §3.2 support the statement. S05 §7 (exposure categories) is weak support and could be dropped.
9. **CR 272: "for the severity bands it replaces decision 9's owner-approved defaults".** Decision 9 covered thresholds and windows (DECISIONS_FOR_THE_OWNER.md 104-110); severity bands were not named in it. Say "decision 9's defaults do not apply to the severity bands".
10. **The registers do not carry the new design items.** N01's required field groups (ENTITY_REGISTER) do not list the severity grading levels (dollar, percentage, or both). E09, E10, E23, E57, E59 and E64 do not list "cost of extra work recorded against its instruction or variation", although OD 16 says the data need "goes into revision 4". Add them to the field groups or gaps, or say they are prose-only until the Section 18 assessment.
11. **This check is announced but not in the pack.** The README line 22 and GPT prompt line 14 say AUDIT.txt holds "a scoped check of the last changes", but AUDIT.txt has only the first check, the re-check and two fix lists. Add this report and its fix list before sending, and update CR 295.
12. **The CR leaves out a check D7 records.** D7 286 checks severity against S06 §5.1; the CR's owner-decisions section (CR 265-272) does not carry it. Add one line, including S06 §8 (see SF-4).
13. **Authorisation wording.** CR 263 and CR 73 ("fix all of them in one change request immediately after stage 1") could be read as authorising that build. The owner chose the timing (OD 7, 11). Add "raised and authorised as its own change request" for clarity.

---

## 5. The new owner-decisions section and draft 7: consistency

The following points are consistent with OD items 4 to 7:
- PG-DS-AC-14 (D7 253).
- The readiness paragraph (D7 172).
- The severity setup bullet (D7 89): "dollar amount, a percentage of the job, or both; with both set, the grade applies as soon as either is reached; APG suggests no levels; until set, 'grading not set up yet'". This matches OD 20-22.
- The extras and variations panel (CR 271, D7 283).
- The cascade list (D7 286).
- "No build is authorised" is stated (CR 7, 267; D7 7, 11).

The exceptions are SF-3, SF-4, SF-6 and MINOR 8, 9, 12 and 13.

Entity ids are correct against ENTITY_REGISTER.csv:
- E09 Variation (client side), E10 Site instruction or direction.
- E23 Supplier invoice, E57 Timesheet entry, E59 Labour rate and classification, E64 Plant hire.
- E90 Financial policy, N01 Rule settings.

---

## 6. Numbers recomputed

All of the following match:
- **Entities:** 100 in total, 11 covered, 42 partial, 47 missing. By class: B 60/9/27/24, I 20/1/7/12, C 10/0/4/6, V 5/0/0/5, D 3/1/2/0, X 2/0/2/0.
- **Contracts:** 56 rows, 43 rules and figures.
- **Fields:** 155 fields in 33 entities; 33 material. Authority split 6 / 33 / 15 / 101. "149" = 155 - 6. All 155 are built by T, 19 also by D (partly). FIELD_SUPPLY_ROUTES has 210 rows, which is 155 fields plus 55 settings rows (N01 28, E90 24, E03 1, E20 1, E04 1).
- **Messages:** 283 = 243 codes + 25 texts + 4 states + 11 cases. By audience: builder 178, person 31, information 48, system 26. These are true for the CSV as generated, but they will change with B1.
- **Supply plan:** release A 44 (45 with E83, later then 28), B 22, later 29, optional 5. Minimum way in built 47, not 53.
  - Release A built: 32 templates, 3 APG records, 1 document capture and 2 setup; not built: 4 setup, 1 entry screen and 1 APG record.
  - Release A intake today: 9 reference, 24 second loop, 1 direct write, 2 derived, 4 with no record kind, 4 others.
  - Release B: 15 templates (1 built, 14 to build), 6 entry screens, 1 setup.
- **Release A coverage:** RELEASE_A_COVERAGE has 56 rows. 47 rows are not fully built, 28 are not through the reference intake, and the settings needs are N01 29, E90 23, both 9. Two figures read no records (security carrying cost, overdue receivables), and overdue receivables needs only release B data.
- **Chart:** E 0/47, T 37/29, I 0/24, P 0/14, S 2/12, A 8/9, D 3/20.
- **Templates and fields:** 36 templates (29 BZ, 6 MKT, 1 EX); 215 template fields in 35 kinds. 18 survey rows (16 systems).
- **Generators:** I ran build_systems, build_entities, build_rule_contracts, build_chart_data and build_field_coverage in that order in a copy, each as `python3 -I <script> .`, then `build_supply_plan.py ../../03_registers` and `build_message_list.py`. `diff -r` against the pack showed no difference and no stray file.

Not verifiable from the pack:
- Whether `policy_unapproved` is shown to the builder.
- What `repro` raises, since it is not in the pack.
- Whether reconciliation is an action open to the builder.
- The freeze ee1ce3ec.
