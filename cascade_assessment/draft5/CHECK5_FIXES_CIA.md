# The independent check of draft 5: each finding and how draft 5 handles it

Builder work (Claude), BUILDER-EXECUTED: NOT INDEPENDENT. The check is `CHECK_DRAFT5.md` (INDEPENDENT READ-ONLY (agent)): 2 blocking, 10 should fix, 10 minor. The fixes were made in two passes:
- the first, with the owner's answers A to F of 2026-11-13 (owner record items 23 to 28), before this file was written;
- the second while writing this file, which found five findings only partly carried (S-1, S-3, S-5, S-6, S-8). They are marked "completed in the second pass" below.

The tools are `patch_data_v5b.py` and `patch_data_v5c.py` (proposed text, on `cia_data.py`), `patch_src_v5.py` (assessment text), and `assemble.py` (the section table's disposition column). Counts after the fixes: 87 additions, 12 version lines and 2 reworded sentences, 1,880 impact rows over 1,405 locked items.

## Blocking

| # | Finding | Draft 5 now |
| --- | --- | --- |
| B-1 | The one-person exception covers settings that S15 §15.11 calls consequential actions, while saying it covers none; the relaxation of §15.4 and §15.11 is unstated | **Fixed.** S04 DS026 states the relaxation openly: for the exception's cases only, S15 §15.4's separate approval authority and §15.11's approval of changes to financial rules, approved baselines, privileged access and retention release. It names what stays outside: purchase orders and supplier commitments; contract, scope, specification or material changes; claims, notices and commercial communications; deletion or correction of authoritative evidence; and any action outside Profit Guardian. Each approval keeps its own permission, approval record (with its rationale and the risks considered, §15.11) and audit event. The same boundary is in §1, §4, §5 (the approvals row), PG-DS-AC-05 and PG-DS-AC-15. "Approved baselines" are inside, by the owner's answer E (item 27). |
| B-2 | Making the reason optional also loosens S00 §00.3 ("with reasons and evidence"), unstated | **Fixed, by the owner's answer A (item 23).** S00 §00.3's line is reworded the same way (S00 DS004). Section 00 becomes the eighth amended section, with its amendment record (S00 DS001) and version lines (S00 DS002, DS003). §1 and §4 name both reworded sentences. |

## Should fix

| # | Finding | Draft 5 now |
| --- | --- | --- |
| S-1 | The approval record leaves out the rationale; S15 checkpoint D needs recorded reasons | **Fixed; completed in the second pass.** DS026 and PG-DS-AC-15 give the approval record "with its rationale and the risks considered". The second pass added S15 checkpoint D (APG-S15-C0193) and the approval-events line (APG-S15-L0094) to C04's dependents. |
| S-2 | "Authorised person" not defined | **Fixed, by the owner's answer D (item 26).** DS026 defines it: a person with the permission to approve. A capture-only or view-only user does not count. PG-DS-AC-15 tests that adding such a user does not end the exception. |
| S-3 | What a one-person builder cannot do (retention approvals, keyed values) is unstated, and DS017 reads stricter than S02 §3.1 | **Fixed, by the owner's answer C (item 25); completed in the second pass.** The exception covers the approval steps of a retention event and the confirmation of values he keyed, each marked (DS026, DS022, DS017, PG-DS-AC-15). So the lock-out does not arise. The second pass changed DS017 to "where Section 02 §3.1 and PG-FR-025 require it". |
| S-4 | PG-DS-AC-15 misses four cases | **Fixed.** PG-DS-AC-15 and §6.4 now test: the switch to two people (earlier records keep their marker, new ones need the two-person rule); accepting a product default with the marker; no exception for a purchase order, contract or scope change, claim or notice, or deletion of evidence; the rationale on every approval. |
| S-5 | Calling the budget breakdown "a setting" may bring approved baselines under the exception | **Fixed; completed in the second pass.** The owner decided (answer E, item 27) that a one-person builder approves his own budget and its breakdown, marked; for larger builders M01 decision 8 still decides. The second pass separated the two in S05 DS006: the structure of the breakdown is a setting (S04 §18.3); each part's amount is part of the approved budget baseline (S05 §3.3), approved as the budget and its changes are; under the one-person exception, that person approves both, marked. |
| S-6 | With a breakdown both ways, "the part a finding sits in" is undefined | **Fixed, by the owner's answer F (item 28); completed in the second pass.** S06 DS002 measures against each part, applies the more serious grade and names the triggering part. The second pass added to S05 DS006 that each breakdown adds up to the whole on its own, and added the case to §6.4's severity tests. |
| S-7 | The rewording also drops the reason for deferment, which the owner had not decided; grammar | **Fixed, by the owner's answer B (item 24).** Deferment is treated like dismissal (§4, S06 DS005). S06 DS006 and PG-DS-AC-16 say a deferment is recorded the same way. The grammar is fixed: "Dismissal/deferment of a material finding must record who dismissed or deferred it and when". |
| S-8 | Locked text affected by C22 is missing from the dependents | **Fixed; completed in the second pass.** S06 §9, §14 and §16, PG-AI-AC-09 and PG-AI-AC-14, and S13 §13.8 are C22 dependents. §4 says ignoring a finding never closes a defect. The second pass added the sentence the check asked for to S06 DS006: "Dismissing or deferring a finding never closes, verifies or changes the record it is about (Section 13 §13.8)". It also added the case to PG-DS-AC-16 and §6.4. |
| S-9 | Stale wording from before questions 5 and 6 were answered | **Fixed.** Lines 11, 44, 86, 142 and 391 now give the decided state. Items 20 and 21 are cited in C10, C04 and C11. Item 15's heading in the owner record is fixed. `GPT_FIXES_CIA.md`'s B1 and S3 rows are updated, and items 19 to 28 are added there. |
| S-10 | The backfill count (269 = 184 + 85) does not match the impact table | **Fixed.** The figure is now computed from `CIA_COUNTS.txt` (`fill_v5.py`): 337 items, 252 paragraphs and 85 table rows. |

## Minor

| # | Finding | Draft 5 now |
| --- | --- | --- |
| m-1 | The "rationale" field is in S06 §6, not §8 | **Fixed.** §4 says "S06 §6's finding data contract field "rationale" (APG-S06-L0079)". |
| m-2 | S06 DS001's "defaults" conflicts with DS002's "no default" | **Fixed.** DS001 excludes the §8 financial severity levels by name: they have no default, and the builder sets them (DS002). |
| m-3 | §3: the S06 row says only "the version line reworded"; C11's Nature column holds "question 6"; C04 omits item 20 | **Fixed.** `assemble.py` now writes, per section, how many version lines and how many relaxation sentences are reworded (S00 and S06 show both). C11's Nature column is "addition (new design and new code)", and its From column gives items 7, 9, 16, 21 and 28. C04's From column gives items 15, 20 and 25 to 27. |
| m-4 | §4 and §5 never say what the whole-job base is | **Fixed.** Both say: the job's approved budget (item 21). |
| m-5 | PG-DS-AC-17 and §6.4 leave out Appendix B's lifecycle-mapping tests | **Fixed.** Both now include: each state shows its S03 §13 label; "approved" is not "released"; "received" needs its matching bank transaction. |
| m-6 | PG-DS-AC-16 sits in S04 §19, not with S06's criteria | **Kept, with a pointer.** All 17 of this change request's criteria stay together in S04 §19, so the series is not split. S06 DS006 now names PG-DS-AC-16 and where it is kept. |
| m-7 | S01 §3.7 does not name the stage or area budget check | **Fixed.** S01 DS002 adds "including whether each system holds the budget broken down by stage, trade or area (Section 05 §3.3)". |
| m-8 | S05 DS001 does not say the main figure is labelled "forecast" | **Fixed.** DS001 adds "the forecast figures labelled as forecasts (Section 03 §5)". |
| m-9 | S06 DS006 does not say who may dismiss when there are several people | **Fixed.** "A person whose role permits it (role-based permissions, Section 15 §15.4)". No new permission is invented: the role settings decide. |
| m-10 | S05 DS006 sits between DS002 and DS003 | **Not changed (cosmetic).** IDs are given in the order the items were added, and renumbering would ripple through the cross-references. It is disclosed here. |

## Not yet checked independently

The second pass and the minor fixes are wording only and have not been checked independently. The check agent advised "a scoped re-check of the changed lines is enough before GPT; no full round is needed". That re-check is the next step.
