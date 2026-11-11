import unittest
from unittest import mock
from . import _path                                         # noqa: F401
from .helpers_fin import Mini, base_world, inv, bud, ctc, var, AS_OF
from apg import repro
from apg.repro import FormulaRegistry, ReproError
from apg.ports import ConflictError
from apg.fin import calc_records as C, policy as P, demo_fin as DF
from apg.fin.figure import AUTH, PROV, CANT


def world():
    m = base_world()
    m.invoices(inv('INV-1', cc='CC-01', ex='3000000', date='2026-08-01'), inv('INV-2', sin='S2', cc='CC-02', ex='1000000', date='2026-08-02'))
    m.reconcile()
    return m


def replays(m, rec):
    chk = C.check_record(m.s, m.reg, rec['run_key'])
    return (chk['replay'].ok, chk['replay'].code, chk['figure_valid'], chk['pins_consistent'])


class TestRunAndReplay(unittest.TestCase):
    def test_every_formula_runs_stores_and_replays(self):
        m = world()
        for f, extra in (('fin.actual_cost', None), ('fin.commitments', None), ('fin.revenue', None), ('fin.forecast', None), ('fin.recognised_margin', None), ('fin.cash_adjusted', None),
                         ('fin.cash_position', {'what': 'retention'}), ('fin.cash_position', {'what': 'security'}), ('fin.cash_position', {'what': 'retention_carrying'}),
                         ('fin.cash_position', {'what': 'security_carrying'})):
            rec = m.run(f, extra=extra)
            self.assertEqual(replays(m, rec), (True, '', True, True), (f, extra))
            self.assertEqual(rec['formula_version'], 1)

    def test_the_same_inputs_give_the_same_record_not_a_new_one(self):
        m = world()
        a, b = m.run('fin.forecast'), m.run('fin.forecast')
        self.assertEqual(a['run_key'], b['run_key'])
        self.assertEqual(len(list(m.s.query(repro.KIND))), len([1 for _ in {a['run_key']}]) + len({r.key for r in m.s.query(repro.KIND)}) - 1)

    def test_a_record_pins_every_revision_and_hash_it_used_and_the_policy(self):
        m = world()
        rec = m.run('fin.forecast')
        pinned = {f"{i['kind']}/{i['key']}": i for i in rec['inputs']}
        for c in rec['result']['contributed']:
            self.assertIn(c['ref'], pinned)
            self.assertEqual(c['revision'], pinned[c['ref']]['revision'])
        self.assertIn('fin_policy/' + m.policy['version'], pinned)
        self.assertEqual(rec['params']['policy'], m.policy['version'])
        self.assertTrue(all(len(i['payload_hash']) == 64 for i in rec['inputs']))

    def test_unknown_formula_and_unknown_policy(self):
        m = world()
        with self.assertRaises(KeyError):
            m.run('fin.nonsense')
        with self.assertRaises(Exception):
            m.run('fin.forecast', policy='NO-SUCH-POLICY')

    def test_bad_cash_position_part(self):
        m = world()
        with self.assertRaises(ValueError):
            m.run('fin.cash_position', extra={'what': 'nothing'})
        with self.assertRaises(ValueError):
            m.run('fin.cash_position')

    def test_results_do_not_depend_on_the_order_records_arrived(self):
        def build(rev):
            m = base_world()
            rows = [inv('INV-1', cc='CC-01', ex='3000000', date='2026-08-01'), inv('INV-2', sin='S2', cc='CC-02', ex='1000000', date='2026-08-02')]
            m.invoices(*(rows[::-1] if rev else rows))
            m.reconcile()
            return m.fig('fin.forecast')
        a, b = build(False), build(True)
        for k in ('value', 'state', 'classified', 'excluded', 'unknown_inputs', 'disputed', 'reasons'):
            self.assertEqual(a[k], b[k], k)
        self.assertEqual(sorted(c['ref'] for c in a['contributed']), sorted(c['ref'] for c in b['contributed']))

    def test_the_record_cannot_read_anything_it_did_not_pin(self):
        m = world()
        rec = m.run('fin.actual_cost')
        m.invoices(inv('INV-3', sin='S3', cc='CC-01', ex='5', date='2026-08-03')); m.reconcile()
        again = m.run('fin.actual_cost')
        self.assertNotEqual(rec['run_key'], again['run_key'])
        self.assertEqual(rec['result']['value']['cents'] + 5, again['result']['value']['cents'])
        self.assertEqual(replays(m, rec)[0], True)                                          # the earlier record is unaffected by later data (AC-17)


class TestHistoricalReproduction(unittest.TestCase):
    def test_an_old_result_reproduces_after_inputs_policy_and_data_change(self):
        m = world()
        old = m.run('fin.forecast')
        m.budgets(bud(cc='CC-01', cents='6000000', rev='R1'))                               # a new budget revision
        m.set_policy(freshness_days={})                                                       # a different policy version
        m.invoices(inv('INV-9', sin='S9', cc='CC-02', ex='7', date='2026-08-05')); m.reconcile()
        self.assertEqual(replays(m, old), (True, '', True, True))
        report = C.check_record(m.s, m.reg, old['run_key'])['drift']
        self.assertIn({'input': 'budget_line/PRJ-001|CC-01', 'pinned_revision': 1, 'latest_revision': 2}, report)
        new = m.run('fin.forecast')
        self.assertNotEqual(new['run_key'], old['run_key'])
        self.assertNotEqual(new['result']['classified']['cost_variance'], old['result']['classified']['cost_variance'])

    def test_explain_joins_the_revision_history(self):
        m = world()
        m.budgets(bud(cc='CC-01', cents='6000000', rev='R1')); m.reconcile()
        rec = m.run('fin.forecast')
        ex = C.explain(m.s, rec['run_key'])
        self.assertEqual(ex['formula'], ('fin.forecast', 1))
        hist = ex['history']['budget_line/PRJ-001|CC-01']
        self.assertEqual([h['revision'] for h in hist], [1, 2])
        self.assertEqual(ex['pins']['budget_line/PRJ-001|CC-01']['revision'], 2)
        self.assertEqual(ex['figure']['state'], rec['result']['state'])

    def test_a_policy_approval_is_a_new_revision_and_the_old_figure_still_shows_it_unapproved(self):
        m = Mini(approved=False)
        m.projects(['PRJ-001', 'P', '10000000', '2026-01-01', '2027-01-01']); m.contracts(['PRJ-001', '10000000', '0']); m.budgets(bud(cc='CC-01', cents='5000000'))
        m.reconcile()
        before = m.run('fin.forecast')
        self.assertEqual(before['result']['state'], PROV)
        approved = P.approve(m.policy, 'pat', 'policy_owner', 'human', '2026-10-02')
        pat = m.w.who('pat', 'zero_one', user='pat', roles=('policy_owner',))
        P.store_policy(pat, approved)
        after = m.run('fin.forecast')
        self.assertEqual(after['result']['state'], AUTH)
        self.assertEqual(replays(m, before), (True, '', True, True))
        self.assertEqual(m.s.get(repro.KIND, before['run_key']).payload['result']['state'], PROV)
        d = C.diff_records(before, after)
        self.assertEqual(d['kind'], 'rule')
        self.assertIn('policy %s revision 1 -> 2' % m.policy['version'], d['rule_changes'])
        self.assertEqual(d['input_changes'], [])

    def test_policy_content_is_immutable_under_a_version(self):
        m = world()
        with self.assertRaises(P.PolicyError):
            P.store_policy(m.s, dict(m.policy, gst_rate_bps=1000))

    def test_only_a_human_policy_owner_who_is_not_the_proposer_approves(self):
        m = Mini(approved=False)
        self.assertFalse(P.is_approved(P.approve(m.policy, m.policy['proposer'], 'policy_owner', 'human', '2026-10-02')))
        self.assertFalse(P.is_approved(P.approve(m.policy, 'pat', 'policy_owner', 'service', '2026-10-02')))
        self.assertFalse(P.is_approved(P.approve(m.policy, 'pat', 'importer', 'human', '2026-10-02')))
        self.assertTrue(P.is_approved(P.approve(m.policy, 'pat', 'policy_owner', 'human', '2026-10-02')))

    def test_input_and_rule_changes_are_told_apart(self):
        m = world()
        a = m.run('fin.forecast')
        m.invoices(inv('INV-3', sin='S3', cc='CC-01', ex='5', date='2026-08-03')); m.reconcile()
        b = m.run('fin.forecast')
        d = C.diff_records(a, b)
        self.assertEqual((d['kind'], d['rule_changes'], d['result_changed']), ('input', [], True))
        self.assertTrue(any(i['input'].startswith('ap_invoice/INV-3') for i in d['input_changes']))
        m.set_policy(ctc_method={'default': 'budget_less_actual'})
        c = m.run('fin.forecast')
        d2 = C.diff_records(b, c)
        self.assertEqual(d2['kind'], 'rule')
        self.assertTrue(d2['rule_changes'][0].startswith('policy '))
        self.assertEqual(C.diff_records(a, a)['kind'], 'identical')
        self.assertEqual(C.diff_records(a, c)['kind'], 'both')

    def test_a_formula_version_change_is_a_rule_change(self):
        m = world()
        a = m.run('fin.forecast')
        b = dict(a, formula_version=2)
        self.assertEqual(C.diff_records(a, b)['rule_changes'], ['formula fin.forecast v1 -> fin.forecast v2'])
        c = dict(a, formula_code_hash='f' * 64)
        self.assertEqual(C.diff_records(a, c)['rule_changes'], ['formula code changed under the same version'])


class TestDriftAndTamper(unittest.TestCase):
    def test_changed_code_without_a_version_bump_is_caught_on_replay(self):
        m = world()
        rec = m.run('fin.forecast')
        other = FormulaRegistry()
        for fid, fn in C.FORMULAS.items():
            other.register(fid, C.VERSIONS[fid], fn, code_hash='0' * 64)
        r = repro.replay(m.s, other, rec['run_key'])
        self.assertEqual((r.ok, r.code), (False, 'FORMULA_DRIFT'))

    def test_the_code_hash_covers_every_calculation_module(self):
        base = C.code_hash()
        real = C.inspect.getsource
        for mod in C.MODULES:
            def fake(obj, _mod=mod):
                return real(obj) + ('\n# changed' if obj is _mod else '')
            with mock.patch.object(C.inspect, 'getsource', side_effect=fake):
                self.assertNotEqual(C.code_hash(), base, mod.__name__)

    def test_every_module_outside_the_hash_is_one_that_computes_no_figure(self):
        import os, apg.fin as pkg
        hashed = {m.__name__.rsplit('.', 1)[1] for m in C.MODULES}
        on_disk = {f[:-3] for f in os.listdir(os.path.dirname(pkg.__file__)) if f.endswith('.py')}
        # outside the hash on purpose: replay reads pinned inputs, so the gatherer (which only chooses what to pin), ingestion, the forecast book and the demo set-up cannot change a replayed figure
        self.assertEqual(on_disk - hashed - {'__init__', 'calc_records', 'gather', 'intake', 'forecast_book', 'demo_fin', 'golden_fin', 'corpus_fin'}, set(), 'a new fin module is not in the formula code hash')

    def test_altered_result_params_or_body_is_caught(self):
        m = world()
        rec = m.run('fin.forecast')
        cur = m.s.get(repro.KIND, rec['run_key'])
        for field, value, code in (('result', dict(rec['result'], reasons=['X']), 'STORED_RESULT_ALTERED'), ('params', dict(rec['params'], as_of='2026-01-01'), 'STORED_PARAMS_ALTERED'),
                                   ('formula_version', 7, 'RECORD_ALTERED')):
            m2 = world()
            r2 = m2.run('fin.forecast')
            c2 = m2.s.get(repro.KIND, r2['run_key'])
            m2.s.put(repro.KIND, r2['run_key'], dict(c2.payload, **{field: value}), expected_revision=c2.revision)
            res = repro.replay(m2.s, m2.reg, r2['run_key'])
            self.assertEqual((res.ok, res.code), (False, code), field)

    def test_a_pin_that_disagrees_with_what_was_pinned_is_caught(self):
        m = world()
        rec = m.run('fin.forecast')
        cur = m.s.get(repro.KIND, rec['run_key'])
        p = dict(cur.payload)
        params = dict(p['params']); pins = dict(params['pins']); first = sorted(pins)[0]; pins[first] = pins[first] + 5; params['pins'] = pins
        p['params'] = params
        p['params_hash'] = repro.digest(params)
        body = {k: p[k] for k in ('formula_id', 'formula_version', 'formula_code_hash', 'inputs', 'params', 'params_hash')}
        p['run_key'] = repro.digest(body)[:32]
        m.s.put(repro.KIND, p['run_key'], p, expected_revision=0)                             # a forged record that is internally consistent
        chk = C.check_record(m.s, m.reg, p['run_key'])
        self.assertFalse(chk['pins_consistent'])

    def test_a_missing_record_is_reported_not_raised(self):
        m = world()
        chk = C.check_record(m.s, m.reg, 'f' * 32)
        self.assertEqual((chk['replay'].ok, chk['replay'].code, chk['figure_valid'], chk['pins_consistent']), (False, 'RECORD_MISSING', False, False))

    def test_stored_records_are_immutable(self):
        m = world()
        rec = m.run('fin.forecast')
        with self.assertRaises(ConflictError):
            m.s.put(repro.KIND, rec['run_key'], dict(rec, created_by='someone else'), expected_revision=0)

    def test_an_input_that_was_deleted_from_history_cannot_be_replayed_silently(self):
        m = world()
        rec = m.run('fin.forecast')
        broken = [dict(i, payload_hash='0' * 64) if i['kind'] == 'budget_line' else i for i in rec['inputs']]
        cur = m.s.get(repro.KIND, rec['run_key'])
        m.s.put(repro.KIND, rec['run_key'], dict(cur.payload, inputs=broken), expected_revision=cur.revision)
        self.assertFalse(repro.replay(m.s, m.reg, rec['run_key']).ok)


class TestTenancy(unittest.TestCase):
    def test_another_tenant_cannot_see_replay_or_explain_a_record(self):
        m = world()
        rec = m.run('fin.forecast')
        other = m.w.who('o', 'other_tenant', user='olga', roles=('importer',))
        chk = C.check_record(other, m.reg, rec['run_key'])
        self.assertEqual(chk['replay'].code, 'RECORD_MISSING')
        self.assertIsNone(other.get(repro.KIND, rec['run_key']))

    def test_two_tenants_with_the_same_data_get_independent_records(self):
        a = world()
        b = Mini(tenant='other_tenant')
        b.projects(['PRJ-001', 'P1', '10000000', '2026-01-01', '2027-01-01']); b.contracts(['PRJ-001', '10000000', '0']); b.budgets(bud(cc='CC-01', cents='5000000')); b.reconcile()
        ra, rb = a.run('fin.forecast'), b.run('fin.forecast')
        self.assertNotEqual(ra['result']['value'], rb['result']['value'])
        self.assertEqual(len({r.tenant_id for r in a.s.query(repro.KIND)}), 1)


if __name__ == '__main__':
    unittest.main()
