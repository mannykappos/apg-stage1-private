# Scoped re-check of the fixes to draft 5 of the cascade impact assessment

**INDEPENDENT READ-ONLY (agent).** Design only; nothing is built. No input file was changed.

Scope: the 22 findings of `CHECK_DRAFT5.md`, the fixes described in `CHECK5_FIXES_CIA.md`, owner record items 20, 21 and 23 to 28, and the changed lines only.

How it was checked:
- `CIA_PROPOSED_TEXT.csv` was diffed against `CIA_PROPOSED_TEXT_AS_CHECKED.csv` by ID. There are 4 new IDs (APG-S00-DS001 to DS004) and 14 changed rows (S01 DS002; S04 DS017, DS022, DS026; PG-DS-AC-05, 15, 16, 17; S05 DS001, DS006; S06 DS001, DS002, DS005, DS006). That is **18 items, not 17**. The brief's own list also names 18, so the "17" in the brief is a miscount. Nothing was found missing.
- `CIA_DRAFT5.md` was diffed against `CIA_DRAFT5_AS_CHECKED.md`. Every proposed text in the CSV appears word for word in the draft's §12.
- Each § reference in the changed items was looked up in the locked `Section_NN.txt` files.
- The counts were recomputed from the two CSVs.

---

## 1. The 22 earlier findings

| # | Verdict | Evidence |
| --- | --- | --- |
| B-1 | **Fixed** | S04 DS026 now says: "for these cases only, to Section 15 §15.4's separate approval authority and §15.11's approval of changes to financial rules, approved baselines, privileged access and retention release". It also names what stays outside ("purchase orders and supplier commitments; contract, scope, specification or material changes; claims, notices and commercial communications; deletion or correction of authoritative evidence ... no action outside Profit Guardian"). The same boundary is in §1 (line 25), §4 (line 157), §5 Approvals row (line 183), PG-DS-AC-05 and PG-DS-AC-15. Approved baselines are inside, per item 27. Small gaps: M10 is not updated (n-5), and "security cancellation" is in neither list (n-1). |
| B-2 | **Partly** | The S00 line is reworded (S00 DS004). Section 00 is the eighth amended section, with S00 DS001 to DS003. §1 (line 24) and §4 (line 158) name both sentences. But the rewording makes reasons optional for all five outcomes, not just for dismissal. See N-1. |
| S-1 | **Fixed** | DS026: "approval record (with its rationale and the risks considered, Section 15 §15.11)". PG-DS-AC-15: "every approval is recorded with its own permission, rationale and audit event". `CIA_RTM_IMPACT.csv` has C04 rows for APG-S15-C0193 (checkpoint D) and APG-S15-L0094 (approval events). |
| S-2 | **Fixed** | DS026: "An authorised person is a person with the permission to approve; a user who may only capture or view does not count." PG-DS-AC-15: "a user who may only capture or view does not end the exception". One edge case is still open: a person who can approve only some kinds of record. See N-7. |
| S-3 | **Partly** | The proposed text is fixed. DS017 says "where Section 02 §3.1 and PG-FR-025 require it". DS022 and DS026 carry item 25 (retention steps and keyed values, each with its marker). But four lines in the assessment still say a keyed value always needs a second person. See N-3. |
| S-4 | **Partly** | PG-DS-AC-15 now covers all four missing cases: the switch to two people; accepting a product default; never a purchase order, contract or scope change, claim or notice, or deletion of evidence; and rationale. `CHECK5_FIXES_CIA.md` also says §6.4 was updated. It was not. Line 320 still reads "...and no exception for consequential actions or keyed values (15)", which now contradicts item 25. See N-3. |
| S-5 | **Fixed** | S05 DS006: "The structure of the breakdown ... is a setting ... (Section 04 §18.3); the amount of each part is part of the approved budget baseline (§3.3) and is approved as the budget and its changes are. Under the one-person exception ..., that person approves both, marked." But M01 and M03 are now stale. See N-5. |
| S-6 | **Fixed** | S05 DS006: "each breakdown adds up to the whole-job approved budget on its own". S06 DS002: "measured against each; the more serious grade applies, and the finding says which part triggered it". §6.4 line 325 adds the test. For a wording point, see n-4. |
| S-7 | **Fixed** | Item 24 covers deferment. The grammar is fixed in S06 DS005: "Dismissal/deferment of a material finding must record who dismissed or deferred it and when". S06 DS006 and PG-DS-AC-16 add "A deferment is recorded in the same way". But item 24's return date is not carried. See N-2. |
| S-8 | **Partly** | These are now in C22's dependents: S06 §9 (L0095, L0096), §14 (L0122), §16 (L0147 to L0156), PG-AI-AC-09, PG-AI-AC-14 and S13 §13.8 (H0098 to C0111). DS006 has the sentence "never closes, verifies or changes the record it is about (Section 13 §13.8)". PG-DS-AC-16 and §6.4 line 321 carry it. Still missing: S13 checkpoint A (Section_13.txt line 298); the S06 test line "Verify dismissed findings preserve evidence and can reopen" (Section_06.txt line 332, in §17, not §16); and PG-AI-AC-14 as a C04 dependent (it is only under C22). See N-6. |
| S-9 | **Fixed** | Lines 11, 44, 87 (C10), 143 and 393 now give the decided state. C11's From column cites items 16, 21 and 28. C04's From column cites 15, 20 and 25 to 27. Item 15's heading in the owner record now reads "decided 13:01". `GPT_FIXES_CIA.md` S3 row and items 19 to 28 are updated. The fixes left some new stale wording. See N-4, n-3 and n-7. |
| S-10 | **Fixed** | §6.2 line 220: "337 such items ... (252 paragraphs and 85 table rows)". This matches the impact table: 252 + 85 = 337. |
| m-1 | **Fixed** | Line 158: "S06 §6's finding data contract field "rationale" (APG-S06-L0079)". This matches Section_06.txt line 158. |
| m-2 | **Fixed** | S06 DS001: "(the financial severity levels of §8 are not among them: they have no default, and the builder sets them, DS002)". |
| m-3 | **Fixed** | §3 rows S00 and S06 say "and one sentence reworded (owner-approved relaxation)". C11's Nature column is "addition (new design and new code)". C04's From column includes item 20. |
| m-4 | **Fixed** | Line 141: "the job's approved budget (owner record item 21)". Line 179: "the whole-job base being the job's approved budget (question 6)". |
| m-5 | **Fixed** | PG-DS-AC-17 and §6.4 line 322: "each state shows its S03 §13 label, "approved" is not "released", and "received" needs its matching bank transaction". |
| m-6 | **Fixed (kept, with a pointer)** | S06 DS006: "Acceptance criterion PG-DS-AC-16 tests this (it is kept with this change request's other criteria in Section 04 §19)". This is acceptable. |
| m-7 | **Fixed** | S01 DS002: "including whether each system holds the budget broken down by stage, trade or area (Section 05 §3.3)". |
| m-8 | **Fixed** | S05 DS001: "the forecast figures labelled as forecasts (Section 03 §5)". |
| m-9 | **Fixed** | S06 DS006: "a person whose role permits it (role-based permissions, Section 15 §15.4)". This matches Section_15.txt line 85, under §15.4. |
| m-10 | **Not changed, disclosed** | This is cosmetic, and the disclosure is acceptable. |

**Summary:**
- 16 fixed.
- 2 kept or not changed, with an acceptable disclosure (m-6, m-10).
- 4 partly fixed (B-2, S-3, S-4, S-8).

None is "not fixed", and no claim is wrong outright. One claim is wrong in part: `CHECK5_FIXES_CIA.md` says §6.4 was updated for S-4, and it was not.

---

## 2. Faithfulness to the owner's items 20, 21 and 23 to 28

| Item | Carried as decided? | Note |
| --- | --- | --- |
| 20 (accepting a product default, same marker) | Yes | S06 DS001; DS026 ("including the acceptance of a product default (Section 06 §5.1)"); PG-DS-AC-15. |
| 21 (whole-job base = approved budget) | Yes | S06 DS002; §4 line 141; §5 line 179. |
| 23 (Section 00 changed "the same way") | **Says more than decided** | The decision was about dismissed exposures. S00 DS004 drops the required reasons for all five outcomes. See N-1. |
| 24 (deferment: reason optional; "the warning returns on the date chosen") | **Says less than decided** | The optional reason is carried. The return date is not, and the text implies the opposite. See N-2. |
| 25 (retention approvals and keyed values, each marked) | Yes in the proposed text | DS017, DS022, DS026 and PG-DS-AC-15. The assessment still contradicts it in places (N-3). |
| 26 (only people allowed to approve count) | Yes | DS026. Edge case in N-7. |
| 27 (one-person builder approves his budget and breakdown; M01 decision 8 for larger builders) | Yes in the proposed text | DS026 and S05 DS006. M01 and M03 are not updated (N-5). |
| 28 (both breakdowns; the more serious grade; the triggering part named) | Yes | S06 DS002; S05 DS006; §6.4 line 325. |

---

## 3. New findings (changed lines only)

### BLOCKING

**N-1. The Section 00 rewording drops the required reasons for every outcome, not only for dismissals.**
- Locked text (Section_00.txt line 33, APG-S00-L0017): "Track whether an exposure was prevented, mitigated, realised, dismissed or remains unresolved, **with reasons and evidence**."
- S00 DS004: "...prevented, mitigated, realised, dismissed or remains unresolved, with who decided and when, **the reason where one is given**, and evidence."
- The reason now becomes optional when an exposure is recorded as prevented, mitigated or realised. The owner decided only about dismissal (item 23: "S00 §00.3 requires dismissed exposures to be tracked 'with reasons and evidence'... change it the same way").
- The narrower description in S00 DS001 ("on tracking dismissed exposures with reasons"), in §1 line 24 and in §4 line 158 hides the wider loosening. So a locked condition is loosened without saying so, which is the same class of problem as B-2.
- **Fix.** Reword S00 DS004 so that only dismissal changes, for example: "Track whether an exposure was prevented, mitigated, realised, dismissed or remains unresolved, with reasons and evidence; for a dismissal, who dismissed it and when are recorded, and the reason where one is given." No owner question is needed: this is exactly what item 23 decided. The counts do not change.

### SHOULD FIX

**N-2. Item 24's "the warning returns on the date chosen" is not carried, and the text implies the opposite.**
- Item 24: "who and when are recorded, and the warning returns on the date chosen".
- S06 DS006 says a dismissed finding "is raised again only when something material changes", then: "A deferment is recorded in the same way." §4 line 158 says: "Deferment is treated like dismissal (item 24)." PG-DS-AC-16 and §6.4 line 321 test only "a deferment recorded the same way".
- Read together, a deferred warning comes back only on a material change, never on its date.
- **Fix.** In S06 DS006, add: "A deferred finding is raised again on the date the person chose, or sooner if something material changes." This fits S06 §6, "next review date" (Section_06.txt line 154). Add the case to PG-DS-AC-16 and §6.4 line 321. In §4, say "Deferment is recorded like dismissal, and returns on its chosen date (item 24)."

**N-3. Stale lines still say a keyed value always needs a second person, and §6.4 contradicts PG-DS-AC-15.**
- §6.4 line 320 (PG-DS-AC-15 summary): "...and no exception for consequential actions or keyed values (15)". Since item 25 the exception covers keyed values, and it does not cover all consequential actions (retention release and approved baselines are inside).
- §6.4 line 327: "Document values: a keyed value from an uploaded document counts only after a second person confirms it."
- §4 line 160: "One control is stricter than the locked text: a value a person keys from an uploaded document needs a second person's confirmation (S04 DS022)."
- §5 Delivery row (line 187): "until extraction exists, values are keyed and confirmed by a second person".
- §3 C19 row (line 96): "...is confirmed by a second person with the verifier role" | "addition, stricter than S04 §18".
- **Fix.** In each place, add "(or, under the one-person exception, by that person, marked 'confirmed by the person who entered it')". Rewrite the line 320 summary to match PG-DS-AC-15 as it now stands.

**N-4. Stale lines still describe one reworded sentence and leave Section 00 out of C22.**
- §6.1 line 195: "a reworded line: a version line, or S06 §11's one sentence on dismissal ...; the only locked text that changes". This contradicts §6.2 line 223 (two sentences).
- §3 C22 row (line 99):
    - Where: "S06 §11 (one sentence reworded, one paragraph added); PG-DS-AC-16". This leaves out S00 §00.3 (S00 DS004 is C22).
    - Nature: "relaxation of S06 §11" only.
    - From: "owner record item 18" only. Items 23 and 24 are missing.
    - What: does not mention deferment.
- **Fix.** §6.1: "a version line, or one of the two sentences on dismissal (S06 §11, S00 §00.3)". C22 row: add S00 §00.3 (S00 DS004) to Where and Nature; add items 23 and 24 to From; add "or defer" to What.

**N-5. M01 and M03 are not updated for item 27, and M03 is now wrong.**
- M01 (line 422) still lists "who approves a baseline (8)" as open, with no word of the one-person case.
- M03 (line 424): "Baselines: locked in S05 §5.1 and §10 and 8-layer decision 8; **nothing added here**". But S04 DS026 now lets a one-person builder approve his own budget and its breakdown. S05 DS006 now says each part's amount is part of the approved budget baseline. And §4 relaxes S15 §15.11 for "approved baselines".
- **Fix.** M01: "who approves a baseline (8) — except that a one-person builder approves his own, marked (owner record item 27; S04 DS026)". M03: replace "nothing added here" with a pointer to S04 DS026, S05 DS006 and item 27.

**N-6. Dependents still missing after S-8 and item 25.**
- From S-8:
    - S13 checkpoint A (Section_13.txt line 298: "A defect cannot be marked verified and closed solely because someone reports the work complete");
    - S06 line 332 ("Verify dismissed findings preserve evidence and can reopen", in §17);
    - PG-AI-AC-14 as a C04 dependent (it is now only under C22).
- New from item 25 (the exception now covers the approval steps of a retention event and relaxes §15.11 "retention release"). These Section 12 retention-approval lines are not C04 dependents:
    - Section_12.txt line 181 ("Consequential release, cancellation ... requires authorised human approval and an audit trail");
    - line 253 (checkpoint C, APG-S12-C0126: listed under C18 only);
    - line 275 ("Consequential security/retention release ... authorised approval and evidence are recorded");
    - line 323 (approval-path tests).
- A one-person approval still meets "authorised human approval", so nothing here is loosened. But the S18 §6 assessment must list them.
- **Fix.** Add these rows to `CIA_RTM_IMPACT.csv`: S13 checkpoint A and S06 line 332 under C22; PG-AI-AC-14 and the four S12 lines under C04. Add C04 to the §3 S12 row, and regenerate the counts.

**N-7. "Authorised person" is unclear for someone who can approve only some kinds of record.**
- DS026: "An authorised person is a person with the permission to approve". DS022 uses a separate "verifier role" for keyed values.
- Take a builder who adds a bookkeeper with only the verifier role, or with approval rights for keyed values only. It is not said whether:
    - the exception ends for everything, which would lock the owner out of approving his own settings and budget, because nobody else may approve them; or
    - it ends only for the kinds of record the bookkeeper may approve or confirm, so he could still confirm his own keyed values while a verifier exists.
- Item 26 says "a second person with approval rights". It does not settle this case.
- **Fix.** In DS026, define the term per kind of record, for example: "a person allowed to approve, or confirm, that kind of record; the exception ends for a kind once a second person holds that right for it". Add one PG-DS-AC-15 case. If Claude cannot take this as the plain reading of item 26, ask the owner one short question with this example.

### MINOR

- **n-1.** S15 §15.11 lists "Retention release **and security cancellation**" as one item (Section_15.txt line 266). DS026 relaxes "retention release" but names security cancellation in neither list. Add "security cancellation" to DS026's list of what stays outside.
- **n-2.** The lists of what stays outside differ:
    - PG-DS-AC-05 and PG-DS-AC-15 are shorter than DS026's. They leave out supplier commitments, specification or material changes, commercial communications, correction of evidence and security cancellation.
    - PG-DS-AC-15 also leaves out "an action outside Profit Guardian".
    - PG-DS-AC-15 tests "rationale" but not "the risks considered" that DS026 requires.

  Align the three lists, or say "the actions DS026 lists".
- **n-3.** §1, line 34: "Questions 1 to 4 are answered. All are answered, including six more (A to F)..." reads as stale and drops questions 5 and 6. Say "All questions are answered: 1 to 6, and A to F...". Line 35 ("Next") still lists "the Option B wording ... the M15 register revision 4.1", while line 393 lists "the one-person exception ... and the relaxations". Make them match.
- **n-4.** S05 DS006 says "Where the builder breaks it down both ways (by stage and by trade)". But the same paragraph allows "by stage, by trade or cost code, by area, or a mix". Say "in more than one way (for example by stage and by trade)".
- **n-5.** These pointers are not updated:
    - M10 (line 431) still cites only item 15, DS017 and DS026. It does not mention the S15 relaxation, items 20 and 25 to 27, DS022 or S05 DS006. B-1's fix listed M10.
    - The §11 row B (line 463) points only to S06 DS005. Add DS006 and PG-DS-AC-16.
    - The C04 row's Where column (line 81) leaves out S05 DS006 and S06 DS001.
- **n-6.** §6.6's new terms list only "approved by the person who entered it". Add: "confirmed by the person who entered it"; "authorised person"; "one-person exception"; and "defer (a finding)".
- **n-7.** The `GPT_FIXES_CIA.md` B1 row still opens with the pre-fix statement that the exception "does not cover consequential actions (S15 §15.11), the second-person check of keyed values (S04 DS022) or other records". It then contradicts this later in the same cell. Reword the opening.
- **n-8.** Owner awareness only; no text change. DS026 now requires a rationale and the risks considered for every approval, including a one-person builder approving his own settings, budget and retention steps. This rests on the locked S15 checkpoint D ("recorded reasons", Section_15.txt line 386) and is right to keep. It differs from his "reason optional" choice for warnings (item 18). Tell him in one plain sentence before approval, so it does not surprise him.

---

## 4. Counts check (recomputed from the CSVs)

| Item | Draft states (§1, §2, §3, §6.2) | Recomputed | Result |
| --- | --- | --- | --- |
| Additions | 87 (40 paragraphs or bullets, 7 headings, 15 table rows, 17 acceptance criteria, 8 amendment records) | 87 (29 bullets + 11 paragraphs, 7, 15, 17, 8) | matches |
| Reworded | 12 version lines and 2 sentences (S00 L0017, S06 C0112) | 12 + 2 (101 rows in all) | matches |
| Version lines per section | 2 each in S00 to S03; 1 each in S04, S05, S06, S11 | the same | matches |
| Additions per section (§3) | S00 1, S01 7, S02 3, S03 16, S04 47, S05 5, S06 4, S11 4 | the same (sum 87) | matches |
| Reworded per section (§3, in brackets) | 3, 2, 2, 2, 1, 1, 2, 1 | the same (sum 14) | matches |
| Sections amended | 8 (00, 01, 02, 03, 04, 05, 06, 11) | 8 | matches |
| Impact rows / distinct items | 1,880 / 1,405 (1,068 + 252 + 85) | 1,880 / 1,405 (1,068 + 252 + 85) | matches |
| Insertion anchors | 27 | 27 | matches |
| Items touched and change items per section (§3) | as listed (S00 29; S06 111; S13 26; S15 99; ...) | the same (S15 also has M11, not shown, as before) | matches |
| Backfill (§6.2, M19) | 337 (252 paragraphs + 85 table rows) | 252 + 85 = 337 | matches |

N-6's fix will add rows, so the counts will need to be regenerated after it. N-1 changes no count.

## 5. Boundaries

No changed line claims implementation, acceptance or production readiness. Line 9 still states that the document is design only and authorises no build. The only "implemented" in the changed proposed text is the locked S06 phrase "implemented action from verified outcome".

---

## 6. Finding counts

| Class | Count |
| --- | --- |
| BLOCKING | 1 (N-1) |
| SHOULD FIX | 6 (N-2 to N-7) |
| MINOR | 8 (n-1 to n-8) |

| Earlier findings | Count |
| --- | --- |
| Fixed | 16 |
| Kept or not changed, with disclosure (m-6, m-10) | 2 |
| Partly fixed (B-2, S-3, S-4, S-8) | 4 |
| Not fixed | 0 |

S-9's leftover stale wording is logged as new findings (N-4, n-3, n-7), not counted as a partial fix.

**Ready for GPT's targeted confirmation?** Not yet, but it is close.
- Every item is a wording or listing fix.
- N-1 needs no owner question.
- N-7 may need one short owner question.

Once these are fixed, a check of just those lines is enough. No further full agent round is needed. The findings have shrunk from 2 blocking and 10 should fix to 1 small blocking point and 6 should fix, all wording. A further round after this one would start to loop.
