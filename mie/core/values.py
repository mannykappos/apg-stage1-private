"""Exact values, dates and text (MIE1_SPEC sections 4.2, 4.5, 4.9, 5.3, 9.4).  A LEVEL value is a signed integer mantissa with an integer decimal exponent; no float is ever
created; ratios are exact fractions.  Dates are calendar dates and ages are whole days.  Text must be NFC and free of control characters."""
import datetime, re, unicodedata
from fractions import Fraction

DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
STAMP_RE = re.compile(r'^(\d{4}-\d{2}-\d{2})(T\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?(Z|[+-]\d{2}:\d{2})?)?$')
ID_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$')
BIDI = {'‎', '‏', '‪', '‫', '‬', '‭', '‮', '⁦', '⁧', '⁨', '⁩', '؜'}


def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def is_value(v):
    return isinstance(v, dict) and set(v) == {'mantissa', 'exponent'} and is_int(v['mantissa']) and is_int(v['exponent'])


def value_problem(v, limits):
    """-> None or the reason a value is refused: a float, NaN, infinity, boolean or numeric string is never a value; limits bound the exponent and the digits."""
    if not is_value(v):
        return 'value must be {mantissa: integer, exponent: integer}'
    if abs(v['exponent']) > limits['max_abs_exponent']:
        return 'exponent beyond the configured bound'
    if len(str(abs(v['mantissa']))) > limits['max_mantissa_digits']:
        return 'mantissa beyond the configured number of digits'
    return None


def exact(v):
    """{mantissa, exponent} -> Fraction (exact)."""
    m, e = v['mantissa'], v['exponent']
    return Fraction(m * 10 ** e) if e >= 0 else Fraction(m, 10 ** -e)


def in_domain(v, domain):
    m = v['mantissa']
    if domain == 'POSITIVE':
        return m > 0
    if domain == 'NON_NEGATIVE':
        return m >= 0
    return domain == 'SIGNED'


def align(a, b):
    """Two values -> (integer a, integer b, common exponent): both aligned exactly to the smaller exponent."""
    e = min(a['exponent'], b['exponent'])
    return a['mantissa'] * 10 ** (a['exponent'] - e), b['mantissa'] * 10 ** (b['exponent'] - e), e


def ratio_out(f):
    return {'num': f.numerator, 'den': f.denominator}


def decimal_out(mantissa, exponent):
    return {'mantissa': mantissa, 'exponent': exponent}


def parse_date(s):
    """'YYYY-MM-DD' -> datetime.date, or None if it is not a real calendar date in that form."""
    if not isinstance(s, str) or not DATE_RE.match(s):
        return None
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        return None


def stamp_date(s):
    """An ISO date or date-time -> its calendar date, or None."""
    if not isinstance(s, str):
        return None
    m = STAMP_RE.match(s)
    if not m:
        return None
    d = parse_date(m.group(1))
    if d is None:
        return None
    if m.group(2):
        try:
            datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
        except ValueError:
            return None
    return d


def days(a, b):
    """Whole calendar days from date string a to date string b (b - a)."""
    return (parse_date(b) - parse_date(a)).days


def shift(d, n):
    """date string d plus n days -> date string."""
    return (parse_date(d) + datetime.timedelta(days=n)).isoformat()


def text_problem(s, max_len):
    """-> None or why a text value is refused: not a string, not NFC, control or bidirectional-control characters, too long."""
    if not isinstance(s, str):
        return 'text required'
    if unicodedata.normalize('NFC', s) != s:
        return 'text not in NFC'
    if any(unicodedata.category(c) == 'Cc' for c in s) or any(c in BIDI for c in s):
        return 'control or direction-control characters'
    if len(s) > max_len:
        return 'text longer than the configured bound'
    return None


def id_problem(s, max_len):
    """-> None or why an identifier is refused (identifiers are a narrow ASCII set: homoglyphs and look-alike scripts are refused)."""
    p = text_problem(s, max_len)
    if p:
        return p
    if not ID_RE.match(s):
        return 'identifier outside the allowed characters'
    return None
