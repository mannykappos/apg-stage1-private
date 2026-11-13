# Fixes for the first independent check of the cascade impact assessment (draft 1 → draft 2)

Builder work (Claude), BUILDER-EXECUTED: NOT INDEPENDENT. The check is `AGENT_CHECK1_CIA.md` (INDEPENDENT READ-ONLY (agent)): 5 blocking, 19 should fix, 21 minor. Every finding is fixed as below. `build_cia.py` was rewritten (version 2), and its data moved to `cia_data.py`.

| Finding | Fix |
| --- | --- |
| B1 S01 insertion splits §3.6 | Anchored at S01 paragraph 89. `build_cia.py` now fails unless each insertion point is the true end of its block: the next item must be a heading; for a list item, the end of that list; for a table row, the last row. Amendment records are exempt and go before the closing "next section" line. |
| B2 spans held RTM rows only | Spans are now read from the section documents in body order (paragraphs and table rows), so unmapped text is listed as "Sxx paragraph N" or "Sxx table T row R". All 393 locked items added to the impact table were read (`CIA_DEPENDENT_TEXT.txt` has the full text of every dependent). None needs new wording. Counts re-issued: 1,071 locked items. |
| B3 missing dependents | Added: S06 §6 (finding contract), S02 §8, PG-FR-006 and 021, PG-RS-AC-05, PG-AI-AC-07, S06 §9.1 and S13 §13.4 (C11); S08 §7.1, S04 §14 opening and S16 §5 (C09); S02 §2.1, PG-FR-020, S06 §1 and §3, PG-AI-AC-18 (C07); S07 §3, S11 §5, S09 §3, S03 §13 (C05); S04 L0088 and PG-DI-AC-11 (C10); PG-CR-AC-02, 07, 09, 10, PG-PC-AC-02, 05, 09, 12, S05 §3.3, S03 §5, §6, §7, S17 §6 (C13, C14); S14 §14.7 to §14.10 (C17, C07, C13, C14); S08 §4, §5, §6, §7, §15 (C21, the M6 input contracts). |
| B4 severity became money only | S06 DS002 now grades the money part only. Safety, quality, contractual and compliance classification (S06 §8, S13 §13.4) is assessed on its own and never lowered by a small or missing amount. A no-amount finding shows its classification and is marked as having no amount. Owner question 4 added, with an example. Section 4 rewritten for C11. |
| B5 undefined original-scope profit | Defined as a breakdown of the authoritative forecast final margin that adds up exactly (S05 DS002), with S11 DS003 pointing to it. Section 4 now says this is one new financial view, needing financial-core and overlap tests and fixtures, with accrual and overhead sharing specified before build. Question 3 rewritten with a worked example in which an approved variation sits inside the main figure and the panel splits it. |
| S1 RTM IDs would renumber | Section 6.2: regeneration keeps each ID by matching text and old index, updates only the anchor, and fails if an old ID would change. |
| S2 table rows in the RTM | Each table row is now its own addition with its own ID (15 rows); anchor form `table_index=T; row_index=R` defined; counts corrected (81 additions). |
| S3 version lines and lock records | The 10 version lines are listed as the only reworded locked text (REWORD in `cia_data.py`); an amendment record paragraph is added to each lock record. Section 7's T18-08 check covers them; section 1 and section 4 say so. |
| S4 question 1 wrong and narrow | Corrected to the owner in chat (2026-11-13) and in section 11. It cites F-67 and DC-11, and asks about one-person builders across all settings. |
| S5 S05 DS001 settled Q3; categories | Bracket "[owner to confirm: question 3]" added; "authoritative forecast (§5.1)"; budget and profit named; categories mapped to the S11 §8 and S05 §3.2 states; disputed and rejected shown as two columns of the one state; held records follow S04 §9's provisional-view rules. |
| S6 resubmitted and withdrawn are state changes | S11 DS001: they are changes of state through the S11 §8.1 process, with their own record; section 4 corrected. |
| S7 S03 DS004 as a cost category | Reworded as a grouping of costs already counted, not a separate cost (now S03 DS014). |
| S8 developer entities in the annex | S03 DS009: listed for information only and not governed; S04 DS014 limited to entities this blueprint governs. |
| S9 draft 7 items left out | Added: site capture's unreliable location, workers seeing their records, and the correction route (DS023); the cost-code map required, with each match confirmed by a person (DS027); nudge links only after sign-in (DS008); batched reassessment (DS005); readiness scope (DS002); onboarding checklist (DS009); the export-file way in kept when an integration is down (DS014). DS002 aligned with PG-DS-AC-09 ("missing, unverified or stale"). |
| S10 "switched on" | DS002: an insight not switched on or not set up is shown as such, never as no issue; S02 §2.1, S06 §1, §3 and PG-AI-AC-18 added as dependents; section 4 explains. |
| S11 financial policy as a setup answer | DS026: only the settings a builder owns (status maps, choices S05 leaves to the business); product-level decisions are not setup answers (M01). |
| S12 carried matters | M03 now covers assessment governance; M06 lists the currency and contract obligations and the lifecycle difference, marked not settled; M15 (RTM cross-check of the entities) and M16 (the scan is not a proof) added; the CR-10 check added to section 8; the three re-check fixes labelled builder-made and not re-checked (sections 2, 8, 10). |
| S13 Section 08 and the M6 contracts | The M6 input contracts are approved with this change request as an accurate description of today's code, limits included, not as meeting S08 (section 6.1, 6.3); S08 §4 to §7 and §15 reviewed. |
| S14 DB register rows and Amir | No rows are added. The two needs are recorded for the build change requests, with the overlap with DB-APG-002; the owner decides at build time who carries them out (section 6.7). |
| S15 phase numbering | Mapped to Section 14's numbering, with phase 5 for the user-facing parts; the S14 and S18 difference is reported in section 13. |
| S16 tests table | test_fin_costs, test_fin_forecast, test_fin_bridge_book, test_det_detect, test_det_findings, test_det_noise, test_mkt_detect, test_fin_intake (C18) and the corpus tests added; new tests for DS022, DS024, S11 DS001, the breakdown, the what-if columns and severity added. |
| S17 package gaps | A controlled change register is created (S18 §2); decision records and check reports join the manifest; "by design" dropped; Section 18's missing RTM rows reported in section 13. |
| S18 C11 and C14 labelled clarification | Relabelled additions (new design and new presentation). |
| S19 the defect CR's dependency | Section 6.3: DC-1's recorded outcome rests on S11 DS001; that part waits for this approval or carries the requirement itself. |
| M1 insertion-point count | Counts now give distinct anchors (24). |
| M2 "all 19 sections" | "Sections 00 to 17 and the package". |
| M3 Section 00 §11 titles | Every section from 09 to 18, plus 06 and 10. |
| M4 risk table citations | The S16 §9 claim replaced by DS014 plus what S16 §9 actually says; PG-PC-AC-02 and PG-CR-AC-10 cited for double counting. |
| M5 "four stricter controls" | Only DS022 is stricter; the other three restate locked controls (section 4). |
| M6 decision numbers | Named by source each time: "data supply decision N" (`APG_Data_Supply_Decisions`) or "owner record item N" (`OWNER_DECISIONS_2026-11-12.md`). |
| M7 current wording thin | Section 12 quotes up to 160 characters of the locked text at each anchor; `CIA_PROPOSED_TEXT.csv` and `CIA_DEPENDENT_TEXT.txt` hold the full locked text. |
| M8 terminology | Added: nudge, switched on, verifier role, product owner as approver, the extras view, what-if value (scenario-only); "release" renamed "data release" against S17's release gates; PG-DS-AC-12 says "a gate of the first data release". |
| M9 M11 in the change items column | Only C-items are listed by section now. |
| M10 source archive hash | Recorded in section 2 and Appendix A. |
| M11 Appendix C cost carriers | Purchase orders (E21) and subcontracts (E16) added; invoice lines noted as calculated today. |
| M12 programme versions | S03 DS002: "approved or working". |
| M13 unmapped cost code | DS027: accepted with warnings (S04 §8); S04 §8 and §11 added as dependents. |
| M14 "by whom" | Removed from S04 DS011 to match PG-DS-AC-14. |
| M15 second-person scope | DS022 limited to values keyed from an uploaded document where no extraction is available. |
| M16 missing percentage base | S06 DS002: only the amount levels apply, and the finding says so. |
| M17 plain words | Section 1 glosses the RTM, manifest and hashes; four questions, each with an example. |
| M18 row count | See S2. |
| M19 materiality.py | Described as a reference draft, not an implementation (section 6.3). |
| M20 closure placeholders | Section 9 now has the CR template's closure fields. |
| M21 subcontractor claims | Section 6.3: E17 to E19 to the front of the second release, with the back-to-back check (data supply decision 7). |
