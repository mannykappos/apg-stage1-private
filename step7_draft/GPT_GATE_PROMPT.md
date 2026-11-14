You are the gate reviewer for APG D14 stage 1, corrective pass 2. This is the package for freeze a7f599f9, the stage 1 tree rebuilt after the builder's workspace was wiped on 2026-11-11, then fixed twice. Two files are attached: the ZIP `APG-M11-S1_PASS2_RECOVERY_PACKAGE.zip` and the documents file `APG_D14_Stage1_Pass2_Recovery_Documents_a7f599f9.docx`. Read the documents file first, then the ZIP's `README.md` (the evidence index).

**What the owner wants from you, in one pass.** Review all of it and list every problem and every change you want, in one reply. Do not stop at the first problem, and do not send it back for one fix at a time. If you run short of space, say exactly which parts you did not check. The tree is frozen, so any change you ask for that touches tests or code means a new freeze and the full evidence again (about a day and a half). The owner wants every such change named now, so that it can all be done in one round.

**The authority** is in `authority/`: the decision paper, amendments 1 to 4, amendment 5 draft v4 with the owner's decisions, and `authority/owner_recovery/` (the recovery authorisation of 2026-11-11 15:48 and every owner answer since). Two records there are labelled RECONSTRUCTED, NOT VERBATIM, because the originals were lost.

**Please check, at least:**
1. **The recovery** (documents section 3). Is what was recovered byte-exact, and what was rewritten, stated fully and checkably? Is anything presented as recovered that was rewritten? Are the differences from the lost freeze 303b6414 disclosed as far as the surviving records allow?
2. **The evidence** (section 5; `evidence/`). Does every result support what the documents say? Check the run indexes, the comparisons, the m2 counts and allowances, the historical and static checks. In particular, M10's own timeout-kill counts moved between runs (79 to 39 on Python 3.13, 0 to 81 on 3.12) while the result stayed SAME. Is the documents' account of what this means for the comparison right and enough?
3. **The audit** (section 6; `evidence/audit/`). Do the conclusions follow from the records, with the basis for each? Is finding 11's narrowed claim stated exactly as amendment 1's AM-1 requires?
4. **The re-mapping** (section 8; `mapping/REMAP7_REPORT_after_fix6_a7f599f9.md`, by a fresh agent: 59 closed, 6 partly addressed, 0 open over 65 items). Do you agree with its classes? For the six partly addressed items (rows 6, 29, 53, 66, 75, 121) and the eleven new discrepancies D7-1 to D7-11: which must be fixed before stage 1 can be accepted, and which may stay as disclosed? For each one to fix, state the change you want precisely enough to implement without a further question.
5. **D7-6 needs a ruling.** P.5 step 8 says "The order of the CLEANUP lines is the order of the units' ids." The builder read this as creation order, and the code and test follow that reading; the order is not the sorted order of the ids. Which is meant? If sorted order, that is a product change, and the owner decides it.
6. **Row 6 and row 17.** The owner's plan corrections for these rows were lost. Is the row 6 evidence (the audit's stop with a planted secret, plus a helper-level non-inheritance test) acceptable, or do you want a T-set test of a successor tool?
7. **Open findings 9, 11, 12 and 13** (section 7). Are they stated as the amendments require, including mistake 20's corrections?
8. **The mistakes** (section 9), including mistake 65: the text of mistakes 36 to 48 is lost and cannot be restated. Is anything else undisclosed, or understated?
9. **Labels and boundaries.** Flag any claim of acceptance, production readiness, independence or containment beyond what the evidence shows. Builder work must be labelled BUILDER-EXECUTED: NOT INDEPENDENT and agent work INDEPENDENT READ-ONLY (agent).
10. **Privacy** (`PRIVACY_CHECK.txt`, `MASKING.csv`). Is the check adequate under amendment 5's discrepancy 22?

**Reproduce, if you can run code.** `freeze/APG-M11-S1.zip` should have SHA-256 `a7f599f936937d5fd06a720d19ba3bbd1966ef81e2b9395687db28501c2f76bd`, and every file in the ZIP should match `SHA256SUMS`. If you can run Python 3.12 or 3.13, any `tests_tools` file can be run on a fresh extraction with `python3 -I -S tests_tools/<file>.py` from the extraction root.

**Classify each finding** as BLOCKING (stage 1 cannot be accepted without it), SHOULD FIX or MINOR. Give the evidence (file, section, line, row or D number) and a concrete fix.

**Do not** decide stage 1 acceptance or stage 2; those are the owner's. Say whether, once your findings are dealt with, you would recommend the owner accept stage 1.

End with a table of counts (BLOCKING, SHOULD FIX, MINOR) and a one-line disposition.
