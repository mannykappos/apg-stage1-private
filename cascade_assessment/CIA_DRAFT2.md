# APG change request: Data Supply System and Data Readiness, cascade impact assessment (draft 2)

Nov 13, 2026 · prepared by Claude (builder) for Emmanuel (product owner)

**Status.** This is the Section 18 §6 cascade impact assessment for one change request, made of two parts that go through Section 18 together (data supply decision 11 in the decisions document `APG_Data_Supply_Decisions`):
- the data supply design (draft 7);
- the Data Readiness Change Request (revision 4).

It is design only. It authorises no build, changes no locked file, and claims nothing is implemented, accepted or ready for production. Stage 2 stays not authorised, and under S04 §20 no production feature code starts before the Section 01 Discovery Exit Report is signed off. It is the builder's work (BUILDER-EXECUTED: NOT INDEPENDENT).

Draft 2 answers the first independent check of draft 1 (INDEPENDENT READ-ONLY (agent): 5 blocking, 19 should fix, 21 minor). Every finding is fixed; the list is in `CHECK1_FIXES_CIA.md`.

## 1. In plain words

The locked blueprint (Sections 00 to 18, version 1.0) already says most of what the data supply design needs:
- one intake with strict controls;
- nothing invented when data is missing;
- warnings when data is stale.

What it does not yet say is how APG makes sure it can always get the data, and how it tells the builder what it needs. This change request adds that.

- **What changes in the blueprint.** 81 pieces of text are added to 7 of the 19 sections (01, 02, 03, 04, 05, 06 and 11), which go from version 1.0 to 1.1. The full proposed wording is in section 12.
  - Most of it goes into Section 04, the intake: the ways of supplying data; the readiness record that tells the builder what is missing; the rule that every message says what to do; setup questions; and 14 new acceptance criteria (PG-DS-AC-01 to 14), the tests each part must pass.
  - The only locked words that change are the version lines ("Version 1.0" becomes "Version 1.1") in the seven sections. Nothing else already locked is reworded or removed.
- **What it does not change.** No detection rule, no financial figure, and no existing financial definition. Recognised margin, forecast final margin and the others keep their meaning. No approval or check is weakened.
- **What is new money logic.** One addition is a new way of showing a figure: the extras and variations panel splits the job's one main profit figure into the original build and each extra, and the parts add up exactly to it. That needs its own tests (section 4) and your confirmation (question 3).
- **What else it touches.** Every locked paragraph and table row that the changes bear on was read for knock-on effects: 1,071 of them, in Sections 00 to 17 and the package, each listed by its ID or position. None needs new wording.
- **The package around the blueprint needs work after approval:**
  - the requirements matrix (RTM), the master list that gives every requirement an ID;
  - the terminology register;
  - the manifest, the list of files with their fingerprints (hashes);
  - the package checker, which today rejects any section that is not version 1.0 (shown in section 6.7).
- **Four questions for you** (section 11), each with an example:
  1. Can a builder who is the only person using APG approve his own settings?
  2. What is "a percentage of the job" a percentage of?
  3. What do the main budget and profit include, and how does the extras panel split them?
  4. Is it right that the builder's dollar and percentage levels grade only the money side of a finding, and never its safety side?
- **Next.** A scoped independent check of what changed in draft 2, then one GPT pass listing every problem at once, then your formal approval. Only after approval are the version 1.1 files made, and each build still needs its own authorisation.

## 2. Change request identification

| Field (Section 18 §6 and the package's CR template) | Entry |
| --- | --- |
| Change Request ID | Provisional reference APG-CR-DSR. The owner gives it its number in his change-request list at formal approval. His list uses CR-01 to CR-08 and CR-10. |
| Requester | Emmanuel, product owner: the data readiness direction of 2026-11-11 and the one-data-supply-system direction of 2026-11-12. Prepared by Claude (builder). |
| Date | 2026-11-13 (draft 2). |
| What it rests on | The data supply design, draft 7 (2026-11-12). The Data Readiness Change Request, revision 4, with its registers. Revision 4 passed GPT's scoped re-check with nothing blocking; its three smaller points were fixed by Claude afterwards and have not been checked independently since. The owner's decisions record of 2026-11-12 and 13 (`OWNER_DECISIONS_2026-11-12.md`, "owner record item N" below). The data supply decisions document (`APG_Data_Supply_Decisions`, "data supply decision N" below). |
| Affected locked sections (amended) | Sections 01, 02, 03, 04, 05, 06 and 11, each version 1.0 LOCKED, to become 1.1 (hashes below). |
| Affected locked sections (dependents, no text change) | Sections 00, 07, 08, 09, 10, 12, 13, 14, 15, 16 and 17. Section 18 too: its text is unchanged, but its package assets change. |
| Package assets affected | `MASTER_REQUIREMENTS_TRACEABILITY_MATRIX.csv`, `CROSS_SECTION_TERMINOLOGY_REGISTER.md`, `manifest.json`, `validate_handoff_package.py`, `README_HANDOFF.md`, `CLAUDE_HANDOFF_INSTRUCTIONS.md`, `SOURCE_SECTION_INVENTORY.json`, `PACKAGE_VALIDATION_REPORT.txt`, and a new controlled change register (section 6.7). |
| Related, outside the locked blueprint | The 8-layer design blueprint v0.1 is a design baseline, not locked; its 02 §2.11 and 11 §11.2 and §11.6 are dependents. The owner's own change requests CR-02, CR-05, CR-07, CR-08 and CR-10 (section 6.3). The defect change request for DC-1 to DC-13, raised after stage 1. |
| Exact requirement IDs | `CIA_RTM_IMPACT.csv` lists every insertion point, reworded line and dependent: by RTM ID, or by paragraph or table row where the RTM has no row. It has 1,360 rows over 1,071 distinct locked items: 888 with an RTM ID, 112 paragraphs and 71 table rows without one. `build_cia.py` reads the spans from the section documents themselves, not only from the RTM. It fails if an anchor is wrong, or if an insertion point is not the true end of its block. |

The locked package was checked before use:
- every file's SHA-256 matches its manifest;
- the manifest digest (dad3fa91…d89c) matches the package's validation report;
- `validate_handoff_package.py` passes (27 files, 19 sections, 2,712 RTM rows);
- the package archive `Anchor_Profit_Guardian_Blueprint_v1.0.zip` has SHA-256 487becab…d960.

| Section | Locked file version | SHA-256 (first 16 characters) |
| --- | --- | --- |
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
| C02 | Bring the 24 kinds of the second delivery loop, the two direct writes and the in-code authority register under the Section 04 intake. A regression baseline is taken first, and the move has its own change request. | S04 §20 (new bullet) | implementation obligation: S04 §3, §5, §8, §9, §11 and PG-DI-AC-01 to 06 already require it | draft 7, release A item 1 |
| C03 | Controls for each new channel: email sender checks; file scanning and safe parsing; entry screens that never edit a held record. | S04 §18.2 (new); PG-DS-AC-07, 08, 13 | addition | draft 7, intake stage table |
| C04 | Setup questions for the source registry, the Source Authority Register, the cost-code map (each match confirmed by a person), users and roles, the financial policy settings a builder owns, and the rule settings. Each is versioned and approved. | S04 §18.3 (new); PG-DS-AC-05 | addition | draft 7, "Setup questions"; data supply decision 8 |
| C05 | Eight logical entities and a data-gap lifecycle added to the domain model; the controlled entity register as an annex. | S03 §2 and §13 (table rows), S03 §2 (paragraph) | addition | revision 4, entity register |
| C06 | The field register and the field-coverage report, as a gate. | S03 §2 (paragraph), S04 §20, PG-DS-AC-12 | addition | revision 4, field-level coverage |
| C07 | The readiness record (and its scope), the onboarding data checklist, the missing-data list, nudges, the life of a data gap, and how an insight that is not switched on is shown. | S04 §14.1 (new); PG-DS-AC-09, 10; S02 PG-FR-026 | addition | draft 7, "Data readiness" |
| C08 | Decision 13: whenever a check or figure cannot be fully done, say what is missing, why it matters and what to do. | S04 §14.2 (new); PG-DS-AC-14; S02 PG-FR-026 | addition | owner record item 6 |
| C09 | Freshness limits per insight, starting from owner-approved thresholds, each with an owner and rationale. | S04 §14.1 | clarification of S04 §14 ("decision-aware freshness thresholds") and S16 §5 | data supply decision 10 |
| C10 | Detection-rule thresholds ship with owner-approved defaults, visible to the builder, which his approver accepts. | S06 §5.1 (new paragraph) | clarification of S06 §5.1 ("configurable within approved governance boundaries") | data supply decision 9 |
| C11 | Severity levels for the money side of a finding, set by the builder at setup: an amount, a percentage of the job, or both, whichever is reached first. No defaults. Safety and quality classification stays separate. | S06 §8 (new paragraph) | addition (new design and new code); questions 1, 2 and 4 | owner record item 9 and the dialogue of 2026-11-12 |
| C12 | (Folded into C04.) | | | |
| C13 | Extras and variations shown separately, as a breakdown of the one authoritative forecast. The cost of extra work is attributed to its instruction or variation and counted once. The builder records what happens after a variation is rejected. | S11 §8 and §8.2 (new); S05 §3.2 and §6; S03 §6.2 | addition, including one new financial view (section 4); question 3 | owner record item 5 |
| C14 | The authoritative forecast's budget and profit first; each item that is not final beside them, by category, with its what-if effect never added in. | S05 §3.2 (new bullet) | addition (new presentation across budget and profit); question 3 | owner record item 11 |
| C15 | Site capture devices enrolled; the shared-phone user recorded; the place not assumed reliable; workers see what was recorded about them; its privacy settled before it is built. | S04 §18.2 | addition; its privacy design waits for CR-05 | draft 7, Level 2 |
| C16 | Data supply questions added to Section 01 discovery, including the early site-capture gate. | S01 §3.7 (new) | addition | draft 7, "What discovery must answer" |
| C17 | How the data releases fit the build phases. | none (section 6.3) | no text change | draft 7, "Not proven yet" |
| C18 | Retention events through the intake, with a field definition. | the field register and Appendix B | addition to a controlled register | GPT's re-check of revision 4 |
| C19 | A value a person keys from an uploaded document, where no extraction exists, is confirmed by a second person with the verifier role. | S04 §18.2 | addition, stricter than S04 §18 | draft 7, release A item 4 |
| C20 | Who supplies, checks, corrects and approves each kind of record; the way in and supplier on every value; retrospective entries never rewrite a result already shown. | S04 §18.1, §18.2; S03 §3 (table rows); PG-DS-AC-04 | addition | draft 7, "Data supply governance and lifecycle" |
| C21 | The data supply registers and the M6 input contracts become controlled package artefacts; the version lines and amendment records of the seven sections. | S04 §20; the version line and lock record of each amended section; the package (section 6.7) | addition; version lines reworded | revision 4, registers; S18 §6 |

By section:

| Section | Title (as the section itself is titled) | Disposition | Additions (reworded lines) | Locked items touched | Change items |
| --- | --- | --- | --- | --- | --- |
| 00 | Control & Product Charter | dependent: reviewed, no text change | 0 (0) | 14 | C05, C21 |
| 01 | Discovery, Current-State Inventory & Assumptions Register | amended: v1.0 to v1.1; additions, and the version line reworded | 7 (2) | 65 | C16, C21 |
| 02 | Product Requirements, Actors & Workflows | amended: v1.0 to v1.1; additions, and the version line reworded | 3 (2) | 134 | C01, C04, C07, C08, C10, C11, C15, C21 |
| 03 | Domain Model & Canonical Financial Semantics | amended: v1.0 to v1.1; additions, and the version line reworded | 16 (2) | 153 | C05, C06, C07, C13, C14, C18, C20, C21 |
| 04 | Data Ingestion, Normalisation & Reconciliation | amended: v1.0 to v1.1; additions, and the version line reworded | 44 (1) | 115 | C01, C02, C03, C04, C06, C07, C08, C09, C10, C14, C15, C19, C20, C21 |
| 05 | Profitability Calculation Engine | amended: v1.0 to v1.1; additions, and the version line reworded | 4 (1) | 86 | C02, C04, C08, C13, C14, C18, C20, C21 |
| 06 | Active Intelligence & Profit Leakage Detection | amended: v1.0 to v1.1; additions, and the version line reworded | 3 (1) | 56 | C07, C08, C10, C11, C21 |
| 07 | Schedule, Delay & Holding-Cost Intelligence | dependent: reviewed, no text change | 0 (0) | 14 | C05, C08 |
| 08 | Materials, Global Markets & Procurement Intelligence | dependent: reviewed, no text change | 0 (0) | 47 | C08, C09, C21 |
| 09 | Labour, Productivity & Resource Intelligence | dependent: reviewed, no text change | 0 (0) | 28 | C05, C08, C15 |
| 10 | Recommendations, Prioritisation & Scenario Engine | dependent: reviewed, no text change | 0 (0) | 19 | C07, C11, C14 |
| 11 | Commercial & Revenue Intelligence | amended: v1.0 to v1.1; additions, and the version line reworded | 4 (1) | 49 | C05, C08, C13, C21 |
| 12 | Cash Flow, Working Capital, Retentions & Security | dependent: reviewed, no text change | 0 (0) | 19 | C08, C18 |
| 13 | Quality, Rework & Defect Intelligence | dependent: reviewed, no text change | 0 (0) | 12 | C08, C11 |
| 14 | Implementation Plan, Dependency Sequencing & Claude Handoff | dependent: reviewed, no text change | 0 (0) | 115 | C02, C07, C13, C14, C17 |
| 15 | Security, Privacy, Access Control & Governance | dependent: reviewed, no text change | 0 (0) | 73 | C01, C03, C15, C19 |
| 16 | Operational Reliability, Monitoring, Resilience & Recovery | dependent: reviewed, no text change | 0 (0) | 26 | C01, C03, C07, C09 |
| 17 | Testing, Acceptance, Verification & Release Readiness | dependent: reviewed, no text change | 0 (0) | 46 | C02, C06, C13 |
| 18 | Final Blueprint Handoff, Consolidation & Controlled Change Governance | reviewed; no text change; its package assets change (section 6.7) | 0 | none (S18 has no RTM rows: section 13) | C21 |

## 4. Does any locked meaning change?

Section 18 asks for extra care where a change touches a canonical financial definition. The owner's standing rule is that anything that changes a claim's meaning, relaxes a condition or widens scope comes to him first. Here is the answer, item by item.

- **No existing canonical financial definition changes.** Recognised margin, forecast final margin, cash-position-adjusted margin, the authoritative forecast, the revenue lifecycle states, realised saving and source authority all keep their locked meaning (section 6.6).
- **One new financial view is added (C13).** The extras and variations view (S05 DS002, S11 DS003) is a breakdown of the one authoritative forecast final margin, not a second margin:
  - each instruction or variation gets its approved revenue, and the actual cost, commitments and forecast cost to complete attributed to it;
  - the original scope is the remainder;
  - the parts add up exactly to the authoritative figure.

  This is new financial semantics, so it is treated as such. It is labelled with its definition as S03 §5 requires for every view. It triggers the financial-core regression suite (S17 §5) and the overlap suite (S17 §6). It needs its own fixtures and tests (section 6.4). How accruals and overhead are shared with an extra must be specified before it is built (S03 §6.3 already requires that for overhead allocation). Question 3 confirms it with the owner.
- **The financial part of severity is new design (C11), and it stays the financial part only.** S06 §5.1 requires "thresholds ... configurable within approved governance boundaries"; S06 §8 requires them "documented, testable and approved". Levels the builder sets, which are then approved, meet that. But severity is not only money:
  - S13 §13.4 grades quality findings on safety, regulation, structure and building performance;
  - S13 §13.4 also says "financial prioritisation must never override safety or mandatory quality requirements";
  - PG-RS-AC-05 says a score never bypasses safety, quality or approval constraints.

  So S06 DS002 limits the builder's levels to the money part. A finding's safety, quality, contractual and compliance classification is assessed on its own and is never lowered by a small or missing amount. A finding with no defensible amount (PG-AI-AC-07) shows that classification, marked as having no amount. Findings show "ungraded" until the levels are set and approved; that is a labelled state, not a default. Questions 1, 2 and 4 cover the open points.
- **C02, the move to one intake, changes no text but changes results.** The locked Section 04 already requires reconciliation, authority and entity resolution for every record kind; stage 1 does not yet meet that for 24 kinds. When the move is built, the rules see only reconciled records of those kinds, so some results will change. That is why the move has its own change request, with a saved baseline of today's results and every difference explained and signed off (S04 DS028). PG-DS-AC-03 ("a new way in changes no rule") says in its own words that it does not govern this move.
- **C10 says how "approved" is met for the detection defaults.** The defaults are documented, visible to the builder and accepted by his approver, so nothing is substituted silently (S04 §10, PG-DI-AC-11).
- **C13 adds no new revenue state.** S11 §8's "Disputed/rejected amount" stays one state. In S05 DS001 it is shown in two columns, disputed and rejected, by its recorded status. After a rejection the builder records what happens next:
  - "disputed" and "at his own cost" are recorded against the rejected state;
  - "resubmitted" and "withdrawn" are changes of state, made through the process S11 §8.1 requires, each with its own record (S11 DS001).

  The cost attribution (S03 DS014, S05 DS003) groups costs already counted; it never counts them twice (S03 §6.4, S05 §6, PG-PC-AC-02, PG-CR-AC-10).
- **C14 follows the locked rules and adds a presentation.** The locked rules it follows:
  - S05 §5.1 already requires one authoritative forecast;
  - S05 §3.2 already forbids treating unapproved variations or disputed claims as secured revenue;
  - S04 §9 already requires authoritative and provisional outcomes to be compared "without confusing their status";
  - S10 §7.1 isolates scenarios.

  The new part is the per-category columns across budget and profit, each with the effect the item would have if it went through. Those effects are what-if values: labelled, isolated, and never added in. For records on hold, they follow S04 §9's rules for provisional views (S05 DS001).
- **"Switched on" is new wording; it is not a new limit.** Onboarding asks only what the insights a builder switches on need (data supply decision 9, approved in principle). S02 §2.1's mandatory functional domains are product-level, and they stay. S04 DS002 adds that an insight not switched on, or not yet set up, is shown as such, never as "no issue" (S06 §3: "the absence of an alert is not proof").
- **One control is stricter than the locked text:** a value a person keys from an uploaded document needs a second person's confirmation (S04 DS022). Three additions restate locked controls for the new channels:
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
| Financial correctness | The percentage uses the wrong base, or no base exists. | A defined base (question 2); without it only the amount levels apply and the finding says so. |
| Security | New channels (email, uploads, phones) bring spoofed senders, malicious files, prompt injection in documents and lost devices. | S04 DS019 to DS023; PG-DS-AC-07; S15 §15.3 to 15.5, §15.9 and §15.10 apply to every new path; a nudge's link opens the form only after sign-in (S04 DS008). |
| Privacy | Site capture records people, places and photos. | Level 2, not in the first release; S09 §14 applies; its privacy design, including a worker's access to his own records, is settled before it is built (S04 DS023, CR-05); S15 §15.6 classifies the data. |
| Tenant isolation | A new path lets one builder's data reach another, for example through an email address. | The organisation is never taken from an address; PG-DS-AC-06 requires PG-DI-AC-14's isolation tests on every way in. |
| Approvals | Settings take effect without the right approval; or a one-person builder cannot use APG at all. | PG-DS-AC-05: every setting versioned and approved before it takes effect; question 1 settles the one-person case; the detection defaults are owner-approved and accepted by the builder's approver. |
| Auditability | A value cannot be traced to who supplied it, how and when. | PG-DS-AC-04; S03 DS010 to DS013 (channel, supplied_by, verified_by, retrospective); originals kept (S04 §10, DS019). |
| Operational resilience | Readiness reassessment floods the system or the builder; a stopped feed looks like no news. | Reassessment combined for large batches (S04 DS005); gap identity and noise control as S06 §9.1; PG-DS-AC-13 shows a failed or partial intake as such; the export-file way in stays available when an integration is not (S04 DS014; S16 §9 requires failed syncs never be read as "no change"). |
| Delivery | Builders don't supply data that takes too long to give; no extraction vendor is chosen yet. | Onboarding asks only what switched-on insights need; the pilot measures completion and effort; until extraction exists, values are keyed and confirmed by a second person. |

## 6. Downstream effects

### 6.1 Sections and requirements

`CIA_RTM_IMPACT.csv` lists every locked item the change items touch. Each is one of:
- an **insertion point**: text is added after it, and its own wording is unchanged;
- a **reworded version line**: the only locked text that changes;
- a **dependent**: read for knock-on effects, with no change needed.

Spans are read from the section documents, so text the RTM does not map is included. `CIA_DEPENDENT_TEXT.txt` holds the full text of every dependent.

No dependent needs new wording. Where an existing requirement already covers a new channel (for example S15 §15.5 tenant isolation, or S04 §12 human verification), the new channel is simply held to it through PG-DS-AC-06.

The M6 input contracts of revision 4 are approved with this change request as an accurate description of how today's code reads its inputs, with their stated limits. A stated limit is not accepted as meeting Section 08. For example, R07 does not check a quote's issue date, which S08 §5 asks to capture. Each limit stays recorded against its rule.

### 6.2 The requirements matrix (RTM)

- **New rows:** 81, one for each addition: paragraphs, bullets, headings, each table row separately, and the 14 acceptance criteria. Each has status "Specified — implementation status unverified", as every locked RTM row does.
  - New IDs use a series of their own (for example APG-S04-DS001), so they never collide with the RTM's numbered IDs.
  - The 14 acceptance criteria keep their own IDs (PG-DS-AC-01 to 14), as do PG-FR-026 and 027.
  - A table row is anchored as `table_index=T; row_index=R`, a new anchor form the RTM does not use yet.
- **Existing IDs are kept.** Each consolidation ID today is its paragraph index plus one (for example APG-S04-L0122 is paragraph 121). Inserted paragraphs move later paragraphs, so a fresh run of the same numbering would renumber them. The RTM is therefore regenerated by matching each existing row to its text and old index: it keeps the ID, updates only the anchor, and fails if any old ID would change. The rows affected are counted below.
- **Rows the RTM lacks.** The locked RTM has no row for some locked text this change request touches:
  - S02's functional requirements and actors tables (PG-FR-001 to 025 are not in the RTM);
  - S03's entity, common-field and lifecycle tables;
  - S06 §8's first paragraph;
  - S11 §8's state definitions;
  - S15 §15.6's retention paragraph;
  - the version lines.

  The change request proposes adding RTM rows for those it touches, in the forms above. The wider gap is a pre-existing observation (section 13).

- Proposed additions: 81 (38 paragraphs or bullets, 7 headings, 15 table rows, 14 acceptance criteria PG-DS-AC-01 to 14); each is one new RTM row
- Locked text reworded: 10 version lines (two in each of S01, S02 and S03, one in each of S04, S05, S06 and S11); nothing else
- Sections amended (v1.0 -> v1.1): 01, 02, 03, 04, 05, 06, 11
- Impact rows: 1360; distinct locked items touched: 1071 (888 with an RTM ID, 112 paragraphs and 71 table rows the RTM does not map); insertion points: 24 distinct anchors
- Sections reviewed as dependents only: 00, 07, 08, 09, 10, 12, 13, 14, 15, 16, 17

- Existing RTM rows whose paragraph-index anchor moves (they sit after the first inserted paragraph; their IDs are kept):
- S01: 61 of 139 rows (after paragraph 89)
- S02: 0 of 161 rows (after paragraph 175)
- S03: 251 of 256 rows (after paragraph 11)
- S04: 65 of 179 rows (after paragraph 121)
- S05: 129 of 156 rows (after paragraph 33)
- S06: 125 of 158 rows (after paragraph 39)
- S11: 52 of 84 rows (after paragraph 52)

- Pre-existing observation (outside this change request): locked text the RTM does not map, Sections 00-18
- S00: 11 paragraphs not mapped (of 155 non-empty), 0 table body rows not mapped
- S01: 16 paragraphs not mapped (of 155 non-empty), 10 table body rows not mapped
- S02: 15 paragraphs not mapped (of 176 non-empty), 60 table body rows not mapped
- S03: 22 paragraphs not mapped (of 278 non-empty), 55 table body rows not mapped
- S04: 10 paragraphs not mapped (of 189 non-empty), 0 table body rows not mapped
- S05: 21 paragraphs not mapped (of 177 non-empty), 0 table body rows not mapped
- S06: 16 paragraphs not mapped (of 174 non-empty), 0 table body rows not mapped
- S07: 23 paragraphs not mapped (of 148 non-empty), 0 table body rows not mapped
- S08: 27 paragraphs not mapped (of 128 non-empty), 0 table body rows not mapped
- S09: 38 paragraphs not mapped (of 123 non-empty), 0 table body rows not mapped
- S10: 24 paragraphs not mapped (of 115 non-empty), 0 table body rows not mapped
- S11: 29 paragraphs not mapped (of 113 non-empty), 0 table body rows not mapped
- S12: 19 paragraphs not mapped (of 164 non-empty), 0 table body rows not mapped
- S13: 24 paragraphs not mapped (of 191 non-empty), 0 table body rows not mapped
- S14: 24 paragraphs not mapped (of 235 non-empty), 0 table body rows not mapped
- S15: 22 paragraphs not mapped (of 210 non-empty), 0 table body rows not mapped
- S16: 14 paragraphs not mapped (of 157 non-empty), 0 table body rows not mapped
- S17: 46 paragraphs not mapped (of 223 non-empty), 0 table body rows not mapped
- S18: 140 paragraphs not mapped (of 140 non-empty), 0 table body rows not mapped
- total: 541 paragraphs (cover lines and lock-record lines included; all 140 of Section 18), 125 table body rows


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
| Owner's CR-10 | Verified profit ledger. It overlaps C14 (verified figures first) and C13 (the breakdown). Its text is not in this pack, so the overlap must be checked against it before this change request is approved (section 8). | CR-10 |

**How releases fit the phases (C17).** The design calls its scopes of data "releases" (A, B, later). Sections 14 and 18 number the build phases differently:
- **Section 18 §8:** phase 5 is security, reliability and recovery; phase 6 is acceptance.
- **Section 14:** phase 5 (§14.8) is interface and user workflows; phase 6 (§14.9) is verification; phase 7 (§14.10) is database and integration closure.

This assessment uses Section 14's numbering. Every release starts after Phase 0 and the Discovery Exit Report. The first release's work falls in:
- **Phase 1:** the intake, source authority, identity, and the readiness record's shared data-quality status (§14.4).
- **Phase 2:** the financial policy.
- **Phase 3:** the domain rules' use of the readiness record.
- **Phase 5:** the user-facing parts: entry screens, setup questions, the missing-data list and nudges, the extras panel and the verified-first display (§14.8).

No release reaches production use without the evidence of phases 4, 6 and 7. No text change is needed. The numbering difference is reported in section 13.

### 6.4 Tests, regression suites and immutable fixtures

This change request changes no code and no test. The table names the stage 1 tests and fixtures each later build will touch (freeze ee1ce3ec), so the build change requests carry them.

| Change item | Stage 1 tests the build will touch | Fixtures |
| --- | --- | --- |
| C02, C03, C19 | test_ingest_pipeline, _reconcile, _mapping, _contracts, _boundaries, _adversarial, _support, _golden; test_fin_intake, test_det_intake, test_mkt_intake; test_fin_corpus, test_det_corpus, test_mkt_corpus; test_tenancy | regression/GOLDEN_M2, GOLDEN_M3, GOLDEN_FIN, GOLDEN_DET, GOLDEN_MKT and every BASELINE file. The move to one intake needs a new, separately approved baseline; today's files are kept, never overwritten. |
| C04 | test_source_authority; test_f67_policy_approval and test_f671 to f674; test_status_model | none |
| C10, C11 | test_det_policy, test_det_policy_bounds, test_det_detect, test_det_findings, test_det_noise, test_det_golden, test_mkt_detect, test_materiality_engine | GOLDEN_DET and GOLDEN_MKT (severity values change only under the defect change request) |
| C13, C14 | test_fin_revenue, test_fin_commitments, test_fin_costs, test_fin_forecast, test_fin_bridge_book, test_fin_golden | GOLDEN_FIN, BASELINE_M4 |
| C18 | test_fin_cash, test_fin_intake | none |

Section 17 §5 governs every fixture change: review, rationale, versioning and a regression impact assessment, and expected results are never changed to make a failing build pass. A change to cost allocation or to a margin view (C13) triggers the financial-core regression suite. APG-M8.1, the earlier audited packages and the M10 archive stay untouched.

**New tests each build must add.** They are named here so the RTM rows can point to them; IDs are given when they are built.
- PG-DS-AC-01 to 14:
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
  - every message carries what to do, and the message list fails on an uncovered message (14).
- **The extras breakdown:** it adds up exactly to the authoritative forecast final margin, and a cost attributed to a variation is counted once (financial-core and overlap suites, with new fixtures).
- **The what-if columns:** a what-if amount never enters the main figure; a held record's what-if is visible only to authorised reviewers.
- **Severity:** graded by amount, by percentage, and by both, whichever is reached first; ungraded when not set; amount levels only when the base is missing; a safety classification never lowered by a small or missing amount.
- **Variations:** a resubmitted or withdrawn variation changes state only through the S11 §8.1 process.
- **Document values:** a keyed value from an uploaded document counts only after a second person confirms it.
- **Retrospective entries:** a backdated entry leaves a shown result and its records intact, and marks the insight for reassessment.

### 6.5 Acceptance criteria

PG-DS-AC-01 to 14 are new; they sit in S04 §19 after PG-DI-AC-18. No existing acceptance criterion changes.
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
| Potential, estimated, approved, recognised, invoiced and collected revenue | unchanged; S11 DS001 records the builder's next step after a rejection; resubmission and withdrawal go through the lifecycle process |
| Cash, scheduled receipts and payments, scenarios | unchanged; a what-if value is a scenario-only value |
| Source authority | unchanged; S04 DS015 restates that the register decides, never the latest arrival |
| Cross-domain overlap / net impact | unchanged; S05 DS003 applies it to costs attributed to variations |
| Unknown external outcome; closed database-dependent item | unchanged |

**New terms to add, each with its section:** way in (and Level 1, 2, 3); readiness record; data gap; nudge; retrospective record; setup question; switched on (an insight a builder has set up and turned on); ungraded finding; what-if value (a scenario-only value); extras and variations view (a breakdown of forecast final margin); verifier role (a permission, to be mapped to an S02 §3 actor); product owner (as the approver of the detection defaults); data release (a scope of data, distinct from a build phase and from Section 17's release gates); controlled data-supply registers.

### 6.7 Handoff instructions, manifest, hashes, change register and closure register

After approval, and only then:

- **Section files.** Sections 01, 02, 03, 04, 05, 06 and 11 are issued as version 1.1. Each has its version line reworded and an amendment record added to its lock record, as worded in section 12. Each version 1.0 file and its hash is kept as history (S18 §6), in a history folder of the package.
- **The validator must change first.** `validate_handoff_package.py` looks only for files named `..._v1.0_LOCKED.docx`. A copy of the locked package with Section 04 renamed to version 1.1, and its manifest updated, was run through it; it failed with "REQUIRED SECTION DOCUMENT MISSING: 04". It must be amended to take each section's current version from the manifest, and to accept the history files the manifest lists. That amendment is tested itself (T18-05, T18-08).
- **A controlled change register.** S18 §2 requires one, and the package today holds only the CR template. A change register is created, and this change request is entered in it with its assessment, approval and closure.
- **Manifest and hashes.** New entries for:
  - the seven version 1.1 files and the history files;
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
| Paragraph comparison of each version 1.1 file with its version 1.0 | each differs only by the additions and the reworded version lines in `CIA_PROPOSED_TEXT.csv`, word for word; nothing else is reworded or removed | T18-08 |
| RTM regeneration and validation | all 2,712 existing IDs kept (by text and old index); 81 new rows plus the backfilled rows; no blank, duplicate or orphaned ID | T18-02 |
| Fresh extraction and hash check | every controlled file's digest matches the new manifest; the history files are listed | T18-01, T18-05 |
| Terminology review | the new terms added; no collision with a canonical term | T18-07 |
| Cascade check | every new requirement has an RTM row and a named test to come; no dependent left unreviewed | T18-03 |
| Independent review of the version 1.1 texts | the texts match this assessment as approved | S18 §6 |

## 8. Review, approval, versioning and verification after the change

- **Reviews so far.**
  - The design and revision 4 went through: five independent agent checks of revision 4; GPT's check and scoped re-check of revision 4; three agent checks of the design; and a GPT and a Gemini review of the design. Every finding was fixed or answered (in the packs). The three small points from GPT's re-check were fixed by Claude and have not been re-checked independently.
  - This assessment: one independent agent check of draft 1 (5 blocking, 19 should fix, 21 minor), all fixed in draft 2 (`CHECK1_FIXES_CIA.md`).
- **Reviews before approval.**
  1. A scoped independent agent check of what changed in draft 2, with every finding fixed.
  2. One GPT pass, listing every problem at once.
  3. Gemini only if the owner wants a design view.
  4. The overlap with the owner's CR-10 (verified profit ledger) checked against its text.
- **Approval authority.** Emmanuel, product owner. The dispositions open to him: approve; approve with conditions; send back for changes; reject.
- **Versioning.** The seven sections become version 1.1, each with its reworded version line and an amendment record naming this change request and its approval. Version 1.0 and its hash are kept.
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
| Revised versions and new hashes | [Sections 01, 02, 03, 04, 05, 06, 11 v1.1; SHA-256 of each; new manifest digest] |
| Verification results and defects | [section 7 checks: results, defects, retests] |
| Closure decision, owner and date | [ ] |

## 10. Matters carried from earlier reviews

| Matter | Raised by | Where it stands |
| --- | --- | --- |
| M01 The ten shared financial foundation decisions (8-layer 02 §2.11) | GPT | Open owner decisions, not settled here; they are product-level, not builder setup answers (S04 DS026). Needed before the first release's financial policy is built: the cost taxonomy (decision 3, with the cost-code map), how committed cost and cost to complete are worked out (6), how variations are treated (7), and who approves a baseline (8). Freshness (9) is approved in principle (data supply decision 10). The rest are needed before the financial core is built. |
| M02 The Source Authority Register and its approver | GPT | The register is built through setup questions and approved before it takes effect (S04 DS026). Who approves it is an owner decision before first-release item 3. Claude's suggestion: the finance controller (S02 §3, "financial controls"; PG-FR-025). |
| M03 Baseline and assessment governance | GPT | Baselines: locked in S05 §5.1 and §10 and 8-layer decision 8; nothing added here; settled before baselines are built ("later"). Assessments (calculation runs) are first-release records; they are governed by S03 §14.3 and S05 §13 (reproducibility, immutable inputs), which this change request keeps; who may start, rerun or supersede a run is settled before item 6 is built. |
| M04 The commitment policy and status maps | GPT | Supplied through setup questions as builder-owned settings of the financial policy (C04). Their content follows M01's decisions 6 and 7. DC-7 shows why a held variation must not map to approved. |
| M05 Labour data privacy (S09 §14) | GPT | Applies to site capture; settled in CR-05 before it is built (S04 DS023). The first release has no site capture. |
| M06 Retention and security state handling | GPT | Retention events move into the intake with a field definition (C18, Appendix B). The definition must meet two locked obligations today's code does not: an explicit currency (S03 §11.1) and an associated contract as well as project (S03 §10.1). The code's states (withheld, claimed, approved, disputed, released, received) also differ from S03 §13's illustrative lifecycle (which has "Under Review" and no "received"); the mapping is settled in the field definition. Security instruments stay as S03 §10.2 says. Not settled yet. |
| M07 Corrected and disputed data | GPT | S04 §13 already governs corrections. The additions keep what was first received, mark retrospective entries, and never rewrite a shown result (S04 DS024). |
| M08 How the cost of extra work links to its instruction or variation | owner, Claude | Proposed in Appendix C; S03 DS014 and S05 DS002, DS003; question 3. |
| M09 Whether Section 11 needs a clarification for the extras panel | owner, Claude | Yes: S11 DS001 to DS003. |
| M10 How the builder's settings are approved | owner, Claude | Question 1 (all settings, not only severity). |
| M11 Data retention and archiving after close-out, and when a customer leaves | GPT | Checked against Sections 09 and 15 to 17. S15 §15.6 already requires, for each data category, a retention period or rule, archiving and deletion, and legal holds; S16 §8 covers backups. So close-out is covered. What export a leaving customer receives is not stated. No change request now; it is settled with the platform's conventions in discovery. |
| M12 The retention-event (E77) field definition | GPT's re-check | Appendix B, with M06's two open obligations. |
| M13 DC-13's scope | GPT's re-check | Fixed in revision 4 by Claude (MP02, MP03, MP04, MP05 and MP09 named); not re-checked independently. |
| M14 The code-read report's column heading | GPT's re-check | Fixed in revision 4 by Claude; not re-checked independently. |
| M15 The 100 entities cross-checked against every row of the Master RTM | revision 4's next steps | Not done. Needed before the controlled entity register becomes an annex (S03 DS009); added to section 8's steps after approval. |
| M16 The code-read scan is not a proof | GPT's re-check | The field-coverage report (PG-DS-AC-12, S04 DS029) rests on a scan that "does not independently prove" the call-path analysis. So each rule's inputs are confirmed by that rule's tests when the rule is next changed, and the report is never cited as proof on its own. |

**Outside this change request:**
- the five developer entities (the locked blueprint does not cover the developer capability; they are listed in the register for information only and have their own change request);
- the reviewers' further ideas: back-to-back claim checks, adjudication evidence packs, statutory declaration checks, a learning cost-code map (each its own change request);
- sharing data between related companies or joint ventures (its own decision, weighed against tenant isolation);
- the DC fixes;
- stage 2.

## 11. Questions for the owner

**A correction first.** When question 1 was first put to the owner, Claude said every setting in APG only counts once a second person approves it. That is not fully true today: the code refuses an approval by the person who entered a setting (F-67), but it grades findings with severity levels whether or not they are approved, flagging them "not approved" (defect candidate DC-11). The question was corrected the same morning.

**Question 1. Can a builder who is the only person using APG approve his own settings?** Every setting (the cost-code map, the status maps, the rule settings, the severity levels and the rest) takes effect only once approved (S04 DS026, PG-DS-AC-05). The code already refuses an approval by the person who entered the setting. So a builder with only one person in APG could never get any setting approved.
- **Option A:** a second person (for example a bookkeeper added as an approver) must approve. Until then, everything that depends on the setting shows "not approved yet".
- **Option B:** where the builder has only one authorised person, he may approve his own settings. Each such setting, and every figure that uses it, is permanently marked "approved by the person who entered it". With two or more people, the two-person rule applies.

S02 §3.1 separates preparing from approving "where practical", so Option B fits the blueprint. But it loosens the check the code has today, so it needs the owner's yes. Claude suggests Option B, so a one-person builder is not locked out. Asked of the owner on 2026-11-13; answer pending.

**Question 2. A percentage of what?** "2% of the job" needs a base. Claude suggests the current approved contract value: the original contract plus approved variations. For example, on a $5,000,000 job with $100,000 of approved variations, 2% is $102,000. Where the base is missing (no contract value recorded yet), only the dollar levels apply, and the finding says so. Other possible bases are the forecast final cost or the forecast profit.

**Question 3. What do the main budget and profit include, and how does the extras panel split them?** You said the main figure counts only what is 100% verified. Two things need confirming.

First, part of any job's profit is the forecast of what is still to be spent: an estimate the builder approves, not an invoice. Second, approved variations are approved revenue, so they belong in the main figure, and the extras panel then shows how the main figure splits between the original build and each extra.

For example:
- **Main figure:** contract $5,000,000 plus one approved variation of $200,000, so revenue is $5,200,000. Spent and invoiced, $3,100,000; approved forecast to finish, $1,600,000. Main profit: $500,000, labelled as a forecast.
- **The extras panel splits that $500,000:**
  - the variation: $200,000 revenue less $150,000 cost attributed to it, so $50,000 profit;
  - the original build: the other $450,000.
- **Beside the main figure, never in it:** a variation waiting for approval, +$80,000 if approved; a disputed claim, −$20,000 if lost.

Claude suggests: the main figure uses only approved and verified records plus the approved forecast to finish, labelled as a forecast; approved variations are in it; the panel is a split of it that adds up exactly; and everything not final sits beside it. Is that what you mean?

**Question 4. The dollar and percentage levels grade the money side only.** You decided the builder sets the severity levels. The blueprint also grades findings on safety and quality, and says money must never override safety (S13 §13.4).

For example: a subcontractor's insurance has expired. There is no dollar amount, but it is serious. Or a cheap defect lets water into a wall.

Claude's design: the builder's dollar and percentage levels grade how much money is at stake. A safety or quality problem is graded on its own and is never made "low" because the amount is small or unknown. Is that right?

**Also at approval:** the number for this change request in your list.

## 12. Proposed wording, section by section

Every addition and every reworded line, with its ID and the locked text it follows. Square brackets mark the points waiting for questions 1 to 3 and the approval details. The same content is in `CIA_PROPOSED_TEXT.csv`.

### Section 01 (Discovery, Current-State Inventory & Assumptions Register)

Added after **S01 paragraph 89 (no RTM row)**, which reads: "Record which checks can run immediately and which require unavailable services or access."

- **APG-S01-DS001** (heading 2; change item C16): 3.7 Data supply readiness
- **APG-S01-DS002** (bullet; change item C16): Which systems the pilot builders use for each kind of data, with a sample export from each, to confirm the systems survey of the data readiness change request.
- **APG-S01-DS003** (bullet; change item C16): For each file the first release relies on, whether the pilot builder can actually produce it; where it cannot, the readiness record shows the gap and its fallback.
- **APG-S01-DS004** (bullet; change item C16): What site staff record today, on what device, and whether site capture must work offline; this is an early gate, and if a first-pilot insight depends on site facts recorded as they happen, that capture is brought forward.
- **APG-S01-DS005** (bullet; change item C16): How often each kind of data changes, which sets the case for each integration.
- **APG-S01-DS006** (bullet; change item C16): Whether users and roles come from the Anchor platform, and how organisations, legal entities and projects are represented in its tenant model.

Added after **APG-S01-C0155**, which reads: "Evidence boundary: this lock approves the discovery mandate, not the live repository's compliance with it. Repository findings, test results, security status an…"

- **APG-S01-DS007** (amendment record; change item C21): Version 1.1 amendment record: amended by change request APG-CR-DSR [number to be given at approval], approved by [approver] on [date], after its Section 18 §6 cascade impact assessment. The amendment adds text only; the added text is listed in that change request. Version 1.0 and its SHA-256 are kept as history.

Reworded: **S01 paragraph 3 (no RTM row)**, which reads today: "VERSION 1.0 — LOCKED"

- **APG-S01-DS008** (version line; change item C21): VERSION 1.1 — LOCKED (amended by change request APG-CR-DSR [number to be given at approval]; version 1.0 kept as history)

Reworded: **S01 paragraph 151 (no RTM row)**, which reads today: "Version: 1.0"

- **APG-S01-DS009** (version line; change item C21): Version: 1.1 (see the amendment record below)

### Section 02 (Product Requirements, Actors & Workflows)

Added after **S02 table 3 row 25 (no RTM row)**, which reads: "PG-FR-025 | Support finance-controller review and appropriate segregation of duties for material financial approvals, retention/security decisions and working-c…"

- **PG-FR-026** (table row; change item C07, C08): PG-FR-026 | For each insight, tell the builder what data it needs, what is missing, who usually holds it and how to supply it; whenever a check or figure cannot be fully done, say what is missing, why it matters and what the builder is to do.
- **PG-FR-027** (table row; change item C01): PG-FR-027 | Provide, for every data entity Profit Guardian needs, at least one way to supply it that does not depend on the builder's software; adding a way in never changes a detection rule or financial figure.

Added after **APG-S02-C0176**, which reads: "Evidence boundary: this lock approves the intended product requirements and governance boundaries. It does not establish that any source integration, platform r…"

- **APG-S02-DS001** (amendment record; change item C21): Version 1.1 amendment record: amended by change request APG-CR-DSR [number to be given at approval], approved by [approver] on [date], after its Section 18 §6 cascade impact assessment. The amendment adds text only; the added text is listed in that change request. Version 1.0 and its SHA-256 are kept as history.

Reworded: **S02 paragraph 3 (no RTM row)**, which reads today: "VERSION 1.0 — LOCKED"

- **APG-S02-DS002** (version line; change item C21): VERSION 1.1 — LOCKED (amended by change request APG-CR-DSR [number to be given at approval]; version 1.0 kept as history)

Reworded: **S02 paragraph 172 (no RTM row)**, which reads today: "Version: 1.0"

- **APG-S02-DS003** (version line; change item C21): Version: 1.1 (see the amendment record below)

### Section 03 (Domain Model & Canonical Financial Semantics)

Added after **S03 table 1 row 20 (no RTM row)**, which reads: "Outcome record | Evidence of the realised financial or operational result following an action."

- **APG-S03-DS001** (table row; change item C05): Variation and instruction | Client variation, site instruction or direction, with its commercial states (Section 11 §8) and the cost attributed to it (Section 05 §6).
- **APG-S03-DS002** (table row; change item C05): Programme activity and progress | Activity, relationship, calendar and progress record of a programme version, approved or working (Section 07 §3).
- **APG-S03-DS003** (table row; change item C05): Payment claim and certificate | Progress claim, payment schedule or certificate and its states (Section 11 §5).
- **APG-S03-DS004** (table row; change item C05): Labour record and rate | Timesheet entry, work allocation and labour rate (Section 09 §3), subject to Section 09 §14.
- **APG-S03-DS005** (table row; change item C05): Document | Original file or message kept as evidence, with its hash.
- **APG-S03-DS006** (table row; change item C05): Policy and settings record | Versioned, approved configuration: source registry entry, source authority rule, cost-code map, the financial policy settings a builder owns, and rule settings.
- **APG-S03-DS007** (table row; change item C05): Readiness record | Per insight and the scope it applies to, the state of each input and each data gap (Section 04 §14.1).
- **APG-S03-DS008** (table row; change item C05): Data gap | A missing, unverified, conflicting, stale or non-authoritative input, with its identity and lifecycle (Section 04 §14.1).

Added after **APG-S03-C0012**, which reads: "Use existing Anchor primitives where suitable. Do not create duplicate canonical entities solely because Profit Guardian needs a different view. Repository insp…"

- **APG-S03-DS009** (paragraph; change item C05, C06): The controlled entity register, an annex to this section, lists every entity Profit Guardian needs, its blueprint basis, its required field groups, its ways in and their state; it is a data inventory, mapped to existing Anchor entities in Section 01 discovery, not a database schema. Entities it lists as outside this blueprint (the developer entities) are listed for information only and are not governed by it. A field register gives each entity's fields; it becomes the validated schema register before any entry screen is generated from it.

Added after **S03 table 2 row 14 (no RTM row)**, which reads: "schema_version | Version of the canonical representation where needed."

- **APG-S03-DS010** (table row; change item C20): channel | The way in that supplied the record (import file, document or email, entry screen, setup question, site capture, integration).
- **APG-S03-DS011** (table row; change item C20): supplied_by | The person or system that supplied it, and its trust level.
- **APG-S03-DS012** (table row; change item C20): verified_by / verified_at | The person who verified a material value, and when, where verification is required.
- **APG-S03-DS013** (table row; change item C20): retrospective | Set when the record was entered after the event it describes.

Added after **APG-S03-L0072**, which reads: "Verified cost savings."

- **APG-S03-DS014** (bullet; change item C13): Cost of extra work: actual cost or commitments attributed to the instruction or variation they were incurred for; a grouping of costs already counted, not a separate cost (Section 05 §6).

Added after **S03 table 4 row 8 (no RTM row)**, which reads: "Outcome | Pending Verification → Partially Realised / Realised / Not Realised / Reversed"

- **APG-S03-DS015** (table row; change item C07): Data gap | Open → Assigned → Awaiting Evidence → Resolved / Suppressed / Superseded, with Reopened (Section 04 §14.1).

Added after **APG-S03-C0278**, which reads: "Evidence boundary: this lock approves the semantic specification. It does not establish that existing Anchor services, schemas, accounting conventions or data f…"

- **APG-S03-DS016** (amendment record; change item C21): Version 1.1 amendment record: amended by change request APG-CR-DSR [number to be given at approval], approved by [approver] on [date], after its Section 18 §6 cascade impact assessment. The amendment adds text only; the added text is listed in that change request. Version 1.0 and its SHA-256 are kept as history.

Reworded: **S03 paragraph 3 (no RTM row)**, which reads today: "VERSION 1.0 — LOCKED"

- **APG-S03-DS017** (version line; change item C21): VERSION 1.1 — LOCKED (amended by change request APG-CR-DSR [number to be given at approval]; version 1.0 kept as history)

Reworded: **S03 paragraph 274 (no RTM row)**, which reads today: "Version: 1.0"

- **APG-S03-DS018** (version line; change item C21): Version: 1.1 (see the amendment record below)

### Section 04 (Data Ingestion, Normalisation & Reconciliation)

Added after **APG-S04-L0122**, which reads: "Keep data-quality warnings visible and traceable to the affected calculation or recommendation."

- **APG-S04-DS001** (heading 2; change item C07): 14.1 Data readiness — mandatory
- **APG-S04-DS002** (paragraph; change item C07): Maintain a readiness record for each insight (detection rule, financial figure, market figure and any later insight) and the scope it applies to: a project, the organisation, a supplier, the portfolio or external data. It states the insight's state from its own gate (eligible, qualified, blocked or unavailable) and, for each input, how far it has reached: capture available, validation available, authority established, reconciliation available, decision-eligible. An insight is never shown as eligible while an input it needs is missing, unverified or stale. An insight that is not switched on, or not yet set up, is shown as such, never as finding no issue (Section 06 §3).
- **APG-S04-DS003** (bullet; change item C07): For each gap, record the entity and field, the period, the source, the reason (missing, unverified, conflicting, stale, not authoritative, or the underlying record does not exist), the likely holder, the action owner, the approver where one is needed, and the way in that supplies it, saying plainly when that way in is not built.
- **APG-S04-DS004** (bullet; change item C07): Give each gap a stable identity (entity, field, period and source) and a lifecycle: open, assigned, awaiting evidence, resolved, suppressed, reopened, superseded. A gap found again updates its existing record and nudge; suppression windows and re-notification rules follow Section 06 §9.1.
- **APG-S04-DS005** (bullet; change item C07): Reassess readiness at setup, after each intake batch or material change of state (combined for a large batch, but prompt), on a schedule, and whenever a record is corrected, quarantined, superseded or revoked. Raise a shared missing setting once, with the projects it affects.
- **APG-S04-DS006** (bullet; change item C09): An insight may set a tighter freshness limit than its source's default for the inputs it depends on; an overall fresh status never hides a stale critical input. Starting thresholds are owner-approved parameters, each with a documented owner and rationale (Section 16 §5), reviewed in the pilot.
- **APG-S04-DS007** (bullet; change item C07): Show gaps with their factors side by side, as Section 10 §4 requires for findings: the amount affected, urgency, confidence in that amount, whether the person can act now, and what depends on it. A gap is never called a loss or confirmed leakage; any amount comes from a traceable Section 05 calculation or is labelled an estimate.
- **APG-S04-DS008** (bullet; change item C07): A nudge names the period, the field and the fix, and links to the way in that fixes it only after sign-in; no link lets anyone approve or change data without signing in.
- **APG-S04-DS009** (bullet; change item C07): At onboarding, show the builder a data checklist: for the systems he uses, which data their export files and a template can supply and which must come another way, with the way in for each; where that is a judgement and not a confirmed sample export, say so.
- **APG-S04-DS010** (heading 2; change item C08): 14.2 Telling the builder what is needed — mandatory
- **APG-S04-DS011** (paragraph; change item C08): Whenever a rule, figure or other insight cannot fully do a check or produce a figure, it must say so: what is missing, why it matters and what the builder is to do. No case may be silent, and nothing may be shown as complete when it is not. Each such message is proven by a test when it is built. A list of the messages, generated by scanning the code, is kept as a controlled artefact and fails when the code gives a message it does not cover.

Added after **APG-S04-L0148**, which reads: "Manual entry must not be a bypass around approval or audit requirements."

- **APG-S04-DS012** (heading 2; change item C01): 18.1 Ways of supplying data — mandatory
- **APG-S04-DS013** (paragraph; change item C01): Every fact a person or system supplies, through any way in (import file, document or email, entry screen, setup question, site capture, integration), enters through the intake this section defines, with the same envelope (organisation, project, channel, the person or system, and the time) and the same control checkpoints; nothing writes a supplied fact to the store directly. Records Profit Guardian calculates are written by their calculation runs, with the run recorded (Section 03 §14.3).
- **APG-S04-DS014** (bullet; change item C01): Every entity in the controlled entity register that this blueprint governs has at least one Level 1 way in that needs no particular builder software: an import template, document or email capture, an entry screen, a setup question, or a record Profit Guardian calculates. Site capture (Level 2) and integrations (Level 3) reduce effort; neither is ever the only way in, and a source system's export file through a template stays available when its integration is not.
- **APG-S04-DS015** (bullet; change item C01): Adding a way in, or a builder changing systems, may change the intake; it must not change any detection rule or financial figure, its logic or its test results. Teaching a rule or figure to use data it does not read today is a change to that rule under its own change request. Where two ways in supply the same field, the Source Authority Register decides which governs, never the most recent arrival.
- **APG-S04-DS016** (bullet; change item C01): A way in that is not built is never offered to the builder as available.
- **APG-S04-DS017** (bullet; change item C20): For each kind of record, name its supplier, checker, corrector, approver and the owner accountable if it stays missing; one person may hold several of these roles, and they stay distinct in the record.
- **APG-S04-DS018** (heading 2; change item C03): 18.2 Channel controls — mandatory
- **APG-S04-DS019** (bullet; change item C03): Email capture verifies the sender and never takes the organisation from the address alone (§6); a verified sender does not make a document genuine or authorised (§5 and §12 still apply). Original messages and attachments are kept.
- **APG-S04-DS020** (bullet; change item C03): Every uploaded file, attachment and photo is scanned and parsed in isolation within size, archive and resource limits before it is read, and treated as untrusted content (Section 15 §15.9); a malformed or unsupported file is rejected with a reason.
- **APG-S04-DS021** (bullet; change item C03): Entry screens and setup questions carry the signed-in person, pass the same validation as an imported row, and need approval where the register requires. They never edit a held record: correcting a quarantined or pending record goes through the review workflow (§9, §13).
- **APG-S04-DS022** (bullet; change item C19): Where a person keys a material value from an uploaded document because no extraction is available, a second person with the verifier role confirms it before it counts. Each value keeps its own confirmation and provenance, also when confirmation is done in batches.
- **APG-S04-DS023** (bullet; change item C15): Site capture devices are enrolled to the organisation; on a shared device the signed-in user is recorded; the time is checked against the server; each record says how its place was established, and the device location is not assumed reliable. Workers can see what was recorded about them, and a disputed record goes through the correction route (§13). Site capture's privacy requirements follow Section 09 §14; they, and a worker's access to his own records (an actor Section 02 §3 does not yet list), are settled before site capture is built.
- **APG-S04-DS024** (bullet; change item C20): A record entered after the event it describes is marked retrospective. A backdated entry never rewrites a result already shown: the earlier result and the records it used stay on record, and the affected insight is reassessed and labelled.
- **APG-S04-DS025** (heading 2; change item C04): 18.3 Setup questions — mandatory
- **APG-S04-DS026** (paragraph; change item C04): Policies, maps, rates and settings the builder sets (the source registry, the Source Authority Register, the cost-code map, users and roles where the platform does not supply them, the financial policy settings the builder owns, such as its status maps and the choices Section 05 leaves to the business, and the rule settings) are supplied through setup questions, versioned, submitted through the intake, and take effect only after approval by the required role [approval where the builder has only one authorised person: owner decision, question 1]. Onboarding asks only what the insights the builder switches on need. The product-level financial decisions are not builder setup answers.
- **APG-S04-DS027** (bullet; change item C04): The cost-code map is required before any figure that groups by cost code; Profit Guardian suggests matches and a person confirms each one. A record whose cost code is not mapped yet is accepted with warnings (§8), held only from the figures that need the code, and listed for the person who owns the mapping.

Added after **PG-DI-AC-18**, which reads: "PG-DI-AC-18: The baseline test and evidence reports distinguish specification acceptance from proof of live implementation."

- **PG-DS-AC-01** (acceptance criterion; change item C01): Every fact a person or system supplies enters through the Section 04 intake; nothing writes a supplied fact to the store directly. Records APG calculates are written by its calculation runs, with the run recorded.
- **PG-DS-AC-02** (acceptance criterion; change item C01): Two inputs that describe the same source fact (the same values, units, currency, date and time and tax basis) and meet the same authority and verification conditions, supplied through any two ways in, are mapped to identical field values and give the same rule outcome; only the provenance differs. Shown by a test.
- **PG-DS-AC-03** (acceptance criterion; change item C01): Adding a way in changes no detection rule or financial figure logic and no rule test result. Changes to the intake code are allowed. (The one-off move of today's 24 kinds onto the reconciled intake is governed by its own change request.)
- **PG-DS-AC-04** (acceptance criterion; change item C20): Every value records its channel, the person or system that supplied it, and the time.
- **PG-DS-AC-05** (acceptance criterion; change item C04): No manual way in (templates, documents, entry screens, site capture, setup answers) bypasses validation, approval or audit (§18). Setup answers are versioned and take effect only after approval by the required role.
- **PG-DS-AC-06** (acceptance criterion; change item C01): Every way in meets PG-DI-AC-01 to 18, including tenant isolation tested on that path (PG-DI-AC-14), human verification of extracted values (PG-DI-AC-07) and quarantine isolation (PG-DI-AC-03 to 05).
- **PG-DS-AC-07** (acceptance criterion; change item C03): Every uploaded file, email attachment and photo is scanned and parsed in isolation within size, archive and resource limits before it is read; a malformed or unsupported file is rejected with a reason.
- **PG-DS-AC-08** (acceptance criterion; change item C03): A held record is corrected only through the review queue, never by an entry form.
- **PG-DS-AC-09** (acceptance criterion; change item C07): The readiness record is reassessed at setup, after each intake batch or material state change, on its schedule, and when a record is corrected, quarantined, superseded or revoked; an insight is never shown as eligible while an input it needs is missing, unverified or stale.
- **PG-DS-AC-10** (acceptance criterion; change item C07): Each data gap has a stable identity (entity, field, period, source) and moves through open, assigned, awaiting evidence, resolved, suppressed, reopened and superseded; a gap found again updates its existing nudge instead of creating a new one; suppression windows and re-notification rules are defined and tested (Section 06 §9.1).
- **PG-DS-AC-11** (acceptance criterion; change item C01): A way in that is not built is never offered to the builder as available.
- **PG-DS-AC-12** (acceptance criterion; change item C06): Every field a current rule or figure reads, including setting fields, has at least one built way in that carries it, with its authority and verification requirement met; and each way in, when built, carries every field of the entities it serves. Shown by a generated field-coverage report that fails on a gap; a gate of the first data release.
- **PG-DS-AC-13** (acceptance criterion; change item C03): A partly failed or failed intake (a batch with rejected rows, an unreadable document, a stopped feed, an unmatched record) is shown as such, with its count and reasons, and never as a successful intake.
- **PG-DS-AC-14** (acceptance criterion; change item C08): Whenever a rule or figure cannot fully do a check or a figure, it says so: what is missing, why it matters and what the builder is to do. No case is silent, and nothing is shown as complete when it is not. Each message is proven by a test when it is built; a list generated by scanning the code holds every message the scan finds and fails if the code gives one it does not cover.

Added after **APG-S04-L0175**, which reads: "Do not claim an integration, security control or acceptance criterion passed without reproducible evidence."

- **APG-S04-DS028** (bullet; change item C02): Bring every record kind under this section's intake, including the kinds checked today only inside the calculations and the records written straight to the store; take a regression baseline of today's rule and figure results first, explain and sign off every difference, and do it under its own change request.
- **APG-S04-DS029** (bullet; change item C06, C21): Keep the controlled data-supply registers (entity, field, rule input contracts, field coverage, supply routes, messages) current, and regenerate the field-coverage report for each way in as it is built; the report fails on a gap.

Added after **APG-S04-C0188**, which reads: "This lock approves the specification baseline only. It is not a declaration that connectors, source registers, quarantine controls, verification workflows, tena…"

- **APG-S04-DS030** (amendment record; change item C21): Version 1.1 amendment record: amended by change request APG-CR-DSR [number to be given at approval], approved by [approver] on [date], after its Section 18 §6 cascade impact assessment. The amendment adds text only; the added text is listed in that change request. Version 1.0 and its SHA-256 are kept as history.

Reworded: **S04 paragraph 2 (no RTM row)**, which reads today: "Version 1.0 | LOCKED SPECIFICATION BASELINE"

- **APG-S04-DS031** (version line; change item C21): Version 1.1 | LOCKED SPECIFICATION BASELINE (amended by change request APG-CR-DSR [number to be given at approval]; version 1.0 kept as history)

### Section 05 (Profitability Calculation Engine)

Added after **APG-S05-L0034**, which reads: "A commitment is not automatically an additional cost on top of a forecast; determine whether it is already represented."

- **APG-S05-DS001** (bullet; change item C14): [owner to confirm: question 3] Show the budget and profit of the authoritative forecast (§5.1) first. Beside them, show each item that is not final in its own column, mapped to the locked states: awaiting approval (Section 11 §8 draft or submitted values; submitted or unresolved claims in this section); on hold (records pending reconciliation or quarantined); disputed and rejected (both Section 11's one "Disputed/rejected amount" state, in two columns by its recorded status); each with its amount and the effect it would have if it went through. These effects are what-if values: labelled, isolated as Section 10 §7.1 requires, and never added into the authoritative figure. For held records they follow Section 04 §9's rules for provisional views: shown to authorised reviewers and traceable to the unverified records.
- **APG-S05-DS002** (bullet; change item C13): [owner to confirm: question 3] The extras and variations view (Section 11 §8.2) is a breakdown of the authoritative forecast final margin, not a separate margin: for each instruction or variation, its approved revenue and the actual cost, commitments and forecast cost to complete attributed to it; the original scope is the remainder. The parts add up exactly to the authoritative figure, and the view is labelled as a breakdown with its definition (Section 03 §5.4). Values that are not final are shown beside it as above, never in it.

Added after **APG-S05-L0089**, which reads: "Keep unresolved differences visible; do not force them into a clean-looking total."

- **APG-S05-DS003** (bullet; change item C13): Where a cost is attributed to an instruction or variation, it stays in actual cost or commitments exactly once; the attribution groups it and never adds it a second time. A cost, or forecast cost to complete, that is not attributed stays with the original scope.

Added after **APG-S05-C0176**, which reads: "This lock approves the specification baseline only. It does not claim that the live repository, database, calculation engine, forecast controls, benefit verific…"

- **APG-S05-DS004** (amendment record; change item C21): Version 1.1 amendment record: amended by change request APG-CR-DSR [number to be given at approval], approved by [approver] on [date], after its Section 18 §6 cascade impact assessment. The amendment adds text only; the added text is listed in that change request. Version 1.0 and its SHA-256 are kept as history.

Reworded: **S05 paragraph 2 (no RTM row)**, which reads today: "Version 1.0 | LOCKED SPECIFICATION BASELINE"

- **APG-S05-DS005** (version line; change item C21): Version 1.1 | LOCKED SPECIFICATION BASELINE (amended by change request APG-CR-DSR [number to be given at approval]; version 1.0 kept as history)

### Section 06 (Active Intelligence & Profit Leakage Detection)

Added after **APG-S06-C0040**, which reads: "Each rule requires a stable identifier, version, purpose, inputs, evaluation logic, thresholds, exceptions, severity mapping and test cases. Thresholds must be …"

- **APG-S06-DS001** (paragraph; change item C10): Rule thresholds and windows ship with defaults approved by the product owner; the builder's authorised approver accepts them at onboarding and may adjust them within the approved ranges. Each default is documented and visible to the builder; nothing is applied silently (Section 04 §10). A setting with no sensible default (the builder's own categories, or pairs a person declares) is supplied by the builder when the rule is switched on.

Added after **APG-S06-C0087**, which reads: "Keep severity, urgency and confidence separate. A high-severity finding with weak evidence warrants careful verification, not presentation as a confirmed loss. …"

- **APG-S06-DS002** (paragraph; change item C11): The financial part of a finding's severity is graded against levels the builder sets at setup: for each grade an amount, a percentage of the job, or both; with both set, the grade applies as soon as either is reached. The percentage is of [the current approved contract value, that is the original contract plus approved variations: owner to confirm, question 2]; where that value is missing, only the amount levels apply and the finding says so. No default or suggested levels are supplied. The levels are approved as other settings are (Section 04 §18.3). Until they are set and approved, findings still show, marked ungraded, with what to do. A finding's safety, quality, contractual and compliance classification (this section and Section 13 §13.4) is assessed on its own and is never lowered by a small or missing amount; a finding with no defensible amount is shown with that classification and marked as having no amount.

Added after **APG-S06-C0173**, which reads: "This lock approves the specification only. It does not claim that live detection rules, models, workflows, connectors or controls have been implemented, tested …"

- **APG-S06-DS003** (amendment record; change item C21): Version 1.1 amendment record: amended by change request APG-CR-DSR [number to be given at approval], approved by [approver] on [date], after its Section 18 §6 cascade impact assessment. The amendment adds text only; the added text is listed in that change request. Version 1.0 and its SHA-256 are kept as history.

Reworded: **S06 paragraph 2 (no RTM row)**, which reads today: "Version 1.0 | LOCKED SPECIFICATION BASELINE"

- **APG-S06-DS004** (version line; change item C21): Version 1.1 | LOCKED SPECIFICATION BASELINE (amended by change request APG-CR-DSR [number to be given at approval]; version 1.0 kept as history)

### Section 11 (Commercial & Revenue Intelligence)

Added after **S11 paragraph 52 (no RTM row)**, which reads: "Disputed/rejected amount: Value subject to dispute, rejection or unresolved review."

- **APG-S11-DS001** (paragraph; change item C13): For a rejected variation, the builder records what happens next: disputed, carried at the builder's own cost, resubmitted, or withdrawn. A resubmission or a withdrawal is a change of state made through the process §8.1 requires, with its own record. Profit Guardian records the outcome and does not judge the dispute (§11); the cost already incurred stays visible.

Added after **APG-S11-C0055**, which reads: "Potential, estimated, submitted, approved/certified, recognised, invoiced and collected values must remain distinct, with no silent transition between states. E…"

- **APG-S11-DS002** (heading 2; change item C13): 8.2 Extras and variations view — mandatory
- **APG-S11-DS003** (paragraph; change item C13): Show each extra or variation separately from the original contract scope: its value in each state, its status, the cost attributed to it so far, and its effect on the job's profit, as the breakdown Section 05 §3.2 defines. The original scope and the extras are never blended, and no state is added into another.

Added after **APG-S11-C0112**, which reads: "This lock approves the specification only. It does not claim commercial integrations, claim workflows, deadline intelligence or production controls have been im…"

- **APG-S11-DS004** (amendment record; change item C21): Version 1.1 amendment record: amended by change request APG-CR-DSR [number to be given at approval], approved by [approver] on [date], after its Section 18 §6 cascade impact assessment. The amendment adds text only; the added text is listed in that change request. Version 1.0 and its SHA-256 are kept as history.

Reworded: **S11 paragraph 2 (no RTM row)**, which reads today: "Version 1.0 | LOCKED SPECIFICATION BASELINE"

- **APG-S11-DS005** (version line; change item C21): Version 1.1 | LOCKED SPECIFICATION BASELINE (amended by change request APG-CR-DSR [number to be given at approval]; version 1.0 kept as history)


## 13. Pre-existing observations in the locked package (outside this change request)

These were found while doing this assessment. None is changed here; each is reported so the owner can decide whether it needs its own change request.

- **The RTM does not map every locked paragraph.** Comparing each section document with the RTM: in Sections 00 to 17, 401 non-empty paragraphs (cover and lock-record lines included) and 125 table rows have no RTM row. Among them:
  - S02's functional requirements PG-FR-001 to 025;
  - S03's entity table;
  - S04 §14's opening sentence ("Track freshness and completeness by source, project, domain and decision use");
  - S05 §3.2's formula line;
  - S11 §8's revenue state definitions.

  Section 18 has no RTM rows at all, though S18 §4 requires the RTM to trace "the handoff-specific requirements in Section 18". Section 18 checkpoint C blocks handoff if a material requirement is unmapped. The counts are in section 6.2.
- **Section 00 §11 names sections differently from the sections themselves.** This affects every section from 09 to 18, and also 06 and 10. For example, it calls Section 09 "Opportunity Discovery" and Section 11 "Alerts, Dashboard, Reporting"; the files are "Labour, Productivity & Resource Intelligence" and "Commercial & Revenue Intelligence". This assessment uses the titles of the section files.
- **Sections 14 and 18 number the build phases differently** (section 6.3).
- **The validator accepts only version 1.0 files** (section 6.7), so no approved change request could pass it as it stands.

## Appendix A. Files and how to reproduce

- `build_cia.py` with its data file `cia_data.py`, run as `python3 -I build_cia.py <extracted locked package> <output folder>`, writes `CIA_PROPOSED_TEXT.csv`, `CIA_RTM_IMPACT.csv`, `CIA_DEPENDENT_TEXT.txt` and `CIA_COUNTS.txt`.
  - It reads the Master RTM and the 19 section documents, paragraphs and table rows in document order.
  - It fails if an anchor, heading or proposed ID is wrong, or if an insertion point is not the true end of its block.
- `assemble.py` puts those tables into this document.
- Both are builder tools (BUILDER-EXECUTED: NOT INDEPENDENT).
- The locked package used: `Anchor_Profit_Guardian_Blueprint_v1.0.zip` (SHA-256 487becabdf47796800937d13a706a19b63b7b8230ecc5354b2f01a647ae5d960; manifest digest dad3fa91cb1da822779e041bb66279e08b6598861bb222b5e6e709e967f2d89c).

## Appendix B. Retention event (E77): proposed field definition

Taken from the stage 1 code (`fin/cash_states.py`: `record_event`, `check_event`, `fold`, `events_of`). Today the event is written straight to the store; under C18 it comes through the intake, from the first release's entry form.

| Field | Supplied by | Meaning and rule today |
| --- | --- | --- |
| project_ref | the person | the project whose retention pool moves |
| from_state, to_state | the person | one of the allowed moves: withheld to claimed; claimed to approved or disputed; approved to released or disputed; disputed to claimed or approved; released to received |
| amount_cents | the person | a positive whole number of cents, no more than the pool it leaves holds |
| evidence_ref | the person | required; for "received", a stored bank transaction of exactly this amount |
| note | the person | optional text |
| seq | APG | the next number in the project's sequence; events are append-only |
| actor, actor_kind, actor_roles | APG, from the signed-in person | a named person, never a service; "approved", "released" and "received" need the retention approver role, the others the clerk or approver role |
| at | APG | when it was recorded |

**Two locked obligations the definition must add (M06).**
- **A currency:** S03 §11.1 says "every monetary value must have an explicit currency". The event has none today; it assumes the project's.
- **The associated contract:** S03 §10.1 asks for the "associated contract and project". The event moves a project-level pool with no contract link.

The mapping of its states to S03 §13's illustrative retention lifecycle is settled with them.

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
- **Not decided here:**
  - how an accrual or overhead allocation is shared with an extra (to be specified before it is built, as S03 §6.3 requires; second-release data);
  - how a builder's own system marks such costs (discovery, with sample exports).
