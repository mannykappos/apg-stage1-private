## One intake contract for every path

Every way data enters APG passes the same Section 04 controls; no screen, setup answer, email or estimate is a way around them (S04 §18).

Each path must keep: the source and its evidence; identity and duplicate handling; project and tenant scope; field-level source authority; validation; reconciliation; the record's status; reviewer and approval state; audit history; freshness.

| Path | What it fills | Extra rule for this path | Exists today |
| --- | --- | --- | --- |
| Integration through AUIF | recurring feeds from the builder's software | a versioned source profile (below) | no connectors (Amir, at the end) |
| Email and document capture | claims, payment schedules, variations, quotes, invoices, compliance documents | material values extracted by AI/OCR stay provisional until a person confirms them, one tap per document (S04 §12) | partly (`apg/ingest/documents.py`) |
| Phone site capture (CR-05) | progress, delays, defects with photos, plant and labour on site | the person, time and place recorded as evidence | no |
| Entry screens | small, frequent gaps: one forecast line, one variation, one delay | entered values carry the person and need approval where the register says so | no |
| Import templates | bulk data from spreadsheets and exports | each builder's layout mapped and checked once; row-level errors | mechanism yes; templates are synthetic layouts |
| Setup questions | policies and rates: margin and revenue basis, commitment rules, tax, holding-cost and labour rates | versioned; owner approval where the decision register requires it | partly (policies in code, no builder questions) |

Coverage of each input is recorded in five steps, not one: capture available, validation available, authority established, reconciliation available, decision-eligible. A template that accepts a value does not by itself make it correct.

## Estimates

APG may estimate a derived result from disclosed assumptions; it must never invent a missing authoritative fact. Four kinds of value are kept apart: estimates of a missing source fact, builder-supplied forecasts and assumptions, APG-derived qualified calculations, and scenarios.

| Method | Position | Conditions |
| --- | --- | --- |
| Builder-entered cost to complete or forecast | allow | labelled forecast, versioned, dated, attributed to its owner |
| Deterministic calculation from evidenced inputs | allow | formula, inputs, authority, tax/currency basis and version kept |
| Run-rate projection of a stale cost to complete (Gemini) | allow as provisional only | labelled "estimated: run-rate projection", never the authoritative forecast, accepted or overridden by the builder in one step (S05 §5.1–5.2) |
| Holding cost | allow conditionally | S07 and S12 evidence gates met |
| Landed cost | allow conditionally | S08 inputs sufficient; omissions disclosed |
| Indicative market comparison | allow conditionally | source and date visible; stale evidence qualified |
| Scenario | allow | isolated from the authoritative forecast |
| Progress inferred from claims | not as progress | a claim is not proof of physical progress; at most a labelled investigative indicator |
| Labour cost from generic award rates | not as cost | only the builder's verified classification and rates |
| Contract value, claimed amount, approval, deadline or entitlement inferred by AI | never | source evidence and human verification only |
| Carrying cost from face value alone | never | S12 needs the eligible balance and period |

## Source profiles and integration mapping

For each builder software product, a versioned source profile records everything S04 §4 requires, so a builder's gaps are known before they sign up.

- **Contents:** fields supplied and their mapping to APG fields; authority per field (linked to the Source Authority Register); authentication and permissions; transport, cadence, batching and rate limits; schema version; duplicate, retry and error handling; known limits; last receipt, reconciliation and health.
- **Its output** is the readiness forecast for that product: which insights it can feed, and which gaps another path must fill.
- **First profiles** come from sample exports of the pilot builders' systems. A mapped export is a mapping exercise, not proof of a live connector.
- **"Where builders usually hold it"** in the gap analysis is a list of likely locations, to be validated with pilot builders; no coverage promise is made from it.

## Decisions for the owner

**Now, to set the direction:**

1. Adopt the two guarantees as APG's definition of "fail-proof on our end".
2. Approve the data model scope: the 11 missing entities and the partial ones in the gap analysis, split into what builders supply and what APG maintains.
3. Approve as required features: email and document capture, phone site capture, entry screens, the cost-code map at setup, nudges to named roles, and the readiness view.
4. Set the freshness levels (the table holds proposals).
5. Approve the estimating table above.

**Required before production** (a register, decided as each part is designed):

- the ten shared financial foundation decisions (8-layer 02 §2.11): margin measures, revenue basis, cost taxonomy, contingencies, tax basis, cost-to-complete method, variation treatment, approval roles, freshness rules, rounding and currency;
- the Source Authority Register and who approves it;
- baseline and assessment governance;
- the commitment policy;
- labour data privacy and role permissions (S09 §14);
- retention and security state handling;
- the contractual and accounting policies each insight's contract names.

**Next steps after the owner's decisions:**

- Inspect each rule's code and tests against its contract (every "provisional" row), and generate a full field-level schema register with validation rules and tests.
- Map one real builder export (the profit autopsy data) into a first source profile.
- A scoped re-check by GPT against its 33 findings and Gemini's, then the owner decides; no further review rounds unless that check finds a blocking issue.
