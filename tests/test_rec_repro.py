"""M7: reproducibility and reconstruction of historical rankings (Section 10 section 10; Section 05 section 13; PG-RS-AC-12)."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_rec import RecWorld
from apg import canon, repro
from apg.rec import engine as E, inputs as IN, lifecycle as L


class TestRepro(unittest.TestCase):
    def setUp(self):
        self.w = RecWorld()
        self.a = self.w.finding(gross=500000)
        self.b = self.w.finding(gross=900000, strength='weak')

    def test_a_run_replays_from_its_pinned_inputs_and_the_same_inputs_give_the_same_run(self):
        r1 = self.w.run(ingest=False)
        self.assertTrue(repro.replay(self.w.s, self.w.reg, r1['run_key']).ok)
        r2 = self.w.run(ingest=False)
        self.assertEqual(r1['run_key'], r2['run_key'])
        chk = E.check_record(self.w.s, self.w.reg, r1['run_key'])
        self.assertTrue(chk['replay'].ok and chk['pins_consistent'] and chk['is_rec_run'])

    def test_every_finding_input_and_the_policy_are_pinned_at_the_revision_read(self):
        IN.set_inputs(self.w.owner, self.w.clock, self.w.rid(self.a), action_kind='internal_review')
        r = self.w.run(ingest=False)
        pinned = {(i['kind'], i['key']): i['revision'] for i in r['inputs']}
        self.assertEqual(pinned[('rec_policy', self.w.policy['version'])], self.w.s.get('rec_policy', self.w.policy['version']).revision)   # M7.1: the approval is a later revision
        self.assertIn(('rec_input', self.w.rid(self.a)), pinned)
        self.assertEqual(pinned[('finding', self.a)], self.w.s.get('finding', self.a).revision)

    def test_a_tampered_stored_result_is_detected(self):
        r = self.w.run(ingest=False)
        rec = self.w.s.get(repro.KIND, r['run_key'])
        p = canon.deep_copy(rec.payload)
        p['result']['recommendations'][0]['rank'] = 99
        self.w.s.put(repro.KIND, r['run_key'], p, expected_revision=rec.revision)
        self.assertEqual(repro.replay(self.w.s, self.w.reg, r['run_key']).code, 'STORED_RESULT_ALTERED')

    def test_a_later_change_to_an_input_never_changes_an_old_run(self):
        r1 = self.w.run(ingest=False)
        IN.set_inputs(self.w.owner, self.w.clock, self.w.rid(self.a), expected_benefit={'cents': 1, 'basis': 'b'})
        r2 = self.w.run(ingest=False)
        self.assertNotEqual(r1['run_key'], r2['run_key'])
        self.assertTrue(repro.replay(self.w.s, self.w.reg, r1['run_key']).ok)
        self.assertEqual(self.w.entry(r1, self.a)['dimensions']['expected_benefit']['cents'], None)
        self.assertEqual(self.w.entry(r2, self.a)['dimensions']['expected_benefit']['cents'], 1)

    def test_a_past_version_is_reconstructed_with_its_rank_and_values(self):
        self.w.run()
        IN.set_inputs(self.w.owner, self.w.clock, self.w.rid(self.a), expected_benefit={'cents': 700000, 'basis': 'b'}, incremental_costs=[{'component': 'c', 'cents': 0, 'basis': 'none'}])
        self.w.run(as_of='2026-10-01')
        r = L.get(self.w.s, self.w.rid(self.a))
        self.assertEqual(r['version'], 2)
        v1 = L.reconstruct(self.w.s, self.w.reg, self.w.rid(self.a), 1)
        v2 = L.reconstruct(self.w.s, self.w.reg, self.w.rid(self.a), 2)
        self.assertTrue(v1['replay_ok'] and v1['matches_recorded_digest'] and v2['replay_ok'] and v2['matches_recorded_digest'])
        self.assertEqual((v1['entry']['dimensions']['net_benefit']['cents'], v2['entry']['dimensions']['net_benefit']['cents']), (None, 700000))
        self.assertEqual(v1['rank_order'], self.w.policy['rank_order'])
        with self.assertRaises(L.RecError):
            L.reconstruct(self.w.s, self.w.reg, self.w.rid(self.a), 3)

    def test_the_same_formula_version_cannot_mean_different_code(self):
        reg = E.registry()
        with self.assertRaises(repro.ReproError) as cm:
            reg.register(E.FORMULA_ID, E.FORMULA_VERSION, lambda i, p: {}, 'different-code-hash')
        self.assertEqual(cm.exception.code, 'FORMULA_VERSION_REUSED')

    def test_the_code_hash_covers_the_rule_modules(self):
        import inspect
        from apg.rec import policy as RP
        self.assertIn(RP, E.MODULES)
        self.assertIn(IN, E.MODULES)
        self.assertEqual(len(E.code_hash()), 64)
        self.assertTrue(inspect.getsource(E.compute))

    def test_the_formula_is_deterministic_on_its_own_inputs(self):
        r = self.w.run(ingest=False)
        rec = self.w.s.get(repro.KIND, r['run_key']).payload
        inputs = {f"{i['kind']}/{i['key']}": self.w.s.get(i['kind'], i['key'], i['revision']).payload for i in rec['inputs']}
        self.assertEqual(canon.digest(E.compute(inputs, rec['params'])), canon.digest(E.compute(canon.deep_copy(inputs), canon.deep_copy(rec['params']))))
        self.assertEqual(canon.digest(E.compute(inputs, rec['params'])), rec['result_hash'])

    def test_bad_parameters_fail_closed(self):
        r = self.w.run(ingest=False)
        rec = self.w.s.get(repro.KIND, r['run_key']).payload
        inputs = {f"{i['kind']}/{i['key']}": self.w.s.get(i['kind'], i['key'], i['revision']).payload for i in rec['inputs']}
        for bad in (dict(rec['params'], as_of='2026-13-01'), dict(rec['params'], policy='missing')):
            with self.assertRaises((ValueError, E.EngineError)):
                E.compute(inputs, bad)
        broken = dict(inputs)
        broken['rec_policy/' + self.w.policy['version']] = dict(broken['rec_policy/' + self.w.policy['version']], rank_order=['score'])
        with self.assertRaises(E.EngineError) as cm:
            E.compute(broken, rec['params'])
        self.assertEqual(cm.exception.code, 'POLICY_INVALID')


if __name__ == '__main__':
    unittest.main()
