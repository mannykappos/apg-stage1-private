"""Adversarial tests on the ingestion pipeline: each tries to make the pipeline do something it must never do."""
import json, unittest
from . import _path                                         # noqa: F401
from .helpers_ingest import INV_H, World, bz, csvb, inv, inv_file, load_suppliers, tpl
from apg import canon, tenancy
from apg.ingest import demo_setup as D, documents as DOC, freshness as F, pipeline as P, reconcile as R, review, views
from apg.ports import TenantMismatch
from apg.source_authority import AuthorityError, resolve_field

INVT = tpl('TPL-BZ-AP-INVOICES')
REG = D.demo_register()
AS_OF = '2026-09-30'


def load_bz(w, s, tenant, only=None):
    out = {}
    for t, data, src, name, rev in D.files_for(_path.HERE_ROOT, tenant):
        if only and t['template_id'] not in only:
            continue
        out[name] = P.ingest_file(s, w.clock, t, data, src, name, D.DEMO_POLICY, rev)
    return out


class TestTenantSpoofingInFiles(unittest.TestCase):
    def setUp(self):
        self.w = World(); self.s2 = self.w.who('b', 'zero_two', 'bob')

    def attack(self, header_extra, cells_extra, rows=1):
        data = csvb(INV_H + header_extra, [inv(f'INV-{i}') + cells_extra for i in range(1, rows + 1)])
        with self.assertRaises(TenantMismatch):
            P.ingest_file(self.s2, self.w.clock, INVT, data, 'accounting', 'x.csv', D.DEMO_POLICY)
        self.assertEqual(self.s2.query('ap_invoice'), ())
        self.assertEqual(self.s2.query('ingest_receipt'), ())

    def test_every_spelling_of_a_tenant_column_is_a_claim(self):
        for name in ('tenant_id', 'Tenant ID', 'TENANT-ID', 'tenantId', 'tenant.id', 'ten​ant_id', 'ｔenant_id', 'org_id', 'Organisation ID', 'organization', 'customer_id', 'company_id', 'client_id', 'orgUUID'):
            with self.subTest(name=name):
                self.attack([name], ['zero_one'])

    def test_blank_and_non_string_looking_values_are_not_a_matching_claim(self):
        for v in ('', 'zero_two ', 'ZERO_TWO', 'zero_two​', '0', 'null'):
            with self.subTest(value=v):
                self.attack(['tenant_id'], [v])

    def test_a_claim_hidden_as_json_inside_any_cell(self):
        for cell in ('{"tenant_id": "zero_one"}', '[{"x": {"Tenant": "zero_one"}}]', ' {"orgId":"zero_one"} ', '{"a":"{\\"tenant\\": \\"zero_one\\"}"}'):
            with self.subTest(cell=cell):
                data = csvb(INV_H, [inv(sin=cell)])
                with self.assertRaises(TenantMismatch):
                    P.ingest_file(self.s2, self.w.clock, INVT, data, 'accounting', 'x.csv', D.DEMO_POLICY)

    def test_a_nesting_bomb_fails_closed(self):
        bomb = '[' * 5000 + ']' * 5000
        with self.assertRaises(TenantMismatch):
            P.ingest_file(self.s2, self.w.clock, INVT, csvb(INV_H, [inv(sin=bomb)]), 'accounting', 'x.csv', D.DEMO_POLICY)
        self.assertEqual(self.s2.query('ap_invoice'), ())

    def test_one_bad_row_among_many_refuses_the_whole_file(self):
        rows = [inv(f'INV-{i}') + ['zero_two'] for i in range(1, 40)] + [inv('INV-99') + ['zero_one']]
        with self.assertRaises(TenantMismatch):
            P.ingest_file(self.s2, self.w.clock, INVT, csvb(INV_H + ['tenant_id'], rows), 'accounting', 'x.csv', D.DEMO_POLICY)
        self.assertEqual(self.s2.query('ap_invoice'), ())

    def test_a_foreign_claim_inside_an_otherwise_rejected_row_still_refuses_the_file(self):
        rows = [inv('INV-1', date='not-a-date') + ['zero_one']]
        with self.assertRaises(TenantMismatch):
            P.ingest_file(self.s2, self.w.clock, INVT, csvb(INV_H + ['tenant_id'], rows), 'accounting', 'x.csv', D.DEMO_POLICY)
        self.assertEqual(self.s2.query('ingest_reject'), ())

    def test_the_refusal_is_on_the_attackers_audit_log_not_the_victims(self):
        s1 = self.w.who('a', 'zero_one', 'ann')
        P.ingest_file(s1, self.w.clock, INVT, inv_file(inv()), 'accounting', 'f.csv', D.DEMO_POLICY)
        with self.assertRaises(TenantMismatch):
            P.ingest_file(self.s2, self.w.clock, INVT, csvb(INV_H + ['tenant_id'], [inv('INV-7') + ['zero_one']]), 'accounting', 'x.csv', D.DEMO_POLICY)
        self.assertTrue(any(e.event_type == 'tenant_claim.refused' for e in self.w.audit.read(self.s2.ctx)))
        self.assertEqual({e.event_type for e in self.w.audit.read(s1.ctx)}, {'ingest.file_ingested'})
        self.assertTrue(self.w.audit.verify(s1.ctx).ok and self.w.audit.verify(self.s2.ctx).ok)

    def test_a_matching_claim_does_not_survive_into_the_stored_record(self):
        s1 = self.w.who('a', 'zero_one', 'ann')
        P.ingest_file(s1, self.w.clock, INVT, csvb(INV_H + ['Tenant ID', 'note'], [inv() + ['zero_one', '{"tenant_id":"zero_one","k":1}']]), 'accounting', 'f.csv', D.DEMO_POLICY)
        rec = s1.get('ap_invoice', 'INV-1')
        self.assertEqual(tenancy.find_claims(rec.payload), [])
        self.assertEqual(json.loads(rec.payload['raw']['note']), {'k': 1})


class TestTwoTenantsOneStore(unittest.TestCase):
    def test_identical_ids_never_meet_and_each_tenant_gets_its_own_answers(self):
        w = World(); s1 = w.who('a', 'zero_one', 'ann'); s2 = w.who('b', 'zero_two', 'bob')
        r1, r2 = load_bz(w, s1, 'zero_one'), load_bz(w, s2, 'zero_two')
        self.assertGreater(len(r1), 5)
        a1, a2 = R.reconcile(s1, REG, AS_OF), R.reconcile(s2, REG, AS_OF)
        self.assertEqual((a1['records'], a2['records']) > (0, 0), True)
        self.assertEqual(r2['ap_invoices.csv']['counts']['conflict'], 1)                      # zero_two repeats INV-0001 with different content
        self.assertEqual(s1.get('recon_state', 'ap_invoice/INV-0001').payload['effective_outcome'], 'accepted')
        self.assertEqual(s2.get('recon_state', 'ap_invoice/INV-0001').payload['effective_outcome'], 'quarantined')
        self.assertIsNone(s2.get('ap_invoice', 'INV-0187'))
        t1, t2 = views.invoice_cost_view(s1, AS_OF)[0], views.invoice_cost_view(s2, AS_OF)[0]
        self.assertNotEqual(t1.cents, t2.cents)
        keys1 = {r.key for r in s1.query('recon_state')}
        self.assertNotEqual(keys1, {r.key for r in s2.query('recon_state')})
        for kind in ('quarantine', 'ingest_receipt', 'recon_state', 'ap_invoice'):
            self.assertTrue(all(r.tenant_id == 'zero_one' for r in s1.query(kind)))
            self.assertTrue(all(r.tenant_id == 'zero_two' for r in s2.query(kind)))

    def test_the_same_bytes_in_another_tenant_are_not_a_replay(self):
        w = World(); s1 = w.who('a', 'zero_one'); s2 = w.who('b', 'zero_two', 'bob')
        data = inv_file(inv())
        a = P.ingest_file(s1, w.clock, INVT, data, 'accounting', 'f.csv', D.DEMO_POLICY)
        b = P.ingest_file(s2, w.clock, INVT, data, 'accounting', 'f.csv', D.DEMO_POLICY)
        self.assertEqual((a['replay'], b['replay'], b['counts']['new']), (False, False, 1))

    def test_a_reconcile_in_one_tenant_touches_nothing_in_another(self):
        w = World(); s1 = w.who('a', 'zero_one'); s2 = w.who('b', 'zero_two', 'bob')
        load_bz(w, s1, 'zero_one')
        before = [(e.seq, e.hash) for e in w.audit.read(s1.ctx)]
        load_bz(w, s2, 'zero_two'); R.reconcile(s2, REG, AS_OF)
        self.assertEqual(before, [(e.seq, e.hash) for e in w.audit.read(s1.ctx)])
        self.assertEqual(s1.query('recon_state'), ())                                           # nothing was reconciled for tenant one by tenant two's run


class TestMissingEvidenceNeverBecomesCertainty(unittest.TestCase):
    def setUp(self):
        self.w = World(); self.s = self.w.who('a'); load_bz(self.w, self.s, 'zero_one'); R.reconcile(self.s, REG, AS_OF)

    def state(self, k, key):
        return self.s.get('recon_state', f'{k}/{key}').payload

    def test_missing_gst_is_listed_never_counted_as_zero(self):
        g = views.gst_view(self.s)
        self.assertEqual((g.complete, [x[0] for x in g.left_out]), (False, ['INV-0186']))
        self.assertNotIn('gst_cents', self.s.get('ap_invoice', 'INV-0186').payload['fields'])
        self.assertEqual(self.s.get('ap_invoice', 'INV-0186').payload['unknown'], {'gst_cents': 'no_data'})

    def test_missing_cost_code_holds_the_po_and_defaults_nothing(self):
        p = self.s.get('purchase_order', 'PO-0099').payload
        self.assertNotIn('cost_code_ref', p['fields'])
        self.assertEqual(self.state('purchase_order', 'PO-0099')['effective_outcome'], 'pending_reconciliation')

    def test_no_stored_value_is_a_float_or_an_empty_default(self):
        def walk(o):
            if isinstance(o, float):
                raise AssertionError('float')
            if isinstance(o, dict):
                [walk(v) for v in o.values()]
            if isinstance(o, list):
                [walk(v) for v in o]
        for kind in ('ap_invoice', 'purchase_order', 'supplier_quote', 'fx_rate', 'payment'):
            for r in self.s.query(kind):
                walk(r.payload)
                self.assertNotIn('', [v for v in r.payload['fields'].values() if isinstance(v, str)] or ['x'])
        self.assertEqual(self.s.get('supplier_quote', 'Q-0005').payload['fields']['fx_rate_used'], '0.6612')

    def test_authoritative_totals_never_contain_an_unknown_or_held_record(self):
        auth, _ = views.invoice_cost_view(self.s, AS_OF)
        held = {k.split('/')[1] for k, v in ((r.key, r.payload) for r in self.s.query('recon_state') if r.key.startswith('ap_invoice/'))
                if v['effective_outcome'] not in ('accepted', 'accepted_with_warnings') or v['lifecycle'] != 'current'}
        self.assertEqual(held, {'INV-0121', 'INV-0183', 'INV-0187'})
        self.assertTrue(held.isdisjoint(auth.included))
        self.assertFalse(auth.complete)

    def test_expired_quote_and_stale_fx_are_flagged_and_downgrade_the_decision(self):
        v = F.quote_validity(self.s, AS_OF)
        self.assertEqual((v['Q-0004'], v['Q-0001']), ('expired', 'valid'))
        q5 = self.s.get('supplier_quote', 'Q-0005').payload['fields']
        pol = F.FreshnessPolicy({'illustrative_international_quote': 30})                     # ILLUSTRATIVE
        a = F.assess(pol, 'illustrative_international_quote', [('Q-0005 fx rate', q5['fx_rate_date']), ('latest AUD/USD', F.latest_dates(self.s, 'fx_rate', 'fx_date', 'currency_pair')['AUD/USD'])], AS_OF)
        self.assertEqual((a['overall'], [i['state'] for i in a['inputs']]), (F.QUALIFIED, ['stale', 'fresh']))

    def test_market_series_that_ends_months_ago_is_stale_for_a_buy_timing_decision(self):
        ends = F.latest_dates(self.s, 'market_observation', 'obs_date', 'material_ref')
        self.assertEqual(ends['MAT-CU'], '2026-04-15')
        a = F.assess(F.FreshnessPolicy({'illustrative_buy_timing': 45}), 'illustrative_buy_timing', sorted(ends.items()), AS_OF)
        self.assertEqual(a['overall'], F.QUALIFIED)
        self.assertEqual({i['label'] for i in a['inputs'] if i['state'] == 'stale'}, {'MAT-CU'})

    def test_unverified_document_values_are_not_authoritative(self):
        doc = open(_path.HERE_ROOT + '/builder_zero/zero_one/SRC-11_documents/quote_ambiguous_SUP-004.txt', 'rb').read()
        DOC.register_extraction(self.s, self.w.clock, 'DOC-002', doc, DOC.standin_extract_quote(doc.decode()))
        from .test_ingest_support import DOCREG
        for n in ('quantity', 'unit_rate_cents'):
            r = resolve_field(DOCREG, 'DOC-002', 'quote_document', n, [DOC.observation(self.s, 'DOC-002', n)], AS_OF)
            self.assertFalse(r.authoritative)

    def test_a_credit_that_is_not_trusted_never_reduces_cost_silently(self):
        w = World(); s = w.who('a'); load_bz(w, s, 'zero_one', only={'TPL-BZ-SUPPLIERS', 'TPL-BZ-AP-INVOICES', 'TPL-BZ-CREDIT-NOTES'})
        R.reconcile(s, D.demo_register(version='SYN-REG-X'), AS_OF)
        reg = __import__('apg.source_authority', fromlist=['x']).AuthorityRegister('R', tuple(r for r in REG.rules if r.entity_kind != 'credit_note'), 'p', REG.approvals)
        R.reconcile(s, reg, AS_OF)                                                            # the credit note has no authority rule now
        auth, _ = views.invoice_cost_view(s, AS_OF)
        self.assertIn('INV-0184', [x[0] for x in auth.excluded])
        self.assertNotIn('INV-0184', auth.included)


class TestConflictingSourcesNeverInfluenceAuthoritativeFigures(unittest.TestCase):
    def setUp(self):
        self.w = World(); self.s = self.w.who('a', ttl=10**9); self.rec = self.w.who('r', user='rita', roles=('reconciler',), ttl=10**9); load_bz(self.w, self.s, 'zero_one'); R.reconcile(self.s, REG, AS_OF)

    def st(self, k):
        return self.s.get('recon_state', k).payload

    def test_inv_0121_is_in_no_authoritative_figure(self):
        auth, prov = views.invoice_cost_view(self.s, AS_OF)
        self.assertNotIn('INV-0121', auth.included)
        self.assertIn('INV-0121', [x[0] for x in auth.excluded])
        self.assertIn('INV-0121', [x[0] for x in prov.unverified])
        self.assertNotIn('INV-0121', [x[0] for x in views.gst_view(self.s).included] + [x[0] for x in views.gst_view(self.s).left_out])
        self.assertEqual(R.ReviewQueue(self.s).open_items()[0].key.split('/')[0] in ('ap_invoice', 'purchase_order'), True)
        with self.assertRaises(TypeError):
            auth + prov

    def test_re_delivering_the_accounting_file_or_a_pm_copy_of_the_same_value_changes_nothing(self):
        before = views.invoice_cost_view(self.s, AS_OF)[0]
        for t, data, src, name, rev in D.files_for(_path.HERE_ROOT, 'zero_one'):
            if t['template_id'] in ('TPL-BZ-AP-INVOICES', 'TPL-BZ-PM-INVOICES'):
                P.ingest_file(self.s, self.w.clock, t, data + b'\n', src, 'again-' + name, D.DEMO_POLICY)
        R.reconcile(self.s, REG, AS_OF)
        after = views.invoice_cost_view(self.s, AS_OF)[0]
        self.assertEqual((before.cents, before.included, before.excluded), (after.cents, after.included, after.excluded))

    def test_the_secondary_cannot_make_the_disagreement_vanish_by_changing_its_own_story(self):
        pm = tpl('TPL-BZ-PM-INVOICES')
        agree = csvb(['invoice_ref', 'supplier_id', 'project_id', 'ex_gst_cents', 'source'], [['INV-0121', 'SUP-006', 'PRJ-003', '7280125', 'pm-system-export']])
        P.ingest_file(self.s, self.w.clock, pm, agree, 'pm_system', 'pm2.csv', D.DEMO_POLICY)             # now the PM system has two different versions
        R.reconcile(self.s, REG, AS_OF)
        self.assertEqual(self.st('ap_invoice/INV-0121')['effective_outcome'], 'pending_reconciliation')
        self.assertTrue(any(f['code'].startswith('SECONDARY_IN_CONFLICT') for f in self.st('ap_invoice/INV-0121')['findings']))
        self.assertNotIn('INV-0121', views.invoice_cost_view(self.s, AS_OF)[0].included)

    def test_a_secondary_cannot_win_by_having_a_higher_revision_or_a_later_time(self):
        w = World(); s = w.who('a', ttl=10**9); load_bz(w, s, 'zero_one', only={'TPL-BZ-SUPPLIERS', 'TPL-BZ-AP-INVOICES'})
        w.clock.advance(86400 * 30)
        pm = tpl('TPL-BZ-PM-INVOICES')
        P.ingest_file(s, w.clock, pm, csvb(['invoice_ref', 'supplier_id', 'project_id', 'ex_gst_cents', 'source'], [['INV-0050', 'SUP-001', 'PRJ-001', '1', 'later']]), 'pm_system', 'pm.csv', D.DEMO_POLICY)
        R.reconcile(s, REG, AS_OF)
        self.assertNotEqual(s.get('recon_state', 'ap_invoice/INV-0050').payload['effective_outcome'], 'accepted')
        self.assertNotEqual(s.get('recon_state', 'ap_invoice/INV-0050').payload['amount_cents'], 1)

    def test_a_later_accounting_delivery_with_a_different_amount_is_a_conflict_not_a_correction(self):
        t = tpl('TPL-BZ-AP-INVOICES')
        rows = [l for l in bz('zero_one/SRC-01_accounting/ap_invoices.csv').decode().split('\n') if l.startswith('INV-0002,')]
        edited = rows[0].replace(rows[0].split(',')[7], '1')
        self.w.clock.advance(86400 * 90)
        P.ingest_file(self.s, self.w.clock, t, (bz('zero_one/SRC-01_accounting/ap_invoices.csv').decode().split('\n')[0] + '\n' + edited + '\n').encode(), 'accounting', 'late.csv', D.DEMO_POLICY)
        R.reconcile(self.s, REG, AS_OF)
        self.assertEqual(self.st('ap_invoice/INV-0002')['effective_outcome'], 'quarantined')
        self.assertNotIn('INV-0002', views.invoice_cost_view(self.s, AS_OF)[0].included)

    def test_a_reviewer_cannot_promote_a_quarantined_item_without_the_resolver_role_and_a_note(self):
        outsider = self.w.who('o', user='olly', roles=('finance_viewer',))
        with self.assertRaises(AuthorityError):
            review.decide(outsider, 'ap_invoice/INV-0121', 'correct', 'n', 7280125)
        with self.assertRaises(AuthorityError):
            review.decide(self.rec, 'ap_invoice/INV-0121', 'correct', '', 7280125)
        R.reconcile(self.s, REG, AS_OF)
        self.assertEqual(self.st('ap_invoice/INV-0121')['effective_outcome'], 'quarantined')
        review.decide(self.rec, 'ap_invoice/INV-0121', 'correct', 'accounting posted amount confirmed against the bank file', 7280125)
        R.reconcile(self.s, REG, AS_OF)
        self.assertIn('INV-0121', views.invoice_cost_view(self.s, AS_OF)[0].included)
        self.assertEqual(len(self.s.history('ap_invoice', 'INV-0121')), 1)                         # the original evidence is untouched

    def test_replaying_the_whole_history_in_a_fresh_store_gives_the_same_answers(self):
        w2 = World(); s2 = w2.who('a'); load_bz(w2, s2, 'zero_one'); R.reconcile(s2, REG, AS_OF)
        a = {r.key: r.payload for r in self.s.query('recon_state')}
        b = {r.key: r.payload for r in s2.query('recon_state')}
        self.assertEqual(a, b)

    def test_nothing_in_the_audit_chain_was_lost_and_it_verifies(self):
        self.assertTrue(self.w.audit.verify(self.s.ctx).ok)
        types = {e.event_type for e in self.w.audit.read(self.s.ctx)}
        self.assertTrue({'ingest.file_ingested', 'quarantine.hold', 'reconcile.run'} <= types)


class TestHostileFilesAtBuilderZeroScale(unittest.TestCase):
    def test_a_corrupted_copy_of_a_real_file_is_refused_or_rejected_row_by_row_not_half_applied(self):
        w = World(); s = w.who('a'); load_suppliers(w, s)
        raw = bz('zero_one/SRC-01_accounting/ap_invoices.csv')
        lines = raw.decode().split('\n')
        lines[10] = lines[10].replace('2025', '20x5', 1)          # one bad date
        lines[20] = lines[20] + ',surplus'                         # one ragged row
        lines[30] = '​' + lines[30]                           # one hidden character in an identifier
        r = P.ingest_file(s, w.clock, INVT, '\n'.join(lines).encode(), 'accounting', 'bad.csv', D.DEMO_POLICY)
        self.assertEqual((r['counts']['rows'], r['counts']['rejected'], r['counts']['new']), (187, 3, 184))
        self.assertEqual(len(s.query('ap_invoice')), 184)
        self.assertEqual(len(s.query('ingest_reject')), 3)

    def test_the_same_corrupted_file_twice_is_one_effect(self):
        w = World(); s = w.who('a')
        data = bz('zero_one/SRC-01_accounting/ap_invoices.csv').replace(b'2025-05-13', b'2025-13-05', 1)
        a = P.ingest_file(s, w.clock, INVT, data, 'accounting', 'x.csv', D.DEMO_POLICY); b = P.ingest_file(s, w.clock, INVT, data, 'accounting', 'y.csv', D.DEMO_POLICY)
        self.assertEqual((a['replay'], b['replay'], len(s.query('ingest_reject'))), (False, True, 1))


if __name__ == '__main__':
    unittest.main()
