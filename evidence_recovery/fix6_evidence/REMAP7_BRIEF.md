# Brief: scoped re-mapping after fix 6, APG D14 stage 1, corrective pass 2, amendment 5 recovery

You are a fresh, independent agent. You have not seen the builder's work. Your output is labelled **INDEPENDENT READ-ONLY (agent)**. You map a fixed list of requirements to the tests and evidence of one frozen build, and classify each one. You do not fix anything, and you do not judge whether stage 1 is accepted.

## Bases (named so your report can use short paths)

- `SCR` = `<WORKSPACE>` (in your report write it as `SCR`, never the long path).
- `FREEZE` = `SCR/recovery/freeze6/a/APG-M11-S1.zip`. Expected SHA-256 `a7f599f936937d5fd06a720d19ba3bbd1966ef81e2b9395687db28501c2f76bd` (commit `a5d8b99`). The two builds' hashes are in `SCR/recovery/freeze6/two_builds_sha256.txt`. Check the hash yourself, then extract it fresh into `SCR/remap7/x/` and read the code there.
- `OLDFREEZE` = `SCR/recovery/freeze5/a/APG-M11-S1.zip` (`ee1ce3ec…`), the freeze the previous re-mapping read. Use it only to see what changed.
- `M10` = `SCR/recovery/in/APG_M10_CODE_AND_DATA.zip` (expected SHA-256 starts `bd5c592a19858180`). It is immutable.
- `EV6` = `SCR/recovery/ev6/`. This is the full evidence on this freeze, in amendment 5's AM5-6 order:
  - `progress51.txt` (step 1: the T, W and M sets on Python 3.13 and 3.12, in `run_sets/`);
  - `progress523.txt` (steps 2 and 3: `compare_py313/` and `compare_py312/`, the m2 slices and runs);
  - `progress54.txt` (step 4: `historical_py313/` and `historical_py312/`, `static/`, `audit_final/`, including the planted-secret demonstration `secret_stop_demo.txt` and the new conclusions file `outside_services_conclusions.txt`);
  - `interrupted/` holds partial runs cut off by container restarts (logged in `progress51.txt` and `progress523.txt`). They are not evidence.
- `EV5` = `SCR/recovery/ev5/`, the same evidence on the old freeze. Use it only for comparison.
- `REPO` = `/home/claude/apg-stage1-private` (git, branch `records`). Read it only with `git --no-optional-locks` and ordinary reads. It holds:
  - `authority/`: the decision paper, amendments 1 to 4, amendment 5 draft v4, and the owner's posts;
  - `recovery/received/`: the recovery authorisation of 2026-11-11 15:48, the owner's rulings and answers (including 2026-11-13 18:34, "Fix them, then re-run");
  - `build_log/PASS2_BUILD_LOG_RECOVERY.md`: the builder's log of the recovery, with mistakes disclosed;
  - `records/PASS2_BUILD_LOG.md`: the earlier pass's log;
  - `evidence_c9b324eb_review_pack/MAPPING_AGENT_REPORT.md`: the first independent mapping, on `c9b324eb`, with its 127-row requirement table, E points and discrepancy list;
  - `evidence_recovery/step6_remap/REMAP6_REPORT.md`: **the previous re-mapping** (step 6, on `ee1ce3ec`, by another fresh agent): 37 closed, 28 partly addressed, 0 open, and its new discrepancies D6-1 to D6-8;
  - `builder_tools/current_fix6/`: the builder tools that made `EV6`, with `SHA256.txt`;
  - `evidence_recovery/fix6_focus/`, `evidence_recovery/fix6_evidence/`: the builder's focused checks and the masked progress records.
- `FIXPLAN` = `SCR/recovery/FIX6_PLAN.md`: the builder's own list of what fix 6 changed for each P item and D6 item. It is the builder's claim, not evidence. Check each claim against the code and `EV6`.
- The change record is in the freeze: `APG-M11-S1/programme/CHANGE_RECORD_APG-M11-S1.md`.

## Background you need

- The workspace was wiped on 2026-11-11 and the tree rebuilt. Before the wipe, a re-mapping (v4) of an earlier freeze `303b6414` counted **56 closed, 8 partly addressed, 0 open** over 64 items. Only those counts survive.
- Step 6 re-mapped the rebuilt freeze `ee1ce3ec`: **37 C, 28 P, 0 O** over the 65 items. The owner then decided (2026-11-13 18:34): fix them, then re-run.
- Fix 6 changed only tests, test helpers, pins, builder tools, the change record and the logs (no product or successor-tool logic, by the owner's rule). The new freeze is `a7f599f9`. `EV6` is its full evidence.

## Scope: the same 65 items as step 6, plus D6-1 to D6-8

1. **The 65 items** exactly as step 6 scoped them (see `REMAP6_REPORT.md` section 1 and its scope check in section 2). Use the same row numbering.
2. **D6-1 to D6-8**, step 6's new discrepancies. For each, say whether fix 6 resolved it, and how you know. D6-8 (the documents carry this freeze's timeout-kill counts) belongs to the documents, which are not written yet: mark it "packaging", and give the counts the documents must carry, from `EV6`.

"Row N" means row N of the first mapping's requirement table. "Discrepancy N" means its discrepancy list. Use the requirement wording there, read with the decision paper and amendments it cites, and with amendment 5's own text for that item and the owner's rulings, as step 6 did.

## How to classify

- **C = CLOSED BY EVIDENCE.** The requirement is met, and you can name the test or evidence that shows it. For a test: the named test exists in the freeze, asserts what the requirement says (not something weaker), and its file ran OK on both Pythons in `EV6/run_sets/py313_T` and `py312_T`, with no skips or early returns.
- **P = PARTLY ADDRESSED.** Some of it is shown, some is not. Say exactly what is missing.
- **O = STILL OPEN.** Not shown.
- If an item is, by the owner's or the paper's own terms, done only at packaging (the package is not built yet), say so. Classify it as it stands now, and mark it "packaging".
- Be as strict as step 6 was. Do not give credit for intent, comments, `FIXPLAN` or the builder's log alone. Check the code and the evidence. Where step 6 named exactly what was missing, check that exact thing.
- Do not invent new requirements. If a fix meets what step 6 said was missing but you think the requirement asks for more than step 6 said, say so in the row, and list it in section 4.

## Rules

- **Read-only.** Write only under `SCR/remap7/`. Do not change `EV6`, `EV5`, `REPO`, the freezes, M10, `FIXPLAN`, or anything else.
- Do not run the long jobs (the m2 runs, the full suites). You may run small read-only commands: `ls`, `grep`, `sha256sum`, `unzip -l`, `unzip -p`, `diff`, `date`, `git --no-optional-locks log/show`, and short AST or text reads with `python3 -I -S`. You may run one named test file on the fresh extraction if you need to see a test's behaviour, and must say so.
- Disclose every script you write and every command beyond reading.
- No network.
- **Privacy.** Never copy an environment variable's value, a session link, a credential, an e-mail address, or a long workspace path into your report. Write paths relative to the bases above, for example `EV6/static/route_children.txt` or `FREEZE:tests_tools/test_no_timeout_kill.py:437`.
- Take the time from `date` whenever you state one (Australia/Melbourne).

## Output

Write `SCR/remap7/out/REMAP7_REPORT.md`, starting with the title `INDEPENDENT READ-ONLY RE-MAPPING (agent), after fix 6, freeze a7f599f9`. It must contain:

0. **Method and limits.** Inputs and their hashes as you checked them, what you ran, what you wrote, and what you could not check.
1. **The table**, one row per item, with these columns:
   - `#` (row or discrepancy);
   - requirement (short);
   - class now (C/P/O);
   - test / evidence (exact names, file:line);
   - what is missing (for P and O);
   - class at step 6 (`ee1ce3ec`);
   - class in the first mapping (`c9b324eb`).
2. **D6-1 to D6-8.** One row each: resolved, partly or not, with the evidence. D6-8 marked packaging, with the counts.
3. **Counts.** C, P, O over the 64 items (the 65 without row 42), then row 42 on its own, then all 65.
   - Compare with step 6 (37 C, 28 P, 0 O over 65) and with v4's surviving counts (56 C, 8 P, 0 O over 64).
   - List every item you class P or O, and for each its class at step 6 and in the first mapping.
   - List every item that went from C at step 6 to P or O now (a regression), if any.
4. **New discrepancies.** Anything you find wrong outside the item list: a test that does not do what its name says, evidence that disagrees with the build log, a hash that does not match, a claim in the change record, `FIXPLAN` or the log not supported by the evidence, a fix 6 change that reaches beyond tests, helpers, pins, builder tools and records. Number them D7-1, D7-2 and so on.
5. **Summary**, in plain words, in at most 12 lines.

Keep the report factual and short per row. When you finish, reply with the counts, the list of P and O items, and the list of D7 discrepancies only.
