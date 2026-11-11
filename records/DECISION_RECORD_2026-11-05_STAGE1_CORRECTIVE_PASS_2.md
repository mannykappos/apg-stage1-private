# Decision record: APG D14 stage 1, corrective pass 2

**BUILDER-EXECUTED: NOT INDEPENDENT.** Written by the builder on 2026-11-05 (AEDT). It records the owner's decision. It accepts nothing, closes no finding, EDR or CF item, and makes no production-readiness claim.

## The decision
- **Posted by the product owner on 2026-11-05 at 10:56,** filed verbatim as `rec/reviews/RECEIVED_OWNER_POST_2026-11-05_1056_CORRECTIVE_PASS_2_AUTHORISATION.txt` (SHA-256 `d1a72fc7…e9ca8`).
- **What it authorises:** corrective pass 2, as set out in `d14/decisions/APG_D14_STAGE1_CORRECTIVE_PASS_2_DECISION_PAPER.md`, SHA-256 `23d2adb980216c9703287cd8803570dc2fab3cf48f037dfa1d39a0d3029f0ea5`, checked by the builder at filing. This covers every decision in its table (A.2, B.2, C, F.1, F.2, K.1, K.2, K.3) and its stop rule.
- **What it does not authorise:** this is corrective work only. It is not stage 1 acceptance, and it does not authorise stage 2, stage 3, Part B or final verification.

## How it came about
1. **The reviewer's second gate review** of freeze `d5f87d6b…85c8`, 2026-11-04, did not recommend progression: `rec/reviews/RECEIVED_REVIEW_2026-11-04_STAGE1_GATE_2.txt`.
2. **The owner's direction of 19:36 on 2026-11-04** asked the builder for a decision paper.
3. **Six drafts, each reviewed by the reviewer in one pass.** The drafts are in `d14/decisions/` (`…_DRAFT_v1.md` to `…_DRAFT_v6.md`), and the reviews in `rec/reviews/` (`RECEIVED_REVIEW_2026-11-0{4,5}_CORRECTIVE_PASS_2_PAPER_DRAFT_{1..6}.txt`).
4. **The reviewer's check of the final text,** relayed by the owner at 10:44 on 2026-11-05: `RECEIVED_REVIEW_2026-11-05_CORRECTIVE_PASS_2_PAPER_FINAL.txt`. It found the final text ready to post.

## Gaps the builder found while preparing the paper (reported under the stop rule, and now authorised for correction)
- **F.1:** the disk floor reached during a run.
- **F.2:** signal handling.
- **F.2 (c), now P:** a timeout kills only the direct child.
- **K.2:** the case runners run their cases in-process with no time limit.

## What comes first
The audit of section P.9, before any implementation:
- every successor child-start site;
- every path by which a successor runs beneath another successor or an M10 tool;
- the outside-service record of P.2.

If any site, path or service cannot be brought under P, or ruled out, the builder stops and reports.

## Addendum, 23:00 on 2026-11-05: amendment 1 authorised
- **Posted:** the owner authorised amendment 1 at 23:00, filed verbatim as `rec/reviews/RECEIVED_OWNER_POST_2026-11-05_2300_AMENDMENT_1_AUTHORISATION.txt`. It covers `d14/decisions/APG_D14_STAGE1_CORRECTIVE_PASS_2_AMENDMENT_1.md`, SHA-256 `211971452c8f02ac0d24514ebc9a12c1c0cded3eeb55f2c918f125a775c6d382`, checked by the builder at filing: decisions AM-1 to AM-6, and findings 11 to 13.
- **What the work is under:** the posted paper `23d2adb9…f0ea5` as amended, for corrective work only. This is not stage 1 acceptance, and it does not authorise stage 2.
- **The stop rule is in force.**
- **How it came about:**
  - the P.9 stop report;
  - the reviewer's review of it;
  - the paper-to-code verification;
  - amendment draft 1 and its review;
  - the final text (`841a322d…`), the reviewer's check of it, and the one AM-5 (a) wording correction (`211971…`);
  - the reviewer's confirmation (`RECEIVED_REVIEW_2026-11-05_2259_AMENDMENT_1_READY.txt`).
- **The owner's instruction** with the post: "Build until complete". The owner is away, so the builder works unattended. Decisions that are not covered are recorded and not taken. A stop-rule event is reported and stops the work it concerns.

## Addendum, 10:55 on 2026-11-06: amendment 2 authorised
- **Posted:** the owner authorised amendment 2 at 10:55, filed verbatim as `rec/reviews/RECEIVED_OWNER_POST_2026-11-06_1055_AMENDMENT_2_AUTHORISATION.txt`. It covers `d14/decisions/APG_D14_STAGE1_CORRECTIVE_PASS_2_AMENDMENT_2.md`, SHA-256 `a3cc26b5073ea4082de6a7a52013767634e076b64886bba0f49524a7f706cd6e`, checked by the builder at filing: decisions AM2-1 to AM2-4.
- **How it came about:**
  - stop 2 (`rec/ISSUE_RECORD_2026-11-05_CORRECTIVE_PASS_2_STOP_2_K2.md`);
  - draft 1 and the reviewer's review of it;
  - draft 2, and a read-only independent audit of it by a separate agent (`d14/decisions/INDEPENDENT_AUDIT_AMENDMENT_2_DRAFT_2.md`: 1 blocking, 2 should-fix and 7 minor findings, all applied);
  - draft 3, which is the final text;
  - the reviewer's scoped confirmation (`rec/reviews/RECEIVED_REVIEW_2026-11-06_1053_AMENDMENT_2_SCOPED_CONFIRMATION.txt`).
- **What the work is under:** the paper `23d2adb9…f0ea5`, as amended by amendments 1 and 2, for corrective work only. This is not stage 1 acceptance, and it does not authorise stage 2. The stop rule (H and AM-8) remains in force.

## Addendum, 14:38 on 2026-11-06: amendment 3 posted
- The owner posted amendment 3 (`APG_D14_STAGE1_CORRECTIVE_PASS_2_AMENDMENT_3_DRAFT_v2.md`, SHA-256 `89e5a268242c8ce0471d45af12a056c444fad25c57978741e5f3cdb283436715`; byte-identical copy `APG_D14_STAGE1_CORRECTIVE_PASS_2_AMENDMENT_3.md`), decisions AM3-1 to AM3-5 with S11 in AM3-4. Post filed: `rec/reviews/RECEIVED_OWNER_POST_2026-11-06_1438_AMENDMENT_3_AUTHORISATION.txt`.
- Reviewer's confirmation (14:02) filed: `rec/reviews/RECEIVED_REVIEW_2026-11-06_1402_AMENDMENT_3_DRAFT_2.txt`. Its implementation-level points, carried into the build: a test that a `classes` map lacking the group refuses the exit-3 form; AM3-2's "unchanged" read as "on the final candidate" (wording in the test only; the posted text is not edited).
- Corrective work only; not stage 1 acceptance; no stage 2. Stop rule H, AM-8 in force.

## Addendum, 17:31 on 2026-11-06: amendment 4 posted
- The owner posted amendment 4 (`APG_D14_STAGE1_CORRECTIVE_PASS_2_AMENDMENT_4_DRAFT_v1.md`, SHA-256 `b6be070ea935e4242d9411780f6823b46a2e7fdb7ccda546c01073227e47a7d6`; byte-identical copy `…_AMENDMENT_4.md`), decision AM4-1 option A (S12: M10's m2 verdicts from M10's own `run_one`, through an out-of-tree harness). Evidence work only. Post filed: `rec/reviews/RECEIVED_OWNER_POST_2026-11-06_1731_AMENDMENT_4_AUTHORISATION.txt`. Not reviewed by GPT (the owner posted directly).
