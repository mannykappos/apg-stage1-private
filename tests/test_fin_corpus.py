import unittest
from . import _path                                          # noqa: F401
from ._path import HERE_ROOT
from apg.fin import corpus_fin as K


class FinCorpus(unittest.TestCase):
    def test_every_faulty_input_case_gives_the_required_figure(self):
        failed = []
        for case in K.cases():
            ok, msg = K.check_case(case, lambda approved: K.ReferenceWorld(HERE_ROOT, approved=approved))
            if not ok:
                failed.append(f'{case["id"]} {case["desc"]}: {msg}')
        self.assertEqual(failed, [])

    def test_case_ids_are_unique_and_every_case_states_a_state(self):
        ids = [c['id'] for c in K.cases()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(c['expect'].get('state') in ('authoritative', 'provisional', 'cannot_assess') for c in K.cases()))
        self.assertEqual(len(ids), 63, 'the corpus holds 63 faulty-input cases; adding or dropping one is a deliberate change to this number')

    def test_a_wrong_expectation_is_reported_not_passed(self):
        case = dict(K.cases()[0], expect={'state': 'cannot_assess'})
        ok, msg = K.check_case(case, lambda approved: K.ReferenceWorld(HERE_ROOT, approved=approved))
        self.assertFalse(ok)
        case = dict(K.cases()[0], expect={'state': 'authoritative', 'cents': 1})
        self.assertFalse(K.check_case(case, lambda approved: K.ReferenceWorld(HERE_ROOT, approved=approved))[0])
        case = dict(K.cases()[0], expect={'state': 'authoritative', 'reasons_has': ['NOT_THERE']})
        self.assertFalse(K.check_case(case, lambda approved: K.ReferenceWorld(HERE_ROOT, approved=approved))[0])

    def test_the_corpus_covers_every_open_decision_field_the_policy_names(self):
        named = {c['id'][2:] for c in K.cases() if c['id'].startswith('P_')}
        from apg.fin import policy as P
        self.assertEqual(set(P.OPEN_DECISIONS) - named, {'credit_reopens_commitment'})       # that one is exercised by C08, where it matters (a credit against an order-linked invoice)


if __name__ == '__main__':
    unittest.main()
