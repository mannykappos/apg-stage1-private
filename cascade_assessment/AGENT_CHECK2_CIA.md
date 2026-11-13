# INDEPENDENT READ-ONLY (agent) — scoped re-check of CIA_DRAFT2.md (Section 18 §6 cascade impact assessment, APG-CR-DSR)

Reviewer: a fresh independent agent, read-only. Nothing in `cia_audit_in/` was edited, moved or deleted. I checked the modification times afterwards: no input file is newer than the start of this check. Synthetic data only. Scripts I ran: the builder's `build_cia.py` and `assemble.py`, writing into my own folder `scratchpad/agentchk2_cia/`; the package validator; and my own read-only scripts in `scratchpad/agentchk2_tools/`. Those scripts dump each .docx in body order, list each dependent span's start and end, print the item after each insertion point, measure how much of each heading the impact table covers, and compare RTM summaries with the .docx text.

**Verdict: NOT READY for GPT or for owner approval.** The reproduction is exact. The new span logic, the end-of-block check and the table-row anchors work. 36 of the 45 earlier findings are fixed, 9 are partly fixed and none is unfixed. Two blocking problems remain:
- The new financial view and the what-if columns bear on canonical locked text that is still not in the dependents table: S03 §4 and §4.1, and S05 §5.
- A new S05 addition mixes up the approved budget and the authoritative forecast, against S03 §4.1 ("A forecast is not an approved budget").

Each fix below is a wording change or a dependents addition. There is no redesign. One fix pass, then a focused re-check of only the changed items, then GPT. The review is not looping yet: this is the second agent round on this assessment, and the findings are narrower than in round 1.

**Counts: BLOCKING 2, SHOULD FIX 11, MINOR 20**

Abbreviations: Sxx = locked Section xx v1.0. "pN" = python-docx paragraph index (0-based). "D2 l.N" = line N of CIA_DRAFT2.md. In the builder's output, "Sxx table T row R" uses a 1-based table number and the RTM's 0-based paragraphs (see m2).

---

## 1. Status of the 45 findings of check 1

| # | Finding | Status | Evidence in draft 2 and its tables |
| --- | --- | --- | --- |
| B1 | S01 insertion split §3.6 | FIXED | cia_data ADD anchors S01 at ('p', 89). p89 is the last item of §3.6, and p90 is Heading 1 "4. Evidence and deliverables" (my dump). `check_end` (build_cia.py l.85-99) enforces this. |
| B2 | Spans held RTM rows only | FIXED | `span()` reads body items (l.57-69). All 61 unmapped paragraphs named in check 1 are now in CIA_RTM_IMPACT.csv (S05 p28 and p35; S11 p44-51, 56, 57, 59, 60, 16, 19, 28; S10 p19-25; S15 p65 and p72; S12 p75; S05 p97 and 98; S04 p34, 53 and 116; S13 p43; S16 p36; S02 p136). 393 items were added and 1 dropped (APG-S01-L0089, no longer touched). |
| B3 | Named dependents missing | FIXED | Every ID named in B3 is present (checked by ID). New missing dependents are in N1, N4 and N5. |
| B4 | Severity became money only | FIXED | S06 DS002 (D2 l.647) grades the money part only, keeps the classification separate, and covers the no-amount case. Question 4 was added. Residual problem: N9. |
| B5 | Undefined original-scope profit | PARTLY | It is now defined as a breakdown that adds up exactly (S05 DS002, S11 DS003), with tests and question 3. But the cost terms of the breakdown do not follow S05 §3.2's decomposition (N3), and the "budget" half is confused (N2). |
| S1 | RTM IDs would renumber | FIXED | D2 §6.2 l.207: IDs are kept by text and old index, and regeneration fails if an old ID would change. |
| S2 | Table rows in the RTM | FIXED | 15 table rows, each with its own ID; anchor form defined (l.206). Residual: m2 (which numbering base). |
| S3 | Version lines and lock records | PARTLY | 10 version lines in REWORD; 7 amendment records; T18-08 covers them. But the lock-record sentences check 1 named ("Section 04 v1.0 is locked…", S04 p186; S05 p174; S06 p171; S11 p110) are neither reworded nor explained (m3). |
| S4 | Question 1 wrong and narrow | FIXED | Q1 (l.434-440) cites F-67 and DC-11 and covers all settings. The code facts are correct (policy_approval.py l.81; det/policy.py l.7, 119, 141-150; det/detect.py l.46). Residual: N11. |
| S5 | S05 DS001 settled Q3; categories | PARTLY | The Q3 bracket, "authoritative forecast (§5.1)", the state mapping, the two columns and the S04 §9 rules for held records are all done. But "budget" is merged into the forecast, and cost-side pending items are not mapped (N2). |
| S6 | Resubmitted/withdrawn are state changes | PARTLY | S11 DS001 now routes them through §8.1. But "withdrawn" has no target state in S11 §8 (N6). |
| S7 | DS004 as a cost category | FIXED | S03 DS014: "a grouping of costs already counted, not a separate cost (Section 05 §6)". |
| S8 | Developer entities in the annex | PARTLY | DS009 and DS014 are limited. But PG-FR-027 still says "every data entity Profit Guardian needs", and DS009 still says the register "lists every entity Profit Guardian needs" (N13). |
| S9 | Draft 7 items left out | FIXED | DS023 (location, worker access, correction route), DS027, DS008, DS005, DS002 (scope), DS009 and DS014 are all present. DS002 is aligned with AC-09 (see m8). |
| S10 | "Switched on" | FIXED | DS002's last sentence; S02 §2.1, S06 §1 and §3, and PG-AI-AC-18 are in the table; §4 l.157. The citation is wrong (m6). |
| S11 | Financial policy as a setup answer | PARTLY | DS026 limits the setup answers to "settings the builder owns". But "the choices Section 05 leaves to the business" and "the product-level financial decisions" are not defined anywhere in the locked text (N10). |
| S12 | Carried matters | PARTLY | M03, M06, M16, the CR-10 step (§8 item 4) and the "not re-checked" labels are fixed. M15 says the RTM cross-check was "added to section 8's steps after approval", but no such step exists (N12). |
| S13 | Section 08 and the M6 contracts | FIXED | §6.1 l.199 and §6.3 l.262. S08 §4-§7 and §15 are under C21. |
| S14 | DB register rows and Amir | FIXED | §6.7 l.360: no rows are added; the owner decides later; DB-APG-002 overlap noted; nobody is named. |
| S15 | Phase numbering | FIXED | §6.3 l.270-280 maps to S14 (checked against S14 p27-p131 and S18 p66-p73), and §13 reports the difference. Residual: m5. |
| S16 | Tests table | FIXED | Every named test is in stage1_freeze_test_files.txt; the new tests are listed (l.312-317). Residual: m10. |
| S17 | Package gaps | FIXED | Change register created; decision records and check reports join the manifest; "by design" dropped. A new consequence is N4. |
| S18 | C11 and C14 labelled clarification | FIXED | C11: "addition (new design and new code)"; C14: "addition (new presentation…)". |
| S19 | Defect CR's dependency | FIXED | §6.3 l.260. |
| M1 | Insertion-point count | FIXED | "24 distinct anchors" (matches the CSV). |
| M2 | "all 19 sections" | PARTLY | Now reads "in Sections 00 to 17 and the package" (l.27). The table holds no package items (m7). |
| M3 | Section 00 §11 titles | FIXED | §13 l.689, checked against S00 p90-p108. |
| M4 | Risk table citations | FIXED | Now S04 DS014 and S16 §9 (p74 "Do not interpret a failed or partial sync…"); PG-PC-AC-02 and PG-CR-AC-10. |
| M5 | "Four stricter controls" | FIXED | l.158-161. |
| M6 | Decision numbers | PARTLY | Named by source, but three citations are wrong or incomplete (m6). |
| M7 | Current wording thin | FIXED | 160-character quotes; full text in the CSV and TXT. Residual: m4. |
| M8 | Terminology | FIXED | l.342. |
| M9 | M11 among change items | FIXED | |
| M10 | Source archive hash | FIXED | Recorded (l.58 and l.700). It cannot be verified from the pack, because the zip is not included. |
| M11 | Appendix C cost carriers | FIXED | E21 and E16 added. The entity IDs are correct (ENTITY_REGISTER rows 18 and 23). |
| M12 | Programme versions | FIXED | S03 DS002: "approved or working". |
| M13 | Unmapped cost code | FIXED | DS027 "accepted with warnings (§8)"; S04 §8 and §11 in the table. |
| M14 | "by whom" | FIXED | DS011. |
| M15 | Second-person scope | FIXED | DS022. |
| M16 | Percentage base missing | FIXED | S06 DS002. Residual: m12. |
| M17 | Plain words | FIXED | §1 glosses, four questions with examples. |
| M18 | Row count | FIXED | 81. The breakdown of that count does not add up (m1). |
| M19 | materiality.py | FIXED | §6.3 l.266. |
| M20 | Closure placeholders | FIXED | §9 l.396-402. |
| M21 | Subcontractor claims | FIXED | §6.3 l.263. |

Totals: FIXED 36, PARTLY 9, NOT FIXED 0.

---

## 2. New findings

### BLOCKING

**N1. The new financial view (C13) and the what-if columns (C14) bear on canonical locked text that is still not in CIA_RTM_IMPACT.csv.** S18 §6 (p56): "A change affecting a canonical financial definition must identify downstream effects… an unreviewed dependent section blocks approval."

What the impact table covers, measured against the .docx by heading:
- **S03 §4 Canonical financial classifications (0 of 15 items) and §4.1 Mandatory separation rules (0 of 11).**
  - S03 table 3 defines Budget, Forecast, Commitment, Scenario and Exposure.
  - §4.1 p26 says "A forecast is not an approved budget."
  - §4.1 p27 says "A scenario is not the current expected result unless explicitly adopted as the forecast."
  - The CIA itself calls each what-if value "a scenario-only value" (§6.6 l.337 and l.342), and S05 DS001 shows budget and forecast together (see N2).
- **S05 §5 Forecast cost-to-complete engine (0 of 13).** S05 DS002 and DS003, and Appendix C ("the builder may forecast the cost still to come on an extra"), attribute forecast cost to complete to each variation. S05 §5 p54 says "The precise algorithm must be selected after repository discovery".
- **S05 §5.3 Forecast movement bridge (0 of 3).** Movements must reconcile to the total, and the bridge already has an "approved commercial changes" class (p81-p82).
- **S05 §12 Rounding, currency, tax and numerical integrity (0 of 6).** The breakdown and a split cost line must "add up exactly" (DS002; Appendix C).

Fix: add DEP rows to cia_data.py:
- C13 and C14 → S03 '4' and '4.1';
- C13 → S05 '5', '5.3' and '12'.

Then regenerate, review the new rows, and state in §4 how the view meets S03 §4.1 items 3 and 4 and S05 §5.

**N2. S05 DS001 (new in draft 2) puts the approved budget inside the authoritative forecast, and leaves the owner's cost-side examples unmapped.**

Evidence:
- DS001 (D2 l.624) says: "Show the budget and profit of the authoritative forecast (§5.1) first."
- The authoritative forecast (S05 §5.1 p67-p72) has forecast final cost and forecast final margin. It has no budget.
- The budget is the "Approved Budget" of S05 §3.3 p35. S03 table 3 row 1 defines it as "Approved financial allowance", and S03 §4.1 p26 says "A forecast is not an approved budget." Read literally, the new S05 text contradicts a canonical separation rule. §4 (l.130) and §6.6 (l.333) claim no canonical definition changes.
- Owner record item 11 asks for the budget and the profit to show before and after approval, and names cost-side items: "Even the budget change has to show before its approved… Like purchase order on hold or pending". DS001's "awaiting approval" column maps only revenue states (S11 §8 draft and submitted values; claims). Its "on hold" column maps only held records. A purchase order awaiting approval (S03 §13 PO lifecycle "Draft → Submitted → Approved"; S05 §6 p86 "unapproved orders") and a budget revision awaiting approval have no column.
- S11 "Potential" and "Estimated" (p44-p45), and S05 §3.2 "speculative" revenue (p30), are neither mapped nor excluded.
- Question 3's title asks "What do the main budget and profit include", but its example (l.448-453) has no budget at all. The owner is not shown what "budget" means here.

Fix:
1. Reword DS001 to: "Show the approved budget (§3.3) and the authoritative forecast's final cost and final margin (§5.1) first."
2. Add cost-side mappings to the "awaiting approval" column: purchase orders and commitments not yet approved, and budget revisions not yet approved. Each what-if then applies to forecast cost or to the approved budget, as relevant.
3. Say that potential, estimated and speculative values are not shown in these columns (they stay analytical opportunities, S11 §4.1), or give them a column.
4. Add a budget line to question 3's example, for instance: approved budget $4,600,000; a $60,000 budget revision awaiting approval shown beside it; a $40,000 purchase order on hold shown beside the forecast cost.

### SHOULD FIX

**N3. The cost terms of S05 DS002's breakdown can double count, so "the parts add up exactly" cannot be guaranteed as worded.**

Evidence:
- DS002 (l.625) and §4 (l.132): "its approved revenue and the actual cost, commitments and forecast cost to complete attributed to it".
- S05 §3.2 p29: "Forecast Final Cost = Cost Recognised to Date + Forecast Cost to Complete. The decomposition must prevent overlap between recognised costs, commitments and cost-to-complete."
- S05 p33: "A commitment is not automatically an additional cost on top of a forecast."
- Listing commitments as a third term alongside forecast cost to complete repeats the overlap S05 forbids. DS003 deals only with actuals against commitments.
- DS002 also says "Values that are not final are shown beside it… never in it", yet forecast cost to complete (an estimate) is in it.

Fix:
- Define each part's cost as its share of forecast final cost under the same decomposition as S05 §3.2: cost recognised to date plus forecast cost to complete, with an attributed commitment counted once inside the forecast cost to complete (p33).
- Change "values that are not final" to "items whose approval or commercial state is not final (as above)".
- Add a test: an open purchase order attributed to a variation that is also in the forecast cost to complete is counted once.

**N4. Section 18 is not listed as a dependent, although the new span logic can now list it.**

Evidence:
- By-section row 18 (l.124): "none (S18 has no RTM rows: section 13)". But build_cia.py now reads documents, and S18 uses Heading 1 and 2 styles (12 and 13 headings, from my style count), so its spans resolve.
- C21 and §6.7 change exactly what S18 governs:
  - §2 p10: "exact approved filenames and versions";
  - §3 p25-p26: unexpected files rejected; "expected locked version/title". The v1.0 history files would be extra controlled files;
  - §4 p31-p38: RTM;
  - §6 p47-p56;
  - §7 p57-p63: the two DB needs;
  - §9 p78-p84.

Fix: add DEP rows → S18 '2', '3', '4', '6', '7' and '9' for C21 (and C02 and C07 for §7). Regenerate and change row 18 to "dependent: reviewed".

**N5. Other locked text that new or changed additions plainly bear on is missing from the table (0 rows each).**
- S03 §14.3 Calculation record (p220-p229). S04 DS013 cites it ("with the run recorded (Section 03 §14.3)"), and so does M03 (l.410).
- S06 §2 p10, §4 p28 and p34-p35, §7 p81-p83, and PG-AI-AC-06:
  - S04 DS007 restates them: "never called a loss or confirmed leakage; any amount comes from a traceable Section 05 calculation or is labelled an estimate". Draft 7 l.169 cites "S06 §4… S06 §2 and §7, PG-AI-AC-06".
  - S06 DS002's no-amount and compliance findings are S06 §4 p28 and §7's "non-financial risk".
- S12 §12.3 (p26-) and checkpoint C (p124-p125, "Retention/security release gate"), for C18: the retention events and their release and receipt rules.
- S15 §15.11 Human approval and privileged overrides (p126-p136: "Changes to authoritative financial rules or approved baselines"), for C04 and question 1; S15 §15.8 Audit logging, for C20.
- S17 §7 (AI and extraction tests), T17-02 "Partial source feed" and T17-06 "Prompt injection in source document", for PG-DS-AC-13, S04 DS020 and DS022.
- S02 §7 p127 ("incomplete or stale source data must affect recommendations and be disclosed"), for C07 and C08.

Fix: add these to DEP with reasons, regenerate and review.

**N6. S11 DS001's "withdrawn" has no state to move to, so "C13 adds no new revenue state" (§4 l.145) is not supported.**

Evidence:
- DS001 (l.661): "A resubmission or a withdrawal is a change of state made through the process §8.1 requires". Resubmission goes back to "Submitted value" (S11 p47).
- S11 §8 (p44-p52) has no withdrawn or closed state.
- For an item "carried at the builder's own cost", the what-if column ("the effect it would have if it went through", S05 DS001) has no meaning.

Fix: either name the state a withdrawal ends in (for example "removed from the commercial lifecycle, value nil, history kept"), and correct §4 to say whether that is a new state; or treat withdrawn as a terminal recorded status of the one Disputed/rejected state. Say that an own-cost item shows no what-if.

**N7. C02 and S04 DS028 put the two direct writes and the in-code authority register into the migration and its change request. Draft 7 and the CIA's own §6.3 do not.** This was carried from draft 1 and missed by check 1.

Evidence:
- C02 (l.81): "…the two direct writes and the in-code authority register under the Section 04 intake. A regression baseline is taken first, and the move has its own change request."
- DS028 (l.609): "including… the records written straight to the store; take a regression baseline… under its own change request".
- Draft 7 l.189 (release A item 1, cited as C02's source): "The two direct writes… and the in-code authority register are not part of this migration: they enter the reference intake as new record kinds (items 3 and 4), which do not wait for it."
- The CIA's own §6.3 l.262 lists retention events and quote readings as items 2-6.

Fix: limit C02 and DS028 to the 24 kinds of the second delivery loop. Add a sentence saying that the direct writes and the authority register enter the intake as new record kinds under items 3 and 4, without waiting for the migration.

**N8. Question 3's worked example puts a disputed claim inside the main figure.**

Evidence:
- l.453: "Beside the main figure, never in it: … a disputed claim, −$20,000 if lost."
- If the disputed claim is not in the main figure (S05 §3.2 p32; PG-PC-AC-09), losing it changes nothing. A negative what-if implies it is counted in the main figure.
- The owner reads this example to decide the design.

Fix: "a disputed claim of $20,000: +$20,000 if won". Or, if a disputed charge against the builder is meant, say so: "a supplier's disputed back-charge: −$20,000 if it is upheld".

**N9. S06 DS002 relies on a "safety, quality, contractual and compliance classification" that the locked text defines only for quality findings, and "marked ungraded" reads as covering the whole finding.**

Evidence:
- DS002 (l.647) cites "(this section and Section 13 §13.4)". But S06 §8 p85 lists "safety/contract/compliance implications" as prioritisation factors, not as a classification scheme. S13 §13.4 (p43-p52) covers quality records only.
- Question 4's first example, an expired insurance certificate (S06 §4 p28; §5.2 p46), falls outside S13, so no locked scheme grades it.
- "Until they are set and approved, findings still show, marked ungraded" can be read as covering the safety side too.

Fix:
- Say that for findings outside S13 the non-financial classification uses an approved, documented scheme (S06 §8 p86: "documented, testable and approved"), to be defined before build, and record that as an open design point.
- Reword to "the money grade is marked ungraded; the non-financial classification still applies".
- Add "[owner to confirm: question 4]" (see m11).

**N10. S04 DS026's boundary between the builder's settings and product-level decisions is still undefined in the locked text.** This is why S11 is only partly fixed.

Evidence:
- DS026 (l.587): "the choices Section 05 leaves to the business" and "The product-level financial decisions are not builder setup answers". Neither phrase is defined in Sections 00-18.
- S03 §5.1 p37 and S05 §3.1 p20 make the recognition policy one "applicable to the business/project". M01 lists the revenue basis (8-layer 02 §2.11 decision 2) as an owner product decision.
- Question 3 in effect settles part of 8-layer decision 7 ("How are variations treated in management reporting…") and depends on decision 6 (committed cost, cost to complete, EAC), without saying so.

Fix:
- In DS026, list the builder-owned settings (for example the status maps, the cost-code map and the rule settings). Say that recognition and cost-to-complete methods are decided as product-level policy under S05 §3.1 and §5, not by setup answers.
- Link question 3 to M01 decisions 6 and 7.

**N11. Question 1's claim that "Option B fits the blueprint" leaves out the locked approval controls it touches.**

Evidence:
- l.440 quotes S02 §3.1 as "where practical". The full text, p31, is "Where practical and supported by policy".
- Not mentioned: S15 §15.4 p46 "Separate approval authority for consequential actions"; S15 §15.11 p132 (changes to authoritative financial rules are consequential actions that need approval); PG-FR-025 segregation of duties.
- S04 DS017 ("one person may hold several of these roles") and S06 DS001 ("the builder's authorised approver accepts them") carry no question 1 bracket, though both depend on the answer.

Fix: quote S02 §3.1 in full, cite S15 §15.4 and §15.11 in question 1, and add the question 1 bracket to DS017 and S06 DS001.

**N12. M15 says a step was added that is not there, and the timing is wrong.**

Evidence:
- M15 (l.422): the RTM cross-check of the 100 entities is "Needed before the controlled entity register becomes an annex (S03 DS009); added to section 8's steps after approval."
- §8's "After the change" list (l.385-390) has no such step.
- The annex takes effect when version 1.1 is issued (step 1), so the check must come before approval or before step 1.

Fix: add it to §8 "Reviews before approval", or as step 0 before step 1.

**N13. PG-FR-027 and S03 DS009 still take in the developer entities, and §10 overstates what the blueprint leaves out.**

Evidence:
- PG-FR-027 (l.497): "for every data entity Profit Guardian needs".
- DS009 (l.526): the register "lists every entity Profit Guardian needs", including E91-E95 (ENTITY_REGISTER: "not in the locked blueprint").
- By these words a locked functional requirement would require ways in for entities that DS014 and DS009's own next sentence exclude.
- §10 l.426, "the locked blueprint does not cover the developer capability", is too broad: S02 table 2 row 2 has a Developer / principal actor, and PG-FR-024 requires "developer/principal… views of capital exposure, milestones, holding costs".

Fix:
- PG-FR-027: "for every data entity this blueprint governs".
- DS009: "every entity Profit Guardian needs under this blueprint; it also lists, for information only, …".
- §10: "the developer entities E91-E95 are not in the locked blueprint; the developer/principal views of PG-FR-024 are unchanged". Add PG-FR-024 as a dependent of C05.

### MINOR

- **m1.** The counts line is wrong: "81 (38 paragraphs or bullets, 7 headings, 15 table rows, 14 acceptance criteria)" (l.218; CIA_COUNTS line 1; build_cia.py l.153) adds up to 74. The 7 amendment records are missing from the breakdown. Fix: add "7 amendment records".
- **m2.** The table numbering base is mixed and not stated:
  - the output prints 1-based tables (`it[1] + 1`, build_cia.py l.55; "S02 table 3 row 25" is python-docx table 2);
  - cia_data uses 0-based numbers (`('t', 2, 25)`);
  - the paragraph indices are 0-based;
  - the proposed `table_index=T` (l.206) has no stated base.

  Fix: state the base, preferably 0-based to match `paragraph_index`.
- **m3.** The lock-record sentences "Section 04 v1.0 is locked…" (S04 p186, S05 p174, S06 p171, S11 p110) stay as they are, while S01-S03's "Version: 1.0" lines are reworded. This different treatment is not explained. The amendment record says "The amendment adds text only", but the version lines are reworded. Fix: say these sentences stay as the historical lock record, and change the record to "adds text only, apart from the version line(s)".
- **m4.** CIA_DEPENDENT_TEXT.txt is described as holding the "full text" (l.195), but for RTM-mapped items `ref()` returns the RTM summary, which is cut at 500 characters. 3 dependents lose text: APG-S01-C0021, C0044 and C0057 (the last loses "Source freshness and coverage must be explicit…"). Fix: write the .docx text (`it[3]`).
- **m5.** The phase numbering the executor will follow is S18's: CLAUDE_HANDOFF_INSTRUCTIONS.md l.27-32 has phase 5 as security and phase 6 as acceptance. The CIA uses S14's (l.274). Fix: give each release's phases in both numberings, and say this replaces draft 7 l.265 ("phases 1 to 3… phase 4 to 6").
- **m6.** Three citations are wrong or incomplete:
  - §4 l.157 cites "data supply decision 9" for "switched on". Decision 9 is the default rule settings; the idea comes from draft 7's "Setup questions" (l.85) and decision 5, the middle path.
  - C11 (l.90) cites owner record item 9 only. Item 7 is the main severity decision.
  - C13 (l.92) leaves out item 4, the rejected-variation outcome.
- **m7.** §1 (l.27): "1,071 of them, in Sections 00 to 17 and the package". The table holds no package items. Fix: drop "and the package".
- **m8.** S04 DS002 narrowed eligibility from draft 1's "missing, unverified, conflicting, stale or not authoritative" to "missing, unverified or stale". That matches draft 7 and AC-09, but DS003 still lists conflicting and not authoritative as gap reasons. Fix: say that a conflicting or non-authoritative input counts as not verified (S04 §5 p53, §9 p74, PG-DI-AC-03), so the narrowing relaxes nothing.
- **m9.** S01 DS004, "this is an early gate", can be read as a new Gate 01-x that S01 §2 and §7 do not list. Fix: "an early discovery item", or add it to the §7 exit criteria.
- **m10.** §6.4 (l.290-292) is incomplete:
  - add test_det_signal (det/signal.py: "severity is only ever 'unrated' until an approved band applies") and test_mkt_golden for C10 and C11;
  - add test_det_rules_commercial (R04B, DC-1, S11 DS001) for C13;
  - add test_mkt_fx_fresh for C09;
  - "severity values change only under the defect change request" is wrong, because the C11 build changes them too.
- **m11.** No "[owner to confirm: question 4]" bracket on DS002's classification sentence, although l.467 says the brackets mark the open points.
- **m12.** S06 DS002: where a grade has only a percentage level and the base is missing, the money grade is ungraded. Say so, and add a test.
- **m13.** "Every finding is fixed" (l.11, l.377) overclaims, given the 9 partly fixed findings above. Reword to "a fix is claimed for each".
- **m14.** M16 says the report "is never cited as proof on its own", but PG-DS-AC-12 cites only the report. Fix: add to AC-12 or DS029 that each rule's inputs are confirmed by its tests when the rule is next changed (draft 7 l.147).
- **m15.** S03 DS011 `supplied_by` overlaps the existing `created_by / updated_by` (S03 table 2 row 12) and DS010 `channel` overlaps `source_system` (row 4). Fix: say how each new field relates to the existing one.
- **m16.** §6.2 l.208-216: "proposes adding RTM rows for those it touches" gives no count (up to 183 = 112 + 71) and does not say whether every touched item or only the anchors are meant. The `id_type` of the DS-series IDs is not given either (S18 §4 p33).
- **m17.** Appendix A (l.697) and §2 say the tool fails "if an insertion point is not the true end of its block", but they leave out its exemption for amendment records (build_cia.py l.88-89).
- **m18.** Question 1's "A correction first" (l.434: "first put to the owner… corrected the same morning") and "Asked of the owner on 2026-11-13" are not in OWNER_DECISIONS_2026-11-12.md, which has items 1-14 only. Fix: record them there.
- **m19.** In S04 DS023, the parenthesis "(an actor Section 02 §3 does not yet list)" attaches to "access". It should attach to the worker.
- **m20.** §1's plain-words summary ("No detection rule… changes", l.25) does not tell the owner two things. C11 changes the severity mapping, which S06 §5.1 p39 makes part of every rule's definition. C02 changes some results. Add one plain sentence for each.

---

## 3. Checked and found sound

- **Reproduction.** `python3 -I tools/build_cia.py locked_package agentchk2_cia` and `assemble.py` give byte-identical files: CIA_PROPOSED_TEXT.csv (0ec25203…), CIA_RTM_IMPACT.csv (7766b0d9…), CIA_DEPENDENT_TEXT.txt (63dfda4f…), CIA_COUNTS.txt (63b2ddb3…) and CIA_DRAFT2.md (6f8b7e03…).
- **Body order.** No document has w:sdt or nested body paragraphs. python-docx `paragraphs` lines up with the body w:p elements in all 19 documents. All 2,712 RTM anchors match their .docx paragraph text.
- **Spans.** All ~120 dependent spans start at the intended heading and end at the next heading of the same or a higher level (each start and end listed). Unmapped paragraphs and table rows are included.
- **End-of-block check.** Each of the 24 anchors is followed by a heading, the end of its list, or the last row of its table (S03 L0072 is followed by the closing p72 paragraph of §6.2, which is correct). The 7 amendment records sit after the last lock-record line and before "Next section". New headings 3.7, 14.1, 14.2, 18.1-18.3 and 8.2 are in sequence and at the right level.
- **Table-row anchors.** S02 table 3 row 25 is PG-FR-025. S03 table 1 row 20, table 2 row 14 and table 4 row 8 are the last rows of the entity, common-field and lifecycle tables.
- **Counts.**
  - 1,360 rows over 1,071 items (888 + 112 + 71).
  - The anchor-move counts per section.
  - Unmapped text: 541 paragraphs, of which 401 in S00-S17, and 125 table rows.
  - 10 version lines.
  - The by-section additions (7, 3, 16, 44, 4, 3, 4).
- **Package.**
  - Validator: PASS (27 files, 19 sections, 2,712 rows).
  - The 7 hash prefixes in §2 are correct, and the manifest digest dad3fa91… matches the validation report.
  - The archive digest 487becab… cannot be verified here, because the zip is not in the pack.
- **Code facts.**
  - F-67: policy_approval.py l.81; det/policy.py l.7 and l.119.
  - DC-11: severity is graded whether or not the policy is approved (det/detect.py l.46), and findings carry `policy_unapproved` (det/findings.py l.96 and l.294).
  - The bands are `min_cents` only.
  - Appendix B matches fin/cash_states.py: transitions l.18-19, amount and pool l.43-47, evidence, human actor, roles l.20-22 and l.52-55, exact bank match for "received", append-only seq, and `at`.
  - M06's "Under Review" and "received" reading of S03 table 4 row 6 is correct.
- **Entity IDs.** E09, E10, E16, E21, E23, E57, E59, E64, E77, E89 and E90 are as stated (ENTITY_REGISTER.csv).
- **Phases.** The S14 and S18 phase numbering in §6.3 is accurately described.
- **Version lines.** The text at each of the 10 version-line anchors is quoted exactly.
- **Arithmetic.**
  - Question 2: 2% × $5,100,000 = $102,000.
  - Question 3: $5,200,000 − $3,100,000 − $1,600,000 = $500,000; $200,000 − $150,000 = $50,000; $500,000 − $50,000 = $450,000.
- **Owner questions.** Questions 1, 2 and 4 are plain, needed and accurate on the code, apart from N8, N9 and N11.
- **Data supply decisions.** Decisions 7, 8, 9, 10 and 11 are correctly cited, apart from m6.
- **Draft 7 wording.** PG-DS-AC-01 to 14 match draft 7, with editorial changes only. S04 DS008, DS009, DS014, DS022, DS023, DS027 and S06 DS001 are faithful to draft 7 and to data supply decisions 8 and 9.
- **Tests.** Every test and fixture named in §6.4 exists in the freeze list.
- **Honesty boundaries.**
  - There is no claim of implementation, acceptance or production readiness, and stage 2 stays not authorised.
  - Builder work is labelled BUILDER-EXECUTED: NOT INDEPENDENT (l.9, l.699).
  - "Amir" appears only in quoted locked text (S14 p126) in the dependents table. The CIA creates no work for him and no dependence on him (§6.7 l.360).

---

## 4. For the main session (memory)

Nothing new about the user was learned from the files that the main session needs to store.
