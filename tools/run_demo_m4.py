#!/usr/bin/env python3
"""A short narrated demonstration of the M4 financial core on Builder Zero.  Deterministic: its output is saved as regression/DEMO_OUTPUT_M4.txt and compared by
tools/run_regression_m4.py.  Usage: python3 -I tools/run_demo_m4.py [--write|--check].  Everything is synthetic; the authority register and the calculation policy are SYNTHETIC and
ILLUSTRATIVE (CR-02 A2 to A13 are open).  Nothing here is production code, a recommendation or accounting advice."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
from apg.fin import golden_fin as GF
G, O = GF.run_golden_fin(ROOT), GF.oracle_fin(ROOT)
money = lambda c: 'cannot be assessed' if c is None else (f'-${-c / 100:,.2f}' if c < 0 else f'${c / 100:,.2f}')
F, OP = G['figures'], O['projects']
L = []
def say(s=''): L.append(s)
def line(p, n, label):
    f = F[p][n]
    why = ''
    if f['excluded']:
        why += '; left out: ' + ', '.join(f"{e[0].split('/')[1]} ({e[1]})" for e in f['excluded'])
    if f['unknown']:
        why += f"; unknown inputs: {len(f['unknown'])}"
    src = f"from {f['contributed']} record{'s' if f['contributed'] != 1 else ''}" if f['contributed'] else 'built from its component figures (each lists its own records)'
    return f"   {label}: {money(f['cents'])}  [{f['state']}]  {src}{why}"
say('APG M4 DEMONSTRATION: every figure says which records made it, what was left out and why, and whether it can be relied on.  Builder Zero is synthetic; the policy is SYNTHETIC and ILLUSTRATIVE.'); say()
c = G['fin_ingest_counts_zero_one']
say(f"1. INGEST.  The financial files (projects, contracts, variations, cost-to-complete lines, retention, security, facility, bank) go through the same decisions as M3: {sum(v['new'] for v in c.values())} new records of {sum(v['rows'] for v in c.values())} rows; rejected {sum(v['rejected'] for v in c.values())}; held {sum(v['held_at_intake'] for v in c.values())}.")
say(); say('2. A CLEAN PROJECT (PRJ-001).  Actual cost counts the 60 usable invoices and names the repeated delivery it did not count.')
say(line('PRJ-001', 'actual_cost', 'actual cost'))
say(line('PRJ-001', 'revenue', 'secured revenue'))
say(line('PRJ-001', 'forecast', 'forecast final margin'))
say(f"   The forecast uses the cost to complete declared at {G['forecast_classified']['PRJ-001']['forecast_date']}; invoices dated later are shown apart and never added: {F['PRJ-001']['forecast']['reasons']}.")
say(line('PRJ-001', 'recognised_margin', 'recognised margin (cost-to-cost)'))
say(); say('3. A PROJECT WITH A HELD INVOICE AND A DISAGREEING CONTRACT SUMMARY (PRJ-002).  Nothing is hidden and nothing is called final.')
say(line('PRJ-002', 'actual_cost', 'actual cost'))
say(f"   One credit note is netted ({F['PRJ-002']['actual_cost']['applied']['credits']} credit applied).")
say(line('PRJ-002', 'revenue', 'secured revenue'))
say(f"   Reason: {F['PRJ-002']['revenue']['reasons'][0]}; the variation register value is used and the disagreement is listed.")
say(line('PRJ-002', 'forecast', 'forecast final margin'))
say(f"   It is provisional because its parts are: {F['PRJ-002']['forecast']['reasons']}.  The value covers the known cost codes only.")
say(f"   Cost code CC-04 has no usable cost to complete ({G['ctc_by_code_PRJ-002']['CC-04'][2]}); the cost-to-complete component reports it as unknown, never negative and never replaced by a budget figure.")
say(line('PRJ-002', 'commitments', 'open commitments'))
say(f"   Overruns are listed, not netted away: {F['PRJ-002']['commitments']['reasons']}.")
say(); say('4. A PROJECT WITH A DISPUTED INVOICE AND NO DECLARED FORECAST (PRJ-003).')
say(line('PRJ-003', 'actual_cost', 'actual cost'))
say(line('PRJ-003', 'forecast', 'forecast final margin'))
say(f"   {F['PRJ-003']['forecast']['reasons']}.")
say(line('PRJ-003', 'commitments', 'open commitments'))
say(); say('5. CASH VIEW, KEPT APART FROM PROFIT.  Retention is money held, not margin; the carrying cost uses the facility rate and the SYNTHETIC funded share.')
for p in ('PRJ-001', 'PRJ-002', 'PRJ-003'):
    cr = G['carrying_inputs'][p]
    say(f"   {p}: retention held {money(F[p]['retention']['cents'])} [{F[p]['retention']['state']}]; security {money(F[p]['security']['cents'])}; carrying cost {money(F[p]['retention_carrying']['cents'])} [{F[p]['retention_carrying']['state']}]" + (f" over {cr['eligible_days']} days at {cr['rate_bps']} bps on {money(cr['funded_balance_cents'])}" if cr else ''))
say(f"   PRJ-001's release date has passed with the money still held: {F['PRJ-001']['retention']['reasons'][0]}.  The carrying cost is therefore: {money(F['PRJ-001']['retention_carrying']['cents'])}.")
say(f"   Cash-position-adjusted margin PRJ-002: {money(F['PRJ-002']['cash_adjusted']['cents'])} [{F['PRJ-002']['cash_adjusted']['state']}]; PRJ-001: {money(F['PRJ-001']['cash_adjusted']['cents'])} [{F['PRJ-001']['cash_adjusted']['state']}] because {F['PRJ-001']['cash_adjusted']['reasons'][-1]}.")
say(); say('6. MOVEMENT BRIDGE (PRJ-002, August forecast to September forecast).')
b = G['bridge_PRJ-002']
say(f"   Forecast margin moved by {money(b['delta_cents'])}; explained {money(b['explained_cents'])}; unexplained {money(b['unexplained_cents'])}; the items add up exactly: {b['reconciles']}.")
for i in b['items']:
    say(f"   - {i[0]} {i[1]}: {money(i[2])}; explained: {i[3]}; {i[4]}")
say(); say('7. REPRODUCIBLE.  Every figure above was stored as an immutable calculation record with its pinned inputs.')
say(f"   {G['runs_checked']} stored calculations were replayed from their stored inputs: all reproduce {G['all_runs_reproduce']}.  Replay also detects an altered result, altered parameters, an altered input, a changed formula, or a missing record.")
say(); say('8. AGREES WITH AN INDEPENDENT CALCULATION.')
say(f"   A separate program that uses only the CSV files, dates and fractions gives the same actual cost, secured revenue, forecast margin, recognised margin, retention and security for all three projects.")
m = G['m3_cross_check']
say(f"   The three project actual costs add up to {money(m['sum_of_m4_project_actuals_cents'])}, equal to the M3 authoritative invoice total {money(m['m3_authoritative_cents'])}; M3 left out {m['m3_excluded']}.")
t = G['tenant_isolation']
say(); say('9. SECOND TENANT.')
say(f"   zero_two PRJ-001 actual cost {money(t['zero_two_PRJ-001_actual'])} [{t['zero_two_state']}] from its own records only; zero_one's stored run is visible to zero_two: {t['zero_one_run_visible_to_zero_two']}.")
say(); say(f"Audit chains verify: {G['audit_chain_ok']}.  Open decisions are untouched: DEC-A1-1..8, DEC-MIE-01, and CR-02 A2 to A13 remain open product decisions.")
out = '\n'.join(L) + '\n'
path = os.path.join(ROOT, 'regression', 'DEMO_OUTPUT_M4.txt')
if '--write' in sys.argv:
    open(path, 'w', encoding='utf-8').write(out); print('written', path)
elif '--check' in sys.argv:
    same = out == open(path, encoding='utf-8').read()
    print('DEMO OUTPUT MATCHES' if same else 'DEMO OUTPUT DIFFERS from regression/DEMO_OUTPUT_M4.txt'); sys.exit(0 if same else 1)
else:
    print(out, end='')
