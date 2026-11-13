# Focused check of the cascade impact assessment, draft 5 (changes since draft 4)

**INDEPENDENT READ-ONLY (agent).** Design only; nothing is built. Scope: what changed between draft 4 and draft 5 (GPT's B1 to B4, S1 to S3, m1; owner record items 15 to 22; the new and changed proposed text; C22, the S05 §3.3 budget breakdown and the extended C04 in `CIA_RTM_IMPACT.csv`). Entity register rows were not re-checked, as the brief asked.

How it was checked: `CIA_PROPOSED_TEXT.csv` was diffed against `CIA_PROPOSED_TEXT_DRAFT4.csv` (6 new IDs: S05 DS006, S06 DS005, S06 DS006, PG-DS-AC-15, 16, 17; 12 changed rows). The counts were recomputed from the two CSVs. The locked text was read around every changed or new item, and all 19 sections were searched for related requirements ("dismiss", "rationale", "reason", "consequential", "approv", "segregation").

---

## BLOCKING

### B-1. The one-person exception contradicts its own boundary: it covers settings that S15 §15.11 names as consequential actions
- **Evidence.** S04 DS026 (`CIA_PROPOSED_TEXT.csv`; draft 5 line 588) says the exception "does not cover the human approval of consequential actions (Section 15 §15.11)". But the settings it does cover include things that S15 §15.11 (Section_15.txt lines 256 to 268) lists by name as consequential actions:
    - "Changes to authoritative financial rules or approved baselines". DS026 covers the Source Authority Register, which S04 §5 says must be "formally approved" before a source can update an authoritative fact. It also covers the financial policy status maps and the recognition policy a builder uses.
    - "Privileged access changes". DS026 covers users and roles where the platform does not supply them.
- S15 §15.4 (line 94) requires "Separate approval authority for consequential actions". So for these settings the exception does relax §15.4 and §15.11, but the draft never says so:
    - §4 (line 156) treats §15.4 as met by "a separate approve permission".
    - §1 (line 25) says "No other approval or check is weakened".
- GPT's suggested wording was "consequential **external** actions". Draft 5 dropped "external", and that is where the overlap comes from.
- C04's own impact rows list S15 L0133 and L0134 as "reviewed, no text change", so the conflict was looked at but not resolved.
- **Why blocking.** It is the B1 fix itself. The proposed locked text both grants and denies the same approvals, and a relaxation of S15 §15.4 and §15.11 goes unstated.
- **Fix.** In DS026, PG-DS-AC-05 and PG-DS-AC-15, and in §1, §4, §5 (Approvals row) and M10:
    1. Say that the exception does not cover consequential **external** actions. Name them from S15 §15.11 and S02 §7: purchase orders and commitments; contract, scope and material changes; claims and notices; retention release and security cancellation; correction or deletion of authoritative evidence.
    2. Say that changes to the builder's own settings which §15.11 counts as changes to authoritative financial rules or privileged access *are* covered. For a one-person builder, that person approves them, and the record carries the §15.11 workflow fields (proposed change, evidence, risks, approving authority, decision, timestamp, resulting state) and the marker.
    3. Add S15 §15.4 ("separate approval authority") and §15.11 to the stated relaxations in §4 and §1.
    4. Decide whether "approved baselines" (see S-5) are inside or outside the exception, and say which.

### B-2. Optional reasons also loosen Section 00's charter, and the draft does not say so
- **Evidence.** Section_00.txt line 33 (§00.3, Mission A) says: "Track whether an exposure was prevented, mitigated, realised, dismissed or remains unresolved, **with reasons and evidence**."
- S06 DS005 (the reworded §11 sentence) and DS006 make the reason for a dismissal optional.
- This S00 line is not in `CIA_RTM_IMPACT.csv` at all. S00's change items are only C05 and C21.
- §4's relaxation bullet (line 157), §1 (line 25: "Two locked checks are loosened") and the S06 amendment record name only S06 §11.
- After approval, v1.1 would hold two contradicting locked lines: S00 requiring reasons, and S06 making them optional.
- **Fix (small).** Add the S00 line to C22's dependents. Then do one of the following:
    - (a) reword it the same way ("with reasons where given, and evidence"). This adds Section 00 to the amended sections, with its version line(s), an amendment record and updated counts.
    - (b) state in §4 and §1 how the line reads after the change, and get the owner's confirmation.

  Option (a) is the cleaner one. Either way, §1 and §4 must stop saying that only one sentence of S06 §11 changes.

---

## SHOULD FIX

### S-1. The approval record leaves out the rationale GPT asked for; S15 checkpoint D requires recorded reasons
- GPT's B1 fix listed "approver permission, approval record, **rationale** and audit event".
- DS026 and PG-DS-AC-15 give only "permission, approval record and audit event".
- S15 checkpoint D (Section_15.txt line 386) says: "Privileged changes, consequential approvals ... require explicit authority, recorded reasons and traceable outcomes". Self-approval of users and roles is a privileged change.
- **Fix.** Add "and the reason for the change" to DS026 and PG-DS-AC-15, or state in §4 that it is optional. Add S15 checkpoint D (and S15 line 188, approval events) to C04's dependents.

### S-2. "Authorised person" is not defined, so the exception's trigger is unclear
- DS026, DS017, PG-DS-AC-05 and PG-DS-AC-15 turn on "exactly one" versus "two or more authorised people". The owner's words were "the only person using APG" (item 15).
- Take a builder with a site supervisor who only does site capture:
    - read one way, he becomes "two or more authorised people" and can no longer approve his own settings;
    - read the other way, he stays "exactly one".
- **Fix.** Define the term once in DS026: for example, people holding the permission to approve settings, or people with any APG access. Put the choice to the owner in plain words (owner preference). Add a test for the case where a second user without approval rights is added.

### S-3. What a one-person builder cannot do is not stated: approving retention events, confirming keyed values
- DS017 now says: "Preparing and approving stay separated as S02 §3.1 and PG-FR-025 require; the only exception ... settings". It also says the keyed-value check "has no exception".
- S02 §3.1 (line 121) is softer: it says "should be separated ... where practical and supported by policy", and only for consequential financial actions. So DS017 may be read as a strict separation for every kind of record.
- For a one-person builder that means:
    - a retention event he claims cannot be approved, released or received, even though Appendix B's roles are by role today, not by distinct person;
    - a value he keys from an uploaded document never counts (DS022).
- That is the lock-out the owner chose Option B to avoid, now for other records, and he has not been told.
- **Fix.**
    - Make DS017 say "where S02 §3.1 and PG-FR-025 require it".
    - State in §4, §5 and M10 what a one-person builder sees in these cases: for example, "awaiting a second person", with what to do, under decision 13.
    - Put the consequence to the owner in plain terms.

### S-4. PG-DS-AC-15 does not test all of the new rules
- Missing from PG-DS-AC-15 and from §6.4, line 318:
    - the switch from one person to two or more (earlier settings keep their marker; every new change needs the two-person rule);
    - a one-person builder accepting a product-owner default carries the marker (S06 DS001, item 20);
    - the exception does not reach "any other record" (for example a retention approval or a commitment);
    - the reason or rationale (S-1).
- **Fix.** Add these four cases.

### S-5. Making the budget breakdown "a setting" may bring approved baselines under the one-person exception
- S05 DS006 (line 633) ends: "It is a setting, approved as other settings are (Section 04 §18.3)".
- The per-part budget amounts are budget-baseline data (S05 §3.3: "budget baseline ID/version ... approved changes"). Approved baselines are a §15.11 consequential action.
- Who approves a baseline is still open: M01 decision 8 and M03 (draft lines 420, 422).
- **Fix.** Separate the two:
    - the *structure* of the breakdown (which parts exist, how costs map to them) is a setting under §18.3;
    - the part budgets are budget-baseline amounts under S05 §3.3, approved under M01 decision 8.

  Or state the widening plainly and put it to the owner.

### S-6. When the budget is broken down both ways, "the part a finding sits in" is undefined
- Item 16 decided "by stage, by trade or cost code, **or both**". S05 DS006 says "or a mix". S06 DS002 measures against "the part of the job the finding sits in".
- With a stage breakdown and a trade breakdown together, a finding sits in two parts. It is not said:
    - whether each breakdown must add up to the whole on its own;
    - which part's budget a percentage uses.
- **Fix.** Say that with both, each breakdown adds up to the whole-job budget on its own, and the finding is measured against each part it sits in, the grade applying as soon as any level is reached (item 7's "whichever hits first"). Add a test to §6.4. If that is more than the owner decided, ask him.

### S-7. The rewording also drops the rationale for *deferment*, which the owner did not decide
- Item 18 is about ignoring (dismissing) a warning. The reworded sentence S06 DS005 makes the rationale optional for "Dismissal/**deferment**".
- §4 (line 157) repeats this, and the S06 amendment record speaks only of "dismissing".
- **Fix.** Either keep "deferment ... must record rationale" and limit the relaxation to dismissal, or get the owner's one-line confirmation for deferment too. Also fix the grammar: "material findings ... it".

### S-8. Locked text plainly affected by C22 is missing from the dependents list
- None of these is in `CIA_RTM_IMPACT.csv`:
    - S06 §14 (line 244): "A dismissal is not automatically proof of false positive; review evidence and **reason**". This now has to work with no reason.
    - S06 §9 (lines 190 and 192): "Preserve dismissed ... findings for audit"; "Reopen when new evidence materially changes the situation".
    - S06 §16 test (line 332): "Verify dismissed findings preserve evidence and can reopen".
    - S13 §13.8 and checkpoint A (lines 196 and 298): a defect cannot be closed only because someone reports it complete. A one-tap ignore of a quality finding must not close or verify the defect record.
    - PG-AI-AC-14 ("Consequential actions cannot bypass human approval"). This bears on C04.
- **Fix.** Add these lines as C22 (and C04) dependents. Add one sentence to S06 DS006: "Dismissing a finding never closes, verifies or changes the record it is about (Section 13 §13.8)."

### S-9. Stale wording left over from before the owner's answers to questions 5 and 6
- Draft 5:
    - line 11: "questions 1 to 4 (owner record items 15 to 18)";
    - line 44: "his answers to this assessment's questions (items 15 to 18)";
    - line 86 (C10): "(question 5: whether a one-person builder accepts them himself)";
    - line 142: "Question 5 asks whether a one-person builder accepts them himself";
    - line 391: GPT is to confirm "the CR-10 comparison", which contradicts line 393 (no comparison now; it is a dependency).
- `GPT_FIXES_CIA.md`:
    - B1 row: "S06 DS001 ... is not silently extended: it is question 5 to the owner";
    - S3 row: "they are answered before approval". Both are now answered, and DS001 *is* extended, by item 20.
- `OWNER_DECISIONS_2026-11-12.md` item 15 heading still says "answer pending". GPT flagged this exact problem in the record.
- **Fix.**
    - Change each of these lines to the decided state.
    - Add items 19 to 22 to the "Also from the owner's answers" list in `GPT_FIXES_CIA.md`.
    - Cite item 20 in C10 (and C04) and in §4's one-person bullet.
    - Cite item 21 in C11's "From" column.

### S-10. The backfill count in §6.2 does not match the impact table
- §6.2 (line 219) says: "269 such items ... (184 paragraphs and 85 table rows)". The impact table has 249 untracked paragraphs, not 184.
- 184 is the same figure as in draft 4, although the paragraph count went from 248 to 249. It equals the 249 paragraphs minus the 65 that sit in the seven amended sections, but the draft never says that those 65 are left out, or why.
- **Fix.** Either give the figure's derivation (which 65 are excluded and how they get RTM rows instead), or correct it to the full count, and have `build_cia.py` compute the figure.

---

## MINOR
- **m-1.** Line 157 says "S06 §8's disposition field 'rationale'". The field is in S06 §6, the finding data contract (APG-S06-L0079).
- **m-2.** S06 DS001 says "Rule thresholds and windows ship with defaults", while S06 DS002 says "No default or suggested levels". Exclude the §8 severity levels from DS001 by name.
- **m-3.** §3:
    - the S06 row's disposition says only "the version line reworded", though its (2) includes the §11 sentence;
    - C11's Nature column holds "question 6";
    - C04's "From" column omits item 20.
- **m-4.** §4 (line 140, "Question 6 confirms the whole-job base") and §5 (line 178) never say what the base is: the job's approved budget.
- **m-5.** PG-DS-AC-17 and §6.4 (line 320) leave out the lifecycle-mapping tests that Appendix B lists (each state's S03 §13 label; "approved" is not "released"; "received" needs its matching bank transaction).
- **m-6.** PG-DS-AC-16 (finding dismissal) sits in S04 §19, the intake. It belongs with S06's criteria (§15).
- **m-7.** Items 16 and 17 say whether a builder's system holds stage or area budgets is confirmed from sample exports in discovery. S01 §3.7 (DS001 to DS006) does not name it.
- **m-8.** S05 DS001 does not itself say the main profit is labelled "forecast" (item 17). S03 §5's labelling arguably covers it; say so in one phrase.
- **m-9.** S06 DS006 says "the builder ... may ignore". For a builder with several people, say which permission may dismiss (S15 §15.4).
- **m-10.** S05 DS006 sits between DS002 and DS003, so the IDs are not in document order. This is cosmetic.

---

## Checked and found in order
- **B1, in part.** These are done:
    - the exception is limited to the builder's own settings in DS026;
    - the marker is on the setting and on "every figure, finding and report" (DS026, PG-DS-AC-05, PG-DS-AC-15);
    - the two-person rule applies with two or more people;
    - approval is its own act (permission, record, audit event);
    - keyed values are excluded;
    - PG-DS-AC-15 exists;
    - DS017 no longer lets roles combine freely;
    - DS001 is now extended openly, by owner item 20 (question 5), not silently.

  The boundary on consequential actions (B-1), the rationale (S-1) and the test gaps (S-4) are still open.
- **B2.** M15 is recorded as done (`REV41_ADDENDUM.md`), so DS009's "an annex" now matches the assessment. Rows were not re-checked, per the brief. The last 14 rows were closed by the builder only, and this is disclosed.
- **B3.** CR-10 is recorded as a dependency (§6.3, §8, §1), as GPT allowed and as item 19 decided.
- **B4.** Appendix B adds `currency` and `contract_ref` and shows the state mapping. PG-DS-AC-17 and the C18 fixtures are added; see m-5 for the remaining test gap.
- **S1.** M19 has an owner and closure evidence, and the S18 §9 gate is not claimed.
- **S2.** The 8-layer blueprint cannot be verified from this pack, because the folder is not among my inputs.
- **S3.** The approval condition is stated.
- **m1.** The draft number is fixed.
- **Item 21.** DS002 measures against the job's approved budget and each part's own budget.
- **Item 16.** DS006 and DS002 carry the decision: the builder chooses the breakdown; the parts add up to a whole-job budget that is always kept; Profit Guardian reports when they do not; it takes the breakdown from his system and asks only for what is missing; a finding not tied to a part is graded on the amount and the whole job only.
- **Item 18.** DS006 and PG-DS-AC-16 carry it: one tap, quick reasons that can be skipped, who and when recorded, the finding kept and raised again only on a material change. See S-7 and B-2.
- **Brackets.** Only `[number to be given at approval]`, `[approver]` and `[date]` remain in the proposed text. The §9 closure fields are placeholders by design.
- **Amendment record.** S06 DS003 names the reworded §11 sentence.
- **Boundaries.** No claim of implementation, acceptance or production readiness.

## Counts check (recomputed from the CSVs)

| Item | Draft 5 states | Recomputed | Result |
| --- | --- | --- | --- |
| Additions | 86 (40 paragraphs or bullets, 7 headings, 15 table rows, 17 acceptance criteria, 7 amendment records) | 86 (29 bullets + 11 paragraphs, 7, 15, 17, 7) | matches |
| Reworded | 10 version lines + 1 sentence | 10 + 1 (97 rows in all) | matches |
| Per-section additions (§3) | 7, 3, 16, 47, 5, 4, 4 | sum 86 | matches |
| Impact rows / distinct items | 1,806 / 1,347 (1,013 + 249 + 85) | 1,806 / 1,347 (1,013 + 249 + 85) | matches |
| Insertion anchors | 26 | 26 | matches |
| Per-section items touched and change items (§3) | as listed | identical (S15 also has M11, not shown) | matches |
| Backfill (§6.2) | 269 (184 paragraphs + 85 table rows) | 249 paragraphs touched without an RTM row | does not match (S-10) |

## Finding counts

| Class | Count |
| --- | --- |
| BLOCKING | 2 |
| SHOULD FIX | 10 |
| MINOR | 10 |

**Ready for GPT's targeted confirmation?** Not yet. Fix B-1 and B-2 (both small wording and scope changes; B-2 may add Section 00 as an eighth amended section) and the SHOULD FIX items first. S-2, S-3, S-5, S-6 and S-7 each need a short, plain-words question to the owner. After that, a scoped re-check of the changed lines is enough before it goes to GPT; no full round is needed.
