"""Small hand-made worlds for the procurement-layer tests.  Every value is synthetic.  A MktMini builds one tenant with only the records a test names, ingests them through the real M3, M4, M5 and
M6 intake paths, reconciles with the SYNTHETIC register, stores the demonstration policies and specification register and runs the real procurement formulas - the same code path as the Builder Zero run."""
import json, os
from . import _path                                         # noqa: F401
from ._path import HERE_ROOT
from .helpers_det import DetMini, det_world, quote, AS_OF, PO_H, csvb, bud, ctc   # noqa: F401
from apg import repro
from apg.fin import snap
from apg.mkt import analysis as AN, common as MC, compare as CP, demo_mkt as DM, detect as MD, gather as MG, intake as MI, policy as MP

MAT_H = ['material_id', 'description', 'unit']
DEM_H = ['demand_id', 'project_id', 'material_id', 'qty', 'unit', 'required_on_site']
DK_H = ['docket_id', 'po_id', 'material_id', 'delivery_date', 'qty_delivered', 'qty_accepted']
SPREQ_H = ['requirement_id', 'project_id', 'material_id', 'basis_ref', 'approved_by', 'approved_on']
RD_H = ['quote_id', 'attribute', 'value', 'extracted_by', 'extractor_kind', 'verified_by', 'verified_on']
TIER_H = ['quote_id', 'min_qty', 'unit_rate_cents']
TERM_H = ['quote_id', 'term', 'value']
LA_H = ['quote_id', 'component', 'per_unit_cents', 'rate_bps', 'currency', 'basis', 'source_ref', 'set_by', 'set_on']
IC_H = ['quote_id', 'check', 'status', 'evidence_ref', 'checked_by', 'checked_on']
FX_H = ['fx_date', 'pair', 'rate']
OBS_H = ['obs_id', 'material_id', 'obs_date', 'value', 'unit', 'kind', 'source_label', 'geography']

STD_MATERIALS = [['MAT-STEEL', 'steel', 'tonne'], ['MAT-CONC40', 'concrete 40', 'm3'], ['MAT-CONC32', 'concrete 32', 'm3'], ['MAT-PBOARD', 'plasterboard', 'sheet'],
                 ['MAT-REO', 'bar', 'tonne'], ['MAT-CU', 'copper', 'metre']]


def pom(po='PO-1', supplier='SUP-001', project='PRJ-001', mat='MAT-STEEL', qty='10', rate='100000', date='2026-08-01', status='open', unit='tonne', cc='CC-01', amount=None):
    amt = amount if amount is not None else str(int(qty) * int(rate))
    return [po, supplier, project, cc, date, mat, qty, unit, rate, amt, status]


def demand(did='DEM-1', project='PRJ-001', mat='MAT-STEEL', qty='100', unit='tonne', required='2026-12-01'):
    return [did, project, mat, qty, unit, required]


def docket(did='DK-1', po='PO-1', mat='MAT-STEEL', date='2026-08-20', delivered='10', accepted='10'):
    return [did, po, mat, date, delivered, accepted]


def reading(q='Q-1', attr='grade', value='300PLUS', by='extractor', kind='ai_model', verified_by='alice', verified_on='2026-09-02'):
    return [q, attr, value, by, kind, verified_by, verified_on]


def std_readings(q='Q-1', unit='tonne', verified_by='alice'):
    """Verified readings for the steel family of the demonstration register."""
    return [reading(q, 'grade', '300PLUS', verified_by=verified_by), reading(q, 'section', '250UB', verified_by=verified_by), reading(q, 'unit', unit, verified_by=verified_by)]


def fxrow(date='2026-09-30', rate='0.6540', pair='AUD/USD'):
    return [date, pair, rate]


def obs(oid='OBS-1', mat='MAT-STEEL', date='2026-09-15', value='10930', kind='index'):
    return [oid, mat, date, value, 'index_points_x100', kind, 'SYNTHETIC-INDEX', 'AU-national']


class MktMini(DetMini):
    def __init__(self, tenant='zero_one', with_suppliers=True, policy=None, approved=True, det_policy=None, mkt_policy=None, mkt_spec=None):
        super().__init__(tenant, with_suppliers, policy, approved, det_policy)
        self.mp = self.install(MP.store_policy, MP.approve_policy, MP.POLICY_KIND, mkt_policy or DM.demo_mkt_policy())
        self.sp = self.install(MP.store_spec, MP.approve_spec, MP.SPEC_KIND, mkt_spec or DM.demo_mkt_spec())
        self.mreg = MD.mkt_registry()

    # ---- ingestion through the real M6 path
    def mk(self, template, header, rows, source):
        return MI.ingest_mkt_file(self.s, self.clock, MI.mkt_template(HERE_ROOT, template), csvb(header, rows), source, 'f.csv')

    def materials(self, *rows):
        return self.mk('TPL-BZ-MATERIALS', MAT_H, rows or STD_MATERIALS, 'master')

    def demands(self, *rows):
        return self.mk('TPL-BZ-MATERIAL-DEMAND', DEM_H, rows, 'materials')

    def dockets(self, *rows):
        return self.mk('TPL-BZ-DELIVERIES', DK_H, rows, 'materials')

    def spec_reqs(self, *rows):
        return self.mk('TPL-MKT-SPEC-REQUIREMENTS', SPREQ_H, rows, 'specification')

    def readings(self, *rows):
        return self.mk('TPL-MKT-QUOTE-READINGS', RD_H, rows, 'procurement')

    def tiers(self, *rows):
        return self.mk('TPL-MKT-QUOTE-TIERS', TIER_H, rows, 'procurement')

    def terms(self, *rows):
        return self.mk('TPL-MKT-QUOTE-TERMS', TERM_H, rows, 'procurement')

    def assumptions(self, *rows):
        return self.mk('TPL-MKT-LANDED-ASSUMPTIONS', LA_H, rows, 'procurement')

    def checks(self, *rows):
        return self.mk('TPL-MKT-IMPORT-CHECKS', IC_H, rows, 'procurement')

    def fx(self, *rows):
        return self.m3('TPL-BZ-FX-RATES', csvb(FX_H, rows), 'market')

    def observations(self, *rows):
        return self.m3('TPL-BZ-MARKET-OBSERVATIONS', csvb(OBS_H, rows), 'market')

    def orders(self, *rows):
        r = self.pos(*rows)
        self.reconcile()
        return r

    def quote_rows(self, *rows):
        r = self.quotes(*rows)
        self.reconcile()
        return r

    # ---- policies
    def set_mkt(self, **override):
        ver = 'M-%d' % (len(self.s.query(MP.POLICY_KIND)) + 1)
        self.mp = self.install(MP.store_policy, MP.approve_policy, MP.POLICY_KIND, DM.demo_mkt_policy(version=ver, **override))
        return self.mp

    def set_spec(self, **override):
        ver = 'S-%d' % (len(self.s.query(MP.SPEC_KIND)) + 1)
        self.sp = self.install(MP.store_spec, MP.approve_spec, MP.SPEC_KIND, DM.demo_mkt_spec(version=ver, **override))
        return self.sp

    def drop(self, *paths):
        """New procurement policy version with the dotted parameters removed (nothing is defaulted)."""
        import copy
        f = DM.demo_mkt_fields()
        for path in paths:
            parts = path.split('.')
            cur = f
            for p in parts[:-1]:
                cur = cur[p]
            cur.pop(parts[-1], None)
        return self.set_mkt(**f)

    # ---- facts and analyses without a stored run
    def facts(self, project=None, as_of=AS_OF, authorised=None):
        if project:
            refs, params = MG.gather_project(self.s, project, as_of, self.policy['version'], self.dp['version'], self.mp['version'], self.sp['version'])
        else:
            refs, params = MG.gather_tenant(self.s, as_of, self.policy['version'], self.dp['version'], self.mp['version'], self.sp['version'], authorised or [])
        return snap.Facts(repro._load(self.s, refs), params)

    def analysis(self, project=None, as_of=AS_OF, authorised=None):
        F = self.facts(project, as_of, authorised)
        return AN.Analysis(F, MC.mkt_policy(F), MC.mkt_spec(F), as_of, project, set(authorised) if authorised is not None else None)

    def ctx(self, project=None, as_of=AS_OF, authorised=None):
        return self.analysis(project, as_of, authorised).ctx

    # ---- runs
    def mdetect(self, project='PRJ-001', as_of=AS_OF):
        return MD.run_project(self.s, self.mreg, self.clock, project, as_of, self.policy['version'], self.dp['version'], self.mp['version'], self.sp['version'])

    def mtenant(self, as_of=AS_OF, authorised=('PRJ-001',)):
        return MD.run_tenant(self.s, self.mreg, self.clock, as_of, self.policy['version'], self.dp['version'], self.mp['version'], self.sp['version'], list(authorised))

    def mres(self, project='PRJ-001', as_of=AS_OF):
        return self.mdetect(project, as_of)['result']

    def mtres(self, as_of=AS_OF, authorised=('PRJ-001',)):
        return self.mtenant(as_of, authorised)['result']

    def mingest(self, rec):
        from apg.det import findings as FD
        return FD.ingest_run(self.svc, self.clock, self.mreg, rec['run_key'])


def mkt_world(**kw):
    """PRJ-001 and PRJ-002 with the det_world base, the standard materials, quotes and orders left to the test."""
    m = MktMini(**kw)
    m.projects(['PRJ-001', 'P1', '10000000', '2026-01-01', '2027-01-01'], ['PRJ-002', 'P2', '10000000', '2026-01-01', '2027-01-01'])
    m.contracts(['PRJ-001', '10000000', '0'], ['PRJ-002', '10000000', '0'])
    m.budgets(bud(cc='CC-01', cents='5000000'), bud(project='PRJ-002', cc='CC-01', cents='5000000'))
    m.ctcs(ctc(cc='CC-01', cents='1500000'))
    m.materials()
    return m


def sigs(result, rule):
    return [s for s in result['signals'] if s['rule']['id'] == 'DET-' + rule]
