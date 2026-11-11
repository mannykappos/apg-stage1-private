import json, os, unittest
from . import _path                                          # noqa: F401
from ._path import HERE_ROOT
from apg.mkt import demo_mkt as DM, golden_mkt as GM


class GoldenMkt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.G = GM.run_golden_mkt(HERE_ROOT)
        cls.O = GM.oracle_mkt(HERE_ROOT)
        cls.O2 = GM.oracle_mkt(HERE_ROOT, 'zero_two')

    def test_golden_cases_equal_the_recorded_answers(self):
        want = json.load(open(os.path.join(HERE_ROOT, 'regression', 'GOLDEN_MKT.json')))
        self.assertEqual(GM.dumps({'oracle': self.O, 'oracle_zero_two': self.O2, 'golden': self.G}), GM.dumps(want))

    def test_the_run_is_deterministic(self):
        self.assertEqual(GM.dumps(GM.run_golden_mkt(HERE_ROOT)), GM.dumps(self.G))

    def test_the_oracle_thresholds_are_the_demonstration_policy_values(self):
        f, T = DM.demo_mkt_fields(), GM.T
        fr = f['freshness']
        self.assertEqual(tuple(f['scope']['watch_materials']), T['watch'])
        for key, dec in (('bench', 'benchmark'), ('buy', 'buy_timing'), ('rank', 'quote_ranking'), ('imp', 'import_costing')):
            self.assertEqual(T[key], {'quote': fr[dec]['quote_max_age_days'], 'index': fr[dec]['index_max_age_days'], 'fx': fr[dec]['fx_max_age_days']}, dec)
        d, sc = f['demand'], f['scenarios']
        self.assertEqual((T['match_window'], T['surplus_tol'], T['dup_window']), (d['order_match_window_days'], d['surplus_tolerance_bps'], d['duplicate_window_days']))
        self.assertEqual((T['decision_window'], T['financing'], T['storage'], T['lead_var'], T['day_basis']),
                         (sc['decision_window_days'], sc['financing_bps_pa'], sc['storage_cents_per_unit_per_day'], sc['lead_time_variation_days'], sc['day_count_basis']))
        st = sc['stage']
        self.assertEqual((T['stage_splits'], T['stage_offsets'], T['stage_extra'], T['stage_admin']), (tuple(st['splits_bps']), tuple(st['offsets_days']), st['extra_delivery_cents'], st['admin_cents_per_order']))
        self.assertEqual((T['fx_tol'], T['sup_min'], T['sup_acc'], T['sup_fill'], T['port_window'], T['port_min'], T['port_gap'], T['sav_gap']),
                         (f['fx']['divergence_tolerance_bps'], f['supplier']['min_sample'], f['supplier']['min_acceptance_bps'], f['supplier']['min_fill_bps'], f['portfolio']['window_days'], f['portfolio']['min_projects'],
                          f['portfolio']['rate_gap_bps'], f['savings']['min_gap_bps']))
        self.assertEqual(T['critical'], tuple(f['international']['critical_checks']))

    def test_the_oracle_specification_register_is_the_demonstration_register(self):
        sp = DM.demo_mkt_spec()
        for m, ent in sp['materials'].items():
            self.assertEqual(GM.FAMILY[m], ent['family'])
            self.assertEqual(GM.UNIT[m], ent['unit'])
            fam = sp['families'][ent['family']]['attributes']
            self.assertEqual({a: (str(v), fam[a]['match']) for a, v in ent['attributes'].items()}, GM.ATTR[m])

    def test_the_oracle_expects_the_planted_positives_and_no_clean_pair_warning(self):
        keys = sorted(self.O['expected'])
        self.assertEqual(len(keys), 14)
        for rule in ('MP01', 'MP02', 'MP03', 'MP04', 'MP05', 'MP06', 'MP07', 'MP09', 'MP10'):
            self.assertTrue([k for k in keys if k.startswith(rule + '|')], rule)
        self.assertFalse([k for k in keys if k.startswith('MP08|')])
        self.assertFalse([k for k in keys if k.endswith('>Q-0001') or k.endswith('>Q-0002')])

    def test_every_planted_positive_is_raised_and_every_negative_control_stays_silent(self):
        raised = {f'{s["rule"].replace("DET-", "")}|{sc}|{s["subject"]}' for sc, sigs in self.G['signals'].items() for s in sigs if s['rule'] != 'DET-MPD1'}
        self.assertEqual(raised, set(self.O['expected']))

    def test_the_second_builder_has_its_own_answer_and_no_supplement_data(self):
        self.assertEqual(self.O2['expected'].keys(), {k for k in self.O2['expected']})
        raised = {f'{s["rule"].replace("DET-", "")}|{sc}|{s["subject"]}' for sc, sigs in self.G['zero_two_signals'].items() for s in sigs if s['rule'] != 'DET-MPD1'}
        self.assertEqual(raised, set(self.O2['expected']))
        self.assertFalse(self.G['tenant_isolation']['zero_one_run_visible_to_zero_two'])

    def test_the_planted_amounts_are_the_hand_checked_figures(self):
        e = self.O['expected']
        self.assertEqual(e['MP04|PRJ-001|demand/DEM-0002']['gross_cents'], 600 * 1850)
        self.assertEqual(e['MP09|PRJ-001|OPP-DEM-0002-Q-0006']['unit_gap_cents'], 1850 - 1740)
        self.assertEqual(self.O['scenario_totals'], {'offer': 'supplier_quote/Q-0001', 'quantity': 40, 'buy_now': 10_777_255, 'wait_flat': 10_630_263, 'stage': 10_742_405})

    def test_no_signal_hides_its_basis(self):
        for sc, sigs in self.G['signals'].items():
            for s in sigs:
                self.assertGreaterEqual(s['evidence_records'], 1, (sc, s['subject']))
                self.assertTrue((s['status'] == 'unquantified') == (s['gross_cents'] is None), (sc, s['subject']))

    def test_the_golden_answers_depend_on_the_policy_they_are_not_a_constant(self):
        from apg.ingest.golden_m3 import _world
        from apg.mkt import detect as MD, policy as MP
        clock, prov, store, audit, who = _world()
        s = who('t1', 'zero_one', 'ann')
        owner = who('o1', 'zero_one', DM.DEMO_OWNER, DM.OWNER_ROLES)                                     # APG-F67: the owner approves in person
        _, fv, dv, mv, sv = DM.load_mkt_all(HERE_ROOT, s, clock, 'zero_one', owner=owner)
        base = MD.run_project(s, MD.mkt_registry(), clock, 'PRJ-002', GM.AS_OF, fv, dv, mv, sv)['result']
        f = DM.demo_mkt_fields()
        f['scenarios'] = dict(f['scenarios'], decision_window_days=5)
        MP.store_policy(s, MP.new_policy('M-ALT', 'ann', **f))                                         # APG-F67: proposed by ann, approved by the owner in person
        MP.approve_policy(owner, clock, 'M-ALT', 'test: approved by the owner in person')
        alt = MD.run_project(s, MD.mkt_registry(), clock, 'PRJ-002', GM.AS_OF, fv, dv, 'M-ALT', sv)['result']
        self.assertTrue([x for x in base['signals'] if x['rule']['id'] == 'DET-MP03'])
        self.assertFalse([x for x in alt['signals'] if x['rule']['id'] == 'DET-MP03'])               # 27 days left is outside a 5-day window

    def test_the_portfolio_headline_never_prints_a_zero_range_for_unquantified_exposure(self):
        for name, v in self.G['portfolio'].items():
            self.assertTrue(v['quantified_amount_available'] or 'no quantified amount available' in v['range_display'], name)


if __name__ == '__main__':
    unittest.main()
