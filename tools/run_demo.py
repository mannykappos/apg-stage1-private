#!/usr/bin/env python3
"""A short narrated demonstration of the M2 controls on Builder Zero's planted scenarios.  Deterministic: its output is saved as regression/DEMO_OUTPUT.txt and
compared by tools/run_regression.py.  Usage: python3 -I tools/run_demo.py [--write]   (--write refreshes the saved output).
All thresholds are ILLUSTRATIVE (builder_zero/scenarios/test_thresholds.json).  Nothing here is production code or a recommendation."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
from apg import golden
G, O = golden.run_golden(ROOT), golden.oracle(ROOT)
money = lambda c: f'${c / 100:,.2f}'
L = []
def say(s=''): L.append(s)
say('APG M2 DEMONSTRATION on Builder Zero (synthetic).  Thresholds are illustrative test values.'); say()
say('1. TENANCY (PS-24).  Two tenants share identifiers such as INV-0001.')
p = G['PS-24']
say(f"   zero_one stored {p['zero_one_stored']} invoices; zero_two stored {p['zero_two_stored']}.  zero_two sent INV-0001 twice with different content: {p['zero_two_held']} - held, not silently overwritten.")
say(f"   {p['spoof_attempts_refused']} attempts to name tenant zero_one inside tenant zero_two's payload were refused and audited; spoofed record stored: {p['spoofed_record_stored']}.")
say(f"   zero_two can see zero_one-only invoice INV-0187: {not p['zero_two_cannot_see_zero_one_only_ids']}.  Audit chains verify: {G['audit_chain_ok']}.")
say(); say('2. CONFLICTING SOURCES (PS-13).  Accounting says INV-0121 is ' + money(O['conflict_accounting_cents']) + '; the project-management export says ' + money(O['conflict_pm_cents']) + '.')
c = G['PS-13']
say(f"   outcomes: {c['outcomes']}.  Authoritative total {money(c['authoritative_cents'])} over {c['included_count']} invoices; complete: {c['complete']}.")
say(f"   left out and shown to reviewers: {c['excluded']}.  Neither number is in the total; all invoices would be {money(O['zero_one_ex_gst_total_cents'])}.")
say(); say('3. MISSING EVIDENCE (PS-21, PS-26).')
m = G['PS-21']
say(f"   GST total of the invoices that have one: {money(m['gst_known_total_cents'])}; complete: {m['gst_complete']}; left out: {m['gst_left_out']}.  A blank is never counted as zero.")
d = G['PS-26']
say(f"   document values '4O' and '$2.650' read as {d['quantity_text_reads_as']} and {d['rate_text_reads_as']}; an OCR value is {d['ocr_outcome']} (authoritative: {d['ocr_authoritative']}) until a person verifies it.")
say(); say('4. MATERIALITY with illustrative thresholds (PS-10, NC-10).  Policy change kind on first activation: ' + G['policy_change_kind'] + ' (two people, one the materiality owner).')
say(f"   split purchase PO-0093/94/95, each below the single-order threshold: {G['PS-10']}")
say(f"   the same pattern 60 days apart (PO-0096/97/98, chain only): {G['NC-10']}")
w = G['NC-10_whole_project_ledger']['PO-0098']
say(f"   OBSERVATION: against the whole project ledger PO-0098 is {w}, because a project-only key also groups it with {O['po_0098_same_project_orders_within_30_days']}.  The key and window are open decision DEC-A1-8; this engine does not settle it.")
s = G['materiality_summary']
say(f"   whole ledger: {s['material']} of {s['orders']} orders material; reasons {s['by_reason']}.")
say(f"   every answer states the decisions it still leans on: {G['materiality_open_decisions']}.  Stored assessment re-verifies: {G['materiality_assessment_verifies']}.")
say(); say('5. REPRODUCIBILITY.')
r = G['reproducibility']
say(f"   project total over pinned invoice revisions: {r['result']}.  After an input gets a new revision, replay still reproduces it: {r['replay_ok_after_input_changed']}; drift reported: {r['drift']}.")
say(); say('6. STATUS LADDER.')
t = G['status_ladder']
say(f"   a claim of Staging-verified resting on mock-only integration evidence is supported only up to {t['supported_status']!r}; first refusal: {t['first_refusal']}.")
text = '\n'.join(L) + '\n'
path = os.path.join(ROOT, 'regression', 'DEMO_OUTPUT.txt')
if '--write' in sys.argv:
    open(path, 'w', encoding='utf-8').write(text); print('written', path); sys.exit(0)
if '--check' in sys.argv:
    ok = os.path.exists(path) and open(path, encoding='utf-8').read() == text
    print('DEMO OUTPUT MATCHES' if ok else 'DEMO OUTPUT DIFFERS'); sys.exit(0 if ok else 1)
print(text, end='')
