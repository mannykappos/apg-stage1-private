"""Reconciliation: what each stored record is worth once its RELATIONSHIPS are looked at.  Blueprint: Section 04 sections 5, 7, 9, 11, 13; PG-DI-AC-01..06, 08, 09, 12.

`reconcile` is a PURE FUNCTION of (the stored records, the approved authority register, the people's decisions, the as-of date).  It does not depend on the order in
which files arrived, so replaying or reordering deliveries cannot change an outcome.  For every stored record it writes a `recon_state` record holding:
  effective_outcome  accepted | accepted_with_warnings | pending_reconciliation | quarantined | rejected   (the worst thing found, never the best)
  lifecycle          'current', or 'duplicate_of' another record (a duplicate delivery has no financial effect)
  findings           every reason, with a code a reviewer can act on
  amount_cents       the value the record contributes, or None; a human correction replaces it only through the review queue
What it checks, and what it will NOT do:
  * a material value is authoritative only through an APPROVED field-level source authority rule (M2 resolve_field); no approved register -> nothing is authoritative
  * a duplicate is exact only when the supplier's own invoice number is the same too; anything merely similar is a CANDIDATE and holds both records
  * a supplier is never chosen by resemblance; ambiguous or unconfirmed suppliers hold the record (entities.py)
  * a link to a PO, invoice or payment target that is not visible yet is a hold ('PO_NOT_VISIBLE'), not a discarded record and not an invented match
  * a person's decision applies only while the blocking facts are exactly the ones the person saw (blocking_digest)
Unresolved items are held in the review queue, visible to reviewers, and are closed automatically only when the blocking facts disappear."""
from dataclasses import dataclass
from .. import canon
from ..source_authority import (ACCEPTED, ACCEPTED_W, PENDING, QUARANTINED, REJECTED, Observation, QuarantineQueue, resolve_field)
from ..values import Known, Unknown
from .entities import AMBIGUOUS, NEEDS_CONFIRMATION, RESOLVED, SupplierDirectory
from .specs import ENTITIES, SPECS

RANK = {ACCEPTED: 0, ACCEPTED_W: 1, PENDING: 2, QUARANTINED: 3, REJECTED: 4}
NOT_CLEARABLE = ('MATERIAL_VALUE_UNKNOWN', 'NO_APPROVED_REGISTER', 'NO_AUTHORITY_RULE', 'AUTHORITATIVE_SOURCE_ABSENT', 'AUTHORITATIVE_VALUE_UNKNOWN', 'AWAITING_', 'AS_OF_INVALID', 'REVISION_INVALID')


@dataclass(frozen=True)
class ReconcileConfig:
    resolver_role: str = 'reconciler'
    required_approvals: int = 1
    supplier_master_required: bool = True


class ReviewQueue(QuarantineQueue):
    """The M2 quarantine queue plus: a blocking digest (a decision applies only to the facts the person saw) and automatic closing when the blocker disappears."""
    def hold_blocking(self, record_ref, outcome, codes, candidates, resolver_role, required_approvals, digest, register_version, evidence):
        cur = self.s.get(self.KIND, record_ref)
        if cur is not None and cur.payload.get('blocking_digest') == digest:
            return cur, False
        p = {'status': 'held', 'record_ref': record_ref, 'outcome': outcome, 'reasons': list(codes), 'field': '', 'register_version': register_version or '', 'resolver_role': resolver_role,
             'required_approvals': required_approvals, 'candidates': [list(c) for c in candidates], 'evidence': list(evidence), 'approvals': [], 'disposition': None, 'blocking_digest': digest}
        rec = self.s.put(self.KIND, record_ref, p, expected_revision=cur.revision if cur else 0)
        self.s.log('quarantine.hold', record_ref, outcome, reason=','.join(codes))
        return rec, True

    def close_resolved(self, record_ref):
        cur = self.s.get(self.KIND, record_ref)
        if cur is None or cur.payload['status'] not in ('held', 'retained'):
            return False
        p = canon.deep_copy(cur.payload)
        p['status'] = 'resolved_by_data'
        p['disposition'] = {'action': 'none', 'note': 'the blocking facts no longer exist', 'by': 'system'}
        self.s.put(self.KIND, record_ref, p, expected_revision=cur.revision)
        self.s.log('quarantine.closed', record_ref, 'resolved_by_data', reason='blocker gone')
        return True


def _f(outcome, code, detail=''):
    return {'outcome': outcome, 'code': code, 'detail': detail}


def _clearable(code):
    return not any(code.startswith(n) for n in NOT_CLEARABLE)


def _val(payload, fld):
    """-> Known | Unknown for a stored field."""
    if fld in payload['fields']:
        return Known(payload['fields'][fld]) if isinstance(payload['fields'][fld], int) and not isinstance(payload['fields'][fld], bool) else Unknown('invalid', 'not a whole number')
    return Unknown(payload['unknown'].get(fld, 'no_data'))


def _composite(payload, names):
    return canon.digest([[n, payload['fields'].get(n), payload['unknown'].get(n)] for n in names])


def reconcile(scoped, register, as_of, config=None):
    cfg = config or ReconcileConfig()
    recs = {kind: {r.key: r for r in scoped.query(kind)} for kind in ENTITIES}
    ents = scoped.query('entity_alias')
    aliases = [(r.payload['text'], r.payload['supplier_id']) for r in ents if r.payload.get('status') == 'approved']
    supplier_rows = [(k, r.payload['fields'].get('supplier_name', '')) for k, r in recs['supplier'].items()
                     if not r.payload.get('conflict') and r.payload['intrinsic']['outcome'] in (ACCEPTED, ACCEPTED_W)]
    directory = SupplierDirectory(supplier_rows, aliases)
    resolutions = {r.key: r.payload for r in scoped.query('entity_resolution')}
    queue = ReviewQueue(scoped)
    F, W, INFO = {}, {}, {}                                  # findings, warnings, side information per (kind, key)
    life = {}

    def add(k, outcome, code, detail=''):
        F.setdefault(k, []).append(_f(outcome, code, detail))

    for kind in ENTITIES:
        for key, r in recs[kind].items():
            k = (kind, key)
            F.setdefault(k, [])
            W[k] = list(r.payload['intrinsic']['warnings'])
            INFO[k] = {}
            for code in r.payload['intrinsic']['pending']:
                add(k, QUARANTINED if code.startswith('CONFLICT_') else PENDING, code)

    # ---- duplicates (Section 04 section 7): exact only with the supplier's own number; similar = candidate
    for kind, spec in SPECS.items():
        names, strong = spec['composite'], spec['strong']
        if not names:
            continue
        groups = {}
        for key, r in recs[kind].items():
            if r.payload.get('conflict'):
                continue
            groups.setdefault(_composite(r.payload, names), []).append(key)
        demoted = set()
        for keys in groups.values():
            if len(keys) < 2:
                continue
            keys.sort()
            sv = [tuple(recs[kind][x].payload['fields'].get(s) for s in strong) for x in keys]
            if strong and all(all(v is not None for v in t) for t in sv) and len(set(sv)) == 1:
                for dup in keys[1:]:
                    life[(kind, dup)] = keys[0]
                    demoted.add(dup)
            else:
                for x in keys:
                    add((kind, x), PENDING, 'DUPLICATE_CANDIDATE:' + ','.join(y for y in keys if y != x), 'same business details under different identifiers')
        if strong:
            sg = {}
            for key, r in recs[kind].items():
                if r.payload.get('conflict') or key in demoted:
                    continue
                t = tuple(r.payload['fields'].get(s) for s in strong)
                if all(v is not None for v in t):
                    sg.setdefault(t, []).append(key)
            for keys in sg.values():
                if len(keys) > 1:
                    for x in sorted(keys):
                        add((kind, x), PENDING, 'DUPLICATE_CANDIDATE:' + ','.join(y for y in sorted(keys) if y != x), 'same supplier invoice number, different details')

    # ---- supplier (Section 04 section 11)
    for kind, spec in SPECS.items():
        sf = spec['supplier_field']
        if not sf:
            continue
        for key, r in recs[kind].items():
            k = (kind, key)
            text = r.payload['fields'].get(sf)
            if r.payload.get('conflict') or text is None:
                continue
            if not directory.ids():
                if cfg.supplier_master_required:
                    add(k, PENDING, 'SUPPLIER_UNVERIFIABLE_NO_MASTER', 'no accepted supplier list has been ingested')
                else:
                    W[k].append('SUPPLIER_NOT_CHECKED')
                continue
            m = directory.resolve(text)
            human = resolutions.get(f'{kind}/{key}')
            if m.status != RESOLVED and human and human.get('text') == text and human.get('supplier_id') in directory.ids():
                INFO[k]['supplier_id'] = human['supplier_id']
                INFO[k]['supplier_basis'] = 'human_resolution'
                W[k].append('SUPPLIER_RESOLVED_BY_PERSON:' + human['supplier_id'])
                continue
            if m.status == RESOLVED:
                INFO[k]['supplier_id'] = m.supplier_id
                INFO[k]['supplier_basis'] = m.method
            else:
                code = {AMBIGUOUS: 'SUPPLIER_AMBIGUOUS', NEEDS_CONFIRMATION: 'SUPPLIER_NEEDS_CONFIRMATION'}.get(m.status, 'SUPPLIER_UNRESOLVED')
                add(k, PENDING, code + (':' + ','.join(m.candidates) if m.candidates else ''), f'{text!r} was not forced to a supplier')

    # ---- relationships
    def live(kind, key):
        r = recs[kind].get(key)
        return r if r is not None and not r.payload.get('conflict') and (kind, key) not in life else None

    for key, r in recs['ap_invoice'].items():
        k, p = ('ap_invoice', key), r.payload
        po = p['fields'].get('purchase_order_ref')
        if po is None or p.get('conflict'):
            continue
        pr = live('purchase_order', po)
        if pr is None:
            add(k, PENDING, 'PO_NOT_VISIBLE:' + po, 'held for reconciliation; no match was invented')
            continue
        for fld, code in (('project_ref', 'PO_PROJECT_MISMATCH'), ('cost_code_ref', 'PO_COST_CODE_MISMATCH')):
            a, b = p['fields'].get(fld), pr.payload['fields'].get(fld)
            if a is not None and b is not None and a != b:
                add(k, PENDING, f'{code}:{po}', f'{a} against {b}')
        s1, s2 = INFO[k].get('supplier_id'), INFO[('purchase_order', po)].get('supplier_id')
        if s1 and s2 and s1 != s2:
            add(k, PENDING, f'PO_SUPPLIER_MISMATCH:{po}', f'{s1} against {s2}')
    for key, r in recs['po_amendment'].items():
        k, p = ('po_amendment', key), r.payload
        po = p['fields'].get('purchase_order_ref')
        if po is not None and not p.get('conflict') and live('purchase_order', po) is None:
            add(k, PENDING, 'PO_NOT_VISIBLE:' + po, 'held for reconciliation')
    credits_by_inv = {}
    for key, r in recs['credit_note'].items():
        k, p = ('credit_note', key), r.payload
        inv = p['fields'].get('against_invoice_ref')
        if inv is None or p.get('conflict') or k in life:
            continue
        ir = live('ap_invoice', inv)
        if ir is None:
            add(k, PENDING, 'CREDIT_TARGET_NOT_VISIBLE:' + inv, 'held for reconciliation')
            continue
        credits_by_inv.setdefault(inv, []).append(key)
        s1, s2 = INFO[k].get('supplier_id'), INFO[('ap_invoice', inv)].get('supplier_id')
        if s1 and s2 and s1 != s2:
            add(k, PENDING, f'CREDIT_SUPPLIER_MISMATCH:{inv}', f'{s1} against {s2}')
    for inv, cks in credits_by_inv.items():
        ia = recs['ap_invoice'][inv].payload['fields'].get('amount_ex_gst_cents')
        amts = [recs['credit_note'][c].payload['fields'].get('amount_ex_gst_cents') for c in cks]
        if ia is not None and all(a is not None for a in amts) and sum(amts) > ia:
            for c in cks:
                add(('credit_note', c), PENDING, 'CREDIT_EXCEEDS_INVOICE:' + inv, f'credits {sum(amts)} against invoice {ia}')
    pays_by_inv = {}
    for key, r in recs['payment'].items():
        k, p = ('payment', key), r.payload
        inv = p['fields'].get('invoice_ref')
        if inv is None or p.get('conflict') or k in life:
            continue
        if live('ap_invoice', inv) is None:
            add(k, PENDING, 'PAYMENT_TARGET_NOT_VISIBLE:' + inv, 'held for reconciliation')
            continue
        pays_by_inv.setdefault(inv, []).append(key)
    for inv, pks in pays_by_inv.items():
        ip = recs['ap_invoice'][inv].payload
        ex, gst = ip['fields'].get('amount_ex_gst_cents'), ip['fields'].get('gst_cents')
        amts = [recs['payment'][c].payload['fields'].get('amount_cents') for c in pks]
        if ex is None or gst is None or any(a is None for a in amts):
            for c in pks:
                W[('payment', c)].append('PAYMENT_LIMIT_UNCHECKED')
        elif sum(amts) > ex + gst:
            for c in pks:
                add(('payment', c), PENDING, 'PAYMENT_EXCEEDS_INVOICE:' + inv, f'payments {sum(amts)} against invoice total {ex + gst}')
    # lineage (information only; it never changes arithmetic): credits against an invoice, and reissue candidates by invoice-number pattern
    for inv, cks in credits_by_inv.items():
        ip = recs['ap_invoice'][inv].payload['fields']
        n = ip.get('supplier_invoice_number')
        reissues = sorted(k2 for k2, r2 in recs['ap_invoice'].items() if k2 != inv and n and r2.payload['fields'].get('supplier_ref') == ip.get('supplier_ref')
                          and r2.payload['fields'].get('project_ref') == ip.get('project_ref') and str(r2.payload['fields'].get('supplier_invoice_number', '')).startswith(n)
                          and r2.payload['fields'].get('supplier_invoice_number') != n)
        INFO[('ap_invoice', inv)]['lineage'] = {'credits': sorted(cks), 'reissue_candidates': reissues, 'reissue_basis': 'invoice-number pattern only; not used in any total'}
        for rk in reissues:
            INFO[('ap_invoice', rk)].setdefault('lineage', {})['reissue_of_candidate'] = inv

    # ---- secondary sources and field authority (Section 04 sections 5, 9, 13)
    sec_obs = {}
    for key, r in recs['pm_invoice'].items():
        tgt, fld = SPECS['pm_invoice']['secondary_for']
        if r.payload.get('conflict'):                                  # a cross-check source that disagrees with itself cannot confirm anything, and its earlier
            if key in recs[tgt]:                                       # disagreement must not simply vanish: the primary is held until a person looks
                add((tgt, key), PENDING, 'SECONDARY_IN_CONFLICT:' + r.payload['source'], 'the cross-check source has several different versions of this record')
            continue
        if live(tgt, key) is None and key not in recs[tgt]:
            add(('pm_invoice', key), PENDING, 'SECONDARY_WITHOUT_PRIMARY:' + key, 'no primary record to compare with')
            continue
        sec_obs.setdefault((tgt, key, fld), []).append(Observation(r.payload['source'], _val(r.payload, fld), f'pm_invoice/{key}@{r.revision}', r.payload['provenance']['received_at'], r.payload['source_revision']))
    auth_info = {}
    for kind, spec in SPECS.items():
        if not spec['material'] or 'secondary_for' in spec:
            continue
        for key, r in recs[kind].items():
            k, p = (kind, key), r.payload
            if p.get('conflict') or k in life:
                continue
            for fld in spec['material']:
                obs = [Observation(p['source'], _val(p, fld), f'{kind}/{key}@{r.revision}', p['provenance']['received_at'], p['source_revision'])] + sec_obs.get((kind, key, fld), [])
                res = resolve_field(register, f'{kind}/{key}', kind, fld, obs, as_of)
                auth_info[(k, fld)] = res
                if res.outcome == ACCEPTED_W:
                    W[k].extend(res.warnings)
                elif res.outcome != ACCEPTED:
                    add(k, res.outcome, res.reasons[0] if len(res.reasons) == 1 else ','.join(res.reasons), '; '.join(res.warnings))

    # ---- combine, apply people's decisions, write
    report = {'by_outcome': {}, 'held': 0, 'closed': 0, 'records': 0}
    for kind in ENTITIES:
        for key, r in recs[kind].items():
            k, p = (kind, key), r.payload
            ref = f'{kind}/{key}'
            fs = F.get(k, [])
            blocking = [x for x in fs if RANK[x['outcome']] >= RANK[PENDING]]
            warns = sorted(set(W[k]))
            amount = None
            spec = SPECS[kind]
            if spec['primary'] and not p.get('conflict'):
                v = _val(p, spec['primary'])
                amount = v.cents if isinstance(v, Known) else None
            review = None
            outcome = ACCEPTED if not warns else ACCEPTED_W
            lifecycle, dup_of = 'current', None
            if k in life:
                lifecycle, dup_of = 'duplicate_of', life[k]
                outcome = ACCEPTED_W
                blocking = []
            elif blocking:
                outcome = max((x['outcome'] for x in blocking), key=lambda o: RANK[o])
                cands = []
                if p.get('conflict'):
                    cands = [[c['content_hash'][:12], str(c['fields'].get(spec['primary'], 'unknown')) if spec['primary'] else '-'] for c in p['conflict']['contenders']]
                for (kk, fld), res in auth_info.items():
                    if kk == k and res.candidates and res.outcome != ACCEPTED:
                        cands = [list(c) for c in res.candidates]
                rule = register.rule_for(kind, spec['primary'], as_of) if register is not None and spec['primary'] and register.approved() else None
                role = rule.conflict_resolver_role if rule else cfg.resolver_role
                need = rule.required_approvals if rule else cfg.required_approvals
                # the digest covers the blocking facts AND who must decide and how many: if the rules change, earlier decisions no longer count
                digest = canon.digest({'codes': sorted(x['code'] for x in blocking), 'content': p.get('content_hash') or [c['content_hash'] for c in p['conflict']['contenders']], 'cands': cands,
                                       'role': role, 'need': need})
                item = scoped.get('quarantine', ref)
                same = item is not None and item.payload.get('blocking_digest') == digest
                if same and item.payload['status'] == 'promoted':
                    disp = item.payload['disposition']
                    stuck = [x for x in blocking if not _clearable(x['code'])]
                    corrected = disp.get('action') == 'correct'
                    stuck = [x for x in stuck if not (corrected and x['code'].startswith(('MATERIAL_VALUE_UNKNOWN', 'AUTHORITATIVE_VALUE_UNKNOWN')))]
                    if stuck:
                        fs = fs + [_f(PENDING, 'PROMOTION_CANNOT_CLEAR:' + stuck[0]['code'], 'a reviewer cannot waive this; it needs new evidence')]
                    else:
                        outcome = ACCEPTED_W
                        warns = sorted(set(warns) | {'PROMOTED_BY_REVIEW:' + disp['action']} | {'CLEARED:' + x['code'] for x in blocking})
                        review = {'status': 'promoted', 'action': disp['action'], 'note': disp.get('note', ''), 'approvals': [a['by'] for a in item.payload['approvals']]}
                        if corrected:
                            amount = disp['corrected_cents']
                            review['corrected_cents'] = amount
                        blocking = []
                elif same and item.payload['status'] == 'rejected':
                    outcome = REJECTED
                    fs = fs + [_f(REJECTED, 'REJECTED_BY_REVIEW', item.payload['disposition'].get('note', ''))]
                    review = {'status': 'rejected', 'note': item.payload['disposition'].get('note', '')}
                    blocking = []
                if blocking:
                    _, new = queue.hold_blocking(ref, outcome, [x['code'] for x in blocking], cands, role, need, digest, register.version if register is not None else None, [f'{ref}@{r.revision}'])
                    report['held'] += 1 if new else 0
                    review = review or {'status': 'open'}
            if not blocking and k not in life and outcome in (ACCEPTED, ACCEPTED_W) and queue.close_resolved(ref):
                report['closed'] += 1
            if outcome in (PENDING, QUARANTINED, REJECTED):
                amount = amount if outcome != REJECTED else None
            state = {'kind': kind, 'key': key, 'revision': r.revision, 'lifecycle': lifecycle, 'duplicate_of': dup_of, 'effective_outcome': outcome,
                     'findings': [x for x in fs], 'warnings': warns, 'amount_cents': amount, 'supplier_id': INFO[k].get('supplier_id'), 'supplier_basis': INFO[k].get('supplier_basis'),
                     'register_version': register.version if register is not None else None, 'lineage': INFO[k].get('lineage'), 'review': review}
            scoped.put('recon_state', ref, state)
            report['by_outcome'][outcome] = report['by_outcome'].get(outcome, 0) + (1 if lifecycle == 'current' else 0)
            if lifecycle == 'duplicate_of':
                report['by_outcome']['duplicate_delivery'] = report['by_outcome'].get('duplicate_delivery', 0) + 1
            report['records'] += 1
    scoped.log('reconcile.run', 'tenant', 'ok', reason=as_of, detail={'records': report['records'], 'held_new': report['held'], 'closed': report['closed']})
    return report
