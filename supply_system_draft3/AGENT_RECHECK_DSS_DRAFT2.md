# INDEPENDENT READ-ONLY (agent) re-check: APG Data Supply System, draft 2

Auditor: a fresh Claude agent, read-only. I edited, moved and created no file except this report. I used only the synthetic material in `recheck_in/` and no network. One pass, scoped as asked.

"Line N" means a line of `DRAFT2_EXPORT.md`.

## How I verified

- **Generator.** I copied `build_supply_plan.py` and `rev3/` to a temporary scratch folder, which I deleted afterwards, and ran `python3 -I build_supply_plan.py rev3` there, so the pack stayed untouched. Both regenerated CSVs are byte-identical to the shipped ones (`diff` clean). SHA-256: SUPPLY_PLAN `7f9d1f61…`, RELEASE_A_COVERAGE `be4c0d88…`.
- **Numbers.** I recomputed every count from `ENTITY_REGISTER.csv`, `RULE_INPUT_CONTRACTS.csv` and the regenerated CSVs with my own code.
- **Claims.** I read the three milestone intakes, `specs.py`, `reconcile.py`, `entities.py`, `filestore.py`, `mapping.py`, `documents.py`, `freshness.py`, `jobs.py`, `source_authority.py` and `cash_states.py`. I grepped every rule and figure for how it reads records (`usable(p)` against `F.recon`). I read S04, S06, S10, Section 18 §6 and §8, 8-layer §11, and the rev3 export.

---

## 1. The 37 draft-1 findings

| # | Class | Status | Evidence |
| --- | --- | --- | --- |
| 1 | BLOCKING | RESOLVED | Lines 27–31 now give 11 reference kinds (matches `specs.SPECS`), 24 milestone kinds (FIN_SPECS 8 + DET_SPECS 7 + MKT_SPECS 9 = 24) and two direct writers. "First job" is line 33, AC-03 is reworded and the plan has an "intake today" column. A new residual claim in release A item 1 is raised as N1. |
| 2 | BLOCKING | RESOLVED | `ids()` expands ranges (script lines 24–28). B is now 22 and includes E48, E49, E69, E70 and E71. |
| 3 | BLOCKING | RESOLVED | E26–E37 are in A with the M6 reason. Release A item 5 writes the M6 contracts. Line 137 states that M6 has no readiness record yet. |
| 4 | BLOCKING | RESOLVED | E20 is in A ("needed by the intake…"). Line 118 states it. |
| 5 | BLOCKING | PARTLY | N01 is added (setup, release A) and flagged for rev3 (line 241). Not done: the audit's "map the named policy fields to E90 explicitly". The coverage CSV says only "yes (N01 or E90)", and line 160 now misstates the 27 (see N2). |
| 6 | BLOCKING | RESOLVED | Rule 3 is reworded (line 21). Line 119 says release B changes nothing until the rule changes. E15 is in B. The scope line (13) is updated. |
| 7 | SHOULD FIX | RESOLVED | The circular check is replaced by RELEASE_A_COVERAGE.csv. Line 157 says membership holds by construction and is not evidence. The report's own counts have problems (N2, N3). |
| 8 | SHOULD FIX | RESOLVED | Script lines 73–76 apply the new rule. E77, E68, E71, E88 and E97 now take the entry screen. Release A item 4 is in place. Line 86 names the person-recorded entities. One residual wording point is N15. |
| 9 | SHOULD FIX | RESOLVED | E05 is in A, with the Anchor platform caveat (line 118 and item 3). |
| 10 | SHOULD FIX | PARTLY | Each way in now says what "partly" means, and "CSV only" is stated. But E16 is still counted among the "built or partly built" minimums (line 126), although no subcontract kind exists. Line 131's definition of "built" ("the stage 1 code accepts the data on synthetic files") is false for E16, E83 and E90. See N26. |
| 11 | SHOULD FIX | RESOLVED | Line 176 includes real extraction, E83, E35 and EDR-22. Plan follow-through is N16. |
| 12 | SHOULD FIX | RESOLVED | Lines 7 and 227 quote S04 §20 accurately (S04 line 170). |
| 13 | SHOULD FIX | RESOLVED | Line 37 adds the authentication row, line 38 file handling, and lines 69 and 92–93 add sender verification, phone enrolment, server time and S09 §14. Offline phone capture is still not discussed (N25, optional). |
| 14 | SHOULD FIX | RESOLVED | Line 77 and AC-08. |
| 15 | SHOULD FIX | RESOLVED | Line 64 gives the five S04 §8 outcomes. |
| 16 | SHOULD FIX | RESOLVED | AC-01, AC-02 and AC-03 are worded as the audit proposed. |
| 17 | SHOULD FIX | RESOLVED | AC-05 to AC-10 are added. AC-10 is narrower than S06 §9.1 (N17). |
| 18 | SHOULD FIX | RESOLVED | Line 150 shows the factors side by side and says "amount affected". Line 151 adds dedupe and suppression. |
| 19 | SHOULD FIX | RESOLVED | Line 230 asks for approval "in principle" and quotes S18 §6 accurately. Line 239 lists the cascade scope (additions in N22). |
| 20 | SHOULD FIX | RESOLVED | Line 96 states the change from rev3 decision 3. Decision 4 covers phone capture. |
| 21 | SHOULD FIX | PARTLY | The phases are renamed to releases. The added mapping line, "all releases sit inside Section 18's phases 1 to 3", is not accurate (N7). |
| 22 | SHOULD FIX | RESOLVED | "Designed", "will" and "a designed label" are used, and freshness says "you set (revision 3 proposes values)". |
| 23 | MINOR | RESOLVED | "The synthetic templates for 33 entities" (line 167). |
| 24 | MINOR | PARTLY | Paths are still mixed: `apg/fin/intake.py` and `apg/ingest` sit beside `fin/cash_states.py`, `source_authority.py` and `ingest/pipeline.py`. There is no mapping to the pack folders, so a reviewer cannot find `apg/fin/intake.py`; it is `milestone_intakes/fin_intake.py` (N19). |
| 25 | MINOR | RESOLVED | Line 11. SYSTEMS_SURVEY.csv has 18 rows: 16 systems plus BANK and EXT. |
| 26 | MINOR | RESOLVED | Line 102. |
| 27 | MINOR | RESOLVED | Line 150 cites S06 §4 and §7 with PG-AI-AC-06. S06 §2 is the more direct source, and PG-AI-AC-06 sits in §15, not §7 (N25). |
| 28 | MINOR | RESOLVED | Line 53 describes the diagram in words, with derived records after the rules. The diagram itself is still only a placeholder in the export. |
| 29 | MINOR | RESOLVED | Line 113. |
| 30 | MINOR | RESOLVED | The reference to GPT is gone from the architecture. |
| 31 | MINOR | RESOLVED | Line 100. |
| 32 | MINOR | RESOLVED | Line 149. |
| 33 | MINOR | RESOLVED | Lines 44, 70 and 71. `verify_field` and `observation()` treat only whole numbers as verified Known values; dates go only through `verified_text`. |
| 34 | MINOR | RESOLVED | Line 167 (`mapping.py` line 95). |
| 35 | OPTIONAL | RESOLVED | Line 137. |
| 36 | OPTIONAL | RESOLVED | Line 49. |
| 37 | OPTIONAL | RESOLVED | Regenerated. My run is byte-identical. The failing-register test was declined with a reason (no pass/fail check remains). |

**Tally:** 33 RESOLVED, 4 PARTLY (5, 10, 21, 24), 0 NOT RESOLVED. The remaining work on the PARTLY ones is in N2, N26, N7 and N19.

---

## 2. Numbers recomputed

| Draft statement (line) | Recomputed | Result |
| --- | --- | --- |
| Releases 42 / 22 / 31 / 5 = 100 (123–129) | 42 / 22 / 31 / 5 | OK |
| A: 35 built or partly = 33 T exists + E01 A partly + E90 S partly; 7 not = 5 S (E02, E03, E04, E05, N01) + E77 E + E89 A | same | OK |
| B: 2 = 1 T exists (E79) + 1 D partly (E16); 20 = 13 T + 6 E + 1 S | same | OK |
| Later: 10 = 3 T (E11, E25, E54) + 6 A (E84 exists; E44, E45, E46, E62, E96 partly) + 1 D (E83); 21 = 8 T + 6 E + 4 S + 3 A | same | OK |
| Optional: 5 T proposed | same | OK |
| Total 47 / 53 (20, 108, 129) | 47 / 53 | OK |
| Templates 37 / 29 (61) | 37 / 29 | OK |
| Document capture 17 / 6 (67) | 17 partly / 6 | OK |
| Entry screens 47, none built (73) | 47 | OK |
| **Setup questions "13 entities, counting the detection-rule settings this draft adds; 1 partly built" (79)** | **register 13 (1 partly, 12 proposed) + N01 = 14** | **MISMATCH (N9)** |
| APG derives 8 / 9 (86) | 1 exists + 7 partly / 9 | OK |
| Phone capture 14, and each also has a Level 1 way in (90, 94) | 14, each with E or T | OK |
| Integrations 24 (100) | 24 | OK |
| 33 templates (167) | 33 A entities with T exists | OK |
| Release A intake 9 / 24 / 2 / 7 (131) | 9 reference (E20–E24, E30, E36, E37, E38); 24 milestone; 2 direct (E03, E77); 5 "no record kind today" + E01 (fields) + E90 (policy object) = 7 | Sum OK. The label is wrong: the column shows "no record kind today" for only 5 (N13). |
| Coverage 23 rows not through the reference intake (159) | 23 | Count OK; wording (N3) |
| **Coverage 27 rows "need detection or policy settings that no register entity held before N01" (160)** | **27 rows have settings without an E-id, but only 13 need detection-rule settings (R01, R03, R09, AGG, R04, R04B, R05–R08, DLY, LAB, DEF). 14 name only financial-policy fields, which E90 holds (register: "variation_status_map, po_status_map, cost_scope, ctc_method and others").** | **Count OK, meaning wrong (N2)** |
| **Coverage 5 rows with a minimum way in not fully built: "the cost-code map, the authority register, the financial policy, retention events" (161)** | **The 5 rows are E90, E04, E03, E77 and E15. Four names are given for five rows, and E15 (receivables) is release B. Counting N01 (proposed) and E90 (partly) settings, 32 of 39 rows depend on an input whose way in is not fully built.** | **MISMATCH (N3)** |
| Coverage: 2 figures read no records (162) | security carrying cost, overdue receivables | OK |
| 14 of B's 22 are templates, 13 still to build (184) | 1 exists + 13 proposed | OK |
| Seven only by file: E21, E24, E57, E73, E29, E36, E37 (178) | same | OK |
| B's listed contents (184) | E13, E14, E15, E16, E39, E42, E43, E47–E51, E63, E68–E72, E76, E79, E80, E81 = 22, all named | OK |
| 99 entities, 39 rows, 16 systems + 2 sources (11) | same | OK |

---

## 3. New and changed claims checked against code and blueprint

- **Milestone intakes (line 30).**
  - 24 kinds is correct.
  - "Cross-record checks inside the calculations" matches the `fin_intake.py` docstring (lines 8–9).
  - The loop mirrors `pipeline.ingest_file` and reuses `mapping.apply_template` and `pipeline.decide`, so "copy" is close enough.
  - **F-16:** the code records F-16 as *closed*. `ingest_fin_file` docstring says "M5 passes its own, closing finding F-16"; `det_intake.py` says "closes M4 finding F-16". The M3 loop and the fin loop are still two. The draft presents the merge as already logged under F-16 (N12).
- **Reference intake "with the full Section 04 treatment" (line 29).** This overclaims. The same table shows resolution for suppliers only (S04 §11 lists projects, contracts and more), no freshness thresholds and CSV only. The figures themselves exclude `PROJECT_UNKNOWN_OR_AMBIGUOUS` records (N11).
- **File handling (line 38).** `filestore.ingest_stored_file` calls only `pipeline.ingest_file` (lines 124–127), so the scan gate covers the 11 reference kinds only. The det and mkt intakes read files with plain `open(p,'rb')` (N11).
- **"Two records are written straight to the store" (line 31).** `documents.register_extraction` also writes `extracted_document` with `scoped.put`, outside the intake. That is a third supplied fact written directly, in conflict with AC-01 (N11).
- **EDR-22.** Matches the `documents.py` docstring.
- **S04 citations.**
  - §3, §4, §5, §6, §7, §8, §9, §10, §11, §12, §13, §14, §15, §16, §17, §18 and §20 are all cited for content they contain.
  - §6's rule on payload-supplied tenant identifiers supports "never taken from the address alone".
- **S06 citations.**
  - §4: correct.
  - §7: see #27.
  - §9.1: correct, but AC-10 covers only dedupe, not the suppression window, re-notification and tests (N17).
  - §10: supports the reassessment triggers.
- **S10 §4.** The five factors are in its list. Correct.
- **S18 §6.** Quoted accurately.
- **S18 §8 phases.** See N7.
- **8-layer §11.6.** The draft's list drops "caller" and "unavailable-data behaviour" (N25, optional).
- **S09 §14.** Only rev3 line 169 cites it ("labour data privacy and role permissions"). The draft's paraphrase, "capture only what the record needs, and only for its purpose", cannot be checked from the pack (N20).
- **AC-01 to AC-11.**
  - Consistent with S04 §19 and S06.
  - AC-01 is contradicted today by three direct writers, not two (N11).
  - AC-06 (PG-DI-AC-07) is contradicted by the E35 template path counted as built (N4).
- **N01.** It is correct that no register entity holds rule parameters: E90's field groups have no thresholds, and every rule calls `C.start(F, dp, …)` and returns nothing when unconfigured. The 27-row claim around it is wrong (N2). Who sets N01 values is not stated (N23).
- **"Releases sit inside Section 18's phases 1 to 3" (line 116).** Inaccurate (N7).
- **"This changes the intake code, not any rule or figure" (line 166).** Not supported by the code (N1).

---

## 4. New problems

### N1. SHOULD FIX: release A item 1 says bringing the 24 milestone kinds under the S04 intake "changes the intake code, not any rule or figure". The code says otherwise.

**What is wrong.**
- The rules and figures read the 11 reference kinds through `F.recon(...)`, the reconciliation state (`costs.py` 57, `commitments.py` 45 and 50, `forecast.py` 27, `rules_cost.py` 185, `rules_commercial.py` 166).
- They read every milestone kind through `usable(p)`, imported from `fin.intake`. That is the intrinsic outcome only (`rules_ops.py` 30/71/134/158/223, `rules_commercial.py` 29/69/139, `cashview.py` 39/45/84/112, `rules_cost.py` 154).
- New S04 reconciliation of those kinds therefore has no effect unless either:
  - the rule and figure files change to read `F.recon`, or
  - `usable()` changes meaning. Then records used today become held, and rule and figure test results change.
- The calculations' own cross-record checks (fin docstring; `PROJECT_UNKNOWN_OR_AMBIGUOUS` in `revenue.py`, `cashview.py`, `forecast.py` and `commitments.py`) would also overlap the new reconciliation, or be removed, which is a figure change.

**Fix.**
- State that item 1 changes which records the rules and figures may use. Say that it is done under its own change request, with the rule and figure tests re-baselined and the differences explained, and that the rules then read the reconciled state as they already do for the 11 kinds.
- Say that AC-03 governs new ways in, not this migration.

### N2. SHOULD FIX: the 27 coverage rows are mis-described (residual of #5).

**What is wrong.**
- Line 160 says these rows need settings "that no register entity held before N01".
- Only 13 rows need detection-rule settings (N01).
- The other 14 (every M4 figure row with a policy field, plus R02) name only financial-policy fields that E90 holds. The draft's own line 83 says so.

**Fix.**
- Split the column into "N01" and "E90 field" and regenerate.
- State 13 and 14.
- This also completes #5's "map the policy fields to E90".

### N3. SHOULD FIX: "5 rows depend on an input whose minimum way in is not fully built" understates the gap.

**What is wrong.**
- The gap column ignores the settings themselves. N01 is proposed and E90 is only partly built.
- Counting them, 32 of the 39 rows depend on a way in that is not fully built. In plain terms, every M4 figure (through E90) and every detection rule (through N01).
- The draft lists four names for five rows. The fifth, E15, is a release B entity sitting in a "release A" report.
- "23 rows read an input" also counts settings and the two rows that read no records.

**Fix.**
- Include the N01 and E90 gaps in the gap column and regenerate.
- Restate the count as 32 of 39, in plain words.
- Mark the E15 row as release B.
- Say "name an input (record or setting)".

### N4. SHOULD FIX: E35 quote readings are counted as a built release A minimum through a synthetic template, which bypasses human verification.

**What is wrong.**
- `MKT_INTAKE_POLICY` makes `verified_by` and `verified_on` warn-only for `quote_reading` (`mkt_intake.py` line 266).
- So a file can assert verification, or omit it, and the record is still usable. That is outside the `documents.py` verifier control.
- This conflicts with S04 §12 and PG-DI-AC-07, so with the draft's own AC-06.
- The same pattern (approver or checker columns optional) applies to E27 `approved_by`, E33 `set_by` and E34 `checked_by`.

**Fix.**
- State that the E35 template path cannot satisfy S04 §12.
- Either make document capture (partly) the minimum for E35, or require the verification fields as material and tie them to a `documents.py` verification.
- Note that the approval columns of E27, E33 and E34 are asserted, not governed.

### N5. SHOULD FIX: six of the "33 templates checked against one real builder's files" have no real builder file.

**What is wrong.**
- E27, E31, E32, E33, E34 and E35 are the M6 "synthetic supplement" templates. `mkt_intake.py` lines 240–242 say they were written "because no Builder Zero file carries them".
- Release A item 2 cannot check them against real exports.
- In the minimum release (no entry screen, no document capture), the M6 inputs depend on builders filling synthetic-layout spreadsheets by hand.

**Fix.**
- Say this in item 2 and under "Not proven".
- Note that these six depend on the recommended entry screen and document capture (decision 2).

### N6. SHOULD FIX: APG outputs of current rules are placed in "later" with the reason "input to an insight not built yet".

**What is wrong.**
- E84 Finding is "covered: apg/det/findings.py", the output of today's rules.
- E45 Assessment (the calculation run), E44, E96 and E62 are partly built by current code.
- Release A depends on some of them:
  - the readiness record E89 links to E84;
  - AC-01 and line 86 require derived records to be "recorded with their calculation run" (E45);
  - nudges follow S06 §9.1 "for alerts" (E85, later).
- "Settled after builder discovery" (line 120) does not apply to these.

**Fix.**
- Place E45 and E84 (and E85, if a nudge is an alert) in release A as the readiness record's dependencies, or give APG outputs their own bucket with a correct reason.
- Regenerate.

### N7. SHOULD FIX: "all releases sit inside Section 18's phases 1 to 3" (residual of #21).

**What is wrong.**
- S18 §8 is one sequence for the whole build: Phase 0 discovery and baseline, then phases 1 (control foundations), 2 (financial core) and 3 (domain intelligence).
- Release A spans all three: intake, authority and identity in 1; the financial policy in 2; readiness and nudges in 3.
- Every release also needs Phase 0 before it and phases 5 and 6 (security, acceptance) before any production use.
- A non-technical reader could take the line to mean that release A ships before phases 4 to 6.

**Fix.** Give the mapping per release, with Phase 0 and the Discovery Exit Report before, and phases 4 to 6 evidence before production.

### N8. SHOULD FIX: the minimum release's retention entry form conflicts with "one general entry feature, not 47 screens".

**What is wrong.**
- Line 75 says forms are generated from field definitions and depend on the schema register, which is not built.
- Minimum item 4 builds one retention entry form, and item 3 needs setup forms.
- Either these are the first use of the general entry feature, so the schema register falls into the minimum, or they are one-off screens, which the draft says it avoids.
- This changes what decision 2 is choosing between.

**Fix.** State which one, and adjust decision 2's two options.

### N9. MINOR: the setup question count is wrong.

Line 79 says "13 entities, counting the detection-rule settings". It is 14 (13 in the register plus N01), or 13 without N01. Correct it.

### N10. SHOULD FIX: "A rule whose input has no built way in will be shown as qualified" (line 153) contradicts the gate-based state in line 141.

**What is wrong.**
- Inputs the contracts mark as needed to "run" (E03, E90, N01) block or stop the insight. They do not qualify it.
- So the sentence would show a blocked insight as qualified, which goes beyond its evidence.
- The R04B example is also about capture completeness: E10 already has a built template.

**Fix.** Say "shown at the state its gate gives: qualified where the input only qualifies it, blocked or unavailable where it is needed to run; never eligible". Keep R04B as an example of incomplete capture.

### N11. MINOR: the architecture overstates the reference intake and undercounts direct writes.

**What is wrong.**
- "Full Section 04 treatment" (line 29) is an overclaim.
- The scan-gated path covers the 11 reference kinds only.
- `documents.py` writes `extracted_document` directly, a third direct writer.

**Fix.** Drop "full". Say the scan gate covers the reference intake only. Name the third writer under AC-01 and release A item 1.

### N12. MINOR: F-16 is described as still logged when the code records it as closed.

**What is wrong.** The code records F-16 as closed, because det and mkt reuse the fin loop instead of copying it. The M3 and fin loops are still separate, and no open item tracks merging them.

**Fix.** Say so, and make the merge new work this amendment adds.

### N13. MINOR: the "7 have no stored record kind" label does not match the column.

**What is wrong.** "7 have no stored record kind yet (the plan's 'intake today' column)". The column says that for only 5. E01 is "fields on stored records" and E90 is "a policy object".

**Fix.** Say "5 have no record kind, plus the provenance fields and the policy object".

### N14. MINOR: the release placement is not wholly mechanical from the contracts.

**What is wrong.** Line 116 says "Mechanical, from revision 3's input contracts". But the M6, INTAKE_NEEDS and FOUNDATION sets are hand-listed (script lines 34–37).

**Fix.** Say "from the contracts plus four named lists".

### N15. MINOR: the definition of "partly" for APG-derived records is wrong for two entities.

**What is wrong.** Line 86 says "Partly means the code computes it but does not store it as its own record". That is wrong for E77, which `record_event` stores as `retention_event`, and for E01, which is fields on records.

**Fix.** Define "partly" per entity, or exclude these two.

### N16. MINOR: the plan does not reflect the recommended option's need for E83.

**What is wrong.** The recommended option needs E83 Document (line 176), but the plan keeps E83 in "later".

**Fix.** Note that choosing option 2 moves E83 (and the entry screens) into release A.

### N17. MINOR: AC-10 covers dedupe only.

**What is wrong.** S06 §9.1 also requires a dedupe identity, a suppression window and re-notification rules, all tested.

**Fix.** Widen AC-10 to match.

### N18. MINOR: line 9's claim overstates the fixes.

**What is wrong.** Line 9 says "Draft 2 fixes all 37 findings", while 4 are only partly resolved.

**Fix.** Change it once the residuals are fixed.

### N19. MINOR: the path convention is mixed (residual of #24).

**What is wrong.** Some paths carry the `apg/` prefix and some do not, and there is no mapping to the pack folders. For example, `apg/fin/intake.py` is `milestone_intakes/fin_intake.py`, and `apg/source_authority.py` is in `stage1_ingest_code/`.

**Fix.** Use one convention and add a one-line path map.

### N20. MINOR: the S09 §14 content cannot be checked.

**What is wrong.** The paraphrase in line 93 is not in the pack.

**Fix.** Cite it as "S09 §14 (labour data privacy and role permissions, per revision 3)" and leave the detail to the cascade assessment.

### N21. MINOR: two wording points will confuse an owner.

**What is wrong.**
- Line 57 counts "six ways to supply data … plus the records APG derives", yet line 112 counts APG-derived records as a Level 1 way in.
- The phone list (line 90) names "crews", but E56 Crew has no phone path; E58 work allocation does.

**Fix.** Use one count, and replace "crews" with "work allocation".

### N22. OPTIONAL: the cascade scope could name more sections.

**What is missing.** The cascade scope (line 239) could add:
- S05 (financial policy and status maps, E90);
- S07 and S13 (the release B programme and quality entities);
- S01 (E05 possibly from the platform).

### N23. OPTIONAL: N01 governance is not stated.

**What is missing.** S06 §5.1 requires thresholds "configurable within approved governance boundaries".

**Fix.** Say whether the product owner sets bounds or defaults and the builder sets values within them, and which role approves.

### N24. MINOR: line 157 overstates coverage for M6.

**What is wrong.** "Every current rule and figure … every input it reads" includes M6, but M6's inputs are inferred from the record kinds the mkt intake ingests, not from contracts.

**Fix.** Qualify it until the M6 contracts are written.

### N25. OPTIONAL: citation precision and one gap.

- §11.6's list omits "caller" and "unavailable-data behaviour".
- S06 §2 is the direct source for traceable amounts.
- Offline phone capture is still not addressed.

### N26. MINOR: E16 and the definition of "built" (residual of #10).

**What is wrong.** E16 is counted as a built or partly built minimum, but no subcontract record kind exists.

**Fix.** Either move E16 to "not built" (B becomes 1 / 21; the total becomes 46 / 54), or footnote it in the table. Also qualify line 131's definition of "built" for E16, E83 and E90.

---

## Totals

**Draft-1 findings (37):**

| Status | Count | Findings |
| --- | --- | --- |
| RESOLVED | 33 | all others |
| PARTLY | 4 | 5, 10, 21, 24 |
| NOT RESOLVED | 0 | |

**New problems (26):**

| Class | Count | Findings |
| --- | --- | --- |
| BLOCKING | 0 | |
| SHOULD FIX | 9 | N1, N2, N3, N4, N5, N6, N7, N8, N10 |
| MINOR | 14 | N9, N11–N21, N24, N26 |
| OPTIONAL | 3 | N22, N23, N25 |
| **Total** | **26** | |

**Number mismatches:** 2 hard mismatches (setup 13 vs 14, N9; the coverage "5 rows" list, N3), and 2 mislabelled counts (the 27 rows, N2; the "7 no record kind", N13). Every other stated number recomputes exactly, and the CSVs regenerate byte-identical.

## Verdict

Draft 2 is a real improvement. All six blocking findings are dealt with, the arithmetic matches the generator exactly, the CSVs regenerate byte for byte, and the stage 1 position is now stated honestly. Nothing new is blocking.

It is not quite ready for GPT yet, because nine SHOULD FIX points remain and most are claims a GPT reviewer with the code would catch:
- Bringing the 24 milestone kinds under the S04 intake does change which records the rules and figures use (N1).
- The coverage report's 27 and 5 are mis-described or understated (N2, N3).
- E35 is counted as built through a template that bypasses human verification (N4).
- Six of the 33 templates have no real-builder file (N5).
- APG outputs of current rules sit in "later" while release A depends on them (N6).
- The Section 18 phase line is inaccurate (N7).
- The minimum release's entry form contradicts the general-entry design (N8).
- "Shown as qualified" can overstate a blocked insight (N10).

Most fixes are text. N2, N3 and N6 (and N26 if E16 is moved) need small generator changes and a regeneration. After that, a focused check of just the changed lines and the regenerated CSVs is enough; this does not need another full agent round. Then it can go to GPT.
