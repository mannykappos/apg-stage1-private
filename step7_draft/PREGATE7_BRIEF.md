# Brief: pre-gate audit of the stage 1 pass 2 recovery package (freeze a7f599f9)

You are a fresh, independent agent. You have not seen the builder's work. Your output is labelled **INDEPENDENT READ-ONLY (agent)**. You audit a delivery package and its documents file before they go to the gate reviewer (GPT). You do not fix anything, and you do not judge whether stage 1 is accepted.

## What to audit

- `PKGZIP` = `SCR/pkg7/APG-M11-S1_PASS2_RECOVERY_PACKAGE.zip`. Check its SHA-256 yourself, extract it fresh into `SCR/pregate7/x/`, and verify every file against its `SHA256SUMS`.
- `DOC` = `SCR/docs7/APG_D14_Stage1_Pass2_Recovery_Documents_a7f599f9.docx` (the documents file; its source text is `SCR/docs7/DOCUMENTS.md`, which you may read instead, but check the .docx holds the same text: `pandoc -t plain` is available).
- `SCR` = `<WORKSPACE>` (write it as `SCR` in your report, never the long path).

Sources you may read to check the package against:
- `EV6` = `SCR/recovery/ev6/` (the unmasked original evidence; the package holds a masked copy);
- `SCR/recovery/freeze6/` (the freeze and its two builds);
- `REPO` = `/home/claude/apg-stage1-private` (branch `records`; read only, with `git --no-optional-locks` and ordinary reads): the authority, the owner's answers, the build logs;
- `SCR/remap7/out/REMAP7_REPORT.md` (the re-mapping the package includes).

## What the package must be (the requirements)

- Decision paper section I (in the package under `authority/`), especially I.3 (what the run records carry; the P.9 audit in `evidence/audit/` with the basis for each conclusion; the evidence index linking `evidence/audit/` and the process-identity and CLEANUP records; the run index's `last_line` described as a prefix of at most 300 characters) and I.5 (one ZIP plus one documents file).
- Amendment 5 draft v4 (in `authority/`): Appendix A part 2 (the documents: findings 9 and 11 to 13, reading 17, mistakes 20 to 35; the evidence index; the cited-names check; the scoped re-mapping; discrepancy 22's package-level privacy check, "any hit stops the packaging"); and amendment 1's AM-1 (what the documents must say for finding 11, including the explicit statement and the risk basis) and AM-5 (e) (the documents' corrections for mistake 20).
- The recovery authorisation (`authority/owner_recovery/RECEIVED_OWNER_POST_2026-11-11_1548_RECOVERY_AUTHORISATION.txt`): "Every rewritten item and every difference from 303b6414 disclosed in the documents"; the labels; the standing rules.
- The owner's answer of 2026-11-15 (`authority/owner_recovery/RECEIVED_OWNER_ANSWER_2026-11-15_STEP7_GO.txt`): the remaining gaps go to the gate disclosed, with no tree change.

## Check, at least

1. **Accuracy.** Every factual statement in `DOC`, `README.md`, `PRIVACY_CHECK.txt` and `GPT_GATE_PROMPT.md` against the evidence, the freeze and the records: hashes, counts, results, dates, file paths cited (do they exist in the package?), owner answers quoted (verbatim where claimed).
2. **Completeness** against the requirements above. Anything required that is missing.
3. **Overclaims and labels.** Any claim of acceptance, production readiness, independence or containment beyond the evidence; any builder work not labelled BUILDER-EXECUTED: NOT INDEPENDENT; any agent work not labelled INDEPENDENT READ-ONLY (agent).
4. **Disclosure.** Every rewritten item, every difference from 303b6414 that the surviving records show, every mistake in the logs, every open item from the re-mapping. Is anything in the logs or the re-mapping missing from `DOC`, or softened?
5. **The masked evidence.** Spot-check that masking changed only the workspace path and the session folder id (compare a few masked files with `EV6`'s originals), and that `MASKING.csv`'s "before" hashes equal the originals' hashes.
6. **The GPT prompt.** Does it ask for one pass with every problem listed, cover what the gate must decide, and avoid steering the reviewer?
7. **Privacy.** Do not reproduce any identifier. Run your own search of `PKGZIP` and `DOC` for e-mail-address shapes, `claude.ai`, `session_`, `/tmp/claude`, and credential shapes, and report only kinds and places. Say whether `PRIVACY_CHECK.txt` reports what you find.

## Rules

- **Read-only.** Write only under `SCR/pregate7/`. Do not change the package, `DOC`, `EV6`, `REPO`, the freezes or anything else.
- Do not run the long jobs. You may run small read-only commands, `sha256sum`, `unzip`, `diff`, `pandoc -t plain`, `python3 -I -S` for short reads, and the cited-names tool in the package (`builder_tools/cited_names_check_s1.py FREEZE DOC_TEXT README`) if you want to repeat it.
- Disclose every script you write and every command beyond reading. No network.
- Take the time from `date` (Australia/Melbourne) whenever you state one.

## Output

Write `SCR/pregate7/out/PREGATE7_REPORT.md`, titled `INDEPENDENT READ-ONLY PRE-GATE AUDIT (agent), package for freeze a7f599f9`, with:
0. Method and limits (inputs and hashes you checked, what you ran).
1. Findings, numbered PG-1, PG-2 …, each classed BLOCKING (must be fixed before the package goes to the gate), SHOULD FIX or MINOR, with the evidence (file, section, line) and a concrete fix. Fixes must not need a change to the frozen tree or the evidence; if one would, say so and class it separately as "needs a tree change (for the owner)".
2. What you checked and found in order.
3. Summary in at most 10 lines, with the counts.

Save the report as you go (the machine can restart). When done, reply with the counts and the one-line list of findings.
