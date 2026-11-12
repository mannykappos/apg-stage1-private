# FOURTH AGENT CHECK OF REVISION 4: the fixes for the third check

**INDEPENDENT READ-ONLY (agent).** This is a fresh agent. Nothing in the pack was edited. Scripts ran only on copies, in a temporary directory, with `python3 -I`, on the synthetic code and data in the pack. The temporary directory was deleted afterwards.

**Scope.** Only the third check's findings and the builder's fix list for them ("Fixes for the third agent check", AUDIT.txt 819-847). Everything is checked against the code in `04_code_read/apg/`.

**Abbreviations used below:**
- CR = `01_CHANGE_REQUEST_REV4.md`
- D7 = `07_decisions/DATA_SUPPLY_SYSTEM_DRAFT7.md`
- OD = `07_decisions/OWNER_DECISIONS_2026-11-12.md`
- MSG = `03_registers/NOT_ASSESSED_MESSAGES.csv` (row = line number in the file, header = 1)
- RIC = `RULE_INPUT_CONTRACTS.csv` (same numbering)
- BML = `03_registers/build_message_list.py`

---

## 1. The message list

### 1(a) Reproduction: PASS

`python3 -I build_message_list.py <copy>/04_code_read/apg <tmp>` prints:

```
messages 512 by kind {'reason code': 260, 'plain-language reason': 135, 'run or figure state': 4,
'refusal or error raised': 101, 'silent today': 11, 'an uncaught error today': 1}
by audience {'person': 91, 'information': 89, 'builder': 257, 'system': 75}
```

- The CSV is byte-identical to the pack's (sha256 2dccaab9...b142a for both).
- I also ran every other generator in a fresh copy, in the README order, plus `build_supply_plan.py`. `diff -r` against the pack shows no difference and no stray file.

### 1(b) Everything the third check named as missed: PASS

**Reason codes.** All 17 codes in the third check's B1 table are now entries:
- TAX_BASIS, CTC_METHOD and FFC_BASIS `_NOT_CONFIGURED`
- A_COMPONENT, A_DEFINED_COMPONENT and A_FORECAST `_CANNOT_BE_ASSESSED`
- EXPIRED, STALE, RECONCILIATION, MISSING, GATE, FRESHNESS, CLEARED, ENCODING, TERMINAL and AMOUNT_COMPARISON_ONLY
- PERCENT_COMPLETE_RESTS_ON_A_FORECAST_THAT_IS_PROVISIONAL
- RECOGNISED_REVENUE_UNKNOWN and FORECAST_REVENUE_UNKNOWN (but see SF-4: their meaning is wrong)

**Texts.** These are all present:
- R07 "is not usable (held, disputed or duplicate)"
- "status %r maps to %s"
- The scenarios texts at mkt/scenarios.py 120, 130, 169, 185, 231 and 242
- mkt/intl.py 33-37
- mkt/fx.py 38
- mkt/spec.py 109-117
- "no approved register"
- the MP09 tax text
- the policy_approval.py refusals
- the ingest/freshness.py states

**The fin `b.unknown(...)` calls.** These are covered by their reason kind ("unknown: no_data", "method_not_configured", "stale", "unmapped", "held", "not_obtained", "invalid"), not by the input each one names. That is defensible because the figure names the input. It does cover the setup gaps the third check named.

### 1(c) Coverage: real misses remain

I used my own AST walk over every production module:
- every string constant and f-string piece, with its syntactic context
- a separate search for codes built with `%` or `+`
- a separate search for conditional (if/else) message branches

The misses below are messages the code gives when something cannot be fully assessed or done that the scan does not list. Each is checked in the code.

**Codes the scan does not list:**

| # | Where | What the code gives | Why the scan misses it |
| --- | --- | --- | --- |
| C1 | fin/figure.py 109 and 118 | `self.reason('COMPONENT_%s:%s' % (c['state'].upper(), nm))`, giving **COMPONENT_PROVISIONAL:<part>** and **COMPONENT_CANNOT_ASSESS:<part>** on every M4 parent figure whose part is not authoritative. This is the commonest "why is this figure provisional or blank" code in M4. | It is a code built by `%` formatting. CODE (BML 479) needs a `:`, a space, a `(` or the end after the code, so `COMPONENT_%s` is not matched, and EXPAND has no entry for it. |

**Builder setup and data gaps the scan does not list (M6 buy timing and comparison):**

| # | Where | Text | Why missed |
| --- | --- | --- | --- |
| C2 | mkt/scenarios.py 79 | "no storage rate is configured: storage cost is not assessed" | appended to a `gaps` list |
| C3 | mkt/scenarios.py 96 | "no financing rate or day-count basis is configured: the working-capital cost is not assessed" | same |
| C4 | mkt/scenarios.py 57 | "lead time is not stated: the delivery date cannot be computed" | same |
| C5 | mkt/scenarios.py 29-42, 53, 66 | payment terms not recorded or unreadable; deposit invalid; "the landed cost is incomplete ... a lower bound"; a quote that lapses before the order date | same |
| C6 | mkt/scenarios.py 148 | `'unknown': ['lead time is not stated' ... 'scenarios.lead_time_variation_days is not configured']`: the latest order date cannot be worked out | the dict key `unknown` is not in the scanned keys |
| C7 | mkt/spec.py 65 | `'reasons': ['material %s is not in the specification register']`: the offer is unverified, so it cannot be ranked (builder action: add the material to the register) | the dict key `reasons` is not scanned |
| C7a | mkt/spec.py 67 | "different product families (%s and %s)" | same |
| C8 | mkt/analysis.py 90, 95, 101, 108 | `{'subject', 'analysis': name, 'missing_parameter': str(e)}`: a whole M6 analysis is not assessed because a procurement setting is missing. Affects coverage, ranking, scenarios, reference, opportunities, duplicates, suppliers, evidence register and portfolio. Only the constant value "mkt_policy" (mkt/detect.py 61) is listed. The STATES row "not_configured" covers rules (mkt/rules.py 39-44), not analyses. | missing_parameter is only picked up when its value is a constant |
| C9 | mkt/demand.py 81 | "docket %s is held (%s) and is not counted"; also line 87, "records no accepted quantity: the delivered quantity is used" | `notes.append` is not scanned (compare "status %r maps to %s", which is listed) |
| C10 | mkt/fresh.py 86-92 | the offer limitations "expired ... history only, not a current basis", "dated after the as-of day: not yet usable", "%d days old against a limit", "is unavailable ..."; and the states expired, future, unavailable, historical_only | list appends; only the FRESHNESS:<qual> code is listed |

**Other categories the patterns do not reach:**
- **C11. The reason why a finding has no amount.** These are passed positionally to `S.unquantified(...)`, so none is listed. Only the generic "status: unquantified" row exists, marked information. Several are builder data gaps:
  - det/rules_commercial.py 48: "the variation has no recorded value"
  - det/rules_commercial.py 90: "no value is recorded for the instructed work"
  - det/rules_ops.py 199: "hourly rates are missing or zero for the recent window"
  - det/rules_ops.py 250: "no rework cost is recorded"
  - mkt/rules.py 260: "no order rate is available to value it"
  - mkt/rules.py 292: "an order amount is missing"
- **C12. Settings that are not well formed.** fin/policy.py validate_policy (59-112), det/policy.py (71-114) and mkt/policy.py (139-276) build a list of bad field names, raised as `PolicyError('; '.join(bad))` and the like. A person entering settings is refused with field names only, for example "po_status_map", "severity_bands" or "rule R01 parameter tolerance_bps". The scan only collects raises whose message is a constant.
- **C13. Minor information items.** The second branch of conditional texts is dropped, because `text()` (BML 490-492) takes only the first piece:
  - det/findings.py 279 "the condition was detected again after resolution" (its first branch is listed)
  - det/portfolio.py 47
  - mkt/suppliers.py 58
  - The supplier levels "not_measured" and "limited_history" (mkt/suppliers.py 56) and the FX state "not_converted" (mkt/fx.py 54, 61, passed positionally) are not listed either.

**Modules not scanned.** The docstring (BML 5-6) and SKIP (BML 28 and 477) leave out:
- `materiality.py`, which the README calls stage 1 code and AGG uses. Its M-* reasons do not reach users in today's code, so no message is lost.
- `mkt/ports_m6.py`, the port interface.

CR 271 says only "Test, demonstration and reference modules are left out".

**Wording against what the script does.**
- The docstring (BML 7-17), D7 172, PG-DS-AC-14 (D7 253), the README and the GPT prompt line 9 are now qualified correctly: a check by the listed patterns, not a proof.
- **CR 271 still claims more than the script does** (SF-1 and SF-2):
  - "collects every reason code (including codes the code builds by joining strings)". COMPONENT_* is a joined code that is missed.
  - "every reason, note and status the rules and analyses give". Only those given under the keys or variable names why, reason, note, status, missing_parameter and sample_note are collected; reasons, unknown, gaps, limitations, notes lists and unquantified reasons are not.

  The sentence after them ("That is a check by those patterns, not a proof") does not undo two plain "every" claims, which C1 to C12 contradict.

### 1(d) Correctness of the new and changed rows

I checked the rows the brief named against the code that gives them:
- every plain-language reason
- every run or figure state
- every refusal or error raised
- the 12 cases with no message today
- the listed codes, and the SF-1 and Minor 6 corrections

The following rows are wrong or misleading. **All other rows I checked are correct in meaning, audience and action for the code that gives them.** That includes:
- the PO and variation class names (fin/policy.py 37-38)
- EXPIRY_REVIEW (fin/cashview.py 89-93)
- TAX_BASIS, CTC_METHOD and FFC_BASIS `_NOT_CONFIGURED` (fin/revenue.py 27-29, fin/forecast.py 154-156)
- A_COMPONENT and A_DEFINED_COMPONENT `_CANNOT_BE_ASSESSED`
- EXPIRED (weak strength: det/rules_commercial.py 220)
- STALE, MISSING, CLEARED, ENCODING, TERMINAL, AMOUNT_COMPARISON_ONLY and PERCENT_COMPLETE_..._PROVISIONAL
- BUDGET_EXCEEDED_BY, FACILITY_STATEMENT_AFTER_AS_OF, CRITICAL_VALUE_MISSING, NON_ASCII_IDENTIFIER, RELEASE_REVIEW_DUE and NOT_RECONCILED
- the R07, R03, R09, AGG, LAB, DEF, R08, DLY, MP03, R05, MP08, import-check, landed-cost and document-capture texts
- the "unknown:" kinds
- the 101 raised refusals (audience by class)

Wrong or misleading:
- **MSG 189 and 94, RECOGNISED_REVENUE_UNKNOWN and FORECAST_REVENUE_UNKNOWN: wrong meaning (SF-4).**
- **MSG 362, "status: not_ingested": wrong action (SF-6).**
- **MSG 512-513, DC-11 and DC-12 (SF-5, MINOR-9, MINOR-10).**
- **MSG 59, 84, 246, 47, 259: wrong "given by" (MINOR-1).**
- **MSG 98 FRESHNESS, 100 GATE, 180 PROVISIONAL, 26 A_FORECAST_CANNOT_BE_ASSESSED, 289 "exclude: not_counted", 366 "status: refused", 369 "status: unknown", 295-300 "freshness: ..." (MINOR-2 to MINOR-8).**

---

## 2. The other fixes (SF-1 to SF-7, Minor 1 to 13)

| Fix | Verdict | Evidence |
| --- | --- | --- |
| SF-1 | PARTLY | The status-map classes and EXPIRY_REVIEW are right. RECOGNISED_REVENUE and FORECAST_REVENUE are moved to NOT_CODE (BML 304). The two `_UNKNOWN` entries that replace them have the wrong meaning (SF-4). |
| SF-2 | PARTLY | CR 87, CR 103, CR 117, RIC 4, RIC 5 and MSG 512 now say the run record and each stored finding carry `policy_unapproved`, and the signal does not. This is correct for create (det/findings.py 96) and update (294). It is not correct for a reopened finding (271-285) or a dismissed finding kept as is (264-268), which keep their old flag. The third check stated this ("The reopened path ... does not refresh the flag"); the fix does not carry it (SF-7). M6 findings carry only the detection policy's flag: correct (mkt/detect.py 66; det/findings.py 224, 230). |
| SF-3 | FIXED | CR 273, D7 89 and OD 19 say: severity bands are dollar amounts only (det/policy.py 141-149, `min_cents`); the materiality model (materiality.py 25 BASES) is not used by severity grading; grading by percentage is new design and new code. **This is accurate.** Severity is `severity_of(dp, abs(potential_impact_cents))` in det/detect.py 46 and mkt/detect.py 45. Small residue: CR 273 says "he has been told" while OD 19 says "the owner is told" (MINOR-13). |
| SF-4 | FIXED | "His setting them is the approval" is gone from the CR and D7, and is disclosed in OD 18. The Section 18 deferral and S06 §5.1 and §8 are in CR 273, D7 89 and D7 286. |
| SF-5 | FIXED | RIC 35 (R04B) states the decided warning. The field files were regenerated, and they reproduce. |
| SF-6 | PARTLY | D7 280 now says the added items carry no list numbers and that D7 "uses [the decisions document's numbering] elsewhere". But D7 103 still reads "The owner chose Level 2 with an early discovery gate (**decision 4**)". In the decisions document, decision 4 is the release rule; phone capture is decision 6 (DECISIONS_FOR_THE_OWNER.md 56, 78; CR 198 "Decision 6"). The new note makes this reference definitely wrong. D7's own list (271-278) is still numbered 1-8 with numbers that differ from the decisions document, and nothing says so (SF-8). |
| SF-7 | FIXED | DC-12 is accurate against fin/commitments.py 49-73. A held, duplicate, unreconciled, no-amount, after-cut-off, status-unknown or unmapped order hits `continue` before the amendment loop (76-110), and R02 reads only `po_lines[...]['amendments']` (det/rules_cost.py 80-90). DC-12 is in the CR table (88), the CR commitments and R02 rows (98, 105), RIC 12 and 29, MSG 513 and OD 21. But the CR also states DC-12 as decided (SF-3). |
| Minor 1 | FIXED | OD 10 attribution; "an uncaught error today (DC-3)" (BML 620); the docstring range (BML 16-17); CR 271 "eleven silent, DC-3 an uncaught error". |
| Minor 2 | FIXED | D7 46. |
| Minor 3 | FIXED | `build_field_coverage.py` docstring says "draft 7". |
| Minor 4 | FIXED | CR 79 and RIC 48 say "a usable order (or a duplicate candidate whose rate every candidate shares)". This matches mkt/compare.py 163-170. |
| Minor 5 | FIXED | CR 86. |
| Minor 6 | FIXED | All ten items, checked one by one. INPUT_MISSING is removed. |
| Minor 7 | FIXED | CR 77; OD 13. |
| Minor 8 | FIXED | CR 272 and D7 283 cite the same sections. |
| Minor 9 | FIXED | CR 273. |
| Minor 10 | PARTLY | ENTITY_REGISTER N01 (severity levels), E09 and E10 are updated. E23, E57, E59 and E64 are not, although CR 272 and D7 283 name them as where the cost-of-extra-work need lands (MINOR-11). |
| Minor 11 | FIXED | AUDIT.txt holds the third check and its fix list; CR 296 names it. |
| Minor 12 | FIXED | CR 273 names S06 §5.1 and §8. |
| Minor 13 | FIXED | CR 73, 264 and 270 say "raised and authorised as its own". **Nothing claims a build is authorised:** see CR 7 and 268, D7 7 and 11, OD 1, 5, 7 and 18, and GPT prompt 29. |

**DC-11 against the code.**
- Severity is applied from the pinned detection policy's bands with no approval check: det/detect.py 46 (`if dp is not None`), mkt/detect.py 45 and det/policy.py 141-149. det/signal.py 9 says otherwise. All accurate.
- The run record carries `det_policy.approved` (det/detect.py 54; mkt/detect.py 64). Accurate.
- The M6 run record also carries mkt_policy and mkt_spec approval (mkt/detect.py 66-67), as RIC 5 says. Accurate.
- Exceptions: the "each stored finding" wording (SF-7) and "nobody approved" (MINOR-9).

**DC-12 against the code.** Accurate, as above. Small inconsistencies in the list of skip reasons (MINOR-10).

---

## 3. Counts recomputed from the CSV

| Stated | Where | Recomputed |
| --- | --- | --- |
| 512 entries | CR 271, D7 172, README, GPT prompt 9, AUDIT 847 | 512 ✓ |
| 260 codes, 135 plain-language reasons, 4 states, 101 raised, 12 with no message (11 silent + 1 uncaught error) | CR 271, AUDIT 847 | 260 / 135 / 4 / 101 / 11 + 1 ✓ (sum 512) |
| builder 257, person 91, information 89, system 75 | CR 271, AUDIT 847 | 257 / 91 / 89 / 75 ✓ (sum 512) |
| DC-1 to DC-12 | CR table 77-88, BML SILENT, MSG 502-513, OD | 12 rows in each ✓ |

**Other counts.** The other counts in AUDIT 847 are unchanged by these fixes and reproduce:
- 100 entities (11 / 42 / 47)
- 56 contract rows, 43 rules and figures
- 155 fields and 55 settings rows
- the authority split 6 / 33 / 15 / 101

---

## 4. Problems

### BLOCKING

None.

### SHOULD FIX

**SF-1. A frequent M4 reason code built by formatting is missing, while CR 271 says every joined code is collected.**
- **Where:** CR 271: "collects every reason code (including codes the code builds by joining strings)".
- **The code:** fin/figure.py 109 and 118: `self.reason('COMPONENT_%s:%s' % (c['state'].upper(), nm))`, giving COMPONENT_PROVISIONAL:<part> and COMPONENT_CANNOT_ASSESS:<part>.
- **Fix:**
  1. Add `'COMPONENT_': ['COMPONENT_PROVISIONAL', 'COMPONENT_CANNOT_ASSESS']` to EXPAND, with entries. Builder: "the figure rests on a part that is provisional (or cannot be assessed); act on that part's reasons".
  2. Make the scan treat an upper-case constant followed by `%s` as a code prefix.
  3. Regenerate and recount.

**SF-2. Further cannot-assess messages the scan misses, and CR 271's "every reason, note and status the rules and analyses give".**
- **What is missed:** C2 to C12 in 1(c). The most important are:
  - **Settings not configured:** mkt/scenarios.py 79 and 96 (storage rate; financing rate or day count), 148 (scenarios.lead_time_variation_days); mkt/analysis.py 90-108 (any missing procurement setting stops a whole analysis, named only by its dotted path).
  - **Builder data gaps:** mkt/spec.py 65 (material not in the specification register); mkt/scenarios.py 57 and 148 (lead time not stated); the six unquantified reasons in C11.
  - **Settings validation:** the refusals in C12.
- **Fix:**
  1. Extend the patterns: list appends to `gaps`, `reasons`, `notes` and `limitations`; the dict keys `reasons`, `unknown` and `outstanding`; the first positional argument of `S.unquantified`; all branches of a conditional text; missing_parameter values from MissingParam; the `bad` lists of the three policy validators.
  2. Add the entries and recount.
  3. Reword CR 271 to the docstring's form: "every text given under the keys and names the script lists (why, reason, note, status, missing_parameter, sample_note)".
  4. Name the modules left out: materiality.py and mkt/ports_m6.py, as well as test, demonstration and reference modules.

**SF-3. DC-12 is stated as decided by the owner, but the owner's record says it is pending.**
- **The record:** OD 21: "puts it to the owner with revision 4; pending his word". CR 270 and GPT prompt 3 and 29 agree that it is pending.
- **Text that contradicts it:**
  - CR 5: "On 2026-11-12 the owner decided how all twelve are fixed".
  - CR 17: "All twelve defect candidates (DC-1 to DC-12) are decided".
  - CR 73: "The owner decided on 2026-11-12 ... that all of them are fixed after stage 1".
  - CR 296: "the further defect candidates (DC-3 to DC-12) are decided by the owner (DC-12 put to him with this revision)", which contradicts itself.
  - MSG 513: today column "no message: the decided fix adds it (DC-12)".
- **Fix:** "DC-1 to DC-11 are decided; DC-12 is put to the owner with this revision". In BML 620, give DC-12 "the proposed fix adds it".

**SF-4. MSG 189 and 94: RECOGNISED_REVENUE_UNKNOWN and FORECAST_REVENUE_UNKNOWN have the wrong meaning and audience.**
- **The rows:** "recognised revenue is not known, so the margin percentage cannot be assessed","resolve what stops the revenue figure" (builder, commercial manager), and the same for forecast revenue.
- **What the code does:**
  - `pct_figure` (fin/margins.py 44-55) gives `label + '_UNKNOWN'` only after the margin itself has a value, and only when the chosen denominator is absent from the margin record's classified data (fin/calc_records.py 70-75).
  - A recognised margin always classifies `recognised_revenue_cents` when it has a value (fin/margins.py 33). A forecast margin always classifies `ffr_cents` (fin/forecast.py 188).
  - So the code is given only when the margin run and the denominator do not match. Examples: a cash-adjusted margin, which classifies neither (fin/cashview.py 199-205); a forecast margin asked for "recognised_revenue"; a recognised margin asked for "forecast_revenue".
  - It is never a revenue data gap.
- **Fix:** "the margin run named does not carry this revenue basis (for example a percentage of a cash-adjusted margin, or a basis the margin was not built on), so no percentage is given". Audience: person (the one asking for the percentage) or system. Action: "choose the margin run that carries this basis".

**SF-5. DC-11's message row and CR 87 overstate today's behaviour.**
- **Where:** MSG 512 "findings are graded with severity bands nobody approved"; CR 87 "even when nobody approved them".
- **What the code does:** when the pinned detection policy is approved, its bands are approved. The defect is that grading does not depend on approval.
- **Fix:** "findings are graded with the pinned detection policy's bands whether or not that policy is approved". This is how D7 89 already puts it: "whether or not anyone approved them".

**SF-6. MSG 362, "status: not_ingested", has the wrong meaning and action.**
- **The row:** "a stored file has not been ingested","import the file" (builder, bookkeeper).
- **What the code does:** ingest/filestore.py 101-124 returns `not_ingested` when APG refuses to ingest a stored file. The code says why: FILE_NOT_FOUND, SCAN_REQUIRED, SCAN_INFECTED or FILE_INTEGRITY. "Import the file" is wrong for all four.
- **Fix:** "APG refused to read a stored file; its code says why (not scanned yet, unsafe, damaged, not found)". Action: "act on the code given with it".

**SF-7. "Each stored finding says whether the detection policy is approved" is not true of reopened or kept-dismissed findings.**
- **Where:** CR 87, CR 103, RIC 4.
- **What the code does:** det/findings.py refreshes `policy_unapproved` on create (96) and update (294). It does not refresh it on the reopened path (271-285) or the kept-dismissed path (264-268), so the flag can be stale from an earlier run.
- **Fix:** add "(set when the finding is created or updated; a reopened finding keeps its earlier flag)".

**SF-8. SF-6 residue: a decision number in D7 is wrong under the note the fix added.**
- **Where:** D7 103: "The owner chose Level 2 with an early discovery gate (decision 4)". In the decisions document, phone capture is decision 6 and decision 4 is the release rule. D7 280 now asserts that D7 uses the decisions document's numbering elsewhere.
- **Fix:**
  1. Change it to "(decision 6)".
  2. Add one line before D7 271: "the numbers in this list are this draft's own; the decisions document's numbers are given in brackets". Or renumber the list.

### MINOR

1. **Wrong "given by" for expanded codes** (BML 607 takes the union of every EXPAND site, or only the literal sites):
   - MSG 59 CTC_METHOD and MSG 84 FFC_BASIS `_NOT_CONFIGURED` say "fin/forecast.py fin/revenue.py"; revenue.py gives neither.
   - MSG 246 TAX_BASIS_NOT_CONFIGURED: forecast.py does not give it directly.
   - MSG 47 COST_SCOPE_NOT_CONFIGURED omits fin/forecast.py 156.
   - MSG 259 VARIATION_STATUS_MAP_NOT_CONFIGURED omits fin/revenue.py 29.

   Fix: record the source file per expanded code.
2. **MSG 98 FRESHNESS.** The action "get a current quote" is incomplete. The stale input may be the FX rate or the index (mkt/compare.py 84-87). "historical_only" (expired or future-dated) makes the offer not rankable at all, not just not definitive (compare.py 124). Fix: "get a current quote, exchange rate or index observation, as the limitations name; an expired quote is history only".
3. **MSG 100 GATE.** The audience is information but the action is "act on the gate codes". Make it builder, or make the action "none; see the gate codes".
4. **MSG 180 PROVISIONAL.** "a total that includes values not yet authoritative" is not quite right. The provisional total is a separate sum of the candidate values of records that are not authoritative only, and it cannot be added to the authoritative total (source_authority.py 270-279, 240).
5. **MSG 26 A_FORECAST_CANNOT_BE_ASSESSED.** "so the movement is not explained" should read "so no movement bridge is built". It is also given when a run that is not a forecast is passed (fin/bridge.py 26-28).
6. **MSG 289 "exclude: not_counted".** "a forecast line the method does not use","none" (information). Two problems:
   - The class is also given to a credit whose invoice is not counted (fin/costs.py 107, TARGET_INVOICE_NOT_COUNTED).
   - It is in HELD (fin/figure.py 17), so it makes the figure provisional (figure.py 112). "No action" is misleading.
7. **MSG 366 "status: refused" and MSG 369 "status: unknown".**
   - `refused` (ingest/jobs.py 49) means no tenant could be established, an authentication fault. It should be system, not builder.
   - `unknown` is also given when the material is not in the specification register (mkt/spec.py 65) or the register is not approved (compare.py 95). "An attribute of the offer is not known" is only one case.
8. **MSG 295-300, "freshness: ...".** `ingest/freshness.py` is called by no other module in the pack. FreshnessPolicy is part of no settings record: M4 uses `freshness_days`, M6 uses the procurement policy. "Set the freshness limit in setup" names a setup that does not exist. Say that no run in stage 1 calls it.
9. **DC-11 wording in MSG 512.** See SF-5. Also the docstring (BML 461) says each DC "gets one" by the owner's decision, which is not yet so for DC-12 (SF-3).
10. **The DC-12 list of skip reasons is not the same everywhere.**
    - MSG 513 has "(held, duplicate, after the cut-off, status unknown)".
    - RIC 12 has "held, duplicate, after the cut-off or status-unknown".
    - CR 88, RIC 29 and OD 21 add "or unmapped".

    The code also skips orders with no reconciliation state or no amount (fin/commitments.py 53). Use one list.
11. **Minor 10 is only partly done.** ENTITY_REGISTER E23, E57, E59 and E64 do not list "the cost of extra work recorded against its instruction or variation". CR 272 and D7 283 name them. Add it, or say the need is recorded on E09 and E10 only, until the Section 18 assessment.
12. **Lesser row points.**
    - MSG 3 ACTUALS_AFTER_FORECAST_DATE_NOT_ADDED is given whenever the as-of date differs from the forecast date, whether or not any cost arrived (fin/forecast.py 201-204).
    - MSG 191 RECONCILIATION's "resolve the hold" does not fit outcome rejected_by_review.
    - MSG 253 UNIT_INCOMPATIBLE (information) and MSG 312 "no declared conversion" (builder) describe the same condition with different audiences.
13. **CR 273: "that was wrong, and he has been told".** OD 19 says "the owner is told". Whether he has already been told is not verifiable from the pack. Use the same tense as OD.

---

## 5. Totals

**0 blocking, 8 should fix, 13 minor.**

The fix list is mostly made. Reproduction, the third check's named misses, the counts, SF-3, SF-4, SF-5 and most minor items check out against the code.

The residue:
- **Coverage.** The rewritten scan still misses a frequent joined M4 code (COMPONENT_PROVISIONAL and COMPONENT_CANNOT_ASSESS). It also misses several M6 "not configured / not assessed" messages, the analysis-level missing parameters, unquantified data-gap reasons and settings-validation refusals. CR 271 still says "every" in two places.
- **The owner's record.** The CR in four places, and one MSG row, say DC-12 is decided, while the owner's record says it is pending.
- **Wrong rows.** The two `_UNKNOWN` entries that replaced the third check's SF-1 rows have the wrong meaning, "status: not_ingested" gives the wrong action, and the DC-11 wording overstates.
- **Small residue:** of SF-2 (the reopened-finding flag) and SF-6 (D7 103 "decision 4").
