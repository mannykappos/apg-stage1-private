import unittest
from . import _path                                          # noqa: F401
from apg import repro as R
from apg.tenancy import ScopedStore
from .helpers import make_env, login


def total_formula(inputs, params):
    inv = inputs['invoice/I1']
    return {'total_cents': sum(l['cents'] for l in inv['lines']) + params.get('adj', 0)}


class Base(unittest.TestCase):
    def setUp(self):
        self.env, self.clock = make_env()
        self.ctx = login(self.env, 'ta', 'ten-a')
        self.sc = ScopedStore(self.env.store, self.env.audit, self.ctx)
        self.sc.put('invoice', 'I1', {'lines': [{'cents': 1000}, {'cents': 250}]})
        self.reg = R.FormulaRegistry(); self.reg.register('total', 1, total_formula)

    def code(self, fn):
        try:
            fn()
        except R.ReproError as e:
            return e.code


class RunReplay(Base):
    def test_run_pins_revision_and_hash_and_replays(self):
        ref = R.pin_latest(self.sc, 'invoice', 'I1'); self.assertEqual(ref.revision, 1)
        rec = R.run(self.sc, self.reg, self.clock, 'total', 1, [ref], {'adj': 5})
        self.assertEqual(rec['result'], {'total_cents': 1255}); self.assertEqual(rec['inputs'][0]['revision'], 1); self.assertEqual(rec['created_by'], 'u1')
        self.assertEqual(rec['created_at'], self.clock.now()); self.assertEqual(rec['formula_version'], 1)
        self.assertTrue(R.replay(self.sc, self.reg, rec['run_key']).ok); self.assertEqual(R.drift_report(self.sc, rec['run_key']), [])

    def test_identical_run_is_idempotent_one_record(self):
        ref = R.pin_latest(self.sc, 'invoice', 'I1')
        a = R.run(self.sc, self.reg, self.clock, 'total', 1, [ref]); self.clock.advance(60); b = R.run(self.sc, self.reg, self.clock, 'total', 1, [ref])
        self.assertEqual(a['run_key'], b['run_key']); self.assertEqual(len(self.sc.history(R.KIND, a['run_key'])), 1)

    def test_params_change_changes_run_key(self):
        ref = R.pin_latest(self.sc, 'invoice', 'I1')
        a = R.run(self.sc, self.reg, self.clock, 'total', 1, [ref], {'adj': 1}); b = R.run(self.sc, self.reg, self.clock, 'total', 1, [ref], {'adj': 2})
        self.assertNotEqual(a['run_key'], b['run_key'])

    def test_audit_event_written(self):
        ref = R.pin_latest(self.sc, 'invoice', 'I1'); R.run(self.sc, self.reg, self.clock, 'total', 1, [ref])
        self.assertIn('repro.run', [e.event_type for e in self.env.audit.read(self.ctx)])


class NoSilentDrift(Base):
    def test_new_input_revision_does_not_change_old_calculation(self):
        ref = R.pin_latest(self.sc, 'invoice', 'I1'); rec = R.run(self.sc, self.reg, self.clock, 'total', 1, [ref])
        self.sc.put('invoice', 'I1', {'lines': [{'cents': 9999}]})
        self.assertTrue(R.replay(self.sc, self.reg, rec['run_key']).ok)
        self.assertEqual(R.drift_report(self.sc, rec['run_key']), [{'input': 'invoice/I1', 'pinned_revision': 1, 'latest_revision': 2}])

    def test_pinning_an_old_revision_gives_old_numbers(self):
        self.sc.put('invoice', 'I1', {'lines': [{'cents': 7}]})
        old = R.InputRef('invoice', 'I1', 1, self.sc.get('invoice', 'I1', 1).payload_hash)
        self.assertEqual(R.run(self.sc, self.reg, self.clock, 'total', 1, [old])['result'], {'total_cents': 1250})

    def test_formula_code_change_under_same_version_is_refused_at_registration(self):
        def total_formula2(inputs, params): return {'total_cents': 0}
        self.assertEqual(self.code(lambda: self.reg.register('total', 1, total_formula2)), 'FORMULA_VERSION_REUSED')
        self.reg.register('total', 2, total_formula2)

    def test_replay_detects_formula_drift(self):
        ref = R.pin_latest(self.sc, 'invoice', 'I1'); rec = R.run(self.sc, self.reg, self.clock, 'total', 1, [ref])
        reg2 = R.FormulaRegistry(); reg2.register('total', 1, lambda i, p: {'total_cents': 1})
        r = R.replay(self.sc, reg2, rec['run_key']); self.assertEqual((r.ok, r.code), (False, 'FORMULA_DRIFT'))

    def test_replay_unknown_formula(self):
        ref = R.pin_latest(self.sc, 'invoice', 'I1'); rec = R.run(self.sc, self.reg, self.clock, 'total', 1, [ref])
        self.assertEqual(R.replay(self.sc, R.FormulaRegistry(), rec['run_key']).code, 'FORMULA_UNKNOWN')


class Tamper(Base):
    def _run(self):
        return R.run(self.sc, self.reg, self.clock, 'total', 1, [R.pin_latest(self.sc, 'invoice', 'I1')], {'adj': 5})

    def test_altered_result_is_detected(self):
        rec = self._run(); self.sc.put(R.KIND, rec['run_key'], dict(rec, result={'total_cents': 1}))
        self.assertEqual(R.replay(self.sc, self.reg, rec['run_key']).code, 'STORED_RESULT_ALTERED')

    def test_altered_result_and_hash_together_is_detected_by_replay(self):
        from apg.canon import digest
        rec = self._run(); fake = {'total_cents': 1}; self.sc.put(R.KIND, rec['run_key'], dict(rec, result=fake, result_hash=digest(fake)))
        self.assertEqual(R.replay(self.sc, self.reg, rec['run_key']).code, 'RESULT_DIFFERS')

    def test_altered_params_detected(self):
        rec = self._run(); self.sc.put(R.KIND, rec['run_key'], dict(rec, params={'adj': 0}))
        self.assertEqual(R.replay(self.sc, self.reg, rec['run_key']).code, 'STORED_PARAMS_ALTERED')

    def test_altered_input_pin_detected(self):
        from apg.canon import digest
        rec = self._run(); ins = [dict(rec['inputs'][0], revision=2)]
        self.sc.put(R.KIND, rec['run_key'], dict(rec, inputs=ins))
        self.assertEqual(R.replay(self.sc, self.reg, rec['run_key']).code, 'RECORD_ALTERED')

    def test_pinned_input_content_changed_in_store_is_detected(self):
        rec = self._run()
        # a pin whose hash does not match what the store holds for that revision is refused
        bad = R.InputRef('invoice', 'I1', 1, 'f' * 64)
        self.assertEqual(self.code(lambda: R.run(self.sc, self.reg, self.clock, 'total', 1, [bad])), 'INPUT_HASH_MISMATCH')

    def test_run_key_mismatch_when_record_copied_to_another_key(self):
        rec = self._run(); self.sc.put(R.KIND, 'copy', dict(rec))
        self.assertEqual(R.replay(self.sc, self.reg, 'copy').code, 'RECORD_ALTERED')


class Refusals(Base):
    def test_missing_input_and_missing_revision(self):
        self.assertEqual(self.code(lambda: R.pin_latest(self.sc, 'invoice', 'NOPE')), 'INPUT_MISSING')
        self.assertEqual(self.code(lambda: R.run(self.sc, self.reg, self.clock, 'total', 1, [R.InputRef('invoice', 'I1', 9, 'a' * 64)])), 'INPUT_REVISION_MISSING')

    def test_no_inputs_duplicate_inputs_unknown_formula(self):
        ref = R.pin_latest(self.sc, 'invoice', 'I1')
        self.assertEqual(self.code(lambda: R.run(self.sc, self.reg, self.clock, 'total', 1, [])), 'NO_INPUTS')
        self.assertEqual(self.code(lambda: R.run(self.sc, self.reg, self.clock, 'total', 1, [ref, ref])), 'DUPLICATE_INPUT')
        self.assertEqual(self.code(lambda: R.run(self.sc, self.reg, self.clock, 'nope', 1, [ref])), 'FORMULA_UNKNOWN')

    def test_nondeterministic_formula_is_refused(self):
        import itertools
        c = itertools.count()
        reg = R.FormulaRegistry(); reg.register('rnd', 1, lambda i, p: {'n': next(c)})
        self.assertEqual(self.code(lambda: R.run(self.sc, reg, self.clock, 'rnd', 1, [R.pin_latest(self.sc, 'invoice', 'I1')])), 'NONDETERMINISTIC')

    def test_float_result_is_refused(self):
        reg = R.FormulaRegistry(); reg.register('fl', 1, lambda i, p: {'x': 1.5})
        self.assertEqual(self.code(lambda: R.run(self.sc, reg, self.clock, 'fl', 1, [R.pin_latest(self.sc, 'invoice', 'I1')])), 'RESULT_NOT_CANONICAL')

    def test_formula_cannot_modify_stored_input(self):
        def evil(i, p):
            n = len(i['invoice/I1']['lines']); i['invoice/I1']['lines'].clear(); return {'n': n}
        reg = R.FormulaRegistry(); reg.register('evil', 1, evil)
        R.run(self.sc, reg, self.clock, 'evil', 1, [R.pin_latest(self.sc, 'invoice', 'I1')])
        self.assertEqual(len(self.sc.get('invoice', 'I1').payload['lines']), 2)

    def test_a_store_that_lies_about_a_hash_is_caught(self):
        ref = R.pin_latest(self.sc, 'invoice', 'I1')
        class Liar:
            def __init__(self, inner): self.inner, self.ctx = inner, inner.ctx
            def get(self, kind, key, revision=None):
                r = self.inner.get(kind, key, revision)
                return r if r is None or kind != 'invoice' else type(r)(r.tenant_id, r.kind, r.key, r.revision, {'lines': [{'cents': 1}]}, r.payload_hash)
        self.assertEqual(self.code(lambda: R.run(Liar(self.sc), self.reg, self.clock, 'total', 1, [ref])), 'INPUT_HASH_MISMATCH')

    def test_bad_formula_version(self):
        for v in (0, -1, 'x', True, None):
            self.assertEqual(self.code(lambda x=v: R.FormulaRegistry().register('f', x, lambda i, p: {})), 'BAD_FORMULA_ID')


class TenantIsolation(Base):
    def test_other_tenant_cannot_replay_or_see_record(self):
        rec = R.run(self.sc, self.reg, self.clock, 'total', 1, [R.pin_latest(self.sc, 'invoice', 'I1')])
        b = ScopedStore(self.env.store, self.env.audit, login(self.env, 'tb', 'ten-b'))
        self.assertEqual(R.replay(b, self.reg, rec['run_key']).code, 'RECORD_MISSING')
        self.assertEqual(self.code(lambda: R.pin_latest(b, 'invoice', 'I1')), 'INPUT_MISSING')


if __name__ == '__main__':
    unittest.main()
