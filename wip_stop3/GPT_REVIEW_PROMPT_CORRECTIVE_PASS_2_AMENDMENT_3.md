You are the reviewer for APG D14 stage 1. During the build of corrective pass 2 (paper `23d2adb9…f0ea5`, as amended by amendment 1 `211971…d382` and amendment 2 `a3cc26b5…cd6e`), the builder found that section C.1 makes E point 3 unmeetable. While checking that, it found that C.1 also moves the identity check of the moved imports to the end of the run. It stopped under H and AM-8, and has made no logic change since.

Attached:
- `ISSUE_RECORD_2026-11-06_CORRECTIVE_PASS_2_STOP_3_C1.md`: the stop report (S9, S10, two readings, disclosures);
- `APG_D14_STAGE1_CORRECTIVE_PASS_2_AMENDMENT_3_DRAFT_v1.md`: the proposed amendment (AM3-1 to AM3-5);
- `WIP_at_stop_3.diff`: the uncommitted work in progress, for reference;
- `S10_demonstration.txt`: the output of the temporary-copy run behind S10;
- the paper and amendments 1 and 2, for reference.

**Please review all of it in one pass, and list every problem you find in one consolidated answer.** Do not stop at the first problem.

Please check:
1. **S9.** Does C.1, together with C.2's "nothing listed is imported first", really make E point 3 ("the start line `IMPORT apg <real path>` asserted on a real runner") unmeetable? Is any real runner left that imports `apg` before `evkit.start`?
2. **S10 and AM3-1.**
   - Is the gap real, and is it a behaviour gap the paper does not list?
   - Do you recommend option A (a post-load identity check, before any item, refused in C.1's form) or option B (recorded as a limitation)?
   - For A, check where the check runs (after A.1's selection for case runners), its refusal form, its tests, and that the comparisons stay stop-rule checks.
3. **AM3-2.** Option A (point 3 rewritten, with no new line) or option B (a new `IMPORT_LOAD` line)? Does option A keep point 3's purpose?
4. **AM3-3.** Is asserting the child's `apg` path through the existing child probe an acceptable reading of E point 17's first half?
5. **AM3-4.** Is the checker change for AM2-2 (d)'s `CHECK … INDETERMINATE exit=3` form right, and no wider than that form?
6. **AM3-5.** The disclosures (mistakes 24 and 25), and the K.1 test's placement under reading 7.
7. **The work while waiting.** The builder goes on writing the E-point tests that S9 and S10 do not touch, as test code only, with no logic change. Say whether that is consistent with H.
8. **The work-in-progress diff,** if you look at it. List any defect you see. It is not offered for acceptance.
9. **Anything else** that is wrong, missing, or ambiguous enough to need rewording before the owner posts amendment 3.

**How to answer:**
- Separate required changes from optional suggestions.
- Say for each AM3 decision whether you recommend the builder's option.
- End with whether amendment 3, with your required changes, is ready for the owner to post.

This is a review of a decision paper amendment. It is not technical acceptance.
