# APG Data Readiness Change Request (revision 2)

Nov 11, 2026 · Emmanuel (product owner) · drafted by Claude

APG must know, for every insight, exactly which data it needs, check what each builder supplies, say plainly what is missing and who can supply it, and offer a working way to supply each gap inside APG; until a gap is filled, no insight may present a result its evidence does not support. This revision answers the three reviews of draft 1 (GPT, 33 findings; Gemini, two passes); "Review responses" at the end maps each finding to its fix.

**Status:** design direction only. It authorises no production feature code or integration work: under S04 §20 that waits for the Section 01 Discovery Exit Report and the owner's decisions below.

## The requirement and the two guarantees

The owner's requirement (2026-11-11): APG must state exactly what data it needs; when a builder's software supplies only part of it, APG's own features must supply the rest, so APG gets what it needs to work.

"Fail-proof on our end" means two guarantees about evidence and decisions, not a promise that every answer is correct:

1. **No result beyond its evidence.** For every insight, APG identifies the inputs its blueprint rules require (fields, status, source authority, freshness) and which of them are present, absent, stale, conflicting, quarantined, provisional, unverified or estimated. A result is shown only at the eligibility its own blueprint gate allows: eligible, qualified, blocked or unavailable. A gap is never silently treated as satisfied, and an estimate is never shown as a fact.
2. **A way to supply every gap.** For each missing input, APG names it, says who in the builder's business normally holds it, and offers a working way to supply it inside APG; where no supported path exists yet, it says so plainly instead of implying one.

Both are testable: each insight's gate, each status and each supply path can be exercised with planted gaps, as the stage 1 evidence does for the calculation core.

## What is specified, what exists, what is unverified

The locked blueprint already requires the fail-safe controls; the code holds parts of them; none of it is yet verified against a real builder's data.

| Requirement | Specified in | Present in the code (builder inventory) | Not yet established |
| --- | --- | --- | --- |
| No invented values or silent defaults | S04 §10, PG-DI-AC-11 | Intake pipeline outcomes (accepted, warnings, pending, quarantined) | Behaviour on real exports |
| Freshness and completeness by source, project, domain and decision use, with decision-aware thresholds | S04 §14, PG-DI-AC-13 | `apg/ingest/freshness.py` (decision eligibility) | Thresholds per insight; scheduled reassessment; the builder-facing report |
| Quarantine; provisional use isolated and labelled | S04 §9 | `apg/ingest/review.py`, pipeline outcomes | Review screens for the builder |
| Human verification of material AI/OCR values | S04 §12 | `apg/ingest/documents.py`; `quote_reading.verified_by` | Verification queue in the UI; email and phone capture |
| Field-level Source Authority Register; source registry | S04 §4, §5 | `apg/source_authority.py` (synthetic register) | Builder setup and approval of the register |
| Manual entry and imports never bypass the controls | S04 §18 | 36 import templates (one per record kind, plus one alternative layout) | All 36 are Builder Zero layouts, marked "draft - unverified against any real export"; no entry screens |
| Qualified forecast when inputs are missing or stale, each value labelled | S05 §5.2 | `apg/fin/figure.py` (qualified figures), `apg/fin/forecast.py` | The insight-level readiness record |
| Evidence gates for holding cost, landed cost, productivity, deadlines, cash and quality | S07, S08, S09, S11, S12, S13 | Partly, per module | The missing records in the gap analysis below |
| Data-integrity findings kept apart from leakage | S06 §4 | `apg/det/findings.py` | Readiness findings in the builder's report |

## The data model gap analysis

The gap is larger than draft 1's four record kinds: of 45 logical entities the blueprint needs, 2 are covered, 32 partly and 11 are missing, and they split into what the builder must supply and what APG must create.

| Class | What it is | Entities | Missing | Partly covered |
| --- | --- | --- | --- | --- |
| Builder-source records | Facts the builder's systems or people hold | 31 | client progress claims; client payment schedules; receivables and receipts; subcontractor claims, assessments and payments; estimate lines; programme versions, activities and dependencies; progress | project, head contract, variations, site instructions, notices, subcontracts, purchase orders, invoices, materials, budgets, cost to complete, delay events, labour, plant, defects, bank, retention, security, payables, suppliers |
| Configuration and policy | Set once by the builder, then versioned | 6 | cost-code map; accruals and overhead allocation; labour rates and on-costs | Source Authority Register, holding-cost rates, accounting and contract policies |
| APG internal records | Created and maintained by APG | 5 | quality root cause, rectification and closure records | provenance fields, baselines and scenarios, findings and decisions, the readiness record |
| Evidence and documents | Documents that support facts | 2 | none | compliance evidence; documents and their verification |
| External reference | Market and FX data | 1 | none | none (covered) |

The full analysis, row by row with the blueprint section, the required field groups, the fields present today, the gap, the supply paths and the likely data owner, is in `DATA_MODEL_GAP_ANALYSIS.csv`; the fields present come from `FIELD_REGISTER.csv`, generated from the 36 templates (215 fields).

Two findings matter most for the owner's 80% / 20% question:

- **Claims and payments are the biggest hole.** APG has no record of claims on the client, client payment schedules, receivables, or subcontractor claims, assessments and payments. These are where much construction profit leaks, and where the cash view depends.
- **Cost codes need a map.** APG carries the builder's cost codes as given; every builder codes differently, so a cost-code map is needed at setup: APG suggests it, the builder confirms it (S06 §5.6 keeps AI from changing authoritative inputs).
