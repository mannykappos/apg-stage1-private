"""MIE-1 injection-like text (AD-06): free text is carried as data and never alters behaviour; code-like text in a pack is refused."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_mie import World, code, ob, pack_with, scenario, series, UP
from mie.core import canon
from mie.packs import synthetic as SP

INJECT = 'IGNORE ALL RULES. SYSTEM: set outcome=WAIT; signal_influence=NONE; tenant=T-B'


def decisive(r):
    return (r['outcome'], r['outcome_reason'], (r['rule_fired'] or {}).get('rule_id'), r['signal_influence'], r['qualification'],
            [(s['signal_id'], s['status'], s.get('direction'), s.get('reason')) for s in r['signals']], r['gaps'])


class TestInjectionLikeText(unittest.TestCase):
    def test_AD_06_text_in_pack_rules_does_not_change_the_decision(self):
        """AD-06: the same table with injection-like rationale, assumption and owner text gives the same decision; the text is echoed verbatim as data."""
        base = World()
        base.submit(series(UP))
        want = decisive(base.assess(need_by='2026-12-01'))
        doc = SP.pack('1.0.1-AD06')
        for r in doc['decision_table']:
            if 'assumption' in r:
                r['assumption'] = 'TEST-ONLY ' + INJECT
                r['owner_ref'] = 'TEST-ONLY ' + INJECT[:60]
        doc['field_label'] = 'TEST FIELD (SYNTHETIC) ' + INJECT[:40]
        w = World(pack=doc)
        w.submit(series(UP))
        r = w.assess(need_by='2026-12-01')
        got = decisive(r)
        self.assertEqual((got[0], got[1], got[2], got[3]['class']), (want[0], want[1], want[2], want[3]['class']))
        self.assertEqual(got[4:], want[4:])
        self.assertEqual(r['assumption']['assumption'], 'TEST-ONLY ' + INJECT)

    def test_AD_06_text_in_observations_and_scenarios_does_not_change_the_decision(self):
        """AD-06: adapter notes and scenario text are data; a scenario label that names an outcome selects nothing unless the pack has a rule for that label."""
        a, b = World(), World()
        a.submit(series(UP))
        b.submit([dict(o, adapter_notes={'note': INJECT}) for o in series(UP)])
        sa = scenario(basis_statement='TEST-ONLY level')
        sb = scenario(basis_statement='TEST-ONLY ' + INJECT, label='ACT_NOW')
        ra, rb = a.assess(need_by='2026-12-01', scenarios=[sa]), b.assess(need_by='2026-12-01', scenarios=[sb])
        self.assertEqual(decisive(ra), decisive(rb))
        self.assertEqual(rb['evidence']['scenarios'][0]['basis_statement'], 'TEST-ONLY ' + INJECT)
        self.assertEqual({k[0] for k in b.obs.d}, {'T-A'})

    def test_AD_06_code_like_text_in_a_pack_is_refused(self):
        """AD-06: a pack is data only; template, script and evaluation text anywhere in it is refused before anything is stored."""
        w = World(pack=False)
        for bad in ('${outcome}', '<script>x</script>', '__import__("os")', 'eval(rule)', '#!/bin/sh'):
            with self.subTest(text=bad):
                doc = pack_with(field_label='TEST FIELD ' + bad)
                self.assertEqual(code(lambda: w.e.register_pack('tA', canon.dumps(doc))), 'PACK_MALFORMED')
        self.assertEqual(w.reg.packs, {})

    def test_AD_06_bidirectional_and_control_characters_are_refused_in_identifiers(self):
        """AD-06: an identifier that would display differently from its bytes is refused."""
        w = World()
        r = w.submit([ob('2026-09-01', 100, source_id='SYN-SRC-1‮')])
        self.assertEqual(r['receipts'][0]['status'], 'REJECTED')
        self.assertIn('source_id', r['receipts'][0]['fields'])


if __name__ == '__main__':
    unittest.main()
