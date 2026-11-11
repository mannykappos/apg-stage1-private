#!/usr/bin/env python3
"""M3 golden-case regression.  Usage: python3 -I tools/run_golden_m3.py [--print] [--write]
Recomputes the Builder Zero ingestion golden cases and the independent oracle (csv module only), compares them with regression/GOLDEN_M3.json, and checks the headline
numbers against the oracle.  --write refreshes the golden file (a reviewed, recorded act)."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
from apg.ingest import golden_m3 as GM
G = GM.run_golden_m3(ROOT); O = GM.oracle_m3(ROOT)
cur = {'oracle': O, 'golden': G}
if '--print' in sys.argv:
    print(GM.dumps(cur)); sys.exit(0)
path = os.path.join(ROOT, 'regression', 'GOLDEN_M3.json')
if '--write' in sys.argv:
    open(path, 'w').write(GM.dumps(cur)); print('written', path); sys.exit(0)
bad = []
def chk(name, ok):
    print(('PASS ' if ok else 'FAIL ') + name); bad.extend([] if ok else [name])
ic = G['invoice_cost_zero_one']
chk('every invoice row was ingested (oracle row count)', G['ingest_counts_zero_one']['ap_invoices.csv']['rows'] == O['invoice_rows'] == G['ingest_counts_zero_one']['ap_invoices.csv']['new'])
chk('authoritative invoice total = oracle total of eligible invoices net of credits', ic['authoritative_cents'] == O['eligible_net_of_credits_ex_gst_cents'] and ic['included_count'] == O['eligible_invoice_count'])
chk('the invoices left out are exactly the oracle\'s duplicate, conflicting and unknown-supplier invoices', sorted(e[0] for e in ic['excluded']) == O['held_invoice_ids'])
chk('PS-11 the duplicate delivery is the oracle\'s duplicate and is counted once', [G['PS-11']['INV-0183'][2]] == ['INV-0001'] and O['duplicate_delivery_ids'] == ['INV-0183'] and G['PS-11']['counted_once'])
chk('PS-11 delivering every file again adds no records', G['PS-11']['redelivery_of_all_files_adds_records'] == 0 and G['PS-11']['whole_files_replayed'][0] == G['PS-11']['whole_files_replayed'][1])
chk('PS-12 credit chain net equals the reissued amount only', G['PS-12']['net_of_the_three_events_cents'] == 5800000 and G['PS-12']['INV-0185'][1] == {'reissue_of_candidate': 'INV-0184'})
chk('PS-13 the conflicting invoice is the oracle\'s and is in no figure', G['PS-13']['INV-0121'][0] == 'quarantined' and O['pm_conflict_ids'] == ['INV-0121'] and not G['PS-13']['in_authoritative_total'] and not G['PS-13']['in_gst_view'])
chk('PS-21 GST total equals the oracle\'s known total net of credits, and names the blank invoice', G['PS-21']['gst_total_cents'] == O['gst_known_net_of_credits_cents_of_eligible'] and [x[0] for x in G['PS-21']['gst_left_out']] == O['gst_blank_ids'] and G['PS-21']['gst_complete'] is False)
chk('PS-21 the order without a cost code is held, not defaulted', G['PS-21']['PO-0099'][0] == 'pending_reconciliation' and O['po_missing_cost_code_ids'] == ['PO-0099'])
chk('PS-22 the unresolved supplier text is the oracle\'s and is not forced to either supplier', O['unknown_supplier_text_ids'] == ['INV-0187'] and G['PS-22']['INV-0187'][1] is None and G['PS-22']['INV-0187'][0] == 'pending_reconciliation')
chk('PS-17 the identical orders are the oracle\'s pair and both are held', sorted(G['PS-17_ingestion_side']) == O['identical_po_groups'][0] and all(v[0] == 'pending_reconciliation' for v in G['PS-17_ingestion_side'].values()))
chk('PS-14 the expired quote and the stale series match the oracle', [k for k, v in {'Q-0004': G['PS-14']['Q-0004']}.items() if v == 'expired'] == O['expired_quote_ids'] and G['PS-14']['MAT-CU_last_observation'] == O['mat_cu_last_observation'])
chk('PS-23 the quote rate and date are the file\'s; the conversion keeps both', G['PS-23']['conversion_at_quote_rate']['rate'] == O['q0005_rate'] and G['PS-23']['conversion_at_quote_rate']['rate_date'] == O['q0005_rate_date'] and G['PS-23']['conversion_at_quote_rate']['source_amount_minor'] == O['q0005_usd_minor'])
chk('PS-24 the repeated identifier in tenant two is the oracle\'s and nothing crossed', G['PS-24']['zero_two_excluded'] == O['zero_two_invoice_ids_with_different_content'] and G['PS-24']['zero_two_conflict_marker_contenders'] == 2 and G['PS-24']['zero_one_untouched_total']
    and G['PS-24']['spoofed_files_refused'] == 3 and not G['PS-24']['spoofed_record_stored'])
chk('PS-26 nothing extracted from a document is authoritative before a person verifies it', all(not f['authoritative_before_verification'] for d in G['PS-26'].values() for f in d.values()))
chk('a reviewer decision changes the total by exactly the corrected amount and leaves the evidence untouched', G['after_reviewer_decision_INV-0121']['delta_cents'] == 7280125 and G['after_reviewer_decision_INV-0121']['evidence_revisions_for_INV-0121'] == 1)
chk('an unscanned file is not ingested', G['scan_gate']['unscanned_code'] == 'SCAN_REQUIRED')
chk('audit chains verify', all(G['audit_chain_ok']))
if not os.path.exists(path):
    print('FAIL golden file missing'); bad.append('golden file')
else:
    want = json.load(open(path))
    same = GM.dumps(cur) == GM.dumps(want)
    chk('computed golden cases equal regression/GOLDEN_M3.json', same)
    if not same:
        for sec in ('oracle', 'golden'):
            for k in sorted(set(want.get(sec, {})) | set(cur[sec])):
                if want.get(sec, {}).get(k) != cur[sec].get(k):
                    print(f'   differs: {sec}.{k}\n     expected {json.dumps(want.get(sec, {}).get(k), sort_keys=True)[:300]}\n     got      {json.dumps(cur[sec].get(k), sort_keys=True)[:300]}')
print(f'\ngolden checks {len(bad)} failed')
print('GOLDEN OK' if not bad else 'GOLDEN REGRESSION')
sys.exit(1 if bad else 0)
