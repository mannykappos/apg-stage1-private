"""A corpus of deliberately faulty or borderline detection inputs and configurations (M5 test input; Blueprint Section 06 sections 5.2, 5.4 and 10, Section 04 section 7), each with the
outcome the detection layer MUST give.  Deterministic.  Synthetic.

Each case starts from the same small synthetic builder (the M4 corpus BASE: one project, a contract, a budget, one declared forecast line, one invoice, retention, a security instrument
and a facility statement; that base raises no signal), applies its faults as further deliveries or policy overrides, reconciles, runs ONE stored detection (a project or the tenant) and
states what the result must say.  A case never says "no error": it names the signals that must be raised, the rules that must be silent, and the runs that must say they did not run.

The checker (`check_case`) drives any *world* with this interface, so Amir can run the same corpus against the Engine's own storage and import path:
    world.deliver(table, rows)                 ingest one delivery (table names are in TABLES and in apg.fin.corpus_fin.TABLES)
    world.reconcile(as_of)                     run the M3 reconciliation
    world.set_policies(approved, fin, rules)   store a new financial policy version (overrides `fin`) and a new detection policy version (rule entries replaced by `rules`; None removes one)
    world.detect(scope, as_of)                 run and store a detection; scope is a project id or 'tenant' -> the result dict (signals, rule_runs, det_policy, counts)
Expectation keys (all optional): raised ['RULE|subject'], lacks ['RULE|subject'], silent ['RULE'], only ['RULE|subject'] (exactly these among the threshold rules R01..DEF),
gross {'RULE|subject': cents}, unquantified ['RULE|subject'], subtype {'RULE|subject': text}, severity {'RULE|subject': label}, run {'RULE': status}, missing {'RULE': [parameter]},
na_has [['RULE', text]], notes_has [['RULE', text]], approved bool, rules_not_run int, limits_has [['RULE|subject', text]]."""
import json, os
from ..fin import corpus_fin as KF, demo_fin as DF, policy as FP
from ..ingest import demo_setup as D, pipeline as P3, reconcile as R3
from ..ingest.golden_m3 import _world
from . import demo_det as DD, detect as DT, intake as DI, policy as DP

AS_OF = KF.AS_OF
THRESHOLD_RULES = ('R01', 'R02', 'R03', 'R04', 'R04B', 'R05', 'R06', 'R07', 'R08', 'R09', 'AGG', 'DLY', 'LAB', 'DEF')
COMP_H = ['supplier_id', 'evidence_type', 'expiry_date']
NOTICE_H = ['notice_id', 'project_id', 'notice_date', 'notice_type', 'linked_variation_id', 'description']
DELAY_H = ['event_id', 'project_id', 'activity_id', 'start_date', 'end_date', 'working_days', 'recorded_cause', 'holding_cost_rate_cents_per_day']
HIRE_H = ['hire_id', 'project_id', 'equipment', 'on_hire_date', 'off_hire_date', 'needed_until', 'rate_cents_per_day']
TS_H = ['entry_id', 'worker_pseudonym', 'project_id', 'work_package', 'work_date', 'ordinary_hours', 'overtime_hours', 'rate_cents_per_hour']
WO_H = ['project_id', 'work_package', 'week_start', 'quantity', 'unit']
DEF_H = ['defect_id', 'project_id', 'subcontractor', 'trade', 'raised_date', 'severity', 'rework_cost_cents', 'status']
QUOTE_H = ['quote_id', 'supplier_id', 'material_id', 'specification', 'issue_date', 'valid_until', 'unit_rate_cents', 'currency', 'fx_rate_used', 'fx_rate_date', 'freight_cents_per_unit',
           'incoterm_delivery_basis', 'lead_time_days', 'price_kind']
TABLES = dict(KF.TABLES)
TABLES.update({'compliance': ('det', 'TPL-BZ-COMPLIANCE', 'compliance', COMP_H, None), 'notices': ('det', 'TPL-BZ-NOTICES', 'commercial', NOTICE_H, None),
               'delays': ('det', 'TPL-BZ-DELAY-EVENTS', 'programme', DELAY_H, None), 'hires': ('det', 'TPL-BZ-PLANT-HIRE', 'plant', HIRE_H, None),
               'timesheets': ('det', 'TPL-BZ-TIMESHEETS', 'labour', TS_H, None), 'outputs': ('det', 'TPL-BZ-WORK-OUTPUT', 'labour', WO_H, None),
               'defects': ('det', 'TPL-BZ-DEFECTS', 'quality', DEF_H, None), 'quotes': ('m3', 'TPL-BZ-QUOTES', 'procurement', QUOTE_H, None)})
inv, po, bud, ctc, var, crn, BASE = KF.inv, KF.po, KF.bud, KF.ctc, KF.var, KF.crn, KF.BASE


def amd(i='AMD-1', po_id='PO-1', date='2026-08-01', delta='100000', ref='', reason='extra'):
    return [i, po_id, date, delta, ref, reason]


def comp(sup='SUP-001', typ='licence', expiry='2027-12-31'):
    return [sup, typ, expiry]


def notice(i='N-1', date='2026-06-01', typ='client_instruction', link='', desc='move wall'):
    return [i, 'PRJ-001', date, typ, link, desc]


def delay(i='D-1', act='A-1', start='2026-07-06', end='2026-07-21', rate='1000000'):
    return [i, 'PRJ-001', act, start, end, '10', 'crane', rate]


def hire(i='H-1', on='2026-01-01', off='', need='2026-03-31', rate='100000'):
    return [i, 'PRJ-001', 'excavator', on, off, need, rate]


def defect(i='DEF-1', sub='SUB-1', trade='waterproofing', raised='2026-05-01', cost='1000000'):
    return [i, 'PRJ-001', sub, trade, raised, 'major', cost, 'open']


def quote(i='Q-1', sup='SUP-001', material='MAT-X', rate='110000', cur='AUD', basis='delivered', freight='0', fx='', fxd=''):
    return [i, sup, material, 's', '2026-09-01', '2026-12-31', rate, cur, fx, fxd, freight, basis, '7', 'quote']


def lab_rows(recent_out=80, unit_last='m2', skip=None):
    """12 complete weeks of one package: 100 hours and 100 units a week, the last four at `recent_out` units."""
    import datetime
    ts, wo = [], []
    d = datetime.date(2026, 7, 6)
    for i in range(12):
        w = (d + datetime.timedelta(days=7 * i)).isoformat()
        if skip != i:
            ts.append(['T-%02d' % i, 'W-1', 'PRJ-001', 'WP-1', w, '100', '0', '5000'])
        wo.append(['PRJ-001', 'WP-1', w, str(recent_out if i >= 8 else 100), unit_last if i == 11 else 'm2'])
    return [('timesheets', ts), ('outputs', wo)]


class ReferenceWorld:
    """The APG reference world: in-memory ports, the real M3, M4 and M5 intake paths, the real stored detections."""
    def __init__(self, root, approved=True):
        self.root = root
        self.clock, self.prov, self.store, self.audit, who = _world()
        self.s = who('t1', 'zero_one', 'ann')
        self.owner = who('o1', 'zero_one', DD.DEMO_OWNER, DD.OWNER_ROLES)                       # APG-F67: approves the policies in person
        self.dreg = D.demo_register()
        self.reg = DT.det_registry()
        P3.ingest_file(self.s, self.clock, self._tpl('TPL-BZ-SUPPLIERS'), KF._csv(KF.SUP_H, [[a, b, ''] for a, b in KF.SUPPLIERS]), 'master', 'suppliers.csv', D.DEMO_POLICY)
        self.policy = self.dp = None
        self.set_policies(approved)

    def _tpl(self, name):
        for d in ('import_templates', 'ingest_templates', 'fin_templates', 'det_templates'):
            p = os.path.join(self.root, d, name + '.json')
            if os.path.exists(p):
                return json.load(open(p, encoding='utf-8'))
        raise FileNotFoundError(name)

    def deliver(self, table, rows, revision_field=None):
        kind, tid, src, header, rev = TABLES[table]
        data = KF._csv(header, rows)
        if kind == 'det':
            return DI.ingest_det_file(self.s, self.clock, self._tpl(tid), data, src, table + '.csv', None, revision_field or rev)
        if kind == 'fin':
            return KF.intake.ingest_fin_file(self.s, self.clock, self._tpl(tid), data, src, table + '.csv', DF.FIN_INTAKE_POLICY, revision_field or rev)
        return P3.ingest_file(self.s, self.clock, self._tpl(tid), data, src, table + '.csv', D.DEMO_POLICY, revision_field or rev)

    def reconcile(self, as_of):
        return R3.reconcile(self.s, self.dreg, as_of)

    def set_policies(self, approved=True, fin=None, rules=None):
        fv = 'P-%d' % (len(self.s.query(FP.POLICY_KIND)) + 1)
        self.policy = DF.install(self.s, self.clock, self.owner if approved else None, fv, **(fin or {}))
        base = DD.demo_det_policy()['rules']
        for k, v in (rules or {}).items():
            if v is None:
                base.pop(k, None)
            else:
                base[k] = v
        dv = 'D-%d' % (len(self.s.query(DP.POLICY_KIND)) + 1)
        self.dp = DD.install_det(self.s, self.clock, self.owner if approved else None, dv, rules=base)

    def detect(self, scope, as_of):
        if scope == 'tenant':
            return DT.run_tenant(self.s, self.reg, self.clock, as_of, self.dp['version'])['result']
        return DT.run_project(self.s, self.reg, self.clock, scope, as_of, self.policy['version'], self.dp['version'])['result']


def cases():
    C = []

    def case(cid, desc, expect, deliver=(), drop=(), fin=None, rules=None, scope='PRJ-001', as_of=AS_OF, approved=True):
        C.append(dict(id=cid, desc=desc, deliver=list(deliver), drop=list(drop), fin=fin, rules=rules, scope=scope, as_of=as_of, approved=approved, expect=expect))
    # ---- the base and the policy
    case('B01', 'the base builder raises nothing under the demonstration policy', dict(only=[], rules_not_run=0, approved=True))
    case('B02', 'an unapproved policy still produces the signal and says it is unapproved', dict(raised=['R01|CC-01'], approved=False), [('invoices', [inv('INV-2', ex='2250001')])], approved=False)
    case('B03', 'a policy with no rule entries runs no project rule and says so for every one of them', dict(only=[], rules_not_run=12, run={r: 'not_configured' for r in THRESHOLD_RULES if r not in ('R06', 'R07')}),
         rules={r: None for r in THRESHOLD_RULES})
    case('B04', 'the same at tenant scope: the two tenant rules say they did not run', dict(only=[], rules_not_run=2, run={'R06': 'not_configured', 'R07': 'not_configured'}),
         [('compliance', [comp(expiry='2026-09-01')])], rules={r: None for r in THRESHOLD_RULES}, scope='tenant')
    # ---- R01 actual cost above budget
    case('C01', 'one cent over the tolerance is a finding (exact comparison)', dict(raised=['R01|CC-01'], gross={'R01|CC-01': 250001}), [('invoices', [inv('INV-2', ex='2250001')])])
    case('C02', 'exactly at the tolerance is silent', dict(only=[], run={'R01': 'evaluated'}), [('invoices', [inv('INV-2', ex='2250000')])])
    case('C03', 'a credit note brings a code back under the tolerance', dict(only=[]), [('invoices', [inv('INV-2', ex='3000000')]), ('credits', [crn(against='INV-2', ex='2000000', gst='0')])])
    case('C04', 'cost on another project is not counted', dict(only=[]), [('projects', [['PRJ-002', 'P2', '1', '2026-01-01', '2027-01-01']]), ('invoices', [inv('INV-2', project='PRJ-002', ex='9000000')])])
    case('C05', 'a large invoice held for an unknown supplier is left out and reported as a held-record signal, not counted as cost', dict(only=[], raised=['D01|actual_cost|held_records']),
         [('invoices', [inv('INV-2', sup='SYN Unknown Supplier', ex='9000000')])])
    case('C06', 'the same invoice delivered twice is not counted twice', dict(only=[]), [('invoices', [inv('INV-2', sin='SI-V-1', ex='3000000')])])
    case('C07', 'an invoice dated after the as-of date is not counted', dict(only=[]), [('invoices', [inv('INV-2', date='2026-10-20', ex='9000000')])])
    case('C08', 'a zero budget is not assessed and is not divided by', dict(only=[], na_has=[['R01', 'BUDGET_NOT_POSITIVE']]), [('budgets', [bud(cc='CC-09', cents='0')]), ('invoices', [inv('INV-2', cc='CC-09', ex='100')])])
    case('C09', 'a missing tolerance means the rule did not run, naming the missing parameter', dict(only=[], run={'R01': 'not_configured'}, missing={'R01': ['tolerance_bps']}),
         [('invoices', [inv('INV-2', ex='9000000')])], rules={'R01': None})
    case('C10', 'a rule switched off in the policy is recorded as switched off', dict(only=[], run={'R01': 'disabled'}), [('invoices', [inv('INV-2', ex='9000000')])], rules={'R01': {'enabled': False}})
    case('C11', 'a cost scope that is not configured makes the rule unassessable, not clean', dict(only=[], run={'R01': 'cannot_assess'}), [('invoices', [inv('INV-2', ex='9000000')])], fin={'cost_scope': None})
    # ---- R02 amendment with no approved change
    pos = ('pos', [po('PO-1', amount='1000000')])
    case('C12', 'an amendment with no change reference is flagged', dict(raised=['R02|AMD-1'], gross={'R02|AMD-1': 100000}), [pos, ('amendments', [amd()])])
    case('C13', 'an amendment linked to an approved variation is silent', dict(lacks=['R02|AMD-1'], silent=['R02']), [pos, ('variations', [var('VAR-1', status='approved')]), ('amendments', [amd(ref='VAR-1')])])
    case('C14', 'an amendment linked to a variation that is only submitted is flagged', dict(raised=['R02|AMD-1']), [pos, ('variations', [var('VAR-1', status='submitted')]), ('amendments', [amd(ref='VAR-1')])])
    case('C15', 'an amendment naming a variation that does not exist is flagged', dict(raised=['R02|AMD-1']), [pos, ('amendments', [amd(ref='VAR-NOPE')])])
    case('C16', 'an amendment dated after the as-of date is not flagged yet', dict(silent=['R02']), [pos, ('amendments', [amd(date='2026-10-20')])])
    # ---- R03 invoiced above order
    case('C17', 'invoiced 7.6 percent over the order is flagged', dict(raised=['R03|PO-1'], gross={'R03|PO-1': 76000}), [pos, ('invoices', [inv('INV-2', po='PO-1', ex='1076000')])])
    case('C18', 'exactly 1 percent over is silent and one cent more is flagged', dict(silent=['R03']), [pos, ('invoices', [inv('INV-2', po='PO-1', ex='1010000')])])
    case('C19', 'one cent beyond 1 percent is flagged', dict(raised=['R03|PO-1']), [pos, ('invoices', [inv('INV-2', po='PO-1', ex='1010001')])])
    case('C20', 'an approved amendment raises the commitment before the test', dict(silent=['R03']), [pos, ('variations', [var('VAR-1', status='approved')]), ('amendments', [amd(ref='VAR-1', delta='100000')]),
                                                                                                         ('invoices', [inv('INV-2', po='PO-1', ex='1100000')])])
    case('C21', 'a held invoice on the order is listed as not assessed, not silently added', dict(na_has=[['R03', 'held']]), [pos, ('invoices', [inv('INV-2', po='PO-1', ex='1100000'), inv('INV-3', sin='SI-009', po='PO-1', ex='10')]),
                                                                                                                      ('invoices', [inv('INV-4', sin='SI-009', po='PO-1', ex='20')])])
    # ---- R04 / R04B
    case('C22', 'an unpriced submitted variation open for months is flagged without an amount', dict(raised=['R04|VAR-2'], unquantified=['R04|VAR-2']), [('variations', [var('VAR-2', status='submitted', value='', raised='2026-02-10')])])
    case('C23', 'sixty days is not beyond sixty days; sixty-one is', dict(silent=['R04']), [('variations', [var('VAR-2', status='submitted', raised='2026-08-01')])])
    case('C24', 'sixty-one days is flagged', dict(raised=['R04|VAR-2']), [('variations', [var('VAR-2', status='submitted', raised='2026-07-31')])])
    case('C25', 'a status the policy does not map is listed, not guessed', dict(lacks=['R04|VAR-2'], na_has=[['R04', 'VAR-2']]), [('variations', [var('VAR-2', status='pending-ish', raised='2026-02-10')])])
    case('C26', 'without the status map the rule cannot assess', dict(run={'R04': 'cannot_assess'}), [('variations', [var('VAR-2', status='submitted', raised='2026-02-10')])], fin={'variation_status_map': None})
    case('C27', 'an old client instruction with no variation is flagged', dict(raised=['R04B|N-1'], unquantified=['R04B|N-1']), [('notices', [notice()])])
    case('C28', 'an instruction linked to a stored variation is silent', dict(silent=['R04B']), [('variations', [var('VAR-1', status='submitted')]), ('notices', [notice(link='VAR-1')])])
    case('C29', 'an instruction naming a variation that is not stored is a data-quality signal', dict(raised=['R04B|N-1'], subtype={'R04B|N-1': 'instruction_link_unresolved'}), [('notices', [notice(link='VAR-NOPE')])])
    case('C30', 'a notice text that looks like a spreadsheet formula changes nothing and is only data', dict(raised=['R04B|N-1']), [('notices', [notice(desc='=HYPERLINK("http://x","y")')])])
    # ---- R05 retention
    case('C31', 'retention past its release date with nothing released and no reason is flagged', dict(raised=['R05|PRJ-001'], gross={'R05|PRJ-001': 500000}),
         [('retention', [['PRJ-001', '500000', '2026-08-01', '', '']])], drop=['retention'])
    case('C32', 'a recorded hold reason makes it silent', dict(silent=['R05']), [('retention', [['PRJ-001', '500000', '2026-08-01', '', 'defects period']])], drop=['retention'])
    case('C33', 'a recorded release makes it silent', dict(silent=['R05']), [('retention', [['PRJ-001', '500000', '2026-08-01', '2026-08-20', '']])], drop=['retention'])
    case('C34', 'no retention ledger is not assessed, not called clean', dict(na_has=[['R05', 'retention']]), drop=['retention'])
    # ---- R06 / R07 tenant scope
    case('C35', 'expired supplier evidence is flagged at tenant scope', dict(raised=['R06|SUP-001|licence'], subtype={'R06|SUP-001|licence': 'compliance_expired'}), [('compliance', [comp(expiry='2026-09-01')])], scope='tenant')
    case('C36', 'evidence expiring in 30 days is flagged and in 31 days is silent', dict(raised=['R06|SUP-001|licence']), [('compliance', [comp(expiry='2026-10-30')])], scope='tenant')
    case('C37', 'evidence expiring in 31 days is silent', dict(silent=['R06']), [('compliance', [comp(expiry='2026-10-31')])], scope='tenant')
    pair = {'R07': {'tolerance_bps': 100, 'pairs': [{'quote': 'Q-1', 'reference_kind': 'quote', 'reference': 'Q-2'}]}}
    case('C38', 'a quote above its declared reference is flagged per unit and never given a total', dict(raised=['R07|Q-1>quote:Q-2'], unquantified=['R07|Q-1>quote:Q-2']),
         [('quotes', [quote('Q-1', rate='110000'), quote('Q-2', sup='SUP-002', rate='100000')])], rules=pair, scope='tenant')
    case('C39', 'an ex-works reference is landed with its freight before the comparison', dict(silent=['R07']), [('quotes', [quote('Q-1', rate='100000'), quote('Q-2', sup='SUP-002', rate='95000', basis='ex-works', freight='5000')])],
         rules=pair, scope='tenant')
    case('C40', 'a foreign-currency quote is not converted here and is listed as not assessed', dict(lacks=['R07|Q-1>quote:Q-2'], na_has=[['R07', 'M6']]),
         [('quotes', [quote('Q-1', rate='110000', cur='USD', fx='1.5', fxd='2026-09-01'), quote('Q-2', sup='SUP-002', rate='100000')])], rules=pair, scope='tenant')
    case('C41', 'a pair naming a quote that is not stored is not assessed', dict(silent=['R07'], na_has=[['R07', 'Q-2']]), [('quotes', [quote('Q-1', rate='110000')])], rules=pair, scope='tenant')
    case('C42', 'different materials in a declared pair are not compared', dict(silent=['R07'], na_has=[['R07', 'different materials']]),
         [('quotes', [quote('Q-1', rate='110000'), quote('Q-2', sup='SUP-002', material='MAT-Y', rate='100000')])], rules=pair, scope='tenant')
    # ---- R08 hire, R09 forecast movement
    case('C43', 'hire long past the need date is flagged with days times the daily rate', dict(raised=['R08|H-1'], gross={'R08|H-1': 18300000}), [('hires', [hire()])])
    case('C44', 'no evidenced need date is not assessed', dict(silent=['R08'], na_has=[['R08', 'need']]), [('hires', [hire(need='')])])
    case('C45', 'off hire before the need date is silent', dict(silent=['R08']), [('hires', [hire(off='2026-03-20')])])
    case('C46', 'a large forecast increase with no recorded reason is flagged', dict(raised=['R09|CC-03|F-8>F-9'], gross={'R09|CC-03|F-8>F-9': 31000000}),
         [('ctcs', [ctc(cc='CC-03', version='F-8', date='2026-08-31', cents='5000000'), ctc(cc='CC-03', version='F-9', date='2026-09-30', cents='36000000', reason='')])])
    case('C47', 'the same movement with a recorded reason is silent', dict(silent=['R09']), [('ctcs', [ctc(cc='CC-03', version='F-8', date='2026-08-31', cents='5000000'), ctc(cc='CC-03', version='F-9', date='2026-09-30', cents='36000000', reason='scope added')])])
    case('C48', 'an unexplained reduction is a data-quality signal and not a saving', dict(raised=['R09|CC-03|F-8>F-9'], unquantified=['R09|CC-03|F-8>F-9'], subtype={'R09|CC-03|F-8>F-9': 'forecast_movement_unexplained'}),
         [('ctcs', [ctc(cc='CC-03', version='F-8', date='2026-08-31', cents='9000000'), ctc(cc='CC-03', version='F-9', date='2026-09-30', cents='1000000', reason='')])])
    # ---- AGG split orders
    def three(d1, d2, d3, a=('9282000', '9044000', '8806000'), cc='CC-01'):
        return ('pos', [po('PO-1', cc=cc, date=d1, amount=a[0]), po('PO-2', cc=cc, date=d2, amount=a[1]), po('PO-3', cc=cc, date=d3, amount=a[2])])
    case('C49', 'three orders inside the window that reach the threshold together are flagged once', dict(raised=['AGG|PRJ-001|SUP-001|MAT-X|CC-01|2026-08-03'], unquantified=['AGG|PRJ-001|SUP-001|MAT-X|CC-01|2026-08-03']),
         [three('2026-08-03', '2026-08-09', '2026-08-14')])
    case('C50', 'the same three orders sixty days apart are not aggregated (known limit: chain splitting, OQ-A1-7)', dict(silent=['AGG']), [three('2026-03-02', '2026-05-04', '2026-07-06')])
    case('C51', 'a cluster containing one order at or above the single-order threshold is a material order, not a split', dict(silent=['AGG'], notes_has=[['AGG', 'CLUSTER_WITH_SINGLE_MATERIAL_ORDER']]),
         [('pos', [po('PO-1', date='2026-07-01', amount='25000000'), po('PO-2', date='2026-07-05', amount='100')])])
    case('C52', 'an order with no cost code cannot be grouped and is listed, not forced into a group', dict(raised=['AGG|PRJ-001|SUP-001|MAT-X|CC-01|2026-07-01'], na_has=[['AGG', 'PO-3']]),
         [('pos', [po('PO-1', date='2026-07-01', amount='13000000'), po('PO-2', date='2026-07-02', amount='13000000'), po('PO-3', cc='', date='2026-07-03', amount='13000000')])])
    case('C53', 'without the aggregation setting the rule names the open decision and does not run', dict(run={'AGG': 'not_configured'}), [three('2026-08-03', '2026-08-09', '2026-08-14')], rules={'AGG': None})
    # ---- DLY / LAB / DEF
    case('C54', 'two overlapping delays are reported once, never added, never priced', dict(raised=['DLY|D-1|D-2'], unquantified=['DLY|D-1|D-2']),
         [('delays', [delay('D-1', start='2026-07-06', end='2026-07-21'), delay('D-2', start='2026-07-15', end='2026-07-30', rate='500000')])])
    case('C55', 'delays that do not share a day are silent', dict(silent=['DLY']), [('delays', [delay('D-1', start='2026-07-06', end='2026-07-21'), delay('D-2', start='2026-07-22', end='2026-07-30')])])
    case('C56', 'a delay with no end date is listed as not assessed', dict(silent=['DLY'], na_has=[['DLY', 'D-2']]), [('delays', [delay('D-1'), delay('D-2', end='')])])
    case('C57', 'output per hour falling by 20 percent over twelve complete weeks is flagged at package level', dict(raised=['LAB|WP-1'], subtype={'LAB|WP-1': 'output_per_hour_falling'}), lab_rows(80))
    case('C58', 'a fall of exactly the threshold (10 percent) is flagged and 9 percent is silent', dict(raised=['LAB|WP-1']), lab_rows(90))
    case('C59', 'a 9 percent fall is silent', dict(silent=['LAB']), lab_rows(91))
    case('C60', 'a week with no recorded hours stops the comparison and says so', dict(silent=['LAB'], na_has=[['LAB', 'complete weeks']]), lab_rows(80, skip=11))
    case('C61', 'a change of unit inside the windows stops the comparison', dict(silent=['LAB'], na_has=[['LAB', 'unit of measure']]), lab_rows(80, unit_last='m3'))
    case('C62', 'an earlier as-of date has too few complete weeks and says so', dict(silent=['LAB'], na_has=[['LAB', 'complete weeks']]), lab_rows(80), as_of='2026-08-14')
    case('C63', 'three defects of one subcontractor and trade with growing rework cost are flagged without concluding responsibility', dict(raised=['DEF|SUB-1|waterproofing'], limits_has=[['DEF|SUB-1|waterproofing', 'responsibility']]),
         [('defects', [defect('DEF-1', raised='2026-05-01', cost='1000000'), defect('DEF-2', raised='2026-06-01', cost='1500000'), defect('DEF-3', raised='2026-07-01', cost='2500000')])])
    case('C64', 'two defects are below the configured count', dict(silent=['DEF']), [('defects', [defect('DEF-1'), defect('DEF-2', raised='2026-06-01')])])
    case('C65', 'defects of different trades do not group', dict(silent=['DEF']), [('defects', [defect('DEF-1'), defect('DEF-2', raised='2026-06-01', trade='roofing'), defect('DEF-3', raised='2026-07-01', trade='tiling')])])
    # ---- faulty inputs at the door
    case('F01', 'a negative rework cost is rejected at intake and no defect pattern is formed from it', dict(silent=['DEF']), [('defects', [defect('DEF-1'), defect('DEF-2', raised='2026-06-01', cost='-5'), defect('DEF-3', raised='2026-07-01')])])
    case('F02', 'a hire rate of zero is rejected at intake and raises nothing', dict(silent=['R08']), [('hires', [hire(rate='0')])])
    case('F03', 'a delay whose end is before its start is not compared', dict(silent=['DLY']), [('delays', [delay('D-1', start='2026-07-21', end='2026-07-06'), delay('D-2', start='2026-07-10', end='2026-07-30')])])
    case('F04', 'an impossible expiry date is rejected at intake and no signal is made from it', dict(silent=['R06']), [('compliance', [comp(expiry='2026-13-45')])], scope='tenant')
    case('F05', 'a defect dated after the as-of date is outside the period, not an error and not counted', dict(silent=['DEF']), [('defects', [defect('DEF-1'), defect('DEF-2', raised='2026-06-01'), defect('DEF-3', raised='2026-12-01')])])
    case('F06', 'an invoice on a project that does not exist is not read into any project', dict(only=[]), [('invoices', [inv('INV-2', project='PRJ-404', ex='9000000')])])
    return C


def _key(s):
    return s['rule']['id'].replace('DET-', '') + '|' + s['subject']


def check_case(case, world_factory):
    """-> (ok, message)."""
    w = world_factory(case.get('approved', True))
    drop = set(case.get('drop', ()))
    for table, rows in BASE:
        if table not in drop:
            w.deliver(table, rows)
    for table, rows in case.get('deliver', ()):
        w.deliver(table, rows)
    w.set_policies(case.get('approved', True), case.get('fin'), case.get('rules'))
    w.reconcile(case.get('as_of', AS_OF))
    try:
        r = w.detect(case.get('scope', 'PRJ-001'), case.get('as_of', AS_OF))
    except Exception as ex:                                                 # noqa: BLE001 - a case may require a refusal
        return False, 'raised %s: %s' % (type(ex).__name__, ex)
    e = case['expect']
    sigs = {_key(s): s for s in r['signals']}
    threshold = {k for k, s in sigs.items() if k.split('|')[0] in THRESHOLD_RULES}
    if 'only' in e and threshold != set(e['only']) | (set(e.get('raised', ())) & threshold):
        return False, 'threshold-rule signals %s (wanted %s)' % (sorted(threshold), sorted(set(e['only']) | set(e.get('raised', ()))))
    for k in e.get('raised', ()):
        if k not in sigs:
            return False, 'signal %s missing; raised %s' % (k, sorted(sigs))
    for k in e.get('lacks', ()):
        if k in sigs:
            return False, 'signal %s must not be raised' % k
    for rid in e.get('silent', ()):
        if any(k.split('|')[0] == rid for k in sigs):
            return False, 'rule %s must be silent but raised %s' % (rid, [k for k in sigs if k.split('|')[0] == rid])
        if r['rule_runs'].get(rid, {}).get('status') != 'evaluated':
            return False, 'rule %s was silent only because it did not run (%s)' % (rid, r['rule_runs'].get(rid, {}).get('status'))
    for k, c in e.get('gross', {}).items():
        if k not in sigs or sigs[k]['quantification']['gross_cents'] != c:
            return False, 'gross for %s is %s (wanted %s)' % (k, sigs.get(k, {}).get('quantification', {}).get('gross_cents'), c)
    for k in e.get('unquantified', ()):
        if k not in sigs or sigs[k]['quantification']['status'] != 'unquantified' or not sigs[k]['quantification']['reason']:
            return False, '%s must be unquantified with a reason' % k
    for k, t in e.get('subtype', {}).items():
        if k not in sigs or sigs[k]['taxonomy']['subtype'] != t:
            return False, 'subtype of %s is %s (wanted %s)' % (k, sigs.get(k, {}).get('taxonomy', {}).get('subtype'), t)
    for k, t in e.get('severity', {}).items():
        if k not in sigs or sigs[k]['priority']['severity'] != t:
            return False, 'severity of %s is %s (wanted %s)' % (k, sigs.get(k, {}).get('priority', {}).get('severity'), t)
    for rid, st in e.get('run', {}).items():
        if r['rule_runs'].get(rid, {}).get('status') != st:
            return False, 'run %s is %s (wanted %s)' % (rid, r['rule_runs'].get(rid, {}).get('status'), st)
    for rid, m in e.get('missing', {}).items():
        if r['rule_runs'][rid]['missing_parameters'] != m:
            return False, 'missing parameters of %s are %s (wanted %s)' % (rid, r['rule_runs'][rid]['missing_parameters'], m)
    for rid, t in e.get('na_has', ()):
        if not any(t in (n['subject'] + ' ' + n['why']) for n in r['rule_runs'][rid]['not_assessed']):
            return False, 'not-assessed entry %r missing for %s: %s' % (t, rid, r['rule_runs'][rid]['not_assessed'][:3])
    for rid, t in e.get('notes_has', ()):
        if not any(t in n for n in r['rule_runs'][rid]['notes']):
            return False, 'note %r missing for %s: %s' % (t, rid, r['rule_runs'][rid]['notes'][:3])
    for k, t in e.get('limits_has', ()):
        if k not in sigs or not any(t in x for x in sigs[k]['data_limits']):
            return False, 'data limit %r missing from %s' % (t, k)
    if 'approved' in e and r['det_policy']['approved'] != e['approved']:
        return False, 'policy approved flag is %s' % r['det_policy']['approved']
    if 'rules_not_run' in e and r['counts']['rules_not_run'] != e['rules_not_run']:
        return False, 'rules not run %s (wanted %s)' % (r['counts']['rules_not_run'], e['rules_not_run'])
    return True, ''
