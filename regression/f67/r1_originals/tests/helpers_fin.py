"""Small hand-made worlds for the financial-core tests.  Every value is synthetic.  A Mini builds one tenant with only the records a test names, ingests them through the real
M3 and M4 intake paths, reconciles with the SYNTHETIC register and runs real calculations - so a test exercises the same code path as the Builder Zero run."""
import json, os
from . import _path                                         # noqa: F401
from ._path import HERE_ROOT
from .helpers_ingest import World, csvb, inv, inv_file, load_suppliers, tpl
from apg import repro
from apg.ingest import demo_setup as D, pipeline as P3, reconcile as R3
from apg.fin import calc_records as C, demo_fin as DF, intake, policy as P

AS_OF = '2026-09-30'
PO_H = ['po_id', 'supplier_id', 'project_id', 'cost_code', 'po_date', 'material_id', 'qty', 'unit', 'unit_rate_cents', 'amount_cents', 'status']
AMD_H = ['amendment_id', 'po_id', 'amendment_date', 'delta_cents', 'approved_change_ref', 'reason']
CRN_H = ['credit_id', 'supplier_id', 'against_invoice_id', 'credit_date', 'ex_gst_cents', 'gst_cents']
BUD_H = ['project_id', 'cost_code', 'budget_cents', 'revision', 'revision_date']
PRJ_H = ['project_id', 'name', 'contract_value_cents', 'start_date', 'planned_finish']
CON_H = ['project_id', 'original_contract_cents', 'approved_variations_cents']
VAR_H = ['variation_id', 'project_id', 'raised_date', 'status', 'value_cents', 'description']
CTC_H = ['project_id', 'cost_code', 'forecast_version', 'forecast_date', 'cost_to_complete_cents', 'estimate_basis', 'movement_reason']
RET_H = ['project_id', 'retention_held_cents', 'release_due_date', 'released_date', 'hold_reason']
SEC_H = ['instrument_id', 'project_id', 'kind', 'face_value_cents', 'expiry_date']
FAC_H = ['facility_id', 'limit_cents', 'drawn_cents', 'rate_bps', 'as_of']
BANK_H = ['txn_id', 'txn_date', 'amount_cents', 'description']


def po(po_id='PO-1', supplier='SUP-001', project='PRJ-001', cc='CC-01', date='2026-01-10', amount='1000000', status='open'):
    return [po_id, supplier, project, cc, date, 'MAT-X', '1', 'ea', amount, amount, status]


def bud(project='PRJ-001', cc='CC-01', cents='5000000', rev='R0', date='2026-01-01'):
    return [project, cc, cents, rev, date]


def ctc(project='PRJ-001', cc='CC-01', version='F-1', date='2026-09-30', cents='1000000', basis='builder estimate', reason='initial'):
    return [project, cc, version, date, cents, basis, reason]


def var(vid='VAR-1', project='PRJ-001', raised='2026-03-01', status='approved', value='100000', desc='x'):
    return [vid, project, raised, status, value, desc]


class Mini:
    def __init__(self, tenant='zero_one', with_suppliers=True, policy=None, approved=True):
        self.w = World()
        self.s = self.w.who('t1', tenant)
        self.clock = self.w.clock
        self.reg = C.fin_registry()
        self.dreg = D.demo_register()
        if with_suppliers:
            load_suppliers(self.w, self.s)
        self.policy = policy or DF.demo_policy(approved=approved)
        P.store_policy(self.s, self.policy)

    # ---- ingestion through the real paths
    def m3(self, template, data, source, revision_field=None, name='f.csv'):
        return P3.ingest_file(self.s, self.clock, tpl(template), data, source, name, D.DEMO_POLICY, revision_field)

    def fin(self, template, data, source, revision_field=None, name='f.csv'):
        return intake.ingest_fin_file(self.s, self.clock, json.load(open(os.path.join(HERE_ROOT, 'fin_templates', template + '.json'))), data, source, name, DF.FIN_INTAKE_POLICY, revision_field)

    def invoices(self, *rows):
        return self.m3('TPL-BZ-AP-INVOICES', inv_file(*rows), 'accounting')

    def pos(self, *rows):
        return self.m3('TPL-BZ-PURCHASE-ORDERS', csvb(PO_H, rows), 'procurement')

    def amendments(self, *rows):
        return self.m3('TPL-BZ-PO-AMENDMENTS', csvb(AMD_H, rows), 'procurement')

    def credits(self, *rows):
        return self.m3('TPL-BZ-CREDIT-NOTES', csvb(CRN_H, rows), 'accounting')

    def budgets(self, *rows):
        return self.m3('TPL-BZ-BUDGET-LINES', csvb(BUD_H, rows), 'job_costing', 'source_revision_label')

    def projects(self, *rows):
        return self.fin('TPL-BZ-PROJECTS', csvb(PRJ_H, rows), 'job_costing')

    def contracts(self, *rows):
        return self.fin('TPL-BZ-CONTRACTS', csvb(CON_H, rows), 'commercial')

    def variations(self, *rows):
        return self.fin('TPL-BZ-VARIATIONS', csvb(VAR_H, rows), 'commercial')

    def ctcs(self, *rows):
        return self.fin('TPL-BZ-CTC-FORECASTS', csvb(CTC_H, rows), 'job_costing')

    def retention(self, *rows):
        return self.fin('TPL-BZ-RETENTION', csvb(RET_H, rows), 'retention_ledger')

    def security(self, *rows):
        return self.fin('TPL-BZ-SECURITY', csvb(SEC_H, rows), 'retention_ledger')

    def facility(self, *rows):
        return self.fin('TPL-BZ-FACILITY', csvb(FAC_H, rows), 'bank')

    def bank(self, *rows):
        return self.fin('TPL-BZ-BANK', csvb(BANK_H, rows), 'bank')

    def reconcile(self, as_of=AS_OF):
        return R3.reconcile(self.s, self.dreg, as_of)

    # ---- calculations
    def run(self, formula, project='PRJ-001', as_of=AS_OF, extra=None, policy=None):
        return C.run_calc(self.s, self.reg, self.clock, formula, project, as_of, policy or self.policy['version'], extra)

    def fig(self, formula, project='PRJ-001', as_of=AS_OF, extra=None, policy=None):
        return self.run(formula, project, as_of, extra, policy)['result']

    def set_policy(self, **override):
        approved = bool(self.policy['approvals'])
        ver = 'P-%d' % (len(self.s.query(P.POLICY_KIND)) + 1)
        pol = DF.demo_policy(version=ver, approved=approved, **override)
        P.store_policy(self.s, pol)
        self.policy = pol
        return pol

    def ref_codes(self, fig):
        return sorted(c['ref'] for c in fig['contributed'])


def base_world(**kw):
    """Project PRJ-001: contract 100,000.00, budget CC-01 50,000.00 and CC-02 30,000.00, one forecast declaring CC-01 only, retention, security, facility."""
    m = Mini(**kw)
    m.projects(['PRJ-001', 'P1', '10000000', '2026-01-01', '2027-01-01'])
    m.contracts(['PRJ-001', '10000000', '0'])
    m.budgets(bud(cc='CC-01', cents='5000000'), bud(cc='CC-02', cents='3000000'))
    m.ctcs(ctc(cc='CC-01', cents='1500000'))
    m.retention(['PRJ-001', '500000', '2027-02-01', '', ''])
    m.security(['BG-1', 'PRJ-001', 'bank_guarantee', '1000000', '2027-06-01'])
    m.facility(['FAC-1', '50000000', '20000000', '800', '2026-09-30'])
    return m
