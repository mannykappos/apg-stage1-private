## Review responses

Every finding of the three reviews of draft 1, and where this revision answers it. All are accepted except where the response says otherwise.

| Finding | Where answered |
| --- | --- |
| GPT B1 guarantees not testable; supply path missing | The requirement and the two guarantees |
| GPT B2 specified vs delivered blurred | What is specified, what exists, what is unverified |
| GPT B3 contracts list record kinds, not fields and states | The insight contracts |
| GPT B4 four missing kinds understate the data model | The data model gap analysis (45 entities, 11 missing, by class) |
| GPT B5 template coverage not established | Specified table: 36 templates found, all synthetic Builder Zero layouts unverified against real exports; `FIELD_REGISTER.csv` |
| GPT B6 controls per path | One intake contract for every path |
| GPT S1 recognised margin basis | Insight contracts, recognised margin; foundation decisions in the register. Note: the margin module builds on the revenue and cost modules, so "reads project only" in the inventory is not itself a gap |
| GPT S2 commitment rule | Insight contracts, committed cost; commitment policy in the register |
| GPT S3 forecast governance | Insight contracts, forecast final margin |
| GPT S4 R01, R02, R09 mapped separately | Insight contracts (provisional until the rule code is inspected) |
| GPT S5 invoice matching, not same-day posting | Insight contracts, R03 |
| GPT S6 R04, R04b from names | Insight contracts (provisional; next steps) |
| GPT S7 retention, security and carrying cost; `retention_event` | Three separate contracts; `retention_event` is created by APG (`apg/fin/cash_states.py`), not supplied by the builder |
| GPT S8 compliance evidence | Insight contracts, R06 |
| GPT S9 quote comparability | Insight contracts, R07 |
| GPT S10 plant idle evidence | Insight contracts, R08 |
| GPT S11 delay: event vs quantified cost | Insight contracts, two levels |
| GPT S12 labour inputs and fairness | Insight contracts, labour productivity |
| GPT S13 quality lifecycle | Gap analysis (APG internal records) and insight contracts |
| GPT S14 cash-adjusted margin | Insight contracts; not assessable until claim and receivable records exist |
| GPT S15 matrix omits data groups | The data model gap analysis |
| GPT S16 source locations are assumptions | Source profiles: likely locations, to be validated |
| GPT S17 readiness states too generic | Readiness: three separate states |
| GPT S18 readiness only at refresh | Readiness: when it runs |
| GPT S19 integration map incomplete | Source profiles and integration mapping |
| GPT S20 estimates of inputs vs outputs | Estimates |
| GPT S21 decision list incomplete | Decisions: required before production |
| GPT S22 discovery gate | Status line at the top; decisions |
| GPT O1 actionable report | Readiness: fix-first list |
| GPT O2 accept vs verify | One intake contract: five coverage steps |
| GPT O3 data owner column | Gap analysis "likely data owner"; readiness: owner by role |
| GPT M1 good level mixes measures | Insight contracts: four separate measures |
| GPT M2 capability states | Specified table and the five coverage steps |
| GPT estimating table | Adopted in Estimates |
| Gemini design 1: CSV-heavy; email and mobile capture | One intake contract: email/document and phone capture as main paths |
| Gemini design 2: subcontractor claims; cost-code map; data ownership | Gap analysis (subcontractor claims, cost-code map); readiness owner by role |
| Gemini design 3: nudges, not a dashboard | Readiness |
| Gemini design 4: freshness levels | Insight contracts (adopted as proposals) |
| Gemini design 5: run-rate estimates | Estimates (provisional only, builder accepts or overrides) |
| Gemini design 6: cost-code decision | Decisions 2 and 3 |
| Gemini design 7: frame gaps as profit risk | Readiness, worded so a gap is never called confirmed leakage (S06 §4) |
| Gemini evidence 1: R04/R04b | As GPT S6 |
| Gemini evidence 2: guarantee wording | As GPT B1 |
| Gemini evidence 3: new kinds need an amendment | Decision 2; the new entities go through the blueprint's controlled change governance (S18), under a new number (CR-06 is taken) |
| Gemini evidence 4: freshness | As Gemini design 4 |
| Gemini evidence 5: cross-references | Kept; the full matrix cross-check remains a next step |
