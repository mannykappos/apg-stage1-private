"""APG-M10 view model: what each prototype screen shows, read from the existing APG code run on Builder Zero (synthetic data only).

Rules this module keeps (and tests_m10 checks):
  * It computes no amount.  Every amount is a value returned by an APG calculation (apg.fin.calc_records.run_calc), a stored source record, a finding's quantification, a
    recommendation run or a procurement scenario, carried with its state ('authoritative', 'provisional', 'cannot_assess') or its label ('record', 'estimate', 'figure',
    'scenario'), and with the id of an evidence entry that says where it came from.  A figure that cannot be assessed has no value, never a zero.
  * Nothing is totalled across projects or across financial interpretations: APG has no portfolio-level financial figure (interpretation I-145), and the detection
    portfolio view is per interpretation (apg/det/portfolio.py).
  * What a person sees is decided by the project-action port of the M9 contract (apg/api/approval_boundary.ProjectActionPort, EDR-31): a project is shown only if the port
    answers exactly True to 'view' for it, and tenant-level material (tenant findings, data health, imports, portfolio procurement) only if it answers True at tenant level.
    The approvals screen is the real `present()` answer for that person; the prototype sends no approval (I-146).
  * No estimate is presented as a realised saving: realised amounts exist only after apg.rec.verify, which this prototype never calls.
The demonstration workflow (a reviewer confirming findings, an owner proposing actions, one approval by the director) is scripted with synthetic people, as the golden runs
of M7 do (apg/rec/golden_rec.py); it is demonstration state, not a recorded decision (I-149).  The figures come from the file-import route (M3), where every APG engine runs;
the connected-systems route (AUIF rev14, M8) is shown on the data-health screen with its own gate answer (I-147).
Usage: build_views(root) -> {'meta': ..., 'views': {view id: view}}; dumps(model) -> canonical JSON text."""
import json
from apg import canon
from apg.api import approval_boundary as AB
from apg.det import demo_det as DD, detect as D, findings as FD, portfolio as PF
from apg.fin import calc_records as C, figure as FG
from apg.ingest import freshness as FR, views as IV
from apg.ingest.golden_m3 import _world
from apg.mkt import demo_mkt as DM, detect as MD
from apg.rec import demo_rec as DR, engine as E, inputs as IN, lifecycle as L, policy as RP
from . import plain as PL

AS_OF = '2026-09-30'
TENANT = '*tenant*'
DIRECTOR_ROLES = (FD.APPROVER, 'director')
PERSONAS = (
    dict(view='zero_one-director', tenant='zero_one', user='dana', name='Dana (director)', roles=DIRECTOR_ROLES, builder='Builder Zero One',
         grants={'PRJ-001': ('view', 'approve'), 'PRJ-002': ('view', 'approve'), 'PRJ-003': ('view', 'approve'), TENANT: ('view', 'approve')}),
    dict(view='zero_two-director', tenant='zero_two', user='drew', name='Drew (director)', roles=DIRECTOR_ROLES, builder='Builder Zero Two',
         grants={'PRJ-001': ('view', 'approve'), TENANT: ('view', 'approve')}),
    dict(view='zero_one-project-manager', tenant='zero_one', user='pat', name='Pat (project manager, PRJ-001 only)', roles=(), builder='Builder Zero One',
         grants={'PRJ-001': ('view',)}),
)
STATEMENT = ('Prototype over synthetic Builder Zero data. Not a production screen, not an API, no login and no live system. Every amount is what the existing APG code '
             'returned; the policies and thresholds behind it are illustrative and the construction definitions are PROPOSED. Estimates are never realised savings.')
FIGURES = (('secured_revenue', 'Secured revenue', 'fin.revenue', None), ('recognised_margin', 'Recognised margin', 'fin.recognised_margin', None),
           ('forecast_final_margin', 'Forecast final margin', 'fin.forecast', None), ('cash_adjusted_margin', 'Cash-position-adjusted margin', 'fin.cash_adjusted', None),
           ('actual_cost', 'Actual cost to date', 'fin.actual_cost', None), ('commitments', 'Open commitments', 'fin.commitments', None),
           ('retention_withheld', 'Retention withheld', 'fin.cash_position', {'what': 'retention'}),
           ('security', 'Security held (face value)', 'fin.cash_position', {'what': 'security'}),
           ('retention_carrying', 'Retention carrying cost', 'fin.cash_position', {'what': 'retention_carrying'}))


class Grants(AB.ProjectActionPort):
    """The prototype's stand-in for the Engine's ProjectActionPort (EDR-31): fixed synthetic grants per (tenant, user, project or tenant level)."""
    def __init__(self, grants):
        self.g = {k: tuple(v) for k, v in grants.items()}

    def allows(self, ctx, scope, action):
        where = scope.get('project') if scope.get('level') == 'project' else TENANT
        return action in self.g.get((ctx.tenant_id, ctx.user_id, where), ())


def _payload(rec):
    return canon.deep_copy(rec.payload) if rec is not None else None


# ---------------------------------------------------------------- the worlds -----------------------------------------------------------------------------

def build_world(root, tenant):
    """One tenant's APG world on the file-import route, with the detection and (zero_one) procurement runs ingested, as golden_rec.build_world does."""
    clock, prov, store, audit, who = _world()
    s = who('t-' + tenant, tenant, 'ann')
    svc = who('svc-' + tenant, tenant, 'detsvc', (FD.SERVICE,), 'service')
    owner = who('o-' + tenant, tenant, DM.DEMO_OWNER, DM.OWNER_ROLES)
    if tenant == 'zero_one':
        receipts, fv, dv, mv, sv = DM.load_mkt_all(root, s, clock, tenant, owner=owner)
    else:
        receipts, fv, dv = DD.load_zero_all(root, s, clock, tenant, owner=owner)
        mv = sv = None
    projects = sorted(r.key for r in s.query('project'))
    dreg, mreg = D.det_registry(), MD.mkt_registry()
    for p in projects:
        FD.ingest_run(svc, clock, dreg, D.run_project(s, dreg, clock, p, AS_OF, fv, dv)['run_key'])
        if mv:
            FD.ingest_run(svc, clock, mreg, MD.run_project(s, mreg, clock, p, AS_OF, fv, dv, mv, sv)['run_key'])
    dt = D.run_tenant(s, dreg, clock, AS_OF, dv)
    FD.ingest_run(svc, clock, dreg, dt['run_key'])
    mt = None
    if mv:
        mt = MD.run_tenant(s, mreg, clock, AS_OF, fv, dv, mv, sv, projects)
        FD.ingest_run(svc, clock, mreg, mt['run_key'])
    return dict(det_policy=dt['result'].get('det_policy'), mkt_policy=(mt or {}).get('result', {}).get('mkt_policy'), tenant=tenant, clock=clock, store=store, audit=audit, who=who, s=s, svc=svc, receipts=receipts, fv=fv, dv=dv, mv=mv, sv=sv, projects=projects, workflow=[])


def run_workflow(W):
    """The scripted demonstration state (synthetic people, I-149): the recommendation policy proposed and approved, a first recommendation run; a day later a reviewer
    confirms the detected findings, a constraint reviewer assesses the missing information of the cost findings, an owner writes inputs for two cost recommendations and
    proposes actions on those two and on one PRJ-001 finding; the director approves one of them through the approval boundary; then a second recommendation run."""
    clock, who, s, t = W['clock'], W['who'], W['s'], W['tenant']
    log = W['workflow']
    rsvc = who('rsvc-' + t, t, 'recsvc', (L.SERVICE,), 'service')
    pol = DR.demo_rec_policy(proposer='paula')
    RP.store_policy(who('pprop-' + t, t, 'paula', ()), pol)
    pol = RP.approve_policy(who('pown-' + t, t, 'quentin', (RP.POLICY_ROLE,)), clock, pol['version'], 'prototype demonstration: the synthetic recommendation policy approved by its owner')
    W['rv'] = pol['version']
    reg = E.registry()
    r1 = E.run(s, reg, clock, AS_OF, pol['version'])
    L.ingest_run(rsvc, clock, reg, r1['run_key'])
    log.append({'who': 'quentin (policy owner)', 'what': 'approved the illustrative recommendation policy %s' % pol['version']})
    if t != 'zero_one':
        W['rec_run'] = r1
        log.append({'who': 'recsvc (service)', 'what': 'ran the recommendations once; nobody has reviewed a finding of this builder'})
        return
    clock.advance(86400)
    rev = who('rev-' + t, t, 'rita', (FD.REVIEWER,))
    for f in sorted(FD.all_findings(s), key=lambda f: f['finding_id']):
        if f['status'] == 'detected':
            FD.transition(rev, clock, f['finding_id'], 'under_review')
            FD.transition(rev, clock, f['finding_id'], 'confirmed', rationale='prototype demonstration: reviewed against the source records')
    log.append({'who': 'rita (reviewer)', 'what': 'confirmed every detected finding after review'})
    crev = who('crev-' + t, t, 'cora', (IN.REVIEWER,))
    for f in sorted(FD.all_findings(s), key=lambda f: f['finding_id']):
        if f['signal']['taxonomy']['family'] == 'cost_commitments':
            for item in f['signal']['confidence']['missing_information']:
                IN.record_evidence_assessment(crev, clock, E.rec_id_of(f['finding_id']), item, False, 'prototype demonstration: not needed to act on a cost overrun')
    log.append({'who': 'cora (constraint reviewer)', 'what': 'assessed the missing information of the cost findings as not critical'})
    cost = sorted((f for f in FD.all_findings(s) if f['signal']['taxonomy']['family'] == 'cost_commitments' and f['signal']['confidence']['evidence_strength'] != 'weak'
                   and f['signal']['quantification']['status'] == 'quantified'), key=lambda f: f['finding_id'])
    picked = cost[:2]
    rowner = who('own-' + t, t, 'olly', (IN.OWNER,))
    for f in picked:
        IN.set_inputs(rowner, clock, E.rec_id_of(f['finding_id']), action_kind='internal_review',
                      expected_benefit={'cents': 100000, 'basis': 'prototype demonstration: owner estimate'},
                      incremental_costs=[{'component': 'quantity surveyor review', 'cents': 40000, 'basis': 'prototype demonstration: one day'}])
    log.append({'who': 'olly (recommendation owner)', 'what': 'entered an estimated benefit and cost for two cost recommendations'})
    fowner = who('fown-' + t, t, 'oscar', (FD.OWNER,))
    prj1 = sorted((f for f in FD.all_findings(s) if f['scope'].get('project') == 'PRJ-001' and f['status'] == 'confirmed'
                   and f['signal']['quantification']['status'] == 'quantified' and f['finding_id'] not in {x['finding_id'] for x in picked}), key=lambda f: f['finding_id'])[:1]
    proposals = picked + prj1
    for f in proposals:
        text = 'review %s with the person responsible and record the outcome' % f['signal'].get('subject')
        FD.transition(fowner, clock, f['finding_id'], 'action_proposed', action_text=text)
    log.append({'who': 'oscar (finding owner)', 'what': 'proposed actions on %d findings' % len(proposals)})
    dana = who('dana-' + t, t, 'dana', DIRECTOR_ROLES)
    port = Grants({(t, 'dana', k): v for k, v in PERSONAS[0]['grants'].items()})
    first = proposals[0]['finding_id']
    shown = AB.present(dana, port, clock, first)
    tok = shown['token']
    req = {'request_id': 'PROTO-APPROVAL-1', 'finding_id': first, 'version': tok['version'], 'digest': tok['digest'], 'proposal': tok['proposal'],
           'rationale': 'prototype demonstration: approved by the synthetic director'}
    W['approval_result'] = AB.request_approval(dana, port, clock, req)
    log.append({'who': 'dana (director)', 'what': 'approved one proposed action through the approval boundary (%s)' % W['approval_result']['code']})
    W['proposals'] = [f['finding_id'] for f in proposals]
    r2 = E.run(s, reg, clock, AS_OF, pol['version'])
    L.ingest_run(rsvc, clock, reg, r2['run_key'])
    W['rec_run'] = r2
    log.append({'who': 'recsvc (service)', 'what': 'ran the recommendations again after the reviews'})


def auif_route(root, tenant):
    """The connected-systems route: Builder Zero imported through AUIF rev14 into a fresh world, and the M8 gate's answer.  Only the gate's answer is kept."""
    from apg_auif import dependency
    dependency.ensure()
    from apg_auif import client, gate
    from apg.ingest import demo_setup as DS, reconcile as R3
    from apg.fin import demo_fin as DF
    clock, prov, store, audit, who = _world()
    s = who('a-' + tenant, tenant, 'ann')
    owner = who('ao-' + tenant, tenant, DD.DEMO_OWNER, DD.OWNER_ROLES)
    env, plan = client.builder_zero(root, tenant, s, clock, ('m3', 'fin', 'det'), None)
    summaries = []
    for iid, ent, f in plan:
        r = env.import_entity(tenant, iid, ent)
        summaries.append({'integration': iid, 'record_type': ent, 'file': f, 'status': r.get('status'), 'reasons': [PL.reason(c) | {'detail': str(d)[:200]} for c, d in r.get('reasons', [])]})
    R3.reconcile(s, DS.demo_register(), AS_OF)
    DF.install(s, clock, owner)
    DD.install_det(s, clock, owner)
    st = gate.assessment_status(s, env.bindings[tenant].expected(), env.module)
    return {'status': st['status'], 'reasons': [PL.reason(r['code']) | {'scope': r['scope'], 'detail': r['detail']} for r in st['reasons']], 'imports': summaries}


# ---------------------------------------------------------------- one person's view ---------------------------------------------------------------------

class Evidence:
    def __init__(self):
        self.items = {}

    def add(self, eid, entry):
        if eid not in self.items:
            self.items[eid] = entry
        return eid


def num(cents=None, state=None, label=None, ev=None, bps=None):
    """One amount on a screen.  cents None means there is no value (cannot assess or not quantified), never zero."""
    out = {'cents': cents, 'ev': ev}
    if state is not None:
        out['state'] = state
    if label is not None:
        out['label'] = label
    if bps is not None:
        out['bps'] = bps
    return out


def _explain(fig):
    x = FG.explain(fig)
    return x.splitlines() if isinstance(x, str) else list(x)


def _calc_evidence(EV, eid, title, rec, fig):
    return EV.add(eid, {'type': 'calculation', 'title': title, 'formula': rec.get('formula_id'), 'formula_version': rec.get('formula_version'), 'run_key': rec['run_key'],
                        'as_of': AS_OF, 'figure': fig.get('name'), 'state': fig['state'], 'cents': (fig.get('value') or {}).get('cents'),
                        'reasons': [PL.reason(r) for r in fig.get('reasons', [])], 'limits': fig.get('limits', []), 'policy': fig.get('policy'),
                        'explain': _explain(fig), 'inputs_pinned': len(rec.get('inputs', [])),
                        'inputs_sample': [{'kind': i['kind'], 'key': i['key'], 'revision': i['revision']} for i in rec.get('inputs', [])[:12]],
                        'contributed': sorted(fig.get('contributed', []), key=lambda c: -abs(c.get('amount_cents') or 0))[:10],
                        'excluded': fig.get('excluded', []), 'unknown_inputs': fig.get('unknown_inputs', [])})


def _record_evidence(EV, s, ref, role=None, revision=None):
    kind, key = ref.split('/', 1)
    r = s.get(kind, key)
    p = _payload(r)
    fields = (p or {}).get('fields', p) if isinstance(p, dict) else p
    return EV.add('E-rec-' + ref, {'type': 'record', 'title': ref, 'ref': ref, 'role': role, 'revision': revision if revision is not None else (r.revision if r else None),
                                   'found': r is not None, 'fields': fields if isinstance(fields, dict) else {},
                                   'source_file': ((p or {}).get('provenance') or {}).get('file_name') if isinstance(p, dict) else None,
                                   'outcome': ((p or {}).get('intrinsic') or {}).get('outcome') if isinstance(p, dict) else None})


def _project_figures(W, EV, p):
    s, clock, reg = W['s'], W['clock'], C.fin_registry()
    rec = s.get('project', p)
    pf = _payload(rec)['fields']
    out = {'id': p, 'name': pf.get('project_name'), 'start': pf.get('start_date'), 'planned_finish': pf.get('planned_finish'),
           'contract_value': num(pf.get('contract_value_cents'), 'authoritative', 'record', _record_evidence(EV, s, 'project/' + p, 'project')), 'figures': {}}
    for key, title, fid, extra in FIGURES:
        r = C.run_calc(s, reg, clock, fid, p, AS_OF, W['fv'], extra)
        fig = r['result']
        ev = _calc_evidence(EV, 'E-fig-%s-%s' % (p, key), '%s, %s' % (title, p), r, fig)
        out['figures'][key] = dict(num((fig.get('value') or {}).get('cents'), fig['state'], 'figure', ev), title=title,
                                   reasons=[PL.reason(x) for x in fig.get('reasons', [])], policy_seen=fig.get('policy'))
        if key == 'forecast_final_margin':
            ctc = (fig.get('components') or {}).get('cost_to_complete')
            if ctc:
                ev2 = EV.add('E-fig-%s-cost_to_complete' % p, {'type': 'calculation', 'title': 'Cost to complete, %s (a component of the forecast)' % p, 'formula': r.get('formula_id'),
                                                               'run_key': r['run_key'], 'as_of': AS_OF, 'figure': ctc.get('name'), 'state': ctc['state'],
                                                               'cents': (ctc.get('value') or {}).get('cents'), 'reasons': [PL.reason(x) for x in ctc.get('reasons', [])],
                                                               'explain': _explain(ctc), 'unknown_inputs': ctc.get('unknown_inputs', []), 'excluded': ctc.get('excluded', []),
                                                               'by_cost_code': (fig.get('classified') or {}).get('ctc_by_code')})
                out['figures']['cost_to_complete'] = dict(num((ctc.get('value') or {}).get('cents'), ctc['state'], 'figure', ev2), title='Cost to complete',
                                                          reasons=[PL.reason(x) for x in ctc.get('reasons', [])])
        if key == 'recognised_margin':
            out['percent_complete_bps'] = (fig.get('classified') or {}).get('percent_complete_bps')
    return out


def _finding(W, EV, f):
    s = W['s']
    sig = f['signal']
    q = sig['quantification']
    evs = [_record_evidence(EV, s, e['ref'], e.get('role'), e.get('revision')) for e in sig.get('evidence', [])]
    fev = EV.add('E-fnd-' + f['finding_id'], {'type': 'finding', 'title': '%s on %s' % (f['rule_id'], sig.get('subject')), 'finding_id': f['finding_id'], 'rule': f['rule_id'],
                                                'status': f['status'], 'version': f['version'], 'state_digest': sig.get('state_digest'), 'explanation': sig.get('explanation'),
                                                'quantification': q, 'confidence': sig.get('confidence'), 'data_limits': sig.get('data_limits', []), 'records': evs,
                                                'history': [{'at': h['at'], 'actor': h['actor'], 'event': h['event'], 'to': h.get('to')} for h in f.get('history', [])]})
    amount = num(q.get('gross_cents'), None, q.get('label'), fev) if q.get('status') == 'quantified' else num(None, None, 'none', fev)
    return {'id': f['finding_id'], 'rule': f['rule_id'], 'subject': sig.get('subject'), 'kind': PL.kind(sig['taxonomy'].get('subtype')), 'subtype': sig['taxonomy'].get('subtype'), 'family': sig['taxonomy'].get('family'),
            'project': f['scope'].get('project'), 'level': f['scope']['level'], 'status': f['status'], 'version': f['version'], 'interpretation': sig.get('interpretation'),
            'amount': amount, 'quantified': q.get('status') == 'quantified', 'amount_basis': q.get('basis'), 'severity': (sig.get('priority') or {}).get('severity'),
            'evidence_strength': (sig.get('confidence') or {}).get('evidence_strength'), 'observed': (sig.get('explanation') or {}).get('observed'),
            'expected': (sig.get('explanation') or {}).get('expected'), 'why': (sig.get('explanation') or {}).get('reason'),
            'missing_information': (sig.get('confidence') or {}).get('missing_information', []), 'records': evs, 'ev': fev}


def _recommendation(EV, e):
    d = e['dimensions']
    mag, net = d.get('magnitude') or {}, d.get('net_benefit') or {}
    ev = EV.add('E-reco-' + e['rec_id'], {'type': 'recommendation', 'title': 'Recommendation %s' % e['rec_id'], 'rec_id': e['rec_id'], 'finding_id': e['finding_id'],
                                           'route': e['route'], 'category': e.get('category'), 'eligibility': e.get('eligibility'), 'magnitude': mag, 'net_benefit': net,
                                           'expected_benefit': d.get('expected_benefit'), 'implementation_cost': d.get('implementation_cost'),
                                           'explanation': e.get('explanation'), 'constraints': e.get('constraints'), 'overlap': e.get('overlap')})
    return {'id': e['rec_id'], 'finding_id': e['finding_id'], 'route': e['route'], 'category': e.get('category'), 'rank': e.get('rank'),
            'codes': [PL.reason(c) for c in (e.get('eligibility') or {}).get('codes', [])],
            'potential_gross': num(mag.get('cents'), None, mag.get('label') or 'none', ev) if mag.get('cents') is not None else num(None, None, 'none', ev),
            'estimated_net': num(net.get('cents'), None, 'estimate', ev) if net.get('status') == 'estimated' else num(None, None, 'none', ev),
            'net_status': net.get('status'), 'approval_role': (e.get('constraints') or {}).get('approval_role'),
            'blocked_by': (e.get('constraints') or {}).get('blocked_by', []), 'what': (e.get('explanation') or {}).get('what_and_why_now'),
            'not_a_claim': (e.get('explanation') or {}).get('not_a_claim'), 'counted_in_totals': (e.get('overlap') or {}).get('counted_in_totals'), 'ev': ev}


def _materials(W, EV, p):
    if not W['mv']:
        return None
    s = W['s']
    res = MD.run_project(s, MD.mkt_registry(), W['clock'], p, AS_OF, W['fv'], W['dv'], W['mv'], W['sv'])
    r = res['result']
    out = []
    for req_id, a in sorted(r['analyses'].get('requirements', {}).items()):
        rq = a.get('requirement') or {}
        rk = a.get('ranking') or {}
        sc = a.get('scenarios') or {}
        mrec = s.get('material', rq.get('material') or '-')
        item = {'requirement': req_id, 'material': rq.get('material'), 'material_name': (_payload(mrec) or {}).get('fields', {}).get('description_text') if mrec else None, 'kind': rq.get('kind'), 'required_date': rq.get('required_date'), 'unit': rq.get('unit'),
                'ranking_status': 'definitive' if rk.get('definitive') else 'not definitive', 'excluded': [{'offer': x.get('offer'), 'class': x.get('class'), 'why': x.get('why', [])}
                                                                                                         for x in rk.get('excluded', [])],
                'offers': [], 'scenario_status': sc.get('status') if sc else None, 'scenarios': [], 'context': (sc or {}).get('context'),
                'outstanding': (sc or {}).get('outstanding', []), 'note': (sc or {}).get('note'), 'changes_authoritative_forecast': (sc or {}).get('changes_authoritative_forecast')}
        for o in rk.get('offers', []):
            g = o.get('gate') or {}
            off = o.get('offer')
            item['offers'].append({'offer': off.get('ref') if isinstance(off, dict) else off, 'supplier': off.get('supplier') if isinstance(off, dict) else None,
                                   'specification': off.get('specification_text') if isinstance(off, dict) else None, 'class': g.get('class'), 'blockers': [PL.reason(b) for b in o.get('blockers', [])],
                                   'freshness': [{'subject': x.get('subject'), 'state': x.get('state'), 'age_days': x.get('age_days'), 'threshold_days': x.get('threshold_days'),
                                                  'valid_until': x.get('valid_until')} for x in o.get('freshness', [])],
                                   'landed_complete': (o.get('landed') or {}).get('complete'), 'reasons': g.get('reasons', [])})
        for x in (sc or {}).get('scenarios', []):
            name = x.get('scenario') if ':' in x.get('scenario', '') or not x.get('price_path') else x['scenario'] + ':' + x['price_path']['name']
            eid = 'E-scn-%s-%s-%s-%s' % (p, req_id, x.get('offer') or '-', name)
            ev = EV.add(eid, {'type': 'scenario', 'title': 'Scenario %s for %s (%s)' % (name, req_id, x.get('offer') or 'no single offer'), 'run_key': res['run_key'],
                              'scenario': x, 'statement': r.get('statement')})
            item['scenarios'].append({'offer': x.get('offer'), 'scenario': name, 'status': x.get('status'),
                                      'landed_total': num(x.get('landed_total_cents'), None, 'scenario', ev) if x.get('landed_total_cents') is not None else None,
                                      'incremental_total': num(x.get('incremental_total_cents'), None, 'scenario', ev) if x.get('incremental_total_cents') is not None else None,
                                      'potential_difference': [num(o.get('potential_difference_cents'), None, 'estimate', ev) for o in x.get('others', [])
                                                               if o.get('potential_difference_cents') is not None],
                                      'offer_class': x.get('offer_class'), 'evidence_gaps': x.get('evidence_gaps', []), 'why': x.get('why'),
                                      'uncertainty': x.get('uncertainty', []), 'blockers': [PL.reason(b) for b in x.get('offer_blockers', [])], 'ev': ev,
                                      'changes_authoritative_forecast': x.get('changes_authoritative_forecast')})
        out.append(item)
    return {'run_key': res['run_key'], 'statement': r.get('statement'), 'requirements': out}


def _data_health(W, EV, auif):
    s = W['s']
    rc = {}
    for name, r in sorted(W['receipts'].items()):
        ev = EV.add('E-imp-' + name, {'type': 'import', 'title': 'Import receipt, %s' % name, 'file': name, 'entity': r.get('entity'), 'source': r.get('source'),
                                      'status': r.get('status'), 'file_sha256': r.get('file_sha256'), 'received_at': r.get('received_at'), 'counts': r.get('counts'),
                                      'not_accepted': [x for x in r.get('results', []) if x.get('result') not in ('new', 'accepted')][:25]})
        c = r.get('counts') or {}
        rc[name] = {'file': name, 'entity': r.get('entity'), 'source': r.get('source'), 'status': r.get('status'), 'ev': ev,
                    'rows': num(c.get('rows'), None, 'count', ev), 'new': num(c.get('new'), None, 'count', ev), 'duplicate': num(c.get('duplicate'), None, 'count', ev),
                    'revision': num(c.get('revision'), None, 'count', ev), 'rejected': num(c.get('rejected'), None, 'count', ev),
                    'held_at_intake': num(c.get('held_at_intake'), None, 'count', ev), 'conflict': num(c.get('conflict'), None, 'count', ev)}
    sources = []
    for src, x in FR.source_status(s, AS_OF).items():
        sources.append({'source': src, 'state': x['state'], 'last_receipt': x['last_receipt'], 'files': x['files'], 'rows': x['rows'], 'rejected_rows': x['rejected_rows'],
                        'record_types': x['entities'], 'ev': [rc[n]['ev'] for n in sorted(rc) if rc[n]['source'] == src]})
    quality = []
    for kind, counts in sorted(FR.quality_summary(s).items()):
        ev = EV.add('E-q-' + kind, {'type': 'quality', 'title': 'Record outcomes, %s' % kind, 'kind': kind, 'counts': counts})
        quality.append({'kind': kind, 'ev': ev, 'counts': {k: num(v, None, 'count', ev) for k, v in sorted(counts.items()) if isinstance(v, int)}})
    held = []
    for x in IV.review_table(s):
        if x['status'] not in ('accepted',) or x['codes']:
            ev = _record_evidence(EV, s, x['ref'], 'held record')
            held.append({'ref': x['ref'], 'status': x['status'], 'codes': [PL.reason(c) for c in x['codes']], 'amount': num(x.get('amount_cents'), None, 'record', ev),
                         'duplicate_of': x.get('duplicate_of'), 'review': x.get('review'), 'ev': ev})
    quarantine = []
    for q in s.query('quarantine'):
        p = _payload(q)
        ev = EV.add('E-qr-' + q.key, {'type': 'quarantine', 'title': 'Quarantined value, %s' % q.key, 'item': p})
        quarantine.append({'key': q.key, 'status': p.get('status'), 'candidates': p.get('candidates'), 'resolver_role': p.get('resolver_role'), 'ev': ev})
    from apg_auif import gate                                     # the M8 comparison gate for the file route (apg_auif.gate.receipt_status); AUIF is already verified by auif_route
    g = gate.receipt_status(W['receipts'], sorted(W['receipts']))
    file_gate = {'status': g['status'], 'reasons': [PL.reason(r['code']) | {'scope': r['scope'], 'detail': r['detail']} for r in g['reasons']]}
    return {'file_route': {'name': 'File import (M3)', 'gate': file_gate, 'receipts': list(rc.values()), 'sources': sources, 'quality': quality, 'held': held, 'quarantine': quarantine},
            'connected_route': dict(auif, name='Connected systems (AUIF rev14, synthetic)')}


def _view(W, persona, auif):
    t = W['tenant']
    port = Grants({(t, persona['user'], k): v for k, v in persona['grants'].items()})
    ctx = W['who']('v-%s' % persona['view'], t, persona['user'], persona['roles'])
    can = lambda scope, a='view': port.allows(ctx.ctx, scope, a) is True
    tenant_view = can({'level': 'tenant'})
    EV = Evidence()
    projects = [p for p in W['projects'] if can({'level': 'project', 'project': p})]
    visible = lambda f: can(f['scope'])
    fall = sorted((f for f in FD.all_findings(W['s']) if visible(f)), key=lambda f: f['finding_id'])
    findings = [_finding(W, EV, f) for f in fall]
    fids = {f['id'] for f in findings}
    recs = [_recommendation(EV, e) for e in sorted(W['rec_run']['result']['recommendations'], key=lambda e: (e.get('rank') is None, e.get('rank') or 0, e['rec_id']))
            if e['finding_id'] in fids]
    prj = [_project_figures(W, EV, p) for p in projects]
    for p in prj:
        p['findings'] = [f['id'] for f in findings if f['project'] == p['id']]
        p['materials'] = _materials(W, EV, p['id'])
    if tenant_view:
        pv = PF.portfolio_view(W['s'])
    elif len(projects) == 1:
        pv = PF.portfolio_view(W['s'], project=projects[0])
    else:
        pv = {'by_interpretation': {}}
    exposure = []
    for k, v in sorted(pv.get('by_interpretation', {}).items()):
        ev = EV.add('E-port-' + k, {'type': 'portfolio', 'title': 'Exposure range, %s' % PL.humanise(k), 'interpretation': k, 'view': v,
                                    'scope': 'tenant' if tenant_view else 'project %s' % ', '.join(projects)})
        exposure.append({'interpretation': k, 'findings': v.get('findings'), 'quantified': v.get('quantified'), 'unquantified': v.get('unquantified'),
                         'available': v.get('quantified_amount_available'), 'lower': num(v.get('lower_bound_cents') if v.get('quantified_amount_available') else None, None, 'range', ev),
                         'upper': num(v.get('upper_bound_cents') if v.get('quantified_amount_available') else None, None, 'range', ev),
                         'labels': v.get('amount_labels', []), 'display': v.get('range_display'), 'note': v.get('note'), 'ev': ev})
    approvals = []
    for fid in W.get('proposals', []):
        f = FD.get(W['s'], fid)
        if not visible(f):
            continue
        shown = AB.present(ctx, port, W['clock'], fid)
        item = {'finding_id': fid, 'present': {k: shown.get(k) for k in ('status', 'code', 'message', 'can_approve', 'finding_status', 'finding_version', 'proposal', 'scope')},
                'token': shown.get('token'), 'finding': next((x for x in findings if x['id'] == fid), None)}
        if shown.get('token'):
            tk = shown['token']
            item['request'] = {'request_id': '(chosen by the screen, one per intended approval)', 'finding_id': fid, 'version': tk['version'], 'digest': tk['digest'],
                               'proposal': tk['proposal'], 'rationale': '(typed by the approver)'}
        if f.get('status') == 'action_approved' and W.get('approval_result', {}).get('finding_id') == fid:
            ar = W['approval_result']
            item['approved'] = {k: ar.get(k) for k in ('status', 'code', 'approved_by', 'approved_at', 'approved_version', 'approved_digest', 'approved_proposal')}
            item['in_force'] = AB.check_for_execution(ctx, port, W['clock'], fid, ar.get('approved_version'), ar.get('approved_digest'), ar.get('approved_proposal'))
        approvals.append(item)
    health = _data_health(W, EV, auif) if tenant_view else None
    states = {}
    for p in prj:
        for k, fg in p['figures'].items():
            states.setdefault(fg['state'], []).append([p['id'], k])
    return {'view': persona['view'], 'tenant': t, 'builder': persona['builder'], 'person': {'user': persona['user'], 'name': persona['name'], 'roles': list(persona['roles'])},
            'access': {'tenant_level': tenant_view, 'projects': projects, 'approve': [p for p in projects if can({'level': 'project', 'project': p}, 'approve')]},
            'as_of': AS_OF, 'projects': prj, 'figure_states': states, 'exposure': exposure, 'findings': findings, 'recommendations': recs,
            'recommendation_statement': W['rec_run']['result'].get('statement'), 'approvals': approvals, 'data_health': health,
            'tenant_materials': _tenant_materials(W, EV) if (tenant_view and W['mv']) else None, 'workflow': W['workflow'] if tenant_view else [],
            'policies': _policies(W, prj), 'evidence': EV.items}


def _tenant_materials(W, EV):
    r = MD.run_tenant(W['s'], MD.mkt_registry(), W['clock'], AS_OF, W['fv'], W['dv'], W['mv'], W['sv'], W['projects'])
    a = r['result']['analyses']
    reg = []
    for mat, x in sorted((a.get('evidence_register') or {}).items()):
        idx = x.get('index') or {}
        reg.append({'material': mat, 'index_state': idx.get('state'), 'index_age_days': idx.get('age_days'), 'index_threshold_days': idx.get('threshold_days'),
                    'quotes': [{'subject': q.get('subject'), 'state': q.get('state'), 'age_days': q.get('age_days'), 'valid_until': q.get('valid_until')} for q in x.get('quotes', [])]})
    dups = []
    for d in a.get('duplicates', []):
        evs = [_record_evidence(EV, W['s'], o['ref'], 'order', o.get('revision')) for o in d.get('orders', [])]
        dups.append({'project': d.get('project'), 'material': d.get('material'), 'supplier': d.get('supplier'), 'held_as_candidates': d.get('held_as_candidates'),
                     'orders': [dict(ref=o['ref'], date=o.get('date'), amount=num(o.get('amount_cents'), None, 'record', ev)) for o, ev in zip(d.get('orders', []), evs)]})
    return {'run_key': r['run_key'], 'evidence_register': reg, 'duplicates': dups, 'statement': r['result'].get('statement')}


def _policies(W, prj):
    """What the runs themselves recorded about their policy (approved or not), never a separate reading."""
    out = []
    fp = next((fg['policy_seen'] for p in prj for fg in p['figures'].values() if fg.get('policy_seen')), None)
    if fp:
        out.append({'name': 'Financial', 'version': fp.get('version'), 'approved': fp.get('approved') is True, 'illustrative': True})
    for name, x in (('Detection', W.get('det_policy')), ('Procurement', W.get('mkt_policy')), ('Recommendation', (W.get('rec_run') or {}).get('result', {}).get('policy'))):
        if x:
            out.append({'name': name, 'version': x.get('version'), 'approved': x.get('approved') is True, 'illustrative': True})
    return out


def build_views(root):
    worlds = {t: build_world(root, t) for t in ('zero_one', 'zero_two')}
    for W in worlds.values():
        run_workflow(W)
    auif = {t: auif_route(root, t) for t in worlds}
    views = {p['view']: _view(worlds[p['tenant']], p, auif[p['tenant']]) for p in PERSONAS}
    return {'meta': {'statement': STATEMENT, 'as_of': AS_OF, 'release': 'APG-M10 (builder-made prototype; not accepted)', 'synthetic': True,
                     'order': [p['view'] for p in PERSONAS], 'labels': {p['view']: '%s, %s' % (p['name'], p['builder']) for p in PERSONAS},
                     'definitions': 'PROPOSED', 'open': ['CF-53', 'EDR-12', 'EDR-29', 'EDR-31']}, 'views': views}


def dumps(model):
    return json.dumps(canon.deep_copy(model), indent=1, sort_keys=True, ensure_ascii=True) + '\n'
