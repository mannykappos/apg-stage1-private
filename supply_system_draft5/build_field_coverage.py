"""APG Data Supply System, draft 5: field-level coverage of the current rules and M4 figures.  Builder work (Claude), not independent.
For every row of revision 3's RULE_INPUT_CONTRACTS.csv, each field name in its 'record kinds and fields' column is attributed to the record kind
named before it in the same row, and checked against THAT kind's fields in FIELD_REGISTER.csv (not against all kinds pooled).
  template field          - a field of that record kind in FIELD_REGISTER.csv (revision 3's inventory of the synthetic stage 1 templates)
  plain-word field        - a plain word the contract uses for a template field of that kind (ALIAS below), checked the same way
  person-entered record   - retention_event: to be recorded by a named person through the release A entry form (today a direct write)
  intake state            - set by the intake itself (duplicate_of, reconciliation state)
  calculation output      - produced by an M4 calculation, not supplied
  setting (N01)           - a detection-rule setting
  linked project          - 'every M4 figure: the record's project_ref': checked on every supplied kind the M4 figures read; a kind without
                            project_ref (credit_note, po_amendment, bank_txn, facility) reaches its project through a linked record or is
                            organisation-level, as listed
Anything else is a GAP.  The script fails on a gap.  It does NOT check the 'configuration or parameter' column (financial policy E90 and
detection-rule settings N01), fields the contracts do not name, or each field's authority and verification requirement.
usage: python3 -I build_field_coverage.py <folder with RULE_INPUT_CONTRACTS.csv and FIELD_REGISTER.csv>"""
import csv, re, sys, collections
d = sys.argv[1]
R = list(csv.DictReader(open(f'{d}/RULE_INPUT_CONTRACTS.csv')))
reg = collections.defaultdict(set)
for f in csv.DictReader(open(f'{d}/FIELD_REGISTER.csv')):
    reg[f['record_kind']].add(f['field'])
KNOWN = {'retention_event': 'person-entered record', 'duplicate_of': 'intake state', 'invoice_lines': 'calculation output',
         'retention_carrying': 'calculation output', 'security_carrying': 'calculation output', 'overdue_receivables': 'calculation output',
         'instruction_types': 'setting (N01)'}
ALIAS = {('ap_invoice', 'amount'): 'amount_ex_gst_cents', ('credit_note', 'amount'): 'amount_ex_gst_cents',
         ('purchase_order', 'amount'): 'amount_ex_gst_cents', ('po_amendment', 'delta'): 'delta_cents',
         ('supplier', 'supplier'): 'supplier_name', ('purchase_order', 'supplier'): 'supplier_ref'}
M4_KINDS = ['ap_invoice', 'credit_note', 'purchase_order', 'po_amendment', 'budget_line', 'ctc_line', 'contract', 'variation', 'retention',
            'security', 'facility', 'bank_txn']
LINKED = {'credit_note': 'through the invoice it credits', 'po_amendment': 'through its purchase order',
          'bank_txn': 'through the retention event that names it', 'facility': 'organisation-level'}
out, gaps = [], []
for r in R:
    text = r['record kinds and fields']
    toks = re.findall(r'[a-z][a-z_]*[a-z]', text)
    cur, checked, other = None, [], {}
    for t in toks:
        if t == 'supplier' and cur == 'purchase_order' and r['rule or figure'].startswith('AGG'):
            checked.append('purchase_order.supplier_ref ("supplier", a grouping key)')   # a grouping key of the order, not the supplier kind
            continue
        if t in reg:
            cur = t
            continue
        if t == 'project_ref' and r['rule or figure'].startswith('every M4 figure'):
            for k in M4_KINDS:
                checked.append(f'{k}.project_ref' if 'project_ref' in reg[k] else f'{k}: {LINKED[k]}')
            continue
        if '_' in t:
            if t in KNOWN:
                other[t] = KNOWN[t]
            elif cur and t in reg[cur]:
                checked.append(f'{cur}.{t}')
            else:
                other[t] = 'GAP'; gaps.append((r['rule or figure'], cur, t))
        elif cur and (cur, t) in ALIAS:
            checked.append(f'{cur}.{ALIAS[(cur, t)]} ("{t}")')
    out.append({'rule or figure': r['rule or figure'], 'record kinds named': ' '.join(sorted({t for t in toks if t in reg})) or '-',
                'fields checked against their own kind': '; '.join(dict.fromkeys(checked)) or '-',
                'other items and what supplies them': '; '.join(f'{k}: {v}' for k, v in other.items()) or '-',
                'reads records': 'no' if text.strip() == '-' else 'yes'})
with open('FIELD_COVERAGE.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0]), lineterminator='\n'); w.writeheader(); w.writerows(out)
pairs = {x for o in out for x in o['fields checked against their own kind'].split('; ') if x != '-' and '.' in x}
print('rows', len(out), 'kind.field pairs checked', len(pairs), 'gaps', gaps)
assert not gaps
