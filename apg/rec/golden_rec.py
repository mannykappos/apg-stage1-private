"""Golden run for M7 on Builder Zero (Blueprint Section 10; the synthetic builder of builder_zero/).

`run_golden_rec()` runs the REAL pipeline end to end: M3 ingestion, M4, M5 and M6 intake, the stored detection and procurement runs, finding ingestion, then two recommendation runs:
  1. on the findings as detection leaves them (nobody has reviewed anything: every recommendation must be an investigation);
  2. a day later, after a reviewer confirmed the findings, a constraint reviewer assessed the missing information of the cost findings as not critical, and an owner wrote inputs for two
     recommendations (so some lines become actions and one becomes submittable).
It also checks replay of every run, reconstruction of a first version after it changed, and that a second tenant sees none of it.  The demonstration policy values are SYNTHETIC (rec/demo_rec.py).
The independent oracle is in tests/test_rec_golden.py: it recomputes routes, categories and counted totals from the stored payloads with the standard library only."""
import json
from .. import canon, repro
from ..det import findings as FD

AS_OF = '2026-09-30'
PROJECTS = ('PRJ-001', 'PRJ-002', 'PRJ-003')


def summarise(res):
    return {'ranked': [[e['rule_id'], e['subject'], e['route'], e['category']] for e in sorted((e for e in res['recommendations'] if e['rank']), key=lambda e: e['rank'])],
            'routes': {r: sum(1 for e in res['recommendations'] if e['route'] == r) for r in ('action', 'investigate', 'in_hand', 'close')},
            'codes': {e['rule_id'] + '|' + e['subject']: e['eligibility']['codes'] for e in res['recommendations']},
            'totals': {k: {x: v[x] for x in ('recommendations', 'counted', 'potential_gross_counted_cents', 'estimated_net_counted_cents', 'not_counted_overlap', 'unquantified')} for k, v in sorted(res['totals'].items())},
            'excluded': len(res['excluded']), 'policy': res['policy']}


def build_world(root):
    from ..ingest.golden_m3 import _world
    from ..det import detect as D
    from ..mkt import demo_mkt as DM, detect as MD
    clock, prov, store, audit, who = _world()
    s1 = who('t1', 'zero_one', 'ann')
    svc = who('svc1', 'zero_one', 'detsvc', ('detection_service',), 'service')
    o1 = who('o1', 'zero_one', DM.DEMO_OWNER, DM.OWNER_ROLES)                                     # APG-F67: the policies are approved by their owner in person
    _, fv, dv, mv, sv = DM.load_mkt_all(root, s1, clock, 'zero_one', owner=o1)
    dreg, mreg = D.det_registry(), MD.mkt_registry()
    for sc in PROJECTS:
        FD.ingest_run(svc, clock, dreg, D.run_project(s1, dreg, clock, sc, AS_OF, fv, dv)['run_key'])
        FD.ingest_run(svc, clock, mreg, MD.run_project(s1, mreg, clock, sc, AS_OF, fv, dv, mv, sv)['run_key'])
    FD.ingest_run(svc, clock, dreg, D.run_tenant(s1, dreg, clock, AS_OF, dv)['run_key'])
    FD.ingest_run(svc, clock, mreg, MD.run_tenant(s1, mreg, clock, AS_OF, fv, dv, mv, sv, list(PROJECTS))['run_key'])
    return clock, prov, store, audit, who, s1, fv


def run_golden_rec(root, keep=False):
    from . import demo_rec as DR, engine as E, inputs as IN, lifecycle as L, policy as RP
    clock, prov, store, audit, who, s1, fv = build_world(root)
    rsvc = who('rsvc', 'zero_one', 'recsvc', (L.SERVICE,), 'service')
    rev = who('rev', 'zero_one', 'rita', (FD.REVIEWER,))
    owner = who('own', 'zero_one', 'olly', (IN.OWNER,))
    owner2 = who('own2', 'zero_one', 'opal', (IN.OWNER,))
    crev = who('crev', 'zero_one', 'cora', (IN.REVIEWER,))
    prop = who('pprop', 'zero_one', 'paula', ())
    pown = who('pown', 'zero_one', 'quentin', (RP.POLICY_ROLE,))
    pol = DR.demo_rec_policy(proposer='paula')
    RP.store_policy(prop, pol)
    pol = RP.approve_policy(pown, clock, pol['version'], 'golden run: the synthetic demonstration policy approved by its owner')
    reg = E.registry()
    G = {'findings': len(FD.all_findings(s1))}
    r1 = E.run(s1, reg, clock, AS_OF, pol['version'])
    G['first'] = summarise(r1['result'])
    G['first_all_investigate'] = all(e['route'] == 'investigate' for e in r1['result']['recommendations'])
    L.ingest_run(rsvc, clock, reg, r1['run_key'])
    clock.advance(86400)
    for f in sorted(FD.all_findings(s1), key=lambda f: f['finding_id']):
        if f['status'] == 'detected':
            FD.transition(rev, clock, f['finding_id'], 'under_review')
            FD.transition(rev, clock, f['finding_id'], 'confirmed', rationale='golden run: reviewed against the source records')
    for f in sorted(FD.all_findings(s1), key=lambda f: f['finding_id']):
        if f['signal']['taxonomy']['family'] == 'cost_commitments':
            for item in f['signal']['confidence']['missing_information']:
                IN.record_evidence_assessment(crev, clock, E.rec_id_of(f['finding_id']), item, False, 'golden run: not needed to act on a cost overrun')
    cost = sorted((f for f in FD.all_findings(s1) if f['signal']['taxonomy']['family'] == 'cost_commitments' and f['signal']['confidence']['evidence_strength'] != 'weak'
                   and f['signal']['quantification']['status'] == 'quantified'), key=lambda f: f['finding_id'])
    picked = [E.rec_id_of(f['finding_id']) for f in cost[:2]]
    from ..fin import calc_records as FC
    base = FC.run_calc(s1, FC.fin_registry(), clock, 'fin.forecast', cost[0]['scope']['project'], AS_OF, fv, {'forecast_version': 'F-2026-09'})
    G['baseline_forecast_state'] = base['result']['state']
    alt = {'name': 'golden run: review the cost code with the site team', 'baseline_ref': repro.KIND + '/' + base['run_key'], 'proposed_action': 'quantity surveyor review of the cost code',
           'affected_activities_resources': 'the cost code named by the finding', 'financial_effects_and_timing': 'avoid further overrun from October', 'incremental_costs': 'one day of review',
           'dependencies_and_approvals': 'project manager approval', 'schedule_quality_safety_operations': 'none expected', 'assumptions_uncertainty_gaps': 'synthetic golden-run values',
           'invalidating_conditions': 'the overrun is explained by an approved change', 'verification_method': 'compare the next forecast with the adopted one'}
    for i, rid in enumerate(picked):
        IN.set_inputs(owner, clock, rid, action_kind='internal_review', expected_benefit={'cents': 100000, 'basis': 'golden run: owner estimate'},
                      incremental_costs=[{'component': 'quantity surveyor review', 'cents': 40000, 'basis': 'golden run: one day'}], alternatives=[alt] if i == 0 else [])
    r2 = E.run(s1, reg, clock, '2026-10-01', pol['version'])
    G['second'] = summarise(r2['result'])
    s2 = L.ingest_run(rsvc, clock, reg, r2['run_key'])
    G['second_ingest'] = {k: len(v) for k, v in s2.items() if isinstance(v, list)}
    sub = []
    for rid in picked:
        e = [x for x in r2['result']['recommendations'] if x['rec_id'] == rid][0]
        try:
            L.submit(owner2, clock, rid)
            sub.append([rid, 'submitted'])
        except L.RecError as x:
            sub.append([rid, x.code, e['constraints']['blocked_by']])
    G['submissions'] = sub
    G['replay'] = [repro.replay(s1, reg, r['run_key']).ok for r in (r1, r2)]
    changed = [rid for rid in picked if L.get(s1, rid)['version'] > 1]
    G['reconstruct_first_version'] = [[rid, L.reconstruct(s1, reg, rid, 1)['matches_recorded_digest']] for rid in changed]
    other = who('t2', 'zero_two', 'bob', (L.SERVICE,), 'service')
    G['tenant_isolation'] = {'zero_two_recommendations': len(L.all_recs(other)), 'zero_two_sees_run': other.get(repro.KIND, r2['run_key']) is not None}
    G['audit_chain_ok'] = audit.verify(s1.ctx).ok
    G['run_keys'] = [r1['run_key'], r2['run_key']]
    return (G, s1) if keep else G


def dumps(g):
    """The golden file leaves out the run keys: a run key includes the hash of the code that ran, so it changes whenever any recommendation module changes, while the answers may not."""
    return json.dumps(canon.deep_copy({k: v for k, v in g.items() if k != 'run_keys'}), indent=1, sort_keys=True, ensure_ascii=True) + '\n'
