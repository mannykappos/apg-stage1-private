# APG M7: the recommendation, prioritisation and scenario engine (contract)

| Field | Value |
|---|---|
| Blueprint | Section 10 (Recommendations, Prioritisation & Scenario Engine) v1.0 LOCKED; Section 05 sections 10, 10.1, 11 and 13; Section 02 section 7; Section 06 sections 9 and 11. No locked text is changed. |
| Code | `apg/rec/`: `policy.py`, `engine.py`, `inputs.py`, `lifecycle.py`, `verify.py`, `demo_rec.py` (synthetic demonstration values), `golden_rec.py` (golden run) |
| Status | Builder-implemented and locally tested; no independent review has taken place. Not integrated with the Anchor Engine. Not production-ready. |
| Revision | APG-M7.1 (correction after the independent audit of M7): source freshness at submission, approval and start (F-64, F-65), section 8a; the policy-approval boundary (F-66), section 2a. APG-M7.2 (correction after the independent audit of M7.1): the check and the act commit together (F-68), section 8b. APG-M7.3 (correction after the independent audit of M7.2): the commit holds whole queries, so a record created during the act refuses it (F-69), section 8c, which replaces the second half of 8b. |

## 1. What it does

It turns governed findings (the M5 and M6 findings) into ranked, explained recommendations. People add what only people can know, and a person decides. A realised benefit is recorded only through a verification gate. APG carries out no action.

```
findings (M5/M6)  ->  rec.prioritise run (reproducible)  ->  recommendation records  ->  people: inputs, reviews, submit, approve/reject/defer/close
                                                                                       ->  people act outside APG  ->  completion with evidence  ->  verification gate
```

## 2. The policy (configuration with no default)

`rec_policy/<version>`. A version is immutable. It is approved only by a human `recommendation_policy_owner` who is not the proposer. A run under an unapproved policy says so.

| Field | What it decides | If missing |
|---|---|---|
| `eligibility.stale_after_days` | Evidence older than this, relative to the run date, routes the finding to investigation | Freshness cannot be judged, so the finding is routed to investigation (`FRESHNESS_NOT_CONFIGURED`) |
| `eligibility.min_strength_for_action` | The minimum evidence strength (weak, moderate or strong) for an action | No action is offered (`STRENGTH_RULE_NOT_CONFIGURED`) |
| `eligibility.due_soon_days` | When a dated condition counts as "soon" and a decision window as "closing" | Only overdue and later are distinguished |
| `categories` | The action category for each financial interpretation (prevent, correct, recover, optimise, negotiate, escalate, monitor) | The finding is routed to investigation (`CATEGORY_NOT_CONFIGURED`) |
| `mandatory_reviews` | Reviews (safety, quality, legal, contractual) required per finding family before an action | No review is required for that family |
| `approval_bands` | The role that approves, by the absolute potential gross amount. The lowest band starts at 0, and an unquantified amount needs the highest band | Nothing can be submitted (`no approval authority is configured`) |
| `rank_order` | The order of the ranking dimensions | The run stops (`RANK_ORDER_NOT_CONFIGURED`), because a ranking without a stated order would be unexplained |
| `scenario_required_above_cents` | From which amount a decision is material and needs a complete alternative | Every action needs an alternative |
| `verification.offset_components` | The hidden or offsetting cost components every verification must address | Nothing can be verified (`VERIFICATION_NOT_CONFIGURED`) |

## 2a. Who approves the policy (APG-M7.1, F-66)

- **Proposing.** `policy.store_policy` stores a proposed version. The proposer is the person storing it, taken from the verified context. A policy can never arrive with approvals, and a machine cannot propose one.
- **Approving.** `policy.approve_policy` is the only way to record an approval. The approver is taken from the verified context and must be a person holding the role recommendation_policy_owner, must not be the proposer, and approves a version once. It writes the approval and an audit event, `rec.policy_approved`.
- **Counting approvals at a run.** A run counts only the approvals that the audit log confirms. The confirmed approvers go into the run's parameters, so a replay gives the same answer. An approval written into the record by any other means does not count.
- **Unapproved policy.** Under an unapproved policy every recommendation is blocked from submission.
- **Store guard.** Restricting who may write the policy record kind and the audit log is the Engine's (EDR-34).

## 3. Eligibility before ranking (Section 10 section 3)

| Route | When | Ranked | Counted in totals |
|---|---|---|---|
| `action` | Confirmed (or with an action proposed), evidence at or above the minimum strength, no unresolved critical missing information, evidence current, a category configured, and not a data-integrity finding | yes | yes (one per overlap component) |
| `investigate` | Any of: not reviewed (detected, under review, reopened); weak evidence; missing information not assessed as non-critical; stale evidence; evidence dated after the run date; an unreadable date; a data-integrity finding; no category configured. Investigation can be the most valuable next action, so these lines are ranked with the actions and the route is shown on every line | yes | yes |
| `in_hand` | The finding's own action is already approved or in progress (M5): tracked, not recommended again | no | yes |
| `close` | The finding is resolved, or an opportunity's decision window has closed (loss of actionability). A person records the closure | no | no |
| `excluded` | The finding is dismissed or superseded. It is listed with the reason | no | no |

Missing information is treated as **critical** until a constraint reviewer records, with a reason, that an item is not critical (`inputs.record_evidence_assessment`).

## 4. The factors, kept apart (Section 10 section 4)

Every recommendation reports each factor separately. There is no combined score.

| Dimension | Value |
|---|---|
| magnitude | The potential gross amount of the exposure or opportunity, with its label (figure, record or estimate). It is never called a benefit |
| urgency | How soon the dated condition falls due: overdue, soon, later, or not dated. "Not dated" means the data names no date; it does not mean "not urgent" |
| confidence | Evidence strength, the critical missing items, alternative explanations, financial status (authoritative, qualified or unquantified), freshness, and whether the detection policy was unapproved |
| time sensitivity | Whether a decision window closes, and its state: open, closing, passed (an exposure that is overdue), expired (an opportunity, routed to close), or none |
| actionability | Whether an authorised person can act now, and every reason why not |
| implementation cost | Every incremental cost a person entered, each with its basis, or "not estimated" |
| expected benefit | What a person expects the action to achieve, with its basis |
| net benefit | Expected benefit minus incremental costs, labelled an estimate. It is stated only when both have been entered |
| dependencies, risk and constraints | Entered dependencies, approval and reviews needed, overlapping findings, consequential-action warnings, and data limits |

**Ranking.** The ranking is lexicographic in the policy's `rank_order`. Each line after the first states the line above it, the first dimension in which the two differ, and both values. A full tie is broken by finding id, and the line says that this is a stated tie-breaker, not a judgement.

## 5. Money (Section 10 section 6)

- Potential gross, expected benefit, incremental costs, estimated net benefit, approved action and verified realised benefit are separate fields.
- Inside one overlap component, only the recommendation with the largest potential gross is counted in the totals. An overlap component uses the M5 rule: the same overlap group, a shared stored record, or a person's `financial_overlap` link.
- Totals are kept per financial interpretation and are never added across interpretations. An unquantified amount is listed; it is not counted as zero.

## 6. Constraints a high rank cannot bypass (PG-RS-AC-05, 08)

A recommendation can be submitted for approval only when all of these hold:

- its route is `action`;
- every mandatory review is recorded and cleared;
- an approval authority applies;
- every incremental cost is estimated;
- the kind of action is stated;
- for a material decision, at least one complete alternative is on record;
- the run's policy is approved by a policy owner, as the audit log confirms (M7.1);
- the recommendation still matches its sources (M7.1, section 8a), and still does when the act is recorded (M7.2 and M7.3, sections 8b and 8c).

The approval call checks the same gate again.

Consequential kinds are flagged on the line. They are purchase order, contract, claim, variation, supplier change, material substitution and other commitment. APG never carries any of them out: `lifecycle.execute` refuses, always.

## 7. Scenarios (Section 10 sections 7 and 7.1)

An alternative is complete only when it states all nine Section 10 section 7 items:

- a reference baseline: a stored forecast calculation, `repro_record/<run key>`, checked when the alternative is written;
- the proposed action and the affected activities or resources;
- its financial effects and timing;
- its incremental costs;
- dependencies and approvals;
- schedule, quality, safety and operations effects;
- assumptions, uncertainty and evidence gaps;
- the conditions that would invalidate it;
- how its outcome will be verified.

An engine-generated "no action" reference is always shown, with the consequence of delay where the data supports one, and "not supportable from the data" otherwise.

No recommendation module adopts, promotes or files a forecast or a forecast slot. Every alternative carries `changes_authoritative_forecast: False`.

## 8. The lifecycle (Section 10 section 9)

| From | To | Who |
|---|---|---|
| generated | awaiting_evidence, awaiting_approval (gated), deferred, closed_without_implementation | recommendation_owner |
| awaiting_evidence | generated, deferred, closed_without_implementation | recommendation_owner |
| awaiting_approval | approved (with the token), rejected | the band's approval role. It may not be the submitter or the author of the inputs |
| awaiting_approval | generated (withdrawn) | recommendation_owner |
| deferred | generated, closed_without_implementation | recommendation_owner. The service also ends a deferral when its date comes |
| rejected | closed_without_implementation | recommendation_owner |
| approved | in_progress (approval still in force), closed_without_implementation | recommendation_owner |
| in_progress | completed_pending_verification (stored implementation evidence), closed_without_implementation | recommendation_owner |
| completed_pending_verification | verified_outcome | benefit_verifier, through `verify.verify` only |

Every act is a person's act. A machine or AI actor is refused.

**Approval binding.** An approval is bound to the recommendation version, its digest and the submission reference (`approval_token`). It follows the lessons of the M6.1 to M6.5 corrections for findings.

**What a material change does.** A material change gives the recommendation a new version (`engine.state_digest` covers everything the approver is shown). The new version ends a submission or an approval and returns the recommendation to `generated`. In `in_progress`, the approval is ended and the event is recorded. History is append-only, and every write is audited.

## 8a. Source freshness (APG-M7.1, F-64 and F-65)

A recommendation record is a snapshot of the run that produced its current version. Submission, approval and the start of work each first call `lifecycle.source_check`. The act is refused (`SOURCE_CHANGED`) unless both of these hold:

- the finding, every finding of its overlap component, the recommendation inputs (costs, benefit, alternatives, reviews, evidence assessments) and the policy are each at exactly the revision the run pinned. A record that was absent must still be absent;
- a run made now, in memory, with the same date and policy, gives this recommendation the same state digest. This also catches a new finding joining the overlap component, or a policy approval that is no longer confirmed.

Anything that cannot be checked counts as a change. After a fresh run, a version whose content is unchanged keeps its submission or approval. A changed version ends them, as before. Completion and verification are not source-checked: they record what happened after people started (I-111).

## 8b. The check and the act commit together (APG-M7.2, F-68)

In M7.1 the check and the write of the recommendation were two store operations, so a change that landed between them was not seen. Now `lifecycle._commit_checked` records submission, approval and the start of work in one atomic store batch. The batch holds:

- **a guard on every stored record the check read**: the run record, the finding, every finding and set of recommendation inputs the recomputation read, and the policy. Each guard is held at the revision the check saw. A guard writes nothing, because the store appends no revision when a payload equals the latest one, and it refuses the whole batch when the expected revision is no longer the latest;
- **the recommendation write itself**, at its own expected revision.

If anything changed after the check, the batch fails and nothing is recorded:

- `SOURCE_CHANGED` when the recommendation no longer matches its sources, so the engine must run again;
- `CONCURRENT_CHANGE` when its sources still match and only another record or the recommendation itself changed, so trying again is enough (I-114).

A record whose stored payload the store would rewrite on screening cannot be held this way, and the act is refused (`SOURCE_GUARD_UNAVAILABLE`).

The store contract cannot hold a record as absent, or a query as unchanged, without writing. So a record created during the act, such as a new overlapping finding, is caught by running the check again once the act is recorded. If the check now fails, the act is reversed at once: an append-only revision with an `act_reversed` history event and the audit event `rec.act_reversed`. The act is then refused. If the recommendation changed again before the reversal could be written, the caller gets `CONCURRENT_CHANGE` and the audit event `rec.reversal_failed`.

For that moment the stored record shows the act. Every act that could follow from it is itself checked and would be refused (I-115). Absence and query guards are the Engine's to provide (EDR-35). The reference in-memory store is single-process and holds no lock. Atomicity against truly concurrent callers is the store's, as EDR-02 already requires.

## 8c. The commit holds whole queries (APG-M7.3, F-69)

M7.2 could hold a record that existed, but not a record that did not exist yet. A new overlapping finding created during the act was caught only by a second check after the commit, and the act was reversed. M7.3 closes that at the store.

- **The store contract.** `RecordStorePort.atomic` now accepts guards (`ports.Guard`) alongside its writes:
  - `Guard('revision', kind, key, n)` holds a record at exactly revision n, where 0 means absent;
  - `Guard('query', kind, where, entries)` holds a whole query at exactly the set of (key, revision) it returned, so no record may be added, changed or removed.

  All guards and writes in a batch are one indivisible step. A guard writes nothing. If any guard fails, nothing is applied and `ConflictError` is raised. The reference store implements this under a lock. The contract is `apg/contracts/record_store_guard_contract.py` (RG-01 to RG-08), and an Engine store must pass it (EDR-36).
- **The lifecycle.** `source_check` returns a guard for everything it read:
  - a whole-query guard for the findings and for the recommendation inputs (the recomputation reads all of them);
  - a revision guard for the run, the policy and every record it read by key.

  `_commit_checked` writes the act in one batch with those guards. A record added, changed or removed before the commit fails it, and nothing is recorded: `SOURCE_CHANGED` if the recommendation no longer matches, otherwise `CONCURRENT_CHANGE`.
- **What goes.** The check after the commit, the reversal and the events `rec.act_reversed` and `rec.reversal_failed` are removed (I-115 no longer applies).
- **When an act takes effect (I-116).** At its commit, on exactly the sources it was checked against. A record committed after that is a later change, ordered after the act in the store. That includes a record created before the call returns. It is handled like any later change: the next checked act is refused, and the next run ends a submission or approval that no longer matches.

## 9. The verification gate (Section 05 section 10.1)

`verify.verify` refuses unless all of these hold:

- the recommendation is `completed_pending_verification`;
- the verifier is a person with the role `benefit_verifier` who did not write, submit, approve, start or complete it;
- the baseline is an M4 forecast calculation that still replays and that a forecast owner adopted (or explicitly promoted) no later than the time the action was started;
- the implementation evidence named at completion still exists unchanged;
- every policy offset component is addressed, either with an amount and basis or as not applicable with a reason.

The realised figure (observed benefit minus offsets, with the variance against the approved net benefit) is computed by the reproducible formula `rec.realised`. It may be negative. Nothing else in APG records a realised benefit: `findings.claim_realised` and `opportunity.claim_saving` still refuse.

## 10. Reproducibility (Section 05 section 13; PG-RS-AC-12)

`rec.prioritise` v1 pins every finding, every recommendation input and the policy at the revision read. Its code hash covers the rule modules. Every recommendation version records the run that produced it. `lifecycle.reconstruct(rid, version)` replays that run and returns the entry as computed, with whether it matches the recorded digest.

## 11. Acceptance criteria and where they are tested

| Criterion | Tests |
|---|---|
| PG-RS-AC-01 factors visible and explainable | test_rec_ranking (TestDimensions, TestOrder) |
| PG-RS-AC-02 magnitude, urgency and confidence distinct | test_rec_ranking.test_magnitude_urgency_and_confidence_are_distinct_values, test_a_large_weak_estimate_does_not_outrank... |
| PG-RS-AC-03 weak or stale evidence qualified | test_rec_eligibility (weak, stale, missing, unreadable date, evidence after run date) |
| PG-RS-AC-04 overlap does not inflate value | test_rec_money.TestOverlap |
| PG-RS-AC-05 constraints cannot be bypassed by rank | test_rec_constraints.TestBlocked |
| PG-RS-AC-06 incremental costs and trade-offs | test_rec_money.TestNetBenefit; test_rec_constraints (no costs, no submission) |
| PG-RS-AC-07 scenarios cannot change the forecast | test_rec_isolation |
| PG-RS-AC-08 human approval for consequential actions | test_rec_lifecycle.TestApproval; test_rec_constraints (kind of action) |
| PG-RS-AC-09 approval and execution distinct | test_rec_lifecycle.test_the_full_path_keeps_recommendation_approval_and_outcome_distinct; execute refusal |
| PG-RS-AC-10 realised benefits need verification | test_rec_verify |
| PG-RS-AC-11 rejected, deferred and unsuccessful auditable | test_rec_lifecycle.TestAuditability |
| PG-RS-AC-12 historical rankings reconstructable | test_rec_repro |
| PG-RS-AC-13 conflicting priorities, expired opportunities, missing evidence, overlapping benefits, blocked actions | test_rec_ranking (conflicting priorities); test_rec_eligibility (expired, missing); test_rec_money (overlap); test_rec_constraints (blocked) |
| PG-RS-AC-14 no claim without reproducible evidence | every result here is builder-run; tools/run_m7_all.py and tools/run_regression_m7.py reproduce it |

## 12. What is not built, and what depends on others

- **Screens and API.** There is no screen or API for any of these calls (M9 and M10).
- **The Anchor Engine.** The mapping to the Anchor workflow, Governor and audit contracts, and the per-project role directory for approval roles, are the Engine's (EDR-33).
- **Policy values.** No real policy value is chosen. The demonstration policy is synthetic, and the product owner sets the real values.
- **Engine #17 and RFC-01.** Nothing of Engine #17 is built. RFC-01 is still PROPOSED and unnumbered.
- **Builder readings.** The builder's readings of the blueprint are interpretations I-99 to I-109, retained for review and not approved.
