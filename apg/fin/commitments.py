"""Commitments: purchase orders and their amendments, and how invoices use them up.  Blueprint: Section 03 section 7, Section 05 PG-PC-AC-02, 05; Section 06 (unapproved cost
exposure is its own class); CR-02 B2 (a purchase order is 'authorised' yet its lifecycle starts at Draft).

  committed        PO amount + amendments that are linked to an APPROVED change
  invoiced         counted invoices that name the PO (dated on or before the cut-off), gross, unless the policy says a credit re-opens the commitment
  open             committed - invoiced, never below zero; an invoice above the commitment is shown as an overrun, not as a negative commitment
  exposure         amendments with no approved change behind them: a separate class, in neither the committed nor the open figure
Because open = committed - invoiced, an invoice moving a PO from 'ordered' to 'billed' lowers the open commitment by exactly what it adds to actual cost: the two
never count the same work twice (PG-PC-AC-05).  A draft PO is not a commitment; a cancelled or closed PO has nothing open.  Delivery or receipt data is not read (none is
ingested), so goods received but not invoiced are NOT in either figure; the figure says so."""
from . import policy as P
from .costs import AUTH_OUTCOMES, NO_CODE, hold_class, invoice_lines
from .figure import FigureBuilder

LIMIT = 'goods received but not yet invoiced are not known (no receipt data is ingested); open commitment is PO value less invoices only'


def variation_class(F, status):
    mp = F.policy.get('variation_status_map') if F.policy else None
    return None if mp is None else mp.get(status)


def build_commitments(F, project, cutoff):
    pol = F.policy
    b = FigureBuilder('open_commitments', 'component', 'fin.commitments', 1, {'project': project}, cutoff, pol)
    if pol is None:
        return b.cannot('POLICY_NOT_PINNED')
    if pol.get('po_status_map') is None:
        return b.cannot('PO_STATUS_MAP_NOT_CONFIGURED', P.OPEN_DECISIONS['po_status_map'])
    b.limit(LIMIT)
    lines, _, _ = invoice_lines(F, project, cutoff)
    consumed, credited, unresolved = {}, {}, {}
    for ln in lines.values():
        po = ln['po']
        if not po:
            continue
        if ln['disp'] == 'counted':
            consumed.setdefault(po, []).append(ln)
        elif ln['disp'] not in ('after_cutoff', 'duplicate_delivery', 'rejected_by_review'):
            unresolved.setdefault(po, []).append(ln)
    certain, possible = F.of_project('purchase_order', project)
    am_certain, am_possible = F.of_project('po_amendment', project)
    amendments = {}
    for key in am_certain:
        base, st = F.get('po_amendment', key), F.recon('po_amendment', key)
        fl = base['fields']
        amendments.setdefault(fl.get('purchase_order_ref'), []).append((key, base, st))
    po_lines, total_open, total_exposure = {}, 0, 0
    for key in certain:
        base, st = F.get('purchase_order', key), F.recon('purchase_order', key)
        fl, ref = base['fields'], 'purchase_order/' + key
        status = fl.get('source_status')
        if st is None or st['effective_outcome'] not in AUTH_OUTCOMES or st['lifecycle'] == 'duplicate_of' or st['amount_cents'] is None:
            if st is not None and st['lifecycle'] == 'duplicate_of':
                b.exclude(ref, 'duplicate_delivery', ['DUPLICATE_OF:' + str(st['duplicate_of'])])
                b.duplicate(ref, 'purchase_order/' + str(st['duplicate_of']))
            else:
                cls, codes = hold_class(st) if st is not None else ('held', ['NO_RECONCILIATION_STATE'])
                b.exclude(ref, cls, codes, fl.get('amount_ex_gst_cents'))
                if cls in ('disputed', 'quarantined'):
                    b.dispute(ref, ','.join(codes))
            continue
        if fl.get('order_date') and fl['order_date'] > cutoff:
            b.exclude(ref, 'after_cutoff', ['DATED_AFTER_CUTOFF:' + fl['order_date']], st['amount_cents'])
            continue
        if status is None:
            b.exclude(ref, 'unknown_value', ['PO_STATUS_UNKNOWN'], st['amount_cents'])
            b.unknown(ref + ' status', 'no_data', P.OPEN_DECISIONS['po_status_map'])
            continue
        cls = pol['po_status_map'].get(status)
        if cls is None:
            b.exclude(ref, 'unknown_value', ['PO_STATUS_UNMAPPED:' + status], st['amount_cents'])
            b.unknown(ref + ' status ' + status, 'unmapped', P.OPEN_DECISIONS['po_status_map'])
            continue
        committed, approved_amd, exposure = st['amount_cents'], 0, 0
        amd_detail = []
        for akey, abase, ast in amendments.get(key, []):
            aref, afl = 'po_amendment/' + akey, abase['fields']
            if ast is None or ast['effective_outcome'] not in AUTH_OUTCOMES or ast['amount_cents'] is None:
                acls, codes = hold_class(ast) if ast is not None else ('held', ['NO_RECONCILIATION_STATE'])
                b.exclude(aref, acls, codes, afl.get('delta_cents'))
                amd_detail.append({'amendment': akey, 'delta_cents': afl.get('delta_cents'), 'treatment': 'held'})
                continue
            if afl.get('amendment_date') and afl['amendment_date'] > cutoff:
                b.exclude(aref, 'after_cutoff', ['DATED_AFTER_CUTOFF:' + afl['amendment_date']], ast['amount_cents'])
                continue
            change = afl.get('approved_change_ref')
            delta = ast['amount_cents']
            if change is None:
                exposure += delta
                amd_detail.append({'amendment': akey, 'delta_cents': delta, 'treatment': 'exposure', 'why': 'NO_APPROVED_CHANGE_REFERENCE'})
                continue
            var = F.get('variation', change)
            vcls = None
            if var is not None and not var.get('conflict'):
                vcls = variation_class(F, var['fields'].get('source_status'))
            if pol.get('variation_status_map') is None:
                exposure += delta
                amd_detail.append({'amendment': akey, 'delta_cents': delta, 'treatment': 'exposure', 'why': 'VARIATION_STATUS_MAP_NOT_CONFIGURED'})
                b.unknown(aref + ' approval', 'method_not_configured', P.OPEN_DECISIONS['variation_status_map'])
            elif vcls == 'approved':
                approved_amd += delta
                b.contribute(aref, F.rev('po_amendment', akey), delta, 'approved_amendment')
                amd_detail.append({'amendment': akey, 'delta_cents': delta, 'treatment': 'committed', 'change': change})
            else:
                exposure += delta
                amd_detail.append({'amendment': akey, 'delta_cents': delta, 'treatment': 'exposure', 'why': 'CHANGE_NOT_APPROVED:' + (change if var is None else str(var['fields'].get('source_status')))})
        total_exposure += exposure
        gross = sum(l['gross'] for l in consumed.get(key, []))
        credits = sum(c['amount'] for l in consumed.get(key, []) for c in l['credits'] if c['applied'])
        reopen = pol.get('credit_reopens_commitment')
        if credits and reopen is None:
            b.unknown(f'{ref} credits {credits}', 'method_not_configured', P.OPEN_DECISIONS['credit_reopens_commitment'])
        invoiced = gross - credits if reopen else gross
        commit_total = committed + approved_amd
        if cls == 'committed':
            open_c, over = max(commit_total - invoiced, 0), max(invoiced - commit_total, 0)
            b.contribute(ref, F.rev('purchase_order', key), commit_total, 'commitment')
            total_open += open_c
        else:
            open_c, over = 0, 0
        for l in unresolved.get(key, []):
            b.unknown(f"{l['ref']} (invoice for {ref}) is not resolved, so how much of the commitment it uses is unknown", 'held')
        if over:
            b.reason('INVOICED_EXCEEDS_COMMITMENT:' + key)
        po_lines[key] = {'class': cls, 'status': status, 'cost_code': fl.get('cost_code_ref') or NO_CODE, 'committed_cents': committed, 'approved_amendments_cents': approved_amd,
                         'unapproved_exposure_cents': exposure, 'invoiced_cents': invoiced, 'open_cents': open_c, 'overrun_cents': over, 'amendments': amd_detail,
                         'invoices': sorted(l['key'] for l in consumed.get(key, [])), 'unresolved_invoices': sorted(l['key'] for l in unresolved.get(key, []))}
    for k in possible:
        b.exclude('purchase_order/' + k, 'unattributed', ['PROJECT_UNKNOWN_OR_AMBIGUOUS'])
    for k in am_possible:
        b.exclude('po_amendment/' + k, 'unattributed', ['PROJECT_UNKNOWN_OR_AMBIGUOUS'])
    b.classify('po_lines', dict(sorted(po_lines.items())))
    b.classify('unapproved_exposure_cents', total_exposure)
    by_code = {}
    for pl in po_lines.values():
        by_code[pl['cost_code']] = by_code.get(pl['cost_code'], 0) + pl['open_cents']
    b.classify('open_by_cost_code', dict(sorted(by_code.items())))
    return b.finish(cents=total_open)
