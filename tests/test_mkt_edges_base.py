"""Edge-case tests for the base layer of the procurement analyses (common views, gatherer, FX, freshness gate, international checks): boundary values, one-of-two-conditions cases and
held/conflicted records, written to pin the contracts stated in the module docstrings."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_mkt import *
from apg.fin.snap import Facts
from apg.mkt import common as C, fresh as FR, fx as FX, gather as MG2, intl as IL

TH = {'quote_max_age_days': 45, 'index_max_age_days': 45, 'fx_max_age_days': 30}


def stored(fields, outcome='accepted', pending=(), received='2026-09-01'):
    """A stored (non-conflict) record payload as the intake writes it."""
    return {'fields': fields, 'intrinsic': {'outcome': outcome, 'pending': list(pending)}, 'provenance': {'received_at': received, 'source': 'synthetic'}}


def recon(outcome='accepted', lifecycle='active', duplicate_of=None, amount=0, findings=()):
    return {'effective_outcome': outcome, 'lifecycle': lifecycle, 'duplicate_of': duplicate_of, 'amount_cents': amount, 'findings': list(findings), 'supplier_id': 'SUP-001'}


def facts(**refs):
    """Facts over hand-made records: keyword names are 'kind__key' with the double underscore standing for '/'."""
    return Facts({k.replace('__', '/', 1): v for k, v in refs.items()}, {'pins': {}})


QUOTE_F = {'material_ref': 'MAT-STEEL', 'specification_text': 's', 'issue_date': '2026-09-01', 'valid_until': '2026-12-31', 'unit_rate_minor_units': 1000, 'currency_code': 'AUD'}


class TestQuantityReading(unittest.TestCase):
    def test_qty_micro_reads_non_negative_numbers_exactly_and_zero_is_a_number(self):
        table = [(0, 0), (5, 5 * C.MICRO), (-1, None), (True, None), (False, None), ('2.5', 2500000), ('0', 0), ('x', None), ('-1', None), (None, None)]
        for given, want in table:
            self.assertEqual(C.qty_micro(given), want, 'qty_micro(%r)' % (given,))

    def test_fmt_qty_keeps_only_the_significant_fraction(self):
        self.assertEqual((C.fmt_qty(5 * C.MICRO), C.fmt_qty(2500000), C.fmt_qty(1)), ('5', '2.5', '0.000001'))

    def test_fields_list_is_the_records_own_fields_or_every_contenders(self):
        self.assertEqual(C.fields_list({'fields': {'a': 1}}), [{'a': 1}])
        self.assertEqual(C.fields_list({'fields': None}), [{}])
        self.assertEqual(C.fields_list({}), [{}])
        marker = {'conflict': {'contenders': [{'fields': {'a': 1}}, {'fields': None}, {}]}}
        self.assertEqual(C.fields_list(marker), [{'a': 1}, {}, {}])


class TestQuoteView(unittest.TestCase):
    def view(self, payload, state):
        refs = {'supplier_quote__Q-1': payload}
        if state is not None:
            refs['recon_state__supplier_quote/Q-1'] = state
        return C.quote_view(facts(**refs), 'Q-1')

    def test_a_missing_quote_has_no_view(self):
        self.assertIsNone(C.quote_view(facts(), 'Q-1'))

    def test_reconciled_accepted_quote_is_ok_and_carries_its_fields(self):
        for outcome in ('accepted', 'accepted_with_warnings'):
            v = self.view(stored(QUOTE_F), recon(outcome))
            self.assertTrue(v['ok'], outcome)
            self.assertEqual((v['material'], v['issue'], v['valid_until'], v['rate'], v['cur'], v['why']), ('MAT-STEEL', '2026-09-01', '2026-12-31', 1000, 'AUD', []))

    def test_a_held_record_that_is_not_a_conflict_is_listed_with_its_own_reason_and_not_looked_up_further(self):
        v = self.view(stored(QUOTE_F, outcome='pending_reconciliation', pending=['AUTHORITATIVE_SOURCE_ABSENT']), recon('accepted'))
        self.assertEqual((v['ok'], v['why']), (False, ['AUTHORITATIVE_SOURCE_ABSENT']))
        v = self.view(stored(QUOTE_F, outcome='quarantined'), recon('accepted'))
        self.assertEqual((v['ok'], v['why']), (False, ['NOT_USABLE']))

    def test_a_conflict_marker_is_held_as_a_conflict(self):
        v = self.view({'conflict': {'contenders': [{'fields': QUOTE_F}, {'fields': dict(QUOTE_F, unit_rate_minor_units=2000)}]}}, recon('accepted'))
        self.assertEqual((v['ok'], v['why']), (False, ['CONFLICT_SAME_KEY']))

    def test_an_unreconciled_quote_is_not_ok(self):
        v = self.view(stored(QUOTE_F), None)
        self.assertEqual((v['ok'], v['why']), (False, ['NOT_RECONCILED']))

    def test_a_quote_is_ok_only_when_the_outcome_is_accepted_AND_it_is_not_a_duplicate(self):
        table = [('rejected', 'active', None, ['RECONCILIATION:rejected']),
                 ('pending_reconciliation', 'active', None, ['RECONCILIATION:pending_reconciliation']),
                 ('accepted', 'duplicate_of', 'Q-0', ['DUPLICATE_OF:Q-0']),
                 ('accepted_with_warnings', 'duplicate_of', 'Q-0', ['DUPLICATE_OF:Q-0']),
                 ('rejected', 'duplicate_of', 'Q-0', ['DUPLICATE_OF:Q-0'])]
        for outcome, life, dup, why in table:
            v = self.view(stored(QUOTE_F), recon(outcome, life, dup))
            self.assertEqual((v['ok'], v['why']), (False, why), (outcome, life))


class TestPurchaseOrderView(unittest.TestCase):
    PO_F = {'project_ref': 'PRJ-001', 'material_ref': 'MAT-STEEL', 'quantity': 10, 'unit_of_measure': 'tonne', 'unit_rate_cents': 100, 'order_date': '2026-08-01', 'source_status': 'open'}

    def view(self, payload, state=None):
        refs = {'purchase_order__PO-1': payload}
        if state is not None:
            refs['recon_state__purchase_order/PO-1'] = state
        return C.po_view(facts(**refs), 'PO-1')

    def test_a_missing_order_has_no_view(self):
        self.assertIsNone(C.po_view(facts(), 'PO-1'))

    def test_a_reconciled_order_with_a_positive_quantity_is_ok(self):
        v = self.view(stored(self.PO_F), recon(amount=1000))
        self.assertEqual((v['ok'], v['qty'], v['amount'], v['project'], v['why']), (True, 10 * C.MICRO, 1000, 'PRJ-001', []))

    def test_a_quantity_that_is_zero_negative_or_unreadable_is_not_positive(self):
        for q in (0, '0', '0.000000', -3, 'abc', '', True, None):
            v = self.view(stored(dict(self.PO_F, quantity=q)), recon())
            self.assertEqual((v['ok'], v['why']), (False, ['QUANTITY_NOT_POSITIVE']), 'quantity %r' % (q,))
        v = self.view(stored(dict(self.PO_F, quantity='0.000001')), recon())
        self.assertEqual((v['ok'], v['qty']), (True, 1))

    def test_a_held_order_that_is_not_a_conflict_keeps_its_own_hold_reasons(self):
        v = self.view(stored(self.PO_F, outcome='pending_reconciliation', pending=['NO_AUTHORITY_RULE']), recon())
        self.assertEqual((v['ok'], v['why']), (False, ['NO_AUTHORITY_RULE']))
        v = self.view({'conflict': {'contenders': [{'fields': self.PO_F}]}}, recon())
        self.assertEqual((v['ok'], v['why']), (False, ['CONFLICT_SAME_KEY']))

    def test_an_unreconciled_order_is_not_ok(self):
        self.assertEqual(self.view(stored(self.PO_F))['why'], ['NOT_RECONCILED'])

    def test_a_possible_duplicate_is_not_ok_but_names_the_other_orders_and_a_duplicate_names_the_original(self):
        finds = [{'code': 'DUPLICATE_CANDIDATE:PO-9'}, {'code': 'OTHER'}, {'code': 'DUPLICATE_CANDIDATE:PO-2'}]
        v = self.view(stored(self.PO_F), recon('pending_reconciliation', findings=finds))
        self.assertEqual((v['ok'], v['why'], v['dup_candidates']), (False, ['RECONCILIATION:pending_reconciliation'], ['PO-2', 'PO-9']))
        v = self.view(stored(self.PO_F), recon('accepted', 'duplicate_of', 'PO-0'))
        self.assertEqual((v['ok'], v['why'], v['duplicate_of']), (False, ['DUPLICATE_OF:PO-0'], 'PO-0'))


class TestDeliveryAndDemandViews(unittest.TestCase):
    DK = {'purchase_order_ref': 'PO-1', 'qty_delivered': '10', 'qty_accepted': '8', 'delivery_date': '2026-08-20', 'material_ref': 'MAT-STEEL'}

    def dview(self, **over):
        return C.delivery_view(facts(delivery__DK=stored(dict(self.DK, **over))), 'DK')

    def test_a_valid_delivery_reads_delivered_and_accepted_quantities(self):
        v = self.dview()
        self.assertEqual((v['ok'], v['delivered'], v['accepted'], v['po'], v['date']), (True, 10 * C.MICRO, 8 * C.MICRO, 'PO-1', '2026-08-20'))
        v = self.dview(qty_accepted=None)
        self.assertEqual((v['ok'], v['accepted']), (True, None))

    def test_a_zero_quantity_is_a_valid_quantity(self):
        v = self.dview(qty_delivered=0, qty_accepted=0)
        self.assertEqual((v['ok'], v['delivered'], v['accepted']), (True, 0, 0))
        v = self.dview(qty_delivered='0', qty_accepted='0')
        self.assertEqual((v['ok'], v['delivered'], v['accepted']), (True, 0, 0))

    def test_either_quantity_being_unreadable_makes_the_delivery_invalid(self):
        for over in ({'qty_delivered': 'abc'}, {'qty_accepted': 'abc'}, {'qty_delivered': '-1'}, {'qty_accepted': '-1'}, {'qty_delivered': 'abc', 'qty_accepted': 'abc'}):
            v = self.dview(**over)
            self.assertEqual((v['ok'], v['why']), (False, ['QUANTITY_INVALID']), over)

    def test_a_delivery_missing_a_needed_field_or_held_is_listed_not_used(self):
        v = self.dview(delivery_date=None)
        self.assertEqual((v['ok'], v['why']), (False, ['MISSING:delivery_date']))
        v = C.delivery_view(facts(delivery__DK=stored(self.DK, outcome='quarantined')), 'DK')
        self.assertEqual((v['ok'], v['why']), (False, ['NOT_USABLE']))

    def test_demand_needs_a_positive_quantity(self):
        d = {'project_ref': 'PRJ-001', 'material_ref': 'MAT-STEEL', 'quantity': '100', 'required_date': '2026-12-01', 'unit_text': 'tonne'}
        v = C.demand_view(facts(material_demand__D=stored(d)), 'D')
        self.assertEqual((v['ok'], v['qty'], v['unit'], v['required']), (True, 100 * C.MICRO, 'tonne', '2026-12-01'))
        for q in ('0', 'abc'):
            v = C.demand_view(facts(material_demand__D=stored(dict(d, quantity=q))), 'D')
            self.assertEqual((v['ok'], v['why']), (False, ['QUANTITY_NOT_POSITIVE']), q)


class TestUnitOf(unittest.TestCase):
    def test_unit_of_is_the_master_records_unit_or_none(self):
        F = facts(material__M1=stored({'unit_text': 'kg'}), material__M2=stored({'unit_text': 'kg'}, outcome='pending_reconciliation', pending=['X']), material__M3=stored({'description_text': 'd'}))
        self.assertEqual(C.unit_of(F, 'M1'), 'kg')
        self.assertIsNone(C.unit_of(F, 'M2'), 'a held master record gives no unit')
        self.assertIsNone(C.unit_of(F, 'M3'), 'a master record with no unit gives no unit')
        self.assertIsNone(C.unit_of(F, 'M-NONE'), 'an unknown material gives no unit')

    def test_unit_of_in_the_built_world(self):
        a = mkt_world().analysis()
        self.assertEqual(C.unit_of(a.F, 'MAT-STEEL'), 'tonne')
        self.assertEqual(C.unit_of(a.F, 'MAT-CONC40'), 'm3')
        self.assertIsNone(C.unit_of(a.F, 'MAT-NOPE'))


# ---------------------------------------------------------------------------------------------------------------- gatherer
class TestGather(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m = mkt_world()
        m.orders(pom('PO-1', project='PRJ-001'), pom('PO-2', project='PRJ-002'),
                 pom('PO-U', project='PRJ-001'), pom('PO-U', project='PRJ-002'))                       # one order id, two projects: the project cannot be told
        m.dockets(docket('DK-1', 'PO-1'), docket('DK-2', 'PO-2'), docket('DK-G', 'PO-GHOST'),
                  docket('DK-C', 'PO-1', delivered='5'), docket('DK-C', 'PO-1', delivered='6'))        # DK-C: two differing rows, a conflict marker that names no order
        m.demands(demand('DEM-1', 'PRJ-001'), demand('DEM-2', 'PRJ-002'), demand('DEM-U', 'PRJ-001'), demand('DEM-U', 'PRJ-002'))
        m.quotes(quote('Q-1', 'SUP-001', 'MAT-STEEL', 's', '2026-09-01', '2026-12-31', '1000'))        # ingested but NOT reconciled: it has no reconciliation state
        cls.m = m

    def pins(self, project=None):
        m = self.m
        if project:
            refs, params = MG2.gather_project(m.s, project, AS_OF, m.policy['version'], m.dp['version'], m.mp['version'], m.sp['version'])
        else:
            refs, params = MG2.gather_tenant(m.s, AS_OF, m.policy['version'], m.dp['version'], m.mp['version'], m.sp['version'], ['PRJ-001', 'PRJ-002'])
        self.assertEqual(sorted(params['pins']), sorted('%s/%s' % (r.kind, r.key) for r in refs))
        return set(params['pins']), params

    def test_the_conflict_fixtures_are_what_the_tests_below_assume(self):
        m = self.m
        self.assertTrue(m.s.get('purchase_order', 'PO-U').payload.get('conflict'))
        self.assertTrue(m.s.get('delivery', 'DK-C').payload.get('conflict'))
        self.assertTrue(m.s.get('material_demand', 'DEM-U').payload.get('conflict'))

    def test_a_project_run_pins_its_own_orders_and_orders_whose_project_cannot_be_told_but_no_other_projects_order(self):
        pins, params = self.pins('PRJ-001')
        self.assertIn('purchase_order/PO-1', pins)
        self.assertIn('purchase_order/PO-U', pins)
        self.assertNotIn('purchase_order/PO-2', pins)
        self.assertEqual((params['scope'], params['project'], params['authorised_projects']), ('project', 'PRJ-001', ['PRJ-001']))
        pins2, _ = self.pins('PRJ-002')
        self.assertIn('purchase_order/PO-2', pins2)
        self.assertIn('purchase_order/PO-U', pins2)
        self.assertNotIn('purchase_order/PO-1', pins2)

    def test_a_project_run_pins_deliveries_of_its_orders_and_deliveries_naming_no_order_only(self):
        pins, _ = self.pins('PRJ-001')
        self.assertIn('delivery/DK-1', pins)
        self.assertIn('delivery/DK-C', pins, 'a conflicted delivery names no order, so it may belong to any project')
        self.assertNotIn('delivery/DK-2', pins, 'a delivery against another project\'s order is not this project\'s')
        self.assertNotIn('delivery/DK-G', pins, 'a delivery against an order no stored record shows is not pinned for a project run')

    def test_a_project_run_pins_its_demand_and_demand_of_unknown_project_but_not_other_projects_demand(self):
        pins, _ = self.pins('PRJ-001')
        self.assertIn('material_demand/DEM-1', pins)
        self.assertIn('material_demand/DEM-U', pins)
        self.assertNotIn('material_demand/DEM-2', pins)

    def test_a_tenant_run_pins_every_order_delivery_and_demand(self):
        pins, params = self.pins()
        for ref in ('purchase_order/PO-1', 'purchase_order/PO-2', 'purchase_order/PO-U', 'delivery/DK-1', 'delivery/DK-2', 'delivery/DK-C', 'delivery/DK-G',
                    'material_demand/DEM-1', 'material_demand/DEM-2', 'material_demand/DEM-U'):
            self.assertIn(ref, pins)
        self.assertEqual((params['scope'], params['project'], params['authorised_projects']), ('tenant', None, ['PRJ-001', 'PRJ-002']))

    def test_reference_records_are_pinned_for_every_run_and_a_reconciliation_state_only_when_one_exists(self):
        for project in ('PRJ-001', None):
            pins, _ = self.pins(project)
            self.assertIn('supplier_quote/Q-1', pins)
            self.assertIn('material/MAT-STEEL', pins)
            self.assertNotIn('recon_state/supplier_quote/Q-1', pins, 'an unreconciled quote has no state to pin')
            self.assertIn('recon_state/purchase_order/PO-1', pins)
        self.m.reconcile()
        pins, _ = self.pins('PRJ-001')
        self.assertIn('recon_state/supplier_quote/Q-1', pins)

    def test_the_lookup_used_for_project_finding_returns_the_stored_payload_or_none(self):
        class Rec:
            payload = {'a': 1}

        class Scoped:
            def get(self, kind, key):
                return Rec() if (kind, key) == ('k', 'x') else None
        look = MG2._look(Scoped())
        self.assertEqual(look('k', 'x'), {'a': 1})
        self.assertIsNone(look('k', 'y'))


# ---------------------------------------------------------------------------------------------------------------- FX
def fx_world(*fx_rows):
    m = mkt_world()
    if fx_rows:
        m.fx(*fx_rows)
    return m


class TestFxEdges(unittest.TestCase):
    def ref(self, m, cur='USD', as_of=AS_OF):
        a = m.analysis(as_of=as_of)
        return FX.reference_rate(a.F, a.mp, cur, as_of)

    def test_conflicted_rates_of_other_pairs_or_later_days_are_not_counted_as_held_for_this_pair(self):
        m = fx_world(fxrow('2026-09-30', '0.60', 'AUD/EUR'), fxrow('2026-09-30', '0.61', 'AUD/EUR'),         # conflict, another pair
                     fxrow('2026-10-15', '0.70', 'AUD/USD'), fxrow('2026-10-15', '0.71', 'AUD/USD'))        # conflict, same pair, after the as-of day
        rec, why = self.ref(m)
        self.assertIsNone(rec)
        self.assertEqual(why, 'no usable AUD/USD rate on or before 2026-09-30')

    def test_a_conflict_for_this_pair_dated_exactly_the_as_of_day_is_counted_as_held(self):
        m = fx_world(fxrow('2026-09-30', '0.65', 'AUD/USD'), fxrow('2026-09-30', '0.66', 'AUD/USD'))
        rec, why = self.ref(m)
        self.assertEqual((rec, why), (None, 'no usable AUD/USD rate on or before 2026-09-30; 1 held or invalid rate records were not used'))
        m = fx_world(fxrow('2026-09-29', '0.65', 'AUD/USD'), fxrow('2026-09-29', '0.66', 'AUD/USD'), fxrow('2026-09-30', '0.65', 'AUD/EUR'))
        self.assertIn('; 1 held', self.ref(m)[1])

    def test_a_rate_dated_the_as_of_day_is_used_and_is_zero_days_old(self):
        rec, why = self.ref(fx_world(fxrow('2026-09-30', '0.6540')))
        self.assertEqual((why, rec['date'], rec['age_days'], rec['rate_micro']), ('', '2026-09-30', 0, 654000))

    def test_a_stored_rate_is_keyed_by_its_own_day_and_pair_so_two_rates_never_tie_for_the_same_pair_and_day(self):
        # the natural key of a rate IS '<fx_date>|<pair>': non-canonical dates are rejected, and a differently written pair is a different pair, so a tie between two stored keys cannot arise
        m = fx_world(fxrow('2026-9-30', '0.7000'), fxrow('2026-09-30', '0.6500'), fxrow('2026-09-30', '0.6600', 'aud/usd'), fxrow('2026-09-30', '0.6700'), fxrow('2026-09-29', '0.6400'))
        a = m.analysis()
        self.assertEqual(sorted(a.F.kind('fx_rate')), ['2026-09-29|AUD/USD', '2026-09-30|AUD/USD', '2026-09-30|aud/usd'])
        for key, p in a.F.kind('fx_rate').items():
            for f in C.fields_list(p):
                self.assertEqual(key, '%s|%s' % (f['fx_date'], f['currency_pair']))

    def test_divergence_is_absent_for_a_stated_conversion_of_zero_or_less(self):
        self.assertIsNone(FX.divergence_bps(100, 0))
        self.assertIsNone(FX.divergence_bps(100, -5))
        self.assertEqual(FX.divergence_bps(100, 100), 0)
        self.assertEqual(FX.divergence_bps(0, 100), -10000)
        self.assertEqual(FX.divergence_bps(101, 100), 100)


# ---------------------------------------------------------------------------------------------------------------- freshness
class TestFreshEdges(unittest.TestCase):
    def qstate(self, issue, valid, as_of=AS_OF):
        q = {'ref': 'supplier_quote/Q-1', 'issue': issue, 'valid_until': valid}
        return FR.quote_state(q, as_of, TH)

    def test_a_quote_issued_on_the_as_of_day_is_current_and_one_issued_the_next_day_is_future(self):
        s = self.qstate('2026-09-30', '2026-12-31')
        self.assertEqual((s['state'], s['age_days']), ('current', 0))
        s = self.qstate('2026-10-01', '2026-12-31')
        self.assertEqual((s['state'], s['age_days']), ('future', -1))

    def test_a_quote_valid_until_the_as_of_day_is_current_with_zero_days_left(self):
        s = self.qstate('2026-09-30', '2026-09-30')
        self.assertEqual((s['state'], s['days_to_expiry']), ('current', 0))

    def index(self, rows, as_of=AS_OF, material='MAT-STEEL'):
        m = mkt_world()
        m.observations(*rows)
        a = m.analysis(as_of=as_of)
        return FR.index_state(a.F, material, as_of, TH)

    def test_an_observation_dated_the_as_of_day_is_used_and_is_zero_days_old(self):
        s = self.index([obs('O1', date='2026-09-30')])
        self.assertEqual((s['state'], s['age_days'], s['observation']['date']), ('fresh', 0, '2026-09-30'))
        s = self.index([obs('O1', date='2026-10-01')])
        self.assertEqual((s['state'], s['observation']), ('unavailable', None))

    def test_two_observations_on_the_latest_day_resolve_to_the_first_key_in_order_not_the_last(self):
        s = self.index([obs('O2', date='2026-09-15', value='20000'), obs('O1', date='2026-09-15', value='10000'), obs('O0', date='2026-09-14', value='5000')])
        self.assertEqual((s['subject'], s['observation']['value_scaled']), ('market_observation/O1', 10000))

    def test_only_conflicts_for_this_material_on_or_before_the_as_of_day_are_counted_as_held(self):
        rows = [obs('OC', 'MAT-CU', '2026-09-15', '1'), obs('OC', 'MAT-CU', '2026-09-15', '2'),                # conflict, another material
                obs('OL', 'MAT-STEEL', '2026-10-15', '1'), obs('OL', 'MAT-STEEL', '2026-10-15', '2')]         # conflict, this material, after the as-of day
        s = self.index(rows)
        self.assertEqual((s['state'], s['held_records']), ('unavailable', 0))

    def test_a_conflict_for_this_material_dated_exactly_the_as_of_day_is_held(self):
        s = self.index([obs('OC', 'MAT-STEEL', '2026-09-30', '1'), obs('OC', 'MAT-STEEL', '2026-09-30', '2'), obs('O1', date='2026-09-10')])
        self.assertEqual((s['state'], s['held_records'], s['observation']['ref']), ('fresh', 1, 'market_observation/O1'))
        s = self.index([obs('OC', 'MAT-STEEL', '2026-09-30', '1'), obs('OC', 'MAT-STEEL', '2026-09-30', '2')])
        self.assertEqual((s['state'], s['held_records']), ('unavailable', 1))

    def stub_index(self, **observations):
        F = facts(**{('market_observation__' + k): v for k, v in observations.items()})
        return FR.index_state(F, 'MAT-STEEL', AS_OF, TH)

    def test_an_observation_is_used_only_when_it_is_usable_AND_its_value_is_a_whole_number(self):
        f = {'material_ref': 'MAT-STEEL', 'obs_date': '2026-09-15', 'value_scaled': 10930}
        s = self.stub_index(O1=stored(f))
        self.assertEqual((s['state'], s['held_records']), ('fresh', 0))
        s = self.stub_index(O1=stored(dict(f, value_scaled='10930')))                       # usable but not an integer
        self.assertEqual((s['state'], s['held_records']), ('unavailable', 1))
        s = self.stub_index(O1=stored(dict(f, value_scaled=None)))
        self.assertEqual((s['state'], s['held_records']), ('unavailable', 1))
        s = self.stub_index(O1=stored(f, outcome='pending_reconciliation', pending=['X']))  # an integer but not usable
        self.assertEqual((s['state'], s['held_records']), ('unavailable', 1))
        s = self.stub_index(O1=stored(f, outcome='pending_reconciliation', pending=['X']), O2=stored(dict(f, value_scaled=7)))
        self.assertEqual((s['state'], s['held_records'], s['observation']['value_scaled']), ('fresh', 1, 7))


# ---------------------------------------------------------------------------------------------------------------- international checks
class TestIntlEdges(unittest.TestCase):
    def setUp(self):
        self.m = mkt_world()
        self.m.quote_rows(quote('Q-I', 'SUP-004', 'MAT-STEEL', 's', '2026-09-10', '2026-12-31', '6900', 'USD', '0.6540', '2026-09-30', '800', 'FOB', '28'),
                          quote('Q-J', 'SUP-004', 'MAT-STEEL', 's', '2026-09-10', '2026-12-31', '6900', 'USD', '0.6540', '2026-09-30', '800', 'FOB', '28'))

    def run_checks(self, key='Q-I'):
        a = self.m.analysis()
        return IL.checks(a.F, a.mp, a.ctx.quotes[key])

    def test_each_row_says_whether_its_check_is_critical_from_the_policy(self):
        c = self.run_checks()
        self.assertEqual([(r['check'], r['critical']) for r in c['checks']],
                         [('customs_classification', True), ('duty_rate_confirmed', True), ('import_permit', True), ('supplier_vetting', False)])

    def test_the_reason_names_exactly_what_a_resolved_or_not_applicable_record_lacks(self):
        self.m.checks(['Q-I', 'customs_classification', 'resolved', '', 'carol', '2026-09-25'],           # no evidence
                      ['Q-I', 'duty_rate_confirmed', 'resolved', 'EV', '', '2026-09-25'],                 # no person
                      ['Q-I', 'import_permit', 'not_applicable', '', '', ''],                             # no person, no date
                      ['Q-I', 'supplier_vetting', 'unresolved', '', 'carol', '2026-09-25'])
        rows = {r['check']: r for r in self.run_checks()['checks']}
        for name in ('customs_classification', 'duty_rate_confirmed'):
            self.assertEqual((rows[name]['status'], rows[name]['why']), ('unresolved', 'recorded as resolved without a person, a date and an evidence reference'), name)
        self.assertEqual((rows['import_permit']['status'], rows['import_permit']['why']), ('unresolved', 'recorded as not_applicable without a person and a date'))
        self.assertEqual((rows['supplier_vetting']['status'], rows['supplier_vetting']['why']), ('unresolved', 'recorded as unresolved'))

    def test_not_applicable_needs_no_evidence_and_a_complete_resolved_record_is_resolved(self):
        self.m.checks(['Q-I', 'customs_classification', 'resolved', 'EV', 'carol', '2026-09-25'], ['Q-I', 'import_permit', 'not_applicable', '', 'carol', '2026-09-25'])
        rows = {r['check']: r for r in self.run_checks()['checks']}
        self.assertEqual((rows['customs_classification']['status'], rows['customs_classification']['why']), ('resolved', ''))
        self.assertEqual((rows['import_permit']['status'], rows['import_permit']['why']), ('not_applicable', ''))
        self.assertEqual(rows['import_permit']['checked_by'], 'carol')

    def test_a_check_recorded_for_another_quote_is_never_read_as_this_quotes(self):
        self.m.checks(['Q-J', 'customs_classification', 'resolved', 'EV-J', 'dave', '2026-09-25'], ['Q-J', 'import_permit', 'resolved', 'EV-J', 'dave', '2026-09-25'])
        c = self.run_checks('Q-I')
        self.assertEqual([r['status'] for r in c['checks']], ['unresolved'] * 4)
        self.assertEqual([r['ref'] for r in c['checks']], [None] * 4)
        self.assertEqual(c['held'], [])
        cj = self.run_checks('Q-J')
        statuses = {r['check']: r['status'] for r in cj['checks']}
        self.assertEqual((statuses['customs_classification'], statuses['import_permit'], statuses['duty_rate_confirmed']), ('resolved', 'resolved', 'unresolved'))
        self.assertEqual(cj['unresolved_critical'], ['duty_rate_confirmed'])

    def test_a_held_check_record_of_another_quote_is_not_listed_as_held_for_this_one(self):
        self.m.checks(['Q-J', 'customs_classification', 'resolved', 'EV', 'dave', '2026-09-25'], ['Q-J', 'customs_classification', 'unresolved', 'EV', 'dave', '2026-09-25'])   # conflict
        self.assertEqual(self.run_checks('Q-I')['held'], [])
        held = self.run_checks('Q-J')['held']
        self.assertEqual([h['ref'] for h in held], ['import_check/Q-J|customs_classification'])


if __name__ == '__main__':
    unittest.main()
