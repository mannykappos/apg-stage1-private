import copy, unittest
from . import _path                                         # noqa: F401
from .helpers_ingest import INV_H, World, csvb, inv, inv_file, load_suppliers, tpl
from apg import canon
from apg.ingest import demo_setup as D, pipeline as P
from apg.ports import ConflictError, TenantMismatch

T = tpl('TPL-BZ-AP-INVOICES')
BUD = tpl('TPL-BZ-BUDGET-LINES')
BUD_H = ['project_id', 'cost_code', 'budget_cents', 'revision', 'revision_date']


def ingest(w, s, rows, template=T, source='accounting', header=None, revision_field=None, name='f.csv', policy=D.DEMO_POLICY, note=None):
    hdr = list(header or INV_H)
    if note is not None:                                   # an unmapped column changes the file's bytes without changing any record's content
        hdr.append('note'); rows = [list(r) + [note] for r in rows]
    data = csvb(hdr, rows)
    return P.ingest_file(s, w.clock, template, data, source, name, policy, revision_field)


def latest(s, kind, key):
    return s.get(kind, key)


class TestDeliveryDecisions(unittest.TestCase):
    def setUp(self):
        self.w = World(); self.s = self.w.who('a')

    def test_new_record_carries_provenance_and_raw_text(self):
        r = ingest(self.w, self.s, [inv(ex=' 000100 ')], name='ap.csv')
        rec = self.s.get('ap_invoice', 'INV-1')
        p = rec.payload
        self.assertEqual(r['counts']['new'], 1)
        self.assertEqual(p['provenance']['file_name'], 'ap.csv')
        self.assertEqual(p['provenance']['file_sha256'], r['file_sha256'])
        self.assertEqual((p['provenance']['uploaded_by'], p['provenance']['row_no'], p['provenance']['source']), ('ann', 1, 'accounting'))
        self.assertEqual(p['raw']['ex_gst_cents'], ' 000100 ')
        self.assertEqual(p['fields']['amount_ex_gst_cents'], 100)
        self.assertTrue(p['provenance']['mapping_version'])

    def test_same_file_again_is_a_recorded_no_op(self):
        data = csvb(INV_H, [inv(), inv('INV-2')])
        a = P.ingest_file(self.s, self.w.clock, T, data, 'accounting', 'f.csv', D.DEMO_POLICY)
        n = len(self.w.store.query(self.s.ctx, 'ap_invoice')), len(self.s.history('ap_invoice', 'INV-1'))
        b = P.ingest_file(self.s, self.w.clock, T, data, 'accounting', 'copy.csv', D.DEMO_POLICY)
        self.assertFalse(a['replay']); self.assertTrue(b['replay'])
        self.assertEqual(n, (len(self.w.store.query(self.s.ctx, 'ap_invoice')), len(self.s.history('ap_invoice', 'INV-1'))))
        self.assertEqual(len(self.s.query('ingest_receipt')), 1)
        self.assertTrue(any(e.event_type == 'ingest.replay' for e in self.w.audit.read(self.s.ctx)))

    def test_same_bytes_from_another_source_are_a_separate_receipt(self):
        data = csvb(INV_H, [inv()])
        P.ingest_file(self.s, self.w.clock, T, data, 'accounting', 'f.csv', D.DEMO_POLICY)
        b = P.ingest_file(self.s, self.w.clock, T, data, 'pm_system', 'f.csv', D.DEMO_POLICY)
        self.assertFalse(b['replay'])
        self.assertEqual(b['counts']['duplicate'], 1)                      # the record exists with identical content: a duplicate delivery, no new record

    def test_duplicate_row_in_a_new_file_changes_nothing(self):
        ingest(self.w, self.s, [inv()])
        rev = self.s.get('ap_invoice', 'INV-1').revision
        r = ingest(self.w, self.s, [inv(), inv('INV-2')], name='g.csv')
        self.assertEqual((r['counts']['duplicate'], r['counts']['new']), (1, 1))
        self.assertEqual(self.s.get('ap_invoice', 'INV-1').revision, rev)
        self.assertEqual(len(self.s.query('ingest_duplicate')), 1)         # evidence of the second delivery is kept

    def test_whitespace_and_formatting_differences_are_the_same_content(self):
        ingest(self.w, self.s, [inv(ex='1000000')])
        r = ingest(self.w, self.s, [inv(ex=' 01000000 ', invoice_id=' INV-1 ')], name='g.csv')
        self.assertEqual(r['counts']['duplicate'], 1)

    def test_changed_content_without_a_revision_is_a_conflict_not_an_overwrite(self):
        ingest(self.w, self.s, [inv(ex='1000000')])
        r = ingest(self.w, self.s, [inv(ex='1100000')], name='g.csv')
        self.assertEqual(r['counts']['conflict'], 1)
        rec = self.s.get('ap_invoice', 'INV-1')
        self.assertEqual(rec.payload['intrinsic']['outcome'], 'quarantined')
        self.assertEqual(rec.payload['fields'], {})                         # no value is presented as current
        amts = sorted(c['fields']['amount_ex_gst_cents'] for c in rec.payload['conflict']['contenders'])
        self.assertEqual(amts, [1000000, 1100000])
        self.assertEqual(self.s.history('ap_invoice', 'INV-1')[0].payload['fields']['amount_ex_gst_cents'], 1000000)      # the first value stays in history

    def test_conflict_marker_is_the_same_whichever_version_arrived_first(self):
        w2 = World(); s2 = w2.who('a')
        ingest(self.w, self.s, [inv(ex='1')]); ingest(self.w, self.s, [inv(ex='2')], name='g.csv')
        ingest(w2, s2, [inv(ex='2')]); ingest(w2, s2, [inv(ex='1')], name='g.csv')
        def strip(p):
            return [{k: c[k] for k in ('content_hash', 'fields', 'source_revision')} for c in p['conflict']['contenders']]
        self.assertEqual(strip(self.s.get('ap_invoice', 'INV-1').payload), strip(s2.get('ap_invoice', 'INV-1').payload))

    def test_a_third_version_joins_the_conflict_and_a_repeat_of_one_does_not(self):
        ingest(self.w, self.s, [inv(ex='1')]); ingest(self.w, self.s, [inv(ex='2')], name='g.csv')
        ingest(self.w, self.s, [inv(ex='3')], name='h.csv')
        r = ingest(self.w, self.s, [inv(ex='2')], name='i.csv', note='resent')
        self.assertEqual(r['counts']['duplicate'], 1)
        self.assertEqual(len(self.s.get('ap_invoice', 'INV-1').payload['conflict']['contenders']), 3)

    def test_same_key_twice_in_one_file_with_different_content_is_a_conflict(self):
        r = ingest(self.w, self.s, [inv(ex='1'), inv(ex='2')])
        self.assertEqual((r['counts']['new'], r['counts']['conflict']), (1, 1))
        self.assertEqual(self.s.get('ap_invoice', 'INV-1').payload['intrinsic']['outcome'], 'quarantined')
        self.assertEqual(self.s.get('ap_invoice', 'INV-1').revision, 1)      # one atomic write for the file

    def test_rejected_rows_are_kept_with_reasons_and_never_become_records(self):
        r = ingest(self.w, self.s, [inv(), inv('INV-2', date='nope'), inv('INV-3')])
        self.assertEqual((r['counts']['new'], r['counts']['rejected']), (2, 1))
        self.assertIsNone(self.s.get('ap_invoice', 'INV-2'))
        rej = self.s.query('ingest_reject')[0].payload
        self.assertEqual((rej['row_no'], rej['problems'][0]['code']), (2, 'INVALID_DATE'))
        self.assertEqual(rej['raw']['invoice_date'], 'nope')

    def test_partial_batch_is_visible_row_by_row(self):
        r = ingest(self.w, self.s, [inv(), inv('INV-2', ex='x'), inv('INV-3', ex='-5')])
        self.assertEqual([x['result'] for x in r['results']], ['new', 'rejected', 'new'])
        self.assertEqual(r['results'][2]['pending'], ['SIGN_CONVENTION:amount_ex_gst_cents'])

    def test_file_rejection_writes_no_records_and_is_audited(self):
        r = P.ingest_file(self.s, self.w.clock, T, b'', 'accounting', 'e.csv', D.DEMO_POLICY)
        self.assertEqual((r['status'], r['code']), ('file_rejected', 'EMPTY_FILE'))
        self.assertEqual(self.s.query('ap_invoice'), ())
        self.assertEqual(self.w.audit.read(self.s.ctx)[-1].event_type, 'ingest.file_rejected')

    def test_a_source_identity_is_required(self):
        with self.assertRaises(P.IngestError):
            P.ingest_file(self.s, self.w.clock, T, inv_file(inv()), '', 'f.csv')

    def test_unknown_entity_has_no_rules(self):
        t = copy.deepcopy(T); t['target_entity'] = 'mystery'
        with self.assertRaises(P.IngestError):
            P.ingest_file(self.s, self.w.clock, t, inv_file(inv()), 'accounting')

    def test_the_whole_file_is_one_atomic_write(self):
        orig = self.w.store.atomic
        calls = []
        def boom(ctx, ops):
            calls.append(len(ops)); raise ConflictError('simulated concurrent writer')
        self.w.store.atomic = boom
        with self.assertRaises(ConflictError):
            ingest(self.w, self.s, [inv(), inv('INV-2')])
        self.w.store.atomic = orig
        self.assertEqual(calls, [3])                                        # two records and the receipt, in ONE call
        self.assertEqual((self.s.query('ap_invoice'), self.s.query('ingest_receipt')), ((), ()))
        r = ingest(self.w, self.s, [inv(), inv('INV-2')])                   # the retry completes it, once
        self.assertEqual((r['counts']['new'], r['replay']), (2, False))

    def test_a_record_changed_by_someone_else_mid_file_aborts_the_whole_file(self):
        ingest(self.w, self.s, [inv()])
        data = csvb(INV_H, [inv(ex='9'), inv('INV-5')])
        real = self.s.get
        # simulate: between reading INV-1 and the write, another writer appends a revision
        def get_then_bump(kind, key, revision=None):
            rec = real(kind, key, revision)
            if kind == 'ap_invoice' and key == 'INV-1' and not getattr(get_then_bump, 'done', False):
                get_then_bump.done = True
                self.w.store.put(self.s.ctx, 'ap_invoice', 'INV-1', dict(rec.payload, row_hash='changed-elsewhere'))
            return rec
        self.s.get = get_then_bump
        with self.assertRaises(ConflictError):
            P.ingest_file(self.s, self.w.clock, T, data, 'accounting', 'g.csv', D.DEMO_POLICY)
        self.s.get = real
        self.assertIsNone(self.s.get('ap_invoice', 'INV-5'))               # nothing from that file was applied

    def test_audit_chain_verifies_after_ingestion(self):
        ingest(self.w, self.s, [inv(), inv('INV-2')])
        self.assertTrue(self.w.audit.verify(self.s.ctx).ok)


class TestRevisions(unittest.TestCase):
    def setUp(self):
        self.w = World(); self.s = self.w.who('a')

    def bud(self, rev, cents='100', key=('PRJ-001', 'CC-01')):
        return csvb(BUD_H, [[key[0], key[1], cents, rev, '2026-01-01']])

    def go(self, data, name='b.csv'):
        return P.ingest_file(self.s, self.w.clock, BUD, data, 'job_costing', name, D.DEMO_POLICY, 'source_revision_label')

    def test_parse_revision(self):
        self.assertEqual([P.parse_revision(x) for x in ('3', 'R3', 'r12', ' 7 ', 'F-2026-08', '', 'R', '1.5', None, True, 4)], [3, 3, 12, 7, None, None, None, None, None, None, 4])

    def test_higher_revision_supersedes_and_old_stays_in_history(self):
        self.go(self.bud('R0', '100')); r = self.go(self.bud('R1', '150'), 'c.csv')
        self.assertEqual(r['counts']['revision'], 1)
        key = 'PRJ-001|CC-01'
        self.assertEqual(self.s.get('budget_line', key).payload['fields']['budget_cents'], 150)
        self.assertEqual([h.payload['fields']['budget_cents'] for h in self.s.history('budget_line', key)], [100, 150])

    def test_an_older_revision_arriving_late_does_not_revert(self):
        self.go(self.bud('R2', '200'))
        r = self.go(self.bud('R1', '100'), 'c.csv')
        self.assertEqual(r['counts']['stale'], 1)
        self.assertEqual(self.s.get('budget_line', 'PRJ-001|CC-01').payload['fields']['budget_cents'], 200)
        self.assertEqual(len(self.s.history('budget_line', 'PRJ-001|CC-01')), 1)
        self.assertEqual(self.s.query('ingest_stale')[0].payload['incoming_revision'], 1)

    def test_same_revision_different_content_is_a_conflict(self):
        self.go(self.bud('R1', '100')); r = self.go(self.bud('R1', '999'), 'c.csv')
        self.assertEqual(r['counts']['conflict'], 1)

    def test_unparseable_revision_has_no_order_so_a_change_conflicts(self):
        self.go(self.bud('draft-a', '100')); r = self.go(self.bud('draft-b', '200'), 'c.csv')
        self.assertEqual(r['counts']['conflict'], 1)
        self.assertIn('REVISION_UNPARSED', self.s.history('budget_line', 'PRJ-001|CC-01')[0].payload['intrinsic']['warnings'])

    def test_order_of_revisions_does_not_change_the_final_state(self):
        revs = [('R1', '100'), ('R2', '200'), ('R3', '300')]
        finals = []
        import itertools
        for perm in itertools.permutations(revs):
            w = World(); s = w.who('a')
            for i, (r, c) in enumerate(perm):
                P.ingest_file(s, w.clock, BUD, self.bud(r, c), 'job_costing', f'b{i}.csv', D.DEMO_POLICY, 'source_revision_label')
            p = s.get('budget_line', 'PRJ-001|CC-01').payload
            finals.append((p['fields'], p['source_revision'], p['intrinsic']['outcome']))
        self.assertEqual(len(set(map(str, finals))), 1)
        self.assertEqual(finals[0][1], 3)

    def test_higher_revision_supersedes_an_open_conflict(self):
        self.go(self.bud('R1', '100')); self.go(self.bud('R1', '110'), 'c.csv')
        self.assertEqual(self.s.get('budget_line', 'PRJ-001|CC-01').payload['intrinsic']['outcome'], 'quarantined')
        r = self.go(self.bud('R2', '120'), 'd.csv')
        self.assertEqual(r['counts']['revision'], 1)
        p = self.s.get('budget_line', 'PRJ-001|CC-01').payload
        self.assertEqual((p['intrinsic']['outcome'], p['fields']['budget_cents'], p['conflict']), ('accepted', 120, None))

    def test_same_revision_same_content_is_a_duplicate_even_from_a_different_file(self):
        self.go(self.bud('R1', '100'))
        r = self.go(csvb(BUD_H + ['note'], [['PRJ-001', 'CC-01', '100', 'R1', '2026-01-01', 'again']]), 'c.csv')
        self.assertEqual(r['counts']['duplicate'], 1)

    def test_decide_table(self):
        ex = {'source_revision': 3, 'content_hash': 'h', 'conflict': None}
        T_ = [(None, 'h', 3, 'new'), (ex, 'h', 3, 'duplicate'), (ex, 'h', None, 'duplicate'), (ex, 'x', 4, 'revision'), (ex, 'x', 2, 'stale'), (ex, 'x', 3, 'conflict'), (ex, 'x', None, 'conflict'),
              (dict(ex, source_revision=None), 'x', 5, 'conflict'), (dict(ex, source_revision=None), 'h', 5, 'duplicate')]
        for e, h, r, want in T_:
            self.assertEqual(P.decide(e, h, r)[0], want, (e, h, r))


class TestTenantHandlingInFiles(unittest.TestCase):
    def test_matching_claim_stripped_foreign_claim_refuses_whole_file_and_is_audited(self):
        w = World(); s1 = w.who('a', 'zero_one'); s2 = w.who('b', 'zero_two', 'bob')
        H = INV_H + ['tenant_id']
        r = P.ingest_file(s1, w.clock, T, csvb(H, [inv() + ['zero_one']]), 'accounting', 'f.csv', D.DEMO_POLICY)
        self.assertEqual(r['stripped_scope_columns'], ['tenant_id'])
        self.assertNotIn('tenant_id', s1.get('ap_invoice', 'INV-1').payload['raw'])
        with self.assertRaises(TenantMismatch):
            P.ingest_file(s2, w.clock, T, csvb(H, [inv('INV-7') + ['zero_one']]), 'accounting', 'f.csv', D.DEMO_POLICY)
        self.assertEqual(s2.query('ap_invoice'), ())
        self.assertIsNone(s2.get('ap_invoice', 'INV-7'))
        self.assertTrue(any(e.event_type == 'tenant_claim.refused' for e in w.audit.read(s2.ctx)))
        self.assertFalse(any(e.event_type == 'tenant_claim.refused' for e in w.audit.read(s1.ctx)))        # the refusal is on the ATTACKER's log

    def test_two_tenants_ingest_the_same_ids_and_never_meet(self):
        w = World(); s1 = w.who('a', 'zero_one'); s2 = w.who('b', 'zero_two', 'bob')
        P.ingest_file(s1, w.clock, T, inv_file(inv(ex='111')), 'accounting', 'f.csv', D.DEMO_POLICY)
        P.ingest_file(s2, w.clock, T, inv_file(inv(ex='222')), 'accounting', 'f.csv', D.DEMO_POLICY)
        self.assertEqual(s1.get('ap_invoice', 'INV-1').payload['fields']['amount_ex_gst_cents'], 111)
        self.assertEqual(s2.get('ap_invoice', 'INV-1').payload['fields']['amount_ex_gst_cents'], 222)
        self.assertEqual(len(s1.query('ingest_receipt')), 1)


class TestPolicy(unittest.TestCase):
    def test_default_policy_is_strict_any_missing_optional_value_holds_the_record(self):
        w = World(); s = w.who('a')
        P.ingest_file(s, w.clock, T, inv_file(inv(gst='', po='PO-1')), 'accounting', 'f.csv')
        self.assertEqual(s.get('ap_invoice', 'INV-1').payload['intrinsic']['pending'], ['CRITICAL_VALUE_MISSING:gst_cents'])

    def test_a_material_field_can_never_be_relaxed(self):
        from apg.ingest.specs import IngestPolicy
        pol = IngestPolicy(warn_unknown={'ap_invoice': ('amount_ex_gst_cents', 'gst_cents')})
        self.assertFalse(pol.tolerates_missing('ap_invoice', 'amount_ex_gst_cents'))
        self.assertTrue(pol.tolerates_missing('ap_invoice', 'gst_cents'))

    def test_future_date_allowance_is_configuration(self):
        from apg.ingest.specs import IngestPolicy
        w = World(); s = w.who('a')
        P.ingest_file(s, w.clock, T, inv_file(inv(date='2026-10-03')), 'accounting', 'f.csv', IngestPolicy(warn_unknown=D.DEMO_POLICY.warn_unknown, future_days_allowed=5))
        self.assertEqual(s.get('ap_invoice', 'INV-1').payload['intrinsic']['pending'], [])
        P.ingest_file(s, w.clock, T, inv_file(inv('INV-2', date='2026-10-03')), 'accounting', 'g.csv', D.DEMO_POLICY)
        self.assertEqual(s.get('ap_invoice', 'INV-2').payload['intrinsic']['pending'], ['FUTURE_DATED:invoice_date'])


if __name__ == '__main__':
    unittest.main()
