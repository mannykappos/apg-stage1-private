import re
s = open('CIA_SOURCE_v4.md').read()
def rep(o, n):
    global s
    c = s.count(o)
    assert c == 1, (c, o[:90])
    s = s.replace(o, n)

rep('cascade impact assessment (draft 4)', 'cascade impact assessment (draft 5)')
rep("Draft 4 answers three independent checks (INDEPENDENT READ-ONLY (agent)):",
    "Draft 5 answers GPT's review of draft 4 (4 blocking, 3 should fix, 1 minor; each finding and its fix in `GPT_FIXES_CIA.md`) and carries the owner's answers of 2026-11-13 to questions 1 to 4 (owner record items 15 to 18). Draft 4 answered three independent checks (INDEPENDENT READ-ONLY (agent)):")
rep("The third check's fixes are wording only and have not been checked independently; to avoid a fourth round, they go to GPT with the rest.",
    "GPT reviewed those fixes with the rest of draft 4.")
# section 1
rep("- **What changes in the blueprint.** 81 pieces of text are added", "- **What changes in the blueprint.** 86 pieces of text are added")
rep("and 14 new acceptance criteria (PG-DS-AC-01 to 14), the tests each part must pass.",
    "and 17 new acceptance criteria (PG-DS-AC-01 to 17), the tests each part must pass.")
rep("""    - The only locked words that change are the version lines ("Version 1.0" becomes "Version 1.1") in the seven sections. Nothing else already locked is reworded or removed.""",
    """    - The locked words that change are the version lines ("Version 1.0" becomes "Version 1.1") in the seven sections, and one sentence of Section 06 §11: dismissing a finding no longer needs a reason (your decision on question 4). Nothing else already locked is reworded or removed.""")
rep("""No approval or check is weakened (if the owner chooses Option B of question 1, that is a stated exception for one-person builders).""",
    """Two locked checks are loosened, each by your decision and stated as such (section 4): a builder who is the only person using APG may approve his own settings, each marked "approved by the person who entered it" (question 1); and a builder may ignore a warning without giving a reason, with who and when still recorded (question 4). No other approval or check is weakened.""")
rep("That needs its own tests (section 4) and your confirmation (question 3).", "That needs its own tests (section 4); you confirmed it (question 3).")
rep("1,342 of them, in Sections 00 to 18", "<<N_ITEMS>> of them, in Sections 00 to 18")
rep("""- **Four questions for you** (section 11), each with an example:
    1. Can a builder who is the only person using APG approve his own settings?
    2. What is "a percentage of the job" a percentage of?
    3. What do the main budget and profit include, and how does the extras panel split them?
    4. Is it right that the builder's dollar and percentage levels grade only the money side of a finding, and never its safety side?
- **Next.** One GPT pass listing every problem at once; alongside it, the 100 entities are cross-checked against the requirements matrix (M15); then your formal approval. Only after approval are the version 1.1 files made, and each build still needs its own authorisation.""",
"""- **Your answers** (section 11). Questions 1 to 4 are answered. <<OPEN_QUESTIONS>>
- **Next.** <<NEXT>> Only after approval are the version 1.1 files made, and each build still needs its own authorisation.""")
# section 2
rep("| Date | 2026-11-13 (draft 3). |", "| Date | 2026-11-13 (draft 5). |")
rep("The owner's decisions record of 2026-11-12 and 13 (`OWNER_DECISIONS_2026-11-12.md`, \"owner record item N\" below).",
    "The owner's decisions record of 2026-11-12 and 13 (`OWNER_DECISIONS_2026-11-12.md`, \"owner record item N\" below), with his answers to this assessment's questions (items 15 to 18). GPT's review of draft 4.")
rep("The 8-layer design blueprint v0.1 is a design baseline, not locked; its 02 §2.11 and 11 §11.2 and §11.6 are dependents.",
    "The 8-layer design blueprint v0.1 is a design baseline, not locked; its 02 §2.11 and 11 §11.2 and §11.6 are dependents (the blueprint is in the pack, `06_change_request_sources/APG_8_LAYER_DESIGN_BLUEPRINT_v0.1/`).")
rep("It has 1,732 rows over 1,342 distinct locked items: 1,009 with an RTM ID, 248 paragraphs and 85 table rows without one",
    "It has <<N_ROWS>> rows over <<N_ITEMS>> distinct locked items: <<N_RTM>> with an RTM ID, <<N_PARA>> paragraphs and <<N_TROW>> table rows without one")
# section 3 table
rep("""| C04 | Setup questions for the source registry, the Source Authority Register, the cost-code map (each match confirmed by a person), users and roles, the financial policy settings a builder owns, and the rule settings. Each is versioned and approved. | S04 §18.3 (new); PG-DS-AC-05 | addition | draft 7, "Setup questions"; data supply decision 8 |""",
"""| C04 | Setup questions for the source registry, the Source Authority Register, the cost-code map (each match confirmed by a person), users and roles, the financial policy settings a builder owns, and the rule settings. Each is versioned and approved. Where the builder has exactly one authorised person, he approves his own settings, each permanently marked "approved by the person who entered it". | S04 §18.3 (new); S04 DS017; PG-DS-AC-05, 15 | addition, with one owner-approved relaxation: the separation of preparing and approving (PG-FR-025, F-67) for one-person builders' own settings (section 4) | draft 7, "Setup questions"; data supply decision 8; owner record item 15 |""")
rep("""| C10 | Detection-rule thresholds ship with owner-approved defaults, visible to the builder, which his approver accepts. |""",
    """| C10 | Detection-rule thresholds ship with owner-approved defaults, visible to the builder, which his approver accepts (question 5: whether a one-person builder accepts them himself). |""")
rep("""| C11 | Severity levels for the money side of a finding, set by the builder at setup: an amount, a percentage of the job, or both, whichever is reached first. No defaults. Safety and quality classification stays separate. | S06 §8 (new paragraph) | addition (new design and new code); questions 1, 2 and 4 | owner record items 7 and 9 |""",
    """| C11 | Severity levels for the money side of a finding, set by the builder at setup: an amount, a percentage, or both, whichever is reached first. The builder chooses whether a percentage is measured against the whole job, the part of the job the finding sits in, or both; the parts are those of his own budget breakdown (by stage, trade or area), which add up to the whole-job budget. No defaults. Safety and quality classification stays separate. | S06 §8 (new paragraph); S05 §3.3 (new paragraph) | addition (new design and new code); question 6 | owner record items 7, 9 and 16 |""")
rep("| addition, including one new financial view (section 4); question 3 | owner record items 4 and 5 |",
    "| addition, including one new financial view (section 4); confirmed by the owner (question 3) | owner record items 4, 5 and 17 |")
rep("| addition (new presentation across budget and profit); question 3 | owner record item 11 |",
    "| addition (new presentation across budget and profit); confirmed by the owner (question 3) | owner record items 11 and 17 |")
rep("""| C18 | Retention events through the intake, with a field definition. | the field register and Appendix B | addition to a controlled register | GPT's re-check of revision 4 |""",
    """| C18 | Retention events through the intake, with a field definition that adds the currency and the associated contract (S03 §11.1, §10.1) and maps the states to S03 §13. | the field register and Appendix B; PG-DS-AC-17 | addition to a controlled register | GPT's re-check of revision 4; GPT's review of draft 4 |""")
rep("""| addition; version lines reworded | revision 4, registers; S18 §6 |""",
    """| addition; version lines reworded | revision 4, registers; S18 §6 |
| C22 | Profit Guardian advises and never blocks: the builder may ignore (dismiss) any finding in one tap, with a reason optional; who and when are recorded; the finding is kept and raised again only when something material changes. | S06 §11 (one sentence reworded, one paragraph added); PG-DS-AC-16 | owner-approved relaxation of S06 §11 ("must record rationale"), section 4 | owner record item 18 |""")
# section 4
rep("Question 3 confirms it with the owner. It meets the canonical separation rules:", "The owner confirmed it (question 3, owner record item 17). It meets the canonical separation rules:")
rep("so one must be designed and approved before C11 is built (M17). Questions 1, 2 and 4 cover the open points.",
    "so one must be designed and approved before C11 is built (M17). The owner settled what a percentage is measured against (question 2): the builder chooses the whole job, the part of the job the finding sits in, or both, the parts being those of his own budget breakdown (S05 DS006), which add up to the whole-job budget; a finding not tied to a part is graded on the amount and the whole job only, and says so. Question 6 confirms the whole-job base.")
rep("so nothing is substituted silently (S04 §10, PG-DI-AC-11).",
    "so nothing is substituted silently (S04 §10, PG-DI-AC-11). Question 5 asks whether a one-person builder accepts them himself, under the one-person exception below.")
rep("""- **"Switched on" is new wording; it is not a new limit.**""",
    """- **Two locked conditions are relaxed, each by the owner's decision of 2026-11-13, and stated as such.**
    - **The one-person exception (C04; question 1, owner record item 15).** S02 §3.1 asks for preparing and approving to be separated "where practical and supported by policy", and PG-FR-025 for "appropriate segregation of duties". The code enforces it today: F-67 (`apg/policy_approval.py`) refuses an approval by the person who proposed the setting. The owner's decision supplies the policy S02 §3.1 allows for. Where a builder has exactly one authorised person, that person may approve the builder's own settings (S04 DS026), and each such setting, and every figure, finding and report that uses it, is permanently marked "approved by the person who entered it". With two or more authorised people, the two-person rule applies. The exception is limited to the builder's own settings of S04 DS026. It does not cover consequential actions, which still need human approval (S15 §15.11), the second-person check of a keyed value (S04 DS022), or any other record kind (S04 DS017). S15 §15.4's "separate approval authority" is met by a separate approve permission, approval record and audit event, kept distinct even when one person holds both roles. F-67's code changes under the build's own change request, with tests (PG-DS-AC-15).
    - **Dismissing a finding without a reason (C22; question 4, owner record item 18).** S06 §11 says "Dismissal/deferment of material findings must record rationale". The owner decided that Profit Guardian advises and does not block: the builder may ignore any warning in one tap, and a reason is optional. The sentence is reworded (S06 DS005): who dismissed or deferred the finding, and when, is still recorded, and the rationale where one is given. The evidence is kept, the finding can be reassessed, and it is raised again on a material change (S06 DS006). PG-AI-AC-13 (dismissal is auditable) and S06 §11's "retain evidence and allow future reassessment" keep their meaning. S06 §8's disposition field "rationale" stays, left empty when none is given. A dismissal is a person's decision, not financial prioritisation overriding safety (S13 §13.4), and the finding's own safety or quality grade is never lowered.
- **"Switched on" is new wording; it is not a new limit.**""")
# section 5
rep("| Financial correctness | The percentage uses the wrong base, or no base exists. | A defined base (question 2); without it only the amount levels apply and the finding says so. |",
    "| Financial correctness | The percentage uses the wrong base, or no base exists; a part's budget does not add up with the others to the job's. | A defined base: the builder's choice of whole job, part or both (question 2), the whole-job base confirmed by question 6; without a base only the levels that can be measured apply and the finding says so; the parts must add up to the whole-job budget, and Profit Guardian says when they do not (S05 DS006). |")
rep("| Approvals | Settings take effect without the right approval; or a one-person builder cannot use APG at all. | PG-DS-AC-05: every setting versioned and approved before it takes effect; question 1 settles the one-person case; the detection defaults are owner-approved and accepted by the builder's approver. |",
    "| Approvals | Settings take effect without the right approval; a one-person builder cannot use APG at all; or the one-person exception spreads to other approvals. | PG-DS-AC-05 and 15: every setting versioned and approved before it takes effect; a one-person builder approves his own settings, each permanently marked, and the marker carried to every figure that uses them; the exception covers settings only, never consequential actions (S15 §15.11) or keyed values (S04 DS022); the approval keeps its own permission, record and audit event. |")
rep("| Auditability | A value cannot be traced to who supplied it, how and when. | PG-DS-AC-04; S03 DS010 to DS013 (channel, supplied_by, verified_by, retrospective); originals kept (S04 §10, DS019). |",
    "| Auditability | A value cannot be traced to who supplied it, how and when. | PG-DS-AC-04; S03 DS010 to DS013 (channel, supplied_by, verified_by, retrospective); originals kept (S04 §10, DS019). |\n| Auditability and safety | A builder ignores a serious warning with no reason, and it is lost. | The warning keeps its own grade; who and when are recorded; the finding and its evidence are kept and can be reopened; it is raised again on a material change (S06 DS005, DS006; PG-DS-AC-16; PG-AI-AC-13). Whether to act is the builder's decision (owner record item 18). |")
# section 6
rep("- a **reworded version line**: the only locked text that changes;",
    "- a **reworded line**: a version line, or S06 §11's one sentence on dismissal (an owner-approved relaxation); the only locked text that changes;")
rep("- **New rows:** 81, one for each addition: paragraphs, bullets, headings, each table row separately, and the 14 acceptance criteria.",
    "- **New rows:** 86, one for each addition: paragraphs, bullets, headings, each table row separately, and the 17 acceptance criteria.")
rep("    - The 14 acceptance criteria keep their own IDs (PG-DS-AC-01 to 14), as do PG-FR-026 and 027.",
    "    - The 17 acceptance criteria keep their own IDs (PG-DS-AC-01 to 17), as do PG-FR-026 and 027.\n    - The reworded S06 §11 sentence keeps its RTM ID (APG-S06-C0112); its summary is updated to the new wording.")
rep("| Owner's CR-10 | Verified profit ledger. It overlaps C14 (verified figures first) and C13 (the breakdown). Its text is not in this pack, so the overlap must be checked against it before this change request is approved (section 8). | CR-10 |",
    "| Owner's CR-10 | Verified profit ledger. It overlaps C14 (verified figures first) and C13 (the breakdown). <<CR10>> | CR-10 |\n| The approval code (F-67) | `apg/policy_approval.py` refuses an approval by the proposer. The one-person exception (C04) changes it, with the tests of PG-DS-AC-15. | the build that implements C04, under its own change request |")
rep("| C04 | test_source_authority; test_f67_policy_approval and test_f671 to f674; test_status_model | none |",
    "| C04 | test_source_authority; test_f67_policy_approval and test_f671 to f674 (the one-person exception changes F-67's rule); test_status_model | none |")
rep("| C18 | test_fin_cash, test_fin_intake | none |",
    "| C18 | test_fin_cash, test_fin_intake | none today; new synthetic fixtures: one project with two contracts in AUD, and an event in another currency (rejected) |\n| C22 | test_det_findings, test_det_noise (dismissal and re-notification) | none |")
rep("- PG-DS-AC-01 to 14:", "- PG-DS-AC-01 to 17:")
rep("    - every message carries what to do, and the message list fails on an uncovered message (14).",
    "    - every message carries what to do, and the message list fails on an uncovered message (14);\n    - the one-person exception and its limits: self-approval with the marker on every dependent figure, the two-person rule with two or more people, the approval's own audit record, and no exception for consequential actions or keyed values (15);\n    - a finding dismissed in one tap with no reason, who and when recorded, kept, reopenable, and raised again on a material change (16);\n    - a retention event without a currency, with another currency, or without its contract is rejected; pools are kept per contract and project (17).")
rep("- **Severity:** graded by amount, by percentage, and by both, whichever is reached first; ungraded when not set; amount levels only when the base is missing; a safety classification never lowered by a small or missing amount.",
    "- **Severity:** graded by amount, by percentage, and by both, whichever is reached first; against the whole job, the finding's part, or both, as set; ungraded when not set; only the measurable levels when a base is missing; a finding not tied to a part graded on the whole job only; budget parts that do not add up to the whole are reported; a safety classification never lowered by a small or missing amount.")
rep("PG-DS-AC-01 to 14 are new; they sit in S04 §19 after PG-DI-AC-18.", "PG-DS-AC-01 to 17 are new; they sit in S04 §19 after PG-DI-AC-18.")
rep("data release (a scope of data, distinct from a build phase and from Section 17's release gates); controlled data-supply registers.",
    "data release (a scope of data, distinct from a build phase and from Section 17's release gates); controlled data-supply registers; \"approved by the person who entered it\" (the one-person marker); ignore (dismiss) a finding; budget breakdown and budget part (a stage, trade or area of the approved budget).")
# section 7
rep("| each differs only by the additions and the reworded version lines in `CIA_PROPOSED_TEXT.csv`, word for word; nothing else is reworded or removed | T18-08 |",
    "| each differs only by the additions, the reworded version lines and S06's one reworded sentence in `CIA_PROPOSED_TEXT.csv`, word for word; nothing else is reworded or removed | T18-08 |")
rep("all 2,712 existing IDs kept (by text and old index); 81 new rows plus the backfilled rows;",
    "all 2,712 existing IDs kept (by text and old index; APG-S06-C0112 with its reworded summary); 86 new rows plus the backfilled rows;")
# section 8
rep("then a focused check of draft 3 (no blocking point; 6 should fix, 7 minor, all wording). A fix is claimed for each (`CHECK1_FIXES_CIA.md`, `CHECK2_FIXES_CIA.md`, `CHECK3_FIXES_CIA.md`).",
    "then a focused check of draft 3 (no blocking point; 6 should fix, 7 minor, all wording). A fix is claimed for each (`CHECK1_FIXES_CIA.md`, `CHECK2_FIXES_CIA.md`, `CHECK3_FIXES_CIA.md`).\n    - GPT's review of draft 4 (4 blocking, 3 should fix, 1 minor). It re-ran the build and got byte-identical tables and text. Its findings are fixed in draft 5 (`GPT_FIXES_CIA.md`). It advised one targeted confirmation of the fixes, not another full round.")
rep("""    1. Done: a focused independent check of draft 3 (no blocking point; its wording points fixed in draft 4, not re-checked).
    2. The 100 entities cross-checked against every row of the Master RTM (M15), before the entity register can become an annex.
    3. One GPT pass, listing every problem at once.
    4. Gemini only if the owner wants a design view.
    5. The overlap with the owner's CR-10 (verified profit ledger) checked against its text.""",
"""    1. Done: a focused independent check of draft 3.
    2. <<M15_STATUS>>
    3. Done: GPT's review of draft 4. Still to come: GPT's targeted confirmation of draft 5's fixes (the Option B wording, the retention definition, the M15 evidence and the CR-10 comparison), as GPT advised.
    4. Gemini only if the owner wants a design view.
    5. <<CR10_STATUS>>
- **Approval conditions.** The owner approves a final text: no square brackets are left in the proposed wording except the change request's number and the approval details. Questions 5 and 6, which came out of GPT's review and the owner's answers, are answered (owner record items 20 and 21), so no bracket for them remains. The CR-10 overlap is a recorded dependency of the approval (owner record item 19), not a check made before it.""")
# section 10
rep("| M06 Retention and security state handling | GPT | Retention events move into the intake with a field definition (C18, Appendix B). The definition must meet two locked obligations today's code does not: an explicit currency (S03 §11.1) and an associated contract as well as project (S03 §10.1). The code's states (withheld, claimed, approved, disputed, released, received) also differ from S03 §13's illustrative lifecycle (which has \"Under Review\" and no \"received\"); the mapping is settled in the field definition. Security instruments stay as S03 §10.2 says. Not settled yet. |",
    "| M06 Retention and security state handling | GPT | Settled in Appendix B: the retention event gains its currency (S03 §11.1) and its associated contract (S03 §10.1), and its states are mapped to S03 §13's illustrative lifecycle; PG-DS-AC-17 tests them. Security instruments stay as S03 §10.2 says. |")
rep("| M10 How the builder's settings are approved | owner, Claude | Question 1 (all settings, not only severity). |",
    "| M10 How the builder's settings are approved | owner, Claude | Decided: Option B (owner record item 15). S04 DS017 and DS026, PG-DS-AC-05 and 15; section 4. |")
rep("| M12 The retention-event (E77) field definition | GPT's re-check | Appendix B, with M06's two open obligations. |",
    "| M12 The retention-event (E77) field definition | GPT's re-check | Done: Appendix B. |")
rep("| M15 The 100 entities cross-checked against every row of the Master RTM | revision 4's next steps | Not done. Needed before the controlled entity register becomes an annex (S03 DS009), so it is a step before approval (section 8, item 2). |",
    "| M15 The 100 entities cross-checked against every row of the Master RTM | revision 4's next steps | <<M15_ROW>> |")
rep("| M16 The code-read scan is not a proof |", """| M19 The locked text the RTM does not map (541 paragraphs and 125 table rows in Sections 00 to 18) | GPT's review of draft 4 | A separate, mandatory work item for package acceptance, outside this change request. Owner: Emmanuel. Closure evidence: a consolidated RTM validation reporting zero missing, duplicate, orphaned or unmapped items, with the manual semantic review documented (S18 §9, checkpoint C). The version 1.1 package cannot pass S18 §9 until it is closed. This change request backfills only the 269 items it touches (section 6.2), and does not claim the S18 §9 gate. |
| M20 The 8-layer design blueprint v0.1 | GPT's review of draft 4 | Now in the pack (`06_change_request_sources/`), so the dependents named in section 2 and M01 can be checked. |
| M16 The code-read scan is not a proof |""")
# section 11
i = s.index('## 11. Questions for the owner'); j = s.index('## 12. Proposed wording')
s = s[:i] + open('Q_SECTION_v5.md').read() + '\n' + s[j:]
rep("Square brackets mark the points waiting for questions 1 to 4 and the approval details.", "<<BRACKETS>>")
# section 13
rep("Section 18 checkpoint C blocks handoff if a material requirement is unmapped. The counts are in section 6.2.",
    "Section 18 checkpoint C blocks handoff if a material requirement is unmapped. The counts are in section 6.2. This is now matter M19: a mandatory work item for package acceptance, outside this change request.")
# appendix B
i = s.index('**Two locked obligations the definition must add (M06).**'); j = s.index('## Appendix C.')
s = s[:i] + open('APPX_B_v5.md').read() + '\n' + s[j:]
rep("| project_ref | the person | the project whose retention pool moves |",
    "| project_ref | the person | the project whose retention pool moves |\n| contract_ref | the person | **new:** the associated contract (S03 §10.1): the head contract (E08) or the subcontract the retention is held under; required; the pool is kept per contract and project |\n| currency | the person, checked by APG | **new:** the ISO 4217 code of amount_cents (S03 §11.1); required; it must equal the currency of the pool it moves; a retention event never converts currency |")
rep("| Field | Supplied by | Meaning and rule today |", "| Field | Supplied by | Meaning and rule (today's, unless marked new) |")
# appendix C
rep("- **Not decided here:**\n    - how an accrual",
    "- **Budget parts (question 2, owner record item 16):** each budget line (E38) carries the part of the job it belongs to: a stage, a trade or cost code, or an area, as the builder breaks his budget down (the work packages of E98, S03 §2). Each cost carries its part too, through its cost code (the cost-code map) or its own tag. A cost with no part counts for the whole job only. The parts add up to the whole-job approved budget (S05 DS006).\n- **Not decided here:**\n    - how an accrual")
rep("The Data Readiness Change Request, revision 4, with its registers.", "The Data Readiness Change Request, revision 4, with its registers, and its entity register revision 4.1 (2026-11-13, the M15 row-level check: 114 entities, `REV41_ADDENDUM.md`).")

# ---- draft 5, second round: the independent check of draft 5 and the owner's answers A to F (items 23 to 28) ----
def rep2(o, n, c=1):
    global s
    assert s.count(o) == c, (s.count(o), o[:90])
    s = s.replace(o, n)
rep2("to questions 1 to 4 (owner record items 15 to 18).", "to questions 1 to 6 and eight further decisions (owner record items 15 to 28), and the fixes of an independent check of draft 5 (`CHECK_DRAFT5.md`, 2 blocking, 10 should fix, 10 minor; fixes in `CHECK5_FIXES_CIA.md`).")
rep2("86 pieces of text are added to 7 of the 19 sections (01, 02, 03, 04, 05, 06 and 11)", "87 pieces of text are added to 8 of the 19 sections (00, 01, 02, 03, 04, 05, 06 and 11)")
rep2('in the seven sections, and one sentence of Section 06 §11: dismissing a finding no longer needs a reason (your decision on question 4).',
     'in the eight sections, and two sentences on dismissing a finding: Section 06 §11 and Section 00 §00.3 no longer require a reason (your decisions on question 4 and question A).')
rep2('Two locked checks are loosened, each by your decision and stated as such (section 4): a builder who is the only person using APG may approve his own settings, each marked "approved by the person who entered it" (question 1); and a builder may ignore a warning without giving a reason, with who and when still recorded (question 4). No other approval or check is weakened.',
     'Two locked checks are loosened, each by your decision and stated as such (section 4): a builder with only one person allowed to approve may approve his own settings, budget and retention steps and confirm the values he keyed, each marked as done by the person who entered it (questions 1, 5, C, D and E), which also loosens, for those cases only, the security section\'s separate approval of financial rules, baselines, access and retention release; and a builder may ignore or defer a warning without giving a reason, with who and when still recorded (questions 4, A and B). No other approval or check is weakened.')
rep2("with his answers to this assessment's questions (items 15 to 18).", "with his answers to this assessment's questions and decisions (items 15 to 28).")
rep2("which his approver accepts (question 5: whether a one-person builder accepts them himself).", "which his approver accepts; a one-person builder accepts them himself, marked (question 5).")
rep2("Question 5 asks whether a one-person builder accepts them himself, under the one-person exception below.", "A one-person builder accepts them himself, marked, under the one-person exception below (question 5, owner record item 20).")
rep2("the version lines and amendment records of the seven sections.", "the version lines and amendment records of the eight sections.")
rep2("| Affected locked sections (amended) | Sections 01, 02, 03, 04, 05, 06 and 11, each version 1.0 LOCKED, to become 1.1", "| Affected locked sections (amended) | Sections 00, 01, 02, 03, 04, 05, 06 and 11, each version 1.0 LOCKED, to become 1.1")
rep2("| Affected locked sections (dependents, no text change) | Sections 00, 07,", "| Affected locked sections (dependents, no text change) | Sections 07,")
rep2("| 01 | v1.0 LOCKED | 5964235f08c0ee6a |", "| 00 | v1.0 LOCKED | 17c35c013dddb7cf |\n| 01 | v1.0 LOCKED | 5964235f08c0ee6a |")
rep2("for each of the 269 such items it touches (184 paragraphs and 85 table rows)", "for each of the <<N_BACK>> such items it touches (<<N_PARA>> paragraphs and <<N_TROW>> table rows)")
rep2("This change request backfills only the 269 items it touches", "This change request backfills only the <<N_BACK>> items it touches")
rep2("86 new rows plus the backfilled rows", "87 new rows plus the backfilled rows")
rep2("- **New rows:** 86, one for each addition", "- **New rows:** 87, one for each addition")
rep2("APG-S06-C0112 with its reworded summary)", "APG-S06-C0112 and APG-S00-L0017 with their reworded summaries)")
rep2("    - The reworded S06 §11 sentence keeps its RTM ID (APG-S06-C0112); its summary is updated to the new wording.",
     "    - The reworded sentences keep their RTM IDs (APG-S06-C0112, APG-S00-L0017); their summaries are updated to the new wording.")
rep2("each differs only by the additions, the reworded version lines and S06's one reworded sentence", "each differs only by the additions, the reworded version lines and the two reworded sentences (S06 §11, S00 §00.3)")
rep2("- **Sections 01, 02, 03, 04, 05, 06 and 11 are issued as version 1.1.**", "- **Sections 00, 01, 02, 03, 04, 05, 06 and 11 are issued as version 1.1.**", 0) if False else None
s = s.replace("Sections 01, 02, 03, 04, 05, 06 and 11 are issued as version 1.1", "Sections 00, 01, 02, 03, 04, 05, 06 and 11 are issued as version 1.1")
s = s.replace("the seven version 1.1 files", "the eight version 1.1 files").replace("The seven sections become version 1.1", "The eight sections become version 1.1")
s = s.replace("[Sections 01, 02, 03, 04, 05, 06, 11 v1.1;", "[Sections 00, 01, 02, 03, 04, 05, 06, 11 v1.1;")
rep2("Still to come: GPT's targeted confirmation of draft 5's fixes (the Option B wording, the retention definition, the M15 evidence and the CR-10 comparison), as GPT advised.",
     "Done: an independent focused check of draft 5 (2 blocking, 10 should fix, 10 minor), its findings fixed and the owner's answers A to F carried (`CHECK5_FIXES_CIA.md`). Still to come: GPT's targeted confirmation of draft 5's fixes (the one-person exception, the retention definition, the M15 register and the relaxations), as GPT advised.")
# the one-person relaxation in section 4
rep2("Where a builder has exactly one authorised person, that person may approve the builder's own settings (S04 DS026), and each such setting, and every figure, finding and report that uses it, is permanently marked \"approved by the person who entered it\". With two or more authorised people, the two-person rule applies. The exception is limited to the builder's own settings of S04 DS026. It does not cover consequential actions, which still need human approval (S15 §15.11), the second-person check of a keyed value (S04 DS022), or any other record kind (S04 DS017).",
     "Where a builder has exactly one authorised person (a person with the permission to approve; a capture-only or view-only user does not count, owner record item 26), that person may approve the builder's own settings, including accepting a product default (item 20) and users and roles; the approved budget and its breakdown (item 27); and the approval steps of a retention event (item 25); and may confirm the values he keyed from documents (item 25; S04 DS022 is this change request's own stricter control). Each such record, and every figure, finding and report that uses it, is permanently marked as approved, or confirmed, by the person who entered it. With two or more authorised people, the two-person rule applies. **This also relaxes Section 15, for these cases only:** S15 §15.4's \"separate approval authority\" and §15.11's approval of \"changes to authoritative financial rules or approved baselines\", \"privileged access changes\" and \"retention release\". The other consequential actions of §15.11 keep their approval: purchase orders and supplier commitments; contract, scope, specification or material changes; claims, notices and commercial communications; deletion or correction of authoritative evidence; and no action outside Profit Guardian is covered (S04 DS017, DS026).")
rep2("S15 §15.4's \"separate approval authority\" is met by a separate approve permission, approval record and audit event, kept distinct even when one person holds both roles.",
     "Each approval keeps its own permission, approval record (with its rationale and the risks considered, S15 §15.11) and audit event, distinct even when one person holds both roles.")
rep2("The sentence is reworded (S06 DS005): who dismissed or deferred the finding, and when, is still recorded, and the rationale where one is given.",
     "The sentence is reworded (S06 DS005), and so is the matching line of Section 00 §00.3 (S00 DS004, owner record item 23): who dismissed or deferred the finding, and when, is still recorded, and the reason where one is given. Deferment is treated like dismissal (item 24).")
rep2("A dismissal is a person's decision, not financial prioritisation overriding safety (S13 §13.4), and the finding's own safety or quality grade is never lowered.",
     "A dismissal is a person's decision, not financial prioritisation overriding safety (S13 §13.4), and the finding's own safety or quality grade is never lowered. Ignoring a finding never closes a defect: rectification and closure keep their own evidence (S13 §13.8).")

rep2("the exception covers settings only, never consequential actions (S15 §15.11) or keyed values (S04 DS022); the approval keeps its own permission, record and audit event. |",
     "the exception covers only his settings, his budget and its breakdown, his retention steps and his keyed values, each marked; never the other consequential actions of S15 §15.11 (purchase orders, contract or scope changes, claims and notices, deletion of evidence) or any action outside Profit Guardian; every approval keeps its own permission, rationale and audit event. |")
rep2('Where the builder has exactly one authorised person, he approves his own settings, each permanently marked "approved by the person who entered it". | S04 §18.3 (new); S04 DS017; PG-DS-AC-05, 15 | addition, with one owner-approved relaxation: the separation of preparing and approving (PG-FR-025, F-67) for one-person builders\' own settings (section 4)',
     'Where the builder has exactly one person allowed to approve, he approves his own settings, budget and retention steps and confirms his keyed values, each permanently marked. | S04 §18.3 (new); S04 DS017, DS022; PG-DS-AC-05, 15 | addition, with one owner-approved relaxation for one-person builders: the separation of preparing and approving (PG-FR-025, F-67) and, for those cases, S15 §15.4 and §15.11 (section 4)')
# draft-5 check minors (m-1, m-3, m-4, m-5)
rep2('S06 §8\'s disposition field "rationale" stays', 'S06 §6\'s finding data contract field "rationale" (APG-S06-L0079) stays')
rep2("| addition (new design and new code); question 6 | owner record items 7, 9 and 16 |", "| addition (new design and new code) | owner record items 7, 9, 16, 21 and 28 |")
rep2('draft 7, "Setup questions"; data supply decision 8; owner record item 15 |', 'draft 7, "Setup questions"; data supply decision 8; owner record items 15, 20 and 25 to 27 |')
rep2("Question 6 confirms the whole-job base.", "Question 6 confirms the whole-job base: the job's approved budget (owner record item 21).")
rep2("the whole-job base confirmed by question 6;", "the whole-job base being the job's approved budget (question 6);")
rep2("or without its contract is rejected; pools are kept per contract and project (17).", "or without its contract is rejected; pools are kept per contract and project; each state shows its S03 §13 label, \"approved\" is not \"released\", and \"received\" needs its matching bank transaction (17).")
rep2("budget parts that do not add up to the whole are reported;", "budget parts that do not add up to the whole are reported, each breakdown on its own when the budget is broken down both ways; a finding in two parts (a stage and a trade) graded against each, the more serious grade applying and the triggering part named;")
rep2("kept, reopenable, and raised again on a material change (16);", "kept, reopenable, and raised again on a material change; a deferment recorded the same way; the defect or other record it is about left unchanged (16);")
# re-check of draft 5 (RECHECK_DRAFT5.md): N-2 to N-5, n-3, n-5, n-6, items 29 and 30
rep2("- **Your answers** (section 11). Questions 1 to 4 are answered. <<OPEN_QUESTIONS>>", "- **Your answers** (section 11). <<OPEN_QUESTIONS>>")
rep2("Still to come: GPT's targeted confirmation of draft 5's fixes (the one-person exception, the retention definition, the M15 register and the relaxations), as GPT advised.",
     "Done: a scoped re-check of those fixes (1 blocking, 6 should fix, 8 minor; `RECHECK_DRAFT5.md`), its findings fixed and the owner's answers G and H carried (`RECHECK5_FIXES_CIA.md`). Still to come: GPT's targeted confirmation of the fixes (the one-person exception and the relaxations, the two reworded sentences, the retention definition, the M15 register revision 4.1), as GPT advised.")
rep2("With two or more authorised people, the two-person rule applies.",
     "With two or more authorised people, the two-person rule applies. It applies per kind of record: once a second person may approve or confirm a kind of record (a bookkeeper who checks keyed values, say), the two-person rule applies to that kind, and the exception continues for the others (owner record item 29). Every approval, also under the exception, records a short reason, as S15 checkpoint D requires (item 30); only warnings may be ignored or deferred without one.")
rep2("Deferment is treated like dismissal (item 24).", "Deferment is recorded like dismissal, and a deferred finding returns on the date chosen, or sooner on a material change (item 24).")
rep2("- **One control is stricter than the locked text:** a value a person keys from an uploaded document needs a second person's confirmation (S04 DS022).",
     "- **One control is stricter than the locked text:** a value a person keys from an uploaded document needs a second person's confirmation (S04 DS022), or, under the one-person exception, that person's own, marked \"confirmed by the person who entered it\" (item 25).")
rep2("until extraction exists, values are keyed and confirmed by a second person.", "until extraction exists, values are keyed and confirmed by a second person (or, under the one-person exception, by that person, marked).")
rep2("a version line, or S06 §11's one sentence on dismissal (an owner-approved relaxation); the only locked text that changes;",
     "a version line, or one of the two sentences on dismissal (S06 §11, S00 §00.3; owner-approved relaxations); the only locked text that changes;")
rep2("the two-person rule with two or more people, the approval's own audit record, and no exception for consequential actions or keyed values (15);",
     "the two-person rule per kind of record once a second person may approve that kind, a short reason and the approval's own audit record on every approval, keyed values and retention steps confirmed or approved by the one person, marked, and no exception for the consequential actions §18.3 lists as outside it (15);")
rep2("a deferment recorded the same way; the defect or other record it is about left unchanged (16);",
     "a deferment recorded the same way and raised again on its chosen date; the defect or other record it is about left unchanged (16);")
rep2("- **Document values:** a keyed value from an uploaded document counts only after a second person confirms it.",
     "- **Document values:** a keyed value from an uploaded document counts only after a second person confirms it, or, under the one-person exception, after that person confirms it, marked.")
rep2("and who approves a baseline (8).", "and who approves a baseline (8), except that a one-person builder approves his own budget and its breakdown, marked (owner record item 27; S04 DS026, S05 DS006).")
rep2("Baselines: locked in S05 §5.1 and §10 and 8-layer decision 8; nothing added here;",
     "Baselines: locked in S05 §5.1 and §10 and 8-layer decision 8; added here only for the one-person builder, who approves his own budget and its breakdown, marked (owner record item 27; S04 DS026, S05 DS006), and the split of the breakdown into a setting (its structure) and baseline amounts (S05 DS006);")
rep2("| Decided: Option B (owner record item 15). S04 DS017 and DS026, PG-DS-AC-05 and 15; section 4. |",
     "| Decided: Option B (owner record item 15), extended by items 20 and 25 to 27 and made per kind of record by item 29; every approval keeps a reason (item 30). For its cases only it relaxes S15 §15.4 and §15.11 (section 4). S04 DS017, DS022 and DS026, S05 DS006, S06 DS001, PG-DS-AC-05 and 15. |")
rep2('"approved by the person who entered it" (the one-person marker);',
     '"approved by the person who entered it" and "confirmed by the person who entered it" (the one-person markers); authorised person (per kind of record); one-person exception; defer (a finding, until a chosen date);')
rep2("| S04 §18.3 (new); S04 DS017, DS022; PG-DS-AC-05, 15 |", "| S04 §18.3 (new); S04 DS017, DS022; S05 DS006; S06 DS001; PG-DS-AC-05, 15 |")
rep2("is confirmed by a second person with the verifier role. | S04 §18.2 | addition, stricter than S04 §18 | draft 7, release A item 4 |",
     "is confirmed by a second person with the verifier role, or, under the one-person exception, by that person, marked. | S04 §18.2; S04 DS026 | addition, stricter than S04 §18 (except under the one-person exception) | draft 7, release A item 4; owner record items 25 and 29 |")
rep2("| C22 | Profit Guardian advises and never blocks: the builder may ignore (dismiss) any finding in one tap, with a reason optional; who and when are recorded; the finding is kept and raised again only when something material changes. | S06 §11 (one sentence reworded, one paragraph added); PG-DS-AC-16 | owner-approved relaxation of S06 §11 (\"must record rationale\"), section 4 | owner record item 18 |",
     "| C22 | Profit Guardian advises and never blocks: the builder may ignore (dismiss) or defer any finding in one tap, with a reason optional; who and when are recorded; the finding is kept and raised again when something material changes, and a deferred one on its chosen date. | S06 §11 (one sentence reworded, one paragraph added); S00 §00.3 (one sentence reworded); PG-DS-AC-16 | owner-approved relaxations of S06 §11 (\"must record rationale\") and S00 §00.3 (\"with reasons and evidence\", for dismissals), section 4 | owner record items 18, 23 and 24 |")
# final narrow check (FINAL_CHECK_DRAFT5.md): F-2 to F-4
rep2('draft 7, "Setup questions"; data supply decision 8; owner record items 15, 20 and 25 to 27 |', 'draft 7, "Setup questions"; data supply decision 8; owner record items 15, 20, 25 to 27, 29 and 30 |')
rep2("deletion or correction of authoritative evidence; and no action outside Profit Guardian is covered", "deletion or correction of authoritative evidence; security cancellation; and no action outside Profit Guardian is covered")
rep2("the builder may ignore (dismiss) or defer any finding in one tap, with a reason optional;", "the builder may ignore (dismiss) any finding in one tap, or defer it to a chosen date, with a reason optional;")
rep2("(purchase orders, contract or scope changes, claims and notices, deletion of evidence) or any action outside Profit Guardian", "(purchase orders, contract or scope changes, claims and notices, deletion of evidence, security cancellation) or any action outside Profit Guardian")
rep2("Where the builder has exactly one person allowed to approve, he approves his own settings, budget and retention steps and confirms his keyed values, each permanently marked.", "Where exactly one person may approve a kind of record, he approves his own records of that kind (settings, budget, retention steps) and confirms his keyed values, each permanently marked; the two-person rule applies to each kind once a second person may approve it.")
rep2("its findings fixed and the owner's answers G and H carried (`RECHECK5_FIXES_CIA.md`).", "its findings fixed and the owner's answers G and H carried (`RECHECK5_FIXES_CIA.md`). Done: a narrow final check of those fixed lines (0 blocking, 1 should fix, 4 minor; `FINAL_CHECK_DRAFT5.md`), its findings fixed (`FINAL5_FIXES_CIA.md`); these last fixes are wording only and were not checked independently again, to avoid a loop.")
rep2("to questions 1 to 6 and eight further decisions (owner record items 15 to 28), and the fixes of an independent check of draft 5 (`CHECK_DRAFT5.md`, 2 blocking, 10 should fix, 10 minor; fixes in `CHECK5_FIXES_CIA.md`)",
     "to questions 1 to 6 and ten further decisions (owner record items 15 to 30), and the fixes of three independent agent checks of draft 5 (`CHECK_DRAFT5.md`, `RECHECK_DRAFT5.md`, `FINAL_CHECK_DRAFT5.md`; fixes in `CHECK5_FIXES_CIA.md`, `RECHECK5_FIXES_CIA.md`, `FINAL5_FIXES_CIA.md`; see section 8)")
rep2("this assessment's questions and decisions (items 15 to 28)", "this assessment's questions and decisions (items 15 to 30)")
rep2("**Every question is answered** (owner record items 15 to 28, 2026-11-13): six questions, the CR-10 decision (item 19), the platform-held records (item 22), and six more (A to F) from the independent check of draft 5.",
     "**Every question is answered** (owner record items 15 to 30, 2026-11-13): six questions, the CR-10 decision (item 19), the platform-held records (item 22), six more (A to F) from the independent check of draft 5, and two (G and H) from its re-check.")
# GPT's targeted confirmation of draft 5: S3 and m1
rep2("a builder with only one person allowed to approve may approve his own settings, budget and retention steps and confirm the values he keyed, each marked as done by the person who entered it (questions 1, 5, C, D and E),",
     "where exactly one person is authorised for the relevant kind of record, that person may approve his own settings, budget and retention steps and confirm the values he keyed, each marked as done by the person who entered it (questions 1, 5, C, D, E and G),")
rep2("06_change_request_sources/APG_8_LAYER_DESIGN_BLUEPRINT_v0.1/", "06_change_request_sources/8_layer_v0.1/")
rep2("Still to come: GPT's targeted confirmation of the fixes (the one-person exception and the relaxations, the two reworded sentences, the retention definition, the M15 register revision 4.1), as GPT advised.",
     "Done: GPT's targeted confirmation of draft 5, the last review round by the owner's decision (owner record item 31): 0 blocking, 4 should fix, 2 minor, and \"ready for the owner's formal approval once the four SHOULD FIX and two MINOR corrections are made; no further GPT or agent review is warranted\" (`GPT_REVIEW_DRAFT5.md`). The builder made those corrections without further review (`GPT5_FIXES_CIA.md`). Still to come: the owner's formal approval.")
open('CIA_SOURCE.md', 'w').write(s)
print('patched')
