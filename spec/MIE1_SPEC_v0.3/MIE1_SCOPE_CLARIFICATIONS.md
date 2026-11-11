# MIE-1 Scope Clarifications

Status: builder-made, not independently reviewed. Revision v0.3 (2026-10-17), additive; the delivered v0.1 and v0.2 packages are preserved unchanged. These sit beside the specification (MIE1_SPEC.md) and the register MIE1_SCOPE_CLARIFICATIONS.csv (SC-01..SC-19).

## What this milestone delivers
A specification and design package: the specification, these clarifications, the draft Section 08 change request, requirements and acceptance registers, traceability, limitations, and package-integrity evidence. Then it STOPS for independent review. No implementation code exists. The test families and sabotage catalogue are plans (SC-12).

## What it does not do
No code of any kind, including reference implementations and tests. No M7 or profit improvement engine. No Engine #17, E1-E5, M9 or AUIF implementation. No Anchor Engine handoff. No deployment, live feed, credential, vendor or licence. No luxury-specific functionality or real luxury data. No connection of any market signal to an APG finding or recommendation.

## What stays unchanged
Locked Sections 00-18, CR-09, the RTM (and the RTM v2.2 candidate), CR-11 (PROPOSED), CR-01 rev 3 (proposed), M6, M8.3 and every preserved release (hashes in MIE1_BASELINES.csv). DEC-A1-1..8, CR-02 A1..A13 and B7 are not touched.

## Terms used
- Pack: a data document the core validates; no executable content.
- Signal: an observed fact about evidence; never a prediction.
- Timing assessment: an advisory record from a pack's decision table; it commits nothing and a human decides.
- Universal: no domain vocabulary in the core; any conforming pack runs. It does not mean all markets behave alike.
- Builder responsibility versus Anchor Engine responsibility: the builder specifies (and, once separately authorised, builds) the core, packs, ports, reference implementations and contract tests. Real feeds and their licences, persistent storage, scheduling, secrets, deployment, notification delivery and hosting remain the Anchor Engine team's, and nothing here assumes how they are done.

## What the reviewer is asked to decide or confirm
1. Whether the specification is complete and consistent enough to authorise implementation.
2. The dispositions recorded in MIE1_OQ_DISPOSITIONS.csv for the nine specification-approval questions (MIE-OQ-05, -06, -10, -11, -14, -16, -18, -19, -20). Questions owned by the reviewer show the reviewer confirmation required; questions owned by the product owner show the product-owner decision still required. The builder has decided none of them.
3. Whether the corrected audit interface (MIE-R-60, -61, -62), the signal-influence safeguard as corrected in v0.3 for the precedence loophole and its result contract (MIE-R-63, MIE-R-69, including the builder-identified clarification that NO_RULE_MATCHED and NO_TABLE results have class NONE and that downstream NOT_ASSESSED rules are owner-labelled), the value-domain and movement mathematics (MIE-R-64, -65) and the observation-feed flow (MIE-R-66) are acceptable, including the structural definition of signal influence (MIE-OQ-26).
4. Whether the sabotage catalogue and test families are adequate, and whether a stricter neutrality check than a deny-list is wanted.
The product owner is asked separately to decide the Section 08 change request (Option A, Option B or neither: MIE-OQ-12) and to name the policy owner for the APG pack's parameters (MIE-OQ-03). Neither decision blocks the specification review.

## Implementation blockers (MIE-R-70)
Implementation cannot be authorised until three blockers are cleared and independently reviewed: BLK-01 audit append and state commit atomicity (an explicit design decision is required; the builder makes none), BLK-02 the M6 mapping (not derived), BLK-03 the Section 08 cascade impact assessment (unfinished). They are in MIE1_IMPLEMENTATION_BLOCKERS.csv. The product owner's Section 08 decision is separate and also outstanding. No revision is closed or implementation-ready.
