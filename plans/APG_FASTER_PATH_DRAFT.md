# APG: the faster path

Draft for discussion, 14 November 2026 · Claude (builder) for Emmanuel (product owner) · BUILDER-EXECUTED: NOT INDEPENDENT

This draft authorises nothing. It follows your direction of 13 November, 21:10: "Ok if its safe then we do it" (`RECEIVED_OWNER_DIRECTION_2026-11-13_2110_SPEED_UP_APPROACH.txt`). Each milestone below starts only when you post its own authorisation, and I draft those for you. The times are my estimates, unverified. Stage 1 of D14 took far longer than planned, so treat them as rough.

## 1. Where APG actually stands

**A correction first.** Last night I told you Phase 2 had not started. That was wrong. Three Phase 2 pieces are already built. They are waiting for acceptance, not to be built.

| Part | Status |
| --- | --- |
| **The 18 existing releases** (M10 is the latest, about 85,000 lines) | Built. Under the D14 audit: none has passed yet. |
| **D14 stage 1** (the M10 audit and its corrective work) | Final evidence run in progress, due about 8pm tonight. Then the re-mapping check, the documents, an agent audit and GPT's gate review. |
| **Phase 2, P2S-01: the PostgreSQL foundation** (APG-F1) | Built. Not accepted. |
| **Phase 2, P2S-02: the audit-integrity fix** (APG-F2) | Built. Not accepted. |
| **Phase 2, P2S-03: stopping broken data deliveries being accepted** (APG-F3) | Built. Not accepted. |
| **M1-0** (the correction for the Q4 and Q8 money defects in M10) | Built. Its evidence gate was passed on 27 October. Not accepted. |
| **What blocks those four** | GPT's JU-1 audit of 27 October found 13 problems (3 critical). By your decision DR-10, Phase 2 pieces cannot be accepted until the D14 audit of all 18 releases is done. |
| **Part B: three known defects** (P2-B6, P2-B7, P7-B1: recovery and timing faults in the job-handling code) | Open and blocking. Kept out of stage 1's work. |
| **CR-11, the data supply plan** | Approved by you last night. Design only. |
| **Integration** | AUIF, its extension (connector kit, webhooks, file import, module client, Governor adapter) and APG's own AUIF adapter (M8 to M8.1) are built. |

## 2. What is left, in phases (Master Blueprint v1.0, section 15)

- **Phase 2, data foundation.** Three pieces built (above). Still to come: P2S-04 (an internal integration route, possibly through AUIF), P2S-06 (the money and currency foundation), and the slices from P2S-09 onwards, which are still to be planned.
- **Phases 3 to 5:** builders' own data entry; documents and site logging; connections to their software. CR-11 is the detailed design for these. AUIF already supplies Phase 5's plumbing.
- **Phase 6:** more intelligence, mostly by strengthening the engines already in M10.
- **Phases 7 and 8:** end-to-end testing, then the separate go-live decision, with Amir.

## 3. The proposed milestones

Each is one authorisation from you. Each one states up front:
- what "done" means;
- when I must stop and ask you;
- what it may and may not change.

Each finished milestone gets an independent agent check (its findings fixed first), then one GPT review that lists every problem in one pass.

**M-A. Finish D14 stage 1.** This is already authorised and in progress. Estimate: 1 to 2 days, mostly review turnaround.

**M-B. The rest of D14 (stages 2, 3 and 4) as one milestone.**
- **M9.4 and M7.3:** the identities are checked first, against the exact release files. M10's audit is then reused only for files proven byte-identical, which is about 95% of each. The 41 differing files in each, and everything they touch, are reviewed in full. If what a changed file touches cannot be shown, that release gets the full review instead. This is the rule GPT set in the D14 plan.
- **The other 15 releases:** a formal sign-off of the review already done, confirmation of the earlier fixes (F-52 to F-66, F-68, F-69), and GPT's decision on the CF runs.
- **Then your 18 dispositions** and the one records-only release.
- Estimate: 3 to 6 days.

**M-C. Clear JU-1, so that P2S-01 to P2S-03 and M1-0 can be accepted.**
- It fixes the evidence-side findings in the four pieces: the runner that can report a pass while an approval is pending, the missing mutation coverage and the reachability probes.
- It also completes the independent static reviews and the PostgreSQL runs.
- Q4 and Q8 close through M1-0's second stage.
- Any fix that changes how the product calculates would be named in the authorisation, or brought to you first.
- It can run alongside M-B: they touch different code.
- Estimate: 4 to 7 days.

**M-D. Part B: the three blocking defects.**
- These change product logic, so they get their own authorisation, with the fix for each stated beforehand.
- It can run alongside M-C once its authorisation is agreed.
- Estimate: 3 to 5 days.

**M-E. Plan the rest of Phase 2 now, in parallel.**
- **Planning only, no code:** P2S-04, P2S-06 and the slices from P2S-09 onwards, cross-checked with CR-11, with AUIF as the integration route.
- **The order rule** that decides which slice may be built before the one before it is accepted. GPT asked for this to be settled before more building.
- Estimate: 1 to 2 days of writing, plus one GPT review.

Then Phases 3 to 5 follow as CR-11's releases, one authorisation each, with Phase 5 shortened by AUIF.

## 4. What does not change

- Every finished milestone still gets an independent agent check and a GPT review.
- M10's audit is reused only for identical files; differing files and everything they touch get a full review.
- The blocking defects (Part B, Q4, Q8) are fixed, never relaxed.
- No production systems, credentials or customer data; synthetic data only. No work for Amir until the end.
- Nothing is called accepted or production-ready until you accept it.

## 5. Your decisions, one at a time, when you are ready

1. Adopt this milestone shape (M-A to M-E)?
2. Run M-B and M-C side by side?
3. Start M-E's planning now, while stage 1 finishes?

I will go through each with you in plain terms before drafting its authorisation.

**What I have not yet confirmed.** I have not confirmed the exact scope of P2S-04 to P2S-09 or the full JU-1 fix list against every record. Both are checked before the M-C and M-E authorisations are drafted.
