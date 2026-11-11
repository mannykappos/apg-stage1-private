"""Adversarial suite on the Builder Zero synthetic builder.  Three promises are attacked here:
   1. a tenant identifier cannot be spoofed;
   2. missing evidence cannot become false certainty;
   3. conflicting source records cannot silently influence an authoritative number.
Every attack asserts both that it is stopped AND what is left behind (nothing stored, a visible reason, an audit event)."""
import dataclasses, json, random, unittest
from . import _path                                          # noqa: F401
from apg import materiality_engine as ME, source_authority as SA, status_model as SM, tenancy
from apg.ports import NoContext, TenantMismatch, Unauthenticated
from apg.values import Known, Unknown, UnknownValueError, total
from .helpers import make_env, login, bz_rows
from .test_source_authority import rule, reg, ob


def invoices(tenant_dir):
    out = []
    for r in bz_rows(f'{tenant_dir}/SRC-01_accounting/ap_invoices.csv'):
        r = dict(r)
        for k in ('ex_gst_cents', 'gst_cents'):
            r[k] = int(r[k]) if r[k] != '' else None
        out.append(r)
    return out


class World(unittest.TestCase):
    def setUp(self):
        self.env, self.clock = make_env()
        self.c1 = login(self.env, 't1', 'zero_one', 'ann', ('finance_reviewer',)); self.c2 = login(self.env, 't2', 'zero_two', 'bob', ('finance_reviewer',))
        self.s1 = tenancy.ScopedStore(self.env.store, self.env.audit, self.c1); self.s2 = tenancy.ScopedStore(self.env.store, self.env.audit, self.c2)
        self.inv1, self.inv2 = invoices('zero_one'), invoices('zero_two')
        for s, rows in ((self.s1, self.inv1), (self.s2, self.inv2)):
            SA.ingest_batch(s, 'ap_invoice', rows, 'invoice_id')

    def count(self, s):
        return len(s.query('ap_invoice'))

    def events(self, ctx, kind):
        return [e for e in self.env.audit.read(ctx) if e.event_type == kind]


class TenantSpoofing(World):
    def test_colliding_identifiers_never_cross(self):
        self.assertEqual((self.count(self.s1), self.count(self.s2)), (len(self.inv1), len(self.inv2) - 2))            # zero_two repeats INV-0001 with different content: held, not stored
        a, b = self.s1.get('ap_invoice', 'INV-0001'), self.s2.get('ap_invoice', 'INV-0002')
        self.assertIsNone(self.s2.get('ap_invoice', 'INV-0001')); self.assertEqual(a.tenant_id, 'zero_one'); self.assertEqual(b.tenant_id, 'zero_two')
        self.assertNotEqual(self.s1.get('ap_invoice', 'INV-0002').payload_hash, b.payload_hash)
        only_in_one = sorted({r['invoice_id'] for r in self.inv1} - {r['invoice_id'] for r in self.inv2})[0]
        self.assertIsNone(self.s2.get('ap_invoice', only_in_one))

    SPOOFS = [{'tenant_id': 'zero_one'}, {'TenantID': 'zero_one'}, {'tenant­_id': 'zero_one'}, {'t​enant': 'zero_one'}, {'ｔenant_id': 'zero_one'}, {'x-tenant': 'zero_one'},
              {'org_id': 'zero_one'}, {'Organisation': 'zero_one'}, {'customer id': 'zero_one'}, {'meta': {'deep': [{'tenant': 'zero_one'}]}},
              {'note': json.dumps({'tenantId': 'zero_one'})}, {'note': json.dumps({'a': json.dumps({'tenant': 'zero_one'})})}, {'tenant_id': ['zero_one']}, {'tenant_id': 'ZERO_ONE'},
              {'tenant_id': ' zero_one'}, {'tenant_id': None}, {'tenant_id': 1}]

    def test_every_spoof_is_refused_stores_nothing_and_is_audited_against_the_attacker(self):
        before2, before1 = self.count(self.s2), self.count(self.s1); audit1_before = len(self.env.audit.read(self.c1))
        for i, extra in enumerate(self.SPOOFS):
            with self.assertRaises(TenantMismatch, msg=str(extra)):
                self.s2.put('ap_invoice', f'EVIL-{i}', dict(self.inv2[0], **extra))
        self.assertEqual(self.count(self.s2), before2); self.assertEqual(self.count(self.s1), before1)
        self.assertIsNone(self.s1.get('ap_invoice', 'EVIL-0')); self.assertEqual(len(self.events(self.c2, 'tenant_claim.refused')), len(self.SPOOFS))
        self.assertEqual(len(self.env.audit.read(self.c1)), audit1_before)                       # the victim's log is untouched

    def test_matching_claim_is_removed_and_never_stored(self):
        r = self.s1.put('ap_invoice', 'OK-1', dict(self.inv1[0], tenant_id='zero_one', note=json.dumps({'tenant': 'zero_one'})))
        self.assertNotIn('tenant_id', r.payload); self.assertEqual(tenancy.find_claims(r.payload), [])

    def test_look_alike_of_the_callers_own_tenant_is_not_a_matching_claim(self):
        for v in ('ZERO_ONE', ' zero_one', 'zero_one ', 'zero_one\u200b', 'zero\u2011one', 'ｚero_one'):
            with self.assertRaises(TenantMismatch, msg=repr(v)): self.s1.put('ap_invoice', 'LOOK', dict(self.inv1[0], tenant_id=v))
        self.assertIsNone(self.s1.get('ap_invoice', 'LOOK'))
        with self.assertRaises(TenantMismatch): tenancy.bind_job(self.env.provider, self.env.store, self.env.audit, {'credentials': 't1', 'claimed_tenant': 'ZERO_ONE', 'payload': {}})

    def test_spoof_inside_an_atomic_batch_applies_nothing(self):
        before = self.count(self.s2)
        ops = [('ap_invoice', 'B-1', dict(self.inv2[0]), None), ('ap_invoice', 'B-2', dict(self.inv2[0], org_id='zero_one'), None)]
        with self.assertRaises(TenantMismatch): self.s2.atomic(ops)
        self.assertEqual(self.count(self.s2), before); self.assertIsNone(self.s2.get('ap_invoice', 'B-1'))

    def test_spoofed_filter_is_refused(self):
        for w in ({'tenant_id': 'zero_one'}, {'Org': 'zero_one'}, {'project_id': 'PRJ-001', 'tenantId': 'zero_one'}):
            with self.assertRaises(TenantMismatch): self.s2.query('ap_invoice', w)

    def test_nesting_bomb_cannot_hide_a_claim(self):
        deep = {'tenant_id': 'zero_one'}
        for _ in range(60):
            deep = {'x': deep}
        with self.assertRaises(TenantMismatch): self.s2.put('ap_invoice', 'DEEP', dict(self.inv2[0], meta=deep))
        bomb = {}
        for _ in range(5000):                                   # far deeper than the interpreter can recurse: must fail closed, not crash or slip through
            bomb = {'x': bomb}
        with self.assertRaises(TenantMismatch): self.s2.put('ap_invoice', 'BOMB', dict(self.inv2[0], meta=bomb))
        self.assertIsNone(self.s2.get('ap_invoice', 'BOMB'))

    def test_forged_altered_expired_and_revoked_contexts_are_useless(self):
        forged = dataclasses.replace(self.c2, tenant_id='zero_one')
        for call in (lambda: self.env.store.get(forged, 'ap_invoice', 'INV-0001'), lambda: self.env.store.put(forged, 'ap_invoice', 'X', {'a': 1}), lambda: self.env.store.query(forged, 'ap_invoice'),
                     lambda: self.env.audit.read(forged), lambda: self.env.audit.append(forged, 'x', 'y', 'ok')):
            with self.assertRaises(Unauthenticated): call()
        self.assertFalse(self.env.provider.verify(forged))
        self.env.provider._contract_revoke('t2')
        with self.assertRaises(Unauthenticated): self.env.store.get(self.c2, 'ap_invoice', 'INV-0001')
        c3 = login(self.env, 't3', 'zero_two', 'cy'); self.env.advance(7200)
        with self.assertRaises(Unauthenticated): self.env.store.get(c3, 'ap_invoice', 'INV-0001')

    def test_a_context_cannot_be_invented_or_omitted(self):
        for bad in (None, {'tenant_id': 'zero_one'}, 'zero_one', 'ann'):
            with self.assertRaises((NoContext, Unauthenticated, AttributeError, TypeError)): self.env.store.get(bad, 'ap_invoice', 'INV-0001')
        with self.assertRaises(NoContext): tenancy.ScopedStore(self.env.store, self.env.audit, None)
        with self.assertRaises(NoContext): dataclasses.replace(self.c2, tenant_id='')

    def test_jobs_reauthenticate_and_cannot_borrow_another_tenant(self):
        scoped, clean = tenancy.bind_job(self.env.provider, self.env.store, self.env.audit, {'credentials': 't2', 'payload': {'invoice': 'INV-0001'}})
        self.assertEqual(scoped.ctx.tenant_id, 'zero_two')
        with self.assertRaises(TenantMismatch): tenancy.bind_job(self.env.provider, self.env.store, self.env.audit, {'credentials': 't2', 'claimed_tenant': 'zero_one', 'payload': {}})
        with self.assertRaises(TenantMismatch): tenancy.bind_job(self.env.provider, self.env.store, self.env.audit, {'credentials': 't2', 'payload': {'tenant_id': 'zero_one'}})
        for creds in ('', None, 'unknown'):
            with self.assertRaises(Unauthenticated): tenancy.bind_job(self.env.provider, self.env.store, self.env.audit, {'credentials': creds, 'payload': {}})
        with self.assertRaises(Unauthenticated): tenancy.bind_job(self.env.provider, self.env.store, self.env.audit, {'payload': {}})

    def test_materiality_assessment_cannot_be_spoofed_either(self):
        with self.assertRaises(TenantMismatch): ME.assess_record(self.s2, {'id': 'x', 'subject': 'invoice', 'amount_cents': 1, 'org_id': 'zero_one'})
        with self.assertRaises(TenantMismatch): ME.assess_record(self.s2, {'id': 'x', 'subject': 'invoice', 'amount_cents': 1}, [{'id': 'y', 'subject': 'invoice', 'tenant': 'zero_one'}])

    def test_tenant_two_assessment_never_uses_tenant_one_policy(self):
        pol = {'version': 'P1', 'rules': {'invoice': {'abs_cents': 1000}}, 'always_material': [], 'aggregate': False}
        p = tenancy.ScopedStore(self.env.store, self.env.audit, login(self.env, 'tp', 'zero_one', 'prop'))
        o1 = tenancy.ScopedStore(self.env.store, self.env.audit, login(self.env, 'to1', 'zero_one', 'o1', ('materiality_owner',)))
        o2 = tenancy.ScopedStore(self.env.store, self.env.audit, login(self.env, 'to2', 'zero_one', 'o2', ('materiality_owner',)))
        ME.propose_policy(p, pol); ME.approve_policy(o1, 'P1'); ME.approve_policy(o2, 'P1'); ME.activate_policy(o1, 'P1')
        rec = {'id': 'r', 'subject': 'invoice', 'amount_cents': 1}
        self.assertFalse(ME.assess_record(o1, rec).material); self.assertEqual(ME.assess_record(self.s2, rec).reasons, (ME.NO_ACTIVE,))


class IntakeConflicts(World):
    def test_same_identifier_with_different_content_in_one_batch_is_held_not_silently_overwritten(self):
        self.assertIsNone(self.s2.get('ap_invoice', 'INV-0001'))
        clean, bad = SA.batch_conflicts(self.inv2, 'invoice_id'); self.assertEqual(list(bad), ['INV-0001']); self.assertEqual(len(bad['INV-0001']), 2)
        self.assertEqual(len(self.events(self.c2, 'ingest.conflict')), 1)
        self.assertEqual(len(self.s2.history('ap_invoice', 'INV-0002')), 1)

    def test_identical_repeats_collapse_and_missing_identifiers_are_held(self):
        r = {'invoice_id': 'A', 'v': 1}; clean, bad = SA.batch_conflicts([r, dict(r), {'v': 2}, {'invoice_id': '', 'v': 3}, {'invoice_id': 'B', 'v': 1}, {'invoice_id': 'B', 'v': 2}, 'junk'], 'invoice_id')
        self.assertEqual([c['invoice_id'] for c in clean], ['A']); self.assertEqual(set(bad), {'<no identifier>', 'B'}); self.assertEqual(len(bad['<no identifier>']), 3)

    def test_conflict_rows_can_be_held_for_review_with_their_evidence(self):
        _, bad = SA.batch_conflicts(self.inv2, 'invoice_id'); res = SA.resolve_field(reg(), 'INV-0001', 'ap_invoice', 'ex_gst_cents',
                                                                                    [ob('accounting', int(r['ex_gst_cents']), rev=1) for r in bad['INV-0001']], '2026-09-30')
        self.assertEqual(res.outcome, SA.QUARANTINED); SA.QuarantineQueue(self.s2).hold('INV-0001', res, 'finance_reviewer', observations=bad['INV-0001'])
        self.assertEqual(len(SA.QuarantineQueue(self.s2).open_items()), 1)


class MissingEvidence(World):
    def rows(self, invs, blanks):
        out = []
        for r in invs:
            v = None if r['invoice_id'] in blanks else r['ex_gst_cents']
            x = SA.resolve_field(reg(), r['invoice_id'], 'ap_invoice', 'ex_gst_cents', [ob('accounting', v if v is not None else Unknown('not_obtained', 'blank in export'))], '2026-09-30')
            out.append((r['invoice_id'], x.outcome, x.value, x.reasons))
        return out

    def test_blank_amounts_are_excluded_and_listed_never_counted_as_zero(self):
        blanks = {r['invoice_id'] for r in self.inv1[:5]}
        t = SA.authoritative_total(self.rows(self.inv1, blanks))
        self.assertFalse(t.complete); self.assertEqual({e[0] for e in t.excluded}, blanks); self.assertEqual(len(t.included), len(self.inv1) - 5)
        self.assertEqual(t.cents, sum(r['ex_gst_cents'] for r in self.inv1 if r['invoice_id'] not in blanks))
        for e in t.excluded: self.assertTrue(e[2])

    def test_complete_only_when_nothing_is_missing(self):
        t = SA.authoritative_total(self.rows(self.inv1, set())); self.assertTrue(t.complete); self.assertEqual(t.cents, sum(r['ex_gst_cents'] for r in self.inv1))

    def test_unknown_values_cannot_be_used_as_numbers(self):
        u = Unknown('no_data')
        for op in (lambda: u + 1, lambda: 1 + u, lambda: u * 2, lambda: int(u), lambda: u.cents, lambda: bool(u), lambda: u < 1, lambda: sum([Known(1), u])):
            with self.assertRaises((UnknownValueError, TypeError)): op()

    def test_total_over_values_says_what_it_left_out(self):
        t = total([('a', Known(100)), ('b', Unknown('stale')), ('c', Known(50)), ('d', Unknown('no_data'))])
        self.assertEqual(t.cents, 150); self.assertFalse(t.complete)
        with self.assertRaises(UnknownValueError): t.require_complete()

    def test_missing_in_both_sources_gives_no_value(self):
        x = SA.resolve_field(reg(), 'I', 'ap_invoice', 'ex_gst_cents', [ob('pm-system', 5)], '2026-09-30')
        self.assertEqual((x.outcome, x.authoritative, x.reasons), (SA.PENDING, False, ('AUTHORITATIVE_SOURCE_ABSENT',))); self.assertIsInstance(x.value, Unknown)
        y = SA.resolve_field(reg(), 'I', 'ap_invoice', 'ex_gst_cents', [], '2026-09-30'); self.assertEqual(y.outcome, SA.PENDING)

    def test_ocr_value_is_provisional_until_a_human_verifies(self):
        o = ob('accounting', 1234, origin='ai_extracted'); x = SA.resolve_field(reg(), 'I', 'ap_invoice', 'ex_gst_cents', [o], '2026-09-30')
        self.assertEqual((x.outcome, x.reasons), (SA.PENDING, ('AWAITING_HUMAN_VERIFICATION',)))
        a = SA.authoritative_total([('I', x.outcome, x.value, x.reasons)]); p = SA.provisional_total([('I', x.outcome, Known(1234))], '2026-09-30')
        self.assertEqual(a.cents, 0); self.assertFalse(a.complete); self.assertEqual(p.cents, 1234); self.assertIn('PROVISIONAL', p.label)
        with self.assertRaises(TypeError): a + p
        with self.assertRaises(TypeError): p + a
        with self.assertRaises(TypeError): a + 5
        v = SA.resolve_field(reg(), 'I', 'ap_invoice', 'ex_gst_cents', [dataclasses.replace(o, human_verified=True)], '2026-09-30'); self.assertTrue(v.authoritative)

    def test_the_comparison_view_keeps_the_two_apart(self):
        a = SA.authoritative_total([('I', SA.ACCEPTED, 100, ()), ('J', SA.PENDING, Unknown('no_data'), ('X',))]); p = SA.provisional_total([('J', SA.PENDING, Known(900))], '2026-09-30')
        c = SA.compare_views(a, p); self.assertEqual((c['authoritative_cents'], c['provisional_only_cents'], c['unresolved_records']), (100, 900, 1)); self.assertFalse(c['authoritative_complete'])

    def test_missing_amounts_are_always_material_never_below_threshold(self):
        pol = {'version': 'AP1', 'rules': {'invoice': {'abs_cents': 25000000}}, 'always_material': [], 'aggregate': False}
        p = tenancy.ScopedStore(self.env.store, self.env.audit, login(self.env, 'tp', 'zero_one', 'prop'))
        o1 = tenancy.ScopedStore(self.env.store, self.env.audit, login(self.env, 'to1', 'zero_one', 'o1', ('materiality_owner',)))
        o2 = tenancy.ScopedStore(self.env.store, self.env.audit, login(self.env, 'to2', 'zero_one', 'o2', ('materiality_owner',)))
        ME.propose_policy(p, pol); ME.approve_policy(o1, 'AP1'); ME.approve_policy(o2, 'AP1'); ME.activate_policy(o1, 'AP1')
        for r in self.inv1[:20]:
            a = ME.assess_record(o1, {'id': r['invoice_id'], 'subject': 'invoice', 'amount_cents': Unknown('not_obtained')}); self.assertEqual((a.material, a.reasons), (True, ('M-AMOUNT-MISSING',)))
        small = ME.assess_record(o1, {'id': 'S', 'subject': 'invoice', 'amount_cents': Known(100)}); self.assertEqual((small.material, small.reasons), (False, ('NM-BELOW',)))

    def test_a_claimed_status_without_the_evidence_is_exposed(self):
        h = 'b' * 64
        ev = lambda kind, env, **k: SM.Evidence(**{'kind': kind, 'ref': kind, 'requirement_ids': ('R',), 'build': 'b1', 'environment': env, 'result': 'pass', 'actor': 'dev', 'actor_kind': 'human',
                                                    'role': '', 'mock_only': False, 'tests': ('T',) if env != 'n/a' else (), 'components': ('x',), 'integrity_hash': h if env != 'n/a' else '', **k})
        claimed = [('Specified', ev('approval', 'n/a', role='product_owner', actor='po')), ('Implemented', ev('implementation', 'n/a')), ('Local-tested', ev('test_run', 'local', mock_only=True)),
                   ('Integration-tested', ev('integration_run', 'integration', mock_only=True)), ('Staging-verified', ev('staging_run', 'staging'))]
        st, err = SM.supported_status('R', claimed); self.assertEqual(st.status, 'Local-tested'); self.assertEqual(err.code, 'MOCK_ONLY')


class ConflictingSources(World):
    def bz_conflict(self):
        pm = bz_rows('zero_one/conflicting_sources/pm_system_invoices.csv')
        self.assertEqual(len(pm), 1); return pm[0]

    def resolve(self, r, pm_cents, rule_=None):
        obs = [ob('accounting', r['ex_gst_cents'], ref=f"accounting:{r['invoice_id']}@1", rev=1)]
        if pm_cents is not None: obs.append(ob('pm-system', pm_cents, ref=f"pm:{r['invoice_id']}@1"))
        return SA.resolve_field(reg([rule_ or rule()]), r['invoice_id'], 'ap_invoice', 'ex_gst_cents', obs, '2026-09-30')

    def all_rows(self, rule_=None):
        pm = self.bz_conflict(); rows = []
        for r in self.inv1:
            x = self.resolve(r, int(pm['ex_gst_cents']) if r['invoice_id'] == pm['invoice_ref'] else None, rule_)
            rows.append((r['invoice_id'], x.outcome, x.value, x.reasons))
        return rows, pm

    def test_the_planted_disagreement_is_quarantined_and_left_out_of_the_total(self):
        rows, pm = self.all_rows(); t = SA.authoritative_total(rows)
        self.assertFalse(t.complete); self.assertEqual([e[0] for e in t.excluded], [pm['invoice_ref']]); self.assertEqual(t.excluded[0][1], SA.QUARANTINED)
        acc = next(r for r in self.inv1 if r['invoice_id'] == pm['invoice_ref'])
        everything = sum(r['ex_gst_cents'] for r in self.inv1); self.assertEqual(t.cents, everything - acc['ex_gst_cents'])
        self.assertNotIn(int(pm['ex_gst_cents']), (t.cents, everything))

    def test_neither_side_appears_in_the_total_but_both_are_shown_to_the_reviewer(self):
        pm = self.bz_conflict(); acc = next(r for r in self.inv1 if r['invoice_id'] == pm['invoice_ref'])
        x = self.resolve(acc, int(pm['ex_gst_cents'])); self.assertIsInstance(x.value, Unknown); self.assertFalse(x.authoritative)
        self.assertEqual(dict(x.candidates), {'accounting': str(acc['ex_gst_cents']), 'pm-system': pm['ex_gst_cents']})

    def test_warning_mode_uses_the_authoritative_value_only_and_says_so(self):
        rows, pm = self.all_rows(rule(on_secondary_disagreement='authoritative_wins_with_warning'))
        acc = next(r for r in self.inv1 if r['invoice_id'] == pm['invoice_ref'])
        x = self.resolve(acc, int(pm['ex_gst_cents']), rule(on_secondary_disagreement='authoritative_wins_with_warning'))
        self.assertEqual((x.outcome, x.value.cents), (SA.ACCEPTED_W, acc['ex_gst_cents'])); self.assertTrue(any('SECONDARY_DISAGREES' in w for w in x.warnings))
        self.assertEqual(SA.authoritative_total(rows).cents, sum(r['ex_gst_cents'] for r in self.inv1))

    def test_a_later_timestamp_never_wins_and_order_never_matters(self):
        base = [ob('accounting', 1000, rev=3, ts='2020-01-01T00:00:00Z'), ob('accounting', 9999, rev=2, ts='2030-01-01T00:00:00Z'), ob('pm-system', 1000, ts='2031-01-01T00:00:00Z')]
        rng = random.Random(7); seen = set()
        for _ in range(60):
            rng.shuffle(base); x = SA.resolve_field(reg(), 'I', 'ap_invoice', 'ex_gst_cents', list(base), '2026-09-30'); seen.add((x.outcome, x.value.cents))
        self.assertEqual(seen, {(SA.ACCEPTED, 1000)})

    def test_same_revision_or_unknown_revision_conflict_is_quarantined(self):
        for obs in ([ob('accounting', 1, rev=2), ob('accounting', 2, rev=2)], [ob('accounting', 1), ob('accounting', 2)], [ob('accounting', 1, rev=1), ob('accounting', 2)]):
            x = SA.resolve_field(reg(), 'I', 'ap_invoice', 'ex_gst_cents', obs, '2026-09-30'); self.assertEqual((x.outcome, x.authoritative), (SA.QUARANTINED, False))

    def test_a_cancelled_or_unpermitted_source_does_not_influence_the_value(self):
        x = SA.resolve_field(reg(), 'I', 'ap_invoice', 'ex_gst_cents', [ob('accounting', 100, rev=1), ob('accounting', 999, rev=2, cancelled=True), ob('rumour-mill', 5000)], '2026-09-30')
        self.assertEqual((x.outcome, x.value.cents), (SA.ACCEPTED_W, 100)); self.assertIn('SOURCE_NOT_PERMITTED:rumour-mill', x.warnings)

    def test_quarantined_conflict_stays_out_until_two_people_resolve_it(self):
        pm = self.bz_conflict(); acc = next(r for r in self.inv1 if r['invoice_id'] == pm['invoice_ref']); x = self.resolve(acc, int(pm['ex_gst_cents']), rule(required_approvals=2))
        q = SA.QuarantineQueue(self.s1); q.hold(acc['invoice_id'], x, 'finance_reviewer', 2)
        r2 = tenancy.ScopedStore(self.env.store, self.env.audit, login(self.env, 'tr2', 'zero_one', 'rae', ('finance_reviewer',)))
        q.dispose(self.c1, acc['invoice_id'], 'accept', 'accounting ledger confirmed against paper invoice')
        self.assertEqual(len(q.open_items()), 1)                                                    # one approval is not enough
        with self.assertRaises(SA.AuthorityError): q.dispose(self.c1, acc['invoice_id'], 'accept', 'again')                  # same person twice
        q.dispose(r2.ctx, acc['invoice_id'], 'accept', 'second check'); self.assertEqual(q.open_items(), ())
        self.assertEqual(self.s1.get('quarantine', acc['invoice_id']).payload['status'], 'promoted')

    def test_other_tenants_conflicts_are_invisible(self):
        pm = self.bz_conflict(); acc = next(r for r in self.inv1 if r['invoice_id'] == pm['invoice_ref']); x = self.resolve(acc, int(pm['ex_gst_cents']))
        SA.QuarantineQueue(self.s1).hold(acc['invoice_id'], x, 'finance_reviewer')
        self.assertEqual(SA.QuarantineQueue(self.s2).open_items(), ()); self.assertIsNone(self.s2.get('quarantine', acc['invoice_id']))

    def test_a_conflicted_value_feeds_materiality_as_missing_not_as_either_number(self):
        pm = self.bz_conflict(); acc = next(r for r in self.inv1 if r['invoice_id'] == pm['invoice_ref']); x = self.resolve(acc, int(pm['ex_gst_cents']))
        pol = {'version': 'AP2', 'rules': {'invoice': {'abs_cents': 10 ** 12}}, 'always_material': [], 'aggregate': False}
        p = tenancy.ScopedStore(self.env.store, self.env.audit, login(self.env, 'tp', 'zero_one', 'prop'))
        o1 = tenancy.ScopedStore(self.env.store, self.env.audit, login(self.env, 'to1', 'zero_one', 'o1', ('materiality_owner',)))
        o2 = tenancy.ScopedStore(self.env.store, self.env.audit, login(self.env, 'to2', 'zero_one', 'o2', ('materiality_owner',)))
        ME.propose_policy(p, pol); ME.approve_policy(o1, 'AP2'); ME.approve_policy(o2, 'AP2'); ME.activate_policy(o1, 'AP2')
        a = ME.assess_record(o1, {'id': acc['invoice_id'], 'subject': 'invoice', 'amount_cents': x.value}); self.assertEqual((a.material, a.reasons), (True, ('M-AMOUNT-MISSING',)))


if __name__ == '__main__':
    unittest.main()
