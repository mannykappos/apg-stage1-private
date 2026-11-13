s=open('register_rev41.py').read()
def rep(o,n):
    global s
    assert s.count(o)==1,o[:70]; s=s.replace(o,n)
rep("links to related findings sharing a cause or exposure (the overlap marker), the calculation run behind its amount'",
    "links to related findings sharing a cause or exposure (the overlap marker), the calculation run behind its amount; explanation (observed condition, expected condition, reason); financial interpretation (actual loss, forecast exposure, opportunity, data-quality risk, non-financial risk); severity, urgency and confidence held separately; reviewer and next review date; a deduplication identity and its update history (a repeat updates the finding, S06 s9.1); the basis of each claim (evidence, inference, hypothesis, unverified) and suspected or confirmed causes and links; the late or missed marker'")
rep("approval needed, dependencies, verification method, lifecycle (proposed to superseded or invalidated)'",
    "approval needed, dependencies, verification method, decision deadline, the result of the eligibility checks before ranking, constraints (applying, addressed, unresolved), lifecycle with the S10 s9 states (recommendation generated, awaiting evidence, awaiting approval, approved, rejected, deferred, in progress, completed pending verification, verified outcome, closed without implementation) and blocked, referred, withdrawn, superseded and invalidated'")
rep("the action, its dependencies, invalidating conditions, verification method and reversibility'",
    "the action, its dependencies, invalidating conditions, verification method and reversibility; the activities and resources it affects; the approvals it requires'")
rep("comparable or not, the attributes compared, who decided'",
    "its class (the five S08 s5 classes), the attributes compared, the documented adjustments, whether a ranking based on it is definitive or indicative, who decided'")
rep("estimated against realised and the reasons; proof of a realised saving'",
    "estimated against realised and the reasons; offsetting and hidden costs; the net realised result; verified by and when; proof of a realised saving'")
rep("the savings-baseline contents (S10 s9, S13)'",
    "for a savings baseline (S05 s10.1, S13 s13.6): its scope, period, quantities, unit costs, conditions, source records, approval and the adjustments allowed'")
rep("integration status: last success, failures, sync state; market coverage",
    "owner and escalation contact; the duplicate, retry, back-off, dead-letter and replay policy; integration status: last success, failures and their class, the retry schedule, missing coverage, required intervention, sync state; market coverage")
rep("field class (source-owned, derived, human-approved, provisional)'",
    "field class (source-owned, derived, human-approved, provisional); the rule for revisions, cancellations, late records and corrections; conflict outcomes and the role allowed to resolve them (S04 s5)'")
rep("duplicate decision, outcome, processing state; per-record lines'",
    "duplicate decision, outcome, processing state, retry and replay history, final disposition; per-record lines'")
rep("unresolved ambiguity, verified by and on, confirmed or corrected'",
    "unresolved ambiguity, the evidence considered, verified by and on, disposition (confirmed, corrected or rejected)'")
rep("the posted journal reference'", "the posted journal reference; the value status \"risk-adjusted\" (S05)'")
rep("responsible role, the assumptions behind a generated deadline'",
    "responsible role, the required action or review, the last verification date, the assumptions behind a generated deadline'")
rep("what was approved or overridden, rationale where given, scope and expiry'",
    "what was approved or overridden, the risks considered, the resulting state, override eligibility, the reason (required for an override, S15 s15.11; optional for dismissing a finding, owner record item 18), scope, expiry and later review'")
rep("trigger, idempotency key, attempts, state, outcome, external reference, time'",
    "trigger, payload reference, idempotency key, correlation id, attempts, state, failure class, next retry, outcome, external reference, time; for a dead-lettered item its owner, replay and closure'")
rep("post-incident review, corrective actions'", "post-incident review, the recovery check, residual limitations, corrective actions each with an owner and due date'")
rep("service and component state, release and its version, restore test and its result, time'",
    "service and component state and the functions affected; a release: version, contents, approval, deployment time and rollback; a restore test: scope, backup used, time to restore, integrity checked, result; time'")
rep("moved between projects), quantity and unit,", "moved between projects), stock ownership, quantity and unit,")
rep("dated inflows and outflows, their source records, qualification, calculation run'",
    "dated inflows and outflows, their source records, assumptions, uncertainty, known gaps, source freshness, qualification, calculation run'")
rep("(renamed \"Plant and equipment use (hired or owned)\")'",
    "(renamed \"Plant and equipment use (hired or owned)\"): ownership (hired or owned) and, for owned plant, the internal cost rate used for hire-versus-own comparisons'")
rep("'classification (S13 s13.4), operational impact,", "'classification (S13 s13.4), installation method, programme activity link, design detail, interface and specification references, operational impact,")
i=s.index("('R41-28',"); j=s.index("]", i)
s=s[:i]+"('R41-28', 'data-sharing and aggregation permissions (eligibility, permitted fields, de-identification, limits); identity and access are E113 (class P)', 'B-B21')"+s[j:]
rep(" 'E09': [('R41-36', 'assumptions and unresolved questions', 'C-G-VAR')],",
    " 'E09': [('R41-36', 'assumptions and unresolved questions; overlap status (whether its value is already counted elsewhere, S05 s7)', 'C-G-VAR, B-B15')],\n 'E13': [('R41-54', 'quantity and rate per claimed item, against the contract\\'s rate or quantity items (E08)', 'C-G-CLM')],\n 'E16': [('R41-55', 'defects liability period', 'part A row S03 L0163')],")
s=s.rstrip(); assert s.endswith(']'); s=s[:-1]
s+="""('E113', 'Common', 'Identity and access (users, service identities, roles, permissions, sessions)', 'P', 'S15 s15.3, s15.4; S14 s14.4', PLAT + 'identity type (human, integration, service, automated), identity status and dates, credentials where APG supports them (never their values), MFA requirement and enrolment, sessions and their expiry and revocation, project-scoped and resource-scoped access grants, permission sets (read, create, update, approve, export, administer), time-bounded privileged access', 'partly: users and roles named on E05', 'no identity and access record', '-', 'S, A', 'S proposed; A proposed', 'Anchor platform; builder admin', 'E05, E102', 'R41-56', 'D-G-IAM'),
]
NOTES = ['E102 (class P) also carries the financial-state transitions of APG itself (claims, certification, collection, retention release, security return; S12, S14 s14.4): discovery confirms that the platform audit log can hold the before and after business state with its evidence; if it cannot, that history is an APG record.']
"""
open('register_rev41.py','w').write(s); print('ok')
