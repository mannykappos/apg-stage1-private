Worked for 7m 17s

### Draft 5 — targeted confirmation

0 blocking findings

My conclusion: the substantive fixes from draft 4 are in place. I found no reason that formal approval must be stopped. The one-person exception is now properly bounded, the two reworded sentences are identified as owner-approved relaxations, the retention definition is materially complete, and the M15 register has been substantially resolved.

I did find four SHOULD FIX points and two MINOR points. None requires another GPT or agent review under owner record item 31. The builder can correct them directly.

### 1\. Draft 4 findings — confirmation

| Draft 4 finding               | Result | Confirmation                                                                                                                                                                         |
| ----------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| B1 — One-person exception     |        | The scope, relaxations, permanent markers, per-kind two-person switch, approval record and tests are now stated. Details below.                                                      |
| B2 — M15 register cross-check |        | Revision 4.1 has 114 entities. The row-level evidence and remaining 14 closures are accounted for.                                                                                   |
| B3 — CR-10 overlap            |        | It is not claimed to have been checked. The overlap with C13/C14 is explicitly deferred until CR-10 is written, or handled through CR-10's own cascade assessment.                   |
| B4 — E77 retention event      |        | Currency, contract reference, lifecycle mapping and synthetic test cases are now included in Appendix B and PG-DS-AC-17.                                                             |
| S1 — RTM unmapped items       |        | M19 makes the 541 paragraphs and 125 table rows a mandatory, separately owned package-acceptance task. It does not falsely claim that the package-acceptance gate is already passed. |
| S2 — Missing 8-layer baseline |        | The blueprint is now included. There is a minor path typo in the assessment, noted below.                                                                                            |
| S3 — Questions 2–4 unresolved |        | The owner answered them, and the proposed wording carries those answers. The only remaining square-bracket placeholders are the CR number and approval details.                      |
| m1 — Draft number             |        | The assessment correctly identifies itself as draft 5.                                                                                                                               |

### 2\. B1 — one-person exception

I confirm this is now substantively correct. This was the most important part of the review, and I checked the proposed wording, the owner decisions, the test criteria and the relevant locked requirements.

### Boundary — what it covers

The exception applies where exactly one person is authorised for the particular kind of record. It covers:

* The builder's own settings, including accepting product defaults and users/roles where the platform does not supply them.

* The builder's approved budget and its breakdown.

* The approval steps of a retention event.

* Confirmation of values that the builder keyed from uploaded documents.

A capture-only or view-only user does not count as an authorised approver.

### Boundary — what it does not cover

The exception does not extend to the other consequential actions in S15 §15.11:

* Purchase orders and supplier commitments.

* Contract, scope, specification or material changes.

* Claims, notices and commercial communications.

* Deletion or correction of authoritative evidence.

* Security cancellation.

* Any action outside Profit Guardian.

That is an important distinction: retention release is expressly included in the stated relaxation, while security cancellation remains excluded.

### The locked requirements are addressed openly

The assessment correctly identifies the specific relaxations:

* PG-FR-025: the segregation-of-duties requirement.

* F-67: the current code refusal when the proposer attempts to approve their own setting. The supplied `policy_approval.py` code confirms that check.

* S15 §15.4: separate approval authority.

* S15 §15.11: approval of financial rules, approved baselines, privileged access changes and retention release, for the exception's cases only.

The exception does not silently remove the rest of the security approval controls. Each approval retains its own permission, approval record, audit event, rationale and risks considered.

### Permanent markers and the two-person switch

The wording correctly requires:

* The record itself to carry the permanent marker.

* Every figure, finding and report using that record to carry the corresponding marker.

* Existing self-approved records to retain their marker after a second person is added.

* The two-person rule to apply to new records and changes for the particular kind of record once a second person is authorised for that kind.

The bookkeeper example in PG-DS-AC-15 is important: a second person who can confirm keyed values ends the exception for keyed values, not for settings, budgets or retention steps.

### Approval record and tests

Every approval, including self-approval, requires a short reason. The approval record also carries the risks considered, as S15 §15.11 requires. The acceptance criterion says it cannot be saved without the reason.

* PG-DS-AC-05 covers setup-answer approval, markers and the exception's limits.

* PG-DS-AC-15 covers self-approval, product defaults, budget and breakdown, retention steps, keyed values, marker propagation, the per-kind switch, capture/view-only users, audit and excluded consequential actions.

These are design acceptance criteria, not tests already executed. That distinction is preserved in the assessment.

One small wording improvement remains: the plain-language summary in §1 says “a builder with only one person allowed to approve”. It should say “a builder with only one person authorised for the relevant kind of record”. The detailed wording is right; the summary should not accidentally suggest that the exception is determined across the whole business.

### 3\. The two reworded sentences

### S06 §11 — APG-S06-DS005

Owner relaxation correctly stated

The new sentence requires who dismissed or deferred a material finding and when, and requires the rationale only where the person gives one. Evidence is retained and future reassessment remains possible.

That is faithful to owner items 18 and 24. The rationale field in S06 §6 remains; it can be empty where no reason is supplied.

### S00 §00.3 — APG-S00-DS004

Owner relaxation correctly stated

The matching Section 00 sentence records who dismissed an exposure and when, with the reason where one is given. It does not extend the relaxation to the other exposure outcomes.

That matches item 23.

### Consistency with the surrounding controls

* S06 §6: the finding data contract and rationale field remain. Good.

* S06 §9.1: the existing controlled reopening and re-notification rules remain. There is a wording point to clarify below.

* S06 §14: evidence and dismissal review remain. There is a wording point to clarify below.

* S06 §16: preserving evidence and allowing dismissed findings to reopen remain. Good.

* PG-AI-AC-13: dismissal and deferral remain auditable. Who and when are recorded. Good.

* S13 §13.4: financial prioritisation does not override safety or mandatory quality requirements. The finding's non-financial classification is not lowered by a small or missing amount. Good.

* S13 §13.8: dismissing or deferring a finding does not close, verify or change the underlying defect or record. Good.

The owner-approved relaxations are therefore correctly identified. They do not authorise the system to erase a finding, suppress its evidence or treat a defect as rectified.

### 4\. SHOULD FIX — four remaining points

These are not reasons to reopen the review, but I would have the builder correct them before issuing the final controlled text.

S1 — Re-notification wording should explicitly preserve all S06 §9.1 triggers.

Evidence: S06 DS006 and PG-DS-AC-16 say a dismissed finding is raised again “only when something material changes”. S06 §9.1 permits controlled reopening or renewed notification on material new evidence, a meaningful status transition, or an approved escalation condition.

Those may all be intended to fall within “something material changes”, but the assessment does not explicitly establish that interpretation.

Fix: clarify that those three §9.1 events are the material triggers referred to in DS006 and PG-DS-AC-16. That preserves the owner's decision without accidentally narrowing the existing re-notification rules.

S2 — S06 §14.1 should make the optional-reason position explicit.

Evidence: the locked text says a dismissal is not automatically proof of a false positive and instructs the reviewer to “review evidence and reason”. The new policy makes the reason optional.

Fix: clarify that the reviewer considers the evidence and any reason given. This can be an added clarification; it need not create a third reworded locked sentence.

S3 — The §1 summary needs the per-kind qualifier.

Evidence: §1 currently describes the exception as applying where the builder has “only one person allowed to approve”. Owner item 29 makes the rule per kind of record. The detailed wording in §4 and S04 DS026 is correct, but the summary is broader than the final decision.

Fix: say “exactly one person authorised for the relevant kind of record”.

S4 — Draft 7's 100-entity supply-plan figures need to be reconciled with revision 4.1.

Evidence: `DATA_SUPPLY_DESIGN_DRAFT7.md` still describes 100 entities and a supply plan generated from revision 4. The new annex register has 114 entities. The 14 additional entities have proposed supply paths in revision 4.1, and the addendum says the first release is unchanged, but the design's aggregate counts and supply-plan reference have not been updated to show the 114-entity position.

This does not mean I found an entity with no proposed path. It is a consistency gap between the supporting design and the revised register.

Fix: update draft 7 and its supply-plan counts from revision 4.1, or explicitly state that its old 100-entity counts are superseded by the 114-entity register and identify the 14 additional entities as later-release scope.

### 5\. M15 — register revision 4.1

Confirmed, with the documentation qualifications above

I checked the supplied row-level evidence and the actual register, rather than relying only on the addendum's summary.

| Check                                       | Result                                                                  |
| ------------------------------------------- | ----------------------------------------------------------------------- |
| Master RTM rows across the four agent files | 2,712 unique rows                                                       |
| Initial verdicts                            | 649 covered; 52 covered by proposed fixes; 430 gaps; 1,581 no data need |
| First re-check                              | 482 flagged rows: 401 carried, 81 still gaps                            |
| Second re-check                             | 81 rows: 67 carried, 14 still gaps                                      |
| Final 14 gaps                               | All corresponding field additions are present in revision 4.1           |
| Final register                              | 114 unique entities                                                     |

I also checked that the 482 rows in the first re-check are exactly the 430 original gaps plus the 52 covered-by-proposed rows, and that the second re-check covers the 81 remaining rows.

The 14 final closures are substantive, not just status changes. They add the missing fields for downstream processing errors, idempotency-key basis, prioritisation weights, eligibility checks, valuation evidence, quality-baseline comparability, calculation correlation and operational restore/release evidence.

### Class P treatment

The seven class P entities are consistently marked as held by the Anchor platform, to be confirmed in discovery:

* E102 audit event.

* E108 data classification and retention policy.

* E109 background job and external action record.

* E110 incident.

* E111 operational record.

* E112 AI interaction record, conditional on APG keeping AI context.

* E113 identity and access.

This is a sound provisional classification, not a claim that those platform capabilities have been verified or implemented. E102's note is particularly appropriate: discovery must establish whether the platform audit log can hold APG's financial-state transitions with before/after values and evidence; otherwise that history becomes an APG record.

E108 and E113 also list the builder admin as a likely data owner and include setup paths. That is not inherently inconsistent with class P: the platform can hold the record while a builder admin supplies or configures tenant-specific information. Discovery must confirm that split.

I reproduced `ENTITY_REGISTER.csv` and `M15_REGISTER_CHANGES.csv` byte-for-byte using the supplied generator and the unchanged `SYSTEMS_SURVEY.csv` from revision 4. The generator does, however, expect that survey file in its working directory; it is not in the revision 4.1 folder itself.

### 6\. MINOR — two remaining points

m1 — Incorrect 8-layer folder path.

The assessment points to `06_change_request_sources/APG_8_LAYER_DESIGN_BLUEPRINT_v0.1/`. The actual folder in the pack is `06_change_request_sources/8_layer_v0.1/`.

Fix: correct the path.

m2 — Revision 4.1 generator documentation and input.

The `build_entities.py` docstring's class legend lists B, C, I, D, X and V, but omits the newly introduced P class. The generator also expects `SYSTEMS_SURVEY.csv` in its current directory, whereas the supplied copy is in `rev4_registers/`.

Fix: add P to the legend and make the generator resolve the revision 4 survey file by path, or include the unchanged input alongside the revision 4.1 generator.

### 7\. Reproduction and boundaries

The draft 5 reproduction succeeded:

* `build_cia.py` regenerated the proposed-text table, impact table, dependent text and counts.

* `fill_v5.py` and `assemble.py` regenerated the assessment.

* The proposed-text CSV, RTM impact CSV, dependent text and Markdown assessment all matched the supplied files byte-for-byte.

* `python-docx` was available, and the supplied Word copy opened as a 37-page document. The relevant Word passages agree with the Markdown.

The counts also reconcile: 87 additions, 12 version-line changes, two reworded sentences, 1,887 impact rows and 1,410 distinct locked items.

The design-only boundary is intact. The assessment authorises no build, does not claim implementation or acceptance, and keeps Stage 2 unauthorised. The E77 changes, the one-person exception, the new severity design and the other proposed features remain future work under their own authorisations.

I have not re-audited every unchanged requirement in all 19 locked sections or independently rerun the four agents' semantic review of all 2,712 RTM rows. I checked the supplied row-level results, the residual 14 closures, the register contents and the specific locked clauses relevant to this confirmation.

### 8\. Final disposition

| Finding class | Count |
| ------------- | ----- |
| BLOCKING      | 0     |
| SHOULD FIX    | 4     |
| MINOR         | 2     |

Disposition: READY FOR THE OWNER'S FORMAL APPROVAL once the four SHOULD FIX and two MINOR corrections are made; no blocking issue remains, and no further GPT or agent review is warranted.

The one-person exception is now properly expressed as an owner-approved policy choice, not an accidental bypass. The remaining points are clarity, consistency and supporting-document maintenance—not grounds to restart the audit.
