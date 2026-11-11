#!/usr/bin/env python3
"""M4 golden-case regression.  Usage: python3 -I tools/run_golden_fin.py [--print] [--write]
Runs the stored financial calculations over Builder Zero, recomputes the headline numbers with the independent oracle (csv module, datetime and Fraction only), and compares both with
regression/GOLDEN_FIN.json.  --write refreshes the golden file (a reviewed, recorded act)."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
from apg.fin import golden_fin as GF
G = GF.run_golden_fin(ROOT); O = GF.oracle_fin(ROOT)
cur = {'oracle': O, 'golden': G}
if '--print' in sys.argv:
    print(GF.dumps(cur)); sys.exit(0)
path = os.path.join(ROOT, 'regression', 'GOLDEN_FIN.json')
if '--write' in sys.argv:
    open(path, 'w').write(GF.dumps(cur)); print('written', path); sys.exit(0)
bad = []
def chk(name, ok):
    print(('PASS ' if ok else 'FAIL ') + name); bad.extend([] if ok else [name])
F, OP = G['figures'], O['projects']
for p in GF.PROJECTS:
    f, o = F[p], OP[p]
    chk(f'{p} actual cost equals the oracle; provisional exactly when the oracle holds an invoice for the project', f['actual_cost']['cents'] == o['actual_cents'] and (f['actual_cost']['state'] == 'provisional') == o['actual_provisional'])
    chk(f'{p} the invoices left out of actual cost are the oracle\'s held and duplicate invoices for the project', sorted(e[0].split("/")[1] for e in f['actual_cost']['excluded']) == sorted(o['held_for_project'] + [i for i in O['duplicate_delivery_ids'] if p == 'PRJ-001']))
    chk(f'{p} secured revenue equals the oracle; provisional exactly when the contract summary disagrees with the register', f['revenue']['cents'] == o['revenue_cents'] and (f['revenue']['state'] == 'provisional') == (not o['revenue_summary_agrees']))
    fc = G['forecast_classified'][p]
    chk(f'{p} forecast version, date, actual, cost-to-complete and final cost equal the oracle (known part)', (fc['forecast_version'] or None) in (o['forecast']['version'], '(derived from budget)') and fc['forecast_date'] == o['forecast']['date']
        and fc['actual_cents'] == o['forecast']['actual_to_forecast_date_cents'] and fc['ctc_cents'] == o['forecast']['ctc_known_cents'] and fc['ffc_cents'] == o['forecast']['ffc_known_cents'])
    chk(f'{p} forecast final margin equals the oracle; complete exactly when no cost code is unknown', f['forecast']['cents'] == o['forecast']['margin_on_known_cents'] and (f['forecast']['state'] == 'authoritative') == (o['forecast']['complete'] and not o['actual_provisional'] and o['revenue_summary_agrees'] and o['forecast']['version'] is not None))
    chk(f'{p} recognised margin equals the oracle', f['recognised_margin']['cents'] == o['recognised_on_known']['margin_cents'] and G['recognised_classified'][p]['recognised_revenue_cents'] == o['recognised_on_known']['revenue_cents'])
    chk(f'{p} retention and security face values equal the oracle', f['retention']['cents'] == o['retention_cents'] and f['security']['cents'] == o['security_cents'])
    chk(f'{p} carrying cost equals the oracle (cannot be assessed exactly when the release date has passed with money withheld)', f['retention_carrying']['cents'] == o['carrying_cents'] and (f['retention_carrying']['state'] == 'cannot_assess') == (o['carrying_cents'] is None))
    chk(f'{p} cash-position-adjusted margin equals the oracle', f['cash_adjusted']['cents'] == o['cash_adjusted_on_known'])
chk('the M4 per-project actual costs add up to the oracle total and to the M3 authoritative invoice total', G['m3_cross_check']['sum_of_m4_project_actuals_cents'] == O['sum_of_project_actuals_cents'] == G['m3_cross_check']['m3_authoritative_cents'])
chk('the invoices M3 leaves out are the oracle\'s held and duplicate invoices', G['m3_cross_check']['m3_excluded'] == sorted(O['held_invoice_ids'] + O['duplicate_delivery_ids']))
chk('every stored calculation replays, has a valid figure and consistent pins', G['all_runs_reproduce'] and G['runs_checked'] == 27)
b = G['bridge_PRJ-002']
chk('the PRJ-002 movement bridge reconciles exactly and surfaces the unexplained cost-to-complete move', b['reconciles'] and b['delta_cents'] == -31000000 and b['unexplained_cents'] == -31000000 and b['explained_cents'] == 0)
t = G['tenant_isolation']
chk('the second builder sees none of the first builder\'s figures and has its own', not t['zero_one_run_visible_to_zero_two'] and t['every_zero_two_pin_resolves_in_its_own_tenant'] and t['zero_two_PRJ-001_actual'] != t['zero_one_PRJ-001_actual'])
chk('audit chains verify', all(G['audit_chain_ok']))
if not os.path.exists(path):
    print('FAIL golden file missing'); bad.append('golden file')
else:
    want = json.load(open(path))
    same = GF.dumps(cur) == GF.dumps(want)
    chk('computed golden cases equal regression/GOLDEN_FIN.json', same)
    if not same:
        for sec in ('oracle', 'golden'):
            for k in sorted(set(want.get(sec, {})) | set(cur[sec])):
                if want.get(sec, {}).get(k) != cur[sec].get(k):
                    print(f'   differs: {sec}.{k}\n     expected {json.dumps(want.get(sec, {}).get(k), sort_keys=True)[:300]}\n     got      {json.dumps(cur[sec].get(k), sort_keys=True)[:300]}')
print(f'\ngolden checks {len(bad)} failed')
print('GOLDEN OK' if not bad else 'GOLDEN REGRESSION')
sys.exit(1 if bad else 0)
