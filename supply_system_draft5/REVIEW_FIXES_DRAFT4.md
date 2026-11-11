# Builder's answers to the GPT and Gemini design reviews of draft 3 — BUILDER-WRITTEN

Draft 4 is the design after these changes. "Fixed" means the text or plan changed; "answered" means the point is accepted in part or declined, with the reason.

## GPT design review (30 points; its totals table lost its class labels; the counts 2, 23, 3 and 1 sum to 29, and the labels blocking, should fix, optional and minor are Claude's inference)
Note: GPT reviewed the Word file, not the pack: it checked no numbers, code or blueprint text. Points 28 and 29 say material was missing that is in the pack (05_inputs/blueprint: Section 18 and Section 04 with PG-DI-AC-01..18).

| # | Point | Outcome in draft 4 |
| --- | --- | --- |
| 1 | Entity coverage is not field coverage | Fixed in part in draft 4, completed in draft 5 (per-kind check, plain words, limits incl. settings; AC-12 a release A gate): new "Field-level coverage" (build_field_coverage.py, FIELD_COVERAGE.csv: every named field of a supplied record carried by a template today, other items each with a supplier, no gap; limits stated); PG-DS-AC-12; purpose rule 2 reworded. |
| 2 | Release A completeness not shown for M6 | Fixed: M6 contracts written, approved and field-checked are a gate before release A is complete. |
| 3 | One identical processing loop is a bottleneck | Fixed: one envelope and control checkpoints, processing specific to each kind. |
| 4 | Migration can change results; make it a hard gate | Fixed: separate milestone, regression baseline first, differences signed off, nothing relies on it until it passes. |
| 5 | Authority conflicts | Fixed: authority scoped by organisation, project, kind, field, period; conflicts held for a person. |
| 6 | AC-02 too broad | Fixed: equivalence defined after canonical mapping (values, units, currency, time, tax basis, authority, verification). |
| 7 | "Derived" mixes calculated and confirmed records | Fixed: "Records APG calculates" vs records a person confirms. |
| 8 | Entity resolution risk | Fixed: uncertain or material matches held until a person confirms. |
| 9 | Generic forms feel like a database | Fixed: one form engine, task-shaped layouts per record kind. |
| 10 | Recommended release A too much before value | Fixed: progressive delivery; recommendation changed to a middle path. |
| 11 | File-dependent inputs may not be obtainable | Fixed: template fallback "not effortless"; discovery confirms each file; readiness shows gap and fallback. |
| 12 | Phone capture may be too late | Fixed: early discovery gate for site capture and offline need. |
| 13 | Location and shared devices | Fixed: place provenance, device location not assumed reliable, signed-in user on shared phones, worker visibility, disputes via correction route. |
| 14 | Too many setup questions upfront | Fixed: progressive setup; N01 pre-set defaults. |
| 15 | Batch verification | Fixed: batch verification keeping per-value confirmation. |
| 16 | Migration as separate milestone | Fixed in part in draft 4, completed in draft 5 (direct writes taken out of the migration); with 4; other release A items do not wait for it. |
| 17 | Real construction files | Fixed: multi-sheet etc.; file families proven on pilot files; unsupported shown; programme relationships and calendars kept. |
| 18 | Scanning not enough | Fixed in part in draft 4 (text), completed in draft 5 (AC-07 widened): safe isolated parsing; size, archive and resource limits; malformed files rejected with a reason. |
| 19 | Sender is not authenticity | Fixed: original kept; sender identity separate from document authority (S04 §5, §12). |
| 20 | Integration selection gate | Fixed: four tests (use, API or export, data quality, effort saved). |
| 21 | Fallback not equivalent in timing | Fixed: retrospective marking; readiness qualifies the insight. |
| 22 | Readiness scope | Fixed: item scope (project, organisation, supplier, portfolio, external); shared gaps raised once. |
| 23 | Reassessing per row | Fixed: per batch or material change, queued and combined; AC-09 updated. |
| 24 | Holder vs owner vs approver | Fixed: holder, action owner, approver; builder assigns roles. |
| 25 | Gap lifecycle | Fixed: open, assigned, awaiting evidence, resolved, suppressed, reopened, superseded; identity by entity, field, period, source. |
| 26 | Reason per gap | Fixed: reason list per gap. |
| 27 | Example nudge role | Fixed: "assigned cost-code owner"; role configurable. |
| 28 | PG-DI criteria not verifiable | Answered: they are in the pack (05_inputs/blueprint/S04.txt §19). The EDR-22 vendor requirements and the AUIF contracts are not in the pack and remain dependencies (stated in draft 5). |
| 29 | Section 18 mapping not verifiable | Answered: Section 18 is in the pack (05_inputs/blueprint/Section_18.txt §8); the mapping follows the agent re-check's correction (its point N7). |
| 30 | Pilot adoption measures | Fixed: "Adoption" under Not proven. |

## GPT note: a governance and lifecycle section
Fixed: new section "Data supply governance and lifecycle" (who supplies, checks, corrects, approves, is accountable; outside data via the builder, no portal; corrections and versions; access boundaries; failed supply; builder effort; evidence trail). Data retention and close-out: listed as a gap in the locked blueprint, own change request.

## Gemini design review (7 points)
| # | Point | Outcome in draft 4 |
| --- | --- | --- |
| 1 | Migration regression risk (blocking) | Fixed with GPT 4/16. |
| 2 | Document capture without the extraction vendor (blocking) | Fixed: release A recommendation is document upload with person-keyed verification (quote readings, evidence); finished capture waits for EDR-22. |
| 3 | Five synthetic M6 templates by hand | Answered: no benchmark defaults (they are facts from real quotes; APG never invents a missing fact); instead asked for only when a builder uses the market insights. |
| 4 | N01 configuration burden | Fixed in part in draft 4, completed in draft 5 (items without a default, approval of defaults, reasons): pre-set defaults the owner approves; adjusting optional. Not tied to one state's contract forms. |
| 5 | Recommended release A over-scoped | Fixed in part in draft 4, completed in draft 5 (ways in for the M6 supplements, E83, second-person confirmation): middle-path recommendation; decision 2 lists three options. |
| 6 | Unmapped cost codes stall intake | Fixed: record completes intake, held "pending cost-code mapping" only for figures needing the code. |
| 7 | Subcontractor claims priority | Fixed as decision 7: E17 to E19 are in "later" by the mechanical rule (Claude's earlier chat message wrongly said release B; corrected); promotion recommended together with the back-to-back check, since no current rule reads them (draft 5). |

## Gemini's five further ideas
Listed under "Ideas raised by the reviewers, not designed here", each as its own change request. One-tap actions without sign-in not recommended (breaks S04 §6 and PG-DS-AC-05); the safe form (link to the form after sign-in) is in the design. Learning cost-code map only within one builder's data (S04 §16).
