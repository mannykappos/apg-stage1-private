"""Draft 7, second stage: the fixes from the scoped re-check of Data Readiness revision 4 (S5, M1, M11, M12, M13 and the field-level
figures S1, S2) and the owner's decisions of 2026-11-12 taken in dialogue (decision 13, the extras and variations panel, severity grading
set by the builder).  Applied to the output of make_draft7.py.  Each replacement must match exactly once.  Builder work (Claude), not
independent.
usage: python3 -I make_draft7.py DRAFT6.md DRAFT7_stage1.md && python3 -I make_draft7b.py DRAFT7_stage1.md DRAFT7.md"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src).read()
R = [
 ("The owner chose Level 2 with an early discovery gate (decision 4),", "The owner chose Level 2 with an early discovery gate (decision 6),"),
 ("the eight below are the ones this design states:", "the eight below are the ones this design states, numbered in this draft's own order (the decisions document's numbers are cited in brackets elsewhere):"),
 ("Formal approval still needs revision 4's scoped GPT check and the Section 18 cascade impact assessment; no build is authorised.",
  "Two agent checks of revision 4 and the owner's further decisions of 2026-11-12 are folded in too: decision 13 (APG tells the builder what it needs, across the whole of APG), the extras and variations panel, and severity grading set by the builder at setup (see the last section). Formal approval still needs revision 4's scoped GPT check and the Section 18 cascade impact assessment; no build is authorised."),
 ("(56 rows, 43 rules and figures, three of the rows stating behaviour shared by a group)",
  "(56 rows, 43 rules and figures; five rows state behaviour shared by four groups)"),
 ("It is not linked to the intake and cannot verify dates yet.",
  "It is not linked to the intake, and a date a person verifies is kept as text and does not reach the authority logic."),
 ("Today they are held as versioned, approved policy records, with no builder setup question.",
  "Today they are held as versioned policy records, counted as approved only once an audited approval exists; the schema and approval logic are in code, and there is no builder setup question."),
 ("- Every answer is versioned, submitted through the intake, and approved by the right role before it takes effect. \"Partly\" (the financial policy) means the policy object exists in code with no builder setup.",
  "- **Severity grading is the exception (the owner, 2026-11-12).** How serious a finding is (its grade) is set by the builder at setup, with no defaults and no suggested levels, because builders' jobs range from a couple of million dollars to a hundred million. For each grade the builder may set a dollar amount, a percentage of the job, or both; with both set, the grade applies as soon as either is reached. Until he has set them, every finding still shows, marked \"grading not set up yet\", with what to do. How the builder's own setting relates to the existing approval of policies by a second person (F-67, PG-DS-AC-05, S06 §8) is settled in the Section 18 assessment. Today severity bands are dollar amounts only, and the code grades with them whether or not anyone approved them (defect candidate DC-11); the materiality model (`materiality.py`) can measure against contract value, forecast final cost or forecast margin, but no severity grading uses it, so grading by a percentage of the job is new design and new code.\n- Every answer is versioned, submitted through the intake, and approved by the right role before it takes effect. \"Partly\" (the financial policy and the rule settings) means versioned policy records exist, counted as approved only once an audited approval exists, with no builder setup question."),
 ("one per contract row that names configuration, per settings entity (56 rows: N01, E90, E03, E20, E04)",
  "one per contract row that names configuration, per settings entity (55 rows: N01, E90, E03, E20, E04)"),
 ("What it shows today: every field is accepted by a built way in, but only by a synthetic template (19, all on quotes and quote readings, also by document capture, which is only partly built); field authority is resolved for 6 fields, the material amounts of the reference intake; 48 more pass through the reference intake with link, duplicate and supplier checks only;",
  "What it shows today: every field is accepted by a built way in, but only by a synthetic template; document capture accepts none of them into the intake yet (it is partly built, not linked); field authority is resolved for 6 fields, the material amounts of the reference intake; 33 more get the reference intake's record-level duplicate, supplier or link checks, and 15 its field validation only;"),
 ("- 29 rows need the rule settings (N01), 23 name financial-policy fields (E90), and 9 need both.",
  "- 29 rows need the rule settings (N01), 23 name financial-policy fields (E90), and 9 need both, as the supply plan counts them (a detection or M6 rule needs N01; a row needs E90 when it names a policy field). `FIELD_SUPPLY_ROUTES.csv` counts settings rows by the entity a contract's configuration names instead (28 rows name N01, 24 name E90), so the two counts differ by design. `SUPPLY_PLAN.csv`, `RELEASE_A_COVERAGE.csv` and `build_supply_plan.py` are in the pack."),
 ("- 48 rows name an input, a record or a setting, whose minimum way in is not fully built.",
  "- 47 rows name an input, a record or a setting, whose minimum way in is not fully built."),
 ("One of the 48, overdue receivables, needs only release B data.", "One of the 47, overdue receivables, needs only release B data."),
 ("The three records written directly today (retention events, authority register rows, extracted documents) are not part of this migration:",
  "The two direct writes (retention events, extracted documents) and the in-code authority register are not part of this migration:"),
 ("5. **The M6 input contracts.** Written first, so the market figures' inputs can be checked like the rest.",
  "5. **The M6 input contracts.** Written in revision 4, so the market figures' inputs are checked like the rest; approved with it."),
 ("6. **Readiness for the builder.** The readiness record (with the findings and calculation runs it depends on), the onboarding checklist, the missing-data list and nudges.",
  "6. **Readiness for the builder.** The readiness record (with the findings and calculation runs it depends on), the onboarding checklist, the missing-data list and nudges; every message a rule or figure gives when it cannot fully assess tells the builder what to do (decision 13)."),
 ("Because originals are kept, choosing the middle path moves the document record (E83: the original file and its hash) into release A.",
  "Because originals are kept, choosing the middle path moves the document record (E83: the original file and its hash) into release A. The supply plan places entities by the mechanical release rule, so it still lists E83 under \"later\"; with the owner's choice applied, release A is 45 entities, and later 28."),
 ("Their minimum ways in are mostly templates (14 of the 22, 13 still to build).",
  "Their minimum ways in are mostly templates (15 of the 22: 1 built, 14 still to build)."),
 ("| PG-DS-AC-13 |", "| PG-DS-AC-14 | Whenever a rule or figure cannot fully do a check or a figure, it says so: what is missing, why it matters and what the builder is to do. No case is silent, and nothing is shown as complete when it is not. Each message is proven by a test when it is built; a list generated by scanning the code holds every message the scan finds and fails if the code gives one it does not cover (decision 13). |\n| PG-DS-AC-13 |"),
 ("5. **The acceptance criteria.** PG-DS-AC-01 to 13.", "5. **The acceptance criteria.** PG-DS-AC-01 to 14 (14 added with decision 13)."),
 ("and the Master Requirements Traceability Matrix (new rows for PG-DS-AC-01 to 13).",
  "Sections 11, 05 and 03 (the extras and variations panel, and the cost of extra work recorded against its instruction or variation); Sections 06 and 10 (decision 13's messages, and severity grading set by the builder, against S06 §5.1 and §8); and the Master Requirements Traceability Matrix (new rows for PG-DS-AC-01 to 14)."),
 ("a stand-in quote parser; not linked to the intake; dates cannot be verified yet |", "a stand-in quote parser; not linked to the intake; a verified date is kept as text and does not reach the authority logic |"),
 ("8. **Reviewers' further ideas.**", "8. **Reviewers' further ideas.**"),
]
for a, b in R:
    n = s.count(a)
    assert n == 1, (n, a[:80])
    s = s.replace(a, b)
# the PG-DS-AC-14 row is put after 13, keeping the table in order
a = s.index("| PG-DS-AC-14 |"); b = s.index("\n", a) + 1
row14 = s[a:b]; s = s[:a] + s[b:]
c = s.index("| PG-DS-AC-13 |"); d = s.index("\n", c) + 1
s = s[:d] + row14 + s[d:]
# readiness: decision 13 and the message list
anchor = "An insight whose input has no built way in is shown at the state its gate gives:"
assert s.count(anchor) == 1
s = s.replace(anchor, """**Every message tells the builder what to do (decision 13).** The owner's rule of 2026-11-12, for the whole of APG: whenever a rule or figure cannot fully do a check or a figure, it says what is missing, why it matters and what the builder is to do, and nothing is silent or shown as complete when it is not. Revision 4's `NOT_ASSESSED_MESSAGES.csv`, generated by scanning the code, lists the messages the production modules give (579 entries, including the 12 cases DC-1 to DC-12 that give no message today), each with who sees it and what the builder is told to do; it fails if the code gives a message its patterns find and the list does not cover. A scan cannot prove that no message is built another way, so each message is proven by a test when it is built. The readiness record, the missing-data list and the nudges deliver those messages; the defect change request after stage 1 is the first place they are built.

""" + anchor)
# the owner's further decisions, after the eight
anchor = "**The cascade impact assessment must cover at least:**"
assert s.count(anchor) == 1
s = s.replace(anchor, """**Added by the owner on 2026-11-12, in a question-by-question dialogue** (his words are quoted in the decisions record; these carry no list numbers, so they do not collide with the decisions document's numbering, which this draft uses elsewhere):

- **Decision 13: APG tells the builder what it needs, across the whole of APG.** "This feature of telling the builder what apg needs to work should be across the whole apg." Every message names what is missing, why it matters and what to do (PG-DS-AC-14); revision 4's message list is the starting inventory. First built in the defect change request after stage 1 (DC-1 to DC-12).
- **Owner requirement: extras and variations in their own panel.** The original build's budget and profit stand on their own; each extra or variation shows its value, status, cost so far and effect on the job's profit; the two are never blended. The money in is already kept separate by the locked blueprint (S11 §3, §4, §8.1 and PG-CR-AC-09; S03 §5 and §6.1; S05 §3.2; S05 §7 lists unrecovered variations as a way profit leaks) and by stage 1's revenue figure; the cost of each extra is not, because costs are recorded only against cost codes. The data need it adds: the cost of extra work, recorded against its instruction or variation (in the register on E09 and E10; how the cost records E23, E57 with E59, and E64 carry it is settled in the Section 18 assessment). When the client rejects a variation, the builder records the outcome (disputed, at his own cost, resubmitted, withdrawn); APG records a dispute and does not judge it (S11 §11).
- **Owner requirement: verified figures first, what is waiting beside them by category.** The main budget and profit count only what is verified and approved (as S05 §3.2, S11 §8.1 and S03 §5.4 already require); beside them, each item not yet final is shown in its own column (waiting for approval, on hold, disputed, rejected) with its dollar amount and its effect on the budget or profit if it goes through; categories are never added into the main figure. The owner: "So the builder can see exactly whats what and not confused". With the extras panel, through the Section 18 assessment.
- **Owner decision: severity grading set by the builder at setup:** a dollar amount, a percentage of the job, or both, the grade applying as soon as either is reached; no suggested levels (see setup questions). Told the percentage part is new design and new code, the owner confirmed: "Yes offer both at setup".

""" + anchor)
open(dst, 'w').write(s)
print('draft 7 stage 2 written', len(R), 'replacements')
