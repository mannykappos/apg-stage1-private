# RFC-01 — Latent Risk & Intervention Engine

| Field | Value |
|---|---|
| Status | **PROPOSED. Not approved. Not yet a numbered change request.** It has not been through independent review, G1 review or product-owner approval. |
| Source | Architecture directive from the product owner, received in the APG project conversation on 2026-10-14 (21:13 AEDT) |
| Recorded by | Builder (Claude), in `programme/RFC_REGISTER.csv` and this file, as part of the M6 delivery |
| Locked baseline | Sections 00–18 v1.0, archive SHA-256 `487becabdf47796800937d13a706a19b63b7b8230ecc5354b2f01a647ae5d960`. **Unchanged.** Nothing in this RFC edits a locked section, CR-09 (including its P4 change register), the RTM, any historical package or any hash. |
| Other proposals untouched | CR-01 rev. 3 is still proposed; CR-02 is still proposed; CR-11 is still proposed; RTM v2.2 is still a candidate; B7 still waits for the product owner. |

## 1. What the RFC proposes

APG is to become a cross-domain financial-risk intelligence and intervention engine for construction businesses: identify emerging threats to margin before avoidable cost is committed, connect evidence across systems, calculate exposure with deterministic rules, recommend an actionable intervention, and verify the financial outcome. The directive names **six strategic capabilities** and **seven governing principles** and plans an architectural milestone it calls **M7 — Latent Risk and Intervention Engine**, built on tested M6 interfaces.

The directive tells the Builder to proceed with M6 under the existing milestone process, to supply sound inputs and interfaces for the later engine, **not** to deliver M7 prematurely, and not to treat the directive as permission to bypass change control, alter the locked baseline or invent unresolved policies.

## 2. The five evidence levels used in this RFC

Kept distinct everywhere in the programme registers; nothing below moves up a level without the evidence for that level.

| Level | Meaning in this RFC |
|---|---|
| 1. Proposed design | Written down, nobody has built it |
| 2. Implemented code | Code exists in this package |
| 3. Locally tested | The Builder's own tests, oracle, corpus and mutation run pass on **synthetic** data. Wording: "builder-implemented and locally tested, not independently reviewed" |
| 4. Independently verified | A reviewer other than the Builder reproduced the result. **None of the M6 results has reached this level.** |
| 5. Production accepted | Demonstrated on real construction projects and accepted by the product owner. **Nothing has reached this level.** |

## 3. Where each of the six capabilities stands today (against the actual files)

| # | Capability | Level reached | What exists | What does not |
|---|---|---|---|---|
| 1 | Latent risk chain engine | Design only for the chain itself; building blocks at level 3 | M5 signals (rule, scope, subject, evidence pins, separate severity, urgency and confidence), finding lifecycle, overlap components built from shared evidence and groups. **M6 adds `apg-event-1` hook fields** (observation time, effective time, source provenance, project, material, supplier) on procurement conditions | No relationship store, no multi-event detection, no chain scoring, no intervention deadline across domains. Section 06 specifies independent rules; chains appear only in this RFC |
| 2 | Unearned margin and physical progress | Not implemented | M5 labour-output rule (hours per unit at package level); M6 delivery dockets with delivered and accepted quantities | No progress claims, inspections, payment-condition data or verified/reported/disputed progress states. Labour hours and deliveries are **not** proof of completion (CR-04 and CR-05 are not started) |
| 3 | Contractual time-bar and notice protection | Not implemented | M5 R04 and R04B: unresolved variations and client instructions with no variation, from notice dates and a configured workflow period | No contract-clause library, triggering events, notice requirements or substantiation checks. Needs CR-06 (rule packs) and **qualified legal review**. No clause is invented here |
| 4 | Landed cost and procurement intelligence | **Level 3 (M6)** | Comparability gate, landed cost, freshness, buy-now / wait / stage / negotiate scenarios, over-ordering, supplier performance, international safeguards, portfolio purchasing, signals MP01–MP10 and MPD1 | Real quotes, real market data, real extraction and a price forecast. No provider is connected or named. The extractor and market feed are test doubles |
| 5 | Cost of capital and trapped cash | Partial, level 3 (M4 and M5) | M4 retention and security carrying cost (policy-driven); M5 R05 retention release date passed | Bank-guarantee fees, security-reduction logic, financing-rate sources and the carrying-cost policy (CR-02) are open; no recommendation logic |
| 6 | Closed-loop intervention efficacy | Partial, level 3 (M5) | Human-only finding lifecycle, action proposal and approval with separation of duties, `claim_realised` refuses | Intervention cost, actual outcome, counterfactual baseline and verified net benefit. M6 `claim_saving` refuses too. The realised-savings gate is the existing M7 row ("Recommendations") |

## 4. How the governing principles are met so far (M6)

| Principle | Where it shows in M6 | Limit |
|---|---|---|
| AI assists, deterministic controls govern | Extraction output is always `unverified`; every number in a ranking or scenario is computed by explicit code; a person verifies readings | The extractor is a text stand-in; no model was run on a real document |
| Unknown means unknown | Missing parameters stop a rule (`not_configured`); unavailable data is "unavailable"; incomplete landed cost is flagged, never zero | — |
| Evidence and provenance are mandatory | Every signal and scenario names source records, policy versions, assumptions and limits; formulas are pinned and replayable | Tenant-run pins name identifiers of unauthorised projects' orders (finding F-39) |
| Reproducible | Four stored runs replay exactly; the code hash is part of the record | — |
| Tenant isolation | zero_two reuses identifiers and sees nothing of zero_one | Engine-level enforcement is EDR work |
| Actionable | Each signal states the consequence, the deadline where it exists, the evidence and the next check | Alert prioritisation across domains is M7 |
| No autonomous consequential action | Every ranking and scenario says a person must approve; nothing purchases, commits or notifies a supplier | — |

## 5. Scope proposed for M6 and for the later engine

**M6 (authorised, existing milestone process, delivered with this RFC record):** everything in section 3 row 4, plus: currency, tax and unit normalisation with explicit failures; quote validity, lead time and required-on-site dates; stale-data handling; reproducible calculation records; the `apg-event-1` event fields; tests for missing data, conflicting quotes, duplicates, currency errors, changed prices, delivery changes and misleading recommendations (78-case corpus, 24 port-contract cases and 25 faulty implementations).

**Later engine (RFC-01 "M7"), planned only, NOT started and NOT delivered:** time-aware cross-domain event relationships; multi-signal risk-chain detection; exposure and scenario calculation across domains; progress and unearned-margin reconciliation; time-bar monitoring; cost-of-capital analysis; intervention lifecycle and efficacy verification; alert prioritisation and repeat-alert control.

## 6. Affected components and dependencies

* **New in this RFC's M7 (not built):** a relationship/event store (Engine, EDR-30 described in M6), a chain-detection layer on top of `apg-event-1` events, an intervention-outcome record, a counterfactual-baseline method.
* **Reused unchanged:** signal contract, finding lifecycle, noise control, repro formulas, tenancy, audit chain.
* **Depends on:** the Anchor Engine (storage, scheduling, permission model, EDR-24 scalable reads, EDR-29 project authorisation, EDR-30 event store); CR-04 (margin fade, EVM, WIP — Section 19), CR-05 (site-to-claim capture — Section 24), CR-06 (rule packs — Section 22; legal review), CR-10 (alerts, Verified Profit Ledger — Section 20), CR-03 (Builder Profit Clock — Section 23), CR-07 (integrations — Section 21), CR-02 (financial policies), and pilot data from builders (CR-08).

## 7. Conflicts with locked and proposed material (reported, not resolved)

1. **Programme numbering.** The programme milestone table (not part of the locked sections) names M7 "Recommendations" (CAP-27 to CAP-30: eligibility, prioritisation, scenario isolation, realised-savings gate). The RFC names its planned milestone M7 "Latent Risk and Intervention Engine". Both cannot be M7. The M7 row is **not edited**; the product owner and auditor decide whether the RFC milestone is a renumbering, an insertion or a later milestone.
2. **Sections 19, 20, 21, 22, 23 and 24 are reserved** in the CR-09 change register (CR-01 A1, proposed) for CR-04, CR-10, CR-07, CR-06, CR-03 and CR-05. Capabilities 1, 2 and 6 overlap the reserved Sections 19, 23 and 24 and 20 (CR-04, CR-03, CR-05, CR-10), and Capability 3 overlaps the reserved Section 22 (CR-06). The RFC therefore cannot create sections without those CRs and CR-01. No section numbers are assigned here.
3. **Locked Section 12 (cash flow, retentions and security) and Section 10 (recommendations)** already specify parts of Capabilities 5 and 6. The RFC does not amend them.
4. **Locked Section 06** specifies independent detection rules, not chains. A chain engine adds a layer; whether it needs a Section 06 amendment is for the blueprint author.
5. **Locked Section 08** matches Capability 4; M6 implements it without change.
6. The directive's phrase "detect at least 72 hours before a cost commitment, mitigate for $2,000 a $10,000 loss" is a **pilot test target**. It is not in any locked section, is not hard-coded anywhere in this package, and is not a requirement the code can claim to meet.

## 8. Acceptance criteria proposed (all unverified at levels 4 and 5)

* Ultimate: on real construction projects, APG identifies material cross-domain threats earlier than the builder's existing process, with reliable evidence and an actionable intervention, and measures the financial outcome defensibly. Target scenario (test target only): detection at least 72 hours before a relevant commitment, followed by an effective $2,000 mitigation of a substantiated $10,000 loss.
* For the later engine (to be refined at its own milestone): every chain names its source events, times, relationship basis and missing information; no chain is reported as certain; exposure is never counted as realised loss; an intervention counts as a benefit only with a recorded cost, a recorded outcome and an independently supported counterfactual.
* For M6 (this delivery): see the M6 documents; the acceptance wording is "no definitive recommendation passes the comparability or freshness gates when it should not". Evidence is at level 3 only.

## 9. Unresolved decisions (none is made here)

* Whether, where and in what number the RFC becomes a change request, and which sections it creates or amends (blueprint author, after CR-01).
* How the RFC milestone relates to the existing M7 row.
* Contractual rule sources for Capability 3 and the qualified legal reviewer.
* The counterfactual baseline method and independence rule for Capability 6.
* The relationship model: which relations are asserted by a person, which are proposed by a model, and the evidence a proposed relation needs.
* Product-owner decisions already open and unchanged: DEC-A1-1 to DEC-A1-8, DEC-MIE-01, CR-02 A1 to A13 (in particular the grouping key DEC-A1-8, the carrying-cost policy and the revenue-recognition policy).
* Whether a ranking built from one supplier's own offers may ever be definitive (raised in M6, finding F-45).

## 10. Approvals required before anything in this RFC changes the baseline

Product-owner approval; independent review of the RFC (not by the Builder); G1 review; assignment of a CR number and owner in the CR-09 change register by the register maintainer; CR-01 approval where reserved sections are involved; qualified legal review for contractual content; and, for any pilot claim, access to builders and an agreed data-handling basis (CR-08). **None of these has happened.**

## 11. What this record does not say

It does not say that any capability other than Capability 4 is implemented at any level; that Capability 4 works on real data; that the RFC is approved or scheduled; that the 72-hour or $2,000/$10,000 figures have been or can be met; that a market-data provider exists; or that APG is ready for production.
