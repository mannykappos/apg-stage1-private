# Brief: scoped re-check of the fixes to draft 5 of the cascade impact assessment

You are a fresh, independent agent. Label your work **INDEPENDENT READ-ONLY (agent)**. This is design only: nothing is built. Do not edit any input.

An earlier independent check of draft 5 (`in/CHECK_DRAFT5.md`) found 2 blocking, 10 should-fix and 10 minor problems. It advised: "Once these are fixed, a scoped re-check of the changed lines is enough before GPT; no full round is needed." The builder (Claude) has fixed them; `in/CHECK5_FIXES_CIA.md` says how, finding by finding. The product owner answered six questions along the way (owner record items 23 to 28 in `in/OWNER_DECISIONS_2026-11-12.md`; also read items 15 to 22).

## Inputs (under `<WORKSPACE>/cia5recheck/in/`)
- `CIA_DRAFT5.md` (now) and `CIA_DRAFT5_AS_CHECKED.md` (what the earlier check read).
- `CIA_PROPOSED_TEXT.csv` (now) and `CIA_PROPOSED_TEXT_AS_CHECKED.csv`. 17 proposed items changed or are new: APG-S00-DS001 to DS004, APG-S01-DS002, APG-S04-DS017, DS022, DS026, PG-DS-AC-05, 15, 16, 17, APG-S05-DS001, DS006, APG-S06-DS001, DS002, DS005, DS006. (Diff the two files yourself to confirm the list.)
- `CIA_RTM_IMPACT.csv`, `CIA_COUNTS.txt`, `GPT_FIXES_CIA.md`, `CHECK_DRAFT5.md`, `CHECK5_FIXES_CIA.md`, `OWNER_DECISIONS_2026-11-12.md`.
- `Section_00.txt` to `Section_18.txt`: the locked text.

## What to check (scoped: the changed lines only, no full round)
1. **Each of the 22 findings:** is it actually fixed as `CHECK5_FIXES_CIA.md` claims, in the proposed text and in the assessment? Quote the evidence. Mark each: fixed / partly / not fixed / claim wrong.
2. **Faithfulness to the owner's items 20, 21 and 23 to 28.** Does any changed text say more or less than he decided?
3. **New problems in the changed lines only:** a locked condition loosened without saying so; a contradiction between changed lines and other parts of the draft; a wrong section reference (check each § reference in the changed items against the locked text); stale wording.
4. **Counts:** recompute from the CSVs (87 additions; 12 version lines and 2 reworded sentences; 1,880 impact rows over 1,405 items, 1,068 with an RTM ID, 252 paragraphs and 85 table rows) and compare with the draft's §1, §3 and §6.2.
5. **Boundaries:** no claim of implementation, acceptance or production readiness.

Do not re-open matters outside the changed lines unless a change created them.

## Output
Write `<WORKSPACE>/cia5recheck/out/RECHECK_DRAFT5.md`:
- a title and the label INDEPENDENT READ-ONLY (agent);
- a table of the 22 findings with your verdict and evidence;
- new findings, classed BLOCKING / SHOULD FIX / MINOR, each with evidence (file and line or ID) and a concrete fix;
- the counts check;
- a finding-count table.
Write plainly, in short sentences. Reply with the finding counts and the path.
