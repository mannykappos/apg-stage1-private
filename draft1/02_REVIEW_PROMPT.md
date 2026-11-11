# Review prompt: APG Data Readiness Change Request (draft, 2026-11-11)

Paste this whole prompt, then attach the files in this folder. The same prompt works for GPT and for Gemini; run each separately and send both results back.

---

You are the independent reviewer of a draft change request for Anchor Profit Guardian (APG), a profit-protection product for construction builders. The product owner decides; Claude drafted it; you review it. Your review decides whether the design is ready for the owner's decisions.

## What is being reviewed

`01_CHANGE_REQUEST_DRAFT.md`: a first draft, for direction. It proposes how APG makes sure it has the data it needs to work. The owner's requirement, in his words: APG must inform the builder what data it needs; if the builder's existing software supplies only part of it (say 80%), APG must have the features to supply the rest, so it gets exactly what it needs.

The draft defines "fail-proof on our end" as two guarantees: APG never gives a wrong or overconfident answer because data was missing; and APG always knows and tells the builder what it lacks, per insight, and how to supply it.

## What you have to check it against

- `04_blueprint_sources/`: the locked APG Construction blueprint v1.0, Sections 03 to 13 (the domain model, data ingestion, the calculation engine, detection, schedule, materials, labour, recommendations, commercial, cash, quality), the Master Requirements Traceability Matrix, and two files of the separate 8 Intelligence Layers blueprint (shared financial foundation, data contracts).
- `03_CODE_INVENTORY.txt`: what the existing APG code holds (record kinds, which modules read which records, the supporting modules), generated from the code by the builder. You cannot see the code itself. Treat this file as the builder's evidence, check that the draft's claims are consistent with it, and say where a claim needs independent verification.

## How to review: one complete pass

Review ALL of the draft in ONE pass and list EVERY problem you find. Do not stop at the first problem, and do not return a partial review to be continued later: the owner wants every finding at once so the draft can be corrected in one round.

Check in particular:

1. **The requirement.** Do the two guarantees capture the owner's requirement? Is anything he asked for missing, or anything promised that cannot be built or tested?
2. **Consistency with the locked blueprint.** Is every row of "What the locked blueprint already guarantees" an accurate reading of the cited section? Does anything in the draft contradict, weaken or duplicate a locked requirement? Changes to locked sections need a formal amendment: flag anything that would need one.
3. **The data contract.** For each insight: are the records it lists the ones the blueprint requires? Is anything missing? Are the proposed minimum and good levels sensible for Victorian commercial builders (about $5–50m turnover)? Is the "below minimum" behaviour consistent with the blueprint's qualified-result rules? Some rows were drafted from rule names (R04 and R04b in particular): flag any you cannot confirm.
4. **The coverage matrix.** Are there inputs the blueprint needs that neither the matrix nor the code inventory covers? Are the four missing record kinds really missing, and are there others? Is "where builders usually hold it" right for that segment?
5. **The readiness report, gap filling, estimates and integration mapping.** Are they complete, simple enough for a busy builder, and safe (never a silent estimate, never a way around the Section 04 controls)? Which estimating methods, if any, would you allow?
6. **The decisions for the owner.** Are they the right decisions, framed so he can choose? Is anything missing?
7. **Anything else** that would stop this design from making APG work with real builder data.

## How to report

For every finding give:

- **Class:** blocking (must be fixed before the owner decides) · should fix · optional improvement · minor.
- **Where:** the section and table row of the draft.
- **What is wrong,** with the evidence: the blueprint section and paragraph, or the line of the code inventory.
- **The fix you recommend.**
- **Rough cost** of the fix: small, medium or large.

End with:

- a one-line verdict: ready for the owner's decisions, ready after the blocking fixes, or not ready;
- the total number of findings in each class;
- anything you could not check, and why.

Do not rewrite the draft. Do not approve anything on the owner's behalf.
