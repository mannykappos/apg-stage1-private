# INDEPENDENT READ-ONLY (agent): focused check of CIA_DRAFT3.md (draft 2 to draft 3), Section 18 §6 cascade impact assessment, APG-CR-DSR

Reviewer: a fresh independent agent, working read-only. Nothing in `cia_audit_in/` was edited, moved or deleted. Afterwards I checked modification times against a marker file made at the start: no input file is newer than the marker. All data is synthetic.

What I ran:
- the builder's `build_cia.py` and `assemble.py`, writing only into `scratchpad/agentchk3_cia/`;
- my own read-only dump script in `scratchpad/agentchk3_tools/`.

Scope: what changed between draft 2 and draft 3 (the tools, `cia_data.py`, the proposed text CSV, the impact CSV and the draft text). Points that have not changed since draft 2 are raised only if they are blocking. None are.

**Verdict: NOT BLOCKED. One more wording-only fix pass is needed before GPT.**
- Both blocking findings of check 2 are resolved in the proposed text.
- Of the 42 earlier findings, 31 are fixed and 11 are partly fixed. None is unfixed.
- Most of the partly fixed findings come from one cause: the proposed wording was corrected, but the summary, test and term passages that restate it were not.
- No new blocking finding.

The fixes below are wording changes plus some extra dependent rows. Nothing needs redesign.

Loop watch: this is the third agent round on this assessment. The findings are getting narrower each round (blocking went 5, then 2, then 0). After this fix pass, I recommend no further full agent round. A confirmation limited to the lines named below is enough, and then GPT.

**Counts: BLOCKING 0, SHOULD FIX 6, MINOR 7**

How to read the references:
- "D3 l.N" is line N of CIA_DRAFT3.md.
- "pN" is the python-docx paragraph index (0-based). An RTM consolidation ID is pN+1.
- "Sxx table T row R" uses the 0-based table numbers that draft 3 now uses.

---

## 1. Status of the findings of check 2

| # | Finding | Status | Evidence in draft 3 |
| --- | --- | --- | --- |
| N1 | Canonical text not in the table | FIXED | cia_data DEP rows were added: C13 and C14 to S03 §4 and §4.1; C13 to S05 §5, §5.3 and §12. The impact CSV now holds S03 table 2 rows 1-13 and L0025-L0034, and S05 H0054-C0083 and H0114-L0119. Each span starts at the right heading and stops at the next heading of the same level. §4 (D3 l.137) now states how the view meets S03 §4.1, S05 §5 and §12. Residual: a4. |
| N2 | Budget inside the forecast; cost side unmapped | PARTLY | S05 DS001 now reads "the approved budget (§3.3) and the authoritative forecast's final cost and final margin (§5.1)". It adds the cost side, excludes potential, estimated and speculative values, and question 3 now has a budget line. But the C14 row (D3 l.94) still says "The authoritative forecast's budget and profit first" (S1). The new cost-side what-ifs have their own problems (S2). |
| N3 | Breakdown cost terms double count | PARTLY | DS002 now follows S05 §3.2 p29 and p33. But §4 (D3 l.133) still gives "the actual cost, commitments and forecast cost to complete attributed to it" (S1). S05 DS003 still says "actual cost or commitments" (a5). The new test is in §6.4 (D3 l.314). |
| N4 | Section 18 not a dependent | FIXED | §2, §3, §4, §6 and §9 were added for C21, and §7 for C02 and C07. 61 S18 items are in the CSV, and the by-section row 18 now reads "dependent: reviewed". My N4 list was incomplete, and further S18 parts plainly bear on the change (S5). |
| N5 | Other missing dependents | FIXED | All are present: S03 §14.3 (C01); S06 §2, §4, §7 and PG-AI-AC-06 (C07); S06 §4 and §7 (C11); S12 §12.3 and checkpoint C (C18; the span is p124-p125); S15 §15.11 and §15.8; S17 §7, T17-02 and T17-06 (C03); S02 §7 (C07). |
| N6 | "Withdrawn" has no state | PARTLY | S11 DS001 and §4 (D3 l.147-148) are fixed: withdrawn is a recorded status, and an own-cost item shows no what-if. But §6.4 (D3 l.317) and §6.6 (D3 l.338) still treat withdrawal as a state change through §8.1 (S1). |
| N7 | Direct writes in the migration | FIXED | C02 (D3 l.82) and DS028 now cover the kinds checked in the calculations only. The direct writes and the authority register enter as new kinds without waiting. This matches draft 7 l.189, including "items 3 and 4". |
| N8 | Disputed claim in Q3 | FIXED | D3 l.456: "a disputed claim of $20,000, +$20,000 if won". |
| N9 | Non-financial classification scheme | PARTLY | The DS002 wording is fixed: quality findings use S13 §13.4, other findings use an approved scheme, "money grade … ungraded", and the question 4 bracket is in. But the open design point is not recorded in §10 or §4, and question 4 does not tell the owner that the scheme does not exist yet (S6). §4 l.143 still says findings show "ungraded" (a1). |
| N10 | Builder settings vs product decisions | FIXED | DS026: "namely its status maps". Question 3 is now linked to M01 decisions 6 and 7 (D3 l.458). The new last sentence of DS026 raises a different point (S3). |
| N11 | Q1's blueprint basis | FIXED | S02 §3.1 is quoted in full; I checked it against S02 p31. S15 §15.4 (p46) and §15.11 (p127, p132) are cited accurately. The brackets are on DS017 and S06 DS001. New concern: S4. |
| N12 | M15 step | FIXED | §8 "Reviews before approval" item 2 (D3 l.382); M15 (l.425). §1 "Next" (l.39) was not updated (a1). |
| N13 | Developer entities | FIXED | PG-FR-027 now says "this blueprint governs". DS009 says "under this blueprint" and lists the developer entities for information only. §10 (D3 l.429) is fixed. C05 to S02 table 2 row 24 (PG-FR-024) is in the CSV. |
| m1 | Counts breakdown | FIXED | "… 7 amendment records" (D3 l.219; CIA_COUNTS line 1). The parts add up to 81. |
| m2 | Numbering base | PARTLY | 0-based numbering is stated in D3 l.53 and in the build_cia.py docstring. But row 0 is the header row, so body rows start at 1, and §6.2's `table_index=T; row_index=R` still states no base (a2). |
| m3 | Lock-record sentences | FIXED | All 7 amendment records: "adds text only, apart from the version line(s) … The lock record above stays as the record of version 1.0." |
| m4 | Dependent text cut short | FIXED | `ref()` now returns the .docx text. APG-S01-C0021, C0044 and C0057 are 521, 620 and 640 characters (they were 500). |
| m5 | Phase numbering | FIXED | D3 l.275-281. I checked against S14 p27-p120 and S18 p66-p73: S14 phases 4, 6 and 7 correspond to S18 phases 4, 5 and 6, and S18 has no interface phase. Draft 7's mapping is replaced. |
| m6 | Citations | FIXED | "Switched on": draft 7 "Setup questions" and decision 5 (draft 7 l.83 and l.197; decisions l.19). C11 now cites items 7 and 9; C13 cites items 4 and 5. |
| m7 | "and the package" | FIXED | "in Sections 00 to 18" (D3 l.28). |
| m8 | Eligibility narrowing | FIXED | DS002: "a conflicting or non-authoritative input counts as not verified (§5, §9)". |
| m9 | "Early gate" | PARTLY | DS004 is fixed. The C16 row (D3 l.96) still says "the early site-capture gate" (a1). |
| m10 | Tests | FIXED | test_det_signal, test_mkt_golden, test_det_rules_commercial, test_mkt_fx_fresh and test_mkt_policy are all in stage1_freeze_test_files.txt (lines 48, 55, 113, 114, 118). The fixture note is corrected. |
| m11 | Question 4 bracket | PARTLY | The bracket is in DS002. §12's header (D3 l.470) still says "questions 1 to 3" (a1). |
| m12 | Percentage-only grade, no base | FIXED | DS002: "a grade that has only a percentage level then does not apply". Covered by the §6.4 test "amount levels only when the base is missing". |
| m13 | "Every finding is fixed" | FIXED | D3 l.11 and l.379. |
| m14 | Scan is not a proof | FIXED | DS029 now carries the sentence. |
| m15 | Overlapping fields | FIXED | DS010 and DS011 now say how they relate to source_system and created_by / updated_by. |
| m16 | Backfill count and id_type | PARTLY | 269 = 184 + 85 matches CIA_COUNTS. The id_type is given for the new series and for backfilled paragraphs, but not for the 85 backfilled table rows (a2). |
| m17 | Exemption not stated | FIXED | Appendix A, D3 l.700. |
| m18 | Q1 not in the decisions record | FIXED | OWNER_DECISIONS item 15 matches §11's correction and both options. It says the answer is pending, and nobody is presented as having decided. |
| m19 | Parenthesis | FIXED | DS023. |
| m20 | Plain words | FIXED | D3 l.26. |
| B5 | Undefined original-scope profit | PARTLY | Through N3: the residual in §4 l.133. |
| S3 | Version lines and lock records | FIXED | Through m3. |
| S5 | S05 DS001 categories | PARTLY | Through N2: the residual in D3 l.94, and S2. |
| S6 | Resubmitted and withdrawn | PARTLY | Through N6: the residuals in §6.4 and §6.6. |
| S8 | Developer entities | FIXED | Through N13. |
| S11 | Financial policy as a setup answer | FIXED | Through N10. The new sentence is S3. |
| S12 | Carried matters | FIXED | Through N12. |
| M2 | "All 19 sections" | FIXED | Through m7. |
| M6 | Decision numbers | FIXED | Through m6. |

Totals: FIXED 31, PARTLY 11, NOT FIXED 0.

---

## 2. New findings

### SHOULD FIX

**S1. Four passages that restate the fixed wording were not updated, so draft 3 contradicts its own proposed text.**

- D3 l.94, C14 row: "The authoritative forecast's budget and profit first". The authoritative forecast has no budget (S05 §5.1 p67-p72; S03 §4.1 L0027, "A forecast is not an approved budget"). DS001 now says it correctly.
  - Fix: "The approved budget and the authoritative forecast's final cost and margin first; …".
- D3 l.133, §4's C13 bullet: "the actual cost, commitments and forecast cost to complete attributed to it". This is the three-term overlap that S05 §3.2 p29 and p33 forbid, and that DS002 now avoids.
  - Fix: copy DS002's wording ("its share of forecast final cost: cost recognised to date plus forecast cost to complete, with an attributed commitment counted once inside the forecast cost to complete").
- D3 l.317, §6.4 test: "a resubmitted or withdrawn variation changes state only through the S11 §8.1 process". Under the new S11 DS001, withdrawal is a recorded status, not a state change. The test as listed would check the wrong behaviour.
  - Fix: "a resubmitted variation changes state back to submitted only through the S11 §8.1 process; disputed, own-cost and withdrawn are recorded statuses of the one Disputed/rejected state, and an own-cost item shows no what-if".
- D3 l.338, §6.6: "resubmission and withdrawal go through the lifecycle process".
  - Fix: "resubmission goes through the lifecycle process; withdrawal is a recorded status".

**S2. The new cost-side what-ifs in S05 DS001, and their example in question 3, misuse a canonical term and can overstate the effect on cost.**

- **The term.** DS001 says "purchase orders and other commitments not yet approved". S03 §4 table 2 row 4 defines a Commitment as a "Documented obligation or authorised commitment". An order that is not yet approved is neither, because S03 table 3 row 2 runs Draft → Submitted → Approved.
- **The amount.** DS001 gives "the effect it would have on … the forecast cost … if it went through". S05 §3.2 p33, the anchor DS001 sits under, says "A commitment is not automatically an additional cost on top of a forecast; determine whether it is already represented." So an order's face value is not its effect on forecast cost when the work is already in the forecast cost to complete.
- **The example.** Question 3 (D3 l.456) says "a $40,000 purchase order on hold, shown beside the forecast cost". It gives no effect and no column. In stage 1, "held" means pending reconciliation (fin/commitments.py l.58), so the order belongs in DS001's "on hold" column. The owner cannot tell that from the example.
- **The variation line.** "+$80,000 to profit if approved" is right only if the variation's cost is already in the forecast. The example does not say so.
- **Budget revisions.** They have no locked state. DS001's "mapped to the locked states" overstates this for them.

Fix:
1. In DS001, change the wording to "on the cost side, purchase orders and subcontracts not yet approved (Section 03 §13: draft or submitted; not yet commitments, Section 03 §4) and budget revisions not yet approved (Section 05 §3.3, 'approved changes')".
2. Add: "for a cost item, the effect on forecast cost is only the part not already represented in the forecast cost to complete (above)".
3. Rewrite the question 3 lines, for example:
   - "a $40,000 purchase order on hold (not yet reconciled), for work already in the forecast to finish: no change to forecast cost if it clears";
   - "a variation waiting for approval: +$80,000 revenue and profit if approved (its cost is already in the forecast)".

**S3. The new last sentence of S04 DS026 can narrow S03 §5.1.**

- DS026 now reads: "Recognition, cost-to-complete and other calculation methods are product-level policy decided under Section 05 §3.1 and §5, not builder setup answers."
- S03 §5.1 (p37) defines Recognised Margin "under the accounting and progress-recognition policy applicable to the business/project". It adds: "The system must identify the policy and source data used."
- S05 §3.1 (p20) only says "Respect approved revenue and cost recognition policy". It does not decide that policy.
- Read literally, DS026 leaves no route by which a builder's own recognition policy reaches APG.
- I suggested this direction myself in check 2 (N10). My wording was incomplete.

Fix: "Which calculation methods Profit Guardian supports is product-level policy (Section 05 §3.1 and §5; M01). Which supported recognition policy applies to a builder's business or project (Section 03 §5.1) is recorded for it and approved as other settings are." Add the same sentence to M01 or M04 in §10.

**S4. Question 1's new paragraph reads S15 §15.4 in Option B's favour, while §1 and §4 still say no check is weakened.**

- D3 l.443: "With Option B the one person is that authority". This treats S15 §15.4's "Separate approval authority for consequential actions" (p46) as a separate approve permission, not a separate person.
- That reading is possible: the list at p41-p48 is a list of permission kinds. But the paragraph does not tell the owner it is a reading.
- It does not mention that Option B drops, for one-person builders, the segregation of duties that PG-FR-025 asks for (S02 table 2 row 25). S02 §3.1 allows that only "where practical and supported by policy".
- §1 (D3 l.25) and §4 still say "No approval or check is weakened", which is true only under Option A. The owner's standing rule (D3 l.129) is that a relaxed condition comes to him as such.

Fix:
1. In question 1, say plainly that Option B is a policy exception to the separation of preparing and approving, for builders with one person. It is allowed by S02 §3.1's "where practical and supported by policy"; it relaxes PG-FR-025's segregation and the code's F-67 check for that case; and it reads S15 §15.4 as a separate approve permission.
2. In §1 l.25 and in §4, add "(Option B of question 1, if chosen, is a stated exception)".

**S5. Section 18 is now a dependent, but parts of it that the CIA itself cites are still not in CIA_RTM_IMPACT.csv.**

- S18 §6 p56 says "an unreviewed dependent section blocks approval".
- The CSV holds S18 §2, §3, §4, §6, §7 and §9 only. Missing:
  - **§5, automated cross-section terminology and conflict review (p39-p45).** §6.6 adds 14 terms, and §7 relies on T18-07.
  - **§8, explicit Claude handoff protocol (p64-p76).** C17's phase mapping (§6.3) is built on S18 §8, and §6.7 changes CLAUDE_HANDOFF_INSTRUCTIONS.md, which §8 governs.
  - **§10, mandatory acceptance tests (p89-p121).** §7 cites T18-01, -02, -03, -05, -07 and -08.
  - **§11, checkpoints A, B and C (p123-p128).** §6.7 cites checkpoint A, and §13 cites checkpoint C.
- My N4 in check 2 left these out.

Fix: add `('C21', '18', ['5', '8', '10', '11'], …)` and `('C17', '18', ['8'], …)` to DEP, regenerate, and review the new rows.

**S6. The open design point that DS002 creates is not recorded, and question 4 implies a grading that does not exist yet.**

- DS002 now says that findings outside quality are classified "by an approved, documented scheme … to be defined before it is built". That is a new design obligation.
- It is not in §10's matters, not in §4's C11 bullet (D3 l.138-143), and not in §4's "Scope widens" list.
- Question 4's first example, an expired insurance certificate (S06 §4 L0029), is exactly a finding that no locked scheme grades. Question 4 says "A safety or quality problem is graded on its own", which tells the owner the grading already exists.

Fix:
1. Add a §10 row, for example: "M17 The non-financial classification scheme for findings outside Section 13 | check 2 | to be designed and approved before C11 is built (S06 §8 p86)". Add one sentence on it to §4's C11 bullet.
2. In question 4, add: "For quality problems the blueprint already has a grading (S13 §13.4). For other problems, like the expired insurance, a grading still has to be designed and approved before this is built."

### MINOR

- **a1. Stale lines, each a short wording fix:**
  - D3 l.39: "A scoped independent check of what changed in draft 2". It should say draft 3, and add the M15 cross-check (§8 item 2).
  - D3 l.96, C16 row: "the early site-capture gate". It should say "early discovery item".
  - D3 l.143: "Findings show 'ungraded'". It should say "the money grade shows 'ungraded'; the non-financial classification still applies".
  - D3 l.470: "questions 1 to 3". It should say "questions 1 to 4".
  - build_cia.py l.2: "Version 2 (after the first independent check)". It should say version 3.
- **a2. Numbering base.**
  - "Tables and rows are numbered from 0" (D3 l.53; build_cia.py l.9) is true, but row 0 is the header, so the first body row is row 1. Say so.
  - Give the same base in §6.2's `table_index=T; row_index=R` (D3 l.207).
  - State the id_type for the 85 backfilled table rows. PG-FR-001 to 025 would be "Source-explicit ID", and the other rows need a stated scheme.
- **a3. Dependent links for the changed text.** The items are in the CSV under other change items, so they were read. Only the link to the change item that now bears on them is missing.
  - C14 (DS001 now maps to these and cites them) needs: S11 §8 and §4.1; S05 §3.3; S03 table 3 row 2 (the order lifecycle); S12 §12.3 L0032-L0033 (disputed, unapproved and scenario-only values kept separate).
  - C04 (question 1) needs: S15 §15.4 (APG-S15-L0047) and S02 table 2 row 25 (PG-FR-025).
- **a4. Rounding against exactness.**
  - §4 (D3 l.137): "the split follows S05 §12's rounding rules, with any rounding difference shown". But DS002 says "The parts add up exactly", and no proposed text mentions S05 §12.
  - Fix: put one sentence in DS002, for example "amounts are in whole cents and the original scope is the remainder, so the parts add up exactly; any percentage shown follows Section 05 §12".
- **a5. S05 DS003 against DS002.** S05 DS003, unchanged, says an attributed cost "stays in actual cost or commitments exactly once". DS002 now places an attributed commitment inside forecast cost to complete. Align DS003: "stays exactly once in cost recognised to date or in forecast cost to complete".
- **a6. Which column holds the new statuses.** S05 DS001 has "disputed" and "rejected" columns "by its recorded status". It does not say where own-cost and withdrawn items go. Fix: "own-cost and withdrawn items sit in the rejected column, with no what-if".
- **a7. Phase brackets.** §6.3 says "with Section 18's in brackets", but phases 1 to 3 carry no bracket. Fix: add "(phases 0 to 4 are numbered the same in both)".

---

## 3. Checked and found sound

- **Reproduction.** I ran `python3 -I tools/build_cia.py locked_package scratchpad/agentchk3_cia` and then `python3 -I tools/assemble.py tools/CIA_SOURCE.md …/agentchk3_cia …/agentchk3_cia/draft3.md`. All five files are byte-identical to the given ones (SHA-256 prefixes):

  | File | SHA-256 prefix |
  | --- | --- |
  | CIA_PROPOSED_TEXT.csv | 0a0b4f02 |
  | CIA_RTM_IMPACT.csv | e52f4ecd |
  | CIA_DEPENDENT_TEXT.txt | b752bb12 |
  | CIA_COUNTS.txt | 35102b53 |
  | CIA_DRAFT3.md | 53b9e58c |

- **Impact-table changes.** 388 rows were added and 115 removed (1,360 to 1,633). Every removed row is the same item under its old 1-based table number. No dependent was lost.
- **Counts.** All agree with the CSVs and with each other:
  - 1,278 distinct items: 1,009 with an RTM ID, 184 paragraphs and 85 table rows without one;
  - 207 new items;
  - the by-section totals and change items (00 to 18);
  - 81 additions = 38 + 7 + 15 + 14 + 7;
  - 269 backfill items.
- **New spans.** Each starts at the named heading and ends at the next heading of the same or a higher level:
  - S12 §12.3 (H0027-C0036) and checkpoint C (H0125-C0126);
  - S17 §7, T17-02 and T17-06;
  - S15 §15.8 and §15.11;
  - S06 §2, §4 and §7;
  - S03 §14.3;
  - S18 §2, §3, §4, §6, §7 and §9.

  PG-FR-024 is S02 table 2 row 24.
- **Locked quotations in changed text.** I checked each against the .docx:
  - S02 §3.1 (p31);
  - S15 §15.4 (p46) and §15.11 (p127, p132);
  - S05 §3.2 p29 and p33; §3.3 p35;
  - S03 §4.1 L0027 and L0028;
  - S06 §8 p86;
  - S11 §4.1 p30 ("analytical opportunities"); S11 §8 p52.
- **Faithfulness to the sources.**
  - C02 and DS028 match draft 7 l.189.
  - DS001 matches owner record item 11's categories and his "budget … before … and after" wording.
  - DS002 follows S05 §3.2's decomposition.
  - S11 DS001 matches owner record item 4's four outcomes, and S11 §8 keeps its single Disputed/rejected state.
  - The "switched on" source matches draft 7's middle path.
- **Owner questions.**
  - Q1 matches owner record item 15, and its code facts are unchanged and correct.
  - Q2: 2% × $5,100,000 = $102,000.
  - Q3: $3,100,000 + $1,600,000 = $4,700,000. $5,200,000 − $4,700,000 = $500,000. $200,000 − $150,000 = $50,000. $500,000 − $50,000 = $450,000. The approved budget of $4,600,000 sits as a separate figure (cost allowance), not inside the forecast. The disputed claim is now shown with the right sign.
  - All four questions are plain, apart from S2 and S6.
- **Honesty boundaries.**
  - D3 l.9 makes no claim of implementation, acceptance or production readiness, and stage 2 stays not authorised.
  - Builder work is labelled BUILDER-EXECUTED: NOT INDEPENDENT (l.9, l.702), and the tools are labelled too.
  - D3 l.11 says the fixes of check 2 have not been checked independently.
  - "Amir" appears only in locked text quoted in the dependents table: S14 L0127, and S18 p15 and p59, now listed as S18 dependents. The draft and the proposed text never name him. §6.7 adds no closure-register rows and leaves the choice of who does the work to the owner. So the CIA creates no work for him and no dependence on him.

---

## 4. For the main session (memory)

The files gave me nothing new about the user that the main session should store.
