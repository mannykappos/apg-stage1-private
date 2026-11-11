import random, unittest
from . import _path                                         # noqa: F401
from .helpers_ingest import INV_H, World, csvb, inv, inv_file, load_suppliers, tpl
from apg.ingest import demo_setup as D, pipeline as P, reconcile as R, review, views
from apg.source_authority import Approval, AuthorityError, AuthorityRegister
from apg.ports import PortError

INVT, POT, CRT, PAYT, PMT, AMDT = (tpl(n) for n in ('TPL-BZ-AP-INVOICES', 'TPL-BZ-PURCHASE-ORDERS', 'TPL-BZ-CREDIT-NOTES', 'TPL-BZ-PAYMENTS', 'TPL-BZ-PM-INVOICES', 'TPL-BZ-PO-AMENDMENTS'))
PO_H = ['po_id', 'supplier_id', 'project_id', 'cost_code', 'po_date', 'material_id', 'qty', 'unit', 'unit_rate_cents', 'amount_cents', 'status']
CR_H = ['credit_id', 'supplier_id', 'against_invoice_id', 'credit_date', 'ex_gst_cents', 'gst_cents']
PAY_H = ['payment_id', 'invoice_id', 'payment_date', 'amount_cents']
PM_H = ['invoice_ref', 'supplier_id', 'project_id', 'ex_gst_cents', 'source']
AS_OF = '2026-09-30'
REG = D.demo_register()


def po(po_id='PO-1', supplier='SUP-001', project='PRJ-001', cc='CC-01', date='2026-04-01', qty='10', rate='100000', amt='1000000'):
    return [po_id, supplier, project, cc, date, 'MAT-1', qty, 'm3', rate, amt, 'open']


class Base(unittest.TestCase):
    def setUp(self):
        self.w = World(); self.s = self.w.who('imp', roles=('importer',))
        self.rec = self.w.who('rec', user='rita', roles=('reconciler',))
        self.rec2 = self.w.who('rec2', user='raj', roles=('reconciler',))
        self.stew = self.w.who('stew', user='sam', roles=('entity_steward',))
        load_suppliers(self.w, self.s)
        self.n = 0

    def put(self, template, header, rows, source, **kw):
        self.n += 1
        return P.ingest_file(self.s, self.w.clock, template, csvb(header, rows), source, f'f{self.n}.csv', D.DEMO_POLICY, kw.get('rev'))

    def invs(self, *rows, source='accounting'):
        return self.put(INVT, INV_H, rows, source)

    def rc(self, register=REG):
        return R.reconcile(self.s, register, AS_OF)

    def state(self, kind, key):
        return self.s.get('recon_state', f'{kind}/{key}').payload

    def outcome(self, kind, key):
        return self.state(kind, key)['effective_outcome']

    def codes(self, kind, key):
        return [f['code'] for f in self.state(kind, key)['findings']]


class TestAuthority(Base):
    def test_no_register_means_nothing_is_authoritative(self):
        self.invs(inv())
        self.rc(None)
        self.assertEqual((self.outcome('ap_invoice', 'INV-1'), self.codes('ap_invoice', 'INV-1')), ('pending_reconciliation', ['NO_APPROVED_REGISTER']))
        auth, prov = views.invoice_cost_view(self.s, AS_OF)
        self.assertEqual((auth.cents, auth.included), (0, ()))

    def test_unapproved_registers_do_not_count(self):
        self.invs(inv())
        for reg in (D.demo_register(approved=False), AuthorityRegister('X', D.demo_register().rules, 'p', (Approval('p', 'authority_owner', 'human', '2026-09-30'),)),
                    AuthorityRegister('X', D.demo_register().rules, 'p', (Approval('q', 'authority_owner', 'service', '2026-09-30'),)),
                    AuthorityRegister('X', D.demo_register().rules, 'p', (Approval('q', 'reviewer', 'human', '2026-09-30'),))):
            self.rc(reg)
            self.assertEqual(self.outcome('ap_invoice', 'INV-1'), 'pending_reconciliation')

    def test_a_field_without_a_rule_is_not_authoritative(self):
        self.invs(inv())
        reg = AuthorityRegister('R2', tuple(r for r in D.demo_register().rules if r.entity_kind != 'ap_invoice'), 'p', D.demo_register().approvals)
        self.rc(reg)
        self.assertEqual(self.codes('ap_invoice', 'INV-1'), ['NO_AUTHORITY_RULE'])

    def test_a_recognised_connector_is_not_automatically_authoritative(self):
        self.invs(inv(), source='some_other_connector')
        self.rc()
        self.assertEqual((self.outcome('ap_invoice', 'INV-1'), self.codes('ap_invoice', 'INV-1')), ('pending_reconciliation', ['AUTHORITATIVE_SOURCE_ABSENT']))

    def test_accepted_with_an_approved_register_and_the_register_version_is_recorded(self):
        self.invs(inv())
        self.rc()
        self.assertEqual((self.outcome('ap_invoice', 'INV-1'), self.state('ap_invoice', 'INV-1')['register_version']), ('accepted_with_warnings', 'SYN-REG-1'))   # PO ref missing warning

    def test_secondary_source_disagreement_quarantines(self):
        self.invs(inv(po='PO-1', ex='500')); self.put(POT, PO_H, [po()], 'procurement')
        self.put(PMT, PM_H, [['INV-1', 'SUP-001', 'PRJ-001', '600', 'pm']], 'pm_system')
        self.rc()
        self.assertEqual((self.outcome('ap_invoice', 'INV-1'), self.codes('ap_invoice', 'INV-1')), ('quarantined', ['SECONDARY_DISAGREES:pm_system']))
        auth, prov = views.invoice_cost_view(self.s, AS_OF)
        self.assertEqual(auth.included, ())
        self.assertEqual([x[0] for x in auth.excluded], ['INV-1'])
        self.assertEqual(prov.unverified[0][:2], ('INV-1', 'quarantined'))

    def test_secondary_source_that_agrees_changes_nothing(self):
        self.invs(inv(po='PO-1', ex='500')); self.put(POT, PO_H, [po()], 'procurement')
        self.put(PMT, PM_H, [['INV-1', 'SUP-001', 'PRJ-001', '500', 'pm']], 'pm_system')
        self.rc()
        self.assertEqual(self.outcome('ap_invoice', 'INV-1'), 'accepted')

    def test_secondary_with_no_primary_is_held_and_never_stands_in(self):
        self.put(PMT, PM_H, [['INV-9', 'SUP-001', 'PRJ-001', '500', 'pm']], 'pm_system')
        self.rc()
        self.assertEqual(self.outcome('pm_invoice', 'INV-9'), 'pending_reconciliation')
        auth, _ = views.invoice_cost_view(self.s, AS_OF)
        self.assertEqual(auth.cents, 0)

    def test_the_secondary_is_not_authoritative_even_when_it_is_the_only_value(self):
        self.put(PMT, PM_H, [['INV-9', 'SUP-001', 'PRJ-001', '500', 'pm']], 'pm_system')
        self.invs(inv('INV-9', ex=''))              # accounting row rejected: required amount missing
        self.rc()
        self.assertIsNone(self.s.get('ap_invoice', 'INV-9'))
        self.assertEqual(views.invoice_cost_view(self.s, AS_OF)[0].cents, 0)

    def test_authority_rule_effective_dates_apply(self):
        self.invs(inv())
        self.assertEqual(R.reconcile(self.s, REG, '2024-01-01')['by_outcome'].get('accepted_with_warnings', 0) >= 0, True)
        self.assertEqual(self.codes('ap_invoice', 'INV-1'), ['NO_AUTHORITY_RULE'])


class TestRelationships(Base):
    def test_invoice_before_its_po_is_held_not_dropped_then_clears_by_itself(self):
        self.invs(inv(po='PO-7'))
        self.rc()
        self.assertEqual(self.codes('ap_invoice', 'INV-1'), ['PO_NOT_VISIBLE:PO-7'])
        self.assertEqual(len(R.ReviewQueue(self.s).open_items()), 1)
        self.put(POT, PO_H, [po('PO-7')], 'procurement')
        rep = self.rc()
        self.assertEqual((self.outcome('ap_invoice', 'INV-1'), rep['closed']), ('accepted', 1))
        self.assertEqual(R.ReviewQueue(self.s).open_items(), ())
        self.assertEqual(self.s.get('quarantine', 'ap_invoice/INV-1').payload['status'], 'resolved_by_data')

    def test_po_mismatches_hold_the_invoice(self):
        self.put(POT, PO_H, [po('PO-1', supplier='SUP-002', project='PRJ-002', cc='CC-09')], 'procurement')
        self.invs(inv(po='PO-1'))
        self.rc()
        self.assertEqual(sorted(c.split(':')[0] for c in self.codes('ap_invoice', 'INV-1')), ['PO_COST_CODE_MISMATCH', 'PO_PROJECT_MISMATCH', 'PO_SUPPLIER_MISMATCH'])
        self.assertEqual(self.outcome('ap_invoice', 'INV-1'), 'pending_reconciliation')

    def test_amendment_for_an_unknown_po_is_held(self):
        self.put(AMDT, ['amendment_id', 'po_id', 'amendment_date', 'delta_cents', 'approved_change_ref', 'reason'], [['AMD-1', 'PO-404', '2026-05-01', '5000', 'VAR-1', 'x']], 'procurement')
        self.rc()
        self.assertEqual(self.codes('po_amendment', 'AMD-1'), ['PO_NOT_VISIBLE:PO-404'])

    def test_exact_duplicate_counts_once_whichever_arrives_first(self):
        a, b = inv('INV-0001'), inv('INV-0183', batch='B-replay')
        for order in ((a, b), (b, a)):
            w = World(); s = w.who('i'); load_suppliers(w, s)
            for i, row in enumerate(order):
                P.ingest_file(s, w.clock, INVT, csvb(INV_H, [row]), 'accounting', f'f{i}.csv', D.DEMO_POLICY)
            R.reconcile(s, REG, AS_OF)
            st = {k: s.get('recon_state', f'ap_invoice/{k}').payload for k in ('INV-0001', 'INV-0183')}
            self.assertEqual((st['INV-0001']['lifecycle'], st['INV-0183']['lifecycle'], st['INV-0183']['duplicate_of']), ('current', 'duplicate_of', 'INV-0001'))
            auth, prov = views.invoice_cost_view(s, AS_OF)
            self.assertEqual((auth.cents, auth.included), (1000000, ('INV-0001',)))
            self.assertEqual(prov.unverified, ())

    def test_same_supplier_invoice_number_with_different_details_holds_both(self):
        self.invs(inv('INV-1', sin='SI-5', ex='100'), inv('INV-2', sin='SI-5', ex='999'))
        self.rc()
        for k, other in (('INV-1', 'INV-2'), ('INV-2', 'INV-1')):
            self.assertIn('DUPLICATE_CANDIDATE:' + other, self.codes('ap_invoice', k))
            self.assertEqual(self.outcome('ap_invoice', k), 'pending_reconciliation')

    def test_look_alike_details_without_a_supplier_number_are_a_candidate_not_a_duplicate(self):
        self.put(POT, PO_H, [po('PO-1'), po('PO-2')], 'procurement')
        self.rc()
        self.assertEqual([self.outcome('purchase_order', k) for k in ('PO-1', 'PO-2')], ['pending_reconciliation'] * 2)
        self.assertEqual(self.state('purchase_order', 'PO-2')['lifecycle'], 'current')

    def test_credit_reissue_net_cost_is_the_reissued_amount(self):
        self.invs(inv('INV-0184', sin='SI-80001', ex='6000000', gst='600000'), inv('INV-0185', sin='SI-80001R', ex='5800000', gst='580000', date='2026-07-26'))
        self.put(CRT, CR_H, [['CRN-1', 'SUP-001', 'INV-0184', '2026-07-25', '6000000', '600000']], 'accounting')
        self.rc()
        auth, _ = views.invoice_cost_view(self.s, AS_OF)
        self.assertEqual(auth.cents, 5800000)
        lin = self.state('ap_invoice', 'INV-0184')['lineage']
        self.assertEqual((lin['credits'], lin['reissue_candidates']), (['CRN-1'], ['INV-0185']))
        self.assertEqual(views.gst_view(self.s).cents, 580000)

    def test_an_untrusted_credit_keeps_its_invoice_out_of_the_authoritative_figure(self):
        self.invs(inv('INV-1', ex='1000'), inv('INV-2', sin='SI-2', ex='400'))
        self.put(CRT, CR_H, [['CRN-1', 'SUP-001', 'INV-1', '2026-07-25', '1000', '']], 'pending_source')
        self.rc()
        auth, _ = views.invoice_cost_view(self.s, AS_OF)
        self.assertEqual(auth.cents, 400)                    # INV-1 is NOT counted at its gross
        self.assertEqual(dict((x[0], x[2]) for x in auth.excluded)['INV-1'], ('LINKED_CREDIT_UNRESOLVED:CRN-1',))

    def test_credit_for_an_invoice_that_is_not_visible_yet_is_held(self):
        self.put(CRT, CR_H, [['CRN-1', 'SUP-001', 'INV-404', '2026-07-25', '1000', '']], 'accounting')
        self.rc()
        self.assertEqual(self.codes('credit_note', 'CRN-1'), ['CREDIT_TARGET_NOT_VISIBLE:INV-404'])
        self.assertEqual(views.invoice_cost_view(self.s, AS_OF)[0].cents, 0)

    def test_credits_beyond_the_invoice_hold_every_credit(self):
        self.invs(inv('INV-1', ex='1000'))
        self.put(CRT, CR_H, [['CRN-1', 'SUP-001', 'INV-1', '2026-07-25', '600', ''], ['CRN-2', 'SUP-001', 'INV-1', '2026-07-26', '700', '']], 'accounting')
        self.rc()
        for k in ('CRN-1', 'CRN-2'):
            self.assertEqual(self.codes('credit_note', k), ['CREDIT_EXCEEDS_INVOICE:INV-1'])

    def test_credit_from_a_different_supplier_is_held(self):
        self.invs(inv('INV-1', ex='1000'))
        self.put(CRT, CR_H, [['CRN-1', 'SUP-002', 'INV-1', '2026-07-25', '600', '']], 'accounting')
        self.rc()
        self.assertEqual(self.codes('credit_note', 'CRN-1'), ['CREDIT_SUPPLIER_MISMATCH:INV-1'])

    def test_payment_checks(self):
        self.invs(inv('INV-1', ex='1000', gst='100'), inv('INV-2', sin='SI-2', ex='500', gst=''))
        self.put(PAYT, PAY_H, [['P1', 'INV-1', '2026-06-01', '1100'], ['P2', 'INV-1', '2026-06-02', '1'], ['P3', 'INV-404', '2026-06-01', '5'], ['P4', 'INV-2', '2026-06-01', '9999']], 'accounting')
        self.rc()
        self.assertEqual(self.codes('payment', 'P1'), ['PAYMENT_EXCEEDS_INVOICE:INV-1'])
        self.assertEqual(self.codes('payment', 'P3'), ['PAYMENT_TARGET_NOT_VISIBLE:INV-404'])
        self.assertEqual((self.outcome('payment', 'P4'), 'PAYMENT_LIMIT_UNCHECKED' in self.state('payment', 'P4')['warnings']), ('accepted_with_warnings', True))


class TestSuppliers(Base):
    def test_ambiguous_text_is_not_forced_and_a_person_can_resolve_it(self):
        self.invs(inv('INV-1', supplier='Metro Steel'))
        self.rc()
        self.assertEqual(self.codes('ap_invoice', 'INV-1'), ['SUPPLIER_AMBIGUOUS:SUP-003,SUP-004'])
        self.assertIsNone(self.state('ap_invoice', 'INV-1')['supplier_id'])
        review.resolve_supplier(self.stew, 'ap_invoice', 'INV-1', 'SUP-003', 'checked the ABN on the PDF')
        self.rc()
        st = self.state('ap_invoice', 'INV-1')
        self.assertEqual((st['effective_outcome'], st['supplier_id'], st['supplier_basis']), ('accepted_with_warnings', 'SUP-003', 'human_resolution'))
        self.assertIn('SUPPLIER_RESOLVED_BY_PERSON:SUP-003', st['warnings'])

    def test_a_single_resembling_candidate_still_needs_confirmation(self):
        self.invs(inv('INV-1', supplier='Alpha Concrete'))
        self.rc()
        self.assertEqual(self.codes('ap_invoice', 'INV-1'), ['SUPPLIER_NEEDS_CONFIRMATION:SUP-001'])
        self.assertIsNone(self.state('ap_invoice', 'INV-1')['supplier_id'])

    def test_unknown_supplier_and_missing_master(self):
        self.invs(inv('INV-1', supplier='SUP-404'))
        self.rc()
        self.assertEqual(self.codes('ap_invoice', 'INV-1'), ['SUPPLIER_UNRESOLVED'])
        w = World(); s = w.who('i')
        P.ingest_file(s, w.clock, INVT, inv_file(inv()), 'accounting', 'f.csv', D.DEMO_POLICY)
        R.reconcile(s, REG, AS_OF)
        self.assertEqual(s.get('recon_state', 'ap_invoice/INV-1').payload['findings'][0]['code'], 'SUPPLIER_UNVERIFIABLE_NO_MASTER')
        R.reconcile(s, REG, AS_OF, R.ReconcileConfig(supplier_master_required=False))
        self.assertIn('SUPPLIER_NOT_CHECKED', s.get('recon_state', 'ap_invoice/INV-1').payload['warnings'])

    def test_resolution_roles_and_staleness(self):
        self.invs(inv('INV-1', supplier='Metro Steel'))
        for who in (self.rec, self.s, self.w.who('ai', user='bot', roles=('entity_steward',), kind='ai')):
            with self.assertRaises(AuthorityError):
                review.resolve_supplier(who, 'ap_invoice', 'INV-1', 'SUP-003', 'x')
        with self.assertRaises(AuthorityError):
            review.resolve_supplier(self.stew, 'ap_invoice', 'INV-1', 'SUP-003', ' ')
        with self.assertRaises(AuthorityError):
            review.resolve_supplier(self.stew, 'ap_invoice', 'INV-1', 'SUP-999', 'n')
        review.resolve_supplier(self.stew, 'ap_invoice', 'INV-1', 'SUP-003', 'ok')
        self.invs(inv('INV-1', supplier='Metro Steel Fixings Inc', ex='1001'))           # the record now says something else: the old decision no longer applies
        self.rc()
        self.assertNotIn('SUPPLIER_RESOLVED_BY_PERSON:SUP-003', self.state('ap_invoice', 'INV-1')['warnings'])

    def test_alias_needs_a_second_person(self):
        review.propose_alias(self.stew, 'M Steel', 'SUP-003')
        with self.assertRaises(AuthorityError):
            review.approve_alias(self.stew, 'M Steel', 'self')
        review.approve_alias(self.w.who('stew2', user='sue', roles=('entity_steward',)), 'M Steel', 'checked')
        self.invs(inv('INV-1', supplier='M Steel'))
        self.rc()
        self.assertEqual(self.state('ap_invoice', 'INV-1')['supplier_basis'], 'approved_alias')

    def test_a_proposed_alias_does_nothing(self):
        review.propose_alias(self.stew, 'M Steel', 'SUP-003')
        self.invs(inv('INV-1', supplier='M Steel'))
        self.rc()
        self.assertEqual(self.codes('ap_invoice', 'INV-1'), ['SUPPLIER_UNRESOLVED'])


class TestReviewDecisions(Base):
    def conflicted(self):
        self.invs(inv('INV-1', ex='500'))
        self.invs(inv('INV-1', ex='700'))
        self.rc()

    def test_a_conflict_is_held_visible_and_excluded(self):
        self.conflicted()
        self.assertEqual(self.outcome('ap_invoice', 'INV-1'), 'quarantined')
        item = R.ReviewQueue(self.s).open_items()[0]
        self.assertEqual((item.key, sorted(c[1] for c in item.payload['candidates'])), ('ap_invoice/INV-1', ['500', '700']))
        self.assertEqual(views.invoice_cost_view(self.s, AS_OF)[0].cents, 0)

    def test_accept_is_refused_when_values_differ_and_correct_needs_two_people_if_the_rule_says_so(self):
        self.conflicted()
        with self.assertRaises(AuthorityError):
            review.decide(self.rec, 'ap_invoice/INV-1', 'accept', 'looks fine')
        review.decide(self.rec, 'ap_invoice/INV-1', 'correct', 'confirmed 700 with the supplier statement', 700)
        self.rc()
        st = self.state('ap_invoice', 'INV-1')
        self.assertEqual((st['effective_outcome'], st['amount_cents'], st['review']['action']), ('accepted_with_warnings', 700, 'correct'))
        self.assertIn('PROMOTED_BY_REVIEW:correct', st['warnings'])
        self.assertEqual(views.invoice_cost_view(self.s, AS_OF)[0].cents, 700)
        # the original evidence is untouched
        self.assertEqual(len(self.s.history('ap_invoice', 'INV-1')), 2)

    def test_who_may_decide(self):
        self.conflicted()
        for who in (self.s, self.stew, self.w.who('ai2', user='bot', roles=('reconciler',), kind='ai'), self.w.who('svc', user='svc', roles=('reconciler',), kind='service')):
            with self.assertRaises(AuthorityError):
                review.decide(who, 'ap_invoice/INV-1', 'correct', 'n', 700)
        with self.assertRaises(AuthorityError):
            review.decide(self.rec, 'ap_invoice/INV-1', 'correct', '  ', 700)
        with self.assertRaises(AuthorityError):
            review.decide(self.rec, 'ap_invoice/INV-1', 'correct', 'n')                # a correction needs a value
        self.rc()
        self.assertEqual(self.outcome('ap_invoice', 'INV-1'), 'quarantined')

    def test_two_approvals_are_enforced_from_the_register_rule(self):
        from apg.source_authority import AuthorityRule
        rules = tuple(r if r.entity_kind != 'ap_invoice' else AuthorityRule('ap_invoice', 'amount_ex_gst_cents', 'accounting', ('pm_system',), 'source_owned', 'quarantine', 'reconciler', 2, '2025-01-01', None, 'o', 'e') for r in REG.rules)
        reg2 = AuthorityRegister('SYN-REG-2', rules, 'synthetic.proposer', REG.approvals)
        self.conflicted()
        self.rc(reg2)
        review.decide(self.rec, 'ap_invoice/INV-1', 'correct', 'n', 700)
        self.rc(reg2)
        self.assertEqual(self.outcome('ap_invoice', 'INV-1'), 'quarantined')
        with self.assertRaises(AuthorityError):
            review.decide(self.rec, 'ap_invoice/INV-1', 'correct', 'again', 700)              # the same person cannot approve twice
        with self.assertRaises(AuthorityError):
            review.decide(self.rec2, 'ap_invoice/INV-1', 'correct', 'n', 650)                 # approvers must agree
        review.decide(self.rec2, 'ap_invoice/INV-1', 'correct', 'agree', 700)
        self.rc(reg2)
        self.assertEqual(self.outcome('ap_invoice', 'INV-1'), 'accepted_with_warnings')

    def test_reject_removes_the_record_from_every_view_but_keeps_it_visible(self):
        self.conflicted()
        review.decide(self.rec, 'ap_invoice/INV-1', 'reject', 'bad export, ignore both')
        self.rc()
        self.assertEqual(self.outcome('ap_invoice', 'INV-1'), 'rejected')
        auth, prov = views.invoice_cost_view(self.s, AS_OF)
        self.assertEqual(auth.cents, 0)
        self.assertIn('ap_invoice/INV-1', [r['ref'] for r in views.review_table(self.s)])

    def test_a_decision_stops_applying_when_the_facts_change(self):
        self.conflicted()
        review.decide(self.rec, 'ap_invoice/INV-1', 'correct', 'n', 700)
        self.rc()
        self.assertEqual(self.outcome('ap_invoice', 'INV-1'), 'accepted_with_warnings')
        self.invs(inv('INV-1', ex='9000'))                                              # a new conflicting delivery
        self.rc()
        self.assertEqual(self.outcome('ap_invoice', 'INV-1'), 'quarantined')
        self.assertEqual(R.ReviewQueue(self.s).open_items()[0].payload['status'], 'held')

    def test_no_reviewer_can_waive_a_missing_authority_register(self):
        self.invs(inv('INV-1'))
        self.rc(None)
        review.decide(self.rec, 'ap_invoice/INV-1', 'accept', 'just approve it')
        self.rc(None)
        st = self.state('ap_invoice', 'INV-1')
        self.assertEqual(st['effective_outcome'], 'pending_reconciliation')
        self.assertTrue(any(f['code'].startswith('PROMOTION_CANNOT_CLEAR') for f in st['findings']))
        self.assertEqual(views.invoice_cost_view(self.s, AS_OF)[0].cents, 0)

    def test_a_missing_material_value_cannot_be_accepted_only_supplied_by_a_person_with_a_note(self):
        ex = tpl('TPL-EX-ACCOUNTING-DOLLARS')                       # this layout has no ex-GST column at all: the invoice amount the rules need does not exist
        P.ingest_file(self.s, self.w.clock, ex, 'Ref,Supplier,Job,Date,Total (inc GST)\nEX-1,Example Supplier A,J1,05/03/2026,"1,100.00"\n'.encode(), 'accounting', 'ex.csv', D.DEMO_POLICY)
        self.rc()
        self.assertEqual(self.codes('ap_invoice', 'EX-1'), ['AUTHORITATIVE_VALUE_UNKNOWN:no_data'])
        self.assertIsNone(self.state('ap_invoice', 'EX-1')['amount_cents'])
        review.decide(self.rec, 'ap_invoice/EX-1', 'accept', 'approve anyway')
        self.rc()
        self.assertEqual(self.outcome('ap_invoice', 'EX-1'), 'pending_reconciliation')
        self.assertEqual(views.invoice_cost_view(self.s, AS_OF)[0].cents, 0)

    def test_dispositions_are_idempotent_after_the_final_decision(self):
        self.conflicted()
        a = review.decide(self.rec, 'ap_invoice/INV-1', 'correct', 'n', 700)
        b = review.decide(self.rec, 'ap_invoice/INV-1', 'correct', 'n', 700)
        self.assertEqual(a.revision, b.revision)

    def test_retain_keeps_the_item_open(self):
        self.conflicted()
        review.decide(self.rec, 'ap_invoice/INV-1', 'retain', 'investigating')
        self.rc()
        self.assertEqual(self.outcome('ap_invoice', 'INV-1'), 'quarantined')
        self.assertEqual(len(R.ReviewQueue(self.s).open_items()), 1)


class TestIdempotenceAndOrder(Base):
    def test_reconcile_twice_changes_nothing(self):
        self.invs(inv('INV-1'), inv('INV-2', sin='SI-2', supplier='Metro Steel'))
        self.rc()
        n1 = {r.key: r.revision for r in self.s.query('recon_state')}
        q1 = {r.key: r.revision for r in self.s.query('quarantine')}
        self.rc()
        self.assertEqual(n1, {r.key: r.revision for r in self.s.query('recon_state')})
        self.assertEqual(q1, {r.key: r.revision for r in self.s.query('quarantine')})

    def test_final_state_does_not_depend_on_arrival_order(self):
        from .helpers_ingest import bz
        names = [('TPL-BZ-SUPPLIERS', 'zero_one/reference/suppliers.csv', 'master'), ('TPL-BZ-AP-INVOICES', 'zero_one/SRC-01_accounting/ap_invoices.csv', 'accounting'),
                 ('TPL-BZ-CREDIT-NOTES', 'zero_one/SRC-01_accounting/credit_notes.csv', 'accounting'), ('TPL-BZ-PURCHASE-ORDERS', 'zero_one/SRC-03_procurement/purchase_orders.csv', 'procurement'),
                 ('TPL-BZ-PM-INVOICES', 'zero_one/conflicting_sources/pm_system_invoices.csv', 'pm_system'), ('TPL-BZ-PAYMENTS', 'zero_one/SRC-01_accounting/payments.csv', 'accounting')]
        finals = []
        for seed in range(6):
            rnd = random.Random(seed)
            w = World(); s = w.who('i'); order = list(names); rnd.shuffle(order)
            for tid, rel, src in order:
                lines = bz(rel).decode().split('\n')
                head, body = lines[0], [x for x in lines[1:] if x]
                rnd.shuffle(body)
                half = len(body) // 2 if seed % 2 else len(body)        # sometimes deliver in two files
                for j, part in enumerate((body[:half], body[half:])):
                    if part:
                        P.ingest_file(s, w.clock, tpl(tid), ('\n'.join([head] + part) + '\n').encode(), src, f'{tid}{j}.csv', D.DEMO_POLICY)
                if rnd.random() < 0.5:
                    R.reconcile(s, REG, AS_OF)                         # reconcile at arbitrary points as well
            R.reconcile(s, REG, AS_OF)
            snap = {r.key: (r.payload['effective_outcome'], r.payload['lifecycle'], r.payload['duplicate_of'], r.payload['amount_cents'], tuple(sorted(f['code'] for f in r.payload['findings'])),
                            tuple(r.payload['warnings'])) for r in s.query('recon_state')}
            finals.append(snap)
        for f in finals[1:]:
            self.assertEqual(f, finals[0])
        self.assertEqual(len(finals[0]), 482)


class TestViews(Base):
    def test_provisional_and_authoritative_cannot_be_added(self):
        self.invs(inv('INV-1', ex='100'), inv('INV-2', sin='S2', ex='-5'))
        self.rc()
        auth, prov = views.invoice_cost_view(self.s, AS_OF)
        with self.assertRaises(TypeError):
            auth + prov
        self.assertEqual((auth.cents, prov.cents, prov.label), (100, -5, 'PROVISIONAL - not authoritative'))

    def test_gst_never_counts_a_blank_as_zero(self):
        self.invs(inv('INV-1', gst='100'), inv('INV-2', sin='S2', gst=''))
        self.rc()
        g = views.gst_view(self.s)
        self.assertEqual((g.cents, g.complete, [x[0] for x in g.left_out]), (100, False, ['INV-2']))

    def test_project_filter(self):
        self.invs(inv('INV-1', ex='100'), inv('INV-2', sin='S2', project='PRJ-002', ex='50'))
        self.rc()
        self.assertEqual((views.invoice_cost_view(self.s, AS_OF, 'PRJ-001')[0].cents, views.invoice_cost_view(self.s, AS_OF, 'PRJ-002')[0].cents), (100, 50))

    def test_review_table_shows_everything(self):
        self.invs(inv('INV-1'), inv('INV-2', sin='S2', ex='-1'))
        self.rc()
        refs = {r['ref']: r['status'] for r in views.review_table(self.s)}
        self.assertEqual(refs['ap_invoice/INV-2'], 'pending_reconciliation')


if __name__ == '__main__':
    unittest.main()
