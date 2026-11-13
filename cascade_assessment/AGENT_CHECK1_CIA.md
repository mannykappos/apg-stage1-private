# INDEPENDENT READ-ONLY (agent) check of CIA_DRAFT1.md (Section 18 §6 cascade impact assessment, APG-CR-DSR)

Reviewer: a fresh independent agent, read-only. No file under the input folder was changed. Synthetic data only; nothing was run against a real system. Scripts I ran: the builder's `build_cia.py` and `assemble.py` into my own folder, the package validator on the locked package and on a renamed copy, and my own read-only scripts that dump the .docx files and compare spans with the RTM.

**Verdict: NOT READY for GPT or for owner approval.** The tables reproduce byte for byte, and the package facts are right. But one insertion point moves a locked paragraph under a new heading. The dependents table leaves out locked text that the additions plainly bear on, including a canonical formula, so under S18 §6 the missing dependents block approval. Two additions also change meaning without saying so: severity becomes money only, and a new "original scope profit" figure is introduced without a definition.

**Counts: BLOCKING 5, SHOULD FIX 19, MINOR 21**

Abbreviations: Sxx = locked Section xx v1.0. "p N" = paragraph index N in python-docx order. RTM IDs are as in MASTER_REQUIREMENTS_TRACEABILITY_MATRIX.csv. In that file a consolidation ID's number is the paragraph index + 1 (true for all 2,561 such rows).

---

## BLOCKING

**B1. The S01 insertion point splits §3.6. A locked paragraph would end up under the new §3.7.**
Evidence: the proposed text is inserted after APG-S01-L0089 (p88, "Backup, restore and recovery procedures."). But §3.6 continues at p89, "Record which checks can run immediately and which require unavailable services or access.", and that paragraph has no RTM row. The next heading is p90, "4. Evidence and deliverables". Inserting at p88 places the new heading "3.7 Data supply readiness" and its five bullets between p88 and p89. The locked closing sentence of §3.6 would then read as the end of §3.7, so its scope changes. This contradicts §1 ("Nothing already locked is reworded or removed"), §6.1 ("none needs new wording") and the T18-08 check in §7. Cause: `build_cia.py` anchors to the last *RTM row* in a block, not the last *paragraph*, and nothing checks that the next paragraph is a heading. I checked every other insertion point and each is the true end of its block: S04 p121, p147, p166, p174; S05 p33, p88; S06 p39, p86; S11 p52, p54; S03 p11, p71.
Fix: anchor S01 at `('p', 89)`. Add an assertion to `build_cia.py`: the paragraph after each insertion point must be a heading of the same or higher level (or, for a list insertion, the end of that list). Regenerate the tables.

**B2. The dependents spans hold only RTM rows, so the unmapped locked text inside every "reviewed" heading is missing (61 paragraphs).**
Evidence: `span()` (build_cia.py lines 41-48) returns `bysec[sec]` rows, which are RTM rows only. I re-ran the same DEP spans against the .docx and found 61 non-empty paragraphs inside the reviewed headings that are not in CIA_RTM_IMPACT.csv. They include:
- the canonical formula "Forecast Final Margin = Forecast Final Revenue − Forecast Final Cost" (S05 p28, §3.2, under C13);
- every S11 §8 revenue-state definition, p44-51 (C13);
- the bodies of S11 §9 and §10 (p56, 57, 59, 60): only their headings H0056 and H0059 are listed;
- the S04 §14 opening sentence, p116, "Track freshness and completeness by source, project, domain and decision use" (C07/C09). §13 of the assessment itself names this as unmapped;
- the S16 §5 opening, p36 (C07);
- the S13 §13.4 classification rule, p43;
- the S10 §4 factor definitions, p19-25;
- S15 §15.6 p65 and p72;
- S12 §12.8 p75, S05 §9 p97-98, S11 §3 p16, S11 §4 p19 and p28, S04 §4 p34, S04 §5 p53.

So the claim "679 existing requirements, listed by ID ... none needs its wording changed" is not supported for the locked text that has no RTM row. That text includes a canonical financial definition, which S18 §6 says must be traced with care.
Fix: build each span from the .docx paragraphs and table rows between headings, not from RTM rows. Emit unmapped items as "S0x paragraph N (no RTM row)". Review each one and re-issue the counts.

**B3. Requirements the additions plainly bear on are missing from the dependents table altogether.** Under S18 §6, an unreviewed dependent blocks approval. Not in CIA_RTM_IMPACT.csv (checked by ID):
- **C11 severity:** S06 §6 finding contract "Priority: severity, urgency..." (APG-S06-L0076); S02 §8 priority and alert behaviour (APG-S02-H0136 to C0145, plus unmapped p136); S02 PG-FR-006 and PG-FR-021; S10 PG-RS-AC-05 ("Safety, quality and approval constraints cannot be bypassed by a high score"); S06 PG-AI-AC-07 (findings with no amount); S06 §9.1 for C11 (stage 1 re-notifies on a severity increase, det/noise.py line 49); S13 §13.4. S13 §13.4 is listed only under C08 (messages); its bearing on severity is not assessed.
- **C09 freshness:** S08 §7.1 "Market-data freshness gate — mandatory" (APG-S08-H0052, C0053); S04 p116; S16 p36.
- **C07/C08 readiness and messages:** S02 §2.1 "Each feature must identify its data prerequisites, coverage, freshness and limitations" (APG-S02-C0012); S02 PG-FR-020 ("Surface data gaps, stale sources, failed ingestion..."); S06 §3 "the absence of an alert is not proof" (APG-S06-C0021); S06 PG-AI-AC-18.
- **C05 entities:** the new rows cite S07 §3 and S11 §5, but neither is a dependent (APG-S07-H0013 to C0020; APG-S11-H0032, C0034). S09 §3 is the labour data model behind "Labour record and rate" (APG-S09-H0013). The S03 lifecycle table (S03 table 4) gets no "Data gap" or readiness row.
- **C10 defaults:** S04 L0088 ("Do not invent missing values or silently substitute defaults") and PG-DI-AC-11. Defaults are not silent here, but the reasoning must be recorded.
- **C13/C14 money:** PG-CR-AC-02, 07, 09 and 10; PG-PC-AC-02 and 09; and PG-PC-AC-05 and 12. The last two are cited as controls in §5 but are not in the table. Also missing: S05 §3.3 budget and forecast variance (APG-S05-H0035, C0037, plus the unmapped formula at p35); S03 §6.3 core calculations; S03 §7 cost and commitment lifecycle.
- **Interfaces and phases (C13, C14, C07, C17):** S14 §14.8 "Phase 5 — Interface, workflows and user-facing evidence" (APG-S14-H0095 to C0104), including "An uncertain estimate must not appear definitive merely because it is shown as a single currency value"; S14 §14.10 Phase 7 (APG-S14-H0121 to C0131).
- **S08 for the M6 input contracts:** see S13 below.

Fix: add these to DEP with a stated reason for each, review them, regenerate the tables and update the §3 by-section table.

**B4. C11 (S06 DS002) makes the severity of every finding a money test only. This narrows locked severity, and the assessment does not say so.**
Evidence:
- DS002: "The levels at which findings are graded by severity are set by the builder at setup: for each grade an amount, a percentage of the job, or both".
- S13 §13.4 (p43-52): the classification must consider safety, regulatory, structural, building-performance and other factors, and "Financial prioritisation must never override safety or mandatory quality requirements. A low-cost defect may still require urgent attention."
- S06 §8 (p85) adds "safety/contract/compliance implications"; PG-RS-AC-05 says the same.
- Findings with no defensible amount (PG-AI-AC-07, S06 §4 data-integrity findings, R06 expired insurance) could never be graded and would stay "ungraded" for good. Stage 1 already does this: `severity_of` returns 'unrated' when cents is None (det/policy.py line 144).

§4 says C10 and C11 "do not relax" anything. It does not test severity against S13 or PG-RS-AC-05, and no owner question covers it. The owner chose money and percentage levels for grading. He was not asked about safety or quality findings, or findings with no amount.
Fix: limit DS002 to the money part of severity. Add text saying that non-financial classification (S13 §13.4, S06 §8) is unchanged and is never overridden by an amount, and say how a finding with no amount is graded. Then add owner question 4, in plain words with an example (an expired-insurance finding, $0 amount, safety-relevant).

**B5. A new, undefined profit figure, "the original contract scope's budget and profit", is introduced, and its conflict with C14 is not raised with the owner.**
Evidence:
- S11 DS003: "Show the original contract scope's budget and profit on their own, and each extra or variation separately ... its effect on the job's profit. The two are never blended".
- S05 DS002: "A cost not attributed stays with the original scope".
- S03 DS004 adds a cost concept.

None of these defines how original-scope profit is worked out: forecast cost to complete, accruals and overhead are not split (Appendix C: "Not decided here"). Nor do they say how this figure relates to forecast final margin or the one authoritative forecast (S05 §3.2, §5.1). S03 §5 requires every financial view to be named and to disclose its definition and inputs, and S17 §5 says a change to "margin definitions" or "cost allocation" triggers the financial-core suite. So this is new canonical financial semantics, against §1 and §4's "no canonical financial definition changes", and no fixture or test is named. It also pulls against C14: is an approved variation inside "the main figure" (Q3's example uses the contract only) or kept apart from the "original build" (owner decision 5)? Nobody has asked the owner.
Fix: either define the view in S05 and S03 §5 (a formula, the split of forecast cost to complete, a reconciliation to forecast final margin, a label saying it is not the authoritative forecast, terminology entries, financial-core tests and fixtures), or reword DS003 so variations are shown separately without a separate original-scope profit figure. Add an owner question, with a worked example, on where approved variations sit.

## SHOULD FIX

**S1. The RTM plan contradicts itself.** §6.2 says the anchor IDs "do not change, only their anchor, and the RTM is regenerated from the version 1.1 files". §7 says "all 2,712 existing IDs kept". But every consolidation ID is the paragraph index + 1 (all 2,561 rows; e.g. APG-S04-L0122 = p121). Regenerating with the same scheme would renumber 61, 251, 65, 129, 125 and 52 rows in S01, S03, S04, S05, S06 and S11, and would hand the new paragraphs old-style numbers.
Fix: state that regeneration keeps each existing ID by matching its text and old index, assigns DS-series IDs to new paragraphs, and fails if any old ID changes.

**S2. Table rows cannot get RTM rows "in the RTM's own scheme".** The RTM anchors only `paragraph_index=...`, and no table row in any section has a row. APG-S03-DS001 holds 8 rows and DS003 holds 4, yet each counts as one of the "59 new rows".
Fix: define a table anchor form (e.g. `table_index=t; row_index=r`), give each new table row its own ID, and correct the 59 count (or say rows are grouped).

**S3. The version line and lock record of each amended section must change, but no wording is proposed for them.** §6.7 issues v1.1 "each with a lock record naming this change request". That rewords locked paragraphs (e.g. S04 p2 "Version 1.0 | LOCKED SPECIFICATION BASELINE", S04 §22 p185 "Section 04 v1.0 is locked...", S11 §17 p109, S01 §12, S02 §12). So the T18-08 check, "differs only by the additions in CIA_PROPOSED_TEXT.csv, word for word", would fail by design, and "nothing locked is reworded" is overstated.
Fix: list these edits with their exact wording in CIA_PROPOSED_TEXT.csv, or as a named exception in the §7 check.

**S4. Question 1 states a fact wrongly and understates the impact.**
- "Every other setting in APG is entered by one person and approved by a second before it counts" is not true of stage 1. `det/detect.py` line 46 grades with the pinned policy's bands whether or not it is approved. Findings only carry `policy_unapproved` (det/findings.py lines 230 and 294). This is defect candidate DC-11 (rev 4, line 87; draft 7 line 89), which the assessment never mentions. The real control today is narrower: F-67 refuses an approval by the proposer (policy_approval.py; det/policy.py lines 7 and 118-119).
- The two-person rule also blocks a one-person builder from every setup answer (DS024), from accepting the detection defaults (S06 DS001) and from second-person checks of keyed values (DS020), not only severity.

Fix: reword Q1 to cite DC-11 and the real F-67 control, and say the lock-out applies to all settings. If needed, ask one question about one-person builders across all settings.

**S5. S05 DS001 settles question 3 in the text without saying so, and its categories do not map to the locked states.**
- "Present the authoritative figure first" carries no "[owner to confirm]" bracket, although §12 says brackets mark open points and Q3 is still open.
- "Authoritative figure" is not a defined term (the canonical term is "authoritative forecast").
- The owner asked for budget *and* profit (owner decision 11: "budget or profit"), but DS001 sits only in §3.2 forecast final margin and does not name the budget (S05 §3.3).
- The categories (awaiting approval, on hold, disputed, rejected) are not mapped to S11 §8 (draft, submitted, estimated, "Disputed/rejected" as one state) or to S05 §3.2 (submitted/unresolved, disputed, speculative, scenario-only). Splitting disputed from rejected contradicts §4's "stays one state".
- "On hold" items are quarantined or pending records. Their what-if amounts are S04 §9 provisional analysis, which is visible to authorised reviewers and must be traceable to unverified inputs (APG-S04-L0076). DS001 shows them to everyone who sees the figure, with no such conditions.

Fix: add a Q3 bracket, name budget and profit, add a mapping table from categories to locked states, and require S04 §9 provisional-view rules for held items.

**S6. S11 DS001's outcomes "resubmitted" and "withdrawn" are state changes, not attributes.** §4 says the recorded outcome "is an attribute of a rejected variation". A resubmission puts the variation back to "Submitted value", which is a transition S11 §8.1 says must not happen silently.
Fix: say that resubmission and withdrawal go through the S11 §8.1 lifecycle process with their own record, and correct §4.

**S7. S03 DS004 places "Cost of extra work" in the canonical cost-concepts list (S03 §6.2).** That list holds distinct cost states (budget, forecast to complete, actuals, commitments, accruals...). Read there, it suggests a separate cost category, which contradicts S05 DS002 ("the attribution groups it and never adds it a second time").
Fix: reword it as an attribution of actual cost or commitments to an instruction or variation, "a grouping, not a separate cost (Section 05 §6)", or treat it as a canonical-definition change under S18 §6.

**S8. S03 DS002 makes the entity register an annex of locked S03, but the register includes the five developer entities.** ENTITY_REGISTER.csv E91-E95 are "Developer (optional) ... not in the locked blueprint". DS012 then requires a Level 1 way in for "every entity in the controlled entity register". That widens the scope to what §10 says is "Outside this change request".
Fix: leave optional entities out of the annex and out of DS012, or say they are listed for information only.

**S9. Things draft 7 decided are left out of the wording without saying so, and the risk table cites controls that no proposed text contains.**
- Site capture: draft 7 line 99 says workers can see what was recorded about them, a disputed record goes through the correction route, and the device location is not assumed reliable, and "The detail is left to the cascade impact assessment". DS021 defers all of it to CR-05.
- Cost-code map: draft 7 line 86, and decision 8 as cited in rev 4, say every suggested match is confirmed by a person and the map is mandatory before any figure that groups by cost code. DS024 has neither.
- §5 relies on "a nudge's link opens the form only after sign-in", "Reassessment batched" and "a stopped feed falls back to its file", which are in no proposed text.
- The readiness scope (project, organisation, supplier, portfolio, external data: draft 7 line 160) is cut down to "insight and project".
- DS002 and PG-DS-AC-09 disagree: DS002 says "missing, unverified, conflicting, stale or not authoritative"; the AC says "missing, unverified or stale".
- The onboarding data checklist is missing.

Fix: add the wording, or list each item as deliberately left out, with the reason and the owner's agreement.

**S10. A new concept, "insights the builder switches on", enters locked text without assessment.** DS024 ("the insights the builder switches on") and S06 DS001 ("when the rule is switched on") add per-builder switching. No locked section has it. It bears on S02 §2.1 "mandatory functional domains", S06 §1 and §3 (permanent missions; "the absence of an alert is not proof") and PG-AI-AC-18.
Fix: say that an insight that is not switched on, or not set up, is shown as such and never as "no issue". Add these dependents, and note that the owner approved it in principle (draft 7 line 85).

**S11. DS024 makes "the financial policy" a builder setup answer, but E90 is "Financial policy (the ten foundation decisions)" (ENTITY_REGISTER.csv).** M01 says those ten are open owner decisions. Some of them, such as how committed cost and cost to complete are worked out, are canonical semantics (S03 §1: "one canonical meaning for each financial concept").
Fix: say which parts of the policy the builder sets (status maps, recognition policy as S05 §3.1 allows) and which are product-level decisions under M01.

**S12. The carried matters (§10) overclaim or leave items out.**
- M03 drops "assessment governance" from rev 4's "Required before production" item. Calculation runs (assessments) are release A records (draft 7 line 132).
- M06 calls retention handled. But Appendix B's two "points to settle" are locked obligations, not choices: S03 §11.1 "Every monetary value must have an explicit currency" and S03 §10.1 "Associated contract and project". The code's states (TRANSITIONS: no "Under Review", adds "received") also differ from the S03 lifecycle table row "Retention".
- Rev 4's open next step "Cross-check the 100 entities against every row of the Master RTM (not yet done)" (rev 4, Next steps; also "Partly: Gemini evidence 5") is not carried.
- GPT's stated limit, that the code-read scan "does not independently prove ... the AST call-path analysis", is not carried, although PG-DS-AC-12 and DS026 rely on that report.
- §6.3 says the CR-10 overlap must be "checked against it before either is approved", but §1 "Next" and §8 leave this step out.
- §2 says GPT's three smaller points "are fixed", and §8 says "every finding fixed or answered". The three were fixed by the builder "without a further round" (owner decision 13), so no one independent has checked them.

Fix: correct M03 and M06, add the missing matters, add the CR-10 step to the approval path, and label the fixes as builder-made and not re-checked.

**S13. Section 08 and the M6 input contracts are hardly reviewed, and the assessment disagrees with draft 7 on when they are approved.** Draft 7 line 287 says the assessment must cover "Section 08 (the M6 input contracts)". Release A item 5 (line 193) says they are "approved with it", i.e. with this change request. The assessment reviews only 2 S08 rows (C08 §14, C09 C0079), and §6.3 makes "the M6 input contracts approved" a later milestone.
Fix: decide whether this change request approves them. Either way, review them against S08 §4.1, §5, §6, §7.1 and §15, and add the rows.

**S14. The proposed rows in the DB-Dependent Closure Register create a dependency on Amir, or break the required fields.** S18 §7 (p59), S14 §14.10 (p126) and CLAUDE_HANDOFF_INSTRUCTIONS.md item 7 all require "instructions for Amir" in each row. The register has an "Instructions for Amir" column. §6.7 proposes two Blocked rows yet says "No instruction is issued to anyone". The rows would therefore either have that field blank (failing S18 §7) or make closure depend on Amir. The C02 row also overlaps DB-APG-002 ("Verify ingestion/reconciliation persistence...").
Fix: add no rows in this change request. Record them as rows to add when a build is authorised, with the owner deciding who carries them out, and note the overlap with DB-APG-002.

**S15. The phase mapping (C17) ignores that S14 and S18 number the phases differently.**
- S18 §8: phase 5 is security and recovery, phase 6 is acceptance.
- S14: phase 5 (§14.8) is interface and user workflows, phase 6 (§14.9) is verification, phase 7 (§14.10) is database closure.

The entry screens, setup UI, missing-data list, extras panel and verified-first display are S14 phase 5 work. Yet §6.3 puts release A in "phases 1 to 3", and "No release reaches production use without the phase 4 to 6 evidence" does not say whose numbering it uses. C17's dependents also leave out §14.8 and §14.10.
Fix: map releases to S14's phases explicitly, add the dependents, and report the S14/S18 numbering mismatch as a pre-existing observation in §13.

**S16. The tests table (§6.4) is incomplete.** Present in the freeze list but not named:
- `test_fin_costs` (C13 cost attribution);
- `test_fin_forecast` and `test_fin_bridge_book` (C14 display);
- `test_det_detect`, `test_det_findings` and `test_det_noise` (C11: `severity_of` in detect.py line 46, `severity_rank` in noise.py line 49);
- `test_mkt_detect` (M6 rules grade with the detection bands, DC-11);
- `test_fin_intake` for C18 (retention events entering the intake);
- the corpus tests and BASELINE files, named per item.

The "new tests" list also lacks tests for DS020 (second-person confirmation), DS022 (retrospective entries) and S11 DS001.
Fix: complete both lists.

**S17. The package-side work leaves gaps that S18 §2 and §4 require.**
- S18 §2 requires "a controlled change register". The package holds only the template, and §6.7 does not create a change register or add this change request to it.
- §6.7 does not package the decision records or the independent check reports ("Independent audit findings and accepted checkpoint/decision records").
- §3 says S18 has "no RTM rows, by design". Nothing supports that: S18 §4 requires the RTM to trace "the handoff-specific requirements in Section 18", and CLAUDE_HANDOFF_INSTRUCTIONS item 6 says "Sections 00–18". This is a pre-existing gap, so S18 §6, §7 and §9 cannot be listed as dependents.

Fix: add these items to §6.7 and §13, and drop "by design".

**S18. C11 and C14 are labelled "clarification", but both are new design.** The owner was told that grading by a percentage "is new design and new code" (owner decision 9). Rev 4 says of C14: "What is new is the per-category columns across budget and profit". Labelling them as clarifications understates the change.
Fix: relabel both as additions.

**S19. "The defect change request does not wait for this one" (§6.3) is only partly true.** DC-1's approved fix has the builder record the outcome of a rejected variation (disputed, own cost, resubmitted, withdrawn), with the warning staying open until he does (owner decision 4). That rests on S11 DS001, which is a new requirement in this change request, not a locked one.
Fix: say which part of the DC change request depends on this approval.

## MINOR

- **M1.** "31 insertion points" is really 31 (change item, anchor) pairs on 16 distinct anchors (§6.2 counts line).
- **M2.** §1 says "679 existing requirements ... in all 19 sections". S18 contributes none, and the 679 include headings, table rows and unmapped anchors. Say "679 IDs or anchors in Sections 00-17".
- **M3.** §13: S00 §00.11 differs from *every* section title from 09 to 18, not "most". S06 and S10 also differ ("Active Intelligence & Leakage Detection"; "Recommendations, Scenario Engine & Human Approval").
- **M4.** §5 risk table:
  - "a stopped feed falls back to its file (S16 §9)": S16 §9 says nothing of the kind.
  - "tests in the PG-PC-AC-05 family": AC-05 covers the invoice-to-PO double count. PG-PC-AC-02 and PG-CR-AC-10 fit better.
- **M5.** §4 "Four additions make a control stricter": only DS020 is new. Email organisation repeats S04 §6 L0057, held-record correction repeats S04 §9 L0080, and backdated entries repeat S04 §13 and S05 §13.
- **M6.** The decision numbers (9, 10, 11, 13) and `07_decisions` refer to a decisions document that is not in this pack. In OWNER_DECISIONS_2026-11-12.md, items 9, 10, 11 and 13 are different matters. Name the source document each time.
- **M7.** "Current wording" is thin. Anchors are cut at 110 characters, and the requirements being clarified are not quoted in full (S04 L0119; S06 C0040 and C0087; S05 L0033 and §5.1; S04 L0078).
- **M8.** Terminology (§6.6) is missing "nudge", "authoritative figure", "verifier role" (not an S02 §3 actor), "product owner" as an approver, "original scope profit" and "switched on". "Release" and "first-release gate" (PG-DS-AC-12) clash with S17's release (deployment) gates. "What-if amount" should be related to the canonical "scenario".
- **M9.** The §3 by-section table lists "M11" among S15's change items. M11 is a matter, not a change item.
- **M10.** Appendix A records only the manifest digest. The source zip's SHA-256 is not recorded (S18 §3, §9).
- **M11.** Appendix C leaves out purchase orders and subcontracts as cost carriers, although S05 DS002 says "actual cost or commitments". Draft 7 line 144 also calls invoice lines calculated.
- **M12.** S03 DS001 "Programme activity ... of an approved programme version" is narrower than S07 §3, which requires working forecasts and unapproved proposals to be recorded too (APG-S07-C0019, C0020).
- **M13.** DS024 says a record with an unmapped cost code "completes intake". Map this to an S04 §8 outcome (accepted with warnings) and add S04 §11 L0094 (cost-code mismatches) as a dependent.
- **M14.** DS009 says "what is to be done and by whom", but PG-DS-AC-14 leaves out "by whom".
- **M15.** DS020's scope is unclear. Does a person typing a retention amount from a claim letter into an entry screen need a second person? Limit it to values keyed in the document-upload path, as draft 7 does (lines 192 and 199).
- **M16.** DS002 (S06) does not say what happens when the percentage base (contract value) is missing.
- **M17.** §1 uses RTM, anchors, manifest, hashes and canonical without a plain gloss. Its "Three questions" will grow: see B4, B5, S4 and S14.
- **M18.** §6.2: "59 new rows, one per addition" does not match the table-row additions (see S2).
- **M19.** Q2 says "the code could use" other bases. `materiality.py` is a "REFERENCE MODEL ... DRAFT / PROPOSED. Not an implementation" (its header).
- **M20.** §9 says the assessment "leaves a place for each" closure item, but it has no placeholders. Add the CR template's fields: independent reviewer, revised versions and new hashes, verification results and defects, closure decision, owner and date.
- **M21.** Draft 7 decision 7 (subcontractor claims E17-E19 to the front of release B, with the back-to-back check) is not mentioned in §6.3.

## Checked and found sound

- **Reproduction:** `build_cia.py` and `assemble.py`, run into my own folder under the scratchpad (`agentchk_cia`), give byte-identical CIA_PROPOSED_TEXT.csv (d4b3662d...), CIA_RTM_IMPACT.csv (864a11ca...), CIA_COUNTS.txt (061bd2cd...) and CIA_DRAFT1.md (152a23e9...).
- **Package:** all 27 manifest files match their SHA-256. The manifest digest dad3fa91...d89c matches PACKAGE_VALIDATION_REPORT.txt. The validator passes (27 files, 19 sections, 2,712 RTM rows). A copy with S04 renamed to v1.1 and its manifest updated fails with "REQUIRED SECTION DOCUMENT MISSING: 04", exactly as §6.7 says. The seven hash prefixes in §2 are correct.
- **Anchor logic, apart from B1 and B2:**
  - paragraph indices come correctly from the RTM anchors;
  - table indices are right: S02 table index 2 is the FR register and row 25 is PG-FR-025; S03 table 0 row 20 and table 1 row 14 are the last rows;
  - every DEP heading span resolves to the intended heading and ends at the next heading of the same or higher level (all ~75 spans checked);
  - the anchor-move counts per section are right;
  - the unmapped counts (401 paragraphs, 125 table rows) and the named gaps (PG-FR-001 to 025, S04 p116, S06 p85, S11 p44-52, S15 p71) are right.
- **New headings** fit each section's style and do not clash with existing numbers (S11 has 8.1 only; S04 §14 and §18 have no subsections; S01 §3 ends at 3.6).
- **Appendix B against fin/cash_states.py:** the transitions, positive amount within the pool, evidence and exact bank match for "received", human actor, approver and clerk roles, append-only seq, `at` and `note` are all right. It covers GPT's nine fields plus two, and FIELD_SUPPLY_ROUTES.csv has the nine E77 rows.
- **Code facts:** F-67 (approver holds detection_policy_owner, is not the proposer, and the audit log confirms) is in policy_approval.py and det/policy.py. Severity bands are dollar amounts only (`min_cents`). materiality.py's bases are contract_value, forecast_final_cost and forecast_margin.
- **Arithmetic:** Q2, 2% of $5,100,000 = $102,000. Q3, $5,000,000 − $3,000,000 − $1,500,000 = $500,000.
- **Tests:** every test and fixture named in §6.4 exists in stage1_freeze_test_files.txt, and "freeze ee1ce3ec" matches rev 4.
- **Carried matters:** M13 (DC-13 now names MP02-05 and MP09) and M14 (CODE_READS header) are fixed in rev 4. M11's reading of S15 §15.6 p71 is accurate.
- **Wording against draft 7:** PG-DS-AC-01 to 14 match draft 7 apart from editorial changes ("site capture" for "phone capture", and "first-release gate", see M8). C02's description of the result change and its own change request matches draft 7 release A item 1. The four §4 statements on S04 §9, S05 §3.2, S11 §11 and S06 §8 quote the locked text correctly.
- **Honesty boundaries:** no claim of implementation, acceptance, production readiness or independent verification of the assessment itself. Builder work is labelled BUILDER-EXECUTED: NOT INDEPENDENT. The assessment never mentions Amir (but see S14). Stage 2 stays not authorised, and the S04 §20 gate is correctly stated.
- **Completeness against the template:** every S18 §6 element and CR-template field has a place (ID, requester, date, sections and versions, anchors, proposed text, reasons, risk by area, dependents, tests, review, approver, dispositions, versioning, post-change steps, traceability). The thin or wrong parts are listed above.
