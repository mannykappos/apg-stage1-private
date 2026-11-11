# APG data supply: decisions for the owner

Nov 12, 2026 · @Emmanuel

## How to use this document

These are the decisions needed to close two pieces of design work: the APG Data Readiness Change Request (revision 3), which lists the data APG needs, and the APG Data Supply System (blueprint amendment, draft 5), which designs how APG gets it. Each decision gives the question, the options, Claude's recommendation and the reason. The two documents themselves are the evidence; this is the short form.

**For GPT and Gemini:** please give your opinion on every decision in one pass. For each, say whether you agree with the recommendation, and if not, which option you would choose and why. Flag anything you think is missing from the list. Judge the decisions, not the wording, and do not add new features.

**What approving means.** These are approvals in principle. The blueprint's change process (Section 18 §6) requires a cascade impact assessment before formal approval, and no build starts before the Section 01 Discovery Exit Report and the owner's authorisation (Section 04 §20). Nothing here authorises a build.

| # | Decision | Claude recommends |
| --- | --- | --- |
| 1 | The design principle and the two guarantees | Approve |
| 2 | The data scope (99 entities plus N01) | Approve; developer entities optional |
| 3 | The architecture: one intake, many ways in | Approve |
| 4 | The release rule | Approve |
| 5 | Release A scope | The middle path |
| 6 | Phone site capture | Level 2, with an early discovery gate |
| 7 | Subcontractor claims | Promote, together with decision 12's back-to-back check |
| 8 | The cost-code map | Mandatory before cost-code figures; AI suggestion decided later |
| 9 | Default rule settings | Approve defaults and ranges at build time |
| 10 | Freshness values | Approve the proposed table as a starting point |
| 11 | Acceptance criteria and the route through change control | Approve PG-DS-AC-01 to 13; one change request |
| 12 | Reviewers' further ideas | Take two forward, one later, one after a legal check, decline one |

## A. Direction

### 1. The design principle and the two guarantees

**Question.** Adopt as APG's definition of "fail-proof on our end": every entity has an APG way to be supplied that does not depend on the builder's software (integrations only save effort), and two guarantees: no result is shown beyond its evidence, and every gap has a named way to fill it.

**Options.** Approve; approve with changes; reject.

**Recommendation: approve.** It is the owner's requirement, made testable. Integrations stay optional, so APG works at any split between the builder's systems and APG's own capture.

### 2. The data scope

**Question.** Approve the 99 entities in revision 3's register, plus N01 (detection-rule settings), which draft 5 found missing; the five developer entities as an optional extension.

**Options.** Approve all; approve without the developer entities; narrow the scope.

**Recommendation: approve, with the developer entities optional.** The 99 come from the locked blueprint; revision 3's register was checked by an independent agent audit, and its own GPT check is still to be run. The developer entities are outside the locked blueprint and need their own change.

### 3. The architecture

**Question.** One Section 04 intake with one set of controls; six ways to supply data in three levels (Level 1: import templates, document and email capture, entry screens, setup questions; Level 2: phone site capture; Level 3: integrations through AUIF), plus records APG calculates; every entity with a Level 1 way in; no detection rule or figure changed by a new way in.

**Options.** Approve; approve with changes.

**Recommendation: approve.** Both GPT and Gemini judged the architecture sound. One intake means one set of checks, so a fact is treated the same however it arrives, and a builder switching systems changes effort, not results.

## B. What gets built first

### 4. The release rule

**Question.** Release A is what today's insights read and need to run; release B is what lifts their known limits, each needing its own rule change before it helps; everything else waits for builder discovery.

**Options.** Approve; set a different order.

**Recommendation: approve.** It is mechanical and checkable from the input contracts, and it builds first what produces value first.

### 5. Release A scope

**Question.** How much does the first usable release include?

**Options.**

1. **Minimum:** one intake for every kind; real import (CSV and Excel, a mapping screen, templates checked on a real builder's files); setup; entry forms for setup and retention events only; quote readings keyed by one person and confirmed by a second; the M6 input contracts; readiness, the data checklist and nudges.
2. **Middle path:** the minimum, plus entry forms for the facts the first pilot's insights need (added progressively), document upload with person-keyed values confirmed by a second person, and the five market-insight supplements asked for only when a builder uses those insights.
3. **Full:** the minimum, plus entry forms for every small fact and finished document capture with real extraction (needs an extraction vendor, EDR-22, not yet chosen).

**Recommendation: the middle path.** The minimum assumes a builder can produce a file for everything, which many cannot. The full option depends on an unchosen vendor, and Gemini judged it too big for a first release; GPT kept it as the target but asked for staging. The middle path delivers value on the first pilot project and grows from there.

**Gates in every option.** Release A is not complete until the M6 input contracts are written, the intake migration has passed as its own milestone with today's results as the baseline, and the field-coverage report passes.

### 6. Phone site capture

**Question.** Revision 3 listed phone capture as a required feature. Draft 5 puts it at Level 2: built when discovery shows the need, because every site fact also has an entry form or template.

**Options.** Level 2 with an early discovery gate; required in release A.

**Recommendation: Level 2, with an early discovery gate.** It adds convenience, not coverage. GPT agreed, provided site needs are tested early; delays, defects and instructions entered later are marked as retrospective, and the insight is qualified.

### 7. Subcontractor claims

**Question.** Subcontractor claims, assessments and payments (E17 to E19) sit in "later" by the release rule, because no current insight reads them. Gemini flagged them as a main source of profit leakage. Promote them to the front of release B?

**Options.** Promote now; promote with the back-to-back claim check (decision 12); leave in "later".

**Recommendation: promote, together with the back-to-back check.** Collected alone, the data changes nothing until a rule reads it. Paired with the check, it targets one of the largest leakage points in commercial construction.

## C. Settings the builder needs

### 8. The cost-code map

**Question.** Make a builder-confirmed cost-code map mandatory before any figure that groups by cost code, with APG suggesting matches and the builder confirming each? Records with an unmapped code still come in and wait only for the figures that need the code.

**Options.** Mandatory as described; optional.

**Recommendation: mandatory as described.** Cost figures are only as good as the mapping. Whether the suggestion uses AI is decided when the step is designed; any learning stays within one builder's data.

### 9. Default rule settings

**Question.** Detection-rule thresholds and windows ship with defaults the owner approves, within allowed ranges; the builder's approver accepts them at onboarding and may adjust later. Two settings have no default and come from the builder (R04B's instruction types, R07's comparable pairs).

**Options.** Approve this approach; require every builder to set values.

**Recommendation: approve this approach.** Builders see results without tuning thresholds first. The actual default values are approved at build time.

### 10. Freshness values

**Question.** Set how old each kind of data may be before an insight using it is qualified (table at the end), or replace the values.

**Options.** Approve the table; change values.

**Recommendation: approve the table as a starting point**, to revisit with pilot data. Most values follow the builder's own reporting cycles.

## D. Governance

### 11. Acceptance criteria and the route through change control

**Question.** Approve acceptance criteria PG-DS-AC-01 to 13 for every way in; take revision 3 and the data supply design through Section 18's change process; give the change request its number in the owner's list and say how it relates to CR-07 (builder integrations).

**Options.** One change request or two; numbering.

**Recommendation: approve the criteria; one change request** covering both documents, because they are one design. It sets what data APG needs and its own capture; CR-07 builds the connectors.

### 12. Reviewers' further ideas

**Question.** Which of the ideas raised by the reviewers, outside this design, to take forward as their own change requests?

| Idea | Claude's view |
| --- | --- |
| Back-to-back claim check: compare each subcontractor claim with the matching client claim line | Take forward (high value; pairs with decision 7) |
| Adjudication evidence packs: export the full evidence trail for a disputed claim or variation | Take forward (good value, built on provenance the design keeps) |
| Learning cost-code map from the builder's own confirmed mappings | Later, within one builder's data only |
| Statutory declaration checks before payment | After a legal check (rules differ by state); APG flags, a person decides |
| One-tap approvals in messages without signing in | Decline (anyone with the link could approve); links to the form after sign-in are already in the design |
| Data retention and archiving after close-out | Confirm against the blueprint's security sections first, then a change request if needed |

**Recommendation:** take the first two forward now, the third later, the fourth after a legal check, decline the fifth, and check the sixth.

## Proposed freshness values (decision 10)

| Data | Good | Qualified after |
| --- | --- | --- |
| Variations and order amendments | 30 days | 60 days |
| Cost-to-complete forecast | the current month | one month-end missed |
| Budget revision | the current month | two month-ends |
| Supplier invoices and credits | the last month-end | two month-ends |
| Bank transactions | 7 days | 31 days |
| Facility statement | the last month | two months |
| Claims and payment schedules | the current claim period | one period missed |
| Programme | the last update | one monthly update missed |
| Timesheets | the last week | two weeks |
| Delays, defects, plant hire | weekly | monthly |
| Compliance evidence | before expiry | at expiry |
| Market and quote data | per Section 08 §7.1 | per Section 08 §7.1 |
