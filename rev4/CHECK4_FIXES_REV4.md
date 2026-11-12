# Fixes for the fourth agent check of revision 4 (BUILDER-EXECUTED: NOT INDEPENDENT)

The check's report is above this list in `AUDIT.txt`. Every point is addressed. Code was not changed. Every generator was re-run and reproduces its file byte for byte.

| # | Class | Fix |
| --- | --- | --- |
| SF-1 | Should fix | COMPONENT_PROVISIONAL and COMPONENT_CANNOT_ASSESS added (fin/figure.py builds them as 'COMPONENT_%s:%s'); the scan now treats an upper-case piece followed by %s as a code prefix. |
| SF-2 | Should fix | The scan now also reads the gaps, reasons, notes and limitations lists, the dict keys reasons, unknown and outstanding, the reason a finding has no amount (S.unquantified), every branch of a conditional text and every element of a list, the procurement setting a MissingParam names, and the settings validators' lists of bad fields. All the check's C1 to C13 are in the list. The document's description names the patterns instead of saying "every", and names the modules left out (test, demonstration, reference and port modules, and materiality.py). The list is 579 entries (was 512). |
| SF-3 | Should fix | DC-12 is described everywhere as put to the owner, pending his word (the document, the message list's "today" column, the script comment). |
| SF-4 | Should fix | RECOGNISED_REVENUE_UNKNOWN and FORECAST_REVENUE_UNKNOWN: the margin run named does not carry that revenue basis; audience person; action "choose the margin run that carries this basis". |
| SF-5 | Should fix | DC-11: graded with the pinned detection policy's bands whether or not that policy is approved. |
| SF-6 | Should fix | "status: not_ingested": APG refused to read a stored file; act on its code. |
| SF-7 | Should fix | The flag is set when a finding is created or updated; a reopened or kept-dismissed finding keeps its earlier flag (document, register row, message list). |
| SF-8 | Should fix | Draft 7: phone capture is decision 6; its own list is said to be numbered in its own order. |
| Minor 1 | Minor | Each joined code records the file that builds it. |
| Minor 2 to 8 | Minor | FRESHNESS, GATE, PROVISIONAL, A_FORECAST_CANNOT_BE_ASSESSED, "exclude: not_counted", "status: refused", "status: unknown" and the freshness rows corrected as the check proposed (the freshness rows say no stage 1 run calls `ingest/freshness.py` yet). |
| Minor 9 | Minor | As SF-5 and SF-3. |
| Minor 10 | Minor | One list of DC-12's skip reasons everywhere: held, duplicate, unreconciled, without an amount, after the cut-off, status unknown or unmapped. |
| Minor 11 | Minor | The extra-work cost need is recorded on E09 and E10; how the cost records carry it is left to the Section 18 assessment (document and draft 7). |
| Minor 12 | Minor | ACTUALS_AFTER_FORECAST_DATE_NOT_ADDED, RECONCILIATION and UNIT_INCOMPATIBLE corrected (UNIT_INCOMPATIBLE and "status: incompatible" are builder, like "no declared conversion"). |
| Minor 13 | Minor | The owner was told on 2026-11-12 (document and record agree). |

Counts after the fixes: 579 messages (262 codes, 188 plain-language reasons, 4 states, 113 refusals and errors raised, 12 cases with no message today; builder 288, person 98, information 111, system 82). Other counts unchanged. After four agent rounds the builder stops further agent rounds here, so the review does not loop: the pack goes to GPT's one-pass check next.
