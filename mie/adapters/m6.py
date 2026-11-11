"""The M6 mapping (blocker BLK-02, MIE-L-16): how what APG already holds reaches the core, derived by reading M6 and M3 source (read only; M6 is not changed).
Two ingestion-side routes, both adapter-side and both feeding submit_observations only:

  A. Stored records.  M3 ingests the market observation and FX files into the APG store (templates TPL-BZ-MARKET-OBSERVATIONS and TPL-BZ-FX-RATES); M6 reads them
     (apg/mkt/fresh.py index_state, apg/mkt/fx.py).  records_to_messages() maps those records:
        market_observation.fields.material_ref       -> subject_id
        market_observation.fields.obs_date           -> as_of
        market_observation.fields.value_scaled       -> value {mantissa: value_scaled, exponent: 0}   (kept exactly as stored, in the stored unit; nothing rescaled)
        market_observation.fields.unit_text          -> unit
        market_observation.fields.kind_text          -> observation_class, value_basis through the pack's kind map ('index' -> HISTORICAL_MOVEMENT, INDEX)
        market_observation.fields.source_label_text  -> source_id
        market_observation.fields.geography_text     -> market
        provenance.received_at                       -> retrieved_at
        (the pack's licence for the source)          -> licence_ref
        fx_rate.fields.currency_pair, fx_date, rate_text -> subject 'FX:<pair>', as_of, value parsed exactly from the decimal text (0.6540 -> mantissa 6540, exponent -4),
                                                         in the conversion's rate unit, class CURRENT_REFERENCE, basis INDEX
     A record M4/M6 would not use (fin.intake.usable is false) is not submitted and is reported here.  A conflict marker is submitted as each of its contenders, so that the core
     reports the conflict (it never chooses).
  B. The M6 MarketFeedPort.  feed_to_messages() maps what MarketFeedPort.fetch returns (obs_date, value, unit, kind, source_label, geography, retrieved_at) the same way;
     M6FeedAdapter wraps an M6 feed as the feed adapter for the ingestion driver (FL-10).  The M6 port definition is not edited.

Which component runs these, when, and against which feed is the Anchor Engine's (MIE-OQ-25, ND7-10).  Nothing here is wired into an APG finding or recommendation."""
import re

DECIMAL = re.compile(r'^(-?)(\d+)(?:\.(\d+))?$')


def exact_decimal(text):
    """'0.6540' -> {mantissa 6540, exponent -4}; None for anything that is not a plain decimal."""
    if not isinstance(text, str):
        return None
    m = DECIMAL.match(text.strip())
    if not m:
        return None
    sign, whole, frac = m.group(1), m.group(2), m.group(3) or ''
    mant = int(whole + frac)
    return {'mantissa': -mant if sign else mant, 'exponent': -len(frac)}


def _contenders(payload):
    if payload.get('conflict'):
        return [c.get('fields') or {} for c in payload['conflict']['contenders']]
    return [payload.get('fields') or {}]


def records_to_messages(scoped, doc, kind_map, fx_units, usable):
    """APG store records of the calling tenant -> (messages, skipped).  `scoped` is an APG scoped store; `usable` is apg.fin.intake.usable; fx_units is
    {pair: (rate_unit, market)} from the owner's conversion declarations.  Only subjects the pack declares are mapped."""
    licence = {s['source_id']: s['licence_ref'] for s in doc['sources']}
    subjects = {s['subject_id'] for s in doc['vocabulary']['subjects']}
    msgs, skipped = [], []
    for rec in scoped.query('market_observation'):
        p = rec.payload
        if not p.get('conflict') and not usable(p):
            skipped.append({'record': 'market_observation/' + rec.key, 'why': 'not usable in M4/M6'})
            continue
        for f in _contenders(p):
            if f.get('material_ref') not in subjects:
                skipped.append({'record': 'market_observation/' + rec.key, 'why': 'a material the pack does not track'})
                continue
            cls = kind_map.get(f.get('kind_text'))
            if cls is None:
                skipped.append({'record': 'market_observation/' + rec.key, 'why': 'a kind the pack does not map'})
                continue
            msgs.append({'subject_id': f['material_ref'], 'source_id': f.get('source_label_text'), 'licence_ref': licence.get(f.get('source_label_text')),
                         'market': f.get('geography_text'), 'unit': f.get('unit_text'), 'observation_class': cls[0], 'value_basis': cls[1],
                         'as_of': f.get('obs_date'), 'retrieved_at': p['provenance'].get('received_at'),
                         'value': {'mantissa': f['value_scaled'], 'exponent': 0} if isinstance(f.get('value_scaled'), int) else f.get('value_scaled'),
                         'adapter_notes': {'apg_record': 'market_observation/' + rec.key}})
    for rec in scoped.query('fx_rate'):
        p = rec.payload
        if not p.get('conflict') and not usable(p):
            skipped.append({'record': 'fx_rate/' + rec.key, 'why': 'not usable in M4/M6'})
            continue
        for f in _contenders(p):
            pair = f.get('currency_pair')
            sid = 'FX:%s' % pair
            if pair not in fx_units or sid not in subjects:
                skipped.append({'record': 'fx_rate/' + rec.key, 'why': 'a currency pair the pack does not declare'})
                continue
            unit, market = fx_units[pair]
            msgs.append({'subject_id': sid, 'source_id': 'APG-FX-RATES', 'licence_ref': licence.get('APG-FX-RATES'), 'market': market, 'unit': unit,
                         'observation_class': 'CURRENT_REFERENCE', 'value_basis': 'INDEX', 'as_of': f.get('fx_date'),
                         'retrieved_at': p['provenance'].get('received_at'), 'value': exact_decimal(f.get('rate_text')),
                         'adapter_notes': {'apg_record': 'fx_rate/' + rec.key}})
    return msgs, skipped


def feed_to_messages(fetched, subject_id, licence_ref, kind_map, retrieved_at=None):
    """What an M6 MarketFeedPort.fetch returned -> observation messages.  The M6 port's observations carry no retrieval date, so the adapter asserts one (retrieved_at,
    from the host's clock on the adapter side); the core checks only that it is not earlier than as_of (MIE-L-18)."""
    out = []
    for o in fetched['observations']:
        cls = kind_map.get(o.get('kind'), (None, None))
        out.append({'subject_id': subject_id, 'source_id': o.get('source_label'), 'licence_ref': licence_ref, 'market': o.get('geography'), 'unit': o.get('unit'),
                    'observation_class': cls[0], 'value_basis': cls[1], 'as_of': o.get('obs_date'), 'retrieved_at': o.get('retrieved_at') or retrieved_at,
                    'value': {'mantissa': o['value'], 'exponent': 0} if isinstance(o.get('value'), int) and not isinstance(o.get('value'), bool) else o.get('value'),
                    'adapter_notes': {'m6_obs_id': str(o.get('obs_id'))}})
    return out


class M6FeedAdapter:
    """FL-10: a mapping adapter over an M6 MarketFeedPort.  It calls the M6 port (adapter-side), maps the answer and hands messages to the ingestion driver.
    max_age_days is required by the M6 port (it has no default) and is the integrator's to pass; retrieved_on is the integrator's adapter-side clock (a callable giving the
    ISO date of retrieval), because the M6 port does not report one."""
    def __init__(self, m6_feed, m6_ctx, mapping, kind_map, max_age_days, retrieved_on):
        self.feed, self.ctx, self.mapping, self.kind_map, self.max_age, self.retrieved_on = m6_feed, m6_ctx, mapping, kind_map, max_age_days, retrieved_on

    def retrieve(self, tenant, series_ref, evaluation_date):
        from .feed import FeedUnavailable
        subject_id, licence_ref = self.mapping[series_ref]
        try:
            fetched = self.feed.fetch(self.ctx, series_ref, evaluation_date, self.max_age)
        except Exception as e:
            raise FeedUnavailable('M6 feed: %s' % type(e).__name__)
        return feed_to_messages(fetched, subject_id, licence_ref, self.kind_map, self.retrieved_on())
