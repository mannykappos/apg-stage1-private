# Final narrow check of the fixes to the re-check of draft 5

**INDEPENDENT READ-ONLY (agent).** Design only; nothing is built. No input file was changed.

Scope: the 15 findings of `RECHECK_DRAFT5.md` (N-1 to N-7, n-1 to n-8), the fixes claimed in `RECHECK5_FIXES_CIA.md`, owner record items 29 and 30, and only the lines that changed.

How it was checked:
- `CIA_DRAFT5.md` was diffed against `CIA_DRAFT5_AS_RECHECKED.md`. 27 lines changed, and 2 rows were added (§11 rows G and H).
- `CIA_PROPOSED_TEXT.csv` was diffed against its re-checked copy. 7 rows changed (S00 DS004, S04 DS026, PG-DS-AC-05, 15 and 16, S05 DS006, S06 DS006). There are no new IDs. Every proposed text appears word for word in the draft's §12.
- `CIA_RTM_IMPACT.csv` was diffed against its re-checked copy. 7 rows were added, and none was removed or changed. Each new row's locked text was matched to its `Section_NN.txt` line.
- The counts were recomputed from the CSVs.

---

## 1. Verdicts on the 15 findings

| # | Verdict | Evidence |
| --- | --- | --- |
| N-1 | **Fixed** | S00 DS004 now reads: "...dismissed or remains unresolved, with reasons and evidence; for a dismissal, who dismissed it and when are recorded, and the reason where one is given." The other four outcomes keep "with reasons and evidence". This is the re-check's own wording. S00 DS001 ("on tracking dismissed exposures with reasons") is now accurate. |
| N-2 | **Fixed** | S06 DS006: "a deferred finding is raised again on the date the person chose (§6: next review date), or sooner if something material changes". "next review date" is in S06 §6, Finding data contract (Section_06.txt line 154). The same rule is in PG-DS-AC-16, §6.4 line 321 ("raised again on its chosen date"), the C22 row ("a deferred one on its chosen date"), §4 line 158 ("returns on the date chosen, or sooner on a material change (item 24)") and §11 row B. |
| N-3 | **Fixed** | §4 line 160: "...or, under the one-person exception, that person's own, marked "confirmed by the person who entered it" (item 25)". §5 line 187 and §6.4 line 327 add the same. C19 row: "...or, under the one-person exception, by that person, marked", "owner record items 25 and 29". §6.4 line 320 is rewritten to match PG-DS-AC-15 ("per kind of record", "a short reason", "no exception for the consequential actions §18.3 lists as outside it"). No line still says that a keyed value always needs a second person. |
| N-4 | **Fixed** | §6.1 line 195: "one of the two sentences on dismissal (S06 §11, S00 §00.3; owner-approved relaxations)". The C22 row adds "S00 §00.3 (one sentence reworded)" to Where, "and S00 §00.3 ("with reasons and evidence", for dismissals)" to Nature, "items 18, 23 and 24" to From, and "or defer" to What. For a wording point in What, see F-4. |
| N-5 | **Fixed** | M01 adds "except that a one-person builder approves his own budget and its breakdown, marked (owner record item 27; S04 DS026, S05 DS006)". M03 drops "nothing added here". It now says "added here only for the one-person builder ... and the split of the breakdown into a setting (its structure) and baseline amounts (S05 DS006)". |
| N-6 | **Fixed** | 7 rows were added: C22 APG-S13-C0149 (Section_13.txt line 298), C22 APG-S06-L0166 (Section_06.txt line 332), C04 PG-AI-AC-14 (Section_06.txt line 278), and C04 APG-S12-C0090, C0126, L0137 and L0161 (Section_12.txt lines 181, 253, 275 and 323). Each locked text matches its line word for word. Every ID that appears more than once has the same text each time. The §3 rows now say: S12 "34 / C04, C08, C14, C18"; S13 "27"; S06 "112 / C04, ...". The RTM itself is not among the inputs, so the IDs could be checked only for consistency within the CSV. |
| N-7 | **Fixed as claimed; sibling lines left (F-1)** | DS026: "An authorised person, for a kind of record, is a person with the permission to approve that kind of record (for a keyed value, to confirm it)"; "once a second person is authorised for a kind of record, every new record or change of that kind follows the two-person rule, and the exception continues for the other kinds". PG-DS-AC-15 adds the bookkeeper case. §4 line 157, M10 and §11 row G carry it. But DS017, DS022 and PG-DS-AC-05 still state the test for the whole builder. See F-1. |
| n-1 | **Fixed in DS026** | DS026's outside list ends "...deletion or correction of authoritative evidence; security cancellation)". The §4 and §5 lists do not have it yet. See F-3. |
| n-2 | **Fixed** | PG-DS-AC-05 now says: "never the consequential actions §18.3 lists as outside it, nor any action outside Profit Guardian". PG-DS-AC-15 says: "a short reason, the risks considered and its audit event, and cannot be saved without the reason; the exception never lets that person take any consequential action §18.3 lists as outside it, nor any action outside Profit Guardian". DS026 now holds the one list. |
| n-3 | **Fixed** | §1 line 34: "All questions are answered: 1 to 6; A to F ...; and G and H ...". The scope in §1 line 35 ("Next") and §8 item 3 (line 393) is now word for word the same: "the one-person exception and the relaxations, the two reworded sentences, the retention definition, the M15 register revision 4.1". |
| n-4 | **Fixed** | S05 DS006: "in more than one way (for example by stage and by trade)". |
| n-5 | **Fixed** | M10 now cites: "items 20 and 25 to 27 ... item 29 ... (item 30) ... relaxes S15 §15.4 and §15.11 ... S04 DS017, DS022 and DS026, S05 DS006, S06 DS001, PG-DS-AC-05 and 15". Row B cites "S06 DS005, DS006; PG-DS-AC-16". C04's Where column now includes "S05 DS006; S06 DS001". |
| n-6 | **Fixed** | §6.6 adds: "confirmed by the person who entered it"; "authorised person (per kind of record)"; "one-person exception"; "defer (a finding, until a chosen date)". |
| n-7 | **Fixed** | The B1 row in `GPT_FIXES_CIA.md` now reads: "As first drafted it covered settings only; after the owner's later answers it also covers the budget, retention steps and keyed values ..., and never the consequential actions of S15 §15.11 that it lists as outside it." It also has a new bullet for items 29 and 30. One stale summary is left in the same file. See F-2. |
| n-8 | **Fixed (put to the owner)** | Item 30 says to keep the reason required. DS026: "Every approval, also under the exception, records a short reason (Section 15 checkpoint D)". This matches Section_15.txt line 386, which requires "recorded reasons". PG-DS-AC-15 tests "cannot be saved without the reason". For one owner-awareness remainder, see F-5. |

**Summary:** 14 fixed (one only in DS026, with the other lists handled as F-3). One is fixed as claimed but left sibling lines inconsistent (N-7, logged as F-1). None is "not fixed". No claim in `RECHECK5_FIXES_CIA.md` is wrong.

---

## 2. Owner items 29 and 30

| Item | Carried exactly? | Note |
| --- | --- | --- |
| 29 (the two-person rule applies per kind of record; Dave still approves his own settings, budget and retention steps, marked) | **Yes in DS026, PG-DS-AC-15, §4, §6.4, M10, §11 row G and C19; less than decided in three proposed texts** | DS026 matches the decision, and so does the bookkeeper case in AC-15. But DS017, DS022 and PG-DS-AC-05 still count authorised people across the whole builder. Read literally, they contradict item 29. See F-1. |
| 30 (every approval, including his own, records a short reason; warnings stay reason-optional) | **Yes** | DS026 and PG-DS-AC-15 require it. §4 line 157: "only warnings may be ignored or deferred without one". M10: "every approval keeps a reason (item 30)". §11 row H. Nothing makes a warning's reason required. The required "risks considered" is not new: it rests on the locked S15 §15.11 (line 272, "relevant risks"). But the owner was asked only about the reason. See F-5. |

---

## 3. New findings (changed lines only)

### BLOCKING

None.

### SHOULD FIX

**F-1. The per-kind rule of item 29 is in DS026 but not in DS017, DS022 or PG-DS-AC-05. Read literally, these three still contradict it.**
- PG-DS-AC-05 (on setup answers): "with two or more authorised people, never by the person who entered them; with exactly one, by that person".
    - Take item 29's case: Dave, plus Sue, who may only confirm keyed values. That makes two authorised people, so this test would stop Dave approving his own settings.
    - PG-DS-AC-15 says the opposite: "a bookkeeper who may confirm keyed values ends it for keyed values, not for settings or the budget".
    - Two acceptance criteria would then disagree.
- S04 DS022: "Under the one-person exception (§18.3), a builder with exactly one authorised person confirms the values he keyed himself".
    - Take a second person who may approve settings but not confirm keyed values. Read for the whole builder, this ends Dave's self-confirmation, and nobody else may confirm.
    - Item 29 says the exception continues for that kind.
- S04 DS017: "except under the one-person exception of §18.3 (a builder with exactly one authorised person)".
- DS026's per-kind definition would settle each case if it were read into these lines. But these are proposed locked texts and a test, so the plain words should match.
- **Fix** (wording only; no count changes, no owner question):
    - PG-DS-AC-05: "with two or more people authorised to approve setup answers, never by the person who entered them; with exactly one, by that person".
    - DS022: "Under the one-person exception (§18.3), where exactly one person is authorised to confirm keyed values, that person confirms the values he keyed himself".
    - DS017: "(exactly one person authorised for that kind of record)".
    - Optional, plain-words lines: in §3 C04 What and §1 line 24, add "for each kind of record".

### MINOR

- **F-2. Stale pointers.**
    - The From column of the §3 C04 row (line 81) still ends "owner record items 15, 20 and 25 to 27". Items 29 and 30 change C04, and C19 already cites 29.
    - `GPT_FIXES_CIA.md`, items 19 to 28 bullet: "deferment treated like dismissal (24)". This is the wording N-2 replaced in §4.
    - **Fix.** C04 From: "items 15, 20, 25 to 27, 29 and 30". GPT_FIXES: "deferment recorded like dismissal, returning on its chosen date (24)".
- **F-3. Two lists of excluded actions leave out security cancellation, which DS026 now names (n-1).**
    - §4 line 157 (changed this round): "The other consequential actions of §15.11 keep their approval: purchase orders and supplier commitments; ...; deletion or correction of authoritative evidence; and no action outside Profit Guardian". Security cancellation is missing.
    - §5 Approvals row (line 183): "never the other consequential actions of S15 §15.11 (purchase orders, contract or scope changes, claims and notices, deletion of evidence)".
    - S15 §15.11 lists "Retention release and security cancellation" as one item (Section_15.txt line 264). So a list that leaves out cancellation can be read as letting it in with retention release.
    - **Fix.** Add "security cancellation" to both lists, or replace each list with "the actions S04 DS026 lists as outside it".
- **F-4. The C22 row says a finding can be deferred "in one tap".**
    - The row reads: "the builder may ignore (dismiss) or defer any finding in one tap". S06 DS006 gives one tap only for ignoring. Item 24 decided that the reason is optional, not that deferring takes one tap. A deferment also needs a chosen date.
    - **Fix.** "may ignore (dismiss) any finding in one tap, or defer it to a chosen date, with a reason optional".
- **F-5. Owner awareness only; no text change.** Question H asked only about a reason. DS026 and PG-DS-AC-15 also require "the risks considered" on every approval, including Dave's own. This is right to keep: S15 §15.11 says approval workflows must identify "relevant risks" (line 272). Tell the owner in one plain sentence that this can be a short note, so it does not surprise him.

---

## 4. Counts check (recomputed from the CSVs)

| Item | Draft states (§1, §2, §3, §6.2) | Recomputed | Result |
| --- | --- | --- | --- |
| Additions | 87 (40 paragraphs or bullets, 7 headings, 15 table rows, 17 acceptance criteria, 8 amendment records) | 87 (11 paragraphs + 29 bullets, 7, 15, 17, 8) | matches |
| Reworded | 12 version lines and 2 sentences (S00 L0017, S06 C0112) | 12 + 2 (S00 DS004 on L0017, S06 DS005 on C0112); 101 rows in all | matches |
| Per section, additions (reworded) | 00 1 (3), 01 7 (2), 02 3 (2), 03 16 (2), 04 47 (1), 05 5 (1), 06 4 (2), 11 4 (1) | the same | matches |
| Impact rows | 1,887 (§2 line 49; §6.2 line 225) | 1,887 (1,880 + 7) | matches |
| Distinct items | 1,410 (1,073 with an RTM ID, 252 paragraphs, 85 table rows) (§1 line 28; §2; §6.2) | 1,410 = 1,073 + 252 + 85. The S12 C0126 row was already there under C18, so 7 rows add 5 items. | matches |
| Insertion anchors | 27 | 27 | matches |
| Items touched and change items per section (§3) | S06 112 (C04 added), S12 34 (C04 added), S13 27; the rest unchanged | the same (S15 also has M11, not shown, as before) | matches |
| Backfill (§6.2) | 337 (252 + 85) | 337; all new rows have RTM IDs | matches |

All counts match. The fixes in F-1 to F-4 change no count.

## 5. Boundaries

No changed line claims implementation, acceptance or production readiness. Every new owner item ends "No build", and the draft still authorises none.

---

## 6. Finding counts

| Class | Count |
| --- | --- |
| BLOCKING | 0 |
| SHOULD FIX | 1 (F-1) |
| MINOR | 4 (F-2 to F-5; F-5 is owner awareness only) |

| Re-check findings (N-1 to N-7, n-1 to n-8) | Count |
| --- | --- |
| Fixed | 14 |
| Fixed as claimed, with sibling lines left (N-7, logged as F-1) | 1 |
| Partly / not fixed / claim wrong | 0 |

**Ready for GPT?** Yes, once F-1 to F-4 are made.
- They are wording changes to about eight lines.
- No owner question is needed, and the counts do not change.
- The builder can confirm them by text search.

No further agent round is needed. The findings have shrunk from 1 blocking and 6 should fix to 0 blocking and 1 should fix. Another round would loop.
