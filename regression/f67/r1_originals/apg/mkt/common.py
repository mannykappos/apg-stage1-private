"""Shared helpers for the M6 procurement analyses and rules: rule start-up (is it configured?), run records, exact decimal reading, and NORMALISED VIEWS of the stored records.

Nothing here reads the store, the clock or any global.  A view says whether its record is USABLE and, when it is not, why; a rule that meets an unusable record lists it (never silently
uses it, never silently drops it).  Quantities are held in millionths so that decimals are exact; money is whole cents; rates are millionths of a unit."""
from . import policy as MP
from ..det import common as DC
from ..fin import fmath
from ..fin.intake import usable
import datetime

RULE_VERSIONS = {rid: 1 for rid in MP.RULE_IDS}
RUN_STATES = DC.RUN_STATES
MICRO = 1_000_000
money, pct, days, micro = DC.money, DC.pct, DC.days, DC.micro


def add_days(date, n):
    return (fmath.parse_date(date) + datetime.timedelta(days=n)).isoformat()


class MissingParam(LookupError):
    """A policy value an analysis needed was not configured.  The name is the dotted path, so the run can say exactly which decision is missing; nothing is ever defaulted."""


class Strict(dict):
    """A policy view whose lookups refuse to default: `p['a']['b']` raises MissingParam('a.b') when absent.  `get`, `in` and iteration behave like a dict (absence is allowed to be tested)."""
    def __init__(self, d, path=''):
        super().__init__(d)
        self._path = path

    def __getitem__(self, k):
        if k not in self:
            raise MissingParam(self._path + str(k))
        v = dict.__getitem__(self, k)
        return Strict(v, self._path + str(k) + '.') if isinstance(v, dict) else v

    def get(self, k, default=None):
        if k not in self:
            return default
        return self[k]


def mkt_policy(F):
    ver = F.params.get('mkt_policy')
    p = F.get(MP.POLICY_KIND, ver) if ver else None
    return Strict(MP.view(p)) if p is not None else None


def mkt_spec(F):
    ver = F.params.get('mkt_spec')
    p = F.get(MP.SPEC_KIND, ver) if ver else None
    return MP.spec_view(p) if p is not None else None


def new_run(rid):
    return {'rule': rid, 'version': RULE_VERSIONS[rid], 'status': 'evaluated', 'evaluated': 0, 'signals': 0, 'silent': 0, 'not_assessed': [], 'notes': [], 'missing_parameters': [], 'decision': ''}


def start(F, mp, rid):
    """-> (rule dict, params, run).  rule is None when the rule does not run; the run record then says why (never a silent skip)."""
    run = new_run(rid)
    if mp is None:
        run['status'] = 'cannot_assess'
        run['notes'].append('MKT_POLICY_NOT_PINNED')
        return None, None, run
    ent = (mp.get('rules') or {}).get(rid)
    if ent is not None and ent.get('enabled') is False:
        run['status'] = 'disabled'
        run['notes'].append('SWITCHED_OFF_IN_POLICY')
        return None, None, run
    params, miss = MP.rule_params(mp, rid)
    if params is None:
        run['status'] = 'not_configured'
        run['missing_parameters'] = miss
        run['decision'] = MP.RULES[rid][2]
        return None, None, run
    return {'id': 'DET-' + rid, 'version': RULE_VERSIONS[rid], 'params': params}, params, run


def cannot(run, *codes):
    run['status'] = 'cannot_assess'
    run['notes'].extend(codes)
    return [], run


def held_codes(p):
    if p.get('conflict'):
        return ['CONFLICT_SAME_KEY']
    return list(p['intrinsic']['pending']) or ['NOT_USABLE']


def qty_micro(v):
    """Stored quantity -> millionths: an int (purchase-order quantity) or exact decimal text.  None when it is not a non-negative number."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v * MICRO if v >= 0 else None
    return micro(v)


def fmt_qty(q):
    whole, frac = divmod(q, MICRO)
    return str(whole) if not frac else (str(whole) + '.' + ('%06d' % frac).rstrip('0'))


def mul_div(a, b, d):
    """a * b / d rounded half away from zero, once."""
    return fmath.round_div(a * b, d)


# ---------------------------------------------------------------------------------------------------------------- normalised views
def _base(F, kind, key):
    p = F.get(kind, key)
    return p, ('%s/%s' % (kind, key)), F.rev(kind, key)


def quote_view(F, key):
    p, ref, rev = _base(F, 'supplier_quote', key)
    if p is None:
        return None
    v = {'key': key, 'ref': ref, 'rev': rev, 'ok': False, 'why': [], 'supplier': DC.supplier_of(F, 'supplier_quote', key)}
    if p.get('conflict') or not usable(p):
        v['why'] = held_codes(p)
        return v
    st = F.recon('supplier_quote', key)
    if st is None:
        v['why'] = ['NOT_RECONCILED']
        return v
    if st['effective_outcome'] not in ('accepted', 'accepted_with_warnings') or st['lifecycle'] == 'duplicate_of':
        v['why'] = ['DUPLICATE_OF:' + str(st.get('duplicate_of'))] if st['lifecycle'] == 'duplicate_of' else ['RECONCILIATION:' + str(st['effective_outcome'])]
        return v
    f = p['fields']
    fx = f.get('fx_rate_used')
    v.update(ok=True, material=f.get('material_ref'), spec_text=f.get('specification_text'), issue=f.get('issue_date'), valid_until=f.get('valid_until'), rate=f.get('unit_rate_minor_units'),
             cur=f.get('currency_code'), fx_used=micro(fx) if isinstance(fx, str) else None, fx_text=fx, fx_date=f.get('fx_rate_date'), freight=f.get('freight_per_unit_cents'),
             basis=(f.get('delivery_basis') or '').strip().lower(), lead=f.get('lead_time_days'), kind=f.get('price_kind'), received=p['provenance'].get('received_at'),
             source=p['provenance'].get('source'))
    return v


def po_view(F, key):
    """A purchase order.  `ok` means usable AND reconciled as accepted.  An order that reconciliation holds back only because it looks like a duplicate of another (`DUPLICATE_CANDIDATE:`) is NOT ok,
    but its fields are filled and `dup_candidates` names the other order(s): the over-ordering and duplicate analyses must see it, the financial figures do not."""
    p, ref, rev = _base(F, 'purchase_order', key)
    if p is None:
        return None
    v = {'key': key, 'ref': ref, 'rev': rev, 'ok': False, 'why': [], 'supplier': DC.supplier_of(F, 'purchase_order', key), 'dup_candidates': []}
    if p.get('conflict') or not usable(p):
        v['why'] = held_codes(p)
        return v
    st = F.recon('purchase_order', key)
    if st is None:
        v['why'] = ['NOT_RECONCILED']
        return v
    f = p['fields']
    q = qty_micro(f.get('quantity'))
    if q is None or q <= 0:
        v['why'] = ['QUANTITY_NOT_POSITIVE']
        return v
    v.update(project=f.get('project_ref'), material=f.get('material_ref'), qty=q, unit=f.get('unit_of_measure'), rate=f.get('unit_rate_cents'), amount=st['amount_cents'],
             date=f.get('order_date'), status=f.get('source_status'), cost_code=f.get('cost_code_ref'), received=p['provenance'].get('received_at'))
    if st['lifecycle'] == 'duplicate_of':
        v['why'] = ['DUPLICATE_OF:' + str(st.get('duplicate_of'))]
        v['duplicate_of'] = st.get('duplicate_of')
        return v
    if st['effective_outcome'] not in ('accepted', 'accepted_with_warnings'):
        v['why'] = ['RECONCILIATION:' + str(st['effective_outcome'])]
        v['dup_candidates'] = sorted(c for x in st.get('findings', []) if x['code'].startswith('DUPLICATE_CANDIDATE:') for c in x['code'].split(':', 1)[1].split(','))      # reconciliation joins several candidates with commas
        return v
    v['ok'] = True
    return v


def simple_view(F, kind, key, need=()):
    """View of a kind ingested by M6 intake: usable by its intrinsic outcome.  `need`: fields that must be present for the record to be of use."""
    p, ref, rev = _base(F, kind, key)
    if p is None:
        return None
    v = {'key': key, 'ref': ref, 'rev': rev, 'ok': False, 'why': []}
    if p.get('conflict') or not usable(p):
        v['why'] = held_codes(p)
        return v
    f = p['fields']
    miss = [n for n in need if f.get(n) is None]
    if miss:
        v['why'] = ['MISSING:' + ','.join(miss)]
        return v
    v['ok'] = True
    v['f'] = f
    v['received'] = p['provenance'].get('received_at')
    return v


def demand_view(F, key):
    v = simple_view(F, 'material_demand', key, ('project_ref', 'material_ref', 'quantity', 'required_date'))
    if v is not None and v['ok']:
        f = v['f']
        q = qty_micro(f['quantity'])
        if q is None or q <= 0:
            v.update(ok=False, why=['QUANTITY_NOT_POSITIVE'])
        else:
            v.update(project=f['project_ref'], material=f['material_ref'], qty=q, unit=f.get('unit_text'), required=f['required_date'])
    return v


def delivery_view(F, key):
    v = simple_view(F, 'delivery', key, ('purchase_order_ref', 'qty_delivered', 'delivery_date'))
    if v is not None and v['ok']:
        f = v['f']
        d, a = qty_micro(f['qty_delivered']), (qty_micro(f['qty_accepted']) if f.get('qty_accepted') is not None else None)
        if d is None or (f.get('qty_accepted') is not None and a is None):
            v.update(ok=False, why=['QUANTITY_INVALID'])
        else:
            v.update(po=f['purchase_order_ref'], material=f.get('material_ref'), date=f['delivery_date'], delivered=d, accepted=a)
    return v


def fields_list(p):
    """The field dicts a stored record speaks with: its own, or every contender's when it is a conflict marker."""
    if p.get('conflict'):
        return [c.get('fields') or {} for c in p['conflict']['contenders']]
    return [p.get('fields') or {}]


def names_quote(F, kind, key, quote_key):
    """True when the stored record names the quote.  A record in conflict names whatever its contenders name: a conflicted reading, tier, term, assumption or check must still be shown as HELD
    for its quote (never dropped because the marker itself carries no fields)."""
    p = F.get(kind, key)
    if p is None:
        return False
    if p.get('conflict'):
        return any((c.get('fields') or {}).get('quote_ref') == quote_key for c in p['conflict']['contenders'])
    return (p.get('fields') or {}).get('quote_ref') == quote_key


def keys_of(F, kind):
    return sorted(F.kind(kind))


def views(F, kind, fn):
    return {k: fn(F, k) for k in keys_of(F, kind)}


def unit_of(F, material):
    """Unit of measure of a material from the master record, or None."""
    v = simple_view(F, 'material', material, ('unit_text',)) if F.get('material', material) is not None else None
    return v['f']['unit_text'] if v is not None and v['ok'] else None
