"""Landed cost.  Blueprint: Section 08 sections 6 (Landed Cost = purchase cost + freight and insurance + duties and applicable charges + handling and delivery + other incremental costs; tax treatment
explicit; FX recorded; normalise units; volume tiers, minimum order quantities, pack sizes), 5 (highlight missing inclusions), PG-MP-AC-04, 06.

Every component of a unit's landed cost has a STATUS, so nothing is ever a silent zero:
  purchase       the quoted unit rate, converted to the home currency at the recorded reference rate
  freight, insurance, duty, clearance, handling
     included_in_rate   the delivery basis in the policy table says the unit rate already includes it
     stated             the quote states it (freight only)
     assumed            a person recorded an assumption for this quote (per unit, or basis points of the purchase cost for duty)
     missing            the policy REQUIRES it for this kind of purchase (domestic / international) and nothing gives it: the landed cost is INCOMPLETE and the known parts are shown as a lower bound
     not_required       the policy does not require it and nothing gives it
The unit cost is the sum of the components that are known; `complete` is true only when no required component is missing and the delivery basis is in the table.  Tax is explicit: the landed
cost is stated in the tax treatment the policy declares for the price source.  Rounding: each currency conversion is rounded once to the cent per unit; a total is the unit cost times the quantity
rounded once.  Larger orders: `purchase_plan` prices the whole quantity actually bought (tier, minimum order, pack size) - a lower unit price for a bigger order is never assumed to be a lower total."""
from . import common as C, fx as FX
from .. import canon
from .policy import COMPONENTS

DUTY_LIKE = ('duty',)


def tiers(F, quote_key):
    """-> sorted [(min_qty_micro, unit_rate_minor, ref, revision)] of usable tiers for the quote, plus held tier records."""
    out, held = [], []
    for key in sorted(F.kind('quote_tier')):
        v = C.simple_view(F, 'quote_tier', key, ('quote_ref', 'min_quantity', 'unit_rate_minor_units'))
        if v is None or not C.names_quote(F, 'quote_tier', key, quote_key):
            continue
        if not v['ok']:
            held.append({'ref': v['ref'], 'why': v['why']})
            continue
        m = C.qty_micro(v['f']['min_quantity'])
        if m is None or m <= 0 or v['f']['unit_rate_minor_units'] <= 0:
            held.append({'ref': v['ref'], 'why': ['TIER_INVALID']})
            continue
        out.append((m, v['f']['unit_rate_minor_units'], v['ref'], v['rev']))
    return sorted(out), held


def terms(F, quote_key):
    """-> {term name: value text} of usable terms, with refs."""
    out, held = {}, []
    for key in sorted(F.kind('quote_term')):
        v = C.simple_view(F, 'quote_term', key, ('quote_ref', 'term_name', 'value_text'))
        if v is None or not C.names_quote(F, 'quote_term', key, quote_key):
            continue
        if not v['ok']:
            held.append({'ref': v['ref'], 'why': v['why']})
            continue
        out[v['f']['term_name']] = {'value': v['f']['value_text'], 'ref': v['ref'], 'revision': v['rev']}
    return out, held


def assumptions(F, quote_key):
    """-> {component: assumption} set by a person for the quote (a record with no `set_by` is held back as unsigned)."""
    out, held = {}, []
    for key in sorted(F.kind('landed_assumption')):
        v = C.simple_view(F, 'landed_assumption', key, ('quote_ref', 'component_name'))
        if v is None or not C.names_quote(F, 'landed_assumption', key, quote_key):
            continue
        if not v['ok']:
            held.append({'ref': v['ref'], 'why': v['why']})
            continue
        f = v['f']
        if f['component_name'] not in COMPONENTS or (f.get('per_unit_minor_units') is None) == (f.get('rate_bps') is None) or not f.get('set_by'):
            held.append({'ref': v['ref'], 'why': ['ASSUMPTION_INVALID_OR_UNSIGNED']})
            continue
        if f.get('rate_bps') is not None and f['component_name'] not in DUTY_LIKE:
            held.append({'ref': v['ref'], 'why': ['RATE_ONLY_FOR_DUTY']})
            continue
        out[f['component_name']] = {'per_unit_minor': f.get('per_unit_minor_units'), 'rate_bps': f.get('rate_bps'), 'currency': f.get('currency_code'), 'basis': f.get('basis_text'),
                                    'source_ref': f.get('source_ref'), 'set_by': f['set_by'], 'set_on': f.get('set_on'), 'ref': v['ref'], 'revision': v['rev']}
    return out, held


def is_international(mp, q):
    return q['cur'] != mp['basis']['home_currency'] or q['basis'] in mp['basis']['international_bases']


def unit_landed(F, mp, q, as_of, qty_micro=None):
    """-> landed-cost record for ONE UNIT of the quote (home currency, cents).  `qty_micro` selects the price tier."""
    home = mp['basis']['home_currency']
    intl = is_international(mp, q)
    tier_list, tier_held = tiers(F, q['key'])
    tm, tm_held = terms(F, q['key'])
    asm, asm_held = assumptions(F, q['key'])
    rate, tier_used = q['rate'], None
    if tier_list and qty_micro is not None:
        eligible = [t for t in tier_list if t[0] <= qty_micro]
        if eligible:
            tier_used = eligible[-1]
            rate = tier_used[1]
    conv = FX.convert(F, mp, rate, q['cur'], as_of)
    stated = FX.convert_stated(rate, q['cur'], home, q['fx_used'], q['fx_date'], as_of) if q['cur'] != home else None
    limits, comps = [], []
    sources = [(q['ref'], q['rev'])] + [(t[2], t[3]) for t in (tier_list if tier_used is None else [tier_used])]
    purchase = conv['aud_cents']
    comps.append({'component': 'purchase', 'status': 'known' if purchase is not None else 'missing', 'cents': purchase,
                  'note': 'quoted rate %s %s%s' % (C.money(rate), q['cur'], ' (tier from %s units)' % C.fmt_qty(tier_used[0]) if tier_used else '')})
    includes_known = q['basis'] in mp['basis']['delivery_bases']
    includes = set(mp['basis']['delivery_bases'][q['basis']]['includes']) if includes_known else set()
    required = set(mp['basis']['required_components']['international' if intl else 'domestic'])
    if not includes_known:
        limits.append('delivery basis %r is not in the policy table: what the rate includes is unknown' % q['basis'])
    for c in COMPONENTS:
        cell = {'component': c, 'status': None, 'cents': None, 'note': ''}
        if c in includes:
            cell.update(status='included_in_rate', cents=0, note='the %s basis includes it' % q['basis'])
            if c == 'freight' and q['freight']:
                limits.append('freight %s is stated although the %s basis already includes it: not added again' % (C.money(q['freight']), q['basis']))
        elif c == 'freight' and q['freight'] is not None:
            if mp['basis']['freight_currency'] == 'aud' or q['cur'] == home:
                fc = q['freight']
                cell.update(status='stated', cents=fc, note='stated on the quote, taken as %s' % home)
            else:
                fcv = FX.convert(F, mp, q['freight'], q['cur'], as_of)
                if fcv['aud_cents'] is None:
                    cell.update(status='missing', note='freight is in %s and cannot be converted: %s' % (q['cur'], fcv['why']))
                else:
                    cell.update(status='stated', cents=fcv['aud_cents'], note='stated on the quote in %s, converted at the reference rate' % q['cur'])
        elif c in asm:
            a = asm[c]
            if a['per_unit_minor'] is not None:
                cur = a['currency'] or home
                if cur == home:
                    cell.update(status='assumed', cents=a['per_unit_minor'], note='assumption set by %s (%s)' % (a['set_by'], a['basis'] or 'no basis text'))
                else:
                    cv = FX.convert(F, mp, a['per_unit_minor'], cur, as_of)
                    if cv['aud_cents'] is None:
                        cell.update(status='missing', note='assumption is in %s and cannot be converted: %s' % (cur, cv['why']))
                    else:
                        cell.update(status='assumed', cents=cv['aud_cents'], note='assumption set by %s in %s, converted' % (a['set_by'], cur))
            elif purchase is None:
                cell.update(status='missing', note='duty is a share of the purchase cost, which is unknown')
            else:
                cell.update(status='assumed', cents=C.mul_div(purchase, a['rate_bps'], 10000), note='%s basis points of the purchase cost, assumption set by %s (%s)' % (a['rate_bps'], a['set_by'], a['basis'] or 'no basis text'))
            sources.append((a['ref'], a['revision']))
        elif c in required:
            cell.update(status='missing', note='required for this kind of purchase; nothing in the quote or the assumptions gives it')
        else:
            cell.update(status='not_required', cents=0, note='not required by the policy and not stated')
        comps.append(cell)
    missing = [c['component'] for c in comps if c['status'] == 'missing']
    known = sum(c['cents'] for c in comps if c['cents'] is not None)
    return {'quote': q['ref'], 'international': intl, 'currency': home, 'tax_treatment': mp['basis']['price_tax']['supplier_quote'], 'components': comps, 'unit_cents': known,
            'complete': not missing and includes_known, 'missing': missing, 'limits': limits, 'conversion': conv, 'stated_conversion': stated,
            'tier': None if tier_used is None else {'min_quantity_micro': tier_used[0], 'unit_rate_minor': tier_used[1], 'ref': tier_used[2]}, 'tiers_available': len(tier_list),
            'terms': {k: v['value'] for k, v in sorted(tm.items())}, 'held': tier_held + tm_held + asm_held, 'sources': sorted(set(sources), key=lambda s: (s[0], s[1] if s[1] is not None else -1))}


def rescale(ul, factor_micro, from_unit, to_unit):
    """Re-express a unit landed cost per `to_unit` when the quote is priced per `from_unit` and a person declared that one `from_unit` is `factor_micro`/1,000,000 `to_unit` (quantity in to_unit = quantity in
    from_unit x factor, so a price per to_unit = price per from_unit / factor).  Every component is rescaled and rounded once; the record keeps the factor so the arithmetic can be repeated by hand."""
    out = canon.deep_copy(ul)
    for c in out['components']:
        if c['cents'] is not None:
            c['cents'] = C.mul_div(c['cents'], C.MICRO, factor_micro)
        c['note'] = (c['note'] + '; ' if c['note'] else '') + 'rescaled from per %s to per %s' % (from_unit, to_unit)
    out['unit_cents'] = sum(c['cents'] for c in out['components'] if c['cents'] is not None)
    out['unit_conversion'] = {'from_unit': from_unit, 'to_unit': to_unit, 'factor_micro': factor_micro, 'rounding': 'each component rounded half away from zero once'}
    out['limits'] = out['limits'] + ['prices rescaled from per %s to per %s with the declared factor %s; tiers, minimum orders and pack sizes stay in %s' % (from_unit, to_unit, C.fmt_qty(factor_micro), from_unit)]
    return out


def purchase_plan(F, mp, q, as_of, need_micro):
    """-> what must actually be bought to cover `need_micro`: the quantity (minimum order, pack size), the tier price at that quantity, total cost, surplus and the effective unit cost of the NEED.
    Also prices every higher tier once so a larger order is shown beside the plain one, with the extra total cost and the surplus that comes with it."""
    tm, _ = terms(F, q['key'])

    def num(name):
        t = tm.get(name)
        return C.qty_micro(t['value']) if t else None
    moq, pack = num('moq'), num('pack_size')

    def plan(qty):
        buy = max(qty, moq or 0)
        if pack:
            buy = -(-buy // pack) * pack
        ul = unit_landed(F, mp, q, as_of, buy)
        total = C.mul_div(ul['unit_cents'], buy, C.MICRO)
        return {'buy_qty_micro': buy, 'need_qty_micro': qty, 'surplus_qty_micro': buy - qty, 'unit_cents': ul['unit_cents'], 'complete': ul['complete'], 'total_cents': total,
                'effective_unit_cents_of_need': C.mul_div(total, C.MICRO, qty) if qty else None, 'tier': ul['tier'], 'landed': ul}
    base = plan(need_micro)
    options = []
    for t in tiers(F, q['key'])[0]:
        if t[0] > base['buy_qty_micro']:
            alt = plan(t[0])
            options.append({'buy_qty_micro': alt['buy_qty_micro'], 'unit_cents': alt['unit_cents'], 'total_cents': alt['total_cents'], 'surplus_qty_micro': alt['buy_qty_micro'] - need_micro,
                            'extra_total_cents_vs_plain': alt['total_cents'] - base['total_cents'], 'tier_ref': t[2],
                            'note': 'a larger tier lowers the unit rate but the total paid is %s than buying the need%s' % ('lower' if alt['total_cents'] < base['total_cents'] else 'higher',
                                                                                                                          '; the surplus is not assumed reusable' if alt['buy_qty_micro'] > need_micro else '')})
    return {'plain': base, 'larger_orders': options, 'minimum_order_micro': moq, 'pack_size_micro': pack}


def reference_landed(po, mp):
    """Landed record of a PURCHASE-ORDER rate used as a reference: the rate paid, with the delivery basis NOT recorded (so it can only support an indicative comparison)."""
    return {'quote': po['ref'], 'international': False, 'currency': mp['basis']['home_currency'], 'tax_treatment': mp['basis']['price_tax']['purchase_order'],
            'components': [{'component': 'purchase', 'status': 'known', 'cents': po['rate'], 'note': 'unit rate paid on the order'}], 'unit_cents': po['rate'], 'complete': False,
            'missing': [], 'limits': ['the delivery basis of a purchase-order rate is not recorded, so what it includes is unknown'], 'conversion': None, 'stated_conversion': None, 'tier': None,
            'tiers_available': 0, 'terms': {}, 'held': [], 'basis_known': False, 'sources': [(po['ref'], po['rev'])]}
