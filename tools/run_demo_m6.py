#!/usr/bin/env python3
"""A short narrated demonstration of the M6 materials-and-market layer on Builder Zero.  Deterministic: its output is saved as regression/DEMO_OUTPUT_M6.txt and compared by
tools/run_regression_m6.py.  Usage: python3 -I tools/run_demo_m6.py [--write|--check].  Everything is synthetic; the thresholds are SYNTHETIC and ILLUSTRATIVE (apg/mkt/demo_mkt.py) and
no threshold, freshness limit, basis or specification is a product decision.  Nothing here is production code, a recommendation, a price forecast or advice.  No market-data provider exists
or is named: market observations are the synthetic Builder Zero file."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
from apg.mkt import golden_mkt as GM
G, O = GM.run_golden_mkt(ROOT), GM.oracle_mkt(ROOT)
money = lambda c: 'no amount' if c is None else (f'-${-c / 100:,.2f}' if c < 0 else f'${c / 100:,.2f}')
L = []
def say(s=''): L.append(s)
sig = {(p, s['rule'].replace('DET-', ''), s['subject']): s for p, ss in G['signals'].items() for s in ss}
def one(p, rule, subj, label):
    s = sig[(p, rule, subj)]
    amt = f"{money(s['impact_cents'])} ({s['label']})" if s['status'] == 'quantified' else 'not quantified, and it says why'
    return f"   {label}: {amt}; severity {s['severity']}; {s['evidence_records']} source record{'s' if s['evidence_records'] != 1 else ''}"
sc = G['scenarios']['PRJ-002']
say('APG M6 DEMONSTRATION: comparable quotes, landed cost, freshness, buy-or-wait scenarios and purchasing signals on Builder Zero.  The data is synthetic; every threshold, limit and specification is SYNTHETIC and ILLUSTRATIVE.')
say('No market-data provider is connected or named, and no price is forecast: a "wait" scenario applies only the price paths written in the procurement policy.'); say()
fc = G['findings_created']
say(f"1. DETECT.  Four procurement runs (three projects and the tenant) at {GM.AS_OF} produce {G['findings_total']} findings: " + ', '.join(f'{k} {v}' for k, v in sorted(fc.items())) + '.')
say(f"   The oracle, a separate program that uses only the CSV files, dates and fractions, expects {O['expected_count']} conditions; every one is found and nothing else is reported. The supplier-performance rule looked at nine suppliers and stayed silent, as the oracle expects.")
say(); say('2. THE PLANTED CASES.')
say(one('tenant', 'MP01', 'MAT-CU|index', 'PS-14 stale market series, copper (168 days old)'))
say(one('tenant', 'MP01', 'MAT-REO|quote', 'PS-14 only quote for reinforcing bar has expired'))
say(one('PRJ-002', 'MP02', 'spec_requirement/SPEC-0001>Q-0003', 'PS-15 a cheaper quote at the wrong specification'))
say("   It is named as not comparable and is not offered as a saving: the cheaper rate is 27,000 cents a unit against 28,730 for the like-for-like offer, and the signal says it must not be recommended.")
say(one('PRJ-002', 'MP03', 'demand/DEM-0001', 'PS-16 uncovered demand whose offers lapse inside the decision window'))
say(one('PRJ-001', 'MP04', 'demand/DEM-0002', 'PS-17 orders above the demand'))
say(one('PRJ-001', 'MP05', 'PO-0100|PO-0101', 'PS-17 identical purchase orders (a suspicion, not proof)'))
say(one('tenant', 'MP06', 'Q-0005', 'PS-23 stated exchange rate 151 days old, 109 bps from the reference'))
say(one('tenant', 'MP07', 'Q-0005', 'PS-23 import checks not resolved (customs classification, duty rate, import permit)'))
say(one('PRJ-001', 'MP09', 'OPP-DEM-0002-Q-0006', 'PS-25 a cheaper current quote for plasterboard'))
say("   PS-25 is reported with no amount: everything needed is already ordered, so there is nothing left to buy at the lower rate. It is never counted as a saving.")
say(); say('3. NO WINNER IS CHOSEN.')
r = G['rankings']
say(f"   Six rankings were built (three requirements, each in a project run and in the tenant run). None is definitive: {sum(1 for v in r.values() if v['status'] == 'indicative')} indicative (the foreign offer is only partly comparable and its import checks are unresolved) and {sum(1 for v in r.values() if v['status'] == 'insufficient_offers')} with fewer than two rankable offers. Every one requires a human approval: {all(v['human_approval_required'] for v in r.values())}.")
say(f"   A gate that fails never lets a definitive ranking through: {G['no_definitive_recommendation_when_a_gate_fails']}.")
say(); say('4. BUY NOW, WAIT, STAGE: SCENARIOS, NOT ADVICE.')
say(f"   For 40 tonnes of steel at quote Q-0001 the total cost (landed price plus storage and financing, with the policy's rates) is {money(sc['demand/DEM-0001|supplier_quote/Q-0001|buy_now'])} to buy now, {money(sc['demand/DEM-0001|supplier_quote/Q-0001|wait:flat'])} to wait with a flat price, {money(sc['demand/DEM-0001|supplier_quote/Q-0001|stage'])} to stage the order in two.")
say(f"   The 'wait' figures are modelled values: the quote lapses before the later order date, so they are labelled as not an offer. The paths down 5% and up 5% give {money(sc['demand/DEM-0001|supplier_quote/Q-0001|wait:down_5pct'])} and {money(sc['demand/DEM-0001|supplier_quote/Q-0001|wait:up_5pct'])}. Scenarios never change the official forecast and are not ranked against each other.")
say(); say('5. WHAT IS NOT PUT IN MONEY.')
pq = G['portfolio']
say(f"   Procurement signals that cannot be quantified say why. Of the {pq['forecast_exposure']['findings'] + pq['potential_opportunity']['findings']} findings in the portfolio view, {pq['forecast_exposure']['unquantified'] + pq['potential_opportunity']['unquantified']} are not quantified and are listed apart from the range. When nothing at all is quantified the view says 'no quantified amount available' instead of printing a range of zero (the M5 display issue the auditor raised; tested in test_det_portfolio.py).")
say(f"   Forecast exposure: {G['portfolio']['forecast_exposure']['range_display']}.  Potential opportunity: {G['portfolio']['potential_opportunity']['range_display']}.")
say("   The three portfolio rate-gap signals come from random synthetic order rates (the copper gap is thousands of percent); they exercise the information boundary and say nothing about any real price.")
say(); say('6. REPRODUCIBLE.')
say(f"   {G['runs_checked']} stored procurement runs were replayed from their pinned inputs: all reproduce {G['all_runs_reproduce']}.  Ingesting a run twice changes nothing: {G['replay_of_ingest_is_a_no_op']}.  Event hooks for the later cross-domain engine (apg-event-1: observation time, effective time, source, project, material, supplier) are written as {sum(G['event_count'].values())} event records; nothing is chained or inferred in M6.")
t = G['tenant_isolation']
say(); say('7. SECOND TENANT.')
say(f"   zero_two reuses identifiers and has no procurement supplements; it gets its own answer ({len(G['zero_two_signals']['tenant'])} market-series warnings, nothing on PRJ-001). zero_one's findings visible to zero_two: {t['zero_one_run_visible_to_zero_two']}; zero_two findings before its own ingest: {t['zero_two_findings_before_ingest']}.")
say(); say(f"Audit chains verify: {G['audit_chain_ok']}.  Open decisions are untouched: DEC-A1-1..8, DEC-MIE-01, CR-02 A1 to A13.  RFC-01 is a proposal under change control; nothing here claims it is approved, and the cross-domain engine (M7 in RFC-01) is not started.")
out = '\n'.join(L) + '\n'
path = os.path.join(ROOT, 'regression', 'DEMO_OUTPUT_M6.txt')
if '--write' in sys.argv:
    open(path, 'w', encoding='utf-8').write(out); print('written', path)
elif '--check' in sys.argv:
    same = out == open(path, encoding='utf-8').read()
    print('DEMO OUTPUT MATCHES' if same else 'DEMO OUTPUT DIFFERS from regression/DEMO_OUTPUT_M6.txt'); sys.exit(0 if same else 1)
else:
    print(out, end='')
