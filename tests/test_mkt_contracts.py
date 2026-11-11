"""The MarketFeedPort (EDR-09) and ExtractionRuntimePort (EDR-08) contracts: the in-memory references pass, every deliberately faulty implementation is caught for the intended reason, and every
case is hit by at least one fault."""
import unittest
from . import _path                                         # noqa: F401
from apg.mkt import contracts_m6 as C, faulty_m6 as F, reference_m6 as REF


class TestM6Contracts(unittest.TestCase):
    def test_every_case_passes_on_the_references(self):
        res = C.run_all(REF.feed_env(), REF.extract_env())
        self.assertEqual([r for r in res if not r[3]], [])
        self.assertEqual((len([r for r in res if r[0] == 'market_feed']), len([r for r in res if r[0] == 'extraction'])), (13, 11))

    def test_every_faulty_implementation_is_caught_for_the_intended_reason(self):
        self.assertEqual(len(F.FAULTS), 25)
        for fid, (text, suite, factory, expect) in F.FAULTS.items():
            with self.subTest(fault=fid):
                res = C.run_all(factory if suite == 'market_feed' else None, factory if suite == 'extraction' else None)
                failed = {r[1] for r in res if not r[3]}
                self.assertTrue(set(expect) <= failed, f'{fid} {text}: failed {sorted(failed)}')

    def test_every_case_is_hit_by_at_least_one_fault(self):
        hit = set()
        for _, (_, _, _, expect) in F.FAULTS.items():
            hit |= set(expect)
        self.assertEqual({c[1] for c in C.CASES} - hit, set())

    def test_a_faulty_implementation_does_not_fail_the_other_suite(self):
        res = C.run_all(None, REF.extract_env())
        self.assertTrue(all(r[0] == 'extraction' for r in res))

    def test_the_cases_name_no_market_data_provider(self):
        import inspect
        src = inspect.getsource(C) + inspect.getsource(REF)
        for banned in ('bloomberg', 'reuters', 'refinitiv', 'abs.gov', 'rba.gov', 'lme', 'metals-api'):
            self.assertNotIn(banned, src.lower())


if __name__ == '__main__':
    unittest.main()
