"""M7 golden run on Builder Zero, with an INDEPENDENT oracle: routes, categories and counted totals are recomputed from the stored payloads with the standard library only (nothing from apg.rec),
so the expected answers cannot simply agree with the code that wrote them.  The oracle restates the eligibility rules of Section 10 section 3 and the overlap rule of Section 06 section 9 as the
demonstration policy configures them."""
import datetime, json, os, unittest
from . import _path                                         # noqa: F401
from ._path import HERE_ROOT
from apg.rec import golden_rec as GR

GOLDEN = os.path.join(HERE_ROOT, 'regression', 'm7', 'golden_rec.json')
EXCLUDED, NOT_REVIEWED, IN_HAND = ('dismissed', 'superseded'), ('detected', 'under_review', 'reopened'), ('action_approved', 'in_progress')
STRENGTH = {'weak': 1, 'moderate': 2, 'strong': 3}
POLICY_PREFIXES = ('det_policy/', 'fin_policy/', 'mkt_policy/', 'mkt_spec/')


def oracle(inputs, as_of):
    pol = [v for k, v in inputs.items() if k.startswith('rec_policy/')][0]
    findings = sorted((v for k, v in inputs.items() if k.startswith('finding/')), key=lambda f: f['finding_id'])
    ins = {k.split('/', 1)[1]: v for k, v in inputs.items() if k.startswith('rec_input/')}
    d0 = datetime.date.fromisoformat(as_of)
    out = {}
    for f in findings:
        if f['status'] in EXCLUDED:
            continue
        sig = f['signal']
        rid = 'REC-' + f['finding_id'][4:]
        u = sig['priority']['urgency']
        expired = sig['interpretation'] == 'potential_opportunity' and u.get('time_sensitive') and u.get('date') and datetime.date.fromisoformat(u['date']) < d0
        if f['status'] == 'resolved' or expired:
            out[rid] = ('close', 'close')
            continue
        if f['status'] in IN_HAND:
            out[rid] = ('in_hand', pol['categories'].get(sig['interpretation']))
            continue
        ok_items = {a['item'] for a in ins.get(rid, {}).get('evidence_assessments', []) if a['critical'] is False}
        age = (d0 - datetime.date.fromisoformat(f['last_seen']['as_of'])).days
        inv = (f['status'] in NOT_REVIEWED or STRENGTH[sig['confidence']['evidence_strength']] < STRENGTH[pol['eligibility']['min_strength_for_action']]
               or any(m not in ok_items for m in sig['confidence']['missing_information']) or age > pol['eligibility']['stale_after_days']
               or sig['interpretation'] == 'data_quality_risk' or sig['interpretation'] not in pol['categories'])
        out[rid] = ('investigate', 'investigate') if inv else ('action', pol['categories'][sig['interpretation']])
    # overlap components: same overlap group, a shared stored record (not a policy record), or a person's financial_overlap link
    live = [f for f in findings if f['status'] not in EXCLUDED]
    parent = {f['finding_id']: f['finding_id'] for f in live}

    def root(x):
        while parent[x] != x:
            x = parent[x]
        return x

    def join(a, b):
        ra, rb = root(a), root(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    groups = {}
    for f in live:
        if f['signal'].get('overlap_group'):
            groups.setdefault('g:' + f['signal']['overlap_group'], []).append(f['finding_id'])
        for e in f['signal']['evidence']:
            if not e['ref'].startswith(POLICY_PREFIXES):
                groups.setdefault('r:' + e['ref'], []).append(f['finding_id'])
        for r in f['relations']:
            if r['kind'] == 'financial_overlap' and r['with'] in parent:
                join(f['finding_id'], r['with'])
    for ids in groups.values():
        for x in ids[1:]:
            join(ids[0], x)
    best = {}
    for f in live:
        rid = 'REC-' + f['finding_id'][4:]
        q = f['signal']['quantification']
        if out[rid][0] == 'close' or q['status'] != 'quantified':
            continue
        k = (f['signal']['interpretation'], root(f['finding_id']))
        cand = (-abs(q['gross_cents']), f['finding_id'], q['gross_cents'])
        best[k] = min(best.get(k, cand), cand)
    totals = {}
    for (interp, _), (_, _, g) in best.items():
        totals[interp] = totals.get(interp, 0) + g
    return out, totals


class TestGolden(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.G, cls.s = GR.run_golden_rec(HERE_ROOT, keep=True)

    def test_the_run_matches_the_golden_file(self):
        with open(GOLDEN, encoding='utf-8') as fh:
            self.assertEqual(json.loads(GR.dumps(self.G)), json.load(fh))

    def test_before_review_everything_is_an_investigation(self):
        self.assertTrue(self.G['first_all_investigate'])
        self.assertEqual(self.G['first']['routes']['action'], 0)

    def test_the_oracle_agrees_on_every_route_category_and_counted_total(self):
        for rk in self.G['run_keys']:
            rec = self.s.get('repro_record', rk).payload
            inputs = {f"{i['kind']}/{i['key']}": self.s.get(i['kind'], i['key'], i['revision']).payload for i in rec['inputs']}
            want, totals = oracle(inputs, rec['params']['as_of'])
            got = {e['rec_id']: (e['route'], e['category']) for e in rec['result']['recommendations']}
            self.assertEqual(got, want)
            self.assertEqual({k: v['potential_gross_counted_cents'] for k, v in rec['result']['totals'].items() if v['counted']}, {k: v for k, v in totals.items()})

    def test_gates_hold_on_the_synthetic_builder(self):
        self.assertEqual(self.G['submissions'][0][1], 'submitted')
        self.assertEqual(self.G['submissions'][1][1], 'NOT_SUBMITTABLE')
        self.assertTrue(all(self.G['replay']))
        self.assertTrue(all(ok for _, ok in self.G['reconstruct_first_version']))
        self.assertEqual(self.G['tenant_isolation'], {'zero_two_recommendations': 0, 'zero_two_sees_run': False})
        self.assertTrue(self.G['audit_chain_ok'])


if __name__ == '__main__':
    unittest.main()
