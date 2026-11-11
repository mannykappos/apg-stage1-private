import unittest
from . import _path                                         # noqa: F401
from .helpers_ingest import INV_H, World, csvb, inv, inv_file, load_suppliers, tpl
from apg import tenancy
from apg.ingest import demo_setup as D, documents as DOC, freshness as F, jobs, pipeline as P, reconcile as R
from apg.ports import ConflictError, TenantMismatch
from apg.source_authority import Approval, AuthorityError, AuthorityRegister, AuthorityRule, resolve_field
from apg.values import Known, Unknown
from ._path import HERE_ROOT
import os

INVT = tpl('TPL-BZ-AP-INVOICES')
DOCREG = AuthorityRegister('DOC-REG', tuple(AuthorityRule('quote_document', f, 'document_extraction', (), 'source_owned', 'quarantine', 'reconciler', 1, '2025-01-01', None, 'o', 'SYNTHETIC')
                                            for f in ('quantity', 'unit_rate_cents')), 'p', (Approval('o', 'authority_owner', 'human', '2026-09-30'),))


def doc(name):
    return open(os.path.join(HERE_ROOT, 'builder_zero', 'zero_one', 'SRC-11_documents', name), 'rb').read()


class TestFreshness(unittest.TestCase):
    POL = F.FreshnessPolicy({'market_buy_timing': 30, 'historical_cost': 400})

    def test_assess_table(self):
        A = lambda inputs, use='market_buy_timing': F.assess(self.POL, use, inputs, '2026-09-30')
        self.assertEqual(A([('a', '2026-09-20')])['overall'], F.ELIGIBLE)
        self.assertEqual(A([('a', '2026-09-20'), ('b', '2026-04-15')])['overall'], F.QUALIFIED)
        self.assertEqual(A([('a', '2026-09-20'), ('b', None)])['overall'], F.CANNOT_ASSESS)
        self.assertEqual(A([])['overall'], F.CANNOT_ASSESS)
        self.assertEqual(A([('a', '2026-09-20')], 'unlisted_use')['overall'], F.CANNOT_ASSESS)
        self.assertEqual(A([('a', '2026-09-20')], 'unlisted_use')['inputs'][0]['state'], F.UNCONFIGURED)
        self.assertEqual(A([('a', '2026-10-05')])['overall'], F.CANNOT_ASSESS)             # dated after the as-of date
        self.assertEqual(A([('a', '2026-08-31')])['inputs'][0]['state'], F.FRESH)         # exactly 30 days is within the limit
        self.assertEqual(A([('a', '2026-08-30')])['inputs'][0]['state'], F.STALE)

    def test_same_data_different_decisions(self):
        old = [('cost', '2026-01-01')]
        self.assertEqual(F.assess(self.POL, 'market_buy_timing', old, '2026-09-30')['overall'], F.QUALIFIED)
        self.assertEqual(F.assess(self.POL, 'historical_cost', old, '2026-09-30')['overall'], F.ELIGIBLE)

    def test_no_default_threshold_exists(self):
        self.assertEqual(F.FreshnessPolicy().max_age_days, {})
        self.assertEqual(F.assess(F.FreshnessPolicy(), 'anything', [('x', '2026-09-30')], '2026-09-30')['overall'], F.CANNOT_ASSESS)

    def test_currency_conversion_is_exact_and_explains_itself(self):
        c = F.convert_minor(6900, '0.6612', 'USD', 'AUD', 'AUD/USD', '2026-05-02', 'fx_rates.csv')
        self.assertEqual((c['converted_minor'], c['rate'], c['rate_date'], c['source_amount_minor']), (10436, '0.6612', '2026-05-02', 6900))
        self.assertEqual(F.convert_minor(10000, '0.5', 'AUD', 'USD', 'AUD/USD', 'd', 's')['converted_minor'], 5000)
        self.assertEqual(F.convert_minor(1, '2', 'USD', 'AUD', 'AUD/USD', 'd', 's')['converted_minor'], 1)          # 0.5 rounds half up
        self.assertEqual(F.convert_minor(-1, '2', 'USD', 'AUD', 'AUD/USD', 'd', 's')['converted_minor'], -1)         # symmetric
        for bad in (('0', 'USD', 'AUD'), ('-1', 'USD', 'AUD'), ('0.66', 'EUR', 'AUD'), ('abc', 'USD', 'AUD')):
            with self.assertRaises((ValueError, ZeroDivisionError)):
                F.convert_minor(100, bad[0], bad[1], bad[2], 'AUD/USD', 'd', 's')
        with self.assertRaises(ValueError):
            F.convert_minor(1.5, '0.66', 'USD', 'AUD', 'AUD/USD', 'd', 's')

    def test_quotes_validity_and_data_recency_from_stored_records(self):
        w = World(); s = w.who('a'); load_suppliers(w, s)
        q = tpl('TPL-BZ-QUOTES')
        H = ['quote_id', 'supplier_id', 'material_id', 'specification', 'issue_date', 'valid_until', 'unit_rate_cents', 'currency', 'fx_rate_used', 'fx_rate_date', 'freight_cents_per_unit', 'incoterm_delivery_basis', 'lead_time_days', 'price_kind']
        rows = [['Q-1', 'SUP-001', 'M', 's', '2026-03-01', '2026-06-30', '100', 'AUD', '', '', '0', 'delivered', '', 'quote'], ['Q-2', 'SUP-001', 'M', 's', '2026-09-01', '2026-10-31', '100', 'AUD', '', '', '0', 'delivered', '', 'quote']]
        P.ingest_file(s, w.clock, q, csvb(H, rows), 'procurement', 'q.csv', D.DEMO_POLICY)
        self.assertEqual(F.quote_validity(s, '2026-09-30'), {'Q-1': 'expired', 'Q-2': 'valid'})
        self.assertEqual(F.quote_validity(s, '2026-10-31')['Q-2'], 'valid')
        self.assertEqual(F.quote_validity(s, '2026-11-01')['Q-2'], 'expired')
        fx = tpl('TPL-BZ-FX-RATES')
        P.ingest_file(s, w.clock, fx, csvb(['fx_date', 'pair', 'rate'], [['2026-05-01', 'AUD/USD', '0.65'], ['2026-09-30', 'AUD/USD', '0.66'], ['2026-12-01', 'AUD/USD', '0.70']]), 'market', 'fx.csv', D.DEMO_POLICY)
        R.reconcile(s, D.demo_register(), '2026-09-30')
        self.assertEqual(F.latest_dates(s, 'fx_rate', 'fx_date', 'currency_pair'), {'AUD/USD': '2026-09-30'})   # the future-dated rate (held) is not evidence of recency

    def test_source_status_and_quality_summary(self):
        w = World(); s = w.who('a'); load_suppliers(w, s)
        P.ingest_file(s, w.clock, INVT, inv_file(inv(), inv('INV-2', date='nope')), 'accounting', 'f.csv', D.DEMO_POLICY)
        R.reconcile(s, D.demo_register(), '2026-09-30')
        st = F.source_status(s, '2026-10-11', expected_sources=('accounting', 'procurement'))
        self.assertEqual((st['accounting']['last_receipt'], st['accounting']['lag_days'], st['accounting']['rejected_rows']), ('2026-10-01', 10, 1))
        self.assertEqual((st['procurement']['state'], st['procurement']['lag_days']), ('never_received', None))
        q = F.quality_summary(s)
        self.assertEqual(q['ap_invoice']['rejected_rows'], 1)
        self.assertEqual(q['ap_invoice']['accepted_with_warnings'], 1)


class TestDocuments(unittest.TestCase):
    def setUp(self):
        self.w = World(); self.s = self.w.who('imp'); self.v = self.w.who('ver', user='vera', roles=(DOC.VERIFIER_ROLE,))
        self.amb, self.clear = doc('quote_ambiguous_SUP-004.txt'), doc('quote_clear_SUP-006.txt')
        DOC.register_extraction(self.s, self.w.clock, 'DOC-002', self.amb, DOC.standin_extract_quote(self.amb.decode()))
        DOC.register_extraction(self.s, self.w.clock, 'DOC-001', self.clear, DOC.standin_extract_quote(self.clear.decode()))

    def res(self, doc_id, name):
        return resolve_field(DOCREG, doc_id, 'quote_document', name, [DOC.observation(self.s, doc_id, name)], '2026-09-30')

    def test_ambiguity_is_detected_and_candidates_are_offered_not_chosen(self):
        f = self.s.get('extracted_document', 'DOC-002').payload['fields']
        self.assertEqual((f['quantity']['candidates'], f['quantity']['ambiguous']), ([40], True))
        self.assertEqual((f['unit_rate_cents']['candidates'], f['unit_rate_cents']['ambiguous']), ([265, 265000], True))
        g = self.s.get('extracted_document', 'DOC-001').payload['fields']
        self.assertEqual((g['quantity']['candidates'], g['unit_rate_cents']['candidates'], g['unit_rate_cents']['ambiguous']), ([2000], [1740], False))

    def test_nothing_extracted_is_authoritative_until_a_person_verifies_it(self):
        for d, n in (('DOC-001', 'quantity'), ('DOC-001', 'unit_rate_cents'), ('DOC-002', 'quantity'), ('DOC-002', 'unit_rate_cents')):
            r = self.res(d, n)
            self.assertFalse(r.authoritative, (d, n))
            self.assertEqual(r.outcome, 'pending_reconciliation')
        self.assertEqual(self.res('DOC-001', 'quantity').reasons, ('AWAITING_HUMAN_VERIFICATION',))      # even a perfectly clear reading

    def test_verification_by_a_human_makes_it_usable_and_records_who_when_what(self):
        DOC.verify_field(self.v, self.w.clock, 'DOC-001', 'unit_rate_cents', 1740, 'page 1 line 5', 'matches the PDF')
        r = self.res('DOC-001', 'unit_rate_cents')
        self.assertTrue(r.authoritative)
        self.assertEqual(r.value.cents, 1740)
        v = self.s.get('extracted_document', 'DOC-001').payload['fields']['unit_rate_cents']['verification']
        self.assertEqual((v['by'], v['disposition'], v['evidence'], v['at']), ('vera', 'confirmed', 'page 1 line 5', '2026-10-01T09:00:00Z'))
        self.assertFalse(self.res('DOC-001', 'quantity').authoritative)                                  # other fields are still unverified

    def test_an_ambiguous_value_is_resolved_by_the_person_not_the_software(self):
        self.assertEqual(self.res('DOC-002', 'unit_rate_cents').outcome, 'pending_reconciliation')
        DOC.verify_field(self.v, self.w.clock, 'DOC-002', 'unit_rate_cents', 265000, 'supplier email says $2,650 per tonne', 'thousands separator')
        r = self.res('DOC-002', 'unit_rate_cents')
        self.assertEqual((r.authoritative, r.value.cents), (True, 265000))
        self.assertEqual(self.s.get('extracted_document', 'DOC-002').payload['fields']['unit_rate_cents']['verification']['disposition'], 'corrected')

    def test_who_may_verify(self):
        for who in (self.s, self.w.who('rec', user='rita', roles=('reconciler',)), self.w.who('ai', user='bot', roles=(DOC.VERIFIER_ROLE,), kind='ai'),
                    self.w.who('svc', user='svc', roles=(DOC.VERIFIER_ROLE,), kind='service')):
            with self.assertRaises(AuthorityError):
                DOC.verify_field(who, self.w.clock, 'DOC-001', 'quantity', 2000, 'e', 'n')
        self.assertFalse(self.res('DOC-001', 'quantity').authoritative)
        self.assertTrue(any(e.event_type == 'document.refused' for e in self.w.audit.read(self.s.ctx)))

    def test_verification_needs_evidence_a_note_and_a_whole_number(self):
        for args in ((2000, '', 'n'), (2000, 'e', ' '), (2000.0, 'e', 'n'), (True, 'e', 'n'), ('2000', 'e', 'n'), (None, 'e', 'n')):
            with self.assertRaises(AuthorityError):
                DOC.verify_field(self.v, self.w.clock, 'DOC-001', 'quantity', *args)
        with self.assertRaises(AuthorityError):
            DOC.verify_field(self.v, self.w.clock, 'DOC-001', 'nonsense', 1, 'e', 'n')
        with self.assertRaises(AuthorityError):
            DOC.verify_field(self.v, self.w.clock, 'DOC-404', 'quantity', 1, 'e', 'n')

    def test_a_text_field_takes_verified_text(self):
        DOC.verify_field(self.v, self.w.clock, 'DOC-002', 'valid_until', '2026-10-31', 'PDF header', 'day/month/year')
        self.assertEqual(DOC.verified_text(self.s, 'DOC-002', 'valid_until'), '2026-10-31')
        self.assertIsNone(DOC.verified_text(self.s, 'DOC-001', 'valid_until'))

    def test_the_same_document_id_cannot_hold_different_bytes_or_a_different_reading(self):
        with self.assertRaises(AuthorityError):
            DOC.register_extraction(self.s, self.w.clock, 'DOC-002', self.amb + b' ', DOC.standin_extract_quote(self.amb.decode()))
        other = DOC.standin_extract_quote(self.amb.decode().replace('4O', '41'))
        with self.assertRaises(AuthorityError):
            DOC.register_extraction(self.s, self.w.clock, 'DOC-002', self.amb, other)
        n = self.s.get('extracted_document', 'DOC-002').revision
        DOC.register_extraction(self.s, self.w.clock, 'DOC-002', self.amb, DOC.standin_extract_quote(self.amb.decode()))        # identical: no change
        self.assertEqual(self.s.get('extracted_document', 'DOC-002').revision, n)

    def test_another_tenant_cannot_see_or_verify_a_document(self):
        s2 = self.w.who('t2', 'zero_two', 'bob'); v2 = self.w.who('v2', 'zero_two', 'vic', (DOC.VERIFIER_ROLE,))
        self.assertIsNone(s2.get('extracted_document', 'DOC-001'))
        with self.assertRaises(AuthorityError):
            DOC.verify_field(v2, self.w.clock, 'DOC-001', 'quantity', 2000, 'e', 'n')
        self.assertEqual(DOC.observation(s2, 'DOC-001', 'quantity').value.reason, 'no_data')

    def test_stand_in_reads_numbers_conservatively(self):
        for text, want in (('4O', ([40], True)), ('40', ([40], False)), ('l0', ([10], True)), ('forty', ([], True)), ('4 0', ([], True))):
            f = DOC._qty(text)
            self.assertEqual((f['candidates'], f['ambiguous']), want, text)
        for text, want in (('$17.40', ([1740], False)), ('$2.650', ([265, 265000], True)), ('$2.655', ([265500], True)), ('$1,250.00', ([125000], False)), ('$5', ([500], False)), ('$1.2345', ([], True)), ('$x', ([], True))):
            f = DOC._rate(text)
            self.assertEqual((f['candidates'], f['ambiguous']), want, text)


class TestJobs(unittest.TestCase):
    def setUp(self):
        self.w = World(); self.sleeps = []
        self.effects = []
        self.provider = self.w.provider

    def runner(self, handler, **kw):
        return jobs.JobRunner(self.provider, self.w.store, self.w.audit, handler, sleep=self.sleeps.append, **kw)

    def job(self, jid='J1', tok='a', tenant='zero_one', payload=None, **extra):
        self.provider._contract_register_session(tok, tenant, 'ann', ('importer',), 'human', 360000)
        return dict({'job_id': jid, 'credentials': tok, 'payload': payload or {}}, **extra)

    def test_transient_failures_retry_with_backoff_then_succeed_once(self):
        calls = []
        def h(s, p):
            calls.append(1)
            if len(calls) < 3:
                raise jobs.TransientError('network blip')
            self.effects.append('done'); return {'ok': 1}
        r = self.runner(h, max_attempts=4, backoff_seconds=(1, 2, 4)).run(self.job())
        self.assertEqual((r['status'], r['attempts'], r['result']), ('succeeded', 3, {'ok': 1}))
        self.assertEqual((self.effects, self.sleeps), (['done'], [1, 2]))

    def test_retries_are_bounded_and_end_in_the_dead_letter_list(self):
        n = []
        def h(s, p):
            n.append(1); raise jobs.TransientError('down')
        r = self.runner(h, max_attempts=3).run(self.job())
        self.assertEqual((r['status'], len(n)), ('dead_letter', 3))
        s = self.w.who('chk')
        self.assertEqual(s.get('job', 'J1').payload['status'], 'dead_letter')
        self.assertEqual(len(s.get('job', 'J1').payload['errors']), 3)
        self.assertEqual(self.runner(h, max_attempts=3).run(self.job())['status'], 'dead_letter')       # submitting again does not run it again
        self.assertEqual(len(n), 3)

    def test_a_permanent_error_is_not_retried(self):
        n = []
        def h(s, p):
            n.append(1); raise ValueError('bad input')
        r = self.runner(h, max_attempts=5).run(self.job())
        self.assertEqual((r['status'], len(n), self.sleeps), ('dead_letter', 1, []))
        self.assertIn('ValueError', self.w.who('chk').get('job', 'J1').payload['errors'][-1])

    def test_a_succeeded_job_is_never_run_again(self):
        n = []
        def h(s, p):
            n.append(1); return {'v': len(n)}
        rn = self.runner(h)
        a = rn.run(self.job()); b = rn.run(self.job())
        self.assertEqual((len(n), a['replay'], b['replay'], b['result']), (1, False, True, {'v': 1}))

    def test_crash_after_the_write_does_not_double_the_effect(self):
        data = inv_file(inv('INV-1'), inv('INV-2'))
        state = {'n': 0}
        def h(s, p):
            state['n'] += 1
            P.ingest_file(s, self.w.clock, INVT, data, 'accounting', 'f.csv', D.DEMO_POLICY)
            if state['n'] == 1:
                raise jobs.TransientError('worker died after writing')
            return {'rows': 2}
        r = self.runner(h).run(self.job())
        self.assertEqual((r['status'], r['attempts']), ('succeeded', 2))
        s = self.w.who('chk')
        self.assertEqual((len(s.query('ap_invoice')), len(s.query('ingest_receipt')), s.get('ap_invoice', 'INV-1').revision), (2, 1, 1))

    def test_revoked_credentials_stop_the_job_without_running_the_handler(self):
        n = []
        def h(s, p):
            n.append(1)
            self.provider._contract_revoke('a'); raise jobs.TransientError('revoked while running')
        rn = self.runner(h, max_attempts=3)
        r = rn.run(self.job())
        self.assertEqual((r['status'], len(n), r['recorded']), ('dead_letter', 1, False))
        self.assertEqual(rn.unrecorded[0]['job_id'], 'J1')                    # the failure is not lost even though the tenant store would not accept a write
        self.assertEqual(rn.unrecorded[0]['why_unrecorded'], 'Unauthenticated')

    def test_unknown_credentials_are_refused_and_nothing_runs(self):
        n = []
        r = self.runner(lambda s, p: n.append(1)).run({'job_id': 'J9', 'credentials': 'nope', 'payload': {}})
        self.assertEqual((r['status'], r['reason'], n), ('refused', 'Unauthenticated', []))

    def test_the_tenant_comes_from_the_credentials_never_the_message(self):
        seen = []
        def h(s, p):
            seen.append(s.ctx.tenant_id); return None
        rn = self.runner(h)
        rn.run(self.job('J1', 'a', 'zero_one', {'tenant_id': 'zero_one'}))
        self.assertEqual(rn.run(self.job('J2', 'b', 'zero_two', {'tenant_id': 'zero_one'}))['status'], 'refused')
        self.assertEqual(rn.run(self.job('J3', 'b', 'zero_two', claimed_tenant='zero_one'))['reason'], 'TenantMismatch')
        self.assertEqual(seen, ['zero_one'])
        attacker = self.w.who('chk2', 'zero_two', 'bob')
        self.assertEqual(sum(e.event_type == 'tenant_claim.refused' for e in self.w.audit.read(attacker.ctx)), 2)       # on the attacker's own log
        self.assertIsNone(attacker.get('job', 'J2'))

    def test_job_ids_are_per_tenant(self):
        rn = self.runner(lambda s, p: {'t': s.ctx.tenant_id})
        a = rn.run(self.job('J1', 'a', 'zero_one')); b = rn.run(self.job('J1', 'b', 'zero_two'))
        self.assertEqual((a['result'], b['result'], b['replay']), ({'t': 'zero_one'}, {'t': 'zero_two'}, False))

    def test_requeue_is_explicit(self):
        mode = {'fail': True}
        def h(s, p):
            if mode['fail']:
                raise ValueError('x')
            return {'ok': True}
        rn = self.runner(h)
        self.assertEqual(rn.run(self.job())['status'], 'dead_letter')
        mode['fail'] = False
        self.assertEqual(rn.run(self.job())['status'], 'dead_letter')
        self.assertEqual(rn.requeue(self.job())['status'], 'succeeded')
        with self.assertRaises(ValueError):
            rn.requeue(self.job())

    def test_bad_arguments(self):
        with self.assertRaises(ValueError):
            jobs.JobRunner(self.provider, self.w.store, self.w.audit, lambda s, p: None, max_attempts=0)
        with self.assertRaises(ValueError):
            self.runner(lambda s, p: None).run({'credentials': 'a'})

    def test_handler_result_must_be_storable(self):
        r = self.runner(lambda s, p: {'x': 1.5}).run(self.job())
        self.assertEqual(r['status'], 'dead_letter')


if __name__ == '__main__':
    unittest.main()
