You are reviewing a Section 18 §6 Cascade Impact Assessment for a proposed change request to a LOCKED construction-software blueprint (Anchor Profit Guardian, Sections 00–18, version 1.0). The attached ZIP holds everything you need. Read 00_README.txt first.

What is being assessed: one change request (provisional ID APG-CR-DSR), made of two documents.
- The data supply design, draft 7 (06_change_request_sources/DATA_SUPPLY_DESIGN_DRAFT7.md).
- The Data Readiness Change Request, revision 4 (06_change_request_sources/DATA_READINESS_CR_REV4.md, with its registers). You checked revision 4 earlier and found nothing blocking.

The assessment is 01_ASSESSMENT_DRAFT4.md. A Word copy of the same text is supplied separately. It proposes 81 additions to Sections 01, 02, 03, 04, 05, 06 and 11, which would become version 1.1. It also rewords their 10 version lines, and nothing else. It lists 1,342 locked paragraphs and table rows reviewed as insertion points or dependents. The tables in 03_tables/ are generated from the locked package by 04_tools/build_cia.py (with cia_data.py); 04_tools/assemble.py builds the assessment from CIA_SOURCE.md.

Three independent agent checks have run (08_checks/). The fixes for the third have not been checked independently.

How to review:
1. Review ALL of it in ONE pass and list EVERY problem you find. Do not stop at the first problem, and do not send it back for one fix at a time. If you run short of space, say exactly which parts you did not check.
2. Classify each finding as BLOCKING (approval must not proceed), SHOULD FIX, or MINOR. For each, give the evidence (file, section, line, RTM ID or anchor) and a concrete fix.
3. Check the assessment against Section 18 §6, §9 and §11 checkpoint B, and against the package's CHANGE_REQUEST_CASCADE_IMPACT_TEMPLATE.md. Is every required element present and real?
4. For every proposed addition (03_tables/CIA_PROPOSED_TEXT.csv), read the locked text around its anchor and anywhere else it bears on, in 05_locked_package/. Say whether it contradicts, changes the meaning of, relaxes, or widens the scope of any locked requirement without the assessment saying so. Be hardest on financial definitions (S03 §4–§6, S05 §3–§5, S11 §8, the terminology register), approvals and segregation of duties, source authority, and tenant isolation.
5. Check that the dependents list (03_tables/CIA_RTM_IMPACT.csv) is complete. Section 18 §6 says an unreviewed dependent section blocks approval.
6. Check faithfulness. Does any addition say something the change request and the owner's decisions (06_change_request_sources/OWNER_DECISIONS_2026-11-12.md, APG_Data_Supply_Decisions.md) did not decide? Does it leave out something they did decide, without saying so?
7. Check the four questions for the owner (section 11). Are they accurate, needed, and in plain words, with correct examples and arithmetic? Is anything that should be the owner's decision settled silently in the text? Do not answer the questions for him; say only whether they are framed correctly.
8. If you can run code: in 03_tables/'s parent folder, run `python3 -I 04_tools/build_cia.py 05_locked_package <new folder>` and `python3 -I 04_tools/assemble.py 04_tools/CIA_SOURCE.md <new folder> <new folder>/draft4.md`, then compare with the files given. python-docx is needed.
9. Keep the boundaries. This is design only: no build is authorised and stage 2 is not authorised. Flag any claim of implementation, acceptance or production readiness.

Also say whether you think this assessment is ready for the owner's formal approval once your findings are fixed, or whether another review round is genuinely needed. If the remaining points are wording only, say so, so the review does not loop.

End with a table of counts (BLOCKING, SHOULD FIX, MINOR) and a one-line disposition.
