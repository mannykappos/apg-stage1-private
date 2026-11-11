#!/usr/bin/env python3
"""M5 golden-case regression.  Usage: python3 -I tools/run_golden_det.py [--print] [--write]
Runs the stored detection calculations over Builder Zero, recomputes which conditions the demonstration thresholds make a finding with the independent oracle (csv module, datetime and
Fraction only), and compares both with regression/GOLDEN_DET.json.  --write refreshes the golden file (a reviewed, recorded act)."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
from apg.det import golden_det as GD
G = GD.run_golden_det(ROOT); O = GD.oracle_det(ROOT); O2 = GD.oracle_det(ROOT, 'zero_two')
cur = {'oracle': O, 'oracle_zero_two': O2, 'golden': G}
if '--print' in sys.argv:
    print(GD.dumps(cur)); sys.exit(0)
path = os.path.join(ROOT, 'regression', 'GOLDEN_DET.json')
if '--write' in sys.argv:
    open(path, 'w').write(GD.dumps(cur)); print('written', path); sys.exit(0)
bad = []
def chk(name, ok):
    print(('PASS ' if ok else 'FAIL ') + name); bad.extend([] if ok else [name])
FACTS = {'R01': lambda s: s['gross_cents'], 'R02': lambda s: s['gross_cents'], 'R03': lambda s: s['gross_cents'], 'R04': lambda s: (s['extra']['age_days'], s['gross_cents']),
         'R04B': lambda s: s['extra']['age_days'], 'R05': lambda s: (s['gross_cents'], s['extra']['days_late']), 'R06': lambda s: s['extra']['days_to_expiry'],
         'R07': lambda s: s['extra']['unit_difference_cents'], 'R08': lambda s: (s['extra']['days_beyond_need'], s['gross_cents']), 'R09': lambda s: s['gross_cents'],
         'AGG': lambda s: (s['extra']['orders'], s['extra']['aggregate_cents']), 'DLY': lambda s: (s['extra']['overlap_days'], s['extra']['union_days'], s['extra']['sum_of_durations_days']),
         'LAB': lambda s: (s['extra']['decline_bps'], s['gross_cents']), 'DEF': lambda s: (s['extra']['events'], s['gross_cents'], s['extra']['growing'])}
OFACTS = {'R01': lambda f: f['excess_cents'], 'R02': lambda f: f['delta_cents'], 'R03': lambda f: f['excess_cents'], 'R04': lambda f: (f['age_days'], f['value_cents']), 'R04B': lambda f: f['age_days'],
          'R05': lambda f: (f['withheld_cents'], f['days_late']), 'R06': lambda f: f['days_to_expiry'], 'R07': lambda f: f['unit_difference_cents'], 'R08': lambda f: (f['days_beyond_need'], f['cost_cents']),
          'R09': lambda f: f['movement_cents'], 'AGG': lambda f: (f['orders'], f['aggregate_cents']), 'DLY': lambda f: (f['overlap_days'], f['union_days'], f['sum_days']),
          'LAB': lambda f: (f['decline_bps'], f['cost_cents']), 'DEF': lambda f: (f['events'], f['total_cents'], f['growing'])}
def raised(signals):
    got = {}
    for scope, sigs in signals.items():
        for s in sigs:
            rid = s['rule'].replace('DET-', '')
            if rid in FACTS:
                got[f'{rid}|{scope}|{s["subject"]}'] = FACTS[rid](s)
    return got
got, want = raised(G['signals']), {k: OFACTS[k.split('|')[0]](v) for k, v in O['expected'].items()}
got2, want2 = raised(G['zero_two_signals']), {k: OFACTS[k.split('|')[0]](v) for k, v in O2['expected'].items()}
chk('every condition the oracle expects is raised, and nothing else is raised by the thirteen threshold rules (planted positives found, negative controls silent)', set(got) == set(want))
for k in sorted(set(got) | set(want)):
    chk(f'{k}: the raised facts equal the oracle\'s ({want.get(k)!r})', got.get(k) == want.get(k) and k in got and k in want)
chk('the 15 expected conditions are exactly the planted positives of the scenario register that belong to M5 rules', O['expected_count'] == 15 and len(set(k.split("|")[0] for k in want)) == 14)
chk('the two borderline negatives stay silent: cost at 98 percent of budget (NC-01) and an invoice 0.4 percent above its order (NC-03)', O['ratio_bps']['PRJ-002|CC-05'] == 9800 and 'R01|PRJ-002|CC-05' not in got and O['po_over_bps']['PO-0092'] == 40 and 'R03|PRJ-002|PO-0092' not in got)
chk('the approved-variation amendment (NC-02), the recent priced variation (NC-04), the other suppliers (NC-06), the hire inside its need period (NC-08) and the 60-day-apart orders (NC-10) are silent',
    not any(k in got for k in ('R02|PRJ-002|AMD-002', 'R04|PRJ-002|VAR-0002', 'R08|PRJ-003|HIRE-002')) and not any(k.startswith('AGG|PRJ-002|PRJ-002|SUP-010') for k in got)
    and sorted(k for k in got if k.startswith('R06')) == ['R06|tenant|SUP-005|public_liability_insurance', 'R06|tenant|SUP-008|licence'])
chk('the oracle\'s left-out invoices are the held and duplicate deliveries (INV-0121, INV-0183, INV-0187)', O['excluded_invoices'] == ['INV-0121', 'INV-0183', 'INV-0187'])
d01 = sorted(sc for sc, sigs in G['signals'].items() if any(s['rule'] == 'DET-D01' for s in sigs))
chk('a held-record signal accompanies exactly the projects whose cost figure leaves out a held invoice (PRJ-002, PRJ-003)', d01 == ['PRJ-002', 'PRJ-003'])
chk('no signal is a financial figure without a label, and none is called realised', all((s['status'] == 'unquantified') == (s['gross_cents'] is None) and (s['status'] == 'unquantified' or s['label'] in ('figure', 'record', 'estimate')) for sg in G['signals'].values() for s in sg))
def band(c):
    return None if c is None else ('high' if abs(c) >= 25000000 else 'medium' if abs(c) >= 5000000 else 'low')
chk('severity is the demonstration policy band of the amount at stake (low 0, medium 5,000,000, high 25,000,000 cents) and a signal with no amount at stake is unrated', all(s['severity'] == (band(s['impact_cents']) or 'unrated') for sg in G['signals'].values() for s in sg))
chk('every stored detection run replays, has a valid result and consistent pins', G['all_runs_reproduce'] and G['runs_checked'] == 4)
total = sum(len(v) for v in G['signals'].values())
chk('each signal became exactly one finding on the first ingestion', sum(G['findings_created'].values()) == total == G['findings_total'])
chk('each notification was delivered once; the second sweep a day later created, updated and sent nothing', G['first_flush']['sent'] == total and G['first_flush']['failed'] == 0 and G['second_flush'] == {'sent': 0, 'duplicate': 0, 'failed': 0}
    and all(v['created'] == 0 and v['updated'] == 0 and v['reopened'] == 0 for v in G['second_sweep'].values()) and G['delivered_notes'] == total and G['outstanding'] == 0)
chk('ingesting a run a second time is a no-op', G['replay_of_ingest_is_a_no_op'])
chk('a condition that depends only on the passing of time (VAR-0002 past 60 days) is found by a later sweep and not before', G['later_sweep_finds_VAR-0002'] and 'R04|PRJ-002|VAR-0002' not in got)
chk('an earlier as-of date has too few complete weeks for the labour rule, which says so rather than staying silently clean', G['earlier_asof_labour_not_assessed'])
chk('the portfolio view keeps interpretations apart and shows a range where findings share a record', all(v['lower_bound_cents'] <= v['upper_bound_cents'] for v in G['portfolio'].values()) and 'total' not in G['portfolio'])
chk('the health report states that no alert is not proof of no issue', G['health_statement_present'])
t = G['tenant_isolation']
chk('the second builder sees none of the first builder\'s runs, its pins resolve in its own tenant, and no finding crosses', not t['zero_one_run_visible_to_zero_two'] and t['every_zero_two_pin_resolves_in_its_own_tenant'] and t['zero_two_findings_before_ingest'] == 0 and t['zero_one_findings'] == total)
chk('the second builder\'s own signals equal its own oracle (it has its own records, and its own identifiers that collide with the first builder\'s)', got2 == want2)
chk('audit chains verify', all(G['audit_chain_ok']))
if not os.path.exists(path):
    print('FAIL golden file missing'); bad.append('golden file')
else:
    wantf = json.load(open(path))
    same = GD.dumps(cur) == GD.dumps(wantf)
    chk('computed golden cases equal regression/GOLDEN_DET.json', same)
    if not same:
        for sec in ('oracle', 'oracle_zero_two', 'golden'):
            for k in sorted(set(wantf.get(sec, {})) | set(cur[sec])):
                if wantf.get(sec, {}).get(k) != cur[sec].get(k):
                    print(f'   differs: {sec}.{k}\n     expected {json.dumps(wantf.get(sec, {}).get(k), sort_keys=True)[:300]}\n     got      {json.dumps(cur[sec].get(k), sort_keys=True)[:300]}')
print(f'\ngolden checks {len(bad)} failed')
print('GOLDEN OK' if not bad else 'GOLDEN REGRESSION')
sys.exit(1 if bad else 0)
