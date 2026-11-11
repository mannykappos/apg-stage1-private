# APG-M10 -- the UX/UI prototype, director first (DRAFT, builder-made, prototype over synthetic data)

**Status: builder-made and locally tested; not accepted.** No independent review of APG-M10 has taken place (CF-56). This is a prototype: not a production screen, not an API, no login, no session, no live system. The page loads only its own files and sends nothing; the approval screen sends nothing either. Synthetic Builder Zero data only.

**Authority.** The product owner, 2026-10-21: "Authorise M10 as proposed, director first".

**Open it.** Open `ui/index.html` in a browser (no server needed). Choose who you are viewing as at the top:
* Dana, the director of Builder Zero One (the main view);
* Drew, the director of Builder Zero Two;
* Pat, a project manager who may see PRJ-001 only.

**What it shows.** Six screens: Portfolio, Projects (figures, findings, recommendations), Data health, Imports, Approvals and Materials (buy-timing).
* **Every amount is a value the existing APG code returned.** It is shown with its state (authoritative, provisional, or a hatched "Cannot assess" that is never a zero), and selecting it opens its evidence: the calculation, the reasons, the records it used and left out, and the run key.
* **Nothing is added up across projects.** APG has no portfolio-level figure (I-145).
* **Estimates are labelled as estimates.** No screen presents an estimate as a realised saving: an amount counts as realised only after APG's verification step, which this prototype never runs.
* **What each person sees comes from a project-action port of the M9 contract.** The port is a fixed synthetic stand-in for the Engine's (EDR-31). The approvals screen is the real `present()` answer, with the exact request it would send.

**How it was built.** `apg_ui/viewmodel.py` runs the existing APG code on Builder Zero. `tools/build_m10_views.py` writes `ui/data/views.js` from it, and `--check` proves the stored file is current. `ui/` holds the page, its styles and script, and IBM Plex fonts (OFL). The demonstration state, with reviews, proposals and one approval, is scripted with synthetic people as the M7 golden runs do (I-149).

**Checks.**
* `tests_m10/`: 19 view-model tests.
* `ui_tests/run_ui_tests.js`: browser tests in headless Chromium with axe-core. They check every screen of every view in light and dark, every amount's evidence, the ledger values, the wording about savings, the drawer, approvals, access, data health, materials, phone width and the keyboard.
* `tools/sabotage_m10.py`: 19 seeded breakages, each caught.
* `tools/run_regression_m10.py`: R01 to R08 against APG-M8.1-R1.

Details: `programme/CHANGE_RECORD_APG-M10.md`; screenshots: `logs/m10/screens/`.

**Unchanged and still open.** No APG application code, existing test, data or specification changed. CF-53 is still open, so Builder Zero tenant zero_two still cannot be assessed through the connected-systems route; the data-health screen shows why. CF-57 lists the product decisions the prototype leaves open. Every open EDR and CF item stays open, CF-41 stands, and the construction definitions stay PROPOSED.

How to re-check: the APG-M10 section of `RUN_COMMANDS.txt`.

---- the APG-M8.1-R1 readme follows, unchanged ----

# APG-M8.1-R1 -- records only: the independent auditor's result for APG-M8.1 (DRAFT, builder-made, non-production)

**Status: builder-made, records only; not accepted.** No independent review of this records release has taken place.

**Authority.** The product owner, 2026-10-21: "Authorise the records-only release for the M8.1 audit result". As in APG-M8-R2 (the product owner's decision "Update the 2 lists"), the declared-file lists of the M8 checks that would otherwise report this release's files gain those files. Since APG-M8.1 those lists are held in three files (`tools/run_regression_m81.py`, `tools/run_regression_m8.py`, `tests_m8/test_m8_boundary.py`). That is the only change outside the records.

**What is recorded.**
* **AD-21, APG-M8.1:** "scoped audit passed". No defect was found in the audited scope, and no correction build is indicated. The auditor ran the 172 M8 tests, the 150 groups (Python 3.13.5), the 17 sabotage cases and the 82 mutants (79 killed, 3 documented equivalent, 0 survived).
* **Qualified.** Python 3.12 was not reproduced, so the builder's Python 3.12 results remain builder evidence. The real-Governor extension tests were not rerun; that qualification is inherited from the AUIF rev14 audit (AD-15 to AD-20).
* **The M8 milestone row** (`programme/PROGRAMME_MILESTONES.csv`) no longer says "Not started". It now says what was delivered and audited, and that it is not accepted as a release.

**What this is not.** A pass for the audited scope only. It is not acceptance of the APG programme, not production readiness, and not Engine or Governor integration. CF-53 (which record types may validly be empty) stays open: no record type has been approved as empty, so Builder Zero tenant zero_two still cannot be assessed through AUIF. CF-52, CF-54, CF-55 and every open EDR and CF item stay open or unedited; CF-41 stands; the construction definitions stay PROPOSED. No code, test logic, data or specification changed. Synthetic data only.

**Check.** `python3 -I tools/run_regression_m81r1.py --all` (R01 to R07; R07 reruns the M8.1 regression, which reruns the M8 regression and boundary tests). Details: `programme/CHANGE_RECORD_APG-M8.1-R1.md`.

---- the APG-M8.1 readme follows, unchanged ----

# APG-M8.1 -- APG as a module client of AUIF rev14; DEV-M8-01 ended (DRAFT, builder-made, non-production)

**Status: Builder-implemented and locally tested; not accepted.** No independent verification of APG-M8.1 has taken place. Not a release acceptance, not production approval, and not proof of integration with a real Anchor Engine.

**Authority.** The product owner, 2026-10-21: "Authorise M8.1 as written, on AUIF rev14 as audited with its stated qualifications". AUIF rev14 was audited with no defect found, with qualifications (AD-15 to AD-20): its full fresh-ZIP verifier did not complete in one run, the real-Governor extension tests were not repeated, only its revision-specific mutants were rerun, and Python 3.12 was not reproduced.

**What changed** (full list: `programme/CHANGE_RECORD_APG-M8.1.md`):
* **Dependency.** The AUIF rev14 ZIP (`d534a6e6...`), unmodified and verified by hash before and after every run, replaces rev13 in this package. Earlier ZIPs still carry rev13, unchanged.
* **DEV-M8-01 ended.** Every FIELD mapping is in the contract form `module.apg.<Type>.<attribute>`. rev14 itself refuses the old form, and so does APG's own check.
* **Composite identities.** Every composite natural key is declared to AUIF as a composite source identity. The canonical id is now stable across revisions, and APG checks it against its own rule.
* **The rev14 sync report.** Refused, conflicting and module-failed records stop the import. A read that AUIF does not report as complete stops it too, which replaces M8's page-count workaround. SOURCE_EMPTY is kept.
* **Event notices.** AUIF's EVENT_NOT_APPLIED notices are read and checked against the ordering results. An in-order event AUIF cannot apply stays outstanding. The events AUIF applied are never refused.
* **Tests.** The M8 tests that pinned rev13's defects now test that the corrections are used.

**Unchanged.** Builder Zero synthetic data only. No real system, credential, Engine port, Governor wiring or outbound action. CF-53, which record types may validly be empty, is still open, so Builder Zero tenant zero_two still cannot be assessed through AUIF. CF-52 and every open EDR and CF item stay open. The construction definitions stay PROPOSED.

How to re-check: the APG-M8.1 section of `RUN_COMMANDS.txt`.

---- the APG-M8-R2 readme follows, unchanged ----

# APG-M8-R2 -- records only: the independent auditor's dispositions from the audits of APG-M8, APG-M8-R1 and AUIF rev14 (DRAFT, builder-made, non-production)

**Status: builder-made, records only; not accepted.** No independent review of this records release has taken place yet.

**Authority.** The product owner, 2026-10-21: "Authorise the records-only release for the M8, M8-R1 and rev14 audit results, after the rev14 audit". On the product owner's decision ("Update the 2 lists"), the declared-file lists of the two M8 checks that would otherwise report this release's files (`tests_m8/test_m8_boundary.py`, `tools/run_regression_m8.py`) gain those files; that is the only change outside the records.

**The dispositions** (appended to `programme/AUDIT_DISPOSITION_REGISTER.csv`; a finding's disposition is read from this register, I-127):
* **AD-13, F-82 on APG-M8:** the defect raised and reproduced by the auditor; APG-M8 not accepted pending its correction.
* **AD-14, F-82 on APG-M8-R1:** independently verified corrected ("scoped audit passed"); Python 3.12 results remain builder evidence.
* **AD-15 to AD-20, F-76 to F-81 on AUIF rev14:** no defect found in the rev14 changes audited, a qualified disposition: the full fresh-ZIP verifier did not complete in one run in the auditor's environment, the real-Governor extension tests were not repeated, only the 51 revision-specific mutants were rerun, and Python 3.12 was not reproduced.

**What these are not.** Finding-level dispositions only: not acceptance of any release, not production readiness, not Engine or Governor integration. CF-53 (which record types may validly be empty) and CF-52 stay open; every open EDR and CF item stays open; CF-41 stands; the construction definitions stay PROPOSED. APG still depends on AUIF rev13 under DEV-M8-01; M8.1 (moving APG onto rev14) needs its own authorisation. No code, test logic, data or specification changed.

**Check.** `python3 -I tools/run_regression_m8r2.py --all` (R01 to R08; R07 and R08 rerun the two M8 checks). Details: `programme/CHANGE_RECORD_APG-M8R2.md`.

---- the APG-M8-R1 readme follows, unchanged ----

# APG-M8-R1 -- correction of finding M8-F7: an empty source is not current data (DRAFT, builder-made, non-production)

**Status: Builder-implemented and locally tested; not accepted.** No independent verification of this correction has taken place. Not a release acceptance, not production approval, and not proof of integration with a real Anchor Engine.

**Authority.** The product owner, 2026-10-20: "Authorise M8-R1 as written, after rev14", after the independent audit of APG-M8 refused acceptance pending this correction.

**The finding (M8-F7, F-82).** The audit reproduced it on the delivered APG-M8: after a good import of the synthetic AP invoices, the source file was cut to its header and imported again; AUIF reported NO_DATA, the adapter applied the empty import with no reason, the 187 earlier records stayed, and the gate answered "can assess".

**The correction.** `apg_auif/intake.py` refuses a full read that brings back no record (AUIF's NO_DATA, or nothing delivered and no other outcome) with the integrity reason SOURCE_EMPTY:
- whether the source was empty from the start or became empty after a good import;
- the gate then answers "cannot assess" and the assessment returns no figure and no signal; earlier records stay stored but are never made current by it;
- a clean import after the source is restored makes the assessment possible again;
- an event poll that brings no new event is not an empty source.

**A consequence the builder did not foresee (decision needed, CF-53).** Builder Zero tenant zero_two has eight header-only record types (credit notes, notices, variations, plant hire, PO amendments, supplier quotes, delay events, defects). M3 records them as valid empty deliveries; the AUIF path now refuses each one, so **zero_two cannot be assessed through AUIF**, although its stored records, figures and detection results are the same as on the M3 path. This was found by the first M8-R1 run of the path-equivalence test and declared after it, openly (`programme/CHANGE_RECORD_APG-M8R1.md` section 3a). Whether some record types may validly be empty is the product owner's decision.

**What else changed.** One test file (`tests_m8/test_m8r1_empty_source.py`); five mutants (MI-38 to MI-42, one documented as equivalent); sabotage case S15; regression step R10 against the delivered APG-M8 ZIP; corpus case F11 (header only) declared as a difference before the comparison ran (the AUIF path now refuses it; M3 records an empty delivery); one register row per table plus CF-52 (the M3 path is not examined or changed) and CF-53 (which record types may validly be empty). Full list: `programme/CHANGE_RECORD_APG-M8R1.md`.

**Unchanged.** AUIF rev13 (carried as its ZIP, unmodified; synthetic data only); DEV-M8-01; F-76 to F-81; every open EDR and CF item; the PROPOSED construction definitions; the delivered APG-M8 ZIP and every earlier ZIP.

How to re-check: the APG-M8-R1 section of `RUN_COMMANDS.txt`.

---- the APG-M8 readme follows, unchanged ----

# APG-M8 -- APG as a module client of the frozen AUIF rev13, synthetic data only (DRAFT, builder-made, non-production)

**Status: Builder-implemented and locally tested; not accepted.** No independent verification has taken place yet. This package is not a release acceptance, not production approval, and not proof of integration with a real Anchor Engine.

**Authority (product owner, 2026-10-20).**
- "AUTHORISE M8" (APG integration with the frozen AUIF rev13 module interface, synthetic data only). This was granted after the baselines were verified first.
- After the stop report on finding M8-F1: "Authorise M8 continuation under DEV-M8-01 as written".

**What it is.** It is the delivered APG-F67.4-R2 package plus additions:
- `apg_auif/`: the adapter.
- `tests_m8/`: 14 test files with 154 tests.
- `auif_m8/`: the PROPOSED construction definitions, the AUIF canonical model, and 15 CANDIDATE synthetic translation packs. All of it is configuration only.
- `third_party/auif_rev13/`: the AUIF rev13 ZIP, byte for byte, with its sidecar.
- Seven tools, the change record `programme/CHANGE_RECORD_APG-M8.md`, regression data and logs.

Rows were appended to four programme registers; the Engine handoff register is unchanged. No existing application code, test, tool, template, data file or specification was modified. The APG-F67.4-R2 ZIP and every earlier ZIP are untouched.

**How AUIF is used.**
- AUIF is carried only as its rev13 ZIP, unmodified.
- Before every run, the ZIP's hash, AUIF's own manifest check and its core tree hash are verified on a fresh extraction. They are verified again after the run.
- APG is a module on AUIF's own `BaseModule`. It receives entities, observations, events, integration states and errors. It never requests an action.
- The AUIF runtime uses AUIF's own reference ports: memory persistence, the reference tenant authority, in-memory secrets and a fake clock.
- There is no real system, no credential, no Engine port, no Governor wiring and no outbound action.

**What it shows (builder-run).** Builder Zero runs end to end through AUIF's own CSV importer, then AUIF, then the APG module, then APG records, then the financial core and detection.
- **Same results on both paths.** For both tenants, the AUIF path gives the same records, figures, detection results, exclusions and assessment status as the M3 path.
- **One declared difference in the stored golden answers.** GOLDEN_FIN and GOLDEN_DET reproduce exactly. GOLDEN_M3 reproduces except one difference, which was declared beforehand.
- **Complete lineage.** Every stored record carries lineage: integration, source system, source record, translation pack and hash, canonical id, observed and effective time, and validation state. Every figure input and every signal's evidence traces back to it.
- **No fallback assessment.** Invalid, ambiguous, stale, deferred, partial, wrong-tenant, missing-field and type-mismatched data, and degraded integrations, give "cannot assess" with a reason. No old, default or partial value is shown in its place.

**DEV-M8-01 (finding M8-F1).** AUIF rev13 cannot translate a field into a MODULE-namespace concept (`auif/translation.py` line 152).
- Under DEV-M8-01, translation-pack FIELD mappings write `<Type>.<attribute>`.
- ENTITY mappings and the canonical model keep the full `module.apg.<Type>` name.
- A test pins both the defect and the deviation.
- Once a corrected AUIF revision is authorised, built and audited, the packs must be regenerated under a new authorisation.
- Findings M8-F1 to M8-F6 (F-76 to F-81) are defects in the builder's own AUIF rev13, which was frozen for M8. None was patched. Their fix is a separately authorised AUIF correction revision (CF-50); it is not Engine work.

**Gates.** All open EDR and CF items stay open, including EDR-05, EDR-06, EDR-18, EDR-39, EDR-40, EDR-41 and CF-41. The construction definitions are PROPOSED, never LOCKED. The AUIF-side Engine work remains with Amir.

How to re-check: the APG-M8 section of `RUN_COMMANDS.txt`.

---- the APG-F67.4-R2 readme follows, unchanged ----

# APG F-67.4-R2 -- records-only correction: AD-09 to AD-12 supersede AD-05 to AD-08 (wording only) (DRAFT, builder-made, non-production)

This package is the delivered APG-F67.4-R1 package plus one records-only correction, explicitly authorised by the product owner on 2026-10-20 ("Authorise F-67.4-R2 records correction: ..."). No existing application code, tests, tools or specifications were modified; two R2 verification tools were added. The APG-F67.4-R1 ZIP, and every earlier ZIP, are not touched. The change record is `programme/CHANGE_RECORD_APG-F67.4-R2.md`.

* **The defect.** The audit of R1 found that in AD-05 to AD-08 the field "what is not independently verified" began with a sentence describing the auditor's own evidence, which contradicts the field.
* **The correction.** Programme rows are never edited, so AD-09 to AD-12 are appended, each naming the row it supersedes.
  * Each is identical to that row except the corrected field, which now reads "No finding-specific qualification beyond the execution-limit qualifications recorded for the APG-F67.4 audit as a whole." followed by the unchanged qualifications.
  * Each also has its own id, and its "recorded in" field names the row it supersedes.
  * I-134 records the reading rule: a finding's current disposition is its latest row.
* **Unchanged.** No disposition or finding status changes.
  * The current rows are AD-04 (F-75) and AD-09 to AD-12 (F-74, F-73, F-72, F-67), each independently verified corrected in APG-F67.4, as a finding-level disposition only.
  * EDR-39, EDR-40 and EDR-41, and every other gate, stay open; CF-41 stands.
* **Check.** `python3 -I tools/run_regression_f674r2.py --all` runs R01 to R05, each short.
* **Next.** M8 is not authorised and has not started; it needs its own explicit authorisation.
* **Status.** Builder-made, records-only; not yet independently reviewed.

---- the APG-F67.4-R1 readme follows, unchanged ----

# APG F-67.4-R1 -- records-only: the independent auditor's finding-level dispositions from the audit of APG-F67.4 (DRAFT, builder-made, non-production)

This package is the delivered APG-F67.4 package plus one records-only release, explicitly authorised by the product owner on 2026-10-20 ("Authorise F-67.4-R1 records release: ..."). No existing application code, tests, tools or specifications were modified; two R1 verification tools were added. The APG-F67.4 ZIP, and every earlier ZIP, are not touched. The change record is `programme/CHANGE_RECORD_APG-F67.4-R1.md`.

* **The dispositions.** The audit disposition register gains AD-04 to AD-08:
  * F-75 is independently verified corrected in APG-F67.4, with the auditor's execution-limit qualifications;
  * F-74, F-73, F-72 and F-67 are independently verified corrected in APG-F67.4, on the auditor's independent reruns.
* **The qualifications** (execution limitations, not failed tests). The combined 23-group runner and regression step R08 timed out, so their parts were run individually. Mutation batch 1 was split around the slow documented equivalent. No timeout was counted as a kill.
* **What these are, and what they are not.** These are finding-level dispositions only. They are not acceptance of any release, and not approval to integrate or deploy.
  * EDR-39, EDR-40 and EDR-41 stay open, with every other gate.
  * CF-41 (APG-F67 started without explicit authorisation, not ratified) stands.
  * The findings rows keep their builder text; status is read from the disposition register (I-127).
* **Check.** `python3 -I tools/run_regression_f674r1.py --all` runs R01 to R07, each short.
* **Next.** M8 (AUIF-side integration and file import) is not authorised and has not started; it needs its own explicit authorisation after the audit of this release.
* **Status.** Builder-made, records-only; no independent review of this records release has taken place yet.

---- the APG-F67.4 readme follows, unchanged ----

# APG F-67.4 -- correction of finding F-75: approved content and approval entries are compared by the store's canonical, type-preserving fingerprint (DRAFT, builder-made, non-production)

This package is the delivered APG-F67.3 package plus one correction release, explicitly authorised by the product owner on 2026-10-20 ("Authorise F-67.4 correction release: ..."). The APG-F67.3 ZIP, and every earlier ZIP, are not touched. The change record is `programme/CHANGE_RECORD_APG-F67.4.md`.

* **F-75**, from the independent audit of APG-F67.3.
  * **The defect.** "Unchanged" approved content was compared with Python equality, under which False == 0 and True == 1. A direct write that changed an approved value's type kept the approval.
  * **Same comparison elsewhere, found by the builder.** The re-store checks used the same comparison.
  * **Reproduction.** `tools/probe_f674.py` finds 15 defects on APG-F67.3 and 0 here, across all five policy records.
* **The correction.**
  * "Unchanged" now means unchanged by the store's own canonical, type-preserving fingerprint (`canon.digest`, the payload hash the store uses).
  * It applies to the approved content, the approver's entries and both re-store checks.
  * Key order alone is not a change, and content that cannot be fingerprinted never holds (I-133).
* **Tests.**
  * 9 new tests in `tests/test_f674_type_strict.py`. On APG-F67.3, 7 fail or error; 2 guard behaviour it already had.
  * The F-73 and F-74 tests, and every other test, are unchanged.
* **Finer-grained audit runs.**
  * Runs with one test file per group: `tools/run_f674_all.py --files-list`, `--file N`, `--files A-B`. There are 117 files, each with its count, adding up to the whole suite of 2,583 tests.
  * The earlier small groups are still there.
  * `tools/f674_mutants.py --batch K/10 --timeout 30`: the mutation run in batches.
  * `tools/sabotage_f674.py --only Sxx`: one sabotage case at a time.
  * `tools/run_regression_f674.py --step Rnn`: one regression step at a time.
* **Records.** F-75, SR-119, SR-120, I-133 and CF-45, appended only.
* **Still open.**
  * F-75, F-74, F-73, F-72 and F-67: each stays open until the independent auditor verifies it.
  * CF-36 to CF-40 and CF-42 to CF-45, and EDR-34 and EDR-36 to EDR-41.
  * M8 is not authorised and is not started.
* **Status.** Builder-implemented and locally tested; no independent review has taken place.

---- the APG-F67.3 readme follows, unchanged ----

# APG F-67.3 -- correction of finding F-74 and the approval-binding defect class: a confirmation counts only while the approval it confirms still holds (DRAFT, builder-made, non-production)

This package is the delivered APG-F67.2 package plus one correction release. It was authorised by the product owner on 2026-10-20 ("I authorise chatgpts authorisation"), adopting the auditor's recommended text: "Authorise F-67.3 correction release. ...". The APG-F67.2 ZIP, and every earlier ZIP, are not touched. The change record is `programme/CHANGE_RECORD_APG-F67.3.md`.

* **F-74**, from the independent audit of APG-F67.2.
  * **The defect.** An old, genuine confirmation still counted after its entry was removed and re-planted by direct store writes.
  * **Same class, found by the builder.** The confirmation also still counted after the entry was changed, after the approved content was rewritten, and after the content was rewritten and restored. The owner could not approve the new content either.
  * **Reproduction.** `tools/probe_f673.py` finds 25 defects on APG-F67.2 and 0 here, across all five policy records and eight attack paths.
* **The threat model** (agreed in the authorisation).
  * The attacker can append arbitrary revisions directly to the store.
  * The attacker cannot forge another person's audit event, rewrite history, or change what a pinned revision reads.
  * Those store requirements are now an explicit contract, `apg/contracts/record_store_history_contract.py` (EDR-41). `tools/run_history_contract.py` passes on the reference store and catches four faulty stores.
* **The rule (I-132).**
  * A confirmation counts at the revision a run pins only if the approver's entry and the approved content are unchanged in every revision from the confirmed one through the pinned one.
  * Other people's approvals keep it.
  * A broken confirmation never counts again; the owner approves afresh and is never stuck.
  * Writing both the store and a forged audit event remains the Engine's to prevent (EDR-39, EDR-40).
* **Tests.**
  * 12 new tests in `tests/test_f673_approval_integrity.py`, each over the five records. On APG-F67.2, 10 fail or error; 2 guard properties it already had.
  * No existing test changed.
* **Auditable in small parts.**
  * `tools/run_f673_all.py --list`: 23 short groups.
  * `tools/f673_mutants.py --batch K/9 --timeout 30`: a timeout is rerun under 300 seconds, never counted as a kill.
  * `tools/sabotage_f673.py --only Sxx`: one sabotage case at a time.
  * `tools/run_regression_f673.py --step Rnn`: one regression step at a time.
* **Records.** F-74, SR-117, SR-118, I-132, EDR-41 and CF-44, appended only.
* **Still open.**
  * F-74, F-73, F-72 and F-67: each stays open until the independent auditor verifies it.
  * CF-36 to CF-40 and CF-42 to CF-44, and EDR-34 and EDR-36 to EDR-41.
  * M8 is not authorised and is not started; the F-67.3 authorisation does not accept this release.
* **Status.** Builder-implemented and locally tested; no independent review has taken place.

---- the APG-F67.2 readme follows, unchanged ----

# APG F-67.2 -- correction of finding F-73: approve never completes an approval entry it finds; each confirmation is bound to the revision approve wrote (DRAFT, builder-made, non-production)

This package is the delivered APG-F67.1 package plus one correction release, explicitly authorised by the product owner on 2026-10-20 ("Authorise F-67.2 correction release"). The APG-F67.1 ZIP, and every earlier ZIP, are not touched; this is a separate release with its own hash. The change record is `programme/CHANGE_RECORD_APG-F67.2.md`.

* **F-73**, from the independent audit of APG-F67.1.
  * **The defect.** The F-67.1 recovery path completed an unconfirmed entry in the caller's name after checking only its role and kind. An entry planted straight into the store, with the correct role and kind, was confirmed when the owner approved.
  * **Reproduction.** `tools/probe_f672.py` finds 11 defects on APG-F67.1 and 0 here, across all five policy records.
* **The correction: replace, never complete.**
  * If the caller has an unconfirmed entry in their name, whoever wrote it, approve writes a revision without it, then a revision with a fresh entry of its own.
  * The confirming event names that revision.
  * A confirmation counts only for the revision that added the person's entry.
  * A planted entry never counts, and only the named person, approving in person, replaces it.
  * Refusing the entry instead would let anyone able to write the store block the owner's approval (I-131).
  * Restricting direct writes (EDR-39) and atomic writes (EDR-40) stay with the Engine.
* **Tests.**
  * 11 new tests in `tests/test_f672_forged_entry.py`, each over the five records. On APG-F67.1, 8 fail or error; 3 guard properties F-67.1 already had.
  * Two F-67.1 tests changed (declared) to the new behaviour; no test removed.
* **Auditable in small parts.**
  * `tools/run_f672_all.py --list`: 23 short groups.
  * `tools/f672_mutants.py --batch K/8 --timeout 30`: the mutation run in batches.
  * `tools/sabotage_f672.py --only Sxx`: one sabotage case at a time.
  * `tools/run_regression_f672.py --step Rnn`: one regression step at a time.
  * A mutant that times out under a short timeout is now rerun under 300 seconds before it is classified. The build found that a short timeout could otherwise hide a survivor.
* **Records.** F-73, SR-115, SR-116, I-131 and CF-43, appended only. CF-41 (APG-F67 started without explicit authorisation, not ratified) is unchanged.
* **Still open.**
  * F-73, F-72 and F-67: each stays open until the independent auditor verifies it.
  * CF-36 to CF-40, CF-42 and CF-43, and EDR-34 and EDR-36 to EDR-40.
  * M8 is not authorised and is not started.
* **Status.** Builder-implemented and locally tested; no independent review has taken place.

---- the APG-F67.1 readme follows, unchanged ----

# APG F-67.1 -- correction of finding F-72: an approval stuck after an audit-write failure, for all five policy records (DRAFT, builder-made, non-production)

This package is the delivered APG-F67 package plus one correction release, explicitly authorised by the product owner on 2026-10-20 ("Authorise F-67.1 correction release"). The APG-F67 ZIP, and every earlier ZIP, are not touched; this is a separate release with its own hash. The change record is `programme/CHANGE_RECORD_APG-F67.1.md`.

* **APG-F67 governance (CF-41).** APG-F67 was started without explicit authorisation. As the product owner decided, it is recorded that way and is not ratified retroactively. The APG-F67 ZIP and records are unchanged, and APG-F67 stays unaccepted until independently verified (CF-40).
* **F-72**, from the independent audit of APG-F67.
  * **The defect.** When the audit write failed after the policy record was updated, the approval was recorded but not confirmed. That was fail-closed, but the owner's retry was refused as "already approved", so the policy was stuck.
  * **Scope.** The recommendation policy (APG-M7.1) had the same order, so all five policy records are covered.
  * **Reproduction.** `tools/probe_f671.py` finds 10 defects on APG-F67 and 0 here.
* **The correction.**
  * A failed confirming write raises `ApprovalNotConfirmed`. It says the approval is recorded but NOT CONFIRMED and does not count.
  * The same person, with the same identity and role checks, can call approve again. That writes only the missing confirming event and changes no record.
  * Nobody else can complete it, and nothing is counted twice.
  * `approval_status` shows, per version, what is recorded and what is confirmed.
  * Writing the record and its event atomically is the Engine's job (EDR-40); APG does not claim it.
* **Tests.** 11 new tests in `tests/test_f671_approval_recovery.py`, each over the five records; on APG-F67 all fail or error. No existing test changed.
* **Auditable in small parts.**
  * `tools/run_f671_all.py --list`: the whole suite in small counted groups, with a coverage check.
  * `tools/f671_mutants.py --batch K/N --timeout 30`: the mutation run in batches.
  * `tools/sabotage_f671.py --only Sxx`: one sabotage case at a time.
  * `tools/run_regression_f671.py --step Rnn`: one regression step at a time.
  * The whole suite also stays runnable as one command.
* **Records.** F-72, SR-113, SR-114, I-130, EDR-40, CF-41 and CF-42, appended only.
* **Still open.**
  * F-72 and F-67: each stays open until the independent auditor verifies it.
  * CF-36 to CF-40 and CF-42, and EDR-34 and EDR-36 to EDR-40.
  * M8 is not authorised and is not started.
* **Status.** Builder-implemented and locally tested; no independent review has taken place.

---- the APG-F67 readme follows, unchanged ----

# APG F-67 -- correction of finding F-67: approval provenance for the financial, detection and procurement policies and the specification register (DRAFT, builder-made, non-production)

This package is the delivered MIE-1.1-R1 package plus one correction release. The delivered MIE-1.1-R1 ZIP, and every earlier ZIP, are not touched; this is a separate release with its own hash. The change record is `programme/CHANGE_RECORD_APG-F67.md`.

* **F-67.** This is the builder's same-class sweep of F-66, recorded in M7.1 and left open until now. The financial policy, the detection policy, the procurement policy and the specification register took an approval as plain approver, role and kind fields written by the caller, and a run counted it. `tools/probe_f67.py` shows it four ways for each record on R1 (17 of 17 DEFECT PRESENT, including the control) and 0 of 17 here.
* **The correction reuses the M7.1 pattern for F-66, in one module, `apg/policy_approval.py`.**
  * A version is proposed by the person storing it and never arrives with an approval.
  * An approval is recorded only by `approve_policy` / `approve_spec`, from the approver's own verified context: a person holding the owner role, not the proposer, once. It writes an audit event.
  * A run counts an approval only when the audit log confirms it, and pins the confirmed approvers in its parameters for replay.
  * The caller-asserted `approve()` is removed from the three policy modules.
* **Demonstrations.** The demonstration policies are proposals, approved in person by a synthetic owner. The golden outputs are unchanged.
* **Limit (I-128, EDR-39).** Reference audit events carry no roles, and APG cannot stop direct writes. A person without the role who writes both a record with an approval in their own name and a matching event directly would be counted. Restricting those writes is the Engine's job.
* **Changes from R1.** 18 application files, 3 test helpers and 11 test files changed (declared; R1 originals in `regression/f67/r1_originals/`). Separately, 12 new tests in `tests/test_f67_policy_approval.py`, all failing or erroring on R1. Programme tables have rows appended only.
* **Checks.**
  * The whole suite: 2,540 tests, 0 failures.
  * Mutation: 55 of 55 killed (the first run left 2 survivors, both test gaps, now closed).
  * Sabotage: 27 of 27 caught (`tools/sabotage_f67.py`; the first run missed 3, fixed as the change record says).
  * Regression against R1: `tools/run_regression_f67.py --all`.
  * Short groups: `tools/run_f67_all.py --list`.
  * The MIE-1.1-R1 and earlier per-release tools describe their own release, and here report the F-67 changes as undeclared.
* **Records.**
  * SR-111, SR-112, I-128, I-129, EDR-39 and CF-40.
  * AD-03 records the auditor's completed MIE-1.1 mutation audit (624 / 621 killed / 3 equivalent / 0 survivors). It was run by slices with a 30-second per-mutant timeout instead of the tool's 300 seconds, so it is not an identical rerun under the original setting.
  * The F-67 findings row is not edited (I-129).
* **How it was authorised.** The builder started F-67 when the product owner relayed the R1 audit, as agreed beforehand, and treated that relay as the authorisation. The product owner should confirm this.
* **Still open.**
  * F-67, until the independent auditor verifies it.
  * The M7.3 gates (CF-36), BLK-01 to BLK-03 (CF-37), DEV-MIE-01 (CF-38), EDR-34 and EDR-36 to EDR-39, and the audit of this release (CF-40).
  * M8 is not started; it needs its own authorisation after this audit.
* **Status.** Builder-implemented and locally tested; no independent review has taken place.

---- the MIE-1.1-R1 readme follows, unchanged ----

# APG MIE-1.1-R1 -- records only: the independent auditor's disposition of F-70 and F-71 (DRAFT, builder-made, non-production)

This package is the delivered MIE-1.1 package plus one records-only release. It changes no code, test, tool or specification. The delivered MIE-1.1 ZIP is not touched.

* The independent audit of MIE-1.1, relayed by the product owner on 2026-10-20, found F-70 and F-71 corrected. The product owner and the auditor agreed to record that in the programme registers.
* Programme rows are never edited, so the disposition is recorded in a new append-only table, `programme/AUDIT_DISPOSITION_REGISTER.csv` (AD-01 for F-70, AD-02 for F-71), and the reading is I-127. The F-70 and F-71 rows of the findings register keep their builder text; their verification status is read from the disposition register.
* Each disposition records what the auditor reproduced, what was not reproduced and what the disposition does not mean. The full 624-mutant run is builder-reported (the auditor ran selected mutants); the whole-suite command timed out for the auditor and the counted groups passed separately.
* The disposition is not a release acceptance. EDR-36 to EDR-38, BLK-01 to BLK-03, M7.3 final acceptance, the M9.4 comparison and the development deviation DEV-MIE-01 stay open (CF-36 to CF-39). Earlier findings are not back-filled.
* Check: `python3 -I tools/run_regression_mie1_1r1.py --all` (R01 to R07: byte-identical to MIE-1.1 except the declared records, tables as the tool makes them, the dispositions and caveats, no claims, the probe and the 244 MIE tests still pass).

---- the MIE-1.1 readme follows, unchanged ----

# APG MIE-1.1 -- correction of the two findings of the independent audit of MIE-1 (F-70, F-71; DRAFT, builder-made, non-production)

This package is the delivered MIE-1 package plus one correction release. The independent audit of MIE-1 did not accept it; it reproduced two defects. The delivered MIE-1 ZIP is not touched; this is a separate release with its own hash. The change record is `programme/CHANGE_RECORD_APG-MIE1.1.md`.

* F-70 (auditor F-MIE1-01): an unexpected exception from a store at the commit escaped the core as a raw exception, after the ACCEPTED event and with no FAILED event. Now any exception at the commit other than StoreFailure is INTERNAL_ERROR_FAIL_CLOSED, with one attempted FAILED event and no result. In the same class, an audit sink that raises anything is now AUDIT_UNAVAILABLE with no state change, and a batch of observations is written in one all-or-nothing store call (`ObservationStorePort.append_batch`; EDR-38). MIE-1 left the first items of a batch stored when the store failed part-way.
* F-71 (auditor F-MIE1-02): an observation could name an observation of another subject or series in `supersedes`, and that evidence silently became history. Now a correction must be of the same series (subject, market, unit, class, basis), source, date and kind; anything else is REJECTED with the field named, and nothing changes (I-125). Classification also ignores an incompatible link already in a store.
* Reproduction: `python3 -I tools/probe_mie1_audit_findings.py` prints DEFECT PRESENT 17 times on the delivered MIE-1 package and THE MIE-1 AUDIT FINDINGS ARE CORRECTED here (18 cases with one control).
* New tests (10): `tests/test_mie_core_m11_corrections.py`; 9 fail or error against the MIE-1 code, and the tenth guards an edge of the new code that the MIE-1.1 mutation run found untested. One MIE-1 test changed: AU-07 in `tests/test_mie_core_audit.py` now watches `append_batch`, the store call the batch commit uses. No M2 to M7.3 test and no APG application file changed.
* Checks: 2,528 tests in the whole suite; mutation 624 mutants, 621 killed, 3 documented equivalents (the MIE-1 three), 0 unexplained survivors; sabotage 70 of 70 caught (the 60 catalogue cases and C-01 to C-10 for the corrections). Short groups: `python3 -I tools/run_mie1_1_all.py --list` (groups 9 to 19 are the whole suite in counted parts).
* Development deviation (DEV-MIE-01, CF-38): MIE1_SPEC v0.3 says no implementation code is written until the specification is reviewed, BLK-01 to BLK-03 are cleared and the product owner separately authorises it. The product owner authorised development with BLK-01 to BLK-03 still open. MIE-1 and MIE-1.1 are built under that explicit deviation and do not claim unconditional conformity with that wording; the specification is not edited and no gate is closed.
* Still open: F-70 and F-71 until the auditor verifies them; the M7.3 release gates (CF-36), BLK-01 to BLK-03 (CF-37), EDR-36 to EDR-38, and the MIE-1 audit runs that did not complete (CF-39). The MIE-1 tools describe MIE-1: run here, `tools/run_regression_mie1.py` reports the MIE-1.1 files as undeclared and `tools/run_mie1_all.py` counts the new tests; use the MIE-1.1 tools. Builder-implemented and locally tested, not independently reviewed.

---- the MIE-1 readme follows, unchanged ----

# APG MIE-1 -- the universal market-intelligence core, built as code, with construction as the first industry pack (DRAFT, builder-made, non-production)

This package is the delivered M7.3 package plus MIE-1. The product owner authorised building MIE-1 as code, reusing and generalising M6's market-intelligence logic, with construction as the first industry pack. The M7.3 acceptance and the Engine-store verification stay open as release gates (CF-36). The delivered M7.3 ZIP is not touched; this is a separate release with its own hash. The change record is `programme/CHANGE_RECORD_APG-MIE1.md`; the specification it implements, MIE1_SPEC v0.3, is copied unchanged into `spec/MIE1_SPEC_v0.3/`.

* `mie/core/` is a domain-neutral, deterministic library. It uses the standard library only, reads no clock, network, file or environment, calls no feed and imports nothing from APG. It provides twelve operations, a closed pack schema, exact values with no floats, observations with a licence gate, signals that state only what was observed, a first-match decision table with the signal-influence policy, replay from stored evidence, and a per-tenant audit sequence (validate, compute, append the audit event, commit, return). Everything it needs from its host is an outbound port; the reference ports are in memory and not for production (EDR-37).
* M6 is reused in two ways. Its rules are generalised in the core: thresholds with no default, the last valid day still valid, stale evidence qualifying a result, an index as a movement series, conflicts reported rather than chosen, the approver not the author, scenarios as labelled assumptions. M6 itself is used through adapters: stored market and FX records and the M6 MarketFeedPort are mapped into observations (`mie/adapters/m6.py`, BLK-02, I-121). The core does not import M6, and M6 is not changed.
* `mie/packs/construction.py` is BUY only and CONTEXT_ONLY: no rule may use a market signal until the Section 08 change request is decided. It carries structure only, with no owner value. `mie/packs/synthetic.py` is a TEST FIELD pack that shows a second field runs on the same core code, unchanged.
* The Builder Zero run uses TEST-ONLY owner inputs and is recorded in `regression/mie1/golden_mie1.json`. MAT-STEEL, BUY, required 2026-12-01, assessed 2026-09-30: index UP, outcome ACT_NOW from a date rule, signal influence NONE, and the replay is identical. MAT-PBOARD has no index evidence and is still assessed, because of its AUD/USD conversion (I-123, for review).
* Tests: 234 MIE-1 tests in 15 files, and 2,518 in the whole suite (every earlier test unchanged). There are 8 static checks. All 175 planned cases are accounted for (`programme/MIE1_CASE_COVERAGE.csv`). Mutation: 608 mutants, 605 killed, 3 documented equivalents, 0 unexplained survivors. Sabotage: 60 of 60 catalogue cases caught.
* Short checks: `python3 -I tools/run_mie1_all.py --list` prints 19 groups; groups 9 to 19 are the whole suite in counted parts. One mutation slice: `python3 -I tools/mie_mutants.py --only PK --jobs 2`. One sabotage case: `python3 -I tools/sabotage_mie1.py --only SB-nn`. A run cut off by a time limit is incomplete, not a pass.
* Not implemented: PSA02-D2 (specification_ref and methodology_ref), DECLARATION_CHANGED with re-attestation, and the P1 normal form (SR-108, I-122).
* Still open: BLK-01 to BLK-03 (CF-37), the M7.3 release gates (CF-36), EDR-36 and EDR-37. No APG application file or existing test changed. No APG finding or recommendation consumes a signal. Builder-implemented and locally tested; no independent review has taken place.

---- the M7.3 readme follows, unchanged ----

# APG M7.3 -- the commit holds whole queries, so a record created during an act refuses it, after the independent audit of M7.2 (F-69; DRAFT, builder-made, non-production)

This package is the delivered M7.2 package plus one correction release. The independent audit of M7.2 confirmed that the race on existing records was closed, but did not accept M7.2. It found that a new overlapping finding created during an act was only caught by a check after the commit, which then reversed the act. A finding created just after that check returned left the act standing. A further check only shortens the window; it cannot close it.

The delivered M7.2 ZIP is not touched; this is a separate release with its own hash.

* The record store contract gains guards in its atomic batch (`ports.Guard`): a record at an exact revision (0 = absent), and a whole query at an exact set of (key, revision). The reference store checks them together with the writes as one indivisible step, under a lock. The contract for an Engine store is `apg/contracts/record_store_guard_contract.py` (RG-01 to RG-08, `tools/run_guard_contract.py`; EDR-36).
* Each checked act (submission, approval, start of work) is committed with a whole-query guard on the findings and the recommendation inputs, and a revision guard on everything its check read by key. A record added, changed or removed before the commit fails the commit, and nothing is recorded. The check after the commit and the reversal are removed.
* A record created after the commit is a later change, ordered after the act in the store. The next checked act is refused, and the next run ends what no longer matches (I-116).
* M7.3 changes three M2 files: `apg/ports.py`, `apg/reference_impl.py` and `apg/tenancy.py` (I-117). The change is additive. The 38 M2 contract cases and the 39 faulty implementations give the same results, and every earlier test passes.
* New tests (12): `tests/test_rec_m73_insert_race.py`. They cover the auditor's three interleavings at each boundary, real threads, and the guard contract against the reference store, a store that ignores guards and a store whose batch is not indivisible. Seven tests of `tests/test_rec_m72_race.py` were changed: they expected the reversal or inspected the M7.2 guard form. The other 11 are unchanged.
* The new probe `tools/probe_m72_insert_race.py` prints DEFECT PRESENT six times on M7.2 (the act committed, then reversed) and THE INSERT RACE IS CLOSED here.
* Short checks: `python3 -I tools/run_m73_all.py --list` prints 24 groups. Groups 13 to 22 are the whole unit suite in ten counted parts (2,284 tests). Sabotage runs one case at a time with `tools/sabotage_m73.py --only Sxx`. The mutation runs are `tools/m7_mutants.py --only LC --jobs 2` and `tools/m73_store_mutants.py`, the latter under a minute.
* F-69 stays open until the auditor verifies it, and so do F-64 to F-68. F-67 is still open and not corrected. Builder-implemented and locally tested, not independently reviewed.

---- the M7.2 readme follows, unchanged ----

# APG M7.2 -- the source check and the act commit together, after the independent audit of M7.1 (F-68; DRAFT, builder-made, non-production)

This package is the delivered M7.1 package plus one correction release. The independent audit of M7.1 confirmed that F-64 to F-66 were corrected in the ordinary paths, but did not accept M7.1. It found one more defect:

* F-68: the source-freshness check and the write of the recommendation were separate store operations. A change that landed between them was not seen. The auditor dismissed the finding right after the check, and the submission was still recorded. The same held at approval and at the start of work.

The delivered M7.1 ZIP is not touched; this is a separate release with its own hash.

* Submission, approval and the start of work are now recorded in ONE atomic store batch with a guard on every stored record the check read (`lifecycle._commit_checked`). A guard holds the record at the revision the check saw and writes nothing. If any record changed after the check, the whole batch fails, nothing is recorded, and the act is refused: SOURCE_CHANGED when the sources no longer match, or CONCURRENT_CHANGE when only something else changed and trying again is enough.
* A record created during the act, such as a new overlapping finding, cannot be held through the store contract. The check runs again once the act is recorded. If it now fails, the act is reversed at once, audited and refused (I-115). Absence and query guards are the Engine's (EDR-35).
* New tests (18): `tests/test_rec_m72_race.py`. A competing change is inserted right after the check and immediately before the commit, at all three boundaries, for each kind of source. Run against the M7.1 code, 12 of them fail or error; the other 6 guard behaviour that was already right (for example, a change before the act is still refused by the check itself). The new probe `tools/probe_m71_race.py` prints DEFECT PRESENT eight times on M7.1 and THE RACE IS CLOSED here.
* Short checks: `python3 -I tools/run_m72_all.py --list` prints 18 groups. Groups 8 to 17 are the whole unit suite in ten counted parts (2,272 tests). `tools/sabotage_m72.py --only Sxx` runs one sabotage case, and `tools/m7_mutants.py --only LC --jobs 2` runs one module of the mutation run. A run cut off by a time limit is incomplete, not a pass.
* Changed: `apg/rec/lifecycle.py` and `apg/rec/engine.py`, the mutation tool, the contract, this readme, the run commands and 5 programme tables (rows appended). No existing test changed. `python3 -I tools/run_regression_m72.py --static` checks the rest is byte-identical to M7.1.
* The per-release tools of M7.1 and earlier describe their own release: run in this package, `tools/run_m71_all.py` counts the M7.2 tests too, and `tools/run_regression_m71.py` reports the M7.2 files as undeclared. Run them on their own delivered ZIPs.
* F-68 stays open until the auditor verifies it, and so do F-64 to F-66. F-67 is still open and not corrected. Builder-implemented and locally tested, not independently reviewed.

---- the M7.1 readme follows, unchanged ----

# APG M7.1 -- correction of the recommendation lifecycle and the policy approval after the independent audit of M7 (F-64, F-65, F-66; DRAFT, builder-made, non-production)

This package is the delivered M7 package plus one correction release. The independent audit of M7 did not accept it. It reproduced three defects:

* F-64: a recommendation stayed submittable and approvable after its finding was dismissed, or after its mandatory review was changed to not cleared, without a fresh run.
* F-65: work could be started after the finding changed following approval.
* F-66: a policy approval could be asserted by caller-supplied approver, role and kind fields.

The delivered M7 ZIP is not touched; this is a separate release with its own hash.

* Submission, approval and the start of work now check first that the recommendation still matches its sources (`lifecycle.source_check`). The finding, its overlapping findings, its inputs and reviews and its policy must be at exactly the revisions the run pinned, and a run made now must give the same recommendation. Otherwise the act is refused (SOURCE_CHANGED) until the engine runs again.
* A policy is proposed only by the person storing it, and never arrives with approvals. `approve_policy` records an approval from the approver's own verified context and writes an audit event. A run counts only approvals the audit log confirms. Under an unapproved policy nothing can be submitted. The caller-supplied `approve()` is removed.
* New tests (23): `tests/test_rec_m71_corrections.py`. Run against the M7 code, 20 of them fail or error; the other 3 guard unchanged behaviour. The new probe `tools/probe_m7_audit_findings.py` prints DEFECT PRESENT four times on M7 and THE AUDIT FINDINGS ARE CORRECTED here.
* Same class, not corrected here: the M5 and M6 policies have the same caller-supplied `approve()` (F-67, open). This release changes no M2 to M6 file.
* Short checks: `python3 -I tools/run_m71_all.py --list` prints 16 groups. Groups 6 to 15 are the whole unit suite in ten counted parts (2,254 tests); none takes more than about a minute. `tools/sabotage_m71.py --only Sxx` runs one sabotage case, and `tools/m7_mutants.py --only EN-CMP` runs one slice of the mutation run. A run cut off by a time limit is incomplete, not a pass.
* Changed: 5 apg/rec modules, 4 M7 test files, the golden file, the mutation tool, the contract, this readme, the run commands and 5 programme tables (rows appended). `python3 -I tools/run_regression_m71.py --static` checks the rest is byte-identical to M7.
* F-64 to F-66 stay open until the auditor verifies them. Builder-implemented and locally tested, not independently reviewed.

---- the M7 readme follows, unchanged ----

# APG M7 -- recommendations, prioritisation and scenarios (programme milestone M7; DRAFT, builder-made, non-production)

This package is the delivered M9.4 package plus the M7 engine: `apg/rec` (eight new modules) and what goes with it. It turns the M5 and M6 findings into ranked, explained recommendations. People add the costs, alternatives and reviews and decide. A realised benefit is recorded only through a verification gate. APG carries out no action. The contract is `programme/RECOMMENDATION_ENGINE.md` and the change record is `programme/CHANGE_RECORD_APG-M7.md`.
The delivered M9.4 ZIP is not touched; this is a separate release with its own hash. RFC-01 is still PROPOSED and unnumbered, and nothing of Engine #17 is built.

* Eligibility before ranking: every finding is routed action, investigate, in hand, close or excluded, with the reasons. Unreviewed, weak, stale or missing evidence goes to investigate, never to a ready action.
* Every factor is shown separately (magnitude, urgency, confidence, time sensitivity, actionability, implementation cost, expected and net benefit, dependencies, risk). The ranking follows the order the policy states, and every line names the line above it and the dimension that decided. There is no combined score.
* Overlapping findings are counted once. Totals are per interpretation and never added together.
* Constraints a high rank cannot bypass: mandatory reviews, the approval role of the amount's band, every incremental cost, the kind of action, and a complete alternative for a material decision.
* Approval is bound to the version, digest and submission shown, with separation of duties. A change after approval ends it. `execute` refuses always.
* The verification gate needs four things: an adopted forecast baseline set before the action started, stored implementation evidence, an independent verifier, and every offsetting cost addressed. It then computes the realised figure reproducibly.
* Scenarios never change the official forecast: no recommendation module writes a forecast or forecast slot (tested on the whole path).
* Every run is a reproducible formula (`rec.prioritise` v1), and a past recommendation version can be rebuilt from its run.
* Every policy value is configuration with no default. The demonstration policy (`apg/rec/demo_rec.py`) is SYNTHETIC.
* Checks: `python3 -I tools/run_m7_all.py --list` (short numbered groups), `python3 -I tools/probe_rec_m7.py`, `python3 -I tools/run_regression_m7.py --static`, `python3 -I tools/m7_mutants.py`, `python3 -I tools/sabotage_m7.py`. The results of the builder's runs are in `logs/m7/`.
* No application or test file of M9.4 changed. Seven record files changed: this readme, the run commands, four programme tables (rows appended) and the M7 milestone row.
* Builder-implemented and locally tested, not independently reviewed. F-52 to F-63 and the open carried-forward items stay open.

---- the M9.4 readme follows, unchanged ----

# APG M9.4 -- correction of the clock and session failure handling in the approval request boundary after the independent audit of M9.3 (F-63; DRAFT, builder-made, non-production)

This package is the delivered M9.3 package plus one small correction release. The independent audit of M9.3 confirmed the expiry correction of M9.3 (F-62) and found one more defect: when the clock's `now()` raised an exception, `present`, `request_approval` and `check_for_execution` raised it to the caller, with no refusal and no audit entry (F-63, medium; the audit demonstrated no bypass). The M9.3 ZIP is not touched; this is a separate release with its own hash.
It starts nothing of Engine #17 and nothing of M7. RFC-01 is still PROPOSED and unnumbered.

* Changed application code: `apg/api/approval_boundary.py` only. The session check now reads the clock once, inside a guard: a clock that raises an ordinary exception, a missing or malformed reading, an expiry or actor kind that cannot be read, or a reading that is not a real UTC moment ends the session (fail closed). The three calls then give the refusal they already give for an ended session and write the audit entry they already write; no new result code and no new success outcome. The one reading is used for the whole call, so a clock that fails after its first read cannot stop an approval half way. The M9.3 rule for what a live session is (a real UTC moment, strictly later than now) is unchanged.
* New tests (29): `tests/test_api_m94_corrections.py`, six classes: a clock that raises (ten exception types, all three calls), a clock that says something else (22 bad readings, all three calls), the one-reading rule, accessor failures, failure-path integrity (no state change, no duplicate transition, an audit write that fails is not reported as audited, other tenants, replays, roles) and the M9.3 rule still holding. Run against the delivered M9.3 code, 18 of the 29 fail or error
* New tools: `probe_m93_clock_failure.py` (prints DEFECT PRESENT on M9.3 and THE CLOCK FAILURE IS HANDLED SAFELY here), `make_m94_registers.py`, `programme_check_m94.py`, `run_regression_m94.py` (splittable with `--step`), `run_m94_all.py` (splittable with `--group N`). Changed tools: `m91_mutants.py` (runs the M9.4 tests), `make_m0.py` (runs the M9.4 register step) and the earlier regression and register tools down to `run_regression_m6.py` (accept the M9.4 declarations; every other check is unchanged).
* New document: `programme/CHANGE_RECORD_APG-M9.4.md`. Changed: `programme/APPROVAL_REQUEST_BOUNDARY.md` (what happens when the clock or the expiry cannot be read), this readme, `RUN_COMMANDS.txt` and four programme tables (rows appended: F-63, SR-87 to SR-89, I-96 to I-98, CF-31). No Engine record was added and no milestone row changed.
* Everything else is byte-identical to the delivered M9.3 package. `python3 -I tools/run_regression_m94.py --static` checks all of it.
* Long commands are split: `python3 -I tools/run_m94_all.py --list` prints 88 groups, `--group N` runs one; the regression tool takes `--step Rnn`; the mutation run is given in chunks of ten ids. A run cut off by a time limit is incomplete, not a pass; the nested wrappers that did not finish in the auditor's runs are the groups listed one by one (CF-30, CF-31).
* F-52 to F-63, CF-22, CF-25 and CF-29 stay open until the auditor verifies them independently. The correction is builder-implemented and locally tested, not independently reviewed.

---- the M9.3 readme follows, unchanged ----

# APG M9.3 -- correction of the session expiry check in the approval request boundary after the independent audit of M9.2 (F-62; DRAFT, builder-made, non-production)

This package is the delivered M9.2 package plus one small correction release. The independent audit of M9.2 confirmed that the three M9.1 defects are corrected and found one more gap: the check that decides whether a session is still live compared the expiry time only as a string once its shape matched, so impossible values such as `2999-99-99T99:99:99Z`, `2999-13-01T00:00:00Z` and `2999-01-01T25:61:61Z` counted as live. The auditor demonstrated no bypass with a real sealed session; the helper itself was wrong. The delivered M9.2 ZIP and documents (and the M9.1 ones) are not changed (their hashes are in the documents file); this is a separately versioned, additive release.
It starts nothing of Engine #17 and nothing of M7. RFC-01 is still PROPOSED and unnumbered.

* Changed application code: `apg/api/approval_boundary.py` only. A session is live only if its expiry is a real UTC moment written exactly `YYYY-MM-DDTHH:MM:SSZ` in ASCII (month 1 to 12, a day the month has, 29 February only in a Gregorian leap year, hour 0 to 23, minute and second 0 to 59, year 0001 or later) and strictly later than the present time, which must itself be a real moment (a clock that is not ends every session). The three entry points use the same check (F-62).
* New tests (18): `tests/test_api_m93_corrections.py`, three classes: the rule on its own, the rule through the three entry points of the boundary (`present`, `request_approval`, `check_for_execution`) and the shape flaws that must stay closed. Run against the delivered M9.2 code, 12 of the 18 fail or error; run against this release, all pass. No existing test changed (the 78 API tests of M9.1 and the 24 of M9.2 are unchanged and pass).
* New tools: `probe_m92_session_expiry.py` (prints DEFECT PRESENT on M9.2 and THE SESSION EXPIRY CHECK IS CORRECTED here), `make_m93_registers.py`, `programme_check_m93.py`, `run_regression_m93.py` (splittable with `--step`), `run_m93_all.py` (splittable with `--group N`). Changed tools: `m91_mutants.py` (runs the M9.3 tests), `make_m0.py`, `programme_check_m92.py` and `run_regression_m6.py` to `run_regression_m92.py` (accept the M9.3 rows, tables and declared files; every other check is unchanged).
* New document: `programme/CHANGE_RECORD_APG-M9.3.md`. Changed: `programme/APPROVAL_REQUEST_BOUNDARY.md` (what a live session is), this readme, `RUN_COMMANDS.txt` and four programme tables (rows appended: F-62, SR-84 to SR-86, I-93 to I-95, CF-30). No Engine record was added and no milestone row changed.
* Everything else is byte-identical to the delivered M9.2 package. `python3 -I tools/run_regression_m93.py --static` checks all of it.
* Long commands are split: `python3 -I tools/run_m93_all.py --list` prints 84 groups, `--group N` runs one; the regression tool takes `--step Rnn`; the mutation run is given in chunks of ten ids. A run cut off by a time limit is incomplete, not a pass. The auditor's full nested M5 and M6 wrapper runs on M9.2 did not complete in the auditor's environment; they are recorded as incomplete (CF-30), and this package splits them into numbered groups.
* F-52 to F-62, CF-22, CF-25 and CF-29 stay open until the auditor verifies them independently. The correction is builder-implemented and locally tested, not independently reviewed.

---- the M9.2 readme follows, unchanged ----

# APG M9.2 -- correction of the approval request boundary after the independent audit of M9.1 (F-58 to F-61; DRAFT, builder-made, non-production)

This package is the delivered M9.1 package plus one correction release. The independent audit of M9.1 did not accept it: it reproduced three defects (the approval token returned to a caller who cannot approve, an unaudited conflict outcome, an identifier check that let a trailing newline through) and raised an audit-consistency risk. The delivered M9.1 ZIP and documents are not changed (their hashes are in the documents file); this is a separately versioned, additive release.
It starts nothing of Engine #17 and nothing of M7. RFC-01 is still PROPOSED and unnumbered.

* Changed application code: `apg/api/approval_boundary.py` only. `present` gives the token only when `can_approve` is true (F-58); the conflict on opening the request record is audited (F-59); identifiers and the session expiry time are matched as whole ASCII strings (F-60); a refused call of `check_for_execution` is audited (F-61, found by the builder in the same class); and the approval's audit entry is now written BEFORE the answer is noted, so a failed audit write leaves the request open and the retry writes the entry (the audit is at least once; exactly once needs the Engine, EDR-32).
* New tests (24): `tests/test_api_m92_corrections.py`. Run against the delivered M9.1 code, 16 of the 24 fail or error; run against this release, all pass. No existing test changed (the 78 API tests of M9.1 are unchanged and pass).
* New tools: `probe_m91_audit_findings.py` (prints DEFECT PRESENT on M9.1 and THE AUDIT FINDINGS ARE CORRECTED here), `make_m92_registers.py`, `programme_check_m92.py`, `run_regression_m92.py` (splittable with `--step`), `run_m92_all.py` (splittable with `--group N`). Changed tools: `m91_mutants.py` (runs the correction tests), `make_m0.py`, `programme_check_m91.py` and `run_regression_m6.py` to `run_regression_m91.py` (accept the M9.2 rows, tables and declared files; every other check is unchanged).
* New document: `programme/CHANGE_RECORD_APG-M9.2.md`. Changed: `programme/APPROVAL_REQUEST_BOUNDARY.md` (the token rule, the audit order, strict identifiers; a wrong module path corrected), this readme, `RUN_COMMANDS.txt` and six programme tables (rows appended: F-58 to F-61, SR-81 to SR-83, I-88 to I-92, EDR-32, CF-28, CF-29; the M9 row's handoff list gained EDR-32).
* Everything else is byte-identical to the delivered M9.1 package. `python3 -I tools/run_regression_m92.py --static` checks all of it.
* Long commands are split: `python3 -I tools/run_m92_all.py --list` prints 27 groups, `--group N` runs one; the regression tool takes `--step Rnn`; the mutation run is given in chunks of ten ids. A run cut off by a time limit is incomplete, not a pass.
* F-52 to F-61, CF-22 and CF-25 stay open until the auditor verifies them independently. The corrections are builder-implemented and locally tested, not independently reviewed.

---- the M9.1 readme follows, unchanged ----

# APG M9.1 -- first slice of M9: the approval request boundary (CF-25; DRAFT, builder-made, non-production)

This package is the delivered M6.5 package plus one new, additive package of application code, `apg/api` (five files), and what goes with it. It is the first slice of M9 (workflows and API contract) and the builder's answer to carried-forward item CF-25. It starts nothing of Engine #17 and nothing of M7.
The delivered M5, M6, M6.1, M6.2, M6.3, M6.4 and M6.5 archives and their hashes are not changed; this is a separately versioned release.

* New: `apg/api/approval_boundary.py` with three calls, `present` (what an approval screen shows, and the token to hand back), `request_approval` (the request: checked for shape, a person with a live session and the approver role, authorisation for the finding's project asked of a port on every request, one answer per request id, recovery of a request that stopped half way, an audit event for every outcome) and `check_for_execution` (for whoever carries the action out: is the approval still in force for exactly this version, evidence digest and proposal?). It calls the existing lifecycle (`approve_action`) and changes nothing in it.
* New: the `ProjectActionPort` (EDR-31, an Engine-owned port: may this person view or approve the findings of this project?), a 14-case contract suite, an in-memory reference (a test double, not a permission model) and 16 deliberately faulty ports: `apg/api/contracts_m9.py`, `reference_m9.py`, `faulty_m9.py`; `python3 -I tools/run_m91_contracts.py`.
* New tests (78): `tests/test_api_approval_boundary.py` (67), `tests/test_api_action_port_contract.py` (4), `tests/test_api_static.py` (7). New tools: `probe_approval_boundary.py`, `m91_mutants.py`, `make_m91_registers.py`, `programme_check_m91.py`, `run_regression_m91.py`, `run_m91_all.py`, `run_m91_contracts.py`. New documents: `programme/APPROVAL_REQUEST_BOUNDARY.md` (the contract), `programme/CHANGE_RECORD_APG-M9.1.md`.
* Changed: no application file of M6.5 or earlier, and no existing test. Earlier tools and register checks were changed only to accept the M9.1 files, rows and tables (`make_m0.py`, `programme_check_m4.py`, `m5`, `m6`, `m65`, `run_regression_m6.py` to `run_regression_m65.py`); this readme; `RUN_COMMANDS.txt`; and five programme tables (rows appended: SR-76 to SR-80, I-81 to I-87, EDR-31, CF-26, CF-27; the M9 milestone row gained a status and EDR-31). `python3 -I tools/run_regression_m91.py` checks all of it.
* Everything else is byte-identical to the delivered M6.5 package.
* RFC-01 is still PROPOSED and unnumbered; nothing of Engine #17 is built; M7 has not started.
* There is no screen, API, HTTP layer, session store, role directory or project permission model, and nothing executes an action. The port is the Engine's; the reference is a test double.
* F-52, F-53, F-54, F-55, F-56 and F-57 stay open until the auditor verifies them independently. CF-22 and CF-25 stay open.
* Builder-implemented and locally tested, not independently reviewed.

---- the M6.5 readme follows, unchanged ----

# APG M6.5 -- fifth correction release (finding F-57; DRAFT, builder-made, non-production)

This package is the delivered M6.4 package with one narrowly scoped correction: the approval gate now sits in the lowest-level call. The independent audit of M6.4 showed that `transition(..., 'action_approved', ...)` accepted an approval that named no finding version, no evidence digest and no proposal reference (or only some of them), although the entry point `approve_action` refused it. `transition` itself now requires all three, well formed (`APPROVAL_TOKEN_REQUIRED`), and checks each against the record (`STALE_APPROVAL`, `STALE_PROPOSAL`, `PROPOSAL_CHANGED`). Moving an approved finding to `in_progress` also re-checks that the approval is still in force (`APPROVAL_NOT_CURRENT`).
The delivered M5, M6, M6.1, M6.2, M6.3 and M6.4 archives and their hashes are not changed; this is a separately versioned release. The defect was reported by the independent audit of M6.4 and reproduced by the builder on the delivered M6.4 package.

* Changed in application code: `apg/det/findings.py` only. Added: `tests/test_det_transition_gate.py` (36 tests: 33 written before the change, and 3 added afterwards, see the change record; 8 of them fail on the M6.4 code), `tools/probe_transition_bypass.py` (reproduces the defect; prints DEFECT PRESENT on the M6.4 code), `tools/run_regression_m65.py`, `tools/programme_check_m65.py`, `tools/run_m65_all.py`, `tools/make_m65_registers.py`.
* Existing tests that approve through the lower-level call were changed in their calls, because that call now needs the whole token: `test_det_approval_binding.py`, `test_det_findings.py`, `test_det_findings_edges.py` (these two are M5 files), `test_det_proposal_binding.py`, `test_det_proposal_identity.py`, `test_det_version_types.py`, and the shared fixture file `helpers_det.py` (one helper added). Five tests asserted the old optional behaviour or its consequences and their assertions were changed; they are listed in the change record. Also changed: `tools/m5_mutants.py` (runs the new tests), `tools/make_m0.py`, `tools/probe_approval_binding.py`, `tools/probe_malformed_proposal_version.py`, `tools/probe_stale_proposal.py`, `tools/run_regression_m6.py` to `run_regression_m64.py` (accept the M6.5 declarations), this readme, `RUN_COMMANDS.txt`, and three append-only programme tables (rows F-57, I-79 and I-80, SR-74 and SR-75).
* Everything else is byte-identical to the delivered M6.4 package: `python3 -I tools/run_regression_m65.py` checks it.
* RFC-01 is still PROPOSED and unnumbered; nothing of Engine #17 is built; M7 has not started; the approval request boundary (CF-25) is not started.
* F-52, F-53, F-54, F-55, F-56 and F-57 stay open until the auditor verifies them independently. CF-22 stays open (no approval screen or API exists).
* Builder-implemented and locally tested, not independently reviewed.

---- the M6.4 readme follows, unchanged ----

# APG M6.4 -- fourth correction release (finding F-56; DRAFT, builder-made, non-production)

This package is the delivered M6.3 package with one narrowly scoped correction: an approval is now bound to the exact proposal that the approver was shown. The approval token (`approval_token`) carries a `proposal` reference (a digest of the proposal's text, proposer, time, the version and evidence digest it was written against, and how many proposals it replaced). `approve_action` refuses a token without it (`APPROVAL_TOKEN_REQUIRED`), refuses an approval that names a proposal other than the one on record (`PROPOSAL_CHANGED`), and keeps the reference of the approved proposal in the record.
The delivered M5, M6, M6.1, M6.2 and M6.3 archives and their hashes are not changed; this is a separately versioned release. The defect was found by the builder, not by the auditor, while inspecting the approval gate CF-22.

* Changed in application code: `apg/det/findings.py` only. Added: `tests/test_det_proposal_identity.py` (29 tests: 25 written, and seen to fail, before the change; 4 added afterwards, see the change record), `tools/probe_proposal_swap.py` (reproduces the defect; prints DEFECT PRESENT on the M6.3 code), `tools/run_regression_m64.py`, `tools/programme_check_m64.py`, `tools/run_m64_all.py`, `tools/make_m64_registers.py`.
* Three existing test files were updated because they call `approve_action` or build approval records by hand: `test_det_approval_binding.py`, `test_det_proposal_binding.py`, `test_det_version_types.py` (calls and fixtures only; every assertion is kept). No M5 or earlier test changed. Also changed: `tools/m5_mutants.py` (runs the new tests), `tools/make_m0.py`, `tools/probe_malformed_proposal_version.py`, `tools/programme_check_m62.py`, `tools/programme_check_m63.py`, `tools/run_regression_m6.py`, `tools/run_regression_m61.py`, `tools/run_regression_m62.py`, `tools/run_regression_m63.py` (accept the M6.4 rows and declared files), this readme, `RUN_COMMANDS.txt`, and four append-only programme tables (row F-56, I-75 to I-78, SR-72 and SR-73, CF-25).
* Everything else is byte-identical to the delivered M6.3 package: `python3 -I tools/run_regression_m64.py` checks it.
* RFC-01 is still PROPOSED and unnumbered; nothing of Engine #17 is built; M7 has not started.
* F-52, F-53, F-54, F-55 and F-56 stay open until the auditor verifies them independently. CF-22 stays open (no approval screen or API exists; CF-25 records what a request boundary still needs).
* Builder-implemented and locally tested, not independently reviewed.

---- the M6.3 readme follows, unchanged ----

# APG M6.3 -- third correction release (finding F-55; DRAFT, builder-made, non-production)

This package is the delivered M6.2 package with one narrowly scoped correction: the checks of a stored or named finding version and evidence digest now fail closed. A version must be a whole number of at least 1 and not a boolean; a digest must be a non-empty text; a malformed value makes a proposal or an approval not current, so an action cannot be approved on it.
The delivered M5, M6, M6.1 and M6.2 archives and their hashes are not changed; this is a separately versioned release.

* Changed in application code: `apg/det/findings.py` only. Added: `tests/test_det_version_types.py` (34 tests, written, and seen to fail, before the change), `tools/probe_malformed_proposal_version.py` (reproduces the audit's defect; prints DEFECT PRESENT on the M6.2 code), `tools/run_regression_m63.py`, `tools/programme_check_m63.py`, `tools/run_m63_all.py`, `tools/make_m63_registers.py`.
* No existing test file was changed. Changed elsewhere: `tools/m5_mutants.py` (runs the new tests), `tools/make_m0.py`, `tools/programme_check_m62.py`, `tools/run_regression_m6.py`, `tools/run_regression_m61.py` and `tools/run_regression_m62.py` (accept the M6.3 rows and declared files), this readme, `RUN_COMMANDS.txt`, and four append-only programme tables (row F-55, I-71 to I-74, SR-70 and SR-71, CF-24 added). The exact list, with hashes, is in `programme/CHANGE_RECORD_APG-M6.3.md` and `regression/BASELINE_M62.json`.
* Everything else is byte-identical to the delivered M6.2 package: `python3 -I tools/run_regression_m63.py` checks it.
* RFC-01 is still PROPOSED and unnumbered; nothing of Engine #17 is built; M7 has not started.
* F-52, F-53, F-54 and F-55 stay open until the auditor verifies them independently.
* Builder-implemented and locally tested, not independently reviewed.

---- the M6.2 readme follows, unchanged ----

# APG M6.2 -- second correction release (findings F-53 and F-54; DRAFT, builder-made, non-production)

This package is the delivered M6.1 package with one narrowly scoped correction: an action can only be approved while its proposal was written against the finding's current version and evidence digest, and the exact text and context of a replaced proposal or an ended approval is kept in the record.
The delivered M5, M6 and M6.1 archives and their hashes are not changed; this is a separately versioned release.

* Changed in application code: `apg/det/findings.py` only. Added: `tests/test_det_proposal_binding.py` (47 tests, written, and seen to fail, before the change), `tools/probe_stale_proposal.py` (reproduces the audit's defect; prints DEFECT PRESENT on the M6.1 code), `tools/run_regression_m62.py`, `tools/programme_check_m62.py`, `tools/run_m62_all.py`, `tools/make_m62_registers.py`, `programme/CARRIED_FORWARD_REGISTER.csv`.
* Changed elsewhere: `tests/test_det_approval_binding.py` (an M6.1 file; its tests that approved straight after an ended approval now propose again first), `tools/m5_mutants.py` (runs the new tests), `tools/make_m0.py`, `tools/programme_check_m6.py`, `tools/run_regression_m6.py` and `tools/run_regression_m61.py` (accept the M6.2 rows and declared files), this readme, `RUN_COMMANDS.txt`, and three append-only programme tables (rows F-53 and F-54, I-65 to I-70, SR-66 to SR-69 added). The exact list, with hashes, is in `programme/CHANGE_RECORD_APG-M6.2.md` and `regression/BASELINE_M61.json`.
* Everything else is byte-identical to the delivered M6.1 package: `python3 -I tools/run_regression_m62.py` checks it.
* `programme/CARRIED_FORWARD_REGISTER.csv` lists the issues the audits left open and that this release does not touch (tenant and project isolation, invoice-only cost coverage, synthetic-only data, event and provenance gaps, portfolio purchasing that is not the specified forward aggregation, the governance blockers). It closes nothing.
* RFC-01 is still PROPOSED and unnumbered; nothing of Engine #17 beyond the corrections is built; M7 has not started.
* Builder-implemented and locally tested, not independently reviewed.

---- the M6.1 readme follows, unchanged ----

# APG M6.1 -- correction release of the M6 pack (finding F-52; DRAFT, builder-made, non-production)

This package is the delivered M6 package with one narrowly scoped correction: an approval of a finding's action is now bound to the finding version and the evidence digest that were approved, and is ended when the evidence changes.
The delivered M5 and M6 archives and their hashes are not changed; this is a separately versioned release.

* Changed in application code: `apg/det/findings.py` only. Added: `tests/test_det_approval_binding.py` (21 tests; the first 14 were written, and seen to fail, before the change), `tools/probe_approval_binding.py` (reproduces the defect; prints DEFECT PRESENT on the M6 code), `tools/run_regression_m61.py`, `tools/programme_check_m61.py`, `tools/run_m61_all.py`, `tools/make_m61_registers.py`.
* Changed elsewhere: `tools/m5_mutants.py` (runs the new tests), `tools/make_m0.py` (runs the M6.1 register step), `tools/run_regression_m6.py` (accepts the M6.1 status rows), this readme, `RUN_COMMANDS.txt`, and three append-only programme tables (rows F-52, I-59 to I-64, SR-62 to SR-65 added). The exact list, with hashes, is in `programme/CHANGE_RECORD_APG-M6.1.md` and `regression/BASELINE_M6.json`.
* Everything else is byte-identical to the delivered M6 package: `python3 -I tools/run_regression_m61.py` checks it.
* `programme/E17_GOVERNANCE_RECORD.md` and `programme/E17_GOVERNANCE_REGISTER.csv` record the auditor's 2026-10-15 directions on Engine #17 and the proposed baseline rules. They are records. RFC-01 is still PROPOSED and unnumbered; nothing of Engine #17 beyond this correction is built; M7 has not started.
* `programme/E17_PHASE_0_REPOSITORY_DISCOVERY.md` is the Phase 0 report (builder-produced; not an independent audit).
* Builder-implemented and locally tested, not independently reviewed.

---- the M6 readme follows, unchanged ----

# APG M6 materials and market -- code and data pack (DRAFT, builder-made, non-production)

* `apg/mkt/` -- the procurement and market layer: `policy` (the procurement policy and the specification register: versioned, immutable, two-person, no defaults), `intake` and `mkt_templates/` (quotes, orders, deliveries, materials, readings, FX and index series in),
  `fx` and `fresh` (exchange rates and the freshness gates), `spec` (the specification register), `landed` (landed cost), `intl` (international checks), `compare` (the comparability gate and the ranking), `demand` (demand coverage, over-ordering, duplicates),
  `scenarios` (buy now, wait, stage, negotiate), `opportunity`, `suppliers`, `purchasing` (opportunities, supplier performance, portfolio purchasing), `events` (apg-event-1 hooks only), `analysis`, `rules` (MP01 to MP10 and MPD1), `detect` (the two reproducible formulas),
  `gather`, `common`, `ports_m6`, `contracts_m6`, `reference_m6`, `faulty_m6` (the ExtractionRuntimePort and MarketFeedPort and their contract suites), `golden_mkt`, `demo_mkt`
* `apg/det/` -- the M5 detection layer, unchanged except four files (`detect`, `findings`, `relations`, `portfolio`; listed in `regression/BASELINE_M5.json` as changed in M6); `apg/fin/`, `apg/ingest/`, `apg/` -- earlier layers, unchanged
* `tests/` -- M2 to M5 tests (M5 `test_det_portfolio.py` has 2 new tests) and the M6 tests (`test_mkt_*.py`)
* `tools/` -- test runners, the M6 mutation tool, the regression tools and the earlier checks
* `regression/` -- the M5 baseline hashes, the stored M5 and earlier snapshots of the programme tables, golden answers, saved demonstration outputs
* `programme/` -- milestones, Engine handoff register (30 entries), status register, findings and interpretations registers, and the RFC register with RFC-01 (PROPOSED, not approved)
* `mkt_data/`, `builder_zero/`, `catalogue/`, `research/`, `import_templates/`, `ingest_templates/`, `fin_templates/`, `det_templates/`, `mkt_templates/`, `gap_map/`, `data/`, `reference/cr02/` -- data and reference code (the first and `mkt_templates/` are new in M6; the rest unchanged)
* `logs/` -- the builder's run output; `RUN_COMMANDS.txt`

The explanation is in the separate documents file. No Engine code, repository, database, AUIF package, builder system or market-data provider was inspected or connected.
