"""Authoritative and provisional views built ONLY from stored records and their reconciliation state.  Blueprint: Section 04 section 9, PG-DI-AC-03, 04, 05, 08, 09.

  invoice_cost_view   net invoice cost: invoices less the credits against them.  A duplicate delivery counts once (never twice).  An invoice whose credit is not
                      yet trusted is LEFT OUT of the authoritative figure, not counted at its gross.  Credits and reissues are never 'summed as three events'.
  gst_view            GST on those invoices; an invoice with no GST figure is listed as left out, never counted as zero.
  review_table        every record, its outcome and its reasons: what a reviewer sees, including everything that is held.
The authoritative figure is the M2 AuthoritativeTotal type; the provisional one is the M2 ProvisionalTotal and cannot be added to it."""
from ..source_authority import ACCEPTED, ACCEPTED_W, AUTHORITATIVE_OUTCOMES, authoritative_total, provisional_total
from ..values import Known, as_value, total


def _states(scoped, kind):
    recs = {r.key: r for r in scoped.query(kind)}
    st = {r.key[len(kind) + 1:]: r.payload for r in scoped.query('recon_state') if r.key.startswith(kind + '/')}
    return recs, st


def _status(state):
    return 'duplicate_delivery' if state['lifecycle'] == 'duplicate_of' else state['effective_outcome']


def _cost_rows(scoped, project=None):
    """The rows of the cost figure: (rows for authoritative_total, candidates for provisional_total).  One place decides what is counted, so the cost view and the GST view
    can never disagree about which invoices and credits are in."""
    inv, ist = _states(scoped, 'ap_invoice')
    crn, cst = _states(scoped, 'credit_note')
    rows, cand, linked = [], [], set()
    for key in sorted(inv):
        s = ist.get(key)
        if s is None or (project and inv[key].payload['fields'].get('project_ref') != project):
            continue
        status, amt, reasons = _status(s), s['amount_cents'], [f['code'] for f in s['findings']]
        credits = (s.get('lineage') or {}).get('credits', [])
        net = amt
        if credits and status in AUTHORITATIVE_OUTCOMES:
            bad = [c for c in credits if cst.get(c) is None or cst[c]['effective_outcome'] not in AUTHORITATIVE_OUTCOMES or cst[c]['amount_cents'] is None]
            linked.update(credits)
            if bad:
                status, net, reasons = 'pending_reconciliation', None, ['LINKED_CREDIT_UNRESOLVED:' + ','.join(bad)]
            else:
                net = amt - sum(cst[c]['amount_cents'] for c in credits)
        rows.append((key, status, net, reasons))
        if status not in AUTHORITATIVE_OUTCOMES and status != 'duplicate_delivery':      # a duplicate delivery has no effect, not even a provisional one
            cand.append((key, status, amt))
    for key in sorted(crn):                                          # credits with no visible invoice stay visible, never netted
        s = cst.get(key)
        if s is None or key in linked or project:                       # a project view never lists credits that are not linked to one of its invoices
            continue
        rows.append(('credit:' + key, _status(s) if _status(s) not in AUTHORITATIVE_OUTCOMES else 'pending_reconciliation', None, [f['code'] for f in s['findings']] or ['CREDIT_NOT_LINKED_TO_A_TRUSTED_INVOICE']))
    return rows, cand


def invoice_cost_view(scoped, as_of, project=None, register_version=None):
    rows, cand = _cost_rows(scoped, project)
    return authoritative_total(rows, register_version), provisional_total(cand, as_of)


def gst_view(scoped):
    """GST on exactly the invoices that are in the authoritative cost figure, less the GST on the credits netted against them.  An invoice that is held, or whose credit is not
    trusted, is not in the cost figure and so its GST is not counted either; a credit whose invoice is not in the figure is not subtracted.  An invoice or credit with no GST
    figure is listed as left out, never counted as zero."""
    inv, ist = _states(scoped, 'ap_invoice')
    crn, _ = _states(scoped, 'credit_note')
    counted = set(authoritative_total(_cost_rows(scoped)[0]).included)
    items = [(key, as_value(inv[key].payload['fields'].get('gst_cents'))) for key in sorted(inv) if key in counted]
    netted = sorted({c for key in counted for c in (ist[key].get('lineage') or {}).get('credits', [])})
    for key in netted:
        v = as_value(crn[key].payload['fields'].get('gst_cents'))
        items.append(('credit:' + key, Known(-v.cents) if isinstance(v, Known) else v))
    return total(items)


def review_table(scoped):
    out = []
    for r in scoped.query('recon_state'):
        p = r.payload
        out.append({'ref': r.key, 'status': _status(p), 'codes': [f['code'] for f in p['findings']], 'warnings': p['warnings'], 'amount_cents': p['amount_cents'],
                    'duplicate_of': p['duplicate_of'], 'supplier_id': p['supplier_id'], 'review': (p['review'] or {}).get('status')})
    return out
