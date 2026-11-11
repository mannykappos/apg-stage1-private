"""Recommendation inputs: what PEOPLE add to a recommendation before it can be approved.  Blueprint: Section 10 sections 6 (incremental costs, net benefit), 7 (scenario comparison: the nine things
every alternative states), 9 (consequential external actions), 3 (mandatory safety, quality, legal and contractual reviews), PG-RS-AC-05, 06.

One record per recommendation, `rec_input/<rec id>`, kept as revisions: every change is a new revision and the recommendation run pins the revision it read, so a past ranking can be rebuilt
from exactly the inputs it saw.  Two kinds of person write it:
  * the recommendation owner (`set_inputs`): the kind of action, the expected benefit and every incremental cost with its basis, the alternatives, dependencies and risks;
  * a constraint reviewer (`record_review`): a mandatory review (safety, quality, legal, contractual) and its outcome.  A review that does not clear the action blocks it whatever its rank;
    (`record_evidence_assessment`): whether an item of missing information is critical.  Unassessed items count as critical.
Nothing here is computed or guessed: an empty field stays empty and the engine says what it lacks.  A machine or AI actor can write none of it."""
from .. import canon, repro
from ..ports import ConflictError
from . import policy as RP

KIND = 'rec_input'
OWNER = 'recommendation_owner'
REVIEWER = 'constraint_reviewer'
CONSEQUENTIAL_KINDS = ('purchase_order', 'contract', 'claim', 'variation', 'supplier_change', 'material_substitution', 'other_commitment')
OTHER_KINDS = ('internal_review', 'information_request', 'monitoring')
ACTION_KINDS = CONSEQUENTIAL_KINDS + OTHER_KINDS
ALT_FIELDS = ('name', 'baseline_ref', 'proposed_action', 'affected_activities_resources', 'financial_effects_and_timing', 'incremental_costs', 'dependencies_and_approvals',
              'schedule_quality_safety_operations', 'assumptions_uncertainty_gaps', 'invalidating_conditions', 'verification_method')
REVIEW_OUTCOMES = ('cleared', 'not_cleared')


class InputError(ValueError):
    def __init__(self, code, msg=''):
        super().__init__(f'{code}: {msg}')
        self.code = code


def _text(v):
    return isinstance(v, str) and bool(v.strip())


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def check_alternative(a):
    """-> {'name', 'complete', 'missing', 'changes_authoritative_forecast': False, ...the fields}.  An alternative is complete only when every one of the Section 10 section 7 fields is stated."""
    a = a if isinstance(a, dict) else {}
    missing = [k for k in ALT_FIELDS if not _text(a.get(k))]
    out = {k: a.get(k) for k in ALT_FIELDS}
    out.update(name=a.get('name') if _text(a.get('name')) else '(unnamed)', complete=not missing, missing=missing, generated=False, changes_authoritative_forecast=False)
    return out


def _validate(inp):
    bad = []
    ak = inp.get('action_kind')
    if ak is not None and ak not in ACTION_KINDS:
        bad.append('action_kind must be one of ' + ', '.join(ACTION_KINDS))
    eb = inp.get('expected_benefit')
    if eb is not None and not (isinstance(eb, dict) and set(eb) == {'cents', 'basis'} and _int(eb['cents']) and _text(eb['basis'])):
        bad.append('expected_benefit must be {cents (whole number), basis (text)}')
    ic = inp.get('incremental_costs')
    if ic is not None:
        if not isinstance(ic, list) or not ic or any(not (isinstance(c, dict) and set(c) == {'component', 'cents', 'basis'} and _text(c['component']) and _int(c['cents']) and c['cents'] >= 0 and _text(c['basis'])) for c in ic):
            bad.append('incremental_costs must be a non-empty list of {component, cents (0 or more), basis}; a cost of 0 still needs a basis saying why')
        elif len({c['component'] for c in ic}) != len(ic):
            bad.append('incremental_costs lists a component twice')
    alts = inp.get('alternatives', [])
    if not isinstance(alts, list) or any(not isinstance(a, dict) or set(a) - set(ALT_FIELDS) for a in alts):
        bad.append('alternatives must be a list of objects with the Section 10 section 7 fields only')
    elif len({a.get('name') for a in alts}) != len(alts):
        bad.append('two alternatives have the same name')
    for k in ('dependencies', 'risks'):
        v = inp.get(k, [])
        if not isinstance(v, list) or not all(_text(x) for x in v):
            bad.append(k + ' must be a list of texts')
    return bad


def _need(scoped, role, what):
    ctx = scoped.ctx
    if ctx.actor_kind != 'human':
        scoped.log('rec.refused', what, 'refused', reason='a person is required')
        raise InputError('HUMAN_REQUIRED', what + ' must be done by a person')
    if role not in ctx.roles:
        scoped.log('rec.refused', what, 'refused', reason='missing role ' + role)
        raise InputError('ROLE_REQUIRED', f'{what} needs the role {role}')


def get(scoped, rec_id):
    r = scoped.get(KIND, rec_id)
    return None if r is None else canon.deep_copy(r.payload)


def _baseline_ok(scoped, ref):
    """An alternative's reference baseline must name a stored forecast calculation: 'repro_record/<run key>'."""
    if not (isinstance(ref, str) and ref.startswith(repro.KIND + '/')):
        return False
    rec = scoped.get(repro.KIND, ref.split('/', 1)[1])
    return rec is not None and rec.payload.get('formula_id') == 'fin.forecast'


def set_inputs(scoped, clock, rec_id, **fields):
    """The owner writes or replaces the owner fields.  Reviews already recorded are kept; the author and time are recorded; the record is written with the expected revision."""
    what = f'{KIND}/{rec_id}'
    _need(scoped, OWNER, 'writing recommendation inputs')
    allowed = ('action_kind', 'expected_benefit', 'incremental_costs', 'alternatives', 'dependencies', 'risks')
    extra = set(fields) - set(allowed)
    if extra:
        raise InputError('UNKNOWN_FIELD', ', '.join(sorted(extra)))
    cur = scoped.get(KIND, rec_id)
    base = canon.deep_copy(cur.payload) if cur is not None else {'rec_id': rec_id, 'reviews': [], 'history': []}
    for k in allowed:
        if k in fields:
            try:
                base[k] = canon.deep_copy(fields[k])
            except canon.CanonError as e:
                scoped.log('rec.refused', what, 'refused', reason=str(e)[:200])
                raise InputError('INPUT_INVALID', '%s: %s (money is whole cents; no floats)' % (k, e))
    bad = _validate(base)
    if bad:
        scoped.log('rec.refused', what, 'refused', reason='; '.join(bad)[:200])
        raise InputError('INPUT_INVALID', '; '.join(bad))
    for a in base.get('alternatives', []):
        if _text(a.get('baseline_ref')) and not _baseline_ok(scoped, a['baseline_ref']):
            raise InputError('BASELINE_UNKNOWN', 'alternative %r names %r, which is not a stored forecast calculation (repro_record/<run key>)' % (a.get('name'), a['baseline_ref']))
    base['author'] = scoped.ctx.user_id
    base['written_at'] = clock.now()
    base['history'] = list(base.get('history', [])) + [{'event': 'inputs_written', 'by': scoped.ctx.user_id, 'at': clock.now(), 'fields': sorted(k for k in allowed if k in fields)}]
    try:
        rec = scoped.put(KIND, rec_id, base, expected_revision=0 if cur is None else cur.revision)
    except ConflictError:
        raise InputError('CONCURRENT_CHANGE', 'the inputs changed while they were being written; read them again')
    scoped.log('rec.inputs_written', what, 'ok', detail={'fields': sorted(k for k in allowed if k in fields)})
    return canon.deep_copy(rec.payload)


def record_evidence_assessment(scoped, clock, rec_id, item, critical, rationale):
    """A constraint reviewer records whether one item of missing information (named exactly as the finding names it) is critical for acting.  Until an item is assessed as not critical it is
    treated as critical.  The person who wrote the inputs cannot assess them."""
    what = f'{KIND}/{rec_id}'
    _need(scoped, REVIEWER, 'assessing missing evidence')
    if not _text(item) or not isinstance(critical, bool) or not _text(rationale):
        raise InputError('ASSESSMENT_INVALID', 'an assessment names the missing item, says whether it is critical (true or false) and gives a rationale')
    cur = scoped.get(KIND, rec_id)
    base = canon.deep_copy(cur.payload) if cur is not None else {'rec_id': rec_id, 'reviews': [], 'history': []}
    if base.get('author') == scoped.ctx.user_id:
        raise InputError('SELF_REVIEW', 'the person who wrote the recommendation inputs cannot assess them')
    old = [a for a in base.get('evidence_assessments', []) if a['item'] == item]
    base['evidence_assessments'] = [a for a in base.get('evidence_assessments', []) if a['item'] != item] + [{'item': item, 'critical': critical, 'rationale': rationale, 'by': scoped.ctx.user_id, 'at': clock.now()}]
    base['history'] = list(base.get('history', [])) + [{'event': 'evidence_assessed', 'by': scoped.ctx.user_id, 'at': clock.now(), 'item': item, 'critical': critical, 'replaces': old[0] if old else None}]
    try:
        rec = scoped.put(KIND, rec_id, base, expected_revision=0 if cur is None else cur.revision)
    except ConflictError:
        raise InputError('CONCURRENT_CHANGE', 'the inputs changed while the assessment was being recorded; read them again')
    scoped.log('rec.evidence_assessed', what, 'ok', detail={'item': item[:80], 'critical': critical})
    return canon.deep_copy(rec.payload)


def record_review(scoped, clock, rec_id, review_type, outcome, rationale):
    """A mandatory review by a constraint reviewer.  The same type recorded again replaces the earlier one, which stays in the history."""
    what = f'{KIND}/{rec_id}'
    _need(scoped, REVIEWER, 'recording a mandatory review')
    if review_type not in RP.REVIEW_TYPES or outcome not in REVIEW_OUTCOMES or not _text(rationale):
        raise InputError('REVIEW_INVALID', 'a review needs a type (%s), an outcome (%s) and a rationale' % (', '.join(RP.REVIEW_TYPES), ', '.join(REVIEW_OUTCOMES)))
    cur = scoped.get(KIND, rec_id)
    base = canon.deep_copy(cur.payload) if cur is not None else {'rec_id': rec_id, 'reviews': [], 'history': []}
    if base.get('author') == scoped.ctx.user_id:
        raise InputError('SELF_REVIEW', 'the person who wrote the recommendation inputs cannot review them')
    old = [r for r in base['reviews'] if r['type'] == review_type]
    base['reviews'] = [r for r in base['reviews'] if r['type'] != review_type] + [{'type': review_type, 'outcome': outcome, 'rationale': rationale, 'by': scoped.ctx.user_id, 'at': clock.now()}]
    base['history'] = list(base.get('history', [])) + [{'event': 'review_recorded', 'by': scoped.ctx.user_id, 'at': clock.now(), 'type': review_type, 'outcome': outcome, 'replaces': old[0] if old else None}]
    try:
        rec = scoped.put(KIND, rec_id, base, expected_revision=0 if cur is None else cur.revision)
    except ConflictError:
        raise InputError('CONCURRENT_CHANGE', 'the inputs changed while the review was being recorded; read them again')
    scoped.log('rec.review_recorded', what, 'ok', detail={'type': review_type, 'outcome': outcome})
    return canon.deep_copy(rec.payload)
