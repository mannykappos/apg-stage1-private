import json, os, unittest
from . import _path                                          # noqa: F401
from ._path import HERE_ROOT
from apg import golden


class Golden(unittest.TestCase):
    def test_golden_cases_equal_the_recorded_answers(self):
        want = json.load(open(os.path.join(HERE_ROOT, 'regression', 'GOLDEN_M2.json')))
        got = {'oracle': golden.oracle(HERE_ROOT), 'golden': golden.run_golden(HERE_ROOT)}
        self.assertEqual(golden.dumps(got), golden.dumps(want))

    def test_headline_numbers_agree_with_the_independent_oracle(self):
        g, o = golden.run_golden(HERE_ROOT), golden.oracle(HERE_ROOT)
        self.assertEqual(g['PS-13']['authoritative_cents'], o['zero_one_ex_gst_total_cents'] - o['conflict_accounting_cents'])
        self.assertEqual([e[0] for e in g['PS-13']['excluded']], [o['conflict_invoice']])
        self.assertEqual(g['PS-21']['gst_known_total_cents'], o['zero_one_gst_total_cents_known'])
        self.assertEqual(sorted(x[0] for x in g['PS-21']['gst_left_out']), o['zero_one_gst_blank_ids'])
        self.assertEqual(sorted(g['PS-24']['zero_two_held']), o['zero_two_repeated_ids'])
        self.assertTrue(all(v[0] for v in g['PS-10'].values())); self.assertFalse(any(v[0] for v in g['NC-10'].values()))


if __name__ == '__main__':
    unittest.main()
