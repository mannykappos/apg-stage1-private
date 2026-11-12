# INDEPENDENT READ-ONLY (agent) check 5 of APG Data Readiness CR, revision 4 (the changes made after GPT's check of revision 4)

**INDEPENDENT READ-ONLY (agent).** I am a fresh agent. I edited nothing in the pack. I ran scripts only on a copy, in `agentchk5_tmp/`, with `python3 -I`, using the synthetic code and data in the pack. I deleted the temporary directory afterwards.

Pack: `pack4/APG_DATA_READINESS_CR_REV4_PACK/`. Line numbers are the file's own (`cat -n`).

**Totals: 1 blocking, 6 should fix, 11 minor.**

---

## 0. Method

- **Reproduction.** I copied the pack and ran every generator in the README's order, plus `07_decisions/supply_plan/build_supply_plan.py`. Then I ran `diff -r` against the original. Every file came out byte for byte the same, `CODE_READS.csv` included (51 rows, 406 fields read on the paths).
- **Independent scan.** I wrote my own AST scanner rather than reuse the builder's. It differs in these ways:
  - it resolves names imported from other modules, both functions and constants;
  - it follows function-local imports, and function references that are passed as values rather than called;
  - it does not exclude the builder's GENERIC list, only true Python built-in method names;
  - it can count every record kind, not only the kinds a row's text names.

  I diffed its results against `CODE_READS.csv` row by row, then against `FIELD_SUPPLY_ROUTES.csv`. I traced every difference to a source line by hand.
- **Probe of the builder's scan.** I loaded `build_code_reads.py`'s own tables. I checked what it does with the M6 context attributes, imported names, local imports and GENERIC names, and which helper functions each M6 path actually reaches.
- **Hand traces.** I traced these rows through the code by hand:
  - credits (row 11), R04B, LAB, DEF and D02;
  - MP01, MP02, MP08 and MP09;
  - comparison (row 46) and buy timing (row 47);
  - R01, R07 and the project-scope gatherers.

---

## 1. GPT's ten points (06_previous/GPT_CHECK_OF_REV4.txt)

| # | GPT's point | Verdict | Evidence |
| --- | --- | --- | --- |
| B1 | credit_note.supplier_ref missing from the credits row and from the routes | **RESOLVED** | `RULE_INPUT_CONTRACTS.csv` row 11 now names "supplier_ref (reconciliation compares it with the supplier_ref of the invoice it names: CREDIT_SUPPLIER_MISMATCH; and the credits' amount_ex_gst_cents with that invoice's: CREDIT_EXCEEDS_INVOICE)". `FIELD_SUPPLY_ROUTES.csv` line 27 holds credit_note.supplier_ref. `CODE_READS.csv` row 11 finds it. This matches `ingest/reconcile.py` lines 195-213. What is left over is minor: see M-1. |
| B2 | project_ref fields of the project-scoped rules; D02's kinds | **RESOLVED** | One shared row, row 5 "every project-scoped detection and M6 rule", names project_ref on 12 kinds. Those are exactly the kinds that `F.of_project` is called on in det/ and mkt/rules.py (rules_cost.py 25, 150, 205; rules_commercial.py 24, 64; rules_ops.py 25, 67, 129, 155, 219, 268; mkt/rules.py 476). `CODE_READS.csv` finds project_ref for R04, R04B, R08, R09, DLY, LAB, DEF and D02. Row 44 names D02's kinds and points to `det/gather.py` PROJECT_DET_KINDS. Each kind's project_ref route lists the shared row. What is left over: the DC-13 wording (S-4) and D02's date fields (S-1). |
| B3 | M6: comparison, buy timing, MP01, MP02, MP08, MP09 | **PARTLY** | Resolved in the contract text:<br>- comparison names issue_date, valid_until and the purchase-order reference fields;<br>- buy timing names the coverage inputs;<br>- MP01 names supplier_quote material_ref;<br>- MP02 names quantity (positive);<br>- MP08 names material_ref and unit_rate_cents.<br>MP09 is partly resolved. It now names the demand, order, delivery and quote fields, and refers to the landed-cost row. It still does not name the inputs of the comparability gate or the international checks that `mkt/opportunity.py` lines 51-56 require: gate class, quote readings and the specification register, unresolved critical import checks. See S-6. |
| B4 | the field report must be regenerated so that it covers every field the code reads | **PARTLY** | It is regenerated and now adds the scan's fields (`build_field_coverage.py` lines 62-65 and 103-106). But the code reads one input field that is in no contract, scan or route: the PM-system copy of the invoice amount (B-1). The scan also has limits, and the documents do not state them (S-1, S-2, S-3). |
| SF1 | R07: issue_date not checked | **RESOLVED** | Row 39's limit: "the quote's issue_date is not checked, so a quote dated after the assessment date can be compared (E30)". CR lines 69 and 113. This matches `det/rules_commercial.py` `_landed`, lines 159-188. |
| SF2 | quote_reading.extractor_kind | **RESOLVED** | Named in row 46. Found in `CODE_READS.csv` row 46. Routed. |
| SF3 | buy timing: market-observation unit_text, source_label_text, geography_text | **RESOLVED** | Row 47 text, `CODE_READS.csv` row 47 and the routes all have them. |
| SF4 | MPD1: project fields | **RESOLVED** | Row 58 names "material_demand project_ref and spec_requirement project_ref". This matches `mkt/rules.py` lines 467-476. |
| SF5 | the severity setting's own route; how settings are grouped | **RESOLVED** | `FIELD_SUPPLY_ROUTES.csv` line 223 is the severity grading row, with its route, its approval treatment ("settled in the Section 18 assessment") and today's state (DC-11). CR line 134 and draft 7 line 145 explain how keys are grouped. What is left over is minor: M-7. |
| SF6 | the DC-1, DC-4 and DC-6 wording in the message list | **RESOLVED** | `NOT_ASSESSED_MESSAGES.csv` lines 569, 572 and 574 now say "any stored variation, whatever that variation's state"; "MP02 still evaluates but loses its last-paid reference"; and "a demand line with no positive quantity". What is left over is minor: M-2 and M-3. |

---

## 2. build_code_reads.py

### 2(a) Reproduction
It reproduces. `python3 -I build_code_reads.py ../04_code_read/apg .`, run in `03_registers/`, gives "rows 51 fields read on the paths 406". The output is byte for byte the same as the pack's `CODE_READS.csv`. The script writes `CODE_READS.csv` to the folder it is run from, so the README's instruction to run it inside `03_registers/` is required, not optional.

### 2(b) Does it really follow the code paths?
- **Call resolution.** It works in practice. With GENERIC replaced by true built-in method names only, my scan gives the same field sets for 49 of the 51 rows. The two rows that differ, 10 and 44, both differ because of imported constants (S-1).

  The GENERIC set does contain pack function names: add, cannot, child, classify, contribute, dispute, exclude, finish, get, limit, read, reason, unknown. These are FigureBuilder methods, Facts.get, Strict.get and SupplierDirectory.add. `cannot` and `classify` are called through module aliases, which the script resolves first. None of them reads a record field. No effect found.

  Function-local imports are not processed: `mkt/rules.py` lines 323 and 369, `det/common.py`, `mkt/fx.py`. Calls through them fall back to resolution by method name, so again no effect found.
- **The M6 context views.** The script handles them correctly. `ctx_attr` maps `quotes` to `common.quote_view` and `pos` to `common.po_view`, built from `mkt/compare.py` `Ctx.__init__` (lines 18-23). It adds them whenever a function on the path reads `.quotes` or `.pos`.

  The weakness is in the contract rows, not this mechanism. Row 46 lists neither `last_paid` nor any other reader of `ctx.pos`. Row 47's coverage is computed by the caller, `mkt/analysis.py` line 39, and passed in. So `po_view`, `last_paid`, `coverage` and `delivery_view` are not on those two paths. My probe confirms this: row 46 has po_view False and last_paid False; row 47 has coverage False and delivery_view False. See S-2.
- **Module constants.** The script handles them only when the constant is defined in the same module, or referenced as `alias.NAME`. A constant imported by name is never resolved. Line 133 checks only `(m, c.id)`, and the `imported` table is not consulted. The probe lists 14 such uses, including `ingest/reconcile.py` line 21 (`SPECS`, `ENTITIES`), `det/rules_ops.py` line 14 (`DET_SPECS`), `mkt/landed.py` line 17 (`COMPONENTS`) and `mkt/intl.py` line 9 (`CHECK_STATUSES`). The docstring's own example (line 11, "for example SPECS") is exactly the case that fails: reconcile imports SPECS. See S-1.
- **Entry-function parsing.** It is correct for every row I checked. A part of the code column with no function names (for example "mkt/fresh.py" in row 48, or "mkt/fx.py" in row 53) adds no entries. The docstring says so, and those modules are reached through calls anyway.

  Five rows name no entry function: rows 13, 14, 19, 22 and 23 (amendments, invoices against orders, variations in revenue, retention events, the bank receipt). Their kinds are therefore checked only against their text. The parent rows (12, 18, 21) do not name those kinds, so the scan never attributes those kinds' reads to any row. See S-3.

### 2(c) Misses, by independent method

**Fields the code path reads that are in no contract, CODE_READS row or route.** I took every field of every register kind whose name appears as a string on any row's path in my scan, and removed those already in `FIELD_SUPPLY_ROUTES.csv`. Then I traced each leftover by hand.
- One is a real input: **pm_invoice.amount_ex_gst_cents** (B-1).
- The rest come from shared strings and are not reads of that kind:
  - payment's fields are read by reconcile only for the payment's own state, and no figure reads payments (`fin/costs.py` line 11);
  - bank_txn.description_text, defect.status_text, material.description_text and project.start_date are other kinds' strings.

**Fields routed, but missing from a row's CODE_READS and from that field's "read by":**
- **D02** reads each kind's event date through `DET_SPECS[kind]['dates']`, `det/rules_ops.py` line 278, with the dates defined in `det/intake.py` lines 13-19:
  - notice.notice_date;
  - delay_event.start_date;
  - plant_hire.on_hire_date;
  - timesheet.work_date;
  - work_output.week_start;
  - defect.raised_date.

  All six are missing from `CODE_READS.csv` row 44, and their "read by" in `FIELD_SUPPLY_ROUTES.csv` does not list D02. For example, notice.notice_date is "R04B instruction without variation" only. See S-1.
- **Row 10:** ap_invoice.invoice_date, which reconcile reads through the SPECS composite (`ingest/specs.py` line 14). It is missing from `CODE_READS.csv` row 10, but the row's text names it.
- **Row 47 (buy timing):** the coverage inputs are missing from `CODE_READS.csv`: delivery delivery_date, qty_delivered, qty_accepted and purchase_order_ref; purchase_order quantity, project_ref, source_status and unit_of_measure; material_demand quantity and project_ref. The text names them (S-2).
- **Row 46 (comparison):** purchase_order unit_rate_cents, unit_of_measure and source_status are missing from `CODE_READS.csv`. The text names them (S-2).

**Rows whose path reads a kind that their text does not name.** The scan counts only kinds a row's text names, so these reads get no code check on that row. The fields are routed through other rows, apart from pm_invoice.

| Row | Kinds read on the path but not named | Where |
| --- | --- | --- |
| 11 credits | ap_invoice (supplier_ref, amount_ex_gst_cents); the supplier list and approved aliases (supplier_id); pm_invoice | `ingest/reconcile.py` lines 81-84, 205-213, 247-267 |
| 8 / 10 actual cost | pm_invoice | `ingest/reconcile.py` lines 247-267 |
| 12 commitments | po_amendment, variation, ap_invoice and credit_note (via invoice_lines) | `fin/commitments.py`; row 13 has no entry function |
| 18 revenue | variation | `fin/revenue.py` line 51; row 19 has no entry function |
| 29 R01 (kinds "-") | budget_line, ap_invoice, credit_note | `det/rules_cost.py` lines 25 and 36-39 |
| 30, 31, 34 (R02, R03, D01) | po_amendment, ap_invoice, credit_note, purchase_order | through M4 commitments and actual cost |
| 48 MP01 | material_demand and spec_requirement (demand materials are watched) | `mkt/analysis.py` lines 62-64 |
| 49 MP02 (only purchase_order named) | supplier_quote, quote_reading, material_demand, spec_requirement, material, the landed kinds, fx_rate, import_check | `mkt/rules.py` lines 131-150; mkt/compare.py |
| 50 MP03 | supplier_quote, quote_reading, the landed kinds, fx_rate, import_check | rankings and scenarios |
| 46 comparison, 47 buy timing | import_check, quote_tier, quote_term (row 46), landed_assumption, fx_rate (and quote_reading in row 47) | `mkt/compare.py` through landed.py and intl.py |
| 56 MP09 | quote_reading, import_check, the landed kinds, fx_rate, material | `mkt/opportunity.py` lines 51-56 |

---

## 3. DC-13

I checked it against `fin/snap.py` (project_of, lines 34-48; Facts.of_project, lines 80-90) and every caller.

- **The rules listed are exactly right.** Every det rule that calls `F.of_project` is listed: R01 (rules_cost.py line 25, and through `fin/forecast.py` budget_by_code, whose fourth "possible" value R01 discards at rules_cost.py line 39), R09 (line 150), AGG (line 205), R04 (rules_commercial.py line 24), R04B (line 64), R08 (rules_ops.py line 25), DLY (line 67), LAB (lines 129 and 155), DEF (line 219) and D02 (line 268). MPD1 is listed too (mkt/rules.py line 476). Each keeps `certain` and drops `possible`. No rule is wrongly listed, and no det rule that calls of_project is missed. R02, R03 and R05 read M4 figures, which list unattributed records. R06 and R07 are tenant rules.
- **One phrase is inaccurate: "is in no project's run".** CR line 89, CR line 105, row 5 and `NOT_ASSESSED_MESSAGES.csv` line 581 all say it. In fact both gatherers pin a record whose project cannot be told into every project's run:
  - `det/gather.py` lines 28-30: `if p is None or p == project: pin(...)`;
  - `mkt/gather.py` lines 46-48 and 58-60.

  The rules then discard the "possible" list. The effect stated, neither assessed nor listed, is correct. The mechanism is not. See S-4.
- **Which case happens today is not stated.** Every stage-1 template marks project_ref as required (`FIELD_REGISTER.csv`, required True on all 19 project_ref rows), and a blank required cell is rejected at mapping (`ingest/mapping.py` lines 272-273). So "no project_ref" cannot arrive today. The live case is a conflict marker whose versions name different projects. That case is held, and D02 or MPD1 are the rules that should list it. The CR's valid_until note (line 91) already treats a parallel case this way.
- **The M6 project rules are outside DC-13's list but behave the same way.** Row 5's text says "these rules use only the records certain to belong (F.of_project)". MP02, MP03, MP04, MP05 and MP09 never call of_project. They match orders and requirements by project_ref equality:
  - `mkt/demand.py` lines 35, 53 and 134 (line 134 explicitly drops `project is None`);
  - `mkt/compare.py` lines 40, 49 and 163.

  A usable order without a project_ref is pinned into every project run (mkt/gather.py line 47) and matched by none, and nothing lists it. This is unreachable through today's templates; held or conflicting orders are DC-10's case. Row 5 should say which rules use of_project and which match by equality. See S-4.

---

## 4. Counts (all recomputed from the files)

| Count | Stated | Recomputed | Match |
| --- | --- | --- | --- |
| Contract rows; distinct rules and figures | 57; 43 | 57; 43 (non-"every" names) | yes |
| Shared rows; groups | six; five | six rows starting "every"; five groups (every M4 figure in rows 2 and 7) | yes |
| Fields; entities | 166; 33 | 166 field rows across 33 kinds and 33 entities | yes |
| Settings rows | 56: N01 29, E90 24, E03 1, E20 1, E04 1 | 56: 29 / 24 / 1 / 1 / 1 | yes |
| Authority split | 6 / 36 / 15 / 109 | 6 / 36 (ap_invoice 8, credit_note 4, po_amendment 3, purchase_order 9, supplier_quote 12) / 15 (budget_line 4, fx_rate 3, market_observation 7, supplier 1) / 109 | yes |
| Fields with D | 20 | 20 (supplier_quote 13, quote_reading 7) | yes |
| Release A text | 160 and 109 | 166 − 6 = 160; 109 | yes |
| Material fields | 33 | 33 | yes |
| Messages | 580: 262 / 188 / 4 / 113 / 13; audience 289 / 98 / 111 / 82 | 580: 262 / 188 / 4 / 113 / 12 silent + 1 uncaught; 289 / 98 / 111 / 82 | yes |
| Defect candidates | DC-1 to DC-13 | DC-1 to DC-13 in the CR table and the message list | yes |
| Rows outside the reference intake | 29 of 57 (draft 7 line 180) | 29 (`RELEASE_A_COVERAGE.csv`) | yes (see M-10) |
| Release A gate rows | N01 29, E90 23, both 9; 47 not fully built; 2 read no records | 29, 23, 9; 47; 2 | yes |
| CODE_READS rows | 51 | 51 | yes |
| Rows with code-only reads | 35 | 35 (`FIELD_COVERAGE.csv` column) | yes |

**Old values.** None of 155, "56 contract rows", 55 settings, 33 / 101, 101, 210, 579 or "19 D" appears in the CR, draft 7, the README or the prompt. Some prose counts are stale: see M-4.

---

## 5. Problems

### BLOCKING

**B-1. The PM-system copy of the invoice amount is read on the actual-cost path, but no contract, CODE_READS row or route names it.**
- `ingest/reconcile.py` lines 247-256 read every `pm_invoice` record as a second observation of the ap_invoice amount (`ingest/specs.py` lines 25-26: `secondary_for=('ap_invoice', 'amount_ex_gst_cents')`).
- A pm_invoice in conflict holds the invoice: `SECONDARY_IN_CONFLICT`, lines 249-251, with no register check.
- Lines 265-267 pass the observation to `resolve_field`. Under the Source Authority Register it then either:
  - is the authoritative value, when the register names the PM source (`source_authority.py` lines 180-185); or
  - quarantines or warns the invoice when it disagrees (`SECONDARY_DISAGREES`, lines 210-214).
- `fin/costs.py` line 15 classes both codes as a disputed exclusion from M4 actual cost.

Rows 10 and 11 name `ingest/reconcile.py reconcile` as their code path, and row 3 names reconcile and resolve_field. None of them names pm_invoice, so the scan never counts it: it counts only kinds the text names. `FIELD_SUPPLY_ROUTES.csv` has no pm_invoice row, although `FIELD_REGISTER.csv` holds the template (TPL-BZ-PM-INVOICES) and `ENTITY_REGISTER.csv` E23 lists "pm_invoice".

This is the same kind of omission GPT classed BLOCKING (small) for credit_note.supplier_ref. GPT's prompt asks it to find exactly this. It also contradicts CR line 20, "every field the current rules read, a way in".

**Fix (small):**
1. Add to row 3 (and to row 8 or 10) the following: "pm_invoice amount_ex_gst_cents, matched to the invoice by its key: a second observation of the invoice amount, the authoritative one when the register names that source. If it disagrees, the invoice is quarantined or warned per the register (SECONDARY_DISAGREES). If it is in conflict, the invoice is held (SECONDARY_IN_CONFLICT). With no invoice, it is held itself (SECONDARY_WITHOUT_PRIMARY)."
2. Regenerate the registers. Expect 167 fields, still in 33 entities, since E23 already exists. Update the counts that move: 166, the authority split, 160, and 33 material.

### SHOULD FIX

**S-1. The scan does not resolve constants imported by name, though three documents say it follows module constants.**
- The claims:
  - `build_code_reads.py` line 11: "a module-level name a function on the path uses (for example SPECS) adds that assignment's string constants";
  - CR line 131: "including ... the module constants they use (for example the intake specifications)";
  - `02_GPT_CHECK_PROMPT.md` line 5: "(including ... the module constants they use)".
- The cause: line 133 checks only the current module, so `from .specs import SPECS` (reconcile.py line 21) and `from .intake import DET_SPECS` (rules_ops.py line 14) are never read.
- The real misses:
  - D02's six event-date fields, from `det/rules_ops.py` line 278 (listed in 2(c)): missing from `CODE_READS.csv` row 44, and D02 is absent from those fields' "read by";
  - ap_invoice.invoice_date in row 10.
- A related gap in the contract: D02 skips a held record whose only hold codes are FUTURE_DATED and whose dates are all after the as-of date, noting `OUTSIDE_PERIOD:` (lines 278-281). Row 44's "if missing" says only "reported as a data-integrity signal".

**Fix (small):**
1. In `strings()`, also add `modconst[imported[m][name]]`.
2. Add the date fields and the OUTSIDE_PERIOD rule to row 44.
3. Regenerate.

**S-2. Rows 46 and 47 name only some of the functions whose output they read, so the scan misses fields their text names. The prompt asks GPT to confirm the scan finds them.**
- Row 47's code is "mkt/scenarios.py build, timing, market_context". Coverage is computed by the caller and passed in (`mkt/analysis.py` line 39: `SC.build(self.ctx, req, self.coverage(req))`). So `CODE_READS.csv` row 47 has no delivery quantity or date and no purchase_order quantity, status or unit.
- Row 46 has no reader of `ctx.pos` (`last_paid`, `mkt/compare.py` line 157), so purchase_order unit_rate_cents, unit_of_measure and source_status are absent.
- The routes are not affected, because the text names these fields. But `02_GPT_CHECK_PROMPT.md` line 21 asks "does build_code_reads.py find ... the coverage inputs of buy timing". GPT will find that it does not.

**Fix (small):** add `mkt/demand.py coverage` to row 47's code and `mkt/compare.py last_paid` to row 46's, then regenerate. Alternatively, reword the prompt.

**S-3. The texts describe the scan as more than it is.**
- What the scan actually does:
  - it counts only kinds a row's text names (`build_code_reads.py` line 168);
  - it does not scan the five rows with no entry function (13, 14, 19, 22, 23);
  - it misses imported constants (S-1);
  - it starts only from the functions a row names (S-2).

  So it is over-inclusive where it reaches, but it is **not** an upper bound of what a row reads. The table in 2(c) lists the rows whose path reads unnamed kinds.
- The claims:
  - CR line 13: "Every field the contracts name, and every field the code path of each rule and figure reads (found by scanning the code ...)";
  - CR line 20: "every field the current rules read, a way in" (untrue while B-1 stands);
  - CR line 131: "follows the path from the entry functions through every function they call ... It is an upper bound";
  - draft 7 line 142: "(an upper bound ...)";
  - prompt line 5: "The root cause you named is fixed at its source" and "through every function it calls".
- The caveat in CR line 150 ("a field reached in a way it does not follow ... would still be missed") is good, but it omits the named-kinds limit and the five unscanned rows.

**Fix (small):**
1. Replace "upper bound" with "over-inclusive where it reaches".
2. Add to CR line 150, draft 7 line 147 and the prompt: "it counts only the record kinds a row's text names, and does not scan rows that name no entry function".
3. Soften "fixed at its source" to "addressed: the report now also uses a scan of the code".

**S-4. DC-13 and row 5 describe the mechanism wrongly and leave out the M6 project rules.**
- **Wrong mechanism.** CR lines 89 and 105, row 5 and `NOT_ASSESSED_MESSAGES.csv` line 581 say the record "is in no project's run". In fact it is pinned into every project's run (`det/gather.py` lines 28-30; `mkt/gather.py` lines 46-48 and 58-60), and these rules then drop it as "possible".
- **Reachable case not stated.** The case that happens today is a conflict whose versions name different projects; a missing project_ref is rejected at mapping by every stage-1 template.
- **M6 rules left out.** Row 5 says "these rules use only the records certain to belong (F.of_project)". MP02 to MP05 and MP09 match by project_ref equality instead (mkt/demand.py lines 35, 53 and 134; mkt/compare.py lines 40, 49 and 163). They have the same unlisted effect for a project-unknown order, which is unreachable today.

**Fix (small):**
- Use this wording: "is pinned into every project's run, but these rules use only the records certain to belong (F.of_project) and drop the rest unlisted. Today that is a record whose versions name different projects; a blank project_ref is rejected by every stage-1 template."
- In row 5, name the eleven of_project rules, and add: "the M6 project rules match by project_ref (mkt/demand.py, mkt/compare.py); an order with no project_ref would be matched by none".

**S-5. The CR says the owner decided all thirteen candidates; his record says DC-13 is pending.**
CR line 73 reads: "exposed thirteen behaviours ... The owner decided on 2026-11-12 (...) that all of them are fixed after stage 1 (DC-12, found later, he decided the same day)". `07_decisions/OWNER_DECISIONS_2026-11-12.md` item 12 says DC-13 is "put to the owner, pending his word". The same paragraph's parenthesis, "(put to the owner)", contradicts the sentence. Elsewhere the CR states this correctly (lines 5, 17, 89 and 274), as does draft 7 (lines 172 and 282).

**Fix:** "that DC-1 to DC-12 are fixed after stage 1 ...; DC-13 is put to him."

**S-6. The MP09 row still does not name the ranking inputs that GPT's MP09 point named.**
`mkt/opportunity.py` lines 51-56 raise an opportunity only when all of these hold:
- the quote's gate class is DEFINITIVE_OK, which depends on the quote readings' verification and the specification register (row 46's inputs);
- qualification is "current";
- the landed cost is complete;
- `o['international']['unresolved_critical']` is false (import checks, MP07's inputs);
- and the reference's gate class passes.

Row 56 points to the landed-cost row, but not to these. GPT's point was "through coverage, ranking and last-paid calculations". The fields are routed through rows 46 and 54, so this is wording.

**Fix (small):** add "the comparability gate's inputs, as in the M6 comparison row (quote_reading ..., the specification register), and the import checks, as in MP07 (import_check ...)". MP02's row (49), which names only purchase_order, would benefit from the same cross-reference.

### MINOR

- **M-1. Credits row 11 omits when the supplier check runs.**
  - CREDIT_SUPPLIER_MISMATCH is checked only when both the credit's and the invoice's suppliers resolve to supplier ids against the supplier list or approved aliases (`ingest/reconcile.py` lines 154-163 and 205-207). With no list and `supplier_master_required` off, it is never checked (SUPPLIER_NOT_CHECKED).
  - The row does not say this. Its route row (`FIELD_SUPPLY_ROUTES.csv` line 27) does not name resolution against E20 either, although GPT asked for "its supplier-resolution/verification route".
  - Fix: add "(both suppliers resolved against the supplier list, E20)".
- **M-2. The DC-4 message row is less precise than the CR.** `NOT_ASSESSED_MESSAGES.csv` line 572 says "drops one unstated when the GST rate is not set". The code drops it only when the tax treatments differ too (`mkt/opportunity.py` lines 27-31), as CR line 80 says. Align the row.
- **M-3. DC-6's ambiguity remains in two places.** CR line 82 and row 46 still say "a demand line or specification requirement that is not usable ...; one with no positive quantity ...". GPT's DC-6 point is fixed in the message list, but "one" still reads as including standing requirements. Use "a demand line with no positive quantity".
- **M-4. Some prose counts are stale:**
  - CR line 5, "all four reports are in AUDIT.txt", while the README and prompt line 15 describe a further check. AUDIT.txt currently ends with the fourth-check fixes, so this report and its fix list must be appended before sending.
  - CR line 73, "the two agent checks of this revision": three checks gave defect candidates.
  - CR line 268, "one change request for DC-1 to DC-12": add "and DC-13 if he agrees", as line 274 does.
  - CR line 308, "the three reports".
  - Draft 7 line 11, "Two agent checks of revision 4".
- **M-5. "A row for every project-scoped rule" is misleading.** `02_GPT_CHECK_PROMPT.md` lines 10-11 say "a row for every project-scoped rule" and "a new row for every project-scoped detection and M6 rule". It is one shared row, row 5. Say so, so that GPT does not look for eleven rows.
- **M-6. CR line 105 mentions kinds no detection or M6 rule scopes.** It says "(credit notes and order amendments through the record they link to)", but no detection or M6 rule scopes credit notes or amendments. Only M4 does, in row 7.
- **M-7. Settings rows split by entity repeat the other entity's keys.** For example, R03's "po_status_map; tolerance_bps" appears both as an E90 row and as an N01 row; the same happens for R04 and MP02 to MP10. Each row then carries a key of the other entity. Consider splitting the keys by entity.
- **M-8. build_code_reads.py docstring wording.** Line 5 says "apg/snap-style helpers", but no such module exists (snap is `fin/snap.py`); the module list is fin, det, mkt and ingest plus the three root files. The GENERIC list and function-local imports have no effect today (2(b)). A comment saying so would pre-empt a reviewer's question.
- **M-9. retention_event.project_ref is read but not listed.** It is read at `fin/cash_states.py` line 101 to select a project's events, but row 22's retention-event field list does not include it. That list is the one draft 7 says release A must cover.
- **M-10. The N01 flag in RELEASE_A_COVERAGE.csv comes from the configuration column.** So D02, MPD1 and row 5 show "-", though D02 and MPD1 run only under a pinned detection or procurement policy. They also show "-" for "not through the S04 reference intake", because their entity is "-". Draft 7 line 181 describes the rule as "a detection or M6 rule needs N01". The counts match the file; the description does not match the generator.
- **M-11. The CR has no table for GPT's ten revision-4 points.** It maps GPT's check of revision 3 point by point (line 287), but not GPT's ten points on revision 4. A short table would let GPT check the ten points quickly. Optional.

---

## 6. 02_GPT_CHECK_PROMPT.md

- **Run order.** It is accurate and matches the README; I reproduced every generator from it. It abbreviates the later commands ("`build_entities.py`" for `python3 -I build_entities.py .`), which is acceptable. It does not mention `07_decisions/supply_plan/build_supply_plan.py`. The README does, and that file reproduces too.
- **Scope and rules.** These are accurate and good: one pass, the ten points, over-inclusion is not a defect, and "not verifiable from the pack".
- **What is inaccurate:**
  - line 5 overclaims (S-3);
  - question 3 invites a check the scan fails on buy timing (S-2);
  - lines 10-11 suggest per-rule rows (M-5);
  - line 15 describes an AUDIT.txt ending that is not there yet (M-4).
- **Authorisation.** Nothing implies a build is authorised. The prompt, CR lines 7 and 272, draft 7 line 7 and the owner record keep "no build" throughout.

---

## 7. Owner's decisions

- They are stated as recorded everywhere except CR line 73 (S-5). DC-13 is described as pending in CR lines 5, 17, 89 and 274, draft 7 lines 172 and 282, and `NOT_ASSESSED_MESSAGES.csv` line 581.
- The severity setup (dollar, percentage or both, whichever is reached first, no suggested levels), the extras panel and verified-first figures all match the owner's record items 5, 7, 9 and 11.

---

## 8. What I could not verify from the pack

- The pack does not include `apg/canon.py`, `apg/values.py`, `apg/repro.py` or `apg/ports*.py`. I assumed `canon.deep_copy` and `pin_latest` do not read record fields.
- Whether a real builder's export marks project_ref, valid_until or the work-package reference as optional. The stage-1 templates are synthetic.

---

**Totals: BLOCKING 1 (small), SHOULD FIX 6 (all small), MINOR 11.**
