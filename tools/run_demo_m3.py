#!/usr/bin/env python3
"""A short narrated demonstration of the M3 ingestion pipeline on Builder Zero.  Deterministic: its output is saved as regression/DEMO_OUTPUT_M3.txt and compared by
tools/run_regression_m3.py.  Usage: python3 -I tools/run_demo_m3.py [--write].  Everything is synthetic; the authority register is a SYNTHETIC demonstration register.
Nothing here is production code or a recommendation."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
from apg.ingest import golden_m3 as GM
G, O = GM.run_golden_m3(ROOT), GM.oracle_m3(ROOT)
money = lambda c: f'${c / 100:,.2f}'
L = []
def say(s=''): L.append(s)
ic = G['invoice_cost_zero_one']
say('APG M3 DEMONSTRATION: messy source files in, validated traceable records or explicit quarantine out.  Builder Zero is synthetic; the register is SYNTHETIC.'); say()
t = G['ingest_counts_zero_one']
say(f"1. INGEST.  11 files, {sum(v['rows'] for v in t.values())} rows for zero_one.  Invoices: {t['ap_invoices.csv']['rows']} rows -> {t['ap_invoices.csv']['new']} stored, {t['ap_invoices.csv']['rejected']} rejected.  Purchase orders: {t['purchase_orders.csv']['new']} stored, {t['purchase_orders.csv']['held_at_intake']} held at intake.")
say(f"   After reconciliation against the approved synthetic register: {G['effective_outcomes_zero_one']}.")
say(); say('2. DUPLICATE DELIVERY (PS-11).  INV-0183 repeats INV-0001 (same supplier, number, amount) in a replay batch.')
p = G['PS-11']
say(f"   INV-0183 -> {p['INV-0183']}; counted once: {p['counted_once']}.  Re-delivering all {p['whole_files_replayed'][0]} files: {p['whole_files_replayed'][1]} recognised as replays, {p['redelivery_of_all_files_adds_records']} records added.")
say(); say('3. CREDITED AND REISSUED (PS-12).')
c = G['PS-12']
say(f"   INV-0184 $60,000.00 is netted by CRN-0001; INV-0185 is shown as a reissue CANDIDATE ({c['INV-0185'][1]}) for lineage only, never merged by software.  Net of the three events: {money(c['net_of_the_three_events_cents'])}.")
say(); say('4. TWO SYSTEMS DISAGREE (PS-13).')
x = G['PS-13']
say(f"   INV-0121 accounting {money(O['conflict_accounting_cents'])} vs PM system {money(O['conflict_pm_cents'])} -> {x['INV-0121']}.  In the authoritative total: {x['in_authoritative_total']}; in the GST view: {x['in_gst_view']}.")
say(); say('5. MISSING CRITICAL VALUES (PS-21).')
m = G['PS-21']
say(f"   PO-0099 (no cost code) -> {m['PO-0099']}.  INV-0186 (no GST) -> {m['INV-0186'][0]}, GST unknown: {m['INV-0186'][1]}.  GST total {money(m['gst_total_cents'])}; complete: {m['gst_complete']}; left out: {[e[0] for e in m['gst_left_out']]}.")
say(); say('6. AMBIGUOUS SUPPLIER (PS-22).')
y = G['PS-22']
say(f"   INV-0187 text 'SYN Metro Steel (synthetic)' resembles two suppliers -> {y['INV-0187']}.  Resembling is never choosing.  In the authoritative total: {y['in_authoritative_total']}.")
say(); say('7. IDENTICAL ORDERS (PS-17, ingestion side).')
say(f"   PO-0100 and PO-0101 are identical: {G['PS-17_ingestion_side']}.  A person decides whether one is a duplicate; detection of the surplus is M5.")
say(); say('8. FRESHNESS AND CURRENCY (PS-14, PS-23).  Freshness limits below are ILLUSTRATIVE.')
f = G['PS-14']; q = G['PS-23']
say(f"   Q-0004 is {f['Q-0004']}; Q-0001 is {f['Q-0001']}; MAT-CU series ends {f['MAT-CU_last_observation']} -> buy-timing assessment {f['buy_timing_assessment']}.  With no limit configured the answer is '{f['unconfigured_policy_says']}', never 'fresh'.")
cv = q['conversion_at_quote_rate']
say(f"   Q-0005: {cv['source_amount_minor']} USD minor units at {cv['rate']} ({cv['rate_date']}) = {cv['converted_minor']} AUD cents; at today's rate {q['conversion_at_latest_rate_for_comparison']['rate']} it would be {q['conversion_at_latest_rate_for_comparison']['converted_minor']}.  Assessment: {q['assessment']}.")
say(); say('9. DOCUMENTS (PS-26).')
d = G['PS-26']['DOC-002']
say(f"   DOC-002 quantity candidates {d['quantity']['candidates']} (ambiguous: {d['quantity']['ambiguous']}), rate candidates {d['unit_rate_cents']['candidates']} (ambiguous: {d['unit_rate_cents']['ambiguous']}); authoritative before a person verifies: {d['quantity']['authoritative_before_verification']}.")
say(); say('10. SECOND TENANT (PS-24).')
k = G['PS-24']
say(f"   zero_two repeats INV-0001 with different content -> {k['zero_two_INV-0001']} with {k['zero_two_conflict_marker_contenders']} contenders kept; its authoritative total is {money(k['zero_two_authoritative_cents'])} excluding {k['zero_two_excluded']}.")
say(f"   {k['spoofed_files_refused']} files naming another tenant were refused whole; spoofed record stored: {k['spoofed_record_stored']}; zero_one's total unchanged: {k['zero_one_untouched_total']}.")
say(); say('11. A PERSON DECIDES.')
r = G['after_reviewer_decision_INV-0121']
say(f"   A reconciler corrects INV-0121 with a recorded reason: total moves by {money(r['delta_cents'])} to {money(r['authoritative_cents'])}; the original evidence keeps {r['evidence_revisions_for_INV-0121']} revision.")
say(); say('12. SCAN GATE.')
say(f"   unscanned file -> {G['scan_gate']['unscanned_code']}; after a clean verdict the same bytes ingest, and a second ingest is a replay: {G['scan_gate']['clean_replay_of_same_bytes']}.")
say(); say(f"Authoritative invoice total before any decision: {money(ic['authoritative_cents'])} over {ic['included_count']} invoices; complete: {ic['complete']}; left out: {[e[0] for e in ic['excluded']]}.")
say(f"Audit chains verify: {G['audit_chain_ok']}.  Open decisions are untouched: DEC-A1-1..8, DEC-MIE-01.")
out = '\n'.join(L) + '\n'
path = os.path.join(ROOT, 'regression', 'DEMO_OUTPUT_M3.txt')
if '--write' in sys.argv:
    open(path, 'w', encoding='utf-8').write(out); print('written', path)
elif '--check' in sys.argv:
    same = out == open(path, encoding='utf-8').read()
    print('DEMO OUTPUT MATCHES' if same else 'DEMO OUTPUT DIFFERS from regression/DEMO_OUTPUT_M3.txt'); sys.exit(0 if same else 1)
else:
    print(out, end='')
