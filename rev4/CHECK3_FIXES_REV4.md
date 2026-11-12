# Fixes for the third agent check of revision 4 (BUILDER-EXECUTED: NOT INDEPENDENT)

The check's report is above this list in `AUDIT.txt`. Every point is addressed; none is left open. Code was not changed. Every generator was re-run and reproduces its file byte for byte.

| # | Class | Fix |
| --- | --- | --- |
| B1 | Blocking | `build_message_list.py` rewritten as a parse of the code (Python's ast module) over every production module, `policy_approval.py` included. It now collects one-word and prefix codes and codes built by joining strings (`fld.upper() + '_NOT_CONFIGURED'`, `label + '_UNKNOWN'`, the percent-complete state), every M4 unknown-input reason, exclusion class and dispute text, every why, reason, note, status and missing_parameter given as a dict key, an assignment or a keyword argument (audit-log calls left out), every `(None, text)` return, the freshness and figure states, and every refusal an APG error class raises. All 17 codes the check named, and the reasons it named, are now listed. The list is 512 entries (was 283). The claim is reworded everywhere (the document, draft 7, PG-DS-AC-14, the GPT prompt, the docstring): a check by the listed patterns, not a proof; each message is proven by a test when it is built. |
| SF-1 | Should fix | The status-map entries name the real classes (orders: committed, draft, cancelled, closed; variations: approved, unapproved, disputed, rejected); EXPIRY_REVIEW says the instrument has reached its expiry date; RECOGNISED_REVENUE and FORECAST_REVENUE are now listed as labels joined into RECOGNISED_REVENUE_UNKNOWN and FORECAST_REVENUE_UNKNOWN, which have their own builder entries. |
| SF-2 | Should fix | DC-11 and the "every detection rule" and M6 rows now say the run record and each stored finding carry `policy_unapproved` (det/findings.py), the signal does not, M6 findings carry only the detection policy's flag, and whether the flag is shown to the builder is not settled here. |
| SF-3 | Should fix | The document, draft 7 and the decisions record now say severity bands are dollar amounts only today, the materiality model is not used by severity grading, and grading by a percentage of the job is new design and new code. Claude's wrong statement to the owner is disclosed to him. |
| SF-4 | Should fix | "His setting them is the approval" removed (it was Claude's gloss); how the builder's setting relates to the two-person policy approval (F-67, PG-DS-AC-05, S06 §5.1 and §8) is left to the Section 18 assessment, in the document, draft 7 and the decisions record; S06 §8 added to draft 7's cascade list. |
| SF-5 | Should fix | Row 35 (R04B) states the decided warning; the field files regenerated. |
| SF-6 | Should fix | Draft 7's added items carry no list numbers ("Decision 13", "Owner requirement", "Owner decision"), with a note that they do not collide with the decisions document's numbering. |
| SF-7 | Should fix | Added as DC-12 under the owner's rule, as DC-10 was: in the DC table, the commitments and R02 rows of the register and the document, the message list, and the decisions record (item 8, put to the owner). |
| Minor 1 | Minor | Attribution in the decisions record corrected; DC-3 is called an uncaught error, not silent, in the message list and the text ("eleven silent, DC-3 an uncaught error"); the docstring range corrected. |
| Minor 2 | Minor | Draft 7's intake-stage table cell aligned (a verified date is kept as text and does not reach the authority logic). |
| Minor 3 | Minor | `build_field_coverage.py` docstring says draft 7. |
| Minor 4 | Minor | DC-3's condition: a usable order, or a duplicate candidate whose rate every candidate shares. |
| Minor 5 | Minor | DC-10: D02 does not list such orders either; M4 commitments lists held and unreconciled ones, not zero-quantity ones. |
| Minor 6 | Minor | Message entries corrected: BUDGET_EXCEEDED_BY and FACILITY_STATEMENT_AFTER_AS_OF are builder; CRITICAL_VALUE_MISSING names the intake settings; NON_ASCII_IDENTIFIER says plain ASCII; RELEASE_REVIEW_DUE says review whether release is due and, if so, claim it; NOT_RECONCILED covers quotes; reconciliation is described as done by the intake; INPUT_MISSING removed (it was only in a docstring); the "after the as-of date" texts no longer ask for a date; ACTUALS_AFTER_FORECAST_DATE_NOT_ADDED reworded. |
| Minor 7 | Minor | DC-1's fix uses the recorded wording: a warning that the client rejected the variation for this work, with what to do. |
| Minor 8 | Minor | The citations are the same in the document and draft 7; S05 §7 is cited for what it says (unrecovered variations as a way profit leaks). |
| Minor 9 | Minor | "decision 9's owner-approved defaults do not apply to the severity bands". |
| Minor 10 | Minor | ENTITY_REGISTER: N01 lists the severity grading levels and the missing setup; E09 lists the rejected-variation outcome and the cost of extra work; E10 the cost of extra work. Counts unchanged. |
| Minor 11 | Minor | This report and this list are appended to `AUDIT.txt`; the response table names the third check. |
| Minor 12 | Minor | The document's owner-decisions section names S06 §5.1 and §8. |
| Minor 13 | Minor | "raised and authorised as its own change request" added where the fix timing is stated. |

Counts after the fixes: 100 entities (11 / 42 / 47); 56 contract rows, 43 rules and figures; 155 fields in 33 entities and 55 settings rows; authority 6 / 33 / 15 / 101; 512 messages (260 codes, 135 plain-language reasons, 4 states, 101 refusals and errors raised, 12 cases with no message today; builder 257, person 91, information 89, system 75); DC-1 to DC-12.
