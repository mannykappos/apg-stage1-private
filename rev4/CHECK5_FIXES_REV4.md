# Fixes for the fifth agent check of revision 4 (BUILDER-EXECUTED: NOT INDEPENDENT)

The fifth check covered the changes made after GPT's check of revision 4 (its report is above this list in `AUDIT.txt`). Code was not changed. Every generator was re-run and reproduces its file byte for byte from the pack's own code.

| # | Class | Fix |
| --- | --- | --- |
| B-1 | Blocking | The PM-system copy of the invoice amount (pm_invoice amount_ex_gst_cents, a second source field authority compares with the invoice) is named in the reference-intake row (with SECONDARY_DISAGREES, SECONDARY_IN_CONFLICT, SECONDARY_WITHOUT_PRIMARY) and in the actual-cost row, whose code path now includes reconciliation; pm_invoice is attributed to E23; its route row labels it a second source. 170 fields (was 166). |
| S-1 | Should fix | `build_code_reads.py` resolves imported constants (SPECS, DET_SPECS); D02's event-date fields are now on its row, and its OUTSIDE_PERIOD note is in its contract. |
| S-2 | Should fix | last_paid is on the comparison row's code column and mkt/demand.py coverage on the buy-timing row's; the scan finds their inputs. |
| S-3 | Should fix | "upper bound", "every field the code path reads" and "fixed at its source" replaced: over-inclusive within the kinds a row names, kinds a row does not name are not counted, rows without entry functions are skipped, a check by its listed rules and not a proof (document, draft 7, prompt, docstring). |
| S-4 | Should fix | DC-13 restated: such a record is pinned into every project's run (det/gather.py, mkt/gather.py) and then neither assessed nor listed by any project-scoped rule, D02 and MPD1 included; the main case today is a conflict whose versions name different projects; the M6 coverage rules match by project_ref equality. The decisions record notes that Claude's first example to the owner was not the main case. |
| S-5 | Should fix | The defect section says DC-1 to DC-12 are decided and DC-13 is put to the owner. |
| S-6 | Should fix | MP09 names the comparability-gate inputs (quote readings) and the import checks. |
| M-1 | Minor | The credit supplier check runs only when both suppliers resolve through E20, otherwise SUPPLIER_NOT_CHECKED. |
| M-2 | Minor | DC-4's message row: the tax treatments differ and the GST rate is not set. |
| M-3 | Minor | "a demand line with no positive quantity" in the document and the register. |
| M-4 | Minor | Report counts and DC ranges brought up to date (five reports; the checks and GPT's; DC-13 if he agrees; draft 7's line). |
| M-5 | Minor | The prompt and the document say one shared row. |
| M-6 | Minor | The shared row no longer mentions credit notes and amendments, which no detection or M6 rule scopes. |
| M-7 | Minor | Not changed: a settings row quotes the contract's configuration text whole, and its entity column says which entity the row is for; splitting the keys by entity is left to the schema register, a next step. |
| M-8 | Minor | Docstring corrected (the module list; GENERIC and function-local imports explained). |
| M-9 | Minor | retention_event project_ref named in the retention-event row. |
| M-10 | Minor | Draft 7 describes how the supply plan's N01 flag is counted (from the configuration column). |
| M-11 | Minor | The document has a table mapping GPT's ten points on revision 4 to where each is answered. |

Counts after the fixes: 57 contract rows, 43 rules and figures; 170 fields in 33 entities (34 material) and 56 settings rows; authority 6 / 36 / 17 / 1 / 110; 20 fields with document capture partly built; 580 messages; DC-1 to DC-13 (DC-13 pending the owner).
