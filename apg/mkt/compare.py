"""Requirements, offers, the comparability gate applied, and the ranking.  Blueprint: Section 08 sections 2 (comparable before cheaper; landed cost over headline price; freshness explicit), 4.1,
5 (a quote is not a purchase commitment), 7.1, 12 (unresolved critical checks block a definitive recommendation; a clearly qualified indicative comparison may be shown), 15 (PG-MP-AC-02, 08, 11,
12, 17).

A REQUIREMENT is what a project needs: a material demand line, or a standing specification requirement a person approved.  An OFFER is a supplier quote (or, as a reference only, the rate on a
purchase order).  Every offer is run through the same gates and keeps its own record of what it passed and failed.  A RANKING has one of four statuses and only one of them can ever be used as a basis
for a recommendation:
  definitive           two or more offers, ALL of them comparable or comparable-with-adjustment, current, with a complete landed cost, no unresolved critical international check and no substitution
  indicative           at least two rankable offers but something is outstanding; the outstanding items are listed and the ranking is labelled indicative
  insufficient_offers  fewer than two rankable offers: there is nothing to rank
  no_offers            no usable offer for the requirement
Offers that are not comparable, are unverified, or are expired or not yet issued are never placed in the ranking: they are listed with the reason.  Nothing here commits a purchase or approves a
substitution: both are for a person (PG-MP-AC-17); `human_approval_required` is always true."""
from . import common as C, fresh as FR, intl as IN, landed as LD, spec as SP


class Ctx:
    def __init__(self, F, mp, spec, as_of):
        self.F, self.mp, self.spec, self.as_of = F, mp, spec, as_of
        self.spec_ok = spec is not None and spec['_approved']
        self.quotes = {k: C.quote_view(F, k) for k in C.keys_of(F, 'supplier_quote')}
        self.pos = {k: C.po_view(F, k) for k in C.keys_of(F, 'purchase_order')}
        self._memo = {}

    def memo(self, key, fn):
        if key not in self._memo:
            self._memo[key] = fn()
        return self._memo[key]


# ---------------------------------------------------------------------------------------------------------------- requirements
def requirements(ctx, authorised=None):
    """-> list of requirement dicts, sorted by id.  `authorised`: projects the caller may see (None = all)."""
    F = ctx.F
    out = []
    for k in C.keys_of(F, 'material_demand'):
        v = C.demand_view(F, k)
        if not v['ok']:
            continue
        if authorised is not None and v['project'] not in authorised:
            continue
        out.append({'id': 'demand/' + k, 'kind': 'demand', 'project': v['project'], 'material': v['material'], 'qty_micro': v['qty'], 'unit': v.get('unit'), 'required_date': v['required'],
                    'approved': True, 'sources': [(v['ref'], v['rev'])], 'observed_at': v['received']})
    for k in C.keys_of(F, 'spec_requirement'):
        v = C.simple_view(F, 'spec_requirement', k, ('project_ref', 'material_ref'))
        if not v['ok']:
            continue
        f = v['f']
        if authorised is not None and f['project_ref'] not in authorised:
            continue
        out.append({'id': 'spec_requirement/' + k, 'kind': 'standing', 'project': f['project_ref'], 'material': f['material_ref'], 'qty_micro': None, 'unit': None, 'required_date': None,
                    'approved': bool(f.get('approved_by') and f.get('approved_on')), 'basis_ref': f.get('basis_ref'), 'sources': [(v['ref'], v['rev'])], 'observed_at': v['received']})
    return sorted(out, key=lambda r: r['id'])


# ---------------------------------------------------------------------------------------------------------------- one offer
def _master_unit(ctx, material):
    return ctx.memo(('unit', material), lambda: C.unit_of(ctx.F, material))


def _commercial(ctx, q, ul):
    adj, unq = [], []
    mp = ctx.mp
    if q['basis'] not in mp['basis']['delivery_bases']:
        unq.append(('BASIS_NOT_IN_TABLE', 'delivery basis %r is not in the policy table, so what the rate includes is unknown' % q['basis']))
    for c in ul['components']:
        if c['component'] == 'purchase':
            if c['status'] == 'missing':
                unq.append(('CURRENCY_NOT_CONVERTED', 'the purchase price cannot be converted to %s' % mp['basis']['home_currency']))
            continue
        if c['status'] == 'missing':
            unq.append(('COMPONENT_MISSING:' + c['component'], '%s is required for this purchase and is missing' % c['component']))
        elif c['status'] in ('stated', 'assumed'):
            adj.append({'kind': c['component'] + '_added', 'text': '%s %s %s per unit added to the rate' % (c['component'], c['status'], C.money(c['cents'])), 'cents': c['cents']})
    if q['cur'] != mp['basis']['home_currency'] and ul['conversion']['status'] == 'converted':
        adj.append({'kind': 'currency_converted', 'text': 'converted from %s at the %s reference rate of %s' % (q['cur'], ul['conversion']['rate_date'], ul['conversion']['rate_micro']), 'cents': None})
    return {'adjustments': adj, 'unquantified': unq}


def eval_quote(ctx, q, req, decision, qty_micro=None, with_index=False):
    """-> offer evaluation dict for an OK quote view against a requirement."""
    mp, F, as_of = ctx.mp, ctx.F, ctx.as_of
    th = mp['freshness'][decision]
    rd, rd_held = SP.readings(F, q['key'])
    ul = LD.unit_landed(F, mp, q, as_of, qty_micro)
    states = [FR.quote_state(q, as_of, th)]
    if ul['international']:
        states.append(FR.fx_state(ul['conversion'], th))
    if with_index:
        states.append(FR.index_state(F, req['material'], as_of, th))
    if ctx.spec_ok:
        attr = SP.attribute_check(ctx.spec, req['material'], q['material'], rd, 'quote')
        unit = SP.unit_check(ctx.spec, req['material'], q['material'], rd, _master_unit(ctx, req['material']), _master_unit(ctx, q['material']))
    else:
        attr = {'status': 'unknown', 'family': None, 'attributes': [], 'reasons': [], 'verified': False}
        unit = {'status': 'unverified', 'from': None, 'to': None, 'factor_micro': None, 'inferred': True, 'why': 'no approved register'}
    if unit['factor_micro'] and unit['factor_micro'] != C.MICRO and unit['from'] != unit['to']:
        ul = LD.rescale(ul, unit['factor_micro'], unit['from'], unit['to'])
    comm = _commercial(ctx, q, ul)
    if ul.get('unit_conversion'):
        comm['adjustments'].append({'kind': 'unit_converted', 'text': 'priced per %s, converted to per %s at the declared factor' % (unit['from'], unit['to']), 'cents': None})
    cls, codes, reasons = SP.classify(ctx.spec_ok, attr, unit, comm, req['approved'], 'quote')
    chk = IN.checks(F, mp, q) if ul['international'] else None
    substitution = q['material'] != req['material']
    qual = FR.qualification(states)
    blockers = []
    if cls not in SP.DEFINITIVE_OK:
        blockers.append('GATE:' + cls)
    if qual != 'current':
        blockers.append('FRESHNESS:' + qual)
    if not ul['complete']:
        blockers.append('LANDED_COST_INCOMPLETE')
    if chk and chk['unresolved_critical']:
        blockers.append('INTERNATIONAL_CHECKS_UNRESOLVED')
    if substitution:
        blockers.append('SUBSTITUTION_NEEDS_APPROVAL')
    if ul['held'] or rd_held:
        blockers.append('HELD_SUPPORTING_RECORDS')
    return {'offer': {'kind': 'quote', 'key': q['key'], 'ref': q['ref'], 'revision': q['rev'], 'supplier': q['supplier'], 'material': q['material'], 'specification_text': q['spec_text'],
                      'issue_date': q['issue'], 'valid_until': q['valid_until'], 'lead_time_days': q['lead'], 'price_kind': q['kind'], 'observed_at': q['received']},
            'requirement': req['id'], 'decision': decision, 'freshness': states, 'qualification': qual, 'limitations': FR.limitations(states),
            'gate': {'class': cls, 'codes': codes, 'reasons': reasons, 'attributes': attr['attributes'], 'unit': unit, 'adjustments': comm['adjustments'], 'family': attr['family']},
            'landed': ul, 'international': chk, 'substitution': substitution, 'blockers': blockers,
            'rankable': cls in SP.RANKABLE and qual != 'historical_only' and ul['unit_cents'] > 0,
            'definitive_ok': not blockers, 'readings_used': sorted((a, r['ref'], r['revision']) for a, r in rd.items()), 'held': ul['held'] + rd_held,
            'human_approval_required': True}


def eval_po(ctx, po, req):
    """A purchase-order rate as a REFERENCE: spec from the catalogue code, unit as recorded on the order, delivery basis not recorded."""
    mp, as_of = ctx.mp, ctx.as_of
    th = mp['freshness']['benchmark']
    ul = LD.reference_landed(po, mp)
    age = C.days(po['date'], as_of)
    states = [{'subject': po['ref'], 'class': 'order_rate', 'state': 'stale' if age > th['quote_max_age_days'] else 'current', 'age_days': age, 'threshold_days': th['quote_max_age_days']}]
    pseudo = {'unit': {'value': po['unit'], 'verified': True, 'ref': po['ref'], 'revision': po['rev']}}
    if ctx.spec_ok:
        attr = SP.attribute_check(ctx.spec, req['material'], po['material'], {}, 'purchase_order')
        unit = SP.unit_check(ctx.spec, req['material'], po['material'], pseudo, _master_unit(ctx, req['material']), _master_unit(ctx, po['material']))
    else:
        attr = {'status': 'unknown', 'family': None, 'attributes': [], 'reasons': [], 'verified': False}
        unit = {'status': 'unverified', 'from': None, 'to': None, 'factor_micro': None, 'inferred': True, 'why': 'no approved register'}
    if unit['factor_micro'] and unit['factor_micro'] != C.MICRO and unit['from'] != unit['to']:
        ul = LD.rescale(ul, unit['factor_micro'], unit['from'], unit['to'])
    comm = {'adjustments': [], 'unquantified': [('REFERENCE_BASIS_UNRECORDED', 'the delivery basis and inclusions of a purchase-order rate are not recorded')]}
    if ul.get('unit_conversion'):
        comm['adjustments'].append({'kind': 'unit_converted', 'text': 'priced per %s, converted to per %s at the declared factor' % (unit['from'], unit['to']), 'cents': None})
    cls, codes, reasons = SP.classify(ctx.spec_ok, attr, unit, comm, req['approved'], 'purchase_order')
    return {'offer': {'kind': 'purchase_order', 'key': po['key'], 'ref': po['ref'], 'revision': po['rev'], 'supplier': po['supplier'], 'material': po['material'], 'order_date': po['date'], 'project': po['project'],
                      'observed_at': po['received']},
            'requirement': req['id'], 'decision': 'benchmark', 'freshness': states, 'qualification': FR.qualification(states), 'limitations': FR.limitations(states),
            'gate': {'class': cls, 'codes': codes, 'reasons': reasons, 'attributes': attr['attributes'], 'unit': unit, 'adjustments': comm['adjustments'], 'family': attr['family']},
            'landed': ul, 'international': None, 'substitution': po['material'] != req['material'], 'blockers': ['REFERENCE_ONLY'], 'rankable': False, 'definitive_ok': False, 'readings_used': [], 'held': [],
            'human_approval_required': True}


def last_paid(ctx, req):
    """The most recent usable purchase-order rate for the requirement's project and material (ties broken by key), as a reference evaluation, or None.
    An order that reconciliation holds back ONLY as a possible duplicate of other orders still shows what was ordered: its rate counts when every order it is a candidate duplicate of carries the same
    rate (identical records corroborate the rate, though not that two orders exist).  The evaluation says so."""
    best, corroborated = None, False
    for k, po in sorted(ctx.pos.items()):
        if po.get('project') != req['project'] or po.get('material') != req['material'] or po.get('rate') is None or po.get('date') is None:
            continue
        cand = False
        if not po['ok']:
            if not po['dup_candidates'] or any(ctx.pos.get(c) is None or ctx.pos[c].get('rate') != po['rate'] for c in po['dup_candidates']):
                continue
            cand = True
        if po['status'] is None or ctx.F.policy is None or ctx.F.policy.get('po_status_map', {}).get(po['status']) not in ('committed', 'closed'):
            continue
        if best is None or (po['date'], k) > (best['date'], best['key']):
            best, corroborated = po, cand
    if best is None:
        return None
    ev = eval_po(ctx, best, req)
    if corroborated:
        ev['landed']['limits'] = ev['landed']['limits'] + ['the order is held by reconciliation as a possible duplicate of %s; its rate is the same on every candidate' % ', '.join(best['dup_candidates'])]
    ev['held_as_duplicate_candidate'] = corroborated
    return ev


# ---------------------------------------------------------------------------------------------------------------- ranking
def candidates(ctx, req):
    """Usable quotes that could meet the requirement: the same material, or one in the same product family of the register."""
    fam = None
    if ctx.spec_ok:
        m = ctx.spec['materials'].get(req['material'])
        fam = m['family'] if m else None
    out = []
    for k, q in sorted(ctx.quotes.items()):
        if not q['ok']:
            continue
        if q['material'] == req['material'] or (fam and (ctx.spec['materials'].get(q['material']) or {}).get('family') == fam):
            out.append(q)
    return out


def rank(ctx, req, decision, qty_micro=None, with_index=False):
    offers = [eval_quote(ctx, q, req, decision, qty_micro, with_index) for q in candidates(ctx, req)]
    if not offers:
        return {'requirement': req['id'], 'decision': decision, 'status': 'no_offers', 'offers': [], 'ranking': [], 'excluded': [], 'outstanding': ['no usable quote for this requirement'],
                'human_approval_required': True, 'definitive': False}
    rankable = sorted((o for o in offers if o['rankable']), key=lambda o: (o['landed']['unit_cents'], o['offer']['ref']))
    excluded = [{'offer': o['offer']['ref'], 'class': o['gate']['class'], 'qualification': o['qualification'], 'why': (o['gate']['reasons'] or []) + o['limitations'] or o['blockers']}
                for o in offers if not o['rankable']]
    outstanding = []
    for o in rankable:
        outstanding.extend('%s: %s' % (o['offer']['ref'], b) for b in o['blockers'])
    if len(rankable) < 2:
        status = 'insufficient_offers'
        outstanding.insert(0, 'fewer than two offers can be ranked')
    elif outstanding:
        status = 'indicative'
    else:
        status = 'definitive'
    ranking = [{'rank': i + 1, 'offer': o['offer']['ref'], 'supplier': o['offer']['supplier'], 'unit_cents': o['landed']['unit_cents'], 'complete': o['landed']['complete'],
                'class': o['gate']['class'], 'label': status if status != 'insufficient_offers' else 'single_offer'} for i, o in enumerate(rankable)]
    out = {'requirement': req['id'], 'decision': decision, 'status': status, 'offers': offers, 'ranking': ranking, 'excluded': excluded, 'outstanding': outstanding,
           'human_approval_required': True, 'definitive': status == 'definitive'}
    if len(rankable) >= 2 and len({o['offer']['supplier'] for o in rankable}) == 1:
        # information only, not a gate: whether a one-supplier ranking may be definitive is a product-owner decision (logged as an open interpretation)
        out['notes'] = ['all ranked offers come from one supplier: this orders that supplier\'s own options and is not a comparison between suppliers']
    return out


def may_recommend(ranking):
    """-> (bool, blockers).  The only test later code may use before it treats a ranking as a basis for a recommendation."""
    if ranking['status'] != 'definitive' or not ranking['definitive']:
        return False, list(ranking['outstanding']) or ['ranking is ' + ranking['status']]
    for o in ranking['offers']:
        if o['rankable'] and o['blockers']:
            return False, ['%s: %s' % (o['offer']['ref'], b) for b in o['blockers']]
    return True, []
