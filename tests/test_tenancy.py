import unittest
from . import _path                                          # noqa: F401
from .helpers import make_env, login
from apg import tenancy
from apg.ports import TenantMismatch, Unauthenticated, NoContext


class ClaimDetection(unittest.TestCase):
    def test_claim_keys_found_in_many_disguises(self):
        for k in ('tenant_id', 'tenantId', 'TENANT_ID', 'Tenant-Id', 'x-tenant-id', 'tenant id', 'organisation_id', 'organizationId', 'orgId',
                  'tenant​_id', 'ｔｅｎａｎｔ_id', 'te­nant', 'customer_id', 'TenantRef'):
            self.assertTrue(tenancy.is_claim_key(k), repr(k))

    def test_ordinary_keys_not_flagged(self):
        for k in ('invoice_id', 'supplier_id', 'project_id', 'amount_cents', 'account_number', 'description'):
            self.assertFalse(tenancy.is_claim_key(k), k)

    def test_nested_list_and_embedded_json_claims_found(self):
        p = {'a': [{'b': {'Tenant-ID': 'B'}}], 'note': '{"organisation_id": "B"}', 'deep': {'x': {'y': {'tenantId': 'B'}}}}
        paths = [c[0] for c in tenancy.find_claims(p)]
        self.assertEqual(len(paths), 3)

    def test_depth_bomb_is_refused_not_ignored(self):
        p = cur = {}
        for _ in range(60):
            cur['n'] = {}; cur = cur['n']
        with self.assertRaises(TenantMismatch):
            tenancy.find_claims(p)


class Screening(unittest.TestCase):
    def setUp(self):
        self.env, _ = make_env(); self.a = login(self.env, 'tokA', 'tenant-A')

    def test_matching_claim_stripped_not_used(self):
        clean, claims = tenancy.screen_payload(self.a, {'tenant_id': 'tenant-A', 'v': 1, 'inner': {'org_id': 'tenant-A'}})
        self.assertEqual(clean, {'v': 1, 'inner': {}}); self.assertEqual(len(claims), 2)

    def test_foreign_claim_refused_and_audited(self):
        with self.assertRaises(TenantMismatch):
            tenancy.screen_payload(self.a, {'items': [{'tenantId': 'tenant-B'}]}, self.env.audit)
        ev = self.env.audit.read(self.a)
        self.assertEqual(len(ev), 1); self.assertEqual(ev[0].event_type, 'tenant_claim.refused'); self.assertEqual(ev[0].outcome, 'refused')

    def test_non_string_and_lookalike_claims_refused(self):
        for v in (['tenant-A'], {'id': 'tenant-A'}, 5, None, 'tenant-A ', 'Tenant-A', 'tenant‑A', 'tenant-A​'):
            with self.assertRaises(TenantMismatch, msg=repr(v)):
                tenancy.screen_payload(self.a, {'tenant_id': v})

    def test_embedded_json_claim_refused(self):
        with self.assertRaises(TenantMismatch):
            tenancy.screen_payload(self.a, {'blob': '{"tenant_id": "tenant-B"}'})

    def test_no_context_refused(self):
        with self.assertRaises(NoContext):
            tenancy.screen_payload(None, {})
        with self.assertRaises(NoContext):
            tenancy.screen_payload({'tenant_id': 'tenant-A'}, {})


class Scoped(unittest.TestCase):
    def setUp(self):
        self.env, _ = make_env()
        self.a = login(self.env, 'tokA', 'tenant-A'); self.b = login(self.env, 'tokB', 'tenant-B')
        self.sa = tenancy.ScopedStore(self.env.store, self.env.audit, self.a); self.sb = tenancy.ScopedStore(self.env.store, self.env.audit, self.b)

    def test_scoped_stores_cannot_see_each_other(self):
        self.sa.put('invoice', 'INV-0001', {'v': 'A'}); self.sb.put('invoice', 'INV-0001', {'v': 'B'})
        self.assertEqual(self.sa.get('invoice', 'INV-0001').payload, {'v': 'A'}); self.assertEqual(self.sb.get('invoice', 'INV-0001').payload, {'v': 'B'})

    def test_put_with_foreign_claim_stores_nothing(self):
        with self.assertRaises(TenantMismatch):
            self.sa.put('invoice', 'X', {'tenant_id': 'tenant-B', 'v': 1})
        self.assertIsNone(self.sa.get('invoice', 'X')); self.assertIsNone(self.sb.get('invoice', 'X'))

    def test_atomic_with_one_bad_claim_applies_nothing(self):
        with self.assertRaises(TenantMismatch):
            self.sa.atomic([('invoice', 'P', {'v': 1}, None), ('invoice', 'Q', {'org_id': 'tenant-B'}, None)])
        self.assertIsNone(self.sa.get('invoice', 'P'))

    def test_foreign_filter_is_refused(self):
        self.sa.put('invoice', 'P', {'v': 1}); self.sb.put('invoice', 'Q', {'v': 1})
        with self.assertRaises(TenantMismatch):
            self.sa.query('invoice', {'tenant_id': 'tenant-B'})

    def test_forged_context_cannot_even_build_a_scoped_store_that_works(self):
        import dataclasses
        forged = dataclasses.replace(self.a, tenant_id='tenant-B')
        s = tenancy.ScopedStore(self.env.store, self.env.audit, forged)
        with self.assertRaises(Unauthenticated):
            s.get('invoice', 'INV-0001')


class Jobs(unittest.TestCase):
    def setUp(self):
        self.env, _ = make_env(); login(self.env, 'tokA', 'tenant-A'); login(self.env, 'tokB', 'tenant-B')

    def test_job_rebinds_from_credentials(self):
        s, clean = tenancy.bind_job(self.env.provider, self.env.store, self.env.audit, {'credentials': 'tokA', 'payload': {'v': 1}})
        self.assertEqual(s.ctx.tenant_id, 'tenant-A'); self.assertEqual(clean, {'v': 1})

    def test_job_claiming_other_tenant_refused_and_audited(self):
        with self.assertRaises(TenantMismatch):
            tenancy.bind_job(self.env.provider, self.env.store, self.env.audit, {'credentials': 'tokA', 'claimed_tenant': 'tenant-B', 'payload': {}})
        ctxA = self.env.provider.resolve('tokA')
        self.assertEqual(self.env.audit.read(ctxA)[0].event_type, 'tenant_claim.refused')

    def test_job_without_credentials_or_bad_credentials_refused(self):
        for job in ({}, {'payload': {}}, {'credentials': '', 'payload': {}}, {'credentials': 'nope', 'payload': {}}, None):
            with self.assertRaises(Unauthenticated, msg=repr(job)):
                tenancy.bind_job(self.env.provider, self.env.store, self.env.audit, job)

    def test_retry_of_job_cannot_change_tenant(self):
        job = {'credentials': 'tokA', 'payload': {'v': 1}}
        s1, _ = tenancy.bind_job(self.env.provider, self.env.store, self.env.audit, job)
        s2, _ = tenancy.bind_job(self.env.provider, self.env.store, self.env.audit, dict(job))
        self.assertEqual(s1.ctx.tenant_id, s2.ctx.tenant_id)


if __name__ == '__main__':
    unittest.main()
