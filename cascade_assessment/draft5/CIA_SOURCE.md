# APG change request: Data Supply System and Data Readiness, cascade impact assessment (draft 5)

Nov 13, 2026 · prepared by Claude (builder) for Emmanuel (product owner)

**Status.** This is the Section 18 §6 cascade impact assessment for one change request, made of two parts that go through Section 18 together (data supply decision 11 in the decisions document `APG_Data_Supply_Decisions`):
- the data supply design (draft 7);
- the Data Readiness Change Request (revision 4).

It is design only. It authorises no build, changes no locked file, and claims nothing is implemented, accepted or ready for production. Stage 2 stays not authorised, and under S04 §20 no production feature code starts before the Section 01 Discovery Exit Report is signed off. It is the builder's work (BUILDER-EXECUTED: NOT INDEPENDENT).

Draft 5 answers GPT's review of draft 4 (4 blocking, 3 should fix, 1 minor; each finding and its fix in `GPT_FIXES_CIA.md`) and carries the owner's answers of 2026-11-13 to questions 1 to 6 and ten further decisions (owner record items 15 to 30), and the fixes of three independent agent checks of draft 5 (`CHECK_DRAFT5.md`, `RECHECK_DRAFT5.md`, `FINAL_CHECK_DRAFT5.md`; fixes in `CHECK5_FIXES_CIA.md`, `RECHECK5_FIXES_CIA.md`, `FINAL5_FIXES_CIA.md`; see section 8). Draft 4 answered three independent checks (INDEPENDENT READ-ONLY (agent)): the first, of draft 1, found 5 blocking, 19 should fix and 21 minor; the second, a scoped re-check of draft 2, found 2 blocking, 11 should fix and 20 minor new points; the third, a focused check of draft 3, found no blocking point, and 6 should fix and 7 minor wording points. A fix is claimed for each (`CHECK1_FIXES_CIA.md`, `CHECK2_FIXES_CIA.md`, `CHECK3_FIXES_CIA.md`). GPT reviewed those fixes with the rest of draft 4.

## 1. In plain words

The locked blueprint (Sections 00 to 18, version 1.0) already says most of what the data supply design needs:
- one intake with strict controls;
- nothing invented when data is missing;
- warnings when data is stale.

What it does not yet say is how APG makes sure it can always get the data, and how it tells the builder what it needs. This change request adds that.

- **What changes in the blueprint.** 87 pieces of text are added to 8 of the 19 sections (00, 01, 02, 03, 04, 05, 06 and 11), which go from version 1.0 to 1.1. The full proposed wording is in section 12.
    - Most of it goes into Section 04, the intake: the ways of supplying data; the readiness record that tells the builder what is missing; the rule that every message says what to do; setup questions; and 17 new acceptance criteria (PG-DS-AC-01 to 17), the tests each part must pass.
    - The locked words that change are the version lines ("Version 1.0" becomes "Version 1.1") in the eight sections, and two sentences on dismissing a finding: Section 06 §11 and Section 00 §00.3 no longer require a reason (your decisions on question 4 and question A). Nothing else already locked is reworded or removed.
- **What it does not change.** No existing financial definition: recognised margin, forecast final margin and the others keep their meaning. Two locked checks are loosened, each by your decision and stated as such (section 4): a builder with only one person allowed to approve may approve his own settings, budget and retention steps and confirm the values he keyed, each marked as done by the person who entered it (questions 1, 5, C, D and E), which also loosens, for those cases only, the security section's separate approval of financial rules, baselines, access and retention release; and a builder may ignore or defer a warning without giving a reason, with who and when still recorded (questions 4, A and B). No other approval or check is weakened.
- **Two things that do change results, later, each under its own build:** the builder's own severity levels change how findings are graded (every rule has a severity mapping, S06 §5.1); and moving all records onto one intake (C02) changes which records some rules can use, so some results will change. Both are explained in section 4.
- **What is new money logic.** One addition is a new way of showing a figure: the extras and variations panel splits the job's one main profit figure into the original build and each extra, and the parts add up exactly to it. That needs its own tests (section 4); you confirmed it (question 3).
- **What else it touches.** Every locked paragraph and table row that the changes bear on was read for knock-on effects: <<N_ITEMS>> of them, in Sections 00 to 18, each listed by its ID or position. None needs new wording.
- **The package around the blueprint needs work after approval:**
    - the requirements matrix (RTM), the master list that gives every requirement an ID;
    - the terminology register;
    - the manifest, the list of files with their fingerprints (hashes);
    - the package checker, which today rejects any section that is not version 1.0 (shown in section 6.7).
- **Your answers** (section 11). <<OPEN_QUESTIONS>>
- **Next.** <<NEXT>> Only after approval are the version 1.1 files made, and each build still needs its own authorisation.

## 2. Change request identification

| Field (Section 18 §6 and the package's CR template) | Entry |
| --- | --- |
| Change Request ID | Provisional reference APG-CR-DSR. The owner gives it its number in his change-request list at formal approval. His list uses CR-01 to CR-08 and CR-10. |
| Requester | Emmanuel, product owner: the data readiness direction of 2026-11-11 and the one-data-supply-system direction of 2026-11-12. Prepared by Claude (builder). |
| Date | 2026-11-13 (draft 5). |
| What it rests on | The data supply design, draft 7 (2026-11-12). The Data Readiness Change Request, revision 4, with its registers, and its entity register revision 4.1 (2026-11-13, the M15 row-level check: 114 entities, `REV41_ADDENDUM.md`). Revision 4 passed GPT's scoped re-check with nothing blocking; its three smaller points were fixed by Claude afterwards and have not been checked independently since. The owner's decisions record of 2026-11-12 and 13 (`OWNER_DECISIONS_2026-11-12.md`, "owner record item N" below), with his answers to this assessment's questions and decisions (items 15 to 30). GPT's review of draft 4. The data supply decisions document (`APG_Data_Supply_Decisions`, "data supply decision N" below). |
| Affected locked sections (amended) | Sections 00, 01, 02, 03, 04, 05, 06 and 11, each version 1.0 LOCKED, to become 1.1 (hashes below). |
| Affected locked sections (dependents, no text change) | Sections 07, 08, 09, 10, 12, 13, 14, 15, 16 and 17. Section 18 too: its text is unchanged, but its package assets change. |
| Package assets affected | `MASTER_REQUIREMENTS_TRACEABILITY_MATRIX.csv`, `CROSS_SECTION_TERMINOLOGY_REGISTER.md`, `manifest.json`, `validate_handoff_package.py`, `README_HANDOFF.md`, `CLAUDE_HANDOFF_INSTRUCTIONS.md`, `SOURCE_SECTION_INVENTORY.json`, `PACKAGE_VALIDATION_REPORT.txt`, and a new controlled change register (section 6.7). |
| Related, outside the locked blueprint | The 8-layer design blueprint v0.1 is a design baseline, not locked; its 02 §2.11 and 11 §11.2 and §11.6 are dependents (the blueprint is in the pack, `06_change_request_sources/APG_8_LAYER_DESIGN_BLUEPRINT_v0.1/`). The owner's own change requests CR-02, CR-05, CR-07, CR-08 and CR-10 (section 6.3). The defect change request for DC-1 to DC-13, raised after stage 1. |
| Exact requirement IDs | `CIA_RTM_IMPACT.csv` lists every insertion point, reworded line and dependent: by RTM ID, or by paragraph or table row where the RTM has no row. It has <<N_ROWS>> rows over <<N_ITEMS>> distinct locked items: <<N_RTM>> with an RTM ID, <<N_PARA>> paragraphs and <<N_TROW>> table rows without one (tables and rows are numbered from 0, as python-docx counts them; row 0 is a table's header, so body rows start at 1). `build_cia.py` reads the spans from the section documents themselves, not only from the RTM. It fails if an anchor is wrong, or if an insertion point is not the true end of its block. |

The locked package was checked before use:
- every file's SHA-256 matches its manifest;
- the manifest digest (dad3fa91…d89c) matches the package's validation report;
- `validate_handoff_package.py` passes (27 files, 19 sections, 2,712 RTM rows);
- the package archive `Anchor_Profit_Guardian_Blueprint_v1.0.zip` has SHA-256 487becab…d960.

| Section | Locked file version | SHA-256 (first 16 characters) |
| --- | --- | --- |
| 00 | v1.0 LOCKED | 17c35c013dddb7cf |
| 01 | v1.0 LOCKED | 5964235f08c0ee6a |
| 02 | v1.0 LOCKED | 794b1e1a51786cf2 |
| 03 | v1.0 LOCKED | 0870a3fd72e8d755 |
| 04 | v1.0 LOCKED | 322546fc9f2444ad |
| 05 | v1.0 LOCKED | d73364a7ba398735 |
| 06 | v1.0 LOCKED | f152c1f6d4a8d497 |
| 11 | v1.0 LOCKED | 6b2913b6f8bc4d38 |

## 3. The change items

Each item names what it adds and where. The full wording of every addition, and the locked text it follows, is in section 12.

- **Addition:** new text that adds a requirement without changing an existing one.
- **Clarification:** new text that says how an existing requirement is met.
- **Implementation obligation:** the locked text already requires it, and the change request only records it.

| Item | What it adds | Where | Nature | From |
| --- | --- | --- | --- | --- |
| C01 | One intake for every way in. A Level 1 way in for every entity this blueprint governs, needing no builder software. A new way in never changes a rule. A way in that isn't built is never offered. | S04 §18.1 (new); PG-DS-AC-01, 02, 03, 06, 11; S02 PG-FR-027 | addition | draft 7, "Purpose and the rule", "Architecture" |
| C02 | Bring the 24 kinds of the second delivery loop under the Section 04 intake. A regression baseline is taken first, and the move has its own change request. The two direct writes and the in-code authority register enter the intake as new record kinds (first-release items 3 and 4) without waiting for the move. | S04 §20 (new bullet) | implementation obligation: S04 §3, §5, §8, §9, §11 and PG-DI-AC-01 to 06 already require it | draft 7, release A item 1 |
| C03 | Controls for each new channel: email sender checks; file scanning and safe parsing; entry screens that never edit a held record. | S04 §18.2 (new); PG-DS-AC-07, 08, 13 | addition | draft 7, intake stage table |
| C04 | Setup questions for the source registry, the Source Authority Register, the cost-code map (each match confirmed by a person), users and roles, the financial policy settings a builder owns, and the rule settings. Each is versioned and approved. Where exactly one person may approve a kind of record, he approves his own records of that kind (settings, budget, retention steps) and confirms his keyed values, each permanently marked; the two-person rule applies to each kind once a second person may approve it. | S04 §18.3 (new); S04 DS017, DS022; S05 DS006; S06 DS001; PG-DS-AC-05, 15 | addition, with one owner-approved relaxation for one-person builders: the separation of preparing and approving (PG-FR-025, F-67) and, for those cases, S15 §15.4 and §15.11 (section 4) | draft 7, "Setup questions"; data supply decision 8; owner record items 15, 20, 25 to 27, 29 and 30 |
| C05 | Eight logical entities and a data-gap lifecycle added to the domain model; the controlled entity register as an annex. | S03 §2 and §13 (table rows), S03 §2 (paragraph) | addition | revision 4, entity register |
| C06 | The field register and the field-coverage report, as a gate. | S03 §2 (paragraph), S04 §20, PG-DS-AC-12 | addition | revision 4, field-level coverage |
| C07 | The readiness record (and its scope), the onboarding data checklist, the missing-data list, nudges, the life of a data gap, and how an insight that is not switched on is shown. | S04 §14.1 (new); PG-DS-AC-09, 10; S02 PG-FR-026 | addition | draft 7, "Data readiness" |
| C08 | Decision 13: whenever a check or figure cannot be fully done, say what is missing, why it matters and what to do. | S04 §14.2 (new); PG-DS-AC-14; S02 PG-FR-026 | addition | owner record item 6 |
| C09 | Freshness limits per insight, starting from owner-approved thresholds, each with an owner and rationale. | S04 §14.1 | clarification of S04 §14 ("decision-aware freshness thresholds") and S16 §5 | data supply decision 10 |
| C10 | Detection-rule thresholds ship with owner-approved defaults, visible to the builder, which his approver accepts; a one-person builder accepts them himself, marked (question 5). | S06 §5.1 (new paragraph) | clarification of S06 §5.1 ("configurable within approved governance boundaries") | data supply decision 9 |
| C11 | Severity levels for the money side of a finding, set by the builder at setup: an amount, a percentage, or both, whichever is reached first. The builder chooses whether a percentage is measured against the whole job, the part of the job the finding sits in, or both; the parts are those of his own budget breakdown (by stage, trade or area), which add up to the whole-job budget. No defaults. Safety and quality classification stays separate. | S06 §8 (new paragraph); S05 §3.3 (new paragraph) | addition (new design and new code) | owner record items 7, 9, 16, 21 and 28 |
| C12 | (Folded into C04.) | | | |
| C13 | Extras and variations shown separately, as a breakdown of the one authoritative forecast. The cost of extra work is attributed to its instruction or variation and counted once. The builder records what happens after a variation is rejected. | S11 §8 and §8.2 (new); S05 §3.2 and §6; S03 §6.2 | addition, including one new financial view (section 4); confirmed by the owner (question 3) | owner record items 4, 5 and 17 |
| C14 | The approved budget and the authoritative forecast's final cost and margin first; each item that is not final beside them, by category, with its what-if effect never added in. | S05 §3.2 (new bullet) | addition (new presentation across budget and profit); confirmed by the owner (question 3) | owner record items 11 and 17 |
| C15 | Site capture devices enrolled; the shared-phone user recorded; the place not assumed reliable; workers see what was recorded about them; its privacy settled before it is built. | S04 §18.2 | addition; its privacy design waits for CR-05 | draft 7, Level 2 |
| C16 | Data supply questions added to Section 01 discovery, including site capture as an early discovery item. | S01 §3.7 (new) | addition | draft 7, "What discovery must answer" |
| C17 | How the data releases fit the build phases. | none (section 6.3) | no text change | draft 7, "Not proven yet" |
| C18 | Retention events through the intake, with a field definition that adds the currency and the associated contract (S03 §11.1, §10.1) and maps the states to S03 §13. | the field register and Appendix B; PG-DS-AC-17 | addition to a controlled register | GPT's re-check of revision 4; GPT's review of draft 4 |
| C19 | A value a person keys from an uploaded document, where no extraction exists, is confirmed by a second person with the verifier role, or, under the one-person exception, by that person, marked. | S04 §18.2; S04 DS026 | addition, stricter than S04 §18 (except under the one-person exception) | draft 7, release A item 4; owner record items 25 and 29 |
| C20 | Who supplies, checks, corrects and approves each kind of record; the way in and supplier on every value; retrospective entries never rewrite a result already shown. | S04 §18.1, §18.2; S03 §3 (table rows); PG-DS-AC-04 | addition | draft 7, "Data supply governance and lifecycle" |
| C21 | The data supply registers and the M6 input contracts become controlled package artefacts; the version lines and amendment records of the eight sections. | S04 §20; the version line and lock record of each amended section; the package (section 6.7) | addition; version lines reworded | revision 4, registers; S18 §6 |
| C22 | Profit Guardian advises and never blocks: the builder may ignore (dismiss) any finding in one tap, or defer it to a chosen date, with a reason optional; who and when are recorded; the finding is kept and raised again when something material changes, and a deferred one on its chosen date. | S06 §11 (one sentence reworded, one paragraph added); S00 §00.3 (one sentence reworded); PG-DS-AC-16 | owner-approved relaxations of S06 §11 ("must record rationale") and S00 §00.3 ("with reasons and evidence", for dismissals), section 4 | owner record items 18, 23 and 24 |

By section:

<<SECTION_SUMMARY>>

## 4. Does any locked meaning change?

Section 18 asks for extra care where a change touches a canonical financial definition. The owner's standing rule is that anything that changes a claim's meaning, relaxes a condition or widens scope comes to him first. Here is the answer, item by item.

- **No existing canonical financial definition changes.** Recognised margin, forecast final margin, cash-position-adjusted margin, the authoritative forecast, the revenue lifecycle states, realised saving and source authority all keep their locked meaning (section 6.6).
- **One new financial view is added (C13).** The extras and variations view (S05 DS002, S11 DS003) is a breakdown of the one authoritative forecast final margin, not a second margin:
    - each instruction or variation gets its approved revenue and its share of forecast final cost (cost recognised to date plus forecast cost to complete, with an attributed commitment counted once inside the forecast cost to complete);
    - the original scope is the remainder;
    - the parts add up exactly to the authoritative figure.

  This is new financial semantics, so it is treated as such. It is labelled with its definition as S03 §5 requires for every view. It triggers the financial-core regression suite (S17 §5) and the overlap suite (S17 §6). It needs its own fixtures and tests (section 6.4). How accruals and overhead are shared with an extra must be specified before it is built (S03 §6.3 already requires that for overhead allocation). The owner confirmed it (question 3, owner record item 17). It meets the canonical separation rules: the approved budget stays separate from the forecast (S03 §4.1, "A forecast is not an approved budget"; S05 DS001 shows both, each named); the breakdown is of the adopted authoritative forecast, so it is not a scenario (S03 §4.1, "A scenario is not the current expected result unless explicitly adopted"); each extra's forecast cost to complete is a component of the one forecast, worked out by whatever method S05 §5 selects after discovery, and classified as S05 §5 requires; and the split follows S05 §12's rounding rules, with any rounding difference shown.
- **The financial part of severity is new design (C11), and it stays the financial part only.** S06 §5.1 requires "thresholds ... configurable within approved governance boundaries"; S06 §8 requires them "documented, testable and approved". Levels the builder sets, which are then approved, meet that. But severity is not only money:
    - S13 §13.4 grades quality findings on safety, regulation, structure and building performance;
    - S13 §13.4 also says "financial prioritisation must never override safety or mandatory quality requirements";
    - PG-RS-AC-05 says a score never bypasses safety, quality or approval constraints.

  So S06 DS002 limits the builder's levels to the money part. A finding's safety, quality, contractual and compliance classification is assessed on its own and is never lowered by a small or missing amount. A finding with no defensible amount (PG-AI-AC-07) shows that classification, marked as having no amount. Until the levels are set and approved, a finding's money grade shows "ungraded" and its non-financial classification still applies; that is a labelled state, not a default. For quality findings that classification is S13 §13.4's; for other findings (an expired insurance certificate, say) no locked scheme exists yet, so one must be designed and approved before C11 is built (M17). The owner settled what a percentage is measured against (question 2): the builder chooses the whole job, the part of the job the finding sits in, or both, the parts being those of his own budget breakdown (S05 DS006), which add up to the whole-job budget; a finding not tied to a part is graded on the amount and the whole job only, and says so. Question 6 confirms the whole-job base: the job's approved budget (owner record item 21).
- **C02, the move to one intake, changes no text but changes results.** The locked Section 04 already requires reconciliation, authority and entity resolution for every record kind; stage 1 does not yet meet that for 24 kinds. When the move is built, the rules see only reconciled records of those kinds, so some results will change. That is why the move has its own change request, with a saved baseline of today's results and every difference explained and signed off (S04 DS028). PG-DS-AC-03 ("a new way in changes no rule") says in its own words that it does not govern this move.
- **C10 says how "approved" is met for the detection defaults.** The defaults are documented, visible to the builder and accepted by his approver, so nothing is substituted silently (S04 §10, PG-DI-AC-11). A one-person builder accepts them himself, marked, under the one-person exception below (question 5, owner record item 20).
- **C13 adds no new revenue state.** S11 §8's "Disputed/rejected amount" stays one state. In S05 DS001 it is shown in two columns, disputed and rejected, by its recorded status. After a rejection the builder records what happens next:
    - "disputed", "at his own cost" and "withdrawn" (nil value, history kept) are recorded statuses of the rejected state, not new states;
    - "resubmitted" is a change of state back to submitted, made through the process S11 §8.1 requires, with its own record (S11 DS001).

  An item carried at the builder's own cost shows no what-if. The cost attribution (S03 DS014, S05 DS003) groups costs already counted; it never counts them twice (S03 §6.4, S05 §6, PG-PC-AC-02, PG-CR-AC-10).
- **C14 follows the locked rules and adds a presentation.** The locked rules it follows:
    - S05 §5.1 already requires one authoritative forecast;
    - S05 §3.2 already forbids treating unapproved variations or disputed claims as secured revenue;
    - S04 §9 already requires authoritative and provisional outcomes to be compared "without confusing their status";
    - S10 §7.1 isolates scenarios.

  The new part is the per-category columns across budget and profit, each with the effect the item would have if it went through. Those effects are what-if values: labelled, isolated, and never added in. For records on hold, they follow S04 §9's rules for provisional views (S05 DS001).
- **Two locked conditions are relaxed, each by the owner's decision of 2026-11-13, and stated as such.**
    - **The one-person exception (C04; question 1, owner record item 15).** S02 §3.1 asks for preparing and approving to be separated "where practical and supported by policy", and PG-FR-025 for "appropriate segregation of duties". The code enforces it today: F-67 (`apg/policy_approval.py`) refuses an approval by the person who proposed the setting. The owner's decision supplies the policy S02 §3.1 allows for. Where a builder has exactly one authorised person (a person with the permission to approve; a capture-only or view-only user does not count, owner record item 26), that person may approve the builder's own settings, including accepting a product default (item 20) and users and roles; the approved budget and its breakdown (item 27); and the approval steps of a retention event (item 25); and may confirm the values he keyed from documents (item 25; S04 DS022 is this change request's own stricter control). Each such record, and every figure, finding and report that uses it, is permanently marked as approved, or confirmed, by the person who entered it. With two or more authorised people, the two-person rule applies. It applies per kind of record: once a second person may approve or confirm a kind of record (a bookkeeper who checks keyed values, say), the two-person rule applies to that kind, and the exception continues for the others (owner record item 29). Every approval, also under the exception, records a short reason, as S15 checkpoint D requires (item 30); only warnings may be ignored or deferred without one. **This also relaxes Section 15, for these cases only:** S15 §15.4's "separate approval authority" and §15.11's approval of "changes to authoritative financial rules or approved baselines", "privileged access changes" and "retention release". The other consequential actions of §15.11 keep their approval: purchase orders and supplier commitments; contract, scope, specification or material changes; claims, notices and commercial communications; deletion or correction of authoritative evidence; security cancellation; and no action outside Profit Guardian is covered (S04 DS017, DS026). Each approval keeps its own permission, approval record (with its rationale and the risks considered, S15 §15.11) and audit event, distinct even when one person holds both roles. F-67's code changes under the build's own change request, with tests (PG-DS-AC-15).
    - **Dismissing a finding without a reason (C22; question 4, owner record item 18).** S06 §11 says "Dismissal/deferment of material findings must record rationale". The owner decided that Profit Guardian advises and does not block: the builder may ignore any warning in one tap, and a reason is optional. The sentence is reworded (S06 DS005), and so is the matching line of Section 00 §00.3 (S00 DS004, owner record item 23): who dismissed or deferred the finding, and when, is still recorded, and the reason where one is given. Deferment is recorded like dismissal, and a deferred finding returns on the date chosen, or sooner on a material change (item 24). The evidence is kept, the finding can be reassessed, and it is raised again on a material change (S06 DS006). PG-AI-AC-13 (dismissal is auditable) and S06 §11's "retain evidence and allow future reassessment" keep their meaning. S06 §6's finding data contract field "rationale" (APG-S06-L0079) stays, left empty when none is given. A dismissal is a person's decision, not financial prioritisation overriding safety (S13 §13.4), and the finding's own safety or quality grade is never lowered. Ignoring a finding never closes a defect: rectification and closure keep their own evidence (S13 §13.8).
- **"Switched on" is new wording; it is not a new limit.** Onboarding asks only what the insights a builder switches on need (draft 7, "Setup questions"; data supply decision 5, the middle path, approved in principle). S02 §2.1's mandatory functional domains are product-level, and they stay. S04 DS002 adds that an insight not switched on, or not yet set up, is shown as such, never as "no issue" (S06 §3: "the absence of an alert is not proof").
- **One control is stricter than the locked text:** a value a person keys from an uploaded document needs a second person's confirmation (S04 DS022), or, under the one-person exception, that person's own, marked "confirmed by the person who entered it" (item 25). Three additions restate locked controls for the new channels:
    - email never sets the organisation from the address alone (S04 §6);
    - a held record is corrected only through the review workflow (S04 §9);
    - a backdated entry never rewrites a result already shown (S04 §13, S05 §13).
- **Scope widens, as the owner directed.**
    - Section 01 discovery gains the data supply questions (C16).
    - Section 04 gains the readiness record and the message rule.
    - Site capture lets workers see what was recorded about them. That needs an actor S02 §3 does not list yet; it is settled before site capture is built (S04 DS023).

  These are the owner's directions of 2026-11-11 and 12, approved in principle on 2026-11-12 (owner record item 1). This assessment is the step Section 18 requires before they are formally approved.

## 5. Risk and impact

| Area | What could go wrong | How the change request controls it |
| --- | --- | --- |
| Financial correctness | The move to one intake (C02) changes which records the rules use. | Its own change request; a saved baseline of today's results; every difference explained and signed off; nothing in the first release relies on the move until it passes. |
| Financial correctness | The extras breakdown does not add up to the main figure, or a cost is counted in both the original scope and an extra. | Defined as a breakdown that must add up exactly (S05 DS002); counted once (S05 DS003); financial-core and overlap suites (S17 §5, §6); PG-PC-AC-02 and PG-CR-AC-10 tests. |
| Financial correctness | A what-if amount leaks into the main figure, or looks definitive. | Never added in, labelled, isolated (S05 DS001, S10 §7.1); PG-PC-AC-12 and PG-DI-AC-05 tests; S14 §14.8 ("an uncertain estimate must not appear definitive"). |
| Financial correctness and safety | A money level is read as the whole severity, so a cheap but dangerous defect is ranked low. | S06 DS002 limits the levels to the money part; safety and quality classification stays separate and is never lowered by a small amount (S13 §13.4, PG-RS-AC-05). |
| Financial correctness | The percentage uses the wrong base, or no base exists; a part's budget does not add up with the others to the job's. | A defined base: the builder's choice of whole job, part or both (question 2), the whole-job base being the job's approved budget (question 6); without a base only the levels that can be measured apply and the finding says so; the parts must add up to the whole-job budget, and Profit Guardian says when they do not (S05 DS006). |
| Security | New channels (email, uploads, phones) bring spoofed senders, malicious files, prompt injection in documents and lost devices. | S04 DS019 to DS023; PG-DS-AC-07; S15 §15.3 to 15.5, §15.9 and §15.10 apply to every new path; a nudge's link opens the form only after sign-in (S04 DS008). |
| Privacy | Site capture records people, places and photos. | Level 2, not in the first release; S09 §14 applies; its privacy design, including a worker's access to his own records, is settled before it is built (S04 DS023, CR-05); S15 §15.6 classifies the data. |
| Tenant isolation | A new path lets one builder's data reach another, for example through an email address. | The organisation is never taken from an address; PG-DS-AC-06 requires PG-DI-AC-14's isolation tests on every way in. |
| Approvals | Settings take effect without the right approval; a one-person builder cannot use APG at all; or the one-person exception spreads to other approvals. | PG-DS-AC-05 and 15: every setting versioned and approved before it takes effect; a one-person builder approves his own settings, each permanently marked, and the marker carried to every figure that uses them; the exception covers only his settings, his budget and its breakdown, his retention steps and his keyed values, each marked; never the other consequential actions of S15 §15.11 (purchase orders, contract or scope changes, claims and notices, deletion of evidence, security cancellation) or any action outside Profit Guardian; every approval keeps its own permission, rationale and audit event. |
| Auditability | A value cannot be traced to who supplied it, how and when. | PG-DS-AC-04; S03 DS010 to DS013 (channel, supplied_by, verified_by, retrospective); originals kept (S04 §10, DS019). |
| Auditability and safety | A builder ignores a serious warning with no reason, and it is lost. | The warning keeps its own grade; who and when are recorded; the finding and its evidence are kept and can be reopened; it is raised again on a material change (S06 DS005, DS006; PG-DS-AC-16; PG-AI-AC-13). Whether to act is the builder's decision (owner record item 18). |
| Operational resilience | Readiness reassessment floods the system or the builder; a stopped feed looks like no news. | Reassessment combined for large batches (S04 DS005); gap identity and noise control as S06 §9.1; PG-DS-AC-13 shows a failed or partial intake as such; the export-file way in stays available when an integration is not (S04 DS014; S16 §9 requires failed syncs never be read as "no change"). |
| Delivery | Builders don't supply data that takes too long to give; no extraction vendor is chosen yet. | Onboarding asks only what switched-on insights need; the pilot measures completion and effort; until extraction exists, values are keyed and confirmed by a second person (or, under the one-person exception, by that person, marked). |

## 6. Downstream effects

### 6.1 Sections and requirements

`CIA_RTM_IMPACT.csv` lists every locked item the change items touch. Each is one of:
- an **insertion point**: text is added after it, and its own wording is unchanged;
- a **reworded line**: a version line, or one of the two sentences on dismissal (S06 §11, S00 §00.3; owner-approved relaxations); the only locked text that changes;
- a **dependent**: read for knock-on effects, with no change needed.

Spans are read from the section documents, so text the RTM does not map is included. `CIA_DEPENDENT_TEXT.txt` holds the full text of every dependent.

No dependent needs new wording. Where an existing requirement already covers a new channel (for example S15 §15.5 tenant isolation, or S04 §12 human verification), the new channel is simply held to it through PG-DS-AC-06.

The M6 input contracts of revision 4 are approved with this change request as an accurate description of how today's code reads its inputs, with their stated limits. A stated limit is not accepted as meeting Section 08. For example, R07 does not check a quote's issue date, which S08 §5 asks to capture. Each limit stays recorded against its rule.

### 6.2 The requirements matrix (RTM)

- **New rows:** 87, one for each addition: paragraphs, bullets, headings, each table row separately, and the 17 acceptance criteria. Each has status "Specified — implementation status unverified", as every locked RTM row does.
    - New IDs use a series of their own (for example APG-S04-DS001), so they never collide with the RTM's numbered IDs.
    - The 17 acceptance criteria keep their own IDs (PG-DS-AC-01 to 17), as do PG-FR-026 and 027.
    - The reworded sentences keep their RTM IDs (APG-S06-C0112, APG-S00-L0017); their summaries are updated to the new wording.
    - A table row is anchored as `table_index=T; row_index=R`, a new anchor form the RTM does not use yet; both are numbered from 0, as paragraph indices are, so a table's first body row is row 1.
- **Existing IDs are kept.** Each consolidation ID today is its paragraph index plus one (for example APG-S04-L0122 is paragraph 121). Inserted paragraphs move later paragraphs, so a fresh run of the same numbering would renumber them. The RTM is therefore regenerated by matching each existing row to its text and old index: it keeps the ID, updates only the anchor, and fails if any old ID would change. The rows affected are counted below.
- **Rows the RTM lacks.** The locked RTM has no row for some locked text this change request touches:
    - S02's functional requirements and actors tables (PG-FR-001 to 025 are not in the RTM);
    - S03's entity, common-field and lifecycle tables;
    - S06 §8's first paragraph;
    - S11 §8's state definitions;
    - S15 §15.6's retention paragraph;
    - the version lines.

  The change request proposes adding an RTM row for each of the <<N_BACK>> such items it touches (<<N_PARA>> paragraphs and <<N_TROW>> table rows), in the forms above, with id_type "Change-request-assigned ID (APG-CR-DSR)" for the new series, the existing consolidation scheme for backfilled paragraphs, "Source-explicit ID" for table rows that carry one (PG-FR-001 to 025), and a consolidation-assigned table-row ID (for example APG-S03-T0101 for table 1, row 1) for the others. The wider gap is a pre-existing observation (section 13).

<<COUNTS>>

### 6.3 Implementation tasks (none authorised by this change request)

| Task | What it is | Governed by |
| --- | --- | --- |
| Defect change request | DC-1 to DC-13 fixed after stage 1, with their messages; the first place decision 13 is built. Most of it rests on requirements already locked (PG-AI-AC-04, PG-PC-AC-04 and 15). One part rests on this change request: DC-1's fix has the builder record what happens after a rejected variation, which is S11 DS001. That part waits for this approval, or carries the requirement itself. | its own change request, raised after stage 1 |
| First release, item 1 | One intake for every kind (C02) | its own change request, with its regression baseline |
| First release, items 2 to 6 | Import made real; the general entry feature for setup and retention events; retention events and quote readings through the intake; readiness for the builder | each authorised by the owner by milestone, after the Discovery Exit Report; the M6 input contracts (item 5) are approved with this change request (section 6.1) |
| Second release and later | Data that lifts known limits of today's rules, each with its own rule change. Subcontractor claims, assessments and payments (E17 to E19) move to the front of the second release with the back-to-back claim check (data supply decision 7). | each its own change request |
| Owner's CR-05 | Phone site capture (Level 2), including its privacy design and workers' access to their own records | CR-05 |
| Owner's CR-07 | Integrations through AUIF (Level 3) | CR-07 |
| Owner's CR-02 | Financial integrity completion. Its materiality model, still a reference draft and not an implementation, is one possible base for a severity percentage. | CR-02 |
| Owner's CR-08 | Pilot and acceptance scenarios; the discovery questions of C16 feed it | CR-08 |
| Owner's CR-10 | Verified profit ledger. It overlaps C14 (verified figures first) and C13 (the breakdown). <<CR10>> | CR-10 |
| The approval code (F-67) | `apg/policy_approval.py` refuses an approval by the proposer. The one-person exception (C04) changes it, with the tests of PG-DS-AC-15. | the build that implements C04, under its own change request |

**How releases fit the phases (C17).** The design calls its scopes of data "releases" (A, B, later). Sections 14 and 18 number the build phases differently:
- **Section 18 §8:** phase 5 is security, reliability and recovery; phase 6 is acceptance.
- **Section 14:** phase 5 (§14.8) is interface and user workflows; phase 6 (§14.9) is verification; phase 7 (§14.10) is database and integration closure.

This assessment uses Section 14's numbering, with Section 18's in brackets where they differ (phases 0 to 4 are numbered the same in both), and replaces draft 7's "phases 1 to 3 … phase 4 to 6". Every release starts after Phase 0 and the Discovery Exit Report. The first release's work falls in:
- **Phase 1:** the intake, source authority, identity, and the readiness record's shared data-quality status (§14.4).
- **Phase 2:** the financial policy.
- **Phase 3:** the domain rules' use of the readiness record.
- **Phase 5 (Section 18 §8 has no interface phase of its own):** the user-facing parts: entry screens, setup questions, the missing-data list and nudges, the extras panel and the verified-first display (§14.8).

No release reaches production use without the evidence of phases 4, 6 and 7 (Section 18 §8: phases 4, 5 and 6; the handoff instructions follow Section 18's numbering). No text change is needed. The numbering difference is reported in section 13.

### 6.4 Tests, regression suites and immutable fixtures

This change request changes no code and no test. The table names the stage 1 tests and fixtures each later build will touch (freeze ee1ce3ec), so the build change requests carry them.

| Change item | Stage 1 tests the build will touch | Fixtures |
| --- | --- | --- |
| C02, C03, C19 | test_ingest_pipeline, _reconcile, _mapping, _contracts, _boundaries, _adversarial, _support, _golden; test_fin_intake, test_det_intake, test_mkt_intake; test_fin_corpus, test_det_corpus, test_mkt_corpus; test_tenancy | regression/GOLDEN_M2, GOLDEN_M3, GOLDEN_FIN, GOLDEN_DET, GOLDEN_MKT and every BASELINE file. The move to one intake needs a new, separately approved baseline; today's files are kept, never overwritten. |
| C04 | test_source_authority; test_f67_policy_approval and test_f671 to f674 (the one-person exception changes F-67's rule); test_status_model | none |
| C09 | test_mkt_fx_fresh, test_mkt_policy | GOLDEN_MKT |
| C10, C11 | test_det_policy, test_det_policy_bounds, test_det_detect, test_det_findings, test_det_noise, test_det_signal, test_det_golden, test_mkt_detect, test_mkt_golden, test_materiality_engine | GOLDEN_DET and GOLDEN_MKT (severity values change under the defect change request and again under the C11 build) |
| C13, C14 | test_det_rules_commercial (R04B, DC-1, S11 DS001), test_fin_revenue, test_fin_commitments, test_fin_costs, test_fin_forecast, test_fin_bridge_book, test_fin_golden | GOLDEN_FIN, BASELINE_M4 |
| C18 | test_fin_cash, test_fin_intake | none today; new synthetic fixtures: one project with two contracts in AUD, and an event in another currency (rejected) |
| C22 | test_det_findings, test_det_noise (dismissal and re-notification) | none |

Section 17 §5 governs every fixture change: review, rationale, versioning and a regression impact assessment, and expected results are never changed to make a failing build pass. A change to cost allocation or to a margin view (C13) triggers the financial-core regression suite. APG-M8.1, the earlier audited packages and the M10 archive stay untouched.

**New tests each build must add.** They are named here so the RTM rows can point to them; IDs are given when they are built.
- PG-DS-AC-01 to 17:
    - the same fact through two ways in gives the same result (02);
    - a new way in changes no rule test result (03);
    - no direct write to the store (01);
    - provenance on every value (04);
    - setup answers take effect only after approval (05);
    - tenant isolation, verification and quarantine on every way in (06);
    - malicious and malformed files are rejected (07);
    - an entry form cannot edit a held record (08);
    - readiness is reassessed on each trigger and is never eligible with a missing input (09);
    - gap identity, lifecycle and suppression (10);
    - a way in that isn't built is never offered (11);
    - the field-coverage report fails on a gap (12);
    - a partial intake is shown as partial (13);
    - every message carries what to do, and the message list fails on an uncovered message (14);
    - the one-person exception and its limits: self-approval with the marker on every dependent figure, the two-person rule per kind of record once a second person may approve that kind, a short reason and the approval's own audit record on every approval, keyed values and retention steps confirmed or approved by the one person, marked, and no exception for the consequential actions §18.3 lists as outside it (15);
    - a finding dismissed in one tap with no reason, who and when recorded, kept, reopenable, and raised again on a material change; a deferment recorded the same way and raised again on its chosen date; the defect or other record it is about left unchanged (16);
    - a retention event without a currency, with another currency, or without its contract is rejected; pools are kept per contract and project; each state shows its S03 §13 label, "approved" is not "released", and "received" needs its matching bank transaction (17).
- **The extras breakdown:** it adds up exactly to the authoritative forecast final margin, and a cost attributed to a variation is counted once (financial-core and overlap suites, with new fixtures).
- **The what-if columns:** a what-if amount never enters the main figure; a held record's what-if is visible only to authorised reviewers.
- **Severity:** graded by amount, by percentage, and by both, whichever is reached first; against the whole job, the finding's part, or both, as set; ungraded when not set; only the measurable levels when a base is missing; a finding not tied to a part graded on the whole job only; budget parts that do not add up to the whole are reported, each breakdown on its own when the budget is broken down both ways; a finding in two parts (a stage and a trade) graded against each, the more serious grade applying and the triggering part named; a safety classification never lowered by a small or missing amount.
- **Variations:** a resubmitted variation changes state back to submitted only through the S11 §8.1 process; disputed, own-cost and withdrawn are recorded statuses of the one Disputed/rejected state, and an own-cost or withdrawn item shows no what-if.
- **Document values:** a keyed value from an uploaded document counts only after a second person confirms it, or, under the one-person exception, after that person confirms it, marked.
- **Retrospective entries:** a backdated entry leaves a shown result and its records intact, and marks the insight for reassessment.

### 6.5 Acceptance criteria

PG-DS-AC-01 to 17 are new; they sit in S04 §19 after PG-DI-AC-18. No existing acceptance criterion changes.
- PG-DS-AC-06 ties every way in to PG-DI-AC-01 to 18, so the existing intake criteria apply to each new channel.
- PG-DS-AC-14 is how PG-AI-AC-04 ("missing data creates a qualification") and PG-PC-AC-04 and 15 reach the builder as an instruction.

### 6.6 Terminology

Each term in `CROSS_SECTION_TERMINOLOGY_REGISTER.md` was checked against the additions:

| Term | Effect |
| --- | --- |
| Recognised margin; cash-position-adjusted margin | unchanged |
| Forecast final margin | unchanged; the extras view is a breakdown of it, labelled as such, adding up to it exactly |
| Authoritative forecast | unchanged; S05 DS001 shows it first, and DS002 breaks it down |
| Provisional/qualified value | unchanged; the readiness states (eligible, qualified, blocked, unavailable) use it; held records' what-if values follow it |
| Realised saving / net benefit | unchanged |
| Potential, estimated, approved, recognised, invoiced and collected revenue | unchanged; S11 DS001 records the builder's next step after a rejection; resubmission goes through the lifecycle process; withdrawal is a recorded status |
| Cash, scheduled receipts and payments, scenarios | unchanged; a what-if value is a scenario-only value |
| Source authority | unchanged; S04 DS015 restates that the register decides, never the latest arrival |
| Cross-domain overlap / net impact | unchanged; S05 DS003 applies it to costs attributed to variations |
| Unknown external outcome; closed database-dependent item | unchanged |

**New terms to add, each with its section:** way in (and Level 1, 2, 3); readiness record; data gap; nudge; retrospective record; setup question; switched on (an insight a builder has set up and turned on); ungraded finding; what-if value (a scenario-only value); extras and variations view (a breakdown of forecast final margin); verifier role (a permission, to be mapped to an S02 §3 actor); product owner (as the approver of the detection defaults); data release (a scope of data, distinct from a build phase and from Section 17's release gates); controlled data-supply registers; "approved by the person who entered it" and "confirmed by the person who entered it" (the one-person markers); authorised person (per kind of record); one-person exception; defer (a finding, until a chosen date); ignore (dismiss) a finding; budget breakdown and budget part (a stage, trade or area of the approved budget).

### 6.7 Handoff instructions, manifest, hashes, change register and closure register

After approval, and only then:

- **Section files.** Sections 00, 01, 02, 03, 04, 05, 06 and 11 are issued as version 1.1. Each has its version line reworded and an amendment record added to its lock record, as worded in section 12. Each version 1.0 file and its hash is kept as history (S18 §6), in a history folder of the package.
- **The validator must change first.** `validate_handoff_package.py` looks only for files named `..._v1.0_LOCKED.docx`. A copy of the locked package with Section 04 renamed to version 1.1, and its manifest updated, was run through it; it failed with "REQUIRED SECTION DOCUMENT MISSING: 04". It must be amended to take each section's current version from the manifest, and to accept the history files the manifest lists. That amendment is tested itself (T18-05, T18-08).
- **A controlled change register.** S18 §2 requires one, and the package today holds only the CR template. A change register is created, and this change request is entered in it with its assessment, approval and closure.
- **Manifest and hashes.** New entries for:
    - the eight version 1.1 files and the history files;
    - the controlled data-supply registers and the M6 input contracts;
    - this assessment and its tables;
    - the decision records (the owner's decisions record and the data supply decisions document);
    - the independent check reports.

  Then a new manifest digest and validation report, and the package rebuilt and reopened from a fresh extraction (S18 checkpoint A).
- **Handoff instructions.** `README_HANDOFF.md` and `CLAUDE_HANDOFF_INSTRUCTIONS.md` add the controlled data-supply registers to the reading list; `SOURCE_SECTION_INVENTORY.json` lists the new versions.
- **DB-dependent closure register: no rows added by this change request.** Two needs are recorded here for the build change requests: the intake's persistence for every kind after the move (C02), and the readiness record's persistence and reassessment under concurrency (C07). The first overlaps the existing DB-APG-002. Section 18 §7, S14 §14.10 and the handoff instructions require each register row to carry instructions for the person who runs the database work. So the rows are written only when a build is authorised, and the owner decides then who carries them out.

## 7. Tests and evidence to validate the amendment itself

| Check | What it shows | Section 18 test |
| --- | --- | --- |
| Paragraph comparison of each version 1.1 file with its version 1.0 | each differs only by the additions, the reworded version lines and the two reworded sentences (S06 §11, S00 §00.3) in `CIA_PROPOSED_TEXT.csv`, word for word; nothing else is reworded or removed | T18-08 |
| RTM regeneration and validation | all 2,712 existing IDs kept (by text and old index; APG-S06-C0112 and APG-S00-L0017 with their reworded summaries); 87 new rows plus the backfilled rows; no blank, duplicate or orphaned ID | T18-02 |
| Fresh extraction and hash check | every controlled file's digest matches the new manifest; the history files are listed | T18-01, T18-05 |
| Terminology review | the new terms added; no collision with a canonical term; documented human review of the flagged term families (S18 §5) | T18-07 |
| Cascade check | every new requirement has an RTM row and a named test to come; no dependent left unreviewed | T18-03 |
| Independent review of the version 1.1 texts | the texts match this assessment as approved | S18 §6 |

## 8. Review, approval, versioning and verification after the change

- **Reviews so far.**
    - The design and revision 4 went through: five independent agent checks of revision 4; GPT's check and scoped re-check of revision 4; three agent checks of the design; and a GPT and a Gemini review of the design. Every finding was fixed or answered (in the packs). The three small points from GPT's re-check were fixed by Claude and have not been re-checked independently.
    - This assessment: an independent agent check of draft 1 (5 blocking, 19 should fix, 21 minor) and a scoped re-check of draft 2 (2 blocking, 11 should fix, 20 minor new points, and 9 earlier findings only partly fixed), then a focused check of draft 3 (no blocking point; 6 should fix, 7 minor, all wording). A fix is claimed for each (`CHECK1_FIXES_CIA.md`, `CHECK2_FIXES_CIA.md`, `CHECK3_FIXES_CIA.md`).
    - GPT's review of draft 4 (4 blocking, 3 should fix, 1 minor). It re-ran the build and got byte-identical tables and text. Its findings are fixed in draft 5 (`GPT_FIXES_CIA.md`). It advised one targeted confirmation of the fixes, not another full round.
- **Reviews before approval.**
    1. Done: a focused independent check of draft 3.
    2. <<M15_STATUS>>
    3. Done: GPT's review of draft 4. Done: an independent focused check of draft 5 (2 blocking, 10 should fix, 10 minor), its findings fixed and the owner's answers A to F carried (`CHECK5_FIXES_CIA.md`). Done: a scoped re-check of those fixes (1 blocking, 6 should fix, 8 minor; `RECHECK_DRAFT5.md`), its findings fixed and the owner's answers G and H carried (`RECHECK5_FIXES_CIA.md`). Done: a narrow final check of those fixed lines (0 blocking, 1 should fix, 4 minor; `FINAL_CHECK_DRAFT5.md`), its findings fixed (`FINAL5_FIXES_CIA.md`); these last fixes are wording only and were not checked independently again, to avoid a loop. Still to come: GPT's targeted confirmation of the fixes (the one-person exception and the relaxations, the two reworded sentences, the retention definition, the M15 register revision 4.1), as GPT advised.
    4. Gemini only if the owner wants a design view.
    5. <<CR10_STATUS>>
- **Approval conditions.** The owner approves a final text: no square brackets are left in the proposed wording except the change request's number and the approval details. Questions 5 and 6, which came out of GPT's review and the owner's answers, are answered (owner record items 20 and 21), so no bracket for them remains. The CR-10 overlap is a recorded dependency of the approval (owner record item 19), not a check made before it.
- **Approval authority.** Emmanuel, product owner. The dispositions open to him: approve; approve with conditions; send back for changes; reject.
- **Versioning.** The eight sections become version 1.1, each with its reworded version line and an amendment record naming this change request and its approval. Version 1.0 and its hash are kept.
- **After the change:**
    1. Produce the version 1.1 files from the approved wording only.
    2. Run the checks in section 7.
    3. Have them checked independently.
    4. Update the RTM, terminology register, change register, manifest and validation report.
    5. Record the result and close the change request (section 9).

## 9. Traceability and closure record

Change request APG-CR-DSR (number to come) → this assessment and its tables (`CIA_PROPOSED_TEXT.csv`, `CIA_RTM_IMPACT.csv`, `CIA_DEPENDENT_TEXT.txt`, `CIA_COUNTS.txt`, generated by `build_cia.py` from the locked package) → the approved wording → the version 1.1 files and their hashes → the regenerated RTM, terminology register, change register and manifest → the validation runs → the closure record.

| Closure field (CR template) | Entry |
| --- | --- |
| Independent reviewer | [the agent checks and GPT pass that review this assessment] |
| Authorised approver and decision | [Emmanuel; disposition; date] |
| Revised versions and new hashes | [Sections 00, 01, 02, 03, 04, 05, 06, 11 v1.1; SHA-256 of each; new manifest digest] |
| Verification results and defects | [section 7 checks: results, defects, retests] |
| Closure decision, owner and date | [ ] |

## 10. Matters carried from earlier reviews

| Matter | Raised by | Where it stands |
| --- | --- | --- |
| M01 The ten shared financial foundation decisions (8-layer 02 §2.11) | GPT | Open owner decisions, not settled here; they are product-level, not builder setup answers (S04 DS026). Needed before the first release's financial policy is built: the cost taxonomy (decision 3, with the cost-code map), how committed cost and cost to complete are worked out (6), how variations are treated (7), and who approves a baseline (8), except that a one-person builder approves his own budget and its breakdown, marked (owner record item 27; S04 DS026, S05 DS006). Freshness (9) is approved in principle (data supply decision 10). The rest are needed before the financial core is built. |
| M02 The Source Authority Register and its approver | GPT | The register is built through setup questions and approved before it takes effect (S04 DS026). Who approves it is an owner decision before first-release item 3. Claude's suggestion: the finance controller (S02 §3, "financial controls"; PG-FR-025). |
| M03 Baseline and assessment governance | GPT | Baselines: locked in S05 §5.1 and §10 and 8-layer decision 8; added here only for the one-person builder, who approves his own budget and its breakdown, marked (owner record item 27; S04 DS026, S05 DS006), and the split of the breakdown into a setting (its structure) and baseline amounts (S05 DS006); settled before baselines are built ("later"). Assessments (calculation runs) are first-release records; they are governed by S03 §14.3 and S05 §13 (reproducibility, immutable inputs), which this change request keeps; who may start, rerun or supersede a run is settled before item 6 is built. |
| M04 The commitment policy and status maps | GPT | Supplied through setup questions as builder-owned settings of the financial policy (C04). Their content follows M01's decisions 6 and 7. DC-7 shows why a held variation must not map to approved. |
| M05 Labour data privacy (S09 §14) | GPT | Applies to site capture; settled in CR-05 before it is built (S04 DS023). The first release has no site capture. |
| M06 Retention and security state handling | GPT | Settled in Appendix B: the retention event gains its currency (S03 §11.1) and its associated contract (S03 §10.1), and its states are mapped to S03 §13's illustrative lifecycle; PG-DS-AC-17 tests them. Security instruments stay as S03 §10.2 says. |
| M07 Corrected and disputed data | GPT | S04 §13 already governs corrections. The additions keep what was first received, mark retrospective entries, and never rewrite a shown result (S04 DS024). |
| M08 How the cost of extra work links to its instruction or variation | owner, Claude | Proposed in Appendix C; S03 DS014 and S05 DS002, DS003; question 3. |
| M09 Whether Section 11 needs a clarification for the extras panel | owner, Claude | Yes: S11 DS001 to DS003. |
| M10 How the builder's settings are approved | owner, Claude | Decided: Option B (owner record item 15), extended by items 20 and 25 to 27 and made per kind of record by item 29; every approval keeps a reason (item 30). For its cases only it relaxes S15 §15.4 and §15.11 (section 4). S04 DS017, DS022 and DS026, S05 DS006, S06 DS001, PG-DS-AC-05 and 15. |
| M11 Data retention and archiving after close-out, and when a customer leaves | GPT | Checked against Sections 09 and 15 to 17. S15 §15.6 already requires, for each data category, a retention period or rule, archiving and deletion, and legal holds; S16 §8 covers backups. So close-out is covered. What export a leaving customer receives is not stated. No change request now; it is settled with the platform's conventions in discovery. |
| M12 The retention-event (E77) field definition | GPT's re-check | Done: Appendix B. |
| M13 DC-13's scope | GPT's re-check | Fixed in revision 4 by Claude (MP02, MP03, MP04, MP05 and MP09 named); not re-checked independently. |
| M14 The code-read report's column heading | GPT's re-check | Fixed in revision 4 by Claude; not re-checked independently. |
| M15 The 100 entities cross-checked against every row of the Master RTM | revision 4's next steps | <<M15_ROW>> |
| M17 The non-financial classification scheme for findings outside Section 13 | check 2 | To be designed and approved before C11 is built (S06 DS002; S06 §8: documented, testable and approved). Open. |
| M18 A builder's recognition policy | check 3 | Which recognition policy Profit Guardian supports is product-level (M01, decision 2); which supported policy applies to a builder's business or project is recorded for it and approved as other settings are (S04 DS026, S03 §5.1). |
| M19 The locked text the RTM does not map (541 paragraphs and 125 table rows in Sections 00 to 18) | GPT's review of draft 4 | A separate, mandatory work item for package acceptance, outside this change request. Owner: Emmanuel. Closure evidence: a consolidated RTM validation reporting zero missing, duplicate, orphaned or unmapped items, with the manual semantic review documented (S18 §9, checkpoint C). The version 1.1 package cannot pass S18 §9 until it is closed. This change request backfills only the <<N_BACK>> items it touches (section 6.2), and does not claim the S18 §9 gate. |
| M20 The 8-layer design blueprint v0.1 | GPT's review of draft 4 | Now in the pack (`06_change_request_sources/`), so the dependents named in section 2 and M01 can be checked. |
| M16 The code-read scan is not a proof | GPT's re-check | The field-coverage report (PG-DS-AC-12, S04 DS029) rests on a scan that "does not independently prove" the call-path analysis. So each rule's inputs are confirmed by that rule's tests when the rule is next changed, and the report is never cited as proof on its own. |

**Outside this change request:**
- the five developer entities E91 to E95 (not in the locked blueprint; listed in the register for information only; their own change request). The developer and principal views the blueprint already requires (PG-FR-024) are unchanged;
- the reviewers' further ideas: back-to-back claim checks, adjudication evidence packs, statutory declaration checks, a learning cost-code map (each its own change request);
- sharing data between related companies or joint ventures (its own decision, weighed against tenant isolation);
- the DC fixes;
- stage 2.

## 11. Questions for the owner

**Every question is answered** (owner record items 15 to 30, 2026-11-13): six questions, the CR-10 decision (item 19), the platform-held records (item 22), six more (A to F) from the independent check of draft 5, and two (G and H) from its re-check. The proposed wording carries each answer.

| Question | The owner's answer | Where it goes |
| --- | --- | --- |
| 1. Can a builder who is the only person using APG approve his own settings? | Yes, Option B: where the builder has exactly one authorised person, he may approve his own settings, each such setting and every figure using it permanently marked "approved by the person who entered it"; with two or more people the two-person rule applies. | S04 DS017, DS026; PG-DS-AC-05, 15; section 4 (a stated relaxation) |
| 2. A percentage of what? | The builder chooses how his budget is broken down (by stage, trade or cost code, area, or a mix); the parts add up to the whole-job budget, which is always there; the breakdown comes from his own system where it has one. He chooses whether his percentages are measured against the whole job, the part a finding sits in, or both, alongside his dollar amounts; a finding not tied to a part is graded on the dollar amount and the whole job only. Commercial builds are covered the same way, the parts being whatever the builder budgets by. | S05 DS006; S06 DS002; Appendix C |
| 3. What do the main budget and profit include, and how does the extras panel split them? | Yes, as suggested: the main figures use only approved and verified records plus the builder's approved forecast to finish, labelled as a forecast; approved variations count in them; the extras panel is a split of them that adds up exactly; everything not final sits beside them. | S05 DS001, DS002 |
| 4. Do the dollar and percentage levels grade the money side only? | Yes, and a warning is advisory: it always shows, graded on its own seriousness; the builder decides, and may press Ignore in one tap; a reason is optional (Option B of the follow-up question); who and when are recorded; the warning is kept and raised again only if something material changes. | S06 DS002, DS005 (a reworded sentence: a stated relaxation of S06 §11), DS006; PG-DS-AC-16 |
<<Q56>>

**A correction, kept for the record.** When question 1 was first put to the owner, Claude said every setting in APG only counts once a second person approves it. That was not fully true: the code refuses an approval by the person who entered a setting (F-67), but grades findings with severity levels whether or not they are approved, flagging them "not approved" (defect candidate DC-11). The question was corrected the same morning, before the owner answered.


**Also at approval:** the number for this change request in your list.

## 12. Proposed wording, section by section

Every addition and every reworded line, with its ID and the locked text it follows. <<BRACKETS>> The same content is in `CIA_PROPOSED_TEXT.csv`.

<<PROPOSED_TEXT>>

## 13. Pre-existing observations in the locked package (outside this change request)

These were found while doing this assessment. None is changed here; each is reported so the owner can decide whether it needs its own change request.

- **The RTM does not map every locked paragraph.** Comparing each section document with the RTM: in Sections 00 to 17, 401 non-empty paragraphs (cover and lock-record lines included) and 125 table rows have no RTM row. Among them:
    - S02's functional requirements PG-FR-001 to 025;
    - S03's entity table;
    - S04 §14's opening sentence ("Track freshness and completeness by source, project, domain and decision use");
    - S05 §3.2's formula line;
    - S11 §8's revenue state definitions.

  Section 18 has no RTM rows at all, though S18 §4 requires the RTM to trace "the handoff-specific requirements in Section 18". Section 18 checkpoint C blocks handoff if a material requirement is unmapped. The counts are in section 6.2. This is now matter M19: a mandatory work item for package acceptance, outside this change request.
- **Section 00 §11 names sections differently from the sections themselves.** This affects every section from 09 to 18, and also 06 and 10. For example, it calls Section 09 "Opportunity Discovery" and Section 11 "Alerts, Dashboard, Reporting"; the files are "Labour, Productivity & Resource Intelligence" and "Commercial & Revenue Intelligence". This assessment uses the titles of the section files.
- **Sections 14 and 18 number the build phases differently** (section 6.3).
- **The validator accepts only version 1.0 files** (section 6.7), so no approved change request could pass it as it stands.

## Appendix A. Files and how to reproduce

- `build_cia.py` with its data file `cia_data.py`, run as `python3 -I build_cia.py <extracted locked package> <output folder>`, writes `CIA_PROPOSED_TEXT.csv`, `CIA_RTM_IMPACT.csv`, `CIA_DEPENDENT_TEXT.txt` and `CIA_COUNTS.txt`.
    - It reads the Master RTM and the 19 section documents, paragraphs and table rows in document order.
    - It fails if an anchor, heading or proposed ID is wrong, or if an insertion point is not the true end of its block (amendment records are exempt: they go after the last lock-record line, before any closing "next section" line).
- `assemble.py` puts those tables into this document.
- Both are builder tools (BUILDER-EXECUTED: NOT INDEPENDENT).
- The locked package used: `Anchor_Profit_Guardian_Blueprint_v1.0.zip` (SHA-256 487becabdf47796800937d13a706a19b63b7b8230ecc5354b2f01a647ae5d960; manifest digest dad3fa91cb1da822779e041bb66279e08b6598861bb222b5e6e709e967f2d89c).

## Appendix B. Retention event (E77): proposed field definition

Taken from the stage 1 code (`fin/cash_states.py`: `record_event`, `check_event`, `fold`, `events_of`). Today the event is written straight to the store; under C18 it comes through the intake, from the first release's entry form.

| Field | Supplied by | Meaning and rule (today's, unless marked new) |
| --- | --- | --- |
| project_ref | the person | the project whose retention pool moves |
| contract_ref | the person | **new:** the associated contract (S03 §10.1): the head contract (E08) or the subcontract the retention is held under; required; the pool is kept per contract and project |
| currency | the person, checked by APG | **new:** the ISO 4217 code of amount_cents (S03 §11.1); required; it must equal the currency of the pool it moves; a retention event never converts currency |
| from_state, to_state | the person | one of the allowed moves: withheld to claimed; claimed to approved or disputed; approved to released or disputed; disputed to claimed or approved; released to received |
| amount_cents | the person | a positive whole number of cents, no more than the pool it leaves holds |
| evidence_ref | the person | required; for "received", a stored bank transaction of exactly this amount |
| note | the person | optional text |
| seq | APG | the next number in the project's sequence; events are append-only |
| actor, actor_kind, actor_roles | APG, from the signed-in person | a named person, never a service; "approved", "released" and "received" need the retention approver role, the others the clerk or approver role |
| at | APG | when it was recorded |

**The two locked obligations, now in the definition (M06).**
- **A currency** (S03 §11.1: "every monetary value must have an explicit currency"). Today the event has none and assumes the project's; the definition adds `currency`, which must equal the currency of the pool it moves.
- **The associated contract** (S03 §10.1: "associated contract and project"). Today the event moves a project-level pool with no contract link; the definition adds `contract_ref`, and the pool is kept per contract and project. For a project with one head contract, the pool is the same as today's.

Both are design changes for the build that brings retention events into the intake (first release, item 4); today's code changes then, under that build's own change request.

**The states, mapped to S03 §13's illustrative retention lifecycle** ("Withheld → Release Claimed → Under Review → Approved → Released / Disputed"):

| S03 §13 | The event's state | Note |
| --- | --- | --- |
| Withheld | withheld | money held back from a payment |
| Release Claimed | claimed | a release has been claimed |
| Under Review | claimed | no separate state: a claimed release is under review until it is approved or disputed; views label it "release claimed, under review" |
| Approved | approved | needs the retention approver role; approval is not release (S03 §13: "A retention is not released merely because release was requested or approved") |
| Released | released | needs the retention approver role and evidence |
| Disputed | disputed | from claimed or approved; it goes back to claimed or approved when settled |
| (none) | received | an extra step after Released: the money is in the bank, matched to a stored bank transaction of exactly the amount; S03 §13's rule that status needs evidence |

**Tests (PG-DS-AC-17, C18):**
- an event without a currency, with a currency other than its pool's, or without its contract is rejected with a reason;
- two contracts in one project keep separate pools;
- each state shows its S03 §13 label;
- "approved" does not count as released, and "received" needs its matching bank transaction;
- synthetic fixtures only: one project with two contracts in AUD, and an event in another currency.

## Appendix C. The cost of extra work: proposed data design

- **What is new:** the records that can carry an extra's cost gain an optional reference to the instruction (E10) or variation (E09) the cost was incurred for:
    - supplier invoice lines (E23; today APG calculates invoice lines from the invoice, so the line needs the reference);
    - timesheet entries (E57), priced with the labour rate (E59);
    - plant hire (E64);
    - purchase orders (E21) and subcontracts (E16, second release), for committed cost.
- **One line, one place:** a cost line is attributed to at most one instruction or variation, or split between them by amounts that add up to the line. Whatever is not attributed stays with the original scope. The cost is counted once in actual cost or commitments (S05 DS003).
- **Forecast cost to complete:** the builder may forecast the cost still to come on an extra. Whatever is not forecast against an extra stays with the original scope.
- **Who sets it:** the person who supplies the line, or the person who later attributes it through the review workflow. A later attribution is a governed change, recorded with who, when and why (S04 §13).
- **What the extras view shows:** for each extra or variation, its value in each commercial state (S11 §8), its status, the cost attributed so far, and its share of the job's profit. The original build is the remainder, and the parts add up to the authoritative forecast final margin (S05 DS002).
- **Budget parts (question 2, owner record item 16):** each budget line (E38) carries the part of the job it belongs to: a stage, a trade or cost code, or an area, as the builder breaks his budget down (the work packages of E98, S03 §2). Each cost carries its part too, through its cost code (the cost-code map) or its own tag. A cost with no part counts for the whole job only. The parts add up to the whole-job approved budget (S05 DS006).
- **Not decided here:**
    - how an accrual or overhead allocation is shared with an extra (to be specified before it is built, as S03 §6.3 requires; second-release data);
    - how a builder's own system marks such costs (discovery, with sample exports).
