import json, os, unittest
from . import _path                                          # noqa: F401
from ._path import HERE_ROOT
from apg.ingest import demo_setup as D, golden_m3 as GM, pipeline as P, reconcile as R, views
from .helpers_ingest import World


class GoldenM3(unittest.TestCase):
    def test_golden_cases_equal_the_recorded_answers(self):
        want = json.load(open(os.path.join(HERE_ROOT, 'regression', 'GOLDEN_M3.json')))
        got = {'oracle': GM.oracle_m3(HERE_ROOT), 'golden': GM.run_golden_m3(HERE_ROOT)}
        self.assertEqual(GM.dumps(got), GM.dumps(want))

    def test_the_run_is_deterministic(self):
        self.assertEqual(GM.dumps(GM.run_golden_m3(HERE_ROOT)), GM.dumps(GM.run_golden_m3(HERE_ROOT)))

    def test_headline_numbers_agree_with_the_independent_oracle(self):
        g, o = GM.run_golden_m3(HERE_ROOT), GM.oracle_m3(HERE_ROOT)
        self.assertEqual(g['invoice_cost_zero_one']['authoritative_cents'], o['eligible_net_of_credits_ex_gst_cents'])
        self.assertEqual(sorted(e[0] for e in g['invoice_cost_zero_one']['excluded']), o['held_invoice_ids'])
        self.assertEqual(g['PS-21']['gst_total_cents'], o['gst_known_net_of_credits_cents_of_eligible'])
        self.assertEqual(g['PS-24']['zero_two_excluded'], o['zero_two_invoice_ids_with_different_content'])

    def test_the_golden_answers_depend_on_the_register_it_is_not_a_constant(self):
        """With the register withdrawn nothing is authoritative; with a stricter approval count the same data gives a different answer."""
        w = World(); s = w.who('a')
        for t, data, src, name, rev in D.files_for(HERE_ROOT, 'zero_one'):
            P.ingest_file(s, w.clock, t, data, src, name, D.DEMO_POLICY, rev)
        R.reconcile(s, D.demo_register(approved=False), '2026-09-30')
        a, p = views.invoice_cost_view(s, '2026-09-30')
        self.assertEqual((a.cents, len(a.included)), (0, 0))
        R.reconcile(s, D.demo_register(), '2026-09-30')
        self.assertEqual(views.invoice_cost_view(s, '2026-09-30')[0].cents, 2167471697)


if __name__ == '__main__':
    unittest.main()
