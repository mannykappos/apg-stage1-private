"""Currency conversion with a recorded source, date and method.  Blueprint: Section 08 sections 6 (record source and destination currencies, FX source and timestamp, conversion date and method),
12, PG-MP-AC-05.

The REFERENCE rate is the latest stored rate for the pair on or before the as-of date (method `latest_on_or_before`).  Nothing is interpolated, extrapolated or carried forward silently: the
conversion record names the rate, the stored record it came from, its date and its age, and the caller's freshness gate decides whether that age is acceptable.  The rate a supplier QUOTED is
kept separately (`stated`) and compared, never substituted.  Convention `foreign_per_aud`: a stored rate for AUD/USD of 0.6540 means 1 AUD buys 0.6540 USD, so AUD = USD / rate.  One rounding,
half away from zero, at the end of each conversion."""
from . import common as C
from ..fin.intake import usable

ROUNDING = 'half_away_from_zero_once'


def reference_rate(F, mp, currency, as_of):
    """-> (record dict, why).  record: {ref, revision, pair, date, rate_micro, age_days}.  why is set when no usable rate exists."""
    home = mp['basis']['home_currency']
    pair = '%s/%s' % (home, currency)
    best, held = None, 0
    for key in sorted(F.kind('fx_rate')):
        p = F.get('fx_rate', key)
        if p.get('conflict'):
            held += sum(1 for c in C.fields_list(p) if c.get('currency_pair') == pair and c.get('fx_date') is not None and c['fx_date'] <= as_of) > 0
            continue
        f = p.get('fields') or {}
        if f.get('currency_pair') != pair or f.get('fx_date') is None or f['fx_date'] > as_of:
            continue
        if not usable(p):
            held += 1
            continue
        r = C.micro(f.get('rate_text'))
        if not r:
            held += 1
            continue
        if best is None or f['fx_date'] > best['date']:
            best = {'ref': 'fx_rate/' + key, 'revision': F.rev('fx_rate', key), 'pair': pair, 'date': f['fx_date'], 'rate_micro': r, 'age_days': C.days(f['fx_date'], as_of),
                    'received': p['provenance'].get('received_at')}
    if best is None:
        return None, ('no usable %s rate on or before %s' % (pair, as_of)) + ('; %d held or invalid rate records were not used' % held if held else '')
    return best, ''


def _rec(minor, currency, home, aud, rate_micro, source, rate_date, age, ref, rev, status='converted', why=''):
    return {'status': status, 'why': why, 'from_currency': currency, 'from_minor': minor, 'to_currency': home, 'aud_cents': aud, 'rate_micro': rate_micro, 'convention': 'foreign_per_aud',
            'method': source, 'rounding': ROUNDING, 'rate_source_ref': ref, 'rate_revision': rev, 'rate_date': rate_date, 'rate_age_days': age}


def convert(F, mp, minor, currency, as_of):
    """-> conversion record.  Same currency: no rate needed.  Otherwise the reference rate; status 'not_converted' (with the reason) when none exists."""
    home = mp['basis']['home_currency']
    if currency == home:
        return _rec(minor, currency, home, minor, C.MICRO, 'none_same_currency', None, None, None, None)
    rate, why = reference_rate(F, mp, currency, as_of)
    if rate is None:
        return _rec(minor, currency, home, None, None, mp['fx']['method'], None, None, None, None, 'not_converted', why)
    return _rec(minor, currency, home, C.mul_div(minor, C.MICRO, rate['rate_micro']), rate['rate_micro'], mp['fx']['method'], rate['date'], rate['age_days'], rate['ref'], rate['revision'])


def convert_stated(minor, currency, home, rate_micro, rate_date, as_of):
    """The same conversion at the rate the supplier stated (kept for comparison; never the basis of a decision)."""
    if not rate_micro:
        return _rec(minor, currency, home, None, None, 'supplier_stated', rate_date, None, None, None, 'not_converted', 'the quote states no usable rate')
    age = C.days(rate_date, as_of) if rate_date else None
    return _rec(minor, currency, home, C.mul_div(minor, C.MICRO, rate_micro), rate_micro, 'supplier_stated', rate_date, age, None, None)


def divergence_bps(reference_aud, stated_aud):
    """Signed difference of the reference conversion from the stated conversion, in basis points of the stated one (positive: the reference rate makes the item MORE expensive)."""
    if reference_aud is None or stated_aud is None or stated_aud <= 0:
        return None
    from ..fin import fmath
    return fmath.bps_of(reference_aud - stated_aud, stated_aud)
