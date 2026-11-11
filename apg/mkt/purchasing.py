"""Portfolio purchasing: the same material bought by several projects the viewer is authorised to see.  Blueprint: Section 08 sections 3 (portfolio purchasing: identify opportunities across AUTHORISED
projects without breaching information boundaries), 11 (purchasing leverage is a potential opportunity), 14; Section 06 section 13 (portfolio intelligence respects tenant boundaries).

Information boundary: the analysis is given the set of projects the caller is authorised to see.  An order of any other project is never read into a count, a rate, a volume, a name or a sentence; if
the authorised set does not cover EVERY project that bought the material in the window, no opportunity is reported for that material and only the fact that a boundary applied is recorded (not what is
behind it).  Tenant separation is a separate layer and comes first: the store a run reads is already one tenant's.

What is compared: the volume-weighted average unit rate each project paid for the SAME material code in the window.  If the highest average is above the lowest by at least the policy gap, the opportunity
is the extra paid by the other projects over the lowest average, for the volume they bought.  That is an ESTIMATE of what pooling or matching the best rate might change, never a saving: order rates carry no
recorded delivery basis, quantities and delivery dates differ between projects, and nothing says the better rate was available to the others.  It is labelled `indicative` and `estimate`."""
from . import common as C, demand as DM
from ..fin import fmath


def opportunities(ctx, authorised):
    """-> (list of opportunity dicts, boundary_applied bool)."""
    F, mp, as_of = ctx.F, ctx.mp, ctx.as_of
    pf = mp['portfolio']
    start = C.add_days(as_of, -pf['window_days'])
    by = {}
    for k, po in sorted(ctx.pos.items()):
        if not po['ok'] or po.get('material') is None or po.get('date') is None or po.get('rate') is None or po['date'] < start or po['date'] > as_of or DM._po_class(F, po) not in ('committed', 'closed'):
            continue
        by.setdefault((po['material'], po['unit']), []).append(po)
    out, boundary = [], False
    for (mat, unit), orders in sorted(by.items()):
        projects = sorted({po['project'] for po in orders})
        if any(p not in authorised for p in projects):
            boundary = True
            continue
        if len(projects) < pf['min_projects']:
            continue
        per = {}
        for po in orders:
            d = per.setdefault(po['project'], {'qty': 0, 'cost': 0, 'orders': []})
            d['qty'] += po['qty']
            d['cost'] += C.mul_div(po['rate'], po['qty'], C.MICRO)
            d['orders'].append(po)
        rows = []
        for p, d in sorted(per.items()):
            avg = C.mul_div(d['cost'], C.MICRO, d['qty'])
            rows.append({'project': p, 'volume_micro': d['qty'], 'average_unit_cents': avg, 'orders': [o['ref'] for o in d['orders']]})
        lo, hi = min(rows, key=lambda r: (r['average_unit_cents'], r['project'])), max(rows, key=lambda r: (r['average_unit_cents'], r['project']))
        gap = fmath.bps_of(hi['average_unit_cents'] - lo['average_unit_cents'], lo['average_unit_cents']) if lo['average_unit_cents'] > 0 else None
        if gap is None or gap < pf['rate_gap_bps']:
            continue
        extra = sum(C.mul_div(r['average_unit_cents'] - lo['average_unit_cents'], r['volume_micro'], C.MICRO) for r in rows if r['average_unit_cents'] > lo['average_unit_cents'])
        out.append({'id': 'PORT-%s' % mat, 'material': mat, 'unit': unit, 'window_start': start, 'window_end': as_of, 'projects': rows, 'lowest_project': lo['project'], 'highest_project': hi['project'],
                    'gap_bps': gap, 'combined_volume_micro': sum(r['volume_micro'] for r in rows), 'estimate_cents': extra, 'label': 'indicative', 'status': 'estimate',
                    'caveats': ['order rates record no delivery basis', 'volumes, delivery dates and sites differ between projects', 'nothing shows the lowest rate was available to the others',
                                'a pooled purchase may change supplier terms in either direction'],
                    'sources': sorted({(po['ref'], po['rev']) for po in orders}), 'human_approval_required': True})
    return out, boundary
