# Brief: focused independent check of the cascade impact assessment, draft 5 (what changed since draft 4)

You are a fresh, independent agent. Label your work **INDEPENDENT READ-ONLY (agent)**. This is design only: nothing is built.

Anchor Profit Guardian (APG) has a locked blueprint (Sections 00 to 18, v1.0). A change request (APG-CR-DSR) proposes additions to seven sections, and the Section 18 §6 cascade impact assessment records them. GPT reviewed draft 4 (`in/GPT_REVIEW_DRAFT4.md`: 4 blocking, 3 should fix, 1 minor). The owner then answered six questions and two more decisions (`in/OWNER_DECISIONS_2026-11-12.md`, items 15 to 22). Draft 5 (`in/CIA_DRAFT5.md`) carries GPT's fixes (`in/GPT_FIXES_CIA.md`) and those answers. The entity register was revised to 4.1 after a row-level check (`in/REV41_ADDENDUM.md`, `in/ENTITY_REGISTER.csv`); the register rows themselves were checked by other agents, so do not re-check them row by row.

## Inputs (under `<WORKSPACE>/cia5check/in/`)
- `CIA_DRAFT5.md` and `CIA_DRAFT4.md`, the assessment before and after.
- `CIA_PROPOSED_TEXT.csv` (draft 5) and `CIA_PROPOSED_TEXT_DRAFT4.csv`: every proposed addition and rewording.
- `CIA_RTM_IMPACT.csv`, `CIA_COUNTS.txt`.
- `GPT_REVIEW_DRAFT4.md`, `GPT_FIXES_CIA.md`, `OWNER_DECISIONS_2026-11-12.md`, `REV41_ADDENDUM.md`, `ENTITY_REGISTER.csv`.
- `Section_00.txt` to `Section_18.txt`: the locked text.

## What to check, scoped to what changed
1. **Each GPT finding (B1 to B4, S1 to S3, m1):** is it actually fixed, as GPT asked, in the proposed text and the assessment? Be hardest on B1. Check that:
   - the one-person exception covers the builder's own settings only;
   - the permanent marker is on the setting and on every figure using it;
   - the two-person rule applies with two or more people;
   - approval stays a distinct act;
   - consequential actions and keyed-value checks are excluded;
   - there are tests;
   - DS017 is narrowed;
   - DS001 is not silently extended (the owner answered it as question 5).
2. **Faithfulness to the owner's items 15 to 22.** Does any proposed text say more or less than he decided? Check especially:
   - item 16, the budget breakdown and the percentage bases;
   - item 18, ignoring a warning with an optional reason, and the reworded S06 §11 sentence;
   - item 19, CR-10 as a dependency;
   - item 21, the whole-job budget base.
3. **Relaxations.** Every place a locked condition is loosened must be stated as such: S06 §11's rationale, and PG-FR-025 / F-67 for one-person builders. Does any new text loosen, contradict or widen a locked requirement without saying so? Read the locked text around each changed or new item: S04 DS017, DS026, PG-DS-AC-05, 15, 16 and 17; S05 DS001, DS002 and DS006; S06 DS001, DS002, DS005 and DS006; Appendix B.
4. **Internal consistency of draft 5:**
   - counts (86 additions, 17 acceptance criteria, 10 version lines plus 1 reworded sentence, and the impact counts);
   - section 1 against sections 3, 4, 8, 10 and 11;
   - no leftover square brackets except the approval details;
   - no stale "pending" wording;
   - the amendment record of Section 06 naming the reworded sentence.
5. **The dependents list** (`CIA_RTM_IMPACT.csv`): are the new items' dependents covered? These are C22 (S06 §8, §9.1, §11, PG-AI-AC-13, PG-RS-AC-11, S13 §13.4), the S05 §3.3 budget breakdown, and the extended C04. Is anything plainly affected but missing?
6. **Boundaries:** no claim of implementation, acceptance or production readiness.

## Output
Write `out/CHECK_DRAFT5.md`:
- each finding classed BLOCKING, SHOULD FIX or MINOR, with evidence (file, section, ID or line) and a concrete fix;
- then a counts table, and a one-line view of whether draft 5 is ready to go to GPT for its targeted confirmation.

List every problem in one pass. Read-only: write only under `cia5check/out/`. No network. When done, reply with the counts and the BLOCKING and SHOULD FIX findings only.
