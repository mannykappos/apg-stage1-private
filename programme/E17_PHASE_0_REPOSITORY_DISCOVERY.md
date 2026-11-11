# APG Engine #17 — Phase 0 Repository Discovery

**Pack inspected:** `APG_Engine17_Claude_Pack_REV3.zip` (SHA-256 `4482ba3a8ce1cf2f4d1676abeb4c1095408d02fc82f1096fde41486a10f65d25`, 18 entries, 11 documents).
**Date:** 2026-10-15. **Author:** Builder (Claude). **Status of this document:** builder-made discovery, not independently reviewed.
**Edits made to the repository or any frozen package during this phase: none.** One read-only probe was run against a scratch extraction (Appendix B).

Status words follow the pack's vocabulary: *Specified, Drafted, Implemented, Locally tested, Independently reproduced, Integrated, Roadmap / Not started, Blocked / Unverified*. They are not interchangeable. "Locally tested" here means builder-run in this environment.

---

## 1. Result in one page

1. **There is no Engine #17 in the repository, and no code named for it.** The nearest existing code is the M6 procurement layer (`apg/mkt/`) and the M5 finding lifecycle (`apg/det/`). They cover part of Vector 1 (quote comparability and landed cost), part of Vector 2 (over-ordering and duplicates), and a different feature from Vector 4 (a backward-looking rate gap, not forward aggregation). Vector 3 is largely absent.
2. **Of the 27 acceptance gates:** 6 are Implemented and Locally tested (A04, A05, A11, A16, A17, A19), 10 are Partial, 9 are Not started, 1 (A23) is a defect in frozen M5 code, and 1 (A25) is this document. None is Independently reproduced or Integrated. Detail in section 4.
3. **The safe-by-omission position holds.** Nothing in M5 or M6 reports a net benefit, a realised saving or a verified outcome. `claim_saving` and `claim_realised` always refuse. That is why the false-claim gates are not violated today. It is not the same as the gates being built.
4. **A real defect was found in frozen M5 code (new finding, section 7).** An approved action stays approved after the finding's evidence changes. The approval carries no revision or digest. I reproduced this with a read-only probe against the delivered package. It is exactly what gate E17-A23 is meant to prevent. Fixing it means changing frozen M5 files, which is a change-control act, so I have not touched it.
5. **No baseline concept exists in the pack's sense.** `baseline_version_id` and `baseline_hash` appear nowhere in the code. The reusable parts are real: `canon.digest` (SHA-256 of canonical JSON), `repro` (pins input revisions and payload hashes), and `forecast_book.adopt` (human-approved, superseding, history-keeping). But the pack never says *what a baseline is* for each vector. That is a product-owner decision (section 10).
6. **No integration of any kind is proven.** There is no Anchor Engine, no event bus, no migrations, no AUIF or Governor code, and no Engine #18 port. The repository does not use the numbering "Engine #1 … #18" at all (section 9).
7. **The pack's authority is unclear.** It says to implement "under RFC-01", but RFC-01 is still PROPOSED and not approved (`programme/RFC_REGISTER.csv`). The pack also overlaps locked Sections 05 §10 and 06 §12 and the not-yet-started M7 "Recommendations". Per the stop conditions I am stopping at this gate. Decisions needed are in section 10.

---

## 2. Repository and baseline identity (Phase 0 items 1–2)

| Item | Finding |
|---|---|
| Repository | **No git repository and no Anchor Engine repository was supplied.** The only code is the builder's standalone, sandboxed, non-production prototype, delivered as frozen ZIPs. Branch, revision and clean/dirty state do not exist; identity is by archive hash. |
| Inspected code | `APG_M6_CODE_AND_DATA.zip`, SHA-256 `abcfefd9f28464de46dc205c1112b2ea33f537ef4a788562484c1d24109a1efb`, 443 files, extracted fresh into an empty folder |
| M6 documents | `APG_M6_DOCUMENTS.md`, SHA-256 `fa62d60ad33384a83896e05cb10cc34bbd551803d2b9e678aa21683286daaf00` |
| Frozen earlier deliveries | M5 ZIP `4c15ad56…10be6`, M4 ZIP `b1111b01…16606`, M3 ZIP `deca2f99…e64` (unchanged; the M6 regression compares against them) |
| Locked blueprint | Sections 00–18 v1.0, archive SHA-256 `487becabdf47796800937d13a706a19b63b7b8230ecc5354b2f01a647ae5d960` (unchanged). The full documents are not in the workspace; the **RTM v2.1 candidate** (`data/RTM_v2.1_CANDIDATE.csv`, 1,435 rows, SHA-256 `e429227739affb91422d52f5586a96d9289268bf7708b77882717de8b9084a1f`) carries their requirement text, and every row still reads "Not inspected (Phase 0 pending)". This report does not update the RTM. |
| Change-control records | `programme/RFC_REGISTER.csv`, `RFC-01_LATENT_RISK_AND_INTERVENTION_ENGINE.md`; findings F-01..F-51, interpretations I-01..I-58, handoff entries EDR-01..EDR-30, status rows SR-01..SR-61 |
| Baseline check run | `python3 -I tools/run_m6_all.py` from the clean extraction: **ALL M6 CHECKS PASS, 77 s** (Python 3.13.16, Linux). This includes 544 M6 unit tests and 1,752 in all, the 78-case faulty-input corpus, golden cases against the CSV-only oracle, 24 port-contract cases, 25 faulty implementations caught, and the regression against the delivered M5. **This is my re-run of my own package. It is not an independent reproduction.** |
| Not re-run in this phase | The M6 mutation run (879 mutants, 866 killed, 13 documented equivalent) and the M5 re-runs: builder-reported, long, and unchanged by this phase |

---

## 3. What exists, by the pack's four vectors

| Vector | What the pack requires | What exists (evidence) | Status |
|---|---|---|---|
| **1 Pre-commitment value engineering** | Compare specification-compliant alternatives, packages and methods; net landed value including installation, plant, redesign, warranty; commitment and cancellation state | Quote comparability with five classes and a specification gate (`mkt/spec.py:20,120`, `mkt/compare.py:80,199,227`); landed cost with explicit known/missing components (`mkt/landed.py:80–146`); substitution blocks a definitive result (`compare.py` blocker `SUBSTITUTION_NEEDS_APPROVAL`). **Absent:** installation labour, crane/plant, redesign, certification, warranty cost lines; alternative methods or trade packages; cancellation terms | Partial. The quote-comparison core is Locally tested; the net-value part is Not started |
| **2 Quantity reconciliation & waste** | Takeoff, BOQ, revision, order, delivery, installed, waste, returned and reusable quantities as distinct measures; cross-site surplus | Demand vs ordered vs delivered/accepted with unit checks (`mkt/demand.py:94`), over-order MP04 and duplicate MP05 (`rules.py:240,280`). The code itself states that installed, returned and held quantities "are not in the data" (`demand.py:128`, `rules.py:268`). **Absent:** takeoff/BOQ/drawing revision, waste allowance, reusable surplus, transfer economics | Partial, narrow |
| **3 Commercial & payment-term optimisation** | Early-payment discount vs finance cost, deposit staging, retention and alternative security, cash vs margin separation | Deposit and payment-term financing inside scenarios (`mkt/scenarios.py:24,46–100`, policy-configured bps, no default); retention and security instruments held in M4 (`fin/cashview.py`, `fin/cash_states.py`) with overdue-release detection R05 (`det/rules_commercial.py:102`). **Absent:** early-payment discount analysis (no code at all), alternative-security or surety options, liquidity constraint model | Mostly Not started |
| **4 Portfolio aggregation & multi-site leverage** | Aggregate *uncommitted* compatible demand; price tiers; delivery windows; supplier capacity; negotiation brief | `mkt/purchasing.py:19` and rule MP10 compare average rates already paid by authorised projects and label the gap an *indicative estimate*. This is **backward-looking on committed orders**. It is not the specified feature. Volume tiers are used only inside single-quote purchase plans (`landed.py:165`) | The specified feature is Not started; a different, narrower one is Locally tested |

---

## 4. Requirement-to-code matrix: the 27 acceptance gates

"Locally tested" = builder-run tests pass in this environment. Nothing is Independently reproduced or Integrated.

| Gate | Requirement (short) | Status | Evidence | Gap |
|---|---|---|---|---|
| A01 | Versioned baseline | **Not started** (reusable parts exist) | No `baseline_*` identifier anywhere. Reusable: `canon.py:35` digest; `repro.py:101,127` pins input revisions + payload hashes; `fin/forecast_book.py:68` adoption | The M6 reference is "last rate paid", recorded `approved: False` (`opportunity.py:72`). No approved baseline entity |
| A02 | Net benefit reconciles | **Partial** | Gross estimate only (`opportunity.py:66`); `incremental_costs` is a text string "unknown" (`:74`). Scenario costs exist (`scenarios.py:46`) | No net-benefit calculation, no ledger, no double-deduction control |
| A03 | Pre-commitment awareness | **Partial** | Only *uncovered* demand quantity is considered (`opportunity.py:50`, `demand.py:15,94`); commitments in `fin/commitments.py` | No cancellation terms, deposits paid, work-started or switching state |
| A04 | Quote comparability | **Locally tested** | `compare.py`, `spec.py`, `landed.py`, `fx.py`, `fresh.py`; tests `test_mkt_compare/landed/spec/fx_fresh`; corpus; 879-mutant run (builder) | Warranty, certification and delivery-window terms only partly captured |
| A05 | Specification gate | **Locally tested** | `spec.py:120` classify; readings must be verified by someone other than the extractor; `REQUIREMENT_UNAPPROVED` (`spec.py:126`) | Records an approval flag; no workflow for a professional's sign-off of equivalence |
| A06 | Schedule gate | **Partial** | Lead time vs required date and quote validity (`scenarios.py:138`) | Critical-path data absent (`det/rules_ops.py:103` says so). No explicit "not assessed" field on the opportunity; it simply makes no schedule-slip claim |
| A07 | Quantity lineage | **Partial** | See Vector 2 | Takeoff, BOQ, installed, waste, returns |
| A08 | Portfolio aggregation | **Not started as specified** | See Vector 4 | Uncommitted demand, tiers, windows, capacity |
| A09 | No double counting | **Partial** | M5 overlap components and ranges (`det/relations.py:21`, `det/portfolio.py:25`); fixed `$0–$0` display (`portfolio.py:17`) | No overlap groups for opportunities (shared discount, shared surplus, cash vs margin) |
| A10 | Payment-term economics | **Partial / mostly Not started** | Vector 3 | Early-payment discount, security options, liquidity |
| A11 | Uncertainty | **Locally tested** | Labels `estimate`/`indicative`, no percentages; figure states authoritative / provisional / cannot_assess (`fin/figure.py:13`); missing parameter → `not_configured` | Conflicts with the pack's own wording on "confidence" (section 8, P-9) |
| A12 | Decision deadline | **Partial** | MP03 (`rules.py:171`) and `scenarios.timing` (`:138`): earlier of quote validity and latest order date | Approval lead time is not modelled; policy holds only a `decision_window_days` (`policy.py:88`) |
| A13 | Lifecycle & approval | **Partial** | M5 finding lifecycle (`det/findings.py:22–30,266`): human-only, role-gated, rationale, proposer ≠ approver, append-only history, audit. Ingest replay is a no-op | The pack's opportunity states are not implemented. A repeated identical transition is refused, not treated as an idempotent no-op (read from code, not tested) |
| A14 | Closed-loop outcome | **Not started** | `claim_saving` (`opportunity.py:19`) and `claim_realised` (`findings.py:384`) always refuse; `verified_outcome: None` placeholder | Actual cost, reconciliation to proposal and baseline |
| A15 | Attribution honesty | **Not started** | Nothing is claimed, so nothing is mis-attributed | Categories and counterfactual method |
| A16 | Tenant isolation | **Locally tested** | `tenancy.py:76` ScopedStore; tests `test_mkt_detect.py:197–212`, `test_mkt_intake.py:98`, `test_det_detect.py:143`, golden `zero_two` | Project-level permission (F-39, EDR-29) and notification recipients are Engine work |
| A17 | Reproducibility | **Locally tested** | `repro.py`; `mkt/detect.py:21` code hash over every procurement module (a test now pins that coverage) | — |
| A18 | Degraded dependencies | **Partial** | Held/unusable inputs are explicit (MPD1); port contract suites for the feed and extractor (24 cases) | No timeout, retry or backoff for M6 ports; the dependencies themselves do not exist |
| A19 | Notification idempotency | **Locally tested** | `det/noise.py:26`, `findings.py:226`; NotificationPort contract suite (the M5 reviewer reported 12/12 and 15/15 faulty caught) | Real delivery and recipient directory are Engine work |
| A20 | User actionability | **Partial** | Signals carry evidence, missing items, limits, urgency and owner role (`rules.py:191–197`) | No net value, no explicit next action, no evidence-to-prove-outcome field beyond `verification_requirements` text |
| A21 | Offset-cost completeness | **Not started as a gate** | Pattern to extend: landed components with `known` / `assumed` / `missing` (`landed.py:98–146`) | No category ledger; no quantified / not-applicable / unknown / disputed / excluded states |
| A22 | Baseline-change invalidation | **Not started** | Nearest: `repro.drift_report` (`repro.py:157`) lists later revisions of pinned inputs; forecast supersession in M4 | No recalculate / suspend / supersede / expire logic for opportunities |
| A23 | Approval revision binding | **Defect found in M5** | Probe, Appendix B | Approval survives a material change |
| A24 | Engine #18 outcome contract | **Not started** | No port, no EDR entry, no stand-in | Whole contract |
| A25 | Phase 0 discovery | **This document** | — | — |
| A26 | Event baseline binding | **Not started** | Zero hits for `baseline_version_id` / `baseline_hash` | Fields, validator, negative tests |
| A27 | Indirect site-overhead assessment | **Not started** | Cost scope is explicitly supplier invoices only (`fin/costs.py:19`, `det/rules_cost.py:20`); Builder Zero has timesheet and plant files that M4 does not ingest (`tools/make_m4_registers.py:97`) | Time-based overhead evidence, rates, allocation method |

---

## 5. Dependency map (the pack's #1–#18)

The repository never uses this numbering (section 9). I mapped each pack dependency to the nearest existing code by function. **No integration is proven for any of them; no Anchor Engine code was available.**

| Pack dependency | Nearest existing code | Status |
|---|---|---|
| #1 Financial Intelligence | M4 `apg/fin/` (figures with states, cost, commitments, margin, forecast book). Cost scope is supplier invoices only | Implemented, Locally tested, standalone |
| #2 Data Quality, Evidence & Provenance | M2 `source_authority.py`, M3 `ingest/reconcile.py`, `repro.py` | Implemented, Locally tested, standalone |
| #4 Cross-Domain Relationships | M5 `det/relations.py` (overlap components, links). Time-aware graph is RFC-01 "M7", not started | Partial |
| #9 Universal Market Intelligence | M6 `apg/mkt/` quote, FX and freshness logic; the market feed is a test double (EDR-09). **No separate market-intelligence engine code exists** | Partial, stand-in feed |
| #10 Materials & Procurement | M3 ingestion, M4 commitments, M6 demand and orders | Partial |
| #11 Schedule, Delay & Holding Cost | M5 delay-overlap rule only; no schedule network | Roadmap / Not started |
| #12 Labour, Productivity & Resource | M5 productivity rule over synthetic timesheets; labour not in the cost base | Roadmap / Not started |
| #14 Cash Flow & Working Capital | M4 `fin/cashview.py`, `cash_states.py` | Partial |
| #15 Cost of Capital & Trapped Cash | M6 policy parameter `financing_bps_pa`, no default; no approved assumption source | Partial |
| #18 Intervention Efficacy | None | Not started; absent |

---

## 6. Event and baseline contract inspection (Phase 0 items 6–8)

M6 events (`apg/mkt/events.py`, version `apg-event-1`) compared with the pack's minimum fields (section 2 of the architecture file):

| Pack field | In M6 events? | Evidence |
|---|---|---|
| `tenant_id` | Implicit (events live in a tenant-scoped store), not a field | `tenancy.py` ScopedStore |
| `event_id` | **Yes**, content-addressed `EV-` + SHA-256 prefix, re-verified on validate | `events.py:30,51` |
| idempotency key | Partial: identical content gives an identical id; no separate key | `events.py:30` |
| `event_type`, schema version | **Yes** (12 types, `apg-event-1`) | `events.py:13–15` |
| `observed_at` | **Yes**, required | `events.py:42` |
| `effective_at` | Named `effective_from` / `effective_to`; **map, do not duplicate** | `events.py:44` |
| `recorded_at` | **No** | — |
| `provenance_id` | **No** single id; `sources` = list of (record ref, revision) | `events.py:28` |
| source system / source record ID / source identity | Record-level only; field-level resolution lives in M2/M3, not carried into events | `source_authority.py:166` |
| project / material / supplier | **Yes** | `events.py:27` |
| currency, unit, quantity, normalisation | Only inside `detail`, unvalidated | `events.py:29` |
| verification / conflict / freshness state | In signals, not on the event | — |
| correction / supersession / replay semantics | **No.** A correction creates a new content-addressed id; nothing links it to what it corrects | — |
| policy / calculation version | In the run record, not on the event | `repro.py` |
| `baseline_version_id`, `baseline_hash` | **No** | — |

Events are produced inside signals (`rules.py:197`); **there is no event store or bus** (EDR-30, described only).

Other Phase 0 items:
- **Baseline/scope-change behaviour:** changed budgets, quantities or rates do not touch any stored opportunity. `repro.drift_report` shows what drifted; a person must act. No quarantine state exists for opportunities.
- **Migrations and schema:** none. Storage is the `RecordStorePort` (Engine-side). Immutable baseline-hash storage and quarantine flags are **Blocked: needs the Engine**.
- **HTTP 409:** there is no API layer (M9). The store's `ConflictError` (`ports.py:32`, expected-revision conflicts) is the only equivalent.
- **Source Authority bindings:** `source_authority.py` (M2) is Implemented and Locally tested. M5/M6 signals carry record-level references; I found no field-level provenance carried into M6 outputs.
- **AUIF / Governor isolation of AI-extracted candidates:** neither system is in the repository. What exists is M6's `ExtractionRuntimePort` stand-in, where an extracted reading counts only when verified by someone other than the extractor (`spec.py`, I-45). **Blocked / Unverified** for AUIF and Governor.
- **Engine #18 boundary:** no port, interface, mock or register entry. Nothing to mislabel.

---

## 7. New finding in frozen M5: approval is not bound to the revision approved

**Observed (probe in Appendix B, run against the delivered M6 ZIP's M5 code):**
- A finding was confirmed, an action was proposed, and a second person approved it. State: `action_approved`, finding version **1**, signal digest `67a504082f14`.
- A much larger invoice was then added and a new detection run was ingested. The same finding became **version 2**, signal digest `619f1afb69a4`, status still `action_approved`, approver still `abby`.
- The approval record holds only `text, proposed_by/at, approved_by/at`. It has no finding version, signal digest, baseline or proposal hash.

**Why it matters:** the pack's E17-A23 and locked Section 05 CP-05-3 both require approval to follow the exact thing approved. Here a person's approval of "the original figure" silently covers a changed one. Nothing in M5 *executes* the action (it only records), so no money moves, but the record misleads an auditor.

**Proposed handling (not done):** log as a finding for the register (next free id F-52), mark it a defect in a frozen milestone, and fix it as a baseline-changed M5 correction, as F-36 was in M6. The fix is small in outline: store the digest and version at approval, and on a changed digest move the finding to a state that requires re-approval. It needs a decision before I touch frozen files (section 10, D6).

---

## 8. Review of the pack itself

These are defects in the pack as an instruction set. None changes the verdict that it is a good, careful brief.

| # | Where | Issue | Suggested fix |
|---|---|---|---|
| P-1 | Directive | Phase 4 numbering restarts at 17–20, duplicating Phase 3's 17–19 | Renumber 20–23 |
| P-2 | Architecture file | Section numbers run 1, 2, 3, 4, 5, **3**, 7, 8, 9 (second "3", no 6) | Renumber |
| P-3 | Spec §5 vs §4.1 | `UNQUANTIFIED` is both a lifecycle state and a `net_benefit_status` value | Keep it only as a status, not a lifecycle state |
| P-4 | Spec §5 | A third lifecycle. Locked Section 05 §10 already defines 10 benefit states and M5 has 10 finding statuses. The pack says "reconcile" without saying which governs | State that the locked Section 05 §10 states govern benefit accounting and M5 statuses govern review; map the pack's states onto them |
| P-5 | Spec §4.2, Acceptance A01 | Never defines **what the baseline is** per vector (approved budget? contract rate? approved estimate?) or who approves it | Define per vector; product-owner decision |
| P-6 | Architecture §2.1 | Requires `baseline_hash` over a "canonical baseline snapshot" but not what the snapshot contains | Define the snapshot by reference to existing record revisions (which `repro` already pins) |
| P-7 | Known-context file | Stale: says M6 "was intended" (it is now delivered locally) and the `$0–$0` issue "may remain" (corrected in M6, F-36) | Refresh the status lines |
| P-8 | Whole pack | "Engine #1 … #18" numbering has no definition in the repository or locked baseline | Add a mapping table (section 9) |
| P-9 | Acceptance A11 vs Spec §4, Example E | A11 says "confidence scores have a documented method"; the spec says not to assign arbitrary percentages; Example E shows "88% confidence" | Say explicitly that confidence is qualitative unless a method is approved |
| P-10 | Acceptance negative cases | Case 35 alone carries an id (TC-17-NEG-04); the other 38 are bare numbers | Number all |
| P-11 | Acceptance §5 | The "independent oracle" is a builder-written CSV-only oracle in this programme. The pack says "independent" without the caveat the M5 review recorded | Say "second calculation path, not an external audit" |
| P-12 | Spec §4.1 | The 24-category offset list is a checklist but no rule says who decides which categories are *relevant* for an opportunity | Make the relevance decision a recorded, reviewable act |
| P-13 | Spec §3 | GST/tax, rounding, and time value of money are not governed (the Gemini prompt itself asks) | Reuse M6's rules: integer cents, ex-GST comparison basis, round half away from zero once |
| P-14 | Directive | "Authorised RFC-01 scope" is used as if RFC-01 were approved | See D1 |

---

## 9. Conflicts with locked material and the programme

1. **Locked Section 05 §10 / §10.1 (RTM PGR-05-N033..N036, CP-05-3):** already defines the benefit states, the net-benefit formula, and the realised-savings gate (approved versioned baseline + implementation evidence + authorised verification). The pack's §4–§6 restate and extend it. No contradiction found, but it must be built *on* the locked text, not as a parallel model.
2. **Locked Section 06 §12 (PGR-06-N031):** opportunity discovery when budgets are on track already lists supplier pricing/terms, purchase timing, waste, delivery sequencing, productivity, financing and retention.
3. **Locked Section 08 §11 and Section 05 §10:** the M6 opportunity is deliberately an *estimate*, with the last paid rate marked "not an approved baseline" (`opportunity.py:5–8`).
4. **Programme M7 "Recommendations" (CAP-27..30):** "eligibility, prioritisation, scenario isolation and the realised-savings gate" is the same ground as Engine #17's qualification, ranking and verification. RFC-01 also calls its own planned engine "M7" (finding F-47, open). **Engine #17 has no milestone slot.**
5. **Numbering:** "Engine #N" does not appear in the code, the programme tables, the gap map or the RTM. The nearest structure is Sections 00–18 and milestones M0–M12.
6. **RFC-01 status:** PROPOSED, not approved, not a numbered change request.

I have changed none of these.

---

## 10. Decisions needed (they block implementation, not this report)

| # | Decision | Owner | My recommendation |
|---|---|---|---|
| D1 | **Authority and placement.** Is Engine #17 in scope, under which approved change request, and in which milestone? Options: (a) widen M7 "Recommendations" to carry it; (b) add a milestone after M7; (c) hold until after M12 | Emmanuel (product owner), then the auditor | (a), with RFC-01 approved as a numbered change request and the Engine #17 pack attached as its annex. M7's realised-savings gate and Engine #17's verification are the same control and should be built once |
| D2 | **Engine numbering map.** The authoritative list of Engines #1–#18 and how each maps to blueprint sections or modules | Emmanuel / blueprint author | Supply the table; I will keep it in the programme register |
| D3 | **What is the approved baseline, per vector, and who approves it?** (budget revision, approved estimate/BOQ, contract rate, approved quote?) | Emmanuel with the finance owner | Reuse existing record revisions pinned by `repro`, with a human-approved adoption step modelled on `forecast_book.adopt` |
| D4 | **Lifecycle precedence** (P-4) | Emmanuel / auditor | Section 05 §10 governs; no third lifecycle |
| D5 | **Approved inputs the engine must not invent:** cost-of-capital assumptions, overhead allocation rates, relevant offset categories per opportunity type | Emmanuel / finance owner | Keep configuration-only with no defaults, as M6 does |
| D6 | **May I correct the frozen M5 approval defect** (section 7) as a baseline-changed M5 correction? | Emmanuel / auditor | Yes, as the first item of the Engine #17 work, with the change listed exactly as F-36 was |

Standing items are unchanged: DEC-A1-1..8, DEC-MIE-01, CR-02 A1..A13, B7, independent review of the ten classifications.

---

## 11. Proposed plan (draft; nothing started)

Everything below is Engine-independent, standalone and sandboxed, built with the controls used so far: pure functions, no defaults, human-only decisions, reproducible formulas, independent CSV-only oracle, adversarial tests before logic, mutation run, sabotage checks, honest status wording. Each stage is one ZIP plus one docs file, authorised by milestone.

| Stage | Content | Acceptance gates |
|---|---|---|
| **E0** | Decisions D1–D6 and RFC-01 numbered; Engine map; baseline definition | Gate to start |
| **E1 Foundations** | Baseline registry (id + SHA-256 over canonical snapshot, via `canon.digest`); `apg-event-2` (adds tenant, `recorded_at`, idempotency key, correction/supersession links, baseline pair) with a consumer validator; approval-binding fix; baseline-change handler (recalculate / suspend / supersede / expire) | A01, A13, A22, A23, A26; negative cases 15, 27–29, 33–36 |
| **E2 Opportunity record and net value** | The 13-field qualification record; cost-assessment ledger with five states per category; `net_benefit_status`; bounded scenarios only with evidenced bounds; time-based overhead assessment; commitment and cancellation state | A02, A03, A21, A27; cases 4, 25, 26, 37–39 |
| **E3 Vectors** | V3 payment-term economics and retention/security options; V2 quantity reconciliation (needs new synthetic takeoff/BOQ/installed templates); V4 uncommitted-demand aggregation with tiers and overlap groups; V1 alternatives with installation/plant/redesign offsets | A07–A10; positive cases 5–7; negative cases 5, 6, 10–14, 21–23 |
| **E4 Closed loop** | Engine #18 outcome port, in-memory reference, contract suite and faulty implementations (the EDR-08/09 pattern); six outcome classes; replay and correction rules; attribution categories | A14, A15, A24; cases 20, 24, 30, 31 |
| **E5 Verification** | CSV-only oracle over all positives and the 39 negatives (including expected silence), mutation run, sabotage list, regression, clean-extraction check, handoff entries | A17–A20, A25, full matrix |

**Engine-dependent items go to the handoff register for Amir at M12:** live Engines #9–#15 and #18, the event store/bus (EDR-30), database migrations for immutable baseline hashes and quarantine flags, HTTP 409 mapping, AUIF/Governor isolation of AI-extracted data, real recipients.

**RFC-01 change proposal items to record (all PROPOSED):** Engine #17 scope and its overlap with M7; the three-lifecycle reconciliation; baseline entity and hash; `apg-event-2`; the M5 approval-binding correction; the Engine #18 outcome contract; the numbering map.

---

## 12. Limits of this discovery

- I inspected the delivered M0–M6 packages and the pack. I did **not** inspect an Anchor Engine, AUIF, Governor, any market-intelligence engine code, a database, an event bus, or any real builder data. None was available.
- Statuses marked "read from code" were established by reading source, not by a test. Only the approval-binding behaviour was confirmed by a probe.
- Every test and mutation result is builder-run on synthetic data. Nothing here is independently reproduced, integrated, pilot-validated or production-ready.
- The RTM rows remain "Not inspected (Phase 0 pending)"; I did not edit the RTM, the locked sections, CR-09, or any frozen archive.
- I did not act on the Gemini review prompt in the pack; it is addressed to another reviewer.

---

## Appendix A: commands run

```
python3 -I -c "zipfile … extractall"            # pack and delivered M6 ZIP, each into an empty scratch folder
sha256sum  (pack, M6 ZIP, M6 docs)
python3 -I tools/run_m6_all.py                  # from the clean M6 extraction → ALL M6 CHECKS PASS, 77 s
grep -rInE <pack concept> apg tools             # baseline_*, quarantin, supersed, idempot, recorded_at, provenance_id,
                                                # overhead|standby|crane, early.payment, retention, surety, surplus,
                                                # installed, takeoff|BOQ, outcome|VERIFIED_POSITIVE, critical.path, warranty
python3 -I probe_a23.py                         # Appendix B
```

## Appendix B: the approval-binding probe (scratch file, not part of any package)

```python
import sys; sys.path.insert(0, '.')            # run from the clean M6 extraction
from tests.helpers_det import det_world, inv
from tests.test_det_findings import breach, first
from apg.det import findings as FD
m = breach(); fid, _ = first(m)
FD.transition(m.reviewer, m.clock, fid, 'under_review')
FD.transition(m.reviewer, m.clock, fid, 'confirmed', rationale='yes')
FD.transition(m.owner, m.clock, fid, 'action_proposed', action_text='renegotiate the supplier')
FD.transition(m.approver, m.clock, fid, 'action_approved', rationale='approved on the original figure')
f0 = FD.get(m.svc, fid)                                           # version 1
m.clock.advance(3600)
m.invoices(inv('INV-2', sin='SI-2', ex='4000000', cc='CC-01'))   # a much larger overrun after approval
m.reconcile()
out = m.ingest(m.detect(as_of='2026-10-01'))
f1 = FD.get(m.svc, fid)                                           # version 2
```

Output:

```
BEFORE action_approved 1 67a504082f14 abby
AFTER  action_approved 2 619f1afb69a4 abby updated= ['FND-3b24102724f9e17d839d']
approval carries a version/digest? ['approved_at', 'approved_by', 'proposed_at', 'proposed_by', 'text']
```
