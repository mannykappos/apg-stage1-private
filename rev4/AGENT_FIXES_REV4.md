# Fixes for the independent agent check of revision 4 (BUILDER-EXECUTED: NOT INDEPENDENT)

The agent's report follows this list unchanged. Every finding is addressed; none is left open. Code was not changed: where a finding showed a behaviour the owner may want changed, it is described in the contract as today's code and listed as a defect candidate for the owner (DC-3 to DC-9, and the DC-1 scope question). Before writing the new candidates in, Claude checked them against the code; DC-3 was reproduced by a direct call (an AttributeError).

| # | Class | Fix |
| --- | --- | --- |
| 1 | Blocking | Credits row rewritten: reconciliation links each credit through against_invoice_ref; CREDIT_TARGET_NOT_VISIBLE, CREDIT_EXCEEDS_INVOICE and CREDIT_SUPPLIER_MISMATCH added; the "information only" comment is noted for the code owner, no code change. |
| 2 | Blocking | The field check now matches one-word fields of the current kind (quantity). Fields named: 155 (was 135), material: 33 (was 29). |
| 3 | Blocking | The fields the agent listed are now named in the contracts (retention-event fields, the bank receipt amount, quote references, extracted_by, delivery order, date and material, order unit of measure, quote supplier, specification text and price kind, project contract value, the invoice duplicate keys). Retention-event fields are listed separately (no record definition yet). The document's "What the report does not do" now says the report covers the fields the contracts name, and why a field no contract names would still be missed. |
| 4 | Blocking | The authority column is split: resolved (6 fields), reference intake with link, duplicate and supplier checks only (48), second loop (101). The document's figures and the script docstring are corrected. |
| 5 | Blocking | Document capture is "partly" only where code exists (quotes E30, quote readings E35, the document record E83); 14 entities move to "proposed". The chart's document row is 3 / 20; the subcontract (E16) now has no built path. |
| 6 | Blocking | The specification register is named in the comparison row and in a new row for every M6 figure and rule; it is attributed to N01, whose description is widened. |
| 7 | Blocking | The comparison row lists the gate, blocker and record-state codes; MP03 and MP04 list UNIT_MISMATCH; the new "every M6 figure and rule" row gives MKT_POLICY_NOT_PINNED, SWITCHED_OFF_IN_POLICY and not_configured. |
| 8 | Blocking | Each silent behaviour is stated in its row and E90 added to the configuration of MP05, MP08, MP09 and MP10. Listed as candidates DC-4 (no PO status map; MP09 tax), DC-5 (MP01 with no quote), DC-6 (unusable or zero-quantity requirements). Checking these, Claude found that MP02 and MP09's reference lookup raises an error when the policy holds the PO status map as an explicit empty value (DC-3). |
| 9 | Should fix | Buy timing now reads quote terms (payment days, deposit, minimum order, pack size), with its settings and statuses; the "payment terms are not ingested" limit is removed. |
| 10 | Should fix | DEF's partial-cost case stated; listed as DC-9. |
| 11 | Should fix | Landed-cost settings, MP03's order fields, MP04's docket rule and MP10's min_projects added. |
| 12 | Should fix | Stated in the R04B row and the document: the DC-1 scope question (a usable variation mapped to rejected) goes to the owner. |
| 13 | Should fix | Stated in the commitments and R02 rows and the document; listed as DC-7. |
| 14 | Should fix | A new row for every reference-intake record: the authority-register holds (not clearable by a reviewer) and the supplier-master hold, with E03 and E20 as configuration. |
| 15 | Should fix | N01 reworded as versioned, approved policy records with no builder setup question or owner-approved defaults; status partial, its setup way in partly built, like E90. Counts move: configuration 0 / 4 / 6, total 11 / 42 / 47, setup questions 2 / 12. E90's wording corrected the same way. |
| 16 | Should fix | E03 described as an in-code register object passed to reconciliation, its approval asserted on the object, not audited. Claude also found that draft 6 of the data supply design said authority register rows were written straight to the store; that was wrong, and draft 7 corrects it. |
| 17 | Should fix | Revision 2 added to `06_previous`. |
| 18 | Should fix | The material flag is labelled as a proxy for S04 §12 and a lower bound, with documents.py's own list noted; "must add" for a material field now applies only to a value that comes from a document; the reasons for "none meets PG-DS-AC-12" are corrected. |
| 19 | Minor | Settings rows described as one per contract row that names configuration, per settings entity. |
| 20 | Minor | The GPT prompt is in the pack; the README is corrected; build_entities.py's docstring says revision 4. |
| 21 | Minor | The survey column header aligned ("holds"); the market-feed row says proposed, test doubles only, no provider; Procore's variations and progress claims marked as matched by name only; "would work ... once built". |
| 22 | Minor | Reworded: a person can record a verified date, but it is kept as text and does not reach the authority logic. |
| 23 | Minor | Policy approval behaviour added to every M4 figure and to a new row for every detection rule; R01's codes with no budget line stated and listed as DC-8. |
| 24 | Minor | Two pointer rows added (New 2; B3, S4, S6). |
| 25 | Minor | The 52 entities with no built path now say that five of them are partial, and why. |
| 26 | Minor | The document says the data supply design counts the minimum way in (47 / 53) and this revision counts any path (48 / 52), so they differ by design. |
| 27 | Minor | PG-DS-AC-12 identified as a criterion of the data supply design, approved in principle, not a locked blueprint ID. |
| 28 | Minor | The shared modules the contracts depend on are added to the pack (`fin/figure.py`, `fin/snap.py`, `fin/fmath.py`, `det/common.py`, `det/signal.py`, `det/detect.py`, `policy_approval.py`, `materiality.py`). |

Not verifiable from the pack (agent part 4): the snapshot and figure modules are now in the pack. The intake policy question is answered in the document: the stage 1 intake policy does not tolerate a missing quote validity date, so the error the agent foresaw cannot arise today (a note, not a candidate). The owner's decisions are recorded in `07_decisions/OWNER_DECISIONS_2026-11-12.md`.

Counts after the fixes: 100 entities, 11 covered, 42 partial, 47 missing; 56 contract rows, 43 rules and figures; 155 fields in 33 entities and 56 settings rows; 38 entities with a built path, 10 partly built, 52 with none. Every generator was re-run and reproduces its CSV.

---

