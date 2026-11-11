"""Demand against orders and deliveries: coverage, shortage, over-ordering, possible duplicate orders.  Blueprint: Section 08 sections 4 (reconcile demand against approved quantities, open orders,
deliveries; flag over-ordering, shortage risk, duplicate orders; do NOT classify every variance as waste - legitimate allowances, phased delivery and incomplete records may explain it), 13 (distinguish
verified inventory from estimates and unverified site reports; a surplus is not a loss), PG-MP-AC-01, 14.

How orders are matched to a demand line: there is NO demand reference on a purchase order in the data, so an order belongs to a demand line when it is for the same project and material, was placed inside
the policy's matching window before the required-on-site date (and on or before the as-of day), and its status maps to committed or closed in the financial policy.  That rule is a policy choice, not a
fact of the data; it is reported with every result.  Orders held by reconciliation only because they look like duplicates of each other are counted separately (`possible`), never silently included or
dropped: the confirmed figure and the figure if every suspected order is genuine are both shown.

Quantities are in millionths; a delivery counts at the quantity ACCEPTED when that is recorded, otherwise at the quantity delivered with the gap noted.  Installed, returned and stock-held quantities are
not in the data, so no on-site inventory is claimed: a delivered surplus is a delivery record, not a stock count."""
from . import common as C


def _po_class(F, po):
    pol = F.policy
    if pol is None or pol.get('po_status_map') is None:
        return None
    return pol['po_status_map'].get(po['status']) if po['status'] is not None else None


def _unit_key(u):
    return u.strip().lower() if isinstance(u, str) and u.strip() else None


def unit_mismatches(ctx, req):
    """Orders in the matching window for the same project and material whose unit differs from the demand's unit.  No conversion is applied to orders, so a quantity in another unit cannot be added to or
    compared with the demand: coverage then cannot be assessed (counting it, or leaving it out, would both be a guess)."""
    want = _unit_key(req.get('unit'))
    if want is None:
        return []
    start = C.add_days(req['required_date'], -ctx.mp['demand']['order_match_window_days'])
    out = []
    for k, po in sorted(ctx.pos.items()):
        if po.get('project') != req['project'] or po.get('material') != req['material'] or po.get('date') is None or po['date'] < start or po['date'] > ctx.as_of:
            continue
        if not (po['ok'] or po['dup_candidates']):
            continue
        have = _unit_key(po.get('unit'))
        if have is not None and have != want:
            out.append((po['ref'], po.get('unit'), req.get('unit')))
    return out


def matched_orders(ctx, req):
    """-> (confirmed [po views], possible [po views held only as duplicate candidates], not_counted [(ref, why)]).  Raises LookupError('PO_STATUS_MAP_NOT_CONFIGURED') when the financial policy has no map."""
    F, mp = ctx.F, ctx.mp
    if F.policy is None or F.policy.get('po_status_map') is None:
        raise LookupError('PO_STATUS_MAP_NOT_CONFIGURED')
    start = C.add_days(req['required_date'], -mp['demand']['order_match_window_days'])
    confirmed, possible, skipped = [], [], []
    for k, po in sorted(ctx.pos.items()):
        if po.get('project') != req['project'] or po.get('material') != req['material'] or po.get('date') is None:
            continue
        if po['date'] < start or po['date'] > ctx.as_of:
            continue
        cls = _po_class(F, po)
        if cls not in ('committed', 'closed'):
            skipped.append((po['ref'], 'status %r maps to %s' % (po['status'], cls)))
            continue
        if po['ok']:
            confirmed.append(po)
        elif po['dup_candidates']:
            possible.append(po)
        else:
            skipped.append((po['ref'], ','.join(po['why'])))
    return confirmed, possible, skipped


def delivered_for(ctx, pos):
    """-> (accepted_micro, delivered_micro, dockets, notes).  Dockets are matched to the orders by purchase-order reference and dated on or before the as-of day."""
    refs = {po['key'] for po in pos}
    acc, dlv, rows, notes = 0, 0, [], []
    for k in C.keys_of(ctx.F, 'delivery'):
        d = C.delivery_view(ctx.F, k)
        if d is None:
            continue
        if not d['ok']:
            raw = ctx.F.get('delivery', k).get('fields') or {}
            if raw.get('purchase_order_ref') in refs:
                notes.append('docket %s is held (%s) and is not counted' % (k, ','.join(d['why'])))
            continue
        if d['po'] not in refs or d['date'] > ctx.as_of:
            continue
        counted = d['accepted'] if d['accepted'] is not None else d['delivered']
        if d['accepted'] is None:
            notes.append('docket %s records no accepted quantity: the delivered quantity is used' % k)
        acc += counted
        dlv += d['delivered']
        rows.append({'docket': d['ref'], 'revision': d['rev'], 'po': d['po'], 'date': d['date'], 'delivered_micro': d['delivered'], 'accepted_micro': d['accepted']})
    return acc, dlv, rows, notes


def coverage(ctx, req):
    """-> coverage record for a demand requirement."""
    try:
        confirmed, possible, skipped = matched_orders(ctx, req)
    except LookupError as e:
        return {'requirement': req['id'], 'status': 'cannot_assess', 'why': str(e)}
    mism = unit_mismatches(ctx, req)
    if mism:
        return {'requirement': req['id'], 'status': 'cannot_assess',
                'why': 'UNIT_MISMATCH: ' + '; '.join('%s is in %s but the demand is in %s' % m for m in mism) + '; no unit conversion is applied to orders, so the quantities cannot be compared'}
    need = req['qty_micro']
    ordered = sum(po['qty'] for po in confirmed)
    ordered_all = ordered + sum(po['qty'] for po in possible)
    acc, dlv, dockets, notes = delivered_for(ctx, confirmed + possible)
    tol = ctx.mp['demand']['surplus_tolerance_bps']
    over_conf = max(0, ordered - need)
    over_all = max(0, ordered_all - need)
    over_deliv = max(0, acc - need)
    ordered_material = over_all * 10000 > tol * need and over_all > 0
    delivered_material = over_deliv * 10000 > tol * need and over_deliv > 0
    if ordered_material or delivered_material:
        status = 'over_ordered'
    elif ordered_all < need:
        status = 'uncovered'
    else:
        status = 'covered'
    return {'requirement': req['id'], 'project': req['project'], 'material': req['material'], 'status': status, 'required_micro': need, 'required_date': req['required_date'],
            'window_start': C.add_days(req['required_date'], -ctx.mp['demand']['order_match_window_days']),
            'ordered_confirmed_micro': ordered, 'ordered_if_all_genuine_micro': ordered_all, 'uncovered_micro': max(0, need - ordered_all), 'uncovered_if_suspected_not_genuine_micro': max(0, need - ordered),
            'surplus_confirmed_micro': over_conf, 'surplus_if_all_genuine_micro': over_all, 'accepted_delivered_micro': acc, 'delivered_micro': dlv, 'surplus_delivered_micro': over_deliv,
            'orders': [{'ref': po['ref'], 'revision': po['rev'], 'qty_micro': po['qty'], 'rate_cents': po['rate'], 'date': po['date'], 'supplier': po['supplier'], 'confirmed': po['ok'], 'observed_at': po['received'],
                        'duplicate_candidates': po['dup_candidates']} for po in confirmed + possible],
            'dockets': dockets, 'not_counted': skipped, 'notes': notes, 'tolerance_bps': tol,
            'matching_rule': 'same project and material; order dated from %d days before the required date to the as-of day; status committed or closed in the financial policy; a policy choice, no demand reference exists on an order' % ctx.mp['demand']['order_match_window_days'],
            'inventory_note': 'installed, returned and held quantities are not in the data: a delivered surplus is a delivery record, not a stock count'}


def duplicate_groups(ctx):
    """-> list of groups of orders with the same project, supplier, material, quantity and rate placed within the policy window of each other.  Both confirmed and suspected orders are looked at."""
    win = ctx.mp['demand']['duplicate_window_days']
    cands = [po for k, po in sorted(ctx.pos.items()) if po.get('project') is not None and po.get('date') is not None and po.get('rate') is not None
             and (po['ok'] or po['dup_candidates']) and _po_class(ctx.F, po) in ('committed', 'closed')]
    by = {}
    for po in cands:
        by.setdefault((po['project'], po['supplier'], po['material'], po['qty'], po['rate']), []).append(po)
    out = []
    for key, members in sorted(by.items()):
        members.sort(key=lambda p: (p['date'], p['key']))
        group = [members[0]]
        for po in members[1:]:
            if C.days(group[-1]['date'], po['date']) <= win:
                group.append(po)
            else:
                if len(group) > 1:
                    out.append(group)
                group = [po]
        if len(group) > 1:
            out.append(group)
    return [{'project': g[0]['project'], 'supplier': g[0]['supplier'], 'material': g[0]['material'], 'qty_micro': g[0]['qty'], 'rate_cents': g[0]['rate'],
             'orders': [{'ref': p['ref'], 'revision': p['rev'], 'date': p['date'], 'confirmed': p['ok'], 'amount_cents': p['amount']} for p in g],
             'span_days': C.days(g[0]['date'], g[-1]['date']), 'held_as_candidates': any(not p['ok'] for p in g)} for g in out]
