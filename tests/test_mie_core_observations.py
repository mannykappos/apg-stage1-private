"""MIE-1 observations: validation at submission, licence gate, time rules, identity, duplicates, corrections and conflicts (UT-01..UT-12, UT-47, UT-49, AD-05, AD-07,
AD-10, AD-12, CT-03)."""
import unittest
from . import _path                                         # noqa: F401
from .helpers_mie import EVAL, LIMITS, World, code, ev, ob, rate, series, UP
from mie.core import canon, observations as O, signals as S
from mie.core.observations import REQUIRED


def receipt(w, item):
    return w.submit([item])['receipts'][0]


class TestValidation(unittest.TestCase):
    def setUp(self):
        self.w = World()

    def test_UT_01_each_required_attribute_missing_in_turn_is_rejected_by_name(self):
        """UT-01."""
        for k in REQUIRED:
            with self.subTest(attribute=k):
                o = ob('2026-09-01', 100)
                del o[k]
                r = receipt(self.w, o)
                self.assertEqual((r['status'], r['code'], r['fields']), ('REJECTED', 'OBSERVATION_INVALID', [k]))
                o = ob('2026-09-01', 100)
                o[k] = None
                self.assertEqual(receipt(self.w, o)['fields'], [k])
        o = ob('2026-09-01')
        self.assertEqual(receipt(self.w, o)['fields'], ['value', 'event_label'])
        o = ob('2026-09-01', 100, event_label='SYN-VARIANT-NEW')
        self.assertEqual(receipt(self.w, o)['fields'], ['value', 'event_label'])

    def test_UT_02_floats_nan_infinity_booleans_and_numeric_strings_are_rejected(self):
        """UT-02 (SB-02)."""
        for bad in (1.5, float('nan'), float('inf'), True, '100', {'mantissa': 1.0, 'exponent': 0}, {'mantissa': True, 'exponent': 0}, {'mantissa': '1', 'exponent': 0},
                    {'mantissa': 1, 'exponent': 0.0}, {'mantissa': 1}, {'mantissa': 1, 'exponent': 0, 'x': 1}):
            with self.subTest(value=bad):
                o = ob('2026-09-01', 1)
                o['value'] = bad
                r = receipt(self.w, o)
                self.assertEqual((r['status'], r['fields']), ('REJECTED', ['value']))
        self.assertEqual(self.w.obs.d, {})

    def test_UT_03_values_with_exponents_give_exact_ratios(self):
        """UT-03, UT-49: different exponents align exactly; no float is created; the ratios equal those at one exponent."""
        a = World()
        a.submit([ob('2026-08-01', 10000, -2), ob('2026-09-01', 105, 0)])
        b = World()
        b.submit([ob('2026-08-01', 100, 0), ob('2026-09-01', 10500, -2)])
        sa = [s for s in a.signals()['signals'] if s['signal_id'] == 'SYN-SIG-LEVEL'][0]
        sb = [s for s in b.signals()['signals'] if s['signal_id'] == 'SYN-SIG-LEVEL'][0]
        self.assertEqual(sa['ratio'], {'num': 1, 'den': 20})
        self.assertEqual(sa['ratio'], sb['ratio'])
        self.assertEqual(sa['direction'], 'UP')
        self.assertEqual(sa['difference'], {'mantissa': 500, 'exponent': -2})
        for v in (sa['ratio']['num'], sa['ratio']['den'], sa['difference']['mantissa']):
            self.assertIsInstance(v, int)

    def test_UT_04_unknown_class_or_basis_is_rejected(self):
        """UT-04 (the separation of the four evidence groups is in test_mie_core_timing)."""
        self.assertEqual(receipt(self.w, ob('2026-09-01', 1, observation_class='RUMOUR'))['fields'], ['observation_class'])
        self.assertEqual(receipt(self.w, ob('2026-09-01', 1, value_basis='GUESS'))['fields'], ['value_basis'])
        self.assertEqual(receipt(self.w, ob('2026-09-01', 1, source_id='SYN-SRC-2', value_basis='INDEX'))['fields'], ['value_basis'])

    def test_undeclared_references_are_rejected_by_name(self):
        """MIE-R-06: a source, licence, unit, market or subject the pack does not declare."""
        for k, v in (('source_id', 'SYN-SRC-X'), ('licence_ref', 'SYN-LIC-4'), ('unit', 'SYN-UNIT-X'), ('market', 'SYN-MARKET-X'), ('subject_id', 'SYN-ITEM-X')):
            with self.subTest(attribute=k):
                self.assertEqual(receipt(self.w, ob('2026-09-01', 1, **{k: v}))['fields'], [k])
        self.assertEqual(receipt(self.w, ob('2026-09-01', 1, colour='blue'))['fields'], ['colour'])
        self.assertEqual(receipt(self.w, ev('2026-09-01', 'SYN-NOT-MAPPED'))['fields'], ['event_label'])
        r = self.w.submit(['not an object'])['receipts'][0]
        self.assertEqual(r['fields'], ['$'])

    def test_UT_05_unlicensed_and_unknown_licences_are_never_stored(self):
        """UT-05 (SB-03): UNLICENSED and UNKNOWN are refused at submission (LICENCE_NOT_PERMITTED); the window is applied at use (test_mie_core_signals)."""
        for src, lic in (('SYN-SRC-U', 'SYN-LIC-2'), ('SYN-SRC-K', 'SYN-LIC-3')):
            r = receipt(self.w, ob('2026-09-01', 1, source_id=src, licence_ref=lic))
            self.assertEqual((r['status'], r['code']), ('REJECTED', 'LICENCE_NOT_PERMITTED'))
        self.assertEqual(self.w.obs.d, {})

    def test_UT_07_retrieved_before_as_of_is_refused_and_dates_must_be_real(self):
        """UT-07, AD-08 (impossible dates)."""
        self.assertEqual(receipt(self.w, ob('2026-09-02', 1, retrieved_at='2026-09-01'))['fields'], ['retrieved_at'])
        self.assertEqual(receipt(self.w, ob('2026-09-02', 1, retrieved_at='2026-09-02T00:00:00Z'))['status'], 'ACCEPTED')
        for d in ('2026-02-30', '2026-13-01', '26-09-01', '2026-9-1', '2026-09-01T10:00'):
            with self.subTest(as_of=d):
                self.assertEqual(receipt(self.w, ob(d, 1, retrieved_at='2026-10-01'))['fields'], ['as_of'])
        self.assertEqual(receipt(self.w, ob('2026-09-01', 1, retrieved_at='yesterday'))['fields'], ['retrieved_at'])
        self.assertEqual(receipt(self.w, ob('2026-09-01', 1, valid_until='soon'))['fields'], ['valid_until'])

    def test_UT_47_values_outside_the_unit_domain_are_rejected(self):
        """UT-47 (SB-45)."""
        cases = [('SYN-UNIT', 0, 'REJECTED'), ('SYN-UNIT', -5, 'REJECTED'), ('SYN-UNIT', 5, 'ACCEPTED'), ('SYN-COUNT', -1, 'REJECTED'), ('SYN-COUNT', 0, 'ACCEPTED'),
                 ('SYN-SIGNED', -7, 'ACCEPTED'), ('SYN-SIGNED', 0, 'ACCEPTED')]
        for unit, m, want in cases:
            with self.subTest(unit=unit, mantissa=m):
                r = receipt(self.w, ob('2026-09-0%d' % (abs(m) % 9 + 1), m, 0, unit=unit))
                self.assertIn(r['status'], (want, 'DUPLICATE'))
                if want == 'REJECTED':
                    self.assertEqual(r.get('reason'), 'VALUE_OUT_OF_DOMAIN')

    def test_AD_05_control_characters_twins_bidirectional_marks_and_homoglyphs_are_refused(self):
        """AD-05."""
        for sid in ('SYN-ITEM-A\x00', 'SYN-ITEM-A‮', 'SYN-ITEM-А', 'SYN-ITEM-A‏', 'SYN\nITEM'):
            with self.subTest(subject=repr(sid)):
                self.assertEqual(receipt(self.w, ob('2026-09-01', 1, subject_id=sid))['status'], 'REJECTED')
        self.assertEqual(receipt(self.w, ob('2026-09-01', 1, subject_id='SYN-ITEM-A' + 'x' * 300))['status'], 'REJECTED')

    def test_AD_07_extreme_exponents_and_huge_integers_are_refused_or_exact(self):
        """AD-07: bounds come from the host limits; within them arithmetic is exact."""
        r = receipt(self.w, ob('2026-09-01', 1, 31))
        self.assertEqual((r['status'], r['code']), ('REJECTED', 'LIMIT_EXCEEDED'))
        r = receipt(self.w, ob('2026-09-01', 10 ** 31))
        self.assertEqual((r['status'], r['code']), ('REJECTED', 'LIMIT_EXCEEDED'))
        w = World()
        w.submit([ob('2026-08-01', 10 ** 29, -30), ob('2026-09-01', 10 ** 29 + 1, -30)])
        s = [x for x in w.signals()['signals'] if x['signal_id'] == 'SYN-SIG-LEVEL'][0]
        self.assertEqual(s['ratio'], {'num': 1, 'den': 10 ** 29})
        self.assertEqual(s['direction'], 'UNCHANGED')

    def test_FL_02_an_item_an_adapter_marks_pre_validated_is_still_validated(self):
        """FL-02 (SB-47)."""
        o = ob('2026-09-01', -5, adapter_notes={'pre_validated': True, 'checked_by': 'adapter'})
        r = receipt(self.w, o)
        self.assertEqual((r['status'], r['fields'], r.get('reason')), ('REJECTED', ['value'], 'VALUE_OUT_OF_DOMAIN'))
        self.assertEqual(receipt(self.w, ob('2026-09-01', 1, adapter_notes={'x': 1.5}))['fields'], ['adapter_notes'])


class TestIdentity(unittest.TestCase):
    def test_UT_09_identical_resubmission_is_a_duplicate_and_the_id_is_content_addressed(self):
        """UT-09, CT-03, FL-04."""
        w = World()
        o = ob('2026-09-01', 100)
        r1 = w.submit([o, dict(o)])['receipts']
        self.assertEqual([r['status'] for r in r1], ['ACCEPTED', 'DUPLICATE'])
        r2 = w.submit([dict(o, adapter_notes={'run': 2})])['receipts'][0]
        self.assertEqual(r2['status'], 'DUPLICATE')
        self.assertEqual(r1[0]['observation_id'], r2['observation_id'])
        self.assertEqual(r1[0]['observation_id'], O.observation_id({k: v for k, v in o.items()}))
        self.assertEqual(len(w.obs.d), 1)
        self.assertTrue(r1[0]['observation_id'].startswith('OB-') and len(r1[0]['observation_id']) == 67)
        self.assertEqual(w.obs.append('T-A', r1[0]['observation_id'], o), 'duplicate')

    def test_aliases_store_the_canonical_subject(self):
        """MIE-R-05: the alias table is the only equivalence; the stored observation names the declared subject."""
        w = World()
        r = w.submit([ob('2026-09-01', 100, subject_id='SYN-ITEM-A-ALT'), ob('2026-09-01', 100)])['receipts']
        self.assertEqual([x['status'] for x in r], ['ACCEPTED', 'DUPLICATE'])

    def test_UT_10_a_correction_supersedes_by_a_new_observation_and_the_original_is_kept(self):
        """UT-10."""
        w = World()
        first = w.submit([ob('2026-09-01', 100)])['receipts'][0]['observation_id']
        r = w.submit([ob('2026-09-01', 120, supersedes=first)])['receipts'][0]
        self.assertEqual(r['status'], 'ACCEPTED')
        self.assertIsNotNone(w.obs.get('T-A', first))
        self.assertEqual(w.submit([ob('2026-09-02', 1, supersedes='OB-' + '0' * 64)])['receipts'][0]['fields'], ['supersedes'])
        obs = w.obs.for_subjects('T-A', ['SYN-ITEM-A'])
        st = S.classify(w.doc, obs, EVAL)
        self.assertEqual(st[first], ('HISTORY', None))
        self.assertEqual(st[r['observation_id']], ('ELIGIBLE', None))

    def test_UT_11_and_UT_12_conflicts_are_reported_and_revisions_supersede(self):
        """UT-11, UT-12 (SB-05): equal revision with different values conflicts and both are kept; a higher revision supersedes; equal values with different exponents
        are not a conflict."""
        w = World()
        ids = [r['observation_id'] for r in w.submit([ob('2026-09-01', 100, revision=1), ob('2026-09-01', 110, revision=1),
                                                      ob('2026-08-01', 100, revision=1), ob('2026-08-01', 120, revision=2),
                                                      ob('2026-07-01', 100), ob('2026-07-01', 1, 0)])['receipts']]
        obs = w.obs.for_subjects('T-A', ['SYN-ITEM-A'])
        st = S.classify(w.doc, obs, EVAL)
        conf = S.conflicts(obs, st)
        self.assertEqual(sorted(v for vals in conf.values() for v in vals), sorted(ids[:2]))
        self.assertEqual(st[ids[2]], ('HISTORY', None))
        self.assertEqual(st[ids[3]], ('ELIGIBLE', None))
        view = w.signals()
        dc = [s for s in view['signals'] if s['type'] == 'DATA_CONFLICT'][0]
        self.assertEqual(dc['items'][0]['as_of'], '2026-09-01')
        self.assertEqual(sorted(dc['items'][0]['evidence_ids']), sorted(ids[:2]))
        self.assertIn('CONFLICT_IN_EVIDENCE', [g['reason'] for g in view['gaps']])


class TestLicenceAndTenancyOfEvidence(unittest.TestCase):
    def test_AD_10_licensed_and_window_excluded_data_in_one_window(self):
        """AD-10 (SB-26), UT-05 (outside the licence window): only licensed, in-window evidence is used; the rest is listed."""
        w = World()
        w.submit(series(UP) + [ob('2026-09-20', 99999, source_id='SYN-SRC-W', licence_ref='SYN-LIC-4')])
        s = w.signals()
        lvl = [x for x in s['signals'] if x['signal_id'] == 'SYN-SIG-LEVEL'][0]
        self.assertEqual(lvl['end']['as_of'], '2026-09-15')
        self.assertIn('LICENCE_EXCLUDED', [g['reason'] for g in s['gaps'] if g['kind'] == 'observation'])
        early = w.e.get_signals('tA', w.pin, 'SYN-ITEM-A', '2026-06-01')
        self.assertNotIn('LICENCE_EXCLUDED', [g['reason'] for g in early['gaps'] if g['kind'] == 'observation' and g['observation_id'] != ''])

    def test_AD_12_resubmitting_under_another_tenant_has_no_cross_tenant_effect(self):
        """AD-12, IS-04 (SB-32): a tenant without the activation cannot submit; with its own activation it holds its own copy."""
        w = World()
        o = ob('2026-09-01', 100)
        w.submit([o])
        self.assertEqual(code(lambda: w.submit([o], token='tB')), 'PACK_NOT_ACTIVE')
        w.activate('tB', w.pin)
        r = w.submit([o], token='tB')['receipts'][0]
        self.assertEqual(r['status'], 'ACCEPTED')
        self.assertEqual(len(w.obs.for_subjects('T-A', ['SYN-ITEM-A'])), 1)
        self.assertEqual(len(w.obs.for_subjects('T-B', ['SYN-ITEM-A'])), 1)
        self.assertEqual(sorted(k[0] for k in w.obs.d), ['T-A', 'T-B'])

    def test_a_rejected_item_never_reaches_the_store_and_counts_are_reported(self):
        """MIE-R-06: a rejected observation is counted and never used."""
        w = World()
        r = w.submit([ob('2026-09-01', 100), ob('2026-09-02', -1), rate('2026-09-01', 6540)])
        self.assertEqual(r['counts'], {'ACCEPTED': 2, 'DUPLICATE': 0, 'REJECTED': 1})
        self.assertEqual(len(w.obs.d), 2)


if __name__ == '__main__':
    unittest.main()
