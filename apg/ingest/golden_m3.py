"""Golden cases for M3 on Builder Zero: the REAL ingestion pipeline run over the synthetic builder's CSV files, then reconciliation with the SYNTHETIC approved register.
`regression/GOLDEN_M3.json` holds the expected dict.  `oracle_m3()` recomputes the headline numbers straight from the CSV files with the csv module and plain
arithmetic, using nothing from apg, so the golden file cannot simply agree with the code that wrote it.  Thresholds used for freshness are ILLUSTRATIVE ONLY (see
builder_zero/scenarios/test_thresholds.json for the other illustrative values); nothing here is a product-owner decision."""
import csv, datetime, json, os
from .. import tenancy
from ..ports import TenantMismatch
from ..reference_impl import FakeClock, InMemoryAuditLog, InMemoryRecordStore, StaticContextProvider
from ..source_authority import resolve_field
from . import demo_setup as D, documents as DOC, freshness as F, pipeline as P, reconcile as R, views
from .filestore import InMemoryFileStore, ingest_stored_file
from .ports_m3 import SCANNER_ROLE

AS_OF = '2026-09-30'
ILLUSTRATIVE_FRESHNESS = {'illustrative_buy_timing': 45, 'illustrative_international_quote': 30}      # days, ILLUSTRATIVE ONLY


def _rows(root, rel):
    with open(os.path.join(root, 'builder_zero', rel), encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def oracle_m3(root):
    """Independent recomputation: csv module and arithmetic only."""
    inv = _rows(root, 'zero_one/SRC-01_accounting/ap_invoices.csv'); pm = _rows(root, 'zero_one/conflicting_sources/pm_system_invoices.csv')
    crn = _rows(root, 'zero_one/SRC-01_accounting/credit_notes.csv'); sup = {r['supplier_id'] for r in _rows(root, 'zero_one/reference/suppliers.csv')}
    pos = _rows(root, 'zero_one/SRC-03_procurement/purchase_orders.csv'); fx = _rows(root, 'zero_one/SRC-10_market/fx_rates.csv'); mk = _rows(root, 'zero_one/SRC-10_market/market_observations.csv')
    quotes = _rows(root, 'zero_one/SRC-03_procurement/quotes.csv'); inv2 = _rows(root, 'zero_two/SRC-01_accounting/ap_invoices.csv')
    pmv = {r['invoice_ref']: r['ex_gst_cents'] for r in pm}
    seen, dup_ids = {}, []
    for r in inv:                                                # exact repeat delivery: same supplier + supplier invoice number + every business field
        k = (r['supplier_id'], r['supplier_invoice_no'])
        sig = (r['project_id'], r['po_id'], r['invoice_date'], r['ex_gst_cents'], r['gst_cents'])
        if k in seen and seen[k][1] == sig:
            dup_ids.append(r['invoice_id'])
        else:
            seen.setdefault(k, (r['invoice_id'], sig))
    unknown_supplier = [r['invoice_id'] for r in inv if r['supplier_id'] not in sup]
    conflicted = [r['invoice_id'] for r in inv if r['invoice_id'] in pmv and pmv[r['invoice_id']] != r['ex_gst_cents']]
    held = set(dup_ids) | set(unknown_supplier) | set(conflicted)
    credited, credited_gst = {}, {}
    for c in crn:
        credited[c['against_invoice_id']] = credited.get(c['against_invoice_id'], 0) + int(c['ex_gst_cents'])
        credited_gst[c['against_invoice_id']] = credited_gst.get(c['against_invoice_id'], 0) + int(c['gst_cents'])
    elig = [r for r in inv if r['invoice_id'] not in held]
    gross = sum(int(r['ex_gst_cents']) for r in elig)
    net = gross - sum(v for k, v in credited.items() if k not in held)
    q5 = next(q for q in quotes if q['quote_id'] == 'Q-0005')
    latest_fx = max(r['fx_date'] for r in fx if r['pair'] == 'AUD/USD')
    cu = max(r['obs_date'] for r in mk if r['material_id'] == 'MAT-CU') if 'material_id' in mk[0] else None
    po_sig = {}
    for r in pos:
        po_sig.setdefault((r['supplier_id'], r['project_id'], r['po_date'], r['material_id'], r['qty'], r['unit_rate_cents'], r['amount_cents']), []).append(r['po_id'])
    return {'invoice_rows': len(inv), 'held_invoice_ids': sorted(held), 'duplicate_delivery_ids': sorted(dup_ids), 'unknown_supplier_text_ids': sorted(unknown_supplier),
            'pm_conflict_ids': sorted(conflicted), 'eligible_invoice_count': len(elig), 'eligible_gross_ex_gst_cents': gross, 'eligible_net_of_credits_ex_gst_cents': net,
            'gst_blank_ids': sorted(r['invoice_id'] for r in inv if r['gst_cents'] == ''), 'gst_known_net_of_credits_cents_of_eligible': sum(int(r['gst_cents']) for r in elig if r['gst_cents'] != '') - sum(v for k, v in credited_gst.items() if k not in held),
            'po_missing_cost_code_ids': sorted(r['po_id'] for r in pos if r['cost_code'] == ''), 'identical_po_groups': sorted(sorted(v) for v in po_sig.values() if len(v) > 1),
            'conflict_accounting_cents': int(next(r['ex_gst_cents'] for r in inv if r['invoice_id'] == 'INV-0121')), 'conflict_pm_cents': int(pm[0]['ex_gst_cents']), 'q0005_usd_minor': int(q5['unit_rate_cents']), 'q0005_rate': q5['fx_rate_used'], 'q0005_rate_date': q5['fx_rate_date'], 'latest_aud_usd_date': latest_fx, 'mat_cu_last_observation': cu,
            'expired_quote_ids': sorted(q['quote_id'] for q in quotes if q['valid_until'] < AS_OF), 'zero_two_rows': len(inv2),
            'zero_two_invoice_ids_with_different_content': sorted({i for i in {r['invoice_id'] for r in inv2} if len({tuple(sorted(r.items())) for r in inv2 if r['invoice_id'] == i}) > 1})}


def _world():
    c = FakeClock('2026-10-01T09:00:00Z'); p = StaticContextProvider(c); st = InMemoryRecordStore(p); au = InMemoryAuditLog(p, c)
    def who(tok, tenant, user, roles=('importer',), kind='human'):
        p._contract_register_session(tok, tenant, user, tuple(roles), kind, 360000)
        return tenancy.ScopedStore(st, au, p.resolve(tok))
    return c, p, st, au, who


def _load(root, s, clock, tenant):
    out = {}
    for t, data, src, name, rev in D.files_for(root, tenant):
        out[name] = P.ingest_file(s, clock, t, data, src, name, D.DEMO_POLICY, rev)
    return out


def _st(s, kind, key):
    return s.get('recon_state', f'{kind}/{key}').payload


def run_golden_m3(root):
    clock, prov, store, audit, who = _world()
    s1, s2 = who('t1', 'zero_one', 'ann'), who('t2', 'zero_two', 'bob')
    rec1 = who('r1', 'zero_one', 'rita', ('reconciler',))
    G = {}
    rcpt1, rcpt2 = _load(root, s1, clock, 'zero_one'), _load(root, s2, clock, 'zero_two')
    G['ingest_counts_zero_one'] = {n: {k: v for k, v in r['counts'].items()} for n, r in sorted(rcpt1.items())}
    G['ingest_counts_zero_two'] = {n: {k: v for k, v in r['counts'].items()} for n, r in sorted(rcpt2.items())}
    reg = D.demo_register()
    rep1, rep2 = R.reconcile(s1, reg, AS_OF), R.reconcile(s2, reg, AS_OF)
    G['reconcile_zero_one'] = rep1
    outcomes = {}
    for r in s1.query('recon_state'):
        o = views._status(r.payload)
        outcomes[o] = outcomes.get(o, 0) + 1
    G['effective_outcomes_zero_one'] = dict(sorted(outcomes.items()))
    auth, prov_t = views.invoice_cost_view(s1, AS_OF)
    G['invoice_cost_zero_one'] = {'authoritative_cents': auth.cents, 'included_count': len(auth.included), 'complete': auth.complete, 'excluded': [[e[0], e[1], list(e[2])] for e in auth.excluded],
                                  'provisional_cents': prov_t.cents, 'provisional_unverified': [[e[0], e[1], str(e[2])] for e in prov_t.unverified]}
    # PS-11 replay / duplicate delivery
    d = _st(s1, 'ap_invoice', 'INV-0183')
    G['PS-11'] = {'INV-0183': [views._status(d), d['lifecycle'], d['duplicate_of']], 'INV-0001': _st(s1, 'ap_invoice', 'INV-0001')['effective_outcome'],
                  'counted_once': 'INV-0183' not in auth.included and 'INV-0001' in auth.included, 'redelivery_of_all_files_adds_records': 0}
    before = sum(len(s1.query(k)) for k in ('ap_invoice', 'credit_note', 'payment', 'purchase_order', 'supplier'))
    replays = [P.ingest_file(s1, clock, t, data, src, name, D.DEMO_POLICY, rev)['replay'] for t, data, src, name, rev in D.files_for(root, 'zero_one')]
    G['PS-11']['whole_files_replayed'] = [len(replays), sum(replays)]
    G['PS-11']['redelivery_of_all_files_adds_records'] = sum(len(s1.query(k)) for k in ('ap_invoice', 'credit_note', 'payment', 'purchase_order', 'supplier')) - before
    # PS-12 credit and reissue
    cr = _st(s1, 'credit_note', 'CRN-0001')
    G['PS-12'] = {'INV-0184': [_st(s1, 'ap_invoice', 'INV-0184')['effective_outcome'], _st(s1, 'ap_invoice', 'INV-0184')['lineage']], 'CRN-0001': [cr['effective_outcome'], cr['lineage']],
                  'INV-0185': [_st(s1, 'ap_invoice', 'INV-0185')['effective_outcome'], _st(s1, 'ap_invoice', 'INV-0185')['lineage']],
                  'net_of_the_three_events_cents': 6000000 - 6000000 + 5800000}
    # PS-13 conflicting sources
    x = _st(s1, 'ap_invoice', 'INV-0121')
    G['PS-13'] = {'INV-0121': [x['effective_outcome'], x['lifecycle'], [f['code'] for f in x['findings']]], 'in_authoritative_total': 'INV-0121' in auth.included,
                  'in_gst_view': 'INV-0121' in [g[0] for g in views.gst_view(s1).included]}
    # PS-21 missing critical values
    g = views.gst_view(s1)
    G['PS-21'] = {'PO-0099': [_st(s1, 'purchase_order', 'PO-0099')['effective_outcome'], [f['code'] for f in _st(s1, 'purchase_order', 'PO-0099')['findings']]],
                  'INV-0186': [_st(s1, 'ap_invoice', 'INV-0186')['effective_outcome'], s1.get('ap_invoice', 'INV-0186').payload['unknown']], 'gst_total_cents': g.cents, 'gst_complete': g.complete,
                  'gst_left_out': [list(map(str, e)) for e in g.left_out]}
    # PS-22 ambiguous supplier
    y = _st(s1, 'ap_invoice', 'INV-0187')
    G['PS-22'] = {'INV-0187': [y['effective_outcome'], y['supplier_id'], y['supplier_basis'], [f['code'] for f in y['findings']]], 'in_authoritative_total': 'INV-0187' in auth.included}
    # PS-17 (ingestion side): identical orders are held as candidates for a person to look at
    G['PS-17_ingestion_side'] = {k: [_st(s1, 'purchase_order', k)['effective_outcome'], _st(s1, 'purchase_order', k)['lifecycle'], [f['code'] for f in _st(s1, 'purchase_order', k)['findings']]] for k in ('PO-0100', 'PO-0101')}
    # PS-14 / PS-23 freshness and FX
    qv = F.quote_validity(s1, AS_OF)
    ends = F.latest_dates(s1, 'market_observation', 'obs_date', 'material_ref')
    fxl = F.latest_dates(s1, 'fx_rate', 'fx_date', 'currency_pair')
    q5 = s1.get('supplier_quote', 'Q-0005').payload['fields']
    pol = F.FreshnessPolicy(ILLUSTRATIVE_FRESHNESS)
    a_cu = F.assess(pol, 'illustrative_buy_timing', sorted(ends.items()), AS_OF)
    a_q5 = F.assess(pol, 'illustrative_international_quote', [('Q-0005 rate date', q5['fx_rate_date']), ('latest AUD/USD', fxl['AUD/USD'])], AS_OF)
    conv_old = F.convert_minor(q5['unit_rate_minor_units'], q5['fx_rate_used'], 'USD', 'AUD', 'AUD/USD', q5['fx_rate_date'], 'quote Q-0005')
    G['PS-14'] = {'Q-0004': qv['Q-0004'], 'Q-0001': qv['Q-0001'], 'MAT-CU_last_observation': ends['MAT-CU'], 'buy_timing_assessment': [a_cu['overall'], sorted(i['label'] for i in a_cu['inputs'] if i['state'] == 'stale')],
                  'unconfigured_policy_says': F.assess(F.FreshnessPolicy({}), 'illustrative_buy_timing', sorted(ends.items()), AS_OF)['overall']}
    G['PS-23'] = {'conversion_at_quote_rate': conv_old, 'conversion_at_latest_rate_for_comparison': F.convert_minor(q5['unit_rate_minor_units'], '0.6540', 'USD', 'AUD', 'AUD/USD', fxl['AUD/USD'], 'fx_rates.csv'),
                  'assessment': [a_q5['overall'], [[i['label'], i['state']] for i in a_q5['inputs']]]}
    # PS-26 documents
    docreg = __import__('apg.source_authority', fromlist=['x']).AuthorityRegister('GOLD-DOC-REG', tuple(__import__('apg.source_authority', fromlist=['x']).AuthorityRule(
        'quote_document', f, 'document_extraction', (), 'source_owned', 'quarantine', 'reconciler', 1, '2025-01-01', None, 'o', 'SYNTHETIC') for f in ('quantity', 'unit_rate_cents')), 'p',
        (__import__('apg.source_authority', fromlist=['x']).Approval('o', 'authority_owner', 'human', AS_OF),))
    docs = {}
    for did, fn in (('DOC-001', 'quote_clear_SUP-006.txt'), ('DOC-002', 'quote_ambiguous_SUP-004.txt')):
        raw = open(os.path.join(root, 'builder_zero', 'zero_one', 'SRC-11_documents', fn), 'rb').read()
        DOC.register_extraction(s1, clock, did, raw, DOC.standin_extract_quote(raw.decode()))
        f = s1.get('extracted_document', did).payload['fields']
        docs[did] = {n: {'candidates': f[n]['candidates'], 'ambiguous': f[n]['ambiguous'],
                         'authoritative_before_verification': resolve_field(docreg, did, 'quote_document', n, [DOC.observation(s1, did, n)], AS_OF).authoritative} for n in ('quantity', 'unit_rate_cents')}
    G['PS-26'] = docs
    # PS-24 tenancy
    c2 = _st(s2, 'ap_invoice', 'INV-0001')
    spoof = 0
    for hdr, cell in (('tenant_id', 'zero_one'), ('Tenant ID', 'zero_one'), ('org_id', 'zero_one')):
        data = (','.join(['invoice_id', 'supplier_id', 'supplier_invoice_no', 'project_id', 'cost_code', 'po_id', 'invoice_date', 'ex_gst_cents', 'gst_cents', 'status', 'source_batch', hdr]) + '\n' +
                ','.join(['INV-X', 'SUP-001', 'SI-X', 'PRJ-001', 'CC-01', '', '2026-05-01', '1', '1', 'posted', 'B', cell]) + '\n').encode()
        try:
            P.ingest_file(s2, clock, D.files_for(root, 'zero_two')[1][0], data, 'accounting', 'spoof.csv', D.DEMO_POLICY)
        except TenantMismatch:
            spoof += 1
    a2, _ = views.invoice_cost_view(s2, AS_OF)
    G['PS-24'] = {'zero_two_INV-0001': [c2['effective_outcome'], c2['lifecycle'], [f['code'] for f in c2['findings']]], 'zero_two_conflict_marker_contenders': len(s2.get('ap_invoice', 'INV-0001').payload['conflict']['contenders']),
                  'zero_two_authoritative_cents': a2.cents, 'zero_two_excluded': [e[0] for e in a2.excluded], 'zero_one_untouched_total': auth.cents == views.invoice_cost_view(s1, AS_OF)[0].cents,
                  'spoofed_files_refused': spoof, 'spoofed_record_stored': s2.get('ap_invoice', 'INV-X') is not None,
                  'tenants_with_records': sorted({r.tenant_id for r in s1.query('recon_state')} | {r.tenant_id for r in s2.query('recon_state')})}
    # PS-12/13 resolution by people: a reviewer decision changes the figures only through the recorded path
    from . import review
    review.decide(rec1, 'ap_invoice/INV-0121', 'correct', 'SYNTHETIC golden-case decision: accounting posting confirmed', 7280125)
    R.reconcile(s1, reg, AS_OF)
    after, _ = views.invoice_cost_view(s1, AS_OF)
    G['after_reviewer_decision_INV-0121'] = {'authoritative_cents': after.cents, 'delta_cents': after.cents - auth.cents, 'INV-0121_outcome': _st(s1, 'ap_invoice', 'INV-0121')['effective_outcome'],
                                             'evidence_revisions_for_INV-0121': len(s1.history('ap_invoice', 'INV-0121'))}
    # stored-file path with the scan gate
    files = InMemoryFileStore(prov)
    sc = who('scan', 'zero_one', 'scanner-svc', (SCANNER_ROLE,), 'service')
    t, data, src, name, rev = D.files_for(root, 'zero_one')[1]
    m = files.put(s1.ctx, name, data)
    r_unscanned = ingest_stored_file(s1, files, clock, t, m.file_id, src, D.DEMO_POLICY, rev)
    files.record_scan(sc.ctx, m.file_id, 'clean')
    r_clean = ingest_stored_file(s1, files, clock, t, m.file_id, src, D.DEMO_POLICY, rev)
    G['scan_gate'] = {'unscanned_code': r_unscanned['code'], 'clean_replay_of_same_bytes': r_clean['replay'], 'file_id_stable': m.file_id == files.put(s1.ctx, 'other.csv', data).file_id}
    G['audit_chain_ok'] = [audit.verify(s1.ctx).ok, audit.verify(s2.ctx).ok]
    return G


def dumps(g):
    return json.dumps(g, indent=1, sort_keys=True, ensure_ascii=True) + '\n'
