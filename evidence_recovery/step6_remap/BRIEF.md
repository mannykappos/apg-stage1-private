# Brief: scoped re-mapping (step 6 of the recovery), APG D14 stage 1, corrective pass 2, amendment 5

You are a fresh, independent agent. You have not seen the builder's work. Your output is labelled **INDEPENDENT READ-ONLY (agent)**. You map a fixed list of requirements to the tests and evidence of one frozen build, and classify each one. You do not fix anything, and you do not judge whether stage 1 is accepted.

## Bases (named so your report can use short paths)

- `SCR` = `<WORKSPACE>/scratchpad`
- `FREEZE` = `SCR/recovery/freeze5/a/APG-M11-S1.zip`. Expected SHA-256 `ee1ce3ec4be1a76482595688cfd9b41910fa26f4c9fe9a936f8971e86b5e0735` (commit `e9e11d9`). The two builds' hashes are in `SCR/recovery/freeze5/two_builds_sha256.txt`. Check the hash yourself, then extract it fresh into `SCR/remap6/x/` and read the code there.
- `M10` = `SCR/recovery/in/APG_M10_CODE_AND_DATA.zip` (expected SHA-256 starts `bd5c592a19858180`). It is immutable.
- `EV5` = `SCR/recovery/ev5/`. This is the full step 5 evidence on this freeze, in amendment 5's AM5-6 order:
  - `progress51.txt` (step 1: the T, W and M sets on Python 3.13 and 3.12, in `run_sets/`);
  - `progress523.txt` (steps 2 and 3: `compare_py313/` and `compare_py312/`, the m2 slices and runs; five interruptions are logged there, and the partial runs are kept in `interrupted/`);
  - `progress54.txt` (step 4: `historical_py313/` and `historical_py312/`, `static/`, `audit_final/`).
  - `compare_py31x/wrong_label_m56/` holds outputs superseded for a label mistake. They are kept, not evidence.
- `REPO` = `/home/claude/apg-stage1-private` (git, branch `records`). Read it only with `git --no-optional-locks` and ordinary reads. It holds:
  - `authority/`: the decision paper, amendments 1 to 4, amendment 5 draft v4, and the owner's posts;
  - `recovery/received/`: the recovery authorisation of 2026-11-11 15:48, the owner's rulings and answers;
  - `build_log/PASS2_BUILD_LOG_RECOVERY.md`: the builder's log of the recovery, with mistakes disclosed;
  - `records/PASS2_BUILD_LOG.md`: the earlier pass's log;
  - `evidence_c9b324eb_review_pack/MAPPING_AGENT_REPORT.md`: the first independent mapping, on the earlier freeze `c9b324eb`, with its 127-row requirement table, E points and discrepancy list;
  - `evidence_recovery/`: the step 2 and 3 suite logs of the recovery.
  - The change record is in the freeze: `APG-M11-S1/programme/CHANGE_RECORD_APG-M11-S1.md`.

## Background you need

- The workspace was wiped on 2026-11-11. The tree was rebuilt from recorded hashes and papers. Where code had to be rewritten, the build log says so. Freeze `ee1ce3ec` is the rebuilt freeze.
- Before the wipe, an earlier freeze `303b6414` had a scoped re-mapping (v4): **56 closed, 8 partly addressed, 0 open**. Its item-level report was lost in the wipe; only those counts survive (`REPO/recovery/received/RECEIVED_OWNER_ANSWERS_2026-11-09_TO_2026-11-11.txt`). An earlier re-mapping (v3) was lost entirely.
- The first mapping (`MAPPING_AGENT_REPORT.md`, on `c9b324eb`) does survive, item by item.

## Scope: these 65 items, and only these

The owner's authorisation scopes this to "the 64 items plus row 42". The builder reconstructed that list from amendment 5 draft v4. This is a builder reading; report it as such.

- **Appendix A part 1** of amendment 5, every entry (58 items, row 42 among them):
  - rows 4, 6, 11, 12, 15, 19, 21, 22, 23, 25, 29, 30, 31, 34, 36, 41, 42, 46, 50, 51, 52, 53, 55, 56, 57, 59, 60, 62, 63, 66, 68 (with discrepancy 6), 69, 71, 72, 73, 75, 77, 79, 81, 83, 85, 90, 91, 92, 95, 96, 97, 98, 99, 100, 101, 121 (with discrepancy 1), 7 (with discrepancy 7), 113 (with discrepancy 20);
  - discrepancies 10, 14, 17 and 21.
- **Appendix A part 3**: discrepancies 15, 16, 18 and 22.
- **Rows 106, 110 and 111**, which waited on S13 and S14 and are answered by AM5-1 to AM5-3 and the step 5 evidence.

"Row N" means row N of the first mapping's requirement table. "Discrepancy N" means its discrepancy list. Use the requirement wording there, read with the decision paper and amendments it cites, and with amendment 5's own text for that item (Appendix A, AM5-1 to AM5-5) and the owner's rulings (S15 A, S16 A, S17 (a) A and (b) A, the row 6 and 17 plan corrections, and the row 68 limits answer of 2026-11-12 06:32).

If you find the reconstruction itself is wrong, for example an item amendment 5 sends to "the scoped re-mapping" is missing, say so. Map it too, and list it separately.

## How to classify

- **C = CLOSED BY EVIDENCE.** The requirement is met, and you can name the test or evidence that shows it. For a test: the named test exists in the freeze, asserts what the requirement says (not something weaker), and its file ran OK on both Pythons in `EV5/run_sets/py313_T` and `py312_T`, with no skips or early returns.
- **P = PARTLY ADDRESSED.** Some of it is shown, some is not. Say exactly what is missing.
- **O = STILL OPEN.** Not shown.
- If an item is, by the owner's or the paper's own terms, done only at packaging (the package is not built yet), say so. Classify it as it stands now, and mark it "packaging".
- Be as strict as the first mapping was. Do not give credit for intent, comments or the builder's log alone. Check the code and the evidence.

## Rules

- **Read-only.** Write only under `SCR/remap6/`. Do not change `EV5`, `REPO`, the freeze, M10, or anything else.
- Do not run the long jobs (the m2 runs, the full suites). You may run small read-only commands: `ls`, `grep`, `sha256sum`, `unzip -l`, `unzip -p`, `date`, `git --no-optional-locks log/show`, and short AST or text reads with `python3 -I -S`. You may run one named test file on the fresh extraction if you need to see a test's behaviour, and must say so.
- Disclose every script you write and every command beyond reading.
- No network.
- **Privacy.** Never copy an environment variable's value, a session link, a credential, an e-mail address, or a long workspace path into your report. Write paths relative to the bases above, for example `EV5/static/route_children.txt` or `FREEZE:tests_tools/test_no_timeout_kill.py:437`.
- Take the time from `date` whenever you state one (Australia/Melbourne).

## Output

Write `SCR/remap6/out/REMAP6_REPORT.md`, starting with the title `INDEPENDENT READ-ONLY RE-MAPPING (agent), recovery step 6, freeze ee1ce3ec`. It must contain:

0. **Method and limits.** Inputs and their hashes as you checked them, what you ran, what you wrote, and what you could not check.
1. **The table**, one row per item, with these columns:
   - `#` (row or discrepancy);
   - requirement (short);
   - class now (C/P/O);
   - test / evidence (exact names, file:line);
   - what is missing (for P and O);
   - class in the first mapping (`c9b324eb`).
2. **The scope check.** Is the 65-item reconstruction right? Anything missing or extra?
3. **Counts.** C, P, O over the 64 items (the 65 without row 42), then row 42 on its own, then all 65.
   - Compare with v4's surviving counts (56 C, 8 P, 0 O over 64 items).
   - Say plainly: with v4's item list lost, the comparison is possible only at the level of counts.
   - List every item you class P or O, and for each, whether it was C, P or O in the first mapping.
4. **New discrepancies.** Anything you find wrong that is outside the item list: a test that does not do what its name says, evidence that disagrees with the build log, a hash that does not match, a claim in the change record or log not supported by the evidence. Number them D6-1, D6-2 and so on.
5. **Summary**, in plain words, in at most 12 lines.

Keep the report factual and short per row. When you finish, reply with the counts and the list of P and O items only.
