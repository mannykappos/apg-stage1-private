# Brief: narrow final check of the fixes to the re-check of draft 5

You are a fresh, independent agent. Label your work **INDEPENDENT READ-ONLY (agent)**. Design only; nothing is built. Do not edit any input.

A scoped re-check (`in/RECHECK_DRAFT5.md`) found 1 blocking, 6 should-fix and 8 minor problems (N-1 to N-7, n-1 to n-8). The builder fixed them; `in/RECHECK5_FIXES_CIA.md` says how. The owner answered two more questions (owner record items 29 and 30 in `in/OWNER_DECISIONS_2026-11-12.md`). This is the last check before GPT: the re-check said "checking only those lines is enough before GPT; another full agent round would start to loop". Keep strictly to the fixed lines.

## Inputs (under `<WORKSPACE>/cia5final/in/`)
- `CIA_DRAFT5.md` (now) and `CIA_DRAFT5_AS_RECHECKED.md`; `CIA_PROPOSED_TEXT.csv` and `..._AS_RECHECKED.csv`; `CIA_RTM_IMPACT.csv` and `..._AS_RECHECKED.csv`; `CIA_COUNTS.txt`.
- `RECHECK_DRAFT5.md`, `RECHECK5_FIXES_CIA.md`, `GPT_FIXES_CIA.md`, `OWNER_DECISIONS_2026-11-12.md`, `Section_00.txt` to `Section_18.txt`.

## What to check
1. For each of N-1 to N-7 and n-1 to n-8: is it fixed as `RECHECK5_FIXES_CIA.md` claims? Quote the evidence. Verdict: fixed / partly / not fixed / claim wrong.
2. Are items 29 and 30 carried exactly as decided, no more and no less?
3. Did any fix create a new contradiction, an unstated loosening of locked text, a wrong section or RTM reference, or stale wording? Diff the files to find the changed lines; look only there and at what they directly contradict.
4. Recompute the counts from the CSVs and compare with §1, §3 and §6.2 (87 additions; 12 version lines and 2 reworded sentences; 1,887 impact rows over 1,410 items, 1,073 with an RTM ID).

## Output
Write `<WORKSPACE>/cia5final/out/FINAL_CHECK_DRAFT5.md`: a verdict table, any new findings (BLOCKING / SHOULD FIX / MINOR, with evidence and a concrete fix), the counts check, and a finding-count table. Short, plain sentences. Reply with the counts and the path.
