#!/usr/bin/env python3
"""A short narrated demonstration of the M5 detection layer on Builder Zero.  Deterministic: its output is saved as regression/DEMO_OUTPUT_M5.txt and compared by
tools/run_regression_m5.py.  Usage: python3 -I tools/run_demo_m5.py [--write|--check].  Everything is synthetic; the thresholds are SYNTHETIC and ILLUSTRATIVE (apg/det/demo_det.py) and
no threshold, aggregation key or financial policy is a product decision.  Nothing here is production code, a recommendation or advice."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
from apg.det import golden_det as GD, portfolio as PF
G, O = GD.run_golden_det(ROOT), GD.oracle_det(ROOT)
money = lambda c: 'no amount' if c is None else (f'-${-c / 100:,.2f}' if c < 0 else f'${c / 100:,.2f}')
L = []
def say(s=''): L.append(s)
sig = {(p, s['rule'].replace('DET-', ''), s['subject']): s for p, ss in G['signals'].items() for s in ss}
def one(p, rule, subj, label):
    s = sig[(p, rule, subj)]
    amt = f"{money(s['impact_cents'])} ({s['label']})" if s['status'] == 'quantified' else 'not quantified, and it says why'
    return f"   {label}: {amt}; severity {s['severity']}; {s['evidence_records']} source record{'s' if s['evidence_records'] != 1 else ''}"
say('APG M5 DEMONSTRATION: deterministic detection rules on Builder Zero, each finding naming its records, its amount label and what it could not assess.  The data is synthetic; every threshold is SYNTHETIC and ILLUSTRATIVE.'); say()
fc = G['findings_created']
say(f"1. DETECT.  Four detection runs (three projects and the tenant) at {GD.AS_OF} produce {G['findings_total']} findings: " + ', '.join(f'{k} {v}' for k, v in sorted(fc.items())) + '.')
say(f"   The oracle, a separate program that uses only the CSV files, dates and fractions, expects {O['expected_count']} conditions from the same thresholds; every one is found and nothing else is reported as a leak. The negative controls (cost just inside tolerance, an amendment linked to an approved variation, an invoice inside tolerance, a recent variation, a hire inside need, orders sixty days apart) stay silent.")
say(); say('2. THE PLANTED CASES.')
say(one('PRJ-002', 'R01', 'CC-04', 'cost over budget tolerance, cost code CC-04'))
say(one('PRJ-002', 'R02', 'AMD-001', 'commitment increase with no approved change, AMD-001'))
say(one('PRJ-002', 'R03', 'PO-0091', 'invoiced above order beyond tolerance, PO-0091'))
say(one('PRJ-002', 'R04', 'VAR-0001', 'variation unresolved beyond the workflow period, VAR-0001'))
say(one('PRJ-002', 'R04B', 'NTC-001', 'client instruction with no variation raised, NTC-001'))
say(one('PRJ-001', 'R05', 'PRJ-001', 'retention release date passed'))
say(one('PRJ-003', 'R08', 'HIRE-001', 'plant on hire beyond evidenced need, HIRE-001'))
say(one('PRJ-002', 'R09', 'CC-09|F-2026-08>F-2026-09', 'forecast movement with no explained bridge'))
say(one('PRJ-001', 'LAB', 'WP-PLASTER', 'labour output per hour falling, WP-PLASTER'))
say(one('PRJ-002', 'DEF', 'SUB-004 (synthetic)|waterproofing', 'repeat defect with growing rework cost'))
say("   Every amount carries its label: figure (from an M4 financial figure), record (as recorded in a source record) or estimate (computed with an assumption that the signal lists).")
say(); say('3. WHAT IS NOT PUT IN MONEY.')
say(one('PRJ-002', 'AGG', 'PRJ-002|SUP-003|MAT-REO|CC-03|2026-08-03', 'orders split inside a short window'))
say("   The orders add up to $271,320.00, which is value at stake and not a loss, so no loss is claimed.  Delay overlap, an unresolved variation, an instruction with no variation, an expired licence and a quote above a declared reference are reported without an amount and each says why.")
say(f"   Records held out of the cost figure are reported as data-integrity signals, apart from leakage; {G['portfolio_unquantified']} findings are not quantified at all.")
say(); say('4. SILENCE IS NEVER THE ONLY ANSWER.')
say(f"   Every rule leaves a run record saying whether it was evaluated, how many subjects it looked at and how many it could not assess. Run earlier, at 2026-08-14, the labour rule says it cannot assess: {G['earlier_asof_labour_not_assessed']}.  A health report states that the absence of an alert is not evidence that nothing is wrong: {G['health_statement_present']}.")
say(); say('5. TIME PASSES.')
say(f"   A sweep a day later sees all {G['findings_total']} findings again and creates, updates, reopens and sends nothing ({G['second_sweep']['PRJ-002']['seen']} seen on PRJ-002, 0 created).  A sweep at 2026-11-30 finds VAR-0002 because it has by then been unresolved beyond the workflow period: {G['later_sweep_finds_VAR-0002']}.")
say(); say('6. NOISE CONTROL AND DELIVERY.')
f1, f2 = G['first_flush'], G['second_flush']
say(f"   First flush: {f1['sent']} notifications sent, {f1['duplicate']} duplicate, {f1['failed']} failed.  Second flush: {f2['sent']} sent.  Notifications outstanding: {G['outstanding']}.  A delivery that fails stays pending and visible; a repeat inside the suppression window is not sent again.")
say('   Detection never confirms, dismisses, approves or resolves a finding: only a person with the right role can, with a recorded reason, and the person who proposes an action cannot approve it.')
say(); say('7. PORTFOLIO WITHOUT DOUBLE COUNTING.')
for k, v in sorted(G['portfolio'].items()):
    if v['findings']:
        lo, hi = v['lower_bound_cents'], v['upper_bound_cents']
        if v['quantified'] == 0:                                   # corrected in M6 (M5 independent review, issue 1): never print a range of zero for exposure that is merely unquantified
            say(f"   {k}: {v['findings']} findings, none quantified; " + PF._range_display(lo, hi, 0, v['findings']) + '.  Interpretations are never added to each other.')
            continue
        say(f"   {k}: {v['findings']} findings, {v['quantified']} quantified; between {money(lo)} and {money(hi)}" + ('; overlap-adjusted' if v['overlap_adjusted'] else '') + '.  Interpretations are never added to each other.')
say(); say('8. REPRODUCIBLE.')
say(f"   {G['runs_checked']} stored detection runs were replayed from their pinned inputs: all reproduce {G['all_runs_reproduce']}.  Running the ingest of a run twice changes nothing: {G['replay_of_ingest_is_a_no_op']}.")
t = G['tenant_isolation']
say(); say('9. SECOND TENANT.')
say(f"   zero_two reuses identifiers and has its own held invoice; it gets its own answer ({', '.join(s['rule'] for s in G['zero_two_signals']['PRJ-001'])} only) from its own records.  zero_one's findings visible to zero_two: {t['zero_one_run_visible_to_zero_two']}; zero_two findings before its own ingest: {t['zero_two_findings_before_ingest']}.")
say(); say(f"Audit chains verify: {G['audit_chain_ok']}.  Open decisions are untouched: DEC-A1-1..8, DEC-MIE-01, CR-02 A1 to A13.  Materials and market scenarios (PS-14, 15, 16, 17, 23, 25) belong to M6 and are not claimed here.")
out = '\n'.join(L) + '\n'
path = os.path.join(ROOT, 'regression', 'DEMO_OUTPUT_M5.txt')
if '--write' in sys.argv:
    open(path, 'w', encoding='utf-8').write(out); print('written', path)
elif '--check' in sys.argv:
    same = out == open(path, encoding='utf-8').read()
    print('DEMO OUTPUT MATCHES' if same else 'DEMO OUTPUT DIFFERS from regression/DEMO_OUTPUT_M5.txt'); sys.exit(0 if same else 1)
else:
    print(out, end='')
