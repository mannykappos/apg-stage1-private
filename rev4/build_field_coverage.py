"""Data Readiness revision 4 (shared with the Data Supply System design): field-level coverage of every current rule and figure (M4, detection, M6).  Builder work (Claude), not independent.
For every row of revision 4's RULE_INPUT_CONTRACTS.csv, each field name in its 'record kinds and fields' column is attributed to the record kind
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
Anything else is a GAP.  The script fails on a gap.  This first check does not cover the 'configuration or parameter' column (financial
policy E90, rule settings N01, the cost-code map E04, the authority register E03; the second output lists them as setting rows) or fields
the contracts do not name; authority and verification are listed per field in the second output, not tested.
Second output, FIELD_SUPPLY_ROUTES.csv: one row per record kind and field the contracts read (the checked pairs above), with the entity, its
ways in and their status (from ENTITY_REGISTER.csv), whether the field is material, the verification route of each way in (design, from the
Data Supply System draft 7), and what stage 1 does today for source authority and verification (from the intake code: ingest/specs.py SPECS
are the reference intake's 11 kinds: field authority for the material field of 6 of them, record-level duplicate, supplier or link checks
on ap_invoice, credit_note, po_amendment, purchase_order and supplier_quote, field validation only for budget_line, fx_rate,
market_observation and supplier; the other 24 kinds go through fin/intake.py, with no authority or reconciliation).  Corrected after the
scoped re-check of revision 4 (S1, S2, M6 moq, M14).
usage: python3 -I build_field_coverage.py <folder with RULE_INPUT_CONTRACTS.csv and FIELD_REGISTER.csv>"""
import csv, re, sys, collections
d = sys.argv[1]
R = list(csv.DictReader(open(f'{d}/RULE_INPUT_CONTRACTS.csv')))
reg = collections.defaultdict(set)
for f in csv.DictReader(open(f'{d}/FIELD_REGISTER.csv')):
    reg[f['record_kind']].add(f['field'])
KNOWN = {'retention_event': 'person-entered record', 'duplicate_of': 'intake state', 'invoice_lines': 'calculation output',
         'retention_carrying': 'calculation output', 'security_carrying': 'calculation output', 'overdue_receivables': 'calculation output',
         'instruction_types': 'setting (N01)', 'payment_days': 'a quote_term term_name (value in value_text)',
         'deposit_bps': 'a quote_term term_name (value in value_text)', 'pack_size': 'a quote_term term_name (value in value_text)',
         'moq': 'a quote_term term_name (value in value_text)'}
ALIAS = {('ap_invoice', 'amount'): 'amount_ex_gst_cents', ('credit_note', 'amount'): 'amount_ex_gst_cents',
         ('purchase_order', 'amount'): 'amount_ex_gst_cents', ('po_amendment', 'delta'): 'delta_cents',
         ('supplier', 'supplier'): 'supplier_name', ('purchase_order', 'supplier'): 'supplier_ref'}
# material fields: the 'material' tuples of the intake specs (apg/ingest/specs.py SPECS, apg/fin/intake.py FIN_SPECS, apg/det/intake.py DET_SPECS,
# apg/mkt/intake.py MKT_SPECS), copied here; a material value read from a document needs a person's verification (S04 s12)
MATERIAL = {'ap_invoice': {'amount_ex_gst_cents'}, 'credit_note': {'amount_ex_gst_cents'}, 'payment': {'amount_cents'}, 'purchase_order': {'amount_ex_gst_cents'},
            'po_amendment': {'delta_cents'}, 'supplier_quote': {'unit_rate_minor_units'}, 'pm_invoice': {'amount_ex_gst_cents'}, 'budget_line': {'budget_cents'},
            'contract': {'original_contract_cents'}, 'ctc_line': {'cost_to_complete_cents'}, 'retention': {'retention_held_cents'}, 'security': {'face_value_cents'},
            'facility': {'limit_cents', 'drawn_cents', 'rate_bps'}, 'bank_txn': {'amount_cents'}, 'compliance': {'expiry_date'}, 'notice': {'notice_date'},
            'delay_event': {'start_date'}, 'plant_hire': {'rate_cents_per_day', 'on_hire_date'}, 'timesheet': {'ordinary_hours', 'work_date'},
            'work_output': {'quantity', 'week_start'}, 'defect': {'raised_date'}, 'material': {'unit_text'}, 'material_demand': {'quantity', 'required_date'},
            'delivery': {'qty_delivered', 'delivery_date'}, 'spec_requirement': {'material_ref'}, 'quote_reading': {'value_text'},
            'quote_tier': {'unit_rate_minor_units', 'min_quantity'}, 'quote_term': {'value_text'}, 'import_check': {'status_text'}}
M4_KINDS = ['ap_invoice', 'credit_note', 'purchase_order', 'po_amendment', 'budget_line', 'ctc_line', 'contract', 'variation', 'retention',
            'security', 'facility', 'bank_txn']
LINKED = {'credit_note': 'through the invoice it credits', 'po_amendment': 'through its purchase order',
          'bank_txn': 'through the retention event that names it', 'facility': 'organisation-level'}
ENT, WAYS = {}, {}
for e in csv.DictReader(open(f'{d}/ENTITY_REGISTER.csv')):
    m = re.match(r'\s*(?:partial|covered|partly):\s*([a-z_]+)', e['APG today (record kind: fields)'])
    if m and m.group(1) in reg and m.group(1) not in ENT:
        ENT[m.group(1)] = e['id']; WAYS[m.group(1)] = e['path status']
OWN = {'purchase_order': 'E21', 'notice': 'E10', 'ap_invoice': 'E23', 'payment': 'E25'}   # kinds another entity also mentions: the entity the kind belongs to
for e in csv.DictReader(open(f'{d}/ENTITY_REGISTER.csv')):
    for k, i in OWN.items():
        if e['id'] == i:
            ENT[k], WAYS[k] = i, e['path status']
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
        if t == 'retention_event':                       # a person-entered record with no field definition yet: its fields are listed, not checked
            cur = 'retention_event'
            other[t] = KNOWN[t]
            continue
        if cur == 'retention_event':
            if t in ('seq', 'actor') or '_' in t:
                other[f'retention_event.{t}'] = 'field of the person-entered record (E77); no field definition yet'
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
        elif cur and t in reg[cur]:                       # a one-word field of the current kind (for example quantity), revision 4 agent check finding 2
            checked.append(f'{cur}.{t}')
        elif cur and (cur, t) in ALIAS:
            checked.append(f'{cur}.{ALIAS[(cur, t)]} ("{t}")')
        elif t in KNOWN:                                  # a one-word known item (moq), scoped re-check M6
            other[t] = KNOWN[t]
    kinds_named = sorted({t for t in toks if t in reg})
    pairs = [x.split(' ')[0] for x in checked if '.' in x.split(' ')[0]]
    mat = sorted({x for x in pairs if x.split('.')[1] in MATERIAL.get(x.split('.')[0], set())})
    out.append({'rule or figure': r['rule or figure'], 'record kinds named': ' '.join(kinds_named) or '-',
                'entity and its ways in (register)': ' | '.join(f'{k} {ENT.get(k, "?")}: {WAYS.get(k, "?")}' for k in kinds_named) or '-',
                'material fields (a person verifies them if read from a document, S04 s12)': ' '.join(mat) or '-',
                'fields checked against their own kind': '; '.join(dict.fromkeys(checked)) or '-',
                'other items and what supplies them': '; '.join(f'{k}: {v}' for k, v in other.items()) or '-',
                'reads records': 'no' if text.strip() == '-' else 'yes'})
with open('FIELD_COVERAGE.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0]), lineterminator='\n'); w.writeheader(); w.writerows(out)
pairs = {x.split(' ')[0] for o in out for x in o['fields checked against their own kind'].split('; ') if x != '-' and '.' in x.split(' ')[0]}   # bare kind.field, without the plain-word note
print('rows', len(out), 'kind.field pairs checked', len(pairs), 'gaps', gaps)
assert not gaps

# ---- second output: one row per record kind and field ----
REF_INTAKE = {'ap_invoice', 'budget_line', 'credit_note', 'fx_rate', 'market_observation', 'payment', 'pm_invoice', 'po_amendment',
              'purchase_order', 'supplier', 'supplier_quote'}      # apg/ingest/specs.py SPECS
# field authority: ingest/reconcile.py calls source_authority.resolve_field only for the 'material' fields of reference kinds that have one,
# and not for the secondary kind pm_invoice (revision 4 agent check, finding 4)
AUTH_RESOLVED = {('ap_invoice', 'amount_ex_gst_cents'), ('credit_note', 'amount_ex_gst_cents'), ('purchase_order', 'amount_ex_gst_cents'),
                 ('po_amendment', 'delta_cents'), ('supplier_quote', 'unit_rate_minor_units'), ('budget_line', 'budget_cents'), ('payment', 'amount_cents')}
NO_MATERIAL = {'fx_rate', 'market_observation', 'supplier'}
# record-level checks (ingest/specs.py composite, strong, supplier_field; ingest/reconcile.py relationship checks): only these 5 kinds get any
RECORD_CHECKS = {'ap_invoice', 'credit_note', 'po_amendment', 'purchase_order', 'supplier_quote'}

def authority_today(k, f):
    if (k, f) in AUTH_RESOLVED:
        return 'field authority resolved by the reference intake (source_authority.resolve_field)'
    if k in RECORD_CHECKS:
        return 'reference intake: record-level duplicate, supplier or link checks; no field-authority check for this field'
    if k in NO_MATERIAL:
        return 'reference intake: field validation only (no duplicate, supplier, link or field-authority check; the kind has no material field)'
    if k in REF_INTAKE:
        return 'reference intake: field validation only (no duplicate, supplier, link or field-authority check for this field)'
    return 'not checked: second delivery loop (fin/intake.py)'

ROUTE = {'T': 'T: intake validation of the mapped file (S04 s8, s10); a template cannot carry a value S04 s12 says a person must verify',
         'D': 'D: a person with the verifier role confirms each material value (S04 s12)',
         'E': 'E: the person entering it is recorded; approval where the register requires it',
         'I': 'I: the feed\'s source registry entry (S04 s4); the same intake checks',
         'S': 'S: a versioned setup answer, approved where the register requires it',
         'P': 'P: person, time and place recorded as evidence',
         'A': 'A: calculated by APG from verified inputs'}
NAME = {e['id']: e['entity'] for e in csv.DictReader(open(f'{d}/ENTITY_REGISTER.csv'))}
readers = collections.defaultdict(list)
for o in out:
    for x in o['fields checked against their own kind'].split('; '):
        b = x.split(' ')[0]
        if '.' in b and o['rule or figure'] not in readers[b]:
            readers[b].append(o['rule or figure'])
def _built(w):
    l, st = w.split(' ')[0], w.split(' ')[-1]
    if st == 'exists':
        return l
    return l + (' (partly: not linked to the intake; accepts none of these fields today)' if l == 'D' else ' (partly)')

rows = []
for b in sorted(readers):
    k, f = b.split('.', 1)
    ways = WAYS.get(k, '?')
    built = sorted(_built(w) for w in ways.split('; ') if w.split(' ')[-1] in ('exists', 'partly'))
    mat = f in MATERIAL.get(k, set())
    letters = [w.split(' ')[0] for w in ways.split('; ')]
    rows.append({'record kind': k, 'field': f, 'read by': '; '.join(readers[b]),
                 'entity': f'{ENT.get(k, "?")} {NAME.get(ENT.get(k, ""), "?")}', 'ways in and status (register)': ways,
                 'built today (exists or partly)': ' '.join(built) or 'none',
                 'material in the intake specs (a proxy for S04 s12; a lower bound)': 'yes' if mat else 'no',
                 'verification route of each way in (design)': ' | '.join(ROUTE[l] for l in letters if l in ROUTE),
                 'source authority today': authority_today(k, f),
                 'verification today': ('asserted by the file: a reading counts as verified when its verified_by differs from extracted_by (mkt/spec.py); not tied to the documents.py control' if k == 'quote_reading'
                                        else 'carried unverified by a synthetic template; the documents.py control is not linked to the intake' if mat
                                        else 'intake validation of a synthetic template only'),
                 'release A must still add (PG-DS-AC-12)': ('one intake with authority and reconciliation for this kind; ' if k not in REF_INTAKE else '')
                     + ('field authority through the approved register; ' if (k, f) not in AUTH_RESOLVED else '')
                     + 'the template checked against a real builder file' + ('; if the value comes from a document, document capture linked into the intake with a person verifying it (S04 s12)' if mat else '')})
# settings: the 'configuration or parameter' column, one row per contract row that names one; the entity is read from the text
PATHS = {e['id']: e['path status'] for e in csv.DictReader(open(f'{d}/ENTITY_REGISTER.csv'))}
TODAY = {'E90': 'held as versioned fin_policy records, counted as approved only once an audited approval exists (schema and approval logic in apg/fin/policy.py); no builder setup question',
         'N01': 'held as versioned policy records (det_policy, mkt_policy, mkt_spec), counted as approved only once an audited approval exists (apg/det/policy.py, apg/mkt/policy.py); no builder setup question, no owner-approved defaults or ranges',
         'E04': 'a cost code is carried on each record; no builder-confirmed map',
         'E03': 'an in-code register object passed to reconciliation (source_authority.py); its approval is asserted on the object, not audited; no builder setup',
         'E20': 'supplier records through the reference intake (the supplier kind)'}
for r in R:
    t, rule = r['configuration or parameter'].strip(), r['rule or figure']
    if not t or t == '-':
        continue
    det = bool(re.match(r'(R\d|AGG|D0|DLY|LAB|DEF|every detection)', rule))
    ents = []
    if 'Source Authority Register' in t: ents.append('E03')
    if 'cost-code map' in t: ents.append('E04')
    if 'supplier list (E20)' in t: ents.append('E20')
    if 'E90' in t or 'status_map' in t or rule.startswith('M4') or rule.startswith('every M4'): ents.append('E90')
    if 'N01' in t or (det and re.sub(r'(po|variation)_status_map|and|;|\s', '', t)): ents.append('N01')
    ents = list(dict.fromkeys(e for e in ents if not (e == 'E90' and ('Source Authority Register' in t or 'cost-code map' in t))))
    assert ents, rule
    for e in ents:
        rows.append({'record kind': 'setting', 'field': t, 'read by': rule, 'entity': f'{e} {NAME[e]}',
                     'ways in and status (register)': PATHS[e], 'built today (exists or partly)': ' '.join(sorted(
                         _built(w) for w in PATHS[e].split('; ') if w.split(' ')[-1] in ('exists', 'partly'))) or 'none',
                     'material in the intake specs (a proxy for S04 s12; a lower bound)': 'no', 'verification route of each way in (design)': ' | '.join(ROUTE[w.split(' ')[0]] for w in PATHS[e].split('; ') if w.split(' ')[0] in ROUTE) if e == 'E20' else ROUTE['S'],
                     'source authority today': 'supplier records are sourced data: reference intake (the supplier kind), field validation only; no field-authority check' if e == 'E20'
                         else 'not applicable: a setting is approved, not sourced', 'verification today': TODAY[e],
                     'release A must still add (PG-DS-AC-12)': 'the setup question, versioned; defaults and ranges approved by the owner, accepted by the builder\'s approver, every change recorded (decision 9)'
                         if e == 'N01' else 'a supplier template checked against a real builder file' if e == 'E20'
                         else 'the setup question through the intake, versioned and approved where the register requires it'})
with open('FIELD_SUPPLY_ROUTES.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)
M = 'material in the intake specs (a proxy for S04 s12; a lower bound)'
fr = [r for r in rows if r['record kind'] != 'setting']
print('field supply routes', len(rows), 'fields', len(fr), 'entities', len({r['entity'] for r in fr}), 'settings rows', len(rows) - len(fr),
      'material', sum(r[M] == 'yes' for r in fr), 'authority', collections.Counter(r['source authority today'][:30] for r in fr),
      'built', collections.Counter(r['built today (exists or partly)'] for r in fr), 'settings by entity', collections.Counter(r['entity'][:3] for r in rows if r['record kind'] == 'setting'),
      'unknown entity', sum(r['entity'].startswith('?') for r in rows))
assert not any(r['entity'].startswith('?') for r in rows)

