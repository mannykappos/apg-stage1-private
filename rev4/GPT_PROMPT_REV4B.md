# Scoped re-check: APG Data Readiness Change Request, revision 4, after your check of it

Your check of revision 4 found it NOT READY: four blocking items (the credit note's supplier field; the project-scope fields of the detection rules and D02's record kinds; incomplete M6 contracts for comparison, buy timing, MP01, MP02, MP08 and MP09; the field-level report inheriting those omissions) and six should-fix items (R07's issue date; quote_reading.extractor_kind; the buy-timing market-observation fields; MPD1's project fields; the severity setting's own route and the grouping of settings rows; the DC-1, DC-4 and DC-6 wording in the message list). Your conclusion was that the architecture and the owner's decisions are sound and only the contract and coverage omissions stand in the way.

The root cause you named is addressed: the field-level report no longer rests only on the contract text. `03_registers/build_code_reads.py` parses the code and follows each rule's and figure's code path from its entry functions through every function it calls (including the M6 views of quotes and orders and the module constants they use), and writes `CODE_READS.csv`: the fields of the record kinds each row names that the path reads. Within those kinds it over-includes (a shared helper counts for every row that reaches it); it does not count kinds a row's text does not name, and it is a check by its listed rules, not a proof. `build_field_coverage.py` adds every one of them to the report. The contract rows you named are also corrected in their text.

This is a **scoped check in ONE pass, limited to your ten points**. Review all ten and list every remaining problem now; do not stop at the first one. If nothing BLOCKING remains, the owner proceeds to the Section 18 cascade impact assessment, and smaller points are fixed on the way; there is no further round.

## What changed (the attached zip)
- `01_CHANGE_REQUEST_REV4.md`: the field-level section (now three generated files), the contract tables (one shared row for every project-scoped rule; R07's issue-date limit), the defect table (DC-13, found while answering your check, put to the owner), a table mapping your ten points to where each is answered, and the counts: 57 contract rows, 170 fields in 33 entities, 56 settings rows; authority 6 / 36 / 17 / 1 / 110.
- `03_registers/RULE_INPUT_CONTRACTS.csv`: the credits row (supplier_ref, and reconciliation on its path), the duplicates and actual-cost rows (reconciliation on their path; the PM-system copy of the invoice amount, found by the fifth agent check), one new shared row for every project-scoped detection and M6 rule, D02's and MPD1's kinds, the comparison, buy-timing, MP01, MP02, MP08 and MP09 rows, R07's limit.
- `03_registers/CODE_READS.csv` and `build_code_reads.py` (new); `FIELD_COVERAGE.csv` (a column for fields read on the code path but not named in the text) and `FIELD_SUPPLY_ROUTES.csv` (170 fields; a settings row of its own for the severity grading levels).
- `03_registers/NOT_ASSESSED_MESSAGES.csv`: DC-1, DC-4 and DC-6 reworded; DC-13 added (580 entries).
- `07_decisions/`: draft 7 updated to match; the owner's decisions record (item 12).
- `AUDIT.txt`: ends with a fresh independent agent check of these changes (the fifth: 1 blocking, 6 should fix, 11 minor) and the fix for each.
- Every generator reproduces its file: run, in `03_registers/`, `python3 -I build_systems.py .`, `build_entities.py`, `build_rule_contracts.py`, `build_chart_data.py`, then `python3 -I build_code_reads.py ../04_code_read/apg .`, then `build_field_coverage.py .`, then `python3 -I build_message_list.py ../04_code_read/apg .`.

## Check exactly these
1. For each of your four blocking items: RESOLVED / PARTLY / NOT RESOLVED, with evidence (quote the row or file).
2. For each of your six should-fix items: the same.
3. `build_code_reads.py`: does it find the fields you named (credit_note.supplier_ref, the project_ref fields, supplier_quote issue_date, valid_until and material_ref, purchase_order quantity, material_ref and unit_rate_cents, quote_reading.extractor_kind, the market-observation fields, the coverage inputs of buy timing and MP09)? Name any field a row's code path reads that `CODE_READS.csv` and `FIELD_SUPPLY_ROUTES.csv` still miss, with the file and line.
4. DC-13: is it described accurately against the code?
5. Totals, and whether anything is BLOCKING.

## Rules
- Class every problem BLOCKING (the owner should not proceed to the Section 18 assessment until it is fixed), SHOULD FIX or MINOR, with a rough cost.
- Do not reopen points you found resolved, and do not widen the scope: no new features or design.
- `CODE_READS.csv` over-includes by design within the kinds a row names (a shared helper counts every field it reads for every row that reaches it); over-inclusion is not a defect. Report only fields it misses, including fields of a kind a row's path reads but its text does not name.
- Say "not verifiable from the pack" where the pack cannot settle a point.
