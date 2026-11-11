#!/usr/bin/env python3
"""Writes the M0 programme tables and the draft translation-pack table. Usage: make_m0.py <out_programme_dir> <out_catalogue_dir>"""
import csv, os, sys
OP, OC = sys.argv[1], sys.argv[2]
os.makedirs(OP, exist_ok=True); os.makedirs(OC, exist_ok=True)
def wcsv(path, header, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(header); w.writerows(rows)

STOP = 'Stop and report if: a locked Section 00-18 would need changing (log a spec issue, never edit); a decision only the product owner can make blocks the work; or the work needs the Anchor Engine (log it in the handoff register instead).'
ML = [  # id, name, objective, builds, acceptance, covers_caps, blueprint_phase, produces_edr
 ('M0', 'Programme plan and handoff register', 'Fix the method, conventions, milestone ladder and the format of the Engine handoff register and the status register.',
  'Plan, conventions, handoff register (first entries), status register (first entries). No code.',
  'Registers pass their structural checks; every capability CAP-01..CAP-33 is assigned to a milestone; nothing is claimed beyond Specified.', '', 'Section 14 Phase 0 (planning only)', 'EDR-01..EDR-19 opened'),
 ('M1', 'Pre-pilot readiness pack', 'Give the pilot work something to test against and something to ask: a synthetic builder, a candidate systems catalogue, a file-import template format, draft translation-pack specs.',
  'Builder Zero synthetic data and checker; candidate systems catalogue (vendor-document research); mapping-template format with validator and examples; draft translation-pack specs.',
  'Builder Zero regenerates byte for byte and every planted fact is recomputed from the files; catalogue rows keep their evidence grades; templates validate; validator rejects broken templates.', 'CAP-01; CAP-04; CAP-33', 'Section 14 Phase 0 (non-production prototypes are exempt under Section 01 §8)', ''),
 ('M2', 'Control foundations', 'Build the Engine-independent control logic that every later layer depends on.',
  'Status model and evidence checks; materiality policy engine (from CR-02, with the open decisions left as configuration); source authority logic; tenant-scope guard logic; reproducibility record format; ports and contract tests for storage, events, tenancy.',
  'Local tests and sabotage tests pass; ports are specified with contract tests Amir must pass.', 'CAP-03; CAP-06; CAP-31; CAP-32; CAP-33', 'Section 14 Phase 1', 'EDR-01; EDR-02; EDR-03; EDR-20; EDR-21'),
 ('M3', 'Ingestion pipeline', 'Build the pipeline logic from raw record to reconciled, provenance-carrying canonical record.',
  'Validation layers, quarantine and provisional rules, idempotency and duplicates, entity resolution, freshness and completeness, file and document intake logic.',
  'All Builder Zero ingestion scenarios behave as the register says; replay creates no second financial effect.', 'CAP-02; CAP-03; CAP-04; CAP-05; CAP-06', 'Section 14 Phase 1 and 2', 'EDR-04; EDR-07; EDR-22; EDR-23'),
 ('M4', 'Financial core', 'Build recognised margin, forecast final margin, cost-to-complete and cash-position-adjusted margin with reproducible inputs.',
  'Authoritative calculation modules; bridges; retention and cash logic; immutable calculation records.', 'Calculations reproduce from stored inputs; reference models agree on Builder Zero.', 'CAP-10; CAP-11; CAP-31', 'Section 14 Phase 2', ''),
 ('M5', 'Detection layers', 'Build the deterministic leak and risk detection rules and their lifecycle.',
  'The nine Section 06 rule types; commercial, delay, labour, quality, compliance, plant; alert-noise control; finding lifecycle.', 'Every planted positive is found and every negative control stays silent, at illustrative thresholds.', 'CAP-07; CAP-08; CAP-09; CAP-12; CAP-13; CAP-14; CAP-15; CAP-16; CAP-17', 'Section 14 Phase 3', 'EDR-10'),
 ('M6', 'Materials and market', 'Build quote capture, comparability, landed cost, market data handling, buy-timing scenarios and savings gates.',
  'Comparability gate; landed cost; freshness gate; scenario generator; over-ordering; supplier performance; international safeguards; portfolio purchasing.', 'No definitive recommendation passes the comparability or freshness gates when it should not.', 'CAP-18; CAP-19; CAP-20; CAP-21; CAP-22; CAP-23; CAP-24; CAP-25; CAP-26', 'Section 14 Phase 3', 'EDR-08; EDR-09'),
 ('M7', 'Recommendations', 'Build eligibility, prioritisation, scenario isolation and the realised-savings gate.',
  'Recommendation engine logic; scenario isolation; human-approval records; realised-savings evidence rules.', 'Scenarios never change the official forecast; savings count only with evidence.', 'CAP-27; CAP-28; CAP-29; CAP-30', 'Section 14 Phase 4', ''),
 ('M8', 'AUIF-side integration and file import', 'Build the APG side of the integration surface and the file-import path.',
  'Connector contract adapters (stubbed), translation-pack runtime, mapping-template applier, drift handling, degradation states.', 'File import works end to end on Builder Zero; adapters pass contract tests against stubs.', 'CAP-01; CAP-04; CAP-07', 'Section 14 Phase 4', 'EDR-05; EDR-06'),
 ('M9', 'Workflows and API contract', 'Define and build workflow logic and the API contract.',
  'Review and approval workflows; API specification; authorisation rules as logic.', 'Contract tests and workflow tests pass.', 'CAP-05; CAP-09; CAP-30', 'Section 14 Phase 5', 'EDR-11'),
 ('M10', 'UX/UI prototype', 'Build the user interface prototype over fixtures.',
  'Screens for findings, projects, data health, import, approvals; accessibility and clarity checks.', 'Screens render from Builder Zero data; no screen presents an estimate as a realised saving.', 'CAP-05; CAP-09; CAP-27', 'Section 14 Phase 5', 'EDR-12'),
 ('M11', 'Full verification', 'Run everything together and record what is and is not shown.',
  'End-to-end local tests; adversarial and mutation tests; traceability update.', 'Evidence ladder recorded honestly; remaining gaps listed.', 'CAP-31; CAP-33', 'Section 14 Phase 6', 'EDR-13; EDR-17'),
 ('M12', 'Handoff to Amir', 'Assemble the full build ZIP and the handoff package for Amir to finish.',
  'Build ZIP; per-port handoff description with contract tests; deployment, database and integration closure checklist.', 'Every open handoff register entry has a full description and a contract test.', '', 'Section 14 Phases 6 and 7 (Amir)', 'EDR-14; EDR-15; EDR-16; EDR-18; EDR-19')]
wcsv(f'{OP}/PROGRAMME_MILESTONES.csv', ['milestone_id', 'name', 'objective', 'what_is_built', 'acceptance_criteria', 'stop_conditions', 'covers_capabilities', 'blueprint_phase', 'handoff_register_entries', 'status'],
     [[m[0], m[1], m[2], m[3], m[4], STOP, m[5], m[6], m[7], 'Delivered - builder-checked' if m[0] in ('M0', 'M1', 'M2') else ('In this delivery' if m[0] == 'M3' else 'Not started')] for m in ML])

EDR = [  # id, port, title, needs, why, contract, test, refs, caps, bl, milestones, amir
 ('EDR-01', 'TenantContextPort', 'Authenticated tenant and user context',
  'Every request, job and import must carry a tenant and user identity taken from the authenticated session, never from a payload or file.',
  'Authentication and session handling live in the Engine.',
  'Input: a request or job handle. Output: tenant_id, user_id, roles, or a refusal. Invariants: payload-supplied tenant or organisation IDs are ignored; a missing context is a refusal, not a default tenant.',
  'tenant_context_contract (written in M2, apg/contracts): refusal on missing, unknown, revoked, expired or altered context; credentials carry no tenant; two tenants with the same user ids stay apart. Passes on the in-memory reference implementation; not yet run on any Engine implementation.', '04:6; 04:16; 15:15.5', 'CAP-06', '', 'M2; M3; M9', 'How the Engine exposes the authenticated context to modules; role model.'),
 ('EDR-02', 'RecordStorePort', 'Tenant-scoped persistence with transactions',
  'Store and read canonical records, calculation records, findings and registers, always scoped to a tenant, with transactions and immutable history for financial records.',
  'The database, migrations and transaction behaviour belong to the Engine and its environment.',
  'Operations: put, get, query, append-revision (never overwrite), transaction. Invariants: tenant scope on every call; revisions append; money as integer cents; no cross-tenant reads.',
  'record_store_contract (written in M2, apg/contracts): tenant isolation with colliding keys, append-only revisions, idempotent put, expected-revision conflict, atomic batches with rollback, integer-only payloads, copy-in and copy-out. Passes on the in-memory reference implementation; not yet run on any Engine implementation. True concurrent writers need the real database (see Phase 7 closure).', '04:16; 16:7; 14:14.10', 'CAP-02; CAP-06; CAP-31', 'BL-18', 'M2; M3; M4', 'Database technology; migration tooling; how Section 14 Phase 7 database closure is evidenced.'),
 ('EDR-03', 'AuditLogPort', 'Append-only audit and event log',
  'Record who did what and which evidence was used, tamper-evident, for ingestion, approvals, findings and recalculation.',
  'Audit storage and integrity protection are platform services.',
  'Operations: append(event), read(range), verify(chain). Invariants: append-only; each event carries tenant, actor, time, input reference, formula version.',
  'audit_log_contract (written in M2, apg/contracts): append-only, per-tenant hash chain, verification detects edited, deleted or carefully rewritten events, redaction of secret-like keys, actor kind recorded. Passes on the in-memory reference implementation; not yet run on any Engine implementation.', '04:17; 15:15.8; 17:10', 'CAP-31; CAP-33', '', 'M2; M3; M9', 'Whether the Governor or the Engine owns the log; retention.'),
 ('EDR-04', 'JobRunnerPort', 'Background jobs, scheduling, retries',
  'Run ingestion, recalculation, freshness checks and alert evaluation on a schedule and after events, with retries that cannot create a second financial effect.',
  'Scheduling and workers are deployment concerns of the Engine.',
  'Operations: schedule, enqueue(idempotency_key), retry policy, dead-letter. Invariants: the same idempotency key never produces two effects; failures are visible, not silent.',
  'job_runner_contract (written in M3, apg/ingest/contracts_m3.py, cases JR-01..JR-14): handler runs once with a store bound to the credentials tenant; a succeeded job id is replayed, never re-run; retries are bounded with non-decreasing waits; permanent errors go straight to the dead-letter list; every attempt re-authenticates; the same job id in two tenants is two jobs; tenant claims in a message are refused; requeue is explicit; a terminal failure that cannot be recorded is reported, not dropped. Passes on the in-memory reference runner; 15 deliberately faulty runners are each caught; not yet run on any Engine implementation.', '04:15; 16:6', 'CAP-02; CAP-05', '', 'M3; M5', 'Queue technology; concurrency limits per tenant. A worker needs its OWN service identity to record a terminal failure after the submitting credentials have been revoked or have expired (the reference runner keeps such failures in an unrecorded list and reports them); which identity, how it is issued, and who may requeue a dead-lettered job.'),
 ('EDR-05', 'ConnectorRuntimePort', 'Live connector runtime through AUIF (access tier T1)',
  'Run live connectors to a builder system, receive records with provenance, report health, honour the Governor.',
  'Needs the AUIF runtime, real credentials and a real builder system; the "no real external system" restriction on AUIF is not yet lifted.',
  'Operations: list_sources, pull(since), health, schema_drift_report. Invariants: read-only toward the builder system in the first release; no record is authoritative merely because a connector delivered it; AUIF never authorises.',
  'connector_contract (M8): stub connector passes; malformed, stale, partial and duplicate deliveries handled.', '04:4; 15:15.10; 16:9', 'CAP-01', 'BL-03; BL-17', 'M8', 'Reconcile with the actual AUIF extension package and GD-05; first real system.'),
 ('EDR-06', 'SecretsPort', 'Credentials and secrets for connectors',
  'Hold connector credentials (for example OAuth tokens) with rotation, never in code, logs or fixtures.',
  'Secret storage and rotation are platform services of the Engine.',
  'Operations: get(handle), rotate, revoke. Invariants: secrets never appear in logs, exports or the audit log; per-tenant separation.',
  'secrets_contract (M8): secret never present in log output; revoked secret refused.', '15:15.7; 15:15.10', 'CAP-01; CAP-06', '', 'M8', 'Where secrets are held, how they are rotated, and who can read them.'),
 ('EDR-07', 'FileStorePort', 'Uploaded file and document storage',
  'Store uploaded files and documents with hashing, malware scanning, retention and tenant scope.',
  'Object storage and scanning are platform services.',
  'Operations: put(file) -> content hash, get, scan_status, delete-by-policy. Invariants: tenant scope; content hash recorded; unscanned files are not parsed.',
  'file_store_contract (written in M3, apg/ingest/contracts_m3.py, cases FS-01..FS-10): SHA-256 and size recorded, id depends on the bytes only; same bytes are one file and a later file never replaces an earlier one; returned bytes are an independent copy; another tenant sees a missing file; every call needs a verified context; SCAN GATE (unscanned and infected files cannot be read; only a service identity with the role file_scanner records a verdict; infected is terminal); damaged bytes are refused on every read path; oversize data, non-bytes and unsafe names are refused. Passes on the in-memory reference store; 13 deliberately faulty stores are each caught; not yet run on any Engine implementation.', '04:18; 15:15.6', 'CAP-04; CAP-06', '', 'M3', 'Storage service; scan tool and how it is given the service identity with the role file_scanner; retention periods; maximum file size.'),
 ('EDR-08', 'ExtractionRuntimePort', 'AI document extraction service',
  'Read quotes and invoices from PDFs and emails into structured values with confidence and a human verification step.',
  'The language-model runtime, its keys and its trust-boundary controls are platform services.',
  'Operations: extract(document) -> values with source span and confidence. Invariants: extracted values stay provisional until a person verifies material ones; unclear characters are reported as ambiguous, never guessed.',
  'extraction_contract (M6): ambiguous Builder Zero document yields ambiguity flags, not values.', '04:12; 15:15.9', 'CAP-18', '', 'M6', 'Model choice; data handling; cost controls.'),
 ('EDR-09', 'MarketFeedPort', 'Licensed and public market data retrieval',
  'Fetch market and FX data with source, licence and freshness recorded.',
  'Needs real feeds and licence decisions; vendor terms for several sources are unconfirmed.',
  'Operations: fetch(series), licence_status, freshness. Invariants: every observation carries source, geography, unit, as-of date; stale data downgrades analysis.',
  'market_feed_contract (M6): stale series downgrade; unlicensed series refused.', '08:7.1; 16:5', 'CAP-20; CAP-25', 'BL-05; BL-06', 'M6', 'Which sources are licensed; the DEC-MIE-01 decision.'),
 ('EDR-10', 'NotificationPort', 'Alert delivery to people',
  'Deliver alerts to people with de-duplication and noise control.',
  'Email or in-app delivery is a platform service of the Engine.',
  'Operations: send(recipient, alert, dedupe_key). Invariants: no autonomous external action; repeats suppressed per policy.',
  'notification_contract (M5): duplicate suppressed; delivery failure visible.', '02:8; 06:9.1', 'CAP-08; CAP-21', '', 'M5', 'Which channels are supported (email, in-app) and how users set preferences.'),
 ('EDR-11', 'ApiHostingPort', 'API hosting, authentication and rate limiting',
  'Serve the APG API with authentication, authorisation and rate limits.',
  'Hosting and the gateway are Engine concerns.',
  'Invariants: every route requires an authenticated context; authorisation checked per tenant and role.',
  'api_contract (M9): unauthenticated and cross-tenant calls refused.', '15:15.3; 15:15.4', 'CAP-05; CAP-30', '', 'M9', 'Which gateway is used and how API versions are managed.'),
 ('EDR-12', 'UiHostingPort', 'User interface hosting and sessions',
  'Host the interface and its sessions.',
  'Front-end hosting and session handling are platform services.',
  'Invariants: the interface renders only what the API authorises; estimates never shown as realised savings.',
  'ui_acceptance (M10): screens built from fixtures.', '15:15.3', 'CAP-05; CAP-27', '', 'M10', 'Front-end framework fit with the Engine.'),
 ('EDR-13', 'ObservabilityPort', 'Logs, metrics and alerts on the platform',
  'Make failures, data freshness, queue depth and degraded integrations visible to the people running the system, with no secrets in any log.',
  'The monitoring stack is a deployment concern of the Engine and its environment.',
  'Operations: emit(log, metric, health_state) and a way to read them. Invariants: every failure class listed in Section 16 section 3 can be seen; a stale or failed feed raises a visible state rather than silence; logs never contain secrets or another tenant data.',
  'observability_check (M11): inject each failure class on fixtures and confirm a visible signal; scan sample logs for secret patterns.', '16:4; 04:17', 'CAP-05', '', 'M11', 'Which monitoring tools the Engine already uses; who receives platform alerts; log retention period.'),
 ('EDR-14', 'BackupRestorePort', 'Backup, restore and disaster recovery',
  'Take backups of the APG records, restore them into a clean environment, and show the restored data is the same.',
  'Backups and restores need the real database and environment, which this build does not have.',
  'Operations: backup, restore, verify. Invariants: a restored copy passes the same integrity checks as the original (tenant scope, append-only history, hash chain of the audit log); restore time and data-loss window are recorded against targets.',
  'restore_drill (Amir): restore a backup into an empty environment, run record_store_contract and audit_log_contract against it, record the elapsed time.', '16:8', 'CAP-02', 'BL-18', 'M12', 'Recovery point and recovery time targets; who runs and signs the drill; where backups are held.'),
 ('EDR-15', 'DeploymentPort', 'Environments, deployment and staging',
  'A repeatable way to build, configure, deploy, roll back and test APG in a staging environment before any real use.',
  'The environments, pipeline and deployment tooling belong to the Engine team.',
  'Invariants: configuration is versioned and separate from code; a failed deployment can be rolled back; staging uses no real customer data unless approved; the build ZIP is the only input to the pipeline.',
  'deploy_checklist (Amir): deploy the build ZIP to staging, run all local suites there, roll back, deploy again, record each result.', '16:10; 14:14.10', 'CAP-33', 'BL-18', 'M12', 'Pipeline tooling; environment names; who approves a release; how configuration secrets are injected.'),
 ('EDR-16', 'GovernorPort', 'Governor decisions on what is permitted',
  'Before any consequential action (for example sending an alert externally or changing a record), ask the Governor whether it is permitted. AUIF connectors never authorise anything themselves.',
  'The Governor is a separate platform system that this build cannot reach.',
  'Operation: permitted(action, context) returns allow or deny with a reason. Invariants: deny by default if the Governor cannot be reached; every decision is written to the audit log; APG never treats a connector delivery as permission.',
  'governor_contract (M12): a stub Governor that allows, denies and times out; APG must deny on timeout and must log every decision.', '', 'CAP-30', '', 'M12', 'Governor interface and versioning. This is a platform requirement from the Anchor architecture, not a clause of the APG blueprint.'),
 ('EDR-17', 'DatabaseVerificationPort', 'Database-dependent verification',
  'Replay, concurrency and idempotency tests that can only be proven against the real database.',
  'Section 17 requires database-dependent evidence; fixtures and stubs cannot supply it.',
  'Tests: replay the same delivery twice and confirm one financial effect; run concurrent writers on one record; kill a job mid-write and confirm no partial state; confirm tenant isolation under load.',
  'db_verification_suite (written in M11, run by Amir against the real database).', '17:9; 17:8', 'CAP-33', 'BL-18', 'M11', 'Test database provisioning; whether production-like volumes are needed; who signs the evidence.'),
 ('EDR-18', 'RealSystemProofPort', 'Integration closure on a real builder system',
  'Prove at least one connector against a real builder system and reconcile its data against the builder own records.',
  'Needs a pilot builder, real access and AUIF running with the no-real-system restriction lifted.',
  'Evidence for connector readiness levels C4 (proven in a sandbox), C5 (reconciled on real data) and C6 (running with freshness monitoring). Invariant: read-only toward the builder system in the first release.',
  'integration_closure (Amir): for each connector, run the connector contract suite, then reconcile a sample of records against the builder system and record differences.', '14:14.10', 'CAP-01', 'BL-01; BL-03', 'M12', 'Which system first; access arrangements; the pilot builder agreement.'),
 ('EDR-20', 'RecordKindAuthorisationPort', 'Write authorisation by record kind',
  'Some record kinds (materiality policies and approvals, the decision ledger, source authority registers, quarantine dispositions, calculation records) must be writable only through the control functions that check roles, never by a direct store write from a tenant user session.',
  'Role and permission enforcement belongs to the Engine API and database layer; the port contract in M2 scopes by tenant but does not know roles.',
  'Input: a context, a record kind and a write. Output: allowed or refused. Invariant: a user session without the service identity of the owning control cannot write these kinds, and a refusal is audited. M2 tests prove the control functions check roles but cannot stop a direct write at the port.',
  'kind_authorisation_contract (to be written with M9 authorisation rules): a session holding only a tenant role cannot put into a protected kind; the owning control can; refusals are audited.', '04:6; 15:15.5; 04:17', 'CAP-06; CAP-31; CAP-33', '', 'M2; M3; M9', 'Which identities may write which kinds; how service identities are issued and rotated.'),
 ('EDR-21', 'AuditAnchorPort', 'Independent anchor for the audit chain head',
  'Detect a careful rewrite of the newest audit events, which a hash chain alone cannot detect, by publishing the chain head (sequence and hash) to a store the application cannot write.',
  'An independent store, time source or notary is a platform service.',
  'Operations: publish(head), fetch anchors, compare with verify(chain). Invariant: a chain whose head does not match a later anchor, or whose history before an anchor changed, fails verification. M2 contract tests detect a rewrite that breaks a link but state this limit for the tail.',
  'audit_anchor_contract (to be written with M9): rewrite the last events with recomputed hashes and show verification against the anchor fails.', '04:17; 15:15.8', 'CAP-31; CAP-33', '', 'M2; M3; M9', 'Anchor store and cadence; who can read anchors.'),
 ('EDR-19', 'RepositoryDiscoveryPort', 'Section 01 discovery of the real repository',
  'Inspect the real Anchor repository and environment, map the integration surfaces and sign off the Discovery Exit Report before any production feature code is merged.',
  'This build has no repository access, so Section 01 discovery has not been done.',
  'Section 01 requires discovery gates, an integration surface map and a signed exit report. Invariant: production code stays frozen until that report is signed; read-only probes and sandboxed prototypes are exempt.',
  'discovery_exit_report (Amir with the auditor): walk each Section 01 gate and attach the evidence.', '01:2; 01:8', 'CAP-33', 'BL-04', 'M12', 'Repository access; who signs the exit report; how this build code is reconciled with the real structure.')]
EDR += [
 ('EDR-22', 'SourceIdentityPort', 'Registered source identity for deliveries',
  'Check that the person or connector delivering a file or record is registered to deliver as the source it names (for example accounting or pm_system), so a delivery cannot claim the authority of a source it does not hold.',
  'Registered connectors, users and their permissions live in the Engine; the ingestion code in this build trusts the source name it is given and the authority register only names sources.',
  'Input: an authenticated context and a source name. Output: allowed or refused for that source in that tenant. Invariants: the source name on a delivery is checked against the sources the caller is registered for; a refusal is audited and nothing is written; the authority register names sources, the Engine decides who may speak as them.',
  'source_identity_contract (to be written with M8): a user or connector registered for pm_system cannot deliver as accounting; an unregistered source name is refused; refusals are audited.', '04:5; 04:6', 'CAP-02; CAP-06', '', 'M3; M8', 'How connectors and uploaders are registered per source; whether one identity may hold several sources; how this relates to the role model in EDR-20.'),
 ('EDR-23', 'BatchWriteLimitsPort', 'Transaction size limits for whole-file writes',
  'Write a whole delivered file (its records, its rejected rows, its duplicate and stale evidence and its receipt) as one all-or-nothing batch, so a failed or interrupted file leaves nothing half applied.',
  'Transaction size, duration and lock limits belong to the Engine database; the reference store accepts any batch.',
  'Input: one batch of up to the configured maximum file size (this build defaults to 100,000 rows and 5 MB) with expected-revision checks. Invariants: all or nothing; a refused batch leaves no record, reject or receipt behind; if a limit forces a file to be split, that is a stated decision because splitting removes the all-or-nothing guarantee for the file.',
  'atomic_batch_size_contract (to be written with M8): a batch at the configured maximum commits or is refused whole; a refused batch leaves nothing behind; a concurrent change to one record fails the whole batch.', '04:7; 04:15', 'CAP-02; CAP-05', '', 'M3; M8', 'The largest batch the database accepts; whether larger files are refused or split, and how a split file keeps one receipt and one replay key.'),
]
EDR.sort(key=lambda e: e[0])
wcsv(f'{OP}/ENGINE_HANDOFF_REGISTER.csv', ['edr_id', 'port', 'title', 'what_apg_needs', 'why_the_engine_is_needed', 'contract_summary', 'contract_test', 'blueprint_refs', 'capabilities', 'backlog_ids', 'needed_by_milestones', 'decisions_for_amir', 'owner', 'status', 'evidence_seen'],
     [[e[0], e[1], e[2], e[3], e[4], e[5], e[6], e[7], e[8], e[9], e[10], e[11], 'Amir (engine, database, environment)', 'Open - contract test written' if e[0] in ('EDR-01', 'EDR-02', 'EDR-03', 'EDR-04', 'EDR-07') else 'Open - described only', 'No Engine code, repository or environment seen; no implementation exists'] for e in EDR])

SR = [  # id, item, milestone, ladder, evidence, limit
 ('SR-01', 'Builder Zero synthetic data generator', 'M1', 'Local-tested', 'builder_zero_check.py: 43 checks incl. byte-for-byte regeneration', 'Builder-run, non-production, no independent review'),
 ('SR-02', 'Builder Zero checker', 'M1', 'Local-tested', 'Sabotage tests in the build record', 'Builder-run, no independent review'),
 ('SR-03', 'Candidate systems catalogue (56 rows)', 'M1', 'Research record', 'Vendor documents read 2026-10-13; spot-checked; grades kept', 'Not a requirement status. Not confirmed with any builder.'),
 ('SR-04', 'Mapping-template format, validator and examples', 'M1', 'Local-tested', 'mapping_template_check.py: 5 checks incl. 11 rejected broken templates', 'Draft; not yet checked on any real export'),
 ('SR-05', 'Draft translation-pack specs', 'M1', 'Specified', 'Each vendor entity name traced to the catalogue text', 'Unverified drafts'),
 ('SR-06', 'Programme milestones and handoff register', 'M0', 'Specified', 'programme_check.py', 'Plan only'),
 ('SR-07', 'Values, canonical JSON and port definitions', 'M2', 'Local-tested', 'tests/test_values.py; mutation run over canon.py and values.py', 'Builder-run on in-memory doubles; non-production; no independent review'),
 ('SR-08', 'Contract suites for tenant context, record store and audit log, with faulty-implementation proof', 'M2', 'Local-tested', 'tools/run_contracts.py; tools/run_faults.py (each faulty implementation must fail the suite)', 'Passes on in-memory reference doubles only; never run on an Engine implementation; ports are not integration-tested'),
 ('SR-09', 'Tenant-scope guards', 'M2', 'Local-tested', 'tests/test_tenancy.py; tests/test_adversarial_builder_zero.py (tenant spoofing); mutation run', 'Builder-run; synthetic builders only; role enforcement on direct store writes is an open handoff entry (EDR-20)'),
 ('SR-10', 'Source authority, quarantine and batch intake guard', 'M2', 'Local-tested', 'tests/test_source_authority.py; adversarial conflicting-source cases; mutation run', 'Rules in tests are synthetic; no real authority register exists, and none is approved'),
 ('SR-11', 'Status and evidence model', 'M2', 'Local-tested', 'tests/test_status_model.py; mutation run', 'Builder-run; models Section 17 section 2; not yet used on the real RTM'),
 ('SR-12', 'Reproducibility records', 'M2', 'Local-tested', 'tests/test_repro.py; golden reproducibility case; mutation run', 'Builder-run on in-memory store'),
 ('SR-13', 'Materiality policy engine around the CR-02 rev 2 model', 'M2', 'Local-tested', 'tests/test_materiality_engine.py; CR-02 reference tests and 79 CR-02 mutants rerun on the packaged model; engine mutation run', 'CR-02 remains PROPOSED; DEC-A1-1 to DEC-A1-8 remain open; test thresholds are illustrative'),
 ('SR-14', 'Golden regression cases and M0/M1 baseline', 'M2', 'Local-tested', 'tools/run_golden.py; tools/run_regression.py', 'Golden values come from the builder\'s own code plus an independent csv oracle; no independent review'),
 ('SR-15', 'Strict file mapping layer (exact money and dates, hidden characters, encodings, file-level refusals)', 'M3', 'Local-tested', 'tests/test_ingest_mapping.py; tools/run_ingest_corpus.py (44 deliberately faulty files); mutation run', 'Builder-run on Builder Zero layouts and synthetic faulty files; not run on any real export'),
 ('SR-16', 'Delivery decisions: duplicate, revision, stale, conflict; one atomic write per file; replay as a recorded no-op', 'M3', 'Local-tested', 'tests/test_ingest_pipeline.py; tests/test_ingest_adversarial.py; golden PS-11 and PS-24; mutation run', 'Builder-run on the in-memory store; real transaction limits are handoff entry EDR-23'),
 ('SR-17', 'Reconciliation: duplicates, relationship checks, field authority, review queue and decisions', 'M3', 'Local-tested', 'tests/test_ingest_reconcile.py (includes arrival-order independence over 482 records); golden PS-12, PS-13, PS-17, PS-21; mutation run', 'The authority register used is SYNTHETIC; no real register exists or is approved; DEC-A1-1 to DEC-A1-8 remain open'),
 ('SR-18', 'Supplier entity resolution that never chooses between look-alike suppliers', 'M3', 'Local-tested', 'tests/test_ingest_reconcile.py; golden PS-22; mutation run', 'Builder-run; the resolution ladder is the builder reading of Section 04 section 11 (interpretation I-11)'),
 ('SR-19', 'Freshness, completeness, quote validity and exact currency conversion', 'M3', 'Local-tested', 'tests/test_ingest_support.py; golden PS-14 and PS-23; mutation run', 'No built-in thresholds; every limit used in tests is ILLUSTRATIVE; with no limit configured the answer is cannot_assess'),
 ('SR-20', 'Document intake with human verification of extracted values (stand-in text extractor)', 'M3', 'Local-tested', 'tests/test_ingest_support.py; golden PS-26; mutation run', 'The extractor is a stand-in for two Builder Zero text files, not an extraction product (EDR-08); no extracted value is authoritative until a person verifies it'),
 ('SR-21', 'Job runner: bounded retries, dead-letter, replay, re-authentication, with the JobRunnerPort contract', 'M3', 'Local-tested', 'tests/test_ingest_support.py; tests/test_ingest_contracts.py; tools/run_m3_contracts.py; tools/run_m3_faults.py; mutation run', 'Passes on the in-memory reference runner only; never run on an Engine scheduler (EDR-04)'),
 ('SR-22', 'File store port with scan gate, and the scan-gated import path, with the FileStorePort contract', 'M3', 'Local-tested', 'tests/test_ingest_contracts.py; tools/run_m3_contracts.py; tools/run_m3_faults.py; golden scan-gate case; mutation run', 'Passes on the in-memory reference store only; no scanner exists in this build (EDR-07)'),
 ('SR-23', 'M3 golden cases, independent csv oracle, narrated demonstration and regression against the delivered M2 package', 'M3', 'Local-tested', 'tools/run_golden_m3.py; tools/run_demo_m3.py; tools/run_regression_m3.py', "Golden values come from the builder's own code plus an independent csv oracle; no independent review")]
wcsv(f'{OP}/STATUS_REGISTER.csv', ['item_id', 'item', 'milestone', 'evidence_ladder_status', 'evidence', 'claim_limit'], [list(s) for s in SR])

TP = [  # class, catalogue_id, system, apg_entity, vendor_entity, grade, open_question
 ('Q1', 'CAT-001', 'Procore', 'project', 'projects', 'B', 'Object list is from a secondary source; confirm in official reference.'),
 ('Q1', 'CAT-001', 'Procore', 'supplier', 'vendors', 'B', 'Confirm vendor fields and tax identifiers.'),
 ('Q1', 'CAT-001', 'Procore', 'defect', 'punch_items', 'B', 'A punch item may not equal a defect with rework cost; confirm how builders record rework cost.'),
 ('Q1', 'CAT-001', 'Procore', 'budget_line', 'budgets', 'C', 'Unconfirmed from official docs.'),
 ('Q1', 'CAT-001', 'Procore', 'commitment', 'commitments', 'C', 'Unconfirmed from official docs.'),
 ('Q1', 'CAT-001', 'Procore', 'variation', 'change orders', 'C', 'Unconfirmed; also confirm whether unpriced variations and client instructions are recorded here.'),
 ('Q1', 'CAT-001', 'Procore', 'ap_invoice', 'invoices', 'C', 'Unconfirmed; most builders may hold invoices in accounting instead (source authority question).'),
 ('Q2', 'CAT-008', 'Xero', 'ap_invoice', 'Invoice', 'B', 'Existence confirmed by webhook categories; field-level mapping unconfirmed.'),
 ('Q2', 'CAT-008', 'Xero', 'credit_note', 'CreditNote', 'B', 'Existence confirmed by webhook categories; link from credit to invoice unconfirmed.'),
 ('Q2', 'CAT-008', 'Xero', 'supplier', 'Contact', 'B', 'Existence confirmed by webhook categories.'),
 ('Q2', 'CAT-008', 'Xero', 'bank_transaction', 'BankTransactions', 'B', 'Confirmed in official spec (partial).'),
 ('Q2', 'CAT-008', 'Xero', 'payment', 'Payments', 'C', 'Unconfirmed.'),
 ('Q2', 'CAT-008', 'Xero', 'purchase_order', 'PurchaseOrders', 'C', 'Unconfirmed.'),
 ('Q2', 'CAT-008', 'Xero', 'cost_code', 'TrackingCategories', 'C', 'Unconfirmed whether builders use tracking categories as job cost codes.'),
 ('Q3', 'CAT-017', 'CostX', 'estimate', 'Estimates', 'B', 'Entities and fields unconfirmed; REST/OData access named by vendor page.'),
 ('Q3', 'CAT-017', 'CostX', 'material_demand', 'takeoff quantities', 'B', 'Whether quantities carry units and specification detail is unconfirmed.'),
 ('Q5', 'CAT-025', 'Oracle Primavera P6', 'programme_activity', 'activity', 'A', 'Seen in the REST endpoint list; field detail not read.'),
 ('Q5', 'CAT-025', 'Oracle Primavera P6', 'programme_baseline', 'baselineProject', 'A', 'Seen in the endpoint list.'),
 ('Q5', 'CAT-025', 'Oracle Primavera P6', 'working_calendar', 'calendar', 'A', 'Seen in the endpoint list.'),
 ('Q5', 'CAT-026', 'Microsoft Project', 'programme_activity', 'Tasks', 'B', 'MSPDI file schema; desktop installs have no live API (file exchange only).'),
 ('Q5', 'CAT-026', 'Microsoft Project', 'programme_baseline', 'Baseline', 'B', 'From an archived 2007 schema reference; confirm current.'),
 ('Q5', 'CAT-026', 'Microsoft Project', 'working_calendar', 'Calendars', 'B', 'MSPDI file schema.'),
 ('S1', 'CAT-032', 'Xero Payroll (Australia) API', 'timesheet', 'Timesheet', 'B', 'Endpoint existence seen; field detail unconfirmed.'),
 ('S1', 'CAT-032', 'Xero Payroll (Australia) API', 'timesheet_line', 'Timesheet Line', 'B', 'Can carry a tracking item; whether that maps to a job or cost code is unconfirmed.'),
 ('S3', 'CAT-042', 'Consumer Data Right (Open Banking) for business', 'bank_transaction', 'Bank transaction and account data', 'C', 'Representative route may bar serving a business consumer; needs legal confirmation.'),
 ('M', 'CAT-043', 'ABS Data API plus ABS Producer Price Indexes', 'market_observation', 'Producer Price Indexes', 'A', 'Quarterly, national with limited state data; an index, not a price.'),
 ('M', 'CAT-044', 'RBA exchange rates (Statistical Table F11)', 'fx_rate', 'Units of foreign currency per AUD', 'A', 'File download only; reference rate, not a transaction rate.')]
wcsv(f'{OC}/TRANSLATION_PACK_DRAFTS.csv', ['tracker_class', 'catalogue_id', 'system', 'apg_entity', 'vendor_entity_named_in_catalogue', 'evidence_grade', 'status', 'open_question'],
     [[t[0], t[1], t[2], t[3], t[4], t[5], 'draft - unverified', t[6]] for t in TP])
print(len(ML), 'milestones;', len(EDR), 'handoff entries;', len(SR), 'status rows;', len(TP), 'translation rows')
# M4: the milestone, handoff and status tables also carry the M4 rows; they are added by tools/make_m4_registers.py (the same step is applied to the findings and interpretations files by the package build)
import subprocess
_r = subprocess.run([sys.executable, '-I', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'make_m4_registers.py'), OP], capture_output=True, text=True)
if _r.returncode != 0:
    sys.exit('make_m4_registers.py failed: ' + _r.stderr[-500:])
# M5: the same tables also carry the M5 rows (tools/make_m5_registers.py)
_r = subprocess.run([sys.executable, '-I', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'make_m5_registers.py'), OP], capture_output=True, text=True)
if _r.returncode != 0:
    sys.exit('make_m5_registers.py failed: ' + _r.stderr[-500:])
# M6: the same tables also carry the M6 rows (tools/make_m6_registers.py)
_r = subprocess.run([sys.executable, '-I', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'make_m6_registers.py'), OP], capture_output=True, text=True)
if _r.returncode != 0:
    sys.exit('make_m6_registers.py failed: ' + _r.stderr[-500:])
# M6.1: the correction release adds its rows and the Engine #17 governance register (tools/make_m61_registers.py)
_r = subprocess.run([sys.executable, '-I', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'make_m61_registers.py'), OP], capture_output=True, text=True)
if _r.returncode != 0:
    sys.exit('make_m61_registers.py failed: ' + _r.stderr[-500:])
# M6.2: the second correction release adds its rows and the carried-forward register (tools/make_m62_registers.py)
_r = subprocess.run([sys.executable, '-I', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'make_m62_registers.py'), OP], capture_output=True, text=True)
if _r.returncode != 0:
    sys.exit('make_m62_registers.py failed: ' + _r.stderr[-500:])
# M6.3: the third correction release adds its rows (tools/make_m63_registers.py)
_r = subprocess.run([sys.executable, '-I', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'make_m63_registers.py'), OP], capture_output=True, text=True)
if _r.returncode != 0:
    sys.exit('make_m63_registers.py failed: ' + _r.stderr[-500:])
# M6.4: the fourth correction release adds its rows (tools/make_m64_registers.py)
_r = subprocess.run([sys.executable, '-I', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'make_m64_registers.py'), OP], capture_output=True, text=True)
if _r.returncode != 0:
    sys.exit('make_m64_registers.py failed: ' + _r.stderr[-500:])
# M6.5: the fifth correction release adds its rows (tools/make_m65_registers.py)
_r = subprocess.run([sys.executable, '-I', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'make_m65_registers.py'), OP], capture_output=True, text=True)
if _r.returncode != 0:
    sys.exit('make_m65_registers.py failed: ' + _r.stderr[-500:])
# M9.1: the first slice of M9 adds its rows (tools/make_m91_registers.py)
_r = subprocess.run([sys.executable, '-I', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'make_m91_registers.py'), OP], capture_output=True, text=True)
if _r.returncode != 0:
    sys.exit('make_m91_registers.py failed: ' + _r.stderr[-500:])
# M9.2: the correction of the approval request boundary adds its rows (tools/make_m92_registers.py)
_r = subprocess.run([sys.executable, '-I', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'make_m92_registers.py'), OP], capture_output=True, text=True)
if _r.returncode != 0:
    sys.exit('make_m92_registers.py failed: ' + _r.stderr[-500:])
# M9.3: the correction of the session expiry check adds its rows (tools/make_m93_registers.py)
_r = subprocess.run([sys.executable, '-I', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'make_m93_registers.py'), OP], capture_output=True, text=True)
if _r.returncode != 0:
    sys.exit('make_m93_registers.py failed: ' + _r.stderr[-500:])
# M9.4: the correction of the clock failure handling adds its rows (tools/make_m94_registers.py)
_r = subprocess.run([sys.executable, '-I', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'make_m94_registers.py'), OP], capture_output=True, text=True)
if _r.returncode != 0:
    sys.exit('make_m94_registers.py failed: ' + _r.stderr[-500:])
