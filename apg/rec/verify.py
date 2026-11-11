"""The realised-benefit verification gate.  Blueprint: Section 05 section 10.1 (a benefit may be reported as realised net profit improvement only after (a) an approved, versioned baseline is
established, (b) implementation evidence exists and (c) an authorised verification step confirms the outcome against the baseline, including relevant offsetting or hidden costs; a negotiated price,
quote, approved recommendation or forecast alone is not a realised saving), Section 10 section 10 (outcome verification, variance against expectations), PG-RS-AC-10, PG-PC-AC-13.

`verify` is the ONLY way a recommendation reaches `verified_outcome`.  It refuses unless all of these hold:
  * the recommendation is `completed_pending_verification` (approved, started and completed with named implementation evidence that still exists at the revision named);
  * the verifier is a person with the role benefit_verifier who did not write the inputs, submit, approve, start or complete it;
  * the baseline is a stored forecast calculation (fin.forecast) that replays cleanly and that a forecast owner adopted (or explicitly promoted) in a forecast slot - an approved, versioned
    baseline in the M4 sense - before the action was started;
  * every offsetting cost component the policy lists is addressed: an amount with its basis, or 'not applicable' with the reason (a component left out is a refusal, never a zero).
The realised figure is then computed by the reproducible formula `rec.realised` over the pinned verification record, the baseline record and the implementation evidence records:
realised net = observed benefit - the offsetting costs, with the variance against the net benefit that was approved.  It may be negative: a verified outcome can show that the benefit was not
realised.  The baseline and the verification are records of PEOPLE's statements; this gate makes them complete, attributable and reproducible, it does not measure the site."""
from .. import canon, repro
from ..fin import calc_records as FC, forecast_book as FB
from . import lifecycle as L

VKIND = 'rec_verification'
FORMULA_ID, FORMULA_VERSION = 'rec.realised', 1


class VerifyError(ValueError):
    def __init__(self, code, msg=''):
        super().__init__(f'{code}: {msg}')
        self.code = code


def _text(v):
    return isinstance(v, str) and bool(v.strip())


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def realised(inputs, params):
    """The formula.  inputs: the verification record, the baseline record and the evidence records, as pinned.  params: {'verification': key}."""
    v = inputs[VKIND + '/' + params['verification']]
    offsets = v['offsets']
    total = sum(o['cents'] for o in offsets.values() if 'cents' in o)
    net = v['observed_benefit_cents'] - total
    exp = v['expected_net_cents']
    return {'rec_id': v['rec_id'], 'observed_benefit_cents': v['observed_benefit_cents'], 'offsetting_costs_cents': total, 'realised_net_cents': net,
            'expected_net_cents': exp, 'variance_cents': None if exp is None else net - exp, 'baseline': v['baseline'], 'evidence': v['evidence'],
            'offsets': canon.deep_copy(offsets), 'label': 'verified realised net benefit (Section 05 section 10.1 gate)' if net > 0 else 'verified: no realised net benefit',
            'verified_by': v['by'], 'verified_at': v['at']}


def registry(reg=None):
    reg = reg or repro.FormulaRegistry()
    reg.register(FORMULA_ID, FORMULA_VERSION, realised)
    return reg


def _baseline(scoped, fin_reg, run_key, started_at):
    """-> the slot entry that adopted the baseline, or raise."""
    rec = scoped.get(repro.KIND, run_key)
    if rec is None or rec.payload.get('formula_id') != 'fin.forecast':
        raise VerifyError('BASELINE_NOT_A_FORECAST', 'the baseline must be a stored forecast calculation (fin.forecast)')
    chk = FC.check_record(scoped, fin_reg, run_key)
    if not chk['replay'].ok or not chk['figure_valid'] or not chk['pins_consistent']:
        raise VerifyError('BASELINE_DOES_NOT_REPRODUCE', chk['replay'].code or 'figure or pins')
    p = rec.payload['params']
    slot = scoped.get(FB.SLOT_KIND, FB.slot_key(p.get('project'), p.get('as_of')))
    hist = [h for h in (slot.payload['history'] if slot is not None else []) if h['run_key'] == run_key and h['event'] in ('adopted', 'promoted_scenario')]
    if not hist:
        raise VerifyError('BASELINE_NOT_APPROVED', 'the baseline was never adopted by a forecast owner; an unadopted calculation is not an approved baseline')
    if not (hist[0]['at'] <= started_at):
        raise VerifyError('BASELINE_AFTER_START', 'the baseline was adopted on %s, after the action started on %s; a baseline must be set before the change it measures' % (hist[0]['at'], started_at))
    return hist[0], rec


def verify(scoped, clock, rec_reg, fin_reg, rid, baseline_run_key, observed_benefit_cents, offsets, rationale, policy):
    """-> the recommendation record, now `verified_outcome`, with the stored outcome.  `offsets`: {component: {'cents', 'basis'} | {'not_applicable': reason}}; `policy`: the recommendation policy payload."""
    ctx = scoped.ctx
    what = f'{L.KIND}/{rid}'
    if ctx.actor_kind != 'human':
        scoped.log('rec.refused', what, 'refused', reason='verification is a person\'s act')
        raise VerifyError('HUMAN_REQUIRED', 'verification must be done by a person')
    if L.VERIFIER not in ctx.roles:
        scoped.log('rec.refused', what, 'refused', reason='missing role ' + L.VERIFIER)
        raise VerifyError('ROLE_REQUIRED', 'verification needs the role ' + L.VERIFIER)
    rec = scoped.get(L.KIND, rid)
    if rec is None:
        raise VerifyError('RECOMMENDATION_UNKNOWN', rid)
    r = canon.deep_copy(rec.payload)
    if r['status'] != 'completed_pending_verification':
        scoped.log('rec.refused', what, 'refused', reason='not completed')
        raise VerifyError('NOT_COMPLETED', 'only a completed recommendation can be verified (it is %s)' % r['status'])
    impl, appr, sub = r.get('implementation') or {}, r.get('approval') or {}, r.get('submission') or {}
    involved = {x for x in (r['current'].get('inputs_author'), sub.get('by'), appr.get('by'), impl.get('started_by'), impl.get('completed_by')) if x}
    if ctx.user_id in involved:
        scoped.log('rec.refused', what, 'refused', reason='the verifier took part in the recommendation')
        raise VerifyError('VERIFIER_NOT_INDEPENDENT', 'the verifier must not have written, submitted, approved, started or completed this recommendation')
    if not _text(rationale):
        raise VerifyError('RATIONALE_REQUIRED', 'record how the outcome was verified')
    if not _int(observed_benefit_cents):
        raise VerifyError('OBSERVED_REQUIRED', 'the observed benefit is a whole number of cents (it may be zero or negative)')
    comps = ((policy or {}).get('verification') or {}).get('offset_components')
    if not comps:
        raise VerifyError('VERIFICATION_NOT_CONFIGURED', 'the policy lists no offsetting cost components; a verification cannot be judged complete')
    if not isinstance(offsets, dict):
        raise VerifyError('OFFSETS_REQUIRED', 'address every offsetting cost component')
    miss = [c for c in comps if c not in offsets]
    bad = [c for c, o in offsets.items() if not (isinstance(o, dict) and ((set(o) == {'cents', 'basis'} and _int(o['cents']) and o['cents'] >= 0 and _text(o['basis'])) or (set(o) == {'not_applicable'} and _text(o['not_applicable']))))]
    if miss or bad:
        scoped.log('rec.refused', what, 'refused', reason='offsetting costs not addressed')
        raise VerifyError('OFFSETS_NOT_ADDRESSED', 'missing: %s; malformed: %s (each component needs an amount and basis, or not_applicable with a reason)' % (', '.join(miss) or 'none', ', '.join(bad) or 'none'))
    ev = impl.get('evidence_refs') or []
    for kind, key, rev, h in ev:
        x = scoped.get(kind, key, rev)
        if x is None or x.payload_hash != h:
            raise VerifyError('IMPLEMENTATION_EVIDENCE_CHANGED', f'{kind}/{key} r{rev} is no longer the record that was named')
    if not ev:
        raise VerifyError('IMPLEMENTATION_EVIDENCE_REQUIRED', 'no implementation evidence on record')
    adopted, brec = _baseline(scoped, fin_reg, baseline_run_key, impl.get('started_at') or '')
    n = len([x for x in scoped.query(VKIND) if x.payload['rec_id'] == rid])
    vkey = f'{rid}|{n + 1}'
    v = {'rec_id': rid, 'version': r['version'], 'by': ctx.user_id, 'at': clock.now(), 'rationale': rationale, 'observed_benefit_cents': observed_benefit_cents, 'offsets': canon.deep_copy(offsets),
         'expected_net_cents': appr.get('expected', {}).get('net_benefit_cents'), 'baseline': {'run_key': baseline_run_key, 'adopted_by': adopted['by'], 'adopted_at': adopted['at']},
         'evidence': [[k, key, rev] for k, key, rev, _ in ev]}
    scoped.put(VKIND, vkey, v, expected_revision=0)
    refs = [repro.pin_latest(scoped, VKIND, vkey), repro.InputRef(repro.KIND, baseline_run_key, brec.revision, brec.payload_hash)]
    refs += [repro.InputRef(k, key, rev, h) for k, key, rev, h in ev if (k, key) != (repro.KIND, baseline_run_key)]
    out = repro.run(scoped, rec_reg, clock, FORMULA_ID, FORMULA_VERSION, refs, {'verification': vkey})
    rec = scoped.get(L.KIND, rid)
    r = canon.deep_copy(rec.payload)
    if r['status'] != 'completed_pending_verification':
        raise VerifyError('CONCURRENT_CHANGE', 'the recommendation changed during verification')
    r['outcome'] = {'verification': vkey, 'run_key': out['run_key'], 'result': out['result']}
    r['status'] = 'verified_outcome'
    L._event(r, scoped, clock, 'status_change', 'completed_pending_verification', 'verified_outcome', {'run_key': out['run_key'], 'realised_net_cents': out['result']['realised_net_cents'],
                                                                                                    'variance_cents': out['result']['variance_cents'], 'rationale': rationale})
    L._put(scoped, rec, r)
    scoped.log('rec.verified', what, 'ok', detail={'realised_net_cents': out['result']['realised_net_cents']})
    return r
