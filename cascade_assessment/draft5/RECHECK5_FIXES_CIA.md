# The scoped re-check of draft 5's fixes: each finding and how draft 5 handles it

Builder work (Claude), BUILDER-EXECUTED: NOT INDEPENDENT. The re-check is `RECHECK_DRAFT5.md` (INDEPENDENT READ-ONLY (agent)). It found 1 blocking, 6 should fix and 8 minor problems (one of them a note for the owner). It also found 4 of the earlier 22 findings only partly fixed, and one claim in `CHECK5_FIXES_CIA.md` wrong in part: §6.4's PG-DS-AC-15 summary had not been updated. That error is mine, and it is fixed below (N-3).

The owner answered two questions on 2026-11-13, recorded by 20:28 (owner record items 29 and 30):
- **G.** A second person who may approve only some kinds of record ends the exception for those kinds only.
- **H.** Every approval keeps a required reason.

Tools: `patch_data_v5d.py` (proposed text, on `cia_data.py`), `patch_src_v5.py` (assessment text), `FILL_v5.json` (§1 and §11). Counts after the fixes:
- 87 additions; 12 version lines and 2 reworded sentences, unchanged;
- 1,887 impact rows over 1,410 locked items (1,073 with an RTM ID), up from 1,880 and 1,405, from the dependents added under N-6.

| # | Finding | Draft 5 now |
| --- | --- | --- |
| N-1 (blocking) | S00 DS004 made the reason optional for every outcome, not only dismissals | **Fixed.** S00 DS004 now reads: "... dismissed or remains unresolved, with reasons and evidence; for a dismissal, who dismissed it and when are recorded, and the reason where one is given." Only dismissal changes, as item 23 decided. |
| N-2 | Item 24's return date not carried | **Fixed.** S06 DS006: "a deferred finding is raised again on the date the person chose (§6: next review date), or sooner if something material changes". This is also in PG-DS-AC-16, §6.4, §3 (the C22 row), §4 (the dismissal bullet) and §11 row B. |
| N-3 | Lines still said a keyed value always needs a second person; §6.4's AC-15 summary contradicted AC-15 | **Fixed.** §4 (the stricter control), §5 (the delivery row), §3 (C19, now citing items 25 and 29) and §6.4 (document values) all add "or, under the one-person exception, by that person, marked". The §6.4 line for criterion 15 is rewritten to match PG-DS-AC-15. |
| N-4 | §6.1 and the C22 row described one reworded sentence | **Fixed.** §6.1 says "one of the two sentences on dismissal (S06 §11, S00 §00.3)". The C22 row adds S00 §00.3 to Where and Nature, items 23 and 24 to From, and deferment to What. |
| N-5 | M01 and M03 not updated for item 27 | **Fixed.** M01: "except that a one-person builder approves his own budget and its breakdown, marked (item 27; S04 DS026, S05 DS006)". M03 drops "nothing added here" and points to the same items, and to the split of the breakdown into a setting (its structure) and baseline amounts. |
| N-6 | Dependents still missing | **Fixed.** Added to `CIA_RTM_IMPACT.csv` by `cia_data.py`: <ul><li>under C22: S13 checkpoint A (APG-S13-C0149) and the S06 test line (APG-S06-L0166);</li><li>under C04: PG-AI-AC-14 and the four S12 retention and security approval lines (APG-S12-C0090, C0126, L0137, L0161).</li></ul> The §3 S12 row now lists C04. The counts are regenerated (above). |
| N-7 | "Authorised person" unclear for someone who may approve only some kinds of record | **Fixed, by the owner's answer G (item 29).** S04 DS026 defines an authorised person per kind of record (for a keyed value, the person who may confirm it). Once a second person is authorised for a kind, the two-person rule applies to that kind and the exception continues for the others. PG-DS-AC-15 tests the bookkeeper case. §4, M10 and §11 (row G) record it. |
| n-1 | "Security cancellation" in neither list | **Fixed.** DS026 lists it as outside the exception. |
| n-2 | The three lists of excluded actions differ | **Fixed.** PG-DS-AC-05 and PG-DS-AC-15 now refer to "the consequential actions §18.3 lists as outside it, nor any action outside Profit Guardian", so DS026 holds the one list. PG-DS-AC-15 tests a short reason and the risks considered, and that an approval cannot be saved without the reason. |
| n-3 | §1's "Questions 1 to 4 are answered. All are answered ..."; "Next" differed from §10 | **Fixed.** §1 says "All questions are answered: 1 to 6; A to F ...; and G and H ...". §1 "Next" and §8 item 3 name the same scope for GPT's confirmation. |
| n-4 | "both ways (by stage and by trade)" against "or a mix" | **Fixed.** S05 DS006 says "in more than one way (for example by stage and by trade)". |
| n-5 | M10, §11 row B and C04's Where column not updated | **Fixed.** M10 cites items 15, 20, 25 to 27, 29 and 30, the S15 relaxation, and S04 DS017, DS022, DS026, S05 DS006, S06 DS001 and PG-DS-AC-05 and 15. Row B cites S06 DS005, DS006 and PG-DS-AC-16. C04's Where column adds S05 DS006 and S06 DS001. |
| n-6 | §6.6's new terms incomplete | **Fixed.** Added: "confirmed by the person who entered it"; authorised person (per kind of record); one-person exception; defer (a finding, until a chosen date). |
| n-7 | `GPT_FIXES_CIA.md` B1 row opened with the pre-fix statement | **Fixed.** It now says the exception first covered settings only and, after the owner's later answers, also the budget, retention steps and keyed values; never the consequential actions it lists as outside it. Items 29 and 30 are added. |
| n-8 (owner note) | Every approval needs a recorded reason under S15 checkpoint D, unlike warnings | **Put to the owner (question H). He chose to keep it required (item 30).** DS026 says so, and PG-DS-AC-15 tests it. |

The re-check's own note: its brief gave the number of changed items as 17 when there were 18, although its list was right. That miscount is mine.

## Check of these fixes

These fixes are wording and listing only. Each was checked by the builder against the rebuilt draft and CSVs (BUILDER-EXECUTED: NOT INDEPENDENT):
- no stale phrase is left;
- the counts are regenerated;
- the build reproduces from the locked package.

The re-check advised that "checking only those lines is enough before GPT; another full agent round would start to loop". So one narrow agent check of these lines runs before the pack goes to GPT, and no further round follows.
