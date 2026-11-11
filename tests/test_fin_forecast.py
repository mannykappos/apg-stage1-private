import unittest
from . import _path                                         # noqa: F401
from .helpers_fin import Mini, base_world, inv, bud, ctc, var, AS_OF, CTC_H, BUD_H
from .helpers_ingest import csvb
from apg.fin import margins
from apg.fin.figure import AUTH, PROV, CANT


def fc(m, project='PRJ-001', as_of=AS_OF, extra=None):
    return m.fig('fin.forecast', project, as_of, extra)


def world(inv_cc01='3000000', inv_cc02='1000000', **kw):
    m = base_world(**kw)
    rows = []
    if inv_cc01:
        rows.append(inv('INV-1', cc='CC-01', ex=inv_cc01, date='2026-08-01'))
    if inv_cc02:
        rows.append(inv('INV-2', sin='S2', cc='CC-02', ex=inv_cc02, date='2026-08-02'))
    if rows:
        m.invoices(*rows)
    m.reconcile()
    return m


class TestForecastFinalMargin(unittest.TestCase):
    def test_headline_arithmetic_and_components_reconcile(self):
        m = world()
        f = fc(m)
        c = f['classified']
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 2500000))
        self.assertEqual((c['ffr_cents'], c['actual_cents'], c['ctc_cents'], c['ffc_cents']), (10000000, 4000000, 3500000, 7500000))
        self.assertEqual(c['ffr_cents'] - c['ffc_cents'], f['value']['cents'])
        self.assertEqual(c['actual_cents'] + c['ctc_cents'], c['ffc_cents'])
        cf = f['components']['cost_to_complete']
        self.assertEqual(sum(e['cents'] for e in cf['classified']['ctc_by_code'].values()), cf['value']['cents'])         # CTC components add to the total (AC-07)
        self.assertEqual({k: (v['method'], v['cents']) for k, v in c['ctc_by_code'].items()}, {'CC-01': ('declared', 1500000), 'CC-02': ('budget_less_actual', 2000000)})
        self.assertEqual(c['forecast_version'], 'F-1')
        self.assertEqual(set(f['components']), {'forecast_revenue', 'actual_cost', 'cost_to_complete'})

    def test_cost_variance_against_the_budget(self):
        f = fc(world())
        self.assertEqual(f['classified']['cost_variance'], {'total_cents': -500000, 'by_code': {'CC-01': -500000, 'CC-02': 0}})

    def test_actuals_after_the_forecast_date_do_not_change_the_forecast(self):
        def build(extra_rows):
            m = Mini()
            m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0'])
            m.budgets(bud(cc='CC-01', cents='5000000'))
            m.ctcs(ctc(cc='CC-01', date='2026-08-31', cents='1500000'))
            m.invoices(inv('INV-1', cc='CC-01', ex='3000000', date='2026-08-01'), *extra_rows)
            m.reconcile()
            return fc(m, as_of='2026-09-30')
        without = build([])
        with_later = build([inv('INV-2', sin='S2', cc='CC-01', ex='700000', date='2026-09-10')])
        self.assertEqual(without['value'], with_later['value'])
        self.assertEqual(without['classified']['ffc_cents'], with_later['classified']['ffc_cents'])
        self.assertEqual(with_later['classified']['since_forecast_actual_cents'], 700000)

    def test_invoice_after_the_forecast_date_is_shown_separately_never_added(self):
        m = Mini()
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0'])
        m.budgets(bud(cc='CC-01', cents='5000000'))
        m.ctcs(ctc(cc='CC-01', date='2026-08-31', cents='1500000'))
        m.invoices(inv('INV-1', cc='CC-01', ex='3000000', date='2026-08-01'), inv('INV-2', sin='S2', cc='CC-01', ex='400000', date='2026-09-10'))
        m.reconcile()
        f = fc(m, as_of='2026-09-30')
        c = f['classified']
        self.assertEqual((c['forecast_date'], c['actual_cents'], c['ffc_cents']), ('2026-08-31', 3000000, 4500000))     # the 400,000 after the forecast date is NOT added
        self.assertEqual(c['since_forecast_actual_cents'], 400000)
        self.assertIn('ACTUALS_AFTER_FORECAST_DATE_NOT_ADDED', f['reasons'])

    def test_unapproved_variations_never_enter_forecast_revenue(self):
        m = world()
        m.variations(var('V-S', status='submitted', value='900000'), var('V-A', status='approved', value='100000'))
        m.reconcile()
        f = fc(m)
        self.assertEqual(f['classified']['ffr_cents'], 10100000)                              # base + approved only; the submitted 900,000 is not revenue
        self.assertEqual(f['state'], PROV)                                                    # the contract summary (0 approved) disagrees with the register (100,000)

    def test_declared_only_method_leaves_codes_without_a_line_unknown(self):
        m = world(); m.set_policy(ctc_method={'default': 'declared'})
        f = fc(m)
        self.assertEqual(f['state'], PROV)
        self.assertEqual(f['classified']['ctc_cents'], 1500000)
        self.assertEqual(f['classified']['ctc_by_code']['CC-02']['unknown'], 'NO_DECLARED_LINE')
        self.assertIn('CTC_UNKNOWN:CC-02', f['components']['cost_to_complete']['reasons'])

    def test_budget_less_actual_method_ignores_the_declared_line_and_says_so(self):
        m = world(); m.set_policy(ctc_method={'default': 'budget_less_actual'})
        f = fc(m)
        cf = f['components']['cost_to_complete']
        self.assertEqual(f['classified']['ctc_cents'], 2000000 + 2000000)
        self.assertEqual(f['state'], PROV)                                                   # a declared estimate exists but the method does not use it
        self.assertEqual(cf['excluded'][0]['class'], 'not_counted')
        self.assertIn('DECLARED_LINE_NOT_USED_BY_METHOD', cf['excluded'][0]['codes'][0])

    def test_per_cost_code_override(self):
        m = world(); m.set_policy(ctc_method={'default': 'budget_less_actual', 'by_cost_code': {'CC-01': 'declared'}})
        f = fc(m)
        self.assertEqual({k: v['method'] for k, v in f['classified']['ctc_by_code'].items()}, {'CC-01': 'declared', 'CC-02': 'budget_less_actual'})
        self.assertEqual((f['state'], f['classified']['ctc_cents']), (AUTH, 3500000))

    def test_budget_exceeded_gives_an_unknown_cost_to_complete_never_a_negative_one(self):
        m = world(inv_cc02='3500000')
        f = fc(m)
        e = f['classified']['ctc_by_code']['CC-02']
        self.assertEqual((e['cents'], e['unknown']), (None, 'BUDGET_EXCEEDED_BY:500000'))
        self.assertEqual(f['state'], PROV)
        self.assertEqual(f['classified']['ctc_cents'], 1500000)

    def test_exactly_spent_budget_is_a_zero_cost_to_complete(self):
        m = world(inv_cc02='3000000')
        e = fc(m)['classified']['ctc_by_code']['CC-02']
        self.assertEqual(e['cents'], 0)

    def test_a_held_declared_line_is_not_silently_replaced_by_budget_less_actual(self):
        m = Mini()
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0'])
        m.budgets(bud(cc='CC-01', cents='5000000'))
        m.ctcs(ctc(cc='CC-01', cents='1500000'))
        m.ctcs(ctc(cc='CC-01', cents='2500000'))                                              # same key, different content: conflict
        m.invoices(inv('INV-1', cc='CC-01', ex='100', date='2026-08-01')); m.reconcile()
        f = fc(m)
        self.assertEqual(f['state'], CANT)                                                    # no cost-to-complete information at all
        cf = f['components']['cost_to_complete']
        self.assertEqual(cf['classified']['ctc_by_code']['CC-01']['unknown'], 'DECLARED_LINE_HELD:ctc_line/PRJ-001|CC-01|F-1')

    def test_declared_only_method_uses_only_lines_that_exist(self):
        m = Mini()
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0'])
        m.budgets(bud(cc='CC-01')); m.ctcs(ctc(cc='CC-07', cents='5')); m.set_policy(ctc_method={'default': 'declared'})
        m.invoices(inv('INV-1', cc='CC-01', ex='100', date='2026-08-01')); m.reconcile()
        f = fc(m)
        self.assertEqual(f['classified']['ctc_by_code']['CC-01']['unknown'], 'NO_DECLARED_LINE')
        self.assertEqual(f['classified']['ctc_cents'], 5)
        self.assertEqual(f['state'], PROV)

    def test_cost_in_a_code_with_no_budget_and_no_declared_line_is_unknown(self):
        m = world()
        m.invoices(inv('INV-5', sin='S5', cc='CC-77', ex='10', date='2026-08-01')); m.reconcile()
        e = fc(m)['classified']['ctc_by_code']['CC-77']
        self.assertEqual((e['cents'], e['unknown']), (None, 'NO_BUDGET_FOR_CODE'))

    def test_cost_with_no_code_cannot_have_a_code_level_estimate(self):
        m = world()
        from apg.ingest import pipeline as P3, demo_setup as D
        from apg.ingest.specs import IngestPolicy
        from apg.ingest import pipeline
        from .helpers_ingest import tpl, inv_file
        pol = IngestPolicy(warn_unknown={'ap_invoice': ('gst_cents', 'purchase_order_ref', 'source_status', 'source_batch_ref', 'cost_code_ref')})
        P3.ingest_file(m.s, m.clock, tpl('TPL-BZ-AP-INVOICES'), inv_file(inv('INV-8', sin='S8', cc='', ex='10', date='2026-08-01')), 'accounting', 'z.csv', pol)
        m.reconcile()
        f = fc(m)
        self.assertEqual(f['classified']['ctc_by_code']['(no cost code)']['unknown'], 'COST_NOT_ALLOCATED_TO_A_COST_CODE')
        self.assertEqual(f['state'], PROV)

    def test_declared_line_for_a_code_not_in_the_budget_is_used(self):
        m = world()
        m.ctcs(ctc(cc='CC-55', cents='700000'))
        m.reconcile()
        e = fc(m)['classified']['ctc_by_code']['CC-55']
        self.assertEqual((e['cents'], e['method']), (700000, 'declared'))


class TestVersionSelection(unittest.TestCase):
    def two_versions(self, d1='2026-08-31', d2='2026-09-30', reason2=''):
        m = Mini()
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0'])
        m.budgets(bud(cc='CC-01', cents='5000000'))
        m.ctcs(ctc(cc='CC-01', version='F-A', date=d1, cents='1500000', reason='initial'), ctc(cc='CC-01', version='F-B', date=d2, cents='2500000', reason=reason2))
        m.invoices(inv('INV-1', cc='CC-01', ex='3000000', date='2026-08-01')); m.reconcile()
        return m

    def test_latest_version_by_date_is_chosen(self):
        f = fc(self.two_versions())
        self.assertEqual((f['classified']['forecast_version'], f['classified']['ctc_cents']), ('F-B', 2500000))

    def test_an_earlier_version_can_be_asked_for_and_history_is_preserved(self):
        m = self.two_versions()
        f = fc(m, extra={'forecast_version': 'F-A'})
        self.assertEqual((f['classified']['forecast_version'], f['classified']['forecast_date'], f['classified']['ctc_cents']), ('F-A', '2026-08-31', 1500000))
        self.assertEqual(len(m.s.query('ctc_line')), 2)

    def test_a_version_dated_after_the_as_of_date_is_not_yet_known(self):
        f = fc(self.two_versions(), as_of='2026-09-15')
        self.assertEqual(f['classified']['forecast_version'], 'F-A')

    def test_two_different_versions_on_the_same_latest_date_cannot_be_chosen_between(self):
        f = fc(self.two_versions(d1='2026-09-30'))
        self.assertEqual(f['state'], CANT)
        self.assertTrue(f['reasons'][0].startswith('AMBIGUOUS_LATEST_FORECAST:F-A,F-B'))

    def test_unknown_version_asked_for(self):
        f = fc(self.two_versions(), extra={'forecast_version': 'F-ZZ'})
        self.assertEqual((f['state'], f['reasons']), (CANT, ['FORECAST_VERSION_NOT_FOUND:F-ZZ']))

    def test_version_whose_lines_carry_different_dates_cannot_be_used(self):
        m = Mini()
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0'])
        m.budgets(bud(cc='CC-01'), bud(cc='CC-02'))
        m.ctcs(ctc(cc='CC-01', date='2026-08-31'), ctc(cc='CC-02', date='2026-09-30'))
        f = fc(m)
        self.assertEqual((f['state'], f['reasons']), (CANT, ['FORECAST_VERSION_DATES_DISAGREE:F-1']))

    def test_no_version_and_a_method_that_needs_one(self):
        m = Mini()
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0']); m.budgets(bud(cc='CC-01'))
        m.set_policy(ctc_method={'default': 'declared'})
        self.assertEqual((fc(m)['state'], fc(m)['reasons']), (CANT, ['NO_FORECAST_VERSION']))
        m.set_policy(ctc_method={'default': 'declared_else_budget_less_actual', 'by_cost_code': {'CC-01': 'declared'}})
        self.assertEqual(fc(m)['reasons'], ['NO_FORECAST_VERSION'])

    def test_no_version_but_budget_methods_gives_a_derived_forecast_that_says_so(self):
        m = Mini()
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0']); m.budgets(bud(cc='CC-01', cents='5000000'))
        m.invoices(inv('INV-1', cc='CC-01', ex='1000000', date='2026-08-01')); m.reconcile()
        f = fc(m)
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 5000000))                 # forecast final cost = the budget, by the policy's method
        self.assertIn('FORECAST_DERIVED_FROM_BUDGET_NO_DECLARED_VERSION', f['reasons'])
        self.assertEqual(f['classified']['forecast_version'], '(derived from budget)')

    def test_no_budget_at_all_and_nothing_declared_cannot_be_assessed(self):
        m = Mini()
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0'])
        f = fc(m)
        self.assertEqual(f['state'], CANT)


class TestForecastQualification(unittest.TestCase):
    def test_stale_forecast_is_provisional_and_says_how_old(self):
        m = world()
        f = fc(m, as_of='2026-12-31')
        self.assertEqual(f['state'], PROV)
        self.assertTrue(any('is 92 days old, beyond the 45 configured' in u['input'] for u in f['unknown_inputs']))
        self.assertIn('STALE:forecast F-1', f['reasons'])

    def test_exactly_at_the_limit_is_fresh_one_day_over_is_stale(self):
        m = world()
        self.assertEqual(fc(m, as_of='2026-11-14')['state'], AUTH)                            # 45 days
        self.assertEqual(fc(m, as_of='2026-11-15')['state'], PROV)                            # 46 days

    def test_freshness_not_configured_is_an_open_decision_not_a_pass(self):
        m = world(); m.set_policy(freshness_days={})
        f = fc(m)
        self.assertEqual(f['state'], PROV)
        self.assertTrue(any('CR-02 A10' in u['decision'] for u in f['unknown_inputs']))

    def test_old_budget_is_stale_when_a_limit_is_configured(self):
        m = world(); m.set_policy(freshness_days={'forecast': 45, 'budget': 100, 'facility': 45})
        self.assertEqual(fc(m)['state'], PROV)

    def test_mixed_budget_revisions_are_disputed(self):
        m = world()
        m.budgets(bud(cc='CC-03', cents='100', rev='R1'))
        m.reconcile()
        f = fc(m)
        self.assertEqual(f['state'], PROV)
        self.assertIn('MIXED_BUDGET_REVISIONS', f['reasons'])
        self.assertEqual(f['classified']['budget_revision_labels'], ['R0', 'R1'])

    def test_held_budget_line_is_listed(self):
        m = world()
        m.budgets(bud(cc='CC-01', cents='9999999', rev='R0'))                                  # same key and revision, different amount: conflict
        m.reconcile()
        f = fc(m)
        self.assertEqual(f['state'], PROV)
        self.assertTrue(any(e['ref'] == 'budget_line/PRJ-001|CC-01' for e in f['excluded']))

    def test_revenue_that_cannot_be_assessed_means_no_forecast(self):
        m = world(); m.set_policy(tax_basis=None)
        self.assertEqual(fc(m)['state'], CANT)

    def test_provisional_revenue_makes_the_forecast_provisional(self):
        m = world()
        m.variations(var('V-A', status='approved', value='500')); m.reconcile()                # contract summary says 0: disagreement
        f = fc(m)
        self.assertEqual(f['state'], PROV)
        self.assertEqual(f['components']['forecast_revenue']['state'], PROV)

    def test_missing_method_decisions_name_the_open_decision(self):
        for fld, text in (('ctc_method', 'A3'), ('ffc_basis', 'A4'), ('cost_scope', 'A5')):
            m = world(); m.set_policy(**{fld: None})
            f = fc(m)
            self.assertEqual((f['state'], f['value']['cents']), (CANT, None), fld)
            self.assertIn(text, f['unknown_inputs'][0]['decision'], fld)

    def test_an_unapproved_policy_never_gives_an_authoritative_forecast(self):
        self.assertEqual(fc(world(approved=False))['state'], PROV)

    def test_a_negative_margin_is_a_value(self):
        m = world(inv_cc01='9000000', inv_cc02='2000000')
        m.ctcs(ctc(cc='CC-01', version='F-2', date='2026-09-30', cents='4000000')); m.reconcile()
        f = fc(m, extra={'forecast_version': 'F-2'})
        self.assertLess(f['value']['cents'], 0)


class TestRecognisedMargin(unittest.TestCase):
    def test_cost_to_cost_arithmetic(self):
        f = world().fig('fin.recognised_margin')
        c = f['classified']
        self.assertEqual((c['recognised_revenue_cents'], c['recognised_cost_cents']), (5333333, 4000000))             # 10,000,000 x 4,000,000 / 7,500,000, rounded once
        self.assertEqual(f['value']['cents'], 1333333)
        self.assertEqual((c['percent_complete_bps'], c['recognised_at'], c['method']), (5333, '2026-09-30', 'cost_to_cost'))
        self.assertEqual(f['state'], AUTH)

    def test_rounding_is_applied_once_and_matches_the_integer_rule(self):
        from apg.fin.fmath import round_div
        m = world(inv_cc01='1', inv_cc02='')
        m.ctcs(ctc(cc='CC-01', version='F-2', date='2026-09-30', cents='19999999')); m.reconcile()
        f = m.fig('fin.recognised_margin', extra={'forecast_version': 'F-2'})
        c = f['classified']
        ffc = f['components']['forecast_basis']['classified']['ffc_cents']
        self.assertEqual(c['recognised_revenue_cents'], round_div(10000000 * c['recognised_cost_cents'], ffc))

    def test_method_not_configured(self):
        m = world(); m.set_policy(recognition_method=None)
        f = m.fig('fin.recognised_margin')
        self.assertEqual((f['state'], f['value']['cents']), (CANT, None))
        self.assertIn('A5', f['unknown_inputs'][0]['decision'])

    def test_forecast_that_cannot_be_assessed_means_no_recognised_margin(self):
        m = world(); m.set_policy(ctc_method=None)
        self.assertEqual(m.fig('fin.recognised_margin')['state'], CANT)

    def test_provisional_forecast_makes_it_provisional_and_says_why(self):
        m = world(inv_cc02='3500000')
        f = m.fig('fin.recognised_margin')
        self.assertEqual(f['state'], PROV)
        self.assertIn('PERCENT_COMPLETE_RESTS_ON_A_FORECAST_THAT_IS_PROVISIONAL', f['reasons'])

    def test_zero_forecast_cost_is_not_a_division_by_zero(self):
        m = Mini()
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0'])
        m.budgets(bud(cc='CC-01', cents='0')); m.reconcile()
        f = m.fig('fin.recognised_margin')
        self.assertEqual(f['state'], CANT)
        self.assertEqual(f['reasons'], ['FORECAST_FINAL_COST_NOT_POSITIVE'])

    def test_percentages_have_explicit_outcomes(self):
        b = margins.pct_figure('p', world().fig('fin.recognised_margin'), 5333333, 'REV')
        self.assertEqual((b['state'], b['value']['bps']), (AUTH, 2500))                          # 1,333,333 / 5,333,333 = 25.00%
        z = margins.pct_figure('p', world().fig('fin.recognised_margin'), 0, 'REV')
        self.assertEqual((z['state'], z['reasons']), (CANT, ['NOT_APPLICABLE_REVENUE_ZERO_OR_NEGATIVE']))
        n = margins.pct_figure('p', world().fig('fin.recognised_margin'), -5, 'REV')
        self.assertEqual(n['state'], CANT)
        u = margins.pct_figure('p', world().fig('fin.recognised_margin'), None, 'REV')
        self.assertEqual((u['state'], u['reasons']), (CANT, ['REV_UNKNOWN']))
        gone = margins.pct_figure('p', Mini().fig('fin.recognised_margin'), 5, 'REV')
        self.assertEqual(gone['state'], CANT)                                                    # the margin itself cannot be assessed

    def test_cash_receipts_do_not_move_recognised_margin(self):
        m = world()
        a = m.fig('fin.recognised_margin')
        m.bank(['TX-1', '2026-09-01', '900000000', 'client receipt'])
        m.reconcile()
        self.assertEqual(m.fig('fin.recognised_margin'), a)

    def test_three_margins_are_three_distinct_named_views(self):
        m = world()
        r, f, c = m.fig('fin.recognised_margin'), m.fig('fin.forecast'), m.fig('fin.cash_adjusted')
        self.assertEqual((r['view'], f['view'], c['view']), ('recognised', 'forecast_final', 'cash_adjusted'))
        self.assertEqual(len({r['name'], f['name'], c['name']}), 3)
        self.assertNotEqual(r['value']['cents'], f['value']['cents'])


if __name__ == '__main__':
    unittest.main()
