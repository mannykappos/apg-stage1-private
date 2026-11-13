Worked for 4m 36s

### APG-CR-DSR — Section 18 cascade assessment, draft 4

Initial disposition: NOT READY for formal approval yet. The assessment is substantial and its generation process reproduces correctly, but the owner's new Option B decision changes the approval analysis. The current draft still says the answer is pending, and one proposed addition gives the exception a wider scope than the owner approved.

I also found two pre-approval dependencies that the assessment itself says remain outstanding: the M15 entity-to-RTM cross-check and the CR-10 overlap check. The latter cannot be completed from this pack because CR-10's text is absent.

I have reviewed the assessment, all 81 proposed additions and 10 version-line changes, the impact and dependent-text tables, the three agent checks and their fix records, the supplied change-request documents and owner decisions, and the relevant locked sections. I also ran both reproduction commands; the generated tables and Markdown assessment match the supplied files byte for byte.

### 1\. BLOCKING findings

### B1. Option B has not been incorporated into the proposed requirements, and DS017 makes the exception too broad

BLOCKING · medium cost

The owner has now selected Option B. The assessment still treats the decision as pending and does not carry the approved exception accurately into the proposed wording.

Where the pack falls short

* `01_ASSESSMENT_DRAFT4.md` §1, line 25 says no approval or check is weakened, with Option B merely described as a possible future exception. Option B is now the owner's decision.

* §11, lines 441–445 still presents the two options and says the answer is pending.

* §10, M10 at line 420 still says the approval arrangement is an open question.

* `CIA_PROPOSED_TEXT.csv`, `APG-S04-DS017`, says one person may hold several of the supplier, checker, corrector and approver roles for each kind of record. That is broader than the owner's decision, which concerns a builder approving his own settings.

* `APG-S04-DS026` still has a bracketed placeholder for the one-person approval case. It does not state the approved exception or require the permanent marking of each setting and every figure using it.

* `APG-S06-DS001` has a similar placeholder about the builder's approver accepting product-owner-approved detection defaults. Those defaults are not necessarily the builder's own settings; the owner's answer does not clearly authorise self-acceptance of them.

* `PG-DS-AC-05` requires approval by the required role but says nothing about the one-person exception or its permanent audit marking.

The locked requirements can accommodate Option B, but only with a carefully bounded exception.

* S02 §3.1, paragraph 31, says preparation and approval should be separated where practical and supported by policy. The owner's decision supplies that policy exception for a builder with only one authorised person.

* S02 table 2, row 25, PG-FR-025, requires appropriate segregation of duties for material financial approvals, retention/security decisions and working-capital actions. The owner's decision expressly relaxes that segregation for the builder's own settings in the one-person case.

* The code's `apg/policy_approval.py`, lines 90–104, refuses approval by the proposer. The exception requires a controlled change to that rule for the defined settings case.

* S15 §15.4, paragraph 46, requires separate approval authority. The assessment's reading of this as a distinct approval permission is possible, but the permission and audit trail must remain distinct even when the same person holds both roles.

* S15 §15.11, paragraphs 127–135, continues to require human approval for consequential actions, including changes to authoritative financial rules and approved baselines.

Concrete fix

Update the four proposed items and the assessment's summary and carried matters so they say, in substance:

* When a builder has exactly one authorised person, that person may approve the builder's own settings under this explicit policy exception.

* Each such setting and every figure that uses it permanently carries the marker “approved by the person who entered it”.

* Where there are two or more authorised people, the two-person rule applies.

* The exception applies to settings only. It does not waive human approval for consequential external actions, or the separate second-person verification required for a person-keyed value from an uploaded document.

* The approver permission, approval record, rationale and audit event remain distinct and recorded, even when the same individual performs both roles.

Narrow `DS017`: do not let its general role-combination wording imply that supplier, checker, corrector and approver roles may freely collapse for all record kinds. Make clear that the Option B exception is limited to settings.

For `DS001`, clarify whether acceptance of product-owner-approved detection defaults remains a separate approval from the builder's approval of his own settings. Do not silently extend Option B to that separate act.

Add explicit tests for the one-person exception, the two-person rule, permanent marking of dependent figures, audit confirmation, and preservation of approvals for consequential actions.

### B2. M15 is an explicit pre-approval step but remains undone; DS009 also calls the register an annex prematurely

BLOCKING · medium cost

The assessment says the 100 entities must be cross-checked against every row of the Master RTM before approval:

* §1, line 39: the cross-check is still to happen before formal approval.

* §8, line 382: it is listed as review-before-approval item 2.

* §10, M15, line 425: “Not done” and “a step before approval”.

* `APG-S03-DS009` already describes the controlled entity register as “an annex to this section”.

That is an internal sequencing conflict: the proposed locked wording calls it an annex now, while the assessment says it cannot become an annex until M15 is complete.

Concrete fix: complete and record the M15 cross-check, including exceptions and disposition, before approval; or change DS009 to say the register becomes a controlled annex only after that cross-check is completed and accepted. Do not leave both statements in the approved wording.

### B3. The CR-10 overlap check is required before approval, but CR-10 is absent

BLOCKING · small/medium cost

The assessment correctly identifies a material overlap:

* §6.3, line 269: CR-10, the verified profit ledger, overlaps C14 (verified figures first) and C13 (the extras breakdown).

* §8, line 385: the overlap must be checked against CR-10 before this change request is approved.

But the assessment also says CR-10's text is not in the pack. I therefore cannot verify whether the proposed budget/profit presentation and extras breakdown conflict with, duplicate or change the verified-profit-ledger design.

Concrete fix: include the current CR-10 text or an authoritative extract covering the overlapping requirements, and record the comparison and outcome. If the owner intends to defer a particular overlap, record that explicitly as a separate dependency rather than describing the check as complete.

### B4. E77 retention-event definition does not yet meet two mandatory locked requirements

BLOCKING · small/medium cost

Appendix B, lines 707–727, calls itself a proposed field definition for retention events. It lists `project_ref`, states, amount, evidence and actor fields. It then acknowledges two mandatory requirements:

* S03 §11.1, paragraph 176: every monetary value must have an explicit currency.

* S03 §10.1, paragraphs 136–144: the retention record must identify the associated contract as well as the project.

But neither `currency` nor an associated contract reference appears in the proposed field table. The appendix says they “must add” them; it does not actually define them.

There is a second incomplete point: Appendix B says the mapping of the code's states to S03 §13's illustrative retention lifecycle is settled, but does not show the mapping. The code has `received`, while the illustrative lifecycle includes “Under Review” and does not have `received`. The mapping is therefore not verifiable from the pack.

The C18 test row in §6.4, line 294, also lists no fixtures. The test plan does not explicitly cover the required currency, contract association and lifecycle mapping.

Concrete fix: complete Appendix B with the currency and associated-contract fields, show the explicit lifecycle mapping, and add corresponding test cases and fixtures to C18. The design must preserve S03 §§10.1, 11.1 and 13 rather than defer those mandatory fields to implementation.

### 2\. SHOULD FIX findings

### S1. The remaining RTM gaps will prevent final package acceptance

SHOULD FIX · medium/high cost

The assessment's §6.2 and §13 report:

* 541 paragraphs in Sections 00–18 without RTM mapping;

* 125 table body rows without RTM mapping;

* all 140 paragraphs in Section 18 without RTM rows.

Section 18 §9, paragraph 82, requires the consolidated RTM validation to report zero missing, duplicate, orphaned or unmapped items in the controlled inventory, with manual semantic review documented. Section 18 checkpoint C, paragraph 128, also makes RTM completeness mandatory.

The assessment treats these gaps as a pre-existing observation outside this CR. That may be a reasonable scope boundary for this change request, but the resulting v1.1 package cannot pass the locked final acceptance gate while material requirements remain unmapped.

Concrete fix: record this as a separate, mandatory package-acceptance work item, with an owner and closure evidence. It need not be folded into APG-CR-DSR, but it must not be mistaken for a completed Section 18 §9 gate.

### S2. The referenced 8-layer design baseline is not in the supplied pack

SHOULD FIX · small cost

The README says the 8-layer design blueprint v0.1 is included. The actual `06_change_request_sources/` directory contains the data supply decisions, draft 7, revision 4, GPT re-check and owner decisions, but not that 8-layer blueprint.

The assessment cites it as a dependent at §2, line 52, and uses its §2.11 decisions in M01 at §10, line 411. Those references and the claimed dependency are therefore not verifiable from the pack.

Concrete fix: include the referenced v0.1 document, or correct the README and assessment to identify exactly which supplied source records are being relied on instead. Do not imply the underlying baseline was reviewed if it was not.

### S3. The question 2–4 placeholders need an explicit approval condition

SHOULD FIX · small cost

The remaining questions are well framed, but the proposed wording still contains unresolved owner-confirmation brackets:

* `APG-S06-DS002`: percentage base (question 2) and non-financial classification scheme (question 4).

* `APG-S05-DS001` and `APG-S05-DS002`: the verified-first presentation and extras breakdown (question 3).

The assessment is transparent about these being open. The questions themselves are needed and should remain with the owner. However, the assessment should state whether the owner must answer them as part of formal approval, or whether approval is conditional on their resolution before the affected text is issued or built.

Concrete fix: make the approval path explicit. Do not issue a supposedly final v1.1 text containing unresolved bracketed alternatives.

### 3\. MINOR finding

### m1. Draft date still says “draft 3”

MINOR · trivial cost

`01_ASSESSMENT_DRAFT4.md`, §2, line 47, gives the date as “2026-11-13 (draft 3)”. The document is draft 4.

Fix: change “draft 3” to “draft 4”.

### 4\. Required checks

### Section 18 §6, §9 and checkpoint B

| Requirement                                                              | Result                                       | Reason                                                                                                                                                                                     |
| ------------------------------------------------------------------------ | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| CR identification, requester, date, affected sections and source anchors | Present                                      | §2 identifies the request and the seven amended sections.                                                                                                                                  |
| Current wording, proposed wording, rationale and evidence                | Present                                      | CIA_PROPOSED_TEXT.csv includes each proposed addition and its locked anchor text.                                                                                                          |
| Financial, security, privacy, governance, operational and tenant risks   | Present                                      | §5 covers these areas. The Option B update is still required.                                                                                                                              |
| Downstream dependents                                                    | Present for the locked sections reviewed     | The impact table includes 1,342 distinct locked items. Section 18's §5, §8, §10 and §11 were added after check 3, alongside the other relevant subsections.                                |
| RTM impact                                                               | Partly                                       | The CR's touched items are mapped, but M15 remains outstanding and the wider pre-existing unmapped inventory prevents final package acceptance.                                            |
| Tests and immutable fixtures                                             | Present, with gaps                           | §6.4 names existing suites and fixtures; the Option B and E77 additions need explicit test coverage.                                                                                       |
| Terminology and financial definitions                                    | Present                                      | §6.6 reviews the key terms. The extras view is identified as new semantics rather than a replacement definition.                                                                           |
| Handoff instructions, manifest and hashes                                | Present                                      | §6.7 sets out the post-approval package work.                                                                                                                                              |
| Independent review, named approval and closure                           | Present as a process, not completed evidence | §8 and §9 identify the review and approval steps and leave closure fields to be completed later.                                                                                           |
| Section 18 §9 final acceptance                                           | Not yet demonstrated                         | The RTM completeness issue in S1 remains.                                                                                                                                                  |
| Section 18 checkpoint B                                                  | Substantially present                        | The assessment addresses dependent sections, RTM, tests, fixtures, terminology and package metadata. The outstanding findings above prevent treating the cascade as complete for approval. |

The locked-section dependent list is materially improved and appears complete for the named change items. I found no omitted locked section that is plainly affected but absent from the impact list. The additional Section 18 dependencies are present. This is not the same as saying every downstream acceptance task has been completed.

### Financial definitions, approvals, source authority and tenant isolation

I checked the additions against the surrounding locked text, with particular attention to S03 §§4–6, S05 §§3–5, S11 §8, the terminology register, and the approval and security requirements.

* Financial definitions: the proposed extras view is correctly described as a breakdown of one authoritative forecast final margin, not a second margin. The approved budget remains separate from the forecast. The cost attribution is described as grouping costs already counted, not adding another cost. The remaining owner decision in question 3 is correctly exposed rather than silently decided.

* Revenue states: S11 DS001 keeps the single “Disputed/rejected” state and treats disputed, own-cost and withdrawn as recorded statuses. Resubmission goes through the existing §8.1 process. I found no remaining contradiction in that treatment.

* What-if figures: S05 DS001 maps non-final items to separate columns and keeps their effects outside the authoritative figure. It also directs held records to the provisional-view controls. The question 3 example's arithmetic is correct.

* Source authority: DS026 makes the Source Authority Register a governed setting and does not let the latest arrival decide authority. The owner/approver for the register remains an identified open decision, not something the assessment silently assigns.

* Tenant isolation: the new intake criteria require tenant-isolation tests on each path; the email rule does not infer the organisation from the address. I found no proposed relaxation of S15 §15.5.

* Approvals: Option B is the exception that needs to be precisely incorporated. It must not become a general permission for one person to approve arbitrary consequential actions or to combine all record roles.

### Faithfulness to the data supply design and owner's decisions

The major directions are represented: one intake, readiness reporting, the builder's missing-data instructions, setup questions, cost attribution for extras, verified-first presentation, and builder-set severity levels.

The owner's new Option B answer is the exception: it is not yet reflected as a completed decision in the assessment or its proposed requirements. The pack's owner-decision record still says the answer is pending; the later answer supplied with your prompt supersedes that status and must be carried into the controlled record.

I also found no basis to treat the missing 8-layer source as reviewed. Its content remains not verifiable from the pack.

### Owner questions

* Question 1: no longer an open question. The owner has answered Option B. The assessment should record the decision, its exact scope and its consequences, not ask it again.

* Question 2: accurate and needed. The arithmetic is correct: 2% of $5.1 million is $102,000. The base remains the owner's choice.

* Question 3: accurate and needed. The example arithmetic is correct: $5.2m revenue less $4.7m forecast final cost gives $500,000; the $50,000 variation contribution leaves $450,000 for the original scope. It correctly highlights that forecast cost to complete is an estimate, not an invoice. The owner still needs to decide whether this is what he means by verified-first main figures.

* Question 4: accurate and needed. It distinguishes the money grade from safety and quality classification, and correctly tells the owner that a non-financial scheme outside Section 13 still needs to be designed and approved.

I have not answered questions 2–4 on the owner's behalf.

### 5\. Reproduction and review boundary

I ran, from the pack's parent directory:

```bash
python3 -I 04_tools/build_cia.py 05_locked_package <new folder>
python3 -I 04_tools/assemble.py 04_tools/CIA_SOURCE.md <new folder> <new folder>/draft4.md
```

Both completed successfully. The generated `CIA_PROPOSED_TEXT.csv`, `CIA_RTM_IMPACT.csv` and `draft4.md` matched the supplied files byte for byte.

That establishes reproducibility of the builder's tools and inputs. It does not independently prove the semantic correctness of every dependency assignment or the future implementation.

I reviewed all 81 additions and 10 version-line changes. I did not treat the assessment as implementation evidence. Its design-only boundary is stated correctly: no build is authorised, Stage 2 is not authorised, and no implementation, acceptance or production-readiness claim is made.

### 6\. Final counts and disposition

| Classification | Count |
| -------------- | ----- |
| BLOCKING       | 4     |
| SHOULD FIX     | 3     |
| MINOR          | 1     |

Disposition: NOT READY for formal approval. Fix the four blockers together, update the assessment for the owner's Option B decision, and complete the identified pre-approval checks. The other points are bounded corrections or later package-acceptance work, not reasons for another broad redesign.

Is another review round genuinely needed? Yes, but it should be a single targeted confirmation of the corrected Option B wording, E77 definition, M15 evidence and CR-10 comparison. The assessment's structure, financial presentation and dependent-section analysis do not need another full review loop. Once those four blockers are resolved and the remaining owner decisions are recorded as approval conditions or final choices, I would expect the assessment to be ready for formal approval.
