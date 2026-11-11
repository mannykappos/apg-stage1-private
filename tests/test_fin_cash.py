import unittest
from fractions import Fraction
from . import _path                                         # noqa: F401
from .helpers_fin import Mini, base_world, inv, bud, ctc, var, AS_OF
from apg.fin import cash_states as CS, cashview, calc_records as C
from apg.fin.figure import AUTH, PROV, CANT


def pos(m, what='retention', as_of=AS_OF):
    return m.fig('fin.cash_position', 'PRJ-001', as_of, {'what': what})


def ledger(m):
    return m.s.get('retention', 'PRJ-001').payload['fields']


def bankmap(m):
    return {'bank_txn/' + r.key: r.payload['fields'] for r in m.s.query('bank_txn')}


def actor(m, token, user, *roles, kind='human'):
    return m.w.who(token, 'zero_one', user=user, roles=roles, kind=kind)


def ev(m, who, frm, to, amt, evidence='EV-1', bank=None):
    return CS.record_event(who, m.clock, 'PRJ-001', ledger(m), frm, to, amt, evidence, bank=bank if bank is not None else bankmap(m))


def reconciled():
    m = base_world()
    m.reconcile()
    return m


class TestRetentionPools(unittest.TestCase):
    def test_ledger_balance_starts_as_withheld_and_nothing_else(self):
        f = pos(reconciled())
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 500000))
        self.assertEqual(f['classified']['pools_cents'], {'withheld': 500000, 'claimed': 0, 'approved': 0, 'disputed': 0, 'released': 0, 'received': 0})
        self.assertEqual(f['contributed'][0]['ref'], 'retention/PRJ-001')

    def test_the_full_path_one_evidenced_event_at_a_time(self):
        m = reconciled()
        clerk, boss = actor(m, 'c', 'clara', 'retention_clerk'), actor(m, 'b', 'bruno', 'retention_approver')
        ev(m, clerk, 'withheld', 'claimed', 300000, 'CLAIM-1')
        ev(m, boss, 'claimed', 'approved', 300000, 'CERT-1')
        ev(m, boss, 'approved', 'released', 300000, 'REL-1')
        m.bank(['TX-9', '2026-09-20', '300000', 'retention'])
        m.reconcile()
        ev(m, boss, 'released', 'received', 300000, 'bank_txn/TX-9')
        f = pos(m)
        self.assertEqual(f['classified']['pools_cents'], {'withheld': 200000, 'claimed': 0, 'approved': 0, 'disputed': 0, 'released': 0, 'received': 300000})
        self.assertEqual(f['value']['cents'], 200000)                                       # only what is still withheld
        self.assertEqual(sum(f['classified']['pools_cents'].values()), 500000)             # money is moved, never created
        self.assertEqual([c['ref'] for c in f['contributed'] if c['ref'].startswith('retention_event/')], ['retention_event/PRJ-001|000%d' % i for i in (1, 2, 3, 4)])

    def test_no_state_can_be_skipped(self):
        m = reconciled()
        boss = actor(m, 'b', 'bruno', 'retention_approver')
        for frm, to in (('withheld', 'approved'), ('withheld', 'released'), ('withheld', 'received'), ('claimed', 'released'), ('approved', 'received'), ('received', 'withheld')):
            with self.assertRaises(CS.RetentionError) as cx:
                ev(m, boss, frm, to, 1)
            self.assertEqual(cx.exception.code, 'TRANSITION_NOT_ALLOWED', (frm, to))
        self.assertEqual(list(m.s.query(CS.EVENT_KIND)), [])

    def test_cannot_move_more_than_the_pool_holds(self):
        m = reconciled()
        clerk = actor(m, 'c', 'clara', 'retention_clerk')
        with self.assertRaises(CS.RetentionError) as cx:
            ev(m, clerk, 'withheld', 'claimed', 500001)
        self.assertEqual(cx.exception.code, 'INSUFFICIENT_IN_POOL')
        ev(m, clerk, 'withheld', 'claimed', 500000)
        with self.assertRaises(CS.RetentionError) as cx:
            ev(m, clerk, 'withheld', 'claimed', 1)
        self.assertEqual(cx.exception.code, 'INSUFFICIENT_IN_POOL')

    def test_amounts_must_be_positive_whole_cents(self):
        m = reconciled()
        clerk = actor(m, 'c', 'clara', 'retention_clerk')
        for a in (0, -5, 1.5, True, '5', None):
            with self.assertRaises(CS.RetentionError) as cx:
                ev(m, clerk, 'withheld', 'claimed', a)
            self.assertEqual(cx.exception.code, 'AMOUNT_INVALID', repr(a))

    def test_evidence_is_required(self):
        m = reconciled()
        clerk = actor(m, 'c', 'clara', 'retention_clerk')
        with self.assertRaises(CS.RetentionError) as cx:
            ev(m, clerk, 'withheld', 'claimed', 1, evidence='')
        self.assertEqual(cx.exception.code, 'EVIDENCE_REQUIRED')

    def test_roles_and_human_actors(self):
        m = reconciled()
        nobody, clerk = actor(m, 'n', 'nina', 'importer'), actor(m, 'c', 'clara', 'retention_clerk')
        svc, ai = actor(m, 's', 'svc', 'retention_approver', kind='service'), actor(m, 'a', 'bot', 'retention_approver', kind='ai')
        boss = actor(m, 'b', 'bruno', 'retention_approver')
        with self.assertRaises(CS.RetentionError) as cx:
            ev(m, nobody, 'withheld', 'claimed', 1)
        self.assertEqual(cx.exception.code, 'CLERK_ROLE_REQUIRED')
        ev(m, clerk, 'withheld', 'claimed', 100)
        with self.assertRaises(CS.RetentionError) as cx:
            ev(m, clerk, 'claimed', 'approved', 100)                                         # a clerk may not take a consequential step
        self.assertEqual(cx.exception.code, 'APPROVER_ROLE_REQUIRED')
        for who in (svc, ai):
            with self.assertRaises(CS.RetentionError) as cx:
                ev(m, who, 'claimed', 'approved', 100)
            self.assertEqual(cx.exception.code, 'HUMAN_ACTOR_REQUIRED')
        ev(m, boss, 'claimed', 'approved', 100)
        self.assertEqual(len(m.s.query(CS.EVENT_KIND)), 2)

    def test_received_needs_a_bank_transaction_of_exactly_that_amount(self):
        m = reconciled()
        clerk, boss = actor(m, 'c', 'clara', 'retention_clerk'), actor(m, 'b', 'bruno', 'retention_approver')
        ev(m, clerk, 'withheld', 'claimed', 400000); ev(m, boss, 'claimed', 'approved', 400000); ev(m, boss, 'approved', 'released', 400000)
        for evid in ('nothing', 'bank_txn/TX-NOPE'):
            with self.assertRaises(CS.RetentionError) as cx:
                ev(m, boss, 'released', 'received', 400000, evid)
            self.assertEqual(cx.exception.code, 'BANK_EVIDENCE_REQUIRED')
        m.bank(['TX-1', '2026-09-20', '399999', 'close but no'])
        m.reconcile()
        with self.assertRaises(CS.RetentionError) as cx:
            ev(m, boss, 'released', 'received', 400000, 'bank_txn/TX-1')                       # one cent out: exact equality, no tolerance configured
        self.assertEqual(cx.exception.code, 'BANK_EVIDENCE_REQUIRED')
        m.bank(['TX-2', '2026-09-21', '400000', 'exact'])
        m.reconcile()
        ev(m, boss, 'released', 'received', 400000, 'bank_txn/TX-2')
        self.assertEqual(pos(m)['classified']['pools_cents']['received'], 400000)

    def test_dispute_is_a_side_state_that_returns_to_claimed_or_approved(self):
        m = reconciled()
        clerk, boss = actor(m, 'c', 'clara', 'retention_clerk'), actor(m, 'b', 'bruno', 'retention_approver')
        ev(m, clerk, 'withheld', 'claimed', 200000)
        ev(m, clerk, 'claimed', 'disputed', 200000)
        self.assertEqual(pos(m)['classified']['pools_cents']['disputed'], 200000)
        ev(m, boss, 'disputed', 'approved', 200000)
        self.assertEqual(pos(m)['classified']['pools_cents']['approved'], 200000)

    def test_a_forecast_release_date_passing_moves_nothing_and_asserts_no_entitlement(self):
        m = Mini()
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0'])
        m.retention(['PRJ-001', '500000', '2026-09-01', '', '']); m.reconcile()
        f = pos(m)
        self.assertEqual(f['value']['cents'], 500000)
        self.assertEqual(f['classified']['pools_cents']['released'], 0)
        self.assertEqual(f['classified']['flags'], ['RELEASE_REVIEW_DUE'])
        self.assertTrue(any(r.startswith('RELEASE_REVIEW_DUE') and 'not asserted' in r for r in f['reasons']))

    def test_ledger_with_a_release_date_puts_the_money_in_released_not_received(self):
        m = Mini()
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0'])
        m.retention(['PRJ-001', '500000', '2026-08-01', '2026-08-15', '']); m.reconcile()
        f = pos(m)
        self.assertEqual(f['classified']['pools_cents']['released'], 500000)
        self.assertEqual(f['classified']['pools_cents']['received'], 0)
        self.assertEqual(f['value']['cents'], 0)
        self.assertEqual(f['classified']['flags'], ['RELEASED_PER_LEDGER_CASH_RECEIPT_NOT_EVIDENCED'])

    def test_no_ledger_record_is_unknown_not_zero(self):
        m = Mini()
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0']); m.reconcile()
        f = pos(m)
        self.assertEqual((f['state'], f['value']['cents']), (CANT, None))

    def test_conflicting_ledger_versions_are_held_and_disputed(self):
        m = reconciled()
        m.retention(['PRJ-001', '600000', '2027-02-01', '', '']); m.reconcile()
        f = pos(m)
        self.assertEqual((f['state'], f['value']['cents']), (CANT, None))
        self.assertEqual(f['excluded'][0]['class'], 'disputed')

    def test_a_forged_or_damaged_event_sequence_is_found_when_the_pools_are_rederived(self):
        m = reconciled()
        clerk = actor(m, 'c', 'clara', 'retention_clerk')
        ev(m, clerk, 'withheld', 'claimed', 100000)
        good = m.s.get(CS.EVENT_KIND, 'PRJ-001|0001')
        bad = dict(good.payload); bad['seq'] = 3; bad['amount_cents'] = 900000
        m.s.put(CS.EVENT_KIND, 'PRJ-001|0003', bad, expected_revision=0)                     # a gap and an impossible amount written around the rules
        m.reconcile()
        f = pos(m)
        self.assertIn('RETENTION_EVENTS_INCONSISTENT', f['reasons'])
        self.assertEqual(f['state'], PROV)
        self.assertEqual(f['disputed'][0]['ref'], 'retention_event/PRJ-001')
        with self.assertRaises(CS.RetentionError) as cx:
            ev(m, clerk, 'claimed', 'disputed', 1)
        self.assertEqual(cx.exception.code, 'STORED_EVENTS_INCONSISTENT')

    def test_two_writers_racing_for_the_same_sequence_cannot_both_succeed(self):
        from apg.ports import ConflictError
        m = reconciled()
        clerk = actor(m, 'c', 'clara', 'retention_clerk')
        ev(m, clerk, 'withheld', 'claimed', 100000)
        stale = dict(m.s.get(CS.EVENT_KIND, 'PRJ-001|0001').payload)
        with self.assertRaises(ConflictError):
            m.s.put(CS.EVENT_KIND, 'PRJ-001|0001', dict(stale, amount_cents=1), expected_revision=0)

    def test_events_are_tenant_private(self):
        m = reconciled()
        clerk = actor(m, 'c', 'clara', 'retention_clerk')
        ev(m, clerk, 'withheld', 'claimed', 100000)
        other = m.w.who('o', 'other_tenant', user='olga', roles=('retention_clerk',))
        self.assertEqual(list(other.query(CS.EVENT_KIND)), [])

    def test_a_calculation_pins_the_events_it_used_and_reproduces(self):
        m = reconciled()
        clerk = actor(m, 'c', 'clara', 'retention_clerk')
        r1 = m.run('fin.cash_position', extra={'what': 'retention'})
        ev(m, clerk, 'withheld', 'claimed', 100000)
        r2 = m.run('fin.cash_position', extra={'what': 'retention'})
        self.assertEqual(r1['result']['classified']['pools_cents']['claimed'], 0)
        self.assertEqual(r2['result']['classified']['pools_cents']['claimed'], 100000)
        self.assertNotEqual(r1['run_key'], r2['run_key'])
        self.assertIn('retention_event/PRJ-001|0001', [c['ref'] for c in r2['result']['contributed']])
        chk = C.check_record(m.s, m.reg, r1['run_key'])
        self.assertEqual((chk['replay'].ok, chk['figure_valid'], chk['pins_consistent']), (True, True, True))                    # the earlier run still reproduces from its own pinned inputs


class TestSecurity(unittest.TestCase):
    def test_face_value_is_its_own_figure_and_not_a_cost_or_cash(self):
        f = pos(reconciled(), 'security')
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 1000000))
        self.assertEqual(f['classified']['instruments'][0]['face_value_cents'], 1000000)
        self.assertTrue(any('not cash' in l for l in f['limits']))

    def test_expiry_passing_raises_a_review_flag_only(self):
        m = reconciled()
        f = pos(m, 'security', '2027-07-01')
        self.assertEqual(f['classified']['flags'], ['EXPIRY_REVIEW:BG-1'])
        self.assertEqual(f['value']['cents'], 1000000)

    def test_several_instruments_add_and_unattributed_ones_are_listed_not_added(self):
        m = reconciled()
        m.security(['BG-2', 'PRJ-001', 'insurance_bond', '250000', '2027-09-01'])
        m.security(['BG-3', 'PRJ-404', 'bank_guarantee', '777', '2027-09-01'])
        m.reconcile()
        f = pos(m, 'security')
        self.assertEqual(f['value']['cents'], 1250000)
        self.assertEqual(sorted(i['instrument'] for i in f['classified']['instruments']), ['BG-1', 'BG-2'])

    def test_conflicting_instrument_is_held(self):
        m = reconciled()
        m.security(['BG-1', 'PRJ-001', 'bank_guarantee', '1100000', '2027-06-01']); m.reconcile()
        f = pos(m, 'security')
        self.assertEqual(f['state'], CANT)

    def test_no_instrument_is_unknown_not_zero(self):
        m = Mini()
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0']); m.reconcile()
        f = pos(m, 'security')
        self.assertEqual((f['state'], f['value']['cents']), (CANT, None))

    def test_security_carrying_cost_cannot_be_assessed(self):
        f = pos(reconciled(), 'security_carrying')
        self.assertEqual(f['state'], CANT)
        self.assertTrue(f['reasons'][0].startswith('NO_CASH_MARGIN_EVIDENCE'))


class TestCarryingCost(unittest.TestCase):
    def test_formula_matches_an_independent_exact_computation(self):
        f = pos(reconciled(), 'retention_carrying')
        exact = Fraction(500000, 1) * Fraction(5000, 10000) * Fraction(800, 10000) * 124 / 365      # funded balance x rate x days / basis
        self.assertAlmostEqual(float(exact), 6794.5, 1)
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 6795))
        i = f['classified']['inputs']
        self.assertEqual((i['funded_balance_cents'], i['eligible_days'], i['rate_bps'], i['rate_source'], i['to']), (250000, 124, 800, 'facility/FAC-1', '2027-02-01'))

    def test_retention_face_value_is_not_the_carrying_cost(self):
        m = reconciled()
        self.assertNotEqual(pos(m)['value']['cents'], pos(m, 'retention_carrying')['value']['cents'])
        self.assertTrue(any('NOT this figure' in l for l in pos(m, 'retention_carrying')['limits']))

    def test_day_count_basis_is_policy(self):
        m = reconciled(); m.set_policy(carrying=dict(m.policy['carrying'], day_count_basis=360))
        self.assertEqual(pos(m, 'retention_carrying')['value']['cents'], 6889)               # 250,000 x 8% x 124 / 360

    def test_funded_share_is_policy_and_zero_share_costs_nothing(self):
        m = reconciled(); m.set_policy(carrying=dict(m.policy['carrying'], funded_share_bps=0))
        self.assertEqual(pos(m, 'retention_carrying')['value']['cents'], 0)

    def test_not_configured_names_the_open_decision(self):
        m = reconciled(); m.set_policy(carrying=None)
        f = pos(m, 'retention_carrying')
        self.assertEqual((f['state'], f['reasons']), (CANT, ['CARRYING_NOT_CONFIGURED']))
        self.assertIn('A7', f['unknown_inputs'][0]['decision'])

    def test_no_release_date_cannot_be_assessed(self):
        m = Mini()
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0'])
        m.retention(['PRJ-001', '500000', '', '', '']); m.facility(['FAC-1', '5', '5', '800', '2026-09-30']); m.reconcile()
        self.assertIn('NO_EXPECTED_RELEASE_DATE', pos(m, 'retention_carrying')['reasons'])

    def test_a_passed_release_date_with_money_still_withheld_is_not_costed_as_zero(self):
        m = Mini()
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0'])
        m.retention(['PRJ-001', '500000', '2026-09-01', '', '']); m.facility(['FAC-1', '5', '5', '800', '2026-09-30']); m.reconcile()
        f = pos(m, 'retention_carrying')
        self.assertEqual((f['state'], f['value']['cents']), (CANT, None))
        self.assertTrue(f['reasons'][0].startswith('EXPECTED_RELEASE_DATE_PASSED_AND_NOT_RELEASED'))

    def test_nothing_withheld_costs_nothing(self):
        m = Mini()
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0'])
        m.retention(['PRJ-001', '0', '2026-09-01', '', '']); m.facility(['FAC-1', '5', '5', '800', '2026-09-30']); m.reconcile()
        self.assertEqual(pos(m, 'retention_carrying')['value']['cents'], 0)

    def test_facility_rate_problems(self):
        m = reconciled(); m.facility(['FAC-2', '1', '1', '900', '2026-09-30']); m.reconcile()
        self.assertEqual(pos(m, 'retention_carrying')['reasons'], ['SEVERAL_FACILITIES:facility/FAC-1,facility/FAC-2'.replace('facility/', '')])
        m2 = Mini()
        m2.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m2.contracts(['PRJ-001', '10000000', '0']); m2.retention(['PRJ-001', '500000', '2027-02-01', '', '']); m2.reconcile()
        self.assertEqual(pos(m2, 'retention_carrying')['reasons'], ['NO_FACILITY_STATEMENT'])
        m3 = reconciled(); m3.facility(['FAC-1', '50000000', '20000000', '950', '2026-09-30']); m3.reconcile()
        self.assertTrue(pos(m3, 'retention_carrying')['reasons'][0].startswith('FACILITY_RECORD_HELD'))

    def test_facility_statement_after_the_as_of_date_is_not_used(self):
        m = Mini()
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0'])
        m.retention(['PRJ-001', '500000', '2027-02-01', '', '']); m.facility(['FAC-1', '5', '5', '800', '2026-09-30']); m.reconcile()
        self.assertEqual(pos(m, 'retention_carrying', '2026-09-20')['reasons'], ['FACILITY_STATEMENT_AFTER_AS_OF'])

    def test_stale_facility_statement_makes_it_provisional(self):
        m = reconciled()
        f = pos(m, 'retention_carrying', '2026-12-31')
        self.assertEqual(f['state'], PROV)
        self.assertTrue(any('beyond the 45 configured' in u['input'] for u in f['unknown_inputs']))

    def test_proxy_rate_is_provisional_and_says_so(self):
        m = reconciled(); m.set_policy(carrying={'eligibility': 'as_of_to_release_due_date', 'rate_source': 'declared_proxy', 'proxy_rate_bps': 700, 'day_count_basis': 365, 'funded_share_bps': 5000})
        f = pos(m, 'retention_carrying')
        self.assertEqual((f['state'], f['value']['cents']), (PROV, 5945))
        self.assertIn('RATE_IS_A_POLICY_PROXY_NOT_AN_EVIDENCED_FACILITY_RATE', f['reasons'])

    def test_overlap_attestation_missing_is_provisional(self):
        m = reconciled()
        self.assertEqual(pos(m, 'retention_carrying')['state'], AUTH)                         # demo policy attests the overlap rule
        m.set_policy(carrying={k: v for k, v in m.policy['carrying'].items() if k != 'overlap'})
        f = pos(m, 'retention_carrying')
        self.assertEqual(f['state'], PROV)
        self.assertEqual(f['unknown_inputs'][0]['input'], 'overlap with other financing costs')

    def test_unapproved_policy_is_never_authoritative(self):
        self.assertEqual(pos(reconciled(), 'retention_carrying')['state'], AUTH)
        m = base_world(approved=False); m.reconcile()
        self.assertEqual(pos(m, 'retention_carrying')['state'], PROV)

    def test_the_cost_runs_forward_only(self):
        m = reconciled()
        early, late = pos(m, 'retention_carrying', '2026-09-30')['value']['cents'], pos(m, 'retention_carrying', '2026-12-01')['value']['cents']
        self.assertGreater(early, late)                                                        # fewer days left to the release date


class TestCashAdjustedMargin(unittest.TestCase):
    def test_base_less_listed_components(self):
        m = reconciled()
        c = m.fig('fin.cash_adjusted')
        base = c['components']['base_margin_forecast_final']
        self.assertEqual(c['classified']['cash_costs_cents'], 6795)
        self.assertEqual(c['value']['cents'], base['value']['cents'] - 6795)
        self.assertTrue(any('NOT a statutory or accounting margin' in l for l in c['limits']))
        self.assertEqual(c['view'], 'cash_adjusted')

    def test_recognised_base(self):
        m = reconciled(); m.set_policy(cash_adjustment={'base': 'recognised', 'components': ['retention_carrying']})
        c = m.fig('fin.cash_adjusted')
        self.assertIn('base_margin_recognised', c['components'])

    def test_a_defined_component_that_cannot_be_assessed_makes_the_whole_figure_unassessable(self):
        m = reconciled(); m.set_policy(cash_adjustment={'base': 'forecast_final', 'components': ['retention_carrying', 'overdue_receivables']})
        c = m.fig('fin.cash_adjusted')
        self.assertEqual((c['state'], c['value']['cents']), (CANT, None))
        self.assertEqual(c['reasons'], ['A_DEFINED_COMPONENT_CANNOT_BE_ASSESSED', 'COMPONENT_CANNOT_ASSESS:overdue_receivables'])
        self.assertTrue(m.fig('fin.cash_position', extra={'what': 'retention_carrying'})['value']['cents'] is not None)

    def test_overdue_receivables_are_never_assessed_without_receivables_data(self):
        m = reconciled(); m.set_policy(cash_adjustment={'base': 'forecast_final', 'components': ['overdue_receivables']})
        c = m.fig('fin.cash_adjusted')
        self.assertEqual(c['components']['overdue_receivables']['reasons'][0][:20], 'NO_RECEIVABLES_DATA:')

    def test_not_configured(self):
        m = reconciled(); m.set_policy(cash_adjustment=None)
        c = m.fig('fin.cash_adjusted')
        self.assertEqual((c['state'], c['reasons']), (CANT, ['CASH_ADJUSTMENT_NOT_CONFIGURED']))
        self.assertIn('A2', c['unknown_inputs'][0]['decision'])

    def test_provisional_parts_make_it_provisional(self):
        m = reconciled()
        self.assertEqual(m.fig('fin.cash_adjusted')['state'], AUTH)
        m.set_policy(carrying=dict(m.policy['carrying'], rate_source='declared_proxy', proxy_rate_bps=700))
        self.assertEqual(m.fig('fin.cash_adjusted')['state'], PROV)

    def test_the_three_margins_stay_separate_and_receipts_move_none_of_them(self):
        m = reconciled()
        a = [m.fig(f)['value']['cents'] for f in ('fin.recognised_margin', 'fin.forecast', 'fin.cash_adjusted')]
        m.bank(['TX-1', '2026-09-01', '123456789', 'a client receipt']); m.reconcile()
        b = [m.fig(f)['value']['cents'] for f in ('fin.recognised_margin', 'fin.forecast', 'fin.cash_adjusted')]
        self.assertEqual(a, b)
        self.assertEqual(len(set(a)), 3)


if __name__ == '__main__':
    unittest.main()
