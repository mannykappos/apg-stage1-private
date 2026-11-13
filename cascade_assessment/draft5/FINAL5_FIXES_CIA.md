# The narrow final check of draft 5: each finding and how draft 5 handles it

Builder work (Claude), BUILDER-EXECUTED: NOT INDEPENDENT. The check is `FINAL_CHECK_DRAFT5.md` (INDEPENDENT READ-ONLY (agent)): 0 blocking, 1 should fix, 4 minor (one of them a note for the owner). It found 14 of the re-check's 15 findings fixed. The fifteenth (N-7) was fixed as claimed, but it left three sibling lines inconsistent (F-1). Tools: `patch_data_v5e.py` (proposed text) and `patch_src_v5.py` (assessment text). The counts are unchanged: 87 additions; 12 version lines and 2 reworded sentences; 1,887 impact rows over 1,410 items.

| # | Finding | Draft 5 now |
| --- | --- | --- |
| F-1 | DS017, DS022 and PG-DS-AC-05 still counted authorised people across the whole builder, against item 29 | **Fixed** as the check worded it. PG-DS-AC-05: "with two or more people authorised to approve setup answers". DS022: "where exactly one person is authorised to confirm keyed values, that person confirms the values he keyed himself". DS017: "(exactly one person authorised for that kind of record)". The §3 C04 row now says the rule is per kind of record. |
| F-2 | Stale pointers | **Fixed.** C04's From column cites items 15, 20, 25 to 27, 29 and 30. In `GPT_FIXES_CIA.md`, item 24 now reads "deferment recorded like dismissal, returning on its chosen date". |
| F-3 | §4 and §5 lists left out security cancellation | **Fixed.** Both lists name it. |
| F-4 | The C22 row said a deferral takes "one tap" | **Fixed.** "may ignore (dismiss) any finding in one tap, or defer it to a chosen date, with a reason optional". |
| F-5 (owner note) | Every approval also records "the risks considered", which the locked S15 §15.11 requires; the owner was asked only about the reason | **Told to the owner** with the pack: this is a short note, for example "small change, no effect on other jobs". It is a locked requirement, so it is kept. No text change. |

## No further agent round

These fixes are wording only, as the check said ("No further agent round is needed"). The builder checked them against the rebuilt draft (BUILDER-EXECUTED: NOT INDEPENDENT):
- each changed phrase is present;
- the old phrases are gone;
- the counts are unchanged;
- the build reproduces from the locked package.

GPT's targeted confirmation covers them. Three agent rounds on draft 5 (the check, the re-check and this final check) are enough, and a fourth would be a loop.
