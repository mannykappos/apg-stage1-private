#!/usr/bin/env python3
"""Golden-case regression.  Usage: python3 -I tools/run_golden.py [--print] [--write]
Default: recompute the Builder Zero golden cases and the independent oracle, compare with regression/GOLDEN_M2.json, and check the headline numbers
against the oracle (which uses only the csv module).  --print shows the computed result.  --write refreshes the golden file (a reviewed, recorded act)."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
from apg import golden
G = golden.run_golden(ROOT); O = golden.oracle(ROOT)
cur = {'oracle': O, 'golden': G}
if '--print' in sys.argv:
    print(golden.dumps(cur)); sys.exit(0)
path = os.path.join(ROOT, 'regression', 'GOLDEN_M2.json')
if '--write' in sys.argv:
    open(path, 'w').write(golden.dumps(cur)); print('written', path); sys.exit(0)
bad = []
def chk(name, ok):
    print(('PASS ' if ok else 'FAIL ') + name); bad.extend([] if ok else [name])
# the golden numbers must agree with the independent oracle
chk('invoice rows per tenant match the oracle', G['PS-24']['zero_one_stored'] + len(G['PS-24']['zero_one_held']) * 0 == O['zero_one_invoice_rows'] and G['PS-24']['zero_two_stored'] == O['zero_two_invoice_rows'] - sum(G['PS-24']['zero_two_held'].values()))
chk('PS-13 authoritative total = all accounting invoices minus the conflicted one', G['PS-13']['authoritative_cents'] == O['zero_one_ex_gst_total_cents'] - O['conflict_accounting_cents']
    and [e[0] for e in G['PS-13']['excluded']] == [O['conflict_invoice']] and G['PS-13']['complete'] is False)
chk('PS-13 neither conflicting number is in the total', G['PS-13']['authoritative_cents'] not in (O['zero_one_ex_gst_total_cents'], O['zero_one_ex_gst_total_cents'] - O['conflict_accounting_cents'] + O['conflict_pm_cents']))
chk('PS-21 GST total is the known total and names the blank invoices', G['PS-21']['gst_known_total_cents'] == O['zero_one_gst_total_cents_known'] and sorted(x[0] for x in G['PS-21']['gst_left_out']) == O['zero_one_gst_blank_ids'])
chk('PS-24 the repeated identifier in tenant two is held', sorted(G['PS-24']['zero_two_held']) == O['zero_two_repeated_ids'])
chk('PS-10 split purchase is material in aggregate, NC-10 spaced purchases are not', all(v[0] for v in G['PS-10'].values()) and not any(v[0] for v in G['NC-10'].values()))
chk('NC-10 whole-ledger observation: PO-0098 is grouped with the unrelated orders the oracle finds nearby', G['NC-10_whole_project_ledger']['PO-0098'][0] is True and len(O['po_0098_same_project_orders_within_30_days']) >= 1)
if not os.path.exists(path):
    print('FAIL golden file missing'); bad.append('golden file')
else:
    want = json.load(open(path))
    same = golden.dumps(cur) == golden.dumps(want)
    chk('computed golden cases equal regression/GOLDEN_M2.json', same)
    if not same:
        for sec in ('oracle', 'golden'):
            for k in sorted(set(want.get(sec, {})) | set(cur[sec])):
                if want.get(sec, {}).get(k) != cur[sec].get(k):
                    print(f'   differs: {sec}.{k}\n     expected {json.dumps(want.get(sec, {}).get(k), sort_keys=True)[:300]}\n     got      {json.dumps(cur[sec].get(k), sort_keys=True)[:300]}')
print(f'\ngolden checks {len(bad)} failed')
print('GOLDEN OK' if not bad else 'GOLDEN REGRESSION')
sys.exit(1 if bad else 0)
