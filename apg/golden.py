"""Golden cases on Builder Zero.  Runs the M2 controls over the synthetic builder's planted scenarios and returns a plain, deterministic dict.

`regression/GOLDEN_M2.json` holds the expected dict.  Later milestones must keep producing it: if a change moves any of these answers, either the change
is wrong or the golden file needs a reviewed, recorded update.  THRESHOLDS HERE COME FROM builder_zero/scenarios/test_thresholds.json AND ARE ILLUSTRATIVE ONLY.

`oracle()` recomputes the headline numbers straight from the CSV files with the csv module and plain arithmetic, using none of apg, so the golden file
cannot simply agree with the code that wrote it."""
import csv, json, os
from . import materiality_engine as ME, repro, source_authority as SA, status_model as SM, tenancy
from .canon import digest
from .reference_impl import FakeClock, InMemoryAuditLog, InMemoryRecordStore, StaticContextProvider
from .values import Known, Unknown, as_value, total


def _rows(root, rel):
    with open(os.path.join(root, 'builder_zero', rel), encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def _int(v):
    return int(v) if v not in ('', None) else None


def _near(root, po_id, days):
    import datetime
    pos = _rows(root, 'zero_one/SRC-03_procurement/purchase_orders.csv'); me = next(r for r in pos if r['po_id'] == po_id)
    d = lambda x: datetime.date.fromisoformat(x)
    return sorted(r['po_id'] for r in pos if r['project_id'] == me['project_id'] and r['po_id'] != po_id and abs((d(r['po_date']) - d(me['po_date'])).days) <= days)


def oracle(root):
    inv1 = _rows(root, 'zero_one/SRC-01_accounting/ap_invoices.csv'); inv2 = _rows(root, 'zero_two/SRC-01_accounting/ap_invoices.csv')
    pm = _rows(root, 'zero_one/conflicting_sources/pm_system_invoices.csv')
    ids2 = {}
    for r in inv2:
        ids2.setdefault(r['invoice_id'], []).append(r)
    return {'zero_one_invoice_rows': len(inv1), 'zero_one_ex_gst_total_cents': sum(int(r['ex_gst_cents']) for r in inv1),
            'zero_one_gst_total_cents_known': sum(int(r['gst_cents']) for r in inv1 if r['gst_cents'] != ''), 'zero_one_gst_blank_ids': sorted(r['invoice_id'] for r in inv1 if r['gst_cents'] == ''),
            'zero_two_invoice_rows': len(inv2), 'zero_two_repeated_ids': sorted(k for k, v in ids2.items() if len({tuple(sorted(x.items())) for x in v}) > 1),
            'po_0098_same_project_orders_within_30_days': _near(root, 'PO-0098', 30), 'conflict_invoice': pm[0]['invoice_ref'], 'conflict_pm_cents': int(pm[0]['ex_gst_cents']),
            'conflict_accounting_cents': next(int(r['ex_gst_cents']) for r in inv1 if r['invoice_id'] == pm[0]['invoice_ref'])}


def _world():
    c = FakeClock(); p = StaticContextProvider(c); st = InMemoryRecordStore(p); au = InMemoryAuditLog(p, c)
    def who(tok, tenant, user, roles=(), kind='human'):
        p._contract_register_session(tok, tenant, user, tuple(roles), kind, 36000)
        return tenancy.ScopedStore(st, au, p.resolve(tok))
    return c, p, st, au, who


def _typed(rows, numeric):
    out = []
    for r in rows:
        r = dict(r)
        for k in numeric:
            if k in r:
                r[k] = _int(r[k])
        out.append(r)
    return out


def run_golden(root):
    th = json.load(open(os.path.join(root, 'builder_zero', 'scenarios', 'test_thresholds.json'), encoding='utf-8'))
    clock, prov, store, audit, who = _world()
    s1, s2 = who('t1', 'zero_one', 'ann', ('finance_reviewer',)), who('t2', 'zero_two', 'bob', ('finance_reviewer',))
    inv1 = _typed(_rows(root, 'zero_one/SRC-01_accounting/ap_invoices.csv'), ('ex_gst_cents', 'gst_cents'))
    inv2 = _typed(_rows(root, 'zero_two/SRC-01_accounting/ap_invoices.csv'), ('ex_gst_cents', 'gst_cents'))
    G = {}
    # --- PS-24 tenancy and intake
    k1, bad1 = SA.ingest_batch(s1, 'ap_invoice', inv1, 'invoice_id'); k2, bad2 = SA.ingest_batch(s2, 'ap_invoice', inv2, 'invoice_id')
    G['PS-24'] = {'zero_one_stored': len(k1), 'zero_one_held': sorted(bad1), 'zero_two_stored': len(k2), 'zero_two_held': {k: len(v) for k, v in sorted(bad2.items())},
                  'zero_two_cannot_see_zero_one_only_ids': s2.get('ap_invoice', 'INV-0187') is None and s1.get('ap_invoice', 'INV-0187') is not None}
    spoofs = 0
    for extra in ({'tenant_id': 'zero_one'}, {'org_id': 'zero_one'}, {'meta': [{'Tenant': 'zero_one'}]}):
        try:
            s2.put('ap_invoice', 'EVIL', dict(inv2[1], **extra))
        except Exception as e:
            spoofs += type(e).__name__ == 'TenantMismatch'
    G['PS-24']['spoof_attempts_refused'] = spoofs; G['PS-24']['spoofed_record_stored'] = s2.get('ap_invoice', 'EVIL') is not None
    # --- PS-13 conflicting sources
    pm = _rows(root, 'zero_one/conflicting_sources/pm_system_invoices.csv')[0]
    reg = SA.AuthorityRegister('REG-GOLDEN-1', (SA.AuthorityRule('ap_invoice', 'ex_gst_cents', 'accounting', ('pm-system',), 'source_owned', 'quarantine', 'finance_reviewer', 1, '2025-01-01', None, 'finance-owner',
                                                                 'SYNTHETIC golden-case rule - not a real authority decision'),), 'proposer', (SA.Approval('alice', 'authority_owner', 'human', '2026-10-01'),), None)
    rows, outcomes = [], {}
    for r in inv1:
        obs = [SA.Observation('accounting', r['ex_gst_cents'], f"accounting:{r['invoice_id']}@1", '2026-10-01T00:00:00Z', 1)]
        if r['invoice_id'] == pm['invoice_ref']:
            obs.append(SA.Observation('pm-system', int(pm['ex_gst_cents']), f"pm:{r['invoice_id']}@1", '2026-10-01T00:00:00Z'))
        x = SA.resolve_field(reg, r['invoice_id'], 'ap_invoice', 'ex_gst_cents', obs, th['as_of'])
        outcomes[x.outcome] = outcomes.get(x.outcome, 0) + 1; rows.append((r['invoice_id'], x.outcome, x.value, x.reasons))
    t = SA.authoritative_total(rows)
    G['PS-13'] = {'outcomes': dict(sorted(outcomes.items())), 'authoritative_cents': t.cents, 'complete': t.complete, 'excluded': [[e[0], e[1], list(e[2])] for e in t.excluded],
                  'included_count': len(t.included)}
    # --- PS-21 missing critical values
    gst = total((r['invoice_id'], r['gst_cents']) for r in inv1)
    G['PS-21'] = {'gst_known_total_cents': gst.cents, 'gst_complete': gst.complete, 'gst_left_out': [[x[0], x[1]] for x in gst.left_out]}
    # --- PS-26 ambiguous document values
    q, rate = as_value('4O'), as_value('$2.650')
    ocr = SA.resolve_field(SA.AuthorityRegister('REG-G2', (SA.AuthorityRule('quote', 'qty', 'documents', (), 'source_owned', 'quarantine', 'finance_reviewer', 1, '2025-01-01', None, 'o', 'SYNTHETIC'),), 'p',
                                                (SA.Approval('alice', 'authority_owner', 'human', 'd'),), None),
                           'DOC-002', 'quote', 'qty', [SA.Observation('documents', 40, 'doc:DOC-002', '2026-10-01T00:00:00Z', 1, origin='ai_extracted')], th['as_of'])
    G['PS-26'] = {'quantity_text_reads_as': type(q).__name__ + ':' + q.reason, 'rate_text_reads_as': type(rate).__name__ + ':' + rate.reason, 'ocr_outcome': ocr.outcome, 'ocr_authoritative': ocr.authoritative}
    # --- PS-10 / NC-10 materiality with the ILLUSTRATIVE thresholds
    pos = _typed(_rows(root, 'zero_one/SRC-03_procurement/purchase_orders.csv'), ('amount_cents',))
    pol = {'version': 'GOLDEN-ILLUSTRATIVE-1', 'rules': {'purchase_order': {'abs_cents': th['single_order_materiality_abs_cents']}}, 'always_material': [], 'aggregate': True,
           'aggregation': {'keys': list(th['aggregation_keys']), 'window_days': th['aggregation_window_days']}}
    prop, o1, o2 = who('tp', 'zero_one', 'prop'), who('to1', 'zero_one', 'o1', ('materiality_owner',)), who('to2', 'zero_one', 'o2', ('materiality_owner',))
    ME.propose_policy(prop, pol); ME.approve_policy(o1, pol['version']); ME.approve_policy(o2, pol['version']); G['policy_change_kind'] = ME.activate_policy(o1, pol['version'])
    recs = [{'id': r['po_id'], 'subject': 'purchase_order', 'amount_cents': r['amount_cents'] if r['amount_cents'] is not None else Unknown('no_data'), 'date': r['po_date'], 'group': {'project': r['project_id']}} for r in pos]
    verdicts = {}
    for rec in recs:
        a = ME.assess_record(o1, rec, [c for c in recs if c['id'] != rec['id']]); verdicts[rec['id']] = [a.material, list(a.reasons)]
    byid = {r['id']: r for r in recs}
    def chain(ids):                                 # the scenario's own records only: does the CHAIN aggregate?
        out = {}
        for i in ids:
            a_ = ME.assess_record(o1, byid[i], [byid[j] for j in ids if j != i]); out[i] = [a_.material, list(a_.reasons)]
        return out
    G['PS-10'] = chain(['PO-0093', 'PO-0094', 'PO-0095']); G['NC-10'] = chain(['PO-0096', 'PO-0097', 'PO-0098'])
    # Observation, not a decision: with the project as the only grouping key and the whole project ledger as candidates, PO-0098 also groups with unrelated orders.
    G['NC-10_whole_project_ledger'] = {'PO-0098': verdicts['PO-0098'], 'PO-0096': verdicts['PO-0096'], 'PO-0097': verdicts['PO-0097']}
    G['materiality_summary'] = {'orders': len(verdicts), 'material': sum(1 for v in verdicts.values() if v[0]), 'by_reason': {}}
    for v in verdicts.values():
        for rs in v[1]:
            G['materiality_summary']['by_reason'][rs] = G['materiality_summary']['by_reason'].get(rs, 0) + 1
    G['materiality_summary']['by_reason'] = dict(sorted(G['materiality_summary']['by_reason'].items()))
    a = ME.assess_record(o1, recs[0], recs[1:])
    G['materiality_open_decisions'] = list(a.open_decisions); G['materiality_assessment_verifies'] = list(ME.verify_assessment(o1, a.key))
    # --- reproducibility
    f = repro.FormulaRegistry(); f.register('project_ex_gst_total', 1, lambda inputs, params: {'cents': sum(v['ex_gst_cents'] for k, v in sorted(inputs.items()) if v['project_id'] == params['project']), 'n': len(inputs)})
    ref = [repro.pin_latest(s1, 'ap_invoice', r['invoice_id']) for r in inv1 if r['project_id'] == 'PRJ-002' and r['ex_gst_cents'] is not None]
    rec = repro.run(s1, f, clock, 'project_ex_gst_total', 1, ref, {'project': 'PRJ-002'})
    s1.put('ap_invoice', ref[0].key, dict(s1.get('ap_invoice', ref[0].key).payload, ex_gst_cents=1))
    G['reproducibility'] = {'result': rec['result'], 'run_key': rec['run_key'], 'replay_ok_after_input_changed': repro.replay(s1, f, rec['run_key']).ok,
                            'drift': repro.drift_report(s1, rec['run_key'])}
    # --- status ladder: a claim beyond its evidence
    H = 'c' * 64
    ev = lambda kind, env, **k: SM.Evidence(**{'kind': kind, 'ref': f'golden-{kind}', 'requirement_ids': ('GOLDEN-REQ',), 'build': 'b1', 'environment': env, 'result': 'pass', 'actor': 'dev', 'actor_kind': 'human', 'role': '',
                                                'mock_only': False, 'tests': ('T',) if env != 'n/a' else (), 'components': ('x',), 'integrity_hash': H if env != 'n/a' else '', **k})
    claim = [('Specified', ev('approval', 'n/a', role='product_owner', actor='po')), ('Implemented', ev('implementation', 'n/a')), ('Local-tested', ev('test_run', 'local')),
             ('Integration-tested', ev('integration_run', 'integration', mock_only=True)), ('Staging-verified', ev('staging_run', 'staging'))]
    st_, err = SM.supported_status('GOLDEN-REQ', claim)
    G['status_ladder'] = {'supported_status': st_.status, 'first_refusal': err.code}
    G['audit_chain_ok'] = [audit.verify(s1.ctx).ok, audit.verify(s2.ctx).ok]
    return G


def dumps(g):
    return json.dumps(g, indent=1, sort_keys=True, ensure_ascii=True) + '\n'
