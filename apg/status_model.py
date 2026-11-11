"""The evidence ladder as enforced code.  Blueprint: Section 17 sections 2 and 3.

  Specified < Implemented < Local-tested < Integration-tested < Staging-verified < Operationally verified < Accepted < Closed
  plus Blocked and Failed.

"A state may only advance when its prerequisites and evidence are present.  No label, report, CI status or manual assertion may silently
promote a blocked, skipped, mock-only or failed requirement to passed, accepted or closed."  This module is that sentence as code.

State objects are immutable.  advance() returns a NEW state or raises StatusError with a code; nothing is changed in place."""
import re
from dataclasses import dataclass, field, replace

LADDER = ('Specified', 'Implemented', 'Local-tested', 'Integration-tested', 'Staging-verified', 'Operationally verified', 'Accepted', 'Closed')
BLOCKED, FAILED = 'Blocked', 'Failed'
_SHA = re.compile(r'[0-9a-f]{64}')
LOCAL_ENVS = ('local', 'isolated')
NON_PASS = ('fail', 'skipped', 'skip', 'blocked', 'not_run')


class StatusError(ValueError):
    def __init__(self, code, msg=''):
        super().__init__(f'{code}: {msg}')
        self.code = code


@dataclass(frozen=True)
class Evidence:
    kind: str                 # approval | implementation | test_run | integration_run | staging_run | operational | review | closure | block | resolve
    ref: str                  # where the evidence lives (file path, log id, report id)
    requirement_ids: tuple    # evidence counts only for the requirements it names
    build: str                # revision / build identifier the evidence is about
    environment: str          # local | isolated | integration | staging | target | n/a
    result: str               # pass | fail | skipped | blocked | not_run
    actor: str
    actor_kind: str           # human | ai | service
    role: str = ''
    mock_only: bool = False
    tests: tuple = ()
    components: tuple = ()
    integrity_hash: str = ''  # SHA-256 (hex) of the evidence artefact
    reason: str = ''          # block reason / residual limitations / closure rationale
    next_action: str = ''


@dataclass(frozen=True)
class RequirementState:
    requirement_id: str
    status: str = ''                      # '' = not yet specified
    build: str = ''
    builder: str = ''
    required_level: str = 'Staging-verified'
    mandatory_tests: tuple = ()
    last_good: str = ''
    blocked_reason: str = ''
    evidence: tuple = ()
    history: tuple = ()
    stale_note: str = ''


def new_requirement(requirement_id, required_level='Staging-verified', mandatory_tests=()):
    if required_level not in LADDER[2:6]:
        raise StatusError('LEVEL', 'required_level must be Local-tested, Integration-tested, Staging-verified or Operationally verified')
    return RequirementState(requirement_id, required_level=required_level, mandatory_tests=tuple(mandatory_tests))


def rank(status):
    return LADDER.index(status) if status in LADDER else -1


def _basic(ev, st):
    if st.requirement_id not in ev.requirement_ids:
        raise StatusError('EVIDENCE_NOT_FOR_REQUIREMENT', f'{ev.ref} does not name {st.requirement_id}')
    if ev.result in NON_PASS or ev.result != 'pass':
        raise StatusError('EVIDENCE_NOT_PASSING', f'{ev.ref}: result {ev.result!r}')
    if not ev.ref or not ev.actor:
        raise StatusError('EVIDENCE_INCOMPLETE', 'evidence needs a ref and an actor')
    if ev.actor_kind not in ('human', 'ai', 'service'):
        raise StatusError('EVIDENCE_INCOMPLETE', 'actor_kind')


def _run_checks(ev, st, kinds, envs, allow_mock):
    _basic(ev, st)
    if ev.kind != kinds:
        raise StatusError('WRONG_EVIDENCE_KIND', f'needs {kinds}, got {ev.kind}')
    if ev.environment not in envs:
        raise StatusError('WRONG_ENVIRONMENT', f'needs one of {envs}, got {ev.environment}')
    if ev.mock_only and not allow_mock:
        raise StatusError('MOCK_ONLY', 'mock-only evidence cannot support this status')
    if not _SHA.fullmatch(ev.integrity_hash or ''):
        raise StatusError('NO_INTEGRITY_HASH', 'evidence needs a SHA-256 of the artefact')
    if not st.build or ev.build != st.build:
        raise StatusError('STALE_OR_DIFFERENT_BUILD', f'evidence is for build {ev.build!r}, requirement is at {st.build!r}')
    if not ev.tests:
        raise StatusError('NO_TESTS_NAMED', 'a test run must name the tests it ran')


def advance(st, target, ev):
    """-> new RequirementState.  One rung at a time; evidence must fit the rung."""
    if st.status in (BLOCKED, FAILED):
        raise StatusError('NOT_ADVANCEABLE', f'state is {st.status}; resolve it first')
    if target not in LADDER:
        raise StatusError('UNKNOWN_STATUS', target)
    nxt = LADDER[0] if st.status == '' else (LADDER[rank(st.status) + 1] if rank(st.status) + 1 < len(LADDER) else None)
    if target == 'Accepted' and st.status in LADDER[:6]:
        # Operational evidence is required only where it is APPLICABLE (Section 17 section 2).  Rungs up to the requirement's required level are mandatory;
        # rungs above it may be left out, so acceptance can follow the required level directly.
        if rank(st.status) < rank(st.required_level):
            raise StatusError('BELOW_REQUIRED_LEVEL', f'needs at least {st.required_level} before acceptance, is {st.status or "unspecified"}')
    elif target != nxt:
        raise StatusError('SKIPPED_RUNG', f'from {st.status or "nothing"} the next status is {nxt}, not {target}')
    builder, build = st.builder, st.build
    if target == 'Specified':
        _basic(ev, st)
        if ev.kind != 'approval' or ev.actor_kind != 'human' or ev.role not in ('product_owner', 'spec_approver'):
            raise StatusError('NOT_APPROVED', 'Specified needs a human approval by the product owner or spec approver')
    elif target == 'Implemented':
        _basic(ev, st)
        if ev.kind != 'implementation' or not ev.build:
            raise StatusError('NO_IMPLEMENTATION', 'Implemented needs an implementation record with a build/revision')
        builder, build = ev.actor, ev.build
    elif target == 'Local-tested':
        _run_checks(ev, st, 'test_run', LOCAL_ENVS, True)
    elif target == 'Integration-tested':
        _run_checks(ev, st, 'integration_run', ('integration',), False)
        if not ev.components:
            raise StatusError('NO_COMPONENTS', 'integration evidence must name the integrated components')
    elif target == 'Staging-verified':
        _run_checks(ev, st, 'staging_run', ('staging',), False)
    elif target == 'Operationally verified':
        _run_checks(ev, st, 'operational', ('target',), False)
    elif target == 'Accepted':
        _basic(ev, st)
        if ev.kind != 'review' or ev.actor_kind != 'human' or ev.role != 'authorised_reviewer':
            raise StatusError('NOT_AUTHORISED', 'Accepted needs a human authorised reviewer')
        if ev.actor == st.builder:
            raise StatusError('SELF_ACCEPTANCE', 'the builder cannot accept their own work')
        if ev.build != st.build:
            raise StatusError('STALE_OR_DIFFERENT_BUILD', 'review is for a different build')
    elif target == 'Closed':
        _basic(ev, st)
        if ev.kind != 'closure' or ev.actor_kind != 'human' or ev.role != 'closure_authority' or not ev.reason:
            raise StatusError('NOT_AUTHORISED', 'Closed needs a human closure authority and a recorded rationale')
        if ev.build != st.build:
            raise StatusError('STALE_OR_DIFFERENT_BUILD', 'closure is for a different build')
        seen = set()
        for e in st.evidence:
            if e.build == st.build and e.result == 'pass' and e.kind in ('test_run', 'integration_run', 'staging_run', 'operational'):
                seen.update(e.tests)
        missing = [t for t in st.mandatory_tests if t not in seen]
        if missing:
            raise StatusError('MANDATORY_TEST_MISSING', ','.join(missing))
        kinds = {e.kind for e in st.evidence if e.build == st.build and e.result == 'pass'}
        need = {'test_run': 2, 'integration_run': 3, 'staging_run': 4, 'operational': 5}
        for k, r in need.items():
            if rank(st.required_level) >= r and k not in kinds:
                raise StatusError('GATE_MISSING', f'{k} evidence for this build is required before closure')
    return replace(st, status=target, build=build, builder=builder, evidence=st.evidence + (ev,), history=st.history + ((st.status, target, ev.ref),), last_good=target, stale_note='')


def record_failure(st, ev):
    """Verification ran and did not satisfy the criteria -> Failed.  The last good status is remembered; moving on needs new passing evidence."""
    if st.requirement_id not in ev.requirement_ids or ev.result != 'fail':
        raise StatusError('NOT_A_FAILURE_RECORD', 'failure evidence must name the requirement and have result fail')
    return replace(st, status=FAILED, last_good=st.last_good or st.status, evidence=st.evidence + (ev,), history=st.history + ((st.status, FAILED, ev.ref),))


def block(st, reason, next_action):
    if not reason or not next_action:
        raise StatusError('BLOCK_NEEDS_REASON_AND_NEXT_ACTION')
    return replace(st, status=BLOCKED, last_good=st.last_good or st.status, blocked_reason=reason, history=st.history + ((st.status, BLOCKED, reason),))


def recover(st, ev):
    """Leave Blocked or Failed: needs passing evidence for the SAME requirement at the current build; returns to the last good status, never above it."""
    if st.status not in (BLOCKED, FAILED):
        raise StatusError('NOT_BLOCKED_OR_FAILED')
    _basic(ev, st)
    if ev.build != st.build or not _SHA.fullmatch(ev.integrity_hash or ''):
        raise StatusError('STALE_OR_DIFFERENT_BUILD', 'recovery evidence must be for the current build and carry a hash')
    return replace(st, status=st.last_good, blocked_reason='', evidence=st.evidence + (ev,), history=st.history + ((st.status, st.last_good, ev.ref),))


def change_build(st, new_build, implementer):
    """The implementation changed.  Earlier evidence belongs to the old build, so the requirement falls back to Implemented."""
    if st.status == '' or rank(st.status) < rank('Implemented'):
        raise StatusError('NOT_IMPLEMENTED_YET')
    if new_build == st.build:
        return st
    return replace(st, status='Implemented', build=new_build, builder=implementer, last_good='Implemented', stale_note=f'evidence for build {st.build} no longer applies',
                   history=st.history + ((st.status, 'Implemented', f'build changed to {new_build}'),))


def supported_status(requirement_id, evidence_list, required_level='Staging-verified', mandatory_tests=()):
    """Replay a list of (target, Evidence) from scratch.  -> (final RequirementState, first error or None).  Use it to check a claimed status."""
    st = new_requirement(requirement_id, required_level, mandatory_tests)
    for target, ev in evidence_list:
        try:
            st = advance(st, target, ev)
        except StatusError as e:
            return st, e
    return st, None
