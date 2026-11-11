"""Freshness, completeness and decision eligibility.  Blueprint: Section 04 section 14 (and Section 08 sections 7.1 and 14 for quote and market freshness), PG-DI-AC-13.

A source can be connected and still be too old or too thin for a particular decision.  This module reports that state and what it means for a decision, from stored
receipts and records only.  It has NO built-in thresholds: how old is too old for which decision is configuration (FreshnessPolicy).  With no threshold configured the
answer is 'unconfigured' -- never 'fresh'.  Dates are ISO 'YYYY-MM-DD' strings; the as-of date is always passed in."""
import datetime
from dataclasses import dataclass, field
from fractions import Fraction

FRESH, STALE, MISSING, UNCONFIGURED, FUTURE = 'fresh', 'stale', 'missing', 'unconfigured', 'future_dated'
ELIGIBLE, QUALIFIED, CANNOT_ASSESS = 'eligible', 'qualified', 'cannot_assess'


def _d(s):
    return datetime.date.fromisoformat(s)


def age_days(older, as_of):
    return (_d(as_of) - _d(older)).days


@dataclass(frozen=True)
class FreshnessPolicy:
    """max_age_days: {decision_use: days}.  A use that is not listed is unconfigured."""
    max_age_days: dict = field(default_factory=dict)


def assess(policy, use, inputs, as_of):
    """inputs: [(label, latest_date_or_None)].  -> {'overall', 'inputs': [{'label','date','age_days','state'}]}.
    Any missing, unconfigured or future-dated input means the decision cannot be assessed; any stale input qualifies it.  Nothing is called eligible by default."""
    limit = policy.max_age_days.get(use)
    rows = []
    for label, d in inputs:
        if d is None:
            rows.append({'label': label, 'date': None, 'age_days': None, 'state': MISSING})
        elif limit is None:
            rows.append({'label': label, 'date': d, 'age_days': age_days(d, as_of), 'state': UNCONFIGURED})
        else:
            a = age_days(d, as_of)
            rows.append({'label': label, 'date': d, 'age_days': a, 'state': FUTURE if a < 0 else (STALE if a > limit else FRESH)})
    states = {r['state'] for r in rows}
    overall = CANNOT_ASSESS if (not rows or states & {MISSING, UNCONFIGURED, FUTURE}) else (QUALIFIED if STALE in states else ELIGIBLE)
    return {'use': use, 'overall': overall, 'limit_days': limit, 'inputs': rows}


def source_status(scoped, as_of, expected_sources=()):
    """Per source: last receipt, lag in days, rows and rejected rows seen.  A source we expected but never received from is listed as never_received."""
    recs = scoped.query('ingest_receipt')
    out = {}
    for r in recs:
        p = r.payload
        s = out.setdefault(p['source'], {'source': p['source'], 'last_receipt': '', 'files': 0, 'rows': 0, 'rejected_rows': 0, 'entities': set()})
        s['files'] += 1
        s['rows'] += p['counts']['rows']
        s['rejected_rows'] += p['counts']['rejected']
        s['entities'].add(p['entity'])
        s['last_receipt'] = max(s['last_receipt'], p['received_at'][:10])
    for src in expected_sources:
        out.setdefault(src, {'source': src, 'last_receipt': '', 'files': 0, 'rows': 0, 'rejected_rows': 0, 'entities': set()})
    for s in out.values():
        s['entities'] = sorted(s['entities'])
        s['lag_days'] = age_days(s['last_receipt'], as_of) if s['last_receipt'] else None
        s['state'] = 'never_received' if not s['files'] else 'received'
    return dict(sorted(out.items()))


def latest_dates(scoped, kind, date_field, group_field=None):
    """-> {group: latest date} over the accepted-or-warned current records of a kind (held and duplicate records do not count as evidence of recency)."""
    states = {r.key[len(kind) + 1:]: r.payload for r in scoped.query('recon_state') if r.key.startswith(kind + '/')}
    out = {}
    for r in scoped.query(kind):
        st = states.get(r.key)
        if r.payload.get('conflict') or st is None or st['lifecycle'] != 'current' or st['effective_outcome'] not in ('accepted', 'accepted_with_warnings'):
            continue
        d = r.payload['fields'].get(date_field)
        if d is None:
            continue
        g = r.payload['fields'].get(group_field) if group_field else '*'
        if g is None:
            continue
        out[g] = max(out.get(g, ''), d)
    return out


def quote_validity(scoped, as_of):
    """-> {quote_id: 'valid' | 'expired'} from the quote's own valid_until.  An expired quote cannot support an unqualified current recommendation (Section 08 section 7.1)."""
    out = {}
    for r in scoped.query('supplier_quote'):
        v = r.payload['fields'].get('valid_until')
        out[r.key] = 'unknown' if v is None else ('valid' if v >= as_of else 'expired')
    return out


def convert_minor(amount_minor, rate_text, from_ccy, to_ccy, pair, rate_date, rate_source):
    """Exact, reproducible currency conversion (PG-DI-AC-10).  `rate_text` is the pair's rate as stated by the source ('AUD/USD 0.6612' means 1 AUD = 0.6612 USD).
    Rounds half up in whole minor units.  Returns the converted amount WITH the source amount, rate, date, source and method, so the figure can be reproduced and challenged."""
    base, quote = pair.split('/')
    r = Fraction(rate_text)
    if r <= 0 or not isinstance(amount_minor, int) or isinstance(amount_minor, bool):
        raise ValueError('rate must be positive and amount a whole number of minor units')
    if (from_ccy, to_ccy) == (quote, base):
        exact = Fraction(amount_minor) / r
    elif (from_ccy, to_ccy) == (base, quote):
        exact = Fraction(amount_minor) * r
    else:
        raise ValueError(f'{pair} cannot convert {from_ccy} to {to_ccy}')
    n, d = exact.numerator, exact.denominator
    q, rem = divmod(abs(n) * 2 + d, 2 * d)
    cents = q if n >= 0 else -q
    return {'source_amount_minor': amount_minor, 'source_currency': from_ccy, 'converted_minor': cents, 'target_currency': to_ccy, 'rate': rate_text, 'pair': pair,
            'rate_date': rate_date, 'rate_source': rate_source, 'method': f'{from_ccy}->{to_ccy} exact fraction, half-up to whole minor units'}


def quality_summary(scoped):
    """Per record kind: how many current records are in each outcome, plus rejected rows from receipts.  Held and rejected data stays visible."""
    out = {}
    for r in scoped.query('recon_state'):
        p = r.payload
        k = out.setdefault(p['kind'], {})
        key = 'duplicate_delivery' if p['lifecycle'] == 'duplicate_of' else p['effective_outcome']
        k[key] = k.get(key, 0) + 1
    for r in scoped.query('ingest_receipt'):
        e = out.setdefault(r.payload['entity'], {})
        e['rejected_rows'] = e.get('rejected_rows', 0) + r.payload['counts']['rejected']
    return dict(sorted(out.items()))
