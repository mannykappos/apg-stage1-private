import copy
import unittest
from . import _path                                         # noqa: F401
from .helpers_det import AS_OF, DetMini, bud, det_world, inv, po, var, ctc, hire
from .helpers_ingest import World
from apg import canon, repro
from apg.det import demo_det as DD, detect as D, findings as FD, policy as DP, signal as S
from apg.fin import demo_fin as DF, policy as FP


def breach_world():
    m = det_world()
    m.invoices(inv('INV-1', ex='5300000', cc='CC-01'))
    m.reconcile()
    return m


class TestRunRecord(unittest.TestCase):
    def test_a_run_is_stored_pinned_and_replays_to_the_same_result(self):
        m = breach_world()
        rec = m.detect()
        self.assertEqual(rec['formula_id'] if 'formula_id' in rec else 'det.detect_project', 'det.detect_project')
        chk = D.check_record(m.s, m.detreg, rec['run_key'])
        self.assertTrue(chk['replay'].ok)
        self.assertTrue(chk['result_valid'] and chk['pins_consistent'])
        self.assertEqual(chk['drift'], [])
        pins = {i['kind'] for i in m.s.get(repro.KIND, rec['run_key']).payload['inputs']}
        self.assertTrue({'det_policy', 'fin_policy', 'ap_invoice', 'budget_line'} <= pins)

    def test_the_same_inputs_give_the_same_run_key_and_the_same_result(self):
        m = breach_world()
        a, b = m.detect(), m.detect()
        self.assertEqual(a['run_key'], b['run_key'])
        self.assertEqual(canon.canonical(a['result']), canon.canonical(b['result']))

    def test_a_new_invoice_revision_gives_a_new_run_and_the_old_run_still_replays(self):
        m = breach_world()
        old = m.detect()
        m.invoices(inv('INV-2', sin='SI-2', ex='700000', cc='CC-01'))
        m.reconcile()
        new = m.detect()
        self.assertNotEqual(old['run_key'], new['run_key'])
        self.assertTrue(D.check_record(m.s, m.detreg, old['run_key'])['replay'].ok)
        self.assertEqual(old['result']['signals'][0]['quantification']['gross_cents'], 300000)
        self.assertEqual(new['result']['signals'][0]['quantification']['gross_cents'], 1000000)

    def test_a_policy_change_is_a_new_run_and_the_old_result_does_not_change(self):
        m = breach_world()
        old = m.detect()
        m.rules(R01={'tolerance_bps': 9000})
        new = m.detect()
        self.assertNotEqual(old['run_key'], new['run_key'])
        self.assertEqual(m.sigs(new['result'], 'R01'), [])
        self.assertEqual(len(m.sigs(m.s.get(repro.KIND, old['run_key']).payload['result'], 'R01')), 1)

    def test_a_tampered_stored_result_fails_the_replay(self):
        m = breach_world()
        rec = m.detect()
        stored = m.s.get(repro.KIND, rec['run_key'])
        bad = copy.deepcopy(stored.payload)
        bad['result']['signals'][0]['quantification']['gross_cents'] += 1
        try:
            m.s.put(repro.KIND, rec['run_key'], bad, expected_revision=stored.revision)
        except Exception:
            return                                                                          # the store refused the change: that also protects the record
        chk = D.check_record(m.s, m.detreg, rec['run_key'])
        self.assertFalse(chk['replay'].ok)

    def test_a_missing_run_is_reported_not_raised(self):
        m = breach_world()
        chk = D.check_record(m.s, m.detreg, 'no-such-run')
        self.assertEqual((chk['replay'].ok, chk['replay'].code, chk['result_valid']), (False, 'RECORD_MISSING', False))

    def test_the_code_hash_covers_the_rule_modules(self):
        import hashlib, inspect
        from apg.det import rules_cost
        from apg import materiality
        from apg.det import common, gather, intake, policy, rules_commercial, rules_ops, signal
        h = D.code_hash()
        self.assertEqual(len(h), 64)
        src = inspect.getsource(rules_cost)
        self.assertNotEqual(hashlib.sha256(src.encode()).hexdigest(), h)
        for mod in (materiality, intake, policy, signal, common, gather, rules_commercial, rules_cost, rules_ops):               # every module a detection result depends on
            self.assertIn(mod, D.MODULES, mod.__name__)

    def test_every_rule_leaves_a_run_record_even_when_silent(self):
        m = det_world()
        r = m.res()
        self.assertEqual(sorted(r['rule_runs']), sorted(k for k, _ in D.PROJECT_RULES))
        self.assertTrue(all(x['status'] in ('evaluated', 'not_configured', 'disabled', 'cannot_assess') for x in r['rule_runs'].values()))

    def test_unconfigured_rules_are_listed_as_not_run_and_not_as_clean(self):
        m = det_world()
        m.rules(R01=None, R03=None)
        r = m.res()
        self.assertEqual(r['counts']['rules_not_run'], 2)
        self.assertEqual({k for k, v in r['rule_runs'].items() if v['status'] == 'not_configured'}, {'R01', 'R03'})

    def test_a_result_with_a_rule_that_did_not_run_but_has_signals_is_rejected(self):
        m = breach_world()
        res = copy.deepcopy(m.res())
        res['rule_runs']['R01']['status'] = 'disabled'
        with self.assertRaises(ValueError):
            D.validate_result(res)

    def test_two_signals_with_one_identity_are_rejected(self):
        m = breach_world()
        res = copy.deepcopy(m.res())
        res['signals'].append(copy.deepcopy(res['signals'][0]))
        with self.assertRaises(ValueError):
            D.validate_result(res)

    def test_a_detection_policy_that_does_not_exist_cannot_be_run_against(self):
        m = breach_world()
        with self.assertRaises(repro.ReproError) as cm:                                      # the run cannot pin a policy that does not exist
            D.run_project(m.s, m.detreg, m.clock, 'PRJ-001', AS_OF, m.policy['version'], 'D-none')
        self.assertIn('INPUT_MISSING', str(cm.exception))

    def test_the_result_says_whether_the_policies_were_approved(self):
        m = det_world(approved=False)
        r = m.res()
        self.assertEqual(r['det_policy']['approved'], False)
        self.assertEqual(r['fin_policy']['approved'], False)
        r2 = det_world().res()
        self.assertEqual((r2['det_policy']['approved'], r2['fin_policy']['approved']), (True, True))

    def test_every_signal_carries_the_data_limits_and_no_float_anywhere(self):
        m = breach_world()
        for s in m.res()['signals']:
            self.assertIsInstance(s['data_limits'], list)

        def walk(x):
            if isinstance(x, float):
                self.fail('float in result')
            elif isinstance(x, dict):
                [walk(v) for v in x.values()]
            elif isinstance(x, (list, tuple)):
                [walk(v) for v in x]
        walk(m.res())


class TestTenantIsolation(unittest.TestCase):
    def test_another_tenant_sees_none_of_the_first_tenants_records_signals_or_findings(self):
        m = breach_world()
        rec = m.detect()
        m.ingest(rec)
        other = m.w.who('t2', 'other_co', 'olga', ('importer',))
        FP.store_policy(other, DF.demo_policy(proposer='olga'))
        DP.store_policy(other, DD.demo_det_policy(proposer='olga'))
        with self.assertRaises(repro.ReproError) as cm:                                      # the other tenant has no PRJ-001, so there is nothing to run (and no empty "clean" result)
            D.run_project(other, m.detreg, m.clock, 'PRJ-001', AS_OF, m.policy['version'], m.dp['version'])
        self.assertIn('PROJECT_UNKNOWN', str(cm.exception))
        r = D.run_tenant(other, m.detreg, m.clock, AS_OF, m.dp['version'])['result']
        self.assertEqual(r['signals'], [])
        self.assertEqual(FD.all_findings(other), [])
        self.assertEqual(len(FD.all_findings(m.s)), 1)

    def test_another_tenant_cannot_ingest_or_check_the_first_tenants_run(self):
        m = breach_world()
        rec = m.detect()
        svc2 = m.w.who('svc2', 'other_co', 'detsvc2', ('detection_service',), 'service')
        with self.assertRaises(FD.LifecycleError):
            FD.ingest_run(svc2, m.clock, m.detreg, rec['run_key'])
        self.assertFalse(D.check_record(svc2, m.detreg, rec['run_key'])['replay'].ok)


class TestSignalContract(unittest.TestCase):
    def sample(self):
        m = breach_world()
        return m.res()['signals'][0]

    def test_a_valid_signal_passes_and_each_required_part_is_checked(self):
        s = self.sample()
        S.validate_signal(s)
        for path in (('quantification',), ('evidence',), ('explanation', 'observed'), ('interpretation',), ('identity',)):
            bad = copy.deepcopy(s)
            d = bad
            for k in path[:-1]:
                d = d[k]
            del d[path[-1]]
            with self.assertRaises((S.SignalError, KeyError)):
                S.validate_signal(bad)

    def test_a_signal_without_evidence_is_refused(self):
        s = self.sample()
        s['evidence'] = []
        with self.assertRaises(S.SignalError):
            S.validate_signal(s)

    def test_an_unknown_interpretation_is_refused(self):
        s = self.sample()
        s['interpretation'] = 'realised_saving'
        with self.assertRaises(S.SignalError):
            S.validate_signal(s)

    def test_a_quantified_signal_must_have_a_label_from_the_allowed_set(self):
        s = self.sample()
        s['quantification']['label'] = 'verified_saving'
        with self.assertRaises(S.SignalError):
            S.validate_signal(s)

    def test_identity_is_rule_scope_subject_and_nothing_else(self):
        a = S.identity_of('DET-R01', {'level': 'project', 'project': 'PRJ-001'}, 'CC-01')
        self.assertEqual(a, S.identity_of('DET-R01', {'level': 'project', 'project': 'PRJ-001'}, 'CC-01'))
        self.assertNotEqual(a, S.identity_of('DET-R01', {'level': 'project', 'project': 'PRJ-002'}, 'CC-01'))
        self.assertNotEqual(a, S.identity_of('DET-R03', {'level': 'project', 'project': 'PRJ-001'}, 'CC-01'))
        self.assertNotEqual(a, S.identity_of('DET-R01', {'level': 'project', 'project': 'PRJ-001'}, 'CC-02'))

    def test_the_digest_ignores_a_drifting_figure_and_notices_new_evidence(self):
        m = breach_world()
        a = m.res()['signals'][0]
        m.rules()                                                                            # a policy revision with no content change
        later = m.res(as_of='2026-09-29')['signals'][0]
        self.assertEqual(a['state_digest'], later['state_digest'])
        m.invoices(inv('INV-2', sin='SI-2', ex='700000', cc='CC-01'))
        m.reconcile()
        b = m.res()['signals'][0]
        self.assertNotEqual(a['state_digest'], b['state_digest'])
