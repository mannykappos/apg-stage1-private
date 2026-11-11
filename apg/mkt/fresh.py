"""The market-data and quote freshness gate.  Blueprint: Section 08 sections 7.1 (every market-dependent recommendation uses a decision-specific threshold, records the threshold and the data age, and is
downgraded or qualified when evidence is stale, unavailable or outside quote validity), 14 (expired quotes or stale data may stay as history but cannot support an unqualified current recommendation),
PG-MP-AC-07, PG-DI-AC-13.

Every state record carries the decision it was judged for, the threshold used and the age found, so a reader can see WHY it passed or not.  Thresholds come from the procurement policy; there is no default.

  quote     future (issued after the as-of day) > expired (valid-until before the as-of day; the last valid day itself is valid) > stale (older than the threshold) > current
  index     the latest usable observation on or before the as-of day: unavailable | stale | fresh.  An index is a movement series, never a price; its kind is reported as stored.
  fx        the conversion's rate age against the threshold
Qualification of an analysis: 'current' when every item is current or fresh; 'qualified' when something is stale or unavailable but nothing is expired; 'historical_only' when a quote it rests on
is expired or not yet issued (it can be shown as history, never as a current basis)."""
from . import common as C
from ..fin.intake import usable

QUOTE_OK, INDEX_OK = 'current', 'fresh'


def quote_state(q, as_of, th):
    """q: a quote view that is ok.  th: the freshness dict of the decision."""
    age = C.days(q['issue'], as_of)
    left = C.days(as_of, q['valid_until'])
    if age < 0:
        state = 'future'
    elif left < 0:
        state = 'expired'
    elif age > th['quote_max_age_days']:
        state = 'stale'
    else:
        state = QUOTE_OK
    return {'subject': q['ref'], 'class': 'quote', 'state': state, 'age_days': age, 'threshold_days': th['quote_max_age_days'], 'valid_until': q['valid_until'], 'days_to_expiry': left}


def index_state(F, material, as_of, th):
    """Latest usable index observation for the material on or before as_of."""
    best, held = None, 0
    for key in sorted(F.kind('market_observation')):
        p = F.get('market_observation', key)
        if p.get('conflict'):
            held += sum(1 for c in C.fields_list(p) if c.get('material_ref') == material and c.get('obs_date') is not None and c['obs_date'] <= as_of) > 0
            continue
        f = p.get('fields') or {}
        if f.get('material_ref') != material or f.get('obs_date') is None or f['obs_date'] > as_of:
            continue
        if not usable(p) or not isinstance(f.get('value_scaled'), int):
            held += 1
            continue
        if best is None or f['obs_date'] > best['f']['obs_date']:
            best = {'key': key, 'f': f, 'p': p}
    if best is None:
        return {'subject': 'material/' + material, 'class': 'index', 'state': 'unavailable', 'age_days': None, 'threshold_days': th['index_max_age_days'], 'observation': None,
                'held_records': held}
    f = best['f']
    age = C.days(f['obs_date'], as_of)
    return {'subject': 'market_observation/' + best['key'], 'class': 'index', 'state': 'stale' if age > th['index_max_age_days'] else INDEX_OK, 'age_days': age,
            'threshold_days': th['index_max_age_days'], 'held_records': held,
            'observation': {'ref': 'market_observation/' + best['key'], 'revision': F.rev('market_observation', best['key']), 'date': f['obs_date'], 'value_scaled': f['value_scaled'],
                            'unit': f.get('unit_text'), 'kind': f.get('kind_text'), 'source_label': f.get('source_label_text'), 'geography': f.get('geography_text'),
                            'retrieved_at': best['p']['provenance'].get('received_at')}}


def fx_state(conv, th):
    if conv['status'] != 'converted':
        return {'subject': 'fx/' + conv['from_currency'], 'class': 'fx', 'state': 'unavailable', 'age_days': None, 'threshold_days': th['fx_max_age_days'], 'why': conv['why']}
    if conv['rate_age_days'] is None:                                   # same currency: nothing to be stale
        return {'subject': 'fx/' + conv['from_currency'], 'class': 'fx', 'state': 'fresh', 'age_days': None, 'threshold_days': th['fx_max_age_days']}
    return {'subject': conv['rate_source_ref'], 'class': 'fx', 'state': 'stale' if conv['rate_age_days'] > th['fx_max_age_days'] else 'fresh', 'age_days': conv['rate_age_days'],
            'threshold_days': th['fx_max_age_days']}


def qualification(states):
    """-> 'current' | 'qualified' | 'historical_only'."""
    st = [s['state'] for s in states]
    if any(s in ('expired', 'future') for s in st):
        return 'historical_only'
    if any(s in ('stale', 'unavailable') for s in st):
        return 'qualified'
    return 'current'


def limitations(states):
    out = []
    for s in states:
        if s['state'] in (QUOTE_OK, INDEX_OK):
            continue
        if s['state'] == 'expired':
            out.append('%s expired %d days before the as-of day (valid until %s): history only, not a current basis' % (s['subject'], -s['days_to_expiry'], s['valid_until']))
        elif s['state'] == 'future':
            out.append('%s is dated after the as-of day: not yet usable' % s['subject'])
        elif s['state'] == 'stale':
            out.append('%s is %d days old against a limit of %d days for this decision' % (s['subject'], s['age_days'], s['threshold_days']))
        else:
            out.append('%s is unavailable%s' % (s['subject'], (': ' + s['why']) if s.get('why') else ': no usable observation on or before the as-of day'))
    return out
