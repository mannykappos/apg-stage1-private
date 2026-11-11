# Change record APG-MIE-1: the universal market-intelligence core, built as code, with construction as the first industry pack

| Field | Value |
|---|---|
| Release | APG-MIE-1, a separately versioned, additive release. It is the delivered M7.3 package (ZIP SHA-256 `f14b6818000cb1ac76482d5d2b5246f82030aa84216eb44dc6b0ee1fac7f6307`, 918 files; the full hash of every file is in `regression/mie1/M7_3_MANIFEST.sha256`) plus the market-intelligence core, its packs, adapters, tests and tools. The delivered M7.3 ZIP and documents are not modified or replaced. |
| Status | **Builder-implemented and locally tested; no independent review has taken place.** Nothing here is accepted or approved, and nothing is for use outside tests. |
| Authority | The product owner's authorisation, relayed after the M7.3 audit: build MIE-1 as code, reusing and generalising M6's market-intelligence logic, with construction as the first industry pack; audit the runnable code and tests. The M7.3 acceptance and the Engine-store verification stay recorded as open release gates (CF-36), not as reasons to stop development. |
| Specification | MIE1_SPEC v0.3 and its registers, copied unchanged into `spec/MIE1_SPEC_v0.3/` (23 files). The implementation follows it; where it leaves a choice, the reading taken is recorded as an interpretation (I-118 to I-124). |
| Gates still open | M7.3 final release acceptance (the full sabotage and mutation suites were not independently completed); EDR-36 (the Engine store's guard contract); the M9.4 ZIP comparison; the implementation blockers BLK-01, BLK-02 and BLK-03 (CF-37); EDR-37 (the core's host ports). None is closed or decided here. |

## 1. What was built

| Part | Where | What it does |
|---|---|---|
| The core | `mie/core/` (canon, values, vocab, pack, observations, signals, timing, ports, reference, engine) | A domain-neutral, deterministic library. Standard library only (hashlib, json, unicodedata, fractions, datetime, re); no clock, random source, network, file or environment access; no feed call; no APG import. Twelve operations (OP-01 to OP-12) over a closed pack schema (`mie-pack-1`), exact values (`{mantissa, exponent}`, no floats), observations with a licence gate, signals that state only what was observed, a first-match decision table with a closed predicate language, the signal-influence policy, replay by stored evidence, and a per-tenant audit sequence: validate, compute, append the audit event, commit, return. |
| The ports | `mie/core/ports.py`, `mie/core/reference.py` | Everything the core needs from its host is an outbound port: context, observation store, pack registry, result store, audit append and audit query, approvals, the cost-value hook slot, limits. The reference ports are in memory and labelled non-production (EDR-37). |
| The synthetic pack | `mie/packs/synthetic.py` | "TEST FIELD (SYNTHETIC)": invented identifiers, BUY and SELL, the SIGNAL_RULES profile, every value TEST-ONLY. It shows that a second field runs on the same core code, unchanged (SY-01 to SY-03, SY-06). |
| The construction pack | `mie/packs/construction.py` | BUY only, CONTEXT_ONLY (no rule may use a market signal until the Section 08 change request is decided), structure only. `owner_inputs_from_m6_policy` takes from the tenant's M6 procurement policy exactly what it already holds (the watched materials and the buy-timing freshness limits); everything else stays null for the owner. |
| Adapters | `mie/adapters/feed.py`, `m6.py`, `apg_host.py` | The observation-feed flow outside the core (ingestion driver, feed adapter, source port); the M6 mapping (BLK-02, I-121) from stored M3/M6 records and from the M6 MarketFeedPort; APG's verified context as the core's tenant context. |

**How M6 was reused and generalised.** The core does not import M6 (the isolation gate forbids it), so the reuse is of M6's rules, generalised to any field, plus direct use of M6 through the adapters:

- **Freshness.** M6's freshness gate (`apg/mkt/fresh.py`) judges evidence against a decision-specific threshold from the procurement policy, with no default. In the core this becomes a pack freshness limit per observation class, again with no default. A request limit is allowed only for a class the pack does not limit, and an invalid request value counts as not supplied (FRESHNESS_LIMIT_MISSING).
- **Expiry and qualification.** As in M6, the last valid day is still valid. Expired evidence stays as labelled history and never supports an unqualified result. Stale or missing evidence makes the result QUALIFIED, with the reasons listed.
- **Indices, conversions and the feed.** As in M6, an index is a movement series, never a price. An FX rate becomes a declared conversion series with its own movement signal. The M6 MarketFeedPort rules become checks at `submit_observations` and assessment, and FL-10 runs them through the real M6 reference feed: licence states, an exact repeat counting as one observation, conflicting dates reported rather than chosen, nothing after the as-of date, malformed rows dropped.
- **Approvals.** M6's approver-is-not-proposer rule becomes the activation rule: the approval is verified per tenant and exact pin, and the pack's author may not approve it.
- **Scenarios.** M6's caller-supplied scenario paths become caller scenarios, labelled ASSUMPTION and never derived from history.

## 2. Tests and checks (all run fresh by the build; logs in `logs/mie1/`)

| Check | Result |
|---|---|
| MIE-1 unit tests | 234 tests in 15 files: the core with the synthetic pack only (12 files, 200), the feed flow and portability (11), and the construction pack on Builder Zero (23) |
| Whole unit suite | 2,518 tests: the 2,284 M2 to M7.3 tests, unchanged, plus the MIE-1 tests (`tools/run_mie1_all.py`, groups 9 to 19) |
| Static checks | 8 of 8: neutrality against the deny list (NE-01), imports (NE-02, NE-03), field names (NE-04), operations (NE-05), no clock, random, network or file access (NE-06), no feed call (FL-01), no APG module importing the core (IG-01), no MIE module importing APG (IG-05) |
| Planned cases | All 175 cases of MIE1_TEST_STRATEGY accounted for: 164 by a named test, 6 by a named tool step, 5 not applicable (they check the specification package itself). The full map is in `programme/MIE1_CASE_COVERAGE.csv` (`tools/mie_coverage.py`) |
| Mutation run | 608 mutants over canon, values, pack, observations, signals, timing and engine (every comparison, and/or, not, raise and integer +/- site): 605 killed, 3 documented as equivalent with a proof, 0 unexplained survivors. The first full run left 82 survivors; they were boundary and branch gaps, closed by `tests/test_mie_core_canon.py` and `tests/test_mie_core_boundaries.py` |
| Sabotage | All 60 entries of the MIE-1 sabotage catalogue (SB-01 to SB-60) caught, each by its named test file, the static checks or a regression step. The first full run missed two: SB-26 was pointed at the wrong test file, and SB-25 found a real gap (no test showed that two value bases never form one series), now closed by a UT-04 test |
| Golden Builder Zero run | `regression/mie1/golden_mie1.json`, deterministic, with an identical replay |
| Regression against M7.3 | `tools/run_regression_mie1.py`: every M7.3 file byte-identical except README.md, RUN_COMMANDS.txt and four programme tables (rows appended); no APG application file or existing test changed (IG-04) |
| Isolation | IG-02: the M6 and M7 golden Builder Zero outputs are byte-identical between a process where the core cannot be imported and one that has run the construction pack on the same data first; the mapping never writes to the APG store or its audit chain |

## 3. The Builder Zero run (every owner input TEST-ONLY)

The construction pack, completed with the M6 policy part and TEST-ONLY owner inputs (units, markets, sources, licences, movement parameters, an order-lead parameter of 90 days and a three-rule CONTEXT_ONLY table using only the required date), is registered, approved and activated for `zero_one` through APG's verified context. The stored market and FX records are mapped: 72 messages, all accepted: 52 index observations (MAT-STEEL 19, MAT-REO 19, MAT-CU 14; MAT-PBOARD is watched but has none) and 20 AUD/USD rates. The 19 MAT-TIMB records are reported as not mapped, because MAT-TIMB is not a watched material.

- **MAT-STEEL, BUY, required 2026-12-01, assessed 2026-09-30.**
  - Days to the required date: 62.
  - Index movement: UP. AUD/USD movement: UNCHANGED.
  - Outcome: ACT_NOW from the TEST-ONLY rule "the required date is within the order lead time". Signal influence: NONE.
  - Qualification: UNQUALIFIED. The replay is identical.
- **The same request without a date.** NOT_ASSESSED, CONSTRAINT_MISSING.
- **MAT-PBOARD, BUY, required 2026-10-15.**
  - Builder Zero has no plasterboard index, so the required index evidence is NO_EVIDENCE and the result is QUALIFIED.
  - The outcome is still ACT_NOW: the AUD/USD conversion declared for every material counts as usable evidence.
  - This reading is recorded as I-123, with what changes if it is wrong.

These outcomes are the result of TEST-ONLY rules and values. They are not guidance, and no APG finding or recommendation consumes them.

## 3a. A defect found and fixed during the build

The M6 MarketFeedPort reports no retrieval date for an observation. A first run of FL-10 therefore had every M6 feed observation rejected (`retrieved_at` missing). The M6 feed adapter now asserts the retrieval date from the integrator's clock, on the adapter side (I-124). The core still checks only that the retrieval date is not earlier than `as_of`.

## 4. Not implemented

- **PSA02-D2.** `specification_ref` and `methodology_ref` on observations, and the rejection of a mismatch.
- **DECLARATION_CHANGED and re-attestation of a pack.**
- **The P1 normal form.** It is not approved (OD-06).

Each depends on a decision that is still open, and no placeholder code stands in for any of them (SR-108, I-122).

## 5. Files changed and added (compared byte for byte with the delivered M7.3 ZIP)

**Changed (6)**

- `README.md` and `RUN_COMMANDS.txt`: an MIE-1 section above the M7.3 text.
- Four programme tables, with rows appended and no existing row changed:
  - `STATUS_REGISTER.csv` (SR-105 to SR-108);
  - `INTERPRETATIONS_REGISTER.csv` (I-118 to I-124);
  - `ENGINE_HANDOFF_REGISTER.csv` (EDR-37);
  - `CARRIED_FORWARD_REGISTER.csv` (CF-36, CF-37).
- The rows are made by `tools/make_mie1_registers.py`.

**Added**

- `mie/` (core, packs, adapters, neutrality deny list).
- `spec/MIE1_SPEC_v0.3/`.
- 15 test files `tests/test_mie_*.py` and 2 helpers.
- Tools:
  - `tools/mie_static.py`, `mie_coverage.py`, `mie_mutants.py`;
  - `sabotage_mie1.py`, `run_regression_mie1.py`, `run_mie1_all.py`;
  - `run_golden_mie1.py`, `make_mie1_registers.py`.
- `regression/mie1/`: the M7.3 manifest, the M7.3 table snapshot and the golden file.
- `logs/mie1/`.
- This record, and `programme/MIE1_CASE_COVERAGE.csv`.

No APG application file and no existing test changed. The per-release tools of M7.3 and earlier describe their own release. Run in this package, `tools/run_regression_m73.py` reports the MIE-1 files as undeclared; run it on the delivered M7.3 ZIP.

## 6. What the auditor is asked to check

1. Run `python3 -I tools/run_mie1_all.py --range 1-8`, then the whole suite in its counted parts (`--range 9-19`).
2. Run the mutation run in slices (`tools/mie_mutants.py --only PK --jobs 2`, and so on). Check the three documented equivalents.
3. Run the sabotage cases (`tools/sabotage_mie1.py --only SB-nn`).
4. Review I-118 to I-124 and the M6 mapping (BLK-02).
5. Confirm that the open gates in CF-36 and CF-37 are correctly stated.
