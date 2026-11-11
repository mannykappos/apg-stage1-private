"""Supplier performance from evidence.  Blueprint: Section 08 section 9 (measures from evidenced records; consider sample size, material category and recency; limited history must not by itself imply poor
reliability; observed performance is not a hypothesis about the future; supplier selection recommendations need authorised human review), PG-MP-AC-10.

Measures, all computed from purchase orders and delivery dockets the data actually holds:
  fill rate          accepted quantity / ordered quantity, over the orders that have at least one docket (open orders are not counted as short)
  acceptance rate    accepted quantity / delivered quantity, over dockets that record an accepted quantity
  observed lead time days from order date to the first docket of each order (minimum, median, maximum)
  price movement     lowest and highest unit rate paid for one material, as basis points of the lowest (information only)
Not measured, because the data does not hold them: on-time delivery (no promised date on an order), quote accuracy, defects and returns, disputes.  A supplier whose sample is smaller than the policy minimum is
reported as `limited_history`: its numbers are shown and NO conclusion is drawn.  A level is `below_level` only when the sample is large enough AND the rate is under the policy level.
This is observed performance on the records shown, not a prediction, and not a ranking of suppliers."""
from . import common as C, demand as DM
from ..fin import fmath


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) // 2


def profiles(ctx, authorised=None):
    """-> {supplier: profile}.  `authorised`: projects whose orders may be used (None = all)."""
    F, mp, as_of = ctx.F, ctx.mp, ctx.as_of
    sp = mp['supplier']
    dockets = {}
    for k in C.keys_of(F, 'delivery'):
        d = C.delivery_view(F, k)
        if d is not None and d['ok'] and d['date'] <= as_of:
            dockets.setdefault(d['po'], []).append(d)
    by = {}
    for k, po in sorted(ctx.pos.items()):
        if not po['ok'] or po.get('supplier') is None or po.get('date') is None or po['date'] > as_of or DM._po_class(F, po) not in ('committed', 'closed'):
            continue
        if authorised is not None and po['project'] not in authorised:
            continue
        by.setdefault(po['supplier'], []).append(po)
    out = {}
    for sup, orders in sorted(by.items()):
        delivered_orders = [(po, sorted(dockets[po['key']], key=lambda d: (d['date'], d['key']))) for po in orders if po['key'] in dockets]
        ordered = sum(po['qty'] for po, _ in delivered_orders)
        accepted = sum((d['accepted'] if d['accepted'] is not None else d['delivered']) for _, ds in delivered_orders for d in ds)
        with_acc = [d for _, ds in delivered_orders for d in ds if d['accepted'] is not None]
        dl, ac = sum(d['delivered'] for d in with_acc), sum(d['accepted'] for d in with_acc)
        leads = [C.days(po['date'], ds[0]['date']) for po, ds in delivered_orders if C.days(po['date'], ds[0]['date']) >= 0]
        prices = {}
        for po in orders:
            if po.get('rate') is not None:
                prices.setdefault(po['material'], []).append(po['rate'])
        n = len(delivered_orders)
        limited = n < sp['min_sample']
        fill = fmath.bps_of(accepted, ordered) if ordered else None
        acc = fmath.bps_of(ac, dl) if dl else None
        levels = {}
        for name, val, floor in (('fill_rate', fill, sp['min_fill_bps']), ('acceptance_rate', acc, sp['min_acceptance_bps'])):
            levels[name] = 'not_measured' if val is None else ('limited_history' if limited else ('below_level' if val < floor else 'at_or_above_level'))
        out[sup] = {'supplier': sup, 'orders': len(orders), 'orders_with_deliveries': n, 'sample_note': ('%d order(s) with deliveries against a minimum of %d: no conclusion is drawn' % (n, sp['min_sample'])) if limited
                    else '%d orders with deliveries (minimum %d)' % (n, sp['min_sample']),
                    'limited_history': limited, 'fill_rate_bps': fill, 'acceptance_rate_bps': acc, 'levels': levels,
                    'lead_time_days': {'min': min(leads), 'median': _median(leads), 'max': max(leads), 'n': len(leads)} if leads else None,
                    'price_spread_bps_by_material': {m: fmath.bps_of(max(v) - min(v), min(v)) for m, v in sorted(prices.items()) if len(v) > 1 and min(v) > 0},
                    'period': {'first_order': min(po['date'] for po in orders), 'last_order': max(po['date'] for po in orders)},
                    'evidence': [(po['ref'], po['rev']) for po, _ in delivered_orders] + [(d['ref'], d['rev']) for _, ds in delivered_orders for d in ds],
                    'not_measured': ['on-time delivery (no promised date on an order)', 'quote accuracy', 'defects, returns and rework', 'disputes'],
                    'note': 'observed performance on these records; not a prediction and not a ranking of suppliers'}
    return out
