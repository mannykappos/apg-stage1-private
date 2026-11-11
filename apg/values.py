"""Values that know when they are not known.

Section 04 section 8/10: missing critical values are not silently invented or defaulted.  Section 05 AC-04/AC-15: missing or stale inputs
give an explicitly qualified result; zero denominators give an explicit qualified outcome.  So an unknown value here can never be turned
into a number by accident: arithmetic on it raises, and totals say which inputs they leave out and why.

The reasons mirror the AUIF distinctions: no data / could not obtain data / invalid data / ambiguous data / stale, plus conflicted
(two sources disagree) and excluded (held out of authoritative use by a control)."""
from dataclasses import dataclass

NO_DATA, NOT_OBTAINED, INVALID, AMBIGUOUS, STALE, CONFLICTED, EXCLUDED = (
    'no_data', 'not_obtained', 'invalid', 'ambiguous', 'stale', 'conflicted', 'excluded')
REASONS = (NO_DATA, NOT_OBTAINED, INVALID, AMBIGUOUS, STALE, CONFLICTED, EXCLUDED)


class UnknownValueError(TypeError):
    """Raised when code tries to use an unknown value as if it were a number."""


@dataclass(frozen=True)
class Known:
    cents: int
    evidence: tuple = ()          # references (record kind/key/revision strings) the value rests on

    def __post_init__(self):
        if not isinstance(self.cents, int) or isinstance(self.cents, bool):
            raise TypeError('Known.cents must be an int (integer cents)')

    def __bool__(self):
        raise UnknownValueError('use .cents explicitly; truthiness of money is ambiguous')


@dataclass(frozen=True)
class Unknown:
    reason: str
    detail: str = ''

    def __post_init__(self):
        if self.reason not in REASONS:
            raise ValueError(f'unknown reason {self.reason!r}')

    @property
    def cents(self):
        raise UnknownValueError(f'value is unknown ({self.reason}): {self.detail}')

    def __bool__(self):
        raise UnknownValueError('an unknown value has no truth value')

    def _no(self, *a, **k):
        raise UnknownValueError(f'arithmetic on an unknown value ({self.reason}) is refused')
    __add__ = __radd__ = __sub__ = __rsub__ = __mul__ = __rmul__ = __int__ = __float__ = __lt__ = __gt__ = __le__ = __ge__ = _no


def as_value(x, reason=NO_DATA, detail=''):
    """Turn a raw cell into Known/Unknown.  None or '' -> Unknown(reason); a non-integer string or a float -> Unknown(INVALID)."""
    if isinstance(x, (Known, Unknown)):
        return x
    if x is None or x == '':
        return Unknown(reason, detail)
    if isinstance(x, bool):
        return Unknown(INVALID, 'boolean is not money')
    if isinstance(x, int):
        return Known(x)
    if isinstance(x, str):
        s = x.strip()
        if s and (s.isascii() and (s.isdigit() or (s[0] == '-' and s[1:].isdigit()))):
            return Known(int(s))
        return Unknown(INVALID, f'not a whole number of cents: {x!r}')
    return Unknown(INVALID, f'unsupported type {type(x).__name__}')


@dataclass(frozen=True)
class Total:
    """A sum that says what it leaves out.  `complete` is True only if nothing was left out."""
    cents: int
    complete: bool
    included: tuple
    left_out: tuple          # ((id, reason, detail), ...)

    def require_complete(self):
        if not self.complete:
            raise UnknownValueError(f'total is incomplete: {len(self.left_out)} input(s) left out')
        return self.cents


def total(items):
    """items: iterable of (id, Known|Unknown|raw).  Unknown items are left out and listed, never counted as zero."""
    s, inc, out = 0, [], []
    for iid, v in items:
        v = as_value(v)
        if isinstance(v, Known):
            s += v.cents; inc.append(iid)
        else:
            out.append((iid, v.reason, v.detail))
    return Total(s, not out, tuple(inc), tuple(out))


def ratio_bps(numerator, denominator):
    """Basis points, integer, rounded half away from zero.  A missing, unknown or non-positive denominator gives Unknown, never zero."""
    n, d = as_value(numerator), as_value(denominator)
    if isinstance(n, Unknown):
        return n
    if isinstance(d, Unknown):
        return d
    if d.cents <= 0:
        return Unknown(INVALID, 'denominator is zero or negative')
    q, r = divmod(abs(n.cents) * 10000, d.cents)
    if 2 * r >= d.cents:
        q += 1
    return Known(q if n.cents >= 0 else -q)
