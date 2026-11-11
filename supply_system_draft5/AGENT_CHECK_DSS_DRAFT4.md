# Agent check of APG Data Supply System, draft 4: INDEPENDENT READ-ONLY (agent)

I am a separate, fresh agent with no part in writing the draft. This is a scoped check, done in one pass, using only the folder `check4_in`. I edited nothing in that folder. To re-run the generators I copied the folder to a scratch location first.

## Totals

| Class | Count |
| --- | --- |
| BLOCKING | 0 |
| SHOULD FIX | 12 |
| MINOR | 12 |
| OPTIONAL | 2 |
| **Total** | **26** |

## What I did

1. **Compared draft 3 with draft 4** using Python difflib, and checked only the changed lines. Unchanged text is not raised again.
2. **Re-ran `build_field_coverage.py rev3`** on a copy. Its output was `rows 39 template field mentions 89 gaps 0`, and `FIELD_COVERAGE.csv` came out **byte-identical** to the one in the pack. I also re-ran `build_supply_plan.py rev3`: `SUPPLY_PLAN.csv` and `RELEASE_A_COVERAGE.csv` are identical too, which confirms both are unchanged from draft 3.
3. **Checked the field coverage independently, per record kind.** I wrote my own parser that assigns each field named in `RULE_INPUT_CONTRACTS.csv` to the record kind it follows, then looked for it in `FIELD_REGISTER.csv` under that kind only.
4. **Checked the new claims against the source text:** the blueprint (S04 §5, §6, §8 to §18; S06 §5.1, §9.1, §10; S10 §9; Section 18 §6 and §8), the code (`fin/costs.py`, `fin/cashview.py`, `ingest/reconcile.py`, `det/intake.py`), `SUPPLY_PLAN.csv` rows E17 to E19 and E83, and the four review files.

## Field-level coverage: independent verification

- **The counts are right.** The script finds 89 mentions (counting each field once per contract row) and 65 distinct field names. Counting without that per-row de-duplication gives 91.
- **The result holds when checked per record kind.** Every field name containing an underscore that a contract gives for a supplied record exists in `FIELD_REGISTER.csv` under that same record kind. My only mismatches came from parsing:
  - In AGG, "supplier" is a grouping key, not the supplier record.
  - "Every M4 figure: the record's project_ref" names no record kind.
- **The script's method is weaker than described.** It checks each name against the fields of *all* record kinds pooled together, not against the named kind. Details are in finding S1.
- **The other items have a real supplier in the code:**
  - `invoice_lines` is calculated in `fin/costs.py:51`.
  - `duplicate_of` is set by the intake in `ingest/reconcile.py:292`.
  - The carrying components are calculated outputs.
  - `instruction_types` is listed among N01's settings.
- **Not checked, and not all stated as limits:**
  - Plain-word field names ("amount", "delta", "quantity", "reason", "treatment", "flags", "withheld").
  - Every setting in the contracts' "configuration or parameter" column: the E90 policy fields, and the N01 thresholds and windows.
  - Retention-event fields. They have no field definitions at all.
  - Whether the templates in the register actually exist in the code. The template files are not in the pack. Revision 3 itself calls `FIELD_REGISTER.csv` "an inventory ... not a validated schema register".

## Review points: is the stated outcome in draft 4?

### GPT design review

| # | Verdict | Note |
| --- | --- | --- |
| 1 | PARTLY | A field check exists and its counts are right. But it checks names against all record kinds pooled, skips the configuration fields, and leaves authority and verification to PG-DS-AC-12 (S1, S2, S3). |
| 2 | FIXED | Written M6 contracts are a gate for release A. |
| 3 | FIXED | One shared intake envelope, with processing specific to each record kind. |
| 4 | FIXED | Separate milestone, regression baseline taken first, differences signed off. |
| 5 | FIXED | See M8 on "change of authority". |
| 6 | FIXED | AC-02 is now partly circular (M3). |
| 7 | PARTLY | The prose now separates the two kinds of record, but the count of 17 and the word "derives" still mix them (M1). |
| 8 | FIXED | Goes further than S04 §11 allows (S10). |
| 9 | FIXED | |
| 10 | FIXED | Progressive delivery and the middle path. GPT's position is misreported (S5). |
| 11 | FIXED | The fallback for each file-only fact is not named (O1). |
| 12 | FIXED | Early discovery gate. |
| 13 | FIXED | |
| 14 | FIXED | |
| 15 | FIXED | |
| 16 | PARTLY | "The other release A items do not wait for it" conflicts with items 3 and 4 (S4). |
| 17 | FIXED | |
| 18 | PARTLY | Added to the text, but AC-07 still covers scanning only (M2). |
| 19 | FIXED | |
| 20 | FIXED | Four tests. |
| 21 | FIXED | |
| 22 | FIXED | |
| 23 | FIXED | AC-09 updated. |
| 24 | FIXED | |
| 25 | FIXED | The lifecycle is in the text but not in AC-10 (O2). |
| 26 | FIXED | |
| 27 | FIXED | |
| 28 | Answered, reasonably | The PG-DI criteria are in the pack (I confirmed S04 §19). GPT's EDR-22 and AUIF part is not answered (M12). |
| 29 | Answered, reasonably | I checked the mapping against Section 18 §8: phase 1 covers identity, tenant isolation and ingestion/source authority; phase 2 the financial core; phase 3 domain intelligence; phases 4 to 6 the evidence. It agrees. The cited "N7" is not in the pack, so I could not check that reference. |
| 30 | FIXED | |

### GPT governance note

| Point | Verdict | Note |
| --- | --- | --- |
| Roles | FIXED | Not mapped to the readiness roles (M6). |
| Outside data | FIXED | |
| Corrections | FIXED | |
| Retention and close-out | PARTLY | Listed, but called a gap "in the locked blueprint itself" (S12). |
| Access | PARTLY | Cites S04 §6 and §16 for sharing with joint ventures and related companies, which those sections do not cover (S11). |
| Failed supply | FIXED | AC-13. |
| Builder effort | FIXED | |
| Evidence trail | FIXED | |

### Gemini design review

| # | Verdict | Note |
| --- | --- | --- |
| 1 | FIXED | |
| 2 | FIXED | Document upload stays in release A but the document record (E83) stays in "later" (S8). |
| 3 | Answered | Declining invented defaults is well argued (S04 §10, PG-DI-AC-11). For builders who do use the market figures, the hand-filling burden remains and the way in is not stated (S6). |
| 4 | PARTLY | Labelled FIXED. Defaults are adopted, but the decline of state-specific defaults gives no reason (M5), and some N01 items cannot have defaults (M4). |
| 5 | PARTLY | Labelled FIXED. Gemini asked for the minimum as the baseline; the draft chose the middle path. That is a reasonable answer but a partial acceptance (M10). |
| 6 | FIXED | |
| 7 | FIXED as decision 7 | E17 to E19 are confirmed in "later" in `SUPPLY_PLAN.csv` ("input to an insight not built yet"). No contract's "known limit" names them. The recommendation is not explained (S9), and "both reviews" is wrong (S5). |

### Gemini's five further ideas

They stay a list and do not widen the design. Stat-dec gating is correctly recast as "APG flags, a person decides" (S10 §9). Declining one-tap links is well argued (S04 §6, PG-DS-AC-05). The learning cost-code map is called "allowed" in terms that conflict with the design (M11).

## Problems

### SHOULD FIX

**S1. The field check compares names against all record kinds pooled, not the named kind, so it does not do what its docstring and the draft say.**
- `build_field_coverage.py` takes the union of every kind's fields and asks whether each name appears anywhere in it. The docstring says "a field of that record kind". The draft says the check "fails if one appears".
- A contract naming a field that exists only on some other kind would pass.
- My per-kind check passes, so the result stands, but the method needs correcting. One contract row shows the weakness: "every M4 figure: the record's project_ref". `project_ref` does not exist on `credit_note`, `po_amendment`, `bank_txn` or `facility`. It passes only because other kinds have it. (In the code, `bank_txn` is linked through retention events, `fin/cashview.py:45-47`.)
- Plain-word names are skipped entirely, because only names containing `_` are checked.
- **Fix:** check each field against its own kind. Handle the `project_ref` row explicitly (project found through a linked record; facility is organisation-level). Fail on any plain-word name that has no stated corresponding field.

**S2. "Every field a current rule or M4 figure reads is checked separately" (Purpose rule 2) overclaims, and the stated limits leave out the biggest exclusions.**
- Not checked:
  - The contracts' whole "configuration or parameter" column (E90 policy fields; N01 thresholds, windows and pairs).
  - Plain-word fields.
  - Fields the contracts do not name, such as the bank-transaction link.
  - Retention-event fields, which have no definitions.
- The phrase "carried by an existing template today" rests on revision 3's register, which revision 3 itself calls an inventory and not a validated schema register. The template files are not in the pack.
- Line 139 says retention events "are recorded by a person", in the present tense. Today `fin/cash_states.py` writes them directly.
- **Fix:** reword rule 2 to "every field the contracts name for a supplied record". Add these exclusions to "Its limits". Write the retention-event sentence in the future tense.

**S3. PG-DS-AC-12 and the text describing it disagree, and AC-12 is not among release A's gates.**
- The text says AC-12 "makes the full check, for every way in, a release condition".
- AC-12 itself requires "at least one built way in" per field.
- "Release A is not complete until two gates are passed" lists only the M6 contracts and the migration.
- **Fix:** choose one reading (at least one way in, or every way in). State whether AC-12 is a release A gate. If it is, make it the third gate.

**S4. Release A item 1 conflicts with items 3 and 4 over what waits for the migration.**
- Item 1's scope includes "the directly written records": retention events and authority-register rows.
- It then says "the other release A items do not wait for it".
- But item 4 moves retention events "through that form and the intake, replacing today's direct write", and item 3 routes the authority register "through the intake". Both are inside item 1's scope.
- **Fix:** either take the three direct writes out of item 1 and say they enter the reference intake as new record kinds, independent of the 24-kind migration, or state that items 3 and 4 depend on item 1.

**S5. Reviewers' positions are misreported in three places that inform the owner's decisions.**
- **Line 100:** "Both design reviews agreed with Level 2". Gemini says nothing about phone capture.
- **Line 186:** "Both design reviews said the earlier recommendation ... is too much". GPT said "keep the recommended scope as the target, but make rollout progressive", and its verdict agrees with entry screens and document capture being in release A. Only Gemini called it over-scoped.
- **Line 197:** "Both reviews flagged them as a main source of profit leakage". Only Gemini did; GPT does not mention subcontractor claims as leakage.
- **Fix:** attribute each position correctly. This matters most for decisions 2, 4 and 7.

**S6. The middle path does not say how the five M6 supplements would be supplied, and for three of them there is no form.**
- The bullet sits under "Entry forms only for ..." and implies forms.
- But `SUPPLY_PLAN.csv` lists no entry screen for E27 (specification requirement), E31 (quote tier) or E32 (quote term), only a template and document capture. Finished document capture is not in the middle path.
- So for a builder who does use the market figures, these remain hand-filled synthetic templates. That is the burden Gemini point 3 raised.
- **Fix:** name the way in for each of the five under the middle path. For E27, E31 and E32, either a hand-filled template or the person-keyed document upload extended to them. Say so in the answer to Gemini 3.

**S7. "Even so, seven release A facts come only by file" was carried over from draft 3, where it followed "with both additions". Under the middle path it is misleading.**
- The seven (E21, E24, E29, E36, E37, E57, E73) are the release A facts with no entry screen or document route in any option. That checks out.
- But under the middle path, entry forms exist only for the first pilot's insights, and document upload carries values only for quote readings. So many other release A facts also come only by file until their form is added: contracts, variations, budget, forecast lines and others.
- **Fix:** "Seven release A facts have no other way in under any option; under the middle path, others also come by file until their form is added."

**S8. The middle path keeps uploaded documents as evidence, but the document record (E83) stays in "later". And "person-keyed verification" does not say who verifies.**
- The text says originals are kept and attached to records, and that only finished capture "moves the document record (E83) into scope". Yet E83 is in "later" in `SUPPLY_PLAN.csv`.
- Item 4 says "values keyed by that person". It reads as if the same verifier both keys and confirms the value. Section 04 §12's verification applies to AI/OCR-extracted values. A keyed value is manual entry under §18.
- **Fix:** either put E83 in release A for the upload, or say where the originals are held. State whether keyed quote readings need a second person to confirm them, or why the keyer's own confirmation with the attached document is enough.

**S9. Decision 7 recommends promoting E17 to E19 without saying what that would deliver.**
- By the draft's own release rule (decision 3), release B data "changes nothing until the rule or figure that would use them is changed".
- No current rule names E17 to E19 even as a limit. The only consumer would be the back-to-back claim check, which is listed as "not designed here".
- Promoting them means collecting data that nothing reads, unless a new rule follows under its own change request.
- **Fix:** state this in decision 7. Either tie the promotion to taking the back-to-back idea forward (decision 8), or say the benefit is only that the data is ready early.

**S10. "An uncertain or material match is held until a person confirms it" goes further than Section 04 §11.**
- §11 allows matching on stable IDs, approved cross-reference tables and documented composite rules. It forbids only "confidence alone" authorising a material merge.
- Almost every invoice-to-PO or project match is material, so read literally, nearly every match waits for a person. That works against the adoption aims elsewhere in the draft.
- **Fix:** "a match that is uncertain, or material and not made by a stable ID or approved cross-reference rule, is held until a person confirms it".

**S11. Access boundaries "including information shared between related companies or joint ventures (S04 §6, §16)" cite sections that do not cover it.**
- S04 §6 is about checking tenant, organisation, project and entity scope on every ingestion path. S04 §16 is tenant isolation.
- Neither defines sharing across related companies or joint ventures. Sharing across tenants could conflict with §16.
- **Fix:** say the blueprint does not define this sharing, that it needs its own decision, and add it to the cascade list (Section 01 tenant model, Sections 15 to 17 security).

**S12. "Gaps in the locked blueprint itself: data retention ..." is claimed from four sections.**
- The pack holds only S04, S06, S10 and Section 18, plus file 11.
- S04 §6 already defers to "discovered platform security and retention conventions", and S04 §16 covers backups.
- Sections 15 to 17 (security, reliability and recovery) and Section 09 are not in the pack.
- **Fix:** "Not found in the sections in this pack (S04 §6 defers to platform retention conventions); confirm against Sections 09 and 15 to 17 before raising a change request."

### MINOR

**M1. GPT 7 is only half done.**
- The heading "Records APG calculates (17 entities list it; 8 built or partly built)" still counts E02 and the five records a person confirms (E68, E71, E77, E88, E97). E77 (retention events) is one of the "8 built or partly built".
- "Records APG derives" survives in purchase rule 1 of the mechanical rule, the Level 1 introduction, the words-only description of the diagram, AC-01 and decision 1.
- **Fix:** split the count (11 calculated, 5 confirmed by a person, 1 setup question with a calculated alternative) and use one term throughout.

**M2. AC-07 still covers only scanning.**
- GPT 18 asked for safe parsing, limits and rejection of malformed files as part of the acceptance design.
- **Fix:** extend AC-07, or add a criterion.

**M3. AC-02 is circular.**
- Inputs are "equivalent" when they have "the same values", and equivalent inputs then "give the same field values".
- **Fix:** define equivalence on the source facts before mapping, and test that mapping produces identical field values and the same rule outcome.

**M4. N01 cannot be fully pre-set to defaults.**
- R07's comparable pairs are "declared by a person". R04B's instruction types are specific to each builder.
- It is also unclear whether the builder's approver must accept the shipped defaults before they take effect (AC-05).
- **Fix:** list the N01 items that have no default, and say what approval the defaults need.

**M5. The answers to Gemini 3 and 4 do not explain two things.**
- Why defaults are acceptable for N01 thresholds (they are settings) but not for the M6 supplements (they are facts). One sentence would do.
- Why state-specific defaults are declined ("not tied to one state's contract forms" has no reason).
- **Fix:** add the reasons.

**M6. Governance roles and readiness roles are not mapped to each other.**
- Governance names five roles: supplies, checks, corrects, approves, accountable. Readiness names three: holder, action owner, approver.
- "For each kind of record the builder names" five roles also cuts against the progressive setup.
- **Fix:** map the two sets. Say the roles start from defaults and are asked for progressively.

**M7. "A nudge links straight to the form that fixes it" overpromises.**
- Many fixes are a file, the review queue, or a way in that is not built yet.
- **Fix:** "to the way in that fixes it (form, upload or review queue)".

**M8. "A change of authority mid-project is held for a person" catches approved changes too.**
- Read literally, it holds even an approved, versioned change to the authority register, which already has effective dates under S04 §5.
- **Fix:** limit it to an unapproved or overlapping change.

**M9. Some review counts are imprecise.**
- "Five reviews shaped it" lists four reviews plus a note.
- The fix list quotes GPT's class totals, which sum to 29, while also saying GPT made 30 points. The class labels are the builder's inference.
- **Fix:** state these exactly.

**M10. The fix list says "Fixed" where the change was partial.**
- GPT 1, 16 and 18; Gemini 4 and 5.
- **Fix:** relabel them "Fixed in part" or "Answered".

**M11. The ideas list calls the learning cost-code map "allowed" in terms that conflict with the design.**
- The text: "allowed ... a person still confirming low-confidence ones". That implies high-confidence matches would apply automatically.
- This conflicts with line 84 ("the builder confirms each one") and with S04 §11 ("confidence alone must not authorise").
- **Fix:** keep every confirmation, or note that changing this rule belongs to that idea's own change request.

**M12. GPT 28's request about EDR-22 and AUIF is not answered.**
- **Fix:** say that the EDR-22 vendor requirements and the AUIF contracts are not in the pack and stay dependencies.

### OPTIONAL

**O1.** For the file-only facts, name the fallback (a hand-filled template) and say it is available in release A, as GPT 11 asked.

**O2.** Add the gap lifecycle states to AC-10 so that they can be tested.

### Wording for a non-technical owner (guidance, not counted in the totals)

"Intake envelope", "control checkpoints", "canonical mapping" and "regression baseline" appear without a plain gloss. Add one plain-language clause each where they are first used.

## Verdict

Draft 4 answers both design reviews in substance. The new field-level check is reproducible, its counts are right, and my own per-kind check confirms that no field named for a supplied record is missing. The governance section and AC-13 are faithful to the GPT note, and the ideas list stays a list rather than widening the design. Nothing is presented as built that is not, and nothing blocks. But it is not quite ready for the owner's decisions. The 12 should-fix points are all text edits:
- Three misreported reviewer positions bear directly on decisions 2, 4 and 7.
- The field check promises more than it does (pooled kinds, no configuration fields).
- AC-12 has two readings and an unclear place among release A's gates.
- The migration gate contradicts items 3 and 4.
- The middle path leaves the M6 supplements, the document record and keyed verification unclear.
- Decision 7 does not say that promoting E17 to E19 delivers nothing until a new rule exists.
- Three blueprint citations go further than the text (entity matching, joint-venture access, data retention).

These can be fixed and checked with a scoped look at the changed lines. A further GPT or Gemini round is not needed.
