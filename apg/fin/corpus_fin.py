"""A corpus of deliberately faulty financial inputs and configurations (M4 test input; Blueprint Section 04 section 7, Section 05, Section 12), each with the outcome the financial core MUST give.  Deterministic.  Synthetic.

Each case starts from the same small synthetic builder (BASE: one project, a contract, a budget, one declared forecast line, one invoice, retention, a security instrument and
a facility statement), applies its faults as further deliveries or policy overrides, reconciles, runs ONE stored calculation and states what the resulting figure must say.
A case never says "no error": it states the figure's state, value, reasons and the records that must be listed as left out, unknown or disputed.

The checker (`check_case`) drives any *world* with this interface, so Amir can run the same corpus against the Engine's own storage and import path:
    world.deliver(table, rows, revision_field=None)   ingest one delivery (table names are in TABLES)
    world.reconcile(as_of)                            run the M3 reconciliation
    world.set_policy(approved=True, **override)       store a new policy version and make it the one used
    world.run(formula, project, as_of, extra)         run and store a calculation -> the figure (dict)
Expectation keys (all optional except state): state, cents, bps, reasons_has, reasons_lack, excluded_has [[ref, class]], excluded_lack [ref], unknown_has [text in input/decision/reason],
disputed_has [ref], classified {key: value}, contributed_has [ref], contributed_lack [ref]."""
import json, os
from .. import tenancy
from ..ingest import demo_setup as D, pipeline as P3, reconcile as R3
from ..ingest.golden_m3 import _world
from . import calc_records as C, demo_fin as DF, intake, policy as P

AS_OF = '2026-09-30'
INV_H = ['invoice_id', 'supplier_id', 'supplier_invoice_no', 'project_id', 'cost_code', 'po_id', 'invoice_date', 'ex_gst_cents', 'gst_cents', 'status', 'source_batch']
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
SUP_H = ['supplier_id', 'name', 'abn_synthetic']
SUPPLIERS = (('SUP-001', 'Alpha Concrete Pty Ltd'), ('SUP-002', 'Beta Timber Pty Ltd'), ('SUP-003', 'Metro Steel Pty Ltd'), ('SUP-004', 'Metro Steel and Fixings Pty Ltd'))

# table -> (kind, template, source, header, revision field)
TABLES = {'invoices': ('m3', 'TPL-BZ-AP-INVOICES', 'accounting', INV_H, None), 'credits': ('m3', 'TPL-BZ-CREDIT-NOTES', 'accounting', CRN_H, None),
          'pos': ('m3', 'TPL-BZ-PURCHASE-ORDERS', 'procurement', PO_H, None), 'amendments': ('m3', 'TPL-BZ-PO-AMENDMENTS', 'procurement', AMD_H, None),
          'budgets': ('m3', 'TPL-BZ-BUDGET-LINES', 'job_costing', BUD_H, 'source_revision_label'), 'projects': ('fin', 'TPL-BZ-PROJECTS', 'job_costing', PRJ_H, None),
          'contracts': ('fin', 'TPL-BZ-CONTRACTS', 'commercial', CON_H, None), 'variations': ('fin', 'TPL-BZ-VARIATIONS', 'commercial', VAR_H, None),
          'ctcs': ('fin', 'TPL-BZ-CTC-FORECASTS', 'job_costing', CTC_H, None), 'retention': ('fin', 'TPL-BZ-RETENTION', 'retention_ledger', RET_H, None),
          'security': ('fin', 'TPL-BZ-SECURITY', 'retention_ledger', SEC_H, None), 'facility': ('fin', 'TPL-BZ-FACILITY', 'bank', FAC_H, None), 'bank': ('fin', 'TPL-BZ-BANK', 'bank', BANK_H, None)}


def inv(i='INV-1', sup='SUP-001', sin=None, project='PRJ-001', cc='CC-01', po='', date='2026-08-01', ex='3000000', gst='300000'):
    return [i, sup, sin or 'SI-' + i[-3:], project, cc, po, date, ex, gst, 'posted', 'B-1']


def po(i='PO-1', sup='SUP-001', project='PRJ-001', cc='CC-01', date='2026-01-10', amount='1000000', status='open'):
    return [i, sup, project, cc, date, 'MAT-X', '1', 'ea', amount, amount, status]


def bud(project='PRJ-001', cc='CC-01', cents='5000000', rev='R0', date='2026-01-01'):
    return [project, cc, cents, rev, date]


def ctc(project='PRJ-001', cc='CC-01', version='F-1', date='2026-09-30', cents='1500000', reason='initial'):
    return [project, cc, version, date, cents, 'builder estimate', reason]


def var(i='VAR-1', project='PRJ-001', status='approved', value='100000', raised='2026-03-01'):
    return [i, project, raised, status, value, 'x']


def crn(i='CRN-1', sup='SUP-001', against='INV-1', date='2026-08-20', ex='200000', gst='20000'):
    return [i, sup, against, date, ex, gst]


BASE = [('projects', [['PRJ-001', 'P1', '10000000', '2026-01-01', '2027-01-01']]), ('contracts', [['PRJ-001', '10000000', '0']]), ('budgets', [bud(cc='CC-01', cents='5000000'), bud(cc='CC-02', cents='3000000')]),
        ('ctcs', [ctc()]), ('invoices', [inv()]), ('retention', [['PRJ-001', '500000', '2027-02-01', '', '']]), ('security', [['BG-1', 'PRJ-001', 'bank_guarantee', '1000000', '2027-06-01']]),
        ('facility', [['FAC-1', '50000000', '20000000', '800', '2026-09-30']])]


def _csv(header, rows):
    import csv, io
    b = io.StringIO()
    w = csv.writer(b, lineterminator='\n')
    w.writerow(header)
    w.writerows(rows)
    return b.getvalue().encode('utf-8')


class ReferenceWorld:
    """The APG reference world: in-memory ports, the real M3 and M4 intake paths, the real stored calculations."""
    def __init__(self, root, approved=True):
        self.root = root
        self.clock, self.prov, self.store, self.audit, who = _world()
        self.s = who('t1', 'zero_one', 'ann')
        self.owner = who('o1', 'zero_one', 'synthetic.policy_owner', (P.POLICY_ROLE,))          # APG-F67: approves the policy in person
        self.reg, self.dreg = C.fin_registry(), D.demo_register()
        P3.ingest_file(self.s, self.clock, self._tpl('TPL-BZ-SUPPLIERS'), _csv(SUP_H, [[a, b, ''] for a, b in SUPPLIERS]), 'master', 'suppliers.csv', D.DEMO_POLICY)
        self.policy = None
        self.set_policy(approved=approved)

    def _tpl(self, name):
        for d in ('import_templates', 'ingest_templates', 'fin_templates'):
            p = os.path.join(self.root, d, name + '.json')
            if os.path.exists(p):
                return json.load(open(p, encoding='utf-8'))
        raise FileNotFoundError(name)

    def deliver(self, table, rows, revision_field=None):
        kind, tid, src, header, rev = TABLES[table]
        data = _csv(header, rows)
        f = P3.ingest_file if kind == 'm3' else intake.ingest_fin_file
        pol = D.DEMO_POLICY if kind == 'm3' else DF.FIN_INTAKE_POLICY
        return f(self.s, self.clock, self._tpl(tid), data, src, table + '.csv', pol, revision_field or rev)

    def reconcile(self, as_of):
        return R3.reconcile(self.s, self.dreg, as_of)

    def set_policy(self, approved=True, **override):
        ver = 'P-%d' % (len(self.s.query(P.POLICY_KIND)) + 1)
        self.policy = DF.install(self.s, self.clock, self.owner if approved else None, ver, **override)
        return self.policy

    def run(self, formula, project, as_of, extra):
        return C.run_calc(self.s, self.reg, self.clock, formula, project, as_of, self.policy['version'], extra)['result']


def _get(d, path):
    for part in path.split('.'):
        d = d[part]
    return d


def check_case(case, world_factory):
    """-> (ok, message)."""
    w = world_factory(case.get('approved', True))
    drop = set(case.get('drop', ()))
    for table, rows in BASE:
        if table not in drop:
            w.deliver(table, rows)
    for table, rows in case.get('deliver', ()):
        w.deliver(table, rows)
    if case.get('policy'):
        w.set_policy(approved=case.get('approved', True), **case['policy'])
    w.reconcile(case.get('as_of', AS_OF))
    try:
        f = w.run(case['formula'], case.get('project', 'PRJ-001'), case.get('as_of', AS_OF), case.get('extra'))
    except Exception as e:                                                  # noqa: BLE001 - a case may require a refusal
        if case['expect'].get('raises') and case['expect']['raises'] in (type(e).__name__, getattr(e, 'code', '')):
            return True, 'refused'
        return False, 'raised %s: %s' % (type(e).__name__, e)
    e = case['expect']
    if 'raises' in e:
        return False, 'wanted a refusal, got a figure'
    if f['state'] != e['state']:
        return False, 'state %s (wanted %s); reasons %s' % (f['state'], e['state'], f['reasons'][:3])
    if 'cents' in e and f['value']['cents'] != e['cents']:
        return False, 'cents %s (wanted %s)' % (f['value']['cents'], e['cents'])
    if 'bps' in e and f['value']['bps'] != e['bps']:
        return False, 'bps %s (wanted %s)' % (f['value']['bps'], e['bps'])
    for r in e.get('reasons_has', ()):
        if not any(r in x for x in f['reasons']):
            return False, 'reason %r missing from %s' % (r, f['reasons'])
    for r in e.get('reasons_lack', ()):
        if any(r in x for x in f['reasons']):
            return False, 'reason %r must not appear' % r
    for ref, cls in e.get('excluded_has', ()):
        if not any(x['ref'] == ref and x['class'] == cls for x in f['excluded']):
            return False, 'exclusion %s/%s missing from %s' % (ref, cls, [(x['ref'], x['class']) for x in f['excluded']])
    for ref in e.get('excluded_lack', ()):
        if any(x['ref'] == ref for x in f['excluded']):
            return False, 'record %s must not be listed as left out' % ref
    for t in e.get('unknown_has', ()):
        if not any(t in u['input'] or t in u['reason'] or t in u['decision'] for u in f['unknown_inputs']):
            return False, 'unknown input %r missing from %s' % (t, [u['input'] for u in f['unknown_inputs']])
    for ref in e.get('disputed_has', ()):
        if not any(x['ref'] == ref for x in f['disputed']):
            return False, 'dispute %s missing' % ref
    for k, v in e.get('classified', {}).items():
        try:
            got = _get(f['classified'], k)
        except (KeyError, TypeError):
            return False, 'classified %s missing' % k
        if got != v:
            return False, 'classified %s = %r (wanted %r)' % (k, got, v)
    refs = {c['ref'] for c in f['contributed']}
    for ref in e.get('contributed_has', ()):
        if ref not in refs:
            return False, 'contributor %s missing' % ref
    for ref in e.get('contributed_lack', ()):
        if ref in refs:
            return False, 'record %s must not contribute' % ref
    return True, 'ok'


def cases():
    C_ = []

    def add(cid, desc, formula, expect, deliver=(), policy=None, drop=(), extra=None, as_of=AS_OF, approved=True, project='PRJ-001'):
        C_.append({'id': cid, 'desc': desc, 'formula': formula, 'expect': expect, 'deliver': list(deliver), 'policy': policy, 'drop': list(drop), 'extra': extra, 'as_of': as_of,
                   'approved': approved, 'project': project})
    A, P_, N = 'authoritative', 'provisional', 'cannot_assess'
    # ---- cost
    add('K01', 'the same invoice delivered twice is counted once', 'fin.actual_cost', dict(state=A, cents=3000000, contributed_has=['ap_invoice/INV-1']), [('invoices', [inv()])])
    add('K02', 'same supplier invoice number with a different amount: conflict, neither version counted', 'fin.actual_cost',
        dict(state=P_, cents=0, excluded_has=[['ap_invoice/INV-1', 'disputed']], disputed_has=['ap_invoice/INV-1'], contributed_lack=['ap_invoice/INV-1']), [('invoices', [inv(ex='3100000')])])
    add('K03', 'invoice from a supplier that is not in the supplier list', 'fin.actual_cost', dict(state=P_, cents=3000000, excluded_has=[['ap_invoice/INV-2', 'held']], contributed_lack=['ap_invoice/INV-2']),
        [('invoices', [inv('INV-2', sup='SUP-999')])])
    add('K04', 'invoice dated after the day it was received', 'fin.actual_cost', dict(state=P_, cents=3000000, excluded_has=[['ap_invoice/INV-2', 'held']]), [('invoices', [inv('INV-2', date='2031-01-01')])])
    add('K05', 'invoice with no cost code', 'fin.actual_cost', dict(state=P_, cents=3000000, excluded_has=[['ap_invoice/INV-2', 'unknown_value']]), [('invoices', [inv('INV-2', cc='')])])
    add('K06', 'credit note larger than its invoice: the pair is held, nothing is guessed', 'fin.actual_cost',
        dict(state=P_, cents=0, excluded_has=[['credit_note/CRN-1', 'held'], ['ap_invoice/INV-1', 'unresolved_link']]), [('credits', [crn(ex='3500000')])])
    add('K07', 'credit note against an invoice that does not exist', 'fin.actual_cost', dict(state=P_, cents=3000000, excluded_has=[['credit_note/CRN-1', 'unattributed']]), [('credits', [crn(against='INV-404')])])
    add('K08', 'credit note dated after the as-of date is not applied', 'fin.actual_cost', dict(state=A, cents=3000000, excluded_has=[['credit_note/CRN-1', 'after_cutoff']]), [('credits', [crn(date='2026-10-01')])])
    add('K09', 'a credit note is applied once even when delivered twice', 'fin.actual_cost', dict(state=A, cents=2800000, contributed_has=['credit_note/CRN-1']), [('credits', [crn()]), ('credits', [crn()])])
    add('K10', 'an invoice for another project does not count here', 'fin.actual_cost', dict(state=A, cents=3000000, contributed_lack=['ap_invoice/INV-2']), [('invoices', [inv('INV-2', project='PRJ-002')])])
    add('K11', 'a negative invoice amount is held, not netted', 'fin.actual_cost', dict(state=P_, cents=3000000, excluded_has=[['ap_invoice/INV-2', 'held']]), [('invoices', [inv('INV-2', ex='-500')])])
    add('K12', 'a conflicting invoice whose versions name different projects is unattributed on this project too', 'fin.actual_cost',
        dict(state=P_, cents=3000000, excluded_has=[['ap_invoice/INV-9', 'unattributed']]), [('invoices', [inv('INV-9', sin='S9', project='PRJ-001', ex='10')]), ('invoices', [inv('INV-9', sin='S9', project='PRJ-002', ex='10')])])
    # ---- commitments
    add('C01', 'purchase order with no cost code', 'fin.commitments', dict(state=P_, cents=0, excluded_has=[['purchase_order/PO-1', 'unknown_value']]), [('pos', [po(cc='')])])
    add('C02', 'purchase order with a status the policy does not map', 'fin.commitments', dict(state=P_, cents=0, unknown_has=['status weird']), [('pos', [po(status='weird')])])
    add('C03', 'two identical purchase orders: both held', 'fin.commitments', dict(state=P_, cents=0, disputed_has=['purchase_order/PO-1', 'purchase_order/PO-2']), [('pos', [po('PO-1'), po('PO-2')])])
    add('C04', 'invoiced more than the order: open is zero and the overrun is stated', 'fin.commitments', dict(state=A, cents=0, reasons_has=['INVOICED_EXCEEDS_COMMITMENT:PO-1']),
        [('pos', [po(amount='1000000')]), ('invoices', [inv('INV-2', sin='S2', po='PO-1', ex='1500000')])])
    add('C05', 'amendment on a purchase order that does not exist', 'fin.commitments', dict(state=P_, cents=1000000, excluded_has=[['po_amendment/AMD-1', 'unattributed']]),
        [('pos', [po()]), ('amendments', [['AMD-1', 'PO-404', '2026-08-01', '100', '', 'x']])])
    add('C06', 'an unapproved amendment is exposure, not commitment', 'fin.commitments', dict(state=A, cents=1000000, classified={'unapproved_exposure_cents': 100000}),
        [('pos', [po()]), ('amendments', [['AMD-1', 'PO-1', '2026-08-01', '100000', '', 'x']])])
    add('C07', 'a cancelled order is not a commitment', 'fin.commitments', dict(state=A, cents=0), [('pos', [po(status='cancelled')])])
    add('C08', 'a credit against an order-linked invoice when nobody has decided whether it reopens the commitment', 'fin.commitments', dict(state=P_, unknown_has=['A12']),
        [('pos', [po()]), ('invoices', [inv('INV-2', sin='S2', po='PO-1', ex='500000')]), ('credits', [crn(against='INV-2', ex='100000')])], policy={'credit_reopens_commitment': None})
    # ---- revenue
    add('V01', 'a submitted variation is not revenue', 'fin.revenue', dict(state=A, cents=10000000), [('variations', [var('V-S', status='submitted', value='900000')])])
    add('V02', 'an approved variation in the register while the contract summary says none', 'fin.revenue', dict(state=P_, cents=10100000, reasons_has=['CONTRACT_SUMMARY_DISAGREES_WITH_REGISTER']), [('variations', [var()])])
    add('V03', 'an approved variation with no value', 'fin.revenue', dict(state=P_, cents=10000000, unknown_has=['variation/VAR-1 value']), [('variations', [var(value='')])])
    add('V04', 'a variation status the policy does not map', 'fin.revenue', dict(state=P_, cents=10000000, unknown_has=['status pending-legal']), [('variations', [var(status='pending-legal')])])
    add('V05', 'no contract record', 'fin.revenue', dict(state=N, unknown_has=['contract/PRJ-001']), drop=['contracts'])
    add('V06', 'two different contract deliveries', 'fin.revenue', dict(state=N, disputed_has=['contract/PRJ-001']), [('contracts', [['PRJ-001', '10500000', '0']])])
    add('V07', 'GST-inclusive basis with no rate configured', 'fin.revenue', dict(state=N, reasons_has=['GST_RATE_NOT_CONFIGURED']), policy={'tax_basis': 'inc_gst'})
    add('V08', 'a disputed variation is not revenue and is listed', 'fin.revenue', dict(state=P_, cents=10000000, disputed_has=['variation/VAR-1']), [('variations', [var(status='disputed', value='50000')])])
    # ---- forecast
    add('F01', 'two different forecast versions on the same latest date', 'fin.forecast', dict(state=N, reasons_has=['AMBIGUOUS_LATEST_FORECAST:F-1,F-2']), [('ctcs', [ctc(version='F-2', cents='2000000')])])
    add('F02', 'forecast older than the freshness limit', 'fin.forecast', dict(state=P_, cents=2500000, reasons_has=['STALE:forecast F-1']), as_of='2026-12-31')
    add('F03', 'budget already exceeded in a cost code: its cost to complete is unknown, never negative', 'fin.forecast',
        dict(state=P_, cents=2000000, classified={'ctc_by_code.CC-02.unknown': 'BUDGET_EXCEEDED_BY:500000'}), [('invoices', [inv('INV-2', sin='S2', cc='CC-02', ex='3500000')])])
    add('F04', 'a declared forecast line delivered with two different amounts is not replaced by a guess', 'fin.forecast',
        dict(state=P_, cents=4000000, classified={'ctc_by_code.CC-01.unknown': 'DECLARED_LINE_HELD:ctc_line/PRJ-001|CC-01|F-1'}), [('ctcs', [ctc(cents='1700000')])])
    add('F05', 'budget lines from mixed revisions', 'fin.forecast', dict(state=P_, reasons_has=['MIXED_BUDGET_REVISIONS']), [('budgets', [bud(cc='CC-03', cents='100', rev='R1')])])
    add('F06', 'declared forecast lines disagree on the forecast date', 'fin.forecast', dict(state=N, reasons_has=['FORECAST_VERSION_DATES_DISAGREE:F-1']), [('ctcs', [ctc(cc='CC-02', date='2026-08-31', cents='1')])])
    add('F07', 'no forecast and a policy that needs a declared line', 'fin.forecast', dict(state=N, reasons_has=['NO_FORECAST_VERSION']), drop=['ctcs'], policy={'ctc_method': {'default': 'declared'}})
    add('F08', 'cost in a code that has no budget and no estimate', 'fin.forecast', dict(state=P_, cents=2499990, classified={'ctc_by_code.CC-77.unknown': 'NO_BUDGET_FOR_CODE'}),
        [('invoices', [inv('INV-2', sin='S2', cc='CC-77', ex='10')])])
    add('F09', 'an invoice dated after the forecast date is shown separately and never added', 'fin.forecast',
        dict(state=A, cents=2500000, reasons_has=['ACTUALS_AFTER_FORECAST_DATE_NOT_ADDED'], classified={'since_forecast_actual_cents': 400000, 'forecast_date': '2026-08-31', 'ffc_cents': 7500000}),
        [('ctcs', [ctc(version='F-0', date='2026-08-31', cents='1500000')]), ('invoices', [inv('INV-2', sin='S2', date='2026-09-10', ex='400000')])], extra={'forecast_version': 'F-0'})
    add('F10', 'no budget and no forecast at all', 'fin.forecast', dict(state=N), drop=['budgets', 'ctcs'])
    # ---- margins
    add('M01', 'recognised margin built on a provisional forecast says so', 'fin.recognised_margin', dict(state=P_, cents=1625000, reasons_has=['PERCENT_COMPLETE_RESTS_ON_A_FORECAST_THAT_IS_PROVISIONAL']),
        [('invoices', [inv('INV-2', sin='S2', cc='CC-02', ex='3500000')])])
    add('M02', 'recognised margin with a zero forecast cost', 'fin.recognised_margin', dict(state=N, reasons_has=['FORECAST_FINAL_COST_NOT_POSITIVE']), drop=['budgets', 'ctcs', 'invoices'], deliver=[('budgets', [bud(cents='0')])])
    add('M03', 'cash-adjusted margin when a listed component has no data', 'fin.cash_adjusted', dict(state=N, reasons_has=['COMPONENT_CANNOT_ASSESS:overdue_receivables']),
        policy={'cash_adjustment': {'base': 'forecast_final', 'components': ['retention_carrying', 'overdue_receivables']}})
    # ---- retention, security, carrying
    add('R01', 'retention release date passed with money still withheld: a review prompt, not an entitlement', 'fin.cash_position',
        dict(state=A, cents=500000, reasons_has=['RELEASE_REVIEW_DUE'], classified={'flags': ['RELEASE_REVIEW_DUE'], 'pools_cents.released': 0}), drop=['retention'],
        deliver=[('retention', [['PRJ-001', '500000', '2026-09-01', '', '']])], extra={'what': 'retention'})
    add('R02', 'carrying cost when the release date has passed and the money is still withheld', 'fin.cash_position', dict(state=N, reasons_has=['EXPECTED_RELEASE_DATE_PASSED_AND_NOT_RELEASED']),
        drop=['retention'], deliver=[('retention', [['PRJ-001', '500000', '2026-09-01', '', '']])], extra={'what': 'retention_carrying'})
    add('R03', 'two different retention ledger deliveries', 'fin.cash_position', dict(state=N, disputed_has=['retention/PRJ-001']), [('retention', [['PRJ-001', '600000', '2027-02-01', '', '']])], extra={'what': 'retention'})
    add('R04', 'a security instrument past its expiry date: a review flag, the face value is unchanged', 'fin.cash_position', dict(state=A, cents=1000000, classified={'flags': ['EXPIRY_REVIEW:BG-1']}),
        as_of='2027-07-01', extra={'what': 'security'})
    add('R05', 'two facility statements', 'fin.cash_position', dict(state=N, reasons_has=['SEVERAL_FACILITIES']), [('facility', [['FAC-2', '1', '1', '900', '2026-09-30']])], extra={'what': 'retention_carrying'})
    add('R06', 'a facility statement dated in the future is held', 'fin.cash_position', dict(state=N, reasons_has=['FACILITY_RECORD_HELD']), drop=['facility'],
        deliver=[('facility', [['FAC-1', '1', '1', '800', '2026-10-15']])], extra={'what': 'retention_carrying'})
    add('R07', 'the ledger says released, no receipt is evidenced: released is not received', 'fin.cash_position',
        dict(state=A, cents=0, classified={'pools_cents.released': 500000, 'pools_cents.received': 0, 'flags': ['RELEASED_PER_LEDGER_CASH_RECEIPT_NOT_EVIDENCED']}), drop=['retention'],
        deliver=[('retention', [['PRJ-001', '500000', '2026-08-01', '2026-08-15', '']])], extra={'what': 'retention'})
    add('R08', 'a negative retention balance is held, not reported', 'fin.cash_position', dict(state=N, excluded_has=[['retention/PRJ-001', 'unknown_value']]), drop=['retention'],
        deliver=[('retention', [['PRJ-001', '-500', '2027-02-01', '', '']])], extra={'what': 'retention'})
    add('R09', 'retention with no expected release date: no carrying cost can be estimated', 'fin.cash_position', dict(state=N, reasons_has=['NO_EXPECTED_RELEASE_DATE']), drop=['retention'],
        deliver=[('retention', [['PRJ-001', '500000', '', '', '']])], extra={'what': 'retention_carrying'})
    add('R10', 'two different security instrument deliveries', 'fin.cash_position', dict(state=N, excluded_has=[['security/BG-1', 'disputed']]), [('security', [['BG-1', 'PRJ-001', 'bank_guarantee', '1100000', '2027-06-01']])],
        extra={'what': 'security'})
    add('R11', 'carrying cost on a policy proxy rate is provisional and says so', 'fin.cash_position',
        dict(state=P_, cents=5945, reasons_has=['RATE_IS_A_POLICY_PROXY_NOT_AN_EVIDENCED_FACILITY_RATE'], unknown_has=['evidenced facility rate']),
        policy={'carrying': {'eligibility': 'as_of_to_release_due_date', 'rate_source': 'declared_proxy', 'proxy_rate_bps': 700, 'day_count_basis': 365, 'funded_share_bps': 5000, 'overlap': 'cost_scope_excludes_financing_costs'}},
        extra={'what': 'retention_carrying'})
    # ---- policy
    add('P01', 'an unapproved policy never gives an authoritative figure', 'fin.forecast', dict(state=P_, cents=2500000, reasons_has=['POLICY_NOT_APPROVED']), approved=False)
    for fld, formula, extra, dec in (('recognition_method', 'fin.recognised_margin', None, 'A5'), ('ctc_method', 'fin.forecast', None, 'A3'), ('ffc_basis', 'fin.forecast', None, 'A4'), ('tax_basis', 'fin.revenue', None, 'A6'),
                                     ('cost_scope', 'fin.actual_cost', None, 'A5'), ('variation_status_map', 'fin.revenue', None, 'A12'), ('po_status_map', 'fin.commitments', None, 'A12'),
                                     ('carrying', 'fin.cash_position', {'what': 'retention_carrying'}, 'A7'), ('cash_adjustment', 'fin.cash_adjusted', None, 'A2')):
        deliver = [('pos', [po()])] if fld == 'po_status_map' else []
        add('P_' + fld, 'open decision %s is not configured: no figure, and the decision is named' % fld, formula, dict(state=N, unknown_has=[dec]), deliver, policy={fld: None}, extra=extra)
    add('P_freshness_days', 'no freshness limit configured: the forecast is provisional, never silently fresh', 'fin.forecast', dict(state=P_, cents=2500000, unknown_has=['A10']), policy={'freshness_days': {}})
    return C_
