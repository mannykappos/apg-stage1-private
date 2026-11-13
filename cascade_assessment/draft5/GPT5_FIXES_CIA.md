# GPT's targeted confirmation of draft 5: each finding and how it is fixed

Builder work (Claude), BUILDER-EXECUTED: NOT INDEPENDENT. GPT's review is `GPT_REVIEW_DRAFT5.md`, received from the owner at 20:52 on 2026-11-13: 0 blocking, 4 should fix, 2 minor. Its disposition: "READY FOR THE OWNER'S FORMAL APPROVAL once the four SHOULD FIX and two MINOR corrections are made; no blocking issue remains, and no further GPT or agent review is warranted." This was the last review round, by the owner's decision (owner record item 31), so these fixes are made without further review.

Tools: `patch_data_v5f.py` (proposed text), `patch_src_v5.py` and `FILL_v5.json` (assessment text), `build_entities.py` and `REV41_ADDENDUM.md` (register revision 4.1). The counts are unchanged: 87 additions; 12 version lines and 2 reworded sentences; 1,887 impact rows over 1,410 items.

| # | Finding | Fix |
| --- | --- | --- |
| S1 | "Raised again only when something material changes" might narrow S06 §9.1's triggers | S06 DS006 and PG-DS-AC-16 now name them: material new evidence, a meaningful status transition or an approved escalation condition. |
| S2 | S06 §14's "review evidence and reason" against the optional reason | S06 DS006 adds: "Where a dismissal is reviewed (§14: a dismissal is not automatically proof of a false positive), the reviewer considers the evidence and any reason given." This adds no third reworded sentence. S06 §14 is already a C22 dependent. |
| S3 | §1's summary lacked the per-kind qualifier | §1 now says "where exactly one person is authorised for the relevant kind of record", and cites question G. |
| S4 | Draft 7's 100-entity counts against revision 4.1's 114 | The M15 row (section 9) and `REV41_ADDENDUM.md` now say that draft 7's 100-entity counts are superseded by revision 4.1's 114. They also say the 14 new entities (E100 to E113) are later-release scope, each with its supply path in revision 4.1. Draft 7 itself is not edited, as GPT's alternative allowed. |
| m1 | Wrong 8-layer folder path | Corrected to `06_change_request_sources/8_layer_v0.1/`. |
| m2 | `build_entities.py` legend lacked class P, and the generator needed the survey file in its working directory | The legend adds class P. The generator now uses `SYSTEMS_SURVEY.csv` from its working directory if one is there; otherwise it uses the unchanged revision 4 copy in `../rev4_registers/`. The builder ran it in the pack layout and checked its outputs: `ENTITY_REGISTER.csv`, `M15_REGISTER_CHANGES.csv`, `CHART_DATA_PATHS.csv` and `FIELD_SUPPLY_ROUTES.csv` are byte-identical to those supplied. |

**A note on GPT's review.** Its finding table for B1 to m1 came through with an empty result column; the confirmations are in its text. GPT said it did not re-audit every unchanged requirement or rerun the agents' reading of all 2,712 RTM rows, and it named what it did check. That matches the targeted scope the prompt asked for.
