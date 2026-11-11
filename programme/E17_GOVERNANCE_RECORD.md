# Engine #17 governance record (received 2026-10-15)

| Field | Value |
|---|---|
| Status | **A record of directions received. Not an approval of RFC-01, not a numbering of it, not an adoption of any baseline.** |
| Source | The auditor's response to the Phase 0 report, relayed by the product owner on 2026-10-15 |
| Recorded by | Builder (Claude), in this file and in `programme/E17_GOVERNANCE_REGISTER.csv` (G-01 to G-12) |
| Locked baseline | Sections 00–18 v1.0, archive SHA-256 `487becabdf47796800937d13a706a19b63b7b8230ecc5354b2f01a647ae5d960`. **Unchanged.** CR-09, the RTM, CR-01 rev. 3, CR-02, CR-11 and every earlier package are untouched. |
| Still waiting on the product owner | RFC-01 approval and number; DEC-A1-1 to DEC-A1-8; DEC-MIE-01; B7 |

## 1. What was directed

| # | Direction | Where it is recorded | What the builder did |
|---|---|---|---|
| 1 | Fold Engine #17 into M7 Recommendations as a controlled extension. RFC-01 must be formally approved and numbered before implementation under that authority. | G-01 | Nothing under that authority has been built. RFC-01 stays PROPOSED and unnumbered. M7 has not started. |
| 2 | Do not invent an Engine #1–#18 map; the pack's numbers are provisional labels. | G-02 | No map made. |
| 3 | Baselines are versioned source records with canonical hashes and explicit human-approved adoption, defined per opportunity type. The last paid rate is never an approved baseline by default. | G-03 to G-07 | Recorded. Not implemented. |
| 4 | Section 05 §10 governs benefit states; M5's statuses govern finding review; no third lifecycle. | G-08 | The correction adds no status and does not change the table of allowed transitions. |
| 5 | Cost of capital, overhead rates and offset categories stay configuration-only until approved; a missing required value blocks a definitive net-benefit claim. | G-09 | Nothing configured. |
| 6 | The M5 approval-defect correction is authorised, with six controls. | G-10, F-52 | Done in APG-M6.1; see `CHANGE_RECORD_APG-M6.1.md`. |

## 2. Proposed baseline rules by vector (PROPOSED)

**PROPOSED** by the auditor, subject to the relevant owners approving the underlying records. **None is implemented, and no owner has approved a record.**

| Vector | Baseline to compare against | Approval needed |
|---|---|---|
| V1 value engineering | Current approved specification, scope, design revision and the commercial estimate or comparable quote for the original solution | Technical authority approves equivalence; commercial authority approves the cost comparison |
| V2 quantity and waste | Approved takeoff or BOQ and drawing revision, reconciled with orders, deliveries and verified installed quantities | Project commercial or quantity-surveying authority; technical review where revisions affect scope |
| V3 payment terms | Existing contractual payment terms, approved funding or cost-of-capital assumptions and the cash-flow position | Commercial authority approves terms; the finance owner approves the financial assumptions |
| V4 portfolio aggregation | Compatible, approved demand that remains genuinely uncommitted, with specification, quantity, delivery window and project constraints recorded | Each affected project's commercial authority, plus the delegated procurement authority for a portfolio purchase |

General rules that go with them: a baseline is versioned and immutable once adopted; a material change leads to recalculation, suspension, supersession or expiry and never changes the basis of an existing opportunity silently; each approval records who, when, and exactly which version and hash.

**What the builder notes about the code as it stands.** M6 holds quotes, orders, deliveries, the specification register and demand, so parts of V1, V3 and V4 can be compared against it. It holds no takeoff, no BOQ, no verified installed quantity (V2), no funding assumption and no cash-flow position (V3). The "last paid" reference M6 shows is a reference for comparison only. It is not a baseline and the code does not call it one.

## 3. What is blocked, and by whom

| To do | Needs | From |
|---|---|---|
| Any Engine #17 implementation beyond the correction | RFC-01 approved and numbered, with the annex below attached | Product owner |
| Versioned-baseline foundations | The per-vector rules above confirmed; the owner of each baseline named | Product owner; baseline owners |
| Any definitive net-benefit figure | Cost of capital, overhead rates, offset categories approved and configured | Finance owner |
| Cross-references to other engines | A mapping, if one is wanted | Blueprint author or product owner |
| Value-realisation work that depends on approvals | The auditor's independent verification of APG-M6.1 | Auditor |

## 4. Draft annex for RFC-01 (for the product owner to number and approve, or amend)

This is draft text. It becomes part of anything only if the product owner chooses to approve it. The builder has not numbered it.

**RFC-01 Annex A (draft): Engine #17, four-vector value realisation, as a controlled extension of M7 Recommendations**

1. **Scope.** Opportunity qualification, the offset-cost completeness gate, versioned baselines, re-evaluation on material change (recalculated, suspended for review, superseded, expired) and the link to the realised-benefit gate, all built once inside M7. Four vectors: V1 value engineering, V2 quantity and waste, V3 payment-term optimisation, V4 portfolio aggregation.
2. **Out of scope.** A separate engine, a separate lifecycle, any change to a locked section, CR-09 or the RTM, any invented rate or threshold, any execution of an action or movement of money, and anything that needs the Anchor Engine (those go to the handoff register).
3. **Lifecycles.** Benefit states: Section 05 §10. Finding review: the M5 statuses. No third lifecycle.
4. **Baselines.** As in section 2 of this record, once the product owner confirms them and the owners approve the records.
5. **Finance assumptions.** Configuration only, approved by the finance owner. A missing required value blocks a definitive net-benefit claim.
6. **Prerequisite already done.** The approval-binding correction (F-52, APG-M6.1), awaiting the auditor's independent verification.
7. **Navigation.** The pack's Engine #1–#18 labels are provisional until a mapping is approved.
8. **Evidence levels.** Every result is reported at one of the five levels in RFC-01 (proposed design, implemented code, locally tested, independently verified, production accepted). The builder's work reaches "locally tested" at most.
9. **Acceptance gates.** The 27 gates E17-A01 to E17-A27 and 39 negative cases of the pack, with independent review of each stage (E1–E5) before the next starts.
10. **Approvals required.** Product owner (RFC-01 and its number); each baseline owner; the finance owner; the auditor (independent review). **None has happened.**

## 5. What this record does not do

It does not approve or number RFC-01. It does not adopt a baseline, configure a finance assumption, settle an open decision or build any part of Engine #17. It is a record of what was said and of what the builder did and did not do in response.
