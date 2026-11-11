import re, unittest
from . import _path                                          # noqa: F401
from . import corpus_mkt as K


class MktCorpus(unittest.TestCase):
    def test_every_faulty_or_borderline_input_case_gives_the_required_result(self):
        failed = []
        for c in K.cases():
            ok, msg = K.check_case(c)
            if not ok:
                failed.append(f'{c["id"]} {c["desc"]}: {msg}')
        self.assertEqual(failed, [])

    def test_case_ids_are_unique_and_the_count_is_deliberate(self):
        ids = [c['id'] for c in K.cases()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 78, 'the corpus holds 78 cases; adding or dropping one is a deliberate change to this number')

    def test_every_case_states_something_checkable(self):
        for c in K.cases():
            self.assertTrue(set(c['expect']) & {'rank', 'rules', 'fn'}, c['id'])

    def test_every_rule_has_a_case_that_raises_it_and_a_case_that_keeps_it_silent_or_unrun(self):
        raised, silent = set(), set()
        for c in K.cases():
            r = c['expect'].get('rules', {})
            raised |= {x.split(':')[0] for x in r.get('raised', ())}
            silent |= {x.split(':')[0] for x in r.get('silent', ())} | set(r.get('run', {}))
        every = {f'MP{i:02d}' for i in range(1, 11)} | {'MPD1'}
        # MP10 is kept silent by the information-boundary case F05, which is an fn check
        self.assertEqual(every - raised, set(), 'a rule has no case that raises it')
        self.assertEqual(every - silent - {'MP10'}, set(), 'a rule has no case that keeps it silent')

    def test_the_rfc01_test_categories_are_all_present(self):
        text = ' '.join(c['desc'].lower() for c in K.cases())
        for word in ('no quote', 'conflict', 'duplicate', 'exchange rate', 'stale', 'lead time', 'human approval', 'large quantity'):
            self.assertIn(word, text, word)
        groups = {re.match(r'[A-Z]', c['id']).group(0) for c in K.cases()}
        self.assertEqual(groups, set('ABCDEF'))


if __name__ == '__main__':
    unittest.main()
