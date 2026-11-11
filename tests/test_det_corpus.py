import unittest
from . import _path                                          # noqa: F401
from ._path import HERE_ROOT
from apg.det import corpus_det as K


def world(approved):
    return K.ReferenceWorld(HERE_ROOT, approved=approved)


class DetCorpus(unittest.TestCase):
    def test_every_faulty_or_borderline_input_case_gives_the_required_result(self):
        failed = []
        for case in K.cases():
            ok, msg = K.check_case(case, world)
            if not ok:
                failed.append(f'{case["id"]} {case["desc"]}: {msg}')
        self.assertEqual(failed, [])

    def test_case_ids_are_unique_and_the_count_is_deliberate(self):
        ids = [c['id'] for c in K.cases()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 75, 'the corpus holds 75 cases; adding or dropping one is a deliberate change to this number')

    def test_every_rule_has_a_case_that_raises_it_and_a_case_that_keeps_it_silent(self):
        raised, silent = set(), set()
        for c in K.cases():
            raised |= {k.split('|')[0] for k in c['expect'].get('raised', ())}
            silent |= set(c['expect'].get('silent', ()))
        self.assertEqual(set(K.THRESHOLD_RULES) - raised, set())
        self.assertEqual(set(K.THRESHOLD_RULES) - silent - {'R01'}, set())                  # R01's silent cases use only=[] with a run check

    def test_every_case_states_something_it_requires(self):
        for c in K.cases():
            self.assertTrue(set(c['expect']) & {'only', 'raised', 'lacks', 'silent', 'run', 'na_has', 'approved'}, c['id'])

    def test_a_wrong_expectation_is_reported_not_passed(self):
        base = K.cases()[0]
        for exp in ({'raised': ['R01|CC-01']}, {'only': ['R01|CC-01']}, {'run': {'R01': 'disabled'}}, {'approved': False}, {'rules_not_run': 3}, {'na_has': [['R01', 'nothing']]}):
            self.assertFalse(K.check_case(dict(base, expect=exp), world)[0], exp)
        c1 = [c for c in K.cases() if c['id'] == 'C01'][0]
        for exp in ({'raised': ['R01|CC-01'], 'gross': {'R01|CC-01': 1}}, {'raised': ['R01|CC-01'], 'unquantified': ['R01|CC-01']}, {'raised': ['R01|CC-01'], 'subtype': {'R01|CC-01': 'x'}},
                    {'raised': ['R01|CC-01'], 'severity': {'R01|CC-01': 'high'}}, {'lacks': ['R01|CC-01']}, {'raised': ['R01|CC-01'], 'limits_has': [['R01|CC-01', 'no such text']]},
                    {'silent': ['R01']}):
            self.assertFalse(K.check_case(dict(c1, expect=exp), world)[0], exp)

    def test_a_rule_that_did_not_run_is_never_accepted_as_silent(self):
        c = [c for c in K.cases() if c['id'] == 'C09'][0]
        self.assertTrue(K.check_case(c, world)[0])
        self.assertFalse(K.check_case(dict(c, expect={'silent': ['R01']}), world)[0])


if __name__ == '__main__':
    unittest.main()
