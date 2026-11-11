"""Boundary and guard tests added after the first M4 mutation run (83 of 672 one-place changes were not noticed).  Each test below is aimed at a specific kind of gap the run showed:
a date exactly on the cut-off, a limit exactly at its edge, a guard that nothing tested on its own, a record that has no reconciliation state yet, and a value that was only ever
checked in combination with others.  Everything is synthetic."""
import copy, unittest
from . import _path                                         # noqa: F401
from .helpers_fin import Mini, base_world, inv, bud, ctc, po, var, AS_OF, CTC_H, CON_H, AMD_H, CRN_H, RET_H, SEC_H, FAC_H
from .test_fin_forecast import world, fc
from .test_fin_bridge_book import project_world, run_fc, bridge
from .helpers_ingest import csvb
from apg import repro
from apg.ports import ConflictError
from apg.fin import figure, fmath, policy as P, snap, costs, bridge as B, calc_records as C, forecast_book as FB, intake, cash_states as CS
from apg.fin import policy as POL
from apg.fin.figure import FigureBuilder, FigureError, AUTH, PROV, CANT
from apg.fin.demo_fin import demo_policy


def _b(approved=True):
    return FigureBuilder('x', 'v', 'f', 1, {'project': 'P'}, AS_OF, {'version': 'V', '_approved': approved})


def facts(m, project='PRJ-001', as_of=AS_OF):
    from apg.fin import gather
    from apg.repro import _load
    refs, params = gather.gather(m.s, project, as_of, m.policy['version'])
    return snap.Facts(_load(m.s, refs), params)


def excl(f, ref):
    return [e for e in f['excluded'] if e['ref'] == ref]


class TestFigureGuards(unittest.TestCase):
    def test_a_required_component_that_cannot_be_assessed_refuses_any_value(self):
        child = _b().cannot('NO_DATA')
        for kw in ({'cents': 5}, {'bps': 5}):
            b = _b(); b.child('c', child)
            with self.assertRaises(FigureError):
                b.finish(**kw)

    def test_an_optional_component_that_cannot_be_assessed_only_lowers_the_parent_to_provisional(self):
        b = _b(); b.child('c', _b().cannot('NO_DATA'), required=False)
        f = b.finish(cents=5)
        self.assertEqual((f['state'], f['value']['cents']), (PROV, 5))
        self.assertIn('COMPONENT_CANNOT_ASSESS:c', f['reasons'])

    def test_an_optional_authoritative_component_does_not_lower_the_parent(self):
        b = _b(); b.child('c', _b().finish(cents=1), required=False)
        self.assertEqual(b.finish(cents=2)['state'], AUTH)

    def test_the_policy_version_and_approval_are_recorded_on_the_figure(self):
        self.assertEqual(_b().finish(cents=1)['policy'], {'version': 'V', 'approved': True})
        self.assertEqual(_b(approved=False).finish(cents=1)['policy'], {'version': 'V', 'approved': False})

    def test_a_figure_with_both_values_is_refused_at_build_and_at_validation(self):
        with self.assertRaises(FigureError):
            _b().finish(cents=1, bps=1)
        f = _b().finish(cents=1)
        f['value']['bps'] = 5
        with self.assertRaises(FigureError):
            figure.validate_figure(f)

    def test_validation_refuses_each_breach_on_its_own(self):
        good = _b().finish(cents=1)
        prov = _b(approved=False).finish(cents=1)
        figure.validate_figure(good); figure.validate_figure(prov)
        f = copy.deepcopy(prov); f['state'] = 'bogus'
        with self.assertRaises(FigureError):
            figure.validate_figure(f)
        f = copy.deepcopy(prov); f['excluded'].append({'ref': 'x/1', 'class': 'bogus', 'codes': [], 'amount_cents': None})
        with self.assertRaises(FigureError):
            figure.validate_figure(f)
        f = copy.deepcopy(good); f['components']['c'] = copy.deepcopy(prov)
        with self.assertRaises(FigureError):
            figure.validate_figure(f)

    def test_worst_refuses_an_unknown_state(self):
        with self.assertRaises(FigureError):
            figure.worst([AUTH, 'bogus'])
        self.assertEqual(figure.worst([AUTH, PROV]), PROV)


class TestEdgesOfArithmeticAndPolicy(unittest.TestCase):
    def test_a_date_that_is_not_text_or_does_not_round_trip_is_a_value_error(self):
        for bad in (None, 20260930, '2026-W01-1', '2026-9-30', '20260930', '2026-02-30'):
            with self.assertRaises(ValueError, msg=repr(bad)):
                fmath.parse_date(bad)

    def test_the_funded_share_proxy_rate_and_freshness_limits_accept_their_edges_and_nothing_beyond(self):
        car = dict(eligibility='as_of_to_release_due_date', rate_source='declared_proxy', proxy_rate_bps=0, day_count_basis=365, funded_share_bps=10000)
        P.new_policy('V1', 'p', carrying=car, freshness_days={'forecast': 0})
        P.new_policy('V2', 'p', carrying=dict(car, funded_share_bps=0))
        for bad in (dict(car, funded_share_bps=10001), dict(car, funded_share_bps=-1), dict(car, proxy_rate_bps=-1)):
            with self.assertRaises(P.PolicyError):
                P.new_policy('V3', 'p', carrying=bad)
        with self.assertRaises(P.PolicyError):
            P.new_policy('V4', 'p', freshness_days={'forecast': -1})

    def test_an_approval_needs_four_non_empty_text_fields(self):
        p = P.new_policy('V1', 'proposer')
        ok = {'approver': 'a', 'role': 'policy_owner', 'kind': 'human', 'date': '2026-09-30'}
        self.assertEqual(P.validate_policy(dict(p, approvals=[ok])), [])
        for field, bad in (('approver', 5), ('approver', ''), ('role', ''), ('date', None)):
            self.assertIn('approvals', P.validate_policy(dict(p, approvals=[dict(ok, **{field: bad})])), (field, bad))

    def test_new_policy_raises_policy_error_on_a_malformed_policy(self):
        with self.assertRaises(P.PolicyError):
            P.new_policy('V1', 'p', ctc_method='declared')


class TestAttributionRule(unittest.TestCase):
    INV = {('ap_invoice', 'INV-1'): {'fields': {'project_ref': 'PRJ-1'}}, ('ap_invoice', 'INV-2'): {'fields': {'project_ref': 'PRJ-2'}}}
    lookup = staticmethod(lambda kind, key: TestAttributionRule.INV.get((kind, key)))

    def test_a_credit_note_follows_its_one_invoice(self):
        self.assertEqual(snap.project_of('credit_note', {'fields': {'against_invoice_ref': 'INV-1'}}, self.lookup), 'PRJ-1')

    def test_a_conflict_marker_naming_two_invoices_is_unattributed_even_when_both_invoices_exist(self):
        marker = {'conflict': {'contenders': [{'fields': {'against_invoice_ref': 'INV-1'}}, {'fields': {'against_invoice_ref': 'INV-2'}}]}}
        self.assertIsNone(snap.project_of('credit_note', marker, self.lookup))

    def test_without_a_lookup_or_a_link_a_credit_note_is_unattributed(self):
        self.assertIsNone(snap.project_of('credit_note', {'fields': {'against_invoice_ref': 'INV-1'}}, None))
        self.assertIsNone(snap.project_of('credit_note', {'fields': {}}, self.lookup))
        self.assertIsNone(snap.project_of('po_amendment', {'fields': {'purchase_order_ref': 'PO-404'}}, self.lookup))

    def test_of_project_uses_the_project_it_is_given_before_the_calculation_s_own(self):
        inputs = {'ap_invoice/A': {'fields': {'project_ref': 'PRJ-1'}}, 'ap_invoice/B': {'fields': {'project_ref': 'PRJ-2'}}, 'ap_invoice/C': {'fields': {}}}
        F = snap.Facts(inputs, {'project': 'PRJ-1'})
        self.assertEqual(F.of_project('ap_invoice'), (['A'], ['C']))
        self.assertEqual(F.of_project('ap_invoice', 'PRJ-2'), (['B'], ['C']))


class TestIntakeEdges(unittest.TestCase):
    def setUp(self):
        self.m = Mini(with_suppliers=False)

    def test_an_optional_value_that_is_present_but_unreadable_holds_the_record(self):
        r = self.m.contracts(['PRJ-001', '10000000', 'abc'])
        self.assertEqual(r['counts']['held_at_intake'], 1)
        p = self.m.s.get('contract', 'PRJ-001').payload
        self.assertEqual(p['intrinsic']['pending'], ['INVALID_VALUE:approved_variations_cents:INVALID_MONEY'])
        self.assertFalse(intake.usable(p))

    def test_a_revision_label_that_cannot_be_read_is_warned_only_when_there_is_one(self):
        def warns(row, field):
            return self.m.fin('TPL-BZ-CTC-FORECASTS', csvb(CTC_H, [row]), 'job_costing', revision_field=field)['results'][0]['warnings']
        self.assertEqual(warns(ctc(cc='CC-01', version='F-1'), 'forecast_version'), ['REVISION_UNPARSED'])                 # text that is not a revision number
        self.assertEqual(warns(ctc(cc='CC-02', version='F-1'), 'cost_to_complete_cents'), [])                              # a whole number is a revision
        self.assertNotIn('REVISION_UNPARSED', warns(ctc(cc='CC-03', version='F-1', reason=''), 'movement_reason_text'))    # nothing there to read

    def test_the_same_version_delivered_again_into_a_conflict_is_not_added_a_second_time(self):
        self.m.contracts(['PRJ-001', '10000000', '0'])
        self.m.contracts(['PRJ-001', '11000000', '0'])                                                                        # same key, different content, no revision -> conflict marker
        self.assertEqual(len(self.m.s.get('contract', 'PRJ-001').payload['conflict']['contenders']), 2)
        self.m.contracts(['PRJ-001', '10000000', '0'], ['PRJ-002', '5', '0'])                                                  # a new file that repeats the first version
        self.assertEqual(len(self.m.s.get('contract', 'PRJ-001').payload['conflict']['contenders']), 2)
        self.m.contracts(['PRJ-001', '12000000', '0'], ['PRJ-003', '5', '0'])                                                  # a genuinely third version is added
        self.assertEqual(len(self.m.s.get('contract', 'PRJ-001').payload['conflict']['contenders']), 3)

    def test_a_refused_file_is_audited_under_its_own_name_or_a_generic_one(self):
        self.m.fin('TPL-BZ-CONTRACTS', b'wrong,header\n1,2\n', 'commercial', name='bad.csv')
        self.assertEqual(self.m.w.audit.read(self.m.s.ctx)[-1].resource, 'bad.csv')
        self.m.fin('TPL-BZ-CONTRACTS', b'wrong,header\n1,3\n', 'commercial', name='')
        self.assertEqual(self.m.w.audit.read(self.m.s.ctx)[-1].resource, 'file')

    def test_a_write_that_loses_a_race_is_reported_and_nothing_is_recorded_as_ingested(self):
        def lose(ops):
            raise ConflictError('changed while the file was being processed')
        self.m.s.atomic = lose
        with self.assertRaises(ConflictError):
            self.m.contracts(['PRJ-001', '10000000', '0'])
        events = [e.event_type for e in self.m.w.audit.read(self.m.s.ctx)]
        self.assertEqual(events[-1], 'ingest.conflict_retry')
        self.assertNotIn('ingest.file_ingested', events)



def refs(f, cls=None):
    return sorted(e['ref'] for e in f['excluded'] if cls is None or e['class'] == cls)


def codes_of(f, ref):
    return [e['codes'] for e in f['excluded'] if e['ref'] == ref]


class TestCreditDatesAndOrphans(unittest.TestCase):
    def test_a_credit_dated_on_the_cut_off_day_is_applied_and_the_next_day_is_not(self):
        m = Mini()
        m.invoices(inv('INV-A', ex='1000000'))
        m.credits(['CRN-1', 'SUP-001', 'INV-A', '2026-09-30', '250000', '0'])
        m.reconcile()
        f = m.fig('fin.actual_cost', as_of='2026-09-30')
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 750000))
        self.assertEqual([c['ref'] for c in f['applied']['credits']], ['credit_note/CRN-1'])
        f = m.fig('fin.actual_cost', as_of='2026-09-29')
        self.assertEqual(f['value']['cents'], 1000000)
        self.assertEqual(codes_of(f, 'credit_note/CRN-1'), [['CREDIT_DATED_AFTER_CUTOFF:2026-09-30']])        # the date is quoted in the reason

    def test_a_credit_whose_invoice_is_outside_the_period_says_so(self):
        m = Mini()
        m.invoices(inv('INV-A', date='2026-10-01', ex='1000000'))
        m.credits(['CRN-1', 'SUP-001', 'INV-A', '2026-09-15', '250000', '0'])
        m.reconcile('2026-10-05')
        f = m.fig('fin.actual_cost', as_of='2026-09-30')
        self.assertEqual(refs(f, 'after_cutoff'), ['ap_invoice/INV-A', 'credit_note/CRN-1'])
        self.assertEqual(codes_of(f, 'credit_note/CRN-1'), [['TARGET_INVOICE_AFTER_CUTOFF:INV-A']])

    def test_a_credit_against_an_invoice_that_is_held_is_not_counted_and_is_not_called_after_the_cut_off(self):
        m = Mini()
        m.invoices(inv('INV-A', supplier='SUP-999', ex='1000000'))                       # supplier unresolved, so the invoice is held
        m.credits(['CRN-1', 'SUP-001', 'INV-A', '2026-07-25', '250000', '0'])
        m.reconcile()
        f = m.fig('fin.actual_cost')
        self.assertEqual(f['value']['cents'], 0)
        self.assertEqual([(e['class'], e['codes']) for e in f['excluded'] if e['ref'] == 'credit_note/CRN-1'], [('not_counted', ['TARGET_INVOICE_NOT_COUNTED:INV-A:held'])])

    def test_records_that_were_never_reconciled_are_held_not_a_crash(self):
        m = Mini()
        m.invoices(inv('INV-A', ex='1000000'))
        m.credits(['CRN-1', 'SUP-001', 'INV-A', '2026-07-25', '250000', '0'])
        f = m.fig('fin.actual_cost')                                                   # nothing has been reconciled yet
        self.assertEqual(f['value']['cents'], 0)
        self.assertEqual(codes_of(f, 'ap_invoice/INV-A'), [['NO_RECONCILIATION_STATE']])
        self.assertEqual(f['state'], PROV)

    def test_the_count_of_counted_invoices_follows_the_cost_code_asked_for(self):
        m = Mini()
        m.invoices(inv('INV-1', ex='100', cc='CC-01'), inv('INV-2', sin='S2', ex='250', cc='CC-02'), inv('INV-3', sin='S3', ex='7', cc='CC-02'),
                   inv('INV-4', sin='S3', ex='7', cc='CC-02', batch='B-2'))                                           # INV-4 repeats INV-3: not counted
        m.reconcile()
        F = facts(m)
        self.assertEqual(costs.build_actual(F, 'PRJ-001', AS_OF)['classified']['counted_invoices'], 3)
        self.assertEqual(costs.build_actual(F, 'PRJ-001', AS_OF, cost_code='CC-01')['classified']['counted_invoices'], 1)
        self.assertEqual(costs.build_actual(F, 'PRJ-001', AS_OF, cost_code='CC-02')['classified']['counted_invoices'], 2)


class TestCommitmentAndRevenueEdges(unittest.TestCase):
    def test_an_order_dated_on_the_cut_off_day_is_open_and_the_next_day_is_after_the_cut_off(self):
        m = Mini()
        m.pos(po('PO-1', date='2026-09-30', amount='1000000'), po('PO-2', date='2026-10-01', amount='500000'))
        m.reconcile('2026-10-05')
        f = m.fig('fin.commitments')
        self.assertEqual(f['value']['cents'], 1000000)
        self.assertEqual(refs(f, 'after_cutoff'), ['purchase_order/PO-2'])

    def test_an_amendment_dated_on_the_cut_off_day_counts_and_the_next_day_does_not(self):
        m = Mini()
        m.pos(po('PO-1', amount='1000000'))
        m.amendments(['AM-1', 'PO-1', '2026-09-30', '100000', '', 'x'], ['AM-2', 'PO-1', '2026-10-01', '40000', '', 'x'])
        m.reconcile('2026-10-05')
        f = m.fig('fin.commitments')
        self.assertEqual(refs(f, 'after_cutoff'), ['po_amendment/AM-2'])
        self.assertNotIn('po_amendment/AM-1', refs(f, 'after_cutoff'))
        self.assertEqual(f['classified']['po_lines']['PO-1']['unapproved_exposure_cents'], 100000)

    def test_orders_and_amendments_that_were_never_reconciled_are_held_not_a_crash(self):
        m = Mini()
        m.pos(po('PO-1', amount='1000000'))
        m.reconcile()
        m.amendments(['AM-1', 'PO-1', '2026-09-01', '100000', '', 'x'])             # arrived after the last reconciliation
        m.pos(po('PO-2', amount='500000'))
        f = m.fig('fin.commitments')
        self.assertEqual(codes_of(f, 'po_amendment/AM-1'), [['NO_RECONCILIATION_STATE']])
        self.assertEqual(codes_of(f, 'purchase_order/PO-2'), [['NO_RECONCILIATION_STATE']])
        self.assertEqual(f['value']['cents'], 1000000)

    def test_a_variation_raised_on_the_as_of_day_counts_and_the_next_day_does_not(self):
        m = base_world()
        m.variations(var('V-1', raised='2026-09-30', status='approved', value='100'), var('V-2', raised='2026-10-01', status='approved', value='200'))
        m.reconcile('2026-10-05')
        f = m.fig('fin.revenue')
        self.assertEqual(refs(f, 'after_cutoff'), ['variation/V-2'])
        self.assertIn('variation/V-1', [c['ref'] for c in f['contributed']])





def ctc_part(f):
    return f['components']['cost_to_complete']


class TestCostToCompleteDetail(unittest.TestCase):
    def test_each_cost_to_complete_cites_its_source_and_only_a_declared_line_has_a_pinned_revision(self):
        f = ctc_part(fc(world()))
        got = {c['ref']: c['revision'] for c in f['contributed']}
        self.assertEqual(got, {'ctc_line/PRJ-001|CC-01|F-1': 1, 'budget_less_actual/CC-02': None})

    def test_a_declared_line_the_policy_does_not_use_is_left_out_and_not_pinned(self):
        m = world(); m.set_policy(ctc_method={'default': 'budget_less_actual'})
        f = ctc_part(fc(m))
        self.assertEqual({c['ref']: c['revision'] for c in f['contributed']}, {'budget_less_actual/CC-01': None, 'budget_less_actual/CC-02': None})
        self.assertEqual([(e['ref'], e['class'], e['codes']) for e in f['excluded']], [('ctc_line/PRJ-001|CC-01|F-1', 'not_counted', ['DECLARED_LINE_NOT_USED_BY_METHOD:budget_less_actual'])])

    def test_the_kind_of_unknown_says_whether_data_is_missing_or_invalid(self):
        m = world(inv_cc02='3500000')                                                     # CC-02 over budget
        m.invoices(inv('INV-9', sin='S9', cc='CC-09', ex='100', date='2026-08-03')); m.reconcile()            # CC-09 has cost and no budget
        by = {u['input']: u for u in ctc_part(fc(m))['unknown_inputs']}
        self.assertEqual(by['cost to complete for CC-02']['reason'], 'invalid')
        self.assertEqual(by['cost to complete for CC-02']['decision'], 'BUDGET_EXCEEDED_BY:500000')
        self.assertEqual(by['cost to complete for CC-09']['reason'], 'no_data')
        self.assertEqual(by['cost to complete for CC-09']['decision'], 'NO_BUDGET_FOR_CODE')
        m2 = world(); m2.set_policy(ctc_method={'default': 'declared'})
        by = {u['input']: u for u in ctc_part(fc(m2))['unknown_inputs']}
        self.assertEqual((by['cost to complete for CC-02']['reason'], by['cost to complete for CC-02']['decision']), ('no_data', 'NO_DECLARED_LINE'))

    def test_a_held_declared_line_is_unknown_for_a_reason_and_is_not_a_dispute(self):
        m = Mini()
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0'])
        m.budgets(bud(cc='CC-01', cents='5000000'), bud(cc='CC-02', cents='3000000'))
        m.ctcs(ctc(cc='CC-01', cents='-5'), ctc(cc='CC-02', cents='900000'))               # a negative cost to complete is held at intake (SIGN_CONVENTION)
        m.reconcile()
        f = ctc_part(fc(m))
        self.assertEqual([(e['ref'], e['class'], e['codes']) for e in f['excluded']], [('ctc_line/PRJ-001|CC-01|F-1', 'unknown_value', ['SIGN_CONVENTION:cost_to_complete_cents'])])
        self.assertEqual(f['disputed'], [])
        e = f['classified']['ctc_by_code']['CC-01']
        self.assertEqual((e['cents'], e['unknown']), (None, 'DECLARED_LINE_HELD:ctc_line/PRJ-001|CC-01|F-1'))
        self.assertEqual(f['classified']['ctc_by_code']['CC-02']['cents'], 900000)           # the other code still uses its declared line

    def test_a_conflicting_declared_line_is_a_dispute(self):
        m = world()
        m.ctcs(ctc(cc='CC-01', cents='1600000')); m.reconcile()
        f = ctc_part(fc(m))
        self.assertEqual([d['ref'] for d in f['disputed']], ['ctc_line/PRJ-001|CC-01|F-1'])


class TestBudgetsInTheForecast(unittest.TestCase):
    def test_a_budget_line_that_was_never_reconciled_is_held_and_is_not_a_dispute(self):
        m = world()
        m.budgets(bud(cc='CC-03', cents='100', rev='R0'))                                  # arrived after the last reconciliation
        f = fc(m)
        self.assertEqual([(e['class'], e['codes']) for e in f['excluded'] if e['ref'] == 'budget_line/PRJ-001|CC-03'], [('held', ['NO_RECONCILIATION_STATE'])])
        self.assertNotIn('budget_line/PRJ-001|CC-03', [d['ref'] for d in f['disputed']])
        self.assertEqual(f['state'], PROV)

    def test_a_conflicting_budget_line_is_a_dispute(self):
        m = world()
        m.budgets(bud(cc='CC-01', cents='9999999', rev='R0')); m.reconcile()
        self.assertIn('budget_line/PRJ-001|CC-01', [d['ref'] for d in fc(m)['disputed']])

    def test_the_total_cost_variance_needs_an_authoritative_cost_to_complete(self):
        f = fc(world())
        self.assertEqual(f['classified']['cost_variance']['total_cents'], f['classified']['ffc_cents'] - 8000000)
        g = fc(world(approved=False))                                                      # same data, policy not approved: every part is provisional
        self.assertEqual(g['classified']['ffc_cents'], f['classified']['ffc_cents'])
        self.assertEqual(g['classified']['cost_variance']['by_code'], f['classified']['cost_variance']['by_code'])
        self.assertIsNone(g['classified']['cost_variance']['total_cents'])





def cworld(ret=('500000', '2027-02-01', '', ''), fac_date='2026-09-30', sec=None):
    m = Mini()
    m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0'])
    if ret:
        m.retention(['PRJ-001'] + list(ret))
    m.facility(['FAC-1', '50000000', '20000000', '800', fac_date])
    for row in sec or ():
        m.security(row)
    m.reconcile()
    return m


def cash(m, what, as_of=AS_OF):
    return m.fig('fin.cash_position', 'PRJ-001', as_of, {'what': what})


class TestCashDateEdges(unittest.TestCase):
    def test_a_release_date_on_the_as_of_day_raises_the_review_flag_and_the_next_day_does_not(self):
        self.assertEqual(cash(cworld(('500000', '2026-09-30', '', '')), 'retention')['classified']['flags'], ['RELEASE_REVIEW_DUE'])
        f = cash(cworld(('500000', '2026-10-01', '', '')), 'retention')
        self.assertEqual(f['classified']['flags'], [])
        self.assertFalse(any(r.startswith('RELEASE_REVIEW_DUE') for r in f['reasons']))

    def test_nothing_withheld_raises_no_review_flag_even_when_the_date_has_passed(self):
        self.assertEqual(cash(cworld(('0', '2026-09-01', '', '')), 'retention')['classified']['flags'], [])

    def test_carrying_cost_is_refused_on_the_release_date_itself_and_costed_for_one_day_the_day_before(self):
        f = cash(cworld(('500000', '2026-09-30', '', '')), 'retention_carrying')
        self.assertEqual((f['state'], f['value']['cents']), (CANT, None))
        self.assertTrue(f['reasons'][0].startswith('EXPECTED_RELEASE_DATE_PASSED_AND_NOT_RELEASED'))
        g = cash(cworld(('500000', '2026-10-01', '', '')), 'retention_carrying')
        self.assertEqual((g['state'], g['classified']['inputs']['eligible_days']), (AUTH, 1))
        self.assertEqual(g['value']['cents'], 55)                                          # 250,000 funded x 8.00% x 1 / 365, rounded once

    def test_a_facility_statement_exactly_at_the_freshness_limit_is_not_stale_and_one_day_older_is(self):
        m = cworld()
        ok = cash(m, 'retention_carrying', '2026-11-14')                                   # 45 days after the statement, limit 45
        self.assertEqual(ok['state'], AUTH)
        old = cash(m, 'retention_carrying', '2026-11-15')
        self.assertEqual(old['state'], PROV)
        self.assertTrue(any('46 days old' in u['input'] for u in old['unknown_inputs']))

    def test_an_instrument_expiring_on_the_as_of_day_is_flagged_and_a_later_or_blank_expiry_is_not(self):
        m = cworld(sec=[['BG-1', 'PRJ-001', 'bank_guarantee', '100', '2026-09-30'], ['BG-2', 'PRJ-001', 'bank_guarantee', '200', '2026-10-01'], ['BG-3', 'PRJ-001', 'insurance_bond', '300', '']])
        f = cash(m, 'security')
        self.assertEqual(f['classified']['flags'], ['EXPIRY_REVIEW:BG-1'])
        self.assertEqual({i['instrument']: i['review'] for i in f['classified']['instruments']}, {'BG-1': True, 'BG-2': False, 'BG-3': False})
        self.assertIn('security/BG-3 expiry_date', [u['input'] for u in f['unknown_inputs']])
        self.assertEqual(f['value']['cents'], 600)

    def test_a_release_recorded_by_events_alone_is_not_a_ledger_release(self):
        m = cworld()
        clerk, boss = actor(m, 'c', 'clara', 'retention_clerk'), actor(m, 'b', 'bruno', 'retention_approver')
        CS.record_event(clerk, m.clock, 'PRJ-001', m.s.get('retention', 'PRJ-001').payload['fields'], 'withheld', 'claimed', 300000, 'CLAIM-1', bank={})
        CS.record_event(boss, m.clock, 'PRJ-001', m.s.get('retention', 'PRJ-001').payload['fields'], 'claimed', 'approved', 300000, 'CERT-1', bank={})
        CS.record_event(boss, m.clock, 'PRJ-001', m.s.get('retention', 'PRJ-001').payload['fields'], 'approved', 'released', 300000, 'REL-1', bank={})
        f = cash(m, 'retention')
        self.assertEqual(f['classified']['pools_cents']['released'], 300000)
        self.assertEqual(f['classified']['flags'], [])                                     # no released date on the ledger, so no "released per ledger" flag


def actor(m, token, user, *roles):
    return m.w.who(token, 'zero_one', user=user, roles=roles, kind='human')





def item(r, part, **kw):
    out = [i for i in r['classified']['items'] if i['part'] == part and all(i.get(k) == v for k, v in kw.items())]
    return out


class TestBridgeItems(unittest.TestCase):
    def test_a_new_variation_and_a_new_invoice_together_are_two_exact_explained_items(self):
        m = project_world()
        a = run_fc(m, 'F-A')
        m.variations(var('V-1', status='approved', value='700000'))
        m.invoices(inv('INV-2', sin='S2', cc='CC-01', ex='400000', date='2026-08-20'))
        m.reconcile()
        b = run_fc(m, 'F-A')
        r = bridge(m, a, b)
        self.assertEqual([(i['part'], i['ref'], i['effect_cents'], i['explained']) for i in r['classified']['items']],
                         [('revenue', 'variation/V-1', 700000, True), ('actual_cost', 'ap_invoice/INV-2', -400000, True)])
        self.assertEqual((r['value']['cents'], r['classified']['reconciles'], r['classified']['unexplained_items']), (300000, True, 0))

    def synth(self):
        m = project_world()
        m.variations(var('V-1', status='approved', value='700000')); m.reconcile()
        a = run_fc(m, 'F-A')['result']
        return a, copy.deepcopy(a)

    @staticmethod
    def change(fig, ref, delta):
        rev = fig['components']['forecast_revenue']
        for c in rev['contributed']:
            if c['ref'] == ref:
                c['amount_cents'] += delta
        rev['value']['cents'] += delta
        fig['value']['cents'] += delta

    def test_a_revenue_record_whose_amount_changed_is_unexplained_even_when_it_is_an_approved_variation(self):
        a, b = self.synth()
        self.change(b, 'variation/V-1', 50)
        r = B.build_bridge(a, b)
        it = item(r, 'revenue', ref='variation/V-1')
        self.assertEqual([(i['effect_cents'], i['explained'], i['why']) for i in it], [(50, False, 'REVENUE_RECORD_AMOUNT_CHANGED_WITHOUT_RECORDED_REASON')])
        self.assertTrue(r['classified']['reconciles'])

    def test_a_record_that_appears_with_a_role_other_than_a_new_variation_is_unexplained(self):
        a, b = self.synth()
        a['components']['forecast_revenue']['contributed'] = [c for c in a['components']['forecast_revenue']['contributed'] if c['ref'] != 'contract/PRJ-001']
        a['components']['forecast_revenue']['value']['cents'] -= 10000000
        a['value']['cents'] -= 10000000
        r = B.build_bridge(a, b)
        it = item(r, 'revenue', ref='contract/PRJ-001')
        self.assertEqual([(i['explained'], i['why']) for i in it], [(False, 'REVENUE_RECORD_AMOUNT_CHANGED_WITHOUT_RECORDED_REASON')])
        c = B.build_bridge(b, b)                                                              # nothing moves: no items at all
        self.assertEqual(c['classified']['items'], [])

    def test_a_revenue_record_that_stopped_counting_says_so(self):
        a, b = self.synth()
        rev = b['components']['forecast_revenue']
        rev['contributed'] = [c for c in rev['contributed'] if c['ref'] != 'variation/V-1']
        rev['value']['cents'] -= 700000
        b['value']['cents'] -= 700000
        r = B.build_bridge(a, b)
        self.assertEqual([(i['effect_cents'], i['explained'], i['why']) for i in item(r, 'revenue', ref='variation/V-1')], [(-700000, False, 'REVENUE_RECORD_NO_LONGER_COUNTED')])

    def test_cost_to_complete_that_was_unknown_or_becomes_unknown_is_never_explained_and_names_its_record(self):
        a, b = self.synth()
        a['classified']['ctc_by_code']['CC-01'] = {'cents': None, 'method': 'declared', 'source': None, 'reason': None}
        b['classified']['ctc_by_code']['CC-01'] = {'cents': 500, 'method': 'declared', 'source': 'ctc_line/NEW', 'reason': 'r'}
        it = item(B.build_bridge(a, b), 'cost_to_complete', cost_code='CC-01')
        self.assertEqual([(i['ref'], i['explained'], i['why']) for i in it], [('ctc_line/NEW', False, 'COST_TO_COMPLETE_NEWLY_KNOWN_WAS_UNKNOWN')])
        a, b = b, a                                                                           # the other way round
        a['classified']['ctc_by_code']['CC-01'] = {'cents': 500, 'method': 'declared', 'source': 'ctc_line/OLD', 'reason': 'r'}
        b['classified']['ctc_by_code']['CC-01'] = {'cents': None, 'method': 'declared', 'source': None, 'reason': None}
        it = item(B.build_bridge(a, b), 'cost_to_complete', cost_code='CC-01')
        self.assertEqual([(i['ref'], i['explained'], i['why']) for i in it], [('ctc_line/OLD', False, 'COST_TO_COMPLETE_NOW_UNKNOWN')])

    def test_a_derived_cost_to_complete_is_explained_only_while_the_budget_is_unchanged(self):
        a, b = self.synth()
        for f, c in ((a, 100), (b, 40)):
            f['classified']['ctc_by_code']['CC-02'] = {'cents': c, 'method': 'budget_less_actual', 'source': 'budget_less_actual', 'reason': None}
        r = B.build_bridge(a, b)
        self.assertEqual([(i['explained'], i['why']) for i in item(r, 'cost_to_complete', cost_code='CC-02')], [(True, 'derived from budget less actual; budget unchanged')])
        b['classified']['budget_by_code'] = dict(b['classified']['budget_by_code'], **{'CC-02': 1})
        r = B.build_bridge(a, b)
        self.assertEqual([(i['explained'], i['why']) for i in item(r, 'cost_to_complete', cost_code='CC-02')], [(False, 'BUDGET_CHANGED_AND_CTC_DERIVED_FROM_IT')])

    def test_the_bridge_is_approved_only_when_both_forecasts_were_run_under_an_approved_policy(self):
        m = project_world(approved=False)
        POL.store_policy(m.s, demo_policy(version='SYN-FIN-POL-2', approved=True))
        a = run_fc(m, 'F-A')
        b = m.run('fin.forecast', extra={'forecast_version': 'F-A'}, policy='SYN-FIN-POL-2')
        self.assertEqual(b['result']['policy']['approved'], True)
        r = bridge(m, a, b)
        self.assertEqual(r['policy'], {'version': 'SYN-FIN-POL-2', 'approved': False})
        self.assertIn('POLICY_NOT_APPROVED:SYN-FIN-POL-2', r['reasons'])


class TestBookEdges(unittest.TestCase):
    def setUp(self):
        self.m = project_world()
        self.run = run_fc(self.m, 'F-A')
        self.owner = self.m.w.who('o', 'zero_one', user='olga', roles=('forecast_owner',))
        self.owner2 = self.m.w.who('o2', 'zero_one', user='omar', roles=('forecast_owner',))
        self.key = FB.slot_key('PRJ-001', AS_OF)

    def slot(self):
        return self.m.s.get(FB.SLOT_KIND, self.key)

    def damage(self, **fields):
        cur = self.slot()
        self.m.s.put(FB.SLOT_KIND, self.key, dict(cur.payload, **fields), expected_revision=cur.revision)

    def scenario(self, name):
        r = self.m.run('fin.forecast', extra={'forecast_version': 'F-A', 'scenario': name})
        FB.register_scenario(self.m.s, 'PRJ-001', AS_OF, r['run_key'], name)
        return r

    def test_registering_the_same_scenario_run_twice_keeps_one_entry_and_a_second_run_is_added(self):
        a = self.scenario('low')
        FB.register_scenario(self.m.s, 'PRJ-001', AS_OF, a['run_key'], 'low')
        self.assertEqual(self.slot().payload['scenarios'], {'low': [a['run_key']]})
        self.assertEqual(self.slot().payload['scenarios']['low'].count(a['run_key']), 1)

    def test_a_slot_with_only_scenarios_is_consistent_and_has_no_authoritative_forecast(self):
        self.scenario('low')
        self.assertEqual(FB.verify_slot(self.m.s, 'PRJ-001', AS_OF), [])
        self.assertIsNone(FB.current(self.m.s, 'PRJ-001', AS_OF))

    def test_an_authoritative_run_with_no_history_is_a_damaged_slot(self):
        self.scenario('low')
        self.damage(authoritative=self.run['run_key'])
        self.assertEqual(FB.verify_slot(self.m.s, 'PRJ-001', AS_OF), ['AUTHORITATIVE_DIFFERS_FROM_LAST_ADOPTION'])

    def test_a_scenario_is_not_a_problem_while_it_is_not_the_authoritative_run(self):
        FB.adopt(self.owner, self.m.reg, self.m.clock, 'PRJ-001', AS_OF, self.run['run_key'])
        self.scenario('low')
        self.assertEqual(FB.verify_slot(self.m.s, 'PRJ-001', AS_OF), [])

    def test_a_scenario_that_is_the_authoritative_run_needs_a_recorded_promotion_of_that_run(self):
        FB.adopt(self.owner, self.m.reg, self.m.clock, 'PRJ-001', AS_OF, self.run['run_key'])
        sc = self.scenario('low')
        self.damage(scenarios={'low': [self.run['run_key']]})                               # the adopted run is also listed as a scenario, without any promotion
        self.assertEqual(FB.verify_slot(self.m.s, 'PRJ-001', AS_OF), ['SCENARIO_IS_AUTHORITATIVE_WITHOUT_PROMOTION:low'])
        h = self.slot().payload['history']
        self.damage(history=[dict(h[0], event='promoted_scenario', run_key=sc['run_key'])])  # a promotion of a different run does not cover it
        self.assertIn('SCENARIO_IS_AUTHORITATIVE_WITHOUT_PROMOTION:low', FB.verify_slot(self.m.s, 'PRJ-001', AS_OF))

    def test_the_refusal_to_adopt_a_run_that_does_not_reproduce_says_what_failed(self):
        rec = self.m.s.get(repro.KIND, self.run['run_key'])
        self.m.s.put(repro.KIND, self.run['run_key'], dict(rec.payload, result_hash='0' * 64), expected_revision=rec.revision)
        with self.assertRaises(FB.BookError) as cx:
            FB.adopt(self.owner, self.m.reg, self.m.clock, 'PRJ-001', AS_OF, self.run['run_key'])
        self.assertIn('STORED_RESULT_ALTERED', str(cx.exception))
        self.assertNotIn('figure or pins', str(cx.exception))


class TestRecordReports(unittest.TestCase):
    def test_a_record_that_was_never_revised_has_no_history_and_a_revised_one_lists_its_revisions(self):
        m = project_world()
        r = run_fc(m, 'F-A')
        self.assertEqual(C.explain(m.s, r['run_key'])['history'], {})
        m.budgets(bud(cc='CC-01', cents='5100000', rev='R1')); m.reconcile()
        r2 = run_fc(m, 'F-A')
        h = C.explain(m.s, r2['run_key'])['history']
        self.assertIn('budget_line/PRJ-001|CC-01', h)
        self.assertEqual(sorted(x['revision'] for x in h['budget_line/PRJ-001|CC-01']), [1, 2])
        self.assertTrue(all(len(v) > 1 for v in h.values()))

    def test_a_diff_names_the_revision_on_each_side_of_an_input_change_and_what_was_added_or_removed(self):
        m = project_world()
        a = m.s.get(repro.KIND, run_fc(m, 'F-A')['run_key']).payload
        m.budgets(bud(cc='CC-01', cents='5100000', rev='R1')); m.reconcile()
        b = m.s.get(repro.KIND, run_fc(m, 'F-A')['run_key']).payload
        d = C.diff_records(a, b)
        ch = [i for i in d['input_changes'] if i.get('input') == 'budget_line/PRJ-001|CC-01']
        self.assertEqual(ch, [{'input': 'budget_line/PRJ-001|CC-01', 'from': 1, 'to': 2}])
        gone = copy.deepcopy(b)
        gone['inputs'] = [i for i in gone['inputs'] if not (i['kind'] == 'budget_line' and i['key'].endswith('CC-02'))]
        d2 = C.diff_records(a, gone)
        self.assertIn({'input': 'budget_line/PRJ-001|CC-02', 'from': 1, 'to': None}, d2['input_changes'])
        d3 = C.diff_records(gone, a)
        self.assertIn({'input': 'budget_line/PRJ-001|CC-02', 'from': None, 'to': 1}, d3['input_changes'])

    def test_a_policy_change_is_a_rule_change_that_says_whether_it_was_a_new_revision_or_a_different_version(self):
        m = project_world(approved=False)
        a = m.s.get(repro.KIND, run_fc(m, 'F-A')['run_key']).payload
        pol = m.s.get(POL.POLICY_KIND, m.policy['version'])
        POL.store_policy(m.s, POL.approve(pol.payload, 'owner.person', POL.POLICY_ROLE, 'human', '2026-09-30'))          # same version, one more approval: revision 2
        b = m.s.get(repro.KIND, m.run('fin.forecast', extra={'forecast_version': 'F-A'})['run_key']).payload
        d = C.diff_records(a, b)
        self.assertEqual(d['rule_changes'], ['policy %s revision 1 -> 2' % m.policy['version']])
        POL.store_policy(m.s, demo_policy(version='SYN-FIN-POL-2', approved=True))
        c = m.s.get(repro.KIND, m.run('fin.forecast', extra={'forecast_version': 'F-A'}, policy='SYN-FIN-POL-2')['run_key']).payload
        d = C.diff_records(b, c)
        self.assertEqual(sorted(d['rule_changes']), sorted(['policy %s added or removed' % m.policy['version'], 'policy SYN-FIN-POL-2 added or removed']))



class TestFirstLineOfDefenceMessages(unittest.TestCase):
    """The figure builder refuses some mistakes twice (once at build, once at validation).  These tests pin the FIRST refusal, so it cannot be lost quietly behind the second."""
    def test_two_values_are_refused_before_anything_else(self):
        with self.assertRaisesRegex(FigureError, 'one value'):
            _b().finish(cents=1, bps=1)

    def test_a_value_on_top_of_a_required_part_that_cannot_be_assessed_is_refused_by_name(self):
        for kw in ({'cents': 5}, {'bps': 5}):
            b = _b(); b.child('c', _b().cannot('NO_DATA'))
            with self.assertRaisesRegex(FigureError, 'component c cannot be assessed'):
                b.finish(**kw)

    def test_a_zero_day_count_basis_is_refused_by_name_not_as_a_zero_divisor(self):
        with self.assertRaisesRegex(ValueError, 'day-count basis must be positive'):
            fmath.carrying_cents(100, 100, 10, 0)

    def test_a_policy_that_is_not_well_formed_is_refused_and_nothing_is_stored(self):
        m = Mini()
        bad = dict(P.new_policy('V-BAD', 'p'), ctc_method='declared')
        with self.assertRaises(P.PolicyError):
            P.store_policy(m.s, bad)
        self.assertIsNone(m.s.get(P.POLICY_KIND, 'V-BAD'))


if __name__ == '__main__':
    unittest.main()
