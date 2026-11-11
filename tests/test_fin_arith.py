import unittest
from . import _path                                         # noqa: F401
from apg.fin import fmath, figure, policy as P
from apg.fin.figure import FigureBuilder, FigureError, AUTH, PROV, CANT


class TestRounding(unittest.TestCase):
    def test_half_away_from_zero(self):
        for n, d, want in ((5, 2, 3), (-5, 2, -3), (4, 2, 2), (-4, 2, -2), (1, 3, 0), (2, 3, 1), (-2, 3, -1), (0, 7, 0), (7, 7, 1), (3, 2, 2), (-3, 2, -2)):
            self.assertEqual(fmath.round_div(n, d), want, (n, d))

    def test_refuses_bad_operands(self):
        for n, d in ((1.0, 2), (1, 2.0), (True, 2), (1, 0), (1, -3)):
            with self.assertRaises((TypeError, ValueError)):
                fmath.round_div(n, d)

    def test_bps_zero_and_negative_denominator_is_none(self):
        self.assertIsNone(fmath.bps_of(5, 0))
        self.assertIsNone(fmath.bps_of(5, -10))
        self.assertEqual(fmath.bps_of(1, 3), 3333)
        self.assertEqual(fmath.bps_of(-1, 3), -3333)
        self.assertEqual(fmath.bps_of(0, 5), 0)

    def test_dates(self):
        self.assertEqual(fmath.days_between('2026-09-30', '2026-12-18'), 79)
        self.assertEqual(fmath.days_between('2026-12-18', '2026-09-30'), -79)
        self.assertEqual(fmath.days_between('2024-02-28', '2024-03-01'), 2)               # leap year
        for bad in ('2026-9-30', '30/09/2026', '2026-02-30', '', None, 20260930):
            with self.assertRaises((ValueError, TypeError)):
                fmath.parse_date(bad)

    def test_carrying_cost_formula(self):
        self.assertEqual(fmath.carrying_cents(11500000, 780, 79, 365), 194145)
        self.assertEqual(fmath.carrying_cents(0, 780, 79, 365), 0)
        self.assertEqual(fmath.carrying_cents(1000000, 0, 79, 365), 0)
        self.assertEqual(fmath.carrying_cents(1000000, 800, 0, 365), 0)
        self.assertNotEqual(fmath.carrying_cents(1000000, 800, 90, 365), fmath.carrying_cents(1000000, 800, 90, 360))    # the day-count basis matters
        self.assertEqual(fmath.carrying_cents(365, 10000, 1, 365), 1)                                                     # exact
        for args in ((-1, 1, 1, 365), (1, -1, 1, 365), (1, 1, -1, 365), (1, 1, 1, 0)):
            with self.assertRaises(ValueError):
                fmath.carrying_cents(*args)
        for args in ((1.5, 1, 1, 365), (1, True, 1, 365)):
            with self.assertRaises(TypeError):
                fmath.carrying_cents(*args)

    def test_rounded_once_not_in_the_middle(self):
        # 1 cent funded for many days: rounding at each step would give 0, rounding once gives the exact answer
        self.assertEqual(fmath.carrying_cents(100000, 1, 365, 365), 10)
        self.assertEqual(fmath.scale_cents(1, 1, 3), 0)
        self.assertEqual(fmath.scale_cents(2, 1, 3), 1)


def _b(**kw):
    return FigureBuilder('x', 'v', 'f', 1, {'project': 'P'}, '2026-09-30', {'version': 'V', '_approved': kw.get('approved', True)})


class TestFigureRules(unittest.TestCase):
    def test_clean_figure_is_authoritative(self):
        f = _b().finish(cents=10)
        self.assertEqual((f['state'], f['value']['cents']), (AUTH, 10))

    def test_no_value_is_cannot_assess_never_zero(self):
        b = _b(); b.unknown('i', 'no_data')
        f = b.finish()
        self.assertEqual(f['state'], CANT)
        self.assertIsNone(f['value']['cents'])
        with self.assertRaises(FigureError):
            _b().finish()                                                           # no value and no reason is refused: a figure that is not authoritative must say why
        self.assertEqual(_b().finish(cents=0)['state'], AUTH)                      # a genuine zero is a value

    def test_degrading_inputs_make_it_provisional(self):
        for fn in (lambda b: b.exclude('r', 'held', ['X']), lambda b: b.exclude('r', 'disputed', ['X']), lambda b: b.exclude('r', 'unattributed'), lambda b: b.unknown('i', 'no_data'),
                   lambda b: b.dispute('r', 'why'), lambda b: b.exclude('r', 'unknown_value'), lambda b: b.exclude('r', 'quarantined'), lambda b: b.exclude('r', 'not_counted'),
                   lambda b: b.exclude('r', 'unresolved_link')):
            b = _b(); fn(b)
            self.assertEqual(b.finish(cents=1)['state'], PROV)

    def test_by_design_exclusions_do_not_degrade(self):
        for cls in ('duplicate_delivery', 'after_cutoff', 'rejected_by_review'):
            b = _b(); b.exclude('r', cls, ['X'])
            self.assertEqual(b.finish(cents=1)['state'], AUTH, cls)

    def test_unapproved_policy_is_never_authoritative(self):
        self.assertEqual(_b(approved=False).finish(cents=1)['state'], PROV)

    def test_limits_and_reasons_do_not_degrade(self):
        b = _b(); b.limit('a stated limit'); b.reason('SOME_NOTE')
        self.assertEqual(b.finish(cents=1)['state'], AUTH)

    def test_composite_takes_the_worst_component(self):
        c = _b(); c.unknown('i', 'no_data'); child = c.finish(cents=1)
        b = _b(); b.child('c', child)
        f = b.finish(cents=2)
        self.assertEqual((f['state'], f['reasons']), (PROV, ['COMPONENT_PROVISIONAL:c']))      # the parent names the part it is waiting on
        gone = _b().cannot('NOPE')
        b = _b(); b.child('c', gone)
        with self.assertRaises(FigureError):
            b.finish(cents=2)                                                         # a value over a component that cannot be assessed is refused
        b = _b(); b.child('c', gone)
        f = b.finish()
        self.assertEqual((f['state'], f['reasons']), (CANT, ['COMPONENT_CANNOT_ASSESS:c']))

    def test_optional_component_that_cannot_be_assessed_degrades_to_provisional(self):
        b = _b(); b.child('c', _b().cannot('NOPE'), required=False)
        self.assertEqual(b.finish(cents=2)['state'], PROV)

    def test_cannot_names_the_open_decision(self):
        f = _b().cannot('METHOD_NOT_CONFIGURED', 'CR-02 A3')
        self.assertEqual(f['unknown_inputs'][0]['decision'], 'CR-02 A3')
        self.assertEqual(f['state'], CANT)

    def test_two_values_and_non_integer_values_refused(self):
        with self.assertRaises(FigureError):
            _b().finish(cents=1, bps=1)
        for bad in (1.5, '1', True):
            with self.assertRaises(FigureError):
                _b().finish(cents=bad)

    def test_unknown_exclusion_class_refused(self):
        with self.assertRaises(FigureError):
            _b().exclude('r', 'whatever')

    def test_validate_catches_tampered_figures(self):
        f = _b().finish(cents=1)
        bad = dict(f, state=AUTH, unknown_inputs=[{'input': 'i', 'reason': 'r', 'decision': ''}])
        with self.assertRaises(FigureError):
            figure.validate_figure(bad)
        bad = dict(f, state=CANT)
        with self.assertRaises(FigureError):
            figure.validate_figure(bad)
        bad = dict(f, value={'cents': None, 'bps': None})
        with self.assertRaises(FigureError):
            figure.validate_figure(bad)
        bad = dict(f, value={'cents': 1.5, 'bps': None})
        with self.assertRaises(Exception):
            figure.validate_figure(bad)

    def test_lists_are_sorted_so_the_hash_is_stable(self):
        a = _b(); a.exclude('b', 'held'); a.exclude('a', 'held'); a.unknown('z', 'x'); a.unknown('y', 'x')
        f = a.finish(cents=1)
        self.assertEqual([e['ref'] for e in f['excluded']], ['a', 'b'])
        self.assertEqual([u['input'] for u in f['unknown_inputs']], ['y', 'z'])

    def test_explain_is_readable(self):
        b = _b(); b.exclude('inv/1', 'held', ['SUPPLIER_AMBIGUOUS']); b.unknown('gst', 'no_data'); b.dispute('inv/2', 'conflict')
        text = '\n'.join(figure.explain(b.finish(cents=12345)))
        for part in ('provisional', '123.45', 'inv/1', 'SUPPLIER_AMBIGUOUS', 'unknown: gst', 'disputed: inv/2'):
            self.assertIn(part, text)


class TestPolicy(unittest.TestCase):
    def test_a_new_policy_configures_nothing(self):
        p = P.new_policy('V1', 'alice')
        for f in P.OPEN_DECISIONS:
            if f != 'freshness_days':
                self.assertIsNone(p.get(f), f)
        self.assertFalse(P.is_approved(p))
        self.assertEqual({f for f, _ in P.missing(p, list(P.OPEN_DECISIONS))}, set(P.OPEN_DECISIONS))

    def test_approval_rules(self):
        """APG-F67 (F-67): the proposer, another role, an AI and a service cannot approve; a human policy owner approves in person; the approval counts only with the
        audit log's confirmation."""
        from apg import policy_approval as PA
        from .helpers_ingest import World
        w = World()
        alice = w.who('a', 'zero_one', 'alice')
        P.store_policy(alice, P.new_policy('V1', 'alice'))
        for tok, user, role, kind in (('a2', 'alice', P.POLICY_ROLE, 'human'), ('b1', 'bob', 'someone_else', 'human'), ('b2', 'bob', P.POLICY_ROLE, 'ai'),
                                      ('b3', 'bob', P.POLICY_ROLE, 'service')):
            with self.assertRaises(P.PolicyError):
                P.approve_policy(w.who(tok, 'zero_one', user, (role,), kind), w.clock, 'V1', 'ok')
        p = P.approve_policy(w.who('b4', 'zero_one', 'bob', (P.POLICY_ROLE,)), w.clock, 'V1', 'ok')
        self.assertFalse(P.is_approved(p))
        self.assertTrue(P.is_approved(p, PA.confirmed(alice, P.POLICY_KIND, 'V1')))

    def test_validation_rejects_malformed_policies(self):
        bad = [dict(recognition_method='straight_line'), dict(ctc_method={'default': 'guess'}), dict(ctc_method={'by_cost_code': {}}), dict(ctc_method={'default': 'declared', 'by_cost_code': {'CC-1': 'x'}}),
               dict(ffc_basis='other'), dict(tax_basis='gross'), dict(gst_rate_bps=-1), dict(gst_rate_bps=True), dict(cost_scope=[]), dict(cost_scope=['labour']), dict(cost_scope=['supplier_invoices', 'supplier_invoices']),
               dict(variation_status_map={}), dict(variation_status_map={'x': 'maybe'}), dict(po_status_map={'open': 'live'}), dict(credit_reopens_commitment='yes'),
               dict(reconciliation_tolerance_cents=-1), dict(reconciliation_tolerance_cents=1.5), dict(freshness_days={'invoices': 3}), dict(freshness_days={'forecast': -1}),
               dict(carrying={'eligibility': 'as_of_to_release_due_date', 'rate_source': 'facility', 'day_count_basis': 365}),
               dict(carrying={'eligibility': 'x', 'rate_source': 'facility', 'day_count_basis': 365, 'funded_share_bps': 5000}),
               dict(carrying={'eligibility': 'as_of_to_release_due_date', 'rate_source': 'facility', 'day_count_basis': 364, 'funded_share_bps': 5000}),
               dict(carrying={'eligibility': 'as_of_to_release_due_date', 'rate_source': 'facility', 'day_count_basis': 365, 'funded_share_bps': 10001}),
               dict(carrying={'eligibility': 'as_of_to_release_due_date', 'rate_source': 'declared_proxy', 'day_count_basis': 365, 'funded_share_bps': 5000}),
               dict(carrying={'eligibility': 'as_of_to_release_due_date', 'rate_source': 'facility', 'day_count_basis': 365, 'funded_share_bps': 5000, 'proxy_rate_bps': 5}),
               dict(cash_adjustment={'base': 'recognised', 'components': []}), dict(cash_adjustment={'base': 'x', 'components': ['retention_carrying']}),
               dict(cash_adjustment={'base': 'recognised', 'components': ['retention_carrying', 'retention_carrying']}), dict(cash_adjustment={'base': 'recognised', 'components': ['interest']}),
               dict(unknown_field=1)]
        for kw in bad:
            self.assertTrue(P.validate_policy(dict({'version': 'V', 'proposer': 'a', 'approvals': []}, **kw)), kw)
        for kw in ({'version': ''}, {'proposer': ''}, {'approvals': [{'approver': 'a'}]}, {'approvals': 'x'}):
            self.assertTrue(P.validate_policy(dict({'version': 'V', 'proposer': 'a', 'approvals': []}, **kw)), kw)
        self.assertTrue(P.validate_policy('x'))
        with self.assertRaises(P.PolicyError):
            P.new_policy('V', 'a', recognition_method='nope')

    def test_valid_complete_policy(self):
        from apg.fin import demo_fin as DF
        p = DF.demo_policy()
        self.assertEqual(P.validate_policy(p), [])
        self.assertEqual((p['approvals'], P.is_approved(p)), ([], False))                  # APG-F67: the demonstration policy is a proposal; its owner approves it in person
        self.assertEqual(P.missing(p, list(P.OPEN_DECISIONS)), [])
        self.assertEqual(P.view(P.new_policy('V', 'a'))['_approved'], False)


if __name__ == '__main__':
    unittest.main()
