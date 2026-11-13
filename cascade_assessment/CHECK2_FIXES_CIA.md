# Fixes for the second independent check of the cascade impact assessment (draft 2 → draft 3)

Builder work (Claude), BUILDER-EXECUTED: NOT INDEPENDENT. The check is `AGENT_CHECK2_CIA.md` (INDEPENDENT READ-ONLY (agent)). It found 36 of the 45 earlier findings fixed and 9 partly fixed, plus 2 blocking, 11 should-fix and 20 minor new points. A fix is claimed for each, as below.

| Finding | Fix |
| --- | --- |
| N1 canonical text not in the table | Added as dependents: S03 §4 and §4.1 (C13, C14); S05 §5, §5.3 and §12 (C13). All 207 new items were read. Section 4 now says how the view meets S03 §4.1 items 3 and 4, S05 §5 (the method is chosen after discovery, and each component is classified) and S05 §12. |
| N2 budget inside the forecast; cost side unmapped | S05 DS001 now shows "the approved budget (§3.3) and the authoritative forecast's final cost and final margin (§5.1)". Cost-side items awaiting approval (orders and commitments, budget revisions) are added. Potential, estimated and speculative values are excluded (S11 §4.1). Question 3's example now has a budget line, a budget revision and an order on hold. |
| N3 breakdown cost terms | S05 DS002 uses S05 §3.2's decomposition (cost recognised to date plus forecast cost to complete, with an attributed commitment counted once inside the forecast cost to complete). The phrase is now "items whose approval or commercial state is not final". The test of counting it once is in section 6.4's breakdown tests. |
| N4 Section 18 not a dependent | S18 §2, §3, §4, §6 and §9 added (C21), and §7 added (C02, C07). Row 18 now reads "dependent: reviewed". |
| N5 other missing dependents | Added: S03 §14.3 (C01); S06 §2, §4, §7 and PG-AI-AC-06 (C07); S06 §4 and §7 (C11); S12 §12.3 and checkpoint C (C18); S15 §15.11 (C04); S15 §15.8 (C20); S17 §7, T17-02 and T17-06 (C03); S02 §7 (C07). |
| N6 "withdrawn" has no state | S11 DS001: disputed, own cost and withdrawn (nil value, history kept) are recorded statuses of the one Disputed/rejected state. Only resubmission is a change of state, back to submitted, through §8.1. An own-cost item shows no what-if (S05 DS001). Section 4 corrected. |
| N7 direct writes in the migration | C02 and S04 DS028 are limited to the 24 kinds. The direct writes and the authority register enter as new record kinds (items 3 and 4) without waiting. |
| N8 disputed claim in question 3 | Now "a disputed claim of $20,000, +$20,000 if won". |
| N9 non-financial classification scheme | S06 DS002: quality findings use S13 §13.4; other findings use an approved, documented scheme, to be defined before build (an open design point). "Ungraded" now applies to the money grade only. Question 4 bracket added. |
| N10 builder settings vs product decisions | S04 DS026 names the builder-owned financial settings (its status maps). Recognition, cost-to-complete and other methods are product-level policy under S05 §3.1 and §5. Question 3 is linked to M01 decisions 6 and 7. |
| N11 question 1's blueprint basis | S02 §3.1 quoted in full; S15 §15.4 and §15.11 cited. Question 1 brackets added to S04 DS017 and S06 DS001. |
| N12 M15 step | Added as step 2 of "Reviews before approval" (section 8); M15 updated. |
| N13 developer entities | PG-FR-027 now says "every data entity this blueprint governs"; S03 DS009 now says "needs under this blueprint" and lists the developer entities for information only; section 10 corrected, and PG-FR-024 added as a dependent of C05. |
| m1 counts breakdown | The 7 amendment records are added to the counts line. |
| m2 numbering base | Tables and rows are numbered from 0 throughout, as python-docx counts them; stated in section 2 and in build_cia.py. |
| m3 lock-record sentences | The amendment record now says the amendment adds text "apart from the version line(s)", and that the lock record above stays as the record of version 1.0. |
| m4 dependent text cut short | The dependent text now comes from the document itself, not the RTM summary. |
| m5 phase numbering | Section 14's numbering, with Section 18's in brackets; draft 7's mapping is replaced. |
| m6 citations | "Switched on": draft 7, "Setup questions", and data supply decision 5. C11: owner record items 7 and 9. C13: items 4 and 5. |
| m7 "and the package" | Now "in Sections 00 to 18". |
| m8 eligibility narrowing | S04 DS002: a conflicting or non-authoritative input counts as not verified (§5, §9). |
| m9 "early gate" | Now "an early discovery item". |
| m10 tests | Added: test_det_signal, test_mkt_golden, test_det_rules_commercial, test_mkt_fx_fresh, test_mkt_policy. Severity values change under the defect change request and again under the C11 build. |
| m11 question 4 bracket | Added in S06 DS002. |
| m12 percentage-only grade with no base | S06 DS002: that grade does not apply. Covered by section 6.4's test "amount levels only when the base is missing". |
| m13 "every finding is fixed" | Now "a fix is claimed for each", with the second check's fixes not yet checked independently. |
| m14 the scan is not a proof | Added to S04 DS029: each rule's inputs are also confirmed by its tests when the rule is next changed. |
| m15 overlapping fields | S03 DS010 and DS011 say how they relate to source_system and created_by / updated_by. |
| m16 backfill count and id_type | 269 items (184 paragraphs and 85 table rows); id_type stated (section 6.2). |
| m17 exemption not stated | Appendix A states the amendment-record exemption. |
| m18 question 1 not in the decisions record | Added as owner record item 15. |
| m19 parenthesis | S04 DS023 reworded. |
| m20 plain words | Section 1 says the severity levels and the move to one intake both change results later. |
| Earlier partly fixed (B5, S3, S5, S6, S8, S11, S12, M2, M6) | Covered by N2 and N3 (B5, S5), m3 (S3), N6 (S6), N13 (S8), N10 (S11), N12 (S12), m7 (M2) and m6 (M6). |
