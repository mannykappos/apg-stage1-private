# Builder's fixes to the INDEPENDENT READ-ONLY (agent) check of draft 4 (26 points: 12 should fix, 12 minor, 2 optional) — BUILDER-WRITTEN

Draft 5 is the design after these fixes. build_field_coverage.py rewritten (per-kind); build_supply_plan.py label renamed ("APG calculates"); both regenerate identical CSVs on repeat runs.

| # | Fix in draft 5 |
| --- | --- |
| S1 | Field check now attributes each field to the kind named before it and checks it against that kind; plain words matched to named fields (amount, delta, supplier); the project field checked on every kind the M4 figures read, with linked or organisation-level kinds listed; AGG's "supplier" grouping key handled as an order field. 87 kind-and-field pairs, no gap. |
| S2 | Purpose rule 2 says "every field the contracts name for a supplied record"; limits now list the configuration column, unnamed fields, undefined retention-event fields, authority/verification, and that the register is an inventory; retention events in the future tense. |
| S3 | AC-12 has one reading (at least one built way in per field incl. settings; each way in carries its entities' fields when built) and is release A's third gate. |
| S4 | The three direct writes are taken out of the migration: they enter the reference intake as new kinds and do not wait for it. |
| S5 | Reviewer positions attributed correctly (phone: GPT only; release A: Gemini over-scoped, GPT staged; subcontractor leakage: Gemini). |
| S6 | Middle path names the way in for each M6 supplement (E33, E34 entry forms; E27, E31, E32 template or keyed upload). |
| S7 | Seven file-only facts restated as "no other way in under any option"; others by file until their form is added. |
| S8 | Middle path moves E83 into release A; keyed quote readings confirmed by a second person with the verifier role (S04 §12, §18). |
| S9 | Decision 7 says promotion only readies data and ties it to the back-to-back check (decision 8). |
| S10 | Matching wording follows S04 §11 (stable IDs and approved cross-reference rules allowed). |
| S11 | Sharing between related companies or joint ventures: not defined by the blueprint in the pack; own decision; cascade list adds Section 01 tenant model and Sections 15 to 17. |
| S12 | Retention: "possible gap", not found in the pack's sections; S04 §6 and §16 noted; confirm against Sections 09 and 15 to 17. |
| M1 | Calculated records split: 11 calculated (7 built or partly, 4 not); 5 person-confirmed; E02 setup with a calculated alternative; one term ("records APG calculates") throughout, diagram label updated. |
| M2 | AC-07 covers safe isolated parsing, limits and rejection of malformed files. |
| M3 | AC-02 defines equivalence on the source facts before mapping. |
| M4 | N01: R04B instruction types and R07 pairs have no default; builder's approver accepts defaults at onboarding. |
| M5 | Reasons added: thresholds are sensitivity choices, M6 supplements are facts; defaults general because contract forms differ by state. |
| M6 | Governance roles mapped to readiness roles; roles start from defaults, confirmed progressively. |
| M7 | Nudges link to the way in that fixes it (form, upload or review queue). |
| M8 | Only an unapproved or overlapping authority change is held; an approved, dated change takes effect from its date. |
| M9 | Status line states the reviews exactly; fix list notes GPT's counts sum to 29 and the labels are inferred. |
| M10 | Fix list relabels GPT 1, 16, 18 and Gemini 4, 5 as fixed in part in draft 4, completed in draft 5. |
| M11 | Learning cost-code map: every match still confirmed within this design; changing that belongs to its own change request. |
| M12 | EDR-22 vendor requirements and AUIF contracts stated as not in the pack, dependencies. |
| O1 | File-only facts: hand-filled template fallback available in release A. |
| O2 | AC-10 lists the gap lifecycle states. |
| Wording | Plain glosses added for intake envelope, control checkpoints, mapping and regression baseline. |
