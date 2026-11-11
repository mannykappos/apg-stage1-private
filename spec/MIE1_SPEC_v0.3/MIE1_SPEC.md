# MIE-1 — Universal Market Intelligence Engine: Core and Pack Specification (revision v0.3)

Status: SPECIFICATION AND DESIGN ONLY. Builder-made. NOT independently reviewed. NOT implemented. This document specifies required behaviour; it is not evidence that any code, feed, pack or integration exists, runs or passes.
Date: 2026-10-17 (revision v0.3; the delivered v0.1 of 2026-10-16 and v0.2 of 2026-10-17 are preserved unchanged). Product owner: Emmanuel. Independent reviewer: the auditor. Builder: Claude.
Authority: Consolidated Authorisation, Workstream B (RUL-MIE-01..09) the instruction of 2026-10-17 that returned the first independent audit findings (RUL-MIE-10) and the instruction of 2026-10-17 07:10 Sydney that returned the second (RUL-MIE-11), in MIE1_RULINGS.csv.
Stopping point: this package is returned for independent review. STOP. Neither this revision nor the delivered v0.1 and v0.2 packages is declared closed or implementation-ready. No implementation code is written or authorised until the specification has been reviewed, the explicit blockers BLK-01..BLK-03 (section 16.1) are cleared, and the product owner separately authorises implementation.

---

## 0. What this revision (v0.3) changes

The independent review of v0.2 reproduced its manifest, the 43/43 checker and the 47/47 tamper results and substantially accepted the six earlier corrections, but did not approve it for implementation: it returned one further finding, a precedence loophole in the signal-influence safeguard (MIE-R-63). v0.3 is a new, additive revision; v0.1 (ZIP d0c51fa431c3050a08f104e22d31c7a6301be1e2a31a4cbf19aaedbdac8e5e73) and v0.2 (ZIP 0bd6177cb4f1262dd9565ab759c67e220bdad6f276dde85affb41fac5cf45fde) are not edited. Change log: MIE1_V03_CHANGE_LOG.csv (the v0.2 log is kept as history); every register row added or revised in v0.3 carries a v03_change tag, and the v02_change column keeps the v0.2 history. Nothing here approves the Section 08 change request (Option A, Option B or neither stays with the product owner), no open question is decided, and no product-owner decision is made.
- MIE-B1 precedence loophole closed: a rule is downstream when any signal-influenced rule stands earlier in the table, whatever that earlier rule's configured outcome (NOT_ASSESSED included) or basis. Every signal-influenced rule and every downstream rule must be OWNER_ASSUMPTION with an owner reference and an assumption statement, whatever its own outcome. The exemption for rules after a signal-influenced NOT_ASSESSED rule is deleted (MIE-R-22, MIE-R-63, MIE-AC-24, MIE-AC-29; section 6.6).
- MIE-B2 pack check and result contract made consistent. These are builder-identified clarifications for the reviewer to contest, not product-owner decisions: the class and the pack check use the same two definitions; a refused pack produces no result of any class; the evaluator fails closed rather than emit an unlabelled DIRECT or PRECEDENCE result; NO_TABLE and NO_RULE_MATCHED have class NONE (MIE-R-69; section 6.6).
- MIE-B3 implementation blockers made explicit: audit append and state commit atomicity needing an explicit design decision (BLK-01), the M6 mapping not derived (BLK-02) and the Section 08 cascade impact assessment unfinished (BLK-03) (MIE-R-70, MIE-AC-30; section 16.1).
- Preserved: the audit interface, the movement mathematics, the adapter-side observation flow and the nine dispositions are not changed.

### 0.1 Carried from v0.2
The v0.2 change list, unchanged in substance:
- MIE-A1 audit contract: AuditLogPort is append only; AuditQueryPort (PT-10) reads and verifies; list_audit (OP-12) reads through it and appends one access event that is not in its own result, so there is no recursion; a fixed sequence (validate, compute, append the audit event, commit, return); every operation lists the common failures including AUDIT_UNAVAILABLE (MIE-R-40, MIE-R-60, MIE-R-61, MIE-R-62; section 9.2).
- MIE-A2 signal-influence safeguard: every outcome that a market signal influences, not only WAIT and HOLD, follows the assumption-labelled owner policy, with a disclosed influence class (MIE-R-63; section 6.6).
- MIE-A3 negative and zero values: per-unit value domains, a declared movement basis, a direction-safe ratio with the absolute value of the start as denominator, ZERO_BASE for a zero start under RELATIVE, a crosses_zero flag (MIE-R-64, MIE-R-65; sections 4.9 and 5.3).
- MIE-A4 observation-feed flow: an ingestion driver triggers, a feed adapter invokes ObservationSourcePort and maps, the driver submits to submit_observations, and the core alone validates; ObservationSourcePort is adapter-side, not a core port; the core never retrieves (MIE-R-45, MIE-R-46, MIE-R-47, MIE-R-66; section 10.4).
- MIE-A5 specification-approval questions: MIE1_OQ_DISPOSITIONS.csv records a disposition and the decision still needed for each of the nine (MIE-R-67; section 15).
- MIE-A6 acceptance criteria MIE-AC-23..MIE-AC-28, tests, mutants and traceability extended (MIE-R-68).

## 1. Purpose and what this is not

MIE-1 specifies a domain-neutral Market Intelligence core that tracks subjects (things whose market is of interest), records licensed, dated observations about them, reports observed signals, and produces advisory timing assessments. Everything specific to a field (its subjects, units, sources, licence records, thresholds and decision rules) is held in a replaceable, versioned, hash-pinned pack. The first pack is the APG construction pack (BUY only). A synthetic second pack proves portability.

It is not: a forecast engine; a price predictor; a trading or ordering system; a replacement for M6; a luxury-assets product; a deployment design. No signal predicts a price, and nothing here claims one does.

The core is largely new build. M6 (apg/mkt/) is a procurement-analysis layer that follows Section 08 and is not a market-movement engine; it stays unchanged and is a future consumer (section 11).

## 2. Rulings that bound this specification

RUL-MIE-01 (DEC-MIE-01 confirmed) universal core plus packs, APG pack BUY only, synthetic second pack. RUL-MIE-02 only the change-request process is approved; until the product owner approves the change request itself, no market signal feeds any APG finding or recommendation. RUL-MIE-03 the four safeguards (no unqualified forecast; no universal rise/fall assumption; scenarios cannot alter approved forecasts; a human decides every purchase). RUL-MIE-04 nothing locked or frozen is edited. RUL-MIE-05 MIE-1 first; M7 and the profit improvement engine do not start. RUL-MIE-06 no domain vocabulary in the core; nothing invented. RUL-MIE-07 clean boundary, no deployment commitment, no live anything. RUL-MIE-08 specification only. RUL-MIE-09 builder-run and independent results reported separately. RUL-MIE-10 (2026-10-17) corrections only in a new additive revision; specification only; the Section 08 change is not approved; no product-owner decision is made silently; stop for independent review.

## 3. Architecture

### 3.1 Layers and dependency direction
1. Core: schemas, vocabularies, validators, signal computation, decision-table evaluator, result identity, replay. Pure and deterministic (MIE-R-04).
2. Packs: data documents the core validates (MIE-R-28). A pack never contains code.
3. Host ports: everything the core needs from its environment is an outbound port (section 10.2).
4. Consumers: callers of the inbound operations (section 10.1). APG is a future consumer, blocked by the isolation gate (MIE-R-51).
Dependency direction: consumers and packs depend on the core; the core depends on nothing of APG, packs or consumers (MIE-R-02).

### 3.2 Domain neutrality (MIE-R-01)
The core contains no domain-specific term. The deny-list `mie-deny-1` holds the domain terms of the three fields named in the ruling: construction, builder, material, supplier, subcontractor, tender, landed, freight, project, vehicle, car, watch, luxury, dealer, chronograph, horology. The static check runs over core source, schemas, vocabularies, error codes, messages and tests as whole words, and must be shown to fail on a planted term (NE-02). The words price, market, source, licence, level, unit, observation, signal, variant and counterparty are generic market-intelligence vocabulary and are allowed. A deny-list shows absence of listed terms only; it cannot prove that no domain concept is present (MIE-L-03). A stricter allow-list of core identifiers is a possible later hardening and is not required here.

### 3.3 Determinism (MIE-R-04)
The core reads no clock, random source, network, file system or environment. evaluation_date, as_of and retrieved_at are inputs. Identical inputs give identical bytes. Core, pack-schema, signal, outcome, event-class and error vocabularies are versioned and reported by describe() (OP-01, MIE-R-03).

## 4. Data model

### 4.1 Subjects and equivalence (MIE-R-05)
A subject is an opaque pack-scoped identifier with a pack-declared kind. The core never infers that two identifiers are the same thing. Equivalence exists only where the pack declares an explicit alias table; an alias mapping to more than one canonical identifier, or any cycle, makes the pack invalid. Values are compared only within one unit, one market and one pack-declared comparison group; otherwise the comparison is NOT_ASSESSED with reason UNIT_MISMATCH and a gap is listed.

### 4.2 Observations (MIE-R-06, MIE-R-07, MIE-R-08)
Required attributes: source_id, licence_ref, market, unit, observation_class, value_basis, as_of (calendar date), retrieved_at, and either a LEVEL value or an EVENT class. Optional: valid_until, revision (integer), supersedes. A LEVEL value is a signed integer with an integer decimal exponent; floats, NaN, infinities, booleans and numeric strings are refused; all arithmetic is exact integer arithmetic and ratios are exact fractions. An EVENT observation carries a pack-declared event label that the pack maps to a core event class (AVAILABILITY_CHANGED, VARIANT_INTRODUCED, VARIANT_WITHDRAWN).
observation_class is HISTORICAL_MOVEMENT, CURRENT_REFERENCE or COUNTERPARTY_OFFER. value_basis is ASKING, OFFER, INDEX or COMPLETED_TRANSACTION. Forward scenarios are caller inputs, not stored observations (MIE-R-25), and are the fourth evidence group. The four groups are never merged, averaged across or relabelled (MIE-R-19), and a result presents them separately.
An observation that lacks any required attribute, names a source, licence, unit, market, class or basis the pack does not declare, or carries a value outside its unit's declared value domain (section 4.9; reason VALUE_OUT_OF_DOMAIN), is rejected with the field named (OBSERVATION_INVALID) and counted as rejected; it is never used.

### 4.3 Identity, immutability and corrections (MIE-R-13)
observation_id = "OB-" + lower-case hex SHA-256 over the canonical bytes (section 7.2) of the observation attributes. The tenant is not part of the identifier; storage is tenant-scoped (MIE-R-39). Observations are append-only. Re-submission of identical content is an idempotent no-op reported as a duplicate. A correction is a new observation naming the one it supersedes; both are retained for replay.

### 4.4 Licence gate (MIE-R-09)
Each source in the pack names a licence record; each licence record declares status (LICENSED, UNLICENSED, UNKNOWN), valid_from, valid_to and an opaque terms_ref. An observation is stored only if its licence is LICENSED at ingestion (else LICENCE_NOT_PERMITTED) and is used only while the licence is LICENSED and the evaluation_date lies within its window; an observation outside the window is excluded and reported with reason LICENCE_EXCLUDED. UNKNOWN is never treated as licensed. The core evaluates status and window only and never interprets terms (MIE-L-04). A change in a licence's status or window is a new pack version (MIE-L-15).

### 4.5 Time rules (MIE-R-10)
Ages are whole calendar days: evaluation_date minus as_of. An observation dated after the evaluation_date is never used and is listed with reason OBSERVATION_AFTER_EVALUATION_DATE, however recent its retrieval. retrieved_at earlier than as_of is refused. An observation with valid_until before the evaluation_date is expired for current use (reason EXPIRED_EVIDENCE); it remains available as labelled history. Date-only granularity is a stated limitation (MIE-OQ-06, MIE-L-11).

### 4.6 No gap filling (MIE-R-11)
No interpolation, extrapolation, smoothing, carry-forward or borrowing from other series or the future. A missing point stays missing and appears as an evidence gap (MIE-R-24).

### 4.7 Conflicts and revisions (MIE-R-12)
For one series and as_of: a higher revision supersedes a lower; an exact repeat is one observation; two different values at the same revision are both reported, the date is listed as conflicting, and the core never chooses. A signal that needs a conflicting point at an endpoint is NOT_ASSESSED with reason CONFLICT_IN_EVIDENCE. Conflicts inside a pack-declared comparison group are reported by DATA_CONFLICT (MIE-OQ-21 defers wider divergence signals).

### 4.8 Freshness (MIE-R-14)
No default. A freshness limit is a whole number of days (not negative, not boolean, not a float) from the pack's freshness_limits (policy-owner configuration) or, only where the pack has none for that evidence class, from the request. A request limit for a class where the pack already has one is refused as REQUEST_MALFORMED, so a caller cannot loosen a policy limit. A missing limit gives NOT_ASSESSED with reason FRESHNESS_LIMIT_MISSING. Exactly at the limit is fresh; one day beyond is stale. The limit and the age are recorded in every result. Stale evidence stays available as history and is flagged; for the purposes of a decision-table predicate a stale signal counts as NOT_ASSESSED with reason STALE_EVIDENCE (MIE-R-27).

### 4.9 Value domains (MIE-R-64)
The core never assumes that a value is a positive price. Each unit in a pack declares value_domain, with no default: POSITIVE (value greater than zero), NON_NEGATIVE (zero or more) or SIGNED (any integer). A pack whose unit lacks it is refused (PACK_MALFORMED). A value outside its unit's declared domain is rejected at ingestion with reason VALUE_OUT_OF_DOMAIN and counted as rejected (UT-47). A conversion series must be in the POSITIVE domain (PK-26). Zero is a value only when observed and absence is never zero (MIE-R-07). Whether a negative or zero value is economically sensible for a series is the pack owner's judgement; the core cannot make it (MIE-L-20).

## 5. Signals

### 5.1 Vocabulary (MIE-R-15, version mie-signal-1)
LEVEL_MOVEMENT, CONVERSION_MOVEMENT, AVAILABILITY_CHANGE, VARIANT_INTRODUCED, VARIANT_WITHDRAWN, DATA_STALE, DATA_MISSING, DATA_CONFLICT (MIE1_SIGNAL_VOCABULARY.csv). The vocabulary is closed. A pack chooses which signals apply and supplies their parameters; it cannot add a type or change a meaning (PK-07). Any change is a core change with a new vocabulary version (MIE-OQ-20 asks whether the event classes are complete).

### 5.2 Content of a signal (MIE-R-16, MIE-R-17)
Every signal states an observed fact about evidence, never a future price or prediction; no schema field is named forecast, predicted, expected or projected (NE-04). Every signal carries: type, vocabulary version, status (ASSESSED, or NOT_ASSESSED with a reason code), subject, evidence class and basis, window, evidence identifiers, data age, the parameters used and who owns them, and a basis statement of counts (observations, distinct sources, conflicts, gaps). A movement signal also carries its movement basis, the endpoint values, the exact difference, the exact ratio where defined, the direction and the crosses_zero flag (section 5.3). The basis statement is descriptive; it is not a probability, and no confidence number exists (MIE-OQ-14).

### 5.3 LEVEL_MOVEMENT and CONVERSION_MOVEMENT mechanics (MIE-R-65, MIE-AC-25)
Parameters (all supplied by the pack, none defaulted — MIE-R-18): window_days, min_points, movement_basis (ABSOLUTE or RELATIVE), the threshold T as an exact positive integer ratio p/q (zero, negative or non-ratio thresholds refuse the pack: PK-27), freshness limit. Window = [evaluation_date - window_days, evaluation_date]. Eligible points = licensed, not future-dated, within the licence window, in one series (one unit, one market, one class, one basis). The start point is the earliest eligible as_of in the window and the end point the latest; at least min_points distinct dates are required (else INSUFFICIENT_POINTS). A missing parameter, including movement_basis or the threshold, gives NOT_ASSESSED with reason PARAMETER_MISSING (UT-48); the core assumes no basis.
Let s be the start value and e the end value, aligned to a common decimal exponent as exact integers (UT-49), and d = e - s.
- ABSOLUTE: defined for every s and e, including zero and negative values. T is a difference in the unit itself. Direction is UP when d >= T, DOWN when d <= -T and otherwise UNCHANGED (UT-45).
- RELATIVE: the ratio is r = d / |s|, with the absolute value of the start as denominator, so the sign of r always equals the sign of d and a rise in value is UP for a negative start exactly as for a positive one (UT-43). It is defined only when s is not zero; a zero start gives NOT_ASSESSED with reason ZERO_BASE and a listed gap, for every end value (UT-19, UT-42). Direction is UP when r >= T, DOWN when r <= -T and otherwise UNCHANGED.
- crosses_zero: when s and e have opposite signs the signal states crosses_zero = true, so that r is not read as a percentage change of a price (UT-44: -10 to 10 is UP with ratio 2; 10 to -10 is DOWN with ratio -2).
- The signal reports basis, s, e, d, r where defined, direction and crosses_zero, with both endpoints' evidence identifiers.
No movement is computed with a signed denominator or with floating point. Negating every value of a SIGNED series negates d and r and exchanges UP with DOWN under both bases; this symmetry is a tested property (UT-46, MIE-R-20). Mirrored histories give mirrored signals; nothing in the core prefers either direction (UT-25).

### 5.4 Other signals
CONVERSION_MOVEMENT applies LEVEL_MOVEMENT mechanics to a pack-declared conversion series between two units; there is no other source of conversion. AVAILABILITY_CHANGE, VARIANT_INTRODUCED and VARIANT_WITHDRAWN come only from EVENT observations the pack maps, within an event lookback supplied by the pack. DATA_STALE reports age and limit; DATA_MISSING lists every gap against the pack's required_evidence declaration; DATA_CONFLICT lists both values.

## 6. Timing assessment

### 6.1 Intentions and outcomes (MIE-R-21)
A pack declares its allowed intentions, a subset of BUY and SELL. Outcomes are fixed per intention: BUY gives ACT_NOW, WAIT, STAGE, NEGOTIATE or NOT_ASSESSED; SELL gives ACT_NOW, HOLD, WAIT or NOT_ASSESSED. An intention the pack does not allow is refused with INTENTION_NOT_ALLOWED, and no path can emit an outcome outside the pack's allowed intentions (UT-26). A monitor view for owned assets is the signal view (get_signals); a separate HOLD intention is deferred (MIE-OQ-11). Whether the outcome vocabulary is sufficient is MIE-OQ-18.

### 6.2 The decision table (MIE-R-22, MIE-AC-22)
The core ships no rules. The pack carries an ordered list of rules: rule_id, intention, a conjunction of predicates, an outcome allowed for the intention, a rationale code, a basis class (OBSERVED_EVIDENCE_ONLY or OWNER_ASSUMPTION) and, for OWNER_ASSUMPTION, an owner reference and an assumption statement. The predicate language is closed and total: SIGNAL_PRESENT(type, class, direction), SIGNAL_NOT_ASSESSED(type, optional reason), GAP_PRESENT(reason), CONSTRAINT_COMPARE(days_to_need_by, comparison, pack parameter), CONSTRAINT_ABSENT, SCENARIO_PRESENT(label), QUALIFIED; each may be negated; there is no loop, disjunction or arithmetic beyond integer comparison (disjunction is written as separate rules). Rules are tried in order and the first match wins (UT-28). No table gives NOT_ASSESSED with reason NO_TABLE; no match gives NO_RULE_MATCHED. Any rule that uses a market-signal predicate (SIGNAL_PRESENT or SIGNAL_NOT_ASSESSED on LEVEL_MOVEMENT, CONVERSION_MOVEMENT, AVAILABILITY_CHANGE, VARIANT_INTRODUCED or VARIANT_WITHDRAWN) is signal-influenced whatever its outcome and is governed by the safeguard in section 6.6, as is every rule placed after a signal-influenced rule (a downstream rule, whatever the earlier rule's outcome) (v0.1 limited this to WAIT and HOLD; v0.2 did not; v0.3 also removes the NOT_ASSESSED exemption for later rules). Predicates on DATA_STALE, DATA_MISSING and DATA_CONFLICT are data-quality predicates, not market-signal predicates. days_to_need_by is the need-by date minus the evaluation_date; a missing constraint gives CONSTRAINT_MISSING when a rule needs it. The expressive limit of the language is acknowledged (MIE-L-07).

### 6.3 Scenarios (MIE-R-25)
A scenario is an explicit caller input: scenario identifier, label, owner reference, basis statement, assumed level and unit. The core never generates a scenario, never derives one from history (UT-32), labels each result element as an ASSUMPTION and not a forecast, and has no operation, message or field that reads, writes or references an approved forecast (NE-05, UT-33). A forecast-shaped input is refused as SCENARIO_INVALID.

### 6.4 Qualification and gaps (MIE-R-24, MIE-R-27)
The pack declares required_evidence. If any required evidence is stale, expired, unavailable, unlicensed or conflicting, the result is QUALIFIED with each reason stated. Every missing, excluded, stale, conflicting or unlicensed input is an evidence gap with a reason code; a gap is never counted as zero and never dropped (UT-31). A result with no usable evidence is NOT_ASSESSED; it never yields an outcome from nothing (AD-09).

### 6.5 Result record (MIE-R-23, MIE-R-26)
A timing result contains: result identifier; versions and pack pin (section 8); intention; constraints echoed; evidence used (identifier, class, basis, age, freshness limit) in four separate groups; signals; the rule fired and its basis class; the outcome; the assumption label and the signal-influence class where applicable; the uncertainty statement (basis counts plus the fixed statement that observed movement is not a forecast); all gaps; the qualification; and the statement that the record is advisory, commits nothing, and that a human decides. There is no operation that orders, commits, notifies or changes external state (MIE-R-26, NE-05).

### 6.6 Signal-influence safeguard (MIE-R-63, MIE-R-69, MIE-AC-24, MIE-AC-29)
The rule applies to every outcome, not only WAIT and HOLD, and to every rule that can fire only because a signal-influenced rule did not match, because under a signal-using profile a market signal could otherwise steer ACT_NOW, STAGE or NEGOTIATE without being labelled.
- A market signal is a signal of type LEVEL_MOVEMENT, CONVERSION_MOVEMENT, AVAILABILITY_CHANGE, VARIANT_INTRODUCED or VARIANT_WITHDRAWN.
- Definition 1. A rule is signal-influenced when it contains a market-signal predicate, whatever its configured outcome (ACT_NOW, WAIT, STAGE, NEGOTIATE, HOLD or NOT_ASSESSED).
- Definition 2. A rule is downstream when at least one signal-influenced rule stands earlier in the table, whatever that earlier rule's configured outcome or basis class, and whether or not the rule itself contains a market-signal predicate. Rules are first-match, so a downstream rule can fire only because every earlier rule, the signal-influenced ones included, did not match.
- Pack check, from the two definitions only: every signal-influenced rule and every downstream rule must carry basis_class OWNER_ASSUMPTION with an owner reference and an assumption statement, whatever its own configured outcome (NOT_ASSESSED included); otherwise the pack is refused with PACK_RULE_POLICY_VIOLATION by validate_pack and by register_pack (PK-19, PK-21, PK-22, PK-23, PK-28, PK-29, PK-30, PK-32, AD-14, AD-15). Equivalently, every rule from the first signal-influenced rule onward is owner-labelled; a pack that wants unassumed rules places them before the first signal-influenced rule; a no-match outcome needs no rule.
- The loophole closed in v0.3. In v0.2 a rule after a signal-influenced rule whose configured outcome was NOT_ASSESSED was exempt. Rule 1 signal-influenced with outcome NOT_ASSESSED and a predicate that does not match, then rule 2 under OBSERVED_EVIDENCE_ONLY with outcome ACT_NOW: rule 2 could fire as PRECEDENCE with no owner reference and no assumption statement. v0.3 refuses that pack (PK-28, PK-29; mutant SB-50). The same sequence with owner-labelled rules is accepted (PK-33) and yields PRECEDENCE with the label (UT-50).
- Every result discloses a signal-influence class, by the same two definitions: DIRECT (the fired rule is signal-influenced); PRECEDENCE (the fired rule is downstream and is not itself signal-influenced); NONE (the fired rule is neither, so no signal-influenced rule stands before it; or the profile is CONTEXT_ONLY; or no rule fired, that is NOT_ASSESSED with reason NO_TABLE or NO_RULE_MATCHED, where NO_RULE_MATCHED lists the signal-influenced rules evaluated) (UT-38, UT-39, UT-40, UT-51, UT-52, UT-53).
- Pack check and class use one definition, so a result of class DIRECT or PRECEDENCE always has an owner-labelled fired rule. A pack that breaks the policy produces no result of any class: register_pack stores nothing, get_pack and activate_pack return NOT_FOUND and assess_timing returns PACK_NOT_ACTIVE (MIE-R-69, PK-31). The evaluator also checks the fired rule's label before it emits; a DIRECT or PRECEDENCE result from an unlabelled rule is never emitted: the core returns INTERNAL_ERROR_FAIL_CLOSED, appends a FAILED audit event and stores nothing (UT-54).
- A DIRECT or PRECEDENCE outcome is labelled assumption-based and carries the owner reference and assumption statement of the fired rule and the identifiers of the signal-influenced rules evaluated (UT-37). It is never presented as a forecast or as a tendency of prices, and it is qualified when its evidence is stale, expired, unavailable or conflicting (UT-41).
- A pack containing any OWNER_ASSUMPTION rule can be activated only with a verified approval reference (section 7.5, PK-25), and the result records that reference. This is the sense in which the policy is approved: the owner approves the pack, assumptions included; the core cannot approve it.
- The core does not judge whether a signal is materially influential. Influence is structural, so the label can over-state influence and cannot under-state it (MIE-L-19); whether that definition is acceptable is MIE-OQ-26.
Under CONTEXT_ONLY no rule may use a market-signal predicate (PK-18) and signals are context only.

## 7. Packs

### 7.1 Pack schema mie-pack-1 (MIE-R-28)
Closed; unknown keys, duplicate keys and executable content are refused. Sections: pack_schema, pack_id, pack_version, field_label, core_compat (exact core versions), allowed_intentions, decision_profile, vocabulary (subject kinds, units with decimal scale, markets), alias tables, comparison groups, sources (each naming a licence record and allowed value bases), licence records (status, valid_from, valid_to, opaque terms_ref), event mapping, conversion series, enabled signals with parameters and parameter_owner_ref, freshness_limits with owner_ref, required_evidence, decision_table, hook declarations, and provenance (author reference, owner reference, synthetic flag). The approval reference is supplied at activation, not stored in the pack.

### 7.2 Canonical form and hash (MIE-R-29, PK-20)
Canonical bytes: UTF-8 JSON; object keys sorted by the UTF-8 bytes of the key; no insignificant whitespace; arrays keep order; integers in plain decimal with no sign for positives and no leading zeros; no floats; strings NFC with only the mandatory escapes; duplicate keys refused at parse. The pack hash is lower-case hex SHA-256 over the canonical bytes of the pack document (which contains no hash of itself). The same canonical form identifies observations (OB-) and results (RS-). MIE-OQ-04 asks whether to adopt RFC 8785 instead.

### 7.3 Validation (MIE-R-31, MIE-R-32)
A pack is refused, with the stated code, for: malformed or unknown structure (PACK_MALFORMED); unsupported schema (PACK_SCHEMA_UNSUPPORTED); no supported core version (PACK_CORE_INCOMPATIBLE); an attempt to override a core invariant — a default freshness limit, making a non-LICENSED status usable, floats, intentions outside BUY and SELL, a new signal type, a changed signal meaning, an outcome outside the per-intention vocabulary (PACK_INVARIANT_OVERRIDE); dangling references (source to licence, rule to parameter, hook to port); duplicate identifiers; non-NFC text; a rule whose outcome is not allowed for its intention; a signal predicate under CONTEXT_ONLY (MIE-R-34); a signal-influenced or downstream rule that breaks the signal-influence policy of section 6.6 (PACK_RULE_POLICY_VIOLATION, raised by validate_pack and register_pack; a refused pack is not stored and cannot be activated, MIE-R-69); a unit without value_domain (PACK_MALFORMED), a conversion series outside the POSITIVE domain, a movement threshold that is zero, negative or not an exact integer ratio.

### 7.4 Versioning, immutability, withdrawal (MIE-R-30)
(pack_id, pack_version) is bound to one hash forever. Identical bytes published again are a no-op; different bytes under the same pair are refused (PACK_VERSION_CONFLICT). Withdrawal is a separate registry record; the pack bytes never change. A withdrawn pack (PACK_WITHDRAWN) accepts no new assessments; its stored results still replay. Every request pins (id, version, hash); a mismatch is PACK_HASH_MISMATCH.

### 7.5 Activation and approval (MIE-R-33)
A tenant activates a pinned pack with an owner approval reference. The core records it and asks ApprovalVerifierPort to verify it; the core cannot approve a pack and a builder-authored pack cannot self-approve. Missing or rejected approval is PACK_APPROVAL_MISSING. A pack with any OWNER_ASSUMPTION rule needs this verified approval to be activated at all (MIE-R-63). A later activation never edits an earlier one. How approvals are verified is MIE-OQ-17; that the core cannot establish genuineness is MIE-L-05. Whether packs are platform-wide or tenant-private is MIE-OQ-02. Who supplies a pack's parameters is MIE-OQ-03.

### 7.6 Decision profile (MIE-R-34)
CONTEXT_ONLY: market signals are returned beside the outcome, no rule may use a market-signal predicate, and the signal-influence class of every outcome is NONE. SIGNAL_RULES: rules may use market-signal predicates subject to section 6.6. The core supports both; the profile a given pack may use is fixed by the pack's owner and, for the APG pack, by the Section 08 change request decision (MIE-OQ-12): CONTEXT_ONLY until then.

### 7.7 Hook slots (MIE-R-48)
A pack may declare named hooks for field-specific cost or value calculations (for example landed cost in one field, depreciation in another). The core defines only the CostValueHookPort slot: pure, deterministic, inputs and outputs integer-only, refusal as HOOK_UNAVAILABLE. No hook formula or implementation is specified or built in MIE-1 (MIE-OQ-13).

## 8. Reproducibility (MIE-R-35, MIE-R-36, MIE-R-37)
result_id = "RS-" + SHA-256 over the canonical bytes of: core version and every vocabulary version, the pack pin, the request, and the evidence set (observation identifiers, each of which contains its content digest). Any change in a pinned input changes the identifier (RP-02). Replay recomputes from stored evidence by identifier, never the latest data, and must reproduce the stored result byte for byte (RP-01, RP-03). Missing evidence gives REPLAY_EVIDENCE_UNAVAILABLE; a missing pack gives REPLAY_PACK_UNAVAILABLE; neither gives a partial replay. Replay under different named versions yields a drift report and never overwrites the original (RP-05). The core mirrors the discipline of apg.repro (run, replay, drift_report, pinned InputRef) without importing it (MIE-OQ-19). Retention of evidence versus licence-driven deletion is unresolved (MIE-OQ-07).

## 9. Tenancy, audit, failure

### 9.1 Tenancy (MIE-R-38, MIE-R-39)
Every operation takes a context verified by TenantContextPort. A tenant field in a payload is refused. Missing, forged or expired context is refused for every operation (TENANT_CONTEXT_MISSING, TENANT_CONTEXT_INVALID). Another tenant's subject, series, observation, result or activation is indistinguishable from a missing one: the same code (NOT_FOUND) and the same shape. A licence held by one tenant is not a licence for another. Returned values are independent copies. Stored keys are tenant-scoped. Timing side channels are not claimed closed (MIE-L-10). Cross-tenant sharing of licensed data is unresolved (MIE-OQ-08).

### 9.2 Audit (MIE-R-40, MIE-R-60, MIE-R-61, MIE-R-62)
Ports. AuditLogPort (PT-05) is append only and surfaces every failure. AuditQueryPort (PT-10) is read-only and tenant-scoped: read (tenant, from sequence, limit) and verify (tenant). Both mirror the shape of APG's AuditLogPort (EDR-03: append, read, verify; apg/ports.py:141-160) without importing it; the split gives list_audit a read path and keeps every other operation unable to read events.
Sequence. For an operation with a verified tenant context the core (1) validates the request, (2) computes the outcome without side effects, (3) appends the audit event, (4) only then commits state through the store ports, and (5) returns the result. The event carries identifiers and digests, never licensed values (AU-10), the operation identifier, an outcome class, the error code if any and a correlation identifier. Outcome classes: OK (a completed read or validation), ACCEPTED (a state-changing operation that passed validation and is about to commit), REFUSED (a refusal, with its error code: AU-12), FAILED (a failure). If step 3 fails the operation returns AUDIT_UNAVAILABLE with no result and no state change, for every operation including reads (AU-06, AU-07, MIE-OQ-16). ACCEPTED is not proof that the commit happened: if a store port fails at step 4 the core returns STORE_UNAVAILABLE and makes one attempt to append a FAILED event, so the trail never records a completed change that did not happen (AU-08). Atomicity between an audit append and a store commit is a host property the core cannot supply (MIE-OQ-23, MIE-L-17).
Reading the audit. list_audit (OP-12) fixes a cutoff sequence number, reads the calling tenant's events up to it through AuditQueryPort, and then appends exactly one access event of type AUDIT_READ. That event is not in its own result and returning it creates no further event, so the operation cannot recurse; the next call shows it (AU-01, AU-02). If the access event cannot be appended, list_audit returns AUDIT_UNAVAILABLE and no events (AU-03). The result includes the chain verification result: a broken or tampered chain is reported and never trimmed or repaired (AU-05). Another tenant's events are invisible (AU-04).
Unattributable refusals. A context that cannot be verified names no tenant, so there is no tenant chain to write to: the refusal returns TENANT_CONTEXT_MISSING or TENANT_CONTEXT_INVALID and produces no tenant audit event (AU-09). Whether the host records such refusals elsewhere is MIE-OQ-24.
Error lists. MIE1_PORTS.csv lists every error each operation can return; every operation lists TENANT_CONTEXT_MISSING, TENANT_CONTEXT_INVALID, AUDIT_UNAVAILABLE and INTERNAL_ERROR_FAIL_CLOSED, and the others as MIE-R-62 states (AU-11).

### 9.3 Failure (MIE-R-41)
Failure is typed and closed. Operation-level problems are errors (MIE1_ERROR_VOCABULARY.csv, kind ERROR): never a partial result, never an outcome. Not-assessable evidence inside a complete result uses reason codes (kind REASON). An unexpected exception becomes INTERNAL_ERROR_FAIL_CLOSED. A pack not activated for the calling tenant gives PACK_NOT_ACTIVE; a failing store port gives STORE_UNAVAILABLE and the operation fails closed (section 9.2 orders this against the audit append); evidence-free requests give the reason NO_EVIDENCE inside a complete NOT_ASSESSED result.

### 9.4 Limits and text (MIE-R-42, MIE-R-43)
Batch size, string length, series length, rule count and pack size are bounded by a LimitsConfig object the host supplies; the core ships no production value. Absent limits give LIMIT_NOT_CONFIGURED; exceeded limits give LIMIT_EXCEEDED. Values are the host's (MIE-OQ-09). All text is data: NFC or refused, control characters refused, bounded; injection-like content is inert.

## 10. Service boundary (MIE-R-44, MIE-R-45, MIE-R-46)

### 10.1 Inbound operations
OP-01 describe, OP-02 validate_pack, OP-03 register_pack, OP-04 get_pack, OP-05 withdraw_pack, OP-06 activate_pack, OP-07 submit_observations, OP-08 get_signals, OP-09 assess_timing, OP-10 replay_result, OP-11 get_result, OP-12 list_audit. Messages are value-typed canonical objects; each operation takes a verified tenant context. Inputs, outputs and the full error list of each operation are in MIE1_PORTS.csv. The semantics are the same whether the core is embedded as a library or hosted as a service; the specification commits to neither and to no transport (MIE-OQ-01). The reference implementation language is not decided (MIE-OQ-22).

### 10.2 Outbound ports
PT-01 TenantContextPort (existing definition, EDR-01), PT-02 ObservationStorePort, PT-03 PackRegistryPort, PT-04 ResultStorePort, PT-05 AuditLogPort (append; shape of EDR-03), PT-07 CostValueHookPort, PT-08 ApprovalVerifierPort, PT-09 LimitsConfig, PT-10 AuditQueryPort (read and verify; shape of EDR-03). PT-06 ObservationSourcePort is not in this list: it is an adapter-side contract (section 10.4) and the core never calls it. Whether PT-02 and PT-04 reuse RecordStorePort (EDR-02) is MIE-OQ-15. No port assumes a database, queue, scheduler, vendor or deployment shape. The core has no clock port because it reads no clock.
Each port has a contract suite and an in-memory reference implementation labelled non-production; so does the adapter-side ObservationSourcePort; no persistence, durability or performance is claimed (MIE-R-46, MIE-L-13).

### 10.3 Relationship to MarketFeedPort (MIE-R-47)
The core restates the MarketFeedPort invariants for observations: the contract suite includes an analogue of each of MF-01..MF-13, applied at submit_observations and at assessment (MIE1_TRACE_TO_EXISTING_CONTRACTS.csv; FL-10). The M6 port definition is not changed; a mapping adapter on the ingestion side is the integration route (MIE-OQ-10). The M6 attribute mapping is not yet derived (MIE-L-16).

### 10.4 Observation-feed flow (MIE-R-66, MIE-AC-26)
The flow, step by step, is in MIE1_FEED_FLOW.csv (FF-01..FF-09). In words:
1. An ingestion driver on the host or integration side decides when to retrieve. The trigger is not specified, and which component is the driver and where it runs is not decided (MIE-OQ-25, RUL-MIE-07).
2. The driver calls a feed adapter. The feed adapter is the only component that invokes ObservationSourcePort (PT-06) and the only one that knows a feed's protocol.
3. The feed adapter maps what it retrieved to the observation message schema and sets source_id, licence_ref, market, unit, class, basis, as_of and retrieved_at. Any validation it performs is a convenience; the core never trusts it (FL-02).
4. The driver submits the batch, with its verified tenant context and the pack pin, to submit_observations (OP-07). The batch names no tenant (FL-09).
5. The core alone validates every item (attributes, pack declarations, licence gate, value domain, time rules, size limits) and returns a per-item receipt. This is the single place observation validation is authoritative.
6. The driver acts on the receipts. A retry of a batch is safe: identical content is a duplicate no-op (FL-04).
What the core does not do: it never calls ObservationSourcePort or any feed, retrieves nothing during get_signals or assess_timing (FL-01, FL-07), and never learns of a feed failure. A feed failure is an adapter-side event; no core operation is invoked and no core state changes (FL-05); it reaches the core only as a missing observation, which assessment reports as an evidence gap and never fills (FL-06). A licence status that a feed asserts is recorded as evidence at most; only the pack's licence record grants use (FL-08). retrieved_at is asserted by the adapter and the core checks only that it is not earlier than as_of (MIE-L-18). M6 and its MarketFeedPort are not changed and no deployment is chosen.

## 11. APG construction pack boundary (MIE-R-49, MIE-R-50, MIE-R-51, MIE-R-52)
- Allowed intentions: BUY only. SELL is refused (UT-27) and no SELL-side outcome can be produced (UT-26).
- Vocabulary: names M6's terms (material identity, units, currency, geography, source kinds) by reference; it defines no new M6 behaviour. The mapping from M6's observation attributes to core attributes (source, geography, unit, kind, date) and its kind values to class and basis has not been derived in this specification and will be derived from M6 source at implementation start; this is recorded as MIE-L-16.
- Content supplied by the builder: structure only. No threshold, freshness limit, parameter, rule or financial assumption. The pack is INCOMPLETE until the policy owner supplies them (MIE-OQ-03); an incomplete pack gives NOT_ASSESSED and lists the missing items, and operations needing them return PACK_INCOMPLETE.
- Decision profile: CONTEXT_ONLY until the Section 08 change request is decided (MIE-OQ-12).
- Isolation gate (MIE-R-51, MIE-AC-13): no APG finding or recommendation imports or consumes the core; no consumer adapter exists; APG outputs are byte-identical with and without the core. Wiring is a separately authorised later step.
- Frozen baselines (MIE-R-52): M6 and the whole APG suite unchanged and passing; preserved release hashes and locked-file hashes re-verified (MIE1_BASELINES.csv).
- Value domains, movement basis and thresholds for the APG pack are owner-supplied like its other parameters; the builder supplies none (MIE-R-64, MIE-R-65).
- Cost hook: landed cost stays in M6. Binding it to a pack hook is not specified in MIE-1.

## 12. Synthetic portability pack (MIE-R-53, MIE-R-54)
A pack labelled SYNTHETIC with field label "TEST FIELD (SYNTHETIC)", invented identifiers (for example SYN-ITEM-A, SYN-UNIT, SYN-MARKET-1), allowed intentions BUY and SELL, and the SIGNAL_RULES profile so the rule machinery is exercised. It names no vendor, uses no real data, makes no market claim, and has no luxury functionality. Every value it or any fixture carries is a test fixture flagged TEST-ONLY and is not guidance (SY-06). Portability is shown by: core file hashes identical before and after the pack is added (SY-02) and both packs running the same assess code path (SY-03). It demonstrates structure only (MIE-L-08).

## 13. Test strategy, adversarial cases, sabotage, acceptance (MIE-R-55, MIE-R-56)
Families and counts are in MIE1_TEST_STRATEGY.csv: NE static (neutrality, import graph, forbidden fields, clock use); PK pack; UT unit; RP replay; IS tenancy; CT port contracts; AD adversarial; AU audit contract; FL observation-feed flow; IG frozen-baseline and isolation gate; SY synthetic and APG pack; QA meta. Every case is PLANNED; none is written or run.
Adversarial coverage: stale, conflicting, unlicensed, missing and malicious inputs (AD-01..AD-15): sink and store failures, hostile text, extreme numbers, impossible dates, all-bad worlds, one-directional histories, cross-tenant re-submission, duplicate keys.
Sabotage: MIE1_SABOTAGE_CATALOGUE.csv lists 60 deliberate faults, each tied to the requirement it violates and the tests that must catch it (QA-01). Method: targeted, hand-written faults in a copy of the core, one at a time; every one must fail at least one named test; a survivor is a defect unless recorded as an equivalent mutant with its reason. No kill-rate threshold other than 100% of the catalogue is set; operator-based automatic mutation may be added by the reviewer.
Reporting (MIE-R-57) separates builder-run from independently verified results with exact hashes, defects and limitations, and (MIE-R-58) makes no readiness, market-validity, predictive or coverage claim. Acceptance: MIE-AC-01..MIE-AC-30 (MIE1_ACCEPTANCE.csv) each name their requirements, method and planned tests. MIE-AC-12 requires builder-run and independently verified results to be reported separately.

## 14. Relationship to locked Section 08 and the change request (MIE-R-59)
Section 08 s2 says forecasts remain separate; s7 keeps historical movement, current reference prices, supplier quote movement and forward-looking scenarios distinct and says historical trends do not guarantee future prices; s7.1 and s14 require freshness thresholds and qualification; s8 defines Wait as an assessment of explicit future-price scenarios and says not to apply a universal rule that prices will rise or fall; s18 decision (3) repeats the freshness rule.
The conflict is narrow: the locked text gives market observations no role in the buy-timing outcome other than benchmarking and history; MIE-1 introduces signals that could. The core itself keeps every safeguard (MIE-R-16, MIE-R-19, MIE-R-20, MIE-R-25, MIE-R-26, MIE-R-27). The draft change request (MIE1_DRAFT_CHANGE_REQUEST_S08.md) offers Option A (context only) and Option B (assumption-labelled owner rules) for the product owner. It is unnumbered, a DRAFT and not approved. Until approved, nothing feeds any APG finding (MIE-R-51). In v0.2 the draft states that, under Option B, every outcome a market signal influences (not only WAIT and HOLD) is assumption-labelled (MIE-R-63); the draft remains unnumbered, unapproved, and neither option is chosen. In v0.3 the draft's clause (h) also states that a rule placed after a signal-influenced rule is governed whatever the earlier rule's outcome; the draft remains unnumbered, unapproved and undecided.

## 15. Open architectural questions and the nine specification-approval dispositions (MIE-R-67, MIE-AC-27)
MIE1_OPEN_QUESTIONS.csv holds all 26 questions with options, a builder recommendation (not a decision), owner, what each blocks and a status. The ones that most change the design: MIE-OQ-01 shared service or embedded library; MIE-OQ-02 pack scope and publication rights; MIE-OQ-03 who owns each pack's parameters; MIE-OQ-04 canonical form; MIE-OQ-05 data-only packs; MIE-OQ-06 time granularity; MIE-OQ-07 retention versus licence deletion; MIE-OQ-08 licence terms and display; MIE-OQ-09 limit values; MIE-OQ-10 MarketFeedPort relationship; MIE-OQ-11 owned-asset monitoring; MIE-OQ-12 Section 08 option; MIE-OQ-13 hooks; MIE-OQ-14 uncertainty statement; MIE-OQ-15 store reuse; MIE-OQ-16 read-path audit; MIE-OQ-17 approval verification; MIE-OQ-18 outcome vocabulary; MIE-OQ-19 repro reuse; MIE-OQ-20 event classes; MIE-OQ-21 divergence signals; MIE-OQ-22 implementation language. New in v0.2: MIE-OQ-23 audit and commit atomicity; MIE-OQ-24 audit of unattributable refusals; MIE-OQ-25 who runs the ingestion driver and adapters; MIE-OQ-26 whether the structural definition of signal influence is acceptable. In v0.3 MIE-OQ-23 is named as the open design decision behind blocker BLK-01 (section 16.1); it remains open and undecided.
The nine questions the audit asked to be settled before implementation are MIE-OQ-05, -06, -10, -11, -14, -16, -18, -19 and -20. MIE1_OQ_DISPOSITIONS.csv records, for each, the disposition the specification is written to, the justification, the basis (the independent reviewer's recorded default of 2026-10-17 where one exists, otherwise the builder's recommendation), the consequence if the alternative is chosen, the decision owner, the decision still needed and a status. None is recorded as decided by the builder. Where the independent reviewer owns the question and recorded a default, the status is SPECIFIED - REVIEWER CONFIRMATION REQUIRED (MIE-OQ-05, -10, -16, -19); where the product owner owns it, the status is SPECIFIED AS PROPOSED - PRODUCT-OWNER DECISION REQUIRED (MIE-OQ-06, -11, -14, -18, -20), even where the reviewer's default agrees with the proposal. MIE-OQ-16 is specified only after the audit interface correction of section 9.2. The Section 08 choice (MIE-OQ-12) is separate and is not made here.
| question | disposition (first sentence) | status |
|---|---|---|
| MIE-OQ-05 | Packs are data only: closed schema mie-pack-1, no executable content, validated by the core (MIE-R-28, MIE-R-31; PK-03) | SPECIFIED - REVIEWER CONFIRMATION REQUIRED |
| MIE-OQ-06 | as_of, valid_until, evaluation_date and ages are calendar dates; ages are whole days (MIE-R-10, MIE-L-11) | SPECIFIED AS PROPOSED - PRODUCT-OWNER DECISION REQUIRED |
| MIE-OQ-10 | M6 and its MarketFeedPort stay unchanged | SPECIFIED - REVIEWER CONFIRMATION REQUIRED |
| MIE-OQ-11 | get_signals (OP-08) is the monitor view in MIE-1 | SPECIFIED AS PROPOSED - PRODUCT-OWNER DECISION REQUIRED |
| MIE-OQ-14 | The uncertainty statement is structured counts (observations, distinct sources, conflicts, gaps) plus the fixed statement that observed movement is not a forecast | SPECIFIED AS PROPOSED - PRODUCT-OWNER DECISION REQUIRED |
| MIE-OQ-16 | Every operation with a verified context fails closed with AUDIT_UNAVAILABLE when its audit event cannot be recorded, reads included | SPECIFIED - REVIEWER CONFIRMATION REQUIRED |
| MIE-OQ-18 | The outcome vocabulary is closed: BUY gives ACT_NOW, WAIT, STAGE, NEGOTIATE, NOT_ASSESSED; SELL gives ACT_NOW, HOLD, WAIT, NOT_ASSESSED | SPECIFIED AS PROPOSED - PRODUCT-OWNER DECISION REQUIRED |
| MIE-OQ-19 | The core mirrors the replay discipline of apg | SPECIFIED - REVIEWER CONFIRMATION REQUIRED |
| MIE-OQ-20 | Three event classes, closed: AVAILABILITY_CHANGED, VARIANT_INTRODUCED, VARIANT_WITHDRAWN (MIE-R-15) | SPECIFIED AS PROPOSED - PRODUCT-OWNER DECISION REQUIRED |
None of the 26 questions is decided here. The others can follow the specification review.

## 16. Limitations
MIE1_LIMITATIONS.csv (MIE-L-01..MIE-L-21). In short: specification only, nothing implemented; all checks builder-run; deny-list is partial evidence of neutrality; licence terms and approval authenticity are not established by the core; signals are observed movement, not forecasts; decision-table language is small; the synthetic pack proves structure only; no real feed or vendor; no performance claim; the change request is a draft. Added in v0.2: audit append and state commit are not atomic (MIE-L-17); retrieved_at is asserted by the adapter (MIE-L-18); signal influence is structural and can over-state (MIE-L-19); the core cannot judge whether a movement measure is meaningful for a series (MIE-L-20). Added in v0.3: the Section 08 cascade impact assessment has not been performed (MIE-L-21); MIE-L-16 and MIE-L-17 now name blockers.

### 16.1 Implementation blockers (MIE-R-70, MIE-AC-30)
MIE1_IMPLEMENTATION_BLOCKERS.csv records three blockers, each OPEN - BLOCKS IMPLEMENTATION AUTHORISATION. None is resolved and the builder decides none.
- BLK-01 Audit append and state commit are not atomic (MIE-R-61, MIE-L-17, MIE-OQ-23). An explicit design decision must be recorded and independently reviewed before implementation is authorised. The builder makes no decision and gives no recommendation here.
- BLK-02 The mapping from M6 observation attributes and kinds to the core is not derived (MIE-R-49, MIE-L-16). It must be derived from M6 source (read only; M6 unchanged) and independently reviewed.
- BLK-03 The Section 08 cascade impact assessment is unfinished (MIE-R-59, MIE-L-21). It must be performed under change control and independently reviewed. The product owner's decision on Option A, Option B or neither is separate and also outstanding.
Neither this revision nor the delivered v0.1 and v0.2 packages is declared closed or implementation-ready.

## 17. Evidence status of this package
Builder-run: the consistency checker over the registers and documents (tools/check_mie1_records.py), tamper tests of that checker, a clean-extraction re-run and a re-hash of the preserved artifacts including the delivered v0.1 and v0.2 packages. These test the internal consistency of the specification only. Independently verified: nothing in this revision. (The independent audit of v0.1 verified that package's integrity, and the independent review of v0.2 reproduced its manifest, 43/43 checker and 47/47 tamper results; neither extends to v0.3.) This package makes no claim that MIE-1 is production-ready or complete beyond its authorised milestone. STOP: returned for independent review; no implementation code is written.

## 18. Acceptance and requirement index (generated from MIE1_ACCEPTANCE.csv; the checker compares it with the register)
- MIE-AC-01 Neutrality and independence: MIE-R-01, MIE-R-02
- MIE-AC-02 Portability: MIE-R-53, MIE-R-54
- MIE-AC-03 Pack validation: MIE-R-15, MIE-R-28, MIE-R-29, MIE-R-30, MIE-R-31, MIE-R-32
- MIE-AC-04 Observation integrity: MIE-R-05, MIE-R-06, MIE-R-07, MIE-R-08, MIE-R-09, MIE-R-10, MIE-R-11, MIE-R-13
- MIE-AC-05 Explicit freshness and parameters: MIE-R-14, MIE-R-18
- MIE-AC-06 Allowed outcomes: MIE-R-21, MIE-R-49
- MIE-AC-07 Gaps and advisory records: MIE-R-23, MIE-R-24, MIE-R-26
- MIE-AC-08 Reproducibility: MIE-R-04, MIE-R-35, MIE-R-36, MIE-R-37
- MIE-AC-09 Tenant isolation: MIE-R-38, MIE-R-39
- MIE-AC-10 Frozen baselines: MIE-R-52
- MIE-AC-11 Sabotage proof: MIE-R-55, MIE-R-56
- MIE-AC-12 Honest reporting: MIE-R-57, MIE-R-58
- MIE-AC-13 Isolation gate: MIE-R-51
- MIE-AC-14 Pack immutability and approval: MIE-R-29, MIE-R-30, MIE-R-33
- MIE-AC-15 Scenarios and forecasts stay separate: MIE-R-19, MIE-R-25, MIE-R-26
- MIE-AC-16 Observed facts, no prediction, direction-neutral: MIE-R-15, MIE-R-16, MIE-R-17, MIE-R-20
- MIE-AC-17 Stale, conflicting and missing evidence: MIE-R-12, MIE-R-14, MIE-R-24, MIE-R-27
- MIE-AC-18 Fail closed: MIE-R-40, MIE-R-41, MIE-R-42, MIE-R-43
- MIE-AC-19 Service boundary: MIE-R-03, MIE-R-44, MIE-R-45, MIE-R-46, MIE-R-47, MIE-R-48
- MIE-AC-20 No builder-invented values: MIE-R-18, MIE-R-34, MIE-R-50, MIE-R-53
- MIE-AC-21 Change request discipline: MIE-R-34, MIE-R-59
- MIE-AC-22 Deterministic decision table: MIE-R-22
- MIE-AC-23 Audit contract coherence: MIE-R-40, MIE-R-60, MIE-R-61, MIE-R-62
- MIE-AC-24 Signal-influence safeguard for every outcome: MIE-R-22, MIE-R-23, MIE-R-34, MIE-R-63
- MIE-AC-25 Value domains and movement mathematics: MIE-R-07, MIE-R-17, MIE-R-20, MIE-R-64, MIE-R-65
- MIE-AC-26 Observation-feed flow: MIE-R-45, MIE-R-46, MIE-R-47, MIE-R-66
- MIE-AC-27 Specification-approval dispositions: MIE-R-67
- MIE-AC-28 Revision discipline: MIE-R-68
- MIE-AC-29 Precedence loophole closed; pack check and result contract consistent: MIE-R-22, MIE-R-23, MIE-R-63, MIE-R-69
- MIE-AC-30 Explicit implementation blockers: MIE-R-70
