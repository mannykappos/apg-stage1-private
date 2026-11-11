"""Small hand-made worlds for the M7 recommendation tests.  Every value is synthetic.

A RecWorld is one tenant with a real M4 financial world (so a forecast can be calculated and adopted as a verification baseline) and findings written as the detection service writes them
(`findings.new_finding` of a signal made by `signal.make`, the real signal contract).  People then act on the findings through the real M5 lifecycle (`findings.transition`).  The recommendation
run, the records, the inputs and the verification are the real M7 code.  The findings are fixtures: they do not come from a detection rule, so a test can name exactly the evidence strength,
missing information, dates, overlap and amounts it needs."""
from . import _path                                         # noqa: F401
from .helpers_fin import AS_OF, Mini, bud, ctc, inv                                       # noqa: F401
from apg import canon
from apg.det import findings as FD, signal as S
from apg.fin import forecast_book as FB
from apg.rec import demo_rec as DR, engine as E, inputs as IN, lifecycle as L, policy as RP, verify as V

LONG = 10 ** 8
RULE = {'id': 'DET-TST', 'version': 1, 'params': {}}

COMPLETE_ALT = {'name': 'switch supplier', 'baseline_ref': None, 'proposed_action': 'place the order with the second supplier', 'affected_activities_resources': 'level 3 slab pour',
                'financial_effects_and_timing': 'lower landed cost from the October order', 'incremental_costs': 'qualification of the new supplier, entered in the incremental costs',
                'dependencies_and_approvals': 'commercial manager approval', 'schedule_quality_safety_operations': 'no schedule change; quality documents to be checked',
                'assumptions_uncertainty_gaps': 'the quote is held until its expiry', 'invalidating_conditions': 'the quote is withdrawn or the specification changes',
                'verification_method': 'compare the invoiced landed cost with the adopted forecast'}


class RecWorld:
    def __init__(self, tenant='zero_one', policy=None, approved=True, with_baseline=True):
        m = Mini(tenant)
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0'])
        m.budgets(bud(cc='CC-01', cents='5000000'), bud(cc='CC-02', cents='3000000'))
        m.ctcs(ctc(cc='CC-01', version='F-A', date='2026-08-31', cents='1500000', reason='initial'))
        m.invoices(inv('INV-1', cc='CC-01', ex='3000000', date='2026-08-01'))
        m.reconcile()
        self.m, self.w, self.clock, self.tenant = m, m.w, m.clock, tenant
        w = self.w
        self.s = w.who('t1-' + tenant, tenant, 'ann', ('importer',), ttl=LONG)
        self.det = w.who('det-' + tenant, tenant, 'detsvc', (FD.SERVICE,), 'service', ttl=LONG)
        self.rev = w.who('rev-' + tenant, tenant, 'rita', (FD.REVIEWER,), ttl=LONG)
        self.fown = w.who('fown-' + tenant, tenant, 'fred', (FD.OWNER,), ttl=LONG)
        self.fapr = w.who('fapr-' + tenant, tenant, 'faye', (FD.APPROVER,), ttl=LONG)
        self.svc = w.who('rsvc-' + tenant, tenant, 'recsvc', (L.SERVICE,), 'service', ttl=LONG)
        self.owner = w.who('own-' + tenant, tenant, 'olly', (IN.OWNER,), ttl=LONG)
        self.owner2 = w.who('own2-' + tenant, tenant, 'opal', (IN.OWNER,), ttl=LONG)
        self.creview = w.who('crev-' + tenant, tenant, 'cora', (IN.REVIEWER,), ttl=LONG)
        self.pm = w.who('pm-' + tenant, tenant, 'pete', ('project_manager',), ttl=LONG)
        self.cm = w.who('cm-' + tenant, tenant, 'cass', ('commercial_manager',), ttl=LONG)
        self.director = w.who('dir-' + tenant, tenant, 'dina', ('director',), ttl=LONG)
        self.verifier = w.who('ver-' + tenant, tenant, 'vera', (L.VERIFIER,), ttl=LONG)
        self.fcowner = w.who('fco-' + tenant, tenant, 'olga', (FB.OWNER_ROLE,), ttl=LONG)
        self.ai = w.who('ai-' + tenant, tenant, 'assistant', (IN.OWNER, L.VERIFIER, 'project_manager', 'commercial_manager', 'director', IN.REVIEWER), 'ai', ttl=LONG)
        self.polprop = w.who('pprop-' + tenant, tenant, 'paula', (), ttl=LONG)                       # proposes policies (any person)
        self.polown = w.who('pown-' + tenant, tenant, 'quentin', (RP.POLICY_ROLE,), ttl=LONG)       # approves them (the policy owner)
        self.approved = approved
        self.policy = self._store_policy(policy or DR.demo_rec_policy(proposer='paula'))
        self.reg = V.registry(E.registry())
        self.baseline = None
        if with_baseline:
            self.baseline = m.run('fin.forecast', extra={'forecast_version': 'F-A'})
            FB.adopt(self.fcowner, m.reg, self.clock, 'PRJ-001', AS_OF, self.baseline['run_key'])
        self.n = 0

    # ---- findings (fixtures through the real signal contract and lifecycle)
    def finding(self, subject=None, interp='forecast_exposure', family='cost_commitments', gross=1000000, label='record', strength='strong', missing=(), date=None, time_sensitive=False,
                overlap=None, refs=None, project='PRJ-001', status='confirmed', limits=(), as_of=AS_OF):
        self.n += 1
        subject = subject or 'SUBJ-%03d' % self.n
        quant = S.quantified(gross, 'synthetic test amount', 'test/calc', label=label) if gross is not None else S.unquantified('no defensible amount in the fixture')
        refs = refs or ['invoice/INV-%03d' % self.n]
        sig = S.make(RULE, {'level': 'project', 'project': project}, subject, family, 'test_subtype', interp, [S.evidence(r, 1) for r in refs], 'observed condition ' + subject,
                     'expected condition', 'why it matters', quant, strength, missing=missing, limits=limits,
                     urgency={'time_sensitive': bool(time_sensitive), 'date': date, 'basis': 'fixture date' if date else ''}, overlap_group=overlap)
        f = FD.new_finding(sig, 'run-fixture-%d' % self.n, '2026-09-30T00:00:00Z', as_of, False)
        self.det.put(FD.KIND, f['finding_id'], f)
        if status in ('under_review', 'confirmed', 'dismissed', 'action_proposed', 'action_approved', 'in_progress', 'resolved', 'superseded'):
            FD.transition(self.rev, self.clock, f['finding_id'], 'under_review')
        if status in ('confirmed', 'action_proposed', 'action_approved', 'in_progress', 'resolved'):
            FD.transition(self.rev, self.clock, f['finding_id'], 'confirmed', rationale='evidence checked')
        if status == 'dismissed':
            FD.transition(self.rev, self.clock, f['finding_id'], 'dismissed', rationale='not a real issue')
        if status in ('action_proposed', 'action_approved', 'in_progress', 'resolved'):
            FD.transition(self.fown, self.clock, f['finding_id'], 'action_proposed', action_text='do the thing')
        if status in ('action_approved', 'in_progress', 'resolved'):
            g = FD.get(self.s, f['finding_id'])
            t = FD.approval_token(g)
            FD.approve_action(self.fapr, self.clock, f['finding_id'], t['version'], t['digest'], 'ok', t['proposal'])
        if status in ('in_progress', 'resolved'):
            FD.transition(self.fown, self.clock, f['finding_id'], 'in_progress')
        if status == 'resolved':
            FD.transition(self.fown, self.clock, f['finding_id'], 'resolved', rationale='done', evidence_ref='invoice/INV-001')
        if status == 'superseded':
            other = self.finding(status='confirmed')
            FD.transition(self.rev, self.clock, f['finding_id'], 'superseded', rationale='replaced', superseded_by=other)
        return f['finding_id']

    def rid(self, fid):
        return E.rec_id_of(fid)

    # ---- recommendation runs
    def run(self, as_of=AS_OF, policy=None, ingest=True, project=None):
        r = E.run(self.s, self.reg, self.clock, as_of, policy or self.policy['version'], project)
        if ingest:
            L.ingest_run(self.svc, self.clock, self.reg, r['run_key'])
        return r

    def entry(self, run, fid):
        return [e for e in run['result']['recommendations'] if e['finding_id'] == fid][0]

    def _store_policy(self, p):
        RP.store_policy(self.polprop, p)
        if self.approved:
            return RP.approve_policy(self.polown, self.clock, p['version'], 'test policy approved by its owner')
        return RP.store_policy(self.polprop, p).payload

    def set_policy(self, **override):
        ver = 'REC-T-%d' % (len(self.s.query(RP.POLICY_KIND)) + 1)
        self.policy = self._store_policy(DR.demo_rec_policy(version=ver, proposer='paula', **override))
        return self.policy

    # ---- inputs that make a recommendation submittable
    def ready(self, fid, benefit=600000, costs=None, kind='purchase_order', alts=None, reviews=True, assess=True):
        rid = self.rid(fid)
        IN.set_inputs(self.owner, self.clock, rid, action_kind=kind, expected_benefit={'cents': benefit, 'basis': 'owner estimate'},
                      incremental_costs=costs if costs is not None else [{'component': 'qualification', 'cents': 100000, 'basis': 'two days of a quantity surveyor'}],
                      alternatives=alts if alts is not None else [dict(COMPLETE_ALT, baseline_ref='repro_record/' + self.baseline['run_key'])])
        f = FD.get(self.s, fid)
        if reviews:
            for t in (self.policy.get('mandatory_reviews') or {}).get(f['signal']['taxonomy']['family'], []):
                IN.record_review(self.creview, self.clock, rid, t, 'cleared', 'reviewed')
        if assess:
            for item in f['signal']['confidence']['missing_information']:
                IN.record_evidence_assessment(self.creview, self.clock, rid, item, False, 'not needed to act')
        return rid

    def approver_for(self, rec):
        role = rec['current']['constraints']['approval_role']
        return {'project_manager': self.pm, 'commercial_manager': self.cm, 'director': self.director}[role]

    def to_approved(self, fid, **kw):
        rid = self.ready(fid, **kw)
        self.run()
        L.submit(self.owner2, self.clock, rid)
        r = L.get(self.s, rid)
        t = L.approval_token(r)
        return L.approve(self.approver_for(r), self.clock, rid, t['version'], t['digest'], t['submission'], 'approved in the test')

    def to_completed(self, fid, **kw):
        rid = self.rid(fid)
        self.to_approved(fid, **kw)
        L.transition(self.owner2, self.clock, rid, 'in_progress')
        return L.transition(self.owner2, self.clock, rid, 'completed_pending_verification', evidence_refs=[('ap_invoice', 'INV-1', 1)])

    def offsets(self, **over):
        o = {c: {'not_applicable': 'nothing of this kind arose'} for c in self.policy['verification']['offset_components']}
        o.update(over)
        return o
