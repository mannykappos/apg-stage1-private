"""Small hand-made worlds for the detection-layer tests.  Every value is synthetic.  A DetMini builds one tenant with only the records a test names, ingests them through the real
M3, M4 and M5 intake paths, reconciles with the SYNTHETIC register, stores the demonstration policies and runs the real detection formulas - the same code path as the Builder Zero run."""
import json, os
from . import _path                                         # noqa: F401
from ._path import HERE_ROOT
from .helpers_fin import AS_OF, Mini, base_world, bud, ctc, po, var, PO_H, BUD_H, CTC_H, VAR_H, RET_H, PRJ_H     # noqa: F401
from .helpers_ingest import csvb, inv, inv_file                                                             # noqa: F401
from apg import repro
from apg.det import demo_det as DD, detect as D, findings as FD, intake as DI, monitor as MON, policy as DP
from apg.det.reference_m5 import InMemoryNotifier

COMP_H = ['supplier_id', 'evidence_type', 'expiry_date']
NOTICE_H = ['notice_id', 'project_id', 'notice_date', 'notice_type', 'linked_variation_id', 'description']
DELAY_H = ['event_id', 'project_id', 'activity_id', 'start_date', 'end_date', 'working_days', 'recorded_cause', 'holding_cost_rate_cents_per_day']
HIRE_H = ['hire_id', 'project_id', 'equipment', 'on_hire_date', 'off_hire_date', 'needed_until', 'rate_cents_per_day']
TS_H = ['entry_id', 'worker_pseudonym', 'project_id', 'work_package', 'work_date', 'ordinary_hours', 'overtime_hours', 'rate_cents_per_hour']
WO_H = ['project_id', 'work_package', 'week_start', 'quantity', 'unit']
DEF_H = ['defect_id', 'project_id', 'subcontractor', 'trade', 'raised_date', 'severity', 'rework_cost_cents', 'status']
QUOTE_H = ['quote_id', 'supplier_id', 'material_id', 'specification', 'issue_date', 'valid_until', 'unit_rate_cents', 'currency', 'fx_rate_used', 'fx_rate_date', 'freight_cents_per_unit',
           'incoterm_delivery_basis', 'lead_time_days', 'price_kind']
AMD_H = ['amendment_id', 'po_id', 'amendment_date', 'delta_cents', 'approved_change_ref', 'reason']


def quote(qid='Q-1', supplier='SUP-001', material='MAT-X', spec='s', issue='2026-09-01', valid='2026-12-31', rate='100000', cur='AUD', fx='', fxd='', freight='0', basis='delivered', lead='7', kind='quote'):
    return [qid, supplier, material, spec, issue, valid, rate, cur, fx, fxd, freight, basis, lead, kind]


def comp(sup='SUP-001', typ='licence', expiry='2027-12-31'):
    return [sup, typ, expiry]


def hire(hid='H-1', project='PRJ-001', equip='excavator', on='2026-01-01', off='', need='2026-03-31', rate='100000'):
    return [hid, project, equip, on, off, need, rate]


def delay(eid='D-1', project='PRJ-001', act='A-1', start='2026-07-06', end='2026-07-21', wd='10', cause='crane', rate='1000000'):
    return [eid, project, act, start, end, wd, cause, rate]


def defect(did='DEF-1', project='PRJ-001', sub='SUB-1', trade='waterproofing', raised='2026-05-01', sev='major', cost='1000000', status='open'):
    return [did, project, sub, trade, raised, sev, cost, status]


def notice(nid='N-1', project='PRJ-001', date='2026-06-01', typ='client_instruction', link='', desc='move wall'):
    return [nid, project, date, typ, link, desc]


class DetMini(Mini):
    def __init__(self, tenant='zero_one', with_suppliers=True, policy=None, approved=True, det_policy=None):
        super().__init__(tenant, with_suppliers, policy, approved)
        self.dp = self.install(DP.store_policy, DP.approve_policy, DP.POLICY_KIND, det_policy or DD.demo_det_policy())
        LONG = 10 ** 8                                          # sessions that outlive the days some tests advance the clock by
        self.s = self.w.who('t1', tenant, ttl=LONG)
        self.svc = self.w.who('svc', tenant, 'detsvc', ('detection_service',), 'service', ttl=LONG)
        self.reviewer = self.w.who('rev', tenant, 'rita', (FD.REVIEWER,), ttl=LONG)
        self.owner = self.w.who('own', tenant, 'oscar', (FD.OWNER,), ttl=LONG)
        self.approver = self.w.who('apr', tenant, 'abby', (FD.APPROVER,), ttl=LONG)
        self.dreg = self.dreg
        self.detreg = D.det_registry()
        self.notifier = InMemoryNotifier(self.w.provider, self.w.clock)

    # ---- ingestion through the real M5 path
    def det(self, template, data, source, name='f.csv'):
        return DI.ingest_det_file(self.s, self.clock, json.load(open(os.path.join(HERE_ROOT, 'det_templates', template + '.json'))), data, source, name)

    def compliance(self, *rows):
        return self.det('TPL-BZ-COMPLIANCE', csvb(COMP_H, rows), 'compliance')

    def notices(self, *rows):
        return self.det('TPL-BZ-NOTICES', csvb(NOTICE_H, rows), 'commercial')

    def delays(self, *rows):
        return self.det('TPL-BZ-DELAY-EVENTS', csvb(DELAY_H, rows), 'programme')

    def hires(self, *rows):
        return self.det('TPL-BZ-PLANT-HIRE', csvb(HIRE_H, rows), 'plant')

    def timesheets(self, *rows):
        return self.det('TPL-BZ-TIMESHEETS', csvb(TS_H, rows), 'labour')

    def outputs(self, *rows):
        return self.det('TPL-BZ-WORK-OUTPUT', csvb(WO_H, rows), 'labour')

    def defects(self, *rows):
        return self.det('TPL-BZ-DEFECTS', csvb(DEF_H, rows), 'quality')

    def quotes(self, *rows):
        return self.m3('TPL-BZ-QUOTES', csvb(QUOTE_H, rows), 'procurement')

    # ---- detection
    def set_det(self, **override):
        ver = 'D-%d' % (len(self.s.query(DP.POLICY_KIND)) + 1)
        self.dp = self.install(DP.store_policy, DP.approve_policy, DP.POLICY_KIND, DD.demo_det_policy(version=ver, **override))
        return self.dp

    def rules(self, **rule_overrides):
        """New detection policy version with some rule entries replaced (a value of None removes the entry)."""
        base = DD.demo_det_policy()['rules']
        for k, v in rule_overrides.items():
            if v is None:
                base.pop(k, None)
            else:
                base[k] = v
        return self.set_det(rules=base)

    def detect(self, project='PRJ-001', as_of=AS_OF, dpol=None):
        return D.run_project(self.s, self.detreg, self.clock, project, as_of, self.policy['version'], dpol or self.dp['version'])

    def tdetect(self, as_of=AS_OF, dpol=None):
        return D.run_tenant(self.s, self.detreg, self.clock, as_of, dpol or self.dp['version'])

    def res(self, project='PRJ-001', as_of=AS_OF, dpol=None):
        return self.detect(project, as_of, dpol)['result']

    def tres(self, as_of=AS_OF, dpol=None):
        return self.tdetect(as_of, dpol)['result']

    def ingest(self, rec):
        return FD.ingest_run(self.svc, self.clock, self.detreg, rec['run_key'])

    @staticmethod
    def sigs(result, rule):
        return [s for s in result['signals'] if s['rule']['id'] == 'DET-' + rule]

    @staticmethod
    def run(result, rule):
        return result['rule_runs'][rule]


def det_world(**kw):
    """base_world (PRJ-001 with contract, budget, forecast, retention, security, facility) plus the detection policies."""
    m = DetMini(**kw)
    m.projects(['PRJ-001', 'P1', '10000000', '2026-01-01', '2027-01-01'])
    m.contracts(['PRJ-001', '10000000', '0'])
    m.budgets(bud(cc='CC-01', cents='5000000'), bud(cc='CC-02', cents='3000000'))
    m.ctcs(ctc(cc='CC-01', cents='1500000'))
    m.retention(['PRJ-001', '500000', '2027-02-01', '', ''])
    m.security(['BG-1', 'PRJ-001', 'bank_guarantee', '1000000', '2027-06-01'])
    m.facility(['FAC-1', '50000000', '20000000', '800', '2026-09-30'])
    return m


def approve_filled(scoped, clock, fid, **named):
    """Approve through the lowest-level call (`FD.transition`), for a test that is about something other than the token.  Since M6.5 (finding F-57) `transition` refuses an approval that does not name
    the finding version, the evidence digest and the proposal reference, so this names whatever the test does not name itself, taken from the record as the approver would have been shown it.  What a
    test does name (including a wrong or malformed value) is passed through unchanged."""
    try:
        tok = FD.approval_token(FD.get(scoped, fid))
    except Exception:                                       # a damaged record may not give a token at all; the call is then made with what the test names
        tok = {}
    kw = {'approving_version': tok.get('version'), 'approving_digest': tok.get('digest'), 'approving_proposal': tok.get('proposal')}
    kw.update(named)
    return FD.transition(scoped, clock, fid, 'action_approved', **kw)
