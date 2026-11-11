# Data design change request: working notes (owner asked 2026-11-11 18:01-18:14; started 18:15)
Owner's ask: APG must know exactly what data it needs, tell the builder, and fill gaps (e.g. builder system gives 80%, APG
features provide the other 20%). "Make sure it's 100%". Route: draft CR -> GPT single-pass review -> owner decides. Stage 1 first.
Agreed framing: fail-proof on our end = APG never gives a wrong/overconfident answer because data was missing, and always says
what it lacks; coverage matrix proves (or disproves) that existing APG features fill the gaps.

## Already locked in the blueprint (v1.0) -- the CR extends, does not repeat
- S04 s14 freshness/completeness by source/project/domain/decision use; suppress/qualify/downgrade recommendations when inputs
  stale or missing; visible warnings. s10 no invented values/silent defaults. s18 manual uploads and controlled entry (same controls;
  spreadsheet column mapping, row-level errors). s9 quarantine vs labelled provisional. s12 AI/OCR values need human verification.
  s5 field-level Source Authority Register. s4 source registry (fields supplied, cadence, limitations).
- S05 s5/5.2 qualified/provisional forecast when CTC inputs missing; show evidenced/estimated/stale/missing/scenario per value;
  s15 asks for a calculation catalogue listing each metric's inputs (implementation instruction).
- S06 data-integrity findings distinct from leakage; absence of alert is not proof.
- 8-layers blueprint 11_DATA_CONTRACTS: logical entities (Project, FinancialRecord, EstimateLine, Baseline, Assessment, Variation,
  Alert, Scenario...).
## What the CR adds (the gap)
1. Per-insight data contract (each insight -> required inputs, freshness, minimum/good level, behaviour per level).
2. Builder-facing readiness report ("what APG needs") at setup and each refresh, in plain words, per insight on/qualified/off.
3. Gap-filling paths mapped to every required input (existing templates; in-app quick entry; phone/site capture CR-05; setup Qs).
4. Coverage matrix: input -> typical source systems -> existing APG feature -> gap? (checked against the code).
5. Per-software integration coverage maps (Section 01 discovery / CR-07).
6. Estimate labelling and confidence levels; never silent.
## Existing code inventory (tree c9b324eb-equivalent, apg/)
- 35 canonical entities, each with a CSV import template (TPL-BZ-*) and the S04 pipeline (new/duplicate/revision/stale/conflict;
  accepted/warnings/pending/quarantined):
  - ingest/specs (M3): supplier, ap_invoice, credit_note, payment, purchase_order, po_amendment, supplier_quote, pm_invoice,
    budget_line, fx_rate, market_observation
  - fin/intake (M4): project, contract, variation, ctc_line, retention, security, facility, bank_txn
  - det/intake (M5): compliance, notice, delay_event, plant_hire, timesheet, work_output, defect
  - mkt/intake (M6): material, material_demand, delivery, spec_requirement, quote_reading, quote_tier, quote_term,
    landed_assumption, import_check
- Also: source_authority.py, ingest/freshness.py, ingest/documents.py, ingest/review.py, ingest/mapping.py, fin/figure.py,
  values.py, status_model.py, rec/inputs.py (recommendation action kinds).
- Preliminary possible gaps to verify: programme activities / percent complete (progress); payment claims / payment schedules
  (SOP Act); labour rates/award costs; site diary; estimate lines (8-layers EstimateLine) vs budget_line; in-app entry UI (apg_ui
  is a prototype: plain.py, viewmodel.py); live connectors (none; AUIF / Amir).
## Next
- Read S03 (domain), S06-S13 inputs per insight; build the insight list and the matrix; check each entity's fields.
- Deliverable: a Docs document (CR draft) + the matrix (Sheets?) -> GPT prompt (single pass, classed findings).
- Sections 07, 09, 11, 12, 13 also lock "missing/stale -> qualified result or blocker, never false precision" (S07 holding cost:
  rates, eligible duration, counterfactual; S09 productivity needs comparable baseline; S11 deadlines traceable; S12 cash forecasts
  state as-of, freshness, gaps; S13 savings need baseline). So the fail-safe principle is locked; the CR adds the builder-facing
  "what APG needs" contract, readiness report, gap-filling and the coverage proof.
- S09 inputs: programme, timesheet, payroll/cost, progress, procurement, quality, subcontractor. S07 needs schedule logic,
  dependencies, calendars, progress -> no programme/progress entity in intake today (candidate gap).
## The doc
- Docs artifact https://claude.ai/artifact/TgphrwwwbtDqdjgfX2Pxh8 ; project d81d02d9-af7d-4d55-8d96-f4d04b851a13 ; body node 06784e63-77d0
- Filled: s1 requirement, s2 already-locked table (rev 4). Pending ids: s3 .316 contract, s4 .317 matrix, s5 .318 readiness,
  s6 .319 gap filling, s7 .320 estimates, s8 .321 integration, s9 .322 decisions (prefix mb3aztskjgw).
- 19:05 First draft complete (all 9 sections, rev 11). Remaining before GPT: field-level matrix check; check contract rows vs rule
  specs (R04/R04b described from names); cross-check MASTER RTM + 8-layer contracts; map a real builder export.
- Matrix found 4 missing record kinds: programme/progress; client claims/payment schedules/receipts; labour rates; estimate lines.
  No entry screens (apg_ui read-only prototype); no site capture; documents.py to check; no connectors.
