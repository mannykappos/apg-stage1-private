#!/usr/bin/env python3
"""M6 golden-case regression.  Usage: python3 -I tools/run_golden_mkt.py [--print] [--write]
Runs the stored procurement calculations over Builder Zero, recomputes the planted scenarios with the independent oracle (csv module, datetime and Fraction only), and compares both with
regression/GOLDEN_MKT.json.  --write refreshes the golden file (a reviewed, recorded act)."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
from apg.mkt import golden_mkt as GM
G = GM.run_golden_mkt(ROOT); O = GM.oracle_mkt(ROOT); O2 = GM.oracle_mkt(ROOT, 'zero_two')
cur = {'oracle': O, 'oracle_zero_two': O2, 'golden': G}
if '--print' in sys.argv:
    print(GM.dumps(cur)); sys.exit(0)
path = os.path.join(ROOT, 'regression', 'GOLDEN_MKT.json')
if '--write' in sys.argv:
    open(path, 'w').write(GM.dumps(cur)); print('written', path); sys.exit(0)
bad = []
def chk(name, ok):
    print(('PASS ' if ok else 'FAIL ') + name); bad.extend([] if ok else [name])
def raised(signals):
    got = {}
    for scope, sigs in signals.items():
        for s in sigs:
            rid = s['rule'].replace('DET-', '')
            if rid != 'MPD1':
                got[f'{rid}|{scope}|{s["subject"]}'] = s['facts']
    return got
got, want = raised(G['signals']), O['expected']
got2, want2 = raised(G['zero_two_signals']), O2['expected']
chk('every condition the oracle expects is raised, and nothing else is raised by the ten procurement rules (planted positives found, negative controls silent)', set(got) == set(want))
for k in sorted(set(got) | set(want)):
    chk(f'{k}: the raised facts equal the oracle\'s ({want.get(k)!r})', got.get(k) == want.get(k) and k in got and k in want)
for ps, rule in (('PS-14', 'MP01'), ('PS-15', 'MP02'), ('PS-16', 'MP03'), ('PS-17', 'MP04'), ('PS-17', 'MP05'), ('PS-23', 'MP06'), ('PS-23', 'MP07'), ('PS-25', 'MP09')):
    chk(f'{ps} is found by {rule}', any(k.startswith(rule + '|') for k in want) and any(k.startswith(rule + '|') for k in got))
chk('negative controls: no supplier is below a performance level (MP08 silent), and the declared comparable pair Q-0001/Q-0002 raises no comparability warning', not any(k.startswith('MP08|') for k in got) and not any(k.endswith('>Q-0001') or k.endswith('>Q-0002') for k in got))
chk('the buy-now, wait and stage totals of the declared steel offer equal the oracle\'s hand-checkable arithmetic', all(G['scenarios']['PRJ-002'].get(f'demand/DEM-0001|supplier_quote/Q-0001|{n}') == v for n, v in (('buy_now', O['scenario_totals']['buy_now']), ('wait:flat', O['scenario_totals']['wait_flat']), ('stage', O['scenario_totals']['stage']))))
chk('no definitive ranking is produced while the declared steel offers include a partly comparable, stale offer (acceptance: no definitive recommendation passes a gate it should not)', G['rankings']['PRJ-002|demand/DEM-0001']['definitive'] is False and G['no_definitive_recommendation_when_a_gate_fails'])
chk('every ranking says a person must approve', all(v['human_approval_required'] for v in G['rankings'].values()))
chk('no signal is a financial figure without a label, and none is called realised', all((s['status'] == 'unquantified') == (s['gross_cents'] is None) and (s['status'] == 'unquantified' or s['label'] in ('figure', 'record', 'estimate')) for sg in G['signals'].values() for s in sg))
chk('every saving opportunity and portfolio gap is an estimate', all(s['label'] == 'estimate' for sg in G['signals'].values() for s in sg if s['rule'] in ('DET-MP09', 'DET-MP10') and s['status'] == 'quantified'))
chk('every stored procurement run replays, has a valid result and consistent pins', G['all_runs_reproduce'] and G['runs_checked'] == 4)
total = sum(len(v) for v in G['signals'].values())
chk('each signal became exactly one finding on the first ingestion; ingesting a run again is a no-op', sum(G['findings_created'].values()) == total == G['findings_total'] and G['replay_of_ingest_is_a_no_op'])
chk('the portfolio view no longer prints a zero range for unquantified exposure (M5 review issue 1)', all(v['quantified_amount_available'] or 'no quantified amount available' in v['range_display'] for v in G['portfolio'].values()))
t = G['tenant_isolation']
chk('the second builder sees none of the first builder\'s runs, its pins resolve in its own tenant, and no finding crosses', not t['zero_one_run_visible_to_zero_two'] and t['every_zero_two_pin_resolves_in_its_own_tenant'] and t['zero_two_findings_before_ingest'] == 0 and t['zero_one_findings'] == total)
chk('the second builder\'s own signals equal its own oracle', got2 == want2)
chk('audit chains verify', all(G['audit_chain_ok']))
if not os.path.exists(path):
    print('FAIL golden file missing'); bad.append('golden file')
else:
    wantf = json.load(open(path))
    same = GM.dumps(cur) == GM.dumps(wantf)
    chk('computed golden cases equal regression/GOLDEN_MKT.json', same)
    if not same:
        for sec in ('oracle', 'oracle_zero_two', 'golden'):
            for k in sorted(set(wantf.get(sec, {})) | set(cur[sec])):
                if wantf.get(sec, {}).get(k) != cur[sec].get(k):
                    print(f'   differs: {sec}.{k}\n     expected {json.dumps(wantf.get(sec, {}).get(k), sort_keys=True)[:300]}\n     got      {json.dumps(cur[sec].get(k), sort_keys=True)[:300]}')
print(f'\ngolden checks {len(bad)} failed')
print('GOLDEN OK' if not bad else 'GOLDEN REGRESSION')
sys.exit(1 if bad else 0)
