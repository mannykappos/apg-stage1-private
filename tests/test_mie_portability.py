"""MIE-1 portability: the synthetic pack is labelled and claim-free; a second field runs on the same core code, unchanged (SY-01, SY-02, SY-03, SY-06)."""
import glob, hashlib, os, re, unittest
from . import _path                                         # noqa: F401
from ._path import HERE_ROOT
from .helpers_mie import EVAL, World, ob, series, UP
from mie.core import canon, engine as E, signals as S, timing as T
from mie.packs import synthetic as SP


def core_hashes():
    return {os.path.basename(p): hashlib.sha256(open(p, 'rb').read()).hexdigest() for p in sorted(glob.glob(os.path.join(HERE_ROOT, 'mie', 'core', '*.py')))}


class TestSynthetic(unittest.TestCase):
    def test_SY_01_the_synthetic_pack_is_labelled_and_claims_nothing(self):
        """SY-01."""
        doc = SP.pack()
        self.assertEqual(doc['field_label'], 'TEST FIELD (SYNTHETIC)')
        self.assertTrue(doc['provenance']['synthetic'])
        text = canon.dumps(doc).decode('utf-8').lower()
        for word in ('vendor', 'www.', 'http', 'real data', 'guaranteed', 'will rise', 'will fall', 'forecast'):
            self.assertNotIn(word, text)
        ids = re.findall(r'"(syn-[a-z0-9-]+)"', text)
        self.assertTrue(ids)

    def test_SY_06_every_author_chosen_value_is_flagged_test_only(self):
        """SY-06: owner references and terms in the synthetic pack and the shared fixtures say TEST-ONLY."""
        doc = SP.pack()
        refs = [p['owner_ref'] for p in doc['parameters']] + [f['owner_ref'] for f in doc['freshness_limits']] + [s['parameter_owner_ref'] for s in doc['signals']] + \
               [l['terms_ref'] for l in doc['licences']] + [doc['provenance']['author_ref'], doc['provenance']['owner_ref']] + \
               [r['owner_ref'] for r in doc['decision_table'] if 'owner_ref' in r] + [r['assumption'] for r in doc['decision_table'] if 'assumption' in r]
        self.assertTrue(refs)
        for r in refs:
            self.assertIn('TEST-ONLY', r)
        helpers = open(os.path.join(HERE_ROOT, 'tests', 'helpers_mie.py'), encoding='utf-8').read()
        self.assertIn('TEST-ONLY', helpers)

    def test_SY_02_core_files_are_identical_before_and_after_a_pack_is_added(self):
        """SY-02: registering, activating and running the second field changes no core file."""
        before = core_hashes()
        w = World()
        w.submit(series(UP))
        w.assess('SELL')
        w.assess('BUY', need_by='2026-12-01')
        self.assertEqual(core_hashes(), before)

    def test_SY_03_both_packs_run_through_the_same_assess_code_path(self):
        """SY-03: the same engine functions serve a BUY and SELL pack and a BUY-only pack (a second, independently shaped pack built from the first)."""
        calls = []
        real_ev, real_build = S.assess_evidence, T.build

        def ev_spy(doc, *a, **k):
            calls.append(('evidence', doc['pack_id'], tuple(doc['allowed_intentions'])))
            return real_ev(doc, *a, **k)

        def build_spy(doc, *a, **k):
            calls.append(('build', doc['pack_id'], tuple(doc['allowed_intentions'])))
            return real_build(doc, *a, **k)
        S.assess_evidence, T.build = ev_spy, build_spy
        try:
            w = World()
            w.submit(series(UP))
            w.assess('SELL')
            other = SP.pack('other')
            other.update(pack_id='SYN-SECOND-FIELD', allowed_intentions=['BUY'], decision_table=None)
            w2 = World(pack=other)
            w2.submit(series(UP))
            w2.assess('BUY')
        finally:
            S.assess_evidence, T.build = real_ev, real_build
        self.assertEqual(calls, [('evidence', 'SYN-TEST-FIELD', ('BUY', 'SELL')), ('build', 'SYN-TEST-FIELD', ('BUY', 'SELL')),
                                 ('evidence', 'SYN-SECOND-FIELD', ('BUY',)), ('build', 'SYN-SECOND-FIELD', ('BUY',))])


if __name__ == '__main__':
    unittest.main()
