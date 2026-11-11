"""Exact integer arithmetic for money.  No floats anywhere.  Blueprint: Section 05 section 12 (decimal-safe arithmetic, zero denominators), PG-PC-AC-14, PG-PC-AC-15.

round_div rounds half AWAY from zero: 5/2 -> 3, -5/2 -> -3.  That is one stated rounding rule applied at the END of a calculation (never in the middle), so the same
inputs always give the same cents."""
import datetime


def round_div(n, d):
    """n / d rounded half away from zero.  d must be a positive int."""
    if not isinstance(n, int) or isinstance(n, bool) or not isinstance(d, int) or isinstance(d, bool):
        raise TypeError('round_div needs integers')
    if d <= 0:
        raise ValueError('divisor must be positive')
    q, r = divmod(abs(n), d)
    if 2 * r >= d:
        q += 1
    return q if n >= 0 else -q


def scale_cents(cents, num, den):
    """cents * num / den, rounded once at the end."""
    return round_div(cents * num, den)


def bps_of(numerator, denominator):
    """numerator / denominator in basis points (integer, half away from zero), or None when the denominator is zero or negative (no valid ratio)."""
    if denominator <= 0:
        return None
    return round_div(numerator * 10000, denominator)


def parse_date(text):
    if not isinstance(text, str) or len(text) != 10:
        raise ValueError(f'not an ISO date: {text!r}')
    d = datetime.date.fromisoformat(text)
    if d.isoformat() != text:
        raise ValueError(f'not an ISO date: {text!r}')
    return d


def days_between(start, end):
    """Whole days from start to end (end - start); negative if end is earlier.  Dates are ISO text."""
    return (parse_date(end) - parse_date(start)).days


def carrying_cents(balance_cents, rate_bps, days, basis):
    """Section 12 section 7:  Eligible Balance x Annual Rate x Eligible Days / Day-Count Basis, rounded once.  rate_bps is the annual rate in basis points (780 = 7.80%)."""
    for v in (balance_cents, rate_bps, days, basis):
        if not isinstance(v, int) or isinstance(v, bool):
            raise TypeError('carrying cost needs integers')
    if balance_cents < 0 or rate_bps < 0 or days < 0:
        raise ValueError('balance, rate and days must not be negative')
    if basis <= 0:
        raise ValueError('day-count basis must be positive')
    return round_div(balance_cents * rate_bps * days, 10000 * basis)
