"""MIE-1: the construction pack, the M6 mapping and the isolation gate on Builder Zero (SY-04, SY-05, UT-26, UT-27, FL-10, IG-02, the golden run).  This file uses field
words and APG modules, so it is outside the core's neutrality scan; the core itself is unchanged by it.  Every owner input is TEST-ONLY (helpers_mie_construction)."""
import dataclasses, hashlib, json, os, subprocess, sys, unittest
from . import _path                                         # noqa: F401
from ._path import HERE_ROOT
from .helpers_mie_construction import LIMITS, ApgWorld, EVALUATION_DATE, NEED_BY, OWNER, completed_pack, golden_run, test_only_inputs
from apg.mkt import demo_mkt as DM, reference_m6 as RM
from mie.adapters import apg_host, feed as F, m6 as M6A
from mie.core import canon, engine as E, reference as R, vocab as Y
from mie.core.vocab import MieError
from mie.packs import construction as C

GOLDEN = os.path.join(HERE_ROOT, 'regression', 'mie1', 'golden_mie1.json')
M73_MANIFEST = os.path.join(HERE_ROOT, 'regression', 'mie1', 'M7_3_MANIFEST.sha256')


def code(fn):
    try:
        fn()
    except MieError as e:
        return e.code
    return None


class World:
    """One Builder Zero world for the class (the intake run takes a few seconds)."""
    w = None

    @classmethod
    def get(cls):
        if cls.w is None:
            cls.w = ApgWorld(HERE_ROOT)
        return cls.w


class TestBasePack(unittest.TestCase):
    def test_SY_04_the_base_pack_validates_allows_buy_only_and_carries_no_owner_value(self):
        """SY-04, MIE-R-49, MIE-R-50: structure only; no threshold, parameter, rule, subject, licence or freshness limit chosen by the author."""
        e = World.get().e
        doc = C.base_pack()
        v = e.validate_pack(World.get().ctx1, C.pack_bytes(doc))
        self.assertTrue(v['valid'], v)
        self.assertEqual(doc['allowed_intentions'], ['BUY'])
        self.assertEqual(doc['decision_profile'], 'CONTEXT_ONLY')
        for k in ('signals', 'parameters', 'freshness_limits', 'licences', 'sources', 'required_evidence', 'conversions', 'hooks'):
            self.assertEqual(doc[k], [], k)
        self.assertEqual(doc['vocabulary']['subjects'], [])
        self.assertIsNone(doc['decision_table'])
        self.assertEqual(doc['provenance']['owner_ref'], C.NOT_NAMED)
        self.assertNotIn('threshold', canon.dumps(doc).decode())

    def test_SY_04_activated_as_it_stands_the_base_pack_assesses_nothing(self):
        """SY-04: an incomplete pack: a material it does not declare is PACK_INCOMPLETE; nothing is invented."""
        w = World.get()
        pin = w.install(C.base_pack('0.1.0-SY04'))
        self.assertEqual(code(lambda: w.e.assess_timing(w.ctx1, pin, 'MAT-STEEL', 'BUY', {'need_by': NEED_BY}, [], EVALUATION_DATE)), 'PACK_INCOMPLETE')
        self.assertEqual(code(lambda: w.e.get_signals(w.ctx1, pin, 'MAT-STEEL', EVALUATION_DATE)), 'NOT_FOUND')

    def test_SY_05_the_pack_names_m6_terms_and_takes_only_what_the_m6_policy_holds(self):
        """SY-05, MIE-R-49, MIE-R-52: the watched materials and the buy-timing freshness limits come from the tenant's M6 policy unchanged; nothing else is taken from it."""
        pol = DM.demo_mkt_policy()
        got = C.owner_inputs_from_m6_policy(pol, 'X')
        self.assertEqual(set(got), {'subjects', 'freshness_limits', 'owner_ref'})
        self.assertEqual(got['subjects'], pol['scope']['watch_materials'])
        bt = pol['freshness']['buy_timing']
        self.assertEqual({f['observation_class']: f['days'] for f in got['freshness_limits']},
                         {'HISTORICAL_MOVEMENT': bt['index_max_age_days'], 'CURRENT_REFERENCE': bt['fx_max_age_days']})
        self.assertEqual(C.M6_KIND_MAP, {'index': ('HISTORICAL_MOVEMENT', 'INDEX')})
        doc = completed_pack()
        self.assertEqual(sorted(s['subject_id'] for s in doc['vocabulary']['subjects']), ['FX:AUD/USD', 'MAT-CU', 'MAT-PBOARD', 'MAT-REO', 'MAT-STEEL'])
        self.assertEqual(DM.demo_mkt_policy(), pol)                                            # nothing in M6 was changed by the mapping

    def test_the_completed_pack_validates_and_every_owner_value_is_flagged(self):
        """MIE-R-50: the completed version is a new pack version; every owner value in this test fixture says TEST-ONLY."""
        w = World.get()
        doc = completed_pack()
        self.assertTrue(w.e.validate_pack(w.ctx1, C.pack_bytes(doc))['valid'])
        refs = [p['owner_ref'] for p in doc['parameters']] + [s['parameter_owner_ref'] for s in doc['signals']] + [l['terms_ref'] for l in doc['licences']] + \
               [r['owner_ref'] for r in doc['decision_table'] if 'owner_ref' in r] + [r['assumption'] for r in doc['decision_table'] if 'assumption' in r] + \
               [doc['provenance']['owner_ref']]
        self.assertTrue(all('TEST-ONLY' in r for r in refs), refs)
        self.assertEqual(C.base_pack()['decision_table'], None)                              # the base is untouched


class TestBuyOnly(unittest.TestCase):
    def test_UT_26_no_input_produces_a_sell_side_outcome_under_the_buy_only_pack(self):
        """UT-26 (SB-10): every combination of material, date and scenario gives a BUY outcome; HOLD never appears."""
        w = World.get()
        doc = completed_pack('0.2.1-UT26')
        pin = w.install(doc)
        msgs, _ = w.messages(doc)
        w.e.submit_observations(w.ctx1, pin, msgs)
        seen = set()
        for subject in ('MAT-STEEL', 'MAT-REO', 'MAT-CU', 'MAT-PBOARD', 'FX:AUD/USD'):
            for c in ({}, {'need_by': '2026-10-01'}, {'need_by': NEED_BY}, {'need_by': '2027-06-30'}):
                for when in ('2026-06-01', EVALUATION_DATE, '2026-12-31'):
                    r = w.e.assess_timing(w.ctx1, pin, subject, 'BUY', c, [], when)
                    self.assertIn(r['outcome'], Y.OUTCOMES['BUY'])
                    self.assertEqual(r['signal_influence']['class'], 'NONE')
                    seen.add(r['outcome'])
        self.assertNotIn('HOLD', seen)
        self.assertTrue({'ACT_NOW', 'WAIT', 'NOT_ASSESSED'} <= seen, seen)

    def test_UT_26_a_sell_rule_cannot_be_added_to_the_buy_only_pack(self):
        """UT-26: a pack that allows BUY only and lists a SELL rule is refused at validation, so no stored version can hold one."""
        w = World.get()
        doc = completed_pack('0.2.2-UT26')
        doc['decision_table'].append({'rule_id': 'APG-R-SELL', 'intention': 'SELL', 'outcome': 'HOLD', 'rationale_code': 'X', 'basis_class': 'OBSERVED_EVIDENCE_ONLY',
                                      'predicates': [{'p': 'CONSTRAINT_ABSENT', 'constraint': 'days_to_need_by', 'negate': False}]})
        self.assertEqual(code(lambda: w.e.validate_pack(w.ctx1, C.pack_bytes(doc))), 'PACK_MALFORMED')
        self.assertEqual(code(lambda: w.e.register_pack(w.ctx1, C.pack_bytes(doc))), 'PACK_MALFORMED')

    def test_UT_27_a_sell_intention_is_refused(self):
        """UT-27."""
        w = World.get()
        pin = w.install(completed_pack('0.2.3-UT27'))
        self.assertEqual(code(lambda: w.e.assess_timing(w.ctx1, pin, 'MAT-STEEL', 'SELL', {}, [], EVALUATION_DATE)), 'INTENTION_NOT_ALLOWED')

    def test_a_market_predicate_is_refused_under_context_only(self):
        """MIE-R-51 at pack level: until the Section 08 change request is decided no APG rule may use a market signal."""
        w = World.get()
        doc = completed_pack('0.2.4-CTX')
        doc['decision_table'].insert(0, {'rule_id': 'APG-R-UP', 'intention': 'BUY', 'outcome': 'ACT_NOW', 'rationale_code': 'X', 'basis_class': 'OWNER_ASSUMPTION',
                                         'owner_ref': OWNER, 'assumption': 'TEST-ONLY',
                                         'predicates': [{'p': 'SIGNAL_PRESENT', 'type': 'LEVEL_MOVEMENT', 'evidence_class': None, 'direction': 'UP', 'negate': False}]})
        self.assertEqual(code(lambda: w.e.validate_pack(w.ctx1, C.pack_bytes(doc))), 'PACK_RULE_POLICY_VIOLATION')


class TestM6Mapping(unittest.TestCase):
    def test_BLK_02_the_stored_records_map_exactly(self):
        """BLK-02: every watched-material index record and every AUD/USD rate becomes one message with the value kept exactly; untracked materials are reported, not dropped silently."""
        w = World.get()
        doc = completed_pack()
        msgs, skipped = w.messages(doc)
        recs = {r.key: r.payload for r in w.s1.query('market_observation')}
        fx = {r.key: r.payload for r in w.s1.query('fx_rate')}
        idx = [m for m in msgs if m['observation_class'] == 'HISTORICAL_MOVEMENT']
        rates = [m for m in msgs if m['observation_class'] == 'CURRENT_REFERENCE']
        self.assertEqual(len(rates), len(fx))
        self.assertEqual(len(idx) + len(skipped), len(recs))
        for m in idx:
            f = recs[m['adapter_notes']['apg_record'].split('/', 1)[1]]['fields']
            self.assertEqual((m['subject_id'], m['as_of'], m['value'], m['unit'], m['source_id'], m['market']),
                             (f['material_ref'], f['obs_date'], {'mantissa': f['value_scaled'], 'exponent': 0}, f['unit_text'], f['source_label_text'], f['geography_text']))
        for m in rates:
            f = fx[m['adapter_notes']['apg_record'].split('/', 1)[1]]['fields']
            self.assertEqual(M6A.exact_decimal(f['rate_text']), m['value'])
            self.assertEqual(m['subject_id'], 'FX:' + f['currency_pair'])
        self.assertEqual({s['why'] for s in skipped}, {'a material the pack does not track'})
        self.assertEqual(M6A.exact_decimal('0.6540'), {'mantissa': 6540, 'exponent': -4})
        self.assertIsNone(M6A.exact_decimal('6.5e-1'))

    def test_the_mapping_reads_and_never_writes_the_apg_store(self):
        """IG-02 (store side): mapping, submitting and assessing leave every APG record and the APG audit chain exactly as they were."""
        w = ApgWorld(HERE_ROOT)
        before = (canon_store(w), len(w.audit._d.get('zero_one', [])))
        golden_flow(w)
        self.assertEqual((canon_store(w), len(w.audit._d.get('zero_one', []))), before)

    def test_another_tenants_records_never_reach_the_engine(self):
        """IS-03 on the host: the zero_two scoped store maps only zero_two records, and zero_two cannot see the zero_one pack activation or results."""
        w = World.get()
        doc = completed_pack('0.2.5-IS')
        pin = w.install(doc)
        msgs1, _ = w.messages(doc)
        r = w.e.submit_observations(w.ctx1, pin, msgs1)
        res = w.e.assess_timing(w.ctx1, pin, 'MAT-STEEL', 'BUY', {'need_by': NEED_BY}, [], EVALUATION_DATE)
        self.assertEqual(code(lambda: w.e.get_result(w.ctx2, res['result_id'])), 'NOT_FOUND')
        self.assertEqual(code(lambda: w.e.assess_timing(w.ctx2, pin, 'MAT-STEEL', 'BUY', {}, [], EVALUATION_DATE)), 'PACK_NOT_ACTIVE')
        self.assertEqual(r['counts']['ACCEPTED'] + r['counts']['DUPLICATE'], len(msgs1))
        self.assertEqual(r['counts']['REJECTED'], 0)
        msgs2, _ = w.messages(doc, w.s2)
        self.assertFalse({m['adapter_notes']['apg_record'] for m in msgs2} - {'market_observation/' + x.key for x in w.s2.query('market_observation')}
                         - {'fx_rate/' + x.key for x in w.s2.query('fx_rate')})

    def test_the_apg_context_adapter_refuses_what_apg_does_not_verify(self):
        """EDR-37 host port: a forged, expired or missing APG context is refused by the core with the core's own codes."""
        w = ApgWorld(HERE_ROOT)
        self.assertEqual(code(lambda: w.e.describe(None)), 'TENANT_CONTEXT_MISSING')
        self.assertEqual(code(lambda: w.e.describe('t1')), 'TENANT_CONTEXT_INVALID')
        forged = dataclasses.replace(w.ctx1, tenant_id='zero_two')                          # the seal no longer matches
        self.assertEqual(code(lambda: w.e.describe(forged)), 'TENANT_CONTEXT_INVALID')
        self.assertEqual(w.e.describe(w.ctx1)['versions'], Y.VERSIONS)
        w.clock.advance(10 ** 7)
        self.assertEqual(code(lambda: w.e.describe(w.ctx1)), 'TENANT_CONTEXT_INVALID')


def canon_store(w):
    """A digest of every revision of every record in the APG reference store (all tenants)."""
    return hashlib.sha256(repr(sorted(w.store._d.items(), key=lambda kv: kv[0])).encode()).hexdigest()


def golden_flow(w):
    doc = completed_pack()
    pin = w.install(doc)
    msgs, _ = w.messages(doc)
    w.e.submit_observations(w.ctx1, pin, msgs)
    r = w.e.assess_timing(w.ctx1, pin, 'MAT-STEEL', 'BUY', {'need_by': NEED_BY}, [], EVALUATION_DATE)
    w.e.replay_result(w.ctx1, r['result_id'])
    return r


class TestM6Feed(unittest.TestCase):
    """FL-10: the M6 MarketFeedPort reference, unchanged, wrapped by the mapping adapter; the analogues of MF-01..MF-13 hold at submit_observations and assessment."""
    def setUp(self):
        env = RM.feed_env()()
        self.prov, self.feed = env.provider, env.feed
        self.prov._contract_register_session('m6', 'zero_one', 'ann', ('importer',), 'human', 10 ** 6)
        self.m6ctx = self.prov.resolve('m6')
        self.obs, self.aud = R.RefObservations(), R.RefAudit()
        self.appr = R.RefApprovals()
        self.e = E.Engine(apg_host.ApgContext(self.prov), self.obs, R.RefRegistry(), R.RefResults(), self.aud, self.aud, self.appr, R.RefHooks(),
                          R.RefLimits(dict(LIMITS)))
        doc = completed_pack()
        self.pin = self.e.register_pack(self.m6ctx, canon.dumps(doc))['pin']
        self.appr.register('APR', 'TEST-ONLY approver', self.pin, 'zero_one')
        self.e.activate_pack(self.m6ctx, self.pin, 'APR')
        self.adapter = M6A.M6FeedAdapter(self.feed, self.m6ctx, {'SER-STEEL': ('MAT-STEEL', 'TEST-ONLY-LIC-INDEX')}, C.M6_KIND_MAP, 45, lambda: EVALUATION_DATE)
        self.drv = F.IngestionDriver(self.e, self.adapter)

    def row(self, oid, date, value, **kw):
        r = {'obs_id': oid, 'obs_date': date, 'value': value, 'unit': 'index_points_x100', 'kind': 'index', 'source_label': 'SYNTHETIC-INDEX', 'geography': 'AU-national'}
        r.update(kw)
        return r

    def load(self, rows, licence='licensed'):
        self.feed._contract_load_series('zero_one', 'SER-STEEL', rows, licence)

    def run_(self, when=EVALUATION_DATE):
        return self.drv.run(self.m6ctx, 'zero_one', self.pin, ['SER-STEEL'], when)['SER-STEEL']

    def test_FL_10_a_good_series_maps_submits_and_assesses(self):
        """FL-10 (MF-01, MF-02 analogues): values kept exactly; per-item receipts; the movement is computed by the core."""
        self.load([self.row('a', '2026-07-15', 10000), self.row('b', '2026-08-15', 10400), self.row('c', '2026-09-15', 10930)])
        rep = self.run_()
        self.assertEqual(rep['result']['counts'], {'ACCEPTED': 3, 'DUPLICATE': 0, 'REJECTED': 0})
        r = self.e.assess_timing(self.m6ctx, self.pin, 'MAT-STEEL', 'BUY', {'need_by': NEED_BY}, [], EVALUATION_DATE)
        mv = [s for s in r['signals'] if s['signal_id'] == 'APG-INDEX-MOVEMENT'][0]
        self.assertEqual((mv['status'], mv['direction']), ('ASSESSED', 'UP'))
        self.assertEqual(r['outcome'], 'ACT_NOW')

    def test_FL_10_retries_are_duplicates(self):
        """FL-10 (MF-03 analogue: an exact repeat is one observation)."""
        self.load([self.row('a', '2026-09-15', 10930), self.row('a2', '2026-09-15', 10930)])
        self.assertEqual(self.run_()['result']['counts'], {'ACCEPTED': 1, 'DUPLICATE': 0, 'REJECTED': 0})
        self.assertEqual(self.run_()['result']['counts'], {'ACCEPTED': 0, 'DUPLICATE': 1, 'REJECTED': 0})

    def test_FL_10_conflicting_values_on_one_date_are_reported_never_chosen(self):
        """FL-10 (MF-04 analogue)."""
        self.load([self.row('a', '2026-09-15', 10930), self.row('b', '2026-09-15', 11000)])
        self.assertEqual(self.run_()['result']['counts']['ACCEPTED'], 2)
        r = self.e.assess_timing(self.m6ctx, self.pin, 'MAT-STEEL', 'BUY', {'need_by': NEED_BY}, [], EVALUATION_DATE)
        self.assertIn('CONFLICT_IN_EVIDENCE', r['qualification']['reasons'])
        self.assertIn('DATA_CONFLICT', [s['signal_id'] for s in r['signals']])

    def test_FL_10_an_unlicensed_series_never_reaches_the_core(self):
        """FL-10 (MF-05, MF-06 analogues): the M6 port refuses; the refusal stays adapter-side; no core call, no core state."""
        self.load([self.row('a', '2026-09-15', 10930)], licence='unlicensed')
        n = len(self.aud.chains.get('zero_one', []))
        rep = self.run_()
        self.assertFalse(rep['submitted'])
        self.assertEqual((len(self.aud.chains.get('zero_one', [])), self.obs.d), (n, {}))

    def test_FL_10_malformed_rows_are_dropped_by_the_m6_port_and_bad_items_are_rejected_by_the_core(self):
        """FL-10 (MF-07, MF-08 analogues): a row the M6 port rejects is not returned; a returned row in a unit the pack does not declare is rejected by the core with the field named."""
        self.load([self.row('a', 'not-a-date', 10930), self.row('b', '2026-09-15', 10930, unit='tonnes'), self.row('c', '2026-09-14', 10900)])
        rep = self.run_()['result']
        self.assertEqual(rep['counts'], {'ACCEPTED': 1, 'DUPLICATE': 0, 'REJECTED': 1})
        bad = [x for x in rep['receipts'] if x['status'] == 'REJECTED'][0]
        self.assertEqual(bad['code'], 'OBSERVATION_INVALID')
        self.assertIn('unit', bad['fields'])

    def test_FL_10_nothing_after_the_evaluation_date_and_staleness_is_the_cores(self):
        """FL-10 (MF-09 to MF-11 analogues): the port returns nothing after as_of; the pack's freshness limit (from M6 buy_timing) decides staleness."""
        self.load([self.row('a', '2026-07-01', 10000), self.row('b', '2026-07-20', 10100), self.row('c', '2026-10-15', 11000)])
        self.assertEqual(self.run_()['result']['counts']['ACCEPTED'], 2)
        r = self.e.assess_timing(self.m6ctx, self.pin, 'MAT-STEEL', 'BUY', {'need_by': NEED_BY}, [], EVALUATION_DATE)
        self.assertIn('STALE_EVIDENCE', r['qualification']['reasons'])

    def test_FL_10_an_unknown_series_and_a_failing_port_stay_adapter_side(self):
        """FL-10 (MF-12, MF-13 analogues)."""
        self.assertFalse(self.run_()['submitted'])

        class Down(RM.InMemoryMarketFeed):
            def fetch(self, *a):
                raise RuntimeError('unreachable')
        self.adapter.feed = Down(self.prov, None)
        self.assertFalse(self.run_()['submitted'])
        self.assertEqual(self.obs.d, {})

    def test_FL_10_the_m6_port_definition_is_not_edited(self):
        """FL-10, MIE-R-47: apg/mkt/ports_m6.py and reference_m6.py are byte-identical to the delivered M7.3 package.  (apg/mkt/policy.py was in this list until APG-F67,
        which changes it to correct F-67, a separate finding about policy approvals; it is not part of the M6 port definition.)"""
        man = {line[66:].rstrip('\n'): line[:64] for line in open(M73_MANIFEST, encoding='utf-8')}
        for p in ('apg/mkt/ports_m6.py', 'apg/mkt/reference_m6.py', 'apg/mkt/fresh.py', 'apg/mkt/fx.py'):
            self.assertEqual(hashlib.sha256(open(os.path.join(HERE_ROOT, p), 'rb').read()).hexdigest(), man[p], p)


class TestGolden(unittest.TestCase):
    def test_the_golden_builder_zero_run_equals_the_recorded_answer(self):
        """The construction pack on Builder Zero: MAT-STEEL BUY with the demand's required date, assessed at 2026-09-30 and replayed identically."""
        got = golden_run(HERE_ROOT)
        want = json.load(open(GOLDEN, encoding='utf-8'))
        self.assertEqual(canon.dumps(got), canon.dumps(want))
        self.assertEqual(got['MAT-STEEL']['outcome'], 'ACT_NOW')
        self.assertEqual(got['MAT-STEEL']['influence'], 'NONE')
        self.assertEqual(got['MAT-STEEL']['days_to_need_by'], 62)
        self.assertTrue(got['replay']['identical'])
        self.assertEqual(got['receipt_counts']['REJECTED'], 0)

    def test_the_golden_run_is_deterministic(self):
        self.assertEqual(canon.dumps(golden_run(HERE_ROOT)), canon.dumps(golden_run(HERE_ROOT)))


BLOCK = ("import sys\n"
         "class B:\n"
         "    def find_spec(self, name, path=None, target=None):\n"
         "        if name == 'mie' or name.startswith('mie.'):\n"
         "            raise ImportError('the core is absent in this run')\n"
         "sys.meta_path.insert(0, B())\n")
OUT = ("sys.path.insert(0, %r)\n"
       "import hashlib\n"
       "from apg.mkt import golden_mkt as GM\n"
       "from apg.rec import golden_rec as GR\n"
       "print(hashlib.sha256(GM.dumps(GM.run_golden_mkt(%r)).encode()).hexdigest())\n"
       "print(hashlib.sha256(GR.dumps(GR.run_golden_rec(%r)).encode()).hexdigest())\n"
       "print('mie loaded' if any(m == 'mie' or m.startswith('mie.') for m in sys.modules) else 'mie absent')\n")


class TestIsolation(unittest.TestCase):
    def test_IG_02_apg_outputs_are_identical_with_and_without_the_core(self):
        """IG-02 (SB-27): the M6 and M7 golden Builder Zero outputs, computed in a process where the core cannot be imported, equal those computed in a process that has
        imported the core and run the construction pack on the same data first."""
        r = HERE_ROOT
        out = OUT % (r, r, r)
        without = subprocess.run([sys.executable, '-I', '-B', '-c', BLOCK + out], capture_output=True, text=True, timeout=900)
        pre = ("sys.path.insert(0, %r)\n"
               "from tests import helpers_mie_construction as H\n"
               "H.golden_run(%r)\n") % (r, r)
        with_core = subprocess.run([sys.executable, '-I', '-B', '-c', 'import sys\n' + pre + out], capture_output=True, text=True, timeout=900)
        self.assertEqual(without.returncode, 0, without.stderr[-500:])
        self.assertEqual(with_core.returncode, 0, with_core.stderr[-500:])
        a, b = without.stdout.split(), with_core.stdout.split()
        self.assertEqual(without.stdout.strip().splitlines()[-1], 'mie absent')
        self.assertEqual(with_core.stdout.strip().splitlines()[-1], 'mie loaded')
        self.assertEqual(a[:2], b[:2])


if __name__ == '__main__':
    unittest.main()
