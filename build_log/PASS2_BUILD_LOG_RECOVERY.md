# APG D14 stage 1, corrective pass 2: recovery build log (BUILDER-EXECUTED: NOT INDEPENDENT)

Times are AEDT (UTC+11), read from the clock at each entry. This log continues the pass 2 build log, which was lost in the
workspace wipe of 2026-11-11. The lost log's entries up to amendment 5 draft 2 survive in records/PASS2_BUILD_LOG.md (from the AM5
review pack); everything after that is restated here from the conversation record and marked as such.

## 2026-11-11

- 15:31 Workspace loss found (recovery/LOSS_RECORD_2026-11-11.md). Nothing had been sent to the owner or to the reviewer.
- 15:48 Recovery authorisation received; filed verbatim as recovery/received/RECEIVED_OWNER_POST_2026-11-11_1548_RECOVERY_AUTHORISATION.txt.
- 15:50 Owner: "Done" (private repository mannykappos/apg-stage1-private created).
- 15:51 Repository attached with push access; cloned (empty).
- 15:58 Branch `main`: the stage 1 tree.
  - Commit 57f778a "base": freeze e4531a35's tree, recovered byte-exact from APG-M11-S1_STAGE1_PACKAGE.zip (131bffa4…33f9).
    The one-word commit message predates the repository; it is kept so the commit is unchanged.
  - Commit 0d1d233: the partial reconstruction of freeze c9b324eb, 1538 of 1555 files byte-exact to c9b324eb's recorded
    s1_sha256; 17 files still to finish (step 2).
- Branch `records` (this branch): the authority, the surviving records, the c9b324eb review pack evidence, builder tools, the
  stop 3 work in progress, the loss record and this log.

### Privacy (amendment 5, discrepancy 22, and the owner's decision of 2026-11-11 "Mask loose, accept in ZIPs")

- Before each push the branch is searched for the user's e-mail, the session and conversation ids, the container id and credential
  shapes. Two loose record files held the conversation id inside workspace paths; it is masked as `<SESSION-ID>`, with both hashes in
  recovery/PRIVACY_MASKING.csv.
- Branch `main` keeps logs/m81/baseline/00_hashes.txt unchanged: it is part of the immutable M10 baseline and holds the conversation
  id inside paths (2 lines). Masking it would change an immutable file and break every byte-exact comparison. It sits in the owner's
  own private repository; it is listed here, and will be listed in PRIVACY_CHECK.txt at packaging, as accepted under the owner's
  decision (inside the freezes and M10).
- Commit messages carry the `Co-Authored-By` line only. The session-link trailer the tooling suggests is left out, because it would
  write the session id into the repository, which the privacy rule forbids.

### Mistakes (numbering continues the lost log: 36 to 48 are restated in the documents)

- 49. The builder kept the whole pass 2 workspace on one disk with no off-box copy, although the session had already restarted four
  times. The wipe destroyed it. Corrected: every commit and every finished evidence step now goes to this repository, and checkpoint
  zips go to the owner at the end of steps 3, 5 and 7.
