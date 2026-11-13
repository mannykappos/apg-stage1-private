# Fixes for the third independent check of the cascade impact assessment (draft 3 → draft 4)

Builder work (Claude), BUILDER-EXECUTED: NOT INDEPENDENT. The check is `AGENT_CHECK3_CIA.md` (INDEPENDENT READ-ONLY (agent)): no blocking point; 6 should fix and 7 minor, all wording or dependents. It found 31 of check 2's points fixed and 11 partly fixed; the residuals are its S1 to S6 and a1 to a7, fixed below. These fixes have not been checked independently; they go to GPT with the rest rather than through a fourth agent round.

| Finding | Fix |
| --- | --- |
| S1 four stale passages | C14 row now "The approved budget and the authoritative forecast's final cost and margin first". §4's C13 bullet uses S05 DS002's decomposition. The §6.4 variations test and the §6.6 revenue row now treat withdrawal as a recorded status. |
| S2 cost-side what-ifs | S05 DS001 now has orders and subcontracts not yet approved (S03 §13 draft or submitted; not yet commitments, S03 §4). Budget revisions are mapped to S05 §3.3's approved changes. A cost item's effect is only the part not already in the forecast cost to complete. Question 3's lines are rewritten (the variation's cost already in the forecast; the order on hold is for work already forecast, so there is no change to forecast cost). |
| S3 DS026 and S03 §5.1 | DS026: the supported methods are product-level; which supported recognition policy applies to a builder's business or project is recorded and approved as other settings are. Added as M18. |
| S4 question 1 and S15 §15.4 | Question 1 states that Option B is a policy exception for one-person builders. It relaxes PG-FR-025's segregation and F-67 for that case, and reads S15 §15.4 as a separate approve permission. §1 notes the exception. |
| S5 Section 18 parts missing | S18 §5, §8, §10 and §11 added (C21), and §8 (C17); S18 §5's human review added to the terminology check in §7. |
| S6 open design point | M17 added (a non-financial classification scheme for findings outside S13, to be designed and approved before C11 is built); §4's C11 bullet and question 4 say so. |
| a1 stale lines | §1 "Next", the C16 row, §4's "ungraded", §12's "questions 1 to 4" and build_cia.py's version line are all updated. |
| a2 numbering base and id_type | Row 0 is the header and body rows start at 1 (§2, §6.2, build_cia.py); id_type is given for backfilled table rows. |
| a3 dependent links | C14: S11 §4.1 and §8, S05 §3.3, the S03 order lifecycle row, S12 L0032 and L0033. C04: S15 L0047 and PG-FR-025. |
| a4 rounding | S05 DS002: whole cents, and the original scope is the remainder, so the parts add up exactly; any percentage follows §12. |
| a5 DS003 | Now "stays exactly once in cost recognised to date or in forecast cost to complete". |
| a6 own-cost and withdrawn column | S05 DS001: they sit in the rejected column, with no what-if. |
| a7 phase brackets | "Phases 0 to 4 are numbered the same in both." |
