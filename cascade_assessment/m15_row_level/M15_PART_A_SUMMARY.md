# M15 row-level check, Part A (Sections 00 to 03)

**INDEPENDENT READ-ONLY (agent).** Design work only; nothing built. Each of the 700 rows of `in/RTM_PART_A.csv` was read one at a time, with the surrounding section text, against `ENTITY_REGISTER.csv` (required field groups) and the M15 heading-level fixes. Row file: `out/M15_PART_A.csv` (700 rows, same order as the input).

## Counts by verdict

| Verdict | Rows |
| --- | --- |
| COVERED | 211 |
| COVERED-BY-PROPOSED | 14 |
| GAP | 73 |
| NO-DATA-NEED | 402 |
| **Total** | **700** |

Rows with a data need (Y): 298. By section: S00: COVERED 25, COVERED-BY-PROPOSED 8, GAP 17, NO-DATA-NEED 94, S01: NO-DATA-NEED 139, S02: COVERED 65, COVERED-BY-PROPOSED 2, GAP 32, NO-DATA-NEED 62, S03: COVERED 121, COVERED-BY-PROPOSED 4, GAP 24, NO-DATA-NEED 107.

Section 01 is discovery and delivery instruction throughout, so all 139 of its rows are NO-DATA-NEED; its post-completion discovery list (S01 3.5) points at the same data judged in S00, S02 and S03.

## Proposed fixes (smallest change that closes each GAP)

Fifteen fixes close all 73 GAP rows. Two are new entities (G5, G11); the rest are field groups on existing entities.

| Fix | Change | GAP rows it closes |
| --- | --- | --- |
| G1 | E01 gains the S03 s3/s11.3 time and actor fields (effective/event time, source-reported time, observed time, recorded/persisted time, valid from/to, created/updated by, organisation and project scope, schema version) | 8: S00-L0069, S02-L0032, S02-L0118, S03-C0014, S03-L0045, S03-C0181, S03-L0224, S03-L0229 |
| G2 | E78 gains currency of face value, collateral, capital or facility usage (link to E74), internal owner, status (active, approaching expiry, release review, released, renewed, disputed) and linked obligations/disputes | 4: S00-L0051, S03-L0149, S03-L0153, S03-L0154 |
| G3 | E66 gains operational impact and links to the affected retention (E75/E76) and security (E78) conditions, with the portion of the balance demonstrably affected | 6: S00-L0053, S02-L0091, S03-L0143, S03-L0154, S03-L0159, S03-L0165 |
| G4 | E08 gains a final-account group (agreed final contract sum, final-account adjustments, status, date agreed) | 2: S02-L0095, S03-L0063 |
| G5 | new entity Closeout obligation (project, obligation type, source clause or document, due date, owner, status open/closed/transferred/waived/resolved, authorising decision E87, evidence) | 4: S00-C0049, S02-L0092, S02-L0094, S02-C0096 |
| G6 | E84 gains affected scope (project, package), time horizon and intervention window (latest useful intervention time), contributing conditions and root-cause hypotheses, lifecycle status with resolution reason, and links to related findings sharing a cause or exposure (overlap marker) | 14: S00-L0014, S00-L0015, S00-L0017, S00-L0031, S00-L0055, S00-L0073, S02-L0050, S02-C0063, S02-L0095, S02-L0117, S02-L0132, S02-L0139, S03-L0192, S03-L0193 |
| G7 | E85 gains assigned owner (person or role), assignment history, deferral (defer-until and reason) and action-tracking state | 5: S00-L0032, S00-L0075, S02-L0051, S02-L0082, S02-L0102 |
| G8 | E86 gains estimated financial effect (current exposure ref, gross benefit, implementation cost, expected net benefit, calculation basis), accountable role, timing (deadline, time to benefit), feasibility, reversibility and downside, and lifecycle status (proposed, under review, approved, rejected, executed, withdrawn, superseded, invalidated) | 19: S00-L0022, S00-L0024, S00-L0031, S00-L0068, S02-L0017, S02-L0019, S02-L0022, S02-L0057, S02-L0058, S02-L0062, S02-L0106, S02-L0119, S02-L0120, S02-C0125, S02-L0141, S02-L0143, S03-L0034, S03-L0190, S03-L0202 |
| G9 | E88 gains outcome classification (realised, partially realised, avoided, reversed, not realised, unverified), baseline used, estimated-versus-realised difference and reasons for material differences | 9: S00-L0017, S00-L0024, S00-L0068, S02-L0022, S02-C0063, S02-L0110, S02-L0111, S02-L0112, S03-L0030 |
| G10 | N01 gains alert settings (grouping rules, escalation thresholds, notification frequency, approved by) | 1: S02-C0145 |
| G11 | new entity Audit event (actor, tenant, time, correlation id, action, subject record, prior and new values or state, access to sensitive data); may map to the platform-native audit mechanism found under S01 Gate 01-C | 4: S00-L0075, S00-L0086, S02-L0031, S03-L0200 |
| G12 | E90 gains per-margin-view definition: included and excluded categories and treatment of unapproved claims, retention and security | 3: S03-C0036, S03-L0047, S03-L0050 |
| G13 | E02 gains market coverage by material category, geography and specification, with freshness per slice | 1: S00-L0066 |
| G14 | E37 gains rate kind (actual, quoted, contractual, scenario); E96 gains conversion details (original currency and amount, target currency, rate used, rate source and time, method, included fees) | 1: S03-C0177 |
| G15 | E45 gains references to the findings and recommendations it produced; E84 gains a reference to the calculation run behind its quantification | 2: S03-L0186, S03-L0229 |

## Every GAP row

| Row | Requirement words | What is missing | Fix |
| --- | --- | --- | --- |
| APG-S00-L0014 | Detect symptoms, contributing conditions and plausible root causes; do not merely report an overrun after it has happened. | E84 has rule, evidence, quantification, confidence, limits but no cause field; E68 is defect-only. | G6 |
| APG-S00-L0015 | Estimate the financial exposure, affected project/package, relevant time horizon, intervention window and evidence supporting the finding. | Exposure and evidence covered by E84 quantification/evidence; scope, horizon and intervention window are not. | G6 |
| APG-S00-L0017 | Track whether an exposure was prevented, mitigated, realised, dismissed or remains unresolved, with reasons and evidence. | No entity holds the resolution state or reason; E88 holds only realised result. | G6, G9 |
| APG-S00-L0022 | Rank opportunities using transparent criteria such as expected net benefit, confidence, urgency, feasibility, time to benefit, downside exposure and reversibility. | Confidence (E84) and priority (E85) exist; net benefit, feasibility, time to benefit, downside and reversibility are not held. | G8 |
| APG-S00-L0024 | Track opportunities from discovery through assessment, approval, action, outcome or rejection; distinguish projected benefit from realised benefit. | Chain of entities exists but no lifecycle status or projected-benefit field. | G8, G9 |
| APG-S00-L0031 | The system prioritises material, timely, actionable findings and provides evidence, assumptions, uncertainty, net financial impact, trade-offs and the latest useful intervention time where supportable. | Evidence/confidence on E84, assumptions on E46; net impact and latest useful intervention time not held. | G6, G8 |
| APG-S00-L0032 | The user receives an appropriately routed alert or work item and can inspect evidence, approve/reject/defer, assign an owner and track the action. | E85 has recipient and state, E87 the decision; no owner, deferral or action tracking. | G7 |
| APG-S00-C0049 | Profit Guardian's monitoring does not automatically end at practical completion, handover or occupancy. Where source records and contractual data are available, it must continue to track relevant commercial, retention... | Retention, security and defects exist, but closeout obligations and their closed/transferred/waived state are not held. | G5 |
| APG-S00-L0051 | Track bank guarantees, performance bonds and other security instruments, including value, beneficiary, issuer, issue/expiry dates, fees/collateral where known, release conditions, dependencies, owner and source. | E78 lacks collateral, dependencies, owner. | G2 |
| APG-S00-L0053 | Connect unresolved defects to applicable retention/security conditions and financial exposure where evidence supports the relationship. Do not assume every contract has identical release conditions or assert legal ent... | Only E76 (trade retention) links defects; E75 and E78 have no defect link. | G3 |
| APG-S00-L0055 | Calculate tied-up capital or delay cost only with declared rates, periods and assumptions. Avoid double-counting principal balances, financing costs, fees and linked defect exposures across findings. | Rates and periods covered (E53, E74, E45); overlap across findings needs links. | G6 |
| APG-S00-L0066 | Do not promise universal or real-time market coverage without verified coverage and permitted access. Track gaps by material category, geography, specification and freshness. | E02 is per source and E89 per insight; no coverage slice by category/geography/spec. | G13 |
| APG-S00-L0068 | Separate actual, committed, forecast, scenario, opportunity, avoided cost, expected net benefit, additional revenue, margin impact and realised outcome. | E96 value status covers actual..scenario; expected net benefit and avoided-vs-realised classification not held. | G8, G9 |
| APG-S00-L0069 | Every material finding must trace to source records/observations, timestamps, units, transformations, assumptions and calculation/rule/model versions. | Sources, versions, assumptions covered; E01 has no timestamps. | G1 |
| APG-S00-L0073 | Prevent double counting between related causes, interventions, packages and scenarios; mark overlap explicitly when it cannot be resolved. | Not carried by E84 (see fix). | G6 |
| APG-S00-L0075 | Maintain an auditable baseline and record user decisions, overrides, action history and outcome evidence. | Baseline, decisions/overrides and outcome evidence covered; action history not held. | G7, G11 |
| APG-S00-L0086 | Record provenance and access for commercially sensitive project, supplier, pricing, contract and financial data. | Provenance in E01; access records not held by any entity. | G11 |
| APG-S02-L0017 | Quantification of financial exposure and potential benefit. | Exposure in E84 quantification; potential benefit not held. | G8 |
| APG-S02-L0019 | Recommendations with evidence, assumptions, trade-offs and deadlines. | Evidence/assumptions via E84/E46; recommendation deadline not held. | G8 |
| APG-S02-L0022 | Verification of actual outcomes against the original estimate. | Original benefit estimate and difference not held. | G8, G9 |
| APG-S02-L0031 | Administrative access must not silently alter financial history. | E01 revision/supersession keeps versions but not who changed what. | G11 |
| APG-S02-L0032 | Where practical and supported by policy, preparation of financial data and approval of consequential financial actions should be separated. | Approver in E87; preparer (created by) not held on records. | G1 |
| APG-S02-L0050 | Check for duplicate or related findings sharing the same underlying exposure. | Not carried by E84 (see fix). | G6 |
| APG-S02-L0051 | Prioritise the finding and assign an authorised owner. | Priority on E85; owner not held. | G7 |
| APG-S02-L0057 | Calculate estimated gross benefit, implementation cost and net benefit. | Not carried by E86 (see fix). | G8 |
| APG-S02-L0058 | Identify uncertainty, timing, dependencies and downside risk. | Uncertainty via E84/E46; timing and downside of the recommendation not held. | G8 |
| APG-S02-L0062 | Track execution and measure the realised outcome. | Realised result on E88; execution status not held. | G8 |
| APG-S02-C0063 | Do not report the same benefit as both avoided cost and realised savings, or count a cost reduction twice through linked findings. | Not carried by E88, E84 (see fix). | G6, G9 |
| APG-S02-L0082 | Assign the action to an authorised owner. | Not carried by E85, E86 (see fix). | G7, G8 |
| APG-S02-L0091 | Link open defects to relevant retention or security conditions where evidence supports the relationship. | Not carried by E66, E75, E78 (see fix). | G3 |
| APG-S02-L0092 | Highlight approaching dates, blocked releases, unresolved closeout items and capital remaining tied up. | Dates and capital covered; closeout items not held. | G5 |
| APG-S02-L0094 | Track release, recovery, rectification and final closure. | Final closure of obligations not held. | G5 |
| APG-S02-L0095 | Reconcile the final financial outcome without counting a single underlying exposure multiple times. | No final-account record and no shared-exposure link. | G4, G6 |
| APG-S02-C0096 | Monitoring must continue after practical completion until relevant obligations are closed, explicitly transferred or otherwise resolved with documented evidence. | Not carried by E87, E83 (see fix). | G5 |
| APG-S02-L0102 | Assign the issue to an authorised compliance, commercial or project owner for verification and action. | Not carried by E85 (see fix). | G7 |
| APG-S02-L0106 | Original estimate and assumptions. | Assumptions via E46; the estimated benefit is not held. | G8 |
| APG-S02-L0110 | Difference between estimated and realised benefit. | Not carried by E88 (see fix). | G9 |
| APG-S02-L0111 | Reasons for material differences. | Not carried by E88 (see fix). | G9 |
| APG-S02-L0112 | Outcome classification: realised, partially realised, avoided, reversed or unverified. | Not carried by E88 (see fix). | G9 |
| APG-S02-L0117 | Finding: what was detected, where and when. | Where (scope) not held on E84. | G6 |
| APG-S02-L0118 | Evidence: source records, calculations, timestamps and data-quality limitations. | Timestamps not held. | G1 |
| APG-S02-L0119 | Financial effect: current exposure, potential gross benefit, expected net benefit and calculation basis. | Not carried by E84, E86 (see fix). | G8 |
| APG-S02-L0120 | Action: specific proposed intervention and accountable role. | Accountable role not held. | G8 |
| APG-S02-C0125 | A recommendation must not be labelled guaranteed savings. Estimated benefits remain estimates until validated. A recommendation may be withdrawn, superseded or invalidated when evidence changes, but its historical rec... | Supersession via E01; withdrawn/invalidated status not held. | G8 |
| APG-S02-L0132 | No double-counting: linked findings must represent shared underlying financial exposures explicitly. | Not carried by E84 (see fix). | G6 |
| APG-S02-L0139 | Time sensitivity and proximity to a deadline. | Contract deadlines in E12; finding intervention window not held. | G6 |
| APG-S02-L0141 | Reversibility of the proposed action. | Not carried by E86 (see fix). | G8 |
| APG-S02-L0143 | Cost and risk of intervention. | Not carried by E86 (see fix). | G8 |
| APG-S02-C0145 | The system must avoid duplicate and low-value alert flooding. Related findings should be grouped when they share a root cause or financial exposure while material differences remain visible. Escalation thresholds and ... | No setting holds escalation or notification frequency; grouping needs G6 links. | G6, G10 |
| APG-S03-C0014 | These are logical field names, not mandatory literal database columns. Final mapping must follow existing Anchor conventions. | Row anchors the s3 field table. E01 has source, record id, revision, ingestion state, verification, supersession only; evidence refs via E83 links. | G1 |
| APG-S03-L0030 | An avoided cost is not automatically a reduction in recorded expenditure. | Not carried by E88 (see fix). | G9 |
| APG-S03-L0034 | A recommendation's estimated benefit is not a realised benefit until measured and verified. | Estimated benefit not held. | G8 |
| APG-S03-C0036 | Profit Guardian must support multiple explicitly named financial views. It must not collapse accounting performance, expected final project performance and liquidity/capital pressure into a single margin figure. Every... | Exclusions per view not held. | G12 |
| APG-S03-L0045 | Reporting period and effective timestamp. | Period via E07 reporting calendar; effective timestamp not held. | G1 |
| APG-S03-L0047 | Included and excluded categories. | Not carried by E90 (see fix). | G12 |
| APG-S03-L0050 | Treatment of unapproved claims, retention and security. | E90 variation treatment covers unapproved variations/claims only. | G12 |
| APG-S03-L0063 | Final-account adjustments. | No final-account record. | G4 |
| APG-S03-L0143 | Conditions, disputes and linked defects. | Conditions on E75, disputes as E77 events; client retention has no defect link. | G3 |
| APG-S03-L0149 | Face value and currency. | No currency on E78. | G2 |
| APG-S03-L0153 | Capital or facility usage where known. | Not carried by E78, E74 (see fix). | G2 |
| APG-S03-L0154 | Status, verification evidence and linked obligations, disputes or defects. | Verification via E01; status and links not held. | G2, G3 |
| APG-S03-L0159 | Severity and operational impact. | Severity held; operational impact not. | G3 |
| APG-S03-L0165 | Links to retention or security conditions where supported. | Not carried by E66, E75, E78 (see fix). | G3 |
| APG-S03-C0177 | Every monetary value must have an explicit currency. Currency conversions must record source and target currencies, rate source, rate and timestamp, conversion method, included fees/adjustments and whether the rate is... | E37 has pair, date, rate, source; method, fees and rate kind not held, and converted records do not keep the conversion. | G14 |
| APG-S03-C0181 | Distinguish effective/event time, source-reported time, Anchor observation time, persistence time and calculation time. Contractual dates, calendar versus working days, time zones and business calendars must be explic... | Calendars via E50/E07; the five time kinds not held. | G1 |
| APG-S03-L0186 | Findings reference supporting evidence and calculations. | Evidence covered; finding-to-calculation-run reference not held. | G15 |
| APG-S03-L0190 | Outcomes are distinguishable from estimated benefits. | Estimated benefit not held. | G8 |
| APG-S03-L0192 | Related findings can link to shared causes, transactions, obligations or exposures. | Not carried by E84 (see fix). | G6 |
| APG-S03-L0193 | Portfolio aggregation avoids counting the same underlying effect multiple times. | Needs the shared-exposure links. | G6 |
| APG-S03-L0200 | State changes preserve provenance and relevant prior values. | No state-transition history. | G11 |
| APG-S03-L0202 | Approval alone does not mean a recommendation was executed. | No executed state. | G8 |
| APG-S03-L0224 | Relevant source timestamps. | Not carried by E45, E01 (see fix). | G1 |
| APG-S03-L0229 | Execution timestamp and references to resulting findings/recommendations. | Not carried by E45 (see fix). | G1, G15 |

## Every COVERED-BY-PROPOSED row, by M15 fix

**M15 fix 1: E100 material movement and stock** (6 rows)

- APG-S00-L0016: leakage evidence: labour, rework, idle resources, delay, waste, procurement, variations, supplier, defects
- APG-S00-L0038: material identity/spec/quantities, pricing, landed cost, lead times, waste, stock reuse, approved alternatives
- APG-S00-L0058: versioned materials register incl. consumed/returned/damaged/wasted quantities, remaining need
- APG-S00-L0063: buy/wait/stage/requote/negotiate/transfer stock/substitute options
- APG-S02-L0066: ordered, delivered, consumed, returned, damaged, wasted, remaining quantities
- APG-S03-C0109: quantity states connected by movements

**M15 fix 3: E27 approved equivalents and substitutions** (5 rows)

- APG-S00-L0038: material identity/spec/quantities, pricing, landed cost, lead times, waste, stock reuse, approved alternatives
- APG-S00-L0043: specifications, coordination issues, alternative methods/materials with approvals
- APG-S00-L0063: buy/wait/stage/requote/negotiate/transfer stock/substitute options
- APG-S03-L0103: brand or approved-equivalent constraints
- APG-S03-L0123: delivery time, availability, substitution constraints

**M15 fix 4: E08 pricing basis, milestones, defects liability period** (4 rows)

- APG-S00-L0041: defects, rework drivers, rectification, warranty exposure, DLP obligations, responsibility, prevention
- APG-S00-L0052: practical completion, DLP dates, defect notices, severity, responsibility, deadlines, inspections, sign-offs, costs, recovery
- APG-S02-L0090: defects, responsible parties, rectification costs, maintenance periods
- APG-S03-L0163: defect liability or maintenance period

**M15 fix 5: E64 owned plant and equipment use** (2 rows)

- APG-S00-L0016: leakage evidence: labour, rework, idle resources, delay, waste, procurement, variations, supplier, defects
- APG-S00-L0044: equipment utilisation, hire vs own, deliveries, storage, idle resources

No row in Part A depends only on M15 fix 2 (E101 cash-flow forecast), fix 6 (E73/E96 ledger journals and balances) or the E38 budget-part change. S00 L0045 (cash flow and capital exposure) is covered by existing entities; E101 would serve it but its words do not require a time-phased forecast.

## Where I think the M15 heading-level result is wrong or incomplete

1. **Its claim of completeness after reading S03 s2, s3 and s8 to s10 in full does not hold.** Rows in exactly those lists are uncovered: the S03 s3 common fields (G1), retention linked defects and disputes in s10.1 (G3), security instrument currency, facility usage, status and links in s10.2 (G2), defect operational impact and links in s10.3 (G3). E01 carries only source, record id, revision, ingestion state, verification and supersession; the s3 table also requires observed, effective and recorded times, validity interval, actor and schema version, and S03 s11.3 requires five distinct time kinds.
2. **It says it read S02 workflows A to H item by item, but the intelligence chain is under-specified in the register.** Workflow C and H and the S02 s6 recommendation contract need estimated gross and net benefit, implementation cost, accountable role, reversibility, lifecycle status (proposed to executed, withdrawn, invalidated), outcome classification, estimate-versus-realised difference and reasons. E86 holds only finding, action, conditions; E88 only decision, realised result, date (G8, G9). Owner assignment and deferral of alerts and actions (S00 L0032; Workflows B, E, G) have no home (G7).
3. **S03 s13 lifecycle table was not used.** Finding, Recommendation, Outcome and Security-instrument lifecycles have no status field in the register (E84, E86, E88, E78). These are folded into G6, G8, G9 and G2.
4. **Final account and closeout obligations are missing.** S03 s6.1 ("Final-account adjustments"), S03 s10.6 (obligations open until closed, transferred or waived; final-account items stay visible), S00 00.5.1, S02 Workflow F, and outside my part S07, S11, S12 s12.10 all name them. No entity carries the final account or a closeout obligation and its closed/transferred/waived state (G4, G5). M15 read S03 s10 and S12 s12.8 to s12.10 and did not flag this.
5. **No audit or access record.** S00 L0086 (record access to sensitive data), S02 L0031 (no silent alteration of financial history) and S03 L0200 (state changes keep prior values) need an audit event. E01 revision/supersession keeps record versions but not who changed or read what (G11). This may be satisfied by the platform-native audit mechanism that S01 Gate 01-C must find; if so the register should still name it as an external entity so the requirement traces.
6. **Linked-exposure / double-counting data is missing.** Many rows (S00 L0055, L0073; S02 L0050, L0132, C0145; S03 L0192, L0193) require findings to link to shared causes and exposures. E84 links only to E85 (G6).
7. **Smaller misses:** margin-view exclusions and treatment of retention/security (S03 s5, G12); market coverage by material category and geography (S00 L0066, G13); FX rate kind and conversion record (S03 s11.1, G14); calculation run to finding links (S03 s12, s14.3, G15); alert escalation and notification-frequency settings (S02 s8, G10).
8. **M15 fix 4 (DLP on E08) is right but may be incomplete:** defects liability periods also run on subcontracts (trade rectification responsibility, S00 L0041). Consider the same field group on E16. Not raised as a GAP because no Part A row states the subcontract DLP explicitly.
9. M15 says none of its gaps affects the first data release. Several of the gaps above (G1 time fields, G6 finding scope and links, G8/G9 benefit and outcome fields) touch records the first release presumably writes (findings, recommendations, outcomes, every record's provenance). I did not check release placement; it should be re-checked once these are accepted.

## Minor notes judged COVERED (worth a word in the register, not a GAP)

- S03 C0130: E48/E99 name planned and actual dates only; forecast dates are taken as the planned dates of the latest E47 programme version. Name "forecast" explicitly.
- S03 L0104: packaging and order multiples are not named on E26; taken as covered by N01 declared unit conversions and quote tiers/terms (E31, E32).
- S03 L0117: expected waste or yield loss is taken as a landed-cost component on E33; it is not named.
- S03 L0142: E75 has a due date but no explicit milestone link.
- S00 L0046: E36 is keyed on material; freight and energy indices fit only if its material field admits an indicator family.
- S02 L0027: project-level scoping of role assignments is assumed to sit in E05 roles (platform identity).
- Currency: S03 C0177 says every monetary value needs an explicit currency. Entities outside E96 (E75, E74, E77 and others) rely on the project currency (E07). Only E78, whose row names currency, is raised as a GAP (G2); G14 covers conversions.

## Rows I could not judge

None: all 700 rows were judged. Note on scope: the RTM rows do not include the bodies of several tables and boxed paragraphs in these sections, so they were read for context only and judged through the rows that anchor them. These are: S02 s2.1 domain table, s3 actors table, s5 functional requirements register and s9 non-functional table; S03 s2 hierarchy, s3 common fields, s4 categories, s6.3 formulas, s13 lifecycle table; and the bodies of S03 s10.5 and s10.6 (only their headings are rows). Their data needs feed G1, G3, G4, G5 and the status parts of G2, G6, G8, G9. If the RTM is meant to trace those table rows, they are missing from it.

