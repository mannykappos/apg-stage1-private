# APG approval request boundary (APG-M9.1, first slice of M9; carried-forward item CF-25, gate CF-22; revised for APG-M9.2, APG-M9.3 and APG-M9.4)

Status: builder-implemented and locally tested; no independent review has taken place. This describes logic in `apg/api/approval_boundary.py` that an approval screen or an API would call. No screen, API, HTTP layer, session store, role directory or project permission model exists in this package. The suggested mapping in section 7 is for the Engine's author to accept or replace; it is not an API specification that anyone has approved. Blueprint references (locked Sections 00 to 18, unchanged): Section 15 sections 15.4 (authorisation), 15.5 (tenant isolation), 15.8 (audit), 15.11 (approval workflows).

## 1. What it is for

`findings.approve_action` is the lifecycle's own entry point. It already refuses an approval that does not name the finding version, the evidence digest and the proposal reference the approver was shown (F-52, F-53, F-54, F-55, F-56, F-57). A screen or an API needs more around it, and the earlier audits (CF-22, CF-25) said so: a request that is safe to repeat, an approver who is authorised for the finding's project, no leakage between tenants or projects, and an audit event for every outcome. The boundary is that "more", as logic only.

## 2. The three calls

All three take a tenant-scoped store (`scoped`, which carries the verified context), the project-action port, and the clock. None raises for a bad request; each returns a plain dictionary.

| Call | Who | What it does |
|---|---|---|
| `present(scoped, port, clock, finding_id)` | a person who may view the finding | Returns what an approval screen shows: the finding's status and version, its scope, the proposal (text, proposer, time), whether this person can approve now (`can_approve`), and the token to hand back. The token is given only to a caller who can approve the finding now: the proposal is current and not yet approved, the caller has the approver role and is not the proposer, and the port allows `approve` in the finding's project (F-58, I-88). A caller who may only view still sees the proposal and the status, with `can_approve: false` and no token. |
| `request_approval(scoped, port, clock, request)` | a person with the approver role who may approve in the finding's project | Approves the proposed action of one finding, once. |
| `check_for_execution(scoped, port, clock, finding_id, version, digest, proposal)` | whoever carries the action out, outside APG | Returns `{'valid': bool, 'code': ...}`: is the approval still in force for exactly this version, evidence digest and proposal? |

### The request

Exactly these six fields, and no other (an unknown field is refused; a tenant or an approver named in the request is a claim, never a choice):

| Field | Rule |
|---|---|
| `request_id` | text of 1 to 128 ASCII characters from `A-Z a-z 0-9 . _ : -` and nothing else (a final newline, a space or a non-ASCII digit makes the request malformed; the whole string is matched, F-60, I-91); chosen by the caller, one per intended approval |
| `finding_id` | the same rule |
| `version` | whole number of at least 1 (not a boolean), from the token that was shown |
| `digest` | non-empty text of at most 128 characters, from the token |
| `proposal` | non-empty text of at most 128 characters, from the token |
| `rationale` | non-empty text of at most 2000 characters; kept in the finding's own history, never copied to the boundary's audit events |

The size limits are bounds on input, not policy values (I-81).

## 3. The order of checks in `request_approval`

1. The request is checked for shape. A bad request is refused (`REQUEST_MALFORMED`) before anything is looked at.
2. The caller must be a person (`HUMAN_REQUIRED`), with a session that has not expired (`SESSION_EXPIRED`), holding the approver role (`ROLE_REQUIRED`).
   A session has not expired only if its expiry is a **real UTC moment** written exactly `YYYY-MM-DDTHH:MM:SSZ` in ASCII digits (month 1 to 12, a day the month has in that year with 29 February only in a Gregorian leap year, hour 0 to 23, minute and second 0 to 59, year 0001 to 9999; a leap second, a zone offset, fractional seconds and any other shape are refused) and is **strictly later** than the present time, which must itself be a real moment in the same format; if the clock does not give one, no session is live. `2999-99-99T99:99:99Z` has the right shape and is not a moment (F-62, I-93 to I-95).
   **A clock or an expiry that cannot be read ends the session (F-63).** If `clock.now()` raises an ordinary exception, is missing or is not callable, or if the context's expiry (or its actor kind) cannot be read, the call does not raise: it gives its ordinary refusal (`present`: `NOT_ALLOWED`; `request_approval`: `SESSION_EXPIRED`, or `HUMAN_REQUIRED` for a kind that cannot be read; `check_for_execution`: `{'valid': False, 'code': 'NOT_ALLOWED'}`), no approval is made and nothing is stored, and the refusal is audited best-effort with a reason that says the clock gave no usable time. No new code was added. An interrupt (`KeyboardInterrupt`, `SystemExit`) is not caught. The clock is read **once** per call; the lifecycle then uses that one reading as the time of the call, so a clock that fails on a later read cannot stop an approval half way, and the session check and the approval's timestamps are the same instant. The session issuer, the seal and the clock are the Engine's.
3. The finding is looked up in the caller's own tenant, and the project-action port is asked whether this person may `approve` in the finding's project (or at tenant level for a tenant-level finding). An unknown finding, a finding of another tenant and a finding the person may not approve all get the same answer, `NOT_FOUND` (I-83). The port is asked on every request, replays included.
4. The request id is looked up. The same id with the same content from the same person returns the first answer (section 4). The same id with different content, or from another person, is refused (`REQUEST_ID_REUSED`).
5. The lifecycle is called (`approve_action`), which applies its own checks (`SELF_APPROVAL`, `APPROVAL_TOKEN_REQUIRED`, `STALE_APPROVAL`, `STALE_PROPOSAL`, `PROPOSAL_CHANGED`, `TRANSITION_NOT_ALLOWED` and the rest). Its refusals become the answer to the request id too.
6. The final answer is noted under the request id and audited.

## 4. One answer per request id

- A first request opens a record of kind `approval_request` (keyed by a digest of the request id, in the caller's tenant), then calls the lifecycle, then audits an approval, then records the final answer. The approval's audit entry is written BEFORE the answer is noted (I-89): if it cannot be written the call raises, the approval exists, the request stays pending, and the same request sent again recognises the approval from the finding's history and writes the entry. The audit of an approval is therefore at least once; a crash between the entry and the note can leave two entries for one approval (the second says it was recovered). Exactly-once needs a transaction across the state change and the log, which is the Engine's (EDR-32, CF-29).
- Sending the same request again returns the first answer with `replayed: true` and does nothing a second time. The replay is audited (`approval_request.replayed`).
- A replay is the first answer, not the finding's present state. If the evidence has changed since, the approval has ended, and only `check_for_execution` says whether an approval is in force (I-84).
- A refusal that happens before a request record is opened (steps 1 to 3) is not stored under the id and is not replayed; it is audited each time (I-85).
- `CONCURRENT_CHANGE` (the finding changed while the request was being processed, or two copies of the same request met while the record was being opened) is not a final answer: the result carries `retry: true` and the same request may be sent again. Both are audited as `approval_request.refused` with the code in the detail (F-59, I-90).
- If two copies of the same request meet while one is writing its answer, the first answer noted under the request id is the answer to the request id: the other copy returns that answer with `replayed: true` (audited as `approval_request.replayed`) whatever it found itself.
- A request that stopped half way (a crash between the approval and the note of it) is recognised on the next try from the finding's own history, and the person is not approved twice. The approval is credited to the request only if the history, after the request was opened, shows this person approving exactly this version, digest and proposal (I-87).

## 5. Results and codes

Every result carries `status` (`approved`, `refused` or, for `present`, `shown`), `code`, `message`, `request_id`, `finding_id`, and `finding_status` / `finding_version` when a finding was found. An approval also carries `approved_by`, `approved_at`, `approved_version`, `approved_digest`, `approved_proposal` and `recovered`. Every answer to `request_approval` carries `replayed`.

| Code | Meaning |
|---|---|
| `OK` | approved, or shown |
| `REQUEST_MALFORMED` | the request is not exactly the six fields in the right form |
| `HUMAN_REQUIRED`, `SESSION_EXPIRED`, `ROLE_REQUIRED` | the caller is not a person, the session has ended, or the approver role is missing |
| `NOT_FOUND` | no such finding for this caller (unknown, another tenant, or not permitted in its project) |
| `REQUEST_ID_REUSED` | the id was used for different content or by another person |
| `REQUEST_UNREADABLE` | the request record could not be read |
| `CONCURRENT_CHANGE` | retry the same request |
| `SELF_APPROVAL`, `APPROVAL_TOKEN_REQUIRED`, `STALE_APPROVAL`, `STALE_PROPOSAL`, `PROPOSAL_CHANGED`, `TRANSITION_NOT_ALLOWED`, ... | the lifecycle's own refusals, unchanged from M6.5 |
| `TENANT_MISMATCH` | a payload named another tenant |
| `NOT_ALLOWED`, `NOT_IN_FORCE` | from `present` and `check_for_execution` |

## 6. Audit (Section 15.8)

Every call writes one event to the tenant's audit log: `approval_request.accepted`, `.refused`, `.replayed`, `.viewed` or `.execution_check`, with the request id, the finding id and the code. No event carries the rationale text. The lifecycle writes its own event for the approval itself (`finding.transition`) whatever the boundary does. This includes a malformed or expired call of `check_for_execution` (F-61, I-92) and the `CONCURRENT_CHANGE` outcome (F-59). A refusal for a context that no longer verifies cannot be written to the tenant's log; the refusal stands, and no event exists to claim (F-63: the same holds when the clock failed and the log write fails too). Refusals are logged on a best-effort basis (a failure to log a refusal is not raised: the refusal is the answer); a success is logged without that protection, so an approval, a screen or a valid execution check that cannot be audited is not given. A session that was revoked in the Engine's session store no longer verifies, so the finding cannot be looked up for it: `request_approval` and `present` answer `NOT_FOUND` (the same answer as for an unknown finding), `check_for_execution` answers `valid: false` with `NOT_FOUND`, nothing is stored or changed, and the refusal is not logged if the tenant's log cannot be reached.

## 7. Suggested mapping for the Engine's author (to accept or replace)

| Call | Suggested route |
|---|---|
| `present` | `GET /findings/{id}/approval` |
| `request_approval` | `POST /findings/{id}/approval-requests` with the six fields; `request_id` could also be an idempotency header |
| `check_for_execution` | `GET /findings/{id}/approval/check?version=&digest=&proposal=` |

Suggested statuses: approved 200 (a replay also 200, marked replayed); `REQUEST_MALFORMED` 400; `SESSION_EXPIRED` 401; `HUMAN_REQUIRED`, `ROLE_REQUIRED`, `SELF_APPROVAL` 403; `NOT_FOUND` 404; `CONCURRENT_CHANGE`, `STALE_APPROVAL`, `STALE_PROPOSAL`, `PROPOSAL_CHANGED`, `REQUEST_ID_REUSED`, `TRANSITION_NOT_ALLOWED` 409.

## 8. What the Engine must provide (handoff register)

| Need | Register entry |
|---|---|
| Per-action project permission: `allows(ctx, scope, action)` with the 14-case contract `tools/run_m91_contracts.py` | EDR-31 (new); the sibling of EDR-29 (the list of visible projects) |
| API hosting, authentication, rate limiting, mapping of the results above | EDR-11 |
| Record kinds writable only through the control functions; the kind `approval_request` should be one of them | EDR-20 |
| Persistence of `approval_request` records with atomic write and revision checks (the reference store supplies this in tests) | EDR-02 (delivered earlier) |

## 9. What this does not show

- No screen, no API, no HTTP, no session, no role directory exists here, and nothing executes an action.
- The project permission model is not decided. A reference port (a test double, not a permission model) stands in for it; the contract suite shows the port's required behaviour, not that any real implementation meets it.
- Any holder of the approver role in a tenant could approve in every project of it until the Engine's port exists (CF-25 as written in M6.4 stays open).
- Rate limiting, abuse protection of the request-id space, clock trust and the Engine's own transport security are the Engine's. The boundary fails closed when a clock cannot be read or says nothing usable; it cannot tell a wrong but well-formed time from the right one. The other attributes of the context (tenant, user, roles, session id, seal) are the Engine's sealed context and are read without protection; a context that raises when those are read is not handled here.
- If the audit log cannot be written after an approval was recorded, the lifecycle's own event still exists and the call raises; the retry writes the boundary's `accepted` event (section 4). Until it is retried the boundary's entry is missing. A reconciliation for approvals whose request was never retried (the caller gave up) is the Engine's (EDR-32).
- A request id can be probed by an authorised approver: sending an id that someone else used for a different finding the sender may approve gives `REQUEST_ID_REUSED`. Request ids are not secrets.
- Nothing here has been independently reviewed. CF-22 and CF-25 stay open; F-52 to F-57 stay open until independently verified.
