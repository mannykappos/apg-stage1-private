"""APG Data Supply System, draft 2: the entity supply plan.  Builder work (Claude), not independent.
Reads revision 3's ENTITY_REGISTER.csv and RULE_INPUT_CONTRACTS.csv; writes SUPPLY_PLAN.csv and RELEASE_A_COVERAGE.csv.

Release rules (stated in the doc and applied here mechanically):
  A  - entities whose records a current rule or M4 figure actually reads (contract rows whose 'record kinds and fields' is not '-');
     - the configuration the contracts name by entity id, plus N01 (detection-rule settings, which no register entity holds);
     - the inputs of the current M6 market figures (the record kinds the M6 code ingests; their contracts are still to be written);
     - what the intake itself needs before it will use those records: E20 supplier list (the reference intake holds supplier-bearing
       records without it), E05 organisation, users and roles (every approval needs a role; may come from the Anchor platform);
     - the intake's own records (E01 provenance, E02 source registry, E03 authority register) and the readiness record (E89).
  B  - entities that close a known limit of a current rule or figure (the contracts' last column, ranges such as 'E47 to E50' expanded),
       not already in A.  Supplying them changes nothing until the consuming rule or figure is changed under its own change request.
  later    - the rest of the register: inputs of insights not built yet.
  optional - the developer entities (class V, outside the locked blueprint).
Minimum way in: Level 1 only (T import template, D document capture, E entry screen, S setup question, A record APG derives).
  Configuration takes S where listed.  An APG-internal entity takes A only when the register lists A and no entry screen: where people
  record or decide it (E listed), the entry screen is the minimum.  Otherwise the most-built path wins (exists, partly, proposed), ties
  T, D, E, S, A.  P (phone) and I (integration) are never the minimum."""
import csv, re, sys
REV3 = sys.argv[1]
E = list(csv.DictReader(open(f'{REV3}/ENTITY_REGISTER.csv')))
R = list(csv.DictReader(open(f'{REV3}/RULE_INPUT_CONTRACTS.csv')))

def ids(s):
    out = set(re.findall(r'E\d\d', s))
    for a, b in re.findall(r'E(\d\d) to E(\d\d)', s):
        out |= {f'E{n:02d}' for n in range(int(a), int(b) + 1)}
    return out

read = set().union(*(ids(r['entity']) for r in R if r['record kinds and fields'].strip() != '-'))
named_only = set().union(*(ids(r['entity']) for r in R)) - read
config = set().union(*(ids(r['configuration or parameter']) for r in R))
limits = set().union(*(ids(r['known limit and the entity that closes it']) for r in R))
M6 = {'E26', 'E27', 'E28', 'E29', 'E30', 'E31', 'E32', 'E33', 'E34', 'E35', 'E36', 'E37'}
INTAKE_NEEDS = {'E20', 'E05'}
FOUNDATION = {'E01', 'E02', 'E03', 'E89'}
READINESS_DEPS = {'E45', 'E84'}   # the calculation run and the finding: APG outputs of current code the readiness record needs
MUST_VERIFY = {'E35'}              # values S04 s12 requires a person to verify: a template cannot satisfy that, so document capture is the minimum
A_SET = read | config | M6 | INTAKE_NEEDS | FOUNDATION | READINESS_DEPS | {'N01'}

# which stage 1 intake a record kind goes through today (apg/ingest/specs.py SPECS; apg/fin, apg/det, apg/mkt *_SPECS)
S04_REF = {'supplier', 'ap_invoice', 'credit_note', 'payment', 'purchase_order', 'po_amendment', 'supplier_quote', 'pm_invoice',
           'budget_line', 'fx_rate', 'market_observation'}
MILESTONE = {'project', 'contract', 'variation', 'ctc_line', 'retention', 'security', 'facility', 'bank_txn', 'compliance', 'notice',
             'delay_event', 'plant_hire', 'timesheet', 'work_output', 'defect', 'material', 'material_demand', 'delivery',
             'spec_requirement', 'quote_reading', 'quote_tier', 'quote_term', 'landed_assumption', 'import_check'}
DIRECT = {'E77': 'written directly by apg/fin/cash_states.py record_event', 'E03': 'written directly by apg/source_authority.py ingest_batch',
          'E01': 'fields on stored records (source_record_id on 22 of 35 kinds)', 'E90': 'a policy object in apg/fin/policy.py; no builder setup',
          'E45': 'derived by current code (snapshots and qualified figures)', 'E84': 'derived by current code (apg/det/findings.py)'}

def intake_today(e):
    if e['id'] in DIRECT:
        return DIRECT[e['id']]
    m = re.match(r'\s*(?:partial|covered|partly):\s*([a-z_]+)', e['APG today (record kind: fields)'])
    k = m.group(1) if m else None
    if k in S04_REF:
        return f'{k}: S04 reference intake (delivery rules, reconciliation, authority, supplier resolution)'
    if k in MILESTONE:
        return f'{k}: milestone intake (the same mapping and delivery decisions; cross-record checks made by the calculations, not S04 reconciliation)'
    return 'no record kind today'

POLICY_FIELDS = {'cost_scope', 'po_status_map', 'variation_status_map', 'credit_reopens_commitment', 'freshness_days', 'ctc_method', 'ffc_basis',
                 'tax_basis', 'gst_rate_bps', 'recognition_method', 'carrying', 'cash_adjustment'}
L1, ORDER, BUILT = 'TDESA', 'TDESA', {'exists': 0, 'partly': 1, 'proposed': 2}
NAME = {'T': 'import template', 'D': 'document capture', 'E': 'entry screen', 'S': 'setup question', 'A': 'APG derives',
        'P': 'phone site capture', 'I': 'integration'}
SUPP = [{'id': 'N01', 'entity': 'Detection-rule settings (thresholds, windows, R04B instruction types, R07 comparable pairs declared by a person)',
         'class': 'C', 'status': 'missing', 'path status': 'S proposed', 'APG today (record kind: fields)': 'missing: passed to each rule as its parameters; no entity holds them'}]
rows = []
for e in E + SUPP:
    paths = [(p.split()[0], p.split()[-1]) for p in e['path status'].split(';')]
    assert all(c in NAME and s in BUILT for c, s in paths), e['id']
    l1 = [p for p in paths if p[0] in L1]
    assert l1, e['id']
    codes = {c for c, _ in l1}
    if e['id'] in MUST_VERIFY and 'D' in codes:
        best = next(p for p in l1 if p[0] == 'D')
    elif e['class'] == 'C' and 'S' in codes:
        best = next(p for p in l1 if p[0] == 'S')
    elif e['class'] == 'I' and 'A' in codes and 'E' not in codes:
        best = next(p for p in l1 if p[0] == 'A')
    elif e['class'] == 'I' and 'E' in codes:
        best = next(p for p in l1 if p[0] == 'E')
    else:
        best = min(l1, key=lambda p: (BUILT[p[1]], ORDER.index(p[0])))
    i = e['id']
    if e['class'] == 'V':
        rel, why = 'optional', 'developer extension (outside the locked blueprint)'
    elif i in A_SET:
        rel = 'A'
        why = ('read by a current rule or M4 figure' if i in read else 'configuration a current contract names' if i in config or i == 'N01'
               else 'input to a current M6 market figure (its contract is still to be written)' if i in M6
               else 'needed by the intake before it will use release A records' if i in INTAKE_NEEDS
               else 'APG output of current code that the readiness record needs' if i in READINESS_DEPS else 'the intake or readiness itself')
    elif i in limits:
        rel, why = 'B', 'closes a known limit of a current rule or figure; useful only once that rule or figure is changed'
    else:
        rel = 'later'
        why = ('APG output partly produced by current code; kept as its own record when its use is designed' if e['class'] == 'I' and e['status'] != 'missing'
               else 'input to an insight not built yet')
    if i in named_only and rel == 'B':
        why += ' (named by a contract whose figure reads no record today)'
    rows.append({'id': i, 'entity': e['entity'], 'class': e['class'], 'status today': e['status'], 'release': rel, 'why this release': why,
                 'minimum way in (Level 1)': NAME[best[0]], 'its build state': best[1],
                 'intake today': intake_today(e) if i != 'N01' else 'no record kind today',
                 'other Level 1 ways in': '; '.join(f'{NAME[c]} ({s})' for c, s in l1 if (c, s) != best),
                 'Level 2 and 3': '; '.join(f'{NAME[c]} ({s})' for c, s in paths if c not in L1)})
with open('SUPPLY_PLAN.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)

# Release A coverage report: per contract row, what it reads and how ready each input's way in is.  This is a consistency report, not a
# pass/fail test of the design: release A is defined to contain these entities, so membership cannot fail; the useful output is the gaps.
plan = {r['id']: r for r in rows}
out = []
for c in R:
    cfg = c['configuration or parameter']
    toks = set(re.findall(r'[a-z_]{4,}', cfg))
    pol = toks & POLICY_FIELDS
    det = bool(cfg.strip()) and bool(toks - POLICY_FIELDS - {'policy', 'configured', 'missing', 'stops', 'figure', 'with', 'credits', 'present',
                                                          'unknown', 'every', 'linked', 'amendment', 'exposure', 'approval', 'each', 'where', 'pairs',
                                                          'declared', 'comparable', 'person', 'rate_source', 'funded_share_bps', 'proxy_rate_bps',
                                                          'base', 'components', 'whole', 'budget', 'cost', 'code', 'source', 'authority', 'register'}) \
          and not c['rule or figure'].startswith(('M4', 'every M4'))
    need = sorted(ids(c['entity']) | ids(cfg) | ({'E90'} if pol else set()) | ({'N01'} if det else set()))
    gaps = [f"{i} {plan[i]['minimum way in (Level 1)']} {plan[i]['its build state']}" for i in need if plan[i]['its build state'] != 'exists']
    recs = sorted(ids(c['entity'])) if c['record kinds and fields'].strip() != '-' else []
    noref = [i for i in recs if 'S04 reference intake' not in plan[i]['intake today']]
    out.append({'rule or figure': c['rule or figure'], 'reads records': 'no' if c['record kinds and fields'].strip() == '-' else 'yes',
                'entities': ' '.join(need) or '-',
                'minimum way in not fully built': '; '.join(gaps) or '-',
                'not through the S04 reference intake today': ' '.join(noref) or '-',
                'needs detection-rule settings (N01)': 'yes' if det else '-',
                'needs financial-policy fields (E90)': ', '.join(sorted(pol)) or '-',
                'release of what it reads': ' '.join(sorted({plan[i]['release'] for i in need})) or '-'})
with open('RELEASE_A_COVERAGE.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0]), lineterminator='\n'); w.writeheader(); w.writerows(out)

from collections import Counter
print('rows', len(rows), 'release', sorted(Counter(r['release'] for r in rows).items()))
for rel in ['A', 'B', 'later', 'optional']:
    rr = [r for r in rows if r['release'] == rel]
    print(rel, len(rr), sorted(Counter((r['its build state'], r['minimum way in (Level 1)']) for r in rr).items()))
print('named but not read:', sorted(named_only))
print('A not exists:', [(r['id'], r['minimum way in (Level 1)'], r['its build state']) for r in rows if r['release'] == 'A' and r['its build state'] != 'exists'])
print('A intake:', Counter(r['intake today'].split(':')[-1].strip()[:30] for r in rows if r['release'] == 'A'))
print('A only by file:', [r['id'] for r in rows if r['release'] == 'A' and not any(x in r['other Level 1 ways in'] + r['minimum way in (Level 1)'] for x in ('entry screen', 'document capture', 'setup question', 'APG derives'))])
print('N01 rows', sum(o['needs detection-rule settings (N01)'] != '-' for o in out), 'E90 rows', sum(o['needs financial-policy fields (E90)'] != '-' for o in out),
      'gap rows', sum(o['minimum way in not fully built'] != '-' for o in out), 'outside ref intake', sum(o['not through the S04 reference intake today'] != '-' for o in out))
for o in out: print(' ', o['rule or figure'][:34].ljust(34), '| N01', o['needs detection-rule settings (N01)'].ljust(3), '| E90', o['needs financial-policy fields (E90)'][:50], '|', o['release of what it reads'])
