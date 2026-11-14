# APG D14 stage 1, corrective pass 2 (recovery): the package for freeze a7f599f9

BUILDER-EXECUTED: NOT INDEPENDENT, except the files labelled INDEPENDENT READ-ONLY (agent) in `mapping/` and the pre-gate audit.
This is a gate package for review. It is not stage 1 acceptance and claims no production readiness. Stage 2 is not authorised.

The documents file (`APG_D14_Stage1_Pass2_Recovery_Documents_a7f599f9.docx`, sent beside this ZIP) explains the package: what was
built and rebuilt, the results, the open findings, the open gaps and every mistake. This README is the evidence index (decision paper
I.3; amendment 5 row 122). `SHA256SUMS` lists every file. `GPT_GATE_PROMPT.md` is the review prompt.

## The freeze

| File | What it is |
|---|---|
| `freeze/APG-M11-S1.zip` | Freeze a7f599f9 (SHA-256 `a7f599f936937d5fd06a720d19ba3bbd1966ef81e2b9395687db28501c2f76bd`), commit a5d8b99. Every evidence file below was made on it. |
| `freeze/two_builds_sha256.txt` | The freeze built twice from two fresh clones: byte-identical. |
| `freeze/frozen_compare.csv` | Against the M10 archive `bd5c592a…5192`: 3 changed, 1463 identical, 89 new, problems 0; 73 successor tools, every M10 original byte-identical. |

The in-tree change record is `APG-M11-S1/programme/CHANGE_RECORD_APG-M11-S1.md` inside the freeze; a copy is in
`records/CHANGE_RECORD_APG-M11-S1_in_freeze_a7f599f9.md`.

## The evidence, in amendment 5's AM5-6 order

Every job ran one at a time, with a 10 GB disk floor. The drivers and the job-by-job record are in `evidence/progress/`
(`progress51.txt`, `progress523.txt`, `progress54.txt`, `progress6.txt`). Three container restarts on 2026-11-14 interrupted three
jobs; each was rerun from the start, and the partial runs are not included (`evidence/progress/interrupted_runs_not_included.txt`).

**Step 1: the run sets** (`evidence/run_sets/`). Each set has `run_index.csv` (order, Python, command, start, seconds, exit, log,
the log's SHA-256 and `last_line`, a prefix of at most 300 characters of the log's last line), `logs/` and `tree_after.txt` (the
extraction checked file by file against the freeze after the set).

| Set | Python 3.13 | Python 3.12 |
|---|---|---|
| T: the 10 `tests_tools` files, 727 tests | `py313_T` (10 of 10 OK) | `py312_T` (10 of 10 OK) |
| W: the 19 wrappers | `py313_W`, `wrapper_check.txt` (no non-passing group line) | `py312_W`, same |
| M: `m8_mutants_s1` | `py313_M`, `m8_check.txt` (79 KILLED, 3 EQUIVALENT: MI-36, MI-39, MD-02) | `py312_M`, same |

**Step 2: the comparisons** (`evidence/compare_py313/`, `evidence/compare_py312/`): `golden.txt`, `pairs.txt`, `b6.txt`, `k2.txt`
(new side a7f599f9 against e4531a35, by the owner's answer of 2026-11-11 22:47) and `b6_recorded_totals.txt`,
`k2_recorded_totals.txt` (against d5f87d6b's recorded totals). All SAME on both Pythons.

**Step 3: m2** (same folders): `m2_logs/m10_script_list.txt` (the AM5-1 A substitute: M10's `--list`, 199 ids, RI10 at 51),
`m2h_000_040.txt` to `m2h_160_199.txt` (the five harness slices, AM5-2), `m2s.txt` (the successor as written), `m2_logs/equiv_1worker.txt`
(AM5-3 B: every EQUIV id SURVIVED with one worker) and `m2.txt` (the comparison with the AM4-1 and AM5-3 A1 allowances). `RESULT m2 SAME`
on both Pythons. M10's own breakdown in `m2.txt` (timeout kills: 39 on 3.13, 81 on 3.12) is explained in the documents.

**Step 4: the historical checks, the static checks and the audit**
- `evidence/historical_py313/`, `historical_py312/`: 100 rows each, exit and last line as recorded 100 of 100, archive files
  changed 0.
- `evidence/static/`: `frozen_compare.txt` (problems 0), `route_scan.txt` and `.csv`, `route_children.txt` (HOLDS),
  `case_inventory_limit_py313.txt` and `_py312.txt` (HOLDS).
- `evidence/audit/` (the P.9 audit and P.2's outside-service record, decision paper I.3):
  - `child_start_scan.txt`: the inventory of child-start sites and paths (P.9 part 1);
  - `outside_services.txt`, `process_api_reach.txt`: the outside-service record of P.2;
  - **`outside_services_conclusions.txt`: the conclusions, with the basis for each (audit item 6)**;
  - `secret_stop_demo.txt`: the planted-secret demonstration (row 6): the audit stops with exit 3, recording the name only;
  - `tset_start_scan.txt`: every process start in `tests_tools` with its limit (row 68): 102 sites, 102 with a limit;
  - `py313_finding13_probes.txt`, `py312_finding13_probes.txt`: the probe in each of finding 13's six path classes (AM-5(e),
    row 75), copied unchanged from the T logs at packaging.

## The process-identity and CLEANUP records (decision paper I.3; B.5; row 121)

- **`evidence/identity/py313_identity_records.txt`** and **`py312_identity_records.txt`**: every `P_IDENTITY` line the P, B, K.2 and
  F.2 tests wrote (704 per Python): each child's pid, start time and pgid, its `CLEANUP` lines and the supervisor that cleaned it up.
  Copied unchanged at packaging from the T logs, each block naming its source log and that log's SHA-256 from the run index.
- The same lines, in place, are in `evidence/run_sets/py31x_T/logs/T03`, `T08`, `T09` and `T10`. Search them for `P_IDENTITY`,
  `CLEANUP`, `CLEANUP_SUMMARY` and `CLEANUP_AMBIGUOUS`.
- Not every such test writes a record. The re-mapping names the ones that do not (row 121; D7-2).

## The mappings (`mapping/`)

- `REMAP7_REPORT_after_fix6_a7f599f9.md` (INDEPENDENT READ-ONLY (agent)): the scoped re-mapping of this freeze: 59 closed, 6 partly
  addressed, 0 open over the 65 items; D6-1 to D6-8; D7-1 to D7-11. Its brief is `REMAP7_BRIEF.md`.
- `REMAP6_REPORT_ee1ce3ec.md` (INDEPENDENT READ-ONLY (agent)): the previous re-mapping (37 / 28 / 0), on freeze ee1ce3ec.
- `MAPPING_AGENT_REPORT_first_c9b324eb.md` (INDEPENDENT READ-ONLY (agent)): the first mapping, on c9b324eb, with the requirement
  table the row numbers refer to.

## Authority and records

- `authority/`: the decision paper, amendments 1 to 4, amendment 5 draft v4 (`3649fa74…295b`), the owner's posts; and
  `authority/owner_recovery/`: the recovery authorisation of 2026-11-11 15:48, every owner answer since, and two records
  RECONSTRUCTED, NOT VERBATIM (the 2026-11-08 posts lost in the wipe).
- `records/`: the pass 2 build log up to amendment 5 draft 2 (`PASS2_BUILD_LOG.md`), the recovery build log
  (`PASS2_BUILD_LOG_RECOVERY.md`), the loss record, the issue and decision records, the fix 6 plan (`FIX6_PLAN.md`, the builder's own
  claims), the change record of the c9b324eb review pack (superseded by the copy from this freeze).
- `builder_tools/`: every builder tool and driver that made this evidence or this package, with `SHA256.txt`.
- `cited_names_check.txt`: every test name the documents and this README cite, checked against the freeze (row 120).

## Privacy (amendment 5, discrepancy 22)

`PRIVACY_CHECK.txt` records the package-level search of every file and every ZIP member. Workspace paths in text files are masked
as `<WORKSPACE>` and the session folder id as `<SESSION-ID>`; `MASKING.csv` lists each masked file with its SHA-256 before and after,
so a masked log can still be matched to the hash its run index recorded. The freeze ZIP is unchanged: its immutable M10 baseline file
`logs/m81/baseline/00_hashes.txt` holds the session folder id inside two paths, accepted under the owner's decision of 2026-11-11
("Mask loose, accept in ZIPs").
